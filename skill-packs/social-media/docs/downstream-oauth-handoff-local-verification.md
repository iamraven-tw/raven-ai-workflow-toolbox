# 下游 OAuth 交接本機驗證

日期：2026-09-06。範圍為待辦 `INIT-03`：對齊 `social-content-publishing`、`social-community-management`、`social-performance-analysis` 的 Instagram／Threads 連線說明。只修改公開技能文件、行為案例與靜態契約；沒有讀取原生秘密、呼叫平台、發布、回覆或擷取成效。

## 對齊結果

- 三個技能的主流程都明定：採套件 Meta API 路徑時，可信 adapter 只能在同一程序透過 `social-media-setup` 的 `Runtime.access()` 取用並驗證 Token，不直接讀原生秘密庫分段，也不把 Token 放進模型、對話、命令列或一般資料檔。
- Instagram 平台文件分開 `instagram_login` 與 `instagram_facebook_login`。前者使用 Instagram User Token／`graph.instagram.com`；後者使用相連 Page Token／`graph.facebook.com`。登入路線、host 與 Token 不得混用。
- 直接 Instagram Login 的初次 scope、當前基本身分與逐功能端點證據分開。發布由 container／publish、留言由 comments、成效由 insights 端點判定；單一成功不推定其他功能。
- Threads 透過同一 runtime 使用自己的長期 User Token；每次由官方 debugger 核對目前 scope，再以 `/me` 核對帳號。不得拿 Facebook Page 或 Instagram Token 替代。
- Runtime 只負責 OAuth、秘密取用、刷新與身分／可查 scope 證據，不是發布、留言、Sheets、私訊或成效資料擷取器，也不取代各技能原有的預覽、確認與讀回。
- 較早驗證文件保留當時內容，只追加日期明確的後續狀態，不改寫舊結果。

## 虛構驗證範圍

發布、互動及成效的 Agent 行為案例都加入 setup OAuth 已存在的情境：應使用 `Runtime.access()`、維持各自遠端確認關卡，並處理直接 Instagram Login 的功能證據限制。套件靜態驗證器檢查三個主技能與六份 Instagram／Threads 平台文件均含正確交接、登入路線和功能端點邊界；這是文件契約檢查，不是 Agent 對話或平台實測。

| 層級 | 結果 |
|---|---|
| 靜態結構與文件 | 套件驗證器與差異空白檢查通過；檢查三個主技能、六份平台文件、三份虛構行為案例、相對連結、隱私與語法 |
| 三個技能格式 | `social-content-publishing`、`social-community-management`、`social-performance-analysis` 的 quick validation 全部通過 |
| 本機技能發現 | 整包隔離安裝生命週期通過，三個技能仍進入安裝候選；未執行真實 Agent 技能探索 |
| API 套件是否可安裝 | 沒有新增第三方套件或 API driver |
| 使用者登入／OAuth | 未執行；本輪只對齊已存在 runtime 的文件交接 |
| 平台讀取 | 未執行 |
| 測試發布／回覆／成效擷取 | 未執行 |
| 另一臺電腦驗收 | 未執行 |
| 正式公開支援 | 尚未成立；未 commit、push 或發布版本 |

整包回歸共 241 項，240 項通過、1 項原生環境探測依政策略過。案例文件與靜態契約不等於三個真實 Agent 對話已執行；該層仍留待 `PACK-01`。

完成 `INIT-03` 只表示下游不再誤稱缺少 OAuth，也不會因 OAuth 存在就宣稱功能 driver 已串接。真正執行介面仍由後續 `PUB-*`、`COM-*`、`PERF-*` 待辦處理。
