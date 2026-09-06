#!/usr/bin/env python3
"""發布交易整合的虛構測試；所有 adapter 都是記憶體假物件。"""

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/social-content-publishing/scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("publish_execute", SCRIPTS / "publish_execute.py")
execute = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(execute)
job = execute.job
official = execute.official


class FakeAdapter:
    """只記錄階段與回傳虛構平台資料，不讀憑證或連網。"""

    def __init__(self):
        self.calls = []
        self.access_error = None
        self.photo_error_at = None
        self.facebook_error = None
        self.instagram_statuses = []

    def verify_access(self, grant):
        self.calls.append(("verify_access", grant["platform"], grant["target_id"]))
        if self.access_error:
            raise official.PublishAPIError(self.access_error)
        return {"platform": grant["platform"], "target_id": grant["target_id"],
                "ready": True}

    def facebook_upload_photo(self, grant, **kwargs):
        number = sum(1 for call in self.calls if call[0] == "facebook_upload_photo") + 1
        self.calls.append(("facebook_upload_photo", number, kwargs))
        if self.photo_error_at == number:
            raise official.PublishAPIError("remote_result_unknown")
        return {"stage": "photo-uploaded", "remote_id": str(500 + number),
                "status": "pending_readback"}

    def facebook_create_feed(self, grant, **kwargs):
        self.calls.append(("facebook_create_feed", kwargs))
        if self.facebook_error:
            raise official.PublishAPIError(self.facebook_error)
        return {"stage": "post-created", "remote_id": "10001_70001",
                "status": "pending_readback"}

    def facebook_readback(self, grant, post_id):
        self.calls.append(("facebook_readback", post_id))
        return {"id": post_id, "message": "虛構貼文",
                "permalink_url": "https://www.facebook.com/fictional/posts/70001",
                "created_time": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
                "is_published": True, "scheduled_publish_time": None,
                "attachments": None}

    def instagram_create_media(self, grant, params):
        self.calls.append(("instagram_create_media", params))
        return {"stage": "container-created", "remote_id": "81001",
                "status": "pending_processing"}

    def instagram_container_status(self, grant, container_id):
        self.calls.append(("instagram_container_status", container_id))
        status = self.instagram_statuses.pop(0)
        return {"id": container_id, "status_code": status, "status": status}

    def instagram_publish(self, grant, container_id):
        self.calls.append(("instagram_publish", container_id))
        return {"stage": "media-published", "remote_id": "82002",
                "status": "pending_readback"}

    def instagram_readback(self, grant, media_id):
        self.calls.append(("instagram_readback", media_id))
        return {"id": media_id, "caption": "虛構貼文", "media_type": "IMAGE",
                "media_product_type": "FEED",
                "permalink": "https://www.instagram.com/p/fictional/",
                "timestamp": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
                "children": None}

    def youtube_start_upload(self, grant, **kwargs):
        self.calls.append(("youtube_start_upload", kwargs))
        return object()

    def youtube_upload(self, grant, session, **kwargs):
        self.calls.append(("youtube_upload", kwargs))
        return {"stage": "upload-incomplete", "remote_id": None,
                "uploaded_range": "bytes=0-9", "status": "pending"}


class PublishExecutionTests(unittest.TestCase):
    def setUp(self):
        """每案建立獨立暫存工作區與虛構計畫。"""

        self.temp = tempfile.TemporaryDirectory(prefix="fictional-publish-execute-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.relative = "social-media/publishing/integration-job/plan.json"
        (self.root / self.relative).parent.mkdir(parents=True)
        self.asset = self.root / "fictional-image.bin"
        self.asset.write_bytes(b"fictional-image")
        self.item = {
            "id": "first", "platform": "facebook",
            "target_label": "虛構粉絲專頁", "target_id": "10001",
            "target_url": "https://www.facebook.com/fictional",
            "interface": "official_api", "format": "text", "title": "",
            "body": "虛構貼文", "assets": [], "action": "publish_now",
            "scheduled_at": None, "settings": {"visibility": "public"},
            "review_ref": "fictional-content-review", "unresolved": [],
        }
        self.plan = {"schema_version": 1, "job_id": "integration-job",
                     "items": [self.item]}
        self.write()

    def write(self):
        """只寫暫存工作區。"""

        (self.root / self.relative).write_text(
            json.dumps(self.plan, ensure_ascii=False), encoding="utf-8",
        )

    def begin(self, item_id="first"):
        """模擬使用者已確認完整預覽。"""

        preview = job.preview(self.root, self.relative)
        return job.transaction(
            self.root, self.relative, "begin", item_id=item_id,
            expected=preview["preview_sha256"],
            approval_ref="fictional-user-publish-confirmation", confirmed=True,
        )

    def executor(self, adapter):
        return execute.PublishExecutor(self.root, self.relative, adapter=adapter)

    def add_asset(self, name="fictional-image.bin", content=None):
        path = self.root / name
        if content is not None:
            path.write_bytes(content)
        return {"path": name, "sha256": job.file_hash(path),
                "alt_text": "虛構圖片"}

    def ledger(self):
        return json.loads((self.root / self.relative).with_name("ledger.json").read_text())

    def test_facebook_text_runs_access_claim_checkpoint_readback_and_receipt(self):
        self.begin()
        adapter = FakeAdapter()
        result = self.executor(adapter).execute_api("first")
        self.assertEqual(result["result"], "published")
        self.assertEqual([call[0] for call in adapter.calls],
                         ["verify_access", "facebook_create_feed", "facebook_readback"])
        attempt = self.ledger()["items"]["first"]
        self.assertEqual(attempt["state"], "published")
        self.assertEqual(attempt["operations"][0]["stage"], "facebook-post")
        self.assertEqual(attempt["operations"][0]["remote_id"], "10001_70001")
        receipt = json.loads((self.root / result["receipt"]).read_text())
        self.assertEqual(receipt["settings_readback"], {"visibility": "public"})
        self.assertNotIn("access", json.dumps(receipt).lower())

    def test_preflight_credential_failure_happens_before_write_claim(self):
        self.begin()
        adapter = FakeAdapter()
        adapter.access_error = "reauth_required"
        with self.assertRaisesRegex(official.PublishAPIError, "reauth_required"):
            self.executor(adapter).execute_api("first")
        attempt = self.ledger()["items"]["first"]
        self.assertEqual(attempt["state"], "in_progress")
        self.assertEqual(attempt["operations"], [])

    def test_partial_carousel_stops_without_deleting_or_calling_feed(self):
        second = self.root / "fictional-second.bin"
        second.write_bytes(b"fictional-second")
        self.item.update(
            format="carousel",
            assets=[self.add_asset(), self.add_asset(second.name)],
            settings={"visibility": "public", "media_urls": [
                "https://media.example.invalid/one.jpg",
                "https://media.example.invalid/two.jpg",
            ]},
        )
        self.write()
        self.begin()
        adapter = FakeAdapter()
        adapter.photo_error_at = 2
        result = self.executor(adapter).execute_api("first")
        self.assertEqual(result["result"], "unknown")
        self.assertEqual(sum(call[0] == "facebook_upload_photo" for call in adapter.calls), 2)
        self.assertFalse(any(call[0] == "facebook_create_feed" for call in adapter.calls))
        attempt = self.ledger()["items"]["first"]
        self.assertEqual(attempt["operations"][0]["remote_id"], "501")
        self.assertEqual(attempt["operations"][1]["state"], "claimed")
        with self.assertRaisesRegex(ValueError, "execution_not_allowed"):
            self.executor(adapter).execute_api("first")
        self.assertEqual(sum(call[0] == "facebook_upload_photo" for call in adapter.calls), 2)

    def test_container_processing_resumes_by_reading_same_id_without_recreate(self):
        self.item.update(
            platform="instagram", target_label="虛構 IG", target_id="20002",
            target_url="https://www.instagram.com/fictional", format="image",
            assets=[self.add_asset()], settings={
                "media_urls": ["https://media.example.invalid/ig.jpg"],
                "share_to_feed": True,
            },
        )
        self.write()
        self.begin()
        adapter = FakeAdapter()
        adapter.instagram_statuses = ["IN_PROGRESS", "FINISHED"]
        executor = self.executor(adapter)
        first = executor.execute_api("first")
        self.assertEqual(first["result"], "pending")
        self.assertEqual(first["ledger_state"], "in_progress")
        second = executor.execute_api("first")
        self.assertEqual(second["result"], "pending")
        self.assertEqual(sum(call[0] == "instagram_create_media" for call in adapter.calls), 1)
        self.assertEqual(sum(call[0] == "instagram_publish" for call in adapter.calls), 1)
        attempt = self.ledger()["items"]["first"]
        self.assertEqual([op["stage"] for op in attempt["operations"]],
                         ["instagram-parent-container", "instagram-publish"])

    def test_youtube_308_is_recorded_and_never_starts_second_session(self):
        video = self.root / "fictional-video.mp4"
        video.write_bytes(b"fictional-video")
        self.item.update(
            platform="youtube", target_label="虛構頻道", target_id="UCfake001",
            target_url="https://www.youtube.com/@fictional", format="video",
            title="虛構影片", assets=[self.add_asset(video.name)],
            settings={"category_id": "22", "tags": ["虛構"],
                      "privacy_status": "private", "notify_subscribers": False,
                      "made_for_kids": False, "contains_synthetic_media": True},
        )
        self.write()
        self.begin()
        adapter = FakeAdapter()
        result = self.executor(adapter).execute_api("first")
        self.assertEqual(result["result"], "pending")
        self.assertEqual(sum(call[0] == "youtube_start_upload" for call in adapter.calls), 1)
        self.assertEqual(sum(call[0] == "youtube_upload" for call in adapter.calls), 1)
        checkpoints = self.ledger()["items"]["first"]["checkpoints"]
        self.assertEqual(checkpoints[0]["outcome"], "sensitive-reference-memory-only")
        self.assertEqual(checkpoints[1]["outcome"], "pending-without-remote-id")
        with self.assertRaisesRegex(ValueError, "execution_not_allowed"):
            self.executor(adapter).execute_api("first")
        self.assertEqual(sum(call[0] == "youtube_start_upload" for call in adapter.calls), 1)

    def test_unknown_first_platform_blocks_second_platform_begin(self):
        second = dict(self.item)
        second.update(id="second", body="第二篇虛構貼文")
        self.plan["items"].append(second)
        self.write()
        self.begin("first")
        adapter = FakeAdapter()
        adapter.facebook_error = "remote_result_unknown"
        result = self.executor(adapter).execute_api("first")
        self.assertEqual(result["result"], "unknown")
        with self.assertRaisesRegex(ValueError, "previous_item_unverified"):
            self.begin("second")
        self.assertEqual(sum(call[0] == "facebook_create_feed" for call in adapter.calls), 1)

    def test_substack_handoff_claim_and_independent_reload_observation(self):
        self.item.update(
            platform="substack", target_label="虛構刊物",
            target_id="fictional-publication",
            target_url="https://publication.example.invalid",
            interface="controlled_browser", format="article", title="虛構文章",
            settings={"audience": "free", "send_email": False},
        )
        self.write()
        self.begin()
        executor = self.executor(FakeAdapter())
        handoff = executor.prepare_browser_handoff("first")
        self.assertFalse(handoff["external_actions"])
        saved = json.loads((self.root / handoff["handoff"]).read_text())
        self.assertEqual(saved["rules"][0], "claim_before_first_remote_edit")
        self.assertEqual(executor.claim_browser_write("first")["result"],
                         "browser_write_claimed")
        with self.assertRaisesRegex(ValueError, "stage_already_claimed_do_not_resend"):
            executor.claim_browser_write("first")
        observation = {
            "source": "controlled_browser", "state": "published",
            "platform_id": "fictional-post-id",
            "url": "https://publication.example.invalid/p/fictional",
            "platform_time": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            "observed_at": job.now(), "content_matches": True,
            "media_matches": True, "settings_readback": self.item["settings"],
            "selected": {"reloaded": True, "publication_matches": True},
        }
        observation_path = "social-media/publishing/integration-job/observation.json"
        (self.root / observation_path).write_text(
            json.dumps(observation, ensure_ascii=False), encoding="utf-8",
        )
        result = executor.record_observation("first", observation_path)
        self.assertEqual(result["result"], "published")
        self.assertEqual(self.ledger()["items"]["first"]["state"], "published")


if __name__ == "__main__":
    unittest.main()
