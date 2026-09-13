# 社群媒體管理工作流待辦清單

更新日期：2026-09-06。依本機 manifest、技能文件與既有驗證紀錄建立；初始化與流程確認文件已對齊，但沒有執行實機驗收。

本清單不是執行授權。後續依「初始化 → 發布 → 社群互動 → 成效分析」逐項討論及處理；所有工具包完成後，才另行安排集中實機驗收。登入、App、OAuth、下載安裝、遠端寫入、排程、commit、push 與發布版本均保留各自確認關卡。

## 已有成果：不重做

- 七個技能已建立本機候選版，安裝清單完整；不等於所有執行介面或正式支援完成。
- Facebook Pages、YouTube、Instagram Login、Instagram via Facebook Login、Threads 已有 OAuth 接收、交換、原生秘密庫交接與有效性管理程式。Google 與 Meta 的更新方式分開。
- OAuth 整合已補上共用權杖生命週期契約與維護入口：需要持續維護的連線預設建立每日排程、立即驗證一次，正常無變化保持安靜；沒有已驗證排程時不得把整合標為完整完成。真實排程產品仍需在集中實機驗收中逐環境驗證。
- 發布交易護欄、四平台公開留言 API／交易協調器、Google Sheets 六欄 RAW／型別讀回協調器、留言隔離資料契約、四週期分析／人工確認策略寫回，已有本機 helper 與虛構測試。YouTube／Instagram 留言網址保留受控瀏覽器補證；Substack 留言採受控 Chrome handoff。
- 完成 `PUB-01` 後的歷史整包紀錄為 251 項測試：250 通過、1 項原生探測依政策略過。PUB-02 修改後為 258 項；PUB-03 修改後為 264 項；COM-01 修改後為 285 項；COM-02 修改後為 307 項；COM-03 修改後為 316 項；COM-04 修改後為 322 項；COM-05 修改後為 347 項；PERF-01 修改後為 361 項；PERF-02 修改後為 369 項；PERF-03 修改後為 371 項；PACK-01 修改後為 376 項；PACK-02 與 PACK-03 修改後均為 382 項：381 通過、1 項原生探測依政策略過。任何本機數字都不等於實機驗收。

依據：[manifest](../install.manifest.toml)、[七技能流程確認狀態](workflow-review-status.md)、[Instagram via Facebook Login 驗證](instagram-facebook-login-oauth-local-verification.md)、[Instagram Login 當前權限證據](instagram-current-scope-evidence-local-verification.md)、[較早 OAuth 驗證](instagram-threads-oauth-local-verification.md)、[發布驗證](content-publishing-local-verification.md)、[互動驗證](community-management-local-verification.md)、[成效驗證](performance-analysis-local-verification.md)。較早驗證文件保留當時狀態，不覆寫歷史結果。

## 一、初始化與文件對齊：本機工作已完成

- [x] **INIT-01 — Instagram via Facebook Login**：已建立明確 `login_route`、Facebook User code／長 Token 交換、完整 granted permission 核對、唯一相連 Page／IG 選取、只保存目標 Page Token、每次取用重新驗證與不明結果停止；專用契約及虛構正反例通過。真實登入、OAuth、相連帳號與功能端點仍列集中實機驗收，不納入此完成標記。
- [x] **INIT-02 — IG 當前完整權限證據**：2026-09-06 查證的 Meta 官方 Instagram Login、Postman 集合與 Insights 文件可確認五項核心 scope，但沒有文件化全部當前 scope 重新列舉介面。已把它從程式缺口改列平台證據限制：初次交換清單、當前基本身分與逐功能端點證據分開；拒絕假造 `/me/permissions`／`debug_token`，明確權限或失效錯誤停止，未知寫入不重送。真實端點仍列集中實機驗收。
- [x] **INIT-03 — 下游文件對齊新 OAuth**：發布、互動與成效三技能均改由可信 adapter 在同一程序透過 `Runtime.access()` 取用；Instagram 依 `instagram_login`／`instagram_facebook_login` 選正確 host／Token，Threads 由 debugger 核對目前 scope。三技能保留自己的確認與功能端點證據，OAuth 不冒充發布、回覆或 insights driver。較早驗證文件只追加 2026-09-06 後續狀態，沒有改寫舊結果。
- [x] **DOC-01 — 流程確認狀態對齊**：七技能均標為「流程已確認、本機候選、實機待驗」，新增單一現況文件並同步 manifest、README 與用戶端說明；較早驗證文件只追加後續狀態，不改寫建立當日結果。流程確認不替代真實 Agent、登入、OAuth、平台讀寫或正式支援驗收。

## 二、發布：確認並接好實際執行介面

目前五份平台文件共用一個交易協調器。YouTube、Facebook、Instagram、Threads 使用受限的官方 API adapter；Substack 使用受控 Chrome handoff，不建立非官方寫入 API。未綑綁 SDK 不必然需要另造一套；可用且符合契約的既有工具應優先重用。

- [x] **PUB-01 — 五平台執行接線**：YouTube、Facebook、Instagram、Threads 選定並加入受限的低階官方 API adapter，由 Agent 在 begin 後逐階段呼叫；Substack 因官方 MCP 唯讀，選定由 Agent 操作已核准 OpenCLI 的受控 Chrome。機器可讀來源表記錄格式、備援、呼叫者與缺口；四平台以假 Runtime／HTTP 驗證主機、端點、身分、Token 交接及不重送。交易護欄自動整合仍屬 PUB-02，真實平台執行留集中驗收。
- [x] **PUB-02 — 執行與本機護欄整合**：新增 `publish_execute.py`，將已核准預覽、一次性 begin、setup Runtime 憑證預檢、每次外部寫入前 claim、分階段 checkpoint、正式 GET／瀏覽器 observation、去敏感 evidence 與 receipt 接到選定工具。虛構測試涵蓋部分成功、claimed 後中斷、IG 容器續查、YouTube 308、結果不明、Substack browser handoff 及跨平台停止；不自動重送、切換介面重發或刪除。真實 Token、平台與瀏覽器仍留集中驗收。依據：[發布交易整合驗證](publishing-transaction-integration-local-verification.md)。
- [x] **PUB-03 — 官方規格缺口**：已查 YouTube Data API／Help、Meta 官方 Postman、官方 SDK 原始碼與 Facebook 影片公告，並將平台＋格式＋變體路由寫入 schema 2 能力表。Facebook 影片／Reels、Threads 輪播、Instagram 圖片影片混合輪播目前走受控瀏覽器；前兩者是「官方 API 有能力、本機 adapter 未實作」，不是平台不支援。YouTube 現有影片 API 路徑保留；Instagram／Threads 額度改為執行時讀官方 endpoint，Facebook Reels 舊限制不硬編碼。6 項新契約測試及整包 264 項離線測試通過 263 項、略過 1 項原生探測。真實版本、帳號額度、瀏覽器與發布仍留集中驗收。依據：[官方規格與格式路由驗證](publishing-official-specs-local-verification.md)。

完成標準：每個平台都有可辨識的執行來源、輸入／輸出、授權與讀回契約、停止條件和離線測試；真實發布待集中驗收。來源：[發布驗證與保留缺口](content-publishing-local-verification.md)。

## 三、社群互動：接通留言與六欄人工審核

- [x] **COM-01 — 留言擷取與回覆接線**：YouTube、Facebook、Instagram、Threads 已接受限官方 API adapter 與本機交易協調器；Substack 已接受控 Chrome handoff。每則回覆先重新核對自有貼文、原留言與完整自家回覆，再以 begin、每次 mutation 前的單次 claim、checkpoint、獨立 GET／重載 observation 與 record 執行。Threads 官方 `/replies`／`/conversation`、permalink、replied_to 與兩階段回覆已補查；IG 官方 Comment 可可靠取得 ID／timestamp，但沒有 permalink，因此留言與回覆都必須由受控瀏覽器補精確網址，YouTube 同樣保留網址補證。45 項留言針對測試與整包 285 項離線測試通過 284 項、略過 1 項原生探測。真實 Token、平台、瀏覽器與回覆仍留集中實機驗收。依據：[留言接線驗證](community-execution-integration-local-verification.md)。
- [x] **COM-02 — Google Sheets 接線**：已新增固定 `sheets.googleapis.com` 的最小 REST adapter 與交易協調器，接好整頁空白檢查、一次性 sheet-claim、六欄 RAW PUT、`userEnteredValue` 型別讀回、整列配對、approve-batch 重讀 F 欄，以及每則 API／瀏覽器回覆前 `refresh_sheet=true` 重讀。結果不明只 GET 不重送。Google 登入／OAuth／Token 保存與社群平台分開，缺授權交既有 Google 工作流；本機 `gws` 因內容經程序引數且上游不列正式支援產品，未作敏感留言預設 transport。57 項針對測試與整包 307 項離線測試通過 306 項、略過 1 項原生探測；真實 Google 帳號、Sheets 與回覆留集中實機驗收。依據：[Sheets 接線驗證](community-sheets-integration-local-verification.md)。
- [x] **COM-03 — 隔離分類器選擇**：依最小 MVP 選定本機人工審查，不啟用證據不足的 AI。已加入 127.0.0.1、無 JavaScript／外部資源的整批人工頁面，核對 loopback Host 與同源 POST；主 Agent 不讀頁面。每則決策保存 0600 收據並綁來源雜湊，allow 只取得進六欄表資格；不確定／疑似注入留隔離區。queue 固定拒絕 `isolated_ai`，日後須先證明 host-enforced sandbox、負向權限測試及外傳／費用授權才可另行啟用。9 項新增測試、76 項互動針對測試及整包 316 項離線測試通過 315 項、略過 1 項原生探測；真實使用者操作與 AI sandbox 未驗收。依據：[人工審查驗證](community-review-isolation-local-verification.md)。
- [x] **COM-04 — 完整虛構串接測試**：已用同一臨時工作區串接 fetch、固定隔離、人工 allow、六欄 RAW、F 欄改稿、對話確認、逐則回覆與完整讀回；6 項跨元件測試涵蓋風險隔離、重複、整列排序、單欄錯置、核准後競態、錯序、既有回覆、Sheets claim 中斷、回覆讀回中斷與 create unknown。測試發現並修正 unknown observation 無法綁回原 API claim 的缺口；新狀態轉換只接受 pending／unknown 與唯一未完成 claim，不重送，failed 不解鎖。82 項互動測試全數通過；整包 322 項離線測試通過 321 項、略過 1 項原生探測。真實 Agent、Sheets 與平台仍留集中實機驗收。依據：[完整虛構串接驗證](community-end-to-end-local-verification.md)。
- [x] **COM-05 — Facebook／Instagram 按需私訊 MVP**：使用者已確認兩平台皆採叫 Agent 時才同步，只處理對方先發起、最新仍為對方訊息、24 小時內且最近脈絡全為純文字的對話，第一版不建 Webhook。已建立獨立 0600 queue、三登入路徑正式 API adapter、交易協調器與人工審查模式；私訊不進 Google Sheets，完成頁預覽後仍需對同一批次再次確認。傳送前重讀資格，單次 claim／checkpoint 後獨立讀回；pending 只查同一 ID，unknown 只以唯一相符觀測解決，不重送。33 項私訊／人工針對性測試全數通過，Instagram via Facebook Login 資源交接另有 18 項通過；真實 Meta App、OAuth、App Review、對話與傳送留集中實機驗收。依據：[Meta 私訊 MVP 官方查證](community-direct-messaging-mvp-research.md)、[私訊本機驗證](community-direct-messaging-local-verification.md)。

來源：[社群互動驗證與限制](community-management-local-verification.md)。

## 四、成效分析：接入資料來源與確認口徑

- [x] **PERF-01 — 五平台資料來源**：YouTube、Facebook、Instagram、Threads 已接帳號層單一 metric 的受限官方 GET adapter；Substack 優先官方唯讀 MCP，再以官方匯出／受控瀏覽器的雜湊綁定 artifact 匯入。collector 保存平台、期間、時區、帳號範圍、metric／定義、來源、查詢、API 版本、取回時間與涵蓋，並轉成既有分析契約；手填數字、RSS 或缺原始證據的摘要不算 API 整合。YouTube 以逐日 probe 判定完整性；Meta 目前證據不足時固定 unknown。14 項新針對測試全數通過，成效技能 40 項通過；整包 361 項離線測試通過 360 項、略過 1 項原生探測。真實 API／MCP／匯出／瀏覽器讀取留集中實機驗收。依據：[資料來源接線驗證](performance-sources-local-verification.md)。
- [x] **PERF-02 — 官方指標查證缺口**：已建立 `metric-catalog.json`／`metric_catalog.py` 並接到 adapter 與 collector。YouTube 固定十項帳號層白名單、正確 unit／aggregation、America/Los_Angeles、無 filter 與逐日 probe，views／engagedViews 分開定義；Facebook 不從 SDK enum 猜 metric，強制當次 `show_description_from_api_doc`、name／period／正式說明；Instagram 同樣以當次 name／period／description 驗證；Threads 只允許五項帳號範例活動 metric，followers_count／人口統計／貼文 lifetime 改列描述；Substack artifact 核對 Admin＋Bestseller MCP 或備援來源資格，曆期 helper 只收可證明期間的三項語意指標。Meta 說明改變會換 observed definition，coverage 不因有數字升級。48 項成效針對測試全數通過；整包 369 項離線測試通過 368 項、略過 1 項原生探測。真實 Page／IG／Threads／YouTube／Substack 讀取與帳號資格仍留集中實機驗收。依據：[指標目錄與口徑驗證](performance-metric-catalog-local-verification.md)。
- [x] **PERF-03 — 資料到策略的虛構行為測試**：已讓 weekly、monthly、quarterly、yearly 各自在獨立暫存工作區，以同一結構的虛構 API 觀測走完 collector、真正零值／不可用／權限不足／讀取失敗／定義改變、四項觀察、唯一問題、人工判斷、只讀預覽、再次確認寫回與讀回。缺人類判斷、少於三項觀察、兩個問題或缺第二次確認均停止；原始數字、dataset 與逐期報告只留私人 performance 目錄，策略只追加精簡結論。新增 2 項端到端測試後，成效針對性 50 項全數通過；整包 371 項離線測試通過 370 項、略過 1 項原生探測。真實 Agent、帳號資料、私人策略與平台仍留集中實機驗收。依據：[四週期完整虛構驗證](performance-end-to-end-local-verification.md)。

來源：[成效驗證與限制](performance-analysis-local-verification.md)、[資料來源接線驗證](performance-sources-local-verification.md)。

## 五、既有技能與整包收尾

- [x] **PACK-01 — 虛構 Agent 對話前測**：目前 root Agent 完整讀取七份技能來源後，直接產生十個「使用者訊息 → Agent 回應 → 操作紀錄」前向回合，涵蓋七技能、一次一問、明確任務不強迫初始化、先交調查再定案、只讀選取平台、草稿不發布、圖片／影片正確分流，以及留言、私訊、發布與策略寫回的分開確認。5 項自動測試再核對完整回應、問題數、平台範圍及零外部動作；整包 376 項離線測試通過 375 項、略過 1 項原生探測。這是同一 Agent 的虛構前測，不是獨立模型或真實安裝入口驗收；後者仍列 `LIVE-01`。依據：[對話前測驗證](agent-dialogue-preflight-local-verification.md)、[完整對話紀錄](../tests/agent-dialogue-preflight.md)。
- [x] **PACK-02 — 四種製圖路徑驗收準備**：已建立同內容的 1080 × 1350 三頁繁體中文輪播與 1080 × 1080 方形重排簡報、四路共用品牌設定、三份無 placeholder 網頁提示詞、無 JavaScript／遠端資源的 HTML＋CSS 原稿、469 字元溢位負例及 `not_run` 分層結果範本。Codex／Antigravity 直接生成、網頁預設提示詞與當次才代操作、HTML renderer／字型／DOM 邊界、實際尺寸、逐字看圖、成圖核准及發布交接均有獨立關卡。6 項新 fixture 測試及 43 項圖片／安裝相關測試全數通過；整包 382 項離線測試通過 381 項、略過 1 項原生探測。真正模型生成、瀏覽器操作、環境渲染與真人視覺驗收仍留集中實機驗收。依據：[四路驗收準備](image-acceptance-preparation-local-verification.md)、[圖片原始驗證](image-production-local-verification.md)。
- [x] **PACK-03 — 修改後回歸**：已在目前工作樹重新執行套件靜態／Python／Markdown 相對連結／公開隱私與授權邊界、7／7 技能格式、失效 symlink、差異格式、13 項隔離安裝／更新／回復／移除，以及全部 382 項虛構測試；結果為 381 通過、1 項原生憑證實機探測依集中驗收政策略過。沒有沿用舊數字，也沒有接觸真實 Agent、私人工作區或平台。依據：[完整本機回歸](package-regression-local-verification.md)。
- [x] **PACK-04 — 候選狀態與交付整理**：已同步 manifest、README、安裝、架構、流程現況、用戶端證據與驗收分層，並新增單一 [本機候選交付紀錄](local-candidate-handoff.md)。較早驗證文件只追加後續狀態；其他技能包及根目錄的無關修改均保留。公開與私人工作區維持獨立快照，沒有建立同步；沒有登入、安裝第三方工具、外部寫入、commit、push 或發布。

## 六、集中實機驗收：所有工具包完成後，另行授權

執行前使用 [集中實機驗收手冊](live-acceptance-runbook.md) 逐層確認前置條件、當次授權、成功證據與停止條件，並從[空白結果範本](live-acceptance-result-template.json)建立該次私人驗收紀錄。手冊與範本已備妥，但所有項目仍是 `not_run`；準備文件不構成任何實機或外部操作授權。

- [ ] **LIVE-01 — 本機技能發現**：在宣告支援的真實 Agent 入口測試七技能發現、資源載入與對話行為；既有第一技能 Codex 證據不延伸成全部用戶端通過。
- [ ] **LIVE-02 — 第三方工具／套件安裝**：先告知 OpenCLI 作者 GitHub、固定版本及影響，再測下載、完整性、建置、擴充、Bridge、更新／回復／移除。缺少的 Pillow／字型或其他依賴先決定是否提供安裝契約；不因技能檔案可安裝就宣稱 API 套件可安裝。
- [ ] **LIVE-03 — 原生秘密庫**：macOS Keychain 與 Windows Credential Manager 分別驗證可見 Terminal 隱藏輸入、保存、跨程序讀取、中斷恢復與另行確認的刪除；確認秘密不進對話、命令列、一般設定或日誌。
- [ ] **LIVE-04 — 使用者登入與 OAuth**：逐條驗證 App 設定、使用者刪減權限、同意、HTTPS callback、交換、帳號核對、刷新、撤權／到期與重新授權；不以其中一條成功代表全部平台成功。
- [ ] **LIVE-05 — 平台讀取**：分別驗證公開題材搜尋、帳號／貼文、公開留言、成效與缺值狀態；Facebook／Instagram／Threads／YouTube 為主要研究平台，X 僅研究補充。試算表讀取另記結果。
- [ ] **LIVE-06 — 外部寫入與完整流程**：取得各項明確授權後，測發布及逐平台讀回、六欄 RAW 審核與確認後回覆、另行核准的私訊功能，以及私人策略的預覽確認寫回。測試寄信、排程或清理測試內容均須另外確認，不當成附帶操作。
- [ ] **LIVE-07 — 另一臺電腦**：在乾淨且獲授權的第二環境驗證安裝、依賴、平台連線與功能；包含 Windows 權限／檔案原子替換等未驗證行為，不複製維護者私人設定。
- [ ] **LIVE-08 — 正式公開支援與發行**：依實際證據逐項決定可宣告的支援範圍；檢查公開資料、依賴與授權。commit、push、版本標記及發布逐一另行授權，未通過項目保留候選或不支援。

## 七、不自動擴大 MVP

下列是既有文件揭露的範圍限制，不因出現在待辦文件就變成全部必做：

- Stories、Notes、直播、Substack 影片／Podcast、Threads 串文、既有貼文修改／刪除與排程。
- 留言隱藏／刪除／封鎖、非頂層留言、Chat、付費留言與自動解鎖重發。
- 去年同期、固定貼文天齡、lifetime、未完成期間及跨資料集合併分析。
- 廣告、付款帳務、企業成員、商品目錄／商店等延伸管理。

- [x] **SCOPE-01 — 條件式擴充政策已固定，目前未觸發**：每次只在真實需求出現時說明現有替代方式、必要官方查證、依賴、權限與測試成本，再決定納入或延後；本輪沒有以補齊清單為理由擴大既有最小工作流。完成標記只代表政策已落實，不代表上列功能已實作。
