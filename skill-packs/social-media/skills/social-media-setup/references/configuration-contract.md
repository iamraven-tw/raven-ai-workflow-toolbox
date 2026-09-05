# 設定契約

## 正式路徑

- 一般設定：`social-media/config.json`
- 非敏感狀態：`.local/social-media/setup-state.json`
- 非敏感憑證參照：`.local/social-media/credential-references.json`

前三者都相對於使用者明確指定的工作區。憑證參照由 `scripts/credential_store.py` 依 `credential-references.schema.json` 管理，只保存隨機 namespace、原生 backend、平台／憑證名稱與驗證時間；秘密值只存在 macOS Keychain、Windows Credential Manager 或使用者另行指定的安全儲存。不得使用目前 shell 位置猜測工作區。

## 一般設定

設定使用 `schema_version: 3`，必須符合 `social-media-config.schema.json`，只包含：

- 策略狀態、目標、受眾、內容主題、平台角色與策略來源相對路徑。
- 五個平台的選取狀態、請求功能、授權模式、已確認／拒絕的 permission、偏好介面、整合狀態與最後實際驗證時間。

平台被選取後，`authorization_profile` 預設為 `full_management`；只有使用者明確縮小權限或只要求單一功能時才使用 `custom`。`requested_permissions` 記錄 OAuth 前確認的實際 permission／scope 名稱，`declined_permissions` 只記錄使用者明確要求移除的項目。兩個清單不得重複，且不得包含 Token、App／資源 ID 或憑證位置。未選取的平台固定使用 `not_selected` 與兩個空清單。

Facebook、Instagram 與 Threads 可在一次 Meta 初始化中一起規劃，但三筆整合紀錄仍分開保存。共用預覽不代表共用 App、OAuth、Token 或驗證結果。

`account_read` 代表只驗證帳號與平台資源可由正式介面讀取，不等於貼文、留言、成效或任何寫入功能可用。每個平台必須分別保存：

- `verification.api_app`：API／開發者 App。
- `verification.user_auth`：使用者登入／OAuth。
- `verification.platform_read`：平台資源讀回。
- `verification.remote_write`：發布、回覆或其他遠端寫入。

`status: verified` 只表示 `platform_read: verified`，不表示 `remote_write` 已通過。`last_verified_at` 只有在同一輪取得平台讀回或遠端寫入證據時才能填入；不能以設定時間代替。遠端寫入未要求、未授權與未測試必須分開。

## 預覽與套用

候選檔先由 `preview` 驗證。預覽雜湊同時綁定候選內容、正式設定目前內容與目標工作區；因此任何一項在確認前改變，`apply` 都會停止。套用採原子替換，並在寫入後重新讀回。

既有正式設定不會因執行 `preview` 變動。`apply` 必須有使用者對同一份預覽的明確確認；命令列的 `--confirm-write` 只用來避免程式誤呼叫。

## 禁止欄位

任何層級的鍵名包含 Token、secret、password、Cookie、credential、API key、client ID／secret、App／Page／Account／Channel ID 或 credential path 時拒絕。常見 Bearer token、JWT、私鑰與帶認證查詢參數的 URL 也拒絕。

如果某平台操作需要這些值，只能在實際執行時從外部變更預覽列出的秘密儲存取用，不得先抄入候選設定。使用者沒有另行指定時，依 `local-credential-storage.md` 預設使用作業系統原生憑證庫；這項預設不授權任何遠端寫入。
