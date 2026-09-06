# 用戶端相容

## Toolbox 註冊目標

| 用戶端 | 使用者層 | 工作區層 | 官方文件 | 技能發現驗證 |
|---|---|---|---|---|
| Claude Code | `$HOME/.claude/skills` | `<workspace>/.claude/skills` | <https://code.claude.com/docs/en/slash-commands> | 尚未執行 |
| Codex | `$HOME/.agents/skills` | `<workspace>/.agents/skills` | <https://learn.chatgpt.com/docs/build-skills> | 尚未執行 |
| Google Antigravity | `$HOME/.gemini/config/skills` | `<workspace>/.agents/skills` | <https://antigravity.google/docs/skills> | 尚未執行 |

管理器會檢查技能根目錄的結尾是否與註冊 ID 相符，不符就停止，避免寫錯位置。

## 上游宣告支援的被盤點工具

這一份是「會被掃描到的工具」，跟上面「技能安裝到哪裡」是兩件事。

| 工具 | 上游驗證狀態 |
|---|---|
| Claude Code | 上游已在本機實測 |
| Codex | 上游已在本機實測 |
| Google Antigravity | 上游已在本機實測；對話紀錄是二進位資料庫，使用次數無法對應 |
| Cursor | 路徑取自官方文件，尚未在真機驗證 |
| OpenClaw | 路徑取自官方文件，尚未在真機驗證 |
| Hermes Agent | 上游已在本機實測 |

Cursor 的 User Rules 存在應用程式設定而不是檔案，上游會在網站上顯示提示文字而不是硬猜路徑。

## 跨工具共用

`~/.agents/skills` 同時餵 Codex、Cursor 與 OpenClaw；`AGENTS.md` 同時餵 Codex、Cursor 與 Hermes。上游用 realpath 去重，同一個檔案只算一個項目並標「共用於 ×N」。

這也表示：把本套件的六個技能安裝到 `$HOME/.agents/skills` 之後，Codex 與 Cursor 都會看到，不需要重複安裝。
