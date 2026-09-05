# YouTube API 實際初始化

查證日期：2026-09-05。只在選取 YouTube 整合時讀取；核心與延伸 scope 以 [YouTube 平台文件](platforms/youtube.md) 為準。本文件處理後台操作，接收、交換與更新使用 [OAuth 執行器](oauth-runtime.md)。已有程式及虛構測試，不代表實機驗收。

## 前提與一次預覽

先確認唯一目標頻道、既有受控瀏覽器、可用原生憑證庫，以及隨技能提供的 `oauth_callback.py` 與兩個 OAuth 模組完整。依 `oauth-runtime.md` 檢查 Desktop app、loopback 與秘密儲存前提；缺少任一必要條件，只能準備預覽，不能先揭露 Secret 或請使用者授權。

外部變更預覽一起列出：既有或新建 Google Cloud project、專案擁有者、兩個 API、App 名稱、Audience、測試使用者、完整核心 scope 與選用 scope、Desktop app client、loopback callback、原生憑證庫與憑證名稱、唯讀驗證請求。使用者可移除權限；未確認的帳務、組織關聯、公開 App、上傳及留言都排除。

## Agent 操作與人工關卡

1. **開啟 Google Cloud Console。** Agent 核對登入帳號與目標專案；沒有適合的既有專案且預覽允許新建時，填入已確認的專案名稱及擁有關係。只在登入、2FA、條款或資源歸屬不明時交回使用者；不擅自建立帳單帳戶或改組織。
2. **啟用 API。** 在選定專案的 API Library 找到並啟用 YouTube Data API v3，以及需要成效時的 YouTube Analytics API；逐一讀回啟用狀態。一般頻道管理採使用者 OAuth，不能只建立 API key 就宣稱完成；Analytics 查詢同樣需要 OAuth。[YouTube Data API 授權前置作業](https://developers.google.com/youtube/v3/guides/auth/installed-apps)、[Analytics 授權憑證](https://developers.google.com/youtube/reporting/guides/registering_an_application)
3. **設定 Google Auth platform。** 進入 Branding；首次設定使用 Get Started。Agent 填已確認的 App 名稱、支援信箱及聯絡資訊，於 Audience 選 Internal 或 External，不因同一人使用就猜可用 Internal。平台要求接受資料政策時由人確認；External 測試用途只加已核准的 Test users。在 Data Access → Add or Remove Scopes 填入預覽清單，讀回再比對。這是共用 Google Auth 後台程序，不代表把 Workspace API 的 scope 加入 YouTube。[官方同意畫面設定](https://developers.google.com/workspace/guides/configure-oauth-consent)
4. **建立桌面 client。** 進入 Google Auth platform → Clients → Create Client，Application type 選 Desktop app，填名稱並建立，再讀回 client 類型。不是 Web application、Chrome Extension 或服務帳戶。Client ID 與需要的 client secret 依本包政策送入秘密儲存；不下載到公開套件或一般設定。平台只准人取得的秘密依 [Terminal 隱藏輸入流程](local-credential-storage.md) 處理。[官方建立憑證程序](https://developers.google.com/workspace/guides/create-credentials)
5. **啟動 OAuth，交回使用者同意。** Agent 準備隨機 `state`、PKCE S256 與僅綁定 loopback 的短期接收程序，再開啟官方授權頁；使用者本人核對 Google 帳號、頻道及 scope 後同意。桌面路徑可用 `127.0.0.1` 的可用本機 port；不採已停用的 OOB 手動複製授權碼，也不把 Google 的 loopback 支援推定為 Meta 支援。[Google 桌面 OAuth](https://developers.google.com/identity/protocols/oauth2/native-app)
6. **自動保存並檢查授權。** 經驗證的 OAuth 程式核對 callback／state，以 PKCE 在記憶體完成交換；access token 與 refresh token 直接寫入原生憑證庫。比對實際回傳 scope、有效期限與預覽，不把原始回應列印到工具輸出。Refresh token 不代表永久有效；到期、撤銷或刷新失敗需區分並停止，不能自動再次要求同意或重送不明交換。[Google Token 保存與刷新](https://developers.google.com/identity/protocols/oauth2/native-app)
7. **讀回而非上傳測試。** 以 `GET https://www.googleapis.com/youtube/v3/channels?part=id,snippet&mine=true` 配合程序內的 Bearer header 確認頻道；有分頁時繼續唯讀分頁，不把 `id` 或 `forHandle` 與 `mine` 混用。核對回傳 ID 與名稱是否符合已確認目標；沒有頻道、多個結果不能唯一判定或缺少 scope 時停止。這只驗證帳號路徑，不代表成效、影片上傳、留言或公開 App 審查已通過。最後顯示一般設定預覽，使用者確認後才寫入。[官方 channels.list](https://developers.google.com/youtube/v3/docs/channels/list)

## 輸出、交接與停止

分開回報 project、API 啟用、OAuth client、使用者同意、原生保存、頻道讀回與尚未測試功能。專案／頻道 ID 和秘密值留在私人秘密儲存；一般設定只保存整合意圖、scope 與有證據的分層狀態。

畫面偏離預覽、需要額外付款／組織權限、OAuth 程式不具備安全接收與交換能力，或授權／儲存結果不明時停止。不能為了避開警告改用不相容 client、OOB、服務帳戶或自行部署公開 callback。後續內容交給相應技能，本技能不做測試上傳。

## 虛構驗證

桌面 client 路徑、API key 誤選、Audience 不確定、缺少安全 OAuth 程式、scope 偏離及頻道不符的流程審查案例見套件 `tests/behavior-cases.md`。自動化虛構交換、刷新與 loopback HTTP 測試見 `tests/test_oauth_runtime.py`；不等於真實平台 OAuth。全部真實後台及平台操作集中到最後實機驗收。
