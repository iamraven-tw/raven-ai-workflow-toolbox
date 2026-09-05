# 六個主題以外的風格來源

六個內建主題是第一版的預設路徑。以下都是擴充，需要使用者另行同意，且不在虛構測試涵蓋範圍。

## 可用來新增主題的其他指引來源

| 來源 | 內容 | 授權 | 用法 |
|---|---|---|---|
| [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)（125k stars） | 85 種風格定義（極簡瑞士、新粗野主義、玻璃擬態、便當格、黏土風、賽博龐克等），各含色彩、效果、適用產品、CSS 關鍵字與實作檢查表；161 組色盤、57 組字型配對、Google Fonts 全表 | MIT | 風格維度比 open-design 多，可用它的檢查表確認新主題有明確差異點，並用字型表為主題挑中文字型 |
| [Google Labs design.md 範例](https://github.com/google-labs-code/design.md/tree/main/examples) | 3 個完整範例（atmospheric-glass、paws-and-paths、totality-festival），各含 DESIGN.md、design_tokens.json、tailwind.config.js | Apache-2.0 | 可直接轉成新主題；也是「一套主題該定義到多細」的標準 |
| [open-design](https://github.com/nexu-io/open-design) 其他品牌指引 | 153 份 DESIGN.md，以真實品牌命名的那些最完整（17 到 28KB），以形容詞命名的只有 3KB 且內容空泛 | Apache-2.0 | 只用完整的那批；主題名稱用意象名，來源記在 theme.json |
| [Astro 官方主題庫](https://astro.build/themes/) | 真正做好的整站範本，多數 MIT | 各自不同 | 不是指引而是成品，可拆版面手法，但每個要個別確認授權 |

| 來源 | 條件 | 做法 | 狀態 |
|---|---|---|---|
| open-design 的其他設計指引 | 需要網路下載單一 `DESIGN.md`；manifest 已記錄 commit `50e305dff2b64d9dc0220e5dfa5d8c98ba4364e3` | 照指引新增一個完整主題目錄，重新匯出預覽 | 可做，屬維護者工作 |
| 使用者自己的品牌色與字型 | 使用者提供色碼與字型名稱 | 以最接近的內建主題為基底複製成新主題，只改 theme.css 的變數；仍要重新匯出預覽 | 可做，不需網路 |
| Google Fonts | 外部字型請求，影響隱私與載入 | 在主題 BaseLayout 加入 `<link>`，並在隱私說明揭露 | 第二版 |

擴充來源加入前都要照 manifest `[style_sources]` 的納入門檻：OSI 授權、Stars 一萬以上或大廠出品、近 90 天有更新、固定 commit 或版本、不含品牌圖片或字型檔。
