#!/usr/bin/env python3
"""驗證第一個社群媒體技能的結構、邊界與公開內容。"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTED = {"social-media-setup"}
PLANNED = {
    "social-content-planning",
    "social-content-writing",
    "social-image-production",
    "social-content-publishing",
    "social-community-management",
    "social-performance-analysis",
}
PLATFORMS = {"youtube", "instagram", "facebook", "threads", "substack"}
TEXT_SUFFIXES = {".md", ".toml", ".py", ".json", ".yaml", ".yml", ".txt"}
PRIVATE_PATTERNS = (
    "/" + "Users/",
    "/" + "Volumes/",
    "C:\\" + "Users\\",
    "kai" + "yuankang",
    "iam" + "raven",
    "ravan" + "-ai",
    "macmini/" + "newsletter",
    ".hermes" + "/",
)
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\bya29\.[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


class ValidationError(RuntimeError):
    """代表公開候選版可修正的靜態問題。"""


def read_manifest() -> dict:
    """讀取套件 manifest。"""

    with (ROOT / "install.manifest.toml").open("rb") as handle:
        return tomllib.load(handle)


def parse_skill_name(skill_file: Path) -> str:
    """從技能 frontmatter 讀取名稱。"""

    text = skill_file.read_text(encoding="utf-8")
    match = re.match(r"^---\n(?P<header>.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise ValidationError(f"缺少有效 frontmatter：{skill_file}")
    name = re.search(r"^name:\s*([a-z0-9-]+)\s*$", match.group("header"), re.MULTILINE)
    if not name:
        raise ValidationError(f"frontmatter 缺少 name：{skill_file}")
    return name.group(1)


def validate_manifest(manifest: dict) -> None:
    """確認只把第一個完成技能列入安裝。"""

    expected = {
        "schema_version": 1,
        "manifest_type": "social-media-install",
        "status": "local_candidate_first_skill",
        "installable": True,
        "requires_network": False,
        "support_level": "first_skill_installable_candidate_not_formally_supported",
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValidationError(f"manifest.{key} 不符")
    manifest_date = manifest.get("checked_on")
    if not isinstance(manifest_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", manifest_date):
        raise ValidationError("manifest.checked_on 必須是 ISO 日期")
    implemented = {record.get("id") for record in manifest.get("skills", [])}
    planned = {record.get("id") for record in manifest.get("planned_skills", [])}
    if implemented != IMPLEMENTED or planned != PLANNED or implemented & planned:
        raise ValidationError("已完成與待建立技能集合不符")
    if manifest.get("installation", {}).get("managed_entries") != ["social-media-setup"]:
        raise ValidationError("安裝器只能管理目前完成的第一個技能")
    if manifest.get("workspace", {}).get("configuration_schema_version") != 3:
        raise ValidationError("manifest 必須宣告一般設定 schema version 3")
    credential_storage = manifest.get("credential_storage", {})
    expected_credential_storage = {
        "helper": "skills/social-media-setup/scripts/credential_store.py",
        "registry_schema": "skills/social-media-setup/references/credential-references.schema.json",
        "registry_schema_version": 2,
        "terminal_helper": "skills/social-media-setup/scripts/credential_terminal.py",
        "registry_target": "<workspace>/.local/social-media/credential-references.json",
        "default_macos_backend": "macos-keychain",
        "default_windows_backend": "windows-credential-manager",
        "unsupported_os_policy": "stop_without_plaintext_fallback",
        "interactive_input": "visible_terminal_hidden_prompt",
        "secret_cli_output": False,
    }
    if credential_storage != expected_credential_storage:
        raise ValidationError("manifest 的原生憑證庫契約不完整")
    if manifest.get("acceptance_policy", {}).get("default_tests") != "fictional_local_only":
        raise ValidationError("目前一般測試必須維持虛構本機資料，不自動開始實機驗收")
    oauth = manifest.get("oauth_runtime", {})
    if oauth.get("routes") != ["facebook", "youtube"] or oauth.get("status") != "implemented_fictional_tests_live_deferred":
        raise ValidationError("OAuth 執行器範圍必須明列 Facebook Pages／YouTube，不能代表全部平台")
    for key in ("entrypoint", "engine", "transport", "state_schema"):
        if not (ROOT / oauth.get(key, "missing")).is_file():
            raise ValidationError("OAuth 執行器缺少 manifest 對應檔案")
    if manifest.get("license_spdx") != "Apache-2.0":
        raise ValidationError("缺少 Apache-2.0 授權聲明")
    if not (ROOT / "LICENSE").is_file():
        raise ValidationError("可獨立散布的技能包缺少 LICENSE")
    if manifest.get("dependencies"):
        raise ValidationError("第一技能不得宣告第三方套件依賴")
    runtime = manifest.get("runtime", {})
    if runtime.get("local_strategy_requires_network") is not False:
        raise ValidationError("純策略設定不得要求網路")
    if runtime.get("platform_capability_refresh_requires_network") is not True:
        raise ValidationError("平台能力刷新必須揭露網路需求")
    if runtime.get("external_account_actions_require_explicit_authorization") is not True:
        raise ValidationError("外部帳號操作必須保留明確授權關卡")
    gates = {item.get("id"): item.get("status") for item in manifest.get("readiness_gates", [])}
    if gates.get("local_credential_storage") != (
        "implementation_and_fictional_backend_tests_complete_macos_windows_live_not_performed"
    ):
        raise ValidationError("原生憑證庫不得在實機驗收前標示完成")
    if gates.get("formal_public_support") != "not_supported":
        raise ValidationError("候選版不得宣稱正式公開支援")
    for reference in manifest.get("official_references", []):
        if not str(reference.get("url", "")).startswith("https://"):
            raise ValidationError("官方來源必須使用 HTTPS")
        reference_date = reference.get("checked_on")
        if not isinstance(reference_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", reference_date):
            raise ValidationError("官方來源缺少有效查證日期")
        if reference_date > manifest_date:
            raise ValidationError("官方來源查證日期不得晚於 manifest.checked_on")


def validate_skill_structure(manifest: dict) -> None:
    """確認技能可獨立安裝且平台文件完整。"""

    skill_root = ROOT / "skills"
    actual = {path.name for path in skill_root.iterdir() if path.is_dir()}
    if actual != IMPLEMENTED:
        raise ValidationError(f"技能目錄不應出現空殼：{sorted(actual)}")
    skill = skill_root / "social-media-setup"
    if parse_skill_name(skill / "SKILL.md") != "social-media-setup":
        raise ValidationError("技能名稱與 manifest 不符")
    required = {
        "agents/openai.yaml",
        "assets/default-config.json",
        "scripts/credential_store.py",
        "scripts/credential_terminal.py",
        "scripts/oauth_callback.py",
        "scripts/oauth_runtime.py",
        "scripts/oauth_http.py",
        "references/oauth-runtime.md",
        "references/oauth-state.schema.json",
        "scripts/manage_workspace.py",
        "references/credential-references.schema.json",
        "references/local-credential-storage.md",
        "references/strategy-mode.md",
        "references/integration-mode.md",
        "references/meta-api-setup.md",
        "references/youtube-api-setup.md",
        "references/permission-selection.md",
        "references/configuration-contract.md",
        "references/verification-levels.md",
        "references/social-media-config.schema.json",
        "references/setup-state.schema.json",
    }
    missing = [name for name in sorted(required) if not (skill / name).is_file()]
    if missing:
        raise ValidationError("技能缺少必要檔案：" + ", ".join(missing))
    platform_root = skill / "references/platforms"
    platforms = {path.stem for path in platform_root.glob("*.md")}
    if platforms != PLATFORMS:
        raise ValidationError(f"平台初始化文件不完整：{sorted(platforms)}")

    skill_text = (skill / "SKILL.md").read_text(encoding="utf-8")
    required_phrases = (
        "策略初始化",
        "平台整合初始化",
        "一次只問一個最重要的問題",
        "預設採完整管理模式",
        "如果有任何權限不想開放，請現在告訴我",
        "同一次 Meta 初始化",
        "取得明確確認後才寫入",
        "不得把瀏覽器內部請求或第三方套件冒充官方 API",
        "實際整合執行",
        "最小化人類操作",
        "不要求使用者手動選 use case",
        "macOS Keychain 或 Windows Credential Manager",
        "credential_store.py put",
        "使用者只貼上一次",
        "不代表已授權發布",
        "執行錯誤最小回填",
        "一次小修正、一次針對性重測",
        "不得修改已安裝快取、內建技能、外掛或第三方來源",
        "不發布",
        "停止條件",
        "虛構工作區驗證",
    )
    for phrase in required_phrases:
        if phrase not in skill_text:
            raise ValidationError(f"技能契約缺少：{phrase}")

    meta_text = (skill / "references/meta-api-setup.md").read_text(encoding="utf-8")
    facebook_text = (skill / "references/platforms/facebook.md").read_text(encoding="utf-8")
    instagram_text = (skill / "references/platforms/instagram.md").read_text(encoding="utf-8")
    threads_text = (skill / "references/platforms/threads.md").read_text(encoding="utf-8")
    behavior_text = (ROOT / "tests/behavior-cases.md").read_text(encoding="utf-8")
    meta_requirements = (
        "Meta 三平台合併初始化",
        "同一次設定對話中詢問是否一併設定另外兩個",
        "不可預設一定共用",
        "人工關卡一：身分、安全與法律同意",
        "人工關卡二：OAuth 同意",
        "不得要求使用者把值貼進對話",
        "credential_store.py put --platform facebook --name app-secret",
        "store_secret()",
        "state",
        "platform_read",
        "remote_write",
    )
    for phrase in meta_requirements:
        if phrase not in meta_text:
            raise ValidationError(f"Meta 實際初始化契約缺少：{phrase}")
    facebook_requirements = (
        "預設正式整合路徑：完整社群管理授權",
        "明確縮限路徑：粉絲專頁唯讀驗證",
        "pages_show_list",
        "GET /me/accounts?fields=id,name,access_token,tasks",
        "pages_manage_posts",
        "pages_manage_metadata",
        "pages_messaging",
        "read_insights",
        "可選延伸權限",
        "Page 唯讀查詢",
    )
    for phrase in facebook_requirements:
        if phrase not in facebook_text:
            raise ValidationError(f"Facebook 完整管理契約缺少：{phrase}")
    instagram_requirements = (
        "預設完整核心權限",
        "instagram_business_basic",
        "instagram_business_content_publish",
        "instagram_business_manage_comments",
        "instagram_business_manage_insights",
        "instagram_business_manage_messages",
        "instagram_manage_messages",
        "同一次 Meta 初始化",
    )
    for phrase in instagram_requirements:
        if phrase not in instagram_text:
            raise ValidationError(f"Instagram 完整管理契約缺少：{phrase}")
    threads_requirements = (
        "threads_basic",
        "threads_content_publish",
        "threads_read_replies",
        "threads_manage_replies",
        "threads_manage_insights",
        "沒有一般私訊管理 API",
        "同一次 Meta 初始化",
    )
    for phrase in threads_requirements:
        if phrase not in threads_text:
            raise ValidationError(f"Threads 完整管理契約缺少：{phrase}")
    for case_number in range(11, 35):
        if f"## {case_number}." not in behavior_text:
            raise ValidationError(f"缺少進階虛構行為案例 {case_number}")

    default = json.loads((skill / "assets/default-config.json").read_text(encoding="utf-8"))
    if default["strategy"]["status"] != "not_configured":
        raise ValidationError("公開範本必須維持 not_configured")
    if default["schema_version"] != 3:
        raise ValidationError("一般設定 schema_version 必須是 3")
    if set(default["integrations"]) != PLATFORMS:
        raise ValidationError("公開範本必須明列五個平台")
    for record in default["integrations"].values():
        if record["selected"] or record["requested_capabilities"]:
            raise ValidationError("公開範本不得預選平台或功能")
        if record.get("authorization_profile") != "not_selected":
            raise ValidationError("未選平台的授權模式必須是 not_selected")
        if record.get("requested_permissions") or record.get("declined_permissions"):
            raise ValidationError("公開範本不得預先要求或拒絕 permission")
        if record.get("verification") != {
            "api_app": "not_started",
            "user_auth": "not_started",
            "platform_read": "not_started",
            "remote_write": "not_requested",
        }:
            raise ValidationError("公開範本必須分開初始化四個整合驗證層級")
    json.loads((skill / "references/social-media-config.schema.json").read_text(encoding="utf-8"))
    json.loads((skill / "references/setup-state.schema.json").read_text(encoding="utf-8"))
    credential_schema = json.loads(
        (skill / "references/credential-references.schema.json").read_text(
            encoding="utf-8"
        )
    )
    oauth_schema = json.loads((skill / "references/oauth-state.schema.json").read_text(encoding="utf-8"))
    if oauth_schema.get("additionalProperties") is not False or oauth_schema["properties"]["contains_credentials"] != {"const": False}:
        raise ValidationError("OAuth 狀態不得放入額外欄位或秘密")
    if credential_schema.get("properties", {}).get("contains_credentials") != {
        "const": False
    }:
        raise ValidationError("憑證參照 schema 必須禁止秘密值")
    credential_text = (skill / "references/local-credential-storage.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "預設使用目前登入作業系統帳號的原生憑證庫",
        "不得改存 `.env`",
        "不得接受 `--value`",
        "不代表已授權發布",
        "不得新增會把秘密印到 stdout 的 `get` 命令",
        "另一臺電腦必須重新 OAuth",
    ):
        if phrase not in credential_text:
            raise ValidationError(f"本機憑證儲存契約缺少：{phrase}")
    credential_script = (skill / "scripts/credential_store.py").read_text(
        encoding="utf-8"
    )
    for phrase in ("SecItemAdd", "CredWriteW", "getpass.getpass"):
        if phrase not in credential_script:
            raise ValidationError(f"原生憑證 helper 缺少：{phrase}")
    if 'add_argument("--value"' in credential_script:
        raise ValidationError("憑證 helper 不得接受命令列秘密值")


def validate_public_boundary() -> None:
    """掃描公開文字中的私人路徑、來源名稱與常見秘密。"""

    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"[\ue000-\uf8ff\ufffd]", text):
            raise ValidationError(f"公開文字含非預期私用字元或解碼替代字元：{path}")
        for pattern in PRIVATE_PATTERNS:
            if pattern.lower() in text.lower():
                raise ValidationError(f"公開檔案含私人來源或路徑：{path}: {pattern}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise ValidationError(f"公開檔案疑似含秘密：{path}")


def validate_python_sources() -> None:
    """以記憶體編譯 Python，避免在來源目錄產生快取。"""

    for path in ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")


def main() -> int:
    """執行全部靜態檢查。"""

    try:
        manifest = read_manifest()
        validate_manifest(manifest)
        validate_skill_structure(manifest)
        validate_public_boundary()
        validate_python_sources()
    except (ValidationError, OSError, ValueError, tomllib.TOMLDecodeError) as error:
        print(f"驗證失敗：{error}", file=sys.stderr)
        return 1
    print("靜態結構、技能契約、公開邊界與 Python 語法驗證通過。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
