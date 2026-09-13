"""定期檢查並按既有 OAuth 契約刷新社群平台權杖。"""

import argparse
import json

from oauth_http import OAuthError
from oauth_runtime import Runtime


PLATFORMS = ("facebook", "instagram", "threads", "youtube")
RECOVERABLE_READ_STATES = {"read_failed", "rate_limited"}


class SafeParser(argparse.ArgumentParser):
    """拒絕參數時不回顯可能包含私人路徑或識別資料的輸入。"""

    def error(self, message):
        self.exit(2, '{"status":"invalid_arguments","contains_credentials":false}\n')


def maintain(workspace, platform, connection="main", *, confirmed_read=False,
             allow_refresh=False, runtime_factory=Runtime):
    """處理一條已存在連線；不建立連線、不啟動 OAuth，也不輸出秘密。"""
    result = {"platform": platform, "connection": connection,
              "contains_credentials": False, "refreshed": False}
    try:
        if not confirmed_read:
            raise OAuthError("authorization_required")
        runtime = runtime_factory(workspace, platform, connection)
        before = runtime.status()
        state = before["status"]
        if state not in {"ready", *RECOVERABLE_READ_STATES}:
            result.update(status=state, action="manual_attention_required")
            return result
        runtime.access(confirmed_read=True, allow_refresh=allow_refresh,
                       resume=state in RECOVERABLE_READ_STATES, maintenance=True)
        if platform == "instagram":
            config = runtime.config()
            if (config.get("login_route") == "instagram_facebook_login"
                    and "instagram_manage_contents" in config.get("scopes", [])):
                runtime.access_instagram_user(confirmed_read=True, maintenance=True)
        after = runtime.status()
        result.update(status=after["status"],
                      refreshed=before.get("revision") != after.get("revision"),
                      action="none" if after["status"] == "ready" else "manual_attention_required")
    except OAuthError as error:
        result.update(status=error.kind, action=(
            "retry_later" if error.kind in RECOVERABLE_READ_STATES
            else "manual_attention_required"))
    except Exception:
        result.update(status="stopped_check_local_state", action="manual_attention_required")
    return result


def main():
    parser = SafeParser(description="社群 OAuth 權杖定期維護")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--platform", action="append", choices=PLATFORMS, required=True)
    parser.add_argument("--connection", default="main")
    parser.add_argument("--confirm-read", action="store_true")
    parser.add_argument("--allow-refresh", action="store_true")
    args = parser.parse_args()
    platforms = list(dict.fromkeys(args.platform))
    results = [maintain(args.workspace_root, platform, args.connection,
                        confirmed_read=args.confirm_read, allow_refresh=args.allow_refresh)
               for platform in platforms]
    attention = any(row["action"] != "none" for row in results)
    print(json.dumps({"status": "attention_required" if attention else "ready",
                      "contains_credentials": False, "results": results}, ensure_ascii=False))
    return 2 if attention else 0


if __name__ == "__main__":
    raise SystemExit(main())
