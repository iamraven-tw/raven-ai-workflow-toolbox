#!/usr/bin/env python3
"""Meta 私訊協調器的虛構串接測試；不讀取或傳送真實私訊。"""

from datetime import datetime, timedelta, timezone
import hashlib
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
    "direct_message_execute", SCRIPT_DIR / "direct_message_execute.py")
execute = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(execute)
queue = execute.queue


class FakeAdapter:
    """保留呼叫次數，回傳可控制的虛構 Meta 結果。"""

    def __init__(self):
        self.calls = []
        self.fail_verify = False
        self.fail_send = None
        self.read_errors = []
        self.fetch_result = None
        self.current = None
        self.found = None

    def verify_access(self, scope):
        self.calls.append(("verify", scope["platform"]))
        if self.fail_verify:
            raise execute.DirectMessageAPIError("reauth_required")
        return {"ready": True}

    def fetch_conversations(self, scope):
        self.calls.append(("fetch", scope["platform"]))
        return self.fetch_result

    def read_conversation(self, scope, conversation_id):
        self.calls.append(("read_conversation", conversation_id))
        return self.current

    def send_text(self, grant):
        self.calls.append(("send_text", grant["stage"]))
        if self.fail_send:
            raise execute.DirectMessageAPIError(self.fail_send)
        return {"recipient_id": grant["recipient_id"], "message_id": "reply001"}

    def read_message(self, scope, conversation_id, recipient_id, message_id):
        self.calls.append(("read_message", message_id))
        if self.read_errors:
            raise execute.DirectMessageAPIError(self.read_errors.pop(0))
        return self.readback(message_id, conversation_id, recipient_id)

    def find_sent_message(self, scope, conversation_id, recipient_id, text, after):
        self.calls.append(("find_sent_message", conversation_id))
        if isinstance(self.found, Exception):
            raise self.found
        return self.found or self.readback("reply-observed", conversation_id, recipient_id)

    @staticmethod
    def readback(message_id, conversation_id="t_conversation001",
                 recipient_id="visitor001"):
        return {"message_id": message_id, "conversation_id": conversation_id,
                "recipient_id": recipient_id, "text": "人類確認的私訊回覆。",
                "platform_time": queue.common.now(),
                "observed_at": queue.common.now(), "sender_owned": True,
                "recipient_matches": True, "conversation_matches": True}


class DirectMessageCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-direct-message-execute-")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name).resolve()
        self.adapter = FakeAdapter()
        self.coordinator = execute.DirectMessageCoordinator(
            self.workspace, adapter=self.adapter)

    @staticmethod
    def record(text="虛構訪客訊息"):
        created = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        return {"platform": "facebook", "account_id": "10001",
                "conversation_id": "t_conversation001", "visitor_id": "visitor001",
                "visitor_name": "虛構訪客", "message_id": "message001",
                "message_text": text, "message_created_at": created,
                "context": [{"message_id": "message001", "sender_id": "visitor001",
                             "sender_name": "虛構訪客", "direction": "inbound",
                             "text": text, "created_at": created}],
                "fetched_at": queue.common.now()}

    def state(self):
        return json.loads(queue.state_path(self.workspace).read_text(encoding="utf-8"))

    def prepare(self):
        record = self.record()
        pair = queue.run(self.workspace, "ingest", {
            "platform": "facebook", "account_id": "10001", "records": [record],
            "confirmed_read": True, "approval_ref": "fictional-read-approval",
        })["keys"][0]
        queue.run(self.workspace, "review", pair | {
            "reviewer": "human", "review_ref": "fictional-human-review",
            "decision": "allow", "conversation_summary": "訪客詢問功能。",
            "draft": "人類確認的私訊回覆。",
        })
        session = {"schema_version": 1, "kind": "manual_direct_message_review",
                   "mode": "direct_messages", "status": "complete",
                   "entries": [{"key": pair["key"], "status": "ready"}]}
        relative = "social-media/community/direct-messages/manual-reviews/review001.json"
        path = queue.local(self.workspace, relative)
        path.parent.mkdir(parents=True, mode=0o700)
        path.write_text(json.dumps(session), encoding="utf-8")
        if os.name != "nt":
            os.chmod(path, 0o600)
        queue.run(self.workspace, "prepare", {
            "batch_id": "dm-batch001", "keys": [pair["key"]],
            "review_session_path": relative,
            "review_session_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
        queue.run(self.workspace, "approve", {
            "batch_id": "dm-batch001", "confirmed_reply": True,
            "approval_ref": "fictional-send-approval",
        })
        original = self.state()["items"][pair["key"]]["source"]
        self.adapter.current = original | {"fetched_at": queue.common.now()}
        return pair["key"], original

    @staticmethod
    def command(key):
        return {"batch_id": "dm-batch001", "key": key,
                "allow_token_refresh": False}

    def test_fetch_saves_private_evidence_before_ingest_without_echoing_text(self):
        record = self.record("不應出現在一般輸出")
        self.adapter.fetch_result = {"records": [record], "expired": 1,
                                     "latest_outbound": 2, "unsupported": 3,
                                     "complete": True, "fetched_at": queue.common.now()}
        result = self.coordinator.fetch_api({
            "fetch_id": "dm-fetch001", "scope": {
                "platform": "facebook", "account_id": "10001",
                "approval_ref": "fictional-read-approval", "confirmed_read": True,
                "allow_token_refresh": False, "max_conversations": 10,
            }})
        self.assertEqual(result["screened"], 1)
        self.assertEqual((result["expired"], result["latest_outbound"],
                          result["unsupported"]), (1, 2, 3))
        self.assertNotIn("不應出現在一般輸出", json.dumps(result, ensure_ascii=False))
        evidence = self.workspace / result["fetch_path"]
        self.assertIn("不應出現在一般輸出", evidence.read_text(encoding="utf-8"))
        if os.name != "nt":
            self.assertEqual(evidence.stat().st_mode & 0o777, 0o600)

    def test_access_failure_stops_before_attempt_or_claim(self):
        key, _ = self.prepare()
        self.adapter.fail_verify = True
        with self.assertRaisesRegex(execute.DirectMessageAPIError, "reauth_required"):
            self.coordinator.execute_api(self.command(key))
        self.assertNotIn(key, self.state()["attempts"])

    def test_send_claim_checkpoint_and_readback_complete(self):
        key, _ = self.prepare()
        result = self.coordinator.execute_api(self.command(key))
        self.assertEqual(result, {"result": "replied", "external_write_verified": True})
        self.assertEqual([call[0] for call in self.adapter.calls],
                         ["verify", "read_conversation", "send_text", "read_message"])
        attempt = self.state()["attempts"][key]
        self.assertEqual(attempt["state"], "replied")
        self.assertEqual(attempt["message_created"], "reply001")

    def test_pending_readback_resumes_same_id_without_resending(self):
        key, _ = self.prepare()
        self.adapter.read_errors = [execute.DirectMessageAPIError("read_failed")]
        first = self.coordinator.execute_api(self.command(key))
        self.assertEqual(first["result"], "pending")
        second = self.coordinator.execute_api(self.command(key), resume=True)
        self.assertEqual(second["result"], "replied")
        self.assertEqual(sum(call[0] == "send_text" for call in self.adapter.calls), 1)
        self.assertEqual([call for call in self.adapter.calls if call[0] == "read_message"][-1][1],
                         "reply001")

    def test_unknown_send_never_retries_and_unique_observation_resolves(self):
        key, _ = self.prepare()
        self.adapter.fail_send = "remote_result_unknown"
        first = self.coordinator.execute_api(self.command(key))
        self.assertEqual(first["result"], "unknown")
        self.adapter.fail_send = None
        resolved = self.coordinator.resolve_unknown_api(self.command(key))
        self.assertEqual(resolved["result"], "replied")
        self.assertEqual(sum(call[0] == "send_text" for call in self.adapter.calls), 1)
        self.assertEqual(self.state()["attempts"][key]["message_created"],
                         "reply-observed")

    def test_ambiguous_unknown_observation_keeps_batch_stopped(self):
        key, _ = self.prepare()
        self.adapter.fail_send = "remote_result_unknown"
        self.coordinator.execute_api(self.command(key))
        self.adapter.found = execute.DirectMessageAPIError("ambiguous_readback")
        result = self.coordinator.resolve_unknown_api(self.command(key))
        self.assertEqual(result["result"], "unknown")
        self.assertEqual(self.state()["attempts"][key]["state"], "unknown")

    def test_conversation_changed_stops_before_send_claim(self):
        key, original = self.prepare()
        changed = original | {"message_text": "新的訊息", "fetched_at": queue.common.now()}
        changed["context"] = [original["context"][0] | {"text": "新的訊息"}]
        self.adapter.current = changed
        with self.assertRaisesRegex(ValueError, "conversation_changed"):
            self.coordinator.execute_api(self.command(key))
        self.assertFalse(any(call[0] == "send_text" for call in self.adapter.calls))
        self.assertNotIn(key, self.state()["attempts"])


if __name__ == "__main__":
    unittest.main()
