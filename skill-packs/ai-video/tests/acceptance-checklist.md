# AI 剪片工作流驗收清單

## A. 發行與依賴門檻

- [x] Toolbox 公開核心採 Apache License 2.0；第三方內容保留各自授權。
- [x] Raven Video-Use v0.1.1 已公開，保留上游 MIT License、上游關係與修改說明。
- [x] manifest 已鎖定 fork tag、Release commit、資產 URL、資產 SHA-256 與關鍵檔案雜湊。
- [x] uv、CPython、OpenCC、FFmpeg／libass、Qwen runtime、CKIP runtime 與模型 revision 已鎖定來源及完整性資訊。
- [x] 模型權重、Python runtime、Homebrew binary 與第三方原始碼不打包進 Toolbox。
- [x] 公開候選版沒有維護者素材、聲音、品牌預設、真實集數、帳號、私人路徑或內容型詞庫。

## B. 安裝與生命週期門檻

- [x] Agent 安裝入口會自動選擇 Raven fork，不要求使用者自行判斷官方版或 fork。
- [x] 下載、系統套件、技能入口及大型模型各有獨立預覽與同意點。
- [x] 正常安裝與重複安裝在獨立暫存環境通過。
- [x] 主要環境、ASR runtime 與 CKIP runtime 的缺件可由固定 lock 精確修復。
- [x] Python 版本不符、Homebrew 版本不符及實體技能目錄衝突時會停止且不覆寫。
- [x] v0.1.0 與 v0.1.1 的更新、回復及重新切換通過，舊版本保留。
- [x] 移除只解除已確認的技能 symlink；版本目錄、runtime、模型快取與影片工作區分開管理。

## C. 自動與本機驗證

- [x] Toolbox manifest、Markdown 連結、公開 fixture、隱私邊界與狀態一致性通過。
- [x] Video-Use v0.1.1 在全新暫時 uv 0.12.7／Python 3.12.14 環境通過 94 項自動測試。
- [x] uv 0.12.7、CPython 3.12.14、公開 fork 資產及 runtime locks 的 SHA-256 通過。
- [x] ASR 91 個套件與 CKIP 26 個套件通過首次同步、重複同步、缺件修復與相依性檢查。
- [x] Homebrew 即時 metadata 與 macOS 26 bottles 通過版本及 SHA-256 驗證；既有版本衝突正確停止。
- [x] 固定 Qwen 模型曾完成中性合成臺灣中文離線轉錄與詞級對齊。
- [x] 固定 CKIP 模型曾完成中性句子的詞彙與片語快取。
- [x] 正式中文字幕詞界、寬度、停留時間、重疊、渲染、解碼及 CJK 字形檢查通過。
- [x] 可重複產生的公開色塊／音調素材、中性逐字稿 fixture 與 smoke test 入口已包含在候選版。
- [x] Codex 與 Claude Code 可從專案層級入口實際發現同一份技能。
- [x] Antigravity 官方工作區路徑與技能結構已核對；因本機 CLI 未登入，實際發現明確保留到 D 節。

完成 A～C 代表 Agent 端 MVP 已完成，可以交給外部電腦驗收；不代表 D 節已通過。

## D. 最終外部電腦人工驗收

以下由使用者在所有工作流完成後一次執行：

- [ ] 從公開 GitHub 下載全新 Toolbox，不使用維護者本機檔案。
- [ ] 在 macOS 14 以上 Apple Silicon 乾淨環境安裝鎖定 Homebrew 套件、uv、Python 與 Video-Use。
- [ ] 重新啟動選用的 AI Agent，確認技能發現；若使用 Antigravity，完成登入後的實際發現。
- [ ] 明確同意後完成 Qwen 與 CKIP 的首次固定模型下載。
- [ ] 使用一支有權使用的測試影片完成素材盤點、轉錄、內容剪輯、正式字幕、渲染與技術 QA。
- [ ] 人工觀看及聆聽完整成品，確認內容、字幕、音畫、字形與可讀性。
- [ ] 關閉後重新開啟，確認能從保存狀態繼續，不重複轉錄或破壞檔案。
- [ ] 驗證失敗時能安全停止、切回舊版或只移除技能入口。

D 節通過後，才可把實際測試環境加入 manifest 的 `officially_supported`；若失敗，候選版仍保持可回復狀態，但不得宣稱正式支援。
