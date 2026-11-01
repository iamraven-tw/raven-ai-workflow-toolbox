# ADR 0006：C 級外部來源的版本政策

- 狀態：Accepted
- 日期：2026-10-06（2026-10-31 補充 AI 知識庫本地 RAG）
- 調整：[`docs/dependency-policy.md`](../dependency-policy.md) 的「固定版本」原則，對下列 C 級外部來源開放 `latest` 例外；其他依賴維持固定版本。

## 背景

本專案原則上由安裝 manifest 從正式來源取得固定版本，不追蹤 `latest`。實際維護後發現，有一類元件用固定版本反而比較麻煩，也沒有換到更多安全性：

- 它們是獨立的工具或資料，不是工具包的一部分，也不適合複製進本 repository（體積、平台相依或生態系特性）。
- 有些元件本身更新很快，或必須跟著外部平台改版（例如瀏覽器擴充功能、時區資料），停在舊版反而容易壞掉。
- 這些生態系（PyPI、npm、Homebrew、GitHub Release）本來就有自己的完整性檢查機制。

## 決策

### 1. C 級外部來源可以追蹤 `latest`

無法封存、也不屬於工具包本身的獨立工具與資料，標示為 C 級外部來源，`version_policy = "latest"`：安裝當下的最新正式版。manifest 或來源契約必須記錄：

- `tier = "C"` 與 `version_policy = "latest"`。
- 維護者最後測試過的版本（`tested_version` 或 `tested_release`），只供參考與核對，不是安裝目標。
- `external_source_notice = "standard"`：安裝前必須宣讀標準外部來源提醒。

目前適用範圍：

| 技能包 | 元件 | 紀錄方式 |
|---|---|---|
| 社群媒體 | OpenCLI（CLI 原始碼與同一 Release 的 Chrome 擴充功能） | `opencli-source.json` schema v2：記錄 Release 選擇規則、擴充功能權限基準，以及 `tested_release`（commit、tree、LICENSE、鎖檔與資產雜湊） |
| 社群媒體 | tzdata（Python 官方 IANA 時區資料） | `requirements.txt` 不釘版本，只接受 wheel；manifest 記錄 `tested_version` 與雜湊 |
| AI 知識庫 | graphifyy（Graphify） | manifest 記錄 `tested_version` 與當時觀察到的最新版 |
| AI 知識庫 | 本地 RAG 元件：Ollama、qwen3-embedding:4b、lancedb、pyarrow、jieba、pypdf、requests | manifest 標示 C 級 `latest` |
| 根目錄環境準備 | uv | 依官方安裝方式安裝當下最新版 |

### 2. 安裝後驗證，失敗時停止

最新版可能與技能不相容。安裝後執行技能包既有的驗證指令；失敗時回報並停止，不自動改裝舊版，也不擅自升級其他元件。之後的 `upgrade` 只在使用者要求時執行，執行前同樣先提醒。

### 3. 標準外部來源提醒

Agent 安裝任何 C 級元件前，以下列意思向使用者說明並取得同意，清單依實際元件填寫，用白話：

> 以下元件來自外部專案，不是 Raven AI 工具包的一部分：〔元件、容量〕。下載後我會先核對檔案是否與工具包記錄的版本一致，再安裝。要繼續嗎？

安裝、核對與驗證由 Agent 代為執行；同一次安裝中的多個外部元件合併成一次提醒；使用者追問時，再說明來源網址、版本與核對方式。這段提醒的目的是讓使用者知道哪些東西不是工具包的一部分，不是把安裝步驟推給使用者。

## 理由

- 這些元件不是工具包本身，盡到告知義務、安裝後驗證，比假裝釘住一個很快過期的版本更誠實。
- 下載最新版時不可能預先記錄雜湊，所以改成記錄「最後測試版本」供核對與排錯。
- 不在範圍內的依賴（fork、範本 lockfile 內的 npm 套件、Video-Use 引擎等）仍維持固定版本，行為可重現。

## 後果

- 不同時間安裝的使用者可能拿到不同版本；回報問題時需要附上實際安裝的版本。
- 維護者需要定期用最新版重跑驗證，並更新 `tested_version`／`tested_release`。
- 新增 C 級 `latest` 元件時，必須同步更新本 ADR、`docs/dependency-policy.md` 與根 `AGENTS.md`。
