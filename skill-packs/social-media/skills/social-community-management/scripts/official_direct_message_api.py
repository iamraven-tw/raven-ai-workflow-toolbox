"""Facebook Messenger 與 Instagram 私訊的受限官方 API adapter。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import http.client
import importlib
import json
from pathlib import Path
import re
import ssl
import sys
from urllib.parse import urlencode, urlsplit


class DirectMessageAPIError(RuntimeError):
    """固定錯誤種類，避免私訊、姓名或 Token 出現在錯誤訊息。"""

    ALLOWED = {
        "authorization_required", "invalid_request", "adapter_unavailable",
        "reauth_required", "permission_mismatch", "target_mismatch",
        "rate_limited", "rejected", "read_failed", "remote_result_unknown",
        "pagination_incomplete", "message_window_expired",
        "conversation_not_replyable", "unsupported_message",
        "readback_incomplete", "ambiguous_readback",
    }

    def __init__(self, kind):
        self.kind = kind if kind in self.ALLOWED else "read_failed"
        super().__init__(self.kind)


class HTTPResult:
    """只在可信程序記憶體保留必要 JSON。"""

    __slots__ = ("status", "payload", "headers")

    def __init__(self, status, payload, headers=None):
        self.status = status
        self.payload = payload
        self.headers = {str(key).lower(): str(value)
                        for key, value in (headers or {}).items()}


def _resource_id(value):
    """限制 Meta 資源識別，不能注入路徑或查詢字串。"""

    if type(value) not in {str, int}:
        raise DirectMessageAPIError("invalid_request")
    value = str(value)
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,500}", value):
        raise DirectMessageAPIError("invalid_request")
    return value


def _plain(value, *, maximum=40_000, allow_empty=False):
    """不改寫外部文字，只拒絕型別、大小與控制字元。"""

    if (not isinstance(value, str) or len(value) > maximum
            or (not allow_empty and not value.strip())
            or any(ord(char) < 32 and char not in "\n\r\t" for char in value)):
        raise DirectMessageAPIError("unsupported_message")
    return value


def _instant(value):
    """解析平台時間並要求時區。"""

    if not isinstance(value, str):
        raise DirectMessageAPIError("read_failed")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise DirectMessageAPIError("read_failed") from None
    if parsed.tzinfo is None:
        raise DirectMessageAPIError("read_failed")
    return parsed.astimezone(timezone.utc)


def _payload(value, *, mutation=False):
    """空回應不能被推定成成功。"""

    if not isinstance(value, dict):
        raise DirectMessageAPIError("remote_result_unknown" if mutation else "read_failed")
    return value


def _classify(status, value, *, mutation):
    """將 Meta 錯誤收斂為固定狀態；寫入不自動重試。"""

    error = value.get("error") if isinstance(value, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    if status == 401 or code in {102, 190}:
        raise DirectMessageAPIError("reauth_required")
    if status == 429:
        raise DirectMessageAPIError("rate_limited")
    if status == 403 or code in {10, 200}:
        raise DirectMessageAPIError("permission_mismatch")
    if not 200 <= status < 300 or error:
        if mutation and (300 <= status < 400 or status >= 500):
            raise DirectMessageAPIError("remote_result_unknown")
        raise DirectMessageAPIError("rejected" if mutation else "read_failed")


class OfficialDirectMessageHTTP:
    """只連兩個 Meta 官方 Graph 主機的對話、訊息與傳送端點。"""

    MAX_RESPONSE = 2 * 1024 * 1024

    @staticmethod
    def _allowed(method, endpoint):
        parsed = urlsplit(endpoint)
        if (parsed.scheme != "https" or parsed.netloc not in {
                "graph.facebook.com", "graph.instagram.com"}
                or parsed.query or parsed.fragment or parsed.username or parsed.password):
            return False
        identifier = r"[A-Za-z0-9_.-]{1,500}"
        base = rf"/v[0-9]+\.0/{identifier}"
        if method == "GET":
            return bool(re.fullmatch(base + r"(?:/conversations)?", parsed.path))
        return method == "POST" and bool(re.fullmatch(base + r"/messages", parsed.path))

    @staticmethod
    def _bearer(value):
        """Token 只放 Authorization header，拒絕換行。"""

        if not isinstance(value, str) or not value or "\r" in value or "\n" in value:
            raise DirectMessageAPIError("authorization_required")
        return value

    @staticmethod
    def _value(value):
        """查詢參數只接受簡單值。"""

        if isinstance(value, bool):
            return "true" if value else "false"
        if type(value) in {str, int}:
            return str(value)
        raise DirectMessageAPIError("invalid_request")

    def request_json(self, method, endpoint, *, query=None, json_body=None,
                     bearer=None, mutation=False):
        """送出單次請求；不跟隨重新導向、不接受 Token 查詢參數。"""

        method = str(method).upper()
        if method not in {"GET", "POST"} or not self._allowed(method, endpoint):
            raise DirectMessageAPIError("invalid_request")
        if query is not None and (not isinstance(query, dict)
                or any(str(key).lower() in {
                    "access_token", "token", "authorization"} for key in query)):
            raise DirectMessageAPIError("invalid_request")
        headers = {
            "Accept": "application/json", "Cache-Control": "no-store",
            "Authorization": "Bearer " + self._bearer(bearer),
        }
        body = None
        if json_body is not None:
            if method != "POST" or not isinstance(json_body, dict):
                raise DirectMessageAPIError("invalid_request")
            body = json.dumps(json_body, ensure_ascii=False,
                              separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=UTF-8"
            headers["Content-Length"] = str(len(body))
        parsed = urlsplit(endpoint)
        path = parsed.path
        if query:
            path += "?" + urlencode({key: self._value(value)
                                     for key, value in query.items()})
        connection = http.client.HTTPSConnection(
            parsed.hostname, timeout=60, context=ssl.create_default_context())
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read(self.MAX_RESPONSE + 1)
            if len(raw) > self.MAX_RESPONSE:
                raise DirectMessageAPIError(
                    "remote_result_unknown" if mutation else "read_failed")
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                value = None
            _classify(response.status, value, mutation=mutation)
            return HTTPResult(response.status, value, dict(response.getheaders()))
        except DirectMessageAPIError:
            raise
        except Exception:
            raise DirectMessageAPIError(
                "remote_result_unknown" if mutation else "read_failed") from None
        finally:
            connection.close()


def _default_runtime(workspace, platform, connection):
    """從 setup 技能載入 Runtime，秘密只在同一程序記憶體出現。"""

    scripts = Path(__file__).resolve().parents[2] / "social-media-setup" / "scripts"
    if not scripts.is_dir():
        raise DirectMessageAPIError("adapter_unavailable")
    added = str(scripts) not in sys.path
    if added:
        sys.path.insert(0, str(scripts))
    try:
        module = importlib.import_module("oauth_runtime")
        return module.Runtime(workspace, platform, connection=connection)
    except DirectMessageAPIError:
        raise
    except Exception:
        raise DirectMessageAPIError("adapter_unavailable") from None
    finally:
        if added and sys.path and sys.path[0] == str(scripts):
            sys.path.pop(0)


class OfficialDirectMessageAdapter:
    """按需同步可回覆對話、傳送一次純文字並獨立讀回。"""

    READ_KEYS = {
        "platform", "account_id", "approval_ref", "confirmed_read",
        "allow_token_refresh", "max_conversations",
    }
    WRITE_KEYS = {
        "platform", "account_id", "conversation_id", "recipient_id", "text",
        "approval_ref", "transaction_status", "stage", "allow_token_refresh",
    }
    MESSAGE_FIELDS = "id,created_time,from,to,message"

    def __init__(self, workspace, *, connection="main", runtime_factory=None,
                 http_transport=None, clock=None):
        self.workspace = Path(workspace).expanduser().resolve()
        if (not self.workspace.is_dir()
                or not re.fullmatch(r"[a-z][a-z0-9-]{0,19}", connection)):
            raise DirectMessageAPIError("invalid_request")
        self.connection = connection
        self.runtime_factory = runtime_factory or _default_runtime
        self.http = http_transport or OfficialDirectMessageHTTP()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def _now(self):
        """取得可測試的 UTC 觀測時間。"""

        value = self.clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise DirectMessageAPIError("adapter_unavailable")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _scope(scope):
        """對話讀取必須綁定使用者核准的平台、帳號與批次上限。"""

        if not isinstance(scope, dict) or set(scope) != OfficialDirectMessageAdapter.READ_KEYS:
            raise DirectMessageAPIError("authorization_required")
        if (scope.get("platform") not in {"facebook", "instagram"}
                or scope.get("confirmed_read") is not True
                or scope.get("allow_token_refresh") not in {True, False}
                or type(scope.get("max_conversations")) is not int
                or not 1 <= scope["max_conversations"] <= 20
                or not isinstance(scope.get("approval_ref"), str)
                or not scope["approval_ref"].strip()
                or len(scope["approval_ref"]) > 300):
            raise DirectMessageAPIError("authorization_required")
        _resource_id(scope["account_id"])
        return scope

    @staticmethod
    def _grant(grant):
        """傳送只接受 direct_message_queue 已 begin 並 claim 的最小執行包。"""

        if not isinstance(grant, dict) or set(grant) != OfficialDirectMessageAdapter.WRITE_KEYS:
            raise DirectMessageAPIError("authorization_required")
        if (grant.get("platform") not in {"facebook", "instagram"}
                or grant.get("transaction_status") != "in_flight"
                or grant.get("stage") != "message_send"
                or grant.get("allow_token_refresh") not in {True, False}
                or not isinstance(grant.get("approval_ref"), str)
                or not grant["approval_ref"]):
            raise DirectMessageAPIError("authorization_required")
        for field in ("account_id", "conversation_id", "recipient_id"):
            _resource_id(grant[field])
        _plain(grant["text"], maximum=10_000)
        return grant

    def _runtime_context(self, platform, account_id, allow_refresh):
        """核對 setup 目標、登入路徑與訊息 permission 後取得 Token。"""

        try:
            runtime = self.runtime_factory(self.workspace, platform, self.connection)
            config = runtime.config()
            if str(config.get("target_id")) != account_id:
                raise DirectMessageAPIError("target_mismatch")
            route = config.get("login_route")
            scopes = set(config.get("scopes", []))
            required = {
                "facebook_pages": {"pages_messaging", "pages_manage_metadata",
                                   "pages_read_engagement"},
                "instagram_login": {"instagram_business_basic",
                                    "instagram_business_manage_messages"},
                "instagram_facebook_login": {"instagram_basic",
                                             "instagram_manage_messages",
                                             "pages_manage_metadata"},
            }.get(route)
            if required is None or not required.issubset(scopes):
                raise DirectMessageAPIError("permission_mismatch")
            token = runtime.access(confirmed_read=True, allow_refresh=allow_refresh)
            details = runtime.resource_context(confirmed_read=True)
            if (details.get("target_id") != account_id
                    or details.get("login_route") != route
                    or details.get("graph_version") != config.get("graph_version")):
                raise DirectMessageAPIError("target_mismatch")
            if not isinstance(token, str) or not token:
                raise DirectMessageAPIError("reauth_required")
            version = config.get("graph_version")
            if not isinstance(version, str) or not re.fullmatch(r"v[0-9]+\.0", version):
                raise DirectMessageAPIError("adapter_unavailable")
            if route == "instagram_login":
                host, conversation_owner = "https://graph.instagram.com", account_id
            elif route == "instagram_facebook_login":
                host = "https://graph.facebook.com"
                conversation_owner = _resource_id(details.get("page_id"))
            else:
                host, conversation_owner = "https://graph.facebook.com", account_id
            return {
                "platform": platform, "account_id": account_id, "route": route,
                "token": token, "base": f"{host}/{version}",
                "conversation_owner_id": conversation_owner,
                "message_actor_id": account_id,
            }
        except DirectMessageAPIError:
            raise
        except Exception as error:
            mapping = {
                "authorization_required": "authorization_required",
                "reauth_required": "reauth_required", "refresh_required": "reauth_required",
                "permission_mismatch": "permission_mismatch",
                "target_mismatch": "target_mismatch", "rate_limited": "rate_limited",
            }
            raise DirectMessageAPIError(
                mapping.get(getattr(error, "kind", None), "adapter_unavailable")) from None

    def _context(self, scope):
        """建立只供目前呼叫使用的固定端點上下文。"""

        scope = self._scope(scope)
        context = self._runtime_context(
            scope["platform"], scope["account_id"], scope["allow_token_refresh"])
        return scope, context

    def verify_access(self, scope):
        """在本機 claim 前驗證既有連線，只回傳非敏感摘要。"""

        scope, context = self._context(scope)
        return {"platform": scope["platform"], "account_id": scope["account_id"],
                "login_route": context["route"], "ready": True}

    def _page(self, endpoint, query, token, maximum):
        """最多五頁且不跟隨 paging.next；有剩餘資料即標不完整。"""

        values, current, complete = [], dict(query), False
        for _ in range(5):
            payload = _payload(self.http.request_json(
                "GET", endpoint, query=current, bearer=token).payload)
            rows = payload.get("data")
            if not isinstance(rows, list):
                raise DirectMessageAPIError("read_failed")
            room = maximum - len(values)
            values.extend(rows[:room])
            paging = payload.get("paging", {})
            cursors = paging.get("cursors", {}) if isinstance(paging, dict) else {}
            cursor = cursors.get("after") if isinstance(cursors, dict) else None
            if len(rows) > room or (len(values) >= maximum and cursor):
                break
            if not cursor:
                complete = True
                break
            if not isinstance(cursor, str) or not cursor or len(cursor) > 2000:
                raise DirectMessageAPIError("read_failed")
            current["after"] = cursor
        return values, complete

    def _conversation_ids(self, scope, context):
        """按需列出使用者核准上限內的對話。"""

        query = {"fields": "id,updated_time", "limit": scope["max_conversations"]}
        if scope["platform"] == "instagram":
            query["platform"] = "instagram"
        rows, complete = self._page(
            f"{context['base']}/{context['conversation_owner_id']}/conversations",
            query, context["token"], scope["max_conversations"])
        identifiers = []
        for row in rows:
            if not isinstance(row, dict):
                raise DirectMessageAPIError("read_failed")
            identifiers.append(_resource_id(row.get("id")))
        if len(identifiers) != len(set(identifiers)):
            raise DirectMessageAPIError("read_failed")
        return identifiers, complete

    def _message_ids(self, context, conversation_id):
        """取得官方可讀的最近訊息 ID；MVP 最多處理最近 20 則。"""

        _resource_id(conversation_id)
        payload = _payload(self.http.request_json(
            "GET", f"{context['base']}/{conversation_id}",
            query={"fields": "messages"}, bearer=context["token"]).payload)
        messages = payload.get("messages")
        rows = messages.get("data") if isinstance(messages, dict) else None
        if not isinstance(rows, list) or not rows:
            raise DirectMessageAPIError("conversation_not_replyable")
        values = []
        for row in rows[:20]:
            if not isinstance(row, dict):
                raise DirectMessageAPIError("read_failed")
            values.append(_resource_id(row.get("id")))
        if len(values) != len(set(values)):
            raise DirectMessageAPIError("read_failed")
        return values

    def _detail(self, context, message_id):
        """逐則讀取寄件者、收件者、完整純文字與平台時間。"""

        message_id = _resource_id(message_id)
        payload = _payload(self.http.request_json(
            "GET", f"{context['base']}/{message_id}",
            query={"fields": self.MESSAGE_FIELDS}, bearer=context["token"]).payload)
        if _resource_id(payload.get("id")) != message_id:
            raise DirectMessageAPIError("read_failed")
        sender = payload.get("from")
        recipients = payload.get("to")
        recipient_rows = recipients.get("data") if isinstance(recipients, dict) else None
        if (not isinstance(sender, dict) or not isinstance(recipient_rows, list)
                or len(recipient_rows) != 1 or not isinstance(recipient_rows[0], dict)):
            raise DirectMessageAPIError("unsupported_message")
        sender_id = _resource_id(sender.get("id"))
        recipient_id = _resource_id(recipient_rows[0].get("id"))
        sender_name = sender.get("username") or sender.get("name") or ""
        if not isinstance(sender_name, str) or len(sender_name) > 1000:
            raise DirectMessageAPIError("unsupported_message")
        return {
            "message_id": message_id, "sender_id": sender_id,
            "sender_name": sender_name, "recipient_id": recipient_id,
            "text": _plain(payload.get("message")),
            "created_at": _plain(payload.get("created_time"), maximum=100),
        }

    @staticmethod
    def _direction(detail, account_id, visitor_id=None):
        """只接受帳號與單一訪客之間的雙向對話，不支援群組。"""

        if detail["sender_id"] == account_id:
            if visitor_id is not None and detail["recipient_id"] != visitor_id:
                raise DirectMessageAPIError("unsupported_message")
            return "outbound"
        if detail["recipient_id"] != account_id:
            raise DirectMessageAPIError("unsupported_message")
        if visitor_id is not None and detail["sender_id"] != visitor_id:
            raise DirectMessageAPIError("unsupported_message")
        return "inbound"

    def _conversation_record(self, context, conversation_id):
        """只讓最新一則是訪客純文字、且仍在 24 小時內的對話進隔離。"""

        message_ids = self._message_ids(context, conversation_id)
        details = [self._detail(context, message_id) for message_id in message_ids]
        details.sort(key=lambda item: _instant(item["created_at"]), reverse=True)
        newest = details[0]
        direction = self._direction(newest, context["account_id"])
        if direction != "inbound":
            return "latest_outbound", None
        visitor_id = newest["sender_id"]
        rows = []
        for detail in details:
            direction = self._direction(detail, context["account_id"], visitor_id)
            rows.append({
                "message_id": detail["message_id"], "sender_id": detail["sender_id"],
                "sender_name": detail["sender_name"], "direction": direction,
                "text": detail["text"], "created_at": detail["created_at"],
            })
        observed = self._now()
        age = observed - _instant(newest["created_at"])
        if age < timedelta(0) or age > timedelta(hours=24):
            return "expired", None
        record = {
            "platform": context["platform"], "account_id": context["account_id"],
            "conversation_id": conversation_id, "visitor_id": visitor_id,
            "visitor_name": newest["sender_name"], "message_id": newest["message_id"],
            "message_text": newest["text"], "message_created_at": newest["created_at"],
            "context": rows, "fetched_at": observed.isoformat(),
        }
        return "eligible", record

    def fetch_conversations(self, scope):
        """按需同步對話，分開回報可回覆、過期、已回覆及不支援。"""

        scope, context = self._context(scope)
        identifiers, complete = self._conversation_ids(scope, context)
        records = []
        counts = {"expired": 0, "latest_outbound": 0, "unsupported": 0}
        for conversation_id in identifiers:
            try:
                state, record = self._conversation_record(context, conversation_id)
            except DirectMessageAPIError as error:
                if error.kind not in {"conversation_not_replyable", "unsupported_message"}:
                    raise
                counts["unsupported"] += 1
                continue
            if state == "eligible":
                records.append(record)
            else:
                counts[state] += 1
        return {"records": records, **counts, "complete": complete,
                "fetched_at": self._now().isoformat()}

    def read_conversation(self, scope, conversation_id):
        """傳送前重讀同一對話，最新訊息與 24 小時資格都必須仍相同。"""

        _, context = self._context(scope)
        conversation_id = _resource_id(conversation_id)
        state, record = self._conversation_record(context, conversation_id)
        if state == "expired":
            raise DirectMessageAPIError("message_window_expired")
        if state != "eligible":
            raise DirectMessageAPIError("conversation_not_replyable")
        return record

    def _write_context(self, grant):
        """從單次 claim 重新驗證相同 setup 連線。"""

        grant = self._grant(grant)
        context = self._runtime_context(
            grant["platform"], grant["account_id"], grant["allow_token_refresh"])
        return grant, context

    def send_text(self, grant):
        """傳送一次純文字；沒有 HUMAN_AGENT、附件、範本或 Quick Replies。"""

        grant, context = self._write_context(grant)
        body = {"recipient": {"id": grant["recipient_id"]},
                "message": {"text": grant["text"]}}
        if grant["platform"] == "facebook":
            body["messaging_type"] = "RESPONSE"
        payload = _payload(self.http.request_json(
            "POST", f"{context['base']}/{context['message_actor_id']}/messages",
            json_body=body, bearer=context["token"], mutation=True).payload,
            mutation=True)
        recipient_id = _resource_id(payload.get("recipient_id"))
        message_id = _resource_id(payload.get("message_id"))
        if recipient_id != grant["recipient_id"]:
            raise DirectMessageAPIError("remote_result_unknown")
        return {"recipient_id": recipient_id, "message_id": message_id}

    def _readback(self, context, conversation_id, recipient_id, message_id):
        """核對訊息仍屬同一對話、由自有帳號送給指定訪客。"""

        message_ids = self._message_ids(context, conversation_id)
        if message_id not in message_ids:
            raise DirectMessageAPIError("readback_incomplete")
        detail = self._detail(context, message_id)
        if (self._direction(detail, context["account_id"], recipient_id) != "outbound"
                or detail["recipient_id"] != recipient_id):
            raise DirectMessageAPIError("readback_incomplete")
        return {
            "message_id": message_id, "conversation_id": conversation_id,
            "recipient_id": recipient_id, "text": detail["text"],
            "platform_time": detail["created_at"],
            "observed_at": self._now().isoformat(), "sender_owned": True,
            "recipient_matches": True, "conversation_matches": True,
        }

    def read_message(self, scope, conversation_id, recipient_id, message_id):
        """取得已 checkpoint 訊息的獨立讀回。"""

        _, context = self._context(scope)
        for value in (conversation_id, recipient_id, message_id):
            _resource_id(value)
        return self._readback(context, conversation_id, recipient_id, message_id)

    def find_sent_message(self, scope, conversation_id, recipient_id, text, after):
        """結果不明時只讀查找唯一吻合訊息；找不到或多筆都不重送。"""

        _, context = self._context(scope)
        for value in (conversation_id, recipient_id):
            _resource_id(value)
        _plain(text, maximum=10_000)
        after_time = _instant(after)
        matches = []
        for message_id in self._message_ids(context, conversation_id):
            detail = self._detail(context, message_id)
            try:
                direction = self._direction(detail, context["account_id"], recipient_id)
            except DirectMessageAPIError:
                continue
            if (direction == "outbound" and detail["recipient_id"] == recipient_id
                    and detail["text"] == text and _instant(detail["created_at"]) >= after_time):
                matches.append(message_id)
        if len(matches) != 1:
            raise DirectMessageAPIError("ambiguous_readback")
        return self._readback(
            context, conversation_id, recipient_id, matches[0])
