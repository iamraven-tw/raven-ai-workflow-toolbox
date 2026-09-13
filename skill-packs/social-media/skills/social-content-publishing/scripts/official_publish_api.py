"""四個平台的最小官方發布 API adapter；不提供 Substack 私有端點。"""

from __future__ import annotations

import hashlib
import http.client
import importlib
import json
import mimetypes
import re
import ssl
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit


class PublishAPIError(RuntimeError):
    """只回傳固定錯誤種類，避免平台本文或憑證進入輸出。"""

    ALLOWED = {
        "authorization_required", "invalid_request", "adapter_unavailable",
        "reauth_required", "permission_mismatch", "target_mismatch",
        "rate_limited", "rejected", "read_failed", "remote_result_unknown",
        "asset_changed", "upload_incomplete",
    }

    def __init__(self, kind):
        self.kind = kind if kind in self.ALLOWED else "read_failed"
        super().__init__(self.kind)


class HTTPResult:
    """只在可信程式內保存必要回應；不自動列印。"""

    __slots__ = ("status", "payload", "headers")

    def __init__(self, status, payload, headers=None):
        self.status = status
        self.payload = payload
        self.headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}


class SensitiveUploadSession:
    """YouTube upload URL 只留在同一程序記憶體，repr 永不顯示。"""

    __slots__ = ("_url", "item_id", "preview_sha256", "target_id", "asset_sha256",
                 "size", "content_type", "connection")

    def __init__(self, url, *, item_id, preview_sha256, target_id, asset_sha256,
                 size, content_type, connection):
        self._url = url
        self.item_id = item_id
        self.preview_sha256 = preview_sha256
        self.target_id = target_id
        self.asset_sha256 = asset_sha256
        self.size = size
        self.content_type = content_type
        self.connection = connection

    def __repr__(self):
        return "SensitiveUploadSession(<redacted>)"


def _identifier(value, *, graph=False):
    """平台 ID 僅接受官方常見的十進位或 Page_post 組合。"""

    pattern = r"[0-9]+(?:_[0-9]+)?" if graph else r"[0-9]+"
    if type(value) not in (str, int) or not re.fullmatch(pattern, str(value)):
        raise PublishAPIError("invalid_request")
    return str(value)


def _youtube_resource_id(value):
    """YouTube 頻道與影片 ID 不是十進位，僅接受官方 URL 安全字元。"""

    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{6,100}", value):
        raise PublishAPIError("invalid_request")
    return value


def _plain_text(value, *, allow_empty=False, maximum=100_000):
    """拒絕控制字元與過大文字；平台精確上限仍由平台端判定。"""

    if not isinstance(value, str) or (not allow_empty and not value) or len(value) > maximum:
        raise PublishAPIError("invalid_request")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise PublishAPIError("invalid_request")
    return value


def _https_url(value):
    """媒體來源必須是沒有嵌入帳密的 HTTPS URL。"""

    if not isinstance(value, str):
        raise PublishAPIError("invalid_request")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise PublishAPIError("invalid_request")
    return value


def _form_value(value):
    """Graph API 複合欄位用精簡 JSON；布林值使用小寫字串。"""

    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if type(value) in (str, int):
        return str(value)
    raise PublishAPIError("invalid_request")


def _safe_json(payload, *, mutation):
    """成功回應必須是 JSON 物件；空回應不推定成功。"""

    if not isinstance(payload, dict):
        raise PublishAPIError("remote_result_unknown" if mutation else "read_failed")
    return payload


def _classify(status, payload, *, mutation):
    """不輸出遠端錯誤本文，且非冪等寫入錯誤不自動重送。"""

    error = payload.get("error") if isinstance(payload, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    details = error.get("errors", []) if isinstance(error, dict) else []
    reasons = {
        row.get("reason") for row in details
        if isinstance(row, dict) and isinstance(row.get("reason"), str)
    } if isinstance(details, list) else set()
    if status == 401 or code in {102, 190}:
        raise PublishAPIError("reauth_required")
    if status == 429 or "quotaExceeded" in reasons:
        raise PublishAPIError("rate_limited")
    if status == 403 or code in {10, 200}:
        raise PublishAPIError("permission_mismatch")
    if not 200 <= status < 300 or error:
        if mutation and (300 <= status < 400 or status >= 500):
            raise PublishAPIError("remote_result_unknown")
        raise PublishAPIError("rejected" if mutation else "read_failed")


class OfficialPublishHTTP:
    """只連四平台正式主機；不跟隨重新導向，也不接受任意 endpoint。"""

    MAX_RESPONSE = 2 * 1024 * 1024

    @staticmethod
    def _allowed(method, endpoint):
        parsed = urlsplit(endpoint)
        if parsed.scheme != "https" or parsed.query or parsed.fragment or parsed.username or parsed.password:
            return False
        path = parsed.path
        if parsed.netloc == "www.googleapis.com":
            return ((method == "POST" and path == "/upload/youtube/v3/videos")
                    or (method in {"GET", "PUT", "DELETE"} and path == "/youtube/v3/videos"))
        versioned = r"/v[0-9]+\.0/"
        graph_id = r"[0-9]+(?:_[0-9]+)?"
        if parsed.netloc == "graph.facebook.com":
            if method == "POST":
                return bool(re.fullmatch(versioned + graph_id + r"/(?:feed|photos|media|media_publish)", path)
                            or re.fullmatch(versioned + r"[0-9]+_[0-9]+", path))
            if method == "DELETE":
                return bool(re.fullmatch(versioned + graph_id, path))
            return method == "GET" and bool(re.fullmatch(versioned + graph_id + r"(?:/(?:feed|media))?", path))
        if parsed.netloc == "graph.instagram.com":
            if method == "POST":
                return bool(re.fullmatch(versioned + r"[0-9]+/(?:media|media_publish)", path))
            return method == "GET" and bool(re.fullmatch(versioned + r"[0-9]+", path))
        if parsed.netloc == "graph.threads.net":
            if method == "POST":
                return bool(re.fullmatch(versioned + r"me/(?:threads|threads_publish)", path))
            return method == "GET" and bool(re.fullmatch(versioned + r"(?:me/threads|[0-9]+)", path))
        if parsed.netloc == "graph.threads.com":
            return method == "DELETE" and bool(re.fullmatch(versioned + r"[0-9]+", path))
        return False

    @staticmethod
    def _session_url(endpoint):
        parsed = urlsplit(endpoint)
        query = parse_qs(parsed.query, keep_blank_values=True)
        return (parsed.scheme == "https" and parsed.netloc == "www.googleapis.com"
                and parsed.path == "/upload/youtube/v3/videos" and not parsed.fragment
                and parsed.username is None and parsed.password is None
                and query.get("uploadType") == ["resumable"]
                and len(query.get("upload_id", [])) == 1 and bool(query["upload_id"][0]))

    @staticmethod
    def _bearer(value):
        if not isinstance(value, str) or not value or "\r" in value or "\n" in value:
            raise PublishAPIError("authorization_required")
        return value

    @staticmethod
    def _endpoint_with_query(endpoint, query):
        if not query:
            return endpoint
        if any(str(key).lower() in {"access_token", "token", "authorization"} for key in query):
            raise PublishAPIError("invalid_request")
        return endpoint + "?" + urlencode({key: _form_value(value) for key, value in query.items()})

    @staticmethod
    def _payload(raw, *, allow_empty=False):
        if not raw and allow_empty:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return None

    def request_json(self, method, endpoint, *, query=None, form=None, json_body=None,
                     bearer=None, mutation=False, headers=None, allow_empty=False):
        """送出一次 JSON／表單請求；例外時不含 URL、本文或 Token。"""

        method = str(method).upper()
        if method not in {"GET", "POST", "PUT", "DELETE"} or not self._allowed(method, endpoint):
            raise PublishAPIError("invalid_request")
        if mutation is not (method != "GET") or (method == "DELETE" and (form is not None or json_body is not None)):
            raise PublishAPIError("invalid_request")
        if sum(value is not None for value in (form, json_body)) > 1:
            raise PublishAPIError("invalid_request")
        token = self._bearer(bearer)
        request_headers = {"Accept": "application/json", "Cache-Control": "no-store",
                           "Authorization": "Bearer " + token}
        for key, value in (headers or {}).items():
            if (not re.fullmatch(r"[A-Za-z0-9-]+", str(key)) or not isinstance(value, str)
                    or "\r" in value or "\n" in value or str(key).lower() == "authorization"):
                raise PublishAPIError("invalid_request")
            request_headers[str(key)] = value
        body = None
        if form is not None:
            if not isinstance(form, dict) or any(str(key).lower() in {"access_token", "token", "authorization"} for key in form):
                raise PublishAPIError("invalid_request")
            body = urlencode({key: _form_value(value) for key, value in form.items()}).encode("utf-8")
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif json_body is not None:
            if not isinstance(json_body, dict):
                raise PublishAPIError("invalid_request")
            body = json.dumps(json_body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            request_headers["Content-Type"] = "application/json; charset=UTF-8"
        if body is not None:
            request_headers["Content-Length"] = str(len(body))
        parsed = urlsplit(endpoint)
        connection = http.client.HTTPSConnection(parsed.hostname, timeout=60, context=ssl.create_default_context())
        try:
            connection.request(method, self._endpoint_with_query(parsed.path, query), body=body,
                               headers=request_headers)
            response = connection.getresponse()
            raw = response.read(self.MAX_RESPONSE + 1)
            if len(raw) > self.MAX_RESPONSE:
                raise PublishAPIError("remote_result_unknown" if mutation else "read_failed")
            payload = self._payload(raw, allow_empty=allow_empty)
            _classify(response.status, payload, mutation=mutation)
            return HTTPResult(response.status, payload, dict(response.getheaders()))
        except PublishAPIError:
            raise
        except Exception:
            raise PublishAPIError("remote_result_unknown" if mutation else "read_failed") from None
        finally:
            connection.close()

    def upload_file(self, endpoint, path, *, bearer, content_type):
        """YouTube 單次上傳目前檔案；308 只回報可續傳，不自行重送。"""

        if not self._session_url(endpoint) or not re.fullmatch(r"(?:video/[A-Za-z0-9.+-]+|application/octet-stream)", content_type):
            raise PublishAPIError("invalid_request")
        token = self._bearer(bearer)
        size = path.stat().st_size
        parsed = urlsplit(endpoint)
        connection = http.client.HTTPSConnection(parsed.hostname, timeout=300, context=ssl.create_default_context())
        try:
            connection.putrequest("PUT", parsed.path + "?" + parsed.query)
            connection.putheader("Authorization", "Bearer " + token)
            connection.putheader("Content-Type", content_type)
            connection.putheader("Content-Length", str(size))
            connection.putheader("Cache-Control", "no-store")
            connection.endheaders()
            with path.open("rb") as handle:
                while chunk := handle.read(1024 * 1024):
                    connection.send(chunk)
            response = connection.getresponse()
            raw = response.read(self.MAX_RESPONSE + 1)
            if len(raw) > self.MAX_RESPONSE:
                raise PublishAPIError("remote_result_unknown")
            payload = self._payload(raw, allow_empty=response.status == 308)
            headers = dict(response.getheaders())
            if response.status == 308:
                return HTTPResult(308, payload or {}, headers)
            _classify(response.status, payload, mutation=True)
            return HTTPResult(response.status, payload, headers)
        except PublishAPIError:
            raise
        except Exception:
            raise PublishAPIError("remote_result_unknown") from None
        finally:
            connection.close()


def _default_runtime(workspace, platform, connection):
    """從並列安裝的 setup 技能載入 Runtime，不複製秘密處理。"""

    scripts = Path(__file__).resolve().parents[2] / "social-media-setup" / "scripts"
    if not scripts.is_dir():
        raise PublishAPIError("adapter_unavailable")
    added = str(scripts) not in sys.path
    if added:
        sys.path.insert(0, str(scripts))
    try:
        module = importlib.import_module("oauth_runtime")
        return module.Runtime(workspace, platform, connection=connection)
    except PublishAPIError:
        raise
    except Exception:
        raise PublishAPIError("adapter_unavailable") from None
    finally:
        if added and sys.path and sys.path[0] == str(scripts):
            sys.path.pop(0)


class OfficialAPIAdapter:
    """在 publish_job 已 begin 後，由受信任 Agent 逐階段呼叫。"""

    GRANT_KEYS = {"item_id", "preview_sha256", "approval_ref", "platform", "target_id",
                  "transaction_status", "allow_token_refresh"}

    def __init__(self, workspace, *, connection="main", runtime_factory=None, http_transport=None):
        self.workspace = Path(workspace).expanduser().resolve()
        if not self.workspace.is_dir() or not re.fullmatch(r"[a-z][a-z0-9-]{0,19}", connection):
            raise PublishAPIError("invalid_request")
        self.connection = connection
        self.runtime_factory = runtime_factory or _default_runtime
        self.http = http_transport or OfficialPublishHTTP()

    @staticmethod
    def _grant(grant, platform, target_id):
        if not isinstance(grant, dict) or set(grant) != OfficialAPIAdapter.GRANT_KEYS:
            raise PublishAPIError("authorization_required")
        if (grant.get("platform") != platform or str(grant.get("target_id")) != str(target_id)
                or grant.get("transaction_status") != "in_progress"
                or grant.get("allow_token_refresh") not in {True, False}
                or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", str(grant.get("item_id", "")))
                or not re.fullmatch(r"[0-9a-f]{64}", str(grant.get("preview_sha256", "")))
                or not isinstance(grant.get("approval_ref"), str) or not grant["approval_ref"]
                or len(grant["approval_ref"]) > 300):
            raise PublishAPIError("authorization_required")
        return grant

    def _access(self, grant, platform, target_id):
        """先核准交易，再由 setup Runtime 驗證與取用記憶體 Token。"""

        grant = self._grant(grant, platform, target_id)
        return self._read_access(platform, target_id, confirmed_read=True,
                                 allow_refresh=grant["allow_token_refresh"])

    def _read_access(self, platform, target_id, *, confirmed_read, allow_refresh=False):
        """共用身分核對；唯讀準備不用捏造發布確認或先 begin。"""
        if confirmed_read is not True or type(allow_refresh) is not bool:
            raise PublishAPIError("authorization_required")
        try:
            runtime = self.runtime_factory(self.workspace, platform, self.connection)
            config = runtime.config()
            if str(config.get("target_id")) != str(target_id):
                raise PublishAPIError("target_mismatch")
            token = runtime.access(confirmed_read=True, allow_refresh=allow_refresh)
            if not isinstance(token, str) or not token:
                raise PublishAPIError("reauth_required")
            return config, token
        except PublishAPIError:
            raise
        except Exception as error:
            kind = getattr(error, "kind", None)
            mapping = {
                "authorization_required": "authorization_required", "reauth_required": "reauth_required",
                "refresh_required": "reauth_required", "permission_mismatch": "permission_mismatch",
                "target_mismatch": "target_mismatch", "rate_limited": "rate_limited",
            }
            raise PublishAPIError(mapping.get(kind, "adapter_unavailable")) from None

    def verify_access(self, grant):
        """在 claim 外部寫入前先驗證既有連線；只回傳非敏感身分摘要。"""

        if not isinstance(grant, dict):
            raise PublishAPIError("authorization_required")
        platform = grant.get("platform")
        target_id = grant.get("target_id")
        if platform not in {"youtube", "facebook", "instagram", "threads"}:
            raise PublishAPIError("adapter_unavailable")
        if platform == "youtube":
            target_id = _youtube_resource_id(target_id)
        else:
            target_id = _identifier(target_id)
        config, _ = self._access(grant, platform, target_id)
        return {"platform": platform, "target_id": str(target_id),
                "login_route": config.get("login_route"), "ready": True}

    def _management_rows(self, endpoint, token, resource_id, fields):
        """最多五頁，只用游標組固定端點；不跟隨回應中的 next 網址。"""
        query, seen = {"fields": fields, "limit": 100}, set()
        for _ in range(5):
            payload = _safe_json(self.http.request_json("GET", endpoint, query=query,
                bearer=token, mutation=False).payload, mutation=False)
            rows = payload.get("data")
            if not isinstance(rows, list) or any(not isinstance(row, dict) or not row.get("id") for row in rows):
                raise PublishAPIError("read_failed")
            matches = [row for row in rows if str(row["id"]) == resource_id]
            if len(matches) > 1:
                raise PublishAPIError("read_failed")
            if matches:
                return matches[0], True
            paging = payload.get("paging", {})
            if not isinstance(paging, dict):
                raise PublishAPIError("read_failed")
            if not paging.get("next"):
                return None, True
            cursor = paging.get("cursors", {}).get("after")
            if not isinstance(cursor, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,2048}", cursor) or cursor in seen:
                raise PublishAPIError("read_failed")
            seen.add(cursor)
            query["after"] = cursor
        return None, False

    def _content_snapshot(self, platform, target_id, resource_id, config, token):
        """只選內容、版本與擁有者證據；原始回應及秘密不落盤。"""
        if platform == "youtube":
            resource_id = _youtube_resource_id(resource_id)
            payload = _safe_json(self.http.request_json("GET", "https://www.googleapis.com/youtube/v3/videos",
                query={"id": resource_id, "part": "snippet,status"}, bearer=token, mutation=False).payload,
                mutation=False)
            rows = payload.get("items")
            if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
                raise PublishAPIError("read_failed")
            row, snippet = rows[0], rows[0].get("snippet", {})
            if row.get("id") != resource_id or snippet.get("channelId") != target_id:
                raise PublishAPIError("target_mismatch")
            details = {"snippet": {key: snippet[key] for key in (
                "title", "description", "categoryId", "tags", "defaultLanguage", "defaultAudioLanguage") if key in snippet},
                "privacy_status": (row.get("status") or {}).get("privacyStatus")}
            result = {"id": resource_id, "title": snippet.get("title"), "body": snippet.get("description", ""),
                      "version": row.get("etag"), "url": None, "details": details}
        elif platform == "facebook":
            resource_id = _identifier(resource_id, graph=True)
            if not resource_id.startswith(target_id + "_"):
                raise PublishAPIError("target_mismatch")
            endpoint = f"https://graph.facebook.com/{config['graph_version']}/{resource_id}"
            row = _safe_json(self.http.request_json("GET", endpoint, query={"fields":
                "id,message,updated_time,from,permalink_url,is_published,application"},
                bearer=token, mutation=False).payload, mutation=False)
            if row.get("id") != resource_id or (row.get("from") or {}).get("id") != target_id:
                raise PublishAPIError("target_mismatch")
            result = {"id": resource_id, "title": "", "body": row.get("message", ""),
                "version": row.get("updated_time"), "url": row.get("permalink_url"),
                "details": {"is_published": row.get("is_published"),
                            "application_id": (row.get("application") or {}).get("id")}}
        elif platform in {"threads", "instagram"}:
            resource_id = _identifier(resource_id)
            if platform == "instagram" and config.get("login_route") != "instagram_facebook_login":
                raise PublishAPIError("adapter_unavailable")
            endpoint = (f"https://graph.threads.net/{config['graph_version']}/me/threads" if platform == "threads"
                        else f"https://graph.facebook.com/{config['graph_version']}/{target_id}/media")
            fields = "id,text,permalink,timestamp,media_type" if platform == "threads" else "id,caption,permalink,timestamp,media_type,children{id}"
            row, _ = self._management_rows(endpoint, token, resource_id, fields)
            if row is None:
                raise PublishAPIError("read_failed")
            result = {"id": resource_id, "title": "", "body": row.get("text" if platform == "threads" else "caption", ""),
                "version": row.get("timestamp"), "url": row.get("permalink"),
                "details": {"media_type": row.get("media_type")}}
            if platform == "instagram":
                children = (row.get("children") or {}).get("data", [])
                if not isinstance(children, list) or any(not isinstance(child, dict) for child in children):
                    raise PublishAPIError("read_failed")
                result["details"]["children"] = [_identifier(child.get("id")) for child in children]
        else:
            raise PublishAPIError("adapter_unavailable")
        if not isinstance(result["version"], str) or not result["version"]:
            raise PublishAPIError("read_failed")
        if any(not isinstance(result[key], str) for key in ("title", "body")):
            raise PublishAPIError("read_failed")
        if result["url"] is not None:
            _https_url(result["url"])
        return result

    def inspect_content(self, platform, target_id, resource_id, *, confirmed_read=False, allow_refresh=False):
        """預覽前獨立唯讀入口；不建立交易、不寫入平台。"""
        if platform not in {"facebook", "threads", "youtube", "instagram"}:
            raise PublishAPIError("adapter_unavailable")
        target_id = _youtube_resource_id(target_id) if platform == "youtube" else _identifier(target_id)
        config, token = self._read_access(platform, target_id, confirmed_read=confirmed_read, allow_refresh=allow_refresh)
        return self._content_snapshot(platform, target_id, resource_id, config, token)

    @staticmethod
    def _management_permission(platform, config):
        """檢查既有權限，不從發布權限推定可以刪除。"""
        scopes = set(config.get("scopes", []))
        needed = {"facebook": {"pages_manage_posts"}, "threads": {"threads_basic", "threads_delete"},
                  "instagram": {"instagram_basic", "instagram_manage_contents"}}
        if platform == "youtube":
            valid = bool(scopes & {"https://www.googleapis.com/auth/youtube",
                "https://www.googleapis.com/auth/youtube.force-ssl", "https://www.googleapis.com/auth/youtubepartner"})
        else:
            valid = needed.get(platform, {"unsupported"}).issubset(scopes)
        if not valid:
            raise PublishAPIError("permission_mismatch")

    def delete_content(self, grant, *, resource_id, before):
        """核對完整舊快照後送一次刪除；受理不冒充刪除讀回。"""
        platform, target = grant.get("platform"), grant.get("target_id")
        config, token = self._access(grant, platform, target)
        self._management_permission(platform, config)
        current = self._content_snapshot(platform, target, resource_id, config, token)
        if current != before:
            raise PublishAPIError("asset_changed")
        if platform == "instagram":
            # 已從自己 media 列表核對父媒體；刪除只用另行驗證的 Facebook User Token。
            try:
                runtime = self.runtime_factory(self.workspace, platform, self.connection)
                if runtime.config().get("target_id") != target:
                    raise PublishAPIError("target_mismatch")
                token = runtime.access_instagram_user(confirmed_read=True)
            except PublishAPIError:
                raise
            except Exception as error:
                raise PublishAPIError(getattr(error, "kind", "reauth_required")) from None
        if platform == "youtube":
            result = self.http.request_json("DELETE", "https://www.googleapis.com/youtube/v3/videos",
                query={"id": resource_id}, bearer=token, mutation=True, allow_empty=True)
            accepted = result.status == 204
        else:
            if platform == "facebook" and current["details"]["is_published"] is not True:
                raise PublishAPIError("adapter_unavailable")
            host = "graph.facebook.com" if platform in {"facebook", "instagram"} else "graph.threads.com"
            result = self.http.request_json("DELETE", f"https://{host}/{config['graph_version']}/{resource_id}",
                bearer=token, mutation=True)
            payload = _safe_json(result.payload, mutation=True)
            accepted = payload.get("success") is True
            if platform in {"threads", "instagram"}:
                accepted = accepted and str(payload.get("deleted_id")) == resource_id
        if not accepted:
            raise PublishAPIError("remote_result_unknown")
        return {"remote_id": resource_id, "status": "deletion_accepted"}

    def youtube_update_content(self, grant, *, resource_id, before, title, description):
        """只改標題與說明；保留既有 snippet 可寫欄位，不觸碰可見性。"""
        target = _youtube_resource_id(grant.get("target_id"))
        config, token = self._access(grant, "youtube", target)
        self._management_permission("youtube", config)
        current = self._content_snapshot("youtube", target, resource_id, config, token)
        if current != before:
            raise PublishAPIError("asset_changed")
        snippet = dict(current["details"]["snippet"])
        # 當前 update 文件未列 defaultAudioLanguage 可寫，不能猜測送出或刪掉它。
        if snippet.get("defaultAudioLanguage"):
            raise PublishAPIError("adapter_unavailable")
        snippet.pop("defaultAudioLanguage", None)
        if not snippet.get("categoryId"):
            raise PublishAPIError("read_failed")
        snippet.update(title=_plain_text(title, maximum=100), description=_plain_text(description, allow_empty=True, maximum=5000))
        result = self.http.request_json("PUT", "https://www.googleapis.com/youtube/v3/videos",
            query={"part": "snippet"}, json_body={"id": resource_id, "snippet": snippet},
            bearer=token, mutation=True)
        if _safe_json(result.payload, mutation=True).get("id") != resource_id:
            raise PublishAPIError("remote_result_unknown")
        return {"remote_id": resource_id, "status": "pending_readback"}

    def management_readback(self, grant, resource_id):
        """已核准交易的獨立內容讀回。"""
        config, token = self._access(grant, grant.get("platform"), grant.get("target_id"))
        return self._content_snapshot(grant["platform"], grant["target_id"], resource_id, config, token)

    def deletion_readback(self, grant, resource_id):
        """有效連線下獨立列舉；缺頁、錯誤、單純 404 均不算已刪除。"""
        platform, target = grant.get("platform"), grant.get("target_id")
        config, token = self._access(grant, platform, target)
        self._management_permission(platform, config)
        if platform == "youtube":
            payload = _safe_json(self.http.request_json("GET", "https://www.googleapis.com/youtube/v3/videos",
                query={"id": _youtube_resource_id(resource_id), "part": "id"}, bearer=token, mutation=False).payload,
                mutation=False)
            rows = payload.get("items")
            if not isinstance(rows, list):
                raise PublishAPIError("read_failed")
            absent, complete = rows == [], True
        else:
            if platform == "facebook":
                resource_id = _identifier(resource_id, graph=True)
                if not resource_id.startswith(target + "_"):
                    raise PublishAPIError("target_mismatch")
                endpoint = f"https://graph.facebook.com/{config['graph_version']}/{target}/feed"
            elif platform == "instagram":
                resource_id = _identifier(resource_id)
                if config.get("login_route") != "instagram_facebook_login":
                    raise PublishAPIError("adapter_unavailable")
                endpoint = f"https://graph.facebook.com/{config['graph_version']}/{target}/media"
            else:
                resource_id = _identifier(resource_id)
                endpoint = f"https://graph.threads.net/{config['graph_version']}/me/threads"
            row, complete = self._management_rows(endpoint, token, resource_id, "id")
            absent = row is None and complete
        return {"resource_id": resource_id, "absent": absent, "complete": complete,
                "connection_verified": True}

    def _asset(self, relative):
        """YouTube 本機檔案只能位於工作區內且不得是 symlink。"""

        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise PublishAPIError("invalid_request")
        current = self.workspace
        for part in Path(relative).parts:
            if part in {"", ".", ".."}:
                raise PublishAPIError("invalid_request")
            current /= part
            if current.is_symlink():
                raise PublishAPIError("invalid_request")
        resolved = current.resolve(strict=True)
        if not resolved.is_relative_to(self.workspace) or not resolved.is_file():
            raise PublishAPIError("invalid_request")
        return resolved

    @staticmethod
    def _hash(path):
        value = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                value.update(chunk)
        return value.hexdigest()

    @staticmethod
    def _id(payload, key="id", *, graph=False, youtube=False, mutation=True):
        payload = _safe_json(payload, mutation=mutation)
        try:
            if youtube:
                value = payload.get(key)
                if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{6,100}", value):
                    raise PublishAPIError("invalid_request")
                return value
            return _identifier(payload.get(key), graph=graph)
        except PublishAPIError:
            raise PublishAPIError("remote_result_unknown" if mutation else "read_failed") from None

    def youtube_start_upload(self, grant, *, asset_path, metadata, notify_subscribers,
                             content_type=None):
        """建立一次 resumable session；不把 session URL 放進回傳文字。"""

        target_id = _youtube_resource_id(grant.get("target_id") if isinstance(grant, dict) else None)
        config, token = self._access(grant, "youtube", target_id)
        if set(metadata or {}) != {"snippet", "status"} or type(notify_subscribers) is not bool:
            raise PublishAPIError("invalid_request")
        snippet, status = metadata["snippet"], metadata["status"]
        if not isinstance(snippet, dict) or not isinstance(status, dict):
            raise PublishAPIError("invalid_request")
        if not {"title", "description", "categoryId"}.issubset(snippet):
            raise PublishAPIError("invalid_request")
        if set(snippet) - {"title", "description", "categoryId", "tags", "defaultLanguage"}:
            raise PublishAPIError("invalid_request")
        if set(status) - {"privacyStatus", "publishAt", "selfDeclaredMadeForKids",
                          "containsSyntheticMedia", "embeddable", "license", "publicStatsViewable"}:
            raise PublishAPIError("invalid_request")
        _plain_text(snippet["title"], maximum=500)
        _plain_text(snippet["description"], allow_empty=True)
        _identifier(snippet["categoryId"])
        if status.get("privacyStatus") not in {"private", "public", "unlisted"}:
            raise PublishAPIError("invalid_request")
        if "tags" in snippet and (not isinstance(snippet["tags"], list)
                                  or any(not isinstance(tag, str) or not tag for tag in snippet["tags"])):
            raise PublishAPIError("invalid_request")
        path = self._asset(asset_path)
        content_type = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if not re.fullmatch(r"(?:video/[A-Za-z0-9.+-]+|application/octet-stream)", content_type):
            raise PublishAPIError("invalid_request")
        endpoint = "https://www.googleapis.com/upload/youtube/v3/videos"
        result = self.http.request_json(
            "POST", endpoint,
            query={"uploadType": "resumable", "part": "snippet,status",
                   "notifySubscribers": notify_subscribers},
            json_body=metadata, bearer=token, mutation=True, allow_empty=True,
            headers={"X-Upload-Content-Length": str(path.stat().st_size),
                     "X-Upload-Content-Type": content_type},
        )
        location = result.headers.get("location")
        if not isinstance(location, str) or not OfficialPublishHTTP._session_url(location):
            raise PublishAPIError("remote_result_unknown")
        return SensitiveUploadSession(
            location, item_id=grant["item_id"], preview_sha256=grant["preview_sha256"],
            target_id=target_id, asset_sha256=self._hash(path), size=path.stat().st_size,
            content_type=content_type, connection=self.connection,
        )

    def youtube_upload(self, grant, session, *, asset_path):
        """只對同一 session、同一核准項目與未變檔案送一次 PUT。"""

        if not isinstance(session, SensitiveUploadSession):
            raise PublishAPIError("invalid_request")
        self._grant(grant, "youtube", session.target_id)
        if (grant["item_id"] != session.item_id
                or grant["preview_sha256"] != session.preview_sha256
                or self.connection != session.connection):
            raise PublishAPIError("authorization_required")
        path = self._asset(asset_path)
        if path.stat().st_size != session.size or self._hash(path) != session.asset_sha256:
            raise PublishAPIError("asset_changed")
        _, token = self._access(grant, "youtube", session.target_id)
        result = self.http.upload_file(session._url, path, bearer=token,
                                       content_type=session.content_type)
        if result.status == 308:
            uploaded = result.headers.get("range")
            if uploaded is not None and not re.fullmatch(r"bytes=0-[0-9]+", uploaded):
                raise PublishAPIError("remote_result_unknown")
            return {"stage": "upload-incomplete", "remote_id": None,
                    "uploaded_range": uploaded, "status": "pending"}
        video_id = self._id(result.payload, youtube=True)
        return {"stage": "video-uploaded", "remote_id": video_id, "status": "pending_readback"}

    def youtube_readback(self, grant, video_id):
        """用 owner Token 讀回指定影片與頻道；不從 ID 拼接成功網址。"""

        video_id = _youtube_resource_id(video_id)
        target_id = _youtube_resource_id(grant.get("target_id") if isinstance(grant, dict) else None)
        _, token = self._access(grant, "youtube", target_id)
        result = self.http.request_json(
            "GET", "https://www.googleapis.com/youtube/v3/videos",
            query={"part": "snippet,status,processingDetails", "id": video_id},
            bearer=token, mutation=False,
        )
        rows = _safe_json(result.payload, mutation=False).get("items")
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            raise PublishAPIError("read_failed")
        row = rows[0]
        if str(row.get("id")) != video_id or str(row.get("snippet", {}).get("channelId")) != target_id:
            raise PublishAPIError("target_mismatch")
        return {"id": video_id, "snippet": row.get("snippet"), "status": row.get("status"),
                "processingDetails": row.get("processingDetails")}

    def facebook_create_feed(self, grant, *, message="", link=None,
                             attached_media=None, scheduled_publish_time=None):
        """建立文字、連結或已上傳照片組合的 Page 貼文。"""

        target_id = _identifier(grant.get("target_id") if isinstance(grant, dict) else None)
        config, token = self._access(grant, "facebook", target_id)
        message = _plain_text(message, allow_empty=True)
        if not message and not link and not attached_media:
            raise PublishAPIError("invalid_request")
        form = {"message": message}
        if link is not None:
            form["link"] = _https_url(link)
        if attached_media is not None:
            if (not isinstance(attached_media, list) or not attached_media
                    or any(not re.fullmatch(r"[0-9]+", str(item)) for item in attached_media)):
                raise PublishAPIError("invalid_request")
            form["attached_media"] = [{"media_fbid": str(item)} for item in attached_media]
        if scheduled_publish_time is not None:
            if type(scheduled_publish_time) is not int or scheduled_publish_time <= 0:
                raise PublishAPIError("invalid_request")
            form.update(published=False, scheduled_publish_time=scheduled_publish_time)
        endpoint = f"https://graph.facebook.com/{config['graph_version']}/{target_id}/feed"
        result = self.http.request_json("POST", endpoint, form=form, bearer=token, mutation=True)
        post_id = self._id(result.payload, graph=True)
        if not post_id.startswith(target_id + "_"):
            raise PublishAPIError("remote_result_unknown")
        return {"stage": "post-created", "remote_id": post_id,
                "status": "pending_readback"}

    def facebook_upload_photo(self, grant, *, source_url, caption="", alt_text="", published=True):
        """用已授權的 HTTPS 素材來源建立 Page 照片；不代建公開圖床。"""

        target_id = _identifier(grant.get("target_id") if isinstance(grant, dict) else None)
        config, token = self._access(grant, "facebook", target_id)
        if type(published) is not bool:
            raise PublishAPIError("invalid_request")
        form = {"url": _https_url(source_url), "caption": _plain_text(caption, allow_empty=True),
                "alt_text_custom": _plain_text(alt_text, allow_empty=True), "published": published}
        endpoint = f"https://graph.facebook.com/{config['graph_version']}/{target_id}/photos"
        result = self.http.request_json("POST", endpoint, form=form, bearer=token, mutation=True)
        payload = _safe_json(result.payload, mutation=True)
        photo_id = self._id(payload)
        post_id = payload.get("post_id")
        if post_id is not None:
            post_id = _identifier(post_id, graph=True)
            if not post_id.startswith(target_id + "_"):
                raise PublishAPIError("remote_result_unknown")
        return {"stage": "photo-uploaded", "remote_id": photo_id, "post_id": post_id,
                "status": "pending_readback"}

    def facebook_update_message(self, grant, *, post_id, message, before_message, before_updated_time):
        """只改同一 App 建立的指定專頁貼文；先查版本再送一次，不重試。"""
        target_id = _identifier(grant.get("target_id") if isinstance(grant, dict) else None)
        post_id = _identifier(post_id, graph=True)
        if not post_id.startswith(target_id + "_"):
            raise PublishAPIError("target_mismatch")
        message = _plain_text(message)
        config, token = self._access(grant, "facebook", target_id)
        if "pages_manage_posts" not in config.get("scopes", []):
            raise PublishAPIError("permission_mismatch")
        endpoint = f"https://graph.facebook.com/{config['graph_version']}/{post_id}"
        before = _safe_json(self.http.request_json("GET", endpoint,
            query={"fields": "id,message,updated_time,application"}, bearer=token, mutation=False).payload,
            mutation=False)
        if (before.get("id") != post_id or not config.get("client_id")
                or (before.get("application") or {}).get("id") != config["client_id"]):
            raise PublishAPIError("target_mismatch")
        if before.get("message", "") != before_message or before.get("updated_time") != before_updated_time:
            raise PublishAPIError("asset_changed")
        result = _safe_json(self.http.request_json("POST", endpoint, form={"message": message},
            bearer=token, mutation=True).payload, mutation=True)
        if result.get("success") is not True:
            raise PublishAPIError("remote_result_unknown")
        return {"stage": "post-updated", "remote_id": post_id, "status": "pending_readback"}

    def facebook_readback(self, grant, post_id, *, management=False):
        """讀回 PagePost 必要欄位；後續交易層再與預覽逐項比較。"""

        post_id = _identifier(post_id, graph=True)
        target_id = _identifier(grant.get("target_id") if isinstance(grant, dict) else None)
        config, token = self._access(grant, "facebook", target_id)
        endpoint = f"https://graph.facebook.com/{config['graph_version']}/{post_id}"
        result = self.http.request_json(
            "GET", endpoint,
            query={"fields": "id,message,permalink_url,created_time,is_published,scheduled_publish_time,attachments" + (",updated_time" if management else "")},
            bearer=token, mutation=False,
        )
        payload = _safe_json(result.payload, mutation=False)
        if str(payload.get("id")) != post_id or not post_id.startswith(target_id + "_"):
            raise PublishAPIError("target_mismatch")
        selected = {key: payload.get(key) for key in (
            "id", "message", "permalink_url", "created_time", "is_published",
            "scheduled_publish_time", "attachments")}
        if management:
            selected["updated_time"] = payload.get("updated_time")
        return selected

    def _instagram_context(self, grant):
        target_id = _identifier(grant.get("target_id") if isinstance(grant, dict) else None)
        config, token = self._access(grant, "instagram", target_id)
        route = config.get("login_route")
        if route == "instagram_login":
            host = "graph.instagram.com"
        elif route == "instagram_facebook_login":
            host = "graph.facebook.com"
        else:
            raise PublishAPIError("adapter_unavailable")
        return target_id, config, token, host

    def instagram_create_media(self, grant, params):
        """建立單圖、輪播子項／父項或 Reel 容器，不自動發布。"""

        if not isinstance(params, dict) or not params:
            raise PublishAPIError("invalid_request")
        allowed = {"image_url", "video_url", "media_type", "caption", "alt_text", "children",
                   "is_carousel_item", "cover_url", "share_to_feed"}
        if set(params) - allowed:
            raise PublishAPIError("invalid_request")
        clean = dict(params)
        for key in ("image_url", "video_url", "cover_url"):
            if key in clean:
                clean[key] = _https_url(clean[key])
        for key in ("caption", "alt_text"):
            if key in clean:
                clean[key] = _plain_text(clean[key], allow_empty=True)
        if "children" in clean:
            if (not isinstance(clean["children"], list) or len(clean["children"]) < 2
                    or any(not re.fullmatch(r"[0-9]+", str(item)) for item in clean["children"])):
                raise PublishAPIError("invalid_request")
            clean["children"] = [str(item) for item in clean["children"]]
        media_type = clean.get("media_type")
        if media_type not in {None, "IMAGE", "VIDEO", "REELS", "CAROUSEL"}:
            raise PublishAPIError("invalid_request")
        if media_type == "CAROUSEL" and "children" not in clean:
            raise PublishAPIError("invalid_request")
        if media_type in {"VIDEO", "REELS"} and "video_url" not in clean:
            raise PublishAPIError("invalid_request")
        if media_type in {None, "IMAGE"} and "image_url" not in clean:
            raise PublishAPIError("invalid_request")
        target_id, config, token, host = self._instagram_context(grant)
        endpoint = f"https://{host}/{config['graph_version']}/{target_id}/media"
        result = self.http.request_json("POST", endpoint, form=clean, bearer=token, mutation=True)
        return {"stage": "container-created", "remote_id": self._id(result.payload),
                "status": "pending_processing"}

    def instagram_container_status(self, grant, container_id):
        """容器只做一次唯讀狀態查詢；有界輪詢由上層控制。"""

        container_id = _identifier(container_id)
        _, config, token, host = self._instagram_context(grant)
        endpoint = f"https://{host}/{config['graph_version']}/{container_id}"
        result = self.http.request_json("GET", endpoint, query={"fields": "id,status_code,status"},
                                        bearer=token, mutation=False)
        payload = _safe_json(result.payload, mutation=False)
        if str(payload.get("id")) != container_id:
            raise PublishAPIError("target_mismatch")
        return {"id": container_id, "status_code": payload.get("status_code"),
                "status": payload.get("status")}

    def instagram_publish(self, grant, container_id):
        """對已完成容器送一次 media_publish。"""

        container_id = _identifier(container_id)
        target_id, config, token, host = self._instagram_context(grant)
        endpoint = f"https://{host}/{config['graph_version']}/{target_id}/media_publish"
        result = self.http.request_json("POST", endpoint, form={"creation_id": container_id},
                                        bearer=token, mutation=True)
        return {"stage": "media-published", "remote_id": self._id(result.payload),
                "status": "pending_readback"}

    def instagram_readback(self, grant, media_id):
        """讀回正式媒體，而不是把 container ID 當貼文。"""

        media_id = _identifier(media_id)
        _, config, token, host = self._instagram_context(grant)
        endpoint = f"https://{host}/{config['graph_version']}/{media_id}"
        result = self.http.request_json(
            "GET", endpoint,
            query={"fields": "id,caption,media_type,media_product_type,permalink,timestamp,children"},
            bearer=token, mutation=False,
        )
        payload = _safe_json(result.payload, mutation=False)
        if str(payload.get("id")) != media_id:
            raise PublishAPIError("target_mismatch")
        return {key: payload.get(key) for key in (
            "id", "caption", "media_type", "media_product_type", "permalink", "timestamp", "children")}

    def _threads_context(self, grant):
        target_id = _identifier(grant.get("target_id") if isinstance(grant, dict) else None)
        config, token = self._access(grant, "threads", target_id)
        if config.get("login_route") != "threads_login":
            raise PublishAPIError("adapter_unavailable")
        return target_id, config, token

    def threads_create_container(self, grant, params):
        """建立單則文字、圖片或影片容器；禁用自動發布與回覆欄位。"""

        if not isinstance(params, dict) or not params:
            raise PublishAPIError("invalid_request")
        allowed = {"text", "media_type", "image_url", "video_url", "alt_text", "reply_control",
                   "link_attachment", "topic_tag", "is_spoiler_media"}
        if set(params) - allowed or params.get("media_type") not in {"TEXT", "IMAGE", "VIDEO"}:
            raise PublishAPIError("invalid_request")
        clean = dict(params)
        if "text" in clean:
            clean["text"] = _plain_text(clean["text"], allow_empty=True)
        if clean["media_type"] == "TEXT" and not clean.get("text") and not clean.get("link_attachment"):
            raise PublishAPIError("invalid_request")
        for key in ("image_url", "video_url", "link_attachment"):
            if key in clean:
                clean[key] = _https_url(clean[key])
        if clean["media_type"] == "IMAGE" and "image_url" not in clean:
            raise PublishAPIError("invalid_request")
        if clean["media_type"] == "VIDEO" and "video_url" not in clean:
            raise PublishAPIError("invalid_request")
        for key in ("alt_text", "reply_control", "topic_tag"):
            if key in clean:
                clean[key] = _plain_text(clean[key], allow_empty=False, maximum=500)
        _, config, token = self._threads_context(grant)
        endpoint = f"https://graph.threads.net/{config['graph_version']}/me/threads"
        result = self.http.request_json("POST", endpoint, form=clean, bearer=token, mutation=True)
        return {"stage": "container-created", "remote_id": self._id(result.payload),
                "status": "pending_processing"}

    def threads_container_status(self, grant, container_id):
        """讀一次容器狀態；不在底層自行等待或重送。"""

        container_id = _identifier(container_id)
        _, config, token = self._threads_context(grant)
        endpoint = f"https://graph.threads.net/{config['graph_version']}/{container_id}"
        result = self.http.request_json("GET", endpoint, query={"fields": "id,status"},
                                        bearer=token, mutation=False)
        payload = _safe_json(result.payload, mutation=False)
        if str(payload.get("id")) != container_id:
            raise PublishAPIError("target_mismatch")
        return {"id": container_id, "status": payload.get("status")}

    def threads_publish(self, grant, container_id):
        """對同一容器送一次 threads_publish。"""

        container_id = _identifier(container_id)
        _, config, token = self._threads_context(grant)
        endpoint = f"https://graph.threads.net/{config['graph_version']}/me/threads_publish"
        result = self.http.request_json("POST", endpoint, form={"creation_id": container_id},
                                        bearer=token, mutation=True)
        return {"stage": "thread-published", "remote_id": self._id(result.payload),
                "status": "pending_readback"}

    def threads_readback(self, grant, thread_id):
        """從自己的貼文列表找正式 ID，避免把其他帳號同文案誤認成功。"""

        thread_id = _identifier(thread_id)
        _, config, token = self._threads_context(grant)
        endpoint = f"https://graph.threads.net/{config['graph_version']}/me/threads"
        query = {"fields": "id,text,permalink,timestamp,media_type,username", "limit": 100}
        seen, matches = set(), []
        for _ in range(5):
            result = self.http.request_json("GET", endpoint, query=query,
                                            bearer=token, mutation=False)
            payload = _safe_json(result.payload, mutation=False)
            rows = payload.get("data")
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise PublishAPIError("read_failed")
            matches.extend(row for row in rows if str(row.get("id")) == thread_id)
            if len(matches) > 1:
                raise PublishAPIError("read_failed")
            if matches:
                row = matches[0]
                return {key: row.get(key) for key in (
                    "id", "text", "permalink", "timestamp", "media_type", "username")}
            cursor = payload.get("paging", {}).get("cursors", {}).get("after")
            if cursor is None:
                break
            if (not isinstance(cursor, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,2048}", cursor)
                    or cursor in seen):
                raise PublishAPIError("read_failed")
            seen.add(cursor)
            query["after"] = cursor
        raise PublishAPIError("read_failed")
