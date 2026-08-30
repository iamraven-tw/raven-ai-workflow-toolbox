# 交給 AI Agent 的安裝入口

本文件是 `My Real Second Brain` 的人類可讀安裝入口；`install.manifest.toml` 是機器可讀入口。使用者不需要分別前往 Graphify 與 `notebooklm-py` 下載；AI Agent 應依 manifest 安裝五個自有技能與固定版本的預設後端，並保留未來替換後端的能力。

## 安裝流程

```mermaid
flowchart TD
    A["讀取 AGENTS.md、install.manifest.toml 與安裝文件"] --> B["唯讀檢查作業系統、Python、uv 與既有版本"]
    B --> C["向使用者說明下載項目、版本與影響範圍"]
    C --> D{"使用者同意安裝？"}
    D -- "否" --> E["停止，不變更環境"]
    D -- "是" --> F["安裝五個必要的自有技能"]
    F --> FA["確認第二大腦工作區位置"]
    FA --> FB["合併 template，只建立缺少項目"]
    FB --> G["安裝固定版本的預設後端"]
    G --> GA["安裝專案範圍的上游技能"]
    GA --> H["驗證 CLI 與技能"]
    H --> I{"需要 Notebook 登入？"}
    I -- "是" --> J["停下，由使用者本人完成登入"]
    I -- "否" --> K["執行存取驗證"]
    J --> K
    K --> L["寫入不含憑證的本機安裝狀態"]
```

## Agent 執行規則

1. 先讀取 `docs/installation.md`、`docs/client-compatibility.md` 與 `docs/providers.md`。
2. 技能清單、來源路徑、安裝範圍、provider 版本與順序，一律來自 `install.manifest.toml`。
3. 下載、安裝、覆蓋既有工具或開啟登入流程前，先取得使用者同意。
4. 預設使用套件管理器安裝正式發行版，不 clone 上游 repository。
5. 五個自有技能預設安裝於使用者範圍；上游技能預設安裝於專案範圍。
6. 先確認使用者指定的工作區，再把 `template/` 合併進去；只建立缺少項目，任何同名衝突都先停止詢問。
7. 上游技能視為可以重新產生的依賴，不混入本專案自行維護的 `skills/`。
8. Notebook 登入由使用者本人完成；不得讀取或保存其憑證。
9. 驗證失敗時停止並回報，不自動刪除既有環境或資料。

完整命令與驗證標準請見 `docs/installation.md`。
