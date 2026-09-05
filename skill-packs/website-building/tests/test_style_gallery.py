#!/usr/bin/env python3
"""以虛構工作區驗證內建主題、畫廊產生（用匯出預覽）、主題選擇與 scaffold 銜接。"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GALLERY = ROOT / "skills/website-design-preview/scripts/style_gallery.py"
SCAFFOLD = ROOT / "skills/website-build/scripts/scaffold_site.py"
THEMES = ROOT / "template/src/themes"
PREVIEWS = ROOT / "skills/website-design-preview/assets/previews"
DEFAULT = ROOT / "skills/website-setup/assets/default-config.json"
TONALITIES = {"warm_literary", "dark_immersive", "clean_minimal", "photo_showroom", "colorful_energetic", "editorial_press"}


def run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(arguments, capture_output=True, text=True)


def configured_config() -> dict:
    payload = json.loads(DEFAULT.read_text(encoding="utf-8"))
    payload["business"].update(
        {
            "status": "configured",
            "site_name": "虛構工作室",
            "one_line_positioning": "幫虛構的小店把流程交給 AI",
            "audience_summary": "沒有技術團隊的虛構店主",
            "offerings": [{"name": "虛構啟動諮詢", "summary": "一次會談釐清可自動化的流程"}],
            "trust_signals": ["虛構的三年顧問經驗"],
            "primary_call_to_action": {"kind": "mailto", "label": "寫信給我", "target": "mailto:hello@example.invalid"},
            "contact_channels": [{"kind": "email", "label": "Email", "target": "mailto:hello@example.invalid"}],
        }
    )
    payload["design"].update({"status": "recommended", "tonality": "warm_literary"})
    return payload


class StyleGalleryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="fictional-website-style-")
        self.workspace = Path(self.temporary.name) / "ws"
        (self.workspace / "website").mkdir(parents=True)
        (self.workspace / "website/config.json").write_text(json.dumps(configured_config(), ensure_ascii=False), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def gallery(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return run(["python3", str(GALLERY), *arguments])

    def test_themes_cover_all_tonalities_and_carry_attribution(self) -> None:
        result = self.gallery("list", "--recommend", "dark_immersive")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["count"], 6)
        self.assertEqual({theme["tonality"] for theme in payload["themes"]}, TONALITIES)
        self.assertEqual(payload["recommended"], "nightshift")
        for path in THEMES.glob("*/theme.json"):
            theme = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(theme["source_license"], "Apache-2.0")
            self.assertTrue(theme["source_repository"].startswith("https://"))
            for required in ("theme.css", "Home.astro", "BlogIndex.astro", "BlogPost.astro", "Header.astro", "Footer.astro", "BaseLayout.astro"):
                self.assertTrue((path.parent / required).is_file(), f"{theme['id']} 缺少 {required}")
        self.assertEqual(self.gallery("list", "--recommend", "not_a_tonality").returncode, 2)

    def test_previews_are_exported_for_every_theme(self) -> None:
        manifest = json.loads((PREVIEWS / "manifest.json").read_text(encoding="utf-8"))
        ids = {record["id"] for record in manifest["themes"]}
        self.assertEqual(ids, {path.parent.name for path in THEMES.glob("*/theme.json")})
        for record in manifest["themes"]:
            for page in ("home", "blog", "post"):
                target = PREVIEWS / record["pages"][page]["file"]
                self.assertTrue(target.is_file(), target)
                text = target.read_text(encoding="utf-8")
                self.assertIn("<style>", text)
                self.assertNotIn('href="/_astro/', text)
                self.assertNotIn('src="/images/', text)

    def test_render_substitutes_user_content_and_marks_recommendation(self) -> None:
        result = self.gallery("render", "--workspace-root", str(self.workspace), "--recommend", "warm_literary")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["recommended"], "bookshop")
        self.assertEqual(payload["content_source"], "website/config.json")
        gallery = Path(payload["gallery"])
        text = gallery.read_text(encoding="utf-8")
        self.assertIn('class="card recommended" id="bookshop"', text)
        self.assertEqual(text.count('<article class="card'), 6)
        html_previews = [item for item in payload["previews"] if item.endswith(".html")]
        self.assertEqual(len(html_previews), 18)
        self.assertTrue((gallery.parent / "previews/images/samples/photos.json").is_file())
        self.assertGreaterEqual(len(list((gallery.parent / "previews/images/samples").glob("*.jpg"))), 6)
        home = (gallery.parent / "previews/bookshop/home.html").read_text(encoding="utf-8")
        self.assertIn("虛構工作室", home)
        self.assertIn("幫虛構的小店把流程交給 AI", home)
        self.assertIn("虛構啟動諮詢", home)
        self.assertNotIn("範例工作室", home)
        self.assertFalse((self.workspace / "website/design.json").exists())

    def test_render_without_config_keeps_fictional_content(self) -> None:
        empty = Path(self.temporary.name) / "empty"
        empty.mkdir()
        result = self.gallery("render", "--workspace-root", str(empty))
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["content_source"], "fictional_defaults")
        self.assertIsNone(payload["recommended"])

    def test_select_requires_confirmation_and_replace(self) -> None:
        self.assertEqual(self.gallery("select", "--workspace-root", str(self.workspace), "--theme", "broadsheet").returncode, 2)
        self.assertFalse((self.workspace / "website/design.json").exists())
        self.assertEqual(self.gallery("select", "--workspace-root", str(self.workspace), "--theme", "no-such", "--confirm-write").returncode, 2)

        selected = self.gallery("select", "--workspace-root", str(self.workspace), "--theme", "broadsheet", "--confirm-write")
        self.assertEqual(selected.returncode, 0, selected.stderr)
        payload = json.loads(selected.stdout)
        self.assertEqual(payload["config_patch"]["design"], {"status": "confirmed", "tonality": "editorial_press", "style_source": "bundled", "style_id": "broadsheet"})
        design = json.loads((self.workspace / "website/design.json").read_text(encoding="utf-8"))
        self.assertEqual(design["theme"], "broadsheet")
        self.assertEqual(design["contains_credentials"], False)

        self.assertEqual(self.gallery("select", "--workspace-root", str(self.workspace), "--theme", "broadsheet", "--confirm-write").returncode, 0)
        different = self.gallery("select", "--workspace-root", str(self.workspace), "--theme", "gallery", "--confirm-write")
        self.assertEqual(different.returncode, 2)
        self.assertIn("--replace", different.stderr)
        self.assertEqual(self.gallery("select", "--workspace-root", str(self.workspace), "--theme", "gallery", "--confirm-write", "--replace").returncode, 0)

    def test_selected_theme_feeds_scaffold_automatically(self) -> None:
        self.gallery("select", "--workspace-root", str(self.workspace), "--theme", "nightshift", "--confirm-write")
        target = Path(self.temporary.name) / "site"
        config = self.workspace / "website/config.json"
        plan = run(["python3", str(SCAFFOLD), "plan", "--config", str(config), "--target", str(target)])
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertEqual(json.loads(plan.stdout)["theme"], "nightshift")
        scaffold = run(["python3", str(SCAFFOLD), "scaffold", "--config", str(config), "--target", str(target), "--confirm-write"])
        self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
        self.assertIn("theme: 'nightshift'", (target / "site.config.mjs").read_text(encoding="utf-8"))
        self.assertIn("#5e6ad2", (target / "public/favicon.svg").read_text(encoding="utf-8"))
        self.assertTrue((target / "src/themes/nightshift/theme.css").is_file())
        explicit = run(["python3", str(SCAFFOLD), "plan", "--config", str(config), "--target", str(Path(self.temporary.name) / "site2"), "--theme", "playground"])
        self.assertEqual(json.loads(explicit.stdout)["theme"], "playground")
        unknown = run(["python3", str(SCAFFOLD), "plan", "--config", str(config), "--target", str(Path(self.temporary.name) / "site3"), "--theme", "nope"])
        self.assertEqual(unknown.returncode, 2)

    def test_symlink_targets_stop(self) -> None:
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        os.symlink(outside, self.workspace / ".local")
        result = self.gallery("render", "--workspace-root", str(self.workspace))
        self.assertEqual(result.returncode, 2)
        self.assertFalse(any(outside.iterdir()))


if __name__ == "__main__":
    unittest.main()
