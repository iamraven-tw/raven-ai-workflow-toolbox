#!/usr/bin/env python3
"""回歸測試五個技能的觸發、責任、交接與寫入邊界。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_skill(name: str) -> str:
    """讀取指定自有技能。"""

    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def frontmatter_description(text: str) -> str:
    """取得技能 frontmatter 的 description。"""

    match = re.search(r'^description:\s*["\'](?P<value>.+)["\']$', text, re.MULTILINE)
    if not match:
        raise AssertionError("技能缺少單行 description")
    return match.group("value")


class SkillContractTests(unittest.TestCase):
    """確認未來修改不會把五個既有技能重新混成同一個流程。"""

    @classmethod
    def setUpClass(cls) -> None:
        """一次載入全部技能與工作區規則。"""

        cls.skills = {
            name: read_skill(name)
            for name in (
                "my-real-second-brain-setup",
                "solopreneur-profile",
                "book-notes",
                "knowledge-source-retrieval",
                "socratic-dialogue",
            )
        }
        cls.template_rules = (ROOT / "template" / "AGENTS.md").read_text(
            encoding="utf-8"
        )

    def test_descriptions_have_distinct_primary_triggers(self) -> None:
        """五個說明應提供可區分的主要觸發詞。"""

        descriptions = {
            name: frontmatter_description(text) for name, text in self.skills.items()
        }
        self.assertIn("安裝、更新、回復、移除", descriptions["my-real-second-brain-setup"])
        self.assertIn("一人公司的長期設定檔", descriptions["solopreneur-profile"])
        self.assertIn("明確要求記錄閱讀內容", descriptions["book-notes"])
        self.assertIn("知識來源檢索與外部索引管理", descriptions["knowledge-source-retrieval"])
        self.assertIn("挑戰假設、比較立場或形成決策", descriptions["socratic-dialogue"])
        self.assertEqual(len(set(descriptions.values())), 5)

    def test_first_run_does_not_block_explicit_task(self) -> None:
        """未設定背景時只能在沒有明確任務的首次使用主動引導。"""

        profile = self.skills["solopreneur-profile"]
        self.assertIn("使用者沒有提出其他明確任務", profile)
        self.assertIn("不要因設定檔未完成而阻擋", profile)
        self.assertIn("一次只問一個主要問題", profile)

    def test_profile_write_requires_preview_and_confirmation(self) -> None:
        """背景資料建立與更新都必須先預覽。"""

        profile = self.skills["solopreneur-profile"]
        self.assertIn("顯示準備新增、修改與保留的內容", profile)
        self.assertIn("取得使用者明確確認後才寫檔", profile)
        self.assertIn("設定檔和最新明確說法衝突時", profile)

    def test_book_notes_are_explicit_and_continue_one_file(self) -> None:
        """一般談書不寫入，同一本書延續既有檔案。"""

        book = self.skills["book-notes"]
        self.assertIn("一般聊天提到書名不自動建立檔案", book)
        self.assertIn("同一本書永遠追加到同一份 Markdown", book)
        self.assertIn("status: reading", book)
        self.assertIn("status` 改為 `finished", book)

    def test_book_notes_separate_user_source_and_ai(self) -> None:
        """閱讀記錄不得混淆使用者、作者與 AI 延伸。"""

        book = self.skills["book-notes"]
        for marker in (
            "使用者直接說出的想法",
            "書中內容整理",
            "使用者心得",
            "討論延伸",
            "待確認",
        ):
            self.assertIn(marker, book)
        self.assertIn("不把 AI 的延伸理解偽裝成書中內容", book)

    def test_retrieval_is_local_first_and_provider_optional(self) -> None:
        """外部 Provider 失效時仍要保留本機回答與限制。"""

        retrieval = self.skills["knowledge-source-retrieval"]
        self.assertIn("先查本機路由索引", retrieval)
        self.assertIn("再定向搜尋已知相關", retrieval)
        self.assertIn("仍可用本地來源完成目前能回答的部分", retrieval)
        self.assertIn("不得將兩者視為不可替換的永久介面", retrieval)
        self.assertIn("只有使用者明確要求加入、上傳或保存來源時", retrieval)
        self.assertIn("social-media-strategy-and-insights.md", retrieval)
        self.assertIn("不能在沒有使用者討論、補充與確認時", retrieval)

    def test_retrieval_uses_rag_only_for_original_text(self) -> None:
        """Wiki 與 Graphify 優先；只有要原文、出處、數字或 Wiki 不足時才查 RAG，且必須標出檔案與段落。"""

        retrieval = self.skills["knowledge-source-retrieval"]
        self.assertIn("Wiki 與 Graphify 優先", retrieval)
        self.assertIn("使用者要原文、原話、出處、精確數字或引用", retrieval)
        self.assertIn("沒有足夠細節回答", retrieval)
        self.assertIn("一律標出檔案與段落標題", retrieval)
        self.assertIn("已由 `query.py` 處理", retrieval)
        self.assertNotIn("notebooklm ask", retrieval)
        adapters = (
            ROOT / "skills/knowledge-source-retrieval/references/provider-adapters.md"
        ).read_text(encoding="utf-8")
        self.assertIn("不要自己在問題前加 `Instruct:` 前綴", adapters)
        self.assertIn("回答一律標出 `source` 與 `section`", adapters)
        self.assertNotIn("notebooklm auth", adapters)

    def test_inbox_flow_copies_and_empties(self) -> None:
        """單一收件匣：複製不搬移原檔、長文進 external 與摘要頁、其他交給既有規則、最後清空。"""

        retrieval = self.skills["knowledge-source-retrieval"]
        self.assertIn("只有一個收件匣：`sources/inbox/`", retrieval)
        self.assertIn("絕不搬移、改名或刪除使用者的原檔", retrieval)
        self.assertIn("PDF 或 6000 字以上的長文", retrieval)
        self.assertIn("三到五行摘要與關鍵詞", retrieval)
        self.assertIn("`wiki_pending`", retrieval)
        self.assertIn("收件匣應該是空的", retrieval)
        self.assertIn("交給 `/book-notes`", retrieval)

    def test_setup_handles_notebooklm_upgrade_without_deleting(self) -> None:
        """升級時告知不再使用 NotebookLM、不刪資料、不強制移除，並由 Agent 完成本地 RAG 設定。"""

        setup = self.skills["my-real-second-brain-setup"]
        self.assertIn("## 從 NotebookLM 版本升級", setup)
        self.assertIn("**不會被刪除**", setup)
        self.assertIn("不強制移除", setup)
        self.assertIn("brew services start ollama", setup)
        self.assertIn("qwen3-embedding:4b", setup)
        self.assertIn("sources/rag/.venv", setup)
        self.assertIn("不需要自己輸入指令", setup)
        self.assertIn("取得同意後才修改", setup)
        self.assertNotIn("Notebook 登入", setup)

    def test_socratic_dialogue_hands_off_without_auto_write(self) -> None:
        """對話先檢索、一次一題，最後仍不等於寫入授權。"""

        dialogue = self.skills["socratic-dialogue"]
        self.assertIn("使用 `/knowledge-source-retrieval`", dialogue)
        self.assertIn("每輪原則上只問一個主要問題", dialogue)
        self.assertIn("對話完成不等於授權寫檔", dialogue)
        self.assertIn("交給 `/solopreneur-profile`", dialogue)

    def test_workspace_rules_are_user_safe(self) -> None:
        """一般使用者工作區只含使用契約，不含維護流程。"""

        rules = self.template_rules
        self.assertIn("已有明確任務時不阻擋工作", rules)
        self.assertIn("一般討論不得自動寫入", rules)
        self.assertIn("Graphify 與本地 RAG 是預設但可替換", rules)
        self.assertIn("絕不搬移或刪除原檔", rules)
        for forbidden in ("git push", "public-candidate", "release snapshot"):
            self.assertNotIn(forbidden, rules.lower())


if __name__ == "__main__":
    unittest.main()
