# AI 剪片工作流協作規則

本目錄正在建立可公開安裝的 AI 剪片工作流。MVP 優先整理既有能力、依賴契約與驗收門檻，不重新實作已有功能。

## 開始前

- 先讀 `README.md`、`INSTALL.md`、`install.manifest.toml`、`docs/architecture.md` 與根專案的 `docs/dependency-policy.md`。
- manifest 標示 `status = "ready_for_external_acceptance"` 與 `installable = true` 時，代表可依 `INSTALL.md` 建立外部驗收候選版，不代表正式支援。下載、安裝共用套件、建立技能入口及模型下載仍要各自先顯示影響並取得使用者同意。
- Video-Use 整合方式以根專案的 `docs/decisions/0001-video-use-integration.md` 為準。

## MVP 邊界

- 優先從現有 Video-Use fork 的已驗證能力抽出通用契約，不為了填滿目錄新增程式碼、空殼技能或示範功能。
- `SKILL.md` 只有在能執行真實流程、依賴來源已鎖定且驗證入口存在時才建立。
- 維護者品牌、內容路由、私人文章、帳號、絕對路徑、素材、模型快取與成品不得進入本套件。
- 即使不構成資安問題，真實集數、人工驗收原話、測試素材雜湊、內容型預設詞彙、維護者慣用安裝路徑與品牌案例也不得進入公開 runtime 或 Agent 指令；它們會干擾使用者的 AI Agent 判斷。必要測試改用虛構或有明確公開授權的案例。
- Raven 名稱只可出現在 fork 來源、維護責任及產品歸屬，不得作為字幕詞庫、測試人物、影片主題或預設美術方向。
- 維護者的私人剪片流程與公開候選版各自修改，不建立 hook 或同步機制；只有使用者明確指定的改進才重新做公開化與版本驗證。
- 第三方程式預設由 manifest 安裝，不複製進本目錄；所有來源、版本、授權與修改關係寫入 `THIRD_PARTY_NOTICES.md`。
- 發布、push、建立遠端 fork、下載模型、付費操作與外部帳號變更仍需要使用者明確授權。
- Toolbox 的用戶端註冊路徑優先於 Video-Use v0.1.1 `install.md` 內的舊範例；不得把 Codex 技能安裝到已淘汰的 `$HOME/.codex/skills` 路徑。

## 驗證

- 在所有工作流與自動檢查完成前，不要求使用者進行零碎人工測試。
- 最終人工驗收由使用者在另一臺電腦下載並安裝完整 Toolbox 後執行。
- 在此之前使用本機的結構、manifest、連結、隱私、依賴與行為驗證；未驗證部分明確標示，不用推測補齊。
