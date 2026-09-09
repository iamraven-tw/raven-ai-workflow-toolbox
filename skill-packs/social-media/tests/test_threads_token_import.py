"""官方測試權杖匯入的虛構驗證，禁止網路及原生庫存取。"""
import unittest
import test_meta_user_oauth as meta_tests
from test_oauth_runtime import Runtime, vault, callback
from threads_token_import import import_token
from oauth_http import OAuthError


class ThreadsImportTests(unittest.TestCase):
    setUp = meta_tests.MetaUserOAuthTests.setUp
    kind = meta_tests.MetaUserOAuthTests.kind
    def prepare_import(self):
        runtime = Runtime(self.workspace, 'threads', backend=self.backend,
                          transport=self.http, clock=lambda: self.now[0])
        vault.store_secret(self.workspace, 'threads', 'dashboard-token', 'fictional-import',
                           source='interactive-terminal', backend=self.backend)
        info = {'app_id': '123', 'user_id': '456', 'expires_at': self.now[0] + 5000000,
                'scopes': ['threads_basic', 'threads_manage_insights']}
        user = {'id': '456', 'username': 'fictional'}
        self.http.replies = [{'data': info}, user, {'data': info}, user]
        return runtime

    def run_import(self, runtime, **overrides):
        args = dict(client_id='123', username='fictional',
            scopes=['threads_basic', 'threads_manage_insights'], version='v1.0',
            source_ref='dashboard-token', confirmed_read=True, confirmed_store=True)
        return import_token(runtime, **(args | overrides))

    def test_import_and_separate_runtime_access(self):
        runtime = self.prepare_import()
        self.assertEqual(self.run_import(runtime)['status'], 'ready')
        self.assertEqual(runtime.config()['callback_mode'], 'token_import')
        self.http.replies = [{'data': {'app_id': '123', 'user_id': '456',
            'expires_at': self.now[0] + 5000000,
            'scopes': ['threads_basic', 'threads_manage_insights']}},
            {'id': '456', 'username': 'fictional'}]
        restored = Runtime(self.workspace, 'threads', backend=self.backend,
                           transport=self.http, clock=lambda: self.now[0])
        self.assertEqual(restored.access(confirmed_read=True), 'fictional-import')
        for path in self.workspace.rglob('*.json'):
            self.assertNotIn('fictional-import', path.read_text())
        with self.assertRaises(OAuthError):
            callback.serve(restored, confirmed=True)

    def test_rejects_wrong_app_before_config_write(self):
        runtime = self.prepare_import()
        self.http.replies[0]['data']['app_id'] = '999'
        self.kind('target_mismatch', lambda: self.run_import(runtime))
        self.assertEqual(runtime.status()['status'], 'not_configured')

    def test_rejects_unapproved_scope(self):
        runtime = self.prepare_import()
        self.http.replies[0]['data']['scopes'].append('threads_content_publish')
        self.kind('permission_mismatch', lambda: self.run_import(runtime))
        self.assertEqual(runtime.status()['status'], 'not_configured')

    def test_rejects_username_and_short_expiry(self):
        runtime = self.prepare_import()
        self.kind('target_mismatch', lambda: self.run_import(runtime, username='other'))
        runtime = self.prepare_import_fresh_expiry(runtime)
        self.kind('expired', lambda: self.run_import(runtime))

    def prepare_import_fresh_expiry(self, runtime):
        self.http.replies = [{'data': {'app_id': '123', 'user_id': '456',
            'expires_at': self.now[0] + 3600,
            'scopes': ['threads_basic', 'threads_manage_insights']}}]
        return runtime

    def test_no_permission_no_read_and_no_overwrite(self):
        runtime = self.prepare_import()
        self.kind('authorization_required', lambda: self.run_import(runtime, confirmed_read=False))
        self.assertFalse(self.http.calls)
        self.run_import(runtime)
        count = len(self.http.calls)
        self.kind('recovery_required', lambda: self.run_import(runtime))
        self.assertEqual(len(self.http.calls), count)
