"""Instagram／Threads 完全虛構的 OAuth 驗證，不碰帳號、網路或原生憑證庫。"""

import json
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlencode, urlsplit

from test_oauth_runtime import MemoryVault, Transport, configuration, vault, callback
from oauth_http import OAuthError, OfficialHTTP, classify_response
from oauth_runtime import Runtime, validate_config
import meta_user_oauth as adapter


def config(platform):
    """所有 ID 與網域都是虛構的；IG 兩種 ID 刻意不同。"""
    value = configuration("facebook")
    value.update(platform=platform, scopes=(["instagram_business_basic", "instagram_business_content_publish",
                                             "instagram_business_manage_comments", "instagram_business_manage_insights",
                                             "instagram_business_manage_messages"]
        if platform == "instagram" else ["threads_basic", "threads_content_publish"]),
        graph_version="v25.0" if platform == "instagram" else "v1.0")
    return value


def long_token(token="fictional-long", ttl=60 * adapter.DAY):
    return {"access_token": token, "token_type": "bearer", "expires_in": ttl}


class MetaUserOAuthTests(unittest.TestCase):
    """交換、儲存、取用、刷新與停止條件，HTTP 回應皆由記憶體提供。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-meta-oauth-")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.backend, self.http, self.now = MemoryVault(), Transport(), [100000]
        guard = mock.patch.object(vault, "detect_backend", side_effect=AssertionError("no native access"))
        guard.start()
        self.addCleanup(guard.stop)
        network = mock.patch("http.client.HTTPSConnection", side_effect=AssertionError("no network"))
        network.start()
        self.addCleanup(network.stop)

    def runtime(self, platform):
        # 每個子情境使用獨立的虛構工作區，不覆蓋上一個情境的憑證。
        workspace = self.workspace / (platform + "-" + str(len(self.backend.values)))
        workspace.mkdir()
        runtime = Runtime(workspace, platform, backend=self.backend, transport=self.http, clock=lambda: self.now[0])
        vault.store_secret(workspace, platform, "app-secret", "fictional-secret",
                           source="interactive-terminal", backend=self.backend)
        runtime.configure(config(platform), confirmed=True)
        return runtime

    def reads(self, platform, expiry=None):
        if platform == "instagram":
            return [{"id": "789", "user_id": "456", "username": "fictional", "account_type": "Business"}]
        return [{"data": {"user_id": "456", "scopes": config(platform)["scopes"],
                          "expires_at": expiry or self.now[0] + 60 * adapter.DAY}},
                {"id": "456", "username": "fictional"}]

    def replies(self, platform):
        short = {"access_token": "fictional-short", "user_id": 789 if platform == "instagram" else 456}
        if platform == "instagram":
            short["permissions"] = ",".join(config(platform)["scopes"])
            short = {"data": [short]}
        return [short, long_token()] + self.reads(platform)

    def session(self, runtime):
        return callback.CallbackSession(runtime, config(runtime.platform)["redirect_uri"], confirmed=True)

    def finish(self, runtime):
        session = self.session(runtime)
        return session.accept("/oauth/callback?" + urlencode({"state": session.state, "code": "fictional-code"}))

    def ready(self, platform):
        runtime = self.runtime(platform)
        self.http.replies = self.replies(platform)
        self.assertEqual(self.finish(runtime)["status"], "ready")
        self.assertFalse(self.http.replies)
        self.http.calls.clear()
        return runtime

    def kind(self, expected, action):
        with self.assertRaises(OAuthError) as caught:
            action()
        self.assertEqual(caught.exception.kind, expected)

    def test_configuration_separates_routes_and_requires_https(self):
        for platform in sorted(adapter.PLATFORMS):
            self.assertEqual(validate_config(config(platform))["platform"], platform)
            for changed in ({"scopes": ["pages_show_list"]}, {"scopes": config(platform)["scopes"] + ["pages_messaging"]},
                            {"redirect_uri": "http://callback.example.test/oauth/callback"}, {"target_id": "bad"}):
                with self.subTest(platform=platform, changed=changed):
                    self.kind("invalid_configuration", lambda: validate_config(config(platform) | changed))

    def test_authorization_urls_and_once_only_launch(self):
        for platform in sorted(adapter.PLATFORMS):
            session = self.session(self.runtime(platform))
            url = urlsplit(session.authorization_url())
            self.assertEqual(url.scheme + "://" + url.netloc + url.path, adapter.AUTH_URLS[platform])
            query = parse_qs(url.query)
            self.assertEqual(query["scope"], [",".join(config(platform)["scopes"])])
            self.assertNotIn("client_secret", query)
            self.assertNotIn("code_challenge", query)
            self.kind("replay", session.authorization_url)

    def test_both_exchange_save_only_long_token_and_private_metadata(self):
        for platform in sorted(adapter.PLATFORMS):
            runtime = self.runtime(platform)
            self.http.replies = self.replies(platform)
            self.finish(runtime)
            bundle = runtime._bundle()
            self.assertEqual(bundle["expires_at"], self.now[0] + 60 * adapter.DAY)
            self.assertNotIn("refresh_token", bundle)
            calls = self.http.calls
            self.assertEqual(calls[0][0], "POST")
            self.assertEqual(calls[0][2].get("multipart", False), platform == "instagram")
            self.assertEqual(calls[1][2]["query"]["grant_type"], ("ig" if platform == "instagram" else "th") + "_exchange_token")
            self.assertNotIn("fictional-short", json.dumps(self.backend.values))
            for path in self.workspace.rglob("*.json"):
                raw = path.read_text()
                for private in ("fictional-long", "fictional-secret", "callback.example.test", "provider_user_id"):
                    self.assertNotIn(private, raw)
            self.http.calls.clear()

    def test_instagram_accepts_flat_exchange_and_nested_profile(self):
        runtime = self.runtime("instagram")
        replies = self.replies("instagram")
        replies[0] = replies[0]["data"][0]
        replies[-1] = {"data": [replies[-1]]}
        self.http.replies = replies
        self.assertEqual(self.finish(runtime)["status"], "ready")

    def test_instagram_rejects_incomplete_or_extra_initial_permissions(self):
        for permissions in (None, "instagram_business_basic", "instagram_business_basic,instagram_business_basic",
                            config("instagram")["scopes"] + ["instagram_business_manage_messages"]):
            with self.subTest(permissions=permissions):
                runtime = self.runtime("instagram")
                self.http.replies = self.replies("instagram")
                self.http.replies[0]["data"][0]["permissions"] = permissions
                self.http.calls.clear()
                self.kind("permission_mismatch", lambda: self.finish(runtime))
                self.assertEqual(len(self.http.calls), 1)

    def test_instagram_binds_both_ids_and_professional_account(self):
        for changed in ({"id": "456"}, {"user_id": "789"}, {"account_type": "PERSONAL"}, {"username": ""}):
            runtime = self.runtime("instagram")
            self.http.replies = self.replies("instagram")
            self.http.replies[-1].update(changed)
            self.kind("target_mismatch", lambda: self.finish(runtime))
            self.assertNotEqual(runtime.status()["status"], "ready")

    def test_threads_checks_current_debugger_and_profile(self):
        cases = [({"user_id": "789"}, "target_mismatch"), ({"app_id": "999"}, "target_mismatch"),
                 ({"is_valid": False}, "reauth_required"), ({"scopes": ["threads_basic"]}, "permission_mismatch"),
                 ({"expires_at": 0}, "read_failed"), ({"expires_at": self.now[0]}, "reauth_required"),
                 ({"data_access_expires_at": self.now[0]}, "reauth_required")]
        for changed, expected in cases:
            runtime = self.runtime("threads")
            self.http.replies = self.replies("threads")
            self.http.replies[2]["data"].update(changed)
            self.kind(expected, lambda: self.finish(runtime))

    def test_threads_rejects_wrong_profile_even_if_debugger_matches(self):
        runtime = self.runtime("threads")
        self.http.replies = self.replies("threads")
        self.http.replies[-1]["id"] = "999"
        self.kind("target_mismatch", lambda: self.finish(runtime))

    def test_invalid_long_token_has_no_invented_expiry(self):
        for value in (None, 0, True, "3600", -1):
            runtime = self.runtime("instagram")
            self.http.replies = self.replies("instagram")
            self.http.replies[1]["expires_in"] = value
            self.kind("remote_result_unknown", lambda: self.finish(runtime))

    def test_bad_token_type_is_sanitized(self):
        runtime = self.runtime("threads")
        self.http.replies = self.replies("threads")
        self.http.replies[1]["token_type"] = None
        self.kind("remote_result_unknown", lambda: self.finish(runtime))

    def test_normal_access_reads_current_identity_without_refresh(self):
        for platform in sorted(adapter.PLATFORMS):
            runtime = self.ready(platform)
            self.http.replies = self.reads(platform)
            self.assertEqual(runtime.access(confirmed_read=True, allow_refresh=True), "fictional-long")
            self.assertTrue(all(not c[2].get("mutation") for c in self.http.calls))

    def test_instagram_current_check_uses_identity_only_and_never_fakes_scope_endpoint(self):
        runtime = self.ready("instagram")
        self.http.replies = self.reads("instagram")
        self.assertEqual(runtime.access(confirmed_read=True), "fictional-long")
        self.assertEqual([urlsplit(call[1]).path for call in self.http.calls], ["/v25.0/me"])
        for endpoint in ("https://graph.instagram.com/v25.0/me/permissions",
                         "https://graph.instagram.com/debug_token"):
            self.kind("invalid_configuration", lambda endpoint=endpoint: OfficialHTTP().request("GET", endpoint))

    def test_instagram_feature_permission_or_reauth_failure_is_sanitized(self):
        cases = ((403, {}, "permission_mismatch"),
                 (400, {"error": {"code": 10}}, "permission_mismatch"),
                 (400, {"error": {"code": 200}}, "permission_mismatch"),
                 (401, {}, "reauth_required"),
                 (400, {"error": {"code": 190}}, "reauth_required"),
                 (429, {}, "rate_limited"))
        for status, payload, expected in cases:
            with self.subTest(status=status, payload=payload):
                self.kind(expected, lambda: classify_response(status, payload))
        self.kind("remote_result_unknown", lambda: classify_response(500, {}, mutation=True))

    def test_expired_token_requires_new_consent_without_http(self):
        for platform in sorted(adapter.PLATFORMS):
            runtime = self.ready(platform)
            self.now[0] += 61 * adapter.DAY
            self.kind("reauth_required", lambda: runtime.access(confirmed_read=True, allow_refresh=True))
            self.assertFalse(self.http.calls)

    def test_refresh_eligible_tokens_once_and_verify_new_token(self):
        for platform in sorted(adapter.PLATFORMS):
            runtime = self.ready(platform)
            revision = runtime.status()["revision"]
            self.now[0] += 54 * adapter.DAY
            self.http.replies = self.reads(platform) + [long_token("fictional-new")] + self.reads(platform)
            self.assertEqual(runtime.access(confirmed_read=True, allow_refresh=True), "fictional-new")
            mutations = [c for c in self.http.calls if c[2].get("mutation")]
            self.assertEqual(len(mutations), 1)
            self.assertEqual(mutations[0][2]["query"]["grant_type"], ("ig" if platform == "instagram" else "th") + "_refresh_token")
            self.assertNotIn("client_secret", mutations[0][2]["query"])
            self.assertNotEqual(runtime.status()["revision"], revision)
            self.assertEqual(runtime._bundle()["issued_at"], self.now[0])

    def test_under_24_hours_does_not_refresh_even_with_short_ttl(self):
        runtime = self.ready("instagram")
        bundle = runtime._bundle() | {"expires_at": self.now[0] + 2 * adapter.DAY}
        runtime._save_bundle(bundle)
        runtime.mark("ready")
        self.http.replies = self.reads("instagram")
        self.assertEqual(runtime.access(confirmed_read=True, allow_refresh=True), "fictional-long")
        self.assertEqual(len(self.http.calls), 1)

    def test_no_refresh_authority_uses_valid_old_token(self):
        runtime = self.ready("threads")
        self.now[0] += 54 * adapter.DAY
        self.http.replies = self.reads("threads")
        self.assertEqual(runtime.access(confirmed_read=True), "fictional-long")
        self.assertTrue(all(not c[2].get("mutation") for c in self.http.calls))

    def test_near_expiry_without_refresh_authority_stops(self):
        runtime = self.ready("instagram")
        self.now[0] += 60 * adapter.DAY - 30
        self.http.replies = self.reads("instagram")
        self.kind("refresh_required", lambda: runtime.access(confirmed_read=True))

    def test_expiry_during_verification_does_not_refresh(self):
        runtime = self.ready("instagram")
        self.now[0] += 60 * adapter.DAY - 1
        self.http.replies = self.reads("instagram")
        original = self.http.request
        def slow(*args, **kwargs):
            result = original(*args, **kwargs)
            self.now[0] += 2
            return result
        with mock.patch.object(self.http, "request", side_effect=slow):
            self.kind("reauth_required", lambda: runtime.access(confirmed_read=True, allow_refresh=True))
        self.assertEqual(len(self.http.calls), 1)

    def test_unknown_refresh_is_not_retried_even_with_resume(self):
        runtime = self.ready("threads")
        self.now[0] += 54 * adapter.DAY
        self.http.replies = self.reads("threads") + [OAuthError("remote_result_unknown")]
        self.kind("remote_result_unknown", lambda: runtime.access(confirmed_read=True, allow_refresh=True))
        count = len(self.http.calls)
        self.kind("recovery_required", lambda: runtime.access(confirmed_read=True, allow_refresh=True, resume=True))
        self.assertEqual(len(self.http.calls), count)

    def test_revoked_permission_stops_before_refresh(self):
        runtime = self.ready("threads")
        self.now[0] += 54 * adapter.DAY
        self.http.replies = [{"data": {"user_id": "456", "scopes": ["threads_basic"]}}]
        self.kind("permission_mismatch", lambda: runtime.access(confirmed_read=True, allow_refresh=True))
        self.assertEqual(len(self.http.calls), 1)

    def test_refresh_readback_mismatch_never_falls_back_to_old_token(self):
        runtime = self.ready("instagram")
        self.now[0] += 54 * adapter.DAY
        self.http.replies = self.reads("instagram") + [long_token("fictional-new")] + self.reads("instagram")
        self.http.replies[-1]["user_id"] = "999"
        self.kind("target_mismatch", lambda: runtime.access(confirmed_read=True, allow_refresh=True))
        self.assertEqual(runtime._bundle()["access_token"], "fictional-new")
        self.assertNotEqual(runtime.status()["status"], "ready")

    def test_no_read_authority_never_contacts_platform(self):
        runtime = self.ready("threads")
        self.kind("authorization_required", lambda: runtime.access(allow_refresh=True))
        self.assertFalse(self.http.calls)

    def test_invalid_state_and_cancellation_never_exchange(self):
        for platform in sorted(adapter.PLATFORMS):
            for cancelled in (False, True):
                runtime = self.runtime(platform)
                session = self.session(runtime)
                query = {"state": session.state, "error": "access_denied"} if cancelled else {"state": "wrong", "code": "fictional"}
                self.kind("cancelled" if cancelled else "invalid_callback",
                          lambda: session.accept("/oauth/callback?" + urlencode(query)))
                self.assertFalse(self.http.calls)

    def test_ambiguous_response_rejected(self):
        for payload in ({"data": []}, {"data": [{}, {}]}, {"data": [{}], "access_token": "fictional"}):
            self.kind("read_failed", lambda: adapter.single(payload))

    def test_cli_preview_has_no_native_or_network_access(self):
        for platform in sorted(adapter.PLATFORMS):
            value = config(platform)
            args = ["oauth_callback.py", "preview", "--workspace-root", str(self.workspace)]
            for key in ("platform", "client_id", "target_id", "graph_version", "redirect_uri", "callback_port", "callback_mode"):
                args.extend(["--" + key.replace("_", "-"), str(value[key])])
            for scope in value["scopes"]:
                args.extend(["--scope", scope])
            output = io.StringIO()
            with mock.patch.object(sys, "argv", args), contextlib.redirect_stdout(output):
                self.assertEqual(callback.main(), 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["platform"], platform)
            self.assertEqual(len(payload["preview_digest"]), 64)
            self.assertNotIn("callback.example.test", output.getvalue())
            self.assertFalse(self.backend.values)

    def test_saving_interruption_resumes_readback_without_exchange(self):
        runtime = self.ready("instagram")
        runtime.mark("storage_incomplete")
        self.http.replies = self.reads("instagram")
        self.assertEqual(runtime.access(confirmed_read=True, resume=True), "fictional-long")
        self.assertEqual(len(self.http.calls), 1)
        self.assertFalse(self.http.calls[0][2].get("mutation"))

    def test_state_schema_includes_new_routes(self):
        schema = json.loads((Path(callback.__file__).parent.parent / "references/oauth-state.schema.json").read_text())
        self.assertEqual(set(schema["properties"]["platform"]["enum"]), {"facebook", "youtube", "instagram", "threads"})

    def test_official_error_is_sanitized(self):
        self.kind("reauth_required", lambda: classify_response(400, {"error_type": "OAuthException", "code": 190,
                                                                    "error_message": "fictional-secret"}, True))

    def test_http_multipart_and_no_redirect_or_foreign_endpoint(self):
        connection = mock.Mock()
        response = connection.getresponse.return_value
        response.status = 200
        response.read.return_value = b'{"access_token":"fictional"}'
        with mock.patch("http.client.HTTPSConnection", return_value=connection) as factory:
            OfficialHTTP().request("POST", "https://api.instagram.com/oauth/access_token",
                                   form={"code": "fictional-code"}, multipart=True, mutation=True)
            sent = connection.request.call_args.kwargs
            self.assertIn("multipart/form-data; boundary=", sent["headers"]["Content-Type"])
            self.assertIn(b'name="code"\r\n\r\nfictional-code', sent["body"])
            response.status = 302
            self.kind("remote_result_unknown", lambda: OfficialHTTP().request("GET", "https://graph.threads.net/access_token", mutation=True))
            self.assertEqual(factory.call_count, 2)
            for endpoint in ("https://untrusted.example.test/access_token", "https://graph.instagram.com/v25.0/media_publish",
                             "https://graph.facebook.com/oauth/access_token", "https://graph.threads.net/me/permissions",
                             "https://graph.instagram.com/v25.0/me/permissions"):
                self.kind("invalid_configuration", lambda: OfficialHTTP().request("GET", endpoint))
            self.assertEqual(factory.call_count, 2)


if __name__ == "__main__":
    unittest.main()
