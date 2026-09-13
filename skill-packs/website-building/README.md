# 官網打造工作流

這是 Raven AI 一人公司工具包 的公開官網打造技能包。目標是讓一人公司創業者把「從零到官網上線、服務串接與日常維運」交給 AI Agent 全程執行；人類只提供事實、做取捨、完成外部帳號的登入與同意，並授權付費、公開發布或其他高影響操作。目前是**七個技能（設定、文案、風格挑選、建置、部署、服務串接、維運）與起始範本都已完成的本機候選版**，尚未正式支援。

目前可獨立散布的決策摘要見 [套件決策](docs/package-decisions.md)，發布待辦見 [Preview 清單](docs/release-checklist.md)。

## 核心承諾

第一版完成時，人類需要親自做的事只有下列項目，其餘由 Agent 完成。完整理由見 [`docs/human-touchpoints.md`](docs/human-touchpoints.md)。

1. 回答一次商業訪談。
2. 批次確認預設方案，或說「全部用預設」。
3. 建立 Cloudflare 帳號，並在瀏覽器點一次 `wrangler login` 的同意。
4. 授權首次部署到 `workers.dev`。
5. 要自訂網域時：購買網域，必要時在 Cloudflare 後台加入網域與在註冊商改 nameserver。
6. 授權綁定網域與正式公開。
7. 需要表單、電子報、預約或付款時，建立／登入選定服務，完成條款、身分或收款資料，並分別授權服務資源建立、網站寫入、重新部署與選擇性的端到端測試。

## 目前可用

- `website-setup`：讀取工作區既有設定當預設值，一次完成商業訪談，產生頁面清單、風格推薦、託管方案與網域路線的預設方案，批次確認後寫入 `website/config.json` 與不含秘密的狀態檔。本技能不建立專案、不部署、不碰任何 Cloudflare 資源。
- `website-content-writing`：Agent 依事實完成已選頁面文案，與設計推薦一起批次確認；不要求人類先寫。部落格與文章依需求選用。確認後寫入 `website/copy.json`，`website-build` 建站時自動套用，已建好的站用 `sync` 同步。
- `website-design-preview`：範本內建六個主題，各參考一個公開商業示範頁的版面手法與動畫類型自行實作（程式碼與素材未複製；版面、字型、間距、元件、動畫都不同，不是換色）。走到選風格的步驟時 Agent 主動產生本機畫廊，用真正建置出來的首頁展示、替換成使用者的站名與文案、截圖並標示建議；使用者只回一個編號。選定後寫入 `website/design.json`，建站或重建時整站換主題。使用者端不需要 Node，不需要網路。
- `website-deploy`：Wrangler 登入檢查、部署預覽、`wrangler deploy` 到 `workers.dev`、HTTP 讀回、四條網域路線與 custom domain 綁定、移除 `noindex` 正式公開。每個外部動作都先預覽、取得授權、執行後讀回；套件不保存任何 Token。人類只做建立帳號、瀏覽器點一次同意、授權部署、買網域與必要的 Add a site／改 nameserver、授權公開。
- `website-service-integration`：把已建好的靜態網站接上聯絡表單、電子報、預約與付款服務。預設使用原生 HTTPS POST 與 hosted links，不加入第三方 SDK、iframe 或網站端 secret；每項整合都帶服務商與隱私政策揭露。Agent 先規劃、寫入、建置與讀回；人類只處理服務帳號登入／同意、付款身分與收款資料，以及分階段授權。付款只驗證結帳入口，不自動扣款。
- `website-operations`：對公開網址做狀態碼、必要內容、延遲與 TLS 健康檢查；建立含逐檔 SHA-256 manifest 的本機 ZIP 備份並驗證；只復原到新的隔離目錄；依賴更新先查官方資料、驗證備份並在隔離複本建置。監控排程、更新寫入、部署、線上 rollback、外部備份與刪除都各自需要明確授權。
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

七個技能均已加入 manifest 的安裝清單；真實公開監控、異地備份、依賴更新與線上回復仍屬後續實機驗收，不能由本機虛構測試推定為已通過。

## 技術路線

- Astro 靜態輸出、Tailwind CSS、TypeScript；不使用 SSR、不綁定 KV／D1／R2。
- Cloudflare Workers 靜態資產，免費方案；預設先部署到 `workers.dev` 子網域，自訂網域是授權後的第二步。
- 部署預設由 Agent 在本機執行 `wrangler deploy`；Git 連動 Workers Builds 降為可選。
- 套件不保存任何 Cloudflare API Token，只用 Wrangler 自己的 OAuth 登入狀態。
- 內容以 repository 內的 Markdown 為唯一來源；外部 CMS 同步不進第一版。
- 表單採公開 HTTPS POST；電子報、預約與付款採 hosted links。服務串接不保存憑證、不植入第三方 script／iframe；需要 API secret、webhook、會員、購物車或資料庫時另行設計。

## 風格來源

預設六個主題為小夜燈、暗房、白盒子、日光、晨光、週刊，見 [`style-catalog.md`](skills/website-design-preview/references/style-catalog.md)。它們參考公開示範頁的版面手法自行實作，未複製來源的程式碼或素材；來源記錄在各 theme.json 與 THIRD_PARTY_NOTICES.md。open-design 只保留為可選擴充來源，不是現行六主題的實作來源。新增主題必須記錄可追溯依據、遵守 manifest 的來源政策並重新匯出預覽，不把來源品牌當預設值。

## 本機實作與集中實機驗收

目前先做本機程式與虛構測試；範本的 `npm ci` 與 `astro build` 以 `WEBSITE_NODE_ACCEPTANCE=1` 選擇性執行。所有工具包完成後才集中安排 Wrangler 登入、`workers.dev` 部署、自訂網域、真實服務帳號與另一臺電腦驗收。流程確認仍逐技能進行，不以實機驗收阻擋下一個技能。實作時必須確認的外部事實列在 manifest 的 `[[external_facts_to_confirm]]`。

## 公開邊界

本套件只包含一般化流程、中性 schema、官方能力摘要與虛構測試。任何實際網站專案只能作為設計證據；帳號、網域、Worker 名稱、品牌內容、價格、外部連結與部署設定都不得搬入本套件。套件內含 Apache-2.0 授權；套件本身不綑綁或安裝第三方套件，範本依賴由使用者專案的 `npm ci` 從 npm registry 取得，詳見 `THIRD_PARTY_NOTICES.md`。
