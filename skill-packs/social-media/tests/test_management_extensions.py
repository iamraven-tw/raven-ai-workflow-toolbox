"""YouTube 修改及 Instagram 刪文專用 User Token 的虛構測試。"""

import copy
import unittest

import test_content_deletion as deletion
import test_instagram_facebook_oauth as ig
import test_publish_execute as flow


class YouTubeUpdateTests(unittest.TestCase):
    setUp = deletion.DeleteAdapterTests.setUp
    configured = deletion.DeleteAdapterTests.configured
    row = deletion.DeleteAdapterTests.row

    def test_snippet_preserved_and_put_is_not_upload(self):
        api, low = deletion.api, deletion.low
        row = self.row("youtube")
        row["items"][0]["snippet"].update(tags=["existing"], defaultLanguage="zh-TW")
        http = low.FakeHTTP(api.HTTPResult(200, row), api.HTTPResult(200, row),
                            api.HTTPResult(200, {"id": "abcDEF_1234"}))
        adapter, grant = self.configured("youtube", http)
        before = adapter.inspect_content("youtube", grant["target_id"], "abcDEF_1234", confirmed_read=True)
        adapter.youtube_update_content(grant, resource_id="abcDEF_1234", before=before, title="新標題", description="新說明")
        method, endpoint, kwargs = http.calls[-1]
        self.assertEqual(method, "PUT")
        self.assertNotIn("upload", endpoint)
        self.assertEqual(kwargs["query"], {"part": "snippet"})
        self.assertEqual(kwargs["json_body"]["snippet"], {"title": "新標題", "description": "新說明",
            "categoryId": "22", "tags": ["existing"], "defaultLanguage": "zh-TW"})
        self.assertNotIn("status", kwargs["json_body"])

    def test_unknown_audio_language_write_support_stops(self):
        api, low = deletion.api, deletion.low
        row = self.row("youtube")
        row["items"][0]["snippet"]["defaultAudioLanguage"] = "zh-TW"
        http = low.FakeHTTP(api.HTTPResult(200, row), api.HTTPResult(200, row))
        adapter, grant = self.configured("youtube", http)
        before = adapter.inspect_content("youtube", grant["target_id"], "abcDEF_1234", confirmed_read=True)
        with self.assertRaisesRegex(api.PublishAPIError, "adapter_unavailable"):
            adapter.youtube_update_content(grant, resource_id="abcDEF_1234", before=before, title="新標題", description="")
        self.assertTrue(all(c[0] == "GET" for c in http.calls))


class YouTubeUpdateFlowTests(unittest.TestCase):
    setUp = flow.PublishExecutionTests.setUp
    write = flow.PublishExecutionTests.write
    begin = flow.PublishExecutionTests.begin
    executor = flow.PublishExecutionTests.executor

    def test_verified_update_without_fabricated_url_or_time(self):
        before = {"id": "abcDEF_1234", "title": "舊片", "body": "舊說明", "version": "etag-before", "url": None,
            "details": {"snippet": {"title": "舊片", "description": "舊說明", "categoryId": "22", "tags": ["保留"]},
                        "privacy_status": "private"}}
        self.item.update(platform="youtube", format="video", target_id="UCfictionalChannel01",
            target_url="https://www.youtube.com/@fictional", action="update_content", title="新片名", body="新說明",
            settings={"resource_id": "abcDEF_1234", "before": before})
        self.write()
        self.begin()
        fake = flow.FakeAdapter()
        fake.youtube_update_content = lambda *a, **kw: {"remote_id": "abcDEF_1234"}
        after = copy.deepcopy(before)
        after.update(title="新片名", body="新說明", version="etag-after")
        after["details"]["snippet"].update(title="新片名", description="新說明")
        fake.management_readback = lambda *a: after
        self.assertEqual(self.executor(fake).execute_api("first")["result"], "updated")


class InstagramUserTokenTests(unittest.TestCase):
    setUp = ig.InstagramFacebookOAuthTests.setUp
    runtime = ig.InstagramFacebookOAuthTests.runtime
    replies = ig.InstagramFacebookOAuthTests.replies
    session = ig.InstagramFacebookOAuthTests.session
    finish = ig.InstagramFacebookOAuthTests.finish
    kind = ig.InstagramFacebookOAuthTests.kind

    def ready_with_delete(self):
        scopes = ig.SCOPES + ["instagram_manage_contents"]
        runtime = self.runtime(ig.config(scopes=scopes))
        replies = self.replies()
        replies[4]["data"].append({"permission": "instagram_manage_contents", "status": "granted"})
        replies[6]["data"]["scopes"].append("instagram_manage_contents")
        self.user_replies = copy.deepcopy(replies[-3:]) + [ig.debug("USER", user_id="789"),
            {"data": [{"permission": s, "status": "granted"} for s in scopes + ["public_profile"]]},
            {"data": [ig.page()]}]
        self.http.replies = replies
        self.assertEqual(self.finish(runtime)["status"], "ready")
        self.http.calls.clear()
        return runtime

    def test_user_is_native_only_and_default_still_returns_page(self):
        runtime = self.ready_with_delete()
        self.assertEqual(runtime._bundle()["facebook_user_access_token"], "fictional-long")
        for path in self.root.rglob("*.json"):
            self.assertNotIn("fictional-long", path.read_text())
        self.http.replies = copy.deepcopy(self.user_replies[:3])
        self.assertEqual(runtime.access(confirmed_read=True), "fictional-page")
        self.http.replies = copy.deepcopy(self.user_replies)
        self.assertEqual(runtime.access_instagram_user(confirmed_read=True), "fictional-long")
        self.assertTrue(all(not c[2].get("mutation") for c in self.http.calls))

    def test_missing_user_does_not_substitute_page_token(self):
        runtime = self.ready_with_delete()
        bundle = runtime._bundle()
        bundle.pop("facebook_user_access_token")
        runtime._save_bundle(bundle)
        runtime.mark("ready")
        self.http.replies = copy.deepcopy(self.user_replies[:3])
        self.kind("reauth_required", lambda: runtime.access_instagram_user(confirmed_read=True))
        self.assertEqual(runtime.status()["status"], "ready")

    def test_wrong_user_or_revoked_page_stops(self):
        for reason in ("user", "page"):
            runtime = self.ready_with_delete()
            self.http.replies = copy.deepcopy(self.user_replies)
            if reason == "user":
                self.http.replies[3]["data"]["user_id"] = "999"
            else:
                self.http.replies[-1] = {"data": []}
            self.kind("target_mismatch", lambda: runtime.access_instagram_user(confirmed_read=True))

    def test_user_expiry_maintenance_warns_without_disabling_page(self):
        runtime = self.ready_with_delete()
        self.http.replies = copy.deepcopy(self.user_replies)
        self.kind("reauth_required", lambda: runtime.access_instagram_user(confirmed_read=True, maintenance=True))
        self.assertEqual(runtime.status()["status"], "ready")


if __name__ == "__main__":
    unittest.main()
