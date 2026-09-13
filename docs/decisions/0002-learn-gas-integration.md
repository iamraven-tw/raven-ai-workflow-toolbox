# ADR 0002：Learn-GAS 作為固定版本外部依賴

- 狀態：Superseded by [ADR 0005](0005-single-repository.md)
- 以下保存 0.1.0 時期的歷史決策，0.2.0 起不再作為安裝指示。
- 日期：2026-08-31
- 範圍：Google 工具自動化 MVP

## 背景

Learn-GAS 已是獨立公開 repository，實際包含四個可用技能、共用術語、安裝規格、驗證程式、教學模板與 MIT License。Toolbox 需要補足的是 Apps Script、Workspace API／OAuth 與 Cloud Run 之間的需求分流，不是重新維護第二份 Apps Script 教材。

若複製 Learn-GAS，兩份技能會在修正、授權、文件與測試上漂移；若只依賴 `main`，安裝結果又無法重現。因此 MVP 採用固定 commit 的外部依賴。

## 決策

1. Learn-GAS 保持獨立 repository 與單一來源。
2. Toolbox 不 vendoring、不使用 Git submodule，也不自動同步維護者工作目錄。
3. `skill-packs/google-automation/install.manifest.toml` 固定完整 commit、Git tree 與 LICENSE SHA-256。
4. Toolbox 自有 `google-workflow-router` 只負責跨路線需求判斷、確認關卡與完成狀態；Apps Script 工作交給 Learn-GAS 四個技能。
5. Agent 先把固定 commit 取得到新的本機目錄，驗證來源與上游測試，再由 Toolbox 安裝管理器註冊技能。
6. 更新 Learn-GAS 時，建立 manifest 變更、驗證新 commit、執行 Learn-GAS 與 Toolbox 全部測試，再建立新的公開候選快照；不自動追蹤 `main`。
7. 回復時使用安裝狀態保存的前一版入口；不改動使用者的 Apps Script 專案、OAuth 或 Google Cloud 資源。

## 固定版本

- Repository：<https://github.com/iamraven-tw/Learn-GAS>
- Commit：`7d50a7bfcfbe41ea9d88c2aef8f11200871433a3`
- Git tree：`ef6e45626d59ae18745eb5c7245de0b3f2e48cc9`
- LICENSE SHA-256：`39106e322b00c852430a6e6fca5f93b1465b24a6abd8a6d723df99ae9d2eaa15`
- License：MIT

## 為何不選其他方案

- **整份複製：** 會產生兩個維護來源與授權／修正漂移。
- **Git submodule：** 增加使用者下載與打包複雜度，仍不能替代版本驗證與 Agent 安裝入口。
- **只提供網址：** 無法保證版本、相容性、回復與三種 Agent 安裝狀態。
- **重新開發 Apps Script 技能：** 沒有獨立缺口，違反 MVP 優先重用既有能力的原則。

## 授權與散布

Toolbox 自有路由、安裝器與文件採 Apache License 2.0。Learn-GAS 不包含在 Toolbox Git tree 或發行資產內；使用者從其公開 repository 取得，仍適用 MIT License。若未來改為實體打包或重新散布，必須重新評估並隨包附上 MIT License 與著作權聲明。

## 失敗與替代方案

- 公開 repository、固定 commit、tree、LICENSE 或上游測試任一不符時停止安裝，保留現有已驗證版。
- GitHub 暫時不可用時，可以使用事先取得且能驗證相同 commit／tree 的乾淨本機 clone；不得改用未鎖定分支。
- 若 Learn-GAS 未來停止維護或授權改變，先保留最後可驗證 commit，再另立 ADR 評估 fork、vendoring 或替代技能；不在安裝時臨時換來源。
