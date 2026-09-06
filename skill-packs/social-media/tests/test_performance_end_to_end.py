"""以同一批虛構資料驗證成效收集、討論與確認寫回；不連外部平台。"""

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills/social-performance-analysis/scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location(
    "performance_collect_end_to_end", SCRIPT_DIR / "performance_collect.py")
collect = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collect)
review = collect.review


class FictionalStatusAdapter:
    """用 metric 與期間回傳真零、缺值及三種錯誤，不執行網路請求。"""

    FAILURES = {
        "shares": "permission_denied",
        "subscribersGained": "rate_limited",
        "subscribersLost": "invalid_metric",
    }

    def __init__(self, current_period):
        self.current_period = current_period
        self.calls = []

    def fetch(self, scope, query, period, *, aggregation):
        """前期一律可用；本期依 metric 製造可辨識的虛構狀態。"""

        del aggregation
        metric = query["metric"]
        self.calls.append((metric, period))
        current = period == self.current_period
        if current and metric in self.FAILURES:
            raise collect.PerformanceAPIError(self.FAILURES[metric])
        if current and metric == "comments":
            status, value, coverage = "unavailable", None, "complete"
        else:
            values = {
                "views": (0, 12),
                "likes": (7, 0),
                "comments": (3, 4),
                "shares": (2, 5),
                "subscribersGained": (1, 6),
                "subscribersLost": (2, 8),
            }
            status, value, coverage = (
                "available", values[metric][0 if current else 1], "complete")
        return {
            "platform": scope["platform"],
            "account_id": scope["account_id"],
            "interface": "official_api",
            "login_route": "youtube_desktop",
            "api_version": "v2",
            "metric": metric,
            "requested_period": period,
            "observed_at": datetime(2024, 4, 3, 12,
                                    tzinfo=timezone.utc).isoformat(),
            "status": status,
            "value": value,
            "coverage": coverage,
            "response_definition": "虛構回應定義",
            "raw": {"fictional": True, "private-number": 987654321},
        }


class PerformanceEndToEndTests(unittest.TestCase):
    """逐一演練四週期及資料到策略的兩段人工關卡。"""

    METRICS = (
        "views", "likes", "comments", "shares",
        "subscribersGained", "subscribersLost",
    )

    @staticmethod
    def plan(mode):
        """建立符合 YouTube 最小指標目錄的虛構收集計畫。"""

        periods = review.periods(mode, "2024-04-01")
        catalog = collect.metric_catalog.load_catalog()["platforms"]["youtube"]["metrics"]
        series = []
        for metric in PerformanceEndToEndTests.METRICS:
            contract = catalog[metric]
            series.append({
                "key": "fictional-" + metric.lower(),
                "role": "虛構教育內容",
                "metric": metric,
                "definition": contract["definition"],
                "unit": contract["unit"],
                "aggregation": contract["aggregation"],
                "scope": "owned-channel",
                "segment": "all-content",
                "basis": contract["basis"],
                "query": {"metric": metric, "coverage_probe": True, "filters": ""},
            })
        return {
            "schema_version": 1,
            "report_id": "fictional-" + mode,
            "mode": mode,
            "timezone": "America/Los_Angeles",
            "platform": "youtube",
            "account_ref": "fictional-channel",
            **periods,
            "source_mode": "official_api",
            "scope": {
                "platform": "youtube",
                "account_id": "fictional-channel",
                "approval_ref": "fictional-read-approval",
                "confirmed_read": True,
                "allow_token_refresh": False,
            },
            "series": series,
        }

    @staticmethod
    def report(data, dataset_hash, *, with_human):
        """建立四項觀察與唯一策略問題；人類回答是另一個階段。"""

        report = {
            "schema_version": 1,
            "report_id": data["report_id"],
            "dataset_sha256": dataset_hash,
            "observations": [
                {
                    "id": "obs-zero",
                    "series_keys": ["fictional-views", "fictional-likes"],
                    "fact": "一個可用序列本期是真正零值，另一個前期是真正零值。",
                    "inference": "零值可比較，但零基準不能顯示成無限成長率。",
                    "limitations": "虛構資料不能代表真實頻道表現。",
                },
                {
                    "id": "obs-unavailable",
                    "series_keys": ["fictional-comments"],
                    "fact": "本期來源明確回報資料不可用。",
                    "inference": "不可把資料不可用補成零。",
                    "limitations": "本案例不判斷平台為何沒有資料。",
                },
                {
                    "id": "obs-access",
                    "series_keys": ["fictional-shares", "fictional-subscribersgained"],
                    "fact": "權限不足與讀取失敗是兩個不同狀態。",
                    "inference": "兩者都不能拿來計算本期增減。",
                    "limitations": "虛構錯誤不代表真實帳號需要重新授權。",
                },
                {
                    "id": "obs-definition",
                    "series_keys": ["fictional-subscriberslost"],
                    "fact": "來源回報指標定義已改變。",
                    "inference": "新舊定義必須拆段，不能接成連續趨勢。",
                    "limitations": "尚未取得可證明一致的歷史口徑。",
                },
            ],
            "questions": ["下一期是否先補足資料品質，再決定內容投入？"],
            "asked_at": "2024-04-04T10:00:00+00:00",
        }
        if with_human:
            report.update({
                "human": {
                    "response": "先補足權限與定義證據，不依缺值調整內容。",
                    "conversation_ref": "fictional-user-turn",
                    "received_at": "2024-04-04T10:01:00+00:00",
                },
                "insight": {
                    "conclusion": "下一期先補足資料品質，再評估內容投入。",
                    "user_judgment": "使用者決定不依缺值調整內容。",
                    "scope": "只適用此虛構頻道與本次相鄰完整曆期。",
                    "confidence": "low",
                    "recheck_on": "2024-05-01",
                    "observation_ids": ["obs-access", "obs-definition"],
                },
            })
        return report

    def run_mode(self, mode):
        """完成單一週期的收集、討論、預覽、確認寫入與讀回。"""

        with tempfile.TemporaryDirectory(
                prefix=f"fictional-performance-e2e-{mode}-") as temporary:
            root = Path(temporary).resolve()
            plan = self.plan(mode)
            adapter = FictionalStatusAdapter(plan["period"])
            collected = collect.run(root, "collect-official", plan, adapter=adapter)
            self.assertFalse(collected["external_writes"])
            self.assertEqual(len(adapter.calls), len(self.METRICS) * 2)
            self.assertEqual(collected["point_status_counts"], {
                "available": 8,
                "unavailable": 1,
                "permission_denied": 1,
                "read_failed": 1,
                "definition_changed": 1,
            })

            dataset_path = collected["dataset_path"]
            dataset_file = root / dataset_path
            data = json.loads(dataset_file.read_text(encoding="utf-8"))
            results = {item["key"]: item for item in review.analyze(root, data)}
            self.assertEqual(results["fictional-views"]["delta"], -12)
            self.assertEqual(results["fictional-views"]["percent_change"], -100)
            self.assertTrue(results["fictional-likes"]["comparable"])
            self.assertIsNone(results["fictional-likes"]["percent_change"])
            self.assertEqual(
                results["fictional-likes"]["baseline_note"],
                "nonpositive_baseline_no_percent_change")
            expected_reasons = {
                "fictional-comments": "current:unavailable",
                "fictional-shares": "current:permission_denied",
                "fictional-subscribersgained": "current:read_failed",
                "fictional-subscriberslost": "current:definition_changed",
            }
            for key, reason in expected_reasons.items():
                self.assertFalse(results[key]["comparable"])
                self.assertIn(reason, results[key]["reasons"])
                self.assertIsNone(results[key]["delta"])

            target = root / review.STRATEGY
            target.parent.mkdir(parents=True)
            original = "---\nstatus: not_configured\n---\n\n保留原策略。\n".encode()
            target.write_bytes(original)
            report_relative = (
                f"social-media/performance/{data['report_id']}/report.json")
            report_file = root / report_relative
            draft = self.report(data, review.digest(dataset_file.read_bytes()),
                                with_human=False)
            report_file.write_bytes(review.canonical(draft))
            review.check_report(data, draft["dataset_sha256"], draft)
            self.assertEqual(target.read_bytes(), original)
            with self.assertRaisesRegex(ValueError, "尚缺使用者判斷"):
                review.preview(root, dataset_path, report_relative)

            final_report = self.report(
                data, draft["dataset_sha256"], with_human=True)
            report_file.write_bytes(review.canonical(final_report))
            plan_preview = review.preview(root, dataset_path, report_relative)[0]
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(plan_preview["target"], review.STRATEGY)
            self.assertNotIn("987654321", plan_preview["append_text"])
            self.assertNotIn("subscribersGained", plan_preview["append_text"])

            with self.assertRaisesRegex(ValueError, "明確寫入確認"):
                review.apply(root, dataset_path, report_relative,
                             plan_preview["preview_sha256"], False)
            self.assertEqual(target.read_bytes(), original)
            receipt = review.apply(root, dataset_path, report_relative,
                                   plan_preview["preview_sha256"], True)
            self.assertEqual(receipt["status"], "verified_local")
            written = target.read_bytes()
            self.assertTrue(written.startswith(original))
            self.assertIn(data["report_id"].encode(), written)
            self.assertNotIn(b"987654321", written)
            self.assertNotIn(b"subscribersGained", written)
            self.assertTrue(dataset_file.is_relative_to(root / review.DATA_ROOT))
            self.assertTrue(report_file.is_relative_to(root / review.DATA_ROOT))
            state = root / ".local/social-media/performance"
            self.assertTrue((state / f"{data['report_id']}.before.md").is_file())
            self.assertTrue((state / f"{data['report_id']}.transaction.receipt.json").is_file())

    def test_four_modes_complete_data_to_strategy_flow(self):
        """週、月、季、年都必須經過同樣的第二次確認關卡。"""

        for mode in review.MODES:
            with self.subTest(mode=mode):
                self.run_mode(mode)

    def test_report_must_have_three_to_five_observations_and_one_question(self):
        """資料收集完成也不能繞過報告結構與單一問題。"""

        with tempfile.TemporaryDirectory(
                prefix="fictional-performance-e2e-gate-") as temporary:
            root = Path(temporary).resolve()
            plan = self.plan("monthly")
            result = collect.run(
                root, "collect-official", plan,
                adapter=FictionalStatusAdapter(plan["period"]))
            dataset_file = root / result["dataset_path"]
            data = json.loads(dataset_file.read_text(encoding="utf-8"))
            report = self.report(
                data, review.digest(dataset_file.read_bytes()), with_human=False)
            report["observations"] = report["observations"][:2]
            with self.assertRaisesRegex(ValueError, "三至五項"):
                review.check_report(data, report["dataset_sha256"], report)
            report = self.report(
                data, review.digest(dataset_file.read_bytes()), with_human=False)
            report["questions"].append("第二個問題不應同時出現。")
            with self.assertRaisesRegex(ValueError, "一個最重要"):
                review.check_report(data, report["dataset_sha256"], report)


if __name__ == "__main__":
    unittest.main()
