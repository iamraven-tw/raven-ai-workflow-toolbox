# AI Agent 安裝流程

## 目標

讓使用者只需提供 `My Real Second Brain` repository 連結與「請幫我安裝」，再由 AI Agent 安裝五個自有技能並準備預設後端。上游程式與技能不提交到本倉庫，第一次安裝仍需要網路。

## 1. 唯讀檢查

Agent 先確認：

- 作業系統與 CPU 架構。
- Python 是否符合上游最低需求。
- `uv` 是否存在。
- `install.manifest.toml` 所列五個技能來源是否完整。
- 使用者指定的第二大腦工作區是否存在，以及 `template/` 會新增或衝突哪些檔案。
- 目標技能位置是否已有同名但內容不同的技能。
- `graphify`、`notebooklm` 是否已安裝，以及版本是否符合 manifest。
- 專案範圍是否已有同名上游技能，內容是否會被覆蓋。

此階段不得安裝、升級、登入或改寫檔案。

## 2. 取得安裝同意

Agent 應列出：

- 即將下載的套件名稱與固定版本。
- 安裝位置與技能寫入位置。
- 第二大腦工作區位置，以及 `template/` 將新增、保留或發生衝突的項目。
- Notebook 登入需要使用者互動。
- `notebooklm-py` 使用非官方介面的風險。

使用者同意後才能繼續。

## 3. 安裝五個自有技能

依 `install.manifest.toml` 的 `[[skills]]` 逐一安裝。預設範圍為 `user`，讓技能能在之後的工作中被 Agent 發現：

- `skills/my-real-second-brain-setup`
- `skills/solopreneur-profile`
- `skills/book-notes`
- `skills/knowledge-source-retrieval`
- `skills/socratic-dialogue`

如果目標已有同名技能，先比較內容並回報；不得靜默覆蓋。使用者可以明確改選專案範圍，但 Agent 不得自行更改預設範圍。

不同宿主的預設使用者範圍位置如下。安裝前仍要檢查目前版本的官方規格與既有內容：

| 宿主 | 使用者範圍技能位置 | 專案規則入口 |
|---|---|---|
| ChatGPT／Codex | `~/.agents/skills/` | `AGENTS.md` |
| Claude Code | `~/.claude/skills/` | `CLAUDE.md`，由它匯入 `AGENTS.md` |
| Google Antigravity | `~/.gemini/config/skills/` | `AGENTS.md` |

公開範本同時提供 `AGENTS.md` 與 `CLAUDE.md`，但規則內容只維護在 `AGENTS.md`；這能避免三個宿主因重複規則逐漸產生差異。

已驗證版本、測試範圍與已知限制請見 `client-compatibility.md`。版本更新後必須重新實測，不得只因檔案位置符合文件就宣稱相容。

## 4. 初始化第二大腦工作區

1. 明確取得使用者指定的工作區；不得把 repository 本身或目前不明的目錄當成預設目的地。
2. 依 manifest 的 `[workspace]` 將 `template/` 合併到工作區。
3. 只建立缺少的目錄與檔案；同名且內容不同時停止並顯示差異，不得覆蓋。
4. 既有工作區可以保留自己的專案指令與案例專用目錄，但 `sources/` 的核心目錄與 schema 必須相容。
5. 不得把公開範本反向當成清空、重建或刪除使用者資料的授權。

## 5. 安裝固定版本的 provider

目前 manifest 所列版本的等價命令如下；實際執行時仍須從 `install.manifest.toml` 讀值：

```bash
uv tool install "graphifyy==0.9.35"
uv tool install "notebooklm-py[browser]==0.8.0"
```

若缺少 `uv`，先向使用者說明並取得安裝 `uv` 的同意。不得靜默改用系統 Python 的全域 `pip`。

## 6. 註冊 provider 的專案範圍技能

Agent 應依目前宿主選擇上游支援的專案範圍安裝方式。例如：

```bash
graphify install --project --platform codex
notebooklm skill install --scope project --target agents
```

若宿主不是 Codex，先讀取上游說明並使用相符的平台參數。產生的上游技能目錄已列入 `.gitignore`，不應提交成為本專案原始碼。

## 7. 登入與驗證

```bash
graphify --version
notebooklm --version
notebooklm auth check --test --json
```

尚未登入時，Agent 可以啟動 `notebooklm login`，但必須停下讓使用者本人完成登入。驗證時必須同時確認狀態成功與實際遠端驗證成功，不能只檢查憑證檔案存在。

驗證順序由 manifest 的 `[[verification_steps]]` 決定：先確認五個自有技能與工作區骨架，再確認 provider 版本、provider 技能與 Notebook 遠端存取。

## 8. 本機狀態

全部驗證成功後，可在被 `.gitignore` 排除的 `.second-brain/` 保存：

- 已安裝的 provider ID 與版本。
- 驗證時間。
- 技能安裝目標。
- 不含秘密資訊的健康狀態。

不得保存 Cookie、Token、登入狀態內容、Notebook 私人資料或上游來源全文。

## 更新與修復

- 不因上游有新版就自動升級。
- 先由維護者更新 `install.manifest.toml`，再測試安裝與相容性。
- Graphify manifest、環境或變更數量異常時，不自動重建整個知識庫。
- 修復不得以刪除使用者資料、Notebook 或既有索引作為預設手段。
