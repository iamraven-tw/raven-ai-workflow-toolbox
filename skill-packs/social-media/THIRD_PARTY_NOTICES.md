# 第三方聲明

初始化的 `meta_user_oauth.py` 與 `instagram_facebook_oauth.py` 是自有 Python 標準函式庫實作。Instagram／Threads 官方文件、Meta 官方 Postman 與官方 SDK／fbsamples 原始碼只用來核對行為，沒有複製、下載安裝或綑綁官方範例／SDK，也沒有新增浮動版本依賴。實際依據見 [直接登入／Threads 契約](skills/social-media-setup/references/instagram-threads-oauth.md) 及 [Facebook Login 契約](skills/social-media-setup/references/instagram-facebook-login-oauth.md)。

第六技能的 `community_queue.py`、`manual_review.py`、`official_sheets_api.py` 與 `community_sheets.py` 為自有 Python 實作，不綑綁 Google／Meta SDK、Sheets 連接器或模型分類器。人工審查頁只使用 Python 標準函式庫、本包自有 HTML／CSS 與本機回環 HTTP，不下載前端框架、字型或圖示；isolated AI 目前未選用、未安裝也未呼叫。Sheets adapter 的 HTTPS transport 使用標準函式庫；選配的預設 Token provider 只會在真正執行時匯入環境已存在的 [google-auth-library-python](https://github.com/googleapis/google-auth-library-python)，本包不下載、不安裝、不複製、不重新設定 Google 憑證。缺少它時，可由既有且已授權的 Google 工作流注入等價的記憶體 Token provider，否則停止。平台與 Sheets 文件只參照官方說明與官方原始碼，沒有複製 SDK；私人來源只作行為證據，不散布其設定、憑證、品牌或排程。

本機另觀測到 [Google Workspace CLI](https://github.com/googleworkspace/cli) 0.6.0，但沒有由此技能安裝或綑綁，也未用它傳送資料。上游說明該工具仍積極開發且不是正式支援的 Google 產品；目前更新 body 需經程序引數，因此不作訪客文字的預設 transport。日後改用它或其他連接器，仍須另外完成來源、授權、秘密暴露、RAW 與型別讀回驗證。

技能檔案安裝器不綑綁、不下載，也不安裝第三方程式；只使用 Python 標準函式庫。實際專案初始化則預設提出下列 OpenCLI 準備，由 Agent 在下載前告知並依核准範圍執行。這兩個安裝階段不可混淆。憑證保存使用的 Apple Security framework 或 Microsoft WinCred API 也不是本套件散布的第三方依賴。

## OpenCLI

- 原始作者來源：[jackwener/opencli](https://github.com/jackwener/opencli)，不是 fork，也不是社群平台官方 API。
- 版本與完整性以 [固定來源契約](skills/social-media-setup/references/opencli-source.json) 為唯一依據：CLI v1.8.8、該版本 Release 的擴充功能 v1.0.24，含完整 commit／tree、LICENSE／鎖檔雜湊及 GitHub 宣告的資產 SHA-256。
- 上游 [LICENSE](https://github.com/jackwener/opencli/blob/8271afc67e8504bda94c147f446ee29775d08274/LICENSE) 為 Apache-2.0；保留授權與存在時的 NOTICE、著作權聲明。npm 相依套件保留各自授權，不宣稱全為 Apache-2.0。
- 不複製上游程式碼到公開 Toolbox。實際來源從 GitHub 取得固定 ref，再透過上游鎖檔取得 npm 相依套件；不執行未固定的 npm 全域安裝或第三方鏡像下載。
- 安裝目標、支援環境、容量、權限、費用、驗證、更新／回復／移除與可替代方案見 [初始化流程](skills/social-media-setup/references/opencli-initialization.md)。目前僅查證公開來源與契約，尚未實測下載、建置、擴充啟用或 Bridge 連線。

## HTML＋CSS、免費 SVG 與本機渲染

- HTML＋CSS 版型為 Toolbox 自有來源，只有虛構內容與 CSS 幾何形狀，沒有綑綁第三方圖示、字型或網路程式。
- 圖示參考固定為 [Tailwind Labs Heroicons v2.2.0](https://github.com/tailwindlabs/heroicons/tree/v2.2.0)，[MIT 授權](https://github.com/tailwindlabs/heroicons/blob/v2.2.0/LICENSE)，查證日期 2026-09-05。實際任務優先使用有來源的既有 SVG；若要從固定官方版本取得少數檔案，先告知並在已核准下載範圍內執行，記錄各檔雜湊及 LICENSE，不安裝 npm 套件或下載全庫。本輪沒有取得／綑綁任何圖示。
- 免費使用仍須保留著作權與授權；其他字型、素材不能套用圖示授權。外來 SVG 使用前要排除可執行／外部連線內容。
- 截圖依執行環境已有的本機渲染工具及其技能；本包不安裝瀏覽器／Playwright、不上傳私人 HTML 到線上服務，也不宣稱所有用戶端均已能輸出 PNG。原稿完成與實際截圖驗收分開。

## Pillow 與字型：只使用既有環境

- 圖片技能的文字排版與成品解碼使用 [python-pillow/Pillow](https://github.com/python-pillow/Pillow)，不是社群平台 SDK。公開包只含自己寫的 helper，沒有複製 Pillow、字型或模型。
- 候選來源記錄為 [12.3.0](https://github.com/python-pillow/Pillow/tree/12.3.0)，[該版 LICENSE](https://github.com/python-pillow/Pillow/blob/12.3.0/LICENSE) 為 MIT-CMU；Pillow 內含／連結的其他函式庫各有授權，不統稱 Apache-2.0。本輪本機測試使用既有 12.1.1 與 12.3.0；沒有下載、重裝或更新。
- manifest 明列 installable=false、existing_environment_only。缺少依賴就停止該 helper；未完成下載資產完整性與乾淨環境安裝契約，不提供無固定來源的安裝捷徑。新增安裝需另行授權。技能安裝／移除不變更既有 Pillow 或字型。
- 使用 CPU 與記憶體，不需模型帳號或推論費；畫布和頁數有本機資源上限。字型須由使用者現有環境提供並確認使用權，路徑與字型雜湊留私人紀錄；不預設所有電腦有合法可用的中文字型。測試暫用 Pillow 既有內建 Latin 字型，不能代表中文已驗收。
- AI 生圖服務、模型及權利依使用者當前可用環境另行判斷，本包不下載模型、不宣稱某個付費服務已整合或免費可用。

平台名稱與官方文件連結僅用於說明互通能力，並不表示 YouTube、Meta、Facebook、Instagram、Threads 或 Substack 背書本技能包。未來加入平台 SDK、CLI 或連接器前，必須另行記錄來源、固定版本、授權、完整性、安裝方式、是否為官方介面及可替換方案。

第七技能的 performance_review.py、performance_collect.py、metric_catalog.py 與 official_performance_api.py 均為自有 Python 標準函式庫實作，不綑綁 YouTube／Meta SDK、Substack MCP client 或第三方成效套件。metric-catalog.json 只記錄本包自己的最小口徑與官方來源連結；官方文件與 Meta 官方原始碼僅作能力證據，未複製其程式碼。HTTPS adapter 只連已列入 allowlist 的官方主機及 GET 端點；Substack 官方唯讀 MCP 的資格限制與匯出／瀏覽器備援分開揭露，匯入器只正規化已保存證據。本包不把非公開端點當正式 API，也不新增浮動 main 安裝依賴。
