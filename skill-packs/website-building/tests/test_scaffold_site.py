#!/usr/bin/env python3
"""以虛構設定驗證 scaffold_site.py 的計畫、建立、拒絕條件與佔位素材。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from .website_platform_support import directory_symlink_or_skip
except ImportError:
    from website_platform_support import directory_symlink_or_skip


ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = ROOT / "skills/website-build/scripts/scaffold_site.py"
DEFAULT = ROOT / "skills/website-setup/assets/default-config.json"


def run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """執行公開命令並保留輸出。"""

    return subprocess.run(arguments, capture_output=True, text=True)


def configured_config(optional: list[str] | None = None) -> dict:
    """建立通過契約的虛構設定。"""

    payload = json.loads(DEFAULT.read_text(encoding="utf-8"))
    payload["business"].update(
        {
            "status": "configured",
            "site_name": "虛構工作室",
            "one_line_positioning": "幫虛構的小店把流程交給 AI",
            "audience_summary": "沒有技術團隊的虛構店主",
            "offerings": [
                {"name": "虛構啟動諮詢", "summary": "一次會談釐清可自動化的流程"},
                {"name": "虛構建置", "summary": "把流程做成實際運作的系統"},
            ],
            "trust_signals": ["虛構的三年顧問經驗"],
            "primary_call_to_action": {"kind": "mailto", "label": "寫信給我", "target": "mailto:hello@example.invalid"},
            "contact_channels": [{"kind": "email", "label": "Email", "target": "mailto:hello@example.invalid"}],
        }
    )
    payload["pages"]["optional"] = optional or []
    payload["hosting"]["worker_name"] = "fictional-studio"
    return payload


class ScaffoldTests(unittest.TestCase):
    """確認建立專案不覆蓋、不含秘密、素材規格正確。"""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="fictional-website-build-")
        self.root = Path(self.temporary.name)
        self.config = self.root / "config.json"
        self.target = self.root / "site"
        self.write_config(configured_config())

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_config(self, payload: dict) -> None:
        self.config.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def command(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, str(SCAFFOLD), *arguments])

    def test_plan_is_read_only_and_scaffold_requires_confirmation(self) -> None:
        """plan 不建立目錄；scaffold 需要旗標。"""

        plan = self.command("plan", "--config", str(self.config), "--target", str(self.target))
        self.assertEqual(plan.returncode, 0, plan.stderr)
        payload = json.loads(plan.stdout)
        self.assertEqual(payload["result"], "plan")
        self.assertEqual(payload["worker_name"], "fictional-studio")
        self.assertFalse(self.target.exists())

        without_flag = self.command("scaffold", "--config", str(self.config), "--target", str(self.target))
        self.assertEqual(without_flag.returncode, 2)
        self.assertFalse(self.target.exists())

    def test_scaffold_writes_config_pages_and_placeholders(self) -> None:
        """建立專案後站點設定、可選頁面與佔位素材都正確。"""

        self.write_config(configured_config(["faq", "pricing"]))
        result = self.command("scaffold", "--config", str(self.config), "--target", str(self.target), "--confirm-write")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], "scaffolded")
        self.assertEqual(sorted(payload["optional_pages"]), ["faq.astro", "pricing.astro"])

        site_config = (self.target / "site.config.mjs").read_text(encoding="utf-8")
        self.assertIn("虛構工作室", site_config)
        self.assertIn("mailto:hello@example.invalid", site_config)
        self.assertIn("optional: ['faq', 'pricing']", site_config)
        self.assertIn("indexing: 'noindex'", site_config)
        self.assertIn("fonts: 'google'", site_config)
        self.assertIn('"name": "fictional-studio"', (self.target / "wrangler.jsonc").read_text(encoding="utf-8"))
        self.assertTrue((self.target / "src/pages/faq.astro").is_file())
        self.assertTrue((self.target / "src/pages/pricing.astro").is_file())
        self.assertFalse((self.target / "src/pages/portfolio.astro").exists())
        self.assertFalse((self.target / "optional-pages").exists())
        self.assertFalse((self.target / "node_modules").exists())

        og = (self.target / "public/og-image.png").read_bytes()
        self.assertTrue(og.startswith(b"\x89PNG"))
        self.assertEqual(int.from_bytes(og[16:20], "big"), 1200)
        self.assertEqual(int.from_bytes(og[20:24], "big"), 630)
        icon = (self.target / "public/apple-touch-icon.png").read_bytes()
        self.assertEqual(int.from_bytes(icon[16:20], "big"), 180)
        self.assertIn("虛構", (self.target / "public/favicon.svg").read_text(encoding="utf-8"))
        self.assertIn("theme: 'whitebox'", (self.target / "site.config.mjs").read_text(encoding="utf-8"))
        for name in ("hero.svg", "avatar.svg", "offering-1.svg", "offering-2.svg", "offering-3.svg"):
            self.assertTrue((self.target / "public/images/placeholders" / name).is_file())

    def test_theme_selection_changes_config_and_placeholder_colors(self) -> None:
        """指定主題時站點設定、tsconfig 與佔位素材顏色都跟著主題。"""

        result = self.command("scaffold", "--config", str(self.config), "--target", str(self.target), "--theme", "weekly", "--confirm-write")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["theme"], "weekly")
        self.assertEqual(payload["theme_name"], "週刊")
        self.assertIn("theme: 'weekly'", (self.target / "site.config.mjs").read_text(encoding="utf-8"))
        self.assertIn("#876533", (self.target / "public/favicon.svg").read_text(encoding="utf-8"))
        for theme in ("nightlight", "darkroom", "whitebox", "daylight", "sunrise", "weekly"):
            self.assertTrue((self.target / "src/themes" / theme / "theme.css").is_file())

        design = self.root / "config-dir" ; design.mkdir()
        (design / "config.json").write_text(self.config.read_text(encoding="utf-8"), encoding="utf-8")
        (design / "design.json").write_text(json.dumps({"schema_version": 1, "theme": "daylight"}), encoding="utf-8")
        plan = self.command("plan", "--config", str(design / "config.json"), "--target", str(self.root / "site-b"))
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertEqual(json.loads(plan.stdout)["theme"], "daylight")

    def test_rejects_unconfigured_business_secrets_and_non_empty_target(self) -> None:
        """未設定、含秘密或目標非空都停止。"""

        unconfigured = json.loads(DEFAULT.read_text(encoding="utf-8"))
        self.write_config(unconfigured)
        result = self.command("plan", "--config", str(self.config), "--target", str(self.target))
        self.assertEqual(result.returncode, 2)
        self.assertIn("website-setup", result.stderr)

        with_secret = configured_config()
        with_secret["hosting"]["api_token"] = "fictional"
        self.write_config(with_secret)
        result = self.command("plan", "--config", str(self.config), "--target", str(self.target))
        self.assertEqual(result.returncode, 2)
        self.assertIn("秘密", result.stderr)

        self.write_config(configured_config())
        self.target.mkdir()
        (self.target / "KEEP.txt").write_text("虛構既有內容\n", encoding="utf-8")
        result = self.command("scaffold", "--config", str(self.config), "--target", str(self.target), "--confirm-write")
        self.assertEqual(result.returncode, 2)
        self.assertEqual((self.target / "KEEP.txt").read_text(encoding="utf-8"), "虛構既有內容\n")
        self.assertFalse((self.target / "site.config.mjs").exists())

        inside = ROOT / "template" / "should-not-exist"
        result = self.command("plan", "--config", str(self.config), "--target", str(inside))
        self.assertEqual(result.returncode, 2)
        self.assertFalse(inside.exists())

    def test_rejects_symlink_target(self) -> None:
        """symlink 目標停止。"""

        outside = self.root / "outside"
        outside.mkdir()
        directory_symlink_or_skip(self, outside, self.target)
        result = self.command("scaffold", "--config", str(self.config), "--target", str(self.target), "--confirm-write")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(any(outside.iterdir()))


if __name__ == "__main__":
    unittest.main()
