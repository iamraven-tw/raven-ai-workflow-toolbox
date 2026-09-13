# 單一儲存庫整併紀錄

目標：Learn-GAS 與 My Real Second Brain 的後續更新只進入 raven-ai-workflow-toolbox。決策見 [ADR 0005](../decisions/0005-single-repository.md)。

## 來源盤點

- Learn-GAS：`7d50a7bfcfbe41ea9d88c2aef8f11200871433a3`，本機與公開 HEAD 相同、來源乾淨。158 個技能、教材、範例與驗證檔案已移入 Google 技能包。MIT 著作權為 `Copyright (c) 2026 iamraven-tw`；Git 作者記錄為 Kaiyuan Kang。
- My Real Second Brain：以公開 HEAD `6a725bcca90464c1606377479150650c2ec0c67e` 乾淨 clone 比對，29 個受追蹤檔案均在 Toolbox 有對應位置。採用 Toolbox 已演進的內容，不回填舊版同步流程。Apache-2.0 原授權保留；公開歷史作者為 Raven。
- 精確路徑、逐檔原始 SHA-256 及對應結果：[source-inventory.json](source-inventory.json)。雜湊記錄的是遷移基線，不隨後續功能修改更新。
- 私人 My Real Second Brain 工作區不作為公開遷移來源。

## 已實作

- [x] Toolbox 單一維護政策與取代舊決策。
- [x] Google 0.2.0 內建原四技能、共用術語、範例與測試。
- [x] schema 2 manifest、內建來源鎖定及原 MIT 授權隨技能安裝。
- [x] 舊 schema 1 安裝狀態可更新；直接安裝的同名技能停止並提示保留備份。
- [x] AI 知識庫的公開來源對照與單一維護說明。
- [x] 根文件、技能包安裝規格、來源政策與舊版遷移指引。

## 驗證

以下為本機候選版的實際驗證結果，不代表遠端發布或新版本實機驗收。

| 驗證範圍 | 結果 |
|---|---|
| Google 安裝生命週期、舊版更新與回復、來源及授權異常拒絕 | 19 項通過 |
| 原 Learn-GAS 教材工具 | 43 項通過 |
| AI 知識庫 | 24 項通過 |
| 根層共用契約 | 11 項通過 |
| 社群媒體 | 469 項，466 項通過、3 項略過 |
| 官網打造 | 82 項，79 項通過、3 項略過 |
| AI Agent 規則與技能盤點 | 13 項通過 |
| 六個技能包靜態驗證 | 全部通過 |
| 發行檔案與敏感內容模式檢查 | 通過，無發現項目；未執行完整安全或法律稽核 |
| Git 差異空白檢查 | 通過 |

共執行 661 項測試：655 項通過，6 項依條件略過。略過範圍涉及原生憑證／Windows 權限及需另外啟用的 Node 真實建置驗收，不能視為完成。

- Google 技能包複製到獨立暫存目錄後，套件驗證、教材驗證及 43 項教材測試仍通過，不依賴 Toolbox 根目錄文件。
- 新安裝測試將外部命令搜尋路徑設為空白，證實不需要 Git 或舊 Learn-GAS clone；仍保留其他技能。舊 schema 1 更新後可在舊來源不存在時完整回復。
- 既有官網與盤點測試在 macOS 的暫存路徑含 symlink 時被其安全檢查拒絕；改用實際目錄 `TMPDIR=/private/tmp` 後通過，未放寬安全檢查。
- 未操作 Google 遠端資源、真實帳號、使用者既有技能安裝或私人知識庫。沒有沿用舊版本的用戶端技能發現驗收結果。

主要重跑入口：各技能包 `tests/validate_*.py`、各測試目錄的 `python3 -m unittest discover -s <測試目錄> -p 'test_*.py'`、Google `scripts/validate_upstream.py`、根層 `scripts/validate_release.py` 與 `git diff --check`。

舊專案的搬遷公告提案保存於 [legacy-notices.md](legacy-notices.md)，依維護者最新決定取消執行，未寫入舊儲存庫。

## 公開切換待辦

- [ ] 發行包含整併內容的 Toolbox Preview；發布前再核對遠端 HEAD 與待發布差異。
- [ ] 從公開發行版本在乾淨環境安裝、驗證 Google 與 AI 知識庫，並核對舊版遷移。
- [ ] 執行各用戶端實際技能發現及需要本人帳號的實機驗收。
- [x] 確認舊儲存庫處理方式：兩個專案保持原狀，不新增公告、不處理 Issue／Pull Request、不封存，也不刪除。

之後所有功能、文件、問題回報與版本均集中到 Toolbox；舊儲存庫不再主動維護。
