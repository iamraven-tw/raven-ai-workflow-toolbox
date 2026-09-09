# Instagram Login／Threads OAuth 本機驗證

日期：2026-09-05。補充既有 [Facebook Pages／YouTube 驗證紀錄](oauth-local-verification.md)，不改寫前次結果。範圍只限第一技能的新增 OAuth 路徑，不實作後續發布、互動或成效資料擷取。

## 完成的本機能力

共用接收器增加 Instagram Login／Threads 選項，搭配獨立 `meta_user_oauth.py`：code 換短 Token、各自長期 Token 交換、原生庫保存、按需刷新與讀回驗證。平台狀態 schema 加入兩個平台，manifest 保留本機候選與未實機驗收標記。沒有新增技能、背景排程或 SDK。

IG 初次交換 scope 與當前雙 ID／專業帳號核對；Threads 讀 debugger 的期限／scope／使用者並核對 `/me`。過期不刷新，未滿 24 小時不刷新，只有最後七天且刷新已授權才嘗試一次。未知結果不重送，新世代讀回失敗不退回舊 Token。

## 驗收分層

| 層級 | 本輪結果 |
|---|---|
| 靜態結構與文件 | 套件驗證器與第一技能 quick validation 通過；包含 manifest、schema、語法、相對連結、編碼、隱私、symlink 與技能契約；差異空白檢查通過 |
| 本機技能發現 | 隔離安裝生命週期通過，新增程式及文件確實安裝、安裝副本的 CLI 可載入；未重新執行真實 Agent 技能探索 |
| API 套件可安裝 | 未新增 API 套件，使用 Python 標準函式庫；沒有下載安裝測試，不代表其他 SDK 已可安裝 |
| 本機虛構行為 | 整包 222 項測試，221 通過、1 項原生探測依政策略過；其中新增平台測試 28 項、既有 Facebook／YouTube OAuth 測試 29 項全部通過 |
| 原生秘密庫／真實 Terminal | 未驗收；使用記憶體庫與模擬傳輸，不存取真實憑證 |
| 使用者登入與 OAuth | 未執行；HTTPS／TLS 入口、使用者同意、App 角色與審查待集中驗收 |
| 平台讀取 | 未執行；虛構回應不能證明真實 Token 或額外權限可用 |
| 測試發布 | 未執行；不發布、不回覆、不傳私訊 |
| 另一臺電腦驗收 | 未執行 |
| 正式公開支援 | 尚未提供；本輪沒有 commit、push 或發布版本 |

## 明確保留的缺口

- Instagram **via Facebook Login** 尚無專用執行器，不可拿 Page 驗證替代。
- Instagram Login 的全部當前 scope 重新列舉介面尚未完成官方支援查證；僅保留初次授予清單，基本帳號讀回不保證額外功能未撤權。
- 真實 callback、原生保存、平台 Token 回應格式、帳號與權限、刷新及功能端點，全部仍需最後的實機驗收。
- 官方依據與各自端點見 [執行契約](../skills/social-media-setup/references/instagram-threads-oauth.md)。不因程式或模擬通過就宣稱整體初始化已完整驗收。

## 重現

在本技能包根目錄執行，不加入原生驗收 opt-in：

```sh
SOCIAL_NATIVE_ACCEPTANCE=0 PYTHONDONTWRITEBYTECODE=1 python3 tests/validate_package.py
SOCIAL_NATIVE_ACCEPTANCE=0 PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
```

測試透過既有本機 Python 執行；新增平台測試封鎖真實 HTTPS 與原生 backend 探測。既有 callback 測試只連本機 loopback、不跟隨官方 Location、不開瀏覽器。此紀錄不包含 private workspace 或真實帳號證據。

## 後續狀態（2026-09-06）

「Instagram via Facebook Login 尚無專用執行器」保留為 2026-09-05 當時結果。其後已新增專用 Page Token 路徑與虛構測試；直接 Instagram Login 的當前完整 scope 讀回也已完成官方查證，結論是已查資料沒有文件化該介面，因此保留初次交換清單並由各功能端點判定。後續證據分別見 [Instagram via Facebook Login 驗證](instagram-facebook-login-oauth-local-verification.md)、[Instagram Login 當前權限證據](instagram-current-scope-evidence-local-verification.md)及[下游 OAuth 交接驗證](downstream-oauth-handoff-local-verification.md)。

## Threads 官方測試權杖實機驗收（2026-09-09）

範圍仍是 `social-media-setup` 的平台初始化讀取驗收。本人在獨立測試 App 的官方產生器完成同意及 Token 隱藏輸入，Windows Credential Manager 保存與讀回成功；依 [匯入契約](../skills/social-media-setup/references/threads-token-import.md) 建立獨立 Threads 連線。沒有改動既有正式 App。

實機 debugger 回傳有效 USER Token、全部五項已核准核心 scope、期限、user ID 與 `application`，但沒有 `app_id`。修正原匯入器強制要求該欄位的假設：由指定後台的人工作業來源與 API 名稱交叉核對，保存 `dashboard_source_and_application` 證據。這不是 API 數字 App ID 驗證；若回應提供不符的 App ID 仍拒絕。

| 層級 | 實測結果 |
|---|---|
| 原生庫／連線 | Windows 隱藏 Terminal 輸入、分段 bundle 保存、讀回及新 Runtime 取用通過 |
| 帳號 | debugger 與 `/v1.0/me` 的 user ID 相符，username 符合使用者指定目標 |
| 內容 | 官方 `/{user-id}/threads` 回傳 HTTP 200 與非空貼文樣本；仍有下一頁，只記 `sample_only` |
| 成效 | 共用 OAuth Runtime 的正式成效 adapter 成功讀取 `/{user-id}/threads_insights?metric=views`；`coverage=unknown`，不宣稱涵蓋指定日期或完整報表 |
| OAuth callback | 仍未通過；官方後台 Token 匯入不等於回呼表單可保存或 code flow 已修復 |
| Token 刷新 | 未到刷新窗口，未實機觸發；只測試虛構刷新保留 App 來源證據及後續核對 |
| 發布／回覆／其他技能 | 未執行，取得核心權限不等於已授權或驗證遠端寫入 |
| macOS／另一臺電腦／公開使用者 | 未實機驗收；不由 Windows 結果推定通過 |

驗證：匯入器 9 項、Meta User OAuth 30 項、既有 OAuth Runtime 29 項虛構測試全部通過；套件靜態驗證與 `git diff --check` 通過。公開紀錄不含真實帳號、App／資源 ID、貼文、成效數值、憑證或私人路徑。
