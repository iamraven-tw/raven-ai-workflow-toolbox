#!/usr/bin/env python3
"""把本機留言 queue 接到六欄 Google Sheets v4；不在輸出顯示內容。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import community_queue as queue
from official_sheets_api import OfficialSheetsAdapter, SheetsAPIError


class CommunitySheetsError(RuntimeError):
    """對 Agent 只回傳固定錯誤，不夾帶試算表文字。"""


def _require(ok, reason):
    """用固定代碼停止，不回顯外部資料。"""

    if not ok:
        raise CommunitySheetsError(reason)


def _state(root):
    """讀取 queue 狀態；實際修改仍交 queue 的鎖與原子寫入。"""

    path = queue.local(root, "social-media/community/state.json")
    _require(path.is_file(), "queue_not_initialized")
    value = queue.read_json(path)
    _require(value.get("schema_version") == 1, "queue_version")
    return value


def _batch(root, batch_id):
    """讀出指定批次，不把六欄值放進一般輸出。"""

    queue.identifier(batch_id)
    batch = _state(root).get("batches", {}).get(batch_id)
    _require(isinstance(batch, dict), "batch_missing")
    return batch


def _write_json(root, relative, value):
    """以 0600 原子保存含儲存格的讀回證據。"""

    path = queue.local(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    encoded = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
    _require(len(encoded) <= 4_000_000, "sheet_evidence_too_large")
    descriptor, name = tempfile.mkstemp(prefix=".community-sheet-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        if os.name == "posix":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()
    return path


def _relative(root, path):
    """證據只回傳私人工作區內的相對位置。"""

    return path.relative_to(root).as_posix()


class CommunitySheetsCoordinator:
    """處理一次 RAW 寫入、獨立型別讀回與每次回覆前重讀。"""

    def __init__(self, workspace, *, adapter=None):
        self.root = queue.workspace(workspace)
        self.adapter = adapter or OfficialSheetsAdapter()

    def _save_snapshot(self, batch_id, purpose, snapshot):
        """保存快照並回傳可供其他可信協調器載入的 reference。"""

        queue.identifier(batch_id)
        _require(purpose in {"write_readback", "approval", "reply_preflight"},
                 "snapshot_purpose")
        digest = hashlib.sha256(json.dumps(
            snapshot, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode("utf-8")).hexdigest()
        path = _write_json(
            self.root,
            f"social-media/community/sheets/{batch_id}-{purpose}-{digest[:16]}.json",
            {"schema_version": 1, "kind": "community_sheet_snapshot",
             "batch_id": batch_id, "purpose": purpose,
             "snapshot_sha256": digest, "snapshot": snapshot})
        return path, digest

    def _verify_readback(self, batch_id):
        """讀回固定 A:F，只有完全符合原輸出才轉成人工審核狀態。"""

        batch = _batch(self.root, batch_id)
        try:
            snapshot = self.adapter.read_snapshot(batch["binding"], len(batch["rows"]) + 1)
        except SheetsAPIError as error:
            return {"result": "pending", "reason": error.kind,
                    "external_write_may_have_occurred": True}
        path, digest = self._save_snapshot(batch_id, "write_readback", snapshot)
        try:
            result = queue.run(self.root, "sheet-verify", {
                "batch_id": batch_id, "snapshot": snapshot})
        except (ValueError, TypeError, KeyError):
            return {"result": "mismatch", "reason": "sheet_write_readback_mismatch",
                    "snapshot_path": _relative(self.root, path),
                    "snapshot_sha256": digest, "external_write_may_have_occurred": True}
        return {"result": result["result"], "snapshot_path": _relative(self.root, path),
                "snapshot_sha256": digest, "external_write_verified": True}

    def write_batch(self, data):
        """先確認空白專用分頁，再 claim、RAW 寫入一次並獨立讀回。"""

        required = {"batch_id", "keys", "binding", "confirmed_sheet_write",
                    "approval_ref"}
        _require(isinstance(data, dict) and set(data) == required,
                 "sheet_write_fields")
        _require(data["confirmed_sheet_write"] is True
                 and isinstance(data["approval_ref"], str)
                 and bool(data["approval_ref"].strip()), "sheet_write_approval_required")
        self.adapter.require_empty(data["binding"])
        queue.run(self.root, "export", data)
        return self._claim_write_verify(data["batch_id"])

    def _claim_write_verify(self, batch_id):
        """claim 後只送一次；任何寫入錯誤都不在本方法重試。"""

        claim = queue.run(self.root, "sheet-claim", {"batch_id": batch_id})
        try:
            accepted = self.adapter.write_values(claim)
        except SheetsAPIError as error:
            state = "unknown" if error.kind == "remote_result_unknown" else "failed"
            queue.run(self.root, "sheet-write-result", {
                "batch_id": batch_id, "state": state})
            return {"result": state, "reason": error.kind,
                    "external_write_may_have_occurred": state == "unknown"}
        queue.run(self.root, "sheet-write-result", {
            "batch_id": batch_id, "state": accepted["result"]})
        return self._verify_readback(batch_id)

    def resume_write(self, data):
        """沒有 claim 才可送出；已有 claim 時只能讀回查明。"""

        _require(isinstance(data, dict) and set(data) == {"batch_id"},
                 "sheet_resume_fields")
        batch = _batch(self.root, data["batch_id"])
        _require(batch["status"] == "sheet_write_pending", "sheet_not_pending")
        operation = batch.get("sheet_operation")
        if operation is None:
            self.adapter.require_empty(batch["binding"])
            return self._claim_write_verify(data["batch_id"])
        _require(operation.get("state") != "failed", "sheet_write_failed_no_retry")
        return self._verify_readback(data["batch_id"])

    def approve_batch(self, data):
        """收到對話確認後重新讀 F 欄，再綁定精確最終文字。"""

        required = {"batch_id", "confirmed_reply", "approval_ref"}
        _require(isinstance(data, dict) and set(data) == required,
                 "sheet_approval_fields")
        _require(data["confirmed_reply"] is True
                 and isinstance(data["approval_ref"], str)
                 and bool(data["approval_ref"].strip()), "reply_approval_required")
        batch = _batch(self.root, data["batch_id"])
        _require(batch["status"] in {"awaiting_approval", "approved"},
                 "batch_not_reviewable")
        snapshot = self.adapter.read_snapshot(batch["binding"], len(batch["rows"]) + 1)
        path, digest = self._save_snapshot(data["batch_id"], "approval", snapshot)
        result = queue.run(self.root, "approve", {
            "batch_id": data["batch_id"], "snapshot": snapshot,
            "confirmed_reply": True, "approval_ref": data["approval_ref"]})
        return {"result": result["result"], "reply_count": result["reply_count"],
                "snapshot_path": _relative(self.root, path),
                "snapshot_sha256": digest, "external_write": False}

    def current_snapshot(self, batch_id, *, purpose="reply_preflight"):
        """每則平台回覆前重新讀原分頁，保存但不輸出六欄內容。"""

        batch = _batch(self.root, batch_id)
        _require(batch["status"] == "approved", "approval_required")
        snapshot = self.adapter.read_snapshot(batch["binding"], len(batch["rows"]) + 1)
        path, digest = self._save_snapshot(batch_id, purpose, snapshot)
        return {"snapshot": snapshot, "snapshot_path": _relative(self.root, path),
                "snapshot_sha256": digest}


def run(workspace, command, data, *, adapter=None):
    """提供測試與 CLI 共用入口。"""

    coordinator = CommunitySheetsCoordinator(workspace, adapter=adapter)
    if command == "write-batch":
        return coordinator.write_batch(data)
    if command == "resume-write":
        return coordinator.resume_write(data)
    if command == "approve-batch":
        return coordinator.approve_batch(data)
    if command == "read-for-reply":
        _require(isinstance(data, dict) and set(data) == {"batch_id"},
                 "sheet_read_fields")
        result = coordinator.current_snapshot(data["batch_id"])
        return {key: value for key, value in result.items() if key != "snapshot"}
    raise CommunitySheetsError("command_invalid")


def main():
    """CLI 只輸出狀態與私人 evidence 路徑，不顯示六欄內容。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("write-batch", "resume-write",
                                            "approve-batch", "read-for-reply"))
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        root = queue.workspace(args.workspace)
        data = queue.read_json(queue.local(root, args.input))
        print(json.dumps(run(root, args.command, data), ensure_ascii=False))
        return 0
    except (CommunitySheetsError, SheetsAPIError, ValueError, TypeError, KeyError,
            OSError, UnicodeError):
        print('{"result":"stopped","reason":"invalid_or_conflicting_state"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
