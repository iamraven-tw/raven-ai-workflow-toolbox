#!/usr/bin/env python3
"""短期本機 OAuth 回呼與 Agent CLI，不接收命令列秘密或自動同意登入。"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import re
import secrets
import ssl
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import TCPServer
from urllib.parse import parse_qs, urlencode, urlsplit

import credential_store as vault
from oauth_http import OAuthError
from oauth_runtime import Runtime, validate_config, ROUTES
from meta_user_oauth import AUTH_URLS


class CallbackSession:
    """state、PKCE、授權碼僅在記憶體；重啟建立新流程，不重用舊授權碼。"""

    def __init__(self, runtime, redirect_uri, *, confirmed=False, restart=False, clock=time.monotonic):
        if not confirmed:
            raise OAuthError("authorization_required")
        self.runtime, self.redirect_uri, self.clock = runtime, redirect_uri, clock
        self.config = runtime.config()
        if self.config["callback_mode"] == "token_import":
            raise OAuthError("invalid_configuration")
        # 在開啟授權畫面前確認秘密可讀，不把值留在物件或輸出。
        if not runtime._load(self.config["secret_ref"]):
            raise OAuthError("not_configured")
        self.state = secrets.token_urlsafe(32)
        self.verifier = secrets.token_urlsafe(48)
        self.launch_key = secrets.token_urlsafe(32)
        self.attempt = secrets.token_hex(8)
        self.deadline = clock() + 900
        self.consumed, self.launched = False, False
        uri = urlsplit(redirect_uri)
        if self.config["platform"] == "youtube":
            if (uri.scheme != "http" or uri.hostname != "127.0.0.1" or not uri.port
                    or uri.path != "/oauth/callback" or uri.query or uri.fragment or uri.username):
                raise OAuthError("invalid_configuration")
        elif redirect_uri != self.config["redirect_uri"]:
            raise OAuthError("invalid_configuration")
        with runtime.lock():
            if runtime.status()["status"] != "configured" and not restart:
                raise OAuthError("recovery_required")
            runtime.mark("authorizing", attempt=self.attempt)

    def authorization_url(self):
        """只交給 HTTP Location；呼叫方不得列印含私人 client ID 的 URL。"""
        if self.launched or self.consumed or self.clock() >= self.deadline:
            raise OAuthError("replay")
        self.launched = True
        params = {"client_id": self.config["client_id"], "response_type": "code",
                  "redirect_uri": self.redirect_uri, "state": self.state}
        if self.config["platform"] == "youtube":
            params.update(scope=" ".join(self.config["scopes"]),
                code_challenge=base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).decode().rstrip("="),
                code_challenge_method="S256", access_type="offline")
            endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        elif (self.config["platform"] in AUTH_URLS
              and self.config["login_route"] != "instagram_facebook_login"):
            params["scope"] = ",".join(self.config["scopes"])
            endpoint = AUTH_URLS[self.config["platform"]]
        else:
            params["scope"] = ",".join(self.config["scopes"])
            endpoint = f"https://www.facebook.com/{self.config['graph_version']}/dialog/oauth"
        return endpoint + "?" + urlencode(params)

    def accept(self, request_target):
        """一次性驗證回呼；所有驗證都在交換授權碼之前。"""
        with self.runtime.lock():
            current = self.runtime.status()
            if (self.consumed or current["attempt"] != self.attempt
                    or current["status"] != "authorizing"):
                raise OAuthError("replay")
            try:
                if self.clock() >= self.deadline:
                    raise OAuthError("timeout")
                uri = urlsplit(request_target)
                if uri.scheme or uri.netloc or uri.fragment or uri.path != "/oauth/callback" or len(uri.query) > 16384:
                    raise OAuthError("invalid_callback")
                try:
                    values = parse_qs(uri.query, keep_blank_values=True, strict_parsing=True, max_num_fields=16)
                except ValueError:
                    raise OAuthError("invalid_callback") from None
                if any(len(v) != 1 for v in values.values()):
                    raise OAuthError("invalid_callback")
                supplied = values.get("state", [""])[0]
                if not hmac.compare_digest(supplied.encode(), self.state.encode()):
                    raise OAuthError("invalid_callback")
                if "error" in values:
                    raise OAuthError("cancelled")
                if "iss" in values and (self.config["platform"] != "youtube"
                                       or values["iss"] != ["https://accounts.google.com"]):
                    raise OAuthError("invalid_callback")
                code = values.get("code", [""])[0]
                if not code or len(code) > 8192 or any(ord(c) < 32 for c in code):
                    raise OAuthError("invalid_callback")
                self.consumed = True
                return self.runtime.complete(code, self.redirect_uri, self.verifier)
            except OAuthError as error:
                self.consumed = True
                if self.runtime.status()["status"] == "authorizing":
                    self.runtime.mark(error.kind)
                raise
            finally:
                if self.consumed:
                    self.state = self.verifier = ""


class CallbackServer(HTTPServer):
    """單使用者短期伺服器；關閉錯誤 traceback 避免輸出請求內容。"""
    def server_bind(self):
        """固定 loopback 名稱，不觸發不必要的反向 DNS 查詢。"""
        TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]

    def get_request(self):
        """限制每個連線等待時間，防止單一慢連線永久占用接收器。"""
        connection, address = super().get_request()
        connection.settimeout(2)
        if getattr(self, "tls_context", None):
            try:
                connection = self.tls_context.wrap_socket(connection, server_side=True)
            except Exception:
                connection.close()
                raise OSError("TLS connection rejected") from None
        return connection, address

    def handle_error(self, request, client_address):
        """不將請求路徑或例外內容印出。"""
        pass


class Handler(BaseHTTPRequestHandler):
    """不記錄 query、不載入外部資源、不回顯平台錯誤。"""
    def log_message(self, *args):
        """停用標準 access log，避免 callback 授權碼進入日誌。"""
        pass

    def send_error(self, code, message=None, explain=None):
        """連 HTTP 語法錯誤也只回固定訊息，不回顯原始請求行。"""
        self.reply(code)

    def reply(self, status, location=None):
        """固定文字與安全標頭；不把原始 callback 寫進 HTML。"""
        body = "OAuth 步驟已處理，請返回 AI Agent 查看結果。".encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        if location:
            self.send_header("Location", location)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        """只接受預期 Host、啟動路徑與 callback；忽略外來 proxy 標頭。"""
        session = self.server.session
        hosts = self.headers.get_all("Host", [])
        if len(hosts) != 1 or hosts[0] not in self.server.allowed_hosts:
            self.reply(400)
            return
        try:
            if self.path == "/start/" + session.launch_key:
                self.reply(302, session.authorization_url())
            elif self.path == "/oauth/complete":
                self.reply(200)
                if session.consumed:
                    self.server.finished = True
            elif urlsplit(self.path).path == "/oauth/callback":
                if hosts[0] != urlsplit(session.redirect_uri).netloc:
                    raise OAuthError("invalid_callback")
                try:
                    session.accept(self.path)
                except OAuthError:
                    pass
                finally:
                    # 不論成功或拒絕，都導向不含授權碼的本機結果頁。
                    self.reply(303, "/oauth/complete")
                    self.server.finish_deadline = time.monotonic() + 5
            else:
                self.reply(404)
        except OAuthError:
            self.reply(400)


def serve(runtime, *, confirmed=False, restart=False, https_proxy_confirmed=False, notify=print):
    """啟動接收器但不自行操作瀏覽器；Agent 只開啟回傳的本機啟動網址。"""
    if not confirmed:
        raise OAuthError("authorization_required")
    config = runtime.config()
    if config["callback_mode"] == "token_import":
        raise OAuthError("invalid_configuration")
    if config["callback_mode"] == "https_proxy" and not https_proxy_confirmed:
        raise OAuthError("authorization_required")
    context = None
    if config["callback_mode"] == "https_local":
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(config["tls_cert"], config["tls_key"])
    # 所有模式只綁 loopback；公開 HTTPS 入口必須由使用者既有受控反向代理提供。
    with CallbackServer(("127.0.0.1", config["callback_port"]), Handler) as server:
        server.tls_context = context
        local_origin = f"http://127.0.0.1:{server.server_port}"
        redirect = (local_origin + "/oauth/callback") if runtime.platform == "youtube" else config["redirect_uri"]
        session = CallbackSession(runtime, redirect, confirmed=True, restart=restart)
        server.session, server.finished, server.finish_deadline = session, False, float("inf")
        server.timeout = 0.5
        server.allowed_hosts = {urlsplit(redirect).netloc, f"127.0.0.1:{server.server_port}"}
        origin = ("https://" + urlsplit(redirect).netloc) if context else local_origin
        notify(json.dumps({"status": "waiting_for_consent", "launch_url": origin + "/start/" + session.launch_key,
                           "contains_credentials": False}), flush=True)
        try:
            while not server.finished and time.monotonic() < min(session.deadline, server.finish_deadline):
                server.handle_request()
            if not session.consumed:
                with runtime.lock():
                    if runtime.status()["attempt"] == session.attempt:
                        runtime.mark("timeout")
        except KeyboardInterrupt:
            with runtime.lock():
                if runtime.status()["status"] == "authorizing" and runtime.status()["attempt"] == session.attempt:
                    runtime.mark("cancelled")
            raise OAuthError("cancelled") from None
    return runtime.status()


class SafeParser(argparse.ArgumentParser):
    """即使誤傳秘密參數，也不把參數值回顯到錯誤輸出。"""
    def error(self, message):
        self.exit(2, '{"status":"invalid_arguments","contains_credentials":false}\n')


def main():
    """不接受 --code／--token／client secret，輸出永遠不包含 Token。"""
    parser = SafeParser(description="社群 OAuth 設定、接收與有效性檢查")
    parser.add_argument("command", choices=["preview", "configure", "run", "status", "check"])
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--platform", required=True, choices=sorted(ROUTES))
    parser.add_argument("--connection", default="main")
    parser.add_argument("--login-route")
    parser.add_argument("--client-id")
    parser.add_argument("--target-id")
    parser.add_argument("--scope", action="append", default=[])
    parser.add_argument("--secret-ref", default="app-secret")
    parser.add_argument("--graph-version", default="")
    parser.add_argument("--redirect-uri", default="")
    parser.add_argument("--callback-mode", choices=["loopback", "https_proxy", "https_local"], default="loopback")
    parser.add_argument("--callback-port", type=int, default=0)
    parser.add_argument("--tls-cert", default="")
    parser.add_argument("--tls-key", default="")
    parser.add_argument("--preview-digest")
    for flag in ("confirm-config", "confirm-replace", "confirm-oauth", "confirm-read",
                 "confirm-store", "confirm-restart", "confirm-https-proxy", "allow-refresh", "resume"):
        parser.add_argument("--" + flag, action="store_true")
    args = parser.parse_args()
    try:
        if args.command in {"preview", "configure"}:
            config = {key: getattr(args, key) for key in (
                "platform", "client_id", "target_id", "secret_ref", "graph_version", "redirect_uri",
                "callback_port", "callback_mode", "tls_cert", "tls_key")} | {"scopes": args.scope}
            if args.login_route:
                config["login_route"] = args.login_route
            config = validate_config(config)
            if not re.fullmatch(r"[a-z][a-z0-9-]{0,19}", args.connection):
                raise OAuthError("invalid_configuration")
            # 確認不可跨工作區或連線代稱挪用；預覽只解析路徑，不碰原生憑證。
            preview = {"configuration": config, "workspace": str(vault.resolve_workspace(args.workspace_root)),
                       "connection": args.connection}
            digest = hashlib.sha256(json.dumps(preview, sort_keys=True).encode()).hexdigest()
            if args.command == "preview":
                print(json.dumps({"platform": args.platform, "connection": args.connection,
                    "login_route": config["login_route"], "scopes": args.scope,
                    "callback_mode": args.callback_mode, "preview_digest": digest,
                    "contains_credentials": False}))
                return 0
            if args.preview_digest != digest:
                raise OAuthError("authorization_required")
        runtime = Runtime(args.workspace_root, args.platform, args.connection)
        if args.command == "configure":
            result = runtime.configure(config, confirmed=args.confirm_config, replace=args.confirm_replace)
        elif args.command == "run":
            result = serve(runtime, confirmed=args.confirm_oauth and args.confirm_read and args.confirm_store,
                           restart=args.confirm_restart, https_proxy_confirmed=args.confirm_https_proxy)
        elif args.command == "check":
            runtime.access(confirmed_read=args.confirm_read, allow_refresh=args.allow_refresh, resume=args.resume)
            result = runtime.status()
        else:
            result = runtime.status()
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["status"] in {"configured", "ready"} else 2
    except OAuthError as error:
        print(json.dumps({"status": error.kind, "contains_credentials": False}))
        return 2
    except (Exception, KeyboardInterrupt):
        print(json.dumps({"status": "stopped_check_local_state", "contains_credentials": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
