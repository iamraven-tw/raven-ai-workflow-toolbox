# My Real Second Brain 知識庫

這是可複製到使用者工作區的最小骨架，只包含空白模板與通用規則。

## 知識層級

| 類型 | 目錄 | 角色 |
|---|---|---|
| 策略與已確認洞察 | `strategy/` | 使用者確認的一人公司方向、社群策略、長期洞察與重要變更 |
| 第一大腦心得 | `book-notes/` | 使用者直接說出、閱讀與思考後形成的內容 |
| 次級資料 | `references/` | 一般篇幅的作者文章、文件與網路來源紀錄 |
| 收件匣 | `inbox/` | 唯一的收件匣；要納入知識庫的檔案先放這裡，處理完清空 |
| 外部原文 | `external/` | PDF 或 6000 字以上的長篇原文，供本地 RAG 查證 |
| 本地 RAG | `rag/` | 匯入與查詢腳本、Python 環境與可重建的向量索引 |
| 結構化知識 | `wiki/` | Agent 整理的扁平知識頁，必須連回心得或來源 |
| 衍生輸出 | `graphify-out/` | 可重建的圖譜、報告與互動式 HTML |

## 最小目錄

```text
sources/
├── README.md
├── .graphifyignore
├── .gitignore
├── inbox/
├── external/
│   └── README.md
├── rag/
│   ├── README.md
│   └── scripts/
│       ├── common.py
│       ├── ingest.py
│       └── query.py
├── strategy/
│   ├── README.md
│   ├── solopreneur-profile.md
│   └── social-media-strategy-and-insights.md
├── book-notes/
│   └── README.md
├── references/
│   └── README.md
├── wiki/
│   ├── index.md
│   └── log.md
└── graphify-out/
    └── README.md
```

實際案例可以按需要增加專案專用目錄，但不能把擴充誤列為所有使用者必須安裝的核心。

## 策略設定

第一次啟動且使用者沒有其他明確任務、`strategy/solopreneur-profile.md` 仍是 `status: not_configured` 時，使用 `/solopreneur-profile` 逐步建立設定。已有明確任務時不強制先填設定檔。

創業方向問題先讀設定檔，再透過 `/knowledge-source-retrieval` 尋找既有知識；需要挑戰假設或比較選項時使用 `/socratic-dialogue`。任何設定檔寫入都先預覽並取得使用者確認。

社群策略、內容規劃、平台角色或成效判斷相關問題，同時讀取 `strategy/social-media-strategy-and-insights.md`。它只保存人類討論並確認過的長期結論；原始報告與單次成效不得自動寫入。

## Wiki 分類

`wiki/` 先保持扁平，用 frontmatter 表達分類：

```yaml
---
type: concept | topic | synthesis | decision
status: draft | reviewed | approved | superseded
---
```

只有某一類累積到確實需要獨立管理時，才建立子目錄。

## 知識詰問與寫回

使用者想檢查觀點、挑戰假設、比較立場或形成決策時，使用 `/socratic-dialogue`：

1. 先透過 `/knowledge-source-retrieval` 查第二大腦。
2. 資料不足、可能過時或缺少可信反方時，再搜尋公開網路並保留可核對的原始網址。
3. 一次只推進一個主要問題，每二至三輪整理一次共識、分歧與待查證事項。
4. 最後由使用者確認共同理解；對話完成不等於授權寫入檔案。
5. 只有使用者明確要求保存時，才把書籍心得寫入 `book-notes/`、綜合觀點或決策寫入 `wiki/`，或把指定網路資料寫入 `references/`。

網路資料的保存格式與著作權邊界見 `references/README.md`。不另外建立完整對話紀錄目錄，避免未確認的 AI 推論變成新的知識層。

## 收件匣與本地 RAG

只有一個收件匣：`inbox/`。使用者要納入知識庫的檔案都先放進這裡；檔案原本在其他位置時，Agent 複製一份進來，絕不搬移或刪除原檔。

Agent 執行 `rag/scripts/ingest.py` 後：

1. PDF，或 6000 字以上的長文：原檔搬到 `external/`，切成約 700 字的片段存進本地向量索引，並在 `wiki/` 建立 `ext_<檔名>.md` 摘要頁草稿；Agent 接著補寫三到五行摘要與關鍵詞。
2. 其他檔案（自己的筆記、短文）：Agent 依既有規則整理進 `wiki/`、`book-notes/` 或 `references/`。
3. 全部處理完後清空 `inbox/`；處理失敗的檔案留在原處並回報。

查詢時先看 Wiki 與 Graphify。只有使用者要原文、出處、精確數字或引用，或 Wiki 不夠詳細時，才查本地 RAG，回答一律標出檔案與段落標題。

## Graphify 範圍

`.graphifyignore` 讓 Graphify 只讀整理過的知識：`wiki/` 底下只有外部原文摘要頁 `ext_*.md` 進入圖譜，讓圖譜知道「有哪些原文可查」；`inbox/`、`external/` 與 `rag/` 是原始檔、待處理檔與索引，不進圖譜。
