# 相容性與驗證狀態

## 狀態定義

- **可安裝候選版：** Agent 端已有固定來源、安全停止點、生命週期與本機驗證，可以交給另一臺電腦做最後驗收。
- **正式支援：** 只有實際環境完成乾淨安裝、首次模型下載、完整影片流程及人工觀看／聆聽後才能加入。

目前屬第一種，`install.manifest.toml` 因此是 `installable = true`，但 `officially_supported = []`。

## 已完成的本機證據

- 全新的暫時 uv 0.12.7／Python 3.12.14 環境通過 Video-Use 94 項自動測試。
- 固定 revision 的 Qwen 模型曾以中性合成臺灣中文音訊完成離線轉錄與詞級對齊；正式字幕、影片合成、完整解碼及 CJK 字形畫面檢查通過。
- 公開 v0.1.1 Release 已重新下載，資產 SHA-256、封包根目錄、路徑安全及關鍵 lock 雜湊均相符。
- 官方 standalone uv 0.12.7 與 uv 管理的 CPython 3.12.14 build 已核對資產 SHA-256，並在隔離位置啟動。
- ASR 91 個套件與 CKIP 26 個套件通過強制雜湊安裝、重複同步及相依性檢查；故意移除套件後可由 lock 精確補回。
- 錯誤的 Python 3.14 runtime 會停止且保留原內容；實體技能目錄衝突不會被覆寫。
- v0.1.0 → v0.1.1 更新、切回 v0.1.0、再切回 v0.1.1 都只切換技能 symlink；舊版本與工作區保留。
- 移除測試只解除已確認的技能 symlink；版本目錄、ASR／CKIP runtime 及使用者衝突目錄均保留。
- macOS 26 Apple Silicon 的 OpenCC、FFmpeg-full、libass 即時 Homebrew metadata 與鎖定版本／bottle SHA-256 相符；本機既有舊版被正確判定為衝突，沒有升降版或移除。
- Codex CLI 與 Claude Code `/skills` 能從專案層級 symlink 發現同一份 `video-use` 技能。
- 公開 smoke test 會在暫存目錄產生色塊與音調影片，套用中性逐字稿、正式字幕與渲染，不使用私人素材。

## 支援矩陣

| 項目 | 候選版狀態 | 外部驗收仍要確認 |
|---|---|---|
| macOS 14 以上 Apple Silicon | 可安裝候選；本機隔離與核心路徑通過 | 另一臺乾淨電腦的完整安裝與人工成品驗收 |
| macOS 13 以下 | 不支援 | 不列入 v0.1 MVP |
| Windows／Linux | 未測試 | 不列入 v0.1 MVP |
| Codex | 專案路徑 `.agents/skills/video-use` 實際發現通過 | 外部電腦重啟後再確認 |
| Claude Code | 專案路徑 `.claude/skills/video-use` 實際發現通過 | 外部電腦重啟後再確認 |
| Google Antigravity | 官方工作區路徑 `.agents/skills/video-use` 與結構已核對 | 本機 CLI 未登入；由外部已登入環境實際發現 |
| uv／Python | 固定資產與隔離啟動通過 | 外部電腦首次下載 |
| Qwen3-ASR runtime／模型 | runtime lock 安裝、固定模型本機既有快取端到端通過 | 外部電腦首次下載約 6.54 GB，並以授權影片轉錄 |
| CKIP 正式中文字幕 | runtime lock 與固定模型既有快取句子測試通過 | 外部電腦首次下載約 814 MB 權重 |
| Homebrew 系統套件 | 即時 metadata、macOS 26 bottles 與衝突停止通過 | 乾淨系統實際安裝 OpenCC 1.4.2、FFmpeg-full 9.0.1_1、libass 0.17.5 |

## 不應擴大的結論

- Homebrew bottle 下載與 SHA-256 通過，不等於乾淨系統已安裝成功。
- 公開 smoke test 使用音調與預先建立的中性逐字稿，不等於 Qwen 已辨識真人語音。
- 技能被 Agent 發現，不等於所有 helper、模型與系統套件都已可用。
- 技術 QA 通過，不等於使用者已觀看、聆聽或同意發布成品。
