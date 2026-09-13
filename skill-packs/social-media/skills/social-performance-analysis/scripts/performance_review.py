#!/usr/bin/env python3
"""成效分析的離線檢查與確認寫回；不連線、不載入憑證、不產生策略判斷。"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


MODES = ("weekly", "monthly", "quarterly", "yearly")
PLATFORMS = {"youtube", "instagram", "facebook", "threads", "substack"}
STATUSES = {"available", "unavailable", "permission_denied", "read_failed", "definition_changed"}
IDENTITY = ("metric", "definition", "unit", "aggregation", "scope", "segment", "basis", "timezone")
STRATEGY = "sources/strategy/social-media-strategy-and-insights.md"
DATA_ROOT = "social-media/performance"


class TimezoneDataMissing(ValueError):
    """執行環境缺 IANA 資料，不能把它誤報成使用者時區錯誤。"""


def load_timezone(key):
    """先確認資料庫可讀，絕不以 UTC 代替指定時區。"""
    try:
        ZoneInfo("UTC")
    except ZoneInfoNotFoundError:
        raise TimezoneDataMissing("timezone_data_missing: install pinned tzdata requirements") from None
    return ZoneInfo(key)


def require(condition, message):
    """用可預期錯誤停止，不忽略不完整輸入。"""
    if not condition:
        raise ValueError(message)


def text(value, limit=1200):
    """限制可寫入摘要，不接受 HTML 標記或多行結構覆寫。"""
    require(isinstance(value, str) and 0 < len(value.strip()) <= limit, "文字缺漏或過長")
    require(not any(ord(c) < 32 for c in value) and "<" not in value and ">" not in value,
            "文字不可含控制字元、換行或 HTML")
    return value.strip()


def digest(data):
    """計算本機內容完整性，不代表來源真實性或人工同意。"""
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()


def period(start, end):
    require(date.fromisoformat(start) < date.fromisoformat(end), "期間必須起日早於不含尾日")
    return {"start": start, "end": end}


def periods(mode, as_of):
    """以來源時區的當地日期產生最近完整曆期，不包含尚未結束期間。"""
    require(mode in MODES, "未知檢視週期")
    today = date.fromisoformat(as_of)
    if mode == "weekly":
        end = today - timedelta(days=today.weekday())
        start = end - timedelta(days=7)
        previous = start - timedelta(days=7)
    else:
        width = {"monthly": 1, "quarterly": 3, "yearly": 12}[mode]
        month = ((today.month - 1) // width) * width + 1
        end = date(today.year, month, 1)

        def back(d):
            index = d.year * 12 + d.month - 1 - width
            return date(index // 12, index % 12 + 1, 1)

        start, previous = back(end), back(back(end))
    return {"period": period(start.isoformat(), end.isoformat()),
            "comparison_period": period(previous.isoformat(), start.isoformat())}


def workspace(value):
    """拒絕技能來源、公開 Toolbox、寬泛目錄與 symlink 目標。"""
    path = Path(value).absolute()
    require(path.is_dir() and path != Path.home() and path != Path(path.anchor), "需明確私人工作區")
    require(path.resolve() == path, "請使用實體工作區路徑")
    require(not any(name in path.parts for name in (".agents", ".claude", ".codex", ".gemini")),
            "不得在 Agent 設定或技能掃描目錄存私人報告")
    for parent in (path, *path.parents):
        require(not (parent / "skill-packs").exists(), "不得寫入公開 Toolbox")
        require(not (parent / "install.manifest.toml").exists(), "不得寫入獨立技能包來源")
        require(not (parent / "SKILL.md").exists(), "不得使用技能目錄作為工作區")
    return path


def safe_path(root, relative):
    """僅接受工作區相對路徑，拒絕連結與目錄穿越。"""
    text(str(relative), 1024)
    part = Path(relative)
    require(not part.is_absolute() and bool(part.parts) and ".." not in part.parts, "路徑必須位於私人工作區")
    result = root / part
    require(result.resolve().is_relative_to(root), "路徑逸出工作區")
    for node in (result, *result.parents):
        if node == root:
            break
        require(not node.is_symlink(), "不接受 symlink")
    return result


def load(root, relative):
    path = safe_path(root, relative)
    require(path.is_file() and path.stat().st_size <= 5_000_000, "資料檔缺漏或過大")
    raw = path.read_bytes()
    return json.loads(raw), digest(raw)


def timestamp(value):
    parsed = datetime.fromisoformat(value)
    require(parsed.tzinfo is not None, "讀取時間需含時區")
    return parsed


def analyze(root, data):
    """只在同一序列的完整、同定義資料間計算，不做跨平台排名或加總。"""
    require(data.get("schema_version") == 1 and data.get("mode") in MODES, "資料版本或週期錯誤")
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", data.get("report_id", "")), "報告 ID 格式錯誤")
    load_timezone(data["timezone"])
    for field in ("period", "comparison_period"):
        period(**data[field])
    require(data["comparison_period"]["end"] == data["period"]["start"], "MVP 只比較相鄰曆期")
    require(periods(data["mode"], data["period"]["end"]) == {
        k: data[k] for k in ("period", "comparison_period")}, "期間不是完整曆期")
    require(isinstance(data.get("series"), list) and 0 < len(data["series"]) <= 200, "需 1–200 個指標序列")
    results, seen = [], set()
    for series in data["series"]:
        key = text(series["key"], 100)
        require(key not in seen and series["platform"] in PLATFORMS, "序列重複或平台不符")
        seen.add(key)
        text(series["account_ref"])
        text(series["role"])
        for name, window in (("current", "period"), ("previous", "comparison_period")):
            point = series[name]
            require(point["status"] in STATUSES and point["coverage"] in {"complete", "partial", "unknown"}, "資料狀態不符")
            for identity in IDENTITY:
                text(point[identity])
            load_timezone(point["timezone"])
            require(point["timezone"] == data["timezone"], "不同來源時區需另建資料集，不能換標籤")
            require(point["period"] == data[window], "指標的實際期間不符")
            require(point["aggregation"] in {"total", "unique", "snapshot", "average", "rate"}, "聚合方式不符")
            require(point["basis"] in {"period_activity", "period_end_snapshot"}, "累積貼文或固定天齡請另列描述，不套曆期增減")
            require((point["aggregation"] == "snapshot") == (point["basis"] == "period_end_snapshot"), "快照不可假裝期間總量")
            observed = timestamp(point["observed_at"])
            require(observed.astimezone(load_timezone(point["timezone"])).date() >= date.fromisoformat(point["period"]["end"]),
                    "讀取時間早於期間結束")
            require(observed <= datetime.now(observed.tzinfo), "讀取時間不可在未來")
            value = point["value"]
            if point["status"] == "available":
                require(type(value) in (int, float) and math.isfinite(value), "有效資料必須為有限數值")
                if point["unit"] == "percent":
                    require(0 <= value <= 100, "百分率需使用 0–100")
            else:
                require(value is None, "缺資料不可填零或其他數值")
            evidence = safe_path(root, point["evidence_path"])
            require(evidence.is_relative_to(root / DATA_ROOT) and evidence.is_file(), "證據必須留在私人逐期資料目錄")
            require(digest(evidence.read_bytes()) == point["evidence_sha256"], "證據已變更，需重建報告")
        current, previous = series["current"], series["previous"]
        reasons = []
        for label, point in (("current", current), ("previous", previous)):
            if point["status"] != "available":
                reasons.append(label + ":" + point["status"])
            if point["coverage"] != "complete":
                reasons.append(label + ":coverage_" + point["coverage"])
        reasons += ["changed:" + name for name in IDENTITY if current[name] != previous[name]]
        result = {"key": key, "platform": series["platform"], "role": series["role"],
                  "comparable": not reasons, "reasons": reasons, "delta": None, "percent_change": None}
        if not reasons:
            result["delta"] = current["value"] - previous["value"]
            require(math.isfinite(result["delta"]), "差值超出可用數值範圍")
            result["delta_unit"] = "percentage_points" if current["unit"] == "percent" else current["unit"]
            if previous["value"] > 0:
                result["percent_change"] = result["delta"] / previous["value"] * 100
                require(math.isfinite(result["percent_change"]), "百分比超出可用數值範圍")
            else:
                result["baseline_note"] = "nonpositive_baseline_no_percent_change"
        days = [(date.fromisoformat(data[p]["end"]) - date.fromisoformat(data[p]["start"])).days
                for p in ("period", "comparison_period")]
        result["duration_note"] = "unequal_calendar_days_not_efficiency" if days[0] != days[1] else "equal_calendar_days"
        results.append(result)
    return results


def check_report(data, data_hash, report, writeback=False):
    """結構確認不取代 Agent 查核事實與真實對話確認。"""
    require(report.get("schema_version") == 1 and report.get("report_id") == data["report_id"]
            and report.get("dataset_sha256") == data_hash, "報告未綁定目前資料集")
    observations = report.get("observations", [])
    require(3 <= len(observations) <= 5, "需三至五項有證據的重要觀察；不足不得硬湊")
    keys, ids = {s["key"] for s in data["series"]}, set()
    for item in observations:
        identifier = text(item["id"], 100)
        require(identifier not in ids, "觀察 ID 重複")
        ids.add(identifier)
        require(bool(item["series_keys"]) and set(item["series_keys"]) <= keys, "觀察需連結存在的序列")
        for field in ("fact", "inference", "limitations"):
            text(item[field])
    questions = report.get("questions", [])
    require(len(questions) == 1, "每次只討論一個最重要的策略問題")
    text(questions[0])
    if not writeback:
        return
    human = report.get("human")
    require(isinstance(human, dict), "尚缺使用者判斷")
    text(human["response"])
    text(human["conversation_ref"])
    answered = timestamp(human["received_at"])
    require(timestamp(report["asked_at"]) <= answered <= datetime.now(answered.tzinfo), "討論時間順序不符")
    insight = report["insight"]
    require(set(insight) == {"conclusion", "user_judgment", "scope", "confidence", "recheck_on", "observation_ids"}, "只允許精簡策略結論欄位")
    for field in ("conclusion", "user_judgment", "scope"):
        text(insight[field], 600)
    require(insight["confidence"] in {"low", "medium", "high"}, "需標示信心")
    require(date.fromisoformat(insight["recheck_on"]) > answered.date(), "下次檢視日期需晚於討論")
    require(bool(insight["observation_ids"]) and set(insight["observation_ids"]) <= ids, "結論缺少觀察依據")


def preview(root, dataset_path, report_path):
    """預覽只讀，綁定原策略、報告、資料與證據，不建立任何檔案。"""
    for relative in (dataset_path, report_path):
        require(safe_path(root, relative).is_relative_to(root / DATA_ROOT), "報告與資料集必須留在私人逐期目錄")
    data, data_hash = load(root, dataset_path)
    report, report_hash = load(root, report_path)
    analyze(root, data)
    check_report(data, data_hash, report, writeback=True)
    target = safe_path(root, STRATEGY)
    before = target.read_bytes() if target.exists() else b""
    marker = "<!-- social-performance-review:" + data["report_id"] + " -->"
    require(marker not in before.decode("utf-8"), "本期結論已寫入，不可重複")
    insight = report["insight"]
    addition = ("\n\n" + marker + "\n## 已確認成效洞察\n\n"
                + f"- 檢視期間：{data['mode']} {data['period']['start']} 至 {data['period']['end']}（不含尾日）；來源時區 {data['timezone']}\n"
                + f"- 結論：{insight['conclusion']}\n- 使用者判斷：{insight['user_judgment']}\n"
                + f"- 適用範圍與限制：{insight['scope']}\n- 信心：{insight['confidence']}\n"
                + f"- 再檢視日期：{insight['recheck_on']}\n"
                + f"- 證據：{report_path}；觀察 {', '.join(insight['observation_ids'])}\n")
    after = before + addition.encode()
    plan = {"report_id": data["report_id"], "target": STRATEGY,
            "before_sha256": digest(before), "after_sha256": digest(after),
            "dataset_sha256": data_hash, "report_sha256": report_hash,
            "workspace": str(root), "append_text": addition,
            "creates_file": not target.exists()}
    plan["preview_sha256"] = digest(canonical(plan))
    return plan, before, after


def write_new(path, payload):
    """新紀錄不可覆蓋，POSIX 權限僅目前使用者；Windows ACL 另需實機驗證。"""
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


@contextmanager
def locked(root):
    folder = safe_path(root, ".local/social-media/performance")
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = folder / "writeback.lock"
    write_new(path, b"locked\n")
    try:
        yield folder
    finally:
        path.unlink()


def apply(root, dataset_path, report_path, preview_hash, confirmed):
    """再次確認才寫入；保留原檔備份與交易證據，遇衝突不重試。"""
    require(confirmed, "需要本次預覽後的明確寫入確認")
    with locked(root) as state:
        # 未完成的交易一律停止，由人比對 journal、備份與目標後再決定。
        for journal in state.glob("*.transaction.json"):
            require(journal.with_suffix(".receipt.json").exists(), "既有交易結果不明，先人工檢查")
        plan, before, after = preview(root, dataset_path, report_path)
        require(plan["preview_sha256"] == preview_hash, "預覽已過期或內容改變，請重新預覽確認")
        transaction = state / (plan["report_id"] + ".transaction.json")
        backup = state / (plan["report_id"] + ".before.md")
        target = safe_path(root, STRATEGY)
        target.parent.mkdir(parents=True, exist_ok=True)
        require((target.read_bytes() if target.exists() else b"") == before, "策略遭其他程序修改")
        write_new(backup, before)
        write_new(transaction, canonical(plan))
        fd, temp_name = tempfile.mkstemp(prefix=".performance-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(after)
                handle.flush()
                os.fsync(handle.fileno())
            require((target.read_bytes() if target.exists() else b"") == before, "策略遭其他程序修改")
            os.replace(temp_name, target)
            if os.name == "posix":
                directory_fd = os.open(target.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        require(target.read_bytes() == after, "寫入讀回不符，停止並保留交易")
        receipt = {"status": "verified_local", "report_id": plan["report_id"],
                   "preview_sha256": preview_hash, "strategy_sha256": digest(after),
                   "verified_at": datetime.now().astimezone().isoformat()}
        write_new(transaction.with_suffix(".receipt.json"), canonical(receipt))
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("periods", "analyze", "check-report", "preview", "apply"))
    parser.add_argument("--workspace")
    parser.add_argument("--dataset")
    parser.add_argument("--report")
    parser.add_argument("--mode", choices=MODES)
    parser.add_argument("--as-of")
    parser.add_argument("--preview-sha256")
    parser.add_argument("--confirm-write", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "periods":
            result = periods(args.mode, args.as_of)
        else:
            root = workspace(args.workspace)
            if args.action in ("preview", "apply"):
                result = (preview(root, args.dataset, args.report)[0] if args.action == "preview" else
                          apply(root, args.dataset, args.report, args.preview_sha256, args.confirm_write))
            else:
                data, sha = load(root, args.dataset)
                result = analyze(root, data)
                if args.action == "check-report":
                    report, _ = load(root, args.report)
                    check_report(data, sha, report)
                    result = {"status": "structure_valid_not_human_or_fact_verification"}
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, TypeError, KeyError, OSError, OverflowError) as error:
        # 不輸出檔案內容或完整 traceback；錯誤只供本機使用。
        print(json.dumps({"status": "stopped", "reason": str(error)}, ensure_ascii=False))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
