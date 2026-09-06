# 第四技能本機候選驗證

日期：2026-09-05。候選版本：0.4.0，未 commit、未發布。第 3 個技能流程已確認，本輪只建立 social-image-production；第 4 個待使用者流程確認，未開始第 5 個技能。

## 四路製圖與初始化偏好調整

依使用者後續要求加入 Codex、Antigravity、網頁模型與 HTML＋CSS 四種方式；一般設定升為 schema 4，保留 schema 3 既有交易相容，只在預覽確認後新增圖片偏好，不自動遷移私人工作區。image_routing.py 是唯讀選路器：內建工具不重問、網頁預設提示詞、代操作需當次請求、資訊密集偏好與當次明確指示的優先順序皆有測試。HTML／CSS 自有範本及免費 SVG 來源規則已加入，沒有實際瀏覽器截圖、下載圖示或呼叫模型。

本次調整後全套 **121 項：120 通過、1 項原生憑證探測依政策跳過**。新增 6 項分流、2 項設定升級／授權欄位拒絕及 1 項 HTML 成品紀錄測試；HTML 紀錄以 Pillow fixture 檢查契約，不是假稱 HTML 已渲染。schema 3→4 的實際 preview／apply 虛構交易證明確認前正式設定不變，確認後保留原策略與平台整合。兩個修改技能均通過 quick_validate，套件靜態及 git diff --check 通過。下方 112 項為最初建立時的歷史結果。

分層狀態仍以下表為準：本輪只增加本機設定／選路／原稿與虛構程式驗證，不增加真實 Agent 發現、API 套件安裝、登入／OAuth、平台讀取、發布、另一臺電腦或正式公開支援證據。四路真實執行、SVG 實際使用、HTML PNG 匯出、模型與中文視覺品質仍待集中驗收。

## 新增範圍

主流程、發現 metadata、製作／視覺檢查規範、備援／紀錄契約、中性簡報範本、image_assets.py 與虛構案例。AI 生圖為主要路徑；文字備援產出真實 PNG，檔案 checker 處理 PNG／JPEG 解碼、像素、容量、順序、SHA-256、圖片核准失效與交接阻擋。Pillow 是可選的既有執行環境需求，不是安裝器新增下載。

## 本機驗證方式

在套件目錄執行：

```text
SOCIAL_NATIVE_ACCEPTANCE=0 PYTHONDONTWRITEBYTECODE=1 python3 tests/validate_package.py
SOCIAL_NATIVE_ACCEPTANCE=0 PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
python3 <skill-creator>/scripts/quick_validate.py skills/social-image-production
git diff --check
```

本輪總計 112 項：111 通過、1 項原生憑證探測依集中實機驗收政策跳過。圖片新增 15 項（含缺少 Pillow 的停止測試）；另外增加三技能升四技能、同名衝突、回復與修改保護測試。既有一／兩技能升級測試一併覆蓋四技能目標。所有安裝只在虛構暫存入口執行，未安裝到使用者正式 Agent 目錄。

Pillow 12.1.1 執行全套；既有 12.3.0 另跑圖片 15 項，結果記錄在本次交付。真實 PNG 僅以虛構 Latin 文字與既有測試字型渲染至暫存目錄，未呼叫 AI、未安裝套件、未使用私人素材。中文和實際 Agent 圖片品質案例仍待集中驗收。

## 驗收分層

| 層級 | 本次結果 |
|---|---|
| 靜態結構與文件 | 套件 validator、技能 frontmatter、連結／公開資料邊界與 Python 語法檢查通過 |
| 本機技能發現 | 四技能隔離入口及安裝生命週期通過；第 4 個真實 Agent 發現／對話行為未驗收 |
| API 套件是否可安裝 | 未新增平台 API SDK；OpenCLI 真實安裝未驗收；Pillow 只驗證既有環境，新安裝契約未完成 |
| 使用者登入與 OAuth | 未執行，集中留後 |
| 平台讀取 | 未執行 |
| 測試發布 | 未執行；圖片 helper 永遠回報 publishing_authorized=false |
| 另一臺電腦驗收 | 未執行；不同 Python 執行環境不是另一臺電腦 |
| 正式公開支援 | 未宣稱支援，仍為四技能本機候選 |

另列圖片能力：本機程式化 PNG 已通過虛構測試；AI 模型、實際素材上傳、中文字形、人工視覺確認、模型費用與五平台接受均未驗收。使用者核准雜湊只是一致性檢查，不是本人簽章或發布授權。

## 後續流程狀態（2026-09-06）

本文件保留 2026-09-05 建立當日的待確認狀態。其後四路製圖流程已獲准繼續下一技能；這不表示模型生圖、瀏覽器操作、HTML 匯出或人工視覺驗收已通過。七技能統一現況見 [流程確認文件](workflow-review-status.md)。

## PACK-02 後續狀態（2026-09-06）

四路集中驗收需要的共用品牌簡報、1080 × 1350 三頁輪播、1080 × 1080 方形重排、三份完整網頁提示詞、安全 HTML＋CSS 原稿、469 字元溢位負例及 `not_run` 結果範本已備妥，並通過 6 項 fixture 靜態測試。這只是驗收準備；Codex／Antigravity 生成、網頁模型操作、HTML renderer、中文字型、實際看圖與人類成圖核准仍未執行。依據見 [四路驗收準備](image-acceptance-preparation-local-verification.md)。
