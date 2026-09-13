# 社群媒體管理工作流

這是 Raven AI 一人公司工具包 的公開、平台無關社群媒體技能包。目前已建立**七個技能的本機候選版**，七份流程均已逐項說明並獲准繼續。另已由目前 root Agent 使用十個虛構回合前測一次一問、直接任務、研究關卡、平台選取及跨技能交接；這不是獨立模型或真實安裝入口驗收。流程確認與對話前測都不等於外部整合、實機驗收或正式公開支援完成；現況見 [七技能流程確認與驗收狀態](docs/workflow-review-status.md)與[虛構 Agent 對話前測](docs/agent-dialogue-preflight-local-verification.md)。

## 目前可用

- `social-media-setup`：以策略初始化或平台整合初始化兩種模式運作。選取平台後預設提出技能包已支援核心功能的完整管理權限，逐項說明並讓使用者在 OAuth 前刪減；選取 Meta 任一平台時，一併詢問是否設定 Facebook、Instagram 與 Threads。平台整合獲明確授權後，Agent 應完成可安全代辦的開發者 App、OAuth 設定與正式 API 讀回。使用者沒有另行指定時，API 憑證預設存入目前作業系統帳號的 macOS Keychain 或 Windows Credential Manager；一般設定與非敏感參照檔不含憑證值。
- `social-content-planning`：讀取自身知識與歷史內容，先調查 Facebook、Instagram、Threads、YouTube 的當前相似題材，X 作研究補充；交付總共 3–5 個代表案例與限制，讓使用者決定方向後才形成選題、內容行事曆與跨平台簡報。X 不新增為發布平台；不登入、不申請 API、不發布或建立遠端排程。流程及可調整的調查預算見 [技能主文件](skills/social-content-planning/SKILL.md)。

- `social-content-writing`：將已核准題材或直接提供的文章改寫為各平台草稿，只讀選取的平台規格；整理圖上文字、腳本與媒體需求，預覽與文案核准後才交接，不生成或發布媒體。見 [技能主文件](skills/social-content-writing/SKILL.md) 與 [本機驗證](docs/content-writing-local-verification.md)。

- `social-image-production`：初始化一次保存 Codex、Antigravity、網頁模型或 HTML＋CSS 偏好；內建工具直接生圖，網頁模型預設交提示詞、當次要求才代操作，資訊密集圖卡可直接走 HTML＋CSS／免費 SVG。四路共用品牌、繁體中文、兩種尺寸、溢位負例、完整網頁提示詞、HTML 原稿與結果紀錄 fixture 已備妥，但尚未真正生成或渲染。保存來源與成圖核准，保留 Pillow 文字備援，不發布。見 [技能主文件](skills/social-image-production/SKILL.md)、[本機驗證](docs/image-production-local-verification.md)與[四路驗收準備](docs/image-acceptance-preparation-local-verification.md)。

- `social-content-publishing`：完整預覽與發布確認後，依序使用五份平台文件，讀回網址、平台 ID、時間與狀態。YouTube、Facebook、Instagram、Threads 已有正式 API adapter 與本機交易協調器；Substack 有已核准 OpenCLI 受控 Chrome 的 handoff、寫入 claim 與 observation 紀錄契約。路由進一步依平台＋格式＋變體區分：Facebook 影片／Reels、Threads 輪播、Instagram 圖片影片混合輪播目前先走受控瀏覽器；官方文件有能力不表示本機 adapter 已實作。交易整合與格式路由只通過虛構測試，不能宣稱已完成實機發布。見 [技能主文件](skills/social-content-publishing/SKILL.md)、[執行來源驗證](docs/publishing-execution-sources-local-verification.md)、[官方規格驗證](docs/publishing-official-specs-local-verification.md) 與 [交易整合驗證](docs/publishing-transaction-integration-local-verification.md)。

- `social-community-management`：公開留言先本機隔離與固定規則篩查，由 Agent 產生摘要與草稿，直接交六欄 RAW Sheets 作唯一人工審核、使用者確認後重新讀取最終文字，再逐則回覆及驗證。YouTube、Facebook、Instagram、Threads 已有正式 API adapter 與 claim／checkpoint／讀回協調器；YouTube／Instagram 以受控瀏覽器補精確留言網址，Substack 使用受控 Chrome handoff。Facebook／Instagram 私訊另採已確認的按需 MVP：只有使用者叫 Agent 時才同步，只處理對方先發起、最新仍為對方訊息、24 小時內且純文字的對話；私訊走獨立 queue、本機人工預覽、第二次確認、單次傳送及正式讀回，不進 Google Sheets、不建 Webhook。未經證明的 isolated AI 明確停用。公開留言與私訊的完整虛構串接均已通過，但仍只是本機假 Runtime／HTTP；真實 Meta／Google 登入、App Review、Sheets、平台讀寫及人工操作未驗收。見 [技能主文件](skills/social-community-management/SKILL.md)、[Meta 私訊 MVP 查證](docs/community-direct-messaging-mvp-research.md)、[Meta 私訊本機驗證](docs/community-direct-messaging-local-verification.md)、[原始本機驗證](docs/community-management-local-verification.md)、[留言接線驗證](docs/community-execution-integration-local-verification.md)、[Sheets 接線驗證](docs/community-sheets-integration-local-verification.md)、[人工審查驗證](docs/community-review-isolation-local-verification.md)與[完整虛構串接驗證](docs/community-end-to-end-local-verification.md)。

品牌視覺設定已補齊於 schema 5：主／輔色、背景／文字色、字型、風格及 Logo／主視覺相對參考。四種製圖方式共用已確認設定；本次指示優先，單次配色不自動寫回。舊 schema 3／4 不因安裝就遷移。

## 第七技能：成效分析

`social-performance-analysis`：每週、每月、每季、每年四種回顧。YouTube、Facebook、Instagram、Threads 已有受限帳號層官方唯讀 adapter；Substack 優先以合資格官方唯讀 MCP 的已保存證據匯入，並保留官方匯出與受控瀏覽器備援。機器可讀指標目錄會先檢查 YouTube 白名單與美西時區、Facebook／Instagram 當次正式欄位說明、Threads 曆期排除項目及 Substack 來源資格；SDK 欄位存在不算可讀證據。所有來源再轉成同一私人資料契約，無完整性證據不計算成長。接著依平台角色提出三至五項觀察，只討論一個策略問題；使用者補充判斷、看過預覽並再次確認後，才追加精簡結論至私人策略檔。原始指標與逐期報告不搬進長期策略或公開套件。見 [技能主文件](skills/social-performance-analysis/SKILL.md)、[指標目錄驗證](docs/performance-metric-catalog-local-verification.md)、[資料來源接線驗證](docs/performance-sources-local-verification.md)、[四週期完整虛構驗證](docs/performance-end-to-end-local-verification.md)與[原始本機驗證](docs/performance-analysis-local-verification.md)。

候選版 0.7.0 的 full_pack 只表示七個技能納入安裝清單；Sheets REST 程式已實作，但仍依賴宿主既有且已授權的 Google OAuth／短期 Token。隔離 AI 不是目前可選功能；未來須完成 host-enforced sandbox、負向權限測試及外部資料／費用授權才會啟用。發布與公開留言回覆各有四平台 API adapter 與交易協調器，Substack 仍依賴受控瀏覽器；成效另有四平台唯讀 API adapter 與 Substack 證據正規化。這些都不是已綑綁完整平台 SDK，也不是實機發布／回覆／Sheets／成效讀取已驗收。YouTube／Instagram 留言另需要受控瀏覽器補精確 permalink；Facebook Reels 與 Threads 輪播雖有官方 API 路徑，仍因本機 adapter 或當前限制證據未完整而走受控瀏覽器。Instagram Login 的全部當前 scope 重新讀回經 2026-09-06 官方查證後列為平台證據限制：只保留初次交換清單與當前基本身分，各功能需由自己的正式端點判定。七技能流程均已確認，但不會因此自動進入真實帳號驗收。

## 本機實作與集中實機驗收

後續工作與分層驗收統一追蹤於 [待辦清單](docs/todo.md)，區分尚待實作／查證、文件對齊、選配擴充及最後集中實機驗收；列入清單不代表已授權執行。

目前七技能最小工作流的本機程式、虛構測試、對話前測、四路製圖驗收準備與整包回歸已收尾；交付狀態見 [本機候選交付紀錄](docs/local-candidate-handoff.md)。所有工具包完成後才依 [集中實機驗收手冊](docs/live-acceptance-runbook.md) 安排真實 Terminal、第三方安裝、原生憑證庫、登入／OAuth、平台讀取、測試發布與另一臺電腦驗收。手冊與空白結果範本已備妥，但未取得實機授權、未開始執行；任何本機通過都不會自動提升為下一層或正式支援。

第 2 個技能的靜態、虛構資料與安裝遷移結果，見 [本機候選驗證](docs/content-planning-local-verification.md)。選定的七技能虛構 Agent 對話案例已由目前 root Agent 完成前向測試；獨立模型、真實安裝入口與真實社群搜尋仍未執行。

本機憑證程式已補上中斷恢復、單程序鎖及可見 Terminal 隱藏輸入；Facebook Pages、YouTube、Instagram Login、Instagram via Facebook Login 與 Threads 的 OAuth 接收、交換、原生保存、有效性檢查與重新授權關卡均已提供。YouTube 與直接 Meta User Token 路徑各按自身規則刷新；Page Token 路徑只檢查失效，不套用其他刷新。五條執行路徑已有虛構測試，仍待集中實機驗收。Instagram Login 沒有使用未文件化的 scope introspection；初次授權與逐功能端點證據分開。見 [直接登入與 Threads 契約](skills/social-media-setup/references/instagram-threads-oauth.md)、[Facebook Login 契約](skills/social-media-setup/references/instagram-facebook-login-oauth.md)、[權限證據驗證](docs/instagram-current-scope-evidence-local-verification.md)及 [OAuth 共用契約](skills/social-media-setup/references/oauth-runtime.md)。

## 公開邊界

本套件只包含一般化流程、中性 schema、官方能力摘要與虛構測試。私人工作區只能作為設計證據；任何帳號、網址、品牌語氣、排程、平台識別碼、憑證位置與內容資料都不得搬入本套件。

套件內含 Apache-2.0 授權。技能安裝器不綑綁或安裝第三方套件；實際專案初始化預設準備 OpenCLI，先告知作者 GitHub、固定版本、位置與權限，在核准範圍內由 AI Agent 下載、建置與驗證。拒絕或延後仍可走其他可用路徑。此流程尚未實機驗收，詳見 [OpenCLI 初始化](skills/social-media-setup/references/opencli-initialization.md) 與 `THIRD_PARTY_NOTICES.md`。本機憑證 helper 維持只使用 Python 標準函式庫與作業系統原生介面。Windows 成效分析另需 [固定 tzdata 執行期](skills/social-performance-analysis/references/python-runtime.md)，不由技能安裝器自動安裝。

技能安裝與純策略設定不需要網路；平台整合模式若要刷新官方能力或實際連線則需要網路。登入、OAuth、建立 App、平台讀取與遠端寫入仍各自需要明確授權。共用 Meta 引導不代表三平台共用 App、OAuth、Token 或驗證結果。目前尚未完成 macOS／Windows 真實憑證寫入生命週期，也尚未完成真實 Meta 登入、App、OAuth 或平台讀取驗收。
