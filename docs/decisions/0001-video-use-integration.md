# ADR 0001：Video-Use 整合方式

- 狀態：已接受
- 日期：2026-08-30
- 適用範圍：`skill-packs/ai-video/`

## 背景

官方 [Browser Use／Video-Use](https://github.com/browser-use/video-use) 提供對話式影片剪輯基礎，但目前官方版本不包含 Raven 現有工作流需要的離線臺灣中文轉錄、繁體轉換、中文詞界保護與中文字幕語意斷句。這些補強已修改多個核心路徑，現階段無法當成單純的外掛安裝。

Raven AI 一人公司工具包 也預期整合其他第三方專案，因此不能把「將第三方原始碼全部複製進 Toolbox」當成預設發行方式。

## 決策

1. MVP 使用 Raven 維護的公開 Video-Use fork。
2. 不向 Video-Use 上游提交 Pull Request。
3. Toolbox 不直接收錄完整 Video-Use 原始碼；安裝 manifest 取得已發布並鎖定的 fork ref。
4. fork 必須保留上游 MIT License、上游網址、基準 commit、修改摘要及驗證結果。
5. fork repository、正式 ref 與 checksum 尚未建立前，AI 剪片套件保持 `installable = false`。
6. 未來目標是改成官方 Video-Use 加上獨立的 Raven 臺灣中文擴充套件；這是演進方向，不是 MVP 前置條件。
7. 維護者私人工作流不搬入 Toolbox；只有去識別化、參數化並通過公開驗證的通用改進，才能進入公開技能包。

## 結果

- 使用者最後只需從 Toolbox 的安裝入口取得正確版本，不必自行判斷官方版或 fork。
- Raven 需要承擔 fork 的版本、上游更新、安全修正與相容性維護。
- Toolbox manifest 必須明確顯示第三方來源與 fork 關係。
- MVP 不需要先完成擴充套件重構，也不改變現有 Video-Use 工作目錄。

## 執行狀態

2026-08-31 已發布 [Raven Video-Use v0.1.1](https://github.com/iamraven-tw/video-use/releases/tag/v0.1.1)，並鎖定 Release commit、標籤與自行建立的下載資產 SHA-256。Toolbox 候選版隨後完成隔離安裝、重複安裝、缺件修復、版本衝突、更新、回復、移除、公開合成案例，以及 Codex／Claude Code 的技能發現驗證。

因此 AI 剪片套件可標示為 `installable = true`，讓使用者在另一臺電腦執行最後驗收；這個欄位只代表「已有可執行且可回復的候選安裝路徑」，不代表正式支援。鎖定 Homebrew 套件的乾淨系統安裝、首次模型下載、Antigravity 實際技能發現與真實影片觀看／聆聽，保留在外部電腦驗收。全部通過後才可把 `officially_supported` 加入實際環境。

## 重新評估條件

2026-09-07 Windows 移植補充：在下一個 fork Release 發布前，Toolbox 仍下載已發布的 v0.1.1 資產，再套用 manifest 鎖定的最小文字補丁。補丁逐檔驗證輸入與輸出 SHA-256，透明保留上游授權與修改關係；不依賴本機 branch、不收錄完整 source。日後新 Release 納入移植時，須驗證後移除重複補丁。Windows 使用完整副本註冊，macOS 的版本鎖定與連結路線保留。

只有在下列條件成立時，才評估改為官方核心＋擴充套件：

- 中文補強能透過穩定公開介面掛載，不再修改多個上游核心檔案。
- 擴充套件能獨立安裝、更新、回復與測試。
- 與 fork 版本的字幕、轉錄、EDL 與渲染結果通過相同驗收案例。
- 既有使用者有明確且可回復的移轉路徑。
