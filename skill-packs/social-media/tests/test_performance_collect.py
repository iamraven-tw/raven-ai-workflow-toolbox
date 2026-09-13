"""用虛構證據驗證五平台成效資料收集層；不連外部服務。"""

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

try:
    from .platform_support import assert_private_file, private_fixture
except ImportError:
    from platform_support import assert_private_file, private_fixture


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills/social-performance-analysis/scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location(
    "performance_collect", SCRIPT_DIR / "performance_collect.py")
collect = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collect)


class FakeAdapter:
    """回傳可預期的虛構官方觀測。"""

    def __init__(self, failure=None):
        self.calls = []
        self.failure = failure

    def fetch(self, scope, query, period, *, aggregation):
        self.calls.append((scope, query, period, aggregation))
        if self.failure:
            raise collect.PerformanceAPIError(self.failure)
        value = 20 if period["start"] == "2024-02-01" else 10
        return {"platform": scope["platform"], "account_id": scope["account_id"],
                "interface": "official_api", "login_route": "youtube_desktop",
                "api_version": "v2", "metric": query["metric"],
                "requested_period": period,
                "observed_at": datetime(2024, 3, 2, 12,
                                        tzinfo=timezone.utc).isoformat(),
                "status": "available", "value": value,
                "coverage": "complete", "response_definition": "虛構定義",
                "raw": {"fictional": True}}


class BombAdapter:
    """中斷續跑時若仍讀 API 就讓測試失敗。"""

    def fetch(self, *args, **kwargs):
        del args, kwargs
        raise AssertionError("不應重讀 API")


class PerformanceCollectTests(unittest.TestCase):
    """驗證來源證據、狀態映射、續跑與 Substack 匯入。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-performance-collect-")
        self.root = Path(self.temp.name).resolve()
        private_fixture(self.root)
        periods = collect.review.periods("monthly", "2024-03-01")
        self.plan = {
            "schema_version": 1, "report_id": "fictional-source",
            "mode": "monthly", "timezone": "America/Los_Angeles",
            "platform": "youtube",
            "account_ref": "fictional-channel", **periods,
            "source_mode": "official_api",
            "scope": {"platform": "youtube", "account_id": "fictional-channel",
                      "approval_ref": "fictional-approval", "confirmed_read": True,
                      "allow_token_refresh": False},
            "series": [{"key": "fictional-views", "role": "虛構教育觸及",
                        "metric": "views",
                        "definition": "youtube-analytics-views-2026-08-27",
                        "unit": "count", "aggregation": "total",
                        "scope": "owned-channel", "segment": "all-content",
                        "basis": "period_activity",
                        "query": {"metric": "views", "coverage_probe": True}}],
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_official_collection_builds_private_evidence_and_dataset(self):
        adapter = FakeAdapter()
        result = collect.run(self.root, "collect-official", self.plan,
                             adapter=adapter)
        self.assertEqual(result["result"], "complete")
        self.assertEqual(result["series_count"], 1)
        self.assertEqual(result["point_status_counts"]["available"], 2)
        self.assertFalse(result["external_writes"])
        self.assertEqual(len(adapter.calls), 2)

        dataset = json.loads((self.root / result["dataset_path"]).read_text())
        self.assertEqual(dataset["series"][0]["current"]["value"], 20)
        self.assertEqual(dataset["series"][0]["previous"]["value"], 10)
        evidence = self.root / dataset["series"][0]["current"]["evidence_path"]
        payload = json.loads(evidence.read_text())
        self.assertEqual(payload["request"]["query"]["metric"], "views")
        self.assertNotIn("fictional-secret", evidence.read_text())
        assert_private_file(self, evidence)
        self.assertTrue((self.root / ".local/social-media/performance/collections/"
                         "fictional-source.json").is_file())

    def test_same_plan_resumes_without_api_reread(self):
        collect.run(self.root, "collect-official", self.plan,
                    adapter=FakeAdapter())
        result = collect.run(self.root, "collect-official", self.plan,
                             adapter=BombAdapter())
        self.assertEqual(result["result"], "complete")

    def test_permission_and_definition_errors_remain_distinct_from_zero(self):
        for kind, status in (("permission_denied", "permission_denied"),
                             ("invalid_metric", "definition_changed"),
                             ("rate_limited", "read_failed")):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(
                    prefix="fictional-performance-failure-") as temporary:
                plan = json.loads(json.dumps(self.plan))
                plan["report_id"] = "fictional-" + kind.replace("_", "-")
                failure_root = Path(temporary).resolve()
                result = collect.run(failure_root, "collect-official", plan,
                                     adapter=FakeAdapter(kind))
                dataset = json.loads(
                    (failure_root / result["dataset_path"]).read_text())
                point = dataset["series"][0]["current"]
                self.assertEqual(point["status"], status)
                self.assertIsNone(point["value"])
                self.assertEqual(point["coverage"], "unknown")

    def imported_plan(self):
        """建立 Substack 正式來源證據匯入計畫。"""

        plan = json.loads(json.dumps(self.plan))
        plan.update(platform="substack", account_ref="fictional-publication",
                    source_mode="imported_evidence",
                    scope={"confirmed_read": True})
        item = plan["series"][0]
        item.update(metric="traffic_views", definition="substack-traffic-2026",
                    scope="owned-publication")
        item.pop("query")
        item["artifacts"] = {
            "current": "social-media/performance/import/current.json",
            "previous": "social-media/performance/import/previous.json"}
        return plan

    def write_import(self, plan, label, value, *, tamper=False):
        """建立含原始證據雜湊的虛構匯入 artifact。"""

        folder = self.root / "social-media/performance/import"
        folder.mkdir(parents=True, exist_ok=True)
        raw = folder / f"{label}-raw.json"
        raw.write_text(json.dumps({"fictional": True, "value": value}))
        item = plan["series"][0]
        period = plan["period" if label == "current" else "comparison_period"]
        artifact = {
            "schema_version": 1, "kind": "performance_source_observation",
            "platform": "substack", "interface": "official_substack_mcp",
            "account_ref": plan["account_ref"],
            **{field: item[field] for field in collect.SERIES_FIELDS},
            "timezone": plan["timezone"], "period": period,
            "status": "available", "coverage": "complete", "value": value,
            "observed_at": "2024-03-02T12:00:00+00:00",
            "eligibility": "admin_bestseller_mcp_connected",
            "raw_evidence_path": raw.relative_to(self.root).as_posix(),
            "raw_evidence_sha256": collect.review.digest(raw.read_bytes()),
        }
        if tamper:
            artifact["raw_evidence_sha256"] = "0" * 64
        (folder / f"{label}.json").write_text(json.dumps(artifact))

    def test_substack_import_requires_bound_raw_official_evidence(self):
        plan = self.imported_plan()
        self.write_import(plan, "current", 20)
        self.write_import(plan, "previous", 10)
        result = collect.run(self.root, "collect-import", plan)
        self.assertEqual(result["interfaces"], ["official_substack_mcp"])
        dataset = json.loads((self.root / result["dataset_path"]).read_text())
        self.assertEqual(dataset["series"][0]["current"]["value"], 20)

    def test_number_only_or_tampered_import_is_rejected(self):
        plan = self.imported_plan()
        self.write_import(plan, "current", 20, tamper=True)
        self.write_import(plan, "previous", 10)
        with self.assertRaisesRegex(collect.PerformanceCollectError,
                                    "import_raw_evidence_changed"):
            collect.run(self.root, "collect-import", plan)

        (self.root / plan["series"][0]["artifacts"]["current"]).write_text(
            json.dumps({"value": 20}))
        with self.assertRaises(collect.PerformanceCollectError):
            collect.run(self.root, "collect-import", plan)

    def test_cli_import_outputs_only_summary_and_requires_private_data_root(self):
        plan = self.imported_plan()
        plan["report_id"] = "fictional-cli"
        self.write_import(plan, "current", 20)
        self.write_import(plan, "previous", 10)
        source = self.root / "social-media/performance/import/plan.json"
        source.write_text(json.dumps(plan))
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "performance_collect.py"),
             "collect-import", "--workspace", str(self.root),
             "--input", source.relative_to(self.root).as_posix()],
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], "complete")
        self.assertNotIn("value", result.stdout)
        self.assertNotIn("traffic_views", result.stdout)

        outside = self.root / "plan.json"
        outside.write_text(json.dumps(plan))
        stopped = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "performance_collect.py"),
             "collect-import", "--workspace", str(self.root),
             "--input", "plan.json"], capture_output=True, text=True,
            check=False)
        self.assertEqual(stopped.returncode, 2)
        self.assertEqual(json.loads(stopped.stdout)["result"], "stopped")

    def test_changed_plan_and_timezone_stop(self):
        collect.run(self.root, "collect-official", self.plan,
                    adapter=FakeAdapter())
        changed = json.loads(json.dumps(self.plan))
        changed["series"][0]["role"] = "changed-role"
        with self.assertRaisesRegex(collect.PerformanceCollectError,
                                    "collection_plan_changed"):
            collect.run(self.root, "collect-official", changed,
                        adapter=FakeAdapter())

        invalid = json.loads(json.dumps(self.plan))
        invalid["report_id"] = "fictional-timezone"
        invalid["timezone"] = "Mars/Olympus"
        with self.assertRaisesRegex(collect.PerformanceCollectError,
                                    "timezone_invalid"):
            collect.run(self.root, "collect-official", invalid,
                        adapter=FakeAdapter())

    def test_missing_timezone_data_stops_before_api_read(self):
        with mock.patch.object(collect.review, "ZoneInfo",
                               side_effect=collect.review.ZoneInfoNotFoundError):
            with self.assertRaisesRegex(collect.PerformanceCollectError, "timezone_data_missing"):
                collect.run(self.root, "collect-official", self.plan, adapter=BombAdapter())


if __name__ == "__main__":
    unittest.main()
