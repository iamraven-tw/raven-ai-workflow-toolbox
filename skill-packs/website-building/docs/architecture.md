# 架構

## 分層

1. 套件層保存 manifest、安裝生命週期、人類接觸點清單、Cloudflare 邊界、公開資料邊界與驗收分層。
2. 每個技能的 `SKILL.md` 保存流程；Agent 執行的步驟與人類接觸點分開列出。
3. 使用者工作區保存一般設定 `website/config.json`；`.local/website/` 保存非敏感技術狀態。網站專案本身由 `website-build` 建立在使用者指定的目錄，不放在技能目錄內。
4. 秘密不進入套件：Cloudflare 登入狀態由 Wrangler 自己保存；若未來需要 API Token，依社群媒體套件的原生憑證庫設計存入作業系統憑證庫。
5. 風格檔採 DESIGN.md 規格，由 `website-design-preview` 按需下載並快取到工作區；套件不預先複製整個風格庫。
6. 部署、綁網域與公開由 `website-deploy` 處理；任何本機產物、指令輸出或按鈕都不等於平台成功，必須讀回。

## 目前切片

目前有 `website-setup`、`website-design-preview` 與 `website-build`。`website-design-preview` 用範本內建的六個完整主題（各依一份公開設計指引實作）產生本機畫廊，展示的是預先建置好的真實頁面並替換成使用者內容，Agent 主動截圖展示，選定後寫入 `website/design.json`。`website-setup` 讀取工作區既有設定（知識庫的一人公司設定檔、社群媒體設定）當預設值，一次完成商業訪談，產生頁面清單、風格推薦、託管方案與網域路線的預設方案，批次確認後寫入設定與狀態。`website-build` 從 `template/` 建立專案、填入設定、產生佔位素材、`npm ci` 與建置、用 `check_site.py` 檢查靜態輸出並截圖。兩者都不登入、不部署。

## 技能間的資料流

```text
website-setup ──► website/config.json ──► website-content-writing（文案）
                                      ├──► website-design-preview（畫廊展示）──► website/design.json
                                      ├──► website-build（Astro 專案、建置、自動檢查，自動讀 design.json 選主題）
                                      └──► website-deploy（登入、部署、網域、公開）
```

後續技能只讀取設定檔，不重複詢問商業資訊。它們各自更新設定檔中屬於自己的 `design`、`hosting` 與 `verification` 欄位，寫入前同樣先預覽再確認。

## 後續技能契約

| 技能 | 必須補齊 |
|---|---|
| `website-content-writing` | 文案草稿格式、事實與 AI 建議的標記方式、批次確認、寫回設定的欄位 |
| `website-deploy` | Wrangler 登入檢查、部署預覽、`workers.dev` 部署與讀回、四條網域路線、custom domain 宣告、`noindex` 移除、上線報告 |
| `website-service-integration`、`website-operations` | 第二版；先定義使用者故事與外部服務的授權關卡 |
