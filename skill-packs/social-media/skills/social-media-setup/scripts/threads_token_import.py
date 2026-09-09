"""匯入官方後台產生的 Threads 測試權杖；秘密只從原生庫進入記憶體。"""

import argparse
import json
import re

from oauth_runtime import Runtime, validate_config
from oauth_http import OAuthError
from meta_user_oauth import identifier, permission_set, DAY


def import_token(runtime, *, client_id, username, scopes, version, source_ref,
                 confirmed_read=False, confirmed_store=False):
    """先核對官方 App／帳號／scope／期限，再保存；不覆蓋既有連線。"""
    if not confirmed_read or not confirmed_store:
        raise OAuthError('authorization_required')
    if (runtime.platform != 'threads' or not re.fullmatch(r'[0-9]+', client_id)
            or not re.fullmatch(r'[A-Za-z0-9._]{1,30}', username)
            or not re.fullmatch(r'v[0-9]+\.0', version)):
        raise OAuthError('invalid_configuration')
    expected = permission_set(scopes)
    if 'threads_basic' not in expected or any(not s.startswith('threads_') for s in expected):
        raise OAuthError('invalid_configuration')
    with runtime.lock():
        if runtime.status()['status'] != 'not_configured':
            raise OAuthError('recovery_required')
        token = runtime._load(source_ref)
        info = runtime.http.request('GET', 'https://graph.threads.net/debug_token',
                                   query={'input_token': token, 'access_token': token}).get('data')
        if not isinstance(info, dict):
            raise OAuthError('read_failed')
        # 沒有 code 交換綁定 App 的證據，匯入必須明確核對 debugger app_id。
        if identifier(info.get('app_id')) != client_id:
            raise OAuthError('target_mismatch')
        if info.get('is_valid') is False:
            raise OAuthError('reauth_required')
        if permission_set(info.get('scopes')) != expected:
            raise OAuthError('permission_mismatch')
        now, expiry = int(runtime.clock()), info.get('expires_at')
        if type(expiry) is not int or expiry <= now + DAY:
            raise OAuthError('expired')
        user = runtime.http.request('GET', f'https://graph.threads.net/{version}/me',
                                   query={'fields': 'id,username', 'access_token': token})
        target = identifier(user.get('id'))
        if target != identifier(info.get('user_id')) or user.get('username', '').lower() != username.lower():
            raise OAuthError('target_mismatch')
        config = validate_config({'platform': 'threads', 'login_route': 'threads_login',
            'client_id': client_id, 'target_id': target, 'scopes': sorted(expected),
            'secret_ref': source_ref, 'graph_version': version, 'redirect_uri': '',
            'callback_port': 0, 'callback_mode': 'token_import', 'tls_cert': '', 'tls_key': ''})
        bundle = {'platform': 'threads', 'access_token': token, 'provider_user_id': target,
            'client_id': client_id, 'scopes': sorted(expected), 'issued_at': now,
            'expires_at': expiry, 'source': 'official_dashboard_import'}
        runtime._verify(config, bundle)
        # 設定及所有驗證在同一把鎖中；失敗不交付 ready，也不自動重送。
        runtime.mark('configured')
        try:
            runtime._store(runtime.prefix + '-config', json.dumps(config, separators=(',', ':')))
            runtime._save_bundle(bundle)
            persisted = runtime._bundle()
            if persisted != bundle:
                raise OAuthError('storage_incomplete')
            runtime.mark('ready')
        except Exception:
            runtime.mark('storage_incomplete')
            raise OAuthError('storage_incomplete') from None
    return {'status': 'ready', 'platform': 'threads', 'source': 'official_dashboard_import',
            'callback_verified': False, 'contains_credentials': False}


def main():
    parser = argparse.ArgumentParser(description='匯入已保存在原生庫的官方 Threads 測試權杖')
    parser.add_argument('--workspace-root', required=True)
    parser.add_argument('--connection', default='main')
    parser.add_argument('--client-id', required=True)
    parser.add_argument('--username', required=True)
    parser.add_argument('--scope', action='append', required=True)
    parser.add_argument('--graph-version', required=True)
    parser.add_argument('--source-ref', default='dashboard-token')
    parser.add_argument('--confirm-read', action='store_true')
    parser.add_argument('--confirm-store', action='store_true')
    args = parser.parse_args()
    try:
        result = import_token(Runtime(args.workspace_root, 'threads', connection=args.connection),
            client_id=args.client_id, username=args.username, scopes=args.scope,
            version=args.graph_version, source_ref=args.source_ref,
            confirmed_read=args.confirm_read, confirmed_store=args.confirm_store)
    except Exception as error:
        result = {'status': getattr(error, 'kind', 'read_failed'), 'contains_credentials': False}
    print(json.dumps(result))
    return 0 if result['status'] == 'ready' else 1


if __name__ == '__main__':
    raise SystemExit(main())
