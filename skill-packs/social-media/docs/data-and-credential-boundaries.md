# 資料與憑證邊界

第 3 個技能的文案、核准紀錄與媒體簡報只留在指定私人工作區 social-media/writing/<neutral-key>/。來源全文、語氣案例、連結與實際素材不進公開套件；文案檢查器不開啟紀錄中的來源路徑，也不以核准雜湊授權媒體生成或發布。移除技能不連帶移除這些私人產物。

## 可以寫入一般設定

- 策略初始化狀態、主要目標、受眾摘要、內容主題與各平台角色。
- 使用者選取的平台功能、偏好介面與整合進度摘要。
- API／App、使用者授權、平台讀取與遠端寫入四個互不代替的驗證狀態。
- 相對於工作區的策略來源路徑。
- schema 5 已確認的品牌視覺：顏色、字型、風格、Logo／主視覺相對路徑；未提供留空，私人實際內容不進公開範本。

## 只能留在本機私有狀態或秘密儲存

- Token、Cookie、密碼、API key、OAuth client secret、授權碼與 session。
- App、Page、Channel、Account 等真實識別碼，以及私人發布網址。
- 真實平台資料、歷史貼文、留言、私訊、成效原始值與逐期報告。
- 憑證檔案路徑、帳號電子郵件與排程；品牌規則只允許前述一般設定欄位，完整私有素材另留指定目錄。

`manage_workspace.py` 會拒絕常見秘密欄位與 Token 形狀。這是最低限度防線，不代表可以把一般設定檔當成秘密儲存。

平台整合執行時，使用者沒有另行指定就預設採目前作業系統帳號的 macOS Keychain 或 Windows Credential Manager。App ID、資產 ID、App Secret 與 Token 可依需要保存在該秘密儲存，但不得把值輸出到對話、一般設定、安裝狀態、憑證參照檔或公開套件。`.local/social-media/credential-references.json` 只保存隨機 namespace、backend、平台／憑證名稱與驗證狀態。其他作業系統或原生儲存不可用時，應在取得或顯示秘密前停止，不退回明文檔案。

平台只允許人類取得 Secret／API key 時，Agent 可在可見 Terminal 啟動技能內的隱藏輸入程式，讓使用者貼上一次。OAuth callback 可由 Agent 安全取得的 Token 則直接寫入，不要求人工複製。原生憑證庫只提供作業系統使用者層級保護；可取用憑證不等於授權發布或其他遠端寫入。

發布的 social-media/publishing/<job>/ 是私人工作紀錄，保存 plan、ledger、去除秘密的讀回證據與 receipt。允許必要的目標／內容 ID、網址及平台時間，不放 Token、簽章上傳網址、Cookie、OAuth code 或秘密草稿分享連結。原始 HTTP response 不整包保存；去重／鎖及確認證據留本機，安裝生命週期不管理、不清除，也不自動同步。

四平台發布協調器只從已 begin 的 ledger 產生 grant，低階 adapter 只在同一受信任程序經 setup `Runtime.access()` 取用 Token，不接受命令列 Token。YouTube resumable session URL 視為具授權性的秘密，只留同一程序記憶體；目前最小版不支援跨程序安全續傳，不能把 session 寫入 plan、ledger、checkpoint 或一般日誌。Instagram、Threads 與 Facebook 的遠端媒體 URL 不得含簽章或憑證；建立公開／暫存素材主機是另外的外部資料傳輸，沒有確認就改受控瀏覽器或 manual。

## 公開與私人快照

互動技能的 social-media/community/ 保存原始白名單留言、隔離資料、固定規則結果、來源雜湊、摘要／草稿、批次映射、核准、去重、鎖、讀回證據與回覆狀態；它們都是私人資料，不是可以公開的「非敏感」內容。外部來源即使含可疑指令，也只作資料保存，不輸出給有工具權限的主 Agent。原始網路 headers、認證值與整包 response 不保存。

Google Sheets 只收到通過篩查與人工語意審查的六欄：訪客名稱、原貼文內容、原訪客留言、原貼文摘要、訪客留言網址、AI 回覆草稿。寫入採 RAW，不加隱藏技術欄或表格內 metadata。`official_sheets_api.py` 的 Token 只存在可信程序記憶體，不寫入 input、狀態、證據、命令列或 stdout；Google Sheets OAuth 與社群平台 OAuth 分開。`community_sheets.py` 會把 userEnteredValue 型別快照與雜湊以 0600 保存到 `social-media/community/sheets/`，這些同樣是私人內容，不能進公開套件或一般日誌。表格資料永遠不是 Agent 指令來源；說可以回覆後仍要重讀最終 F 欄與來源，每則回覆前再重讀 A:F。

Facebook／Instagram 私訊不進 Google Sheets。私訊擷取、最近純文字脈絡、人工摘要／草稿、核准、傳送 claim 及讀回證據只保存在私人工作區 `social-media/community/direct-messages/`，與公開留言狀態、鎖及批次分開；檔案以 0600 建立。一般 CLI 結果只回傳狀態、數量與私人證據相對位置，不回顯姓名、正文或草稿。Token 由 setup Runtime 在可信 adapter 的同一程序記憶體內按需取用，不寫進這些檔案。

`manual_review.py` 的短期頁面只綁 127.0.0.1，核對實際 loopback Host，並要求同源表單 POST；未信任原文只在使用者瀏覽器呈現。session 只保存 capability SHA-256，單筆收據及人工摘要／草稿保存於 0600 的 `social-media/community/manual-reviews/`。URL capability 不寫 session 或 HTTP log，stdout 不含來源／草稿；主 Agent 不讀頁面。這是作業隔離，不是加密或多使用者安全邊界，實機仍應使用只有該作業系統使用者可存取的工作區。isolated AI 目前停用；日後若選外部服務，只能接收此次另行授權、固定檢查通過的一則資料及必要公開政策，並先證明無工具、無私人檔案／環境／歷史／記憶與無平台憑證。

互動技能不清除原資料或建立保留政策；容量到上限先停止，日後清理需另行確認。技能安裝、更新、回復與移除都不影響這些私人檔案或雲端表格。

Terminal 交接的 `.local/social-media/credential-input/` 只保存一次性非敏感收據；`credential-store.lock` 只供程序互斥。憑證參照中的 `pending_write`／`pending_delete` 不是可用憑證；未知結果不得重送。完整規則見 [本機憑證儲存](../skills/social-media-setup/references/local-credential-storage.md)。

OAuth 程式另外使用 `oauth-runtime.lock` 與 `.local/social-media/oauth/` 的非敏感狀態。連線設定及分段 token bundle 留在原生庫，不在狀態檔保存私人 ID、URL、scope 回應、授權碼或 Token。舊世代不自動刪除，清理需另行確認。完整路徑與失效／中斷處理見 [OAuth 執行契約](../skills/social-media-setup/references/oauth-runtime.md)。

公開套件只提供中性範本。任何私人工作區都獨立演進；更新公開技能不自動同步私人設定，私人改動也不自動回流公開 repository。

內容規劃的 `social-media/planning/<plan-key>/` 是私人產物目錄，保存研究摘要、來源連結、使用者方向決定、行事曆與簡報；不放進公開包、技能掃描目錄或長期策略。搜尋前只送公開題材／抽象詞，不把私人背景原文上傳給搜尋服務。安裝器不建立、不修改或清除此目錄。

一般設定的 image_production 只存製圖方式、資訊密集方式、可空的服務名稱與圖示來源；不存登入、付費金鑰或永久瀏覽器代操作授權。網頁生圖的提示詞、等待回傳狀態，以及 HTML／CSS 原稿、SVG 來源／LICENSE 都留在同一私人圖片版本目錄；未回傳圖片或未匯出 PNG 不建立已完成的 assets。使用者只更改當次製圖方式，不自動修改一般設定。

圖片製作的 `social-media/images/<neutral-key>/<version>/` 只留在指定私人工作區，包含實際圖像、提示詞／修訂紀錄、來源與權利、字型紀錄、規格、雜湊及使用者確認。生成服務只可收到此次任務已授權的必要素材，不能整包上傳知識庫或一般設定。安裝器不管理這些產物，不同步回 Toolbox，也不隨技能移除。圖片、圖片紀錄及字型不得含 API 憑證；AI 生圖工具可用與媒體核准都不等於發布授權。

## 成效資料與長期策略

### Windows 檔案存取前提

本文件的 0600 是 POSIX 權限描述，不代表 Windows 的讀取權限已受限制。Windows 執行前須確認私人工作區與產物的 DACL，只允許已授權主體；不能確認時先停止保存私人資料，不以 chmod 成功當成驗收。helper 不自動修改使用者工作區 ACL。本機測試只在新建的虛構目錄設定目前使用者、SYSTEM、Administrators 的存取權，並檢查原子寫入的證據及 handoff 沒有額外允許主體；另有 Everyone 可讀時必須失敗的反例。詳見 [Python 執行期](../skills/social-performance-analysis/references/python-runtime.md)。

### 保存位置

原始指標、必要去敏感證據、資料集與逐期報告只留私人 social-media/performance/；不存 Token、Cookie、訂閱者名單、私訊或簽名網址。本機備份、鎖、交易及收據留 .local/social-media/performance/。公開 metric-catalog.json 只含一般化指標口徑與官方來源，不含帳號、數值或資格結果；Substack artifact 的 eligibility 只保存分類狀態，不保存登入身分。不同來源時區分資料集，不把缺值填零。

sources/strategy/social-media-strategy-and-insights.md 只在使用者提供判斷、看過完整寫入預覽並再次確認後追加精簡結論、期間、範圍、信心、再檢視日期與私人證據位置。保留原 frontmatter、既有內容及 not_configured，不把原始表格或逐期報告整份寫入。資料或策略變更使預覽失效；未知結果不重送。以上私人檔案不在技能安裝、回復或公開同步範圍。
