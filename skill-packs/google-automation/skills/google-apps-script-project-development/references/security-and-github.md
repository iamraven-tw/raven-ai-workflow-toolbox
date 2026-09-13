# 安全與 GitHub

## 不得提交的內容

- `~/.clasprc.json` 或任何副本
- OAuth client secret、refresh token、access token
- 服務帳戶金鑰
- API 金鑰、Webhook secret、密碼
- 含私人資料的測試輸入與執行記錄
- 未確認可公開的 Script ID、Deployment ID、試算表 ID 或資料庫 ID

官方 `clasp` 指引目前建議將 `.clasprc.json` 與 `.clasp.json` 排除於 Git。即使某個識別碼不是完整憑證，公開前仍應採最小揭露原則。

## 本機 Git 預設規則

- 每份新建、接管或教學專案都先確認 Git 狀態。
- 除非使用者明確說不用 Git，否則 Git 必須在第一次程式修改前可用。
- 每個可獨立驗收的修改通過測試後，由 Agent 主動建立本機 commit。
- 一次 commit 只包含本次 Agent 修改的檔案，不得混入使用者原有的 staged、unstaged 或 untracked 變更。
- 修改前已有重疊變更時先停止並說明，不得覆蓋、還原或假裝全部是本次變更。
- 提交前必須檢查 staged diff、執行 `git diff --cached --check` 並搜尋敏感資料。
- Git identity 缺少時不得捏造；請使用者提供，預設只設定目前 repository。
- 使用者若明確停用 Git，Agent 記錄適用範圍，並在交付時說明本次沒有可回復的 Git 版本點。

「主動上版」指建立通過驗證的本機 Git commit，不代表自動同步到 GitHub。只有本機 commit 的資料仍可能隨磁碟損壞而遺失。

## GitHub 發布前檢查

1. 檢查 `git status` 與所有待提交差異。
2. 搜尋常見敏感欄位：`token`、`secret`、`password`、`scriptId`、`private_key`。
3. 確認 `.gitignore` 在第一次提交前已生效。
4. 確認範例只使用明確的 placeholder。
5. 補上授權條款、使用方式、需求版本與已知限制。
6. 在建立 GitHub 遠端與首次 push 前取得使用者確認。

## OAuth scopes

- 優先依 Apps Script 自動推導 scopes。
- 需要明確設定時，只加入功能所需的最小 scopes。
- 新增 Gmail、Drive、Calendar 或觸發器管理權限時，說明每個 scope 的用途。
- 不得為了省事使用過度寬廣的 scopes。

## Script Properties 與紀錄檔(Log)

- 所有建立、接管與後續修改都必須遵守 [專案品質標準](project-quality-standard.md)；以下是不可放寬的安全底線。
- Spreadsheet ID、Form ID、文件範本 ID、Folder ID、API Key 與第三方 Token 不得硬寫進原始碼。
- Agent 建立 Script Properties 的讀取、必要欄位檢查與中文錯誤訊息；實際敏感值由使用者直接在 Apps Script 專案設定輸入。
- Agent 不得要求使用者把 API Key、Token、密碼或 OAuth 憑證貼進對話。唯一教學例外是第二階段第 8 課：Agent 可依教學技能規則顯示一次只供當課使用的 `WEBHOOK_TOKEN` 臨時教學密語，明確說明它不適合正式使用且不得要求學生回傳；臨時值與學生自行更換的正式值都不得進入程式、測試、紀錄檔(Log)、Git 或課程進度。
- Google 帳號密碼、OAuth access token 與 refresh token 永遠不得存入 Script Properties。
- 紀錄檔(Log)只能記錄屬性「已設定／未設定」，不得輸出實際敏感值。
- 執行記錄不得包含完整郵件、Webhook 原始敏感內容或不必要的個資。
- Script Properties 不是專業秘密管理系統；不得用來保存不應與專案編輯者共享的機密。

## 遠端操作確認點

下列動作必須先向使用者展示目標與影響：

- `clasp push` 或 `clasp pull`
- 建立、更新或刪除 deployment
- 建立或刪除 Apps Script trigger
- 建立 GitHub repository
- 設定 Git remote
- `git push`

若由 Agent 撰寫設定函式讓使用者建立觸發條件，仍須先顯示處理函式、事件來源、事件類型、執行帳號及頻率。設定函式必須先檢查既有觸發條件，重複執行不得建立副本；實際執行與 UI 驗證由使用者完成。
