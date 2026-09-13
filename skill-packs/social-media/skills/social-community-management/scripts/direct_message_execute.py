#!/usr/bin/env python3
"""將 Meta 私訊官方 adapter 接到本機隔離與一次性傳送護欄。"""

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

import direct_message_queue as queue
from official_direct_message_api import (
    DirectMessageAPIError,
    OfficialDirectMessageAdapter,
)


class DirectMessageExecuteError(RuntimeError):
    """對 CLI 只顯示固定失敗狀態，不夾帶私訊內容。"""


def _require(ok, reason):
    """條件不符就停止，錯誤不回顯不可信資料。"""

    if not ok:
        raise DirectMessageExecuteError(reason)


def _state(root):
    """只讀獨立私訊狀態；修改仍交 queue 的鎖與原子寫入。"""

    path = queue.state_path(root)
    _require(path.is_file(), "queue_not_initialized")
    value = queue.read_json(path)
    _require(value.get("schema_version") == 1, "queue_version")
    return value


def _write_json(root, relative, value):
    """含外部私訊的證據只用 0600 原子寫入私人工作區。"""

    path = queue.local(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    encoded = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
    _require(len(encoded) <= 8_000_000, "evidence_too_large")
    descriptor, name = tempfile.mkstemp(prefix=".direct-message-execute-", dir=path.parent)
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
    """證據位置只回傳私人工作區內的相對路徑。"""

    return path.relative_to(root).as_posix()


def _item_context(root, batch_id, key):
    """取得已核准批次與私訊，不把內容放進一般輸出。"""

    state = _state(root)
    batch = state.get("batches", {}).get(batch_id)
    item = state.get("items", {}).get(key)
    _require(batch and item and key in batch.get("keys", []), "item_not_in_batch")
    return state, batch, item


def _scope(item, *, allow_refresh):
    """沿用擷取時的讀取核准與帳號範圍。"""

    source = item["source"]
    return {
        "platform": source["platform"], "account_id": source["account_id"],
        "approval_ref": item["read_approval_ref"], "confirmed_read": True,
        "allow_token_refresh": allow_refresh, "max_conversations": 1,
    }


def _grant(claim, *, allow_refresh):
    """只把 queue claim 與刷新選擇交低階 adapter。"""

    return {
        "platform": claim["platform"], "account_id": claim["account_id"],
        "conversation_id": claim["conversation_id"],
        "recipient_id": claim["recipient_id"], "text": claim["text"],
        "approval_ref": claim["approval_ref"],
        "transaction_status": claim["transaction_status"],
        "stage": claim["stage"], "allow_token_refresh": allow_refresh,
    }


def _record_simple(root, batch_id, key, state):
    """保存 pending／unknown／failed；任何一種都不自動重送。"""

    return queue.run(root, "record", {
        "batch_id": batch_id, "key": key, "receipt": {"state": state},
    })


def _receipt(root, batch_id, key, readback):
    """將獨立讀回轉成完整 receipt，先保存去秘密證據。"""

    state, _, item = _item_context(root, batch_id, key)
    attempt = state.get("attempts", {}).get(key)
    source = item["source"]
    _require(attempt and readback["message_id"] == attempt.get("message_created"),
             "message_checkpoint_mismatch")
    _require(readback["conversation_id"] == source["conversation_id"]
             and readback["recipient_id"] == source["visitor_id"]
             and readback["text"] == attempt["text"]
             and readback["sender_owned"] is True
             and readback["recipient_matches"] is True
             and readback["conversation_matches"] is True,
             "readback_incomplete")
    evidence_value = {
        "schema_version": 1, "kind": "direct_message_readback",
        "platform": source["platform"], "account_id": source["account_id"],
        "conversation_id": source["conversation_id"], "readback": readback,
    }
    relative = ("social-media/community/direct-messages/readbacks/"
                f"{key}-{readback['message_id']}.json")
    evidence = _write_json(root, relative, evidence_value)
    value = {
        "state": "replied", "message_id": readback["message_id"],
        "account_id": source["account_id"],
        "conversation_id": readback["conversation_id"],
        "recipient_id": readback["recipient_id"], "text": readback["text"],
        "platform_time": readback["platform_time"],
        "observed_at": readback["observed_at"], "sender_matches": True,
        "recipient_matches": True, "conversation_matches": True,
        "evidence_path": _relative(root, evidence),
        "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
    }
    return queue.run(root, "record", {
        "batch_id": batch_id, "key": key, "receipt": value,
    })


class DirectMessageCoordinator:
    """按需同步與逐則傳送的本機協調器，不輸出私訊內容。"""

    def __init__(self, workspace, *, adapter=None):
        self.root = queue.workspace(workspace)
        self.adapter = adapter or OfficialDirectMessageAdapter(self.root)

    def fetch_api(self, data):
        """讀官方 Conversations API，先存證，再將可回覆項目送隔離。"""

        _require(isinstance(data, dict) and set(data) == {"fetch_id", "scope"},
                 "fetch_fields")
        queue.identifier(data["fetch_id"])
        scope = data["scope"]
        self.adapter.verify_access(scope)
        fetched = self.adapter.fetch_conversations(scope)
        evidence = _write_json(
            self.root,
            f"social-media/community/direct-messages/fetches/{data['fetch_id']}.json",
            {"schema_version": 1, "kind": "official_direct_message_fetch",
             "scope": {"platform": scope["platform"],
                       "account_id": scope["account_id"],
                       "approval_ref": scope["approval_ref"],
                       "max_conversations": scope["max_conversations"]},
             **fetched},
        )
        if fetched["records"]:
            ingest = queue.run(self.root, "ingest", {
                "platform": scope["platform"], "account_id": scope["account_id"],
                "records": fetched["records"], "confirmed_read": True,
                "approval_ref": scope["approval_ref"],
            })
        else:
            ingest = {"screened": 0, "quarantined": 0, "duplicates": 0, "keys": []}
        return {
            "result": "complete" if fetched["complete"] else "partial_requires_attention",
            "fetch_path": _relative(self.root, evidence),
            "screened": ingest["screened"],
            "quarantined": ingest["quarantined"],
            "duplicates": ingest["duplicates"],
            "expired": fetched["expired"],
            "latest_outbound": fetched["latest_outbound"],
            "unsupported": fetched["unsupported"],
            "pagination_complete": fetched["complete"],
            "external_writes": False,
        }

    def execute_api(self, data, *, resume=False):
        """傳送一則純文字並讀回；續查只讀既有 message ID。"""

        _require(isinstance(data, dict)
                 and set(data) == {"batch_id", "key", "allow_token_refresh"}
                 and data["allow_token_refresh"] in {True, False},
                 "execute_fields")
        batch_id, key = data["batch_id"], data["key"]
        state, _, item = _item_context(self.root, batch_id, key)
        source = item["source"]
        scope = _scope(item, allow_refresh=data["allow_token_refresh"])
        self.adapter.verify_access(scope)
        if resume:
            bundle = queue.run(self.root, "resume", {
                "batch_id": batch_id, "key": key,
            })
            message_id = bundle["message_id"]
        else:
            current = self.adapter.read_conversation(scope, source["conversation_id"])
            bundle = queue.run(self.root, "begin", {
                "batch_id": batch_id, "key": key, "current": current,
            })
            message_id = None
            try:
                claim = queue.run(self.root, "claim", {
                    "batch_id": batch_id, "key": key, "stage": "message_send",
                })
                created = self.adapter.send_text(
                    _grant(claim, allow_refresh=data["allow_token_refresh"]))
                message_id = created["message_id"]
                queue.run(self.root, "checkpoint", {
                    "batch_id": batch_id, "key": key, "remote_id": message_id,
                })
            except DirectMessageAPIError as error:
                status = "unknown" if error.kind == "remote_result_unknown" else "failed"
                _record_simple(self.root, batch_id, key, status)
                return {"result": status, "reason": error.kind,
                        "external_write_may_have_occurred": status == "unknown"}
        try:
            readback = self.adapter.read_message(
                scope, source["conversation_id"], source["visitor_id"], message_id)
        except DirectMessageAPIError as error:
            _record_simple(self.root, batch_id, key, "pending")
            return {"result": "pending", "reason": error.kind,
                    "external_write_may_have_occurred": True}
        result = _receipt(self.root, batch_id, key, readback)
        return {"result": result["result"], "external_write_verified": True}

    def resolve_unknown_api(self, data):
        """只讀查明 unknown；唯一訊息吻合才綁回原 claim，不重新傳送。"""

        _require(isinstance(data, dict)
                 and set(data) == {"batch_id", "key", "allow_token_refresh"}
                 and data["allow_token_refresh"] in {True, False},
                 "resolve_fields")
        state, _, item = _item_context(self.root, data["batch_id"], data["key"])
        attempt = state.get("attempts", {}).get(data["key"])
        _require(attempt and attempt["state"] == "unknown"
                 and not attempt.get("message_created"), "attempt_not_unknown")
        source = item["source"]
        scope = _scope(item, allow_refresh=data["allow_token_refresh"])
        self.adapter.verify_access(scope)
        try:
            readback = self.adapter.find_sent_message(
                scope, source["conversation_id"], source["visitor_id"],
                attempt["text"], attempt["started_at"])
        except DirectMessageAPIError as error:
            return {"result": "unknown", "reason": error.kind,
                    "external_write_may_have_occurred": True}
        queue.run(self.root, "observation-checkpoint", {
            "batch_id": data["batch_id"], "key": data["key"],
            "remote_id": readback["message_id"],
        })
        result = _receipt(self.root, data["batch_id"], data["key"], readback)
        return {"result": result["result"], "external_write_verified": True}


def run(workspace, command, data, *, adapter=None):
    """提供測試與 CLI 共用入口。"""

    coordinator = DirectMessageCoordinator(workspace, adapter=adapter)
    if command == "fetch-api":
        return coordinator.fetch_api(data)
    if command == "execute-api":
        return coordinator.execute_api(data)
    if command == "resume-api":
        return coordinator.execute_api(data, resume=True)
    if command == "resolve-unknown-api":
        return coordinator.resolve_unknown_api(data)
    raise DirectMessageExecuteError("command_invalid")


def main():
    """CLI 只收私人 JSON 路徑；輸出不含姓名、私訊、草稿或 Token。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=(
        "fetch-api", "execute-api", "resume-api", "resolve-unknown-api",
    ))
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        root = queue.workspace(args.workspace)
        data = queue.read_json(queue.local(root, args.input))
        print(json.dumps(run(root, args.command, data), ensure_ascii=False))
        return 0
    except (DirectMessageExecuteError, DirectMessageAPIError,
            ValueError, TypeError, KeyError, OSError, UnicodeError):
        print('{"result":"stopped","reason":"invalid_or_conflicting_state"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
