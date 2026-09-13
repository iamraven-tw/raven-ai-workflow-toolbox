---
name: google-apps-script-project-development
description: 建立、接管、同步與準備部署 Google Apps Script 專案，並作為整組技能未指定目的時的共同分流入口。當使用者提到 Google Apps Script 但沒有說要做專案或學習，或提到開發環境、Node.js、Git、clasp、appsscript.json、新專案、既有專案、Script ID、OAuth、push、trigger、deployment、GitHub 或實際自動化需求時使用。
---

# Google Apps Script 專案開發

## 責任

本技能負責開發環境、需求分流、專案架構、本機檔案、Git、`clasp`、OAuth、遠端同步、觸發器與部署確認。逐課教學內容交由 `google-apps-script-teaching`；Google Docs 固定版面交由 `google-docs-layout`；發生錯誤時使用 `google-apps-script-debugging`。

## 執行順序

1. 先讀取[初學者術語規則](../learner-facing-terminology.md)與 [免費基礎應用分流](references/basic-application-routing.md)。面向一般使用者或初學者時，先用白話解釋用途，再使用「中文名稱(English)」。使用者未指定目的時，先只詢問要「做 Apps Script 專案」或「學習 Apps Script」；選專案後再問建立或接管，選教學後只先讓學員在開始前自由選擇第一階段或第二階段。兩者沒有先修限制。第一階段五個案例彼此獨立，由學員自由選擇；第二階段八課共用同一個累積專案，開始後固定依序完成第 1 至第 8 課，中斷時從最早未完成處恢復，不再詢問階段或下一課。使用者已明確指定時跳過重複提問。
2. 目的與專案／案例選定後，讀取 [共用首次使用環境關卡](references/development-environment.md)。首次使用或環境狀態不明時完整健檢；已有本次可驗證的健康結果時只快速複核，不重複安裝。
3. 選擇做專案時，依使用者選擇完整讀取 [建立／接管流程](references/project-mode-workflows.md)，不得把兩種模式當成相同的初始化流程；選擇教學時轉交 `google-apps-script-teaching`。
4. 目標專案確定後，先讀取 [Agent First 專案設計](references/agent-first-project-design.md)，提出精簡的操作流程、分工、入口、設定位置、確認點與失敗恢復摘要；使用者確認操作方式後才選定技術架構。
5. 讀取 [專案工作流程](references/project-workflow.md)，完成該專案的目錄、Git、忽略規則及專案內 `clasp` 檢查。
6. 寫程式前完整讀取 [專案品質標準](references/project-quality-standard.md)，套用 Script Properties、測試、繁體中文紀錄檔(Log)與觸發器設定函式規則。
7. 需求涉及信封、標籤、證書、名牌、票券或其他 Google Docs 固定版面時，使用 `google-docs-layout`。
8. 需要引導使用者操作 Google 介面時，讀取 [UI 操作原則](references/ui-operation-policy.md)；預設只提供已核對的繁體中文操作指引。
9. 需要操作 `clasp` 時，讀取 [clasp 工作流程](references/clasp-workflow.md)。
10. 需要建立、更新、回復或封存 deployment 時，讀取 [部署、版本與回復流程](references/deployment-workflow.md)。
11. 只要涉及 Git、GitHub、帳號、OAuth、私人 ID、觸發器或部署，就讀取 [安全與 GitHub](references/security-and-github.md)。
12. 遇到任何錯誤或異常結果，使用 `google-apps-script-debugging`；不得用強制推送、過寬權限或公開部署掩蓋問題。

## 開發原則

- Agent 處理終端機命令、程式、本機檔案、驗證與 Git；使用者只處理系統授權、Google OAuth、必要設定值與遠端操作確認。
- Agent 預設不操作使用者的電腦或瀏覽器 UI。應使用已核對的繁體中文介面名稱，一次提供一個操作步驟與成功判斷；只有使用者明確要求時，才協助操作當次指定的 UI。
- 只要要求使用者開啟、切換或操作任何網頁，就必須在同一則指示中提供已核對且可點擊的目標連結。這包括 Apps Script、Sheets、Forms、Docs、Drive、Gmail、deployment 與外部網站；若尚未取得或無法核對連結，先取得並核對，在連結可提供前不得要求使用者自行尋找或操作該頁面。
- 使用者親自完成 UI 測試並判斷實際成果；Agent 可以說明檢查位置、預期畫面與異常時應提供的非敏感資訊。
- 教學技能的 Script Properties、安全測試、重複執行、繁體中文紀錄檔(Log)與使用者驗收規則，同樣強制套用於建立、接管及後續修改的實際專案。
- 教學技能已有 `validated` 程式模板時，專案初始化必須安全取用該模板，不得重新生成同一套業務程式；模板複製仍不得覆寫目的地的不同內容。
- 每個主要入口與測試函式都要產生可驗證的繁體中文紀錄檔(Log)，不得只輸出原始物件、英文例外或沒有成功判斷的訊息。
- 專案需要安裝型觸發器時，Agent 優先建立可重複安全執行的設定與檢查函式，讓使用者確認影響後親自在 Apps Script 執行；不得因重跑而建立重複觸發條件。
- 進入專案後先檢查 Git repository、分支與既有變更。
- 除非使用者明確指示不用 Git，每個可獨立驗收的修改通過測試後，主動建立只包含本次變更的本機 commit。
- 使用者未指定位置時，查詢作業系統真正的「文件」資料夾，使用其中的 `GoogleAppsScript/<專案名稱>`。
- `clasp` 預設安裝於專案內並固定版本，不以全域安裝為預設。
- OAuth 與 Apps Script API 已由唯讀命令驗證時直接沿用，不重複詢問 Google 帳號。
- 面向使用者時，所有可翻譯的英文技術術語都依[初學者術語規則](../learner-facing-terminology.md)使用「中文名稱(English)」；例如「紀錄檔(Log)」「指令碼屬性(Script Properties)」「觸發器(trigger)」「部署(deployment)」，不得只使用英文術語或縮寫。
- 面向使用者第一次提到 `clasp push` 時，先說明它是由 Agent 把本機已完成並通過測試的程式與資訊清單同步到指定的 Google Apps Script 專案；這只更新遠端程式，不等於執行函式、寄信、建立觸發器或部署。固定稱為「推送到Apps Script(clasp push)」，後續確認、進度與結果不得只顯示英文命令；終端命令與 Agent 內部工程檢查仍使用原始 `clasp push`。
- 新專案預設使用依功能分檔的 `.gs`，避免為一般 Apps Script 增加不必要的編譯流程。
- 只有專案複雜度確實需要型別檢查、npm 套件或模組化建置時，才使用 TypeScript；此時必須同時建立 bundler、建置輸出檢查與專用推送目錄，絕不直接推送原始 `.ts`。
- 所有新程式碼加入必要的繁體中文註解與可診斷的繁體中文紀錄檔(Log)。
- `appsscript.json` 只使用完成需求所需的最小 OAuth scopes。
- `appsscript.json`有變更時，`clasp push`可能另外詢問是否覆寫資訊清單。這種情況第一次就必須使用互動式終端執行一般 `clasp push`，讀到提示且目標與待推送內容仍符合使用者確認摘要時才回答確認；不得先用非互動模式試跑。若已只回覆`Skipping push`，不得宣告成功，也不得改用強制推送，應在完成差異檢查後以互動式終端重跑同一個一般 `clasp push`。
- `.clasprc.json`、`.clasp.json`、OAuth 憑證、API Key、Token、私人 ID 與測試個資不得進入 Git 或一般回覆。教學模式有三個窄例外：Agent 第一次建立並驗證教學 Apps Script 專案後，可在目前的私人教學對話提供可點擊的 Apps Script 編輯器網址，但不得另外列出原始 Script ID；Agent 建立的一般 Google 資源需要填入指令碼屬性時，可在重新核對後提供該資源的可點擊網址與完整資源 ID；第二階段第 8 課可依教學技能規則，用本機安全亂數產生並顯示一次只供當課使用的 `WEBHOOK_TOKEN` 臨時教學密語，明確說明它不適合正式使用且不得要求學生回傳。三者都不得保存到教材、紀錄檔(Log)、課程進度或 Git，學生自行更換的正式值不得進入對話。

## 遠端確認

執行以下動作前必須顯示目標、影響與待處理摘要，取得使用者明確確認：

- 建立遠端 Apps Script 或綁定型 Google 檔案。
- `clasp pull` 或 `clasp push`。
- 建立、更新或刪除觸發器。
- 建立、更新或刪除 deployment。
- 建立 GitHub repository、設定 remote 或執行 `git push`。

確認只適用於當次摘要，不延伸到後續操作。

## 第一版範圍

- 個人 Google 帳號可使用。
- 不需要信用卡、付費 Workspace 或管理員身分。
- 使用 Apps Script 內建服務、基礎觸發器及簡單 Web App／Webhook。
- 第一階段「指定資料夾檔案上傳紀錄器」可使用唯讀的 Google Drive Activity v2，作為唯一已確認的進階服務例外；它使用 Apps Script 預設 Cloud 專案，不要求付費或標準 Google Cloud 專案。
- 除上述窄例外外，進階 Google 服務、Add-on、Google Chat App、Admin SDK、標準 Google Cloud 專案、外部付費 API 與 Marketplace 留待下一版。

## 交付

回報本機路徑、專案類型、Git commit、測試結果、待推送檔案、OAuth 影響、已完成遠端操作與尚未驗證項目。命令成功不等於遠端完成，必須查驗實際 Apps Script 與 Google Workspace 結果。
