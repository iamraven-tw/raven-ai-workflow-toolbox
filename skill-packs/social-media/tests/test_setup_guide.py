"""教學可搬移、唯讀啟動與內容完整性；不執行真實平台設定。"""

import contextlib
import importlib.util
import io
import json
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlparse, unquote


PACK = Path(__file__).resolve().parents[1]
SKILL = PACK / "skills/social-media-setup"
GUIDE = SKILL / "assets/api-setup-guide"
spec = importlib.util.spec_from_file_location("guide_launcher", SKILL / "scripts/open_setup_guide.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class SetupGuideTests(unittest.TestCase):
    def test_known_routes_and_relative_assets(self):
        for platform, routes in launcher.ROUTES.items():
            for route in routes:
                result = urlparse(launcher.guide_url(platform, route, 3))
                self.assertEqual(result.scheme, "file")
                self.assertEqual(result.fragment, f"{platform}/{route}/2")
                self.assertTrue(Path(unquote(result.path)).is_file())
        html = (GUIDE / "index.html").read_text()
        assets = [urlparse(value).path for value in re.findall(r'(?:src|href)="([^"]+)"', html)]
        for asset in ("guide.css", "guide.js", "guides.js"):
            self.assertIn(asset, assets)
            self.assertTrue((GUIDE / asset).is_file())

    def test_reject_untrusted_route_and_bad_step(self):
        for args in (("unknown",), ("youtube", "../../private"), ("instagram", "javascript:alert(1)"),
                     ("threads", None, 0), ("threads", None, 101)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                launcher.guide_url(*args)

    def test_instagram_default_supports_requested_delete_route(self):
        # 新設定走完整管理主線，既有直接登入深連結仍保留。
        self.assertEqual(urlparse(launcher.guide_url("instagram")).fragment, "instagram/facebook_login/0")
        self.assertEqual(urlparse(launcher.guide_url("instagram", "instagram_login")).fragment,
                         "instagram/instagram_login/0")

    @unittest.skipUnless(shutil.which("node"), "內容驗證需既有 Node")
    def test_self_managed_routes_and_secret_handoff_contract(self):
        # 比對實際資料而非原始碼片段，防止預設路線或共用函式接錯。
        code = "const fs=require('node:fs'),vm=require('node:vm');const c={window:{}};vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),c);process.stdout.write(JSON.stringify(c.window.SETUP_GUIDE));"
        data = json.loads(subprocess.run(["node", "-e", code, str(GUIDE / "guides.js")],
                                        capture_output=True, text=True, check=True).stdout)
        routes = {r["id"]: r for r in data["routes"]}
        content = {key: json.dumps(value, ensure_ascii=False) for key, value in routes.items()}
        self.assertIn("instagram_manage_contents", content["facebook_login"])
        self.assertIn("Facebook User Token", content["facebook_login"])
        self.assertIn("不含 API 刪文", content["instagram_login"])
        self.assertIn("threads_delete", content["threads"])
        self.assertFalse(any("設定回呼" in s["title"] for s in routes["threads"]["steps"]))
        self.assertNotIn("threadsSecretLocation", content["threads"])
        self.assertIn("threadsTokenLocation", content["threads"])
        self.assertIn("Page Access Token", content["page_token"])
        self.assertIn("metaSecretLocation", content["page_token"])
        self.assertFalse(any("設定回呼" in s["title"] for s in routes["page_token"]["steps"]))
        self.assertIn("metaSecretLocation", content["pages"])
        for phrase in ("7 天", "youtube.force-ssl", "yt-analytics.readonly", "私人", "loopback"):
            self.assertIn(phrase, content["desktop"])
        for route in routes.values():
            self.assertEqual(route["steps"][1]["title"], "確認功能與使用條件")
            joined = json.dumps(route, ensure_ascii=False)
            self.assertIn("我準備好輸入了", joined)
            self.assertIn("已輸入完畢", joined)
            self.assertIn("Enter", joined)
            # 每條路線都提供同一張交接圖，但不增加額外設定關卡。
            self.assertTrue(any("secureHandoff" in s.get("images", []) for s in route["steps"]))
        self.assertIn("尚未完成", data["status"])

    def test_default_does_not_open_browser_or_claim_verification(self):
        output = io.StringIO()
        with patch.object(launcher.webbrowser, "open") as browser, contextlib.redirect_stdout(output):
            launcher.main(["--platform", "youtube"])
        browser.assert_not_called()
        result = json.loads(output.getvalue())
        self.assertFalse(result["browser_open_requested"])
        self.assertEqual(result["platform_verification"], "not_performed")
        self.assertEqual(result["coverage"], "illustrated_guide")

    def test_browser_acceptance_is_reported_not_assumed(self):
        for accepted in (False, True):
            output = io.StringIO()
            with patch.object(launcher.webbrowser, "open", return_value=accepted) as browser, contextlib.redirect_stdout(output):
                launcher.main(["--platform", "threads", "--open"])
            browser.assert_called_once()
            self.assertEqual(json.loads(output.getvalue())["browser_open_accepted"], accepted)

    def test_relocated_install_uses_its_own_assets_without_writes(self):
        with tempfile.TemporaryDirectory(prefix="setup-guide-test-") as temp:
            target = Path(temp) / "安裝路徑 with spaces/social-media-setup"
            shutil.copytree(SKILL, target)
            before = sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file())
            run = subprocess.run(["python3", str(target / "scripts/open_setup_guide.py"), "--platform", "instagram", "--route", "facebook_login"], capture_output=True, text=True, check=True)
            result = urlparse(json.loads(run.stdout)["guide_url"])
            self.assertEqual(Path(unquote(result.path)), (target / "assets/api-setup-guide/index.html").resolve())
            self.assertEqual(before, sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()))

    def test_missing_page_fails_without_browser(self):
        with patch.object(launcher.Path, "is_file", return_value=False), self.assertRaises(FileNotFoundError):
            launcher.guide_url("youtube")

    @unittest.skipUnless(shutil.which("node"), "內容驗證需既有 Node；不由測試安裝")
    def test_content_routes_images_sources_and_annotation_bounds(self):
        # 在無網路、無瀏覽器物件的獨立上下文執行純教學資料。
        code = "const fs=require('node:fs'),vm=require('node:vm');const c={window:{}};vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),c,{timeout:1000});process.stdout.write(JSON.stringify(c.window.SETUP_GUIDE));"
        result = subprocess.run(["node", "-e", code, str(GUIDE / "guides.js")], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        actual = {p: tuple(r["id"] for r in data["routes"] if r["platform"] == p) for p in launcher.ROUTES}
        self.assertEqual(actual, launcher.ROUTES)
        # 新實拍必須真正接入路線，不能只登錄圖片而讓使用者看不到。
        attached = {image_id for route in data["routes"] for step in route["steps"] for image_id in step.get("images", [])}
        for image_id in ("instagramConsentAccount", "instagramConsentPermissions", "threadsConsent", "threadsTokenResult", "youtubeClientCreated", "youtubeAccountConsent", "youtubeTestingWarning", "youtubeOAuthConsent", "youtubeBrandFirst", "youtubeBrandAudience", "youtubeBrandContact", "youtubeBrandPolicy"):
            self.assertIn(image_id, attached)
        for route in data["routes"]:
            self.assertGreaterEqual(len(route["steps"]), 6)
            for step in route["steps"]:
                for key in ("title", "intro", "owner", "actions", "expected", "help"):
                    self.assertTrue(step[key], (route["id"], key))
                self.assertIn(step["source"], data["sources"])
                image_ids = step.get("images", [step["image"]] if step.get("image") else [])
                for image_id in image_ids:
                    self.assertIn(image_id, data["images"])
                # 不可把建立後的主控板當成完整的新建 App 圖文流程。
                if step["title"] == "建立或選用 Meta App":
                    self.assertTrue(image_ids)
                    self.assertTrue(step.get("capture"))
        for source in data["sources"].values():
            url = urlparse(source["url"])
            self.assertEqual(url.scheme, "https")
            self.assertIn(url.netloc, ("developers.facebook.com", "developers.google.com", "support.google.com"))
            self.assertFalse(url.query)
        for image in data["images"].values():
            path = (GUIDE / image["file"]).resolve()
            self.assertTrue(path.is_relative_to(GUIDE.resolve()))
            self.assertTrue(path.is_file())
            raw = path.read_bytes()
            self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(int.from_bytes(raw[16:20], "big"), image["width"])
            self.assertEqual(int.from_bytes(raw[20:24], "big"), image["height"])
            self.assertIn(image["source"], data["sources"])
            self.assertTrue(image["kind"] and image["captured"] and image["note"])
            if "capturePage" in image:
                capture = urlparse(image["capturePage"])
                self.assertEqual(capture.scheme, "https")
                self.assertIn(capture.netloc, {"developers.facebook.com", "console.cloud.google.com"})
                self.assertFalse(capture.query)
                self.assertNotRegex(capture.path, r"\d{5,}")
            for mark in image["marks"]:
                self.assertTrue(0 <= mark["x"] < mark["x"] + mark["w"] <= 100)
                self.assertTrue(0 <= mark["y"] < mark["y"] + mark["h"] <= 100)

    def test_static_guide_has_no_secret_form_or_network_client(self):
        html = (GUIDE / "index.html").read_text()
        self.assertIn("connect-src 'none'", html)
        self.assertIn("form-action 'none'", html)
        self.assertNotIn("<input", html)
        self.assertNotIn("<form", html)
        script = (GUIDE / "guide.js").read_text()
        for disallowed in ("fetch(", "XMLHttpRequest", "localStorage", "sessionStorage", "document.cookie", "innerHTML", "eval("):
            self.assertNotIn(disallowed, script)


if __name__ == "__main__":
    unittest.main()
