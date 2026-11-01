---
name: my-real-second-brain-setup
description: "安裝、更新、回復、移除、修復或驗證 My Real Second Brain。當使用者提供 repository 連結並要求安裝，或要求設定本專案時，引導 AI Agent 依 install.manifest.toml 管理全部必要自有技能、安全初始化使用者指定的工作區；取得同意後才安裝可替換後端（Graphify 與本地 RAG：Ollama、向量模型與 Python 環境），全部由 Agent 執行、使用者不需輸入指令；也處理從 NotebookLM 版本升級，並分層回報驗證結果。"
---

# My Real Second Brain 安裝

## 啟動條件

使用者要求安裝、設定、更新、修復或驗證 `My Real Second Brain` 及其預設後端時使用；也包括從使用 NotebookLM 的舊版升級。

## 必讀文件

先定位含有 `install.manifest.toml` 的本 repository 根目錄，再完整讀取：

1. `AGENTS.md`
2. `INSTALL.md`
3. `install.manifest.toml`
4. `docs/installation.md`
5. `docs/providers.md`
6. `docs/integrations/local-rag.md`

若找不到 repository 根目錄，停止並請使用者重新提供本機 checkout 或 repository 連結；不得假設這些檔案位於目前工作目錄。

## 工作流程

這是多階段技能。採取任何安裝行動前，必須先向使用者展示 `INSTALL.md` 的 Mermaid 流程，標出外部下載、技能寫入與停止位置。所有命令都由 Agent 執行；使用者只需要回答同意與否，不需要自己輸入指令。流程圖不代表使用者已核准後續操作。

1. 唯讀檢查作業系統、記憶體、Python、`uv`、Homebrew、Ollama 與已下載模型、既有 provider、專案技能與使用者指定的工作區。工作區有舊的 `sources/references/notebooks/` 時，改走下方「從 NotebookLM 版本升級」。
2. 解析 `install.manifest.toml`，確認全部必要技能、工作區範本、來源路徑、安裝範圍、provider 版本與排序皆有效。
3. 說明下載內容、容量、授權、記憶體需求（本地 RAG 使用時約 3.1 GB，閒置約 2 分鐘後自動釋放；建議 16 GB 記憶體以上的 Mac）、技能位置、工作區範本差異與覆蓋風險。全部免費，不需要任何帳號。
4. 取得使用者同意後，依 manifest 順序安裝全部自有技能；預設使用者範圍，不靜默覆蓋同名技能。
5. 先用 `scripts/manage_install.py workspace-status` 顯示模板差異；取得同意後再初始化。只建立缺少項目，既有一般檔案即使內容不同也保留，只有檔案與目錄類型衝突時才停止。
6. 宣讀標準外部來源提醒後，從正式套件來源安裝 Graphify，並在同一個使用者工作區以上游支援的專案範圍方式註冊 Graphify 技能；不複製上游 repository。
7. 依 `docs/integrations/local-rag.md` 安裝本地 RAG：`brew install ollama`、`brew services start ollama`（開機自動啟動）、`ollama pull qwen3-embedding:4b`、在 `sources/rag/.venv` 建立 Python 環境並安裝 lancedb、pyarrow、jieba、pypdf、requests。已存在且可用的元件直接沿用。
8. 依 manifest 的驗證順序檢查自有技能、工作區骨架、Graphify 版本與技能，以及本地 RAG（服務、模型、套件，並用暫存資料夾與虛構文件完成一次匯入與查詢）。
9. 分別回報自有技能、工作區、Graphify 套件、Graphify 技能與本地 RAG；不得把其中一層通過寫成全部完成。

## 從 NotebookLM 版本升級

舊版（0.1.x）使用 NotebookLM 與 `notebooklm-py`。偵測到舊版安裝或 `sources/references/notebooks/` 時：

1. 先用白話告訴使用者：新版不再使用 NotebookLM，改用在自己電腦上執行的本地 RAG；使用者在 NotebookLM 裡的筆記本與資料**不會被刪除**。
2. 以 `update` 更新五個自有技能，再用 `workspace-status` 與 `init-workspace` 補上 `sources/inbox/`、`sources/external/`、`sources/rag/scripts/` 等缺少項目；既有檔案一律保留。
3. 既有 `sources/.graphifyignore` 不會自動更新；預覽變更並取得同意後才修改：把舊的 `wiki/` 這一行**取代**成 `wiki/*` 與 `!wiki/ext_*.md` 兩行（只附加新行而保留 `wiki/` 時，摘要頁仍會被排除），再補上缺少的 `inbox/`、`external/`、`rag/`。
4. 依工作流程第 7 步安裝 Ollama、設定 `brew services`、下載模型並建立 `.venv`。
5. 舊的 `sources/references/notebooks/` 保留為歷史紀錄，不刪除、不再同步。
6. `notebooklm-py` 與其專案範圍技能可以留著，不強制移除；使用者主動要求時才另外取得同意後移除。不讀取、輸出或刪除登入狀態檔。
7. 詢問使用者是否要把 NotebookLM 的原始來源下載到 `sources/inbox/`（可選）；同意才協助，之後走一般收件匣流程。
8. 分層回報升級結果。

## 自有技能管理器

- `install`：安裝五個自有技能；相同內容重跑為 no-op，不同版本要求明確改用 `update`。
- `update`：驗證現有雜湊、建立本機快照，再以可回復交易更新。
- `rollback`：回復最近一次更新前快照。
- `remove`：只把受管理技能移到隔離區；不刪除第二大腦工作區或 provider。
- `status`：唯讀比對安裝狀態與實際雜湊。
- `workspace-status` 與 `init-workspace`：分開預覽與寫入，確保模板只補上缺少項目。

使用前先從 manifest 選定 registration，明確提供目標技能目錄與位於技能掃描目錄外的狀態目錄。狀態只保存版本、路徑、雜湊、快照與隔離位置，不保存憑證或知識內容。

## 永久邊界

- 不將 Graphify 或本地 RAG 視為不可替換的系統核心。
- 不把上游原始碼或產生的技能提交到本專案。
- 不略過 manifest 中標示 `required = true` 的任何自有技能。
- 不自行猜測工作區，不覆蓋既有專案指令、筆記、索引或資料。
- 不讀取、輸出、保存或提交 Cookie、Token、登入狀態內容與私人來源。
- 不靜默安裝 `uv`、Homebrew、Ollama 或模型，不改用全域 `pip`，不覆蓋不同內容的技能。
- 不在驗證失敗時自動刪除環境、圖譜、索引、來源、`sources/external/` 原文或使用者的 NotebookLM 資料。
- provider 替換只改 adapter 與設定，不得靜默改寫使用者核心知識。
- 移除自有技能不等於移除 provider，也不等於刪除工作區；每一層都必須分開取得授權與驗證。
