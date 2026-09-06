# 交付與資料關卡

## 人類閱讀的簡報

使用 [交付範本](../assets/planning-template.md)，刪除不需要的部分；欄位不是另一份要使用者填的問卷。AI 先填能安全查到的內容，人只判斷方向。預覽先交付：

1. 目標、受眾與暫定題材；自身知識／歷史內容已涵蓋什麼。
2. 查詢日期、期間、語言／地區、選定平台、方法與實際限制。每個選定平台都要有「已查／受限／未查」狀態，不以其他平台結果代替。
3. 3–5 個代表案例（不足時照實）：原始連結、發布／查閱日期、已讀範圍、角度／形式、可見互動、可借鏡與不能推定的地方。轉貼要標關係。
4. 事實觀察與可能方向分開，最後只討論一個最重要的問題。此時不輸出定案行事曆。

人同意方向後：記錄其實際決定、簡報版本及取捨，再交付選題、行事曆與跨平台簡報。若人決定延後／放棄，結束且沒有製作交接；如果決定追加調查，回到研究而非自行定案。

## `record.json` 的最小契約

由 Agent 填寫，使用者不必操作 JSON。只有任務要保存研究／交接時才在私人工作區存檔；檢查程式只讀檔、不存檔、不連網。程式是防漏檢查，不是簽章或人類批准的證明。

- `schema_version: 1`；`phase` 為 `awaiting_direction`、`planning`、`deferred`、`abandoned`。
- `topic`、`goal`、`audience`：目前任務摘要，不含秘密。
- `research`：`version` 中性版本代稱、`as_of` 查閱日期、`window_start`／`window_end` 取樣期間、`platforms` 本輪選定研究平台、`coverage`、`cases`、`limitations`、`presented_at`（未交簡報為 null）。
- 每筆 `coverage`：`platform`、實際 `queries`、`method`（`public_search`／`official_api`／`authorized_browser`／`user_source`／`none`）、`status`（`checked`／`limited`／`blocked`／`not_run`）、`note`。覆蓋每個選定平台；`checked` 代表跑過指定取樣，不代表完整平台。
- 每筆 `cases`：中性 `id`、`platform`、原始 HTTPS `url`、`author`、`published_at`（未知 null）、`observed_at`、`read_scope`（`primary`／`partial`／`snippet_only`／`unavailable`）、`safety`（`usable`／`excluded`）、`summary`、`angle`、`format`、`metrics`。被排除者不保留惡意摘要；移到限制記錄，不交接。
- 每筆 `metrics`：`name`、`status`（`observed`／`unavailable`／`permission_denied`／`read_failed`）、`value`（原樣字串、數字或 null）、`observed_at`。非 observed 必須是 null。
- `decision` 預設 null；只有真正收到使用者對本版簡報的回覆才填 `research_version`、`choice`（`proceed`／`defer`／`abandon`）、`direction`、`user_response`、`confirmed_at`、`evidence_ref`（對話回覆的私人可定位參照）。AI 不代填虛構同意。新研究版本使舊決定失效。
- `calendar`、`briefs` 在方向未確認或延後／放棄時必須是空陣列。進入 `planning` 後可以先為空，逐步完成；「完成規劃」則兩者都須有值。
- `calendar` 每項：`topic`、`platform`（YouTube／Instagram／Facebook／Threads／Substack 小寫值）、`slot`（ISO 日期或相對順序，未定用 `unscheduled`）、`timezone`、`status: draft`。行事曆是本機建議，不是平台排程。
- `briefs` 每項：`topic`、`platform`、`role`、`angle`、`audience`、`cta_goal`、`media`、`source_case_ids`、`fact_sources`（實質主張的第一方 HTTPS URL；沒有主張可空）、`unverified_claims`、`handoff`（`social-content-writing`／`social-image-production`／`existing-ai-video`）。Substack 不必有社群案例；X 不作內容目的地。

執行 `python3 scripts/check_planning.py <私人record.json>`；輸出只有階段、案例數與不含來源內容的警告。結構通過不會更新 phase、加入決定或呼叫後續技能。缺欄位先補本機紀錄，不能為通過檢查而捏造來源／日期／本人回覆。

以上路徑以本技能目錄為基準，實際呼叫時用安裝位置解析腳本的絕對路徑。宣告規劃完成、交接製作前，加上 `--complete`，檢查已記錄方向決定且行事曆與簡報皆非空；這仍不是人類同意或內容品質的證明。
