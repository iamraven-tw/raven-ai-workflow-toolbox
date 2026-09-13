# solo-site-starter

這是 Raven AI 一人公司工具包 官網打造技能包的去識別化 Astro 起始範本。品牌名稱、文案、聯絡方式與圖片全部是虛構佔位，由 `website-build` 依使用者的 `website/config.json` 重新產生。

## 六個主題

`src/themes/<主題>/` 各自擁有完整的版面、導覽、頁尾、首頁、文章列表與文章頁，以及自己的 `theme.css`。六個主題都參考公開示範頁的版面手法與動畫類型自行實作，程式碼、文案、圖片與字型檔皆未複製，來源記在各自的 `theme.json`。不是同一版面換顏色。所有主題共用 `src/lib/motion.ts`（Motion，MIT）的進場、跑馬燈、視差、游標與懸停動畫，並尊重 `prefers-reduced-motion`。

| id | 名稱 | 調性 | 來源 |
|---|---|---|---|
| `nightlight` | 小夜燈 | 親切個人 | 版面參考（個人設計師作品集示範頁） |
| `darkroom` | 暗房 | 暗黑沉浸 | 版面參考（黑底品牌工作室示範頁） |
| `whitebox` | 白盒子 | 極簡純淨 | 版面參考（建築事務所示範頁） |
| `daylight` | 日光 | 攝影展廳 | 版面參考（照片主導的行銷代理商示範頁） |
| `sunrise` | 晨光 | 鮮豔活力 | 版面參考（漸層行銷代理商示範頁） |
| `weekly` | 週刊 | 雜誌印刷 | 版面參考（慢新聞雜誌示範頁） |

切換主題：改 `site.config.mjs` 的 `theme` 欄位再重建。`astro.config.mjs` 會把 `@theme` 別名指到對應目錄。不要在 `tsconfig.json` 加 `paths`，Astro 會用它蓋掉別名。

## 結構

```text
site.config.mjs          站點設定（主題、品牌、文案、聯絡、頁面、收錄狀態）
astro.config.mjs         Astro 設定，site 與 @theme 別名來自 site.config.mjs
wrangler.jsonc           Cloudflare Workers 靜態資產部署設定
src/themes/<id>/         theme.json、theme.css、BaseLayout、Header、Footer、Home、BlogIndex、BlogPost
src/pages/               首頁、關於、服務、文章列表、單篇文章、聯絡、404、RSS；只取資料並掛主題
src/components/          共用服務串接元件；預設不啟用任何外部服務
src/data/integrations.json 表單、電子報、預約與付款的公開串接設定；不得放秘密
src/lib/                 導覽資料、手機選單行為與共用動畫層 motion.ts（所有主題共用）
src/styles/global.css    Tailwind 匯入與最小共用樣式，不含任何顏色與字型
optional-pages/          作品集、案例、價目、常見問題、電子報；只在設定啟用時複製進 src/pages/
src/content/posts/       Markdown 文章
public/                  favicon、OG 圖、佔位圖片（顏色依主題產生）
public/images/samples/   14 張 Unsplash 授權示範照片與 photos.json 來源清單；上線前請換成自己的照片
```

共用頁面與可選頁面只使用各主題都必須定義的 `.t-*` 類別（`t-container`、`t-section`、`t-h1`、`t-card`、`t-btn` 等），所以同一份頁面在不同主題下外觀完全不同。

## 指令

```bash
npm ci          # 依 lockfile 安裝固定版本
npm run build   # 產出 dist/
npm run preview # 本機預覽 dist/
```

## 字型與照片

- `site.fonts` 為 `google` 時，各主題會載入 `theme.json` 指定的 Google Fonts（含不同的中文字型），網站會向 fonts.googleapis.com 發請求；改成 `system` 就完全不發外部請求，只用系統字型。
- `public/images/samples/` 的照片來自 Unsplash（經 Picsum 取得），授權允許商用且不需標示；`photos.json` 保留每張的作者與原網址。它們只是示範，請在上線前換成自己的照片。

## 不要做的事

- 不要把 API Token、帳號識別碼或任何秘密寫進 `site.config.mjs`、`wrangler.jsonc` 或環境檔。
- 不要加入 SSR adapter、KV、D1、R2 等會離開免費方案的資源。
- 上線前 `site.indexing` 維持 `noindex`；由 `website-deploy` 在使用者授權後改成 `index`。
- 外部服務由 `website-service-integration` 寫入公開 HTTPS endpoint／hosted link；不要加入 API secret、未審查的 script 或 iframe。
- 新增主題時要照一份可追溯的設計指引，或明確記錄的公開版面參考，實作全部檔案，並在 `theme.json` 記錄來源、授權與「未複製程式碼與素材」的聲明。
