#!/usr/bin/env python3
"""本機發布交易護欄；不連網、不取憑證、不代替平台讀回或人類確認。"""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from urllib.parse import urlsplit

FORMATS = {"youtube": {"video"}, "instagram": {"image", "carousel", "reel"},
           "facebook": {"text", "image", "carousel", "video"},
           "threads": {"text", "image", "carousel", "video"}, "substack": {"article"}}
HOSTS = {"youtube": {"youtube.com", "www.youtube.com", "youtu.be"},
         "instagram": {"instagram.com", "www.instagram.com"},
         "facebook": {"facebook.com", "www.facebook.com"},
         "threads": {"threads.net", "www.threads.net", "threads.com", "www.threads.com"}}
INTERFACES = {"official_api", "official_connector", "reliable_cli", "controlled_browser", "computer_use", "manual"}
FINAL = {"published", "scheduled"}
ITEM_KEYS = {"id", "platform", "target_label", "target_id", "target_url", "interface",
             "format", "title", "body", "assets", "action", "scheduled_at", "settings", "review_ref", "unresolved"}


def require(condition, reason):
    """只回報固定原因，不回顯私人內容或解析器輸入。"""
    if not condition:
        raise ValueError(reason)


def exact(value, keys):
    """拒絕漏欄及把秘密藏進未知欄位。"""
    require(isinstance(value, dict) and set(value) == keys, "fields_invalid")


def short(value, maximum=300):
    """驗證非空短文字；不將欄位當成指令。"""
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= maximum
            and all(ord(c) >= 32 for c in value), "text_invalid")


def timestamp(value):
    """所有時間都要有時區，不能拿本機時間猜平台時間。"""
    require(isinstance(value, str), "time_missing")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "timezone_missing")
    return parsed


def now():
    """產生交易觀測用 UTC 時間。"""
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    """綁定所有欄位與陣列順序。"""
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def secrets(value):
    """攔截常見秘密鍵與值；不是完整的資料外洩偵測器。"""
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub("[^a-z]", "", key.lower())
            require(not any(s in normalized for s in ("token", "secret", "password", "cookie", "authorization", "apikey")), "secret_key")
            secrets(child)
    elif isinstance(value, list):
        for child in value:
            secrets(child)
    elif isinstance(value, str):
        require(not re.search(r"Bearer\s+\S+|-----BEGIN .*PRIVATE KEY|[?&](?:access_token|token|code|signature|sig|key|auth)=", value, re.I), "secret_value")


def workspace_path(raw):
    """要求已存在的明確工作區，禁止在技能包或掃描入口內產生使用者資料。"""
    supplied = Path(raw).absolute()
    require(supplied.is_dir() and supplied != Path(supplied.anchor), "workspace_invalid")
    for current in (supplied, *supplied.parents):
        require(not current.is_symlink(), "symlink")
        require(not (current / "install.manifest.toml").exists(), "package_is_not_workspace")
    require(not any(supplied.parts[i] == "skills" and supplied.parts[i - 1] in (".agents", ".claude", ".codex", ".gemini")
                    for i in range(1, len(supplied.parts))), "skill_root_is_not_workspace")
    return supplied


def local(root, relative, *, must_exist=True):
    """拒絕絕對路徑、跳出工作區與任一層 symlink。"""
    require(isinstance(relative, str) and relative and "\\" not in relative and ":" not in relative
            and not relative.startswith(("~", "/")), "path_invalid")
    parsed = PurePosixPath(relative)
    require(".." not in parsed.parts and parsed != PurePosixPath("."), "path_invalid")
    current = root
    for part in parsed.parts:
        current = current / part
        require(not current.is_symlink(), "symlink")
    if must_exist:
        require(current.is_file(), "file_missing")
    return current


def read(path):
    """讀取小型 JSON；不讀原始網路回應或秘密。"""
    require(path.stat().st_size <= 4_000_000, "json_too_large")
    result = json.loads(path.read_text(encoding="utf-8"))
    secrets(result)
    return result


def file_hash(path):
    """以固定記憶體量驗證大型媒體。"""
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def url_host(value):
    """只接受不含認證的 HTTPS；不跟隨或抓取 URL。"""
    short(value, 2000)
    parsed = urlsplit(value)
    require(parsed.scheme == "https" and parsed.hostname and not parsed.username
            and not parsed.password and parsed.port in (None, 443) and not parsed.fragment, "url_invalid")
    secrets(value)
    return parsed.hostname


def preview(root, relative):
    """檢查所有素材並回傳完整的唯讀預覽。"""
    plan = read(local(root, relative))
    exact(plan, {"schema_version", "job_id", "items"})
    require(type(plan["schema_version"]) is int and plan["schema_version"] == 1, "schema_invalid")
    require(isinstance(plan["job_id"], str) and re.fullmatch("[a-z0-9][a-z0-9-]{0,79}", plan["job_id"]), "job_invalid")
    require(relative == f'social-media/publishing/{plan["job_id"]}/plan.json', "plan_location_invalid")
    require(isinstance(plan["items"], list) and 1 <= len(plan["items"]) <= 20, "items_invalid")
    ids = set()
    for item in plan["items"]:
        exact(item, ITEM_KEYS)
        for key in ("id", "target_label", "target_id", "review_ref"):
            short(item[key])
        require(item["id"] not in ids, "duplicate_item")
        ids.add(item["id"])
        platform = item["platform"]
        require(platform in FORMATS and item["format"] in FORMATS[platform], "format_unsupported")
        require(item["interface"] in INTERFACES, "interface_invalid")
        host = url_host(item["target_url"])
        if platform in HOSTS:
            require(host in HOSTS[platform], "target_host_invalid")
        require(isinstance(item["title"], str) and isinstance(item["body"], str)
                and bool((item["title"] + item["body"]).strip()), "copy_missing")
        require(item["unresolved"] == [], "unresolved")
        require(isinstance(item["settings"], dict) and bool(item["settings"]), "settings_missing")
        require(item["action"] in ("publish_now", "native_schedule"), "action_invalid")
        if item["action"] == "native_schedule":
            require(platform in ("youtube", "facebook", "substack"), "schedule_unsupported")
            timestamp(item["scheduled_at"])
        else:
            require(item["scheduled_at"] is None, "unexpected_schedule")
        require(isinstance(item["assets"], list), "assets_invalid")
        if item["format"] in ("image", "carousel", "video", "reel"):
            require(len(item["assets"]) >= (2 if item["format"] == "carousel" else 1), "media_missing")
        for asset in item["assets"]:
            exact(asset, {"path", "sha256", "alt_text"})
            require(isinstance(asset["alt_text"], str), "alt_text_invalid")
            path = local(root, asset["path"])
            require(path.stat().st_size > 0 and file_hash(path) == asset["sha256"], "asset_changed")
    return {"plan": plan, "preview_sha256": digest({"workspace": str(root), "plan": plan}), "external_actions": False}


def fingerprint(item):
    """忽略 job 名稱、介面與排程，攔截改名重送相同內容。"""
    return digest({k: item[k] for k in ("platform", "target_id", "format", "title", "body")}
                  | {"media": [a["sha256"] for a in item["assets"]]})


@contextmanager
def locked(root):
    """本機單工作區互斥；中斷留下鎖時不自動清除或重送。"""
    base = local(root, "social-media/publishing", must_exist=False)
    require(base.is_dir(), "publishing_directory_missing")
    lock = local(root, "social-media/publishing/.transaction.lock", must_exist=False)
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, b"publishing-transaction\n")
        os.fsync(descriptor)
        yield
    finally:
        os.close(descriptor)
        lock.unlink()


def save(path, value):
    """原子儲存私有狀態；不覆蓋來源文案或媒體。"""
    descriptor, temporary = tempfile.mkstemp(prefix=".ledger-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def attempt_context(root, relative, item_id, *, require_executable=False,
                    allow_token_refresh=True):
    """從已落地帳本產生最小執行內容，不接受呼叫者自造授權狀態。"""
    require(type(allow_token_refresh) is bool, "refresh_policy_invalid")
    with locked(root):
        view = preview(root, relative)
        plan = view["plan"]
        matches = [item for item in plan["items"] if item["id"] == item_id]
        require(len(matches) == 1, "item_missing")
        state_path = local(
            root, f'social-media/publishing/{plan["job_id"]}/ledger.json',
            must_exist=False,
        )
        require(state_path.exists(), "begin_required")
        ledger = read(state_path)
        require(ledger.get("preview_sha256") == view["preview_sha256"], "preview_changed")
        attempt = ledger.get("items", {}).get(item_id)
        require(isinstance(attempt, dict), "begin_required")
        if require_executable:
            require(attempt.get("state") == "in_progress", "execution_not_allowed")
        else:
            require(attempt.get("state") not in FINAL, "already_verified")
        require(isinstance(attempt.get("operations", []), list), "ledger_invalid")
        grant = {
            "item_id": item_id,
            "preview_sha256": view["preview_sha256"],
            "approval_ref": attempt.get("approval_ref"),
            "platform": matches[0]["platform"],
            "target_id": matches[0]["target_id"],
            "transaction_status": attempt.get("state"),
            "allow_token_refresh": allow_token_refresh,
        }
        return {
            "item": matches[0],
            "attempt": json.loads(json.dumps(attempt)),
            "grant": grant,
            "job_id": plan["job_id"],
            "preview_sha256": view["preview_sha256"],
        }


def transaction(root, relative, command, *, item_id, expected=None, approval_ref=None,
                confirmed=False, stage=None, remote_id=None, checkpoint_outcome=None,
                receipt_path=None):
    """先落地執行意圖，再由 Agent 做外部動作；未知只准讀回補證據。"""
    with locked(root):
        view = preview(root, relative)
        plan = view["plan"]
        matches = [i for i in plan["items"] if i["id"] == item_id]
        require(len(matches) == 1, "item_missing")
        item = matches[0]
        state_path = local(root, f'social-media/publishing/{plan["job_id"]}/ledger.json', must_exist=False)
        ledger = read(state_path) if state_path.exists() else {
            "schema_version": 1, "preview_sha256": view["preview_sha256"], "items": {}}
        require(ledger["preview_sha256"] == view["preview_sha256"], "preview_changed")
        if command == "begin":
            require(confirmed is True and expected == view["preview_sha256"], "publish_confirmation_required")
            short(approval_ref)
            secrets(approval_ref)
            if item["action"] == "native_schedule":
                require(timestamp(item["scheduled_at"]) > datetime.now(timezone.utc), "schedule_in_past")
            require(item_id not in ledger["items"], "already_attempted_do_not_resend")
            for prior in plan["items"][:plan["items"].index(item)]:
                require(ledger["items"].get(prior["id"], {}).get("state") in FINAL, "previous_item_unverified")
            # 掃描持久紀錄，而非只靠同次執行的記憶體去重。
            base = root / "social-media/publishing"
            for folder in base.iterdir():
                require(not folder.is_symlink(), "symlink")
                if folder.is_dir():
                    other_path = local(root, str((folder / "ledger.json").relative_to(root)), must_exist=False)
                    if other_path.exists():
                        for attempt in read(other_path)["items"].values():
                            require(attempt["fingerprint"] != fingerprint(item), "duplicate_attempt")
            ledger["items"][item_id] = {
                "state": "awaiting_manual" if item["interface"] == "manual" else "in_progress",
                "fingerprint": fingerprint(item), "approval_ref": approval_ref,
                "begun_at": now(), "operations": [], "checkpoints": [], "receipts": [],
            }
        else:
            require(item_id in ledger["items"], "begin_required")
            attempt = ledger["items"][item_id]
            require(attempt["state"] not in FINAL, "already_verified")
            if command == "claim":
                require(attempt["state"] == "in_progress", "readback_only")
                require(isinstance(stage, str) and re.fullmatch("[a-z][a-z0-9-]{0,79}", stage), "stage_invalid")
                operations = attempt.setdefault("operations", [])
                require(not any(operation.get("stage") == stage for operation in operations),
                        "stage_already_claimed_do_not_resend")
                operations.append({"stage": stage, "state": "claimed", "claimed_at": now(),
                                   "completed_at": None, "remote_id": None,
                                   "outcome": None})
            elif command == "checkpoint":
                require(attempt["state"] == "in_progress", "readback_only")
                require(isinstance(stage, str) and re.fullmatch("[a-z][a-z0-9-]{0,79}", stage), "stage_invalid")
                require(checkpoint_outcome in {"remote-id-saved", "sensitive-reference-memory-only",
                                               "pending-without-remote-id"},
                        "checkpoint_outcome_invalid")
                if checkpoint_outcome == "remote-id-saved":
                    require(isinstance(remote_id, str) and re.fullmatch("[A-Za-z0-9_-]{1,200}", remote_id), "remote_id_invalid")
                else:
                    require(remote_id is None, "remote_id_must_be_omitted")
                operations = attempt.setdefault("operations", [])
                matches = [operation for operation in operations if operation.get("stage") == stage]
                require(len(matches) == 1 and matches[0].get("state") == "claimed",
                        "stage_claim_required")
                secrets({"stage": stage, "remote_id": remote_id})
                completed_at = now()
                matches[0].update(state="completed", completed_at=completed_at,
                                  remote_id=remote_id, outcome=checkpoint_outcome)
                attempt["checkpoints"].append({"stage": stage, "remote_id": remote_id,
                                               "outcome": checkpoint_outcome,
                                               "at": completed_at})
            elif command == "record":
                receipt = read(local(root, receipt_path))
                validate_receipt(root, item, receipt)
                require(timestamp(receipt["observed_at"]) >= timestamp(attempt["begun_at"]), "readback_predates_attempt")
                attempt["state"] = receipt["state"]
                attempt["receipts"].append(receipt)
            else:
                raise ValueError("command_invalid")
        save(state_path, ledger)
        return {"result": ledger["items"][item_id]["state"], "item_id": item_id,
                "external_actions": False, "manual_only": item["interface"] == "manual",
                "ledger": str(state_path.relative_to(root))}


def validate_receipt(root, item, receipt):
    """驗證 Agent 已讀回的正規化資料，不能單靠此宣稱真實平台成功。"""
    exact(receipt, {"item_id", "target_id", "state", "platform_id", "url", "platform_time",
                    "observed_at", "content_matches", "media_matches", "settings_readback",
                    "evidence_path", "evidence_sha256"})
    require(receipt["item_id"] == item["id"] and receipt["target_id"] == item["target_id"], "readback_target_mismatch")
    require(receipt["state"] in FINAL | {"pending", "unknown", "failed"}, "state_invalid")
    observed = timestamp(receipt["observed_at"])
    require(observed <= datetime.now(timezone.utc), "observation_in_future")
    require(type(receipt["content_matches"]) is bool and type(receipt["media_matches"]) is bool, "comparison_invalid")
    evidence = local(root, receipt["evidence_path"])
    require(evidence.stat().st_size > 0 and file_hash(evidence) == receipt["evidence_sha256"], "evidence_changed")
    if receipt["url"] is not None:
        host = url_host(receipt["url"])
        allowed = HOSTS.get(item["platform"], {url_host(item["target_url"])})
        require(host in allowed, "readback_host_mismatch")
    if receipt["state"] in FINAL:
        expected_state = "scheduled" if item["action"] == "native_schedule" else "published"
        require(receipt["state"] == expected_state, "unexpected_platform_state")
        short(receipt["platform_id"], 200)
        require(receipt["url"] is not None and receipt["content_matches"] and receipt["media_matches"], "readback_incomplete")
        require(receipt["settings_readback"] == item["settings"], "settings_mismatch")
        platform_time = timestamp(receipt["platform_time"])
        if receipt["state"] == "published":
            require(platform_time <= observed, "publication_in_future")
        else:
            require(platform_time == timestamp(item["scheduled_at"]) and platform_time > observed, "schedule_mismatch")


def main():
    """錯誤只輸出固定標記，不印私人輸入、秘密或例外原文。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preview", "begin", "claim", "checkpoint", "record"))
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--item")
    parser.add_argument("--preview-sha256")
    parser.add_argument("--approval-ref")
    parser.add_argument("--confirm-publish", action="store_true")
    parser.add_argument("--stage")
    parser.add_argument("--remote-id")
    parser.add_argument("--checkpoint-outcome", choices=("remote-id-saved",
                                                         "sensitive-reference-memory-only",
                                                         "pending-without-remote-id"))
    parser.add_argument("--receipt")
    args = parser.parse_args()
    try:
        root = workspace_path(args.workspace)
        if args.command == "preview":
            result = preview(root, args.plan)
        else:
            result = transaction(root, args.plan, args.command, item_id=args.item,
                                 expected=args.preview_sha256, approval_ref=args.approval_ref,
                                 confirmed=args.confirm_publish, stage=args.stage,
                                 remote_id=args.remote_id,
                                 checkpoint_outcome=args.checkpoint_outcome,
                                 receipt_path=args.receipt)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        print(json.dumps({"result": "blocked", "external_actions": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
