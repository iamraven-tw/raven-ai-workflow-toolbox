#!/usr/bin/env python3
"""把官方唯讀 API 或已保存來源證據轉成成效 dataset；不產生策略結論。"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import performance_review as review
import metric_catalog
from official_performance_api import (
    OfficialPerformanceAdapter,
    PerformanceAPIError,
)


PLATFORMS = {"youtube", "facebook", "instagram", "threads", "substack"}
IMPORT_INTERFACES = {
    "official_substack_mcp", "official_export", "controlled_browser",
}
PLAN_FIELDS = {
    "schema_version", "report_id", "mode", "timezone", "platform",
    "account_ref", "period", "comparison_period", "source_mode", "scope",
    "series",
}
SERIES_FIELDS = {
    "key", "role", "metric", "definition", "unit", "aggregation", "scope",
    "segment", "basis",
}
POINT_IDENTITY = (
    "metric", "definition", "unit", "aggregation", "scope", "segment",
    "basis", "timezone", "period",
)


class PerformanceCollectError(RuntimeError):
    """固定停止原因，不把平台回應或私人數字放進錯誤文字。"""


def _require(ok, reason):
    """用固定原因停止。"""

    if not ok:
        raise PerformanceCollectError(reason)


def _identifier(value):
    """限制 report／series ID，避免路徑逸出。"""

    _require(isinstance(value, str)
             and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value),
             "identifier_invalid")
    return value


def _private_text(value, limit=1200):
    """私人 metadata 可含空白，但不能含控制字元或 HTML。"""

    _require(isinstance(value, str) and 0 < len(value.strip()) <= limit
             and not any(ord(char) < 32 for char in value)
             and "<" not in value and ">" not in value,
             "text_invalid")
    return value.strip()


def _read(root, relative, *, maximum=8_000_000):
    """讀工作區內 JSON，拒絕過大與 symlink。"""

    path = review.safe_path(root, relative)
    _require(path.is_file() and path.stat().st_size <= maximum, "source_missing")
    try:
        return path, json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError):
        raise PerformanceCollectError("source_invalid") from None


def _write_new(root, relative, value):
    """以 0600 原子建立私人資料，不覆蓋既有報告或證據。"""

    path = review.safe_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    encoded = review.canonical(value)
    _require(len(encoded) <= 8_000_000, "output_too_large")
    descriptor, name = tempfile.mkstemp(prefix=".performance-source-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise PerformanceCollectError("output_exists") from None
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


def _load_existing(root, relative, request_hash):
    """中斷續跑只重用同一 request hash 的既有證據，不重讀 API。"""

    path = review.safe_path(root, relative)
    if not path.exists():
        return None
    _require(path.is_file() and path.stat().st_size <= 8_000_000,
             "existing_evidence_invalid")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError):
        raise PerformanceCollectError("existing_evidence_invalid") from None
    _require(value.get("schema_version") == 1
             and value.get("kind") == "official_performance_observation"
             and value.get("request_sha256") == request_hash,
             "existing_evidence_changed")
    return path, value


def _plan(data, source_mode):
    """驗證單一平台／來源時區的 collection plan。"""

    _require(isinstance(data, dict) and set(data) == PLAN_FIELDS
             and data.get("schema_version") == 1
             and data.get("source_mode") == source_mode,
             "plan_fields")
    _identifier(data["report_id"])
    _require(data.get("mode") in review.MODES
             and data.get("platform") in PLATFORMS,
             "plan_scope")
    _private_text(data["account_ref"])
    try:
        expected = review.periods(data["mode"], data["period"]["end"])
    except (ValueError, KeyError, TypeError):
        raise PerformanceCollectError("period_invalid") from None
    _require(expected == {"period": data["period"],
                          "comparison_period": data["comparison_period"]},
             "period_invalid")
    try:
        review.load_timezone(data["timezone"])
    except review.TimezoneDataMissing:
        raise PerformanceCollectError("timezone_data_missing") from None
    except (review.ZoneInfoNotFoundError, ValueError, TypeError):
        raise PerformanceCollectError("timezone_invalid") from None
    series = data.get("series")
    _require(isinstance(series, list) and 0 < len(series) <= 20,
             "series_invalid")
    seen = set()
    for item in series:
        expected_fields = SERIES_FIELDS | ({"query"} if source_mode == "official_api"
                                           else {"artifacts"})
        _require(isinstance(item, dict) and set(item) == expected_fields,
                 "series_fields")
        _identifier(item["key"])
        _require(item["key"] not in seen, "series_duplicate")
        seen.add(item["key"])
        for field in ("role", "metric", "definition", "unit", "scope", "segment"):
            _private_text(item[field])
        _require(item["aggregation"] in {"total", "unique", "snapshot", "average", "rate"}
                 and item["basis"] in {"period_activity", "period_end_snapshot"}
                 and ((item["aggregation"] == "snapshot")
                      == (item["basis"] == "period_end_snapshot")),
                 "series_identity")
        if source_mode == "official_api":
            _require(data["platform"] != "substack" and isinstance(item["query"], dict)
                     and item["query"].get("metric") == item["metric"],
                     "official_query_invalid")
            try:
                metric_catalog.validate_official_series(
                    data["platform"], item, data["timezone"])
            except metric_catalog.MetricCatalogError:
                raise PerformanceCollectError(
                    "official_metric_contract_invalid") from None
        else:
            _require(isinstance(item["artifacts"], dict)
                     and set(item["artifacts"]) == {"current", "previous"}
                     and all(isinstance(value, str) for value in item["artifacts"].values()),
                     "import_artifacts_invalid")
            try:
                metric_catalog.validate_imported_series(data["platform"], item)
            except metric_catalog.MetricCatalogError:
                raise PerformanceCollectError(
                    "import_metric_contract_invalid") from None
    scope = data.get("scope")
    if source_mode == "official_api":
        _require(isinstance(scope, dict)
                 and set(scope) == OfficialPerformanceAdapter.SCOPE_KEYS
                 and scope.get("platform") == data["platform"]
                 and scope.get("account_id") == data["account_ref"],
                 "official_scope_invalid")
    else:
        _require(scope == {"confirmed_read": True}, "import_scope_invalid")
    return data


def _point(item, period, status, value, coverage, observed_at,
           evidence_path, evidence_hash, timezone, *, definition=None):
    """建立 performance_review schema 1 的單一 point。"""

    return {
        "metric": item["metric"],
        "definition": definition if definition is not None else item["definition"],
        "unit": item["unit"], "aggregation": item["aggregation"],
        "scope": item["scope"], "segment": item["segment"],
        "basis": item["basis"], "timezone": timezone, "period": period,
        "status": status, "coverage": coverage, "value": value,
        "observed_at": observed_at, "evidence_path": evidence_path,
        "evidence_sha256": evidence_hash,
    }


def _failure_status(kind):
    """映射到分析契約的五種狀態。"""

    if kind == "permission_denied":
        return "permission_denied"
    if kind == "invalid_metric":
        return "definition_changed"
    return "read_failed"


def _journal(root, plan):
    """collection 計畫只保存雜湊與非敏感範圍，供中斷續跑核對。"""

    request_hash = review.digest(review.canonical(plan))
    relative = f".local/social-media/performance/collections/{plan['report_id']}.json"
    path = review.safe_path(root, relative)
    value = {"schema_version": 1, "kind": "performance_collection",
             "report_id": plan["report_id"], "platform": plan["platform"],
             "source_mode": plan["source_mode"], "request_sha256": request_hash}
    if path.exists():
        _, current = _read(root, relative, maximum=1_000_000)
        _require(current == value, "collection_plan_changed")
    else:
        _write_new(root, relative, value)
    return request_hash


def _dataset(plan, series):
    """組合既有分析 helper 所需 dataset。"""

    return {"schema_version": 1, "report_id": plan["report_id"],
            "mode": plan["mode"], "timezone": plan["timezone"],
            "period": plan["period"],
            "comparison_period": plan["comparison_period"], "series": series}


class PerformanceCollector:
    """官方 API 與匯入證據共用的本機 dataset 建立器。"""

    def __init__(self, workspace, *, adapter=None):
        self.root = review.workspace(workspace)
        self.adapter = adapter or OfficialPerformanceAdapter(self.root)

    def collect_official(self, data):
        """呼叫四平台受限 adapter，保存原始證據後建立 dataset。"""

        plan = _plan(data, "official_api")
        request_hash = _journal(self.root, plan)
        output = []
        counts = {status: 0 for status in review.STATUSES}
        for item in plan["series"]:
            row = {"key": item["key"], "platform": plan["platform"],
                   "account_ref": plan["account_ref"], "role": item["role"]}
            for label, period_name in (("current", "period"),
                                       ("previous", "comparison_period")):
                period = plan[period_name]
                evidence_relative = (f"social-media/performance/{plan['report_id']}/evidence/"
                                     f"{item['key']}-{label}.json")
                evidence_request = {
                    "request_sha256": request_hash, "series_key": item["key"],
                    "label": label, "period": period, "query": item["query"],
                    "aggregation": item["aggregation"],
                }
                evidence_request_hash = review.digest(review.canonical(evidence_request))
                existing = _load_existing(
                    self.root, evidence_relative, evidence_request_hash)
                if existing:
                    evidence_path, evidence = existing
                    observation = evidence["observation"]
                else:
                    try:
                        observation = self.adapter.fetch(
                            plan["scope"], item["query"], period,
                            aggregation=item["aggregation"])
                    except PerformanceAPIError as error:
                        observation = {
                            "platform": plan["platform"],
                            "account_id": plan["account_ref"],
                            "interface": "official_api",
                            "metric": item["metric"], "requested_period": period,
                            "observed_at": datetime.now().astimezone().isoformat(),
                            "status": _failure_status(error.kind), "value": None,
                            "coverage": "unknown", "error_kind": error.kind,
                        }
                    _require(observation.get("platform") == plan["platform"]
                             and observation.get("account_id") == plan["account_ref"]
                             and observation.get("interface") == "official_api"
                             and observation.get("metric") == item["metric"]
                             and observation.get("requested_period") == period,
                             "observation_scope_mismatch")
                    evidence = {
                        "schema_version": 1,
                        "kind": "official_performance_observation",
                        "request_sha256": evidence_request_hash,
                        "request": evidence_request,
                        "series_identity": {field: item[field]
                                            for field in SERIES_FIELDS},
                        "observation": observation,
                    }
                    evidence_path = _write_new(
                        self.root, evidence_relative, evidence)
                status = observation.get("status")
                value = observation.get("value")
                coverage = observation.get("coverage")
                _require(status in review.STATUSES
                         and coverage in {"complete", "partial", "unknown"}
                         and ((status == "available"
                               and type(value) in {int, float} and math.isfinite(value))
                              or (status != "available" and value is None)),
                         "observation_invalid")
                counts[status] += 1
                encoded = evidence_path.read_bytes()
                try:
                    observed_definition = metric_catalog.observed_definition(
                        plan["platform"], item["definition"], observation)
                except metric_catalog.MetricCatalogError:
                    raise PerformanceCollectError(
                        "observation_definition_invalid") from None
                row[label] = _point(
                    item, period, status, value, coverage,
                    observation["observed_at"],
                    evidence_path.relative_to(self.root).as_posix(),
                    review.digest(encoded), plan["timezone"],
                    definition=observed_definition)
            output.append(row)
        dataset = _dataset(plan, output)
        # 以既有分析器再次驗證實際證據、期間、數值與定義一致性。
        review.analyze(self.root, dataset)
        target_relative = f"social-media/performance/{plan['report_id']}/dataset.json"
        target = review.safe_path(self.root, target_relative)
        if target.exists():
            _require(target.read_bytes() == review.canonical(dataset),
                     "dataset_changed")
        else:
            _write_new(self.root, target_relative, dataset)
        return {"result": "complete", "dataset_path": target_relative,
                "series_count": len(output), "point_status_counts": counts,
                "external_writes": False}

    @staticmethod
    def _imported(root, path_value, plan, item, period):
        """驗證 MCP／官方匯出／受控瀏覽器已保存的觀測與原始證據。"""

        path, artifact = _read(root, path_value)
        fields = {"schema_version", "kind", "platform", "interface", "account_ref",
                  *SERIES_FIELDS, "timezone", "period", "status", "coverage",
                  "value", "observed_at", "eligibility",
                  "raw_evidence_path", "raw_evidence_sha256"}
        _require(isinstance(artifact, dict) and set(artifact) == fields
                 and artifact.get("schema_version") == 1
                 and artifact.get("kind") == "performance_source_observation"
                 and artifact.get("platform") == plan["platform"]
                 and artifact.get("interface") in IMPORT_INTERFACES
                 and artifact.get("account_ref") == plan["account_ref"]
                 and artifact.get("period") == period
                 and all(artifact.get(field) == item[field]
                         for field in SERIES_FIELDS)
                 and artifact.get("timezone") == plan["timezone"],
                 "import_identity_mismatch")
        try:
            metric_catalog.validate_import_eligibility(
                plan["platform"], artifact["interface"], artifact["eligibility"])
        except metric_catalog.MetricCatalogError:
            raise PerformanceCollectError("import_source_ineligible") from None
        status, value, coverage = (artifact.get("status"), artifact.get("value"),
                                   artifact.get("coverage"))
        _require(status in review.STATUSES
                 and coverage in {"complete", "partial", "unknown"}
                 and ((status == "available" and type(value) in {int, float}
                       and math.isfinite(value))
                      or (status != "available" and value is None)),
                 "import_value_invalid")
        raw = review.safe_path(root, artifact["raw_evidence_path"])
        _require(raw.is_file() and raw.stat().st_size <= 8_000_000
                 and raw.is_relative_to(root / review.DATA_ROOT)
                 and review.digest(raw.read_bytes()) == artifact["raw_evidence_sha256"],
                 "import_raw_evidence_changed")
        return path, artifact

    def collect_import(self, data):
        """只從已有原始證據的正式來源 artifact 建 dataset，不把手填值冒充 API。"""

        plan = _plan(data, "imported_evidence")
        _journal(self.root, plan)
        output = []
        counts = {status: 0 for status in review.STATUSES}
        interfaces = set()
        for item in plan["series"]:
            row = {"key": item["key"], "platform": plan["platform"],
                   "account_ref": plan["account_ref"], "role": item["role"]}
            for label, period_name in (("current", "period"),
                                       ("previous", "comparison_period")):
                path, artifact = self._imported(
                    self.root, item["artifacts"][label], plan, item,
                    plan[period_name])
                interfaces.add(artifact["interface"])
                counts[artifact["status"]] += 1
                row[label] = _point(
                    item, plan[period_name], artifact["status"], artifact["value"],
                    artifact["coverage"], artifact["observed_at"],
                    path.relative_to(self.root).as_posix(), review.digest(path.read_bytes()),
                    plan["timezone"])
            output.append(row)
        dataset = _dataset(plan, output)
        review.analyze(self.root, dataset)
        target_relative = f"social-media/performance/{plan['report_id']}/dataset.json"
        target = review.safe_path(self.root, target_relative)
        if target.exists():
            _require(target.read_bytes() == review.canonical(dataset),
                     "dataset_changed")
        else:
            _write_new(self.root, target_relative, dataset)
        return {"result": "complete", "dataset_path": target_relative,
                "series_count": len(output), "point_status_counts": counts,
                "interfaces": sorted(interfaces), "external_writes": False}


def run(workspace, command, data, *, adapter=None):
    """測試與 CLI 共用入口。"""

    collector = PerformanceCollector(workspace, adapter=adapter)
    if command == "collect-official":
        return collector.collect_official(data)
    if command == "collect-import":
        return collector.collect_import(data)
    raise PerformanceCollectError("command_invalid")


def main():
    """CLI 只輸出資料集位置與狀態數量，不輸出原始數值。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("collect-official", "collect-import"))
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        root = review.workspace(args.workspace)
        source_path, data = _read(root, args.input)
        _require(source_path.is_relative_to(root / review.DATA_ROOT),
                 "input_scope_invalid")
        print(json.dumps(run(root, args.command, data), ensure_ascii=False))
        return 0
    except (PerformanceCollectError, PerformanceAPIError, ValueError, TypeError,
            KeyError, OSError, OverflowError, UnicodeError) as error:
        # 只公開可操作的依賴缺口，其餘錯誤保留原本不洩漏資料的摘要。
        reason = ("timezone_data_missing" if isinstance(error, PerformanceCollectError)
                  and str(error) == "timezone_data_missing" else "invalid_or_conflicting_state")
        print(json.dumps({"result": "stopped", "reason": reason}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
