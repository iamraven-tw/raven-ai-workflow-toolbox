# 起始範本結構

範本位於技能包的 `template/`，名稱 `solo-site-starter`，Apache-2.0。所有品牌、文案、聯絡方式與圖片都是虛構佔位。

發行來源只維護這一份；安裝管理器依 manifest 組合到 website-build/assets/template，納入完整安裝雜湊與生命週期。安裝後建置及同層風格畫廊都讀此副本，原下載目錄可移走。範本不含 node_modules／dist／.astro，npm ci 只在建立的網站專案內執行。

## 鎖定版本

| 套件 | 版本 | 授權 | 用途 |
|---|---|---|---|
| astro | 6.0.8 | MIT | 靜態站點框架 |
| tailwindcss | 4.2.2 | MIT | 樣式 |
| @tailwindcss/vite | 4.2.2 | MIT | Tailwind 4 的 Vite 外掛 |
| @tailwindcss/typography | 0.5.19 | MIT | 文章閱讀排版 |
| @astrojs/sitemap | 3.7.1 | MIT | sitemap |
| @astrojs/rss | 4.0.17 | MIT | RSS |

`package-lock.json` 鎖定完整依賴樹；使用者專案一律用 `npm ci`，不用 `npm install`。Wrangler 不在範本依賴內，由 `website-deploy` 以固定版本的 `npx wrangler@<版本>` 執行。

## 檔案

| 路徑 | 說明 |
|---|---|
| `site.config.mjs` | 站點設定，由 `scaffold` 依 `website/config.json` 產生；含 `theme` 欄位，頁面與主題只從這裡讀品牌資訊 |
| `src/site-config.d.ts` | 站點設定的型別 |
| `astro.config.mjs` | `site` 來自站點設定；`@theme` 別名依 `site.theme` 指到 `src/themes/<id>/`；sitemap 與 Tailwind |
| `wrangler.jsonc` | 只宣告 `assets.directory`，`name` 由 `scaffold` 填入 |
| `src/styles/global.css` | Tailwind 匯入與最小共用樣式，不含任何顏色與字型 |
| `src/lib/nav.ts`、`src/lib/menu.ts` | 導覽資料與手機選單行為，所有主題共用 |
| `src/content.config.ts` | 文章集合 schema：title、date、description、coverImage、tags |
| `src/content/posts/hello-world.md` | 虛構範例文章 |

## 六個主題

`src/themes/<id>/` 各自擁有 `theme.json`、`theme.css`、`BaseLayout.astro`、`Header.astro`、`Footer.astro`、`Home.astro`、`BlogIndex.astro`、`BlogPost.astro`。六個主題都參考公開示範頁的版面手法自行實作（程式碼與素材未複製）；版面、字型、間距、元件、動畫都不同，動畫共用 `src/lib/motion.ts`（Motion，MIT）。

| id | 名稱 | 調性 | 來源 |
|---|---|---|---|
| `nightlight` | 小夜燈 | 親切個人 | 版面參考（個人設計師作品集示範頁） |
| `darkroom` | 暗房 | 暗黑沉浸 | 版面參考（黑底品牌工作室示範頁） |
| `whitebox` | 白盒子 | 極簡純淨 | 版面參考（建築事務所示範頁） |
| `daylight` | 日光 | 攝影展廳 | 版面參考（照片主導的行銷代理商示範頁） |
| `sunrise` | 晨光 | 鮮豔活力 | 版面參考（漸層行銷代理商示範頁） |
| `weekly` | 週刊 | 雜誌印刷 | 版面參考（慢新聞雜誌示範頁） |

共用頁面（關於、服務、聯絡、404、可選頁面）只用各主題都必須定義的 `.t-*` 類別，契約見 `website-design-preview` 的 `references/token-contract.md`。

## 範例路由（建立專案時只保留已選頁面）

| 路由 | 檔案 | 內容 |
|---|---|---|
| `/` | `src/pages/index.astro` | Hero、Offerings、Trust、CallToAction |
| `/about` | `src/pages/about.astro` | 頭像佔位、定位、受眾、工作方式 |
| `/services` | `src/pages/services.astro` | Offerings、Trust、CallToAction |
| `/blog` | `src/pages/blog/index.astro` | 文章列表 |
| `/blog/[slug]` | `src/pages/blog/[slug].astro` | 單篇文章 |
| `/contact` | `src/pages/contact.astro` | 聯絡管道與行動呼籲 |
| `/404` | `src/pages/404.astro` | 找不到頁面 |
| `/rss.xml` | `src/pages/rss.xml.ts` | RSS |
| `/sitemap-index.xml` | 由 sitemap 整合產生 | sitemap |

## 可選頁面

位於 `template/optional-pages/`，只在 `pages.optional` 啟用時由 `scaffold` 複製進 `src/pages/`。

| 識別 | 路由 | 檔案 | 內容 |
|---|---|---|---|
| `portfolio` | `/portfolio` | `portfolio.astro` | 作品卡片網格 |
| `case_studies` | `/case-studies` | `case-studies.astro` | 問題、做法、成果三段式 |
| `pricing` | `/pricing` | `pricing.astro` | 依 offerings 列方案，價格為佔位 |
| `faq` | `/faq` | `faq.astro` | 原生 details 摺疊，不需 JavaScript |
| `newsletter` | `/newsletter` | `newsletter.astro` | 說明與訂閱入口；由 `website-service-integration` 接上 hosted link |

## 設計原則

- 只有 Header 的手機選單用了一小段 JavaScript，其餘頁面純靜態。
- 除使用者可關閉的 Google Fonts 外，沒有分析程式或第三方腳本；服務串接預設只用原生 HTTPS POST 與 hosted links。
- 換主題只改 `site.config.mjs` 的 `theme` 欄位並重建；不要在 `tsconfig.json` 加 `paths`，Astro 會用它蓋掉別名。
- 每個主題的信任區塊沒有資料就不顯示，避免 AI 編造數字。
