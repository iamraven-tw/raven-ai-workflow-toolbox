# 留言擷取與回覆接線本機驗證

日期：2026-09-06。範圍為待辦 `COM-01`：補齊自有公開貼文的留言擷取、完整自家回覆檢查、核准文字回覆與獨立讀回。所有測試使用虛構資料、假 Runtime、FakeHTTP 與假瀏覽器 observation；沒有登入、讀取真實留言、寫入 Google Sheets 或回覆任何人。

## 執行來源

| 平台 | 主要路徑 | 已接流程 | 仍待實機證明 |
| --- | --- | --- | --- |
| YouTube | 官方 Data API＋受控 Chrome 網址補證 | 自有影片核對、頂層留言、完整直接回覆、`comments.insert`、GET 回覆、claim／checkpoint | 真實權限、配額、留言與回覆 permalink 定位 |
| Facebook | 官方 Graph API | 自有 Page 貼文、comments edge、完整自家回覆、文字回覆、`permalink_url` 讀回 | 真實 Page task、App Review、欄位與回覆 |
| Instagram | 官方 Instagram API＋受控 Chrome 網址補證 | 兩種 login route、自有媒體、comments／replies、文字回覆、ID／時間／父關係讀回 | 真實專業帳號、留言／回覆 permalink 定位 |
| Threads | 官方 Threads API | 自有貼文、`replies`／`conversation` 契約、直接父關係、建立容器、狀態、publish、permalink 讀回 | 真實 scope、Access Level、容器狀態與回覆 |
| Substack | 已核准 OpenCLI 受控 Chrome | 本機 fetch 證據、browser handoff、寫入前 claim、真正重載 observation | 真實登入、留言介面、穩定 ID／精確平台時間 |

機器可讀版本在 [執行來源表](../skills/social-community-management/references/execution-sources.json)。Substack 沒有使用第三方或反向工程端點冒充官方 API。

## 新增元件與安全邊界

- `official_community_api.py`：只接受固定 Google／Meta 官方主機、GET／POST 方法與留言端點，不接受 Token 查詢參數、任意 URL、重新導向或自動重試。Token 只由 setup `Runtime.access()` 在同一程序記憶體取得。
- `community_execute.py`：先保存 0600 fetch／handoff／readback 證據，再協調 queue。每次外部 mutation 前必須取得該 stage 的單次 claim；不明結果保留 unknown，阻擋下一則與重送。
- `community_queue.py`：來源增加穩定 visitor ID 與留言時間；ingest 必須綁已確認讀取範圍。Threads 的 container／publish 與一般 API／瀏覽器回覆各有獨立 claim；resume 只能續查已 checkpoint 的遠端識別。
- YouTube 與 Instagram 官方留言物件沒有供本流程使用的 permalink 欄位。API 取得的 ID、作者、時間與正文先留私人證據；沒有受控瀏覽器精確 URL 就不進六欄表或不標 replied。

## 官方查證摘要

- YouTube：`commentThreads.list` 取得頂層留言，但內嵌 replies 可能不是完整清單；完整直接回覆需用 `comments.list(parentId=...)`。文字回覆使用 `comments.insert`，不是 `commentThreads.insert`；成功後再用 `comments.list(id=...)` 讀回。
- Facebook：Meta 官方 Comment SDK 原始碼提供 comments edge，以及 id、message、created_time、from、parent、permalink_url 欄位。
- Instagram：Meta 官方 IGComment SDK 原始碼提供 id、text、timestamp、from／user、username、parent_id 與 replies edge／create_reply；沒有 permalink 欄位，因此保留混合補證。
- Threads：Meta 官方 workspace 文件提供 `/{thread-id}/replies` 與 `/{thread-id}/conversation`；reply 欄位包含 permalink、is_reply_owned_by_me、root_post、replied_to。回覆先以 reply_to_id 建容器，再用 threads_publish 發布。
- Substack：只採官方留言資格說明及受控 UI；沒有找到可作為本候選包正式寫入介面的官方公開 comments API。

## 驗證結果

以 `PYTHONDONTWRITEBYTECODE=1`、`SOCIAL_NATIVE_ACCEPTANCE=0` 執行：

- `test_community_queue.py`、`test_official_community_api.py`、`test_community_execute.py`：45 項通過，包含已建立回覆的安全續查與非預期自家回覆競態停止。
- 全套 `unittest discover`：285 項中 284 項通過，1 項真實 macOS 原生憑證探測依集中實機政策略過。
- `validate_package.py`：manifest、七技能結構、執行來源、公開資料邊界與 Python 語法通過。
- 七份技能的 `quick_validate.py` 全部通過；Markdown 相對連結／fence 由下述本機檢查通過，`git diff --check` 也通過。

上述結果只能證明本機交易與資料契約在虛構案例成立。API 套件可安裝、登入／OAuth、平台讀取、Google Sheets、真實回覆、另一臺電腦與正式公開支援均未驗收。

## 分層狀態

| 層級 | 狀態 |
| --- | --- |
| 靜態結構與文件 | 已通過本機驗證 |
| 本機技能發現 | 未執行真實 Agent 發現；只有套件結構檢查 |
| API 套件是否可安裝 | 沒有新增 SDK；Python 程式只用標準函式庫，未做第三方安裝 |
| 使用者登入與 OAuth | 未執行 |
| 平台讀取 | 未執行；FakeHTTP 不代表真實平台 |
| 測試發布／回覆 | 未執行 |
| 另一臺電腦驗收 | 未執行 |
| 正式公開支援 | 尚未成立 |
