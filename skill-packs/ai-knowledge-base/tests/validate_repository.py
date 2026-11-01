#!/usr/bin/env python3
"""驗證 My Real Second Brain 公開核心的結構、技能與隱私邊界。"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = {
    "my-real-second-brain-setup",
    "solopreneur-profile",
    "book-notes",
    "knowledge-source-retrieval",
    "socratic-dialogue",
}
EXPECTED_REGISTRATIONS = {
    "agents_workspace": "<workspace>/.agents/skills",
    "claude_workspace": "<workspace>/.claude/skills",
    "codex_user": "$HOME/.agents/skills",
    "claude_user": "$HOME/.claude/skills",
    "antigravity_desktop_user": "$HOME/.gemini/config/skills",
    "antigravity_cli_user": "$HOME/.gemini/antigravity-cli/skills",
}
# 有外部套件 pin 的 Provider；本地 RAG 是自有腳本加上 C 級元件，另外檢查
EXPECTED_PROVIDERS = {
    "graphify": {
        "package_spec": "graphifyy",
        "version": "latest",
        "tested_version": "0.9.35",
        "upstream_tag": "v0.9.35",
        "upstream_commit": "9f25a3aaa1050913c2d8a1b9f0b0f0ed18296abd",
        "license_spdx": "Apache-2.0",
        "latest_observed": "0.9.99",
    },
}
EXPECTED_PROVIDER_IDS = {"graphify", "local_rag"}
EXPECTED_RAG_COMPONENTS = {"ollama", "qwen3-embedding-4b", "rag-python-packages"}
EXPECTED_RAG_PACKAGES = ["lancedb", "pyarrow", "jieba", "pypdf", "requests"]
RAG_SCRIPTS = ("common.py", "ingest.py", "query.py")
PRIVATE_PATTERNS = (
    "/" + "Users/",
    "/" + "home/",
    "C:\\" + "Users\\",
)
TEXT_SUFFIXES = {".md", ".toml", ".py", ".txt", ".yaml", ".yml"}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])",
    re.IGNORECASE,
)
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\bya29\.[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(
        r"https?://[^\s)>]+[?&](?:token|api_key|key|auth|code)=[^&\s)>]+",
        re.IGNORECASE,
    ),
)


class ValidationError(Exception):
    """代表可由維護者修正的 repository 驗證錯誤。"""


def read_manifest() -> dict:
    """讀取安裝 manifest。"""

    manifest_path = ROOT / "install.manifest.toml"
    with manifest_path.open("rb") as file:
        return tomllib.load(file)


def parse_skill_name(skill_file: Path) -> str:
    """從 SKILL.md frontmatter 取得技能名稱。"""

    text = skill_file.read_text(encoding="utf-8")
    match = re.match(r"^---\n(?P<frontmatter>.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise ValidationError(f"缺少有效 frontmatter：{skill_file}")

    name_match = re.search(
        r"^name:\s*[\"']?(?P<name>[a-z0-9-]+)[\"']?\s*$",
        match.group("frontmatter"),
        re.MULTILINE,
    )
    if not name_match:
        raise ValidationError(f"frontmatter 缺少 name：{skill_file}")
    return name_match.group("name")


def validate_manifest_and_skills(manifest: dict) -> None:
    """確認 manifest 與技能目錄互相一致。"""

    skills = manifest.get("skills", [])
    ids = [item["id"] for item in skills]
    if set(ids) != EXPECTED_SKILLS:
        raise ValidationError(
            f"manifest 技能集合不符：預期 {sorted(EXPECTED_SKILLS)}，實際 {sorted(ids)}"
        )
    if len(ids) != len(set(ids)):
        raise ValidationError("manifest 出現重複技能 ID")

    skill_root = ROOT / "skills"
    actual_skill_dirs = {
        path.name
        for path in skill_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    }
    if actual_skill_dirs != EXPECTED_SKILLS:
        raise ValidationError(
            f"技能目錄必須恰好是五個既有技能：{sorted(actual_skill_dirs)}"
        )

    orders = [item["install_order"] for item in skills]
    if len(orders) != len(set(orders)) or orders != sorted(orders):
        raise ValidationError("技能 install_order 必須唯一且遞增")

    for item in skills:
        skill_dir = ROOT / item["source_path"]
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            raise ValidationError(f"找不到必要技能：{skill_file}")
        if parse_skill_name(skill_file) != item["id"]:
            raise ValidationError(f"技能名稱與 manifest 不一致：{skill_file}")


def validate_manifest_contract(manifest: dict) -> None:
    """確認安裝狀態、登錄路徑、生命週期與 Provider pin 可機器判讀。"""

    if manifest.get("status") != "ready_for_external_acceptance":
        raise ValidationError("manifest 狀態必須是 ready_for_external_acceptance")
    if manifest.get("installable") is not True:
        raise ValidationError("可供外部驗收候選版必須明確標示 installable = true")
    if manifest.get("support_level") != "installable_candidate_not_formally_supported":
        raise ValidationError("manifest 不得把候選版標成正式支援")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(manifest.get("checked_on", ""))):
        raise ValidationError("manifest.checked_on 必須是 ISO 日期")

    installation = manifest.get("installation", {})
    if installation.get("managed_entries") != [
        "my-real-second-brain-setup",
        "solopreneur-profile",
        "book-notes",
        "knowledge-source-retrieval",
        "socratic-dialogue",
    ]:
        raise ValidationError("installation.managed_entries 必須依責任順序列出五個技能")
    if installation.get("state_schema_version") != 1:
        raise ValidationError("installation.state_schema_version 必須明確固定")
    manager = ROOT / str(installation.get("manager", ""))
    if not manager.is_file() or manager.is_symlink():
        raise ValidationError(f"找不到實體安裝管理器：{manager}")

    registrations = manifest.get("registrations", {})
    for registration, expected_path in EXPECTED_REGISTRATIONS.items():
        data = registrations.get(registration)
        if not isinstance(data, dict) or data.get("path") != expected_path:
            raise ValidationError(f"用戶端登錄路徑不符：{registration}")

    workspace = manifest.get("workspace", {})
    if workspace.get("copy_policy") != "merge_missing_preserve_existing_stop_on_type_conflict":
        raise ValidationError("工作區模板必須只補缺少內容並在類型衝突時停止")

    providers = {item.get("id"): item for item in manifest.get("providers", [])}
    if set(providers) != EXPECTED_PROVIDER_IDS:
        raise ValidationError("Provider 集合必須恰好是 graphify 與 local_rag；NotebookLM 已不再是預設 Provider")
    for provider_id, expected in EXPECTED_PROVIDERS.items():
        provider = providers[provider_id]
        for key, value in expected.items():
            if provider.get(key) != value:
                raise ValidationError(f"Provider pin 不符：{provider_id}.{key}")
        for hash_key in ("wheel_sha256", "sdist_sha256"):
            if not SHA256_PATTERN.fullmatch(str(provider.get(hash_key, ""))):
                raise ValidationError(f"Provider 缺少有效 SHA-256：{provider_id}.{hash_key}")
        for url_key in (
            "source",
            "source_version",
            "upstream",
            "upstream_release",
            "license_url",
            "latest_source_version",
            "latest_release",
        ):
            if not str(provider.get(url_key, "")).startswith("https://"):
                raise ValidationError(f"Provider 缺少 HTTPS 官方來源：{provider_id}.{url_key}")
        if provider.get("version_decision") != "install_latest_per_adr_0006_tested_version_recorded_for_reference":
            raise ValidationError(f"Provider 版本決策必須是 ADR 0006 的 latest 政策：{provider_id}")
        if provider.get("tier") != "C" or provider.get("version_policy") != "latest" or provider.get("external_source_notice") != "standard":
            raise ValidationError(f"Provider 必須標示 C 級、latest 與標準外部來源提醒：{provider_id}")
    for provider_id, provider in providers.items():
        if provider.get("replaceable") is not True:
            raise ValidationError(f"Provider 必須保持可替換：{provider_id}")
        if "candidate" not in str(provider.get("support_status", "")):
            raise ValidationError(f"Provider 不得被標成正式支援：{provider_id}")
    validate_local_rag(manifest, providers["local_rag"])

    mutation_steps = {
        "confirm_changes",
        "install_self_skills",
        "initialize_workspace",
        "install_provider_packages",
        "install_provider_skills",
        "install_local_rag",
    }
    install_steps = manifest.get("install_steps", [])
    orders = [item.get("order") for item in install_steps]
    if len(orders) != len(set(orders)) or orders != sorted(orders):
        raise ValidationError("install_steps.order 必須唯一且遞增")
    steps_by_id = {item.get("id"): item for item in install_steps}
    for step_id in mutation_steps:
        if steps_by_id.get(step_id, {}).get("requires_confirmation") is not True:
            raise ValidationError(f"會改變狀態的步驟缺少確認關卡：{step_id}")

    verification_ids = {
        item.get("id") for item in manifest.get("verification_steps", [])
    }
    required_verification = {
        "verify_self_skills",
        "verify_workspace",
        "verify_provider_versions",
        "verify_provider_skills",
        "verify_local_rag",
        "write_local_state",
    }
    if not required_verification.issubset(verification_ids):
        raise ValidationError("manifest 缺少分層驗證或非敏感狀態步驟")


def validate_local_rag(manifest: dict, rag: dict) -> None:
    """確認本地 RAG 的路徑、元件分級、資源揭露與舊 NotebookLM 升級契約。"""

    if rag.get("role") != "grounded_retrieval" or rag.get("replaces") != ["notebook"]:
        raise ValidationError("local_rag 必須是取代 notebook 的有根據檢索 Provider")
    if rag.get("requires_user_login") is not False or rag.get("uploads_user_content") is not False:
        raise ValidationError("local_rag 不得要求登入或上傳使用者內容")
    if rag.get("user_types_commands") is not False or rag.get("performed_by") != "agent":
        raise ValidationError("local_rag 必須由 Agent 完成設定，使用者不需輸入指令")
    if rag.get("embedding_model") != "qwen3-embedding:4b":
        raise ValidationError("local_rag 向量模型必須是 qwen3-embedding:4b")
    if rag.get("external_min_chars") != 6000 or rag.get("chunk_chars") != 700:
        raise ValidationError("local_rag 分流門檻必須是 6000 字、切段約 700 字")
    expected_paths = {
        "venv_path": "sources/rag/.venv",
        "index_path": "sources/rag/lancedb",
        "inbox_path": "sources/inbox",
        "external_path": "sources/external",
        "workspace_scripts_path": "sources/rag/scripts",
    }
    for key, value in expected_paths.items():
        if rag.get(key) != value:
            raise ValidationError(f"local_rag 路徑不符：{key}")
    required = manifest["workspace"]["required_directories"]
    for directory in ("sources/inbox", "sources/external", "sources/rag/scripts"):
        if directory not in required:
            raise ValidationError(f"工作區必要目錄缺少：{directory}")
    if any("notebooks" in directory for directory in required):
        raise ValidationError("新工作區範本不得再要求 Notebook 路由目錄")

    scripts = ROOT / str(rag.get("scripts_template_path", ""))
    for name in RAG_SCRIPTS:
        script = scripts / name
        if not script.is_file():
            raise ValidationError(f"缺少本地 RAG 腳本：{script}")
        try:  # 至少確認語法正確；行為由 tests/test_local_rag.py 的確定性測試驗證
            compile(script.read_text(encoding="utf-8"), str(script), "exec")
        except SyntaxError as error:
            raise ValidationError(f"本地 RAG 腳本語法錯誤：{script}：{error}") from error
    common = (scripts / "common.py").read_text(encoding="utf-8")
    if "parents[2]" not in common or "Instruct:" not in common:
        raise ValidationError("common.py 必須以 sources/ 為根目錄並保留 Qwen3 查詢前綴")
    supported = re.search(r"SUPPORTED_SUFFIXES = \{([^}]*)\}", common)
    if not supported or set(re.findall(r'"(\.[a-z]+)"', supported.group(1))) != {".md", ".markdown", ".txt", ".pdf", ".html", ".htm"}:
        raise ValidationError("common.py 必須以白名單限制匯入格式：md、markdown、txt、pdf、html、htm")
    if 'errors="replace"' in common:
        raise ValidationError("common.py 不得以 errors=\"replace\" 讀檔，亂碼會被當成內容建立索引")
    if not (Path(__file__).resolve().parent / "test_local_rag.py").is_file():
        raise ValidationError("缺少本地 RAG 行為測試 tests/test_local_rag.py")
    if scripts.relative_to(ROOT / manifest["workspace"]["template_path"]).as_posix() != "sources/rag/scripts":
        raise ValidationError("本地 RAG 腳本必須位於範本的 sources/rag/scripts/")

    components = {item.get("id"): item for item in rag.get("components", [])}
    if set(components) != EXPECTED_RAG_COMPONENTS:
        raise ValidationError(f"local_rag 元件集合不符：{sorted(components)}")
    for component_id, component in components.items():
        if component.get("tier") != "C" or component.get("version_policy") != "latest" or component.get("external_source_notice") != "standard":
            raise ValidationError(f"local_rag 元件必須標示 C 級、latest 與標準外部來源提醒：{component_id}")
        if not str(component.get("source", "")).startswith("https://"):
            raise ValidationError(f"local_rag 元件缺少 HTTPS 來源：{component_id}")
    if "brew services start ollama" not in components["ollama"].get("install_commands", []):
        raise ValidationError("Ollama 必須以 brew services 設定開機自動啟動")
    if components["rag-python-packages"].get("packages") != EXPECTED_RAG_PACKAGES:
        raise ValidationError("本地 RAG Python 套件清單不符")

    upgrade = manifest.get("upgrade_from_notebooklm", {})
    if upgrade.get("notebooklm_remote_data") != "keep_untouched":
        raise ValidationError("升級流程不得刪除使用者的 NotebookLM 資料")
    if upgrade.get("notebooklm_py_package") != "may_stay_installed_no_forced_uninstall":
        raise ValidationError("升級流程不得強制移除 notebooklm-py")
    # 舊版 .graphifyignore 的 wiki/ 必須被「取代」，只附加新行會讓 ext_*.md 仍被排除
    if upgrade.get("graphifyignore") != "preview_replace_wiki_line_and_append_missing_then_confirm":
        raise ValidationError("升級時 .graphifyignore 必須預覽後以 wiki/* 與 !wiki/ext_*.md 取代舊的 wiki/")
    if upgrade.get("graphifyignore_replace") != {"from": "wiki/", "to": ["wiki/*", "!wiki/ext_*.md"]}:
        raise ValidationError("graphifyignore_replace 必須把 wiki/ 換成 wiki/* 與 !wiki/ext_*.md")
    if upgrade.get("graphifyignore_append_missing") != ["inbox/", "external/", "rag/"]:
        raise ValidationError("graphifyignore_append_missing 必須是 inbox/、external/、rag/")
    upgrade_docs = {
        "INSTALL.md": ROOT / "INSTALL.md",
        "docs/installation.md": ROOT / "docs" / "installation.md",
        "docs/integrations/graphify.md": ROOT / "docs" / "integrations" / "graphify.md",
        "my-real-second-brain-setup": ROOT / "skills" / "my-real-second-brain-setup" / "SKILL.md",
    }
    for label, path in upgrade_docs.items():
        text = path.read_text(encoding="utf-8")
        if "`wiki/*`" not in text or "`!wiki/ext_*.md`" not in text or "取代" not in text:
            raise ValidationError(f"{label} 必須說明升級時以 wiki/* 與 !wiki/ext_*.md 取代舊的 wiki/")
        if "append_missing_lines" in text:
            raise ValidationError(f"{label} 不得只要求附加缺少的 .graphifyignore 規則")
    if "measured_reference" in rag:
        raise ValidationError("維護者實測數字不得放在 manifest 產品欄位；改放 local-rag.md 的參考紀錄")
    if "參考紀錄：維護者單機實測" not in (ROOT / "docs" / "integrations" / "local-rag.md").read_text(encoding="utf-8"):
        raise ValidationError("local-rag.md 缺少標示清楚的維護者實測參考紀錄")

    template_root = ROOT / manifest["workspace"]["template_path"] / "sources"
    ignore_lines = (template_root / ".graphifyignore").read_text(encoding="utf-8").splitlines()
    for line in ("inbox/", "external/", "rag/", "wiki/*", "!wiki/ext_*.md"):
        if line not in ignore_lines:
            raise ValidationError(f".graphifyignore 缺少規則：{line}")
    if "wiki/" in ignore_lines:
        raise ValidationError(".graphifyignore 不得整個排除 wiki/，否則 ext_*.md 摘要頁不會進圖譜")
    gitignore_lines = (template_root / ".gitignore").read_text(encoding="utf-8").splitlines()
    for line in ("rag/.venv/", "rag/lancedb/"):
        if line not in gitignore_lines:
            raise ValidationError(f"工作區 .gitignore 缺少：{line}")
    inbox_files = [path.name for path in (template_root / "inbox").iterdir()]
    if inbox_files != [".gitkeep"]:
        raise ValidationError("範本 inbox/ 只能有 .gitkeep，其他檔案會被當成待匯入資料")


def validate_workspace_template(manifest: dict) -> None:
    """確認公開範本具備 manifest 宣告的核心路徑。"""

    template_root = ROOT / manifest["workspace"]["template_path"]
    for relative in manifest["workspace"]["required_directories"]:
        expected = template_root / relative
        if not expected.is_dir():
            raise ValidationError(f"範本缺少必要目錄：{expected}")

    profile = template_root / "sources/strategy/solopreneur-profile.md"
    profile_text = profile.read_text(encoding="utf-8")
    if "status: not_configured" not in profile_text:
        raise ValidationError("公開一人公司設定範本必須保持 not_configured")

    social_strategy = (
        template_root / "sources/strategy/social-media-strategy-and-insights.md"
    )
    social_strategy_text = social_strategy.read_text(encoding="utf-8")
    if "status: not_configured" not in social_strategy_text:
        raise ValidationError("公開社群媒體策略與洞察範本必須保持 not_configured")
    for required in ("每週", "每月", "每季", "每年", "使用者補充或修正"):
        if required not in social_strategy_text:
            raise ValidationError(f"公開社群媒體策略範本缺少必要欄位：{required}")

    validate_client_instruction_files(template_root, "工作區範本")


def validate_client_instruction_files(root: Path, label: str) -> None:
    """確認 Codex、Claude 與 Antigravity 都能載入同一份專案規則。"""

    agents = root / "AGENTS.md"
    claude = root / "CLAUDE.md"
    if not agents.is_file():
        raise ValidationError(f"{label} 缺少 AGENTS.md：{agents}")
    if not claude.is_file():
        raise ValidationError(f"{label} 缺少 CLAUDE.md：{claude}")
    if "@AGENTS.md" not in claude.read_text(encoding="utf-8"):
        raise ValidationError(f"{label} 的 CLAUDE.md 未匯入 AGENTS.md：{claude}")


def iter_public_text_files() -> list[Path]:
    """列出需要驗證的公開文字檔，排除 Git 與本機暫存。"""

    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or (
            path.suffix not in TEXT_SUFFIXES and path.name not in {"LICENSE", "NOTICE"}
        ):
            continue
        relative = path.relative_to(ROOT)
        if relative.parts[0] in {".git", ".local"}:
            continue
        files.append(path)
    return files


def validate_markdown_fences(files: list[Path]) -> None:
    """確認 Markdown 程式碼區塊成對出現。"""

    for path in files:
        if path.suffix != ".md":
            continue
        fence_count = sum(
            1
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.lstrip().startswith("```")
        )
        if fence_count % 2:
            raise ValidationError(f"Markdown fence 未成對：{path}")


def validate_relative_links(files: list[Path]) -> None:
    """確認 repository 內的相對 Markdown 連結存在。"""

    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in files:
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        for target in link_pattern.findall(text):
            clean = target.strip().strip("<>").split("#", 1)[0]
            if not clean or re.match(r"^[a-z]+://", clean) or clean.startswith("mailto:"):
                continue
            resolved = (path.parent / clean).resolve()
            if not resolved.exists():
                raise ValidationError(f"失效相對連結：{path} -> {target}")


def validate_privacy(files: list[Path]) -> None:
    """確認公開文字檔沒有私人路徑、真實信箱或常見憑證值。"""

    for path in files:
        text = path.read_text(encoding="utf-8")
        for pattern in PRIVATE_PATTERNS:
            if pattern in text:
                raise ValidationError(f"發現私人或本機資訊：{path} -> {pattern}")
        emails = [
            email
            for email in EMAIL_PATTERN.findall(text)
            if not email.endswith("@example.invalid")
        ]
        if emails:
            raise ValidationError(f"發現公開候選版不應包含的電子郵件：{path}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise ValidationError(f"發現疑似憑證或含秘密參數的網址：{path}")


def validate_no_public_symlinks() -> None:
    """公開套件必須包含實體檔案，不能依賴維護者本機 symlink。"""

    symlinks = [
        path
        for path in ROOT.rglob("*")
        if path.is_symlink()
        and not {".git", ".local"}.intersection(path.relative_to(ROOT).parts)
    ]
    if symlinks:
        raise ValidationError(f"公開核心含 symlink：{symlinks}")


def main() -> int:
    """執行全部 repository 驗證。"""

    try:
        manifest = read_manifest()
        validate_manifest_and_skills(manifest)
        validate_manifest_contract(manifest)
        validate_client_instruction_files(ROOT, "repository 根目錄")
        validate_workspace_template(manifest)
        files = iter_public_text_files()
        validate_markdown_fences(files)
        validate_relative_links(files)
        validate_privacy(files)
        validate_no_public_symlinks()
    except (OSError, KeyError, tomllib.TOMLDecodeError, ValidationError) as error:
        print(f"驗證失敗：{error}", file=sys.stderr)
        return 1

    print(
        "驗證通過：manifest 生命週期與固定版本、本地 RAG 契約、五個技能、用戶端登錄、"
        "工作區範本、Markdown、相對連結、隱私邊界與 symlink 檢查均正常。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
