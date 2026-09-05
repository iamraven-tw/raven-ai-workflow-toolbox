# 社群媒體管理工作流

這是 AI Workflow Toolbox 的公開、平台無關社群媒體技能包。目前是**只完成第一個技能的本機候選版**，不是七個技能均已完成，也不是正式公開支援。

## 目前可用

- `social-media-setup`：以策略初始化或平台整合初始化兩種模式運作。選取平台後預設提出技能包已支援核心功能的完整管理權限，逐項說明並讓使用者在 OAuth 前刪減；選取 Meta 任一平台時，一併詢問是否設定 Facebook、Instagram 與 Threads。平台整合獲明確授權後，Agent 應完成可安全代辦的開發者 App、OAuth 設定與正式 API 讀回。使用者沒有另行指定時，API 憑證預設存入目前作業系統帳號的 macOS Keychain 或 Windows Credential Manager；一般設定與非敏感參照檔不含憑證值。

## 已確認、尚未建立

- `social-content-planning`
- `social-content-writing`
- `social-image-production`
- `social-content-publishing`
- `social-community-management`
- `social-performance-analysis`

這些名稱列在 manifest 的 `planned_skills`，但目前沒有可被 Agent 發現的技能目錄。每個技能完成流程審查後才會加入安裝清單。

## 本機實作與集中實機驗收

目前先做本機程式與虛構測試；所有工具包完成後才集中安排真實 Terminal、原生憑證庫、登入／OAuth、平台讀取、測試發布與另一臺電腦驗收。流程確認仍逐技能進行，不以實機驗收阻擋下一個技能。

本機憑證程式已補上中斷恢復、單程序鎖及可見 Terminal 隱藏輸入；Facebook Pages／YouTube 的 OAuth 接收、交換、原生保存、有效性檢查與重新授權關卡也已提供。YouTube 包含 refresh；Facebook 檢查 Page Token 失效，不套用 Google refresh。這兩條執行路徑已有虛構平台與本機 loopback 測試，仍待集中實機驗收。Instagram／Threads 尚無專用 OAuth 執行器，不因同屬 Meta 就視為已完成。完整界線見 [`docs/architecture.md`](docs/architecture.md) 與 [OAuth 執行契約](skills/social-media-setup/references/oauth-runtime.md)。

## 公開邊界

本套件只包含一般化流程、中性 schema、官方能力摘要與虛構測試。私人工作區只能作為設計證據；任何帳號、網址、品牌語氣、排程、平台識別碼、憑證位置與內容資料都不得搬入本套件。

套件內含 Apache-2.0 授權。現階段不綑綁或安裝第三方套件；本機憑證 helper 只使用 Python 標準函式庫與作業系統原生介面，詳見 `THIRD_PARTY_NOTICES.md`。

技能安裝與純策略設定不需要網路；平台整合模式若要刷新官方能力或實際連線則需要網路。登入、OAuth、建立 App、平台讀取與遠端寫入仍各自需要明確授權。共用 Meta 引導不代表三平台共用 App、OAuth、Token 或驗證結果。目前尚未完成 macOS／Windows 真實憑證寫入生命週期，也尚未完成真實 Meta 登入、App、OAuth 或平台讀取驗收。
