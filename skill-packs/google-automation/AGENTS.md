# Google 工具自動化協作規則

本目錄是 AI Workflow Toolbox 的 Google 工具自動化公開候選技能包。MVP 只補足跨技術分流、安裝契約與驗收門檻；Google Apps Script 的既有能力維持在 Learn-GAS 單一來源。

## 開始前

- 先讀 `README.md`、`INSTALL.md`、`install.manifest.toml`、`docs/architecture.md`、`docs/mvp-boundary.md`，以及根專案的 `docs/dependency-policy.md`。
- Learn-GAS 的整合方式以根專案的 `docs/decisions/0002-learn-gas-integration.md` 為準。
- `installable = true` 只表示 Agent 端門檻通過、可交給外部電腦驗收，不表示正式支援。

## 公開與安全邊界

- 不複製 Learn-GAS 的四個技能或範例程式；只從 manifest 固定的公開 commit 安裝。
- 不保存或輸出 Token、Cookie、OAuth client secret、`.clasprc.json`、`.clasp.json`、Script ID、Cloud Project ID、帳號資訊或真實 Google 資源網址。
- 測試只用虛構文字、暫存目錄及程式產生的 repository；不得使用維護者或使用者的 Google 資源。
- 本機程式、登入、OAuth 授權、遠端部署與人工驗收必須分開記錄。
- `clasp push`、登入、OAuth、Google Cloud 資源、部署、付費操作、push 與發布仍需各自明確同意。
- 私人流程與公開版本只做人工挑選的版本快照，不建立自動同步。

## 實作與驗證

- 沒有獨立缺口時不新增技能。MVP 只維護 `google-workflow-router` 這個跨路線入口。
- 安裝管理器只管理狀態檔已記錄且內容雜湊相符的入口；未知內容、人工修改或來源不符時停止。
- 在最後外部驗收前，完成 manifest、相對連結、隱私、授權、固定依賴、安裝生命週期及三種 Agent 路徑的本機驗證。
