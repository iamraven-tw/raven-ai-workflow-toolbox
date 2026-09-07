# Meta 初始化實機驗收紀錄

日期：2026-09-07。Windows；受控瀏覽器、新建獨立測試 App。只記錄可重複查核的通用行為，不包含私人帳號、App ID、回呼網址或憑證。

| 驗收項目 | 結果 |
| --- | --- |
| 開發者後台登入 | 本人完成，已讀回應用程式清單 |
| 獨立 App 建立 | 已完成；本人接受建立頁的條款後，Agent 讀回新 App 主控板 |
| 三平台使用案例 | 本次建立精靈允許同時選取「存取 Threads API」、「管理 Instagram 的訊息和內容」、「管理粉絲專頁的所有內容」；建立後均有獨立設定入口 |
| 商家資產管理組合 | 本次選擇稍後連結；不代表目標資產關係、企業驗證或公開支援已通過 |
| Windows 原生憑證庫 | inspect 可用；本輪尚未保存 Meta Secret 或 Token |
| HTTPS callback | 尚未配置；既有 App 可使用 API 不代表已有可沿用的 OAuth 接收器 |
| OAuth／平台身分／內容／成效 | 尚未實測 |
| 發布、留言、私訊、Webhook | 尚未實測 |
| macOS | 尚未實機驗收 |

## 已觀察到的流程細節

- 建立精靈的「內容管理」篩選可找到三個對應使用案例。最終摘要會收合其他案例，需展開核對；建立後再核對主控板入口。
- 最終建立頁明示繼續即同意條款，由本人完成。填好表單不等於 App 已建立。
- Instagram 同時提供 Instagram Login 與 Facebook Login 兩個設定入口，且有獨立的 Instagram App ID；不可把 Meta App ID 直接當作所有平台的 client ID。
- 本次 Instagram Login 引導仍顯示切換 Facebook Login 以使用洞察報告的文字，但同一 App 的權限表列有 `instagram_business_manage_insights`。此處只記錄介面差異；不可由單段引導判定該路線不支援 insights，也不可因權限出現在表格便宣稱端點可用。需查核官方端點並完成目標帳號實讀。
- 同一 App 可以容納本次三個使用案例，不代表三平台共用 Token、Secret、OAuth 或驗收結果。未完成 HTTPS、原生保存與本人 OAuth 同意前，不進入 Token 測試。

以上是部分初始化證據，不能標示整個 Meta 整合或技能已通過。實際後台可能隨 App 條件改變，仍以當次介面及正式 API 驗收為準。
