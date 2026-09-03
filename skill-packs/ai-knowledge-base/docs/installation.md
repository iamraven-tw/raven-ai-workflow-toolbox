# AI Agent 安裝與生命週期

## 狀態邊界

這個候選版能在本機管理五個自有技能與安全初始化工作區。第三方套件安裝、外部登入、遠端 Notebook 存取、另一臺電腦實測與正式支援都是獨立狀態，不能由本機測試結果推論。

## 1. 唯讀檢查

Agent 先確認：

- 作業系統、Python 版本與 `uv` 是否可用。
- manifest 所列五個技能與模板來源是否完整。
- 使用者選定的 Agent、registration、技能目錄與狀態目錄。
- 目標位置是否有同名技能、symlink、人工修改或不完整內容。
- 工作區模板會新增、保留或發生類型衝突的項目。
- `graphify`、`notebooklm` 是否存在及其實際版本，但不在此階段安裝或登入。

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
- provider 的套件名稱、固定版本、最新觀察版本、未自動升級理由與非官方介面風險。
- Notebook 登入與遠端驗證仍需使用者互動。

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
- 初始化狀態只保存版本、路徑與相對檔名，不保存檔案內容、Notebook ID 或憑證。
- 移除技能不會反向刪除工作區，模板更新也不會重寫使用者修改。

## 5. 第三方 provider

manifest 目前保留以下固定版本：

```bash
uv tool install "graphifyy==0.9.35"
uv tool install "notebooklm-py[browser]==0.8.0"
```

這些命令只有在使用者另行同意下載與改變共用環境後才可執行。若缺少 `uv`，先說明影響並取得同意；不得靜默改用全域 `pip`。

專案範圍技能可依宿主選擇：

```bash
graphify install --project --platform agents
graphify install --project --platform codex
notebooklm skill install --scope project --target agents
notebooklm skill install --scope project --target claude
```

先使用上游的預覽或狀態命令檢查既有內容，不得加上強制覆蓋選項。Antigravity 的 Graphify 專屬命令與一般 Agent Skills 命令不同；使用前依固定版本說明核對，不把 Codex 命令套用到所有宿主。

## 6. Provider 更新、回復與移除

- 不追蹤未固定的 latest 版本，也不因 PyPI 出現新版就直接更新。
- 先在隔離環境驗證新的固定版本、安裝產物、上游技能與三種 Agent 發現，再改 manifest。
- 更新前記錄原固定版本、套件安裝方式與專案範圍技能狀態；失敗時重新安裝原固定規格並重新驗證。
- Graphify 技能可使用上游 `graphify uninstall` 或相應平台命令移除；預設不得加上會刪除圖譜輸出的 `--purge`。
- Notebook 上游技能使用 `notebooklm skill uninstall --scope project --target <target>`；套件、技能、登入狀態與遠端 Notebook 必須分開處理。
- 移除套件或登入狀態會改變共用環境，仍需另行取得同意。遠端 Notebook、來源與分享權限不屬於本機解除安裝範圍。

## 7. 登入與分層驗證

Notebook 登入必須停下讓使用者本人操作。登入後的遠端驗證命令是：

```bash
notebooklm auth check --test --json
notebooklm list --json
```

`auth check --json` 只證明本機狀態可解析；只有加上 `--test` 且回傳 `status: ok`、`checks.token_fetch: true`，才證明當時能向遠端取得權杖。`notebooklm status` 是目前 Notebook 選擇狀態，不是登入驗證。

最後必須分開回報：

1. 靜態結構與文件檢查。
2. 本機五個技能的安裝與 Agent 發現。
3. 第三方套件是否實際安裝、版本是否符合。
4. provider 專案技能是否被各用戶端發現。
5. 使用者是否完成外部登入。
6. 遠端 Notebook 或服務是否實際存取成功。
7. 是否已在另一臺電腦完成實機驗收。
8. 是否已由維護者宣告正式公開支援。

前一項通過不能代替後一項。Agent 端全部門檻通過時，最高只能標示為「可供外部驗收」。
