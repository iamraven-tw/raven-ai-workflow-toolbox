# ADR 0004：agent-inventory 作為固定版本外部依賴

- 狀態：Accepted for local candidate
- 日期：2026-09-06
- 範圍：AI Agent 規則與技能盤點技能包

## 背景

`iamraven-tw/agent-inventory` 已是獨立的公開 repository（MIT），內含六個技能、六個工具轉接器、掃描與合併腳本，以及一個本機網站。它解決的問題是：使用者累積了大量分散在不同 AI agent 的規則與技能，卻沒有一個地方能看到全貌。

Toolbox 要補的不是重寫一份盤點程式，而是把它納入既有的安裝、驗證、隱私與授權框架，讓它跟其他五個技能包用同一套規則被安裝與驗收。

## 決策

1. 建立 `skill-packs/agent-inventory/`，作為第六個技能包。
2. **不複製上游原始碼**。上游以固定 tag 記錄在 manifest，由 Agent 在使用者同意後 clone；安裝器只核對雜湊並複製其中六個技能目錄。
3. **不提供 Toolbox 自有技能**。上游已有 `/inventory` 總入口，再包一層只會重複，也會讓使用者分不清該叫哪一個。本套件因此沒有 `skills/` 目錄。
4. 安裝管理器沿用 `google-automation` 的生命週期模型：`status`、`install`、`update`、`rollback`、`remove`，狀態寫在技能掃描範圍之外，同名衝突一律停止不覆寫。
5. 把上游具備的破壞性能力明列為人類授權關卡，寫進 manifest 的 `[human_authorization_gates]` 與公開文件。

## 固定版本

| 項目 | 值 |
|---|---|
| Tag | `v0.2.1` |
| Commit | `c162b0adce4d1519b60f76de15bc00df85d611ce` |
| Tree | `9ccdd73635bb74b95e6d2a111c994758602f5a23` |
| LICENSE SHA-256 | `8e30b10020d068a10bf4376e97df27bf34c9a52b01de5c3d0f6e26f594353dac` |
| 授權 | MIT |
| 綑綁 | 否 |

採用當天先以 `v0.1.0` 鎖定既有 `main`；同日上游新增第六個技能 `inventory-flow`（為每個技能畫 Mermaid 流程圖並標出人類介入點），Toolbox 尚未提交，因此直接改鎖 `v0.2.0`。該版本另移除一個誤入版控的自指 symlink（安裝器會拒絕含 symlink 的技能目錄）並修正總入口的步驟數說明。同日再出 `v0.2.1`：技能改由設定檔的 `repoRoot` 定位 clone（見已知限制第 1 點），Toolbox 隨即改鎖。升級一律先更新 manifest 的 tag、commit、tree 與授權雜湊，重跑套件測試，再調整驗收關卡。

## 為何不選其他方案

- **複製原始碼進 Toolbox**：違反 `docs/dependency-policy.md`，會造成兩份程式各自演進、上游修正無法傳遞，授權與出處也難以追溯。
- **併入現有技能包**：盤點 agent 設定與知識管理、社群、官網、剪片都不同領域，會讓既有套件的職責變模糊。
- **只在 README 提一句「可以去用這個工具」**：使用者仍要自己處理安裝、衝突、更新與移除，也拿不到 Toolbox 的隱私與授權邊界說明。

## 人類授權關卡

| 動作 | 說明 |
|---|---|
| 下載上游 repository | 唯一的連網安裝步驟，先說明來源、固定版本、授權與容量 |
| 選擇掃描範圍 | 由上游 `inventory-setup` 詢問要掃哪些工具與專案根目錄 |
| 讀取規則全文寫摘要 | Agent 會讀到規則內容；若使用者的規則檔本來就有機密資訊，安裝前要先提醒 |
| 刪除規則或技能 | 上游網站的 `/api/delete`，移到系統垃圾桶；安裝器不會代為執行 |
| 在網頁上改寫原檔 | 上游網站的 `/api/save`，直接寫回實體檔案；安裝器不會代為執行 |
| 手改摘要或流程圖 | 上游網站的 `/api/summary` 與 `/api/flow`，只寫 `data/user-*.json`，不碰實體檔案 |
| 用外部編輯器開檔 | 上游網站的 `/api/open`，在本機啟動應用程式 |
| 寫入 `repoRoot` | 安裝最後一步，Agent 建立或更新 `~/.config/agent-inventory/config.json` 的這一個鍵 |

## 已知限制

1. **相對路徑（已於 v0.2.1 處理）**：v0.2.0 以前，六個技能的指令寫成 `python3 bin/scan.py`，只有在 clone 目錄下才會命中，`inventory-summarize` 與 `inventory-flow` 還要 Agent 自己以相對路徑讀寫 `data/`。v0.2.1 起，設定檔新增 `repoRoot`：每個技能開頭先取得 `$REPO`（設定檔 → 目前目錄是 clone → 問使用者），所有指令與 `data/` 路徑改用絕對路徑；`inventory-setup`、`install.sh` 與每次 `scan.py` 都會維護這個鍵。Toolbox 的安裝最後一步由 Agent 在使用者確認後寫入 `repoRoot`，讓全域安裝後可以直接使用。
2. **未驗證的工具**：上游宣告的 Cursor 與 OpenClaw 路徑取自官方文件，尚未在真機驗證；Antigravity 的對話紀錄是二進位資料庫，使用次數無法對應。本套件不代為宣稱這些已驗證。

## 授權與散布

上游為 MIT，授權文字隨 clone 一併取得，不在 Toolbox 重製。被盤點工具的名稱只用於標示來源，不代表相關公司背書。網頁編輯器從 `esm.sh` 載入 CodeMirror 6，屬使用者瀏覽器的對外請求，已記錄在第三方聲明與隱私文件。

## 失敗與替代方案

- 上游不可用或授權改變時，Toolbox 移除這個套件即可，其他五個套件不受影響。
- 使用者不想連網時，本套件無法安裝；沒有離線替代方案，也不提供內建副本。
- 驗收關卡任一未通過時，套件維持本機候選版，不標示為正式支援。
