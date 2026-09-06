#!/usr/bin/env python3
"""唯讀檢查研究紀錄與方向關卡，不搜尋、不批准、不保存或發布。"""

import argparse
import json
import math
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DESTINATIONS = {"youtube", "instagram", "facebook", "threads", "substack"}
RESEARCH_PLATFORMS = DESTINATIONS | {"x"}


class InvalidRecord(ValueError):
    """固定錯誤代稱，不洩漏研究內容或私人路徑。"""


def require(condition, code):
    """以固定代稱指出未滿足的契約。"""
    if not condition:
        raise InvalidRecord(code)


def text_fields(value, names):
    """只驗證必要文字，不以文字推測人類意圖。"""
    require(isinstance(value, dict), "object_required")
    require(all(isinstance(value.get(k), str) and value[k].strip() for k in names), "missing_text")


def day(value):
    """日期必須明確，不能以未知或搜尋索引時間冒充。"""
    try:
        require(isinstance(value, str), "invalid_date")
        return date.fromisoformat(value)
    except ValueError:
        raise InvalidRecord("invalid_date") from None


def moment(value):
    """確認關卡使用有時區的 ISO 時間。"""
    try:
        result = datetime.fromisoformat(value)
        require(result.tzinfo is not None, "timezone_required")
        return result
    except (TypeError, ValueError):
        raise InvalidRecord("invalid_time") from None


def source_url(value):
    """拒絕秘密 URL 並去除常見追蹤參數；僅用於重複檢查，不連線。"""
    require(isinstance(value, str), "invalid_url")
    uri = urlsplit(value)
    require(uri.scheme == "https" and uri.hostname and not uri.username and not uri.password, "invalid_url")
    pairs = parse_qsl(uri.query)
    require(not any(any(s in k.lower() for s in ("token", "secret", "password", "cookie", "api_key")) for k, _ in pairs), "secret_url")
    clean = [(k, v) for k, v in pairs if not k.lower().startswith("utm_") and k not in {"fbclid", "si"}]
    return urlunsplit((uri.scheme, uri.netloc.lower(), uri.path.rstrip("/"), urlencode(sorted(clean)), ""))


def validate(record, *, complete=False):
    """只驗證提供的紀錄，不能證明網頁真實或確認來自人類。"""
    text_fields(record, ("topic", "goal", "audience", "phase"))
    require(record.get("schema_version") == 1, "schema_version")
    phase = record["phase"]
    require(phase in {"awaiting_direction", "planning", "deferred", "abandoned"}, "invalid_phase")
    research = record.get("research")
    text_fields(research, ("version", "as_of", "window_start", "window_end"))
    as_of = day(research["as_of"])
    require(day(research["window_start"]) <= day(research["window_end"]) <= as_of, "invalid_window")
    platforms = research.get("platforms")
    require(isinstance(platforms, list) and platforms and all(isinstance(p, str) and p in RESEARCH_PLATFORMS for p in platforms), "invalid_platforms")
    require(len(platforms) == len(set(platforms)), "duplicate_platforms")
    coverage = research.get("coverage")
    require(isinstance(coverage, list), "coverage_required")
    for item in coverage:
        text_fields(item, ("platform", "method", "status", "note"))
        require(item["status"] in {"checked", "limited", "blocked", "not_run"}, "invalid_coverage")
        require(item["method"] in {"public_search", "official_api", "authorized_browser", "user_source", "none"}, "invalid_method")
        queries = item.get("queries")
        require(isinstance(queries, list) and all(isinstance(q, str) and q.strip() for q in queries), "invalid_queries")
        if item["status"] in {"checked", "limited"}:
            require(queries and item["method"] != "none", "missing_search_evidence")
    require(len(coverage) == len(platforms) and {c["platform"] for c in coverage} == set(platforms), "missing_coverage")
    require(isinstance(research.get("limitations"), list) and all(isinstance(s, str) for s in research["limitations"]), "limitations_required")
    cases = research.get("cases")
    require(isinstance(cases, list), "cases_required")
    ids, urls, usable, warnings = set(), set(), set(), []
    for item in cases:
        text_fields(item, ("id", "platform", "url", "author", "observed_at", "read_scope", "safety"))
        require(item["platform"] in platforms, "case_outside_scope")
        require(item["id"] not in ids, "duplicate_case")
        canonical = source_url(item["url"])
        require(canonical not in urls, "duplicate_source")
        ids.add(item["id"])
        urls.add(canonical)
        require(day(item["observed_at"]) <= as_of, "future_observation")
        if item.get("published_at") is not None:
            require(day(item["published_at"]) <= day(item["observed_at"]), "future_publication")
            if not day(research["window_start"]) <= day(item["published_at"]) <= day(research["window_end"]):
                warnings.append("outside_window")
        else:
            warnings.append("publication_date_unknown")
        require(item["read_scope"] in {"primary", "partial", "snippet_only", "unavailable"}, "invalid_read_scope")
        require(item["safety"] in {"usable", "excluded"}, "invalid_safety")
        if item["safety"] == "excluded":
            require(not item.get("summary"), "excluded_text_not_allowed")
        elif item["read_scope"] in {"primary", "partial"}:
            text_fields(item, ("summary", "angle", "format"))
            usable.add(item["id"])
        else:
            warnings.append("unverified_primary")
        require(isinstance(item.get("metrics"), list), "metrics_required")
        for metric in item["metrics"]:
            text_fields(metric, ("name", "status", "observed_at"))
            require(day(metric["observed_at"]) <= as_of, "future_metric")
            require(metric["status"] in {"observed", "unavailable", "permission_denied", "read_failed"}, "metric_status")
            value = metric.get("value")
            if metric["status"] == "observed":
                require((type(value) in {int, float} and math.isfinite(value) and value >= 0)
                        or (isinstance(value, str) and bool(value.strip())), "observed_value_required")
            else:
                require(value is None, "missing_is_not_zero")
    if len(usable) < 3:
        warnings.append("limited_cases")
    if any(c["status"] != "checked" for c in coverage):
        warnings.append("limited_coverage")
    decision = record.get("decision")
    calendar, briefs = record.get("calendar"), record.get("briefs")
    require(isinstance(calendar, list) and isinstance(briefs, list), "outputs_required")
    if phase == "awaiting_direction":
        require(decision is None and not calendar and not briefs, "direction_gate_not_passed")
    else:
        text_fields(decision, ("research_version", "choice", "direction", "user_response", "confirmed_at", "evidence_ref"))
        require(decision["research_version"] == research["version"], "stale_decision")
        require(moment(decision["confirmed_at"]) >= moment(research.get("presented_at")), "decision_before_briefing")
        require(decision["choice"] == {"planning": "proceed", "deferred": "defer", "abandoned": "abandon"}[phase], "decision_phase_mismatch")
        if phase != "planning":
            require(not calendar and not briefs, "stopped_plan_has_outputs")
    for item in calendar:
        text_fields(item, ("topic", "platform", "slot", "timezone"))
        require(item["platform"] in DESTINATIONS and item.get("status") == "draft", "calendar_not_draft")
    for item in briefs:
        text_fields(item, ("topic", "platform", "role", "angle", "audience", "cta_goal", "media", "handoff"))
        require(item["platform"] in DESTINATIONS, "research_only_destination")
        require(item["handoff"] in {"social-content-writing", "social-image-production", "existing-ai-video"}, "invalid_handoff")
        refs = item.get("source_case_ids")
        require(isinstance(refs, list) and all(isinstance(r, str) and r in usable for r in refs), "unusable_handoff_source")
        require(isinstance(item.get("fact_sources"), list) and isinstance(item.get("unverified_claims"), list), "fact_check_fields_required")
        for url in item["fact_sources"]:
            source_url(url)
    if complete:
        require(phase == "planning" and calendar and briefs, "planning_incomplete")
    return {"valid": True, "phase": phase, "usable_cases": len(usable), "warnings": sorted(set(warnings)),
            "human_approval_verified": False, "network_accessed": False}


def main():
    """只回固定檢查結果，出錯時不輸出私人內容。"""
    parser = argparse.ArgumentParser(description="唯讀檢查社群研究與方向關卡")
    parser.add_argument("record")
    parser.add_argument("--complete", action="store_true")
    args = parser.parse_args()
    try:
        path = Path(args.record)
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 1024 * 1024, "invalid_record_file")
        result = validate(json.loads(path.read_text(encoding="utf-8")), complete=args.complete)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except InvalidRecord as error:
        print(json.dumps({"valid": False, "error": str(error)}))
    except Exception:
        print(json.dumps({"valid": False, "error": "invalid_record"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
