#!/usr/bin/env python3
"""虛構文案與媒體需求的資料測試，不使用任何平台或模型。"""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/social-content-writing/scripts/check_drafts.py"
SPEC = importlib.util.spec_from_file_location("writing_check", SCRIPT)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def sample(platform="facebook", form="post"):
    """室內盆栽是虛構題材，來源不會被程式開啟。"""
    return {"schema_version": 1, "input": {"kind": "direct_user", "evidence_ref": "fictional-request"},
            "drafts": [{"id": "draft-a", "platform": platform, "format": form,
                        "title": "換盆前先觀察", "body": "先觀察根系與盆土。你會先檢查哪一項？",
                        "cta_goal": "討論觀察方式", "voice_basis": "使用者指定清楚中性",
                        "sources": ["fictional-article"], "unresolved": [], "media": [],
                        "status": "draft", "approval": None}]}


def approve(record, index=0):
    """只有測試才產生虛構同意，模擬綁定目前整份內容。"""
    draft = record["drafts"][index]
    draft["status"] = "approved"
    draft["approval"] = {"scope": "copy_only", "digest": CHECK.digest(draft, record["input"]),
                         "user_response": "虛構同意這份文案", "evidence_ref": "fictional-response",
                         "confirmed_at": "2026-09-05T12:00:00+08:00"}


class WritingTests(unittest.TestCase):
    """驗證格式與資料關卡，不宣稱模型寫作品質或真人授權。"""

    def test_direct_article_and_planning_inputs(self):
        """直接改寫不必先做規劃；規劃證據只能作為待核對參照。"""
        record = sample()
        self.assertTrue(CHECK.validate(record)["valid"])
        record["input"]["kind"] = "planning"
        self.assertFalse(CHECK.validate(record)["human_approval_verified"])
        del record["input"]["evidence_ref"]
        with self.assertRaises(CHECK.InvalidDraft):
            CHECK.validate(record)

    def test_youtube_utf8_bytes_are_not_chinese_character_count(self):
        """同樣看似短的中文說明也可能超過位元組上限。"""
        record = sample("youtube", "video")
        record["drafts"][0]["body"] = "文" * 1666
        self.assertEqual(CHECK.validate(record)["drafts"][0]["utf8_bytes"], 4998)
        record["drafts"][0]["body"] += "文"
        with self.assertRaises(CHECK.InvalidDraft):
            CHECK.validate(record)

    def test_youtube_title_and_forbidden_angle_brackets(self):
        """獨立測試標題長度與官方不允許的符號。"""
        for field, value in [("title", "文" * 101), ("title", ""), ("body", "<範例>")]:
            record = sample("youtube", "short")
            record["drafts"][0][field] = value
            with self.subTest(field=field), self.assertRaises(CHECK.InvalidDraft):
                CHECK.validate(record)

    def test_threads_body_includes_cta_and_emoji(self):
        """正文的 CTA 及 emoji 都納入 code point 預檢。"""
        record = sample("threads")
        record["drafts"][0]["body"] = "文" * 499 + "🌱"
        self.assertEqual(CHECK.validate(record)["drafts"][0]["characters"], 500)
        record["drafts"][0]["body"] += "？"
        with self.assertRaises(CHECK.InvalidDraft):
            CHECK.validate(record)

    def test_unknown_limits_and_unsupported_destinations(self):
        """未知硬上限只能警告，不能冒充 X 或長文字附件已支援。"""
        self.assertIn("platform_hard_limit_not_verified", CHECK.validate(sample())["drafts"][0]["warnings"])
        for platform, form in [("x", "post"), ("threads", "text_attachment"), ("substack", "note")]:
            with self.subTest(platform=platform), self.assertRaises(CHECK.InvalidDraft):
                CHECK.validate(sample(platform, form))

    def test_instagram_caption_boundary_is_separate_from_overlay(self):
        """Instagram 檢查完整 caption，標籤與發布路線仍需複核。"""
        record = sample("instagram", "carousel")
        record["drafts"][0]["body"] = "文" * 2200
        self.assertTrue(CHECK.validate(record)["valid"])
        record["drafts"][0]["body"] += "文"
        with self.assertRaises(CHECK.InvalidDraft):
            CHECK.validate(record)

    def test_approval_is_not_initial_request_or_publish_permission(self):
        """草稿請求不是版本核准；文案核准不授權發布。"""
        record = sample()
        with self.assertRaises(CHECK.InvalidDraft):
            CHECK.validate(record, handoff=True)
        approve(record)
        self.assertFalse(CHECK.validate(record, handoff=True)["publishing_authorized"])

    def test_changed_copy_media_or_input_invalidates_approval(self):
        """改文字、來源脈絡或媒體需求都不能沿用舊核准。"""
        for change in ("body", "sources", "input", "extra", "media"):
            record = sample()
            approve(record)
            if change == "input":
                record["input"]["evidence_ref"] = "new-request"
            elif change == "sources":
                record["drafts"][0]["sources"].append("new-source")
            elif change == "media":
                record["drafts"][0]["media"] = [{"kind": "image", "status": "needed",
                    "rights": "自製示意圖", "references": [],
                    "brief": {"visual": "盆栽示意", "exact_text": ["新標題"],
                              "aspect_ratio": "4:5 建議", "alt_text": "設計意圖：一盆植物"}}]
            else:
                record["drafts"][0][change] = "新內容"
            with self.subTest(change=change), self.assertRaises(CHECK.InvalidDraft):
                CHECK.validate(record, handoff=True)

    def test_partial_approval_and_unresolved_claims(self):
        """只交接核准版本，不能夾帶未核准或待查主張。"""
        record = sample()
        other = copy.deepcopy(record["drafts"][0])
        other["id"] = "draft-b"
        record["drafts"].append(other)
        approve(record)
        CHECK.validate(record, handoff=True, ids=["draft-a"])
        with self.assertRaises(CHECK.InvalidDraft):
            CHECK.validate(record, handoff=True)
        record["drafts"][0]["unresolved"] = ["尚未核對數字"]
        approve(record)
        with self.assertRaises(CHECK.InvalidDraft):
            CHECK.validate(record, handoff=True, ids=["draft-a"])

    def test_media_routes_and_missing_edit_footage(self):
        """圖片、剪輯、錄製與新影片生成不能混成一條可執行路線。"""
        record = sample()
        media = record["drafts"][0]["media"]
        media.append({"kind": "image", "status": "needed", "rights": "自製構圖",
                      "references": [], "brief": {"visual": "盆栽觀察圖", "exact_text": ["先觀察"],
                                                   "aspect_ratio": "4:5 建議", "alt_text": "設計意圖：盆栽示意"}})
        for kind in ("edit_video", "record_video", "generate_video"):
            media.append({"kind": kind, "status": "needed", "rights": "待製作端確認",
                          "references": ["fictional-footage"] if kind == "edit_video" else [],
                          "brief": {"script": "先觀察盆土。", "shots": ["盆土特寫"],
                                    "duration_target": "30 秒目標", "aspect_ratio": "9:16 建議"}})
        routes = CHECK.validate(record)["drafts"][0]["routes"]
        self.assertEqual(routes, list(CHECK.ROUTES.values()))
        media[1]["references"] = []
        with self.assertRaises(CHECK.InvalidDraft):
            CHECK.validate(record)

    def test_cli_reads_only_and_sanitizes_invalid_json(self):
        """實際執行唯讀命令，不輸出私人文章內容或改檔。"""
        with tempfile.TemporaryDirectory(prefix="fictional-writing-") as directory:
            target = Path(directory) / "draft.json"
            content = json.dumps(sample(), ensure_ascii=False)
            target.write_text(content, encoding="utf-8")
            run = subprocess.run([sys.executable, str(SCRIPT), str(target)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0)
            self.assertNotIn("盆土", run.stdout)
            self.assertEqual(target.read_text(encoding="utf-8"), content)
            target.write_text("fictional-invalid-json", encoding="utf-8")
            run = subprocess.run([sys.executable, str(SCRIPT), str(target)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertNotIn(str(target), run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
