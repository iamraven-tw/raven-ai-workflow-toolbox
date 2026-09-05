#!/usr/bin/env python3
"""開啟原生可見 Terminal，並以不含秘密的收據交回結果。"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import credential_store as vault


RECEIPTS = Path(".local/social-media/credential-input")
TTL_SECONDS = 900
STATES = {"waiting_for_input", "input_started", "verified", "stopped", "launch_failed"}


def receipt_path(workspace, ticket):
    """只接受固定格式識別碼與工作區內的非連結路徑。"""

    if not vault.NAMESPACE_PATTERN.fullmatch(ticket):
        raise vault.CredentialStoreError("Terminal 收據識別碼不符")
    current = vault.resolve_workspace(workspace)
    for part in (RECEIPTS / f"{ticket}.json").parts:
        current /= part
        if current.is_symlink():
            raise vault.CredentialStoreError("Terminal 收據不得包含 symlink")
    return current


def read_receipt(workspace, ticket):
    """收據只記錄作業名稱、確認旗標與狀態，不能承載秘密。"""

    value = json.loads(receipt_path(workspace, ticket).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != {
        "ticket", "platform", "name", "operation", "replace", "created_at",
        "status", "contains_credentials"
    }:
        raise vault.CredentialStoreError("Terminal 收據格式不符")
    vault.validate_reference(value["platform"], value["name"])
    if (value["ticket"] != ticket or value["operation"] not in {"put", "recover"}
            or type(value["replace"]) is not bool or type(value["created_at"]) is not int
            or value["status"] not in STATES or value["contains_credentials"] is not False):
        raise vault.CredentialStoreError("Terminal 收據內容不符")
    return value


def save_receipt(workspace, value):
    """原子寫入非敏感收據；寫入失敗不得宣稱憑證成功。"""

    path = receipt_path(workspace, value["ticket"])
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".receipt-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def launch_process(arguments):
    """命令只含程式路徑與收據 ID；不透過 shell 傳送秘密。"""

    if sys.platform == "darwin":
        script = ('on run argv\n tell application "Terminal"\n activate\n'
                  ' do script (item 1 of argv)\n end tell\nend run')
        result = subprocess.run(
            ["/usr/bin/osascript", "-e", script, shlex.join(arguments)],
            capture_output=True, timeout=20, check=False,
        )
        if result.returncode:
            raise vault.CredentialStoreError("無法開啟 Terminal；可能需要使用者允許控制")
    elif os.name == "nt":
        subprocess.Popen(arguments, creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        raise vault.CredentialStoreError("目前僅提供 macOS 與 Windows Terminal 啟動器")


def launch(workspace, platform, name, *, confirmed, replace=False, operation="put"):
    """確認後建立一次性收據，再開啟人類可見的輸入視窗。"""

    if not confirmed:
        raise vault.CredentialStoreError("必須先確認憑證保存預覽")
    platform, name = vault.validate_reference(platform, name)
    if operation not in {"put", "recover"}:
        raise vault.CredentialStoreError("不支援的互動作業")
    workspace = vault.resolve_workspace(workspace)
    # 取得秘密前就檢查原生介面及既有參照；測試以虛構 backend 注入。
    backend = vault.detect_backend()
    registry = vault.ensure_registry_backend(vault.load_registry(workspace), backend)
    if operation == "put" and f"{platform}/{name}" in registry["entries"] and not replace:
        raise vault.CredentialStoreError("同名憑證已存在；請先確認是否取代")
    ticket = secrets.token_hex(16)
    receipt = {"ticket": ticket, "platform": platform, "name": name,
               "operation": operation, "replace": replace, "created_at": int(time.time()),
               "status": "waiting_for_input", "contains_credentials": False}
    with vault.workspace_lock(workspace):
        save_receipt(workspace, receipt)
    arguments = [sys.executable, "-B", str(Path(__file__).resolve()), "_input",
                 "--workspace-root", str(workspace), "--ticket", ticket]
    try:
        launch_process(arguments)
    except (OSError, subprocess.SubprocessError, vault.CredentialStoreError):
        # 啟動逾時可能已有視窗；只封鎖還沒開始的收據，不重開第二個視窗。
        with vault.workspace_lock(workspace):
            receipt = read_receipt(workspace, ticket)
            if receipt["status"] == "waiting_for_input":
                receipt["status"] = "launch_failed"
                save_receipt(workspace, receipt)
    return status(workspace, ticket)


def status(workspace, ticket):
    """只讀收據；程序失聯或逾時不推定憑證已存妥，也不自動重試。"""

    receipt = read_receipt(workspace, ticket)
    state = receipt["status"]
    if state in {"waiting_for_input", "input_started"} and time.time() > receipt["created_at"] + TTL_SECONDS:
        state = "unknown_check_registry"
    return {"ticket": ticket, "platform": receipt["platform"], "name": receipt["name"],
            "status": state, "contains_credentials": False}


def receive(workspace, ticket):
    """消耗一次性輸入收據；取消或例外只留下停止狀態。"""

    with vault.workspace_lock(workspace):
        receipt = read_receipt(workspace, ticket)
        if (receipt["status"] != "waiting_for_input"
                or time.time() > receipt["created_at"] + TTL_SECONDS):
            raise vault.CredentialStoreError("Terminal 收據已使用或逾時；不得重送")
        receipt["status"] = "input_started"
        save_receipt(workspace, receipt)
    arguments = argparse.Namespace(
        command=receipt["operation"], workspace_root=str(workspace),
        platform=receipt["platform"], name=receipt["name"],
        confirm_replace=receipt["replace"], confirm_recovery=True,
    )
    try:
        # 驗證成功只來自隱藏輸入程式的原生讀回，不是視窗成功開啟。
        result = vault.interactive_put(arguments)
        receipt["status"] = "verified" if result["status"] == "verified" else "stopped"
    except (Exception, KeyboardInterrupt):
        receipt["status"] = "stopped"
    with vault.workspace_lock(workspace):
        save_receipt(workspace, receipt)
    return status(workspace, ticket)


def main():
    """CLI 不接受憑證值，也不顯示原始例外。"""

    parser = argparse.ArgumentParser(description="原生 Terminal 隱藏憑證輸入交接")
    parser.add_argument("command", choices=["launch", "status", "_input"])
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--platform", choices=sorted(vault.PLATFORMS))
    parser.add_argument("--name")
    parser.add_argument("--ticket")
    parser.add_argument("--operation", choices=["put", "recover"], default="put")
    parser.add_argument("--confirm-store", action="store_true")
    parser.add_argument("--confirm-replace", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "launch":
            result = launch(args.workspace_root, args.platform, args.name,
                            confirmed=args.confirm_store, replace=args.confirm_replace,
                            operation=args.operation)
        elif args.command == "status":
            result = status(args.workspace_root, args.ticket)
        else:
            result = receive(args.workspace_root, args.ticket)
    except (Exception, KeyboardInterrupt):
        print("Terminal 作業停止；請檢查收據及憑證 status，勿貼秘密到對話。", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] in {"verified", "waiting_for_input", "input_started"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
