"""用虛構研究與人類回覆驗證資料關卡；不模擬成真實 Agent 驗收。"""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/social-content-planning/scripts/check_planning.py"
SPEC = importlib.util.spec_from_file_location("planning_check", SCRIPT)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def research_record():
    """所有網址、作者與數字都是測試虛構資料。"""
    platforms = ["facebook", "instagram", "threads", "youtube", "x"]
    return {
        "schema_version": 1, "phase": "awaiting_direction", "topic": "虛構盆栽換盆", "goal": "提供初學者可操作的知識",
        "audience": "室內盆栽初學者", "decision": None, "calendar": [], "briefs": [],
        "research": {"version": "r1", "as_of": "2026-09-05", "window_start": "2026-08-06", "window_end": "2026-09-05",
                     "platforms": platforms, "presented_at": "2026-09-05T10:00:00+08:00", "limitations": ["完全虛構，不是平台樣本"],
                     "coverage": [{"platform": p, "queries": ["虛構換盆 問題"], "method": "public_search", "status": "checked",
                                   "note": "只跑指定的小輪查詢"} for p in platforms],
                     "cases": [{"id": f"c{i}", "platform": p, "url": f"https://example.test/posts/{i}",
                                "author": f"虛構作者{i}", "published_at": "2026-09-01", "observed_at": "2026-09-05",
                                "read_scope": "primary", "safety": "usable", "summary": "示範盆器與根系檢查",
                                "angle": "操作前的判斷", "format": "圖文", "metrics": [
                                    {"name": "公開讚數", "status": "observed", "value": 0, "observed_at": "2026-09-05"},
                                    {"name": "觸及", "status": "unavailable", "value": None, "observed_at": "2026-09-05"}]} for i, p in enumerate(platforms[:3])]}}


def approved_record():
    """只用於測試的虛構決定，正式執行不能由 Agent 捏造。"""
    record = research_record()
    record["phase"] = "planning"
    record["decision"] = {"research_version": "r1", "choice": "proceed", "direction": "聚焦是否需要換盆",
                          "user_response": "虛構回覆：先教大家判斷，不重複別人的完整教學。",
                          "confirmed_at": "2026-09-05T10:05:00+08:00", "evidence_ref": "fictional-turn-2"}
    record["calendar"] = [{"topic": "先判斷再換盆", "platform": "instagram", "slot": "第 1 篇", "timezone": "Asia/Taipei", "status": "draft"}]
    record["briefs"] = [{"topic": "先判斷再換盆", "platform": "instagram", "role": "圖像判斷教學", "angle": "先判斷",
                         "audience": "初學者", "cta_goal": "保存檢查清單", "media": "輪播圖", "source_case_ids": ["c0"],
                         "fact_sources": ["https://example.test/fictional-first-party-guide"], "unverified_claims": [],
                         "handoff": "social-image-production"}]
    return record


class PlanningTests(unittest.TestCase):
    """結構化行為關卡不以特定文件措辭判定成功。"""
    def test_briefing_stops_before_calendar(self):
        record = research_record()
        result = CHECK.validate(record)
        self.assertFalse(result["human_approval_verified"])
        self.assertEqual(result["phase"], "awaiting_direction")
        record["calendar"] = approved_record()["calendar"]
        with self.assertRaises(CHECK.InvalidRecord):
            CHECK.validate(record)

    def test_initial_topic_is_not_a_decision(self):
        record = research_record()
        record["phase"] = "planning"
        with self.assertRaises(CHECK.InvalidRecord):
            CHECK.validate(record)

    def test_confirmed_direction_allows_local_draft(self):
        record = approved_record()
        before = copy.deepcopy(record)
        self.assertTrue(CHECK.validate(record, complete=True)["valid"])
        self.assertEqual(before, record)

    def test_old_or_early_decision_is_rejected(self):
        for field, value in (("research_version", "old"), ("confirmed_at", "2026-09-05T09:00:00+08:00")):
            record = approved_record()
            record["decision"][field] = value
            with self.assertRaises(CHECK.InvalidRecord):
                CHECK.validate(record)

    def test_defer_and_abandon_have_no_handoff(self):
        for phase, choice in (("deferred", "defer"), ("abandoned", "abandon")):
            record = approved_record()
            record["phase"], record["decision"]["choice"] = phase, choice
            with self.assertRaises(CHECK.InvalidRecord):
                CHECK.validate(record)
            record["calendar"], record["briefs"] = [], []
            self.assertTrue(CHECK.validate(record)["valid"])

    def test_no_results_and_blocked_platforms_do_not_become_empty_market(self):
        record = research_record()
        record["research"]["cases"] = []
        record["research"]["coverage"][0].update(status="blocked", note="虛構登入牆")
        result = CHECK.validate(record)
        self.assertEqual(result["warnings"], ["limited_cases", "limited_coverage"])
        self.assertEqual(result["phase"], "awaiting_direction")

    def test_missing_platform_cannot_be_silently_skipped(self):
        record = research_record()
        record["research"]["coverage"].pop()
        with self.assertRaises(CHECK.InvalidRecord):
            CHECK.validate(record)

    def test_zero_unavailable_and_rounded_display_are_distinct(self):
        record = research_record()
        self.assertTrue(CHECK.validate(record)["valid"])
        record["research"]["cases"][0]["metrics"][0]["value"] = "1.2K"
        self.assertTrue(CHECK.validate(record)["valid"])
        record["research"]["cases"][0]["metrics"][1]["value"] = 0
        with self.assertRaises(CHECK.InvalidRecord):
            CHECK.validate(record)

    def test_duplicate_source_tracking_links_are_not_independent_cases(self):
        record = research_record()
        duplicate = copy.deepcopy(record["research"]["cases"][0])
        duplicate.update(id="duplicate", url=duplicate["url"] + "?utm_source=fictional")
        record["research"]["cases"].append(duplicate)
        with self.assertRaises(CHECK.InvalidRecord):
            CHECK.validate(record)

    def test_snippet_or_excluded_source_cannot_be_handed_off(self):
        for changes in ({"read_scope": "snippet_only"}, {"safety": "excluded", "summary": ""}):
            record = approved_record()
            record["research"]["cases"][0].update(changes)
            with self.assertRaises(CHECK.InvalidRecord):
                CHECK.validate(record)

    def test_x_is_research_only_and_calendar_is_not_remote_schedule(self):
        for changes in ({"platform": "x"}, {"status": "scheduled"}):
            record = approved_record()
            record["calendar"][0].update(changes)
            with self.assertRaises(CHECK.InvalidRecord):
                CHECK.validate(record)

    def test_unknown_or_old_publication_is_a_warning_not_recent_evidence(self):
        record = research_record()
        record["research"]["cases"][0]["published_at"] = None
        record["research"]["cases"][1]["published_at"] = "2020-01-01"
        result = CHECK.validate(record)
        self.assertIn("outside_window", result["warnings"])
        self.assertIn("publication_date_unknown", result["warnings"])

    def test_cli_only_reads_local_record_and_hides_content(self):
        with tempfile.TemporaryDirectory(prefix="fictional-planning-") as folder:
            path = Path(folder) / "record.json"
            text = json.dumps(approved_record(), ensure_ascii=False)
            path.write_text(text, encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), str(path), "--complete"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("虛構", result.stdout)
            self.assertNotIn("example.test", result.stdout)
            self.assertEqual(path.read_text(encoding="utf-8"), text)
            self.assertEqual(list(Path(folder).iterdir()), [path])


if __name__ == "__main__":
    unittest.main()
