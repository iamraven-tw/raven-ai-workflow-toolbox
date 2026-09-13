"""Facebook 權杖匯入只用虛構 HTTP 與記憶體原生庫，不動真實帳號。"""

import copy
import unittest
from unittest import mock
import test_oauth_runtime as oauth_tests
from test_oauth_runtime import Runtime, vault, callback
from facebook_token_import import import_token
from oauth_http import OAuthError


class FacebookImportTests(unittest.TestCase):
    setUp = oauth_tests.OAuthTests.setUp
    tearDown = oauth_tests.OAuthTests.tearDown
    assert_kind = oauth_tests.OAuthTests.assert_kind

    def prepare(self):
        """模擬兩項秘密已由本人完成安全輸入。"""
        runtime = Runtime(self.workspace, "facebook", backend=self.backend,
                          transport=self.http, clock=lambda: self.now[0])
        for name, value in (("app-secret", "fictional-secret"), ("dashboard-token", "fictional-page")):
            vault.store_secret(self.workspace, "facebook", name, value,
                               source="interactive-terminal", backend=self.backend)
        self.info = {"is_valid": True, "app_id": "123", "type": "PAGE", "expires_at": 0,
                     "scopes": ["pages_show_list", "pages_read_engagement", "public_profile"]}
        self.http.replies = [{"data": copy.deepcopy(self.info)}, {"id": "456", "name": "Fictional page"}]
        return runtime

    def run_import(self, runtime, **changes):
        """測試只使用公開虛構識別碼與最小測試範圍。"""
        args = dict(client_id="123", page_id="456", scopes=["pages_show_list", "pages_read_engagement"],
                    version="v1.0", confirmed_read=True, confirmed_store=True)
        return import_token(runtime, **(args | changes))

    def test_import_restore_no_callback_and_no_plaintext(self):
        runtime = self.prepare()
        result = self.run_import(runtime)
        self.assertEqual(result["status"], "ready")
        self.assertIs(result["callback_verified"], False)
        self.assertEqual(runtime.config()["callback_mode"], "token_import")
        self.http.replies = [{"data": self.info}, {"id": "456", "name": "Fictional page"}]
        restored = Runtime(self.workspace, "facebook", backend=self.backend, transport=self.http,
                           clock=lambda: self.now[0])
        self.assertEqual(restored.access(confirmed_read=True), "fictional-page")
        for path in self.workspace.rglob("*.json"):
            for value in ("fictional-page", "fictional-secret"):
                self.assertNotIn(value, path.read_text())
        with self.assertRaises(OAuthError):
            callback.serve(restored, confirmed=True)

    def test_authorization_and_existing_connection_stop_without_network(self):
        runtime = self.prepare()
        self.assert_kind("authorization_required", lambda: self.run_import(runtime, confirmed_store=False))
        self.assertFalse(self.http.calls)
        self.run_import(runtime)
        count = len(self.http.calls)
        self.assert_kind("recovery_required", lambda: self.run_import(runtime))
        self.assertEqual(len(self.http.calls), count)

    def test_wrong_app_type_scope_and_expiry_do_not_save_connection(self):
        runtime = self.prepare()
        for changes, kind in (({"app_id": "999"}, "target_mismatch"),
                              ({"type": "USER"}, "target_mismatch"),
                              ({"scopes": ["pages_show_list"]}, "permission_mismatch"),
                              ({"expires_at": 1}, "expired")):
            self.http.replies = [{"data": self.info | changes}]
            self.assert_kind(kind, lambda: self.run_import(runtime))
            self.assertEqual(runtime.status()["status"], "not_configured")

    def test_wrong_page_is_not_saved(self):
        runtime = self.prepare()
        self.http.replies[1]["id"] = "999"
        self.assert_kind("target_mismatch", lambda: self.run_import(runtime))
        self.assertEqual(runtime.status()["status"], "not_configured")

    def test_storage_failure_cannot_deliver_ready_or_retry(self):
        runtime = self.prepare()
        with mock.patch.object(runtime, "_save_bundle", side_effect=OSError("fictional-secret")):
            self.assert_kind("storage_incomplete", lambda: self.run_import(runtime))
        self.assertEqual(runtime.status()["status"], "storage_incomplete")
        count = len(self.http.calls)
        self.assert_kind("recovery_required", lambda: self.run_import(runtime))
        self.assertEqual(len(self.http.calls), count)


if __name__ == "__main__":
    unittest.main()
