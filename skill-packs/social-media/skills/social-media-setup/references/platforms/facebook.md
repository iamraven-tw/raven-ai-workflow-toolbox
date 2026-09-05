# Facebook 平台初始化

查證日期：2026-09-05。本文件處理 Facebook 粉絲專頁，不把個人動態牆或社團能力推定為相同 API。

執行本文件前先讀 `../meta-api-setup.md`。Meta 後台與 OAuth 共用步驟依該文件處理；本文件只補 Facebook Pages 的帳號、permission、請求與驗收差異。

## 帳號與授權原則

Facebook 粉絲專頁管理使用 Facebook Login、使用者授權與 Page access token。先確認使用者對目標 Page 具有相應工作權限；Agent 不靠口述直接標為通過。

使用者第一次選取 Facebook 且沒有明確縮小範圍時，預設採 `full_management`，一次提出下列完整核心權限。這只是 OAuth 授權預設，不代表 Agent 已獲准立即發布、刪除、回覆或傳送私訊。

## 預設完整核心權限

| 核心功能 | permission | 官方允許範圍與必須揭露的影響 |
|---|---|---|
| 基本登入身分 | `public_profile` | Facebook Login 會自動授予，用於驗證應用程式使用者；不是 Agent 額外勾選的權限。 |
| 辨識可管理 Page | `pages_show_list` | 列出使用者管理的粉絲專頁並驗證管理關係。 |
| 讀取 Page 內容 | `pages_read_engagement` | 讀取 Page 發布的內容、部分追蹤者資料、Page 中繼資料與相關洞察；相依於 `pages_show_list`。 |
| 讀取訪客內容與公開留言 | `pages_read_user_content` | 讀取使用者或其他 Page 發布到目標 Page 的內容、留言、評分及標註；官方允許用途也包含刪除使用者留言。 |
| 發布與管理貼文 | `pages_manage_posts` | 建立、更新及刪除 Page 的貼文、相片或影片；相依於 `pages_read_engagement` 與 `pages_show_list`。 |
| 回覆與管理留言 | `pages_manage_engagement` | 建立、編輯及刪除 Page 留言，以及按讚／收回讚；相依於 `pages_read_user_content` 與 `pages_show_list`。 |
| 成效 | `read_insights` | 讀取 Page 與內容洞察；相依於 `pages_read_engagement` 與 `pages_show_list`。 |
| Webhook 與 Page 設定 | `pages_manage_metadata` | 訂閱及接收 Page Webhook，也能更新 Page 設定；因包含設定寫入能力，不能只描述成「通知權限」。 |
| Messenger 私訊 | `pages_messaging` | 存取及管理 Page 的 Messenger 對話，用於使用者主動開始的互動、客服與交易確認；相依於 `pages_manage_metadata` 與 `pages_show_list`。 |

執行前重新核對官方 permission 相依、Page task、Standard／Advanced Access、App Review 與 Business Verification。App 角色以外的使用者通常需要 App Review；測試 App 角色不等於公開支援。

Messenger 的完整核心授權仍受政策限制：收件者必須先向 Page 傳送訊息，或已同意接收標準訊息窗之外的訊息；一般客服回覆以官方目前的 24 小時規則為界。權限存在不能繞過訊息窗、opt-in、訊息標籤或其他政策。

## 可選延伸權限

下列能力不是社群內容管理核心預設，但 Agent 必須在同一份權限預覽中以類別列出，詢問使用者是否一併申請。只有使用者明確選取的類別才加入 OAuth；實際 permission 名稱與相依項仍須在執行當天重新查證。

| 類別 | 常見 permission | 說明 |
|---|---|---|
| 廣告成效唯讀 | `ads_read` | 讀取廣告帳號與廣告成效，不等於可建立或修改廣告。 |
| 建立及管理廣告 | `ads_management`、`pages_manage_ads` | 建立、修改與管理廣告活動及 Page 關聯廣告；可能需要 Marketing API access 與額外審查。 |
| 官方 Ads MCP | `ads_mcp_management` | 只有使用者要以 Meta 官方 Ads MCP 管理行銷活動或商務資產時才評估。 |
| 名單型廣告 | `leads_retrieval` | 讀取名單型廣告表單提交資料；涉及個人資料，並依賴廣告與企業相關權限。 |
| 企業資產 | `business_management` | 透過 Business Management API 讀寫企業資產及廣告帳號關係；不能模糊描述成一般 Page 管理。實際成員／角色操作另依端點與目前使用者角色核對。 |
| 商品目錄 | `catalog_management` | 建立、讀取、更新及刪除企業商品目錄；依賴 `business_management`。 |
| 商務帳號與訂單 | `commerce_manage_accounts`、`commerce_account_read_settings`、`commerce_account_read_orders`、`commerce_account_manage_orders` | 讀取商務設定與訂單，或建立／管理商務帳號及更新訂單。 |
| 商務財務報告 | `commerce_account_read_reports` | 讀取商務帳號財務報告；這不等於可管理一般 Meta 付款方式或帳單。若使用者要求「付款管理」，必須再查實際產品與端點，不能自行擴張解讀。 |
| 行動呼籲按鈕 | `pages_manage_cta` | 管理 Page 的 CTA 按鈕。 |
| 直播 | `publish_video` | 發布直播串流；一般貼文影片仍依 Page 貼文流程處理。 |
| 即時文章 | `pages_manage_instant_articles` | 建立或更新 Instant Articles；只在使用者仍使用該產品時評估。 |
| 商務事件 | `pages_events` | 傳送購買、加入購物車、名單等事件供廣告最佳化與分析；不是一般活動行事曆管理。 |
| Messenger 工具或付費行銷訊息 | `pages_utility_messages`、`paid_marketing_messages`、`marketing_messages_messenger` | 涉及範本、opt-in、付費行銷與額外政策；permission 名稱與產品資格必須在當下再次核對。 |
| 訪客個人化資料 | `pages_user_gender`、`pages_user_locale`、`pages_user_timezone` | 取得性別、地區／語言或時區等資料；涉及額外個資，預設不要求。 |
| 品牌合作與創作者探索 | `facebook_branded_content_ads_brand`、`facebook_creator_marketplace_discovery` | 管理合作廣告權限或探索創作者；不是一般自主內容發布。 |

不要預設要求使用者電子郵件、廣告、付款、企業資產、商品或訪客個人化資料。官方後台若顯示上表沒有列出的相鄰權限，先解釋正式名稱、用途、資料範圍與審查條件，再詢問是否加入。

## 預設正式整合路徑：完整社群管理授權

這條路徑建立 Facebook Page 的帳號讀取、內容讀寫、公開留言、成效、Webhook 與 Messenger 技術權限。設定技能只驗證 App、OAuth、實際授權清單與安全的唯讀 Page 讀回；發布、留言寫入與私訊傳送由後續技能各自實測。

### Agent 執行步驟

1. 依 `meta-api-setup.md` 顯示包含所有核心 permission、相依關係、可選延伸權限、審查需求及排除動作的外部變更預覽。
2. 使用者可在 OAuth 前刪除任一核心 permission 或選取延伸權限；刪減後改用 `custom` 並列出受影響功能。
3. Agent 建立或設定 Meta App、Facebook Login、Pages API、Messenger、OAuth callback 與完整已確認 permission。若 Messenger Webhook 需要尚未授權的公開 HTTPS 服務或部署，先停止該部分，不因此假裝私訊已可用。
4. 使用者本人在 OAuth 畫面核對帳號、Page 與 permission 後同意。
5. Agent 依 [OAuth 執行器](../oauth-runtime.md) 驗證 callback，於記憶體交換及檢查短期／長期 User access token；再讀回實際授予 permission，逐項與確認清單比較。User Token 不持久保存。
6. 呼叫 `GET /me/accounts?fields=id,name,access_token,tasks`，僅在記憶體解析回應；安全保存已確認目標的 Page access token，再讀回該 Page 的 `id` 與 `name`。不要保存其他 Page 的 Token。
7. 只把 App／OAuth／權限清單與 Page 唯讀關係標成已驗證。`publish`、`public_comments` 的寫入、`analytics` 指標查詢與 `direct_messages` 收發仍分別保持未測試，直到對應技能取得另一次行動確認並讀回結果。
8. 顯示一般設定寫入預覽；確認後才記錄 `full_management` 或 `custom`、要求及拒絕的 permission。

### 成功條件

- App 的實際 use case／產品與 callback 已讀回且符合預覽。
- OAuth `state` 驗證成功，Token 已進入獲准秘密儲存且未出現在輸出。
- 實際授予 permission 與使用者確認清單完全一致，沒有未說明的多餘權限。
- `/me/accounts` 回傳指定 Page，tasks 可供判斷 Page 關係，且 Page 唯讀查詢讀回相同 `id` 與 `name`。
- 未把「已取得寫入 permission」誤報成貼文、留言、成效或 Messenger 已完成實測。

## 明確縮限路徑：粉絲專頁唯讀驗證

只有使用者明確說「先只讀」、「不要發文」或拒絕其他核心權限時，才改走此路徑。它證明 Meta App、Facebook Login、User access token、Page 關係與正式 API 讀取確實可用，不發布、不回覆、不排程，也不證明 App 已通過公開使用者所需審查。

### 前提

- 使用者已指定可辨識的目標 Facebook Page。
- 登入的 Facebook 個人帳號確實具有該 Page 所需工作權限；Agent 不靠使用者口述直接標為通過。
- 受控瀏覽器、相容 OAuth callback 與獲准秘密儲存均可用。
- 第一輪只測 App 角色或使用者自有／可管理資產；其他帳號、Advanced Access、App Review 與 Business Verification 另列驗收。

### 縮限 permission

先只要求列出可管理 Page 所需的 `pages_show_list`。若本輪另明確要求讀取 Page 內容或互動，重新預覽後才加入 `pages_read_engagement`，以及當下官方文件證明必要的其他唯讀 permission。

唯讀驗證不得要求使用者已拒絕的 `pages_manage_posts`、`pages_manage_engagement`、`pages_manage_metadata` 或 `pages_messaging`。後續要新增功能時重新顯示完整權限預覽並取得確認。

### Agent 執行步驟

1. 依 `meta-api-setup.md` 顯示外部變更預覽並取得確認。
2. Agent 開啟 Meta for Developers；只在登入、2FA、首次開發者條款或平台強制驗證時交回使用者。
3. Agent 建立 Meta App，選取目前官方後台中可支援 Facebook Login 與 Pages API 的 use case／產品，並設定已確認的 OAuth callback 與 `pages_show_list`。
4. Agent 啟動 OAuth；使用者本人確認 Facebook 帳號、Page 資源與 permission 後同意。
5. Agent 依 [OAuth 執行器](../oauth-runtime.md) 驗證 callback，於記憶體取得並檢查短期／長期 User access token，不把 Token 放入 URL 紀錄、stdout、對話或一般設定，也不持久保存 User Token。
6. 以當下支援的 Graph API 版本呼叫 `GET /me/accounts?fields=id,name,access_token,tasks`。官方 GET 所需 Token／appsecret proof 由固定主機的受控 HTTPS 程序傳送，不建立 URL 日誌、不使用代理、不跟隨重新導向，也不在瀏覽器開啟含秘密的 API URL。
7. 解析回應時僅把已確認目標的 Page access token 送入獲准秘密儲存；不保存其他 Page 的 Token。使用者只看到 Page 名稱、遮蔽識別資訊與 tasks，不顯示原始 Token。
8. 若目標 Page 唯一吻合，再以其 Page access token 呼叫唯讀 Page 查詢，至少讀回 `id` 與 `name`，並核對 Page 名稱與 Page token 所代表的資源。
9. 讀回已授權 permission、Token 類型與可判斷的到期資訊。記錄實際時間、Graph API 版本及遮蔽後證據。
10. 顯示一般設定寫入預覽；確認後才以 `custom` 記錄實際要求與拒絕的 permission，並把 Facebook 整合摘要標成平台讀取已驗證。遠端寫入仍標示未授權或未測試。

### 成功條件

必須同時成立：

- Meta App 的實際 use case／產品與 OAuth callback 已讀回且符合預覽。
- OAuth callback `state` 驗證成功，Token 已進入獲准秘密儲存且未出現在輸出。
- `/me/accounts` 實際回傳指定 Page，且 tasks 可供判斷目前帳號的 Page 關係。
- Page 唯讀查詢讀回相同 Page 的 `id` 與 `name`。
- permission 與本輪縮限預覽一致，沒有取得使用者拒絕的管理貼文、留言或私訊權限。

下列情況都不是成功：只看到 App Dashboard、只取得 App ID 或 Token、HTTP 請求已送出、只收到 HTTP 200、Page 清單為空、目標 Page 不唯一、tasks 不符或原始回應無法安全解析。

### 停止與追問

- 未登入或帳號不符：只請使用者完成正確帳號登入，不自動切換。
- 多個 Page 都可能符合：顯示不含 Token 的候選名稱，一次只問使用者要哪一個。
- 已確認 permission 不足：先保留錯誤證據，重查當下官方文件，再預覽新增 permission；不直接擴權重跑 OAuth。
- App Review／Business Verification 阻擋：保持第一輪驗證結果，不把 App 角色測試宣稱為公開支援。
- API 結果不明：停止，不重新建立 App，也不盲目重送 OAuth 或 API 寫入。

## 功能判斷

| 功能 | 官方路線 | 初始化重點 |
|---|---|---|
| 發布 | Pages API 貼文、相片、影片或 Reels 流程 | 貼文類型、Page task、發布／排程權限與媒體處理狀態 |
| 公開留言 | Page 貼文留言讀取與 `pages_manage_engagement` | 訪客內容讀取權限、Webhook／輪詢、每則回覆讀回 |
| 成效 | Page／貼文 insights | 指標定義、資料窗口、權限與已棄用指標；不可把缺值當 0 |
| 私訊 | Messenger Platform | `pages_messaging`、`pages_manage_metadata`、使用者先發起、時間窗、Webhook 與審查；屬於預設完整核心權限，但收發仍需獨立實測 |

## 驗證

- 取得 Page access token 不代表具有所有 Page 工作權限。
- 建立貼文、上傳或排程請求成功後，仍要用 Page 與貼文 ID 讀回 permalink、建立／排程時間、發布狀態與目標 Page。
- Messenger 的 24 小時與 opt-in 規則不能用一般留言權限或已取得的 OAuth permission 繞過；每次批次回覆或主動訊息仍受對應技能的預覽與確認約束。

## 官方來源

- [Pages API 貼文](https://developers.facebook.com/docs/pages-api/posts/)
- [Meta permissions](https://developers.facebook.com/docs/permissions/)
- [Meta App Review](https://developers.facebook.com/docs/app-review/)
- [取得可管理 Page 與 Page access token](https://www.postman.com/meta/facebook/request/bqfxwbp/get-access-tokens-of-pages-you-manage)
- [Meta 官方 Facebook Postman workspace](https://www.postman.com/meta/facebook/overview)
- [Messenger Platform 官方 Postman 文件](https://www.postman.com/meta/messenger-platform-api/documentation/iyp204x/messenger-platform-api)
- [Meta 官方 Facebook Marketing API workspace](https://www.postman.com/meta/facebook-marketing-api/overview)
