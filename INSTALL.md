# Raven AI 一人公司工具包 安裝入口

> **PREVIEW · `0.1.0-preview.1`** — 本版本供早期驗收，尚未正式支援。安裝前請先閱讀 [PREVIEW 發行說明](docs/preview-release.md)，並以各技能包 manifest 的實際狀態為準。

本 repository 由多個可獨立演進的技能包組成。根目錄不提供會一次安裝全部內容的指令；先選擇需要的技能包，再由具備本機操作能力的 AI Agent 閱讀該套件的 `INSTALL.md` 與 `install.manifest.toml`。

## 目前狀態

| 技能包 | 狀態 | 安裝入口 |
|---|---|---|
| AI 知識庫 | Agent 端候選版可供外部驗收；尚未正式支援 | [`skill-packs/ai-knowledge-base/INSTALL.md`](skill-packs/ai-knowledge-base/INSTALL.md) |
| AI 剪片工作流 | Agent 端 MVP 已完成，可安裝為外部驗收候選版；尚未正式支援 | [`skill-packs/ai-video/INSTALL.md`](skill-packs/ai-video/INSTALL.md) |
| Google 工具自動化 | Agent 端 MVP 已完成，可安裝為外部驗收候選版；尚未正式支援 | [`skill-packs/google-automation/INSTALL.md`](skill-packs/google-automation/INSTALL.md) |
| 社群媒體管理工作流 | 七個技能為可安裝的本機候選（候選版 0.7.0）；七份流程審查已完成，登入／OAuth、平台讀取與測試發布尚未執行，尚未正式支援 | [`skill-packs/social-media/INSTALL.md`](skill-packs/social-media/INSTALL.md) |
| 官網打造工作流 | 七個技能（設定、文案、風格挑選、建置、部署、服務串接、維運）與起始範本為可安裝的本機候選；尚未正式支援 | [`skill-packs/website-building/INSTALL.md`](skill-packs/website-building/INSTALL.md) |
| AI Agent 規則與技能盤點 | 上游 v0.2.1 已鎖定並以乾淨 clone 核對雜湊，本套件為可安裝的本機候選；技能發現、實際盤點與另一臺電腦驗收尚未執行，尚未正式支援 | [`skill-packs/agent-inventory/INSTALL.md`](skill-packs/agent-inventory/INSTALL.md) |

## 第一次安裝後的盤點邀請

Agent 在目標使用範圍完成第一個 Toolbox 技能包的全新安裝，而且技能發現驗證成功後，主動詢問一次：

> 是否要盤點這台電腦上 AI Agent 的全域規則、全域技能、專案規則與專案技能？開始前會先列出偵測到的工具與候選專案，由你選擇掃描範圍。

- 這只是邀請，不代表使用者已授權安裝盤點技能或讀取任何規則內容；不得自動開始掃描。
- 使用者答應時，先依 [`skill-packs/agent-inventory/INSTALL.md`](skill-packs/agent-inventory/INSTALL.md) 檢查六個盤點技能是否已安裝。尚未安裝時，仍須分別取得下載上游與寫入技能目錄的同意；安裝完成後才交給 `inventory`，由 `inventory-setup` 顯示工具與候選專案並取得掃描範圍。
- 使用者拒絕或選擇稍後處理時立即停止，不影響已完成的技能包，也不在同一安裝流程中重複詢問。
- `status`、相同版本重跑、修復、更新、回復與移除不屬於第一次安裝，不觸發這項邀請。

## 共通規則

1. 安裝前先唯讀檢查作業系統、硬體、既有工具、目標位置與衝突。
2. 列出即將下載的第三方套件、固定版本、來源、授權、容量、可能費用與登入需求。
3. 取得使用者確認後才能下載、安裝、覆寫、登入或變更權限。
4. 不安裝 manifest 標示為 `installable = false` 的套件。
5. 完成後依套件 manifest 驗證技能、依賴、工作區與可見結果；任何必要步驟未通過時不得宣稱安裝成功。
6. 安裝狀態只能保存不含 Token、Cookie、帳號內容與私人素材的必要資訊。

第三方來源與 fork 的選擇方式見 [`docs/dependency-policy.md`](docs/dependency-policy.md)。自行撰寫的公開核心採 [Apache License 2.0](LICENSE)，第三方內容保留各自授權。

## 取得固定 Preview

從 [v0.1.0-preview.1](https://github.com/iamraven-tw/raven-ai-workflow-toolbox/releases/tag/v0.1.0-preview.1) 下載 Source code (zip)，解壓後由 Agent 閱讀本文件；或使用 Git：

```bash
git clone --branch v0.1.0-preview.1 --depth 1 https://github.com/iamraven-tw/raven-ai-workflow-toolbox.git
```

產品已改名為「Raven AI 一人公司工具包」。既有狀態目錄、憑證命名空間、schema ID 與 `product_id = "ai-workflow-toolbox"` 保留相容性，不必搬移或刪除。固定相容性補丁中的舊名稱屬版本化內容，仍按原雜湊驗證。

# Windows 與 macOS 平台分流

Google 工具自動化在兩平台皆使用其 `scripts/validate_upstream.py` 完成固定上游驗證；Windows 權限不足的 symlink 案例明確列為 skipped。AI 剪片在 Windows x64 使用 [Windows 安裝入口](skill-packs/ai-video/docs/windows-install.md)，macOS 14+ Apple Silicon 使用 [既有 macOS 安裝契約](skill-packs/ai-video/INSTALL.md)。不得在 Windows 執行 Homebrew 或 Bash 續行範例。各平台的候選驗證範圍與未完成項目見 [測試計畫](docs/windows-test-plan.md)。
