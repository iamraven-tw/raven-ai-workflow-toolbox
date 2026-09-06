# 第六技能本機候選驗證

日期：2026-09-05。候選版 0.6.0，六個技能可納入離線安裝；第 6 技能等待使用者流程確認，第 7 技能尚未建立。未 commit、push、發布版本、登入、安裝第三方工具、操作試算表、抓真實留言或回覆。根目錄、AI 知識庫及官網技能的既有／並行修改保持不動。

## 實作

- social-community-management：明確觸發、輸入／輸出、平台分流、確認與停止關卡；五份平台文件、Sheets／分類器／本機交易契約。
- community_queue.py：固定規則篩查與隔離、來源版本／去重、語意審查結果綁定、六欄 RAW payload、表格型別讀回、來源映射、最終 F 欄核准、一次性 begin、checkpoint、精確回覆讀回與持久狀態。
- 無網路、無憑證呼叫、無模型或背景工作。沒有內建平台／Sheets HTTP transport、Google OAuth 或隔離 AI runtime。現有可信工具必須滿足契約才可執行；不把文件稱作已串接。
- 安裝 manifest 增加第六技能，保留舊版一至五技能升級、同名衝突、人工改動保護、回復與可回復移除；不變更一般設定 schema 5、不觸碰私人狀態。

## 來源與一般化

只讀查閱既有私人留言監控的入口、固定規則、準備、平台讀取與回覆程式，未執行腳本或讀取憑證。沿用「不向主 Agent 直接輸出原留言」「空回應不是零則」「先查是否已有自家回覆」「逐則讀回」的行為；未複製私人品牌尾綴、固定字數／語言、帳號名稱、Token 路徑、排程、舊 API 版本或內部 Substack 端點。原來源不是六欄 Sheets 版本的實機驗收。

Google 官方 comments insert/list/resource 與 Sheets RAW／CellData 已重新查閱；Meta 以官方 Comment／IGComment 原始碼與官方 Postman 核對。本次 Meta 部分 HTML 429／失敗，Threads 完整讀回 edge 的官方查證仍有限，因此平台文件保留執行前刷新或 UI 備援條件。Substack 依官方留言資格文件，只提供受控 UI 路徑，不冒稱有公開寫入 API。

## 保留限制

1. 固定規則不是完整注入防護；隔離 AI runtime 由宿主實際提供，沒有則先人工審查。
2. 六欄允許人工修改 F，技術上無法可靠區分單獨排序 F 的錯置與刻意改稿；需核對配對、只做整列排序。回覆前雖重讀，仍有最後讀取與送出之間的競態窗口。
3. 有介面拿不到精確留言 URL／ID／時間時，該項不冒充完成；IG 留言連結與部分瀏覽器讀回能力待實機確認。
4. pending／unknown／failed 阻擋後續與重送；沒有解鎖重發或自動清理，不能把人工修復說成已自動續跑。
5. MVP 為自有公開內容的頂層訪客留言與文字回覆。私訊執行、刪除／隱藏／封鎖、Notes／Chat、付費留言、排程及 Webhook 不在目前範圍。
6. 權限、對話確認、資料來源及證據真實性仍由可信工具與人類確認；本機雜湊／旗標不能證明本人同意或平台回應真實。

## 驗證紀錄

以 PYTHONDONTWRITEBYTECODE=1、SOCIAL_NATIVE_ACCEPTANCE=0 執行：

- 套件 validate_package.py 通過，涵蓋結構、契約、公開邊界及 Python 語法。
- 全套 166 個測試中 165 個通過，1 個真實原生憑證探測依集中驗收政策跳過；包含六技能隔離安裝、一至五技能升級、衝突、回復及移除。
- 第六技能 24 個測試通過，含五平台共用流程的虛構端到端案例；最後補上 POSIX 目錄 fsync 後，再跑這 24 個測試通過。
- 六份 SKILL.md 的 quick_validate 通過；第六技能相對連結與 Markdown fence 檢查通過；git diff --check 通過。

測試使用虛構留言、假儲存格型別與假平台證據，不呼叫 API、Sheets、模型或秘密儲存。不宣稱已完成真實 Agent 對話前測、隔離 runtime 測試或平台回覆。

## 分層回報

| 層級 | 本次範圍 |
| --- | --- |
| 靜態結構與文件 | 檢查 manifest、技能資源、語法、隱私、Markdown 與契約 |
| 本機技能發現 | 六技能隔離安裝入口與雜湊；不是第六技能的真實 Agent 發現／前測 |
| API 套件可安裝 | 沒有新增 SDK 或安裝測試；helper 只用標準函式庫 |
| 使用者登入／OAuth | 未執行；Google Sheets 與社群憑證不互相替代 |
| 平台讀取 | 未執行；公開官方文件查證不是讀取使用者留言 |
| 測試發布／回覆／Sheets 寫入 | 未執行，依使用者指示集中留到最後 |
| 另一臺電腦驗收 | 未執行，Windows 檔案權限與真實工具另驗 |
| 正式公開支援 | 尚未成立，不以私人來源成功或離線測試推定 |

## 後續流程狀態（2026-09-06）

本文件保留 2026-09-05 建立當日「第六技能待確認、第七技能尚未建立」的歷史狀態。其後本技能流程已獲准繼續建立第七技能；這不表示平台留言、Google Sheets、隔離 AI 或私訊已接通或實測。七技能統一現況見 [流程確認文件](workflow-review-status.md)。

其後 `COM-01` 已新增四平台正式 API adapter 與交易協調器：Facebook／Threads 可由官方 permalink 欄位完成契約讀回；YouTube／Instagram 保留受控瀏覽器網址補證；Substack 採受控 Chrome handoff。這只通過假 Runtime／HTTP／observation 的本機整合測試，沒有改寫上方建立當日結果。詳見 [留言擷取與回覆接線驗證](community-execution-integration-local-verification.md)。

`COM-02` 再新增固定 Google Sheets v4 REST adapter 與交易協調器，接好整頁空白檢查、一次性 RAW PUT、userEnteredValue 型別讀回、F 欄人工核准重讀及每則平台回覆前重讀。Google OAuth 沒有在本技能重做，gws 也未被選作敏感留言預設 transport。這仍只有 FakeHTTP／虛構儲存格測試；真實 Sheets、隔離分類器、私訊與平台仍是後續或集中驗收項目。詳見 [Sheets 接線驗證](community-sheets-integration-local-verification.md)。

`COM-03` 依最小 MVP 選定本機人工安全審查，新增 127.0.0.1、無 JavaScript／外部資源的批次頁面與 0600 人類決策收據；主 Agent 不讀頁面，queue 拒絕未經證明的 isolated_ai。這只通過虛構回環測試，尚未由真實使用者操作；未來 AI 分類器須另行完成 host-enforced sandbox、負向權限測試與資料／費用授權。詳見 [人工審查驗證](community-review-isolation-local-verification.md)。

`COM-04` 已用同一虛構工作區串接 fetch、固定隔離、人工 allow、六欄 RAW、F 欄改稿、對話確認、逐則回覆與獨立讀回，並覆蓋重複、錯置、競態、已有回覆、Sheets／平台中斷及 unknown。測試發現並修正 unknown observation 無法綁回原 API claim 的狀態機缺口；仍不允許重送。詳見 [完整虛構串接驗證](community-end-to-end-local-verification.md)。

`COM-05` 已依使用者確認建立 Facebook／Instagram 按需私訊 MVP：只處理對方先發起、最新仍是對方訊息、24 小時內且最近脈絡全為純文字的對話，第一版不建 Webhook。私訊使用獨立 queue、本機人工預覽與第二次確認，不進 Google Sheets；三種 setup 登入路徑由受限官方 adapter 取得記憶體 Token，傳送前重讀資格，單次 claim／checkpoint 後獨立讀回，pending／unknown 不重送。33 項私訊與人工針對性測試全數通過，整包 347 項測試通過 346 項、依政策略過 1 項原生探測；真實 Meta App、OAuth、App Review、對話及傳送仍留集中實機驗收。詳見 [Meta 私訊本機驗證](community-direct-messaging-local-verification.md)。
