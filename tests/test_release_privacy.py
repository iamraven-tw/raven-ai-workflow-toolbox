"""公開檔案守門器的虛構回歸測試。"""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('release_audit', Path(__file__).resolve().parents[1] / 'scripts/validate_release.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ReleasePrivacyTests(unittest.TestCase):
    def test_private_file_names_rejected(self):
        for name in ('.local/report.json', 'a/__pycache__/x.pyc', '.env', 'key.pem', 'storage_state.json'):
            self.assertTrue(audit.forbidden(name), name)

    def test_public_examples_allowed(self):
        for name in ('.env.example', 'README.md', 'skills/setup/references/schema.json'):
            self.assertFalse(audit.forbidden(name), name)

    def test_secret_findings_do_not_echo_values(self):
        synthetic = 'ghp_' + 'A' * 36
        result = audit.findings(synthetic.encode())
        self.assertEqual(result, [{'kind': 'github_token', 'line': 1}])
        self.assertNotIn(synthetic, str(result))

    def test_private_paths_and_keys_detected(self):
        for sample in ('/'.join(('C:', 'Users', 'example', 'file')), '/'.join(('', 'Users', 'example', 'file')),
                       '-----BEGIN ' + 'PRIVATE KEY-----'):
            self.assertTrue(audit.findings(sample.encode()))

    def test_neutral_text_is_allowed(self):
        self.assertEqual(audit.findings('虛構品牌 https://example.invalid'.encode()), [])
