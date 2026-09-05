# AI Workflow Toolbox 協作規則

本專案提供一人公司創業者可安裝、可驗收的 AI 工作流技能包。通用核心、公開範本與私人實際案例必須分開。

## 工作原則

- 主要文件使用繁體中文；技術名詞保留必要英文。
- 修改技能前完整閱讀該技能的 `SKILL.md` 與直接連結的必要 reference。
- 公開技能只包含去識別化、參數化、可重複使用的規則與虛構範例。
- 「沒有資安風險」不等於「適合公開」：維護者的品牌案例、集數、驗收回覆、工作路徑、測試雜湊、慣用詞庫、視覺偏好與其他私人脈絡，只要會讓使用者的 AI Agent 誤判任務、預設值或內容目標，就必須排除、參數化或改成明確的虛構範例。
- Raven 名稱只可用於必要的作者、維護者、產品與 fork 關係說明，不得成為使用者內容、預設詞庫、測試人格或工作流目標。
- 不得提交私人筆記、品牌設定、真實帳號、Cookie、Token、私人資源 ID、絕對本機路徑或未公開內容。
- 發布、push、部署、刪除、付費操作與遠端帳號變更需要使用者明確授權。
- 本機驗證、人工驗收與遠端發布狀態分開回報。

## 共用套件

- 每個 `skill-packs/<name>/` 必須能由使用者單獨下載與安裝，不依賴維護者本機 symlink。
- 套件若有獨立來源 repository，保留原授權、必要聲明與完整可用檔案。
- 維護者的私人工作流程與本公開 repository 各自獨立演進，不建立 hook、檔案監看、雙向同步或自動一般化流程。
- 公開發行採版本快照：只有使用者明確要求納入的改進，才經過人工挑選、去識別化、參數化與公開驗證後，放進下一個版本。
- `.local/` 只保存不提交的本機候選版、歷史草稿與驗證紀錄。即使其中存在舊的 `sync-manifest.toml`，AI Agent 也不得讀取或執行；除非使用者日後明確重新啟用同步設計。

## 第三方依賴與 fork

- 第三方專案預設由安裝 manifest 從正式來源取得固定版本，不直接複製進本 repository，也不追蹤 `latest` 或未鎖定的 `main`。
- 官方版本符合需求時使用官方來源；能以獨立擴充完成時保留官方核心；只有必要功能必須修改核心時才使用公開、可追溯的 fork。
- fork 必須記錄上游網址、基準版本、實際下載來源、固定 ref、授權、修改理由、更新與回復方式；不得把 fork 描述為官方版本。
- 模型權重、快取、虛擬環境與使用者素材不屬於技能包原始碼，不得提交；下載前必須說明來源、容量、授權、硬體需求與可能費用。
- `Video-Use` 現階段使用 Raven 維護的非官方公開 fork；`v0.1.0` 已鎖定 Release commit 與下載資產 SHA-256。未來目標是官方 `Video-Use` 加上獨立的臺灣中文擴充套件，不規劃向上游提交 Pull Request。系統依賴與 Toolbox 安裝驗證完成前，AI 剪片套件仍不得標示為可安裝。
- 完整政策見 `docs/dependency-policy.md`；特定整合決策見 `docs/decisions/`。

## AI 知識庫

- `skill-packs/ai-knowledge-base/` 是可獨立安裝的完整發行副本。
- 通用資料骨架位於該套件的 `template/sources/`；實際使用者資料不得放入本 repository。
- 一人公司設定是 AI 知識庫的一部分；公開版只提供 `not_configured` 空白範本。
- 修改套件後執行其 `tests/validate_repository.py`，並使用技能驗證器檢查所有 `skills/<name>/SKILL.md`。

## 官網打造

- `skill-packs/website-building/` 交給 AI Agent 全程執行；人類只做 `docs/human-touchpoints.md` 列出的接觸點。技能不得新增清單以外的人類步驟，需要時先更新該清單與 ADR 0003。
- 商業資訊只在 `website-setup` 問一次，之後的技能從 `website/config.json` 讀取；每個技能先給完整預設方案再批次確認。
- 託管固定 Cloudflare Workers 靜態資產免費方案；套件不保存任何 Cloudflare API Token，只用 Wrangler 自己的 OAuth 登入狀態。
- 範本內建六個主題，每個都參考一個可追溯的公開示範頁的版面手法與動畫類型自行實作（版面、字型、間距、元件、動畫都不同），不得複製其程式碼、文案、圖片或字型檔，也不得只做同一版面換顏色；主題用意象命名，來源網址與「未複製」聲明記錄在 `theme.json` 與第三方聲明。所有主題共用 `src/lib/motion.ts` 的動畫層，必須尊重 `prefers-reduced-motion`。走到選風格的步驟時 Agent 必須主動用畫廊展示真正建置出來的頁面，不用文字描述取代。修改任一主題後必須重新執行 `export_previews.py`。
- `template/` 是自有的 Astro 起始範本，只能含虛構品牌與佔位素材；依賴鎖定確切版本並附 lockfile，不得提交 `node_modules/`、`dist/` 或 `.astro/`。
- 修改套件後執行其 `tests/validate_package.py` 與 `python3 -m unittest skill-packs.website-building.tests.test_install_lifecycle skill-packs.website-building.tests.test_workspace_config skill-packs.website-building.tests.test_scaffold_site skill-packs.website-building.tests.test_check_site skill-packs.website-building.tests.test_style_gallery skill-packs.website-building.tests.test_deploy_site skill-packs.website-building.tests.test_content_writer`；改動範本後另以 `WEBSITE_NODE_ACCEPTANCE=1` 跑真實建置。

## 程式與驗證

- 新增程式優先使用 Python 或 TypeScript，並加入繁體中文註解。
- 完成前檢查 frontmatter、Markdown fence、相對連結、授權、隱私資訊與公開套件是否含失效 symlink。
- 驗證失敗時停在目前工作項目修正，不宣稱後續階段完成。
