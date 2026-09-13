#!/usr/bin/env python3
"""以作業系統原生憑證庫保存社群平台 API 憑證。"""

from __future__ import annotations

import argparse
import ctypes
import getpass
import hmac
import json
import os
import re
import secrets
import sys
import tempfile
import warnings
from contextlib import contextmanager
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


REGISTRY_RELATIVE = Path(".local/social-media/credential-references.json")
REGISTRY_SCHEMA_VERSION = 2
PLATFORMS = {"youtube", "instagram", "facebook", "threads", "substack"}
BACKEND_NAMES = {"macos-keychain", "windows-credential-manager"}
SOURCE_NAMES = {"interactive-terminal", "oauth-callback", "agent-generated", "controlled-browser"}
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
NAMESPACE_PATTERN = re.compile(r"^[0-9a-f]{32}$")
ENTRY_KEY_PATTERN = re.compile(
    r"^(youtube|instagram|facebook|threads|substack)/[a-z][a-z0-9-]{0,63}$"
)
MAX_SECRET_BYTES = 5 * 512
SERVICE_PREFIX = "ai-workflow-toolbox.social-media"
SERVICE_ACCOUNT = "ai-workflow-toolbox"


class CredentialStoreError(RuntimeError):
    """代表憑證庫作業無法安全完成。"""


class CredentialNotFound(CredentialStoreError):
    """代表指定的憑證不存在。"""


class CredentialBackend(Protocol):
    """定義原生憑證庫需要提供的最小介面。"""

    name: str

    def exists(self, target: str) -> bool:
        """回報目標憑證是否存在，不顯示內容。"""

    def put(self, target: str, value: str, *, replace: bool) -> None:
        """新增或明確取代一筆憑證。"""

    def read(self, target: str) -> str:
        """讀取憑證供受信任的本機 adapter 使用。"""

    def delete(self, target: str) -> None:
        """刪除一筆已知憑證。"""


class MacOSKeychain:
    """透過 Apple Security framework 存取登入鑰匙圈。"""

    name = "macos-keychain"
    err_success = 0
    err_item_not_found = -25300
    cf_string_encoding_utf8 = 0x08000100

    def __init__(self) -> None:
        """載入 macOS 內建框架與必要 CFType 常數。"""

        if sys.platform != "darwin":
            raise CredentialStoreError("macOS Keychain 只能在 macOS 使用")
        security_path = "/System/Library/Frameworks/Security.framework/Security"
        core_path = "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
        try:
            self.security = ctypes.CDLL(security_path)
            self.core = ctypes.CDLL(core_path)
        except OSError as error:
            raise CredentialStoreError("找不到 macOS Security framework") from error

        self.core.CFStringCreateWithCString.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_uint32,
        ]
        self.core.CFStringCreateWithCString.restype = ctypes.c_void_p
        self.core.CFDataCreate.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.c_long,
        ]
        self.core.CFDataCreate.restype = ctypes.c_void_p
        self.core.CFDictionaryCreate.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_long,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        self.core.CFDictionaryCreate.restype = ctypes.c_void_p
        self.core.CFDataGetLength.argtypes = [ctypes.c_void_p]
        self.core.CFDataGetLength.restype = ctypes.c_long
        self.core.CFDataGetBytePtr.argtypes = [ctypes.c_void_p]
        self.core.CFDataGetBytePtr.restype = ctypes.POINTER(ctypes.c_ubyte)
        self.core.CFRelease.argtypes = [ctypes.c_void_p]
        self.core.CFRelease.restype = None

        self.security.SecItemAdd.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self.security.SecItemAdd.restype = ctypes.c_int32
        self.security.SecItemUpdate.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.security.SecItemUpdate.restype = ctypes.c_int32
        self.security.SecItemCopyMatching.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self.security.SecItemCopyMatching.restype = ctypes.c_int32
        self.security.SecItemDelete.argtypes = [ctypes.c_void_p]
        self.security.SecItemDelete.restype = ctypes.c_int32

        self.k_sec_class = self._constant(self.security, "kSecClass")
        self.k_sec_class_generic_password = self._constant(
            self.security, "kSecClassGenericPassword"
        )
        self.k_sec_attr_service = self._constant(self.security, "kSecAttrService")
        self.k_sec_attr_account = self._constant(self.security, "kSecAttrAccount")
        self.k_sec_value_data = self._constant(self.security, "kSecValueData")
        self.k_sec_return_data = self._constant(self.security, "kSecReturnData")
        self.k_sec_match_limit = self._constant(self.security, "kSecMatchLimit")
        self.k_sec_match_limit_one = self._constant(
            self.security, "kSecMatchLimitOne"
        )
        self.k_cf_boolean_true = self._constant(self.core, "kCFBooleanTrue")

    @staticmethod
    def _constant(library: Any, name: str) -> int:
        """讀取框架輸出的 CFTypeRef 常數。"""

        value = ctypes.c_void_p.in_dll(library, name).value
        if value is None:
            raise CredentialStoreError(f"macOS framework 缺少必要常數 {name}")
        return value

    def _string(self, value: str) -> int:
        """建立由呼叫端負責釋放的 CFString。"""

        reference = self.core.CFStringCreateWithCString(
            None, value.encode("utf-8"), self.cf_string_encoding_utf8
        )
        if not reference:
            raise CredentialStoreError("macOS Keychain 無法建立文字參數")
        return reference

    def _data(self, value: bytes) -> int:
        """建立會複製內容的 CFData。"""

        buffer = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
        reference = self.core.CFDataCreate(None, buffer, len(value))
        if not reference:
            raise CredentialStoreError("macOS Keychain 無法建立秘密資料")
        return reference

    def _dictionary(self, pairs: list[tuple[int, int]]) -> int:
        """建立短生命週期 CFDictionary；所有 key/value 在呼叫期間保持有效。"""

        keys = (ctypes.c_void_p * len(pairs))(*(key for key, _ in pairs))
        values = (ctypes.c_void_p * len(pairs))(*(value for _, value in pairs))
        reference = self.core.CFDictionaryCreate(
            None, keys, values, len(pairs), None, None
        )
        if not reference:
            raise CredentialStoreError("macOS Keychain 無法建立查詢")
        return reference

    def _match_query(self, target: str) -> tuple[int, list[int]]:
        """建立以 service 與 account 唯一定位的查詢。"""

        service = self._string(target)
        account = self._string(SERVICE_ACCOUNT)
        query = self._dictionary(
            [
                (self.k_sec_class, self.k_sec_class_generic_password),
                (self.k_sec_attr_service, service),
                (self.k_sec_attr_account, account),
            ]
        )
        return query, [service, account]

    def _release_all(self, references: list[int]) -> None:
        """釋放此類別建立的 Core Foundation 物件。"""

        for reference in reversed(references):
            if reference:
                self.core.CFRelease(reference)

    def exists(self, target: str) -> bool:
        """查詢項目是否存在，不輸出內容。"""

        try:
            self.read(target)
        except CredentialNotFound:
            return False
        return True

    def put(self, target: str, value: str, *, replace: bool) -> None:
        """以 SecItemAdd／SecItemUpdate 寫入，不建立含秘密的 argv。"""

        query, query_values = self._match_query(target)
        data = self._data(value.encode("utf-8"))
        try:
            present = self.exists(target)
            if present and not replace:
                raise CredentialStoreError("指定憑證已存在；必須明確確認取代")
            if present:
                attributes = self._dictionary([(self.k_sec_value_data, data)])
                try:
                    status = self.security.SecItemUpdate(query, attributes)
                finally:
                    self._release_all([attributes])
            else:
                add_query = self._dictionary(
                    [
                        (self.k_sec_class, self.k_sec_class_generic_password),
                        (self.k_sec_attr_service, query_values[0]),
                        (self.k_sec_attr_account, query_values[1]),
                        (self.k_sec_value_data, data),
                    ]
                )
                try:
                    status = self.security.SecItemAdd(add_query, None)
                finally:
                    self._release_all([add_query])
            if status != self.err_success:
                raise CredentialStoreError(
                    f"macOS Keychain 寫入失敗（OSStatus {status}）"
                )
        finally:
            self._release_all([query, *query_values, data])

    def read(self, target: str) -> str:
        """以 SecItemCopyMatching 讀取，秘密只留在程序記憶體。"""

        query, query_values = self._match_query(target)
        full_query = self._dictionary(
            [
                (self.k_sec_class, self.k_sec_class_generic_password),
                (self.k_sec_attr_service, query_values[0]),
                (self.k_sec_attr_account, query_values[1]),
                (self.k_sec_return_data, self.k_cf_boolean_true),
                (self.k_sec_match_limit, self.k_sec_match_limit_one),
            ]
        )
        result = ctypes.c_void_p()
        try:
            status = self.security.SecItemCopyMatching(
                full_query, ctypes.byref(result)
            )
            if status == self.err_item_not_found:
                raise CredentialNotFound("macOS Keychain 中找不到指定憑證")
            if status != self.err_success or not result.value:
                raise CredentialStoreError(
                    f"macOS Keychain 讀取失敗（OSStatus {status}）"
                )
            length = self.core.CFDataGetLength(result.value)
            pointer = self.core.CFDataGetBytePtr(result.value)
            raw = ctypes.string_at(pointer, length)
        finally:
            if result.value:
                self.core.CFRelease(result.value)
            self._release_all([query, full_query, *query_values])
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise CredentialStoreError("macOS Keychain 憑證不是有效 UTF-8") from error

    def delete(self, target: str) -> None:
        """以 SecItemDelete 刪除唯一匹配項目。"""

        query, query_values = self._match_query(target)
        try:
            status = self.security.SecItemDelete(query)
        finally:
            self._release_all([query, *query_values])
        if status != self.err_success:
            raise CredentialStoreError(
                f"macOS Keychain 刪除失敗（OSStatus {status}）；保留 registry 供人工檢查"
            )


class WindowsCredentialManager:
    """透過 Windows WinCred API 保存目前登入使用者的 generic credential。"""

    name = "windows-credential-manager"
    credential_type_generic = 1
    persist_local_machine = 2
    error_not_found = 1168

    def __init__(self) -> None:
        """延後載入 Windows DLL，避免其他平台匯入時失敗。"""

        if os.name != "nt":
            raise CredentialStoreError("Windows Credential Manager 只能在 Windows 使用")

        from ctypes import wintypes

        class Credential(ctypes.Structure):
            """對應 WinCred 的 CREDENTIALW 結構。"""

            _fields_ = [
                ("Flags", wintypes.DWORD),
                ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR),
                ("Comment", wintypes.LPWSTR),
                ("LastWritten", wintypes.FILETIME),
                ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", wintypes.DWORD),
                ("AttributeCount", wintypes.DWORD),
                ("Attributes", ctypes.c_void_p),
                ("TargetAlias", wintypes.LPWSTR),
                ("UserName", wintypes.LPWSTR),
            ]

        self.credential_class = Credential
        self.api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        self.api.CredWriteW.argtypes = [ctypes.POINTER(Credential), wintypes.DWORD]
        self.api.CredWriteW.restype = wintypes.BOOL
        self.api.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(Credential)),
        ]
        self.api.CredReadW.restype = wintypes.BOOL
        self.api.CredDeleteW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
        ]
        self.api.CredDeleteW.restype = wintypes.BOOL
        self.api.CredFree.argtypes = [ctypes.c_void_p]
        self.api.CredFree.restype = None

    def _read_pointer(self, target: str) -> Any:
        """取得 WinCred 配置的指標，交由呼叫端釋放。"""

        pointer = ctypes.POINTER(self.credential_class)()
        succeeded = self.api.CredReadW(
            target,
            self.credential_type_generic,
            0,
            ctypes.byref(pointer),
        )
        if not succeeded:
            code = ctypes.get_last_error()
            if code == self.error_not_found:
                raise CredentialNotFound("Windows Credential Manager 中找不到指定憑證")
            raise CredentialStoreError(
                f"Windows Credential Manager 讀取失敗（系統錯誤碼 {code}）"
            )
        return pointer

    def exists(self, target: str) -> bool:
        """查詢憑證存在性並立即釋放系統記憶體。"""

        try:
            pointer = self._read_pointer(target)
        except CredentialNotFound:
            return False
        self.api.CredFree(pointer)
        return True

    def put(self, target: str, value: str, *, replace: bool) -> None:
        """新增或取代同一 TargetName 的 generic credential。"""

        if not replace and self.exists(target):
            raise CredentialStoreError("指定憑證已存在；必須明確確認取代")
        encoded = value.encode("utf-8")
        buffer = (ctypes.c_ubyte * len(encoded)).from_buffer_copy(encoded)
        credential = self.credential_class()
        credential.Flags = 0
        credential.Type = self.credential_type_generic
        credential.TargetName = target
        credential.Comment = "AI Workflow Toolbox social media credential"
        credential.CredentialBlobSize = len(encoded)
        credential.CredentialBlob = ctypes.cast(
            buffer, ctypes.POINTER(ctypes.c_ubyte)
        )
        credential.Persist = self.persist_local_machine
        credential.AttributeCount = 0
        credential.Attributes = None
        credential.TargetAlias = None
        credential.UserName = SERVICE_ACCOUNT
        if not self.api.CredWriteW(ctypes.byref(credential), 0):
            code = ctypes.get_last_error()
            raise CredentialStoreError(
                f"Windows Credential Manager 寫入失敗（系統錯誤碼 {code}）"
            )

    def read(self, target: str) -> str:
        """讀取應用程式自訂的 UTF-8 credential blob。"""

        pointer = self._read_pointer(target)
        try:
            credential = pointer.contents
            raw = ctypes.string_at(
                credential.CredentialBlob, credential.CredentialBlobSize
            )
        finally:
            self.api.CredFree(pointer)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise CredentialStoreError(
                "Windows Credential Manager 憑證不是有效 UTF-8"
            ) from error

    def delete(self, target: str) -> None:
        """刪除已由 registry 唯一指向的 generic credential。"""

        if not self.api.CredDeleteW(target, self.credential_type_generic, 0):
            code = ctypes.get_last_error()
            raise CredentialStoreError(
                f"Windows Credential Manager 刪除失敗（系統錯誤碼 {code}）"
            )


def utc_now() -> str:
    """回傳穩定的 UTC ISO 時間。"""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_reference(platform: str, name: str) -> tuple[str, str]:
    """限制平台與憑證名稱，避免目標名稱注入。"""

    normalized_platform = platform.strip().lower()
    normalized_name = name.strip().lower()
    if normalized_platform not in PLATFORMS:
        raise CredentialStoreError("不支援的社群平台")
    if not NAME_PATTERN.fullmatch(normalized_name):
        raise CredentialStoreError("憑證名稱只能使用小寫英文字母、數字與連字號")
    return normalized_platform, normalized_name


def validate_secret(value: str) -> None:
    """拒絕空值、控制字元與超過 Windows 原生上限的內容。"""

    if not value:
        raise CredentialStoreError("憑證不可為空")
    if "\x00" in value or "\n" in value or "\r" in value:
        raise CredentialStoreError("憑證不可包含 NUL 或換行字元")
    if len(value.encode("utf-8")) > MAX_SECRET_BYTES:
        raise CredentialStoreError(
            f"憑證超過跨平台安全上限 {MAX_SECRET_BYTES} bytes"
        )


def resolve_workspace(value: str | Path) -> Path:
    """要求使用者明確指定已存在、非 symlink 的工作區。"""

    supplied = Path(value).expanduser()
    if supplied.is_symlink():
        raise CredentialStoreError("工作區根目錄不得是 symlink")
    try:
        resolved = supplied.resolve(strict=True)
    except FileNotFoundError as error:
        raise CredentialStoreError("指定工作區不存在") from error
    if not resolved.is_dir():
        raise CredentialStoreError("指定工作區不是目錄")
    return resolved


def registry_path(workspace_root: Path) -> Path:
    """建立 registry 路徑並拒絕既有 symlink 元件。"""

    current = workspace_root
    for part in REGISTRY_RELATIVE.parts:
        current = current / part
        if current.is_symlink():
            raise CredentialStoreError("憑證參照路徑不得包含 symlink")
    return workspace_root / REGISTRY_RELATIVE


def validate_registry(payload: Any) -> dict[str, Any]:
    """驗證本機參照檔只含非敏感欄位。"""

    if not isinstance(payload, dict):
        raise CredentialStoreError("憑證參照檔格式錯誤")
    required = {
        "schema_version",
        "namespace",
        "backend",
        "entries",
        "contains_credentials",
    }
    if set(payload) != required:
        raise CredentialStoreError("憑證參照檔欄位不符")
    if payload["schema_version"] not in (1, REGISTRY_SCHEMA_VERSION):
        raise CredentialStoreError("憑證參照檔版本不支援")
    if not isinstance(payload["namespace"], str) or not NAMESPACE_PATTERN.fullmatch(
        payload["namespace"]
    ):
        raise CredentialStoreError("憑證參照 namespace 無效")
    if payload["backend"] not in BACKEND_NAMES:
        raise CredentialStoreError("憑證參照 backend 無效")
    if payload["contains_credentials"] is not False:
        raise CredentialStoreError("憑證參照檔不得包含秘密")
    if not isinstance(payload["entries"], dict):
        raise CredentialStoreError("憑證參照 entries 必須是物件")
    for key, entry in payload["entries"].items():
        if not isinstance(key, str) or not ENTRY_KEY_PATTERN.fullmatch(key):
            raise CredentialStoreError("憑證參照 entry 名稱無效")
        if not isinstance(entry, dict) or set(entry) != {
            "platform",
            "name",
            "source",
            "status",
            "updated_at",
        }:
            raise CredentialStoreError("憑證參照 entry 欄位不符")
        platform, name = key.split("/", 1)
        if entry["platform"] != platform or entry["name"] != name:
            raise CredentialStoreError("憑證參照 entry 與索引不一致")
        allowed = {"verified"} if payload["schema_version"] == 1 else {
            "verified", "pending_write", "pending_delete"
        }
        if entry["source"] not in SOURCE_NAMES or entry["status"] not in allowed:
            raise CredentialStoreError("憑證參照 entry 狀態無效")
        if not isinstance(entry["updated_at"], str) or "T" not in entry["updated_at"]:
            raise CredentialStoreError("憑證參照 entry 時間無效")
    return payload


def load_registry(workspace_root: Path) -> dict[str, Any] | None:
    """讀取既有 registry；不存在時回傳 None。"""

    path = registry_path(workspace_root)
    if not path.exists():
        return None
    if not path.is_file():
        raise CredentialStoreError("憑證參照目標不是一般檔案")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CredentialStoreError("無法讀取憑證參照檔") from error
    validate_registry(payload)
    # 舊版只在記憶體升級；下次經確認的變更才落盤。
    payload["schema_version"] = REGISTRY_SCHEMA_VERSION
    return payload


@contextmanager
def workspace_lock(workspace_root: str | Path, lock_name="credential-store.lock"):
    """以作業系統鎖防止兩個程序同時修改；程序結束會自動釋放。"""

    workspace = resolve_workspace(workspace_root)
    parent = registry_path(workspace).parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if lock_name not in {"credential-store.lock", "oauth-runtime.lock"}:
        raise CredentialStoreError("不支援的鎖名稱")
    path = parent / lock_name
    if path.is_symlink():
        raise CredentialStoreError("憑證鎖不得是 symlink")
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "r+b") as handle:
        # Windows 鎖定一個固定 byte；內容不包含任何秘密。
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise CredentialStoreError("另一個憑證作業進行中；請稍後重新檢查") from None
        try:
            yield workspace
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def serialized(function):
    """把同一工作區的修改限制為單一程序。"""

    @wraps(function)
    def guarded(workspace_root, *args, **kwargs):
        with workspace_lock(workspace_root):
            return function(workspace_root, *args, **kwargs)
    return guarded


def new_registry(backend_name: str) -> dict[str, Any]:
    """建立不含任何秘密的新 registry。"""

    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "namespace": secrets.token_hex(16),
        "backend": backend_name,
        "entries": {},
        "contains_credentials": False,
    }


def write_registry(workspace_root: Path, payload: dict[str, Any]) -> None:
    """以原子替換寫入非敏感 registry。"""

    validate_registry(payload)
    path = registry_path(workspace_root)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if parent.is_symlink() or not parent.resolve(strict=True).is_relative_to(workspace_root):
        raise CredentialStoreError("憑證參照目錄不在指定工作區內")
    content = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".credential-references.", dir=parent
    )
    temporary_path = Path(temporary_name)
    try:
        if os.name == "posix":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def detect_backend() -> CredentialBackend:
    """依作業系統選擇不需第三方套件的預設憑證庫。"""

    if sys.platform == "darwin":
        return MacOSKeychain()
    if os.name == "nt":
        return WindowsCredentialManager()
    raise CredentialStoreError(
        "目前 MVP 只支援 macOS Keychain 與 Windows Credential Manager；不得退回明文檔案"
    )


def ensure_registry_backend(
    registry: dict[str, Any] | None, backend: CredentialBackend
) -> dict[str, Any]:
    """避免同一 registry 在未確認下切換原生憑證庫。"""

    if registry is None:
        return new_registry(backend.name)
    if registry["backend"] != backend.name:
        raise CredentialStoreError("工作區記錄的憑證庫與目前作業系統不一致")
    return registry


def target_name(registry: dict[str, Any], platform: str, name: str) -> str:
    """從非敏感 namespace 產生穩定的原生憑證目標名稱。"""

    return f"{SERVICE_PREFIX}.{registry['namespace']}.{platform}.{name}"


@serialized
def store_secret(
    workspace_root: str | Path,
    platform: str,
    name: str,
    value: str,
    *,
    source: str,
    replace: bool = False,
    backend: CredentialBackend | None = None,
) -> dict[str, Any]:
    """保存後立即讀回比對，只回傳不含秘密的結果。"""

    normalized_platform, normalized_name = validate_reference(platform, name)
    validate_secret(value)
    if source not in SOURCE_NAMES:
        raise CredentialStoreError("不支援的憑證來源")
    workspace = resolve_workspace(workspace_root)
    selected_backend = backend or detect_backend()
    registry = ensure_registry_backend(load_registry(workspace), selected_backend)
    key = f"{normalized_platform}/{normalized_name}"
    target = target_name(registry, normalized_platform, normalized_name)
    already_exists = selected_backend.exists(target)
    if (already_exists or key in registry["entries"]) and not replace:
        raise CredentialStoreError("指定憑證已存在；取代前必須重新預覽並確認")
    # 先保留 namespace 與未完成狀態，再碰原生儲存。失敗後不會遺失目標。
    registry["entries"][key] = {
        "platform": normalized_platform,
        "name": normalized_name,
        "source": source,
        "status": "pending_write",
        "updated_at": utc_now(),
    }
    write_registry(workspace, registry)
    selected_backend.put(target, value, replace=already_exists or replace)
    stored_value = selected_backend.read(target)
    if not hmac.compare_digest(stored_value.encode("utf-8"), value.encode("utf-8")):
        raise CredentialStoreError("憑證讀回比對失敗；保留 pending_write，不得直接重送")
    registry["entries"][key]["status"] = "verified"
    registry["entries"][key]["updated_at"] = utc_now()
    write_registry(workspace, registry)
    return {
        "platform": normalized_platform,
        "name": normalized_name,
        "backend": selected_backend.name,
        "status": "verified",
        "registry": REGISTRY_RELATIVE.as_posix(),
        "contains_credentials": False,
    }


def load_secret(
    workspace_root: str | Path,
    platform: str,
    name: str,
    *,
    backend: CredentialBackend | None = None,
) -> str:
    """供受信任的社群平台 adapter 取用；呼叫端不得列印回傳值。"""

    normalized_platform, normalized_name = validate_reference(platform, name)
    workspace = resolve_workspace(workspace_root)
    selected_backend = backend or detect_backend()
    registry = ensure_registry_backend(load_registry(workspace), selected_backend)
    key = f"{normalized_platform}/{normalized_name}"
    if key not in registry["entries"]:
        raise CredentialNotFound("本機 registry 沒有指定憑證參照")
    if registry["entries"][key]["status"] != "verified":
        raise CredentialStoreError("憑證作業尚未完成；必須先確認恢復，不得交給平台使用")
    value = selected_backend.read(
        target_name(registry, normalized_platform, normalized_name)
    )
    validate_secret(value)
    return value


def credential_status(
    workspace_root: str | Path,
    *,
    backend: CredentialBackend | None = None,
) -> dict[str, Any]:
    """列出非敏感參照與可用性，不回傳或顯示秘密。"""

    workspace = resolve_workspace(workspace_root)
    selected_backend = backend or detect_backend()
    registry = load_registry(workspace)
    if registry is None:
        return {
            "backend": selected_backend.name,
            "registry": REGISTRY_RELATIVE.as_posix(),
            "entries": [],
            "contains_credentials": False,
        }
    registry = ensure_registry_backend(registry, selected_backend)
    entries = []
    for key in sorted(registry["entries"]):
        entry = registry["entries"][key]
        available = selected_backend.exists(
            target_name(registry, entry["platform"], entry["name"])
        )
        entries.append(
            {
                "platform": entry["platform"],
                "name": entry["name"],
                "available": available and entry["status"] == "verified",
                "stored": available,
                "status": entry["status"],
                "last_verified_at": entry["updated_at"] if entry["status"] == "verified" else None,
            }
        )
    return {
        "backend": selected_backend.name,
        "registry": REGISTRY_RELATIVE.as_posix(),
        "entries": entries,
        "contains_credentials": False,
    }


@serialized
def remove_secret(
    workspace_root: str | Path,
    platform: str,
    name: str,
    *,
    confirmed: bool,
    backend: CredentialBackend | None = None,
) -> dict[str, Any]:
    """取得明確確認後刪除單一憑證及其參照。"""

    if not confirmed:
        raise CredentialStoreError("缺少 --confirm-delete；未刪除任何憑證")
    normalized_platform, normalized_name = validate_reference(platform, name)
    workspace = resolve_workspace(workspace_root)
    selected_backend = backend or detect_backend()
    registry = ensure_registry_backend(load_registry(workspace), selected_backend)
    key = f"{normalized_platform}/{normalized_name}"
    if key not in registry["entries"]:
        raise CredentialNotFound("本機 registry 沒有指定憑證參照")
    registry["entries"][key]["status"] = "pending_delete"
    registry["entries"][key]["updated_at"] = utc_now()
    write_registry(workspace, registry)
    target = target_name(registry, normalized_platform, normalized_name)
    if selected_backend.exists(target):
        selected_backend.delete(target)
    if selected_backend.exists(target):
        raise CredentialStoreError("刪除讀回仍存在；保留 pending_delete，不得標示成功")
    del registry["entries"][key]
    write_registry(workspace, registry)
    return {
        "platform": normalized_platform,
        "name": normalized_name,
        "backend": selected_backend.name,
        "status": "deleted",
        "contains_credentials": False,
    }


@serialized
def recover_secret(workspace_root, platform, name, value, *, confirmed, backend=None):
    """以原值比對未完成寫入；不重新寫入憑證庫、不用存在性猜成功。"""

    if not confirmed:
        raise CredentialStoreError("恢復憑證參照需要明確確認")
    platform, name = validate_reference(platform, name)
    validate_secret(value)
    workspace = resolve_workspace(workspace_root)
    selected = backend or detect_backend()
    registry = ensure_registry_backend(load_registry(workspace), selected)
    entry = registry["entries"].get(f"{platform}/{name}")
    if entry is None or entry["status"] != "pending_write":
        raise CredentialStoreError("指定憑證沒有待恢復的寫入")
    actual = selected.read(target_name(registry, platform, name))
    if not hmac.compare_digest(actual.encode("utf-8"), value.encode("utf-8")):
        raise CredentialStoreError("恢復比對不一致；保留未完成狀態，不覆蓋憑證")
    entry.update(status="verified", updated_at=utc_now())
    write_registry(workspace, registry)
    return {"platform": platform, "name": name, "backend": selected.name,
            "status": "verified", "contains_credentials": False}


def interactive_put(args: argparse.Namespace) -> dict[str, Any]:
    """只在可見互動式 Terminal 接受不回顯的貼上內容。"""

    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise CredentialStoreError(
            "憑證輸入必須在可見的互動式 Terminal 執行；不得從命令列參數、pipe 或對話傳入"
        )
    platform, name = validate_reference(args.platform, args.name)
    selected_backend = detect_backend()
    workspace = resolve_workspace(args.workspace_root)
    registry = ensure_registry_backend(load_registry(workspace), selected_backend)
    recovering = getattr(args, "command", "put") == "recover"
    if recovering and not args.confirm_recovery:
        raise CredentialStoreError("恢復前必須確認；尚未要求秘密輸入")
    if not recovering and f"{platform}/{name}" in registry["entries"] and not args.confirm_replace:
        raise CredentialStoreError("同名憑證已存在；先確認取代，不要求重貼")
    # 貼上後的 Enter 就是保存確認，不再要求第二次輸入或確認。
    action = "比對恢復" if recovering else "儲存"
    prompt = f"請貼上 {platform} 的 {name}（輸入不回顯；按 Enter 即確認{action}，Ctrl+C 取消）："
    try:
        with warnings.catch_warnings():
            # getpass 無法關閉回顯時不得降級成普通輸入。
            warnings.simplefilter("error", getpass.GetPassWarning)
            value = getpass.getpass(prompt)
    except (getpass.GetPassWarning, EOFError, KeyboardInterrupt):
        raise CredentialStoreError("隱藏輸入取消或不可用；未保存憑證") from None
    try:
        if recovering:
            return recover_secret(args.workspace_root, platform, name, value,
                                  confirmed=args.confirm_recovery, backend=selected_backend)
        return store_secret(
            args.workspace_root,
            platform,
            name,
            value,
            source="interactive-terminal",
            replace=args.confirm_replace,
            backend=selected_backend,
        )
    finally:
        del value


def build_parser() -> argparse.ArgumentParser:
    """建立不接受秘密命令列參數的 CLI。"""

    parser = argparse.ArgumentParser(
        description="以 macOS Keychain 或 Windows Credential Manager 保存社群 API 憑證"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="預覽預設憑證庫")
    inspect_parser.add_argument("--workspace-root", required=True)

    status_parser = subparsers.add_parser("status", help="檢查非敏感參照與存在性")
    status_parser.add_argument("--workspace-root", required=True)

    put_parser = subparsers.add_parser("put", help="在隱藏提示中貼上並保存一筆憑證")
    put_parser.add_argument("--workspace-root", required=True)
    put_parser.add_argument("--platform", required=True, choices=sorted(PLATFORMS))
    put_parser.add_argument("--name", required=True)
    put_parser.add_argument("--confirm-replace", action="store_true")

    recover_parser = subparsers.add_parser("recover", help="隱藏輸入原值並比對未完成寫入")
    recover_parser.add_argument("--workspace-root", required=True)
    recover_parser.add_argument("--platform", required=True, choices=sorted(PLATFORMS))
    recover_parser.add_argument("--name", required=True)
    recover_parser.add_argument("--confirm-recovery", action="store_true")

    remove_parser = subparsers.add_parser("remove", help="刪除一筆已知憑證")
    remove_parser.add_argument("--workspace-root", required=True)
    remove_parser.add_argument("--platform", required=True, choices=sorted(PLATFORMS))
    remove_parser.add_argument("--name", required=True)
    remove_parser.add_argument("--confirm-delete", action="store_true")
    return parser


def main() -> int:
    """執行 CLI 並確保錯誤輸出不含秘密值。"""

    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            workspace = resolve_workspace(args.workspace_root)
            backend = detect_backend()
            existing = load_registry(workspace)
            if existing is not None:
                ensure_registry_backend(existing, backend)
            result = {
                "backend": backend.name,
                "registry": REGISTRY_RELATIVE.as_posix(),
                "input": "visible-terminal-hidden-prompt",
                "persistent": True,
                "contains_credentials": False,
            }
        elif args.command == "status":
            result = credential_status(args.workspace_root)
        elif args.command in {"put", "recover"}:
            result = interactive_put(args)
        elif args.command == "remove":
            result = remove_secret(
                args.workspace_root,
                args.platform,
                args.name,
                confirmed=args.confirm_delete,
            )
        else:
            parser.error("未知命令")
            return 2
    except (CredentialStoreError, OSError):
        print("憑證庫作業停止；請檢查非敏感 status，勿重送不明作業。", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
