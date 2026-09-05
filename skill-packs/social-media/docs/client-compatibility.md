# 本機技能發現

查驗日期：2026-09-04。

| 用戶端 | 方法 | 結果 | 未驗證範圍 |
|---|---|---|---|
| Codex CLI 0.144.1 | 將候選安裝到虛構暫存工作區的 `.agents/skills/`，執行不呼叫模型的 `codex debug prompt-input` | 通過；實際列出 `social-media-setup` 名稱、完整說明與工作區技能來源 | 未執行技能、未讀平台、未登入、未發布 |
| Claude Code | 未執行 | 未驗證 | 技能發現與實際流程皆未驗證 |
| Google Antigravity Desktop／CLI | 未執行 | 未驗證 | 技能發現、登入與實際流程皆未驗證 |

結構測試另外確認 manifest 只安裝第一技能，六個待建立技能沒有空殼目錄。Codex 發現通過不能代替其他用戶端或另一臺電腦驗收。

## 作業系統憑證庫

用戶端技能發現與作業系統憑證庫是不同驗收層。macOS Security framework 已完成唯讀 backend 偵測與不存在項目查詢；寫入、重開程序後讀取及刪除尚未執行。Windows WinCred 實作只通過語法與虛構 backend 契約測試，尚未在 Windows Credential Manager 實測。任何一項都不能由 Codex 技能發現結果推定通過。
