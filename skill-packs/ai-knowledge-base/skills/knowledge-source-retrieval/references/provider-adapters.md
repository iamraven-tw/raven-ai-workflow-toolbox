# 預設 Provider Adapter

只有工作區實際使用 Graphify 或本地 RAG 時才讀本文件。若工作區設定其他 Provider，應依 `SKILL.md` 的能力契約執行，不要套用這裡的工具名稱與欄位。

## 本地 RAG（Ollama + qwen3-embedding:4b + LanceDB）

本地 RAG 取代已停用的 NotebookLM；不再把資料送進 NotebookLM，也不再建立或同步 Notebook 集合。

### 位置與真相來源

| 路徑 | 內容 |
|---|---|
| `sources/inbox/` | 唯一的收件匣；處理完應為空 |
| `sources/external/` | 長篇外部原文的原檔，是引用的真相來源 |
| `sources/wiki/ext_*.md` | 每份原文的摘要頁（`rag: true`、`source:` 指向原檔） |
| `sources/rag/scripts/` | `ingest.py`、`query.py`、`common.py` |
| `sources/rag/.venv/` | Agent 建立的 Python 環境（lancedb、pyarrow、jieba、pypdf、requests），可重建 |
| `sources/rag/lancedb/` | 原文切段後的向量與全文索引，可由 `external/` 重建 |

索引只是檢索工具；回答引用以 `external/` 原檔內容為準。所有指令都在工作區根目錄以 `sources/rag/.venv/bin/python` 執行，不使用系統 Python 或其他環境。

### 何時查詢

1. 先看 Wiki（含 `ext_*.md`）與 Graphify。
2. 只有使用者要原文、原話、出處、精確數字或引用，或 Wiki 不夠詳細時，才查本地 RAG。

### 查詢

1. 在工作區根目錄執行 `sources/rag/.venv/bin/python sources/rag/scripts/query.py "問題" -k 5`。
2. 參數只有 `-k <筆數>`（預設 5）、`--mode hybrid|vector|fts`（預設 hybrid）與 `--root <sources 目錄>`（預設為腳本往上兩層）。`hybrid` 是向量加 jieba 中文斷詞全文檢索，以倒數排名合併。只想找特定詞彙時可用 `--mode fts`；只想找相近意思時可用 `--mode vector`。
3. 不要自己在問題前加 `Instruct:` 前綴；Qwen3 查詢前綴已由 `query.py` 處理。
4. 輸出是 JSON 陣列，每筆有 `source`（如 `external/定價研究.pdf`）、`section`（段落標題，沒有標題時是「（開頭）」；PDF 是「第 N 頁」，頁內有標題時是「第 N 頁｜標題」）、`chunk`、`score` 與 `text`。
5. 回答一律標出 `source` 與 `section`；PDF 的 `section` 已含頁碼。需要更完整上下文時，回到 `external/` 原檔定向閱讀。
6. `query.py` 印出 `{"error": "no_index"}` 代表尚無外部原文，回報「本地 RAG 目前沒有資料」；`embed_failed` 依下方失敗處理檢查 Ollama；`fts_unavailable` 表示全文索引需要重新匯入重建。

### 匯入

1. 使用者檔案原本在其他位置時，複製到 `sources/inbox/`，原檔不動。
2. 執行 `sources/rag/.venv/bin/python sources/rag/scripts/ingest.py`。
3. 依 JSON 報告處理：`external` 的每份補寫 `ext_*.md` 三到五行摘要與關鍵詞（`reindexed: true` 是內容相同的重建，摘要頁已存在，不重寫）；`wiki_pending` 依既有規則歸檔後刪除收件匣副本；`unsupported`（不支援的格式與子資料夾）與 `errors` 留在收件匣並回報。只接受 `.md`、`.markdown`、`.txt`、`.pdf`、`.html`、`.htm`，文字檔須為 UTF-8。
4. 參數只有 `--min-chars <字數>`（預設 6000）、`--all-external` 與 `--root <sources 目錄>`。預設門檻：PDF 或 6000 字以上進 `external/`，切成約 700 字的片段（前後重疊 120 字）。使用者明確要求時才用 `--all-external` 或 `--min-chars`。
5. 資源：匯入或查詢時 Ollama 約佔 3.1 GB 記憶體，閒置約 2 分鐘後自動卸載。大量匯入前先告訴使用者大概需要的時間；技能包附有 `docs/integrations/local-rag.md` 時，需要數字可引用其中的「參考紀錄：維護者單機實測」，並說明那只是單一電腦的參考值；沒有該文件時只說明會依檔案大小而定，不編造數字。

### 失敗處理

- 連線錯誤：Ollama 沒有在執行，執行 `brew services start ollama` 後重跑。
- 找不到模型：說明容量後重新 `ollama pull qwen3-embedding:4b`。
- `ModuleNotFoundError`：`.venv` 不完整，重新安裝五個套件。
- 失敗時保留收件匣與既有索引，不宣稱匯入成功。
- 舊版留下的 Notebook 紀錄（例如 `sources/references/notebooks/`）若仍存在，只保留為歷史紀錄，不新增、不同步。

## Graphify

### 角色與輸出

- `sources/graphify-out/graph.json`：Agent 查詢節點、關係與信心標記。
- `sources/graphify-out/graph.html`：使用者探索關係的互動式網頁。
- `sources/graphify-out/SOURCES_OVERVIEW.md`：來源概況與路由輔助。

實際檔名可能隨 Provider 版本改變；先使用目前已安裝的 Graphify 技能檢查能力與輸出，不把這些檔名當成所有知識結構 Provider 的永久介面。

### 分析範圍

- Graphify 分析 Wiki 與外部原文摘要頁 `wiki/ext_*.md`，讓外部原文透過摘要與關鍵詞連進知識圖譜；圖譜不含原文本身，需要原文時改查本地 RAG。
- `sources/.graphifyignore` 以 `wiki/*` 加 `!wiki/ext_*.md` 實作：一般 Wiki 頁面不重複進圖譜，摘要頁進圖譜；並排除 `inbox/`、`external/`、`rag/`。
- 修改 `.graphifyignore` 前先向使用者預覽新規則並取得同意。

### 查詢與交付

- 使用已安裝的 Graphify 技能定向查詢，不直接掃描整個圖譜輸出。
- 保留 `EXTRACTED`、`INFERRED`、`AMBIGUOUS` 等信心標記。
- 本次若成功建立或更新圖譜，且 `graph.html` 存在，提供可開啟的絕對路徑。
- 涉及三個以上節點、跨文件關係、概念路徑、核心節點或群聚結構時，主動附上互動圖。
- 同時說明最值得查看的二至五個節點或關係，不能只交付檔案。

### 更新狀態

- `.needs_update` 存在、索引標成 `pending_update`，或 HTML 早於 JSON 時，將視覺化標為可能過期。
- 新增一小段筆記不代表必須立即重建；先標記更新需求，再依資料量與當次任務決定。
- 只有更新實際成功後，才能把狀態改為 `current`。
- manifest 缺失、環境異常或變更數量不合理時停止，不自動重建或清空既有圖譜。
