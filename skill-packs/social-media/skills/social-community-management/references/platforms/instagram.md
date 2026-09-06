# Instagram 公開留言

查證：2026-09-06，Meta 官方 IGComment 原始碼與 Instagram Postman。`official_community_api.py` 與 `community_execute.py` 已用兩種登入路徑的假 Runtime／HTTP 串接；未驗證實機。版本與帳號能力在實際執行前刷新。

## 連線與讀取

只處理自有專業帳號媒體的公開頂層留言。Instagram Login 的 graph.instagram.com 與 Facebook Login 的 graph.facebook.com 不混用；分別核對 instagram_business_basic／instagram_business_manage_comments，或 instagram_basic／instagram_manage_comments 及需要的 Page scopes。App Review／Access Level 依目標帳號與當前路徑核對，不因自己測試帳號能用就宣稱可服務任意帳號。[Meta 官方登入路徑與權限](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)

採套件正式 API 路徑時，可信 adapter 在同一程序以 `Runtime(workspace, "instagram", connection=...)` 讀取私人 `login_route`，再於已確認的留言讀取範圍內呼叫 `Runtime.access(confirmed_read=True, allow_refresh=...)`。直接 Instagram Login 只從初次交換得知完整 scope；當次 `/{ig-media-id}/comments` 成功才是留言功能證據。Facebook Login 由 runtime 讀回 Page Token scope 與 Page／IG 關係。兩條路徑都不得把 Token 放入模型、對話、命令列或本機輸入檔；明確缺權限或失效交 setup，讀取不完整不當成零則。[Instagram Login 權限證據限制](../../../social-media-setup/references/instagram-threads-oauth.md#ig-權限證據與逐功能檢查)

`fetch-api` 先 GET /{ig-media-id} 核對 owner.id，再從 /{ig-media-id}/comments 讀 id、text、from／可用作者識別、username、timestamp、parent_id；用 /{ig-comment-id}/replies 查直接回覆。自家帳號以穩定 ID 比對，不只拿顯示名稱。每個列表最多五頁、本批最多 100 則；自家回覆檢查未完成就不回覆。[IGComment 官方欄位與 replies edge](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/igcomment.py)

來源寫入本機後才篩查，不先讓主 Agent 讀原文。官方 IGComment 已確認能提供留言 ID 與 timestamp，但官方欄位沒有 permalink；API 紀錄先保存在 fetch 證據，只有受控 Chrome 取得並核實該留言連結後，才以 `ingest-browser` 進隔離與 E 欄。只有媒體 permalink 時不能冒充訪客留言網址。

## 回覆與驗證

完成共通審核、可以回覆與重讀後，`execute-api` 取得 begin 與 reply_create claim，再 POST /{ig-comment-id}/replies，message 是精確 F 欄文字；成功 ID checkpoint。不是 /messages，也不會自動發布新媒體。

以 GET /{reply-id} 獨立核對 id、text、timestamp、作者與 parent_id；API 讀回因缺 permalink 保留 pending。受控 Chrome 重載並核實同一回覆連結後，以 `record-observation` 完成同一 attempt。不能把「回傳 ID」或「可讀到相同文字」當成所有欄位已完成；缺作者、父關係、網址或時間就停，錯誤、逾時及空回應不重送。

UI 備援：確認專業帳號 → 開指定媒體留言 → 展開自家直接回覆 → 核對 visitor 與原文 → 填 F 欄 → 回覆一次 → 真正重載與定位。工具無法先將外部原文安全送本機隔離時，改人工擷取，不用直接把整個頁面灌入有權限的主 Agent。

## 私訊界線

Meta 的私密回覆與一般訊息另有資格、時間及對話限制，不是公開回覆 API。本 MVP 只做一般私訊：只有使用者明確要求時才讀 [私訊 MVP 契約](../direct-messaging-contract.md)並啟動 `direct_message_execute.py`；不從留言自動改走私密回覆。

- **Instagram Login：** 使用 setup 的 Instagram User access token、`graph.instagram.com`、IG 專業帳號 ID，核對 `instagram_business_basic` 與 `instagram_business_manage_messages`。
- **Instagram via Facebook Login：** 使用 setup 保存的 linked Page access token、`graph.facebook.com`，核對 `instagram_basic`、`instagram_manage_messages` 與 `pages_manage_metadata`。Conversations edge 的 owner 是 linked Page ID，傳送 edge 的 actor 是 IG 專業帳號 ID；不可把兩個 ID 互換。

按需讀取為 `GET /{owner-id}/conversations?platform=instagram` → `GET /{conversation-id}?fields=messages` → 逐則 `GET /{message-id}?fields=id,created_time,from,to,message`。只保留最新一則由同一訪客先發起、未超過 24 小時且最近脈絡全為純文字的單人對話。Requests 超過 30 天可能不由 API 回傳、群組與分享媒體不在第一版；空結果不能推定沒有訊息。[Meta 官方 Instagram 對話文件](https://www.postman.com/meta/instagram/folder/23987686-6a91368f-1fa8-4614-9ed6-7d1e08c21e62)

人類另行確認批次後，`POST /{ig-user-id}/messages` 只送精確 `recipient.id` 與 `message.text` 一次。取得 message ID 立即 checkpoint，再 GET 同一 message ID 核對帳號寄件者、對話、訪客、完整文字及平台時間才算 replied。讀回失敗只查同一 ID；結果不明停止且不重送。[Meta 官方 Instagram Send API](https://www.postman.com/meta/instagram/folder/uxudqu0/send-api)

第一版不建 Webhook、不背景監控、不排程，不使用 `HUMAN_AGENT`、留言轉私密回覆、附件、範本或 24 小時窗外傳送。取得 permission 不等於讀取／傳送授權。完整查證與實機缺口見 [Meta 私訊 MVP 文件](../../../../docs/community-direct-messaging-mvp-research.md)。[Meta 官方私密回覆說明](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-af579d08-121e-4897-8f45-5fd41ace49df)
