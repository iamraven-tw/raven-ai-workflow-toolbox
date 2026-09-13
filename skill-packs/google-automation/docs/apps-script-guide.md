# Learn-GAS：讓 AI Agent 帶你完成 Google Apps Script 自動化

Learn-GAS 是一套面向 Google Apps Script 初學者的 Agent Skills。使用者不需要先學會程式語法，也不需要親自操作終端機；只要說明想完成的工作，AI Agent 就會協助規劃、撰寫、測試與管理程式，再把登入、授權、真正的介面操作及成果判斷留給使用者完成。

這套技能同時支援：

- Anthropic Claude Code
- OpenAI Codex
- Google Antigravity

三種 Agent 使用同一套教學、專案開發與安全規則，但各自的技能安裝位置與啟動文件不同。第一次使用前請先閱讀[安裝規格](../INSTALL.md)。

整個專案將 Google Apps Script 工作拆成「教學」「專案開發」「除錯」與「Google Docs 固定版面」四個清楚責任，避免同一個技能同時承擔課程、環境、修正與排版工作。

## 這個專案要解決什麼問題

Google Apps Script 可以把 Google Sheets、Forms、Docs、Drive、Gmail 與其他 Google 服務串成自動化流程，但第一次接觸的人通常會同時遇到程式、權限、設定、測試與介面操作等多種問題。

Learn-GAS 把這些工作重新分配：

- AI Agent 負責理解需求、建立本機檔案、撰寫程式、執行工程測試、管理 `clasp` 與本機 Git。
- 使用者負責帳號登入、授權、必要設定、真正的功能操作及可見成果驗收。
- 推送到Apps Script(clasp push)、建立觸發器、部署與 GitHub 遠端操作都必須分別取得使用者確認。
- 技術術語先用白話解釋用途，再提供固定的中文名稱(English)，避免只看到難懂的縮寫。

這不是讓使用者背誦語法的教材，而是一套教使用者如何指揮、檢查與驗收 AI Agent 的實作流程。

## 專案包含的技能

### Google Apps Script 專案開發

入口：[google-apps-script-project-development](../skills/google-apps-script-project-development/SKILL.md)

負責整套技能的共同分流，以及開發環境、需求釐清、本機專案、Git、`clasp`、OAuth、遠端同步、觸發器與部署確認。使用者只說想使用 Google Apps Script 時，使用 `google-apps-script-project-development` 作為共同分流入口，先詢問要做專案或學習。

### Google Apps Script 教學

入口：[google-apps-script-teaching](../skills/google-apps-script-teaching/SKILL.md)

負責初學者課程、進度管理、逐課說明與成果驗收。課程分成五個獨立生活案例，以及一套逐課累積的活動報名與通知系統。

### Google Apps Script 除錯

入口：[google-apps-script-debugging](../skills/google-apps-script-debugging/SKILL.md)

負責重現問題、讀取繁體中文紀錄檔(Log)、區分需求邏輯與實作錯誤、完成最小修正及回歸測試。教學或實際專案發生錯誤時都使用同一套除錯流程。

### Google Docs 固定版面

入口：[google-docs-layout](../skills/google-docs-layout/SKILL.md)

負責信封、標籤、證書、名牌、票券等固定版面，將位置、字體、方向與分頁需求轉成 Apps Script 程式與實際文件驗收。本技能不是新的首頁模式，只有選定的教學案例或實際專案涉及固定版面時才會使用。

## 教學內容

### 第一階段：五個獨立案例

第一階段不要求依編號完成。Agent 會讀取課程進度並列出尚未完成的案例，讓學員自由選擇。

| 案例 | 主要 Google 服務 | 可以看到的成果 |
|---|---|---|
| 家庭支出記錄表 | Google Sheets | 建立支出資料、分類與可檢查的表格結果 |
| 批次信封版面產生器 | Google Docs | 從設定與資料產生可列印的信封版面 |
| 教師隨機測驗與成績報表 | Google Forms、Sheets | 產生測驗並整理成績資料 |
| 指定資料夾檔案上傳記錄器 | Google Drive、Sheets | 定期檢查指定資料夾並記錄檔案 |
| 個人化批次郵件寄送器 | Gmail、Sheets | 依收件資料產生並安全處理個人化郵件 |

這五個案例的完整已驗收 `.gs` 程式位於 [`skills/google-apps-script-teaching/templates/beginner/`](../skills/google-apps-script-teaching/templates/beginner/)。Agent 應安全取用模板，不重新生成同一套業務程式，也不得覆寫內容不同的既有學員專案。

### 第二階段：活動報名與通知系統

第二階段使用同一個專案逐課累積完整自動化流程。開始後固定依序完成第 1 至第 8 課，中途可以暫停，下次由 Agent 從最早未完成處恢復。

| 課次 | 課程 | 本課加入的能力 |
|---|---|---|
| 第 1 課 | [Google Sheets 基礎讀寫](../skills/google-apps-script-teaching/references/lessons/lesson-01-sheets.md) | 建立與更新活動報名資料，理解試算表、工作表與資料範圍 |
| 第 2 課 | [Script Properties 與設定檢查](../skills/google-apps-script-teaching/references/lessons/lesson-02-properties.md) | 把資源設定與程式分開，缺少設定時安全停止 |
| 第 3 課 | [Google Forms 收集資料與資料驗證](../skills/google-apps-script-teaching/references/lessons/lesson-03-forms.md) | 建立報名表單、驗證輸入並寫入試算表 |
| 第 4 課 | [Google Sheets 批次處理](../skills/google-apps-script-teaching/references/lessons/lesson-04-batch.md) | 整批驗證資料並產生可追蹤的處理狀態 |
| 第 5 課 | [Google Docs／Drive 產生文件](../skills/google-apps-script-teaching/references/lessons/lesson-05-docs-drive.md) | 依報名資料建立確認文件並避免重複產生 |
| 第 6 課 | [Gmail 報名通知](../skills/google-apps-script-teaching/references/lessons/lesson-06-gmail.md) | 建立安全的通知流程並防止重複寄送 |
| 第 7 課 | [表單觸發器與時間觸發器](../skills/google-apps-script-teaching/references/lessons/lesson-07-triggers.md) | 讓新報名與待辦工作在背景自動進入流程 |
| 第 8 課 | [Web App／Webhook](../skills/google-apps-script-teaching/references/lessons/lesson-08-webapp-webhook.md) | 建立受控的外部入口並完成完整自動化 |

每一課都包含：

- 學員看得見的真正 Google 服務成果。
- 正常、錯誤、缺少設定與重複執行測試。
- 防止同一筆工作重複建立、寄送或處理的設計。
- 可讀的繁體中文紀錄檔(Log)。
- 必要權限與外部影響說明。
- 使用者操作順序與成功判斷。
- 課末一題不阻擋進度的簡短理解題。

教學模式的正常、錯誤、重複執行及課程特有工程測試由 Agent 完成；使用者只完成必要設定、授權、真正的 UI 使用流程與可見成果判斷。

五個第一階段案例與第二階段八課的累積快照都已在[模板目錄](../skills/google-apps-script-teaching/templates/)及[模板清單](../skills/google-apps-script-teaching/templates/catalog.json)中標記為 `validated`。這代表技能包內的模板已通過既定驗證，不代表程式已推送到任何使用者的 Apps Script、已建立觸發器或已完成部署。

## 安裝與開始使用

本指南說明 Toolbox 內原 Learn-GAS 的課程與功能。取得 raven-ai-workflow-toolbox 後，依 [唯一安裝規格](../INSTALL.md) 選擇 Google 自動化技能包。可以單獨安裝，不需要其他五包。

所有後續修改與變更提案(Pull Request)只提交 raven-ai-workflow-toolbox。學員專案保存在使用者自己的工作區。

## 學員專案與技能儲存庫必須分開

Toolbox 技能包保存可重複使用的技能、教案、驗收模板與工具，不是放置個人 Apps Script 專案的工作區。

使用者未指定位置時，Agent 會查詢作業系統真正的「文件」資料夾，並將學員專案建立在：

```text
GoogleAppsScript/<專案名稱>/
```

第二階段活動報名教學預設使用 `activity-registration`。不得把學員的 `.clasp.json`、程式設定、課程進度或私人 Google 資源資料寫回 Toolbox 技能儲存庫。

## 品質與安全原則

- 第一版以個人 Google 帳號可免費使用的 Apps Script 內建服務為範圍。
- 實際專案與教學共用指令碼屬性(Script Properties)檢查、正常／錯誤／重複執行測試、可見成果及繁體中文紀錄檔(Log)標準。
- Apps Script 更新 Sheets 時預設保留使用者手動調整的欄寬，只有第一次建立版面或需求明確指定時才設定。
- 建立全新專案與接管既有專案使用不同流程；接管前先唯讀盤點並保護既有狀態。
- OAuth 權限採完成需求所需的最小範圍。
- 不得提交 `.clasprc.json`、`.clasp.json`、OAuth 憑證、API 金鑰、Token 或私人 Script ID。
- Agent 預設不操作使用者的電腦或瀏覽器介面；只有使用者明確要求時才協助操作當次指定的介面。
- 只要要求使用者開啟、切換或操作任何網頁，Agent 必須在同一則指示提供已核對且可點擊的目標連結；尚未取得連結時先取得，不要求使用者自行尋找頁面。
- 推送到Apps Script(clasp push)、建立觸發器、部署、建立 GitHub 遠端或公開發布前，都必須取得各自的使用者確認。

## 驗證技能包

在 Google 技能包目錄執行：

```bash
python3 scripts/validate_skills.py
```

這項驗證檢查技能結構、必要文件、教學路由與安全規則。通過本機驗證不代表已安裝到任何 Agent，也不代表已對 Google 或 GitHub 執行遠端操作。

## 官方參考資料

- [Google Apps Script：使用 clasp](https://developers.google.com/apps-script/guides/clasp)
- [Google Apps Script：專案資訊清單](https://developers.google.com/apps-script/manifest)
- [google/clasp](https://github.com/google/clasp)
- [Claude Code：Skills](https://code.claude.com/docs/en/skills)
- [OpenAI Codex：Skills](https://developers.openai.com/codex/skills)
- [Google Antigravity：Agent Skills](https://antigravity.google/docs/skills)

## 使用、修改與貢獻

此功能已整併至 raven-ai-workflow-toolbox 公開專案。任何人都可以下載、使用、修改及散布，也可以建立自己的副本(Fork)，再透過變更提案(Pull Request)分享改善內容。

個人 Apps Script 專案、Google 帳號設定與私人資料不需要公開，也不應提交回 Toolbox 技能包。

## 非官方聲明

本教材源自 Learn-GAS，現在是 Raven AI 一人公司工具包的一部分，並非 Google、Anthropic 或 OpenAI 的官方產品，也未獲得這些公司背書。Google Apps Script、Claude Code、Codex、Antigravity 及其他產品名稱與商標均屬其各自權利人所有。

## 授權

本教材與原 Learn-GAS 技能採用 [MIT License](../LICENSE.learn-gas)。任何人都可以使用、複製、修改、合併、發布及散布本專案，也可以用於私人或商業用途；再散布時必須保留原始著作權與授權聲明。

Copyright (c) 2026 iamraven-tw
