# Windows x64 安裝契約

此路線使用固定 Raven Video-Use v0.1.1 Release，加上 manifest 鎖定的 `windows-macos-v1` 文字補丁。補丁核對每個輸入／輸出 SHA-256，不依賴本機開發 clone 或未發布 branch。macOS 的 Homebrew 與原始 lock 保留；不把 Windows 的套件解析結果套到 macOS。

## 前置條件與影響

- Windows x64、可執行的 Python 3.11+（僅用來啟動安裝器）、網路及使用者可寫入的目錄。實際工作環境固定 Python 3.12.14。
- 從 manifest 固定網址下載 uv 0.12.7、Astral CPython 3.12.14 build 20260825、Gyan FFmpeg 9.0.1 essentials（含 libass）。三個壓縮檔合計約 150 MB，Python 套件／解壓／快取另需數 GB。
- OpenCC 1.4.2 使用官方 CPython 3.12 Windows wheel；ASR 與 CKIP 分開以 Windows 專用 lock、`--require-hashes --strict` 安裝。Windows ASR 使用 CPU，速度須在實際素材驗收。
- 不需要管理員、symlink、Homebrew、全域 PATH 改動或雲端登入。技能以完整目錄副本註冊，runtime 放在技能掃描目錄外。
- 不下載 Qwen 或 CKIP 模型。模型 revision、首次下載及正式字幕的人工验收要求維持原契約。

## 安裝

Agent 將下列參數代入核對過的路徑；PowerShell 用單行命令。`--workspace` 是使用者選定的工作區，`--state-root` 不得位於技能掃描目錄內。

```powershell
python skill-packs/ai-video/scripts/install_windows.py --workspace '<workspace>' --state-root '<state-root>'
```

預設註冊 `.agents/skills/video-use`，供 Codex／Antigravity 使用；Claude Code 加 `--client claude`。可使用 `--cache-root` 指定下載快取。所有現有下載均重新核對 SHA-256，既有工具檔案遭修改即停止。

安裝器驗證固定封包、補丁、套件載入、98 項引擎測試與公開合成影片之後，才註冊技能。技能含 `toolbox-runtime.json`，列出實際 Python、FFmpeg、ASR、CKIP 路徑；Agent 依此設定當次子程序的環境，不依賴固定使用者名稱。

## 重跑、更新、回復與移除

相同參數重跑會核對技能內容、runtime 設定、原始工具與補丁，再同步固定依賴及重新驗證；成功回報 `verified_existing`。不宣稱完全沒有磁碟寫入。技能或 component 被人工修改、未知同名目錄、或版本不同時停止，不覆寫。

更新先選擇新的隔離工作區及 state root 安裝、測試；保留原工作區供回復。不要搬動 Python venv。確認新版後才由 Agent 在核對既有入口內容後切換或移除指定技能副本。此版本沒有自動跨版本切換／移除指令；不得套用 macOS 的 unlink 流程刪除實體目錄。移除只針對 receipt 記載且雜湊仍吻合的技能目錄，工具、模型、component 與媒體預設保留。

若下載或 runtime 驗證中斷，保留快取並重跑；安裝器會核對準備好的 component。不要手動修改檔案來繞過版本檢查。

## 驗證範圍

Windows 11 x64 已驗證：固定套件載入、CPU tensor 運算、影片本機技能安裝、字幕 QA、FFmpeg 真實渲染、中文／空白路徑及可見的繁體字形。合成案例使用事先建立的逐字稿與 CKIP fixture，不代表模型辨識／斷詞已實測。

macOS 的路徑與平台閘門有回歸測試；這輪沒有 macOS 主機，原生安裝／渲染仍須在 macOS 14+ Apple Silicon 實測。Windows ARM64、Intel Mac、CUDA、首次模型下載與真實影片尚未列為正式支援。
