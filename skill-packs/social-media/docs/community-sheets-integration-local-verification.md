# Google Sheets 六欄接線本機驗證

日期：2026-09-06。範圍為待辦 `COM-02`：把第六技能既有的六欄資料契約接到 Google Sheets v4 正式 REST 介面，並將表格寫入、人工核准與平台回覆保持為不同關卡。所有執行測試使用虛構儲存格、假 Token provider 與 FakeHTTP；沒有登入 Google、執行 OAuth、讀寫真實試算表、回覆留言、安裝套件或變更私人 newsletter 工作區。

## 已建立的接線

- `official_sheets_api.py`：固定連 `sheets.googleapis.com`，只允許 `spreadsheets.get` 與 `spreadsheets.values.update`；不接受查詢參數 Token、不跟隨重新導向、不自動重試。寫入固定 `valueInputOption=RAW`，讀取保留 `CellData.userEnteredValue` 的 string／formula／number 型別。
- `community_sheets.py`：先確認整個指定專用分頁沒有使用者輸入，再依序執行本機 export、一次性 sheet-claim、一次 PUT、結果紀錄、獨立 GET 與 sheet-verify。claim 後中斷或回應不明只可讀原綁定分頁，不能 append、清空、切換工具或重送。
- `community_queue.py`：批次新增 Sheets 寫入核准參照與 sheet operation 狀態。sheet-claim 只能取得一次；只有 claimed／request_accepted／unknown 能以精確讀回完成 awaiting_approval。
- `community_execute.py`：正式 API 與受控瀏覽器回覆輸入使用 `refresh_sheet=true`，在每一則 begin 前由 Sheets 協調器重新讀取 A:F；測試專用內嵌 snapshot 不作實際回覆 SOP。
- Sheets 快照、型別及雜湊寫到私人工作區 `social-media/community/sheets/`，檔案模式為 0600；CLI stdout 只回傳狀態與證據路徑，不顯示六欄文字。

## 授權與工具選擇

Sheets 權限固定為 `https://www.googleapis.com/auth/spreadsheets`，與 YouTube／Meta OAuth 分開。adapter 接受可信程序注入的短期 Token provider；選配預設路徑只沿用環境已存在的 `google-auth` Application Default Credentials。本技能不建立 Google Cloud 專案、不執行登入／OAuth、不保存 Token，也不安裝 `google-auth`；缺授權時交回既有 Google 自動化工作流。

本機查得 `gws` 0.6.0，但沒有用它執行。本版不把它列為預設 transport，原因是更新 body 經 `--json` 程序引數傳入，可能讓訪客文字出現在程序清單；此外上游明示此 CLI 仍在積極開發且不是正式支援的 Google 產品。這不是說它無法操作 Sheets，而是本次敏感資料邊界不採用該介面。

## 官方依據

- Google 官方 [`spreadsheets.values.update`](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/update) 定義固定範圍 PUT 與 `valueInputOption`。
- Google 官方 [寫入範例](https://developers.google.com/workspace/sheets/api/samples/writing) 說明 RAW 會把例如 `=1+2` 保留為字串，而不是解析為公式。
- Google 官方 [`spreadsheets.get`](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/get) 支援指定 ranges、grid data 與欄位限制。
- Google 官方 [`CellData`](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/cells) 區分 `userEnteredValue`、effective value 與 formatted value，因此本流程用原始輸入型別拒絕公式／數字冒充文字。
- Google 官方 [field mask 指南](https://developers.google.com/workspace/sheets/api/guides/field-masks) 用來限制讀取欄位；[Google Workspace CLI 上游](https://github.com/googleworkspace/cli) 用來核對本機候選工具的定位，不把它描述成 Sheets 官方 API 本身。

## 本機驗證內容

- 固定 spreadsheet ID、數字 sheet ID、精確分頁名稱、官方主機、方法、range 與欄位遮罩。
- 整個專用分頁非空即在 export 前停止；不同文件、分頁 ID 或名稱不能通過。
- RAW 六欄 body、更新列／欄／儲存格數量讀回；未 claim、USER_ENTERED、錯誤欄數與錯誤範圍在網路前停止。
- 稀疏 GridData 還原固定 A:F，真正空白補 `{}`；formulaValue／numberValue 不轉字串。
- 寫入 5xx、重新導向、逾時或壞回應視為結果不明；不重送。程式在 claim 或送出後中斷，續跑只 GET。
- 使用者說可以回覆後重新讀 F、整列排序仍依前五欄配對、每則 API／瀏覽器回覆前再次重讀；任何變動停止。
- 私人 evidence 權限、stdout 不含留言文字、Google OAuth 與回覆授權分離。

## 驗證結果

- `test_official_sheets_api.py`、`test_community_sheets.py`、`test_community_queue.py` 與 `test_community_execute.py` 共 57 項針對測試通過。
- 社群媒體技能包 307 項離線測試中 306 項通過；1 項真實原生憑證探測依 `SOCIAL_NATIVE_ACCEPTANCE=0` 的集中驗收政策略過。
- `validate_package.py` 通過靜態結構、技能契約、公開邊界、相對連結、Markdown 與 Python 語法。
- 七份 `SKILL.md` 均通過 skill-creator `quick_validate.py`；`git diff --check` 通過。

以上仍只代表本機虛構接線，不代表真實 Google 帳號可用。

## 分層狀態

| 層級 | 本待辦結果 |
| --- | --- |
| 靜態結構與文件 | validate_package、七技能 quick_validate 與 diff check 通過 |
| 本機技能發現 | 307 項整包離線測試包含安裝／更新／回復／移除；未重跑真實用戶端發現 |
| API 套件是否可安裝 | 沒有安裝；REST transport 使用標準函式庫，選配 `google-auth` 只沿用既有環境 |
| 使用者登入與 OAuth | 未執行；由既有 Google 工作流另行驗收 |
| 平台／試算表讀取 | 沒有讀真實平台或試算表；FakeHTTP 不是平台讀取驗收 |
| 測試寫入／回覆 | 沒有執行；RAW body 虛構測試不等於雲端寫入 |
| 另一臺電腦驗收 | 未執行；Windows ACL、憑證與網路仍待集中驗收 |
| 正式公開支援 | 尚未成立；仍是本機候選實作 |
