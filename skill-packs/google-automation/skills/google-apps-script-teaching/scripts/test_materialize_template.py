#!/usr/bin/env python3
"""驗證教學模板複製工具的安全行為。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import materialize_template


class MaterializeTemplateTests(unittest.TestCase):
    """覆蓋正常複製、重跑與安全拒絕。"""

    def assert_destination_matches_template(
        self,
        destination: Path,
        template_id: str,
    ) -> None:
        """確認學生專案的受控檔案完整等於指定模板快照。"""
        catalog = materialize_template.load_catalog()
        template = materialize_template.find_template(catalog, template_id)
        _, source_files = materialize_template.validate_template(template)
        actual_files = materialize_template.controlled_destination_files(
            destination.resolve()
        )

        self.assertEqual(set(actual_files), set(source_files))
        for relative, source in source_files.items():
            self.assertEqual(
                actual_files[relative].read_bytes(),
                source.read_bytes(),
                relative.as_posix(),
            )

    def materialize_activity_lesson(
        self,
        destination: Path,
        lesson_number: int,
    ) -> list[tuple[Path | None, Path, str]]:
        """依正式順序把第二階段專案準備到指定課次。"""
        plan = materialize_template.materialize(
            "activity-registration/lesson-01",
            destination,
            dry_run=False,
            replace_clasp_bootstrap=False,
        )
        for current_lesson in range(2, lesson_number + 1):
            plan = materialize_template.upgrade_materialized_template(
                f"activity-registration/lesson-{current_lesson - 1:02d}",
                f"activity-registration/lesson-{current_lesson:02d}",
                destination,
                dry_run=False,
            )
        return plan

    def test_validated_template_can_copy_and_repeat(self) -> None:
        """已驗收模板可以複製，重跑時只略過相同內容。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-template-test-") as root:
            destination = Path(root) / "project"
            first_plan = materialize_template.materialize(
                "beginner/expense-tracker",
                destination,
                dry_run=False,
                replace_clasp_bootstrap=False,
            )
            repeat_plan = materialize_template.materialize(
                "beginner/expense-tracker",
                destination,
                dry_run=False,
                replace_clasp_bootstrap=False,
            )

            self.assertTrue(first_plan)
            self.assertTrue((destination / "src/01_ExpenseTracker.gs").is_file())
            self.assertTrue(all(action == "略過" for _, _, action in repeat_plan))

    def test_activity_registration_lesson01_can_copy_and_repeat(self) -> None:
        """第 1 課累積模板可完整複製，重跑時不覆寫相同內容。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-template-test-") as root:
            destination = Path(root) / "project"
            first_plan = materialize_template.materialize(
                "activity-registration/lesson-01",
                destination,
                dry_run=False,
                replace_clasp_bootstrap=False,
            )
            repeat_plan = materialize_template.materialize(
                "activity-registration/lesson-01",
                destination,
                dry_run=False,
                replace_clasp_bootstrap=False,
            )

            expected_files = {
                ".claspignore",
                "src/00_Log.gs",
                "src/00_Menu.gs",
                "src/01_Sheets.gs",
                "src/appsscript.json",
            }
            actual_files = {
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file()
            }
            sheets_source = (destination / "src/01_Sheets.gs").read_text(
                encoding="utf-8"
            )
            menu_source = (destination / "src/00_Menu.gs").read_text(
                encoding="utf-8"
            )

            self.assertTrue(first_plan)
            self.assertEqual(actual_files, expected_files)
            self.assertIn("function setupLessonSheet()", sheets_source)
            self.assertIn("function onOpen(e)", menu_source)
            self.assertIn("初始化活動報名資料", menu_source)
            self.assertTrue(all(action == "略過" for _, _, action in repeat_plan))

    def test_activity_registration_lesson02_can_copy_and_repeat(self) -> None:
        """第 2 課累積模板包含設定檢查，重跑時不覆寫相同內容。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-template-test-") as root:
            destination = Path(root) / "project"
            first_plan = self.materialize_activity_lesson(destination, 2)
            repeat_plan = materialize_template.upgrade_materialized_template(
                "activity-registration/lesson-01",
                "activity-registration/lesson-02",
                destination,
                dry_run=False,
            )

            expected_files = {
                ".claspignore",
                "src/00_Log.gs",
                "src/00_Menu.gs",
                "src/01_Sheets.gs",
                "src/02_Config.gs",
                "src/appsscript.json",
            }
            actual_files = {
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file()
            }
            config_source = (destination / "src/02_Config.gs").read_text(
                encoding="utf-8"
            )
            menu_source = (destination / "src/00_Menu.gs").read_text(
                encoding="utf-8"
            )

            self.assertTrue(first_plan)
            self.assertEqual(actual_files, expected_files)
            self.assertIn("function checkLesson02Settings()", config_source)
            self.assertIn("SPREADSHEET_ID", config_source)
            self.assertIn("檢查系統設定", menu_source)
            self.assertTrue(all(action == "略過" for _, _, action in repeat_plan))

    def test_activity_registration_lesson03_can_copy_and_repeat(self) -> None:
        """第 3 課累積模板包含 Forms 程式，重跑時不覆寫相同內容。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-template-test-") as root:
            destination = Path(root) / "project"
            first_plan = self.materialize_activity_lesson(destination, 3)
            repeat_plan = materialize_template.upgrade_materialized_template(
                "activity-registration/lesson-02",
                "activity-registration/lesson-03",
                destination,
                dry_run=False,
            )

            expected_files = {
                ".claspignore",
                "src/00_Log.gs",
                "src/00_Menu.gs",
                "src/01_Sheets.gs",
                "src/02_Config.gs",
                "src/03_Forms.gs",
                "src/appsscript.json",
            }
            actual_files = {
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file()
            }
            forms_source = (destination / "src/03_Forms.gs").read_text(
                encoding="utf-8"
            )
            menu_source = (destination / "src/00_Menu.gs").read_text(
                encoding="utf-8"
            )

            self.assertTrue(first_plan)
            self.assertEqual(actual_files, expected_files)
            self.assertIn("function setupLesson03Form()", forms_source)
            self.assertIn("FORM_ID", forms_source)
            self.assertIn("設定活動報名表單", menu_source)
            self.assertTrue(all(action == "略過" for _, _, action in repeat_plan))

    def test_activity_registration_lesson04_can_copy_and_repeat(self) -> None:
        """第 4 課累積模板包含批次與選單，重跑時不覆寫相同內容。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-template-test-") as root:
            destination = Path(root) / "project"
            first_plan = self.materialize_activity_lesson(destination, 4)
            repeat_plan = materialize_template.upgrade_materialized_template(
                "activity-registration/lesson-03",
                "activity-registration/lesson-04",
                destination,
                dry_run=False,
            )

            expected_files = {
                ".claspignore",
                "src/00_Log.gs",
                "src/00_Menu.gs",
                "src/01_Sheets.gs",
                "src/02_Config.gs",
                "src/03_Forms.gs",
                "src/04_Batch.gs",
                "src/appsscript.json",
            }
            actual_files = {
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file()
            }
            batch_source = (destination / "src/04_Batch.gs").read_text(
                encoding="utf-8"
            )
            menu_source = (destination / "src/00_Menu.gs").read_text(
                encoding="utf-8"
            )

            self.assertTrue(first_plan)
            self.assertEqual(actual_files, expected_files)
            self.assertIn("function processPendingRegistrations()", batch_source)
            self.assertIn("function runLesson04Tests()", batch_source)
            self.assertIn("批次處理待處理報名", menu_source)
            self.assertTrue(all(action == "略過" for _, _, action in repeat_plan))

    def test_activity_registration_lesson05_can_copy_and_repeat(self) -> None:
        """第 5 課累積模板包含文件功能，重跑時不覆寫相同內容。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-template-test-") as root:
            destination = Path(root) / "project"
            first_plan = self.materialize_activity_lesson(destination, 5)
            repeat_plan = materialize_template.upgrade_materialized_template(
                "activity-registration/lesson-04",
                "activity-registration/lesson-05",
                destination,
                dry_run=False,
            )

            expected_files = {
                ".claspignore",
                "src/00_Log.gs",
                "src/00_Menu.gs",
                "src/01_Sheets.gs",
                "src/02_Config.gs",
                "src/03_Forms.gs",
                "src/04_Batch.gs",
                "src/05_Documents.gs",
                "src/appsscript.json",
            }
            actual_files = {
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file()
            }
            documents_source = (destination / "src/05_Documents.gs").read_text(
                encoding="utf-8"
            )
            menu_source = (destination / "src/00_Menu.gs").read_text(
                encoding="utf-8"
            )

            self.assertTrue(first_plan)
            self.assertEqual(actual_files, expected_files)
            self.assertIn(
                "function createPendingRegistrationDocuments()",
                documents_source,
            )
            self.assertIn("DOC_TEMPLATE_ID", documents_source)
            self.assertIn("OUTPUT_FOLDER_ID", documents_source)
            self.assertIn("建立報名確認文件", menu_source)
            self.assertTrue(all(action == "略過" for _, _, action in repeat_plan))

    def test_activity_registration_lesson06_can_copy_and_repeat(self) -> None:
        """第 6 課累積模板包含安全寄信與重設入口。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-template-test-") as root:
            destination = Path(root) / "project"
            first_plan = self.materialize_activity_lesson(destination, 6)
            repeat_plan = materialize_template.upgrade_materialized_template(
                "activity-registration/lesson-05",
                "activity-registration/lesson-06",
                destination,
                dry_run=False,
            )

            expected_files = {
                ".claspignore",
                "src/00_Log.gs",
                "src/00_Menu.gs",
                "src/01_Sheets.gs",
                "src/02_Config.gs",
                "src/03_Forms.gs",
                "src/04_Batch.gs",
                "src/05_Documents.gs",
                "src/06_Gmail.gs",
                "src/appsscript.json",
            }
            actual_files = {
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file()
            }
            gmail_source = (destination / "src/06_Gmail.gs").read_text(
                encoding="utf-8"
            )
            menu_source = (destination / "src/00_Menu.gs").read_text(
                encoding="utf-8"
            )
            manifest = json.loads(
                (destination / "src/appsscript.json").read_text(
                    encoding="utf-8"
                )
            )

            self.assertTrue(first_plan)
            self.assertEqual(actual_files, expected_files)
            self.assertIn("MailApp.sendEmail", gmail_source)
            self.assertNotIn("TEST_EMAIL", gmail_source)
            self.assertIn("寄送報名確認郵件", menu_source)
            self.assertIn("確認未寄出並重設", menu_source)
            self.assertIn(
                "https://www.googleapis.com/auth/script.send_mail",
                manifest["oauthScopes"],
            )
            self.assertNotIn(
                "https://www.googleapis.com/auth/gmail.send",
                manifest["oauthScopes"],
            )
            self.assertTrue(all(action == "略過" for _, _, action in repeat_plan))

    def test_activity_registration_lesson07_can_copy_and_repeat(self) -> None:
        """第 7 課累積模板包含可控觸發器與單次處理保護。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-template-test-") as root:
            destination = Path(root) / "project"
            first_plan = self.materialize_activity_lesson(destination, 7)
            repeat_plan = materialize_template.upgrade_materialized_template(
                "activity-registration/lesson-06",
                "activity-registration/lesson-07",
                destination,
                dry_run=False,
            )

            expected_files = {
                ".claspignore",
                "src/00_Log.gs",
                "src/00_Menu.gs",
                "src/01_Sheets.gs",
                "src/02_Config.gs",
                "src/03_Forms.gs",
                "src/04_Batch.gs",
                "src/05_Documents.gs",
                "src/06_Gmail.gs",
                "src/07_Triggers.gs",
                "src/appsscript.json",
            }
            actual_files = {
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file()
            }
            trigger_source = (destination / "src/07_Triggers.gs").read_text(
                encoding="utf-8"
            )
            menu_source = (destination / "src/00_Menu.gs").read_text(
                encoding="utf-8"
            )

            self.assertTrue(first_plan)
            self.assertEqual(actual_files, expected_files)
            self.assertIn("batchSize: 1", trigger_source)
            self.assertIn("LESSON07_TIMER_ATTEMPTED_AT", trigger_source)
            self.assertNotIn("PROCESSING_BATCH_SIZE", trigger_source)
            self.assertIn("啟用表單提交自動處理", menu_source)
            self.assertIn("停止第 7 課自動化", menu_source)
            self.assertTrue(all(action == "略過" for _, _, action in repeat_plan))

    def test_activity_registration_lesson08_can_copy_and_repeat(self) -> None:
        """第 8 課累積模板包含安全 Web App 與 Webhook 去重。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-template-test-") as root:
            destination = Path(root) / "project"
            first_plan = self.materialize_activity_lesson(destination, 8)
            repeat_plan = materialize_template.upgrade_materialized_template(
                "activity-registration/lesson-07",
                "activity-registration/lesson-08",
                destination,
                dry_run=False,
            )

            expected_files = {
                ".claspignore",
                "src/00_Log.gs",
                "src/00_Menu.gs",
                "src/01_Sheets.gs",
                "src/02_Config.gs",
                "src/03_Forms.gs",
                "src/04_Batch.gs",
                "src/05_Documents.gs",
                "src/06_Gmail.gs",
                "src/07_Triggers.gs",
                "src/08_WebApp.gs",
                "src/appsscript.json",
            }
            actual_files = {
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file()
            }
            web_app_source = (destination / "src/08_WebApp.gs").read_text(
                encoding="utf-8"
            )
            menu_source = (destination / "src/00_Menu.gs").read_text(
                encoding="utf-8"
            )
            manifest = json.loads(
                (destination / "src/appsscript.json").read_text(
                    encoding="utf-8"
                )
            )

            self.assertTrue(first_plan)
            self.assertEqual(actual_files, expected_files)
            self.assertIn("function doGet(e)", web_app_source)
            self.assertIn("function doPost(e)", web_app_source)
            self.assertIn("SpreadsheetApp.openById", web_app_source)
            self.assertIn("DUPLICATE", web_app_source)
            self.assertNotIn("runLesson08RemoteTests", menu_source)
            self.assertIn(
                "https://www.googleapis.com/auth/script.external_request",
                manifest["oauthScopes"],
            )
            self.assertTrue(all(action == "略過" for _, _, action in repeat_plan))

    def test_activity_registration_can_upgrade_lesson01_through_lesson08(
        self,
    ) -> None:
        """第二階段能從第 1 課逐課受控升級到第 8 課並安全重跑。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-upgrade-test-") as root:
            destination = Path(root) / "project"
            materialize_template.materialize(
                "activity-registration/lesson-01",
                destination,
                dry_run=False,
                replace_clasp_bootstrap=False,
            )
            self.assert_destination_matches_template(
                destination,
                "activity-registration/lesson-01",
            )

            for lesson_number in range(2, 9):
                previous_id = (
                    f"activity-registration/lesson-{lesson_number - 1:02d}"
                )
                target_id = f"activity-registration/lesson-{lesson_number:02d}"
                plan = materialize_template.upgrade_materialized_template(
                    previous_id,
                    target_id,
                    destination,
                    dry_run=False,
                )
                repeat_plan = materialize_template.upgrade_materialized_template(
                    previous_id,
                    target_id,
                    destination,
                    dry_run=False,
                )

                self.assertTrue(
                    any(action in {"新增", "升級"} for _, _, action in plan)
                )
                self.assertTrue(
                    all(action == "略過" for _, _, action in repeat_plan)
                )
                self.assert_destination_matches_template(destination, target_id)

    def test_activity_later_lesson_cannot_be_copied_directly(self) -> None:
        """第 2 至第 8 課必須沿相鄰快照升級，不得直接具現化。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-upgrade-test-") as root:
            destination = Path(root) / "project"
            with self.assertRaisesRegex(ValueError, "不得直接複製"):
                materialize_template.materialize(
                    "activity-registration/lesson-02",
                    destination,
                    dry_run=False,
                    replace_clasp_bootstrap=False,
                )
            self.assertFalse(destination.exists())

    def test_activity_upgrade_refuses_modified_previous_file_before_writing(
        self,
    ) -> None:
        """前課受控檔案遭修改時，整次升級在新增檔案前停止。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-upgrade-test-") as root:
            destination = Path(root) / "project"
            materialize_template.materialize(
                "activity-registration/lesson-01",
                destination,
                dry_run=False,
                replace_clasp_bootstrap=False,
            )
            modified = destination / "src/00_Menu.gs"
            modified.write_text("// 學員自行修改\n", encoding="utf-8")

            with self.assertRaisesRegex(FileExistsError, "已有不同內容"):
                materialize_template.upgrade_materialized_template(
                    "activity-registration/lesson-01",
                    "activity-registration/lesson-02",
                    destination,
                    dry_run=False,
                )

            self.assertEqual(
                modified.read_text(encoding="utf-8"),
                "// 學員自行修改\n",
            )
            self.assertFalse((destination / "src/02_Config.gs").exists())

    def test_activity_upgrade_refuses_extra_source_file_before_writing(
        self,
    ) -> None:
        """src 出現前課快照以外的檔案時不得猜測合併。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-upgrade-test-") as root:
            destination = Path(root) / "project"
            materialize_template.materialize(
                "activity-registration/lesson-01",
                destination,
                dry_run=False,
                replace_clasp_bootstrap=False,
            )
            custom_file = destination / "src/UserCustom.gs"
            custom_file.write_text("// 學員自訂功能\n", encoding="utf-8")

            with self.assertRaisesRegex(FileExistsError, "快照以外"):
                materialize_template.upgrade_materialized_template(
                    "activity-registration/lesson-01",
                    "activity-registration/lesson-02",
                    destination,
                    dry_run=False,
                )

            self.assertTrue(custom_file.is_file())
            self.assertFalse((destination / "src/02_Config.gs").exists())

    def test_activity_upgrade_refuses_missing_previous_file_before_writing(
        self,
    ) -> None:
        """前課受控檔案缺少時不得升級或補猜內容。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-upgrade-test-") as root:
            destination = Path(root) / "project"
            materialize_template.materialize(
                "activity-registration/lesson-01",
                destination,
                dry_run=False,
                replace_clasp_bootstrap=False,
            )
            missing_file = destination / "src/01_Sheets.gs"
            missing_file.unlink()

            with self.assertRaisesRegex(FileExistsError, "缺少前課受控檔案"):
                materialize_template.upgrade_materialized_template(
                    "activity-registration/lesson-01",
                    "activity-registration/lesson-02",
                    destination,
                    dry_run=False,
                )

            self.assertFalse(missing_file.exists())
            self.assertFalse((destination / "src/02_Config.gs").exists())

    def test_activity_upgrade_dry_run_does_not_write(self) -> None:
        """受控升級預覽只回報計畫，不變更前課專案。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-upgrade-test-") as root:
            destination = Path(root) / "project"
            materialize_template.materialize(
                "activity-registration/lesson-01",
                destination,
                dry_run=False,
                replace_clasp_bootstrap=False,
            )
            plan = materialize_template.upgrade_materialized_template(
                "activity-registration/lesson-01",
                "activity-registration/lesson-02",
                destination,
                dry_run=True,
            )

            self.assertTrue(
                any(action in {"新增", "升級"} for _, _, action in plan)
            )
            self.assert_destination_matches_template(
                destination,
                "activity-registration/lesson-01",
            )

    def test_activity_upgrade_refuses_skipped_or_backward_lesson(self) -> None:
        """第二階段不得跳課或倒退套用快照。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-upgrade-test-") as root:
            destination = Path(root) / "project"
            materialize_template.materialize(
                "activity-registration/lesson-01",
                destination,
                dry_run=False,
                replace_clasp_bootstrap=False,
            )

            with self.assertRaisesRegex(ValueError, "只能依序升級相鄰課次"):
                materialize_template.upgrade_materialized_template(
                    "activity-registration/lesson-01",
                    "activity-registration/lesson-03",
                    destination,
                    dry_run=False,
                )
            with self.assertRaisesRegex(ValueError, "只能依序升級相鄰課次"):
                materialize_template.upgrade_materialized_template(
                    "activity-registration/lesson-02",
                    "activity-registration/lesson-01",
                    destination,
                    dry_run=False,
                )
            self.assertFalse((destination / "src/02_Config.gs").exists())
            self.assertFalse((destination / "src/03_Forms.gs").exists())

    def test_activity_upgrade_refuses_pending_snapshot(self) -> None:
        """前課或目標課尚未驗收時均不得進入升級。"""
        catalog = materialize_template.load_catalog()
        previous = dict(
            materialize_template.find_template(
                catalog,
                "activity-registration/lesson-01",
            )
        )
        target = dict(
            materialize_template.find_template(
                catalog,
                "activity-registration/lesson-02",
            )
        )

        with tempfile.TemporaryDirectory(prefix="learn-gas-upgrade-test-") as root:
            destination = Path(root) / "project"
            target["status"] = "pending"
            with self.assertRaisesRegex(ValueError, "尚未完成驗收"):
                materialize_template.build_upgrade_plan(
                    previous,
                    target,
                    destination,
                )

            target["status"] = "validated"
            previous["status"] = "pending"
            with self.assertRaisesRegex(ValueError, "尚未完成驗收"):
                materialize_template.build_upgrade_plan(
                    previous,
                    target,
                    destination,
                )

    def test_different_existing_file_is_refused(self) -> None:
        """目的檔案內容不同時不得覆寫。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-template-test-") as root:
            destination = Path(root) / "project"
            target = destination / "src/00_Log.gs"
            target.parent.mkdir(parents=True)
            target.write_text("// 使用者既有內容\n", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                materialize_template.materialize(
                    "beginner/expense-tracker",
                    destination,
                    dry_run=False,
                    replace_clasp_bootstrap=False,
                )
            self.assertEqual(target.read_text(encoding="utf-8"), "// 使用者既有內容\n")

    def test_pending_template_is_refused(self) -> None:
        """尚未完成驗收的第二階段模板不得發放。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-template-test-") as root:
            with self.assertRaisesRegex(ValueError, "尚未完成驗收"):
                materialize_template.build_copy_plan(
                    {
                        "id": "activity-registration/test-pending",
                        "status": "pending",
                        "sourceRoot": "activity-registration/lesson-08",
                        "files": [],
                    },
                    Path(root) / "project",
                    replace_clasp_bootstrap=False,
                )

    def test_pristine_clasp_bootstrap_can_be_replaced(self) -> None:
        """只有可辨識的 clasp 空白初始檔可以被模板取代。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-template-test-") as root:
            destination = Path(root) / "project"
            source_directory = destination / "src"
            source_directory.mkdir(parents=True)
            (source_directory / "Code.gs").write_text(
                "function myFunction() {\n}\n",
                encoding="utf-8",
            )
            (source_directory / "appsscript.json").write_text(
                json.dumps(
                    {
                        "timeZone": "Asia/Taipei",
                        "dependencies": {},
                        "exceptionLogging": "STACKDRIVER",
                        "runtimeVersion": "V8",
                    }
                ),
                encoding="utf-8",
            )

            materialize_template.materialize(
                "beginner/expense-tracker",
                destination,
                dry_run=False,
                replace_clasp_bootstrap=True,
            )

            self.assertFalse((source_directory / "Code.gs").exists())
            self.assertTrue((source_directory / "01_ExpenseTracker.gs").is_file())

    def test_nonempty_clasp_bootstrap_is_refused(self) -> None:
        """已有業務程式時，不得使用初始檔取代模式。"""
        with tempfile.TemporaryDirectory(prefix="learn-gas-template-test-") as root:
            destination = Path(root) / "project"
            source_directory = destination / "src"
            source_directory.mkdir(parents=True)
            existing = source_directory / "Existing.gs"
            existing.write_text("function existing() {}\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "非 clasp 初始檔案"):
                materialize_template.materialize(
                    "beginner/expense-tracker",
                    destination,
                    dry_run=False,
                    replace_clasp_bootstrap=True,
                )
            self.assertTrue(existing.is_file())

    def test_repository_destination_is_refused(self) -> None:
        """學生專案不得被具現化在 Learn-GAS 儲存庫內。"""
        destination = materialize_template.REPOSITORY_ROOT / "unsafe-test-target"
        with self.assertRaisesRegex(ValueError, "不得建立在 Learn-GAS"):
            materialize_template.materialize(
                "beginner/expense-tracker",
                destination,
                dry_run=True,
                replace_clasp_bootstrap=False,
            )
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
