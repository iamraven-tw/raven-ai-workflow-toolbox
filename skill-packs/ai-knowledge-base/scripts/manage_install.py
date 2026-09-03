#!/usr/bin/env python3
"""管理 AI 知識庫自有技能與工作區模板的本機生命週期。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import tomllib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PACKAGE_ROOT / "install.manifest.toml"
STATE_SCHEMA_VERSION = 1


class InstallError(RuntimeError):
    """表示應安全停止、且不應繼續變更檔案的錯誤。"""


def utc_now() -> str:
    """回傳適合寫入狀態檔的 UTC 時間。"""

    return datetime.now(UTC).replace(microsecond=0).isoformat()


def read_manifest(manifest_path: Path) -> tuple[dict[str, Any], Path]:
    """讀取 manifest，並驗證候選版允許被本機管理器使用。"""

    resolved = manifest_path.expanduser().resolve(strict=True)
    with resolved.open("rb") as handle:
        manifest = tomllib.load(handle)

    if manifest.get("schema_version") != 1:
        raise InstallError("不支援的 manifest schema_version。")
    if manifest.get("manifest_type") != "my-real-second-brain-install":
        raise InstallError("manifest_type 不屬於 AI 知識庫技能包。")
    if manifest.get("status") != "ready_for_external_acceptance":
        raise InstallError("候選版尚未標示為可供外部驗收。")
    if manifest.get("installable") is not True:
        raise InstallError("manifest 尚未允許安裝自有技能。")

    installation = manifest.get("installation", {})
    if not installation.get("candidate_version"):
        raise InstallError("manifest 缺少 installation.candidate_version。")
    return manifest, resolved


def sha256_file(file_path: Path) -> str:
    """計算單一檔案的 SHA-256。"""

    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_entry(entry_path: Path) -> str:
    """計算檔案或目錄的可重現雜湊，並拒絕任何 symlink。"""

    if entry_path.is_symlink():
        raise InstallError(f"不接受 symlink：{entry_path}")
    if entry_path.is_file():
        return sha256_file(entry_path)
    if not entry_path.is_dir():
        raise InstallError(f"不是可管理的檔案或目錄：{entry_path}")

    digest = hashlib.sha256()
    for path in sorted(entry_path.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise InstallError(f"不接受 symlink：{path}")
        relative = path.relative_to(entry_path).as_posix().encode("utf-8")
        if path.is_dir():
            digest.update(b"D\0" + relative + b"\0")
        elif path.is_file():
            digest.update(b"F\0" + relative + b"\0")
            digest.update(bytes.fromhex(sha256_file(path)))
        else:
            raise InstallError(f"不接受特殊檔案：{path}")
    return digest.hexdigest()


def path_is_within(path: Path, parent: Path) -> bool:
    """判斷 path 是否等於或位於 parent 之下。"""

    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def safe_source(package_root: Path, relative_path: str) -> Path:
    """解析 manifest 來源，避免跳出技能包目錄。"""

    source = (package_root / relative_path).resolve(strict=True)
    if not path_is_within(source, package_root):
        raise InstallError(f"來源路徑超出技能包：{relative_path}")
    return source


def desired_entries(
    manifest: dict[str, Any], manifest_path: Path
) -> tuple[dict[str, Path], dict[str, str]]:
    """由 manifest 建立五個自有技能的來源與雜湊。"""

    package_root = manifest_path.parent
    entries: dict[str, Path] = {}
    hashes: dict[str, str] = {}
    for skill in manifest.get("skills", []):
        if skill.get("required") is not True:
            continue
        skill_id = skill.get("id")
        source_path = skill.get("source_path")
        if not isinstance(skill_id, str) or not isinstance(source_path, str):
            raise InstallError("required skill 缺少 id 或 source_path。")
        if skill_id in entries:
            raise InstallError(f"重複的技能 ID：{skill_id}")
        source = safe_source(package_root, source_path)
        if source.name != skill_id or not (source / "SKILL.md").is_file():
            raise InstallError(f"技能來源結構不正確：{skill_id}")
        entries[skill_id] = source
        hashes[skill_id] = sha256_entry(source)

    managed = manifest.get("installation", {}).get("managed_entries", [])
    if sorted(entries) != sorted(managed):
        raise InstallError("installation.managed_entries 與 required skills 不一致。")
    if len(entries) != 5:
        raise InstallError("公開候選版應恰好管理五個必要技能。")
    return entries, hashes


def validate_registration(
    manifest: dict[str, Any], registration: str, client_root: Path, state_root: Path
) -> tuple[Path, Path]:
    """核對登錄名稱、官方路徑尾端與狀態位置。"""

    registrations = manifest.get("registrations", {})
    registration_data = registrations.get(registration)
    if not isinstance(registration_data, dict):
        raise InstallError(f"未知的 registration：{registration}")

    expected = registration_data.get("path")
    if not isinstance(expected, str):
        raise InstallError(f"registration 缺少 path：{registration}")
    if expected.startswith("<workspace>"):
        tail = expected.removeprefix("<workspace>")
    elif expected.startswith("$HOME"):
        tail = expected.removeprefix("$HOME")
    else:
        raise InstallError(f"registration path 必須使用公開佔位符：{registration}")

    expected_parts = Path(tail.lstrip("/")).parts
    resolved_client = client_root.expanduser().resolve(strict=False)
    resolved_state = state_root.expanduser().resolve(strict=False)
    if expected_parts and resolved_client.parts[-len(expected_parts) :] != expected_parts:
        raise InstallError(
            f"client-root 與 {registration} 的官方路徑尾端不符：{'/'.join(expected_parts)}"
        )
    if path_is_within(resolved_state, resolved_client):
        raise InstallError("state-root 不得放在 Agent 技能掃描目錄內。")
    return resolved_client, resolved_state


def state_file(state_root: Path, registration: str) -> Path:
    """取得單一登錄的狀態檔位置。"""

    return state_root / "registrations" / f"{registration}.json"


def load_state(file_path: Path) -> dict[str, Any] | None:
    """讀取既有狀態，沒有狀態時回傳 None。"""

    if not file_path.exists():
        return None
    if file_path.is_symlink() or not file_path.is_file():
        raise InstallError(f"狀態路徑不是一般檔案：{file_path}")
    try:
        state = json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise InstallError(f"無法讀取安裝狀態：{error}") from error
    if state.get("schema_version") != STATE_SCHEMA_VERSION:
        raise InstallError("不支援的安裝狀態版本。")
    return state


def write_json_atomic(file_path: Path, payload: dict[str, Any]) -> None:
    """以同一檔案系統的暫存檔原子更新 JSON。"""

    file_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{file_path.name}.", dir=file_path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, file_path)
    finally:
        if temporary.exists():
            temporary.unlink()


def copy_entry(source: Path, target: Path) -> None:
    """複製一個已驗證的技能來源，不跟隨 symlink。"""

    if source.is_dir():
        shutil.copytree(source, target, symlinks=False)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def existing_hashes(client_root: Path, names: list[str]) -> dict[str, str | None]:
    """讀取目前目標內容的雜湊；缺少的項目以 None 表示。"""

    result: dict[str, str | None] = {}
    for name in names:
        target = client_root / name
        result[name] = sha256_entry(target) if target.exists() or target.is_symlink() else None
    return result


def verify_active(client_root: Path, active: dict[str, Any]) -> None:
    """確認受管理內容仍與狀態相同，避免覆蓋使用者修改。"""

    expected = active.get("entries", {})
    if not isinstance(expected, dict) or not expected:
        raise InstallError("安裝狀態缺少 active.entries。")
    actual = existing_hashes(client_root, list(expected))
    changed = [name for name, digest in expected.items() if actual.get(name) != digest]
    if changed:
        raise InstallError(
            "受管理技能已缺少或被修改，為保留內容而停止：" + ", ".join(changed)
        )


def stage_entries(entries: dict[str, Path], transaction_root: Path) -> Path:
    """先把完整候選內容放進狀態目錄中的交易暫存區。"""

    staged = transaction_root / "new"
    staged.mkdir(parents=True)
    for name, source in entries.items():
        copy_entry(source, staged / name)
    return staged


def replace_entries(client_root: Path, names: list[str], staged: Path, transaction_root: Path) -> None:
    """以可復原交易替換目標項目。"""

    old_root = transaction_root / "old"
    old_root.mkdir(parents=True)
    client_root.mkdir(parents=True, exist_ok=True)
    moved_old: list[str] = []
    moved_new: list[str] = []
    try:
        for name in names:
            target = client_root / name
            if target.exists() or target.is_symlink():
                target.replace(old_root / name)
                moved_old.append(name)
        for name in names:
            (staged / name).replace(client_root / name)
            moved_new.append(name)
    except Exception as error:
        for name in reversed(moved_new):
            target = client_root / name
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            elif target.exists() or target.is_symlink():
                target.unlink()
        for name in reversed(moved_old):
            backup = old_root / name
            if backup.exists() or backup.is_symlink():
                backup.replace(client_root / name)
        raise InstallError(f"檔案交易失敗，已回復變更：{error}") from error


def restore_replaced_entries(
    client_root: Path,
    names: list[str],
    expected_new_hashes: dict[str, str],
    transaction_root: Path,
) -> None:
    """狀態寫入失敗時，把剛替換的內容回復成交易前版本。"""

    current = existing_hashes(client_root, names)
    changed = [name for name in names if current.get(name) != expected_new_hashes[name]]
    if changed:
        raise InstallError(
            "新技能在交易完成後又被修改，未自動覆蓋；舊版仍保留於交易目錄："
            + ", ".join(changed)
        )

    old_root = transaction_root / "old"
    for name in names:
        target = client_root / name
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        elif target.exists() or target.is_symlink():
            target.unlink()
    for name in names:
        backup = old_root / name
        if backup.exists() or backup.is_symlink():
            backup.replace(client_root / name)


def create_snapshot(
    state_root: Path, active: dict[str, Any], client_root: Path
) -> dict[str, Any]:
    """建立可供 rollback 使用的完整快照。"""

    snapshot_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    snapshot_root = state_root / "snapshots" / snapshot_id
    content_root = snapshot_root / "content"
    content_root.mkdir(parents=True)
    for name in active["entries"]:
        copy_entry(client_root / name, content_root / name)
    metadata = {
        "snapshot_id": snapshot_id,
        "created_at": utc_now(),
        "version": active["version"],
        "manifest_sha256": active["manifest_sha256"],
        "entries": active["entries"],
    }
    write_json_atomic(snapshot_root / "snapshot.json", metadata)
    return metadata


def new_active(
    version: str, manifest_path: Path, hashes: dict[str, str]
) -> dict[str, Any]:
    """建立不含憑證或使用者內容的 active 狀態。"""

    return {
        "version": version,
        "manifest_sha256": sha256_file(manifest_path),
        "entries": hashes,
        "installed_at": utc_now(),
    }


def base_state(registration: str, client_root: Path) -> dict[str, Any]:
    """建立單一登錄的基礎狀態。"""

    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "registration": registration,
        "client_root": str(client_root),
        "active": None,
        "history": [],
        "removed": [],
    }


def ensure_matching_state(
    state: dict[str, Any], registration: str, client_root: Path
) -> None:
    """避免把另一個目標的狀態誤用於目前登錄。"""

    if state.get("registration") != registration:
        raise InstallError("狀態檔 registration 與目前命令不符。")
    if state.get("client_root") != str(client_root):
        raise InstallError("狀態檔 client_root 與目前命令不符。")


def install_or_update(args: argparse.Namespace, *, update: bool) -> dict[str, Any]:
    """執行正常安裝或明確更新。"""

    manifest, manifest_path = read_manifest(Path(args.manifest))
    client_root, state_root = validate_registration(
        manifest, args.registration, Path(args.client_root), Path(args.state_root)
    )
    entries, hashes = desired_entries(manifest, manifest_path)
    version = str(manifest["installation"]["candidate_version"])
    file_path = state_file(state_root, args.registration)
    state = load_state(file_path)
    names = list(entries)
    actual = existing_hashes(client_root, names)

    if state is None:
        if update:
            raise InstallError("找不到既有安裝；請先使用 install。")
        present = [name for name, digest in actual.items() if digest is not None]
        if present and actual != hashes:
            raise InstallError("目標已有未知或不完整的同名技能，未進行任何變更。")
        state = base_state(args.registration, client_root)
        if actual == hashes:
            state["active"] = new_active(version, manifest_path, hashes)
            write_json_atomic(file_path, state)
            return {"result": "adopted_identical", "version": version}
    else:
        ensure_matching_state(state, args.registration, client_root)
        active = state.get("active")
        if active:
            verify_active(client_root, active)
            same = active.get("version") == version and active.get("entries") == hashes
            if same:
                return {"result": "noop", "version": version, "verification": "hashes_match"}
            if not update:
                raise InstallError("候選版本或內容不同；請先檢查差異，再明確使用 update。")
        elif update:
            raise InstallError("目前狀態已移除；請使用 install 重新安裝。")

    transaction_root = state_root / "transactions" / uuid.uuid4().hex
    preserve_transaction = False
    snapshot: dict[str, Any] | None = None
    try:
        staged = stage_entries(entries, transaction_root)
        active = state.get("active")
        if active:
            snapshot = create_snapshot(state_root, active, client_root)
            state.setdefault("history", []).append(snapshot)
        replace_entries(client_root, names, staged, transaction_root)
        state["active"] = new_active(version, manifest_path, hashes)
        try:
            write_json_atomic(file_path, state)
        except Exception as state_error:
            try:
                restore_replaced_entries(client_root, names, hashes, transaction_root)
            except Exception as restore_error:
                preserve_transaction = True
                raise InstallError(
                    "狀態寫入失敗且自動回復未完成；交易備份保留於 "
                    f"{transaction_root}：{restore_error}"
                ) from state_error
            if snapshot is not None:
                snapshot_dir = state_root / "snapshots" / str(snapshot["snapshot_id"])
                if snapshot_dir.exists():
                    shutil.rmtree(snapshot_dir)
            raise InstallError(f"狀態寫入失敗，已回復技能變更：{state_error}") from state_error
    finally:
        if transaction_root.exists() and not preserve_transaction:
            shutil.rmtree(transaction_root)

    if update:
        result = "updated"
    elif state.get("removed"):
        result = "reinstalled"
    else:
        result = "installed"
    return {"result": result, "version": version, "managed_entries": names}


def rollback(args: argparse.Namespace) -> dict[str, Any]:
    """回復到最近一次更新前的受管理快照。"""

    manifest, _ = read_manifest(Path(args.manifest))
    client_root, state_root = validate_registration(
        manifest, args.registration, Path(args.client_root), Path(args.state_root)
    )
    file_path = state_file(state_root, args.registration)
    state = load_state(file_path)
    if state is None:
        raise InstallError("找不到安裝狀態。")
    ensure_matching_state(state, args.registration, client_root)
    active = state.get("active")
    if not active:
        raise InstallError("目前沒有可回復的作用中安裝。")
    verify_active(client_root, active)
    history = state.get("history", [])
    if not history:
        raise InstallError("沒有更新前快照可供回復。")

    snapshot = history[-1]
    snapshot_root = state_root / "snapshots" / snapshot["snapshot_id"] / "content"
    entries = {name: snapshot_root / name for name in snapshot["entries"]}
    for name, source in entries.items():
        if not source.exists() or sha256_entry(source) != snapshot["entries"][name]:
            raise InstallError(f"回復快照缺少或已損壞：{name}")

    transaction_root = state_root / "transactions" / uuid.uuid4().hex
    preserve_transaction = False
    try:
        staged = stage_entries(entries, transaction_root)
        names = list(entries)
        replace_entries(client_root, names, staged, transaction_root)
        state["history"] = history[:-1]
        state["active"] = {
            "version": snapshot["version"],
            "manifest_sha256": snapshot["manifest_sha256"],
            "entries": snapshot["entries"],
            "installed_at": utc_now(),
        }
        try:
            write_json_atomic(file_path, state)
        except Exception as state_error:
            try:
                restore_replaced_entries(
                    client_root,
                    names,
                    snapshot["entries"],
                    transaction_root,
                )
            except Exception as restore_error:
                preserve_transaction = True
                raise InstallError(
                    "回復後的狀態寫入失敗，且原版本未能自動復原；交易備份保留於 "
                    f"{transaction_root}：{restore_error}"
                ) from state_error
            raise InstallError(f"狀態寫入失敗，已復原回復前版本：{state_error}") from state_error
    finally:
        if transaction_root.exists() and not preserve_transaction:
            shutil.rmtree(transaction_root)
    return {"result": "rolled_back", "version": snapshot["version"]}


def remove(args: argparse.Namespace) -> dict[str, Any]:
    """把受管理技能移到可復原隔離區，不刪除使用者工作區。"""

    manifest, _ = read_manifest(Path(args.manifest))
    client_root, state_root = validate_registration(
        manifest, args.registration, Path(args.client_root), Path(args.state_root)
    )
    file_path = state_file(state_root, args.registration)
    state = load_state(file_path)
    if state is None:
        raise InstallError("找不到安裝狀態。")
    ensure_matching_state(state, args.registration, client_root)
    active = state.get("active")
    if not active:
        return {"result": "noop", "reason": "already_removed"}
    verify_active(client_root, active)

    quarantine_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    quarantine = state_root / "quarantine" / quarantine_id
    quarantine.mkdir(parents=True)
    moved: list[str] = []
    try:
        for name in active["entries"]:
            (client_root / name).replace(quarantine / name)
            moved.append(name)
    except Exception as error:
        for name in reversed(moved):
            (quarantine / name).replace(client_root / name)
        raise InstallError(f"移除交易失敗，已回復變更：{error}") from error

    try:
        state.setdefault("removed", []).append(
            {
                "removed_at": utc_now(),
                "quarantine": str(quarantine),
                "active": active,
            }
        )
        state["active"] = None
        write_json_atomic(file_path, state)
    except Exception as state_error:
        try:
            for name, digest in active["entries"].items():
                if sha256_entry(quarantine / name) != digest:
                    raise InstallError(f"隔離內容在移除交易中被修改：{name}")
            for name in active["entries"]:
                (quarantine / name).replace(client_root / name)
            quarantine.rmdir()
        except Exception as restore_error:
            raise InstallError(
                "移除狀態寫入失敗且自動回復未完成；隔離內容保留於 "
                f"{quarantine}：{restore_error}"
            ) from state_error
        raise InstallError(f"移除狀態寫入失敗，已回復技能：{state_error}") from state_error
    return {"result": "removed_to_quarantine", "quarantine": str(quarantine)}


def status(args: argparse.Namespace) -> dict[str, Any]:
    """唯讀檢查受管理技能狀態。"""

    manifest, _ = read_manifest(Path(args.manifest))
    client_root, state_root = validate_registration(
        manifest, args.registration, Path(args.client_root), Path(args.state_root)
    )
    state = load_state(state_file(state_root, args.registration))
    if state is None:
        return {"result": "not_managed", "client_root": str(client_root)}
    ensure_matching_state(state, args.registration, client_root)
    active = state.get("active")
    if not active:
        return {"result": "removed", "verification": "no_active_entries"}
    verify_active(client_root, active)
    return {
        "result": "installed",
        "version": active["version"],
        "verification": "hashes_match",
        "managed_entries": sorted(active["entries"]),
    }


def template_inventory(template_root: Path) -> tuple[list[Path], list[Path]]:
    """列出模板中的目錄與檔案，並拒絕特殊檔案。"""

    directories: list[Path] = []
    files: list[Path] = []
    for source in sorted(template_root.rglob("*"), key=lambda item: item.as_posix()):
        if source.is_symlink():
            raise InstallError(f"模板不得包含 symlink：{source}")
        relative = source.relative_to(template_root)
        if source.is_dir():
            directories.append(relative)
        elif source.is_file():
            files.append(relative)
        else:
            raise InstallError(f"模板包含特殊檔案：{source}")
    return directories, files


def inspect_workspace(
    manifest: dict[str, Any], manifest_path: Path, workspace_root: Path
) -> dict[str, Any]:
    """唯讀預覽模板會新增與保留哪些項目。"""

    package_root = manifest_path.parent
    template_relative = manifest.get("workspace", {}).get("template_path")
    if not isinstance(template_relative, str):
        raise InstallError("manifest 缺少 workspace.template_path。")
    template_root = safe_source(package_root, template_relative)
    target_root = workspace_root.expanduser().resolve(strict=False)
    if path_is_within(target_root, package_root):
        raise InstallError("工作區不得位於技能包內；請明確選擇另一個使用者工作區。")
    if target_root.is_symlink():
        raise InstallError("工作區根目錄不得是 symlink。")

    directories, files = template_inventory(template_root)
    create_directories: list[str] = []
    create_files: list[str] = []
    identical_files: list[str] = []
    preserved_existing: list[str] = []
    type_conflicts: list[str] = []

    for relative in directories:
        target = target_root / relative
        if target.is_symlink() or (target.exists() and not target.is_dir()):
            type_conflicts.append(relative.as_posix())
        elif not target.exists():
            create_directories.append(relative.as_posix())
    for relative in files:
        source = template_root / relative
        target = target_root / relative
        if target.is_symlink() or (target.exists() and not target.is_file()):
            type_conflicts.append(relative.as_posix())
        elif not target.exists():
            create_files.append(relative.as_posix())
        elif sha256_file(source) == sha256_file(target):
            identical_files.append(relative.as_posix())
        else:
            preserved_existing.append(relative.as_posix())

    return {
        "workspace_root": str(target_root),
        "template_root": str(template_root),
        "create_directories": create_directories,
        "create_files": create_files,
        "identical_files": identical_files,
        "preserved_existing": preserved_existing,
        "type_conflicts": sorted(set(type_conflicts)),
    }


def workspace_status(args: argparse.Namespace) -> dict[str, Any]:
    """公開工作區預覽，不執行任何寫入。"""

    manifest, manifest_path = read_manifest(Path(args.manifest))
    inspection = inspect_workspace(manifest, manifest_path, Path(args.workspace_root))
    inspection["result"] = "blocked" if inspection["type_conflicts"] else "preview"
    return inspection


def workspace_state_file(state_root: Path, workspace_root: Path) -> Path:
    """以工作區路徑雜湊區分非敏感初始化狀態。"""

    key = hashlib.sha256(str(workspace_root).encode("utf-8")).hexdigest()[:16]
    return state_root / "workspaces" / f"{key}.json"


def initialize_workspace(args: argparse.Namespace) -> dict[str, Any]:
    """只新增模板缺少的項目，絕不覆蓋既有檔案。"""

    manifest, manifest_path = read_manifest(Path(args.manifest))
    inspection = inspect_workspace(manifest, manifest_path, Path(args.workspace_root))
    if inspection["type_conflicts"]:
        raise InstallError(
            "工作區存在檔案類型衝突，未進行任何變更："
            + ", ".join(inspection["type_conflicts"])
        )

    workspace_root = Path(inspection["workspace_root"])
    template_root = Path(inspection["template_root"])
    created_files: list[Path] = []
    created_directories: list[Path] = []
    version = str(manifest["installation"]["candidate_version"])
    try:
        if not workspace_root.exists():
            workspace_root.mkdir(parents=True)
            created_directories.append(workspace_root)
        for relative_text in inspection["create_directories"]:
            target = workspace_root / relative_text
            if not target.exists():
                target.mkdir()
                created_directories.append(target)
        for relative_text in inspection["create_files"]:
            source = template_root / relative_text
            target = workspace_root / relative_text
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(source.read_bytes())
            shutil.copymode(source, target)
            created_files.append(target)
        state_root = Path(args.state_root).expanduser().resolve(strict=False)
        payload = {
            "schema_version": STATE_SCHEMA_VERSION,
            "workspace_root": str(workspace_root),
            "candidate_version": version,
            "initialized_at": utc_now(),
            "created_files": inspection["create_files"],
            "preserved_existing": inspection["preserved_existing"],
            "contains_credentials": False,
        }
        write_json_atomic(workspace_state_file(state_root, workspace_root), payload)
    except Exception as error:
        for target in reversed(created_files):
            if target.exists():
                target.unlink()
        for target in reversed(created_directories):
            try:
                target.rmdir()
            except OSError:
                pass
        raise InstallError(f"初始化失敗，已移除本次新增項目：{error}") from error
    changed = bool(inspection["create_directories"] or inspection["create_files"])
    return {
        "result": "initialized_missing_items" if changed else "noop",
        "candidate_version": version,
        "created_directories": inspection["create_directories"],
        "created_files": inspection["create_files"],
        "preserved_existing": inspection["preserved_existing"],
    }


def build_parser() -> argparse.ArgumentParser:
    """建立公開命令列介面。"""

    parser = argparse.ArgumentParser(
        description="管理 AI 知識庫的五個自有技能與工作區模板。"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("install", "update", "rollback", "remove", "status"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
        subparser.add_argument("--registration", required=True)
        subparser.add_argument("--client-root", required=True)
        subparser.add_argument("--state-root", required=True)

    for command in ("workspace-status", "init-workspace"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
        subparser.add_argument("--workspace-root", required=True)
        subparser.add_argument("--state-root", required=command == "init-workspace")
    return parser


def main() -> int:
    """解析命令、輸出機器可讀 JSON，錯誤時以代碼 2 安全停止。"""

    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "install":
            result = install_or_update(args, update=False)
        elif args.command == "update":
            result = install_or_update(args, update=True)
        elif args.command == "rollback":
            result = rollback(args)
        elif args.command == "remove":
            result = remove(args)
        elif args.command == "status":
            result = status(args)
        elif args.command == "workspace-status":
            result = workspace_status(args)
        elif args.command == "init-workspace":
            result = initialize_workspace(args)
        else:
            parser.error("未知命令")
            return 2
    except (InstallError, OSError) as error:
        print(json.dumps({"result": "stopped", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
