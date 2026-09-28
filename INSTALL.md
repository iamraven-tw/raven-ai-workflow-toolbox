# Raven AI 一人公司工具包｜安裝入口

這份文件提供給協助安裝的 AI Agent。請先問使用者想安裝哪些技能包，再讀取對應套件的安裝說明；不需要一次安裝全部。

如果你無法直接讀取 GitHub 儲存庫，請讓使用者先下載 ZIP 並解壓，再從本機檔案繼續。登入與外部服務授權由使用者本人完成。

| 技能包 | 安裝說明 |
|---|---|
| AI 剪片 | [skill-packs/ai-video/INSTALL.md](skill-packs/ai-video/INSTALL.md) |
| Google 工具自動化 | [skill-packs/google-automation/INSTALL.md](skill-packs/google-automation/INSTALL.md) |
| AI 知識庫 | [skill-packs/ai-knowledge-base/INSTALL.md](skill-packs/ai-knowledge-base/INSTALL.md) |
| 社群媒體管理 | [skill-packs/social-media/INSTALL.md](skill-packs/social-media/INSTALL.md) |
| 官網打造 | [skill-packs/website-building/INSTALL.md](skill-packs/website-building/INSTALL.md) |
| WordPress MCP 工作流 | [skill-packs/wordpress-workflow/INSTALL.md](skill-packs/wordpress-workflow/INSTALL.md) |
| AI Agent 規則與技能盤點 | [skill-packs/agent-inventory/INSTALL.md](skill-packs/agent-inventory/INSTALL.md) |

每個技能包獨立安裝。執行前，依該套件的 `INSTALL.md` 與 `install.manifest.toml` 檢查作業系統、安裝條件、第三方依賴與實際支援範圍；不要從根目錄推定所有功能都已完成實機驗收。

## 第一次安裝後的盤點邀請

Agent 在目標使用範圍完成第一個 Toolbox 技能包的全新安裝，而且技能發現驗證成功後，主動詢問一次：

> 是否要盤點這台電腦上 AI Agent 的全域規則、全域技能、專案規則與專案技能？開始前會先列出偵測到的工具與候選專案，由你選擇掃描範圍。

- 這只是邀請，不代表使用者已授權安裝盤點技能或讀取任何規則內容；不得自動開始掃描。
- 使用者答應時，先依 [`skill-packs/agent-inventory/INSTALL.md`](skill-packs/agent-inventory/INSTALL.md) 檢查六個盤點技能是否已安裝。尚未安裝時，將下載、安裝、技能註冊與來源設定合併成一次完整預覽與確認；安裝完成後才交給 `inventory`，由 `inventory-setup` 顯示工具與候選專案並取得掃描範圍。
- 使用者拒絕或選擇稍後處理時立即停止，不影響已完成的技能包，也不在同一安裝流程中重複詢問。
- `status`、相同版本重跑、修復、更新、回復與移除不屬於第一次安裝，不觸發這項邀請。

## 共通規則

1. 安裝前先唯讀檢查作業系統、硬體、既有工具、目標位置與衝突。
2. 列出即將下載的第三方套件、固定版本、來源、授權、容量、可能費用與登入需求。
3. 將本次所選套件的下載、安裝、技能註冊與必要來源設定放進同一份預覽，一次確認後由 Agent 完成與驗證；不逐步重問。未知同名覆寫、登入、權限變更或新增費用仍須對應授權，不由安裝推定。
4. 不安裝 manifest 標示為 `installable = false` 的套件。
5. 完成後依套件 manifest 驗證技能、依賴、工作區與可見結果；任何必要步驟未通過時不得宣稱安裝成功。
6. 安裝狀態只能保存不含 Token、Cookie、帳號內容與私人素材的必要資訊。

第三方來源與 fork 的選擇方式見 [`docs/dependency-policy.md`](docs/dependency-policy.md)。自行撰寫的公開核心採 [Apache License 2.0](LICENSE)，第三方內容保留各自授權。

## 平台差異

不同作業系統與 AI Agent 的安裝位置可能不同。請以各技能包的安裝說明為準，先檢查使用者目前的環境，再選擇對應步驟。AI 剪片的 [Windows 說明](skill-packs/ai-video/docs/windows-install.md)與 [macOS 說明](skill-packs/ai-video/INSTALL.md)分開提供。
