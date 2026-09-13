#!/usr/bin/env python3
"""建立並安全更新 Learn-GAS 全課程進度。"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path


ALLOWED_STATES = {
    "not_started",
    "local_ready",
    "awaiting_push_confirmation",
    "ui_validation",
    "blocked",
    "completed",
}
ALLOWED_TEMPLATE_STATES = {"pending", "validated"}
PHASE_LABELS = {1: "第一階段", 2: "第二階段"}
PHASE_ITEM_COUNTS = {1: 5, 2: 8}
PHASE_ONE_LESSON_NAMES = {
    1: "家庭支出記錄表",
    2: "批次信封版面產生器",
    3: "教師隨機測驗與成績報表",
    4: "指定資料夾檔案上傳記錄器",
    5: "個人化批次郵件寄送器",
}
PHASE_ONE_LEGACY_MARKERS = {
    1: ("案例一", "案例 1", "案例1", "家庭支出記錄表"),
    2: ("案例二", "案例 2", "案例2", "批次信封版面產生器"),
    3: ("案例三", "案例 3", "案例3", "教師隨機測驗與成績報表"),
    4: ("案例四", "案例 4", "案例4", "指定資料夾檔案上傳記錄器"),
    5: ("案例五", "案例 5", "案例5", "個人化批次郵件寄送器"),
}
LEGACY_PHASE_ONE_COMPLETE_SUMMARIES = (
    "五個生活應用入門案例均已完成",
    "第一階段五個案例均已完成",
)
PROGRESS_RELATIVE_PATH = Path("docs/course-progress.md")
SCRIPT_PATH = Path(__file__).resolve()
TEACHING_ROOT = SCRIPT_PATH.parents[1]
REPOSITORY_ROOT = SCRIPT_PATH.parents[3]
PROGRESS_TEMPLATE_PATH = TEACHING_ROOT / "examples" / "course-progress-template.md"
PRIVATE_PATTERNS = (
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    re.compile(r"/Users/|[A-Za-z]:\\Users\\"),
    re.compile(
        r"\b(?:script|spreadsheet|form|folder|deployment)[ _-]?id\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:token|secret|private[_ -]?key|password)\b", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9_-]{24,}\b"),
)


def validate_safe_text(label: str, value: str) -> str:
    """拒絕可能包含網址、私人 ID、Email、秘密或表格破壞字元的紀錄。"""
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label}不可空白")
    if "\n" in normalized or "\r" in normalized or "|" in normalized:
        raise ValueError(f"{label}不可包含換行或直線符號")
    if any(pattern.search(normalized) for pattern in PRIVATE_PATTERNS):
        raise ValueError(f"{label}疑似包含私人資料或秘密，不會寫入")
    return normalized


def validate_checked_date(checked_date: str | None) -> str:
    """取得 YYYY-MM-DD 日期，避免把任意文字寫進進度檔。"""
    effective_date = checked_date or date.today().isoformat()
    try:
        date.fromisoformat(effective_date)
    except ValueError as error:
        raise ValueError("--checked-date 必須使用 YYYY-MM-DD") from error
    return effective_date


def resolve_progress_path(destination: Path) -> Path:
    """解析安全的課程工作區進度路徑。"""
    if not destination.is_absolute():
        raise ValueError("--destination 必須使用絕對路徑")

    destination_root = destination.resolve()
    try:
        destination_root.relative_to(REPOSITORY_ROOT.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("課程工作區不得位於 Learn-GAS 技能儲存庫內")

    progress_path = (destination_root / PROGRESS_RELATIVE_PATH).resolve()
    try:
        progress_path.relative_to(destination_root)
    except ValueError as error:
        raise ValueError("課程進度路徑超出課程工作區") from error
    return progress_path


def initialize_progress(destination: Path) -> bool:
    """第一次開始任一階段時建立統一進度，已有檔案則完整保留。"""
    progress_path = resolve_progress_path(destination)
    if progress_path.exists():
        if not progress_path.is_file():
            raise ValueError("課程進度路徑不是一般檔案")
        return False
    if not PROGRESS_TEMPLATE_PATH.is_file():
        raise FileNotFoundError("找不到 Learn-GAS 全課程進度範本")

    progress_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROGRESS_TEMPLATE_PATH, progress_path)
    return True


def update_checked_date(lines: list[str], effective_date: str) -> None:
    """更新課程進度的最近檢查日期。"""
    date_prefix = "- 最近檢查日期："
    date_index = next(
        (index for index, line in enumerate(lines) if line.startswith(date_prefix)),
        None,
    )
    if date_index is None:
        raise ValueError("課程進度缺少最近檢查日期")
    lines[date_index] = f"{date_prefix}{effective_date}"


def write_if_changed(progress_path: Path, original: str, lines: list[str]) -> bool:
    """內容相同時不重寫檔案。"""
    updated = "\n".join(lines) + ("\n" if original.endswith("\n") else "")
    if updated == original:
        return False
    progress_path.write_text(updated, encoding="utf-8")
    return True


def select_phase(
    destination: Path,
    phase: int,
    checked_date: str | None = None,
) -> tuple[bool, bool]:
    """初次選擇階段；第二階段開始後鎖定到第 8 課完成。"""
    if phase not in PHASE_LABELS:
        raise ValueError("--select-phase 必須是 1 或 2")

    created = initialize_progress(destination)
    progress_path = resolve_progress_path(destination)
    original = progress_path.read_text(encoding="utf-8")
    lines = original.splitlines()
    selection_prefix = "- 目前選擇："
    selection_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith(selection_prefix)
        ),
        None,
    )
    if selection_index is None:
        raise ValueError("課程進度缺少目前選擇")

    current_phase = read_selected_phase(lines)
    if (
        current_phase == 2
        and phase != 2
        and not is_phase_completed(lines, phase=2)
    ):
        raise ValueError(
            "第二階段進行中，只能中斷後從最早未完成處恢復；"
            "完成第 8 課前不能切換階段"
        )

    lines[selection_index] = (
        f"{selection_prefix}`phase-{phase}`（{PHASE_LABELS[phase]}）"
    )
    update_checked_date(lines, validate_checked_date(checked_date))
    changed = write_if_changed(progress_path, original, lines)
    return created, changed


def validate_legacy_progress_path(
    legacy_progress_path: Path,
    unified_progress_path: Path,
) -> Path:
    """確認舊進度來源是不同於統一進度的絕對一般檔案。"""
    if not legacy_progress_path.is_absolute():
        raise ValueError("--import-legacy-progress 必須使用絕對路徑")
    resolved = legacy_progress_path.resolve()
    if resolved == unified_progress_path.resolve():
        raise ValueError("舊版進度來源不得是目前的統一進度檔")
    if not resolved.is_file():
        raise ValueError("找不到可讀取的舊版課程進度檔")
    return resolved


def detect_legacy_phase_one_completions(content: str) -> set[int]:
    """只從舊版 Markdown 的明確完成文字辨識第一階段案例。"""
    if any(
        summary in content for summary in LEGACY_PHASE_ONE_COMPLETE_SUMMARIES
    ):
        return set(PHASE_ONE_LESSON_NAMES)

    completions: set[int] = set()
    completed_pattern = re.compile(
        r"(?:狀態|課程狀態)\s*[：:]\s*`?completed`?",
        re.IGNORECASE,
    )
    header_matches = list(
        re.finditer(r"(?m)^#{2,6}\s+(.+?)\s*$", content)
    )
    for index, header_match in enumerate(header_matches):
        section_end = (
            header_matches[index + 1].start()
            if index + 1 < len(header_matches)
            else len(content)
        )
        title = header_match.group(1)
        section = content[header_match.end() : section_end]
        if not completed_pattern.search(section):
            continue
        for lesson, markers in PHASE_ONE_LEGACY_MARKERS.items():
            if any(marker in title for marker in markers):
                completions.add(lesson)

    for lesson, lesson_name in PHASE_ONE_LESSON_NAMES.items():
        table_pattern = re.compile(
            rf"(?m)^\|[^|\n]*第一階段[^|\n]*\|\s*"
            rf"{lesson}\.\s*{re.escape(lesson_name)}\s*\|\s*"
            r"`?completed`?\s*\|"
        )
        if table_pattern.search(content):
            completions.add(lesson)
    return completions


def import_legacy_phase_one_progress(
    destination: Path,
    legacy_progress_paths: list[Path],
    checked_date: str | None = None,
) -> tuple[list[int], bool]:
    """把舊版第一階段明確完成證據安全匯入統一進度。"""
    if not legacy_progress_paths:
        raise ValueError("必須提供至少一個 --import-legacy-progress")

    progress_path = resolve_progress_path(destination)
    completed_lessons: set[int] = set()
    seen_sources: set[Path] = set()
    for raw_source in legacy_progress_paths:
        source = validate_legacy_progress_path(raw_source, progress_path)
        if source in seen_sources:
            continue
        seen_sources.add(source)
        detected = detect_legacy_phase_one_completions(
            source.read_text(encoding="utf-8")
        )
        if not detected:
            raise ValueError("舊版進度檔沒有可辨識的第一階段完成證據")
        completed_lessons.update(detected)

    if not completed_lessons:
        raise ValueError("沒有可匯入的第一階段完成證據")

    initialize_progress(destination)
    original = progress_path.read_text(encoding="utf-8")
    lines = original.splitlines()

    # 先完成所有衝突檢查，避免只更新一部分案例。
    for lesson in sorted(completed_lessons):
        current_status = read_progress_status(lines, lesson, phase=1)
        if current_status not in {"not_started", "completed"}:
            raise ValueError(
                f"第一階段第 {lesson} 個案例已有進行中的統一進度，"
                "不會以舊版紀錄覆寫"
            )

    imported_lessons: list[int] = []
    for lesson in sorted(completed_lessons):
        row_index, cells, field_indexes = find_progress_row(
            lines,
            lesson,
            phase=1,
        )
        status_index, local_index, remote_index, template_index, next_index = (
            field_indexes
        )
        if cells[status_index].strip("`") == "completed":
            continue

        cells[status_index] = "`completed`"
        cells[local_index] = "舊版驗收紀錄"
        cells[remote_index] = "既有課程完成證據已核對"
        cells[template_index] = "`validated`"
        cells[next_index] = "已完成，可自由選擇其他案例"
        lines[row_index] = "| " + " | ".join(cells[1:-1]) + " |"
        imported_lessons.append(lesson)

    if is_phase_completed(lines, phase=1):
        for lesson in imported_lessons:
            row_index, cells, field_indexes = find_progress_row(
                lines,
                lesson,
                phase=1,
            )
            cells[field_indexes[4]] = "第一階段完成"
            lines[row_index] = "| " + " | ".join(cells[1:-1]) + " |"

    update_checked_date(lines, validate_checked_date(checked_date))
    changed = write_if_changed(progress_path, original, lines)
    return sorted(completed_lessons), changed


def find_progress_row(
    lines: list[str],
    lesson: int,
    phase: int | None,
) -> tuple[int, list[str], tuple[int, int, int, int, int]]:
    """找出統一格式或既有第二階段格式的課程列與欄位索引。"""
    if phase is None:
        row_pattern = re.compile(rf"^\|\s*{lesson}\.\s")
        expected_cell_count = 8
        field_indexes = (2, 3, 4, 5, 6)
    else:
        phase_label = PHASE_LABELS[phase]
        row_pattern = re.compile(rf"^\|\s*{phase_label}\s*\|\s*{lesson}\.\s")
        expected_cell_count = 9
        field_indexes = (3, 4, 5, 6, 7)

    row_index = next(
        (index for index, line in enumerate(lines) if row_pattern.match(line)),
        None,
    )
    if row_index is None:
        phase_text = f"{PHASE_LABELS[phase]}第 " if phase is not None else "第 "
        raise ValueError(f"課程進度表找不到{phase_text}{lesson} 課")

    cells = [cell.strip() for cell in lines[row_index].split("|")]
    if (
        len(cells) != expected_cell_count
        or cells[0] != ""
        or cells[-1] != ""
    ):
        raise ValueError(f"第 {lesson} 課進度列格式不正確")
    return row_index, cells, field_indexes


def read_selected_phase(lines: list[str]) -> int | None:
    """讀取統一進度目前選擇的階段。"""
    selection_prefix = "- 目前選擇："
    selection_line = next(
        (line for line in lines if line.startswith(selection_prefix)),
        None,
    )
    if selection_line is None:
        raise ValueError("課程進度缺少目前選擇")
    if "`not_selected`" in selection_line:
        return None
    for phase, label in PHASE_LABELS.items():
        if f"`phase-{phase}`（{label}）" in selection_line:
            return phase
    raise ValueError("課程進度的目前選擇格式不正確")


def read_progress_status(
    lines: list[str],
    lesson: int,
    phase: int | None,
) -> str:
    """讀取指定課程項目的狀態。"""
    _row_index, cells, field_indexes = find_progress_row(lines, lesson, phase)
    status_index = field_indexes[0]
    return cells[status_index].strip("`")


def is_phase_completed(lines: list[str], phase: int) -> bool:
    """確認指定階段所有項目均已完成。"""
    return all(
        read_progress_status(lines, lesson, phase) == "completed"
        for lesson in range(1, PHASE_ITEM_COUNTS[phase] + 1)
    )


def validate_phase_two_sequence(
    lines: list[str],
    lesson: int,
    status: str,
    phase: int | None,
) -> None:
    """第二階段只能依序前進，不能跳過尚未完成的前一課。"""
    if phase not in {None, 2} or lesson <= 1 or status == "not_started":
        return

    for previous_lesson in range(1, lesson):
        if read_progress_status(lines, previous_lesson, phase) != "completed":
            raise ValueError(
                f"第二階段必須先完成第 {previous_lesson} 課，"
                f"才能開始第 {lesson} 課"
            )


def update_progress(
    destination: Path,
    lesson: int,
    status: str,
    local_version: str | None = None,
    remote_evidence: str | None = None,
    template_status: str | None = None,
    next_checkpoint: str | None = None,
    checked_date: str | None = None,
    phase: int | None = None,
) -> bool:
    """更新一個課程項目；保留既有第二階段專案進度格式相容性。"""
    if status not in ALLOWED_STATES:
        raise ValueError(f"不支援的課程狀態：{status}")
    if (
        template_status is not None
        and template_status not in ALLOWED_TEMPLATE_STATES
    ):
        raise ValueError(f"不支援的模板狀態：{template_status}")
    if phase is not None and phase not in PHASE_LABELS:
        raise ValueError("--phase 必須是 1 或 2")

    maximum = PHASE_ITEM_COUNTS.get(phase, 8)
    if lesson < 1 or lesson > maximum:
        raise ValueError(f"--lesson 必須介於 1 到 {maximum}")

    progress_path = resolve_progress_path(destination)
    if not progress_path.is_file():
        if phase is None:
            raise FileNotFoundError(
                "找不到 docs/course-progress.md，請先選擇第一或第二階段"
            )
        initialize_progress(destination)

    safe_local_version = (
        validate_safe_text("本機版本", local_version)
        if local_version is not None
        else None
    )
    safe_remote_evidence = (
        validate_safe_text("遠端證據", remote_evidence)
        if remote_evidence is not None
        else None
    )
    safe_next_checkpoint = (
        validate_safe_text("下一個檢查點", next_checkpoint)
        if next_checkpoint is not None
        else None
    )

    original = progress_path.read_text(encoding="utf-8")
    lines = original.splitlines()
    validate_phase_two_sequence(lines, lesson, status, phase)
    row_index, cells, field_indexes = find_progress_row(lines, lesson, phase)
    status_index, local_index, remote_index, template_index, next_index = (
        field_indexes
    )

    cells[status_index] = f"`{status}`"
    if safe_local_version is not None:
        cells[local_index] = safe_local_version
    if safe_remote_evidence is not None:
        cells[remote_index] = safe_remote_evidence
    if template_status is not None:
        cells[template_index] = f"`{template_status}`"
    if safe_next_checkpoint is not None:
        cells[next_index] = safe_next_checkpoint
    lines[row_index] = "| " + " | ".join(cells[1:-1]) + " |"

    update_checked_date(lines, validate_checked_date(checked_date))
    return write_if_changed(progress_path, original, lines)


def parse_args() -> argparse.Namespace:
    """解析 Agent 使用的統一課程進度參數。"""
    parser = argparse.ArgumentParser(
        description="建立或更新 Learn-GAS 的非私人課程進度。"
    )
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument(
        "--import-legacy-progress",
        action="append",
        type=Path,
        help="從舊版進度檔匯入明確完成的第一階段案例；可重複提供",
    )
    parser.add_argument("--select-phase", type=int, choices=sorted(PHASE_LABELS))
    parser.add_argument("--phase", type=int, choices=sorted(PHASE_LABELS))
    parser.add_argument("--lesson", type=int)
    parser.add_argument("--status", choices=sorted(ALLOWED_STATES))
    parser.add_argument("--local-version")
    parser.add_argument("--remote-evidence")
    parser.add_argument("--template-status", choices=sorted(ALLOWED_TEMPLATE_STATES))
    parser.add_argument("--next-checkpoint")
    parser.add_argument("--checked-date")
    return parser.parse_args()


def main() -> int:
    """建立、選擇階段或更新進度，且不輸出路徑與私人資料。"""
    args = parse_args()
    try:
        if args.import_legacy_progress:
            conflicting_options = (
                args.initialize
                or args.select_phase is not None
                or args.phase is not None
                or args.lesson is not None
                or args.status is not None
                or args.local_version is not None
                or args.remote_evidence is not None
                or args.template_status is not None
                or args.next_checkpoint is not None
            )
            if conflicting_options:
                raise ValueError(
                    "--import-legacy-progress 不得與初始化、選階段"
                    "或單課更新參數同時使用"
                )
            lessons, changed = import_legacy_phase_one_progress(
                args.destination,
                args.import_legacy_progress,
                args.checked_date,
            )
            action = "已匯入" if changed else "略過"
            lesson_text = ",".join(str(lesson) for lesson in lessons)
            print(
                f"[成功] 舊版第一階段進度{action}｜"
                f"完成案例={lesson_text}"
            )
            return 0

        if args.select_phase is not None:
            created, changed = select_phase(
                args.destination,
                args.select_phase,
                args.checked_date,
            )
            action = "已建立並選擇" if created else ("已切換" if changed else "略過")
            print(
                f"[成功] 課程進度{action}｜"
                f"目前階段={PHASE_LABELS[args.select_phase]}"
            )
            return 0

        if args.initialize:
            created = initialize_progress(args.destination)
            action = "已建立" if created else "已存在並保留"
            print(f"[成功] 課程進度{action}")
            return 0

        if args.lesson is None or args.status is None:
            raise ValueError("更新課程時必須同時提供 --lesson 與 --status")

        changed = update_progress(
            destination=args.destination,
            lesson=args.lesson,
            status=args.status,
            local_version=args.local_version,
            remote_evidence=args.remote_evidence,
            template_status=args.template_status,
            next_checkpoint=args.next_checkpoint,
            checked_date=args.checked_date,
            phase=args.phase,
        )
        action = "已更新" if changed else "略過"
        phase_text = (
            f"｜階段={PHASE_LABELS[args.phase]}" if args.phase is not None else ""
        )
        print(
            f"[成功] 課程進度{action}{phase_text}｜"
            f"課次={args.lesson}｜狀態={args.status}"
        )
        return 0
    except (FileNotFoundError, OSError, ValueError) as error:
        print(f"[失敗] 無法更新課程進度｜原因：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
