"""只使用虛構平台回應、記憶體憑證庫與本機 loopback 的 OAuth 測試。"""

import contextlib
import copy
import hashlib
import hmac
import http.client
import io
import json
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlencode, urlsplit

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/social-media-setup/scripts"
sys.path.insert(0, str(SCRIPTS))
import credential_store as vault
import oauth_callback as callback
from oauth_http import OAuthError, OfficialHTTP, classify_response
from oauth_runtime import Runtime, validate_config

SCOPE = "https://www.googleapis.com/auth/youtube.readonly"


class MemoryVault:
    """不接觸 macOS 或 Windows 真實儲存。"""
    name = "macos-keychain"

    def __init__(self):
        self.values = {}

    def exists(self, target):
        return target in self.values

    def put(self, target, value, *, replace):
        if target in self.values and not replace:
            raise vault.CredentialStoreError("fictional conflict")
        self.values[target] = value

    def read(self, target):
        if target not in self.values:
            raise vault.CredentialNotFound("fictional missing")
        return self.values[target]

    def delete(self, target):
        del self.values[target]


class Transport:
    """依序提供虛構回應；任何未預期的請求都使測試失敗。"""
    def __init__(self):
        self.replies, self.calls = [], []

    def request(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint, kwargs))
        if not self.replies:
            raise AssertionError("unexpected request")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return copy.deepcopy(reply)


def configuration(platform):
    """中性虛構設定，不使用私人帳號或真實 callback。"""
    return {"platform": platform, "client_id": "123" if platform == "facebook" else "fictional-client",
            "target_id": "456" if platform == "facebook" else "fictional-channel",
            "scopes": ["pages_show_list", "pages_read_engagement"] if platform == "facebook" else [SCOPE],
            "secret_ref": "app-secret", "graph_version": "v25.0" if platform == "facebook" else "",
            "redirect_uri": "https://callback.example.test/oauth/callback" if platform == "facebook" else "",
            "callback_port": 8123 if platform == "facebook" else 0,
            "callback_mode": "https_proxy" if platform == "facebook" else "loopback",
            "tls_cert": "", "tls_key": ""}


def google_token(**overrides):
    """提供虛構的授權交換回應。"""
    return {"access_token": "fictional-access", "refresh_token": "fictional-refresh",
            "token_type": "Bearer", "expires_in": 3600, "scope": SCOPE} | overrides


def channel():
    return {"items": [{"id": "fictional-channel", "snippet": {"title": "Fictional channel"}}]}


class OAuthTests(unittest.TestCase):
    """跨平台生命週期及故障關卡，不啟用任何實機驗收。"""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-oauth-")
        self.workspace = Path(self.temp.name)
        self.backend, self.http, self.now = MemoryVault(), Transport(), [1000]
        self.native_guard = mock.patch.object(vault, "detect_backend", side_effect=AssertionError("no native access"))
        self.native_guard.start()

    def tearDown(self):
        self.native_guard.stop()
        self.temp.cleanup()

    def runtime(self, platform="youtube"):
        runtime = Runtime(self.workspace, platform, backend=self.backend, transport=self.http, clock=lambda: self.now[0])
        vault.store_secret(self.workspace, platform, "app-secret", "fictional-secret",
                           source="interactive-terminal", backend=self.backend)
        runtime.configure(configuration(platform), confirmed=True)
        return runtime

    def session(self, runtime, **kwargs):
        uri = "http://127.0.0.1:8123/oauth/callback" if runtime.platform == "youtube" else runtime.config()["redirect_uri"]
        return callback.CallbackSession(runtime, uri, confirmed=True, **kwargs)

    def finish(self, runtime, **kwargs):
        session = self.session(runtime, **kwargs)
        return session.accept("/oauth/callback?" + urlencode({"state": session.state, "code": "fictional-code"}))

    def google_ready(self):
        runtime = self.runtime()
        self.http.replies = [google_token(), channel()]
        self.finish(runtime)
        return runtime

    def facebook_replies(self):
        scopes = configuration("facebook")["scopes"] + ["public_profile"]
        user = {"data": {"is_valid": True, "app_id": "123", "type": "USER", "user_id": "789", "expires_at": 90000}}
        page = {"data": {"is_valid": True, "app_id": "123", "type": "PAGE", "expires_at": 0, "scopes": scopes}}
        return [{"access_token": "fictional-short"}, user, {"access_token": "fictional-long"}, copy.deepcopy(user),
                {"data": [{"permission": s, "status": "granted"} for s in scopes]},
                {"data": [{"id": "999", "access_token": "fictional-unselected", "tasks": ["ANALYZE"]}],
                 "paging": {"next": "https://untrusted.example.test/do-not-follow", "cursors": {"after": "next-cursor"}}},
                {"data": [{"id": "456", "access_token": "fictional-page", "tasks": ["MANAGE"]}]},
                page, {"id": "456", "name": "Fictional page"}]

    def assert_kind(self, kind, function):
        with self.assertRaises(OAuthError) as caught:
            function()
        self.assertEqual(caught.exception.kind, kind)

    def test_business_login_configuration_dialog_and_exchange(self):
        runtime = self.runtime('facebook')
        runtime.configure(configuration('facebook') | {'business_login_config_id': '987'},
                          confirmed=True, replace=True)
        session = self.session(runtime)
        params = parse_qs(urlsplit(session.authorization_url()).query)
        self.assertEqual(params['config_id'], ['987'])
        self.assertNotIn('scope', params)
        self.assertEqual(params['state'], [session.state])
        self.assertEqual(params['redirect_uri'], [runtime.config()['redirect_uri']])
        self.http.replies = self.facebook_replies()
        session.accept('/oauth/callback?' + urlencode({'state': session.state, 'code': 'fictional-code'}))
        self.assertEqual(runtime.status()['status'], 'ready')
        self.assertEqual(runtime.config()['business_login_config_id'], '987')

    def test_business_login_configuration_rejects_invalid_or_other_platform(self):
        for value in ('', 'abc', 123, True, None, '12 34'):
            self.assert_kind('invalid_configuration', lambda: validate_config(
                configuration('facebook') | {'business_login_config_id': value}))
        self.assert_kind('invalid_configuration', lambda: validate_config(
            configuration('youtube') | {'business_login_config_id': '987'}))

    def test_business_login_configuration_still_rejects_extra_grants(self):
        runtime = self.runtime('facebook')
        runtime.configure(configuration('facebook') | {'business_login_config_id': '987'},
                          confirmed=True, replace=True)
        self.http.replies = self.facebook_replies()
        self.http.replies[4]['data'].append({'permission': 'business_management', 'status': 'granted'})
        self.assert_kind('permission_mismatch', lambda: self.finish(runtime))
        self.assertEqual(runtime.status()['parts'], 0)

    def test_configuration_is_confirmed_and_private(self):
        runtime = Runtime(self.workspace, "youtube", backend=self.backend, transport=self.http)
        self.assert_kind("authorization_required", lambda: runtime.configure(configuration("youtube")))
        self.assertFalse(self.backend.values)
        runtime.configure(configuration("youtube"), confirmed=True)
        for path in self.workspace.rglob("*.json"):
            self.assertNotIn("fictional-client", path.read_text())
            self.assertNotIn("fictional-channel", path.read_text())

    def test_invalid_configuration_fails_closed(self):
        cases = [("scopes", [["nested"]]), ("callback_port", True), ("redirect_uri", None),
                 ("callback_mode", "external"), ("scopes", [SCOPE, SCOPE])]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                config = configuration("youtube") | {key: value}
                self.assert_kind("invalid_configuration", lambda: validate_config(config))
        for uri in ("http://callback.example.test/oauth/callback", "https://callback.example.test:bad/oauth/callback"):
            self.assert_kind("invalid_configuration", lambda: validate_config(configuration("facebook") | {"redirect_uri": uri}))

    def test_google_pkce_authorization_and_replay(self):
        runtime = self.runtime()
        session = self.session(runtime)
        params = parse_qs(urlsplit(session.authorization_url()).query)
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertEqual(params["access_type"], ["offline"])
        self.assertNotIn("client_secret", params)
        self.assert_kind("replay", session.authorization_url)
        self.http.replies = [google_token(), channel()]
        path = "/oauth/callback?" + urlencode({"state": session.state, "code": "fictional-code"})
        self.assertEqual(session.accept(path)["status"], "ready")
        self.assert_kind("replay", lambda: session.accept(path))
        self.assertEqual(len(self.http.calls), 2)
        self.assertEqual(session.state, "")
        self.assertEqual(session.verifier, "")

    def test_bad_callback_never_exchanges(self):
        runtime = self.runtime()
        for suffix in ("state=bad&code=secret", "state={state}&code=a&code=b", "state={state}&code=",
                       "state={state}&code=a&iss=https%3A%2F%2Fevil.example.test", "state={state}&code=%0A"):
            session = self.session(runtime, restart=True)
            self.assert_kind("invalid_callback", lambda: session.accept("/oauth/callback?" + suffix.format(state=session.state)))
        self.assertFalse(self.http.calls)

    def test_cancel_timeout_and_old_session(self):
        runtime = self.runtime()
        old = self.session(runtime)
        session = self.session(runtime, restart=True, clock=lambda: self.now[0])
        self.assert_kind("replay", lambda: old.accept("/oauth/callback?state=x&code=y"))
        self.assertEqual(runtime.status()["attempt"], session.attempt)
        self.assert_kind("cancelled", lambda: session.accept("/oauth/callback?state=" + session.state + "&error=access_denied"))
        session = self.session(runtime, restart=True, clock=lambda: self.now[0])
        self.now[0] += 901
        self.assert_kind("timeout", lambda: session.accept("/oauth/callback?state=" + session.state + "&code=a"))
        self.assertFalse(self.http.calls)

    def test_native_preflight_before_oauth(self):
        runtime = self.runtime()
        self.backend.values.clear()
        with self.assertRaises(vault.CredentialStoreError):
            self.session(runtime)
        self.assertFalse(self.http.calls)

    def test_google_exchange_preserves_private_values(self):
        runtime = self.google_ready()
        self.assertEqual(self.http.calls[0][0], "POST")
        form = self.http.calls[0][2]["form"]
        self.assertEqual(form["grant_type"], "authorization_code")
        self.assertIn("code_verifier", form)
        self.assertEqual(runtime.status()["status"], "ready")
        for path in self.workspace.rglob("*.json"):
            for secret in ("fictional-access", "fictional-refresh", "fictional-secret", "fictional-code"):
                self.assertNotIn(secret, path.read_text())
        self.http.replies = [channel()]
        self.assertEqual(runtime.access(confirmed_read=True), "fictional-access")

    def test_google_refresh_preserves_or_rotates_refresh_token(self):
        runtime = self.google_ready()
        self.now[0] = 4600
        self.assert_kind("refresh_required", lambda: runtime.access(confirmed_read=True))
        self.http.replies = [{"access_token": "fictional-next", "token_type": "Bearer", "expires_in": 3600}, channel()]
        self.assertEqual(runtime.access(confirmed_read=True, allow_refresh=True, resume=True), "fictional-next")
        self.assertEqual(runtime._bundle()["refresh_token"], "fictional-refresh")
        self.now[0] = 8200
        self.http.replies = [google_token(refresh_token="fictional-rotated"), channel()]
        runtime.access(confirmed_read=True, allow_refresh=True)
        self.assertEqual(runtime._bundle()["refresh_token"], "fictional-rotated")

    def test_generated_tokens_save_without_human_input_and_never_enter_files(self):
        """已核准的交換與刷新直接存原生介面，不再要求人類複製 Token。"""
        with mock.patch("builtins.input", side_effect=AssertionError("不得再次人工確認")), mock.patch.object(
                vault.getpass, "getpass", side_effect=AssertionError("不得要求貼上 OAuth Token")):
            runtime = self.google_ready()
            self.assertEqual(runtime._bundle()["access_token"], "fictional-access")
            self.now[0] = 4600
            self.http.replies = [google_token(access_token="fictional-new-access",
                                             refresh_token="fictional-new-refresh"), channel()]
            runtime.access(confirmed_read=True, allow_refresh=True)
            self.assertEqual(runtime._bundle()["refresh_token"], "fictional-new-refresh")
            self.assertEqual(runtime.status()["status"], "ready")
        # 真實原生庫另行驗收；此處查驗檔案與公開狀態不含模擬秘密。
        for path in self.workspace.rglob("*.json"):
            for value in ("fictional-new-access", "fictional-new-refresh"):
                self.assertNotIn(value, path.read_text())
                self.assertNotIn(value, json.dumps(runtime.status()))

    def test_expired_refresh_and_invalid_grant_stop(self):
        runtime = self.runtime()
        self.http.replies = [google_token(refresh_token_expires_in=100), channel()]
        self.finish(runtime)
        self.now[0] += 3601
        before = len(self.http.calls)
        self.assert_kind("reauth_required", lambda: runtime.access(confirmed_read=True, allow_refresh=True))
        self.assertEqual(len(self.http.calls), before)
        self.http.replies = [OAuthError("reauth_required")]
        self.assert_kind("reauth_required", lambda: self.finish(runtime, restart=True))
        self.assertEqual(runtime.status()["status"], "reauth_required")

    def test_refresh_result_unknown_is_not_retried(self):
        runtime = self.google_ready()
        self.now[0] = 4600
        self.http.replies = [OAuthError("remote_result_unknown")]
        self.assert_kind("remote_result_unknown", lambda: runtime.access(confirmed_read=True, allow_refresh=True))
        count = len(self.http.calls)
        self.assert_kind("recovery_required", lambda: runtime.access(confirmed_read=True, allow_refresh=True, resume=True))
        self.assertEqual(len(self.http.calls), count)

    def test_missing_scope_or_refresh_is_not_ready(self):
        runtime = self.runtime()
        for field, expected in (("scope", "permission_mismatch"), ("refresh_token", "reauth_required")):
            response = google_token()
            del response[field]
            self.http.replies = [response]
            self.assert_kind(expected, lambda: self.finish(runtime, restart=True))
            self.assertNotEqual(runtime.status()["status"], "ready")

    def test_scope_or_channel_mismatch(self):
        runtime = self.runtime()
        self.http.replies = [google_token(scope=SCOPE + " extra-scope")]
        self.assert_kind("permission_mismatch", lambda: self.finish(runtime))
        self.http.replies = [google_token(), {"items": []}]
        self.assert_kind("target_mismatch", lambda: self.finish(runtime, restart=True))

    def test_google_channel_pagination(self):
        runtime = self.runtime()
        self.http.replies = [google_token(), {"items": [], "nextPageToken": "next"}, channel()]
        self.finish(runtime)
        self.assertEqual(self.http.calls[-1][2]["query"]["pageToken"], "next")

    def test_long_tokens_are_chunked_only_in_vault(self):
        # 使用 Windows 名稱契約，仍是記憶體替身，絕不呼叫 WinCred。
        self.backend.name = "windows-credential-manager"
        runtime = self.runtime()
        token = "fictional-long-token-" * 1000
        self.http.replies = [google_token(access_token=token), channel()]
        self.finish(runtime)
        self.assertGreater(runtime.status()["parts"], 1)
        self.assertEqual(runtime._bundle()["access_token"], token)
        self.assertTrue(all(len(v.encode()) <= 2560 for v in self.backend.values.values()))

    def test_interrupted_storage_can_only_resume_readback(self):
        runtime = self.google_ready()
        runtime.mark("saving")
        self.http.replies = [channel()]
        runtime.access(confirmed_read=True, resume=True)
        self.assertEqual(self.http.calls[-1][0], "GET")
        runtime.mark("storage_incomplete")
        part = next(key for key in self.backend.values if key.endswith("-p0"))
        del self.backend.values[part]
        count = len(self.http.calls)
        self.assert_kind("storage_incomplete", lambda: runtime.access(confirmed_read=True, resume=True))
        self.assertEqual(len(self.http.calls), count)

    def test_interrupted_exchange_never_reuses_code(self):
        runtime = self.runtime()
        self.http.replies = [TimeoutError("fictional-secret must not escape")]
        self.assert_kind("remote_result_unknown", lambda: self.finish(runtime))
        count = len(self.http.calls)
        self.assert_kind("recovery_required", lambda: runtime.access(confirmed_read=True, resume=True))
        self.assertEqual(len(self.http.calls), count)

    def test_facebook_exchange_page_selection_and_proof(self):
        runtime = self.runtime("facebook")
        self.http.replies = self.facebook_replies()
        self.finish(runtime)
        self.assertEqual(runtime.status()["status"], "ready")
        self.assertEqual(runtime._bundle(), {"platform": "facebook", "access_token": "fictional-page"})
        values = " ".join(self.backend.values.values())
        for secret in ("fictional-short", "fictional-long", "fictional-unselected"):
            self.assertNotIn(secret, values)
        self.assertTrue(all(urlsplit(call[1]).hostname == "graph.facebook.com" for call in self.http.calls))
        self.assertEqual(self.http.calls[6][2]["query"]["after"], "next-cursor")
        self.assertEqual(self.http.calls[2][2]["query"]["grant_type"], "fb_exchange_token")
        proof = hmac.new(b"fictional-secret", b"fictional-page|940", hashlib.sha256).hexdigest()
        self.assertEqual(self.http.calls[-1][2]['query']['appsecret_time'], 940)
        self.assertEqual(self.http.calls[-1][2]["query"]["appsecret_proof"], proof)
        self.http.replies = self.facebook_replies()[-2:]
        self.assertEqual(runtime.access(confirmed_read=True), "fictional-page")
        self.assertTrue(all("oauth/access_token" not in c[1] for c in self.http.calls[-2:]))

    def test_facebook_maintenance_warns_before_page_or_data_access_expiry(self):
        runtime = self.runtime("facebook")
        self.http.replies = self.facebook_replies()
        self.finish(runtime)
        for field in ("expires_at", "data_access_expires_at"):
            page = self.facebook_replies()[-2]
            page["data"][field] = self.now[0] + 6 * 24 * 60 * 60
            self.http.replies = [page]
            self.assert_kind("reauth_required", lambda: runtime.access(
                confirmed_read=True, maintenance=True, resume=field == "data_access_expires_at"))

    def test_facebook_rejects_wrong_app_user_and_page(self):
        runtime = self.runtime("facebook")
        for index, field, value in ((1, "app_id", "wrong"), (3, "user_id", "different"), (7, "type", "USER")):
            replies = self.facebook_replies()
            replies[index]["data"][field] = value
            self.http.replies = replies
            self.assert_kind("target_mismatch", lambda: self.finish(runtime, restart=True))

    def test_facebook_specific_page_when_complete_listing_is_empty(self):
        runtime = self.runtime('facebook')
        replies = self.facebook_replies()
        self.http.replies = replies[:5] + [{'data': []},
            {'id': '456', 'name': 'Fictional page', 'access_token': 'fictional-page'}] + replies[-2:]
        self.finish(runtime)
        self.assertEqual(runtime.status()['status'], 'ready')
        call = self.http.calls[6]
        self.assertEqual(call[1], 'https://graph.facebook.com/v25.0/456')
        self.assertEqual(call[2]['query']['fields'], 'id,name,access_token')
        self.assertNotIn('fictional-long', ' '.join(self.backend.values.values()))

    def test_facebook_specific_page_rejects_wrong_target_or_missing_token(self):
        runtime = self.runtime('facebook')
        for page in ({'id':'999', 'name':'Other', 'access_token':'fictional-other'},
                     {'id':'456', 'name':'Fictional page'}):
            self.http.replies = self.facebook_replies()[:5] + [{'data': []}, page]
            self.assert_kind('target_mismatch', lambda: self.finish(runtime, restart=True))
            self.assertEqual(runtime.status()['parts'], 0)

    def test_facebook_failed_listing_does_not_trigger_specific_page(self):
        runtime = self.runtime('facebook')
        self.http.replies = self.facebook_replies()[:5] + [OAuthError('read_failed')]
        self.assert_kind('read_failed', lambda: self.finish(runtime))
        self.assertFalse(any(c[1].endswith('/456') for c in self.http.calls))

    def test_facebook_unknown_expiry_revocation_and_permission(self):
        runtime = self.runtime("facebook")
        for field, value, expected in (("expires_at", None, "read_failed"), ("expires_at", 999, "expired"),
                                        ("is_valid", False, "reauth_required"), ("scopes", [], "permission_mismatch")):
            self.http.replies = self.facebook_replies()
            self.http.replies[7]["data"][field] = value
            self.assert_kind(expected, lambda: self.finish(runtime, restart=True))

    def test_facebook_proxy_requires_explicit_confirmation(self):
        runtime = self.runtime("facebook")
        self.assert_kind("authorization_required", lambda: callback.serve(runtime, confirmed=True))
        self.assertFalse(self.http.calls)

    def test_loopback_http_protocol_without_browser_or_external_network(self):
        runtime = self.runtime()
        self.http.replies = [google_token(), channel()]
        messages, errors = queue.Queue(), []
        stdout, stderr = io.StringIO(), io.StringIO()

        def run():
            """測試執行緒只開本機 socket，平台請求仍使用 Transport。"""
            try:
                callback.serve(runtime, confirmed=True, notify=lambda text, **kw: messages.put(json.loads(text)))
            except Exception as error:
                errors.append(error)

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            thread = threading.Thread(target=run, daemon=True)
            thread.start()
            try:
                notice = messages.get(timeout=5)
            except queue.Empty:
                self.fail(f"fictional receiver failed: {errors!r}")
            uri = urlsplit(notice["launch_url"])
            self.assertEqual(uri.hostname, "127.0.0.1")

            def request(path, host=None):
                """不跟隨官方授權 Location，避免真實外部連線。"""
                client = http.client.HTTPConnection(uri.hostname, uri.port, timeout=3)
                client.request("GET", path, headers={"Host": host or uri.netloc})
                reply = client.getresponse()
                result = (reply.status, reply.getheader("Location"), reply.read())
                client.close()
                return result

            self.assertEqual(request(uri.path, "attacker.example.test")[0], 400)
            status, location, _ = request(uri.path)
            self.assertEqual(status, 302)
            self.assertEqual(urlsplit(location).hostname, "accounts.google.com")
            state = parse_qs(urlsplit(location).query)["state"][0]
            result = request("/oauth/callback?" + urlencode({"state": state, "code": "fictional-code"}))
            self.assertEqual(result[:2], (303, "/oauth/complete"))
            self.assertNotIn(b"fictional-code", result[2])
            self.assertEqual(request("/oauth/complete")[0], 200)
            thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertFalse(errors)
        self.assertEqual(stdout.getvalue() + stderr.getvalue(), "")
        self.assertEqual(runtime.status()["status"], "ready")


class HTTPTests(unittest.TestCase):
    """傳輸層不跟隨重新導向、不重試、不洩漏錯誤本文。"""
    def test_fixed_hosts_only(self):
        for endpoint in ("https://evil.example.test/token", "http://oauth2.googleapis.com/token",
                         "https://oauth2.googleapis.com/token?secret=x", "https://graph.facebook.com/v25.0/delete"):
            with self.assertRaises(OAuthError):
                OfficialHTTP().request("GET", endpoint)

    def test_cli_argument_errors_do_not_echo_secrets(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "oauth_callback.py"), "status",
                                 "--workspace-root", "fictional", "--platform", "youtube",
                                 "--token", "fictional-sensitive-value"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("fictional-sensitive-value", result.stdout + result.stderr)
        self.assertIn("invalid_arguments", result.stderr)

    def test_state_schema_matches_runtime_states(self):
        from oauth_runtime import STATES
        schema = json.loads((SCRIPTS.parent / "references/oauth-state.schema.json").read_text())
        self.assertEqual(set(schema["properties"]["status"]["enum"]), STATES)

    def test_preview_binds_workspace_and_connection_without_native_access(self):
        with tempfile.TemporaryDirectory(prefix="fictional-preview-") as temporary:
            args = ["oauth_callback.py", "preview", "--workspace-root", temporary, "--platform", "youtube",
                    "--client-id", "fictional-client", "--target-id", "fictional-channel", "--scope", SCOPE]
            digests = []
            for name in ("first", "second"):
                output = io.StringIO()
                with mock.patch.object(sys, "argv", args + ["--connection", name]), contextlib.redirect_stdout(output), \
                     mock.patch.object(callback, "Runtime", side_effect=AssertionError("no native runtime")):
                    self.assertEqual(callback.main(), 0)
                digests.append(json.loads(output.getvalue())["preview_digest"])
                self.assertNotIn("fictional-client", output.getvalue())
            self.assertNotEqual(digests[0], digests[1])
            self.assertFalse(list(Path(temporary).iterdir()))

    def test_configure_rejects_wrong_digest_before_native_access(self):
        with tempfile.TemporaryDirectory(prefix="fictional-preview-") as temporary:
            args = ["oauth_callback.py", "configure", "--workspace-root", temporary, "--platform", "youtube",
                    "--client-id", "fictional-client", "--target-id", "fictional-channel", "--scope", SCOPE,
                    "--preview-digest", "incorrect", "--confirm-config"]
            output = io.StringIO()
            with mock.patch.object(sys, "argv", args), contextlib.redirect_stdout(output), \
                 mock.patch.object(callback, "Runtime", side_effect=AssertionError("no native runtime")):
                self.assertEqual(callback.main(), 2)
            self.assertEqual(json.loads(output.getvalue())["status"], "authorization_required")

    def test_classification_is_sanitized(self):
        for status, payload, mutation, expected in (
            (400, {"error": "invalid_grant"}, True, "reauth_required"),
            (400, {"error": {"code": 190, "message": "fictional-secret"}}, False, "reauth_required"),
            (429, {}, False, "rate_limited"), (403, {}, False, "permission_mismatch"),
            (403, {"error": {"errors": [{"reason": "quotaExceeded"}]}}, False, "rate_limited"),
            (401, {"error": {"errors": [{"reason": "youtubeSignupRequired"}]}}, False, "target_mismatch"),
            (302, {}, True, "remote_result_unknown"), (200, None, False, "read_failed")):
            with self.assertRaises(OAuthError) as caught:
                classify_response(status, payload, mutation)
            self.assertEqual(str(caught.exception), expected)

    def test_timeout_does_not_retry_or_print_secrets(self):
        with mock.patch("oauth_http.http.client.HTTPSConnection") as factory:
            factory.return_value.request.side_effect = TimeoutError("fictional-secret")
            with self.assertRaises(OAuthError) as caught:
                OfficialHTTP().request("POST", "https://oauth2.googleapis.com/token", form={"code": "fictional-code"}, mutation=True)
            self.assertEqual(str(caught.exception), "remote_result_unknown")
            self.assertEqual(factory.return_value.request.call_count, 1)
            self.assertTrue(factory.call_args.kwargs["context"].check_hostname)

    def test_redirect_never_followed(self):
        with mock.patch("oauth_http.http.client.HTTPSConnection") as factory:
            response = factory.return_value.getresponse.return_value
            response.status, response.read.return_value = 302, b"{}"
            with self.assertRaises(OAuthError):
                OfficialHTTP().request("GET", "https://www.googleapis.com/youtube/v3/channels", bearer="fictional-secret")
            self.assertEqual(factory.call_count, 1)
            self.assertEqual(factory.return_value.request.call_args.kwargs["headers"]["Authorization"], "Bearer fictional-secret")


if __name__ == "__main__":
    unittest.main()
