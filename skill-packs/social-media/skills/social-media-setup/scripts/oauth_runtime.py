"""Facebook Pages 與 YouTube OAuth 交換、讀回及 Token 生命週期。"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

import credential_store as vault
from oauth_http import OAuthError, OfficialHTTP


ROUTES = {"facebook", "youtube"}
STATES = {"not_configured", "configured", "authorizing", "exchanging", "refreshing", "saving", "ready",
          "reauth_required", "permission_mismatch", "target_mismatch", "expired",
          "invalid_callback", "cancelled", "timeout", "read_failed", "rate_limited",
          "remote_result_unknown", "storage_incomplete", "refresh_required"}


def validate_config(config):
    """所有私人連線中繼資料只進原生儲存；不接受自訂 Token endpoint。"""
    required = {"platform", "client_id", "target_id", "scopes", "secret_ref",
                "graph_version", "redirect_uri", "callback_port", "callback_mode",
                "tls_cert", "tls_key"}
    if not isinstance(config, dict) or set(config) != required or config["platform"] not in ROUTES:
        raise OAuthError("invalid_configuration")
    if any(not isinstance(config[k], str) for k in required - {"scopes", "callback_port"}):
        raise OAuthError("invalid_configuration")
    for key in ("client_id", "target_id", "secret_ref"):
        if not isinstance(config[key], str) or not config[key] or re.search(r"[\s\x00-\x1f]", config[key]):
            raise OAuthError("invalid_configuration")
    vault.validate_reference(config["platform"], config["secret_ref"])
    scopes = config["scopes"]
    if (not isinstance(scopes, list) or not scopes
            or any(not isinstance(s, str) or not re.fullmatch(r"[a-zA-Z0-9._:/-]+", s) for s in scopes)
            or len(scopes) != len(set(scopes))):
        raise OAuthError("invalid_configuration")
    if type(config["callback_port"]) is not int or not 0 <= config["callback_port"] <= 65535:
        raise OAuthError("invalid_configuration")
    if config["platform"] == "facebook":
        try:
            uri = urlsplit(config["redirect_uri"])
            uri.port
        except ValueError:
            raise OAuthError("invalid_configuration") from None
        if (uri.scheme != "https" or not uri.hostname or uri.username or uri.password
                or uri.query or uri.fragment or uri.path != "/oauth/callback"
                or config["callback_mode"] not in {"https_local", "https_proxy"}
                or not config["callback_port"]
                or not re.fullmatch(r"v[0-9]+\.0", config["graph_version"])
                or not config["client_id"].isdigit() or not config["target_id"].isdigit()):
            raise OAuthError("invalid_configuration")
        if "pages_show_list" not in scopes:
            raise OAuthError("invalid_configuration")
        if config["callback_mode"] == "https_local" and not (config["tls_cert"] and config["tls_key"]):
            raise OAuthError("invalid_configuration")
    elif (config["callback_mode"] != "loopback" or config["redirect_uri"] or config["graph_version"]
          or config["tls_cert"] or config["tls_key"]
          or "https://www.googleapis.com/auth/youtube.readonly" not in scopes):
        raise OAuthError("invalid_configuration")
    return config


class Runtime:
    """同一工作區序列化執行，秘密永不出現在 repr 或狀態回報。"""

    def __init__(self, workspace, platform, connection="main", *, backend=None, transport=None, clock=time.time):
        if platform not in ROUTES or not re.fullmatch(r"[a-z][a-z0-9-]{0,19}", connection):
            raise OAuthError("invalid_configuration")
        self.workspace = vault.resolve_workspace(workspace)
        self.platform, self.connection = platform, connection
        self.backend = backend or vault.detect_backend()
        self.http, self.clock = transport or OfficialHTTP(), clock
        self.prefix = f"oauth-{connection}"

    def lock(self):
        """與單筆原生儲存使用不同鎖，避免巢狀互鎖。"""
        return vault.workspace_lock(self.workspace, "oauth-runtime.lock")

    def _path(self):
        """狀態路徑固定且每層拒絕 symlink，包括失效連結。"""
        current = self.workspace
        for part in (".local", "social-media", "oauth", f"{self.platform}-{self.connection}.json"):
            current /= part
            if current.is_symlink():
                raise OAuthError("invalid_configuration")
        return current

    def status(self):
        """只讀非敏感狀態，不把程序中斷推定為成功。"""
        path = self._path()
        if not path.exists():
            return {"schema_version": 1, "platform": self.platform, "connection": self.connection,
                    "status": "not_configured", "revision": None, "parts": 0, "attempt": None,
                    "updated_at": 0, "contains_credentials": False}
        data = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(data, dict) or set(data) != {"schema_version", "platform", "connection", "status", "revision",
                         "parts", "updated_at", "contains_credentials", "attempt"}
                or data["schema_version"] != 1 or data["platform"] != self.platform
                or data["connection"] != self.connection or data["status"] not in STATES
                or data["contains_credentials"] is not False
                or type(data["updated_at"]) is not int or type(data["parts"]) is not int
                or not 0 <= data["parts"] <= 128
                or any(data[k] is not None and (not isinstance(data[k], str) or not re.fullmatch(r"[0-9a-f]{16}", data[k])) for k in ("revision", "attempt"))):
            raise OAuthError("invalid_configuration")
        return data

    def mark(self, state, *, revision=None, parts=None, attempt=None):
        """先寫作業狀態再送請求；原子替換且不保存 Token 指紋或授權碼。"""
        if state not in STATES:
            raise OAuthError("invalid_configuration")
        data = self.status()
        data.update(status=state, updated_at=int(self.clock()))
        if revision is not None:
            data.update(revision=revision, parts=parts)
        if attempt is not None:
            data["attempt"] = attempt
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary = tempfile.mkstemp(prefix=".oauth-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def _load(self, name):
        """秘密只回到受信任呼叫程式的記憶體。"""
        return vault.load_secret(self.workspace, self.platform, name, backend=self.backend)

    def _store(self, name, value, replace=False):
        """沿用原生寫入、讀回比對與未完成參照的保護。"""
        vault.store_secret(self.workspace, self.platform, name, value,
                           source="oauth-callback", replace=replace, backend=self.backend)

    def configure(self, config, *, confirmed=False, replace=False):
        """預覽確認後才保存私人連線設定；不碰任何外部帳號。"""
        validate_config(config)
        if not confirmed or config["platform"] != self.platform:
            raise OAuthError("authorization_required")
        with self.lock():
            if self.status()["status"] in {"exchanging", "refreshing", "saving", "remote_result_unknown"}:
                raise OAuthError("recovery_required")
            self._store(self.prefix + "-config", json.dumps(config, separators=(",", ":")), replace)
            self.mark("configured")
        return self.status()

    def config(self):
        """讀取加密的私人設定，不對外輸出。"""
        return validate_config(json.loads(self._load(self.prefix + "-config")))

    def _save_bundle(self, bundle):
        """可變長 Token 分段留在原生憑證庫，避免 Windows 單筆大小限制。"""
        text = json.dumps(bundle, ensure_ascii=True, separators=(",", ":"))
        chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
        if len(chunks) > 128:
            raise OAuthError("storage_incomplete")
        revision = secrets.token_hex(8)
        self.mark("saving", revision=revision, parts=len(chunks))
        for index, chunk in enumerate(chunks):
            self._store(f"{self.prefix}-{revision}-p{index}", chunk)

    def _bundle(self):
        """只組合目前候選世代；缺件或未完成原生寫入就停止。"""
        state = self.status()
        if not state["revision"] or not state["parts"]:
            raise OAuthError("reauth_required")
        try:
            text = "".join(self._load(f"{self.prefix}-{state['revision']}-p{i}") for i in range(state["parts"]))
            data = json.loads(text)
            if not isinstance(data, dict) or data.get("platform") != self.platform:
                raise ValueError()
            return data
        except Exception:
            raise OAuthError("storage_incomplete") from None

    def _graph(self, config, path, token, query=None):
        """Facebook 正式 GET 與時間戳 appsecret proof；URL 只在程序內傳輸。"""
        stamp = int(self.clock())
        proof = hmac.new(self._load(config["secret_ref"]).encode(), f"{token}|{stamp}".encode(), hashlib.sha256).hexdigest()
        params = dict(query or {}, access_token=token, appsecret_proof=proof, appsecret_time=stamp)
        return self.http.request("GET", f"https://graph.facebook.com/{config['graph_version']}/{path}", query=params)

    def _debug(self, config, token, expected_type):
        """驗證 App、類型、期限及使用者；Page 身分另外以 /me 讀回核對。"""
        app_token = config["client_id"] + "|" + self._load(config["secret_ref"])
        data = self._graph(config, "debug_token", app_token, {"input_token": token}).get("data", {})
        if data.get("is_valid") is not True:
            raise OAuthError("reauth_required")
        if str(data.get("app_id")) != config["client_id"] or data.get("type") != expected_type:
            raise OAuthError("target_mismatch")
        for key in ("expires_at", "data_access_expires_at"):
            expiry = data.get(key)
            if expiry is not None and (type(expiry) is not int or expiry < 0):
                raise OAuthError("read_failed")
            if expiry and expiry <= self.clock():
                raise OAuthError("expired")
        if type(data.get("expires_at")) is not int:
            raise OAuthError("read_failed")
        return data

    def _rows(self, config, path, token, query=None):
        """只沿固定端點使用 cursor；拒絕不完整、循環或超過上限分頁。"""
        query, seen, rows = dict(query or {}), set(), []
        for _ in range(100):
            payload = self._graph(config, path, token, query)
            data = payload.get("data")
            if not isinstance(data, list) or any(not isinstance(x, dict) for x in data):
                raise OAuthError("read_failed")
            rows.extend(data)
            paging = payload.get("paging", {})
            if not paging.get("next"):
                return rows
            cursor = paging.get("cursors", {}).get("after")
            if not isinstance(cursor, str) or not cursor or cursor in seen:
                raise OAuthError("read_failed")
            seen.add(cursor)
            query["after"] = cursor
        raise OAuthError("read_failed")

    def _verify(self, config, bundle):
        """只做身分及權限讀回，沒有發布、留言或成效寫入。"""
        if self.platform == "facebook":
            info = self._debug(config, bundle["access_token"], "PAGE")
            expected = set(config["scopes"]) | {"public_profile"}
            if set(info.get("scopes", [])) != expected:
                raise OAuthError("permission_mismatch")
            actual = self._graph(config, "me", bundle["access_token"], {"fields": "id,name"})
            if str(actual.get("id")) != config["target_id"] or not actual.get("name"):
                raise OAuthError("target_mismatch")
        else:
            if bundle["expires_at"] <= self.clock():
                raise OAuthError("expired")
            if set(bundle["scopes"]) != set(config["scopes"]):
                raise OAuthError("permission_mismatch")
            query, seen, matches = {"part": "id,snippet", "mine": "true"}, set(), []
            for _ in range(100):
                page = self.http.request("GET", "https://www.googleapis.com/youtube/v3/channels",
                                         query=query, bearer=bundle["access_token"])
                items = page.get("items")
                if not isinstance(items, list) or any(not isinstance(x, dict) for x in items):
                    raise OAuthError("read_failed")
                matches.extend(x for x in items if x.get("id") == config["target_id"] and x.get("snippet", {}).get("title"))
                cursor = page.get("nextPageToken")
                if not cursor:
                    break
                if not isinstance(cursor, str) or cursor in seen:
                    raise OAuthError("read_failed")
                seen.add(cursor)
                query["pageToken"] = cursor
            else:
                raise OAuthError("read_failed")
            if len(matches) != 1:
                raise OAuthError("target_mismatch")

    def _google_bundle(self, response, old=None):
        """保留未輪替的 refresh token；不把缺少 scope 或期限當有效。"""
        token, expiry = response.get("access_token"), response.get("expires_in")
        if not isinstance(token, str) or not token or type(expiry) is not int or expiry <= 0:
            raise OAuthError("remote_result_unknown")
        if str(response.get("token_type", "")).lower() != "bearer":
            raise OAuthError("remote_result_unknown")
        scopes = response.get("scope")
        if scopes is None and old is not None:
            scopes = " ".join(old["scopes"])
        if not isinstance(scopes, str):
            raise OAuthError("permission_mismatch")
        refresh = response.get("refresh_token") or (old or {}).get("refresh_token")
        if not isinstance(refresh, str) or not refresh:
            raise OAuthError("reauth_required")
        bundle = {"platform": "youtube", "access_token": token, "refresh_token": refresh,
                  "expires_at": int(self.clock()) + expiry, "scopes": scopes.split(),
                  "refresh_expires_at": (old or {}).get("refresh_expires_at")}
        if "refresh_token_expires_in" in response:
            seconds = response["refresh_token_expires_in"]
            if type(seconds) is not int or seconds <= 0:
                raise OAuthError("reauth_required")
            bundle["refresh_expires_at"] = int(self.clock()) + seconds
        return bundle

    def complete(self, code, redirect_uri, verifier):
        """只由已檢查 state 的 CallbackSession 呼叫；呼叫方持有 runtime 鎖。"""
        config = self.config()
        self.mark("exchanging")
        try:
            secret = self._load(config["secret_ref"])
            if self.platform == "youtube":
                response = self.http.request("POST", "https://oauth2.googleapis.com/token", mutation=True,
                    form={"client_id": config["client_id"], "client_secret": secret,
                          "redirect_uri": redirect_uri, "code": code, "code_verifier": verifier,
                          "grant_type": "authorization_code"})
                bundle = self._google_bundle(response)
            else:
                endpoint = f"https://graph.facebook.com/{config['graph_version']}/oauth/access_token"
                response = self.http.request("GET", endpoint, mutation=True, query={
                    "client_id": config["client_id"], "client_secret": secret,
                    "redirect_uri": redirect_uri, "code": code})
                short = response.get("access_token")
                if not isinstance(short, str) or not short:
                    raise OAuthError("remote_result_unknown")
                short_info = self._debug(config, short, "USER")
                response = self.http.request("GET", endpoint, mutation=True, query={
                    "client_id": config["client_id"], "client_secret": secret,
                    "grant_type": "fb_exchange_token", "fb_exchange_token": short})
                user = response.get("access_token")
                if not isinstance(user, str) or not user:
                    raise OAuthError("remote_result_unknown")
                long_info = self._debug(config, user, "USER")
                if not short_info.get("user_id") or short_info.get("user_id") != long_info.get("user_id"):
                    raise OAuthError("target_mismatch")
                granted = {x.get("permission") for x in self._rows(config, "me/permissions", user) if x.get("status") == "granted"}
                if granted != set(config["scopes"]) | {"public_profile"}:
                    raise OAuthError("permission_mismatch")
                pages = self._rows(config, "me/accounts", user, {"fields": "id,name,access_token,tasks"})
                found = [x for x in pages if str(x.get("id")) == config["target_id"]]
                if len(found) != 1 or not found[0].get("access_token") or not found[0].get("tasks"):
                    raise OAuthError("target_mismatch")
                # 只保存選定 Page Token，不保存其他 Page 或短期 User Token。
                bundle = {"platform": "facebook", "access_token": found[0]["access_token"]}
            self._save_bundle(bundle)
            self._verify(config, bundle)
            self.mark("ready")
        except OAuthError as error:
            self.mark(error.kind)
            raise
        except Exception:
            self.mark("storage_incomplete" if self.status()["status"] == "saving" else "remote_result_unknown")
            raise OAuthError(self.status()["status"]) from None
        return self.status()

    def access(self, *, confirmed_read=False, allow_refresh=False, resume=False):
        """供後續受信任技能取用；每次讀回驗證，必要時只刷新一次。不得列印回傳值。"""
        if not confirmed_read:
            raise OAuthError("authorization_required")
        with self.lock():
            state = self.status()["status"]
            if state in {"exchanging", "refreshing", "remote_result_unknown", "authorizing", "configured"}:
                raise OAuthError("recovery_required")
            if state != "ready" and not resume:
                raise OAuthError("recovery_required")
            config, bundle = self.config(), self._bundle()
            try:
                if self.platform == "youtube" and bundle["expires_at"] <= self.clock() + 60:
                    if not allow_refresh:
                        raise OAuthError("refresh_required")
                    if bundle.get("refresh_expires_at") and bundle["refresh_expires_at"] <= self.clock():
                        raise OAuthError("reauth_required")
                    self.mark("refreshing")
                    response = self.http.request("POST", "https://oauth2.googleapis.com/token", mutation=True,
                        form={"client_id": config["client_id"], "client_secret": self._load(config["secret_ref"]),
                              "grant_type": "refresh_token", "refresh_token": bundle["refresh_token"]})
                    bundle = self._google_bundle(response, bundle)
                    self._save_bundle(bundle)
                self._verify(config, bundle)
                self.mark("ready")
                return bundle["access_token"]
            except OAuthError as error:
                self.mark(error.kind)
                raise
            except Exception:
                state = "storage_incomplete" if self.status()["status"] == "saving" else "remote_result_unknown"
                self.mark(state)
                raise OAuthError(state) from None
