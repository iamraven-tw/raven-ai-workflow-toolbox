# 人工討論與策略寫回

## 逐期報告與兩個人類關卡

先顯示有依據的三至五項觀察，然後只問一個策略問題。收到使用者的判斷後，才形成策略預覽；第二次明確確認只針對預覽的實際文字。不能把「資料可以讀」「看起來合理」或「繼續分析」推定為允許寫策略。

私人 report.json 格式：

- schema_version：1；report_id 與 dataset 一致；dataset_sha256 是該資料檔實際 bytes 雜湊。
- observations：3–5 筆；每筆 id、series_keys（至少一個存在序列）、fact、inference、limitations。不同觀察可以引用相同序列，但不得重複湊數。
- questions：恰好一個字串；內容也只能問一個主要決策，不把問卷塞成長句。
- asked_at：實際提問的帶時區時間。
- human：討論前可為 null；收到使用者回應後填 response、conversation_ref（私人對話參照）、received_at。
- insight：討論前可為 null；預覽前必須只含 conclusion、user_judgment、scope、confidence（low／medium／high）、recheck_on、observation_ids。

fact、inference、limitations 必須清楚分開；未知原因寫未知。insight 只保留有適用範圍的精簡結論與使用者補充，不存原始表格、逐人資料、全部觀察或完整對話。使用者判斷若與資料不一致，忠實記錄不同意見與限制，不把判斷改寫成證實因果。

## 預覽與寫入

    python3 scripts/performance_review.py preview --workspace WORKSPACE --dataset social-media/performance/fictional-review/dataset.json --report social-media/performance/fictional-review/report.json

preview 不寫任何檔案。顯示 target、creates_file 與完整 append_text；向使用者解釋是追加而非覆蓋。保留回傳的 preview_sha256，等使用者看完明確確認後才執行：

    python3 scripts/performance_review.py apply --workspace WORKSPACE --dataset social-media/performance/fictional-review/dataset.json --report social-media/performance/fictional-review/report.json --preview-sha256 PREVIEW_HASH --confirm-write

helper 不會驗證對話身分；confirm-write 只是技術護欄，Agent 必須先取得真實確認，不得自行替使用者打勾。預覽後改報告、策略或證據，原確認失效，重新預覽與確認。

本版保留原策略所有 bytes、frontmatter、既有洞察及 not_configured；只追加一段有期間、結論、人類判斷、範圍、信心、再檢視與證據位置的紀錄。檔案不存在時，預覽需明示建立；不複製公開 AI 知識庫骨架或擅自重設其他設定。不同來源時區的資料集各自預覽；本版不做跨資料集合併交易。

## 備份、鎖與結果不明

寫回前保存原策略與 transaction，原子替換策略後逐字讀回，最後保存 receipt。備份及交易位於 .local/social-media/performance/。重複 report_id、既有鎖、缺收據交易、預覽過期均停止。

程序中斷後不能刪鎖就盲目重跑。先確認沒有仍執行中的程序，人工比對 transaction 的 before_sha256、after_sha256 與實際目標：

- 目標符合 after：可能已寫入，不再追加；保留證據，另行確認修復收據。
- 目標符合 before：可能尚未寫入；保留備份，另行確認恢復，不沿用舊確認。
- 都不符合：已有其他修改或未知狀態，停止並請使用者決定。

helper 不自動清除殘留鎖、覆蓋備份或還原策略。鎖只協調本 helper；不控制其他編輯器，寫回前後仍需確認沒有其他程序同時改檔。POSIX 檔案使用限制權限，Windows ACL 與跨電腦行為另待驗收。
