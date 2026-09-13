# 官網打造 0.7.0 Preview

本包隨「Raven AI 一人公司工具包」的 v0.1.0-preview.1 發行，遠端狀態以 母專案的 GitHub prerelease 為準。這是可交給 AI Agent 安裝的七技能候選包，包含 Astro 範本與離線六主題畫廊。安裝不執行 Node、不登入外部服務、不建立網站或監控排程。

## 本次內容

- 七技能：設定、文案、設計預覽、建置、部署、服務串接與維運。
- 舊版更新的逐檔預覽、狀態／來源雜湊綁定、失敗回復與可回復移除。
- 表單 HTTPS POST，以及電子報、預約、付款 hosted links；不含 webhook、付款後端或資料庫。
- 公開 GET／TLS、本機備份與隔離還原；依賴更新和事件處理由 Agent 依授權流程操作，不自動部署。

## 安裝與回報

1. 若下載獨立 ZIP，核對其 SHA-256 與同次發布的 SHA256SUMS.txt；若下載整套工具包，保留其中完整的 skill-packs/website-building 目錄。
2. 把 [INSTALL.md](../INSTALL.md) 交給 Agent，先做唯讀 status／discover-state 與相符的 install 或更新預覽，不直接覆蓋既有技能。
3. 確認本機寫入後安裝；Agent 再檢查雜湊與實際用戶端技能發現。只有發現結果通過，才開始網站任務。
4. 問題回報請附版本、OS、Agent 版本、出錯步驟與去識別化錯誤，不附 Token、Cookie、帳號、私人檔案或網站資料。

本機安裝管理器需要 Python 3.11 以上；建站另外需要 Node 22.20.0 以上的受支援偶數版（24 分支使用 24.12.0 以上）與 npm 9.6.5 以上。已驗證環境與未完成項目見 [驗收報告](release-acceptance.md) 和 [相容性](client-compatibility.md)。Preview 不代表正式支援。

## 維護者重現

在包根執行：

```text
python -B tests/validate_package.py
python -B -m unittest discover -s tests -p test_*.py
```

真實建置驗收先在目前 shell 設定 WEBSITE_NODE_ACCEPTANCE=1，再重跑測試；這會從 npm registry 安裝固定依賴至測試隔離專案，並測六主題與服務入口。不要在公開來源內留下 node_modules。

建立發行副本：`python -B scripts/prepare_release.py --output-dir <包外尚不存在的目錄> --confirm-write`。輸出獨立目錄、ZIP、files.json 與 SHA256SUMS.txt；這只準備本機資產，不會執行 git、push 或 Release。正式發行時對同一份凍結資產再次驗收，核准後才上傳，公開後重新下載比對。
