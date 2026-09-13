# 官網打造 0.7.0 套件決策

本文件保存獨立下載所需的現行決策，摘要自 Toolbox ADR 0003；歷史討論不屬於安裝依賴。版本 0.7.0 是七技能 Preview 候選，不代表正式公開支援。

- 商業事實只訪談一次，後續從 website/config.json 讀取；人類接觸點以 [human-touchpoints.md](human-touchpoints.md) 為準。外部操作先預覽、授權、執行，再讀回。
- 自有 Astro 靜態範本，固定版本與 lockfile；Node 22.20.0 以上的受支援偶數版（24 分支使用 24.12.0 以上）。六個主題與版面來源保留在各 theme.json；預設 whitebox，沒有代寫部落格文章的預設流程。
- 預設 Cloudflare Workers 靜態資產與 workers.dev。已有網域可沿用，DNS 不在 Cloudflare 時先由本人加入站點並切換 nameserver。OAuth、DNS、部署與公開收錄仍分開授權；不在包內保存 API Token。
- 聯絡表單為公開 HTTPS POST；電子報、預約與付款為 hosted HTTPS links。外部服務資源由 Agent 使用可用介面在授權後操作，不是 Python helper 的供應商 API 功能。未實測的送出／收件／預約不標示完成；付款不自動建立交易。
- 維運 helper 支援公開 GET／TLS、本機 ZIP 備份與雜湊驗證、新目錄隔離還原。依賴更新、事件處理、異地備份與線上 rollback 是 Agent 流程，沒有自動套用、上傳、刪除或排程。
- 安裝七個實體技能；範本附於 website-build/assets/template。安裝狀態與舊版快照放在掃描目錄之外，不使用 symlink 或私人同步。
- Preview 可附未驗收項目公開；正式支援仍需真實 Cloudflare、網域、服務與公開監控、指定平台／用戶端及第二臺電腦的證據。能力範圍見 [capability-matrix.md](capability-matrix.md)。
