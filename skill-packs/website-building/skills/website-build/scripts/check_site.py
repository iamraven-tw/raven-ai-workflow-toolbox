#!/usr/bin/env python3
"""檢查 astro build 產出的 dist/：必要頁面、meta、內部連結、圖片與收錄狀態。只用標準函式庫。"""

from __future__ import annotations

import argparse
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


REQUIRED_HTML = {
    "home": "index.html",
    "about": "about/index.html",
    "services": "services/index.html",
    "blog": "blog/index.html",
    "contact": "contact/index.html",
    "not_found": "404.html",
}
OPTIONAL_HTML = {
    "portfolio": "portfolio/index.html",
    "case_studies": "case-studies/index.html",
    "pricing": "pricing/index.html",
    "faq": "faq/index.html",
    "newsletter": "newsletter/index.html",
}
REQUIRED_FILES = ("rss.xml", "sitemap-index.xml", "favicon.svg", "og-image.png", "apple-touch-icon.png")
REQUIRED_META = ("description", "robots")
REQUIRED_OG = ("og:title", "og:description", "og:image")


class PageParser(HTMLParser):
    """收集單一頁面的標題、meta、連結與圖片。"""

    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.meta: dict[str, str] = {}
        self.links: list[str] = []
        self.images: list[str] = []
        self.h1_count = 0
        self.lang = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag == "html":
            self.lang = attributes.get("lang", "")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = attributes.get("name") or attributes.get("property")
            if key:
                self.meta[key] = attributes.get("content", "")
        elif tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])
        elif tag == "img" and attributes.get("src"):
            self.images.append(attributes["src"])
            if "alt" not in attributes:
                self.images.append("__missing_alt__:" + attributes["src"])
        elif tag == "h1":
            self.h1_count += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def resolve_internal(dist: Path, target: str) -> bool:
    """內部路徑是否對應到 dist 中的檔案。"""

    path = urlsplit(target).path
    if not path.startswith("/"):
        return True
    relative = path.lstrip("/")
    candidates = [dist / relative, dist / relative / "index.html"]
    if relative.endswith("/"):
        candidates.append(dist / relative.rstrip("/") / "index.html")
    if relative and not relative.endswith("/") and "." not in Path(relative).name:
        candidates.append(dist / (relative + ".html"))
    if relative == "":
        candidates.append(dist / "index.html")
    return any(candidate.is_file() for candidate in candidates)


def check(dist: Path, config: dict[str, Any] | None, expected_indexing: str) -> dict[str, Any]:
    """執行全部檢查並回傳結構化結果。"""

    findings: list[dict[str, str]] = []

    def fail(kind: str, detail: str) -> None:
        findings.append({"kind": kind, "detail": detail})

    if not dist.is_dir():
        return {"result": "failed", "findings": [{"kind": "dist_missing", "detail": str(dist)}]}

    expected_pages = dict(REQUIRED_HTML)
    optional = config.get("pages", {}).get("optional", []) if config else []
    for page in optional:
        if page in OPTIONAL_HTML:
            expected_pages[page] = OPTIONAL_HTML[page]
    for page, relative in expected_pages.items():
        if not (dist / relative).is_file():
            fail("missing_page", f"{page}: {relative}")
    for relative in REQUIRED_FILES:
        if not (dist / relative).is_file():
            fail("missing_file", relative)

    expected_robots = "index, follow" if expected_indexing == "index" else "noindex, nofollow"
    pages_checked = 0
    for html_file in sorted(dist.rglob("*.html")):
        parser = PageParser()
        parser.feed(html_file.read_text(encoding="utf-8", errors="replace"))
        pages_checked += 1
        label = html_file.relative_to(dist).as_posix()
        if not parser.title.strip():
            fail("missing_title", label)
        if not parser.lang:
            fail("missing_lang", label)
        for key in REQUIRED_META:
            if not parser.meta.get(key):
                fail("missing_meta", f"{label}: {key}")
        for key in REQUIRED_OG:
            if not parser.meta.get(key):
                fail("missing_og", f"{label}: {key}")
        if parser.meta.get("robots") and parser.meta["robots"] != expected_robots:
            fail("robots_mismatch", f"{label}: {parser.meta['robots']} (expected {expected_robots})")
        if parser.h1_count != 1:
            fail("h1_count", f"{label}: {parser.h1_count}")
        for href in parser.links:
            if href.startswith(("http://", "https://", "mailto:", "tel:", "#")):
                continue
            if not resolve_internal(dist, href):
                fail("broken_link", f"{label}: {href}")
        for src in parser.images:
            if src.startswith("__missing_alt__:"):
                fail("missing_alt", f"{label}: {src.split(':', 1)[1]}")
                continue
            if src.startswith(("http://", "https://", "data:")):
                continue
            if not resolve_internal(dist, src):
                fail("missing_image", f"{label}: {src}")

    return {
        "result": "passed" if not findings else "failed",
        "dist": str(dist),
        "pages_checked": pages_checked,
        "expected_indexing": expected_indexing,
        "findings": findings,
        "not_covered": ["screenshots", "responsive_layout", "javascript_runtime", "remote_deploy"],
    }


def main() -> int:
    """解析參數並輸出 JSON。"""

    parser = argparse.ArgumentParser(description="檢查 dist/ 靜態輸出")
    parser.add_argument("--dist", required=True)
    parser.add_argument("--config", default=None)
    parser.add_argument("--expected-indexing", choices=("noindex", "index"), default="noindex")
    args = parser.parse_args()
    config: dict[str, Any] | None = None
    if args.config:
        try:
            config = json.loads(Path(args.config).expanduser().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            print(json.dumps({"result": "stopped", "error": f"無法讀取設定：{error}"}, ensure_ascii=False), file=sys.stderr)
            return 2
    result = check(Path(args.dist).expanduser(), config, args.expected_indexing)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
