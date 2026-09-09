"""虛構原生庫及本機 HTTP 測試；不碰真實秘密、登入或平台。"""

import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode

from test_credential_store import CREDENTIAL_STORE as vault, FakeBackend

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/social-media-setup/scripts"))
sys.modules["credential_store"] = vault
import credential_browser as bridge


class BrowserCredentialTests(unittest.TestCase):
    """保存一次、來源邊界、既有值與秘密不外流是驗收核心。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-browser-import-")
        self.addCleanup(self.temp.cleanup)
        self.workspace, self.backend = Path(self.temp.name), FakeBackend()
        self.origin = "https://credential-example.test:54443"

    def session(self, **kwargs):
        return bridge.ImportSession(self.workspace, "threads", "app-secret", self.origin,
                                    confirmed=True, backend=self.backend, **kwargs)

    def body(self, session, **kwargs):
        return urlencode({"csrf": session.csrf, "secret": "fictional-secret", **kwargs}).encode()

    def test_roundtrip_once_no_secret_in_files_or_page(self):
        session = self.session()
        self.assertIn("type='password'", session.form())
        session.accept(self.body(session), self.origin)
        self.assertEqual(session.status, "verified")
        self.assertEqual(vault.load_secret(self.workspace, "threads", "app-secret", backend=self.backend),
                         "fictional-secret")
        with self.assertRaises(ValueError):
            session.accept(self.body(session), self.origin)
        for path in self.workspace.rglob("*.json"):
            self.assertNotIn("fictional-secret", path.read_text())
        self.assertNotIn("fictional-secret", session.form())

    def test_existing_secret_refused_before_collecting(self):
        session = self.session()
        session.accept(self.body(session), self.origin)
        with self.assertRaises(vault.CredentialStoreError):
            self.session()

    def test_invalid_origin_csrf_and_duplicate_fields_do_not_write(self):
        session = self.session()
        for body, origin in [(self.body(session), "https://other.example"),
                             (self.body(session, csrf="wrong"), self.origin),
                             (self.body(session) + b"&secret=duplicate", self.origin)]:
            with self.subTest(origin=origin, duplicate=b"duplicate" in body):
                with self.assertRaises(ValueError):
                    session.accept(body, origin)
                self.assertFalse(session.consumed)
        self.assertEqual(vault.credential_status(self.workspace, backend=self.backend)["entries"], [])

    def test_expired_and_unapproved_do_not_write(self):
        now = [10]
        session = self.session(clock=lambda: now[0])
        now[0] += 901
        with self.assertRaises(ValueError):
            session.accept(self.body(session), self.origin)
        with self.assertRaises(vault.CredentialStoreError):
            bridge.ImportSession(self.workspace, "threads", "app-secret", self.origin, backend=self.backend)

    def test_bad_secret_consumes_attempt_without_echo(self):
        session = self.session()
        with self.assertRaises(vault.CredentialStoreError):
            session.accept(self.body(session, secret=""), self.origin)
        self.assertTrue(session.consumed)
        self.assertEqual(session.status, "storage_incomplete")

    def test_handler_rejects_cross_origin_and_redirects_after_verified(self):
        session = self.session()
        with bridge.CallbackServer(("127.0.0.1", 0), bridge.Handler) as server:
            server.session, server.finished = session, False
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                def request(method, path, body=None, **overrides):
                    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
                    headers = {"Host": session.host, "Origin": self.origin,
                               "Content-Type": "application/x-www-form-urlencoded", **overrides}
                    connection.request(method, path, body=body, headers=headers)
                    response = connection.getresponse()
                    result = response.status, dict(response.getheaders()), response.read()
                    connection.close()
                    return result
                bad = request("POST", session.path, self.body(session), Origin="https://other.example")
                self.assertEqual(bad[0], 400)
                self.assertFalse(session.consumed)
                self.assertEqual(request("GET", session.path, Host="other.example")[0], 400)
                result = request("POST", session.path, self.body(session))
                self.assertEqual(result[0], 303)
                self.assertEqual(result[1]["Location"], "/credential/complete")
                self.assertEqual(result[1]["Cache-Control"], "no-store")
                self.assertNotIn(b"fictional-secret", result[2])
                self.assertEqual(request("GET", "/credential/complete")[2], b"verified")
                self.assertEqual(request("POST", session.path, self.body(session))[0], 400)
            finally:
                server.shutdown()
                worker.join()


if __name__ == "__main__":
    unittest.main()
