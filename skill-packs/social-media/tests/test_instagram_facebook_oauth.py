"""Instagram via Facebook Login 的虛構 OAuth 測試，不碰帳號或網路。"""

import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlencode, urlsplit

from test_oauth_runtime import MemoryVault, Transport, vault, callback
from oauth_http import OAuthError
from oauth_runtime import Runtime, validate_config
import instagram_facebook_oauth as adapter


SCOPES = ["pages_show_list", "pages_read_engagement", "instagram_basic",
          "instagram_content_publish", "instagram_manage_comments",
          "instagram_manage_insights", "instagram_manage_messages", "pages_manage_metadata"]


def config(**changes):
    """中性虛構設定；目標是 IG ID，不是相連 Page ID。"""
    value = {"platform": "instagram", "login_route": adapter.LOGIN_ROUTE,
             "client_id": "123", "target_id": "456", "scopes": list(SCOPES),
             "secret_ref": "app-secret", "graph_version": "v25.0",
             "redirect_uri": "https://callback.example.test/oauth/callback",
             "callback_port": 8123, "callback_mode": "https_proxy",
             "tls_cert": "", "tls_key": ""}
    value.update(changes)
    return value


def debug(kind, *, user_id=None, scopes=None, expires_at=90000, valid=True):
    """模擬 Meta debugger 的安全必要欄位。"""
    data = {"is_valid": valid, "app_id": "123", "type": kind,
            "expires_at": expires_at}
    if user_id is not None:
        data["user_id"] = user_id
    if scopes is not None:
        data["scopes"] = scopes
    return {"data": data}


def page(page_id="321", ig_id="456", token="fictional-page", tasks=None):
    """模擬 /me/accounts 中的單一相連 Page。"""
    return {"id": page_id, "name": "Fictional page", "access_token": token,
            "tasks": ["ANALYZE", "CREATE_CONTENT", "MODERATE"] if tasks is None else tasks,
            "instagram_business_account": {"id": ig_id}}


class InstagramFacebookOAuthTests(unittest.TestCase):
    """路線選擇、交換、Page／IG 綁定、保存及每次讀回。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-ig-facebook-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.backend, self.http, self.now, self.counter = MemoryVault(), Transport(), [1000], 0
        native = mock.patch.object(vault, "detect_backend", side_effect=AssertionError("no native access"))
        native.start()
        self.addCleanup(native.stop)
        network = mock.patch("http.client.HTTPSConnection", side_effect=AssertionError("no network"))
        network.start()
        self.addCleanup(network.stop)

    def runtime(self, value=None):
        self.counter += 1
        workspace = self.root / f"case-{self.counter}"
        workspace.mkdir()
        runtime = Runtime(workspace, "instagram", backend=self.backend,
                          transport=self.http, clock=lambda: self.now[0])
        vault.store_secret(workspace, "instagram", "app-secret", "fictional-secret",
                           source="interactive-terminal", backend=self.backend)
        runtime.configure(value or config(), confirmed=True)
        return runtime

    def replies(self, *, pages=None):
        expected = SCOPES + ["public_profile"]
        return [
            {"access_token": "fictional-short"},
            debug("USER", user_id="789"),
            {"access_token": "fictional-long"},
            debug("USER", user_id="789"),
            {"data": [{"permission": item, "status": "granted"} for item in expected]},
            {"data": pages if pages is not None else [page()]},
            debug("PAGE", scopes=expected, expires_at=0),
            {"id": "321", "name": "Fictional page",
             "instagram_business_account": {"id": "456"}},
            {"id": "456", "username": "fictional_ig"},
        ]

    def session(self, runtime):
        return callback.CallbackSession(runtime, config()["redirect_uri"], confirmed=True)

    def finish(self, runtime):
        session = self.session(runtime)
        return session.accept("/oauth/callback?" + urlencode({
            "state": session.state, "code": "fictional-code"}))

    def kind(self, expected, action):
        with self.assertRaises(OAuthError) as caught:
            action()
        self.assertEqual(caught.exception.kind, expected)

    def ready(self):
        runtime = self.runtime()
        self.http.replies = self.replies()
        self.assertEqual(self.finish(runtime)["status"], "ready")
        self.assertFalse(self.http.replies)
        self.http.calls.clear()
        return runtime

    def access_replies(self):
        return self.replies()[-3:]

    def test_route_is_explicit_and_old_instagram_config_keeps_direct_default(self):
        self.assertEqual(validate_config(config())["login_route"], adapter.LOGIN_ROUTE)
        direct = config()
        direct.pop("login_route")
        direct["scopes"] = ["instagram_business_basic"]
        self.assertEqual(validate_config(direct)["login_route"], "instagram_login")

    def test_wrong_route_and_mixed_permissions_fail_closed(self):
        cases = [
            config(login_route="facebook_pages"),
            config(scopes=[scope for scope in SCOPES if scope != "pages_show_list"]),
            config(scopes=[scope for scope in SCOPES if scope != "pages_read_engagement"]),
            config(scopes=[scope for scope in SCOPES if scope != "instagram_basic"]),
            config(scopes=SCOPES + ["instagram_business_basic"]),
            config(scopes=SCOPES + ["youtube.readonly"]),
        ]
        for value in cases:
            with self.subTest(value=value):
                self.kind("invalid_configuration", lambda: validate_config(value))

    def test_authorization_uses_facebook_not_instagram(self):
        session = self.session(self.runtime())
        uri = urlsplit(session.authorization_url())
        self.assertEqual(uri.hostname, "www.facebook.com")
        self.assertEqual(uri.path, "/v25.0/dialog/oauth")
        query = parse_qs(uri.query)
        self.assertEqual(query["scope"], [",".join(SCOPES)])
        self.assertNotIn("client_secret", query)

    def test_exchange_selects_linked_page_and_persists_only_page_token(self):
        runtime = self.runtime()
        self.http.replies = self.replies(pages=[page("999", "111", "fictional-other"), page()])
        self.finish(runtime)
        self.assertEqual(runtime._bundle(), {
            "platform": "instagram", "login_route": adapter.LOGIN_ROUTE,
            "access_token": "fictional-page", "page_id": "321",
            "facebook_user_id": "789"})
        self.assertEqual(self.http.calls[5][2]["query"]["fields"],
                         "id,name,access_token,tasks,instagram_business_account")
        self.assertEqual(self.http.calls[1][2]["query"]["input_token"], "fictional-short")
        self.assertEqual(self.http.calls[2][2]["query"]["grant_type"], "fb_exchange_token")
        stored = " ".join(self.backend.values.values())
        for discarded in ("fictional-short", "fictional-long", "fictional-other"):
            self.assertNotIn(discarded, stored)

    def test_each_access_rechecks_page_and_instagram_without_mutation(self):
        runtime = self.ready()
        self.http.replies = self.access_replies()
        self.assertEqual(runtime.access(confirmed_read=True, allow_refresh=True), "fictional-page")
        self.assertEqual([urlsplit(call[1]).path for call in self.http.calls],
                         ["/v25.0/debug_token", "/v25.0/321", "/v25.0/456"])
        self.assertTrue(all(not call[2].get("mutation") for call in self.http.calls))

    def test_resource_context_exposes_page_id_only_after_ready_and_confirmation(self):
        runtime = self.ready()
        self.kind("authorization_required", lambda: runtime.resource_context())
        context = runtime.resource_context(confirmed_read=True)
        self.assertEqual(context, {
            "platform": "instagram", "login_route": adapter.LOGIN_ROUTE,
            "target_id": "456", "graph_version": "v25.0", "page_id": "321",
        })
        self.assertNotIn("access_token", context)
        self.assertFalse(self.http.calls)

    def test_scope_check_allows_declined_unrequested_history(self):
        runtime = self.runtime()
        replies = self.replies()
        replies[4]["data"].append({"permission": "ads_management", "status": "declined"})
        self.http.replies = replies
        self.assertEqual(self.finish(runtime)["status"], "ready")

    def test_missing_extra_or_duplicate_granted_scope_stops_before_page_discovery(self):
        for mutate, expected in (
            (lambda rows: rows.pop(), "permission_mismatch"),
            (lambda rows: rows.append({"permission": "ads_management", "status": "granted"}), "permission_mismatch"),
            (lambda rows: rows.append(copy.deepcopy(rows[0])), "read_failed"),
            (lambda rows: rows.append({"permission": "unused", "status": "unknown"}), "read_failed"),
        ):
            runtime = self.runtime()
            replies = self.replies()
            mutate(replies[4]["data"])
            self.http.replies = replies
            self.kind(expected, lambda: self.finish(runtime))
            self.assertEqual(len(self.http.calls), 5)
            self.http.calls.clear()

    def test_short_and_long_user_must_match(self):
        runtime = self.runtime()
        self.http.replies = self.replies()
        self.http.replies[3]["data"]["user_id"] = "999"
        self.kind("target_mismatch", lambda: self.finish(runtime))
        self.assertEqual(len(self.http.calls), 4)

    def test_linked_page_must_be_unique(self):
        for pages in ([], [page(), page("654")]):
            runtime = self.runtime()
            self.http.replies = self.replies(pages=pages)
            self.kind("target_mismatch", lambda: self.finish(runtime))
            self.assertEqual(len(self.http.calls), 6)
            self.http.calls.clear()

    def test_page_requires_name_token_tasks_and_link(self):
        cases = [
            page(token=""),
            page(tasks=[]),
            page(ig_id="999"),
            page() | {"name": ""},
            page() | {"id": "bad"},
            page() | {"instagram_business_account": "456"},
        ]
        for candidate in cases:
            runtime = self.runtime()
            self.http.replies = self.replies(pages=[candidate])
            self.kind("target_mismatch", lambda: self.finish(runtime))
            self.http.calls.clear()

    def test_page_debug_rejects_revocation_wrong_app_type_scope_and_expiry(self):
        cases = [
            ({"is_valid": False}, "reauth_required"),
            ({"app_id": "999"}, "target_mismatch"),
            ({"type": "USER"}, "target_mismatch"),
            ({"scopes": ["pages_show_list"]}, "permission_mismatch"),
            ({"expires_at": self.now[0]}, "expired"),
        ]
        for changed, expected in cases:
            runtime = self.runtime()
            replies = self.replies()
            replies[6]["data"].update(changed)
            self.http.replies = replies
            self.kind(expected, lambda: self.finish(runtime))
            self.assertNotEqual(runtime.status()["status"], "ready")
            self.http.calls.clear()

    def test_page_or_instagram_readback_mismatch_stops(self):
        cases = [(7, {"id": "999"}), (7, {"instagram_business_account": {"id": "999"}}),
                 (8, {"id": "999"}), (8, {"username": ""})]
        for index, changed in cases:
            runtime = self.runtime()
            self.http.replies = self.replies()
            self.http.replies[index].update(changed)
            self.kind("target_mismatch", lambda: self.finish(runtime))
            self.http.calls.clear()

    def test_invalid_state_and_cancel_never_exchange(self):
        for query, expected in (({"state": "wrong", "code": "fictional"}, "invalid_callback"),
                                ({"error": "access_denied"}, "cancelled")):
            runtime = self.runtime()
            session = self.session(runtime)
            if "state" not in query:
                query["state"] = session.state
            self.kind(expected, lambda: session.accept("/oauth/callback?" + urlencode(query)))
            self.assertFalse(self.http.calls)

    def test_unknown_exchange_does_not_retry(self):
        runtime = self.runtime()
        self.http.replies = [OAuthError("remote_result_unknown")]
        self.kind("remote_result_unknown", lambda: self.finish(runtime))
        count = len(self.http.calls)
        self.kind("recovery_required", lambda: runtime.access(
            confirmed_read=True, allow_refresh=True, resume=True))
        self.assertEqual(len(self.http.calls), count)

    def test_access_requires_read_authority(self):
        runtime = self.ready()
        self.kind("authorization_required", lambda: runtime.access(allow_refresh=True))
        self.assertFalse(self.http.calls)

    def test_tampered_bundle_route_or_ids_never_contacts_platform(self):
        for changed in ({"login_route": "instagram_login"}, {"page_id": "bad"},
                        {"facebook_user_id": "bad"}, {"access_token": ""}):
            runtime = self.ready()
            bundle = runtime._bundle() | changed
            runtime._save_bundle(bundle)
            runtime.mark("ready")
            self.kind("storage_incomplete" if changed == {"access_token": ""} else "target_mismatch",
                      lambda: runtime.access(confirmed_read=True))
            self.assertFalse(self.http.calls)

    def test_cli_preview_includes_route_but_not_private_ids(self):
        value = config()
        args = ["oauth_callback.py", "preview", "--workspace-root", str(self.root),
                "--platform", "instagram", "--login-route", adapter.LOGIN_ROUTE,
                "--client-id", value["client_id"], "--target-id", value["target_id"],
                "--graph-version", value["graph_version"], "--redirect-uri", value["redirect_uri"],
                "--callback-port", str(value["callback_port"]), "--callback-mode", value["callback_mode"]]
        for scope in value["scopes"]:
            args.extend(["--scope", scope])
        output = io.StringIO()
        with mock.patch.object(sys, "argv", args), contextlib.redirect_stdout(output):
            self.assertEqual(callback.main(), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["login_route"], adapter.LOGIN_ROUTE)
        self.assertNotIn(value["target_id"], output.getvalue())
        self.assertNotIn(value["redirect_uri"], output.getvalue())


if __name__ == "__main__":
    unittest.main()
