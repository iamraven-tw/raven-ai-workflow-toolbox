# 平台啟用圖文教學

## 啟動時呈現，不只給文件路徑

實際開始 Facebook、Instagram、Threads 或 YouTube 的 App／API 人工設定時，先主動呈現隨技能提供的 `assets/api-setup-guide/index.html`，定位選取的平台與登入路線。不要等使用者自行尋找網頁。只討論策略、檢查狀態或執行已有可用連線的工作時，不強制重跑教學。

```sh
python3 <social-media-setup>/scripts/open_setup_guide.py --platform youtube
python3 <social-media-setup>/scripts/open_setup_guide.py --platform facebook --route page_token
python3 <social-media-setup>/scripts/open_setup_guide.py --platform facebook --route pages
python3 <social-media-setup>/scripts/open_setup_guide.py --platform instagram --route facebook_login
```

Agent 取得 `guide_url` 後，優先使用執行環境提供的網頁顯示能力開啟並讓使用者看到。沒有顯示能力時，加上 `--open` 請作業系統開啟預設瀏覽器，並交付可點擊的教學路徑。這只是開啟本機檔案，不授權操作使用者的日常瀏覽器。`browser_open_accepted` 只代表開啟請求被接受；未能顯示時明確告知，提供人工開啟路徑，不宣稱已呈現。Agent 需要操作 Chrome 查驗頁面時仍遵守所在環境的瀏覽器分工。

可用平台是 `facebook`、`instagram`、`threads`、`youtube`。Instagram 新設定預設 `facebook_login`，因本次完整管理包含 API 刪文；已存在的直接登入連線保留，先揭露缺少刪文能力，不自動遷移。`--step` 是從 1 起算的教學位置，不是已完成步驟數。網址片段可用來接續；不建立新的帳號資料庫或 OAuth 狀態系統。

## 自用管理的選路契約（優先於舊版全面 OAuth 指引）

| 平台 | 優先選路 | 回呼與秘密 |
| --- | --- | --- |
| Facebook | 既有有效連線 → 官方後台／Graph API Explorer 匯入 → 明確選定才用 HTTPS OAuth | 匯入交 Page Token 及同一 App Secret；不設定 HTTPS。OAuth 備援才設定回呼，兩個分支不全部做 |
| Instagram | 新設定採 Facebook Login，專業帳號連接專頁；直接登入只供接受無 API 刪文限制者 | OAuth 路線需要 HTTPS 與一般 Meta App Secret；刪文使用 Facebook User Token，不能拿 Page Token 代替 |
| Threads | 自有 App／測試角色的官方 User Token 匯入 | 不必為匯入設定 HTTPS，不先索取 App Secret；後台 Token 由本人先存入原生庫，程式再驗證及整理 |
| YouTube | Desktop OAuth，啟用 Data API 與 Analytics API | 本機 HTTP loopback／PKCE；Client ID／Client Secret，不申請額外 API key 或公開 HTTPS 網址 |

管理功能與限制依內容發布技能的 `references/content-management.md` 及當次功能檢查判定，不在教學選路表維護第二份程式待辦。

最短路線是選路依據，不是程式已可用的承諾。Agent 必須先檢查安全入口、匯入／交換器與本次必要功能；若使用者要求整組功能而尚有缺口，先揭露並停止取得秘密，可繼續說明申請內容，不強迫使用者先產生無法使用的 Token。若使用者接受只啟用已實作部分，記錄刪減；原生庫不可用或保存失敗仍須停止。

官方能力核對重點（2026-09-13；實作狀態另依本機程式查驗）：

- [Facebook 貼文](https://developers.facebook.com/documentation/pages-api/posts)：可刪除；修改限該 App 建立的貼文。[留言](https://developers.facebook.com/docs/graph-api/reference/comment/)可管理；[Messenger](https://www.postman.com/meta/messenger-platform-api/documentation/iyp204x/messenger-platform-api)回覆受平台時限與互動條件約束。私訊不是任意主動群發。
- [Instagram 媒體](https://developers.facebook.com/documentation/instagram-platform/reference/instagram-media)：刪除限 Facebook Login、Facebook User Token 與 `instagram_basic`／`instagram_manage_contents`；不支援以該更新 API 修改 caption。不可刪廣告媒體或單一輪播子項。[留言管理](https://developers.facebook.com/documentation/instagram-platform/comment-moderation)可先按需讀取，不強制 Webhook。
- [Threads 刪文](https://developers.facebook.com/documentation/threads/posts/delete-posts)另需 `threads_delete`。目前查核未找到已發布文字修改或一般私訊 API；公開 conversation 不等於私訊，不承諾這兩項。
- [YouTube API](https://developers.google.com/youtube/v3/docs)提供影片中繼資料修改、刪除與留言管理；不代表可替換影片檔案，沒有一般私訊管理端點。[Analytics 報表](https://developers.google.com/youtube/analytics/reference/reports/query)可按影片篩選。
- [Google OAuth 到期條件](https://developers.google.com/identity/protocols/oauth2)：External Testing 的本次 YouTube 權限通常使 refresh token 7 天到期，不強制長期保留測試模式；正式狀態與 OAuth 驗證分開判定。[YouTube 上傳](https://developers.google.com/youtube/v3/docs/videos/insert)另有未審核專案上傳限私人的規則，不能把 OAuth 驗證當成解除限制。

不為自用初始化加入廣告、商店、行銷網站或試算表。Webhook 是即時事件通知入口，OAuth 回呼是登入授權交接，二者不能混稱；只有所選功能與實際端點要求時才增加。

## 人機交接

- 教學是按需查閱，不是每次都要從頭完成的清單。先檢查既有連線，只呈現已選平台的缺項；內容、成效、留言與私訊保留，廣告／商店不加入預設問答。回呼頁限適用的授權碼路線；現有 Token、其他官方授權方式及套件支援程度必須分開核對，不以「自用」推定免授權或免審查。
- Agent 先提供本次權限、回呼網址與必要的一般資料；人類可一次看完並整批操作，不要求每一步回覆「完成」。
- API、MCP 或已有 OpenCLI adapter 可在授權範圍內完成的非敏感工作仍由 Agent 處理。只剩 Computer Use 時才提出人工操作與較慢的代做選項；不因為開啟教學而直接使用 Computer Use。
- 已同意 Agent 代辦後，App 名稱、聯絡信箱等一般資料填寫及精靈換頁不必交回人類操作；沿用已確認資料，示範名稱可用虛構資料。真實後台不可任填可能屬於他人的信箱；沿用已確認或預填的信箱並於拍攝前遮蔽。代填與補拍不授權最終建立、商家資產變更或條款同意。
- 後台秘密取得、隱藏輸入、OAuth 同意、本人驗證與條款仍由本人操作。已授權 OAuth 程式交換／刷新產生的 Token 可直接保存到系統憑證庫，不要求本人逐次確認，不顯示秘密。
- **安全停止條件**：原生庫或隱藏輸入不可用、保存／讀回失敗、帳號／權限不符或遠端結果不明時停止，不自動重送。Threads 後台 Token 仍先由本人存入原生庫，匯入器只驗證並整理同一筆已保存資料。
- 教學沒有秘密輸入欄位、分析追蹤、遠端請求或瀏覽器持久儲存。切換步驟、看到最後一頁或點開官方入口，都不會改寫平台整合狀態。

## 取得憑證與終端機交接

「本人輸入並儲存秘密」必須依路線呈現入口圖，不只給通用安全提醒。Facebook 兩條分支／Instagram Facebook Login 使用 Meta「應用程式設定 → 基本資料」的 App Secret；Instagram Login 使用 Instagram 專用密鑰。Facebook 匯入另交 Page Token，Threads 自用匯入交 Threads User Token，不以 App Secret 代替。Facebook 的專頁授權與權杖交接使用獨立圖文，不以 App Secret 圖代替。YouTube 使用 Desktop OAuth Client ID／Client Secret，不以 API key 代替。

已複製者只需告訴 Agent「我準備好輸入了」；Agent 開啟隱藏輸入終端機，使用者貼上並按 Enter 即確認儲存，再告知已輸入。Agent 檢查非敏感結果並接續已授權驗證。OAuth 交換／刷新產生的 Token 由程式直接保存與讀回，不要求再複製或按 Enter。

Google 既有用戶端頁的實拍與 [官方說明](https://support.google.com/cloud/answer/15549257?hl=en) 均指出：完整 Client Secret 只在建立當下顯示，不能事後重新查看或下載。教學須先提醒備妥安全入口；遺失時不擅自按 Add secret、刪除或重設。建立當下的一次性秘密位置已有遮蔽實拍。

## 教學與執行狀態分開

圖文教學已完成；Agent 啟動時呈現對應路線，不以歷史補拍清單或平台實機驗收阻擋教學。畫面來源與限制見圖片 metadata 及 `assets/api-setup-guide/CAPTURE_STATUS.md`，不將開發進度當使用者待辦。

真實設定仍核對當次帳號、權限、安全保存、平台讀取與維護排程，不把看完教學當成使用者已完成整合。

## 更新方式

內容集中在 `assets/api-setup-guide/guides.js`，介面與內容分離，不另建資料服務。每張圖記錄 `source`、`kind`、`captured`、尺寸、去識別化說明與百分比標示。真實後台、官方文件示例必須明確區分；沒拍到的步驟使用明確缺圖文字，不產生假介面。

更新內容與導覽時同步調整 `index.html` 兩個腳本的版本查詢值。此次 Chrome 曾載入新六分支內容、卻沿用只允許 Instagram 選路的舊導覽；加入版本後核對實際載入的腳本並重跑全部步驟。不要只換頁面網址的 revision 就假設所有資源已更新。

先於擷取前遮蔽帳號、專案、私人 App 名稱／ID、網址查詢、通知和秘密，再檢視最終圖片；錯誤提示也可能含私人 ID。只有檢查過的圖片可加入公開包。截圖來源頁與商標權利見套件 `THIRD_PARTY_NOTICES.md`。不把平台畫面誤標為本專案程式授權。

修改後執行 `tests/test_setup_guide.py`、套件結構驗證及安裝生命週期測試；另在真實瀏覽器檢查桌面／窄螢幕、平台／路線／步驟、標示位置、放大和鍵盤操作。沒有登入、建立 App 或執行 OAuth 的本機測試，不能提升平台驗證層級。
