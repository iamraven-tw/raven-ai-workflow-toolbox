# Meta 私訊 MVP 官方查證與確認範圍

查證與確認日期：2026-09-06。對應待辦 `COM-05`。目前狀態：**官方能力查證與 MVP 架構確認完成，本機收發程式及虛構測試已建立，實機未驗收**。

本文件只使用 Meta 官方開發者資料與 Meta 官方 Postman 工作區。它不授權登入 Meta、建立 App、完成 OAuth、部署服務、讀取真實私訊或傳送訊息。取得 OAuth permission 也不等於已核准傳送訊息。

## 已確認的官方能力

### Facebook 粉絲專頁 Messenger

- Send API 需要 Page access token、`pages_messaging`，而要求 Token 的人必須能在 Page 執行 `MESSAGE` 工作。收件者必須在最近 24 小時內曾傳訊給 Page，或已同意接收標準 24 小時訊息窗之外的訊息。[Meta 官方 Messenger Send API](https://www.postman.com/meta/messenger-platform-api/folder/7cc3gd2/send-api)
- Conversations API 可列出粉絲專頁對話、訊息及單則訊息的寄件者與時間。官方文件列出的 Messenger 權限包含 `pages_manage_metadata`、`pages_read_engagement` 與 `pages_messaging`；讀取沒有 App、帳號、Page 或 Business 角色的一般使用者對話時，需要 Advanced Access。[Meta 官方 Conversations API](https://www.postman.com/meta/messenger-platform-api/folder/22794852-255610cd-47f5-4f4d-b3fa-71aec360be9a)
- 本技能只能把標準訊息窗、使用者先發起及當次端點回應當成傳送資格證據，不能以已取得 permission 推定可以主動聯繫任何人。

### Instagram 專業帳號私訊

- Instagram Login 路徑只適用於 Business／Creator 專業帳號。對話功能使用 `instagram_business_basic` 與 `instagram_business_manage_messages`、Instagram User access token，以及 `graph.instagram.com`。[Meta 官方 Instagram Login 對話文件](https://www.postman.com/meta/instagram/folder/23987686-6a91368f-1fa8-4614-9ed6-7d1e08c21e62)
- Facebook Login 路徑使用相連 Page 的 access token；官方對話文件列出 `instagram_basic`、`instagram_manage_messages` 與 `pages_manage_metadata`，並要求 App 所屬企業通過驗證。[Meta 官方 Instagram via Facebook Login 對話文件](https://www.postman.com/meta/messenger-platform-api/folder/22794852-255610cd-47f5-4f4d-b3fa-71aec360be9a)
- Instagram 對話只能由 Instagram 使用者先開始；Send API 的收件者必須先傳訊給該專業帳號。官方限制也包含不支援群組訊息、訊息要求匣內超過 30 天未活動的對話不會由 API 回傳，以及分享媒體只提供 URL。[Meta 官方 Instagram Send API](https://www.postman.com/meta/instagram/folder/uxudqu0/send-api)
- 標準自動化回覆採 24 小時訊息窗。`HUMAN_AGENT` 可支援較長的人工作業時間，但需要另外的 Human Agent permission／App Review，而且不得用於自動訊息；它不納入建議 MVP。[Meta 官方 Instagram 訊息標籤文件](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-af579d08-121e-4897-8f45-5fd41ace49df)
- 留言後的「私密回覆」是另一種功能：初次私密回覆有自己的七天限制，對方回覆後才形成可在 24 小時窗內繼續的對話。它不是一般收件匣回覆，也不納入建議 MVP。[Meta 官方 Instagram 私密回覆文件](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-af579d08-121e-4897-8f45-5fd41ace49df)

### Webhook 與審查

- Meta 的 Instagram 訊息文件以 Webhook server 接收通知，並訂閱 `messages`、`messaging_postbacks` 等事件。需要即時收件時，必須另外建立及驗證 Webhook 路徑。[Meta 官方 Instagram Webhooks 文件](https://www.postman.com/meta/workspace/instagram/documentation/23987686-9386f468-7714-490f-9bfc-9442db5c8f00)
- Standard Access／Advanced Access、App Review、Business Verification 與測試角色取決於登入路徑、App 所有權及要服務的帳號／對話對象；自己管理的測試帳號可讀不代表可公開服務其他使用者。

## 架構判斷，不是官方能力宣告

以下是依現有技能安全邊界做出的本機設計判斷：

- 即時 Webhook 會新增公開 HTTPS endpoint、長期執行環境、驗證 Token／簽章處理、事件去重、持久化、秘密管理、監控、部署與回復。這明顯超過目前純本機候選的最小變更，且部署需要另一項明確授權。
- 第一版可不建 Webhook，改為使用者叫 Agent 處理私訊時才透過 Conversations API 同步。代價是**不是即時收件**；使用者若沒有在 24 小時內執行工作流，標準自動回覆資格可能失效。
- 現有公開留言流程的本機隔離、固定規則、人工語意審查、草稿預覽、明確回覆確認、單次 claim、獨立讀回與不明結果停止，可以一般化後重用；私訊正文仍不得先交給有工具與憑證的主 Agent。

## 已確認的最小 MVP

第一版同時支援 Facebook 粉絲專頁 Messenger 與 Instagram 專業帳號私訊，兩種 Instagram 登入路徑均保留；但只實作：

1. 使用者明確叫 Agent 處理私訊時，按需同步所選帳號的對話，不背景監控、不建立排程。
2. 只收取由訪客先發起、仍在標準 24 小時訊息窗內的對話。
3. 私訊先進私人工作區隔離與固定規則，再由目前的本機人工頁面做語意審查。
4. 只產生純文字回覆草稿；使用者看過目標帳號、對話對象與最終文字並明確確認後，才逐則傳送。
5. 每則傳送前重讀對話與訊息窗；傳送後由正式 API 獨立讀回訊息 ID、對話／收件者、完整文字、平台時間及狀態。結果不明時停止，不重送。

第一版明確排除：陌生開發、批次行銷、標準窗外傳送、`HUMAN_AGENT` 七天標籤、留言轉私密回覆、附件、範本、Quick Replies、表情回應、標記已讀、封鎖／刪除、群組訊息、Webhook、背景服務與排程。這些功能若日後需要，逐項重新查證、預覽權限與確認。

## 使用者確認紀錄

使用者已於 2026-09-06 確認採用：「**Facebook 與 Instagram 私訊採使用者叫 Agent 時才同步，只處理對方先發起且仍在 24 小時內的純文字訊息；第一版不建 Webhook。**」

本機候選因此已建立獨立私訊 queue、官方 API adapter、交易協調器與人工審查模式。這項確認不授權讀取或傳送真實私訊，也不包含 Webhook；若日後要求即時收件，必須另行設計及授權公開 HTTPS Webhook 與部署。

## 分層驗收狀態

| 層級 | 狀態 |
| --- | --- |
| 官方能力與權限查證 | 已完成本次文件查證 |
| MVP 架構確認 | 已確認上述按需、24 小時、純文字、不建 Webhook 範圍 |
| 本機收發程式與虛構資料測試 | 已建立並通過針對性虛構測試；見[本機驗證](community-direct-messaging-local-verification.md) |
| 使用者登入、OAuth、App Review／Business Verification | 未執行 |
| 真實平台讀取與傳送 | 未執行 |
| Webhook／部署 | 不在建議 MVP；未授權、未建立 |
| 正式公開支援 | 未宣告 |
