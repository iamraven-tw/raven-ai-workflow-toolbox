# 本機 Wrangler 部署路線（預設）

## 為什麼是預設

Git 連動的 Workers Builds 要使用者進 Cloudflare 後台接 GitHub／GitLab、授權 App、選 repository，人工步驟多。本機 Wrangler 只需要人在瀏覽器點一次 `wrangler login` 的同意，其餘都由 Agent 執行。

## 版本

Wrangler 以 `4.129.0` 鎖在範本的 `devDependencies`，由 `npm ci` 安裝；`deploy_site.py` 用 `npx --no-install wrangler` 執行專案內的版本，不追蹤 latest。

## 登入

1. `deploy_site.py status --project <dir>` 執行 `wrangler whoami`。未登入時輸出 `login_required`。
2. Agent 執行 `npx wrangler login`。瀏覽器會打開 Cloudflare 授權頁；人只要按「允許」。沒有帳號的人先在同一頁註冊，這是唯一不能代辦的帳號步驟。
3. 重跑 `status`。輸出只包含遮罩後的信箱、帳號名稱、權限範圍與是否有 zone 編輯權；不輸出帳號 ID。
4. Wrangler 把 OAuth Token 存在使用者家目錄的 Wrangler 設定內，由它自己管理；本技能不讀、不複製、不記錄。

## 部署

1. `plan --stage workers_dev`：檢查 `wrangler.jsonc` 只宣告 `assets.directory`、`site.indexing` 為 `noindex`、`dist/` 存在且不比來源舊，計算上傳量。
2. 使用者授權後 `deploy --confirm-deploy --expect-indexing noindex`。命令在 `CI=1` 下執行，避免互動提示卡住。
3. 若帳號尚未有 `workers.dev` 子網域，wrangler 會停下來要求先設定。Agent 提出建議名稱（例如依站名的小寫 slug），使用者選定後到 Cloudflare 後台 Workers & Pages 頁「Your subdomain」設定一次，再重跑 `deploy`。這是一次性的人類決定。
4. 解析輸出中的 `https://<worker>.<子網域>.workers.dev`。沒有網址就標示 `deployed_url_unknown`，改用 `verify` 讀回判斷，不假設上線。

## 讀回

`verify --url <網址>` 檢查：首頁、關於、服務、文章列表、聯絡、範例文章回 200；不存在路徑回 404；`rss.xml`、`sitemap-index.xml`、`favicon.svg`、`og-image.png` 存在；首頁 robots 與預期一致；`og:image` 不再指向 `example.invalid`。

首次部署後 `site.url` 仍是 `example.invalid`，`verify` 會回報 `placeholder_site_url`。處理方式：`set-url --url <workers.dev 網址> --confirm-write`，重建、重部署、再 `verify`。

## Worker 名稱

`wrangler.jsonc` 的 `name` 會成為 `workers.dev` 網址的 DNS 標籤：只能小寫字母、數字與連字號，63 字元以內，不以連字號開頭或結尾。`scaffold_site.py` 已依站名產生合規的預設值。

## 免費方案邊界

只部署靜態資產，不使用 `main` 指令碼、KV、D1、R2；`deploy_site.py` 讀到這些欄位會停止。任何會離開免費方案的操作由人自己完成。
