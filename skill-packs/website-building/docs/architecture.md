# 架構

## 分層

1. 套件層保存 manifest、安裝生命週期、人類接觸點清單、Cloudflare 邊界、公開資料邊界與驗收分層。
2. 每個技能的 `SKILL.md` 保存流程；Agent 執行的步驟與人類接觸點分開列出。
3. 使用者工作區保存一般設定 `website/config.json`；`.local/website/` 保存非敏感技術狀態。網站專案本身由 `website-build` 建立在使用者指定的目錄，不放在技能目錄內。
4. 秘密不進入套件：Cloudflare 登入狀態由 Wrangler 自己保存；本版不提供 API Token 或其他技能包憑證庫的整合。
5. 預設風格是內建六主題與離線畫廊。DESIGN.md 與其他外部風格只列為可選擴充，不在預設安裝時下載。
6. 部署、綁網域與公開由 `website-deploy` 處理；任何本機產物、指令輸出或按鈕都不等於平台成功，必須讀回。
7. `website-operations` 只對公開網址做 GET 健康檢查，並在 `.local/website/operations/` 保存健康歷史與帶 SHA-256 manifest 的本機備份；復原只進新目錄，更新與部署授權分開。

## 目前切片

目前七個技能都已建立：`website-setup`、`website-content-writing`、`website-design-preview`、`website-build`、`website-deploy`、`website-service-integration` 與 `website-operations`。`website-content-writing` 由 Agent 先完成已選頁面的文案，標明來源，再與設計一起批次確認；文案寫進 `website/copy.json`，每個欄位帶來源標記，工具擋下 AI 建議裡沒有依據的數字與定稿時的必填空白。部落格選配，無文章不阻擋建站；`website-build` 建站時自動渲染成 `site.copy.mjs`，已建好的站用 `sync`。`website-deploy` 用 `deploy_site.py` 做 Wrangler 登入檢查、部署預覽、`wrangler deploy`、HTTP 讀回、自訂網域與正式公開；每個外部動作都有預覽、授權旗標與讀回。`website-service-integration` 用 `manage_integrations.py` 管理 `website/integrations.json`，把公開 HTTPS 表單 endpoint 與電子報、預約、付款 hosted links 接到共用 Astro 元件，並分開驗證本機 HTML、公開網站與選擇性的端到端動作；不保存憑證、不植入第三方 script／iframe、不自動測試扣款。`website-operations` 用 `manage_operations.py` 管理公開健康檢查、帶逐檔雜湊的 ZIP 備份與隔離復原，依賴更新則要求精確版本、已驗證備份、隔離建置與獨立部署授權。`website-design-preview` 用範本內建的六個完整主題產生本機畫廊；`website-setup` 一次完成商業訪談；`website-build` 從 `template/` 建立並檢查網站。設定與建置技能都不登入、不部署。

## 技能間的資料流

```text
website-setup ──► website/config.json ──► website-content-writing（Agent 撰寫文案）──► website/copy.json（需要文章時寫入 website/posts/）
                                      ├──► website-design-preview（畫廊展示）──► website/design.json
                                      ├──► website-build（Astro 專案、建置、自動檢查，自動讀 design.json 選主題）
                                      └──► website-deploy（deploy_site.py：登入、部署、讀回、網域、公開）
website/config.json + 已建網站 ──► website-service-integration ──► website/integrations.json + Astro 共用元件 ──► website-deploy（另行授權重新部署）
website/config.json + 已建／已上線網站 ──► website-operations ──► website/operations.json + .local/website/operations/{health-history.json,backups/}
```

後續技能只讀取設定檔，不重複詢問商業資訊。它們各自更新設定檔中屬於自己的 `design`、`hosting` 與 `verification` 欄位，寫入前同樣先預覽再確認。

所有七個技能都已具備來源流程、工具與虛構驗證；真實帳號、公開網址、監控排程、異地備份、線上更新與第二臺電腦仍依驗收分層逐項標示，不因本機完成而自動通過。
