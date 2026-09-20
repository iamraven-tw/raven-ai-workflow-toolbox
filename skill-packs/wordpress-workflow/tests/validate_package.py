#!/usr/bin/env python3
"""驗證 WordPress MCP 公開候選包的結構、安全邊界與 manifest。"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    "wordpress-mcp-workflow",
    "wordpress-customize-theme",
    "wordpress-publish-article",
}
TEXT_SUFFIXES = {".md", ".toml", ".py", ".yaml", ".yml", ".txt"}
PRIVATE_PATTERNS = (
    "/" + "Users/",
    "/" + "Volumes/",
    "C:\\" + "Users\\",
)
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bya29\.[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


class ValidationError(RuntimeError):
    """代表公開候選包可修正的驗證問題。"""


def read_manifest() -> dict:
    """讀取安裝 manifest。"""

    with (ROOT / "install.manifest.toml").open("rb") as handle:
        return tomllib.load(handle)


def parse_skill_name(skill_file: Path) -> str:
    """從技能 frontmatter 取得技能名稱。"""

    text = skill_file.read_text(encoding="utf-8")
    match = re.match(r"^---\n(?P<header>.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise ValidationError(f"缺少有效 frontmatter：{skill_file}")
    name = re.search(r"^name:\s*([a-z0-9-]+)\s*$", match.group("header"), re.MULTILINE)
    if not name:
        raise ValidationError(f"frontmatter 缺少 name：{skill_file}")
    return name.group(1)


def validate_manifest(manifest: dict) -> None:
    """確認 manifest 只列入本包的三個候選技能。"""

    expected = {
        "schema_version": 1,
        "manifest_type": "wordpress-workflow-install",
        "status": "local_candidate_full_pack",
        "installable": True,
        "requires_network": False,
        "support_level": "full_pack_installable_candidate_not_formally_supported",
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValidationError(f"manifest.{key} 不符")
    declared = {record.get("id") for record in manifest.get("skills", [])}
    managed = set(manifest.get("installation", {}).get("managed_entries", []))
    if declared != SKILLS or managed != SKILLS:
        raise ValidationError("manifest 技能集合不符")
    if manifest.get("runtime", {}).get("secrets_must_not_be_stored_in_package") is not True:
        raise ValidationError("manifest 缺少機密資料邊界")


def validate_structure() -> None:
    """確認必要文件、技能入口與安裝器存在。"""

    for relative in (
        "README.md",
        "INSTALL.md",
        "THIRD_PARTY_NOTICES.md",
        "install.manifest.toml",
        "scripts/manage_install.py",
    ):
        if not (ROOT / relative).is_file():
            raise ValidationError(f"缺少必要檔案：{relative}")
    actual = {path.name for path in (ROOT / "skills").iterdir() if path.is_dir()}
    if actual != SKILLS:
        raise ValidationError("skills 目錄與 manifest 不一致")
    for skill_id in SKILLS:
        skill_file = ROOT / "skills" / skill_id / "SKILL.md"
        if parse_skill_name(skill_file) != skill_id:
            raise ValidationError(f"技能名稱不符：{skill_id}")


def validate_public_content() -> None:
    """拒絕私人識別資料、常見秘密格式、symlink 與直接發布預設。"""

    for path in ROOT.rglob("*"):
        if path.is_symlink():
            raise ValidationError(f"公開包不得含 symlink：{path.relative_to(ROOT)}")
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in PRIVATE_PATTERNS:
            if pattern in text:
                raise ValidationError(f"發現私人識別資料：{path.relative_to(ROOT)}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise ValidationError(f"發現疑似秘密：{path.relative_to(ROOT)}")
    publish_skill = (ROOT / "skills/wordpress-publish-article/SKILL.md").read_text(
        encoding="utf-8"
    )
    if "Always use `status: publish`" in publish_skill:
        raise ValidationError("公開文章技能不得把直接發布設為固定預設")
    for phrase in ("status: draft", "status: publish", "ask one short question"):
        if phrase not in publish_skill:
            raise ValidationError(f"文章狀態邊界不完整：{phrase}")


def main() -> int:
    """執行公開包靜態驗證。"""

    try:
        validate_manifest(read_manifest())
        validate_structure()
        validate_public_content()
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, ValidationError) as error:
        print(f"驗證失敗：{error}", file=sys.stderr)
        return 1
    print("WordPress MCP 技能包靜態驗證通過：3 個技能，未發現私人識別資料或秘密格式。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
