# Google Apps Script 學習路徑

## 路線原則

這組技能第一次使用時，先由 `google-apps-script-project-development` 完成免費基礎應用分流；使用者選擇教學模式後，可以在開始前自由選擇第一階段或第二階段，兩者沒有先修限制。第一階段五個案例彼此獨立，可自由選擇；第二階段八課共用同一個累積專案，必須依序完成。選定後自動建立或讀取統一課程進度，再執行共用開發環境關卡。共用環境關卡不是第一或第二階段的課程。

第一版教學分成兩層，以個人 Google 帳號、不需信用卡、不需付費 Workspace、不需管理員身分為基線：

1. [生活應用入門課程](beginner-application-path.md)：五個彼此獨立的生活小專案，由學員自由選擇。
2. 整合專案課程：依序使用下方第 1 至第 8 課，逐步累積成完整的「活動報名與通知系統」。

學員可在開始前直接選擇任一階段。選擇第一階段後，可依興趣自由選擇任一未完成案例；案例彼此不依賴。選擇第二階段後即進入固定的第 1 至第 8 課，因每課沿用前課專案成果，不在課間切換階段或詢問是否進入下一課；若中斷，Agent 下次從第二階段最早未完成的課次或檢查點恢復。

第一階段需要的函式選單、執行記錄等介面基本操作與 Script Properties 會在入門案例第一次需要時融入，不另外安排沒有應用情境的獨立課程；第二階段則從第 1 課起使用 Sheets 共用選單。各階段都以一個可驗證成果收尾，未通過驗收就不增加下一個服務。

程式與工程測試由 AI Agent 負責撰寫、執行與維護。使用者只學習目前生活案例或整合專案真正會操作的 UI，並親自完成必要設定、授權與可見成果驗證。

## 全技能共用入口：開發環境關卡

- Agent 偵測 macOS／Windows、CPU 架構、Shell 與 WSL。
- 先唯讀檢查既有 Node.js、npm、Git、`clasp`、API 與 OAuth。
- 環境完整就跳過安裝，部分缺少才補齊。
- 需要時安裝仍受支援的 Node.js LTS。
- 使用者選定教學、專案或除錯目標後，在目標專案內固定 `@google/clasp` 版本並建立敏感檔案忽略規則。
- 啟用 Apps Script API。
- 由使用者完成正確 Google 帳號的 OAuth。
- 環境教材與操作由 `google-apps-script-project-development` 提供。

驗收：Agent 能證明電腦層工具健康；目標確定後，也能證明專案內 `clasp`、Git 與忽略規則可用。Agent 說明本次是沿用或補齊環境，而且尚未發生遠端專案同步。

## 第一階段：生活應用入門課程

第一階段使用五個已確認且彼此獨立的生活小專案；編號只供識別，不代表先修順序：

1. Google Sheets：家庭支出記錄表。
2. Google Docs：批次信封版面產生器。
3. Google Forms：教師隨機測驗與成績報表。
4. Google Drive：指定資料夾檔案上傳紀錄器。
5. Gmail：個人化批次郵件寄送器。

每個案例以一個主要 Google App 為核心；必要時可用 Sheets 擔任資料來源或結果紀錄。詳細規格使用[生活應用入門課程](beginner-application-path.md)。

## 第二階段：活動報名與通知整合專案

下方第 1 至第 8 課屬於整合專案課程，都以 [教學案例與共同規格](teaching-examples.md) 的「活動報名與通知系統」為主，不在課程中途更換情境。Agent 先查教學模板登錄表：第 1 課已有 `validated` 累積快照時使用一般複製；第 2 至第 8 課必須使用 `scripts/materialize_template.py --upgrade-from`，只從相鄰前課快照受控升級，不得直接複製後面課次、跳課、手動合併或重新撰寫。尚為 `pending`、且目前正在維護 Toolbox 的 Google 自動化技能包時才實作一次。每一課都準備測試並在驗證通過後建立本機 Git commit；取得使用者確認後才執行 `clasp push`。使用者明確停用 Git 時除外。

學員第一次選擇任一階段時，Agent 在獨立的 `GoogleAppsScript/learn-gas-course` 工作區自動建立涵蓋兩階段的 `docs/course-progress.md`；已有紀錄時不覆寫。若統一進度推出前已有舊版課程紀錄，Agent 只在核對明確完成證據後使用 `scripts/update_course_progress.py --import-legacy-progress` 匯入；工具找不到明確證據或遇到進行中的統一進度時停止，不猜測、不覆寫，也不保存舊檔路徑。每次選擇或狀態改變都由 Agent 使用同一工具記錄，學生不需要手動維護，進度也不得包含私人 Google ID、網址、Email、秘密或私人絕對路徑。

每一課完成工程測試、使用者 UI 驗收、可見結果、繁體中文紀錄檔(Log)與收尾小問題後，維護流程要把當時完整累積的 `.claspignore` 與 `src/` 收錄為 `templates/activity-registration/lesson-XX`，將 `catalog.json` 狀態改成 `validated`，再通過技能驗證。一般學習者不得使用 `pending` 草稿。

每課都必須完成 Script Properties 檢查、正常案例、錯誤案例、重複執行驗證及繁體中文紀錄檔(Log)；這些工程測試由 Agent 負責。第二階段從第 1 課起由共用 `onOpen(e)` 建立 Sheets 的「活動報名工具」，之後累積真正的日常或管理入口。使用者親自從該選單完成案例真正的 UI 使用流程，必要時到 Apps Script 左側「執行項目」查看本次結果，再到對應 Google 服務驗證成果。

實際逐步操作、課程狀態、每次推送確認與八份教案使用 [教學執行協定](course-execution-protocol.md)。本文件只負責路線摘要，不取代逐課完成門檻。

## 第二階段模組一：Sheets 與專案設定

### 第 1 課：用 Apps Script 改動 Google Sheets

- 從 Google Sheets 開啟活動報名與通知系統的綁定型 Apps Script 專案。
- 用白話理解函式(function)是 AI 代理(Agent)寫好的一個「有名字的動作」。
- 知道程式碼與測試由 Agent 維護，使用者不需要手寫程式或逐項執行測試函式。
- 重新整理 Google Sheets，從「活動報名工具」選擇「初始化活動報名資料」；選單項目會呼叫 Agent 寫好的函式，也就是一個「有名字的動作」。
- 認識 `[開始]`、`[成功]` 與 `[失敗]` 中文紀錄檔(Log)。
- 理解第一次授權與重複執行。
- 回到 Google Sheets 肉眼確認工作表與資料是否正確。
- 教材：[第一個 Sheets 自動化練習](../examples/first-sheet-lesson/README.md)。

驗收：使用者能從 Sheets 選單親自執行初始化動作、必要時到 Apps Script「執行項目」找到相符紀錄，並在 Sheets 驗證結果；Agent 的工程測試證明重跑不產生重複資料。

### 第 2 課：Script Properties 與設定檢查

- 區分程式碼、一般設定與敏感設定。
- 先在尚未設定 `SPREADSHEET_ID` 時執行檢查，親眼看到缺少設定會安全停止。
- 在 Apps Script 專案設定建立 `SPREADSHEET_ID` 與本課需要的屬性。
- 由 Agent 建立集中式設定讀取及缺漏檢查。
- 紀錄檔(Log)只顯示「已設定／未設定」，不顯示實際值。
- 說明 API Key、第三方 Token、Folder ID 等未來應放置的位置。
- Google 帳號密碼與 OAuth Token 永遠不得存放。

驗收：使用者先看到缺少設定的中文紀錄檔(Log)，再新增屬性並成功開啟練習試算表；錯誤回歸測試不刪除使用者已設定的真實值。

## 第二階段模組二：收集與處理資料

### 第 3 課：使用 Google Forms 收集資料與驗證

- 建立活動報名用的練習 Google Form。
- 將回覆寫入 Google Sheets。
- 驗證姓名、Email、活動場次與空白欄位。
- Forms 先阻擋明顯格式錯誤，Apps Script 的資料驗證與錯誤情境由 Agent 測試。
- 本課不建立觸發器；表單送出後的自動處理留到第 7 課。
- 使用者實際提交一筆假資料並查看 Sheets；Agent 另測一筆正確資料與錯誤資料。

驗收：正確回覆出現在指定試算表；Agent 測試證明錯誤輸入不會進入後續處理，而且使用者知道自動處理尚未啟用。

### 第 4 課：Sheets 批次處理

- 用白話理解「一次拿出整批資料、整理完成、再一次寫回」。
- 主要功能集中在 `04_Batch.gs`，不為每個測試建立新檔案。
- Agent 使用 `runLesson04Tests` 一次測試零筆、一筆、多筆、錯誤與重複執行。

驗收：能批次處理有效資料、略過錯誤或已完成資料，重跑不會產生重複業務結果。

## 第二階段模組三：產生文件與通知

### 第 5 課：使用 Docs 與 Drive 產生文件

- 從 Script Properties 讀取 `DOC_TEMPLATE_ID` 與 `OUTPUT_FOLDER_ID`。
- 根據測試表單資料建立 Google Docs。
- 將文件放進專用的 Drive 測試資料夾。
- 產生可辨識的檔名並把文件 ID 寫回處理表。
- 重複執行時避免建立重複文件。

驗收：Drive 中只出現一份內容正確的測試文件；重跑不會重複建立，紀錄檔(Log)不包含完整文件內容或敏感設定。

### 第 6 課：使用 Gmail 寄送報名通知

- 根據前一課結果，把確認文件轉成 PDF 附件。
- 正式收件人來自該筆報名資料的 Email，不建立 `TEST_EMAIL`。
- 第 1 課固定教材資料自動使用目前執行者的 Google 帳號 Email；會進入
  寄送流程的表單測試資料使用學員能親自收信的地址。
- 使用只能寄信、不能讀取 Gmail 信箱的 `MailApp`。
- 寄送前明確告知會真實寄出一封郵件，並取得確認。
- 在主旨與工作表記錄通知編號、寄送狀態與時間，避免重複寄送。
- 上次寄送結果不確定時停止；只有確認沒有寄出後才能安全重設。

驗收：報名資料指定的收件匣收到一封內容與 PDF 附件正確的郵件，寄件
備份也有相符紀錄；工作表顯示通知編號，重跑不會寄出第二封。

## 第二階段模組四：自動執行

### 第 7 課：表單或時間觸發器

- 比較手動函式、表單提交與時間型觸發器。
- 表單觸發器只驗證並標記新回覆，不建立文件或寄信。
- 時間觸發器每次最多處理一筆，郵件寄到該筆報名資料的 Email。
- Agent 的模擬測試不修改遠端資料、不建立觸發器也不寄信。
- 取得確認後，由使用者親自在「觸發條件」UI 建立兩種觸發器。
- 核對時區、執行帳號、背景執行記錄、重複事件與失敗結果。
- 兩種觸發器各成功執行一次後，由使用者親自在 UI 刪除測試觸發器。

驗收：表單與時間觸發器各實際成功執行一次；只寄出一封測試郵件，重複事件不會產生重複文件或郵件，且使用者能從「觸發條件」與「執行項目」判斷結果並完成清理。

## 第二階段模組五：簡單網頁入口

### 第 8 課：簡單 Web App／Webhook

- 使用 `doGet(e)` 回傳簡單 HTML、文字或測試狀態。
- 使用 `doPost(e)` 接收不含敏感資料的測試內容。
- Webhook Token 只從 Script Properties 讀取，放在 JSON 本文，不放網址或紀錄檔(Log)。
- Agent 先完成沒有遠端副作用的本機測試；取得實際請求確認後，再由 Agent 對 `/exec` 網址送出正常、錯誤與重送請求。
- 回應使用繁體中文 JSON 與應用層 `code`，不宣稱 Apps Script 能自訂 HTTP 狀態碼。
- 使用者親自在部署 UI 選擇執行身分與公開存取範圍。
- `clasp push` 後若程式有變更，必須更新版本化 deployment，實際 `/exec` 才會使用新版本。
- 完成驗證後取得確認，由使用者封存公開測試 deployment。

驗收：實際 `/exec` 網址可取得預期 GET 回應；四種真實 POST 只有正常請求新增一筆資料，重送不會重複；「執行項目」沒有敏感資料，而且公開測試 deployment 已封存。

## 第一版支援但不列入固定教學的基礎應用

- Google Calendar 測試行程。
- Google Slides 基礎簡報產生。
- Sheets／Docs／Slides／Forms 自訂選單。
- Drive 檔案整理。
- 多個免費內建 Google 服務組成的基礎流程。

這些功能可以用於使用者選定的實際專案，但不為第一版教學增加平行課程。

## 下一版範圍

- 進階 Google 服務與外部 API。
- Google Chat App、Workspace Add-on 與 Marketplace。
- Workspace 管理員與 Admin SDK。
- Vertex AI、BigQuery、Cloud SQL 與其他 Cloud Billing 功能。
- API executable、標準 Google Cloud 專案與自訂 OAuth Client。
- 大型既有專案與正式高流量後端。
