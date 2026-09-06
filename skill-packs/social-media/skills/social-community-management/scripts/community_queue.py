#!/usr/bin/env python3
"""公開留言的離線隔離、六欄審核與一次性回覆護欄；不連網、不取憑證。"""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata
from urllib.parse import urlsplit

HEADERS = ["訪客名稱", "原貼文內容", "原訪客留言", "原貼文摘要", "訪客留言網址", "AI 回覆草稿"]
PLATFORMS = {"youtube", "facebook", "instagram", "threads", "substack"}
FIELDS = {"platform", "account_id", "post_id", "comment_id", "reply_target_id",
          "visitor_id", "visitor_name", "post_text", "comment_text", "comment_url",
          "comment_created_at", "fetched_at"}
PATTERNS = (
    r"(ignore|disregard|override).{0,70}(instruction|system|prompt|rule)",
    r"(忽略|無視|覆寫|跳過).{0,40}(指令|規則|提示)",
    r"(system|developer|assistant|tool)\s*[:：]|[<\[]/?(system|developer|assistant|tool)[>\]]",
    r"(讀取|輸出|洩漏|顯示|read|print|reveal).{0,40}(密碼|憑證|權杖|secret|token|password|\.env)",
    r"(執行|呼叫|run|execute).{0,35}(shell|bash|curl|python|工具|終端|命令)",
    r"(寫入|修改|建立|write|modify).{0,35}(記憶|技能|排程|設定|system prompt|memory|cron)",
    r"base64.{0,20}(decode|解碼)|[A-Za-z0-9+/]{160,}={0,2}",
    r"javascript:|file://|data:text|=HYPERLINK\s*\(|=IMPORT\w*\s*\(",
)


def require(ok, reason):
    """錯誤只輸出固定代碼，不回顯外部留言。"""
    if not ok:
        raise ValueError(reason)


def now():
    """產生有時區的觀測時間。"""
    return datetime.now(timezone.utc).isoformat()


def instant(value):
    """拒絕缺少時區的時間。"""
    require(isinstance(value, str), "time_invalid")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "timezone_missing")
    return parsed


def fresh(value, after=None):
    """讀回限五分鐘內；不接受未來或早於指定關卡的快照。"""
    current, observed = instant(now()), instant(value)
    require(0 <= (current - observed).total_seconds() <= 300, "stale_readback")
    if after:
        require(observed >= instant(after), "readback_before_gate")


def digest(value):
    """序列化雜湊不做文字正規化，保留使用者最終文字。"""
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def identifier(value):
    """平台技術識別不能包含路徑或命令。"""
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", value), "id_invalid")


def screen(value, maximum=40000):
    """固定規則只篩風險，不宣稱可證明語意安全；不改寫或截斷原文。"""
    if not isinstance(value, str) or len(value) > maximum:
        return ["type_or_size"]
    reasons = []
    if any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} and c not in "\n\t" for c in value):
        reasons.append("hidden_or_control")
    normalized = unicodedata.normalize("NFKC", value)
    if any(re.search(p, normalized, re.I | re.S) for p in PATTERNS):
        reasons.append("suspicious_instruction")
    compact = re.sub(r"[\W_]+", "", normalized.casefold())
    if any(m in compact for m in ("ignorepreviousinstructions", "忽略之前指令", "讀取apikey")):
        reasons.append("obfuscated_instruction")
    return sorted(set(reasons))


def platform_url(platform, value, custom_host=None):
    """只核對格式與主機，不開網址；真實歸屬由可信平台讀取器確認。"""
    require(isinstance(value, str) and not screen(value, 3000), "url_invalid")
    parsed = urlsplit(value)
    require(parsed.scheme == "https" and parsed.hostname and not parsed.username
            and not parsed.password and parsed.port in (None, 443), "url_invalid")
    require(not re.search(r"[?&](token|access_token|code|sig|signature|key|auth)=", value, re.I), "secret_url")
    hosts = {
        "youtube": {"youtube.com", "www.youtube.com", "youtu.be"},
        "facebook": {"facebook.com", "www.facebook.com"},
        "instagram": {"instagram.com", "www.instagram.com"},
        "threads": {"threads.net", "www.threads.net", "threads.com", "www.threads.com"},
    }
    host = parsed.hostname
    require(host in hosts.get(platform, set()) or
            (platform == "substack" and (host == "substack.com" or host.endswith(".substack.com")
                                        or host == custom_host)), "platform_host_mismatch")


def source(record, platform, account, custom_host=None):
    """可信讀取器只提供選取欄位，所有外部文字仍要本機篩查。"""
    require(isinstance(record, dict) and set(record) == FIELDS, "source_fields")
    require(record["platform"] == platform in PLATFORMS and record["account_id"] == account, "scope_mismatch")
    for field in ("account_id", "post_id", "comment_id", "reply_target_id", "visitor_id"):
        identifier(record[field])
    instant(record["comment_created_at"])
    instant(record["fetched_at"])
    platform_url(platform, record["comment_url"], custom_host)
    require(all(isinstance(record[f], str) for f in ("visitor_name", "post_text", "comment_text")), "source_type")
    require(bool(record["comment_text"].strip()), "empty_comment")
    key = digest([platform, account, record["comment_id"]])
    fingerprint = digest({k: v for k, v in record.items() if k != "fetched_at"})
    reasons = sorted({r for f in ("visitor_name", "post_text", "comment_text")
                      for r in screen(record[f])})
    return key, fingerprint, reasons


def workspace(raw):
    """拒絕公開套件、技能掃描目錄、廣泛根目錄與 symlink。"""
    root = Path(raw).absolute()
    require(root.is_dir() and root != Path(root.anchor) and root != Path.home(), "workspace_invalid")
    for entry in (root, *root.parents):
        require(not entry.is_symlink() and not (entry / "install.manifest.toml").exists(), "workspace_boundary")
    require(not any(p in {".agents", ".claude", ".codex", ".gemini"} for p in root.parts), "skill_scan_boundary")
    return root


def local(root, relative):
    """輸入檔案必須在明確私人工作區，且不跟隨任何 symlink。"""
    require(isinstance(relative, str) and relative and not relative.startswith(("/", "~"))
            and ":" not in relative and "\\" not in relative, "path_invalid")
    parts = Path(relative).parts
    require(".." not in parts, "path_invalid")
    current = root
    for part in parts:
        current = current / part
        require(not current.is_symlink(), "symlink")
    return current


def read_json(path):
    """限制輸入大小；解析失敗不輸出原文。"""
    require(path.is_file() and path.stat().st_size <= 16_000_000, "file_invalid")
    return json.loads(path.read_text(encoding="utf-8"))


@contextmanager
def storage(root):
    """持久狀態原子寫入；一次命令一把鎖，崩潰鎖不自動清除。"""
    directory = local(root, "social-media/community")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = local(root, "social-media/community/state.json")
    lock = local(root, "social-media/community/queue.lock")
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    temporary = None
    try:
        os.close(descriptor)
        state = read_json(target) if target.exists() else {"schema_version": 1, "items": {}, "quarantine": [], "batches": {}, "attempts": {}}
        require(state.get("schema_version") == 1, "state_version")
        yield state
        encoded = json.dumps(state, ensure_ascii=False, indent=2).encode()
        require(len(encoded) <= 16_000_000, "state_full")
        fd, name = tempfile.mkstemp(prefix=".community-", dir=directory)
        temporary = Path(name)
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        if os.name == "posix":
            directory_fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
        lock.unlink()


def binding(value):
    """試算表識別只留本機；專用分頁固定 A:F。"""
    require(isinstance(value, dict) and set(value) == {"spreadsheet_id", "sheet_id", "title"}, "sheet_binding")
    identifier(value["spreadsheet_id"])
    require(type(value["sheet_id"]) is int and value["sheet_id"] >= 0, "sheet_binding")
    require(isinstance(value["title"], str) and 0 < len(value["title"]) <= 100
            and not screen(value["title"]), "sheet_binding")


def snapshot(batch, snap):
    """接受 userEnteredValue 型別快照；公式、數字或錯置欄列都拒絕。"""
    require(isinstance(snap, dict) and set(snap) == {"binding", "observed_at", "rows"}, "snapshot_fields")
    require(snap["binding"] == batch["binding"], "sheet_changed")
    fresh(snap["observed_at"], batch["created_at"])
    require(isinstance(snap["rows"], list) and len(snap["rows"]) == len(batch["rows"]) + 1, "rows_changed")
    values = []
    for row in snap["rows"]:
        require(isinstance(row, list) and len(row) == 6, "six_columns_required")
        cells = []
        for cell in row:
            require(isinstance(cell, dict) and (not cell or set(cell) == {"stringValue"}), "formula_or_non_text_cell")
            value = cell.get("stringValue", "")
            require(isinstance(value, str), "cell_type")
            cells.append(value)
        values.append(cells)
    require(values[0] == HEADERS, "headers_changed")
    # 對照前五欄，不靠易變的列號；整列排序可接受，部分欄排序無法可靠推定人類意圖。
    expected = {digest(row[:5]): key for key, row in batch["rows"].items()}
    require(len(expected) == len(batch["rows"]), "ambiguous_mapping")
    mapped = {}
    for row in values[1:]:
        key = expected.get(digest(row[:5]))
        require(key and key not in mapped, "source_columns_changed")
        require(not screen(row[5], 10000), "reply_requires_review")
        mapped[key] = row[5]
    return mapped


def operate(state, action, data):
    """執行純本機狀態轉換；回傳資料需在 state 落盤後才交可信執行器。"""
    if action == "ingest":
        require(data["platform"] in PLATFORMS, "platform_invalid")
        identifier(data["account_id"])
        require(data.get("confirmed_read") is True and isinstance(data.get("approval_ref"), str)
                and bool(data["approval_ref"].strip()), "read_approval_required")
        records = data["records"]
        require(isinstance(records, list) and len(records) <= 100, "batch_size")
        result = {"screened": 0, "quarantined": 0, "duplicates": 0, "keys": []}
        for record in records:
            try:
                key, fingerprint, reasons = source(record, data["platform"], data["account_id"], data.get("custom_host"))
            except (ValueError, TypeError, KeyError):
                state["quarantine"].append({"reason": "malformed_or_out_of_scope", "raw": record})
                result["quarantined"] += 1
                continue
            old = state["items"].get(key)
            if old:
                if old["source_hash"] == fingerprint:
                    result["duplicates"] += 1
                    continue
                # 保留原文與既有發布證據，改版只隔離，不覆寫舊核准。
                old["state"] = "quarantined"
                state["quarantine"].append({"key": key, "reason": "source_changed", "raw": record})
                result["quarantined"] += 1
                continue
            status = "quarantined" if reasons else "screened"
            state["items"][key] = {"source": record, "source_hash": fingerprint, "reasons": reasons,
                                   "state": status, "custom_host": data.get("custom_host"),
                                   "read_approval_ref": data["approval_ref"]}
            result[status] += 1
            if status == "screened":
                result["keys"].append({"key": key, "source_hash": fingerprint})
        return result
    if action == "review":
        key = data["key"]
        item = state["items"][key]
        require(item["state"] == "screened" and data["source_hash"] == item["source_hash"], "review_source_changed")
        # 最小 MVP 只啟用可稽核的人工作業；未接通隔離 runtime 前不得自填 AI 標記。
        require(data["reviewer"] == "human", "isolated_ai_not_enabled")
        require(isinstance(data["review_ref"], str) and data["review_ref"].strip(), "review_evidence_required")
        require(data["decision"] in {"allow", "uncertain", "quarantine"}, "decision_invalid")
        if data["decision"] != "allow":
            item["state"] = "quarantined"
            item["reasons"] = [data["decision"]]
            return {"result": "quarantined"}
        for field in ("post_summary", "draft"):
            require(isinstance(data[field], str) and data[field].strip() and not screen(data[field], 10000), "draft_requires_review")
        item.update(state="ready", summary=data["post_summary"], draft=data["draft"],
                    review_ref=data["review_ref"], reviewer=data["reviewer"])
        return {"result": "ready"}
    if action == "export":
        identifier(data["batch_id"])
        require(data["batch_id"] not in state["batches"], "batch_exists")
        binding(data["binding"])
        keys = data["keys"]
        require(isinstance(keys, list) and 0 < len(keys) <= 100 and len(set(keys)) == len(keys), "batch_keys")
        require(data.get("confirmed_sheet_write") is True and data.get("approval_ref"), "sheet_write_approval_required")
        require(not any((b["binding"]["spreadsheet_id"], b["binding"]["sheet_id"]) ==
                        (data["binding"]["spreadsheet_id"], data["binding"]["sheet_id"])
                        for b in state["batches"].values()), "sheet_already_bound")
        rows = {}
        for key in keys:
            item = state["items"][key]
            require(item["state"] == "ready", "item_not_ready")
            record = item["source"]
            rows[key] = [record["visitor_name"], record["post_text"], record["comment_text"],
                         item["summary"], record["comment_url"], item["draft"]]
            item["state"] = "batched"
        require(len({digest(row[:5]) for row in rows.values()}) == len(rows), "ambiguous_mapping")
        batch = {"binding": data["binding"], "created_at": now(), "rows": rows,
                 "status": "sheet_write_pending",
                 "sheet_write_approval_ref": data["approval_ref"],
                 "sheet_operation": None}
        state["batches"][data["batch_id"]] = batch
        title = data["binding"]["title"].replace("'", "''")
        return {"valueInputOption": "RAW", "range": f"'{title}'!A1:F{len(rows)+1}",
                "majorDimension": "ROWS", "values": [HEADERS, *rows.values()]}
    batch = state["batches"][data["batch_id"]]
    if action == "sheet-claim":
        require(batch["status"] == "sheet_write_pending", "sheet_not_writable")
        require(batch.get("sheet_operation") is None, "sheet_write_already_claimed_do_not_resend")
        title = batch["binding"]["title"].replace("'", "''")
        batch["sheet_operation"] = {"state": "claimed", "claimed_at": now()}
        return {"binding": batch["binding"], "valueInputOption": "RAW",
                "range": f"'{title}'!A1:F{len(batch['rows'])+1}",
                "majorDimension": "ROWS", "values": [HEADERS, *batch["rows"].values()],
                "transaction_status": "claimed",
                "approval_ref": batch["sheet_write_approval_ref"]}
    if action == "sheet-write-result":
        require(batch["status"] == "sheet_write_pending", "sheet_not_writable")
        operation = batch.get("sheet_operation")
        require(operation and operation["state"] == "claimed", "sheet_claim_required")
        require(data["state"] in {"request_accepted", "unknown", "failed"},
                "sheet_result_invalid")
        operation.update(state=data["state"], recorded_at=now())
        return {"result": data["state"]}
    if action in {"sheet-verify", "approve", "begin", "resume"}:
        mapped = snapshot(batch, data["snapshot"])
    if action == "sheet-verify":
        require(batch["status"] == "sheet_write_pending", "sheet_already_verified")
        operation = batch.get("sheet_operation")
        require(operation and operation["state"] in {"claimed", "request_accepted", "unknown"},
                "sheet_claim_required")
        require(mapped == {k: v[5] for k, v in batch["rows"].items()}, "sheet_write_mismatch")
        batch["status"] = "awaiting_approval"
        operation.update(state="readback_verified", verified_at=now())
        return {"result": "awaiting_approval"}
    if action == "approve":
        require(batch["status"] in {"awaiting_approval", "approved"}, "batch_not_reviewable")
        require(not any(k in state["attempts"] for k in batch["rows"]), "batch_already_started")
        require(data.get("confirmed_reply") is True and data.get("approval_ref"), "reply_approval_required")
        require(any(v.strip() for v in mapped.values()), "no_replies_selected")
        require(all(state["items"][k]["state"] == "batched" for k in mapped), "item_changed")
        batch.update(status="approved", replies=mapped, approval_ref=data["approval_ref"], approved_at=now())
        return {"result": "approved", "reply_count": sum(bool(v.strip()) for v in mapped.values())}
    if action == "begin":
        require(batch["status"] == "approved", "approval_required")
        fresh(data["snapshot"]["observed_at"], batch["approved_at"])
        require(mapped == batch["replies"], "final_text_changed")
        key = data["key"]
        require(key in mapped and bool(mapped[key].strip()) and key not in state["attempts"], "duplicate_or_skipped")
        require(not any(a["state"] != "replied" for a in state["attempts"].values()), "previous_reply_unverified")
        remaining = [k for k in batch["rows"] if mapped[k].strip() and k not in state["attempts"]]
        require(remaining and key == remaining[0], "reply_order")
        item = state["items"][key]
        require(item["state"] == "batched", "item_changed")
        record = item["source"]
        current = data["current"]
        current_key, current_hash, reasons = source(current, record["platform"], record["account_id"], item["custom_host"])
        fresh(current["fetched_at"], batch["approved_at"])
        require(current_key == key and current_hash == item["source_hash"] and not reasons, "comment_changed")
        require(data.get("own_reply_check") == "none_found_complete", "own_reply_check_required")
        # 先落盤 in_flight，發送後崩潰也不能重新取得執行包。
        state["attempts"][key] = {"state": "in_flight", "started_at": now(),
                                   "batch_id": data["batch_id"], "text": mapped[key],
                                   "operations": []}
        return {"platform": record["platform"], "account_id": record["account_id"],
                "comment_id": record["comment_id"], "reply_target_id": record["reply_target_id"], "text": mapped[key]}
    if action == "resume":
        key = data["key"]
        require(key in mapped and mapped[key].strip(), "duplicate_or_skipped")
        attempt = state["attempts"].get(key)
        require(attempt and attempt["batch_id"] == data["batch_id"]
                and attempt["state"] == "pending", "attempt_not_resumable")
        item = state["items"][key]
        record = item["source"]
        current_key, current_hash, reasons = source(
            data["current"], record["platform"], record["account_id"], item["custom_host"])
        fresh(data["current"]["fetched_at"], batch["approved_at"])
        require(current_key == key and current_hash == item["source_hash"] and not reasons,
                "comment_changed")
        require(data.get("own_reply_check") == "none_found_complete", "own_reply_check_required")
        operations = attempt.setdefault("operations", [])
        require(not any(operation["state"] == "claimed"
                        and operation["stage"] not in {
                            checkpoint.get("claim_stage")
                            for checkpoint in attempt.get("checkpoints", [])
                        } for operation in operations), "unresolved_claim_do_not_resend")
        require(attempt.get("container_created") or attempt.get("reply_created"),
                "resume_checkpoint_required")
        attempt["state"] = "in_flight"
        return {"platform": record["platform"], "account_id": record["account_id"],
                "comment_id": record["comment_id"], "reply_target_id": record["reply_target_id"],
                "text": attempt["text"], "container_id": attempt.get("container_created"),
                "reply_id": attempt.get("reply_created")}
    if action == "claim":
        attempt = state["attempts"][data["key"]]
        require(attempt["batch_id"] == data["batch_id"] and attempt["state"] == "in_flight",
                "attempt_invalid")
        stage = data["stage"]
        require(stage in {"reply_create", "reply_container", "reply_publish", "browser_reply"},
                "stage_invalid")
        operations = attempt.setdefault("operations", [])
        require(not any(operation["stage"] == stage for operation in operations),
                "stage_already_claimed_do_not_resend")
        operations.append({"stage": stage, "state": "claimed", "claimed_at": now()})
        return {"platform": state["items"][data["key"]]["source"]["platform"],
                "account_id": state["items"][data["key"]]["source"]["account_id"],
                "comment_id": state["items"][data["key"]]["source"]["comment_id"],
                "reply_target_id": state["items"][data["key"]]["source"]["reply_target_id"],
                "text": attempt["text"], "transaction_status": "in_flight",
                "stage": stage, "approval_ref": batch["approval_ref"]}
    if action == "observation-checkpoint":
        # 結果不明時不重送；獨立讀回只能解決唯一且仍未完成的原回覆 claim。
        require(set(data) == {"batch_id", "key", "claim_stage", "remote_id"},
                "observation_checkpoint_fields")
        attempt = state["attempts"][data["key"]]
        require(attempt["batch_id"] == data["batch_id"]
                and attempt["state"] in {"pending", "unknown"}
                and not attempt.get("reply_created"), "attempt_invalid")
        identifier(data["remote_id"])
        require(data["claim_stage"] in {
            "reply_create", "reply_publish", "browser_reply"
        }, "claim_stage_invalid")
        unresolved = [operation for operation in attempt.get("operations", [])
                      if operation.get("state") == "claimed"]
        require(len(unresolved) == 1
                and unresolved[0].get("stage") == data["claim_stage"],
                "observation_claim_ambiguous")
        unresolved[0]["state"] = "checkpointed"
        attempt["reply_created"] = data["remote_id"]
        attempt.setdefault("checkpoints", []).append({
            "stage": "reply_created", "claim_stage": data["claim_stage"],
            "remote_id": data["remote_id"], "saved_at": now(),
            "resolved_by_independent_observation": True,
        })
        return {"result": "checkpointed"}
    if action == "checkpoint":
        attempt = state["attempts"][data["key"]]
        require(attempt["batch_id"] == data["batch_id"] and attempt["state"] == "in_flight", "attempt_invalid")
        identifier(data["remote_id"])
        require(data["stage"] in {"container_created", "reply_created"}, "stage_invalid")
        require(data["stage"] not in attempt, "checkpoint_exists")
        claim_stage = "reply_container" if data["stage"] == "container_created" else data.get("claim_stage")
        require(claim_stage in {"reply_create", "reply_publish", "browser_reply"}
                if data["stage"] == "reply_created" else claim_stage == "reply_container",
                "claim_stage_invalid")
        operations = attempt.setdefault("operations", [])
        matches = [operation for operation in operations if operation["stage"] == claim_stage]
        require(len(matches) == 1 and matches[0]["state"] == "claimed", "stage_claim_required")
        matches[0]["state"] = "checkpointed"
        attempt[data["stage"]] = data["remote_id"]
        attempt.setdefault("checkpoints", []).append({"stage": data["stage"],
                                                       "claim_stage": claim_stage,
                                                       "remote_id": data["remote_id"],
                                                       "saved_at": now()})
        return {"result": "checkpointed"}
    if action == "record":
        attempt = state["attempts"][data["key"]]
        require(attempt["batch_id"] == data["batch_id"] and attempt["state"] != "replied", "attempt_invalid")
        receipt = data["receipt"]
        require(receipt["state"] in {"replied", "pending", "unknown", "failed"}, "receipt_state")
        fields = {"state", "reply_id", "account_id", "reply_target_id", "text", "url", "observed_at",
                  "platform_time", "parent_matches", "author_matches", "evidence_path", "evidence_sha256"}
        require(set(receipt) == (fields if receipt["state"] == "replied" else {"state"}), "receipt_fields")
        if receipt["state"] == "replied":
            record = state["items"][data["key"]]["source"]
            identifier(receipt["reply_id"])
            require(receipt["account_id"] == record["account_id"] and receipt["reply_target_id"] == record["reply_target_id"]
                    and receipt["text"] == attempt["text"], "readback_mismatch")
            require(not attempt.get("reply_created") or receipt["reply_id"] == attempt["reply_created"], "reply_id_changed")
            platform_url(record["platform"], receipt["url"], state["items"][data["key"]]["custom_host"])
            fresh(receipt["observed_at"], attempt["started_at"])
            require(instant(attempt["started_at"]).replace(microsecond=0) <= instant(receipt["platform_time"])
                    <= instant(receipt["observed_at"]), "platform_time_invalid")
            require(receipt.get("parent_matches") is True and receipt.get("author_matches") is True, "readback_identity_missing")
            require(data.get("evidence_verified") is True, "evidence_missing")
        attempt.update(state=receipt["state"], receipt=receipt)
        return {"result": receipt["state"]}
    raise ValueError("action_invalid")


def run(root, action, data):
    """所有輸出在原子狀態保存完成後才可使用；檔案證據由本機核對。"""
    root = workspace(root)
    if action == "record" and data["receipt"]["state"] == "replied":
        evidence = local(root, data["receipt"]["evidence_path"])
        require(evidence.is_file() and evidence.stat().st_size <= 4_000_000, "evidence_missing")
        require(hashlib.sha256(evidence.read_bytes()).hexdigest() == data["receipt"]["evidence_sha256"], "evidence_changed")
        data = dict(data, evidence_verified=True)
    with storage(root) as state:
        result = operate(state, action, data)
    return result


def main():
    """命令列只收私人資料檔位置；隔離內容不進 stdout 或錯誤訊息。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["ingest", "review", "export", "sheet-verify", "approve",
                                           "begin", "resume", "claim", "checkpoint", "record"])
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
