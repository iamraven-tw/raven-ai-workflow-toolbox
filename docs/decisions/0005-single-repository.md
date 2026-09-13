# ADR 0005：Toolbox 作為唯一維護來源

- 狀態：Accepted；本機實作與公開切換依遷移紀錄分開追蹤。
- 日期：2026-09-13
- 取代：[ADR 0002](0002-learn-gas-integration.md)。
- 依據：維護者決定往後只更新 raven-ai-workflow-toolbox。

Learn-GAS 與 My Real Second Brain 的公開核心併入 Toolbox。Google 技能包內建四個 Apps Script 技能；AI 知識庫保留已演進的五個技能與空白範本，不以舊版覆蓋現行改善。

技能、測試、文件、錯誤修正及版本只在本 repository 維護。兩個舊專案保留歷史，不建立雙向同步、自動回填或第二套發行流程。第三方 Graphify、notebooklm-py 及其他獨立依賴不受本次整併影響。

每包保留獨立安裝入口；Google 0.2.0 使用 schema 2 manifest 與本包雜湊，不依賴舊 repository 或 Git。既有 schema 1 安裝狀態仍可更新與從備份回復；直接安裝的未知同名技能先停止並保護內容。

MIT 與 Apache-2.0 的原聲明保留。歷史 commit、逐檔來源雜湊與比對記錄供追溯，不作未來下載設定。公開遷移只涉及工具，不移動使用者 Apps Script、課程紀錄或私人知識。

本機整併與回歸測試 → 公開候選發行 → 公開版本下載與乾淨安裝驗證。依維護者最新決定，兩個舊儲存庫保持原狀，不更新公告、不處理舊 Issue／Pull Request，也不封存。未完成的實機關卡維持待驗，不因整併宣稱正式支援。

完整盤點、驗證結果與公開切換待辦見 [遷移紀錄](../migrations/single-repository.md)。
