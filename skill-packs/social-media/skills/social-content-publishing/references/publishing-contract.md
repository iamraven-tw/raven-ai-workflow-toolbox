# 發布交易與執行契約

## 分工與最小範圍

Agent 是執行者；五份平台文件定義操作差異，`publish_job.py` 處理檢查、雜湊、鎖、一次性階段 claim 與結果紀錄，`official_publish_api.py` 提供 YouTube、Facebook、Instagram、Threads 的低階正式 API 請求，`publish_execute.py` 負責從已 begin 的 ledger 產生 grant、先驗證 setup Runtime、依序呼叫低階 adapter、checkpoint、讀回及形成 receipt。低階 adapter 仍不自行判斷人類是否真的同意；Agent 必須以對話中的真實確認參照執行 begin。Substack 只採受控瀏覽器或手動路徑，不存在套件自造的寫入 API。

目前支援整理全新的貼文／媒體立即發布；YouTube、Facebook、Substack 可走文件列出的原生排程。IG／Threads 不建立等待發布的本機服務；需要排程先交本機計畫並回報未實作。另有 Facebook 同 App 貼文文字修改，沿用同一帳本，不另建工作流。其他內容修改／刪除、草稿另存、留言、私訊、Notes、Stories、直播仍未放進這份交易。Substack 的編輯器自動保存只是發布交易中的中間狀態，不代表獨立草稿功能已驗收。

### Facebook 文字修改

`action=update_content`、`platform=facebook`、`interface=official_api`、`format=text`、`title=""`、`assets=[]`、`scheduled_at=null`。`body` 是完整新文案；settings 只含 `post_id`、`before_message`、`before_updated_time`，後兩者來自先前已授權唯讀查詢，原樣保存平台值。向使用者呈現確切貼文與新舊內容，再沿用 preview → begin → execute-api；`--confirm-publish` 是共用歷史旗標，此處只允許已核准修改，不能用原本發布核准代替。

執行器重新核對專頁、建立貼文的 application 與目前連線 App ID、pages_manage_posts，以及原文／更新時間未變。缺欄或別人已修改即停止；這不是平台原子條件更新，查驗至送出間仍可能有並行修改。每次只 POST message，不改媒體、連結、可見性或排程。寫後獨立 GET 文案、網址與 updated_time，相符才記 `updated`；不足記 pending，未知結果不重送。修改前快照與指定 post ID 一起納入預覽及去重，不沿用新貼文的文案去重規則。

官方：[專頁貼文更新與同 App 限制](https://developers.facebook.com/documentation/pages-api/posts)。程式與虛構測試已建立，未執行真實修改。其他平台及刪除仍不可套用這個 action。

## plan.json：由 AI 填，人類看成品預覽

根欄位固定 schema_version=1、job_id（小寫英數與連字號）、items（依執行順序，最多 20 項）。每項固定：

- id、platform（五平台）、target_label（易讀帳號名稱）、target_id（真實執行時核對的資源識別）、target_url（HTTPS 帳號／刊物網址）。
- interface：official_api、official_connector、reliable_cli、controlled_browser、computer_use 或 manual。工具不足改 manual，要改回可執行介面必須新預覽。manual 的 begin 只記 awaiting_manual／manual_only，不允許 Agent 發布；使用者自行操作後可用 record 保存獨立讀回證據。
- format：youtube=video；facebook=text／image／carousel／video；instagram=image／carousel／reel；threads=text／image／carousel／video；substack=article。文件對特定影片介面的缺口仍優先，不是格式通過就保證可發布。
- title、body（完整最終文字）、assets（有序列表）。每個 asset 是 path（工作區相對路徑）、sha256、alt_text。主影片、縮圖、字幕與附圖的用途另外列 settings，不把不同檔誤當多張貼圖。檔案路徑、內容或順序改變都需新預覽。
- action=publish_now 或 native_schedule；scheduled_at 為有時區的 ISO 時間或 null。排程須在確認和實際執行時仍是未來；settings 另列人看得懂的時區。
- settings：物件，由平台文件定義這次的可見性、格式選項、通知／寄信、素材來源與上傳位置等，沒有認證資訊。未知且影響結果的設定不得略過。
- review_ref：實際內容／媒體核准對話參照；unresolved 必須為空陣列。來源與權利證據可在 settings 列私人相對參照；不是重新驗證這些證據的程式替代品。

輸入是本機私密資料但不是憑證保管處。不要保存 OAuth callback、帶簽章的上傳網址、Authorization、Cookie、秘密草稿連結、原始網路 response。大型影片以分塊計算雜湊，不整片載入記憶體。

## 本機命令

以下 <...> 全是佔位符，由 AI 使用私人實際資料替換，不請人照抄；所有 plan／observation 路徑相對 --workspace。

    python3 scripts/publish_job.py preview --workspace <workspace> --plan social-media/publishing/<job>/plan.json
    python3 scripts/publish_job.py begin --workspace <workspace> --plan social-media/publishing/<job>/plan.json --item <id> --preview-sha256 <digest> --approval-ref <真實使用者確認參照> --confirm-publish
    python3 scripts/publish_execute.py execute-api --workspace <workspace> --plan social-media/publishing/<job>/plan.json --item <id> --connection <name> --execute-external-write
    python3 scripts/publish_execute.py prepare-browser --workspace <workspace> --plan social-media/publishing/<job>/plan.json --item <id>
    python3 scripts/publish_execute.py claim-browser --workspace <workspace> --plan social-media/publishing/<job>/plan.json --item <id>
    python3 scripts/publish_execute.py record-observation --workspace <workspace> --plan social-media/publishing/<job>/plan.json --item <id> --observation social-media/publishing/<job>/observation.json

preview 唯讀回傳完整內容與預覽雜湊；begin 綁定整份 plan、素材與工作區。命令列旗標僅防誤觸，真實對話確認由 Agent 負責，不能用布林值冒充。begin 成功後才能從已核准介面執行一次，不得先上傳再補紀錄。`execute-api` 的旗標表示 Agent 明確要進入帳本已核准的外部寫入，不是新的人類同意，也不能跳過 begin。每項在 ledger.json 只有一次 begin；跨 job 相同目的地／文案／素材也阻擋。跨程序互斥鎖只保護本機交易，不會讓平台支援冪等。

協調器在每個非冪等寫入之前先以 ledger `claim` 唯一占用該階段，取得安全容器／貼文 ID 後立即 checkpoint。程序若死在兩者之間，下一次只記 unknown 並轉唯讀查明；不會再呼叫一次同一 POST。Instagram／Threads 已保存容器 ID 且仍處理中時，可以重新執行協調器，但只 GET 同一容器；完成後才 claim 尚未呼叫過的 publish 階段。YouTube resumable session URI 可能具授權性，只留同一程序記憶體，帳本只記 `sensitive-reference-memory-only`；308 或程序中斷後不建立第二個 session，目前最小版不提供跨程序續傳。低階 `claim`／`checkpoint` 命令是協調器內部契約，日常不由 Agent 手動拼接。

## API 執行輸入

共同的文字、標題與本機素材仍來自 item；`settings` 只放非敏感且已顯示在預覽的平台選項。協調器目前接受：

- YouTube：category_id、tags、privacy_status、notify_subscribers、made_for_kids、contains_synthetic_media；可另帶 default_language、embeddable、license、public_stats_viewable。原生排程由 action／scheduled_at 轉成 private＋publishAt。
- Facebook：visibility；需要時另帶 link、依 assets 順序排列的 media_urls。圖片先以 published=false 建立，全部取得 ID 後才組成單一 feed；video 尚未進 API 路徑。
- Instagram：依 assets 順序排列的 media_urls；Reel 可帶 share_to_feed。輪播逐子容器 checkpoint，再建立父容器。
- Threads：文字不用 media_urls；單圖／單片使用一筆 media_urls，可另帶 reply_control、link_attachment、topic_tag、is_spoiler_media。輪播尚未進 API 路徑。

media_urls 必須是已在預覽中揭露、平台可取得且不含簽章或憑證的 HTTPS 來源；協調器不代建圖床、不公開本機檔案。`allow_token_refresh` 不是平台成品選項，不放 settings；預設允許 setup Runtime 在既有 scope 內按官方流程更新一次有效憑證，不能新增 scope 或換帳號。若預檢失敗，會在任何發布 claim 前停止，修復既有連線後可再預檢。

## receipt.json 與狀態

欄位固定：

- item_id、target_id：必須與計畫完全一致。
- state：published、scheduled、pending、unknown 或 failed。
- platform_id、url、platform_time：成功狀態必填；其他可 null。URL 必須是平台實際讀回的 HTTPS 網址，不能憑空組合宣稱已驗證。Substack 自訂網域須與預覽 target_url 主機相同。
- observed_at：實際讀回時間，含時區。platform_time 為平台發布時間；scheduled 時為平台讀回的預定時間，不能當成已發布的實際時間。若只有觀測時間或相對「剛剛」、缺平台 ID，記 pending，不猜補。
- content_matches、media_matches：與已確認內容逐項比對的布林值。
- settings_readback：讀回核對的平台設定；成功時必須與 plan.settings 相同。這是 Agent 正規化後的結果，不是把 request 直接當 response；無法驗證就 pending。
- evidence_path、evidence_sha256：私人工作區內已去除秘密的 GET 選取欄位／重新載入畫面證據及檔案雜湊。不得拿送出請求截圖或原始 secrets dump 充數。

Agent 必須先確實讀回，再建立 receipt；helper 只能證明文件完整與匹配，不能辨別假造證據。published 的時間不得晚於 observed_at；排程時間要與要求的時刻一致。pending／unknown／failed 都阻擋後續平台，狀態檔保留已完成部分。

已有未知結果只允許更新唯讀查明的 receipt，不可重送、刪 ledger、換 job_id 或切瀏覽器再發。即使確認平台拒絕也不自動重試；修正後先說明原因與重複風險，另請使用者決定，MVP 不提供解鎖重發命令。已成功項不可改寫成失敗；也不自動撤文作「回復」。

第一項 begin 後整份 plan 已鎖定，不原地改稿。如果使用者要改尚未開始的其他項目，保留原 ledger，只把未執行項形成新 job 與新預覽／確認；不得包含已執行或未知項。尚未有任何 begin 時，部分平台核准則直接縮小 plan 再預覽確認。

## 可信執行介面與秘密

API 執行器需鎖定官方主機與 endpoint、避免將憑證傳到重導向／任意媒體主機、逾時不得自動 retry 非冪等 POST，輸出白名單欄位。setup 的 `oauth_http.py` 只允許 OAuth 與身分／權限讀回端點，不能拿來發布；四平台由 `OfficialAPIAdapter` 在同一程序經 `Runtime.access()` 取用 Token，`publish_execute.py` 只從 ledger 建 grant，沒有 Token 參數。可信 adapter 沒有可用且已授權的發布介面時，停下或改走經確認的 UI／手動路徑。

可靠 CLI 先查實際已安裝版本與 help／唯讀能力，不猜命令、不自動升級。OpenCLI 是作者的第三方開源工具，不是 Meta、Google 或 Substack 官方 API。需要下載依 setup 的來源告知與確認，不在發布中偷裝。瀏覽器使用環境指定的 Agent 專用瀏覽器及橋接工具；不得讀取 Cookie、密碼或把安全驗證交給 AI。Computer Use 仍受相同帳號、預覽及停止邊界限制。
