# HTML＋CSS 資訊圖卡與免費 SVG

適用比較表、步驟、資料重點、簡報型資訊圖與高文字密度輪播。只處理圖片排版，不建立官網、不部署、不產生影片。圖片要求不會因使用 HTML 而轉交官網建置技能。

## 可執行流程

1. 以 [資訊圖卡範本](../assets/information-card.html) 為起點，依這次需求調整；範本為虛構文字、純 CSS，沒有網路資源。使用固定畫布像素、清楚標題／主體／註記層次與 CSS Grid／Flexbox。文字保留為 HTML 文字節點，以便精確核對和修改；將外部文字 HTML escape，不直接當 markup、CSS、script 或 URL 執行。
2. 資訊太多先分頁或調整配置，不靠極小字或 overflow:hidden 藏掉內容。每頁保持共同字級層次、配色、留白及圖示風格。使用本機已授權字型，等待字型載入完成再檢查；不引用遠端字型 CDN。
3. 圖示依設定選 Heroicons 或不使用。優先使用既有且有來源／授權紀錄的 SVG；沒有時，只從下方固定官方來源取得本次需要的少數檔案及 LICENSE，事前告知，依已核准下載範圍執行。未授權下載可先用 CSS 幾何圖形，不自行安裝套件或下載整個圖庫。
4. 外來 SVG 視為未信任檔案，檢查後只保留必要的靜態 path／shape 與樣式屬性；排除 script、事件屬性、foreignObject、外部 href／image／CSS URL 等可執行或連網內容。SVG 來源、版本、個別檔案雜湊、授權與修改要記錄。不能只因副檔名是 SVG 就當安全素材。
5. 使用環境已提供、已授權的本機 HTML 渲染與截圖工具；無頭瀏覽器可依其 Playwright 技能操作。不得為截圖偷偷安裝 Playwright／Chromium、開外部網站登入或將私人 HTML 上傳線上轉圖服務。渲染時封鎖非本機網路請求；若工具無法做到，改用能隔離的既有工具或停下。缺少工具時只交 HTML／CSS 原稿，標記 awaiting_export，不把原稿叫作 PNG。
6. 以每頁的固定畫布作截圖，不截整個瀏覽器視窗。設定 viewport 與輸出倍率，使實際 PNG 與 brief 像素一致；等待 document.fonts.ready 及必要素材完成。檢查每頁 scrollWidth／scrollHeight 沒有超出 clientWidth／clientHeight，並檢查所有文字框的邊界。通過尺寸檢查後仍要實際開 PNG 看字、裁切、圖示和手機預覽，不以 DOM 檢查取代視覺驗收。
7. 保存 HTML、CSS、素材來源／授權與 PNG；再按 image_assets.py check 的契約建立 manifest。production.route=html_css，tool 是實際渲染工具與已知版本，model=not_applicable，source_refs 包含原稿及圖示授權紀錄，created_at 是實際輸出時間。不填假的 AI／Pillow 製作紀錄。

## 免費圖示來源

查證 2026-09-05：[Tailwind Labs Heroicons v2.2.0](https://github.com/tailwindlabs/heroicons/tree/v2.2.0)，提供 SVG 圖示；[LICENSE](https://github.com/tailwindlabs/heroicons/blob/v2.2.0/LICENSE) 為 MIT。免費不代表沒有條件；保留著作權及授權聲明，素材與原稿一起交付時一併保存 LICENSE，不必把授權全文塞進圖卡。

只從固定版本選檔；不使用不明免費素材站、遠端嵌入 script 或未鎖定 CDN。Toolbox 不綑綁這套圖示、不提供自動下載器；更換來源須查該來源自身授權，不能套用 Heroicons 的 MIT。字型、照片與圖示的權利分別確認。
