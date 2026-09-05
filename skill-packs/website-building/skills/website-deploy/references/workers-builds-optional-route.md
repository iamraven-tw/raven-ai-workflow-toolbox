# Git 連動 Workers Builds（可選路線）

只在使用者主動要求「push 就自動部署」時採用。人類步驟比本機 Wrangler 多，因此不是預設。

## 人類步驟

1. 在 Cloudflare 後台 Workers & Pages 建立 Worker 並選「連接 Git」。
2. 授權 Cloudflare 存取 GitHub 或 GitLab 帳號，選 repository 與分支。
3. 設定建置指令 `npm run build`、部署指令 `npx wrangler deploy`。

## Agent 可代辦

- 把專案推到使用者指定的 repository（需要使用者已登入的 Git 遠端與明確授權）。
- 檢查 `wrangler.jsonc` 與 `package.json` 的指令符合後台設定。
- 部署後用 `deploy_site.py verify` 讀回。

## 注意

- 這條路線的部署由 Cloudflare 的建置機器執行，Agent 看不到即時輸出，失敗要到後台看紀錄，屬人類步驟。
- Deploy Hook 網址是私人識別碼，不得寫進設定檔、狀態檔或公開套件。
- 兩條路線不要混用：同一個 Worker 由 Git 連動管理時，本機 `wrangler deploy` 會覆蓋它。
