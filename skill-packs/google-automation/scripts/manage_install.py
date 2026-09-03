#!/usr/bin/env python3
"""安全管理 Google 工具自動化技能入口的安裝生命週期。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import tomllib


STATE_SCHEMA_VERSION = 1


class InstallError(RuntimeError):
    """代表需要安全停止、且不應自動繼續的安裝錯誤。"""


@dataclass(frozen=True)
class DesiredEntry:
    """記錄一個準備註冊的檔案或目錄及其完整性資料。"""

    name: str
    source: Path
    kind: str
    sha256: str


def utc_now() -> str:
    """回傳可寫入狀態檔的 UTC 時間。"""

    return datetime.now(UTC).replace(microsecond=0).isoformat()


def sha256_file(file_path: Path) -> str:
    """以串流方式計算單一檔案的 SHA-256。"""

    digest = hashlib.sha256()
    with file_path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_entry(entry_path: Path) -> tuple[str, str]:
    """計算檔案或目錄的可重現內容雜湊，並拒絕 symlink。"""

    if entry_path.is_symlink():
        raise InstallError(f"來源或入口不得是 symlink：{entry_path}")
    if entry_path.is_file():
        return "file", sha256_file(entry_path)
    if not entry_path.is_dir():
        raise InstallError(f"找不到必要來源：{entry_path}")

    digest = hashlib.sha256()
    digest.update(b"directory\0")
    for child in sorted(entry_path.rglob("*"), key=lambda path: path.as_posix()):
        relative = child.relative_to(entry_path).as_posix()
        if child.is_symlink():
            raise InstallError(f"來源或入口內不得包含 symlink：{child}")
        if child.is_dir():
            digest.update(b"dir\0")
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            continue
        if not child.is_file():
            raise InstallError(f"來源含不支援的項目：{child}")
        digest.update(b"file\0")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(child).encode("ascii"))
        digest.update(b"\0")
    return "directory", digest.hexdigest()


def read_manifest(manifest_path: Path) -> dict[str, Any]:
    """讀取並驗證本機 manifest 的基本候選狀態。"""

    try:
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise InstallError(f"無法讀取 manifest：{manifest_path}: {error}") from error

    if manifest.get("schema_version") != 1:
        raise InstallError("不支援的 manifest schema_version")
    if manifest.get("status") != "ready_for_external_acceptance":
        raise InstallError("manifest 尚未達到 ready_for_external_acceptance")
    if manifest.get("installable") is not True:
        raise InstallError("manifest 目前不允許安裝")
    if manifest.get("support_level") != "installable_candidate_not_formally_supported":
        raise InstallError("manifest 沒有正確區分候選安裝與正式支援")
    return manifest


def run_git(repository: Path, *arguments: str) -> str:
    """執行唯讀 Git 命令並保留可理解的錯誤。"""

    try:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        details = getattr(error, "stderr", "") or str(error)
        raise InstallError(f"Learn-GAS Git 驗證失敗：{details.strip()}") from error
    return result.stdout.strip()


def verify_learn_gas(manifest: dict[str, Any], source_root: Path) -> dict[str, str]:
    """核對 Learn-GAS commit、tree、授權雜湊及乾淨狀態。"""

    integration = manifest.get("integration", {}).get("learn_gas", {})
    expected_ref = integration.get("ref")
    expected_tree = integration.get("tree")
    expected_license = integration.get("license_sha256")
    if not all(isinstance(value, str) and value for value in (expected_ref, expected_tree, expected_license)):
        raise InstallError("manifest 缺少 Learn-GAS 固定來源資訊")

    resolved_source = source_root.expanduser().resolve()
    if not resolved_source.is_dir():
        raise InstallError(f"Learn-GAS 來源目錄不存在：{resolved_source}")
    actual_ref = run_git(resolved_source, "rev-parse", "HEAD")
    actual_tree = run_git(resolved_source, "rev-parse", "HEAD^{tree}")
    status = run_git(resolved_source, "status", "--porcelain", "--untracked-files=all")
    if actual_ref != expected_ref:
        raise InstallError(f"Learn-GAS commit 不符：{actual_ref} != {expected_ref}")
    if actual_tree != expected_tree:
        raise InstallError(f"Learn-GAS tree 不符：{actual_tree} != {expected_tree}")
    if status:
        raise InstallError("Learn-GAS 來源有修改或未追蹤檔案，不可作為固定安裝來源")

    license_path = resolved_source / "LICENSE"
    if not license_path.is_file():
        raise InstallError("Learn-GAS 缺少 LICENSE")
    actual_license = sha256_file(license_path)
    if actual_license != expected_license:
        raise InstallError(
            f"Learn-GAS LICENSE SHA-256 不符：{actual_license} != {expected_license}"
        )
    return {"ref": actual_ref, "tree": actual_tree, "license_sha256": actual_license}


def validate_simple_name(name: str, *, label: str) -> str:
    """限制狀態鍵與受管理入口為單一安全名稱。"""

    if not name or name in {".", ".."} or Path(name).name != name:
        raise InstallError(f"{label} 不是安全的單層名稱：{name!r}")
    if any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for character in name):
        raise InstallError(f"{label} 含不允許字元：{name!r}")
    return name


def validate_registration(
    manifest: dict[str, Any], registration: str, client_root: Path, state_root: Path
) -> tuple[Path, Path]:
    """確認註冊 ID、技能根目錄形狀與狀態目錄安全邊界。"""

    validate_simple_name(registration, label="registration")
    record = manifest.get("registrations", {}).get(registration)
    if not isinstance(record, dict):
        raise InstallError(f"manifest 沒有註冊 ID：{registration}")

    resolved_client = client_root.expanduser().resolve()
    resolved_state = state_root.expanduser().resolve()
    if resolved_client == Path(resolved_client.anchor):
        raise InstallError("技能根目錄不可是檔案系統根目錄")
    if resolved_state == Path(resolved_state.anchor):
        raise InstallError("狀態目錄不可是檔案系統根目錄")
    if resolved_state == resolved_client or resolved_state.is_relative_to(resolved_client):
        raise InstallError("狀態目錄必須位於技能掃描根目錄之外")

    path_hint = str(record.get("path", ""))
    allowed_suffixes = ("/.agents/skills", "/.claude/skills", "/.gemini/config/skills")
    expected_suffix = next((suffix for suffix in allowed_suffixes if path_hint.endswith(suffix)), None)
    if expected_suffix is None:
        raise InstallError(f"manifest 註冊路徑無法驗證：{path_hint}")
    if not resolved_client.as_posix().endswith(expected_suffix):
        raise InstallError(
            f"技能根目錄與 {registration} 不符：預期結尾 {expected_suffix}，實際 {resolved_client}"
        )
    return resolved_client, resolved_state


def build_desired_entries(
    manifest_path: Path,
    manifest: dict[str, Any],
    learn_gas_source: Path,
) -> tuple[dict[str, DesiredEntry], dict[str, Any]]:
    """從 Toolbox 與固定 Learn-GAS 來源建立六個受管理入口。"""

    package_root = manifest_path.parent.resolve()
    source_config = manifest.get("managed_sources", {})
    router_relative = source_config.get("router_path")
    skill_names = source_config.get("learn_gas_skills")
    shared_files = source_config.get("learn_gas_shared_files")
    if not isinstance(router_relative, str):
        raise InstallError("manifest 缺少 router_path")
    if not isinstance(skill_names, list) or not isinstance(shared_files, list):
        raise InstallError("manifest 缺少 Learn-GAS 受管理來源清單")

    verified_learn_gas = verify_learn_gas(manifest, learn_gas_source)
    resolved_learn_gas = learn_gas_source.expanduser().resolve()
    sources: dict[str, Path] = {
        "google-workflow-router": package_root / router_relative,
    }
    for raw_name in skill_names:
        name = validate_simple_name(str(raw_name), label="Learn-GAS 技能名稱")
        sources[name] = resolved_learn_gas / "skills" / name
    for raw_name in shared_files:
        name = validate_simple_name(str(raw_name), label="Learn-GAS 共用檔名")
        sources[name] = resolved_learn_gas / "skills" / name

    expected_entries = manifest.get("installation", {}).get("managed_entries")
    if sorted(sources) != sorted(expected_entries or []):
        raise InstallError("manifest 的 managed_entries 與實際來源清單不一致")

    desired: dict[str, DesiredEntry] = {}
    for name, source in sources.items():
        validate_simple_name(name, label="受管理入口")
        kind, digest = hash_entry(source)
        if kind == "directory" and not (source / "SKILL.md").is_file():
            raise InstallError(f"技能目錄缺少 SKILL.md：{source}")
        desired[name] = DesiredEntry(name=name, source=source, kind=kind, sha256=digest)

    active = {
        "toolbox_version": manifest.get("installation", {}).get("candidate_version"),
        "learn_gas_ref": verified_learn_gas["ref"],
        "learn_gas_tree": verified_learn_gas["tree"],
        "entries": {
            name: {"kind": entry.kind, "sha256": entry.sha256}
            for name, entry in sorted(desired.items())
        },
    }
    if not isinstance(active["toolbox_version"], str) or not active["toolbox_version"]:
        raise InstallError("manifest 缺少 candidate_version")
    return desired, active


def state_file_path(state_root: Path, registration: str, client_root: Path) -> Path:
    """以註冊 ID 與目標路徑建立不含帳號資料的穩定狀態檔名。"""

    target_key = hashlib.sha256(str(client_root).encode("utf-8")).hexdigest()[:16]
    return state_root / "registrations" / f"{registration}-{target_key}.json"


def read_state(state_path: Path) -> dict[str, Any] | None:
    """讀取既有狀態；不存在時回傳 None。"""

    if not state_path.exists():
        return None
    if state_path.is_symlink() or not state_path.is_file():
        raise InstallError(f"狀態路徑不是一般檔案：{state_path}")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InstallError(f"無法讀取安裝狀態：{state_path}: {error}") from error
    if state.get("schema_version") != STATE_SCHEMA_VERSION:
        raise InstallError("不支援的安裝狀態版本")
    return state


def write_json_atomic(file_path: Path, payload: dict[str, Any]) -> None:
    """在同一檔案系統先完成暫存寫入，再原子替換狀態檔。"""

    temporary_path: Path | None = None
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{file_path.name}.", suffix=".tmp", dir=file_path.parent
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, ensure_ascii=False, indent=2, sort_keys=True)
            file_handle.write("\n")
            file_handle.flush()
            os.fsync(file_handle.fileno())
        os.replace(temporary_path, file_path)
    except OSError as error:
        raise InstallError(f"無法安全寫入狀態檔：{file_path}: {error}") from error
    finally:
        if temporary_path is not None and temporary_path.exists():
            try:
                temporary_path.unlink()
            except OSError:
                pass


def path_exists(path: Path) -> bool:
    """連失效 symlink 也視為已存在，避免意外覆寫。"""

    return os.path.lexists(path)


def remove_exact_path(path: Path) -> None:
    """只移除已解析的單一受管理入口或內部暫存目錄。"""

    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path_exists(path):
        raise InstallError(f"無法安全移除不支援的項目：{path}")


def copy_entry(source: Path, target: Path) -> None:
    """保留目錄結構複製已驗證來源，不追蹤 symlink。"""

    kind, _ = hash_entry(source)
    if kind == "directory":
        shutil.copytree(source, target, symlinks=False)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def verify_active_entries(client_root: Path, active: dict[str, Any]) -> None:
    """確認目前受管理入口仍和狀態中的種類與雜湊相符。"""

    entries = active.get("entries")
    if not isinstance(entries, dict) or not entries:
        raise InstallError("安裝狀態缺少受管理入口")
    for raw_name, expected in entries.items():
        name = validate_simple_name(str(raw_name), label="狀態入口")
        target = client_root / name
        if not path_exists(target):
            raise InstallError(f"受管理入口遺失，停止以避免覆寫：{target}")
        actual_kind, actual_digest = hash_entry(target)
        if actual_kind != expected.get("kind") or actual_digest != expected.get("sha256"):
            raise InstallError(f"受管理入口已被修改，停止以保留內容：{target}")


def existing_entries_match(client_root: Path, desired: dict[str, DesiredEntry]) -> bool:
    """判斷無狀態的既有入口是否全部與預定來源完全相同。"""

    present = [name for name in desired if path_exists(client_root / name)]
    if not present:
        return False
    if len(present) != len(desired):
        missing = sorted(set(desired) - set(present))
        raise InstallError(f"技能根目錄只有部分受管理入口；缺少：{', '.join(missing)}")
    for name, expected in desired.items():
        target = client_root / name
        actual_kind, actual_digest = hash_entry(target)
        if actual_kind != expected.kind or actual_digest != expected.sha256:
            raise InstallError(f"發現未知或不同內容，不會接管：{target}")
    return True


def transactional_replace(client_root: Path, desired: dict[str, DesiredEntry]) -> None:
    """先完整暫存所有來源，再逐項替換；失敗時回復已交換項目。"""

    client_root.parent.mkdir(parents=True, exist_ok=True)
    if path_exists(client_root) and (client_root.is_symlink() or not client_root.is_dir()):
        raise InstallError(f"技能根目錄不是一般目錄：{client_root}")
    client_root.mkdir(parents=True, exist_ok=True)

    operation_id = uuid.uuid4().hex
    stage_root = client_root.parent / f".{client_root.name}.toolbox-stage-{operation_id}"
    displaced_root = client_root.parent / f".{client_root.name}.toolbox-displaced-{operation_id}"
    stage_root.mkdir()
    displaced_root.mkdir()
    swapped: list[tuple[Path, Path, bool]] = []
    try:
        for name, entry in desired.items():
            copy_entry(entry.source, stage_root / name)
            staged_kind, staged_hash = hash_entry(stage_root / name)
            if staged_kind != entry.kind or staged_hash != entry.sha256:
                raise InstallError(f"暫存複製驗證失敗：{name}")

        for name in sorted(desired):
            target = client_root / name
            displaced = displaced_root / name
            had_existing = path_exists(target)
            if had_existing:
                os.replace(target, displaced)
            try:
                os.replace(stage_root / name, target)
            except Exception:
                if had_existing and path_exists(displaced):
                    os.replace(displaced, target)
                raise
            swapped.append((target, displaced, had_existing))
    except Exception as error:
        for target, displaced, had_existing in reversed(swapped):
            if path_exists(target):
                remove_exact_path(target)
            if had_existing and path_exists(displaced):
                os.replace(displaced, target)
        if isinstance(error, InstallError):
            raise
        raise InstallError(f"技能入口替換失敗，已嘗試回復：{error}") from error
    finally:
        if stage_root.exists():
            shutil.rmtree(stage_root)
        if displaced_root.exists():
            shutil.rmtree(displaced_root)


def desired_from_backup(backup_root: Path, active: dict[str, Any]) -> dict[str, DesiredEntry]:
    """把已記錄的備份轉回可驗證的來源清單。"""

    entries: dict[str, DesiredEntry] = {}
    for raw_name, expected in active.get("entries", {}).items():
        name = validate_simple_name(str(raw_name), label="備份入口")
        source = backup_root / "entries" / name
        kind, digest = hash_entry(source)
        if kind != expected.get("kind") or digest != expected.get("sha256"):
            raise InstallError(f"回復備份的雜湊不符：{source}")
        entries[name] = DesiredEntry(name=name, source=source, kind=kind, sha256=digest)
    return entries


def snapshot_entries(
    state_root: Path,
    registration: str,
    client_root: Path,
    active: dict[str, Any],
    *,
    purpose: str,
) -> dict[str, Any]:
    """把目前已驗證入口複製到掃描目錄外的可回復位置。"""

    verify_active_entries(client_root, active)
    backup_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:10]}"
    target_key = hashlib.sha256(str(client_root).encode("utf-8")).hexdigest()[:16]
    backup_root = state_root / "backups" / f"{registration}-{target_key}" / backup_id
    entries_root = backup_root / "entries"
    entries_root.mkdir(parents=True)
    try:
        for raw_name in active["entries"]:
            name = validate_simple_name(str(raw_name), label="備份入口")
            copy_entry(client_root / name, entries_root / name)
        desired_from_backup(backup_root, active)
        metadata = {
            "backup_id": backup_id,
            "purpose": purpose,
            "created_at": utc_now(),
            "path": str(backup_root),
            "active": active,
        }
        write_json_atomic(backup_root / "metadata.json", metadata)
        return metadata
    except Exception:
        if backup_root.exists():
            shutil.rmtree(backup_root)
        raise


def same_active(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """比較會影響安裝內容的版本與雜湊。"""

    keys = ("toolbox_version", "learn_gas_ref", "learn_gas_tree", "entries")
    return all(left.get(key) == right.get(key) for key in keys)


def base_state(registration: str, client_root: Path, active: dict[str, Any]) -> dict[str, Any]:
    """建立新的非敏感安裝狀態。"""

    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "registration": registration,
        "client_root": str(client_root),
        "status": "active",
        "active": active,
        "history": [],
        "future": [],
        "removed": None,
        "updated_at": utc_now(),
    }


def install_command(args: argparse.Namespace) -> dict[str, Any]:
    """執行首次安裝、完全相同內容的接管或安全重跑。"""

    manifest_path = args.manifest.expanduser().resolve()
    manifest = read_manifest(manifest_path)
    client_root, state_root = validate_registration(
        manifest, args.registration, args.client_root, args.state_root
    )
    desired, active = build_desired_entries(manifest_path, manifest, args.learn_gas_source)
    state_path = state_file_path(state_root, args.registration, client_root)
    state = read_state(state_path)

    if state and state.get("status") == "active":
        verify_active_entries(client_root, state["active"])
        if same_active(state["active"], active):
            return {"result": "noop", "state": str(state_path), "entries": sorted(desired)}
        raise InstallError("已有不同的受管理版本；請在驗證新版後使用 update")

    if state and state.get("status") == "removed":
        conflicts = [name for name in desired if path_exists(client_root / name)]
        if conflicts:
            raise InstallError(f"移除後出現未知入口，不會重新安裝：{', '.join(conflicts)}")
        transactional_replace(client_root, desired)
        state["status"] = "active"
        state["active"] = active
        state["removed"] = None
        state["updated_at"] = utc_now()
        try:
            write_json_atomic(state_path, state)
        except Exception:
            for name in desired:
                target = client_root / name
                if path_exists(target):
                    remove_exact_path(target)
            raise
        return {"result": "reinstalled", "state": str(state_path), "entries": sorted(desired)}

    adopted = existing_entries_match(client_root, desired) if client_root.exists() else False
    if not adopted:
        conflicts = [name for name in desired if path_exists(client_root / name)]
        if conflicts:
            raise InstallError(f"發現未知入口，不會覆寫：{', '.join(conflicts)}")
        transactional_replace(client_root, desired)
    new_state = base_state(args.registration, client_root, active)
    try:
        write_json_atomic(state_path, new_state)
    except Exception:
        if not adopted:
            for name in desired:
                target = client_root / name
                if path_exists(target):
                    remove_exact_path(target)
        raise
    return {
        "result": "adopted_identical" if adopted else "installed",
        "state": str(state_path),
        "entries": sorted(desired),
    }


def update_command(args: argparse.Namespace) -> dict[str, Any]:
    """保留已驗證舊版後，交易式更新到新的 manifest 與來源。"""

    manifest_path = args.manifest.expanduser().resolve()
    manifest = read_manifest(manifest_path)
    client_root, state_root = validate_registration(
        manifest, args.registration, args.client_root, args.state_root
    )
    desired, active = build_desired_entries(manifest_path, manifest, args.learn_gas_source)
    state_path = state_file_path(state_root, args.registration, client_root)
    state = read_state(state_path)
    if not state or state.get("status") != "active":
        raise InstallError("找不到可更新的 active 安裝狀態")
    verify_active_entries(client_root, state["active"])
    if same_active(state["active"], active):
        return {"result": "noop", "state": str(state_path), "entries": sorted(desired)}

    backup = snapshot_entries(
        state_root,
        args.registration,
        client_root,
        state["active"],
        purpose="update_history",
    )
    try:
        transactional_replace(client_root, desired)
        verify_active_entries(client_root, active)
    except Exception:
        backup_entries = desired_from_backup(Path(backup["path"]), backup["active"])
        transactional_replace(client_root, backup_entries)
        raise
    state.setdefault("history", []).append(backup)
    state["future"] = []
    state["active"] = active
    state["status"] = "active"
    state["updated_at"] = utc_now()
    try:
        write_json_atomic(state_path, state)
    except Exception:
        backup_entries = desired_from_backup(Path(backup["path"]), backup["active"])
        transactional_replace(client_root, backup_entries)
        verify_active_entries(client_root, backup["active"])
        raise
    return {"result": "updated", "state": str(state_path), "backup_id": backup["backup_id"]}


def load_target_state(args: argparse.Namespace) -> tuple[Path, Path, Path, dict[str, Any]]:
    """為不需要 manifest 的狀態操作解析並驗證目標。"""

    client_root = args.client_root.expanduser().resolve()
    state_root = args.state_root.expanduser().resolve()
    if state_root == client_root or state_root.is_relative_to(client_root):
        raise InstallError("狀態目錄必須位於技能掃描根目錄之外")
    validate_simple_name(args.registration, label="registration")
    state_path = state_file_path(state_root, args.registration, client_root)
    state = read_state(state_path)
    if not state:
        raise InstallError("找不到此註冊與技能根目錄的安裝狀態")
    if state.get("registration") != args.registration or state.get("client_root") != str(client_root):
        raise InstallError("狀態檔與要求的註冊目標不一致")
    return client_root, state_root, state_path, state


def rollback_command(args: argparse.Namespace) -> dict[str, Any]:
    """從最新且雜湊相符的歷史備份回復。"""

    client_root, state_root, state_path, state = load_target_state(args)
    if state.get("status") != "active":
        raise InstallError("只有 active 安裝可以回復")
    verify_active_entries(client_root, state["active"])
    history = state.get("history")
    if not isinstance(history, list) or not history:
        raise InstallError("沒有可回復的歷史版本")

    target_backup = history[-1]
    target_entries = desired_from_backup(Path(target_backup["path"]), target_backup["active"])
    future_backup = snapshot_entries(
        state_root,
        args.registration,
        client_root,
        state["active"],
        purpose="rollback_future",
    )
    try:
        transactional_replace(client_root, target_entries)
        verify_active_entries(client_root, target_backup["active"])
    except Exception:
        current_entries = desired_from_backup(Path(future_backup["path"]), future_backup["active"])
        transactional_replace(client_root, current_entries)
        raise

    state["history"] = history[:-1]
    state.setdefault("future", []).append(future_backup)
    state["active"] = target_backup["active"]
    state["updated_at"] = utc_now()
    try:
        write_json_atomic(state_path, state)
    except Exception:
        current_entries = desired_from_backup(Path(future_backup["path"]), future_backup["active"])
        transactional_replace(client_root, current_entries)
        verify_active_entries(client_root, future_backup["active"])
        raise
    return {
        "result": "rolled_back",
        "state": str(state_path),
        "restored_backup_id": target_backup["backup_id"],
    }


def remove_command(args: argparse.Namespace) -> dict[str, Any]:
    """把六個已驗證入口移到可回復隔離區，不刪除其他內容。"""

    client_root, state_root, state_path, state = load_target_state(args)
    if state.get("status") != "active":
        raise InstallError("此安裝目前不是 active 狀態")
    verify_active_entries(client_root, state["active"])
    quarantine = snapshot_entries(
        state_root,
        args.registration,
        client_root,
        state["active"],
        purpose="removed_quarantine",
    )

    removed_names: list[str] = []
    try:
        for raw_name in state["active"]["entries"]:
            name = validate_simple_name(str(raw_name), label="移除入口")
            target = client_root / name
            remove_exact_path(target)
            removed_names.append(name)
    except Exception as error:
        restore_entries = desired_from_backup(Path(quarantine["path"]), quarantine["active"])
        transactional_replace(client_root, restore_entries)
        if isinstance(error, InstallError):
            raise
        raise InstallError(f"移除途中失敗，已嘗試還原：{error}") from error

    state["status"] = "removed"
    state["removed"] = quarantine
    state["updated_at"] = utc_now()
    try:
        write_json_atomic(state_path, state)
    except Exception:
        restore_entries = desired_from_backup(Path(quarantine["path"]), quarantine["active"])
        transactional_replace(client_root, restore_entries)
        verify_active_entries(client_root, quarantine["active"])
        raise
    return {
        "result": "removed_to_quarantine",
        "state": str(state_path),
        "quarantine": quarantine["path"],
        "entries": sorted(removed_names),
    }


def status_command(args: argparse.Namespace) -> dict[str, Any]:
    """唯讀回報目前狀態與內容驗證結果。"""

    try:
        client_root, _, state_path, state = load_target_state(args)
    except InstallError as error:
        if "找不到此註冊" in str(error):
            return {"result": "not_installed"}
        raise
    verification = "not_applicable"
    if state.get("status") == "active":
        verify_active_entries(client_root, state["active"])
        verification = "hashes_match"
    return {
        "result": "status",
        "status": state.get("status"),
        "verification": verification,
        "state": str(state_path),
        "active": state.get("active"),
        "history_count": len(state.get("history", [])),
    }


def add_target_arguments(parser: argparse.ArgumentParser) -> None:
    """加入所有生命週期命令共用的明確目標參數。"""

    parser.add_argument("--registration", required=True, help="manifest 的註冊 ID")
    parser.add_argument("--client-root", type=Path, required=True, help="實際技能根目錄")
    parser.add_argument("--state-root", type=Path, required=True, help="技能掃描目錄外的狀態根目錄")


def add_source_arguments(parser: argparse.ArgumentParser) -> None:
    """加入需要固定本機來源的安裝與更新參數。"""

    parser.add_argument("--manifest", type=Path, required=True, help="本套件 manifest")
    parser.add_argument(
        "--learn-gas-source", type=Path, required=True, help="已驗證的固定 Learn-GAS clone"
    )


def build_parser() -> argparse.ArgumentParser:
    """建立命令列介面。"""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="首次安裝或安全重跑")
    add_target_arguments(install_parser)
    add_source_arguments(install_parser)
    install_parser.set_defaults(handler=install_command)

    update_parser = subparsers.add_parser("update", help="保留舊版後更新")
    add_target_arguments(update_parser)
    add_source_arguments(update_parser)
    update_parser.set_defaults(handler=update_command)

    rollback_parser = subparsers.add_parser("rollback", help="回復最近的已驗證歷史版本")
    add_target_arguments(rollback_parser)
    rollback_parser.set_defaults(handler=rollback_command)

    remove_parser = subparsers.add_parser("remove", help="移到可回復隔離區")
    add_target_arguments(remove_parser)
    remove_parser.set_defaults(handler=remove_command)

    status_parser = subparsers.add_parser("status", help="唯讀檢查安裝狀態")
    add_target_arguments(status_parser)
    status_parser.set_defaults(handler=status_command)
    return parser


def main() -> None:
    """執行命令並輸出機器可讀結果。"""

    args = build_parser().parse_args()
    try:
        result = args.handler(args)
    except InstallError as error:
        print(json.dumps({"result": "stopped", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2) from error
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
