#!/usr/bin/env python3
"""驗證官網打造技能包第一個技能的結構、邊界與公開內容。"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTED = {"website-setup", "website-design-preview", "website-build"}
PLANNED = {
    "website-content-writing",
    "website-deploy",
    "website-service-integration",
    "website-operations",
}
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
    """確認只把第一個完成技能列入安裝，且依賴仍是規劃狀態。"""

    expected = {
        "schema_version": 1,
        "manifest_type": "website-building-install",
        "status": "local_candidate_partial_pack",
        "installable": True,
        "requires_network": False,
        "support_level": "partial_pack_installable_candidate_not_formally_supported",
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
    for key in ("configuration_manager", "configuration_schema", "state_schema", "template_path"):
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
    for gate in ("wrangler_login", "workers_dev_deploy", "custom_domain", "second_computer_acceptance"):
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
    for tonality in ("warm_literary", "dark_immersive", "clean_minimal", "photo_showroom", "colorful_energetic", "editorial_press"):
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
    for case_number in range(1, 25):
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
    tonalities = {"warm_literary", "dark_immersive", "clean_minimal", "photo_showroom", "colorful_energetic", "editorial_press"}
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
        for key in ("name", "tonality", "order", "description", "fits", "source_guide", "source_repository", "source_license", "placeholder_colors"):
            if key not in theme:
                raise ValidationError(f"主題 {theme['id']} 缺少 {key}")
        if theme["source_license"] != "Apache-2.0" or not str(theme["source_repository"]).startswith("https://"):
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


def main() -> int:
    """執行全部靜態檢查。"""

    try:
        manifest = read_manifest()
        validate_manifest(manifest)
        validate_skill_structure()
        validate_public_boundary()
        validate_relative_links()
        validate_python_sources()
    except (ValidationError, OSError, ValueError, KeyError, tomllib.TOMLDecodeError) as error:
        print(f"驗證失敗：{error}", file=sys.stderr)
        return 1
    print("靜態結構、技能契約、公開邊界、相對連結與 Python 語法驗證通過。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
