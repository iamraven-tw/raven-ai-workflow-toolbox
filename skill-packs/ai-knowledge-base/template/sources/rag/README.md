# 本地 RAG

本地 RAG 讓 Agent 在你的電腦上搜尋長篇外部原文（`../external/`），找出原話、出處與精確數字。整個過程不連網、不上傳，也不需要登入任何帳號。

這個資料夾全部由 Agent 安裝與操作，你不需要自己輸入任何指令。

| 位置 | 內容 | 可否刪除 |
|---|---|---|
| `scripts/` | 匯入（`ingest.py`）、查詢（`query.py`）與共用工具（`common.py`） | 不要刪除；由技能包提供 |
| `.venv/` | Agent 建立的 Python 環境（lancedb、pyarrow、jieba、pypdf、requests） | 可重建；不納入版本控制 |
| `lancedb/` | 原文切段後的向量與全文索引 | 可由 `../external/` 重建（Agent 把原文複製回收件匣重新匯入，不會產生重複檔案）；不納入版本控制 |

## 運作方式

1. 你把檔案交給 Agent，或放進 `../inbox/`。
2. Agent 執行 `ingest.py`：PDF 或 6000 字以上的長文搬到 `../external/`，切成約 700 字的片段存進 `lancedb/`，並在 `../wiki/` 建立 `ext_<檔名>.md` 摘要頁草稿；其他短文與你自己的筆記，由 Agent 依規則整理進 Wiki 或讀書筆記。
   - 只接受 PDF、Markdown、純文字（UTF-8）與 HTML；Word、簡報、圖片等其他格式與子資料夾會留在 `../inbox/`，Agent 會告訴你原因。
3. Agent 補寫三到五行摘要與關鍵詞，最後清空 `../inbox/`。
4. 查詢時 Agent 先看 Wiki 與 Graphify；只有你要原文、出處、精確數字或引用，或 Wiki 不夠詳細時，才用 `query.py` 搜尋，回答會標出檔案與段落標題。

## 資源用量

- 需要本機的 Ollama 與 `qwen3-embedding:4b` 向量模型（約 2.5 GB）。
- 匯入或查詢時約佔 3.1 GB 記憶體；閒置約 2 分鐘後模型自動卸載，Ollama 只剩約 40 MB。
- 建議 16 GB 記憶體以上的 Mac。
