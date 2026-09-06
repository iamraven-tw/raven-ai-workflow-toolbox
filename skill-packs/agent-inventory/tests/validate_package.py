#!/usr/bin/env python3
"""驗證 agent-inventory 技能包的靜態結構、固定來源、公開邊界與相對連結。"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "README.md",
    "INSTALL.md",
    "AGENTS.md",
    "CLAUDE.md",
    "THIRD_PARTY_NOTICES.md",
    "install.manifest.toml",
    "scripts/manage_install.py",
    "tests/test_install_lifecycle.py",
    "docs/architecture.md",
    "docs/data-and-privacy-boundaries.md",
    "docs/client-compatibility.md",
)
UPSTREAM_SKILLS = (
    "inventory",
    "inventory-setup",
    "inventory-scan",
    "inventory-summarize",
    "inventory-flow",
    "inventory-serve",
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
TEXT_SUFFIXES = {".md", ".py", ".toml", ".json", ".yaml", ".yml"}
# 這些字串本身不能整段出現在原始碼裡，否則驗證器會掃到自己，因此拆開後再組合。
FORBIDDEN_SUBSTRINGS = (
    "/User" + "s/",
    "/Volume" + "s/Workspace",
    "op" + "://",
    "ghp" + "_",
    "sk" + "-",
    "xoxb" + "-",
    "AKI" + "A",
)
SECRET_KEY_PATTERN = re.compile(
    r"\b(api[_-]?key|secret|password|access[_-]?token|refresh[_-]?token)\b\s*[:=]\s*[\"'][^\"']+[\"']",
    re.IGNORECASE,
)


class ValidationError(RuntimeError):
    """代表套件不符合公開發行條件。"""


def load_manifest() -> dict:
    """讀取並檢查 manifest 的基本欄位。"""

    manifest = tomllib.loads((ROOT / "install.manifest.toml").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValidationError("manifest schema_version 必須是 1")
    if manifest.get("manifest_type") != "agent-inventory-install":
        raise ValidationError("manifest_type 不符")
    if manifest.get("support_level") != "installable_candidate_not_formally_supported":
        raise ValidationError("manifest 沒有正確區分候選安裝與正式支援")
    if manifest.get("installable") is not True:
        raise ValidationError("manifest 未標示可安裝")
    return manifest


def validate_files() -> None:
    """確認必要檔案存在，且沒有把上游原始碼複製進來。"""

    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    if missing:
        raise ValidationError("套件缺少必要檔案：" + ", ".join(missing))
    for vendored in ("skills", "bin", "adapters", "site", "data", ".agents"):
        if (ROOT / vendored).exists():
            raise ValidationError(f"本套件不得包含上游原始碼或自有技能目錄：{vendored}")
    for path in ROOT.rglob("*"):
        if path.is_symlink():
            raise ValidationError(f"套件不得包含 symlink：{path.relative_to(ROOT)}")


def validate_pinned_source(manifest: dict) -> None:
    """確認上游鎖定 tag、完整 commit、tree 與授權雜湊。"""

    integration = manifest.get("integration", {}).get("agent_inventory", {})
    if integration.get("repository") != "https://github.com/iamraven-tw/agent-inventory":
        raise ValidationError("上游 repository 網址不符")
    if not str(integration.get("tag", "")).startswith("v"):
        raise ValidationError("上游必須鎖定 tag")
    for key, pattern, label in (
        ("ref", HEX40, "commit"),
        ("tree", HEX40, "tree"),
        ("license_sha256", HEX64, "LICENSE SHA-256"),
    ):
        value = str(integration.get(key, ""))
        if not pattern.match(value):
            raise ValidationError(f"上游 {label} 不是完整雜湊：{value!r}")
    if integration.get("license") != "MIT":
        raise ValidationError("上游授權必須記錄為 MIT")
    if integration.get("vendor_source") is not False:
        raise ValidationError("vendor_source 必須為 false")
    if integration.get("auto_update") is not False:
        raise ValidationError("auto_update 必須為 false")

    dependencies = manifest.get("dependencies", [])
    upstream = next((item for item in dependencies if item.get("id") == "agent-inventory"), None)
    if upstream is None:
        raise ValidationError("dependencies 缺少 agent-inventory")
    if upstream.get("bundle_source") is not False:
        raise ValidationError("agent-inventory 不得綑綁進本 repository")
    if upstream.get("ref") != integration.get("ref"):
        raise ValidationError("dependencies 與 integration 的 ref 不一致")


def validate_entries(manifest: dict) -> None:
    """確認受管理入口與上游技能清單一致。"""

    managed = manifest.get("installation", {}).get("managed_entries", [])
    sources = manifest.get("managed_sources", {}).get("upstream_skills", [])
    if sorted(managed) != sorted(UPSTREAM_SKILLS):
        raise ValidationError(f"managed_entries 與預期的六個上游技能不符：{managed}")
    if sorted(sources) != sorted(UPSTREAM_SKILLS):
        raise ValidationError(f"upstream_skills 與預期的六個上游技能不符：{sources}")
    if manifest.get("installation", {}).get("manager_network_access") is not False:
        raise ValidationError("安裝管理器不得宣告需要網路")
    if manifest.get("installation", {}).get("modifies_user_rules_or_skills") is not False:
        raise ValidationError("安裝器不得宣告會修改使用者規則或技能")


def validate_boundaries(manifest: dict) -> None:
    """確認人類授權關卡、隱私宣告、已知限制與驗收關卡都有記錄。"""

    gates = manifest.get("human_authorization_gates", {})
    for key in (
        "clone_upstream_repository",
        "scan_scope_selection",
        "summary_generation_reads_rule_contents",
        "delete_rule_or_skill_to_trash",
        "overwrite_rule_or_skill_from_the_web_editor",
        "open_file_with_external_editor",
    ):
        if not gates.get(key):
            raise ValidationError(f"缺少人類授權關卡宣告：{key}")

    privacy = manifest.get("privacy", {})
    if privacy.get("network_during_scan") is not False:
        raise ValidationError("隱私宣告必須說明掃描不連網")
    if privacy.get("server_binding") != "127.0.0.1":
        raise ValidationError("隱私宣告必須說明網站只綁定 127.0.0.1")
    if privacy.get("uploads") != "none":
        raise ValidationError("隱私宣告必須說明不上傳任何內容")
    if "esm_sh" not in str(privacy.get("network_in_web_ui", "")):
        raise ValidationError("隱私宣告必須揭露網頁編輯器的對外請求")

    if not manifest.get("known_limitations"):
        raise ValidationError("manifest 必須記錄已知限制")
    gate_ids = {item.get("id") for item in manifest.get("readiness_gates", [])}
    for required in (
        "static_structure_and_documents",
        "upstream_pinned_and_verified",
        "install_repeat_conflict_update_rollback_remove",
        "agent_discovery",
        "end_to_end_inventory_run",
        "second_computer_acceptance",
        "formal_public_support",
    ):
        if required not in gate_ids:
            raise ValidationError(f"缺少驗收關卡：{required}")


def validate_documents(manifest: dict) -> None:
    """確認文件敘述與 manifest 一致，並揭露必要邊界。"""

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    tag = manifest["integration"]["agent_inventory"]["tag"]
    ref = manifest["integration"]["agent_inventory"]["ref"]

    for name, text, phrases in (
        ("README.md", readme, (tag, "不複製上游原始碼", "esm.sh", "127.0.0.1", "尚未正式支援")),
        ("INSTALL.md", install, (tag, ref, "--inventory-source", "不會覆寫", "絕對路徑")),
        ("THIRD_PARTY_NOTICES.md", notices, (tag, ref, "MIT", "esm.sh")),
    ):
        for phrase in phrases:
            if phrase not in text:
                raise ValidationError(f"{name} 缺少必要說明：{phrase}")
    if "Mermaid" not in readme and "```mermaid" not in readme:
        raise ValidationError("README 必須以 Mermaid 呈現盤點流程")
    if "```mermaid" not in install:
        raise ValidationError("INSTALL 必須以 Mermaid 呈現安裝流程")


def validate_links() -> None:
    """確認所有相對連結都指向存在的檔案。"""

    broken: list[str] = []
    for path in ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\[[^\]]*\]\((?!https?://|mailto:|#)([^)]+)\)", text):
            target = match.group(1).split("#")[0]
            if not target:
                continue
            if not (path.parent / target).resolve().exists():
                broken.append(f"{path.relative_to(ROOT)} -> {target}")
    if broken:
        raise ValidationError("相對連結失效：" + ", ".join(broken))


def validate_public_boundary() -> None:
    """掃描公開文字中的私人路徑與常見秘密。"""

    for path in ROOT.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        for forbidden in FORBIDDEN_SUBSTRINGS:
            if forbidden in text:
                raise ValidationError(f"{relative} 含不可公開的字串：{forbidden}")
        if SECRET_KEY_PATTERN.search(text):
            raise ValidationError(f"{relative} 疑似含硬編碼秘密")


def validate_python() -> None:
    """確認 Python 檔語法正確且只用標準函式庫。"""

    allowed_roots = {
        "argparse", "ast", "hashlib", "json", "os", "re", "shutil", "subprocess",
        "sys", "tempfile", "tomllib", "unittest", "uuid", "dataclasses",
        "datetime", "pathlib", "typing", "__future__",
    }
    for path in sorted(ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if name not in allowed_roots:
                    raise ValidationError(f"{path.relative_to(ROOT)} 匯入非標準函式庫：{name}")


def main() -> int:
    """執行全部驗證。"""

    try:
        manifest = load_manifest()
        validate_files()
        validate_pinned_source(manifest)
        validate_entries(manifest)
        validate_boundaries(manifest)
        validate_documents(manifest)
        validate_links()
        validate_public_boundary()
        validate_python()
    except ValidationError as error:
        print(f"驗證失敗：{error}", file=sys.stderr)
        return 1
    print("靜態結構、上游固定版本、公開邊界、相對連結與 Python 檢查通過。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
