"""Instagram Login／Threads 專用 User Token 路徑；不使用 Facebook Page Token。"""

import re

from oauth_http import OAuthError


PLATFORMS = {"instagram", "threads"}
DAY = 24 * 60 * 60
REFRESH_WINDOW = 7 * DAY
HOSTS = {"instagram": "graph.instagram.com", "threads": "graph.threads.net"}
AUTH_URLS = {"instagram": "https://www.instagram.com/oauth/authorize",
             "threads": "https://www.threads.com/oauth/authorize"}


def identifier(value):
    """只在記憶體核對平台 ID，不接受布林或浮點值造成身分誤認。"""
    if type(value) not in (str, int) or not re.fullmatch(r"[0-9]+", str(value)):
        raise OAuthError("target_mismatch")
    return str(value)


def permission_set(value):
    """接受官方字串或字串陣列，不把缺值或重複資料當成核准清單。"""
    if isinstance(value, str):
        value = re.split(r"[\s,]+", value.strip())
    if (not isinstance(value, list) or not value or
            any(not isinstance(x, str) or not re.fullmatch(r"[a-z_]+", x) for x in value)
            or len(value) != len(set(value))):
        raise OAuthError("permission_mismatch")
    return set(value)


def single(payload, kind="read_failed"):
    """官方 IG 文件有 data 單筆陣列，保留平面物件相容但拒絕多筆歧義。"""
    if not isinstance(payload, dict):
        raise OAuthError(kind)
    if "data" in payload:
        rows = payload["data"]
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            raise OAuthError(kind)
        # 不猜測兩種格式同時出現時哪一個 Token／身分才是真的。
        if set(payload) - {"data"}:
            raise OAuthError(kind)
        return rows[0]
    return payload


def token_bundle(runtime, config, response, user_id, scopes, started):
    """TTL 只採正式回應；不硬補 60 天，也不產生 Google refresh_token。"""
    if not isinstance(response, dict):
        raise OAuthError("remote_result_unknown")
    token, ttl = response.get("access_token"), response.get("expires_in")
    if (not isinstance(token, str) or not token or type(ttl) is not int or ttl <= 0
            or not isinstance(response.get("token_type"), str)
            or response["token_type"].lower() != "bearer"):
        raise OAuthError("remote_result_unknown")
    return {"platform": runtime.platform, "access_token": token,
            "provider_user_id": identifier(user_id), "client_id": config["client_id"],
            "scopes": sorted(scopes), "issued_at": started, "expires_at": started + ttl}


def graph(runtime, config, path, token, fields=None):
    """固定平台及端點，Token 不離開傳輸程式的記憶體。"""
    query = {"access_token": token}
    if fields:
        query["fields"] = fields
    return runtime.http.request("GET", f"https://{HOSTS[runtime.platform]}/{config['graph_version']}/{path}",
                                query=query)


def verify(runtime, config, bundle):
    """IG 驗證當前基本帳號與初次 scope；Threads 另讀當前 debugger scope。"""
    now = runtime.clock()
    if (type(bundle.get("expires_at")) is not int or type(bundle.get("issued_at")) is not int
            or bundle["issued_at"] > now or bundle["expires_at"] <= bundle["issued_at"]):
        raise OAuthError("read_failed")
    if bundle["expires_at"] <= now:
        raise OAuthError("reauth_required")
    if bundle.get("client_id") != config["client_id"]:
        raise OAuthError("target_mismatch")
    if permission_set(bundle.get("scopes")) != set(config["scopes"]):
        raise OAuthError("permission_mismatch")
    token = bundle["access_token"]
    if runtime.platform == "instagram":
        user = single(graph(runtime, config, "me", token, "id,user_id,username,account_type"))
        if (identifier(user.get("id")) != bundle["provider_user_id"]
                or identifier(user.get("user_id")) != config["target_id"]
                or not isinstance(user.get("username"), str) or not user["username"]
                or user.get("account_type", "").lower() not in {"business", "media_creator"}):
            raise OAuthError("target_mismatch")
        # 未查得同路徑下可重新列出全部 scope 的正式介面，禁止假造 GET permissions。
        # 此處的 scope 是初次交換證據；後續功能仍需自己處理撤權／審查／端點錯誤。
    else:
        payload = runtime.http.request("GET", "https://graph.threads.net/debug_token",
                                       query={"input_token": token, "access_token": token})
        info = payload.get("data")
        if not isinstance(info, dict):
            raise OAuthError("read_failed")
        if info.get("is_valid") is False:
            raise OAuthError("reauth_required")
        if "app_id" in info and identifier(info["app_id"]) != config["client_id"]:
            raise OAuthError("target_mismatch")
        if config.get('callback_mode') == 'token_import':
            if info.get('is_valid') is not True or info.get('type') != 'USER':
                raise OAuthError('reauth_required')
            evidence = bundle.get('app_identity_evidence')
            if evidence == 'api_app_id':
                if identifier(info.get('app_id')) != config['client_id']:
                    raise OAuthError('target_mismatch')
            elif evidence == 'dashboard_source_and_application':
                if not bundle.get('application') or info.get('application') != bundle['application']:
                    raise OAuthError('target_mismatch')
            else:
                raise OAuthError('target_mismatch')
        if identifier(info.get("user_id")) != bundle["provider_user_id"]:
            raise OAuthError("target_mismatch")
        if permission_set(info.get("scopes")) != set(config["scopes"]):
            raise OAuthError("permission_mismatch")
        if type(info.get("expires_at")) is not int or info["expires_at"] <= 0:
            raise OAuthError("read_failed")
        if info["expires_at"] <= now:
            raise OAuthError("reauth_required")
        for key in ("data_access_expires_at",):
            if key in info:
                if type(info[key]) is not int or info[key] < 0:
                    raise OAuthError("read_failed")
                if info[key] and info[key] <= now:
                    raise OAuthError("reauth_required")
        user = graph(runtime, config, "me", token, "id,username")
        if (identifier(user.get("id")) != config["target_id"]
                or identifier(user.get("id")) != bundle["provider_user_id"]
                or not isinstance(user.get("username"), str) or not user["username"]):
            raise OAuthError("target_mismatch")


def exchange(runtime, config, code, redirect_uri, secret):
    """初次交換僅一次；短期 Token 不持久保存，不發送到錯誤的平台。"""
    platform = runtime.platform
    endpoint = ("https://api.instagram.com/oauth/access_token" if platform == "instagram"
                else "https://graph.threads.net/oauth/access_token")
    kwargs = {"form": {"client_id": config["client_id"], "client_secret": secret,
                       "grant_type": "authorization_code", "redirect_uri": redirect_uri, "code": code},
              "mutation": True}
    if platform == "instagram":
        kwargs["multipart"] = True
    response = single(runtime.http.request("POST", endpoint, **kwargs), "remote_result_unknown")
    short = response.get("access_token")
    if not isinstance(short, str) or not short:
        raise OAuthError("remote_result_unknown")
    user_id = identifier(response.get("user_id"))
    if platform == "instagram":
        scopes = permission_set(response.get("permissions"))
        if scopes != set(config["scopes"]):
            raise OAuthError("permission_mismatch")
    else:
        # Threads 短 Token 回應沒有 scope；稍後必須由官方 debugger 實際核對。
        scopes = set(config["scopes"])
        if user_id != config["target_id"]:
            raise OAuthError("target_mismatch")
    started = int(runtime.clock())
    prefix = "ig" if platform == "instagram" else "th"
    response = runtime.http.request("GET", f"https://{HOSTS[platform]}/access_token", mutation=True,
        query={"grant_type": prefix + "_exchange_token", "client_secret": secret, "access_token": short})
    return token_bundle(runtime, config, response, user_id, scopes, started)


def access_bundle(runtime, config, bundle, allow_refresh):
    """先讀回舊 Token；只在最後七天按需刷新，不建立背景排程。"""
    verify(runtime, config, bundle)
    now = runtime.clock()
    # 唯讀請求耗時期間也可能到期，不對已過期的 Token 發動刷新。
    if bundle["expires_at"] <= now:
        raise OAuthError("reauth_required")
    if bundle["expires_at"] - now > REFRESH_WINDOW:
        return bundle
    old_enough = now - bundle["issued_at"] >= DAY
    if not allow_refresh or not old_enough:
        # 還有效時不強迫提早更新；逼近到期才停止要求授權或重新授權。
        if bundle["expires_at"] - now <= 60:
            raise OAuthError("refresh_required" if old_enough else "reauth_required")
        return bundle
    runtime.mark("refreshing")
    prefix = "ig" if runtime.platform == "instagram" else "th"
    started = int(runtime.clock())
    response = runtime.http.request("GET", f"https://{HOSTS[runtime.platform]}/refresh_access_token",
        mutation=True, query={"grant_type": prefix + "_refresh_token", "access_token": bundle["access_token"]})
    fresh = token_bundle(runtime, config, response, bundle["provider_user_id"], set(bundle["scopes"]), started)
    # 刷新不能把人工來源證據升級成 API App ID 證據，亦不能遺失後續核對條件。
    for key in ('source', 'app_identity_evidence', 'application'):
        if key in bundle:
            fresh[key] = bundle[key]
    runtime._save_bundle(fresh)
    verify(runtime, config, fresh)
    return fresh
