# Threads 公開回覆

查證：2026-09-06，Meta 官方 Threads API workspace 已確認 `/replies`、`/conversation`、回覆欄位、`reply_to_id` 與兩階段發布；`official_community_api.py` 與 `community_execute.py` 已用假 Runtime／HTTP 串接。未登入、未讀取或回覆真實帳號。

## 讀取與支援條件

核對 Threads 自己的使用者識別與 Token，不拿 FB Page 或 IG Token 備援。官方 collection 列 threads_basic、threads_content_publish、threads_read_replies、threads_manage_replies；依目前要做的讀取／回覆操作確認實際 scopes 與 Access Level，不一次推定所有管理功能已驗收。[Meta 官方 collection](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api)

採套件正式 API 路徑時，可信 adapter 在同一程序以 `Runtime(workspace, "threads", connection=...)` 呼叫 `Runtime.access(confirmed_read=True, allow_refresh=...)`；runtime 會用官方 debugger 核對目前 scope，再以 `/me` 核對使用者。Token 不得進模型、對話、命令列或留言輸入檔。失效或 scope 不符交 setup；runtime 成功也只代表連線與已設定 scope 當下有效，完整回覆列表與父關係仍須由本文件的正式端點查明。

範圍是對自有公開 Threads 貼文的訪客直接回覆，不包含搜尋陌生貼文並主動留言。`fetch-api` 先從 `/me/threads` 分頁核對自有貼文，再用 `/{thread-id}/replies` 取得直接回覆；欄位包含 id、text、timestamp、permalink、username、is_reply、is_reply_owned_by_me、root_post、replied_to。`/{thread-id}/conversation` 可取得扁平化的頂層與巢狀對話，但本 MVP 的直接父子檢查仍用 replies edge，避免把後代回覆誤當頂層訪客留言。[官方回覆讀取文件](https://www.postman.com/meta/threads/request/y4uzu58/respond-to-replies)

抓取最多本批 100 則、每個列表最多五頁；顯示名稱與文字直接交本機 ingest。空 body、分頁缺失、無法判斷是不是對自有貼文回覆都不是零則。回覆前重新完整查自家是否已直接回覆；不能因取得單頁列表或 username 相似就跳過。

## 確認後回覆

所有共通關卡通過後，`execute-api` 先 begin 與 reply_container claim，再於 graph.threads.net 的已核對版本 POST `/me/threads`，media_type=TEXT、text=最終 F 欄、reply_to_id=核准訪客回覆 ID；不啟用 auto_publish_text。這是回覆父節點，不是新貼文，不附加媒體／引用／轉貼。[官方文字容器 request](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api?entity=request-34203612-e19a804d-ed93-45cd-82f8-7b8110a60744)

容器 ID 先 checkpoint；GET /{container-id}?fields=id,status 讀到 IN_PROGRESS 時標 pending，只能用 `resume-api` 續查同一容器。讀到 FINISHED 後另取得 reply_publish claim，再對 `/me/threads_publish` 傳 creation_id 一次並 checkpoint 正式回覆 ID。PUBLISHED 卻沒有正式 ID、ERROR、EXPIRED 或未知狀態都停止，不重建容器。

獨立從父留言 `/{reply-target-id}/replies` 分頁讀回同一正式 ID，核對 text、permalink、timestamp、is_reply_owned_by_me 與 replied_to.id。容器 FINISHED 不是已回覆；無法證明父對象、作者或精確時間時 pending，不重送。

UI 路徑：確認 Threads 身分 → 指定自有貼文 → 展開訪客回覆及自家回覆 → 對正確節點選回覆 → 填 F 欄 → 發送一次 → 真正重新載入定位回覆與父節點。回覆審批、隱藏／取消隱藏、刪除、私訊與陌生貼文互動不在本次範圍。
