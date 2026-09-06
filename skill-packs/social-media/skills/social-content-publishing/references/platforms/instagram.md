# Instagram 發布 adapter

查證：2026-09-06，以 Meta 官方 Postman 與 SDK 原始碼；精確格式與版本限制執行前再查。未登入、未發布。

## 先分清登入路徑

專業帳號（Business／Creator）才走此 API；Instagram Login 與 Facebook Login 是兩條不同連線。Instagram Login 使用 instagram_business_basic／instagram_business_content_publish；Facebook Login 使用 instagram_basic／instagram_content_publish 與相應 Page 讀取權限，並需關聯粉絲專頁。不能把 FB Page Token 換個平台名稱當 IG Login Token。[Meta 官方兩種登入說明](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)

套件已有兩條 Instagram OAuth 路徑，但不是發布 driver。採正式 API 時，可信 adapter 在同一程序建立 `Runtime(workspace, "instagram", connection=...)`，先讀私人連線設定的 `login_route`，再於本次已授權讀取／刷新範圍內呼叫 `Runtime.access(confirmed_read=True, allow_refresh=...)`；Token 不得進模型、對話、命令列或一般 JSON。`instagram_login` 回傳 Instagram User Token，使用 `graph.instagram.com`；`instagram_facebook_login` 回傳相連 Page Token，使用 `graph.facebook.com`。不得互換 host／Token，也不得為此重設另一條連線。

直接 Instagram Login 的 runtime 會核對初次完整 scope 與目前基本身分，但 Meta 目前已查官方資料沒有文件化全部當前 scope 讀回介面。因此只有實際 container／publish 端點能證明當次發布權限；明確缺權限或失效時停止並交 setup，建立或發布結果不明時停止且不重送。Facebook Login 路徑會讀回 Page Token 的當前 scope 與 Page／IG 關係，但仍不能取代發布端點驗證。[Instagram Login 權限證據限制](../../../social-media-setup/references/instagram-threads-oauth.md#ig-權限證據與逐功能檢查)

## 實際執行來源

主要路徑是本技能 `scripts/publish_execute.py` 串接 `official_publish_api.py`：Agent 在 begin 後執行 `execute-api`，協調器逐子容器／父容器 claim 與 checkpoint，只 GET 同一容器狀態，FINISHED 後才 claim `media_publish`，再讀正式媒體與形成 receipt。adapter 依 `login_route` 自動限制在 `graph.instagram.com` 或 `graph.facebook.com`，不接受 Token，也不自行等待或重送。官方 API 需要可公開取得的 HTTPS 媒體來源；未另外核准素材主機、或只有本機檔案時，改走已核准的 Instagram 受控瀏覽器，否則手動交付。

## 準備與執行

settings 列實際 IG 帳號、caption、單圖／輪播／Reel、媒體規格、順序、裁切、封面、share_to_feed、替代文字及適用選項；不預設跨貼 FB。核對此介面當前圖片格式、比例、容量與輪播數量，不沿用 App UI 上限。Meta 要以 URL 取檔時，檔案需在已授權且可取得的主機；沒有主機不能自行公開私人檔案、部署雲端或建立 tunnel。

當前官方 collection 列出的 API 規格包括：圖片只接受 JPEG，不接受擴充 JPEG 的 MPO／JPS；輪播最多 10 個圖片或影片；Reel 容器為 MOV／MP4、3 秒至 15 分鐘、最高 1 GB、23–60 FPS。這些是 API 路徑規格，不等於 App UI 的限制。[Instagram 發布與 Reels 規格](https://www.postman.com/meta/instagram/folder/830j7my/reels-publishing)

同一份官方 collection 目前一處寫每 24 小時 100 篇 API 發布，輪播段落卻仍寫 50 篇，文件本身不一致。本技能不硬編碼 50 或 100；執行前以 `/{ig-user-id}/content_publishing_limit` 查當前帳號用量，並把無資料、權限不足與讀取失敗分開。輪播官方能力可混合圖片與影片，但目前交易協調器只建立圖片子容器；純圖片輪播可走正式 API，混合輪播先走受控 Chrome 或手動，不能把影片 URL 當 image_url。[Instagram 官方發布 collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-ab559ffb-8e2c-4b0a-b43a-5737b6d2f672)

共同確認與 begin 後：

1. 依登入路徑選可信工具的正式 host／API 版本：FB Login 的 graph.facebook.com，IG Login 的 graph.instagram.com。單圖建立 /{ig-user-id}/media 的 image_url／caption；輪播依序建立 is_carousel_item=true 的子項，再用 media_type=CAROUSEL、children 與 caption 建父項；Reel 用 media_type=REELS 與 video_url。每個成功建立的容器 ID 立即 checkpoint。[Meta IGUser 建立欄位](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/iguser.py)
2. 容器 GET 讀 status_code／status，只有 FINISHED 才進下一步；IN_PROGRESS 做有界唯讀查詢，ERROR／EXPIRED 停。建容器本身是外部寫入，不可擺在確認之前。
3. POST /{ig-user-id}/media_publish，以 creation_id 指定同一個父容器／單項容器，保存回傳的正式 media ID。FINISHED 是待發布，media ID 與 container ID 不可混用。官方 collection 有 Reel 的完整建立、狀態查詢、發布例子；實際登入路徑及格式必須由工具確認支援。

## 讀回與 UI 備援

正式 media ID 讀 id、caption、media_type、media_product_type、permalink、timestamp，輪播讀 children 核對數量與順序；再開啟 permalink 檢查實際圖片／影片、封面與裁切。[Meta IGMedia 官方欄位](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/igmedia.py)

只有同一帳號且文案、媒體、選項都匹配，才記 published。某選項無法由 API 讀取則補重新載入的管理介面；拿不到精確 ID／時間不猜，記 pending。API 媒體容器處理預設最多五次唯讀查詢，每次間隔依官方建議或 Retry-After；未完成交回 pending，不長時間佔住任務、不重建容器。

瀏覽器路徑：核對帳號 → 建立貼文／Reel → 選最終檔及順序 → 裁切／封面 → caption／替代文字等 → 對照預覽 → 分享一次 → 重新載入個人頁並開貼文。若工具不支援、登入受阻或結果不明，停並交手動包。MVP 不提供 IG 原生／本機排程、Stories 或協作邀請流程；不把「尚未實作」說成平台絕對不支援。
