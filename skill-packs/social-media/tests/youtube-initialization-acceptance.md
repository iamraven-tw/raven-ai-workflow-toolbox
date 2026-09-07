# YouTube 初始化實機驗收紀錄

日期：2026-09-07。Windows；使用受控瀏覽器及獨立 Cloud 測試專案。此公開紀錄只記通用行為，不包含私人資源識別、帳號或憑證。

| 驗收項目 | 結果 |
| --- | --- |
| 新建專案、切换至新專案 | 通過；切換後需重新核對頁面與連結目標 |
| YouTube Data API v3 | 已啟用並讀回；啟用後詳細頁載入錯誤，重載讀回成功 |
| YouTube Analytics API | 已啟用並讀回 |
| Google Auth 初始表單 | 已填應用程式資訊、External 測試用途與聯絡資訊；停在本人資料政策確認 |
| Desktop client、OAuth 同意與 Token 保存 | 尚未執行 |
| 真實 Data API 內容與 Analytics 資料讀取 | 尚未執行，不能以後台啟用代替 |
| Windows 原生儲存 | 前一階段以一次性虛構值完成寫入、跨程序讀回及移除；不是 OAuth Token 驗收 |
| macOS 原生儲存與平台連線 | 尚未實機驗收 |

恢復測試：先讀回目前 Google Auth 頁面，確認本人已完成政策確認，再接續 Desktop client、兩個唯讀 scope、測試使用者與共用 Runtime 驗收。不得重建已存在的測試專案或重送結果不明的交換；後續逐項更新紀錄。
