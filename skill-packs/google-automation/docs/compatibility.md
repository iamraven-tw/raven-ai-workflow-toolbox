# 相容性與驗證狀態

## 狀態定義

- **結構通過：** 路徑、`SKILL.md`、相鄰參考資料與 manifest 能由本機驗證器正確讀取。
- **實際發現通過：** 對應 Agent 用戶端在測試工作區列出或載入該技能。
- **正式支援：** 使用者在另一臺電腦完成全新來源取得、三種 Agent 所需入口、至少一條 Google 實際流程與人工驗收。

目前是可安裝的外部驗收候選版；`officially_supported = []`。

## 官方技能入口

| 用戶端 | 工作區／專案入口 | 使用者入口 | 官方資料 | 本候選版狀態 |
|---|---|---|---|---|
| Codex | `<workspace>/.agents/skills` | `$HOME/.agents/skills` | [Build skills](https://learn.chatgpt.com/docs/build-skills) | Codex CLI 0.144.1 以 `debug prompt-input` 實際列出五個技能，未送出模型請求 |
| Claude Code | `<workspace>/.claude/skills` | `$HOME/.claude/skills` | [Extend Claude with skills](https://code.claude.com/docs/en/slash-commands) | Claude Code 2.1.206 以 `/skills` 實際列出五個技能，未送出模型提示 |
| Google Antigravity | `<workspace>/.agents/skills` | `$HOME/.gemini/config/skills` | [Antigravity Skills](https://antigravity.google/docs/skills) | 官方路徑、安裝內容與 CLI 1.1.22 已檢查；本機未登入，實際發現保留給外部驗收 |

Codex 與 Antigravity 在同一工作區共用 `.agents/skills`，只安裝一次。Toolbox 不使用舊的 `$HOME/.codex/skills`。Antigravity CLI 的全域目錄與 Antigravity IDE 不同，本候選版以 IDE／工作區技能為驗收目標。

## 執行環境

| 項目 | 候選版狀態 | 尚待確認 |
|---|---|---|
| Python 3.11 以上 | 安裝管理器與測試只使用標準函式庫 | 外部電腦實際版本 |
| macOS | 本機開發與生命週期測試目標 | 另一臺電腦乾淨安裝 |
| Windows／Linux | 路徑設計不綁定 macOS，但尚未實機測試 | 複製、檔案權限與三種 Agent 發現 |
| Learn-GAS | 固定 commit、tree、LICENSE 與上游測試可驗證 | 外部來源重新取得 |
| Google 帳號／OAuth／Cloud | 本候選版未登入、未授權、未部署 | 最終 Google 實機驗收 |

## 已完成的本機證據

- macOS 26.5.1 Apple Silicon、Python 3.14.7、Git 2.52.0 的暫存工作區完成兩種工作區入口安裝。
- 固定 Learn-GAS commit、Git tree、LICENSE SHA-256、四技能驗證與 43 項教學工具單元測試通過。
- 實際候選版正常安裝與重跑 `noop` 通過；狀態讀回六個入口雜湊相符。
- 六項生命週期測試涵蓋正常安裝、重跑、錯誤更新命令停止、更新、回復、可復原移除、重新安裝、未知檔案／目錄／symlink、人工修改、錯誤依賴與狀態目錄邊界。
- Codex 與 Claude Code 從各自工作區入口實際發現同一個路由技能及四個 Learn-GAS 技能。
- Antigravity CLI 偵測到未登入後已停止，未啟動登入流程；官方入口與同一份 `.agents/skills` 結構已完成本機檢查。

技能被 Agent 發現，只證明安裝入口有效；不代表 Google 帳號、OAuth、API、Apps Script 或 Cloud Run 已可用。
