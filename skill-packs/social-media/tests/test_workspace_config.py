#!/usr/bin/env python3
"""以虛構工作區驗證設定預覽、確認、寫入與秘密拒絕。"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / "skills/social-media-setup/scripts/manage_workspace.py"
DEFAULT = ROOT / "skills/social-media-setup/assets/default-config.json"


def run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """執行公開命令並保留輸出。"""

    return subprocess.run(arguments, capture_output=True, text=True)


class WorkspaceConfigurationTests(unittest.TestCase):
    """確認本機設定交易不會略過預覽或洩漏秘密。"""

    def setUp(self) -> None:
        """建立完全隔離的虛構候選與工作區。"""

        self.temporary = tempfile.TemporaryDirectory(prefix="fictional-social-setup-")
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "fictional-workspace"
        self.candidate = self.root / "candidate.json"
        payload = json.loads(DEFAULT.read_text(encoding="utf-8"))
        payload["strategy"].update(
            {
                "status": "partial",
                "primary_goal": "讓虛構讀者找到公開教學",
                "audience_summary": "需要清楚步驟的虛構初學者",
                "content_pillars": ["虛構教學"],
            }
        )
        payload["strategy"]["platform_roles"]["youtube"] = "保存完整虛構教學"
        payload["integrations"]["youtube"] = {
            "selected": True,
            "requested_capabilities": ["analytics"],
            "authorization_profile": "custom",
            "requested_permissions": [
                "https://www.googleapis.com/auth/yt-analytics.readonly"
            ],
            "declined_permissions": [],
            "preferred_interface": "official_api",
            "status": "planned",
            "verification": {
                "api_app": "planned",
                "user_auth": "planned",
                "platform_read": "planned",
                "remote_write": "not_requested",
            },
            "last_verified_at": None,
        }
        self.write_candidate(payload)

    def tearDown(self) -> None:
        """移除作業系統暫存資料。"""

        self.temporary.cleanup()

    def write_candidate(self, payload: dict) -> None:
        """寫入單一虛構候選。"""

        self.candidate.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def command(self, command: str, *extra: str) -> subprocess.CompletedProcess[str]:
        """呼叫設定管理器。"""

        arguments = [
            "python3",
            str(MANAGER),
            command,
            "--workspace-root",
            str(self.workspace),
        ]
        if command in {"preview", "apply"}:
            arguments.extend(["--candidate", str(self.candidate)])
        arguments.extend(extra)
        return run(arguments)

    def preview(self) -> dict:
        """取得成功預覽並解析 JSON。"""

        result = self.command("preview")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_preview_is_read_only_and_apply_requires_same_confirmation(self) -> None:
        """預覽不寫入，且套用必須帶同一份預覽雜湊。"""

        preview = self.preview()
        self.assertFalse(self.workspace.exists())
        self.assertTrue(preview["changes"])
        self.assertFalse(preview["contains_credentials"])

        missing_confirmation = self.command(
            "apply", "--expected-preview-sha256", preview["preview_sha256"]
        )
        self.assertEqual(missing_confirmation.returncode, 2)
        self.assertFalse(self.workspace.exists())

        wrong_digest = self.command(
            "apply",
            "--expected-preview-sha256",
            "0" * 64,
            "--confirm-write",
        )
        self.assertEqual(wrong_digest.returncode, 2)
        self.assertFalse(self.workspace.exists())

        applied = self.command(
            "apply",
            "--expected-preview-sha256",
            preview["preview_sha256"],
            "--confirm-write",
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        result = json.loads(applied.stdout)
        self.assertEqual(result["readback"], "hashes_match")
        config = self.workspace / "social-media/config.json"
        state = self.workspace / ".local/social-media/setup-state.json"
        self.assertTrue(config.is_file())
        self.assertTrue(state.is_file())
        state_payload = json.loads(state.read_text(encoding="utf-8"))
        self.assertFalse(state_payload["contains_credentials"])
        self.assertNotIn("candidate", state_payload)

        status = self.command("status")
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(json.loads(status.stdout)["verification"], "hashes_match")

    def test_preview_digest_stops_overwrite_after_existing_change(self) -> None:
        """正式設定在確認前變動時，舊預覽不可套用。"""

        first = self.preview()
        initial_apply = self.command(
            "apply",
            "--expected-preview-sha256",
            first["preview_sha256"],
            "--confirm-write",
        )
        self.assertEqual(initial_apply.returncode, 0, initial_apply.stderr)

        payload = json.loads(self.candidate.read_text(encoding="utf-8"))
        payload["strategy"]["primary_goal"] = "第二份虛構候選"
        self.write_candidate(payload)
        stale_preview = self.preview()

        config = self.workspace / "social-media/config.json"
        external = json.loads(config.read_text(encoding="utf-8"))
        external["strategy"]["primary_goal"] = "預覽後的虛構人工修改"
        config.write_text(
            json.dumps(external, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        stopped = self.command(
            "apply",
            "--expected-preview-sha256",
            stale_preview["preview_sha256"],
            "--confirm-write",
        )
        self.assertEqual(stopped.returncode, 2)
        preserved = json.loads(config.read_text(encoding="utf-8"))
        self.assertEqual(preserved["strategy"]["primary_goal"], "預覽後的虛構人工修改")

    def test_secret_fields_and_secret_shapes_are_rejected(self) -> None:
        """秘密鍵名與常見 Token 形狀都在預覽前拒絕。"""

        payload = json.loads(self.candidate.read_text(encoding="utf-8"))
        payload["access_token"] = "fictional-value-that-must-not-be-stored"
        self.write_candidate(payload)
        result = self.command("preview")
        self.assertEqual(result.returncode, 2)
        self.assertIn("不得包含秘密", result.stderr)
        self.assertFalse(self.workspace.exists())

        payload.pop("access_token")
        payload["strategy"]["audience_summary"] = (
            "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJmaWN0aW9uYWwifQ.signature"
        )
        self.write_candidate(payload)
        result = self.command("preview")
        self.assertEqual(result.returncode, 2)
        self.assertIn("疑似含有秘密", result.stderr)

    def test_schema_rejects_path_escape_and_unproven_verified_status(self) -> None:
        """相對路徑跳脫與沒有讀回時間的 verified 都會停止。"""

        payload = json.loads(self.candidate.read_text(encoding="utf-8"))
        payload["strategy"]["strategy_source"] = "../private.md"
        self.write_candidate(payload)
        self.assertEqual(self.command("preview").returncode, 2)

        payload["strategy"]["strategy_source"] = "sources/strategy/social.md"
        payload["integrations"]["youtube"]["status"] = "verified"
        self.write_candidate(payload)
        result = self.command("preview")
        self.assertEqual(result.returncode, 2)
        self.assertIn("缺少平台讀取證據", result.stderr)

    def test_verification_stages_cannot_be_collapsed(self) -> None:
        """平台讀取、OAuth 與遠端寫入必須保存為不同狀態。"""

        payload = json.loads(self.candidate.read_text(encoding="utf-8"))
        integration = payload["integrations"]["youtube"]
        integration["status"] = "verified"
        integration["last_verified_at"] = "2030-01-02T03:04:05+00:00"
        integration["verification"] = {
            "api_app": "verified",
            "user_auth": "verified",
            "platform_read": "verified",
            "remote_write": "not_authorized",
        }
        self.write_candidate(payload)
        preview = self.preview()
        self.assertEqual(
            preview["candidate"]["integrations"]["youtube"]["verification"]["platform_read"],
            "verified",
        )
        self.assertEqual(
            preview["candidate"]["integrations"]["youtube"]["verification"]["remote_write"],
            "not_authorized",
        )

        integration["verification"]["user_auth"] = "not_started"
        self.write_candidate(payload)
        rejected = self.command("preview")
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("缺少使用者授權證據", rejected.stderr)

    def test_facebook_account_read_can_verify_without_remote_write(self) -> None:
        """Facebook 唯讀驗證可通過，但不得連帶宣稱遠端寫入成功。"""

        payload = json.loads(self.candidate.read_text(encoding="utf-8"))
        payload["integrations"]["facebook"] = {
            "selected": True,
            "requested_capabilities": ["account_read"],
            "authorization_profile": "custom",
            "requested_permissions": ["pages_show_list"],
            "declined_permissions": [
                "pages_manage_posts",
                "pages_manage_engagement",
                "pages_messaging",
            ],
            "preferred_interface": "official_api",
            "status": "verified",
            "verification": {
                "api_app": "verified",
                "user_auth": "verified",
                "platform_read": "verified",
                "remote_write": "not_authorized",
            },
            "last_verified_at": "2030-01-02T03:04:05+00:00",
        }
        self.write_candidate(payload)
        preview = self.preview()
        facebook = preview["candidate"]["integrations"]["facebook"]
        self.assertEqual(facebook["requested_capabilities"], ["account_read"])
        self.assertEqual(facebook["authorization_profile"], "custom")
        self.assertEqual(facebook["requested_permissions"], ["pages_show_list"])
        self.assertEqual(facebook["verification"]["platform_read"], "verified")
        self.assertEqual(facebook["verification"]["remote_write"], "not_authorized")

        candidate_facebook = payload["integrations"]["facebook"]
        candidate_facebook["verification"]["platform_read"] = "not_started"
        candidate_facebook["verification"]["remote_write"] = "verified"
        self.write_candidate(payload)
        rejected = self.command("preview")
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("缺少平台讀取證據", rejected.stderr)

    def test_full_management_permission_intent_is_preserved(self) -> None:
        """完整管理權限與逐平台 Meta 設定可以保存，但不等於遠端寫入。"""

        payload = json.loads(self.candidate.read_text(encoding="utf-8"))
        payload["integrations"]["threads"] = {
            "selected": True,
            "requested_capabilities": [
                "account_read",
                "publish",
                "public_comments",
                "analytics",
            ],
            "authorization_profile": "full_management",
            "requested_permissions": [
                "threads_basic",
                "threads_content_publish",
                "threads_read_replies",
                "threads_manage_replies",
                "threads_manage_insights",
            ],
            "declined_permissions": [],
            "preferred_interface": "official_api",
            "status": "planned",
            "verification": {
                "api_app": "planned",
                "user_auth": "planned",
                "platform_read": "planned",
                "remote_write": "not_authorized",
            },
            "last_verified_at": None,
        }
        self.write_candidate(payload)
        preview = self.preview()
        threads = preview["candidate"]["integrations"]["threads"]
        self.assertEqual(threads["authorization_profile"], "full_management")
        self.assertIn("threads_manage_insights", threads["requested_permissions"])
        self.assertEqual(threads["verification"]["remote_write"], "not_authorized")

    def test_permission_lists_cannot_overlap(self) -> None:
        """同一 permission 不得同時記為要求與拒絕。"""

        payload = json.loads(self.candidate.read_text(encoding="utf-8"))
        youtube = payload["integrations"]["youtube"]
        youtube["declined_permissions"] = list(youtube["requested_permissions"])
        self.write_candidate(payload)
        rejected = self.command("preview")
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("不得同時要求與拒絕", rejected.stderr)

    def test_meta_bundle_keeps_platform_permissions_separate(self) -> None:
        """Meta 可同輪初始化，但三平台權限與功能必須分開保存。"""

        payload = json.loads(self.candidate.read_text(encoding="utf-8"))
        planned_verification = {
            "api_app": "planned",
            "user_auth": "planned",
            "platform_read": "planned",
            "remote_write": "not_authorized",
        }
        payload["integrations"]["facebook"] = {
            "selected": True,
            "requested_capabilities": [
                "account_read",
                "publish",
                "public_comments",
                "analytics",
                "direct_messages",
            ],
            "authorization_profile": "full_management",
            "requested_permissions": [
                "pages_show_list",
                "pages_read_engagement",
                "pages_read_user_content",
                "pages_manage_posts",
                "pages_manage_engagement",
                "read_insights",
                "pages_manage_metadata",
                "pages_messaging",
            ],
            "declined_permissions": [],
            "preferred_interface": "official_api",
            "status": "planned",
            "verification": dict(planned_verification),
            "last_verified_at": None,
        }
        payload["integrations"]["instagram"] = {
            "selected": True,
            "requested_capabilities": [
                "account_read",
                "publish",
                "public_comments",
                "analytics",
                "direct_messages",
            ],
            "authorization_profile": "full_management",
            "requested_permissions": [
                "instagram_business_basic",
                "instagram_business_content_publish",
                "instagram_business_manage_comments",
                "instagram_business_manage_insights",
                "instagram_business_manage_messages",
            ],
            "declined_permissions": [],
            "preferred_interface": "official_api",
            "status": "planned",
            "verification": dict(planned_verification),
            "last_verified_at": None,
        }
        payload["integrations"]["threads"] = {
            "selected": True,
            "requested_capabilities": [
                "account_read",
                "publish",
                "public_comments",
                "analytics",
            ],
            "authorization_profile": "full_management",
            "requested_permissions": [
                "threads_basic",
                "threads_content_publish",
                "threads_read_replies",
                "threads_manage_replies",
                "threads_manage_insights",
            ],
            "declined_permissions": [],
            "preferred_interface": "official_api",
            "status": "planned",
            "verification": dict(planned_verification),
            "last_verified_at": None,
        }
        self.write_candidate(payload)
        preview = self.preview()["candidate"]["integrations"]
        self.assertIn("pages_messaging", preview["facebook"]["requested_permissions"])
        self.assertIn(
            "instagram_business_manage_messages",
            preview["instagram"]["requested_permissions"],
        )
        self.assertNotIn("direct_messages", preview["threads"]["requested_capabilities"])
        self.assertTrue(
            all(
                permission.startswith("threads_")
                for permission in preview["threads"]["requested_permissions"]
            )
        )

    def test_unselected_platform_cannot_carry_authorization_intent(self) -> None:
        """未選平台不得偷帶完整管理模式或 permission。"""

        payload = json.loads(self.candidate.read_text(encoding="utf-8"))
        facebook = payload["integrations"]["facebook"]
        facebook["authorization_profile"] = "full_management"
        facebook["requested_permissions"] = ["pages_show_list"]
        self.write_candidate(payload)
        rejected = self.command("preview")
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("未選取的 facebook 不得帶有整合設定", rejected.stderr)

    @unittest.skipUnless(hasattr(os, "symlink"), "此平台不支援 symlink 測試")
    def test_intermediate_symlink_cannot_redirect_configuration(self) -> None:
        """固定目標的父目錄 symlink 不得把寫入導向工作區外。"""

        outside = self.root / "outside"
        outside.mkdir()
        self.workspace.mkdir()
        (self.workspace / "social-media").symlink_to(outside, target_is_directory=True)
        result = self.command("preview")
        self.assertEqual(result.returncode, 2)
        self.assertIn("父路徑不得是 symlink", result.stderr)
        self.assertFalse((outside / "config.json").exists())


if __name__ == "__main__":
    unittest.main()
