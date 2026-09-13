# 第三方專案總覽

本文件是根 repository 的第三方來源索引。各技能包必須在自己的 `THIRD_PARTY_NOTICES.md` 記錄實際依賴、版本、用途、整合方式與授權；本文件不取代上游授權，也不表示下列專案已經被收進本 repository。

## AI 知識庫

AI 知識庫目前整合 Graphify 與 `notebooklm-py`，並記錄其他概念來源。完整資訊見 [`skill-packs/ai-knowledge-base/THIRD_PARTY_NOTICES.md`](skill-packs/ai-knowledge-base/THIRD_PARTY_NOTICES.md)。

## AI 剪片工作流

AI 剪片以 [Browser Use 的 Video-Use](https://github.com/browser-use/video-use) 為工程基礎，現階段使用 [Raven 非官方 fork v0.1.1](https://github.com/iamraven-tw/video-use/releases/tag/v0.1.1)。Release commit 與下載資產 SHA-256 已鎖定；未來目標是官方 Video-Use 加上獨立的臺灣中文擴充套件。完整狀態見 [`skill-packs/ai-video/THIRD_PARTY_NOTICES.md`](skill-packs/ai-video/THIRD_PARTY_NOTICES.md)。

## Google 工具自動化

Google 工具自動化使用 [Learn-GAS](https://github.com/iamraven-tw/Learn-GAS) 的固定公開 commit，提供 Google Apps Script 教學、專案開發／接管、除錯與 Google Docs 固定版面。Learn-GAS 採 MIT License，原始碼不複製進 Toolbox；安裝時核對完整 commit、Git tree、LICENSE SHA-256 與上游測試。完整資訊見 [`skill-packs/google-automation/THIRD_PARTY_NOTICES.md`](skill-packs/google-automation/THIRD_PARTY_NOTICES.md)。

## 官網、社群與盤點

- 官網內含自行實作的 Astro 範本與離線預覽；預覽內嵌的 Motion／Tailwind 程式與樣式保留 MIT 授權。見 [官網第三方聲明](skill-packs/website-building/THIRD_PARTY_NOTICES.md)及隨資產散布的 [完整授權文字](skill-packs/website-building/skills/website-design-preview/assets/previews/THIRD_PARTY_LICENSES.txt)。
- 社群平台介面、工具與素材的使用邊界見 [社群第三方聲明](skill-packs/social-media/THIRD_PARTY_NOTICES.md)。本發行不含平台憑證或使用者媒體。
- 盤點工具由固定上游版本取得，不內嵌掃描程式；來源與 MIT 授權見 [盤點第三方聲明](skill-packs/agent-inventory/THIRD_PARTY_NOTICES.md)。

## 收錄原則

- 第三方程式預設由套件 manifest 從正式來源取得，不直接複製進本 repository。
- 任何實際散布的第三方程式、文件、字型、圖片、音訊、影片或模型，都必須先確認授權並保留必要聲明。
- 專案名稱與商標屬於各自權利人；本專案不因技術整合而代表或獲得其官方背書。
