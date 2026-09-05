# OAuth 接收、交換與憑證有效性

查證日期：2026-09-05。選取 Facebook Pages 或 YouTube，且要實際授權或取用既有憑證時讀取本文件。這是 `social-media-setup` 的共用執行器，不是新技能。程式與虛構測試已建立；真實 OAuth、原生憑證庫與平台讀取尚未驗收。

## 路徑與界線

| 路徑 | 程式實作 | 仍需外部條件 |
|---|---|---|
| YouTube Desktop app | 本機 HTTP loopback、state、PKCE S256、code 交換、refresh、頻道讀回 | 已核准 client、API 啟用、登入同意、scope／審查資格 |
| Facebook Pages 的 Web server code flow | HTTPS callback、state、短期 User Token 換長期 User Token、選定 Page Token、權限與身分檢查 | 相容 Facebook Login App、精確註冊 HTTPS redirect、既有受控 TLS 入口、Page 工作權限與審查 |
| Instagram／Threads | 本輪沒有專用執行器 | 不得把 Facebook 程式改個平台名稱就使用；共用規劃不等於共用 Token 流程 |

Facebook 這條路徑是伺服器端交換，**不能把 App 設成 Native/Desktop 後套用**。App Secret 只留在使用者控制的本機程序與原生憑證庫，不能打包給其他使用者。同一套公開工具可以由每位使用者各自設定 App，但不散布共用 App Secret。Meta 的 HTTPS 條件與 Google Desktop app 的 HTTP loopback 不相同。

## 一次預覽與人類最少操作

1. Agent 先依平台文件提出完整核心權限，包含平台正式支援的私訊；讓使用者移除不想開放的權限，另外選擇廣告等延伸項目。程式不替使用者決定 scope；每個 `--scope` 必須來自已確認的清單。
2. 把目標帳號／Page／頻道、App 類型、callback、秘密庫、連線代稱、將保存的值與唯讀檢查列入同一份外部變更預覽。明確說明日後可自動讀取憑證、檢查有效性與在核准範圍內刷新；不包含發布、回覆、排程或自動再授權。
3. Agent 代辦已授權的後台填寫；本人只處理登入、安全／法律確認、資源選擇及 OAuth 同意。不要求使用者貼授權碼。
4. App Secret／client secret 能安全直接取得時由程式保存；否則依 `local-credential-storage.md` 由 Agent 開 Terminal，使用者只在隱藏提示貼上一次。預先存成該平台的 `app-secret`，不可傳到命令列或對話。
5. Agent 以 `preview` 產生連線設定摘要與 digest，在私人介面向使用者補充核對確切目標與 callback；确認後才以相同參數 `configure --confirm-config --preview-digest <digest>` 保存。取代既有設定還要確認並加入 `--confirm-replace`。這不是另一張問卷，可以納入同一份初始化預覽。
6. Agent 啟動 `run`，只開啟輸出的短期本機 `launch_url`；由接收器導向官方授權頁。本人同意後，程式交換、原生保存、讀回驗證；Agent 查看非敏感結果。
7. 只有 `ready` 才代表這一次身分／授權讀回成功。最後一般設定仍依 `manage_workspace.py` 顯示寫入預覽並確認，不能由 OAuth 程式自動修改。

下列命令是 Agent 在授權後操作的介面，不是要求使用者自行組命令。`<...>` 是私人環境中的替代值，不得直接照貼；範例的唯讀 scope 只示範語法，不是預設權限清單。

```sh
python3 scripts/oauth_callback.py preview --workspace-root <私人工作區> --platform youtube --client-id <桌面client-ID> --target-id <頻道ID> --scope https://www.googleapis.com/auth/youtube.readonly
python3 scripts/oauth_callback.py configure --workspace-root <私人工作區> --platform youtube --client-id <桌面client-ID> --target-id <頻道ID> --scope https://www.googleapis.com/auth/youtube.readonly --preview-digest <預覽digest> --confirm-config
python3 scripts/oauth_callback.py run --workspace-root <私人工作區> --platform youtube --confirm-oauth --confirm-read --confirm-store
python3 scripts/oauth_callback.py status --workspace-root <私人工作區> --platform youtube
python3 scripts/oauth_callback.py check --workspace-root <私人工作區> --platform youtube --confirm-read --allow-refresh
```

Metadata 參數不是秘密值，但 client ID／target ID 仍是私人資料，必須只在私人工作區執行，不貼回公開技能、一般設定或公開日誌。`preview` 的機器摘要不列出這些值；Agent 必須在私人預覽中另外核對它們，不能只讓人確認一串 digest。

Facebook 額外參數：`--platform facebook --graph-version <當下已核對版本> --callback-mode https_proxy --callback-port <固定本機port> --redirect-uri https://<使用者控制的網域>/oauth/callback`，另傳該 App／Page ID 與全部確認 scope。本輪官方文件範例為 `v25.0`，程式不預設版本。設定、後台註冊與交換的 redirect URI 必須逐字一致。

`https_proxy` 只使用已存在且使用者控制的 HTTPS 入口：TLS 驗證有效、精確 Host 保留、只轉送 `/oauth/callback` 與 `/oauth/complete` 到本機 loopback、不得記錄 query／授權碼，不可交給第三方臨時接收服務。Agent 查核後，在使用者核准此架構下傳 `--confirm-https-proxy`。本套件不會自行部署代理或隧道。若沒有此條件，停在預覽並說明需要的額外部署授權。

既有本機 TLS 可改用 `https_local`，提供 `--tls-cert`／`--tls-key` 的私人路徑，redirect 的主機必須在瀏覽器解析到 `127.0.0.1`，port 要與接收器一致，憑證必須是瀏覽器信任且符合該主機的憑證。不得關閉憑證驗證或臨時要求使用者忽略警告。TLS 私鑰是既有 HTTPS 基礎設施的檔案，不由此程式產生或複製到技能目錄；路徑隨連線設定留在原生儲存。

## 程式與資料保存

- `oauth_callback.py`：短期單使用者接收器，僅監聽 `127.0.0.1`，15 分鐘失效，state／PKCE／code 僅留記憶體；拒絕不符 Host、重複欄位、錯誤 state、過期及重播。Callback 處理後導向不含 code 的本機結果頁，不輸出平台原始錯誤。
- `oauth_http.py`：只允許固定官方 HTTPS 主機與端點、TLS 驗證、不使用系統代理、不跟隨 redirect、不重試、不記錄 URL／回應。Google 使用表單 POST 與 Bearer header；Facebook 官方 GET 參數可能含秘密，但只在受控程序內經 TLS 傳輸，絕不送到瀏覽器導覽、工具輸出或 URL 日誌。
- `oauth_runtime.py`：交換、分段保存、有效性與身分讀回；共用 `credential_store.py` 的原生讀寫與驗證。不下載 SDK，不存 `.env`。
- 連線設定（含私人 ID／TLS 路徑）留在原生庫 `oauth-<connection>-config`；token bundle 留在 `oauth-<connection>-<revision>-p<index>`，每段不超過 2000 ASCII 字元，避開 Windows 單筆大小上限。參照檔只保存名稱、狀態與來源。
- `.local/social-media/oauth/<platform>-<connection>.json` 只保存版本、平台、代稱、狀態、分段數、隨機 revision／attempt、時間與不含憑證聲明；schema 見 `oauth-state.schema.json`。`.local/social-media/oauth-runtime.lock` 序列化同一工作區的交換與取用。
- 舊世代保留在原生庫，避免未確認刪除與無法恢復。需要清理時先預覽確切舊世代，使用既有單筆刪除流程並另行確認；不得刪除現行 revision 或正在寫入的值。不把舊世代自動切回當備援。

## 有效性與後續技能交接

受信任的發布、互動與成效 adapter 應在自身取得任務授權後，於同一程序呼叫：

```python
# 秘密只留在程序記憶體，不列印，不交給模型或子程序參數。
from oauth_runtime import Runtime
runtime = Runtime(workspace, "youtube", connection="main")
token = runtime.access(confirmed_read=True, allow_refresh=True)
# 在 adapter 自己的預覽、確認與目標核對通過後才執行獲准任務。
```

`allow_refresh` 只在使用者核准持續取用／刷新，或本次明確授權刷新時啟用，不因「檢查狀態」就刷新。`status` 不讀取 token、不連平台；`check` 會讀取平台。原生憑證庫的 `verified` 僅表示存入與讀回一致，不能代替平台驗證；後續 adapter 不得繞過本 runtime 直接拿某段 token 去發布。

YouTube：每次核對 scope 與 `channels.list(mine=true)` 的選定頻道。access token 剩餘不超過 60 秒時，需要已核准的 refresh；新回應沒有 refresh token 就保留原值，有新值則保存新世代。`invalid_grant`、已知 refresh 到期或撤銷時回到明確重新授權關卡，不自動開瀏覽器。初次回應缺少 refresh token 時不宣稱已完成可持續使用的連線；若需要再次 consent，先解釋原因並確認，不盲目重跑。

Facebook：先驗短期及長期 User Token 的 App、使用者、類型與期限；讀回 `/me/permissions`，只保留指定 Page 的 Token。每次取用檢查 Page Token、App、scope、期限與 `/me` 的 Page ID。`expires_at=0` 表示沒有排定到期時間，**不等於永遠有效**；缺值不視為零。到期／撤銷需要重新登入授權，不把 Page Token 套進 Google refresh 流程。檢查採每次使用時執行，不建立背景排程。公開留言、私訊、成效端點仍由後續技能驗證，取得 permission 不是端點全部可用的證明。

Scope 要求與實際讀回不一致（少授予或多出未同意項目）一律停止，不自行擴權。Facebook 隱含的 `public_profile` 必須在預覽揭露，程式將其納入核對。

## 停止、恢復與最小 MVP

- `configured`：只有本機連線設定，未授權；`authorizing`：等待本人；`exchanging`／`refreshing`：已開始一次交換。
- `ready`：該次憑證保存與指定資源讀回成功，不代表其他 API 功能或正式支援。
- `permission_mismatch`／`target_mismatch`：停止，由人確認差異；不得改目標或權限後默默繼續。
- `expired`／`reauth_required`：說明需要重新授權。本人核准後 `run --confirm-restart` 建立全新 state／code，絕不重用舊 code。
- `remote_result_unknown`、程序中斷停在 `exchanging`／`refreshing`：禁止自動重試或 `--resume` 刷新。先報告，取得重新授權確認後才開始新流程。
- `read_failed`／`rate_limited`：保留狀態，檢查服務或權限；讀取重試仍須由 Agent 判斷已在授權內，不內建自動重試。

- `saving`／`storage_incomplete`：不交付 token。若全部分段已是原生 `verified`，經確認後 `check --confirm-read --resume` 只重新讀回驗證，不重跑 code 交換；缺件或 `pending_write` 依 `local-credential-storage.md` 恢復。不知道原值就不猜。
- `refresh_required`：確認刷新授權後，`check --confirm-read --allow-refresh --resume`；不是重新登入。

YouTube 的 `quotaExceeded` 會歸入 `rate_limited`，不建議以擴權解決；有 Google 帳號但尚未建立 YouTube 頻道的 `youtubeSignupRequired` 屬於目標條件不符。依據：[官方 API 錯誤表](https://developers.google.com/youtube/v3/docs/errors)。

沒有背景服務、Webhook 部署、自動修補平台權限、無限重試或多帳號自動切換。錯誤修正仍遵守主技能的一次小修正與針對性重測。

## 官方依據與虛構驗證

已直接讀取的當前官方文件：[Google Desktop OAuth](https://developers.google.com/identity/protocols/oauth2/native-app)、[Google 官方 refresh 實作](https://github.com/googleapis/google-auth-library-python/blob/main/google/oauth2/_client.py)、[YouTube channels.list](https://developers.google.com/youtube/v3/docs/channels/list)、[Facebook manual flow](https://developers.facebook.com/docs/facebook-login/guides/advanced/manual-flow/)、[長期 Token](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived/)、[Facebook Login 安全規則](https://developers.facebook.com/docs/facebook-login/security/)、[Meta Token 類型](https://developers.facebook.com/documentation/facebook-login/guides/access-tokens)、[Meta 官方 Page Token 範例](https://www.postman.com/meta/facebook/request/bqfxwbp/get-access-tokens-of-pages-you-manage)。只作行為查證，未複製或安裝官方 SDK。

`tests/test_oauth_runtime.py` 使用虛構 backend／HTTP 回應，涵蓋交換、長 Token 分段、刷新、scope／目標不符、撤銷、state、PKCE、重播、中斷及不明結果。Loopback HTTP 測試只連本機，讀取官方 Location 但不跟隨，不開瀏覽器；不是平台 OAuth 實測。TLS、反向代理、原生庫、使用者同意及實際權限讀回全部留到最後集中驗收。
