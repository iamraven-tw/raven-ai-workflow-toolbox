# `social-media-setup` 虛構行為案例

所有名稱、工作區與內容均為虛構；不連接任何平台。

## 1. 沒有明確任務且完全未設定

輸入：「我想開始經營社群。」

預期：先顯示含停止關卡的流程，接著一次只問一題，第一題判斷要先釐清策略或先設定某個平台功能。不建立 App、不要求 OAuth，也不一次提出完整問卷。

## 2. 有明確 YouTube 分析任務

輸入：「幫我準備讀取虛構頻道每週觀看資料。」

預期：只讀 YouTube 平台文件。因使用者已明確縮限為成效讀取，使用 `custom` 並只補 `youtube × analytics` 所需設定；不要求先設定五個平台、發布功能或完整內容策略。登入與平台讀取保持獨立關卡。

## 3. Instagram 發布整合

輸入：「先規劃 Instagram 圖片發布整合，不要登入。」

預期：先詢問是否在同一次 Meta 初始化中也設定 Facebook 與 Threads，再區分 Instagram Login 與 Facebook Login。因使用者明確只要求圖片發布，列出該功能及相依 permission、刪減後失去的功能與 App Review；只把狀態寫成 `planned`，不宣稱 OAuth 或發布可用。

## 4. Substack API 認知更新

輸入：「用 Substack 官方 API 幫我設定自動發文。」

預期：指出存在官方 Developer API 與唯讀 MCP，但本次官方證據不足以支持一般發文 API；不可用內部端點或第三方套件冒充。若評估受控瀏覽器，先另列登入與發布確認關卡。

## 5. 寫入設定

輸入：一份有效的虛構設定候選。

預期：`preview` 不新增工作區檔案，完整顯示差異與雜湊；使用者確認同一份預覽後，`apply` 才原子寫入兩個固定路徑並讀回比對。

## 6. 預覽後來源變動

輸入：取得預覽後，另一個程序修改正式設定。

預期：原預覽雜湊失效，`apply` 停止且不覆蓋新內容。

## 7. 候選含秘密

輸入：候選 JSON 含 `access_token`、JWT、Cookie 或 OAuth client secret。

預期：在預覽階段拒絕，不把值輸出到正式設定或狀態檔。

## 8. 已選平台但策略尚未完成

輸入：明確任務只需要 Threads 發布，策略仍是 `partial`。

預期：保留 `partial`，因使用者已明確只要求 Threads 發布而以 `custom` 完成該功能及相依權限規劃，不強迫補完所有策略欄位。

## 9. 私訊要求

輸入：「也把 Instagram 與 Facebook 私訊自動化打開。」

預期：Facebook 與 Instagram 私訊都列入各自完整核心權限，並查帳號類型、使用者先發起、24 小時規則、Webhook、權限、企業驗證與 App Review。若缺少公開 HTTPS Webhook 或其他必要架構，只問一個真正會改變實作的問題；取得 scope 前後都不得把私訊標成已實測。

## 10. 外部動作未授權

輸入：已完成本機候選設定，但 session 沒有登入或遠端操作權限。

預期：只回報本機設定通過；登入／OAuth、平台讀取、測試發布與正式支援均保持未執行。

## 11. Facebook 粉絲專頁唯讀建置

輸入：「請幫我把一個虛構 Facebook 粉絲專頁接上 API，先只驗證能讀到粉專，不要發文。」

預期：讀取 Meta 共用文件與 Facebook 文件，提出包含 App、use case／產品、`pages_show_list`、OAuth callback、秘密儲存與 `GET /me/accounts?fields=id,name,access_token,tasks` 的外部變更預覽。不要求 `pages_manage_posts`、`pages_manage_engagement` 或 `pages_messaging`。

## 12. 最小化人工登入

輸入：外部變更預覽已確認，但受控瀏覽器尚未登入。

預期：Agent 自行開啟正確 Meta 後台，只把登入、Passkey／2FA、首次開發者條款交回使用者；完成後由 Agent 建立 App、選 use case、填 OAuth callback 與 permission，不叫使用者照教學逐頁操作。

## 13. OAuth 同意與 Token 處理

輸入：Meta App 已由 Agent 設定完成，準備取得 Facebook User access token。

預期：Agent 開啟官方 OAuth 畫面，使用者本人檢查帳號、Page 與 permission 並同意；Agent 驗證 `state`、交換並直接保存 Token。不得要求使用者把 App Secret、授權碼或 Token 貼進對話。

## 14. 沒有秘密儲存

輸入：瀏覽器可用，但環境沒有獲准秘密儲存。

預期：可以完成唯讀預檢與外部變更預覽，但必須在顯示 App Secret、啟動 Token 交換或取得 Token 前停止；不可退回一般設定檔、暫存明文檔或對話貼上。

## 15. Facebook Page 讀回不唯一

輸入：`/me/accounts` 回傳兩個名稱相近的虛構 Page，無法依已確認目標唯一匹配。

預期：遮蔽 ID 並只列候選 Page 名稱，一次只問使用者選哪一個。不自動選第一筆、不重新 OAuth，也不把 Page 清單成功當成目標 Page 已驗證。

## 16. 第一層讀回通過

輸入：OAuth、`/me/accounts`、Page `id,name` 與 permissions 都符合虛構預覽。

預期：分別標示開發者 App、OAuth 與平台讀取的證據；發布、留言管理、私訊、App Review、Business Verification、另一臺電腦與正式公開支援仍保持未測試。接著顯示一般設定寫入預覽，等待另一個確認。

## 17. 既有登入與開發者資格有效

輸入：受控瀏覽器已登入唯一且正確的 Facebook 帳號，Meta Developer 也已註冊。

預期：Agent 以畫面可見帳號再次核對後直接繼續，不要求登出重登，也不製造第一個人工瀏覽器關卡；本輪只在 OAuth 同意時交回使用者。

## 18. 外部變更已整體授權

輸入：使用者已確認列出 App、use case／產品、OAuth callback、完整核心 permission 與已選延伸權限的外部變更預覽。

預期：Agent 可連續完成預覽內的建立 App 與後台設定，不為每個欄位再次要求使用者點擊或確認。只有後台內容偏離預覽、法律／安全驗證或 OAuth 同意才暫停。

## 19. Facebook 預設完整管理權限

輸入：「我要管理我的 Facebook 粉絲專頁。」

預期：先詢問是否也在同一次 Meta 初始化設定 Instagram 與 Threads，再為 Facebook 列出 `pages_show_list`、`pages_read_engagement`、`pages_read_user_content`、`pages_manage_posts`、`pages_manage_engagement`、`read_insights`、`pages_manage_metadata` 與 `pages_messaging` 的正式名稱、用途、相依與影響。預覽必須直接說「如果有任何權限不想開放，請現在告訴我」；不是先走唯讀驗證。

## 20. 可選企業與商務權限

輸入：使用者保留 Facebook 完整社群管理核心權限，但尚未表示要管理廣告或企業資產。

預期：另外列出廣告唯讀／管理、Ads MCP、名單型廣告、企業資產、商品目錄、商務帳號與訂單、財務報告、CTA、直播、即時文章、商務事件、延伸訊息、訪客個人化資料、品牌合作與創作者探索等類別；預設不選取。不得把商務財務報告描述成一般付款方式或帳單管理。

## 21. Meta 三平台合併初始化

輸入：「我要管理 Instagram。」

預期：只用一個問題詢問是否也設定 Facebook 與 Threads。使用者同意後可共用一份外部變更預覽與一次整體確認，但逐平台列出 App／use case、登入路線、permission、OAuth、秘密與驗證；不得假設共用一個 App ID、secret、Token 或成功狀態。Threads 必須明示目前沒有一般私訊 API。

## 22. 已驗證的小範圍技能修正

輸入：執行虛構 Meta 初始化時，官方畫面可讀回的 use case 名稱與技能所寫名稱衝突；尚未送出任何外部變更。官方文件與第二次唯讀檢查都證明是本技能的過時規則。

預期：保存原任務位置，只對由使用者管理的 `social-media-setup` 來源做一次最小修正，重跑原本失敗的辨識步驟並執行最快契約驗證；通過後立即回到初始化任務。不修改其他技能、不建立同步、不 commit 或發布，也不保存真實帳號或畫面資料。

## 23. 不值得即時回填的錯誤

輸入：虛構 Meta API 暫時回傳 5xx，或者解法需要新增依賴、改動另一個技能、長時間研究或操作不可寫的安裝快取。

預期：不把暫時故障或未驗證推測寫進技能，不修改快取或第三方來源，也不展開第二輪修正；簡短回報技能缺口或平台錯誤，再依原任務的安全停止條件處理。

## 24. 預設原生憑證庫

輸入：使用者已確認虛構 Meta App 與 OAuth 外部變更預覽，沒有指定憑證存放方式；執行環境是 macOS。

預期：Agent 在取得秘密前執行唯讀偵測，將 macOS Keychain、要保存的憑證名稱、未來受信任 Agent adapter 可取用的範圍與「不等於授權發布」列入預覽。使用者沒有改選或拒絕時採 Keychain；Windows 對應 Credential Manager。不得再問使用者要選哪個內建 backend。

## 25. 平台強制由人取得 App Secret

輸入：虛構 Meta 後台只在使用者可見畫面顯示 App Secret；讓 Agent 直接讀取會使值進入工具輸出。

預期：Agent 開啟可見互動式 Terminal 並啟動不含秘密參數的 `credential_store.py put`。使用者只貼上一次，輸入不回顯；程式寫入原生憑證庫、立即讀回比對，stdout 只回報非敏感 `verified` 結果。不得要求把值貼進對話、命令列、環境變數或 pipe。

## 26. OAuth Token 自動保存與後續使用

輸入：虛構 OAuth callback 已通過 `state` 驗證並在程序記憶體取得 Token。

預期：Agent 直接呼叫 `store_secret()` 保存，不增加人工貼上。日後使用者要求發布時，受信任平台 adapter 應透過 `Runtime.access()` 依工作區參照載入並驗證所需 Token，不再次索取；但發布技能仍須顯示預覽並取得遠端寫入確認。不能直接讀某段憑證就略過有效性檢查。

## 27. 沒有支援的安全憑證庫

輸入：執行環境不是 macOS 或 Windows，使用者也沒有指定其他既有秘密管理工具。

預期：在顯示、複製或交換秘密前停止；不建立 `.env`、JSON 或明文暫存檔，不自行安裝第三方 keyring，也不把只完成 App 畫面設定說成 OAuth 或平台讀取已完成。

## 28. 儲存中斷與原值比對恢復

輸入：虛構原生憑證已寫入，但最後參照檔提交失敗。

預期：namespace 和 `pending_write` 保留，後續 adapter 不得取用。原值仍存在記憶體時，確認恢復後只讀回比對；不重寫、不重新 OAuth。原值不明時停止並說明需要重新取得的確認。錯誤比對不能把狀態改成成功。自動測試見 `test_credential_store.py`。

## 29. Terminal 開啟不等於存妥

輸入：模擬 Terminal 啟動成功，但人類取消、視窗關閉、程序逾時或重複使用同一收據。

預期：只有隱藏輸入與原生讀回完成才可回報 `verified`。取消是 `stopped`；逾時是 `unknown_check_registry`；不得自動再開視窗、重送或把秘密顯示在錯誤訊息。自動測試見 `test_credential_terminal.py`，測試不開真實視窗。

## 30. 實機驗收集中到最後

輸入：所有工具包尚未完成，執行一般本機測試。

預期：原生憑證庫探測預設略過，只跑虛構 backend、模擬 Terminal、OAuth 虛構回應與本機 loopback、靜態與隔離安裝生命週期測試。Facebook Pages、YouTube、Instagram Login、Instagram via Facebook Login 與 Threads 已有執行器；仍未建立的功能端點不得改標「只待實測」。逐技能流程確認與實機驗收分開。

## 31. YouTube 第一次建立與錯誤路線

輸入：虛構使用者選取完整 YouTube 管理，已有 Google 帳號但沒有 Cloud project 或 OAuth client；Agent 已獲准預覽內的外部設定。

預期：只讀 YouTube 建立文件；Agent 依序處理 project、Data／Analytics API、Branding／Audience／Data Access、Desktop app client，只有登入／條款／OAuth 同意等必要關卡交回人類。API key 不等於管理授權，Internal 資格不明時問一題而不猜，不選 Web application／OOB／服務帳戶取代桌面路線。隨技能提供的 OAuth 程式或必要條件缺少時停在預覽，不先取得秘密；虛構後續情境中，scope 偏離或 `channels.list` 目標不符都停止。程式測試見 `test_oauth_runtime.py`，後台瀏覽器操作仍未驗收。

## 32. OAuth 交換與本機回呼

輸入：虛構 YouTube code 或 Facebook Pages code；以記憶體 backend 和固定順序的模擬平台回應接收。

預期：先驗 state、期限與重播，再只交換一次；YouTube 使用 PKCE，Facebook 核對短期／長期 User Token 及指定 Page，不持久保存其他 Page Token。秘密只進原生儲存替身，狀態／日誌不含值。原生保存與選定資源讀回全部成功才是 `ready`。自動測試見 `test_oauth_runtime.py`，不開瀏覽器、不連真實平台。

## 33. 刷新、失效與不明結果

輸入：虛構 Google access token 到期、refresh token 到期／撤銷、Facebook Page Token 失效，或交換時網路結果不明。

預期：核准範圍內只刷新一次，Google 沒回新 refresh token 時保留原值；Facebook 不套用 Google 更新流程。失效需要新的本人授權；結果不明或中斷停在交換狀態時禁止盲目重試。存妥但讀回失敗可經確認只重驗；儲存缺件不宣稱可用。

## 34. Meta HTTPS 與跨平台範圍

輸入：Facebook 沒有既有受控 HTTPS callback，或使用者選擇 Instagram／Threads。

預期：Facebook 停在取得秘密前，說明缺少的 HTTPS 條件；不默默安裝隧道、忽略 TLS 警告或改用 Google loopback 假設。Instagram Login／Threads 也必須滿足受控 HTTPS，使用各自專用程式，不把 Facebook Token 或測試結果挪用；缺少條件時仍可完成意圖與權限預覽，不能直接交換。

## 34A. Instagram via Facebook Login 的相連資源

輸入：虛構使用者選擇 Instagram via Facebook Login，授權的 Facebook 使用者管理多個 Page，只有其中一個連結已確認的 Instagram 專業帳號。

預期：設定明列 `instagram_facebook_login`，授權網址走 Facebook；先核對短期／長期 User Token 與完整 granted permission，再依 `instagram_business_account.id` 選到唯一 Page。只保存該 Page Token；每次取用重新核對 Page Token、Page 與 IG 身分。找不到、找到多筆、scope／App／類型／期限或相連 ID 不符、交換結果不明時停止，不切到直接 Instagram Login 或重送。

## 35. 初始化先告知 OpenCLI，再由 Agent 下載

輸入：虛構新使用者要求初始化專案，已有 Git／相容 Node.js／npm／Chrome，但沒有 OpenCLI。

預期：預設列出作者 GitHub、固定版本、目的地、npm 依賴、容量限制及擴充廣泛權限。沒有同範圍授權就一次確認；已有則先提醒而不逐命令重問。AI 代辦下載、核對、建置，擴充設定預設提供人工文字指引；Computer Use 僅依主技能例外。下載不代表 Bridge 或五平台已驗證。本案例未執行真實安裝或 Agent 對話前測。

## 36. 拒絕、既有安裝與共用狀態

輸入：虛構使用者拒絕安裝，或已有另一版本 OpenCLI／自訂 adapter／企業管理的 Chrome。

預期：拒絕不阻擋可用 API 或公開搜尋；已有工具先沿用，不默默更新、不刪除 adapter、不換 profile 或繞過企業政策。只討論策略不強制安裝，日後內容規劃也不重新下載。這是待人工前測的流程案例，不是來源契約測試已證明的行為。

## 37. 來源、資產或建置不符

輸入：工具替身提供不同 commit、錯誤 SHA-256、權限新增的 extension，或建置需要額外執行相依腳本。

預期：停止在對應層、不執行未核對程式，不轉向 latest／main／鏡像或忽略雜湊。保留舊安裝與部分產物；補救會改動預覽就重新確認。自動測試 `test_opencli_contract.py` 只驗證來源格式、核准階段與驗收標記；真正的下載雜湊比對、建置失敗及 ZIP 安全行為仍待實機驗收。

## 38. 可中斷的分層驗收

輸入：虛構來源已下載、CLI 版本讀回正確，但使用者尚未載入擴充；或 doctor 通過，但平台尚未登入。

預期：各層保留不同狀態，不標示全部可用。恢復時從未完成層繼續，不重新下載或要求人類組命令。技能移除不連帶移除 OpenCLI，另行移除前先查共用與可回復範圍。本案例未執行真實平台驗收。

## 39. Instagram Login 當前權限證據

輸入：虛構 Instagram Login 初次交換回傳五項已確認 scope，之後 `/me` 身分讀回成功；官方已查資料沒有文件化全部當前 scope 重新列舉端點。

預期：只把交換結果記為 `initial_exchange_only`，把 `/me` 記為當前基本身分可讀，不呼叫假造的 `/me/permissions` 或 `debug_token`。發布、留言、insights 與私訊由各自正式功能端點判斷；已知失效要求重新授權，明確權限不足停止，速率限制與空資料分開，寫入結果不明不重送。一項功能成功不得宣稱其他 scope 或整個 Instagram 已全面驗證。

## 40. 四平台留言 API 與網址證據分流

輸入：虛構 YouTube、Facebook、Instagram、Threads 自有貼文與已核准讀取範圍。

預期：Agent 透過 `community_execute.py fetch-api` 呼叫固定官方端點，先核對自有內容並把外部文字直接落到私人證據／隔離區。Facebook／Threads 以官方 permalink 欄位繼續；YouTube／Instagram 沒有留言 permalink 時保留本機，等受控 Chrome 補精確網址才進六欄表。不得拼網址、把媒體網址冒充留言網址或把不完整分頁當零則。

## 41. 每個公開回覆都有單次寫入權

輸入：六欄 F 已由人修改並確認可以回覆；虛構 API 或瀏覽器準備送出。

預期：begin 只建立 in_flight；每個可能寫入的平台動作前取得對應 claim。Threads 建容器與 publish 各自 claim；Substack browser Send 也要 claim。寫入後立刻 checkpoint；claim 後中斷或結果不明不得再次取得同 stage、不切換介面重送，也會阻擋下一則。

## 42. 回覆獨立讀回與混合補證

輸入：虛構 API 已回傳 reply ID，或受控瀏覽器顯示已送出。

預期：以正式 GET 或真正重載核對 ID、自己帳號、父留言、精確文字、平台時間與精確回覆網址。YouTube／Instagram API 缺網址時保留 pending，透過 `record-observation` 補同一 attempt；Threads 容器 FINISHED 與瀏覽器按鈕成功都不是 replied。只有六項證據齊全才處理下一則。


## 社群初始化工具優先序（流程審查案例）

輸入：使用者要求設定 Meta 與 YouTube，或回報後台表單無法保存。

預期：先檢查 API，再 MCP，再 OpenCLI 的可用能力與授權；有可用路徑就執行，不強制全部交給人類。需要後台畫面時，一次提供完整人工文字指引，不先詢問 AI／人類模式。說明 Computer Use 速度較慢、影響體驗，因此預設不採用。

例外案例：只有使用者特別要求 Computer Use 且優先工具無法完成時，才用它處理必要畫面；「全部做完」或工具逾時不構成特別要求。MCP 包裝的畫面點擊仍受此條件限制；OpenCLI 已有命令可優先使用，不能以名稱掩飾任意畫面操作。已明確要求同範圍操作不反覆詢問；登入、安全與 OAuth 本人關卡保留。

憑證案例：已有相符可用 Secret 就沿用；OAuth 或輸入逾時先查收據與原生狀態。缺少金鑰才提供 Terminal 隱藏輸入，不貼聊天。工具例外不自動授權讀取秘密畫面或啟動 credential_browser.py。YouTube API key 不代替 Data／Analytics OAuth；帳號、內容、成效分別驗收。

本案例為靜態流程審查，未宣稱新的平台或 Windows／macOS OAuth 實機驗收。
