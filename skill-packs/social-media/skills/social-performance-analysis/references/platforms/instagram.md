# Instagram 成效

查證日期：2026-09-06。官方 Meta 文件摘要，未做帳號讀取。

## 帳號與介面

只對適用的專業帳號及其媒體取得 insights。Instagram Login 使用 instagram_business_basic、instagram_business_manage_insights；Facebook Login 使用 instagram_basic、instagram_manage_insights、pages_read_engagement。需先確認實際登入路徑；官方亦列特定 Business Manager 角色關係可能需要 ads 權限，遇到才交 setup 說明並確認，不為一般報告偷偷擴權。第三方客戶的 Advanced Access 與自有測試的 Standard Access 分開。[官方 Insights 指引](https://www.postman.com/meta/instagram/folder/23987686-f659d7d1-d74c-44e4-9192-9b1e8694c511)

採套件正式 API 路徑時，可信 adapter 在同一程序以 `Runtime(workspace, "instagram", connection=...)` 讀取私人 `login_route`，並在已授權的成效讀取範圍內呼叫 `Runtime.access(confirmed_read=True, allow_refresh=...)`。直接 Instagram Login 的完整 scope 只有初次交換證據，當次 insights GET 才證明成效功能可用；Facebook Login 由 runtime 讀回 Page Token 的目前 scope 與 Page／IG 關係。Token 不得進模型、對話、命令列或資料集。明確權限不足交 setup；空資料、權限拒絕、失效與讀取錯誤分開，不能因空集合要求重新 OAuth。[Instagram Login 權限證據限制](../../../social-media-setup/references/instagram-threads-oauth.md#ig-權限證據與逐功能檢查)

## 指標與限制

按角色選帳號 reach、views、互動或追蹤變化；媒體 likes、comments、shares、saved 或適用的觀看時間。不是所有型態都支援所有指標：先驗當前 API 版本、媒體型態、period、metric_type、breakdown，再讀資料，不把範例或共用 SDK enum 當成本帳號白名單。帳號與媒體、自然與廣告不可混成同一定義。[官方帳號與媒體 Insights 範例](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-1ff01566-3509-48bd-a0f4-8571a91ccfdf)

官方指引指出部分帳號指標有追蹤者門檻，User Metrics 資料最長保留 90 天；不可承諾第一次就能直接補齊年度。資料不存在或暫時不可用可能回空集合，不能視為零。reach 是去重性質，不加總每日值冒充整月觸及。API 回傳 UTC timestamp 不表示該聚合一定是 UTC 曆日；保留 end_time 及真正期間語意。

## 讀回與停止

套件的 `official_performance_api.py` 已接帳號層單一 metric。`instagram_login` 走 `graph.instagram.com/{version}/{ig-user-id}/insights`；`instagram_facebook_login` 走 `graph.facebook.com/{version}/{ig-user-id}/insights`，並各自核對前述 scope 與目標。目錄不把 metric 名稱靜態列為保證；只有當次回應 name、要求的 period 與非空 description 相符才保存為 available，description／period 跨期改變會自動換 observed definition。第一版不接媒體層 insights，且 coverage 固定 unknown，不能因有 `total_value` 就宣稱完整曆期。

保存登入類型（非 Token）、帳號參照、欄位說明、期間、版本、完整性及取得時間。資料不可用就標 unavailable，權限失敗確認後標 permission_denied；更名或停用標 definition_changed 並分段。季度／年度需要私人合法歷史資料；無資料時不以公開讚數或不同日期累積值替代。假 Runtime／HTTP 已通過，不代表真實 IG 帳號或 insights 已驗收。
