#!/usr/bin/env python3
"""驗證成效指標目錄；不連網、不讀私人帳號或憑證。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


CATALOG_PATH = Path(__file__).resolve().parent.parent / "references" / "metric-catalog.json"


class MetricCatalogError(ValueError):
    """代表計畫與已查證的最小指標契約不符。"""


def load_catalog():
    """嚴格讀取隨技能安裝的公開指標目錄。"""

    try:
        value = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise MetricCatalogError("catalog_unavailable") from None
    if (not isinstance(value, dict) or value.get("schema_version") != 1
            or value.get("kind") != "social_performance_metric_catalog"
            or set(value.get("platforms", {})) != {
                "youtube", "facebook", "instagram", "threads", "substack"}):
        raise MetricCatalogError("catalog_invalid")
    return value


def _platform(name):
    """取得單一平台規則。"""

    value = load_catalog()["platforms"].get(name)
    if not isinstance(value, dict):
        raise MetricCatalogError("platform_invalid")
    return value


def _identity(item, contract):
    """核對不允許 Agent 自行猜測的單位與聚合口徑。"""

    for field in ("unit", "aggregation", "basis"):
        if item.get(field) != contract.get(field):
            raise MetricCatalogError("metric_identity_mismatch")
    expected = contract.get("definition")
    if expected is not None and item.get("definition") != expected:
        raise MetricCatalogError("metric_definition_mismatch")


def validate_official_series(platform, item, timezone):
    """在任何 API 呼叫前核對 collection plan 的指標口徑。"""

    rule = _platform(platform)
    query = item.get("query")
    if not isinstance(query, dict) or query.get("metric") != item.get("metric"):
        raise MetricCatalogError("metric_query_mismatch")
    mode = rule.get("validation_mode")
    if platform == "youtube":
        contract = rule.get("metrics", {}).get(item.get("metric"))
        if not isinstance(contract, dict):
            raise MetricCatalogError("metric_not_allowlisted")
        _identity(item, contract)
        if (timezone != rule.get("source_timezone")
                or query.get("coverage_probe") is not True
                or query.get("filters", "") != ""):
            raise MetricCatalogError("youtube_query_contract")
    elif platform in {"facebook", "instagram"}:
        if item.get("definition") != rule.get("required_definition"):
            raise MetricCatalogError("runtime_definition_required")
        if query.get("api_period") not in rule.get("allowed_periods", []):
            raise MetricCatalogError("period_not_allowlisted")
        if platform == "facebook" and query.get(
                "show_description_from_api_doc") is not True:
            raise MetricCatalogError("api_description_probe_required")
        if platform == "instagram" and query.get("metric_type") not in rule.get(
                "allowed_metric_types", []):
            raise MetricCatalogError("metric_type_not_allowlisted")
    elif platform == "threads":
        contract = rule.get("metrics", {}).get(item.get("metric"))
        if not isinstance(contract, dict):
            raise MetricCatalogError("metric_not_allowlisted")
        _identity(item, contract)
    else:
        raise MetricCatalogError("official_api_not_supported")
    if mode not in {"static_allowlist", "runtime_official_description",
                    "official_example_allowlist"}:
        raise MetricCatalogError("validation_mode_invalid")


def validate_adapter_query(platform, query, aggregation):
    """保護直接呼叫 adapter 的程式，避免繞過 collection plan。"""

    rule = _platform(platform)
    metric = query.get("metric")
    if platform == "youtube":
        contract = rule.get("metrics", {}).get(metric)
        if (not isinstance(contract, dict)
                or aggregation != contract.get("aggregation")
                or query.get("coverage_probe") is not True
                or query.get("filters", "") != ""):
            raise MetricCatalogError("metric_not_allowlisted")
    elif platform == "facebook":
        if (query.get("api_period") not in rule.get("allowed_periods", [])
                or query.get("show_description_from_api_doc") is not True):
            raise MetricCatalogError("runtime_probe_required")
    elif platform == "instagram":
        if (query.get("api_period") not in rule.get("allowed_periods", [])
                or query.get("metric_type") not in rule.get("allowed_metric_types", [])):
            raise MetricCatalogError("runtime_probe_invalid")
    elif platform == "threads":
        contract = rule.get("metrics", {}).get(metric)
        if not isinstance(contract, dict) or aggregation != contract.get("aggregation"):
            raise MetricCatalogError("metric_not_allowlisted")
    else:
        raise MetricCatalogError("official_api_not_supported")


def validate_imported_series(platform, item):
    """限制 Substack 匯入為可比較的語意指標，不接收任意手填名稱。"""

    if platform != "substack":
        return
    rule = _platform(platform)
    contract = rule.get("metrics", {}).get(item.get("metric"))
    if not isinstance(contract, dict):
        raise MetricCatalogError("metric_not_allowlisted")
    _identity(item, contract)


def validate_import_eligibility(platform, interface, eligibility):
    """確認來源當次已具備官方介面所要求的讀取資格。"""

    if platform != "substack":
        return
    expected = _platform(platform).get(
        "allowed_eligibility_by_interface", {}).get(interface)
    if expected is None or eligibility != expected:
        raise MetricCatalogError("source_ineligible")


def observed_definition(platform, base_definition, observation):
    """把 Meta 當次正式欄位說明綁進定義，讓跨期變更自動不可比較。"""

    if observation.get("status") != "available" or platform == "youtube":
        return base_definition
    if platform not in {"facebook", "instagram", "threads"}:
        return base_definition
    description = observation.get("response_definition")
    period = observation.get("response_period")
    if (not isinstance(description, str) or not description.strip()
            or not isinstance(period, str) or not period):
        raise MetricCatalogError("response_definition_missing")
    payload = (period + "\n" + description.strip()).encode("utf-8")
    suffix = hashlib.sha256(payload).hexdigest()[:16]
    return base_definition + ":observed-" + suffix
