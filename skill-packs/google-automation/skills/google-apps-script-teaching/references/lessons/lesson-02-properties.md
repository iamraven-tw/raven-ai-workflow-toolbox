# 第 2 課：Script Properties 與設定檢查

## 本課成果

把練習試算表 ID 放進 Apps Script 的 Script Properties；程式先用設定核對目前綁定的試算表，缺少或填錯時以中文停止，不把 ID 寫進原始碼，也不擴大 OAuth 權限。

## 課前簡介（Agent 必須先說）

這一課不是增加新的報名功能，而是替後續整合建立安全的設定檢查。`SPREADSHEET_ID`來自第 1 課由 Agent 建立並綁定的同一份「活動報名與通知系統」試算表；它像試算表的「門牌號碼」，讓程式在工作前確認目前操作的就是正確資料來源。Agent 要從已核對的試算表網址直接擷取並提供完整 ID，說明它位於`/spreadsheets/d/`與`/edit`之間，不把擷取工作交給學生。把值放在 Script Properties，能讓設定與程式分開、換資源時不用改程式，也避免私人 ID 進入原始碼、紀錄檔(Log)或 Git。Agent 負責缺少、錯誤與重複設定測試；學生負責親自填寫並從 Sheets 選單檢查。驗收看紀錄檔(Log)只顯示「已設定／未設定」，而且第 1 課兩筆資料完全不變。

## 核心概念

1. 程式負責做事情；Script Properties 負責保存這個專案會用到的設定。
2. Spreadsheet ID 可以想成試算表的「門牌號碼」，程式靠它每次找到同一份試算表。
3. 把 ID 放在 Script Properties，可以讓設定與程式碼分開；換試算表時只改設定，也不把私人 ID 寫進程式、紀錄檔(Log)或 Git。
4. 程式開始工作前，應先確認必要設定是否存在。
5. 綁定型專案可以比對目前試算表，不必為了 `openById()` 取得整個帳號的完整試算表權限。
6. Script Properties 不是專業秘密管理系統。

本課主要檔案是 `02_Config.gs`。設定讀取、設定檢查及本課測試都集中在這個檔案，不另外增加零碎測試檔。

## Agent 實作

- 建立集中式 `getScriptConfig_()` 與 `validateRequiredProperties_()`。
- 建立 `openCourseSpreadsheet_()`，讀取 `SPREADSHEET_ID` 後，與 `SpreadsheetApp.getActiveSpreadsheet().getId()` 比對。
- 將第 1 課後續讀寫改成先通過設定比對，再使用目前綁定的試算表。
- 建立以下測試入口：
  - `checkLesson02Settings()`
  - `testLesson02Normal()`
  - `testLesson02MissingSetting()`
  - `testLesson02WrongSpreadsheet()`
  - `testLesson02Repeat()`
- 錯誤測試向純設定驗證函式注入缺少屬性的物件，不刪除使用者已設定的真實值。
- 錯誤門牌號碼測試使用固定假字串，不接觸或輸出真實 ID。
- 程式、測試與紀錄檔(Log)都不得包含實際試算表 ID。

## 使用者操作

Agent 預設不操作使用者 UI。使用者親自完成：

1. 先在尚未設定 `SPREADSHEET_ID` 時執行設定檢查。
2. 若練習試算表由 Agent 建立，Agent 重新核對後直接提供可點擊的試算表網址，不要求學生自己找網址或貼回來；若是使用者原有的試算表，才由使用者提供 URL。
3. Agent 說明 Spreadsheet ID 是網址中 `/spreadsheets/d/` 與 `/edit` 中間的文字。
4. Agent 直接提供可複製的完整 ID。
5. 使用者在 Apps Script 左側選擇「專案設定」，找到「指令碼屬性」，點擊「編輯指令碼屬性」。
6. 點擊「新增指令碼屬性」，在「屬性」填入 `SPREADSHEET_ID`，在「值」填入 Agent 提供的 ID，再點擊「儲存指令碼屬性」。

一般 Google 資源 URL／ID 不是密碼；本課試算表由 Agent 建立，因此由 Agent 從已核對網址擷取並直接提供完整 ID，不把這項工作交給學生。只有使用者原有或親自建立的資源，才由使用者主動提供 URL 給 Agent 協助擷取。實際值仍不得寫入程式、測試、紀錄檔(Log)、Git 或公開截圖。若網址含 Token、簽章或其他驗證資料，則視為敏感值，不可貼進對話。

## Script Properties

| 名稱 | 用途 | 敏感性 | 紀錄檔(Log) |
|---|---|---|---|
| `SPREADSHEET_ID` | 指定本課共用試算表 | 非密碼，仍不寫入程式、紀錄檔(Log)或 Git | 只顯示已設定／未設定 |

未來的 `FORM_ID`、`DOC_TEMPLATE_ID`、`OUTPUT_FOLDER_ID` 等非敏感
Google 資源設定，都使用相同的「已核對網址、ID 所在區段、完整 ID、
逐欄填寫」流程。活動報名者的 Email 是工作表資料，不是
`TEST_EMAIL` 指令碼屬性；第 6 課會直接使用選定報名資料中的 Email。
API Key、第三方 Token、Client Secret、Webhook Secret 與 Private Key
是敏感值，Agent 只提供屬性名稱，由使用者自行輸入。Google 密碼與
OAuth Token 永遠不得存入。

## 權限說明

本課仍只讀寫目前綁定的練習試算表。程式使用 `SpreadsheetApp.getActiveSpreadsheet()`，並以 Script Property 核對門牌號碼；不得使用需要完整 `spreadsheets` OAuth scope 的 `SpreadsheetApp.openById()`。資訊清單維持 `spreadsheets.currentonly`，也不新增 Gmail、Forms、Docs、觸發器或部署權限。

## 推送到Apps Script(clasp push)前摘要

Agent 顯示本課設定讀取檔、調整過的 Sheets 檔、測試入口、Git commit 與權限差異。實際 `SPREADSHEET_ID` 不出現在摘要。

取得使用者確認後才推送。

## 使用者 UI 驗收順序

工程測試由 Agent 完成。學生只操作真正的設定流程：

1. 開啟試算表並重新整理，選擇「活動報名工具」→「檢查系統設定」；尚未設定時到 Apps Script 左側「執行項目」確認缺少設定且沒有資料寫入。
2. 若練習試算表由 Agent 建立，Agent 直接提供已核對的可點擊連結、`SPREADSHEET_ID` 所在位置與完整 ID；只有使用者原有的試算表才由使用者提供 URL。
3. 使用者到「專案設定」的「指令碼屬性」，使用「編輯指令碼屬性」及「新增指令碼屬性」輸入 `SPREADSHEET_ID`，再點擊「儲存指令碼屬性」。
4. 回到試算表重新整理，再選擇「活動報名工具」→「檢查系統設定」；到「執行項目」確認只顯示「已設定」，不顯示實際值。
5. 開啟 Agent 提供的練習試算表連結，確認是同一份「活動報名與通知系統」。
6. `testLesson02Normal`、`testLesson02MissingSetting` 與 `testLesson02Repeat` 不出現在 Sheets 選單，也不需要學生執行。

## 預期紀錄檔(Log)

```text
[開始] 準備檢查第 2 課設定
[設定] SPREADSHEET_ID=已設定｜實際值不顯示
[成功] 設定與目前綁定的練習試算表相符
[失敗] 缺少必要的指令碼屬性｜名稱=SPREADSHEET_ID｜未執行資料寫入
[失敗] SPREADSHEET_ID 與目前綁定的練習試算表不相符｜未執行資料寫入
[略過] 設定已驗證｜重複檢查不會改變資料
```

## 驗收

- 正常：Agent 測試證明程式能用設定核對目前綁定的正確試算表，學生也看到同一份練習試算表。
- UI：使用者親自新增 Script Property，回到 Sheets 從「活動報名工具」選擇「檢查系統設定」。
- 錯誤：Agent 測試證明缺少設定或門牌號碼不相符時會停止，而且沒有資料寫入。
- 重複：Agent 測試證明設定檢查可重跑，不改變 Script Properties 或工作表。
- 安全：原始碼、Git diff 與紀錄檔(Log)都沒有實際 ID；manifest 維持 `spreadsheets.currentonly`，程式沒有 `openById()`。
- 可診斷：使用者能在 Apps Script 左側「執行項目」指出「已設定」與「未設定」的差異。

## 使用者檢查點

請使用者用自己的話回答：「為什麼 Spreadsheet ID 不應直接寫在程式碼中？」並指出日後 API Key 應放在哪裡、哪裡絕對不能放。

通過後才進入第 3 課。
