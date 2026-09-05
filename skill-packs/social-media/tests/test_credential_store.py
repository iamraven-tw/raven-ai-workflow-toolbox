#!/usr/bin/env python3
"""以虛構 backend 驗證本機憑證儲存契約。"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from argparse import Namespace
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/social-media-setup/scripts/credential_store.py"
SPEC = importlib.util.spec_from_file_location("social_credential_store", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("無法載入 credential_store.py")
CREDENTIAL_STORE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CREDENTIAL_STORE
SPEC.loader.exec_module(CREDENTIAL_STORE)


class FakeBackend:
    """只在測試記憶體保存虛構值，不接觸真實憑證庫。"""

    name = "macos-keychain"

    def __init__(self) -> None:
        """建立空白虛構儲存。"""

        self.values: dict[str, str] = {}

    def exists(self, target: str) -> bool:
        """回報虛構項目存在性。"""

        return target in self.values

    def put(self, target: str, value: str, *, replace: bool) -> None:
        """依取代旗標保存虛構值。"""

        if target in self.values and not replace:
            raise CREDENTIAL_STORE.CredentialStoreError("必須確認取代")
        self.values[target] = value

    def read(self, target: str) -> str:
        """讀取虛構值。"""

        if target not in self.values:
            raise CREDENTIAL_STORE.CredentialNotFound("不存在")
        return self.values[target]

    def delete(self, target: str) -> None:
        """刪除單一虛構值。"""

        if target not in self.values:
            raise CREDENTIAL_STORE.CredentialNotFound("不存在")
        del self.values[target]


class CredentialStoreTests(unittest.TestCase):
    """確認秘密不進入參照檔、命令列或一般輸出。"""

    def setUp(self) -> None:
        """建立隔離工作區與虛構 backend。"""

        self.temporary = tempfile.TemporaryDirectory(
            prefix="fictional-social-credentials-"
        )
        self.workspace = Path(self.temporary.name) / "fictional-workspace"
        self.workspace.mkdir()
        self.backend = FakeBackend()

    def tearDown(self) -> None:
        """移除虛構工作區。"""

        self.temporary.cleanup()

    def test_store_read_and_status_never_emit_secret(self) -> None:
        """新增、讀回與狀態輸出都只留下非敏感參照。"""

        secret = "虛構-meta-secret-123"
        result = CREDENTIAL_STORE.store_secret(
            self.workspace,
            "facebook",
            "app-secret",
            secret,
            source="interactive-terminal",
            backend=self.backend,
        )
        self.assertEqual(result["status"], "verified")
        self.assertFalse(result["contains_credentials"])
        self.assertNotIn(secret, json.dumps(result))

        registry_path = self.workspace / CREDENTIAL_STORE.REGISTRY_RELATIVE
        registry_text = registry_path.read_text(encoding="utf-8")
        self.assertNotIn(secret, registry_text)
        registry = json.loads(registry_text)
        self.assertFalse(registry["contains_credentials"])
        self.assertEqual(
            set(registry["entries"]), {"facebook/app-secret"}
        )
        if sys.platform != "win32":
            self.assertEqual(registry_path.stat().st_mode & 0o777, 0o600)

        loaded = CREDENTIAL_STORE.load_secret(
            self.workspace,
            "facebook",
            "app-secret",
            backend=self.backend,
        )
        self.assertEqual(loaded, secret)
        status = CREDENTIAL_STORE.credential_status(
            self.workspace, backend=self.backend
        )
        self.assertTrue(status["entries"][0]["available"])
        self.assertNotIn(secret, json.dumps(status))

    def test_replace_requires_explicit_confirmation(self) -> None:
        """同名項目不會在未確認時被覆蓋。"""

        CREDENTIAL_STORE.store_secret(
            self.workspace,
            "facebook",
            "access-token",
            "fictional-first-token",
            source="oauth-callback",
            backend=self.backend,
        )
        with self.assertRaises(CREDENTIAL_STORE.CredentialStoreError):
            CREDENTIAL_STORE.store_secret(
                self.workspace,
                "facebook",
                "access-token",
                "fictional-second-token",
                source="oauth-callback",
                backend=self.backend,
            )
        self.assertEqual(next(iter(self.backend.values.values())), "fictional-first-token")

        replaced = CREDENTIAL_STORE.store_secret(
            self.workspace,
            "facebook",
            "access-token",
            "fictional-second-token",
            source="oauth-callback",
            replace=True,
            backend=self.backend,
        )
        self.assertEqual(replaced["status"], "verified")
        self.assertEqual(next(iter(self.backend.values.values())), "fictional-second-token")

    def test_remove_requires_confirmation_and_targets_one_entry(self) -> None:
        """刪除必須確認，且不影響其他憑證。"""

        for name in ("app-secret", "access-token"):
            CREDENTIAL_STORE.store_secret(
                self.workspace,
                "facebook",
                name,
                f"fictional-{name}",
                source="oauth-callback",
                backend=self.backend,
            )
        with self.assertRaises(CREDENTIAL_STORE.CredentialStoreError):
            CREDENTIAL_STORE.remove_secret(
                self.workspace,
                "facebook",
                "app-secret",
                confirmed=False,
                backend=self.backend,
            )
        removed = CREDENTIAL_STORE.remove_secret(
            self.workspace,
            "facebook",
            "app-secret",
            confirmed=True,
            backend=self.backend,
        )
        self.assertEqual(removed["status"], "deleted")
        status = CREDENTIAL_STORE.credential_status(
            self.workspace, backend=self.backend
        )
        self.assertEqual(
            [(item["platform"], item["name"]) for item in status["entries"]],
            [("facebook", "access-token")],
        )

    def test_symlink_registry_path_is_rejected(self) -> None:
        """symlink 不得把非敏感參照寫到工作區外。"""

        if not hasattr(Path, "symlink_to"):
            self.skipTest("平台不支援 symlink")
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        local = self.workspace / ".local"
        local.mkdir()
        try:
            (local / "social-media").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("目前環境不允許建立 symlink")
        with self.assertRaises(CREDENTIAL_STORE.CredentialStoreError):
            CREDENTIAL_STORE.store_secret(
                self.workspace,
                "facebook",
                "app-secret",
                "fictional-secret",
                source="interactive-terminal",
                backend=self.backend,
            )
        self.assertFalse(any(outside.iterdir()))

    def test_cli_has_no_secret_value_or_read_command(self) -> None:
        """公開 CLI 不接受秘密參數，也不提供 stdout 讀值命令。"""

        help_result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertNotIn("--value", help_result.stdout)
        commands = CREDENTIAL_STORE.build_parser()._subparsers._group_actions[0].choices
        self.assertNotIn("get", commands)
        self.assertEqual(set(commands), {"inspect", "status", "put", "remove", "recover"})

    def test_interactive_put_refuses_non_terminal_input(self) -> None:
        """非互動 pipe 不得繞過隱藏 Terminal 輸入。"""

        arguments = Namespace(
            workspace_root=str(self.workspace),
            platform="facebook",
            name="app-secret",
            confirm_replace=False,
        )
        with mock.patch.object(sys.stdin, "isatty", return_value=False):
            with self.assertRaises(CREDENTIAL_STORE.CredentialStoreError):
                CREDENTIAL_STORE.interactive_put(arguments)
        self.assertFalse(self.backend.values)

    def test_interactive_secret_uses_hidden_prompt_and_sanitized_result(self) -> None:
        """互動秘密只經 getpass 與 backend，不出現在結果。"""

        secret = "fictional-hidden-secret"
        arguments = Namespace(
            workspace_root=str(self.workspace),
            platform="facebook",
            name="app-secret",
            confirm_replace=False,
        )
        with mock.patch.object(sys.stdin, "isatty", return_value=True), mock.patch.object(
            sys.stderr, "isatty", return_value=True
        ), mock.patch.object(
            CREDENTIAL_STORE.getpass, "getpass", return_value=secret
        ), mock.patch.object(
            CREDENTIAL_STORE, "detect_backend", return_value=self.backend
        ):
            result = CREDENTIAL_STORE.interactive_put(arguments)
        self.assertEqual(result["status"], "verified")
        self.assertNotIn(secret, json.dumps(result))

    def test_interrupted_registry_commit_recovers_without_vault_write(self):
        """憑證已寫入、最終參照寫入失敗時，保留目標且不得交給平台。"""

        original = CREDENTIAL_STORE.write_registry
        writes = 0
        def fail_second(workspace, payload):
            nonlocal writes
            writes += 1
            if writes == 2:
                raise OSError("fictional interruption")
            return original(workspace, payload)
        with mock.patch.object(CREDENTIAL_STORE, "write_registry", side_effect=fail_second):
            with self.assertRaises(OSError):
                CREDENTIAL_STORE.store_secret(self.workspace, "facebook", "app-secret",
                    "fictional-secret", source="oauth-callback", backend=self.backend)
        registry = CREDENTIAL_STORE.load_registry(self.workspace)
        self.assertEqual(registry["entries"]["facebook/app-secret"]["status"], "pending_write")
        with self.assertRaises(CREDENTIAL_STORE.CredentialStoreError):
            CREDENTIAL_STORE.load_secret(self.workspace, "facebook", "app-secret", backend=self.backend)
        with self.assertRaises(CREDENTIAL_STORE.CredentialStoreError):
            CREDENTIAL_STORE.recover_secret(self.workspace, "facebook", "app-secret",
                "wrong-fictional-secret", confirmed=True, backend=self.backend)
        with mock.patch.object(self.backend, "put", side_effect=AssertionError("不得重寫")):
            result = CREDENTIAL_STORE.recover_secret(self.workspace, "facebook", "app-secret",
                "fictional-secret", confirmed=True, backend=self.backend)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(CREDENTIAL_STORE.load_registry(self.workspace)["namespace"], registry["namespace"])

    def test_write_ahead_failure_never_touches_vault(self):
        """無法保存可恢復的參照時，原生憑證完全不變。"""

        with mock.patch.object(CREDENTIAL_STORE, "write_registry", side_effect=OSError):
            with self.assertRaises(OSError):
                CREDENTIAL_STORE.store_secret(self.workspace, "facebook", "app-secret",
                    "fictional-secret", source="oauth-callback", backend=self.backend)
        self.assertFalse(self.backend.values)

    def test_v1_registry_migrates_only_on_confirmed_mutation(self):
        """讀取舊版參照不改檔；經確認的新增才保存新版。"""

        CREDENTIAL_STORE.store_secret(self.workspace, "facebook", "app-secret",
            "fictional-secret", source="oauth-callback", backend=self.backend)
        path = self.workspace / CREDENTIAL_STORE.REGISTRY_RELATIVE
        old = json.loads(path.read_text())
        old["schema_version"] = 1
        path.write_text(json.dumps(old), encoding="utf-8")
        before = path.read_bytes()
        self.assertEqual(CREDENTIAL_STORE.load_registry(self.workspace)["schema_version"], 2)
        self.assertEqual(path.read_bytes(), before)
        CREDENTIAL_STORE.store_secret(self.workspace, "facebook", "page-token",
            "fictional-page-token", source="oauth-callback", backend=self.backend)
        self.assertEqual(json.loads(path.read_text())["schema_version"], 2)

    def test_failed_native_write_is_not_available(self):
        """原生寫入失敗保留可追蹤參照，不算保存成功。"""

        with mock.patch.object(self.backend, "put", side_effect=OSError):
            with self.assertRaises(OSError):
                CREDENTIAL_STORE.store_secret(self.workspace, "facebook", "app-secret",
                    "fictional-secret", source="oauth-callback", backend=self.backend)
        state = CREDENTIAL_STORE.credential_status(self.workspace, backend=self.backend)["entries"][0]
        self.assertFalse(state["available"])
        self.assertFalse(state["stored"])
        self.assertEqual(state["status"], "pending_write")
        self.assertIsNone(state["last_verified_at"])

    def test_delete_interruption_can_finish_without_second_delete(self):
        """刪除完成但參照未提交時，再確認只清理該筆參照。"""

        CREDENTIAL_STORE.store_secret(self.workspace, "facebook", "app-secret",
            "fictional-secret", source="oauth-callback", backend=self.backend)
        original = CREDENTIAL_STORE.write_registry
        def fail_final(workspace, payload):
            if not payload["entries"]:
                raise OSError("fictional interruption")
            return original(workspace, payload)
        with mock.patch.object(CREDENTIAL_STORE, "write_registry", side_effect=fail_final):
            with self.assertRaises(OSError):
                CREDENTIAL_STORE.remove_secret(self.workspace, "facebook", "app-secret",
                    confirmed=True, backend=self.backend)
        with mock.patch.object(self.backend, "delete", side_effect=AssertionError("不得重刪")):
            self.assertEqual(CREDENTIAL_STORE.remove_secret(self.workspace, "facebook", "app-secret",
                confirmed=True, backend=self.backend)["status"], "deleted")

    def test_broken_symlink_and_lock_contention_stop(self):
        """失效 symlink 與同時寫入都必須在碰憑證庫前停止。"""

        path = self.workspace / CREDENTIAL_STORE.REGISTRY_RELATIVE
        path.parent.mkdir(parents=True)
        path.symlink_to(self.workspace / "missing.json")
        with self.assertRaises(CREDENTIAL_STORE.CredentialStoreError):
            CREDENTIAL_STORE.load_registry(self.workspace)
        path.unlink()
        with CREDENTIAL_STORE.workspace_lock(self.workspace):
            with self.assertRaises(CREDENTIAL_STORE.CredentialStoreError):
                CREDENTIAL_STORE.store_secret(self.workspace, "facebook", "app-secret",
                    "fictional-secret", source="oauth-callback", backend=self.backend)
        self.assertFalse(self.backend.values)

    def test_hidden_input_never_falls_back_to_echo(self):
        """無法停用回顯時停止，不能接受不安全輸入。"""

        args = Namespace(workspace_root=str(self.workspace), platform="facebook",
                         name="app-secret", confirm_replace=False)
        with mock.patch.object(sys.stdin, "isatty", return_value=True), mock.patch.object(
            sys.stderr, "isatty", return_value=True), mock.patch.object(
            CREDENTIAL_STORE.getpass, "getpass", side_effect=CREDENTIAL_STORE.getpass.GetPassWarning), mock.patch.object(
            CREDENTIAL_STORE, "detect_backend", return_value=self.backend):
            with self.assertRaises(CREDENTIAL_STORE.CredentialStoreError):
                CREDENTIAL_STORE.interactive_put(args)
        self.assertFalse(self.backend.values)

    @unittest.skipUnless(sys.platform == "darwin" and os.environ.get("SOCIAL_NATIVE_ACCEPTANCE") == "1",
                         "實機驗收延後；預設不存取原生憑證庫")
    def test_macos_framework_loads_and_missing_lookup_is_read_only(self) -> None:
        """確認 Apple Security framework 可載入並安全查詢不存在項目。"""

        backend = CREDENTIAL_STORE.MacOSKeychain()
        target = f"ai-workflow-toolbox.social-media.test-{uuid.uuid4().hex}"
        self.assertFalse(backend.exists(target))


if __name__ == "__main__":
    unittest.main()
