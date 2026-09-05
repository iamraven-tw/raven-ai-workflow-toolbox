# 主題契約

## 主題必須提供的檔案

| 檔案 | 用途 |
|---|---|
| `theme.json` | id、name、tonality、order、description、fits、source_guide、source_repository、source_license、placeholder_colors |
| `theme.css` | 主題全部樣式；必須定義下方的 `.t-*` 共用類別 |
| `BaseLayout.astro` | 匯入 `global.css` 與 `theme.css`，含 SEO meta、robots、Header、Footer |
| `Header.astro`、`Footer.astro` | 從 `src/lib/nav.ts` 取連結，版面自行決定；手機選單用 `mobile-menu-button` 與 `mobile-menu` 兩個 id |
| `Home.astro` | 首頁全部區塊 |
| `BlogIndex.astro` | 接 `posts` 屬性 |
| `BlogPost.astro` | 接 title、date、description、slug、coverImage、tags、toc 與 slot |

## 共用頁面依賴的 `.t-*` 類別

`about`、`services`、`contact`、`404` 與可選頁面只用這些類別，各主題自行決定它們長什麼樣。

| 類別 | 用途 |
|---|---|
| `t-container` | 內容寬度與左右邊距 |
| `t-section` | 區塊上下間距 |
| `t-eyebrow` | 眉標小字 |
| `t-h1`、`t-h2`、`t-h3` | 標題層級 |
| `t-card-title` | 卡片標題 |
| `t-lead` | 導言 |
| `t-muted` | 次要文字 |
| `t-card` | 卡片或等價容器 |
| `t-btn`、`t-btn-secondary` | 主要與次要按鈕 |
| `t-link` | 行內連結 |
| `t-tag` | 標籤 |
| `t-divider` | 分隔線 |
| `t-grid-3`、`t-grid-2` | 響應式欄位 |
| `t-list-item` | 聯絡管道等列表項 |
| `t-note` | 提示框 |
| `t-details` | 摺疊項 |
| `t-media` | 圖片容器 |
| `t-prose` | 文章內文的 Tailwind Typography 變數 |

## website/design.json

```json
{
  "schema_version": 1,
  "theme": "bookshop",
  "name": "紙本書店",
  "tonality": "warm_literary",
  "source_guide": "claude",
  "selected_at": "2026-01-01T00:00:00+00:00",
  "contains_credentials": false
}
```

`website-build` 的 `scaffold_site.py` 會自動讀取與 `config.json` 同目錄的 `design.json`，把 `theme` 寫進 `site.config.mjs`，並依 `theme.json` 的 `placeholder_colors` 產生佔位素材。也可用 `--theme` 直接指定。
