# 第 3 個技能本機候選驗證

日期：2026-09-05。social-content-writing 已實作為三技能候選 0.3.0 的一部分，待使用者確認流程；版本號不代表已發布。

## 本輪檢查

- 主文件、五份平台規格、媒體／交付契約、草稿範本、唯讀檢查器與用戶端中繼資料一起隨技能安裝，不依賴私人工作區或下載第三方程式。
- 執行 tests/validate_package.py：靜態結構、公開邊界掃描與 Python 語法通過。skill-creator quick_validate 檢查新技能通過。
- 以 SOCIAL_NATIVE_ACCEPTANCE=0、PYTHONDONTWRITEBYTECODE=1 執行全部 unittest：共 96 項，95 項通過、1 項原生憑證探測依約跳過。
- 其中 11 項新文案測試：直接／規劃入口、YouTube bytes 與標題限制、Threads 正文、Instagram caption、未知限制與不支援格式、文案核准非發布、修改後核准失效、部分核准／待查、四種媒體交接與唯讀 CLI。
- 增加兩技能到三技能的隔離安裝／升級／回復／人工修改保護測試，既有一技能到目前候選與完整生命週期仍通過。沒有安裝到使用者正式技能入口。
- [7 份虛構 Agent 案例](../tests/content-writing-cases.md) 已建立，但未執行獨立 Agent 前測；不將資料格式通過宣稱為模型行為或文案品質通過。

## 官方資料與限制

本輪讀取 YouTube videos API、Meta 官方 API／Threads 公告、Substack 官方發文說明。Meta 頁面初次工具請求遇到 429，後以公開 HTTP 直接讀取 IG User media 與 Pages Posts 文件，不登入帳號。YouTube title／description、Instagram 指定路線 caption、Threads 基本正文已核對；Facebook／Substack 未從官方內容取得通用正文上限，不沿用模型印象。各平台直接來源、日期與適用範圍保存在技能 references/platforms/。

文字預檢不是完整平台驗證器：不驗證遠端資產、連結可點擊資格、影片格式、圖片品質、標籤解析或事實真實性。核准雜湊只防紀錄漂移，不驗證人類身分，成功輸出固定 publishing_authorized: false。

## 驗收分層

| 層級 | 狀態 |
|---|---|
| 靜態結構與文件 | 上述本機檢查通過；使用者流程審查待確認 |
| 本機技能發現 | 隔離三技能入口與完整資源通過；第 3 個實際 Agent 發現／執行未測 |
| API 套件是否可安裝 | 第 3 個無新增第三方依賴；既有 OpenCLI 真實安裝仍未驗收 |
| 使用者登入與 OAuth | 本輪未執行；既有程式僅虛構測試 |
| 平台讀取 | 只讀官方公開文件，沒有實測私人帳號或內容讀取 |
| 測試發布 | 未執行；本技能僅產生本機草稿／媒體需求 |
| 另一臺電腦驗收 | 未執行，留待集中驗收 |
| 正式公開支援 | 尚未成立，未 commit／push／發布版本 |

未建立第 4 個技能，不生成圖片／影片、不發布；未修改根目錄共用文件、官網工具包、AI 知識庫或私人 newsletter。公開與私人快照維持獨立。

## 後續流程狀態（2026-09-06）

本文件保留 2026-09-05 建立當日的待確認狀態。其後本技能流程已獲准繼續下一技能；這不表示真實 Agent 對話、文案品質、平台限制或任何發布已通過。七技能統一現況見 [流程確認文件](workflow-review-status.md)。

## PACK-01 後續狀態（2026-09-06）

目前 root Agent 已對一個明確文章改寫入口完成虛構前向測試，驗證只讀選取平台、交付草稿／媒體需求且不發布。原本「未執行獨立 Agent 前測」仍為真：這不是全部 7 份案例、獨立模型、真實安裝入口、文案品質或平台限制驗收。依據見 [虛構 Agent 對話前測](agent-dialogue-preflight-local-verification.md)。
