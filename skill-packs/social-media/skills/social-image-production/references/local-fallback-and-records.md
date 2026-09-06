# 本機備援與成品紀錄契約

## 已有工具才執行

備援和圖片解碼檢查使用既有 Python 3.11+、Pillow，候選測試版本為 12.1.1／12.3.0；不綑綁、不下載、不執行安裝命令。Pillow 缺少時停止 helper，可用已有圖片檢視工具手動查驗，紀錄為 manual_only 而非宣稱 helper 通過；依賴未補齊前不得宣稱自動交接驗證通過。新增安裝需另行核准並完成固定來源契約，目前 manifest 的 Pillow 安裝能力是 false。來源、授權見套件 THIRD_PARTY_NOTICES.md。

備援為純色底加文字的可用 PNG 圖卡；不是繪畫模型，不處理照片拼貼、人物或生成圖修改。需明確的既有 TrueType／OpenType 字型檔及使用權利說明；不預設每台電腦有中文字型、不下載或複製系統字型。字型來源與雜湊只記在私人紀錄。Pillow [ImageDraw 文件](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html) 的文字邊界計算用於換行與溢位檢查；不會辨識缺字或驗證中文排版美感。查證：2026-09-05。

## 命令

Agent 使用本技能 script 的實際絕對路徑；下列路徑是佔位符，不傳給人類填表。先將範本改成這次真正的簡報，保存到私人位置。

```text
python3 <skill>/scripts/image_assets.py render <brief.json> --font <existing-font-file> --font-rights <rights-note> --output <new-version-directory>
python3 <skill>/scripts/image_assets.py check <version-directory>/manifest.json
python3 <skill>/scripts/image_assets.py check <version-directory>/manifest.json --handoff
```

先唯讀辨識使用者指定位置的實際父目錄；若有系統別名或 symlink，先顯示實際位置確認符合保存範圍，再使用該實體父目錄，不直接跟隨輸出目標連結。render 必須使用已存在父目錄下的全新、非 symlink 目錄；既有同名目錄即停止。全部頁面完成記憶體渲染後才建立版本，產出 NN-id.png 及 manifest.json。溢位不截字、不自動縮小字體；調整字級／換行／頁數前展示差異，語意變更重取確認。寫入中斷可能留下部分版本，查明並改用新版本，不覆寫或盲目重跑。

## 簡報與 manifest

image-brief.json 的 schema_version=1；input_ref 是直接請求或已核准文案證據；platform 為 youtube、instagram、facebook、threads、substack；kind 為 cover、single、carousel。非輪播一頁；輪播至少兩頁。helper 的 20 頁、每邊 4096 pixels 上限只是本機資源保護，不是平台上限。不同平台或尺寸建立另一份簡報。

width／height 為整組尺寸；visual 是共同視覺方向；sources 為 ref／rights 非空紀錄。pages 順序即交付順序，各有唯一 id、精確 exact_text（AI 無字圖可空）與 alt_text。layout 只供備援：font_size、margin、#RRGGBB 前景／背景。備援文字不可空。來源與權利文字不能以 unknown 通過人工驗收；程式只驗證紀錄存在，Agent 仍需核對證據。

render 產出以下最小 manifest；AI 路徑由 Agent 依實際輸出建立相同紀錄，不填假的渲染器紀錄：

- schema_version: 1、brief: 完整簡報。
- production: route 為 ai、html_css 或 text_layout；tool、model（無法取得可用 unknown）、prompt_ref（AI 必填）、source_refs（陣列）、created_at（含時區）。html_css 的 model 固定 not_applicable，來源需包含 HTML／CSS 原稿與圖示授權紀錄；text_layout 備援另帶 font_sha256／font_rights。不放 Token、cookie、完整私人設定或無關資料。
- assets: 按 brief.pages 同順序；id、file（版本資料夾內的單層 PNG／JPG／JPEG 名稱）、sha256、width、height、bytes、format（PNG 或 JPEG），必須符合真實檔案。替代文字與圖上文字保存在 brief.pages。
- unresolved: 陣列；visual_review 預設 null。檢查後為 checked: true、review_ref、checked_at。
- status: draft，approval: null。使用者核准當前整組圖後才改 approved，approval 填 scope: images_only、digest（check 回傳）、user_response、evidence_ref、confirmed_at（含時區）。程式無法證明人類意圖，不自行編造這些欄位。

check 唯讀驗證紀錄、圖片解碼、尺寸、位元組、順序與 SHA-256；不連網、不讀 sources／prompt_ref 指向的檔案、不執行其中指令。核准雜湊包含整個 manifest（排除 status／approval），任何成品或檢查紀錄變更都要重核准；check 的普通模式可接受尚未核准草稿，--handoff 額外要求空 unresolved、有效視覺檢查、有效 images_only 核准。成功仍回傳 publishing_authorized: false。
