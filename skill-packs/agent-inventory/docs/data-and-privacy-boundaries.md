# 資料與隱私邊界

## 安裝階段

| 動作 | 是否連網 | 讀什麼 | 寫什麼 |
|---|---|---|---|
| `status` | 否 | 安裝狀態檔、目標技能目錄、來源設定及版本 | 無 |
| clone 上游 | **是** | 無 | 狀態目錄下的 `source/v0.2.1/` |
| `install`、`update` | 否 | 上游 clone、manifest | 六個技能目錄、狀態檔、備份快照、唯一來源設定 |
| `rollback`、`remove` | 否 | 狀態檔、備份快照 | 技能目錄、隔離區、狀態檔 |
| 寫入 `repoRoot`（安裝器，同一次安裝確認） | 否 | `~/.config/agent-inventory/config.json` | 同一檔案，只新增或更新 `repoRoot` 一個鍵 |

安裝器不讀取使用者的規則內容，也不執行掃描。

## 盤點階段（上游執行）

| 項目 | 內容 |
|---|---|
| 讀取範圍 | 上游轉接器宣告的規則與技能路徑，加上使用者在 `inventory-setup` 選定的專案根目錄 |
| 使用紀錄 | 讀 Claude Code 的 history 與逐字稿、Codex 的 sessions、Hermes 的 state.db，用於統計呼叫次數與上次使用時間 |
| 寫入範圍 | 只寫上游 clone 的 `data/`（含 `summaries/`、`flows/`、`user-summaries.json`、`user-flows.json`），以及 `~/.config/agent-inventory/config.json` |
| 摘要內容 | 由 Agent 讀規則全文後重寫；上游摘要規格明確禁止寫入密碼、Token、帳號等敏感字串 |
| 流程圖 | `inventory-flow` 由 Agent 讀技能內容後畫 Mermaid 圖並標出人類介入點；純參考型技能標為無流程 |
| 網路 | 掃描與摘要不連網 |
| 網站 | 只綁定 `127.0.0.1`，預設連接埠 8765 |
| 對外請求 | 只有網頁編輯器從 `esm.sh` 載入 CodeMirror 6；離線時退回內建純文字編輯器 |
| 上傳 | 無 |

## Agent 讀到規則全文這件事

`inventory-summarize` 會讓 Agent 讀取每一條規則與技能的內容才能寫摘要。這代表：

- 若使用者的規則檔裡本來就寫了機密資訊，Agent 會讀到。安裝前應提醒使用者這一點。
- 摘要只寫進本機檔案，不會離開這台電腦；但 Agent 本身的對話紀錄可能保留讀到的片段，這取決於使用者的用戶端設定，不在本套件控制範圍。
- 上游技能已要求 Agent 不要把讀到的檔案內容貼回對話。

## 具破壞性的能力

上游網站提供三個會影響實體檔案的端點，全部由使用者在網站上主動觸發，安裝器不會代為執行：

| 端點 | 行為 | 上游的保護 |
|---|---|---|
| `/api/delete` | 把規則或技能移到系統垃圾桶 | 先列出實際受影響路徑與工具；專案與跨工具共用的項目要輸入名稱才能執行；symlink 只移除連結本身 |
| `/api/save` | 直接寫回實體檔案 | 存檔前備份到 `data/backups/`（每檔 10 版）；載入時記住內容雜湊，期間被別的程式改過就拒絕存檔 |
| `/api/open` | 在本機啟動文字編輯器、Finder、VS Code 或 Cursor | 只接受 inventory 中列出的檔案 |

另有 `/api/summary` 與 `/api/flow` 讓使用者在網站上手改摘要與流程圖，只寫進 `data/user-summaries.json` 與 `data/user-flows.json`，不碰實體規則或技能檔；上游 `merge.py` 不會覆蓋手改內容。

## 移除時保留什麼

`remove` 只把六個受管理技能移到可回復隔離區。以下不會被刪除，需要使用者自行處理：

- 上游 clone 與其 `data/`（掃描結果與摘要）。
- `~/.config/agent-inventory/config.json`（含安裝時寫入的 `repoRoot`）。
- 使用者自己的任何規則與技能。
