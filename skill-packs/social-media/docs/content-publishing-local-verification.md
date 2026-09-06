# 第五技能本機候選驗證

日期：2026-09-05。候選版 0.5.0；第 4 技能流程已確認，第 5 技能等待使用者確認。本次未 commit、push、發布版本、安裝第三方工具或操作任何真實帳號。保留根目錄、AI 知識庫與其他技能包的既有修改。

## 本次新增

- social-content-publishing：平台無關主流程、五份平台執行文件、發布交易契約、UI metadata。
- publish_job.py：唯讀預覽、綁定內容／有序媒體／工作區、一次性 begin、工作區鎖、跨 job 去重、checkpoint、正規化 receipt 與持久 ledger。只用 Python 標準函式庫，沒有任何網路／憑證操作。
- 手動路徑以 awaiting_manual 保存交付狀態；只有使用者實際操作後的獨立讀回才可驗證。發布中斷／結果不明不重送，後續項目也不開始；已成功項不自動撤回。
- 一般設定 schema 5 的 brand_visual；schema 3／4 保留原版本交易，升級需要預覽及確認，保留原策略、整合與製圖偏好。Codex／Antigravity／網頁／HTML＋CSS 共用品牌簡報，本次覆寫不永久保存。
- 五技能安裝、舊一至四技能升級／回復、未知同名來源與人工修改保護。

## 已執行驗證

以 SOCIAL_NATIVE_ACCEPTANCE=0、PYTHONDONTWRITEBYTECODE=1 執行：

    python3 tests/validate_package.py
    python3 -m unittest discover -s tests -p 'test_*.py'

結果：靜態檢查通過；141 個測試中 140 通過，1 個真實原生憑證探測依集中驗收政策跳過。發布案例使用虛構媒體位元組／假平台回應，不表示圖片解碼或影片轉碼通過。品牌設定另使用當前既有 JSON Schema 驗證器與標準函式庫設定管理器交叉比較 10 組新舊版／合法／非法設定，全部一致；沒有安裝此驗證器，也沒有新增執行期依賴。

skill-creator 的 quick_validate 分別檢查 setup、圖片、發布技能；另查相對 Markdown 連結、fence 與 git diff 空白錯誤。這些只驗證檔案，不是 Agent 前測。發布欄位匹配只能驗證提供的證據完整，不能辨別 Agent 是否假造平台回應或人類同意。

## 官方來源與保留缺口

Google 的 insert、videos 資源、list 與 resumable 規則；Meta 官方 Postman 的 IG／Threads、Meta 官方 SDK 的 Page／PagePost／IGUser／IGMedia；Substack 官方文章發布與唯讀 MCP 說明，都已查閱，直接連結放在對應平台文件。Meta 部分開發者 HTML 頁本次限流／錯誤，以官方 collection／原始碼核對端點，不宣稱完成所有版本或媒體上限驗證。真實執行前仍需刷新所用版本與格式。

沒有內建五平台 HTTP driver，沒有把 OAuth 程式擴成發布器。五份 adapter 是給 Agent 的實際操作文件，API／官方連接器／可靠 CLI／受控瀏覽器都須由當前環境提供已授權可用工具；否則手動交付。Instagram／Threads 專用 OAuth driver 仍未完成，不能重用 Facebook runtime 冒充。Facebook 影片與 Threads 輪播 API 詳細參數、Stories／Notes／直播／現有貼文修改或刪除不在這份 MVP，按文件揭露缺口並選可用介面，不偷偷擴大任務。

## 後續狀態（2026-09-06）

本文件中所有 2026-09-05 的狀態敘述均保留為當時結果，包括後文所稱未補齊 IG 專用 OAuth。其後本技能流程已獲准繼續下一技能；這不表示平台發布接線或真實發布已通過。`social-media-setup` 亦已加入 Instagram Login、Instagram via Facebook Login 與 Threads 的專用 OAuth 路徑；2026-09-06 的 `INIT-03` 已將本技能兩份平台文件改為由可信 adapter 經 `Runtime.access()` 取用，並依登入路線選正確 host／Token。OAuth runtime 仍不是五平台發布 driver，也不取代本技能的發布預覽、確認、正式端點與獨立讀回。流程現況見 [流程確認文件](workflow-review-status.md)，OAuth 更新證據見 [下游 OAuth 交接驗證](downstream-oauth-handoff-local-verification.md)。

## 既有私人來源的一般化補充

本次只讀查閱真正的技能入口、發布程式與私人歷史紀錄，沒有執行來源腳本。可重用的選檔、媒體綁定、同一影片附加步驟、容器分階段、同一草稿與實際保存檢查，整理到發布技能與 references/existing-workflow-reuse.md。公開文件不含原始私人帳號、網址、路徑、內容、ID 或排程。

來源有多平台含 ID 的發布報告，以及影片／字幕、Reel 讀回、排程及草稿保存紀錄；各自保留原證據強度，不統一改稱已公開發布。本次一般化的是操作文件與沿用規則，沒有移植私人 HTTP／瀏覽器執行程式，沒有補齊 Threads 串文、Substack 影片／Podcast 或 IG 專用 OAuth。舊來源可減少相同路徑的重複實測，但不能替代新憑證介面、新環境與程式改動的驗證。

YouTube 字幕／清單的官方 insert、list 文件與 Substack 官方文章流程已重新查閱；瀏覽器保存細節標為來源行為證據，不冒稱官方穩定介面。執行前仍保留現行版本查證與發布確認。

本次針對性驗證：套件 validate_package.py 通過；test_content_publishing.py 的 15 個離線測試通過；publishing 的 quick_validate 通過；git diff --check 通過。未重跑全套 141 個測試，未安裝依賴，未進行平台讀取或任何遠端寫入。這些檢查覆蓋現有本機交易護欄與文件結構，不驗證新加的遠端操作說明能在當前帳號成功執行。

## 分層回報

以下表格是通用候選版的驗收狀態，並非私人來源的歷史結果。

| 層級 | 結果 |
| --- | --- |
| 靜態結構與文件 | 本機檢查與虛構測試通過 |
| 本機技能發現 | 五份隔離安裝入口及雜湊通過；只有 setup 有前次 Codex 探測證據，新四份尚無真實 Agent 發現／前測 |
| API 套件是否可安裝 | 沒有新增 API 套件或安裝測試；發布 helper 只用標準函式庫 |
| 使用者登入與 OAuth | 未執行，保留集中實機關卡 |
| 平台讀取 | 未執行；官方公開文件查證不是讀取使用者平台 |
| 測試發布／排程／寄信 | 未執行 |
| 另一臺電腦驗收 | 未執行 |
| 正式公開支援 | 尚未成立，不因本機通過而升級聲明 |

## PUB-01 後續狀態（2026-09-06）

本文件所有 2026-09-05「沒有內建 driver」敘述保留為當時結果。其後 PUB-01 已新增 `official_publish_api.py`：YouTube、Facebook、Instagram、Threads 有受限官方主機的低階 API adapter；Substack 明確選定已核准 OpenCLI 的受控 Chrome，沒有自造官方寫入 API。執行來源、支援格式、Agent 呼叫責任與備援已寫入機器可讀表。

這仍不是完整發布器：API adapter 尚未自動讀取 publish_job ledger、寫 checkpoint 或形成 receipt，列入 PUB-02；Facebook 影片與 Threads 輪播等規格缺口列入 PUB-03。新增的 10 項 adapter 測試與整包 251 項回歸均通過，其中整包 1 項原生憑證探測依政策跳過；全部使用假 Runtime 與 FakeHTTP，沒有登入、Token、平台讀取或遠端寫入。當次結果見 [五平台執行來源驗證](publishing-execution-sources-local-verification.md)。

## PUB-02 後續狀態（2026-09-06）

上述「尚未自動讀取 ledger」保留為 PUB-01 當時狀態。其後 `publish_execute.py` 已串接四平台的 begin、Runtime 預檢、逐階段 claim／checkpoint、正式 GET、去敏感 evidence 與 receipt；Substack 加入受控 Chrome handoff、首次寫入 claim 與重載 observation。Facebook 影片、Threads 輪播及精確格式／上限仍列 PUB-03；真實平台執行仍未進行。當次結果見 [發布交易整合本機驗證](publishing-transaction-integration-local-verification.md)。
