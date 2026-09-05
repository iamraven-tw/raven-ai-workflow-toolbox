# 官網打造工作流

這是 AI Workflow Toolbox 的公開官網打造技能包。目標是讓一人公司創業者把「從零到官網上線」交給 AI Agent 全程執行；人類只提供事實、做取捨、完成外部帳號的登入與同意、授權付費或公開發布。目前是**第一版五個技能（設定、文案、風格挑選、建置、部署）與起始範本都已完成的本機候選版**，第二版的整合與維運技能尚未建立，也尚未正式支援。

設計決策見 [ADR 0003](../../docs/decisions/0003-website-building-workflow.md)。

## 核心承諾

第一版完成時，人類需要親自做的事只有下列項目，其餘由 Agent 完成。完整理由見 [`docs/human-touchpoints.md`](docs/human-touchpoints.md)。

1. 回答一次商業訪談。
2. 批次確認預設方案，或說「全部用預設」。
3. 建立 Cloudflare 帳號，並在瀏覽器點一次 `wrangler login` 的同意。
4. 授權首次部署到 `workers.dev`。
5. 要自訂網域時：購買網域，必要時在 Cloudflare 後台加入網域與在註冊商改 nameserver。
6. 授權綁定網域與正式公開。

## 目前可用

- `website-setup`：讀取工作區既有設定當預設值，一次完成商業訪談，產生頁面清單、風格推薦、託管方案與網域路線的預設方案，批次確認後寫入 `website/config.json` 與不含秘密的狀態檔。本技能不建立專案、不部署、不碰任何 Cloudflare 資源。
- `website-content-writing`：引導使用者填寫首頁、關於、服務、聯絡、文章列表與 404 的文案。Agent 依設定檔列出每欄的用途、字數與一個虛構範例，必填五欄請使用者自己寫；他沒空時 AI 先填起點並標記為建議、明講建議親自改過一遍。工具會擋下 AI 建議裡沒依據的數字、定稿仍含佔位或必填空白。建站階段不寫部落格文章，文章由使用者自己用 Markdown 寫，技能只檢查格式並帶進網站。確認後寫入 `website/copy.json`，`website-build` 建站時自動套用，已建好的站用 `sync` 同步。
- `website-design-preview`：範本內建六個主題，各參考一個公開商業示範頁的版面手法與動畫類型自行實作（程式碼與素材未複製；版面、字型、間距、元件、動畫都不同，不是換色）。走到選風格的步驟時 Agent 主動產生本機畫廊，用真正建置出來的首頁展示、替換成使用者的站名與文案、截圖並標示建議；使用者只回一個編號。選定後寫入 `website/design.json`，建站或重建時整站換主題。使用者端不需要 Node，不需要網路。
- `website-deploy`：Wrangler 登入檢查、部署預覽、`wrangler deploy` 到 `workers.dev`、HTTP 讀回、四條網域路線與 custom domain 綁定、移除 `noindex` 正式公開。每個外部動作都先預覽、取得授權、執行後讀回；套件不保存任何 Token。人類只做建立帳號、瀏覽器點一次同意、授權部署、買網域與必要的 Add a site／改 nameserver、授權公開。
- `website-build`：從 `template/` 的去識別化 Astro 起始範本建立專案，依設定檔寫入站點設定與 Worker 名稱、複製啟用的可選頁面、覆寫設計 token、產生佔位素材，然後 `npm ci`、`npm run build`、用 `check_site.py` 檢查靜態輸出，再用瀏覽器工具截圖。人類只在建立前確認一次計畫。本技能不登入 Cloudflare、不部署。

## 起始範本

`template/` 是自有的 Astro 6 起始範本 `solo-site-starter`，Apache-2.0，品牌、文案、聯絡方式與圖片全部虛構。依賴由 `package.json` 鎖定確切版本並附 `package-lock.json`，使用者專案一律 `npm ci`。

| 類型 | 內容 |
|---|---|
| 固定頁面 | 首頁、關於、服務、文章列表、單篇文章、聯絡、404，加 RSS 與 sitemap |
| 可選頁面 | 作品集、案例、價目、常見問題、電子報；只在設定啟用時複製進專案 |
| 文案層 | `site.copy.mjs` 各頁標題、導言、段落與按鈕文字，欄位為 null 時沿用主題自己的預設語氣 |
| 主題內容 | 每個主題各有 theme.css、BaseLayout、Header、Footer、Home、BlogIndex、BlogPost；首頁敘事結構各不相同（長文、產品頁、純文字留白、全幅照片章節、彩色便當格、報紙頭版） |
| 字型 | 各主題載入不同的 Google Fonts 中文字型（`site.fonts = 'google'`），可改 `system` 不發外部請求 |
| 示範照片 | 14 張 Unsplash 授權照片與 `photos.json` 來源清單，上線前請換成自己的照片 |
| 主題 | `src/themes/<id>/` 六套完整主題，由 `site.config.mjs` 的 `theme` 切換 |
| 佔位素材 | favicon、OG 圖、apple-touch-icon、Hero、頭像、三個服務圖示，由 `scaffold_site.py` 依站名與 token 產生 |

完整清單見 [`skills/website-build/references/template-structure.md`](skills/website-build/references/template-structure.md)。

## 已確認、尚未建立

| 順序 | 技能 | 第一版 |
|---|---|---|
| 6 | `website-service-integration` | 第二版 |
| 7 | `website-operations` | 第二版 |

這些名稱列在 manifest 的 `planned_skills`，目前沒有可被 Agent 發現的技能目錄。每個技能完成流程審查後才會加入安裝清單。

## 技術路線

- Astro 靜態輸出、Tailwind CSS、TypeScript；不使用 SSR、不綁定 KV／D1／R2。
- Cloudflare Workers 靜態資產，免費方案；預設先部署到 `workers.dev` 子網域，自訂網域是授權後的第二步。
- 部署預設由 Agent 在本機執行 `wrangler deploy`；Git 連動 Workers Builds 降為可選。
- 套件不保存任何 Cloudflare API Token，只用 Wrangler 自己的 OAuth 登入狀態。
- 內容以 repository 內的 Markdown 為唯一來源；外部 CMS 同步不進第一版。

## 風格來源

預設路徑是範本內建的六個主題，見 [`skills/website-design-preview/references/style-catalog.md`](skills/website-design-preview/references/style-catalog.md)：紙本書店、夜間工作室、留白畫廊、黑白展場、遊樂場、報刊編輯。每個主題依 open-design（Apache-2.0，固定 commit）的一份設計指引完整實作，來源記錄在各主題的 `theme.json` 與 `THIRD_PARTY_NOTICES.md`。新增主題屬於維護者工作，要照另一份可追溯的設計指引實作全部檔案並重新匯出預覽。納入門檻寫在 manifest 的 `[style_sources]`：OSI 授權、GitHub Stars 一萬以上或大廠出品、近 90 天有更新、能固定 commit 或版本、不含品牌圖片或字型檔。以真實品牌命名的風格只以六大視覺調性呈現，不把品牌名當預設值。

## 本機實作與集中實機驗收

目前先做本機程式與虛構測試；範本的 `npm ci` 與 `astro build` 以 `WEBSITE_NODE_ACCEPTANCE=1` 選擇性執行。所有工具包完成後才集中安排 Wrangler 登入、`workers.dev` 部署、自訂網域與另一臺電腦驗收。流程確認仍逐技能進行，不以實機驗收阻擋下一個技能。實作時必須確認的外部事實列在 manifest 的 `[[external_facts_to_confirm]]`。

## 公開邊界

本套件只包含一般化流程、中性 schema、官方能力摘要與虛構測試。任何實際網站專案只能作為設計證據；帳號、網域、Worker 名稱、品牌內容、價格、外部連結與部署設定都不得搬入本套件。套件內含 Apache-2.0 授權；套件本身不綑綁或安裝第三方套件，範本依賴由使用者專案的 `npm ci` 從 npm registry 取得，詳見 `THIRD_PARTY_NOTICES.md`。
