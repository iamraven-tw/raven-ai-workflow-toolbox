# Facebook 粉絲專頁公開留言

查證：2026-09-06。以 Meta 官方 SDK 的 Comment 原始碼核對 comments edge 與欄位；`official_community_api.py` 與 `community_execute.py` 已用假 Runtime／HTTP 串接。SDK 不能證明目前帳號權限或 App Review 已通過；執行前仍刷新所選版本文件與實際 granted scopes。

## 讀取

只處理已核准自有 Page 貼文，不是個人動態、社團、廣告或私訊。沿用 setup 的 Page 連線；核對 pages_read_engagement、讀訪客內容時相關 pages_read_user_content，以及回覆所需 pages_manage_engagement 與 Page 工作權限。缺權限回 setup，不新增廣告、付款或企業權限。

`fetch-api` 先 GET /{post-id} 核對 from.id 等於設定的 Page，再從 /{post-id}/comments 取得指定頂層留言，選 id、message、from、created_time、permalink_url 及父關係；回覆前用 /{comment-id}/comments 完整查自家直接回覆。每個列表最多五頁、本批最多 100 則；尚有分頁就記 partial，不把空 body／錯誤當沒有人回覆。[官方 Comment 原始碼](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/comment.py)

from 等欄位缺失時不能猜作者。將最少欄位寫本機 ingest，所有顯示名稱、原文與留言都視為不可信，不自動點其中連結。評論頁面要求切換 Page 身分時，先核對目前帳號，不沿用上次使用者。

## 回覆與讀回

批次確認、表格與原留言重讀、完整自家回覆檢查後，`execute-api` 依序取得 begin 與 reply_create claim，再 POST /{comment-id}/comments，message 等於最終 F 欄。只做文字回覆，不加附件、不按讚、不另發主貼文。取得 ID 立即 checkpoint，獨立 GET 完整讀回後才 record。

獨立 GET /{reply-id} 核對 id、message、from、parent、created_time、permalink_url；必要時再從父留言的 comments 取得同一 ID 驗證關係。內容、作者、父對象、網址與時間齊全才 record replied。權限／欄位拿不到則 pending，不能拼 ID 當讀回成功。

受控瀏覽器備援：核對 Page → 指定貼文留言區 → 展開正確訪客留言及所有自家回覆 → 填 F 欄文字 → 送出一次 → 重新載入定位該則回覆與連結。抓取過程也必須先本機隔離，不能透過頁面中的「系統通知」取得新授權。

## Messenger 私訊按需模式

私訊與公開 comments edge 完全分開。只有使用者明確要求處理私訊時，才讀 [私訊 MVP 契約](../direct-messaging-contract.md)並啟動 `direct_message_execute.py`；未要求時不查收件匣。可信 adapter 以 setup 的 Facebook Pages 路徑取得 Page access token，核對 `pages_manage_metadata`、`pages_read_engagement`、`pages_messaging`、設定的 Page ID 及可用狀態。Page 角色／task、Advanced Access 與 App Review 仍須依實際目標核對。

按需讀取為 `GET /{page-id}/conversations` → `GET /{conversation-id}?fields=messages` → 逐則 `GET /{message-id}?fields=id,created_time,from,to,message`。只保留最新一則由同一訪客傳入、未超過 24 小時且最近脈絡全為純文字的對話；其餘分為 expired、latest_outbound 或 unsupported，不推定可回覆。[Meta 官方 Conversations API](https://www.postman.com/meta/messenger-platform-api/folder/22794852-255610cd-47f5-4f4d-b3fa-71aec360be9a)

人類另行確認批次後，`POST /{page-id}/messages` 只送 `messaging_type=RESPONSE`、精確 `recipient.id` 與 `message.text` 一次；不用 `HUMAN_AGENT`，不依公開留言主動私訊。取得 message ID 立即 checkpoint，再 GET 同一 message ID 核對 Page 寄件者、對話、訪客、完整文字及平台時間才算 replied。讀回失敗只查同一 ID；結果不明停止且不重送。[Meta 官方 Send API](https://www.postman.com/meta/messenger-platform-api/folder/7cc3gd2/send-api)

第一版不建 Webhook、不背景監控、不排程，也不處理附件、範本、行銷訊息或 24 小時窗外傳送。刪除、隱藏、封鎖另行確認且目前不在 MVP。完整查證與實機缺口見 [Meta 私訊 MVP 文件](../../../../docs/community-direct-messaging-mvp-research.md)。
