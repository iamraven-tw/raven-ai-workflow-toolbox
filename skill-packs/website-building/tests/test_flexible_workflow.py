#!/usr/bin/env python3
"""驗證選頁、Agent 文案與實際精簡網站的接續行為，不執行部署。"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    """載入受測 helper，不執行命令列入口。"""
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


setup = module("flex_setup", "skills/website-setup/scripts/manage_workspace.py")
writer = module("flex_writer", "skills/website-content-writing/scripts/content_writer.py")
deploy = module("flex_deploy", "skills/website-deploy/scripts/deploy_site.py")


def config():
    """只建立虛構單頁業務資料。"""
    value = json.loads((ROOT / "skills/website-setup/assets/default-config.json").read_text())
    value["business"].update(status="configured", site_name="測試工作室",
        one_line_positioning="協助整理工作流程", audience_summary="小型團隊",
        offerings=[{"name": "流程諮詢", "summary": "一起釐清流程"}],
        primary_call_to_action={"kind": "mailto", "label": "聯絡", "target": "mailto:test@example.invalid"})
    return value


class FlexibleWorkflowTests(unittest.TestCase):
    def test_minimal_and_legacy_pages_and_invalid_choices(self):
        """單頁及舊六頁都有效，未知、重複與缺首頁仍拒絕。"""
        value = config()
        setup.validate_configuration(value)
        for pages in (["home", "about", "services", "blog", "contact", "not_found"], ["home", "blog", "not_found"]):
            value["pages"]["required"] = pages
            setup.validate_configuration(value)
        for pages in (["home", "home", "not_found"], ["home", "../secret", "not_found"], ["blog", "not_found"]):
            value["pages"]["required"] = pages
            with self.assertRaises(setup.ConfigurationError):
                setup.validate_configuration(value)

    def test_form_route_requires_contact_page(self):
        """表單前提在提案時檢查，不到建置才產生失效連結。"""
        value = config()
        value["business"]["primary_call_to_action"].update(kind="form_later", target=None)
        with self.assertRaises(setup.ConfigurationError):
            setup.validate_configuration(value)
        value["pages"]["required"].append("contact")
        setup.validate_configuration(value)

    def test_agent_copy_does_not_require_unselected_pages(self):
        """Agent 候選可定稿，未選頁面不出現在人工填寫清單。"""
        value = config()
        copy = writer.command_draft(value)
        for page in ("home", "not_found"):
            for key in copy[page]:
                copy[page][key] = {"text": "一起釐清工作流程", "source": "ai_suggestion"}
        copy["status"] = "final"
        self.assertEqual(writer.validate_copy(copy, value), [])
        self.assertEqual(writer.validate_copy(copy, None), [])
        self.assertTrue(all(row["path"].split(".")[0] in value["pages"]["required"]
                            for row in writer.command_guide(copy)["fields"]))
        copy["home"]["title"]["text"] = "已服務 9999 家客戶"
        self.assertIn("unverified_number", [f["kind"] for f in writer.validate_copy(copy, value)])

    def test_remote_checks_follow_selected_pages(self):
        """遠端驗證不要求未選頁面或 RSS，也檢查已選額外頁。"""
        value = config()
        value["pages"]["optional"] = ["faq"]
        seen = []
        def fetch(url, **kwargs):
            seen.append(url)
            if "this-page-should-not-exist" in url:
                return 404, {}, b""
            return 200, {}, b'<meta name="robots" content="noindex, nofollow"><meta property="og:image" content="https://example.test/og.png">'
        with patch.object(deploy, "fetch", side_effect=fetch):
            self.assertEqual(deploy.command_verify("https://example.test", expect_indexing="noindex", config=value)["result"], "verified")
        self.assertIn("https://example.test/faq/", seen)
        self.assertNotIn("https://example.test/blog/", seen)
        self.assertNotIn("https://example.test/rss.xml", seen)

    @unittest.skipUnless(os.environ.get("WEBSITE_NODE_ACCEPTANCE") == "1", "需明確啟用真實 Node 建置")
    def test_six_themes_build_without_blog_or_dead_links(self):
        """同一份精簡網站在六種主題都可實際建置且無失效連結。"""
        with tempfile.TemporaryDirectory(prefix="website-flexible-") as directory:
            root = Path(directory).resolve()
            value = config()
            candidate = root / "config.json"
            candidate.write_text(json.dumps(value), encoding="utf-8")
            target = root / "site"
            def run(args, cwd=None):
                result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-2000:])
            run([sys.executable, str(ROOT / "skills/website-build/scripts/scaffold_site.py"), "scaffold", "--config", str(candidate), "--target", str(target), "--confirm-write"])
            run(["npm", "ci"], target)
            site = target / "site.config.mjs"
            baseline = site.read_text()
            for theme in ("whitebox", "nightlight", "darkroom", "daylight", "sunrise", "weekly"):
                site.write_text(baseline.replace("theme: 'whitebox'", "theme: '" + theme + "'"), encoding="utf-8")
                run(["npm", "run", "build"], target)
                self.assertFalse((target / "dist/blog").exists())
                self.assertFalse((target / "dist/rss.xml").exists())
                run([sys.executable, str(ROOT / "skills/website-build/scripts/check_site.py"), "--dist", str(target / "dist"), "--config", str(candidate)])


if __name__ == "__main__":
    unittest.main()
