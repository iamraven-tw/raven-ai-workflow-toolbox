"""專頁修改的虛構測試；不碰真實帳號、Token 或貼文。"""

import unittest
import test_publish_execute as flow
import test_official_publish_api as adapter_tests


class UpdateFlowTests(unittest.TestCase):
    setUp = flow.PublishExecutionTests.setUp
    write = flow.PublishExecutionTests.write
    begin = flow.PublishExecutionTests.begin
    executor = flow.PublishExecutionTests.executor

    def configure_update(self):
        """舊文及時間都屬於確認預覽。"""
        self.item.update(action="update_content", settings={"post_id": "10001_70001",
            "before_message": "舊文", "before_updated_time": "2026-01-01T00:00:00+00:00"})
        self.write()

    def test_update_readback_and_no_resend(self):
        self.configure_update()
        self.begin()
        fake = flow.FakeAdapter()
        writes = []
        def update(grant, **kwargs):
            writes.append(kwargs)
            return {"remote_id": "10001_70001"}
        def readback(grant, post_id, **kwargs):
            return {"id": post_id, "message": self.item["body"],
                "updated_time": "2026-01-02T00:00:00+00:00",
                "permalink_url": "https://www.facebook.com/10001_70001"}
        fake.facebook_update_message = update
        fake.facebook_readback = readback
        runner = self.executor(fake)
        self.assertEqual(runner.execute_api("first")["result"], "updated")
        with self.assertRaises(ValueError):
            runner.execute_api("first")
        self.assertEqual(len(writes), 1)

    def test_unknown_update_blocks_second_write(self):
        self.configure_update()
        self.begin()
        fake = flow.FakeAdapter()
        writes = []
        def update(grant, **kwargs):
            writes.append(kwargs)
            raise flow.official.PublishAPIError("remote_result_unknown")
        fake.facebook_update_message = update
        runner = self.executor(fake)
        self.assertEqual(runner.execute_api("first")["result"], "unknown")
        with self.assertRaises(ValueError):
            runner.execute_api("first")
        self.assertEqual(len(writes), 1)

    def test_wrong_post_and_modified_preview_rejected(self):
        self.configure_update()
        self.item["settings"]["post_id"] = "99999_70001"
        self.write()
        with self.assertRaisesRegex(ValueError, "post_target_invalid"):
            self.begin()
        self.configure_update()
        self.begin()
        self.item["body"] = "未核准的新版本"
        self.write()
        with self.assertRaisesRegex(ValueError, "preview_changed"):
            self.executor(flow.FakeAdapter()).execute_api("first")


class UpdateAdapterTests(unittest.TestCase):
    setUp = adapter_tests.OfficialPublishAPITests.setUp

    def test_before_state_app_and_permission_checks(self):
        api = adapter_tests.api
        grant = adapter_tests.OfficialPublishAPITests.grant("facebook", "10001")
        for mismatch in (None, "app", "message", "time", "permission"):
            with self.subTest(mismatch=mismatch):
                before = {"id": "10001_70001", "message": "舊文", "updated_time": "old-time",
                          "application": {"id": "12345"}}
                if mismatch == "app":
                    before["application"]["id"] = "99999"
                if mismatch == "message":
                    before["message"] = "別人已改過"
                if mismatch == "time":
                    before["updated_time"] = "new-time"
                class Runtime:
                    def config(self):
                        return {"target_id": "10001", "client_id": "12345", "graph_version": "v99.0",
                                "scopes": [] if mismatch == "permission" else ["pages_manage_posts"]}
                    def access(self, **kwargs):
                        return "fictional-test-token"
                http = adapter_tests.FakeHTTP(api.HTTPResult(200, before), api.HTTPResult(200, {"success": True}))
                adapter = api.OfficialAPIAdapter(self.root, runtime_factory=lambda *a: Runtime(), http_transport=http)
                def invoke():
                    return adapter.facebook_update_message(grant, post_id="10001_70001", message="新文",
                        before_message="舊文", before_updated_time="old-time")
                if mismatch:
                    with self.assertRaises(api.PublishAPIError):
                        invoke()
                    self.assertFalse(any(call[0] == "POST" for call in http.calls))
                else:
                    self.assertEqual(invoke()["remote_id"], "10001_70001")
                    self.assertEqual([call[0] for call in http.calls], ["GET", "POST"])


if __name__ == "__main__":
    unittest.main()
