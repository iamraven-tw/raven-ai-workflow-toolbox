---
name: google-workflow-router
description: 判斷 Google 自動化需求應走 Google Apps Script、既有 Apps Script 接管、Google Workspace API／OAuth、Cloud Run service、Cloud Run job／Cloud Scheduler，或需要專門設計的路線。當使用者提到 Google 自動化、Sheets、Docs、Forms、Drive、Gmail、Apps Script、Workspace API、OAuth、Webhook、Cloud Run、排程、既有指令碼、長時間工作或不知道該用哪個 Google 工具時使用。
---

# Google 自動化分流

先理解使用者要完成的工作，再選技術。不要先建立 Cloud Project、要求 OAuth、安裝 `clasp`，或把所有需求都塞進 Apps Script。

## 執行流程

1. 讀取 [需求判斷記錄](references/decision-record.md)，從現有說明與檔案填入能確定的欄位。
2. 只詢問會改變路線、且無法從現況查出的必要資訊。
3. 依下方路線選擇唯一主要入口；需要混合架構時，說明各元件的責任與邊界。
4. 在動手前列出本機工作、Google 登入、OAuth、遠端變更、可能費用與人工驗收。
5. 只執行目前已獲授權的階段。使用 [完成狀態](references/completion-gates.md) 回報，不把部分成功寫成全部完成。

## 路線 A：Google Apps Script／Learn-GAS

下列需求使用 [Apps Script 分流](references/apps-script-route.md)：

- 學習 Apps Script，或建立、修改、除錯 Apps Script。
- 接管使用者已有的 Apps Script 專案。
- 以 Sheets、Docs、Forms、Drive、Gmail 等內建服務完成個人或小型團隊自動化。
- Google Docs 固定版面、標籤、信封、證書或列印位置。

本包內建原 Learn-GAS 的四個技能：

- 未指定目的、建立或接管專案：`google-apps-script-project-development`
- 明確要逐步學習：`google-apps-script-teaching`
- 錯誤、權限、同步或結果異常：`google-apps-script-debugging`
- Google Docs 固定版面：`google-docs-layout`

這四個流程只在 Toolbox 維護。若技能未安裝或版本不符，依本套件 `INSTALL.md` 驗證內建來源後安裝；不得回到舊儲存庫下載。

## 路線 B：Google Workspace API／OAuth

外部程式、桌面工具、現有後端或需要 Apps Script 未涵蓋的 API 時，使用 [Workspace API 與 OAuth 路線](references/workspace-api-oauth-route.md)。

先判斷：

- 公開資料可否使用 API key。
- 是否代表目前使用者，需要 OAuth client 與使用者同意。
- 是否由應用程式擁有資料，或在受管理環境代表工作負載，需要服務帳戶或其他工作負載身分。
- scope 是否已縮到最小；是否涉及敏感／受限 scope、測試使用者或正式驗證。

本機程式與假資料測試可以先完成。建立或修改 Cloud Project、啟用 API、建立 OAuth client、下載 client secret、登入與授權都要各自取得明確同意；不得請使用者把 secret 或 Token 貼到對話。

## 路線 C：Cloud Run

依 [Cloud Run 路線](references/cloud-run-route.md) 選擇：

- 需要 HTTP／Webhook 入口、明確並行與逾時控制：Cloud Run service。
- 需要跑到完成的長時間批次：Cloud Run job。
- 需要固定時間啟動 job 或 service：Cloud Scheduler。

出現高流量、可能超過 Apps Script 配額、長時間工作、容器相依套件、公開端點或更完整部署生命週期時，不要因為資料最後進入 Sheets 就預設使用 Apps Script。

Cloud Run 不是無條件答案。若 Apps Script 能在已查驗的限制內更簡單、安全地完成，仍走 Learn-GAS。

## 路線 D：需要專門設計

Workspace Marketplace 外掛、Google Chat 應用程式、Admin SDK、網域層級委派、多租戶公開 OAuth、敏感／受限 scope 正式驗證、高風險資料、正式 SLA 或大型雲端架構不在本 MVP。

遇到這些需求時：

1. 保存需求、資料流、權限與風險。
2. 明確標示「需要專門設計或審查」。
3. 不新增空殼技能，也不把本機概念驗證寫成可正式上線。

## 固定安全規則

- 不保存 Token、Cookie、OAuth client secret、`.clasprc.json`、`.clasp.json`、Script ID、Cloud Project ID 或真實資源網址。
- `clasp push`、外部登入、OAuth、遠端寫入、Cloud 資源、部署、付費操作與公開網址各自需要明確確認。
- API、OAuth、配額、CLI 與 Cloud 行為可能改變；會影響決策時查閱參考文件中的官方連結與目前工具 `--help`。
- 測試優先使用虛構或程式產生的資料；需要真實帳號才能驗證的部分保留給使用者。
