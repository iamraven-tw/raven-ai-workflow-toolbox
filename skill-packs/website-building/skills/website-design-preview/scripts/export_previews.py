#!/usr/bin/env python3
"""維護者用：用 Node 把範本以六個主題各建一次，匯出成單檔 HTML 預覽，供畫廊離線展示。"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = SKILL_ROOT.parents[1]
TEMPLATE = PACKAGE_ROOT / "template"
PREVIEWS = SKILL_ROOT / "assets" / "previews"
CHECK_SITE = PACKAGE_ROOT / "skills" / "website-build" / "scripts" / "check_site.py"
PAGES = {"home": "index.html", "post": "blog/hello-world/index.html", "blog": "blog/index.html"}
EXCLUDES = shutil.ignore_patterns("node_modules", "dist", ".astro", ".DS_Store")


def themes() -> list[dict]:
    """讀取範本內所有主題描述檔。"""

    found = []
    for path in sorted((TEMPLATE / "src" / "themes").glob("*/theme.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["id"] != path.parent.name:
            raise SystemExit(f"主題 id 與目錄不一致：{path}")
        found.append(payload)
    return sorted(found, key=lambda item: item["order"])


def set_theme(site_config: Path, theme_id: str) -> None:
    """改寫 site.config.mjs 的 theme 欄位。"""

    text = site_config.read_text(encoding="utf-8")
    updated, count = re.subn(r"theme: '[a-z0-9-]+'", f"theme: '{theme_id}'", text)
    if count != 1:
        raise SystemExit("site.config.mjs 找不到唯一的 theme 欄位")
    site_config.write_text(updated, encoding="utf-8")


def inline_assets(html: str, dist: Path) -> str:
    """把 dist 內的 CSS、模組腳本與圖片內嵌成單檔。"""

    def read(relative: str) -> Path | None:
        target = dist / relative.lstrip("/")
        return target if target.is_file() else None

    def css_repl(match: re.Match[str]) -> str:
        target = read(match.group(1))
        return f"<style>{target.read_text(encoding='utf-8')}</style>" if target else match.group(0)

    html = re.sub(r'<link rel="stylesheet" href="(/_astro/[^"]+\.css)">', css_repl, html)

    def js_repl(match: re.Match[str]) -> str:
        target = read(match.group(1))
        return f"<script type=\"module\">{target.read_text(encoding='utf-8')}</script>" if target else match.group(0)

    html = re.sub(r'<script type="module" src="(/_astro/[^"]+\.js)"></script>', js_repl, html)

    def img_repl(match: re.Match[str]) -> str:
        target = read(match.group(2))
        if not target:
            return match.group(0)
        mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        data = base64.b64encode(target.read_bytes()).decode("ascii")
        return f'{match.group(1)}="data:{mime};base64,{data}"'

    # 示範照片不內嵌（會讓每份預覽膨脹超過 1MB），改成指向預覽目錄旁的共用副本
    html = re.sub(r'(src|href)="/images/samples/([^"]+)"', r'\1="../images/samples/\2"', html)
    html = re.sub(r'(src|href)="(/images/[^"]+|/favicon\.svg|/apple-touch-icon\.png)"', img_repl, html)
    # 內部連結指回畫廊，避免預覽裡點到不存在的頁面
    html = re.sub(r'href="/(?!http)[^"#]*"', 'href="#"', html)
    return html


def main() -> int:
    parser = argparse.ArgumentParser(description="匯出六個主題的離線預覽")
    parser.add_argument("--only", default=None, help="只匯出單一主題 id")
    parser.add_argument("--keep", action="store_true", help="保留暫存建置目錄")
    args = parser.parse_args()

    selected = [theme for theme in themes() if args.only in (None, theme["id"])]
    if not selected:
        raise SystemExit("找不到指定主題")
    work = Path(tempfile.mkdtemp(prefix="website-preview-export-"))
    site_dir = work / "site"
    shutil.copytree(TEMPLATE, site_dir, ignore=EXCLUDES)
    print(f"[export] 暫存目錄 {site_dir}", file=sys.stderr)
    install = subprocess.run(["npm", "ci", "--no-audit", "--no-fund"], cwd=site_dir, capture_output=True, text=True)
    if install.returncode != 0:
        print(install.stderr[-3000:], file=sys.stderr)
        raise SystemExit("npm ci 失敗")

    samples_src = TEMPLATE / "public" / "images" / "samples"
    samples_dst = PREVIEWS / "images" / "samples"
    if samples_dst.exists():
        shutil.rmtree(samples_dst)
    shutil.copytree(samples_src, samples_dst)
    manifest = {"exported_at": datetime.now(UTC).replace(microsecond=0).isoformat(), "template_theme_count": len(themes()), "sample_photos": sorted(path.name for path in samples_dst.glob("*.jpg")), "themes": []}
    for theme in selected:
        set_theme(site_dir / "site.config.mjs", theme["id"])
        build = subprocess.run(["npm", "run", "build"], cwd=site_dir, capture_output=True, text=True)
        if build.returncode != 0:
            print(build.stdout[-3000:] + build.stderr[-3000:], file=sys.stderr)
            raise SystemExit(f"主題 {theme['id']} 建置失敗")
        dist = site_dir / "dist"
        check = subprocess.run(["python3", str(CHECK_SITE), "--dist", str(dist)], capture_output=True, text=True)
        if check.returncode != 0:
            print(check.stdout[-3000:], file=sys.stderr)
            raise SystemExit(f"主題 {theme['id']} 未通過 check_site")
        out_dir = PREVIEWS / theme["id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        record = {"id": theme["id"], "name": theme["name"], "tonality": theme["tonality"], "pages": {}}
        for key, relative in PAGES.items():
            html = inline_assets((dist / relative).read_text(encoding="utf-8"), dist)
            target = out_dir / f"{key}.html"
            target.write_text(html, encoding="utf-8")
            record["pages"][key] = {"file": f"{theme['id']}/{key}.html", "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "bytes": target.stat().st_size}
        manifest["themes"].append(record)
        print(f"[export] {theme['id']} 完成", file=sys.stderr)
        shutil.rmtree(dist)
    (PREVIEWS / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.keep:
        shutil.rmtree(work)
    print(json.dumps({"result": "exported", "themes": [t["id"] for t in selected], "previews": str(PREVIEWS)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
