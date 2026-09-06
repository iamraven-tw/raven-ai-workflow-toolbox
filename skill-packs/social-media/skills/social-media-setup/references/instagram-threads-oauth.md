# Instagram Login／Threads OAuth 執行契約

查證日期：2026-09-06。只有選取這兩條路徑才讀本文件；共用確認、HTTPS callback、原生保存與恢復規則先讀 [OAuth 契約](oauth-runtime.md)。這是初始化技能的程式，不是發布或私訊技能。

## 前置條件與輸入

- Agent 先依平台文件列出完整核心權限，讓使用者刪減；不要把下方必要的 basic scope 當成預設僅唯讀。
- 每平台分開確認 App ID、App Secret、目標帳號、scope、API 版本、精確 HTTPS redirect URI、callback 接收方式、原生秘密庫與日後按需刷新授權。登入與 OAuth 同意交由本人。
- `platform=instagram` 明確指 **Instagram Login**，使用專用 Instagram App ID／Secret、專業帳號及 `instagram_business_*` scope；不接受 Facebook Login 的 `instagram_basic` 或 Page scope。
- IG `target_id` 是專業帳號 `user_id`，不是 App-scoped `id`；初次 code 回應中的 `user_id` 是 App-scoped ID。程式分別保存並核對，不因欄位同名就混用。Agent 從已授權的官方帳號資料／後台取得目標，不要求人抄 Token，也不以任意登入帳號自動取代已確認目標。
- `platform=threads` 使用 Threads 專用 App ID／Secret；`target_id` 是 Threads App-scoped ID。不得拿 Instagram 或 Facebook 的 ID／Token 代替。
- API 版本無預設；查證時 IG 官方範例為 `v25.0`，Threads 為 `v1.0`，執行前重新核對。
- 設定前 `preview`、確認後 `configure`，兩者需相同參數及 digest。Meta 三平台同用既有 HTTPS 接收條件，不建立代理、不安裝隧道、不關閉 TLS 驗證。

Agent 依共用命令介面傳 `--platform instagram` 或 `--platform threads`，以及 `--client-id`、`--target-id`、逐項 `--scope`、`--graph-version`、`--callback-mode https_proxy`、`--callback-port`、`--redirect-uri`。Secret 必須已透過隱藏輸入或受信任程序存入該平台 `app-secret`，不得當作命令列參數。

## 授權與交換順序

| 階段 | Instagram Login | Threads |
|---|---|---|
| 瀏覽器同意 | `www.instagram.com/oauth/authorize` | `www.threads.com/oauth/authorize`，依 Meta 官方範例原始碼 |
| code 交換 | POST `api.instagram.com/oauth/access_token`，multipart form | POST `graph.threads.net/oauth/access_token`，URL-encoded form |
| 長期交換 | GET `graph.instagram.com/access_token`，`ig_exchange_token` | GET `graph.threads.net/access_token`，`th_exchange_token` |
| 日後刷新 | GET `graph.instagram.com/refresh_access_token`，`ig_refresh_token` | GET `graph.threads.net/refresh_access_token`，`th_refresh_token` |
| 唯讀核對 | 版本化 `/me` 的 `id,user_id,username,account_type` | `/debug_token` 與版本化 `/me` 的 `id,username` |

1. 一次性 state 與 code 在記憶體核對，錯誤／取消／逾時／重播不交換。官方 code 有效一小時；本接收器採更短的 15 分鐘。授權網址的 `#_` 不是 code，瀏覽器 fragment 不傳給伺服器。
2. 只交換一次短期 Token。IG 支援官方文件的單筆 `data` 陣列與平面回應；拒絕多筆或混合歧義。IG 核對交換回應 `permissions` 與已確認清單完全一致。Threads 在稍後 debugger 核對。
3. 用各自 grant 換長期 Token，短期 Token 不保存。要求有效 `access_token`、bearer 類型與正整數 `expires_in`；缺期限不能自行補成 60 天。
4. 長期 Token、初次 scope、App／使用者 ID、取得時間與到期時間僅寫原生憑證庫，沿用分段寫入與逐段讀回。一般設定與 OAuth 狀態不含這些值。
5. IG 分別核對 App-scoped ID、專業帳號 ID、非空 username 與專業帳號類型。Threads debugger 核對使用者、期限與完整 scope，再以 `/me` 核對帳號；回應若提供 App ID、is_valid 或資料存取期限，也必須符合。
6. 全部成功才記 `ready`。交付非敏感狀態、實際已驗證範圍與未驗證功能，不把 Token 交給模型。下游只能在已核准任務中透過 `Runtime.access()` 取得記憶體 Token。

## 有效性、刷新與停止

- 官方長期 Token 通常 60 天；實際期限只採回應值。刷新必須仍有效、且取得至少 24 小時，不能救回過期 Token。這兩條沒有 Google 式 refresh token。
- 本套件在每次使用時先驗證；剩最後七天且 `allow_refresh=True` 才刷新一次。這個七天窗口是本機政策。未授權刷新或未滿 24 小時時仍可使用有效 Token，但剩餘不超過 60 秒就停止，不勉強執行下游任務。
- 刷新前若已撤權或身分不符就停止；刷新後保存新世代並重新讀回。讀回失敗不改回舊 Token。交換／刷新結果不明時不重送，不允許 `resume` 偷做第二次交換。
- 已到期、撤銷或必須重新登入時，告知原因，取得重新授權確認後建立新 state／code。沒有自動開啟授權頁、背景服務或排程。
- `check` 會連平台，需讀取授權；`status` 不讀 Token、不連平台。保存與讀回相同不等於平台仍有效。

## IG 權限證據與逐功能檢查

2026-09-06 重新檢查 Meta 官方 Instagram Login、Instagram API Postman 集合及 Insights 文件。官方列出五項核心功能 scope，但在這條登入路線的已查文件與集合中，**沒有文件化可重新列出全部當前 scope 的正式端點**，也沒有 Instagram Login 專用的 `debug_token` 或 `/me/permissions` 操作。不得用搜尋不到當成平台永遠不會提供；每次實際初始化仍要重新查證。但在有新的官方證據前，不假造端點、不套用 Facebook debugger，也不把第三方工具的推測寫成正式能力。

IG 的完整清單證據只來自初次 code 交換；之後版本化 `/me` 成功只證明當下基本帳號與專業身分可讀取。`ready` 不證明發布、留言、insights 或私訊權限仍在。下游依自己真正要執行的官方端點取得當次功能證據：

| 功能 | 初始 scope | 當次證據與失敗處理 |
|---|---|---|
| 帳號／媒體讀取 | `instagram_business_basic` | `/me` 身分讀回只證明基本讀取；媒體讀取仍由實際 GET 結果判定。 |
| 發布 | `instagram_business_content_publish` | 只有經發布技能核准後的 container／publish 端點結果能證明當次可發布；不能為了測 scope 先建立容器。 |
| 公開留言 | `instagram_business_manage_comments` | 先以實際留言讀取判斷；回覆、隱藏或刪除仍需各自核准與讀回。 |
| 成效 | `instagram_business_manage_insights` | 以實際 insights 查詢判斷；成功空陣列是可用但無資料，不可當成缺權限或零。 |
| 私訊 | `instagram_business_manage_messages` | 先以核准的 conversations 讀取判斷；Send API 仍受對話資格、訊息窗口與另行回覆核准限制。 |

功能端點回傳已知憑證失效時標為 `reauth_required`；明確權限不足時標為 `permission_mismatch`；速率限制與資料空值分開；寫入結果不明時標為 `remote_result_unknown` 並停止，不自動重送。單一功能成功只證明該端點當次可用，不能回填成「全部當前 scope 已驗證」。Agent 必須在初始化交接中保留 `initial_exchange_only` 與 `verify_at_function_endpoint` 兩種證據層級。

Instagram via Facebook Login 是另一條已獨立實作的路線，必須改讀 [Page Token 專用契約](instagram-facebook-login-oauth.md) 並明傳 `login_route`；不能自動切換，或把 Page 身分驗證當成 IG 驗證。

## 官方查證與本機驗證

- [IG Business Login、code、長期交換與刷新](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login/)
- [IG Get Started 與兩種 ID 定義](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started/)
- [Meta 官方 Instagram Login Postman 集合](https://www.postman.com/meta/instagram/folder/1z5vxzu/instagram-api-with-instagram-login)：帳號、發布、留言與私訊的目前 scope。
- [Meta 官方 Instagram Insights](https://www.postman.com/meta/instagram/folder/23987686-f659d7d1-d74c-44e4-9192-9b1e8694c511)：Instagram Login 的 insights scope、空資料與期間限制。
- [Threads code 與授權](https://developers.facebook.com/docs/threads/get-started/get-access-tokens-and-permissions/)
- [Threads 長期 Token 與刷新](https://developers.facebook.com/docs/threads/get-started/long-lived-tokens/)
- [Threads 個人檔案](https://developers.facebook.com/docs/threads/threads-profiles/)
- [Meta 官方 Threads 範例原始碼](https://github.com/fbsamples/threads_api/blob/main/src/index.js)：目前授權網域、表單交換、同 Token 認證 debugger 與回應欄位；不是第三方套件或內部端點。
- [Meta 官方 Threads debugger 範例](https://www.postman.com/meta/threads/request/34203612-e9a7f46e-e48c-4987-a203-22fb25a4b604)

`tests/test_meta_user_oauth.py` 只用虛構記憶體庫及 HTTP 回應，涵蓋兩種交換、權限／ID 差異、過期／刷新窗口、拒絕跨路線與不明結果；不登入、不讀真實秘密、不連平台、不安裝 SDK。真實 TLS callback、OAuth、原生庫、權限與功能讀回待最後集中驗收。
