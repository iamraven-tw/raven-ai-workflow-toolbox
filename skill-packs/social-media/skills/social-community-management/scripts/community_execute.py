#!/usr/bin/env python3
"""將官方留言 adapter／受控瀏覽器交接接到本機 queue 護欄。"""

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
from official_community_api import CommunityAPIError, OfficialCommunityAdapter
from official_sheets_api import SheetsAPIError


class CommunityExecuteError(RuntimeError):
    """對 CLI 只顯示固定失敗狀態，不夾帶訪客文字。"""


def _require(ok, reason):
    """失敗不回顯輸入內容。"""

    if not ok:
        raise CommunityExecuteError(reason)


def _state(root):
    """讀取本機 queue 狀態；真正修改仍交由 queue 的鎖與原子寫入。"""

    path = queue.local(root, "social-media/community/state.json")
    _require(path.is_file(), "queue_not_initialized")
    value = queue.read_json(path)
    _require(value.get("schema_version") == 1, "queue_version")
    return value


def _write_json(root, relative, value):
    """將含外部文字的證據以 0600 原子寫入私人工作區。"""

    path = queue.local(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    encoded = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
    _require(len(encoded) <= 8_000_000, "evidence_too_large")
    descriptor, name = tempfile.mkstemp(prefix=".community-execute-", dir=path.parent)
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
    """所有交接與證據路徑都維持在私人工作區內。"""

    return str(path.relative_to(root))


def _item_context(root, batch_id, key):
    """讀出已核准批次與留言，不把文字放進一般輸出。"""

    state = _state(root)
    batch = state.get("batches", {}).get(batch_id)
    item = state.get("items", {}).get(key)
    _require(batch and item and key in batch.get("rows", {}), "item_not_in_batch")
    return state, batch, item


def _scope(item, *, allow_refresh):
    """把已保存的讀取核准與來源範圍交給官方 adapter。"""

    source = item["source"]
    return {
        "platform": source["platform"], "account_id": source["account_id"],
        "post_id": source["post_id"], "approval_ref": item["read_approval_ref"],
        "confirmed_read": True, "allow_token_refresh": allow_refresh,
        "url_observations": {source["comment_id"]: source["comment_url"]},
    }


def _grant(claim, source, *, allow_refresh):
    """只加入低階 adapter 所需的貼文識別與刷新選擇。"""

    return {
        "platform": claim["platform"], "account_id": claim["account_id"],
        "post_id": source["post_id"], "comment_id": claim["comment_id"],
        "reply_target_id": claim["reply_target_id"], "text": claim["text"],
        "approval_ref": claim["approval_ref"],
        "transaction_status": claim["transaction_status"], "stage": claim["stage"],
        "allow_token_refresh": allow_refresh,
    }


def _record_simple(root, batch_id, key, state):
    """保存 pending／unknown／failed；這些狀態都不得自動重送。"""

    return queue.run(root, "record", {"batch_id": batch_id, "key": key,
                                      "receipt": {"state": state}})


def _receipt(root, batch_id, key, readback):
    """將獨立讀回轉成 queue 的完整 receipt 並先保存證據。"""

    state, _, item = _item_context(root, batch_id, key)
    attempt = state["attempts"].get(key)
    source = item["source"]
    _require(attempt and readback["reply_id"] == attempt.get("reply_created"),
             "reply_checkpoint_mismatch")
    _require(readback["reply_target_id"] == source["reply_target_id"]
             and readback["text"] == attempt["text"]
             and readback["author_owned"] is True and readback.get("url"),
             "readback_incomplete")
    evidence_value = {
        "schema_version": 1, "kind": "community_reply_readback",
        "platform": source["platform"], "account_id": source["account_id"],
        "post_id": source["post_id"], "comment_id": source["comment_id"],
        "readback": readback,
    }
    relative = f"social-media/community/readbacks/{key}-{readback['reply_id']}.json"
    evidence = _write_json(root, relative, evidence_value)
    value = {
        "state": "replied", "reply_id": readback["reply_id"],
        "account_id": source["account_id"],
        "reply_target_id": readback["reply_target_id"], "text": readback["text"],
        "url": readback["url"], "platform_time": readback["platform_time"],
        "observed_at": readback["observed_at"], "parent_matches": True,
        "author_matches": True, "evidence_path": _relative(root, evidence),
        "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
    }
    return queue.run(root, "record", {"batch_id": batch_id, "key": key,
                                      "receipt": value})


class CommunityCoordinator:
    """本機協調器；不將外部留言或最終回覆印到標準輸出。"""

    def __init__(self, workspace, *, adapter=None, sheets=None):
        self.root = queue.workspace(workspace)
        self.adapter = adapter or OfficialCommunityAdapter(self.root)
        self.sheets = sheets

    def _reply_snapshot(self, data, batch_id):
        """正式路徑即時讀 Sheets；內嵌快照只保留給可信測試與底層呼叫。"""

        has_snapshot = "snapshot" in data
        has_refresh = data.get("refresh_sheet") is True
        _require(has_snapshot != has_refresh, "sheet_snapshot_source")
        if has_snapshot:
            return data["snapshot"]
        if self.sheets is None:
            # 延遲載入可避免單純讀留言時要求 Google Sheets 執行環境。
            from community_sheets import CommunitySheetsCoordinator

            self.sheets = CommunitySheetsCoordinator(self.root)
        return self.sheets.current_snapshot(batch_id)["snapshot"]

    def fetch_api(self, data):
        """讀取官方 API、直接保存本機，再將有可靠 URL 的項目送隔離。"""

        _require(set(data) == {"fetch_id", "scope"}, "fetch_fields")
        queue.identifier(data["fetch_id"])
        scope = data["scope"]
        self.adapter.verify_access(scope)
        fetched = self.adapter.fetch_comments(scope)
        evidence = _write_json(
            self.root, f"social-media/community/fetches/{data['fetch_id']}.json",
            {"schema_version": 1, "kind": "official_api_fetch", "scope": {
                "platform": scope["platform"], "account_id": scope["account_id"],
                "post_id": scope["post_id"], "approval_ref": scope["approval_ref"],
            }, **fetched})
        if fetched["records"]:
            ingest = queue.run(self.root, "ingest", {
                "platform": scope["platform"], "account_id": scope["account_id"],
                "records": fetched["records"], "confirmed_read": True,
                "approval_ref": scope["approval_ref"],
            })
        else:
            ingest = {"screened": 0, "quarantined": 0, "duplicates": 0, "keys": []}
        return {
            "result": "complete" if fetched["complete"] and not fetched["missing_url_records"]
            else "partial_requires_attention",
            "fetch_path": _relative(self.root, evidence), "screened": ingest["screened"],
            "quarantined": ingest["quarantined"], "duplicates": ingest["duplicates"],
            "missing_comment_urls": len(fetched["missing_url_records"]),
            "pagination_complete": fetched["complete"], "external_writes": False,
        }

    def ingest_browser(self, data):
        """接收可信瀏覽器直接擷取的最小欄位；仍先落本機隔離。"""

        required = {"fetch_id", "platform", "account_id", "approval_ref", "confirmed_read",
                    "custom_host", "records", "complete", "observed_at"}
        _require(isinstance(data, dict) and set(data) == required, "browser_fetch_fields")
        queue.identifier(data["fetch_id"])
        queue.instant(data["observed_at"])
        _require(data["confirmed_read"] is True and data["complete"] in {True, False}
                 and isinstance(data["records"], list), "browser_fetch_invalid")
        evidence = _write_json(
            self.root, f"social-media/community/fetches/{data['fetch_id']}.json",
            {"schema_version": 1, "kind": "controlled_browser_fetch", **data})
        ingest = queue.run(self.root, "ingest", {
            "platform": data["platform"], "account_id": data["account_id"],
            "records": data["records"], "custom_host": data["custom_host"],
            "confirmed_read": True, "approval_ref": data["approval_ref"],
        }) if data["records"] else {
            "screened": 0, "quarantined": 0, "duplicates": 0, "keys": []}
        return {"result": "complete" if data["complete"] else "partial_requires_attention",
                "fetch_path": _relative(self.root, evidence), "screened": ingest["screened"],
                "quarantined": ingest["quarantined"], "duplicates": ingest["duplicates"],
                "external_writes": False}

    def _preflight(self, batch_id, key, snapshot, *, allow_refresh, resume):
        """在 queue begin／resume 前重新讀留言並完整查自家回覆。"""

        state, _, item = _item_context(self.root, batch_id, key)
        source = item["source"]
        scope = _scope(item, allow_refresh=allow_refresh)
        self.adapter.verify_access(scope)
        current = self.adapter.read_comment(
            scope, source["comment_id"], source["comment_url"])
        own = self.adapter.own_replies(scope, source["comment_id"])
        _require(own["complete"], "own_reply_check_incomplete")
        attempt = state.get("attempts", {}).get(key) if resume else None
        expected_reply = attempt.get("reply_created") if attempt else None
        owned_ids = set(own["owned_reply_ids"])
        if expected_reply:
            # 只允許讀回先前 checkpoint 的同一回覆；其他自家回覆仍視為競態。
            _require(not (owned_ids - {expected_reply}), "reply_already_exists")
        else:
            _require(not owned_ids, "reply_already_exists")
        action = "resume" if resume else "begin"
        bundle = queue.run(self.root, action, {
            "batch_id": batch_id, "key": key, "snapshot": snapshot,
            "current": current, "own_reply_check": "none_found_complete",
        })
        return state, item, scope, bundle

    def execute_api(self, data, *, resume=False):
        """回覆一則並獨立讀回；任何不明狀態都阻擋後續。"""

        common = {"batch_id", "key", "allow_token_refresh"}
        _require(frozenset(data) in {frozenset(common | {"snapshot"}),
                                     frozenset(common | {"refresh_sheet"})},
                 "execute_fields")
        _require(data["allow_token_refresh"] in {True, False}, "refresh_choice")
        batch_id, key = data["batch_id"], data["key"]
        snapshot = self._reply_snapshot(data, batch_id)
        _, item, scope, bundle = self._preflight(
            batch_id, key, snapshot, allow_refresh=data["allow_token_refresh"],
            resume=resume)
        platform, source = bundle["platform"], item["source"]
        reply_id = bundle.get("reply_id")
        try:
            if platform == "threads":
                container_id = bundle.get("container_id")
                if not container_id:
                    claim = queue.run(self.root, "claim", {
                        "batch_id": batch_id, "key": key, "stage": "reply_container"})
                    created = self.adapter.create_threads_container(
                        _grant(claim, source, allow_refresh=data["allow_token_refresh"]))
                    container_id = created["container_id"]
                    queue.run(self.root, "checkpoint", {
                        "batch_id": batch_id, "key": key, "stage": "container_created",
                        "claim_stage": "reply_container", "remote_id": container_id})
                status = self.adapter.threads_container_status(scope, container_id)
                if status["status"] == "IN_PROGRESS":
                    _record_simple(self.root, batch_id, key, "pending")
                    return {"result": "pending", "reason": "container_processing",
                            "external_write_may_have_occurred": True}
                if status["status"] == "PUBLISHED":
                    _record_simple(self.root, batch_id, key, "unknown")
                    return {"result": "unknown", "reason": "container_published_without_reply_id",
                            "external_write_may_have_occurred": True}
                if status["status"] != "FINISHED":
                    _record_simple(self.root, batch_id, key, "failed")
                    return {"result": "failed", "reason": "container_rejected",
                            "external_write_may_have_occurred": True}
                if not reply_id:
                    claim = queue.run(self.root, "claim", {
                        "batch_id": batch_id, "key": key, "stage": "reply_publish"})
                    published = self.adapter.publish_threads_reply(
                        _grant(claim, source, allow_refresh=data["allow_token_refresh"]),
                        container_id)
                    reply_id = published["reply_id"]
                    queue.run(self.root, "checkpoint", {
                        "batch_id": batch_id, "key": key, "stage": "reply_created",
                        "claim_stage": "reply_publish", "remote_id": reply_id})
            elif not reply_id:
                claim = queue.run(self.root, "claim", {
                    "batch_id": batch_id, "key": key, "stage": "reply_create"})
                created = self.adapter.create_reply(
                    _grant(claim, source, allow_refresh=data["allow_token_refresh"]))
                reply_id = created["reply_id"]
                queue.run(self.root, "checkpoint", {
                    "batch_id": batch_id, "key": key, "stage": "reply_created",
                    "claim_stage": "reply_create", "remote_id": reply_id})
        except CommunityAPIError as error:
            status = "unknown" if error.kind == "remote_result_unknown" else "failed"
            _record_simple(self.root, batch_id, key, status)
            return {"result": status, "reason": error.kind,
                    "external_write_may_have_occurred": status == "unknown"}
        try:
            readback = self.adapter.read_reply(
                scope, source["reply_target_id"], reply_id)
        except CommunityAPIError as error:
            _record_simple(self.root, batch_id, key, "pending")
            return {"result": "pending", "reason": error.kind,
                    "external_write_may_have_occurred": True}
        if not readback.get("url"):
            evidence = _write_json(
                self.root, f"social-media/community/readbacks/{key}-{reply_id}-api.json",
                {"schema_version": 1, "kind": "api_readback_missing_permalink",
                 "platform": platform, "readback": readback})
            _record_simple(self.root, batch_id, key, "pending")
            return {"result": "pending", "reason": "browser_permalink_observation_required",
                    "readback_path": _relative(self.root, evidence),
                    "external_write_may_have_occurred": True}
        result = _receipt(self.root, batch_id, key, readback)
        return {"result": result["result"], "external_write_verified": True}

    def prepare_browser_reply(self, data):
        """在受控瀏覽器真正輸入前 begin 與 claim，回傳私人 handoff 路徑。"""

        common = {"batch_id", "key", "current", "own_reply_check"}
        _require(frozenset(data) in {frozenset(common | {"snapshot"}),
                                     frozenset(common | {"refresh_sheet"})}
                 and data["own_reply_check"] == "none_found_complete",
                 "browser_reply_fields")
        snapshot = self._reply_snapshot(data, data["batch_id"])
        _, _, item = _item_context(self.root, data["batch_id"], data["key"])
        bundle = queue.run(self.root, "begin", {
            "batch_id": data["batch_id"], "key": data["key"],
            "snapshot": snapshot, "current": data["current"],
            "own_reply_check": data["own_reply_check"],
        })
        source = item["source"]
        handoff_value = {
            "schema_version": 1, "kind": "controlled_browser_reply",
            "platform": bundle["platform"], "account_id": bundle["account_id"],
            "post_id": source["post_id"], "comment_id": bundle["comment_id"],
            "reply_target_id": bundle["reply_target_id"], "comment_url": source["comment_url"],
            "text": bundle["text"], "single_submit_only": True,
            "required_readback": ["reply_id", "reply_target_id", "text", "url",
                                  "platform_time", "observed_at", "author_owned"],
        }
        path = _write_json(
            self.root, f"social-media/community/handoffs/{data['key']}-reply.json",
            handoff_value)
        queue.run(self.root, "claim", {
            "batch_id": data["batch_id"], "key": data["key"], "stage": "browser_reply"})
        return {"result": "browser_handoff_ready", "handoff_path": _relative(self.root, path),
                "external_write_performed": False}

    def record_observation(self, data):
        """以 API 後補 permalink 或瀏覽器完整重載證據完成同一 attempt。"""

        _require(set(data) == {"batch_id", "key", "observation"}, "observation_fields")
        state, _, item = _item_context(self.root, data["batch_id"], data["key"])
        attempt = state.get("attempts", {}).get(data["key"])
        _require(attempt and attempt["state"] in {"in_flight", "pending", "unknown"},
                 "attempt_not_observable")
        observation = data["observation"]
        if set(observation) == {"state"} and observation["state"] in {
                "pending", "unknown", "failed"}:
            return _record_simple(self.root, data["batch_id"], data["key"],
                                  observation["state"])
        required = {"reply_id", "reply_target_id", "text", "url", "platform_time",
                    "observed_at", "author_owned"}
        _require(isinstance(observation, dict) and set(observation) == required,
                 "observation_readback_fields")
        source = item["source"]
        queue.identifier(observation["reply_id"])
        queue.identifier(observation["reply_target_id"])
        queue.platform_url(source["platform"], observation["url"], item.get("custom_host"))
        queue.instant(observation["platform_time"])
        queue.instant(observation["observed_at"])
        if not attempt.get("reply_created"):
            # 不明結果不能重送；只有找到同一則回覆時，才能綁回原本唯一的寫入 claim。
            claim_stages = [
                operation["stage"] for operation in attempt.get("operations", [])
                if operation.get("state") == "claimed"
                and operation.get("stage") in {
                    "reply_create", "reply_publish", "browser_reply"
                }
            ]
            _require(len(claim_stages) == 1, "observation_claim_ambiguous")
            if attempt["state"] == "in_flight":
                queue.run(self.root, "checkpoint", {
                    "batch_id": data["batch_id"], "key": data["key"],
                    "stage": "reply_created", "claim_stage": claim_stages[0],
                    "remote_id": observation["reply_id"],
                })
            else:
                queue.run(self.root, "observation-checkpoint", {
                    "batch_id": data["batch_id"], "key": data["key"],
                    "claim_stage": claim_stages[0],
                    "remote_id": observation["reply_id"],
                })
        readback = dict(observation)
        result = _receipt(self.root, data["batch_id"], data["key"], readback)
        return {"result": result["result"], "external_write_verified": True}


def run(workspace, command, data, *, adapter=None, sheets=None):
    """提供測試與 CLI 共用入口。"""

    coordinator = CommunityCoordinator(workspace, adapter=adapter, sheets=sheets)
    if command == "fetch-api":
        return coordinator.fetch_api(data)
    if command == "ingest-browser":
        return coordinator.ingest_browser(data)
    if command == "execute-api":
        return coordinator.execute_api(data)
    if command == "resume-api":
        return coordinator.execute_api(data, resume=True)
    if command == "prepare-browser-reply":
        return coordinator.prepare_browser_reply(data)
    if command == "record-observation":
        return coordinator.record_observation(data)
    raise CommunityExecuteError("command_invalid")


def main():
    """命令列僅接受工作區內 JSON；輸出不含留言、回覆或 Token。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("fetch-api", "ingest-browser", "execute-api",
                                            "resume-api", "prepare-browser-reply",
                                            "record-observation"))
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        root = queue.workspace(args.workspace)
        data = queue.read_json(queue.local(root, args.input))
        print(json.dumps(run(root, args.command, data), ensure_ascii=False))
        return 0
    except (CommunityExecuteError, CommunityAPIError, SheetsAPIError,
            ValueError, TypeError, KeyError,
            OSError, UnicodeError):
        print('{"result":"stopped","reason":"invalid_or_conflicting_state"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
