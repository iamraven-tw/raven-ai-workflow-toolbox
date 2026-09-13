"""刪除的交易、身分、讀回與真實傳輸層模擬測試；不連網。"""

import copy
import json
import unittest
from unittest.mock import patch

import test_publish_execute as flow
import test_official_publish_api as low

api = low.api


class DeletionTests(unittest.TestCase):
    setUp = flow.PublishExecutionTests.setUp
    write = flow.PublishExecutionTests.write
    begin = flow.PublishExecutionTests.begin
    executor = flow.PublishExecutionTests.executor

    def setup_delete(self, platform="facebook"):
        """只有虛構擁有者與內容。"""
        target, resource, url, fmt = {
            "facebook": ("10001", "10001_70001", "https://www.facebook.com/10001_70001", "text"),
            "threads": ("30003", "70001", "https://www.threads.com/@fictional/post/example", "text"),
            "youtube": ("UCfictionalChannel01", "abcDEF_1234", None, "video"),
            "instagram": ("20002", "70001", "https://www.instagram.com/p/fictional/", "image"),
        }[platform]
        self.before = {"id": resource, "title": "", "body": "虛構貼文", "version": "old-version",
                       "url": url, "details": {}}
        self.item.update(platform=platform, target_id=target, format=fmt, action="delete_content",
            target_url=url or "https://www.youtube.com/@fictional",
            settings={"resource_id": resource, "before": self.before})
        self.write()
        self.begin()
        self.fake = flow.FakeAdapter()
        self.deletes = []
        def delete(grant, **kwargs):
            self.deletes.append(kwargs)
            return {"remote_id": resource}
        self.fake.delete_content = delete
        self.proof = {"resource_id": resource, "absent": True, "complete": True, "connection_verified": True}
        self.fake.deletion_readback = lambda *args: self.proof

    def test_all_three_platforms_delete_once(self):
        # 每個平台在獨立測試工作區跑同一套交易，不建立第二套帳本。
        for platform in ("facebook", "threads", "youtube", "instagram"):
            with self.subTest(platform=platform):
                if platform != "facebook":
                    self.setUp()
                self.setup_delete(platform)
                runner = self.executor(self.fake)
                self.assertEqual(runner.execute_api("first")["result"], "deleted")
                with self.assertRaises(ValueError):
                    runner.execute_api("first")
                self.assertEqual(len(self.deletes), 1)

    def test_incomplete_list_is_pending_not_deleted(self):
        self.setup_delete()
        self.proof.update(complete=False, absent=False)
        runner = self.executor(self.fake)
        self.assertEqual(runner.execute_api("first")["result"], "pending")
        with self.assertRaises(ValueError):
            runner.execute_api("first")
        self.assertEqual(len(self.deletes), 1)

    def test_unknown_does_not_readback_as_success_or_resend(self):
        self.setup_delete()
        def unknown(grant, **kwargs):
            self.deletes.append(kwargs)
            raise flow.official.PublishAPIError("remote_result_unknown")
        self.fake.delete_content = unknown
        runner = self.executor(self.fake)
        self.assertEqual(runner.execute_api("first")["result"], "unknown")
        with self.assertRaises(ValueError):
            runner.execute_api("first")
        self.assertEqual(len(self.deletes), 1)

    def test_different_caption_cannot_bypass_delete_dedup(self):
        self.setup_delete()
        original = flow.job.fingerprint(self.item)
        self.item["body"] = "不能用改文案再次刪同一項"
        self.item["settings"]["before"]["body"] = self.item["body"]
        self.assertEqual(flow.job.fingerprint(self.item), original)


class DeleteAdapterTests(unittest.TestCase):
    setUp = low.OfficialPublishAPITests.setUp

    def configured(self, platform, http, *, scopes=None):
        """虛構 Runtime 保留實際傳輸前的帳號與 scope 查核。"""
        target, route = self.routes[platform]
        if platform == "instagram":
            route = "instagram_facebook_login"
        permissions = {"facebook": ["pages_manage_posts"], "threads": ["threads_basic", "threads_delete"],
                       "youtube": ["https://www.googleapis.com/auth/youtube.force-ssl"],
                       "instagram": ["instagram_basic", "instagram_manage_contents"]}
        class Runtime:
            def config(self):
                return {"target_id": target, "client_id": "12345", "graph_version": "v99.0",
                        "login_route": route, "scopes": permissions[platform] if scopes is None else scopes}
            def access(self, **kwargs):
                return "fictional-token"
            def access_instagram_user(self, **kwargs):
                return "fictional-user-token"
        return api.OfficialAPIAdapter(self.root, runtime_factory=lambda *a: Runtime(), http_transport=http), low.OfficialPublishAPITests.grant(platform, target)

    def row(self, platform):
        """三種 API 的原生回應，不假裝它們格式相同。"""
        if platform == "facebook":
            return {"id": "10001_70001", "from": {"id": "10001"}, "message": "舊文",
                    "updated_time": "2026-01-01T00:00:00Z", "is_published": True,
                    "permalink_url": "https://www.facebook.com/10001_70001"}
        if platform == "threads":
            return {"data": [{"id": "70001", "text": "舊文", "timestamp": "2026-01-01T00:00:00Z",
                              "permalink": "https://www.threads.com/@fictional/post/one", "media_type": "TEXT"}]}
        if platform == "instagram":
            return {"data": [{"id": "70001", "caption": "舊文", "timestamp": "2026-01-01T00:00:00Z",
                              "permalink": "https://www.instagram.com/p/fictional/", "media_type": "IMAGE"}]}
        return {"items": [{"id": "abcDEF_1234", "etag": "fictional-etag",
                          "snippet": {"channelId": "UCfictionalChannel01", "title": "舊片", "description": "說明", "categoryId": "22"}}]}

    def test_verified_delete_and_empty_readback(self):
        for platform in ("facebook", "threads", "youtube", "instagram"):
            with self.subTest(platform=platform):
                resource = {"facebook": "10001_70001", "threads": "70001", "youtube": "abcDEF_1234", "instagram": "70001"}[platform]
                row = self.row(platform)
                ack = api.HTTPResult(204, {}) if platform == "youtube" else api.HTTPResult(200, {"success": True, "deleted_id": resource})
                empty = {"items": []} if platform == "youtube" else {"data": []}
                http = low.FakeHTTP(api.HTTPResult(200, row), api.HTTPResult(200, row), ack, api.HTTPResult(200, empty))
                adapter, grant = self.configured(platform, http)
                before = adapter.inspect_content(platform, grant["target_id"], resource, confirmed_read=True)
                self.assertEqual(adapter.delete_content(grant, resource_id=resource, before=before)["status"], "deletion_accepted")
                self.assertTrue(adapter.deletion_readback(grant, resource)["absent"])
                self.assertEqual([c[0] for c in http.calls], ["GET", "GET", "DELETE", "GET"])
                if platform == "threads":
                    self.assertIn("graph.threads.com", http.calls[2][1])
                if platform == "instagram":
                    self.assertEqual(http.calls[2][2]["bearer"], "fictional-user-token")
                    self.assertEqual(http.calls[0][2]["bearer"], "fictional-token")

    def test_changed_content_wrong_owner_missing_permission_stop(self):
        for reason in ("changed", "owner", "permission"):
            with self.subTest(reason=reason):
                row = self.row("facebook")
                http = low.FakeHTTP(api.HTTPResult(200, row))
                adapter, grant = self.configured("facebook", http)
                before = adapter.inspect_content("facebook", "10001", "10001_70001", confirmed_read=True)
                changed = copy.deepcopy(row)
                if reason == "changed":
                    changed["message"] = "另一版"
                if reason == "owner":
                    changed["from"]["id"] = "99999"
                http.responses.append(api.HTTPResult(200, changed))
                if reason == "permission":
                    adapter, grant = self.configured("facebook", http, scopes=[])
                with self.assertRaises(api.PublishAPIError):
                    adapter.delete_content(grant, resource_id="10001_70001", before=before)
                self.assertNotIn("DELETE", [c[0] for c in http.calls])

    def test_pagination_limit_is_not_absence(self):
        http = low.FakeHTTP(*[api.HTTPResult(200, {"data": [], "paging": {
            "next": "https://untrusted.invalid/do-not-follow", "cursors": {"after": f"page{i}"}}}) for i in range(5)])
        adapter, grant = self.configured("facebook", http)
        proof = adapter.deletion_readback(grant, "10001_70001")
        self.assertFalse(proof["absent"])
        self.assertFalse(proof["complete"])
        self.assertTrue(all("graph.facebook.com" in call[1] for call in http.calls))

    def test_transport_allows_exact_writes_and_rejects_others(self):
        """跑真實 request_json 的方法與端點驗證；只替換 HTTPS socket。"""
        for method, url, status, body in (
            ("POST", "https://graph.facebook.com/v99.0/10001_70001", 200, b'{"success":true}'),
            ("DELETE", "https://graph.facebook.com/v99.0/10001_70001", 200, b'{"success":true}'),
            ("DELETE", "https://graph.threads.com/v99.0/70001", 200, b'{"success":true,"deleted_id":"70001"}'),
            ("DELETE", "https://www.googleapis.com/youtube/v3/videos", 204, b''),
        ):
            with self.subTest(method=method, url=url), patch.object(api.http.client, "HTTPSConnection") as factory:
                response = factory.return_value.getresponse.return_value
                response.status = status
                response.read.return_value = body
                response.getheaders.return_value = []
                result = api.OfficialPublishHTTP().request_json(method, url, bearer="fictional", mutation=True, allow_empty=True)
                self.assertEqual(result.status, status)
                self.assertEqual(factory.return_value.request.call_count, 1)
        for method, url in (("DELETE", "https://graph.facebook.com/v99.0/me"),
                            ("DELETE", "https://graph.threads.net/v99.0/me/threads"),
                            ("PUT", "https://graph.facebook.com/v99.0/10001_70001")):
            self.assertFalse(api.OfficialPublishHTTP._allowed(method, url))


if __name__ == "__main__":
    unittest.main()
