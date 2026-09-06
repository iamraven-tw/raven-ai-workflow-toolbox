#!/usr/bin/env python3
"""安全管理社群媒體技能包目前已完成技能的本機生命週期。"""

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
    """表示為保留使用者內容而安全停止的安裝錯誤。"""


def utc_now() -> str:
    """回傳秒級 UTC ISO 時間。"""

    return datetime.now(UTC).replace(microsecond=0).isoformat()


def sha256_file(file_path: Path) -> str:
    """以串流方式計算單一檔案雜湊。"""

    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_entry(entry: Path) -> str:
    """計算目錄的可重現雜湊，並拒絕任何 symlink。"""

    if entry.is_symlink() or not entry.is_dir():
        raise InstallError(f"技能來源或入口必須是一般目錄：{entry}")
    digest = hashlib.sha256()
    for child in sorted(entry.rglob("*"), key=lambda item: item.as_posix()):
        if child.is_symlink():
            raise InstallError(f"技能內容不得包含 symlink：{child}")
        relative = child.relative_to(entry).as_posix().encode("utf-8")
        if child.is_dir():
            digest.update(b"D\0" + relative + b"\0")
        elif child.is_file():
            digest.update(b"F\0" + relative + b"\0")
            digest.update(bytes.fromhex(sha256_file(child)))
        else:
            raise InstallError(f"技能內容含特殊檔案：{child}")
    return digest.hexdigest()


def read_manifest(manifest_path: Path) -> tuple[dict[str, Any], Path]:
    """讀取本機候選 manifest，保留第一版快照的回復相容性。"""

    resolved = manifest_path.expanduser().resolve(strict=True)
    try:
        with resolved.open("rb") as handle:
            manifest = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise InstallError(f"無法讀取 manifest：{error}") from error
    expected = {
        "schema_version": 1,
        "manifest_type": "social-media-install",
        "installable": True,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise InstallError(f"manifest.{key} 不符合本機候選契約")
    allowed = {
        ("local_candidate_first_skill", "first_skill_installable_candidate_not_formally_supported"),
        ("local_candidate_partial_pack", "partial_pack_installable_candidate_not_formally_supported"),
        ("local_candidate_full_pack", "full_pack_installable_candidate_not_formally_supported"),
    }
    if (manifest.get("status"), manifest.get("support_level")) not in allowed:
        raise InstallError("manifest 不是受支援的本機候選")
    version = manifest.get("installation", {}).get("candidate_version")
    if not isinstance(version, str) or not version:
        raise InstallError("manifest 缺少 candidate_version")
    return manifest, resolved


def safe_source(package_root: Path, relative: str) -> Path:
    """解析且限制來源只能位於技能包內。"""

    source = (package_root / relative).resolve(strict=True)
    if not source.is_relative_to(package_root):
        raise InstallError(f"來源跳出技能包：{relative}")
    return source


def desired_entries(manifest: dict[str, Any], manifest_path: Path) -> dict[str, tuple[Path, str]]:
    """從 manifest 建立目前已完成技能的來源清單。"""

    entries: dict[str, tuple[Path, str]] = {}
    for record in manifest.get("skills", []):
        if record.get("required") is not True:
            continue
        skill_id = record.get("id")
        source_relative = record.get("source_path")
        if not isinstance(skill_id, str) or Path(skill_id).name != skill_id:
            raise InstallError("manifest 含不安全的技能 ID")
        if not isinstance(source_relative, str):
            raise InstallError(f"技能 {skill_id} 缺少 source_path")
        source = safe_source(manifest_path.parent, source_relative)
        if source.name != skill_id or not (source / "SKILL.md").is_file():
            raise InstallError(f"技能來源結構不正確：{skill_id}")
        if skill_id in entries:
            raise InstallError(f"重複技能 ID：{skill_id}")
        entries[skill_id] = (source, sha256_entry(source))
    managed = manifest.get("installation", {}).get("managed_entries")
    if sorted(entries) != sorted(managed or []):
        raise InstallError("managed_entries 與已完成技能不一致")
    if not entries:
        raise InstallError("manifest 沒有可安裝的已完成技能")
    planned = {record.get("id") for record in manifest.get("planned_skills", [])}
    if planned & set(entries):
        raise InstallError("已完成技能與 planned_skills 重複")
    return entries


def validate_registration(
    manifest: dict[str, Any], registration: str, client_root: Path, state_root: Path
) -> tuple[Path, Path]:
    """驗證技能入口與狀態目錄的界線。"""

    record = manifest.get("registrations", {}).get(registration)
    if not isinstance(record, dict):
        raise InstallError(f"未知 registration：{registration}")
    path_hint = record.get("path")
    if not isinstance(path_hint, str):
        raise InstallError("registration 缺少 path")
    if path_hint.startswith("<workspace>"):
        suffix = path_hint.removeprefix("<workspace>")
    elif path_hint.startswith("$HOME"):
        suffix = path_hint.removeprefix("$HOME")
    else:
        raise InstallError("registration path 必須使用公開佔位符")
    client = client_root.expanduser().resolve(strict=False)
    state = state_root.expanduser().resolve(strict=False)
    if client == Path(client.anchor) or state == Path(state.anchor):
        raise InstallError("技能或狀態目錄不得是檔案系統根目錄")
    expected_parts = Path(suffix.lstrip("/")).parts
    if expected_parts and client.parts[-len(expected_parts) :] != expected_parts:
        raise InstallError(f"client-root 與 {registration} 宣告路徑不符")
    if state == client or state.is_relative_to(client):
        raise InstallError("state-root 必須位於技能掃描目錄外")
    return client, state


def state_path(state_root: Path, registration: str, client_root: Path) -> Path:
    """依目標路徑區分多個相同 registration 狀態。"""

    key = hashlib.sha256(str(client_root).encode("utf-8")).hexdigest()[:16]
    return state_root / "registrations" / f"{registration}-{key}.json"


def read_state(file_path: Path) -> dict[str, Any] | None:
    """讀取既有安裝狀態。"""

    if not os.path.lexists(file_path):
        return None
    if file_path.is_symlink() or not file_path.is_file():
        raise InstallError(f"安裝狀態不是一般檔案：{file_path}")
    try:
        state = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InstallError(f"無法讀取安裝狀態：{error}") from error
    if not isinstance(state, dict) or state.get("schema_version") != STATE_SCHEMA_VERSION:
        raise InstallError("安裝狀態版本不支援")
    return state


def write_json_atomic(file_path: Path, payload: dict[str, Any]) -> None:
    """在相同檔案系統寫完後再原子替換。"""

    file_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{file_path.name}.", dir=file_path.parent)
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


def copy_skill(source: Path, target: Path) -> None:
    """複製已驗證技能，不保留或跟隨 symlink。"""

    shutil.copytree(source, target, symlinks=False)


def current_hashes(client_root: Path, names: list[str]) -> dict[str, str | None]:
    """取得目前各同名入口雜湊。"""

    result: dict[str, str | None] = {}
    for name in names:
        target = client_root / name
        result[name] = sha256_entry(target) if os.path.lexists(target) else None
    return result


def verify_active(client_root: Path, active: dict[str, Any]) -> None:
    """避免覆蓋安裝後的人工作品或損壞入口。"""

    entries = active.get("entries")
    if not isinstance(entries, dict) or not entries:
        raise InstallError("active 狀態缺少 entries")
    actual = current_hashes(client_root, list(entries))
    changed = [name for name, digest in entries.items() if actual.get(name) != digest]
    if changed:
        raise InstallError("受管理技能已缺少或修改，未覆蓋：" + ", ".join(changed))


def validate_state_target(state: dict[str, Any], registration: str, client_root: Path) -> None:
    """避免把另一個目標的狀態誤用於目前安裝。"""

    if state.get("registration") != registration or state.get("client_root") != str(client_root):
        raise InstallError("安裝狀態與目前 registration 或 client-root 不符")


def base_state(registration: str, client_root: Path) -> dict[str, Any]:
    """建立不含憑證與內容資料的狀態。"""

    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "registration": registration,
        "client_root": str(client_root),
        "active": None,
        "history": [],
        "removed": [],
        "contains_credentials": False,
    }


def active_record(version: str, manifest_path: Path, hashes: dict[str, str]) -> dict[str, Any]:
    """建立目前作用中版本記錄。"""

    return {
        "version": version,
        "manifest_sha256": sha256_file(manifest_path),
        "entries": hashes,
        "installed_at": utc_now(),
    }


def stage_entries(entries: dict[str, tuple[Path, str]], transaction: Path) -> Path:
    """先在狀態目錄完成整批候選複製。"""

    staged = transaction / "new"
    staged.mkdir(parents=True)
    for name, (source, expected_hash) in entries.items():
        copy_skill(source, staged / name)
        if sha256_entry(staged / name) != expected_hash:
            raise InstallError(f"暫存技能雜湊不符：{name}")
    return staged


def replace_entries(client_root: Path, names: list[str], staged: Path, transaction: Path,
                    remove_names: list[str] | None = None) -> None:
    """將舊入口移入交易區後換入完整新入口。"""

    old = transaction / "old"
    old.mkdir(parents=True)
    client_root.mkdir(parents=True, exist_ok=True)
    moved_old: list[str] = []
    moved_new: list[str] = []
    try:
        for name in names + (remove_names or []):
            target = client_root / name
            if os.path.lexists(target):
                target.replace(old / name)
                moved_old.append(name)
        for name in names:
            (staged / name).replace(client_root / name)
            moved_new.append(name)
    except Exception as error:
        for name in reversed(moved_new):
            shutil.rmtree(client_root / name)
        for name in reversed(moved_old):
            (old / name).replace(client_root / name)
        raise InstallError(f"安裝交易失敗，已回復：{error}") from error


def make_snapshot(state_root: Path, active: dict[str, Any], client_root: Path) -> dict[str, Any]:
    """保存可供單步 rollback 的已驗證技能快照。"""

    snapshot_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    root = state_root / "snapshots" / snapshot_id
    content = root / "content"
    content.mkdir(parents=True)
    for name in active["entries"]:
        copy_skill(client_root / name, content / name)
    snapshot = {
        "snapshot_id": snapshot_id,
        "created_at": utc_now(),
        "version": active["version"],
        "manifest_sha256": active["manifest_sha256"],
        "entries": active["entries"],
    }
    write_json_atomic(root / "snapshot.json", snapshot)
    return snapshot


def install_or_update(args: argparse.Namespace, *, update: bool) -> dict[str, Any]:
    """安裝、收養完全相同內容，或明確更新目前技能。"""

    manifest, manifest_path = read_manifest(Path(args.manifest))
    client_root, state_root = validate_registration(
        manifest, args.registration, Path(args.client_root), Path(args.state_root)
    )
    entries = desired_entries(manifest, manifest_path)
    hashes = {name: digest for name, (_, digest) in entries.items()}
    names = list(entries)
    version = str(manifest["installation"]["candidate_version"])
    file_path = state_path(state_root, args.registration, client_root)
    state = read_state(file_path)
    actual = current_hashes(client_root, names)

    if state is None:
        if update:
            raise InstallError("找不到既有安裝，請先使用 install")
        present = [name for name, digest in actual.items() if digest is not None]
        if present and actual != hashes:
            raise InstallError("目標已有未知或不完整的同名技能，未變更")
        state = base_state(args.registration, client_root)
        if actual == hashes:
            state["active"] = active_record(version, manifest_path, hashes)
            write_json_atomic(file_path, state)
            return {"result": "adopted_identical", "version": version, "managed_entries": names}
    else:
        validate_state_target(state, args.registration, client_root)
        active = state.get("active")
        if active:
            verify_active(client_root, active)
            if active.get("version") == version and active.get("entries") == hashes:
                return {"result": "noop", "version": version, "verification": "hashes_match"}
            if not update:
                raise InstallError("來源不同；檢查差異後明確使用 update")
        elif update:
            raise InstallError("目前安裝已移除，請使用 install")

        # 新增技能不能覆蓋不屬於舊版 active 的同名入口。
        managed_before = set((active or {}).get("entries", {}))
        if any(actual[name] is not None for name in set(names) - managed_before):
            raise InstallError("新增技能與非受管理入口衝突，未變更")

    removed_names = sorted(set((state.get("active") or {}).get("entries", {})) - set(names))

    transaction = state_root / "transactions" / uuid.uuid4().hex
    snapshot: dict[str, Any] | None = None
    try:
        staged = stage_entries(entries, transaction)
        previous_active = state.get("active")
        if previous_active:
            snapshot = make_snapshot(state_root, previous_active, client_root)
            state.setdefault("history", []).append(snapshot)
        replace_entries(client_root, names, staged, transaction, removed_names)
        state["active"] = active_record(version, manifest_path, hashes)
        try:
            write_json_atomic(file_path, state)
        except Exception as state_error:
            old = transaction / "old"
            for name in names + removed_names:
                target = client_root / name
                if target.exists():
                    shutil.rmtree(target)
                backup = old / name
                if backup.exists():
                    backup.replace(target)
            if snapshot is not None:
                shutil.rmtree(state_root / "snapshots" / snapshot["snapshot_id"])
            raise InstallError(f"狀態寫入失敗，已回復技能：{state_error}") from state_error
    finally:
        if transaction.exists():
            shutil.rmtree(transaction)
    result = "updated" if update else ("reinstalled" if state.get("removed") else "installed")
    return {"result": result, "version": version, "managed_entries": names}


def rollback(args: argparse.Namespace) -> dict[str, Any]:
    """回復最近一次更新前的完整技能快照。"""

    manifest, _ = read_manifest(Path(args.manifest))
    client_root, state_root = validate_registration(
        manifest, args.registration, Path(args.client_root), Path(args.state_root)
    )
    file_path = state_path(state_root, args.registration, client_root)
    state = read_state(file_path)
    if state is None:
        raise InstallError("找不到安裝狀態")
    validate_state_target(state, args.registration, client_root)
    active = state.get("active")
    if not active:
        raise InstallError("目前沒有作用中安裝")
    verify_active(client_root, active)
    history = state.get("history")
    if not isinstance(history, list) or not history:
        raise InstallError("沒有可回復快照")
    snapshot = history[-1]
    content = state_root / "snapshots" / snapshot["snapshot_id"] / "content"
    names = list(snapshot["entries"])
    removed_names = sorted(set(active["entries"]) - set(names))
    # 快照要恢復的入口若已被其他來源占用，不能以回復為名覆蓋。
    if any(os.path.lexists(client_root / name) for name in set(names) - set(active["entries"])):
        raise InstallError("回復技能與非受管理入口衝突，未變更")
    for name, digest in snapshot["entries"].items():
        if sha256_entry(content / name) != digest:
            raise InstallError(f"回復快照缺少或損壞：{name}")

    transaction = state_root / "transactions" / uuid.uuid4().hex
    entries = {name: (content / name, snapshot["entries"][name]) for name in names}
    try:
        staged = stage_entries(entries, transaction)
        replace_entries(client_root, names, staged, transaction, removed_names)
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
            old = transaction / "old"
            for name in names + removed_names:
                target = client_root / name
                if target.exists():
                    shutil.rmtree(target)
                backup = old / name
                if backup.exists():
                    backup.replace(target)
            raise InstallError(f"回復狀態寫入失敗，已恢復回復前版本：{state_error}") from state_error
    finally:
        if transaction.exists():
            shutil.rmtree(transaction)
    return {"result": "rolled_back", "version": snapshot["version"]}


def remove(args: argparse.Namespace) -> dict[str, Any]:
    """把已驗證技能移到可復原隔離區，不刪除工作區設定。"""

    manifest, _ = read_manifest(Path(args.manifest))
    client_root, state_root = validate_registration(
        manifest, args.registration, Path(args.client_root), Path(args.state_root)
    )
    file_path = state_path(state_root, args.registration, client_root)
    state = read_state(file_path)
    if state is None:
        raise InstallError("找不到安裝狀態")
    validate_state_target(state, args.registration, client_root)
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
        state.setdefault("removed", []).append(
            {"removed_at": utc_now(), "quarantine": str(quarantine), "active": active}
        )
        state["active"] = None
        write_json_atomic(file_path, state)
    except Exception as error:
        for name in reversed(moved):
            (quarantine / name).replace(client_root / name)
        raise InstallError(f"移除失敗，已回復：{error}") from error
    return {"result": "removed_to_quarantine", "quarantine": str(quarantine)}


def status(args: argparse.Namespace) -> dict[str, Any]:
    """唯讀檢查來源、目標衝突與受管理內容。"""

    manifest, manifest_path = read_manifest(Path(args.manifest))
    client_root, state_root = validate_registration(
        manifest, args.registration, Path(args.client_root), Path(args.state_root)
    )
    entries = desired_entries(manifest, manifest_path)
    hashes = {name: digest for name, (_, digest) in entries.items()}
    actual = current_hashes(client_root, list(entries))
    state = read_state(state_path(state_root, args.registration, client_root))
    if state is None:
        present = [name for name, digest in actual.items() if digest is not None]
        if not present:
            return {"result": "available", "would_install": list(entries), "conflicts": []}
        if actual == hashes:
            return {"result": "unmanaged_identical", "would_adopt": list(entries), "conflicts": []}
        return {"result": "blocked", "conflicts": present}
    validate_state_target(state, args.registration, client_root)
    active = state.get("active")
    if not active:
        return {"result": "removed", "verification": "no_active_entries"}
    verify_active(client_root, active)
    source_version = str(manifest["installation"]["candidate_version"])
    conflicts = [name for name in entries if name not in active["entries"] and actual[name] is not None]
    if conflicts:
        return {"result": "blocked", "conflicts": conflicts}
    if active.get("version") != source_version or active.get("entries") != hashes:
        return {
            "result": "installed_update_available",
            "installed_version": active.get("version"),
            "source_version": source_version,
            "managed_entries": sorted(active["entries"]),
            "verification": "installed_hashes_match_state_source_differs",
        }
    return {
        "result": "installed",
        "version": active["version"],
        "managed_entries": sorted(active["entries"]),
        "verification": "hashes_match",
    }


def build_parser() -> argparse.ArgumentParser:
    """建立五個生命週期命令的共同介面。"""

    parser = argparse.ArgumentParser(description="管理社群媒體技能包本機候選")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("install", "update", "rollback", "remove", "status"):
        child = subparsers.add_parser(command)
        child.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
        child.add_argument("--registration", required=True)
        child.add_argument("--client-root", required=True)
        child.add_argument("--state-root", required=True)
    return parser


def main() -> int:
    """執行命令並使用 JSON 回報。"""

    args = build_parser().parse_args()
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
        else:
            raise InstallError("未知命令")
    except (InstallError, OSError) as error:
        print(json.dumps({"result": "stopped", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
