# 次級資料

`references/` 保存不是由使用者第一大腦直接產生、但可用來支持閱讀、研究與查證的資料，例如作者文章、PDF、TXT、軟體文件與報告。

1. 已存在於其他位置的本機檔案預設不複製；只有使用者明確要求納入知識庫時才保存於此。
2. 一般一本書或單一文件不需要 Notebook，可以在當次任務定向讀取。
3. 只有資料集龐大、跨大量文件，或反覆載入明顯浪費 Token 時才使用 Notebook。
4. Notebook 大型內容不在本機備份；本機只在 `notebooks/` 保存路由、中繼資料與來源清單。
5. 次級資料用來支持 `../book-notes/`，不能取代使用者直接說出的心得。

## 網路來源

Agent 在研究或 `/socratic-dialogue` 對話中使用網路資料時，必須在當次回答附上可直接開啟的原始網址，並說明該來源支持、補充或挑戰哪一項說法。網路資料預設只用於當次任務，不因為曾被引用就自動保存到本目錄。

只有使用者明確要求長期保存時，才在 `references/` 建立本機紀錄。至少使用以下 frontmatter：

```yaml
---
source_type: web
title: 網頁或資料名稱
author: 作者或未標示
publisher: 發布者或網站名稱
source_url: https://example.com/original-page
published_on: YYYY-MM-DD 或未標示
retrieved_on: YYYY-MM-DD
saved_reason: 為什麼要長期保存
---
```

正文保存必要摘要、短引文、來源支持或挑戰的觀點，以及它與使用者既有知識的關係。不要只保存搜尋結果頁或轉址網址，也不得整篇複製受著作權保護的網頁內容。
