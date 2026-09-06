# 社群互動完整虛構串接驗證

日期：2026-09-06。範圍為待辦 `COM-04`。本次以同一個臨時私人工作區串接留言平台協調器、固定規則、本機人工審查、Google Sheets 協調器、回覆交易與獨立讀回。平台與 Sheets adapter 全部是記憶體內的虛構來源；沒有網路、帳號、Token、Google Sheets 寫入、平台回覆、瀏覽器操作或第三方套件安裝。

## 串接範圍

`test_community_end_to_end.py` 不直接改寫 queue 狀態來假裝整條成功。正常路徑依序使用：

1. `community_execute.py fetch-api` 保存擷取證據並 ingest。
2. `community_queue.py` 固定規則區分 screened、quarantined 與 duplicate。
3. `manual_review.py` 建立人類收據並把 allow 項目標為 ready。
4. `community_sheets.py write-batch` 檢查空白、取得唯一 claim、RAW 寫入及獨立 `userEnteredValue` 讀回。
5. 虛構人類修改 F 欄後，`approve-batch` 重讀並綁定最終文字。
6. `community_execute.py execute-api` 每則再次重讀 A:F、讀原留言、完整查自家回覆、取得平台 claim、寫入一次並獨立讀回。
7. `community_queue.py record` 只在 ID、作者、父留言、精確文字、網址、平台時間與證據雜湊完整時標為 replied。

## 已驗證情境

- 同批包含兩則正常留言與一則疑似提示詞注入；風險項不進 Sheets，相同擷取只記 duplicate。
- 六欄採 RAW，人工改過的 F 欄才會送給虛構平台；整列排序仍能依前五欄映射並按原批次順序執行。
- 先送第二則、只排序單一來源欄、確認後再修改 F 欄，都在平台 claim 前停止。
- 完整查到既有自家回覆時，不建立 attempt，也不產生平台寫入。
- Sheets claim 後中斷且遠端已有相同內容時，resume 只讀回，不再 PUT；確認後仍可完成同一批次。
- 已取得 reply ID 但第一次讀回失敗時保持 pending；續查沿用同一 ID，不再 create。
- create 結果 unknown 時阻擋下一則與所有重送。只有完整 observation 能綁回原本唯一且未完成的 `reply_create`、`reply_publish` 或 `browser_reply` claim；`failed`、claim 不唯一或只停在 Threads container claim 都不能解鎖。

## 測試發現與修正

原本 `record-observation` 在沒有 reply ID 時固定使用 `browser_reply` checkpoint，API create 結果 unknown 後即使獨立查到同一回覆，也無法綁回原 `reply_create`／`reply_publish` claim。這不是重送問題，而是安全恢復路徑缺失。

修正後新增內部 `observation-checkpoint` 狀態轉換：只接受 pending／unknown、沒有既有 reply ID、且只有一個未完成的可產生回覆 claim。它保存「由獨立 observation 解決」證據，再走原有完整 receipt 驗證；不新增 retry、解鎖或刪除命令。

## 驗證結果

以 `PYTHONDONTWRITEBYTECODE=1`、`SOCIAL_NATIVE_ACCEPTANCE=0` 執行：

- `test_community_end_to_end.py`：6 項完整串接測試全數通過。
- 社群互動 7 份測試檔：82 項全數通過。
- 整包 `unittest discover`：322 項中 321 項通過，1 項真實原生憑證探測依集中實機政策略過。
- `validate_package.py`、七份技能 `quick_validate.py` 與 `git diff --check` 均通過。

這些結果證明本機狀態與協調器在虛構外部來源下能串成一條流程；不能證明真實 Agent 會正確操作人工頁面、Google OAuth／Sheets、平台 Token、瀏覽器或遠端回覆。

## 分層狀態

| 層級 | 本待辦結果 |
| --- | --- |
| 靜態結構與文件 | manifest、契約、案例、validator、七技能格式與差異檢查通過 |
| 本機技能發現 | 未執行真實 Agent；整包離線安裝生命週期測試通過 |
| API 套件是否可安裝 | 沒有新增或安裝套件；虛構 adapter 與自有程式只用標準函式庫 |
| 使用者登入與 OAuth | 未執行 |
| 平台讀取 | 未執行；FakePlatform 不是平台證據 |
| 測試寫入／回覆 | 未執行；FakeSheets／FakePlatform 沒有網路 |
| 另一臺電腦驗收 | 未執行 |
| 正式公開支援 | 尚未成立；仍是本機候選實作 |
