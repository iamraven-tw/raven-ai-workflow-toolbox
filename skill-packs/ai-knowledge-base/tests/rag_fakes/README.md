# 本地 RAG 測試替身

`test_local_rag.py` 的確定性測試用這些極簡替身取代 `requests`、`jieba`、`lancedb` 與 `pypdf`，讓預設的 `python3 -m unittest` 不需要安裝任何套件也能執行 `ingest.py` 與 `query.py`。

- 只實作腳本用到的最小介面，資料以 JSON 存在暫存資料夾，不代表真實 LanceDB 的排序品質。
- `pypdf` 替身只讀測試自己產生的極簡 PDF，不是 PDF 解析器。
- 真實套件的端對端測試仍由 `AI_KB_RAG_PYTHON` 指定的 Python 執行。
- 這裡不屬於使用者工作區範本，也不會被安裝。
