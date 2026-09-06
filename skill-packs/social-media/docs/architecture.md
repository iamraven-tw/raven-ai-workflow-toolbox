# 架構

## 分層

1. 套件層保存 manifest、安裝生命週期、公開資料邊界與驗收分層。
2. 每個技能的 `SKILL.md` 保存平台無關流程。
3. 平台差異保存於該技能的 `references/platforms/`；執行多平台任務時，只讀被選取的平台文件。
4. 使用者工作區保存一般策略設定；`.local/social-media/` 保存非敏感技術狀態與憑證參照。使用者未另行指定時，秘密值預設保存在目前作業系統帳號的 macOS Keychain 或 Windows Credential Manager，不進入一般設定、參照檔與公開套件。
5. 平台整合初始化可透過執行環境既有的受控瀏覽器與正式 API，實際建立開發者 App、完成 OAuth 後讀回驗證；套件不綑綁瀏覽器工具，也不把 UI 內部請求冒充正式 API。
6. 發布由第 5 技能及平台執行文件處理，核准回覆由第 6 技能處理；任何本機產物、App 畫面或送出請求都不等於平台成功。

## 目前切片

專案初始化另有 [OpenCLI 工具準備](../skills/social-media-setup/references/opencli-initialization.md)：預設提出固定作者 GitHub 來源，下載前告知並依核准範圍由 Agent 執行；純策略討論與離線技能安裝不強制下載。這是第 1 個技能內的本機工具流程，不是第 8 個技能，不改變正式 API 優先原則。來源契約已固定，下載、建置、擴充啟用與 Browser Bridge 尚未實測。

目前有 `social-media-setup`、`social-content-planning`、`social-content-writing`、`social-image-production` 、`social-content-publishing` 、`social-community-management` 與 `social-performance-analysis` 七個本機候選技能。初始化技能能建立策略與整合意圖、檢查官方能力，並在使用者另行授權且執行環境具有必要工具時，由 Agent 操作官方後台、建立 App、設定 OAuth、把憑證保存到原生憑證庫並執行平台唯讀驗證。平台被選取後預設提出已支援核心功能的完整管理權限；使用者可在 OAuth 前刪減。Facebook、Instagram 與 Threads 可共用一次 Meta 規劃和預覽，但 App／use case、permission、OAuth、Token 與驗證仍分開。Facebook 粉絲專頁完整管理授權是第一條定義完成的 Meta 路徑；原生憑證庫只有虛構 backend 測試，真實登入、OAuth、平台讀取及所有遠端寫入均尚未驗收，因此仍是待外部驗收候選版。內容規劃的研究與確認關卡見下方第 2 個技能段落。

`PACK-01` 另保存十個逐輪虛構前向對話，涵蓋七技能觸發、一次一問、明確任務不強迫初始化、先研究後定案、只讀選取平台、草稿不發布、圖片／影片分流、公開留言／私訊與成效的分開確認。該紀錄由目前 root Agent 直接套用來源技能產生，未使用獨立模型，也未在已安裝的真實 Agent 入口執行；見[對話前測紀錄](agent-dialogue-preflight-local-verification.md)。

## 後續技能契約

### 第一技能實作與驗收邊界

| 項目 | 本機狀態 | 繼續條件 |
|---|---|---|
| 原生憑證寫入／讀回、未完成寫入恢復、刪除恢復、單程序鎖 | 已有程式與虛構 backend 測試 | 真實作業系統驗收集中留到最後 |
| 可見 Terminal 啟動、一次隱藏輸入與非敏感收據 | 已有程式與模擬啟動／取消／逾時／重複收據測試 | macOS／Windows 真實視窗及權限提示留到最後 |
| Facebook Pages HTTPS callback、state、Token 交換與保存 | 已有程式及虛構交換／權限／分頁／目標測試 | 既有受控 HTTPS callback、相容 Web server App 與真實 OAuth 留到最後；不自行部署 |
| Facebook Page Token 有效性與重新授權 | 每次取用檢查 App、scope、期限及 Page；失效停止、新 OAuth 要再確認 | 不宣稱無到期 Token 永久有效；不是 Google refresh，也不包含 Instagram／Threads |
| YouTube 後台程序、OAuth 與刷新 | 已有 Desktop loopback、PKCE、交換、refresh、保存與頻道讀回程式及虛構測試 | 真實後台、授權與 Google scope／驗證資格留到最後 |
| 跨平台中斷與不明結果 | 單次交換、先寫狀態、分段原生保存；不盲目重送 | 真實原生儲存中斷與另一臺電腦另行驗收 |
| Instagram Login／Threads 專用 OAuth | 已有各自 code 交換、長 Token、按需刷新、身分與權限證據檢查及虛構測試 | IG 官方已查資料未文件化全部當前 scope 讀回；保留初次清單並逐功能驗證，真實帳號待驗收 |
| Instagram via Facebook Login | 已有 User code／長 Token、唯一相連 Page Token、Page／IG 關係與 scope 讀回及虛構測試 | Page Token 不套用其他刷新；真實 Facebook Login、相連帳號與功能端點待驗收 |
| Facebook／Instagram 私訊 | 按需同步、不建 Webhook 的最小 MVP 已確認；獨立 queue、官方 API adapter、交易協調器與人工審查模式已有虛構測試 | 真實 App、OAuth、權限／審查、對話讀取、傳送與讀回集中留到最後；若要求即時收件，另行設計及授權公開 HTTPS 服務與部署 |

2026-09-05 已直接取得並閱讀 Meta 官方 manual flow、長期 Token、Login 安全與 Token 類型文件，補齊先前 429 所阻擋的查證。2026-09-06 再核對 Meta 官方 Instagram Login、Instagram API Postman 集合與 Insights 文件：可確認五項核心功能 scope，但已查資料沒有文件化全部當前 scope 讀回端點，因此不實作假介面。依官方 Web server code flow 實作 Facebook Pages；Google 依官方 Desktop OAuth 與官方 refresh 原始碼查證，未複製或安裝 SDK。直接來源、各 Token 差異與執行介面見 [OAuth 契約](../skills/social-media-setup/references/oauth-runtime.md)。

有程式與虛構測試的路徑為 Facebook Pages、YouTube、Instagram Login、Instagram via Facebook Login 與 Threads；[直接登入／Threads 契約](../skills/social-media-setup/references/instagram-threads-oauth.md) 及 [Facebook Login 契約](../skills/social-media-setup/references/instagram-facebook-login-oauth.md) 分別明列 Token、期限與權限證據限制。各功能端點與真實平台驗收仍分開列示，不用單一「Meta 完成」概括。

### 第二技能：先調查、再決定、再規劃

`social-content-planning` 已有本機候選主文件、調查規範、交付範本與唯讀紀錄檢查器。自身知識／歷史內容 → 五平台取樣（Meta、YouTube、X）→ 交付現況簡報 → 等待使用者方向決定 → 來源深查／行事曆／跨平台簡報。調查平台不等於發布目的地；X 只研究，Substack 可作內容目的地。

方向關卡檢查以簡報版本、交付時間、實際使用者回覆及確認時間為依據；程式只能驗證提供的紀錄，不能證明本人真的同意或內容真實。規劃產物只留私人工作區，不改一般整合設定、AI 知識庫與長期策略。沒有新增五平台搜尋 API 程式；實際搜尋使用 Agent 已提供、已獲授權的工具。

### 第三技能：文案、預覽與媒體需求

`social-content-writing` 接受核准規劃或直接改寫請求，按需讀取五份平台文案規格，產出私人本機草稿與媒體需求包。圖片、既有素材剪輯、人類錄製、AI 新影片生成分開；後兩者不自動執行。唯讀檢查器處理字元／位元組、媒體分流與文案核准雜湊，不授權發布。詳見 [本機驗證](content-writing-local-verification.md)。

### 第四技能：AI 圖片製作與文字排版備援

`social-image-production` 接收核准圖片需求或直接製圖請求，優先使用已授權 AI 生圖；沒有模型權限時以既有 Pillow／字型製作 PNG 圖卡。保存完整簡報、來源、實際尺寸與雜湊，逐張視覺檢查與整組成圖確認後才交接；不發布、不生成影片。Pillow 只作既有執行環境整合，安裝能力標示 false，不由技能安裝器下載。詳見 [本機驗證](image-production-local-verification.md)。

第四技能圖片路徑補充：schema 5 保存一次製圖偏好與品牌視覺；Codex／Antigravity 收到明確需求直接使用對應內建工具，網頁模型預設提示詞交付、當次要求才受控瀏覽器代操作，HTML＋CSS 是正式資訊密集排版路徑。分流器只讀設定、不授權工具；Pillow 保留簡單備援。舊 schema 3／4 交易相容，升級需預覽確認，不重設平台或 OAuth。`PACK-02` 已加入同內容三頁直式與方形簡報、完整網頁提示詞、安全 HTML、溢位負例及分層結果範本；只通過本機 fixture 測試，真正四路生成／渲染與看圖仍待集中驗收，見[四路驗收準備](image-acceptance-preparation-local-verification.md)。

### 第五技能：依序發布與讀回

social-content-publishing 使用一個共通流程與五份平台文件。PUB-01 已選定並實作 YouTube、Facebook、Instagram、Threads 的低階官方 API adapter；Substack 因官方 MCP 唯讀，選定由 Agent 透過已核准 OpenCLI 操作受控 Chrome。PUB-02 再以 publish_execute.py 串接 publish_job.py 的預覽綁定、互斥、去重、寫入前 claim、checkpoint、獨立讀回與 receipt；Substack 使用同一帳本的 browser handoff／claim／observation。PUB-03 再把路由下沉到平台＋格式＋變體：Facebook 影片／Reels、Threads 輪播及 Instagram 圖片影片混合輪播目前走受控瀏覽器；YouTube 影片、Facebook 一般貼文、Instagram 圖片／純圖片輪播／Reel、Threads 文字／單圖／單片才走既有 API adapter。上傳／建容器／遠端草稿也在使用者確認之後；claimed 後中斷只准讀回查明，未知結果阻擋重送與下一平台。固定限制不從舊範例硬編碼，執行時查 Graph 版本、帳號資格及可用額度。這是本機虛構整合，不代表實測完成；實測仍集中於最後。

品牌補充：一般設定最新為 schema 5，加入 brand_visual；保留 schema 3／4 原版本交易，升級仍需預覽確認。四種製圖方式共用品牌視覺，本次明確指示優先但不永久寫回。

### 第六技能：本機隔離、六欄審核與回覆

social-community-management 已建立五份平台文件、本機 queue、四平台正式 API adapter、平台交易協調器，以及 Google Sheets v4 固定 REST adapter／交易協調器。本機先篩查外部內容；語意審查最小 MVP 固定由人類在 127.0.0.1、無 JavaScript／外部資源的短期頁面完成，主 Agent 不讀頁面。人類 allow 收據綁來源雜湊後才可進六欄表；未經證明的 isolated_ai 在 queue 層停用。RAW 審核表只有六欄，技術映射、核准與狀態留本機。Sheets 流程先核對整個專用分頁空白，再 export → 單次 sheet-claim → 一次 RAW PUT → 獨立 GET／型別讀回；結果不明只讀不重送。確認可以回覆後 approve-batch 重讀 F 欄，每則 API 或瀏覽器回覆前再以 refresh_sheet=true 重讀 A:F，並核對原留言與完整自家回覆，再以 begin → 每次寫入前 claim → checkpoint → 獨立讀回 → record 執行。API／瀏覽器寫入結果 unknown 時整批先停；只有獨立 observation 找到完整同一回覆，才能綁回唯一原 claim，不重送。YouTube／Instagram 因官方留言物件缺 permalink，須由受控 Chrome 補精確網址；Substack 全程使用受控 Chrome handoff，不呼叫內部端點。Google 登入、Cloud 專案、OAuth 與 Token 保存不在本技能重做，需由既有 Google 工作流提供記憶體 Token；gws 因內容會經程序引數且上游不列為正式支援產品，不作敏感留言的預設 transport。上述整條公開留言流程已用同一虛構批次跨人工審查、Sheets 與平台協調器測試。

Facebook／Instagram 私訊採另一套獨立 queue 與狀態：只有使用者叫 Agent 時，才依 setup 的 Facebook Pages、Instagram Login 或 Instagram via Facebook Login 路徑按需同步；最多 20 個對話、各保留最近 20 則純文字，只讓最新由對方傳入且仍在 24 小時內者進本機人工頁面。私訊不進 Google Sheets；人類看過帳號、對話對象與最終文字後，仍需回到 Agent 對同一批次再次確認。傳送前重讀對話與資格，之後依 begin → message_send claim → checkpoint → 獨立 GET → receipt 執行；pending 只查同一 message ID，unknown 只允許唯一相符觀測綁回原 claim，不重送。第一版不建 Webhook、不背景監控、不排程。這條私訊流程已通過本機假 Runtime／HTTP 與虛構端到端測試，但真實人工操作、Meta App／OAuth／App Review、對話讀取、傳送、Sheets／公開留言平台及隔離 AI 均仍未實機驗收。詳見 [原始本機驗證](community-management-local-verification.md)、[留言接線驗證](community-execution-integration-local-verification.md)、[Sheets 接線驗證](community-sheets-integration-local-verification.md)、[人工審查驗證](community-review-isolation-local-verification.md)、[完整虛構串接驗證](community-end-to-end-local-verification.md)、[Meta 私訊 MVP 查證](community-direct-messaging-mvp-research.md)與[Meta 私訊本機驗證](community-direct-messaging-local-verification.md)。

### 第七技能：四週期、證據比較與策略寫回

social-performance-analysis 已建立一份共通 SKILL.md、五份平台指標文件、來源／週期／資料契約與人工確認寫回契約。metric-catalog.json／metric_catalog.py 先限制已查證的指標身分：YouTube 固定白名單與美西時區，Facebook／Instagram 依當次正式 description／period 建立可讀證據，Threads 排除 followers_count、人口統計與貼文 lifetime，Substack 核對 Admin／Bestseller MCP 或備援來源資格。official_performance_api.py 以 setup Runtime 接四平台受限單一 metric GET；performance_collect.py 保存去敏感證據並轉成 dataset，Meta 欄位說明改變會換 observed definition；Substack 則正規化官方唯讀 MCP、官方匯出或受控瀏覽器的雜湊綁定 artifact。performance_review.py 維持離線完整曆期、來源定義與證據雜湊檢查、序列內比較、報告結構、精簡策略預覽與確認後追加。YouTube 用逐日 probe 判定涵蓋；Meta 未能證明曆期完整時保留 unknown。三至五項觀察、一個策略問題、使用者判斷與再次寫入確認均保留；四週期各自的完整虛構串接見[資料到策略驗證](performance-end-to-end-local-verification.md)。其他依據見[指標目錄驗證](performance-metric-catalog-local-verification.md)、[原始本機驗證](performance-analysis-local-verification.md)與[資料來源接線驗證](performance-sources-local-verification.md)。

0.7.0 的 full_pack 是安裝結構狀態，不是全平台功能支援標章；已確認缺口與集中實機驗收政策不變。一般設定 schema 維持 5，不修改 AI 知識庫公開範本或任何私人策略。初始化、發布、互動、成效與整包本機驗證的收尾狀態統一見 [本機候選交付紀錄](local-candidate-handoff.md)；公開 Toolbox 與私人工作區維持獨立快照，不建立同步。
