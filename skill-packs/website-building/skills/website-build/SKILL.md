---
name: website-build
description: "從去識別化的 Astro 起始範本建立一人公司官網專案。當使用者已完成官網設定（website/config.json），要 AI 建立網站專案、套用設計、填入文案、產生佔位圖片、在本機建置與預覽、自動檢查頁面時使用。人類只在建立前確認一次目標目錄與方案；本技能不登入 Cloudflare、不部署、不購買或綁定網域。"
---

# 官網建置

這是官網打造工作流的第四個技能。目標是讓 Agent 從設定檔一路做到「本機可預覽、自動檢查通過」的網站專案，人類不需要碰任何指令。

## 責任

- 讀取 `website/config.json`；商業資訊未設定時停止並交回 `website-setup`，不重問訪談。
- 檢查 Node.js 環境；缺少時說明版本需求與官方下載來源，不自行安裝系統軟體。
- 用 `scripts/scaffold_site.py plan` 列出目標目錄、Worker 名稱、主題、可選頁面與佔位素材，一次讓使用者確認。
- 確認後用 `scaffold` 建立專案：複製範本（含六個主題）、寫入 `site.config.mjs`（含選定主題）與 `wrangler.jsonc`、複製啟用的可選頁面、依主題顏色產生佔位素材。
- 執行 `npm ci`（依 lockfile 安裝固定版本）與 `npm run build`。
- 用 `scripts/check_site.py` 檢查 `dist/`：必要頁面、meta、robots、內部連結、圖片與 alt。
- 啟動 `npm run preview`，用用戶端內建的瀏覽器工具在三個斷點截圖；沒有瀏覽器工具時，依 `references/page-checks.md` 評估可選的 Playwright。
- 依 `website-setup` 的寫入流程，把 `verification.local_build` 與 `verification.automated_page_checks` 更新到設定檔。
- 分層回報，並交接給 `website-deploy`。

本技能不撰寫正式文案、不挑風格、不執行 `wrangler login`、不部署、不修改任何外部服務。文案與風格若尚未由對應技能完成，就用範本的中性預設與佔位文案先建起來，並在回報中明列哪些內容是佔位。

## 輸入

- `website/config.json`：商業資訊、頁面、設計、託管設定。`business.status` 必須不是 `not_configured`。
- 使用者指定的專案目標目錄。必須是空目錄或不存在，且不在技能包、範本或 Agent 技能掃描目錄內。
- 可選：`website-design-preview` 寫入的 `website/design.json`（選定主題）。`scaffold` 會自動讀取與 `config.json` 同目錄的這個檔案，也可用 `--theme` 指定；都沒有就用預設主題 `whitebox`，並在回報中提醒可以先用 `website-design-preview` 挑主題。
- 可選：`website-content-writing` 寫入的 `website/copy.json` 與 `website/posts/`。`scaffold` 會自動渲染成 `site.copy.mjs` 並複製文章；沒有就沿用範本的預設語氣與佔位句，並在回報中提醒可以先寫文案。
- 可選：使用者提供的 Logo 或照片。有的話在建置前放進 `public/images/`，並更新對應的 `src` 路徑；沒有就用佔位圖。

不得讀取瀏覽器 Cookie、環境變數中的 Token，或要求使用者貼上任何秘密。

## 啟動流程

這是多階段技能。開始執行前，用 Mermaid 向使用者呈現本次實際採用的分支、確認關卡與停止位置。

1. 讀設定，確認 `business.status`。`not_configured` 就停止並交回 `website-setup`。
2. 檢查環境：使用 Node 22.20.0 以上的受支援偶數版（24 分支使用 24.12.0 以上），npm 9.6.5 以上。依固定 lockfile 內 Astro 及平台依賴的 engines 核對；不足時停止並說明，不自行安裝。
3. `scaffold_site.py plan`：列出計畫。向使用者一次確認目標目錄與計畫內容；使用者說「全部用預設」視為確認。
4. `scaffold_site.py scaffold --confirm-write`：建立專案。命令旗標不是對話核准，必須先取得第 3 步的確認。
5. 有使用者素材時放入 `public/images/` 並更新引用。
6. `npm ci`。這一步會依 lockfile 從 npm registry 下載固定版本套件；第一次執行前說明容量與來源。失敗時讀錯誤訊息，常見原因見 `references/build-and-check.md`。
7. `npm run build`。失敗時停在這裡修正，不宣稱後面的步驟完成。
8. `check_site.py --dist <target>/dist --config <workspace>/website/config.json`。有 finding 就修正後重跑，直到 `passed`。
9. `npm run preview` 後，用瀏覽器工具在 375、768、1440 三個寬度截取首頁、服務、文章列表、單篇文章、聯絡與 404，檢查版面沒有溢出、導覽可用、手機選單可開合。截圖整理成一份給使用者看，不要求使用者自己打開瀏覽器。
10. 依 `website-setup` 的預覽與確認流程更新設定檔的 `verification.local_build` 與 `verification.automated_page_checks`。
11. 回報並交接。

## 範本

起始範本位於技能包的 `template/`，結構、頁面與元件清單見 `references/template-structure.md`。範本的品牌、文案、聯絡方式與圖片全部是虛構佔位；`scaffold` 會用設定檔的內容覆寫 `site.config.mjs`，其餘頁面從這個檔案讀取。

安裝版使用本技能內受雜湊管理的 `assets/template/`；來源版才使用技能包根層 template。缺少資產時停止並回報安裝不完整，不猜測維護者目錄或改用其他專案範本。不要直接修改安裝範本；使用者內容只寫到獨立網站專案。

- 固定頁面：首頁、關於、服務、文章列表、單篇文章、聯絡、404，加上 RSS 與 sitemap。
- 可選頁面：作品集、案例、價目、常見問題、電子報。只在 `pages.optional` 啟用時才複製進 `src/pages/`。
- 六個主題在 `src/themes/<id>/`，由 `site.config.mjs` 的 `theme` 決定；換主題只改這個欄位並重建。
- 收錄狀態固定 `noindex`，由 `website-deploy` 在使用者授權正式公開後改成 `index`。

## 佔位素材

`scaffold` 會依站名與主題顏色產生 favicon、OG 圖、apple-touch-icon、Hero 佔位圖、頭像佔位圖與三個服務圖示，規格見 `references/placeholder-assets.md`。網站不會因為缺素材而無法建置或上線。使用者提供素材時只替換對應檔案，不改變尺寸規格；不覆蓋或刪除使用者提供的檔案。

## 寫入範圍

- 使用者指定的專案目標目錄：全部由本技能建立與修改。
- `website/config.json` 與 `.local/website/setup-state.json`：只透過 `website-setup` 的 `manage_workspace.py` 預覽與確認流程更新 `verification` 欄位。

不得寫入技能目錄、公開 Toolbox、範本目錄或任何外部服務。`node_modules/`、`dist/`、`.astro/` 屬於建置產物，不得提交進 Toolbox。

## 執行錯誤最小回填

實際執行出錯，或可觀察行為與本技能規則衝突時，原任務優先：

1. 先保存目前進度；建置產物不需要保存。
2. 若 `references/troubleshooting.md` 已存在，只讀與目前症狀相關的段落；不存在時不要先建立空檔。
3. 只有能證明錯誤來自本技能或範本、修正限於同一個由使用者管理的技能來源、不新增依賴或外部授權，且重跑原失敗步驟通過時，才立即回填：主要流程更新本 `SKILL.md`，範本錯誤更新 `template/`，已驗證的特定環境或例外才建立或更新 `references/troubleshooting.md`。
4. 只做一次小修正、一次針對性重測，再執行本技能最快的既有格式／契約驗證，隨即回到原任務。
5. 一次修正仍失敗、需要升級 Astro 或 Tailwind 主版本、需要跨技能改造，或修正本身需要新的外部動作時，停止回填並簡短回報技能缺口。

不得修改已安裝快取、內建技能、外掛或第三方來源，也不得直接修改 `node_modules/` 內容。真實品牌內容、網域、Worker 名稱與一次性使用者選擇不得進入公開技能或範本。回填不授權 commit、push、發布或部署。

## 輸出與交接

每次輸出至少包含：

- 專案目錄、Worker 名稱、主題、啟用的可選頁面。
- 哪些內容是佔位（文案、圖片），以及對應技能。
- `npm ci`、`npm run build`、`check_site.py` 的結果與 finding。
- 截圖清單與觀察到的問題。
- 各層狀態：本機設定、本機建置、自動化頁面檢查已完成；Wrangler 登入、`workers.dev` 部署、自訂網域、公開收錄未開始。
- 交給 `website-deploy` 的下一步與剩下的人類接觸點：建立 Cloudflare 帳號、`wrangler login`、授權首次部署。

## 停止條件

- 商業資訊未設定，或設定檔含秘密欄位。
- 目標目錄不是空的、是 symlink，或位於技能包內。
- Node.js 版本不足或 npm 不可用。
- 使用者未確認計畫。
- `npm ci`、`npm run build` 或 `check_site.py` 失敗且一次修正後仍失敗。
- 使用者要求的動作屬於 `website-deploy`（登入、部署、網域）。

停止時保留已建立的專案目錄與錯誤訊息，不刪除使用者可能已修改的檔案。

## 驗證

公開候選版以虛構工作區驗證：未設定停止、目標目錄非空停止、計畫不寫檔、確認後建立專案、`site.config.mjs` 含設定內容且不含秘密、可選頁面依設定複製、佔位素材規格正確、`check_site.py` 對完整輸出通過並對缺頁與斷鏈失敗。範本的 `npm ci` 與 `astro build` 以 `WEBSITE_NODE_ACCEPTANCE=1` 選擇性執行；沒有執行時不宣稱範本可建置。
