"""四平台公開留言的受限官方 API adapter；不提供 Substack 私有端點。"""

from __future__ import annotations

from datetime import datetime, timezone
import http.client
import importlib
import json
from pathlib import Path
import re
import ssl
import sys
from urllib.parse import urlencode, urlsplit


class CommunityAPIError(RuntimeError):
    """只攜帶固定錯誤種類，避免外部留言或秘密出現在錯誤訊息。"""

    ALLOWED = {
        "authorization_required", "invalid_request", "adapter_unavailable",
        "reauth_required", "permission_mismatch", "target_mismatch",
        "rate_limited", "rejected", "read_failed", "remote_result_unknown",
        "pagination_incomplete", "comment_url_required", "reply_already_exists",
        "reply_processing", "readback_incomplete",
    }

    def __init__(self, kind):
        self.kind = kind if kind in self.ALLOWED else "read_failed"
        super().__init__(self.kind)


class HTTPResult:
    """將必要回應留在可信程式記憶體，不自行輸出。"""

    __slots__ = ("status", "payload", "headers")

    def __init__(self, status, payload, headers=None):
        self.status = status
        self.payload = payload
        self.headers = {str(key).lower(): str(value)
                        for key, value in (headers or {}).items()}


def _now():
    """建立帶時區的擷取時間。"""

    return datetime.now(timezone.utc).isoformat()


def _plain(value, *, maximum=100_000, allow_empty=False):
    """外部文字不正規化，只拒絕型別、大小與危險控制字元。"""

    if (not isinstance(value, str) or len(value) > maximum
            or (not allow_empty and not value.strip())):
        raise CommunityAPIError("read_failed")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise CommunityAPIError("read_failed")
    return value


def _resource_id(value, *, youtube=False, graph_post=False):
    """限制平台識別格式，不允許把路徑或查詢字串注入端點。"""

    if not isinstance(value, str):
        raise CommunityAPIError("invalid_request")
    if youtube:
        pattern = r"[A-Za-z0-9_-]{3,100}"
    elif graph_post:
        pattern = r"[0-9]+(?:_[0-9]+)?"
    else:
        pattern = r"[0-9]+"
    if not re.fullmatch(pattern, value):
        raise CommunityAPIError("invalid_request")
    return value


def _safe_url(value, platform):
    """受控瀏覽器補證只接受該平台 HTTPS 網址，不開啟網址。"""

    if not isinstance(value, str):
        raise CommunityAPIError("comment_url_required")
    parsed = urlsplit(value)
    allowed = {
        "youtube": {"youtube.com", "www.youtube.com", "youtu.be"},
        "facebook": {"facebook.com", "www.facebook.com"},
        "instagram": {"instagram.com", "www.instagram.com"},
        "threads": {"threads.net", "www.threads.net", "threads.com", "www.threads.com"},
    }
    if (parsed.scheme != "https" or parsed.hostname not in allowed[platform]
            or parsed.username or parsed.password or parsed.port not in (None, 443)
            or re.search(r"[?&](?:token|access_token|code|sig|key|auth)=", value, re.I)):
        raise CommunityAPIError("comment_url_required")
    return value


def _payload(value, *, mutation=False):
    """成功回應必須是 JSON 物件；空回應不推定成功。"""

    if not isinstance(value, dict):
        raise CommunityAPIError("remote_result_unknown" if mutation else "read_failed")
    return value


def _classify(status, value, *, mutation):
    """將平台錯誤收斂為固定狀態；非冪等寫入不自動重送。"""

    error = value.get("error") if isinstance(value, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    details = error.get("errors", []) if isinstance(error, dict) else []
    reasons = {row.get("reason") for row in details
               if isinstance(row, dict) and isinstance(row.get("reason"), str)} \
        if isinstance(details, list) else set()
    if status == 401 or code in {102, 190}:
        raise CommunityAPIError("reauth_required")
    if status == 429 or "quotaExceeded" in reasons or "rateLimitExceeded" in reasons:
        raise CommunityAPIError("rate_limited")
    if status == 403 or code in {10, 200}:
        raise CommunityAPIError("permission_mismatch")
    if not 200 <= status < 300 or error:
        if mutation and (300 <= status < 400 or status >= 500):
            raise CommunityAPIError("remote_result_unknown")
        raise CommunityAPIError("rejected" if mutation else "read_failed")


class OfficialCommunityHTTP:
    """只連留言工作流需要的固定官方主機與端點，不跟隨重新導向。"""

    MAX_RESPONSE = 2 * 1024 * 1024

    @staticmethod
    def _allowed(method, endpoint):
        parsed = urlsplit(endpoint)
        if (parsed.scheme != "https" or parsed.query or parsed.fragment
                or parsed.username or parsed.password):
            return False
        path = parsed.path
        if parsed.netloc == "www.googleapis.com":
            return ((method == "GET" and path in {
                "/youtube/v3/videos", "/youtube/v3/commentThreads", "/youtube/v3/comments"})
                    or (method == "POST" and path == "/youtube/v3/comments"))
        versioned = r"/v[0-9]+\.0/"
        identifier = r"[0-9]+(?:_[0-9]+)?"
        if parsed.netloc == "graph.facebook.com":
            if method == "GET":
                return bool(re.fullmatch(versioned + identifier + r"(?:/(?:comments|replies))?", path))
            return bool(re.fullmatch(versioned + identifier + r"/(?:comments|replies)", path))
        if parsed.netloc == "graph.instagram.com":
            if method == "GET":
                return bool(re.fullmatch(versioned + r"[0-9]+(?:/(?:comments|replies))?", path))
            return bool(re.fullmatch(versioned + r"[0-9]+/replies", path))
        if parsed.netloc == "graph.threads.net":
            if method == "GET":
                return bool(re.fullmatch(versioned + r"(?:me/threads|[0-9]+(?:/(?:replies|conversation))?)", path))
            return bool(re.fullmatch(versioned + r"me/(?:threads|threads_publish)", path))
        return False

    @staticmethod
    def _bearer(value):
        """拒絕空白或可注入標頭的 Token。"""

        if not isinstance(value, str) or not value or "\r" in value or "\n" in value:
            raise CommunityAPIError("authorization_required")
        return value

    @staticmethod
    def _value(value):
        """只接受 API 查詢與表單需要的簡單值。"""

        if isinstance(value, bool):
            return "true" if value else "false"
        if type(value) in {str, int}:
            return str(value)
        raise CommunityAPIError("invalid_request")

    def request_json(self, method, endpoint, *, query=None, form=None, json_body=None,
                     bearer=None, mutation=False):
        """送出單次請求；不接受 Token 查詢參數，也不重試。"""

        method = str(method).upper()
        if method not in {"GET", "POST"} or not self._allowed(method, endpoint):
            raise CommunityAPIError("invalid_request")
        if sum(value is not None for value in (form, json_body)) > 1:
            raise CommunityAPIError("invalid_request")
        for values in (query, form):
            if values is not None and (not isinstance(values, dict)
                    or any(str(key).lower() in {"access_token", "token", "authorization"}
                           for key in values)):
                raise CommunityAPIError("invalid_request")
        request_headers = {
            "Accept": "application/json", "Cache-Control": "no-store",
            "Authorization": "Bearer " + self._bearer(bearer),
        }
        body = None
        if form is not None:
            body = urlencode({key: self._value(value) for key, value in form.items()}).encode()
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif json_body is not None:
            if not isinstance(json_body, dict):
                raise CommunityAPIError("invalid_request")
            body = json.dumps(json_body, ensure_ascii=False,
                              separators=(",", ":")).encode("utf-8")
            request_headers["Content-Type"] = "application/json; charset=UTF-8"
        if body is not None:
            request_headers["Content-Length"] = str(len(body))
        parsed = urlsplit(endpoint)
        path = parsed.path
        if query:
            path += "?" + urlencode({key: self._value(value) for key, value in query.items()})
        connection = http.client.HTTPSConnection(
            parsed.hostname, timeout=60, context=ssl.create_default_context())
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            raw = response.read(self.MAX_RESPONSE + 1)
            if len(raw) > self.MAX_RESPONSE:
                raise CommunityAPIError("remote_result_unknown" if mutation else "read_failed")
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                value = None
            _classify(response.status, value, mutation=mutation)
            return HTTPResult(response.status, value, dict(response.getheaders()))
        except CommunityAPIError:
            raise
        except Exception:
            raise CommunityAPIError("remote_result_unknown" if mutation else "read_failed") from None
        finally:
            connection.close()


def _default_runtime(workspace, platform, connection):
    """從並列 setup 技能載入 Runtime，秘密只在同一程序記憶體出現。"""

    scripts = Path(__file__).resolve().parents[2] / "social-media-setup" / "scripts"
    if not scripts.is_dir():
        raise CommunityAPIError("adapter_unavailable")
    added = str(scripts) not in sys.path
    if added:
        sys.path.insert(0, str(scripts))
    try:
        module = importlib.import_module("oauth_runtime")
        return module.Runtime(workspace, platform, connection=connection)
    except CommunityAPIError:
        raise
    except Exception:
        raise CommunityAPIError("adapter_unavailable") from None
    finally:
        if added and sys.path and sys.path[0] == str(scripts):
            sys.path.pop(0)


class OfficialCommunityAdapter:
    """取得留言、檢查自家回覆、建立核准回覆並獨立讀回。"""

    READ_KEYS = {"platform", "account_id", "post_id", "approval_ref", "confirmed_read",
                 "allow_token_refresh", "url_observations"}
    WRITE_KEYS = {"platform", "account_id", "post_id", "comment_id", "reply_target_id",
                  "text", "approval_ref", "transaction_status", "stage",
                  "allow_token_refresh"}
    REPLY_FIELDS = ("id,text,timestamp,permalink,username,is_reply,is_reply_owned_by_me,"
                    "root_post,replied_to")

    def __init__(self, workspace, *, connection="main", runtime_factory=None,
                 http_transport=None):
        self.workspace = Path(workspace).expanduser().resolve()
        if not self.workspace.is_dir() or not re.fullmatch(r"[a-z][a-z0-9-]{0,19}", connection):
            raise CommunityAPIError("invalid_request")
        self.connection = connection
        self.runtime_factory = runtime_factory or _default_runtime
        self.http = http_transport or OfficialCommunityHTTP()

    @staticmethod
    def _scope(scope):
        """讀取必須綁定已確認的平台、帳號與自有貼文。"""

        if not isinstance(scope, dict) or set(scope) != OfficialCommunityAdapter.READ_KEYS:
            raise CommunityAPIError("authorization_required")
        platform = scope.get("platform")
        if (platform not in {"youtube", "facebook", "instagram", "threads"}
                or scope.get("confirmed_read") is not True
                or scope.get("allow_token_refresh") not in {True, False}
                or not isinstance(scope.get("approval_ref"), str)
                or not scope["approval_ref"] or len(scope["approval_ref"]) > 300
                or not isinstance(scope.get("url_observations"), dict)):
            raise CommunityAPIError("authorization_required")
        if platform == "youtube":
            _resource_id(scope["account_id"], youtube=True)
            _resource_id(scope["post_id"], youtube=True)
        else:
            _resource_id(scope["account_id"])
            _resource_id(scope["post_id"], graph_post=platform == "facebook")
        for key, value in scope["url_observations"].items():
            _resource_id(str(key), youtube=platform == "youtube")
            _safe_url(value, platform)
        return scope

    @staticmethod
    def _grant(grant, stage):
        """外部寫入只接受 community_queue 已 begin 並 claim 的最小執行包。"""

        if not isinstance(grant, dict) or set(grant) != OfficialCommunityAdapter.WRITE_KEYS:
            raise CommunityAPIError("authorization_required")
        platform = grant.get("platform")
        if (platform not in {"youtube", "facebook", "instagram", "threads"}
                or grant.get("transaction_status") != "in_flight"
                or grant.get("stage") != stage
                or grant.get("allow_token_refresh") not in {True, False}
                or not isinstance(grant.get("approval_ref"), str) or not grant["approval_ref"]):
            raise CommunityAPIError("authorization_required")
        if platform == "youtube":
            for key in ("account_id", "post_id", "comment_id", "reply_target_id"):
                _resource_id(grant[key], youtube=True)
        else:
            _resource_id(grant["account_id"])
            _resource_id(grant["post_id"], graph_post=platform == "facebook")
            _resource_id(grant["comment_id"])
            _resource_id(grant["reply_target_id"])
        _plain(grant["text"], maximum=10_000)
        return grant

    def _access(self, platform, account_id, *, allow_refresh):
        """核對設定目標後才取 Token；不把 Token 放進回傳資料。"""

        try:
            runtime = self.runtime_factory(self.workspace, platform, self.connection)
            config = runtime.config()
            if str(config.get("target_id")) != account_id:
                raise CommunityAPIError("target_mismatch")
            token = runtime.access(confirmed_read=True, allow_refresh=allow_refresh)
            if not isinstance(token, str) or not token:
                raise CommunityAPIError("reauth_required")
            return config, token
        except CommunityAPIError:
            raise
        except Exception as error:
            mapping = {
                "authorization_required": "authorization_required", "reauth_required": "reauth_required",
                "refresh_required": "reauth_required", "permission_mismatch": "permission_mismatch",
                "target_mismatch": "target_mismatch", "rate_limited": "rate_limited",
            }
            raise CommunityAPIError(mapping.get(getattr(error, "kind", None),
                                                "adapter_unavailable")) from None

    def _context(self, scope):
        """依登入路徑選固定官方 host 與 Graph 版本。"""

        scope = self._scope(scope)
        platform = scope["platform"]
        config, token = self._access(
            platform, scope["account_id"], allow_refresh=scope["allow_token_refresh"])
        if platform == "youtube":
            return scope, config, token, "https://www.googleapis.com"
        version = config.get("graph_version")
        if not isinstance(version, str) or not re.fullmatch(r"v[0-9]+\.0", version):
            raise CommunityAPIError("adapter_unavailable")
        if platform == "instagram":
            route = config.get("login_route")
            if route == "instagram_login":
                host = "https://graph.instagram.com"
            elif route == "instagram_facebook_login":
                host = "https://graph.facebook.com"
            else:
                raise CommunityAPIError("adapter_unavailable")
        elif platform == "facebook":
            host = "https://graph.facebook.com"
        else:
            if config.get("login_route") != "threads_login":
                raise CommunityAPIError("adapter_unavailable")
            host = "https://graph.threads.net"
        return scope, config, token, f"{host}/{version}"

    def verify_access(self, scope):
        """在本機 claim 前驗證既有連線，只回傳非敏感摘要。"""

        scope, config, _, _ = self._context(scope)
        return {"platform": scope["platform"], "account_id": scope["account_id"],
                "post_id": scope["post_id"], "login_route": config.get("login_route"),
                "ready": True}

    def _page(self, endpoint, query, token, *, google=False):
        """最多五頁、一百項；有剩餘 cursor 時回報不完整。"""

        items = []
        current = dict(query)
        complete = False
        for _ in range(5):
            result = self.http.request_json("GET", endpoint, query=current, bearer=token)
            payload = _payload(result.payload)
            data = payload.get("items" if google else "data")
            if not isinstance(data, list):
                raise CommunityAPIError("read_failed")
            room = 100 - len(items)
            items.extend(data[:room])
            if google:
                cursor = payload.get("nextPageToken")
                key = "pageToken"
            else:
                paging = payload.get("paging", {})
                cursors = paging.get("cursors", {}) if isinstance(paging, dict) else {}
                cursor = cursors.get("after") if isinstance(cursors, dict) else None
                key = "after"
            if len(data) > room or (len(items) >= 100 and cursor):
                break
            if not cursor:
                complete = True
                break
            if not isinstance(cursor, str) or not cursor or len(cursor) > 2000:
                raise CommunityAPIError("read_failed")
            current[key] = cursor
        return items, complete

    @staticmethod
    def _post_text(platform, payload, account_id):
        """核對自有貼文並抽取六欄需要的原貼文內容。"""

        if platform == "youtube":
            snippet = payload.get("snippet")
            if not isinstance(snippet, dict) or snippet.get("channelId") != account_id:
                raise CommunityAPIError("target_mismatch")
            title = _plain(snippet.get("title"), maximum=1000)
            description = _plain(snippet.get("description", ""), maximum=100_000,
                                 allow_empty=True)
            return title + (("\n\n" + description) if description else "")
        owner = payload.get("from") if platform == "facebook" else payload.get("owner")
        if not isinstance(owner, dict) or str(owner.get("id")) != account_id:
            raise CommunityAPIError("target_mismatch")
        field = {"facebook": "message", "instagram": "caption", "threads": "text"}[platform]
        return _plain(payload.get(field, ""), allow_empty=True)

    def _fetch_post(self, scope, token, base):
        """讀回目標自有貼文，不信任呼叫者提供的正文。"""

        platform, post_id = scope["platform"], scope["post_id"]
        if platform == "youtube":
            result = self.http.request_json(
                "GET", base + "/youtube/v3/videos",
                query={"part": "snippet", "id": post_id}, bearer=token)
            items = _payload(result.payload).get("items")
            if not isinstance(items, list) or len(items) != 1 or items[0].get("id") != post_id:
                raise CommunityAPIError("target_mismatch")
            return self._post_text(platform, items[0], scope["account_id"])
        if platform == "facebook":
            fields = "id,message,from,permalink_url"
        elif platform == "instagram":
            fields = "id,caption,owner,permalink"
        else:
            # Threads 以自有清單核對 owner；不把可讀到的陌生貼文當管理目標。
            items, complete = self._page(
                base + "/me/threads",
                {"fields": "id,text,permalink,owner,username,timestamp", "limit": 50}, token)
            matches = [item for item in items if isinstance(item, dict) and item.get("id") == post_id]
            if len(matches) != 1:
                raise CommunityAPIError("pagination_incomplete" if not complete else "target_mismatch")
            return self._post_text(platform, matches[0], scope["account_id"])
        result = self.http.request_json(
            "GET", f"{base}/{post_id}", query={"fields": fields}, bearer=token)
        payload = _payload(result.payload)
        if str(payload.get("id")) != post_id:
            raise CommunityAPIError("target_mismatch")
        return self._post_text(platform, payload, scope["account_id"])

    @staticmethod
    def _author(platform, payload):
        """取得穩定作者識別與顯示名稱；缺識別時不猜。"""

        if platform == "youtube":
            channel = payload.get("authorChannelId")
            author_id = channel.get("value") if isinstance(channel, dict) else None
            name = payload.get("authorDisplayName")
        elif platform == "facebook":
            author = payload.get("from")
            author_id = str(author.get("id")) if isinstance(author, dict) and author.get("id") else None
            name = author.get("name") if isinstance(author, dict) else None
        elif platform == "instagram":
            author = payload.get("from") or payload.get("user")
            author_id = str(author.get("id")) if isinstance(author, dict) and author.get("id") else None
            name = payload.get("username") or (author.get("username") if isinstance(author, dict) else None)
        else:
            author_id = payload.get("username")
            name = payload.get("username")
        if not isinstance(author_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", author_id):
            raise CommunityAPIError("read_failed")
        return author_id, _plain(name, maximum=1000)

    def _comment_url(self, scope, payload, comment_id):
        """YouTube／Instagram API 無留言 permalink，必須使用已觀察的實際網址。"""

        platform = scope["platform"]
        field = "permalink_url" if platform == "facebook" else "permalink"
        value = payload.get(field) if platform in {"facebook", "threads"} else None
        if value:
            return _safe_url(value, platform)
        observed = scope["url_observations"].get(comment_id)
        return _safe_url(observed, platform) if observed else None

    def _record(self, scope, post_text, comment_id, snippet, *, payload=None):
        """正規化成 community_queue 的本機來源格式。"""

        platform = scope["platform"]
        original = payload if payload is not None else snippet
        author_id, author_name = self._author(platform, snippet)
        text_field = "textOriginal" if platform == "youtube" else (
            "message" if platform == "facebook" else "text")
        text = _plain(snippet.get(text_field), maximum=40_000)
        time_field = "publishedAt" if platform == "youtube" else (
            "created_time" if platform == "facebook" else "timestamp")
        created = _plain(snippet.get(time_field), maximum=100)
        url = self._comment_url(scope, original, comment_id)
        value = {
            "platform": platform, "account_id": scope["account_id"],
            "post_id": scope["post_id"], "comment_id": comment_id,
            "reply_target_id": comment_id, "visitor_id": author_id,
            "visitor_name": author_name, "post_text": post_text,
            "comment_text": text, "comment_url": url,
            "comment_created_at": created, "fetched_at": _now(),
        }
        return value

    def fetch_comments(self, scope):
        """讀自有貼文的頂層訪客留言；缺實際 URL 的項目另列，不送 queue。"""

        scope, _, token, base = self._context(scope)
        platform, post_id = scope["platform"], scope["post_id"]
        post_text = self._fetch_post(scope, token, base)
        if platform == "youtube":
            endpoint = base + "/youtube/v3/commentThreads"
            query = {"part": "snippet", "videoId": post_id, "textFormat": "plainText",
                     "order": "time", "maxResults": 100}
            items, complete = self._page(endpoint, query, token, google=True)
        else:
            edge = "replies" if platform == "threads" else "comments"
            endpoint = f"{base}/{post_id}/{edge}"
            if platform == "facebook":
                fields = "id,message,from,created_time,permalink_url,parent"
                query = {"fields": fields, "filter": "toplevel", "order": "chronological",
                         "limit": 100}
            elif platform == "instagram":
                query = {"fields": "id,text,from,username,timestamp,parent_id", "limit": 100}
            else:
                query = {"fields": self.REPLY_FIELDS, "reverse": False, "limit": 100}
            items, complete = self._page(endpoint, query, token)
        records, missing_urls = [], []
        for item in items:
            if not isinstance(item, dict):
                raise CommunityAPIError("read_failed")
            if platform == "youtube":
                thread = item.get("snippet")
                top = thread.get("topLevelComment") if isinstance(thread, dict) else None
                snippet = top.get("snippet") if isinstance(top, dict) else None
                comment_id = top.get("id") if isinstance(top, dict) else None
                if not isinstance(snippet, dict):
                    raise CommunityAPIError("read_failed")
                _resource_id(comment_id, youtube=True)
                record = self._record(scope, post_text, comment_id, snippet, payload=top)
            else:
                comment_id = str(item.get("id"))
                _resource_id(comment_id)
                if platform == "threads":
                    replied_to = item.get("replied_to")
                    if (not isinstance(replied_to, dict) or str(replied_to.get("id")) != post_id
                            or item.get("is_reply") is not True):
                        raise CommunityAPIError("read_failed")
                    if item.get("is_reply_owned_by_me") is True:
                        continue
                record = self._record(scope, post_text, comment_id, item, payload=item)
            if record["comment_url"] is None:
                missing_urls.append(record)
            else:
                records.append(record)
        return {"records": records, "missing_url_records": missing_urls,
                "complete": complete, "fetched_at": _now()}

    def read_comment(self, scope, comment_id, preserved_url):
        """回覆前重讀同一留言與自有貼文；Threads 從父貼文 replies 找 ID。"""

        scope = dict(self._scope(scope))
        platform = scope["platform"]
        if platform == "youtube":
            _resource_id(comment_id, youtube=True)
        else:
            _resource_id(comment_id)
        scope["url_observations"] = dict(scope["url_observations"], **{comment_id: preserved_url})
        scope, _, token, base = self._context(scope)
        post_text = self._fetch_post(scope, token, base)
        if platform == "youtube":
            result = self.http.request_json(
                "GET", base + "/youtube/v3/comments",
                query={"part": "snippet", "id": comment_id, "textFormat": "plainText"},
                bearer=token)
            items = _payload(result.payload).get("items")
            if not isinstance(items, list) or len(items) != 1 or items[0].get("id") != comment_id:
                raise CommunityAPIError("read_failed")
            return self._record(scope, post_text, comment_id, items[0]["snippet"], payload=items[0])
        if platform == "threads":
            items, complete = self._page(
                f"{base}/{scope['post_id']}/replies",
                {"fields": self.REPLY_FIELDS, "reverse": False, "limit": 100}, token)
            matches = [item for item in items if isinstance(item, dict)
                       and str(item.get("id")) == comment_id]
            if len(matches) != 1:
                raise CommunityAPIError("pagination_incomplete" if not complete else "read_failed")
            return self._record(scope, post_text, comment_id, matches[0], payload=matches[0])
        fields = ("id,message,from,created_time,permalink_url,parent" if platform == "facebook"
                  else "id,text,from,username,timestamp,parent_id")
        result = self.http.request_json(
            "GET", f"{base}/{comment_id}", query={"fields": fields}, bearer=token)
        item = _payload(result.payload)
        if str(item.get("id")) != comment_id:
            raise CommunityAPIError("read_failed")
        return self._record(scope, post_text, comment_id, item, payload=item)

    def own_replies(self, scope, comment_id):
        """完整列舉直接回覆；無法完成分頁就不能宣稱沒有自家回覆。"""

        scope, _, token, base = self._context(scope)
        platform = scope["platform"]
        if platform == "youtube":
            _resource_id(comment_id, youtube=True)
            endpoint = base + "/youtube/v3/comments"
            query = {"part": "snippet", "parentId": comment_id,
                     "textFormat": "plainText", "maxResults": 100}
            items, complete = self._page(endpoint, query, token, google=True)
            owned = []
            for item in items:
                snippet = item.get("snippet") if isinstance(item, dict) else None
                author_id, _ = self._author(platform, snippet or {})
                if author_id == scope["account_id"]:
                    owned.append(str(item.get("id")))
        else:
            _resource_id(comment_id)
            edge = "comments" if platform == "facebook" else "replies"
            endpoint = f"{base}/{comment_id}/{edge}"
            if platform == "facebook":
                fields = "id,message,from,created_time,permalink_url,parent"
            elif platform == "instagram":
                fields = "id,text,from,username,timestamp,parent_id"
            else:
                fields = self.REPLY_FIELDS
            items, complete = self._page(
                endpoint, {"fields": fields, "limit": 100}, token)
            owned = []
            for item in items:
                if not isinstance(item, dict):
                    raise CommunityAPIError("read_failed")
                if platform == "threads":
                    parent = item.get("replied_to")
                    if not isinstance(parent, dict) or str(parent.get("id")) != comment_id:
                        raise CommunityAPIError("read_failed")
                    is_owned = item.get("is_reply_owned_by_me") is True
                else:
                    author_id, _ = self._author(platform, item)
                    is_owned = author_id == scope["account_id"]
                if is_owned:
                    owned.append(str(item.get("id")))
        return {"complete": complete, "owned_reply_ids": owned,
                "none_found_complete": complete and not owned}

    def _write_context(self, grant, stage):
        """將 claim 執行包轉成讀取 scope，再取得同一帳號 Token。"""

        grant = self._grant(grant, stage)
        scope = {
            "platform": grant["platform"], "account_id": grant["account_id"],
            "post_id": grant["post_id"], "approval_ref": grant["approval_ref"],
            "confirmed_read": True, "allow_token_refresh": grant["allow_token_refresh"],
            "url_observations": {},
        }
        scope, config, token, base = self._context(scope)
        return grant, config, token, base

    def create_reply(self, grant):
        """YouTube／Facebook／Instagram 各送一次文字回覆。"""

        grant, _, token, base = self._write_context(grant, "reply_create")
        platform = grant["platform"]
        if platform == "threads":
            raise CommunityAPIError("invalid_request")
        if platform == "youtube":
            result = self.http.request_json(
                "POST", base + "/youtube/v3/comments", query={"part": "snippet"},
                json_body={"snippet": {"parentId": grant["reply_target_id"],
                                       "textOriginal": grant["text"]}},
                bearer=token, mutation=True)
        else:
            edge = "comments" if platform == "facebook" else "replies"
            result = self.http.request_json(
                "POST", f"{base}/{grant['reply_target_id']}/{edge}",
                form={"message": grant["text"]}, bearer=token, mutation=True)
        payload = _payload(result.payload, mutation=True)
        reply_id = payload.get("id")
        _resource_id(str(reply_id), youtube=platform == "youtube")
        return {"reply_id": str(reply_id)}

    def create_threads_container(self, grant):
        """建立一次 Threads 文字回覆容器，不使用 auto_publish_text。"""

        grant, _, token, base = self._write_context(grant, "reply_container")
        if grant["platform"] != "threads":
            raise CommunityAPIError("invalid_request")
        result = self.http.request_json(
            "POST", base + "/me/threads",
            form={"media_type": "TEXT", "text": grant["text"],
                  "reply_to_id": grant["reply_target_id"]},
            bearer=token, mutation=True)
        container_id = str(_payload(result.payload, mutation=True).get("id"))
        _resource_id(container_id)
        return {"container_id": container_id}

    def threads_container_status(self, scope, container_id):
        """只讀同一 Threads 容器狀態，不建立新容器。"""

        _resource_id(container_id)
        scope, _, token, base = self._context(scope)
        if scope["platform"] != "threads":
            raise CommunityAPIError("invalid_request")
        result = self.http.request_json(
            "GET", f"{base}/{container_id}", query={"fields": "id,status"}, bearer=token)
        payload = _payload(result.payload)
        if str(payload.get("id")) != container_id or payload.get("status") not in {
                "IN_PROGRESS", "FINISHED", "PUBLISHED", "ERROR", "EXPIRED"}:
            raise CommunityAPIError("read_failed")
        return {"container_id": container_id, "status": payload["status"]}

    def publish_threads_reply(self, grant, container_id):
        """對已保存的 Threads 容器送一次 publish。"""

        _resource_id(container_id)
        grant, _, token, base = self._write_context(grant, "reply_publish")
        if grant["platform"] != "threads":
            raise CommunityAPIError("invalid_request")
        result = self.http.request_json(
            "POST", base + "/me/threads_publish", form={"creation_id": container_id},
            bearer=token, mutation=True)
        reply_id = str(_payload(result.payload, mutation=True).get("id"))
        _resource_id(reply_id)
        return {"reply_id": reply_id}

    def read_reply(self, scope, reply_target_id, reply_id, preserved_url=None):
        """獨立讀回正式回覆；YouTube／IG 的 permalink 留給受控 UI 補證。"""

        scope = self._scope(scope)
        platform = scope["platform"]
        _resource_id(reply_target_id, youtube=platform == "youtube")
        _resource_id(reply_id, youtube=platform == "youtube")
        scope, _, token, base = self._context(scope)
        if platform == "youtube":
            result = self.http.request_json(
                "GET", base + "/youtube/v3/comments",
                query={"part": "snippet", "id": reply_id, "textFormat": "plainText"},
                bearer=token)
            items = _payload(result.payload).get("items")
            if not isinstance(items, list) or len(items) != 1 or items[0].get("id") != reply_id:
                raise CommunityAPIError("read_failed")
            item = items[0]["snippet"]
            parent_id, text, timestamp = item.get("parentId"), item.get("textOriginal"), item.get("publishedAt")
            author_id, _ = self._author(platform, item)
            url = _safe_url(preserved_url, platform) if preserved_url else None
            owned = author_id == scope["account_id"]
        elif platform == "threads":
            items, complete = self._page(
                f"{base}/{reply_target_id}/replies",
                {"fields": self.REPLY_FIELDS, "reverse": False, "limit": 100}, token)
            matches = [item for item in items if isinstance(item, dict)
                       and str(item.get("id")) == reply_id]
            if len(matches) != 1:
                raise CommunityAPIError("pagination_incomplete" if not complete else "read_failed")
            item = matches[0]
            parent = item.get("replied_to")
            parent_id = str(parent.get("id")) if isinstance(parent, dict) else None
            text, timestamp = item.get("text"), item.get("timestamp")
            url = _safe_url(item.get("permalink"), platform)
            owned = item.get("is_reply_owned_by_me") is True
        else:
            fields = ("id,message,from,created_time,permalink_url,parent" if platform == "facebook"
                      else "id,text,from,username,timestamp,parent_id")
            result = self.http.request_json(
                "GET", f"{base}/{reply_id}", query={"fields": fields}, bearer=token)
            item = _payload(result.payload)
            if str(item.get("id")) != reply_id:
                raise CommunityAPIError("read_failed")
            if platform == "facebook":
                parent = item.get("parent")
                parent_id = str(parent.get("id")) if isinstance(parent, dict) else None
                text, timestamp = item.get("message"), item.get("created_time")
                url = _safe_url(item.get("permalink_url"), platform)
            else:
                parent_id = str(item.get("parent_id")) if item.get("parent_id") else None
                text, timestamp = item.get("text"), item.get("timestamp")
                url = _safe_url(preserved_url, platform) if preserved_url else None
            author_id, _ = self._author(platform, item)
            owned = author_id == scope["account_id"]
        if parent_id != reply_target_id:
            raise CommunityAPIError("readback_incomplete")
        return {"reply_id": reply_id, "reply_target_id": parent_id,
                "text": _plain(text, maximum=10_000),
                "platform_time": _plain(timestamp, maximum=100),
                "author_owned": owned, "url": url, "observed_at": _now()}

