#!/usr/bin/env python3
"""規劃、套用與驗證官網的 hosted service integrations。

只寫入公開設定與受管理的 Astro 元件，不保存憑證，也不送出表單、建立預約或付款。
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = SKILL_ROOT / "assets/default-integrations.json"
COMPONENT_SOURCE = SKILL_ROOT / "assets/ServiceIntegrations.astro"
WORKSPACE_CONFIG = Path("website/integrations.json")
STATE_FILE = Path(".local/website/integration-state.json")
PROJECT_CONFIG = Path("src/data/integrations.json")
PROJECT_COMPONENT = Path("src/components/ServiceIntegrations.astro")
CONTACT_PAGE = Path("src/pages/contact.astro")
NEWSLETTER_PAGE = Path("src/pages/newsletter.astro")
SERVICE_KEYS = ("contact_form", "newsletter", "booking", "payment")
HOSTED_KEYS = ("newsletter", "booking", "payment")
FORM_FIELDS = ["name", "email", "message"]
START_MARKER = "<!-- website-service-integration:start -->"
END_MARKER = "<!-- website-service-integration:end -->"
IMPORT_LINE = "import ServiceIntegrations from '../components/ServiceIntegrations.astro';"
SECRET_KEY = re.compile(
    r"(^|[_-])(token|secret|password|passwd|cookie|credential|api[_-]?key|access[_-]?key|client[_-]?id|account[_-]?id|webhook)([_-]|$)",
    re.IGNORECASE,
)
SECRET_VALUE = (
    re.compile(r"\b(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{12,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{12,}\b", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


class IntegrationError(RuntimeError):
    """表示應停止且不應繼續寫入或外部操作的錯誤。"""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def canonical_json(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def file_hash(path: Path) -> str | None:
    if not os.path.lexists(path):
        return None
    if path.is_symlink() or not path.is_file():
        raise IntegrationError(f"受管理路徑必須是一般檔案：{path}")
    return sha256_bytes(path.read_bytes())


def read_json(path: Path, *, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise IntegrationError(f"{label}必須是一般 JSON 檔案：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise IntegrationError(f"{label}不是有效 JSON：{error}") from error
    if not isinstance(payload, dict):
        raise IntegrationError(f"{label}根節點必須是 object")
    return payload


def exact_keys(value: Any, expected: set[str], *, path: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise IntegrationError(f"{path} 欄位不符；預期 {sorted(expected)}，實際 {actual}")
    return value


def reject_secret_material(value: Any, *, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if SECRET_KEY.search(str(key)):
                raise IntegrationError(f"{path}.{key} 看似秘密或私人識別碼，不得寫入整合設定")
            reject_secret_material(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_secret_material(child, path=f"{path}[{index}]")
    elif isinstance(value, str):
        if any(pattern.search(value) for pattern in SECRET_VALUE):
            raise IntegrationError(f"{path} 看似包含秘密，不得寫入整合設定")


def public_https_url(value: Any, *, path: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 1000:
        raise IntegrationError(f"{path} 必須是公開 HTTPS 網址")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise IntegrationError(f"{path} 必須是沒有帳密的 HTTPS 網址")
    hostname = parsed.hostname.lower()
    if hostname == "example.invalid" or hostname.endswith(".example.invalid"):
        raise IntegrationError(f"{path} 仍是 example.invalid")
    for key, _ in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        if SECRET_KEY.search(key):
            raise IntegrationError(f"{path} 的 query 參數 {key} 看似秘密；請改用正式 public URL")
    return value


def text_field(value: Any, *, path: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise IntegrationError(f"{path} 必須是 1–{maximum} 字元文字")
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise IntegrationError(f"{path} 含控制字元")
    return value


def validate_public_fields(service: dict[str, Any], *, path: str, enabled: bool, target_key: str) -> None:
    text_field(service["label"], path=f"{path}.label", maximum=100)
    if enabled:
        text_field(service["provider"], path=f"{path}.provider", maximum=100)
        public_https_url(service[target_key], path=f"{path}.{target_key}")
        public_https_url(service["privacy_url"], path=f"{path}.privacy_url")
    elif service["provider"] is not None or service[target_key] is not None or service["privacy_url"] is not None:
        raise IntegrationError(f"{path} 未啟用時 provider、{target_key} 與 privacy_url 必須為 null")


def validate_config(payload: dict[str, Any]) -> dict[str, Any]:
    """驗證設定與跨欄位契約，回傳原 payload 供呼叫端串接。"""

    reject_secret_material(payload)
    exact_keys(payload, {"schema_version", "status", "services", "disclosure"}, path="$")
    if payload["schema_version"] != 1:
        raise IntegrationError("schema_version 必須是 1")
    if payload["status"] not in {"not_configured", "configured"}:
        raise IntegrationError("status 必須是 not_configured 或 configured")
    services = exact_keys(payload["services"], set(SERVICE_KEYS), path="$.services")

    form = exact_keys(
        services["contact_form"],
        {"enabled", "provider", "mode", "endpoint", "label", "fields", "consent_required", "privacy_url"},
        path="$.services.contact_form",
    )
    if not isinstance(form["enabled"], bool) or form["mode"] != "html_post":
        raise IntegrationError("contact_form 必須使用 html_post 並明確設定 enabled")
    if form["fields"] != FORM_FIELDS or form["consent_required"] is not True:
        raise IntegrationError("contact_form 欄位固定為 name、email、message，且必須要求隱私同意")
    validate_public_fields(form, path="$.services.contact_form", enabled=form["enabled"], target_key="endpoint")

    for key in HOSTED_KEYS:
        expected = {"enabled", "provider", "mode", "url", "label", "privacy_url"}
        if key == "payment":
            expected.add("verification_scope")
        service = exact_keys(services[key], expected, path=f"$.services.{key}")
        if not isinstance(service["enabled"], bool) or service["mode"] != "hosted_link":
            raise IntegrationError(f"{key} 必須使用 hosted_link 並明確設定 enabled")
        if key == "payment" and service["verification_scope"] != "link_only_no_transaction":
            raise IntegrationError("付款驗證範圍固定為 link_only_no_transaction")
        validate_public_fields(service, path=f"$.services.{key}", enabled=service["enabled"], target_key="url")

    disclosure = exact_keys(payload["disclosure"], {"heading", "intro", "form_consent_label"}, path="$.disclosure")
    text_field(disclosure["heading"], path="$.disclosure.heading", maximum=100)
    text_field(disclosure["intro"], path="$.disclosure.intro", maximum=500)
    text_field(disclosure["form_consent_label"], path="$.disclosure.form_consent_label", maximum=300)
    enabled = [key for key in SERVICE_KEYS if services[key]["enabled"]]
    if payload["status"] == "not_configured" and enabled:
        raise IntegrationError("not_configured 不得啟用服務")
    if payload["status"] == "configured" and not enabled:
        raise IntegrationError("configured 至少要啟用一項服務")
    return payload


def validate_project(raw: str) -> Path:
    project = Path(raw).expanduser().resolve(strict=False)
    if not project.is_dir():
        raise IntegrationError(f"網站專案不存在：{project}")
    contact = project / CONTACT_PAGE
    if contact.is_symlink() or not contact.is_file():
        raise IntegrationError("網站專案缺少 src/pages/contact.astro")
    if not (project / "package.json").is_file():
        raise IntegrationError("網站專案缺少 package.json")
    return project


def validate_workspace(raw: str) -> Path:
    workspace = Path(raw).expanduser().resolve(strict=False)
    if not workspace.is_dir():
        raise IntegrationError(f"工作區不存在：{workspace}")
    config = workspace / "website/config.json"
    if config.is_symlink() or not config.is_file():
        raise IntegrationError("缺少 website/config.json；請先完成 website-setup")
    return workspace


def patch_page(text: str, *, newsletter_only: bool = False) -> str:
    """在已知 Astro 頁面加入受管理元件；標記損壞時停止。"""

    has_start = START_MARKER in text
    has_end = END_MARKER in text
    if has_start != has_end:
        raise IntegrationError("頁面的 website-service-integration 標記不完整；停止避免覆蓋人工修改")
    if has_start:
        if IMPORT_LINE not in text:
            raise IntegrationError("頁面已有整合標記但缺少元件 import")
        return text
    if "---" not in text or "</BaseLayout>" not in text:
        raise IntegrationError("頁面結構不是可管理的 Astro BaseLayout 頁面")
    first_close = text.find("---", 3)
    if first_close < 0:
        raise IntegrationError("Astro frontmatter 不完整")
    text = text[:first_close] + IMPORT_LINE + "\n" + text[first_close:]
    lines = []
    for line in text.splitlines():
        if "表單類整合屬第二版" in line or "實際訂閱表單屬第二版整合" in line:
            continue
        if "聯絡表單會在第二版加入" in line or "訂閱表單與電子報服務串接會在第二版加入" in line:
            continue
        lines.append(line)
    text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    invocation = "<ServiceIntegrations only={['newsletter']} />" if newsletter_only else "<ServiceIntegrations />"
    block = f"  {START_MARKER}\n  {invocation}\n  {END_MARKER}\n"
    return text.replace("</BaseLayout>", block + "</BaseLayout>", 1)


def expected_files(workspace: Path, project: Path, candidate: dict[str, Any]) -> dict[Path, bytes]:
    files = {
        workspace / WORKSPACE_CONFIG: canonical_json(candidate),
        project / PROJECT_CONFIG: canonical_json(candidate),
        project / PROJECT_COMPONENT: COMPONENT_SOURCE.read_bytes(),
    }
    contact = project / CONTACT_PAGE
    files[contact] = patch_page(contact.read_text(encoding="utf-8")).encode("utf-8")
    newsletter = project / NEWSLETTER_PAGE
    if newsletter.is_file() and not newsletter.is_symlink():
        files[newsletter] = patch_page(newsletter.read_text(encoding="utf-8"), newsletter_only=True).encode("utf-8")
    elif os.path.lexists(newsletter):
        raise IntegrationError("src/pages/newsletter.astro 必須是一般檔案")
    return files


def compute_plan(workspace: Path, project: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    files = expected_files(workspace, project, candidate)
    changes = []
    fingerprints: dict[str, str | None] = {}
    for path, content in files.items():
        current = file_hash(path)
        relative = str(path.relative_to(workspace if path.is_relative_to(workspace) else project)).replace("\\", "/")
        fingerprints[str(path)] = current
        changes.append({"path": relative, "change": "unchanged" if current == sha256_bytes(content) else ("create" if current is None else "update")})
    enabled = [key for key in SERVICE_KEYS if candidate["services"][key]["enabled"]]
    digest_payload = {
        "candidate_sha256": sha256_bytes(canonical_json(candidate)),
        "current": fingerprints,
        "component_sha256": sha256_bytes(COMPONENT_SOURCE.read_bytes()),
    }
    plan_sha = sha256_bytes(canonical_json(digest_payload))
    flows = []
    for key in enabled:
        service = candidate["services"][key]
        target = service.get("endpoint") or service.get("url")
        flows.append({"service": key, "provider": service["provider"], "target": target, "privacy_url": service["privacy_url"]})
    return {
        "result": "plan",
        "plan_sha256": plan_sha,
        "enabled_services": enabled,
        "changes": changes,
        "public_data_flows": flows,
        "external_effects": [],
        "requires_separate_deploy_authorization": True,
        "contains_credentials": False,
        "_files": files,
    }


def public_plan(plan: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in plan.items() if key != "_files"}


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-website-integration")
    temporary.write_bytes(content)
    os.replace(temporary, path)


def command_status(workspace: Path, project: Path) -> dict[str, Any]:
    config_path = workspace / WORKSPACE_CONFIG
    if not config_path.exists():
        return {"result": "not_configured", "config": str(config_path), "contains_credentials": False}
    config = validate_config(read_json(config_path, label="整合設定"))
    project_path = project / PROJECT_CONFIG
    state_path = workspace / STATE_FILE
    expected_hash = sha256_bytes(canonical_json(config))
    project_hash = file_hash(project_path)
    markers_ok = START_MARKER in (project / CONTACT_PAGE).read_text(encoding="utf-8") and END_MARKER in (project / CONTACT_PAGE).read_text(encoding="utf-8")
    state = read_json(state_path, label="整合狀態") if state_path.is_file() and not state_path.is_symlink() else None
    matches = project_hash == expected_hash and markers_ok and state is not None and state.get("config_sha256") == expected_hash
    return {
        "result": "applied" if matches else "drifted",
        "status": config["status"],
        "enabled_services": [key for key in SERVICE_KEYS if config["services"][key]["enabled"]],
        "project_config_matches": project_hash == expected_hash,
        "managed_markers_present": markers_ok,
        "state_matches": bool(state and state.get("config_sha256") == expected_hash),
        "contains_credentials": False,
    }


def command_apply(workspace: Path, project: Path, candidate: dict[str, Any], *, expected_plan: str, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise IntegrationError("缺少 --confirm-write；未修改任何檔案")
    plan = compute_plan(workspace, project, candidate)
    if expected_plan != plan["plan_sha256"]:
        raise IntegrationError("plan 雜湊已失效；候選設定或目標檔案已變更，請重新 plan")
    files: dict[Path, bytes] = plan["_files"]
    state_path = workspace / STATE_FILE
    backups = {path: (path.read_bytes() if path.is_file() and not path.is_symlink() else None) for path in [*files, state_path]}
    try:
        for path, content in files.items():
            write_atomic(path, content)
        state = {
            "schema_version": 1,
            "config_sha256": sha256_bytes(canonical_json(candidate)),
            "component_sha256": sha256_bytes(COMPONENT_SOURCE.read_bytes()),
            "applied_at": utc_now(),
            "contains_credentials": False,
        }
        write_atomic(state_path, canonical_json(state))
    except OSError as error:
        for path, previous in backups.items():
            try:
                if previous is None:
                    if path.exists() and path.is_file() and not path.is_symlink():
                        path.unlink()
                else:
                    write_atomic(path, previous)
            except OSError:
                pass
        raise IntegrationError(f"整合寫入失敗，已嘗試回復：{error}") from error
    return {
        "result": "applied",
        "enabled_services": plan["enabled_services"],
        "config_sha256": sha256_bytes(canonical_json(candidate)),
        "next": ["npm run build", "manage_integrations.py verify --workspace-root <工作區> --project <網站專案>", "如網站已上線，交給 website-deploy 預覽並授權重新部署"],
        "contains_credentials": False,
    }


def expected_public_values(config: dict[str, Any]) -> list[str]:
    values = [config["disclosure"]["heading"], config["disclosure"]["intro"]]
    for key in SERVICE_KEYS:
        service = config["services"][key]
        if service["enabled"]:
            values.extend([service["provider"], service["privacy_url"], service.get("endpoint") or service.get("url")])
    return [value for value in values if isinstance(value, str)]


def verify_html(document: str, config: dict[str, Any]) -> list[dict[str, str]]:
    decoded = html.unescape(document)
    findings = []
    for value in expected_public_values(config):
        if value not in decoded:
            findings.append({"kind": "missing_public_value", "detail": value})
    if config["services"]["contact_form"]["enabled"]:
        for field in (*FORM_FIELDS, "privacy_consent"):
            if not re.search(rf'name=["\']{re.escape(field)}["\']', decoded):
                findings.append({"kind": "missing_form_field", "detail": field})
        if 'method="post"' not in decoded.lower() and "method='post'" not in decoded.lower():
            findings.append({"kind": "missing_post_method", "detail": "contact_form"})
    return findings


def fetch(url: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "ai-workflow-toolbox-service-integration/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, ""
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise IntegrationError(f"無法讀回 {url}：{error}") from error


def validate_readback_base(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    local = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    if not ((parsed.scheme == "https" and parsed.hostname) or local) or parsed.username or parsed.password:
        raise IntegrationError("公開讀回只接受 HTTPS；本機測試允許 localhost／127.0.0.1")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise IntegrationError("公開讀回網址只能包含 origin，不得帶路徑、query 或 fragment")
    return url.rstrip("/")


def command_verify(workspace: Path, project: Path, url: str | None) -> dict[str, Any]:
    config_path = workspace / WORKSPACE_CONFIG
    config = validate_config(read_json(config_path, label="整合設定"))
    findings: list[dict[str, str]] = []
    project_config = project / PROJECT_CONFIG
    if file_hash(project_config) != sha256_bytes(canonical_json(config)):
        findings.append({"kind": "project_config_drift", "detail": str(PROJECT_CONFIG)})
    contact_source = (project / CONTACT_PAGE).read_text(encoding="utf-8")
    if START_MARKER not in contact_source or END_MARKER not in contact_source or IMPORT_LINE not in contact_source:
        findings.append({"kind": "managed_block_missing", "detail": str(CONTACT_PAGE)})
    dist_contact = project / "dist/contact/index.html"
    if not dist_contact.is_file():
        findings.append({"kind": "dist_missing", "detail": "請先執行 npm run build"})
    else:
        newest_source = max(
            (project / PROJECT_CONFIG).stat().st_mtime,
            (project / PROJECT_COMPONENT).stat().st_mtime if (project / PROJECT_COMPONENT).is_file() else 0,
            (project / CONTACT_PAGE).stat().st_mtime,
        )
        if dist_contact.stat().st_mtime < newest_source:
            findings.append({"kind": "dist_stale", "detail": "dist/contact/index.html 比整合來源舊"})
        findings.extend(verify_html(dist_contact.read_text(encoding="utf-8"), config))
    public = None
    if url:
        base = validate_readback_base(url)
        status, document = fetch(base + "/contact/")
        public_findings = [] if status == 200 else [{"kind": "unexpected_status", "detail": f"/contact/ -> {status}"}]
        if status == 200:
            public_findings.extend(verify_html(document, config))
        findings.extend({"kind": "public_" + item["kind"], "detail": item["detail"]} for item in public_findings)
        public = {"url": base, "contact_status": status, "verified": not public_findings}
    return {
        "result": "verified" if not findings else "failed",
        "enabled_services": [key for key in SERVICE_KEYS if config["services"][key]["enabled"]],
        "local_build_verified": not any(not item["kind"].startswith("public_") for item in findings),
        "public_readback": public,
        "findings": findings,
        "not_covered": ["external_hosted_page_content", "form_delivery", "newsletter_subscription", "booking_creation", "payment_or_settlement"],
        "verified_at": utc_now(),
        "contains_credentials": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="管理官網表單、電子報、預約與 hosted payment links")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "plan", "apply", "verify"):
        child = sub.add_parser(name)
        child.add_argument("--workspace-root", required=True)
        child.add_argument("--project", required=True)
        if name in {"plan", "apply"}:
            child.add_argument("--candidate", default=str(DEFAULT_CONFIG))
        if name == "apply":
            child.add_argument("--expected-plan-sha256", required=True)
            child.add_argument("--confirm-write", action="store_true")
        if name == "verify":
            child.add_argument("--url", default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        workspace = validate_workspace(args.workspace_root)
        project = validate_project(args.project)
        if args.command == "status":
            result = command_status(workspace, project)
        elif args.command == "plan":
            candidate = validate_config(read_json(Path(args.candidate).expanduser(), label="候選整合設定"))
            result = public_plan(compute_plan(workspace, project, candidate))
        elif args.command == "apply":
            candidate = validate_config(read_json(Path(args.candidate).expanduser(), label="候選整合設定"))
            result = command_apply(workspace, project, candidate, expected_plan=args.expected_plan_sha256, confirmed=args.confirm_write)
        elif args.command == "verify":
            result = command_verify(workspace, project, args.url)
        else:
            raise IntegrationError("未知命令")
    except (IntegrationError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"result": "stopped", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("result") not in {"failed", "drifted"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
