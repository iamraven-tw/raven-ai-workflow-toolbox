# 發布交易整合本機驗證

日期：2026-09-06。範圍是 PUB-02 的本機交易協調器與虛構 adapter 串接；未登入、未讀取真實帳號、未取用原生秘密庫、未建立容器、未上傳、未發布、未排程、未寄信，也未操作 OpenCLI／Chrome。

## 已接通流程

`publish_execute.py` 只接受已完成 `publish_job.py begin` 的項目。四個 API 平台依序執行：從 ledger 建立 grant → setup Runtime 身分／憑證預檢 → 每個非冪等寫入前 claim → 呼叫固定平台 adapter → 安全 ID checkpoint → 獨立 GET → 去敏感 evidence → receipt／ledger。Token 仍由 `Runtime.access()` 在同一程序記憶體交給低階 adapter，沒有 Token 命令列參數或一般 JSON。

Substack 不建立假 API。協調器在本機產生綁定預覽、確認、目標、全文、素材與選項的 browser handoff；Agent 核對已登入的 Chrome 與刊物後，在第一次遠端編輯前 claim `browser-write`，操作後真正重載頁面，再把正規化 observation 交回同一 receipt 護欄。

## 中斷與讀回規則

- `begin` 仍是每項一次。每個遠端寫入階段另有一次性 claim；同一階段不能取得第二次 claim。
- claim 後尚未 checkpoint 就中斷，重新執行只記 unknown，不再送出該寫入，也不刪除遠端半成品或本機 ledger。
- Instagram／Threads 已取得容器 ID但仍處理中時，帳本保持 in_progress；下一次只 GET 同一容器，FINISHED 後才 claim 尚未執行的 publish。
- YouTube session URI 不落地。308、沒有影片 ID或程序中斷會記 pending／unknown，且不建立第二個 resumable session；跨程序續傳不在目前最小範圍。
- 官方 GET 缺正式網址、媒體實際比對或完整設定時，只能記 pending。Agent 另以真正重載的管理介面補 observation；不能把 request 原樣複製成 readback。
- 前一平台不是 published／scheduled 時，後一平台不能 begin。沒有自動重送、換介面重發、刪除或回復遠端內容。

## 虛構案例

`test_publish_execute.py` 使用記憶體 FakeAdapter，涵蓋：

1. Facebook 純文字由憑證預檢、claim、checkpoint、PagePost GET 到完整 receipt。
2. 憑證預檢失敗發生在寫入 claim 之前；不留下假定已發送的操作。
3. Facebook 輪播第一張成功、第二張結果不明時，保存第一個 ID，不建立 feed、不刪除、不重送。
4. Instagram 容器第一次仍處理、第二次 FINISHED 時，只重讀同一 container ID，建立與 publish 各一次。
5. YouTube 308 保存「敏感 session 僅在記憶體」與「未取得 ID」狀態，不開第二個 session。
6. 第一平台 unknown 時阻擋第二平台 begin。
7. Substack handoff、一次性 browser claim 及真正重載後 observation／receipt。

針對發布的三個測試檔共 32 項通過：本機交易護欄 15 項、低階官方 adapter 10 項、交易整合 7 項。全部使用虛構工作區與假平台回應。

## 驗證分層

| 層級 | 結果 |
| --- | --- |
| 靜態結構與文件 | validator、技能 quick validation、差異空白檢查均通過 |
| 本機技能發現 | 本輪未執行 |
| API 套件是否可安裝 | 未新增套件；三支發布程式只使用 Python 標準函式庫 |
| 使用者登入與 OAuth | 未執行；FakeAdapter 未取用秘密庫 |
| 平台讀取 | 未執行；所有 readback 是虛構資料 |
| 測試發布 | 未執行；沒有任何真實外部寫入 |
| 另一臺電腦驗收 | 未執行 |
| 正式公開支援 | 尚未成立 |

本機通過證明交易順序與停止護欄可重複測試，不證明 Meta、Google 或 Substack 的真實帳號、權限、格式、UI 或當前 API 版本可用。實機發布仍留到整包完成後的集中驗收。

本次修改後整包共執行 258 項：257 通過，1 項原生憑證探測依集中實機驗收政策略過。這個數字包含現有七技能的離線回歸，不包含任何網路或使用者帳號行為。
