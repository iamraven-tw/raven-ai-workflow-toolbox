# Substack 成效

查證日期：2026-09-05。不能再籠統寫成「Substack 沒有官方 AI 讀取途徑」。

## 官方支援與備援

Substack 官方提供唯讀 MCP，可讀出版物成效、流量、訂閱及留存等；目前同時要求出版物 Admin、Bestseller 出版物與支援 MCP connector 的客戶端，不能發布或修改帳號，也不能讀 profile／Notes 活動。先檢查使用者是否已有這個授權連接器，不自動建立或登入；只有「已連接」而無上述資格不能標成可用。[官方 AI Assistant 連接說明](https://support.substack.com/hc/en-us/articles/50834026608916-How-to-connect-Substack-to-your-AI-Assistant)

這不是所有使用者都能用的通用公開 REST 成效 API。本次未查得可供所有出版物使用的正式通用 REST 規格；不得把內部端點或第三方套件描述成官方 API。RSS 是內容發現途徑，不能代替完整成效。無合資格 MCP 時依序看[官方出版物匯出](https://support.substack.com/hc/en-us/articles/360037466012-How-do-I-export-my-posts)、已有可靠且授權的 OpenCLI／受控瀏覽器。OpenCLI 指令與欄位須先讀現有版本說明，不猜名稱；需要登入交回使用者。

本包不建立 Substack REST client。Agent 用上述正式來源保存最小原始證據後，建立 `performance_source_observation` artifact；`performance_collect.py collect-import` 核對平台、出版物參照、metric 定義、期間、時區、來源介面、`eligibility` 與原始證據雜湊，再轉成共通 dataset。MCP 固定要求 `admin_bestseller_mcp_connected`；匯出與受控瀏覽器使用各自較低但明確的帳號讀取資格。只有手動填寫的數字、RSS 或沒有原始證據的摘要會停止，不能宣稱已串接。

## 指標與定義

按深度閱讀、訂閱或留存角色選 total views、open rate、link clicks、文章帶來的訂閱、訂閱總量／流失。Total views 包含網頁、email、App 的重複觀看；open rate 是收到 email 或 App 後閱讀的訂閱者比例，不應只叫「email 開信率」，更不等於讀完全文；link clicks 同時有開啟者比例與總點擊數，不能混成一個欄位。使用官方分母與原標籤。[官方指標指南](https://support.substack.com/hc/en-us/articles/5320347155860-A-guide-to-Substack-metrics)

官方曾更新 App 收件與閱讀的計算方式，可能影響新舊文章比率；舊資料與新報表口徑不一致時標 definition_changed，不能斷言策略改善造成成長。[官方 Posts 頁變更說明](https://support.substack.com/hc/en-us/articles/15853567274772-Guide-to-your-Substack-Posts-page)

## 私人資料與比較

只抓必要聚合數字，不匯出訂閱者姓名、email 或信用卡資料。每篇累積表現需固定發布後觀察天齡；本版 helper 的機器白名單只接受明確期間 `traffic_views` 與期末 `total_subscribers`／`paid_subscribers` 快照，lifetime 單篇另列描述。Gross annualized revenue 是以目前付費訂閱年化的快照，不是本期實收；本版不把它放進期間營收序列。

保存介面種類、出版物參照、原標籤、期間、時區、讀取時間與定義；工具未提供的欄位標 unavailable。不合資格的連接器或失敗讀取不能填零；能力不足時停在匯出檔或資料限制摘要。artifact 正規化已通過虛構檔案測試，但真實 MCP、匯出與瀏覽器尚未驗收。
