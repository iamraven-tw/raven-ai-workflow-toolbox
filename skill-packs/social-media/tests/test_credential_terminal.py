#!/usr/bin/env python3
"""模擬 Terminal 啟動與輸入，不開視窗或使用真實憑證庫。"""

import importlib.util
import json
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_credential_store import CREDENTIAL_STORE, FakeBackend

sys.modules["credential_store"] = CREDENTIAL_STORE
SCRIPT = Path(__file__).resolve().parents[1] / "skills/social-media-setup/scripts/credential_terminal.py"
SPEC = importlib.util.spec_from_file_location("credential_terminal", SCRIPT)
TERMINAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TERMINAL)


class TerminalTests(unittest.TestCase):
    """收據必須反映真實子程序結果，不能只看視窗啟動。"""

    def setUp(self):
        """使用隔離目錄與完全虛構的後端。"""
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-terminal-")
        self.workspace = Path(self.temp.name)
        self.backend = FakeBackend()
        patch = mock.patch.object(CREDENTIAL_STORE, "detect_backend", return_value=self.backend)
        patch.start()
        self.addCleanup(patch.stop)

    def tearDown(self):
        """清除本測試產生的虛構資料。"""
        self.temp.cleanup()

    def launch(self):
        """只模擬開啟視窗，檢查子程序參數不含憑證。"""
        with mock.patch.object(TERMINAL, "launch_process") as process:
            result = TERMINAL.launch(self.workspace, "facebook", "app-secret", confirmed=True)
        self.assertNotIn("fictional-secret", repr(process.call_args))
        return result

    def test_launch_input_readback_and_replay(self):
        """啟動不算成功；完成隱藏輸入後才回報 verified，收據只能用一次。"""
        result = self.launch()
        self.assertEqual(result["status"], "waiting_for_input")
        with mock.patch.object(sys.stdin, "isatty", return_value=True), mock.patch.object(
            sys.stderr, "isatty", return_value=True), mock.patch.object(
            CREDENTIAL_STORE.getpass, "getpass", return_value="fictional-secret"), mock.patch.object(
            CREDENTIAL_STORE, "detect_backend", return_value=self.backend):
            output = TERMINAL.receive(self.workspace, result["ticket"])
        self.assertEqual(output["status"], "verified")
        for path in self.workspace.rglob("*.json"):
            self.assertNotIn("fictional-secret", path.read_text())
        with self.assertRaises(CREDENTIAL_STORE.CredentialStoreError):
            TERMINAL.receive(self.workspace, result["ticket"])

    def test_launch_failure_does_not_retry(self):
        """視窗啟動失敗只留狀態，不自動重開。"""
        with mock.patch.object(TERMINAL, "launch_process", side_effect=OSError) as process:
            result = TERMINAL.launch(self.workspace, "facebook", "app-secret", confirmed=True)
        self.assertEqual(result["status"], "launch_failed")
        self.assertEqual(process.call_count, 1)

    def test_cancel_error_and_timeout_are_not_success(self):
        """取消和逾時不得顯示秘密或被推定為完成。"""
        result = self.launch()
        with mock.patch.object(CREDENTIAL_STORE, "interactive_put", side_effect=RuntimeError("fictional-secret")):
            output = TERMINAL.receive(self.workspace, result["ticket"])
        self.assertEqual(output["status"], "stopped")
        self.assertNotIn("fictional-secret", json.dumps(output))
        result = self.launch()
        with mock.patch.object(TERMINAL.time, "time", return_value=10**12):
            self.assertEqual(TERMINAL.status(self.workspace, result["ticket"])["status"], "unknown_check_registry")
            with self.assertRaises(CREDENTIAL_STORE.CredentialStoreError):
                TERMINAL.receive(self.workspace, result["ticket"])

    def test_approval_and_ticket_path_guards(self):
        """未確認不能開啟 Terminal，收據 ID 不能穿越路徑。"""
        with self.assertRaises(CREDENTIAL_STORE.CredentialStoreError):
            TERMINAL.launch(self.workspace, "facebook", "app-secret", confirmed=False)
        with self.assertRaises(CREDENTIAL_STORE.CredentialStoreError):
            TERMINAL.status(self.workspace, "../outside")
        self.assertFalse(list(self.workspace.iterdir()))

    def test_macos_launcher_quotes_paths_without_executing_shell(self):
        """以 mock 查驗含空白與特殊字元的命令；不真的開啟 Terminal。"""
        arguments = ["fictional python", "folder with space/$(fictional)/script.py", "_input"]
        with mock.patch.object(TERMINAL.sys, "platform", "darwin"), mock.patch.object(
            TERMINAL.subprocess, "run", return_value=mock.Mock(returncode=0)) as run:
            TERMINAL.launch_process(arguments)
        passed = run.call_args.args[0]
        self.assertEqual(passed[0], "/usr/bin/osascript")
        self.assertEqual(shlex.split(passed[-1]), arguments)
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_windows_launcher_uses_new_console_without_shell(self):
        """只檢查 Windows 子程序參數，不呼叫 WinCred 或實際開視窗。"""
        arguments = ["fictional-python.exe", "fictional helper.py", "_input"]
        with mock.patch.object(TERMINAL.sys, "platform", "win32"), mock.patch.object(
            TERMINAL.os, "name", "nt"), mock.patch.object(
            TERMINAL.subprocess, "CREATE_NEW_CONSOLE", 16, create=True), mock.patch.object(
            TERMINAL.subprocess, "Popen") as process:
            TERMINAL.launch_process(arguments)
        process.assert_called_once_with(arguments, creationflags=16)


if __name__ == "__main__":
    unittest.main()
