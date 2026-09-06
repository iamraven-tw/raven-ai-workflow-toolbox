"""驗證四種製圖路徑的公開驗收 fixture；不呼叫模型、瀏覽器或 renderer。"""

from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/social-image-production"
ASSETS = SKILL / "assets"


def load_module(name, path):
    """載入技能內的無網路 helper。"""

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


routing = load_module("image_routing_acceptance", SKILL / "scripts/image_routing.py")
images = load_module("image_assets_acceptance", SKILL / "scripts/image_assets.py")


class CardParser(HTMLParser):
    """只解析本機 fixture 的標籤、屬性與可見文字。"""

    def __init__(self):
        super().__init__()
        self.tags = []
        self.attributes = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


class ImageAcceptancePreparationTests(unittest.TestCase):
    """確認簡報、品牌、尺寸、HTML 安全及路徑預期已備妥。"""

    def setUp(self):
        self.main = json.loads(
            (ASSETS / "acceptance-test-brief.json").read_text(encoding="utf-8"))
        self.square = json.loads(
            (ASSETS / "acceptance-test-square-brief.json").read_text(encoding="utf-8"))
        self.overflow = json.loads(
            (ASSETS / "acceptance-overflow-brief.json").read_text(encoding="utf-8"))
        self.config = {
            "schema_version": 5,
            "image_production": {
                "default_method": "codex",
                "information_dense_method": "html_css",
                "web_provider": "Fictional Web Model",
                "icon_source": "none",
            },
            "brand_visual": {
                "status": "confirmed",
                "primary_color": "#174A4A",
                "secondary_color": "#E9A23B",
                "background_color": "#F7F4EC",
                "text_color": "#1E2A2A",
                "font_family": "Noto Sans TC",
                "style_notes": "現代編輯式資訊圖卡",
                "logo_ref": None,
                "main_visual_ref": None,
            },
        }

    def test_two_briefs_are_valid_with_traditional_chinese_and_exact_sizes(self):
        """直式三頁與方形單頁可直接交給既有資產契約。"""

        images.validate_brief(self.main)
        images.validate_brief(self.square)
        self.assertEqual((self.main["width"], self.main["height"],
                          len(self.main["pages"])), (1080, 1350, 3))
        self.assertEqual((self.square["width"], self.square["height"],
                          len(self.square["pages"])), (1080, 1080, 1))
        text = "".join(page["exact_text"] for page in self.main["pages"])
        self.assertIn("AI Agent 是什麼？", text)
        self.assertIn("重要動作保留人工確認", text)
        self.assertTrue(any("\u4e00" <= char <= "\u9fff" for char in text))
        images.validate_brief(self.overflow)
        self.assertGreater(len(self.overflow["pages"][0]["exact_text"]), 400)

    def test_four_routes_share_brand_without_writing_config(self):
        """四種方法只改當次 route，不改共用品牌設定。"""

        before = json.dumps(self.config, ensure_ascii=False, sort_keys=True)
        expected = {
            "codex": "direct_generate",
            "antigravity": "direct_generate",
            "web": "deliver_prompt",
            "html_css": "render_html",
        }
        for method, action in expected.items():
            with self.subTest(method=method):
                result = routing.select_route(self.config, method=method)
                self.assertEqual(result["action"], action)
                self.assertEqual(result["visual"]["values"]["primary_color"], "#174A4A")
                self.assertEqual(result["visual"]["values"]["font_family"], "Noto Sans TC")
                self.assertFalse(result["writes_config"])
                self.assertFalse(result["publishing_authorized"])
        self.assertEqual(json.dumps(self.config, ensure_ascii=False, sort_keys=True), before)

    def test_information_dense_and_web_browser_request_are_not_persistent(self):
        """比較表走 HTML；一次網頁代操作不會變成後續長期授權。"""

        self.assertEqual(
            routing.select_route(self.config, information_dense=True)["method"],
            "html_css")
        self.config["image_production"]["default_method"] = "web"
        requested = routing.select_route(self.config, browser_requested=True)
        self.assertEqual(requested["action"], "operate_browser_with_current_request")
        self.assertEqual(routing.select_route(self.config)["action"], "deliver_prompt")
        self.assertNotIn("browser_requested", self.config["image_production"])

    def test_html_fixture_is_local_three_page_and_matches_exact_copy(self):
        """HTML 沒有 script／遠端資源，且三頁都能追溯到簡報原文。"""

        source = (ASSETS / "acceptance-information-card.html").read_text(
            encoding="utf-8")
        parser = CardParser()
        parser.feed(source)
        self.assertEqual(parser.tags.count("article"), 3)
        self.assertNotIn("script", parser.tags)
        for tag, attrs in parser.attributes:
            del tag
            for name in ("src", "href"):
                self.assertNotIn(name, attrs)
        visible = re.sub(r"\s+", "", "".join(parser.text))
        for phrase in ("AIAgent是什麼？", "回答當下問題", "根據目標選擇工具並完成多步驟工作",
                       "接收目標", "選擇工具", "執行任務", "讀回驗證",
                       "重要動作保留人工確認"):
            self.assertIn(phrase, visible)
        self.assertIn('width: 1080px', source)
        self.assertIn('height: 1350px', source)
        self.assertIn("default-src 'none'", source)
        for color in ("#174a4a", "#e9a23b", "#f7f4ec", "#1e2a2a"):
            self.assertIn(color, source.lower())

    def test_acceptance_reference_keeps_runtime_and_handoff_gates_separate(self):
        """準備文件不得把路由、生成、看圖、核准或發布混為一層。"""

        text = (SKILL / "references/acceptance-testing.md").read_text(encoding="utf-8")
        for phrase in (
                "路徑 A：Codex", "路徑 B：Antigravity", "路徑 C：網頁模型",
                "路徑 D：HTML＋CSS", "awaiting_user_images", "awaiting_export",
                "overflow:hidden", "document.fonts.ready", "逐張實際開圖",
                "publishing_authorized", "正式設定 bytes 在測試前後都必須相同"):
            self.assertIn(phrase, text)

    def test_web_prompts_are_complete_and_result_template_starts_not_run(self):
        """三頁網頁提示詞無待填欄位，結果範本不預先宣稱通過。"""

        prompts = (ASSETS / "acceptance-web-prompts.md").read_text(encoding="utf-8")
        self.assertEqual(prompts.count("請製作 1080 × 1350"), 3)
        self.assertNotIn("<從", prompts)
        for page in self.main["pages"]:
            self.assertIn(page["exact_text"], prompts)
        self.assertIn("請把生成的三張圖片傳回來", prompts)
        results = json.loads(
            (ASSETS / "acceptance-result-template.json").read_text(encoding="utf-8"))
        self.assertEqual(
            [item["route"] for item in results["routes"]],
            ["codex", "antigravity", "web", "html_css"])
        self.assertEqual(results["live_status"], "not_performed")
        self.assertFalse(results["all_external_actions_authorized"])
        for item in results["routes"]:
            for key, value in item.items():
                if key not in {"route", "manifest_ref", "notes"}:
                    self.assertEqual(value, "not_run")


if __name__ == "__main__":
    unittest.main()
