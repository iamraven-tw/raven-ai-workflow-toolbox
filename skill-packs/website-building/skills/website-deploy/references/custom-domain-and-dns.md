# 自訂網域與 DNS

查證日期：2026-09-05，來源為 Cloudflare 官方文件（見 manifest `official_references`）。

## 已確認的官方行為

- Custom Domain 需要帳號內已啟用的 Cloudflare zone；主機名不得已有 CNAME 記錄。
- 在 `wrangler.jsonc` 加 `routes: [{ "pattern": "example.invalid", "custom_domain": true }]`，部署時 Cloudflare 自動建立 DNS 記錄並簽發 Advanced Certificate。
- Custom Domain 要求主機名完全一致：綁 `example.invalid` 不會接到 `www.example.invalid` 的請求。官方的轉址做法是在後台加轉址規則並放一筆代理的佔位 DNS 記錄，這是後台操作。
- 靜態資產支援 `public/_redirects`，規則可含主機名。

## 本技能的做法

`domain apply` 預設同時綁定根網域與 `www`（兩個 `custom_domain` route），兩邊都能正常開啟，不需要後台轉址規則。另外寫入 `public/_redirects`：

```text
https://www.example.invalid/* https://example.invalid/:splat 301
```

這條轉址是盡力而為：生效就有 www 到根網域的 301；不生效時 www 仍可瀏覽，只是兩個主機名都提供內容，canonical 指向根網域。要嚴格轉址時，後台的轉址規則列為可選的人類步驟。`--no-www` 可以只綁根網域。

## 四條路線與人類步驟

| 使用者狀況 | Agent 做的事 | 人類步驟 |
|---|---|---|
| 沒有網域，先用 `workers.dev` | 部署、讀回、`set-url` | 帳號子網域首次取名 |
| 向 Cloudflare Registrar 購買 | 買完網域已在同帳號 zone；`domain check` 確認 NS，`domain plan`、`apply`、部署、讀回 | 付款一次 |
| 向其他註冊商購買，或既有網域 DNS 不在 Cloudflare | 準備 Cloudflare 會給的 nameserver 值、定期 `domain check` 輪詢；NS 生效後同上 | 付款、Cloudflare 後台 Add a site 選免費方案、到註冊商改 nameserver |
| 既有網域已在 Cloudflare | `domain check`、`plan`、`apply`、部署、讀回 | 授權一次 |

## 一般後台設定的人機分工

`wrangler whoami` 的權限範圍通常只有 `zone (read)`，沒有建立 zone 的權限；`status` 會回報 `zone_edit`。改用 API Token 代辦也要人進後台建 Token，人類步驟沒有減少，而且套件政策是不保存 Token。一般後台設定先用已授權 API／CLI／OpenCLI；確認沒有其他方法、只剩 Computer Use 時，提供較快的人工指引或經使用者選擇由 Agent 操作，提醒速度可能較慢。登入、本人驗證、條款與付款仍由本人完成；不為少一次點擊新增秘密保存方式。

## Cloudflare Registrar 與 `.tw`

Registrar 支援的頂級網域清單頁面為動態載入，2026-09-05 未能機器確認 `.tw` 與 `.com.tw` 是否可購買。執行時 Agent 先請使用者在後台 Registrar 頁搜尋該網域；買不到就走外部註冊商路線，不因此阻擋 `workers.dev` 上線。

## 讀回

`domain check --domain <網域>` 用系統的 `nslookup` 讀 NS 是否以 `cloudflare.com` 結尾，並確認能解析；沒有 `nslookup` 時回 `null` 並改由 `verify` 直接連線判斷。綁定後 `verify --config <workspace>/website/config.json --url https://<網域>` 檢查 HTTPS 200、404、sitemap、robots、OG。DNS 傳播時間不在檢查範圍，未生效時等一段時間再重跑。
