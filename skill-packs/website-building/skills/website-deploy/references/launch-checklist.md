# 上線檢查與上線報告

## 正式公開前

- `verify --url <正式網址> --expect-indexing noindex` 全部通過。
- `site.url` 已是正式網址（`workers.dev` 或自訂網域），不再是 `example.invalid`。
- 佔位文案與示範照片是否已替換由使用者決定；未替換要在報告中明列，不擋公開。
- 使用者明確授權移除 `noindex`。

## 正式公開

1. `publish --confirm-write` 把 `site.indexing` 改為 `index`。
2. `npm run build`、`deploy --confirm-deploy --expect-indexing index`。
3. `verify --url <正式網址> --expect-indexing index`。
4. 設定檔 `verification.public_index = index_verified`。

## 上線報告內容

- 正式網址、`workers.dev` 網址、Worker 名稱、部署時間。
- 主題、頁面清單、啟用的可選頁面。
- 各層驗證狀態：本機建置、自動化檢查、Wrangler 登入、`workers.dev` 部署、自訂網域、公開收錄。
- 仍是佔位的內容：文案、照片、價格。
- 之後怎麼更新：改 Markdown 或設定、`npm run build`、`deploy`、`verify`。
- 剩下的可選人類步驟：後台 www 轉址規則、Cloudflare Web Analytics、搜尋引擎站長工具提交。
- 不含帳號識別碼、Token 或任何秘密。
