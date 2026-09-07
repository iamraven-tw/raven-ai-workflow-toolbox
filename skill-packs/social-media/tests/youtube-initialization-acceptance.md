# YouTube 初始化實機驗收紀錄

日期：2026-09-07。Windows；使用受控瀏覽器及獨立 Cloud 測試專案。此公開紀錄只記通用行為，不包含私人資源識別、帳號或憑證。

| 驗收項目 | 結果 |
| --- | --- |
| 新建專案、切换至新專案 | 通過；切換後需重新核對頁面與連結目標 |
| YouTube Data API v3 | 已啟用並讀回；啟用後詳細頁載入錯誤，重載讀回成功 |
| YouTube Analytics API | 已啟用並讀回 |
| Google Auth 初始表單 | 本人完成政策確認並建立；兩個唯讀 scope 已保存 |
| 測試使用者 | 正式清單顯示一位；曾同時出現資格提示，後續本人 OAuth 與頻道讀回成功，確認此測試帳號可用 |
| Desktop client | 已建立電腦版應用程式；建立對話框提示 secret 僅能當次保存 |
| 原生秘密輸入 | 本人完成 Windows Terminal 隱藏輸入，收據 verified |
| OAuth 同意與 Token 保存 | 本人完成，loopback callback、交換、原生保存及指定頻道讀回成功，Runtime ready |
| 真實 Data API 內容讀取 | 通過；共用 main connection，最多五筆 uploads 取樣成功，保留 sample_only 與 has_more，不宣稱完整歷史 |
| 真實 Analytics 資料讀取 | 通過；同一 main connection，單一 views 指標、已結束的七個美西日期，聚合與逐日涵蓋檢查 complete |
| Windows 原生儲存 | 真實 OAuth 完成後另啟 Python 程序，兩個 adapter 透過同一 Runtime 取用已保存憑證成功；未強制觸發到期刷新或撤權測試 |
| macOS 原生儲存與平台連線 | 尚未實機驗收 |

本輪初始化與兩條最小唯讀路徑已完成。後續沿用同一私人工作區與 connection，不重新建專案／client 或要求再次貼秘密。完整選題流程、正式週期報告、其他指標、到期刷新、撤權恢復與 macOS 仍須各自驗收；不把本輪成功擴大為整包技能或所有平台功能通過。
