# 第三方聲明

目前候選版包含七個技能：`website-setup`、`website-content-writing`、`website-design-preview`、`website-build`、`website-deploy`、`website-service-integration` 與 `website-operations`。範本內建的六個主題與服務串接元件都是本專案自行實作的程式碼（Apache-2.0）。服務串接只產生標準 HTML form 與連結，不綑綁任何表單、電子報、預約或付款供應商的 SDK、嵌入碼或商標資產。維運工具以 Python 標準函式庫執行 HTTP/TLS 檢查、ZIP 備份、雜湊驗證與隔離復原，不綑綁監控、備份或更新供應商 SDK。每個主題各參考一個公開的商業主題示範頁（網址記在各主題 `theme.json` 的 `source_references`）的版面手法與動畫類型自行實作：只借鏡區塊順序、版面結構與動畫種類，未複製任何程式碼、樣式表、文案、圖片、影片或字型檔，也未使用其名稱。主題不含任何品牌 Logo、字型檔或商標，主題名稱為本專案自訂。早期版本曾參考 [nexu-io/open-design](https://github.com/nexu-io/open-design)（Apache-2.0）的設計指引，目前的六個主題已不再由其衍生；該專案只保留在 `references/extended-sources.md` 作為日後擴充的可選來源。各品牌或產品名稱僅用於標示來源，不代表相關公司背書。全站動畫使用 [Motion](https://motion.dev)（MIT），以 npm 固定版本由使用者的 `npm ci` 安裝。安裝管理器不下載或安裝第三方套件；離線畫廊則包含固定版本建置後的 Motion／Framer Motion JavaScript 與 Tailwind CSS／Typography 樣式，隨包保留 [第三方授權全文](skills/website-design-preview/assets/previews/THIRD_PARTY_LICENSES.txt)，也隨技能安裝。本機管理器、工作區設定程式、scaffold、整合與檢查程式只使用 Python 標準函式庫。

`template/` 是本專案自有的 Astro 起始範本（Apache-2.0）。它的 `package.json` 與 `package-lock.json` 宣告下列第三方 npm 套件，由使用者專案執行 `npm ci` 時從 npm registry 取得，不綑綁 node_modules；離線預覽內嵌的建置產物依上一段保留授權：

| 套件 | 版本 | 授權 |
|---|---|---|
| astro | 6.0.8 | MIT |
| tailwindcss | 4.2.2 | MIT |
| @tailwindcss/vite | 4.2.2 | MIT |
| @tailwindcss/typography | 0.5.19 | MIT |
| @astrojs/sitemap | 3.7.1 | MIT |
| @astrojs/rss | 4.0.17 | MIT |
| motion | 13.2.0 | MIT |
| wrangler | 4.129.0 | MIT OR Apache-2.0 |

lockfile 內的間接依賴各自適用其授權。

## 示範照片

`template/public/images/samples/` 內 14 張照片來自 [Unsplash](https://unsplash.com)，經 [Picsum](https://picsum.photos) 取得，適用 [Unsplash License](https://unsplash.com/license)：可免費商用、可修改、不需標示。`photos.json` 仍保留每張照片的作者與原網址。這些照片只作示範，使用者上線前應換成自己的照片；本技能包不提供任何以這些照片建立競爭服務的用途。`skills/website-design-preview/assets/previews/images/samples/` 是同一批照片的副本，供畫廊預覽使用。

## Google Fonts

`site.fonts` 為 `google` 時，各主題會從 fonts.googleapis.com 載入 Google Fonts（Noto Sans TC、Noto Serif TC、Huninn、Iansui、Chocolate Classical Sans、Archivo、Albert Sans、Inter Tight、Urbanist、Space Grotesk、Playfair Display 等，實際清單見各主題 `theme.json`）。字型檔不包含在本技能包內，各字型適用其在 Google Fonts 上的開放字型授權；載入時瀏覽器會向 Google 發出請求，隱私影響見 `docs/data-and-credential-boundaries.md`。改為 `system` 即不載入。

後續技能預計使用的第三方專案已列於 `install.manifest.toml` 的 `[[planned_dependencies]]`，包含 Google Labs 的 DESIGN.md 規格、daisyUI 與 Playwright。它們目前只是規劃記錄，尚未進入任何安裝路徑。進入安裝路徑前，必須依 Toolbox 的第三方依賴政策固定版本或 commit、記錄授權、完整性驗證、容量與可替換方案，並在本檔案補上對應聲明。

Cloudflare、Astro、Tailwind、Google 與其他名稱僅用於說明互通能力，並不表示這些公司背書本技能包。
