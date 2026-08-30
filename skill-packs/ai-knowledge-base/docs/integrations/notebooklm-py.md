# notebooklm-py 整合邊界

## 角色

`notebooklm-py` 與其 `notebooklm` 通用技能，是 `My Real Second Brain` 目前操作 Notebook 的預設底層工具。它負責：

- 驗證登入狀態。
- 建立與列出 Notebook。
- 新增、列出與查核來源。
- 查詢內容並取得來源引用。

Notebook 的路由選擇、知識優先度、來源整合與本機索引維護，仍由 `knowledge-source-retrieval` 負責。

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
