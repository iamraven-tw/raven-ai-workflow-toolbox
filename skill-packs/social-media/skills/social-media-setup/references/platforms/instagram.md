# Instagram 平台初始化

查證日期：2026-09-06。Instagram 權限、登入路線與 App Review 會變動，實際設定前重查官方文件。

執行本文件前先讀 `../meta-api-setup.md`。使用者只要選取 Facebook、Instagram 或 Threads 任一平台，就在同一次 Meta 初始化中詢問是否也設定另外兩個；共用的是引導、盤點與預覽，不預設三者共用同一個 App、OAuth、Token 或驗證結果。

## 帳號與登入路線

官方目前有兩條不可混寫的整合路線：

1. **Instagram Login**：專業帳號可直接授權，不要求先連結 Facebook 粉絲專頁；使用 Instagram User access token 與 `graph.instagram.com`。
2. **Facebook Login**：Instagram 專業帳號必須連結使用者可管理的 Facebook 粉絲專頁；使用 Facebook User／Page access token 與 `graph.facebook.com`。

一般消費者帳號不屬於這些專業 API 的支援對象。Agent 應先根據人類提供的帳號類型、Page 連結狀態與實際所需功能（有連線時再以正式 API 讀回），再推薦路線；若使用者同時設定 Facebook Page，仍不得只因帳號相連就假定 Facebook Login 必然較適合。

## 預設完整核心權限

使用者選取 Instagram 且沒有明確縮小功能時，預設請求帳號讀取、內容發布、公開留言管理、成效與私訊所需的完整核心權限。必須在 OAuth 前顯示實際 scope 名稱、用途與限制；取得 scope 不代表已授權立即發文、刪除留言或傳送私訊。

### Instagram Login 路線

| 核心功能 | permission | 用途 |
|---|---|---|
| 帳號與媒體讀取 | `instagram_business_basic` | 讀取專業帳號與其媒體的基本資料。 |
| 發布 | `instagram_business_content_publish` | 建立並發布支援的 Instagram 內容。 |
| 公開留言 | `instagram_business_manage_comments` | 讀取、回覆及管理專業帳號媒體留言。 |
| 成效 | `instagram_business_manage_insights` | 讀取專業帳號與媒體 insights；空資料不得當成 0。 |
| 私訊 | `instagram_business_manage_messages` | 存取與回覆使用者先發起的 Instagram 對話。 |

### Facebook Login 路線

| 核心功能 | permission | 用途與相依 |
|---|---|---|
| Page 與帳號關係 | `pages_show_list`、`pages_read_engagement`、`instagram_basic` | 找到使用者管理的 Page 與相連的 Instagram 專業帳號，並讀取基本媒體資料。 |
| 發布 | `instagram_content_publish` | 建立並發布支援的 Instagram 內容。 |
| 公開留言 | `instagram_manage_comments` | 讀取、回覆及管理媒體留言。 |
| 成效 | `instagram_manage_insights` | 讀取專業帳號與媒體 insights；需要 `instagram_basic` 與 `pages_read_engagement`。 |
| 私訊 | `instagram_manage_messages`、`pages_manage_metadata` | 存取 Instagram 對話；需要相連 Page、具 `MESSAGING` 工作權限的 Page token，且官方目前要求 App 所屬企業通過驗證。 |

如果帳號透過 Business Manager 角色授予，而不是直接具有 Page 角色，部分 insights 路徑可能另需 `ads_management` 與 `ads_read`。這兩項不得因名稱相近而默默加入；Agent 必須說明原因並取得使用者確認。

Instagram Login 目前不支援廣告或標註能力。使用者選取這些延伸功能時，應重新評估 Facebook Login／Marketing API 或其他官方路線，而不是把額外 scope 塞進不支援的登入路線。

## 功能與限制

| 功能 | 官方能力 | 初始化與後續驗證重點 |
|---|---|---|
| 發布 | 圖片、影片、Reels 與輪播採 media container，再查狀態並 publish | 帳號類型、媒體可取用性、container 狀態與發布後 permalink；每次寫入仍另行確認。 |
| 公開留言 | 讀取、回覆、隱藏／取消隱藏、刪除與留言控制 | Webhook 與輪詢分開；逐則操作後讀回。 |
| 成效 | 帳號與媒體 insights | 指標窗口、帳號擁有關係與缺值狀態；部分帳號／指標門檻可能回空資料。 |
| 私訊 | Send API、Conversations API 與 Webhook | 對話必須由 Instagram 使用者先發起；一般回覆受官方目前的 24 小時訊息窗，以及收件匣、群組訊息與支援內容限制。 |

- 官方內容發布目前限制每個專業帳號在滾動 24 小時內最多 100 個 API 發布內容；實作前重新查閱端點與帳號層限制。
- 標準媒體 URL 流程通常要求平台可公開抓取媒體；不可把私人本機路徑直接當成可上傳 URL。
- container 建立成功後要輪詢處理狀態，再發布；發布後再以回傳 ID 讀回 permalink、時間與媒體狀態。
- 私訊權限屬預設核心，但使用者沒有先傳訊、超出目前 24 小時標準訊息窗或不符合政策時，不得傳送；執行時仍要重查當下規則與可能適用的例外。取得 OAuth scope 也不等於已完成私訊實測。
- 非 App 角色帳號通常需要 Advanced Access 與 App Review；測試者可用不代表公開使用者可用。

## 初始化與驗證

1. 先把 Instagram 與同輪選取的 Facebook／Threads 放進一份 Meta 外部變更預覽，但逐平台列出 App/use case、permission、OAuth 與必要審查。
2. 使用者可在 OAuth 前刪除任何核心 permission；刪減後把 Instagram 記為 `custom`，並列出失去的功能。
3. Agent 依實際帳號關係提出登入路線與完整文字步驟，由人類完成 App、callback、產品／use case 與 permission 設定。
4. 使用者本人完成必要登入、安全驗證、條款與 OAuth 同意；Agent 不要求使用者把 Secret、授權碼或 Token 貼進對話。
5. Instagram Login 使用 [專用 OAuth 程式](../instagram-threads-oauth.md)，核對初次交換 scope、當前專業帳號類型及兩種 ID。2026-09-06 查證的官方資料沒有文件化全部當前 scope 重新列舉介面；交接必須標成初次授權證據，並由發布、留言、成效與私訊的實際功能端點各自驗證。Facebook Login 使用 [Page Token 專用程式](../instagram-facebook-login-oauth.md)，核對 Facebook User、唯一相連 Page、Page Token 與 Instagram 帳號；不能借用 Facebook Page 的目標身分驗證。
6. 只把實際完成的 App、OAuth 與安全唯讀資源讀回標為已驗證。發布、留言寫入、insights 查詢與私訊收發分別等待後續技能實測。

## 官方來源

- [Meta 官方 Instagram API workspace](https://www.postman.com/meta/instagram/overview)
- [Instagram API with Instagram Login](https://www.postman.com/meta/instagram/folder/6raa77c/instagram-api-with-instagram-login)
- [Instagram API with Facebook Login](https://www.postman.com/meta/instagram/folder/u4g5a2a/instagram-api-with-facebook-login)
- [Instagram Insights 權限對照](https://www.postman.com/meta/instagram/folder/23987686-f659d7d1-d74c-44e4-9192-9b1e8694c511)
- [Meta 官方 Instagram API 文件集](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)
- [Meta App Review](https://developers.facebook.com/docs/app-review/)
