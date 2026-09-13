# PREVIEW 發行說明

本次 `0.1.0-preview.2` 為整併版 Preview，公開發行狀態以 GitHub Release 為準。變更：Google 技能包升為 0.2.0、內建原 Learn-GAS 四技能；兩個舊專案的公開核心只在 Toolbox 維護。AI 知識庫沿用既有五技能與保護使用者資料的安裝流程。兩個舊儲存庫維持原狀，不新增公告或封存。詳見 [遷移紀錄](migrations/single-repository.md)。

Raven AI 一人公司工具包 目前的產品版本是 **`0.1.0-preview.2`**，發行通道為 **PREVIEW**。

PREVIEW 代表目前版本已整理成可安裝、可測試、可回報問題的產品快照，適合願意協助驗收的早期使用者；它不代表所有技能包已完成實機驗證、具備正式支援，或適合直接用於不可回復的正式營運工作。

## 版本規則

- 根目錄的 [`release.toml`](../release.toml) 是產品版本與發行通道的單一依據。
- Preview 更新依序使用 `0.1.0-preview.1`、`0.1.0-preview.2` 等 SemVer prerelease 版本。
- 各技能包仍以自己的 `install.manifest.toml` 記錄安裝能力、相依版本、驗證證據與未完成項目；產品進入 PREVIEW 不會自動提高個別技能包的成熟度。
- `1.0.0` 以前可能有破壞性變更。升級前必須先預覽差異並保留可回復路徑，不追蹤未鎖定的 `main` 或 `latest`。

## 使用邊界

- 先從根目錄 [`INSTALL.md`](../INSTALL.md) 選擇單一技能包，不提供一次安裝全部內容的入口。
- 登入、OAuth、下載、部署、發布、寄信、付費操作與遠端帳號變更仍依各技能包的人工確認關卡執行。
- 尚未完成的實機、外部帳號、另一臺電腦或人工觀看／聆聽驗收，必須維持「未驗證」標示。
- Preview 問題回報應包含技能包名稱、作業系統、Agent 用戶端、執行階段與去識別化錯誤；不得附上 Token、Cookie、真實帳號資料或私人素材。

## 公開 PREVIEW 前的門檻

產品版本與通道由 `release.toml` 記錄；遠端是否已發布，以 [GitHub prerelease](https://github.com/iamraven-tw/raven-ai-workflow-toolbox/releases/tag/v0.1.0-preview.2) 為準，不在原始碼內保存會隨發布動作過期的布林值。公開前應完成：

1. 凍結本次納入範圍，確認工作樹中的每項改動都屬於本次 Preview。
2. 執行根層與各受影響技能包的完整驗證，保存失敗、略過與未執行項目，不把它們改寫成通過。
3. 檢查公開內容、授權、相依來源、秘密值與私人資料；確認 README 的支援矩陣和 manifest 相符。
4. 建立 commit 與 annotated tag `v0.1.0-preview.2`，再由維護者明確授權 push、repository 公開與 GitHub prerelease。
5. 公開後從遠端重新下載該 tag，在乾淨環境至少重跑安裝入口與核心 smoke test，並讀回 Release 內容與資產。

## 升級為穩定版的最低門檻

1. 所有納入穩定版的技能包完成 manifest 所列必要驗收，未納入者清楚標成實驗或排除。
2. 支援的平台與 Agent 用戶端有可重現的乾淨安裝、更新、回復與移除結果。
3. 需要遠端操作的核心路徑完成真實讀回驗證，且重複執行不會造成非預期寫入。
4. 公開發行、第三方授權、隱私、安全回報、商標與支援範圍完成檢查。
5. 建立可追溯的 Git tag 與發行說明，並由維護者明確決定發布。
