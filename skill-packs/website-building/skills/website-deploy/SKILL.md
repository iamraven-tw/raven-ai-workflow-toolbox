---
name: website-deploy
description: "把 website-build 建好的一人公司官網部署到 Cloudflare Workers 靜態資產免費方案。當使用者要上線、要部署、要綁自訂網域、要正式公開（移除 noindex），或要檢查目前上線狀態時使用。Agent 執行 Wrangler 登入檢查、部署預覽、wrangler deploy、HTTP 讀回、自訂網域設定與公開；人類只做建立 Cloudflare 帳號、在瀏覽器點一次 wrangler login 同意、授權首次部署、買網域與必要的 Add a site／改 nameserver、授權正式公開。套件不保存任何 Token。"
---

# 官網部署

這是官網打造工作流的第五個技能，也是「從零到上線」的最後一步。每個外部動作都先預覽、取得明確授權、執行後從平台讀回；指令沒有報錯不等於上線。

## 責任

- 檢查 Wrangler 是否可用與登入狀態（`deploy_site.py status`）；未登入時由 Agent 啟動 `npx wrangler login`，人類只在瀏覽器點一次「允許」。
- 產生部署預覽（`plan`）：Worker 名稱、預期網址、上傳檔案數與容量、費用為零、剩餘人類步驟。一次讓使用者授權。
- 執行 `deploy --confirm-deploy`，解析輸出中的公開網址；失敗就停下來回報，不重試。
- 用 `verify --url` 讀回：必要頁面 200、不存在路徑 404、RSS、sitemap、robots、OG。通過才算部署完成。
- 首次部署後用 `set-url` 把 `site.url` 改成實際的 `workers.dev` 網址並重建重部署，讓 canonical 與 OG 指到可用的位置。
- 依 `references/custom-domain-and-dns.md` 的四條路線處理自訂網域：`domain check` 讀 NS 是否已在 Cloudflare、`domain plan` 預覽、授權後 `domain apply` 寫入 routes、重建、部署、`verify --url https://<網域>`。
- 使用者授權正式公開後，`publish --confirm-write` 把 `indexing` 改為 `index`，重建、部署、`verify --expect-indexing index`。
- 每個階段完成後，依 `website-setup` 的 `manage_workspace.py` 預覽與確認流程更新設定檔的 `verification` 欄位：`wrangler_login`、`workers_dev_deploy`、`custom_domain`、`public_index`。
- 產出上線報告並交接給第二版的維運技能。

本技能不建立 Cloudflare 帳號、不代按 OAuth 同意、不輸入付款資料、不用瀏覽器自動化操作 Cloudflare 後台、不保存任何 API Token 或帳號識別碼。

## 輸入

- 已由 `website-build` 建好且 `npm run build` 通過的專案目錄（含 `wrangler.jsonc`、`site.config.mjs`、`dist/`）。
- `website/config.json`：`hosting.worker_name`、`hosting.custom_domain` 的意願、現況與路線。
- 使用者是否已有 Cloudflare 帳號、網域現況。

不讀取瀏覽器 Cookie、環境變數中的 Token，不要求使用者貼上任何秘密。Wrangler 的登入狀態由它自己保存在使用者家目錄，本技能不碰。

## 啟動流程

這是多階段技能。開始執行前，用 Mermaid 向使用者呈現本次採用的分支、授權關卡與停止位置。

1. 確認前置：專案目錄存在、`dist/` 已建置且比來源新、`site.indexing` 仍是 `noindex`。不滿足就先回 `website-build`。
2. `status`。未登入時說明「我會執行 wrangler login，瀏覽器會打開 Cloudflare 授權頁，你只要按允許；沒有帳號的話先在同一頁註冊」，然後執行 `npx wrangler login`，等使用者完成後重跑 `status`。
3. `plan --stage workers_dev`。把預覽完整列給使用者：Worker 名稱、網址樣式、上傳量、費用為零、這一步會建立公開連結。取得明確授權。
4. `deploy --confirm-deploy --expect-indexing noindex`。若帳號尚未有 `workers.dev` 子網域，wrangler 會要求先取名；這是使用者的一次性決定，Agent 提出建議名稱讓使用者選，必要時請使用者到 Cloudflare 後台 Workers & Pages 頁設定一次再重跑。
5. `verify --url <workers.dev 網址>`。有 finding 就修正後重跑；通過後執行 `set-url --url <網址> --confirm-write`，重建、再 `deploy`、再 `verify`。
6. 更新設定檔 `verification.wrangler_login = verified`、`workers_dev_deploy = deployed_readback_verified`（透過 `manage_workspace.py` 預覽與確認）。
7. 依設定檔 `hosting.custom_domain.wanted` 決定是否進入網域階段；`no` 或 `undecided` 就跳到第 10 步。
8. 網域階段：`domain check --domain <網域>`。NS 不在 Cloudflare 時，列出人類步驟（買網域、Add a site、改 nameserver），等使用者完成後每隔一段時間重跑 `check`，不要求使用者回報技術細節。NS 已在 Cloudflare 後，`domain plan`，取得授權，`domain apply --confirm-write`，重建、`deploy`、`verify --url https://<網域>`。更新 `verification.custom_domain = verified` 與 `hosting.custom_domain.domain`。
9. 網域路線細節與每條路線的人類步驟見 `references/custom-domain-and-dns.md`。
10. 正式公開：說明「移除 noindex 後搜尋引擎會開始收錄」，取得授權，`publish --confirm-write`，重建、`deploy --expect-indexing index`、`verify --expect-indexing index`。更新 `verification.public_index = index_verified`。
11. 依 `references/launch-checklist.md` 產出上線報告並交接。

命令旗標不是對話核准。`--confirm-deploy` 與 `--confirm-write` 只能在使用者對同一份預覽明確同意後使用。

## 授權關卡

| 動作 | 影響 | 預覽必須包含 |
|---|---|---|
| `wrangler login` | 瀏覽器授權 Wrangler 存取帳號 | 會打開哪個網址、人要做什麼、不會保存 Token 到套件 |
| 首次 `deploy` | 建立公開連結 | Worker 名稱、網址樣式、上傳量、費用為零 |
| `domain apply` 與部署 | 建立 DNS 記錄與憑證、網站以正式網域公開 | 要綁的主機名、DNS 變更、www 處理方式 |
| `publish` 與部署 | 搜尋引擎可收錄 | 目前網址、robots 變更 |

購買網域、Add a site、改 nameserver、建立 Cloudflare 帳號、OAuth 同意由人類親自完成；Agent 準備好要填的值並在完成後讀回，不代辦也不催促。

## 寫入範圍

- 專案目錄內：`wrangler.jsonc` 的 `routes`、`site.config.mjs` 的 `url` 與 `indexing`、`public/_redirects`。
- `website/config.json` 的 `verification` 與 `hosting.custom_domain.domain`：只透過 `website-setup` 的預覽與確認流程。
- Cloudflare 上：只有使用者授權的 Worker 部署、自訂網域綁定與其自動產生的 DNS 記錄與憑證。

不得寫入任何 Token、帳號識別碼或 zone 識別碼到專案、設定檔、狀態檔或對話紀錄；`status` 只輸出遮罩後的信箱與帳號名稱。不刪除任何 Cloudflare 資源。

## 執行錯誤最小回填

實際執行出錯，或 Cloudflare 的可觀察行為與本技能規則衝突時，原任務優先：

1. 先保存目前進度與已知的遠端狀態；部署結果不明時不重送，改用 `verify` 讀回判斷。
2. 若 `references/troubleshooting.md` 已存在，只讀與目前症狀相關的段落；不存在時不要先建立空檔。
3. 只有能證明錯誤來自本技能、修正限於同一個由使用者管理的技能來源、不新增依賴或外部授權，且重跑原失敗步驟通過時，才立即回填：流程更新本 `SKILL.md`，特定環境或 Cloudflare 行為變化才建立或更新 `references/troubleshooting.md`。
4. 只做一次小修正、一次針對性重測，再執行本技能最快的既有格式／契約驗證，隨即回到原任務。
5. 一次修正仍失敗、需要 Cloudflare 後台操作、需要新的權限或付費、或需要跨技能改造時，停止回填並簡短回報缺口。

不得修改已安裝快取、內建技能、外掛或第三方來源。真實網域、帳號、Worker 名稱與一次性使用者選擇不得進入公開技能。回填不授權 commit、push 或任何原任務未授權的遠端變更。

## 輸出與交接

每次輸出至少包含：

- 目前階段與採用的網域路線。
- 每個外部動作的預覽、使用者授權、執行結果與讀回結果，分開列。
- 公開網址（`workers.dev` 與自訂網域）、Worker 名稱、部署時間；不含帳號識別碼。
- 各層狀態：Wrangler 登入、`workers.dev` 部署、自訂網域、公開收錄。只有 `verify` 通過的層級標示完成。
- 剩下的人類接觸點與下一個唯一建議動作。
- 上線報告（見 `references/launch-checklist.md`），交接給第二版的 `website-operations`。

## 停止條件

- 專案缺少 `dist/`、`dist/` 比來源舊，或 `wrangler.jsonc` 含 `main`、綁定資源或帳號識別碼。
- Wrangler 未登入且使用者尚未完成瀏覽器授權。
- 使用者未對本階段的預覽明確授權。
- `deploy` 回傳非零、未輸出網址且 `verify` 讀不到網站。
- 自訂網域的 NS 不在 Cloudflare、該主機名已有 CNAME，或使用者想要的頂級網域不在 Cloudflare Registrar 清單且尚未決定外部註冊商。
- `verify` 有 finding 且一次修正後仍失敗。
- 任何步驟需要付費、需要輸入付款資料或需要 Cloudflare 後台操作以外的權限。

停止時保留已部署的版本與所有本機檔案，不回滾、不刪除、不重送。

## 驗證

公開候選版以虛構專案與假的 wrangler 程式驗證：登入與未登入的解析（信箱遮罩、不記帳號 ID、判斷 zone 權限）、部署預覽與 stale dist 警告、首次部署拒絕 `index`、`deploy` 需要旗標且能解析 `workers.dev` 網址、失敗時停止、`verify` 對本機服務的完整輸出通過並對缺檔與 robots 不符失敗、`domain apply` 正確寫入 routes 與 `_redirects` 且重跑不重複、`publish` 拒絕 example.invalid 並需要旗標、`wrangler.jsonc` 含禁止欄位時停止。真實 Cloudflare 登入、部署、網域與另一臺電腦驗收延後到所有工具包完成後集中執行。
