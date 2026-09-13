# 更新與例行維護

## 依賴更新

1. 唯讀執行 `npm outdated --json`，再查每個候選套件的官方 release notes、支援的 Node 版本、遷移說明與安全公告；不要只依 `latest` 或記憶決定。
2. 先列完整預設批次：目前版本、候選精確版本、patch／minor／major、理由、破壞性風險、預計修改檔與回復方式。major update 單獨一批。
3. 取得備份授權並建立、驗證備份。沒有可驗證備份時停止。
4. 在隔離複本用精確版本執行 `npm install --save-exact <package>@<version>`（dev dependency 保留 `--save-dev`），檢查 `package.json` 與 `package-lock.json` 差異；不得使用無參數 `npm update`、版本 tag、寬鬆範圍或 `npm audit fix --force`。
5. 在隔離複本執行 `npm ci`、`npm run build` 與 `check_site.py`；模板或頁面有變更時再做瀏覽器檢查。`npm ci` 依 lockfile 做 frozen install，若兩份套件檔不同步應直接失敗。
6. 顯示測試證據與檔案差異，取得本機更新寫入授權後才套用。套用後在實際專案重跑 `npm ci`、建置與頁面檢查。
7. 已上線網站另交 `website-deploy` 預覽並取得部署授權；部署後由正式網址讀回。失敗時用已驗證備份回復本機檔案；若需要 Cloudflare rollback，另行預覽與授權。

## 內容與整合維護

- 文案與 Markdown 文章交 `website-content-writing`，保留使用者自己改過的內容，不用依賴更新覆蓋。
- 版面與程式修改交 `website-build` 完成本機建置與頁面檢查。
- 表單、電子報、預約與付款入口交 `website-service-integration`；不把服務端資料混進網站備份。
- 網域續約、服務訂閱與付款方式由外部平台管理。Agent 可在讀到到期資訊後提醒，但不得猜測到期日、代購或輸入付款資料。

## 官方依據（查核日 2026-09-13）

- [npm outdated](https://docs.npmjs.com/cli/v11/commands/npm-outdated/) 支援 JSON 輸出，可列出過期依賴。
- [npm ci](https://docs.npmjs.com/cli/v11/commands/npm-ci/) 要求既有 lockfile，且 package.json 與 lockfile 不一致時會失敗，不會替專案改寫它們。
- [package-lock.json](https://docs.npmjs.com/cli/v11/configuring-npm/package-lock-json/) 描述可重現的依賴樹，應與專案一起保存。
- [Cloudflare Workers Rollbacks](https://developers.cloudflare.com/workers/versions-and-deployments/rollbacks/) 說明 rollback 會立即建立並啟用一個回到指定版本的新 deployment，因此必須視為獨立外部變更。
