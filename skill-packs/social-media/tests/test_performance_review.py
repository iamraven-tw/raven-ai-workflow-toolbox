"""只用隔離虛構資料驗證四週期、比較與策略寫回，不連平台。"""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/social-performance-analysis/scripts/performance_review.py"
SPEC = importlib.util.spec_from_file_location("performance_review", SCRIPT)
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


class PerformanceTests(unittest.TestCase):
    """明確區分結構檢查、離線行為及未執行的外部驗收。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-performance-")
        self.root = Path(self.temp.name).resolve()
        self.folder = self.root / "social-media/performance/fictional-review"
        self.folder.mkdir(parents=True)
        self.evidence = self.folder / "evidence.json"
        self.evidence.write_text('{"fictional":true,"current":120,"previous":100}', encoding="utf-8")
        periods = review.periods("monthly", "2024-03-01")
        self.data = {"schema_version": 1, "report_id": "fictional-review", "mode": "monthly",
                     "timezone": "UTC", **periods, "series": []}
        def point(value, period):
            return {"metric": "fictional_views", "definition": "fictional-v1", "unit": "count",
                    "aggregation": "total", "scope": "owned-account", "segment": "organic",
                    "basis": "period_activity", "timezone": "UTC", "period": period,
                    "status": "available", "coverage": "complete", "value": value,
                    "observed_at": "2024-03-02T12:00:00+00:00",
                    "evidence_path": str(self.evidence.relative_to(self.root)),
                    "evidence_sha256": review.digest(self.evidence.read_bytes())}
        self.data["series"] = [{
            "key": "fictional-views", "platform": "youtube", "account_ref": "fictional-channel",
            "role": "虛構教育觸及", "current": point(120, periods["period"]),
            "previous": point(100, periods["comparison_period"])}]
        self.dataset_path = str((self.folder / "dataset.json").relative_to(self.root))
        self.report_path = str((self.folder / "report.json").relative_to(self.root))
        self.report = {
            "schema_version": 1, "report_id": "fictional-review",
            "observations": [
                {"id": "obs-1", "series_keys": ["fictional-views"], "fact": "虛構本期為 120、前期為 100。",
                 "inference": "觸及增加，原因待討論。", "limitations": "不代表完整觀看。"},
                {"id": "obs-2", "series_keys": ["fictional-views"], "fact": "兩期天數不同。",
                 "inference": "不能只憑總數推論效率。", "limitations": "沒有投入資料。"},
                {"id": "obs-3", "series_keys": ["fictional-views"], "fact": "目前僅有觀看指標。",
                 "inference": "無法判斷深度閱讀。", "limitations": "缺觀看時間資料。"}],
            "questions": ["這期是否有調整內容投入？"], "asked_at": "2024-03-03T12:00:00+00:00",
            "human": {"response": "這期增加教學示範。", "conversation_ref": "fictional-turn-2",
                      "received_at": "2024-03-03T12:01:00+00:00"},
            "insight": {"conclusion": "先觀察教學示範是否能持續帶來深度閱讀。",
                        "user_judgment": "使用者表示增加了教學示範，尚未確認因果。",
                        "scope": "僅適用目前頻道與相鄰月份，不推論其他平台。",
                        "confidence": "low", "recheck_on": "2024-04-01",
                        "observation_ids": ["obs-1", "obs-3"]}}
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        (self.root / self.dataset_path).write_bytes(review.canonical(self.data))
        self.report["dataset_sha256"] = review.digest((self.root / self.dataset_path).read_bytes())
        (self.root / self.report_path).write_bytes(review.canonical(self.report))

    def preview(self):
        return review.preview(self.root, self.dataset_path, self.report_path)[0]

    def apply(self, sha=None, confirmed=True):
        return review.apply(self.root, self.dataset_path, self.report_path,
                            sha or self.preview()["preview_sha256"], confirmed)

    def test_four_calendar_modes(self):
        expected = {
            "weekly": ("2023-12-25", "2024-01-01"),
            "monthly": ("2023-12-01", "2024-01-01"),
            "quarterly": ("2023-10-01", "2024-01-01"),
            "yearly": ("2023-01-01", "2024-01-01")}
        for mode, (start, end) in expected.items():
            with self.subTest(mode=mode):
                self.assertEqual(review.periods(mode, "2024-01-01")["period"], {"start": start, "end": end})

    def test_leap_month_and_difference(self):
        self.assertEqual(self.data["period"], {"start": "2024-02-01", "end": "2024-03-01"})
        result = review.analyze(self.root, self.data)[0]
        self.assertEqual(result["delta"], 20)
        self.assertEqual(result["percent_change"], 20)
        self.assertEqual(result["duration_note"], "unequal_calendar_days_not_efficiency")

    def test_zero_is_not_missing_or_infinite_growth(self):
        point = self.data["series"][0]["previous"]
        point["value"] = 0
        result = review.analyze(self.root, self.data)[0]
        self.assertTrue(result["comparable"])
        self.assertIsNone(result["percent_change"])
        self.data["series"][0]["current"]["value"] = 0
        self.assertEqual(review.analyze(self.root, self.data)[0]["delta"], 0)

    def test_four_missing_states_stay_distinct(self):
        for state in review.STATUSES - {"available"}:
            with self.subTest(state=state):
                point = self.data["series"][0]["current"]
                point.update(status=state, value=None)
                result = review.analyze(self.root, self.data)[0]
                self.assertFalse(result["comparable"])
                self.assertIn("current:" + state, result["reasons"])
                self.assertIsNone(result["delta"])

    def test_missing_zero_and_bad_numbers_rejected(self):
        point = self.data["series"][0]["current"]
        point.update(status="unavailable", value=0)
        with self.assertRaises(ValueError):
            review.analyze(self.root, self.data)
        point["status"] = "available"
        for value in (None, True, float("nan"), float("inf")):
            point["value"] = value
            with self.assertRaises(ValueError):
                review.analyze(self.root, self.data)

    def test_definition_scope_and_segment_changes_not_compared(self):
        for name in ("definition", "metric", "scope", "segment", "unit"):
            data = copy.deepcopy(self.data)
            data["series"][0]["previous"][name] += "-changed"
            result = review.analyze(self.root, data)[0]
            self.assertFalse(result["comparable"])
            self.assertIn("changed:" + name, result["reasons"])

    def test_partial_and_unknown_coverage_not_compared(self):
        for coverage in ("partial", "unknown"):
            self.data["series"][0]["current"]["coverage"] = coverage
            self.assertFalse(review.analyze(self.root, self.data)[0]["comparable"])

    def test_percent_points_not_percent_change(self):
        for name, value in (("current", 60), ("previous", 50)):
            self.data["series"][0][name].update(value=value, unit="percent", aggregation="rate")
        result = review.analyze(self.root, self.data)[0]
        self.assertEqual(result["delta"], 10)
        self.assertEqual(result["delta_unit"], "percentage_points")
        self.assertEqual(result["percent_change"], 20)

    def test_mixed_timezone_and_lifetime_rejected(self):
        for key, value in (("timezone", "Asia/Taipei"), ("basis", "lifetime")):
            data = copy.deepcopy(self.data)
            data["series"][0]["current"][key] = value
            with self.assertRaises(ValueError):
                review.analyze(self.root, data)

    def test_incomplete_period_and_early_read_rejected(self):
        data = copy.deepcopy(self.data)
        data["period"]["end"] = "2024-02-20"
        with self.assertRaises(ValueError):
            review.analyze(self.root, data)
        self.data["series"][0]["current"]["observed_at"] = "2024-02-20T00:00:00+00:00"
        with self.assertRaises(ValueError):
            review.analyze(self.root, self.data)

    def test_other_platform_separate_not_ranked(self):
        second = copy.deepcopy(self.data["series"][0])
        second.update(key="fictional-second", platform="facebook", role="虛構公開討論")
        self.data["series"].append(second)
        result = review.analyze(self.root, self.data)
        self.assertEqual([r["platform"] for r in result], ["youtube", "facebook"])
        self.assertTrue(all("rank" not in r and "total" not in r for r in result))

    def test_snapshot_is_only_net_change(self):
        for name in ("current", "previous"):
            self.data["series"][0][name].update(aggregation="snapshot", basis="period_end_snapshot")
        self.assertEqual(review.analyze(self.root, self.data)[0]["delta"], 20)
        self.data["series"][0]["current"]["basis"] = "period_activity"
        with self.assertRaises(ValueError):
            review.analyze(self.root, self.data)

    def test_report_structure_before_human_is_allowed(self):
        self.report["human"] = None
        self.report["insight"] = None
        self.save()
        review.check_report(self.data, self.report["dataset_sha256"], self.report)
        with self.assertRaises(ValueError):
            self.preview()

    def test_three_to_five_observations_and_one_question(self):
        for change in ("few", "many", "questions", "reference"):
            report = copy.deepcopy(self.report)
            if change == "few":
                report["observations"] = report["observations"][:2]
            elif change == "many":
                report["observations"] *= 2
            elif change == "questions":
                report["questions"].append("第二題")
            else:
                report["observations"][0]["series_keys"] = ["not-present"]
            with self.assertRaises(ValueError):
                review.check_report(self.data, report["dataset_sha256"], report)

    def test_preview_does_not_write(self):
        before = sorted(str(p) for p in self.root.rglob("*"))
        plan = self.preview()
        self.assertTrue(plan["creates_file"])
        self.assertEqual(before, sorted(str(p) for p in self.root.rglob("*")))
        self.assertNotIn("fictional_views", plan["append_text"])
        self.assertNotIn("120", plan["append_text"])

    def test_confirmation_required(self):
        with self.assertRaises(ValueError):
            self.apply(confirmed=False)
        self.assertFalse((self.root / review.STRATEGY).exists())

    def test_apply_preserves_existing_and_readback_receipt(self):
        target = self.root / review.STRATEGY
        target.parent.mkdir(parents=True)
        before = b"---\r\nstatus: not_configured\r\n---\r\nKEEP\r\n"
        target.write_bytes(before)
        plan = self.preview()
        self.assertEqual(self.apply(plan["preview_sha256"])["status"], "verified_local")
        after = target.read_bytes()
        self.assertTrue(after.startswith(before))
        self.assertEqual(review.digest(after), plan["after_sha256"])
        self.assertEqual((self.root / ".local/social-media/performance/fictional-review.before.md").read_bytes(), before)

    def test_changed_strategy_requires_new_preview(self):
        sha = self.preview()["preview_sha256"]
        target = self.root / review.STRATEGY
        target.parent.mkdir(parents=True)
        target.write_text("另一個編輯者的內容", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.apply(sha)
        self.assertEqual(target.read_text(), "另一個編輯者的內容")

    def test_changed_report_and_evidence_stop(self):
        sha = self.preview()["preview_sha256"]
        self.report["insight"]["conclusion"] = "另一個結論"
        self.save()
        with self.assertRaises(ValueError):
            self.apply(sha)
        self.evidence.write_text("已改變", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.preview()

    def test_duplicate_and_lock_stop(self):
        self.apply()
        with self.assertRaises(ValueError):
            self.preview()
        lock = self.root / ".local/social-media/performance/writeback.lock"
        lock.write_text("另一程序")
        with self.assertRaises(FileExistsError):
            self.apply("unused")
        self.assertTrue(lock.exists())

    def test_unfinished_transaction_stops(self):
        state = self.root / ".local/social-media/performance"
        state.mkdir(parents=True)
        (state / "fictional-old.transaction.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "結果不明"):
            self.apply()

    def test_interrupted_write_keeps_backup_and_blocks_retry(self):
        sha = self.preview()["preview_sha256"]
        with mock.patch.object(review.os, "replace", side_effect=OSError("虛構中斷")):
            with self.assertRaises(OSError):
                self.apply(sha)
        state = self.root / ".local/social-media/performance"
        self.assertTrue((state / "fictional-review.before.md").is_file())
        self.assertTrue((state / "fictional-review.transaction.json").is_file())
        self.assertFalse((self.root / review.STRATEGY).exists())
        with self.assertRaisesRegex(ValueError, "結果不明"):
            self.apply(sha)

    def test_receipt_failure_never_repeats_strategy_write(self):
        original = review.write_new
        def fail_receipt(path, payload):
            if str(path).endswith(".receipt.json"):
                raise OSError("虛構收據失敗")
            return original(path, payload)
        sha = self.preview()["preview_sha256"]
        with mock.patch.object(review, "write_new", side_effect=fail_receipt):
            with self.assertRaises(OSError):
                self.apply(sha)
        target = self.root / review.STRATEGY
        before_retry = target.read_bytes()
        with self.assertRaises(ValueError):
            self.apply(sha)
        self.assertEqual(target.read_bytes(), before_retry)

    def test_path_traversal_symlinks_and_public_root_rejected(self):
        with self.assertRaises(ValueError):
            review.safe_path(self.root, "../outside")
        target = self.root / "linked"
        target.symlink_to(self.folder, target_is_directory=True)
        with self.assertRaises(ValueError):
            review.safe_path(self.root, "linked/dataset.json")
        (self.root / "skill-packs").mkdir()
        with self.assertRaises(ValueError):
            review.workspace(self.root)
        with self.assertRaises(ValueError):
            review.workspace(Path.home())
        standalone = self.root / "fictional-standalone"
        standalone.mkdir()
        (standalone / "install.manifest.toml").write_text("schema_version = 1")
        # 另用沒有 Toolbox 父目錄的獨立暫存來源驗證單包防護。
        with tempfile.TemporaryDirectory(prefix="fictional-standalone-") as temporary:
            source = Path(temporary).resolve()
            (source / "install.manifest.toml").write_text("schema_version = 1")
            with self.assertRaisesRegex(ValueError, "獨立技能包"):
                review.workspace(source)

    def test_private_summary_does_not_accept_extra_raw_data(self):
        self.report["insight"]["raw_metrics"] = self.data["series"]
        self.save()
        with self.assertRaises(ValueError):
            self.preview()
        del self.report["insight"]["raw_metrics"]
        self.report["insight"]["conclusion"] = "文字\n## 假指令"
        self.save()
        with self.assertRaises(ValueError):
            self.preview()

    def test_real_cli_periods_and_check_report(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "periods", "--mode", "yearly",
                                 "--as-of", "2024-06-01"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(result.stdout)["period"]["start"], "2023-01-01")
        result = subprocess.run([sys.executable, str(SCRIPT), "check-report", "--workspace", str(self.root),
                                 "--dataset", self.dataset_path, "--report", self.report_path],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
