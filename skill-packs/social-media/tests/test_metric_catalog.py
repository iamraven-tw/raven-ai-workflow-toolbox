"""用虛構計畫驗證成效指標白名單與來源資格；不連網。"""

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills/social-performance-analysis/scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import metric_catalog as catalog


class MetricCatalogTests(unittest.TestCase):
    """確認文件化規則確實能阻止過時名稱與錯誤口徑。"""

    @staticmethod
    def youtube_item(metric="views"):
        """建立完全虛構的 YouTube plan series。"""

        definitions = {
            "views": "youtube-analytics-views-2026-08-27",
            "engagedViews": "youtube-analytics-engaged-views-2026-08-27",
        }
        return {
            "metric": metric, "definition": definitions.get(metric, "invented"),
            "unit": "count", "aggregation": "total",
            "basis": "period_activity",
            "query": {"metric": metric, "coverage_probe": True},
        }

    def test_catalog_has_five_platforms_and_direct_official_sources(self):
        value = catalog.load_catalog()
        self.assertEqual(set(value["platforms"]), {
            "youtube", "facebook", "instagram", "threads", "substack"})
        for source in value["sources"].values():
            self.assertRegex(source, r"^https://")

    def test_youtube_views_and_engaged_views_keep_distinct_definitions(self):
        catalog.validate_official_series(
            "youtube", self.youtube_item("views"), "America/Los_Angeles")
        catalog.validate_official_series(
            "youtube", self.youtube_item("engagedViews"), "America/Los_Angeles")
        self.assertNotEqual(self.youtube_item("views")["definition"],
                            self.youtube_item("engagedViews")["definition"])
        with self.assertRaisesRegex(catalog.MetricCatalogError,
                                    "youtube_query_contract"):
            catalog.validate_official_series(
                "youtube", self.youtube_item("views"), "UTC")

    def test_youtube_unknown_metric_and_wrong_unit_stop(self):
        with self.assertRaisesRegex(catalog.MetricCatalogError,
                                    "metric_not_allowlisted"):
            catalog.validate_official_series(
                "youtube", self.youtube_item("estimatedRevenue"),
                "America/Los_Angeles")
        item = self.youtube_item("views")
        item["unit"] = "minutes"
        with self.assertRaisesRegex(catalog.MetricCatalogError,
                                    "metric_identity_mismatch"):
            catalog.validate_official_series(
                "youtube", item, "America/Los_Angeles")

    def test_facebook_requires_runtime_api_description_probe(self):
        item = {
            "metric": "current_metric_from_official_ui",
            "definition": "facebook-page-insights-runtime-description",
            "unit": "count", "aggregation": "total",
            "basis": "period_activity",
            "query": {"metric": "current_metric_from_official_ui",
                      "api_period": "day",
                      "show_description_from_api_doc": True},
        }
        catalog.validate_official_series("facebook", item, "UTC")
        item["query"].pop("show_description_from_api_doc")
        with self.assertRaisesRegex(catalog.MetricCatalogError,
                                    "api_description_probe_required"):
            catalog.validate_official_series("facebook", item, "UTC")

    def test_threads_snapshot_and_substack_ineligible_source_stop(self):
        threads = {
            "metric": "followers_count", "definition": "invented",
            "unit": "count", "aggregation": "snapshot",
            "basis": "period_end_snapshot", "query": {"metric": "followers_count"},
        }
        with self.assertRaisesRegex(catalog.MetricCatalogError,
                                    "metric_not_allowlisted"):
            catalog.validate_official_series("threads", threads, "UTC")
        with self.assertRaisesRegex(catalog.MetricCatalogError,
                                    "source_ineligible"):
            catalog.validate_import_eligibility(
                "substack", "official_substack_mcp", "connected_only")

    def test_meta_response_description_change_changes_definition_id(self):
        first = {"status": "available", "response_period": "day",
                 "response_definition": "虛構正式說明 A"}
        second = json.loads(json.dumps(first))
        second["response_definition"] = "虛構正式說明 B"
        self.assertNotEqual(
            catalog.observed_definition("facebook", "base", first),
            catalog.observed_definition("facebook", "base", second))


if __name__ == "__main__":
    unittest.main()
