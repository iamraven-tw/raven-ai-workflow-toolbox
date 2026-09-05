# 建置與檢查

## 環境需求

- Node.js 20 以上（範本 `engines` 宣告）。檢查：`node --version`。
- npm 可用。檢查：`npm --version`。
- 缺少時停止並提供官方下載來源，不自行安裝系統軟體，也不改用其他套件管理器。

## 指令順序

```bash
npm ci            # 依 package-lock.json 安裝固定版本；第一次會從 npm registry 下載
npm run build     # 產出 dist/
npm run preview   # 本機預覽 dist/，預設 http://localhost:4321
```

第一次 `npm ci` 前向使用者說明：來源是 npm registry、版本由 lockfile 鎖定、大約需要的磁碟空間，以及不會執行任何登入。

## check_site.py 檢查項目

| 檢查 | 說明 |
|---|---|
| 必要頁面 | 六個固定頁面與啟用的可選頁面都有對應 HTML |
| 必要檔案 | `rss.xml`、`sitemap-index.xml`、`favicon.svg`、`og-image.png`、`apple-touch-icon.png` |
| 每頁 | `<title>`、`lang`、description、robots、og:title、og:description、og:image、恰好一個 `h1` |
| robots | 與 `--expected-indexing` 一致；建置階段一律 `noindex` |
| 內部連結 | `href` 以 `/` 開頭的連結都能對應到 dist 中的檔案 |
| 圖片 | `src` 對應的檔案存在，且每張圖都有 `alt` 屬性 |

未涵蓋：截圖、響應式版面、JavaScript 執行、遠端部署。這些由瀏覽器工具或 Playwright 補上。

## 常見失敗

| 症狀 | 原因 | 處理 |
|---|---|---|
| `npm ci` 說 lockfile 與 package.json 不一致 | 有人改了 package.json 沒更新 lockfile | 不要改用 `npm install`；回報並停止 |
| `astro build` 找不到 `site.config.mjs` | scaffold 未完成或目錄被搬動 | 重新執行 `plan` 比對目錄 |
| `astro build` 抱怨 content collection schema | 文章 frontmatter 缺欄位 | 修正該篇文章的 frontmatter |
| `check_site.py` 回報 `broken_link` | 頁面連到未啟用的可選頁面 | 啟用該頁或移除連結 |
| `check_site.py` 回報 `robots_mismatch` | `site.indexing` 被改成 `index` | 建置階段改回 `noindex`，公開由 `website-deploy` 處理 |
