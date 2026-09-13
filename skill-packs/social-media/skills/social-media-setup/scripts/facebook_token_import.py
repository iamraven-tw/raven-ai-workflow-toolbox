"""匯入本人已存入原生庫的 Page Token；不開回呼、不接收秘密參數。"""

import argparse
import json

from oauth_http import OAuthError
from oauth_runtime import Runtime, validate_config
import credential_store as vault


def import_token(runtime, *, client_id, page_id, scopes, version,
                 source_ref="dashboard-token", secret_ref="app-secret",
                 confirmed_read=False, confirmed_store=False):
    """先核對 App、PAGE 類型、範圍、到期及專頁，再保存獨立連線。"""
    if not confirmed_read or not confirmed_store:
        raise OAuthError("authorization_required")
    if runtime.platform != "facebook" or source_ref == secret_ref:
        raise OAuthError("invalid_configuration")
    vault.validate_reference("facebook", source_ref)
    config = validate_config({
        "platform": "facebook", "login_route": "facebook_pages",
        "client_id": client_id, "target_id": page_id, "scopes": scopes,
        "secret_ref": secret_ref, "graph_version": version,
        "redirect_uri": "", "callback_port": 0, "callback_mode": "token_import",
        "tls_cert": "", "tls_key": "",
    })
    with runtime.lock():
        if runtime.status()["status"] != "not_configured":
            raise OAuthError("recovery_required")
        # 缺少 App Secret 時在任何平台請求前停止；不降低 debugger/proof 保護。
        runtime._load(secret_ref)
        token = runtime._load(source_ref)
        bundle = {"platform": "facebook", "access_token": token,
                  "source": "official_dashboard_import"}
        runtime._verify(config, bundle)
        try:
            runtime.mark("configured")
            runtime._store(runtime.prefix + "-config", json.dumps(config, separators=(",", ":")))
            runtime._save_bundle(bundle)
            if runtime._bundle() != bundle:
                raise OAuthError("storage_incomplete")
            runtime.mark("ready")
        except Exception:
            runtime.mark("storage_incomplete")
            raise OAuthError("storage_incomplete") from None
    return {"platform": "facebook", "status": "ready",
            "source": "official_dashboard_import", "callback_verified": False,
            "contains_credentials": False}


def main():
    """CLI 只收已確認的識別資料與原生庫項目名稱，不接受 Token 值。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--connection", default="main")
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--page-id", required=True)
    parser.add_argument("--scope", action="append", required=True)
    parser.add_argument("--graph-version", required=True)
    parser.add_argument("--source-ref", default="dashboard-token")
    parser.add_argument("--secret-ref", default="app-secret")
    parser.add_argument("--confirm-read", action="store_true")
    parser.add_argument("--confirm-store", action="store_true")
    args = parser.parse_args()
    try:
        result = import_token(Runtime(args.workspace_root, "facebook", connection=args.connection),
                              client_id=args.client_id, page_id=args.page_id, scopes=args.scope,
                              version=args.graph_version, source_ref=args.source_ref,
                              secret_ref=args.secret_ref, confirmed_read=args.confirm_read,
                              confirmed_store=args.confirm_store)
    except Exception as error:
        # 不輸出例外本文，以免底層包含平台回應或秘密。
        result = {"status": getattr(error, "kind", "read_failed"), "contains_credentials": False}
    print(json.dumps(result))
    return 0 if result["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
