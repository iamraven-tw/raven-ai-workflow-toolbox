#!/usr/bin/env python3
"""經授權將官方畫面中的既有秘密經本機 HTTPS 表單送入原生庫；不重設秘密。"""

import argparse
import hmac
import html
import json
import re
import secrets
import ssl
import time
from urllib.parse import parse_qs, urlsplit

import credential_store as vault
from oauth_callback import CallbackServer, Handler as BaseHandler


class ImportSession:
    """先確認目標不存在再接收；單次提交、短期有效、不保留秘密內容。"""

    def __init__(self, workspace, platform, name, origin, *, confirmed=False,
                 backend=None, clock=time.monotonic):
        if not confirmed:
            raise vault.CredentialStoreError("需要已確認的保存授權")
        self.platform, self.name = vault.validate_reference(platform, name)
        self.workspace = vault.resolve_workspace(workspace)
        self.backend = backend or vault.detect_backend()
        registry = vault.ensure_registry_backend(vault.load_registry(self.workspace), self.backend)
        target = vault.target_name(registry, platform, name)
        if f"{platform}/{name}" in registry["entries"] or self.backend.exists(target):
            raise vault.CredentialStoreError("目標已存在；先查 status，不重新索取或覆寫")
        uri = urlsplit(origin)
        if (uri.scheme != "https" or not uri.hostname or uri.username or uri.password
                or uri.path or uri.query or uri.fragment or not uri.port
                or not re.fullmatch(r"[a-zA-Z0-9.-]+", uri.hostname)
                or not (uri.hostname in {"localhost", "127.0.0.1"} or uri.hostname.endswith(".test"))):
            raise vault.CredentialStoreError("需要精確本機 HTTPS origin")
        self.origin, self.host = origin, uri.netloc
        self.clock, self.deadline = clock, clock() + 900
        self.key, self.csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.consumed, self.status = False, "waiting_for_input"

    @property
    def path(self):
        """一次性路徑不包含被保存的秘密。"""
        return "/credential/" + self.key

    def form(self):
        """無腳本、外部資源、預填秘密或瀏覽器自動完成。"""
        return ("<!doctype html><meta charset='utf-8'><title>Native credential import</title>"
                f"<p>{html.escape(self.platform)} / {html.escape(self.name)}</p>"
                f"<form method='post' action='{self.path}' autocomplete='off'>"
                f"<input type='hidden' name='csrf' value='{self.csrf}'>"
                "<label>App Secret <input type='password' name='secret' autocomplete='off' required></label>"
                "<button type='submit'>Save to native credential store</button></form>")

    def accept(self, body, origin):
        """同源及 CSRF 核對先於秘密保存，失敗輸出只有固定狀態。"""
        if self.consumed or self.clock() >= self.deadline or origin != self.origin:
            raise ValueError("request_rejected")
        values = parse_qs(body.decode("utf-8"), strict_parsing=True, keep_blank_values=True,
                          max_num_fields=2)
        if (set(values) != {"csrf", "secret"} or any(len(v) != 1 for v in values.values())
                or not hmac.compare_digest(values["csrf"][0].encode(), self.csrf.encode())):
            raise ValueError("request_rejected")
        self.consumed = True
        self.status = "storage_incomplete"
        try:
            vault.store_secret(self.workspace, self.platform, self.name, values["secret"][0],
                               source="controlled-browser", backend=self.backend)
            self.status = "verified"
        finally:
            values.clear()


class Handler(BaseHandler):
    """沿用無 access log／traceback 的本機伺服器，拒絕跨站與重播。"""

    def reply(self, status, location=None, body="Credential step processed."):
        """不回顯請求內容，成功使用 303 清除表單頁與重送提示。"""
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        if location:
            self.send_header("Location", location)
        self.end_headers()
        self.wfile.write(payload)

    def valid_host(self):
        """拒絕 Host 混淆，不接受轉送標頭。"""
        return self.headers.get_all("Host", []) == [self.server.session.host]

    def do_GET(self):
        """表單僅在有效期間可讀，完成頁只呈現固定非敏感狀態。"""
        s = self.server.session
        if not self.valid_host():
            return self.reply(400)
        if self.path == "/credential/complete" and s.consumed:
            self.reply(200, body=s.status)
            self.server.finished = True
        elif self.path == s.path and not s.consumed and s.clock() < s.deadline:
            self.reply(200, body=s.form())
        else:
            self.reply(404)

    def do_POST(self):
        """只接收同源、小型、明確長度的表單；不接受 Token URL 或通用上傳。"""
        s = self.server.session
        lengths = self.headers.get_all("Content-Length", [])
        origins = self.headers.get_all("Origin", [])
        if (s.consumed or s.clock() >= s.deadline or not self.valid_host() or self.path != s.path
                or origins != [s.origin] or self.headers.get("Transfer-Encoding")
                or self.headers.get_content_type() != "application/x-www-form-urlencoded"
                or len(lengths) != 1 or not lengths[0].isdigit()
                or not 1 <= int(lengths[0]) <= 16384):
            return self.reply(400)
        try:
            body = self.rfile.read(int(lengths[0]))
            if len(body) != int(lengths[0]):
                raise ValueError("request_rejected")
            s.accept(body, origins[0])
        except Exception:
            pass
        finally:
            body = b""
        if s.consumed:
            self.server.finish_deadline = time.monotonic() + 5
            self.reply(303, "/credential/complete")
        else:
            self.reply(400)


def serve(args):
    """所有作業僅監聽 127.0.0.1；憑證信任與 hosts 必須已另行準備。"""
    session = ImportSession(args.workspace_root, args.platform, args.name, args.origin,
                            confirmed=args.confirm_store)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(args.tls_cert, args.tls_key)
    with CallbackServer(("127.0.0.1", urlsplit(args.origin).port), Handler) as server:
        server.session, server.tls_context = session, context
        server.finished, server.finish_deadline, server.timeout = False, float("inf"), 0.5
        print(json.dumps({"status": session.status, "launch_url": args.origin + session.path,
                          "platform": args.platform, "name": args.name, "contains_credentials": False}), flush=True)
        while not server.finished and time.monotonic() < min(session.deadline, server.finish_deadline):
            server.handle_request()
    return {"status": session.status if session.consumed else "timeout", "platform": args.platform,
            "name": args.name, "contains_credentials": False}


def main():
    """CLI 不接受秘密值、替換旗標或任意監聽介面。"""
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("workspace-root", "platform", "name", "origin", "tls-cert", "tls-key"):
        parser.add_argument("--" + field, required=True)
    parser.add_argument("--confirm-store", action="store_true")
    try:
        result = serve(parser.parse_args())
    except (Exception, KeyboardInterrupt):
        result = {"status": "stopped_check_registry", "contains_credentials": False}
    print(json.dumps(result))
    return 0 if result["status"] == "verified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
