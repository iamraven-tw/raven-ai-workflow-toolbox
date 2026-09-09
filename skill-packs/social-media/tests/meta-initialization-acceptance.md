# Meta 初始化實機驗收紀錄

日期：2026-09-07；更新：2026-09-09。Windows；受控瀏覽器、新建獨立測試 App。只記錄可重複查核的通用行為，不包含私人帳號、App ID、回呼網址或憑證。

| 驗收項目 | 結果 |
| --- | --- |
| 開發者後台登入 | 本人完成，已讀回應用程式清單 |
| 獨立 App 建立 | 已完成；本人接受建立頁的條款後，Agent 讀回新 App 主控板 |
| 三平台使用案例 | 本次建立精靈允許同時選取「存取 Threads API」、「管理 Instagram 的訊息和內容」、「管理粉絲專頁的所有內容」；建立後均有獨立設定入口 |
| 商家資產管理組合 | 本次選擇稍後連結；不代表目標資產關係、企業驗證或公開支援已通過 |
| Windows 原生憑證庫 | Instagram App Secret 與長期 User Token 保存及讀回通過；另一個程序以同一 runtime 取用成功 |
| HTTPS callback | 本機 TLS 與外部瀏覽器健康檢查通過；實際 OAuth callback 尚未通過，見下方 |
| OAuth／平台身分／內容／成效 | Instagram 最小讀取驗收通過，見下方；Facebook／Threads 尚未通過 |
| 發布、留言、私訊、Webhook | 尚未實測 |
| macOS | 尚未實機驗收 |

## 已觀察到的流程細節

- 建立精靈的「內容管理」篩選可找到三個對應使用案例。最終摘要會收合其他案例，需展開核對；建立後再核對主控板入口。
- 最終建立頁明示繼續即同意條款，由本人完成。填好表單不等於 App 已建立。
- Instagram 同時提供 Instagram Login 與 Facebook Login 兩個設定入口，且有獨立的 Instagram App ID；不可把 Meta App ID 直接當作所有平台的 client ID。
- 本次 Instagram Login 引導仍顯示切換 Facebook Login 以使用洞察報告的文字，但同一 App 的權限表列有 `instagram_business_manage_insights`。此處只記錄介面差異；不可由單段引導判定該路線不支援 insights，也不可因權限出現在表格便宣稱端點可用。需查核官方端點並完成目標帳號實讀。
- 同一 App 可以容納本次三個使用案例，不代表三平台共用 Token、Secret、OAuth 或驗收結果。未完成 HTTPS、原生保存與本人 OAuth 同意前，不進入 Token 測試。

## Windows 本機 HTTPS 前置驗證（2026-09-08）

- 經使用者授權，使用官方 mkcert v1.4.4 建立並信任測試 CA，產生測試主機憑證；私鑰保留在限制存取的私人目錄。
- 備份 hosts 後加入單一測試主機至 loopback 的對應。管理員程序完成、結果收據與 DNS 讀回均通過；使用者未看見提示時先查完成狀態，不重複建立請求。
- 本次 AppData 路徑在不同程序間出現可見性差異。改放私人工作區後，Python 可讀取憑證。記錄觀察結果，不將未查明的虛擬化機制寫成已證實原因。
- 內建 Windows PowerShell 拒絕執行腳本；改用本環境已有且允許腳本的 PowerShell 完成 hosts 修改，未變更執行原則。
- 獨立健康檢查服務只監聽 IPv4 loopback；Python 以系統信任庫、正常主機名稱與憑證驗證完成 HTTPS 請求。此服務不接收 OAuth code 或交換 Token，不取代正式 OAuth runtime。
- Codex 內建瀏覽器開啟測試主機時回報 `net::ERR_BLOCKED_BY_CLIENT`。尚未判定阻擋原因，不關閉安全檢查，也不以程式端成功宣稱瀏覽器 callback 已通過。
- 使用者在外部瀏覽器回報健康檢查成功文字，完成瀏覽器 HTTPS 人工驗收；尚非 OAuth 驗收。首次健康檢查因服務五分鐘到期而拒絕連線，確認程序已結束後延長至三十分鐘並重新驗證成功；交接時應檢查服務存活及剩餘時間。
- Instagram Login 回呼已保存，後台產生的授權網址包含正確 redirect URI。未直接使用缺少 runtime state 保護的後台範例網址進行 OAuth。
- Threads 回呼填入並儲存後，重新載入仍為空白；改用鍵盤輸入並選取網址選項也未讀回持久結果，介面未顯示明確錯誤。原因未確認，暫不標示回呼設定成功，不開始該路線 OAuth。

## Instagram 測試角色驗收（2026-09-09）

- 已在登入後的 Instagram 設定核對目標帳號及其顯示的相連 Facebook Page；這是後台關係證據，不是 API 身分讀取驗收。
- 先讀回新 App 角色表與 Instagram「網站權限 → 應用程式和網站 → 測試員邀請」，均未見新 App 邀請；保留舊 App 角色及授權。
- 在 Meta 角色表選擇 Instagram 測試人員，輸入帳號後等待搜尋結果並點選精確匹配項目，再提交。此次表單關閉，角色表新增目標帳號並顯示待確認；Instagram 重新載入後也出現新 App 邀請。只輸入文字後送出未取得成功證據，不能視為已選取帳號。
- 邀請接受畫面附帶 Meta 條款與開發商政策同意，已停在本人操作交接；尚未將角色標示為生效，也未開始 OAuth。
- 已將搜尋結果選取與邀請讀回要求補入主技能。此項操作修正經真實介面驗證；官方 App Roles 文件另行讀取時回傳 HTTP 429，未以文件抓取失敗推定平台規則。

以上是部分初始化證據，不能標示整個 Meta 整合或技能已通過。實際後台可能隨 App 條件改變，仍以當次介面及正式 API 驗收為準。

## Instagram OAuth 與分層讀取（2026-09-09）

- 本人接受邀請後，重新載入角色表已不再顯示待確認。五項 `instagram_business_*` 核心權限均顯示可供測試，包含 `instagram_business_manage_insights`；未重新送出已生效的權限新增操作。
- 首次接收器在十五分鐘期限後回報 `timeout`，未進入交換。核對狀態後使用新 state 啟動同範圍 OAuth，不重用舊 callback 或 code。
- 本次受控瀏覽器成功從本機 TLS 啟動網址進入官方 Instagram 同意畫面；本人允許後回到完成頁。早前的瀏覽器阻擋仍屬既有觀察，不能推定每次皆會阻擋。
- 正式 runtime 完成 code 交換、長期 Token 交換、目標專業帳號及初始五項 scope 核對、Windows 原生保存與讀回，狀態為 `ready`。
- 另一個 Python 程序經 `Runtime.access()` 取用同一連線，身分檢查通過；Graph API v25.0 媒體端點 HTTP 200，取得五筆資料且仍有下一頁。此項僅為內容抽樣，不是完整歷史內容驗收。
- 同一程序使用既有 `OfficialPerformanceAdapter` 與同一 OAuth 連線讀取帳號 insights；`reach`、`period=day`、`metric_type=total_value` 的七日查詢回傳數值。此項證明成效端點可讀；adapter 的期間完整性仍為 `unknown`，未推定為完整覆蓋，也未加總每日去重觸及。
- API 回應本文、私人帳號與成效值不納入公開證據。未測試發布、留言、私訊、強制刷新、撤權或 macOS；初始 scope 證據也不代表所有寫入功能已驗證。

## Threads 測試角色與回呼阻擋（2026-09-09）

- 選取精確帳號搜尋結果後送出 Threads 測試角色邀請；本人登入並接受後，重新載入 Meta 角色表已不再顯示待確認，Threads 設定也出現該測試帳號。
- 網站權限頁的邀請分頁在本次受控點擊後未切換；使用 Tab 定位及 Enter 啟用後成功顯示邀請。這是本次操作證據，不推定為 Threads 普遍故障。
- 回呼欄位形成完整網址標籤後，以 Tab 定位儲存並按 Enter，取得明確提示「無法儲存表單，請確認你輸入的所有資訊皆正確無誤，然後再試一次」。尚未識別被拒絕的欄位，不再把原因描述為單純未按到儲存，也不宣稱回呼已保存。
- 已重查 [Meta 官方 Threads 範例](https://github.com/fbsamples/threads_api/blob/main/README.md)：本機映射網域、HTTPS 與自訂 port 是範例採用的方式。此來源不能證明本次特定網址已獲後台接受；未填入假的解除安裝／刪除端點來試圖通過表單。
- Threads Secret、OAuth 與 API 讀取仍未完成；保留既有正式 App 與 Instagram 成功連線。
- 本人手動儲存也重現相同表單錯誤，排除單純自動化點擊失效；未再要求重按。另查得官方範例倉庫的 [Issue #73](https://github.com/fbsamples/threads_api/issues/73)，由外部開發者回報跨瀏覽器、App 及正式 HTTPS 網域仍無法儲存。查閱時仍開啟且未見修正；這是相似症狀的第一手回報，不是 Meta 官方承認根因，也不證明本次網址本身沒有問題。Threads 初始化保持阻擋，未把推測寫成通用修復步驟。
