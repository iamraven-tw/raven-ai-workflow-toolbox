"""驗證平台測試護欄不把真錯誤當成環境略過。"""

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

try:
    from . import platform_support as support
except ImportError:
    import platform_support as support


class PlatformSupportTests(unittest.TestCase):
    def test_only_windows_privilege_error_is_skipped(self):
        error = OSError("fictional privilege failure")
        error.winerror = 1314
        link = mock.Mock()
        link.symlink_to.side_effect = error
        with mock.patch.object(support.os, "name", "nt"):
            with self.assertRaises(unittest.SkipTest):
                support.symlink_or_skip(self, link, Path("fictional"))

    def test_other_symlink_errors_are_not_hidden(self):
        link = mock.Mock()
        link.symlink_to.side_effect = OSError("fictional disk failure")
        with self.assertRaises(OSError):
            support.symlink_or_skip(self, link, Path("fictional"))

    @unittest.skipUnless(os.name == "nt", "Windows DACL 驗證")
    def test_acl_checker_rejects_everyone_read_access(self):
        with tempfile.TemporaryDirectory(prefix="fictional-acl-") as temporary:
            root = Path(temporary)
            support.private_fixture(root)
            support.assert_private_file(self, root)
            support._powershell(root, r"""
                $acl = [Security.AccessControl.DirectorySecurity]::new(
                    $env:FICTIONAL_ACL_PATH, [Security.AccessControl.AccessControlSections]::Access)
                $everyone = [Security.Principal.SecurityIdentifier]::new('S-1-1-0')
                $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
                    $everyone, 'Read', 'Allow'))
                [IO.Directory]::SetAccessControl($env:FICTIONAL_ACL_PATH, $acl)
            """)
            with self.assertRaises(AssertionError):
                support.assert_private_file(self, root)
