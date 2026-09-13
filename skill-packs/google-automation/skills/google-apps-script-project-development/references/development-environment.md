# 共用首次使用關卡：檢查並準備開發環境

## 定位

這是整組 Google Apps Script 技能共用的 Agent-first 環境關卡，不是教學課程。使用者未指定目的時，先完成「做專案或學習」及後續專案／案例選擇；目標選定後，不論接下來要學習、建立／接管專案或除錯，都必須觸發本流程。

AI Agent 負責檢查環境、執行安裝命令、建立本機檔案與驗證結果；使用者不需要親自手寫程式或逐條輸入終端機命令。

使用者只在以下情況親自操作：

- 核准作業系統的管理員權限或軟體安裝提示。
- 既有 OAuth 無法驗證、帳號有歧義或即將進行遠端寫入時，確認要使用的 Google 帳號。
- 在瀏覽器完成 Google 登入與 OAuth 授權。
- 處理 CAPTCHA、兩步驟驗證或組織管理員政策。
- 決定可能影響既有專案或帳號的操作。

如果 Agent 不能存取終端機與本機檔案，停止本流程並說明：目前的 Agent 無法完成本機 `clasp` 工作流程。不要把整套安裝命令改丟給初學者自行處理。

## 兩層環境關卡

目標選定後，共用環境分成兩層，避免誤建不需要的教學或開發專案：

1. **電腦層首次健檢**：在模式與案例／專案選定後完成，檢查作業系統、文件資料夾、Node.js、npm、Git、Apps Script API 與既有 `clasp` OAuth。
2. **目標專案層健檢**：使用者選擇教學、建立、接管或除錯目標後立即完成，檢查實際專案目錄、Git repository、忽略規則、套件設定及專案內 `clasp`。

不得為了完成電腦層健檢，先建立 `activity-registration` 或其他假專案。除錯既有專案時，也不得把新工具設定寫入錯誤的目錄。

## 本流程成果

完成後應具備：

- 已確認的作業系統、CPU 架構、Shell 與專案目錄。
- 已由作業系統解析的「文件」資料夾，以及位於其中的 `GoogleAppsScript` 工作根目錄。
- 仍受支援的 Node.js LTS，以及可用的 npm／npx。
- 已安裝並驗證的 Git。
- 已啟用的 Apps Script API。
- 已用唯讀命令驗證有效的 `clasp` OAuth；只有帳號有歧義時才要求使用者選擇。
- 目標確定後，安裝在該專案內且版本已固定的 `@google/clasp`。
- 除非使用者明確停用，目標專案已有安全 Git 基線 commit。
- 保護 `.clasprc.json`、`.clasp.json`、`node_modules` 與秘密資料的忽略規則。

本流程不建立或接管遠端 Apps Script 專案，也不執行 `clasp pull`、`clasp push`、部署或觸發器操作。

## 核心原則：先檢查，再決定是否安裝

第一次從教學、專案開發或除錯任一入口使用本技能組時，選定目標後的第一個環境動作永遠是唯讀健檢。Agent 不得預設使用者尚未安裝，也不得為了統一環境而重裝已經通過驗收的工具。

後續再次使用任一技能時，若本次工作已有可驗證的健康結果，只快速複核實際版本、路徑與目標專案狀態；不得只依賴舊紀錄，也不得無故重跑安裝或 OAuth。

健檢後分成四種結果：

| 結果 | Agent 行為 |
|---|---|
| **環境完整** | 不安裝、不升級、不重新登入；記錄現有版本與路徑，直接完成本流程 |
| **部分缺少** | 保留健康項目，只安裝或設定缺少的部分，再重新驗證 |
| **版本或路徑衝突** | 先找出實際執行來源與影響，向使用者說明後才修復；不盲目重裝 |
| **無法檢查** | 說明缺少的 Agent 能力或權限並停止，不把整套命令丟給初學者 |

「已經安裝」不等於「環境完整」。必須符合下列跳過標準：

| 項目 | 可以跳過安裝或設定的條件 |
|---|---|
| Node.js | 版本仍受支援、符合目前 `clasp` 引擎需求，而且實際路徑可確認 |
| npm／npx | 可執行，且與目前 Node.js 屬於同一套環境 |
| 專案內 clasp | 已記錄在 `package.json`／lockfile，版本相容，`--version` 與 `--help` 實際成功 |
| 全域 clasp | 只作為已存在資訊；不能取代技能預設的專案內固定版本 |
| Git | 命令可用、路徑可確認、repository 狀態已盤點，而且預設上版規則可執行；不重裝既有 Git |
| 忽略規則 | 必要項目已存在；只補缺少規則，不覆寫使用者原有內容 |
| Apps Script API | 目前帳號的開啟狀態已實際確認，或已由成功的唯讀 API 呼叫證明 |
| clasp OAuth | 既有授權仍有效，而且 `show-authorized-user` 與 `list-scripts` 等唯讀驗證命令成功；帳號沒有歧義 |

因此，已完整設定過的使用者可能在選定目標並完成唯讀健檢後，直接進入所選流程，不需要再次安裝 Node.js、`clasp` 或重新執行 OAuth。

## 預設工作目錄

如果使用者沒有指定其他位置，Agent 將專案放在作業系統實際的「文件」資料夾下：

| 環境 | 預設結構 |
|---|---|
| macOS | `<文件資料夾>/GoogleAppsScript/<專案名稱>` |
| Windows | `<文件資料夾>\GoogleAppsScript\<專案名稱>` |
| WSL | 選定 WSL 或 Windows 工具鏈後，使用同一側的文件資料夾與 Node.js，不跨兩邊混用 |

`GoogleAppsScript` 只是使用者 Apps Script 專案的共同工作根目錄，不是這個技能儲存庫。實際專案必須再建立自己的子目錄。

教學模式使用「活動報名與通知系統」時，預設專案資料夾名稱為 `activity-registration`。例如，常見結果可能是：

- macOS：`/Users/<user>/Documents/GoogleAppsScript/activity-registration`
- Windows：`C:\Users\使用者名稱\Documents\GoogleAppsScript\activity-registration`

以上只是常見範例，不能當成實際路徑。Agent 必須向作業系統查詢真正的文件資料夾，因為資料夾可能使用當地語系名稱，或被 iCloud、OneDrive、組織政策重新導向。

### macOS 解析方式

```bash
# 由 macOS 查詢目前使用者真正的文件資料夾，不直接假設為 ~/Documents。
documents_directory="$(osascript -e 'POSIX path of (path to documents folder)')"
printf '%s\n' "$documents_directory"
```

Agent 將查詢結果去除結尾斜線後，加上 `GoogleAppsScript/<專案名稱>`。不得重新定義或改寫 `$HOME`。

### Windows 解析方式

在 PowerShell 使用系統 API，不直接拼接 `C:\Users\<名稱>\Documents`：

```powershell
# 取得目前 Windows 帳號真正的文件資料夾，包含 OneDrive 或組織重新導向。
$documentsDirectory = [Environment]::GetFolderPath('MyDocuments')
$projectRoot = Join-Path $documentsDirectory 'GoogleAppsScript'
$projectDirectory = Join-Path $projectRoot 'activity-registration'

$documentsDirectory
$projectDirectory
```

### WSL 解析方式

如果 Agent 與 Node.js 位於 WSL，預設使用 WSL 端的文件資料夾；若 `xdg-user-dir DOCUMENTS` 可用就採用其結果，否則確認 WSL 使用者家目錄下是否已有 `Documents`。不要把 WSL `node_modules` 與 Windows Node.js、Windows `clasp` 憑證交叉使用。

若使用者明確選擇 Windows 工具鏈，就改由 Windows PowerShell 解析 `MyDocuments`，並在 Windows 端完成整個專案。

### 建立前檢查

Agent 解析出完整路徑後：

1. 顯示預計使用的絕對路徑。
2. 唯讀檢查 `GoogleAppsScript` 工作根目錄及專案目錄是否已存在。
3. 目錄不存在或為空時，才建立該專案目錄。
4. 目錄已有檔案時，先盤點內容；不得覆寫、清空或直接初始化。
5. 專案名稱需移除 Windows 不允許的 `\ / : * ? " < > |` 等字元，並避免使用 `.`、`..` 或空白名稱。
6. 如果文件資料夾由 iCloud、OneDrive 或其他服務同步，先告知 `node_modules` 也可能被同步；使用者未指定其他位置時仍沿用文件資料夾，但不得隱瞞這項影響。

使用者若已指定安全的專案目錄，就沿用該位置，不強制搬到文件資料夾。既有專案也不得因本規則自動搬移。

不得把使用者的新專案建立在任何技能來源目錄、`skills/google-apps-script-*` 目錄或 Learn-GAS 儲存庫內。技能目錄只保存教材、範例與驗證工具，不作為使用者專案的工作位置。

## 開始前不要重複詢問可驗證項目

Agent 能自行偵測的資訊不要反問使用者：

1. 顯示 Agent 解析出的預設專案目錄；使用者沒有提出其他位置時就採用，不要求回覆確認。
2. 先用 `show-authorized-user` 與 `list-scripts` 等唯讀命令驗證既有 OAuth。驗證成功且沒有帳號歧義時，直接沿用並進入下一步，不再詢問「要使用哪個 Google 帳號」。
3. 只有未登入、授權失效、存在多組 named credentials、組織政策限制、偵測結果與使用者指定帳號不一致，或使用者主動要求換帳號時，才詢問帳號。
4. 即將建立遠端專案、執行 `clasp push` 或部署時，把實際帳號列在該次遠端操作摘要中一起確認，不另外插入一個沒有必要的帳號問題。

不要要求使用者提供密碼、OAuth 權杖、完整 `.clasprc.json` 或私人 Script ID。

## 環境步驟一：唯讀健檢與結果分類

任何安裝前，Agent 先執行唯讀檢查。

### macOS

```bash
# 確認作業系統、CPU 架構與目前 Shell。
uname -s
uname -m
printf '%s\n' "$SHELL"

# 找出實際會執行的工具與版本。
command -v node
command -v npm
command -v npx
command -v git
command -v clasp
node --version
npm --version
npx --version
```

若工具不存在，允許單一檢查命令失敗，繼續整理其餘結果。不得因第一個 `command -v` 失敗就中止整份健檢。

另外確認：

- `arm64` 代表 Apple Silicon，`x86_64` 代表 Intel。
- 是否已有 Homebrew、nvm、fnm、Volta 或其他 Node 管理方式。
- `npm config get prefix` 與實際 `node` 路徑是否屬於同一套環境。
- Shell 中是否有同名函式、別名或舊版執行檔遮蔽新版本。

### Windows

在 PowerShell 執行唯讀檢查：

```powershell
# 確認 Windows、CPU 架構與 PowerShell 環境。
[System.Runtime.InteropServices.RuntimeInformation]::OSDescription
[System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
$PSVersionTable.PSVersion

# 找出目前 PATH 上的工具；缺少工具時不終止整份健檢。
Get-Command node, npm, npx, git, clasp -All -ErrorAction SilentlyContinue
node --version
npm --version
npx --version
```

另外確認：

- 使用的是原生 Windows、WSL，還是 Agent 本身位於 WSL。
- Node.js 安裝架構是否與 Windows 架構相符。
- 安裝完成後是否需要重開終端機才能取得新 PATH。
- PowerShell 是否只擋住 `npm.ps1`／`npx.ps1`，但 `npm.cmd`／`npx.cmd` 可正常執行。

如果使用 WSL，整個專案必須選定在 WSL 或 Windows 其中一邊執行。不要混用 Windows Node、WSL Node、兩邊的 `node_modules` 或不同位置的 `clasp` 憑證。

健檢完成後，Agent 先產出「環境完整／部分缺少／版本或路徑衝突／無法檢查」其中一個結論，再決定後續階段。若所有項目都符合跳過標準，直接前往完成報告，不執行第二至第六階段的任何安裝或設定。

## 環境步驟二：決定 Node.js

`clasp` 由 Node.js 執行，npm／npx 通常會隨 Node.js 一起安裝。

若既有 Node.js 已符合跳過標準，保留原狀並跳過本階段。不要只為了改成教材偏好的版本而重裝。

每次實際安裝前，Agent 必須重新查驗：

```bash
# 查詢目前 clasp 版本及其 Node.js 引擎需求，不把舊教材版本當成永久事實。
npm view @google/clasp version engines --json
```

並從 [Node.js Releases](https://nodejs.org/en/about/previous-releases) 確認目前仍受支援的 LTS。以 2026 年 7 月的基線而言：

- Node.js 24 LTS：新環境預設。
- Node.js 22 LTS：已安裝時可繼續使用。
- Node.js 20 或更舊版本：不作為新環境，應升級。
- Current、奇數版或未在教材驗證過的未來版本：先核對 `clasp` 引擎需求；不要未經說明自動降級或改動既有工具鏈。

### 需要安裝或升級時

Agent 先向使用者顯示：

- 將安裝的 Node.js LTS 主版本。
- 下載來源。
- 是否需要管理員權限。
- 是否會影響電腦上既有 Node.js 專案。

取得必要確認後才進行系統層級安裝。

macOS 預設使用 Node.js 官方安裝程式，或沿用電腦上已存在且健康的版本管理器。不要為了本流程再疊加第二套 Node 管理器，也不要用 `sudo npm install -g` 解決 npm 權限問題。

Windows 預設使用符合 x64 或 ARM64 架構的 Node.js 官方 LTS 安裝程式。完成後重新開啟終端機並再次檢查版本與路徑。

## 環境步驟三：安裝 Git 並建立安全基線

Git 是 Agent 的版本保護工具，不是要求初學者另外學習的課程。除非使用者明確表示這個專案不用 Git，否則 Git 缺少時必須在第一次程式或專案設定修改前補齊。

### 1. 安裝或沿用 Git

若 `git --version` 與實際路徑已驗證成功，沿用現有 Git，不重裝也不任意升級。

macOS 缺少 Git 時：

- 優先使用 Apple Command Line Tools 提供的 Git，或沿用已存在且健康的 Homebrew。
- 不為了安裝 Git 額外安裝第二套套件管理器。
- `xcode-select --install` 會觸發系統安裝介面，Agent 先說明影響，再由使用者核准。

Windows 缺少 Git 時：

- 使用 Git for Windows 官方安裝程式；若系統已有 `winget`，Agent 可提出官方 `Git.Git` 套件作為安裝方式。
- 安裝前說明來源與系統影響，取得使用者核准後再執行。
- 安裝後重開終端機，重新驗證 `git --version` 與 `Get-Command git -All`。

若專案使用 WSL，就在同一個 WSL 發行版內安裝及執行 Git，不混用 Windows Git。

### 2. 先建立忽略規則

在 `git init`、安裝 `clasp` 或建立 Apps Script 專案前，確認專案的 `.gitignore` 至少排除：

```gitignore
# Node.js 相依套件與建置產物
node_modules/
dist/

# clasp 本機憑證與私人專案對應
.clasprc.json
**/.clasprc.json
.clasp.json
**/.clasp.json

# 本機秘密與環境設定
.env
.env.*
!.env.example
```

`.clasprc.json` 含有 OAuth 憑證；`.clasp.json` 含有遠端專案對應資訊。不得在畫面回覆、除錯紀錄或 Git 中輸出完整內容。

既有 `.gitignore` 只補缺少規則，不覆寫使用者內容。

### 3. 確認 repository

- 既有 Git 專案先檢查 repository 根目錄、分支、`git status`、staged 與 unstaged diff。
- 不得把既有使用者變更提交、還原或混入 Agent 的 commit。
- 全新空目錄可由 Agent 執行 `git init`，先提交安全忽略規則與最小專案說明作為基線。
- 既有但尚未使用 Git 的目錄，先掃描敏感資料並列出準備納入基線的檔案；取得使用者確認後才建立初始 commit。
- 如果 Agent 要修改的檔案已有未提交內容，停止並說明重疊範圍，不擅自覆蓋或提交。

### 4. 確認 Git identity

先讀取目前 repository 或既有全域 `user.name` 與 `user.email`。資訊不存在時不得捏造，請使用者提供後，預設只設定目前 repository；除非使用者明確要求，不修改全域 Git 設定。

### 5. 預設上版規則

「每次修改」指一個可獨立驗收的成果，不是每次存檔：

1. 完成修改。
2. 通過語法、型別、測試及專案驗證。
3. 搜尋秘密、私人 ID 與測試個資。
4. 只 stage 本次 Agent 修改的檔案。
5. 檢查 staged diff 與 `git diff --cached --check`。
6. 主動建立內容清楚的本機 commit。
7. 回報 commit 識別碼與包含的成果。

驗證失敗時不建立完成版 commit。使用者明確表示不用 Git 時，記錄停用範圍並在交付時說明沒有版本點。

本機 commit 是版本紀錄，不是異機備份；GitHub repository、remote 與 `git push` 都必須另外取得使用者確認。

## 環境步驟四：建立專案內 clasp

### 1. 確認目錄

- 解析並顯示完整目錄。
- 沒有自訂位置時，使用已解析的 `<文件資料夾>/GoogleAppsScript/<專案名稱>`。
- 檢查是否已有 `package.json`、`package-lock.json`、`.clasp.json` 或使用者檔案。
- 既有 `package.json` 必須先閱讀，不能直接覆寫。
- 如果目錄不正確或疑似屬於另一個專案，停止並請使用者確認。

### 2. 建立 npm 專案

只有在目標目錄沒有 `package.json` 時，才由 Agent 初始化 npm 專案。不要在家目錄、磁碟根目錄或含有不明使用者檔案的廣泛目錄執行。

### 3. 固定 clasp 版本

若專案已經有固定版本，而且實際驗證通過，沿用既有版本並跳過安裝。不要因 registry 出現新版就自動升級。

Agent 先取得 registry 回報的明確版本與 Node.js 引擎需求，再以該明確版本安裝：

```bash
# <已確認版本> 必須替換成 registry 實際回報的版本，不可保留占位字串執行。
npm install --save-dev --save-exact @google/clasp@<已確認版本>
```

預設不使用全域安裝，原因是：

- `package.json` 與 `package-lock.json` 可以記錄實際版本。
- 不依賴使用者電腦的全域 npm prefix。
- 避免 macOS 的全域寫入權限問題。
- Windows、macOS 與其他 Agent 都能在專案內取得相同版本。
- 未來 `clasp` 發生破壞性變更時，不會讓舊專案無預警改用新版命令。

若電腦已有全域 `clasp`，不要自行移除；專案操作仍優先使用本機版本。接管模式尚未選定遠端專案時，只有唯讀的帳號驗證與 `list-scripts` 可使用已驗證的既有 `clasp`；選定專案後立即改用該專案內固定版本。

### 4. 驗證真正被執行的版本

```bash
# 驗證相依套件與專案內 clasp，不以安裝命令成功作為完成證據。
npm ls @google/clasp --depth=0
npm exec -- clasp --version
npm exec -- clasp --help
```

Windows PowerShell 如果封鎖 `.ps1` shim，可改用：

```powershell
# 只改用 Windows 的 cmd shim，不放寬整台電腦的執行政策。
npm.cmd ls @google/clasp --depth=0
npm.cmd exec -- clasp --version
npm.cmd exec -- clasp --help
```

不要為了執行 npm 而把 PowerShell 設成 `Unrestricted` 或永久 `Bypass`。若組織原則封鎖命令，停止並交由使用者或管理員決定。

## 環境步驟五：驗證並提交開發工具設定

完成 Node.js、專案內 `clasp`、`.gitignore` 與基本專案結構後：

1. 驗證 Node.js、npm、專案內 `clasp` 與 Git。
2. 確認 `.gitignore` 確實排除憑證、`.clasp.json`、`node_modules` 與秘密檔案。
3. 檢查本次 staged diff 與敏感資料。
4. 建立「完成 Apps Script 開發環境」的本機 commit。

如果使用者明確停用 Git，跳過 commit，但完成報告必須標記「使用者已停用 Git，本次沒有版本復原點」。

## 環境步驟六：Apps Script API 與 Google 登入

### 1. 啟用 Apps Script API

先執行 `list-scripts` 等唯讀命令。若成功列出可存取專案，代表現有 OAuth 與 Apps Script API 足以使用，本步直接通過，不另外要求開啟設定頁或確認帳號。

只有唯讀驗證顯示 Apps Script API 未啟用時，才開啟 [Apps Script 使用者設定](https://script.google.com/home/usersettings)，由使用者確認目前瀏覽器登入帳號，再啟用 Apps Script API。

這是 Google 帳號設定變更。Agent 可以協助開啟正確頁面與辨識狀態，但不能只因設定頁已開啟就宣稱 API 已啟用；必須看見實際開啟狀態或取得使用者明確確認。

如果目前帳號的 API 狀態已實際確認開啟，不要再次切換設定。

### 2. clasp OAuth 登入

```bash
# 啟動 Google OAuth；帳號選擇、登入與授權由使用者親自完成。
npm exec -- clasp login
```

Agent 在執行前先提醒：

- 使用者要選擇剛才確認的 Google 帳號。
- 授權是讓 `clasp` 管理該帳號可存取的 Apps Script 專案。
- 不要把授權完成後產生的憑證檔貼給 Agent 或加入 Git。

Windows 若遇到 PowerShell shim 問題，使用 `npm.cmd exec -- clasp login`。

若既有授權已由唯讀命令證明仍有效，而且沒有帳號歧義，跳過 `clasp login` 並直接繼續，不要求使用者重複確認帳號或 OAuth。

### 3. 驗證登入

- 確認 OAuth 流程明確完成，不能只以瀏覽器已開啟判斷。
- 使用目前版本 `--help` 中支援的 `show-authorized-user` 與 `list-scripts` 等唯讀命令驗證授權。
- 唯讀驗證成功時直接記錄「沿用有效授權」，不要再把帳號確認變成教學模式的阻塞問題。
- 驗證輸出若含專案名稱、Script ID 或帳號資料，只在本機判斷，不在回覆中逐字轉貼。
- 組織帳號若封鎖第三方 OAuth，停止並說明需要管理員允許 `clasp`，不要改用私人 OAuth 憑證繞過政策。

## macOS 與 Windows 的差異摘要

| 項目 | macOS | Windows |
|---|---|---|
| 架構 | Apple Silicon `arm64` 或 Intel `x86_64` | 常見為 x64，也可能是 ARM64 |
| 預設 Shell | 通常是 zsh | 通常是 PowerShell |
| Node 安裝 | 官方安裝程式或沿用既有版本管理器 | 官方 x64／ARM64 LTS 安裝程式 |
| 常見問題 | npm prefix、`EACCES`、多套 Node、PATH 遮蔽 | PATH 尚未更新、`.ps1` shim、組織執行政策 |
| 不應採用 | `sudo npm install -g` 當通用解法 | 全域放寬 PowerShell execution policy |
| 特殊情境 | Homebrew 路徑依 CPU 架構不同 | WSL 與原生 Windows 必須擇一 |

## 錯誤分流

### 安裝完成但版本沒變

找出所有同名執行檔、npm prefix 與實際 Node 路徑。直接驗證專案內版本，不要重複盲目安裝。

### `node`、`npm` 或 `npx` 找不到

重新開啟終端機後再檢查。如果仍找不到，核對安裝架構與 PATH；不要直接修改整份使用者設定檔。

### macOS 出現 `EACCES`

確認目前是在專案目錄進行本機安裝。不要改用 `sudo`；先找出目錄擁有者、npm prefix 與使用中的 Node 安裝來源。

### Windows 顯示無法載入 `npm.ps1`

先改用 `npm.cmd`／`npx.cmd`。若 `.cmd` 可執行，就不需要改變全域 execution policy。

### Apps Script API 未啟用

回到使用者設定頁確認實際開關與帳號。不要用重複 `clasp login` 掩蓋 API 尚未啟用。

### OAuth 帳號錯誤或受組織阻擋

停止，不建立或同步專案。讓使用者登出錯誤帳號，或請組織管理員處理允許清單。

## 停止條件

出現以下任一情況，不進入下一課：

- Agent 沒有終端機或檔案系統能力。
- 專案目錄不明，或可能覆蓋既有使用者檔案。
- Git 缺少或無法建立安全基線，而且使用者沒有明確指示停用 Git。
- Git identity 缺少，且需要建立 commit 前仍未取得使用者提供的資料。
- 目標檔案已有來源不明或與本次重疊的未提交變更。
- Node.js 版本不受支援，且使用者尚未核准安裝或升級。
- 偵測到多套 Node／npm，但無法確認實際執行路徑。
- 套件來源不是官方 npm registry，或下載內容無法確認。
- Apps Script API 狀態未確認。
- OAuth 未完成、帳號不正確或被組織政策阻擋。
- 專案內疑似已有 `.clasp.json`，但遠端目標尚未確認。
- Git 忽略規則可能讓憑證或私人 ID 進入版本控制。

## 完成報告

Agent 必須用簡短表格回報：

| 檢查項目 | 必須回報 |
|---|---|
| 分流結果 | 環境完整、部分缺少、版本或路徑衝突，或無法檢查 |
| 本次處理 | 沿用既有環境、補齊哪些項目，或修復哪些衝突 |
| 系統 | 作業系統、架構、Shell／PowerShell；WSL 狀態 |
| 文件資料夾 | 作業系統解析出的實際路徑，以及是否由 iCloud、OneDrive 或組織重新導向 |
| 專案 | 已確認的絕對路徑；沒有自訂位置時應位於 `GoogleAppsScript/<專案名稱>` |
| Node.js | 版本、是否為受支援 LTS、實際執行路徑 |
| npm／npx | 版本與可用狀態 |
| clasp | 專案內固定版本與實際驗證結果 |
| Git | 版本、repository、分支、基線 commit；或使用者明確停用 Git |
| Apps Script API | 已實際確認開啟，或尚未完成 |
| Google OAuth | 唯讀驗證成功並沿用有效授權；帳號有歧義時才標記待使用者選擇 |
| 遠端操作 | 明確寫「未執行 pull、push 或部署」 |

只有電腦層必要項目符合成果，才能進入建立、接管、教學或除錯分流；目標確定後，還要完成該專案層的 Git、忽略規則與專案內 `clasp` 檢查，才可開始修改程式。若原有環境已全部通過，完成報告必須明確寫「沿用既有環境，未重新安裝」。

## 官方依據

- [Use the command-line interface with clasp](https://developers.google.com/apps-script/guides/clasp)
- [google/clasp](https://github.com/google/clasp)
- [Node.js Releases](https://nodejs.org/en/about/previous-releases)
- [npm：解決全域安裝 EACCES](https://docs.npmjs.com/resolving-eacces-permissions-errors-when-installing-packages-globally/)
- [Microsoft：PowerShell Execution Policies](https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_execution_policies)
