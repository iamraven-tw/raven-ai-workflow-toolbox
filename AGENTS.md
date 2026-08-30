# AI Workflow Toolbox 協作規則

本專案提供一人公司創業者可安裝、可驗收的 AI 工作流技能包。通用核心、公開範本與私人實際案例必須分開。

## 工作原則

- 主要文件使用繁體中文；技術名詞保留必要英文。
- 修改技能前完整閱讀該技能的 `SKILL.md` 與直接連結的必要 reference。
- 公開技能只包含去識別化、參數化、可重複使用的規則與虛構範例。
- 不得提交私人筆記、品牌設定、真實帳號、Cookie、Token、私人資源 ID、絕對本機路徑或未公開內容。
- 發布、push、部署、刪除、付費操作與遠端帳號變更需要使用者明確授權。
- 本機驗證、人工驗收與遠端發布狀態分開回報。

## 共用套件

- 每個 `skill-packs/<name>/` 必須能由使用者單獨下載與安裝，不依賴維護者本機 symlink。
- 套件若有獨立來源 repository，保留原授權、必要聲明與完整可用檔案。
- 如果本機存在 `.local/sync-manifest.toml`，修改共用套件前必須先讀取，辨識 canonical、mirror 與 runtime consumer；完成前執行 manifest 指定的一致性檢查。
- `.local/` 只保存維護者本機路徑、同步狀態與驗證紀錄，永不提交。
- 兩個來源同時有未同步修改時停止，不自動選邊覆寫。

## AI 知識庫

- `skill-packs/ai-knowledge-base/` 是可獨立安裝的完整發行副本。
- 通用資料骨架位於該套件的 `template/sources/`；實際使用者資料不得放入本 repository。
- 一人公司設定是 AI 知識庫的一部分；公開版只提供 `not_configured` 空白範本。
- 修改套件後執行其 `tests/validate_repository.py`，並使用技能驗證器檢查所有 `skills/<name>/SKILL.md`。

## 程式與驗證

- 新增程式優先使用 Python 或 TypeScript，並加入繁體中文註解。
- 完成前檢查 frontmatter、Markdown fence、相對連結、授權、隱私資訊與公開套件是否含失效 symlink。
- 驗證失敗時停在目前工作項目修正，不宣稱後續階段完成。
