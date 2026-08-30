# 預設 Provider Adapter

只有工作區實際使用 Graphify 或 `notebooklm-py` 時才讀本文件。若工作區設定其他 Provider，應依 `SKILL.md` 的能力契約執行，不要套用這裡的工具名稱與欄位。

## Notebook／notebooklm-py

### 真相來源

- `sources/references/notebooks/` 是本機路由索引與最近一次成功同步的快照。
- Notebook 遠端來源清單是遠端真相；本機索引不能證明遠端目前完全相同。
- 自動化一律使用完整 Notebook ID，不依賴 `notebooklm use` 的全域目前選擇。

### 驗證與查詢

1. 執行 `notebooklm auth check --test --json`。
2. 同時確認 `status=ok` 與 `checks.token_fetch=true`。
3. 使用 `notebooklm ask "問題" -n <notebook_id> --json`。
4. 需要限制來源時，明確加入 `-s <source_id>`。
5. 保存 `references[].source_id`、`citation_number` 與 `cited_text`，再用來源清單對回標題與網址。

登入失效時停止遠端查詢，讓使用者本人重新登入；不得讀取或輸出登入狀態內容。

### 登錄與同步

- 以 `notebooklm source list -n <notebook_id> --json` 取得遠端來源。
- 每個 entry 至少記錄 Notebook 標題、完整 ID、網址、主題、用途、同步狀態、最後驗證時間、複查時間與來源清單。
- 來源清單至少記錄來源 ID、標題、類型、URL、遠端狀態、加入時間與最後看到時間。
- 遠端已移除來源改標 `removed_remote`，不要直接刪除本機歷史。

### 加入來源

1. 確認目的 Notebook。
2. 執行 `notebooklm source add <來源> -n <notebook_id> --json`。
3. 取得 `source.id` 後，再用來源清單或經使用者同意的等待操作確認遠端狀態。
4. 遠端確認完成後才更新本機 entry。
5. 只有本流程建立的傳輸暫存副本可在完成後清理；使用者原始檔案不得刪除。

`notebooklm-py` 使用非官方介面。介面變更或回傳異常時，保留本機索引與原始資料，將狀態標成 `error` 或 `unverified`，不得宣稱成功。

## Graphify

### 角色與輸出

- `sources/graphify-out/graph.json`：Agent 查詢節點、關係與信心標記。
- `sources/graphify-out/graph.html`：使用者探索關係的互動式網頁。
- `sources/graphify-out/SOURCES_OVERVIEW.md`：來源概況與路由輔助。

實際檔名可能隨 Provider 版本改變；先使用目前已安裝的 Graphify 技能檢查能力與輸出，不把這些檔名當成所有知識結構 Provider 的永久介面。

### 查詢與交付

- 使用已安裝的 Graphify 技能定向查詢，不直接掃描整個圖譜輸出。
- 保留 `EXTRACTED`、`INFERRED`、`AMBIGUOUS` 等信心標記。
- 本次若成功建立或更新圖譜，且 `graph.html` 存在，提供可開啟的絕對路徑。
- 涉及三個以上節點、跨文件關係、概念路徑、核心節點或群聚結構時，主動附上互動圖。
- 同時說明最值得查看的二至五個節點或關係，不能只交付檔案。

### 更新狀態

- `.needs_update` 存在、索引標成 `pending_update`，或 HTML 早於 JSON 時，將視覺化標為可能過期。
- 新增一小段筆記不代表必須立即重建；先標記更新需求，再依資料量與當次任務決定。
- 只有更新實際成功後，才能把狀態改為 `current`。
- manifest 缺失、環境異常或變更數量不合理時停止，不自動重建或清空既有圖譜。
