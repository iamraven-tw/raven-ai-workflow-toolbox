#!/usr/bin/env python3
"""以手工建立的虛構 dist 驗證 check_site.py；另以環境變數選擇性執行真實 Node 建置。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "skills/website-build/scripts/check_site.py"
SCAFFOLD = ROOT / "skills/website-build/scripts/scaffold_site.py"
DEFAULT = ROOT / "skills/website-setup/assets/default-config.json"


def page(title: str, *, robots: str = "noindex, nofollow", links: tuple[str, ...] = (), images: tuple[str, ...] = (), h1: int = 1) -> str:
    """產生符合檢查條件的最小 HTML。"""

    body = "".join(f'<a href="{href}">x</a>' for href in links) + "".join(f'<img src="{src}" alt="">' for src in images)
    heading = "".join(f"<h1>{title}</h1>" for _ in range(h1))
    return (
        '<!doctype html><html lang="zh-TW"><head><meta charset="utf-8">'
        f"<title>{title}</title>"
        '<meta name="description" content="虛構描述">'
        f'<meta name="robots" content="{robots}">'
        f'<meta property="og:title" content="{title}">'
        '<meta property="og:description" content="虛構描述">'
        '<meta property="og:image" content="https://example.invalid/og-image.png">'
        f"</head><body>{heading}{body}</body></html>"
    )


class CheckSiteTests(unittest.TestCase):
    """確認檢查器對完整輸出通過，對缺頁、斷鏈與收錄錯誤失敗。"""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="fictional-website-dist-")
        self.dist = Path(self.temporary.name) / "dist"
        self.build_dist()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, content: str | bytes) -> None:
        target = self.dist / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")

    def build_dist(self) -> None:
        self.write("index.html", page("首頁", links=("/about", "/blog/hello/", "/contact"), images=("/images/placeholders/hero.svg",)))
        self.write("about/index.html", page("關於"))
        self.write("services/index.html", page("服務"))
        self.write("blog/index.html", page("文章", links=("/blog/hello/",)))
        self.write("blog/hello/index.html", page("文章一"))
        self.write("contact/index.html", page("聯絡", links=("mailto:hello@example.invalid",)))
        self.write("404.html", page("找不到", links=("/", "/blog")))
        for name in ("rss.xml", "sitemap-index.xml", "favicon.svg", "og-image.png", "apple-touch-icon.png", "images/placeholders/hero.svg"):
            self.write(name, "x")

    def run_check(self, *extra: str) -> tuple[int, dict]:
        result = subprocess.run(["python3", str(CHECK), "--dist", str(self.dist), *extra], capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def test_complete_dist_passes(self) -> None:
        code, payload = self.run_check()
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["result"], "passed")
        self.assertEqual(payload["pages_checked"], 7)
        self.assertIn("screenshots", payload["not_covered"])

    def test_missing_page_and_broken_link_fail(self) -> None:
        shutil.rmtree(self.dist / "services")
        self.write("about/index.html", page("關於", links=("/nowhere",), images=("/images/missing.png",)))
        code, payload = self.run_check()
        self.assertEqual(code, 1)
        kinds = {finding["kind"] for finding in payload["findings"]}
        self.assertEqual(kinds, {"missing_page", "broken_link", "missing_image"})

    def test_robots_h1_and_alt_are_checked(self) -> None:
        self.write("about/index.html", page("關於", robots="index, follow", h1=2).replace('alt=""', ""))
        self.write("services/index.html", page("服務", images=("/favicon.svg",)).replace(' alt=""', ""))
        code, payload = self.run_check()
        self.assertEqual(code, 1)
        kinds = {finding["kind"] for finding in payload["findings"]}
        self.assertIn("robots_mismatch", kinds)
        self.assertIn("h1_count", kinds)
        self.assertIn("missing_alt", kinds)
        code, payload = self.run_check("--expected-indexing", "index")
        self.assertIn("robots_mismatch", {finding["kind"] for finding in payload["findings"]})

    def test_optional_page_required_when_enabled(self) -> None:
        config = Path(self.temporary.name) / "config.json"
        payload = json.loads(DEFAULT.read_text(encoding="utf-8"))
        payload["pages"]["optional"] = ["faq"]
        config.write_text(json.dumps(payload), encoding="utf-8")
        code, result = self.run_check("--config", str(config))
        self.assertEqual(code, 1)
        self.assertIn({"kind": "missing_page", "detail": "faq: faq/index.html"}, result["findings"])
        self.write("faq/index.html", page("常見問題"))
        code, result = self.run_check("--config", str(config))
        self.assertEqual(code, 0, result)


@unittest.skipUnless(os.environ.get("WEBSITE_NODE_ACCEPTANCE") == "1", "需要 WEBSITE_NODE_ACCEPTANCE=1 與 Node.js")
class NodeBuildAcceptanceTests(unittest.TestCase):
    """選擇性：真的 scaffold、npm ci、astro build，再用 check_site.py 檢查。"""

    def test_template_builds_and_passes_checks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fictional-website-node-") as temporary:
            root = Path(temporary)
            config = root / "config.json"
            payload = json.loads(DEFAULT.read_text(encoding="utf-8"))
            payload["business"].update(
                {
                    "status": "configured",
                    "site_name": "虛構工作室",
                    "one_line_positioning": "幫虛構的小店把流程交給 AI",
                    "audience_summary": "沒有技術團隊的虛構店主",
                    "offerings": [{"name": "虛構諮詢", "summary": "一次會談"}],
                    "primary_call_to_action": {"kind": "mailto", "label": "寫信給我", "target": "mailto:hello@example.invalid"},
                    "contact_channels": [{"kind": "email", "label": "Email", "target": "mailto:hello@example.invalid"}],
                }
            )
            payload["pages"]["optional"] = ["portfolio", "case_studies", "pricing", "faq", "newsletter"]
            config.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            # 文案層：一份最小 copy.json 與一篇文章，確認 site.copy.mjs 與文章替換在真實建置下可用
            copy_json = {
                "schema_version": 1, "status": "draft", "language": "zh-TW", "facts_snapshot": [], "contains_credentials": False,
                "home": {k: {"text": None, "source": "placeholder"} for k in ("eyebrow", "title", "lead", "primary_cta", "secondary_cta", "offerings_eyebrow", "offerings_heading", "offerings_intro", "trust_eyebrow", "trust_heading", "closing_eyebrow", "closing_heading", "closing_lead")},
                "about": {"title": {"text": "關於虛構工作室", "source": "ai_suggestion"}, "intro": {"text": None, "source": "placeholder"}, "sections": [{"heading": {"text": "我怎麼工作", "source": "ai_suggestion"}, "body": {"text": "先釐清目標再動手。", "source": "ai_suggestion"}}], "cta_heading": {"text": None, "source": "placeholder"}},
                "services": {"title": {"text": None, "source": "placeholder"}, "intro": {"text": None, "source": "placeholder"}, "closing_note": {"text": None, "source": "placeholder"}},
                "contact": {"title": {"text": None, "source": "placeholder"}, "intro": {"text": "選一個方便的方式。", "source": "ai_suggestion"}, "form_note": {"text": None, "source": "placeholder"}},
                "blog": {"title": {"text": None, "source": "placeholder"}, "intro": {"text": None, "source": "placeholder"}, "empty_note": {"text": None, "source": "placeholder"}},
                "not_found": {"title": {"text": None, "source": "placeholder"}, "lead": {"text": None, "source": "placeholder"}},
                "posts": [{"slug": "first-post", "file": "first-post.md", "source": "ai_suggestion"}],
            }
            copy_json["home"]["title"] = {"text": "虛構的新標題", "source": "ai_suggestion"}
            (root / "copy.json").write_text(json.dumps(copy_json, ensure_ascii=False), encoding="utf-8")
            (root / "posts").mkdir()
            (root / "posts/first-post.md").write_text("---\ntitle: \"虛構的第一篇\"\ndate: \"2026-01-02\"\ndescription: \"虛構描述\"\ntags: [\"虛構\"]\n---\n\n## 開始\n\n" + "這是虛構文章的內文。" * 12 + "\n", encoding="utf-8")
            target = root / "site"
            scaffold = subprocess.run(
                ["python3", str(SCAFFOLD), "scaffold", "--config", str(config), "--target", str(target), "--confirm-write"],
                capture_output=True, text=True,
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
            self.assertTrue(json.loads(scaffold.stdout)["copy_layer"]["applied"])
            self.assertTrue((target / "src/content/posts/first-post.md").is_file())
            self.assertFalse((target / "src/content/posts/hello-world.md").exists())
            install = subprocess.run(["npm", "ci", "--no-audit", "--no-fund"], cwd=target, capture_output=True, text=True)
            self.assertEqual(install.returncode, 0, install.stderr[-2000:])
            build = subprocess.run(["npm", "run", "build"], cwd=target, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout[-2000:] + build.stderr[-2000:])
            check = subprocess.run(
                ["python3", str(CHECK), "--dist", str(target / "dist"), "--config", str(config)], capture_output=True, text=True
            )
            self.assertEqual(check.returncode, 0, check.stdout)
            home_html = (target / "dist/index.html").read_text(encoding="utf-8")
            self.assertIn("虛構的新標題", home_html)
            self.assertTrue((target / "dist/blog/first-post/index.html").is_file())


if __name__ == "__main__":
    unittest.main()
