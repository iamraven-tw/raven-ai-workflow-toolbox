#!/usr/bin/env python3
"""驗證四個 Google Apps Script 技能的結構、契約與安全基線。"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPOSITORY_ROOT / "skills"
TEACHING_ROOT = SKILLS_ROOT / "google-apps-script-teaching"
PROJECT_ROOT = SKILLS_ROOT / "google-apps-script-project-development"
DEBUGGING_ROOT = SKILLS_ROOT / "google-apps-script-debugging"
DOCS_LAYOUT_ROOT = SKILLS_ROOT / "google-docs-layout"
TEACHING_TEMPLATES_ROOT = TEACHING_ROOT / "templates"
LEARNER_TERMINOLOGY_PATH = SKILLS_ROOT / "learner-facing-terminology.md"

EXPECTED_SKILLS = {
    TEACHING_ROOT: "google-apps-script-teaching",
    PROJECT_ROOT: "google-apps-script-project-development",
    DEBUGGING_ROOT: "google-apps-script-debugging",
    DOCS_LAYOUT_ROOT: "google-docs-layout",
}


def validate_required_files() -> list[str]:
    """確認四個技能與主要教材都存在。"""
    required_files = [
        REPOSITORY_ROOT / "docs" / "apps-script-guide.md",
        REPOSITORY_ROOT / "INSTALL.md",
        REPOSITORY_ROOT / "AGENTS.md",
        REPOSITORY_ROOT / "CLAUDE.md",
        REPOSITORY_ROOT / "LICENSE.learn-gas",
        REPOSITORY_ROOT / ".gitignore",
        LEARNER_TERMINOLOGY_PATH,
        TEACHING_ROOT / "SKILL.md",
        TEACHING_ROOT / "agents" / "openai.yaml",
        TEACHING_ROOT / "references" / "teaching-workflow.md",
        TEACHING_ROOT / "references" / "teaching-examples.md",
        TEACHING_ROOT / "references" / "learning-path.md",
        TEACHING_ROOT / "references" / "beginner-application-path.md",
        TEACHING_ROOT / "references" / "course-execution-protocol.md",
        TEACHING_ROOT / "references" / "apps-script-ui-zh-tw.md",
        TEACHING_ROOT
        / "examples"
        / "course-progress-template.md",
        TEACHING_ROOT / "examples" / "first-sheet-lesson" / "README.md",
        TEACHING_ROOT / "examples" / "first-sheet-lesson" / "Code.gs",
        TEACHING_ROOT / "templates" / "README.md",
        TEACHING_ROOT / "templates" / "catalog.json",
        TEACHING_ROOT / "templates" / "activity-registration" / "README.md",
        TEACHING_ROOT / "scripts" / "materialize_template.py",
        TEACHING_ROOT / "scripts" / "test_materialize_template.py",
        TEACHING_ROOT / "scripts" / "update_course_progress.py",
        TEACHING_ROOT / "scripts" / "test_update_course_progress.py",
        PROJECT_ROOT / "SKILL.md",
        PROJECT_ROOT / "agents" / "openai.yaml",
        PROJECT_ROOT / "references" / "agent-first-project-design.md",
        PROJECT_ROOT / "references" / "project-workflow.md",
        PROJECT_ROOT / "references" / "development-environment.md",
        PROJECT_ROOT / "references" / "basic-application-routing.md",
        PROJECT_ROOT / "references" / "project-mode-workflows.md",
        PROJECT_ROOT / "references" / "project-quality-standard.md",
        PROJECT_ROOT / "references" / "ui-operation-policy.md",
        PROJECT_ROOT / "references" / "clasp-workflow.md",
        PROJECT_ROOT / "references" / "deployment-workflow.md",
        PROJECT_ROOT / "references" / "security-and-github.md",
        PROJECT_ROOT / "examples" / "basic-project" / "README.md",
        PROJECT_ROOT / "examples" / "basic-project" / ".claspignore",
        PROJECT_ROOT / "examples" / "basic-project" / ".gitignore",
        PROJECT_ROOT / "examples" / "basic-project" / "src" / "00_Log.gs",
        PROJECT_ROOT / "examples" / "basic-project" / "src" / "01_Config.gs",
        PROJECT_ROOT / "examples" / "basic-project" / "src" / "Main.gs",
        PROJECT_ROOT / "examples" / "basic-project" / "src" / "Tests.gs",
        PROJECT_ROOT
        / "examples"
        / "basic-project"
        / "src"
        / "appsscript.json",
        DEBUGGING_ROOT / "SKILL.md",
        DEBUGGING_ROOT / "agents" / "openai.yaml",
        DEBUGGING_ROOT / "references" / "debugging-workflow.md",
        DOCS_LAYOUT_ROOT / "SKILL.md",
        DOCS_LAYOUT_ROOT / "agents" / "openai.yaml",
        DOCS_LAYOUT_ROOT / "references" / "fixed-layout-workflow.md",
        DOCS_LAYOUT_ROOT / "references" / "envelope-layout-baseline.md",
    ]
    return [
        f"缺少必要檔案：{path.relative_to(REPOSITORY_ROOT)}"
        for path in required_files
        if not path.is_file()
    ]


def validate_public_license() -> list[str]:
    """確認公開儲存庫使用已核准的 MIT 授權及著作權名稱。"""
    errors: list[str] = []
    license_path = REPOSITORY_ROOT / "LICENSE.learn-gas"
    readme_path = REPOSITORY_ROOT / "docs" / "apps-script-guide.md"

    if license_path.is_file():
        license_content = license_path.read_text(encoding="utf-8")
        for fragment in [
            "MIT License",
            "Copyright (c) 2026 iamraven-tw",
            "Permission is hereby granted, free of charge",
        ]:
            if fragment not in license_content:
                errors.append(f"LICENSE 缺少必要內容：{fragment}")

    return errors


def validate_skill_entrypoints() -> list[str]:
    """確認 repository 只有四個預期的 SKILL.md 入口。"""
    expected_paths = {root / "SKILL.md" for root in EXPECTED_SKILLS}
    expected_paths.add(SKILLS_ROOT / "google-workflow-router" / "SKILL.md")
    actual_paths = set(SKILLS_ROOT.glob("*/SKILL.md"))
    errors: list[str] = []

    for path in sorted(expected_paths - actual_paths):
        errors.append(f"缺少技能入口：{path.relative_to(REPOSITORY_ROOT)}")
    for path in sorted(actual_paths - expected_paths):
        errors.append(f"發現非預期技能入口：{path.relative_to(REPOSITORY_ROOT)}")

    for root, expected_name in EXPECTED_SKILLS.items():
        path = root / "SKILL.md"
        if not path.is_file():
            continue

        content = path.read_text(encoding="utf-8")
        match = re.match(
            r"^---\n(?P<header>.*?)\n---\n",
            content,
            re.DOTALL,
        )
        if match is None:
            errors.append(f"{expected_name} 缺少有效 YAML frontmatter")
            continue

        header = match.group("header")
        if f"name: {expected_name}" not in header:
            errors.append(f"{expected_name} 的 frontmatter name 不正確")
        if not re.search(r"^description:\s*\S+", header, re.MULTILINE):
            errors.append(f"{expected_name} 缺少 description")

    return errors


def validate_installation_contract() -> list[str]:
    """新的安裝契約由 Toolbox 套件驗證器管理；此處核對內建入口。"""
    import tomllib
    manifest = tomllib.loads((REPOSITORY_ROOT / "install.manifest.toml").read_text(encoding="utf-8"))
    expected = {root.name for root in EXPECTED_SKILLS} | {"google-workflow-router", "learner-facing-terminology.md"}
    if manifest.get("schema_version") != 2 or set(manifest["installation"]["managed_entries"]) != expected:
        return ["Toolbox 內建安裝契約不完整"]
    return []


def validate_skill_boundaries() -> list[str]:
    """確認四個技能的責任及轉接文字完整。"""
    checks = {
        REPOSITORY_ROOT / "docs" / "apps-script-guide.md": [
            "教學模式的正常、錯誤、重複執行",
            "工程測試由 Agent 完成",
            "真正的 UI 使用流程",
        ],
        TEACHING_ROOT / "SKILL.md": [
            "本技能只負責教學內容",
            "google-apps-script-project-development",
            "google-apps-script-debugging",
            "google-docs-layout",
            "共用的首次使用環境關卡",
            "一次載入或展示八課內容",
            "正常測試、錯誤測試、重複執行測試",
            "保留使用者手動調整的欄寬",
            "Google Docs 的頁面方向不等於內容排版",
            "每次 `clasp push` 完成後",
            "在同一則回覆一次說完",
            "第二階段要提供已核對的試算表連結",
            "不得停在「請回覆已重整」",
            "可點擊的 Apps Script 編輯器網址",
            "不得另外顯示原始 Script ID",
            "在 Apps Script 左側『檔案』選擇 `<檔案名稱>`",
            "不得省略先選檔案的步驟",
            "這個應用程式未經 Google 驗證",
            "前往『<教材名稱>』（不安全）",
            "提供可點擊網址",
            "提供可複製的完整 ID",
            "不得要求學生自己找網址",
            "scripts/update_course_progress.py",
            "不把進度紀錄工作交給學生",
        ],
        PROJECT_ROOT / "SKILL.md": [
            "本技能負責開發環境",
            "共用首次使用環境關卡",
            "Agent First 專案設計",
            "使用者確認操作方式後才選定技術架構",
            "預設使用依功能分檔的 `.gs`",
            "預設不操作使用者的電腦或瀏覽器 UI",
            "教學技能的 Script Properties",
            "可驗證的繁體中文紀錄檔(Log)",
            "觸發器",
            "部署、版本與回復流程",
            "google-apps-script-teaching",
            "google-apps-script-debugging",
            "google-docs-layout",
            "遠端確認",
            "clasp push",
        ],
        DEBUGGING_ROOT / "SKILL.md": [
            "本技能負責所有 Apps Script",
            "首次使用環境關卡",
            "重述完整業務邏輯",
            "使用者確認",
            "既有「執行記錄」",
            "一次驗證一個假設",
            "google-apps-script-project-development",
            "google-docs-layout",
            "回歸測試",
        ],
        DOCS_LAYOUT_ROOT / "SKILL.md": [
            "本技能負責把參考圖或位置需求",
            "google-apps-script-project-development",
            "google-apps-script-teaching",
            "google-apps-script-debugging",
            "本技能不是新的首頁模式",
            "固定版面工作流程",
            "信封排版定稿案例",
            "一個無框線表格",
            "不得在每個字後插入手動換行",
            "TableCell.editAsText()",
            "getFontSize(offset)",
            "使用者開啟文件目視確認",
            "不可任意改動的基線",
        ],
    }
    errors: list[str] = []
    for path, fragments in checks.items():
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(
                    f"技能邊界缺少必要內容："
                    f"{path.relative_to(REPOSITORY_ROOT)}：{fragment}"
                )

    old_root = SKILLS_ROOT / "google-apps-script-project-guide"
    if (old_root / "SKILL.md").exists():
        errors.append("舊的 google-apps-script-project-guide 入口仍存在")

    return errors


def validate_agent_prompts() -> list[str]:
    """確認四個預設提示符合各自責任。"""
    checks = {
        TEACHING_ROOT / "agents" / "openai.yaml": [
            "$google-apps-script-teaching",
            "一次只進行一個案例或一課",
            "Script Properties",
            "google-docs-layout",
            "推送到Apps Script(clasp push)",
            "已有 validated 教學模板時直接取用",
            "不要重新生成同一套程式",
            "自由選擇第一階段或第二階段",
            "兩者沒有先修限制",
            "第一階段五個案例彼此獨立",
            "不要強制依編號完成",
            "完成一個後再讓我選擇",
            "統一課程進度",
            "第二階段八課共用同一個累積專案",
            "進入第二階段後固定依序完成第 1 至第 8 課",
            "每課完成後直接開始下一課",
            "不要再問我要不要繼續或切換階段",
            "若資源由你建立",
            "直接提供完整 ID",
            "不得要求我自己找網址或拆出 ID",
        ],
        PROJECT_ROOT / "agents" / "openai.yaml": [
            "$google-apps-script-project-development",
            "再檢查環境",
            "本機 commit",
            "預設不要操作我的 UI",
            "正常／錯誤／重複執行測試",
            "設定與檢查函式",
            "google-docs-layout",
            "推送到Apps Script(clasp push)",
            "已有 validated 程式模板時直接安全取用",
            "不要重新生成或覆寫不同內容",
            "第一階段五個案例彼此獨立",
            "不要強制依編號完成",
            "完成一個後再讓我選擇",
            "第二階段八課共用同一個累積專案",
            "進入第二階段後固定依序完成第 1 至第 8 課",
            "不要詢問是否繼續或切換",
            "中斷時從最早未完成處恢復",
            "若由你建立且需要填入指令碼屬性",
            "直接提供完整 ID",
            "不得要求我自己找網址或拆出 ID",
        ],
        DEBUGGING_ROOT / "agents" / "openai.yaml": [
            "$google-apps-script-debugging",
            "重述我希望製作的完整業務邏輯",
            "取得我的確認後",
            "優先用既有紀錄檔(Log)",
            "可重現案例",
            "一次驗證一個假設",
            "回歸測試",
            "google-docs-layout",
        ],
        DOCS_LAYOUT_ROOT / "agents" / "openai.yaml": [
            "$google-docs-layout",
            "參考圖",
            "單一無框線表格",
            "整格文字套用字體",
            "遠端讀回實際文字樣式",
            "推送到Apps Script(clasp push)",
        ],
    }
    errors: list[str] = []
    for path, fragments in checks.items():
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(
                    f"預設提示缺少必要內容："
                    f"{path.relative_to(REPOSITORY_ROOT)}：{fragment}"
                )
    return errors


def validate_web_operation_links() -> list[str]:
    """確認所有技能要求網頁操作指示同時提供可點擊連結。"""
    checks = {
        REPOSITORY_ROOT / "docs" / "apps-script-guide.md": [
            "開啟、切換或操作任何網頁",
            "已核對且可點擊的目標連結",
            "不要求使用者自行尋找頁面",
        ],
        TEACHING_ROOT / "SKILL.md": [
            "開啟、切換或操作任何網頁",
            "已核對且可點擊的目標連結",
            "在連結可提供前不得要求學生自行尋找",
        ],
        PROJECT_ROOT / "SKILL.md": [
            "開啟、切換或操作任何網頁",
            "已核對且可點擊的目標連結",
            "在連結可提供前不得要求使用者自行尋找",
        ],
        DEBUGGING_ROOT / "SKILL.md": [
            "操作任何網頁",
            "已核對且可點擊的目標連結",
            "不要求使用者自行尋找頁面",
        ],
        DOCS_LAYOUT_ROOT / "SKILL.md": [
            "操作任何網頁",
            "已核對且可點擊的目標連結",
            "不要求使用者自行尋找文件或頁面",
        ],
        PROJECT_ROOT / "references" / "ui-operation-policy.md": [
            "## 網址先行",
            "同一則指示中提供已核對且可點擊的目標連結",
            "從 Apps Script 回到 Sheets 驗收",
            "不得捏造網址",
        ],
        TEACHING_ROOT / "references" / "teaching-workflow.md": [
            "從 Apps Script 回到 Sheets",
            "必須重新附上目的地連結",
        ],
        TEACHING_ROOT / "references" / "course-execution-protocol.md": [
            "每次從 Apps Script 切換到 Sheets",
            "不得要求使用者自行尋找頁面",
        ],
    }
    prompt_paths = [
        TEACHING_ROOT / "agents" / "openai.yaml",
        PROJECT_ROOT / "agents" / "openai.yaml",
        DEBUGGING_ROOT / "agents" / "openai.yaml",
        DOCS_LAYOUT_ROOT / "agents" / "openai.yaml",
    ]
    errors: list[str] = []

    for path, fragments in checks.items():
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(
                    f"網頁操作連結規則缺少必要內容："
                    f"{path.relative_to(REPOSITORY_ROOT)}：{fragment}"
                )

    for path in prompt_paths:
        content = path.read_text(encoding="utf-8")
        if "操作任何網頁" not in content or "可點擊的目標連結" not in content:
            errors.append(
                f"預設提示缺少網頁操作連結規則："
                f"{path.relative_to(REPOSITORY_ROOT)}"
            )

    return errors


def validate_resource_id_explanations() -> list[str]:
    """確認教學在填寫 Google 資源 ID 前先解釋指令碼屬性的目的。"""
    checks = {
        TEACHING_ROOT / "SKILL.md": [
            "Google 資源的「門牌號碼」",
            "換資源時不用改程式",
            "不得只列屬性名稱與值就要求學生填入",
        ],
        TEACHING_ROOT / "references" / "teaching-workflow.md": [
            "ID 像該資源的「門牌號碼」",
            "讓設定與程式碼分開",
            "必須在 UI 填寫步驟之前說明",
            "若非敏感 Google 資源由 Agent 建立",
            "不得把擷取工作交給學生",
            "只有使用者原有或親自建立的資源",
        ],
        TEACHING_ROOT / "references" / "teaching-examples.md": [
            "ID 是資源的「門牌號碼」",
            "換資源時不用改程式",
            "不把私人 ID 寫進原始碼、紀錄檔(Log)或 Git",
            "一般 Google 資源由 Agent 建立時",
            "不得要求學生自己拆網址",
        ],
        TEACHING_ROOT / "references" / "course-execution-protocol.md": [
            "同一份 Google 資源的「門牌號碼」",
            "說明完成後才進入 UI 填寫",
            "不得只丟出屬性名稱與值",
            "若一般 Google 資源由 Agent 建立",
            "不得要求學生自己拆網址",
        ],
        TEACHING_ROOT
        / "references"
        / "lessons"
        / "lesson-02-properties.md": [
            "Spreadsheet ID 可以想成試算表的「門牌號碼」",
            "換試算表時只改設定",
            "本課試算表由 Agent 建立",
            "不把這項工作交給學生",
        ],
        TEACHING_ROOT / "references" / "beginner-application-path.md": [
            "ID 像資源的「門牌號碼」",
            "Form ID 是這份表單的「門牌號碼」",
            "`QUIZ_FORM_ID`讓程式後續更新同一份測驗",
        ],
    }
    errors: list[str] = []

    for path, fragments in checks.items():
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(
                    f"資源 ID 教學說明缺少必要內容："
                    f"{path.relative_to(REPOSITORY_ROOT)}：{fragment}"
                )

    # 核心流程不得再保留未區分資源來源的舊句子，避免 Agent 把擷取工作丟回學生。
    ambiguous_rules = {
        TEACHING_ROOT / "references" / "teaching-workflow.md": [
            "非敏感的 Google 資源 URL／ID 可由使用者主動提供",
        ],
        TEACHING_ROOT / "references" / "teaching-examples.md": [
            "一般 Google 資源 URL／ID 等非敏感設定，可由使用者主動貼給 Agent",
        ],
        TEACHING_ROOT / "references" / "course-execution-protocol.md": [
            "一般 Google 資源 URL／ID 等非敏感設定，可由使用者主動貼給 Agent",
        ],
        TEACHING_ROOT
        / "references"
        / "lessons"
        / "lesson-02-properties.md": [
            "一般 Google 資源 URL／ID 不是密碼，可由使用者主動提供給 Agent",
        ],
        PROJECT_ROOT / "references" / "project-quality-standard.md": [
            "一般 Google 資源 URL／ID 等非敏感設定，可由使用者主動貼給 Agent",
        ],
    }
    for path, fragments in ambiguous_rules.items():
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment in content:
                errors.append(
                    f"資源 ID 流程仍含未區分來源的舊規則："
                    f"{path.relative_to(REPOSITORY_ROOT)}：{fragment}"
                )

    prompt_path = TEACHING_ROOT / "agents" / "openai.yaml"
    prompt = prompt_path.read_text(encoding="utf-8")
    if (
        "Google 資源 ID 放進指令碼屬性前" not in prompt
        or "先用白話說明這樣做的原因" not in prompt
    ):
        errors.append("教學預設提示缺少資源 ID 指令碼屬性原因說明")

    return errors


def validate_teaching_closing_questions() -> list[str]:
    """確認每個教學範例都用低負擔小問題收尾，且答錯不阻擋進度。"""
    checks = {
        TEACHING_ROOT / "SKILL.md": [
            "每個教學範例的最後都安排一題",
            "不論答對或答錯都可繼續下一個範例",
        ],
        TEACHING_ROOT / "references" / "teaching-workflow.md": [
            "每個教學範例完成實際成果驗收後",
            "只回覆選項數字",
            "不得要求重答",
        ],
        TEACHING_ROOT / "references" / "beginner-application-path.md": [
            "每個案例通過可見成果驗收後",
            "不論答對或答錯都能繼續下一個案例",
        ],
        TEACHING_ROOT / "references" / "course-execution-protocol.md": [
            "收尾小問題",
            "不論答對或答錯都算完成檢查點",
        ],
        TEACHING_ROOT / "references" / "teaching-examples.md": [
            "**收尾小問題**",
            "不論答對或答錯都可繼續",
        ],
        TEACHING_ROOT / "examples" / "first-sheet-lesson" / "README.md": [
            "最後問學生",
            "不論答對或答錯都可繼續下一課",
        ],
    }
    errors: list[str] = []

    for path, fragments in checks.items():
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(
                    f"教學收尾小問題規則缺少必要內容："
                    f"{path.relative_to(REPOSITORY_ROOT)}：{fragment}"
                )

    prompt = (
        TEACHING_ROOT / "agents" / "openai.yaml"
    ).read_text(encoding="utf-8")
    if "每個教學範例最後問一題簡短的小問題" not in prompt:
        errors.append("教學預設提示缺少每個範例的收尾小問題")

    return errors


def validate_agent_owned_teaching_tests() -> list[str]:
    """確認工程測試由 Agent 負責，學生只做真實 UI 驗收。"""
    checks = {
        TEACHING_ROOT / "SKILL.md": [
            "Agent 負責執行正常測試、錯誤測試、重複執行測試",
            "不得把測試矩陣轉成學生逐項點選函式的作業",
            "學生的一次真實 UI 驗收",
            "學生只執行一次真正的使用流程",
            "每一個要求學生操作或回報的步驟",
            "正常流程已成功時，不得把反覆查看",
        ],
        TEACHING_ROOT / "agents" / "openai.yaml": [
            "不要要求我逐項執行測試函式",
            "真正的 UI 使用流程",
        ],
        TEACHING_ROOT / "references" / "teaching-workflow.md": [
            "測試函式可以保留供 Agent 驗證與除錯",
            "不是學生的例行操作",
            "不要求學生為了證明工程品質而重跑",
            "不代表把工程測試責任交回學生",
            "不是正常成功流程的學習成果",
        ],
        TEACHING_ROOT / "references" / "beginner-application-path.md": [
            "由 Agent 執行並保存證據",
            "不要求學生逐項操作測試函式",
        ],
        TEACHING_ROOT / "references" / "teaching-examples.md": [
            "第 1 至 5 項由 Agent 執行並保存證據",
            "不得列成學生每課都要依序操作的作業",
        ],
        TEACHING_ROOT / "references" / "learning-path.md": [
            "程式與工程測試由 AI Agent 負責",
            "使用者親自從該選單完成案例真正的 UI 使用流程",
        ],
        TEACHING_ROOT / "references" / "course-execution-protocol.md": [
            "### E. 使用者 UI 驗收",
            "測試函式只供 Agent 驗證或除錯",
            "使用者親自完成本課指定的真實 UI 操作",
            "每個學生步驟都要能回答",
            "正常成功時不得列成學生的額外回報關卡",
        ],
        PROJECT_ROOT / "references" / "project-mode-workflows.md": [
            "工程測試由 Agent 執行",
            "操作真正的教學 UI",
        ],
    }
    errors: list[str] = []
    for path, fragments in checks.items():
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(f"{path.relative_to(REPOSITORY_ROOT)} 缺少 Agent 測試分工：{fragment}")

    lessons_root = TEACHING_ROOT / "references" / "lessons"
    for path in sorted(lessons_root.glob("lesson-*.md")):
        content = path.read_text(encoding="utf-8")
        if "## 使用者 UI 驗收順序" not in content:
            errors.append(f"{path.name} 缺少使用者 UI 驗收順序")
        if "工程測試" not in content or "Agent" not in content:
            errors.append(f"{path.name} 未明確說明工程測試由 Agent 負責")
        if "## 遠端測試順序" in content:
            errors.append(f"{path.name} 仍使用舊的遠端測試順序標題")

    return errors


def validate_drive_activity_teaching_exception() -> list[str]:
    """確認檔案上傳案例的 Drive Activity 窄例外與免費邊界一致。"""
    checks = {
        TEACHING_ROOT / "SKILL.md": [
            "唯一已確認的進階服務例外",
            "Google Drive Activity v2",
            "不延伸到其他案例或進階服務",
        ],
        PROJECT_ROOT / "SKILL.md": [
            "唯一已確認的進階服務例外",
            "使用 Apps Script 預設 Cloud 專案",
        ],
        PROJECT_ROOT / "references" / "basic-application-routing.md": [
            "只限「指定資料夾檔案上傳紀錄器」辨識外部上傳",
            "預設 Cloud 專案會在加入服務時自動啟用對應 API",
            "其他情境則寫明沒有使用進階服務",
        ],
        TEACHING_ROOT / "references" / "beginner-application-path.md": [
            "免費的 Google Drive Activity 進階服務",
            "不能把它們說成上傳者與上傳時間",
            "不得猜測姓名或 Email",
        ],
    }
    errors: list[str] = []

    for path, fragments in checks.items():
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(
                    f"Drive Activity 教學例外缺少必要內容："
                    f"{path.relative_to(REPOSITORY_ROOT)}：{fragment}"
                )

    return errors


def validate_high_frequency_teaching_trigger_safety() -> list[str]:
    """確認高頻教學觸發器有停止入口、期限與配額說明。"""
    checks = {
        TEACHING_ROOT / "SKILL.md": [
            "學生可見的停止入口",
            "程式自動到期保護",
            "高頻設定只供短暫教學",
            "不得停在「已啟用」",
            "外部影響上限必須涵蓋整次授權",
            "外部動作前留下單次嘗試記號",
            "按「使用者」加總",
            "不是每個專案各自計算",
        ],
        TEACHING_ROOT / "references" / "course-execution-protocol.md": [
            "不能只用文字提醒學生稍後關閉",
            "「已啟用」不是需要停下回報的檢查點",
            "顯示目前是否啟用與安全期限",
            "學生忘記操作時也不會無期限耗用配額",
            "不得把每次執行的批次上限誤當成",
            "按建立者帳號跨專案加總",
            "不得把理論上限直接當成安全值",
        ],
        TEACHING_ROOT / "references" / "beginner-application-path.md": [
            "啟用每分鐘檢查（教學 10 分鐘）",
            "停止自動檢查",
            "查看自動檢查狀態",
            "runUploadCheckByTimer",
            "每分鐘執行一天會觸發 1,440 次",
            "每 15 或 30 分鐘",
            "Google 官方配額說明",
            "Apps Script、Sheets 與測試資料夾連結",
            "不得停在「已啟用」要求學生先回覆",
            "免費額度與正式使用間隔",
            "每日總執行時間是 90 分鐘",
            "不是每個專案各有 90 分鐘",
            "同一個 Google 帳號",
            "1、5、10、15 或 30 分鐘",
            "3.75 秒",
            "30 分鐘：免費帳號的建議預設",
            "執行時間一起保留安全餘裕",
        ],
    }
    errors: list[str] = []

    for path, fragments in checks.items():
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(
                    "高頻教學觸發器缺少安全規則："
                    f"{path.relative_to(REPOSITORY_ROOT)}：{fragment}"
                )

    return errors


def validate_manifest_push_confirmation() -> list[str]:
    """確認資訊清單變更不會被非互動式 clasp push 假成功掩蓋。"""
    checks = {
        PROJECT_ROOT / "SKILL.md": [
            "`appsscript.json`有變更",
            "`Skipping push`",
            "不得改用強制推送",
            "第一次就必須使用互動式終端",
            "不得先用非互動模式試跑",
        ],
        PROJECT_ROOT / "references" / "clasp-workflow.md": [
            "### 資訊清單覆寫提示",
            "Manifest file has been updated",
            "使用互動式終端",
            "第一次就使用互動式終端（具 TTY）",
            "以互動式終端重跑同一個一般 `clasp push`",
            "Apps Script API 或其他唯讀方式比對遠端檔案名稱與內容",
            "`檔名.gs`與`檔名.js`逐一比較實際內容",
            "遠端查驗命令必須設定遇錯即停",
            "不得繼續輸出「逐檔比對通過」",
            "不覆寫學生專案",
        ],
        DEBUGGING_ROOT / "references" / "debugging-workflow.md": [
            "只顯示`Skipping push`",
            "等待互動式覆寫確認",
            "不得以`--force`取代原因確認",
        ],
    }
    errors: list[str] = []

    for path, fragments in checks.items():
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(
                    f"資訊清單推送確認規則缺少必要內容："
                    f"{path.relative_to(REPOSITORY_ROOT)}：{fragment}"
                )

    return errors


def validate_clasp_push_terminology() -> list[str]:
    """確認所有技能入口都使用初學者可理解的推送固定用語。"""
    fixed_term = "推送到Apps Script(clasp push)"
    entrypoint_paths = [
        REPOSITORY_ROOT / "docs" / "apps-script-guide.md",
        REPOSITORY_ROOT / "AGENTS.md",
        TEACHING_ROOT / "SKILL.md",
        PROJECT_ROOT / "SKILL.md",
        DEBUGGING_ROOT / "SKILL.md",
        DOCS_LAYOUT_ROOT / "SKILL.md",
        TEACHING_ROOT / "agents" / "openai.yaml",
        PROJECT_ROOT / "agents" / "openai.yaml",
        DEBUGGING_ROOT / "agents" / "openai.yaml",
        DOCS_LAYOUT_ROOT / "agents" / "openai.yaml",
        TEACHING_ROOT / "references" / "teaching-workflow.md",
        TEACHING_ROOT / "references" / "course-execution-protocol.md",
        PROJECT_ROOT / "references" / "clasp-workflow.md",
    ]
    errors: list[str] = []

    for path in entrypoint_paths:
        content = path.read_text(encoding="utf-8")
        if fixed_term not in content:
            errors.append(
                "推送固定用語缺失："
                f"{path.relative_to(REPOSITORY_ROOT)}：{fixed_term}"
            )

    explanation_checks = {
        TEACHING_ROOT / "SKILL.md": [
            "本機已完成並通過測試的程式與資訊清單",
            "不等於執行函式、寄信、建立觸發器或部署",
            "不得只寫 `clasp push`",
        ],
        PROJECT_ROOT / "SKILL.md": [
            "本機已完成並通過測試的程式與資訊清單",
            "不等於執行函式、寄信、建立觸發器或部署",
            "不得只顯示英文命令",
        ],
        TEACHING_ROOT / "references" / "teaching-workflow.md": [
            "同步到指定的 Google Apps Script 專案",
            "不等於執行函式、寄信、建立觸發器或部署",
            "終端命令、程式碼區塊與 Agent 內部工程檢查",
        ],
        TEACHING_ROOT / "references" / "course-execution-protocol.md": [
            "這一步只更新遠端程式",
            "你不需要操作終端機",
            "不得只顯示英文命令",
        ],
        PROJECT_ROOT / "references" / "clasp-workflow.md": [
            "同步到指定的 Google Apps Script 專案",
            "不等於執行函式、寄信、建立觸發器或部署",
            "命令、版本與檔案清單留給 Agent 自行核對",
        ],
    }
    for path, fragments in explanation_checks.items():
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(
                    "推送意涵說明不完整："
                    f"{path.relative_to(REPOSITORY_ROOT)}：{fragment}"
                )

    return errors


def validate_learner_facing_terminology() -> list[str]:
    """確認學員術語以中文為主，並保留必要英文對照。"""
    required_terms = [
        "紀錄檔(Log)",
        "函式(function)",
        "指令碼屬性(Script Properties)",
        "使用者介面(UI)",
        "識別碼(ID)",
        "網址(URL)",
        "電子郵件(Email)",
        "應用程式介面(API)",
        "授權機制(OAuth)",
        "觸發器(trigger)",
        "部署(deployment)",
        "資訊清單(manifest)",
        "網路應用程式(Web App)",
        "網路回呼(Webhook)",
        "版本控制(Git)",
        "本機版本提交(commit)",
        "AI 代理(Agent)",
        "推送到Apps Script(clasp push)",
    ]
    entrypoint_paths = [
        REPOSITORY_ROOT / "docs" / "apps-script-guide.md",
        REPOSITORY_ROOT / "AGENTS.md",
        TEACHING_ROOT / "SKILL.md",
        PROJECT_ROOT / "SKILL.md",
        DEBUGGING_ROOT / "SKILL.md",
        DOCS_LAYOUT_ROOT / "SKILL.md",
        TEACHING_ROOT / "agents" / "openai.yaml",
        PROJECT_ROOT / "agents" / "openai.yaml",
        DEBUGGING_ROOT / "agents" / "openai.yaml",
        DOCS_LAYOUT_ROOT / "agents" / "openai.yaml",
        TEACHING_ROOT / "references" / "teaching-workflow.md",
        TEACHING_ROOT / "references" / "apps-script-ui-zh-tw.md",
    ]
    errors: list[str] = []

    terminology = LEARNER_TERMINOLOGY_PATH.read_text(encoding="utf-8")
    for term in required_terms:
        if term not in terminology:
            errors.append(f"初學者術語表缺少固定名稱：{term}")

    for path in entrypoint_paths:
        content = path.read_text(encoding="utf-8")
        if "中文名稱(English)" not in content:
            errors.append(
                "技能入口缺少中英術語格式："
                f"{path.relative_to(REPOSITORY_ROOT)}"
            )
        if "紀錄檔(Log)" not in content:
            errors.append(
                "技能入口缺少紀錄檔固定名稱："
                f"{path.relative_to(REPOSITORY_ROOT)}"
            )

    # 檔名與程式識別字中的 Log 必須保留；其餘文件不得只寫英文名稱。
    standalone_log = re.compile(
        r"(?<!紀錄檔\()(?<![A-Za-z0-9_])Log(?![A-Za-z0-9_])"
    )
    documentation_paths = [
        REPOSITORY_ROOT / "AGENTS.md",
        REPOSITORY_ROOT / "docs" / "apps-script-guide.md",
        *sorted(SKILLS_ROOT.rglob("*.md")),
        *sorted(SKILLS_ROOT.rglob("*.yaml")),
        *sorted(SKILLS_ROOT.rglob("*.gs")),
    ]
    for path in documentation_paths:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if standalone_log.search(line):
                errors.append(
                    "文件仍單獨使用英文紀錄檔名稱："
                    f"{path.relative_to(REPOSITORY_ROOT)}:{line_number}"
                )

    return errors


def validate_manifest() -> list[str]:
    """確認基本專案 manifest 可解析且不預先擴張 OAuth scopes。"""
    manifest_path = (
        PROJECT_ROOT
        / "examples"
        / "basic-project"
        / "src"
        / "appsscript.json"
    )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"範例 appsscript.json 無法解析：{error}"]

    errors: list[str] = []
    if manifest.get("runtimeVersion") != "V8":
        errors.append("範例 appsscript.json 必須使用 V8 runtime")
    if "oauthScopes" in manifest:
        errors.append("基本範例不應預先加入 OAuth scopes")
    return errors


def validate_sensitive_files() -> list[str]:
    """避免把 clasp 憑證或私人專案對應檔加入 repository。"""
    forbidden_names = {".clasprc.json", ".clasp.json"}
    errors: list[str] = []
    for path in REPOSITORY_ROOT.rglob("*"):
        if path.is_file() and path.name in forbidden_names:
            errors.append(
                f"發現不應提交的檔案：{path.relative_to(REPOSITORY_ROOT)}"
            )
    return errors


def validate_teaching_templates() -> list[str]:
    """確認已驗收模板完整、可解析，且沒有私人專案資料。"""
    catalog_path = TEACHING_TEMPLATES_ROOT / "catalog.json"
    if not catalog_path.is_file():
        return ["缺少教學模板登錄表：skills/google-apps-script-teaching/templates/catalog.json"]

    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"教學模板登錄表無法解析：{error}"]

    errors: list[str] = []
    if catalog.get("schemaVersion") != 1:
        errors.append("教學模板登錄表 schemaVersion 必須是 1")

    templates = catalog.get("templates")
    if not isinstance(templates, list):
        return [*errors, "教學模板登錄表的 templates 必須是陣列"]

    expected_beginner = {
        "beginner/expense-tracker": {
            "sourceCommit": "bb09854",
            "fragments": [
                "function setupExpenseTracker()",
                "function checkExpenseTrackerSettings()",
                "function testExpenseTrackerNormal()",
                "function testExpenseTrackerInvalidAmount()",
                "function testExpenseTrackerRepeat()",
            ],
        },
        "beginner/envelope-generator": {
            "sourceCommit": "72e260c",
            "fragments": [
                "function setupEnvelopeGenerator()",
                "function generateEnvelopeDocuments()",
                "function checkEnvelopeSettings()",
                "function testEnvelopeNormal()",
                "function testEnvelopeLandscape()",
                "function testEnvelopeInvalidAddress()",
                "function testEnvelopeRepeat()",
            ],
        },
        "beginner/quiz-generator": {
            "sourceCommit": "f9f9b5b",
            "fragments": [
                "function setupQuizGenerator()",
                "function checkQuizBank()",
                "function generateQuizForm()",
                "function updateScoreReport()",
                "function testQuizNormal()",
                "function testQuizErrors()",
                "function testQuizRepeat()",
            ],
        },
        "beginner/drive-upload-logger": {
            "sourceCommit": "45dd343",
            "fragments": [
                "function setupDriveUploadLogger()",
                "function checkDriveUploadSettings()",
                "function initializeUploadBaseline()",
                "function checkNewDriveUploads(event)",
                "function setupUploadCheckTrigger()",
                "function removeUploadCheckTrigger()",
                "function testDriveUploadNormal()",
                "function testDriveUploadErrors()",
                "function testDriveUploadRepeat()",
            ],
        },
        "beginner/personalized-batch-mailer": {
            "sourceCommit": "7910d19",
            "fragments": [
                "function setupPersonalizedBatchMailer()",
                "function sendPersonalizedBatchEmails()",
                "function runBatchMailerDryRunTests()",
            ],
        },
    }
    by_id: dict[str, dict[str, object]] = {}
    for item in templates:
        if not isinstance(item, dict):
            errors.append("教學模板登錄表包含非物件項目")
            continue
        template_id = item.get("id")
        if not isinstance(template_id, str) or not template_id:
            errors.append("教學模板缺少有效 id")
            continue
        if template_id in by_id:
            errors.append(f"教學模板 id 重複：{template_id}")
            continue
        by_id[template_id] = item

    for template_id, expected in expected_beginner.items():
        item = by_id.get(template_id)
        if item is None:
            errors.append(f"缺少第一階段已驗收模板：{template_id}")
            continue
        if item.get("status") != "validated":
            errors.append(f"第一階段模板必須是 validated：{template_id}")
        if item.get("sourceCommit") != expected["sourceCommit"]:
            errors.append(f"第一階段模板來源 commit 不符：{template_id}")

        source_root_value = item.get("sourceRoot")
        files_value = item.get("files")
        if not isinstance(source_root_value, str) or not isinstance(files_value, list):
            errors.append(f"已驗收模板缺少 sourceRoot 或 files：{template_id}")
            continue

        source_root = (TEACHING_TEMPLATES_ROOT / source_root_value).resolve()
        try:
            source_root.relative_to(TEACHING_TEMPLATES_ROOT.resolve())
        except ValueError:
            errors.append(f"模板來源超出 templates 目錄：{template_id}")
            continue
        if not source_root.is_dir():
            errors.append(f"模板來源目錄不存在：{template_id}")
            continue

        listed_files: set[str] = set()
        combined_source = ""
        for raw_file in files_value:
            if not isinstance(raw_file, str):
                errors.append(f"模板檔案清單包含非字串：{template_id}")
                continue
            relative = Path(raw_file)
            if relative.is_absolute() or ".." in relative.parts:
                errors.append(f"模板檔案路徑不安全：{template_id}：{raw_file}")
                continue
            listed_files.add(relative.as_posix())
            path = source_root / relative
            if not path.is_file():
                errors.append(f"模板檔案不存在：{template_id}：{raw_file}")
                continue
            if path.suffix == ".gs":
                combined_source += path.read_text(encoding="utf-8") + "\n"

        actual_files = {
            path.relative_to(source_root).as_posix()
            for path in source_root.rglob("*")
            if path.is_file()
        }
        if listed_files != actual_files:
            missing = sorted(listed_files - actual_files)
            unlisted = sorted(actual_files - listed_files)
            if missing:
                errors.append(f"模板登錄但不存在的檔案：{template_id}：{missing}")
            if unlisted:
                errors.append(f"模板存在但未登錄的檔案：{template_id}：{unlisted}")

        manifest_path = source_root / "src" / "appsscript.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                errors.append(f"模板 manifest 無法解析：{template_id}：{error}")
            else:
                if manifest.get("runtimeVersion") != "V8":
                    errors.append(f"模板 manifest 必須使用 V8：{template_id}")

        ignore_path = source_root / ".claspignore"
        if ignore_path.is_file() and ".clasp.json" not in ignore_path.read_text(
            encoding="utf-8"
        ):
            errors.append(f"模板 .claspignore 未排除 .clasp.json：{template_id}")

        for fragment in expected["fragments"]:
            if fragment not in combined_source:
                errors.append(f"第一階段模板缺少必要入口：{template_id}：{fragment}")
        for log_fragment in ["開始", "成功", "失敗"]:
            if log_fragment not in combined_source:
                errors.append(f"第一階段模板缺少繁體中文紀錄檔(Log)：{template_id}：{log_fragment}")

    expected_lesson_ids = {
        f"activity-registration/lesson-{lesson:02d}" for lesson in range(1, 9)
    }
    actual_lesson_ids = {
        template_id
        for template_id in by_id
        if template_id.startswith("activity-registration/lesson-")
    }
    if actual_lesson_ids != expected_lesson_ids:
        errors.append("第二階段模板登錄表必須完整列出 lesson-01 至 lesson-08")

    progress_template_path = (
        TEACHING_ROOT / "examples" / "course-progress-template.md"
    )
    if progress_template_path.is_file():
        progress_lines = progress_template_path.read_text(
            encoding="utf-8"
        ).splitlines()
        for lesson_number in range(1, 9):
            template_id = f"activity-registration/lesson-{lesson_number:02d}"
            catalog_item = by_id.get(template_id)
            if catalog_item is None:
                continue
            row_prefix = f"| 第二階段 | {lesson_number}. "
            progress_row = next(
                (line for line in progress_lines if line.startswith(row_prefix)),
                None,
            )
            if progress_row is None:
                errors.append(
                    f"統一課程進度範本缺少第二階段第 {lesson_number} 課"
                )
                continue
            cells = [cell.strip() for cell in progress_row.split("|")]
            expected_status = f"`{catalog_item.get('status')}`"
            if len(cells) != 9 or cells[6] != expected_status:
                errors.append(
                    f"統一課程進度範本與 catalog 狀態不一致：{template_id}"
                )

    expected_validated_lessons = {
        "activity-registration/lesson-01": {
            "sourceCommit": "583b904",
            "files": {
                ".claspignore",
                "src/00_Log.gs",
                "src/00_Menu.gs",
                "src/01_Sheets.gs",
                "src/appsscript.json",
            },
            "fragments": [
                "function onOpen(e)",
                "COURSE_MENU_NAME_ = '活動報名工具'",
                "初始化活動報名資料",
                "function setupLessonSheet()",
                "Session.getEffectiveUser()",
                "function checkLesson01Settings()",
                "function testLesson01Normal()",
                "function testLesson01Error()",
                "function testLesson01Repeat()",
                "本課不需要 Script Properties",
            ],
        },
        "activity-registration/lesson-02": {
            "sourceCommit": "583b904",
            "files": {
                ".claspignore",
                "src/00_Log.gs",
                "src/00_Menu.gs",
                "src/01_Sheets.gs",
                "src/02_Config.gs",
                "src/appsscript.json",
            },
            "fragments": [
                "function onOpen(e)",
                "檢查系統設定",
                "初始化活動報名資料",
                "function setupLessonSheet()",
                "function checkLesson02Settings()",
                "function testLesson02Normal()",
                "function testLesson02MissingSetting()",
                "function testLesson02WrongSpreadsheet()",
                "function testLesson02Repeat()",
                "PropertiesService.getScriptProperties()",
                "SpreadsheetApp.getActiveSpreadsheet()",
                "SPREADSHEET_ID",
            ],
        },
        "activity-registration/lesson-03": {
            "sourceCommit": "583b904",
            "files": {
                ".claspignore",
                "src/00_Log.gs",
                "src/00_Menu.gs",
                "src/01_Sheets.gs",
                "src/02_Config.gs",
                "src/03_Forms.gs",
                "src/appsscript.json",
            },
            "fragments": [
                "function onOpen(e)",
                "檢查系統設定",
                "設定活動報名表單",
                "function setupLessonSheet()",
                "function checkLesson03Settings()",
                "function setupLesson03Form()",
                "function testLesson03Normal()",
                "function testLesson03InvalidEmail()",
                "function testLesson03Repeat()",
                "function readLesson03DestinationId_",
                "function configureLesson03Item_",
                "typeof item.asTextItem === 'function'",
                "recoverableBlankItemIndex",
                "寄信驗收請填寫你能親自收信的 Email",
                "FORM_ID",
                "FormApp.openById",
            ],
        },
        "activity-registration/lesson-04": {
            "sourceCommit": "583b904",
            "files": {
                ".claspignore",
                "src/00_Log.gs",
                "src/00_Menu.gs",
                "src/01_Sheets.gs",
                "src/02_Config.gs",
                "src/03_Forms.gs",
                "src/04_Batch.gs",
                "src/appsscript.json",
            },
            "fragments": [
                "function onOpen(e)",
                "批次處理待處理報名",
                "function setupLessonSheet()",
                "function checkLesson04Settings()",
                "function processPendingRegistrations()",
                "function runLesson04Tests()",
                "function testLesson04Zero_()",
                "function testLesson04One_()",
                "function testLesson04Many_()",
                "function testLesson04Error_()",
                "function testLesson04Repeat_()",
                "待產生文件",
                "資料有誤",
                "已完成",
                "通知編號",
            ],
        },
        "activity-registration/lesson-05": {
            "sourceCommit": "583b904",
            "files": {
                ".claspignore",
                "src/00_Log.gs",
                "src/00_Menu.gs",
                "src/01_Sheets.gs",
                "src/02_Config.gs",
                "src/03_Forms.gs",
                "src/04_Batch.gs",
                "src/05_Documents.gs",
                "src/appsscript.json",
            },
            "fragments": [
                "function onOpen(e)",
                "建立報名確認文件",
                "function setupLessonSheet()",
                "function checkLesson05Settings()",
                "function createPendingRegistrationDocuments()",
                "function runLesson05Tests()",
                "function testLesson05Normal()",
                "function testLesson05MissingFolder()",
                "function testLesson05Repeat()",
                "DOC_TEMPLATE_ID",
                "OUTPUT_FOLDER_ID",
                "DriveApp.getFileById",
                "DocumentApp.openById",
                "待產生文件",
                "待寄送郵件",
                "通知編號",
            ],
        },
        "activity-registration/lesson-06": {
            "sourceCommit": "583b904",
            "files": {
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
            },
            "fragments": [
                "function onOpen(e)",
                "寄送報名確認郵件",
                "確認未寄出並重設",
                "function setupLessonSheet()",
                "Session.getEffectiveUser()",
                "function checkLesson06Settings()",
                "function confirmLesson06RegistrationEmailSend()",
                "function confirmLesson06UnsentRecovery()",
                "function sendLesson06RegistrationEmail_()",
                "function runLesson06ErrorTests()",
                "function testLesson06Repeat()",
                "MailApp.sendEmail",
                "通知編號",
                "寄送中",
                "郵件已寄出",
            ],
        },
        "activity-registration/lesson-07": {
            "sourceCommit": "c6bd4ff",
            "files": {
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
            },
            "fragments": [
                "function onOpen(e)",
                "檢查觸發器狀態",
                "啟用表單提交自動處理",
                "啟用短暫時間處理",
                "停止第 7 課自動化",
                "function onRegistrationFormSubmit(e)",
                "function processPendingRegistrationsByTimer(e)",
                "function checkLesson07Triggers()",
                "function confirmLesson07StopAutomation()",
                "function runLesson07ManualTests()",
                "LESSON07_TIMER_ATTEMPTED_AT",
                "batchSize: 1",
                ".newTrigger",
                "ScriptApp.deleteTrigger",
            ],
        },
    }

    for template_id in sorted(expected_lesson_ids):
        item = by_id.get(template_id)
        if item is None:
            continue
        status = item.get("status")
        if status not in {"pending", "validated"}:
            errors.append(f"第二階段模板狀態不正確：{template_id}：{status}")

        expected_lesson = expected_validated_lessons.get(template_id)
        if expected_lesson is not None:
            if status != "validated":
                errors.append(f"已完成課次必須是 validated：{template_id}")
            if item.get("sourceCommit") != expected_lesson["sourceCommit"]:
                errors.append(f"第二階段模板來源 commit 不符：{template_id}")

        if status != "validated":
            continue

        source_root_value = item.get("sourceRoot")
        files_value = item.get("files")
        source_commit = item.get("sourceCommit")
        if (
            not isinstance(source_root_value, str)
            or not isinstance(files_value, list)
            or not isinstance(source_commit, str)
            or not source_commit
        ):
            errors.append(f"已驗收第二階段模板缺少來源資訊：{template_id}")
            continue

        source_root = (TEACHING_TEMPLATES_ROOT / source_root_value).resolve()
        try:
            source_root.relative_to(TEACHING_TEMPLATES_ROOT.resolve())
        except ValueError:
            errors.append(f"第二階段模板來源超出 templates 目錄：{template_id}")
            continue
        if not source_root.is_dir():
            errors.append(f"第二階段模板來源目錄不存在：{template_id}")
            continue

        listed_files: set[str] = set()
        combined_source = ""
        for raw_file in files_value:
            if not isinstance(raw_file, str):
                errors.append(f"第二階段模板檔案清單包含非字串：{template_id}")
                continue
            relative = Path(raw_file)
            if relative.is_absolute() or ".." in relative.parts:
                errors.append(
                    f"第二階段模板檔案路徑不安全：{template_id}：{raw_file}"
                )
                continue
            listed_files.add(relative.as_posix())
            path = source_root / relative
            if not path.is_file():
                errors.append(f"第二階段模板檔案不存在：{template_id}：{raw_file}")
                continue
            if path.suffix == ".gs":
                combined_source += path.read_text(encoding="utf-8") + "\n"

        actual_files = {
            path.relative_to(source_root).as_posix()
            for path in source_root.rglob("*")
            if path.is_file()
        }
        if listed_files != actual_files:
            missing = sorted(listed_files - actual_files)
            unlisted = sorted(actual_files - listed_files)
            if missing:
                errors.append(
                    f"第二階段模板登錄但不存在的檔案：{template_id}：{missing}"
                )
            if unlisted:
                errors.append(
                    f"第二階段模板存在但未登錄的檔案：{template_id}：{unlisted}"
                )

        if expected_lesson is not None:
            if listed_files != expected_lesson["files"]:
                errors.append(f"第二階段模板累積檔案不完整：{template_id}")
            for fragment in expected_lesson["fragments"]:
                if fragment not in combined_source:
                    errors.append(
                        f"第二階段模板缺少必要入口或設定：{template_id}：{fragment}"
                    )
            if (
                template_id == "activity-registration/lesson-06"
                and "TEST_EMAIL" in combined_source
            ):
                errors.append("第 6 課模板仍使用過時的 TEST_EMAIL")
            if (
                template_id == "activity-registration/lesson-07"
                and "PROCESSING_BATCH_SIZE" in combined_source
            ):
                errors.append("第 7 課模板仍使用過時的 PROCESSING_BATCH_SIZE")

        for log_fragment in ["開始", "成功", "失敗"]:
            if log_fragment not in combined_source:
                errors.append(
                    f"第二階段模板缺少繁體中文紀錄檔(Log)：{template_id}：{log_fragment}"
                )

        manifest_path = source_root / "src" / "appsscript.json"
        if not manifest_path.is_file():
            errors.append(f"第二階段模板缺少 manifest：{template_id}")
        else:
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                errors.append(f"第二階段模板 manifest 無法解析：{template_id}：{error}")
            else:
                if manifest.get("runtimeVersion") != "V8":
                    errors.append(f"第二階段模板 manifest 必須使用 V8：{template_id}")
                lesson_number = int(template_id.rsplit("-", 1)[1])
                scopes = set(manifest.get("oauthScopes", []))
                user_email_scope = (
                    "https://www.googleapis.com/auth/userinfo.email"
                )
                if lesson_number <= 6 and user_email_scope not in scopes:
                    errors.append(
                        f"第二階段模板缺少學員 Email 最小權限：{template_id}"
                    )
                if lesson_number == 6:
                    send_scope = (
                        "https://www.googleapis.com/auth/script.send_mail"
                    )
                    if send_scope not in scopes:
                        errors.append("第 6 課模板缺少 MailApp 寄信權限")
                    if "https://www.googleapis.com/auth/gmail.send" in scopes:
                        errors.append("第 6 課模板仍使用過時的 Gmail API 權限")
                    dependencies = manifest.get("dependencies", {})
                    if dependencies.get("enabledAdvancedServices"):
                        errors.append("第 6 課模板不得啟用 Gmail 進階服務")

        ignore_path = source_root / ".claspignore"
        if not ignore_path.is_file():
            errors.append(f"第二階段模板缺少 .claspignore：{template_id}")
        elif ".clasp.json" not in ignore_path.read_text(encoding="utf-8"):
            errors.append(f"第二階段模板 .claspignore 未排除 .clasp.json：{template_id}")

    private_email_pattern = re.compile(
        r"\b[A-Za-z0-9._%+-]+@(?!example\.com\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        re.IGNORECASE,
    )
    long_google_id_pattern = re.compile(r"\b[A-Za-z0-9_-]{40,}\b")
    sensitive_fragments = [
        "/Users/",
        "client_secret",
        "refresh_token",
        "access_token",
        "private_key",
        "BEGIN PRIVATE KEY",
        "scriptId",
        "deploymentId",
    ]
    for path in TEACHING_TEMPLATES_ROOT.rglob("*"):
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        relative_path = path.relative_to(REPOSITORY_ROOT)
        if private_email_pattern.search(content):
            errors.append(f"教學模板包含非 example.com Email：{relative_path}")
        # 長函式名稱也可能符合 ID 字元格式；只有不是函式呼叫或宣告的
        # 長字串才視為可能的私人 Google 資源 ID。
        suspicious_google_ids = [
            match
            for match in long_google_id_pattern.finditer(content)
            if content[match.end():].lstrip()[:1] != "("
        ]
        if suspicious_google_ids:
            errors.append(f"教學模板疑似包含私人 Google 資源 ID：{relative_path}")
        for fragment in sensitive_fragments:
            if fragment.lower() in content.lower():
                errors.append(f"教學模板包含敏感片段：{relative_path}：{fragment}")

    return errors


def validate_template_materializer() -> list[str]:
    """確認模板複製工具保留安全拒絕與不覆寫規則。"""
    path = TEACHING_ROOT / "scripts" / "materialize_template.py"
    if not path.is_file():
        return ["缺少教學模板複製工具"]

    content = path.read_text(encoding="utf-8")
    try:
        compile(content, str(path), "exec")
    except SyntaxError as error:
        return [f"教學模板複製工具語法錯誤：{error}"]

    required_fragments = [
        "status\") != \"validated\"",
        "學生專案不得建立在 Learn-GAS 技能儲存庫內",
        "目的檔案已有不同內容，不會覆寫",
        "filecmp.cmp",
        "inspect_clasp_bootstrap",
        "--replace-clasp-bootstrap",
        "build_upgrade_plan",
        "upgrade_materialized_template",
        "--upgrade-from",
        "第二階段第 2 至第 8 課不得直接複製",
        "第二階段只能依序升級相鄰課次",
        "學生專案的前課檔案已有不同內容，不會升級",
        "學生專案含有前課快照以外的受控檔案，不會升級",
        "累積模板不得移除前課檔案",
        "files_match_snapshot",
        "src 已有非 clasp 初始檔案，不會取代",
        "Code.gs 不是可辨識的 clasp 空白初始函式",
        "appsscript.json 已有非初始設定，不會取代",
        "shutil.copy2",
        "--dry-run",
        "--destination 必須使用絕對路徑",
        "[成功] 模板處理完成",
        "[成功] 模板升級完成",
        "[失敗] 無法建立教學模板",
    ]
    return [
        f"教學模板複製工具缺少安全規則：{fragment}"
        for fragment in required_fragments
        if fragment not in content
    ]


def validate_template_materializer_behavior() -> list[str]:
    """執行模板工具的正常、錯誤與重複使用回歸測試。"""
    test_path = TEACHING_ROOT / "scripts" / "test_materialize_template.py"
    if not test_path.is_file():
        return ["缺少教學模板複製工具回歸測試"]

    result = subprocess.run(
        [sys.executable, str(test_path)],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return []

    details = (result.stdout + result.stderr).strip()
    return [f"教學模板複製工具回歸測試失敗：{details}"]


def validate_course_progress_tool() -> list[str]:
    """確認全課程進度工具支援初次選階段、第二階段鎖定與安全更新。"""
    path = TEACHING_ROOT / "scripts" / "update_course_progress.py"
    test_path = TEACHING_ROOT / "scripts" / "test_update_course_progress.py"
    if not path.is_file() or not test_path.is_file():
        return ["缺少全課程進度工具或回歸測試"]

    content = path.read_text(encoding="utf-8")
    try:
        compile(content, str(path), "exec")
    except SyntaxError as error:
        return [f"課程進度工具語法錯誤：{error}"]

    errors = [
        f"課程進度工具缺少安全規則：{fragment}"
        for fragment in [
            "ALLOWED_STATES",
            "ALLOWED_TEMPLATE_STATES",
            "PHASE_LABELS",
            "initialize_progress",
            "select_phase",
            "--select-phase",
            "import_legacy_phase_one_progress",
            "--import-legacy-progress",
            "五個生活應用入門案例均已完成",
            "舊版進度檔沒有可辨識的第一階段完成證據",
            "已有進行中的統一進度",
            "舊版進度來源不得是目前的統一進度檔",
            "第二階段進行中，只能中斷後從最早未完成處恢復",
            "完成第 8 課前不能切換階段",
            "第二階段必須先完成第",
            "疑似包含私人資料或秘密，不會寫入",
            "--destination 必須使用絕對路徑",
            "課程工作區不得位於 Learn-GAS 技能儲存庫內",
            "課程進度路徑超出課程工作區",
            "找不到 docs/course-progress.md",
            "[成功] 課程進度",
            "[失敗] 無法更新課程進度",
        ]
        if fragment not in content
    ]
    result = subprocess.run(
        [sys.executable, str(test_path)],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        details = (result.stdout + result.stderr).strip()
        errors.append(f"課程進度工具回歸測試失敗：{details}")
    return errors


def validate_first_lesson() -> list[str]:
    """確認第一課具備設定、正常、錯誤與重複測試。"""
    path = TEACHING_ROOT / "examples" / "first-sheet-lesson" / "Code.gs"
    content = path.read_text(encoding="utf-8")
    required_fragments = [
        "function setupLessonSheet()",
        "function checkLesson01Settings()",
        "function testLesson01Normal()",
        "function testLesson01Error()",
        "function testLesson01Repeat()",
        "活動報名資料",
        "setValues",
        "[開始]",
        "[設定]",
        "[成功]",
        "[失敗]",
        "[略過]",
        "//",
    ]
    return [
        f"第一課程式缺少必要內容：{fragment}"
        for fragment in required_fragments
        if fragment not in content
    ]


def validate_basic_project_template() -> list[str]:
    """確認最小專案範本符合設定、中文紀錄檔(Log)與強制測試標準。"""
    template_root = PROJECT_ROOT / "examples" / "basic-project"
    checks = {
        template_root / "README.md": [
            "Script Properties",
            "runProjectTests",
            "正常、錯誤與重複執行測試",
            "Triggers.gs",
            "執行記錄",
        ],
        template_root / ".claspignore": [
            "!src/appsscript.json",
            "!src/**/*.gs",
            "!src/**/*.html",
        ],
        template_root / "src" / "00_Log.gs": [
            "function writeProjectLog_",
            "console.error",
            "console.warn",
            "console.info",
            "/**",
        ],
        template_root / "src" / "01_Config.gs": [
            "PROJECT_PROPERTY_SPECS",
            "function checkProjectSettings()",
            "function validateProjectSettings_",
            "PropertiesService.getScriptProperties()",
            "'設定'",
            "/**",
        ],
        template_root / "src" / "Main.gs": [
            "function healthCheck()",
            "checkProjectSettings()",
            "writeProjectLog_('開始'",
            "writeProjectLog_('成功'",
            "//",
        ],
        template_root / "src" / "Tests.gs": [
            "function runProjectTests()",
            "function testProjectNormal()",
            "function testProjectError()",
            "function testProjectRepeat()",
            "throw error",
            "/**",
        ],
    }
    errors: list[str] = []
    for path, fragments in checks.items():
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(
                    f"基本專案範本缺少必要內容："
                    f"{path.relative_to(REPOSITORY_ROOT)}：{fragment}"
                )

    old_code = template_root / "src" / "Code.gs"
    if old_code.exists():
        errors.append("基本專案範本仍保留舊的 Code.gs")

    return errors


def validate_development_environment() -> list[str]:
    """確認專案開發技能保留跨平台與先檢查再安裝原則。"""
    path = PROJECT_ROOT / "references" / "development-environment.md"
    content = path.read_text(encoding="utf-8")
    required_fragments = [
        "Agent-first",
        "共用首次使用關卡",
        "兩層環境關卡",
        "核心原則：先檢查，再決定是否安裝",
        "GoogleAppsScript/<專案名稱>",
        "osascript -e 'POSIX path of (path to documents folder)'",
        "[Environment]::GetFolderPath('MyDocuments')",
        "activity-registration",
        "skills/google-apps-script-*",
        "WSL 解析方式",
        "環境步驟三：安裝 Git 並建立安全基線",
        "git diff --cached --check",
        "本機 commit 是版本紀錄，不是異機備份",
        "npm exec -- clasp --version",
        "npm.cmd exec -- clasp --version",
        "`show-authorized-user` 與 `list-scripts`",
        "不再詢問「要使用哪個 Google 帳號」",
        "未執行 pull、push 或部署",
    ]
    return [
        f"開發環境文件缺少必要內容：{fragment}"
        for fragment in required_fragments
        if fragment not in content
    ]


def validate_teaching_course() -> list[str]:
    """確認固定路線、教學協定與八份教案完整。"""
    teaching_skill = (TEACHING_ROOT / "SKILL.md").read_text(encoding="utf-8")
    teaching_workflow = (
        TEACHING_ROOT / "references" / "teaching-workflow.md"
    ).read_text(encoding="utf-8")
    learning_path = (
        TEACHING_ROOT / "references" / "learning-path.md"
    ).read_text(encoding="utf-8")
    protocol = (
        TEACHING_ROOT / "references" / "course-execution-protocol.md"
    ).read_text(encoding="utf-8")
    beginner_path = (
        TEACHING_ROOT / "references" / "beginner-application-path.md"
    ).read_text(encoding="utf-8")
    examples = (
        TEACHING_ROOT / "references" / "teaching-examples.md"
    ).read_text(encoding="utf-8")
    lesson08_agent_tool = (
        TEACHING_ROOT
        / "scripts"
        / "run_lesson08_webhook_tests.py"
    ).read_text(encoding="utf-8")
    ui_terms = (
        TEACHING_ROOT / "references" / "apps-script-ui-zh-tw.md"
    ).read_text(encoding="utf-8")
    course_progress_template = (
        TEACHING_ROOT
        / "examples"
        / "course-progress-template.md"
    ).read_text(encoding="utf-8")
    templates_readme = (TEACHING_ROOT / "templates" / "README.md").read_text(
        encoding="utf-8"
    )
    activity_templates_readme = (
        TEACHING_ROOT / "templates" / "activity-registration" / "README.md"
    ).read_text(encoding="utf-8")
    errors: list[str] = []

    intro_contract_checks = {
        "教學技能入口": (
            teaching_skill,
            [
                "每個第一階段案例與第二階段課次都有「課程簡介關卡」",
                "遠端建立摘要、Script Properties 填寫、`clasp push` 確認",
                "不得因資源已建立、程式已推送或學員已回覆「設定完成」而省略",
                "第一階段與第二階段在每次推送到Apps Script(clasp push)成功後",
                "同一則下一步指示開頭加入「精簡課程回顧」",
                "不得只剩操作步驟",
            ],
        ),
        "教學工作流程": (
            teaching_workflow,
            [
                "### 0. 課程簡介關卡",
                "任何遠端建立摘要、Script Properties 填寫、`clasp push` 確認",
                "Google 資源 ID 要再用「門牌號碼」比喻並說明網址區段",
                "第一次交付學生操作時都要在同一則訊息先提供「精簡課程回顧」",
                "不得只剩設定、重新整理、選單、授權或部署步驟",
            ],
        ),
        "教學執行協定": (
            protocol,
            [
                "### A. 課程簡介關卡",
                "即使遠端資源已建立、程式已推送",
                "簡介不是額外確認點",
                "第一次交付學生操作仍要在同一則訊息先提供「精簡課程回顧」",
                "不得只剩操作步驟",
            ],
        ),
        "生活應用入門課程": (
            beginner_path,
            [
                "Agent 必須先完成該案例的「課前簡介」",
                "Agent／學生分工、所需資源與設定，以及驗收方法",
                "第一次交付學生操作要在同一則訊息先提供「精簡課程回顧」",
                "不得只剩操作步驟",
            ],
        ),
        "教學案例共同規格": (
            examples,
            [
                "Agent 先完成「課程簡介關卡」",
                "資源／設定來源、影響與驗收",
                "第一次學生操作指示的同一則訊息先提供「精簡課程回顧」",
                "不得只剩操作步驟",
            ],
        ),
    }
    for label, (content, fragments) in intro_contract_checks.items():
        for fragment in fragments:
            if fragment not in content:
                errors.append(f"{label}缺少課程簡介關卡：{fragment}")

    lesson08_agent_tool_checks = {
        "教學技能入口": (
            teaching_skill,
            [
                "網頁應用程式(Web App)部署不等同可執行 API 部署",
                "不得預設使用 `clasp run`",
                "scripts/run_lesson08_webhook_tests.py",
            ],
        ),
        "教學執行協定": (
            protocol,
            [
                "使用 `scripts/run_lesson08_webhook_tests.py` 的隱藏輸入",
                "不得預設使用 `clasp run`",
                "把測試函式交給學生執行",
            ],
        ),
        "第 8 課 Agent 測試工具": (
            lesson08_agent_tool,
            [
                "getpass",
                "LESSON08-DEMO-REQUEST-001",
                "INVALID_JSON",
                "INVALID_TOKEN",
                "DUPLICATE",
                "不含網址、密語或原始本文",
            ],
        ),
    }
    for label, (content, fragments) in lesson08_agent_tool_checks.items():
        for fragment in fragments:
            if fragment not in content:
                errors.append(f"{label}缺少安全遠端測試規則：{fragment}")

    expected_beginner_intro_count = 5
    actual_beginner_intro_count = beginner_path.count(
        "### 課前簡介（Agent 必須先說）"
    )
    if actual_beginner_intro_count != expected_beginner_intro_count:
        errors.append(
            "生活應用入門課程的課前簡介數量不正確："
            f"預期 {expected_beginner_intro_count}，實際 {actual_beginner_intro_count}"
        )

    phase_two_menu_checks = {
        "教學技能入口": (
            teaching_skill,
            [
                "從第 1 課起就由共用 `onOpen(e)` 建立「活動報名工具」選單",
                "`onOpen(e)` 只建立 UI，不讀寫業務資料",
                "安裝型觸發器仍須另行確認建立、真實執行與刪除",
                "第二階段要提供已核對的試算表連結",
                "從 Sheets 選單、觸發器、表單、Web App 或 Webhook 啟動時",
                "不得要求學生插入圖片、繪圖或指派指令碼",
            ],
        ),
        "教學工作流程": (
            teaching_workflow,
            [
                "從第 1 課開始就以共用 `onOpen(e)` 建立「活動報名工具」選單",
                "`onOpen(e)` 只負責建立選單，不讀寫業務資料",
                "安裝、刪除與真實背景執行仍必須各自取得確認",
                "從 Sheets 自訂選單、觸發器、表單或 Web App 啟動時",
                "不得要求學生插入圖片、繪圖或指派指令碼",
            ],
        ),
        "學習路徑": (
            learning_path,
            [
                "從第 1 課起由共用 `onOpen(e)` 建立 Sheets 的「活動報名工具」",
                "到 Apps Script 左側「執行項目」查看本次結果",
            ],
        ),
        "教學執行協定": (
            protocol,
            [
                "Sheets `活動報名工具`",
                "00_Menu.gs",
                "共用 `onOpen(e)` 與累積選單",
                "開啟或回到試算表 → 重新整理 → 選擇「活動報名工具」→ 選擇當課項目",
                "`onOpen(e)` 只建立選單，不執行業務寫入",
                "不能用這次 `onOpen(e)` 的確認代替",
            ],
        ),
        "繁體中文 UI 用語": (
            ui_terms,
            [
                "第二階段從第 1 課起以 Sheets 的「活動報名工具」作為共通入口",
                "從選單啟動的執行到左側「執行項目」查看",
            ],
        ),
    }
    for label, (content, fragments) in phase_two_menu_checks.items():
        for fragment in fragments:
            if fragment not in content:
                errors.append(f"{label}缺少第二階段 Sheets 選單原則：{fragment}")

    obsolete_phase_two_editor_rules = {
        "教學技能入口": (
            teaching_skill,
            "第 1 課第一次執行前，先說明",
        ),
        "繁體中文 UI 用語": (
            ui_terms,
            "所有教學函式都使用固定操作句型",
        ),
        "學習路徑": (
            learning_path,
            "使用者能在 Apps Script UI 親自選擇並執行必要的初始化動作",
        ),
    }
    for label, (content, obsolete_fragment) in obsolete_phase_two_editor_rules.items():
        if obsolete_fragment in content:
            errors.append(
                f"{label}仍把 Apps Script 函式選單當成第二階段正常入口："
                f"{obsolete_fragment}"
            )

    template_policy_checks = {
        "教學技能入口": (
            teaching_skill,
            [
                "templates/catalog.json",
                "scripts/materialize_template.py",
                "scripts/update_course_progress.py",
                "不得依教案重新生成同一套業務程式",
                "第一階段五個案例已有完整 `validated` 模板",
                "第二階段第 2 至第 8 課必須以 `--upgrade-from`",
                "整項檢查通過前不得寫入",
                "`--import-legacy-progress` 受控匯入",
                "不得靠模板狀態、模糊敘述或記憶猜測完成狀態",
            ],
        ),
        "教學工作流程": (
            teaching_workflow,
            [
                "已有 `validated` 模板時",
                "不得根據教案重新寫一份相似程式",
                "模板狀態是 `pending` 時",
                "開始前自由選擇",
                "沒有先修限制",
                "第一階段五個案例彼此獨立",
                "讓學員自由選擇",
                "不自動指定下一個",
                "第二階段八課是同一個累積專案",
                "完成第 8 課前拒絕切換階段或跳過未完成課次",
                "每課完成後直接開始下一課",
                "GoogleAppsScript/learn-gas-course",
                "scripts/update_course_progress.py",
                "從相鄰前課快照受控升級",
                "已完整升級的相同命令可安全重跑並略過",
                "`--import-legacy-progress` 受控匯入第一階段",
                "不得因模板是 `validated`",
            ],
        ),
        "學習路徑": (
            learning_path,
            [
                "第 2 至第 8 課必須使用 `scripts/materialize_template.py --upgrade-from`",
                "只從相鄰前課快照受控升級",
                "不得直接複製後面課次、跳課、手動合併或重新撰寫",
                "完整累積的 `.claspignore` 與 `src/`",
                "一般學習者不得使用 `pending` 草稿",
                "學員可在開始前直接選擇任一階段",
                "案例彼此不依賴",
                "依興趣自由選擇任一未完成案例",
                "每課沿用前課專案成果",
                "最早未完成",
                "固定的第 1 至第 8 課",
                "不在課間切換階段或詢問是否進入下一課",
                "scripts/update_course_progress.py",
                "scripts/update_course_progress.py --import-legacy-progress",
                "不保存舊檔路徑",
            ],
        ),
        "教學執行協定": (
            protocol,
            [
                "templates/catalog.json",
                "scripts/materialize_template.py",
                "scripts/update_course_progress.py",
                "一般學習流程必須停止並回報模板尚未發布",
                "templates/activity-registration/lesson-XX",
                "完成第 8 課前不得切換階段或跳過未完成課次",
                "Agent 直接開始下一課",
                "只從相鄰前課快照受控升級",
                "任何寫入前證明目前專案完整符合前課快照",
                "`--import-legacy-progress` 受控匯入",
                "不得把 `validated` 模板狀態當作學員完成證據",
            ],
        ),
        "生活應用入門課程": (
            beginner_path,
            [
                "../templates/beginner/",
                "../scripts/materialize_template.py",
                "../scripts/update_course_progress.py --select-phase 1",
                "不得再依本文件重新撰寫案例程式",
                "第一階段五個案例各自獨立",
                "讓學員自由選擇任一未完成案例",
                "不自動指定下一個",
            ],
        ),
        "教學模板說明": (
            templates_readme,
            [
                "--upgrade-from activity-registration/lesson-01",
                "任何寫入前停止",
                "不會猜測合併、刪除學員內容或跳課",
                "第 1 至第 8 課連續升級",
            ],
        ),
        "第二階段模板說明": (
            activity_templates_readme,
            [
                "一般學習流程一律從第 1 課快照開始",
                "scripts/materialize_template.py --upgrade-from",
                "從相鄰前課依序升級",
                "不會覆寫、刪除、猜測合併或重新生成程式",
            ],
        ),
    }
    for label, (content, fragments) in template_policy_checks.items():
        for fragment in fragments:
            if fragment not in content:
                errors.append(f"{label}缺少模板優先規則：{fragment}")

    obsolete_switching_rules = {
        "教學技能入口": (teaching_skill, "學員日後可切換"),
        "教學工作流程": (teaching_workflow, "切換階段只更新目前選擇"),
        "學習路徑": (learning_path, "也可日後切換"),
        "教學執行協定": (protocol, "學員可以維持或切換階段"),
        "生活應用入門課程": (beginner_path, "學員可以日後切換"),
        "課程進度範本": (course_progress_template, "自由選擇或切換階段"),
    }
    for label, (content, obsolete_fragment) in obsolete_switching_rules.items():
        if obsolete_fragment in content:
            errors.append(
                f"{label}仍允許第二階段中途切換：{obsolete_fragment}"
            )

    obsolete_phase_one_ordering = {
        "教學工作流程": (teaching_workflow, "依序從最早未完成案例開始"),
        "生活應用入門課程": (beginner_path, "從最早未完成處開始"),
    }
    for label, (content, obsolete_fragment) in obsolete_phase_one_ordering.items():
        if obsolete_fragment in content:
            errors.append(
                f"{label}仍強制第一階段依序完成：{obsolete_fragment}"
            )

    for fragment in [
        "第一階段與第二階段沒有先修限制",
        "開始前自由選擇",
        "第一階段五個案例彼此獨立",
        "可自由選擇任一未完成案例",
        "第二階段八課共用同一個累積專案",
        "固定依序完成第 1 至第 8 課",
        "完成第 8 課前不得切換階段",
        "第一階段",
        "第二階段",
        "`pending`",
        "`validated`",
        "第一次選擇階段時自動建立",
        "已存在時絕不覆寫",
        "不得記錄 Script ID",
    ]:
        if fragment not in course_progress_template:
            errors.append(f"課程進度範本缺少模板沉澱規則：{fragment}")

    for fragment in [
        "第一版教學分成兩層",
        "全技能共用入口：開發環境關卡",
        "生活應用入門課程",
        "指定資料夾檔案上傳紀錄器",
        "個人化批次郵件寄送器",
        "整合專案課程",
        "第 2 課：Script Properties 與設定檢查",
        "第 6 課：使用 Gmail 寄送報名通知",
        "正式收件人來自該筆報名資料的 Email",
        "不建立 `TEST_EMAIL`",
        "第 8 課：簡單 Web App／Webhook",
    ]:
        if fragment not in learning_path:
            errors.append(f"學習路徑缺少必要內容：{fragment}")

    for fragment in [
        "家庭支出記錄表",
        "批次信封版面產生器",
        "Google Docs",
        "Google Sheets 只擔任",
        "直式",
        "橫式",
        "generateEnvelopeDocuments",
        "五筆政府官網公開的機關名稱與較長地址",
        "第 2 至 6 列",
        "中華郵政國內直式信封書寫位置",
        "中華郵政國內橫式信封書寫位置",
        "寄件資料在左上",
        "貼郵票處在右上",
        "收件資料在中央偏右",
        "Google Docs 沒有原生中文直書功能",
        "不在每個字後插入手動換行",
        "收件人與收件地址字體使用 28",
        "寄件地址及「貼郵票處」使用 24",
        "明確取消粗體與斜體",
        "必須放在同一個表格",
        "表格不得合併儲存格",
        "使用不可斷行連字號",
        "避免位置重排或被拆成兩行",
        "每位收件人只佔一頁",
        "不超過單頁安全高度",
        "郵遞區號沒有被拆到下一頁",
        "視為定稿",
        "不得回頭改動直式已驗收基線",
        "一個 3×3 無框線表格",
        "橫式收件地址與姓名字體至少使用 28",
        "寄件地址與姓名使用 24",
        "不得為了塞進版面而縮小已確認字體",
        "字體必須套用整個儲存格文字",
        "不得只修改第一個段落",
        "testEnvelopeLandscape",
        "恢復使用者原本的方向設定",
        "逐字確認寄件資料實際為 24",
        "只檢查原始碼中的數字不算字體驗收通過",
        "目視確認文字方向",
        "教師隨機測驗與成績報表",
        "100 題題庫",
        "隨機抽取 20 題",
        "全班使用同一份",
        "姓名",
        "學號",
        "updateScoreReport",
        "第一階段不建立提交觸發器",
        "第一份表單必須從這個日常入口建立",
        "不先執行`testQuizNormal`",
        "Form ID 位於`/forms/d/`與`/edit`之間",
        "任何工程測試都不得在`QUIZ_FORM_ID`未設定時搶先建立第一份表單",
        "Agent 的`testQuizNormal`只能在`QUIZ_FORM_ID`設定完成後驗收",
        "一次取用並驗收一個案例",
        "不要一次建立或推送全部案例",
    ]:
        if fragment not in beginner_path:
            errors.append(f"生活應用入門課程缺少必要內容：{fragment}")

    if "目前不先寫 Code" in beginner_path:
        errors.append("生活應用入門課程仍保留已過時的禁止實作文字")

    for fragment in [
        "`郵件工具`選擇`批次寄送郵件`",
        "不需要建立圖片、繪圖或指派指令碼",
        "重複選擇寄送功能",
    ]:
        if fragment not in beginner_path:
            errors.append(f"案例五缺少自訂選單操作規格：{fragment}")

    if "將工作表中的圖片或繪圖指定給該函式" in beginner_path:
        errors.append("案例五仍要求學生手動指派圖片或繪圖")

    for fragment in [
        "每課固定對話循環",
        "docs/course-progress.md",
        "awaiting_push_confirmation",
        "`clasp push` 確認",
        "正常測試",
        "錯誤測試",
        "重複執行測試",
        "google-apps-script-debugging",
        "已核對的試算表連結",
        "選擇「活動報名工具」→ 選擇當課項目",
        "等左側「檔案」重新載入",
        "不得停在重新整理後要求使用者先回覆「已重整」",
        "合併操作使用固定句型",
        "學生的正常使用驗收必須走該入口",
        "`checkQuizBank` 通過 → Sheets 的 `測驗工具`建立第一份測驗",
    ]:
        if fragment not in protocol:
            errors.append(f"教學執行協定缺少必要內容：{fragment}")

    for fragment in [
        "活動報名與通知系統",
        "Script Properties 共同規格",
        "中文紀錄檔(Log)共同規格",
        "每課測試規格",
        "取得使用者確認後，Agent 才執行 `clasp push`",
        "templates/catalog.json",
        "scripts/materialize_template.py",
    ]:
        if fragment not in examples:
            errors.append(f"教學案例缺少必要內容：{fragment}")

    for fragment in [
        "請選取要執行的函式",
        "編輯指令碼屬性",
        "新增指令碼屬性",
        "儲存指令碼屬性",
        "選擇您要執行的功能",
        "選取活動來源",
        "選取分鐘間隔",
        "刪除觸發條件",
        "要永久刪除嗎？",
        "永久刪除",
        "執行項目",
        "新增部署作業",
        "網頁應用程式",
        "誰可以存取",
        "所有人",
        "複製網頁應用程式網址",
        "建立新版本",
        "封存部署作業",
        "只有必須直接從編輯器執行函式時",
        "需要直接執行函式時使用固定句型",
        "活動報名工具",
        "這個應用程式未經 Google 驗證",
        "前往「<教材名稱>」（不安全）",
    ]:
        if fragment not in ui_terms:
            errors.append(f"繁體中文介面用語缺少必要內容：{fragment}")

    lesson_specs = {
        "lesson-01-sheets.md": [
            "00_Log.gs",
            "01_Sheets.gs",
            "testLesson01Normal",
            "testLesson01Repeat",
            "初始化活動報名資料",
            "`onOpen(e)`",
            "本課不需要 Script Properties",
        ],
        "lesson-02-properties.md": [
            "SPREADSHEET_ID",
            "MissingSetting",
            "WrongSpreadsheet",
            "spreadsheets.currentonly",
            "不得使用需要完整 `spreadsheets` OAuth scope",
            "檢查系統設定",
            "`SPREADSHEET_ID`來自第 1 課由 Agent 建立",
        ],
        "lesson-03-forms.md": [
            "FORM_ID",
            "InvalidEmail",
            "The form currently has no response destination.",
            "只把這個已知狀態視為尚未連結",
            "其他錯誤仍原樣拋出",
            "不得只用「回傳空字串」的假實作測試",
            "`Form.getItems()` 回傳通用 `Item`",
            "已直接回傳具體欄位",
            "新增方法回傳的物件不提供 `asTextItem()`",
            "唯一一個、未命名、非必填、無說明、尚無回覆的文字欄位",
            "取得本課單獨的遠端建立確認",
            "活動報名表單",
            "不得要求學生建立空白表單",
            "建立表單與之後的推送到Apps Script(clasp push)是兩個獨立授權點",
            "設定活動報名表單",
            "`FORM_ID`則來自 Agent",
        ],
        "lesson-04-batch.md": [
            "runLesson04Tests",
            "零筆",
            "一筆",
            "多筆",
            "狀態為「資料有誤」",
            "狀態為「已完成」",
            "不得讀寫或覆蓋學生剛填寫的表單回覆分頁",
            "不得把整個 `.gs` 檔案清單寫死",
            "批次處理待處理報名",
            "本課沿用`SPREADSHEET_ID`，不新增資源",
        ],
        "lesson-05-docs-drive.md": [
            "DOC_TEMPLATE_ID",
            "OUTPUT_FOLDER_ID",
            "建立報名確認文件",
            "取得本課單獨的遠端建立確認",
            "活動報名確認範本（教學）",
            "活動報名確認文件（教學輸出）",
            "不得要求學生建立空白文件",
            "只有唯讀權限或缺少建立權限",
            "不得因工具權限不足就把資源建立工作丟回學生",
            "建立 Docs／Drive 資源與之後的推送到Apps Script(clasp push)是兩個",
            "`DriveApp` 以指定 ID 取得範本、資料夾並複製文件需要 `drive` scope",
            "`DOC_TEMPLATE_ID`來自 Agent",
        ],
        "lesson-06-gmail.md": [
            "不建立 `TEST_EMAIL`",
            "confirmLesson06RegistrationEmailSend",
            "confirmLesson06UnsentRecovery",
            "寄送中",
            "郵件已寄出",
            "寄送報名確認郵件",
            "通知編號",
            "確認對話框",
            "MailApp.sendEmail",
            "`script.send_mail`",
            "`userinfo.email`",
            "收件人來自該筆報名資料的 Email",
            "不得改用需要讀信權限的",
        ],
        "lesson-07-triggers.md": [
            "onRegistrationFormSubmit",
            "processPendingRegistrationsByTimer",
            "不建立 `TEST_EMAIL`",
            "被處理報名資料的 Email",
            "runLesson07ManualTests",
            "checkLesson07Triggers",
            "觸發條件",
            "檢查觸發器狀態",
            "不得放進 Sheets 選單",
            "本課不新增學員必填的指令碼屬性",
            "不得再次要求",
            "`PROCESSING_BATCH_SIZE`",
            "啟用表單提交自動處理",
            "啟用短暫時間處理",
            "停止第 7 課自動化",
            "自動到期",
            "整次啟用最多嘗試一筆",
            "時間處理已自動停止=1",
        ],
        "lesson-08-webapp-webhook.md": [
            "doGet(e)",
            "doPost(e)",
            "WEBHOOK_TOKEN",
            "WEB_APP_URL",
            "runLesson08LocalTests",
            "runLesson08RemoteTests",
            "封存",
            "Sheets 選單只提供安全的設定與狀態檢查",
            "本機安全亂數產生 64 個十六進位字元",
            "只供當次課程使用的「臨時教學密語」",
            "因已出現在對話中，只適合本課測試",
            "密碼管理器的密碼產生器",
            "`openssl rand -hex 32`",
            "不得把值回傳給 Agent",
            "只有臨時教學權杖(Token)在私人教學對話顯示一次",
            "SpreadsheetApp.openById()",
            "Web App 執行時綁定檔案特殊方法不可用",
            "完整試算表權限",
            "scripts/run_lesson08_webhook_tests.py",
            "不能預設透過 `clasp run`",
            "不為它另外建立可執行 API 部署",
        ],
    }
    common_fragments = [
        "本課成果",
        "課前簡介（Agent 必須先說）",
        "Agent 實作",
        "Script Properties",
        "推送到Apps Script(clasp push)",
        "使用者 UI 驗收順序",
        "活動報名工具",
        "執行項目",
        "預期紀錄檔(Log)",
        "驗收",
        "使用者檢查點",
    ]
    lessons_root = TEACHING_ROOT / "references" / "lessons"
    for filename, specific_fragments in lesson_specs.items():
        path = lessons_root / filename
        if not path.is_file():
            errors.append(f"缺少逐課教案：{filename}")
            continue
        content = path.read_text(encoding="utf-8")
        for fragment in [*common_fragments, *specific_fragments]:
            if fragment not in content:
                errors.append(f"{filename} 缺少必要內容：{fragment}")

    obsolete_registration_email_rules = {
        "lesson-06-gmail.md": [
            "收件人只能來自 Script Properties 的 `TEST_EMAIL`",
            "sendLesson06TestEmail",
            "寄送教學測試郵件",
            "Gmail.Users.Messages.send",
            "`gmail.send` OAuth 權限",
        ],
        "lesson-07-triggers.md": [
            "收件人只能是 `TEST_EMAIL`",
            "郵件仍只寄到 `TEST_EMAIL`",
            "表單 Email 使用 `example.com` 假地址",
        ],
    }
    for filename, obsolete_fragments in obsolete_registration_email_rules.items():
        content = (lessons_root / filename).read_text(encoding="utf-8")
        for fragment in obsolete_fragments:
            if fragment in content:
                errors.append(f"{filename} 仍保留過時的收件邏輯：{fragment}")

    lesson07 = (lessons_root / "lesson-07-triggers.md").read_text(
        encoding="utf-8"
    )
    protocol = (
        TEACHING_ROOT / "references" / "course-execution-protocol.md"
    ).read_text(encoding="utf-8")
    obsolete_batch_property_rules = [
        "`PROCESSING_BATCH_SIZE=1`",
        "| `PROCESSING_BATCH_SIZE` |",
        "新增或更新\n   `PROCESSING_BATCH_SIZE",
    ]
    for fragment in obsolete_batch_property_rules:
        if fragment in lesson07 or fragment in protocol:
            errors.append(
                "第 7 課仍把程式內建批次上限當成學員必填設定："
                f"{fragment}"
            )

    obsolete_student_trigger_checks = [
        "「觸發條件」目視確認只有一個相符項目",
        "到「執行項目」確認時間觸發器成功",
        "留下表單\n    提交 0、時間驅動 0 的收尾證據",
    ]
    for fragment in obsolete_student_trigger_checks:
        if fragment in lesson07:
            errors.append(
                "第 7 課仍把 Agent 工程證據交給學生反覆驗證："
                f"{fragment}"
            )

    return errors


def validate_project_policy() -> list[str]:
    """確認專案開發技能保留 Git、clasp、安全與分流規則。"""
    checks = {
        PROJECT_ROOT / "references" / "agent-first-project-design.md": [
            "本文件只負責實作前的設計決策",
            "Agent First 設計摘要",
            "初始化、日常操作、工程測試與管理／清理",
            "Google Sheets 能用自訂選單滿足需求時",
            "使用者可理解且需要經常調整的非敏感設定",
            "結果不確定時保留待查狀態",
            "使用者只走一次代表性的真實流程",
            "先核對 Apps Script 的服務、事件、權限與配額",
            "專案品質標準",
            "UI 操作原則",
            "安全與 GitHub",
        ],
        PROJECT_ROOT / "references" / "project-workflow.md": [
            "Agent First 設計摘要",
            "初始化、日常操作、工程測試與管理／清理入口",
            "設定位置與 Agent／使用者分工",
            "建立 Git 安全基線",
            "TypeScript 例外",
            "不得直接把原始 `.ts`",
            "只 stage 本次由 Agent 修改的檔案",
            "GitHub repository、remote 與 `git push`",
            "Agent 預設不操作使用者的 UI",
            "專案品質標準",
            "設定函式與檢查函式",
            "google-apps-script-debugging",
            "第二階段第 2 至第 8 課必須以 `--upgrade-from`",
            "任何修改、缺檔、額外 `src/` 檔案",
            "不得覆寫、刪除、手動合併或重新生成業務程式",
        ],
        PROJECT_ROOT / "references" / "project-mode-workflows.md": [
            "建立實際專案",
            "接管既有 Apps Script",
            "像一個獨立的小工具",
            "附著在某一份 Google Sheets",
            "由 Agent 依需求判斷並提出建議",
            "從 Google 帳號選擇專案",
            "list-scripts",
            "建立本機接管目錄",
            "GoogleAppsScript/<專案名稱>",
            "clone-script",
            "第一次抓取使用 `clone-script`",
            "唯讀盤點",
            "建立安全基線",
            "回復方式",
            "私人教學對話提供可點擊的 Apps Script 編輯器網址",
            "不得另外顯示原始 Script ID",
            "ID 所在的網址區段",
            "完整資源 ID",
        ],
        PROJECT_ROOT / "references" / "project-quality-standard.md": [
            "Script Properties 強制規則",
            "使用者可理解且需要經常調整的非敏感設定",
            "Script Properties 保留給資源 ID、低頻技術設定",
            "若資源由 Agent 建立",
            "不得要求使用者自己找網址或拆出 ID",
            "只有使用者原有或親自建立的資源",
            "唯一教學例外是第二階段第 8 課",
            "`WEBHOOK_TOKEN` 臨時教學密語",
            "不得要求學生回傳",
            "可驗證的繁體中文紀錄檔(Log)",
            "強制測試矩陣",
            "設定檢查",
            "正常案例",
            "錯誤案例",
            "重複執行",
            "零筆、一筆及多筆",
            "遠端測試矩陣尚未完成，不得宣布功能完成",
            "setupProjectTriggers()",
            "checkProjectTriggers()",
            "避免重複建立",
            "觸發條件",
            "執行項目",
            "預設測試形式",
            "runProjectTests()",
            "Vitest",
            "專案文件位置",
            "docs/project-spec.md",
            "docs/test-report.md",
            "Google Sheets 欄寬保護",
            "autoResizeColumns()",
            "setColumnWidth()",
            "日常更新資料時",
            "欄寬保持不變",
            "Google Sheets 控制欄與最後資料列",
            "不得只用這類控制欄或 `getLastRow()`",
            "第一筆資料寫入第 2 列",
            "Google Sheets 自訂選單與 UI 執行環境",
            "自訂選單統一由綁定型 Apps Script 的 `onOpen(e)` 建立",
            "能用自訂選單滿足日常操作入口時",
            "不得把插入圖片、繪圖或指派指令碼轉交使用者",
            "不得直接呼叫 `onOpen()`",
            "不得把 `SpreadsheetApp.getUi()` 當成資料設定流程的一部分",
            "Google Docs 固定版面與文字方向",
            "頁面方向只決定紙張寬高",
            "窄欄自然折行模擬文字方向",
            "不得在每個字後插入手動換行",
            "無框線表格固定資料區",
            "清除不需要的粗體、斜體",
            "將其視為版面基線",
            "不得順便重構或改動已驗收版面",
            "不要把頁首、主要內容與頁尾拆成多個相鄰表格",
            "Google Docs 可能在獨立區塊之間自動分頁",
            "不用合併儲存格製造寬度",
            "合併會改變儲存格索引與欄跨度",
            "不可斷行字元",
            "多行內容的字體樣式要套用整個儲存格文字",
            "對齊與行距則逐段設定",
            "不得只取得第一個子段落",
            "讀回實際 Google Docs 的文字樣式逐字確認",
            "集中定義欄寬、列高與單頁安全高度",
            "每筆資料只佔一頁",
            "目視確認文字方向、位置、分頁及長文字",
        ],
        PROJECT_ROOT / "references" / "ui-operation-policy.md": [
            "Agent 預設不操作使用者的電腦或瀏覽器 UI",
            "正確繁體中文介面名稱",
            "每次只提供一個小步驟",
            "只有使用者明確要求",
            "最終成果判斷",
            "函式名稱、所在檔案",
            "Apps Script 繁體中文介面用語",
            "可點擊的 Apps Script 編輯器網址",
            "不得另外顯示原始 Script ID",
            "上方函式選單",
            "不得省略先選檔案的步驟",
            "這個應用程式未經 Google 驗證",
            "只有按鈕、圖片或繪圖本身是明確需求或教學目標",
            "一般日常入口由 Agent 以 `onOpen(e)` 建立自訂選單",
            "前往『<教材名稱>』（不安全）",
        ],
        PROJECT_ROOT / "references" / "clasp-workflow.md": [
            "`clasp` 3.x 不再轉譯 TypeScript",
            "`rootDir` 指向編譯輸出",
            "clasp list-scripts",
            "clasp clone-script",
            "`clone-script` 用於第一次建立本機連結",
            "作業系統暫存目錄安裝明確固定版本",
            "教學與實際專案",
            "專案品質標準",
            "建立本機 Git commit",
            "取得使用者確認後執行 `clasp push`",
            "重新整理已開啟的 Apps Script 編輯器",
            "等左側「檔案」重新載入",
            "在同一則回覆一次說完",
            "不得停在重新整理後要求使用者多回一次",
            "綁定 Sheets、Docs、Forms 或 Slides",
            "部署、版本與回復流程",
        ],
        PROJECT_ROOT / "references" / "deployment-workflow.md": [
            "新增部署作業",
            "管理部署作業",
            "建立新版本",
            "上一個穩定版本",
            "回復 deployment 不會自動還原",
            "封存部署作業",
            "使用者確認後",
        ],
        PROJECT_ROOT / "references" / "security-and-github.md": [
            "本機 Git 預設規則",
            "Git identity 缺少時不得捏造",
            "遠端操作確認點",
            "唯一教學例外是第二階段第 8 課",
            "`WEBHOOK_TOKEN` 臨時教學密語",
            "學生自行更換的正式值",
        ],
        PROJECT_ROOT / "references" / "basic-application-routing.md": [
            "做 Apps Script 專案",
            "學習 Apps Script",
            "建立新的 Apps Script 專案",
            "接管既有 Apps Script 專案",
            "第一階段：生活應用入門",
            "第二階段：整合專案",
            "活動報名與通知系統",
            "兩個階段沒有先修限制",
            "五個彼此獨立的生活應用，可自由選擇任一案例",
            "不得強制從最小編號開始",
            "八課共用同一專案與前課成果",
            "固定依序完成第 1 至第 8 課",
            "課間不再詢問階段或下一課",
            "中斷後從最早未完成處恢復",
            "google-apps-script-teaching",
        ],
    }
    errors: list[str] = []
    readme = (REPOSITORY_ROOT / "docs" / "apps-script-guide.md").read_text(encoding="utf-8")
    for fragment in [
        "google-apps-script-project-development` 作為共同分流入口",
        "先詢問要做專案或學習",
    ]:
        if fragment not in readme:
            errors.append(f"README 缺少共同分流說明：{fragment}")

    for path, fragments in checks.items():
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(
                    f"專案開發規則缺少必要內容："
                    f"{path.relative_to(REPOSITORY_ROOT)}：{fragment}"
                )
    return errors


def validate_application_route_order() -> list[str]:
    """確認兩層入口、專案分支與教學案例的名稱及編號順序。"""
    path = PROJECT_ROOT / "references" / "basic-application-routing.md"
    content = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if "依序完成五個可獨立使用的生活應用" in content:
        errors.append("免費基礎應用分流仍強制第一階段依序完成")
    expected_groups = [
        [
            "1. 做 Apps Script 專案",
            "2. 學習 Apps Script",
        ],
        [
            "1. 建立新的 Apps Script 專案",
            "2. 接管既有 Apps Script 專案",
        ],
        [
            "## 分支一：建立免費基礎專案",
            "## 分支二：接管既有基礎專案",
            "## 分支三：教學模式",
        ],
        ["第一階段：生活應用入門", "第二階段：整合專案"],
    ]
    for group in expected_groups:
        positions: list[int] = []
        for item in group:
            position = content.find(item)
            if position == -1:
                errors.append(f"免費基礎應用分流缺少選項或分支：{item}")
            else:
                positions.append(position)
        if len(positions) == len(group) and positions != sorted(positions):
            errors.append(f"免費基礎應用分流順序不正確：{'、'.join(group)}")

    for obsolete_item in [
        "1. 建立實際專案",
        "2. 接管既有 Apps Script",
        "3. 進入教學模式",
    ]:
        if f"> {obsolete_item}\n" in content:
            errors.append(f"免費基礎應用分流仍保留舊首頁選項：{obsolete_item}")

    return errors


def validate_removed_vba_migration_mode() -> list[str]:
    """確認已移除的 VBA／既有自動化遷移模式沒有殘留在入口流程。"""
    paths = [
        REPOSITORY_ROOT / "docs" / "apps-script-guide.md",
        PROJECT_ROOT / "SKILL.md",
        PROJECT_ROOT / "agents" / "openai.yaml",
        PROJECT_ROOT / "references" / "basic-application-routing.md",
        PROJECT_ROOT / "references" / "development-environment.md",
        PROJECT_ROOT / "references" / "project-mode-workflows.md",
        PROJECT_ROOT / "references" / "project-workflow.md",
    ]
    forbidden_fragments = [
        "遷移 Excel VBA",
        "VBA／既有自動化",
        "遷移既有自動化",
    ]
    errors: list[str] = []

    for path in paths:
        content = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            if fragment in content:
                errors.append(
                    f"已移除的遷移模式仍有殘留："
                    f"{path.relative_to(REPOSITORY_ROOT)}：{fragment}"
                )

    return errors


def validate_debugging_policy() -> list[str]:
    """確認除錯技能保留完整證據鏈與遠端確認。"""
    path = DEBUGGING_ROOT / "references" / "debugging-workflow.md"
    content = path.read_text(encoding="utf-8")
    required_fragments = [
        "google-apps-script-teaching",
        "google-apps-script-project-development",
        "重述並確認完整業務邏輯",
        "需求邏輯問題",
        "程式實作問題",
        "先重現，再修正",
        "以既有紀錄檔(Log)為第一證據",
        "用紀錄檔(Log)還原實際執行流程",
        "紀錄檔(Log)已足以指出失敗階段時",
        "一次驗證一個假設",
        "Apps Script 編輯器下方的「執行記錄」",
        "觸發器、Web App 與 Webhook",
        "錯誤分類",
        "Script Properties",
        "建立可重現測試",
        "最小修正",
        "診斷紀錄檔(Log)收尾",
        "暫時紀錄檔(Log)",
        "git diff --cached --check",
        "取得使用者確認後才執行 `clasp push`",
        "遠端驗證",
        "完成標準",
        "使用者已確認 Agent 重述的完整業務邏輯",
        "全域客製規則",
    ]
    return [
        f"除錯流程缺少必要內容：{fragment}"
        for fragment in required_fragments
        if fragment not in content
    ]


def validate_docs_layout_policy() -> list[str]:
    """確認 Docs 固定版面技能保留信封驗收學到的核心規則。"""
    workflow = (
        DOCS_LAYOUT_ROOT / "references" / "fixed-layout-workflow.md"
    ).read_text(encoding="utf-8")
    baseline = (
        DOCS_LAYOUT_ROOT / "references" / "envelope-layout-baseline.md"
    ).read_text(encoding="utf-8")
    readme = (REPOSITORY_ROOT / "docs" / "apps-script-guide.md").read_text(encoding="utf-8")
    errors: list[str] = []

    for fragment in [
        "先把參考圖變成驗收條件",
        "一個無框線表格作為一頁的座標骨架",
        "不要先用 `merge()`",
        "集中管理頁面與版面尺寸",
        "setMinimumHeight()` 只保證最小列高",
        "不同方向使用不同排版函式",
        "中文直排使用窄欄自然折行",
        "不要把字串改成「每個字後加 `\\n`」",
        "cell.editAsText()",
        "逐段處理段落屬性",
        "不可斷行連字號",
        "不要為了塞入長文字，直接縮小已確認的字體",
        "一筆一頁與分頁",
        "遠端讀回實際文字樣式",
        "text.getFontSize(index)",
        "使用者目視驗收",
        "常見症狀與修正方向",
        "多行文字仍是 9 號字",
        "developers.google.com/apps-script/reference/document",
    ]:
        if fragment not in workflow:
            errors.append(f"Docs 固定版面流程缺少必要內容：{fragment}")

    for fragment in [
        "每位收件人使用一個主要無框線表格",
        "不可斷行連字號",
        "直式與橫式使用分離的排版函式",
        "直式定稿",
        "[30, 30, 172, 39, 197, 32]",
        "[48, 590, 45]",
        "橫式定稿",
        "3×3 無框線表格",
        "[270, 360, 120]",
        "[120, 290, 70]",
        "寄件資料：24",
        "收件地址、單位與人名：28",
        "多行字體問題的定稿修正",
        "getFontSize(offset)",
        "逐字驗證寄件資料 24、收件資料 28",
    ]:
        if fragment not in baseline:
            errors.append(f"信封排版基線缺少必要內容：{fragment}")

    for fragment in [
        "Google Docs 固定版面」四個清楚責任",
        "google-docs-layout",
        "不是新的首頁模式",
    ]:
        if fragment not in readme:
            errors.append(f"README 缺少 Docs 排版技能說明：{fragment}")

    return errors


def validate_local_markdown_links() -> list[str]:
    """確認 Markdown 指向的本機文件都存在。"""
    errors: list[str] = []
    link_pattern = re.compile(r"\[[^\]]+\]\((?!https?://)([^)#]+\.md)(?:#[^)]+)?\)")
    root_documents = [
        REPOSITORY_ROOT / "docs" / "apps-script-guide.md",
        REPOSITORY_ROOT / "INSTALL.md",
        REPOSITORY_ROOT / "AGENTS.md",
        REPOSITORY_ROOT / "CLAUDE.md",
    ]
    markdown_paths = [*root_documents, *SKILLS_ROOT.rglob("*.md")]
    for path in markdown_paths:
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for target in link_pattern.findall(content):
            resolved = (path.parent / target).resolve()
            if not resolved.is_file():
                errors.append(
                    f"失效文件連結：{path.relative_to(REPOSITORY_ROOT)}"
                    f" -> {target}"
                )
    return errors


def main() -> int:
    """執行全部驗證並回傳適合 CI 使用的結束碼。"""
    errors = [
        *validate_required_files(),
        *validate_public_license(),
        *validate_skill_entrypoints(),
        *validate_installation_contract(),
        *validate_skill_boundaries(),
        *validate_agent_prompts(),
        *validate_web_operation_links(),
        *validate_resource_id_explanations(),
        *validate_teaching_closing_questions(),
        *validate_agent_owned_teaching_tests(),
        *validate_drive_activity_teaching_exception(),
        *validate_high_frequency_teaching_trigger_safety(),
        *validate_learner_facing_terminology(),
        *validate_clasp_push_terminology(),
        *validate_manifest_push_confirmation(),
        *validate_manifest(),
        *validate_sensitive_files(),
        *validate_teaching_templates(),
        *validate_template_materializer(),
        *validate_template_materializer_behavior(),
        *validate_course_progress_tool(),
        *validate_first_lesson(),
        *validate_basic_project_template(),
        *validate_development_environment(),
        *validate_teaching_course(),
        *validate_project_policy(),
        *validate_application_route_order(),
        *validate_removed_vba_migration_mode(),
        *validate_debugging_policy(),
        *validate_docs_layout_policy(),
        *validate_local_markdown_links(),
    ]

    if errors:
        print("技能驗證失敗：")
        for error in errors:
            print(f"- {error}")
        return 1

    print("四個 Google Apps Script 技能驗證通過。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
