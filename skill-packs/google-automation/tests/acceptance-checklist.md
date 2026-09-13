# Google 工具自動化驗收清單

## A. 來源、授權與公開邊界

- [x] Toolbox 自有路由、安裝器與文件適用 Apache License 2.0。
- [x] 原 Learn-GAS 技能由 Toolbox 內建，保留歷史 commit、tree、MIT License 與 LICENSE SHA-256。
- [x] Toolbox Git tree 包含完整四個 Apps Script 技能、範例、測試與授權。
- [x] 公開內容沒有帳號、OAuth 憑證、Script ID、Cloud Project ID、真實 Google 資源網址、私人路徑或維護者工作習慣。
- [x] Markdown 相對連結與必要外部官方連結有效。

## B. MVP 能力與安裝生命週期

- [x] 路由技能能區分 Apps Script 學習／修改、既有專案接管、Workspace API／OAuth、Cloud Run service、Cloud Run job／Scheduler 及需專門審查的範圍。
- [x] 四個 Apps Script 技能與共用術語檔由本包鎖定來源安裝。
- [x] 正常安裝與相同版本重複安裝通過。
- [x] 未知檔案、目錄、symlink、來源不符與人工修改會停止且保留內容。
- [x] 更新先保留舊版，再替換受管理入口；回復可還原最近一版。
- [x] 移除只隔離六個已驗證入口，不刪除來源 repository、使用者專案或 Google 資源。

## C. 自動與本機驗證

- [x] Learn-GAS 上游驗證程式通過。
- [x] Learn-GAS 教學工具的全部單元測試通過。
- [x] Toolbox manifest、技能結構、OpenAI metadata、路由 fixture、隱私、授權與相對連結通過。
- [x] 安裝生命週期單元測試通過。
- [ ] Codex 依工作區 `.agents/skills` 發現技能，或明確留下本機無模型請求可做的最深驗證結果。 本次新版實際發現待驗。
- [ ] Claude Code 依工作區 `.claude/skills` 發現技能，或明確留下本機無模型請求可做的最深驗證結果。 本次新版實際發現待驗。
- [ ] Antigravity 依工作區 `.agents/skills` 發現技能；若需已登入環境，保留到 D 節且不得假裝通過。 本次新版實際發現待驗。
- [x] 本機程式、Google 登入、OAuth、遠端部署與人工驗收在文件及測試中維持不同狀態。

A～C 的本機程式與結構驗證通過，可提供可安裝候選；用戶端實際發現及 D 節仍須獨立驗收。

## D. 單一最終外部電腦／Google 驗收

以下由使用者在其他工作完成後一次執行：

- [ ] 從未使用維護者本機工作目錄的公開候選快照取得 Toolbox 整併發行版，單獨驗證內建 Google 技能包。
- [ ] 選擇一個全新測試工作區，讓 Agent 安裝 `agents_workspace` 與 `claude_workspace`；再重跑一次確認 `noop`。
- [ ] 重新開啟 Codex、Claude Code 與已登入的 Google Antigravity，確認 `google-workflow-router` 與四個 Learn-GAS 技能都能被發現。
- [ ] 用虛構資料提出四類需求：Apps Script 學習、既有 Apps Script 接管、Workspace API／OAuth、長時間排程或 Webhook；確認分流與停止點正確。
- [ ] 選其中一條低風險 Apps Script 測試，確認 Agent 先完成本機程式，再由使用者完成 Google 登入與 OAuth；另行同意後才推送，最後由使用者查看實際結果。
- [ ] 全程確認沒有把 Script ID、Cloud Project ID、OAuth secret、Token、帳號或真實資源網址寫入 Git、技能狀態或一般回覆。
- [ ] 在測試工作區執行更新模擬、回復與移除；確認人工修改會停止，而且移除後來源與 Google 資源仍保留。

D 節通過後，才能把實際作業系統、Agent 版本與 Google 測試條件加入 `officially_supported`。失敗時保留候選狀態與回復資料，不宣稱正式支援。
