# AI Workflow Toolbox 安裝入口

本 repository 由多個可獨立演進的技能包組成。根目錄不提供會一次安裝全部內容的指令；先選擇需要的技能包，再由具備本機操作能力的 AI Agent 閱讀該套件的 `INSTALL.md` 與 `install.manifest.toml`。

## 目前狀態

| 技能包 | 狀態 | 安裝入口 |
|---|---|---|
| AI 知識庫 | Agent 端候選版可供外部驗收；尚未正式支援 | [`skill-packs/ai-knowledge-base/INSTALL.md`](skill-packs/ai-knowledge-base/INSTALL.md) |
| AI 剪片工作流 | Agent 端 MVP 已完成，可安裝為外部驗收候選版；尚未正式支援 | [`skill-packs/ai-video/INSTALL.md`](skill-packs/ai-video/INSTALL.md) |
| Google 工具自動化 | Agent 端 MVP 已完成，可安裝為外部驗收候選版；尚未正式支援 | [`skill-packs/google-automation/INSTALL.md`](skill-packs/google-automation/INSTALL.md) |
| 社群媒體管理工作流 | 尚未建立 | 無 |
| 官網打造工作流 | 前 3 個技能（設定、風格挑選、建置）與起始範本為可安裝的本機候選；其餘四個尚未建立，尚未正式支援 | [`skill-packs/website-building/INSTALL.md`](skill-packs/website-building/INSTALL.md) |

## 共通規則

1. 安裝前先唯讀檢查作業系統、硬體、既有工具、目標位置與衝突。
2. 列出即將下載的第三方套件、固定版本、來源、授權、容量、可能費用與登入需求。
3. 取得使用者確認後才能下載、安裝、覆寫、登入或變更權限。
4. 不安裝 manifest 標示為 `installable = false` 的套件。
5. 完成後依套件 manifest 驗證技能、依賴、工作區與可見結果；任何必要步驟未通過時不得宣稱安裝成功。
6. 安裝狀態只能保存不含 Token、Cookie、帳號內容與私人素材的必要資訊。

第三方來源與 fork 的選擇方式見 [`docs/dependency-policy.md`](docs/dependency-policy.md)。本 repository 尚未公開發布；自行撰寫的公開核心採 [Apache License 2.0](LICENSE)，第三方內容保留各自授權。
