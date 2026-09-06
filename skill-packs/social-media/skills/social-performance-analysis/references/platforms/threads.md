# Threads 成效

查證日期：2026-09-06。依 Meta 官方 Postman 文件，非真實帳號驗收。

## 介面、權限及指標

使用 Threads 自己的授權與 threads_basic、threads_manage_insights；不能拿 Facebook Page Token 代用。採套件正式 API 路徑時，可信 adapter 在同一程序以 `Runtime(workspace, "threads", connection=...)` 呼叫 `Runtime.access(confirmed_read=True, allow_refresh=...)`，由官方 debugger 核對目前 scope 並以 `/me` 核對帳號；Token 不得進模型、對話、命令列或資料集。runtime 成功只證明連線，實際 insights 仍由下列端點判定，權限不足、空資料與讀取失敗分開。官方帳號查詢為 GET `/{threads-user-id}/threads_insights`；本版可執行白名單限 views、likes、replies、reposts、quotes。[官方帳號 Insights](https://www.postman.com/meta/threads/request/4pbwq2u/get-account-insights)

貼文查詢為 GET /{threads-media-id}/insights。官方範例的貼文 views、likes、replies、reposts、quotes 為 lifetime；不可把所有本週發布貼文的 lifetime 值叫作「本週全帳號互動」。[官方貼文 Insights](https://www.postman.com/meta/threads/request/34203612-385abc7d-b3cc-4e5d-9937-ebbe7174e041)

## 定義與期間

帳號範例同時出現 values/end_time 與 total_value，followers_count 描述是目前追蹤者總量，不是日新增，因此本版只列描述，不允許放進曆期 series。follower_demographics 是 breakdown，也不當單一數值。同名 views 的帳號及貼文 scope 不同。保存 response 的 name、description、period、breakdown、end_time、API 版本；不要只保存數字。[官方完整 Insights 範例](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api?entity=request-34203612-b3b2c12a-7ce6-4d86-a3c6-6d31e3b66ea1)

執行前再核對所選 metric 可接受的期間、保留期限、人口統計門檻及版本；本次查證不保證任何任意一年的查詢都支援。UTC 格式時間保留原期間邊界，不自行推定當地曆日。對發展中的 metric 保留定義版本，改變就拆段。

## 判讀與停止

依已確認的即時討論、曝光或導流角色判讀；回覆數不是正面口碑，需要討論品質時只使用已安全審核的互動摘要，不讀私訊補推。缺前期、只有 lifetime 或涵蓋不明，列描述及限制，不計算曆期成長。缺已授權工具／Token 則交 setup 或請使用者匯出，不擅自改用 IG 的 Threads 欄位混合兩種來源。

套件的 `metric-catalog.json` 會拒絕 followers_count、人口統計與貼文 lifetime 指標；`official_performance_api.py` 只接帳號層 `/{threads-user-id}/threads_insights` 單一白名單 metric，並要求回應 name、period=day 與 description 相符。因官方帳號範例未提供可安全套用的任意 `since`／`until` 查詢，本版不自行加入日期參數；requested period 只記錄使用者要分析的範圍，不能證明回應就是該曆期。因此 coverage 固定 unknown，資料可留作限制性描述，但不會通過一般期增減比較。

adapter 會核對 Threads 自己的登入路徑、目標與 scope，Token 只在記憶體；假 Runtime／HTTP 已通過，不代表真實帳號、metric 期間或保留期限已驗收。
