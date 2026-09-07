"""虛構內容取樣測試：不連線、不使用原生秘密。"""
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/social-media-setup/scripts"))
import youtube_content as api


class ContentTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Mock()
        self.runtime.config.return_value = {
            "target_id": "fictional-channel", "login_route": "youtube_desktop",
            "scopes": ["https://www.googleapis.com/auth/youtube.readonly"]}
        self.runtime.access.return_value = "fictional-token"
        self.runtime.resource_context.return_value = {
            "target_id": "fictional-channel", "login_route": "youtube_desktop"}
        self.factory = Mock(return_value=self.runtime)
        self.http = Mock()
        self.channel = {"items": [{"id": "fictional-channel", "contentDetails": {
            "relatedPlaylists": {"uploads": "fictional-uploads"}}}]}

    def call(self, **kwargs):
        return api.sample("fictional-workspace", "fictional-channel",
                          runtime_factory=self.factory, transport=self.http, **kwargs)

    def test_requires_read_authorization(self):
        with self.assertRaisesRegex(api.OAuthError, "authorization_required"):
            self.call()
        self.factory.assert_not_called()

    def test_shared_connection_empty_is_not_failure(self):
        self.http.get.side_effect = [self.channel, {"items": []}]
        result = self.call(confirmed_read=True, allow_refresh=True)
        self.assertEqual(result["status"], "empty")
        self.factory.assert_called_once_with("fictional-workspace", "youtube", connection="main")
        self.runtime.access.assert_called_once_with(confirmed_read=True, allow_refresh=True)

    def test_sample_preserves_limits_and_private_content(self):
        self.http.get.side_effect = [self.channel, {"nextPageToken": "next", "items": [{
            "snippet": {"channelId": "fictional-channel", "title": "虛構影片"},
            "contentDetails": {"videoId": "fictional-video"}}]}]
        result = self.call(confirmed_read=True)
        self.assertTrue(result["has_more"])
        self.assertTrue(result["sample_only"])
        self.assertIsNone(result["videos"][0]["published_at"])
        self.assertNotIn("fictional-token", str(result))
        self.assertEqual(self.http.get.call_args.args[1]["maxResults"], 5)

    def test_wrong_target_stops_before_token(self):
        self.runtime.config.return_value["target_id"] = "other"
        with self.assertRaisesRegex(api.OAuthError, "target_mismatch"):
            self.call(confirmed_read=True)
        self.runtime.access.assert_not_called()

    def test_missing_scope_stops_before_token(self):
        self.runtime.config.return_value["scopes"] = []
        with self.assertRaisesRegex(api.OAuthError, "permission_mismatch"):
            self.call(confirmed_read=True)
        self.runtime.access.assert_not_called()

    def test_response_target_mismatch(self):
        self.http.get.return_value = {"items": [{"id": "other"}]}
        with self.assertRaisesRegex(api.OAuthError, "target_mismatch"):
            self.call(confirmed_read=True)
        self.assertEqual(self.http.get.call_count, 1)

    def test_transport_blocks_other_resources(self):
        with self.assertRaisesRegex(api.OAuthError, "invalid_configuration"):
            api.ContentHTTP().get("videos", {}, "fictional-token")


if __name__ == "__main__":
    unittest.main()
