# YouTube 平台初始化

查證日期：2026-09-05。執行時若結論會影響授權、成本或公開內容，重新查閱官方文件。

建立專案、啟用 API、設定 Google Auth platform 與 Desktop app client 時，讀取 [YouTube 實際初始化](../youtube-api-setup.md)。接收、交換、刷新及頻道讀回已有 [OAuth 執行器](../oauth-runtime.md)，目前只通過虛構測試，尚未驗收真實 OAuth。

## 帳號與介面

- YouTube Data API v3 處理頻道、影片、播放清單、留言、縮圖與字幕等資源。
- YouTube Analytics API 的 `reports.query` 處理頻道或內容擁有者的成效查詢；它與 Data API 的資源讀寫是不同介面。
- 代表使用者讀寫私人或受管理資料需要 OAuth 2.0。API key 不能代替使用者授權完成上傳、留言或私人資料讀取。

## 預設完整核心權限

使用者選取 YouTube 且沒有明確縮小功能時，預設提出帳號讀取、影片上傳與管理、留言／字幕管理及非金額成效所需的完整核心 scope。Agent 必須在 OAuth 前逐項顯示 Google 的實際同意文字；以下是規劃基線，執行時仍依實際端點重新去除不必要的重複 scope：

| 核心功能 | OAuth scope | 必須揭露的影響 |
|---|---|---|
| 頻道與內容讀取 | `https://www.googleapis.com/auth/youtube.readonly` | 查看使用者的 YouTube 帳號。 |
| 影片上傳 | `https://www.googleapis.com/auth/youtube.upload` | 管理使用者的 YouTube 影片，包含上傳。 |
| 貼文、留言、字幕與評分管理 | `https://www.googleapis.com/auth/youtube.force-ssl` | 官方同意文字包含查看、編輯及永久刪除影片、評分、留言與字幕；不可只描述成「留言權限」。 |
| 非金額成效 | `https://www.googleapis.com/auth/yt-analytics.readonly` | 查看 YouTube Analytics 報告；`reports.query` 目前另要求 `youtube.readonly`。 |

完整核心不包含營收報告、頻道會員名單、內容合作夥伴資產或稽核資料。這些相鄰能力應另外詢問，分別評估 `yt-analytics-monetary.readonly`、`youtube.channel-memberships.creator`、`youtubepartner` 與 `youtubepartner-channel-audit`；預設不加入。YouTube 沒有一般頻道私訊 API，因此完整核心不包含私訊，且不得用留言冒充。

OAuth scope 只建立技術能力。上傳、刪除、留言、管理字幕或其他遠端寫入仍須由後續技能顯示實際目標與內容、取得確認並讀回驗證。

## 功能判斷

| 功能 | 官方路線 | 初始化重點 |
|---|---|---|
| 發布 | Data API `videos.insert`，通常採可續傳上傳 | Cloud project、啟用 API、OAuth scope、頻道與隱私狀態、配額與稽核 |
| 公開留言 | `commentThreads.list`、`comments.insert`、`comments.setModerationStatus` | 讀與寫權限分開；回覆或管理前確認頻道身分與留言狀態 |
| 成效 | Analytics API `reports.query` | 指標、維度、日期、擁有者身分與資料保留分開記錄 |
| 私訊 | 沒有一般 YouTube 頻道私訊 API 路線 | 不納入整合；不得以留言冒充私訊 |

## 配額、審查與驗證

- 官方配額頁目前將 `search.list` 與 `videos.insert` 各自列入每日 100 次的獨立限制，其他一般 Data API 操作使用每日 10,000 單位的預設池；不同方法成本不同，實作前重查計算表。
- 2020-07-28 之後建立且尚未通過稽核的 API project，透過 `videos.insert` 上傳的影片會受限為私人狀態；要解除需通過官方合規稽核。
- 額外配額申請會進入合規稽核；通過本機測試不等於可取得額外配額。
- 寫入前要讓使用者保有最後決定權，明確看到目標頻道、內容與可見度。
- 上傳成功回應後仍須以影片 ID 讀回 `snippet`、`status` 與可用網址；可續傳 session 或收到 ID 都不是完整驗證。

## 官方來源

- [Data API 入門](https://developers.google.com/youtube/v3/getting-started)
- [Google API OAuth scope 清單](https://developers.google.com/identity/protocols/oauth2/scopes)
- [YouTube Data API OAuth 2.0](https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps)
- [配額成本與限制](https://developers.google.com/youtube/v3/determine_quota_cost)
- [影片上傳實作](https://developers.google.com/youtube/v3/guides/uploading_a_video)
- [留言實作](https://developers.google.com/youtube/v3/guides/implementation/comments)
- [Analytics reports.query](https://developers.google.com/youtube/analytics/reference/reports/query)
- [開發者政策](https://developers.google.com/youtube/terms/developer-policies)
- [API 稽核與額外配額申請](https://support.google.com/youtube/contact/yt_api_form)
