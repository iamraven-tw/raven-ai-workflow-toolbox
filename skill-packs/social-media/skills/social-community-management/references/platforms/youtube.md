# YouTube 公開留言與回覆

查證：2026-09-06，Google 官方 Data API。`official_community_api.py` 與 `community_execute.py` 已用假 Runtime／HTTP 串接；未登入、未抓真實留言、未回覆。

## 讀取與對象

先用既有授權確認自有頻道與指定影片，只有本次範圍內公開的頂層訪客留言進 MVP。`fetch-api` 先用 videos.list 核對影片的 channelId，再以 commentThreads.list(part=snippet, videoId, textFormat=plainText) 取得討論串；內嵌 replies 可能不完整，完整回覆必須另用 comments.list(parentId=頂層留言 ID) 分頁。不要將討論串 ID 不經核對就當留言 ID，來源使用 snippet.topLevelComment.id。[官方留言流程](https://developers.google.com/youtube/v3/guides/implementation/comments?hl=en)

範圍擷取最多本批 100 則、每個列表最多五頁；到上限或仍有 nextPageToken 要記讀取不完整，不叫「沒有留言」。抓取器直接寫本機選取欄位後 ingest，不先把正文貼入主 Agent。留言關閉、權限不足、配額、空／壞 JSON 分別回報，不混成零則。

回覆前以已驗證頻道識別檢查自家直接回覆，不能只比顯示名稱。分頁未完不能宣稱 none_found_complete。MVP 不回覆第二層留言、不處理 heldForReview／垃圾留言，不偷偷發新頂層留言。

## 確認後執行

完成六欄 RAW 審核、使用者對批次說可以回覆、重新讀表與原留言後，由 `execute-api` 完成 begin、reply_create claim，再用已有 youtube.force-ssl 授權的正式 adapter 呼叫 comments.insert(part=snippet)。body 的 snippet.parentId 是核准頂層留言 ID，snippet.textOriginal 是最終 F 欄；不是 commentThreads.insert。每次插入的官方配額成本目前標示 50 units，仍須在實機執行時依當前專案額度判斷。[官方回覆 API](https://developers.google.com/youtube/v3/docs/comments/insert)

取得回覆 ID 立刻 checkpoint(reply_created)。不自動重試；403、無法回覆、原留言消失先停，不擴權、不改成另外留言。

## 讀回與備援

用 comments.list(id=reply ID, part=snippet) 獨立讀回，核對 id、parentId、textOriginal、authorChannelId 與 publishedAt。官方 comment resource 沒有 permalink 欄位，因此 API 讀回先留 pending；受控 Chrome 定位同一留言／回覆並真正重載後，才能用 `record-observation` 補精確網址。不以影片首頁或自行拼出的網址冒充。[官方 comments.list](https://developers.google.com/youtube/v3/docs/comments/list)

API 不可用時走已授權 YouTube Studio／影片留言區：核對頻道及原留言 → 展開回覆與自家回覆檢查 → 只填核准文字 → 回覆一次 → 真正重新載入並定位新回覆。UI 無法提供精確識別或時間就待人工，不猜補。

私訊不在此技能；刪除、修改與 setModerationStatus 是不同管理寫入，不隨公開回覆同意執行。
