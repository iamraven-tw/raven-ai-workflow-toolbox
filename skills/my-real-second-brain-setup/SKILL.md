---
name: my-real-second-brain-setup
description: "安裝、更新、修復或驗證 My Real Second Brain。當使用者提供 repository 連結並要求安裝，或要求設定本專案時，引導 AI Agent 依 install.manifest.toml 安裝全部必要自有技能、初始化使用者指定的工作區、安裝固定版本的可替換後端與專案範圍上游技能，讓使用者本人完成 Notebook 登入，並驗證結果。"
---

# My Real Second Brain 安裝

## 啟動條件

使用者要求安裝、設定、更新、修復或驗證 `My Real Second Brain` 及其預設後端時使用。

## 必讀文件

先定位含有 `install.manifest.toml` 的本 repository 根目錄，再完整讀取：

1. `AGENTS.md`
2. `INSTALL.md`
3. `install.manifest.toml`
4. `docs/installation.md`
5. `docs/providers.md`

若找不到 repository 根目錄，停止並請使用者重新提供本機 checkout 或 repository 連結；不得假設這些檔案位於目前工作目錄。

## 工作流程

這是多階段技能。採取任何安裝行動前，必須先向使用者展示 `INSTALL.md` 的 Mermaid 流程，標出外部下載、技能寫入、使用者登入與停止位置。流程圖不代表使用者已核准後續操作。

1. 唯讀檢查作業系統、Python、`uv`、既有 provider、專案技能與使用者指定的工作區。
2. 解析 `install.manifest.toml`，確認全部必要技能、工作區範本、來源路徑、安裝範圍、provider 版本與排序皆有效。
3. 說明下載內容、技能位置、工作區範本差異、覆蓋風險與非官方介面風險。
4. 取得使用者同意後，依 manifest 順序安裝全部自有技能；預設使用者範圍，不靜默覆蓋同名技能。
5. 將 `template/` 合併至使用者指定的工作區，只建立缺少項目；任何同名內容衝突都停止詢問。
6. 從正式套件來源安裝固定版本的 provider。
7. 在同一個使用者工作區使用上游支援的專案範圍方式註冊 provider 技能；不複製上游 repository。
8. 需要 Notebook 登入時停下，讓使用者本人完成。
9. 依 manifest 的驗證順序檢查自有技能、工作區骨架、provider 版本、provider 技能、登入與遠端存取。
10. 只有全部必要檢查成功後，才回報安裝完成。

## 永久邊界

- 不將 Graphify 或 Notebook 視為不可替換的系統核心。
- 不把上游原始碼或產生的技能提交到本專案。
- 不略過 manifest 中標示 `required = true` 的任何自有技能。
- 不自行猜測工作區，不覆蓋既有專案指令、筆記、索引或資料。
- 不讀取、輸出、保存或提交 Cookie、Token、登入狀態內容與私人來源。
- 不靜默安裝 `uv`、改用全域 `pip`、升級未鎖定版本或覆蓋不同內容的技能。
- 不在驗證失敗時自動刪除環境、圖譜、索引、來源或 Notebook。
- provider 替換只改 adapter 與設定，不得靜默改寫使用者核心知識。
