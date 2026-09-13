"""驗證真實內建技能的獨立安裝、來源拒絕與舊版遷移回復。"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import manage_install as manager
import test_install_lifecycle as legacy


class BundledInstallTests(unittest.TestCase):
    """測試只操作暫存技能目錄，不接觸真實用戶端或 Google。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='toolbox-bundled-test-')
        self.root = Path(self.temp.name)
        self.pack = self.root / 'standalone-pack'
        shutil.copytree(legacy.PACKAGE_ROOT, self.pack,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        self.client = self.root / 'workspace/.agents/skills'
        self.state = self.root / 'state'

    def tearDown(self):
        self.temp.cleanup()

    def call(self, command, *extra):
        args = [sys.executable, str(self.pack / 'scripts/manage_install.py'), command,
                '--registration', 'agents_workspace', '--client-root', str(self.client),
                '--state-root', str(self.state)]
        if command in ('install', 'update'):
            args += ['--manifest', str(self.pack / 'install.manifest.toml')]
        # 來源獨立於 Git，並限制子程序找不到任何外部命令。
        result = subprocess.run(args + list(extra), capture_output=True, text=True,
                                env=dict(os.environ, PATH='', PYTHONDONTWRITEBYTECODE='1'))
        return result

    def ok(self, command):
        result = self.call(command)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_standalone_without_git_install_repeat_remove(self):
        """真實來源可以獨立安裝；完整授權隨技能散布且保留無關檔案。"""
        self.client.mkdir(parents=True)
        keep = self.client / 'unrelated.txt'
        keep.write_text('保留其他技能', encoding='utf-8')
        self.assertEqual(self.ok('install')['result'], 'installed')
        self.assertEqual(self.ok('install')['result'], 'noop')
        for name in legacy.SKILL_NAMES:
            self.assertIn('MIT License', (self.client/name/'LICENSE').read_text())
        self.assertEqual(self.ok('status')['verification'], 'hashes_match')
        self.assertEqual(self.ok('remove')['result'], 'removed_to_quarantine')
        self.assertEqual(keep.read_text(), '保留其他技能')
        self.assertEqual(self.ok('install')['result'], 'reinstalled')

    def test_legacy_managed_update_and_rollback_without_old_source(self):
        """schema 1 已安裝內容，在舊來源不可用時仍可更新並逐位元組回復。"""
        fixture = legacy.InstallLifecycleTest()
        fixture.setUp()
        try:
            result = fixture.manager('install', package=fixture.package_v1, learn=fixture.learn_v1,
                                     client_root=self.client, state_root=self.state)
            fixture.assert_success(result)
            before = {name: manager.hash_entry(self.client/name) for name in legacy.MANAGED_NAMES}
            fixture.tearDown()
            self.assertEqual(self.ok('update')['result'], 'updated')
            self.assertEqual(self.ok('status')['active']['source_policy'], 'toolbox_bundled')
            self.assertEqual(self.ok('rollback')['result'], 'rolled_back')
            self.assertEqual(before, {name: manager.hash_entry(self.client/name) for name in legacy.MANAGED_NAMES})
        finally:
            fixture.temporary.cleanup()

    def test_tampered_source_stops_before_writing(self):
        """來源被更動時，尚未建立任何安裝目錄。"""
        source = self.pack/'skills/google-apps-script-debugging/SKILL.md'
        source.write_text(source.read_text()+'\n異常修改\n')
        self.assertEqual(self.call('install').returncode, 2)
        self.assertFalse(self.client.exists())

    def test_tampered_license_stops_before_writing(self):
        """即使技能雜湊正常，歷史授權遭修改仍須拒絕。"""
        (self.pack/'LICENSE.learn-gas').write_text('授權異常修改', encoding='utf-8')
        self.assertEqual(self.call('install').returncode, 2)
        self.assertFalse(self.client.exists())

    def test_unlocked_entry_stops_before_writing(self):
        """技能來源多出未鎖定內容時，不得宣稱來源驗證成功。"""
        (self.pack/'skills/unexpected.txt').write_text('未登錄內容', encoding='utf-8')
        self.assertEqual(self.call('install').returncode, 2)
        self.assertFalse(self.client.exists())

    def test_missing_lock_stops_before_writing(self):
        (self.pack/'bundle.lock.json').unlink()
        self.assertEqual(self.call('install').returncode, 2)
        self.assertFalse(self.client.exists())

    def test_external_source_option_is_rejected(self):
        self.assertEqual(self.call('install', '--learn-gas-source', str(self.root/'absent')).returncode, 2)
        self.assertFalse(self.client.exists())

    def test_modified_old_install_is_preserved(self):
        self.ok('install')
        source = self.client/'google-apps-script-debugging/SKILL.md'
        source.write_text(source.read_text()+'\n使用者修改\n')
        self.assertEqual(self.call('update').returncode, 2)
        self.assertEqual(self.call('remove').returncode, 2)
        self.assertIn('使用者修改',source.read_text())

    def test_direct_legacy_partial_install_stops(self):
        """直接安裝舊版的五個入口沒有狀態，不會被自動冒認。"""
        self.client.mkdir(parents=True)
        for name in legacy.MANAGED_NAMES[1:]:
            manager.copy_entry(self.pack/'skills'/name, self.client/name)
        self.assertEqual(self.call('install').returncode, 2)
        self.assertFalse((self.client/'google-workflow-router').exists())

    def test_failed_update_state_write_restores_original(self):
        """來源更新後若狀態檔寫入失敗，舊入口必須完整還原。"""
        self.ok('install')
        before = {name: manager.hash_entry(self.client/name) for name in legacy.MANAGED_NAMES}
        manifest = self.pack/'install.manifest.toml'
        manifest.write_text(manifest.read_text().replace('candidate_version = "0.2.0"','candidate_version = "0.2.1"'))
        skill = self.pack/'skills/google-workflow-router/SKILL.md'
        skill.write_text(skill.read_text()+'\n新版本測試\n')
        result = subprocess.run([sys.executable,str(self.pack/'scripts/lock_bundle.py')], capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        args = manager.build_parser().parse_args(['update','--manifest',str(manifest),
                    '--registration','agents_workspace','--client-root',str(self.client),'--state-root',str(self.state)])
        original = manager.write_json_atomic
        def fail_registration(path, payload):
            if path.parent.name == 'registrations':
                raise manager.InstallError('測試狀態寫入失敗')
            return original(path,payload)
        with patch.object(manager,'write_json_atomic',side_effect=fail_registration):
            with self.assertRaises(manager.InstallError):
                manager.update_command(args)
        self.assertEqual(before,{name:manager.hash_entry(self.client/name) for name in legacy.MANAGED_NAMES})
        self.assertEqual(self.ok('status')['active']['toolbox_version'],'0.2.0')


if __name__ == '__main__':
    unittest.main()
