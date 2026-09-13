#!/usr/bin/env python3
"""以隔離目錄驗證第一個技能的安裝生命週期。"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / "scripts/manage_install.py"
SKILL = "website-setup"
BUILD = "website-build"
DESIGN = "website-design-preview"
DEPLOY = "website-deploy"
CONTENT = "website-content-writing"
SERVICE = "website-service-integration"
OPERATIONS = "website-operations"


def run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """執行生命週期命令並保留輸出。"""

    return subprocess.run(arguments, capture_output=True, text=True)


class InstallLifecycleTests(unittest.TestCase):
    """驗證安裝、重跑、衝突、更新、回復與可回復移除。"""

    def setUp(self) -> None:
        """建立完全隔離的虛構 Agent 入口與狀態。"""

        self.temporary = tempfile.TemporaryDirectory(prefix="fictional-website-install-")
        self.temp_root = Path(self.temporary.name)
        self.client_root = self.temp_root / "fictional-workspace/.agents/skills"
        self.state_root = self.temp_root / "local-state"

    def tearDown(self) -> None:
        """移除作業系統暫存資料。"""

        self.temporary.cleanup()

    def command(
        self,
        command: str,
        *,
        manifest: Path | None = None,
        client_root: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """呼叫安裝管理器的公開介面。"""

        return run(
            [
                sys.executable,
                str(MANAGER),
                command,
                "--manifest",
                str(manifest or ROOT / "install.manifest.toml"),
                "--registration",
                "agents_workspace",
                "--client-root",
                str(client_root or self.client_root),
                "--state-root",
                str(self.state_root),
            ]
        )

    def assert_success(self, result: subprocess.CompletedProcess[str]) -> dict:
        """要求命令成功並解析 JSON。"""

        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def make_version_two(self) -> Path:
        """在暫存目錄建立內容不同的完整第二候選。"""

        package = self.temp_root / "package-v2"
        shutil.copytree(ROOT, package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        manifest = package / "install.manifest.toml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace(
                'candidate_version = "0.7.0"', 'candidate_version = "0.8.0"'
            ),
            encoding="utf-8",
        )
        skill_file = package / f"skills/{SKILL}/SKILL.md"
        skill_file.write_text(
            skill_file.read_text(encoding="utf-8") + "\n<!-- 虛構第二候選 -->\n",
            encoding="utf-8",
        )
        return manifest

    def test_full_lifecycle_and_discovery_entry(self) -> None:
        """完整驗證安裝、更新、回復、移除與重新安裝。"""

        available = self.assert_success(self.command("status"))
        self.assertEqual(available["result"], "available")

        installed = self.assert_success(self.command("install"))
        self.assertEqual(installed["result"], "installed")
        installed_skill = self.client_root / SKILL / "SKILL.md"
        self.assertTrue(installed_skill.is_file())
        self.assertIn("name: website-setup", installed_skill.read_text(encoding="utf-8"))
        self.assertEqual(set(installed["managed_entries"]), {SKILL, CONTENT, DESIGN, BUILD, DEPLOY, SERVICE, OPERATIONS})
        self.assertTrue((self.client_root / BUILD / "SKILL.md").is_file())

        repeated = self.assert_success(self.command("install"))
        self.assertEqual(repeated["result"], "noop")
        self.assertEqual(repeated["verification"], "hashes_match")

        version_two = self.make_version_two()
        wrong_command = self.command("install", manifest=version_two)
        self.assertEqual(wrong_command.returncode, 2)
        self.assertNotIn("虛構第二候選", installed_skill.read_text(encoding="utf-8"))
        update_available = self.assert_success(self.command("status", manifest=version_two))
        self.assertEqual(update_available["result"], "installed_update_available")

        updated = self.assert_success(self.command("update", manifest=version_two))
        self.assertEqual(updated["result"], "updated")
        self.assertIn("虛構第二候選", installed_skill.read_text(encoding="utf-8"))

        rolled_back = self.assert_success(self.command("rollback", manifest=version_two))
        self.assertEqual(rolled_back["result"], "rolled_back")
        self.assertNotIn("虛構第二候選", installed_skill.read_text(encoding="utf-8"))

        removed = self.assert_success(self.command("remove"))
        self.assertEqual(removed["result"], "removed_to_quarantine")
        self.assertFalse((self.client_root / SKILL).exists())
        self.assertTrue(Path(removed["quarantine"]).joinpath(SKILL).is_dir())

        repeated_remove = self.assert_success(self.command("remove"))
        self.assertEqual(repeated_remove["result"], "noop")
        reinstalled = self.assert_success(self.command("install"))
        self.assertEqual(reinstalled["result"], "reinstalled")

    def test_unknown_or_modified_content_is_preserved(self) -> None:
        """未知同名內容與安裝後人工修改都會使變更停止。"""

        foreign_root = self.temp_root / "foreign/.agents/skills"
        foreign = foreign_root / SKILL
        foreign.mkdir(parents=True)
        marker = foreign / "KEEP.txt"
        marker.write_text("虛構外部內容\n", encoding="utf-8")
        blocked = self.command("install", client_root=foreign_root)
        self.assertEqual(blocked.returncode, 2)
        self.assertEqual(marker.read_text(encoding="utf-8"), "虛構外部內容\n")

        self.assert_success(self.command("install"))
        installed = self.client_root / SKILL / "SKILL.md"
        installed.write_text(installed.read_text(encoding="utf-8") + "\n虛構人工修改\n", encoding="utf-8")
        update = self.command("update", manifest=self.make_version_two())
        remove = self.command("remove")
        self.assertEqual(update.returncode, 2)
        self.assertEqual(remove.returncode, 2)
        self.assertIn("虛構人工修改", installed.read_text(encoding="utf-8"))

    def test_identical_unmanaged_skill_is_adopted_without_rewrite(self) -> None:
        """完全相同的既有入口只建立狀態，不重寫內容。"""

        target = self.client_root / SKILL
        target.parent.mkdir(parents=True)
        for name in (SKILL, CONTENT, DESIGN, BUILD, DEPLOY, SERVICE, OPERATIONS):
            shutil.copytree(ROOT / f"skills/{name}", self.client_root / name)
        shutil.copytree(ROOT / "template", self.client_root / BUILD / "assets/template")
        before = (target / "SKILL.md").stat().st_mtime_ns
        adopted = self.assert_success(self.command("install"))
        after = (target / "SKILL.md").stat().st_mtime_ns
        self.assertEqual(adopted["result"], "adopted_identical")
        self.assertEqual(before, after)

    def test_installed_template_gallery_and_scaffold_without_source(self) -> None:
        """來源消失、cwd 改變、整個工作區搬移後仍能從安裝副本建站。"""
        source = self.temp_root / "fictional-source"
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        self.assert_success(self.command("install", manifest=source / "install.manifest.toml"))
        source.rename(self.temp_root / "preserved-source")
        workspace = self.client_root.parents[1]
        moved = self.temp_root / "搬移後的 虛構工作區"
        workspace.rename(moved)
        client = moved / ".agents/skills"
        config = moved / "website/config.json"
        config.parent.mkdir()
        payload = json.loads((client / SKILL / "assets/default-config.json").read_text(encoding="utf-8"))
        payload["business"].update({
            "status": "configured", "site_name": "虛構工作室",
            "one_line_positioning": "協助虛構小店整理流程", "audience_summary": "虛構店主",
            "offerings": [{"name": "虛構諮詢", "summary": "流程討論"}],
            "primary_call_to_action": {"kind": "mailto", "label": "聯絡", "target": "mailto:hello@example.invalid"},
            "contact_channels": [{"kind": "email", "label": "Email", "target": "mailto:hello@example.invalid"}],
        })
        config.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        gallery = client / DESIGN / "scripts/style_gallery.py"
        scaffold = client / BUILD / "scripts/scaffold_site.py"
        def installed(script, *args):
            return self.assert_success(subprocess.run(
                [sys.executable, str(script), *args], cwd=self.temp_root,
                capture_output=True, text=True))
        listed = installed(gallery, "list")
        self.assertEqual(len(listed["themes"]), 6)
        installed(gallery, "render", "--workspace-root", str(moved))
        self.assertTrue((moved / ".local/website/style-gallery/index.html").is_file())
        target = moved / "site"
        installed(scaffold, "scaffold", "--config", str(config), "--target", str(target), "--confirm-write")
        self.assertTrue((target / "package-lock.json").is_file())
        self.assertEqual(len(list((target / "src/themes").glob("*/theme.json"))), 6)
        # 缺失時明確停止，不暗中改讀維護者來源的範本。
        template = client / BUILD / "assets/template"
        template.rename(template.with_name("preserved-template"))
        failed = subprocess.run([sys.executable, str(gallery), "list"], cwd=self.temp_root,
                                capture_output=True, text=True)
        self.assertNotEqual(failed.returncode, 0)

    def test_template_is_managed_during_update_rollback_and_remove(self) -> None:
        self.assert_success(self.command("install"))
        installed = self.client_root / BUILD / "assets/template/README.md"
        original = installed.read_bytes()
        candidate = self.make_version_two()
        with (candidate.parent / "template/README.md").open("a", encoding="utf-8") as stream:
            stream.write("\n虛構的範本更新\n")
        self.assert_success(self.command("update", manifest=candidate))
        self.assertNotEqual(installed.read_bytes(), original)
        self.assert_success(self.command("rollback", manifest=candidate))
        self.assertEqual(installed.read_bytes(), original)
        installed.write_bytes(original + b"\nfictional local edit\n")
        self.assertEqual(self.command("remove").returncode, 2)
        self.assertEqual(self.command("update", manifest=candidate).returncode, 2)

    def test_legacy_install_can_update_to_bundled_template(self) -> None:
        legacy = self.make_version_two()
        text = legacy.read_text(encoding="utf-8")
        text = text.replace('bundled_assets = [{ source_path = "template", target_path = "assets/template" }]\n', '')
        legacy.write_text(text, encoding="utf-8")
        self.assert_success(self.command("install", manifest=legacy))
        template = self.client_root / BUILD / "assets/template"
        self.assertFalse(template.exists())
        self.assertEqual(self.command("install").returncode, 2)
        self.assert_success(self.command("update"))
        self.assertTrue((template / "package-lock.json").is_file())
        self.assert_success(self.command("rollback"))
        self.assertFalse(template.exists())


if __name__ == "__main__":
    unittest.main()
