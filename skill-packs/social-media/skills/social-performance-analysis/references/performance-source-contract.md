# 成效資料來源與正規化契約

## 第一版資料來源

本技能不是任意 HTTP 用戶端。第一版只接受下列已選定路徑：

| 平台 | 優先介面 | 本機接線 | 目前範圍 |
| --- | --- | --- | --- |
| YouTube | YouTube Analytics API v2 `reports.query` | `official_performance_api.py` | 自有頻道、單一指標、完整曆期；聚合查詢加逐日涵蓋探測 |
| Facebook | Graph API Page `/{page-id}/insights` | 同上 | 自有粉絲專頁、單一已查證 metric；不含貼文／Reels 細分 |
| Instagram | Instagram API `/{ig-user-id}/insights` | 同上 | 自有專業帳號、單一已查證 metric；依 Instagram Login 或 Facebook Login 選 host |
| Threads | Threads API `/{threads-user-id}/threads_insights` | 同上 | 自有帳號、單一已查證 metric；第一版不自行發明日期參數 |
| Substack | 官方唯讀 MCP | `performance_collect.py` 匯入證據 | 合資格出版物的已保存聚合觀測；不是通用 REST API |

Substack 無法使用官方 MCP 時，可接受官方匯出檔；最後才接受已核准 OpenCLI／受控 Chrome 從官方後台讀取並保存的證據。RSS 不能代替成效資料。這三種來源都必須先建立 `performance_source_observation` artifact，並綁定工作區內原始證據的 SHA-256；只有一個人工填寫數字的 JSON 不會通過匯入。

機器可讀選擇表見 [execution-sources.json](execution-sources.json)；可交給程式執行的指標、單位、聚合、期間與來源資格另由 [metric-catalog.json](metric-catalog.json) 固定。`metric_catalog.py` 會在發出 API 請求或接受匯入前檢查此目錄。選定介面、SDK 欄位存在或 OAuth scope 已取得，都不等於本帳號能讀該指標。

## 官方 API 讀取流程

1. Agent 依使用者要求選平台、完整曆期、帳號與 1–20 個必要序列，先顯示本次唯讀範圍。讀取資料的同意不包含刷新 Token；只有 `allow_token_refresh=true` 且當次已獲准時才可刷新。
2. 每個序列固定 key、平台角色、metric、definition、unit、aggregation、scope、segment、basis 及平台 query。相同序列的本期和前期不得改定義；這些欄位必須通過 `metric_catalog.py`，不得由 Agent 猜單位或沿用舊名稱。
3. `performance_collect.py collect-official` 透過 `OfficialPerformanceAdapter` 呼叫 setup 的 `Runtime.access()`。Token 只在可信程序記憶體與 Authorization header 中出現，不進 query、計畫、證據、資料集、終端輸出或模型內容。
4. adapter 一次只讀一個 metric，只允許官方 HTTPS 主機與固定 GET 端點，不跟隨重新導向。回應保存至私人 `social-media/performance/<report-id>/evidence/`；保存內容含平台、帳號參照、介面、API 版本、請求期間、query、回應定義、取回時間、去敏感原始回應與錯誤類型。
5. 收集器把結果轉成既有 schema 1 dataset，立即交 `performance_review.py analyze` 重驗期間、時區、證據雜湊、數值與可比較性。資料集固定寫至同一私人報告目錄。
6. 同一 collection plan 以雜湊鎖定。若中斷後證據已完整保存，只重用相同 request hash 的證據；既有證據或計畫不同就停止，不為了補報表再次消耗 API 配額。

第一版的實際指標規則如下：

- YouTube 只接受目錄列出的自有頻道基本活動指標，來源時區固定 `America/Los_Angeles`，不接受 filters；`views` 與 `engagedViews` 使用不同 definition。平均觀看秒數、平均觀看百分比與總數不可互換 aggregation。
- Facebook 不提供靜態 metric 白名單。每次查詢都必須帶 `show_description_from_api_doc=true`，回應須含相同 name、period 與非空 `description_from_api_doc`；否則停止。這只能證明當次帳號／版本讀到該欄位，coverage 仍是 unknown。
- Instagram 不以 SDK enum 當白名單。當次回應須含相同 name、所要求 period 與非空官方 description；metric、period、metric_type 或帳號不適用時，依正式錯誤或空資料分流，不能自動換舊名稱。
- Threads 只接受目前官方帳號範例的 views、likes、replies、reposts、quotes。followers_count 是目前總量快照，人口統計是 breakdown，貼文 insights 是 lifetime，三者不塞進本版相鄰曆期序列。

官方 API plan 的頂層欄位固定為 `schema_version`、`report_id`、`mode`、`timezone`、`platform`、`account_ref`、`period`、`comparison_period`、`source_mode`、`scope`、`series`。`source_mode` 為 `official_api`；scope 必須包含同一 platform／account_id、非空 approval_ref、`confirmed_read=true` 與當次刷新選擇。每個 series 另含 query。

## 匯入證據流程

Substack 或已授權的官方匯出／受控瀏覽器先保存原始 JSON、CSV、HTML 摘要或截圖證據，再建立一個只含單一觀測的 artifact：

- 固定來源身分：platform、interface、account_ref、key、role、metric、definition、unit、aggregation、scope、segment、basis、timezone、period。
- 資料品質：status、coverage、value、observed_at。
- 來源資格：`eligibility` 必須與介面一致。官方 Substack MCP 為 `admin_bestseller_mcp_connected`；官方匯出為 `account_export_authorized`；受控瀏覽器為 `authenticated_admin_browser_read`。只有「已連接」而沒有 Admin／Bestseller 證據，不能冒充合資格 MCP。
- 原始證據：`raw_evidence_path` 必須在私人 `social-media/performance/` 內；`raw_evidence_sha256` 必須和檔案相同。
- interface 只接受 `official_substack_mcp`、`official_export`、`controlled_browser`。瀏覽器來源必須是使用者已登入且已核准的官方後台畫面，不接受非公開端點重播。

匯入 plan 的 `source_mode` 為 `imported_evidence`，scope 固定 `{"confirmed_read": true}`；series 用 `artifacts.current` 與 `artifacts.previous` 指向兩個 artifact。收集器會核對所有身分欄位、時區、實際期間、來源資格與兩層雜湊，不接受換標籤或缺原始證據。Substack 在本版曆期 helper 只接受明確期間的 `traffic_views`，或期末 `total_subscribers`／`paid_subscribers` 快照；文章 lifetime 指標與年化營收另列描述。

## 完整性與停止條件

- YouTube 內部期間尾日不含；送至官方 `endDate` 時改成最後納入日。聚合有值後再用 `dimensions=day` 探測每一日；日期完全吻合才標 complete，少日為 partial，沒有逐日證據為 unknown。空 rows 是 unavailable，不是零。
- Facebook、Instagram 與 Threads 第一版不從數字本身推測完整性。當次正式 description／period 只建立「欄位可讀」證據；直到所選 metric 的期間語意、回傳 end_time／分頁與保留限制有可驗證證據前，coverage 保持 unknown，因此不會計算一般期增減。Meta description 或 period 跨期改變時，收集器會換 observed definition，使序列不可比較。
- Meta 多點 values 只有 total 可相加，snapshot 只取最後值；unique、average 或 rate 不安全時停止。真正平台提供的 `total_value` 可直接保存，但仍不代表期間完整。
- 401／失效交 setup 重新授權；明確權限不足為 permission_denied；無效或停用 metric 為 definition_changed；限流、網路、格式或不明錯誤為 read_failed。任何非 available 狀態的 value 必須是 null。
- 帳號、登入路徑、scope、metric、期間、時區、來源證據或 request hash 不符就停止。結果不明時不改用另一來源拼湊，也不把缺值補成零。

## 本機命令

Agent 使用已安裝技能的實際路徑；INPUT 是私人工作區內已預覽的計畫檔：

    python3 scripts/performance_collect.py collect-official --workspace WORKSPACE --input social-media/performance/REPORT/collection-plan.json
    python3 scripts/performance_collect.py collect-import --workspace WORKSPACE --input social-media/performance/REPORT/collection-plan.json

兩個命令都可能建立私人證據、dataset 及 `.local` collection journal，但不寫長期策略、不發布、不回覆、不排程。CLI 只輸出資料集路徑與各狀態筆數，不輸出成效數字。真實 Token、API、MCP、匯出檔與瀏覽器尚待集中實機驗收。
