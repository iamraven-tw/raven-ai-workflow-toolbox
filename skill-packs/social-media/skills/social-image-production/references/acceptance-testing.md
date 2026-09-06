# 四種製圖路徑的集中驗收簡報

這份文件只在準備或執行圖片集中驗收時讀取。一般製圖任務不需要載入。公開資產全部是虛構內容，不含維護者品牌、帳號或私人路徑。

## 共用測試內容

主案例使用 [直式三頁簡報](../assets/acceptance-test-brief.json)，四條路徑必須使用相同文字、順序與視覺設定：

- 主色 `#174A4A`、輔色 `#E9A23B`、背景 `#F7F4EC`、文字 `#1E2A2A`。
- 字型意圖為 Noto Sans TC；實測環境必須先證明字型已存在且可用於本次產物，否則停止，不下載或假稱中文字形通過。
- 1080 × 1350、三頁 Instagram 測試輪播。這是測試畫布，不代表平台當前官方上限。
- 精確文字含繁體中文、`AI Agent`、阿拉伯數字、標點、問號、箭頭與多行比較。
- [方形簡報](../assets/acceptance-test-square-brief.json)另測 1080 × 1080 的重新排版；不能把直式圖只裁切成方形。
- HTML 路徑以[三頁原稿](../assets/acceptance-information-card.html)為基準；沒有遠端資源或 JavaScript。
- 網頁路徑使用[三份完整提示詞](../assets/acceptance-web-prompts.md)，沒有待使用者補寫的 placeholder。
- 溢位負例使用[故意超量文字簡報](../assets/acceptance-overflow-brief.json)的副本；結果使用[分層紀錄範本](../assets/acceptance-result-template.json)，未執行欄位保持 `not_run`。

所有路徑的最終成品都要逐張實際開圖，核對 exact_text、繁體字形、尺寸、裁切、安全留白、手機縮圖、順序及替代文字。OCR、提示詞、DOM、檔案存在或 manifest 單獨通過都不能取代看圖。

## 共用設定 Fixture

集中驗收在獨立暫存工作區建立 schema 5 虛構設定，`brand_visual.status=confirmed` 並填入上述四種色彩、`font_family=Noto Sans TC`、`style_notes=現代編輯式資訊圖卡`；`logo_ref` 與 `main_visual_ref` 留空。每條路徑輪流設為 `default_method`，正式設定 bytes 在測試前後都必須相同。

資訊密集偏好設為 `html_css`。一般封面依 default_method；比較表加入 `--information-dense` 時應走 HTML＋CSS。本次明確指定其他方式時仍以當次指示優先，且不得改回設定。

## 路徑 A：Codex

1. 設 `default_method=codex`，確認 route 是 `direct_generate`，不出現方式問題或「可以開始嗎」。
2. 實際 Codex 生圖工具可用且本次已授權時，直接生成三頁；工具名稱、模型版本、提示詞與時間依實際回傳保存。
3. manifest 的 `production.route=ai`、`tool` 為實際 Codex 工具、`prompt_ref` 指向私人提示詞紀錄。不能填 Antigravity 或網頁服務名稱。
4. 若工具無法取得 1080 × 1350，保存實際尺寸並停止交接，先預覽後續轉換方案；不能改 JSON 假裝相符。

## 路徑 B：Antigravity

1. 設 `default_method=antigravity`，在 Antigravity 實際環境確認 route 是 `direct_generate`；不把 Codex 的工具可用性當成 Antigravity 已可用。
2. 工具可用且已授權時直接生成相同三頁；保存實際工具、模型、提示詞與輸出。
3. manifest 同樣是 `production.route=ai`，但 `tool` 必須是實際 Antigravity 工具。
4. 找不到工具時停在需求包，不切 Codex、網頁模型或自動購買 API。

## 路徑 C：網頁模型

1. 設 `default_method=web` 且 `web_provider` 使用一個虛構或當次已確認名稱；一般情況 route 必須是 `deliver_prompt`。
2. `prompt-package.md` 每頁都包含完整共同色票、1080 × 1350、該頁 exact_text、不得新增數字／網址／標誌、繁體中文與同系列規則，最後要求使用者把圖片傳回檢查。狀態是 `awaiting_user_images`，不可建立假成圖 manifest。
3. 只有同一回合使用者明確要求代操作，route 才可為 `operate_browser_with_current_request`；下次呼叫不帶該證據時必須恢復 `deliver_prompt`。
4. 實機瀏覽器遇到登入、條款、安全或新增費用時交人；生成結果不明不重按。瀏覽器完成仍要把圖片帶回共同視覺檢查。

實際三份提示詞已完整寫在 `acceptance-web-prompts.md`；每頁至少包含以下結構，不得讓使用者自行補字：

```text
請製作 1080 × 1350 的直式社群圖卡。使用深青 #174A4A、橘色 #E9A23B、米白 #F7F4EC、深色文字 #1E2A2A，採現代編輯式資訊設計。圖上文字必須逐字使用繁體中文，不新增統計、網址、標誌或品牌名稱。

本頁精確文字：
<從 acceptance-test-brief.json 複製該頁 exact_text>

請保留安全留白，確保手機縮圖仍可閱讀，並維持三頁的共同版面層次。
```

## 路徑 D：HTML＋CSS

1. 設 `default_method=html_css` 或讓資訊密集偏好生效，route 必須是 `render_html`。
2. 從驗收 HTML 原稿建立私人版本；品牌色使用 CSS 變數，文字保持 HTML text node。不得加入遠端字型、CDN、script、外部圖片或不安全 SVG。
3. 只使用環境既有且已授權的本機 renderer；沒有 renderer 時交原稿並標 `awaiting_export`，不能宣稱 PNG 完成。
4. 每張以 1080 × 1350 元素本身截圖。等待 `document.fonts.ready`，確認 scrollWidth／scrollHeight 不超出 clientWidth／clientHeight，且所有文字框位於畫布內。
5. manifest 的 `production.route=html_css`、`model=not_applicable`，`source_refs` 包含 HTML／CSS 與實際使用的字型／圖示權利證據。

## 溢位與失敗案例

在不修改正式 fixture 的副本中，把第二頁 Agent 說明替換成重複十次的長句。Pillow 備援及 HTML DOM 邊界檢查都必須停止或要求分頁，不得使用 `overflow:hidden`、縮成無法閱讀的小字、截字或標記已完成。失敗後正式 fixture 與既有版本 bytes 不變。

再分別演練：字型缺字、生成圖出現簡體字、輸出 1024 × 1024、三頁順序錯誤、第二頁被改字、網頁生成結果不明。每項都要保留產物或需求狀態、列出單一下一步，不得把部分成功當整組 approved。

## 產物紀錄與人工關卡

每條路徑的私人版本必須包含 brief、提示詞或 HTML／CSS 原稿、來源／權利、實際輸出及 `manifest.json`。普通 `check` 可以驗證草稿；`--handoff` 只有在 `unresolved=[]`、逐張視覺檢查及使用者看過同一組成品的 `images_only` 核准都有效時才通過，而且 `publishing_authorized` 仍為 false。

集中驗收結果分開記錄：route 選擇、工具可用、依賴／字型、生成或渲染、實際尺寸、逐字與視覺檢查、使用者圖片核准、發布交接。任何一層通過都不能代表其他三條路徑或正式平台支援。
