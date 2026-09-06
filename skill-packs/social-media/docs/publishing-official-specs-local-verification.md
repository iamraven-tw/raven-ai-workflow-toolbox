# 發布官方規格與格式路由本機驗證

日期：2026-09-06。範圍是 PUB-03 的公開官方文件查證、機器可讀格式路由與虛構契約測試；未登入、未取得 Token、未讀取帳號、未建立媒體容器、未上傳、未發布、未排程，也未操作 Chrome。

## 路由結果

| 平台與格式 | 官方能力證據 | 本機實作 | 目前路由 |
| --- | --- | --- | --- |
| YouTube 影片 | Data API v3 `videos.insert` 與 resumable upload | 已接交易協調器 | 正式 API |
| Facebook 文字／HTTPS 圖片／圖片輪播 | Pages feed／photos／attached media | 已接交易協調器 | 正式 API |
| Facebook 影片／Reels | 官方 collection 有 start → upload → status → finish | 未實作；collection 限制與新影片產品方向未完全對齊 | 受控 Business Suite，再手動 |
| Instagram JPEG／純圖片輪播／Reel | 官方 Instagram API collection | 已接交易協調器 | 正式 API；需已核准 HTTPS 媒體來源 |
| Instagram 圖片影片混合輪播 | 官方最多 10 個混合項 | 協調器只建立圖片子容器 | 受控 Chrome，再手動 |
| Threads 文字／單圖／單片 | 官方 Threads API collection | 已接交易協調器 | 正式 API；媒體需已核准 HTTPS 來源 |
| Threads 輪播 | 官方 2–20 個圖片／影片子項與父容器 | 未實作子項／父項的交易 checkpoint | 受控 Chrome，再手動 |
| Substack 文章 | 官方 Dashboard；官方 MCP 唯讀 | 只有 browser handoff／claim／observation | 受控 Chrome，再手動 |

路由必須在完整預覽與 `begin` 前固定。只要某次寫入已 claim 而結果不明，就只能讀回查明，不能改走其他介面重發。

## 格式、版本與上限

### YouTube

官方 `videos.insert` 文件目前明列單檔 256 GB，接受 `video/*` 或 `application/octet-stream`，並支援 resumable upload。YouTube Help 另列平台上限為 12 小時，帳號未驗證時預設最多 15 分鐘；官方格式清單包含 MOV、MPEG、MP4、AVI、WMV、FLV、3GPP、WebM、DNxHR、ProRes、CineForm 與 HEVC，純音訊檔不能直接作為影片。配額文件目前列每天預設 100 次 `videos.insert`、每次 1 個 Video Uploads unit，但明示預設值可變；執行時仍以專案實際值與帳號 Feature eligibility 為準。未通過 API audit 的特定新專案可能只能將上傳影片設為 private。

來源：[videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert)、[resumable upload](https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol)、[Data API 配額](https://developers.google.com/youtube/v3/getting-started#quota)、[影片長度與大小](https://support.google.com/youtube/answer/71673)、[支援檔案格式](https://support.google.com/youtube/troubleshooter/2888402)。

### Facebook

Meta 官方 Postman collection 文件化 Page Reels 的 start、檔案或託管 URL 上傳、狀態讀取與 finish 階段；舊範例同時列 540×960、9:16、至少 23 FPS、4–60 秒。Meta 2025 年官方公告卻說 Facebook 正逐步把所有影片統一為 Reels，產品介面不再限制影片長度或格式。因 collection 範例版本偏舊，公告也不是開發者 API 規格，兩者不能組合成目前精確 API 上限。因此不把舊值寫進驗證器；在實作 Reels adapter 前須重新取得當前 Graph 版本、限制與狀態契約。

來源：[Facebook Reels Publishing API](https://www.postman.com/meta/facebook/documentation/r56bjfd/facebook-api?entity=request-23987686-0b79260c-96bd-49de-875b-6076213785fc)、[Facebook 影片統一為 Reels 公告](https://about.fb.com/news/2025/06/making-it-easier-create-videos-facebook/)、[Meta Page SDK 原始碼](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/page.py)。

### Instagram

官方 collection 目前列圖片只接受 JPEG，不接受 MPO／JPS；輪播最多 10 個圖片或影片；Reel 為 MOV／MP4、3 秒至 15 分鐘、最高 1 GB、23–60 FPS。同一份官方 collection 對 API 發布的 24 小時移動上限同時出現 50 與 100 兩種數字，不能任選一個硬編碼。執行時須讀 `/{ig-user-id}/content_publishing_limit`，並把真正額度、空資料、權限不足與讀取失敗分開。

來源：[Instagram API 官方 collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-ab559ffb-8e2c-4b0a-b43a-5737b6d2f672)、[Reels publishing](https://www.postman.com/meta/instagram/folder/830j7my/reels-publishing)。

### Threads

官方 collection 目前明列輪播由 2–20 個圖片／影片子容器組成，可混合媒體，再建立 `media_type=CAROUSEL` 的父容器。額度應由 `/me/threads_publishing_limit` 的 `quota_usage`／`config` 與回覆額度欄位讀取；能力表不保存模型記憶中的固定數字。collection 本身也提醒最新功能可能先出現在 changelog，因此正式執行仍要刷新所選 Graph 版本。

來源：[Threads 官方 API workspace](https://www.postman.com/meta/threads/overview)、[輪播建立流程](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api?entity=request-34203612-ee0a2365-9d95-4cbe-8087-1cfb04d38c05)、[發布額度端點](https://www.postman.com/meta/threads/request/w3x0n4g/retrieve-publishing-quota-limit)。

## 機器可讀契約與停止規則

[execution-sources.json](../skills/social-content-publishing/references/execution-sources.json) 已升至 schema 2，每個平台具有 `format_routes`；平台的主要介面不能蓋過格式變體路由。測試固定下列邊界：

- Facebook video、Threads carousel 的官方能力與本機 adapter 狀態必須分開。
- Instagram carousel 的純圖片與混合媒體路由必須分開。
- Instagram／Threads 不可硬編碼固定每日額度；YouTube 的文件值也要標示可變並在執行時讀實際專案資格。
- Meta Graph 版本由私人連線設定取得，正式執行前再對官方文件核對；不能因 Postman 範例帶舊版本就固定照抄。
- 任何沒有明確路由的格式停止，不能試送到相似端點。

## 驗證分層

| 層級 | 結果 |
| --- | --- |
| 靜態結構與文件 | 新能力表 schema、平台文件、相對連結、技能 quick validation、差異空白與套件 validator 均通過 |
| 本機技能發現 | 本輪未執行 |
| API 套件是否可安裝 | 未新增套件；本輪沒有安裝依賴 |
| 使用者登入與 OAuth | 未執行 |
| 平台讀取 | 未執行帳號資料；只有公開官方文件查證 |
| 測試發布 | 未執行；不產生任何外部寫入 |
| 另一臺電腦驗收 | 未執行 |
| 正式公開支援 | 尚未成立 |

本次新增 6 項格式路由契約測試；搭配既有低階 adapter 與交易協調器共 23 項針對性測試全數通過。整包離線回歸共 264 項：263 通過，1 項原生憑證探測依集中實機驗收政策略過。這些測試只讀能力表並使用虛構平台回應，不證明真實版本、帳號額度或發布可用。
