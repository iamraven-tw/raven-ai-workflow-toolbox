# 自有內容修改與刪除

查核日期：2026-09-13。這是既有 `publish_job.py`／`publish_execute.py` 的管理模式，不是另一個技能或背景服務。程式與虛構測試已建立；沒有執行真實刪文、改文或影片修改。

## 本輪支援範圍

| 平台 | 本機執行器 | 必要限制 |
| --- | --- | --- |
| Facebook | 已發布 Page 貼文刪除；同 App 貼文文字修改 | 不刪整個 Page；修改限該 App 建立內容；排程／未發布貼文刪除尚未接線 |
| Instagram | Facebook Login 路線的自有動態、Reels、整個輪播刪除 | 原生庫另存並驗證 Facebook User Token；不刪單一輪播子項、不改 caption；Stories 尚未接入列表，廣告媒體由平台拒絕 |
| Threads | 自有貼文刪除 | threads_basic＋threads_delete；不修改文字、不處理私訊；目標必須在自己的貼文列表讀回 |
| YouTube | 指定影片刪除；標題與說明修改 | 不重新上傳；不修改可見性、排程或媒體檔。更新保留分類、標籤、預設文字語言；已有 defaultAudioLanguage 時，因目前 update 文件未列其可寫性，停止並揭露缺口，不冒險清除 |

刪除通常無法復原。前置快照是識別與確認證據，不是內容或影片備份；不要向使用者保證可還原。既有 OAuth 不代替本次刪除確認；只取得相應功能所需的已核准權限，不重跑其他平台設定。

## 前置讀取與一次確認

1. 沿用使用者指定帳號及內容 ID／網址；不猜目標、不先產生刪除動作。用 `inspect-content` 讀取精確目標與擁有者，將選取的內容、版本及安全識別資料寫進私人工作區。這個入口只讀，不需要先建立發布帳本，也不捏造發布 grant。
2. Agent 讀取私人快照，以完整標題／文案、確切帳號及內容識別向使用者呈現目標；含媒體時還要展示該內容或已核對的管理頁，不以相同文案猜媒體。YouTube API 沒有永久連結欄位，快照 url=null，不宣稱拼接網址是 API 讀回證據。
3. 修改展示新舊差異；刪除明示刪的是整篇／整支影片及不可復原風險。確認可以涵蓋一整批，不要求人填 JSON，也不重複詢問同一份預覽。

以下命令由 Agent 操作；值均取自私人工作區，不包含秘密：

```sh
python3 scripts/publish_execute.py inspect-content --workspace <私人工作區> --platform <平台> --target-id <帳號ID> --resource-id <內容ID> --snapshot social-media/publishing/<job>/before.json --confirm-read
```

只保存已授權取得的快照，不覆寫同名 before.json。沒有可用連線交 setup；本入口不刷新、不重做 OAuth、不列印私人內容。`Runtime.access()` 在可信程序內取用 Token；Instagram 刪除另呼叫 `Runtime.access_instagram_user()`，不由 Agent 讀庫或搬運秘密。

## 沿用 plan、begin 與執行

plan 的共同欄位仍見 [交易契約](publishing-contract.md)。管理項目固定 `interface=official_api`、`assets=[]`、`scheduled_at=null`，不要為刪除既有媒體要求再找本機原檔。

- 四平台刪除：`action=delete_content`；settings 固定 `{resource_id, before}`，before 是 inspect-content 的完整快照；item.title／body 與快照相同。format 表示實際內容格式，不代表要再上傳。
- YouTube 修改：`action=update_content`、format=video；settings 同上，item.title／body 是新標題及新說明。發出 PUT 前重新核對快照並保留 snippet 的既有可寫欄位；只送 part=snippet，不夾帶 status。
- Facebook 修改：沿用 [文字修改欄位](publishing-contract.md#facebook-文字修改)；從快照取 id、body、version 對應 post_id、before_message、before_updated_time。只送 message。

Agent 執行 preview → 對話確認 → begin → execute-api。共用 CLI 的 `--confirm-publish` 是歷史名稱，管理模式只代表已確認這份修改／刪除，不取得額外發布權限。每個非冪等動作先 claim、受理後 checkpoint；任何未知結果不重送、不改 job 或介面繞過。刪除去重綁定平台、帳號與內容 ID，不因修改文案或快照就允許再刪一次。

快照比對不是原子條件更新：比對至送出之間仍可能有其他人修改。偵測到不同版本即停止；不要宣稱完全排除並行操作。

## 刪除與修改驗證

- 刪除必須先取得確切受理證據：Facebook success=true；Instagram／Threads 另需 deleted_id 相符；YouTube HTTP 204。Threads 刪除依當前文件使用 graph.threads.com；既有讀取仍走已支援的 graph.threads.net，傳輸白名單分別限制方法及路徑。
- 隨後重新驗證連線並獨立 GET：YouTube 指定 ID 回空 items；Meta 在自有 feed／media／threads 列表中完整列舉後確認不存在。最多五頁，只用 after 游標呼叫固定端點，不跟隨 next 網址；超限、漏頁、循環、權限错误或讀取失敗只能 pending／unknown，不能把 404 當成功。
- 同時有刪除 checkpoint 與完整查無證據才記 deleted。刪除沒有平台時間與可用永久連結，receipt 的 platform_time／url 保持 null，只記真實 observed_at。
- YouTube 修改獨立讀回新標題、說明、保留的 snippet 欄位及未變的可見性才記 updated；不將舊 publishedAt 當更新時間。Facebook 仍依實際 updated_time 讀回。
- pending／unknown 只允許唯讀查明，不能重送；已知受理且查無證據不足時，可以沿用 record-observation 補受控管理介面證據，但必須符合相同目標及證據格式，不捏造已刪除。

## 官方來源

[Facebook 貼文](https://developers.facebook.com/documentation/pages-api/posts)、[Instagram 媒體刪除](https://developers.facebook.com/documentation/instagram-platform/reference/instagram-media)、[Threads 刪除](https://developers.facebook.com/documentation/threads/posts/delete-posts)、[YouTube 刪除](https://developers.google.com/youtube/v3/docs/videos/delete)、[YouTube 更新](https://developers.google.com/youtube/v3/docs/videos/update)。Instagram 文件的 Request Syntax 與範例有不一致文字；依 Deleting 的 DELETE 與成功範例，不複製無關的 comment_enabled 參數。
