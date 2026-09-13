#!/usr/bin/env python3
"""驗證全課程進度的初始化、第二階段順序、更新與安全拒絕。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import update_course_progress


class UpdateCourseProgressTests(unittest.TestCase):
    """覆蓋初次選階段、第二階段鎖定與私人資料防護。"""

    def test_select_phase_one_creates_unified_progress(self) -> None:
        """第一次選第一階段時，自動建立含兩階段的統一進度。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            destination = Path(root) / "learn-gas-course"

            created, changed = update_course_progress.select_phase(
                destination,
                phase=1,
                checked_date="2026-07-30",
            )
            content = (destination / "docs/course-progress.md").read_text(
                encoding="utf-8"
            )

            self.assertTrue(created)
            self.assertTrue(changed)
            self.assertIn("- 目前選擇：`phase-1`（第一階段）", content)
            self.assertIn("| 第一階段 | 1. 家庭支出記錄表 |", content)
            self.assertIn("| 第二階段 | 1. Sheets 基礎讀寫 |", content)

    def test_select_phase_two_does_not_require_phase_one(self) -> None:
        """新人可直接選第二階段，第一階段保持未開始。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            destination = Path(root) / "learn-gas-course"

            update_course_progress.select_phase(
                destination,
                phase=2,
                checked_date="2026-07-30",
            )
            content = (destination / "docs/course-progress.md").read_text(
                encoding="utf-8"
            )

            self.assertIn("- 目前選擇：`phase-2`（第二階段）", content)
            self.assertIn(
                "| 第一階段 | 1. 家庭支出記錄表 | `not_started` |",
                content,
            )

    def test_phase_two_cannot_switch_before_lesson_eight_completed(self) -> None:
        """第二階段未完成第 8 課前不得切回第一階段。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            destination = Path(root) / "learn-gas-course"
            update_course_progress.select_phase(
                destination,
                phase=2,
                checked_date="2026-07-30",
            )
            update_course_progress.update_progress(
                destination=destination,
                phase=2,
                lesson=1,
                status="completed",
                local_version="本課提交",
                remote_evidence="使用者已驗收",
                template_status="validated",
                next_checkpoint="直接進入第 2 課",
                checked_date="2026-07-30",
            )

            with self.assertRaisesRegex(ValueError, "完成第 8 課前不能切換"):
                update_course_progress.select_phase(
                    destination,
                    phase=1,
                    checked_date="2026-07-30",
                )
            content = (destination / "docs/course-progress.md").read_text(
                encoding="utf-8"
            )

            self.assertIn("- 目前選擇：`phase-2`（第二階段）", content)
            self.assertIn(
                "| 第二階段 | 1. Sheets 基礎讀寫 | `completed` |",
                content,
            )

    def test_phase_two_can_switch_after_all_lessons_completed(self) -> None:
        """第二階段八課全部完成後，才可重新選擇第一階段。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            destination = Path(root) / "learn-gas-course"
            update_course_progress.select_phase(
                destination,
                phase=2,
                checked_date="2026-07-30",
            )

            for lesson in range(1, 9):
                update_course_progress.update_progress(
                    destination=destination,
                    phase=2,
                    lesson=lesson,
                    status="completed",
                    remote_evidence="使用者已驗收",
                    checked_date="2026-07-30",
                )

            update_course_progress.select_phase(
                destination,
                phase=1,
                checked_date="2026-07-30",
            )
            content = (destination / "docs/course-progress.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("- 目前選擇：`phase-1`（第一階段）", content)

    def test_phase_two_resume_preserves_completed_lessons(self) -> None:
        """第二階段中斷後重新選取同一階段，不清除既有完成紀錄。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            destination = Path(root) / "learn-gas-course"
            update_course_progress.select_phase(
                destination,
                phase=2,
                checked_date="2026-07-30",
            )
            update_course_progress.update_progress(
                destination=destination,
                phase=2,
                lesson=1,
                status="completed",
                checked_date="2026-07-30",
            )

            _created, changed = update_course_progress.select_phase(
                destination,
                phase=2,
                checked_date="2026-07-31",
            )
            content = (destination / "docs/course-progress.md").read_text(
                encoding="utf-8"
            )

            self.assertTrue(changed)
            self.assertIn("- 目前選擇：`phase-2`（第二階段）", content)
            self.assertIn(
                "| 第二階段 | 1. Sheets 基礎讀寫 | `completed` |",
                content,
            )
            self.assertIn(
                "| 第二階段 | 2. Script Properties | `not_started` |",
                content,
            )

    def test_phase_two_cannot_skip_incomplete_lesson(self) -> None:
        """第二階段不得跳過未完成的前一課。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            destination = Path(root) / "learn-gas-course"
            update_course_progress.select_phase(
                destination,
                phase=2,
                checked_date="2026-07-30",
            )

            with self.assertRaisesRegex(ValueError, "必須先完成第 1 課"):
                update_course_progress.update_progress(
                    destination=destination,
                    phase=2,
                    lesson=2,
                    status="local_ready",
                    checked_date="2026-07-30",
                )

            update_course_progress.update_progress(
                destination=destination,
                phase=2,
                lesson=1,
                status="completed",
                checked_date="2026-07-30",
            )
            changed = update_course_progress.update_progress(
                destination=destination,
                phase=2,
                lesson=2,
                status="local_ready",
                checked_date="2026-07-30",
            )
            self.assertTrue(changed)

    def test_initialize_and_repeat_preserve_existing_progress(self) -> None:
        """初始化重跑時不得以空白範本覆寫既有內容。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            destination = Path(root) / "learn-gas-course"
            self.assertTrue(update_course_progress.initialize_progress(destination))
            progress_path = destination / "docs/course-progress.md"
            customized = progress_path.read_text(encoding="utf-8").replace(
                "`not_started`",
                "`completed`",
                1,
            )
            progress_path.write_text(customized, encoding="utf-8")

            self.assertFalse(update_course_progress.initialize_progress(destination))
            self.assertEqual(
                progress_path.read_text(encoding="utf-8"),
                customized,
            )

    def test_progress_update_and_repeat_are_stable_for_both_phases(self) -> None:
        """兩階段項目都能更新，相同內容重跑時安全略過。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            destination = Path(root) / "learn-gas-course"
            update_course_progress.select_phase(
                destination,
                phase=1,
                checked_date="2026-07-30",
            )

            first_changed = update_course_progress.update_progress(
                destination=destination,
                phase=1,
                lesson=1,
                status="local_ready",
                local_version="本課提交",
                remote_evidence="尚未推送",
                template_status="validated",
                next_checkpoint="等待推送確認",
                checked_date="2026-07-30",
            )
            repeat_changed = update_course_progress.update_progress(
                destination=destination,
                phase=1,
                lesson=1,
                status="local_ready",
                local_version="本課提交",
                remote_evidence="尚未推送",
                template_status="validated",
                next_checkpoint="等待推送確認",
                checked_date="2026-07-30",
            )

            self.assertTrue(first_changed)
            self.assertFalse(repeat_changed)

    def test_phase_one_allows_independent_case_selection(self) -> None:
        """第一階段案例彼此獨立，可先開始任一案例。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            destination = Path(root) / "learn-gas-course"
            update_course_progress.select_phase(
                destination,
                phase=1,
                checked_date="2026-07-30",
            )

            changed = update_course_progress.update_progress(
                destination=destination,
                phase=1,
                lesson=5,
                status="local_ready",
                local_version="本課提交",
                remote_evidence="尚未推送",
                template_status="validated",
                next_checkpoint="等待推送確認",
                checked_date="2026-07-30",
            )
            content = (destination / "docs/course-progress.md").read_text(
                encoding="utf-8"
            )

            self.assertTrue(changed)
            self.assertIn(
                "| 第一階段 | 1. 家庭支出記錄表 | `not_started` |",
                content,
            )
            self.assertIn(
                "| 第一階段 | 5. 個人化批次郵件寄送器 | `local_ready` |",
                content,
            )

    def test_existing_phase_two_project_progress_stays_compatible(self) -> None:
        """既有第二階段專案進度仍可不帶 phase 參數更新。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            destination = Path(root) / "activity-registration"
            progress_path = destination / "docs/course-progress.md"
            progress_path.parent.mkdir(parents=True)
            progress_path.write_text(
                "# 舊格式\n\n"
                "- 最近檢查日期：2026-07-29\n\n"
                "| 課次 | 狀態 | 本機版本 | 遠端證據 | 技能模板 | 下一個檢查點 |\n"
                "|---|---|---|---|---|---|\n"
                "| 1. Sheets 基礎讀寫 | `completed` | — | — | `validated` | 進入第 2 課 |\n"
                "| 2. Script Properties | `not_started` | — | — | `pending` | 驗證設定缺漏 |\n",
                encoding="utf-8",
            )

            changed = update_course_progress.update_progress(
                destination=destination,
                lesson=2,
                status="local_ready",
                local_version="本課提交",
                remote_evidence="尚未推送",
                template_status="pending",
                next_checkpoint="等待推送確認",
                checked_date="2026-07-30",
            )

            self.assertTrue(changed)
            self.assertIn(
                "| 2. Script Properties | `local_ready` |",
                progress_path.read_text(encoding="utf-8"),
            )

    def test_legacy_phase_one_summary_imports_all_cases_and_repeats_safely(
        self,
    ) -> None:
        """舊檔明確記載五案例完成時，可一次匯入且重跑安全略過。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            root_path = Path(root)
            destination = root_path / "learn-gas-course"
            legacy_progress = root_path / "legacy-course-progress.md"
            legacy_progress.write_text(
                "# 私人課程進度\n\n"
                "## 第一階段完成\n\n"
                "五個生活應用入門案例均已完成。\n",
                encoding="utf-8",
            )
            update_course_progress.select_phase(
                destination,
                phase=2,
                checked_date="2026-07-31",
            )

            lessons, changed = (
                update_course_progress.import_legacy_phase_one_progress(
                    destination,
                    [legacy_progress],
                    checked_date="2026-07-31",
                )
            )
            repeat_lessons, repeat_changed = (
                update_course_progress.import_legacy_phase_one_progress(
                    destination,
                    [legacy_progress],
                    checked_date="2026-07-31",
                )
            )
            content = (destination / "docs/course-progress.md").read_text(
                encoding="utf-8"
            )

            self.assertEqual(lessons, [1, 2, 3, 4, 5])
            self.assertTrue(changed)
            self.assertEqual(repeat_lessons, lessons)
            self.assertFalse(repeat_changed)
            self.assertIn("- 目前選擇：`phase-2`（第二階段）", content)
            for lesson, lesson_name in (
                update_course_progress.PHASE_ONE_LESSON_NAMES.items()
            ):
                self.assertIn(
                    f"| 第一階段 | {lesson}. {lesson_name} | `completed` |",
                    content,
                )
            self.assertNotIn(str(legacy_progress), content)

    def test_legacy_phase_one_import_can_combine_explicit_case_sections(
        self,
    ) -> None:
        """多份舊檔可合併匯入各自明確標為完成的獨立案例。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            root_path = Path(root)
            destination = root_path / "learn-gas-course"
            case_two = root_path / "legacy-case-two.md"
            case_five = root_path / "legacy-case-five.md"
            case_two.write_text(
                "# 舊課程\n\n"
                "## 案例二：批次信封版面產生器\n\n"
                "狀態：`completed`\n",
                encoding="utf-8",
            )
            case_five.write_text(
                "# 舊課程\n\n"
                "## 第一階段案例五：個人化批次郵件寄送器\n\n"
                "課程狀態：completed\n",
                encoding="utf-8",
            )

            lessons, changed = (
                update_course_progress.import_legacy_phase_one_progress(
                    destination,
                    [case_two, case_five],
                    checked_date="2026-07-31",
                )
            )
            content = (destination / "docs/course-progress.md").read_text(
                encoding="utf-8"
            )

            self.assertEqual(lessons, [2, 5])
            self.assertTrue(changed)
            self.assertIn(
                "| 第一階段 | 1. 家庭支出記錄表 | `not_started` |",
                content,
            )
            self.assertIn(
                "| 第一階段 | 2. 批次信封版面產生器 | `completed` |",
                content,
            )
            self.assertIn(
                "| 第一階段 | 5. 個人化批次郵件寄送器 | `completed` |",
                content,
            )

    def test_legacy_import_without_explicit_completion_is_refused(self) -> None:
        """只有課名、沒有完成狀態的舊檔不得被猜成已完成。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            root_path = Path(root)
            destination = root_path / "learn-gas-course"
            legacy_progress = root_path / "legacy-course-progress.md"
            legacy_progress.write_text(
                "# 舊課程\n\n"
                "## 案例三：教師隨機測驗與成績報表\n\n"
                "準備開始驗收。\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "沒有可辨識"):
                update_course_progress.import_legacy_phase_one_progress(
                    destination,
                    [legacy_progress],
                    checked_date="2026-07-31",
                )
            self.assertFalse((destination / "docs/course-progress.md").exists())

    def test_legacy_import_refuses_active_unified_case_before_writing(
        self,
    ) -> None:
        """統一進度已有進行中案例時，不得以舊版完成摘要覆寫。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            root_path = Path(root)
            destination = root_path / "learn-gas-course"
            legacy_progress = root_path / "legacy-course-progress.md"
            legacy_progress.write_text(
                "# 舊課程\n\n第一階段五個案例均已完成。\n",
                encoding="utf-8",
            )
            update_course_progress.select_phase(
                destination,
                phase=1,
                checked_date="2026-07-31",
            )
            update_course_progress.update_progress(
                destination=destination,
                phase=1,
                lesson=3,
                status="ui_validation",
                checked_date="2026-07-31",
            )
            progress_path = destination / "docs/course-progress.md"
            original = progress_path.read_text(encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "已有進行中的統一進度"):
                update_course_progress.import_legacy_phase_one_progress(
                    destination,
                    [legacy_progress],
                    checked_date="2026-07-31",
                )
            self.assertEqual(
                progress_path.read_text(encoding="utf-8"),
                original,
            )

    def test_legacy_import_requires_absolute_source_path(self) -> None:
        """舊進度來源必須明確使用絕對路徑。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            destination = Path(root) / "learn-gas-course"
            with self.assertRaisesRegex(ValueError, "必須使用絕對路徑"):
                update_course_progress.import_legacy_phase_one_progress(
                    destination,
                    [Path("legacy-course-progress.md")],
                    checked_date="2026-07-31",
                )

    def test_private_values_and_invalid_states_are_refused(self) -> None:
        """網址、Email、長 ID 與未知狀態都不能寫入進度。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            destination = Path(root) / "learn-gas-course"
            update_course_progress.select_phase(
                destination,
                phase=1,
                checked_date="2026-07-30",
            )

            unsafe_values = [
                "https://docs.google.com/spreadsheets/d/example/edit",
                "student@example.com",
                "abcdefghijklmnopqrstuvwxyz123456",
            ]
            for unsafe_value in unsafe_values:
                with self.subTest(unsafe_value=unsafe_value):
                    with self.assertRaisesRegex(ValueError, "私人資料或秘密"):
                        update_course_progress.update_progress(
                            destination=destination,
                            phase=1,
                            lesson=1,
                            status="local_ready",
                            remote_evidence=unsafe_value,
                            checked_date="2026-07-30",
                        )

            with self.assertRaisesRegex(ValueError, "不支援的課程狀態"):
                update_course_progress.update_progress(
                    destination=destination,
                    phase=1,
                    lesson=1,
                    status="almost_done",
                    checked_date="2026-07-30",
                )

    def test_repository_destination_is_refused(self) -> None:
        """進度工具不得把技能儲存庫本身誤當成課程工作區。"""
        with self.assertRaisesRegex(ValueError, "不得位於 Learn-GAS"):
            update_course_progress.initialize_progress(
                update_course_progress.REPOSITORY_ROOT
            )

    def test_progress_symlink_outside_workspace_is_refused(self) -> None:
        """課程進度捷徑指向工作區外時不得跟隨寫入。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-progress-test-") as root:
            root_path = Path(root)
            destination = root_path / "learn-gas-course"
            docs_path = destination / "docs"
            docs_path.mkdir(parents=True)
            outside = root_path / "outside-progress.md"
            outside.write_text("不可修改\n", encoding="utf-8")
            (docs_path / "course-progress.md").symlink_to(outside)

            with self.assertRaisesRegex(ValueError, "超出課程工作區"):
                update_course_progress.initialize_progress(destination)
            self.assertEqual(outside.read_text(encoding="utf-8"), "不可修改\n")


if __name__ == "__main__":
    unittest.main()
