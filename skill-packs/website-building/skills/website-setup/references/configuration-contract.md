# 設定契約

`website/config.json` 的結構由 `website-config.schema.json` 定義；`scripts/manage_workspace.py` 以純標準函式庫實作相同規則，並額外檢查跨欄位一致性。以下是 Agent 在產生候選設定時必須遵守的規則。

## 秘密與私人識別碼

- 不得出現 token、secret、password、cookie、credential、api key、access key、client id、account id、zone id、deploy hook 等欄位。
- 不得出現 JWT、Bearer、私鑰或帶 token 參數的網址。
- Worker 名稱、網域與聯絡信箱本來就會公開，可以寫入；公開範本必須留空。

## business

- `status = "not_configured"` 時所有欄位必須為空，`primary_call_to_action.kind` 必須是 `not_selected`。
- `status = "configured"` 時必須有 `site_name`、`one_line_positioning`、`audience_summary`、至少一項 `offerings`、`primary_call_to_action.kind != "not_selected"` 與 `label`。
- `primary_call_to_action.kind = "mailto"` 時 `target` 必須以 `mailto:` 開頭；`external_link` 時必須是 `https://`；`form_later` 時 `target` 必須為 null。
- `contact_channels[].kind = "email"` 時 `target` 必須以 `mailto:` 開頭；其他類型必須是 `https://`。
- `profile_source` 必須是工作區相對 POSIX 路徑的 Markdown 檔，或 null。

## pages

`pages.required` 沿用名稱但代表已選核心頁面；至少首頁與技術用 404，其他核心頁面可選，無重複且僅接受已支援識別。部落格不預選；`pages.optional` 保留作品集等額外類型。舊六頁設定有效，不自動刪掉既有網站頁面。

技術 verification 更新由 Agent 依真實結果自動預覽、套用及讀回；已核准本機工作不再要求使用者確認雜湊。商業事實及設計方案仍批次確認。

## design

- `fonts` 只能是 `google`（預設，各主題載入自己的 Google Fonts 中文字型，網站會向 Google 發請求）或 `system`（只用系統字型，不發外部請求）。批次確認時要用一句話說明這個差別。

- `status = "not_selected"` 時 `tonality`、`style_source` 必須是 `not_selected`，`style_id` 為 null。
- `status` 為 `recommended`、`previewed`、`confirmed` 時 `tonality` 不得是 `not_selected`。
- `status = "confirmed"` 時 `style_source` 不得是 `not_selected`；`bundled`（範本內建六個主題）、`open_design` 與 `daisyui` 必須有 `style_id`；`neutral_default` 的 `style_id` 必須為 null。

## hosting

- `provider` 固定 `cloudflare_workers_static`，`plan` 固定 `free`，`workers_dev.enabled` 固定 true。
- `custom_domain.wanted` 為 `undecided` 或 `no` 時：`current_state = "none"`、`acquisition_route = "not_selected"`、`domain = null`。
- `wanted = "yes"` 時 `acquisition_route` 不得是 `not_selected`；`existing` 必須搭配 `existing_on_cloudflare` 或 `existing_dns_elsewhere` 並填 `domain`；`cloudflare_registrar` 與 `external_registrar` 必須搭配 `to_purchase`。

## verification

驗證狀態不得跳層：

- `workers_dev_deploy = "deployed_readback_verified"` 需要 `wrangler_login = "verified"` 與 `local_build = "passed"`。
- `custom_domain.wanted != "yes"` 時 `verification.custom_domain` 必須是 `not_applicable`；`wanted = "yes"` 時不得是 `not_applicable`。
- `verification.custom_domain = "verified"` 需要 `workers_dev_deploy = "deployed_readback_verified"`。
- `public_index = "index_verified"` 需要 `workers_dev_deploy = "deployed_readback_verified"`；若 `wanted = "yes"`，還需要 `verification.custom_domain = "verified"`。

`website-setup` 完成時，`verification` 六個欄位都應維持初始值；只有對應技能實際執行並讀回後才能更新。
