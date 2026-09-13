#!/usr/bin/env python3
"""僅以虛構文字與 Pillow 既有測試字型驗證，不呼叫生成服務。"""

import copy
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from .platform_support import symlink_or_skip
except ImportError:
    from platform_support import symlink_or_skip

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/social-image-production/scripts/image_assets.py"
SPEC = importlib.util.spec_from_file_location("image_assets", SCRIPT)
images = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(images)
try:
    from PIL import Image, ImageFont
except ImportError:
    Image = ImageFont = None


@unittest.skipIf(Image is None, "缺少既有 Pillow；不自動安裝，圖片測試未執行")
class ImageProductionTests(unittest.TestCase):
    """真實 PNG 渲染與虛構審核紀錄；不證明真人或中文字型驗收。"""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fictional-social-image-")
        self.root = Path(self.temporary.name).resolve()
        self.font = self.root / "fictional-test-font.ttf"
        # Pillow 既有內建 Latin 字型只在暫存測試使用，不加入公開包。
        self.font.write_bytes(ImageFont.load_default(size=24).path.getvalue())
        self.brief = {
            "schema_version": 1, "input_ref": "fictional-request", "platform": "instagram",
            "kind": "carousel", "width": 400, "height": 500, "visual": "Fictional plant cards",
            "sources": [{"ref": "fictional-copy", "rights": "Fictional original text"}],
            "pages": [
                {"id": "cover", "exact_text": "Indoor plants", "alt_text": "Plant title card"},
                {"id": "light", "exact_text": "Observe the light\nChoose a plant", "alt_text": "Plant tip card"},
            ],
            "layout": {"font_size": 28, "margin": 30, "background": "#17382D", "foreground": "#FFFFFF"},
        }

    def tearDown(self):
        self.temporary.cleanup()

    def render(self, brief=None, name="version-1"):
        directory = self.root / name
        record = images.render(brief or self.brief, self.font, "Pillow bundled test font; local fixture only", directory)
        return record, directory

    def approve(self, record):
        # 明確的虛構同意，只驗證紀錄契約，不表示使用者真的核准。
        record["visual_review"] = {"checked": True, "review_ref": "fictional-review", "checked_at": "2026-09-05T10:00:00+08:00"}
        record["status"] = "approved"
        record["approval"] = {"scope": "images_only", "digest": images.digest(record), "user_response": "Fictional approval", "evidence_ref": "fictional-message", "confirmed_at": "2026-09-05T10:01:00+08:00"}

    def test_render_real_png_and_readonly_check(self):
        record, root = self.render()
        before = {p.name: p.read_bytes() for p in root.iterdir()}
        result = images.check(record, root)
        self.assertEqual(result["count"], 2)
        self.assertFalse(result["publishing_authorized"])
        self.assertEqual(record["brief"]["pages"], self.brief["pages"])
        with Image.open(root / record["assets"][0]["file"]) as im:
            self.assertEqual(im.size, (400, 500))
            self.assertGreater(len(im.getcolors(maxcolors=10000)), 1)
        self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_draft_cannot_handoff_then_fictional_approval_passes(self):
        record, root = self.render()
        with self.assertRaises(images.ImageError):
            images.check(record, root, True)
        self.approve(record)
        self.assertFalse(images.check(record, root, True)["publishing_authorized"])

    def test_copy_order_and_alt_edits_invalidate_approval(self):
        record, root = self.render()
        self.approve(record)
        for key in ("exact_text", "alt_text"):
            changed = copy.deepcopy(record)
            changed["brief"]["pages"][0][key] += " changed"
            with self.assertRaises(images.ImageError):
                images.check(changed, root, True)
        changed = copy.deepcopy(record)
        changed["assets"].reverse()
        changed["brief"]["pages"].reverse()
        with self.assertRaises(images.ImageError):
            images.check(changed, root, True)

    def test_actual_file_edit_is_detected(self):
        record, root = self.render()
        self.approve(record)
        target = root / record["assets"][0]["file"]
        Image.new("RGB", (400, 500), "red").save(target)
        with self.assertRaises(images.ImageError):
            images.check(record, root, True)

    def test_overflow_writes_nothing(self):
        brief = copy.deepcopy(self.brief)
        brief["pages"][1]["exact_text"] = "Long fictional line\n" * 60
        with self.assertRaisesRegex(images.ImageError, "溢位"):
            self.render(brief)
        self.assertFalse((self.root / "version-1").exists())

    def test_existing_output_is_not_overwritten(self):
        record, root = self.render()
        before = (root / "manifest.json").read_bytes()
        with self.assertRaises(images.ImageError):
            self.render()
        self.assertEqual(before, (root / "manifest.json").read_bytes())

    def test_path_escape_duplicate_and_missing_image(self):
        record, root = self.render()
        for path in ("../outside.png", "/outside.png", "sub/file.png", "sub\\file.png"):
            changed = copy.deepcopy(record)
            changed["assets"][0]["file"] = path
            with self.assertRaises(images.ImageError):
                images.check(changed, root)
        changed = copy.deepcopy(record)
        changed["assets"][1]["file"] = changed["assets"][0]["file"]
        with self.assertRaises(images.ImageError):
            images.check(changed, root)
        (root / record["assets"][0]["file"]).rename(root / "preserved.png")
        with self.assertRaises(images.ImageError):
            images.check(record, root)

    def test_symlink_is_rejected(self):
        record, root = self.render()
        target = root / record["assets"][0]["file"]
        target.rename(self.root / "preserved.png")
        symlink_or_skip(self, target, self.root / "preserved.png")
        with self.assertRaises(images.ImageError):
            images.check(record, root)

    def test_symlink_output_parent_is_rejected(self):
        record, root = self.render()
        link = self.root / "linked"
        symlink_or_skip(self, link, root, directory=True)
        with self.assertRaises(images.ImageError):
            images.render(self.brief, self.font, "fixture", link / "new")

    def test_brief_errors_and_missing_font(self):
        for key, value in (("width", True), ("height", 10000), ("sources", []), ("platform", "x"), ("kind", "single")):
            brief = copy.deepcopy(self.brief)
            brief[key] = value
            with self.assertRaises(images.ImageError):
                self.render(brief)
        with self.assertRaises(images.ImageError):
            images.render(self.brief, self.root / "missing.ttf", "fixture", self.root / "new")
        self.assertFalse((self.root / "new").exists())

    def test_unresolved_and_visual_review_block_handoff(self):
        record, root = self.render()
        for review, unresolved in ((None, []), ({"checked": True, "review_ref": "fixture", "checked_at": "2026-09-05T10:00:00+08:00"}, ["rights unknown"])):
            self.approve(record)
            record["visual_review"], record["unresolved"] = review, unresolved
            record["approval"]["digest"] = images.digest(record)
            with self.assertRaises(images.ImageError):
                images.check(record, root, True)

    def test_ai_record_needs_prompt_and_can_check_same_fixture_bytes(self):
        record, root = self.render()
        # 只用模擬 AI 紀錄測契約，這張圖實際來自 Pillow，不宣稱 AI 已生圖。
        record["production"] = {"route": "ai", "tool": "fictional-generator", "model": "unknown", "source_refs": ["fixture"], "created_at": "2026-09-05T10:00:00+08:00"}
        with self.assertRaises(images.ImageError):
            images.check(record, root)
        record["production"]["prompt_ref"] = "fictional-prompt"
        self.assertEqual(images.check(record, root)["result"], "valid")

    def test_html_render_record_can_be_checked_without_ai_claim(self):
        """用虛構 HTML 製作紀錄檢查契約；圖片仍為 Pillow fixture。"""
        record, root = self.render()
        record["production"] = {"route": "html_css", "tool": "fictional-local-renderer", "model": "not_applicable", "source_refs": ["fictional-card.html", "fictional-icon-license"], "created_at": "2026-09-05T10:00:00+08:00"}
        self.assertEqual(images.check(record, root)["result"], "valid")
        record["production"]["model"] = "fictional-ai"
        with self.assertRaises(images.ImageError):
            images.check(record, root)

    def test_jpeg_supported_but_mismatched_extension_rejected(self):
        record, root = self.render()
        asset = record["assets"][0]
        data = io.BytesIO()
        Image.new("RGB", (400, 500), "green").save(data, format="JPEG")
        asset.update(images.asset_info(data.getvalue()))
        (root / asset["file"]).write_bytes(data.getvalue())
        with self.assertRaises(images.ImageError):
            images.check(record, root)
        asset["file"] = "cover.jpg"
        (root / asset["file"]).write_bytes(data.getvalue())
        self.assertEqual(images.check(record, root)["result"], "valid")

    def test_animation_is_rejected(self):
        data = io.BytesIO()
        frame = Image.new("RGB", (100, 100), "red")
        frame.save(data, format="PNG", save_all=True, append_images=[Image.new("RGB", (100, 100), "blue")], duration=100)
        with self.assertRaises(images.ImageError):
            images.asset_info(data.getvalue())

    def test_cli_render_check_and_blocked_exit(self):
        brief = self.root / "brief.json"
        brief.write_text(json.dumps(self.brief), encoding="utf-8")
        target = self.root / "cli-version"
        cmd = [sys.executable, str(SCRIPT), "render", str(brief), "--font", str(self.font), "--font-rights", "fixture", "--output", str(target)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run([sys.executable, str(SCRIPT), "check", str(target / "manifest.json"), "--handoff"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["publishing_authorized"])


class MissingImageRuntimeTests(unittest.TestCase):
    def test_missing_pillow_stops_without_installer(self):
        # 只模擬 import 缺少，不變更實際 Python 環境。
        with patch.dict(sys.modules, {"PIL": None}):
            with self.assertRaisesRegex(images.ImageError, "缺少 Pillow"):
                images.pillow()


if __name__ == "__main__":
    unittest.main()
