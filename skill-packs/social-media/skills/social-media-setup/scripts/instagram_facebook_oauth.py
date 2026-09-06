"""Instagram via Facebook Login 的 Page Token、相連 Page 與 IG 身分驗證。"""

from oauth_http import OAuthError


LOGIN_ROUTE = "instagram_facebook_login"


def identifier(value):
    """只接受 Meta 的十進位識別碼，避免布林或浮點值被誤認。"""
    if type(value) not in (str, int) or not str(value).isdigit():
        raise OAuthError("target_mismatch")
    return str(value)


def _linked_instagram(page):
    """從官方 Page 關係欄位讀取單一 Instagram 專業帳號。"""
    linked = page.get("instagram_business_account")
    if not isinstance(linked, dict):
        raise OAuthError("target_mismatch")
    return identifier(linked.get("id"))


def _scope_rows(runtime, config, user_token):
    """Facebook User Token 可重新列出目前 permission；拒絕重複或未知狀態。"""
    rows = runtime._rows(config, "me/permissions", user_token)
    permissions = {}
    for row in rows:
        name, status = row.get("permission"), row.get("status")
        if (not isinstance(name, str) or not name or name in permissions
                or status not in {"granted", "declined", "expired"}):
            raise OAuthError("read_failed")
        permissions[name] = status
    granted = {name for name, status in permissions.items() if status == "granted"}
    if granted != set(config["scopes"]) | {"public_profile"}:
        raise OAuthError("permission_mismatch")


def exchange(runtime, config, code, redirect_uri, secret):
    """User code 換長 Token，再只保存目標 IG 所連結 Page 的 Token。"""
    endpoint = f"https://graph.facebook.com/{config['graph_version']}/oauth/access_token"
    response = runtime.http.request("GET", endpoint, mutation=True, query={
        "client_id": config["client_id"], "client_secret": secret,
        "redirect_uri": redirect_uri, "code": code})
    short = response.get("access_token") if isinstance(response, dict) else None
    if not isinstance(short, str) or not short:
        raise OAuthError("remote_result_unknown")
    short_info = runtime._debug(config, short, "USER")

    response = runtime.http.request("GET", endpoint, mutation=True, query={
        "client_id": config["client_id"], "client_secret": secret,
        "grant_type": "fb_exchange_token", "fb_exchange_token": short})
    user = response.get("access_token") if isinstance(response, dict) else None
    if not isinstance(user, str) or not user:
        raise OAuthError("remote_result_unknown")
    long_info = runtime._debug(config, user, "USER")
    user_id = identifier(short_info.get("user_id"))
    if identifier(long_info.get("user_id")) != user_id:
        raise OAuthError("target_mismatch")

    _scope_rows(runtime, config, user)
    pages = runtime._rows(config, "me/accounts", user, {
        "fields": "id,name,access_token,tasks,instagram_business_account"})
    matches = [page for page in pages
               if isinstance(page.get("instagram_business_account"), dict)
               and str(page["instagram_business_account"].get("id")) == config["target_id"]]
    if len(matches) != 1:
        raise OAuthError("target_mismatch")
    page = matches[0]
    page_id = identifier(page.get("id"))
    page_token = page.get("access_token")
    if (not isinstance(page.get("name"), str) or not page["name"]
            or not isinstance(page_token, str) or not page_token
            or not isinstance(page.get("tasks"), list) or not page["tasks"]
            or any(not isinstance(task, str) or not task for task in page["tasks"])
            or _linked_instagram(page) != config["target_id"]):
        raise OAuthError("target_mismatch")

    # 短期及長期 User Token、其他 Page Token 都不持久保存。
    return {"platform": "instagram", "login_route": LOGIN_ROUTE,
            "access_token": page_token, "page_id": page_id,
            "facebook_user_id": user_id}


def verify(runtime, config, bundle):
    """每次取用都重新核對 App、scope、Page 與相連 IG 身分。"""
    if (bundle.get("platform") != "instagram" or bundle.get("login_route") != LOGIN_ROUTE):
        raise OAuthError("target_mismatch")
    identifier(bundle.get("page_id"))
    identifier(bundle.get("facebook_user_id"))
    page_token = bundle.get("access_token")
    if not isinstance(page_token, str) or not page_token:
        raise OAuthError("storage_incomplete")

    info = runtime._debug(config, page_token, "PAGE")
    if set(info.get("scopes", [])) != set(config["scopes"]) | {"public_profile"}:
        raise OAuthError("permission_mismatch")
    page = runtime._graph(config, bundle["page_id"], page_token,
                          {"fields": "id,name,instagram_business_account"})
    if (identifier(page.get("id")) != bundle["page_id"]
            or not isinstance(page.get("name"), str) or not page["name"]
            or _linked_instagram(page) != config["target_id"]):
        raise OAuthError("target_mismatch")
    instagram = runtime._graph(config, config["target_id"], page_token,
                               {"fields": "id,username"})
    if (identifier(instagram.get("id")) != config["target_id"]
            or not isinstance(instagram.get("username"), str) or not instagram["username"]):
        raise OAuthError("target_mismatch")
    return bundle
