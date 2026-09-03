#!/usr/bin/env python3
"""以暫存 repository 與虛構內容驗證技能安裝生命週期。"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
MANAGER = PACKAGE_ROOT / "scripts" / "manage_install.py"
SKILL_NAMES = (
    "google-apps-script-project-development",
    "google-apps-script-teaching",
    "google-apps-script-debugging",
    "google-docs-layout",
)
MANAGED_NAMES = ("google-workflow-router", *SKILL_NAMES, "learner-facing-terminology.md")


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """執行測試命令並保留標準輸出與錯誤。"""

    return subprocess.run(command, cwd=cwd, capture_output=True, text=True)


def write_text(file_path: Path, content: str) -> None:
    """建立測試檔案及其父目錄。"""

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


def sha256_file(file_path: Path) -> str:
    """計算測試 LICENSE 的 SHA-256。"""

    return hashlib.sha256(file_path.read_bytes()).hexdigest()


class InstallLifecycleTest(unittest.TestCase):
    """驗證正常、重跑、衝突、更新、回復與移除。"""

    def setUp(self) -> None:
        """為每個案例建立完全隔離的虛構來源。"""

        self.temporary = tempfile.TemporaryDirectory(prefix="google-automation-test-")
        self.root = Path(self.temporary.name)
        self.learn_v1 = self.make_learn_gas("v1")
        self.learn_v2 = self.make_learn_gas("v2")
        self.package_v1 = self.make_package("0.1.0", self.learn_v1, "路由版本一")
        self.package_v2 = self.make_package("0.2.0", self.learn_v2, "路由版本二")
        self.client_root = self.root / "workspace" / ".agents" / "skills"
        self.state_root = self.root / "state"

    def tearDown(self) -> None:
        """移除只存在於系統暫存目錄的測試資料。"""

        self.temporary.cleanup()

    def git(self, repository: Path, *arguments: str) -> str:
        """執行測試 repository 的 Git 命令。"""

        environment = os.environ.copy()
        environment.update(
            {
                "GIT_AUTHOR_NAME": "Fixture Builder",
                "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                "GIT_COMMITTER_NAME": "Fixture Builder",
                "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
            }
        )
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        return result.stdout.strip()

    def make_learn_gas(self, version: str) -> dict[str, Path | str]:
        """建立只有必要公開結構的虛構 Learn-GAS Git repository。"""

        repository = self.root / f"learn-{version}"
        repository.mkdir()
        write_text(repository / "LICENSE", f"MIT fixture license {version}\n")
        write_text(
            repository / "skills" / "learner-facing-terminology.md",
            f"# 虛構共用術語 {version}\n",
        )
        for skill_name in SKILL_NAMES:
            write_text(
                repository / "skills" / skill_name / "SKILL.md",
                "---\n"
                f"name: {skill_name}\n"
                f"description: 虛構的 {skill_name} {version} 測試技能。\n"
                "---\n\n"
                f"# {skill_name} {version}\n",
            )
        self.git(repository, "init", "-q")
        self.git(repository, "add", ".")
        self.git(repository, "commit", "-q", "-m", f"fixture {version}")
        return {
            "root": repository,
            "ref": self.git(repository, "rev-parse", "HEAD"),
            "tree": self.git(repository, "rev-parse", "HEAD^{tree}"),
            "license_sha256": sha256_file(repository / "LICENSE"),
        }

    def make_package(
        self,
        version: str,
        learn: dict[str, Path | str],
        router_text: str,
    ) -> Path:
        """建立安裝管理器可讀的虛構候選 manifest 與路由技能。"""

        package = self.root / f"package-{version}"
        write_text(
            package / "skills" / "google-workflow-router" / "SKILL.md",
            "---\n"
            "name: google-workflow-router\n"
            "description: 只供安裝生命週期測試的虛構路由技能。\n"
            "---\n\n"
            f"# {router_text}\n",
        )
        manifest = f'''schema_version = 1
manifest_type = "google-automation-install"
status = "ready_for_external_acceptance"
installable = true
support_level = "installable_candidate_not_formally_supported"

[integration.learn_gas]
ref = "{learn['ref']}"
tree = "{learn['tree']}"
license_sha256 = "{learn['license_sha256']}"

[installation]
candidate_version = "{version}"
managed_entries = [
  "google-workflow-router",
  "google-apps-script-project-development",
  "google-apps-script-teaching",
  "google-apps-script-debugging",
  "google-docs-layout",
  "learner-facing-terminology.md",
]

[managed_sources]
router_path = "skills/google-workflow-router"
learn_gas_skills = [
  "google-apps-script-project-development",
  "google-apps-script-teaching",
  "google-apps-script-debugging",
  "google-docs-layout",
]
learn_gas_shared_files = ["learner-facing-terminology.md"]

[registrations.agents_workspace]
clients = ["codex", "google-antigravity"]
scope = "workspace"
path = "<workspace>/.agents/skills"
'''
        write_text(package / "install.manifest.toml", manifest)
        return package

    def manager(
        self,
        command: str,
        *,
        package: Path | None = None,
        learn: dict[str, Path | str] | None = None,
        client_root: Path | None = None,
        state_root: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """呼叫公開命令列介面，避免只測試內部函式。"""

        target_client = client_root or self.client_root
        target_state = state_root or self.state_root
        arguments = [
            "python3",
            str(MANAGER),
            command,
            "--registration",
            "agents_workspace",
            "--client-root",
            str(target_client),
            "--state-root",
            str(target_state),
        ]
        if command in {"install", "update"}:
            assert package is not None and learn is not None
            arguments.extend(
                [
                    "--manifest",
                    str(package / "install.manifest.toml"),
                    "--learn-gas-source",
                    str(learn["root"]),
                ]
            )
        return run(arguments)

    def assert_success(self, result: subprocess.CompletedProcess[str]) -> dict[str, object]:
        """要求命令成功並解析 JSON 結果。"""

        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_full_lifecycle(self) -> None:
        """正常安裝、重跑、更新、回復、移除與重新安裝都可重現。"""

        installed = self.assert_success(
            self.manager("install", package=self.package_v1, learn=self.learn_v1)
        )
        self.assertEqual(installed["result"], "installed")
        for name in MANAGED_NAMES:
            self.assertTrue((self.client_root / name).exists(), name)

        repeated = self.assert_success(
            self.manager("install", package=self.package_v1, learn=self.learn_v1)
        )
        self.assertEqual(repeated["result"], "noop")

        wrong_command = self.manager("install", package=self.package_v2, learn=self.learn_v2)
        self.assertEqual(wrong_command.returncode, 2)
        router = self.client_root / "google-workflow-router" / "SKILL.md"
        self.assertIn("路由版本一", router.read_text(encoding="utf-8"))

        updated = self.assert_success(
            self.manager("update", package=self.package_v2, learn=self.learn_v2)
        )
        self.assertEqual(updated["result"], "updated")
        self.assertIn("路由版本二", router.read_text(encoding="utf-8"))

        rolled_back = self.assert_success(self.manager("rollback"))
        self.assertEqual(rolled_back["result"], "rolled_back")
        self.assertIn("路由版本一", router.read_text(encoding="utf-8"))

        removed = self.assert_success(self.manager("remove"))
        self.assertEqual(removed["result"], "removed_to_quarantine")
        self.assertTrue(Path(str(removed["quarantine"])).is_dir())
        for name in MANAGED_NAMES:
            self.assertFalse((self.client_root / name).exists(), name)

        reinstalled = self.assert_success(
            self.manager("install", package=self.package_v1, learn=self.learn_v1)
        )
        self.assertEqual(reinstalled["result"], "reinstalled")
        status = self.assert_success(self.manager("status"))
        self.assertEqual(status["verification"], "hashes_match")

    def test_unknown_partial_content_stops_without_changes(self) -> None:
        """未知實體目錄不會被接管或覆寫。"""

        foreign_root = self.root / "foreign" / ".agents" / "skills"
        marker = foreign_root / "google-workflow-router" / "KEEP.txt"
        write_text(marker, "保留這個虛構內容\n")
        result = self.manager(
            "install",
            package=self.package_v1,
            learn=self.learn_v1,
            client_root=foreign_root,
            state_root=self.root / "foreign-state",
        )
        self.assertEqual(result.returncode, 2)
        self.assertTrue(marker.is_file())
        self.assertEqual(marker.read_text(encoding="utf-8"), "保留這個虛構內容\n")
        self.assertFalse((foreign_root / SKILL_NAMES[0]).exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "此平台不支援 symlink 測試")
    def test_unknown_symlink_stops(self) -> None:
        """未知 symlink 會停止，不追蹤或解除連結。"""

        foreign_root = self.root / "symlink" / ".agents" / "skills"
        foreign_target = self.root / "foreign-target"
        write_text(foreign_target / "KEEP.txt", "虛構外部目標\n")
        foreign_root.mkdir(parents=True)
        link = foreign_root / "google-workflow-router"
        link.symlink_to(foreign_target, target_is_directory=True)
        result = self.manager(
            "install",
            package=self.package_v1,
            learn=self.learn_v1,
            client_root=foreign_root,
            state_root=self.root / "symlink-state",
        )
        self.assertEqual(result.returncode, 2)
        self.assertTrue(link.is_symlink())
        self.assertTrue((foreign_target / "KEEP.txt").is_file())

    def test_modified_managed_entry_blocks_update_and_remove(self) -> None:
        """安裝後的人工修改會保留，更新與移除都停止。"""

        self.assert_success(self.manager("install", package=self.package_v1, learn=self.learn_v1))
        router = self.client_root / "google-workflow-router" / "SKILL.md"
        router.write_text(router.read_text(encoding="utf-8") + "\n人工保留\n", encoding="utf-8")

        update_result = self.manager("update", package=self.package_v2, learn=self.learn_v2)
        self.assertEqual(update_result.returncode, 2)
        self.assertIn("人工保留", router.read_text(encoding="utf-8"))

        remove_result = self.manager("remove")
        self.assertEqual(remove_result.returncode, 2)
        self.assertTrue(router.is_file())

    def test_wrong_dependency_commit_stops_before_install(self) -> None:
        """manifest 與 Learn-GAS commit 不同時不建立任何入口。"""

        result = self.manager("install", package=self.package_v1, learn=self.learn_v2)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.client_root.exists())

    def test_state_inside_skill_root_is_rejected(self) -> None:
        """狀態與備份不得放進 Agent 技能掃描目錄。"""

        result = self.manager(
            "install",
            package=self.package_v1,
            learn=self.learn_v1,
            state_root=self.client_root / ".state",
        )
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.client_root.exists())


if __name__ == "__main__":
    unittest.main()
