#!/usr/bin/env python3
"""以暫存 repository 與虛構內容驗證 agent-inventory 技能入口的安裝生命週期。"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
MANAGER = PACKAGE_ROOT / "scripts" / "manage_install.py"
REAL_MANIFEST = PACKAGE_ROOT / "install.manifest.toml"
SKILL_NAMES = (
    "inventory",
    "inventory-setup",
    "inventory-scan",
    "inventory-summarize",
    "inventory-flow",
    "inventory-serve",
)


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """執行測試命令並保留標準輸出與錯誤。"""

    return subprocess.run(command, cwd=cwd, capture_output=True, text=True)


def git(repository: Path, *arguments: str) -> str:
    """在測試 repository 執行 Git 並回傳輸出。"""

    result = run(["git", "-C", str(repository), *arguments])
    if result.returncode != 0:
        raise AssertionError(f"git {' '.join(arguments)} 失敗：{result.stderr}")
    return result.stdout.strip()


class InstallLifecycleTest(unittest.TestCase):
    """驗證正常、重跑、衝突、竄改、更新、回復與移除。"""

    def setUp(self) -> None:
        """為每個案例建立完全隔離的虛構上游與目標。"""

        self.temporary = tempfile.TemporaryDirectory(prefix="agent-inventory-test-")
        self.root = Path(self.temporary.name)
        self.upstream_v1 = self.make_upstream("v1")
        self.upstream_v2 = self.make_upstream("v2")
        self.manifest_v1 = self.make_manifest("0.1.0", self.upstream_v1)
        self.manifest_v2 = self.make_manifest("0.2.0", self.upstream_v2)
        self.client_root = self.root / "home" / ".claude" / "skills"
        self.client_root.mkdir(parents=True)
        self.state_root = self.root / "state"

    def tearDown(self) -> None:
        """清除暫存目錄。"""

        self.temporary.cleanup()

    def make_upstream(self, marker: str) -> Path:
        """建立含六個虛構技能與 LICENSE 的暫存 Git repository。"""

        repository = self.root / f"upstream-{marker}"
        skills = repository / ".agents" / "skills"
        skills.mkdir(parents=True)
        for name in SKILL_NAMES:
            skill_dir = skills / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: 虛構測試技能 {name}（{marker}）。\n---\n\n# {name}\n\n虛構內容 {marker}。\n",
                encoding="utf-8",
            )
        (repository / "LICENSE").write_text(f"MIT License\n\n虛構授權文字 {marker}\n", encoding="utf-8")
        run(["git", "init", "--quiet", str(repository)])
        git(repository, "config", "user.email", "test@example.invalid")
        git(repository, "config", "user.name", "Test")
        git(repository, "add", "--all")
        git(repository, "commit", "--quiet", "--message", f"虛構上游 {marker}")
        return repository

    def make_manifest(self, version: str, upstream: Path) -> Path:
        """以真實 manifest 為底，換成虛構上游的雜湊與版本。"""

        text = REAL_MANIFEST.read_text(encoding="utf-8")
        license_hash = hashlib.sha256((upstream / "LICENSE").read_bytes()).hexdigest()
        replacements = {
            'ref = "c162b0adce4d1519b60f76de15bc00df85d611ce"': f'ref = "{git(upstream, "rev-parse", "HEAD")}"',
            'tree = "9ccdd73635bb74b95e6d2a111c994758602f5a23"': f'tree = "{git(upstream, "rev-parse", "HEAD^{tree}")}"',
            'license_sha256 = "8e30b10020d068a10bf4376e97df27bf34c9a52b01de5c3d0f6e26f594353dac"': f'license_sha256 = "{license_hash}"',
            'candidate_version = "0.1.0"': f'candidate_version = "{version}"',
        }
        for old, new in replacements.items():
            self.assertIn(old, text, f"manifest 缺少可替換的欄位：{old[:40]}")
            text = text.replace(old, new, 1)
        manifest_path = self.root / f"manifest-{version}.toml"
        manifest_path.write_text(text, encoding="utf-8")
        return manifest_path

    def manage(self, command: str, *extra: str) -> subprocess.CompletedProcess[str]:
        """以固定的註冊目標執行管理器。"""

        return run([
            "python3", str(MANAGER), command,
            "--registration", "claude_user",
            "--client-root", str(self.client_root),
            "--state-root", str(self.state_root),
            *extra,
        ])

    def install(self, manifest: Path, upstream: Path) -> subprocess.CompletedProcess[str]:
        """執行安裝命令。"""

        return self.manage("install", "--manifest", str(manifest), "--inventory-source", str(upstream))

    def payload(self, result: subprocess.CompletedProcess[str]) -> dict:
        """解析管理器的 JSON 輸出。"""

        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_status_before_install_reports_not_installed(self) -> None:
        """尚未安裝時只回報狀態，不建立任何檔案。"""

        payload = self.payload(self.manage("status"))
        self.assertEqual(payload["result"], "not_installed")
        self.assertEqual(list(self.client_root.iterdir()), [])

    def test_install_registers_five_skills_and_repeat_is_noop(self) -> None:
        """安裝六個技能後重跑不重複寫入。"""

        payload = self.payload(self.install(self.manifest_v1, self.upstream_v1))
        self.assertEqual(payload["result"], "installed")
        self.assertEqual(sorted(payload["entries"]), sorted(SKILL_NAMES))
        for name in SKILL_NAMES:
            self.assertTrue((self.client_root / name / "SKILL.md").is_file(), name)
        self.assertFalse((self.client_root / name).is_symlink())

        repeat = self.payload(self.install(self.manifest_v1, self.upstream_v1))
        self.assertEqual(repeat["result"], "noop")

    def test_existing_unmanaged_entry_stops_without_overwrite(self) -> None:
        """目標已有同名且非本套件管理的項目時停止且不覆寫。"""

        intruder = self.client_root / "inventory"
        intruder.mkdir()
        (intruder / "SKILL.md").write_text("使用者自建技能，不可被覆寫。\n", encoding="utf-8")

        result = self.install(self.manifest_v1, self.upstream_v1)
        self.assertEqual(result.returncode, 2)
        self.assertIn("使用者自建技能", (intruder / "SKILL.md").read_text(encoding="utf-8"))

    def test_modified_upstream_worktree_is_rejected(self) -> None:
        """上游 clone 有未提交修改時拒絕作為安裝來源。"""

        (self.upstream_v1 / ".agents" / "skills" / "inventory" / "SKILL.md").write_text("被改過\n", encoding="utf-8")
        result = self.install(self.manifest_v1, self.upstream_v1)
        self.assertEqual(result.returncode, 2)
        self.assertIn("修改", result.stderr)

    def test_wrong_commit_is_rejected(self) -> None:
        """上游 commit 與 manifest 不符時停止。"""

        result = self.install(self.manifest_v1, self.upstream_v2)
        self.assertEqual(result.returncode, 2)
        self.assertIn("commit 不符", result.stderr)

    def test_update_then_rollback_restores_previous_content(self) -> None:
        """更新換成新版內容，回復後恢復舊版。"""

        self.payload(self.install(self.manifest_v1, self.upstream_v1))
        target = self.client_root / "inventory" / "SKILL.md"
        self.assertIn("v1", target.read_text(encoding="utf-8"))

        updated = self.payload(
            self.manage("update", "--manifest", str(self.manifest_v2), "--inventory-source", str(self.upstream_v2))
        )
        self.assertEqual(updated["result"], "updated")
        self.assertIn("v2", target.read_text(encoding="utf-8"))

        rolled = self.payload(self.manage("rollback"))
        self.assertEqual(rolled["result"], "rolled_back")
        self.assertIn("v1", target.read_text(encoding="utf-8"))

    def test_remove_moves_entries_to_recoverable_quarantine(self) -> None:
        """移除只搬走受管理入口，並保留可回復副本。"""

        self.payload(self.install(self.manifest_v1, self.upstream_v1))
        keep = self.client_root / "使用者自己的技能"
        keep.mkdir()
        (keep / "SKILL.md").write_text("不可被移除\n", encoding="utf-8")

        payload = self.payload(self.manage("remove"))
        self.assertEqual(payload["result"], "removed_to_quarantine")
        quarantine = Path(payload["quarantine"])
        self.assertTrue(quarantine.is_dir())
        for name in SKILL_NAMES:
            self.assertFalse((self.client_root / name).exists(), name)
            self.assertTrue((quarantine / "entries" / name / "SKILL.md").is_file(), name)
        self.assertTrue((keep / "SKILL.md").is_file())

    def test_state_root_inside_client_root_is_rejected(self) -> None:
        """狀態目錄不得位於技能掃描範圍內。"""

        result = run([
            "python3", str(MANAGER), "install",
            "--registration", "claude_user",
            "--client-root", str(self.client_root),
            "--state-root", str(self.client_root / "state"),
            "--manifest", str(self.manifest_v1),
            "--inventory-source", str(self.upstream_v1),
        ])
        self.assertEqual(result.returncode, 2)
        self.assertIn("狀態目錄", result.stderr)

    def test_registration_path_shape_is_checked(self) -> None:
        """技能根目錄形狀與註冊 ID 不符時停止。"""

        wrong_root = self.root / "home" / "somewhere"
        wrong_root.mkdir(parents=True)
        result = run([
            "python3", str(MANAGER), "install",
            "--registration", "claude_user",
            "--client-root", str(wrong_root),
            "--state-root", str(self.state_root),
            "--manifest", str(self.manifest_v1),
            "--inventory-source", str(self.upstream_v1),
        ])
        self.assertEqual(result.returncode, 2)
        self.assertIn("技能根目錄", result.stderr)


if __name__ == "__main__":
    unittest.main()
