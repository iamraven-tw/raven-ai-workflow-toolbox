#!/usr/bin/env python3
"""預覽並安全寫入不含憑證的官網一般設定。"""

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
CONFIG_RELATIVE = Path("website/config.json")
STATE_RELATIVE = Path(".local/website/setup-state.json")

REQUIRED_PAGES = ["home", "about", "services", "blog", "contact", "not_found"]
OPTIONAL_PAGES = {"portfolio", "case_studies", "pricing", "faq", "newsletter"}
BUSINESS_STATUSES = {"not_configured", "partial", "configured"}
CTA_KINDS = {"not_selected", "mailto", "external_link", "form_later"}
CONTACT_KINDS = {"email", "messaging_link", "social_profile", "external_page"}
LANGUAGES = {"zh-TW", "en"}
DESIGN_STATUSES = {"not_selected", "recommended", "previewed", "confirmed"}
TONALITIES = {
    "not_selected",
    "personal_friendly",
    "dark_immersive",
    "clean_minimal",
    "photo_showroom",
    "colorful_energetic",
    "editorial_press",
}
STYLE_SOURCES = {"not_selected", "bundled", "open_design", "daisyui", "neutral_default"}
FONT_MODES = {"google", "system"}
DEPLOY_ROUTES = {"wrangler_local", "workers_builds_git"}
SUBDOMAIN_STATUSES = {"not_started", "requires_user_action", "active"}
DOMAIN_WANTED = {"undecided", "no", "yes"}
DOMAIN_STATES = {"none", "to_purchase", "existing_on_cloudflare", "existing_dns_elsewhere"}
ACQUISITION_ROUTES = {"not_selected", "cloudflare_registrar", "external_registrar", "existing"}
LOCAL_BUILD_STATUSES = {"not_started", "passed", "failed"}
PAGE_CHECK_STATUSES = {"not_started", "passed", "failed"}
WRANGLER_LOGIN_STATUSES = {"not_started", "requires_user_action", "verified", "failed", "unknown"}
DEPLOY_STATUSES = {
    "not_started",
    "not_authorized",
    "requires_user_action",
    "deployed_readback_verified",
    "failed",
    "unknown",
}
CUSTOM_DOMAIN_STATUSES = {"not_applicable", "not_started", "requires_user_action", "verified", "failed", "unknown"}
PUBLIC_INDEX_STATUSES = {"noindex", "index_authorized", "index_verified"}

SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
WORKER_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
DOMAIN_PATTERN = re.compile(r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
SECRET_KEY_FRAGMENTS = {
    "token",
    "secret",
    "password",
    "cookie",
    "credential",
    "apikey",
    "accesskey",
    "clientid",
    "accountid",
    "zoneid",
    "deployhook",
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


def require_exact_keys(payload: Any, expected: set[str], *, path: str) -> dict[str, Any]:
    """要求物件欄位完整且沒有未定義欄位。"""

    if not isinstance(payload, dict):
        raise ConfigurationError(f"{path} 必須是 object")
    actual = set(payload)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ConfigurationError(f"{path} 欄位不符；缺少={missing}，多出={extra}")
    return payload


def validate_optional_text(value: Any, *, path: str, maximum: int) -> None:
    """驗證可為 null 的短文字。"""

    if value is None:
        return
    validate_text(value, path=path, maximum=maximum)


def validate_text(value: Any, *, path: str, maximum: int) -> None:
    """驗證非空短文字。"""

    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ConfigurationError(f"{path} 必須是 1 至 {maximum} 字元的文字")
    if any(ord(character) < 32 and character not in "\n\t" for character in value):
        raise ConfigurationError(f"{path} 含不允許的控制字元")


def validate_enum(value: Any, allowed: set[str], *, path: str) -> None:
    """驗證列舉值。"""

    if not isinstance(value, str) or value not in allowed:
        raise ConfigurationError(f"{path} 不支援：{value!r}")


def validate_relative_markdown(value: Any, *, path: str) -> None:
    """驗證工作區相對的 Markdown 路徑，或 null。"""

    if value is None:
        return
    if not isinstance(value, str) or not value or "\\" in value or len(value) > 300:
        raise ConfigurationError(f"{path} 必須是工作區相對 POSIX 路徑")
    source_path = PurePosixPath(value)
    if source_path.is_absolute() or ".." in source_path.parts or source_path == PurePosixPath("."):
        raise ConfigurationError(f"{path} 不得是絕對路徑、空路徑或跳出工作區")
    if source_path.suffix.lower() != ".md":
        raise ConfigurationError(f"{path} 必須指向 Markdown 檔")


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


def validate_link_target(value: Any, *, path: str, kind: str) -> None:
    """依類型驗證 mailto 或 https 目標。"""

    validate_text(value, path=path, maximum=500)
    if kind == "email":
        if not value.startswith("mailto:") or "@" not in value:
            raise ConfigurationError(f"{path} 必須是 mailto: 位址")
    elif not value.startswith("https://"):
        raise ConfigurationError(f"{path} 必須是 https:// 網址")


def validate_business(business: dict[str, Any]) -> None:
    """驗證商業資訊區塊。"""

    require_exact_keys(
        business,
        {
            "status",
            "site_name",
            "one_line_positioning",
            "audience_summary",
            "offerings",
            "trust_signals",
            "primary_call_to_action",
            "contact_channels",
            "language",
            "profile_source",
        },
        path="$.business",
    )
    validate_enum(business["status"], BUSINESS_STATUSES, path="business.status")
    validate_optional_text(business["site_name"], path="business.site_name", maximum=100)
    validate_optional_text(business["one_line_positioning"], path="business.one_line_positioning", maximum=300)
    validate_optional_text(business["audience_summary"], path="business.audience_summary", maximum=1000)
    validate_enum(business["language"], LANGUAGES, path="business.language")
    validate_relative_markdown(business["profile_source"], path="business.profile_source")

    offerings = business["offerings"]
    if not isinstance(offerings, list) or len(offerings) > 10:
        raise ConfigurationError("business.offerings 必須是最多 10 項的清單")
    names: list[str] = []
    for index, offering in enumerate(offerings):
        require_exact_keys(offering, {"name", "summary"}, path=f"$.business.offerings[{index}]")
        validate_text(offering["name"], path=f"business.offerings[{index}].name", maximum=100)
        validate_text(offering["summary"], path=f"business.offerings[{index}].summary", maximum=300)
        names.append(offering["name"])
    if len(names) != len(set(names)):
        raise ConfigurationError("business.offerings 名稱不得重複")

    signals = business["trust_signals"]
    if not isinstance(signals, list) or len(signals) > 10:
        raise ConfigurationError("business.trust_signals 必須是最多 10 項的清單")
    for index, signal in enumerate(signals):
        validate_text(signal, path=f"business.trust_signals[{index}]", maximum=200)
    if len(signals) != len(set(signals)):
        raise ConfigurationError("business.trust_signals 不得重複")

    cta = require_exact_keys(
        business["primary_call_to_action"], {"kind", "label", "target"}, path="$.business.primary_call_to_action"
    )
    validate_enum(cta["kind"], CTA_KINDS, path="business.primary_call_to_action.kind")
    validate_optional_text(cta["label"], path="business.primary_call_to_action.label", maximum=60)
    if cta["kind"] == "not_selected":
        if cta["label"] is not None or cta["target"] is not None:
            raise ConfigurationError("未選擇的行動呼籲不得帶有 label 或 target")
    else:
        if cta["label"] is None:
            raise ConfigurationError("已選擇的行動呼籲必須有 label")
        if cta["kind"] == "form_later":
            if cta["target"] is not None:
                raise ConfigurationError("form_later 的行動呼籲 target 必須為 null")
        else:
            validate_link_target(
                cta["target"],
                path="business.primary_call_to_action.target",
                kind="email" if cta["kind"] == "mailto" else "link",
            )

    channels = business["contact_channels"]
    if not isinstance(channels, list) or len(channels) > 10:
        raise ConfigurationError("business.contact_channels 必須是最多 10 項的清單")
    for index, channel in enumerate(channels):
        require_exact_keys(channel, {"kind", "label", "target"}, path=f"$.business.contact_channels[{index}]")
        validate_enum(channel["kind"], CONTACT_KINDS, path=f"business.contact_channels[{index}].kind")
        validate_text(channel["label"], path=f"business.contact_channels[{index}].label", maximum=60)
        validate_link_target(
            channel["target"],
            path=f"business.contact_channels[{index}].target",
            kind="email" if channel["kind"] == "email" else "link",
        )

    if business["status"] == "not_configured":
        has_content = bool(
            business["site_name"]
            or business["one_line_positioning"]
            or business["audience_summary"]
            or offerings
            or signals
            or channels
            or cta["kind"] != "not_selected"
        )
        if has_content:
            raise ConfigurationError("not_configured 的商業資訊不得同時帶有內容")
    elif business["status"] == "configured":
        if not business["site_name"] or not business["one_line_positioning"] or not business["audience_summary"]:
            raise ConfigurationError("configured 的商業資訊必須有網站名稱、定位與受眾")
        if not offerings:
            raise ConfigurationError("configured 的商業資訊至少需要一項服務或產品")
        if cta["kind"] == "not_selected":
            raise ConfigurationError("configured 的商業資訊必須選擇主要行動呼籲")


def validate_pages(pages: dict[str, Any]) -> None:
    """驗證頁面清單。"""

    require_exact_keys(pages, {"required", "optional"}, path="$.pages")
    selected = pages["required"]
    if (not isinstance(selected, list) or any(page not in REQUIRED_PAGES for page in selected)
            or len(selected) != len(set(selected)) or not {"home", "not_found"}.issubset(selected)):
        raise ConfigurationError("pages.required 必須是無重複的已選頁面，至少含 home 與 not_found")
    optional = pages["optional"]
    if not isinstance(optional, list) or any(item not in OPTIONAL_PAGES for item in optional):
        raise ConfigurationError("pages.optional 含不支援的頁面")
    if len(optional) != len(set(optional)):
        raise ConfigurationError("pages.optional 不得重複")


def validate_design(design: dict[str, Any]) -> None:
    """驗證設計區塊的狀態一致性。"""

    require_exact_keys(design, {"status", "tonality", "style_source", "style_id", "fonts"}, path="$.design")
    validate_enum(design["status"], DESIGN_STATUSES, path="design.status")
    validate_enum(design["fonts"], FONT_MODES, path="design.fonts")
    validate_enum(design["tonality"], TONALITIES, path="design.tonality")
    validate_enum(design["style_source"], STYLE_SOURCES, path="design.style_source")
    style_id = design["style_id"]
    if style_id is not None and (not isinstance(style_id, str) or not SLUG_PATTERN.fullmatch(style_id)):
        raise ConfigurationError("design.style_id 必須是小寫 slug 或 null")
    if design["status"] == "not_selected":
        if design["tonality"] != "not_selected" or design["style_source"] != "not_selected" or style_id is not None:
            raise ConfigurationError("not_selected 的設計不得帶有調性或風格")
        return
    if design["tonality"] == "not_selected":
        raise ConfigurationError("已推薦或確認的設計必須指定調性")
    if design["status"] == "confirmed":
        if design["style_source"] == "not_selected":
            raise ConfigurationError("confirmed 的設計必須指定風格來源")
        if design["style_source"] in {"bundled", "open_design", "daisyui"} and style_id is None:
            raise ConfigurationError("bundled、open_design 與 daisyui 風格必須指定 style_id")
        if design["style_source"] == "neutral_default" and style_id is not None:
            raise ConfigurationError("neutral_default 不得帶有 style_id")


def validate_hosting(hosting: dict[str, Any]) -> None:
    """驗證託管與網域路線。"""

    require_exact_keys(
        hosting,
        {"provider", "plan", "deploy_route", "worker_name", "workers_dev", "custom_domain"},
        path="$.hosting",
    )
    if hosting["provider"] != "cloudflare_workers_static" or hosting["plan"] != "free":
        raise ConfigurationError("hosting 必須是 Cloudflare Workers 靜態資產免費方案")
    validate_enum(hosting["deploy_route"], DEPLOY_ROUTES, path="hosting.deploy_route")
    worker_name = hosting["worker_name"]
    if worker_name is not None and (not isinstance(worker_name, str) or not WORKER_NAME_PATTERN.fullmatch(worker_name)):
        raise ConfigurationError("hosting.worker_name 必須是小寫 slug 或 null")
    workers_dev = require_exact_keys(hosting["workers_dev"], {"enabled", "subdomain_status"}, path="$.hosting.workers_dev")
    if workers_dev["enabled"] is not True:
        raise ConfigurationError("hosting.workers_dev.enabled 必須是 true")
    validate_enum(workers_dev["subdomain_status"], SUBDOMAIN_STATUSES, path="hosting.workers_dev.subdomain_status")

    domain = require_exact_keys(
        hosting["custom_domain"], {"wanted", "current_state", "acquisition_route", "domain"}, path="$.hosting.custom_domain"
    )
    validate_enum(domain["wanted"], DOMAIN_WANTED, path="hosting.custom_domain.wanted")
    validate_enum(domain["current_state"], DOMAIN_STATES, path="hosting.custom_domain.current_state")
    validate_enum(domain["acquisition_route"], ACQUISITION_ROUTES, path="hosting.custom_domain.acquisition_route")
    name = domain["domain"]
    if name is not None and (not isinstance(name, str) or not DOMAIN_PATTERN.fullmatch(name)):
        raise ConfigurationError("hosting.custom_domain.domain 必須是小寫主機名稱或 null")
    if domain["wanted"] != "yes":
        if domain["current_state"] != "none" or domain["acquisition_route"] != "not_selected" or name is not None:
            raise ConfigurationError("未決定或不要自訂網域時不得帶有網域路線或名稱")
        return
    route = domain["acquisition_route"]
    if route == "not_selected":
        raise ConfigurationError("要自訂網域時必須選擇取得路線")
    if route == "existing":
        if domain["current_state"] not in {"existing_on_cloudflare", "existing_dns_elsewhere"} or name is None:
            raise ConfigurationError("既有網域必須說明 DNS 位置並填入網域")
    elif domain["current_state"] != "to_purchase":
        raise ConfigurationError("購買路線的網域現況必須是 to_purchase")


def validate_verification(verification: dict[str, Any], hosting: dict[str, Any]) -> None:
    """驗證各層驗證狀態不得跳層。"""

    require_exact_keys(
        verification,
        {"local_build", "automated_page_checks", "wrangler_login", "workers_dev_deploy", "custom_domain", "public_index"},
        path="$.verification",
    )
    validate_enum(verification["local_build"], LOCAL_BUILD_STATUSES, path="verification.local_build")
    validate_enum(verification["automated_page_checks"], PAGE_CHECK_STATUSES, path="verification.automated_page_checks")
    validate_enum(verification["wrangler_login"], WRANGLER_LOGIN_STATUSES, path="verification.wrangler_login")
    validate_enum(verification["workers_dev_deploy"], DEPLOY_STATUSES, path="verification.workers_dev_deploy")
    validate_enum(verification["custom_domain"], CUSTOM_DOMAIN_STATUSES, path="verification.custom_domain")
    validate_enum(verification["public_index"], PUBLIC_INDEX_STATUSES, path="verification.public_index")

    deployed = verification["workers_dev_deploy"] == "deployed_readback_verified"
    if deployed and (verification["wrangler_login"] != "verified" or verification["local_build"] != "passed"):
        raise ConfigurationError("workers.dev 部署驗證需要 Wrangler 登入與本機建置證據")
    wanted = hosting["custom_domain"]["wanted"] == "yes"
    if not wanted and verification["custom_domain"] != "not_applicable":
        raise ConfigurationError("未要求自訂網域時 verification.custom_domain 必須是 not_applicable")
    if wanted and verification["custom_domain"] == "not_applicable":
        raise ConfigurationError("要求自訂網域時 verification.custom_domain 不得是 not_applicable")
    domain_verified = verification["custom_domain"] == "verified"
    if domain_verified and not deployed:
        raise ConfigurationError("自訂網域驗證缺少 workers.dev 部署證據")
    if verification["public_index"] == "index_verified":
        if not deployed or (wanted and not domain_verified):
            raise ConfigurationError("公開收錄驗證缺少部署或網域證據")


def validate_configuration(payload: dict[str, Any]) -> None:
    """以不需第三方套件的方式執行完整設定契約。"""

    reject_secret_material(payload)
    require_exact_keys(
        payload, {"schema_version", "business", "pages", "design", "hosting", "verification"}, path="$"
    )
    if payload["schema_version"] != 1:
        raise ConfigurationError("schema_version 必須是 1")
    validate_business(payload["business"])
    validate_pages(payload["pages"])
    if payload["business"]["primary_call_to_action"]["kind"] == "form_later" and "contact" not in payload["pages"]["required"]:
        raise ConfigurationError("form_later 需要已選 contact 頁面")
    validate_design(payload["design"])
    validate_hosting(payload["hosting"])
    validate_verification(payload["verification"], payload["hosting"])


def flatten(payload: Any, *, prefix: str = "$") -> dict[str, Any]:
    """將 JSON 展平成欄位路徑，供預覽顯示差異。"""

    if isinstance(payload, dict):
        result: dict[str, Any] = {}
        for key in sorted(payload):
            result.update(flatten(payload[key], prefix=f"{prefix}.{key}"))
        return result
    if isinstance(payload, list):
        return {prefix: json.dumps(payload, ensure_ascii=False, sort_keys=True)}
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
    config_path = validate_target_path(workspace_root, CONFIG_RELATIVE, label="正式設定目標")
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
    config_path = validate_target_path(workspace_root, CONFIG_RELATIVE, label="正式設定目標")
    state_path = validate_target_path(workspace_root, STATE_RELATIVE, label="設定狀態目標")

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


def validate_timestamp(value: Any, *, path: str) -> None:
    """驗證帶時區的 ISO 日期時間。"""

    if not isinstance(value, str):
        raise ConfigurationError(f"{path} 必須是 ISO 日期時間")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ConfigurationError(f"{path} 不是有效 ISO 日期時間") from error
    if parsed.tzinfo is None:
        raise ConfigurationError(f"{path} 必須包含時區")


def workspace_status(workspace_root: Path) -> dict[str, Any]:
    """唯讀檢查正式設定與非敏感狀態是否一致。"""

    config_path = validate_target_path(workspace_root, CONFIG_RELATIVE, label="正式設定目標")
    state_path = validate_target_path(workspace_root, STATE_RELATIVE, label="設定狀態目標")
    if not os.path.lexists(config_path):
        return {"result": "missing", "config_target": str(config_path), "state_target": str(state_path)}
    config = read_json_file(config_path, label="正式設定")
    validate_configuration(config)
    config_digest = sha256_bytes(config_path.read_bytes())
    if not os.path.lexists(state_path):
        return {"result": "configured_without_state", "config_sha256": config_digest, "contains_credentials": False}
    state = read_json_file(state_path, label="設定狀態")
    require_exact_keys(
        state, {"schema_version", "config_sha256", "applied_at", "contains_credentials"}, path="$.state"
    )
    validate_timestamp(state["applied_at"], path="state.applied_at")
    if state["schema_version"] != 1 or state["contains_credentials"] is not False:
        raise ConfigurationError("設定狀態版本或憑證聲明不符")
    if not isinstance(state["config_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", state["config_sha256"]):
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
        "business_status": config["business"]["status"],
        "verification": "hashes_match",
        "contains_credentials": False,
    }


def build_parser() -> argparse.ArgumentParser:
    """建立命令列介面。"""

    parser = argparse.ArgumentParser(description="安全管理官網一般設定")
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
