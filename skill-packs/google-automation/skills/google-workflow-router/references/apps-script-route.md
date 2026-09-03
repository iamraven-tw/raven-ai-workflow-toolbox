# Apps Script 與 Learn-GAS 路線

## 適用條件

- 工作主要發生在 Google Workspace，規模與時間可落在目前 Apps Script 配額內。
- 使用者需要低維護成本的個人或小型團隊自動化。
- 觸發器、Web App 或內建服務足以完成需求。
- 使用者要學習、修改、除錯或接管 Apps Script。

配額會變動。決策前查閱 [Apps Script 官方配額](https://developers.google.com/apps-script/guides/services/quotas)，並把目前數字與查驗日期留在專案記錄，不寫成永久能力。

## Learn-GAS 入口

| 情境 | 技能 |
|---|---|
| 未指定目的、建立新專案或接管既有專案 | `google-apps-script-project-development` |
| 明確要逐步學習 | `google-apps-script-teaching` |
| 執行錯誤、權限、同步、配額或結果異常 | `google-apps-script-debugging` |
| Google Docs 固定尺寸與位置 | `google-docs-layout` |

Learn-GAS 的專案開發技能是共用環境與遠端操作入口。即使從教學、除錯或固定版面開始，環境、Git、`clasp`、OAuth、推送與部署仍依它的規則處理。

## 接管既有專案

1. 先保護使用者本機檔案與 Git 狀態。
2. 以目前 Google 帳號的唯讀專案清單辨識目標；不要要求使用者貼出 Script ID。
3. 新的空白本機目錄第一次使用 clone；只有已有正確 `.clasp.json` 的後續同步才考慮 pull。
4. 建立未修改遠端內容的 Git 基線，再開始變更。
5. `clasp push`、觸發器與部署是三個不同操作，分別確認與驗證。

## 改走其他路線的訊號

- 外部應用程式本來就需要直接使用 Workspace API。
- 需要公開多使用者登入、敏感 scope 正式驗證或網域管理員能力。
- 執行時間、並行、每日量或相依套件可能超過 Apps Script 限制。
- 需要容器、長時間 job、明確服務版本、Webhook 流量控制或更完整的部署生命週期。
