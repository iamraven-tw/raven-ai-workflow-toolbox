# Facebook 粉絲專頁發布 adapter

查證：2026-09-06。一般貼文以 Meta 官方 SDK 原始碼核對欄位與端點；影片／Reels 另查 Meta 官方 Postman 與官方產品公告。權限沿用已查證的 setup，執行時仍須重新確認所選 Graph API 版本的 Pages 文件。SDK 有欄位或官方 collection 有舊範例，不代表目前每個帳號都可用；未實機驗證。

## 實際執行來源

2026-09-13 補充：同一套 `publish_execute.py` 現可處理 `update_content`，只修改本 App 建立貼文的 message。先讀回確切貼文與更新時間，將新舊文案納入一次確認；程式重新核對 App、權限與未變的舊內容，單次送出後獨立讀回。完整欄位與未知結果規則見 [共用修改契約](../publishing-contract.md#facebook-文字修改)。已通過虛構測試，未修改任何真實貼文；刪除、媒體替換及其他管理功能不因此視為完成。

文字／連結與圖片 URL／多圖主要走本技能 `scripts/publish_execute.py` 串接 `official_publish_api.py`：Agent 在 begin 後執行 `execute-api`，協調器在每張 unpublished photo 與最後 feed 前分別 claim、取得 ID 立即 checkpoint，再以 `facebook_readback` 讀 PagePost 並形成 receipt。Token 由 setup `Runtime.access()` 取得，不經命令列。這個最小路徑不代建素材主機，也尚未處理本機圖片 multipart、影片或 Reels；本機圖片沒有已核准 HTTPS 來源、或格式是影片時，改走已核准的 Business Suite 受控瀏覽器，否則手動交付。

## 影片／Reels 的正式判定

Meta 官方 collection 文件化 Page Reels 的分階段 API：先對 `/{page-id}/video_reels` 執行 `upload_phase=start` 取得 video ID／upload URL，再上傳本機檔或提供可取用的託管影片，讀取影片狀態，最後以 `upload_phase=finish` 搭配 `PUBLISHED`、`DRAFT` 或 `SCHEDULED` 完成。[Facebook Reels Publishing API](https://www.postman.com/meta/facebook/documentation/r56bjfd/facebook-api?entity=request-23987686-0b79260c-96bd-49de-875b-6076213785fc)

但該 collection 的範例仍帶舊版 Graph 版本，並列 540×960、9:16、至少 23 FPS、4–60 秒等舊限制；Meta 2025 年又公告 Facebook 將逐步把所有影片統一為 Reels，且產品介面不再限制影片長度或格式。這兩者不能證明目前 API 的精確限制已同步。[Facebook 影片轉為 Reels 公告](https://about.fb.com/news/2025/06/making-it-easier-create-videos-facebook/)

因此本 MVP 的明確路由是：Facebook 文字、HTTPS 圖片及圖片輪播走正式 API；影片／Reels 雖有官方 API 能力證據，但低階 adapter 尚未實作，預設走已核准的 Business Suite 受控 Chrome，沒有可用瀏覽器就交手動。不要把舊 4–60 秒規則寫進驗證器，也不要把影片送入 photos／feed。要新增 Reels API adapter 時，必須先刷新當前版本、媒體限制、狀態欄位與排程條件，再補分階段 claim／checkpoint／讀回測試。

## 準備

只支援粉絲專頁，不是個人動態或社團。先透過已授權連線核對目標 Page 與內容建立 task、pages_manage_posts 及讀回所需 pages_read_engagement；沒有連線交 setup，不要求先改成廣告／企業管理權限。目標 Page ID 不等於登入者 User ID。

settings 須列 Page 可見性、是否附連結、附圖順序／替代文字、立即或原生排程（明確時區）、是否啟用跨平台分享；跨貼其他平台必須先納入預覽，預設不加。素材主機上傳另列已授權範圍。不可把圖片路徑當成公開 URL。

## 執行

共同 preview → 確認 → begin 後，對已固定的 Graph 版本操作：

1. 文字／連結：POST /{page-id}/feed，使用 message 與已核准 link。
2. 單圖：POST /{page-id}/photos，使用已支援的圖片來源、caption、alt_text_custom；記錄 photo ID，若回傳 post_id 一併保存，不把相簿照片 ID 當貼文 ID。
3. 多圖：逐張以 published=false 建立未公開 photo，checkpoint 每個 ID，再用 feed 的 attached_media 依核准順序組成一篇貼文。中途失敗留下的素材先記錄，不自動刪除；只有完整 ready 才送出 feed 一次。多圖不是多篇貼文。
4. 原生排程按該格式當前官方限制使用 published=false 與 scheduled_publish_time；先查允許時間範圍，不把 SDK 型別檢查當範圍證據。無法查證當前範圍就改可用的 Business Suite 排程 UI 並重新預覽，或停在本機計畫。

上述一般貼文端點與欄位依 [Meta Page 官方原始碼](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/page.py)；僅作查證，沒有安裝或複製 SDK。影片／Reels 不能塞進 photos／feed 當附件已完成；本 MVP 未提供其 API 上傳實作，依上節固定走已核准的 Business Suite 影片 UI。直播不在此範圍。

瀏覽器備援：核對 Page 身分 → 建立貼文／影片 → 填文案與附件 → 核對裁切與順序 → 查看實際可見性、平台勾選與時間 → 按核准範圍發布一次。必要登入或安全驗證交使用者。不可碰到「加強推廣」就順便建立廣告。

## 讀回

以實際 post ID 讀 GET /{post-id}?fields=id,message,permalink_url,created_time,is_published,scheduled_publish_time，必要時讀 attachments 核對媒體；不可拿 request body 當結果。[Meta PagePost 官方欄位](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/pagepost.py)

若 photos 回傳缺 post_id，從已授權的 Page 貼文讀回找到包含相同 photo ID 的唯一項目；不能只靠同文案猜測。UI 則真正重載已發布列表／排程列表，開啟該項，取得 ID、網址、平台時間和附件。published=true 才能記已發布；scheduled 應讀回相同預定時刻，不能當成實際上線時間。欄位缺失、影片尚在處理或只看到成功訊息都 pending；逾時後只查明，不再送一次 feed。
