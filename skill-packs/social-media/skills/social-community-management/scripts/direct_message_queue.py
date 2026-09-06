#!/usr/bin/env python3
"""Meta 私訊的離線隔離、人工草稿確認與一次性傳送護欄；不連網、不取憑證。"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

import community_queue as common


PLATFORMS = {"facebook", "instagram"}
FIELDS = {
    "platform", "account_id", "conversation_id", "visitor_id", "visitor_name",
    "message_id", "message_text", "message_created_at", "context", "fetched_at",
}
CONTEXT_FIELDS = {
    "message_id", "sender_id", "sender_name", "direction", "text", "created_at",
}
WINDOW = timedelta(hours=24)


def require(ok, reason):
    """錯誤只帶固定代碼，不回顯私訊內容。"""

    if not ok:
        raise ValueError(reason)


def identifier(value):
    """接受 Meta 對話與訊息 ID，但拒絕路徑、空白與控制字元。"""

    require(isinstance(value, str)
            and re.fullmatch(r"[A-Za-z0-9_.-]{1,500}", value), "id_invalid")
    return value


def within_window(message_time, observed_time=None):
    """只接受沒有超過標準 24 小時、且不在未來的訊息。"""

    message = common.instant(message_time)
    observed = common.instant(observed_time or common.now())
    return timedelta(0) <= observed - message <= WINDOW


def source(record, platform, account):
    """驗證一則由訪客最新發起的純文字私訊與最近文字脈絡。"""

    require(isinstance(record, dict) and set(record) == FIELDS, "source_fields")
    require(record["platform"] == platform in PLATFORMS
            and record["account_id"] == account, "scope_mismatch")
    for field in ("account_id", "conversation_id", "visitor_id", "message_id"):
        identifier(record[field])
    common.instant(record["message_created_at"])
    common.instant(record["fetched_at"])
    require(within_window(record["message_created_at"], record["fetched_at"]),
            "message_window_expired")
    require(isinstance(record["visitor_name"], str)
            and isinstance(record["message_text"], str)
            and bool(record["message_text"].strip()), "source_type")
    context = record["context"]
    require(isinstance(context, list) and 0 < len(context) <= 20, "context_invalid")
    for row in context:
        require(isinstance(row, dict) and set(row) == CONTEXT_FIELDS,
                "context_fields")
        for field in ("message_id", "sender_id"):
            identifier(row[field])
        require(row["direction"] in {"inbound", "outbound"}
                and isinstance(row["sender_name"], str)
                and isinstance(row["text"], str) and bool(row["text"].strip()),
                "context_invalid")
        common.instant(row["created_at"])
    latest = context[0]
    require(latest["message_id"] == record["message_id"]
            and latest["sender_id"] == record["visitor_id"]
            and latest["direction"] == "inbound"
            and latest["text"] == record["message_text"]
            and latest["created_at"] == record["message_created_at"],
            "latest_inbound_mismatch")
    key = common.digest([platform, account, record["message_id"]])
    fingerprint = common.digest({key: value for key, value in record.items()
                                 if key != "fetched_at"})
    values = [record["visitor_name"], record["message_text"]]
    values.extend(value for row in context for value in (row["sender_name"], row["text"]))
    reasons = sorted({reason for value in values for reason in common.screen(value)})
    return key, fingerprint, reasons


def workspace(raw):
    """沿用公開留言的私人工作區邊界。"""

    return common.workspace(raw)


def local(root, relative):
    """沿用共同的相對路徑與 symlink 防護。"""

    return common.local(root, relative)


def read_json(path):
    """沿用共同輸入大小與 JSON 解析限制。"""

    return common.read_json(path)


def state_path(root):
    """提供人工審查介面固定且不公開的私訊狀態位置。"""

    return local(root, "social-media/community/direct-messages/state.json")


@contextmanager
def storage(root):
    """私訊狀態使用獨立鎖與原子替換，不與公開留言混用。"""

    directory = local(root, "social-media/community/direct-messages")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = state_path(root)
    lock = local(root, "social-media/community/direct-messages/queue.lock")
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    temporary = None
    try:
        os.close(descriptor)
        state = read_json(target) if target.exists() else {
            "schema_version": 1, "items": {}, "quarantine": [],
            "batches": {}, "attempts": {},
        }
        require(state.get("schema_version") == 1, "state_version")
        yield state
        encoded = json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8")
        require(len(encoded) <= 16_000_000, "state_full")
        descriptor, name = tempfile.mkstemp(prefix=".direct-message-", dir=directory)
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
        if os.name == "posix":
            directory_descriptor = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
        lock.unlink()


def _review_session(root, data):
    """核對完成的本機人工頁面，避免沒有看過草稿就建立回覆批次。"""

    relative = data.get("review_session_path")
    expected_hash = data.get("review_session_sha256")
    require(isinstance(relative, str)
            and relative.startswith("social-media/community/direct-messages/manual-reviews/")
            and relative.endswith(".json")
            and re.fullmatch(r"[0-9a-f]{64}", str(expected_hash)),
            "review_session_invalid")
    path = local(root, relative)
    require(path.is_file() and path.stat().st_size <= 2_000_000,
            "review_session_invalid")
    encoded = path.read_bytes()
    require(hashlib.sha256(encoded).hexdigest() == expected_hash,
            "review_session_changed")
    value = json.loads(encoded.decode("utf-8"))
    require(value.get("schema_version") == 1
            and value.get("kind") == "manual_direct_message_review"
            and value.get("status") == "complete"
            and isinstance(value.get("entries"), list), "review_session_invalid")
    entries = value["entries"]
    require(all(entry.get("status") in {"ready", "quarantined"}
                for entry in entries), "review_session_incomplete")
    return value


def operate(state, action, data):
    """執行私訊純本機狀態轉換。"""

    if action == "ingest":
        require(data.get("platform") in PLATFORMS, "platform_invalid")
        identifier(data.get("account_id"))
        require(data.get("confirmed_read") is True
                and isinstance(data.get("approval_ref"), str)
                and bool(data["approval_ref"].strip()), "read_approval_required")
        records = data.get("records")
        require(isinstance(records, list) and len(records) <= 20, "batch_size")
        result = {"screened": 0, "quarantined": 0, "duplicates": 0, "keys": []}
        for record in records:
            try:
                key, fingerprint, reasons = source(
                    record, data["platform"], data["account_id"])
            except (ValueError, TypeError, KeyError):
                state["quarantine"].append({"reason": "malformed_or_out_of_scope"})
                result["quarantined"] += 1
                continue
            old = state["items"].get(key)
            if old:
                if old["source_hash"] == fingerprint:
                    result["duplicates"] += 1
                    continue
                old["state"] = "quarantined"
                state["quarantine"].append({"key": key, "reason": "source_changed"})
                result["quarantined"] += 1
                continue
            status = "quarantined" if reasons else "screened"
            state["items"][key] = {
                "source": record, "source_hash": fingerprint, "reasons": reasons,
                "state": status, "read_approval_ref": data["approval_ref"],
            }
            result[status] += 1
            if status == "screened":
                result["keys"].append({"key": key, "source_hash": fingerprint})
        return result
    if action == "review":
        item = state["items"][data["key"]]
        require(item["state"] == "screened"
                and data["source_hash"] == item["source_hash"],
                "review_source_changed")
        require(data.get("reviewer") == "human", "isolated_ai_not_enabled")
        require(isinstance(data.get("review_ref"), str)
                and data["review_ref"].strip(), "review_evidence_required")
        require(data.get("decision") in {"allow", "uncertain", "quarantine"},
                "decision_invalid")
        if data["decision"] != "allow":
            item["state"] = "quarantined"
            item["reasons"] = [data["decision"]]
            return {"result": "quarantined"}
        for field in ("conversation_summary", "draft"):
            require(isinstance(data.get(field), str) and data[field].strip()
                    and not common.screen(data[field], 10_000),
                    "draft_requires_review")
        item.update(state="ready", summary=data["conversation_summary"],
                    draft=data["draft"], review_ref=data["review_ref"],
                    reviewer="human")
        return {"result": "ready"}
    if action == "prepare":
        identifier(data["batch_id"])
        require(data["batch_id"] not in state["batches"], "batch_exists")
        require(data.get("review_verified") is True, "review_session_invalid")
        keys = data.get("keys")
        require(isinstance(keys, list) and 0 < len(keys) <= 20
                and len(keys) == len(set(keys)), "batch_keys")
        rows = {}
        for key in keys:
            item = state["items"][key]
            require(item["state"] == "ready", "item_not_ready")
            rows[key] = item["draft"]
            item["state"] = "batched"
        state["batches"][data["batch_id"]] = {
            "status": "awaiting_approval", "created_at": common.now(),
            "keys": keys, "replies": rows,
            "review_session_path": data["review_session_path"],
            "review_session_sha256": data["review_session_sha256"],
        }
        return {"result": "awaiting_approval", "batch_id": data["batch_id"],
                "reply_count": len(keys), "external_write": False}
    batch = state["batches"][data["batch_id"]]
    if action == "approve":
        require(batch["status"] == "awaiting_approval", "batch_not_reviewable")
        require(data.get("confirmed_reply") is True
                and isinstance(data.get("approval_ref"), str)
                and data["approval_ref"].strip(), "reply_approval_required")
        require(not any(key in state["attempts"] for key in batch["keys"]),
                "batch_already_started")
        batch.update(status="approved", approval_ref=data["approval_ref"],
                     approved_at=common.now())
        return {"result": "approved", "reply_count": len(batch["keys"])}
    if action == "begin":
        require(batch["status"] == "approved", "approval_required")
        key = data["key"]
        require(key in batch["keys"] and key not in state["attempts"],
                "duplicate_or_skipped")
        require(not any(attempt["state"] != "replied"
                        for attempt in state["attempts"].values()),
                "previous_reply_unverified")
        remaining = [candidate for candidate in batch["keys"]
                     if candidate not in state["attempts"]]
        require(remaining and key == remaining[0], "reply_order")
        item = state["items"][key]
        require(item["state"] == "batched", "item_changed")
        current_key, current_hash, reasons = source(
            data["current"], item["source"]["platform"],
            item["source"]["account_id"])
        common.fresh(data["current"]["fetched_at"], batch["approved_at"])
        require(within_window(data["current"]["message_created_at"]),
                "message_window_expired")
        require(current_key == key and current_hash == item["source_hash"]
                and not reasons, "conversation_changed")
        state["attempts"][key] = {
            "state": "in_flight", "started_at": common.now(),
            "batch_id": data["batch_id"], "text": batch["replies"][key],
            "operations": [],
        }
        record = item["source"]
        return {"platform": record["platform"], "account_id": record["account_id"],
                "conversation_id": record["conversation_id"],
                "recipient_id": record["visitor_id"], "text": batch["replies"][key]}
    if action == "resume":
        key = data["key"]
        attempt = state["attempts"].get(key)
        require(attempt and attempt["batch_id"] == data["batch_id"]
                and attempt["state"] == "pending"
                and attempt.get("message_created"), "attempt_not_resumable")
        attempt["state"] = "in_flight"
        record = state["items"][key]["source"]
        return {"platform": record["platform"], "account_id": record["account_id"],
                "conversation_id": record["conversation_id"],
                "recipient_id": record["visitor_id"], "text": attempt["text"],
                "message_id": attempt["message_created"]}
    if action == "claim":
        attempt = state["attempts"][data["key"]]
        require(attempt["batch_id"] == data["batch_id"]
                and attempt["state"] == "in_flight", "attempt_invalid")
        require(data.get("stage") == "message_send", "stage_invalid")
        require(not attempt["operations"], "stage_already_claimed_do_not_resend")
        attempt["operations"].append({
            "stage": "message_send", "state": "claimed", "claimed_at": common.now(),
        })
        record = state["items"][data["key"]]["source"]
        return {"platform": record["platform"], "account_id": record["account_id"],
                "conversation_id": record["conversation_id"],
                "recipient_id": record["visitor_id"], "text": attempt["text"],
                "transaction_status": "in_flight", "stage": "message_send",
                "approval_ref": batch["approval_ref"]}
    if action in {"checkpoint", "observation-checkpoint"}:
        attempt = state["attempts"][data["key"]]
        expected_state = {"in_flight"} if action == "checkpoint" else {"pending", "unknown"}
        require(attempt["batch_id"] == data["batch_id"]
                and attempt["state"] in expected_state
                and not attempt.get("message_created"), "attempt_invalid")
        identifier(data["remote_id"])
        operations = attempt["operations"]
        require(len(operations) == 1 and operations[0]["stage"] == "message_send"
                and operations[0]["state"] == "claimed", "stage_claim_required")
        operations[0]["state"] = "checkpointed"
        attempt["message_created"] = data["remote_id"]
        attempt.setdefault("checkpoints", []).append({
            "stage": "message_created", "claim_stage": "message_send",
            "remote_id": data["remote_id"], "saved_at": common.now(),
            "resolved_by_independent_observation": action == "observation-checkpoint",
        })
        return {"result": "checkpointed"}
    if action == "record":
        attempt = state["attempts"][data["key"]]
        require(attempt["batch_id"] == data["batch_id"]
                and attempt["state"] != "replied", "attempt_invalid")
        receipt = data["receipt"]
        require(receipt.get("state") in {"replied", "pending", "unknown", "failed"},
                "receipt_state")
        fields = {
            "state", "message_id", "account_id", "conversation_id", "recipient_id",
            "text", "observed_at", "platform_time", "sender_matches",
            "recipient_matches", "conversation_matches", "evidence_path",
            "evidence_sha256",
        }
        require(set(receipt) == (fields if receipt["state"] == "replied" else {"state"}),
                "receipt_fields")
        if receipt["state"] == "replied":
            record = state["items"][data["key"]]["source"]
            identifier(receipt["message_id"])
            require(receipt["account_id"] == record["account_id"]
                    and receipt["conversation_id"] == record["conversation_id"]
                    and receipt["recipient_id"] == record["visitor_id"]
                    and receipt["text"] == attempt["text"], "readback_mismatch")
            require(receipt["message_id"] == attempt.get("message_created"),
                    "message_id_changed")
            common.fresh(receipt["observed_at"], attempt["started_at"])
            require(common.instant(attempt["started_at"]).replace(microsecond=0)
                    <= common.instant(receipt["platform_time"])
                    <= common.instant(receipt["observed_at"]), "platform_time_invalid")
            require(receipt["sender_matches"] is True
                    and receipt["recipient_matches"] is True
                    and receipt["conversation_matches"] is True,
                    "readback_identity_missing")
            require(data.get("evidence_verified") is True, "evidence_missing")
        attempt.update(state=receipt["state"], receipt=receipt)
        return {"result": receipt["state"]}
    raise ValueError("action_invalid")


def run(root, action, data):
    """先驗人工 session／讀回證據，再用獨立鎖保存狀態。"""

    root = workspace(root)
    data = dict(data)
    if action == "prepare":
        session = _review_session(root, data)
        require([entry["key"] for entry in session["entries"]
                 if entry.get("status") == "ready"] == data.get("keys"),
                "review_session_keys")
        data["review_verified"] = True
    if action == "record" and data["receipt"]["state"] == "replied":
        evidence = local(root, data["receipt"]["evidence_path"])
        require(evidence.is_file() and evidence.stat().st_size <= 4_000_000,
                "evidence_missing")
        require(hashlib.sha256(evidence.read_bytes()).hexdigest()
                == data["receipt"]["evidence_sha256"], "evidence_changed")
        data["evidence_verified"] = True
    with storage(root) as state:
        return operate(state, action, data)


def main():
    """CLI 只接受私人檔案位置，輸出不含私訊或草稿。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=(
        "ingest", "review", "prepare", "approve", "begin", "resume",
        "claim", "checkpoint", "observation-checkpoint", "record",
    ))
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        root = workspace(args.workspace)
        result = run(root, args.action, read_json(local(root, args.input)))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, TypeError, KeyError, OSError, UnicodeError):
        print('{"result":"stopped","reason":"invalid_or_conflicting_state"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
