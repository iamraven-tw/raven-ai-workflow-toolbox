# 週期、指標及證據契約

## 四種模式

| 模式 | 預設完整期間 | 判讀重點 |
| --- | --- | --- |
| weekly | 上一個週一至下週一，不含尾日；對比再前一週 | 當週內容、近期異常與下一個小實驗 |
| monthly | 上一個曆月，對比再前一月 | 主題、型態、投入與轉換品質 |
| quarterly | 上一個曆季，對比再前一季 | 平台角色、內容組合、實驗能否延續 |
| yearly | 上一個曆年，對比再前一年 | 長期方向、資源配置與可持續性 |

季節性需要去年同期時，另列人工核對比較，不能用 helper 的相鄰期輸出冒充。不同月／季／年的天數可能不同；總數增減不是效率變化。每週也可能遇日光節約時間，日曆日相同不代表小時數相同。

使用 config 的時區作對話及報告預設，但來源如果只提供另一時區的日彙總，需清楚列出並以其時區另建資料集。不得把美西一日數據標成臺灣一日。helper periods 的 as-of 是已換算至該資料來源時區的當地日期。

API 回傳較晚、部分頁面失敗、保留期限不足：coverage 設 partial 或 unknown，不能補零後算整期成長。年度報告可用先前已合法保存的私人完整歷史或使用者匯出檔；沒有就說明缺口，不自動建立排程補存。

## Python helper 的資料格式（schema_version 1）

dataset.json 包含：

- report_id：小寫英數與連字號，不超過 64 字元；同一個策略寫回單元不可換 ID 重送。
- mode、timezone：四模式之一與有效 IANA 時區。
- period、comparison_period：各含 start、end（ISO 日期、不含尾日），本版檢查完整且相鄰的曆期。
- series：1–200 筆；每筆含唯一 key、platform、account_ref（私人帳號參照）、role（已知角色或明確暫定角色）、current、previous。
- current／previous 各含下表欄位；相同 series 表示同一平台帳號及同一觀察對象，不能把兩個帳號放在一對中。

| 欄位 | 規則 |
| --- | --- |
| metric、definition | 平台欄位名稱、定義／版本識別；定義變更必須換識別 |
| unit | 例如 count、minutes、seconds、percent；percent 用 0–100 |
| aggregation | total、unique、snapshot、average、rate |
| scope、segment | 帳號／內容集合／篩選條件的穩定識別；自然與付費、Shorts 與長片分開 |
| basis | period_activity 或 period_end_snapshot；snapshot 聚合只能配後者 |
| timezone、period | 實際來源時區及完整查詢期間，必須與資料集一致 |
| status | available、unavailable、permission_denied、read_failed、definition_changed |
| value | available 必須有限數值（零有效）；其他狀態必須 null |
| coverage | complete、partial、unknown；complete 必須有完整性證據，不是 Agent 猜測 |
| observed_at | 帶時區讀取時間，不早於期間結束且不在未來 |
| evidence_path、evidence_sha256 | 私人 performance 目錄內必要證據的相對路徑與 SHA-256 |

證據至少記錄平台、帳號參照、介面種類、查詢期間、來源時區、API 版本／UI 標籤、完整分頁狀態、取得時間與限制。請移除 Token、Cookie、訂閱者名單、簽名網址。失敗也保留已去敏感的錯誤類型證據。

程式無法證明資料來自真實官方帳號，也不自動推導 coverage、definition、scope；Agent 須用讀回結果查核。雜湊只防止預覽後資料被換掉，不是驗真章。

## 比較與摘要規則

只在 identity 欄位完全一致、雙方 available 且 complete 時算差異。平均、率、觸及不跨期相加，不用各日平均的簡單平均冒充整期加權值；有分母才另算正確加權率。快照差值只叫淨變化，不推論全部新增或流失。

前期為零或負數時不報百分比成長；百分率之差標示百分點，與相對增減分開。對平台同名 views 不假設相同；平台角色不同不評「哪平台比較差」。單篇 lifetime 與固定發布天齡的表現另列描述，MVP helper 不支援這些期間模型，不強塞成 calendar period。

## 本機命令

Agent 使用已安裝技能的實際 script 路徑。以下相對路徑以技能目錄為基準；WORKSPACE 是使用者已選的私人實體工作區。

    python3 scripts/performance_review.py periods --mode monthly --as-of 2026-09-05
    python3 scripts/performance_review.py analyze --workspace WORKSPACE --dataset social-media/performance/fictional-review/dataset.json
    python3 scripts/performance_review.py check-report --workspace WORKSPACE --dataset social-media/performance/fictional-review/dataset.json --report social-media/performance/fictional-review/report.json

前兩個命令不寫檔。數據及報告由 Agent 在使用者私人工作區建立，不在技能來源生成範例實績。

資料來源 plan、官方 API／匯入證據的建立方式與實際會寫入的私人位置另見 [成效資料來源與正規化契約](performance-source-contract.md)。來源收集是在 analyze 之前的獨立步驟；adapter 成功不會把 coverage 自動提升為 complete，也不會取代 metric 定義查證。
