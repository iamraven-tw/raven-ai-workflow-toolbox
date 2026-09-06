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
3. 平台只在人類可見畫面揭露 App Secret 或 API key，而且讓 Agent 讀取會使秘密進入畫面記錄、對話或工具輸出時，Agent 在可見的互動式 Terminal 啟動 `put`。使用者只把值貼入一次；輸入不回顯。
4. 小程式不得接受 `--value`、命令列參數、環境變數、pipe 或對話中的秘密。秘密只經過隱藏輸入、程序記憶體與原生憑證庫。
5. 寫入後立即從同一 backend 讀回並在記憶體比對；只輸出平台、憑證名稱、backend、`verified` 與 `contains_credentials: false`。

Keychain 鎖定、Windows 登入工作階段不可用，或作業系統要求解鎖／允許存取時，這是額外的系統安全關卡。Agent 只把當下提示交回使用者，不嘗試降低憑證庫保護或改用明文備援。

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
