#!/usr/bin/env python3
"""比較與同步 AI 知識庫通用核心、Toolbox 發行副本與本機執行層。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SyncError(Exception):
    """代表同步設定或操作不安全。"""


@dataclass(frozen=True)
class PackageConfig:
    """同步套件的本機設定。"""

    package_id: str
    canonical_root: Path
    mirror_root: Path
    state_file: Path
    backup_root: Path
    exclude_roots: frozenset[str]
    exclude_names: frozenset[str]
    exclude_suffixes: tuple[str, ...]
    shared_skills: tuple[str, ...]
    runtime: dict[str, Any]


def resolved_absolute(value: str, field: str) -> Path:
    """確認 manifest 使用明確的絕對路徑。"""

    path = Path(value).expanduser()
    if not path.is_absolute():
        raise SyncError(f"{field} 必須是絕對路徑：{value}")
    return path.resolve()


def validate_scoped_root(path: Path, field: str) -> None:
    """拒絕把過度寬廣的目錄當成同步目標。"""

    forbidden = {Path("/").resolve(), Path.home().resolve()}
    if path in forbidden or len(path.parts) < 4:
        raise SyncError(f"{field} 範圍過大，不允許同步：{path}")
    if not path.is_dir():
        raise SyncError(f"{field} 不存在或不是目錄：{path}")


def load_config(manifest_path: Path) -> PackageConfig:
    """讀取並驗證本機 TOML manifest。"""

    if not manifest_path.is_file():
        raise SyncError(f"找不到同步 manifest：{manifest_path}")
    with manifest_path.open("rb") as file:
        data = tomllib.load(file)

    if data.get("schema_version") != 1:
        raise SyncError("只支援 schema_version = 1")

    package = data["package"]
    canonical_root = resolved_absolute(package["canonical_root"], "canonical_root")
    mirror_root = resolved_absolute(package["mirror_root"], "mirror_root")
    state_file = resolved_absolute(package["state_file"], "state_file")
    backup_root = resolved_absolute(package["backup_root"], "backup_root")
    validate_scoped_root(canonical_root, "canonical_root")
    validate_scoped_root(mirror_root, "mirror_root")
    if canonical_root == mirror_root:
        raise SyncError("canonical_root 與 mirror_root 不得相同")

    runtime = data.get("runtime", {"enabled": False})
    if runtime.get("enabled"):
        runtime = dict(runtime)
        runtime["root"] = str(resolved_absolute(runtime["root"], "runtime.root"))

    return PackageConfig(
        package_id=package["id"],
        canonical_root=canonical_root,
        mirror_root=mirror_root,
        state_file=state_file,
        backup_root=backup_root,
        exclude_roots=frozenset(package.get("exclude_roots", [])),
        exclude_names=frozenset(package.get("exclude_names", [])),
        exclude_suffixes=tuple(package.get("exclude_suffixes", [])),
        shared_skills=tuple(package.get("shared_skills", [])),
        runtime=runtime,
    )


def is_excluded(relative: Path, config: PackageConfig) -> bool:
    """判斷相對路徑是否屬於私人資料或工具暫存。"""

    if not relative.parts:
        return False
    if relative.parts[0] in config.exclude_roots:
        return True
    if any(part in config.exclude_names for part in relative.parts):
        return True
    return any(relative.name.endswith(suffix) for suffix in config.exclude_suffixes)


def file_entry(path: Path) -> dict[str, Any]:
    """建立可比較的檔案或 symlink 摘要。"""

    if path.is_symlink():
        return {"kind": "symlink", "target": os.readlink(path)}
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    mode = path.stat().st_mode
    return {
        "kind": "file",
        "sha256": digest,
        "executable": bool(mode & stat.S_IXUSR),
    }


def collect_entries(root: Path, config: PackageConfig) -> dict[str, dict[str, Any]]:
    """收集套件內所有未排除檔案，不跟隨 symlink。"""

    entries: dict[str, dict[str, Any]] = {}
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        kept_directories: list[str] = []
        for directory in directories:
            candidate = current_path / directory
            relative = candidate.relative_to(root)
            if not is_excluded(relative, config):
                kept_directories.append(directory)
        directories[:] = kept_directories

        for filename in files:
            path = current_path / filename
            relative = path.relative_to(root)
            if is_excluded(relative, config):
                continue
            entries[relative.as_posix()] = file_entry(path)

        for directory in directories:
            path = current_path / directory
            if path.is_symlink():
                relative = path.relative_to(root)
                entries[relative.as_posix()] = file_entry(path)

    return dict(sorted(entries.items()))


def tree_hash(entries: dict[str, dict[str, Any]]) -> str:
    """以排序後的相對路徑與內容摘要計算整棵樹的雜湊。"""

    payload = json.dumps(entries, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def compare_entries(
    canonical: dict[str, dict[str, Any]],
    mirror: dict[str, dict[str, Any]],
) -> list[str]:
    """列出兩邊新增、刪除或內容不同的相對路徑。"""

    return sorted(
        path
        for path in set(canonical) | set(mirror)
        if canonical.get(path) != mirror.get(path)
    )


def load_state(config: PackageConfig) -> dict[str, Any] | None:
    """讀取最近一次由工具接受的同步狀態。"""

    if not config.state_file.is_file():
        return None
    try:
        return json.loads(config.state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SyncError(f"無法讀取 sync state：{error}") from error


def classify_status(
    canonical_hash: str,
    mirror_hash: str,
    equal: bool,
    state: dict[str, Any] | None,
) -> str:
    """依上次基準判斷哪一邊發生變更。"""

    if state is None:
        return "synced-unrecorded" if equal else "unknown-divergence"

    canonical_changed = canonical_hash != state.get("canonical_tree")
    mirror_changed = mirror_hash != state.get("mirror_tree")
    if equal:
        return "synced-new" if canonical_changed or mirror_changed else "synced"
    if canonical_changed and not mirror_changed:
        return "canonical-ahead"
    if mirror_changed and not canonical_changed:
        return "mirror-ahead"
    return "conflict"


def current_status(config: PackageConfig) -> dict[str, Any]:
    """取得不寫檔的同步狀態。"""

    canonical = collect_entries(config.canonical_root, config)
    mirror = collect_entries(config.mirror_root, config)
    differences = compare_entries(canonical, mirror)
    canonical_hash = tree_hash(canonical)
    mirror_hash = tree_hash(mirror)
    state = load_state(config)
    return {
        "package": config.package_id,
        "status": classify_status(
            canonical_hash,
            mirror_hash,
            not differences,
            state,
        ),
        "canonical_tree": canonical_hash,
        "mirror_tree": mirror_hash,
        "canonical_files": len(canonical),
        "mirror_files": len(mirror),
        "difference_count": len(differences),
        "differences": differences,
    }


def write_state(config: PackageConfig, status: dict[str, Any]) -> None:
    """只在兩邊一致時記錄新基準。"""

    if status["difference_count"]:
        raise SyncError("兩邊仍有差異，不能記錄為同步完成")
    payload = {
        "schema_version": 1,
        "package": config.package_id,
        "canonical_tree": status["canonical_tree"],
        "mirror_tree": status["mirror_tree"],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    config.state_file.parent.mkdir(parents=True, exist_ok=True)
    config.state_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def runtime_errors(config: PackageConfig) -> list[str]:
    """驗證 newsletter 等本機執行層的 symlink。"""

    runtime = config.runtime
    if not runtime.get("enabled"):
        return []

    root = Path(runtime["root"]).resolve()
    validate_scoped_root(root, "runtime.root")
    skills_dir = (root / runtime["skills_dir"]).resolve()
    errors: list[str] = []

    for skill in config.shared_skills:
        link = root / runtime["skills_dir"] / skill
        expected = (config.canonical_root / "skills" / skill).resolve()
        if not link.is_symlink():
            errors.append(f"缺少技能 symlink：{link}")
            continue
        if link.resolve() != expected:
            errors.append(f"技能 symlink 指向錯誤：{link} -> {link.resolve()}")

    for relative in runtime.get("client_links", []):
        link = root / relative
        if not link.is_symlink():
            errors.append(f"缺少用戶端技能入口：{link}")
            continue
        if link.resolve() != skills_dir:
            errors.append(f"用戶端技能入口指向錯誤：{link} -> {link.resolve()}")

    return errors


def print_result(payload: dict[str, Any], json_output: bool) -> None:
    """以人類可讀或 JSON 格式輸出結果。"""

    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print(f"package: {payload['package']}")
    print(f"status: {payload['status']}")
    print(f"canonical files: {payload['canonical_files']}")
    print(f"mirror files: {payload['mirror_files']}")
    print(f"differences: {payload['difference_count']}")
    for path in payload["differences"][:50]:
        print(f"- {path}")
    if payload["difference_count"] > 50:
        print(f"- 另有 {payload['difference_count'] - 50} 個差異")


def sync_plan(status: dict[str, Any]) -> list[str]:
    """依目前狀態提供不執行修改的下一步。"""

    value = status["status"]
    if value == "synced":
        return ["兩邊與已記錄基準一致，不需同步。"]
    if value in {"synced-unrecorded", "synced-new"}:
        return ["兩邊內容一致；驗證後執行 record 更新本機基準。"]
    if value == "canonical-ahead":
        return ["通用核心有單邊變更；檢查差異後從 canonical 同步到 mirror。"]
    if value == "mirror-ahead":
        return ["Toolbox 副本有單邊變更；檢查差異後先回饋 canonical，再重新同步 mirror。"]
    if value == "unknown-divergence":
        return ["沒有上次基準且兩邊不同；人工確認正確來源後才能指定同步方向。"]
    return ["兩邊都在上次基準後變更且內容不同；停止自動同步並人工合併。"]


def ensure_inside(root: Path, path: Path) -> None:
    """確認即將修改的檔案仍在精確目標目錄內。"""

    resolved_root = root.resolve()
    resolved_parent = path.parent.resolve()
    if resolved_parent != resolved_root and resolved_root not in resolved_parent.parents:
        raise SyncError(f"目標超出允許範圍：{path}")


def backup_existing(path: Path, root: Path, backup_dir: Path) -> None:
    """在覆寫或刪除前建立可還原副本。"""

    if not path.exists() and not path.is_symlink():
        return
    relative = path.relative_to(root)
    backup = backup_dir / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        os.symlink(os.readlink(path), backup)
    else:
        shutil.copy2(path, backup)


def copy_source(source: Path, target: Path) -> None:
    """將單一來源檔案或 symlink 複製到目標。"""

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    if source.is_symlink():
        os.symlink(os.readlink(source), target)
    else:
        shutil.copy2(source, target)


def synchronize(
    config: PackageConfig,
    source_side: str,
    apply_changes: bool,
) -> dict[str, Any]:
    """依明確方向規劃或執行白名單套件同步。"""

    source_root = (
        config.canonical_root if source_side == "canonical" else config.mirror_root
    )
    target_root = (
        config.mirror_root if source_side == "canonical" else config.canonical_root
    )
    source_entries = collect_entries(source_root, config)
    target_entries = collect_entries(target_root, config)
    changed = compare_entries(source_entries, target_entries)

    actions = []
    for relative in changed:
        if relative not in source_entries:
            action = "delete"
        elif relative not in target_entries:
            action = "create"
        else:
            action = "replace"
        actions.append({"action": action, "path": relative})

    result = {
        "package": config.package_id,
        "source": source_side,
        "applied": apply_changes,
        "action_count": len(actions),
        "actions": actions,
    }
    if not apply_changes or not actions:
        return result

    validate_scoped_root(source_root, "source_root")
    validate_scoped_root(target_root, "target_root")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = config.backup_root / f"{timestamp}-{source_side}-to-target"
    backup_dir.mkdir(parents=True, exist_ok=False)

    for action in actions:
        relative = Path(action["path"])
        source = source_root / relative
        target = target_root / relative
        ensure_inside(target_root, target)
        backup_existing(target, target_root, backup_dir)
        if action["action"] == "delete":
            if target.exists() or target.is_symlink():
                target.unlink()
            continue
        copy_source(source, target)

    (backup_dir / "sync-actions.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    after = current_status(config)
    if after["difference_count"]:
        raise SyncError("同步後仍有差異，已保留備份並停止")
    write_state(config, after)
    result["backup_dir"] = str(backup_dir)
    result["result_tree"] = after["canonical_tree"]
    return result


def build_parser() -> argparse.ArgumentParser:
    """建立命令列介面。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    subparsers.add_parser("plan")
    subparsers.add_parser("verify")
    subparsers.add_parser("record")
    sync = subparsers.add_parser("sync")
    sync.add_argument("--from", choices=("canonical", "mirror"), required=True)
    sync.add_argument("--apply", action="store_true")
    return parser


def main() -> int:
    """執行同步命令。"""

    args = build_parser().parse_args()
    try:
        config = load_config(args.manifest.resolve())
        status = current_status(config)

        if args.command == "status":
            print_result(status, args.json_output)
            return 0

        if args.command == "plan":
            payload = dict(status)
            payload["plan"] = sync_plan(status)
            if args.json_output:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print_result(status, False)
                for step in payload["plan"]:
                    print(f"plan: {step}")
            return 0

        if args.command == "verify":
            errors = runtime_errors(config)
            payload = dict(status)
            payload["runtime_errors"] = errors
            print_result(payload, args.json_output)
            for error in errors:
                print(f"runtime error: {error}", file=sys.stderr)
            return 0 if not status["difference_count"] and not errors else 2

        if args.command == "record":
            write_state(config, status)
            print("已記錄目前一致狀態。")
            return 0

        result = synchronize(config, getattr(args, "from"), args.apply)
        if args.json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            mode = "已執行" if args.apply else "預覽"
            print(f"{mode} {result['action_count']} 個同步動作。")
            for action in result["actions"][:50]:
                print(f"- {action['action']}: {action['path']}")
            if result.get("backup_dir"):
                print(f"backup: {result['backup_dir']}")
        return 0
    except (KeyError, OSError, tomllib.TOMLDecodeError, SyncError) as error:
        print(f"同步失敗：{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
