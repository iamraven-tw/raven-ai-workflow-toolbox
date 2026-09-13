# 本機技能發現

查驗日期：2026-09-13。安裝位置相容性不等於實際用戶端發現。

| 用戶端 | 方法 | 結果 | 未驗證範圍 |
|---|---|---|---|
| Codex CLI 0.154.0-alpha.6.2（Windows x64） | 全新 app-server 的 skills/list，forceReload=true | 七技能皆 enabled=true，官網技能解析錯誤為零 | 當前對話下一回合載入、真實外部流程與第二臺電腦仍需分開驗證 |
| Claude Code | 尚未執行 | 未驗證 | 技能發現與實際流程皆未驗證 |
| Google Antigravity Desktop／CLI | 尚未執行 | 未驗證 | 技能發現、登入與實際流程皆未驗證 |

結構測試確認 manifest 安裝全部七技能，沒有待建立技能。Windows 安裝生命週期與隔離還原測試不等於 Codex 已載入。第一個技能發現驗收用戶端是 Codex；通過後再測其他用戶端。任何本機發現結果都不能代替另一臺電腦驗收。

查核方式依 [OpenAI 的 skills/list 說明](https://learn.chatgpt.com/docs/app-server)。只呼叫本機發現介面，沒有建立模型回合、執行網站維運或改變用戶端設定。
