# 七技能能力與驗證邊界

這裡區分「已提供實作」與「已在真實服務驗收」，不把 Agent 指令誤稱為供應商 API。

| 技能 | 腳本實作 | Agent 負責／尚待真實驗收 |
|---|---|---|
| website-setup | 設定 schema、預覽、核准雜湊、寫入與讀回 | 一次訪談、事實核對、方案取捨 |
| website-content-writing | 文案骨架、欄位指南、事實數量檢查、apply／sync | 文案品質與使用者確認；不代寫文章 |
| website-design-preview | 六主題離線畫廊、內容替換、選擇 | 瀏覽器截圖與視覺判斷 |
| website-build | scaffold、附帶範本、靜態頁面檢查 | npm ci／build、跨斷點瀏覽器驗收 |
| website-deploy | Wrangler 狀態、plan／deploy／verify、網域 routes、publish | 真實 OAuth、Cloudflare、DNS／HTTPS 尚待驗收 |
| website-service-integration | HTML POST／hosted links 設定、套用、HTML 讀回 | 建立服務資源、表單收件／訂閱／預約需各別授權及服務端證據；不做真實付款 |
| website-operations | GET／TLS、健康歷史、本機 backup／verify／isolated restore | 精確版本更新、事件處理與排程由 Agent 操作；正式 HTTPS、異地上傳與線上 rollback 尚未驗收 |

未支援：會員、資料庫、webhook、付款後端、任意第三方 script／iframe、自動依賴更新、自動刪備份。秘密檔名排除不保證內容無秘密；ZIP 驗證僅證明完整性。用戶端發現另見 [client-compatibility.md](client-compatibility.md)。
