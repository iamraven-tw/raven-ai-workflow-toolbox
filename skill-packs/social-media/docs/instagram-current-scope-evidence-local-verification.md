# Instagram Login 當前權限證據查證與本機驗證

日期：2026-09-06。範圍為待辦 `INIT-02`：查證 Instagram API with Instagram Login 是否有正式介面可重新列出 Token 的全部當前 scope，並驗證技能在缺少這種介面時不假造端點。沒有登入、執行 OAuth、讀取真實 Token 或呼叫平台。

## 官方查證結論

Meta 官方 Instagram Login 集合列出帳號基本資料、發布、公開留言與私訊需要的四個 `instagram_business_*` scope；官方 Insights 文件另列 `instagram_business_manage_insights`。因此技能的五項核心權限清單有當前官方依據。

已查的 Instagram Login、Token 交換／刷新、Instagram API Postman 集合與 Insights 文件沒有文件化可重新列出這條路徑全部當前 scope 的端點，也沒有列出 Instagram Login 專用的 `debug_token` 或 `/me/permissions` 操作。本結論是「目前已查官方資料沒有文件化」，不是聲稱平台永遠不存在此能力；實際初始化仍要按當時版本重查。

本技能因此不新增猜測 API。初次 code 交換中的 `permissions` 必須與使用者確認清單完全一致；長期 Token 每次取用仍讀 `/me` 核對當前基本身分。發布、留言、insights、私訊則由對應的正式功能端點取得當次證據，不能用 `/me` 成功推定全部權限有效。

官方來源：

- [Instagram API with Instagram Login](https://www.postman.com/meta/instagram/folder/1z5vxzu/instagram-api-with-instagram-login)
- [Instagram Insights](https://www.postman.com/meta/instagram/folder/23987686-f659d7d1-d74c-44e4-9192-9b1e8694c511)
- [Business Login、交換與刷新](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login/)
- [Instagram Login Get Started](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started/)

## 行為邊界

- 初次交換證據：`initial_exchange_only`，證明那次回應包含完整確認清單。
- 當前身分證據：版本化 `/me` 成功，只證明 Token 尚能讀取指定專業帳號的基本身分。
- 當前功能證據：`verify_at_function_endpoint`；每個下游功能各自取得，互不推定。
- 已知失效回到 `reauth_required`；明確缺權限是 `permission_mismatch`；速率限制是 `rate_limited`；寫入結果不明是 `remote_result_unknown`，不得重送。
- insights 成功但回傳空資料不等於零或缺權限；需由成效技能保留 `unavailable`／空資料語意。
- 功能測試本身不能越過發布、回覆、私訊或其他遠端寫入確認。初始化不得為了證明 scope 而建立媒體 container、回覆留言或傳送訊息。

## 本機驗證

`tests/test_meta_user_oauth.py` 使用五項完整虛構核心 scope，確認初次交換會拒絕少授予、多授予及重複授予。新增案例確認每次 Instagram Login 取用只呼叫版本化 `/me`，正式 HTTP 白名單拒絕猜測的 Instagram `/me/permissions` 與 `debug_token`；已知權限、失效與速率錯誤會轉成固定非敏感狀態，未知寫入結果停止。

| 層級 | 結果 |
|---|---|
| 官方能力查證 | 已完成上述當前官方文件與集合查證；未找到文件化的全部當前 scope 讀回介面 |
| 靜態結構與文件 | 套件驗證器、第一技能 quick validation 與差異空白檢查通過；包含 manifest、文件連結、隱私、Python 語法與技能契約 |
| 本機技能發現 | 隔離安裝生命週期測試通過，更新後文件與測試契約納入安裝候選；未執行真實 Agent 技能探索 |
| API 套件是否可安裝 | 未新增第三方套件，仍使用 Python 標準函式庫 |
| OAuth 虛構執行 | Instagram／Threads 專用測試 30 項通過；整包 241 項中 240 項通過、1 項原生探測依政策略過 |
| 使用者登入／OAuth | 未執行 |
| 平台讀取與功能端點 | 未執行；官方文件和虛構回應不是帳號證據 |
| 測試發布／留言／私訊／成效 | 未執行 |
| 另一臺電腦驗收 | 未執行 |
| 正式公開支援 | 尚未成立；未 commit、push 或發布版本 |

這一項完成的意義是：權限證據模型與停止方式已明確，且程式不會冒充不存在的即時全 scope 驗證。它不代表五個功能已用真實帳號通過。
