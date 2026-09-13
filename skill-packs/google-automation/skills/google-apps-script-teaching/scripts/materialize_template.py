#!/usr/bin/env python3
"""將已驗收的教學模板安全複製或升級到學生專案。"""

from __future__ import annotations

import argparse
import filecmp
import json
import re
import shutil
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
TEACHING_ROOT = SCRIPT_PATH.parents[1]
REPOSITORY_ROOT = SCRIPT_PATH.parents[3]
TEMPLATES_ROOT = TEACHING_ROOT / "templates"
CATALOG_PATH = TEMPLATES_ROOT / "catalog.json"
ACTIVITY_LESSON_ID_PATTERN = re.compile(
    r"^activity-registration/lesson-(\d{2})$"
)


def load_catalog() -> dict[str, object]:
    """讀取模板登錄表。"""
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def find_template(catalog: dict[str, object], template_id: str) -> dict[str, object]:
    """依固定 ID 取得模板，避免讓外部輸入直接拼接檔案路徑。"""
    templates = catalog.get("templates", [])
    if not isinstance(templates, list):
        raise ValueError("模板登錄表的 templates 格式不正確")

    for item in templates:
        if isinstance(item, dict) and item.get("id") == template_id:
            return item
    raise ValueError(f"找不到模板：{template_id}")


def is_inside(path: Path, parent: Path) -> bool:
    """判斷路徑是否位於指定目錄內。"""
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_relative_path(raw_path: str) -> Path:
    """只允許安全的相對檔案路徑。"""
    path = Path(raw_path)
    if path.is_absolute() or ".." in path.parts or raw_path.strip() == "":
        raise ValueError(f"模板包含不安全路徑：{raw_path}")
    return path


def validate_template(
    template: dict[str, object],
) -> tuple[Path, dict[Path, Path]]:
    """驗證模板狀態與檔案清單，回傳來源根目錄及檔案對照。"""
    if template.get("status") != "validated":
        raise ValueError(f"模板尚未完成驗收：{template.get('id', '未知模板')}")

    source_root_value = template.get("sourceRoot")
    files_value = template.get("files")
    if not isinstance(source_root_value, str) or not isinstance(files_value, list):
        raise ValueError("已驗收模板缺少 sourceRoot 或 files")

    source_root = (TEMPLATES_ROOT / source_root_value).resolve()
    if not is_inside(source_root, TEMPLATES_ROOT.resolve()):
        raise ValueError("模板來源路徑超出技能模板目錄")

    source_files: dict[Path, Path] = {}
    for raw_file in files_value:
        if not isinstance(raw_file, str):
            raise ValueError("模板檔案清單只能包含字串")
        relative_file = validate_relative_path(raw_file)
        if relative_file in source_files:
            raise ValueError(f"模板檔案清單包含重複路徑：{relative_file}")

        source = (source_root / relative_file).resolve()
        if not source.is_file() or not is_inside(source, source_root):
            raise ValueError(f"模板來源檔案不存在或不安全：{relative_file}")
        source_files[relative_file] = source

    return source_root, source_files


def validate_destination(destination: Path) -> Path:
    """確認學生專案位於 Learn-GAS 儲存庫之外。"""
    resolved = destination.resolve()
    if is_inside(resolved, REPOSITORY_ROOT.resolve()):
        raise ValueError("學生專案不得建立在 Learn-GAS 技能儲存庫內")
    if resolved.exists() and not resolved.is_dir():
        raise ValueError("學生專案目的地不是資料夾")
    return resolved


def controlled_destination_files(destination: Path) -> dict[Path, Path]:
    """列出模板會管理的 .claspignore 與 src 內所有檔案。"""
    controlled: dict[Path, Path] = {}
    claspignore = destination / ".claspignore"
    if claspignore.exists():
        if not claspignore.is_file():
            raise ValueError("目的地的 .claspignore 不是一般檔案")
        controlled[Path(".claspignore")] = claspignore

    source_directory = destination / "src"
    if source_directory.exists():
        if not source_directory.is_dir():
            raise ValueError("目的地的 src 不是資料夾")
        for path in source_directory.rglob("*"):
            if path.is_file():
                controlled[path.relative_to(destination)] = path
    return controlled


def validate_target_parent(target: Path, destination: Path) -> None:
    """在寫入前確認目的檔案的既有上層路徑都是資料夾。"""
    parent = target.parent
    while parent != destination:
        if parent.exists() and not parent.is_dir():
            raise ValueError(f"目的檔案的上層路徑不是資料夾：{parent}")
        parent = parent.parent


def inspect_clasp_bootstrap(destination: Path) -> list[Path]:
    """只接受 clasp 剛建立、尚未加入業務程式的初始 src。"""
    source_directory = destination / "src"
    if not source_directory.exists():
        return []
    if not source_directory.is_dir():
        raise ValueError("目的地的 src 不是資料夾")

    actual_files = {
        path.relative_to(source_directory).as_posix(): path
        for path in source_directory.rglob("*")
        if path.is_file()
    }
    allowed_files = {"Code.gs", "appsscript.json"}
    unexpected = sorted(set(actual_files) - allowed_files)
    if unexpected:
        raise ValueError(f"src 已有非 clasp 初始檔案，不會取代：{unexpected}")

    code_path = actual_files.get("Code.gs")
    if code_path is not None:
        code = code_path.read_text(encoding="utf-8")
        without_comments = re.sub(r"/\*.*?\*/|//[^\n]*", "", code, flags=re.DOTALL)
        if not re.fullmatch(
            r"\s*function\s+myFunction\s*\(\s*\)\s*\{\s*\}\s*",
            without_comments,
        ):
            raise ValueError("Code.gs 不是可辨識的 clasp 空白初始函式")

    manifest_path = actual_files.get("appsscript.json")
    if manifest_path is not None:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        allowed_keys = {
            "timeZone",
            "dependencies",
            "exceptionLogging",
            "runtimeVersion",
        }
        unexpected_keys = sorted(set(manifest) - allowed_keys)
        if unexpected_keys:
            raise ValueError(
                f"appsscript.json 已有非初始設定，不會取代：{unexpected_keys}"
            )
        if manifest.get("dependencies", {}) != {}:
            raise ValueError("appsscript.json 已有服務相依，不會取代")

    return [code_path] if code_path is not None else []


def build_copy_plan(
    template: dict[str, object],
    destination: Path,
    replace_clasp_bootstrap: bool,
) -> list[tuple[Path | None, Path, str]]:
    """先完成全部衝突檢查，再建立複製計畫。"""
    _, source_files = validate_template(template)
    destination = validate_destination(destination)

    bootstrap_files = (
        inspect_clasp_bootstrap(destination) if replace_clasp_bootstrap else []
    )
    plan: list[tuple[Path | None, Path, str]] = []
    for relative_file, source in source_files.items():
        target = (destination / relative_file).resolve()

        if not is_inside(target, destination):
            raise ValueError(f"模板目的檔案超出學生專案：{relative_file}")
        validate_target_parent(target, destination)

        if target.exists():
            if not target.is_file():
                raise ValueError(f"目的路徑不是一般檔案：{target}")
            if filecmp.cmp(source, target, shallow=False):
                plan.append((source, target, "略過"))
                continue
            if (
                replace_clasp_bootstrap
                and relative_file.as_posix() == "src/appsscript.json"
            ):
                plan.append((source, target, "取代初始檔"))
                continue
            raise FileExistsError(f"目的檔案已有不同內容，不會覆寫：{target}")

        plan.append((source, target, "複製"))

    listed_targets = {target for _, target, _ in plan}
    for bootstrap_file in bootstrap_files:
        if bootstrap_file not in listed_targets:
            plan.append((None, bootstrap_file, "移除初始檔"))

    return plan


def parse_activity_lesson_number(template: dict[str, object]) -> int:
    """從第二階段模板 ID 取得課次編號。"""
    template_id = template.get("id")
    if not isinstance(template_id, str):
        raise ValueError("第二階段模板缺少有效 ID")
    match = ACTIVITY_LESSON_ID_PATTERN.fullmatch(template_id)
    if match is None:
        raise ValueError(f"受控升級只適用於第二階段累積模板：{template_id}")
    return int(match.group(1))


def files_match_snapshot(
    actual_files: dict[Path, Path],
    snapshot_files: dict[Path, Path],
) -> bool:
    """確認受控檔案集合與指定快照完全一致。"""
    if set(actual_files) != set(snapshot_files):
        return False
    return all(
        filecmp.cmp(snapshot_files[relative], actual_files[relative], shallow=False)
        for relative in snapshot_files
    )


def build_upgrade_plan(
    previous_template: dict[str, object],
    target_template: dict[str, object],
    destination: Path,
) -> list[tuple[Path | None, Path, str]]:
    """建立相鄰課次的受控升級計畫，任何衝突都在寫入前停止。"""
    _, previous_files = validate_template(previous_template)
    _, target_files = validate_template(target_template)
    destination = validate_destination(destination)

    previous_number = parse_activity_lesson_number(previous_template)
    target_number = parse_activity_lesson_number(target_template)
    if target_number != previous_number + 1:
        raise ValueError(
            "第二階段只能依序升級相鄰課次："
            f"lesson-{previous_number:02d} → lesson-{target_number:02d}"
        )

    removed_files = sorted(set(previous_files) - set(target_files))
    if removed_files:
        display = [path.as_posix() for path in removed_files]
        raise ValueError(f"累積模板不得移除前課檔案：{display}")

    for relative in target_files:
        target = (destination / relative).resolve()
        if not is_inside(target, destination):
            raise ValueError(f"模板目的檔案超出學生專案：{relative}")
        validate_target_parent(target, destination)

    actual_files = controlled_destination_files(destination)

    # 已完整升級時安全略過，讓同一命令可以重跑。
    if files_match_snapshot(actual_files, target_files):
        return [
            (source, (destination / relative).resolve(), "略過")
            for relative, source in target_files.items()
        ]

    missing_files = sorted(set(previous_files) - set(actual_files))
    extra_files = sorted(set(actual_files) - set(previous_files))
    if missing_files:
        display = [path.as_posix() for path in missing_files]
        raise FileExistsError(f"學生專案缺少前課受控檔案，不會升級：{display}")
    if extra_files:
        display = [path.as_posix() for path in extra_files]
        raise FileExistsError(f"學生專案含有前課快照以外的受控檔案，不會升級：{display}")

    for relative, previous_source in previous_files.items():
        actual = actual_files[relative]
        if not filecmp.cmp(previous_source, actual, shallow=False):
            raise FileExistsError(
                f"學生專案的前課檔案已有不同內容，不會升級：{actual}"
            )

    plan: list[tuple[Path | None, Path, str]] = []
    for relative, target_source in target_files.items():
        target = (destination / relative).resolve()
        if relative not in previous_files:
            if target.exists():
                raise FileExistsError(f"新課檔案已存在，不會覆寫：{target}")
            plan.append((target_source, target, "新增"))
            continue

        previous_source = previous_files[relative]
        if filecmp.cmp(previous_source, target_source, shallow=False):
            plan.append((target_source, target, "略過"))
        else:
            plan.append((target_source, target, "升級"))
    return plan


def execute_plan(
    plan: list[tuple[Path | None, Path, str]],
    dry_run: bool,
) -> None:
    """執行已完成全部檢查的複製或升級計畫。"""
    if dry_run:
        return

    for source, target, action in plan:
        if action == "略過":
            continue
        if action == "移除初始檔":
            target.unlink()
            continue
        if source is None:
            raise ValueError(f"複製計畫缺少來源：{target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def materialize(
    template_id: str,
    destination: Path,
    dry_run: bool,
    replace_clasp_bootstrap: bool,
) -> list[tuple[Path | None, Path, str]]:
    """安全具現化指定模板。"""
    catalog = load_catalog()
    template = find_template(catalog, template_id)
    match = ACTIVITY_LESSON_ID_PATTERN.fullmatch(template_id)
    if match is not None and int(match.group(1)) > 1:
        raise ValueError(
            "第二階段第 2 至第 8 課不得直接複製；"
            "請使用 --upgrade-from 從相鄰前課受控升級"
        )
    plan = build_copy_plan(template, destination, replace_clasp_bootstrap)
    execute_plan(plan, dry_run)
    return plan


def upgrade_materialized_template(
    previous_template_id: str,
    target_template_id: str,
    destination: Path,
    dry_run: bool,
) -> list[tuple[Path | None, Path, str]]:
    """將完全符合前課快照的學生專案安全升級到相鄰下一課。"""
    catalog = load_catalog()
    previous_template = find_template(catalog, previous_template_id)
    target_template = find_template(catalog, target_template_id)
    plan = build_upgrade_plan(previous_template, target_template, destination)
    execute_plan(plan, dry_run)
    return plan


def list_templates(catalog: dict[str, object]) -> None:
    """列出模板狀態，不顯示任何私人專案資訊。"""
    templates = catalog.get("templates", [])
    if not isinstance(templates, list):
        raise ValueError("模板登錄表格式不正確")
    for item in templates:
        if not isinstance(item, dict):
            continue
        print(
            f"{item.get('id', '未知')}｜"
            f"{item.get('status', '未知')}｜"
            f"{item.get('displayName', '')}"
        )


def parse_args() -> argparse.Namespace:
    """解析命令列參數。"""
    parser = argparse.ArgumentParser(
        description="將已驗收的 Learn-GAS 教學模板複製到學生專案。"
    )
    parser.add_argument("--template", help="catalog.json 中的模板 ID")
    parser.add_argument("--destination", type=Path, help="學生專案絕對路徑")
    parser.add_argument("--dry-run", action="store_true", help="只顯示複製計畫")
    parser.add_argument(
        "--replace-clasp-bootstrap",
        action="store_true",
        help="只取代可驗證的 clasp 空白 Code.gs 與初始 manifest",
    )
    parser.add_argument(
        "--upgrade-from",
        help="前一課的模板 ID；只允許第二階段相鄰課次受控升級",
    )
    parser.add_argument("--list", action="store_true", help="列出所有模板狀態")
    return parser.parse_args()


def main() -> int:
    """執行模板列出或安全複製。"""
    args = parse_args()
    try:
        catalog = load_catalog()
        if args.list:
            list_templates(catalog)
            return 0

        if not args.template or args.destination is None:
            raise ValueError("必須同時提供 --template 與 --destination")
        if not args.destination.is_absolute():
            raise ValueError("--destination 必須使用絕對路徑")

        if args.upgrade_from and args.replace_clasp_bootstrap:
            raise ValueError(
                "--upgrade-from 不得與 --replace-clasp-bootstrap 同時使用"
            )
        if args.upgrade_from:
            plan = upgrade_materialized_template(
                args.upgrade_from,
                args.template,
                args.destination,
                args.dry_run,
            )
            success_message = "[成功] 模板升級完成"
        else:
            plan = materialize(
                args.template,
                args.destination,
                args.dry_run,
                args.replace_clasp_bootstrap,
            )
            success_message = "[成功] 模板處理完成"
        for _, target, action in plan:
            print(f"[{action}] {target}")
        print(f"{success_message}｜檔案數={len(plan)}")
        return 0
    except (FileExistsError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"[失敗] 無法建立教學模板｜原因：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
