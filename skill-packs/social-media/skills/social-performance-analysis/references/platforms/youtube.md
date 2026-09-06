# YouTube 成效

查證日期：2026-09-06。正式文件查證，不代表帳號或 API 實測。

## 讀取與指標

正式路徑為 YouTube Analytics API v2 的 GET reports；目前 `reports.query` 需要已授權頻道的 `youtube.readonly` 與 `yt-analytics.readonly`。營收另需 monetary scope 與資格，不因能上傳影片就認定能讀 Analytics，也不自動加權限。查詢前確認該報表允許的 metrics、dimensions、filters 組合。[Reports Query](https://developers.google.com/youtube/analytics/reference/reports/query)

本版固定白名單是 views、engagedViews、estimatedMinutesWatched（分鐘）、averageViewDuration（秒）、averageViewPercentage（0–100）、likes、comments、shares、subscribersGained、subscribersLost。官方 Basic user activity report 允許這些指標在無 dimension 的聚合查詢及 day dimension 查詢使用；第一版不接受 filters，因此訂閱增減維持全頻道定義。[Channel Reports](https://developers.google.com/youtube/analytics/channel_reports#video-reports)、[Metrics](https://developers.google.com/youtube/analytics/metrics)

`views` 與 `engagedViews` 不可互換。Targeted Queries 自 2025-04-30 起，Shorts 的 views 計開始／重播，engagedViews 保留先前觀看方法；2026-08-27 又把公開 views 起算對齊所有影片格式，而 engaged view 仍要求播放超過第一格或點擊播放。兩者使用不同 definition ID，舊 views 序列不得無條件接到新口徑。[官方修訂紀錄](https://developers.google.com/youtube/analytics/revision_history)

## 時間與比較

日彙總以美西日期為準，含日光節約時間；本版 collection plan 強制使用 IANA `America/Los_Angeles`，不可標成使用者當地午夜。查詢可能只回到所有所選指標都可用的最後一天。內部資料用不含尾日；一般日報查詢 endDate 對應最後納入日，month dimension 的特殊起訖要求另依文件，不能直接套 daily 轉換。[Dimensions](https://developers.google.com/youtube/analytics/dimensions)、[Reports Query](https://developers.google.com/youtube/analytics/reference/reports/query)

Shorts、長片、直播及自然／廣告來源分組。API 欄位或 views 定義改變須換 definition，不能用新舊口徑接成單一成長線。公開 Data API 累積統計只能作快照，不替代這週 Analytics 活動。沒有去年完整資料就交年度缺口，不反推不存在的歷史。

## 操作交接與停止

套件的 `metric-catalog.json` 與 `metric_catalog.py` 先核對白名單、definition、unit、aggregation、basis、時區、無 filter 及 coverage probe；`official_performance_api.py` 才接帳號層單一 metric。內部不含尾日的期間會轉成官方含尾日 `endDate`，先讀聚合值，再用 `dimensions=day` 核對每一日。日期完全吻合才標 complete；少日標 partial，無 rows 標 unavailable 而非零。Token 經 setup Runtime 只放 Authorization header；回應及 query 由 collector 去敏感保存。這仍不支援營收、群組、影片層多維度或其他 metric 組合。

遇 401／403 先標 read_failed 或確認後的 permission_denied，交 setup；不可把所有 403 都當成單一原因。缺正式 API 條件可用已授權官方匯出；本包不下載 SDK。假 Runtime／HTTP 已通過，不代表真實頻道讀取已驗收。
