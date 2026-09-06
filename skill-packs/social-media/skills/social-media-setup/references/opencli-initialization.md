# 專案初始化：OpenCLI

## 範圍與入口

使用者要求實際初始化社群專案時，預設把 OpenCLI 列入本機工具準備，不等到搜尋失敗才提出。只討論策略、查閱設定、安裝技能檔案或執行既有明確任務，不因此強制安裝。拒絕／延後者仍可使用可用的正式 API、公開搜尋或手動預覽；不能宣稱瀏覽器整合完成。

OpenCLI 是作者維護的開源瀏覽器工具，不是 Meta／Google／X 的官方 API。固定來源以本技能的 [來源契約](opencli-source.json) 為準，由套件 manifest 指向；不能改抓 `latest`、`main`、同名 fork 或搜尋廣告。來源與操作規範一起隨技能安裝，執行時不依賴 Toolbox 根目錄。

## 下載前告知與最小人工確認

Agent 先做不觸碰瀏覽器帳號的工具版本／路徑檢查，再向使用者說明：

> 我會從 OpenCLI 作者的 GitHub 開源專案 https://github.com/jackwener/opencli 下載已固定版本的程式與瀏覽器擴充功能，準備讓 AI 操作你指定的 Chrome。它不是社群平台的官方 API；擴充功能有所有網站、分頁、Cookie 與除錯等廣泛存取權限。我會列出版本、保存位置、依賴下載與可能變動，且不因此登入帳號、發布、回覆或排程。你可以拒絕或延後這項安裝。

實際提醒必須補上來源契約的版本、完整 commit、GitHub 下載 URL、Apache-2.0 授權、目的地、所需 Git／Node.js／npm／Chrome，以及容量與費用：擴充壓縮檔 45,776 bytes；原始碼與 npm 依賴容量尚未實測，不虛構精確值；沒有此流程要求的付費訂閱，但會下載資料並占用磁碟，平台 API 費用另計。只向 npm registry 取得鎖檔指定的相依套件，不把它們描述成全由 GitHub 下載。

取得這份本機安裝預覽的一次確認後，由 Agent 下載、核對、解壓縮、安裝依賴、建置及檢查。若使用者已明確核准相同版本、範圍與目的地，仍在下載前提醒，但不逐條命令重問。只有「初始化」且還沒看過這些影響時，不能用告知取代確認；使用者沉默不算同意。這份核准不等於同意登入、平台 OAuth 或遠端寫入。

## Agent 執行流程

1. **唯讀盤點。** 找到明確的私人專案與工具位置，檢查 Git、Node.js、npm、Chrome、既有 OpenCLI 可執行檔與版本；已有可用版本就優先沿用，記錄與固定候選的差異，不默默升降級。只查工具檔案，不列印環境變數、Cookie 或登入資料。來源建置候選採 Node.js 22.x 且至少 22.13.0，或 24.x：上游說明的最低版本與鎖檔依賴不完全一致，不能只看 `package.json` 的最低值。缺少前置工具時，另列其官方來源、版本與安裝影響，補足核准前不擅自安裝。
2. **預覽位置與影響。** 新下載預設放在私人專案 `.local/tools/opencli/<version>/source` 與同版本 `extension`，不放入技能掃描目錄、公開 Toolbox 或內容資料目錄，確認 Git 忽略這些產物；忽略設定變更也列入預覽。若當地明確指定擴充功能標準位置，沿用當地規則，不把維護者的路徑寫死。既有非空目錄、符號連結或共享 OpenCLI 狀態有衝突就停止，不整理、覆蓋或刪除。先列出 npm cache、OpenCLI 使用者層級狀態、Chrome 擴充資料及本機 daemon 的影響，不聲稱所有寫入都只在專案內。
3. **從 GitHub 取得固定來源。** 確认同一份預覽已核准後，以 HTTPS 在新的來源目錄執行 `git clone --depth 1 --single-branch --branch <tag> <download_url> <source-dir>`，所有佔位符由來源契約及核准目標解析。讀回 `git rev-parse HEAD`、`git rev-parse HEAD^{tree}` 與遠端 URL，分別比對完整 commit、tree 與作者來源；再核對 `LICENSE` 與 `package-lock.json` 的 SHA-256。失敗就停止，不能改用最新版本或先執行建置。保留原 LICENSE 及存在時的 NOTICE，不修改上游程式。
4. **下載擴充功能。** 由 Agent 取得契約的 GitHub Release 資產，先核對 SHA-256 與大小，再檢查 ZIP 路徑不會跳出新目錄、沒有絕對路徑或符號連結，才解壓縮。找到 `manifest.json`、核對版本、權限、`<all_urls>` 與 background 指向檔案存在；與預覽不同就停止重新確認。來源契約的資產雜湊來自 GitHub Release metadata，本機下載時仍必須真正計算比對。
5. **本機建置 CLI。** 在已核對的 source 目錄使用 npm 鎖檔：`npm ci --ignore-scripts --no-audit --no-fund`，再明確執行 `npm run build`。這會下載依賴並執行已核對專案的建置程式，不是零風險操作。跳過自動安裝腳本，避免上游 postinstall／全域安裝改動其他工具；不執行 `npm link`、`npm install -g`、`npx skills add` 或額外 adapter 安裝。建置若因被略過的相依腳本失敗，停下查明原因，只預覽必要的特定補救，不全面開啟腳本、換版或重裝。以 `node <source-dir>/dist/src/main.js --version` 讀回版本；後續以這個確定入口取代不明的全域 `opencli`。
6. **啟用 Browser Bridge。** Agent 用環境允許的既有控制工具開啟指定 Chrome 的 `chrome://extensions`，盡可能代辦可操作步驟。首次缺少可用瀏覽器控制入口、瀏覽器保護或企業政策阻擋時，只把「啟用開發人員模式／載入解壓縮目錄／允許擴充權限」中實際必須由人執行的步驟交回；給出已準備好的確切路徑，不叫使用者重新下載或執行命令。不能用尚未安裝的 OpenCLI 安裝它自己，也不繞過企業政策。啟用本身不要求社群登入。
7. **分層驗證。** 完整 CLI 啟動可能建立／改寫使用者層級 `.opencli` 的模組連結、讀取既有自訂 adapter／plugin，並啟動 daemon；這些不屬於純唯讀檔案檢查。執行前確認它們已列入核准範圍，遇到其他來源的衝突停下，不載入來源不明的自訂程式。依固定版 `--help` 與 Browser Bridge 文件，執行 `doctor`、辨識連線中的 Chrome；多個 profile 不能猜。用專供驗證的新分頁讀取不需登入的中性公開頁，核對標題與網址。只有版本輸出或 doctor 成功，不能標示五平台可搜尋；社群登入、各平台搜尋／讀回均為另外驗收。
8. **記錄與交接。** Agent 在核准的私人 `.local/social-media/opencli-state.json` 保存下方最小狀態；顯示摘要後交回原初始化工作，不要求使用者保存技術資料。後續內容規劃只沿用已驗證的入口與授權，不重新安裝或默默擴權。

## 狀態、重跑與移除

最小非敏感紀錄：來源契約版本與 commit、核准目的地、實際程式與擴充版本、各次雜湊檢查結果、`source`／`dependencies`／`cli`／`extension`／`bridge` 各層狀態、最後實際驗證時間、停止原因。狀態值用 `not_started`、`verified`、`blocked`、`declined`；`source: verified` 不提升其他層。沒有執行不得填驗證時間，不保存 Token、Cookie、帳號名稱、分頁內容或一般瀏覽歷史，也不改寫既有 setup-state schema。

重跑先讀回檔案與狀態：核對過且未變動的來源不重抓；不完整目錄保留，確認後使用新的 staging 位置；安裝／建置出錯不能宣稱已就緒。已存在 OpenCLI 時不關閉其他 daemon、不切換他人的 profile、不更新共享設定。若要更新，使用新固定版本目錄，重新預覽來源、權限與共享狀態影響；驗證前保留舊入口。回復要同時考慮擴充功能路徑與使用者層級狀態，不能只換 CLI 就宣稱成功。

移除技能不連帶移除 OpenCLI。使用者另行要求時，先盤點哪些專案共用，再預覽確切管理範圍；專屬來源／擴充目錄可移到可回復隔離區，Chrome 解除載入另驗證。不遞迴刪除整個使用者目錄、共用 `.opencli`、npm cache 或瀏覽器 profile。

## 查證與未驗證範圍

查證日期：2026-09-05。以下只讀官方作者來源；本輪未下載完整程式或 Release 資產、未安裝依賴、未建置或啟用瀏覽器。上述來源建置調整是 Toolbox 的候選操作流程，須集中實機驗收，不是上游保證已支援的安裝器。

- [官方 GitHub](https://github.com/jackwener/opencli)、[固定版本 Release](https://github.com/jackwener/OpenCLI/releases/tag/v1.8.8)。
- [上游安裝說明](https://github.com/jackwener/opencli/blob/8271afc67e8504bda94c147f446ee29775d08274/docs/guide/installation.md)、[套件與建置命令](https://github.com/jackwener/opencli/blob/8271afc67e8504bda94c147f446ee29775d08274/package.json)、[鎖檔](https://github.com/jackwener/opencli/blob/8271afc67e8504bda94c147f446ee29775d08274/package-lock.json)。
- [擴充權限](https://github.com/jackwener/opencli/blob/8271afc67e8504bda94c147f446ee29775d08274/extension/manifest.json)、[Browser Bridge](https://github.com/jackwener/opencli/blob/8271afc67e8504bda94c147f446ee29775d08274/docs/guide/browser-bridge.md)。
- [安裝腳本](https://github.com/jackwener/opencli/blob/8271afc67e8504bda94c147f446ee29775d08274/scripts/postinstall.js)、[全域 adapter 更新行為](https://github.com/jackwener/opencli/blob/8271afc67e8504bda94c147f446ee29775d08274/scripts/fetch-adapters.js)、[首次 CLI 發現](https://github.com/jackwener/opencli/blob/8271afc67e8504bda94c147f446ee29775d08274/src/discovery.ts)。
