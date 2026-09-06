# Meta API 實際初始化

查證日期：2026-09-05。本文件處理 Facebook、Instagram 與 Threads 共用的 Meta 開發者後台作業；平台帳號關係、權限與驗證請求仍以各自平台文件為準。

## 何時讀取

只在使用者選取 Facebook、Instagram 或 Threads 的平台整合模式時讀取。先確認目標資源，再選 App use case 與登入路線；不要把「Meta API」視為單一產品，也不要因使用者已登入 Facebook 就推定 Instagram 或 Threads 已授權。

## Meta 三平台合併初始化

Facebook、Instagram 與 Threads 都從 Meta 開發者平台開始，因此使用者選取其中一個平台時，Agent 應在同一次設定對話中詢問是否一併設定另外兩個。使用者同意後：

1. 以一份總預覽列出三個平台各自的目標資源、App／use case、登入路線、permission、callback、審查與驗證請求。
2. 依目前後台實際支援情況判斷可否使用同一個 Meta App；不可預設一定共用，也不可為了減少步驟把不相容 use case 塞入同一 App。
3. 即使共用 Meta 開發者帳號或某個 App，也要分開處理各平台可能不同的 App ID／Secret、OAuth、Token、permission 與資源關係。
4. 使用者可用一次對話確認授權總預覽內列出的 App 與後台設定；Meta 若要求多個 OAuth 同意畫面，仍逐一交回使用者親自確認。
5. 每個平台分別讀回並保存驗證狀態。一個平台失敗、未審查或未測試，不影響其他平台已取得的真實證據，也不能被其他平台的成功取代。

## 執行前檢查

Agent 在要求使用者登入前完成以下唯讀工作：

1. 重查選定平台所有核心功能的官方文件、Graph API 版本、permission、相依 permission、Standard／Advanced Access、App Review 與 Business Verification 條件。
2. 確認目標資源種類與可辨識名稱，例如 Facebook Page；若使用者尚未指定唯一目標，只問這一題。
3. 確認環境具有可由 Agent 操作的受控瀏覽器。公開技能不得硬編維護者的瀏覽器名稱、Profile 或擴充套件路徑。
4. 確認有符合當下 Meta 規則的 OAuth callback。若需要公共 HTTPS、正式網域或額外服務，不得自行安裝、部署或開通；先回報缺口並取得授權。
5. 讀取 `local-credential-storage.md`，執行 `credential_store.py inspect`。使用者沒有另行指定時，預設採目前作業系統帳號的 macOS Keychain 或 Windows Credential Manager，並確認可在不把值放入對話、命令列參數、一般設定或日誌的情況下保存 App Secret 與 Token。

任一項不成立時仍可提供本機預覽，但不可進入秘密揭露或 OAuth Token 階段。

## 外部變更預覽

點擊建立 App 前顯示並確認：

- 選定平台、功能與目標資源。
- 將建立或修改的 Meta App，以及目前後台顯示的 use case／產品名稱。
- App 擁有者或 Business portfolio 關係；不確定時不得自動選擇。
- 完整核心 permission、每項用途、讀寫影響、相依關係及使用者要求移除的 permission。
- 平台自動附帶的基本身分 permission，以及不屬於核心但可選的廣告、企業、商務、商品與其他延伸 permission。
- OAuth callback 類型、偵測到的原生憑證庫、預計保存的憑證名稱，以及未來受信任 Agent adapter 可取用的範圍；不顯示私人完整目標名稱或秘密值。
- AI 將執行的後台動作、使用者必須處理的關卡、各功能驗證請求與停止條件。
- App Review、Business Verification、公開使用者支援與遠端寫入測試是否排除在本輪之外。

預覽最後直接告知：「以上是我準備申請的權限。如果有任何一項不想開放，請現在告訴我；我會在 OAuth 前移除，並說明哪些功能會因此無法使用。」

預覽確認只授權其中列出的動作。後台沒有預期 use case、要求更多權限或出現未列出的 Business portfolio 時停止並重新預覽。

## 最小人工介入流程

### 1. Agent 開啟並檢查後台

Agent 開啟 Meta for Developers 的 Apps 頁面，讀取畫面上可見的登入狀態與帳號標籤。已登入時仍要確認它符合預覽中的 App 擁有者；不可切換帳號、讀取 Cookie 或從密碼管理工具取得密碼。

### 2. 人工關卡一：身分、安全與法律同意

只有遇到下列畫面才交回使用者：

- Facebook／Meta 帳號登入、Passkey、2FA 或驗證碼。
- 首次開發者註冊與平台條款接受。
- 密碼重新驗證、身分驗證或企業資料證明。
- 多帳號或多 Business portfolio 且無法依已確認目標唯一判斷。

Agent 應先開到正確頁面，只要求使用者完成當下畫面。使用者完成後，Agent 從同一頁繼續。

### 3. Agent 建立並設定 App

取得外部變更授權後，Agent 負責：

1. 點擊建立 App，填入已預覽的顯示名稱與必要非敏感欄位。
2. 選取符合目前官方文件的 use case／產品；不得依舊版 UI 名稱盲選相似項目。
3. 只在預覽已確認時關聯 Business portfolio 或其他資產。
4. 設定 OAuth redirect URI、必要網域、測試角色、完整核心 permission 與使用者明確選取的延伸 permission。
5. 讀回 App 畫面，確認實際 App、use case／產品與 redirect 設定符合預覽。

App ID 與資產 ID 是私人連線資料，不能寫入公開套件或一般設定。App Secret 只能送入外部變更預覽中的秘密儲存；若顯示 Secret 需要重新驗證密碼，回到人工關卡一。Meta 只在人類可見畫面揭露 Secret、而 Agent 讀取會讓值進入畫面記錄或工具輸出時，Agent 開啟可見互動式 Terminal 並啟動 `credential_store.py put --platform facebook --name app-secret`；使用者只貼上一次，輸入不回顯。不得要求使用者把值貼進對話或命令列。

### 4. 人工關卡二：OAuth 同意

Agent 建立含防偽 `state` 的授權請求並開啟官方 OAuth 畫面。使用者本人確認：

- 目前登入帳號正確。
- 目標 Page、Instagram 專業帳號或 Threads 帳號正確。
- permission 與預覽一致，沒有多要求權限。

使用者完成同意後把控制權交回 Agent。Agent 不代按 OAuth 同意，也不引導使用者把授權碼貼入對話。

### 5. Agent 完成 Token 與讀回驗證

Facebook Pages 使用 [OAuth 執行器](oauth-runtime.md) 的 HTTPS Web server code flow；不得混用 Native/Desktop App。Agent 驗證 callback 的 `state`、錯誤與目標，再依官方流程交換 Token，並透過 `credential_store.py` 的 `store_secret()` 保存選定 Page Token，不增加人工複製。短期及長期 User Token 僅作交換與權限核對，不持久保存。Token、授權碼與 Secret 不得出現在 stdout、錯誤訊息、對話、一般設定或 URL 日誌；官方 GET 所需秘密參數只在本機受控程序內經 HTTPS 傳送，不能當成瀏覽器網址開啟。寫入後必須由同一 backend 讀回比對，並以非敏感參照與 OAuth 狀態記錄結果。Instagram Login／Threads 改用 [專用交換與刷新契約](instagram-threads-oauth.md) 的各自 User Token 流程；Instagram via Facebook Login 使用 [專用 Page Token 契約](instagram-facebook-login-oauth.md)，核對 Facebook 使用者、唯一相連 Page 與 IG 帳號，不能把單純 Page 驗證當成 IG 驗證。

接著先呼叫平台文件指定的唯讀端點，並核對：

- 實際帳號與目標資源。
- 已授權 permission 或可觀察的資源 tasks。
- Token 類型與可判斷的有效期限。
- API 回應時間、Graph API 版本、HTTP／平台錯誤與是否完整分頁。

取得寫入 permission 不代表寫入功能已驗證，也不授權本技能發布、回覆、傳送私訊或變更廣告。這些測試留給對應技能另行預覽與確認。

結果為空、權限不足、資源不唯一、帳號不符、callback `state` 不符或結果不明時停止。不得自動加權限、切換帳號或重跑 OAuth。

## 狀態與證據

每一層獨立回報，不用單一「已連接」概括：

1. `developer_account`：未檢查／需要使用者／已讀回。
2. `developer_app`：未建立／已建立未讀回／已讀回設定。
3. `oauth`：未設定／等待同意／已取得且安全保存／失敗或不明。
4. `platform_read`：未執行／目標資源已讀回／空資料／權限不足／失敗／不明。
5. `remote_write`：未要求／未授權／未測試／已另行驗證。
6. `public_support`：Development／App 角色測試、App Review、Business Verification 與公開使用者支援分開。

設定頁、App ID、Token 產生畫面或 HTTP 200 都不能單獨證明目標平台可讀。證據輸出只保存非敏感摘要、實際時間、API 版本、已授權 permission 名稱、資源類型與遮蔽後識別資訊。

## 官方來源

- [建立 Meta App](https://developers.facebook.com/docs/development/create-an-app/)
- [Meta App Review](https://developers.facebook.com/docs/app-review/)
- [Meta permissions](https://developers.facebook.com/docs/permissions/)
- [Meta 官方 Facebook API workspace](https://www.postman.com/meta/facebook/overview)
- [Meta 官方 Instagram API workspace](https://www.postman.com/meta/instagram/overview)
- [Meta 官方 Threads API workspace](https://www.postman.com/meta/threads/overview)
