#!/usr/bin/env python3
"""以虛構工作區驗證官網設定的預覽、確認、寫入與契約。"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / "skills/website-setup/scripts/manage_workspace.py"
DEFAULT = ROOT / "skills/website-setup/assets/default-config.json"


def run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """執行公開命令並保留輸出。"""

    return subprocess.run(arguments, capture_output=True, text=True)


def configured_candidate() -> dict:
    """建立一份完整、虛構、通過契約的候選設定。"""

    payload = json.loads(DEFAULT.read_text(encoding="utf-8"))
    payload["business"].update(
        {
            "status": "configured",
            "site_name": "虛構工作室",
            "one_line_positioning": "幫虛構的小店把流程交給 AI",
            "audience_summary": "沒有技術團隊、想省時間的虛構店主",
            "offerings": [{"name": "虛構啟動諮詢", "summary": "一次會談釐清可自動化的流程"}],
            "trust_signals": ["虛構的三年顧問經驗"],
            "primary_call_to_action": {"kind": "mailto", "label": "寫信給我", "target": "mailto:hello@example.invalid"},
            "contact_channels": [{"kind": "email", "label": "Email", "target": "mailto:hello@example.invalid"}],
        }
    )
    payload["design"].update({"status": "recommended", "tonality": "clean_minimal"})
    payload["hosting"]["worker_name"] = "fictional-studio"
    return payload


class WorkspaceConfigurationTests(unittest.TestCase):
    """確認本機設定交易不會略過預覽或洩漏秘密。"""

    def setUp(self) -> None:
        """建立完全隔離的虛構候選與工作區。"""

        self.temporary = tempfile.TemporaryDirectory(prefix="fictional-website-setup-")
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "fictional-workspace"
        self.workspace.mkdir()
        self.candidate = self.root / "candidate.json"
        self.write_candidate(configured_candidate())

    def tearDown(self) -> None:
        """移除作業系統暫存資料。"""

        self.temporary.cleanup()

    def write_candidate(self, payload: dict) -> None:
        """寫入候選設定。"""

        self.candidate.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def command(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        """呼叫工作區管理器。"""

        return run(["python3", str(MANAGER), *arguments, "--workspace-root", str(self.workspace)])

    def preview(self) -> dict:
        """取得候選預覽。"""

        result = self.command("preview", "--candidate", str(self.candidate))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def apply(self, digest: str, *, confirm: bool = True) -> subprocess.CompletedProcess[str]:
        """執行寫入。"""

        arguments = ["apply", "--candidate", str(self.candidate), "--expected-preview-sha256", digest]
        if confirm:
            arguments.append("--confirm-write")
        return self.command(*arguments)

    def assert_rejected(self, payload: dict, fragment: str) -> None:
        """要求候選在預覽階段被拒絕且不寫檔。"""

        self.write_candidate(payload)
        result = self.command("preview", "--candidate", str(self.candidate))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn(fragment, result.stderr)
        self.assertFalse((self.workspace / "website").exists())

    def test_default_template_is_valid_and_not_configured(self) -> None:
        """公開範本必須通過契約且維持未設定。"""

        result = self.command("preview")
        self.assertEqual(result.returncode, 0, result.stderr)
        preview = json.loads(result.stdout)
        self.assertEqual(preview["candidate"]["business"]["status"], "not_configured")
        self.assertEqual(preview["candidate"]["verification"]["custom_domain"], "not_applicable")

    def test_preview_is_read_only_and_apply_requires_same_confirmation(self) -> None:
        """預覽不寫檔；寫入需要旗標與相同雜湊，並可讀回。"""

        missing = self.command("status")
        self.assertEqual(json.loads(missing.stdout)["result"], "missing")
        preview = self.preview()
        self.assertFalse((self.workspace / "website").exists())
        self.assertEqual(preview["contains_credentials"], False)
        self.assertTrue(any(change["path"] == "$.business.site_name" for change in preview["changes"]))

        without_flag = self.apply(preview["preview_sha256"], confirm=False)
        self.assertEqual(without_flag.returncode, 2)
        wrong_digest = self.apply("0" * 64)
        self.assertEqual(wrong_digest.returncode, 2)
        self.assertFalse((self.workspace / "website").exists())

        applied = self.apply(preview["preview_sha256"])
        self.assertEqual(applied.returncode, 0, applied.stderr)
        payload = json.loads(applied.stdout)
        self.assertEqual(payload["result"], "configured")
        self.assertEqual(payload["readback"], "hashes_match")
        config = json.loads((self.workspace / "website/config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["business"]["site_name"], "虛構工作室")
        state = json.loads((self.workspace / ".local/website/setup-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["contains_credentials"], False)
        status = json.loads(self.command("status").stdout)
        self.assertEqual(status["result"], "configured")
        self.assertEqual(status["business_status"], "configured")

        reapplied = self.apply(self.preview()["preview_sha256"])
        self.assertEqual(json.loads(reapplied.stdout)["result"], "state_reconciled")

    def test_preview_digest_stops_overwrite_after_existing_change(self) -> None:
        """預覽後正式設定被改動時，舊雜湊失效且不覆蓋。"""

        first = self.preview()
        self.assertEqual(self.apply(first["preview_sha256"]).returncode, 0)
        second = self.preview()
        config_path = self.workspace / "website/config.json"
        changed = json.loads(config_path.read_text(encoding="utf-8"))
        changed["business"]["site_name"] = "另一個虛構名稱"
        config_path.write_text(json.dumps(changed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stale = self.apply(second["preview_sha256"])
        self.assertEqual(stale.returncode, 2)
        self.assertIn("預覽已失效", stale.stderr)
        self.assertEqual(json.loads(config_path.read_text(encoding="utf-8"))["business"]["site_name"], "另一個虛構名稱")
        self.assertEqual(json.loads(self.command("status").stdout)["result"], "changed_after_apply")

    def test_secret_fields_and_secret_shapes_are_rejected(self) -> None:
        """秘密欄位、Token 形狀與 Cloudflare 識別碼都在預覽階段拒絕。"""

        payload = configured_candidate()
        payload["hosting"]["api_token"] = "fictional"
        self.assert_rejected(payload, "秘密或私人識別欄位")
        payload = configured_candidate()
        payload["hosting"]["account_id"] = "fictional"
        self.assert_rejected(payload, "秘密或私人識別欄位")
        payload = configured_candidate()
        payload["business"]["trust_signals"] = ["eyJhbGciOiJIUzI1NiJ9.eyJmaWN0aW9uYWwiOnRydWV9.c2lnbmF0dXJl"]
        self.assert_rejected(payload, "疑似含有秘密內容")
        payload = configured_candidate()
        payload["business"]["primary_call_to_action"]["target"] = "https://example.invalid/?token=fictional"
        self.assert_rejected(payload, "疑似含有秘密內容")

    def test_schema_rejects_path_escape_and_wrong_targets(self) -> None:
        """跳出工作區的路徑與錯誤的連結目標都被拒絕。"""

        payload = configured_candidate()
        payload["business"]["profile_source"] = "../outside/profile.md"
        self.assert_rejected(payload, "跳出工作區")
        payload = configured_candidate()
        payload["business"]["primary_call_to_action"] = {
            "kind": "external_link",
            "label": "預約",
            "target": "http://example.invalid/contact",
        }
        self.assert_rejected(payload, "https://")
        payload = configured_candidate()
        payload["business"]["contact_channels"][0]["target"] = "hello@example.invalid"
        self.assert_rejected(payload, "mailto:")
        payload = configured_candidate()
        payload["schema_version"] = 2
        self.assert_rejected(payload, "schema_version")

    def test_verification_stages_cannot_be_collapsed(self) -> None:
        """驗證狀態不得跳層。"""

        payload = configured_candidate()
        payload["verification"]["workers_dev_deploy"] = "deployed_readback_verified"
        self.assert_rejected(payload, "Wrangler 登入")
        payload = configured_candidate()
        payload["verification"]["public_index"] = "index_verified"
        self.assert_rejected(payload, "公開收錄")
        payload = configured_candidate()
        payload["verification"]["custom_domain"] = "verified"
        self.assert_rejected(payload, "not_applicable")

    def test_custom_domain_routes_are_consistent(self) -> None:
        """網域意願、現況、路線與驗證欄位必須一致。"""

        payload = configured_candidate()
        payload["hosting"]["custom_domain"]["domain"] = "fictional.example"
        self.assert_rejected(payload, "未決定或不要自訂網域")

        payload = configured_candidate()
        payload["hosting"]["custom_domain"] = {
            "wanted": "yes",
            "current_state": "existing_on_cloudflare",
            "acquisition_route": "existing",
            "domain": "fictional.example",
        }
        self.assert_rejected(payload, "不得是 not_applicable")

        payload["verification"]["custom_domain"] = "not_started"
        self.write_candidate(payload)
        preview = self.preview()
        self.assertEqual(preview["candidate"]["hosting"]["custom_domain"]["domain"], "fictional.example")

        payload["hosting"]["custom_domain"].update({"acquisition_route": "cloudflare_registrar"})
        self.assert_rejected(payload, "to_purchase")

    def test_business_and_design_status_consistency(self) -> None:
        """未設定的商業資訊不得帶內容；已確認的設計必須有來源。"""

        payload = json.loads(DEFAULT.read_text(encoding="utf-8"))
        payload["business"]["site_name"] = "虛構工作室"
        self.assert_rejected(payload, "not_configured")
        payload = configured_candidate()
        payload["design"] = {"status": "confirmed", "tonality": "clean_minimal", "style_source": "open_design", "style_id": None, "fonts": "google"}
        self.assert_rejected(payload, "style_id")
        payload = configured_candidate()
        payload["design"] = {"status": "not_selected", "tonality": "clean_minimal", "style_source": "not_selected", "style_id": None, "fonts": "google"}
        self.assert_rejected(payload, "not_selected")

    def test_intermediate_symlink_cannot_redirect_configuration(self) -> None:
        """固定目標路徑中的 symlink 會使寫入停止。"""

        outside = self.root / "outside"
        outside.mkdir()
        os.symlink(outside, self.workspace / "website")
        preview = self.command("preview", "--candidate", str(self.candidate))
        self.assertEqual(preview.returncode, 2)
        self.assertIn("symlink", preview.stderr)
        self.assertFalse(any(outside.iterdir()))


if __name__ == "__main__":
    unittest.main()
