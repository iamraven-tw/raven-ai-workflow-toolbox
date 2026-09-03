# Cloud Run、排程與 Webhook 路線

## 選擇執行型態

依 [Cloud Run 概觀](https://cloud.google.com/run/docs/overview/what-is-cloud-run) 選擇：

| 需求 | 路線 |
|---|---|
| 接收 HTTP、API 或 Webhook，依請求回應 | Cloud Run service |
| 一次啟動後跑到完成的批次 | Cloud Run job |
| 固定時間觸發 service 或 job | Cloud Scheduler |
| 必須持續消費背景工作 | 不直接套用本 MVP，先做專門架構判斷 |

Webhook 參考 [Cloud Run Webhooks](https://cloud.google.com/run/docs/triggering/webhooks)；排程參考 [Cloud Scheduler 觸發 Cloud Run](https://cloud.google.com/run/docs/triggering/using-scheduler)。

## 必須定義

- 呼叫者驗證與最小 IAM。
- 重送、冪等鍵、重複資料與部分成功。
- 逾時、並行、資源上限與下游 Google API 配額。
- secret 的來源與輪替；不寫入映像檔、Git 或狀態檔。
- 結構化日誌、錯誤狀態與人工可查的業務結果。
- 最小／最大執行個體、網路與可能費用。
- 版本、部署、回復與移除方式。

## 分階段交付

1. 本機：服務或 job、虛構資料測試、容器建置與失敗情境。
2. 帳號與權限：確認 Google 帳號、Cloud Project、API、服務身分與最小 IAM。
3. 遠端：經明確同意後建立或修改資源、部署並讀回版本與狀態。
4. 人工驗收：使用者以有權使用的測試資料觸發一次，確認 Google 資源與日誌中的實際結果。

任何一階段通過都不能代替後面的階段。
