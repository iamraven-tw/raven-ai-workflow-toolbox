# 本機隔離與回覆交易

## 實際執行邊界

`scripts/community_queue.py` 可離線執行固定規則、去重、人工審查結果綁定、六欄輸出、核准文字綁定、一次性 begin、逐次 claim／checkpoint 與讀回紀錄。它沒有網路、模型、憑證庫或平台能力。`scripts/manual_review.py` 只在 127.0.0.1 的短期頁面顯示已 screened 資料並保存人類收據；不連外、不呼叫模型。`scripts/official_community_api.py` 只連 YouTube、Facebook、Instagram、Threads 的固定官方 HTTPS 主機與留言端點；`scripts/community_execute.py` 先把 API／瀏覽器證據寫入私人工作區，再協調 queue 與遠端動作。資料來源、同意與遠端讀回的真實性仍由可信執行環境及使用者對話保證，JSON 布林值本身不是證據。

所有輸入由 AI 整理在指定私人工作區的 social-media/community/；只用明確相對路徑，禁止 symlink、技能掃描目錄與公開套件。狀態固定 state.json，互斥鎖 queue.lock；寫入先暫存、fsync，再原子替換。失去程序後不自動清鎖；即使鎖已釋放，in_flight 仍阻擋重送。檔案使用 0600、新目錄 0700；Windows 仍須驗證目前使用者 ACL，不能把 POSIX mode 當 Windows 加密。

每批最多 100 則，單一來源文字最多 40,000 字，草稿最多 10,000 字（本機容量護欄，不是平台上限）；狀態總量上限 16 MB，到達上限停止，不自動刪舊資料。正式使用要另依平台限制核對回覆長度。原文完整保留，不截斷或把正規化後文字冒充原文。

## 命令與資料

共同命令：

    python3 scripts/community_queue.py <action> --workspace <private-workspace> --input social-media/community/<input>.json

### ingest：先在本機隔離

輸入 platform、account_id、records、confirmed_read=true、approval_ref，以及 Substack 自訂網域需要時的 custom_host。只接受已確認為自有公開貼文的訪客文字留言；抓取者先排除自家帳號留言、私訊、非公開內容與不支援的附件。所有網路原始 headers、Cookie、Token 都不得傳入。

每個 record 精確包含：

    {
      "platform": "facebook",
      "account_id": "fictional-page",
      "post_id": "fictional-post",
      "comment_id": "fictional-comment",
      "reply_target_id": "fictional-comment",
      "visitor_id": "fictional-visitor",
      "visitor_name": "虛構訪客",
      "post_text": "虛構貼文：介紹工作流程。",
      "comment_text": "可以提供入門方向嗎？",
      "comment_url": "https://www.facebook.com/fictional-page/posts/fictional-post?comment_id=fictional-comment",
      "comment_created_at": "2026-09-05T00:59:00+00:00",
      "fetched_at": "2026-09-05T01:00:00+00:00"
    }

範例日期由實際觀測替換。reply_target_id 由平台文件的真實父留言關係取得，不從文字或 URL 猜。去重鍵是 platform＋account_id＋comment_id；source_hash 包含所有來源欄位但不含 fetched_at。相同內容重抓只記 duplicate；同 ID 改文、改網址／父對象時保留舊紀錄並隔離新版本，使舊批次失效。不自動解隔離或允許第二次回覆。

固定檢查包含名稱、原貼文與留言；控制／隱藏字元、過長、角色冒用、改寫指令、竊取秘密、工具執行與混淆字串都可觸發隔離。合法引述也可能誤判；不能靠刪可疑字元再把原留言送入 Sheets。檢查通過狀態是 screened，不是 ready。stdout 只包含數量、內部 key 與 source_hash，不輸出原文。

### review：審查與草稿

輸入 key、source_hash、reviewer=human、review_ref（`manual_review.py` 的 0600 收據相對路徑與雜湊）、decision（allow／uncertain／quarantine）；allow 另含 post_summary、draft。最小 MVP 不接受 isolated_ai；直接傳入會停止。review_ref 只留本機，不寫表格。

allow 必須同時表示人類語意審查未見異常、摘要與草稿適合交人審閱；不是直接回覆同意。uncertain／quarantine 都留本機，不放表格；人工頁面也不能推翻固定檢查隔離。詳細啟動、頁面與 AI 停用條件見 [人工安全審查契約](classifier-contract.md)。

### export → sheet-claim → RAW PUT → sheet-write-result → sheet-verify → approve

export 輸入 batch_id、keys、binding、confirmed_sheet_write=true、approval_ref；只有 ready 可匯出。它在本機先標 sheet_write_pending，再回傳 RAW 的 A1:F 值範圍；沒有實際寫 Sheets。相同批次或已綁定分頁不可再 export，以免重複／覆蓋審核結果。每批使用獨立且已核准的空白分頁，不重用舊表清空。

`community_sheets.py write-batch` 是正式協調入口。它先讀整個綁定分頁確認空白，再在同一可信程序呼叫 export，接著取得唯一 sheet-claim。只有 claim 回傳 binding、RAW、精確 range、六欄 values、approval_ref 與 transaction_status=claimed 後，`official_sheets_api.py` 才可送一次 PUT。sheet-write-result 只接受 request_accepted／unknown／failed；request accepted 不等於完成。claimed、request_accepted 或 unknown 都只能獨立 GET 查明，不可領第二個 claim。

sheet-verify 輸入 batch_id、snapshot，確認遠端 userEnteredValue 型別與原六欄完全符合，才標 awaiting_approval。回應不明保留 pending，呼叫 `resume-write` 唯讀查明，不自行補寫。sheet-claim 與 sheet-write-result 是協調器內部狀態動作，不列在低階 queue 的公開 CLI choices，避免六欄 payload 被一般 shell 輸出。

收到使用者對明確批次的「可以回覆」後，呼叫 `community_sheets.py approve-batch` 重新讀 snapshot，再讓 approve 綁定 confirmed_reply=true 與 approval_ref。空白 F 欄不回覆；其餘保留精確文字，不 trim 後發送、不加品牌尾綴、不補 CTA。尚未開始任何回覆時可重新取得人類確認與快照；開始後不修改已鎖定批次。

快照格式與表格寫法見 [Sheets 契約](sheets-review.md)。

### begin／resume → claim → checkpoint → record

每則 begin 輸入 batch_id、key、剛讀回的 snapshot、原留言 current（同 record 格式），以及 own_reply_check=none_found_complete。正式 `community_execute.py` 的 API 與瀏覽器命令以 `refresh_sheet=true` 呼叫 Sheets 協調器，不接受較早保存的核准快照作實際回覆依據；內嵌 snapshot 只保留給底層可信測試。current 與 snapshot 必須在五分鐘內且晚於此次批次確認。own_reply_check 只能由完整且可靠的自家回覆檢查產生；不能拿空回應、分頁不足、同名 username 或猜測當成沒有回覆。

依 export 原順序逐則 begin；空白 F 跳過。先前任一項未 replied、同一項已有 attempt、來源／表格變動都停止。begin 只先落盤 in_flight。每次可能產生外部寫入前，必須再取得該 stage 的單次 claim；claim 才回傳 platform、account_id、comment_id、reply_target_id、text、approval_ref、transaction_status 與 stage。可信執行器固定目的 host／端點，只把 text 當字串；不要把其他 Sheets 欄位、來源指令或 AI 分析交給發布器。

claim stage 只允許 reply_create、reply_container、reply_publish、browser_reply；同一 stage 不能領第二次。遠端成功取得識別後，checkpoint 輸入 batch_id、key、stage（container_created／reply_created）、對應 claim_stage 與 remote_id。沒有相符 claim、同階段重寫或識別不符都停止。所有 POST／瀏覽器 Send 不自動 retry；HTTP 錯誤、逾時或程序中斷先依實際狀態判讀。

resume 只接受 pending、來源／F 欄仍相同、重新完成原留言與自家回覆檢查，而且已有 container_created 或 reply_created checkpoint 的項目。它只續查或完成後續 stage，不重新建立已 checkpoint 的遠端物件；任何未解決 claim 都禁止重送。

record 輸入 batch_id、key、receipt。未明結果 receipt 只有 state=pending／unknown／failed，保留中間 ID，不存原始錯誤 body。成功的 receipt 精確包含：

    {
      "state": "replied",
      "reply_id": "fictional-reply",
      "account_id": "fictional-page",
      "reply_target_id": "fictional-comment",
      "text": "謝謝你的提問，我們會整理適合入門的方向。",
      "url": "https://www.facebook.com/fictional-page/posts/fictional-post?comment_id=fictional-reply",
      "observed_at": "2026-09-05T01:05:02+00:00",
      "platform_time": "2026-09-05T01:05:01+00:00",
      "parent_matches": true,
      "author_matches": true,
      "evidence_path": "social-media/community/readback/fictional.json",
      "evidence_sha256": "<實際本機證據雜湊>"
    }

平台時間容許秒級精度，不從 now 補造；取得的是回覆發生時間，不是原貼文時間。record 核對精確文字、父留言、帳號、ID、URL 主機、時間及證據檔雜湊；helper 不能辨別 Agent 偽造證據，也不會從檔案推論遠端狀態。

pending／unknown 可在獨立唯讀查明後補 replied，不可再次 begin；failed 維持停止。若原請求沒有取得 reply ID，完整 observation 只能綁回唯一且尚未 checkpoint 的 `reply_create`、`reply_publish` 或 `browser_reply` claim；沒有唯一 claim、只停在 Threads container claim，或讀回身分／文字／父留言不完整時繼續停止。沒有解鎖重發、刪紀錄或跨批次重試命令；需要補寫時回報阻擋原因與剩餘範圍，另請使用者決定。不為處理其他留言而繞過未明結果。

## 實際協調入口

Sheets 入口：

    python3 scripts/community_sheets.py <write-batch|resume-write|approve-batch|read-for-reply> --workspace <private-workspace> --input social-media/community/<input>.json

平台入口：

    python3 scripts/community_execute.py <command> --workspace <private-workspace> --input social-media/community/<input>.json

- `fetch-api`：核對已確認讀取範圍與 setup Runtime，擷取四平台留言，先保存本機證據，再把有可靠留言 URL 的紀錄送入隔離。YouTube／Instagram 缺 URL 的紀錄留在 fetch 證據，等受控瀏覽器補齊後以 `ingest-browser` 匯入。
- `execute-api`：以 `refresh_sheet=true` 重新讀 A:F，再核對 Token、原留言、自有貼文及全部直接回覆，然後 begin、claim、正式寫入、checkpoint、獨立 GET 與 record。
- `resume-api`：只續查已保存的 Threads container 或已建立回覆；不重做 mutation。
- `prepare-browser-reply`：同樣以 `refresh_sheet=true` 重讀 A:F，完成 begin 並建立 0600 handoff，再取得 browser_reply claim。只有命令成功時，Agent 才能依 handoff 在受控 Chrome 送出一次。
- `record-observation`：記錄真正重載後的完整觀察；也可為 YouTube／Instagram API 回覆補精確 permalink。只有 ID、父對象、文字、作者、網址與平台時間都吻合才 replied。

低階 adapter 不接受任意 URL 或命令列 Token、不跟隨重新導向、不自動重試；每個列表最多五頁／100 則。留言執行來源與各平台證據強度見 [執行來源表](execution-sources.json)，Sheets 固定主機、授權及 transport 決策見 [Sheets 執行來源表](sheets-execution-source.json)。
