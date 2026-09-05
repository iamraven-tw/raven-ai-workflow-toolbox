"""只對固定官方主機送出 HTTPS；不記錄秘密、不跟隨重新導向、不重試。"""

import http.client
import json
import re
import ssl
from urllib.parse import urlencode, urlsplit


class OAuthError(RuntimeError):
    """只攜帶固定狀態碼，禁止把平台原始訊息帶入日誌。"""

    def __init__(self, kind):
        allowed = {"invalid_configuration", "authorization_required", "reauth_required",
                   "permission_mismatch", "target_mismatch", "expired", "invalid_callback",
                   "cancelled", "timeout", "replay", "read_failed", "rate_limited",
                   "remote_result_unknown", "storage_incomplete", "recovery_required",
                   "refresh_required", "not_configured"}
        self.kind = kind if kind in allowed else "read_failed"
        super().__init__(self.kind)


def classify_response(status, payload, mutation=False):
    """辨識已知拒絕與不明結果；不回傳錯誤本文、URL 或標頭。"""

    error = payload.get("error") if isinstance(payload, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    details = error.get("errors", []) if isinstance(error, dict) else []
    reasons = {item.get("reason") for item in details if isinstance(item, dict) and isinstance(item.get("reason"), str)} if isinstance(details, list) else set()
    # 同樣是 403，YouTube 配額用盡不能誤判成需要擴權。
    if "quotaExceeded" in reasons:
        raise OAuthError("rate_limited")
    if reasons & {"youtubeSignupRequired", "authenticatedUserNotChannel", "channelNotFound", "channelClosed", "channelSuspended"}:
        raise OAuthError("target_mismatch")
    if status == 401 or error == "invalid_grant" or code in {102, 190}:
        raise OAuthError("reauth_required")
    if status == 429:
        raise OAuthError("rate_limited")
    if status == 403 or code in {10, 200}:
        raise OAuthError("permission_mismatch")
    if not 200 <= status < 300 or error:
        raise OAuthError("remote_result_unknown" if mutation else "read_failed")
    if not isinstance(payload, dict):
        raise OAuthError("remote_result_unknown" if mutation else "read_failed")
    return payload


class OfficialHTTP:
    """不用系統代理或通用 URL；呼叫方無法把秘密轉送到任意主機。"""

    def request(self, method, endpoint, *, query=None, form=None, bearer=None, mutation=False):
        """每次只送一次，限制回應大小並保持 TLS 驗證。"""
        url = urlsplit(endpoint)
        allowed = (
            url.netloc == "oauth2.googleapis.com" and url.path in {"/token", "/tokeninfo"}
            or url.netloc == "www.googleapis.com" and url.path == "/youtube/v3/channels"
            or url.netloc == "graph.facebook.com" and re.fullmatch(
                r"/v[0-9]+\.0/(oauth/access_token|debug_token|me/accounts|me/permissions|me|[0-9]+)", url.path)
        )
        if (url.scheme != "https" or url.query or url.fragment or not allowed
                or method not in {"GET", "POST"} or (form is not None and method != "POST")):
            raise OAuthError("invalid_configuration")
        path = url.path + ("?" + urlencode(query) if query else "")
        headers = {"Accept": "application/json", "Cache-Control": "no-store"}
        body = None
        if form is not None:
            body = urlencode(form).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if bearer:
            headers["Authorization"] = "Bearer " + bearer
        connection = http.client.HTTPSConnection(url.hostname, timeout=20, context=ssl.create_default_context())
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("response limit")
            # 重新導向也當錯誤；絕不帶憑證跟隨 Location。
            try:
                payload = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                payload = None
            return classify_response(response.status, payload, mutation)
        except OAuthError:
            raise
        except Exception:
            raise OAuthError("remote_result_unknown" if mutation else "read_failed") from None
        finally:
            connection.close()
