# Substack 平台初始化

查證日期：2026-09-05。不得沿用「Substack 完全沒有官方 API」的舊說法，也不得把窄幅官方能力擴張成一般發布 API。

## 目前可證明的官方介面

- Substack 已公布 Developer API Terms，表示存在受條款管理的官方 Developer API。公開可驗證範圍偏向創作者／publication 的公開資料；目前取得的官方資料不足以證明它提供一般文章發布、留言回覆或完整成效管理。
- 官方「連接 AI Assistant」功能使用 Substack MCP，可唯讀取得 publication metrics 與設定；官方說明明確表示不能發布文章、傳送 Notes、修改帳號或存取 Notes 活動，且目前要求 Admin 與 Bestseller 資格。
- RSS、文章匯出與從其他平台匯入是官方產品介面，但不是社群發布或留言管理 API。
- 官方說明目前仍以 Substack 網站或應用程式建立與發布文章。

## 完整核心的適用方式

使用者選取 Substack 且沒有明確縮小功能時，仍應說明技能包希望支援帳號／publication 讀取、發布、公開留言、成效與私訊；但只能為目前正式介面確實支援的部分要求授權。現階段沒有足夠官方證據可建立一組涵蓋一般發布、留言管理與私訊的 OAuth permission，因此不得虛構 scope，也不得把瀏覽器登入說成 API 授權。

可證明的官方唯讀 MCP 只涵蓋符合資格 publication 的部分 metrics 與設定。發布可在使用者明確同意後採受控登入瀏覽器逐次執行；公開留言與私訊保持不支援或待查證。這些缺口必須在權限預覽中明列，而不是用「完整管理」名稱掩蓋。

## 功能判斷

| 功能 | 可採路線 | 初始化狀態 |
|---|---|---|
| 發布 | 官方網站／App；若使用者明確允許，可評估受控登入瀏覽器 | 不宣稱 Developer API 或 MCP 可發布；瀏覽器是易變備援，必須預覽、確認、讀回 |
| 公開留言 | 目前沒有經本次官方查證確認的一般留言管理 API | 保持手動或另行研究；不採內部端點與第三方套件冒充官方能力 |
| 成效 | 符合資格時可評估官方唯讀 MCP；否則使用官方產品匯出／介面或人工資料 | 資格、可讀欄位、日期範圍與登入各自驗證 |
| 私訊 | 本次官方查證沒有通用私訊自動化介面 | 不納入 MVP |

## 受控瀏覽器備援

只有正式介面無法完成已選功能、使用者明確允許操作已登入瀏覽器，且能安全預覽時才採用。每次必須：確認目標 publication 與文章、停在送出前取得確認、送出一次、重新載入並讀回公開或排程狀態、網址與時間。DOM 定位失敗、結果不明或登入狀態變動時停止；不得用未公開網路請求作為捷徑。

## 官方來源

- [Substack Developer API Terms](https://substack.com/api-tos)
- [Substack 官方 AI Assistant／MCP 說明](https://support.substack.com/hc/en-us/articles/50834026608916-How-to-connect-Substack-to-your-AI-Assistant)
- [Substack RSS](https://support.substack.com/hc/en-us/articles/360038239391-Is-there-an-RSS-feed-for-my-publication)
- [匯出文章](https://support.substack.com/hc/en-us/articles/360037466012-How-do-I-export-my-posts)
- [從其他平台匯入](https://support.substack.com/hc/en-us/articles/360037830351-How-do-I-import-my-posts-from-another-platform-such-as-Mailchimp-WordPress-Medium-or-Ghost)
- [如何發布](https://support.substack.com/hc/en-us/articles/29152946791188-How-can-I-publish-on-Substack)
