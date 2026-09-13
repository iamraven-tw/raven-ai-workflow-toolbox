# Google 工具自動化協作規則

本目錄是 Raven AI 一人公司工具包 的 Google 工具自動化公開候選技能包。本包同時維護跨技術分流與原 Learn-GAS 四個技能；唯一開發來源是 raven-ai-workflow-toolbox。

## 開始前

- 先讀 `README.md`、`INSTALL.md`、`install.manifest.toml`、`docs/architecture.md`、`docs/mvp-boundary.md`，以及根專案的 `docs/dependency-policy.md`。
- Learn-GAS 的整合方式以本包的 `docs/single-source.md` 為準。
- `installable = true` 只表示 Agent 端門檻通過、可交給外部電腦驗收，不表示正式支援。

## 公開與安全邊界

- 四個 Apps Script 技能、範例與測試都在本包維護；舊 repository 只保留歷史，不再下載或同步。
- 不保存或輸出 Token、Cookie、OAuth client secret、`.clasprc.json`、`.clasp.json`、Script ID、Cloud Project ID、帳號資訊或真實 Google 資源網址。
- 測試只用虛構文字、暫存目錄及程式產生的 repository；不得使用維護者或使用者的 Google 資源。
- 本機程式、登入、OAuth 授權、遠端部署與人工驗收必須分開記錄。
- `clasp push`、登入、OAuth、Google Cloud 資源、部署、付費操作、push 與發布仍需各自明確同意。
- 私人流程與公開版本只做人工挑選的版本快照，不建立自動同步。

## 原 Learn-GAS 共用規則

- 面向初學者先用白話說明術語用途，再使用中文名稱(English)，例如紀錄檔(Log)。
- 第一次說明推送到Apps Script(clasp push)時，解釋只同步程式，不等於執行或部署。
- 所有 `appsscript.json` 的 OAuth scopes 保持最小權限。
- 安裝依目前用戶端及本包 INSTALL.md；不依模型名稱猜測，也不自動安裝到所有用戶端。

## 實作與驗證

- 沒有獨立缺口時不新增技能。`google-workflow-router` 負責跨路線入口，Apps Script 的既有四個技能保留各自責任。
- 安裝管理器只管理狀態檔已記錄且內容雜湊相符的入口；未知內容、人工修改或來源不符時停止。
- 在最後外部驗收前，完成 manifest、相對連結、隱私、授權、固定依賴、安裝生命週期及三種 Agent 路徑的本機驗證。
