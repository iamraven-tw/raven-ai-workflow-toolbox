# 備份與復原

## 備份內容

預設備份工作區的 `website/` 與網站專案的原始碼、公開素材、設定、`package.json`、`package-lock.json`。不備份 `node_modules`、`dist`、`.astro`、`.git`、`.local`、`.wrangler`、環境檔、私鑰或常見 credential／secret 檔名。Cloudflare OAuth、服務商資料、表單內容、訂閱名單、預約與交易資料不在本地網站備份範圍內。

`backup-plan` 先列出逐檔清單、檔案數、大小、遺漏項與來源雜湊；Agent 核對清單只含網站來源、不含名單或交易匯出，使用者確認後，`backup` 才能用相同 plan SHA-256 與 `--confirm-write` 建立 ZIP。排除是路徑／檔名規則，不是完整內容秘密掃描；`verify-backup` 只證明完整性，不證明每個檔案均可公開。壓縮檔內含 `backup-manifest.json`，每個 payload 檔案都有 SHA-256。建立後立即執行 `verify-backup`，不能只看 ZIP 存在。

備份可能含使用者的文案、照片與公開聯絡資訊，應留在私人儲存空間。預設位置是工作區的 `.local/website/operations/backups/`，不提交 repository。若使用者要雲端或異地副本，先說明供應商、目的地、費用、加密與資料範圍，再取得獨立上傳授權；本技能不把本機備份自動上傳。

保留數量只產生提醒，不自動刪除舊備份。清理前列出精確檔名與可回復位置，取得刪除／移動授權。

## 隔離復原

`restore-plan` 與 `restore` 永遠解壓到一個不存在的新目錄，產生 `workspace/` 與 `project/` 兩棵樹，不覆寫目前網站。工具會防止 zip-slip、重複路徑、symlink 類型與雜湊不符。復原成功後先比較差異、建置與檢查，再依正常技能流程把需要的檔案寫回；重新部署仍需獨立授權。
