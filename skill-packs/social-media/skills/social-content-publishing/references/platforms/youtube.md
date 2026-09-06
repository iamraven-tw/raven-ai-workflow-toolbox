# YouTube 發布 adapter

查證：2026-09-06，Google 官方文件；未登入、未上傳。

## 實際執行來源

主要路徑是本技能 `scripts/publish_execute.py` 串接 `OfficialAPIAdapter`：Agent 在 `publish_job.py begin` 後執行 `execute-api`，協調器先驗證 setup Runtime，再依序 claim resumable session 與檔案 PUT、checkpoint 影片 ID，最後以 `youtube_readback` 讀回。Token 只存在 Runtime／adapter 記憶體，session URL 只留同一程序；檔案改變、308、例外、5xx 或 claimed 後中斷都不另建 session。縮圖、字幕、播放清單與跨程序安全續傳不在目前協調器最小範圍；這些步驟需要時改用已核准 Studio UI，或停下，不悄悄略過。

## 當前格式、版本與上限

YouTube 使用 Data API v3；本技能不從日期猜新版本。`videos.insert` 當前文件接受 `video/*` 或 `application/octet-stream`，單檔上限 256 GB，並支援 resumable upload。平台層另限制影片最長 12 小時；未驗證的 YouTube 帳號預設只能上傳 15 分鐘內影片。可接受的副檔名以官方清單為準，包括 MOV、MPEG 系列、MP4、AVI、WMV、FLV、3GPP、WebM、DNxHR、ProRes、CineForm 與 HEVC；純音訊檔不能直接當影片上傳。[上傳端點與檔案上限](https://developers.google.com/youtube/v3/docs/videos/insert)、[帳號影片長度限制](https://support.google.com/youtube/answer/71673)、[支援格式](https://support.google.com/youtube/troubleshooter/2888402)

官方文件目前將預設配額拆成每天 100 次 `videos.insert`，每次另計 1 個 Video Uploads quota unit；其他端點的共同預設額度是每天 10,000 units，且官方明示預設值可能變更。因此預覽只能顯示執行當下專案實際配額與帳號資格，不把本段數字當永久保證。[Data API 配額](https://developers.google.com/youtube/v3/getting-started#quota)

## 準備與預覽欄位

範圍是新影片；Shorts 是影片格式與平台判定，不另造 Shorts upload API。先核對頻道 ID、最終影片／縮圖／字幕用途、title、description、categoryId、tags、privacyStatus、notifySubscribers、selfDeclaredMadeForKids、containsSyntheticMedia。後兩項不得由預設值替人作事實判定；從影片與已知指示提出判斷，有疑義才問。settings 明列這些選項與素材用途；各檔雜湊加入 assets。

先確認可用連線含這次上傳與讀回所需 scope，upload scope 不自行視為所有頻道讀取權限。使用既有 setup 的 YouTube 連線與可信工具；缺權限交 setup，不能在發布中暗增。未經稽核的特定 API 專案上傳可能只能 private；預期 public 卻讀回 private 是未達目標，不宣稱成功。配額以執行當下官方文件與專案實際值為準，不沿用舊版固定成本。[上傳與稽核規則](https://developers.google.com/youtube/v3/docs/videos/insert)

## 執行

1. 完成共同 preview／確認／begin，才開始任何上傳。
2. 正式 API 使用 videos.insert 的 resumable upload，metadata 部分按已確認 snippet／status 傳入；原生排程要求 private 且影片從未公開，publishAt 為未來含時區時刻。不要設定過去時間，否則可能立即公開。[狀態與排程條件](https://developers.google.com/youtube/v3/docs/videos)
3. 可信執行器維持同一 upload session，不因中斷建立第二個 insert；依官方協定查詢既有 session 的進度再判斷是否可續傳，不能把網路例外當成未上傳。session URI 不進一般紀錄。取得 video ID 立即 checkpoint。失去可安全續傳證據就停止。[Resumable upload](https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol)
4. 只有預覽已包含縮圖／字幕／播放清單等附加寫入，且目前工具支援，才依下節對同一影片執行。任何附加步驟失敗都保留 video ID，不重傳影片，也不悄悄略過。
5. API 工具不可用則依共通順序評估；Studio UI 路徑為核對頻道 → 建立／上傳影片 → 選檔 → 詳細資料／觀眾與揭露／檢查 → 可見性或排程 → 比對同份預覽 → 送出一次。若 UI 自動預設的選項與預覽不同，先停；禁止第二次重新上傳「試看看」。

## 沿用既有上傳流程：同一影片的附加步驟

這段是來源流程的一般化，不新增 SDK 或命令。預覽的 settings 需列縮圖用途、字幕語言／名稱與檔案、播放清單 ID；全部由本次設定取得，不設私人預設。

1. 縮圖：核對核准圖檔及 API 格式／容量後，以 thumbnails.set(videoId) 上傳；需要轉檔時只能衍生同一核准圖片並重新核對，不自行換圖。[縮圖 API](https://developers.google.com/youtube/v3/docs/thumbnails/set)
2. 字幕：先用 captions.list(part=snippet, videoId) 查有無本工作已建立的字幕。沒有且確認本階段尚未送出，才 captions.insert(part=snippet)，帶 snippet.videoId、language、name 及核准字幕檔，隨即 checkpoint 字幕 ID。同語言／名稱已存在但無法證明來源時先停，不刪除、換名稱或重傳來躲衝突。[字幕上傳](https://developers.google.com/youtube/v3/docs/captions/insert)、[字幕讀取](https://developers.google.com/youtube/v3/docs/captions/list)
3. 播放清單：先 playlistItems.list(part=snippet, playlistId, videoId) 核對成員；已存在則讀回並記錄，不重複加入。不存在且確認未送出時，playlistItems.insert(part=snippet)，填 snippet.playlistId 與 resourceId={kind:youtube#video, videoId}，checkpoint playlist item ID，再讀回。[加入清單](https://developers.google.com/youtube/v3/docs/playlistItems/insert)、[清單讀取](https://developers.google.com/youtube/v3/docs/playlistItems/list)
4. 在尚未中斷的同一核准交易內依序處理；發生中斷、pending 或 unknown 時，只先讀回查明，不整支重跑。現有 helper 沒有授權補寫／解鎖命令；需要補做遠端寫入時回報剩餘階段與所需確認，不以「續跑」繞過交易停止規則。videos.list 僅查到影片存在不足以證明所有權，仍要比對核准頻道及實際管理權限。

字幕 list 只回傳軌道資訊，不代表字幕文字正確；要用播放器／可用的授權下載核對實際內容與時間。字幕與清單成功不替代下列影片整體讀回。

## 讀回與停止

以 videos.list(id=video ID, part=snippet,status,processingDetails) 的 owner 讀回或 Studio 重新載入，核對 channelId、完整文案、privacyStatus、uploadStatus、processingDetails 與預定時間。仍 processing 就 pending；rejected／failed 需回報平台原因但去除秘密。snippet.publishedAt 的意義隨私密／公開狀態有差異，不把上傳時刻當成正式公開時刻。[影片讀取](https://developers.google.com/youtube/v3/docs/videos/list)

從管理介面分享連結或已實際開啟的影片頁取得 URL，檢查播放／媒體與所有附加選項，再正規化 receipt。API 不回傳 permalink 欄位，不得聲稱拼出 watch URL 就是讀回驗證。published 要符合這次核准的可見性；scheduled 要有正確的 future publishAt 且仍 private。通知設定與縮圖無法由單一 GET 證明時補管理介面證據；拿不到則 pending。排程被建立不表示到時已成功公開。
