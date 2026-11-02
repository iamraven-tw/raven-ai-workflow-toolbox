# 第三方專案與概念來源

本文件記錄 `My Real Second Brain` 使用、整合或參考的外部專案。除非另有明確說明，本專案不會把這些專案的原始程式碼直接收進倉庫。

## Graphify

- 專案：https://github.com/Graphify-Labs/graphify
- 作者／維護者：Graphify Labs、Safi Shamsi 與貢獻者
- 本專案中的用途：本地知識圖譜、跨文件關聯、群聚分析、查詢與互動式 HTML 視覺化
- 整合方式：可替換的預設後端；使用者同意後才由 AI Agent 依 `install.manifest.toml` 安裝固定版本；上游通用技能不複製到本倉庫
- 安裝方式：C 級外部來源（ADR 0006），告知後以 `uv tool install graphifyy` 安裝 PyPI 當下最新版
- 維護者最後測試版本：`graphifyy==0.9.35`；[PyPI 版本頁](https://pypi.org/project/graphifyy/0.9.35/)；[上游發行頁](https://github.com/Graphify-Labs/graphify/releases/tag/v0.9.35)
- 授權：目前產品主體採 Apache License 2.0；NOTICE 說明部分重新授權前的內容仍保留 MIT 條款
- 固定版本 NOTICE：https://github.com/Graphify-Labs/graphify/blob/v0.9.35/NOTICE
- 固定版本 LICENSE：https://github.com/Graphify-Labs/graphify/blob/v0.9.35/LICENSE
- 固定版本 MIT 歷史條款：https://github.com/Graphify-Labs/graphify/blob/v0.9.35/LICENSE-MIT

若未來把 Graphify 程式碼或衍生內容納入本倉庫，必須保留適用的 LICENSE、NOTICE、著作權與修改聲明。

## 本地 RAG 外部元件

本地 RAG 的匯入與查詢腳本（`template/sources/rag/scripts/`）是本專案自有程式，採 Apache License 2.0。下列外部元件都是 C 級外部來源（ADR 0006）：不封存進本倉庫，Agent 宣讀標準外部來源提醒並取得同意後，安裝當下最新版。

| 元件 | 用途 | 來源 | 授權 |
|---|---|---|---|
| Ollama | 在本機執行向量模型；以 Homebrew 安裝、`brew services` 開機自動啟動 | https://github.com/ollama/ollama 、https://formulae.brew.sh/formula/ollama | MIT |
| Qwen3-Embedding-4B（Ollama 名稱 `qwen3-embedding:4b`） | 把文字轉成向量；約 2.5 GB 模型權重，不得提交 | https://huggingface.co/Qwen/Qwen3-Embedding-4B 、https://ollama.com/library/qwen3-embedding | Apache-2.0 |
| LanceDB（`lancedb`） | 本機向量與全文索引 | https://github.com/lancedb/lancedb | Apache-2.0 |
| Apache Arrow（`pyarrow`） | LanceDB 的資料格式 | https://github.com/apache/arrow | Apache-2.0 |
| jieba | 中文斷詞，讓全文檢索能找中文詞彙 | https://github.com/fxsjy/jieba | MIT |
| pypdf | 讀取 PDF 文字 | https://github.com/py-pdf/pypdf | BSD-3-Clause |
| Requests（`requests`） | 呼叫本機 Ollama API | https://github.com/psf/requests | Apache-2.0 |

Python 套件安裝在使用者工作區的 `sources/rag/.venv/`，不碰系統 Python。安裝後所有處理都在本機進行，不上傳使用者內容。

## notebooklm-py（已停用）

2026-10-31 起本專案不再安裝或使用 [notebooklm-py](https://github.com/teng-lin/notebooklm-py)（MIT License，非官方社群專案）。先前已安裝的使用者可以保留，本專案不強制移除，也不刪除使用者的 NotebookLM 資料。

## LLM Wiki

- 原始筆記：https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- 作者：Andrej Karpathy
- 本專案中的用途：原始資料、持續演化 Wiki 與規則層的架構概念；以及 ingest、query、lint、index、log 等操作觀念
- 整合方式：概念啟發；本專案使用自己的文字、目錄與技能重新實作

原始 Gist 未標示標準開源授權。本專案不重製或重新授權該文件；README 與文件只做必要的來源標示及概念說明。

## Capacities

- 產品：https://capacities.io/
- 文件：https://docs.capacities.io/
- 維護者：Capacities Labs GmbH
- 本專案中的用途：物件、類型、屬性與關聯式知識整理的概念參考
- 整合方式：概念啟發

Capacities 是專有產品。本專案不包含其程式碼、介面、圖片、Logo、商標、範本或文件文字，也不代表與 Capacities Labs 有合作關係。
