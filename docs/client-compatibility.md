# AI 用戶端相容性

本文件記錄 `My Real Second Brain` 的專案規則入口與技能目錄約定。驗證重點是：AI 從通用核心、Toolbox 發行副本或私人實際案例啟動時，是否能先讀到同一份共用維護契約。

這裡的「通過」只代表規則與技能入口可以被發現，不代表 Provider 安裝、登入、遠端資料存取或所有技能流程都已完成驗收。

## 共用規則入口

| 用戶端 | 專案規則入口 | 專案範圍技能位置 |
|---|---|---|
| ChatGPT／Codex | `AGENTS.md` | `.agents/skills/<skill-name>/SKILL.md` |
| Claude Code | `CLAUDE.md`，第一行以 `@AGENTS.md` 匯入共用規則 | `.claude/skills/<skill-name>/SKILL.md` |
| Google Antigravity Desktop | `AGENTS.md` | `.agents/skills/<skill-name>/SKILL.md` |

規則內容只維護在 `AGENTS.md`；`CLAUDE.md` 只負責匯入，避免兩份規則逐漸不同。工作區範本也必須保留相同結構。

官方規格：

- [Codex 的 AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- [Codex Skills](https://developers.openai.com/codex/skills/)
- [Claude Code 的 CLAUDE.md 與 AGENTS.md 匯入](https://code.claude.com/docs/en/memory)
- [Claude Code Skills](https://code.claude.com/docs/en/slash-commands)
- [Antigravity Rules](https://antigravity.google/docs/rules-workflows)
- [Antigravity Skills](https://antigravity.google/docs/skills)

## 2026-08-30 本機驗證結果

| 用戶端與版本 | 驗證方式 | 結果 | 限制 |
|---|---|---|---|
| Codex CLI `0.144.1` | 從通用核心、Toolbox mirror 與 runtime consumer 三種角色啟動，唯讀檢查實際 prompt 輸入 | 三處都載入共用同步契約；技能名稱與描述可見 | 未在這一步執行技能本體或外部 Provider |
| Claude Code `2.1.206` | 從三種角色執行 `/context`，並在 runtime consumer 啟動除錯掃描 | 三處都載入 `CLAUDE.md`，並由它匯入 `AGENTS.md`；兩層 symlink 後仍從 `.claude/skills` 載入 project skills | 模型回覆測試遇到本機 OAuth 到期而未執行；規則與技能掃描本身為零模型費用 |
| Antigravity Desktop `2.11.0` | 把三種角色各自加入為桌面專案，以不使用工具的問題詢問啟動規則與技能清單 | 三處都回答共用 manifest 相對路徑；runtime consumer 另精確列出四個 symlink 共用技能 | 只驗證桌面版規則與技能發現；未執行檔案修改 |
| Antigravity CLI `1.1.22` | 從相同目錄執行 `/skills` 與最小模型提示 | 未載入 workspace 規則或 workspace skills | 目前視為命令列版已知限制；不要用此結果否定已通過的 Antigravity Desktop 驗證 |

## 驗收方式

每次修改規則入口、技能目錄或本機 symlink 後，至少重新檢查：

1. repository 根目錄與 `template/` 都有實體 `AGENTS.md`、`CLAUDE.md`。
2. `CLAUDE.md` 以 `@AGENTS.md` 匯入規則，不另存一份重複規則。
3. 三個用戶端從各自目標目錄啟動後，能指出 `.local/sync-manifest.toml` 的用途；公開安裝環境沒有該檔案時，不應捏造本機路徑。
4. 專案技能入口能列出 manifest 所列的五個自有技能，且每個目錄都含有效的 `SKILL.md`。
5. 驗證過程不得修改知識內容、上傳資料、安裝 Provider 或把私人路徑寫入公開 repository。

Antigravity CLI 更新後應重新測試 workspace rules 與 workspace skills；只有實際通過後，才能移除上表的已知限制。

## Runtime symlink 驗證

私人實際案例不改寫原始技能資料夾，而是讓三個用戶端入口共同指向一個被 Git 忽略的 runtime 技能農場：

1. 共用知識庫技能各自連到 canonical 的 `skills/<name>/`。
2. 案例專用技能各自連回 runtime consumer 原本的技能資料夾。
3. Codex 的實際 prompt 輸入會顯示共用技能來自 canonical、案例技能來自 runtime consumer。
4. Claude Code 啟動掃描能沿 `.claude/skills` symlink 載入 project skills。
5. Antigravity Desktop 的全新專案對話能列出 `book-notes`、`knowledge-source-retrieval`、`socratic-dialogue` 與 `solopreneur-profile`。

這個結果不代表所有作業系統都支援相同的 symlink 行為。公開套件本身仍必須保存完整實體檔案；symlink 只用於維護者或進階使用者自行設定的本機 runtime。
