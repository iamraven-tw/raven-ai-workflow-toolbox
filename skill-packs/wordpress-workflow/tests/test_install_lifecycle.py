#!/usr/bin/env python3
"""以隔離目錄驗證 WordPress MCP 技能包安裝生命週期。"""

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
SKILLS = (
    "wordpress-mcp-workflow",
    "wordpress-customize-theme",
    "wordpress-publish-article",
)


class InstallLifecycleTests(unittest.TestCase):
    """驗證安裝、重跑、更新、回復、衝突與可復原移除。"""

    def setUp(self) -> None:
        """建立隔離的虛構技能入口與狀態目錄。"""

        self.temporary = tempfile.TemporaryDirectory(prefix="fictional-wordpress-install-")
        self.temp_root = Path(self.temporary.name)
        self.client_root = self.temp_root / "fictional-workspace/.agents/skills"
        self.state_root = self.temp_root / "local-state"

    def tearDown(self) -> None:
        """清理暫存資料。"""

        self.temporary.cleanup()

    def command(self, command: str, manifest: Path | None = None) -> subprocess.CompletedProcess[str]:
        """呼叫安裝管理器並保留 JSON 輸出。"""

        return subprocess.run(
            [
                sys.executable,
                str(MANAGER),
                command,
                "--manifest",
                str(manifest or ROOT / "install.manifest.toml"),
                "--registration",
                "agents_workspace",
                "--client-root",
                str(self.client_root),
                "--state-root",
                str(self.state_root),
            ],
            capture_output=True,
            text=True,
        )

    def success(self, result: subprocess.CompletedProcess[str]) -> dict:
        """要求命令成功並解析 JSON。"""

        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def make_version_two(self) -> Path:
        """建立只供測試的第二版候選。"""

        package = self.temp_root / "package-v2"
        shutil.copytree(ROOT, package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        manifest = package / "install.manifest.toml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace(
                'candidate_version = "0.1.0"', 'candidate_version = "0.2.0"'
            ),
            encoding="utf-8",
        )
        skill_file = package / "skills/wordpress-mcp-workflow/SKILL.md"
        skill_file.write_text(
            skill_file.read_text(encoding="utf-8") + "\n<!-- 虛構第二候選 -->\n",
            encoding="utf-8",
        )
        return manifest

    def test_full_lifecycle(self) -> None:
        """完整驗證安裝、重跑、更新、回復與隔離移除。"""

        available = self.success(self.command("status"))
        self.assertEqual(available["result"], "available")
        installed = self.success(self.command("install"))
        self.assertEqual(installed["result"], "installed")
        for skill in SKILLS:
            self.assertTrue((self.client_root / skill / "SKILL.md").is_file())
        self.assertEqual(self.success(self.command("install"))["result"], "noop")

        version_two = self.make_version_two()
        self.assertEqual(
            self.success(self.command("status", version_two))["result"],
            "installed_update_available",
        )
        self.assertEqual(self.success(self.command("update", version_two))["result"], "updated")
        self.assertIn(
            "虛構第二候選",
            (self.client_root / "wordpress-mcp-workflow/SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(self.success(self.command("rollback", version_two))["result"], "rolled_back")
        removed = self.success(self.command("remove"))
        self.assertEqual(removed["result"], "removed_to_quarantine")
        for skill in SKILLS:
            self.assertFalse((self.client_root / skill).exists())
            self.assertTrue(Path(removed["quarantine"]).joinpath(skill).is_dir())

    def test_unknown_and_modified_content_is_preserved(self) -> None:
        """同名未知內容與安裝後人工修改都不能被覆寫或移除。"""

        foreign = self.client_root / SKILLS[0]
        foreign.mkdir(parents=True)
        marker = foreign / "KEEP.txt"
        marker.write_text("虛構外部內容\n", encoding="utf-8")
        self.assertEqual(self.command("install").returncode, 2)
        self.assertEqual(marker.read_text(encoding="utf-8"), "虛構外部內容\n")

        shutil.rmtree(self.client_root)
        self.success(self.command("install"))
        installed = self.client_root / SKILLS[0] / "SKILL.md"
        installed.write_text(installed.read_text(encoding="utf-8") + "\n虛構人工修改\n", encoding="utf-8")
        self.assertEqual(self.command("remove").returncode, 2)
        self.assertIn("虛構人工修改", installed.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
