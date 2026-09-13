# 第 8 課：Web App／Webhook

## 本課成果

使用者會親自部署一個公開測試 Web App，以實際 `/exec` 網址查看系統狀態；取得確認後，由 Agent 使用本機安全測試工具對該網址送出四個真實 POST，驗證正常、錯誤與重送情境。使用者只需查看 UI 與結果，不必逐項操作測試函式。試算表只新增一筆假資料，完成後封存公開測試 deployment。

## 課前簡介（Agent 必須先說）

這一課替完整系統增加外部入口：瀏覽器可用公開 Web App 查看狀態，測試 Webhook 可把通過驗證的假報名寫入同一份試算表，重送同一個`requestId`不會新增第二筆。`SPREADSHEET_ID`沿用第 2 課；`WEBHOOK_TOKEN`先由 Agent 使用本機安全亂數產生一組只供本課使用的臨時教學密語，學生親自填入且不回傳，並學會日後自行產生正式值；`WEB_APP_URL`則來自學生完成部署後取得的版本化`/exec`網址，讓測試函式知道要呼叫哪個入口。Agent 要先解釋這些設定的來源、用途與放在 Script Properties 的理由，再引導設定。Agent 負責本機安全測試，並在另行確認後對實際網址送出四個 POST；學生負責另行確認公開部署、查看 GET／POST、試算表與`執行項目`，最後另行確認並封存 deployment。公開網址會讓任何人都能送出請求，但只有正確 Token 可通過；本課只用假資料，不接收真實個資、付款資料、密碼或 OAuth Token。

## 核心概念

1. `doGet(e)` 處理瀏覽器或 HTTP GET；`doPost(e)` 處理 HTTP POST。
2. 公開網址收到的資料一律先檢查，再決定是否寫入。
3. Webhook 可能重送；相同 `requestId` 不可新增第二筆資料。
4. 綁定型指令碼以 Web App 執行時沒有目前開啟的試算表情境，因此
   Webhook 必須用第 2 課已核對的 `SPREADSHEET_ID` 明確開啟目標，
   不能沿用 Sheets 選單中的 `getActiveSpreadsheet()`。

本課主要檔案是 `08_WebApp.gs`；共用紀錄檔(Log)沿用 `00_Log.gs`。使用者不需要理解 HTTP 或 JSON 的程式語法。

## Agent 實作

- 將 Web App、Webhook、回應與測試輔助函式集中在 `08_WebApp.gs`。
- `checkLesson08Settings()` 從 Sheets 選單執行時仍核對目前綁定檔案；
  `doPost(e)` 則使用 `SpreadsheetApp.openById()` 與既有
  `SPREADSHEET_ID`，因為 Web App 執行時綁定檔案特殊方法不可用。
- `doGet(e)` 只回傳簡單繁體中文 JSON 狀態，不輸出設定值、帳號、資料筆數或內部錯誤。
- `doPost(e)` 依序完成：
  1. 確認有 POST 本文，並限制可接受的內容類型與小型教學資料大小。
  2. 安全解析 `e.postData.contents` 的 JSON。
  3. 從 JSON 本文取得測試 Token，與 Script Properties 的 `WEBHOOK_TOKEN` 比較；兩者都不得寫入紀錄檔(Log)。
  4. 驗證 `requestId`、姓名、Email、活動場次與資料來源。
  5. 使用 `LockService` 防止同時寫入，並保證在 `finally` 釋放鎖。
  6. 依 `requestId` 查找既有資料，確認不存在才批次寫入 Sheets。
  7. 回傳 `ok`、`code` 與繁體中文 `message`。
- Token 不放網址查詢參數，也不要求使用者交給 Agent。
- 對外回應不得包含 stack trace、Script ID、Deployment ID、屬性值、內部檔案名稱或原始例外。
- Apps Script `TextOutput` 沒有自訂 HTTP 狀態碼的介面；本課使用應用層 `code` 區分結果，例如：
  - `READY`
  - `OK`
  - `INVALID_JSON`
  - `INVALID_TOKEN`
  - `INVALID_DATA`
  - `DUPLICATE`
  - `BUSY`
- 只建立以下給使用者操作的入口：
  - `checkLesson08Settings()`
  - `runLesson08LocalTests()`
  - `runLesson08RemoteTests()`
- `runLesson08LocalTests()` 使用假的 Token、設定與事件，驗證解析、欄位、驗證失敗、鎖定與去重邏輯；不得寫入真實 Sheets，也不得送出 HTTP 請求。
- `runLesson08RemoteTests()` 從 Script Properties 讀取 `WEB_APP_URL` 與 `WEBHOOK_TOKEN`，使用 `UrlFetchApp` 對實際 `/exec` 網址依序送出：
  1. 無效 JSON。
  2. 錯誤的假 Token。
  3. 一筆包含真實測試 Token 的有效假資料。
  4. 使用相同 `requestId` 重送有效假資料。
- 遠端測試只記錄回應的 `ok`、`code` 與中文說明，不記錄 URL、Token 或完整請求本文。
- 網頁應用程式(Web App)部署不是可執行 API 部署，不能預設透過 `clasp run` 呼叫 `runLesson08RemoteTests()`。正常教學路徑由 Agent 在取得確認後執行技能包的 `scripts/run_lesson08_webhook_tests.py`；網址與臨時教學密語都使用隱藏輸入，不出現在命令、終端輸出或檔案。`runLesson08RemoteTests()`保留為 Apps Script 內部除錯入口，不交給學生操作，也不為它另外建立可執行 API 部署。

`doGet` 與 `doPost` 會出現在函式選單，但它們只供實際 Web App 呼叫。Agent 必須提醒使用者不要在編輯器手動選擇這兩個函式。

## Script Properties

| 名稱 | 用途 | 敏感性 |
|---|---|---|
| `SPREADSHEET_ID` | 寫入通過驗證的測試資料 | 非密碼，沿用第 2 課設定 |
| `WEBHOOK_TOKEN` | 驗證測試 Webhook 來源 | 敏感；本課由 Agent 提供臨時教學值，學生自行輸入 |
| `WEB_APP_URL` | 指定版本化 deployment 的 `/exec` 網址 | 非密碼，仍不寫入程式、紀錄檔(Log)或 Git |

### `WEBHOOK_TOKEN`

Agent 在進入本步驟時，使用本機安全亂數產生 64 個十六進位字元，作為只供當次課程使用的「臨時教學密語」，並在私人教學對話中顯示一次。Agent 必須明確告訴學生：這個值因已出現在對話中，只適合本課測試，不適合作為正式秘密。學生直接把它輸入 Apps Script「專案設定」的「指令碼屬性」，依序點擊「編輯指令碼屬性」及「新增指令碼屬性」，輸入後點擊「儲存指令碼屬性」；不得把值回傳給 Agent。

Agent 同時告訴學生，正式使用或想更換密語時可以採用下列任一方式自行產生：

- 密碼管理器的密碼產生器，例如 1Password、Apple「密碼」或 Bitwarden。
- 作業系統或可信任軟體提供的本機安全亂數產生器。
- 在自己的終端機執行 `openssl rand -hex 32`，產生 64 個十六進位字元。

不得使用不明網站代為產生，不得重用 Google 密碼、OAuth Token、其他服務密碼或正式秘密。臨時權杖(Token)只放在私人教學對話與 HTTPS POST 的 JSON 本文，不放網址查詢參數、程式、測試常數、紀錄檔(Log)、Git 或課程進度；學生自行更換的正式值不得貼進對話。

### `WEB_APP_URL`

部署後，使用者可將 `/exec` URL 貼給 Agent。Agent 說明網址中的 `/s/「Deployment ID」/exec` 結構並提供可複製的完整 URL，再由使用者親自在指令碼屬性填入 `WEB_APP_URL`。不得把 URL 寫進程式、紀錄檔(Log)或 Git。

`checkLesson08Settings()` 在部署前允許 `WEB_APP_URL` 尚未設定，並顯示「準備部署」；部署後三項設定都存在時，才顯示「準備遠端測試」。

## 權限與部署說明

本課新增 Web App deployment、`UrlFetchApp` 對外請求權限，以及 Web App
依 `SPREADSHEET_ID` 開啟指定檔案所需的完整試算表權限。前七課在 Sheets
畫面中可使用只限目前檔案的權限；外部 Webhook 沒有目前開啟的試算表，
所以第 8 課才擴大這一項權限。使用者建立 deployment 前，Agent 必須說明：

- 「執行身分」保留畫面顯示的「我」，外部請求會以部署者權限寫入指定練習試算表。
- 「誰可以存取」選擇「所有人」。
- 這會建立一個公開網址，任何人都能送出請求，但只有持有正確測試 Token 的資料才可通過驗證。
- 第一版禁止付款資料、密碼、OAuth Token、真實個資或正式第三方資料。
- 如果帳號沒有匿名公開選項，停止本課部署，不改用其他權限假裝完成 Webhook。

開發測試網址以 `/dev` 結尾，只供專案編輯者測試最新儲存程式；本課實際 Webhook 驗證使用版本化 deployment 的 `/exec` 網址。`clasp push` 只更新專案程式；若部署後再修改程式，使用者必須到「管理部署作業」更新 deployment 至新版本，`/exec` 才會執行新程式。

## 確認點

以下操作分開確認：

1. 推送到Apps Script(clasp push)：只更新程式，不部署，也不送出
   HTTP 請求。
2. 建立公開 deployment：顯示執行身分、匿名存取、資料範圍與公開風險，再由使用者操作 UI。
3. 實際遠端測試：顯示將送出四個 POST、假資料欄位及預期只新增一筆；取得使用者確認後由 Agent 執行本機安全測試工具，不使用 `clasp run`，也不新增可執行 API 部署。
4. 封存 deployment：全部驗收完成後取得確認，再由使用者操作 UI。

每個確認只適用於當次摘要。未獲確認不得推送、部署、更新 deployment、送出實際 POST 或封存 deployment。

## 使用者 UI 驗收順序

本機與遠端工程測試由 Agent 執行。學生只操作敏感設定、部署、瀏覽器與可見結果驗收：

1. Agent 先提供並標示一組只供本課使用的 `WEBHOOK_TOKEN` 臨時教學密語，說明正式使用時的自行產生方式；使用者在「專案設定」的「指令碼屬性」使用「編輯指令碼屬性」及「新增指令碼屬性」輸入該值，再點擊「儲存指令碼屬性」，不把值回傳。
2. 回到試算表重新整理，選擇「活動報名工具」→「檢查系統設定」。用途是檢查部署前設定；預期顯示「準備部署」，而且不連外、不寫入資料。
3. Agent 回報 `runLesson08LocalTests` 已通過，而且沒有遠端副作用。
4. Agent 顯示公開 deployment 摘要並取得使用者確認。
5. 使用者點擊「部署」→「新增部署作業」→ 類型選擇「網頁應用程式」，設定：
   - 「執行身分」：畫面顯示的「我」。
   - 「誰可以存取」：「所有人」。
6. 使用者完成授權並部署，再進入「部署」→「管理部署作業」，選取剛建立的部署作業，點擊「複製網頁應用程式網址」，取得以 `/exec` 結尾的實際網址。
7. 使用者將 `/exec` URL 貼給 Agent；Agent 說明結構後，使用者親自在指令碼屬性新增 `WEB_APP_URL`。
8. 回到試算表再次選擇「活動報名工具」→「檢查系統設定」，預期顯示「準備遠端測試」，不顯示 Token 或 URL。
9. 使用者在瀏覽器開啟 `/exec` URL，確認看到 `READY` 與繁體中文狀態。
10. Agent 顯示四個實際 POST 的欄位與預期結果，取得使用者確認後執行 `scripts/run_lesson08_webhook_tests.py`。工具以隱藏輸入取得網址與臨時教學密語，預期依序得到 `INVALID_JSON`、`INVALID_TOKEN`、`OK`、`DUPLICATE`；若有效測試資料已存在，正常請求也可回傳 `DUPLICATE`，但資料總數不得增加。
11. 使用者到試算表確認同一個教學 `requestId` 只有一筆資料。
12. 使用者到左側「執行項目」查看實際 GET 與 POST 的背景執行結果。
13. Agent 取得封存確認後，使用者點擊「部署」→「管理部署作業」，選取本課公開 deployment，點擊「封存部署作業」。看到 `確定要封存「部署名稱」部署作業嗎？` 後，確認目標正確再點擊「封存」。
14. 使用者再次開啟原 `/exec` URL，確認公開測試入口已不可使用。

`doGet`、`doPost`、`runLesson08LocalTests` 與 `runLesson08RemoteTests` 不放進 Sheets 選單；Web App 的真正日常入口是已部署的 `/exec` URL，Sheets 選單只提供安全的設定與狀態檢查。

若部署後修正程式，必須先完成本機驗證與新的 Git commit，再經確認執行 `clasp push`。接著由使用者進入「部署」→「管理部署作業」，選取原 deployment，點擊「編輯」，在「版本」選擇「建立新版本」，經確認後點擊「部署」，最後由 Agent 重新執行實際 `/exec` 工程測試，使用者查看可見結果。

## 預期紀錄檔(Log)與回應

```text
[開始] 檢查第 8 課設定
[設定] SPREADSHEET_ID=已設定｜WEBHOOK_TOKEN=已設定｜WEB_APP_URL=已設定
[成功] 本機測試完成｜通過=5｜沒有遠端副作用
[開始] 準備執行實際 Webhook 測試｜請求數=4
[失敗] Webhook JSON 格式不正確｜code=INVALID_JSON｜未寫入資料
[失敗] Webhook 驗證失敗｜code=INVALID_TOKEN｜未寫入資料
[成功] Webhook 測試資料已寫入｜code=OK｜新增=1
[略過] requestId 已處理｜code=DUPLICATE｜沒有重複新增
```

對外回應使用簡短繁體中文 JSON：

```json
{"ok":true,"code":"OK","message":"已收到測試報名資料"}
```

```json
{"ok":false,"code":"INVALID_TOKEN","message":"Webhook 驗證失敗"}
```

紀錄檔(Log)與回應不得包含 Token、完整 URL、完整請求本文、原始例外或 Script Properties 實際值。

## 驗收

- 設定：Token 與 URL 只顯示已設定／未設定，不顯示實際值。
- Agent 本機測試：解析、驗證、鎖定與去重都通過，而且沒有遠端副作用。
- GET：瀏覽器透過實際 `/exec` 網址看到 `READY` 與繁體中文狀態。
- Agent 正常 POST：一筆有效假資料寫入練習試算表。
- Agent 錯誤 POST：無效 JSON 與錯誤 Token 都沒有寫入資料。
- Agent 重送：相同 `requestId` 沒有新增第二筆。
- 可診斷：使用者能從回應 `code`、試算表與「執行項目」判斷結果。
- 安全：只有臨時教學權杖(Token)在私人教學對話顯示一次；它未進入程式、測試、URL、紀錄檔(Log)、Git、課程進度或回應。學生自行更換的正式值未出現在對話。
- 部署：使用者理解 `/dev`、`/exec` 與版本更新差異，並已封存公開測試 deployment。

## 使用者檢查點

請使用者用自己的話回答：「為什麼 `clasp push` 成功，不代表 `/exec` 已經使用新程式？」並指出哪個畫面可以更新或封存 deployment、哪三種證據可以證明 Webhook 重送沒有新增第二筆。

完成後，Agent 回顧八課成果，確認沒有遺留測試觸發器或公開 deployment；若使用者要刪除測試資料或 Script Properties，必須另行取得確認。
