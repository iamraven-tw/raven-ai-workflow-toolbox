#!/usr/bin/env python3
"""以隔離目錄驗證候選技能與版本遷移的安裝生命週期。"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / "scripts/manage_install.py"
SKILL = "social-media-setup"
PLANNING = "social-content-planning"
WRITING = "social-content-writing"
IMAGE = "social-image-production"
PUBLISHING = "social-content-publishing"
COMMUNITY = "social-community-management"
PERFORMANCE = "social-performance-analysis"
SKILLS = (SKILL, PLANNING, WRITING, IMAGE, PUBLISHING, COMMUNITY, PERFORMANCE)


def run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """執行生命週期命令並保留輸出。"""

    return subprocess.run(arguments, capture_output=True, text=True)


class InstallLifecycleTests(unittest.TestCase):
    """驗證安裝、重跑、衝突、更新、回復與可回復移除。"""

    def setUp(self) -> None:
        """建立完全隔離的虛構 Agent 入口與狀態。"""

        self.temporary = tempfile.TemporaryDirectory(prefix="fictional-social-install-")
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

    def test_installed_oauth_adapter_can_be_imported_without_setup(self):
        """隔離安裝包含專用程式與文件；help 不讀秘密、不登入、不連平台。"""
        self.assert_success(self.command("install"))
        installed = self.client_root / SKILL
        self.assertTrue((installed / "scripts/meta_user_oauth.py").is_file())
        self.assertTrue((installed / "scripts/instagram_facebook_oauth.py").is_file())
        self.assertTrue((installed / "references/instagram-threads-oauth.md").is_file())
        self.assertTrue((installed / "references/instagram-facebook-login-oauth.md").is_file())
        result = run([sys.executable, str(installed / "scripts/oauth_callback.py"), "--help"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("instagram", result.stdout)
        self.assertIn("threads", result.stdout)

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

    def make_version_one(self) -> Path:
        """在隔離目錄重建只有第一技能的舊版 manifest 契約。"""
        package = self.temp_root / "package-v1"
        shutil.copytree(ROOT, package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.rmtree(package / "skills" / PLANNING)
        shutil.rmtree(package / "skills" / PUBLISHING)
        shutil.rmtree(package / "skills" / WRITING)
        shutil.rmtree(package / "skills" / IMAGE)
        manifest = package / "install.manifest.toml"
        text = manifest.read_text(encoding="utf-8")
        text = re.sub(r'\[\[skills\]\]\nid = "social-content-planning"\n.*?(?=\[\[readiness_gates\]\])', '', text, flags=re.S)
        text = re.sub(r'^managed_entries = .*$', 'managed_entries = ["social-media-setup"]', text, flags=re.M)
        text = text.replace('candidate_version = "0.7.0"', 'candidate_version = "0.1.0"')
        text = text.replace('local_candidate_full_pack', 'local_candidate_first_skill')
        text = text.replace('full_pack_installable_candidate_not_formally_supported', 'first_skill_installable_candidate_not_formally_supported')
        manifest.write_text(text, encoding="utf-8")
        return manifest

    def test_full_lifecycle_and_discovery_entry(self) -> None:
        """完整驗證安裝、更新、回復、移除與重新安裝。"""

        available = self.assert_success(self.command("status"))
        self.assertEqual(available["result"], "available")

        installed = self.assert_success(self.command("install"))
        self.assertEqual(installed["result"], "installed")
        self.assertEqual(set(installed["managed_entries"]), set(SKILLS))
        self.assertTrue((self.client_root / PLANNING / "SKILL.md").is_file())
        self.assertTrue((self.client_root / WRITING / "scripts/check_drafts.py").is_file())
        self.assertTrue((self.client_root / IMAGE / "scripts/image_assets.py").is_file())
        self.assertTrue((self.client_root / IMAGE / "agents/openai.yaml").is_file())
        self.assertTrue((self.client_root / IMAGE /
                         "references/acceptance-testing.md").is_file())
        self.assertTrue((self.client_root / IMAGE /
                         "assets/acceptance-test-brief.json").is_file())
        self.assertTrue((self.client_root / IMAGE /
                         "assets/acceptance-information-card.html").is_file())
        self.assertTrue((self.client_root / PUBLISHING / "scripts/publish_job.py").is_file())
        self.assertEqual(len(list((self.client_root / PUBLISHING / "references/platforms").glob("*.md"))), 5)
        self.assertTrue((self.client_root / COMMUNITY / "scripts/community_queue.py").is_file())
        self.assertEqual(len(list((self.client_root / COMMUNITY / "references/platforms").glob("*.md"))), 5)
        self.assertTrue((self.client_root / PERFORMANCE / "scripts/performance_review.py").is_file())
        self.assertTrue((self.client_root / PERFORMANCE / "scripts/metric_catalog.py").is_file())
        self.assertTrue((self.client_root / PERFORMANCE /
                         "references/metric-catalog.json").is_file())
        self.assertEqual(len(list((self.client_root / PERFORMANCE / "references/platforms").glob("*.md"))), 5)
        installed_skill = self.client_root / SKILL / "SKILL.md"
        self.assertTrue(installed_skill.is_file())
        self.assertIn("name: social-media-setup", installed_skill.read_text(encoding="utf-8"))

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
        self.assertFalse((self.client_root / PLANNING).exists())
        self.assertTrue(Path(removed["quarantine"]).joinpath(PLANNING).is_dir())
        self.assertFalse((self.client_root / WRITING).exists())
        self.assertTrue(Path(removed["quarantine"]).joinpath(WRITING).is_dir())
        self.assertFalse((self.client_root / IMAGE).exists())
        self.assertTrue(Path(removed["quarantine"]).joinpath(IMAGE).is_dir())
        self.assertFalse((self.client_root / PUBLISHING).exists())
        self.assertTrue(Path(removed["quarantine"]).joinpath(PUBLISHING).is_dir())

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
        installed.write_text(
            installed.read_text(encoding="utf-8") + "\n虛構人工修改\n", encoding="utf-8"
        )
        update = self.command("update", manifest=self.make_version_two())
        remove = self.command("remove")
        self.assertEqual(update.returncode, 2)
        self.assertEqual(remove.returncode, 2)
        self.assertIn("虛構人工修改", installed.read_text(encoding="utf-8"))

    def test_identical_unmanaged_skill_is_adopted_without_rewrite(self) -> None:
        """完全相同的既有入口只建立狀態，不重寫內容。"""

        target = self.client_root / SKILL
        target.parent.mkdir(parents=True)
        for name in SKILLS:
            shutil.copytree(ROOT / "skills" / name, self.client_root / name)
        before = (target / "SKILL.md").stat().st_mtime_ns
        adopted = self.assert_success(self.command("install"))
        after = (target / "SKILL.md").stat().st_mtime_ns
        self.assertEqual(adopted["result"], "adopted_identical")
        self.assertEqual(before, after)

    def test_first_skill_upgrade_and_rollback_leave_no_unmanaged_new_entry(self):
        """一技能升級成四技能再回復，不能留下新增的技能入口。"""
        old = self.make_version_one()
        self.assert_success(self.command("install", manifest=old))
        self.assertFalse((self.client_root / PLANNING).exists())
        self.assertFalse((self.client_root / WRITING).exists())
        self.assert_success(self.command("update"))
        self.assertTrue((self.client_root / PLANNING / "SKILL.md").is_file())
        self.assert_success(self.command("rollback"))
        self.assertFalse((self.client_root / PLANNING).exists())
        state = self.assert_success(self.command("status", manifest=old))
        self.assertFalse((self.client_root / WRITING).exists())
        self.assertFalse((self.client_root / IMAGE).exists())
        self.assertEqual(state["managed_entries"], [SKILL])
        self.assert_success(self.command("update"))

    def test_two_skill_upgrade_and_writing_conflicts(self):
        """兩技能升級成四技能，保護同名衝突並驗證回復不留殘骸。"""
        package = self.temp_root / "package-two-skills"
        shutil.copytree(ROOT, package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.rmtree(package / "skills" / WRITING)
        shutil.rmtree(package / "skills" / PUBLISHING)
        shutil.rmtree(package / "skills" / IMAGE)
        manifest = package / "install.manifest.toml"
        text = manifest.read_text(encoding="utf-8")
        text = re.sub(r'\[\[skills\]\]\nid = "social-content-writing"\n.*?(?=\[\[readiness_gates\]\])', '', text, flags=re.S)
        text = re.sub(r'^managed_entries = .*$', 'managed_entries = ["social-media-setup", "social-content-planning"]', text, flags=re.M)
        text = text.replace('candidate_version = "0.7.0"', 'candidate_version = "0.2.0"')
        manifest.write_text(text, encoding="utf-8")
        self.assert_success(self.command("install", manifest=manifest))
        foreign = self.client_root / WRITING
        foreign.mkdir()
        marker = foreign / "KEEP.txt"
        marker.write_text("虛構同名內容", encoding="utf-8")
        self.assertEqual(self.command("update").returncode, 2)
        self.assertEqual(marker.read_text(encoding="utf-8"), "虛構同名內容")
        foreign.rename(self.temp_root / "preserved-foreign-writing")
        self.assert_success(self.command("update"))
        installed = self.client_root / WRITING
        self.assertTrue((installed / "references/platforms/youtube.md").is_file())
        self.assert_success(self.command("rollback"))
        self.assertFalse(installed.exists())
        self.assertFalse((self.client_root / IMAGE).exists())
        self.assertTrue((self.client_root / PLANNING).exists())
        self.assert_success(self.command("update"))
        marker = installed / "KEEP.txt"
        marker.write_text("虛構人工修改", encoding="utf-8")
        self.assertEqual(self.command("rollback").returncode, 2)
        self.assertTrue(marker.exists())

    def test_three_skill_upgrade_image_conflicts_and_rollback(self):
        """三技能升級成四技能；未知與人工修改的圖片技能都必須保留。"""
        package = self.temp_root / "package-three-skills"
        shutil.copytree(ROOT, package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.rmtree(package / "skills" / IMAGE)
        shutil.rmtree(package / "skills" / PUBLISHING)
        manifest = package / "install.manifest.toml"
        text = manifest.read_text(encoding="utf-8")
        text = re.sub(r'\[\[skills\]\]\nid = "social-image-production"\n.*?(?=\[\[readiness_gates\]\])', '', text, flags=re.S)
        text = re.sub(r'^managed_entries = .*$', 'managed_entries = ' + json.dumps(list(SKILLS[:3])), text, flags=re.M)
        text = text.replace('candidate_version = "0.7.0"', 'candidate_version = "0.3.0"')
        manifest.write_text(text, encoding="utf-8")
        self.assert_success(self.command("install", manifest=manifest))
        foreign = self.client_root / IMAGE
        foreign.mkdir()
        marker = foreign / "KEEP.txt"
        marker.write_text("虛構外部技能", encoding="utf-8")
        self.assertEqual(self.command("update").returncode, 2)
        self.assertEqual(marker.read_text(encoding="utf-8"), "虛構外部技能")
        foreign.rename(self.temp_root / "preserved-foreign-image")
        self.assert_success(self.command("update"))
        self.assertTrue((foreign / "scripts/image_assets.py").is_file())
        self.assert_success(self.command("rollback"))
        self.assertFalse(foreign.exists())
        self.assertTrue((self.client_root / WRITING / "SKILL.md").is_file())
        self.assert_success(self.command("update"))
        marker.write_text("虛構人工修改", encoding="utf-8")
        self.assertEqual(self.command("rollback").returncode, 2)
        self.assertTrue(marker.is_file())

    def test_new_skill_collision_is_preserved_during_upgrade(self):
        """新增技能若和其他來源同名，先停止且不覆蓋。"""
        old = self.make_version_one()
        self.assert_success(self.command("install", manifest=old))
        foreign = self.client_root / PLANNING
        foreign.mkdir()
        marker = foreign / "KEEP.txt"
        marker.write_text("虛構其他技能", encoding="utf-8")
        self.assertEqual(self.assert_success(self.command("status"))["result"], "blocked")
        self.assertEqual(self.command("update").returncode, 2)
        self.assertEqual(marker.read_text(encoding="utf-8"), "虛構其他技能")

    def test_four_skill_upgrade_publishing_collision_and_rollback(self):
        """四技能升級七技能；保留同名內容與回復前人工修改。"""
        package = self.temp_root / "package-four-skills"
        shutil.copytree(ROOT, package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.rmtree(package / "skills" / PUBLISHING)
        manifest = package / "install.manifest.toml"
        text = manifest.read_text(encoding="utf-8")
        text = re.sub(r'\[\[skills\]\]\nid = "social-content-publishing"\n.*?(?=\[\[readiness_gates\]\])', '', text, flags=re.S)
        text = re.sub(r'^managed_entries = .*$', 'managed_entries = ' + json.dumps(list(SKILLS[:4])), text, flags=re.M)
        text = text.replace('candidate_version = "0.7.0"', 'candidate_version = "0.4.0"')
        manifest.write_text(text, encoding="utf-8")
        self.assert_success(self.command("install", manifest=manifest))
        foreign = self.client_root / PUBLISHING
        foreign.mkdir()
        marker = foreign / "KEEP.txt"
        marker.write_text("虛構外部技能", encoding="utf-8")
        self.assertEqual(self.command("update").returncode, 2)
        self.assertTrue(marker.is_file())
        foreign.rename(self.temp_root / "preserved-foreign-publishing")
        self.assert_success(self.command("update"))
        self.assertTrue((foreign / "references/platforms/substack.md").is_file())
        self.assert_success(self.command("rollback"))
        self.assertFalse(foreign.exists())
        self.assertTrue((self.client_root / IMAGE / "SKILL.md").is_file())
        self.assert_success(self.command("update"))
        marker.write_text("虛構人工修改", encoding="utf-8")
        self.assertEqual(self.command("rollback").returncode, 2)
        self.assertTrue(marker.is_file())

    def test_five_skill_upgrade_community_collision_and_rollback(self):
        """五技能升級七技能，保留未知來源並可回到原五技能集合。"""
        package = self.temp_root / "package-five-skills"
        shutil.copytree(ROOT, package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.rmtree(package / "skills" / COMMUNITY)
        manifest = package / "install.manifest.toml"
        text = manifest.read_text(encoding="utf-8")
        text = re.sub(r'\[\[skills\]\]\nid = "social-community-management"\n.*?(?=\[\[readiness_gates\]\])', '', text, flags=re.S)
        text = re.sub(r'^managed_entries = .*$', 'managed_entries = ' + json.dumps(list(SKILLS[:5])), text, flags=re.M)
        text = text.replace('candidate_version = "0.7.0"', 'candidate_version = "0.5.0"')
        manifest.write_text(text, encoding="utf-8")
        self.assert_success(self.command("install", manifest=manifest))
        foreign = self.client_root / COMMUNITY
        foreign.mkdir()
        marker = foreign / "KEEP.txt"
        marker.write_text("虛構外部互動技能", encoding="utf-8")
        self.assertEqual(self.command("update").returncode, 2)
        self.assertTrue(marker.is_file())
        foreign.rename(self.temp_root / "preserved-foreign-community")
        self.assert_success(self.command("update"))
        self.assertTrue((foreign / "scripts/community_queue.py").is_file())
        self.assert_success(self.command("rollback"))
        self.assertFalse(foreign.exists())
        self.assertTrue((self.client_root / PUBLISHING / "SKILL.md").is_file())
        self.assert_success(self.command("update"))
        marker.write_text("虛構人工修改", encoding="utf-8")
        self.assertEqual(self.command("rollback").returncode, 2)
        self.assertTrue(marker.is_file())

    def test_new_skill_edit_blocks_rollback(self):
        """回復不得刪除第二技能的人工作品。"""
        old = self.make_version_one()
        self.assert_success(self.command("install", manifest=old))
        self.assert_success(self.command("update"))
        marker = self.client_root / PLANNING / "KEEP.txt"
        marker.write_text("虛構人工修改", encoding="utf-8")
        self.assertEqual(self.command("rollback").returncode, 2)
        self.assertTrue(marker.is_file())

    def test_six_skill_upgrade_performance_collision_and_rollback(self):
        """六技能升級七技能，驗證新增入口、私人策略保留及衝突回復。"""
        package = self.temp_root / "package-six-skills"
        shutil.copytree(ROOT, package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.rmtree(package / "skills" / PERFORMANCE)
        manifest = package / "install.manifest.toml"
        text = manifest.read_text(encoding="utf-8")
        text = re.sub(r'\[\[skills\]\]\nid = "social-performance-analysis"\n.*?(?=\[\[readiness_gates\]\])', '', text, flags=re.S)
        text = re.sub(r'^managed_entries = .*$', 'managed_entries = ' + json.dumps(list(SKILLS[:6])), text, flags=re.M)
        text = text.replace('candidate_version = "0.7.0"', 'candidate_version = "0.6.0"')
        text = text.replace("local_candidate_full_pack", "local_candidate_partial_pack")
        text = text.replace("full_pack_installable_candidate_not_formally_supported", "partial_pack_installable_candidate_not_formally_supported")
        manifest.write_text(text, encoding="utf-8")
        self.assert_success(self.command("install", manifest=manifest))
        private = self.temp_root / "fictional-workspace/sources/strategy/keep.md"
        private.parent.mkdir(parents=True)
        private.write_text("虛構私人策略，不屬於安裝器", encoding="utf-8")
        foreign = self.client_root / PERFORMANCE
        foreign.mkdir()
        marker = foreign / "KEEP.txt"
        marker.write_text("虛構外部成效技能", encoding="utf-8")
        self.assertEqual(self.command("update").returncode, 2)
        self.assertTrue(marker.is_file())
        foreign.rename(self.temp_root / "preserved-foreign-performance")
        self.assert_success(self.command("update"))
        self.assertTrue((foreign / "scripts/performance_review.py").is_file())
        self.assert_success(self.command("rollback"))
        self.assertFalse(foreign.exists())
        self.assertTrue((self.client_root / COMMUNITY / "SKILL.md").is_file())
        self.assertEqual(private.read_text(encoding="utf-8"), "虛構私人策略，不屬於安裝器")
        self.assert_success(self.command("update"))
        marker.write_text("虛構人工修改", encoding="utf-8")
        self.assertEqual(self.command("rollback").returncode, 2)
        self.assertTrue(marker.is_file())

    def test_restore_removed_skill_preserves_foreign_collision(self):
        """明確更新成一技能版後，回復也不能覆蓋新出現的同名來源。"""
        old = self.make_version_one()
        self.assert_success(self.command("install"))
        self.assert_success(self.command("update", manifest=old))
        self.assertFalse((self.client_root / PLANNING).exists())
        foreign = self.client_root / PLANNING
        foreign.mkdir()
        marker = foreign / "KEEP.txt"
        marker.write_text("虛構回復衝突", encoding="utf-8")
        self.assertEqual(self.command("rollback").returncode, 2)
        self.assertEqual(marker.read_text(encoding="utf-8"), "虛構回復衝突")


if __name__ == "__main__":
    unittest.main()
