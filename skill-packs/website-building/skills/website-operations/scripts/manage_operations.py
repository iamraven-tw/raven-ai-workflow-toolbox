#!/usr/bin/env python3
"""設定、檢查、備份與隔離復原一人公司官網。

本工具只對公開網址發 GET。任何本機寫入都要求顯式旗標；它不部署、不回滾、
不送出表單，也不處理 Cloudflare 或外部服務憑證。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = SKILL_ROOT / "assets/default-operations.json"
WORKSPACE_SETUP = Path("website/config.json")
OPERATIONS_CONFIG = Path("website/operations.json")
STATE_DIR = Path(".local/website/operations")
STATE_FILE = STATE_DIR / "state.json"
HEALTH_HISTORY = STATE_DIR / "health-history.json"
DEFAULT_BACKUP_DIR = STATE_DIR / "backups"
BACKUP_FORMAT = "website-operations-backup"
MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
EXCLUDED_DIRS = {".git", ".astro", ".local", ".wrangler", "dist", "node_modules"}
SECRET_NAMES = {
    ".dev.vars",
    "credentials.json",
    "credential.json",
    "secrets.json",
    "secret.json",
    "id_rsa",
    "id_ed25519",
}
SECRET_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}
SECRET_KEY = re.compile(
    r"(^|[_-])(token|secret|password|passwd|cookie|credential|api[_-]?key|access[_-]?key|client[_-]?secret)([_-]|$)",
    re.IGNORECASE,
)
SECRET_VALUE = (
    re.compile(r"\b(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{12,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{12,}\b", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


class OperationsError(RuntimeError):
    """表示必須停止且不可假設操作成功。"""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def canonical_json(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_hash(path: Path) -> str | None:
    if not os.path.lexists(path):
        return None
    if path.is_symlink() or not path.is_file():
        raise OperationsError(f"受管理路徑必須是一般檔案：{path}")
    return sha256_file(path)


def read_json(path: Path, *, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise OperationsError(f"{label}必須是一般 JSON 檔案：{path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise OperationsError(f"{label}不是有效 JSON：{error}") from error
    if not isinstance(value, dict):
        raise OperationsError(f"{label}根節點必須是 object")
    return value


def exact_keys(value: Any, expected: set[str], *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise OperationsError(f"{label}欄位不符；預期 {sorted(expected)}，實際 {actual}")
    return value


def reject_secret_material(value: Any, *, label: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if SECRET_KEY.search(str(key)):
                raise OperationsError(f"{label}.{key} 看似秘密欄位，不得寫入維運設定")
            reject_secret_material(child, label=f"{label}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_secret_material(child, label=f"{label}[{index}]")
    elif isinstance(value, str) and any(pattern.search(value) for pattern in SECRET_VALUE):
        raise OperationsError(f"{label} 看似包含秘密，不得寫入維運設定")


def validate_public_url(value: Any, *, allow_local: bool = False) -> str:
    if not isinstance(value, str) or not value or len(value) > 1000:
        raise OperationsError("公開網址必須是 HTTPS origin")
    parsed = urllib.parse.urlsplit(value)
    local = allow_local and parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    if not ((parsed.scheme == "https" and parsed.hostname) or local):
        raise OperationsError("公開網址只接受 HTTPS；隔離測試可用 localhost／127.0.0.1 HTTP")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise OperationsError("公開網址只能包含沒有帳密、query 或 fragment 的 origin")
    if parsed.hostname and (parsed.hostname == "example.invalid" or parsed.hostname.endswith(".example.invalid")):
        raise OperationsError("公開網址仍是 example.invalid")
    return value.rstrip("/")


def validate_relative_path(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 300 or "\\" in value:
        raise OperationsError(f"{label} 必須是使用 / 的相對路徑")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise OperationsError(f"{label} 不得是絕對路徑或逸出根目錄")
    for part in path.parts:
        if (any(ord(char) < 32 or char in ':<>"|?*' for char in part)
                or part.endswith((".", " "))
                or re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part)):
            raise OperationsError(f"{label} 含不安全路徑片段：{part}")
    return value


def checked_path(path: Path) -> Path:
    """解析前拒絕連結祖先，避免 Windows junction 或 symlink 隱藏逸出。"""
    absolute = path.expanduser().absolute()
    for item in (absolute, *absolute.parents):
        if item.is_symlink() or getattr(item, "is_junction", lambda: False)():
            raise OperationsError(f"路徑不得包含 symlink／junction：{item}")
    return absolute.resolve(strict=False)


def integer(value: Any, *, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise OperationsError(f"{label} 必須介於 {minimum} 與 {maximum} 的整數")
    return value


def validate_config(payload: dict[str, Any]) -> dict[str, Any]:
    reject_secret_material(payload)
    exact_keys(payload, {"schema_version", "status", "public_url", "health", "backup", "updates"}, label="$")
    if payload["schema_version"] != 1 or payload["status"] not in {"not_configured", "configured"}:
        raise OperationsError("schema_version 必須是 1，status 必須是 not_configured 或 configured")

    health = exact_keys(
        payload["health"],
        {"enabled", "timeout_seconds", "tls_warning_days", "history_limit", "checks"},
        label="$.health",
    )
    if not isinstance(health["enabled"], bool):
        raise OperationsError("$.health.enabled 必須是 boolean")
    integer(health["timeout_seconds"], label="$.health.timeout_seconds", minimum=1, maximum=60)
    integer(health["tls_warning_days"], label="$.health.tls_warning_days", minimum=1, maximum=180)
    integer(health["history_limit"], label="$.health.history_limit", minimum=1, maximum=1000)
    checks = health["checks"]
    if not isinstance(checks, list) or not 1 <= len(checks) <= 20:
        raise OperationsError("$.health.checks 必須有 1–20 個項目")
    seen_paths: set[str] = set()
    for index, item in enumerate(checks):
        check = exact_keys(item, {"path", "expected_status", "required_text"}, label=f"$.health.checks[{index}]")
        path = check["path"]
        if not isinstance(path, str) or not path.startswith("/") or path.startswith("//") or any(char in path for char in "?#") or len(path) > 300:
            raise OperationsError(f"$.health.checks[{index}].path 必須是站內絕對 path，且不得含 query 或 fragment")
        if path in seen_paths:
            raise OperationsError(f"健康檢查 path 重複：{path}")
        seen_paths.add(path)
        integer(check["expected_status"], label=f"$.health.checks[{index}].expected_status", minimum=100, maximum=599)
        required = check["required_text"]
        if required is not None and (not isinstance(required, str) or not required or len(required) > 300):
            raise OperationsError(f"$.health.checks[{index}].required_text 必須是 null 或 1–300 字元")

    backup = exact_keys(
        payload["backup"],
        {"retention_count", "stale_after_days", "workspace_paths", "project_paths"},
        label="$.backup",
    )
    integer(backup["retention_count"], label="$.backup.retention_count", minimum=1, maximum=100)
    integer(backup["stale_after_days"], label="$.backup.stale_after_days", minimum=1, maximum=365)
    for key in ("workspace_paths", "project_paths"):
        paths = backup[key]
        if not isinstance(paths, list) or not 1 <= len(paths) <= 50 or len(set(paths)) != len(paths):
            raise OperationsError(f"$.backup.{key} 必須有 1–50 個不重複相對路徑")
        for index, path in enumerate(paths):
            validate_relative_path(path, label=f"$.backup.{key}[{index}]")

    updates = exact_keys(
        payload["updates"],
        {"exact_versions_only", "automatic_apply", "verified_backup_required", "local_build_required", "separate_deploy_authorization_required"},
        label="$.updates",
    )
    required_update_values = {
        "exact_versions_only": True,
        "automatic_apply": False,
        "verified_backup_required": True,
        "local_build_required": True,
        "separate_deploy_authorization_required": True,
    }
    if updates != required_update_values:
        raise OperationsError("更新政策必須維持精確版本、禁止自動套用、先驗證備份與建置、另行授權部署")

    public_url = payload["public_url"]
    if public_url is not None:
        validate_public_url(public_url)
    if health["enabled"] and public_url is None:
        raise OperationsError("啟用健康檢查時必須提供 public_url")
    if payload["status"] == "not_configured" and (public_url is not None or health["enabled"]):
        raise OperationsError("not_configured 不得設定公開網址或啟用健康檢查")
    if payload["status"] == "configured" and not backup["workspace_paths"]:
        raise OperationsError("configured 必須保留至少一個工作區備份路徑")
    return payload


def validate_roots(workspace_raw: str, project_raw: str) -> tuple[Path, Path]:
    workspace = checked_path(Path(workspace_raw))
    project = checked_path(Path(project_raw))
    if not workspace.is_dir() or not (workspace / WORKSPACE_SETUP).is_file():
        raise OperationsError("工作區不存在或缺少 website/config.json；請先完成 website-setup")
    if not project.is_dir() or not (project / "package.json").is_file():
        raise OperationsError("網站專案不存在或缺少 package.json；請先完成 website-build")
    if workspace.is_symlink() or project.is_symlink():
        raise OperationsError("工作區與網站專案根目錄不得是 symlink")
    return workspace, project


def write_atomic(path: Path, content: bytes) -> None:
    checked_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-website-operations")
    with temporary.open("xb") as output:
        output.write(content)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def config_plan(workspace: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    validate_config(candidate)
    target = workspace / OPERATIONS_CONFIG
    current = file_hash(target)
    candidate_hash = sha256_bytes(canonical_json(candidate))
    digest = sha256_bytes(
        canonical_json({"workspace_root": str(workspace), "current": current, "candidate": candidate_hash})
    )
    return {
        "result": "configure_plan",
        "plan_sha256": digest,
        "change": "unchanged" if current == candidate_hash else ("create" if current is None else "update"),
        "target": OPERATIONS_CONFIG.as_posix(),
        "public_url": candidate["public_url"],
        "health_enabled": candidate["health"]["enabled"],
        "external_effects": [],
        "contains_credentials": False,
    }


def command_configure(workspace: Path, candidate: dict[str, Any], expected_plan: str, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise OperationsError("缺少 --confirm-write；未修改任何檔案")
    plan = config_plan(workspace, candidate)
    if plan["plan_sha256"] != expected_plan:
        raise OperationsError("plan 雜湊已失效；候選設定或目標檔案已變更，請重新 configure-plan")
    target = workspace / OPERATIONS_CONFIG
    state = workspace / STATE_FILE
    previous_target = target.read_bytes() if target.is_file() and not target.is_symlink() else None
    previous_state = state.read_bytes() if state.is_file() and not state.is_symlink() else None
    try:
        write_atomic(target, canonical_json(candidate))
        write_atomic(
            state,
            canonical_json(
                {
                    "schema_version": 1,
                    "config_sha256": sha256_bytes(canonical_json(candidate)),
                    "configured_at": utc_now(),
                    "contains_credentials": False,
                }
            ),
        )
    except OSError as error:
        for path, previous in ((target, previous_target), (state, previous_state)):
            try:
                if previous is None:
                    if path.is_file() and not path.is_symlink():
                        path.unlink()
                else:
                    write_atomic(path, previous)
            except OSError:
                pass
        raise OperationsError(f"設定寫入失敗，已嘗試回復：{error}") from error
    return {"result": "configured", "config_sha256": sha256_bytes(canonical_json(candidate)), "contains_credentials": False}


def load_config(workspace: Path) -> dict[str, Any]:
    path = workspace / OPERATIONS_CONFIG
    if not path.is_file():
        raise OperationsError("缺少 website/operations.json；請先 configure-plan 再 configure")
    return validate_config(read_json(path, label="維運設定"))


def latest_health(workspace: Path) -> dict[str, Any] | None:
    path = workspace / HEALTH_HISTORY
    if not path.exists():
        return None
    payload = read_json(path, label="健康歷史")
    checks = payload.get("checks")
    if payload.get("schema_version") != 1 or not isinstance(checks, list):
        raise OperationsError("健康歷史格式不符")
    return checks[-1] if checks else None


def exact_dependency_pins(project: Path) -> dict[str, Any]:
    package = read_json(project / "package.json", label="package.json")
    direct: dict[str, str] = {}
    for section in ("dependencies", "devDependencies"):
        values = package.get(section, {})
        if not isinstance(values, dict):
            raise OperationsError(f"package.json 的 {section} 必須是 object")
        direct.update({str(name): str(version) for name, version in values.items()})
    loose = sorted(name for name, version in direct.items() if re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version) is None)
    return {"direct_count": len(direct), "all_exact": not loose, "non_exact": loose}


def list_backups(workspace: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = workspace / DEFAULT_BACKUP_DIR
    archives = sorted(root.glob("website-backup-*.zip"), key=lambda path: path.stat().st_mtime, reverse=True) if root.is_dir() else []
    latest = archives[0] if archives else None
    age_days = None
    stale = True
    if latest:
        age_days = round((time.time() - latest.stat().st_mtime) / 86400, 2)
        stale = age_days > config["backup"]["stale_after_days"]
    return {
        "count": len(archives),
        "latest": latest.name if latest else None,
        "latest_age_days": age_days,
        "stale": stale,
        "retention_exceeded": len(archives) > config["backup"]["retention_count"],
        "automatic_prune": False,
    }


def command_status(workspace: Path, project: Path) -> dict[str, Any]:
    config_path = workspace / OPERATIONS_CONFIG
    if not config_path.exists():
        return {
            "result": "not_configured",
            "config": OPERATIONS_CONFIG.as_posix(),
            "default": str(DEFAULT_CONFIG),
            "dependency_pins": exact_dependency_pins(project),
            "contains_credentials": False,
        }
    config = load_config(workspace)
    state_path = workspace / STATE_FILE
    state = read_json(state_path, label="維運狀態") if state_path.is_file() and not state_path.is_symlink() else None
    config_hash = sha256_bytes(canonical_json(config))
    return {
        "result": "configured" if state and state.get("config_sha256") == config_hash else "drifted",
        "public_url": config["public_url"],
        "health_enabled": config["health"]["enabled"],
        "latest_health": latest_health(workspace),
        "backups": list_backups(workspace, config),
        "dependency_pins": exact_dependency_pins(project),
        "state_matches": bool(state and state.get("config_sha256") == config_hash),
        "contains_credentials": False,
    }


def fetch_check(url: str, expected_status: int, required_text: str | None, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "ai-workflow-toolbox-website-operations/0.1"})
    started = time.monotonic()
    status = 0
    final_url = url
    body = b""
    error_text = None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            final_url = response.geturl()
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise OperationsError(f"健康檢查回應超過 {MAX_RESPONSE_BYTES} bytes：{url}")
    except urllib.error.HTTPError as error:
        status = error.code
        final_url = error.geturl()
        body = error.read(MAX_RESPONSE_BYTES + 1)
        error_text = f"HTTP {error.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        error_text = str(error)
    elapsed_ms = round((time.monotonic() - started) * 1000, 1)
    text = body.decode("utf-8", errors="replace")
    content_ok = required_text is None or required_text in text
    source_host = (urllib.parse.urlsplit(url).hostname or "").lower()
    final_host = (urllib.parse.urlsplit(final_url).hostname or "").lower()
    redirect_host_ok = source_host == final_host or source_host.removeprefix("www.") == final_host.removeprefix("www.")
    return {
        "url": url,
        "final_url": final_url,
        "status": status,
        "expected_status": expected_status,
        "status_ok": status == expected_status,
        "required_text_ok": content_ok,
        "redirect_host_ok": redirect_host_ok,
        "elapsed_ms": elapsed_ms,
        "error": error_text,
        "passed": status == expected_status and content_ok and redirect_host_ok,
    }


def tls_status(base_url: str, warning_days: int, timeout: int) -> dict[str, Any]:
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme != "https":
        return {"checked": False, "reason": "local_http_test", "passed": True}
    hostname = parsed.hostname
    if not hostname:
        raise OperationsError("公開網址缺少 hostname")
    port = parsed.port or 443
    context = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=hostname) as secure:
                certificate = secure.getpeercert()
    except (OSError, ssl.SSLError) as error:
        return {"checked": True, "passed": False, "error": str(error)}
    expires_raw = certificate.get("notAfter")
    if not isinstance(expires_raw, str):
        return {"checked": True, "passed": False, "error": "憑證缺少 notAfter"}
    expires_at = datetime.fromtimestamp(ssl.cert_time_to_seconds(expires_raw), tz=UTC)
    remaining = (expires_at - datetime.now(UTC)).total_seconds() / 86400
    return {
        "checked": True,
        "expires_at": expires_at.replace(microsecond=0).isoformat(),
        "remaining_days": round(remaining, 2),
        "warning_days": warning_days,
        "passed": remaining >= warning_days,
    }


def record_health(workspace: Path, result: dict[str, Any], limit: int) -> None:
    path = workspace / HEALTH_HISTORY
    if path.exists():
        payload = read_json(path, label="健康歷史")
        if payload.get("schema_version") != 1 or not isinstance(payload.get("checks"), list):
            raise OperationsError("健康歷史格式不符")
    else:
        payload = {"schema_version": 1, "checks": []}
    payload["checks"] = [*payload["checks"], result][-limit:]
    write_atomic(path, canonical_json(payload))


def command_check(workspace: Path, config: dict[str, Any], url_override: str | None, record: bool, confirmed: bool) -> dict[str, Any]:
    if not config["health"]["enabled"] and url_override is None:
        raise OperationsError("健康檢查尚未啟用，且未提供 --url 測試覆寫")
    base_url = validate_public_url(url_override or config["public_url"], allow_local=url_override is not None)
    checks = []
    for item in config["health"]["checks"]:
        checks.append(
            fetch_check(
                base_url + item["path"],
                item["expected_status"],
                item["required_text"],
                config["health"]["timeout_seconds"],
            )
        )
    tls = tls_status(base_url, config["health"]["tls_warning_days"], config["health"]["timeout_seconds"])
    result = {
        "result": "health_check",
        "checked_at": utc_now(),
        "base_url": base_url,
        "checks": checks,
        "tls": tls,
        "passed": all(item["passed"] for item in checks) and tls["passed"],
        "submitted_forms": False,
        "external_writes": [],
    }
    if record:
        if not confirmed:
            raise OperationsError("--record 需要 --confirm-write；健康檢查已完成但未寫入歷史")
        record_health(workspace, result, config["health"]["history_limit"])
        result["recorded_to"] = HEALTH_HISTORY.as_posix()
    elif confirmed:
        raise OperationsError("--confirm-write 只能與 --record 一起使用")
    return result


def is_secret_path(relative: PurePosixPath) -> bool:
    for part in relative.parts:
        lowered = part.lower()
        if lowered == ".env" or lowered.startswith(".env.") or lowered in SECRET_NAMES:
            return True
        if any(lowered.endswith(suffix) for suffix in SECRET_SUFFIXES):
            return True
        if SECRET_KEY.search(lowered):
            return True
    return False


def collect_backup_files(workspace: Path, project: Path, config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    records: list[dict[str, Any]] = []
    omitted: list[dict[str, str]] = []
    seen: set[str] = set()
    total = 0
    groups = (
        ("workspace", workspace, config["backup"]["workspace_paths"]),
        ("project", project, config["backup"]["project_paths"]),
    )
    for group, root, configured_paths in groups:
        for configured in configured_paths:
            validate_relative_path(configured, label="備份來源")
            source = root.joinpath(*PurePosixPath(configured).parts)
            checked_path(source)
            if not os.path.lexists(source):
                omitted.append({"path": f"{group}/{configured}", "reason": "missing"})
                continue
            candidates = [source]
            if source.is_dir() and not source.is_symlink():
                candidates = []
                for directory, dirs, files in os.walk(source, followlinks=False):
                    for name in dirs:
                        checked_path(Path(directory) / name)
                    dirs[:] = [name for name in dirs if name.lower() not in EXCLUDED_DIRS]
                    candidates.extend(Path(directory) / name for name in files)
                candidates.sort()
            for path in candidates:
                checked_path(path)
                relative = PurePosixPath(path.relative_to(root).as_posix())
                validate_relative_path(relative.as_posix(), label="備份來源")
                archive_path = f"payload/{group}/{relative.as_posix()}"
                if archive_path in seen:
                    continue
                if path.is_symlink():
                    raise OperationsError(f"備份來源含 symlink，停止避免逸出：{group}/{relative.as_posix()}")
                if not path.is_file():
                    continue
                if any(part.lower() in EXCLUDED_DIRS for part in relative.parts):
                    omitted.append({"path": f"{group}/{relative.as_posix()}", "reason": "excluded_directory"})
                    continue
                if is_secret_path(relative):
                    omitted.append({"path": f"{group}/{relative.as_posix()}", "reason": "secret_filename"})
                    continue
                size = path.stat().st_size
                if size > MAX_FILE_BYTES:
                    raise OperationsError(f"單一備份檔超過 {MAX_FILE_BYTES} bytes：{group}/{relative.as_posix()}")
                total += size
                if total > MAX_TOTAL_BYTES:
                    raise OperationsError(f"備份總量超過 {MAX_TOTAL_BYTES} bytes")
                records.append(
                    {
                        "source": path,
                        "archive_path": archive_path,
                        "sha256": sha256_file(path),
                        "size": size,
                    }
                )
                seen.add(archive_path)
    if not records:
        raise OperationsError("備份計畫沒有任何可備份檔案")
    return records, omitted


def backup_plan(workspace: Path, project: Path, config: dict[str, Any]) -> dict[str, Any]:
    records, omitted = collect_backup_files(workspace, project, config)
    digest_payload = {
        "workspace_root": str(workspace),
        "project_root": str(project),
        "config_sha256": sha256_bytes(canonical_json(config)),
        "files": [{key: item[key] for key in ("archive_path", "sha256", "size")} for item in records],
        "omitted": omitted,
    }
    return {
        "result": "backup_plan",
        "plan_sha256": sha256_bytes(canonical_json(digest_payload)),
        "file_count": len(records),
        "files": digest_payload["files"],
        "total_bytes": sum(item["size"] for item in records),
        "omitted": omitted,
        "destination": DEFAULT_BACKUP_DIR.as_posix(),
        "credential_handling": "secret_filenames_excluded_content_not_classified",
        "external_effects": [],
        "_records": records,
    }


def public_plan(plan: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in plan.items() if not key.startswith("_")}


def verify_archive(path: Path) -> dict[str, Any]:
    """驗證清單、雜湊與路徑，阻擋 zip-slip、重複路徑及 symlink。"""

    checked_path(path)
    if path.is_symlink() or not path.is_file():
        raise OperationsError(f"備份必須是一般 ZIP 檔：{path}")
    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len({name.casefold() for name in names}):
                raise OperationsError("備份含重複路徑")
            for info in infos:
                validate_relative_path(info.filename, label="備份含不安全路徑")
                pure = PurePosixPath(info.filename)
                if pure.is_absolute() or ".." in pure.parts or "\\" in info.filename:
                    raise OperationsError(f"備份含不安全路徑：{info.filename}")
                mode = (info.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    raise OperationsError(f"備份含 symlink：{info.filename}")
            if "backup-manifest.json" not in names:
                raise OperationsError("備份缺少 backup-manifest.json")
            info_by_name = {info.filename: info for info in infos}
            if info_by_name["backup-manifest.json"].file_size > 10 * 1024 * 1024:
                raise OperationsError("備份 manifest 過大")
            manifest = json.loads(archive.read("backup-manifest.json").decode("utf-8"))
            if not isinstance(manifest, dict) or manifest.get("schema_version") != 1 or manifest.get("format") != BACKUP_FORMAT or not isinstance(manifest.get("files"), list) or not manifest["files"]:
                raise OperationsError("備份 manifest 格式不符")
            expected_names = {"backup-manifest.json"}
            total_size = 0
            for record in manifest["files"]:
                if not isinstance(record, dict) or set(record) != {"archive_path", "sha256", "size"}:
                    raise OperationsError("備份 manifest 檔案欄位不符")
                name = record["archive_path"]
                pure = PurePosixPath(name) if isinstance(name, str) else PurePosixPath(".")
                if len(pure.parts) < 3 or pure.parts[0] != "payload" or pure.parts[1] not in {"workspace", "project"}:
                    raise OperationsError(f"備份 payload 路徑不符：{name}")
                if name in expected_names:
                    raise OperationsError(f"備份 manifest 含重複檔案：{name}")
                if not isinstance(record["size"], int) or not 0 <= record["size"] <= MAX_FILE_BYTES:
                    raise OperationsError(f"備份 manifest 的檔案大小不符：{name}")
                if not isinstance(record["sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) is None:
                    raise OperationsError(f"備份 manifest 的 SHA-256 不符：{name}")
                if name not in info_by_name or info_by_name[name].file_size != record["size"]:
                    raise OperationsError(f"備份 ZIP 與 manifest 大小不符：{name}")
                total_size += record["size"]
                if total_size > MAX_TOTAL_BYTES:
                    raise OperationsError("備份解壓總量超過上限")
                expected_names.add(name)
                content = archive.read(name)
                if len(content) != record["size"] or sha256_bytes(content) != record["sha256"]:
                    raise OperationsError(f"備份檔案驗證失敗：{name}")
            if set(names) != expected_names:
                raise OperationsError("備份內容與 manifest 清單不一致")
    except (zipfile.BadZipFile, KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OperationsError(f"備份 ZIP 無法驗證：{error}") from error
    return {
        "result": "backup_verified",
        "archive": path.name,
        "archive_sha256": sha256_file(path),
        "file_count": len(manifest["files"]),
        "created_at": manifest.get("created_at"),
        "credential_handling": "secret_filenames_excluded_content_not_classified",
    }


def command_backup(workspace: Path, project: Path, config: dict[str, Any], expected_plan: str, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise OperationsError("缺少 --confirm-write；未建立備份")
    plan = backup_plan(workspace, project, config)
    if plan["plan_sha256"] != expected_plan:
        raise OperationsError("plan 雜湊已失效；備份來源已變更，請重新 backup-plan")
    backup_root = workspace / DEFAULT_BACKUP_DIR
    checked_path(backup_root)
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = backup_root / f"website-backup-{stamp}-{expected_plan[:8]}.zip"
    if target.exists():
        raise OperationsError(f"備份目標已存在：{target.name}")
    temporary = target.with_suffix(".zip.tmp")
    records = plan["_records"]
    manifest = {
        "schema_version": 1,
        "format": BACKUP_FORMAT,
        "created_at": utc_now(),
        "config_sha256": sha256_bytes(canonical_json(config)),
        "files": [{key: item[key] for key in ("archive_path", "sha256", "size")} for item in records],
        "omitted": plan["omitted"],
        "credential_handling": "secret_filenames_excluded_content_not_classified",
    }
    created_temporary = False
    created_target = False
    try:
        with zipfile.ZipFile(temporary, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            created_temporary = True
            archive.writestr("backup-manifest.json", canonical_json(manifest))
            for item in records:
                archive.write(item["source"], item["archive_path"])
        os.replace(temporary, target)
        created_target = True
        verified = verify_archive(target)
    except (OSError, zipfile.BadZipFile, OperationsError) as error:
        if created_temporary and temporary.exists():
            temporary.unlink()
        if created_target and target.exists():
            target.unlink()
        if isinstance(error, OperationsError):
            raise OperationsError(f"備份建立後驗證失敗，已移除未完成檔案：{error}") from error
        raise OperationsError(f"備份建立失敗：{error}") from error
    return {
        "result": "backup_created",
        "archive": str(target),
        "archive_sha256": verified["archive_sha256"],
        "file_count": verified["file_count"],
        "verification": "passed",
        "retention_action": "none",
        "credential_handling": "secret_filenames_excluded_content_not_classified",
    }


def restore_plan(archive: Path, recovery: Path) -> dict[str, Any]:
    verified = verify_archive(archive)
    checked_path(recovery)
    if os.path.lexists(recovery):
        raise OperationsError("隔離復原目錄必須不存在")
    digest = sha256_bytes(
        canonical_json(
            {
                "archive_sha256": verified["archive_sha256"],
                "recovery": str(recovery.resolve(strict=False)),
                "target_exists": False,
            }
        )
    )
    return {
        "result": "restore_plan",
        "plan_sha256": digest,
        "archive": archive.name,
        "archive_sha256": verified["archive_sha256"],
        "file_count": verified["file_count"],
        "recovery_directory": str(recovery.resolve(strict=False)),
        "overwrites_existing": False,
        "external_effects": [],
    }


def command_restore(archive: Path, recovery: Path, expected_plan: str, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise OperationsError("缺少 --confirm-write；未建立隔離復原目錄")
    plan = restore_plan(archive, recovery)
    if plan["plan_sha256"] != expected_plan:
        raise OperationsError("plan 雜湊已失效；備份或復原目標已變更，請重新 restore-plan")
    created_recovery = False
    try:
        recovery.mkdir(parents=True, exist_ok=False)
        created_recovery = True
        with zipfile.ZipFile(archive, "r") as source:
            manifest = json.loads(source.read("backup-manifest.json").decode("utf-8"))
            for record in manifest["files"]:
                name = PurePosixPath(record["archive_path"])
                relative = PurePosixPath(*name.parts[1:])
                destination = recovery.joinpath(*relative.parts)
                if not destination.resolve().is_relative_to(recovery.resolve()):
                    raise OperationsError("復原路徑逸出隔離目錄")
                destination.parent.mkdir(parents=True, exist_ok=True)
                write_atomic(destination, source.read(record["archive_path"]))
        restored = []
        for record in manifest["files"]:
            name = PurePosixPath(record["archive_path"])
            destination = recovery.joinpath(*name.parts[1:])
            if sha256_file(destination) != record["sha256"]:
                raise OperationsError(f"隔離復原後雜湊不符：{destination}")
            restored.append(destination)
    except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError, OperationsError) as error:
        if created_recovery and recovery.is_dir() and checked_path(recovery) == recovery.resolve():
            shutil.rmtree(recovery)
        if isinstance(error, OperationsError):
            raise
        raise OperationsError(f"隔離復原失敗，已移除未完成目錄：{error}") from error
    return {
        "result": "restored_to_isolation",
        "recovery_directory": str(recovery.resolve()),
        "file_count": len(restored),
        "overwrote_existing": False,
        "next": ["比較 workspace/ 與 project/ 差異", "在隔離複本建置與檢查", "如需寫回或部署，另行規劃與授權"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    def roots(command: str) -> argparse.ArgumentParser:
        child = subparsers.add_parser(command)
        child.add_argument("--workspace-root", required=True)
        child.add_argument("--project", required=True)
        return child

    roots("status")
    plan = roots("configure-plan")
    plan.add_argument("--candidate", required=True)
    configure = roots("configure")
    configure.add_argument("--candidate", required=True)
    configure.add_argument("--expected-plan-sha256", required=True)
    configure.add_argument("--confirm-write", action="store_true")
    check = roots("check")
    check.add_argument("--url")
    check.add_argument("--record", action="store_true")
    check.add_argument("--confirm-write", action="store_true")
    roots("backup-plan")
    backup = roots("backup")
    backup.add_argument("--expected-plan-sha256", required=True)
    backup.add_argument("--confirm-write", action="store_true")

    verify = subparsers.add_parser("verify-backup")
    verify.add_argument("--archive", required=True)
    restore_preview = subparsers.add_parser("restore-plan")
    restore_preview.add_argument("--archive", required=True)
    restore_preview.add_argument("--recovery-dir", required=True)
    restore = subparsers.add_parser("restore")
    restore.add_argument("--archive", required=True)
    restore.add_argument("--recovery-dir", required=True)
    restore.add_argument("--expected-plan-sha256", required=True)
    restore.add_argument("--confirm-write", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command in {"verify-backup", "restore-plan", "restore"}:
            archive = checked_path(Path(args.archive))
            if args.command == "verify-backup":
                result = verify_archive(archive)
            else:
                recovery = checked_path(Path(args.recovery_dir))
                if args.command == "restore-plan":
                    result = restore_plan(archive, recovery)
                else:
                    result = command_restore(archive, recovery, args.expected_plan_sha256, args.confirm_write)
        else:
            workspace, project = validate_roots(args.workspace_root, args.project)
            if args.command == "status":
                result = command_status(workspace, project)
            elif args.command in {"configure-plan", "configure"}:
                candidate = validate_config(read_json(Path(args.candidate), label="候選維運設定"))
                if args.command == "configure-plan":
                    result = config_plan(workspace, candidate)
                else:
                    result = command_configure(workspace, candidate, args.expected_plan_sha256, args.confirm_write)
            else:
                config = load_config(workspace)
                if args.command == "check":
                    result = command_check(workspace, config, args.url, args.record, args.confirm_write)
                elif args.command == "backup-plan":
                    result = public_plan(backup_plan(workspace, project, config))
                else:
                    result = command_backup(workspace, project, config, args.expected_plan_sha256, args.confirm_write)
    except (OperationsError, OSError, ValueError) as error:
        print(json.dumps({"result": "error", "error": str(error), "external_state": "unchanged_or_unknown"}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.command == "check" and not result["passed"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
