#!/usr/bin/env python3
"""以虛構設定測試四種製圖方式；不呼叫模型或瀏覽器。"""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/social-image-production/scripts/image_routing.py"
SPEC = importlib.util.spec_from_file_location("image_routing", SCRIPT)
routing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(routing)
DEFAULT = ROOT / "skills/social-media-setup/assets/default-config.json"


class ImageRoutingTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(DEFAULT.read_text(encoding="utf-8"))

    def test_four_saved_methods_do_not_ask_again(self):
        for method, action in (("codex", "direct_generate"), ("antigravity", "direct_generate"), ("web", "deliver_prompt"), ("html_css", "render_html")):
            self.config["image_production"]["default_method"] = method
            before = copy.deepcopy(self.config)
            for _ in range(2):
                result = routing.select_route(self.config)
                self.assertEqual((result["method"], result["action"]), (method, action))
                self.assertNotIn("question_count", result)
                self.assertFalse(result["writes_config"])
            self.assertEqual(before, self.config)

    def test_information_dense_preference_and_current_request_priority(self):
        self.config["image_production"]["default_method"] = "codex"
        self.assertEqual(routing.select_route(self.config, information_dense=True)["method"], "html_css")
        self.assertEqual(routing.select_route(self.config, information_dense=True, method="antigravity")["method"], "antigravity")
        self.config["image_production"]["information_dense_method"] = "inherit"
        self.assertEqual(routing.select_route(self.config, information_dense=True)["method"], "codex")

    def test_web_browser_request_is_not_persistent(self):
        self.config["image_production"]["default_method"] = "web"
        result = routing.select_route(self.config, browser_requested=True)
        self.assertEqual(result["action"], "operate_browser_with_current_request")
        self.assertFalse(result["publishing_authorized"])
        self.assertEqual(routing.select_route(self.config)["action"], "deliver_prompt")
        self.assertNotIn("browser_requested", self.config["image_production"])

    def test_unknown_preference_asks_once_but_explicit_request_proceeds(self):
        for config in (self.config, {"schema_version": 3}):
            self.assertEqual(routing.select_route(config)["question_count"], 1)
            self.assertEqual(routing.select_route(config, method="codex")["action"], "direct_generate")

    def test_invalid_or_authorization_fields_rejected(self):
        self.config["image_production"]["default_method"] = "codex"
        for key, value in (("default_method", "other_api"), ("information_dense_method", "auto_paid"), ("web_provider", ""), ("browser_authorized", True), ("api_key", "fictional")):
            config = copy.deepcopy(self.config)
            config["image_production"][key] = value
            with self.assertRaises(ValueError):
                routing.select_route(config)
        with self.assertRaises(ValueError):
            routing.select_route({"schema_version": 4})

    def test_cli_is_readonly(self):
        self.config["image_production"]["default_method"] = "web"
        with tempfile.TemporaryDirectory(prefix="fictional-image-route-") as temporary:
            config = Path(temporary) / "config.json"
            config.write_text(json.dumps(self.config), encoding="utf-8")
            before = config.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), "--config", str(config)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(json.loads(result.stdout)["action"], "deliver_prompt")
            self.assertEqual(config.read_bytes(), before)
            self.assertEqual(list(Path(temporary).iterdir()), [config])

    def test_brand_is_shared_by_four_routes_and_override_is_not_saved(self):
        """虛構品牌色只影響本次簡報，不變成生成或發布授權。"""
        self.config["brand_visual"].update(status="confirmed", primary_color="#126644", font_family="Fictional Sans")
        before = copy.deepcopy(self.config)
        for method in routing.METHODS:
            result = routing.select_route(self.config, method=method, visual_override={"primary_color": "#554488"})
            self.assertEqual(result["visual"]["values"]["primary_color"], "#554488")
            self.assertEqual(result["visual"]["values"]["font_family"], "Fictional Sans")
            self.assertEqual(result["visual"]["sources"]["primary_color"], "current_request")
            self.assertFalse(result["publishing_authorized"])
        self.assertEqual(self.config, before)
        self.assertEqual(routing.select_route(self.config, method="web")["visual"]["values"]["primary_color"], "#126644")

    def test_legacy_visual_is_empty_not_invented(self):
        """沒有品牌的舊版設定不套用任何維護者配色。"""
        old = copy.deepcopy(self.config)
        old["schema_version"] = 4
        old.pop("brand_visual")
        self.assertEqual(routing.select_route(old, method="html_css")["visual"]["values"], {})


if __name__ == "__main__":
    unittest.main()
