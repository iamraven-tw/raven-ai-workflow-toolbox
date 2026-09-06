#!/usr/bin/env python3
"""官方發布 adapter 的虛構傳輸測試；不連線、不讀憑證庫。"""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/social-content-publishing/scripts/official_publish_api.py"
SPEC = importlib.util.spec_from_file_location("official_publish_api", SCRIPT)
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)


class FakeRuntime:
    """只回傳虛構 Token；記錄是否先經 Runtime.access。"""

    def __init__(self, platform, target_id, route, calls):
        self.platform = platform
        self.target_id = target_id
        self.route = route
        self.calls = calls

    def config(self):
        self.calls.append(("config", self.platform))
        return {"platform": self.platform, "target_id": self.target_id,
                "graph_version": "v99.0", "login_route": self.route}

    def access(self, *, confirmed_read=False, allow_refresh=False):
        self.calls.append(("access", self.platform, confirmed_read, allow_refresh))
        return "fictional-token-never-print"


class FakeHTTP:
    """逐次回傳預先放入的官方假回應。"""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.uploads = []

    def request_json(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint, kwargs))
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)

    def upload_file(self, endpoint, path, **kwargs):
        self.uploads.append((endpoint, path, kwargs))
        if not self.responses:
            raise AssertionError("unexpected upload")
        return self.responses.pop(0)


class OfficialPublishAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-official-publish-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.video = self.root / "fictional-video.mp4"
        self.video.write_bytes(b"fictional-video-bytes")
        self.runtime_calls = []
        self.routes = {
            "youtube": ("UCfictionalChannel01", "youtube_desktop"),
            "facebook": ("10001", "facebook_pages"),
            "instagram": ("20002", "instagram_login"),
            "threads": ("30003", "threads_login"),
        }

    def runtime(self, workspace, platform, connection):
        self.assertEqual(Path(workspace), self.root)
        self.assertEqual(connection, "main")
        target, route = self.routes[platform]
        return FakeRuntime(platform, target, route, self.runtime_calls)

    @staticmethod
    def grant(platform, target):
        return {
            "item_id": "fictional-item",
            "preview_sha256": "a" * 64,
            "approval_ref": "fictional-user-publish-confirmation",
            "platform": platform,
            "target_id": target,
            "transaction_status": "in_progress",
            "allow_token_refresh": False,
        }

    @staticmethod
    def youtube_metadata():
        return {
            "snippet": {"title": "虛構影片", "description": "只供測試",
                        "categoryId": "22", "tags": ["虛構"]},
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False,
                       "containsSyntheticMedia": True},
        }

    def test_invalid_grant_stops_before_credential_access(self):
        transport = FakeHTTP()
        adapter = api.OfficialAPIAdapter(self.root, runtime_factory=self.runtime,
                                         http_transport=transport)
        grant = self.grant("facebook", "10001")
        grant["transaction_status"] = "previewed"
        with self.assertRaisesRegex(api.PublishAPIError, "authorization_required"):
            adapter.facebook_create_feed(grant, message="不應發布")
        self.assertEqual(self.runtime_calls, [])
        self.assertEqual(transport.calls, [])

    def test_youtube_resumable_session_upload_and_readback(self):
        session_url = ("https://www.googleapis.com/upload/youtube/v3/videos?"
                       "uploadType=resumable&upload_id=fictional-session")
        transport = FakeHTTP(
            api.HTTPResult(200, {}, {"Location": session_url}),
            api.HTTPResult(201, {"id": "abcDEF_1234"}),
            api.HTTPResult(200, {"items": [{"id": "abcDEF_1234",
                "snippet": {"channelId": "UCfictionalChannel01", "title": "虛構影片"},
                "status": {"privacyStatus": "private"},
                "processingDetails": {"processingStatus": "processing"}}]}),
        )
        adapter = api.OfficialAPIAdapter(self.root, runtime_factory=self.runtime,
                                         http_transport=transport)
        grant = self.grant("youtube", "UCfictionalChannel01")
        session = adapter.youtube_start_upload(
            grant, asset_path=self.video.name, metadata=self.youtube_metadata(),
            notify_subscribers=False,
        )
        self.assertEqual(repr(session), "SensitiveUploadSession(<redacted>)")
        self.assertNotIn("fictional-session", repr(session))
        uploaded = adapter.youtube_upload(grant, session, asset_path=self.video.name)
        self.assertEqual(uploaded["remote_id"], "abcDEF_1234")
        readback = adapter.youtube_readback(grant, "abcDEF_1234")
        self.assertEqual(readback["snippet"]["channelId"], "UCfictionalChannel01")
        self.assertEqual(len(transport.uploads), 1)
        self.assertNotIn("fictional-token-never-print", json.dumps(uploaded))
        start_kwargs = transport.calls[0][2]
        self.assertEqual(start_kwargs["query"]["uploadType"], "resumable")
        self.assertFalse(start_kwargs["query"]["notifySubscribers"])

    def test_youtube_changed_file_and_308_do_not_restart_session(self):
        session_url = ("https://www.googleapis.com/upload/youtube/v3/videos?"
                       "uploadType=resumable&upload_id=fictional-session")
        transport = FakeHTTP(api.HTTPResult(200, {}, {"location": session_url}))
        adapter = api.OfficialAPIAdapter(self.root, runtime_factory=self.runtime,
                                         http_transport=transport)
        grant = self.grant("youtube", "UCfictionalChannel01")
        session = adapter.youtube_start_upload(
            grant, asset_path=self.video.name, metadata=self.youtube_metadata(),
            notify_subscribers=True,
        )
        self.video.write_bytes(b"changed")
        with self.assertRaisesRegex(api.PublishAPIError, "asset_changed"):
            adapter.youtube_upload(grant, session, asset_path=self.video.name)
        self.assertEqual(transport.uploads, [])

        self.video.write_bytes(b"fictional-video-bytes")
        transport.responses.append(api.HTTPResult(308, {}, {"Range": "bytes=0-9"}))
        pending = adapter.youtube_upload(grant, session, asset_path=self.video.name)
        self.assertEqual(pending["status"], "pending")
        self.assertEqual(len(transport.uploads), 1)

    def test_facebook_feed_photo_carousel_and_readback(self):
        transport = FakeHTTP(
            api.HTTPResult(200, {"id": "10001_90001"}),
            api.HTTPResult(200, {"id": "70001"}),
            api.HTTPResult(200, {"id": "10001_90002"}),
            api.HTTPResult(200, {"id": "10001_90002", "message": "虛構輪播",
                "permalink_url": "https://www.facebook.com/10001/posts/90002",
                "created_time": "2026-09-06T01:00:00+0000", "is_published": True,
                "attachments": {"data": []}}),
        )
        adapter = api.OfficialAPIAdapter(self.root, runtime_factory=self.runtime,
                                         http_transport=transport)
        grant = self.grant("facebook", "10001")
        post = adapter.facebook_create_feed(grant, message="虛構文字")
        photo = adapter.facebook_upload_photo(
            grant, source_url="https://media.example.invalid/card.jpg",
            alt_text="虛構圖卡", published=False,
        )
        carousel = adapter.facebook_create_feed(
            grant, message="虛構輪播", attached_media=[photo["remote_id"]],
        )
        readback = adapter.facebook_readback(grant, carousel["remote_id"])
        self.assertEqual(post["remote_id"], "10001_90001")
        self.assertEqual(readback["id"], "10001_90002")
        self.assertEqual(transport.calls[1][2]["form"]["published"], False)
        self.assertEqual(transport.calls[2][2]["form"]["attached_media"],
                         [{"media_fbid": "70001"}])

    def test_instagram_uses_login_route_host_and_separates_container_media(self):
        for route, host in (("instagram_login", "graph.instagram.com"),
                            ("instagram_facebook_login", "graph.facebook.com")):
            with self.subTest(route=route):
                self.routes["instagram"] = ("20002", route)
                transport = FakeHTTP(
                    api.HTTPResult(200, {"id": "81001"}),
                    api.HTTPResult(200, {"id": "81001", "status_code": "FINISHED",
                                         "status": "Finished"}),
                    api.HTTPResult(200, {"id": "82002"}),
                    api.HTTPResult(200, {"id": "82002", "caption": "虛構 IG",
                        "media_type": "IMAGE", "media_product_type": "FEED",
                        "permalink": "https://www.instagram.com/p/fictional/",
                        "timestamp": "2026-09-06T01:00:00+0000"}),
                )
                adapter = api.OfficialAPIAdapter(self.root, runtime_factory=self.runtime,
                                                 http_transport=transport)
                grant = self.grant("instagram", "20002")
                container = adapter.instagram_create_media(grant, {
                    "image_url": "https://media.example.invalid/ig.jpg",
                    "caption": "虛構 IG", "alt_text": "虛構圖片",
                })
                self.assertEqual(adapter.instagram_container_status(
                    grant, container["remote_id"])["status_code"], "FINISHED")
                media = adapter.instagram_publish(grant, container["remote_id"])
                readback = adapter.instagram_readback(grant, media["remote_id"])
                self.assertEqual(container["remote_id"], "81001")
                self.assertEqual(readback["id"], "82002")
                self.assertTrue(all(host in call[1] for call in transport.calls))

    def test_threads_two_stage_publish_and_readback(self):
        transport = FakeHTTP(
            api.HTTPResult(200, {"id": "91001"}),
            api.HTTPResult(200, {"id": "91001", "status": "FINISHED"}),
            api.HTTPResult(200, {"id": "92002"}),
            api.HTTPResult(200, {"data": [{"id": "92002", "text": "虛構 Threads",
                "permalink": "https://www.threads.com/@fictional/post/example",
                "timestamp": "2026-09-06T01:00:00+0000", "media_type": "TEXT",
                "username": "fictional"}]}),
        )
        adapter = api.OfficialAPIAdapter(self.root, runtime_factory=self.runtime,
                                         http_transport=transport)
        grant = self.grant("threads", "30003")
        container = adapter.threads_create_container(
            grant, {"media_type": "TEXT", "text": "虛構 Threads",
                    "reply_control": "everyone"},
        )
        status = adapter.threads_container_status(grant, container["remote_id"])
        thread = adapter.threads_publish(grant, container["remote_id"])
        readback = adapter.threads_readback(grant, thread["remote_id"])
        self.assertEqual(status["status"], "FINISHED")
        self.assertEqual(readback["id"], "92002")
        self.assertEqual(sum(1 for call in transport.calls if call[0] == "POST"), 2)
        self.assertTrue(transport.calls[-1][1].endswith("/me/threads"))

    def test_facebook_and_threads_readback_reject_wrong_owner_or_missing_item(self):
        facebook_http = FakeHTTP(api.HTTPResult(200, {
            "id": "99999_70001", "message": "其他專頁", "is_published": True,
        }))
        facebook = api.OfficialAPIAdapter(self.root, runtime_factory=self.runtime,
                                          http_transport=facebook_http)
        with self.assertRaisesRegex(api.PublishAPIError, "target_mismatch"):
            facebook.facebook_readback(self.grant("facebook", "10001"), "99999_70001")

        threads_http = FakeHTTP(
            api.HTTPResult(200, {"data": [], "paging": {"cursors": {"after": "next-page"}}}),
            api.HTTPResult(200, {"data": []}),
        )
        threads = api.OfficialAPIAdapter(self.root, runtime_factory=self.runtime,
                                         http_transport=threads_http)
        with self.assertRaisesRegex(api.PublishAPIError, "read_failed"):
            threads.threads_readback(self.grant("threads", "30003"), "92002")
        self.assertEqual(len(threads_http.calls), 2)
        self.assertEqual(threads_http.calls[1][2]["query"]["after"], "next-page")

    def test_threads_rejects_auto_publish_and_reply_mutation(self):
        transport = FakeHTTP()
        adapter = api.OfficialAPIAdapter(self.root, runtime_factory=self.runtime,
                                         http_transport=transport)
        grant = self.grant("threads", "30003")
        for key in ("auto_publish_text", "reply_to_id"):
            with self.subTest(key=key), self.assertRaisesRegex(api.PublishAPIError, "invalid_request"):
                adapter.threads_create_container(
                    grant, {"media_type": "TEXT", "text": "不應送出", key: "fictional"},
                )
        self.assertEqual(transport.calls, [])

    def test_transport_host_allowlist_and_error_redaction(self):
        transport = api.OfficialPublishHTTP()
        with self.assertRaisesRegex(api.PublishAPIError, "invalid_request") as caught:
            transport.request_json(
                "POST", "https://attacker.example.invalid/v99.0/10001/feed",
                form={"message": "不應送出"}, bearer="secret-token", mutation=True,
            )
        self.assertNotIn("secret-token", str(caught.exception))
        with self.assertRaisesRegex(api.PublishAPIError, "remote_result_unknown"):
            api._classify(503, {"error": {"message": "secret-token"}}, mutation=True)
        with self.assertRaisesRegex(api.PublishAPIError, "remote_result_unknown"):
            api._classify(302, {}, mutation=True)
        self.assertTrue(transport._allowed(
            "POST", "https://www.googleapis.com/upload/youtube/v3/videos"))
        self.assertTrue(transport._allowed(
            "POST", "https://graph.facebook.com/v99.0/10001/feed"))
        self.assertTrue(transport._allowed(
            "POST", "https://graph.instagram.com/v99.0/20002/media_publish"))
        self.assertTrue(transport._allowed(
            "POST", "https://graph.threads.net/v99.0/me/threads_publish"))
        self.assertFalse(transport._allowed(
            "POST", "https://graph.facebook.com/v99.0/10001"))
        self.assertFalse(transport._allowed(
            "GET", "https://graph.instagram.com/v99.0/20002/media_publish"))
        with self.assertRaisesRegex(api.PublishAPIError, "invalid_request"):
            transport.request_json(
                "POST", "https://graph.facebook.com/v99.0/10001/feed",
                query={"access_token": "secret-token"}, form={"message": "不應送出"},
                bearer="secret-token", mutation=True,
            )

    def test_execution_sources_choose_api_or_controlled_browser_without_fake_substack_api(self):
        source = ROOT / "skills/social-content-publishing/references/execution-sources.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(set(data["platforms"]),
                         {"youtube", "facebook", "instagram", "threads", "substack"})
        for platform in ("youtube", "facebook", "instagram", "threads"):
            self.assertEqual(data["platforms"][platform]["primary_interface"], "official_api")
            self.assertEqual(data["platforms"][platform]["primary_source"],
                             "scripts/official_publish_api.py")
        self.assertEqual(data["platforms"]["substack"]["primary_interface"],
                         "controlled_browser")
        self.assertNotIn("official_api", data["platforms"]["substack"]["primary_source"])
        self.assertEqual(data["live_status"], "not_performed")


if __name__ == "__main__":
    unittest.main()
