# 本機憑證儲存

查證日期：2026-09-05。本文件只處理 API 憑證在本機的安全保存與後續取用，不授權建立 App、OAuth、平台讀取或任何遠端寫入。

## 何時讀取

平台整合會建立或取得 App Secret、API key、access token、refresh token、webhook verify token 或其他憑證時讀取。一般策略設定不需要讀取。

## 預設與使用者選擇

使用者沒有指定秘密儲存方式時，預設使用目前登入作業系統帳號的原生憑證庫：

- macOS：登入 Keychain 的 generic password。
- Windows：Credential Manager 的 generic credential，採 `CRED_PERSIST_LOCAL_MACHINE`，供同一位使用者在同一臺電腦後續登入時使用。
- 其他作業系統：目前 MVP 不提供自動降級；停止於取得秘密前。不得改存 `.env`、JSON、一般文字檔或技能目錄，也不得自行安裝 keyring 套件。

外部變更預覽要列出偵測到的 backend、會保存的憑證名稱、持久性、非敏感參照檔，以及未來同一作業系統使用者下的受信任社群 adapter 可以取用。直接告知使用者可以在此時改選既有秘密管理工具或拒絕持久保存；未提出不同選擇即採上述預設。

系統憑證庫提供靜態加密與作業系統使用者層級保護，但不是技能層的權限沙箱。同一作業系統使用者下、獲准執行的程式可能取用憑證。保存成功只代表後續 Agent 不必再次索取憑證，不代表已授權發布、回覆、刪除、傳送私訊或其他遠端寫入。

## 最少人工作業

1. Agent 先以 `credential_store.py inspect` 唯讀辨識 backend，不要求使用者挑選 macOS 或 Windows 的內建選項。
2. OAuth callback、Agent 產生的 verify token，或 Agent 可在不輸出秘密的程式記憶體中取得的值，直接呼叫 `store_secret()` 保存，不要求使用者複製。
3. 平台只在畫面揭露既有 Secret 時，先依下方「受控瀏覽器自動保存」判斷能否不輸出秘密地直接保存。做不到時才在可見的互動式 Terminal 啟動 `put`；使用者只貼一次，輸入不回顯。
4. 小程式不得接受 `--value`、命令列參數、環境變數、pipe 或對話中的秘密。秘密只經過隱藏輸入、程序記憶體與原生憑證庫。
5. 寫入後立即從同一 backend 讀回並在記憶體比對；只輸出平台、憑證名稱、backend、`verified` 與 `contains_credentials: false`。

Keychain 鎖定、Windows 登入工作階段不可用，或作業系統要求解鎖／允許存取時，這是額外的系統安全關卡。Agent 只把當下提示交回使用者，不嘗試降低憑證庫保護或改用明文備援。

## 先盤點再取得：避免重複輸入

- 先對已確認工作區執行 `credential_store.py status`，只讀平台、名稱、available、stored、status；有 Terminal 交接時再核對那份 ticket。程序執行於沙箱的其他 OS 身分時，存取遭拒不能解讀為「使用者沒保存」。先透過工具允許的權限流程，以正確 OS 使用者查核，不改 ACL、不轉存明文。
- 明確區分 App Secret、OAuth access token、測試後台 Token，以及本機 TLS 私鑰。它們不是同一筆資料；Facebook／Instagram／Threads 的專用 App ID 和秘密也不能互換。只在使用者已指定的工作區與 App 範圍核對，不能廣搜其他帳號憑證。
- `available: true` 且來源符合的 Secret 直接沿用；既有 OAuth 逾時只重建已獲准的 state／code，不重新索取 Secret。遇到 `pending_write` 走恢復流程，不重新開另一個輸入視窗。
- `unknown_check_registry` 表示收據逾時或程序狀態未知，不表示原生庫沒有值。先查 registry 和原生存在性；兩者均無保存證據才標為缺少。
- 將真正需要的人工作業和一般許可分開：密碼重新驗證／2FA 是登入關卡，不是請使用者再複製一次 Secret；完成後由 AI 接續取值、保存和驗收。新的敏感存取仍遵守所用工具的當下確認規則，既有授權不重問。

## 受控瀏覽器自動保存

`credential_browser.py` 接收使用者已授權保存、但尚未存在於原生庫的單筆既有秘密。它不是 OAuth code 接收器，不重設 App Secret，也不接受覆蓋旗標。先核對指定 App、平台、欄位、原生庫及程式可用；只有瀏覽器工具能將欄位值留在執行器記憶體並抑制秘密輸出時才使用。

```text
python scripts/credential_browser.py --workspace-root <私人工作區> --platform threads --name app-secret --origin https://<已信任的本機.test網域>:<port> --tls-cert <既有憑證> --tls-key <既有私鑰> --confirm-store
```

1. 沿用已核准的 HTTPS、hosts 與憑證，接收器固定監聽 `127.0.0.1`。只支援本機 `.test`、localhost 或 loopback origin，不開通公開服務或降低 TLS 驗證。不要與同 port 的 OAuth 接收器同時執行。
2. 確認回傳的表單包含正確平台及名稱後，才傳入秘密。先前同名項目存在時會拒絕啟動；不能因此刪掉原生值或換名稱繞過核對。
3. 使用受控瀏覽器的可見 DOM 欄位讀取，將值保留在工具執行器記憶體；只輸出欄位是否可用，不回傳值、長度、截圖、原始 AX／DOM、錯誤本文或完整表單。不得讀取隱藏應用程式狀態、Cookie、剪貼簿或拼湊後台內部 API。平台要求密碼／2FA 時保留當下頁面，不搜尋其他密碼來源，也不反覆啟動接收器等待逾時。
4. 在同一受控工具程序將記憶體值填入本機表單的 password 欄位，經一般表單 POST 保存；不把值放進命令列、URL、環境變數、pipe 或檔案。表單使用精確 Host、同源 Origin、CSRF、15 分鐘有效期、單次提交與大小限制，不載入外部資源。填入秘密後不擷取表單；不因導向逾時重送 POST。
5. `store_secret()` 完成原生讀回比對才呈現 `verified`，接收器導向無秘密的結果頁並結束。釋放瀏覽器執行器中的值、關閉秘密來源與輸入分頁；重新以 status 核對。任何不明保存結果都先查 registry，不能盲目重送。

此路徑已有虛構 backend、HTTP 邊界與 TLS 表單載入測試；不代表所有平台的秘密取得或 macOS 實機保存均已驗收。Meta 密碼重驗是已觀察到的額外關卡，不能承諾完全無需本人登入。

可見 Terminal 的命令形式如下；`<skill-directory>` 與 `<workspace>` 由 Agent 依實際安裝位置填入，命令本身不包含秘密：

```text
python3 <skill-directory>/scripts/credential_store.py put \
  --workspace-root <workspace> \
  --platform facebook \
  --name app-secret
```

Windows 可依已安裝 Python 入口使用 `py` 或 `python`。不要叫使用者自行尋找腳本。Agent 預設使用同目錄的 `credential_terminal.py launch` 開好 Terminal；`credential_store.py put` 是已經在可見 Terminal 中時的直接入口。若沒有真正可互動的 Terminal，停止，不得用非互動 pipe 模擬輸入。

```text
python3 <skill-directory>/scripts/credential_terminal.py launch \
  --workspace-root <workspace> --platform facebook --name app-secret --confirm-store
python3 <skill-directory>/scripts/credential_terminal.py status \
  --workspace-root <workspace> --ticket <launch-returned-ticket>
```

`--confirm-store` 只能在使用者確認保存預覽後使用。取代既有值要在預覽列出並另外加 `--confirm-replace`。macOS 使用系統 Terminal，Windows 開啟新的 Python console；若 macOS 要求允許控制 Terminal，由使用者決定，不降低系統保護。

啟動器回傳的 `waiting_for_input` 只代表已安排輸入；只有子程序完成原生寫入及讀回比對，收據才成為 `verified`。Agent 用回傳的 ticket 查詢狀態，不讀 Terminal 畫面、剪貼簿或秘密值。`stopped`、`launch_failed` 或逾時後的 `unknown_check_registry` 都不能當成功，也不能自動重開視窗；先檢查憑證 `status`。收據有效 15 分鐘、只能啟動一次，僅含平台、名稱、作業類型、非敏感確認旗標及狀態，不是新增操作授權。Terminal 關閉或程序中斷時，不保證有最終收據。

使用者從平台複製再貼上時，值可能短暫存在作業系統剪貼簿；Agent 不讀取或列印剪貼簿，也不把值貼進對話。是否清除作業系統本身的剪貼簿歷程由使用者依自己的環境決定。

## 本機參照與後續取用

秘密值只在 Keychain 或 Credential Manager。工作區的 `.local/social-media/credential-references.json` 只保存：

- 隨機 namespace。
- backend 名稱。
- 平台與憑證名稱，例如 `facebook/app-secret`。
- 來源類型、最後讀回驗證時間與 `contains_credentials: false`。

參照 schema 為第 2 版，舊版 `verified` 參照可讀取，下次經確認的變更才寫成新版。`pending_write` 與 `pending_delete` 表示作業未完成，不允許後續 adapter 取用。`available` 表示已驗證且仍存在；`stored` 只表示原生項目存在，兩者都不是平台有效性證明。

參照檔不得保存 App ID、Page ID、帳號、Token、秘密值、Keychain 完整輸出或私人平台網址。未來平台 adapter 從受管理的 `credential_store.py` 匯入 `load_secret()`，在程序記憶體取用需要的值；不得新增會把秘密印到 stdout 的 `get` 命令，也不得用通用除錯輸出列印 request header、環境變數或完整平台回應。

使用者提出社群管理或發布任務後，對應技能可以把讀取已保存憑證當作完成該任務的內部步驟，不需再次要求使用者貼上。該技能仍須依自身契約取得遠端動作確認，並且只載入被選取平台與功能需要的憑證。

## 更新、遺失與移除

- 同名憑證存在時預設停止。只有預覽已說明將取代，而且使用者確認後，互動命令才可加上 `--confirm-replace`；OAuth 自動更新也必須在已核准流程內明確傳入 `replace=True`。
- registry 有參照但原生憑證不存在時，狀態回報 `available: false`，停止 API 任務並重新走安全取得流程；不得猜測或改用其他帳號的憑證。
- 技能安裝器的 `remove` 不會刪除作業系統憑證。刪除憑證是另一個破壞性動作，先用 `status` 確認單一目標，再取得使用者明確同意，最後以 `remove --confirm-delete` 刪除該筆及其參照。
- 工作區移到另一臺電腦時，參照檔不能取代憑證遷移；另一臺電腦必須重新 OAuth 或由使用者明確選擇安全遷移方式。

### 中斷恢復

程式先寫入非敏感待辦狀態，再寫入或刪除原生憑證；同一工作區使用程序鎖，第二個修改程序立即停止、不排隊重送。

- `pending_write` 且原生值存在：不能只憑存在性標成功。若原 OAuth 程序仍持有預期值，在使用者確認恢復後呼叫 `recover_secret(..., confirmed=True)` 做記憶體比對；不再次寫入憑證庫。人類持有原值時，用 Terminal launcher 的 `--operation recover --confirm-store` 開啟隱藏輸入，或在既有 Terminal 執行 `credential_store.py recover --confirm-recovery`。
- 不知道預期值、讀回不一致或值不存在：保留未完成狀態，先說明情況；重新取得／取代需要新的明確確認。不得重跑 OAuth 交換來猜測上一筆結果。
- `pending_delete`：再次確認刪除同一筆後執行 `remove --confirm-delete`；先檢查存在性，值已不在時只完成該筆參照移除，不再送第二次刪除。
- 鎖檔與 `.local/social-media/credential-input/` 的收據只供本機協調；安裝器不刪除它們，不含秘密。程序結束會釋放作業系統鎖，不需要手動刪鎖檔。

本 helper 只處理本機保存與恢復；平台到期、撤銷、交換與更新交給 [OAuth 執行器](oauth-runtime.md)。Facebook Pages、YouTube、Instagram Login、Instagram via Facebook Login、Threads 五條路徑已有程式與虛構測試，後續技能必須透過其 `Runtime.access()` 讀回驗證；不能因原生 `verified` 就宣稱平台憑證可長期使用。Instagram Login／Threads 使用各自專用交換與刷新，Instagram via Facebook Login 使用相連 Page Token 且不套用其他刷新，真實原生庫與 OAuth 均留到最後驗收。

## 驗證邊界

公開候選版可用虛構 backend 驗證新增、讀回、取代、刪除、registry 不含秘密、非互動輸入拒絕與 symlink 停止。macOS Keychain 與 Windows Credential Manager 必須分別在真實作業系統完成寫入、重開程序後讀取與移除測試，才能宣稱該平台的原生儲存已實測。

目前依開發順序，所有工具包完成後才集中實機驗收。預設測試不啟動原生 Terminal、不存取 Keychain／Credential Manager；現有 macOS 唯讀探測也預設略過。`SOCIAL_NATIVE_ACCEPTANCE=1` 只用於另行獲准的實機驗收，不是授權替代。

## 官方來源

- [Apple Keychain items](https://developer.apple.com/documentation/security/keychain-items)
- [Apple generic password item](https://developer.apple.com/documentation/security/ksecclassgenericpassword)
- [Microsoft CredWriteW](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritew)
- [Microsoft CredReadW](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credreadw)
- [Microsoft CREDENTIAL structure](https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentialw)
- [Python `getpass`](https://docs.python.org/3/library/getpass.html)
