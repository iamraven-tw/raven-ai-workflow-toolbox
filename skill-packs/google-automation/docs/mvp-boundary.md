# MVP 使用者故事與邊界

## 支援的使用者故事

### 1. 學習或修改 Google Apps Script

> 我想用 AI Agent 學會或修改一個會操作 Sheets、Docs、Forms、Drive 或 Gmail 的 Apps Script。

- 路線：Learn-GAS。
- 入口：未指定目的時先用 `google-apps-script-project-development`；明確教學用 `google-apps-script-teaching`。
- 驗收：本機程式與測試、OAuth、推送到 Apps Script、實際執行與可見結果分開確認。

### 2. 接手既有 Apps Script 專案

> 我已有一個遠端 Apps Script，希望 Agent 安全取得本機副本、建立 Git 基線再繼續開發。

- 路線：Learn-GAS 的 `google-apps-script-project-development`。
- 安全條件：先以登入帳號的唯讀清單辨識專案；不要求使用者貼出 Script ID；第一次取得用 clone，已有正確連結後才考慮 pull。
- 驗收：遠端原始狀態、本機基線、修改、推送與部署各自有證據。

### 3. 從外部程式使用 Google Workspace API

> 我需要一個本機程式或既有服務直接讀寫使用者的 Sheets、Drive 或 Gmail，而不是把程式放在 Apps Script。

- 路線：Workspace API／OAuth。
- Agent 先判斷資料是否公開、代表使用者或代表應用程式，再選 API key、OAuth client 或服務帳戶。
- MVP 可完成需求、scope 最小化、架構、本機程式與不需真實帳號的測試；建立 Cloud Project、OAuth client、登入與授權仍是獨立確認關卡。

### 4. 穩定的 HTTP 或 Webhook 入口

> 外部服務會呼叫一個公開端點，處理可能超過 Apps Script 限制，或需要更明確的並行、逾時、版本與部署控制。

- 路線：Cloud Run service。
- Agent 必須記錄呼叫者驗證、重送、冪等、逾時、錯誤回應、日誌、最小權限與可能費用。
- MVP 可建立本機服務、測試與部署計畫；Cloud Project、Artifact Registry、服務帳戶、秘密、部署與公開端點都需要另行確認。

### 5. 長時間批次或固定排程

> 工作會跑較久、需要明確完成狀態，或要每天／每週執行一次。

- 路線：Cloud Run job；需要固定時間時再加 Cloud Scheduler。
- 不為了排程而把長工作塞進 Apps Script，也不把 Cloud Run service 當作無限時間背景程序。
- MVP 可完成本機 job、測試、重跑與失敗策略；建立 job、Scheduler、IAM 與帳務設定仍需確認。

## 分流依據

Agent 至少收集下列可改變路線的資料；能從專案或說明讀到的內容不重複詢問：

1. 使用者要看到的業務成果。
2. 涉及的 Google 產品、資料擁有者與資料敏感度。
3. 誰觸發：個人、同一 Workspace、外部服務或公開網路。
4. 觸發方式：手動、Google 事件、Webhook、排程或批次。
5. 單次時間、每日量、並行數與可接受的延遲。
6. 是否需要對外公開、多人登入、網域管理員權限或可能計費。
7. 成功、重複執行、錯誤與回復的驗收方式。

Apps Script 配額會變動。只要時間、流量或並行可能接近限制，Agent 必須先查閱 [Apps Script 官方配額](https://developers.google.com/apps-script/guides/services/quotas)，不可使用文件內的舊數字作為永久保證。

## MVP 外的需求

下列需求可以完成盤點與風險說明，但不可宣稱本技能包已能完整交付：

- Workspace Marketplace 外掛、Google Chat 應用程式與正式公開發布。
- Admin SDK、網域層級委派、組織管理員政策或跨網域大量資料遷移。
- 多租戶公開 OAuth 應用程式、敏感或受限 scope 的正式驗證與安全評估。
- 高風險個資、醫療、財務、法遵或需要合約 SLA 的正式系統。
- 大型資料平台、Vertex AI、Cloud SQL、Pub/Sub 等需要另一份獨立架構的產品。
- 正式營運的監控、值班、災難復原、成本治理與基礎設施即程式碼。

遇到這些需求時，路由技能應停在「需要專門設計或審查」，保留已知需求與未決項目，不新增空殼技能掩蓋缺口。
