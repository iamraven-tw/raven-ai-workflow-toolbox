# Toolbox 與 Learn-GAS 能力盤點

- 盤點日期：2026-08-31
- 依據：公開候選版實際檔案、Learn-GAS 固定 commit、Git／授權／測試查驗及目前官方文件

## 盤點結果

### Toolbox 原有能力

| 項目 | 盤點前狀態 | 可重用內容 |
|---|---|---|
| 根安裝入口 | 已能把各技能包分開安裝 | 沿用獨立技能包與 manifest 模式 |
| 依賴政策 | 要求固定版本、來源、授權、完整性、更新與回復 | 直接套用於 Learn-GAS |
| 公開／私人邊界 | 要求獨立公開快照，不自動同步私人流程 | Google 技能包沿用相同版本快照政策 |
| AI 剪片技能包 | 已有候選版狀態、用戶端入口、生命週期與外部驗收範本 | 重用文件與驗收結構，不重用影片專屬程式 |
| Google 工具自動化 | 根 README 只有方向與案例，沒有可安裝技能包 | 需要建立跨技術分流與安裝契約 |

### Learn-GAS 實際能力

| 能力 | 實際內容 | MVP 決定 |
|---|---|---|
| 共同專案入口 | 建立／接管專案、環境、Git、專案內固定 `clasp`、OAuth、推送、觸發器與部署關卡 | 直接重用 `google-apps-script-project-development` |
| 初學者教學 | 第一階段五個彼此獨立案例；第二階段八課累積專案；安全具現化、進度與重跑工具 | 直接重用 `google-apps-script-teaching` |
| 除錯 | 以紀錄、重現、單一假設、最小修正與回歸測試處理錯誤 | 直接重用 `google-apps-script-debugging` |
| Google Docs 固定版面 | 固定尺寸、表格、字體、位置、分頁、遠端讀回與人工目視驗收 | 直接重用 `google-docs-layout` |
| 接管既有 Apps Script | 唯讀列出帳號可存取專案、選定目標、空白目錄第一次 clone、Git 基線、後續才考慮 pull | 不另寫 Toolbox 版本 |
| 安裝 | Codex、Claude Code、Antigravity 的四技能＋共用術語安裝規格 | Toolbox 補上固定版本與可驗證生命週期管理器 |
| 安全 | 禁止憑證、Token、私人 ID；本機、OAuth、推送、部署與人工驗收分開 | 保留並擴大到 Workspace API／Cloud Run |

### Learn-GAS 來源、授權與驗證

| 項目 | 查驗結果 |
|---|---|
| 公開網址 | <https://github.com/iamraven-tw/Learn-GAS>，PUBLIC，未封存 |
| 預設分支 | `main` |
| 固定 commit | `7d50a7bfcfbe41ea9d88c2aef8f11200871433a3` |
| 固定 Git tree | `ef6e45626d59ae18745eb5c7245de0b3f2e48cc9` |
| 授權 | MIT License；LICENSE SHA-256 `39106e322b00c852430a6e6fca5f93b1465b24a6abd8a6d723df99ae9d2eaa15` |
| Git 狀態 | 查驗時本機 `main` 乾淨，HEAD 與公開 `origin/main`／`ls-remote` 相同 |
| 技能驗證 | `scripts/validate_skills.py`：四個技能通過 |
| 單元測試 | 教學工具 43 項通過 |

## 重複內容

下列內容已存在，不在 Toolbox 再做一份：

- Apps Script 的一般需求分流、開發環境、Git 與 `clasp` 工作流程。
- 新專案與既有專案接管。
- Apps Script 教學案例、模板具現化與進度管理。
- Apps Script 除錯與 Google Docs 固定版面。
- 面向初學者的術語、遠端確認與 Google 可見結果驗收。

Learn-GAS 的專案開發技能雖然已有「Apps Script 內部」共同分流，但不判斷是否應改用 Workspace API、OAuth 或 Cloud Run。這是 Toolbox 路由技能的獨立缺口；兩者的邊界以「選定 Apps Script 後交給 Learn-GAS」為準。

## 已補缺口

- [x] Apps Script、Workspace API／OAuth、Cloud Run service、Cloud Run job／Scheduler 與專門審查的跨技術分流。
- [x] 具體 MVP 使用者故事、未包含範圍與停止條件。
- [x] Learn-GAS 固定 commit、tree、授權、更新與回復決策。
- [x] Agent 安裝入口、機器可讀 manifest、架構、相容性與驗收清單。
- [x] 正常、重複、版本衝突、更新、回復、可復原移除與人工修改停止。
- [x] Codex、Claude Code 與 Antigravity 目前官方路徑；Codex／Claude Code 實際本機發現。
- [x] 虛構路由案例、公開內容、隱私、授權、相對連結與外部連結驗證。
- [x] 本機程式、Google 登入、OAuth、遠端部署與人工驗收的五段狀態。

## 保留到外部驗收

- [ ] 從公開候選快照在另一臺電腦重新取得固定 Learn-GAS commit。
- [ ] 已登入 Google Antigravity 的實際技能發現。
- [ ] 以另一個 Google 帳號和完全虛構資料完成一條低風險 Apps Script 流程。
- [ ] 分別觀察 Google 登入、OAuth、推送、實際執行與人工驗收，不共用完成宣告。
- [ ] 驗證後決定是否把該實際環境加入正式支援矩陣。

在這些項目完成前，狀態維持「可安裝的外部驗收候選版」，不寫成正式支援。
