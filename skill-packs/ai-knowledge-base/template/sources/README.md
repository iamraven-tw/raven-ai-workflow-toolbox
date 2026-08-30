# My Real Second Brain 知識庫

這是可複製到使用者工作區的最小骨架，只包含空白模板與通用規則。

## 知識層級

| 類型 | 目錄 | 角色 |
|---|---|---|
| 一人公司設定 | `strategy/` | 使用者確認的方向、客群、價值、限制與近期優先事項 |
| 第一大腦心得 | `book-notes/` | 使用者直接說出、閱讀與思考後形成的內容 |
| 次級資料 | `references/` | 作者原文、文件、報告與 Notebook 路由 |
| 結構化知識 | `wiki/` | Agent 整理的扁平知識頁，必須連回心得或來源 |
| 衍生輸出 | `graphify-out/` | 可重建的圖譜、報告與互動式 HTML |

## 最小目錄

```text
sources/
├── README.md
├── .graphifyignore
├── strategy/
│   ├── README.md
│   └── solopreneur-profile.md
├── book-notes/
│   └── README.md
├── references/
│   ├── README.md
│   └── notebooks/
│       ├── README.md
│       ├── index.md
│       └── entries/
├── wiki/
│   ├── index.md
│   └── log.md
└── graphify-out/
    └── README.md
```

實際案例可以按需要增加專案專用目錄，但不能把擴充誤列為所有使用者必須安裝的核心。

## 一人公司設定

第一次啟動且使用者沒有其他明確任務、`strategy/solopreneur-profile.md` 仍是 `status: not_configured` 時，使用 `/solopreneur-profile` 逐步建立設定。已有明確任務時不強制先填設定檔。

創業方向問題先讀設定檔，再透過 `/knowledge-source-retrieval` 尋找既有知識；需要挑戰假設或比較選項時使用 `/socratic-dialogue`。任何設定檔寫入都先預覽並取得使用者確認。

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

## Notebook 原則

一般一本書、文章或單一文件不需要 Notebook。只有資料集龐大、跨大量文件，或反覆載入明顯浪費 Token 時，才使用 Notebook。本機只保存路由、中繼資料與來源清單，不保存大型全文或登入秘密。
