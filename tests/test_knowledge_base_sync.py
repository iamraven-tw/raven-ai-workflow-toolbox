#!/usr/bin/env python3
"""測試 AI 知識庫同步工具的狀態、衝突、排除與 symlink 驗證。"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools/knowledge_base_sync.py"


class KnowledgeBaseSyncTests(unittest.TestCase):
    """使用完全隔離的臨時目錄驗證同步行為。"""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="knowledge-sync-test-")
        self.root = Path(self.temporary.name)
        self.canonical = self.root / "canonical"
        self.mirror = self.root / "mirror"
        self.local = self.root / "local"
        self.runtime = self.root / "runtime"
        for directory in (self.canonical, self.mirror, self.local, self.runtime):
            directory.mkdir()
        self.write_shared(self.canonical, "初始內容")
        self.write_shared(self.mirror, "初始內容")
        self.manifest = self.local / "sync-manifest.toml"
        self.write_manifest(runtime_enabled=False)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_shared(self, root: Path, content: str) -> None:
        """建立最小通用技能套件。"""

        (root / "skills/sample").mkdir(parents=True, exist_ok=True)
        (root / "README.md").write_text(content + "\n", encoding="utf-8")
        (root / "skills/sample/SKILL.md").write_text(
            "---\nname: sample\ndescription: 測試\n---\n",
            encoding="utf-8",
        )

    def write_manifest(self, runtime_enabled: bool) -> None:
        """建立只供臨時測試使用的 manifest。"""

        runtime_block = textwrap.dedent(
            f"""
            [runtime]
            enabled = {str(runtime_enabled).lower()}
            root = "{self.runtime}"
            skills_dir = ".local/runtime-skills"
            client_links = [".agents/skills"]
            """
        )
        self.manifest.write_text(
            textwrap.dedent(
                f"""
                schema_version = 1

                [package]
                id = "test-package"
                canonical_root = "{self.canonical}"
                mirror_root = "{self.mirror}"
                state_file = "{self.local / 'sync-state.json'}"
                backup_root = "{self.local / 'backups'}"
                exclude_roots = [".git", ".local", "sources"]
                exclude_names = ["__pycache__", ".DS_Store"]
                exclude_suffixes = [".pyc"]
                shared_skills = ["sample"]

                {runtime_block}
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

    def run_cli(self, command: str, *arguments: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        """執行同步工具並檢查預期結束碼。"""

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--manifest",
                str(self.manifest),
                "--json",
                command,
                *arguments,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, expected, result.stderr or result.stdout)
        return result

    def status_json(self) -> dict:
        """取得 JSON 狀態。"""

        return json.loads(self.run_cli("status").stdout)

    def test_identical_without_state_is_read_only(self) -> None:
        """相同內容第一次檢查不應自動寫 state。"""

        status = self.status_json()
        self.assertEqual(status["status"], "synced-unrecorded")
        self.assertEqual(status["difference_count"], 0)
        self.assertFalse((self.local / "sync-state.json").exists())

    def test_detects_canonical_ahead(self) -> None:
        """記錄基準後，只改通用核心應判為 canonical-ahead。"""

        self.run_cli("record")
        (self.canonical / "README.md").write_text("核心更新\n", encoding="utf-8")
        status = self.status_json()
        self.assertEqual(status["status"], "canonical-ahead")
        self.assertEqual(status["differences"], ["README.md"])

    def test_detects_mirror_ahead(self) -> None:
        """記錄基準後，只改 Toolbox 副本應判為 mirror-ahead。"""

        self.run_cli("record")
        (self.mirror / "README.md").write_text("副本更新\n", encoding="utf-8")
        status = self.status_json()
        self.assertEqual(status["status"], "mirror-ahead")

    def test_detects_two_sided_conflict(self) -> None:
        """兩邊各自修改時不得猜測正確來源。"""

        self.run_cli("record")
        (self.canonical / "README.md").write_text("核心更新\n", encoding="utf-8")
        (self.mirror / "README.md").write_text("副本更新\n", encoding="utf-8")
        status = self.status_json()
        self.assertEqual(status["status"], "conflict")

    def test_dry_run_and_apply_with_backup(self) -> None:
        """預覽不寫檔，明確 apply 後同步並保留備份。"""

        self.run_cli("record")
        (self.canonical / "README.md").write_text("核心更新\n", encoding="utf-8")
        (self.canonical / "NEW.md").write_text("新增\n", encoding="utf-8")
        (self.mirror / "OLD.md").write_text("待移除\n", encoding="utf-8")

        dry_run = json.loads(
            self.run_cli("sync", "--from", "canonical").stdout
        )
        self.assertFalse(dry_run["applied"])
        self.assertEqual((self.mirror / "README.md").read_text(encoding="utf-8"), "初始內容\n")
        self.assertTrue((self.mirror / "OLD.md").exists())

        applied = json.loads(
            self.run_cli("sync", "--from", "canonical", "--apply").stdout
        )
        self.assertTrue(applied["applied"])
        self.assertEqual((self.mirror / "README.md").read_text(encoding="utf-8"), "核心更新\n")
        self.assertTrue((self.mirror / "NEW.md").exists())
        self.assertFalse((self.mirror / "OLD.md").exists())
        self.assertTrue(Path(applied["backup_dir"]).is_dir())
        self.assertEqual(self.status_json()["status"], "synced")

    def test_private_root_is_excluded(self) -> None:
        """實際資料根目錄不同不應被當成公開套件差異。"""

        (self.canonical / "sources").mkdir()
        (self.mirror / "sources").mkdir()
        (self.canonical / "sources/private.md").write_text("甲\n", encoding="utf-8")
        (self.mirror / "sources/private.md").write_text("乙\n", encoding="utf-8")
        self.assertEqual(self.status_json()["difference_count"], 0)

    def test_runtime_symlinks(self) -> None:
        """啟用 runtime 後必須同時驗證技能與用戶端入口。"""

        self.write_manifest(runtime_enabled=True)
        runtime_skills = self.runtime / ".local/runtime-skills"
        runtime_skills.mkdir(parents=True)
        (runtime_skills / "sample").symlink_to(
            self.canonical / "skills/sample",
            target_is_directory=True,
        )
        (self.runtime / ".agents").mkdir()
        (self.runtime / ".agents/skills").symlink_to(
            runtime_skills,
            target_is_directory=True,
        )
        self.run_cli("verify")

        (self.runtime / ".agents/skills").unlink()
        self.run_cli("verify", expected=2)


if __name__ == "__main__":
    unittest.main()
