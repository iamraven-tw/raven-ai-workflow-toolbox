#!/usr/bin/env python3
"""以完全虛構的暫存資料驗證安裝與工作區生命週期。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
MANAGER = PACKAGE_ROOT / "scripts" / "manage_install.py"
SKILL_NAMES = (
    "my-real-second-brain-setup",
    "solopreneur-profile",
    "book-notes",
    "knowledge-source-retrieval",
    "socratic-dialogue",
)

MANAGER_SPEC = importlib.util.spec_from_file_location("ai_kb_manage_install", MANAGER)
if MANAGER_SPEC is None or MANAGER_SPEC.loader is None:
    raise RuntimeError("無法載入安裝管理器進行交易失敗測試")
MANAGER_MODULE = importlib.util.module_from_spec(MANAGER_SPEC)
MANAGER_SPEC.loader.exec_module(MANAGER_MODULE)


def write_text(file_path: Path, content: str) -> None:
    """建立虛構測試檔案與父目錄。"""

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


def run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """執行公開命令列介面並保留輸出。"""

    return subprocess.run(arguments, capture_output=True, text=True)


class InstallLifecycleTest(unittest.TestCase):
    """驗證正常、重跑、衝突、更新、回復、移除與初始化。"""

    def setUp(self) -> None:
        """為每個案例建立完全隔離且不含真實資料的環境。"""

        self.temporary = tempfile.TemporaryDirectory(prefix="ai-knowledge-base-test-")
        self.root = Path(self.temporary.name)
        self.package_v1 = self.make_package("0.1.0", "虛構版本一")
        self.package_v2 = self.make_package("0.2.0", "虛構版本二")
        self.client_root = self.root / "workspace" / ".agents" / "skills"
        self.state_root = self.root / "state"

    def tearDown(self) -> None:
        """移除系統暫存目錄中的測試資料。"""

        self.temporary.cleanup()

    def make_package(self, version: str, marker: str) -> Path:
        """建立具有五個虛構技能與安全模板的候選技能包。"""

        package = self.root / f"package-{version}"
        for skill_name in SKILL_NAMES:
            write_text(
                package / "skills" / skill_name / "SKILL.md",
                "---\n"
                f"name: {skill_name}\n"
                f"description: 僅供生命週期測試的 {skill_name}。\n"
                "---\n\n"
                f"# {marker}\n",
            )
        write_text(package / "template" / "AGENTS.md", f"# {marker}的公開規則\n")
        write_text(
            package / "template" / "sources" / "strategy" / "solopreneur-profile.md",
            "---\nstatus: not_configured\n---\n",
        )
        write_text(
            package
            / "template"
            / "sources"
            / "strategy"
            / "social-media-strategy-and-insights.md",
            "---\nstatus: not_configured\n---\n",
        )
        skills_toml = "\n".join(
            "[[skills]]\n"
            f'id = "{skill_name}"\n'
            f'source_path = "skills/{skill_name}"\n'
            "required = true\n"
            for skill_name in SKILL_NAMES
        )
        managed = ",\n  ".join(f'"{name}"' for name in SKILL_NAMES)
        manifest = f'''schema_version = 1
manifest_type = "my-real-second-brain-install"
status = "ready_for_external_acceptance"
installable = true
support_level = "installable_candidate_not_formally_supported"

[workspace]
template_path = "template"

[installation]
candidate_version = "{version}"
managed_entries = [
  {managed},
]

[registrations.agents_workspace]
clients = ["codex", "google-antigravity-desktop"]
scope = "workspace"
path = "<workspace>/.agents/skills"

{skills_toml}
'''
        write_text(package / "install.manifest.toml", manifest)
        return package

    def manager(
        self,
        command: str,
        *,
        package: Path | None = None,
        client_root: Path | None = None,
        state_root: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """呼叫技能安裝命令，確保測試涵蓋公開介面。"""

        package_root = package or self.package_v1
        arguments = [
            "python3",
            str(MANAGER),
            command,
            "--manifest",
            str(package_root / "install.manifest.toml"),
            "--registration",
            "agents_workspace",
            "--client-root",
            str(client_root or self.client_root),
            "--state-root",
            str(state_root or self.state_root),
        ]
        return run(arguments)

    def workspace_manager(
        self,
        command: str,
        workspace_root: Path,
        *,
        package: Path | None = None,
        state_root: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """呼叫工作區預覽或初始化命令。"""

        package_root = package or self.package_v1
        arguments = [
            "python3",
            str(MANAGER),
            command,
            "--manifest",
            str(package_root / "install.manifest.toml"),
            "--workspace-root",
            str(workspace_root),
        ]
        if command == "init-workspace":
            arguments.extend(["--state-root", str(state_root or self.state_root)])
        return run(arguments)

    def manager_arguments(self, package: Path | None = None) -> argparse.Namespace:
        """建立可直接呼叫管理器函式的虛構參數。"""

        package_root = package or self.package_v1
        return argparse.Namespace(
            manifest=str(package_root / "install.manifest.toml"),
            registration="agents_workspace",
            client_root=str(self.client_root),
            state_root=str(self.state_root),
        )

    def assert_success(self, result: subprocess.CompletedProcess[str]) -> dict[str, object]:
        """要求命令成功並解析 JSON。"""

        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_full_skill_lifecycle(self) -> None:
        """完整驗證安裝、重跑、版本衝突、更新、回復與移除。"""

        installed = self.assert_success(self.manager("install"))
        self.assertEqual(installed["result"], "installed")
        for name in SKILL_NAMES:
            self.assertTrue((self.client_root / name / "SKILL.md").is_file())

        repeated = self.assert_success(self.manager("install"))
        self.assertEqual(repeated["result"], "noop")

        wrong_command = self.manager("install", package=self.package_v2)
        self.assertEqual(wrong_command.returncode, 2)
        marker = self.client_root / SKILL_NAMES[0] / "SKILL.md"
        self.assertIn("虛構版本一", marker.read_text(encoding="utf-8"))

        updated = self.assert_success(self.manager("update", package=self.package_v2))
        self.assertEqual(updated["result"], "updated")
        self.assertIn("虛構版本二", marker.read_text(encoding="utf-8"))

        rolled_back = self.assert_success(self.manager("rollback", package=self.package_v2))
        self.assertEqual(rolled_back["result"], "rolled_back")
        self.assertIn("虛構版本一", marker.read_text(encoding="utf-8"))

        removed = self.assert_success(self.manager("remove"))
        self.assertEqual(removed["result"], "removed_to_quarantine")
        self.assertTrue(Path(str(removed["quarantine"])).is_dir())
        for name in SKILL_NAMES:
            self.assertFalse((self.client_root / name).exists())

        repeated_remove = self.assert_success(self.manager("remove"))
        self.assertEqual(repeated_remove["result"], "noop")

        reinstalled = self.assert_success(self.manager("install"))
        self.assertEqual(reinstalled["result"], "reinstalled")
        status = self.assert_success(self.manager("status"))
        self.assertEqual(status["verification"], "hashes_match")

    def test_identical_unmanaged_install_is_adopted(self) -> None:
        """完全相同的既有技能可建立狀態，不會重寫內容。"""

        for name in SKILL_NAMES:
            source = self.package_v1 / "skills" / name
            target = self.client_root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target)
        before = (self.client_root / SKILL_NAMES[0] / "SKILL.md").stat().st_mtime_ns
        adopted = self.assert_success(self.manager("install"))
        after = (self.client_root / SKILL_NAMES[0] / "SKILL.md").stat().st_mtime_ns
        self.assertEqual(adopted["result"], "adopted_identical")
        self.assertEqual(before, after)

    def test_unknown_partial_content_stops_without_changes(self) -> None:
        """未知或不完整的同名內容不會被接管。"""

        foreign_root = self.root / "foreign" / ".agents" / "skills"
        marker = foreign_root / SKILL_NAMES[0] / "KEEP.txt"
        write_text(marker, "必須保留的虛構內容\n")
        result = self.manager(
            "install",
            client_root=foreign_root,
            state_root=self.root / "foreign-state",
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(marker.read_text(encoding="utf-8"), "必須保留的虛構內容\n")
        self.assertFalse((foreign_root / SKILL_NAMES[1]).exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "此平台不支援 symlink 測試")
    def test_unknown_symlink_stops(self) -> None:
        """未知 symlink 不會被跟隨或解除。"""

        foreign_root = self.root / "symlink" / ".agents" / "skills"
        foreign_target = self.root / "foreign-target"
        write_text(foreign_target / "KEEP.txt", "虛構外部目標\n")
        foreign_root.mkdir(parents=True)
        link = foreign_root / SKILL_NAMES[0]
        try:
            link.symlink_to(foreign_target, target_is_directory=True)
        except OSError as error:
            # 只略過建立測試連結的權限缺口，其他錯誤仍須失敗。
            if os.name == "nt" and getattr(error, "winerror", None) == 1314:
                self.skipTest("Windows 未授予建立 symlink 權限；連結防護須在具權限環境補驗")
            raise
        result = self.manager(
            "install",
            client_root=foreign_root,
            state_root=self.root / "symlink-state",
        )
        self.assertEqual(result.returncode, 2)
        self.assertTrue(link.is_symlink())
        self.assertTrue((foreign_target / "KEEP.txt").is_file())

    def test_modified_managed_skill_blocks_update_and_remove(self) -> None:
        """安裝後人工修改的技能會保留，更新與移除都停止。"""

        self.assert_success(self.manager("install"))
        marker = self.client_root / SKILL_NAMES[0] / "SKILL.md"
        marker.write_text(marker.read_text(encoding="utf-8") + "\n人工內容\n", encoding="utf-8")

        update_result = self.manager("update", package=self.package_v2)
        self.assertEqual(update_result.returncode, 2)
        self.assertIn("人工內容", marker.read_text(encoding="utf-8"))

        remove_result = self.manager("remove")
        self.assertEqual(remove_result.returncode, 2)
        self.assertTrue(marker.is_file())

    def test_broken_update_source_stops_before_change(self) -> None:
        """更新來源不完整時，現有版本維持不變。"""

        self.assert_success(self.manager("install"))
        broken = self.package_v2 / "skills" / SKILL_NAMES[-1] / "SKILL.md"
        broken.unlink()
        result = self.manager("update", package=self.package_v2)
        self.assertEqual(result.returncode, 2)
        marker = self.client_root / SKILL_NAMES[0] / "SKILL.md"
        self.assertIn("虛構版本一", marker.read_text(encoding="utf-8"))

    def test_initial_state_write_failure_removes_new_skills(self) -> None:
        """首次安裝狀態寫入失敗時，五個新技能全部回復。"""

        with mock.patch.object(
            MANAGER_MODULE,
            "write_json_atomic",
            side_effect=OSError("虛構狀態寫入失敗"),
        ):
            with self.assertRaises(MANAGER_MODULE.InstallError):
                MANAGER_MODULE.install_or_update(self.manager_arguments(), update=False)
        for name in SKILL_NAMES:
            self.assertFalse((self.client_root / name).exists())

    def test_update_state_write_failure_restores_previous_version(self) -> None:
        """更新檔案完成但狀態失敗時，回到原本完整版本。"""

        self.assert_success(self.manager("install"))
        original_write = MANAGER_MODULE.write_json_atomic

        def fail_registration_state(file_path: Path, payload: dict[str, object]) -> None:
            """允許快照寫入，只讓作用中狀態寫入失敗。"""

            if file_path.name == "snapshot.json":
                original_write(file_path, payload)
                return
            raise OSError("虛構更新狀態失敗")

        with mock.patch.object(
            MANAGER_MODULE,
            "write_json_atomic",
            side_effect=fail_registration_state,
        ):
            with self.assertRaises(MANAGER_MODULE.InstallError):
                MANAGER_MODULE.install_or_update(
                    self.manager_arguments(self.package_v2),
                    update=True,
                )
        marker = self.client_root / SKILL_NAMES[0] / "SKILL.md"
        self.assertIn("虛構版本一", marker.read_text(encoding="utf-8"))
        self.assertEqual(self.assert_success(self.manager("status"))["version"], "0.1.0")

    def test_rollback_state_write_failure_restores_updated_version(self) -> None:
        """回復內容完成但狀態失敗時，重新放回更新後版本。"""

        self.assert_success(self.manager("install"))
        self.assert_success(self.manager("update", package=self.package_v2))
        with mock.patch.object(
            MANAGER_MODULE,
            "write_json_atomic",
            side_effect=OSError("虛構回復狀態失敗"),
        ):
            with self.assertRaises(MANAGER_MODULE.InstallError):
                MANAGER_MODULE.rollback(self.manager_arguments(self.package_v2))
        marker = self.client_root / SKILL_NAMES[0] / "SKILL.md"
        self.assertIn("虛構版本二", marker.read_text(encoding="utf-8"))
        status = self.assert_success(self.manager("status", package=self.package_v2))
        self.assertEqual(status["version"], "0.2.0")

    def test_remove_state_write_failure_restores_active_skills(self) -> None:
        """移入隔離區後狀態失敗時，所有技能回到原位置。"""

        self.assert_success(self.manager("install"))
        with mock.patch.object(
            MANAGER_MODULE,
            "write_json_atomic",
            side_effect=OSError("虛構移除狀態失敗"),
        ):
            with self.assertRaises(MANAGER_MODULE.InstallError):
                MANAGER_MODULE.remove(self.manager_arguments())
        for name in SKILL_NAMES:
            self.assertTrue((self.client_root / name / "SKILL.md").is_file())
        self.assertEqual(self.assert_success(self.manager("status"))["result"], "installed")

    def test_state_inside_skill_root_is_rejected(self) -> None:
        """狀態、快照與隔離區不能污染 Agent 掃描目錄。"""

        result = self.manager("install", state_root=self.client_root / ".state")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.client_root.exists())

    def test_all_declared_client_registrations_accept_only_official_suffixes(self) -> None:
        """六種 workspace／user 登錄都能安裝，錯誤路徑則安全停止。"""

        registrations = {
            "agents_workspace": self.root / "matrix-workspace" / ".agents" / "skills",
            "claude_workspace": self.root / "matrix-workspace" / ".claude" / "skills",
            "codex_user": self.root / "matrix-home-codex" / ".agents" / "skills",
            "claude_user": self.root / "matrix-home-claude" / ".claude" / "skills",
            "antigravity_desktop_user": (
                self.root / "matrix-home-desktop" / ".gemini" / "config" / "skills"
            ),
            "antigravity_cli_user": (
                self.root
                / "matrix-home-cli"
                / ".gemini"
                / "antigravity-cli"
                / "skills"
            ),
        }
        matrix_state = self.root / "matrix-state"
        for registration, client_root in registrations.items():
            with self.subTest(registration=registration):
                arguments = [
                    "python3",
                    str(MANAGER),
                    "install",
                    "--manifest",
                    str(PACKAGE_ROOT / "install.manifest.toml"),
                    "--registration",
                    registration,
                    "--client-root",
                    str(client_root),
                    "--state-root",
                    str(matrix_state),
                ]
                installed = self.assert_success(run(arguments))
                self.assertEqual(installed["managed_entries"], list(SKILL_NAMES))
                for name in SKILL_NAMES:
                    self.assertTrue((client_root / name / "SKILL.md").is_file())

        invalid = run(
            [
                "python3",
                str(MANAGER),
                "install",
                "--manifest",
                str(PACKAGE_ROOT / "install.manifest.toml"),
                "--registration",
                "codex_user",
                "--client-root",
                str(self.root / "wrong" / ".agents" / "not-skills"),
                "--state-root",
                str(self.root / "wrong-state"),
            ]
        )
        self.assertEqual(invalid.returncode, 2)
        self.assertFalse((self.root / "wrong" / ".agents" / "not-skills").exists())

    def test_workspace_preview_init_repeat_and_preserve(self) -> None:
        """模板只補缺少項目，重跑無害，既有檔案永遠保留。"""

        workspace = self.root / "user-workspace"
        custom_agents = "# 使用者自己的虛構規則\n"
        write_text(workspace / "AGENTS.md", custom_agents)

        preview = self.assert_success(self.workspace_manager("workspace-status", workspace))
        self.assertEqual(preview["result"], "preview")
        self.assertIn("AGENTS.md", preview["preserved_existing"])
        self.assertIn("sources/strategy/solopreneur-profile.md", preview["create_files"])
        self.assertIn(
            "sources/strategy/social-media-strategy-and-insights.md",
            preview["create_files"],
        )
        self.assertEqual((workspace / "AGENTS.md").read_text(encoding="utf-8"), custom_agents)

        initialized = self.assert_success(self.workspace_manager("init-workspace", workspace))
        self.assertEqual(initialized["result"], "initialized_missing_items")
        self.assertEqual((workspace / "AGENTS.md").read_text(encoding="utf-8"), custom_agents)
        self.assertTrue((workspace / "sources" / "strategy" / "solopreneur-profile.md").is_file())
        self.assertTrue(
            (
                workspace
                / "sources"
                / "strategy"
                / "social-media-strategy-and-insights.md"
            ).is_file()
        )

        repeated = self.assert_success(self.workspace_manager("init-workspace", workspace))
        self.assertEqual(repeated["result"], "noop")
        states = list((self.state_root / "workspaces").glob("*.json"))
        self.assertEqual(len(states), 1)
        state_text = states[0].read_text(encoding="utf-8")
        self.assertNotIn(custom_agents.strip(), state_text)
        self.assertIn('"contains_credentials": false', state_text)

    def test_workspace_type_conflict_stops_before_changes(self) -> None:
        """目錄與檔案類型衝突時，初始化在寫入前停止。"""

        workspace = self.root / "type-conflict"
        write_text(workspace / "sources", "這是虛構檔案，不是目錄\n")
        result = self.workspace_manager("init-workspace", workspace)
        self.assertEqual(result.returncode, 2)
        self.assertEqual((workspace / "sources").read_text(encoding="utf-8"), "這是虛構檔案，不是目錄\n")
        self.assertFalse((workspace / "AGENTS.md").exists())

    def test_workspace_state_failure_rolls_back_new_files(self) -> None:
        """非敏感狀態無法寫入時，不留下半套初始化工作區。"""

        workspace = self.root / "state-write-failure"
        blocked_state_root = self.root / "state-is-a-file"
        write_text(blocked_state_root, "虛構阻擋檔案\n")
        result = self.workspace_manager(
            "init-workspace",
            workspace,
            state_root=blocked_state_root,
        )
        self.assertEqual(result.returncode, 2)
        self.assertFalse(workspace.exists())
        self.assertEqual(blocked_state_root.read_text(encoding="utf-8"), "虛構阻擋檔案\n")

    def test_package_itself_cannot_be_workspace(self) -> None:
        """管理器不會把公開套件來源誤當成使用者工作區。"""

        result = self.workspace_manager("init-workspace", self.package_v1)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
