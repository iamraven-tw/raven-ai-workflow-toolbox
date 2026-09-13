# 第三方專案與工具

## Learn-GAS

- 專案：<https://github.com/iamraven-tw/Learn-GAS>
- 用途：Google Apps Script 教學、專案開發／接管、除錯與 Google Docs 固定版面。
- 固定 commit：`7d50a7bfcfbe41ea9d88c2aef8f11200871433a3`
- 固定 Git tree：`ef6e45626d59ae18745eb5c7245de0b3f2e48cc9`
- LICENSE SHA-256：`39106e322b00c852430a6e6fca5f93b1465b24a6abd8a6d723df99ae9d2eaa15`
- 授權：MIT License，Copyright (c) 2026 iamraven-tw
- 整合方式：以上 commit 是一次性移入的歷史基線；原始碼已收進本包並只在 Toolbox 維護。完整 MIT 文字位於 `LICENSE.learn-gas`，四個技能目錄各自附帶 LICENSE。

安裝 Agent 必須驗證本包 `bundle.lock.json` 與 MIT 授權雜湊。歷史 commit、tree 僅供追溯，不再下載舊來源。Toolbox 自有的 `google-workflow-router` 適用根專案 Apache License 2.0；Learn-GAS 的檔案仍適用其 MIT License。

## Google clasp

- 專案：<https://github.com/google/clasp>
- 官方說明：<https://developers.google.com/apps-script/guides/clasp>
- 用途：由 Learn-GAS 在個別 Apps Script 專案內管理本機與遠端程式。
- 2026-08-31 查驗版本：`@google/clasp 3.4.1`，要求 Node.js 20 以上，Apache License 2.0。
- npm integrity：`sha512-92wlpu0loC9t4oADuTyJOxQm6T4H2dOD9oQ+BvdFJuzM2uP7cK5dGrrJQhb/m/HLbaR0UOsBXBqRlYbfyR9jbA==`

技能包本身不安裝 `clasp`。Learn-GAS 會在實際專案開始前即時核對官方版本與引擎需求，再把相容版本固定於該專案的 `package.json`／lockfile。這項即時查驗不授權安裝、OAuth 或遠端同步。

## Google 服務

Google Apps Script、Google Workspace APIs、OAuth、Google Cloud Run 與 Cloud Scheduler 是外部服務，不隨 Toolbox 散布。使用者仍受各服務當時的條款、配額、帳務與組織政策約束；manifest 記錄的官方文件查驗日期不保證未來行為不變。
# Windows 驗證相容性補充

Toolbox 的 `scripts/validate_upstream.py` 在通過本包來源雜湊驗證後，只於暫存副本調整 Learn-GAS symlink 測試的權限偵測。保留教學 runtime 與 MIT 授權；歷史 commit、tree 只供追溯；Windows 1314 以 skipped 記錄，不代表 symlink 防護已驗證。這項測試調整由 Toolbox 維護，其他上游驗證失敗仍會停止。
