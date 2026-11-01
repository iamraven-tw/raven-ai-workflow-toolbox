# AI Agent 安裝與生命週期

## 狀態邊界

這個候選版能在本機管理五個自有技能與安全初始化工作區。第三方套件安裝、本地 RAG（Ollama、向量模型與 Python 環境）、另一臺電腦實測與正式支援都是獨立狀態，不能由本機測試結果推論。

## 1. 唯讀檢查

Agent 先確認：

- 作業系統、Python 版本與 `uv` 是否可用。
- manifest 所列五個技能與模板來源是否完整。
- 使用者選定的 Agent、registration、技能目錄與狀態目錄。
- 目標位置是否有同名技能、symlink、人工修改或不完整內容。
- 工作區模板會新增、保留或發生類型衝突的項目。
- `graphify`、`brew`、`ollama` 是否存在及其實際版本、`qwen3-embedding:4b` 是否已下載、電腦記憶體大小，但不在此階段安裝任何東西。
- 工作區是否已有舊版的 `sources/references/notebooks/`；有的話代表是從 NotebookLM 版本升級，改走第 8 節。

使用者範圍與工作區範圍如下；執行時仍須依 manifest 選 registration：

| 用戶端 | 使用者範圍 | 工作區範圍 |
|---|---|---|
| Codex | `~/.agents/skills/` | `<workspace>/.agents/skills/` |
| Claude Code | `~/.claude/skills/` | `<workspace>/.claude/skills/` |
| Antigravity Desktop | `~/.gemini/config/skills/` | `<workspace>/.agents/skills/` |

Antigravity CLI 與 Desktop 是不同產品。manifest 另外記錄 CLI 全域位置 `~/.gemini/antigravity-cli/skills/`（`antigravity_cli_user`），本機管理器可驗證這個路徑契約；但本次沒有完成 CLI 登入與 `/skills` 實際發現，因此不得把 Desktop 或路徑測試推論成 CLI 已通過。

## 2. 預覽並取得同意

Agent 應先說明：

- 五個自有技能會寫到哪裡。
- 狀態、更新快照與移除隔離區會放在哪裡。
- 工作區模板將新增哪些項目、保留哪些既有檔案，以及是否有類型衝突。
- Graphify 的套件名稱、維護者測試版本與最新觀察版本。
- 本地 RAG 會下載的 Ollama、`qwen3-embedding:4b` 模型（約 2.5 GB）與 Python 套件（約 500 MB），全部免費；匯入或查詢時約佔 3.1 GB 記憶體，閒置約 2 分鐘後自動釋放。
- 整個流程由 Agent 執行，使用者不需要輸入指令，也不需要登入任何帳號。

沒有同意時，只能做 `status` 或 `workspace-status` 等唯讀檢查。

## 3. 管理五個自有技能

管理器使用公開佔位符；Agent 要把它們換成使用者已核准的精確路徑：

```bash
python3 scripts/manage_install.py status \
  --registration <registration> \
  --client-root <agent-skill-directory> \
  --state-root <local-state-directory>

python3 scripts/manage_install.py install \
  --registration <registration> \
  --client-root <agent-skill-directory> \
  --state-root <local-state-directory>
```

生命週期行為：

| 操作 | 行為 | 安全停止條件 |
|---|---|---|
| `install` | 全新安裝；相同內容可建立狀態或重跑為 no-op | 未知、不完整或不同內容；版本不同時要求改用 `update` |
| `update` | 驗證現有雜湊、建立完整快照，再交易式替換 | 人工修改、缺檔、來源不完整或快照失敗 |
| `rollback` | 回復最近一次更新前的完整快照 | 沒有快照、現況已被修改或快照損壞 |
| `remove` | 把五個技能移到可復原隔離區 | 現況已被修改；不碰工作區與 provider |
| `status` | 唯讀比對狀態與實際雜湊 | 找不到狀態時只回報未受管理 |

更新、回復與移除使用相同三個路徑參數。例如明確更新：

```bash
python3 scripts/manage_install.py update \
  --registration <registration> \
  --client-root <agent-skill-directory> \
  --state-root <local-state-directory>
```

管理器以結束代碼 `2` 和 JSON 錯誤安全停止。不得把錯誤後的部分結果當成成功，也不得為了重試而刪除未知內容。

## 4. 安全初始化工作區

先預覽：

```bash
python3 scripts/manage_install.py workspace-status \
  --workspace-root <user-selected-workspace>
```

取得使用者確認後才寫入：

```bash
python3 scripts/manage_install.py init-workspace \
  --workspace-root <user-selected-workspace> \
  --state-root <local-state-directory>
```

固定規則：

- 只能使用使用者明確選定、且位於技能包外的工作區。
- 缺少的目錄與檔案才會建立。
- 既有一般檔案不論內容相同或不同都不覆蓋；不同內容會列在 `preserved_existing`。
- 檔案與目錄類型衝突、symlink 或特殊檔案會在任何寫入前停止。
- 重複執行沒有新缺口時回傳 no-op。
- 初始化狀態只保存版本、路徑與相對檔名，不保存檔案內容或憑證。
- 移除技能不會反向刪除工作區，模板更新也不會重寫使用者修改。

## 5. 第三方 provider：Graphify

Graphify 是 C 級外部來源（ADR 0006）：不是工具包的一部分，Agent 先依根專案 `docs/dependency-policy.md` 宣讀標準外部來源提醒並取得同意，再以 `uv tool install` 安裝**當下最新版**；若缺少 `uv`，依根 INSTALL.md 的環境準備先裝 uv，不得靜默改用全域 `pip`。

```bash
uv tool install graphifyy
```

安裝後執行 manifest 的 `verify_commands`（`graphify --version`）確認可用，並把實際版本記進安裝狀態。manifest 的 `tested_version` 只是維護者最後測試過的版本紀錄，不是安裝目標；若最新版讓驗證失敗，回報使用者並停止，不自動改裝舊版。

專案範圍技能可依宿主選擇：

```bash
graphify install --project --platform agents
graphify install --project --platform codex
```

先使用上游的預覽或狀態命令檢查既有內容，不得加上強制覆蓋選項。Antigravity 的 Graphify 專屬命令與一般 Agent Skills 命令不同；使用前依固定版本說明核對，不把 Codex 命令套用到所有宿主。

## 6. 本地 RAG

本地 RAG 取代先前的 NotebookLM。完整規格、收件匣流程、查詢規則與疑難排解見 [`integrations/local-rag.md`](integrations/local-rag.md)。

Agent 宣讀標準外部來源提醒、說明容量與記憶體需求並取得同意後，在使用者工作區根目錄依序執行；使用者不需要輸入任何指令：

```bash
brew install ollama
brew services start ollama
ollama pull qwen3-embedding:4b
uv venv sources/rag/.venv --python 3.12
uv pip install --python sources/rag/.venv/bin/python lancedb pyarrow jieba pypdf requests
```

- 目標是 16 GB 記憶體以上的 Mac；記憶體較少時先說明可能變慢，由使用者決定是否繼續。Windows 與 Linux 尚未驗證，先回報再詢問。
- `brew services start ollama` 讓 Ollama 開機自動啟動。
- 已安裝的 Ollama、已下載的模型與已存在且可匯入套件的 `.venv` 直接沿用，不重裝。
- 腳本 `sources/rag/scripts/` 與 `sources/inbox/`、`sources/external/` 由第 4 節的工作區初始化建立；既有工作區缺少時同樣只補缺少項目。

## 7. Provider 更新、回復與移除

- provider 依 ADR 0006 安裝最新版；`uv tool upgrade`、`brew upgrade ollama` 或重新 `ollama pull` 由使用者要求時才執行，執行前同樣先提醒。
- 維護者定期在隔離環境驗證最新版的安裝產物、上游技能與三種 Agent 發現，更新 manifest 的 `tested_version`。
- 更新前記錄目前實際版本與專案範圍技能狀態；升級後驗證失敗時回報使用者，由使用者決定是否以 `uv tool install graphifyy==<舊版>` 退回。
- Graphify 技能可使用上游 `graphify uninstall` 或相應平台命令移除；預設不得加上會刪除圖譜輸出的 `--purge`。
- 本地 RAG 的移除分層與注意事項見 `integrations/local-rag.md`；`sources/external/` 與 `wiki/ext_*.md` 是使用者資料，不屬於解除安裝範圍。
- 移除套件會改變共用環境，仍需另行取得同意。

## 8. 從 NotebookLM 版本升級

適用已安裝 0.1.x、曾使用 NotebookLM 與 `notebooklm-py` 的使用者。Agent 照下列順序處理，使用者不需要輸入指令：

1. 先用白話告訴使用者：「新版不再使用 NotebookLM，改用在你電腦上執行的本地搜尋（本地 RAG）。你在 NotebookLM 裡的筆記本和資料**都不會被刪除**，之後仍可以照常自己打開使用。」
2. 以 `scripts/manage_install.py update` 更新五個自有技能，再用 `workspace-status` 與 `init-workspace` 補上新範本缺少的項目（`sources/inbox/`、`sources/external/`、`sources/rag/scripts/`、`sources/.gitignore` 等）；既有檔案一律保留。
3. 既有的 `sources/.graphifyignore` 會被列為保留檔案，不會自動更新。Agent 比對新範本，預覽變更並取得同意後才修改：把舊的 `wiki/` 這一行**取代**成 `wiki/*` 與 `!wiki/ext_*.md` 兩行（只附加新行而保留 `wiki/` 時，摘要頁仍會被排除），再補上缺少的 `inbox/`、`external/`、`rag/`。
4. 依第 6 節安裝 Ollama、設定 `brew services` 開機自動啟動、下載 `qwen3-embedding:4b`、建立 `sources/rag/.venv`。
5. 舊的 `sources/references/notebooks/` 保留為歷史紀錄，不刪除、不再同步。
6. `notebooklm-py` 與它在專案範圍安裝的技能可以留著，不強制移除；使用者主動要求時才另外取得同意後移除。不讀取、輸出或刪除它的登入狀態檔。
7. 詢問使用者是否要把 NotebookLM 裡的原始來源搬過來（可選）。同意的話，協助把來源檔案下載或匯出到 `sources/inbox/`（例如使用者自己從 NotebookLM 或 Google 雲端硬碟下載原檔，或在 `notebooklm-py` 仍可用、使用者同意時由 Agent 協助下載），再走一般收件匣流程。不同意就跳過，不影響升級完成。
8. 依第 9 節分層回報。

## 9. 分層驗證

最後必須分開回報：

1. 靜態結構與文件檢查。
2. 本機五個技能的安裝與 Agent 發現。
3. Graphify 套件是否實際安裝、版本是否記錄。
4. Graphify 專案技能是否被各用戶端發現。
5. 本地 RAG：Ollama 服務在執行、`qwen3-embedding:4b` 已列出、`.venv` 可匯入五個套件，以及用暫存資料夾與虛構文件完成一次匯入與查詢。
6. 是否已在另一臺電腦完成實機驗收。
7. 是否已由維護者宣告正式公開支援。

前一項通過不能代替後一項。Agent 端全部門檻通過時，最高只能標示為「可供外部驗收」。
