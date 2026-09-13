# 專案工作流程

## 1. 盤點需求

先依 [免費基礎應用分流](basic-application-routing.md) 判斷是建立、接管或教學模式，以及需求是否落在第一版範圍。建立與接管必須使用各自的 [個別流程](project-mode-workflows.md)。

再依 [Agent First 專案設計](agent-first-project-design.md)提出簡短的「Agent First 設計摘要」，先確認使用者的日常操作方式，再選擇技術架構。摘要把使用者的想法整理成：

- 專案目標
- 使用者與使用情境
- 輸入、輸出、預計使用的 Apps Script 服務與能力限制
- 初始化、日常操作、工程測試與管理／清理入口
- 設定位置與 Agent／使用者分工
- 外部影響、確認點與執行頻率
- 錯誤恢復、狀態顯示與可見驗收標準

若是既有專案，先檢查專案根目錄、`appsscript.json`、`.clasp.json`、來源檔、建置設定與 Git 狀態。讀取 `.clasp.json` 時不得在回覆或紀錄中洩漏完整 Script ID。

## 2. 建立 Git 安全基線

除非使用者明確指示這個專案不用 Git，否則任何新建、接管或教學專案都必須先：

1. 確認 `git` 可執行、目前目錄是否為 repository、目前分支及 `git status`。
2. 既有 repository 先辨識使用者尚未提交的變更；不得擅自提交、丟棄或混入本次 commit。
3. 新目錄先建立安全 `.gitignore`，完成敏感資料掃描後才執行 `git init` 與初始 commit。
4. 既有非 Git 專案若已有檔案，先取得使用者對初始基線內容的確認；不得把來源不明或含敏感資料的全部檔案直接加入。
5. Git 作者資訊不存在時，不得猜測姓名或 Email；請使用者提供後，只設定目前 repository，除非使用者明確要求全域設定。

每個可獨立驗收的修改都依序執行：

1. 完成程式及文件修改。
2. 執行語法、型別、測試及專案驗證。
3. 搜尋憑證、Token、私人 ID 與測試個資。
4. 只 stage 本次由 Agent 修改的檔案。
5. 檢查 staged diff 與 `git diff --cached --check`。
6. 建立描述成果的本機 commit，並向使用者回報 commit。

驗證失敗、變更範圍不明或與既有未提交內容重疊時，不建立完成版 commit；先留在同一階段修正或請使用者決定。

本機 Git commit 只提供版本回復，不是磁碟損壞時的異機備份。GitHub repository、remote 與 `git push` 仍是獨立的外部操作，必須先取得使用者確認。

## 3. 選擇架構

第一版依需求選擇：

- 獨立 Apps Script 專案
- 綁定 Google 文件、試算表、簡報或表單的專案
- 簡單 Web App／Webhook
- 時間型或事件型觸發器

Google Workspace Add-on、Google Chat App、API executable、進階 Google 服務、外部 API 與需要標準 Google Cloud 專案的架構留到下一版。

Agent 先用白話簡短說明：「獨立式像一個不固定綁住檔案的小工具；綁定型則附著在某一份 Google 檔案中。」接著根據輸入、輸出、執行入口與使用情境提出建議及理由。使用者只確認實際操作是否符合需求，不需要自行判斷技術架構。

把遠端 Apps Script 專案與本機原始碼視為兩個需要明確同步的狀態，不得假設兩邊自動一致。

## 4. 建立本機結構

教學模式在建立一般結構前，先由 `google-apps-script-teaching` 查詢 `templates/catalog.json`。已有 `validated` 模板時，使用教學技能的 `scripts/materialize_template.py` 取用登錄檔案；第一階段案例與第二階段第 1 課使用一般複製，第二階段第 2 至第 8 課必須以 `--upgrade-from` 從相鄰前課受控升級。一般複製遇到不同內容必須停止；受控升級則先完整比對前課快照，任何修改、缺檔、額外 `src/` 檔案、未驗收目標或跳課都在寫入前停止。Agent 不得覆寫、刪除、手動合併或重新生成業務程式。若遠端建立後 `clasp create` 剛拉回空白 `Code.gs` 與初始 manifest，Agent 先用 `--dry-run --replace-clasp-bootstrap` 核對；只有工具證明 `src/` 沒有其他程式或服務設定時，才正式取代這兩個初始檔。只有沒有對應教學模板的實際專案，才從下方一般結構開始建立。

一般 Apps Script 專案預設使用分檔 `.gs`：

```text
project/
├── README.md
├── .gitignore
├── .claspignore
├── package.json
├── src/
│   ├── appsscript.json
│   ├── 00_Log.gs
│   ├── 01_Config.gs
│   ├── Main.gs
│   └── Tests.gs
└── docs/                 # 只有複雜專案才建立
```

依功能拆分檔案，但不要為每個小函式建立新檔。需要安裝型觸發器時才加入 `Triggers.gs`。若專案規模很小，不建立空白 `docs/` 或額外測試框架，但仍需保留 README、資訊清單、設定檢查、Apps Script 測試函式與安全忽略規則。

### TypeScript 例外

`clasp` 3.x 不再負責轉譯 TypeScript。只有專案複雜度確實需要型別檢查、npm 套件或模組化建置時，才採用 TypeScript，並建立以下完整流程：

```text
src/*.ts
   ↓ TypeScript + bundler
build/*.js
   ↓ clasp push
Apps Script
```

TypeScript 專案必須：

- 使用 Rollup 或經驗證的同類 bundler，把模組轉成 Apps Script V8 可執行的 JavaScript。
- 保留 Sheets 按鈕、選單、觸發器、`doGet`、`doPost` 等入口函式於 Apps Script 全域範圍。
- 將 `appsscript.json` 複製到建置輸出目錄。
- 讓 `.clasp.json` 的 `rootDir` 指向 `build` 或 `dist`，並用 `.claspignore` 排除原始 `.ts`、測試與套件。
- 在每次推送前依序完成建置、型別檢查、測試與輸出檔案檢查。
- 不假設單獨執行 `tsc` 就能處理 `import`、`export` 或 npm 套件。

未建立並驗證以上流程時，改用 `.gs`，不得直接把原始 `.ts` 交給 `clasp push`。

## 5. 實作與驗證

- 遵守 [專案品質標準](project-quality-standard.md)：Script Properties、正常測試、錯誤測試、重複執行測試、可見結果與繁體中文紀錄檔(Log)都是實際專案的強制門檻。
- 遵守 [UI 操作原則](ui-operation-policy.md)：Agent 預設不操作使用者的 UI，只提供已核對的繁體中文操作名稱、單一步驟與成功判斷。
- 請使用者執行教學函式時，先說明函式名稱、所在檔案、用途、預期紀錄檔(Log)，以及編輯器下方「執行記錄」的檢查重點；操作說明固定依序指出左側「檔案」、上方函式選單與「執行」，不得省略檔案位置。
- Google 端的實際操作、測試與最終成果判斷由使用者完成；只有使用者明確要求時，Agent 才協助操作當次指定的 UI。
- 需要安裝型觸發器時，建立防止重複的設定函式與檢查函式；使用者確認影響後親自執行，並到「觸發條件」與「執行項目」驗證。
- 發生錯誤或驗證失敗時，完整使用 `google-apps-script-debugging`，不得只在教學模式使用除錯規則。
- 將業務邏輯拆成可測試函式。
- 將 Apps Script 全域服務呼叫集中在邊界層。
- `.gs` 專案直接檢查待推送來源；TypeScript 專案先建置，再檢查建置輸出與全域入口函式。
- 對空資料、重複執行、時區、配額與部分失敗建立明確處理。
- 觸發器函式保持簡短，並記錄可追蹤的錯誤資訊。
- 所有日期與排程都明確指定時區。

## 6. 同步與交付

同步前先顯示或摘要：

- 本機專案路徑
- 遠端 Apps Script 目標
- 將被推送的檔案
- 需要新增的 OAuth scopes
- 是否會建立版本、部署或觸發器

同步前的程式必須已通過驗證並建立本機 Git commit；使用者明確停用 Git 時除外。

只有在使用者確認後才執行遠端寫入。完成後重新查驗遠端狀態，不以命令無錯誤結束作為唯一成功依據。
