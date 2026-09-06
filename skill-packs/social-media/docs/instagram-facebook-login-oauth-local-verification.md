# Instagram via Facebook Login 本機驗證

日期：2026-09-06。範圍為待辦 `INIT-01` 的本機程式、文件與虛構測試；不登入、不建立 App、不執行 OAuth、不讀寫真實憑證、不呼叫平台或下游功能端點。

## 實作結果

- 私人 OAuth 設定新增可向後相容的 `login_route`。舊 Instagram 設定缺少欄位時維持 `instagram_login`；本路徑必須明傳 `instagram_facebook_login`。
- 新增 `instagram_facebook_oauth.py`：短期／長期 Facebook User Token 核對、`/me/permissions`、`/me/accounts` 的唯一 Page／IG 關係、Page Token 保存，以及 Page debugger、Page／IG 節點的每次讀回。
- 短期／長期 User Token 與其他 Page Token 不持久保存。選定 Page Token、Page ID、初次 Facebook 使用者 ID 只留原生秘密庫 bundle；一般狀態不含憑證或私人 ID。
- Page Token 沒有套用 Instagram Login、Threads 或 Google 刷新。撤權、期限、App／類型／scope、Page／IG 身分不符都停止並要求新 OAuth；結果不明不重送。
- 共用 CLI 預覽會顯示非敏感登入路線，授權頁使用版本化 Facebook dialog；仍由本人完成登入與 OAuth 同意。

## 官方查證

2026-09-06 重新讀取 Meta 官方 Instagram Postman 文件與 token request：Facebook Login 路徑要求相連 Page／Instagram 專業帳號，使用 User Token 列出 `/me/accounts`，回應包含 Page Token 與 `instagram_business_account`。另讀 Meta 官方 Page／IGUser 原始碼確認可讀欄位與 GET 節點；Facebook code／長 Token 沿用已查證的官方 manual flow。直接來源列於 [專用契約](../skills/social-media-setup/references/instagram-facebook-login-oauth.md)。沒有安裝或複製官方 SDK。

## 分層狀態

| 層級 | 結果 |
|---|---|
| 靜態結構與文件 | 套件驗證器、第一技能 quick validation 與差異空白檢查通過；包含 manifest、schema、Python 語法、相對連結、隱私與技能契約 |
| 本機技能發現 | 隔離安裝生命週期測試通過，新程式與參考文件會進入安裝副本；未執行真實 Agent 技能探索 |
| API 套件是否可安裝 | 沒有新增第三方套件，程式使用 Python 標準函式庫 |
| OAuth 虛構執行 | 17 項專用測試通過；整包共 239 項，238 通過、1 項原生探測依政策略過 |
| 原生憑證庫與真實 Terminal | 未執行 |
| 使用者登入／OAuth | 未執行 |
| 平台讀取 | 未執行；官方文件與虛構回應不算帳號讀取 |
| 測試發布／留言／私訊／成效 | 未執行；本待辦不實作這些功能 |
| 另一臺電腦驗收 | 未執行 |
| 正式公開支援 | 尚未成立；未 commit、push 或發布版本 |

## 驗證範圍

專用測試涵蓋路線向後相容、必要 scope、拒絕混入直接登入 scope、Facebook 授權網址、短期／長期 User Token 同一身分、完整 granted permission、唯一相連 Page、Page 權限工作、只保存目標 Token、Page debugger、Page／IG 讀回、取消／錯誤 state、未知交換不重試、秘密不進 CLI 預覽。整包回歸另涵蓋隔離安裝、更新、回復與移除，因此安裝副本包含本路徑；這仍不等於真實用戶端已發現技能。

實機驗收仍須另行驗證後台產品名稱、App Review／Business Verification、HTTPS callback、真實回應欄位、原生秘密庫、Page／IG 關係、撤權及下游功能。`INIT-01` 完成只表示程式與虛構驗收齊備。
