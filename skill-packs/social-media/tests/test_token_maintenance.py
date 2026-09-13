"""權杖維護入口的行為測試；不接觸網路或原生憑證庫。"""

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).parents[1] / "skills/social-media-setup/scripts"
sys.path.insert(0, str(SCRIPTS))
from oauth_http import OAuthError
from token_maintenance import maintain


class FakeRuntime:
    instances = []
    initial_state = "ready"
    outcome = "ready"
    revision_after = "old"

    def __init__(self, workspace, platform, connection):
        self.platform = platform
        self.calls = []
        self.__class__.instances.append(self)

    def status(self):
        revision = self.revision_after if self.calls else "old"
        return {"status": self.outcome if self.calls else self.initial_state,
                "revision": revision, "contains_credentials": False}

    def access(self, **kwargs):
        self.calls.append(kwargs)
        if self.outcome != "ready":
            raise OAuthError(self.outcome)
        return "fictional-token-never-output"

    def config(self):
        """既有測試維持直接 Instagram Login，不包含刪文 User Token。"""
        return {"login_route": "instagram_login", "scopes": []}


class TokenMaintenanceTests(unittest.TestCase):
    def setUp(self):
        FakeRuntime.instances = []
        FakeRuntime.initial_state = "ready"
        FakeRuntime.outcome = "ready"
        FakeRuntime.revision_after = "old"

    def test_ready_connection_allows_runtime_to_decide_refresh_window(self):
        result = maintain("workspace", "threads", confirmed_read=True,
                          allow_refresh=True, runtime_factory=FakeRuntime)
        self.assertEqual(result["status"], "ready")
        self.assertFalse(result["refreshed"])
        self.assertEqual(FakeRuntime.instances[0].calls, [{
            "confirmed_read": True, "allow_refresh": True, "resume": False,
            "maintenance": True}])
        self.assertNotIn("fictional-token-never-output", str(result))

    def test_revision_change_reports_refresh_without_secret(self):
        FakeRuntime.revision_after = "new"
        result = maintain("workspace", "instagram", confirmed_read=True,
                          allow_refresh=True, runtime_factory=FakeRuntime)
        self.assertTrue(result["refreshed"])
        self.assertEqual(result["action"], "none")

    def test_read_failure_can_resume_but_unknown_write_cannot(self):
        FakeRuntime.initial_state = "read_failed"
        maintain("workspace", "youtube", confirmed_read=True,
                 allow_refresh=True, runtime_factory=FakeRuntime)
        self.assertTrue(FakeRuntime.instances[0].calls[0]["resume"])
        FakeRuntime.instances = []
        FakeRuntime.initial_state = "remote_result_unknown"
        result = maintain("workspace", "threads", confirmed_read=True,
                          allow_refresh=True, runtime_factory=FakeRuntime)
        self.assertEqual(result["action"], "manual_attention_required")
        self.assertEqual(FakeRuntime.instances[0].calls, [])

    def test_read_and_refresh_require_prior_authorization(self):
        result = maintain("workspace", "facebook", allow_refresh=True,
                          runtime_factory=FakeRuntime)
        self.assertEqual(result["status"], "authorization_required")
        self.assertEqual(FakeRuntime.instances, [])


if __name__ == "__main__":
    unittest.main()
