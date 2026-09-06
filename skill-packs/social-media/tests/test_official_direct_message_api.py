#!/usr/bin/env python3
"""Meta 私訊官方 adapter 的虛構 HTTP 測試；不連線真實平台。"""

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills/social-community-management/scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location(
    "official_direct_message_api", SCRIPT_DIR / "official_direct_message_api.py")
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)


NOW = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


class FakeRuntime:
    """模擬 setup Runtime，只回傳虛構 Token 與非敏感資源識別。"""

    def __init__(self, route, target_id):
        self.route = route
        self.target_id = target_id
        self.calls = []

    def config(self):
        scopes = {
            "facebook_pages": ["pages_messaging", "pages_manage_metadata",
                               "pages_read_engagement"],
            "instagram_login": ["instagram_business_basic",
                                "instagram_business_manage_messages"],
            "instagram_facebook_login": ["instagram_basic",
                                         "instagram_manage_messages",
                                         "pages_manage_metadata"],
        }[self.route]
        return {"target_id": self.target_id, "login_route": self.route,
                "graph_version": "v23.0", "scopes": scopes}

    def access(self, **kwargs):
        self.calls.append(("access", kwargs))
        return "fictional-token"

    def resource_context(self, **kwargs):
        self.calls.append(("resource_context", kwargs))
        value = {"platform": "instagram" if self.route.startswith("instagram") else "facebook",
                 "login_route": self.route, "target_id": self.target_id,
                 "graph_version": "v23.0"}
        if self.route == "instagram_facebook_login":
            value["page_id"] = "30001"
        return value


class FakeHTTP:
    """依序回傳虛構 Meta JSON，並保留固定端點呼叫。"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request_json(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint, kwargs))
        if not self.responses:
            raise AssertionError("unexpected HTTP call")
        return api.HTTPResult(200, self.responses.pop(0))


class OfficialDirectMessageAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-direct-message-api-")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name).resolve()

    @staticmethod
    def scope(platform="facebook", account_id="10001", maximum=5):
        return {"platform": platform, "account_id": account_id,
                "approval_ref": "fictional-read-approval", "confirmed_read": True,
                "allow_token_refresh": False, "max_conversations": maximum}

    @staticmethod
    def runtime_factory(route, target_id):
        runtime = FakeRuntime(route, target_id)
        return runtime, lambda *_args: runtime

    @staticmethod
    def conversation_list(conversation_id="t_conversation001"):
        return {"data": [{"id": conversation_id,
                           "updated_time": "2026-09-06T11:50:00+0000"}]}

    @staticmethod
    def message_list(message_id="message001"):
        return {"id": "t_conversation001",
                "messages": {"data": [{"id": message_id,
                                          "created_time": "2026-09-06T11:50:00+0000"}]}}

    @staticmethod
    def detail(*, message_id="message001", sender="visitor001", recipient="10001",
               text="虛構訪客訊息", created="2026-09-06T11:50:00+0000"):
        return {"id": message_id, "created_time": created,
                "from": {"id": sender, "name": "虛構訪客"},
                "to": {"data": [{"id": recipient, "name": "虛構帳號"}]},
                "message": text}

    def test_invalid_scope_and_http_allowlist_stop_before_network(self):
        _, factory = self.runtime_factory("facebook_pages", "10001")
        adapter = api.OfficialDirectMessageAdapter(
            self.workspace, runtime_factory=factory, http_transport=FakeHTTP([]),
            clock=lambda: NOW)
        with self.assertRaisesRegex(api.DirectMessageAPIError, "authorization_required"):
            adapter.verify_access(self.scope() | {"max_conversations": 100})
        transport = api.OfficialDirectMessageHTTP()
        with self.assertRaisesRegex(api.DirectMessageAPIError, "invalid_request"):
            transport.request_json("GET", "https://example.com/v23.0/10001/conversations",
                                   bearer="fictional")
        with self.assertRaisesRegex(api.DirectMessageAPIError, "invalid_request"):
            transport.request_json(
                "GET", "https://graph.facebook.com/v23.0/10001/conversations",
                query={"access_token": "fictional"}, bearer="fictional")

    def test_facebook_fetch_only_returns_latest_inbound_within_24_hours(self):
        runtime, factory = self.runtime_factory("facebook_pages", "10001")
        http = FakeHTTP([self.conversation_list(), self.message_list(), self.detail()])
        adapter = api.OfficialDirectMessageAdapter(
            self.workspace, runtime_factory=factory, http_transport=http,
            clock=lambda: NOW)
        result = adapter.fetch_conversations(self.scope())
        self.assertEqual(len(result["records"]), 1)
        record = result["records"][0]
        self.assertEqual(record["visitor_id"], "visitor001")
        self.assertEqual(record["context"][0]["direction"], "inbound")
        self.assertTrue(result["complete"])
        self.assertEqual(http.calls[0][1],
                         "https://graph.facebook.com/v23.0/10001/conversations")
        self.assertEqual(runtime.calls[0][0], "access")

    def test_expired_latest_outbound_and_non_text_are_separate_states(self):
        _, factory = self.runtime_factory("facebook_pages", "10001")
        expired = (NOW - timedelta(hours=25)).isoformat()
        http = FakeHTTP([
            {"data": [{"id": "t_expired"}, {"id": "t_outbound"},
                      {"id": "t_unsupported"}]},
            {"messages": {"data": [{"id": "expired001"}]}},
            self.detail(message_id="expired001", created=expired),
            {"messages": {"data": [{"id": "outbound001"}]}},
            self.detail(message_id="outbound001", sender="10001",
                        recipient="visitor001"),
            {"messages": {"data": [{"id": "unsupported001"}]}},
            {"id": "unsupported001", "created_time": NOW.isoformat(),
             "from": {"id": "visitor001"}, "to": {"data": [{"id": "10001"}]},
             "message": ""},
        ])
        adapter = api.OfficialDirectMessageAdapter(
            self.workspace, runtime_factory=factory, http_transport=http,
            clock=lambda: NOW)
        result = adapter.fetch_conversations(self.scope())
        self.assertEqual((result["expired"], result["latest_outbound"],
                          result["unsupported"]), (1, 1, 1))
        self.assertEqual(result["records"], [])

    def test_instagram_direct_login_uses_instagram_host_and_ig_account_id(self):
        _, factory = self.runtime_factory("instagram_login", "20001")
        http = FakeHTTP([
            self.conversation_list(), self.message_list(),
            self.detail(recipient="20001"),
        ])
        adapter = api.OfficialDirectMessageAdapter(
            self.workspace, runtime_factory=factory, http_transport=http,
            clock=lambda: NOW)
        result = adapter.fetch_conversations(self.scope("instagram", "20001"))
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(http.calls[0][1],
                         "https://graph.instagram.com/v23.0/20001/conversations")
        self.assertEqual(http.calls[0][2]["query"]["platform"], "instagram")

    def test_instagram_facebook_login_uses_page_for_conversations_and_ig_for_send(self):
        _, factory = self.runtime_factory("instagram_facebook_login", "20001")
        http = FakeHTTP([self.conversation_list(), self.message_list(),
                         self.detail(recipient="20001")])
        adapter = api.OfficialDirectMessageAdapter(
            self.workspace, runtime_factory=factory, http_transport=http,
            clock=lambda: NOW)
        adapter.fetch_conversations(self.scope("instagram", "20001"))
        self.assertEqual(http.calls[0][1],
                         "https://graph.facebook.com/v23.0/30001/conversations")
        send_http = FakeHTTP([{"recipient_id": "visitor001", "message_id": "reply001"}])
        adapter.http = send_http
        result = adapter.send_text({
            "platform": "instagram", "account_id": "20001",
            "conversation_id": "t_conversation001", "recipient_id": "visitor001",
            "text": "虛構回覆", "approval_ref": "fictional-send-approval",
            "transaction_status": "in_flight", "stage": "message_send",
            "allow_token_refresh": False,
        })
        self.assertEqual(result["message_id"], "reply001")
        self.assertEqual(send_http.calls[0][1],
                         "https://graph.facebook.com/v23.0/20001/messages")
        self.assertNotIn("messaging_type", send_http.calls[0][2]["json_body"])

    def test_facebook_send_is_response_and_readback_verifies_conversation(self):
        _, factory = self.runtime_factory("facebook_pages", "10001")
        http = FakeHTTP([{"recipient_id": "visitor001", "message_id": "reply001"}])
        adapter = api.OfficialDirectMessageAdapter(
            self.workspace, runtime_factory=factory, http_transport=http,
            clock=lambda: NOW)
        created = adapter.send_text({
            "platform": "facebook", "account_id": "10001",
            "conversation_id": "t_conversation001", "recipient_id": "visitor001",
            "text": "虛構回覆", "approval_ref": "fictional-send-approval",
            "transaction_status": "in_flight", "stage": "message_send",
            "allow_token_refresh": False,
        })
        self.assertEqual(created["message_id"], "reply001")
        self.assertEqual(http.calls[0][2]["json_body"]["messaging_type"], "RESPONSE")
        adapter.http = FakeHTTP([
            {"messages": {"data": [{"id": "reply001"}]}},
            self.detail(message_id="reply001", sender="10001",
                        recipient="visitor001", text="虛構回覆",
                        created="2026-09-06T12:00:00+0000"),
        ])
        readback = adapter.read_message(
            self.scope(), "t_conversation001", "visitor001", "reply001")
        self.assertTrue(readback["sender_owned"])
        self.assertTrue(readback["conversation_matches"])

    def test_unknown_resolution_requires_one_exact_sent_message(self):
        _, factory = self.runtime_factory("facebook_pages", "10001")
        adapter = api.OfficialDirectMessageAdapter(
            self.workspace, runtime_factory=factory,
            http_transport=FakeHTTP([
                {"messages": {"data": [{"id": "reply001"}]}},
                self.detail(message_id="reply001", sender="10001",
                            recipient="visitor001", text="虛構回覆",
                            created="2026-09-06T12:00:00+0000"),
                {"messages": {"data": [{"id": "reply001"}]}},
                self.detail(message_id="reply001", sender="10001",
                            recipient="visitor001", text="虛構回覆",
                            created="2026-09-06T12:00:00+0000"),
            ]), clock=lambda: NOW)
        readback = adapter.find_sent_message(
            self.scope(), "t_conversation001", "visitor001", "虛構回覆",
            "2026-09-06T11:59:00+00:00")
        self.assertEqual(readback["message_id"], "reply001")
        adapter.http = FakeHTTP([
            {"messages": {"data": [{"id": "reply001"}, {"id": "reply002"}]}},
            self.detail(message_id="reply001", sender="10001",
                        recipient="visitor001", text="虛構回覆",
                        created="2026-09-06T12:00:00+0000"),
            self.detail(message_id="reply002", sender="10001",
                        recipient="visitor001", text="虛構回覆",
                        created="2026-09-06T12:00:00+0000"),
        ])
        with self.assertRaisesRegex(api.DirectMessageAPIError, "ambiguous_readback"):
            adapter.find_sent_message(
                self.scope(), "t_conversation001", "visitor001", "虛構回覆",
                "2026-09-06T11:59:00+00:00")


if __name__ == "__main__":
    unittest.main()
