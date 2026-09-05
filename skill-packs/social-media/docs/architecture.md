# 架構

## 分層

1. 套件層保存 manifest、安裝生命週期、公開資料邊界與驗收分層。
2. 每個技能的 `SKILL.md` 保存平台無關流程。
3. 平台差異保存於該技能的 `references/platforms/`；執行多平台任務時，只讀被選取的平台文件。
4. 使用者工作區保存一般策略設定；`.local/social-media/` 保存非敏感技術狀態與憑證參照。使用者未另行指定時，秘密值預設保存在目前作業系統帳號的 macOS Keychain 或 Windows Credential Manager，不進入一般設定、參照檔與公開套件。
5. 平台整合初始化可透過執行環境既有的受控瀏覽器與正式 API，實際建立開發者 App、完成 OAuth 後讀回驗證；套件不綑綁瀏覽器工具，也不把 UI 內部請求冒充正式 API。
6. 發布、回覆與其他內容寫入仍由後續技能及平台 adapter 處理；任何本機產物、App 畫面或送出請求都不等於平台成功。

## 目前切片

目前只有 `social-media-setup`。它能建立策略與整合意圖、檢查官方能力，並在使用者另行授權且執行環境具有必要工具時，由 Agent 操作官方後台、建立 App、設定 OAuth、把憑證保存到原生憑證庫並執行平台唯讀驗證。平台被選取後預設提出已支援核心功能的完整管理權限；使用者可在 OAuth 前刪減。Facebook、Instagram 與 Threads 可共用一次 Meta 規劃和預覽，但 App／use case、permission、OAuth、Token 與驗證仍分開。Facebook 粉絲專頁完整管理授權是第一條定義完成的 Meta 路徑；原生憑證庫只有虛構 backend 測試，真實登入、OAuth、平台讀取及所有遠端寫入均尚未驗收，因此仍是待外部驗收候選版。

## 後續技能契約

### 第一技能實作與驗收邊界

| 項目 | 本機狀態 | 繼續條件 |
|---|---|---|
| 原生憑證寫入／讀回、未完成寫入恢復、刪除恢復、單程序鎖 | 已有程式與虛構 backend 測試 | 真實作業系統驗收集中留到最後 |
| 可見 Terminal 啟動、一次隱藏輸入與非敏感收據 | 已有程式與模擬啟動／取消／逾時／重複收據測試 | macOS／Windows 真實視窗及權限提示留到最後 |
| Facebook Pages HTTPS callback、state、Token 交換與保存 | 已有程式及虛構交換／權限／分頁／目標測試 | 既有受控 HTTPS callback、相容 Web server App 與真實 OAuth 留到最後；不自行部署 |
| Facebook Page Token 有效性與重新授權 | 每次取用檢查 App、scope、期限及 Page；失效停止、新 OAuth 要再確認 | 不宣稱無到期 Token 永久有效；不是 Google refresh，也不包含 Instagram／Threads |
| YouTube 後台程序、OAuth 與刷新 | 已有 Desktop loopback、PKCE、交換、refresh、保存與頻道讀回程式及虛構測試 | 真實後台、授權與 Google scope／驗證資格留到最後 |
| 跨平台中斷與不明結果 | 單次交換、先寫狀態、分段原生保存；不盲目重送 | 真實原生儲存中斷與另一臺電腦另行驗收 |
| Instagram／Threads 專用 OAuth、Messenger Webhook／內容行動 | 本輪未建立，不能因 Facebook Pages 成功而推定 | 專用 OAuth 需獨立補齊；Webhook 與內容行動由後續技能及另行授權的基礎設施處理 |

2026-09-05 已直接取得並閱讀 Meta 官方 manual flow、長期 Token、Login 安全與 Token 類型文件，補齊先前 429 所阻擋的查證。依官方 Web server code flow 實作 Facebook Pages；Google 依官方 Desktop OAuth 與官方 refresh 原始碼查證，未複製或安裝 SDK。直接來源、各 Token 差異與執行介面見 [OAuth 契約](../skills/social-media-setup/references/oauth-runtime.md)。

這次僅將有程式及虛構測試的 Facebook Pages／YouTube 路徑標記本機完成；其他平台執行器、後續技能與真實平台驗收仍分開列示，不用單一「Meta 完成」概括。

### 後續六技能

後續六個技能要各自補齊觸發、責任、輸入、輸出、寫入範圍、交接、停止條件、虛構測試與驗證。發布、互動與成效分析必須各自具備 YouTube、Instagram、Facebook、Threads、Substack 五份平台文件，不建立五個平台技能。
