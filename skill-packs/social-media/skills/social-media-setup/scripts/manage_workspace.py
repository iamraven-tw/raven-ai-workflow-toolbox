#!/usr/bin/env python3
"""預覽並安全寫入不含憑證的社群媒體一般設定。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = SKILL_ROOT / "assets" / "default-config.json"
CONFIG_RELATIVE = Path("social-media/config.json")
STATE_RELATIVE = Path(".local/social-media/setup-state.json")
PLATFORMS = ("youtube", "instagram", "facebook", "threads", "substack")
CAPABILITIES = {
    "account_read",
    "publish",
    "public_comments",
    "analytics",
    "direct_messages",
}
AUTHORIZATION_PROFILES = {"not_selected", "full_management", "custom"}
INTERFACES = {
    "not_selected",
    "official_api",
    "official_connector",
    "reliable_cli",
    "controlled_browser",
    "computer_use",
    "manual",
}
INTEGRATION_STATUSES = {
    "not_configured",
    "planned",
    "requires_user_action",
    "locally_prepared",
    "partially_verified",
    "verified",
}
API_APP_STATUSES = {
    "not_applicable",
    "not_started",
    "planned",
    "requires_user_action",
    "configured",
    "verified",
    "failed",
    "unknown",
}
USER_AUTH_STATUSES = {
    "not_applicable",
    "not_started",
    "planned",
    "requires_user_action",
    "verified",
    "failed",
    "unknown",
}
PLATFORM_READ_STATUSES = {
    "not_started",
    "planned",
    "requires_user_action",
    "verified",
    "empty",
    "permission_denied",
    "failed",
    "unknown",
}
REMOTE_WRITE_STATUSES = {
    "not_requested",
    "not_authorized",
    "not_tested",
    "requires_user_action",
    "verified",
    "failed",
    "unknown",
}
SECRET_KEY_FRAGMENTS = {
    "token",
    "secret",
    "password",
    "cookie",
    "credential",
    "apikey",
    "accesskey",
    "clientid",
    "appid",
    "pageid",
    "accountid",
    "channelid",
}
SECRET_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bBearer\s+\S+", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(
        r"https?://[^\s]+[?&](?:token|api[_-]?key|auth|code|secret)=[^&\s]+",
        re.IGNORECASE,
    ),
)


class ConfigurationError(RuntimeError):
    """表示必須停止且不應寫入正式設定的錯誤。"""


def utc_now() -> str:
    """回傳秒級 UTC ISO 時間。"""

    return datetime.now(UTC).replace(microsecond=0).isoformat()


def sha256_bytes(content: bytes) -> str:
    """計算位元組內容的 SHA-256。"""

    return hashlib.sha256(content).hexdigest()


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    """建立可重現且適合使用者檢視的 JSON。"""

    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return text.encode("utf-8")


def read_json_file(file_path: Path, *, label: str) -> dict[str, Any]:
    """讀取一般 JSON 檔，拒絕 symlink 與非物件根節點。"""

    if file_path.is_symlink() or not file_path.is_file():
        raise ConfigurationError(f"{label} 必須是一般檔案：{file_path}")
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ConfigurationError(f"無法讀取 {label}：{error}") from error
    if not isinstance(payload, dict):
        raise ConfigurationError(f"{label} 根節點必須是 JSON object")
    return payload


def validate_workspace_root(raw_path: str) -> Path:
    """確認工作區是明確且不過度寬廣的路徑。"""

    supplied = Path(raw_path).expanduser()
    if supplied.is_symlink():
        raise ConfigurationError("工作區根目錄不得是 symlink")
    resolved = supplied.resolve(strict=False)
    if resolved == Path(resolved.anchor):
        raise ConfigurationError("工作區不得是檔案系統根目錄")
    if resolved == SKILL_ROOT or resolved.is_relative_to(SKILL_ROOT):
        raise ConfigurationError("工作區不得位於已安裝技能目錄內")
    return resolved


def validate_target_path(workspace_root: Path, relative: Path, *, label: str) -> Path:
    """拒絕固定目標路徑中的 symlink 與檔案類型衝突。"""

    target = workspace_root / relative
    current = workspace_root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ConfigurationError(f"{label} 的父路徑不得是 symlink：{current}")
        if current.exists() and not current.is_dir():
            raise ConfigurationError(f"{label} 的父路徑存在檔案類型衝突：{current}")
    if target.is_symlink():
        raise ConfigurationError(f"{label} 不得是 symlink：{target}")
    if target.exists() and not target.is_file():
        raise ConfigurationError(f"{label} 存在檔案類型衝突：{target}")
    return target


def require_exact_keys(payload: dict[str, Any], expected: set[str], *, path: str) -> None:
    """要求物件欄位完整且沒有未定義欄位。"""

    actual = set(payload)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ConfigurationError(f"{path} 欄位不符；缺少={missing}，多出={extra}")


def validate_optional_text(value: Any, *, path: str, maximum: int) -> None:
    """驗證可為 null 的短文字。"""

    if value is None:
        return
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ConfigurationError(f"{path} 必須是 1 至 {maximum} 字元的文字或 null")
    if any(ord(character) < 32 and character not in "\n\t" for character in value):
        raise ConfigurationError(f"{path} 含不允許的控制字元")


def validate_permission_list(value: Any, *, path: str) -> list[str]:
    """驗證不含秘密的 OAuth permission／scope 名稱清單。"""

    if not isinstance(value, list) or len(value) > 100:
        raise ConfigurationError(f"{path} 必須是最多 100 個不重複文字")
    for index, permission in enumerate(value):
        if (
            not isinstance(permission, str)
            or permission != permission.strip()
            or not permission
            or len(permission) > 300
            or any(ord(character) < 32 for character in permission)
        ):
            raise ConfigurationError(f"{path}[{index}] 必須是 1 至 300 字元的 permission 名稱")
    if len(value) != len(set(value)):
        raise ConfigurationError(f"{path} 必須是不重複清單")
    return value


def validate_timestamp(value: Any, *, path: str) -> None:
    """驗證可為 null 且帶時區的 ISO 日期時間。"""

    if value is None:
        return
    if not isinstance(value, str):
        raise ConfigurationError(f"{path} 必須是 ISO 日期時間或 null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ConfigurationError(f"{path} 不是有效 ISO 日期時間") from error
    if parsed.tzinfo is None:
        raise ConfigurationError(f"{path} 必須包含時區")


def reject_secret_material(value: Any, *, path: str = "$") -> None:
    """遞迴拒絕秘密欄位與常見秘密內容形狀。"""

    if isinstance(value, dict):
        for raw_key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(raw_key).lower())
            if any(fragment in normalized for fragment in SECRET_KEY_FRAGMENTS):
                raise ConfigurationError(f"一般設定不得包含秘密或私人識別欄位：{path}.{raw_key}")
            reject_secret_material(child, path=f"{path}.{raw_key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_secret_material(child, path=f"{path}[{index}]")
    elif isinstance(value, str):
        if any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS):
            raise ConfigurationError(f"一般設定疑似含有秘密內容：{path}")


def validate_configuration(payload: dict[str, Any]) -> None:
    """以不需第三方套件的方式執行完整設定契約。"""

    reject_secret_material(payload)
    # 舊版唯讀相容；只有明確預覽／確認的新候選才升級，不暗中改設定。
    version = payload.get("schema_version")
    if type(version) is not int or version not in {3, 4, 5}:
        raise ConfigurationError("schema_version 必須是 3、4 或 5")
    keys = {"schema_version", "strategy", "integrations"}
    if version >= 4:
        keys.add("image_production")
    if version == 5:
        keys.add("brand_visual")
    require_exact_keys(payload, keys, path="$")
    if version >= 4:
        image = payload["image_production"]
        if not isinstance(image, dict):
            raise ConfigurationError("image_production 必須是 object")
        require_exact_keys(image, {"default_method", "information_dense_method", "web_provider", "icon_source"}, path="$.image_production")
        if image["default_method"] not in ("not_configured", "codex", "antigravity", "web", "html_css"):
            raise ConfigurationError("image_production.default_method 不支援")
        if image["information_dense_method"] not in ("inherit", "html_css"):
            raise ConfigurationError("image_production.information_dense_method 不支援")
        if image["icon_source"] not in ("heroicons", "none"):
            raise ConfigurationError("image_production.icon_source 不支援")
        validate_optional_text(image["web_provider"], path="image_production.web_provider", maximum=100)

    if version == 5:
        brand = payload["brand_visual"]
        if not isinstance(brand, dict):
            raise ConfigurationError("brand_visual 必須是 object")
        colors = {"primary_color", "secondary_color", "background_color", "text_color"}
        refs = {"logo_ref", "main_visual_ref"}
        require_exact_keys(brand, colors | refs | {"status", "font_family", "style_notes"}, path="brand_visual")
        if brand["status"] not in ("not_configured", "confirmed"):
            raise ConfigurationError("品牌視覺狀態不支援")
        for field in colors:
            if brand[field] is not None and (not isinstance(brand[field], str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", brand[field])):
                raise ConfigurationError("品牌顏色必須是六位 HEX 或 null")
        validate_optional_text(brand["font_family"], path="brand_visual.font_family", maximum=100)
        validate_optional_text(brand["style_notes"], path="brand_visual.style_notes", maximum=1000)
        for field in refs:
            value = brand[field]
            validate_optional_text(value, path=f"brand_visual.{field}", maximum=300)
            if value is not None and (value.startswith(("/", "~")) or "\\" in value or ":" in value or ".." in PurePosixPath(value).parts or PurePosixPath(value) == PurePosixPath(".")):
                raise ConfigurationError("品牌素材只接受工作區相對路徑")
        # 尚未確認的推測只留在當次簡報，不冒充已保存品牌。
        populated = any(value is not None for key, value in brand.items() if key != "status")
        if populated != (brand["status"] == "confirmed"):
            raise ConfigurationError("品牌確認狀態必須與設定內容一致")

    strategy = payload["strategy"]
    if not isinstance(strategy, dict):
        raise ConfigurationError("strategy 必須是 object")
    strategy_keys = {
        "status",
        "primary_goal",
        "audience_summary",
        "content_pillars",
        "platform_roles",
        "strategy_source",
    }
    require_exact_keys(strategy, strategy_keys, path="$.strategy")
    if strategy["status"] not in {"not_configured", "partial", "configured"}:
        raise ConfigurationError("strategy.status 不支援")
    validate_optional_text(strategy["primary_goal"], path="strategy.primary_goal", maximum=500)
    validate_optional_text(strategy["audience_summary"], path="strategy.audience_summary", maximum=1000)

    pillars = strategy["content_pillars"]
    if not isinstance(pillars, list) or len(pillars) > 20:
        raise ConfigurationError("strategy.content_pillars 必須是最多 20 個不重複文字")
    for index, pillar in enumerate(pillars):
        validate_optional_text(pillar, path=f"strategy.content_pillars[{index}]", maximum=200)
    if len(pillars) != len(set(pillars)):
        raise ConfigurationError("strategy.content_pillars 必須是最多 20 個不重複文字")

    roles = strategy["platform_roles"]
    if not isinstance(roles, dict):
        raise ConfigurationError("strategy.platform_roles 必須是 object")
    require_exact_keys(roles, set(PLATFORMS), path="$.strategy.platform_roles")
    for platform in PLATFORMS:
        validate_optional_text(roles[platform], path=f"strategy.platform_roles.{platform}", maximum=500)

    source = strategy["strategy_source"]
    if not isinstance(source, str) or not source or "\\" in source:
        raise ConfigurationError("strategy.strategy_source 必須是工作區相對 POSIX 路徑")
    source_path = PurePosixPath(source)
    if source_path.is_absolute() or ".." in source_path.parts or source_path == PurePosixPath("."):
        raise ConfigurationError("strategy.strategy_source 不得是絕對路徑、空路徑或跳出工作區")
    if source_path.suffix.lower() != ".md":
        raise ConfigurationError("strategy.strategy_source 必須指向 Markdown 檔")

    if strategy["status"] == "not_configured":
        has_strategy = bool(
            strategy["primary_goal"]
            or strategy["audience_summary"]
            or pillars
            or any(roles.values())
        )
        if has_strategy:
            raise ConfigurationError("not_configured 策略不得同時帶有策略內容")

    integrations = payload["integrations"]
    if not isinstance(integrations, dict):
        raise ConfigurationError("integrations 必須是 object")
    require_exact_keys(integrations, set(PLATFORMS), path="$.integrations")
    integration_keys = {
        "selected",
        "requested_capabilities",
        "authorization_profile",
        "requested_permissions",
        "declined_permissions",
        "preferred_interface",
        "status",
        "verification",
        "last_verified_at",
    }
    for platform in PLATFORMS:
        record = integrations[platform]
        if not isinstance(record, dict):
            raise ConfigurationError(f"integrations.{platform} 必須是 object")
        require_exact_keys(record, integration_keys, path=f"$.integrations.{platform}")
        if not isinstance(record["selected"], bool):
            raise ConfigurationError(f"integrations.{platform}.selected 必須是 boolean")
        capabilities = record["requested_capabilities"]
        if not isinstance(capabilities, list):
            raise ConfigurationError(f"integrations.{platform}.requested_capabilities 不支援")
        if any(not isinstance(item, str) or item not in CAPABILITIES for item in capabilities):
            raise ConfigurationError(f"integrations.{platform}.requested_capabilities 不支援")
        if len(capabilities) != len(set(capabilities)):
            raise ConfigurationError(f"integrations.{platform}.requested_capabilities 不支援")
        authorization_profile = record["authorization_profile"]
        if authorization_profile not in AUTHORIZATION_PROFILES:
            raise ConfigurationError(f"integrations.{platform}.authorization_profile 不支援")
        requested_permissions = validate_permission_list(
            record["requested_permissions"],
            path=f"integrations.{platform}.requested_permissions",
        )
        declined_permissions = validate_permission_list(
            record["declined_permissions"],
            path=f"integrations.{platform}.declined_permissions",
        )
        overlap = sorted(set(requested_permissions) & set(declined_permissions))
        if overlap:
            raise ConfigurationError(
                f"integrations.{platform} 同一 permission 不得同時要求與拒絕：{overlap}"
            )
        if record["preferred_interface"] not in INTERFACES:
            raise ConfigurationError(f"integrations.{platform}.preferred_interface 不支援")
        if record["status"] not in INTEGRATION_STATUSES:
            raise ConfigurationError(f"integrations.{platform}.status 不支援")
        verification = record["verification"]
        if not isinstance(verification, dict):
            raise ConfigurationError(f"integrations.{platform}.verification 必須是 object")
        require_exact_keys(
            verification,
            {"api_app", "user_auth", "platform_read", "remote_write"},
            path=f"$.integrations.{platform}.verification",
        )
        if verification["api_app"] not in API_APP_STATUSES:
            raise ConfigurationError(f"integrations.{platform}.verification.api_app 不支援")
        if verification["user_auth"] not in USER_AUTH_STATUSES:
            raise ConfigurationError(f"integrations.{platform}.verification.user_auth 不支援")
        if verification["platform_read"] not in PLATFORM_READ_STATUSES:
            raise ConfigurationError(f"integrations.{platform}.verification.platform_read 不支援")
        if verification["remote_write"] not in REMOTE_WRITE_STATUSES:
            raise ConfigurationError(f"integrations.{platform}.verification.remote_write 不支援")
        validate_timestamp(record["last_verified_at"], path=f"integrations.{platform}.last_verified_at")
        if not record["selected"]:
            expected_unselected = not capabilities and record["preferred_interface"] == "not_selected"
            expected_unselected = expected_unselected and authorization_profile == "not_selected"
            expected_unselected = expected_unselected and not requested_permissions
            expected_unselected = expected_unselected and not declined_permissions
            expected_unselected = expected_unselected and record["status"] == "not_configured"
            expected_unselected = expected_unselected and record["last_verified_at"] is None
            expected_unselected = expected_unselected and verification == {
                "api_app": "not_started",
                "user_auth": "not_started",
                "platform_read": "not_started",
                "remote_write": "not_requested",
            }
            if not expected_unselected:
                raise ConfigurationError(f"未選取的 {platform} 不得帶有整合設定")
        elif not capabilities:
            raise ConfigurationError(f"已選取的 {platform} 至少需要一項功能")
        elif authorization_profile == "not_selected":
            raise ConfigurationError(f"已選取的 {platform} 必須指定授權模式")
        elif record["status"] == "not_configured":
            raise ConfigurationError(f"已選取的 {platform} 狀態至少必須是 planned")
        read_verified = verification["platform_read"] == "verified"
        write_verified = verification["remote_write"] == "verified"
        if record["status"] == "verified" and not read_verified:
            raise ConfigurationError(f"verified 的 {platform} 缺少平台讀取證據")
        if read_verified and record["status"] != "verified":
            raise ConfigurationError(f"{platform} 已有平台讀取證據但摘要狀態不是 verified")
        if read_verified and verification["user_auth"] not in {"verified", "not_applicable"}:
            raise ConfigurationError(f"{platform} 平台讀取驗證缺少使用者授權證據")
        if verification["user_auth"] == "verified" and verification["api_app"] not in {
            "configured",
            "verified",
            "not_applicable",
        }:
            raise ConfigurationError(f"{platform} 使用者授權缺少 API／App 準備證據")
        if write_verified and not read_verified:
            raise ConfigurationError(f"{platform} 遠端寫入驗證缺少平台讀取證據")
        if read_verified or write_verified:
            if record["last_verified_at"] is None or record["preferred_interface"] == "not_selected":
                raise ConfigurationError(f"verified 的 {platform} 缺少介面或驗證時間")
        elif record["last_verified_at"] is not None:
            raise ConfigurationError(f"未完成平台讀取的 {platform} 不得填入驗證時間")
        if record["status"] == "partially_verified":
            partial_evidence = verification["api_app"] == "verified" or verification["user_auth"] == "verified"
            if not partial_evidence or read_verified:
                raise ConfigurationError(f"partially_verified 的 {platform} 證據層級不符")

    selected = [name for name in PLATFORMS if integrations[name]["selected"]]
    if strategy["status"] == "configured":
        if not strategy["primary_goal"] or not strategy["audience_summary"] or not pillars:
            raise ConfigurationError("configured 策略必須有目標、受眾與至少一個內容主題")
        missing_roles = [name for name in selected if not roles[name]]
        if missing_roles:
            raise ConfigurationError("configured 策略缺少已選平台角色：" + ", ".join(missing_roles))


def flatten(payload: Any, *, prefix: str = "$") -> dict[str, Any]:
    """將 JSON 展平成欄位路徑，供預覽顯示差異。"""

    if isinstance(payload, dict):
        result: dict[str, Any] = {}
        for key in sorted(payload):
            result.update(flatten(payload[key], prefix=f"{prefix}.{key}"))
        return result
    return {prefix: payload}


def differences(current: dict[str, Any] | None, candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """列出候選設定相對於目前正式設定的欄位差異。"""

    before = flatten(current) if current is not None else {}
    after = flatten(candidate)
    missing = "<missing>"
    return [
        {"path": path, "before": before.get(path, missing), "after": after.get(path, missing)}
        for path in sorted(set(before) | set(after))
        if before.get(path, missing) != after.get(path, missing)
    ]


def build_preview(workspace_root: Path, candidate_path: Path) -> dict[str, Any]:
    """建立綁定候選、目前設定與工作區的唯讀預覽。"""

    candidate = read_json_file(candidate_path.expanduser().resolve(strict=True), label="候選設定")
    validate_configuration(candidate)
    candidate_content = canonical_bytes(candidate)
    config_path = validate_target_path(
        workspace_root, CONFIG_RELATIVE, label="正式設定目標"
    )
    current: dict[str, Any] | None = None
    current_digest: str | None = None
    if os.path.lexists(config_path):
        current = read_json_file(config_path, label="既有正式設定")
        validate_configuration(current)
        current_digest = sha256_bytes(config_path.read_bytes())

    binding = {
        "candidate_sha256": sha256_bytes(candidate_content),
        "current_config_sha256": current_digest,
        "workspace_root": str(workspace_root),
        "config_target": CONFIG_RELATIVE.as_posix(),
    }
    preview_digest = sha256_bytes(
        json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return {
        "result": "preview",
        "workspace_root": str(workspace_root),
        "config_target": CONFIG_RELATIVE.as_posix(),
        "state_target": STATE_RELATIVE.as_posix(),
        "current_config_sha256": current_digest,
        "candidate_sha256": binding["candidate_sha256"],
        "preview_sha256": preview_digest,
        "changes": differences(current, candidate),
        "candidate": candidate,
        "contains_credentials": False,
    }


def write_bytes_atomic(file_path: Path, content: bytes) -> None:
    """在相同檔案系統完成寫入後再原子替換。"""

    file_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{file_path.name}.", dir=file_path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, file_path)
    finally:
        if temporary.exists():
            temporary.unlink()


def restore_config(config_path: Path, previous: bytes | None) -> None:
    """狀態寫入失敗時回復正式設定。"""

    if previous is None:
        if config_path.exists() and not config_path.is_symlink():
            config_path.unlink()
        return
    write_bytes_atomic(config_path, previous)


def apply_configuration(
    workspace_root: Path,
    candidate_path: Path,
    expected_preview: str,
    *,
    confirmed: bool,
) -> dict[str, Any]:
    """核對預覽後原子寫入正式設定與非敏感狀態。"""

    if not confirmed:
        raise ConfigurationError("缺少 --confirm-write；未寫入任何設定")
    preview = build_preview(workspace_root, candidate_path)
    if not re.fullmatch(r"[0-9a-f]{64}", expected_preview or ""):
        raise ConfigurationError("expected preview SHA-256 格式不正確")
    if preview["preview_sha256"] != expected_preview:
        raise ConfigurationError("預覽已失效：候選、既有設定或目標工作區已變動")

    candidate = preview["candidate"]
    content = canonical_bytes(candidate)
    config_path = validate_target_path(
        workspace_root, CONFIG_RELATIVE, label="正式設定目標"
    )
    state_path = validate_target_path(
        workspace_root, STATE_RELATIVE, label="設定狀態目標"
    )

    previous_config = config_path.read_bytes() if config_path.exists() else None
    previous_state = state_path.read_bytes() if state_path.exists() else None
    config_changed = previous_config != content
    state = {
        "schema_version": 1,
        "config_sha256": sha256_bytes(content),
        "applied_at": utc_now(),
        "contains_credentials": False,
    }
    try:
        if config_changed:
            write_bytes_atomic(config_path, content)
        write_bytes_atomic(state_path, canonical_bytes(state))
    except Exception as error:
        try:
            restore_config(config_path, previous_config)
            restore_config(state_path, previous_state)
        except Exception as restore_error:
            raise ConfigurationError(
                f"寫入失敗且自動回復不完整，請保留現況人工檢查：{restore_error}"
            ) from error
        raise ConfigurationError(f"寫入失敗，已回復本次變更：{error}") from error

    reread = read_json_file(config_path, label="寫入後正式設定")
    validate_configuration(reread)
    reread_digest = sha256_bytes(config_path.read_bytes())
    if reread_digest != state["config_sha256"]:
        raise ConfigurationError("寫入後設定雜湊不符")
    return {
        "result": "configured" if config_changed else "state_reconciled",
        "config_target": str(config_path),
        "state_target": str(state_path),
        "config_sha256": reread_digest,
        "readback": "hashes_match",
        "contains_credentials": False,
    }


def workspace_status(workspace_root: Path) -> dict[str, Any]:
    """唯讀檢查正式設定與非敏感狀態是否一致。"""

    config_path = validate_target_path(
        workspace_root, CONFIG_RELATIVE, label="正式設定目標"
    )
    state_path = validate_target_path(
        workspace_root, STATE_RELATIVE, label="設定狀態目標"
    )
    if not os.path.lexists(config_path):
        return {
            "result": "missing",
            "config_target": str(config_path),
            "state_target": str(state_path),
        }
    config = read_json_file(config_path, label="正式設定")
    validate_configuration(config)
    config_digest = sha256_bytes(config_path.read_bytes())
    if not os.path.lexists(state_path):
        return {
            "result": "configured_without_state",
            "config_sha256": config_digest,
            "contains_credentials": False,
        }
    state = read_json_file(state_path, label="設定狀態")
    require_exact_keys(
        state,
        {"schema_version", "config_sha256", "applied_at", "contains_credentials"},
        path="$.state",
    )
    validate_timestamp(state["applied_at"], path="state.applied_at")
    if state["schema_version"] != 1 or state["contains_credentials"] is not False:
        raise ConfigurationError("設定狀態版本或憑證聲明不符")
    if not isinstance(state["config_sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", state["config_sha256"]
    ):
        raise ConfigurationError("設定狀態缺少有效 config_sha256")
    if state["config_sha256"] != config_digest:
        return {
            "result": "changed_after_apply",
            "config_sha256": config_digest,
            "state_config_sha256": state["config_sha256"],
            "contains_credentials": False,
        }
    return {
        "result": "configured",
        "config_sha256": config_digest,
        "verification": "hashes_match",
        "contains_credentials": False,
    }


def build_parser() -> argparse.ArgumentParser:
    """建立命令列介面。"""

    parser = argparse.ArgumentParser(description="安全管理社群媒體一般設定")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--workspace-root", required=True)

    preview_parser = subparsers.add_parser("preview")
    preview_parser.add_argument("--workspace-root", required=True)
    preview_parser.add_argument("--candidate", default=str(DEFAULT_TEMPLATE))

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--workspace-root", required=True)
    apply_parser.add_argument("--candidate", default=str(DEFAULT_TEMPLATE))
    apply_parser.add_argument("--expected-preview-sha256", required=True)
    apply_parser.add_argument("--confirm-write", action="store_true")
    return parser


def main() -> int:
    """執行命令並輸出機器可讀 JSON。"""

    args = build_parser().parse_args()
    try:
        workspace_root = validate_workspace_root(args.workspace_root)
        if args.command == "status":
            result = workspace_status(workspace_root)
        elif args.command == "preview":
            result = build_preview(workspace_root, Path(args.candidate))
        elif args.command == "apply":
            result = apply_configuration(
                workspace_root,
                Path(args.candidate),
                args.expected_preview_sha256,
                confirmed=args.confirm_write,
            )
        else:
            raise ConfigurationError("未知命令")
    except (ConfigurationError, OSError) as error:
        print(json.dumps({"result": "stopped", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
