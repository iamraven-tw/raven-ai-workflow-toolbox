# clasp 工作流程

`clasp` 是 Google 提供的 Apps Script 命令列工具。預設依 [開發環境](development-environment.md) 安裝在專案內並固定版本。對使用者第一次提到 `clasp push` 時，先說明它是由 Agent 把本機已完成並通過測試的程式與資訊清單同步到指定的 Google Apps Script 專案；這只更新遠端程式，不等於執行函式、寄信、建立觸發器或部署，使用者不需要操作終端機。說明後固定稱為「推送到Apps Script(clasp push)」。後續面向使用者的確認、進度與結果不得只顯示英文命令；命令、版本與檔案清單留給 Agent 自行核對。實際執行前先確認目前安裝版本與可用命令：

```bash
# 優先執行專案內固定的 clasp。
npm exec -- clasp --version
npm exec -- clasp --help
```

## 環境確認

1. 確認 Node.js 是目前受支援、且符合安裝版 `clasp` 引擎需求的 LTS。
2. 確認使用者登入的 Google 帳號。
3. 確認 Apps Script API 已啟用。
4. 確認目前目錄沒有其他專案的 `.clasp.json`。
5. 確認命令使用專案內版本，不是 PATH 上的舊全域版本。

## 新專案

依 `npm exec -- clasp --help` 顯示的目前版本語法建立專案。建立後檢查：

- `.clasp.json` 指向新建立的正確專案。
- `rootDir` 與來源目錄一致。
- `src/appsscript.json` 存在且 JSON 格式正確。
- `.claspignore` 排除 README、Node／Vitest 等本機測試、套件與建置設定，但保留需要推送到 Apps Script、讓使用者從函式選單執行的 `src/Tests.gs`。

獨立式專案預設由 Agent 顯示摘要並取得確認後使用 `clasp` 建立。綁定 Sheets、Docs、Forms 或 Slides 的專案，預設由使用者先親自建立 Google 檔案與 Apps Script 專案，再由 Agent 接管本機程式；不得為了省一步而在未確認時建立遠端檔案。

## 既有專案

接管既有 Apps Script 時，先確認 Google 帳號，再由帳號清單選擇遠端專案：

```bash
# 只讀確認目前 OAuth 帳號並列出該帳號可存取的專案。
npm exec -- clasp show-authorized-user
npm exec -- clasp list-scripts
```

- Agent 不要求使用者自行到 Apps Script 專案設定複製 Script ID；只有清單無法辨識目標時，才請使用者提供專案網址協助核對。
- 清單中的 Script ID 只在本機選定目標，不逐字貼進回覆、紀錄檔(Log)或 Git。
- 使用者選定專案後，解析作業系統真正的「文件」資料夾，預設使用 `GoogleAppsScript/<專案名稱>`。
- 目錄不存在或為空時，先完成 Git、忽略規則及專案內固定版本的 `clasp`，再執行目前版本支援的 clone：

```bash
# <選定的 Script ID> 只在本機代入，不輸出實際值。
npm exec -- clasp clone-script "<選定的 Script ID>" --rootDir src
```

- clone 後核對 `.clasp.json`、`rootDir`、`src/appsscript.json`、遠端名稱與綁定類型，並將未修改的遠端原始狀態建立為 Git 基線。
- 目錄已有檔案時不得直接 clone 或 pull。先確認是否已連結同一專案並保護本機變更；目標不同時改用新的安全目錄。
- `clone-script` 用於第一次建立本機連結；`pull` 用於已有正確 `.clasp.json` 的後續同步。

目標專案尚未選定、因此還沒有專案內 `clasp` 時，唯讀的 `show-authorized-user` 與 `list-scripts` 可以使用已驗證的既有 `clasp`。若電腦沒有可用版本，Agent 可在作業系統暫存目錄安裝明確固定版本，只用於帳號與清單查詢；不得安裝到技能儲存庫，也不得以未固定版本的 `npx` 取代。專案選定後，所有 clone、pull、push 與部署操作都必須改用該專案內固定版本。

## 推送前檢查

依目前版本提供的狀態命令列出待同步檔案，確認 `.claspignore` 生效。接著再次確認：

- 當前工作目錄。
- `.clasp.json` 的目標。
- 目前 Git 變更。
- 是否可能覆寫遠端使用者剛修改的內容。

取得使用者確認後才執行 `clasp push`。若工具回報跳過、衝突或權限不足，不要改用強制推送掩蓋原因；先查明本機與遠端差異。

### 資訊清單覆寫提示

`appsscript.json`有變更時，`clasp push`可能顯示「Manifest file has been updated. Do you want to push and overwrite?」。處理規則：

1. 推送前摘要必須已列出資訊清單、進階服務或 OAuth scopes 的變更，並取得使用者對本次推送的明確確認。
2. 已知 `appsscript.json` 有變更時，第一次就使用互動式終端（具 TTY）執行一般 `clasp push`，不得先用非互動命令試跑。
3. 目標專案與待推送檔案仍和確認摘要一致時，讀到資訊清單覆寫提示後才輸入確認；不用另外要求使用者重複批准同一份已揭露內容。
4. 非互動執行若因預設拒絕提示而只回覆`Skipping push`，代表沒有完成推送。先檢查本機與遠端差異，再以互動式終端重跑同一個一般 `clasp push`；不得宣告成功，也不得直接改用`--force`。
5. 推送後以 Apps Script API 或其他唯讀方式比對遠端檔案名稱與內容；命令顯示`Pushed`仍不能取代遠端查驗。
6. `clasp` 3.x 執行 `pull` 時，遠端 Apps Script 程式可能以 `.js` 副檔名
   下載，即使本機教材使用 `.gs`。驗證時要用相同基底檔名對應
   `檔名.gs`與`檔名.js`逐一比較實際內容，再單獨比較
   `appsscript.json`；不得把單純副檔名不同誤判成內容不同，也不得因此
   略過內容查驗。
7. 遠端查驗命令必須設定遇錯即停，或逐項檢查每個比較結果。只要任何
   檔案缺少或內容不同，就不得繼續輸出「逐檔比對通過」；先前命令即使
   最後結束碼為成功，也不能推翻前面已出現的差異證據。
8. 唯讀拉取使用獨立臨時目錄，不覆寫學生專案；其中的`.clasp.json`
   仍屬私人識別資訊，驗證後要移到系統垃圾桶或以同等安全方式清理，
   不得加入 Git。

## `.gs` 與 TypeScript

一般專案預設直接維護依功能拆分的 `.gs` 檔案。`clasp` 3.x 不再轉譯 TypeScript，因此不得把原始 `.ts` 當成可直接執行的 Apps Script 推送。

只有已建立 TypeScript 與 bundler 流程的專案才可使用 `.ts`。此時必須：

1. 執行專案定義的建置命令，將 `src/*.ts` 轉成 `build` 或 `dist` 中的 JavaScript。
2. 執行型別檢查、測試及建置輸出檢查。
3. 確認 Apps Script 需要的全域入口函式仍存在。
4. 確認 `appsscript.json` 位於編譯輸出中。
5. 確認 `.clasp.json` 的 `rootDir` 指向編譯輸出，而不是 TypeScript 原始碼。
6. 使用狀態命令確認待推送清單只有執行檔、資訊清單與必要 HTML。
7. 建立本機 Git commit，取得使用者確認後才執行 `clasp push`。

沒有 bundler、建置命令或輸出驗證時，停止推送並改用 `.gs`，不得臨時把副檔名從 `.ts` 改成 `.gs` 假裝完成轉譯。

## Agent-first 修改循環

教學與實際專案都不要求使用者複製貼上或修改 Apps Script 程式。每次修改固定由 Agent：

1. 在本機撰寫程式、繁體中文註解、中文紀錄檔(Log)與測試。
2. 執行語法、型別、格式及可在本機完成的測試。
3. 檢查敏感資料，並為通過驗證的本次變更建立本機 Git commit；使用者明確停用 Git 時除外。
4. 列出 Git commit、待上傳檔案、目標 Script 專案與可能新增的 OAuth 權限。
5. 取得使用者確認後執行 `clasp push`。
6. `clasp push` 完成後，在同一則回覆一次說完重新整理已開啟的 Apps Script 編輯器、等左側「檔案」重新載入、選擇檔案、選擇函式及按「執行」；不得停在重新整理後要求使用者多回一次。
7. 使用者執行後，引導查看編輯器下方的執行記錄與對應 Google 服務的可見結果。

實際專案的 Script Properties、測試、繁體中文紀錄檔(Log)與觸發器函式必須遵守 [專案品質標準](project-quality-standard.md)。Script Properties 的實際值不由 `clasp` 專案檔管理。Agent 只建立屬性讀取與檢查程式；API Key、第三方 Token 等敏感值由使用者直接在 Apps Script 專案設定輸入，不經對話、原始碼、測試或 Git。

## 拉取與部署

- `pull` 可能覆寫本機內容，執行前先保存或提交使用者變更。
- 建立、更新、回復或封存 deployment 時，完整使用 [部署、版本與回復流程](deployment-workflow.md)。
- 需要使用者在瀏覽器完成 OAuth 授權時，明確交還操作並等待確認。

## 官方資料

- [Use the command-line interface with clasp](https://developers.google.com/apps-script/guides/clasp)
- [google/clasp](https://github.com/google/clasp)
- [clasp 3.x：移除 TypeScript 轉譯](https://github.com/google/clasp#migrating-from-2x-to-3x)

命令與旗標可能隨版本調整；以目前安裝版本的 `--help` 與 Google 官方文件為準。
