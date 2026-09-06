#!/usr/bin/env python3
"""發布格式能力表的虛構契約測試；不連線、不取憑證。"""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CAPABILITY_PATH = (
    ROOT / "skills/social-content-publishing/references/execution-sources.json"
)


class PublishingCapabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """只讀公開技能包的機器可讀能力表。"""

        cls.capabilities = json.loads(CAPABILITY_PATH.read_text(encoding="utf-8"))
        cls.platforms = cls.capabilities["platforms"]

    def test_route_is_selected_before_preview_and_begin(self):
        """格式路由必須先固定，未知寫入後不能改介面重發。"""

        policy = self.capabilities["routing_policy"]
        self.assertIn("before_preview_and_begin", policy)
        self.assertIn("never_switch_after_an_unknown_write", policy)

    def test_facebook_video_uses_browser_without_denying_official_api(self):
        """官方有 Reels API，不代表目前本機 adapter 已實作。"""

        route = self.platforms["facebook"]["format_routes"]["video"]
        self.assertEqual(route["route"], "controlled_browser")
        self.assertEqual(route["official_capability"], "reels_upload_api_documented")
        self.assertEqual(route["local_adapter"], "not_implemented")
        self.assertIn("legacy_collection_constraints_not_enforced", route)
        self.assertIn("refresh_required", route["current_limit_status"])

    def test_threads_carousel_has_official_bounds_but_browser_route(self):
        """輪播數量證據與本機是否實作必須分開。"""

        route = self.platforms["threads"]["format_routes"]["carousel"]
        self.assertEqual((route["minimum_items"], route["maximum_items"]), (2, 20))
        self.assertEqual(route["route"], "controlled_browser")
        self.assertEqual(route["local_adapter"], "not_implemented")
        self.assertIn("child_containers", route["documented_api_phases"])
        self.assertIn("threads_publishing_limit",
                      self.platforms["threads"]["publishing_limit_endpoint"])

    def test_instagram_carousel_variants_are_not_overclaimed(self):
        """現有協調器只將純圖片輪播列為 API 已實作。"""

        instagram = self.platforms["instagram"]
        route = instagram["format_routes"]["carousel"]
        self.assertEqual(route["maximum_items"], 10)
        self.assertEqual(route["image_only_route"], "official_api")
        self.assertEqual(route["mixed_image_video_route"], "controlled_browser")
        self.assertIn("do_not_hardcode", instagram["fixed_daily_limit_status"])

    def test_youtube_limits_remain_runtime_checked(self):
        """官方文件值要保留，但不能冒充帳號當下資格。"""

        route = self.platforms["youtube"]["format_routes"]["video"]
        self.assertEqual(route["route"], "official_api")
        self.assertEqual(route["maximum_file_size"], "256_GB")
        self.assertEqual(route["maximum_duration"], "12_hours_platform_limit")
        self.assertIn("subject_to_change", route["quota"])
        self.assertEqual(
            set(route["runtime_checks"]),
            {"account_feature_eligibility", "current_project_quota",
             "unverified_api_project_private_only_restriction"},
        )

    def test_all_declared_plan_formats_have_an_explicit_route(self):
        """計畫可接受的格式不能在執行時才猜介面。"""

        expected = {
            "youtube": {"video"},
            "facebook": {"text", "image", "carousel", "video"},
            "instagram": {"image", "carousel", "reel"},
            "threads": {"text", "image", "carousel", "video"},
            "substack": {"article"},
        }
        for platform, formats in expected.items():
            with self.subTest(platform=platform):
                self.assertEqual(set(self.platforms[platform]["format_routes"]), formats)


if __name__ == "__main__":
    unittest.main()
