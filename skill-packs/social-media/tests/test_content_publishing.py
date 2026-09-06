#!/usr/bin/env python3
"""虛構平台資料測試，不連網、不呼叫 API 或憑證庫。"""

import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/social-content-publishing/scripts/publish_job.py"
SPEC = importlib.util.spec_from_file_location("publish_job", SCRIPT)
job = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(job)


class PublishingTests(unittest.TestCase):
    def setUp(self):
        """每案都有獨立暫存工作區、虛構文字、素材及證據。"""
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-social-publish-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.relative = "social-media/publishing/fictional-job/plan.json"
        (self.root / self.relative).parent.mkdir(parents=True)
        self.asset = self.root / "fictional-media.bin"
        self.asset.write_bytes(b"fictional-media-not-a-real-image")
        self.evidence = self.root / "readback.json"
        self.evidence.write_text('{"source":"fictional-platform-response"}', encoding="utf-8")
        item = {"id": "first", "platform": "facebook", "target_label": "虛構教學專頁",
                "target_id": "fictional-page", "target_url": "https://www.facebook.com/fictional-page",
                "interface": "official_api", "format": "image", "title": "", "body": "虛構教學圖卡",
                "assets": [{"path": self.asset.name, "sha256": job.file_hash(self.asset), "alt_text": "虛構圖卡"}],
                "action": "publish_now", "scheduled_at": None, "settings": {"visibility": "public", "crosspost": False},
                "review_ref": "fictional-user-copy-and-image-confirmation", "unresolved": []}
        self.plan = {"schema_version": 1, "job_id": "fictional-job", "items": [item]}
        self.write()

    def write(self):
        """測試產物只寫暫存資料夾。"""
        (self.root / self.relative).write_text(json.dumps(self.plan), encoding="utf-8")

    def preview(self):
        return job.preview(self.root, self.relative)

    def begin(self, item="first", **overrides):
        options = {"item_id": item, "expected": self.preview()["preview_sha256"],
                   "approval_ref": "fictional-user-publish-confirmation", "confirmed": True}
        options.update(overrides)
        return job.transaction(self.root, self.relative, "begin", **options)

    def receipt(self, item=None):
        item = item or self.plan["items"][0]
        return {"item_id": item["id"], "target_id": item["target_id"], "state": "published",
                "platform_id": "fictional-post", "url": "https://www.facebook.com/fictional-page/posts/fictional-post",
                "platform_time": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
                "observed_at": job.now(), "content_matches": True, "media_matches": True,
                "settings_readback": item["settings"], "evidence_path": self.evidence.name,
                "evidence_sha256": job.file_hash(self.evidence)}

    def record(self, receipt):
        path = "social-media/publishing/fictional-job/receipt.json"
        (self.root / path).write_text(json.dumps(receipt), encoding="utf-8")
        return job.transaction(self.root, self.relative, "record", item_id=receipt["item_id"], receipt_path=path)

    def test_preview_is_readonly_and_requires_real_confirmation_flag(self):
        files = sorted(self.root.rglob("*"))
        view = self.preview()
        self.assertEqual(view["plan"], self.plan)
        self.assertEqual(files, sorted(self.root.rglob("*")))
        for override in ({"confirmed": False}, {"expected": "wrong"}, {"approval_ref": ""}):
            with self.assertRaises(ValueError):
                self.begin(**override)
        self.assertFalse((self.root / self.relative).with_name("ledger.json").exists())

    def test_preview_binds_text_media_order_settings_and_workspace(self):
        old = self.preview()["preview_sha256"]
        for field, value in (("body", "改寫的虛構文案"), ("target_id", "other-fictional-page"),
                             ("settings", {"visibility": "private"})):
            plan = copy.deepcopy(self.plan)
            self.plan["items"][0][field] = value
            self.write()
            self.assertNotEqual(self.preview()["preview_sha256"], old)
            with self.assertRaises(ValueError):
                self.begin(expected=old)
            self.plan = plan
        self.write()
        self.asset.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "asset_changed"):
            self.preview()

    def test_begin_checkpoint_and_verified_result(self):
        self.assertEqual(self.begin()["result"], "in_progress")
        job.transaction(self.root, self.relative, "claim", item_id="first",
                        stage="post-created")
        result = job.transaction(self.root, self.relative, "checkpoint", item_id="first",
                                 stage="post-created", remote_id="fictional-post",
                                 checkpoint_outcome="remote-id-saved")
        self.assertEqual(result["result"], "in_progress")
        self.assertEqual(self.record(self.receipt())["result"], "published")
        with self.assertRaises(ValueError):
            self.begin()
        with self.assertRaises(ValueError):
            self.record(self.receipt() | {"state": "failed"})

    def test_unknown_blocks_retries_and_all_later_platforms(self):
        second = copy.deepcopy(self.plan["items"][0])
        second.update(id="second", body="另一份虛構文案")
        self.plan["items"].append(second)
        self.write()
        with self.assertRaisesRegex(ValueError, "previous_item_unverified"):
            self.begin("second")
        self.begin()
        receipt = self.receipt() | {"state": "unknown", "platform_id": None, "url": None, "platform_time": None}
        self.assertEqual(self.record(receipt)["result"], "unknown")
        with self.assertRaises(ValueError):
            self.begin()
        with self.assertRaises(ValueError):
            self.begin("second")
        # 只能補唯讀證據；查明後才允許下一項，不再送出第一項。
        self.record(self.receipt())
        self.assertEqual(self.begin("second")["result"], "in_progress")

    def test_cross_job_duplicate_is_blocked(self):
        self.begin()
        self.plan["job_id"] = "fictional-retry"
        self.relative = "social-media/publishing/fictional-retry/plan.json"
        (self.root / self.relative).parent.mkdir()
        self.write()
        with self.assertRaisesRegex(ValueError, "duplicate_attempt"):
            self.begin()

    def test_readback_needs_url_id_platform_time_and_real_settings(self):
        self.begin()
        for patch in ({"platform_id": None}, {"url": None}, {"platform_time": None},
                      {"platform_time": "2026-01-01T12:00:00"},
                      {"target_id": "other"}, {"url": "https://example.invalid/post"},
                      {"content_matches": False}, {"media_matches": False},
                      {"settings_readback": {}}, {"state": "scheduled"},
                      {"evidence_sha256": "wrong"},
                      {"platform_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()}):
            with self.assertRaises((ValueError, TypeError)):
                self.record(self.receipt() | patch)
        self.assertEqual(self.record(self.receipt())["result"], "published")

    def test_schedule_is_not_published_and_checks_exact_time(self):
        scheduled = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        self.plan["items"][0].update(action="native_schedule", scheduled_at=scheduled)
        self.write()
        self.begin()
        with self.assertRaises(ValueError):
            self.record(self.receipt())
        receipt = self.receipt() | {"state": "scheduled", "platform_time": scheduled}
        self.assertEqual(self.record(receipt)["result"], "scheduled")

    def test_past_and_unsupported_schedules_stop(self):
        self.plan["items"][0].update(action="native_schedule", scheduled_at="2020-01-01T00:00:00Z")
        self.write()
        with self.assertRaisesRegex(ValueError, "schedule_in_past"):
            self.begin()
        self.plan["items"][0].update(platform="instagram", target_url="https://www.instagram.com/fictional")
        self.write()
        with self.assertRaisesRegex(ValueError, "schedule_unsupported"):
            self.preview()

    def test_manual_mode_cannot_execute(self):
        self.plan["items"][0]["interface"] = "manual"
        self.write()
        self.preview()
        result = self.begin()
        self.assertEqual(result["result"], "awaiting_manual")
        self.assertTrue(result["manual_only"])
        self.assertFalse(result["external_actions"])
        with self.assertRaisesRegex(ValueError, "readback_only"):
            job.transaction(self.root, self.relative, "checkpoint", item_id="first", stage="post-created", remote_id="fictional")
        self.assertEqual(self.record(self.receipt())["result"], "published")

    def test_media_order_and_workspace_are_bound_to_preview(self):
        """順序與目標工作區改變都讓原預覽失效。"""
        second = self.root / "fictional-second.bin"
        second.write_bytes(b"different-fictional-media")
        self.plan["items"][0]["assets"].append({"path": second.name, "sha256": job.file_hash(second), "alt_text": "第二張"})
        self.write()
        old = self.preview()["preview_sha256"]
        self.plan["items"][0]["assets"].reverse()
        self.write()
        self.assertNotEqual(self.preview()["preview_sha256"], old)
        other = self.root / "other-workspace"
        (other / self.relative).parent.mkdir(parents=True)
        (other / self.relative).write_bytes((self.root / self.relative).read_bytes())
        (other / self.asset.name).write_bytes(self.asset.read_bytes())
        (other / second.name).write_bytes(second.read_bytes())
        self.assertNotEqual(job.preview(other, self.relative)["preview_sha256"], self.preview()["preview_sha256"])

    def test_readback_before_attempt_is_rejected(self):
        receipt = self.receipt()
        self.begin()
        with self.assertRaisesRegex(ValueError, "readback_predates_attempt"):
            self.record(receipt)

    def test_missing_asset_and_unresolved_and_secrets_block(self):
        for patch in ({"unresolved": ["尚未確認"]}, {"assets": []},
                      {"settings": {"access_token": "fictional"}},
                      {"target_url": "https://www.facebook.com/fictional?token=fictional"}):
            plan = copy.deepcopy(self.plan)
            self.plan["items"][0].update(patch)
            self.write()
            with self.assertRaises(ValueError):
                self.preview()
            self.plan = plan

    def test_lock_and_symlink_are_not_removed_or_followed(self):
        lock = self.root / "social-media/publishing/.transaction.lock"
        lock.write_text("fictional-other-process", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.begin()
        self.assertEqual(lock.read_text(), "fictional-other-process")
        link = self.root / "linked-media.bin"
        link.symlink_to(self.asset)
        self.plan["items"][0]["assets"][0]["path"] = link.name
        self.write()
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.preview()

    def test_all_platform_routes_and_substack_custom_domain(self):
        for platform, format_name, url in (
            ("youtube", "video", "https://www.youtube.com/@fictional"),
            ("instagram", "image", "https://www.instagram.com/fictional"),
            ("threads", "image", "https://www.threads.com/@fictional"),
            ("substack", "article", "https://publication.example.invalid")):
            self.plan["items"][0].update(platform=platform, format=format_name, target_url=url)
            self.write()
            self.preview()
            receipt = self.receipt() | {"url": url + "/fictional-post"}
            job.validate_receipt(self.root, self.plan["items"][0], receipt)
            with self.assertRaises(ValueError):
                job.validate_receipt(self.root, self.plan["items"][0], receipt | {"url": "https://another.example.invalid/post"})

    def test_cli_no_network_and_no_credential_output(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "preview", "--workspace", str(self.root),
                                 "--plan", self.relative], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertFalse(json.loads(result.stdout)["external_actions"])
        self.plan["items"][0]["settings"]["access_token"] = "fictional-sensitive-value"
        self.write()
        result = subprocess.run([sys.executable, str(SCRIPT), "preview", "--workspace", str(self.root),
                                 "--plan", self.relative], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("fictional-sensitive-value", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
