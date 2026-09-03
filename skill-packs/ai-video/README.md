# AI 剪片工作流

> 以 AI Agent 操作的本機剪片流程，從素材盤點一路做到臺灣繁體中文字幕、渲染與 QA。

## 目前狀態

本套件已完成 Agent 端的 MVP，狀態是**可安裝的外部驗收候選版**。它會依固定網址與 SHA-256 下載 [Raven Video-Use v0.1.1](https://github.com/iamraven-tw/video-use/releases/tag/v0.1.1)，不把 fork 原始碼複製進 Toolbox，也不要求使用者自行判斷官方版與 fork。

候選版已完成：

- 固定 uv 0.12.7、CPython 3.12.14、OpenCC、FFmpeg／libass、Qwen runtime、CKIP runtime 與模型 revision。
- 從公開 Release 重新下載並驗證資產 SHA-256、封包安全與關鍵檔案雜湊。
- 在隔離位置完成正常安裝、重複安裝、缺件修復、版本衝突、更新、回復及只移除技能入口的測試。
- Video-Use 94 項自動測試、合成臺灣中文轉錄／對齊、正式字幕、渲染、解碼與 CJK 字形檢查。
- Codex 與 Claude Code 的實際技能發現；Antigravity 的官方工作區路徑與結構檢查。
- 可公開散布的中性合成 smoke test，不含維護者聲音、影片、品牌、集數或私人路徑。

尚未宣稱正式支援。使用者最後會在另一臺電腦驗收鎖定 Homebrew 套件的乾淨安裝、首次模型下載、Antigravity 登入後的技能發現，以及一支有權使用的實際影片。

## MVP 能做什麼

1. 盤點素材、音軌與來源，不改動原始檔。
2. 使用固定 Qwen 模型離線轉錄並保留詞級時間軸。
3. 由逐字稿規劃內容剪輯，產生可回復的 EDL。
4. 用 OpenCC 與 CKIP 建立臺灣繁體中文正式字幕，保護中文詞界與指定詞彙。
5. 合成字幕、必要圖卡或動畫，輸出影片。
6. 檢查音訊、畫面、字幕、時間軸與輸出規格。
7. 將「技術檢查通過」與「使用者已觀看／聆聽」分開回報。

MVP 不包含影片上傳、平台發布、社群排程、特定品牌視覺、私人內容路由或付費 API 自動啟用。

## 元件關係

- **Toolbox AI 剪片技能包**：安裝契約、Agent 用戶端入口、確認關卡、公開測試與驗收。
- **Raven Video-Use fork**：目前的真實剪輯技能、helper 與臺灣中文補強。
- **官方 Video-Use**：上游工程基礎。

未來目標仍是「官方 Video-Use＋Raven 臺灣中文擴充套件」，但 MVP 先維持 fork，避免為了重構延後可用版本。

## 使用方式

請讓具備本機操作能力的 AI Agent 從 [`INSTALL.md`](INSTALL.md) 開始。Agent 會先唯讀檢查並顯示所有下載與系統變更；未取得同意前，不會下載大型模型或改動共用套件。

正式中文字幕需要 CKIP。基本安裝可以先不下載 CKIP 模型，但第一次輸出正式中文字幕時必須完成固定 runtime 與兩個固定模型 revision；不同意安裝時只能交付預覽字幕。

## 文件

- [`INSTALL.md`](INSTALL.md)：AI Agent 安裝、更新、回復與移除契約。
- [`install.manifest.toml`](install.manifest.toml)：機器可讀的版本、來源、checksum、用戶端與狀態。
- [`docs/architecture.md`](docs/architecture.md)：元件與資料邊界。
- [`docs/compatibility.md`](docs/compatibility.md)：已驗證與待外部驗收環境。
- [`tests/acceptance-checklist.md`](tests/acceptance-checklist.md)：自動門檻與最後一次外部電腦人工驗收。
- [`tests/fixtures/synthetic-project/README.md`](tests/fixtures/synthetic-project/README.md)：無私人內容的公開 smoke test 素材規格。
- [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)：第三方來源與授權。

公開版採人工挑選的版本快照，不與維護者的私人剪片流程自動同步。
