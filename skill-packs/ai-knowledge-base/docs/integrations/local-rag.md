# 本地 RAG 整合邊界

## 角色

本地 RAG 是 `My Real Second Brain` 目前預設的「有根據檢索」後端，取代先前的 NotebookLM／`notebooklm-py`。它在使用者自己的電腦上，把長篇外部原文切成小段、建立向量與中文全文索引，讓 Agent 找出原話、出處與精確數字。

- 不連網、不上傳、不需要登入任何帳號；安裝完成後所有資料都留在本機。「不上傳」的前提是 Ollama 跑在這台電腦上；若把 `OLLAMA_HOST` 指到別台電腦，要做向量嵌入的文字片段就會送到那台電腦，資料就離開本機了。
- 只負責「查原文」。日常問題先看 Wiki 與 Graphify，本地 RAG 是補充，不是第一站。
- 外部原文屬於探索性來源，優先度低於使用者已消化的心得；重要內容經使用者閱讀確認後，才能整理成第一大腦知識。

狀態：可安裝候選版，等待外部驗收，不是正式支援。

## 組成

| 元件 | 位置 | 來源與授權 | 分級 |
|---|---|---|---|
| 匯入與查詢腳本 `common.py`、`ingest.py`、`query.py` | `sources/rag/scripts/`（由範本複製） | 本技能包自有程式，Apache-2.0 | 技能包的一部分 |
| Ollama（本機模型服務） | Homebrew 安裝；`brew services` 開機自動啟動 | [Homebrew formula](https://formulae.brew.sh/formula/ollama)、MIT | C 級 `latest` |
| `qwen3-embedding:4b` 向量模型（約 2.5 GB） | Ollama 自己的模型目錄 | [Ollama 模型庫](https://ollama.com/library/qwen3-embedding)、Apache-2.0 | C 級 `latest` |
| lancedb、pyarrow、jieba、pypdf、requests | 工作區內的 `sources/rag/.venv/`（約 500 MB） | PyPI；Apache-2.0、Apache-2.0、MIT、BSD-3-Clause、Apache-2.0 | C 級 `latest` |
| 向量與全文索引 | `sources/rag/lancedb/` | 使用者自己的資料，可重建 | 不屬於技能包 |

`.venv/` 與 `lancedb/` 都寫在工作區的 `sources/.gitignore`，不會進版本控制。

## 硬體需求

- 目標：16 GB 記憶體以上的 Mac。
- 匯入或查詢時 Ollama 約佔 3.1 GB 記憶體；閒置約 2 分鐘後模型自動卸載，只剩約 40 MB。
- 匯入速度與查詢時間依電腦而定；需要預估時間時，只能引用本文最後的「參考紀錄：維護者單機實測」，並說明那是單一電腦的參考值，不是保證。
- Windows 與 Linux 尚未驗證；Agent 遇到非 macOS 環境時先回報，詢問使用者是否要嘗試，不宣稱已支援。

## 安裝（全部由 Agent 執行）

使用者不需要輸入任何指令。Agent 先宣讀根專案 `docs/dependency-policy.md` 的標準外部來源提醒，說明下列下載的來源、容量、授權、記憶體需求，以及「全部免費、不需付費帳號」，取得同意後才執行：

```bash
brew install ollama
brew services start ollama
ollama pull qwen3-embedding:4b
uv venv sources/rag/.venv --python 3.12
uv pip install --python sources/rag/.venv/bin/python lancedb pyarrow jieba pypdf requests
```

- 以上命令都在使用者工作區根目錄執行。
- 缺少 Homebrew 或 uv 時，依根專案 `INSTALL.md` 的環境準備處理；Homebrew 安裝過程若要求輸入電腦密碼，只請使用者在跳出的視窗或終端提示輸入密碼，不請使用者輸入任何指令。
- `brew services start ollama` 讓 Ollama 開機自動啟動，之後不需要手動開啟。
- Ollama 已經安裝或已在執行時沿用，不重裝；模型已存在時 `ollama pull` 只會確認。

## 驗證

1. `ollama --version` 與 `ollama list` 看得到 `qwen3-embedding:4b`。
2. `sources/rag/.venv/bin/python -c "import lancedb, pyarrow, jieba, pypdf, requests"` 成功。
3. 在暫存資料夾建立 `inbox/`，放一份 6000 字以上的虛構文件，執行 `ingest.py --root <暫存資料夾>`，再用 `query.py --root <暫存資料夾>` 查詢，確認回傳檔案與段落標題；結束後刪除暫存資料夾。不得用使用者真實資料驗證。

## 收件匣流程

只有一個收件匣：`sources/inbox/`。

1. 使用者要納入知識庫的檔案，原本在其他位置時，Agent **複製**一份到 `inbox/`；絕不搬移、改名或刪除原檔。
2. Agent 執行：

   ```bash
   sources/rag/.venv/bin/python sources/rag/scripts/ingest.py
   ```

3. 腳本只接受 `.md`、`.markdown`、`.txt`、`.pdf`、`.html`、`.htm`，文字檔必須是 UTF-8 編碼。印出的 JSON 報告：
   - `external`：PDF 或 6000 字以上的檔案。原檔已搬到 `sources/external/`，切成約 700 字（相鄰重疊 120 字）的片段存進索引，並建立 `sources/wiki/ext_<檔名>.md` 摘要頁草稿。`reindexed: true` 代表收件匣裡的檔案和 `external/` 的同名檔內容完全相同，只以原路徑重建索引並刪除收件匣副本，不另存新檔、不新增摘要頁。
   - `wiki_pending`：自己的筆記、短文等其他檔案，仍留在 `inbox/`。
   - `unsupported`：不支援的格式（Word、簡報、試算表、圖片、壓縮檔等）與子資料夾，仍留在 `inbox/`。Agent 回報原因；使用者可另存成 PDF、Markdown 或純文字後再放進來，子資料夾裡的檔案要直接放在 `inbox/`。
   - `errors`：讀取或向量化失敗的檔案（例如 Big5 等非 UTF-8 編碼、內容是二進位資料、沒有文字層的掃描 PDF、Ollama 沒有在執行），仍留在 `inbox/`。
4. Agent 打開每份新外部原文，在摘要頁補寫三到五行摘要與關鍵詞，並把摘要頁連進 `wiki/index.md` 或相關頁面。
5. `wiki_pending` 的檔案由 Agent 依既有規則整理：讀書心得交給 `book-notes`，可演化的整理寫進 `wiki/`，一般篇幅的次級資料放進 `references/`。整理完成後才從 `inbox/` 刪除這些副本。
6. 全部處理完後 `inbox/` 應該是空的；只有 `unsupported` 與 `errors` 的檔案留下，並向使用者回報原因。
7. 在 `wiki/log.md` 追加一行匯入紀錄。

使用者明確表示「整份都當外部原文」時，可加上 `--all-external`；門檻可用 `--min-chars` 調整，但預設維持 6000 字。

## 查詢規則

1. 先看 Wiki（含 `ext_*.md` 摘要頁）與 Graphify。
2. 只有下列情況才查本地 RAG：
   - 使用者要原文、原話、出處、精確數字或引用。
   - Wiki 與筆記沒有足夠細節回答。
3. 查詢命令：

   ```bash
   sources/rag/.venv/bin/python sources/rag/scripts/query.py "使用者的問題" -k 5
   ```

   預設混合檢索（向量加中文全文）；Qwen3 向量模型需要的查詢前綴已由 `query.py` 自動加上，Agent 直接傳入問題即可。

   成功時輸出 JSON 陣列。失敗時輸出一個 JSON 物件並以結束碼 1 結束：`{"error": "no_index"}` 代表還沒有任何外部原文（本地 RAG 目前沒有資料，不是安裝壞掉）；`embed_failed` 代表連不上 Ollama；`fts_unavailable` 代表 `--mode fts` 時全文索引無法使用。混合檢索遇到全文索引無法使用時，只用向量結果並在 stderr 印出警告。
4. 回答一律標出檔案與段落標題，例如「`external/定價研究.md`／第三章 訂閱制」。PDF 的段落標題已含頁碼，例如「`external/定價研究.pdf`／第 3 頁｜訂閱制」；沒有標題時是「第 3 頁」。
5. 查不到或結果不相關時直接說查不到，不用相近段落硬湊答案。

## 已知限制

- 索引以 `external/` 底下的相對路徑記錄來源。同名但內容不同的新版本會另存成帶雜湊尾碼的新檔、另外建索引與摘要頁，不會自動取代舊版；要更新舊文件時先問使用者。內容完全相同的檔案只會以原路徑重建索引，不會重複。
- 腳本不提供刪除單一文件；需要時回報限制，不要直接刪除 `lancedb/`。
- 整個索引壞掉時的重建方式：取得使用者同意後刪除 `sources/rag/lancedb/`，把 `sources/external/` 的原文（不含 `README.md`）**複製**回 `inbox/`，再執行 `ingest.py`。每份原文都會以 `reindexed: true` 回報，沿用原本的 `external/` 路徑與已補寫的摘要頁，收件匣副本自動刪除；不會產生帶雜湊尾碼的副本或第二份摘要頁。即使不小心把 `README.md` 一起複製，也只會列在 `unsupported`，由 Agent 刪除該副本。
- 掃描成圖片、沒有文字層的 PDF 讀不到內容，會列在 `errors`（讀不到任何文字）或切段數很少；回報使用者，不宣稱已匯入完整內容。

## 疑難排解

| 症狀 | 可能原因 | Agent 處理方式 |
|---|---|---|
| `ingest.py` 的 `errors` 出現連線錯誤 | Ollama 沒有在執行 | 執行 `brew services start ollama` 後重跑；檔案仍在 `inbox/`，不會重複匯入 |
| 自訂了 `OLLAMA_HOST` 仍連不上 | 位址指向其他電腦或錯誤的連接埠 | 腳本接受 Ollama 官方格式（`127.0.0.1:11434`、`0.0.0.0`，可不加 `http://`）；確認位址後重跑 |
| `errors` 出現「不是 UTF-8 編碼」 | 檔案是 Big5 等舊編碼 | 告訴使用者用文字編輯器另存成 UTF-8，或在使用者同意後由 Agent 轉存一份 UTF-8 副本到 `inbox/`；原檔不動 |
| 找不到 `qwen3-embedding:4b` | 模型未下載或被刪除 | 說明容量後重新 `ollama pull qwen3-embedding:4b` |
| `ModuleNotFoundError` | `.venv` 不完整 | 重新執行上方 `uv pip install` |
| 電腦變慢 | 匯入大量文件時模型常駐 | 等待匯入完成；閒置約 2 分鐘後自動卸載 |

## 移除

- 移除本地 RAG 分成幾層，每一層都要分開取得同意：停止服務（`brew services stop ollama`）、移除模型（`ollama rm qwen3-embedding:4b`）、移除 Ollama（`brew uninstall ollama`）、刪除 `sources/rag/.venv/` 與 `sources/rag/lancedb/`。
- `sources/external/` 與 `wiki/ext_*.md` 是使用者的資料，不屬於解除安裝範圍。
- 移除自有技能不會移除本地 RAG，也不會刪除任何工作區資料。

## 從 NotebookLM 升級

先前版本使用 NotebookLM 與 `notebooklm-py`。升級流程見 `docs/installation.md` 的「從 NotebookLM 版本升級」：不刪除使用者的 NotebookLM 資料，不強制移除 `notebooklm-py`，舊的 `sources/references/notebooks/` 保留為歷史紀錄。

## 參考紀錄：維護者單機實測

> 這一節只是參考紀錄，不是產品規格或效能保證。數字來自維護者的一臺 Mac mini 與維護者自備、未隨技能包發行的繁體中文測試文件，其他電腦、文件類型與模型版本的結果都可能不同。Agent 引用時必須說明「這是維護者單機的參考值」，不得把它當成使用者電腦會達到的速度，也不得把測試文件內容當成任何預設資料。

- 文件量：33 份繁體中文文件、約 18.1 萬字，切成 421 段。
- 匯入：約 293 秒（約每萬字 16 秒）；據此估算時應說明誤差可能很大。
- 查詢：每次約 0.9 秒。
- 檢索品質：10 題測試問題用混合檢索，10 題的第一名結果都命中正確段落。
