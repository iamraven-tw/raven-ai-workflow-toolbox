# AI 用戶端相容性

本文件記錄 `My Real Second Brain` 的專案規則入口、技能目錄約定與實機發現結果。驗證重點是：使用者取得公開版本並安裝後，用戶端是否真的能列出 manifest 所列的五個技能。

這裡的「通過」只代表規則與技能入口可以被發現，不代表 Provider 安裝、登入、遠端資料存取或所有技能流程都已完成驗收。

## 共用規則入口

| 用戶端 | 專案規則入口 | 專案範圍技能位置 |
|---|---|---|
| Codex | `AGENTS.md` | `.agents/skills/<skill-name>/SKILL.md` |
| Claude Code | `CLAUDE.md`，第一行以 `@AGENTS.md` 匯入共用規則 | `.claude/skills/<skill-name>/SKILL.md` |
| Google Antigravity Desktop／IDE | `AGENTS.md` | `.agents/skills/<skill-name>/SKILL.md` |
| Google Antigravity CLI | 依 CLI 當前規格載入 | `.agents/skills/<skill-name>/SKILL.md` |

規則內容只維護在 `AGENTS.md`；`CLAUDE.md` 只負責匯入，避免兩份規則逐漸不同。工作區範本也必須保留相同結構。

官方規格：

- [Codex 的 AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Codex Skills](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code 的 CLAUDE.md 與 AGENTS.md 匯入](https://code.claude.com/docs/en/memory)
- [Claude Code Skills](https://code.claude.com/docs/en/slash-commands)
- [Antigravity Rules](https://antigravity.google/docs/rules-workflows)
- [Antigravity Skills](https://antigravity.google/docs/skills)
- [Antigravity CLI Plugins 與技能位置](https://www.antigravity.google/docs/cli/plugins/)
- [Antigravity CLI 指令參考](https://www.antigravity.google/docs/cli/reference/)

## 使用者範圍技能位置

| 用戶端 | 使用者範圍位置 | 本候選版登錄名稱 |
|---|---|---|
| Codex | `$HOME/.agents/skills` | `codex_user` |
| Claude Code | `$HOME/.claude/skills` | `claude_user` |
| Antigravity Desktop／IDE | `$HOME/.gemini/config/skills` | `antigravity_desktop_user` |
| Antigravity CLI | `$HOME/.gemini/antigravity-cli/skills` | `antigravity_cli_user` |

Desktop／IDE 與 CLI 是兩個不同的載入面。CLI 未登入、未列出技能或版本較舊，都不能推論 Desktop／IDE 不支援；反方向也一樣。

## 2026-08-31 本機驗證結果

| 用戶端與版本 | 驗證方式 | 結果 | 限制 |
|---|---|---|---|
| Codex CLI `0.144.1` | 在虛構暫存工作區執行不呼叫模型的 `codex debug prompt-input` | **通過**。載入工作區 `AGENTS.md`，並列出五個技能的名稱、說明與 `.agents/skills/` 來源 | 未執行技能內容或 Provider；當時可見 `0.149.0` 更新提示，但本次未升級或宣稱新版相容 |
| Claude Code `2.1.206` | 在相同工作區啟動互動介面但不送出提示，再檢查 debug log | **通過**。記錄顯示 `project: 5`，載入五個 `.claude/skills/` 技能、專案 `CLAUDE.md` 及它匯入的 `AGENTS.md` | 一個使用者範圍外掛的 SessionStart hook 路徑錯誤仍出現，但不影響這五個專案技能載入；未呼叫模型 |
| Antigravity Desktop／IDE `2.5.5`（`com.google.antigravity-ide`） | 只信任虛構暫存工作區，於 Agent 輸入欄鍵入 `/`、讀取動作選單後清除，不送出提示 | **通過**。選單實際列出 `book-notes`、`knowledge-source-retrieval`、`my-real-second-brain-setup`、`socratic-dialogue`、`solopreneur-profile` 與各自說明 | 只驗證 Desktop／IDE 的專案技能發現；未呼叫模型、未修改知識內容。另有 `com.google.antigravity` `2.11.0` 桌面殼層，本次未新增或修改它的專案 |
| Antigravity CLI `1.1.22` | 先檢查 `agy --help`，再從虛構工作區啟動互動介面 | **未完成**。啟動後要求登入與工作區信任，已在登入完成前停止 | 未取得外部登入授權，因此沒有執行 `/skills`；這不是 Desktop／IDE 失敗，也不是 CLI 已不支援的證據 |

上述三個「通過」只證明本機技能發現。`codex debug prompt-input`、Claude debug log 與 Antigravity `/` 選單都沒有驗證外部下載、登入或遠端資料。

## 驗收方式

每次修改規則入口、技能目錄或安裝方式後，至少重新檢查：

1. repository 根目錄與 `template/` 都有實體 `AGENTS.md`、`CLAUDE.md`。
2. `CLAUDE.md` 以 `@AGENTS.md` 匯入規則，不另存一份重複規則。
3. Codex、Claude Code 與 Antigravity Desktop／IDE 從公開候選版或由範本建立的新工作區啟動後，不會捏造維護者路徑、私人專案或同步來源。
4. 三個 Desktop／IDE 用戶端的專案技能入口能列出 manifest 所列的五個自有技能，且每個目錄都含有效的 `SKILL.md`。
5. 驗證過程不得修改知識內容、上傳資料、安裝 Provider 或把私人路徑寫入公開 repository。
6. Antigravity CLI 必須另行執行 `/skills`，不得用 Desktop／IDE 結果代替。

使用者完成 Antigravity CLI 登入後，應重新測試 workspace rules、`.agents/skills/` 與 `/skills`；只有實際列出五個技能，才能把 CLI 標為通過。

## 技能入口限制

公開套件必須保存五個自有技能的完整實體檔案。安裝 Agent 可以依宿主規格，將該次已下載版本的技能複製或連結到使用者核准的位置，但不得連向維護者的其他專案或私人工作區。

技能入口存在不等於安裝已成功；仍須重新啟動或重新載入宿主，確認技能名稱與描述可見。symlink 也不是版本同步機制：更新公開版本時，必須重新執行安裝前檢查、衝突比較與驗證。
