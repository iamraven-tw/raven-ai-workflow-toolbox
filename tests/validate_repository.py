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
PRIVATE_PATTERNS = (
    "/" + "Users/",
    "taiwan" + "kaiyuan",
    "macmini" + "/newsletter",
)
TEXT_SUFFIXES = {".md", ".toml", ".py", ".txt", ".yaml", ".yml"}


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


def iter_public_text_files() -> list[Path]:
    """列出需要驗證的公開文字檔，排除 Git 與本機暫存。"""

    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
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
    """確認公開文字檔沒有維護者私人路徑。"""

    for path in files:
        text = path.read_text(encoding="utf-8")
        for pattern in PRIVATE_PATTERNS:
            if pattern in text:
                raise ValidationError(f"發現私人或本機資訊：{path} -> {pattern}")


def validate_no_public_symlinks() -> None:
    """公開套件必須包含實體檔案，不能依賴維護者本機 symlink。"""

    symlinks = [
        path
        for path in ROOT.rglob("*")
        if path.is_symlink() and ".git" not in path.relative_to(ROOT).parts
    ]
    if symlinks:
        raise ValidationError(f"公開核心含 symlink：{symlinks}")


def main() -> int:
    """執行全部 repository 驗證。"""

    try:
        manifest = read_manifest()
        validate_manifest_and_skills(manifest)
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
        "驗證通過：manifest、五個技能、工作區範本、Markdown、相對連結、"
        "隱私邊界與 symlink 檢查均正常。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
