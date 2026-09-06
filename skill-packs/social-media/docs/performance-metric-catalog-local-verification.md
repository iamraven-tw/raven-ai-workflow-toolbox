# 五平台成效指標目錄與口徑本機驗證

日期：2026-09-06。完成待辦 PERF-02 的官方文件查證、機器可讀指標目錄與離線限制；沒有登入平台、執行 OAuth、讀取真實帳號、建立 Substack MCP connector、匯出私人資料、操作瀏覽器、寫入策略、commit 或 push。

## 官方查證結論

- YouTube Analytics 的基本頻道活動報表同時支援無 dimension 聚合與 day dimension，適用本版的 views、engagedViews、estimatedMinutesWatched、averageViewDuration、averageViewPercentage、comments、likes、shares、subscribersGained、subscribersLost。日資料採美西日期，查詢也可能只回到所有所選 metric 都有資料的最後一日。[Channel Reports](https://developers.google.com/youtube/analytics/channel_reports)、[Reports Query](https://developers.google.com/youtube/analytics/reference/reports/query)、[Metrics](https://developers.google.com/youtube/analytics/metrics)
- YouTube 的 views 與 engagedViews 不是同一口徑。Targeted Queries 自 2025-04-30 起，Shorts views 改計開始播放／重播，engagedViews 保留先前方法；2026-08-27 的修訂又將公開 views 的起算對齊各影片格式。[Revision History](https://developers.google.com/youtube/analytics/revision_history)
- Facebook Page 的公開開發者參考頁本次仍無法穩定取得。Meta 官方 codegen 可確認 Page GET `/insights` 接受 metric、period、since、until 與 `show_description_from_api_doc`，但沒有 Page metric 名稱白名單；官方共用 InsightsResult enum 也不能證明某欄位對特定 Page／版本／權限可讀。[Page codegen](https://raw.githubusercontent.com/facebook/facebook-business-sdk-codegen/main/api_specs/specs/Page.json)、[InsightsResult](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/main/facebook_business/adobjects/insightsresult.py)
- Instagram 官方資料把帳號、登入路徑、permission、metric、period、metric_type、帳號門檻與資料保留分開；空 data 不能當零。第一版因此不從 SDK enum 建靜態白名單，只接受當次 endpoint 回傳相同 name、period 與非空 description 的欄位。[Instagram Insights 官方集合](https://www.postman.com/meta/instagram/folder/23987686-f659d7d1-d74c-44e4-9192-9b1e8694c511)
- Threads 官方帳號範例列出 views、likes、replies、reposts、quotes 與 followers_count，但查詢只顯示 metric／breakdown，沒有本版可安全使用的任意 since／until。followers_count 的說明是目前總追蹤者，貼文 insights 則是 lifetime；兩者不能冒充曆期活動。[Account Insights](https://www.postman.com/meta/threads/request/4pbwq2u/get-account-insights)、[官方完整範例](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api?entity=request-34203612-b3b2c12a-7ce6-4d86-a3c6-6d31e3b66ea1)
- Substack 官方 MCP 目前要求出版物 Admin、Bestseller 出版物及支援 MCP connector 的客戶端；它是唯讀，可讀出版物資料，但不能發布、傳送 Notes、修改帳號或讀 profile／Notes 活動。[官方 MCP 說明](https://support.substack.com/hc/en-us/articles/50834026608916-How-to-connect-Substack-to-your-AI-Assistant)
- Substack total subscribers／paid subscribers 是目前總量；gross annualized revenue 是把目前付費訂閱年化，不是本期實收。單篇 total views 包含重複的 web、email、App 觀看；open rate／delivery rate 的官方計算曾調整，link clicks 同時有開啟者比例與總點擊數。[官方指標指南](https://support.substack.com/hc/en-us/articles/5320347155860-A-guide-to-Substack-metrics)

## 已實作

- `references/metric-catalog.json`：記錄查證日期、官方來源、YouTube 精確指標身分、Facebook／Instagram runtime 定義規則、Threads 可執行與描述性指標，以及 Substack 語意指標與來源資格。
- `scripts/metric_catalog.py`：在 API 或 artifact 匯入前核對 metric、definition、unit、aggregation、basis、來源時區、query 與 eligibility。
- `official_performance_api.py`：Facebook 強制 `show_description_from_api_doc=true`；Meta 回應必須核對 name、period 與正式 description。YouTube 與 Threads 的直接 adapter 呼叫也不能繞過白名單。
- `performance_collect.py`：計畫先通過目錄；Meta 的 period＋description 雜湊會附加到 observed definition，兩期說明不同時既有分析器會拒絕比較。Substack artifact 新增來源介面對應的 eligibility 檢查。

## 保守邊界

- YouTube 只有白名單、無 filter、`America/Los_Angeles` 的帳號層基本活動序列可進第一版；營收、群組、影片篩選及多維度另行查證。
- Facebook／Instagram 當次 name／period／description 相符，只能證明該欄位在當次帳號與版本可讀，不證明完整分頁、保留期限或完整曆期，所以 coverage 仍為 unknown。
- Threads 帳號回應沒有被本包解讀成任意 requested period；coverage 維持 unknown。followers_count、人口統計及貼文 lifetime 只列描述。
- Substack 公開文件沒有承諾穩定 MCP 回應欄位 schema；artifact 必須保留原標籤、定義、期間、資格與原始證據。MCP 不合資格時改評估官方匯出或已核准受控瀏覽器，不降級為 RSS 或內部端點。

## 離線驗證結果

- `test_metric_catalog.py`、`test_official_performance_api.py`、`test_performance_collect.py` 與 `test_performance_review.py` 共 48 項全數通過。
- 涵蓋 YouTube views／engagedViews 定義分離、白名單、時區、錯誤單位／聚合、Facebook description probe、Meta period／description、Threads followers_count 排除、Substack MCP 不合資格、原始證據雜湊、逐日涵蓋與策略資料契約。
- 安裝生命週期 13 項全數通過；社群媒體整包 369 項離線測試通過 368 項，另有 1 項原生憑證探測依集中實機驗收政策略過。套件靜態驗證與 `social-performance-analysis` 技能格式驗證通過。
- 測試只使用虛構帳號、假 Runtime／HTTP 與暫存私人工作區，不代表任何真實指標能讀取。

## 驗收分層

| 驗收層級 | 本次狀態 |
| --- | --- |
| 靜態結構與文件 | 通過；套件 validator 與技能格式 validator 均通過 |
| 本機技能發現 | 未執行；留集中驗收 |
| API 套件是否可安裝 | 未新增 SDK；只用 Python 標準函式庫 |
| 使用者登入與 OAuth | 未執行 |
| 平台讀取 | 未執行；只有假 Runtime／HTTP |
| 測試發布／回覆／策略實機寫回 | 未執行，且不屬本項授權 |
| 另一臺電腦驗收 | 未執行 |
| 正式公開支援 | 尚未成立 |
