---
name: website-service-integration
description: "把已建置的一人公司官網串接聯絡表單、電子報、預約與付款服務。當使用者要把 form_later 換成可用表單、加入訂閱／預約／結帳入口、設定外部服務或驗證整合結果時使用；預設採靜態網站可用的 HTTPS POST 與 hosted links，不保存憑證、不代做真實付款。"
---

# 官網服務串接

這是官網打造工作流的第六個技能。它把已由 `website-build` 建好的 Astro 靜態網站連到使用者選定的外部服務；不重新詢問商業定位，也不把帳號憑證、API Token、付款資料或服務後台識別碼寫入網站或技能包。

本版支援四種低耦合模式：聯絡表單使用標準 HTTPS POST（`html_post`）；電子報、預約與付款使用服務商提供的 HTTPS hosted URL（`hosted_link`）。需要第三方 JavaScript、iframe、API secret、Cloudflare Worker function、webhook、會員登入或資料庫的整合不在本版自動套用範圍，先列為後續方案。

## 啟動流程

這是多階段技能。開始前先用 Mermaid 顯示本次啟用的服務、外部帳號關卡、網站寫入、部署授權與停止位置。

1. 讀取 `website/config.json`、網站專案與既有 `website/integrations.json`；不得重問 `website-setup` 已記錄的商業資訊。
2. 執行 `manage_integrations.py status`，確認網站專案含 `src/pages/contact.astro`，並區分尚未設定、已套用、使用者修改後漂移三種狀態。
3. 只盤點使用者此次需要的服務。使用者已有供應商時沿用；沒有時，依 `references/integration-modes.md` 查詢候選服務的官方文件與目前價格，提出一份預設組合，讓使用者一次批次確認。不要依記憶承諾免費額度或功能。
4. 外部服務尚未準備好時，先預覽將建立的表單、名單、預約頁或付款連結及其公開效果，取得授權後才操作。人類只處理建立帳號、登入、同意條款／OAuth，以及付款服務要求的身分、稅務、銀行或收款資料；Agent 不要求使用者把秘密貼進對話。
5. 取得每項服務的公開 HTTPS endpoint 或 hosted URL，以及官方隱私政策網址。依 `assets/default-integrations.json` 產生完整候選設定；未啟用的服務維持 disabled，不建立空殼入口。
6. `plan --candidate` 驗證候選設定、秘密與網址邊界，列出會寫入的檔案、對外資料流、公開連結與剩餘人類步驟。取得使用者對同一份 plan 的明確授權。
7. `apply --expected-plan-sha256 <雜湊> --confirm-write` 寫入 `website/integrations.json`、專案 `src/data/integrations.json`、共用 Astro 元件並以標記區塊接上聯絡頁；已有電子報頁時同步接上。寫入失敗要回復本次涉及的所有檔案。
8. 執行 `npm run build`，再以 `verify` 檢查設定、原始碼、`dist/contact/index.html`、表單欄位、公開連結與隱私揭露。finding 必須修正後重跑；一次修正仍失敗就停止。
9. 需要更新已上線網站時，交給 `website-deploy` 產生新的部署預覽並另外取得部署授權；「授權串接」不等於「授權部署」。部署後以 `verify --url <正式網址>` 讀回公開頁面。
10. 依 `references/privacy-and-live-verification.md` 開啟每個 hosted URL 驗證目的地。聯絡表單與電子報的真實送出屬額外外部寫入，取得明確授權後使用虛構測試資料並從服務端讀回；付款只驗證結帳入口，不自動扣款或建立測試交易。
11. 回報每項服務的四層狀態：設定、網站本機建置、公開頁讀回、端到端動作。沒有服務端讀回證據時，不得宣稱表單或訂閱已可收到資料。

命令旗標不是對話核准。`--confirm-write` 只能在使用者確認同一份 plan 後使用。

## 預設方案

- 聯絡表單：原生 HTML `<form method="post">` 送往公開 HTTPS endpoint，欄位固定為姓名、Email、訊息與同意勾選；不在前端放 API secret。
- 電子報：連到服務商託管的訂閱頁；不嵌入追蹤腳本。
- 預約：連到服務商託管的預約頁；不嵌入 iframe。
- 付款：連到服務商託管的結帳頁；網站不接觸卡號，也不自動測試扣款。
- 每個已啟用服務都顯示服務商名稱與隱私政策連結；未提供隱私政策網址時停止，不發布入口。

需要比較模式或供應商時讀 `references/integration-modes.md`；準備公開、測試送出或判定完成時讀 `references/privacy-and-live-verification.md`。

## 人類接觸點

- 決定要啟用哪些服務並批次確認預設供應商；已有供應商時只確認沿用。
- 建立或登入外部服務帳號，完成條款、OAuth 或 Email 驗證。
- 付款服務要求時，由本人輸入身分、稅務、銀行與收款資料。
- 授權建立或修改外部服務資源、網站檔案寫入、重新部署，以及選擇性測試送出；各關卡分開。

平台臨時要求 CAPTCHA、簡訊、重新驗證密碼或付款資料時，交回使用者完成當下必要的一步，完成後由 Agent 繼續。

## 寫入與秘密邊界

- 工作區：`website/integrations.json`，只含會公開在 HTML 的服務商名稱、標籤、endpoint、hosted URL 與隱私政策網址。
- 網站專案：`src/data/integrations.json`、`src/components/ServiceIntegrations.astro`，以及聯絡頁／既有電子報頁的受管理標記區塊。
- 本機狀態：`.local/website/integration-state.json`，只保存雜湊與套用時間，不保存服務回覆內容或訪客資料。
- 外部服務：只建立或修改使用者已授權的表單、名單、預約頁或付款連結。

不得保存密碼、Cookie、OAuth token、API key、webhook secret、銀行資料、稅務資料、卡號、服務帳號 ID、訪客表單內容或訂閱名單。公開 form endpoint 或 hosted URL 雖會出現在 HTML，仍要拒絕帶有 `token`、`secret`、`password`、`api_key` 等查詢參數的網址。

## 停止條件

- 網站專案不存在、缺少聯絡頁，或受管理標記區塊已被手動改壞。
- 候選設定含秘密、非 HTTPS 網址、網址帳密、可疑秘密查詢參數或 `example.invalid`。
- 已啟用服務缺少 provider、公開目標或隱私政策網址。
- 供應商要求在前端放 API secret、任意 JavaScript、未審查 iframe、webhook 或伺服器端程式。
- 使用者未確認 plan、外部服務建立、部署或測試送出的對應授權。
- 外部服務需要付費升級，或付款服務要求身分、銀行、稅務或實際扣款。
- 本機或公開讀回有 finding，且一次針對性修正後仍失敗。

停止時保留已存在的網站與遠端服務，不刪除、不停用、不重送表單、不建立交易。

## 輸出

- 本次啟用、略過與尚待準備的服務。
- 每個外部動作的預覽、授權、執行與讀回結果，分開列出。
- 公開資料流：訪客輸入哪些欄位、送到哪個服務商、隱私政策在哪裡。
- 設定、本機建置、公開讀回與端到端測試四層狀態。
- 仍需人類完成的唯一下一步，以及是否需要 `website-deploy` 重新部署。
- 明確說明付款入口只驗證可開啟，未驗證真實扣款與入帳。

## 執行錯誤最小回填

若真實執行證明本技能規則或腳本有誤，先保留網站與遠端服務狀態；外部結果不明時只讀回，不重送。只有能證明錯誤來自本技能、修正限於本技能來源、不增加新依賴或權限，且一次針對性重測能通過時，才做一次小修正並執行本技能測試與套件驗證。否則停止並回報缺口；不得修改已安裝快取、第三方來源、外部服務資料或未獲授權的網站內容。

## 驗證

本機候選版以虛構供應商與 `example.test` 公開網址驗證：預覽雜湊與過期計畫、無授權不寫入、四種服務設定、秘密網址拒絕、受管理頁面接線冪等、失敗回復、靜態 HTML 讀回、公開 HTTP 測試頁讀回，以及未經授權不送出表單或付款。真實服務帳號、真實表單收件、訂閱名單、預約通知、付款入帳與另一臺電腦驗收仍分層回報。
