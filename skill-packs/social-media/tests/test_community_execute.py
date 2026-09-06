#!/usr/bin/env python3
"""留言執行協調器的虛構串接測試；不連線、不回覆真實留言。"""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills/social-community-management/scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

EXEC_SPEC = importlib.util.spec_from_file_location(
    "community_execute", SCRIPT_DIR / "community_execute.py")
execute = importlib.util.module_from_spec(EXEC_SPEC)
EXEC_SPEC.loader.exec_module(execute)
queue = execute.queue


class FakeAdapter:
    """保留呼叫次數並回傳可控制的虛構平台結果。"""

    def __init__(self):
        self.calls = []
        self.fail_verify = False
        self.fail_create = None
        self.container_statuses = ["FINISHED"]
        self.readback_url = "https://www.facebook.com/fictional?comment_id=reply001"
        self.readback_errors = []
        self.owned_reply_ids = []
        self.fetch_result = None

    def verify_access(self, scope):
        self.calls.append(("verify", scope["platform"]))
        if self.fail_verify:
            raise execute.CommunityAPIError("reauth_required")
        return {"ready": True}

    def fetch_comments(self, scope):
        self.calls.append(("fetch", scope["platform"]))
        return self.fetch_result

    def read_comment(self, scope, comment_id, preserved_url):
        self.calls.append(("read_comment", comment_id))
        return self.current

    def own_replies(self, scope, comment_id):
        self.calls.append(("own_replies", comment_id))
        return {"complete": True, "owned_reply_ids": list(self.owned_reply_ids),
                "none_found_complete": not self.owned_reply_ids}

    def create_reply(self, grant):
        self.calls.append(("create_reply", grant["stage"]))
        if self.fail_create:
            raise execute.CommunityAPIError(self.fail_create)
        return {"reply_id": "reply001"}

    def create_threads_container(self, grant):
        self.calls.append(("create_container", grant["stage"]))
        return {"container_id": "82001"}

    def threads_container_status(self, scope, container_id):
        self.calls.append(("container_status", container_id))
        return {"container_id": container_id, "status": self.container_statuses.pop(0)}

    def publish_threads_reply(self, grant, container_id):
        self.calls.append(("publish_reply", grant["stage"], container_id))
        return {"reply_id": "83001"}

    def read_reply(self, scope, reply_target_id, reply_id, preserved_url=None):
        self.calls.append(("read_reply", reply_id))
        if self.readback_errors:
            raise execute.CommunityAPIError(self.readback_errors.pop(0))
        return {"reply_id": reply_id, "reply_target_id": reply_target_id,
                "text": "人類修改後的最終文字。", "platform_time": queue.now(),
                "author_owned": True, "url": self.readback_url,
                "observed_at": queue.now()}


class FakeSheetsCoordinator:
    """模擬每次真正回覆前從審核表重新讀取一次。"""

    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.calls = []

    def current_snapshot(self, batch_id):
        self.calls.append(batch_id)
        self.snapshot["observed_at"] = queue.now()
        return {"snapshot": self.snapshot, "snapshot_path": "fictional-private.json",
                "snapshot_sha256": "0" * 64}


class CommunityCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-community-execute-")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name).resolve()
        self.adapter = FakeAdapter()
        self.coordinator = execute.CommunityCoordinator(self.workspace, adapter=self.adapter)

    @staticmethod
    def record(platform="facebook"):
        urls = {
            "facebook": "https://www.facebook.com/fictional?comment_id=comment001",
            "youtube": "https://www.youtube.com/watch?v=video001&lc=comment001",
            "instagram": "https://www.instagram.com/p/fictional/c/comment001",
            "threads": "https://www.threads.com/@visitor/post/comment001",
            "substack": "https://fictional.substack.com/p/post/comment/comment001",
        }
        account = "10001" if platform in {"facebook", "instagram", "threads"} else "channel001"
        if platform == "substack":
            account = "publication001"
        post_id = "10001_90001" if platform == "facebook" else (
            "video001" if platform == "youtube" else "90001")
        if platform == "substack":
            post_id = "post001"
        return {"platform": platform, "account_id": account, "post_id": post_id,
                "comment_id": "comment001", "reply_target_id": "comment001",
                "visitor_id": "visitor001", "visitor_name": "虛構訪客",
                "post_text": "虛構貼文", "comment_text": "虛構留言",
                "comment_url": urls[platform], "comment_created_at": queue.now(),
                "fetched_at": queue.now()}

    def prepare(self, platform="facebook"):
        """建立已通過本機隔離、六欄讀回與人工回覆確認的批次。"""

        record = self.record(platform)
        ingested = queue.run(self.workspace, "ingest", {
            "platform": platform, "account_id": record["account_id"], "records": [record],
            "confirmed_read": True, "approval_ref": "fictional-read-approval",
            "custom_host": "fictional.substack.com" if platform == "substack" else None,
        })
        key = ingested["keys"][0]["key"]
        queue.run(self.workspace, "review", ingested["keys"][0] | {
            "reviewer": "human", "review_ref": "fictional-human-review", "decision": "allow",
            "post_summary": "貼文摘要", "draft": "原始草稿。",
        })
        binding = {"spreadsheet_id": "fictional-sheet", "sheet_id": 0,
                   "title": "虛構審核表"}
        exported = queue.run(self.workspace, "export", {
            "batch_id": "batch001", "keys": [key], "binding": binding,
            "confirmed_sheet_write": True, "approval_ref": "fictional-sheet-write",
        })
        rows = exported["values"]
        snapshot = {"binding": binding, "observed_at": queue.now(),
                    "rows": [[{"stringValue": value} for value in row] for row in rows]}
        queue.run(self.workspace, "sheet-claim", {"batch_id": "batch001"})
        queue.run(self.workspace, "sheet-write-result", {
            "batch_id": "batch001", "state": "request_accepted"})
        queue.run(self.workspace, "sheet-verify", {
            "batch_id": "batch001", "snapshot": snapshot})
        snapshot["rows"][1][5] = {"stringValue": "人類修改後的最終文字。"}
        snapshot["observed_at"] = queue.now()
        queue.run(self.workspace, "approve", {
            "batch_id": "batch001", "snapshot": snapshot, "confirmed_reply": True,
            "approval_ref": "fictional-reply-approval",
        })
        snapshot["observed_at"] = queue.now()
        self.adapter.current = record | {"fetched_at": queue.now()}
        return key, snapshot, record

    def command(self, key, snapshot):
        return {"batch_id": "batch001", "key": key, "snapshot": snapshot,
                "allow_token_refresh": False}

    def state(self):
        return json.loads((self.workspace / "social-media/community/state.json").read_text())

    def test_fetch_saves_private_evidence_before_ingest_without_echoing_text(self):
        record = self.record("facebook")
        self.adapter.fetch_result = {"records": [record], "missing_url_records": [],
                                     "complete": True, "fetched_at": queue.now()}
        scope = {"platform": "facebook", "account_id": "10001",
                 "post_id": "10001_90001", "approval_ref": "fictional-read-approval",
                 "confirmed_read": True, "allow_token_refresh": False,
                 "url_observations": {}}
        result = self.coordinator.fetch_api({"fetch_id": "fetch001", "scope": scope})
        self.assertEqual(result["result"], "complete")
        self.assertNotIn("虛構留言", json.dumps(result, ensure_ascii=False))
        path = self.workspace / result["fetch_path"]
        self.assertTrue(path.is_file())
        self.assertEqual(len(self.state()["items"]), 1)

    def test_access_failure_happens_before_begin_or_claim(self):
        key, snapshot, _ = self.prepare()
        self.adapter.fail_verify = True
        with self.assertRaisesRegex(execute.CommunityAPIError, "reauth_required"):
            self.coordinator.execute_api(self.command(key, snapshot))
        self.assertEqual(self.state()["attempts"], {})

    def test_facebook_reply_claim_checkpoint_readback_and_receipt(self):
        key, snapshot, _ = self.prepare()
        result = self.coordinator.execute_api(self.command(key, snapshot))
        self.assertEqual(result, {"result": "replied", "external_write_verified": True})
        attempt = self.state()["attempts"][key]
        self.assertEqual(attempt["state"], "replied")
        self.assertEqual(attempt["reply_created"], "reply001")
        self.assertEqual([row["stage"] for row in attempt["operations"]], ["reply_create"])
        self.assertTrue((self.workspace / attempt["receipt"]["evidence_path"]).is_file())

    def test_api_reply_refreshes_sheet_inside_coordinator(self):
        key, snapshot, _ = self.prepare()
        sheets = FakeSheetsCoordinator(snapshot)
        self.coordinator.sheets = sheets
        result = self.coordinator.execute_api({
            "batch_id": "batch001", "key": key, "refresh_sheet": True,
            "allow_token_refresh": False})
        self.assertEqual(result["result"], "replied")
        self.assertEqual(sheets.calls, ["batch001"])
        self.assertNotIn("人類修改後", json.dumps(result, ensure_ascii=False))

    def test_unknown_create_is_not_retried_and_blocks_next_begin(self):
        key, snapshot, _ = self.prepare()
        self.adapter.fail_create = "remote_result_unknown"
        result = self.coordinator.execute_api(self.command(key, snapshot))
        self.assertEqual(result["result"], "unknown")
        self.assertEqual(sum(call[0] == "create_reply" for call in self.adapter.calls), 1)
        with self.assertRaises(ValueError):
            self.coordinator.execute_api(self.command(key, snapshot))
        self.assertEqual(sum(call[0] == "create_reply" for call in self.adapter.calls), 1)

    def test_pending_readback_resumes_same_checkpoint_without_recreating(self):
        key, snapshot, _ = self.prepare()
        self.adapter.readback_errors = ["read_failed"]
        first = self.coordinator.execute_api(self.command(key, snapshot))
        self.assertEqual(first["result"], "pending")
        self.assertEqual(self.state()["attempts"][key]["reply_created"], "reply001")
        self.adapter.owned_reply_ids = ["reply001"]
        snapshot["observed_at"] = queue.now()
        second = self.coordinator.execute_api(self.command(key, snapshot), resume=True)
        self.assertEqual(second["result"], "replied")
        self.assertEqual(sum(call[0] == "create_reply" for call in self.adapter.calls), 1)

    def test_pending_readback_stops_on_unexpected_owned_reply(self):
        key, snapshot, _ = self.prepare()
        self.adapter.readback_errors = ["read_failed"]
        self.coordinator.execute_api(self.command(key, snapshot))
        self.adapter.owned_reply_ids = ["reply001", "reply-by-human"]
        snapshot["observed_at"] = queue.now()
        with self.assertRaisesRegex(execute.CommunityExecuteError, "reply_already_exists"):
            self.coordinator.execute_api(self.command(key, snapshot), resume=True)
        self.assertEqual(sum(call[0] == "create_reply" for call in self.adapter.calls), 1)

    def test_threads_pending_container_resumes_without_recreating(self):
        key, snapshot, record = self.prepare("threads")
        self.adapter.current = record | {"fetched_at": queue.now()}
        self.adapter.container_statuses = ["IN_PROGRESS", "FINISHED"]
        self.adapter.readback_url = "https://www.threads.com/@owner/post/reply001"
        first = self.coordinator.execute_api(self.command(key, snapshot))
        self.assertEqual(first["result"], "pending")
        snapshot["observed_at"] = queue.now()
        second = self.coordinator.execute_api(self.command(key, snapshot), resume=True)
        self.assertEqual(second["result"], "replied")
        self.assertEqual(sum(call[0] == "create_container" for call in self.adapter.calls), 1)
        self.assertEqual(sum(call[0] == "publish_reply" for call in self.adapter.calls), 1)
        attempt = self.state()["attempts"][key]
        self.assertEqual(attempt["container_created"], "82001")
        self.assertEqual(attempt["reply_created"], "83001")

    def test_missing_api_permalink_waits_for_browser_observation(self):
        key, snapshot, record = self.prepare("instagram")
        self.adapter.current = record | {"fetched_at": queue.now()}
        self.adapter.readback_url = None
        first = self.coordinator.execute_api(self.command(key, snapshot))
        self.assertEqual(first["reason"], "browser_permalink_observation_required")
        self.assertEqual(self.state()["attempts"][key]["state"], "pending")
        observed = {"reply_id": "reply001", "reply_target_id": "comment001",
                    "text": "人類修改後的最終文字。",
                    "url": "https://www.instagram.com/p/fictional/c/reply001",
                    "platform_time": queue.now(), "observed_at": queue.now(),
                    "author_owned": True}
        final = self.coordinator.record_observation(
            {"batch_id": "batch001", "key": key, "observation": observed})
        self.assertEqual(final["result"], "replied")

    def test_substack_browser_handoff_claims_before_external_action(self):
        key, snapshot, record = self.prepare("substack")
        handoff = self.coordinator.prepare_browser_reply({
            "batch_id": "batch001", "key": key, "snapshot": snapshot,
            "current": record | {"fetched_at": queue.now()},
            "own_reply_check": "none_found_complete",
        })
        self.assertFalse(handoff["external_write_performed"])
        self.assertNotIn("人類修改後", json.dumps(handoff, ensure_ascii=False))
        handoff_path = self.workspace / handoff["handoff_path"]
        self.assertEqual(handoff_path.stat().st_mode & 0o777, 0o600)
        observed = {"reply_id": "reply001", "reply_target_id": "comment001",
                    "text": "人類修改後的最終文字。",
                    "url": "https://fictional.substack.com/p/post/comment/reply001",
                    "platform_time": queue.now(), "observed_at": queue.now(),
                    "author_owned": True}
        result = self.coordinator.record_observation(
            {"batch_id": "batch001", "key": key, "observation": observed})
        self.assertEqual(result["result"], "replied")
        attempt = self.state()["attempts"][key]
        self.assertEqual(attempt["operations"][0]["stage"], "browser_reply")
        self.assertEqual(attempt["reply_created"], "reply001")

    def test_browser_reply_refreshes_sheet_inside_coordinator(self):
        key, snapshot, record = self.prepare("substack")
        sheets = FakeSheetsCoordinator(snapshot)
        self.coordinator.sheets = sheets
        handoff = self.coordinator.prepare_browser_reply({
            "batch_id": "batch001", "key": key, "refresh_sheet": True,
            "current": record | {"fetched_at": queue.now()},
            "own_reply_check": "none_found_complete",
        })
        self.assertEqual(handoff["result"], "browser_handoff_ready")
        self.assertEqual(sheets.calls, ["batch001"])

    def test_browser_unknown_observation_stops_without_checkpoint(self):
        key, snapshot, record = self.prepare("substack")
        self.coordinator.prepare_browser_reply({
            "batch_id": "batch001", "key": key, "snapshot": snapshot,
            "current": record | {"fetched_at": queue.now()},
            "own_reply_check": "none_found_complete",
        })
        result = self.coordinator.record_observation({
            "batch_id": "batch001", "key": key,
            "observation": {"state": "unknown"}})
        self.assertEqual(result["result"], "unknown")
        self.assertNotIn("reply_created", self.state()["attempts"][key])

    def test_claim_is_single_use_and_checkpoint_requires_matching_claim(self):
        key, snapshot, record = self.prepare()
        queue.run(self.workspace, "begin", {
            "batch_id": "batch001", "key": key, "snapshot": snapshot,
            "current": record | {"fetched_at": queue.now()},
            "own_reply_check": "none_found_complete"})
        queue.run(self.workspace, "claim", {
            "batch_id": "batch001", "key": key, "stage": "reply_create"})
        with self.assertRaisesRegex(ValueError, "stage_already_claimed"):
            queue.run(self.workspace, "claim", {
                "batch_id": "batch001", "key": key, "stage": "reply_create"})
        with self.assertRaisesRegex(ValueError, "stage_claim_required"):
            queue.run(self.workspace, "checkpoint", {
                "batch_id": "batch001", "key": key, "stage": "reply_created",
                "claim_stage": "reply_publish", "remote_id": "reply001"})


if __name__ == "__main__":
    unittest.main()
