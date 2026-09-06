# 本機技能發現

查驗日期：2026-09-04。

| 用戶端 | 方法 | 結果 | 未驗證範圍 |
|---|---|---|---|
| Codex CLI 0.144.1 | 將候選安裝到虛構暫存工作區的 `.agents/skills/`，執行不呼叫模型的 `codex debug prompt-input` | 通過；實際列出 `social-media-setup` 名稱、完整說明與工作區技能來源 | 未執行技能、未讀平台、未登入、未發布 |
| Claude Code | 未執行 | 未驗證 | 技能發現與實際流程皆未驗證 |
| Google Antigravity Desktop／CLI | 未執行 | 未驗證 | 技能發現、登入與實際流程皆未驗證 |

上表是第一技能的既有證據，不延伸至新技能。2026-09-05 的七技能候選以隔離目錄檢查 `social-media-setup`、`social-content-planning`、`social-content-writing`、`social-image-production` 、`social-content-publishing` 、`social-community-management` 與 `social-performance-analysis` 的安裝入口、來源雜湊、更新與回復。七個技能的流程說明均已獲准繼續，但不能以人工流程審查或隔離安裝代表真實 Agent 已發現或正確執行；狀態定義見 [流程確認文件](workflow-review-status.md)。

## 2026-09-06 後續狀態

目前 root Agent 已完整讀取七份技能來源，對十個選定的虛構使用者回合做前向回應及可觀察行為檢查。這是同一 Agent 直接套用來源的虛構對話前測，不是安裝後的真實 Agent 技能發現，也不是獨立模型評估。第 2／3／4／5／6／7 個技能的真實入口發現、獨立對話行為與真實社群搜尋仍未驗收；詳見 [對話前測紀錄](agent-dialogue-preflight-local-verification.md)與[本機候選交付紀錄](local-candidate-handoff.md)。

## 作業系統憑證庫

用戶端技能發現與作業系統憑證庫是不同驗收層。macOS Security framework 已完成唯讀 backend 偵測與不存在項目查詢；寫入、重開程序後讀取及刪除尚未執行。Windows WinCred 實作只通過語法與虛構 backend 契約測試，尚未在 Windows Credential Manager 實測。任何一項都不能由 Codex 技能發現結果推定通過。
