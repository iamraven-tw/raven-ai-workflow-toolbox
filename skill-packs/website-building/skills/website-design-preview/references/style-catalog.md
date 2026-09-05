# 主題目錄

六個主題，各依 open-design（Apache-2.0）的一份設計指引完整實作。主題名稱是本專案自訂的意象名；指引來源只用於聲明與追溯，不作為使用者可見的預設值。

| 編號 | id | 名稱 | 調性 | 指引 | 版面與元件的關鍵差異 | 適合 |
|---|---|---|---|---|---|---|
| 1 | `bookshop` | 紙本書店 | 溫暖書卷 | claude | 羊皮紙底、赤陶色唯一 CTA；襯線標題字重 500；淺色與近黑章節交替；ring shadow 取代邊框；文章列表是編號目錄 | 教學、寫作、諮詢、個人品牌 |
| 2 | `nightshift` | 夜間工作室 | 暗黑沉浸 | linear-app | 近黑畫布、半透明白邊框、靛紫唯一色彩；置中 Hero 加帶邊框媒體；大標負字距；文章列表是時間軸 | 軟體、AI、影音製作 |
| 3 | `gallery` | 留白畫廊 | 極簡純淨 | vercel | 純白、無色彩；陰影當邊框；區塊間一條黑線；服務用編號流程列；文章列表是陰影卡片網格 | 設計、顧問、專業服務 |
| 4 | `showroom` | 黑白展場 | 攝影展廳 | apple | 黑、淺灰、白三色章節交替；置中巨標；膠囊按鈕；藍色只給動作；文章列表是圖片優先卡片 | 攝影、產品、空間、作品集 |
| 5 | `playground` | 遊樂場 | 鮮豔活力 | figma | 介面只有黑白，Hero 是多色漸層；藥丸與圓形按鈕；虛線焦點框；輕字重內文；等寬大寫小標 | 創意工作室、活動、課程 |
| 6 | `broadsheet` | 報刊編輯 | 雜誌印刷 | wired | 零圓角、無陰影；2px 黑框按鈕；細線分欄；等寬大寫眉標；黑色橫幅區塊標題；報頭式導覽；頭版式首頁 | 媒體、評論、電子報 |

## 建議規則

`style_gallery.py list --recommend <調性>` 回傳該調性的主題。調性由 `website-setup` 依受眾推薦；沒有時：

- 「暗色」「科技」「專業」：`dark_immersive`
- 「溫暖」「親切」「書」「教學」：`warm_literary`
- 「乾淨」「簡單」「可信」：`clean_minimal`
- 「照片」「作品」「展示」：`photo_showroom`
- 「活潑」「年輕」「有趣」：`colorful_energetic`
- 「雜誌」「文章」「報導」：`editorial_press`
- 無法判斷：`clean_minimal`

## 字型

所有主題只用系統字型堆疊，Latin 字型依指引指定（Georgia、Inter、Geist、SF Pro、Playfair 等）並提供完整 fallback，中文一律 Noto Sans TC／Noto Serif TC 系統字。沒有外部字型請求。要接 Google Fonts 屬於擴充。

## 新增主題

新增一個主題要：一份可追溯、授權允許的設計指引；`template/src/themes/<id>/` 內完整的 theme.json、theme.css、BaseLayout、Header、Footer、Home、BlogIndex、BlogPost；theme.css 定義全部 `.t-*` 共用類別；用意象命名不用品牌名；重新執行 `export_previews.py`；通過 `tests/test_style_gallery.py`。
