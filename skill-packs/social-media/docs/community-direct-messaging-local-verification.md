# Meta 私訊 MVP 本機驗證

驗證日期：2026-09-06。這份紀錄只涵蓋本機程式、假 Runtime／HTTP 與虛構私訊；沒有登入 Meta、讀取或傳送真實訊息，也沒有建立 Webhook。

## 已實作

- `direct_message_queue.py`：Facebook／Instagram 專用 0600 狀態、固定規則隔離、24 小時檢查、人工 session 雜湊、批次預覽／確認、單次 claim、checkpoint、pending／unknown 停止與完整 receipt。
- `official_direct_message_api.py`：固定 `graph.facebook.com`／`graph.instagram.com`，依 Facebook Pages、Instagram Login、Instagram via Facebook Login 三條既有 setup 路徑取得記憶體 Token；列對話、讀最近 20 則純文字、傳送一次並讀回。
- `direct_message_execute.py`：按需 fetch、傳送前重讀、一次寫入、同 ID 續查及 unknown 的唯一觀測綁定。
- `manual_review.py`：新增 `direct_messages` 模式；私訊只出現在本機無 JavaScript／外部資源的人工頁面，不進 Google Sheets。完成頁明列審查批次、帳號、對話、對象與最終草稿，仍須回到 Agent 另行確認。

## 當次測試結果

以下 33 項針對性測試全數通過：

- 人工審查 11 項：包含原有公開留言 9 項及私訊模式 2 項。
- 私訊完整虛構串接 1 項。
- 私訊交易協調器 7 項。
- 私訊本機 queue 7 項。
- 官方私訊 adapter 7 項。

另外，Instagram via Facebook Login 的 setup Runtime／OAuth 資源交接 18 項全數通過；其中新增測試確認只有 ready 且呼叫者已確認讀取時，才回傳非敏感 linked Page ID，永不回傳 Token。

測試涵蓋：按需同步、過期／最新自家訊息／非純文字分流、疑似提示詞注入隔離、正文不出 stdout、人工第二次確認、三登入路徑、官方主機 allowlist、permission／目標核對、24 小時到期、對話競態、一次傳送、checkpoint、讀回中斷、unknown 不重送、唯一 observation 解鎖及 Google Sheets／Webhook 不建立。

## 尚未驗收

Meta App、Business Verification／App Review、真實 OAuth、三種登入路徑的實際 permission、真實對話欄位與排序、真實 24 小時資格、實際傳送及讀回、另一臺電腦和正式公開支援都未執行。第一版明確不建立 Webhook；這不是「尚未測試的內建功能」。
