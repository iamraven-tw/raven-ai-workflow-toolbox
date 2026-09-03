# notebooklm-py 整合邊界

## 角色

`notebooklm-py` 與其 `notebooklm` 通用技能，是 `My Real Second Brain` 目前操作 Notebook 的預設底層工具。它負責：

- 驗證登入狀態。
- 建立與列出 Notebook。
- 新增、列出與查核來源。
- 查詢內容並取得來源引用。

Notebook 的路由選擇、知識優先度、來源整合與本機索引維護，仍由 `knowledge-source-retrieval` 負責。

候選版固定 `notebooklm-py[browser]==0.8.0`。版本、tag、commit、發行檔雜湊與 MIT 授權來源以 `install.manifest.toml` 為準。本次查到的[最新正式版為 `0.8.1`](https://github.com/teng-lin/notebooklm-py/releases/tag/v0.8.1)，但沒有因新版存在就自動升級。

## 為何不把技能複製進來

上游 CLI 已提供自己的技能安裝與更新機制。直接複製會形成兩份容易分歧的版本，也可能讓指令說明落後於實際套件。

本專案因此只保存整合契約，不重製上游 `SKILL.md` 或程式碼。AI Agent 依 `install.manifest.toml` 安裝經本專案驗證的固定版本；上游文件用於核對安裝方式與相容性。

## 執行契約

- 自動化一律使用完整 Notebook ID，不依賴全域目前選擇狀態。
- 查詢與清單操作優先使用結構化輸出，保留 Notebook、來源與引用 ID。
- 新增來源成功後，必須更新本機 Notebook 索引與同步時間。
- 本機只保存路由中繼資料，不保存大型來源全文。
- Cookie、Token、登入狀態檔及私人憑證不得提交到 Git。
- 刪除 Notebook、來源或分享權限前，必須再次確認明確目標。

## 非官方介面風險

`notebooklm-py` 是非官方社群專案，依賴可能變動的未公開 Google 介面。操作失敗時，應保留本機索引與原始資料，並將狀態標示為未驗證或同步失敗，不得宣稱遠端操作成功。

## 安裝、登入與移除界線

- 套件、Agent 技能、登入狀態與遠端 Notebook 是四個不同層級。
- 專案技能可分別使用 `notebooklm skill install --scope project --target agents` 或 `--target claude`；先用 `status` 或 `--dry-run` 檢查，不使用 `--force` 覆蓋未知內容。
- `notebooklm --version` 只證明 CLI 可執行；`skill status` 只證明技能檔案狀態。
- `notebooklm auth check --test --json` 同時回傳 `status: ok` 與 `checks.token_fetch: true`，才代表當時登入可向遠端驗證；`notebooklm list --json` 才進一步證明 Notebook 清單 RPC 可用。
- 上游技能移除使用 `notebooklm skill uninstall --scope project --target <target>`。這不會自動移除套件、登入檔或遠端 Notebook。
- 清除登入狀態、刪除 Notebook、刪除來源或更動分享權限都不屬於一般本機解除安裝，必須另行取得明確同意。
