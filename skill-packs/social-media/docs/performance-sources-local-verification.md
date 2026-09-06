# 五平台成效資料來源本機驗證

日期：2026-09-06。完成待辦 PERF-01 的本機接線；沒有登入、OAuth、Token 刷新、真實平台讀取、MCP 連線、匯出私人資料、瀏覽器操作、策略寫回、安裝第三方工具、commit 或 push。

## 已實作範圍

- `official_performance_api.py`：以 Python 標準函式庫實作固定 GET allowlist，接 YouTube Analytics API v2、Facebook Page Insights、Instagram Account Insights 與 Threads Account Insights。每次只查一個帳號層 metric；核對 setup Runtime 的帳號、登入路徑、必要 scope 與當次讀取確認。
- Token 只在可信程序記憶體及 Authorization header 使用；禁止放 query。保存證據前會移除 access token、Authorization、Cookie、client secret 欄位及回應字串中的實際 Token。
- `performance_collect.py`：把四平台 API 回應或 Substack／官方匯出／受控瀏覽器的來源 artifact 轉成原有 schema 1 dataset。私人證據使用 0600 建立，保存平台、帳號參照、期間、時區、metric／定義、介面、API 版本、查詢、取回時間、涵蓋及去敏感回應。
- Substack 不建立未公開 REST client。優先來源是合資格的官方唯讀 MCP；不適用時才用官方匯出或已核准受控瀏覽器。artifact 必須綁定私人 performance 目錄內原始證據雜湊；手填數字或 RSS 不會被稱為 API／MCP 整合。
- 收集中斷時，只重用相同 collection plan 與 request hash 的既有證據；計畫、來源或 dataset 不同就停止，不盲目再次消耗 API 配額。

來源選擇、輸入格式及停止條件見[資料來源契約](../skills/social-performance-analysis/references/performance-source-contract.md)與[機器可讀來源表](../skills/social-performance-analysis/references/execution-sources.json)。

## 官方查證依據

- YouTube 官方 `reports.query` 是 `GET https://youtubeanalytics.googleapis.com/v2/reports`，目前列出 `youtube.readonly` 與 `yt-analytics.readonly`；`startDate`／`endDate` 都納入查詢，且回應可能只涵蓋所有要求指標都有資料的最後一日。[YouTube Analytics Reports Query](https://developers.google.com/youtube/analytics/reference/reports/query)
- Meta 官方 Instagram 文件分開列出 Instagram Login 與 Facebook Login 的 insights 權限、host、帳號／媒體端點；部分指標受追蹤者門檻或最長 90 天資料限制影響，空 data 不能當零。[Instagram Insights 官方集合](https://www.postman.com/meta/instagram/folder/23987686-f659d7d1-d74c-44e4-9192-9b1e8694c511)
- Threads 官方帳號 insights 端點為 `/{threads-user-id}/threads_insights`；目前採用的官方範例沒有足以讓本包宣稱任意完整曆期的日期查詢，因此第一版不自行發明參數。[Threads Account Insights](https://www.postman.com/meta/threads/request/4pbwq2u/get-account-insights)
- Facebook Page Insights 官方開發者網頁本次仍無法穩定讀取；Meta 官方 Business SDK 原始碼可確認 Page 與 PagePost 都有 GET `/insights`，參數含 metric、period、since、until，但不能據此推定舊 metric 仍可用。[Meta Business SDK Page 原始碼](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/page.py)、[PagePost 原始碼](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/pagepost.py)
- Substack 官方提供有 Admin／Bestseller 資格限制的唯讀 MCP，可讀出版物即時資料但不能發布或修改；另有官方出版物匯出。兩者都不是供所有出版物使用的通用公開寫入 REST API。[Substack AI Assistant](https://support.substack.com/hc/en-us/articles/50834026608916-How-to-connect-Substack-to-your-AI-Assistant)、[出版物匯出](https://support.substack.com/hc/en-us/articles/360037466012-How-do-I-export-my-posts)

## 涵蓋與資料狀態

- YouTube：內部尾日不含，送 API 時轉成最後納入日；聚合有值後另查 `dimensions=day`。逐日完全吻合才是 complete，缺日為 partial，沒有逐日資料為 unknown；聚合 rows 缺漏是 unavailable，不是零。
- Facebook／Instagram／Threads：adapter 已能取得及保存帳號層單一 metric，但本輪沒有完成所有當前 metric 的期間、分頁、保留與定義證據。coverage 保守固定 unknown，所以既有分析器不會計算一般期增減。
- 明確權限不足、metric 無效／停用、限流／網路錯誤、空資料與真正零分別保留為 permission_denied、definition_changed、read_failed、unavailable 與 available=0。
- Meta 多點 values 只有 total 可以加總，snapshot 只取最後值；unique、average、rate 沒有安全單值時停止。

## 驗證結果

- `test_official_performance_api.py` 與 `test_performance_collect.py`：14 項全數通過。涵蓋官方主機 allowlist、端點、Token 不進 query／證據、scope／目標核對、YouTube 日期與逐日 probe、Meta 保守 coverage、Threads 不發明日期參數、Substack 原始證據雜湊、錯誤狀態、中斷續跑及 CLI 不輸出成效數字。
- 加上原有 `test_performance_review.py`：成效技能 40 項全數通過。
- `validate_package.py`：manifest、必要檔案、來源表、公開邊界、Markdown 相對連結與 Python 語法通過。
- 社群媒體整包：361 項離線測試，360 項通過；1 項原生憑證實機探測依集中驗收政策略過。
- 所有測試都使用虛構帳號、假 Runtime／HTTP 或暫存工作區，未使用任何私人來源資料。

## 尚未驗收與下一項

PERF-01 只表示資料來源選擇、最小接線、證據正規化及離線測試完成，不表示平台資料真實、metric 當前可用、App Review／scope 已通過或帳號讀取成功。

下一項 PERF-02 仍需逐一確認實際要使用的指標與期間口徑，尤其是 Facebook Page Insights 當前 metric／限制、Instagram 的 metric_type／期間組合、Threads 帳號資料的可證明期間，以及 Substack 帳號是否符合官方 MCP 資格。完成 PERF-02 後，才能把有充分證據的平台 coverage 從 unknown 改成 complete；不能只因 API 回傳一個數字就提升狀態。

| 驗收層級 | 本次狀態 |
| --- | --- |
| 靜態結構與文件 | 通過 |
| 本機技能發現 | 未執行；留集中驗收 |
| API 套件是否可安裝 | 未新增 SDK；只使用 Python 標準函式庫 |
| 使用者登入與 OAuth | 未執行 |
| 平台讀取 | 未執行；只有假 Runtime／HTTP |
| 測試發布／回覆／策略實機寫回 | 未執行，且不屬本項授權 |
| 另一臺電腦驗收 | 未執行 |
| 正式公開支援 | 尚未成立 |

## 2026-09-06 後續狀態：PERF-02

上方「下一項 PERF-02」保留 PERF-01 完成當下的歷史狀態。後續已完成官方指標目錄與執行限制：YouTube 固定十項白名單與來源時區；Facebook／Instagram 以當次正式 description／period 驗證而不信任 SDK enum；Threads 排除追蹤者快照、人口統計及貼文 lifetime；Substack artifact 必須記錄介面對應 eligibility。詳見[五平台成效指標目錄與口徑本機驗證](performance-metric-catalog-local-verification.md)。真實平台資料、權限、涵蓋與 MCP 資格仍未驗收，不能因此把 coverage unknown 改為 complete。
