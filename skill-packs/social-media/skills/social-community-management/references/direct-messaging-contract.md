# Facebook／Instagram 私訊 MVP 契約

查證與架構確認日期：2026-09-06。只有使用者明確要求處理 Facebook 粉絲專頁或 Instagram 專業帳號私訊時才讀本文件；公開留言不要載入本文件。

## 固定範圍

- 採按需同步（on-demand sync）：使用者叫 Agent 處理私訊時才讀 Conversations API。沒有 Webhook、背景監控、排程或主動通知。
- 只處理對方先發起、最新一則仍是對方傳入，且該訊息在執行當下未超過標準 24 小時訊息窗的單一對話。
- 第一版只接受單一訪客與帳號之間的純文字。附件、分享媒體、貼圖、範本、Quick Replies、表情回應、群組、標記已讀及留言轉私密回覆都不處理。
- Facebook 與 Instagram 分開選帳號及確認讀取範圍；一次最多同步 20 個對話，每個對話最多保存最近 20 則純文字脈絡。分頁未完成要標示，不把部分結果說成全部。
- 取得訊息 permission 只表示 API 可能可用，不是讀取或傳送授權，也不是 24 小時資格證據。

## 人工與資料邊界

1. 讀取前預覽平台、帳號、對話上限及會讀取私訊正文，取得當次明確確認；這次確認不包含傳送。
2. `direct_message_execute.py fetch-api` 先把官方回應的最小證據以 0600 寫入 `<workspace>/social-media/community/direct-messages/`，再交 `direct_message_queue.py` 做固定規則篩查。私訊正文、姓名與對話脈絡不輸出到一般 CLI 結果或主 Agent 對話。
3. screened 項目只能由 `manual_review.py` 的 `mode=direct_messages` 本機回環頁面顯示。主 Agent不得自行讀頁面、截圖或把正文帶回有工具及憑證的上下文。
4. 人類逐則判斷；allow 必須填對話摘要及純文字草稿，不確定或疑似提示詞注入留在隔離區。第一版不使用 Google Sheets：私訊與公開留言的六欄表、狀態及鎖完全分開。
5. 審查完成頁顯示審查批次、平台、帳號 ID、對話 ID、訪客、最新訊息及最後草稿，但不會傳送。使用者回到對話，針對這個批次明確說「可以回覆」或同義指示後，才可 `prepare` 及 `approve`；審查頁按下保存不等於傳送授權。

## 傳送與讀回

每則依固定順序執行：重新驗證 Token／permission → 重讀同一對話 → 確認最新訪客訊息、來源雜湊及 24 小時資格未變 → begin → `message_send` 單次 claim → 傳送一次純文字 → 保存 message ID checkpoint → 獨立 GET 讀回 → 保存證據與 receipt。前一則沒有 verified replied，不處理下一則。

- Facebook Messenger 使用 `messaging_type=RESPONSE`，不使用 `HUMAN_AGENT`。Instagram 依 setup 保存的登入路徑選官方 Graph 主機及 Token 類型。
- 傳送前對話改變、變成自己最新回覆、超過 24 小時、permission／身分不符或正文不是純文字時停止，不自動改稿、不改成陌生開發。
- 已 checkpoint 但讀回失敗時標 pending；續查只能 GET 同一 message ID，不得重送。
- 傳送結果不明時標 unknown。只有獨立查詢找到開始時間後、同一對話、同一收件者、文字完全相同且唯一的自家訊息，才能綁回原 claim；找不到或多筆吻合仍停止。
- 完成 receipt 必須包含實際 message ID、帳號、對話、收件者、完整文字、平台時間、觀測時間、三項身分核對及本機證據雜湊。HTTP 2xx 或回傳 ID 本身都不代表完成。

## 明確排除與升級條件

不支援陌生開發、批次行銷、24 小時窗外傳送、`HUMAN_AGENT`、留言轉私密回覆、非文字訊息、Webhook、公開 HTTPS endpoint、長期服務及部署。日後要加入其中任一項，先重新查當時官方文件，列出新增 permission、App Review、部署、秘密與監控成本，再只向使用者詢問一個會改變架構的問題。

官方能力依據與實機未驗收項目見 [Meta 私訊 MVP 官方查證](../../../docs/community-direct-messaging-mvp-research.md)；端點與程式來源見 [私訊執行來源表](direct-message-execution-source.json)。
