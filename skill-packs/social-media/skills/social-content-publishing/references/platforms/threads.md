# Threads 發布 adapter

查證：2026-09-06，Meta 官方 Postman；未登入、未發布。精確上限與新功能需依當前 developer changelog 刷新，不能以 collection 未列出推定平台不支援。

## 準備

確認 Threads App／使用者連線及 threads_basic、threads_content_publish，核對 /me 的實際帳號；不是 Facebook Page 的 OAuth 身分。套件已有 Threads OAuth 與長 Token 按需刷新，但不是發布 driver。採正式 API 時，可信 adapter 在同一程序建立 `Runtime(workspace, "threads", connection=...)`，於已授權讀取／刷新範圍內呼叫 `Runtime.access(confirmed_read=True, allow_refresh=...)`；runtime 以官方 debugger 讀回目前 scope 並以 `/me` 核對帳號。Token 不得進模型、對話、命令列或一般 JSON。失效或 scope 不符交 setup，結果不明不切換 Facebook／Instagram Token。settings 明列 text、媒體型別／順序、替代文字、reply_control、連結與其他已選選項；不要擅自加 reply_to_id 把新貼文變成留言。

## 實際執行來源

文字、單圖與單支影片主要走本技能 `scripts/publish_execute.py` 串接 `official_publish_api.py`：Agent 在 begin 後執行 `execute-api`，協調器先 claim／checkpoint 容器，只 GET 同一容器狀態，FINISHED 後才 claim `threads_publish`，最後讀回自有貼文並形成 receipt。adapter 固定 `graph.threads.net`，不接受 Token、`auto_publish_text` 或 `reply_to_id`，也不自行等待或重送。圖片／影片需要已核准的公開 HTTPS 來源；只有本機素材時改走已核准受控瀏覽器。輪播已有官方 API 文件，但本 MVP adapter 尚未實作，因此預設也走受控瀏覽器，否則手動交付。

## 執行

共同 preview／確認／begin 後，使用 graph.threads.net 的當前正式版本：

1. POST /me/threads 建立容器，media_type=TEXT／IMAGE／VIDEO，搭配 text 與已核准 image_url／video_url。遠端取媒體需要可存取來源，公開素材主機是另外的外部影響，不自行架設。以兩階段流程執行，不在確認前使用 auto_publish。[Meta 建立及發布範例](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api?entity=request-34203612-e19a804d-ed93-45cd-82f8-7b8110a60744)
2. 官方 API 的輪播是 2–20 個圖片／影片，可混合；每個子項先以 `is_carousel_item=true` 建立 IMAGE／VIDEO 容器，再以 `media_type=CAROUSEL` 與 children 建立父容器，最後發布父容器。[Threads 輪播建立流程](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api?entity=request-34203612-ee0a2365-9d95-4cbe-8087-1cfb04d38c05) 目前 `OfficialAPIAdapter` 只接受 TEXT／IMAGE／VIDEO，未提供輪播子項、父項與部分成功 checkpoint；所以輪播不得呼叫 `execute-api`，應在預覽前選定受控 Chrome 或手動路徑。這是「官方有能力、套件尚未實作」，不是宣稱 Threads 不支援輪播。
3. 每個容器建立完成先 checkpoint，再 GET /{container-id}?fields=status。FINISHED 表示可發布；IN_PROGRESS 有界唯讀查詢最多五次，ERROR／EXPIRED 停。官方 collection 狀態頁的敘述曾與 GET 範例不一致，查狀態依 GET request，不依文字誤呼叫 POST threads_publish。[Meta 狀態範例](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api?entity=request-34203612-e9a7f46e-e48c-4987-a203-22fb25a4b604)
4. POST /me/threads_publish，creation_id 指向已準備好的容器，只送一次；保存正式貼文 ID。[Meta 發布請求](https://www.postman.com/meta/threads/request/34203612-c940a17f-e719-4b5b-9d28-7390bc658fb7)

發文額度不寫死成模型記憶中的固定數字。執行前以 `/me/threads_publishing_limit?fields=quota_usage,config,reply_quota_usage,reply_config` 讀目前設定與用量；查不到時停止 API 路徑，不用舊上限猜測。[Threads 發布額度端點](https://www.postman.com/meta/threads/request/w3x0n4g/retrieve-publishing-quota-limit)

## 讀回與備援

用同一使用者的 /me/threads 查到該正式 ID，選 id、text、permalink、timestamp、media_type；核對媒體及帳號，再實際開啟 permalink。列表需有限分頁（最多五頁），找不到不等於沒有發布。不是用同文案第一筆猜 ID，也不拿 container ID 代替。[Meta 貼文列表與讀回欄位](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api?entity=request-34203612-13ebe336-0176-4d2b-b208-c36646093139)

容器 PUBLISHED 仍要取得正式貼文 URL／ID／平台時間及內容證據；未取得記 pending／unknown，不重送。瀏覽器備援：核對 Threads 帳號 → 新增串文 → 放最終文字／媒體與順序 → 核對回覆設定 → 發布一次 → 真正重載個人頁、開啟貼文與時間資訊。介面缺精確識別或時間也 pending。MVP 不建 Threads 排程器、不延伸私訊、留言回覆、轉貼或引用他人內容的寫入；這些不是發文確認的附帶授權。
