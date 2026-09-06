# Threads 平台初始化

查證日期：2026-09-05。以 Meta 官方 Threads Postman workspace、權限說明與官方範例 repository 為主要依據。

執行本文件前先讀 `../meta-api-setup.md`。使用者只要選取 Facebook、Instagram 或 Threads 任一平台，就在同一次 Meta 初始化中詢問是否也設定另外兩個；共用的是引導、盤點與預覽，Threads 的 App、OAuth、Token 與驗證證據仍分開處理。

## 帳號與授權

建立具有 Threads use case 的 Meta App，使用 Threads 專用 App ID／secret 與 OAuth 流程。redirect URI 必須符合官方要求；官方範例特別提醒正式 HTTPS redirect 的需求。實際權限與端點仍以執行當天的官方文件及 changelog 為準。

使用者選取 Threads 且沒有明確縮小功能時，預設申請目前受支援的完整社群管理核心權限：

| 核心功能 | permission | 用途 |
|---|---|---|
| 帳號讀取 | `threads_basic` | 讀取 Threads 個人檔案與支援的基本內容資料。 |
| 發布 | `threads_content_publish` | 建立並發布文字或媒體內容。 |
| 公開回覆讀取 | `threads_read_replies` | 讀取貼文回覆與對話。 |
| 公開回覆管理 | `threads_manage_replies` | 回覆及管理支援的回覆狀態。 |
| 成效 | `threads_manage_insights` | 讀取帳號與貼文 insights。 |

Threads 目前查證範圍沒有一般私訊管理 API 或 DM permission，所以完整核心不包含私訊。必須明確告知使用者這是平台不支援，不是漏申請；不得把公開回覆 API 冒充私訊。

## 功能判斷

| 功能 | 官方路線 | 初始化重點 |
|---|---|---|
| 發布 | 建立文字／媒體 container，再 publish | 媒體可取用性、container 狀態與發布後讀回；每次寫入仍另行確認。 |
| 公開留言 | 讀取 replies／conversation、回覆、隱藏或取消隱藏 | 根回覆與巢狀對話分開，逐則操作後讀回。 |
| 成效 | 貼文與帳號 insights | 指標窗口與缺值狀態，不把無資料自動記為 0。 |
| 私訊 | 目前沒有一般 Threads 私訊管理路線 | 不納入；不得用回覆 API 冒充私訊。 |

## 初始化與驗證

1. 在同一份 Meta 外部變更預覽中逐平台列出 Threads App/use case、完整 permission、OAuth、redirect URI 與審查需求。
2. 使用者可在 OAuth 前刪除任一受支援核心 permission；刪減後把 Threads 記為 `custom`，並列出失去的功能。
3. Agent 完成可安全代辦的 App、Threads use case、redirect URI 與 permission 設定；登入、安全驗證、條款與 OAuth 同意才交回使用者。
4. 使用 [專用 OAuth 程式](../instagram-threads-oauth.md) 接收 code、換長 Token、原生保存，並由官方 debugger 及 `/me` 讀回實際 scope、期限與 Threads 帳號；缺少、增加或資源不符都停止，不自動重做授權。日後只能在已核准範圍內按需刷新仍有效且至少 24 小時的長 Token。
5. 只把 App、OAuth 與安全唯讀資源讀回標為已驗證。取得寫入 scope 不代表發布、回覆或 insights 已實測。

container ID 只代表建立階段。後續發布必須讀回 Threads 貼文 ID、permalink、實際時間、文字／媒體與可見狀態；回覆與隱藏操作逐則讀回，結果不明時停止且不重送。

## 官方來源

- [Meta 官方 Threads Postman workspace](https://www.postman.com/meta/threads/overview)
- [Threads API 官方 Postman 文件](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api)
- [Meta 官方 Threads API 範例](https://github.com/fbsamples/threads_api)
- [Meta permissions](https://developers.facebook.com/docs/permissions/)
- [Meta App Review](https://developers.facebook.com/docs/app-review/)
