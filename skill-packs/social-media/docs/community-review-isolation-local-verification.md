# 社群留言人工安全審查本機驗證

日期：2026-09-06。範圍為待辦 `COM-03`。依「最小 MVP」原則，正式審查模式選定為本機人工審查；選配 isolated AI 暫時停用，而不是用未經證明的子 Agent、提示詞或自填旗標冒充安全沙箱。本次只使用虛構留言及本機回環測試，沒有呼叫模型、外傳資料、登入平台、寫入 Sheets、回覆留言、安裝工具或修改私人 newsletter。

## 決策

- 固定規則仍是第一層，命中風險的內容直接留隔離區；未命中只成為 `screened`，不是 allow。
- `screened` 項目由 `manual_review.py serve` 建立一次批次人類審查頁。helper 綁定 127.0.0.1 臨時連接埠，不主動開瀏覽器、不連外，最多 100 則，30 分鐘逾時。
- 主 Agent 只取得本機 URL 與狀態，不能自行讀取頁面、DOM 或截圖。使用者在自己的瀏覽器依序選 allow／uncertain／quarantine；allow 填摘要與草稿。
- `community_queue.py` 只接受 reviewer=human。isolated_ai 會固定停止，避免不存在的隔離能力被誤報為已啟用。
- 人類 allow 只是進入 Google Sheets 六欄審核資格；不代表可以回覆。最終回覆仍需 Sheets 修改、對話確認、逐則重讀與平台讀回。

## 本機介面與資料邊界

頁面不使用 JavaScript、外部資源、連結或遠端字型。未信任文字全部 HTML escape；留言網址只顯示文字。HTTP 只接受實際本機連接埠的 loopback Host，表單必須由同源頁面送出；回應包含 no-store、CSP、禁止 frame、referrer、MIME sniffing、相機、麥克風與定位，一般 request log 停用。短期 URL capability 只在程序記憶體及初始 stdout 存在，session 檔只保存 SHA-256。

每次人類提交先建立 0600 的私人收據，包含 review ID、內部 key、精確來源雜湊、決策、時間，以及 allow 時的摘要／草稿；不重複保存來源正文。queue review 綁定收據相對路徑與雜湊。session、來源、capability、決策欄位、草稿固定規則、工作區或鎖有任何衝突就停止。stdout 與完成頁不顯示來源、摘要或草稿。

這是同一作業系統使用者下的作業隔離，不是多使用者機密運算環境；真實工作區檔案權限與人類頁面操作仍待集中實機驗收。

## 為何不在本版接 AI

目前可用的主 Agent／一般子 Agent都有工具或工作區能力，不能證明「無工具、無發布權限、無憑證、無私人檔案、無環境變數、無歷史與記憶」。另接模型 API 又會新增外部資料傳送、帳號、憑證、費用及供應商契約。因此本版不選較方便但證據不足的 AI 路線。

日後若要啟用，必須先選定由宿主強制的沙箱，並以負向測試證明上述能力不可用；每次只送一則 screened 資料，輸出固定 JSON；模型憑證只留可信 caller；外傳與費用另行取得使用者授權；再明確修改 manifest、審查來源表與 queue allowlist。這些條件沒有通過前，AI 不出現在可選模式中。

## 驗證範圍

- session 只存 capability 雜湊、內部 key 與來源雜湊，檔案為 0600。
- HTML 正確 escape 標籤、比較符號與 ampersand；沒有 script 或可點擊 href。
- HTTP server 只綁 127.0.0.1，核對 loopback Host，設定安全 headers、同源 POST 與固定 body 大小；不寫一般 log。
- allow 先保存人類收據再讓項目 ready；uncertain 進隔離；非 allow 不接受多餘草稿。
- 可疑草稿、錯誤 capability、來源改版與未證明 isolated_ai 都停止。
- serve stdout 只有本機 URL、狀態與相對路徑，不含虛構外部文字。

本待辦新增 9 項人工審核測試；連同既有留言、平台與 Sheets 路徑，76 項針對性測試全數通過。整包離線回歸共 316 項：315 通過、1 項原生探測依政策略過。套件 validator、七份技能 quick_validate 與 `git diff --check` 均通過。

## 分層狀態

| 層級 | 本待辦結果 |
| --- | --- |
| 靜態結構與文件 | validate_package、七技能 quick_validate 與 diff check 通過 |
| 本機技能發現 | 未執行真實 Agent；整包離線安裝生命週期測試已通過 |
| API 套件是否可安裝 | 沒有新增或安裝套件；helper 只使用 Python 標準函式庫 |
| 使用者登入與 OAuth | 不需要且未執行 |
| 平台讀取 | 未執行；測試只有虛構 state |
| 測試寫入／回覆 | 未執行；人工 allow 不授權 Sheets 或平台寫入 |
| 另一臺電腦驗收 | 未執行；Windows loopback、防火牆與 ACL 待集中驗收 |
| 正式公開支援 | 尚未成立；仍是本機候選實作 |
