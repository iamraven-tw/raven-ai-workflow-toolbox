# 最小 Apps Script 專案範本

這是符合專案技能品質標準的最小分檔 `.gs` 範例。它不需要 TypeScript 編譯流程，不包含真實 Script ID，也不會自行建立檔案、寄信、部署或設定觸發條件。

使用前請依目前安裝的 `clasp` 版本建立或複製 Apps Script 專案，並確認 `.clasp.json` 不會被提交至 Git。

## 檔案與函式

| 檔案 | 主要函式 | 用途 |
|---|---|---|
| `00_Log.gs` | `writeProjectLog_` | 統一輸出繁體中文紀錄檔(Log) |
| `01_Config.gs` | `checkProjectSettings` | 檢查必要 Script Properties |
| `Main.gs` | `healthCheck` | 執行沒有副作用的健康檢查 |
| `Tests.gs` | `runProjectTests` | 執行正常、錯誤與重複執行測試 |

專案需要安裝型觸發器時才新增 `Triggers.gs`，並建立防止重複的設定與檢查函式；不需要時不為了形式增加檔案。

## Script Properties

本範例沒有必要的 Script Properties。`checkProjectSettings()` 會在「執行記錄」顯示：

```text
[設定] 本功能沒有必要的 Script Properties｜程式未硬寫私人 ID 或秘密
```

實際專案新增屬性時，先在本 README 記錄屬性名稱、用途、必填與敏感性；實際值仍由使用者親自在 Apps Script「專案設定」的「指令碼屬性」輸入。

## 預設測試

1. Agent 完成本機語法、格式及純邏輯檢查。
2. 取得使用者同意後由 Agent 執行 `clasp push`。
3. 使用者開啟 `Tests.gs`，在函式選單選擇 `runProjectTests`，再按下「執行」。
4. 使用者從編輯器下方「執行記錄」確認設定、正常、錯誤與重複執行測試全部通過。

此範例沒有 Google 服務副作用，因此不會建立可見的試算表、文件或郵件。實際專案仍須到對應 Google 服務檢查可見成果。
