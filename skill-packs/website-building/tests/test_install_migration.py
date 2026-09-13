"""回歸驗證未受管理舊版遷移、快取與回復交易。"""
import argparse
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("website_install_test", ROOT / "scripts/manage_install.py")
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-migration-")
        self.root = Path(self.temp.name)
        self.client = self.root / "workspace/.agents/skills"
        self.state = self.root / "state"
        self.args = argparse.Namespace(manifest=str(ROOT / "install.manifest.toml"),
            registration="agents_workspace", client_root=str(self.client), state_root=str(self.state))
        for name in ("website-setup", "website-build"):
            manager.copy_skill(ROOT / "skills" / name, self.client / name)
        (self.client / "website-setup/personal-note.txt").write_text("fictional user modification", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_migrate_and_rollback_restore_exact_legacy_skill_set(self):
        before = manager.current_hashes(self.client, ["website-setup", "website-build"])
        preview = manager.migration_plan(self.args)
        self.assertFalse(self.state.exists())
        self.assertIn("personal-note.txt", preview["changes"][0]["remove_from_active"])
        self.args.migration_sha256 = preview["plan_sha256"]
        manager.install_or_update(self.args, update=True)
        self.assertTrue((self.client / "website-operations/SKILL.md").is_file())
        manager.rollback(self.args)
        self.assertEqual(set(p.name for p in self.client.iterdir()), set(before))
        self.assertEqual(manager.current_hashes(self.client, list(before)), before)

    def test_stale_plan_refuses_write(self):
        self.args.migration_sha256 = manager.migration_plan(self.args)["plan_sha256"]
        (self.client / "website-setup/personal-note.txt").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(manager.InstallError, "失效"):
            manager.install_or_update(self.args, update=True)
        self.assertFalse(self.state.exists())

    def test_update_does_not_overwrite_new_unmanaged_collision(self):
        self.args.migration_sha256 = manager.migration_plan(self.args)["plan_sha256"]
        manager.install_or_update(self.args, update=True)
        manager.rollback(self.args)
        collision = self.client / "website-operations"
        collision.mkdir()
        (collision / "SKILL.md").write_text("fictional separate installation", encoding="utf-8")
        with self.assertRaisesRegex(manager.InstallError, "未受管理入口衝突"):
            manager.install_or_update(self.args, update=True)
        self.assertEqual((collision / "SKILL.md").read_text(encoding="utf-8"), "fictional separate installation")

    def test_managed_update_plan_expires_with_registration_change(self):
        self.args.migration_sha256 = manager.migration_plan(self.args)["plan_sha256"]
        manager.install_or_update(self.args, update=True)
        del self.args.migration_sha256
        self.args.expected_plan_sha256 = manager.migration_plan(self.args, managed=True)["plan_sha256"]
        self.args.confirm_write = True
        path = manager.state_path(self.state, self.args.registration, self.client)
        state = manager.read_state(path)
        state["note"] = "fictional concurrent change"
        manager.write_json_atomic(path, state)
        with self.assertRaisesRegex(manager.InstallError, "更新計畫已失效"):
            manager.install_or_update(self.args, update=True)

    def test_state_write_failure_restores_existing_and_removes_new(self):
        self.args.migration_sha256 = manager.migration_plan(self.args)["plan_sha256"]
        before = manager.current_hashes(self.client, ["website-setup", "website-build"])
        real_write = manager.write_json_atomic
        def fail_state(path, value):
            if path.parent.name == "registrations":
                raise OSError("fictional disk failure")
            real_write(path, value)
        with patch.object(manager, "write_json_atomic", side_effect=fail_state):
            with self.assertRaisesRegex(manager.InstallError, "狀態寫入失敗"):
                manager.install_or_update(self.args, update=True)
        self.assertEqual(set(p.name for p in self.client.iterdir()), set(before))
        self.assertEqual(manager.current_hashes(self.client, list(before)), before)

    def test_cache_does_not_change_hash_and_is_not_copied(self):
        source = self.client / "website-setup"
        before = manager.sha256_entry(source)
        cache = source / "scripts/__pycache__"
        cache.mkdir()
        (cache / "fictional.pyc").write_bytes(b"generated runtime")
        self.assertEqual(manager.sha256_entry(source), before)
        copied = self.root / "copied"
        manager.copy_skill(source, copied)
        self.assertFalse((copied / "scripts/__pycache__").exists())
        self.assertEqual(manager.sha256_entry(copied), before)

    def test_discovery_only_reads_matching_registration(self):
        destination = manager.state_path(self.state, self.args.registration, self.client)
        state = manager.base_state(self.args.registration, self.client)
        manager.write_json_atomic(destination, state)
        unrelated = manager.base_state(self.args.registration, self.client)
        unrelated["project_id"] = "fictional-other-pack"
        unrelated["active"] = {"entries": {"other-skill": "fictional"}}
        manager.write_json_atomic(self.root / "other/registrations" / destination.name, unrelated)
        (self.state / "sync-manifest.toml").write_text("must never read", encoding="utf-8")
        self.args.search_root = str(self.root)
        result = manager.discover_state(self.args)
        self.assertEqual(len(result["matches"]), 1)
        self.assertEqual(result["matches"][0]["state_root"], str(self.state))
        self.assertEqual(result["unrelated_registrations_skipped"], 1)

    def test_rollback_state_failure_restores_all_seven(self):
        self.args.migration_sha256 = manager.migration_plan(self.args)["plan_sha256"]
        manager.install_or_update(self.args, update=True)
        before = manager.current_hashes(self.client, [p.name for p in self.client.iterdir()])
        with patch.object(manager, "write_json_atomic", side_effect=OSError("fictional disk failure")):
            with self.assertRaisesRegex(manager.InstallError, "回復狀態寫入失敗"):
                manager.rollback(self.args)
        self.assertEqual(manager.current_hashes(self.client, list(before)), before)


if __name__ == "__main__":
    unittest.main()
