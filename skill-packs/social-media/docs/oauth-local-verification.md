# OAuth 本機驗證紀錄

日期：2026-09-05。範圍僅 `social-media-setup` 的 Facebook Pages／YouTube 執行器、憑證交接及公開文件；不是五平台全部完成或實機驗收。

## 本輪結果

| 層級 | 結果 |
|---|---|
| 靜態結構與文件 | manifest、schema、技能契約、公開邊界、文字編碼防線與 Python 語法通過；skill-creator 的 quick validation 通過 |
| 本機技能發現 | 隔離安裝／更新／回復／移除及入口檔案測試通過；本輪未重新執行真實 Agent 探索，manifest 保留先前 Codex 掃描證據，不延伸其他客戶端 |
| API 套件可安裝 | 不適用；沒有新增或安裝第三方 API 套件，程式使用 Python 標準函式庫 |
| OAuth 虛構執行 | 全套 64 個測試，63 通過、1 個原生探測依政策略過；其中 29 個為 OAuth 測試 |
| 原生憑證庫與真實 Terminal | 未驗收；使用記憶體 backend、模擬視窗與虛構 Windows 大小契約 |
| 使用者登入／OAuth | 未執行，集中到所有工具包完成後 |
| 平台讀取 | 未執行；模擬 API 與本機 callback 不算真實平台讀取 |
| 測試發布 | 未執行；本技能也不發布、回覆或排程 |
| 另一臺電腦驗收 | 未執行 |
| 正式公開支援 | 尚未提供；沒有 commit、push 或發布版本 |

虛構測試涵蓋：state／PKCE、拒絕／逾時／重播、callback Host、固定 HTTPS 主機、禁止重新導向、一次交換、部分／多餘 scope、App／Page／頻道不符、Google refresh 保留與輪替、撤銷／過期、Meta Page Token 沒有排定到期時間、長 Token 分段、儲存中斷與不明結果停止、秘密不進狀態或命令列錯誤輸出。

本機 HTTP 測試只在 `127.0.0.1` 接收虛構 code；官方授權 Location 不跟隨。沒有真人同意、真實 Token、平台連線、TLS／反向代理驗收或原生秘密存取。Facebook 的 HTTPS 接入與 Instagram／Threads 專用執行器仍依各自契約處理，不能擴大本次通過範圍。

## 重現方式

在本技能包根目錄執行；不得加入 `SOCIAL_NATIVE_ACCEPTANCE=1`：

```sh
SOCIAL_NATIVE_ACCEPTANCE=0 PYTHONDONTWRITEBYTECODE=1 python3 tests/validate_package.py
SOCIAL_NATIVE_ACCEPTANCE=0 PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
```

不需要安裝第三方套件。技能探索、原生庫、OAuth 同意、平台讀取與發布的外部驗收不是上述命令的一部分。
