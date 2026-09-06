#!/usr/bin/env python3
"""六欄 Sheets 協調器的虛構端到端測試；不連線、不使用 Google 帳號。"""

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills/social-community-management/scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location(
    "community_sheets", SCRIPT_DIR / "community_sheets.py")
community_sheets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(community_sheets)
queue = community_sheets.queue


class FakeSheets:
    """模擬固定綁定、一次寫入與型別化讀回。"""

    def __init__(self):
        self.calls = []
        self.values = None
        self.fail_empty = None
        self.fail_write = None
        self.fail_read = None
        self.mutate = None

    def require_empty(self, binding):
        self.calls.append(("empty", dict(binding)))
        if self.fail_empty:
            raise community_sheets.SheetsAPIError(self.fail_empty)
        return {"result": "empty"}

    def write_values(self, claim):
        self.calls.append(("write", claim["range"], claim["valueInputOption"]))
        self.values = [list(row) for row in claim["values"]]
        if self.fail_write:
            raise community_sheets.SheetsAPIError(self.fail_write)
        return {"result": "request_accepted"}

    def read_snapshot(self, binding, row_count):
        self.calls.append(("read", row_count))
        if self.fail_read:
            raise community_sheets.SheetsAPIError(self.fail_read)
        values = self.values
        if values is None:
            # 代表程序於 claim／送出後中斷；遠端讀回發現內容已存在。
            raise AssertionError("測試必須先提供遠端值")
        rows = [[{"stringValue": value} for value in row] for row in values]
        if self.mutate:
            rows = self.mutate(rows)
        return {"binding": dict(binding), "observed_at": queue.now(), "rows": rows}


class CommunitySheetsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-community-sheets-")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name).resolve()
        self.adapter = FakeSheets()
        self.coordinator = community_sheets.CommunitySheetsCoordinator(
            self.workspace, adapter=self.adapter)
        self.binding = {"spreadsheet_id": "fictional-sheet", "sheet_id": 0,
                        "title": "虛構留言審核"}
        self.record = {
            "platform": "facebook", "account_id": "page001", "post_id": "post001",
            "comment_id": "comment001", "reply_target_id": "comment001",
            "visitor_id": "visitor001", "visitor_name": "虛構訪客",
            "post_text": "虛構貼文", "comment_text": "虛構留言",
            "comment_url": "https://www.facebook.com/post001?comment_id=comment001",
            "comment_created_at": queue.now(), "fetched_at": queue.now(),
        }

    def ready(self):
        ingested = queue.run(self.workspace, "ingest", {
            "platform": "facebook", "account_id": "page001", "records": [self.record],
            "confirmed_read": True, "approval_ref": "fictional-read-approval"})
        pair = ingested["keys"][0]
        queue.run(self.workspace, "review", pair | {
            "reviewer": "human", "review_ref": "fictional-review", "decision": "allow",
            "post_summary": "虛構摘要", "draft": "虛構回覆草稿"})
        return pair["key"]

    def request(self, key):
        return {"batch_id": "batch001", "keys": [key], "binding": self.binding,
                "confirmed_sheet_write": True,
                "approval_ref": "fictional-sheet-write-approval"}

    def state(self):
        return json.loads((self.workspace / "social-media/community/state.json").read_text())

    def written(self):
        key = self.ready()
        result = self.coordinator.write_batch(self.request(key))
        return key, result

    def test_write_preflight_claim_raw_once_readback_and_private_evidence(self):
        _, result = self.written()
        self.assertEqual(result["result"], "awaiting_approval")
        self.assertEqual([call[0] for call in self.adapter.calls],
                         ["empty", "write", "read"])
        self.assertEqual(self.adapter.calls[1][2], "RAW")
        self.assertEqual(self.state()["batches"]["batch001"]["sheet_operation"]["state"],
                         "readback_verified")
        evidence = self.workspace / result["snapshot_path"]
        self.assertTrue(evidence.is_file())
        if os.name != "nt":
            self.assertEqual(evidence.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("虛構留言", json.dumps(result, ensure_ascii=False))

    def test_unknown_write_is_never_resent_and_resume_reads_only(self):
        key = self.ready()
        self.adapter.fail_write = "remote_result_unknown"
        first = self.coordinator.write_batch(self.request(key))
        self.assertEqual(first["result"], "unknown")
        self.assertEqual(sum(call[0] == "write" for call in self.adapter.calls), 1)
        self.adapter.fail_write = None
        self.adapter.values = self.state()["batches"]["batch001"]["rows"].values()
        self.adapter.values = [queue.HEADERS, *[list(row) for row in self.adapter.values]]
        second = self.coordinator.resume_write({"batch_id": "batch001"})
        self.assertEqual(second["result"], "awaiting_approval")
        self.assertEqual(sum(call[0] == "write" for call in self.adapter.calls), 1)

    def test_claimed_crash_resume_only_reads_but_unclaimed_resume_writes_once(self):
        key = self.ready()
        exported = queue.run(self.workspace, "export", self.request(key))
        queue.run(self.workspace, "sheet-claim", {"batch_id": "batch001"})
        self.adapter.values = exported["values"]
        result = self.coordinator.resume_write({"batch_id": "batch001"})
        self.assertEqual(result["result"], "awaiting_approval")
        self.assertEqual(sum(call[0] == "write" for call in self.adapter.calls), 0)

        with tempfile.TemporaryDirectory(prefix="fictional-unclaimed-") as directory:
            workspace = Path(directory).resolve()
            other_adapter = FakeSheets()
            other = community_sheets.CommunitySheetsCoordinator(
                workspace, adapter=other_adapter)
            ingested = queue.run(workspace, "ingest", {
                "platform": "facebook", "account_id": "page001", "records": [self.record],
                "confirmed_read": True, "approval_ref": "read"})
            pair = ingested["keys"][0]
            queue.run(workspace, "review", pair | {"reviewer": "human",
                "review_ref": "review", "decision": "allow", "post_summary": "摘要",
                "draft": "草稿"})
            queue.run(workspace, "export", {"batch_id": "batch002", "keys": [pair["key"]],
                "binding": self.binding, "confirmed_sheet_write": True,
                "approval_ref": "write"})
            done = other.resume_write({"batch_id": "batch002"})
            self.assertEqual(done["result"], "awaiting_approval")
            self.assertEqual(sum(call[0] == "write" for call in other_adapter.calls), 1)

    def test_failed_write_is_not_resumable(self):
        key = self.ready()
        self.adapter.fail_write = "permission_mismatch"
        self.assertEqual(self.coordinator.write_batch(self.request(key))["result"], "failed")
        with self.assertRaisesRegex(community_sheets.CommunitySheetsError,
                                    "sheet_write_failed_no_retry"):
            self.coordinator.resume_write({"batch_id": "batch001"})
        self.assertEqual(sum(call[0] == "write" for call in self.adapter.calls), 1)

    def test_nonempty_sheet_stops_before_export_or_claim(self):
        key = self.ready()
        self.adapter.fail_empty = "sheet_not_empty"
        with self.assertRaisesRegex(community_sheets.SheetsAPIError, "sheet_not_empty"):
            self.coordinator.write_batch(self.request(key))
        self.assertFalse(self.state()["batches"])
        self.assertEqual(self.state()["items"][key]["state"], "ready")

    def test_formula_readback_is_rejected_and_can_be_inspected_without_resend(self):
        key = self.ready()
        self.adapter.mutate = lambda rows: rows[:1] + [
            rows[1][:5] + [{"formulaValue": "=IMPORTDATA(\"x\")"}]]
        result = self.coordinator.write_batch(self.request(key))
        self.assertEqual(result["result"], "mismatch")
        self.assertEqual(sum(call[0] == "write" for call in self.adapter.calls), 1)
        self.assertEqual(self.state()["batches"]["batch001"]["status"],
                         "sheet_write_pending")

    def test_approval_rereads_final_f_and_reply_preflight_rereads_again(self):
        key, _ = self.written()
        def final_text(rows):
            rows[1][5] = {"stringValue": "人類最後核准文字"}
            return rows
        self.adapter.mutate = final_text
        approved = self.coordinator.approve_batch({
            "batch_id": "batch001", "confirmed_reply": True,
            "approval_ref": "fictional-reply-approval"})
        self.assertEqual(approved["result"], "approved")
        self.assertEqual(self.state()["batches"]["batch001"]["replies"][key],
                         "人類最後核准文字")
        before = sum(call[0] == "read" for call in self.adapter.calls)
        current = self.coordinator.current_snapshot("batch001")
        self.assertEqual(sum(call[0] == "read" for call in self.adapter.calls), before + 1)
        self.assertIn("snapshot", current)
        public = community_sheets.run(
            self.workspace, "read-for-reply", {"batch_id": "batch001"},
            adapter=self.adapter)
        self.assertNotIn("snapshot", public)
        self.assertNotIn("人類最後核准文字", json.dumps(public, ensure_ascii=False))

    def test_whole_row_reorder_preserves_mapping_at_approval(self):
        # queue 本身以第一至五欄映射，不依試算表列號；此處以兩列驗證整合層。
        first = self.ready()
        other_record = self.record | {
            "comment_id": "comment002", "reply_target_id": "comment002",
            "comment_url": "https://www.facebook.com/post001?comment_id=comment002"}
        ingested = queue.run(self.workspace, "ingest", {
            "platform": "facebook", "account_id": "page001", "records": [other_record],
            "confirmed_read": True, "approval_ref": "read"})
        second_pair = ingested["keys"][0]
        second = second_pair["key"]
        queue.run(self.workspace, "review", second_pair | {"reviewer": "human",
            "review_ref": "review", "decision": "allow", "post_summary": "摘要二",
            "draft": "草稿二"})
        self.coordinator.write_batch(self.request(first) | {"keys": [first, second]})
        self.adapter.mutate = lambda rows: rows[:1] + list(reversed(rows[1:]))
        approved = self.coordinator.approve_batch({"batch_id": "batch001",
            "confirmed_reply": True, "approval_ref": "reply"})
        self.assertEqual(approved["reply_count"], 2)
        self.assertEqual(set(self.state()["batches"]["batch001"]["replies"]),
                         {first, second})


if __name__ == "__main__":
    unittest.main()
