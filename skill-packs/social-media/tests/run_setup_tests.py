"""只執行 social-media-setup 回歸；從任意工作目錄可啟動。"""
from pathlib import Path
import sys
import unittest

TEST_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(TEST_ROOT))
MODULES = (
    'test_workspace_config', 'test_credential_store', 'test_credential_terminal',
    'test_oauth_runtime', 'test_meta_user_oauth', 'test_instagram_facebook_oauth',
    'test_opencli_contract', 'test_setup_acceptance',
)

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromNames(MODULES)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
