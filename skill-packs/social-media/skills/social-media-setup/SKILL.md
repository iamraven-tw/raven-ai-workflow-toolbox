---
name: social-media-setup
description: "建立或調整社群媒體工作流的策略與平台整合。當使用者要開始社群經營、設定策略、選擇 YouTube、Instagram、Facebook、Threads 或 Substack、檢視完整功能權限、實際建立開發者 App／API／OAuth、驗證平台讀取，或檢查目前設定時使用。平台後台一律由人類依文字指引操作，不使用 Computer Use；平台整合預設提出該平台已支援核心功能的完整權限，逐項說明並允許使用者在 OAuth 前刪減；沒有明確決策時一次只問一個最重要的問題。"
---

# 社群媒體工作流設定

以「策略初始化」或「平台整合初始化」處理目前需求。不要強迫使用者一次完成全部設定，也不要因尚未完整初始化而阻擋明確任務。

## 責任

- 盤點既有一般設定、策略來源與已選功能。
- 實際初始化選取 YouTube 時，預設將 Data API 與 Analytics API 一起設定，供選題規劃與成效分析共用；依 [YouTube 初始化與共用驗收](references/youtube-api-setup.md) 分別驗證內容和成效讀取。使用者明確刪減或延後時記錄缺口，不能把網頁登入當 API 已完成。
- 實際初始化專案時，依 [圖片製作偏好](references/image-production-preferences.md) 一次設定 Codex、Antigravity、網頁模型或 HTML＋CSS、資訊密集圖卡方式，以及使用者已有的品牌色、字型與主視覺參考；後續製圖不每次重問。缺少品牌可留空，推測先預覽、確認才保存。這是一般設定，不建立生圖 API、不呼叫模型。
- 實際初始化專案時，預設準備 OpenCLI；下載前揭露作者 GitHub、固定版本、用途、位置、依賴與擴充權限，依同一份預覽核准範圍由 Agent 代辦，不要求使用者自行下載。
- 只收集目前決策真正需要的資訊，一次詢問一個主要問題。
- 依使用者選取的平台，查核目前官方能力、完整核心權限、相依權限、延伸權限與人工步驟。
- 預設提出該平台所有已支援核心功能的完整權限；逐項說明用途、可執行能力、寫入影響與不同意後失去的功能，並讓使用者在 OAuth 前刪減。
- 社群媒體設定一律由人類操作平台後台；Agent 提供完整文字指引，不使用 Computer Use、受控瀏覽器、DOM 自動化或瀏覽器 CLI 代辦設定。
- 由人類建立 App、啟用 API、選取權限、設定回呼與測試角色、取得金鑰及完成 OAuth 同意；Agent 可依授權準備本機接收器、安全保存與正式 API 讀取驗收。
- API／OAuth 建立後，預設把憑證存入目前作業系統帳號的 macOS Keychain 或 Windows Credential Manager；使用者可在取得秘密前改選或拒絕。
- 將外部工作拆成 API／App、OAuth／登入、平台讀取與遠端寫入等獨立關卡。
- 先顯示完整設定預覽，取得明確確認後才寫入一般設定。
- 分層回報已完成、尚未驗證與必須由人完成的項目。

本技能不撰寫內容、不製作圖片、不發布、不回覆留言、不建立排程，也不執行成效分析。這些工作應交給對應技能；尚未安裝時就清楚回報，不自行代替。

## 輸入

優先從對話與使用者指定工作區取得：

- 明確任務、要處理的平台與功能。
- `social-media/config.json`；若不存在，以 `assets/default-config.json` 作為中性起點。
- 存在時才讀 `sources/strategy/social-media-strategy-and-insights.md`，以及使用者明確指定的既有策略或內容資料。
- 目前已獲授權的本機、登入、OAuth、遠端讀取與遠端寫入範圍。
- 執行平台整合時，使用者可自行操作的瀏覽器、相容 OAuth callback，以及作業系統原生憑證庫；若使用者指定其他秘密管理工具，再依其授權評估。

不得主動搜尋憑證檔、列印環境變數值、讀取瀏覽器 Cookie，或要求使用者把 Token、密碼與 client secret 貼進對話。

## 啟動流程

社群媒體設定一律由人類操作，不提供 AI 代操作選項。先說明：「我會提供官方入口、完整申請步驟、權限與回呼設定，請你自行操作平台後台。完成後，將所需應用程式金鑰或 API key 提供到本機隱藏輸入；不要貼進聊天。我會接續安全保存及 API 驗收。」

依 [完整人工申請清單](references/integration-mode.md#人類自行操作) 一次交付可照做的文字指引，不要求每一步回覆。設定遇到錯誤時，提供修正步驟讓人類操作；不改用 Computer Use、瀏覽器自動化或後台內部請求。已保存的相符憑證先盤點並沿用，不重複索取。此限制涵蓋 Meta、YouTube、Substack 與日後新增平台。

實際初始化時，先利用對話與既有設定確認預期平台；未指定時只問「預計經營哪些平台？預設建議 Meta（Facebook、Instagram、Threads）與 YouTube，也可以指定其他平台。」已有選擇就沿用，不重問。這是預設提案，不是在使用者選擇前啟用全部平台。Meta 與 YouTube 是目前人工確認採用的主要路線；人工確認路線不等於各功能或所有作業系統已實測，仍按驗收紀錄逐項回報。

接受其他平台需求，依當下官方文件、帳號條件與工具能力提出可行方案，不因未列入預設就拒絕。已有平台 adapter 才沿用；沒有時明列尚未實作／驗收及必要授權，不能虛構 API 或把新平台硬寫入不支援它的設定 schema。需要新增支援時另列具體修改範圍，保留已完成平台設定。只討論策略不強制開始 App／OAuth 操作。

這是多階段技能。開始執行前，用 Mermaid 向使用者呈現本次實際採用的分支、確認關卡與停止位置；流程圖不代表外部操作已獲授權。

1. 唯讀檢查工作區設定與策略來源，標示 `missing`、`not_configured`、`partial` 或 `configured`。
2. 判斷使用者是否已有明確任務。
   - 有：不要求先完成策略問卷；平台授權仍預設提出完整核心功能權限，但使用者明確說「只要」或「不要」的範圍視為刪減指示。
   - 沒有，且設定不足：一次只問一個最重要的問題，判斷要走策略初始化，還是設定某個平台功能。
   - 沒有，且設定足夠：摘要目前狀態，詢問這次要修改哪一部分。
3. 選擇一個主要模式；若兩種模式都需要，先完成當前任務的必要部分，再明確交接另一模式。
   - 實際初始化專案時，一併讀 [圖片製作偏好](references/image-production-preferences.md)，從對話已有選擇填入；缺少才問一個製圖方式問題，連同資訊密集圖卡預設併入同一份設定預覽。已有明確非圖片任務不強制補問。只修改製圖偏好時，不重新跑平台整合或 OpenCLI 安裝。
   - 使用者要求實際初始化專案時，同時讀取 [OpenCLI 初始化流程](references/opencli-initialization.md)，預設納入工具準備，先提醒再下載；取得一次涵蓋完整影響的安裝確認後，AI 執行可代辦步驟，不逐條命令重問。已有可用安裝先沿用；拒絕或延後不阻擋仍可完成的工作。只討論策略、讀設定或做既有任務，不強制安裝。
4. 讀取該模式的參考文件：
   - 策略初始化：`references/strategy-mode.md`
   - 平台整合初始化：先讀 `references/integration-mode.md`、`references/permission-selection.md` 與 `references/local-credential-storage.md`，並且只讀使用者選取的 `references/platforms/<platform>.md`
   - 選取 Facebook、Instagram 或 Threads 時，再讀 `references/meta-api-setup.md`；不要把 Meta 三條授權路線混成一條。
   - 選取 YouTube 時，再讀 `references/youtube-api-setup.md`，依桌面 client 路徑操作，不把 API key 當使用者 OAuth。
5. 依下方「實際整合執行」交付人工申請清單；只要求規劃時停在指引。使用者完成平台設定並提供必要資料後，Agent 才接續已授權的本機憑證保存、OAuth 接收與正式 API 驗收。
6. 形成候選設定後，依 `references/configuration-contract.md` 驗證並預覽。
7. 使用者確認預覽後才寫入；重新讀回檔案並比對雜湊。
8. 依 `references/verification-levels.md` 分開回報本機設定、API／App、登入／OAuth、平台讀取與遠端寫入，不猜測較高層已完成。

## 平台整合原則

每個「平台 × 功能」仍須獨立驗證，但首次選取平台時預設採完整管理模式，授權預覽涵蓋該平台所有已支援核心功能。平台設定只提供文字指引，由人類操作官方介面；不使用 Computer Use 或其他瀏覽器自動化作為備援。完成設定後，Agent 優先透過正式 API、官方連接器或可靠 CLI 驗證讀取；介面受限時提供官方匯出或人工查核步驟，標示未驗證項目。不得把瀏覽器內部請求或第三方套件冒充官方 API。

「完整權限」只代表使用者允許建立技術能力，不代表允許 Agent 立即發布、回覆、刪除、建立廣告、傳送私訊或排程。每次遠端寫入仍由對應技能依其預覽與確認關卡執行。使用者刪減權限時，Agent 不反覆勸說；改用 `custom` 權限設定，列出受影響功能並繼續處理仍可完成的部分。

選取 Facebook、Instagram 或 Threads 任一平台時，主動詢問使用者是否要在同一次 Meta 初始化中一併設定另外兩個平台。可以共用一次規劃與外部變更確認，但各平台的 App／use case、帳號關係、permission、OAuth、Token 與讀回證據仍分開，不因其中一個成功而推定另外兩個成功。

Agent 完成指引、本機工具與 API 驗收；所有平台後台、登入與 OAuth 畫面均由人類自行操作。

## 實際整合執行

目前候選版已提供本機憑證保存、恢復、Terminal 交接，以及 Facebook Pages／YouTube／Instagram Login／Instagram via Facebook Login／Threads 的 OAuth callback、交換與有效性執行器。實際執行前必讀 `references/oauth-runtime.md`：Facebook 使用 HTTPS Web server code flow；YouTube 使用 Desktop loopback／PKCE 與 refresh。Instagram Login／Threads 另讀 [專用交換與刷新契約](references/instagram-threads-oauth.md)，使用各自的長期 User Token；Instagram via Facebook Login 讀 [專用 Page Token 契約](references/instagram-facebook-login-oauth.md)，不能與直接登入混用。各路徑依實際驗收紀錄分層判定；[Facebook Windows 實測](../../docs/facebook-windows-live-verification.md)不代表 macOS、其他登入路徑、Messenger 或發布已通過。缺少相容 callback、原生憑證庫或平台必要條件時停在預覽，不得臨時用未查證端點取得秘密。

1. Agent 先核對現有設定與憑證狀態，執行 `scripts/credential_store.py inspect`。預設採 macOS Keychain 或 Windows Credential Manager；不可用時，仍可提供申請指引，但在取得秘密前停止並說明安全儲存缺口。
2. 提供官方後台連結、正確帳號／App 的核對方式，以及建立 App／專案、選 use case、啟用 API、填 redirect URI、加入測試角色與權限的完整文字步驟。清楚區分 Facebook、Instagram、Threads 各自需要的 ID／Secret，以及 YouTube Data API 與 Analytics API。
3. 人類自行完成後台設定、登入、安全驗證、條款與測試邀請。角色必須選取搜尋結果並保存，再核對邀請是否接受；提供這些檢查方法，不代操作畫面。
4. 列出本輪實際需要的 App ID／client ID、目標資源、App Secret／client secret 或 API key，註明用途及提供位置。依 [憑證盤點](references/local-credential-storage.md#先盤點再取得避免重複輸入) 沿用相符且可用的既有值；只有缺少的秘密由人類在 `credential_terminal.py launch` 的隱藏輸入提供。不要要求所有平台都提供 API key；需要使用者 OAuth 的平台，金鑰本身不代表授權完成。
5. 使用者準備好進行 OAuth 後，Agent 啟動本機接收器並提供短期 `launch_url` 連結與有效時間，讓人類自行開啟、核對帳號／資源／權限並同意。不要在使用者尚未完成後台設定時反覆啟動接收器等待逾時。
6. 程式驗證 `state` 與 callback，交換 Token 並直接透過 `store_secret()` 寫入已確認的原生憑證庫。命令、日誌、預覽與錯誤輸出不含秘密。OAuth 逾時不代表 App Secret 過期；先查狀態再恢復，不重用 code、不重複要求輸入、不把 `pending_write` 交給後續技能。

   五條 OAuth 路徑都必須使用 `oauth_callback.py` 的 `preview → configure → run → status`，不得另寫臨時接收器繞過 state、適用路線的 PKCE、儲存及不明結果保護。後續技能依 `oauth-runtime.md` 透過 `Runtime.access()` 在記憶體取用、檢查並依授權刷新；原生 `verified` 不等於平台憑證有效，`ready` 也不代表所有內容功能均已驗證。Instagram Login 的權限清單來自初次交換；目前官方資料未文件化全部當前 scope 讀回，因此當次基本帳號讀回不證明額外功能仍有權限。交接必須標示初次授權證據，發布、留言、insights 與私訊再由各自正式端點判定，明確拒絕或結果不明即停止且不重送。Instagram via Facebook Login 必須明傳 `--login-route instagram_facebook_login`，舊設定不自動改路線。
7. 以正式 API 讀回目標帳號、資源、授權範圍與可判斷的有效期限。解析含 Token 的原始回應時只輸出遮蔽後結果。
8. 只有讀回結果與使用者指定目標一致才標示平台讀取已驗證。遠端發布、回覆或排程仍保持未測試，除非另有明確授權。

外部變更預覽至少列出：平台與功能、將建立或調整的 App、目前官方 use case／產品名稱、完整核心權限及其用途、相依權限與額外影響、可選延伸權限、使用者刪減項目、OAuth callback 類型、偵測到的原生憑證庫、要保存的憑證名稱、未來 Agent 可取用的範圍、預期人工關卡、驗證請求，以及本輪明確排除的遠端操作。預覽要明示使用者可在取得秘密前改選或拒絕持久保存；未提出不同選擇時採原生憑證庫。預覽結尾必須直接告知使用者「如果有任何權限不想開放，請現在告訴我」；後台實際名稱或權限與預覽不同時停止並重新確認，不自行改選相近項目。

若已開好可見 Terminal，`credential_store.py put` 是隱藏輸入的直接入口；使用者只貼上一次。不得由 Agent 讀取後台秘密欄位或啟動瀏覽器自動保存流程。

## Threads 官方測試權杖替代路線

Threads 回呼註冊受阻且使用者仍要求完成自有帳號 API 測試時，可依 [官方測試權杖匯入](references/threads-token-import.md) 使用後台用戶權杖產生器。這是獨立於上述 authorization-code callback 的匯入流程：沿用既有授權，先核對原生庫與相容匯入程式，再取得秘密；不需要一個已成功註冊的 callback。不得把匯入成功標成回呼驗收成功，也不得自行輸入或重放 OAuth code。權杖產生器的開啟、帳號選擇、同意與隱藏輸入全部由人類操作；匯入與 API 驗證由 Agent 完成。

## 最小化人類操作

此處減少的是重複問答與重做，不是讓 AI 接管平台畫面。

- 最早一次完整說明平台、App／API、實際 permission 名稱與用途、可刪減項、回呼與 HTTPS 前提、原生保存／刷新方式、所需金鑰及分層驗收。已確認的授權與目標跨訊息沿用，只補問缺項或新增影響，不重複問「是否繼續」。
- 一次提供完整申請清單，包括手動選 use case、填 redirect URI、保存與重新載入檢查；人類可整批操作完再回報。出錯時只補充失敗步驟，不要求重建已完成 App 或重貼可用金鑰。
- Agent 可以在核准範圍內準備本機程式、HTTPS、原生憑證輸入及 API 驗收；平台後台和瀏覽器擴充設定一律提供文字指引，不使用 Computer Use、受控瀏覽器或 DOM 自動化。
- 需要的 App Secret／API key 由人類貼入已準備好的 Terminal 隱藏輸入；使用者只貼上一次。OAuth callback 可取得的 Token 由程式直接保存，不要求人工複製 code 或 Token。
- 一般設定仍依 preview、digest、確認與讀回流程執行；既有確認涵蓋且候選未變就沿用。缺少必要資料或安全輸入能力時清楚列出缺口，不暗中改用明文或自動操作。

## 寫入流程

1. 將候選設定寫入暫存檔，不直接覆蓋正式設定。
2. 執行 `scripts/manage_workspace.py preview`。向使用者顯示新增、修改、保留、設定目標與預覽雜湊；不要只顯示摘要後省略實際欄位。
3. 只有在使用者明確確認這份預覽後，才以相同候選檔與雜湊執行 `apply --confirm-write`。
4. 既有設定在預覽後變動、候選含秘密欄位、路徑跳出工作區、schema 不符或雜湊不同時停止。
5. 寫入後重新讀取 `social-media/config.json` 與 `.local/social-media/setup-state.json`；驗證內容雜湊一致，並回報 `contains_credentials: false`。

命令旗標不是對話核准。不可因為能執行 `--confirm-write` 就跳過使用者確認。

## 執行錯誤最小回填

實際執行出錯，或平台可觀察行為與本技能規則衝突時，原任務優先：

Meta permission 新增顯示錯誤時，先依 [已驗證的讀回處理方式](references/troubleshooting.md) 判定持久狀態，避免把前端錯誤直接當成保存失敗或重送同一變更。

1. 先保存目前進度與已知外部狀態；遠端結果不明時停止，不為了測試修正而重送可能已成功的請求。
2. 若 `references/troubleshooting.md` 已存在，只讀與目前症狀相關的段落；不存在時不要先建立空檔。
3. 只有能證明錯誤來自本技能、修正限於同一個由使用者管理的技能來源、不新增依賴或外部授權，且重跑原失敗步驟通過時，才立即回填：主要流程更新本 `SKILL.md`，已驗證的特定環境或例外才建立或更新 `references/troubleshooting.md`。
4. 只做一次小修正、一次針對性重測，再執行本技能最快的既有格式／契約驗證，隨即回到原任務。
5. 一次修正仍失敗、需要跨技能或共用架構改造、需要長時間研究、找不到可寫原始來源，或修正本身需要新的外部動作時，停止回填並簡短回報技能缺口；不把未驗證推測寫進技能。

不得修改已安裝快取、內建技能、外掛或第三方來源。真實帳號、網址、識別碼、憑證、私人路徑、品牌內容與一次性使用者選擇不得進入公開技能。回填不授權 commit、push、發布、部署或原任務以外的遠端變更。

## 輸出與交接

每次輸出至少包含：

- 本次模式與目標任務。
- 已確定的策略或平台功能，以及資訊來源。
- 權限設定模式、要求與刪減的 permission，以及每個刪減項目的功能影響。
- 設定預覽或寫入後的工作區相對路徑。
- 各層狀態：本機設定、本機憑證儲存、API／App、使用者登入／OAuth、平台讀取、遠端寫入。
- 有準備 OpenCLI 時，另列來源下載、依賴建置、CLI 版本、擴充功能、Bridge 與平台讀取狀態，不把下載成功當成瀏覽器或搜尋已可用。
- 尚缺資訊、停止原因與下一個唯一建議動作。
- 後續技能交接需要的已核准輸入；不得把未核准推測包裝成設定。
- 憑證只回報 backend、平台、名稱、是否可用與讀回驗證時間；不得輸出值或完整原生目標名稱。

## 寫入範圍

本技能只可在使用者明確指定的工作區寫入：

- `social-media/config.json`：一般策略與整合意圖。
- `.local/social-media/setup-state.json`：設定雜湊、套用時間及不含憑證聲明。
- `.local/social-media/credential-references.json`：原生憑證庫的非敏感 namespace、平台／憑證名稱與驗證狀態；不含秘密值。
- `.local/social-media/credential-store.lock` 與 `.local/social-media/credential-input/`：單程序鎖與 Terminal 一次性非敏感結果收據，不含秘密值、不作為新任務指令。
- `.local/social-media/oauth-runtime.lock` 與 `.local/social-media/oauth/`：OAuth 作業鎖及非敏感狀態；私人連線設定、Token 與分段 bundle 只留原生憑證庫。schema 與恢復規則見 `references/oauth-runtime.md`。
- `.local/social-media/opencli-state.json`：核准目的地、來源、版本與分層驗證紀錄，不含帳號或分頁內容；來源與擴充產物放在已核准且不提交的 `.local/tools/opencli/`，細節依 `references/opencli-initialization.md`。npm cache、Chrome 擴充資料及 OpenCLI 使用者層級狀態不在專案內，只有在同份安裝預覽已揭露並核准時才可由對應工具建立；不得覆蓋既有共享設定。

一般檔案不得寫入技能目錄、公開 Toolbox、策略洞察檔、平台內容或排程。未取得外部變更預覽的明確授權時，不得修改任何外部服務；平台後台建立與調整一律由人類操作；Agent 取得授權後只可執行預覽內的本機連線設定、OAuth 協定交換與讀取驗收，不得發布、回覆或排程。平台私人識別碼與憑證值只能寫入使用者選定的秘密儲存；上述參照檔只記錄可重新定位秘密的非敏感資訊。使用者未另行指定時，外部變更預覽確認同時涵蓋原生憑證庫寫入；保存憑證不代表已授權發布，也不取代後續發布或管理技能的遠端確認。若使用者另行要求更新策略洞察，交給未來的 `social-performance-analysis`，並保留其預覽與再次確認關卡。

## 停止條件

- 工作區、帳號、平台或功能無法唯一判定。
- 需要未獲授權的登入、OAuth、App 建立、套件安裝、遠端讀取或遠端寫入。
- 官方能力仍不明、文件互相衝突，或未先揭露功能需要的 App Review／Business Verification。
- OAuth 畫面出現預覽未列出的 permission，或缺少已確認的 permission。
- 作業系統沒有支援的原生憑證庫、互動式 Terminal 不可用、原生寫入或不顯示內容的讀回驗證失敗，且使用者沒有明確選擇其他安全秘密儲存。
- 候選設定含秘密、私人識別碼或憑證路徑。
- 預覽未確認、預覽後來源變動、同名路徑類型衝突或讀回驗證失敗。

停止時保留現有資料，不自動切換帳號、不嘗試繞過驗證，也不重送可能已成功的外部請求。

## 驗證

公開候選版以虛構工作區驗證：缺少設定、完整核心權限預設、使用者刪減、延伸權限選擇、Meta 三平台合併詢問但分開驗證、一次一問、兩種模式、只讀選取的平台文件、秘密欄位拒絕、預覽前不寫入、錯誤雜湊拒絕、確認後原子寫入、既有變動停止、讀回雜湊、原生憑證庫參照不含秘密、隱藏互動輸入、單筆取代／刪除關卡，以及技能錯誤的一次小修正與停止邊界。虛構 backend 測試不證明 macOS、Windows 或任何平台連線已實測。
