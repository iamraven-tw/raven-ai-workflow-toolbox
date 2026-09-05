# Cloudflare 邊界

查證日期：2026-09-05。本文件記錄免費方案的使用範圍、需要授權的動作、費用停止點與套件不做的事。實作 `website-deploy` 前必須重新核對官方文件。

## 使用範圍

- 只使用 Cloudflare Workers 靜態資產（`wrangler.jsonc` 只宣告 `assets.directory`），免費方案。
- 不使用 SSR adapter、不綁定 KV、D1、R2、Queues 或任何可能計費的資源。
- 預設公開網址是 `<Worker 名稱>.<帳號子網域>.workers.dev`，自動 HTTPS。
- 自訂網域透過 wrangler 設定的 custom domain 路由完成；官方文件說明會自動建立 DNS 記錄與憑證。

## 需要明確授權的動作

| 動作 | 影響 | 由誰執行 |
|---|---|---|
| `wrangler login` | 在瀏覽器授權 Wrangler 存取帳號 | Agent 啟動，人在瀏覽器同意 |
| 首次 `wrangler deploy` | 建立公開的 `workers.dev` 連結 | 人授權，Agent 執行並讀回 |
| 宣告 custom domain 並部署 | 建立 DNS 記錄與憑證，網站對外公開 | 人授權，Agent 執行並讀回 |
| 移除 `noindex` | 允許搜尋引擎收錄 | 人授權，Agent 執行並讀回 |
| 購買網域 | 付費 | 人自己完成 |
| Add a site、改 nameserver | 變更帳號與註冊商設定 | 人自己完成，Agent 準備值並輪詢生效 |

## 費用停止點

- 任何會離開免費方案的操作（升級 Workers Paid、綁定付費資源、購買網域）都由人自己完成，Agent 只說明費用與影響。
- Agent 不得輸入付款資料，也不得替使用者接受付費條款。

## 套件不做的事

- 不保存任何 Cloudflare API Token、帳號識別碼或 zone 識別碼；只用 Wrangler 自己的 OAuth 登入狀態。
- 不用瀏覽器自動化替使用者操作 Cloudflare 後台。
- 不代辦「Add a site」。Wrangler OAuth 沒有建立 zone 的權限，改用 API Token 也要人進後台建立，人類步驟沒有減少。

## 實作時必須確認的外部事實

- Cloudflare Registrar 支援的頂級網域清單，特別是 `.tw` 與 `.com.tw`。官方頁面為動態載入，2026-09-05 未能機器確認。
- Wrangler OAuth 登入的權限範圍是否包含建立 zone；本套件假設不包含。
- 帳號 `workers.dev` 子網域首次啟用是否能由 `wrangler deploy` 互動完成。
- 免費方案的請求數與靜態資產限制，以及是否影響一人公司形象站的日常流量。
