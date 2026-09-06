#!/usr/bin/env python3
"""官方留言 adapter 的虛構傳輸測試；不連線、不取用秘密庫。"""

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/social-community-management/scripts/official_community_api.py"
SPEC = importlib.util.spec_from_file_location("official_community_api", SCRIPT)
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)


class FakeRuntime:
    """回傳虛構 Token 並記錄 Runtime 是否先核對設定。"""

    def __init__(self, platform, target_id, route, calls):
        self.platform = platform
        self.target_id = target_id
        self.route = route
        self.calls = calls

    def config(self):
        self.calls.append(("config", self.platform))
        return {"platform": self.platform, "target_id": self.target_id,
                "login_route": self.route, "graph_version": "v99.0"}

    def access(self, *, confirmed_read=False, allow_refresh=False):
        self.calls.append(("access", self.platform, confirmed_read, allow_refresh))
        return "fictional-community-token"


class FakeHTTP:
    """依序回傳虛構官方回應，不觸碰網路。"""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def request_json(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint, kwargs))
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)


def ok(payload):
    """建立虛構 HTTP 200。"""

    return api.HTTPResult(200, payload)


class OfficialCommunityAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-community-api-")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name).resolve()
        self.runtime_calls = []
        self.routes = {
            "youtube": ("UCfictional01", "youtube_desktop"),
            "facebook": ("10001", "facebook_pages"),
            "instagram": ("20002", "instagram_login"),
            "threads": ("30003", "threads_login"),
        }

    def runtime(self, workspace, platform, connection):
        self.assertEqual(Path(workspace), self.workspace)
        self.assertEqual(connection, "main")
        target, route = self.routes[platform]
        return FakeRuntime(platform, target, route, self.runtime_calls)

    def adapter(self, *responses):
        transport = FakeHTTP(*responses)
        return api.OfficialCommunityAdapter(
            self.workspace, runtime_factory=self.runtime, http_transport=transport), transport

    @staticmethod
    def scope(platform, account_id, post_id, urls=None):
        return {"platform": platform, "account_id": account_id, "post_id": post_id,
                "approval_ref": "fictional-read-approval", "confirmed_read": True,
                "allow_token_refresh": False, "url_observations": urls or {}}

    @staticmethod
    def grant(platform, account_id, post_id, comment_id, text, stage):
        return {"platform": platform, "account_id": account_id, "post_id": post_id,
                "comment_id": comment_id, "reply_target_id": comment_id, "text": text,
                "approval_ref": "fictional-reply-approval", "transaction_status": "in_flight",
                "stage": stage, "allow_token_refresh": False}

    def test_invalid_scope_stops_before_runtime(self):
        adapter, transport = self.adapter()
        scope = self.scope("facebook", "10001", "10001_90001")
        scope["confirmed_read"] = False
        with self.assertRaisesRegex(api.CommunityAPIError, "authorization_required"):
            adapter.verify_access(scope)
        self.assertEqual(self.runtime_calls, [])
        self.assertEqual(transport.calls, [])

    def test_http_allowlist_rejects_arbitrary_hosts_and_token_query(self):
        http = api.OfficialCommunityHTTP()
        self.assertFalse(http._allowed("GET", "https://evil.example/100/comments"))
        self.assertTrue(http._allowed(
            "GET", "https://graph.threads.net/v99.0/30003/replies"))
        with self.assertRaisesRegex(api.CommunityAPIError, "invalid_request"):
            http.request_json(
                "GET", "https://graph.facebook.com/v99.0/10001_90001/comments",
                query={"access_token": "must-not-be-query"}, bearer="fictional")

    def test_youtube_fetch_preserves_id_author_time_and_observed_url(self):
        adapter, transport = self.adapter(
            ok({"items": [{"id": "videoABC123", "snippet": {
                "channelId": "UCfictional01", "title": "虛構影片", "description": "內容"}}]}),
            ok({"items": [{"snippet": {"topLevelComment": {
                "id": "commentABC123", "snippet": {
                    "authorChannelId": {"value": "UCvisitor01"},
                    "authorDisplayName": "虛構訪客", "textOriginal": "虛構留言",
                    "publishedAt": "2026-09-06T01:00:00Z"}}}}]}),
        )
        scope = self.scope(
            "youtube", "UCfictional01", "videoABC123",
            {"commentABC123": "https://www.youtube.com/watch?v=videoABC123&lc=commentABC123"})
        result = adapter.fetch_comments(scope)
        record = result["records"][0]
        self.assertTrue(result["complete"])
        self.assertEqual(record["visitor_id"], "UCvisitor01")
        self.assertEqual(record["comment_created_at"], "2026-09-06T01:00:00Z")
        self.assertIn("lc=commentABC123", record["comment_url"])
        self.assertTrue(transport.calls[1][1].endswith("/commentThreads"))

    def test_youtube_reply_uses_comments_not_comment_threads(self):
        adapter, transport = self.adapter(
            ok({"id": "replyABC123", "snippet": {}}),
            ok({"items": [{"id": "replyABC123", "snippet": {
                "parentId": "commentABC123", "textOriginal": "最終文字",
                "publishedAt": "2026-09-06T01:01:00Z",
                "authorChannelId": {"value": "UCfictional01"},
                "authorDisplayName": "頻道"}}]}),
        )
        grant = self.grant("youtube", "UCfictional01", "videoABC123",
                           "commentABC123", "最終文字", "reply_create")
        reply = adapter.create_reply(grant)
        readback = adapter.read_reply(
            self.scope("youtube", "UCfictional01", "videoABC123"),
            "commentABC123", reply["reply_id"])
        self.assertEqual(reply["reply_id"], "replyABC123")
        self.assertIsNone(readback["url"])
        self.assertEqual(transport.calls[0][1], "https://www.googleapis.com/youtube/v3/comments")
        self.assertEqual(transport.calls[0][2]["json_body"]["snippet"]["parentId"],
                         "commentABC123")

    def test_facebook_fetch_own_reply_create_and_readback(self):
        adapter, transport = self.adapter(
            ok({"id": "10001_90001", "message": "粉專貼文", "from": {"id": "10001"}}),
            ok({"data": [{"id": "70001", "message": "訪客留言",
                           "from": {"id": "60001", "name": "訪客"},
                           "created_time": "2026-09-06T01:00:00+0000",
                           "permalink_url": "https://www.facebook.com/10001/posts/90001?comment_id=70001"}]}),
            ok({"data": []}),
            ok({"id": "70002"}),
            ok({"id": "70002", "message": "最終文字",
                "from": {"id": "10001", "name": "粉專"},
                "created_time": "2026-09-06T01:01:00+0000",
                "permalink_url": "https://www.facebook.com/10001/posts/90001?comment_id=70002",
                "parent": {"id": "70001"}}),
        )
        scope = self.scope("facebook", "10001", "10001_90001")
        record = adapter.fetch_comments(scope)["records"][0]
        self.assertEqual(record["comment_id"], "70001")
        self.assertTrue(adapter.own_replies(scope, "70001")["none_found_complete"])
        reply = adapter.create_reply(
            self.grant("facebook", "10001", "10001_90001", "70001",
                       "最終文字", "reply_create"))
        readback = adapter.read_reply(scope, "70001", reply["reply_id"])
        self.assertTrue(readback["author_owned"])
        self.assertIn("comment_id=70002", readback["url"])
        self.assertEqual(transport.calls[3][2]["form"], {"message": "最終文字"})

    def test_instagram_ids_and_time_are_api_fields_but_permalink_is_not(self):
        adapter, _ = self.adapter(
            ok({"id": "91001", "caption": "IG 貼文", "owner": {"id": "20002"}}),
            ok({"data": [{"id": "92001", "text": "IG 留言",
                           "from": {"id": "93001", "username": "visitor"},
                           "username": "visitor", "timestamp": "2026-09-06T01:00:00+0000"}]}),
        )
        result = adapter.fetch_comments(self.scope("instagram", "20002", "91001"))
        self.assertEqual(result["records"], [])
        self.assertEqual(result["missing_url_records"][0]["comment_id"], "92001")
        self.assertEqual(result["missing_url_records"][0]["comment_created_at"],
                         "2026-09-06T01:00:00+0000")

    def test_instagram_facebook_login_uses_graph_facebook_and_browser_url(self):
        self.routes["instagram"] = ("20002", "instagram_facebook_login")
        adapter, transport = self.adapter(
            ok({"id": "91001", "caption": "IG 貼文", "owner": {"id": "20002"}}),
            ok({"data": [{"id": "92001", "text": "IG 留言",
                           "from": {"id": "93001", "username": "visitor"},
                           "username": "visitor", "timestamp": "2026-09-06T01:00:00+0000"}]}),
        )
        scope = self.scope(
            "instagram", "20002", "91001",
            {"92001": "https://www.instagram.com/p/fictional/c/92001"})
        record = adapter.fetch_comments(scope)["records"][0]
        self.assertIn("/c/92001", record["comment_url"])
        self.assertTrue(all("graph.facebook.com" in call[1] for call in transport.calls))

    def test_threads_replies_have_complete_relation_permalink_and_owner_flag(self):
        adapter, transport = self.adapter(
            ok({"data": [{"id": "80001", "text": "自有貼文",
                           "permalink": "https://www.threads.com/@owner/post/root",
                           "owner": {"id": "30003"}, "username": "owner",
                           "timestamp": "2026-09-06T00:00:00+0000"}]}),
            ok({"data": [{"id": "81001", "text": "訪客回覆",
                           "timestamp": "2026-09-06T01:00:00+0000",
                           "permalink": "https://www.threads.com/@visitor/post/reply",
                           "username": "visitor", "is_reply": True,
                           "is_reply_owned_by_me": False,
                           "root_post": {"id": "80001"},
                           "replied_to": {"id": "80001"}}]}),
            ok({"data": []}),
        )
        scope = self.scope("threads", "30003", "80001")
        record = adapter.fetch_comments(scope)["records"][0]
        own = adapter.own_replies(scope, "81001")
        self.assertEqual(record["visitor_id"], "visitor")
        self.assertIn("/post/reply", record["comment_url"])
        self.assertTrue(own["none_found_complete"])
        self.assertTrue(transport.calls[1][1].endswith("/80001/replies"))

    def test_threads_two_stage_reply_and_parent_readback(self):
        adapter, transport = self.adapter(
            ok({"id": "82001"}),
            ok({"id": "82001", "status": "FINISHED"}),
            ok({"id": "83001"}),
            ok({"data": [{"id": "83001", "text": "最終文字",
                           "timestamp": "2026-09-06T01:01:00+0000",
                           "permalink": "https://www.threads.com/@owner/post/answer",
                           "username": "owner", "is_reply": True,
                           "is_reply_owned_by_me": True,
                           "root_post": {"id": "80001"},
                           "replied_to": {"id": "81001"}}]}),
        )
        scope = self.scope("threads", "30003", "80001")
        container = adapter.create_threads_container(
            self.grant("threads", "30003", "80001", "81001",
                       "最終文字", "reply_container"))
        self.assertEqual(adapter.threads_container_status(
            scope, container["container_id"])["status"], "FINISHED")
        reply = adapter.publish_threads_reply(
            self.grant("threads", "30003", "80001", "81001",
                       "最終文字", "reply_publish"), container["container_id"])
        readback = adapter.read_reply(scope, "81001", reply["reply_id"])
        self.assertEqual(readback["reply_target_id"], "81001")
        self.assertTrue(readback["author_owned"])
        self.assertEqual(sum(call[0] == "POST" for call in transport.calls), 2)

    def test_pagination_cursor_is_rebuilt_without_following_next_url(self):
        adapter, transport = self.adapter(
            ok({"data": [], "paging": {"cursors": {"after": "safe-cursor"}}}),
            ok({"data": []}),
        )
        items, complete = adapter._page(
            "https://graph.threads.net/v99.0/80001/replies",
            {"fields": adapter.REPLY_FIELDS, "limit": 100},
            "fictional-community-token")
        self.assertEqual(items, [])
        self.assertTrue(complete)
        self.assertEqual(transport.calls[1][2]["query"]["after"], "safe-cursor")


if __name__ == "__main__":
    unittest.main()
