# Facebook 粉絲專頁成效

查證日期：2026-09-06；本次 Page Insights 官方網頁仍無法成功讀取，以下區分官方原始碼可確認的部分與當次 API 才能證明的部分。

## 已確認介面

Meta 官方 codegen 的 Page 規格可確認 GET `/insights` 及 breakdown、date_preset、metric、period、show_description_from_api_doc、since、until 參數，但沒有列出 Page 可用 metric 清單。官方 Python Business SDK 的 InsightsResult 雖有共用 Metric enum，也不能證明其中任何欄位能由某一 Page／版本／權限讀取。[Page codegen 規格](https://raw.githubusercontent.com/facebook/facebook-business-sdk-codegen/main/api_specs/specs/Page.json)、[InsightsResult 原始碼](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/main/facebook_business/adobjects/insightsresult.py)

這裡只參考原始碼，不下載、安裝或複製 SDK，main 是查證頁面不是安裝依賴。

## 執行前核對

先讀 setup 保存的粉專參照與已授權能力，逐項確認 pages_read_engagement、read_insights 等實際適用要求、Page tasks、Token 對象、App access 與版本，不因已授權完整管理就當作全部查詢必成功。官方文件頁恢復可讀時，核對目前權限、指標名稱與定義、保留期限、since／until 邊界、period、分頁與停用通知。[待重新讀取的官方 Page Insights 參考](https://developers.facebook.com/docs/graph-api/reference/page/insights/)

未確認 metric 定義時不依舊記憶硬寫 page_impressions 等欄位，也不從共用 SDK enum 建立白名單。不使用 SDK 方法存在作為權限或年資料保證；可改用使用者提供的官方後台匯出，保留原標籤與篩選條件。

套件的 `official_performance_api.py` 已接 `graph.facebook.com/{version}/{page-id}/insights` 的帳號層單一 metric GET，要求 setup 設定含 `pages_read_engagement` 與 `read_insights`，並核對 Page ID。每次強制帶 `show_description_from_api_doc=true`；只有回應 name、period 與非空 `description_from_api_doc` 都相符才保存為 available，並把 period＋description 雜湊綁進 observed definition。失敗、空資料或欄位改版分開處理。adapter 不提供舊欄位清單，也不代表貼文或 Reels insights 已接通；coverage 固定 unknown，直到本 metric 的期間、分頁與完整性有足夠證據。

## 指標選擇與比較

經營角色需要曝光時看當前可用的觸及／觀看；需要討論時看公開互動；需要導流時看實際連結點擊，三者分開。此為分析方向，並非固定 API 欄位承諾。帳號、貼文、Reels、自然／付費要拆開；去重觸及不可每日加總，粉絲總量快照差不等於新增追蹤者。

保存當前版本、官方定義位置、查詢期間、時區、完整性、單位與讀取時間。空資料標 unavailable；權限／執行錯誤分開；欄位改變標 definition_changed。沒有已查證來源就只報限制，不產出假的可比較數字。adapter 已通過假 Runtime／HTTP，不代表真實 Page、metric 或資料完整性已驗收。
