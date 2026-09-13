#!/usr/bin/env python3
"""驗證官網打造技能包的結構、邊界與公開內容。"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTED = {"website-setup", "website-content-writing", "website-design-preview", "website-build", "website-deploy", "website-service-integration", "website-operations"}
PLANNED: set[str] = set()
TEXT_SUFFIXES = {".md", ".toml", ".py", ".json", ".jsonc", ".yaml", ".yml", ".txt", ".astro", ".mjs", ".ts", ".css", ".svg"}
BINARY_ALLOWED_SUFFIXES = {".jpg", ".png"}
PRIVATE_PATTERNS = (
    "/" + "Users/",
    "/" + "Volumes/",
    "C:\\" + "Users\\",
    "kai" + "yuankang",
    "iam" + "raven",
    "raven" + ".tw",
    "raven" + "-ai",
    "macmini/" + "newsletter",
    ".hermes" + "/",
    "deploy_" + "hooks/",
)
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\bya29\.[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)
STYLE_THRESHOLD = {
    "inclusion_threshold_license": "osi_approved",
    "inclusion_threshold_stars": 10000,
    "inclusion_threshold_or": "major_vendor_publication",
    "inclusion_threshold_activity_days": 90,
    "inclusion_threshold_pinning": "fixed_commit_or_version",
    "inclusion_threshold_assets": "no_brand_images_or_font_files",
}


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
    if not re.search(r"^description:\s*\".+\"\s*$", match.group("header"), re.MULTILINE):
        raise ValidationError(f"frontmatter 缺少 description：{skill_file}")
    return name.group(1)


def is_iso_date(value: object) -> bool:
    """檢查 ISO 日期字串。"""

    return isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None


def validate_manifest(manifest: dict) -> None:
    """確認七技能、固定依賴與可獨立下載的契約。"""

    expected = {
        "schema_version": 1,
        "manifest_type": "website-building-install",
        "status": "local_candidate_complete_pack",
        "installable": True,
        "requires_network": False,
        "support_level": "complete_pack_installable_candidate_not_formally_supported",
        "license_spdx": "Apache-2.0",
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValidationError(f"manifest.{key} 不符")
    manifest_date = manifest.get("checked_on")
    if not is_iso_date(manifest_date):
        raise ValidationError("manifest.checked_on 必須是 ISO 日期")
    if not (ROOT / "LICENSE").is_file():
        raise ValidationError("可獨立散布的技能包缺少 LICENSE")
    if not (ROOT / "skills/website-design-preview/assets/previews/THIRD_PARTY_LICENSES.txt").is_file():
        raise ValidationError("離線畫廊缺少可隨安裝保留的第三方授權文字")
    package = json.loads((ROOT / "template/package.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "template/package-lock.json").read_text(encoding="utf-8"))
    if package["engines"] != lock["packages"][""]["engines"] or package["engines"]["node"] != manifest["template"]["node_engine"]:
        raise ValidationError("Node／npm 環境契約必須與 manifest、lockfile 一致")
    decision = manifest.get("decision_record")
    if not isinstance(decision, str) or not (ROOT / decision).is_file():
        raise ValidationError("manifest 必須連回存在的 ADR")

    implemented = {record.get("id") for record in manifest.get("skills", [])}
    planned = {record.get("id") for record in manifest.get("planned_skills", [])}
    if implemented != IMPLEMENTED or planned != PLANNED or implemented & planned:
        raise ValidationError("已完成與待建立技能集合不符")
    if set(manifest.get("installation", {}).get("managed_entries", [])) != IMPLEMENTED:
        raise ValidationError("安裝器只能管理目前已建立的技能")
    for record in manifest.get("planned_skills", []):
        if record.get("status") != "not_implemented" or not isinstance(record.get("first_release"), bool):
            raise ValidationError("planned_skills 必須標示 not_implemented 與 first_release")

    agent = manifest.get("agent_execution", {})
    if agent.get("default_mode") != "agent_executes_human_authorizes":
        raise ValidationError("manifest 必須宣告 Agent 執行、人類授權的預設模式")
    if not (ROOT / agent.get("human_touchpoints", "missing")).is_file():
        raise ValidationError("manifest 缺少人類接觸點文件")
    if agent.get("single_intake") is not True or agent.get("batch_confirmation") is not True:
        raise ValidationError("manifest 必須宣告一次訪談與批次確認")

    workspace = manifest.get("workspace", {})
    if workspace.get("configuration_schema_version") != 1:
        raise ValidationError("manifest 必須宣告一般設定 schema version 1")
    for key in ("configuration_manager", "configuration_schema", "state_schema", "template_path", "integrations_schema", "integrations_manager", "operations_schema", "operations_manager"):
        if not (ROOT / workspace.get(key, "missing")).is_file():
            raise ValidationError(f"manifest.workspace.{key} 對應檔案不存在")
    if workspace.get("credential_policy") != "never_store_in_skill_template_general_config_or_setup_state":
        raise ValidationError("manifest 必須禁止一般設定保存憑證")

    hosting = manifest.get("hosting", {})
    if hosting.get("provider") != "cloudflare_workers_static_assets" or hosting.get("plan") != "free":
        raise ValidationError("託管必須是 Cloudflare Workers 靜態資產免費方案")
    if hosting.get("default_deploy_route") != "wrangler_local":
        raise ValidationError("預設部署路線必須是 Agent 本機 wrangler")
    if hosting.get("api_token_policy") != "never_stored_by_pack_wrangler_oauth_login_only":
        raise ValidationError("套件不得保存 Cloudflare API Token")
    if not (ROOT / hosting.get("boundary_document", "missing")).is_file():
        raise ValidationError("缺少 Cloudflare 邊界文件")

    integrations = manifest.get("service_integrations", {})
    if integrations.get("supported_services") != ["contact_form", "newsletter", "booking", "payment"]:
        raise ValidationError("服務串接類型或順序不符")
    if integrations.get("credential_policy") != "never_store_only_public_values_rendered_in_html":
        raise ValidationError("服務串接不得保存憑證")
    for key in ("embedded_scripts", "iframes", "server_side_secrets"):
        if integrations.get(key) is not False:
            raise ValidationError(f"服務串接第一版不得啟用 {key}")
    if integrations.get("privacy_disclosure_required") is not True:
        raise ValidationError("服務串接必須要求隱私揭露")

    operations = manifest.get("operations", {})
    if operations.get("supported_modes") != ["public_health_check", "local_verified_backup", "isolated_restore", "dependency_update", "incident_response"]:
        raise ValidationError("維運技能支援模式或順序不符")
    if operations.get("backup_format") != "zip_with_sha256_manifest":
        raise ValidationError("維運備份必須使用帶 SHA-256 manifest 的 ZIP")
    if operations.get("restore_policy") != "new_isolated_directory_never_overwrite_current_site":
        raise ValidationError("維運復原不得覆寫目前網站")
    for key in ("backup_upload", "automatic_dependency_updates", "automatic_backup_pruning"):
        if operations.get(key) is not False:
            raise ValidationError(f"維運技能不得預設啟用 {key}")
    if operations.get("scheduled_monitoring_requires_explicit_request") is not True:
        raise ValidationError("定期監控必須由使用者明確要求")

    style = manifest.get("style_sources", {})
    for key, value in STYLE_THRESHOLD.items():
        if style.get(key) != value:
            raise ValidationError(f"風格來源納入門檻不符：{key}")
    if style.get("presentation") != "six_tonalities_no_brand_name_defaults":
        raise ValidationError("風格必須以六大調性呈現，不得以品牌名作預設")
    if style.get("default_path") != "bundled_themes_local_gallery_no_network":
        raise ValidationError("預設風格路徑必須是內建主題與本機畫廊")
    themes_root = ROOT / style.get("bundled_themes", "missing")
    theme_files = sorted(themes_root.glob("*/theme.json")) if themes_root.is_dir() else []
    if len(theme_files) != style.get("bundled_theme_count") or len(theme_files) < 6:
        raise ValidationError("內建主題數量與 manifest 不符")
    for key in ("gallery_script", "gallery_export_script", "gallery_previews"):
        if not (ROOT / style.get(key, "missing")).exists():
            raise ValidationError(f"manifest.style_sources.{key} 對應檔案不存在")
    if not re.fullmatch(r"[0-9a-f]{40}", str(style.get("guide_library_commit", ""))):
        raise ValidationError("設計指引來源必須固定完整 commit")

    if manifest.get("acceptance_policy", {}).get("default_tests") != "fictional_local_only":
        raise ValidationError("目前一般測試必須維持虛構本機資料，不自動開始實機驗收")
    template = manifest.get("template", {})
    for skill in manifest.get("skills", []):
        expected_assets = ([{"source_path": "template", "target_path": "assets/template"}]
                           if skill.get("id") == "website-build" else [])
        if skill.get("bundled_assets", []) != expected_assets:
            raise ValidationError("範本必須隨 website-build 受管理安裝，其餘技能不得注入資產")
    for key in ("path", "lockfile", "scaffold_script", "check_script"):
        if not (ROOT / template.get(key, "missing")).exists():
            raise ValidationError(f"manifest.template.{key} 對應檔案不存在")
    if template.get("install_command") != "npm ci" or template.get("fictional_brand") is not True:
        raise ValidationError("範本必須以 npm ci 安裝且只含虛構品牌")
    package = json.loads((ROOT / "template/package.json").read_text(encoding="utf-8"))
    declared = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    pinned = {dependency["id"]: dependency for dependency in manifest.get("dependencies", [])}
    if not pinned:
        raise ValidationError("範本依賴必須列於 manifest.dependencies")
    for dependency in pinned.values():
        for key in ("id", "role", "source", "pinned_version", "license", "consumer_skill", "installed_by", "status"):
            if not dependency.get(key):
                raise ValidationError(f"dependencies 缺少 {key}")
        if dependency.get("bundle_source") is not False:
            raise ValidationError("套件不得 vendoring 第三方依賴")
        if not str(dependency["source"]).startswith("https://"):
            raise ValidationError("依賴來源必須使用 HTTPS")
    for name, version in declared.items():
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            raise ValidationError(f"範本依賴必須鎖定確切版本：{name}={version}")
        matching = [item for item in pinned.values() if item["pinned_version"] == version and name.replace("@", "").replace("/", "-") == item["id"]]
        if not matching:
            raise ValidationError(f"範本依賴未記錄於 manifest：{name}")
    for dependency in manifest.get("planned_dependencies", []):
        for key in ("id", "role", "source", "license", "consumer_skill", "status"):
            if not dependency.get(key):
                raise ValidationError(f"planned_dependencies 缺少 {key}")
        if not str(dependency["source"]).startswith("https://"):
            raise ValidationError("依賴來源必須使用 HTTPS")
        if not str(dependency["status"]).startswith("reference_only"):
            raise ValidationError("第一技能階段的依賴必須維持 reference_only")
        if dependency["consumer_skill"] not in PLANNED | IMPLEMENTED:
            raise ValidationError("依賴的 consumer_skill 必須是規劃中或已建立的技能")

    gates = {item.get("id"): item.get("status") for item in manifest.get("readiness_gates", [])}
    for gate in ("wrangler_login", "workers_dev_deploy", "custom_domain", "service_integrations_live", "operations_public_monitoring", "second_computer_acceptance"):
        if gates.get(gate) != "not_performed":
            raise ValidationError(f"{gate} 不得在實機驗收前標示完成")
    if gates.get("formal_public_support") != "not_supported":
        raise ValidationError("候選版不得宣稱正式公開支援")
    if not manifest.get("external_facts_to_confirm"):
        raise ValidationError("manifest 必須記錄實作時要確認的外部事實")
    for reference in manifest.get("official_references", []):
        if not str(reference.get("url", "")).startswith("https://"):
            raise ValidationError("官方來源必須使用 HTTPS")
        if not is_iso_date(reference.get("checked_on")):
            raise ValidationError("官方來源缺少有效查證日期")
        if reference["checked_on"] > manifest_date:
            raise ValidationError("官方來源查證日期不得晚於 manifest.checked_on")


def validate_skill_structure() -> None:
    """確認技能可獨立安裝且參考文件完整。"""

    skill_root = ROOT / "skills"
    actual = {path.name for path in skill_root.iterdir() if path.is_dir()}
    if actual != IMPLEMENTED:
        raise ValidationError(f"技能目錄不應出現空殼：{sorted(actual)}")
    validate_template()
    validate_build_skill(skill_root / "website-build")
    validate_design_skill(skill_root / "website-design-preview")
    validate_deploy_skill(skill_root / "website-deploy")
    validate_service_integration_skill(skill_root / "website-service-integration")
    validate_operations_skill(skill_root / "website-operations")
    validate_content_skill(skill_root / "website-content-writing")
    skill = skill_root / "website-setup"
    if parse_skill_name(skill / "SKILL.md") != "website-setup":
        raise ValidationError("技能名稱與 manifest 不符")
    required = {
        "agents/openai.yaml",
        "assets/default-config.json",
        "scripts/manage_workspace.py",
        "references/website-config.schema.json",
        "references/setup-state.schema.json",
        "references/intake-questions.md",
        "references/page-inventory.md",
        "references/tonalities.md",
        "references/hosting-options.md",
        "references/configuration-contract.md",
        "references/verification-levels.md",
    }
    missing = [name for name in sorted(required) if not (skill / name).is_file()]
    if missing:
        raise ValidationError("技能缺少必要檔案：" + ", ".join(missing))

    skill_text = (skill / "SKILL.md").read_text(encoding="utf-8")
    required_phrases = (
        "一次訪談",
        "批次確認",
        "全部用預設",
        "人類接觸點",
        "一人公司設定與社群設定當預設值",
        "不建立專案、不部署",
        "取得明確確認後才寫入",
        "workers.dev",
        "Cloudflare Registrar",
        "命令旗標不是對話核准",
        "執行錯誤最小回填",
        "一次小修正、一次針對性重測",
        "不得修改已安裝快取、內建技能、外掛或第三方來源",
        "停止條件",
        "虛構工作區驗證",
    )
    for phrase in required_phrases:
        if phrase not in skill_text:
            raise ValidationError(f"技能契約缺少：{phrase}")
    if "Mermaid" not in skill_text:
        raise ValidationError("多階段技能必須要求以 Mermaid 呈現流程")

    hosting_text = (skill / "references/hosting-options.md").read_text(encoding="utf-8")
    for phrase in ("wrangler deploy", "cloudflare_registrar", "external_registrar", "Add a site", "nameserver", ".tw"):
        if phrase not in hosting_text:
            raise ValidationError(f"託管與網域文件缺少：{phrase}")
    tonality_text = (skill / "references/tonalities.md").read_text(encoding="utf-8")
    for tonality in ("personal_friendly", "dark_immersive", "clean_minimal", "photo_showroom", "colorful_energetic", "editorial_press"):
        if tonality not in tonality_text:
            raise ValidationError(f"調性文件缺少：{tonality}")
    intake_text = (skill / "references/intake-questions.md").read_text(encoding="utf-8")
    if "核心五題" not in intake_text or "不要問的題目" not in intake_text:
        raise ValidationError("訪談文件必須列出核心五題與不要問的題目")

    touchpoints = (ROOT / "docs/human-touchpoints.md").read_text(encoding="utf-8")
    for phrase in ("wrangler login", "Add a site", "nameserver", "購買網域", "不自訂網域時的最小路徑"):
        if phrase not in touchpoints:
            raise ValidationError(f"人類接觸點文件缺少：{phrase}")
    behavior_text = (ROOT / "tests/behavior-cases.md").read_text(encoding="utf-8")
    for case_number in range(1, 41):
        if f"## {case_number}." not in behavior_text:
            raise ValidationError(f"缺少虛構行為案例 {case_number}")

    default = json.loads((skill / "assets/default-config.json").read_text(encoding="utf-8"))
    if default["schema_version"] != 1 or default["business"]["status"] != "not_configured":
        raise ValidationError("公開範本必須維持 schema 1 與 not_configured")
    if default["business"]["site_name"] or default["business"]["offerings"] or default["business"]["contact_channels"]:
        raise ValidationError("公開範本不得預填商業內容")
    if default["design"]["status"] != "not_selected" or default["design"]["style_id"] is not None:
        raise ValidationError("公開範本不得預選風格")
    if default["hosting"]["worker_name"] is not None or default["hosting"]["custom_domain"]["domain"] is not None:
        raise ValidationError("公開範本不得預填 Worker 名稱或網域")
    if any(value not in {"not_started", "not_applicable", "noindex"} for value in default["verification"].values()):
        raise ValidationError("公開範本的驗證狀態必須全部是初始值")
    for name in ("website-config.schema.json", "setup-state.schema.json"):
        schema = json.loads((skill / "references" / name).read_text(encoding="utf-8"))
        if schema.get("additionalProperties") is not False:
            raise ValidationError(f"{name} 必須禁止額外欄位")
    state_schema = json.loads((skill / "references/setup-state.schema.json").read_text(encoding="utf-8"))
    if state_schema["properties"]["contains_credentials"] != {"const": False}:
        raise ValidationError("狀態 schema 必須禁止秘密")


def validate_template() -> None:
    """確認起始範本完整、去識別化且不含建置產物。"""

    template = ROOT / "template"
    required = (
        "package.json",
        "package-lock.json",
        "astro.config.mjs",
        "site.config.mjs",
        "wrangler.jsonc",
        "tsconfig.json",
        ".gitignore",
        "README.md",
        "src/site-config.d.ts",
        "src/data/integrations.json",
        "src/components/ServiceIntegrations.astro",
        "site.copy.mjs",
        "src/site-copy.d.ts",
        "src/content.config.ts",
        "src/content/posts/hello-world.md",
        "src/styles/global.css",
        "src/lib/nav.ts",
        "src/lib/menu.ts",
        "src/pages/index.astro",
        "src/pages/about.astro",
        "src/pages/services.astro",
        "src/pages/contact.astro",
        "src/pages/404.astro",
        "src/pages/blog/index.astro",
        "src/pages/blog/[slug].astro",
        "src/pages/rss.xml.ts",
        "public/favicon.svg",
        "public/og-image.png",
        "public/apple-touch-icon.png",
    )
    missing = [name for name in required if not (template / name).is_file()]
    if missing:
        raise ValidationError("範本缺少必要檔案：" + ", ".join(missing))
    if "paths" in json.loads((template / "tsconfig.json").read_text(encoding="utf-8")).get("compilerOptions", {}):
        raise ValidationError("範本 tsconfig 不得設定 paths，會蓋掉主題別名")
    if "@theme" not in (template / "astro.config.mjs").read_text(encoding="utf-8"):
        raise ValidationError("範本 astro.config 必須依 site.theme 設定 @theme 別名")
    samples = template / "public/images/samples"
    photos = json.loads((samples / "photos.json").read_text(encoding="utf-8"))
    if photos.get("license") != "Unsplash License" or not str(photos.get("license_url", "")).startswith("https://"):
        raise ValidationError("示範照片清單必須記錄授權與授權網址")
    listed = {record["file"] for record in photos.get("photos", [])}
    actual = {path.name for path in samples.glob("*.jpg")}
    if listed != actual or not actual:
        raise ValidationError("示範照片與 photos.json 清單不一致")
    for record in photos["photos"]:
        for key in ("author", "source_url", "picsum_id", "width", "height", "bytes"):
            if not record.get(key):
                raise ValidationError(f"示範照片 {record.get('file')} 缺少 {key}")
        if (samples / record["file"]).stat().st_size > 400_000:
            raise ValidationError(f"示範照片過大：{record['file']}")
    if sum(record["bytes"] for record in photos["photos"]) > 2_500_000:
        raise ValidationError("示範照片總量超過 2.5MB")
    site_config = (template / "site.config.mjs").read_text(encoding="utf-8")
    if "fonts: 'google'" not in site_config and "fonts: 'system'" not in site_config:
        raise ValidationError("範本站點設定必須宣告 fonts 欄位")
    for path in sorted((template / "src/themes").glob("*/theme.json")):
        theme = json.loads(path.read_text(encoding="utf-8"))
        href = theme.get("google_fonts", {}).get("href", "")
        if not href.startswith("https://fonts.googleapis.com/css2?"):
            raise ValidationError(f"主題 {theme.get('id')} 缺少 Google Fonts 設定")
        if "fontsHref" not in (path.parent / "BaseLayout.astro").read_text(encoding="utf-8"):
            raise ValidationError(f"主題 {theme.get('id')} 的 BaseLayout 未依 site.fonts 載入字型")
    for page in ("portfolio", "case-studies", "pricing", "faq", "newsletter"):
        if not (template / f"optional-pages/{page}.astro").is_file():
            raise ValidationError(f"範本缺少可選頁面：{page}")
    motion = template / "src/lib/motion.ts"
    if not motion.is_file() or "prefers-reduced-motion" not in motion.read_text(encoding="utf-8"):
        raise ValidationError("範本缺少共用動畫層 src/lib/motion.ts，或未尊重 prefers-reduced-motion")
    package = json.loads((template / "package.json").read_text(encoding="utf-8"))
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(package.get("dependencies", {}).get("motion", ""))):
        raise ValidationError("範本必須以確切版本固定 motion 依賴")
    for artifact in ("node_modules", "dist", ".astro"):
        if (template / artifact).exists():
            raise ValidationError(f"範本不得包含建置產物：{artifact}")
    site_config = (template / "site.config.mjs").read_text(encoding="utf-8")
    for phrase in ("example.invalid", "indexing: 'noindex'", "theme: '"):
        if phrase not in site_config:
            raise ValidationError(f"範本站點設定必須維持虛構與 noindex：{phrase}")
    wrangler = (template / "wrangler.jsonc").read_text(encoding="utf-8")
    for forbidden in ("kv_namespaces", "d1_databases", "r2_buckets", "account_id", "routes"):
        if f'"{forbidden}"' in wrangler:
            raise ValidationError(f"範本 wrangler 設定不得包含：{forbidden}")
    for path in template.rglob("*.astro"):
        text = path.read_text(encoding="utf-8")
        if "googletagmanager" in text or "gtag(" in text:
            raise ValidationError(f"範本不得內建分析或追蹤腳本：{path.name}")
        if "fonts.googleapis" in text and (path.name != "BaseLayout.astro" or "fontsHref &&" not in text):
            raise ValidationError(f"外部字型只能在受 site.fonts 開關保護的 BaseLayout 載入：{path}")

    integration_default = json.loads((ROOT / "skills/website-service-integration/assets/default-integrations.json").read_text(encoding="utf-8"))
    template_integration = json.loads((template / "src/data/integrations.json").read_text(encoding="utf-8"))
    if integration_default != template_integration:
        raise ValidationError("範本與 website-service-integration 的預設設定不一致")
    if (ROOT / "skills/website-service-integration/assets/ServiceIntegrations.astro").read_bytes() != (template / "src/components/ServiceIntegrations.astro").read_bytes():
        raise ValidationError("範本與 website-service-integration 的元件來源不一致")


def validate_build_skill(skill: Path) -> None:
    """確認 website-build 的契約與資源。"""

    if parse_skill_name(skill / "SKILL.md") != "website-build":
        raise ValidationError("建置技能名稱不符")
    for name in (
        "agents/openai.yaml",
        "scripts/scaffold_site.py",
        "scripts/check_site.py",
        "references/template-structure.md",
        "references/placeholder-assets.md",
        "references/build-and-check.md",
        "references/page-checks.md",
    ):
        if not (skill / name).is_file():
            raise ValidationError(f"建置技能缺少 {name}")
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    for phrase in (
        "npm ci",
        "check_site.py",
        "--confirm-write",
        "命令旗標不是對話核准",
        "不登入 Cloudflare、不部署",
        "noindex",
        "全部用預設",
        "不自行安裝",
        "執行錯誤最小回填",
        "停止條件",
        "WEBSITE_NODE_ACCEPTANCE=1",
    ):
        if phrase not in text:
            raise ValidationError(f"建置技能契約缺少：{phrase}")
    if "Mermaid" not in text:
        raise ValidationError("多階段技能必須要求以 Mermaid 呈現流程")
    scaffold = (skill / "scripts/scaffold_site.py").read_text(encoding="utf-8")
    if "目標目錄不是空的" not in scaffold or "--confirm-write" not in scaffold:
        raise ValidationError("scaffold 必須拒絕非空目標並要求確認旗標")


def validate_design_skill(skill: Path) -> None:
    """確認 website-design-preview 的契約、六個主題與匯出預覽。"""

    if parse_skill_name(skill / "SKILL.md") != "website-design-preview":
        raise ValidationError("風格技能名稱不符")
    for name in (
        "agents/openai.yaml",
        "scripts/style_gallery.py",
        "scripts/export_previews.py",
        "references/style-catalog.md",
        "references/token-contract.md",
        "references/extended-sources.md",
        "assets/previews/manifest.json",
    ):
        if not (skill / name).is_file():
            raise ValidationError(f"風格技能缺少 {name}")
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    for phrase in ("主動展示", "截圖", "建議", "--confirm-write", "命令旗標不是對話核准", "design.json", "不需要 Node", "不是換色", "執行錯誤最小回填", "停止條件"):
        if phrase not in text:
            raise ValidationError(f"風格技能契約缺少：{phrase}")
    if "Mermaid" not in text:
        raise ValidationError("多階段技能必須要求以 Mermaid 呈現流程")
    tonalities = {"personal_friendly", "dark_immersive", "clean_minimal", "photo_showroom", "colorful_energetic", "editorial_press"}
    brand_words = ("apple", "stripe", "vercel", "linear", "notion", "airbnb", "nike", "tesla", "spotify", "figma", "claude", "wired")
    themes_root = ROOT / "template/src/themes"
    seen: set[str] = set()
    theme_ids: set[str] = set()
    required_files = ("theme.css", "BaseLayout.astro", "Header.astro", "Footer.astro", "Home.astro", "BlogIndex.astro", "BlogPost.astro")
    required_classes = ("t-container", "t-section", "t-eyebrow", "t-h1", "t-h2", "t-h3", "t-card-title", "t-lead", "t-muted", "t-card", "t-btn", "t-btn-secondary", "t-link", "t-tag", "t-divider", "t-grid-3", "t-grid-2", "t-list-item", "t-note", "t-details", "t-media", "t-prose")
    for path in sorted(themes_root.glob("*/theme.json")):
        theme = json.loads(path.read_text(encoding="utf-8"))
        if theme.get("id") != path.parent.name:
            raise ValidationError(f"主題 id 與目錄不一致：{path.parent.name}")
        for key in ("name", "tonality", "order", "description", "fits", "source_guide", "source_license", "placeholder_colors", "google_fonts"):
            if key not in theme:
                raise ValidationError(f"主題 {theme['id']} 缺少 {key}")
        if theme.get("source_kind", "design_guide") == "layout_reference":
            # 版面參考型主題：只參考公開示範頁的版面手法，程式碼與素材皆自行實作，必須明確聲明
            refs = theme.get("source_references", [])
            if not refs or not all(str(url).startswith("https://") for url in refs):
                raise ValidationError(f"主題 {theme['id']} 缺少 https 的版面參考來源")
            if theme["source_license"] != "reference_only_no_code_copied" or "未複製" not in theme.get("source_note", ""):
                raise ValidationError(f"主題 {theme['id']} 必須聲明只參考版面、未複製程式碼與素材")
        elif theme["source_license"] != "Apache-2.0" or not str(theme.get("source_repository", "")).startswith("https://"):
            raise ValidationError(f"主題 {theme['id']} 的來源聲明不完整")
        if any(word in theme["id"] or word in theme["name"].lower() for word in brand_words):
            raise ValidationError(f"主題不得以品牌命名：{theme['id']}")
        for name in required_files:
            if not (path.parent / name).is_file():
                raise ValidationError(f"主題 {theme['id']} 缺少 {name}")
        css = (path.parent / "theme.css").read_text(encoding="utf-8")
        missing = [cls for cls in required_classes if f".{cls}" not in css]
        if missing:
            raise ValidationError(f"主題 {theme['id']} 的 theme.css 缺少共用類別：{', '.join(missing)}")
        seen.add(theme["tonality"])
        theme_ids.add(theme["id"])
    if seen != tonalities:
        raise ValidationError("內建主題必須覆蓋六大調性")
    previews = json.loads((skill / "assets/previews/manifest.json").read_text(encoding="utf-8"))
    exported = {record["id"] for record in previews.get("themes", [])}
    if exported != theme_ids:
        raise ValidationError("匯出預覽與主題清單不一致；請重新執行 export_previews.py")
    home_hashes = set()
    for record in previews["themes"]:
        for page in ("home", "blog", "post"):
            target = skill / "assets/previews" / record["pages"][page]["file"]
            if not target.is_file():
                raise ValidationError(f"缺少預覽檔：{target.name}")
            preview_text = target.read_text(encoding="utf-8")
            if 'href="/_astro/' in preview_text or 'src="/images/placeholders' in preview_text or 'src="/images/samples' in preview_text:
                raise ValidationError(f"預覽檔未內嵌或未改寫資源：{record['id']}/{page}")
            if target.stat().st_size > 400_000:
                raise ValidationError(f"預覽檔過大，照片不應內嵌：{record['id']}/{page}")
        home_hashes.add(record["pages"]["home"]["sha256"])
    if len(home_hashes) != len(previews["themes"]):
        raise ValidationError("有主題的首頁預覽完全相同，表示主題切換失效")
    if not (skill / "assets/previews/images/samples/photos.json").is_file():
        raise ValidationError("預覽目錄缺少示範照片副本")


def validate_deploy_skill(skill: Path) -> None:
    """確認 website-deploy 的契約、授權關卡與不保存 Token。"""

    if parse_skill_name(skill / "SKILL.md") != "website-deploy":
        raise ValidationError("部署技能名稱不符")
    for name in (
        "agents/openai.yaml",
        "scripts/deploy_site.py",
        "references/wrangler-local-route.md",
        "references/workers-builds-optional-route.md",
        "references/custom-domain-and-dns.md",
        "references/launch-checklist.md",
    ):
        if not (skill / name).is_file():
            raise ValidationError(f"部署技能缺少 {name}")
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    for phrase in (
        "wrangler login", "--confirm-deploy", "--confirm-write", "verify --config", "noindex", "命令旗標不是對話核准",
        "不保存任何 API Token", "不代按 OAuth 同意", "不輸入付款資料", "Add a site", "nameserver", "執行錯誤最小回填", "停止條件", "workers.dev",
    ):
        if phrase not in text:
            raise ValidationError(f"部署技能契約缺少：{phrase}")
    if "Mermaid" not in text:
        raise ValidationError("多階段技能必須要求以 Mermaid 呈現流程")
    script = (skill / "scripts/deploy_site.py").read_text(encoding="utf-8")
    for phrase in ("--confirm-deploy", "--confirm-write", "mask_email", "不記帳號 ID", '"account_id"', "example.invalid", "CI"):
        if phrase not in script:
            raise ValidationError(f"部署工具缺少保護：{phrase}")
    for forbidden in ("CLOUDFLARE_API_TOKEN", "api_token=", "Authorization: Bearer"):
        if forbidden in script:
            raise ValidationError(f"部署工具不得直接處理 Token：{forbidden}")
    package = json.loads((ROOT / "template/package.json").read_text(encoding="utf-8"))
    if package.get("devDependencies", {}).get("wrangler") != "4.129.0" or package.get("scripts", {}).get("deploy") != "wrangler deploy":
        raise ValidationError("範本必須鎖定 wrangler 4.129.0 並提供 deploy 指令")


def validate_service_integration_skill(skill: Path) -> None:
    """確認服務串接技能的靜態站點模式、授權與秘密邊界。"""

    if parse_skill_name(skill / "SKILL.md") != "website-service-integration":
        raise ValidationError("服務串接技能名稱不符")
    required = (
        "agents/openai.yaml",
        "assets/default-integrations.json",
        "assets/ServiceIntegrations.astro",
        "scripts/manage_integrations.py",
        "references/integration-config.schema.json",
        "references/integration-modes.md",
        "references/privacy-and-live-verification.md",
    )
    for name in required:
        if not (skill / name).is_file():
            raise ValidationError(f"服務串接技能缺少 {name}")
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    for phrase in (
        "Mermaid", "批次確認", "html_post", "hosted_link", "--confirm-write", "命令旗標不是對話核准",
        "隱私政策", "不自動扣款", "website-deploy", "讀回", "執行錯誤最小回填", "停止條件",
        "不得保存密碼", "form endpoint", "另外取得部署授權",
    ):
        if phrase not in text:
            raise ValidationError(f"服務串接技能契約缺少：{phrase}")
    script = (skill / "scripts/manage_integrations.py").read_text(encoding="utf-8")
    for phrase in (
        "plan_sha256", "--expected-plan-sha256", "--confirm-write", "reject_secret_material",
        "privacy_url", "link_only_no_transaction", "START_MARKER", "write_atomic", "public_readback",
    ):
        if phrase not in script:
            raise ValidationError(f"服務串接工具缺少保護：{phrase}")
    for forbidden in ("requests", "selenium", "playwright", "Authorization: Bearer"):
        if forbidden in script:
            raise ValidationError(f"服務串接工具不得內建第三方執行或憑證處理：{forbidden}")
    default = json.loads((skill / "assets/default-integrations.json").read_text(encoding="utf-8"))
    if default.get("status") != "not_configured" or any(item.get("enabled") for item in default.get("services", {}).values()):
        raise ValidationError("服務串接預設值不得啟用外部服務")
    if set(default.get("services", {})) != {"contact_form", "newsletter", "booking", "payment"}:
        raise ValidationError("服務串接預設值缺少四種服務")


def validate_operations_skill(skill: Path) -> None:
    """確認維運技能的監控、備份、復原與更新安全邊界。"""

    if parse_skill_name(skill / "SKILL.md") != "website-operations":
        raise ValidationError("維運技能名稱不符")
    required = (
        "agents/openai.yaml",
        "assets/default-operations.json",
        "scripts/manage_operations.py",
        "references/operations-config.schema.json",
        "references/monitoring-and-incidents.md",
        "references/backup-and-recovery.md",
        "references/updates-and-maintenance.md",
    )
    for name in required:
        if not (skill / name).is_file():
            raise ValidationError(f"維運技能缺少 {name}")
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    for phrase in (
        "Mermaid", "批次確認", "configure-plan", "backup-plan", "verify-backup", "restore-plan",
        "--confirm-write", "命令旗標不是對話核准", "不送表單", "不測試付款", "website-deploy",
        "另外取得部署授權", "不自動刪除", "隔離目錄", "npm outdated --json", "npm audit fix --force",
        "執行錯誤最小回填", "停止條件",
    ):
        if phrase not in text:
            raise ValidationError(f"維運技能契約缺少：{phrase}")
    script = (skill / "scripts/manage_operations.py").read_text(encoding="utf-8")
    for phrase in (
        "plan_sha256", "--expected-plan-sha256", "--confirm-write", "reject_secret_material",
        "EXCLUDED_DIRS", "SECRET_NAMES", "backup-manifest.json", "verify_archive", "zip-slip",
        "MAX_TOTAL_BYTES", "restored_to_isolation", "submitted_forms", "tls_status", "write_atomic",
    ):
        if phrase not in script:
            raise ValidationError(f"維運工具缺少保護：{phrase}")
    for forbidden in ("requests", "playwright", "selenium", "Authorization: Bearer", "wrangler rollback"):
        if forbidden in script:
            raise ValidationError(f"維運工具不得直接處理第三方執行、憑證或遠端回復：{forbidden}")
    default = json.loads((skill / "assets/default-operations.json").read_text(encoding="utf-8"))
    if default.get("status") != "not_configured" or default.get("public_url") is not None:
        raise ValidationError("維運預設值不得假設公開網址")
    if default.get("health", {}).get("enabled") is not False:
        raise ValidationError("維運預設值不得自動啟用監控")
    updates = default.get("updates", {})
    if updates.get("automatic_apply") is not False or updates.get("verified_backup_required") is not True:
        raise ValidationError("維運預設值必須禁止自動更新並要求可驗證備份")


def validate_content_skill(skill: Path) -> None:
    """確認 website-content-writing 的契約、事實邊界與範本文案層。"""

    if parse_skill_name(skill / "SKILL.md") != "website-content-writing":
        raise ValidationError("文案技能名稱不符")
    for name in ("agents/openai.yaml", "scripts/content_writer.py", "references/writing-rules.md", "references/copy-contract.md", "references/user-posts.md", "assets/field-guide.json"):
        if not (skill / name).is_file():
            raise ValidationError(f"文案技能缺少 {name}")
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    for phrase in ("user_fact", "ai_suggestion", "批次確認", "不編造", "--confirm-write", "命令旗標不是對話核准", "sync", "website/copy.json", "執行錯誤最小回填", "停止邊界", "不部署", "guide", "已選頁面", "user-posts.md"):
        if phrase not in text:
            raise ValidationError(f"文案技能契約缺少：{phrase}")
    if "初始文章" in text or "initial-posts" in text:
        raise ValidationError("文案技能不得再承諾撰寫初始文章")
    guide = json.loads((skill / "assets/field-guide.json").read_text(encoding="utf-8"))
    required = [f["path"] for f in guide["fields"] if f["required"]]
    if set(required) != {"home.title", "home.lead", "about.intro", "about.sections", "contact.intro"}:
        raise ValidationError(f"欄位指南必填集合不符：{required}")
    for field in guide["fields"]:
        for key in ("label", "purpose", "length", "example", "tip"):
            if not field.get(key):
                raise ValidationError(f"欄位指南 {field['path']} 缺少 {key}")
    if "Mermaid" not in text:
        raise ValidationError("多階段技能必須要求以 Mermaid 呈現流程")
    script = (skill / "scripts/content_writer.py").read_text(encoding="utf-8")
    for phrase in ("unverified_number", "placeholder_source", "required_missing", "FABRICATION_HINTS", "--confirm-write", "reject_secrets", "command_guide"):
        if phrase not in script:
            raise ValidationError(f"文案工具缺少保護：{phrase}")
    template = ROOT / "template"
    if not (template / "site.copy.mjs").is_file() or not (template / "src/site-copy.d.ts").is_file():
        raise ValidationError("範本缺少文案層 site.copy.mjs 或型別")
    for page in ("about", "services", "contact", "404"):
        if "site.copy.mjs" not in (template / f"src/pages/{page}.astro").read_text(encoding="utf-8"):
            raise ValidationError(f"共用頁面 {page} 未讀取文案層")
    for path in sorted((template / "src/themes").glob("*/Home.astro")):
        # 結尾標題可以放在首頁或頁尾（有些主題把結尾邀請設計在頁尾）
        home = path.read_text(encoding="utf-8") + (path.parent / "Footer.astro").read_text(encoding="utf-8")
        if "copy.home.title ??" not in home or "copy.home.primary_cta ??" not in home or "copy.home.closing_heading ??" not in home:
            raise ValidationError(f"主題首頁未讀取文案層：{path.parent.name}")
    scaffold = (ROOT / "skills/website-build/scripts/scaffold_site.py").read_text(encoding="utf-8")
    if "apply_copy_layer" not in scaffold:
        raise ValidationError("scaffold 未套用工作區文案層")


def validate_public_boundary() -> None:
    """掃描公開文字中的私人路徑、來源名稱與常見秘密。"""

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts:
            continue
        if path.suffix.lower() in BINARY_ALLOWED_SUFFIXES:
            allowed_dirs = ("template/public", "skills/website-design-preview/assets/previews/images")
            relative = path.relative_to(ROOT).as_posix()
            if not relative.startswith(allowed_dirs):
                raise ValidationError(f"二進位檔只允許放在範本 public 或預覽照片目錄：{relative}")
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
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


def validate_relative_links() -> None:
    """檢查 Markdown 的相對連結都指向存在的檔案。"""

    for path in ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text):
            target = match.group(1)
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (path.parent / target).exists():
                raise ValidationError(f"相對連結失效：{path} -> {target}")


def validate_python_sources() -> None:
    """以記憶體編譯 Python，避免在來源目錄產生快取。"""

    for path in ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")


def validate_json_sources() -> None:
    """確認公開 JSON 與 schema 都可由標準解析器讀取。"""

    for path in ROOT.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValidationError(f"JSON 無法解析：{path}: {error}") from error


def main() -> int:
    """執行全部靜態檢查。"""

    try:
        manifest = read_manifest()
        validate_manifest(manifest)
        validate_skill_structure()
        validate_public_boundary()
        validate_relative_links()
        validate_python_sources()
        validate_json_sources()
    except (ValidationError, OSError, ValueError, KeyError, tomllib.TOMLDecodeError) as error:
        print(f"驗證失敗：{error}", file=sys.stderr)
        return 1
    print("靜態結構、技能契約、公開邊界、相對連結、Python 語法與 JSON 解析驗證通過。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
