"""用虛構回應驗證官方成效 adapter；不連線、不讀真實憑證。"""

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/social-performance-analysis/scripts/official_performance_api.py"
SPEC = importlib.util.spec_from_file_location("official_performance_api", SCRIPT)
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)


class FakeRuntime:
    """只在記憶體提供虛構設定與 Token。"""

    def __init__(self, config, *, token="fictional-secret"):
        self.value = config
        self.token = token

    def config(self):
        return self.value

    def access(self, **kwargs):
        if kwargs.get("confirmed_read") is not True:
            raise AssertionError("讀取確認未傳入 runtime")
        return self.token

    def resource_context(self, **kwargs):
        if kwargs.get("confirmed_read") is not True:
            raise AssertionError("資源確認未傳入 runtime")
        return {"target_id": self.value["target_id"],
                "login_route": self.value["login_route"]}


class FakeHTTP:
    """依序回傳虛構官方 JSON，並保存要求供斷言。"""

    def __init__(self, *payloads):
        self.payloads = list(payloads)
        self.calls = []

    def request_json(self, endpoint, *, query, bearer):
        self.calls.append({"endpoint": endpoint, "query": query, "bearer": bearer})
        if not self.payloads:
            raise AssertionError("未預期的額外 API 呼叫")
        return api.HTTPResult(200, self.payloads.pop(0))


def runtime_factory(config):
    """建立符合 adapter 呼叫介面的虛構 factory。"""

    def build(workspace, platform, connection):
        del workspace, platform, connection
        return FakeRuntime(config)
    return build


def scope(platform, account_id="fictional-account"):
    """建立已確認但完全虛構的讀取範圍。"""

    return {"platform": platform, "account_id": account_id,
            "approval_ref": "fictional-approval", "confirmed_read": True,
            "allow_token_refresh": False}


class OfficialPerformanceAPITests(unittest.TestCase):
    """驗證端點、權限、期間、缺值及保守完整性判定。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-performance-api-")
        self.root = Path(self.temp.name).resolve()
        self.clock = lambda: datetime(2024, 2, 1, 12, tzinfo=timezone.utc)

    def tearDown(self):
        self.temp.cleanup()

    def adapter(self, config, http):
        return api.OfficialPerformanceAdapter(
            self.root, runtime_factory=runtime_factory(config),
            http_transport=http, clock=self.clock)

    def test_youtube_uses_inclusive_end_and_daily_coverage_probe(self):
        aggregate = {"kind": "youtubeAnalytics#resultTable",
                     "columnHeaders": [{"name": "views"}], "rows": [[30]]}
        daily = {"kind": "youtubeAnalytics#resultTable",
                 "columnHeaders": [{"name": "day"}, {"name": "views"}],
                 "rows": [["2024-01-01", 10], ["2024-01-02", 8],
                          ["2024-01-03", 12]]}
        http = FakeHTTP(aggregate, daily)
        config = {"target_id": "fictional-channel", "login_route": "youtube_desktop",
                  "scopes": ["https://www.googleapis.com/auth/youtube.readonly",
                             "https://www.googleapis.com/auth/yt-analytics.readonly"]}
        result = self.adapter(config, http).fetch(
            scope("youtube", "fictional-channel"),
            {"metric": "views", "coverage_probe": True},
            {"start": "2024-01-01", "end": "2024-01-04"},
            aggregation="total")
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["value"], 30)
        self.assertEqual(result["coverage"], "complete")
        self.assertEqual(len(http.calls), 2)
        self.assertEqual(http.calls[0]["endpoint"],
                         "https://youtubeanalytics.googleapis.com/v2/reports")
        self.assertEqual(http.calls[0]["query"]["endDate"], "2024-01-03")
        self.assertEqual(http.calls[1]["query"]["dimensions"], "day")
        self.assertNotIn("access_token", http.calls[0]["query"])
        self.assertEqual(http.calls[0]["bearer"], "fictional-secret")

    def test_youtube_empty_and_partial_data_are_not_complete_zero(self):
        headers = {"kind": "youtubeAnalytics#resultTable",
                   "columnHeaders": [{"name": "views"}]}
        empty = self.adapter(
            {"target_id": "fictional-channel", "login_route": "youtube_desktop",
             "scopes": ["https://www.googleapis.com/auth/youtube.readonly",
                        "https://www.googleapis.com/auth/yt-analytics.readonly"]},
            FakeHTTP(headers)).fetch(
                scope("youtube", "fictional-channel"),
                {"metric": "views", "coverage_probe": True},
                {"start": "2024-01-01", "end": "2024-01-04"},
                aggregation="total")
        self.assertEqual((empty["status"], empty["value"], empty["coverage"]),
                         ("unavailable", None, "unknown"))

        aggregate = dict(headers, rows=[[20]])
        daily = {"kind": "youtubeAnalytics#resultTable",
                 "columnHeaders": [{"name": "day"}, {"name": "views"}],
                 "rows": [["2024-01-01", 10], ["2024-01-03", 10]]}
        partial = self.adapter(
            {"target_id": "fictional-channel", "login_route": "youtube_desktop",
             "scopes": ["https://www.googleapis.com/auth/youtube.readonly",
                        "https://www.googleapis.com/auth/yt-analytics.readonly"]},
            FakeHTTP(aggregate, daily)).fetch(
                scope("youtube", "fictional-channel"),
                {"metric": "views", "coverage_probe": True},
                {"start": "2024-01-01", "end": "2024-01-04"},
                aggregation="total")
        self.assertEqual(partial["coverage"], "partial")

    def test_facebook_queries_page_insights_but_keeps_coverage_unknown(self):
        http = FakeHTTP({"data": [{"name": "fictional_views", "period": "day",
                                   "description_from_api_doc": "虛構觀看定義",
                                   "values": [{"value": 2}, {"value": 3}]}],
                         "paging": {"next": "https://graph.facebook.com/next?access_token=fictional-secret",
                                    "access_token": "fictional-secret"}})
        config = {"target_id": "fictional-page", "login_route": "facebook_pages",
                  "graph_version": "v99.0",
                  "scopes": ["pages_read_engagement", "read_insights"]}
        result = self.adapter(config, http).fetch(
            scope("facebook", "fictional-page"),
            {"metric": "fictional_views", "api_period": "day",
             "show_description_from_api_doc": True},
            {"start": "2024-01-01", "end": "2024-01-04"},
            aggregation="total")
        self.assertEqual(result["value"], 5)
        self.assertEqual(result["coverage"], "unknown")
        self.assertEqual(http.calls[0]["endpoint"],
                         "https://graph.facebook.com/v99.0/fictional-page/insights")
        self.assertEqual(http.calls[0]["query"]["since"], "2024-01-01")
        self.assertEqual(http.calls[0]["query"]["until"], "2024-01-04")
        self.assertEqual(http.calls[0]['query']['fields'], 'name,period,values,description_from_api_doc')
        self.assertIs(http.calls[0]["query"]["show_description_from_api_doc"],
                      True)
        self.assertNotIn("fictional-secret", str(result["raw"]))
        self.assertEqual(result["raw"]["paging"]["access_token"], "[REDACTED]")

    def test_instagram_routes_by_login_type(self):
        payload = {"data": [{"name": "reach", "period": "day",
                              "description": "虛構觸及定義",
                              "total_value": {"value": 7}}]}
        cases = (
            ("instagram_login", ["instagram_business_basic",
                                 "instagram_business_manage_insights"],
             "graph.instagram.com"),
            ("instagram_facebook_login", ["instagram_basic",
                                          "instagram_manage_insights",
                                          "pages_read_engagement"],
             "graph.facebook.com"),
        )
        for route, scopes, host in cases:
            with self.subTest(route=route):
                http = FakeHTTP(payload)
                config = {"target_id": "fictional-ig", "login_route": route,
                          "graph_version": "v99.0", "scopes": scopes}
                result = self.adapter(config, http).fetch(
                    scope("instagram", "fictional-ig"),
                    {"metric": "reach", "api_period": "day",
                     "metric_type": "total_value"},
                    {"start": "2024-01-01", "end": "2024-01-04"},
                    aggregation="unique")
                self.assertEqual(result["value"], 7)
                self.assertIn(host, http.calls[0]["endpoint"])

    def test_threads_uses_threads_insights_without_invented_date_query(self):
        http = FakeHTTP({"data": [{"name": "views", "period": "day",
                                   "description": "虛構個人檔案觀看定義",
                                   "total_value": {"value": 11}}]})
        config = {"target_id": "fictional-threads", "login_route": "threads_login",
                  "graph_version": "v99.0",
                  "scopes": ["threads_basic", "threads_manage_insights"]}
        result = self.adapter(config, http).fetch(
            scope("threads", "fictional-threads"), {"metric": "views"},
            {"start": "2024-01-01", "end": "2024-01-04"},
            aggregation="total")
        self.assertEqual(result["coverage"], "unknown")
        self.assertEqual(http.calls[0]["endpoint"],
                         "https://graph.threads.net/v99.0/fictional-threads/threads_insights")
        self.assertEqual(http.calls[0]["query"], {"metric": "views"})

    def test_scope_target_permissions_and_unsafe_aggregation_stop(self):
        config = {"target_id": "fictional-page", "login_route": "facebook_pages",
                  "graph_version": "v99.0", "scopes": ["pages_read_engagement"]}
        with self.assertRaisesRegex(api.PerformanceAPIError, "permission_denied"):
            self.adapter(config, FakeHTTP()).verify_access(
                scope("facebook", "fictional-page"))

        config["scopes"].append("read_insights")
        with self.assertRaisesRegex(api.PerformanceAPIError, "target_mismatch"):
            self.adapter(config, FakeHTTP()).verify_access(
                scope("facebook", "another-page"))

        payload = {"data": [{"name": "reach", "period": "day",
                              "description_from_api_doc": "虛構觸及定義",
                              "values": [{"value": 2}, {"value": 3}]}]}
        with self.assertRaisesRegex(api.PerformanceAPIError, "unsupported_response"):
            self.adapter(config, FakeHTTP(payload)).fetch(
                scope("facebook", "fictional-page"),
                {"metric": "reach", "api_period": "day",
                 "show_description_from_api_doc": True},
                {"start": "2024-01-01", "end": "2024-01-04"},
                aggregation="unique")

    def test_catalog_rejects_unverified_metric_or_wrong_aggregation(self):
        """固定白名單與平台範例不因欄位看似合理就放行。"""

        youtube = {"target_id": "fictional-channel", "login_route": "youtube_desktop",
                   "scopes": ["https://www.googleapis.com/auth/youtube.readonly",
                              "https://www.googleapis.com/auth/yt-analytics.readonly"]}
        with self.assertRaisesRegex(api.PerformanceAPIError, "invalid_metric"):
            self.adapter(youtube, FakeHTTP()).fetch(
                scope("youtube", "fictional-channel"),
                {"metric": "estimatedRevenue", "coverage_probe": True},
                {"start": "2024-01-01", "end": "2024-01-04"},
                aggregation="total")
        with self.assertRaisesRegex(api.PerformanceAPIError, "invalid_metric"):
            self.adapter(youtube, FakeHTTP()).fetch(
                scope("youtube", "fictional-channel"),
                {"metric": "averageViewDuration", "coverage_probe": True},
                {"start": "2024-01-01", "end": "2024-01-04"},
                aggregation="total")

        threads = {"target_id": "fictional-threads", "login_route": "threads_login",
                   "graph_version": "v99.0",
                   "scopes": ["threads_basic", "threads_manage_insights"]}
        with self.assertRaisesRegex(api.PerformanceAPIError, "invalid_metric"):
            self.adapter(threads, FakeHTTP()).fetch(
                scope("threads", "fictional-threads"),
                {"metric": "followers_count"},
                {"start": "2024-01-01", "end": "2024-01-04"},
                aggregation="snapshot")

    def test_facebook_requires_runtime_official_description_and_period(self):
        """Page 指標名稱沒有靜態清單時，以當次官方說明與 period 作證。"""

        config = {"target_id": "fictional-page", "login_route": "facebook_pages",
                  "graph_version": "v99.0",
                  "scopes": ["pages_read_engagement", "read_insights"]}
        window = {"start": "2024-01-01", "end": "2024-01-04"}
        with self.assertRaisesRegex(api.PerformanceAPIError, "invalid_request"):
            self.adapter(config, FakeHTTP()).fetch(
                scope("facebook", "fictional-page"),
                {"metric": "fictional_views", "api_period": "day"}, window,
                aggregation="total")
        missing = {"data": [{"name": "fictional_views", "period": "day",
                             "description": "一般說明",
                             "values": [{"value": 1}]}]}
        with self.assertRaisesRegex(api.PerformanceAPIError, "invalid_metric"):
            self.adapter(config, FakeHTTP(missing)).fetch(
                scope("facebook", "fictional-page"),
                {"metric": "fictional_views", "api_period": "day",
                 "show_description_from_api_doc": True}, window,
                aggregation="total")
        wrong_period = {"data": [{"name": "fictional_views", "period": "week",
                                  "description_from_api_doc": "正式說明",
                                  "values": [{"value": 1}]}]}
        with self.assertRaisesRegex(api.PerformanceAPIError, "invalid_metric"):
            self.adapter(config, FakeHTTP(wrong_period)).fetch(
                scope("facebook", "fictional-page"),
                {"metric": "fictional_views", "api_period": "day",
                 "show_description_from_api_doc": True}, window,
                aggregation="total")

    def test_http_allowlist_rejects_nonofficial_or_token_query(self):
        self.assertTrue(api.OfficialPerformanceHTTP._allowed(
            "https://youtubeanalytics.googleapis.com/v2/reports"))
        self.assertFalse(api.OfficialPerformanceHTTP._allowed(
            "https://example.com/v2/reports"))
        transport = api.OfficialPerformanceHTTP()
        with self.assertRaisesRegex(api.PerformanceAPIError, "invalid_request"):
            transport.request_json(
                "https://youtubeanalytics.googleapis.com/v2/reports",
                query={"access_token": "fictional-secret"}, bearer="fictional-secret")


if __name__ == "__main__":
    unittest.main()
