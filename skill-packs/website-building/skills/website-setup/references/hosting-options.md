# 託管與網域路線

## 託管（固定）

- Cloudflare Workers 靜態資產，免費方案，不使用 SSR，不綁定會計費的資源。
- 預設由 Agent 在本機執行 `wrangler deploy`；人只在 `wrangler login` 時於瀏覽器同意一次。
- Git 連動 Workers Builds 要人進 Cloudflare 後台接 GitHub／GitLab，人工步驟較多，只在使用者主動要求時改選 `deploy_route = "workers_builds_git"`。

## 網域路線（依人類步驟由少到多）

| 使用者狀況 | `custom_domain` 欄位 | 人要做的事 | Agent 能做的事 |
|---|---|---|---|
| 沒有網域，先上線再說 | `wanted = "undecided"` 或 `"no"`，`current_state = "none"` | 首次啟用 `workers.dev` 子網域時取名一次 | 部署、讀回 |
| 沒有網域，想買 | `wanted = "yes"`，`current_state = "to_purchase"`，`acquisition_route = "cloudflare_registrar"` | 付款一次 | 買完自動在同帳號 DNS 託管，綁定、憑證、重新導向全自動 |
| 想買，但頂級網域不在 Cloudflare Registrar 清單 | 同上，`acquisition_route = "external_registrar"` | 付款、在 Cloudflare 後台 Add a site、到註冊商改 nameserver | 準備 nameserver 值、輪詢生效、之後全自動 |
| 已有網域，DNS 已在 Cloudflare | `wanted = "yes"`，`current_state = "existing_on_cloudflare"`，`acquisition_route = "existing"`，填 `domain` | 授權一次 | 全自動 |
| 已有網域，DNS 不在 Cloudflare | `wanted = "yes"`，`current_state = "existing_dns_elsewhere"`，`acquisition_route = "existing"`，填 `domain` | Add a site、改 nameserver | 準備值、輪詢生效、之後全自動 |

## 設定階段只記錄意願與路線

`website-setup` 只寫入意願、現況與路線，不執行任何 Cloudflare 動作。`verification.custom_domain` 在 `wanted != "yes"` 時必須是 `not_applicable`。實際購買、Add a site、改 nameserver、綁定與讀回都由 `website-deploy` 依其預覽與授權關卡處理。

## 實作時要確認的外部事實

Cloudflare Registrar 支援的頂級網域清單（特別是 `.tw` 與 `.com.tw`）尚未機器確認。`website-setup` 遇到使用者想買這類網域時，先記錄 `acquisition_route = "cloudflare_registrar"` 並標註待確認，由 `website-deploy` 在執行前核對官方清單，不支援時改走外部註冊商。
