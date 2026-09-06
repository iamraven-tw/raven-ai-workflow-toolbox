"""設定技能的中文路徑與選擇性 Windows 原生憑證驗收。"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

from test_credential_store import CREDENTIAL_STORE as vault, SCRIPT as VAULT_SCRIPT

ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / 'skills/social-media-setup/scripts/manage_workspace.py'
DEFAULT = ROOT / 'skills/social-media-setup/assets/default-config.json'


class SetupAcceptanceTests(unittest.TestCase):
    def test_unicode_workspace_preview_apply_readback(self):
        """實際子程序在中文與空白路徑完成預覽、套用及讀回。"""
        with tempfile.TemporaryDirectory(prefix='social-setup-') as temp:
            workspace = Path(temp) / '虛構品牌 空白'
            candidate = Path(temp) / '候選 設定.json'
            candidate.write_bytes(DEFAULT.read_bytes())

            def command(action, *args):
                result = subprocess.run([sys.executable, str(MANAGER), action,
                    '--workspace-root', str(workspace), *args], capture_output=True,
                    text=True, encoding='utf-8', env=dict(os.environ, PYTHONUTF8='1'))
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)

            self.assertEqual(command('status')['result'], 'missing')
            preview = command('preview', '--candidate', str(candidate))
            self.assertFalse((workspace / 'social-media/config.json').exists())
            command('apply', '--candidate', str(candidate), '--expected-preview-sha256',
                    preview['preview_sha256'], '--confirm-write')
            result = command('status')
            self.assertEqual(result['verification'], 'hashes_match')
            self.assertFalse(result['contains_credentials'])

    @unittest.skipUnless(os.name == 'nt' and os.environ.get('SOCIAL_NATIVE_ACCEPTANCE') == '1',
                         '原生 Windows 驗收須明確啟用；只建立一次性虛構項目')
    def test_windows_native_roundtrip_across_processes(self):
        """唯一 namespace 的虛構值跨程序讀回，最後只移除本測試建立的項目。"""
        with tempfile.TemporaryDirectory(prefix='social-native-') as temp:
            workspace = Path(temp) / '虛構憑證 空白'
            workspace.mkdir()
            value = 'fictional-test-虛構-' + uuid.uuid4().hex
            try:
                vault.store_secret(workspace, 'facebook', 'app-secret', value, source='oauth-callback')
                script = ('import sys,hashlib; from pathlib import Path; '
                          'sys.path.insert(0,sys.argv[1]); import credential_store as v; '
                          'value=v.load_secret(Path(sys.argv[2]),"facebook","app-secret"); '
                          'assert hashlib.sha256(value.encode()).hexdigest()==sys.argv[3]; '
                          'print("readback_verified")')
                result = subprocess.run([sys.executable, '-c', script, str(VAULT_SCRIPT.parent),
                    str(workspace), hashlib.sha256(value.encode()).hexdigest()],
                    capture_output=True, text=True, encoding='utf-8', env=dict(os.environ, PYTHONUTF8='1'))
                self.assertEqual(result.returncode, 0, '原生憑證跨程序讀回失敗')
                self.assertEqual(result.stdout.strip(), 'readback_verified')
                for file in workspace.rglob('*.json'):
                    self.assertTrue(value not in file.read_text(encoding='utf-8'),
                                    '虛構憑證值不得寫入一般 JSON')
            finally:
                registry = vault.load_registry(workspace)
                if registry and 'facebook/app-secret' in registry['entries']:
                    vault.remove_secret(workspace, 'facebook', 'app-secret', confirmed=True)
            self.assertEqual(vault.credential_status(workspace)['entries'], [])
