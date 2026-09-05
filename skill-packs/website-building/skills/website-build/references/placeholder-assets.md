# 佔位素材

`scaffold_site.py` 會依站名與主題 `theme.json` 的 `placeholder_colors` 產生下列檔案。全部用標準函式庫產生，不需要圖片處理套件。

| 檔案 | 尺寸 | 格式 | 內容 | 使用者替換時的建議 |
|---|---|---|---|---|
| `public/favicon.svg` | 64×64 | SVG | 主題強調色底、站名前兩字 | 換成 Logo 的 SVG，保持正方形 |
| `public/apple-touch-icon.png` | 180×180 | PNG | 純強調色 | 180×180 PNG |
| `public/og-image.png` | 1200×630 | PNG | 背景色加強調色帶，無文字 | 1200×630 JPG 或 PNG，含站名 |
| `public/images/placeholders/hero.svg` | 960×720 | SVG | 幾何佔位加「請替換」字樣 | 1920×1080 以內的 WebP 或 JPG |
| `public/images/placeholders/avatar.svg` | 400×400 | SVG | 幾何人像 | 400×400 WebP 或 JPG |
| `public/images/placeholders/offering-1.svg` 到 `offering-3.svg` | 48×48 | SVG | 線條圖示 | 48×48 或 64×64 SVG |

## 規則

- PNG 佔位圖沒有文字，因為標準函式庫無法排版字型。OG 圖若要有站名，交給生圖技能或使用者提供。
- 使用者提供素材時，只替換對應檔案，並在需要時更新頁面的 `src` 路徑；不覆蓋或刪除使用者提供的檔案。
- 文章封面圖放在 `public/images/posts/<slug>/cover.jpg`，建議 1200×630、200KB 以內；沒有封面時文章頁不顯示圖片，不用預設圖。
- 所有裝飾性圖片的 `alt` 為空字串；有意義的圖片由使用者提供替代文字。
