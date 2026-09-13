# Google 工具自動化

這是給 AI Agent 使用的 Google 自動化分流與安裝技能包。它先理解使用者真正要完成的工作，再選擇 Google Apps Script、Google Workspace API／OAuth，或 Cloud Run／Cloud Scheduler 路線。

目前狀態是**可安裝的外部驗收候選版**，不是正式支援版本。Agent 端的固定來源、安裝生命週期、公開測試與路徑檢查完成後，仍要由使用者在另一臺電腦或另一個 Google 帳號完成一次最終實機驗收。

## MVP 能做什麼

1. 先整理目標、資料、使用者、觸發方式、執行時間、流量、權限與驗收方法。
2. 將學習、修改、除錯、接管既有 Apps Script 與 Google Docs 固定版面需求，分流到本包內建的四個 Apps Script 技能。
3. 判斷何時應直接使用 Workspace API，並選擇 API key、使用者 OAuth 或服務帳戶等身分模式。
4. 判斷何時 Apps Script 的時間、流量、公開端點或執行生命週期不適合，改走 Cloud Run service、Cloud Run job 或 Cloud Scheduler。
5. 把本機完成、Google 登入、OAuth 授權、遠端資源／部署與人工驗收分成獨立狀態。
6. 在任何登入、OAuth、遠端寫入、資源建立、部署或可能計費前停下來，顯示目標與影響並取得明確同意。

## MVP 不包含

- 一次支援所有 Google 產品，或提供一般性的 Google Cloud 百科。
- Workspace Marketplace 外掛、Google Chat 應用程式、Admin SDK、網域層級委派、多租戶公開 OAuth 應用程式及其驗證送審。
- 正式環境的基礎設施即程式碼、監控、SLA、災難復原、合規或資安認證。
- 自動建立 Google Cloud Project、啟用 API、建立 OAuth client、設定帳務、部署、`clasp push` 或外部登入。
- 在 Learn-GAS 舊儲存庫另行維護或同步第二份 Apps Script 教材。

完整使用者故事與停止條件見 [`docs/mvp-boundary.md`](docs/mvp-boundary.md)。

## 單一來源

從 Google 技能包 0.2.0 起，原 Learn-GAS 四個技能、範例與測試直接在本包維護。所有安裝與更新只需 Toolbox；不再取得 Learn-GAS clone。

原始來源與 MIT 聲明保留於 [來源政策](docs/single-source.md) 與 [授權](LICENSE.learn-gas)。課程及功能說明見 [Apps Script 指南](docs/apps-script-guide.md)。舊版遷移方式見 [安裝規格](INSTALL.md)。

## 使用方式

讓具備本機檔案與終端機操作能力的 AI Agent 從 [`INSTALL.md`](INSTALL.md) 開始。安裝管理器本身不連網、不登入 Google、不建立雲端資源，也不執行 `clasp push`；它只把已驗證的本機來源註冊到使用者指定的技能目錄。

## 文件

- [`INSTALL.md`](INSTALL.md)：Agent 安裝、更新、回復與移除入口。
- [`install.manifest.toml`](install.manifest.toml)：機器可讀的來源、版本、用戶端與狀態。
- [`docs/architecture.md`](docs/architecture.md)：元件、資料與權限邊界。
- [`docs/inventory.md`](docs/inventory.md)：Toolbox／Learn-GAS 實際能力、重複內容、缺口與待辦。
- [`docs/mvp-boundary.md`](docs/mvp-boundary.md)：使用者故事、路線與未包含範圍。
- [`docs/compatibility.md`](docs/compatibility.md)：三種 Agent 與執行環境狀態。
- [`tests/acceptance-checklist.md`](tests/acceptance-checklist.md)：Agent 端門檻與最後一次外部驗收。
- [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)：Learn-GAS 與工具來源、授權和散布方式。

公開版只接受人工挑選、去識別化並重新驗證的版本快照，不與任何私人工作目錄自動同步。
