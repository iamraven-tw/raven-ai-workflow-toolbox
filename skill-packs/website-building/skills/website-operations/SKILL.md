---
name: website-operations
description: "維護已建置或已上線的一人公司官網。當使用者要做網站健康監控、建立或驗證備份、隔離復原、檢查與更新 Astro/npm 依賴、處理故障、安排例行檢查或日常內容維護時使用；不自動部署、刪除備份、回滾線上版本或變更外部帳號。"
---

# 官網維運

這是官網打造工作流的第七個技能。它讀取 `website/config.json`、`website/operations.json` 與既有網站專案，提供公開健康檢查、可驗證本機備份、隔離式復原、依賴更新與事件處理。不得重問已保存的商業資訊，也不得把 Cloudflare 登入狀態、API Token、表單內容、名單、預約或交易資料放進設定、狀態或備份。

## 啟動與分流

這是多階段技能。開始時先用 Mermaid 顯示本次範圍、外部請求、本機寫入、部署／回復授權與停止位置。

1. 讀取一般設定、網站專案與既有維運設定，執行 `manage_operations.py status`。區分未設定、健康檢查失敗、備份過期、依賴待評估與已完成，不把其中一層當成另一層通過。
2. 依需求分流：監控或故障讀 [monitoring-and-incidents.md](references/monitoring-and-incidents.md)；備份／復原讀 [backup-and-recovery.md](references/backup-and-recovery.md)；依賴、內容或整合更新讀 [updates-and-maintenance.md](references/updates-and-maintenance.md)。設定欄位見 [operations-config.schema.json](references/operations-config.schema.json)。
3. 尚未設定時，以 [default-operations.json](assets/default-operations.json) 為起點，從已部署網址產生完整候選。先執行 `configure-plan` 並一次批次確認；使用者說「全部用預設」仍必須在實際寫入前確認 plan SHA-256。
4. `configure`、`backup`、`restore` 或健康紀錄寫入前，都必須先在對話中取得相符的明確授權，再傳入 plan SHA-256 與 `--confirm-write`。命令旗標不是對話核准。

## 監控

- `check` 只做公開 GET、必要文字、狀態碼、延遲與 TLS 到期檢查，不送表單、不建立預約、不測試付款。
- 只有 `check --record --confirm-write` 會把結果寫到 `.local/website/operations/health-history.json`；排程需使用者明確要求並先確認頻率與通知規則。沒有排程能力時只提供可重跑命令，不自行建立作業系統排程。
- 失敗時先讀回一次並定位來源；結果不明就停止，不反覆部署或重送外部動作。修復與 Cloudflare rollback 皆另行預覽與授權。

## 備份與復原

- `backup-plan` 列出檔案、大小、遺漏項與 plan SHA-256；`backup` 在相同計畫仍有效且已授權時建立 ZIP，再用 `verify-backup` 驗證 manifest 與每檔雜湊。
- 預設備份網站來源與工作區 `website/`，排除建置產物、版本庫、登入狀態、環境檔與常見秘密檔名。它不會備份外部服務端資料。
- `restore-plan` 先驗證壓縮檔並鎖定新目標；`restore` 只解壓到新的隔離目錄，絕不覆寫目前專案。比較、建置與驗證通過後，才依對應技能另行規劃寫回與部署。
- 保留數量只提醒，不自動刪除舊備份。刪除或移至隔離區需要另外列出精確目標並取得授權。

## 更新與日常維運

- 依賴先用 `npm outdated --json` 盤點，查官方 release notes 後提出精確版本的完整預設批次。不得直接跑無參數 `npm update` 或 `npm audit fix --force`。
- 更新前必須有剛完成且通過 `verify-backup` 的備份；先在隔離複本更新與執行 `npm ci`、`npm run build`、`check_site.py`，再顯示差異並取得本機寫入授權。
- 內容更新交給 `website-content-writing`，版面／程式交給 `website-build`，表單與 hosted links 交給 `website-service-integration`。每條路徑都先完成本機驗證。
- 已上線網站的任何更新都要交給 `website-deploy`，另外取得部署授權，完成後從正式網址讀回。更新授權不等於部署授權，也不等於 Cloudflare rollback 授權。

## 狀態與證據

- 一般設定：`website/operations.json`，只含公開網址與維運政策。
- 本機狀態：`.local/website/operations/`，保存設定雜湊、健康歷史與備份，不保存秘密；整個目錄不得提交。
- 每次回報分開列：設定、公開健康讀回、TLS、備份建立、備份驗證、隔離復原、本機更新、本機建置、部署、公開更新讀回。只宣告實際取得證據的層級。

## 執行錯誤最小回填

真實執行若證明本技能規則或 `manage_operations.py` 有通用錯誤，保留網站與備份現況；不明寫入不得重送。只在可重現、修正限於本技能且不新增外部權限時做一次小修正與一次針對性重測，再跑技能與套件驗證。否則停止並回報，不修改已安裝快取或私人網站來掩蓋問題。

## 停止條件

- 缺少 `website/config.json`、網站專案、有效維運設定或公開 HTTPS 網址。
- plan 後來源檔、候選設定、備份壓縮檔或目標狀態改變，造成雜湊失效。
- 備份含 symlink、秘密檔名、路徑逸出、單檔或總量超限，或驗證雜湊不符。
- 更新缺少官方相容性依據、精確版本、可驗證備份，或隔離建置失敗。
- 需要部署、rollback、DNS、外部備份上傳、付費、登入、刪除或服務端寫入，但尚未取得該動作的獨立授權。
