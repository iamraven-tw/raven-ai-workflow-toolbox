# Instagram via Facebook Login OAuth 執行契約

查證日期：2026-09-06。只有使用者選擇 Instagram API with Facebook Login 時讀取本文件；共用 callback、秘密庫與恢復規則先讀 [OAuth 契約](oauth-runtime.md)。這條路徑使用 `graph.facebook.com` 與 Facebook Page access token，和 [Instagram Login／Threads](instagram-threads-oauth.md) 不同。

## 前置條件

- Instagram 必須是 Business 或 Creator 專業帳號，並已連結使用者可管理的 Facebook 粉絲專頁；消費者帳號不支援。
- OAuth 私人設定採 `platform=instagram`、`login_route=instagram_facebook_login`。`target_id` 是 Instagram 專業帳號的 Graph ID；Page ID 由授權後的 `/me/accounts` 關係讀回，不要求使用者手動抄寫。
- 使用 Facebook App、Facebook Login for Business、App ID／Secret、目前已查證的 Graph API 版本及精確 HTTPS redirect URI。Agent 必須在外部變更預覽列出 App、登入路線、完整權限、秘密庫、讀回範圍與人工關卡。
- 最低必要 permission 為 `pages_show_list`、`pages_read_engagement`、`instagram_basic`；完整核心依使用者已確認功能加入 `instagram_content_publish`、`instagram_manage_comments`、`instagram_manage_insights`、`instagram_manage_messages` 與 `pages_manage_metadata`。Business Manager 角色情境若需要 `ads_management`／`ads_read`，必須另行說明及確認，不默默加入。
- `public_profile` 是 Facebook Login 隱含授予，必須在預覽揭露並納入讀回核對。取得 permission 不代表下游發布、留言、私訊或成效端點已驗收。

使用共用 CLI 時明確傳入 `--platform instagram --login-route instagram_facebook_login`，加上 App ID、IG 目標 ID、逐項 scope、Graph 版本及 HTTPS callback 參數。沒有 `--login-route` 的舊 Instagram 私人設定維持 `instagram_login`，不會自動改走本路徑。

## 交換與身分綁定

1. 接收器產生一次性 state，從本機啟動頁導向版本化 `www.facebook.com/.../dialog/oauth`。本人核對 Facebook 帳號、相連資源與權限並同意；Agent 不代按同意。
2. callback 通過 state、期限、重播、Host 與 code 檢查後，以一次 GET 呼叫版本化 `graph.facebook.com/.../oauth/access_token` 換取短期 Facebook User Token。
3. 以官方 debugger 核對短期 User Token 的 App、USER 類型、使用者與期限，再用 `fb_exchange_token` 換長期 User Token，重新核對同一 App／使用者與期限。短期或長期 User Token 都不持久保存。
4. 以長期 User Token 讀 `/me/permissions`。實際 granted 必須等於確認清單加上 `public_profile`；歷史 declined／expired 項目可保留，但重複、未知狀態、少授予或多授予都停止。
5. 以 `/me/accounts?fields=id,name,access_token,tasks,instagram_business_account` 搜尋 `instagram_business_account.id == target_id` 的 Page。必須恰好一筆，且 Page ID／名稱、Page Token、非空工作權限及相連 IG ID 全部有效。其他 Page 與 Token 不保存。
6. 將選定 Page Token、Page ID、初次 Facebook 使用者 ID 與登入路線存成原生秘密庫的一個 bundle；一般設定與 OAuth 狀態檔不保存這些值。
7. 以 Page Token 重新讀 debugger、Page 節點的 `id,name,instagram_business_account`，以及 IG 節點的 `id,username`。App、PAGE 類型、目前 scope、期限、Page 與 IG 關係全部一致才標 `ready`。

官方 Meta Postman 的目前路徑使用 User Token 列出可管理 Page，再取得代表相連 Instagram 專業帳號的 Page Token。不能從使用者口述 Page 名稱推定關係，也不能把 Facebook Page 本身當成 IG 帳號。

## 日後取用與失效

- 下游在自身任務授權與預覽通過後，透過 `Runtime.access(confirmed_read=True)` 取得 Page Token；不讀取秘密庫分段、不將 Token 傳入模型、對話或命令列。
- 每次取用重新執行 Page debugger、Page／IG 關係與 IG 基本身分讀回。`allow_refresh` 不會替 Page Token 套用 Instagram Login、Threads 或 Google 的刷新機制。
- Page Token 的 `expires_at=0` 只表示未排定到期，不代表永久有效；撤權、資料存取期限、App／Page／IG 不符、scope 改變或平台拒絕時停止並回到新的 Facebook OAuth 確認，不盲目重送。
- 只讀身分核對成功仍不證明內容發布、留言、私訊或 insights 端點可用。各下游技能必須處理 App Review、Business Verification、訊息窗口、媒體限制與端點錯誤。
- 初次 User Token 不保存，因此無法在背景重新取得 Page Token。需要重新授權時先說明原因，取得本人確認後建立新 state／code；沒有背景登入或排程。

## 停止條件

- OAuth 實際 scope 與預覽不一致，或出現未確認的額外 granted permission。
- User Token 不是同一 App／使用者，Page Token 不是 PAGE 類型，或期限／有效性無法判定。
- 找不到唯一相連 Page、Page 沒有必要工作權限、IG 關係缺失，或 Page／IG 讀回與已確認目標不一致。
- 交換、保存或讀回結果不明。不得重送 code 交換，不得切回另一條 Instagram Login 路徑掩蓋錯誤。
- 缺少使用者控制且可信任的 HTTPS callback、原生秘密庫或當前官方文件。

## 官方依據與本機驗證

- [Meta 官方 Instagram API 文件](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)：Facebook Login 路徑的帳號限制、permission 與 Page Token。
- [取得可管理 Page Token 與相連 IG 帳號](https://www.postman.com/meta/instagram/request/23987686-23613b44-9a39-4ac1-9e2c-fd21b8235f45)：`/me/accounts` 欄位與 Token 關係。
- [Facebook Login manual flow](https://developers.facebook.com/docs/facebook-login/guides/advanced/manual-flow/) 與 [長期 Token](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived/)：code 與長期 User Token 交換。
- [Meta Page 官方原始碼](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/page.py) 與 [IGUser 官方原始碼](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/iguser.py)：Page 的 `instagram_business_account`、Page／IG 節點及正式 GET 欄位；只作行為查證，未安裝或複製 SDK。

`tests/test_instagram_facebook_oauth.py` 使用虛構記憶體秘密庫及 HTTP 回應，封鎖真實網路與原生 backend，涵蓋路線分離、交換、完整權限、唯一 Page／IG 關係、秘密保存、每次讀回、撤權與不明結果。這些測試不是實際 OAuth、App Review、平台讀取或下游功能驗收。
