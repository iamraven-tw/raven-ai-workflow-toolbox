# 五平台發布執行來源本機驗證

日期：2026-09-06。範圍是 PUB-01 的執行來源選擇、四平台低階官方 API adapter 與虛構傳輸測試；未登入、未讀取帳號、未建立容器、未上傳、未發布、未寄信，也未安裝 OpenCLI 或其他第三方套件。

## 選定路徑

| 平台 | 主要介面 | 實際呼叫者與來源 | 本機完成範圍 | 尚待事項 |
| --- | --- | --- | --- | --- |
| YouTube | YouTube Data API | Agent 呼叫 `OfficialAPIAdapter` | resumable session、單次 PUT、影片讀回 | PUB-02 接 checkpoint、安全續傳及附加步驟 |
| Facebook | Pages Graph API | Agent 呼叫 `OfficialAPIAdapter` | feed、HTTPS 圖片、attached_media、PagePost 讀回 | 本機圖片與影片／Reels 走受控瀏覽器；後者官方有 API、adapter 未實作 |
| Instagram | Instagram API | Agent 呼叫 `OfficialAPIAdapter` | 兩種 login_route host、容器、狀態、media_publish、讀回 | API 媒體需已核准 HTTPS 來源；交易整合列 PUB-02 |
| Threads | Threads API | Agent 呼叫 `OfficialAPIAdapter` | 文字／單圖／單片容器、狀態、publish、讀回 | 官方 2–20 項輪播因 adapter 未實作先走受控瀏覽器；遠端媒體需已核准 HTTPS 來源 |
| Substack | 官方 Dashboard 受控瀏覽器 | Agent 透過 setup 固定來源的 OpenCLI 操作 Chrome | 操作契約已選定 | OpenCLI 與真實頁面留集中驗收；無官方寫入 API driver |

機器可讀版本見 [execution-sources.json](../skills/social-content-publishing/references/execution-sources.json)。PUB-03 已將它升至 schema 2，除平台主要介面外，另明列每個格式／變體的路由；它也明確將官方能力、adapter 實作與 `live_status=not_performed` 分開。

## 安全與交易邊界

- API adapter 只接受 YouTube、Facebook、Instagram、Threads 的固定 HTTPS 主機與端點，不跟隨重新導向；Token 只能由同一程序的 setup `Runtime.access()` 取得，沒有 `--token` 或任意 URL 入口。
- 每個寫入方法都要求包含 in_progress、平台、目標、preview SHA-256、確認參照與 refresh 選擇的 grant。PUB-02 完成前，Agent 仍須自己從 `publish_job.py` ledger 核對並逐階段 checkpoint，因此本次不宣稱已成為一鍵發布器。
- YouTube session URL 的 repr 固定隱藏；檔案雜湊改變即停止。308、5xx 或網路例外不建立第二個 session。
- Instagram／Threads 的容器建立與正式發布分開；低階方法不自行輪詢、不使用 auto-publish、不重建容器。Facebook 圖片 URL 與 Meta 遠端抓取媒體都屬另外核准的資料傳輸範圍。
- Substack 官方 MCP 只讀，沒有把第三方 CLI 或內部端點冒充官方發布 API。瀏覽器自動儲存草稿也是外部寫入，必須在發布確認後才進入。

## 官方查證

- YouTube `videos.insert` 的正式 upload endpoint、scope、metadata 與稽核限制，以及 resumable session／PUT／308 規則：[Videos: insert](https://developers.google.com/youtube/v3/docs/videos/insert)、[Resumable uploads](https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol)。
- Facebook Page feed／photos 與 Instagram media／media_publish 以 Meta 官方自動產生 SDK 原始碼及官方 Instagram Postman workspace 核對：[Page](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/page.py)、[IGUser](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/iguser.py)、[Instagram API](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)。SDK 欄位存在不等於每個帳號或版本都已驗收。
- Threads 的容器、輪播與 threads_publish 依 Meta 官方 workspace：[Threads API](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api)。輪播已確認為 2–20 個混合媒體子項，但本機 adapter 尚未實作；collection 可能落後 changelog，正式執行仍須刷新版本與額度。
- Substack 官方說明確認文章經 Dashboard 發布及寄信選項；官方 MCP 明確唯讀：[發布文章](https://support.substack.com/hc/en-us/articles/360037831771-How-do-I-publish-a-new-post-on-Substack)、[AI Assistant MCP](https://support.substack.com/hc/en-us/articles/50834026608916-How-to-connect-Substack-to-your-AI-Assistant)。本次未找到可據以實作文章寫入的正式公開 API。

## 驗證分層

| 層級 | 結果 |
| --- | --- |
| 靜態結構與文件 | 套件 validator、發布技能 quick validation、相對連結與差異空白檢查通過 |
| 本機技能發現 | 本輪未執行 |
| API 套件是否可安裝 | 未新增套件；adapter 使用 Python 標準函式庫 |
| 使用者登入與 OAuth | 未執行；只用假 Runtime |
| 平台讀取 | 未執行；只查官方公開來源與假回應 |
| 測試發布 | 未執行；所有 mutation 都是 FakeHTTP |
| 另一臺電腦驗收 | 未執行 |
| 正式公開支援 | 尚未成立 |

新增的 `test_official_publish_api.py` 共 10 項，全部通過；涵蓋無 grant 不取憑證、YouTube session 隱藏／檔案變更／308、Facebook feed／photo／attached_media 與 Page 歸屬、Instagram 兩種 host、Threads 兩階段及自有貼文分頁、固定方法／主機與錯誤去敏。整包共 251 項：250 通過，1 項原生憑證探測依集中實機驗收政策跳過。測試以 FakeHTTP 回應代替網路，不能證明官方帳號真的接受請求。

## PUB-02 後續狀態

本文件以上保留 PUB-01 當時的低階 adapter 結果。其後 PUB-02 已新增 `publish_execute.py`，將 begin、Runtime 預檢、寫入前 claim、checkpoint、獨立讀回、evidence 與 receipt 串接；Substack 則加入 browser handoff／claim／observation，仍未操作真實瀏覽器。驗證見 [發布交易整合本機驗證](publishing-transaction-integration-local-verification.md)。

## PUB-03 後續狀態

PUB-03 已補齊格式級路由、當前官方媒體限制與文件衝突處理。Facebook 影片／Reels、Threads 輪播及 Instagram 混合輪播不會再因平台主要介面是 API 而誤送至未支援 adapter；完整依據與 6 項契約測試見 [發布官方規格與格式路由本機驗證](publishing-official-specs-local-verification.md)。
