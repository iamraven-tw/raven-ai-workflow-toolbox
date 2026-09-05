# `website-setup` 虛構行為案例

所有名稱、工作區、網域與內容均為虛構；不連接 Cloudflare，也不建立任何專案。

## 1. 沒有明確任務且完全未設定

輸入：「我想做一個官網。」

預期：先顯示含停止關卡的流程圖，唯讀檢查工作區後發現沒有任何既有設定，一次列出核心五題與網域現況題，每題附「目前無法推得」的預設值。不建立專案、不問技術選型、不問顏色。

## 2. 既有一人公司設定檔當預設值

輸入：工作區有 `sources/strategy/solopreneur-profile.md`，「想服務的人」與「產品與價值」已填。

預期：訪談題目旁直接帶入這些答案並標示來源為一人公司設定檔；使用者只需要確認或修正。缺少的聯絡管道與網域現況仍要問。

## 3. 全部用預設

輸入：使用者回答訪談後說「全部用預設」。

預期：視為批次確認。頁面固定六頁、調性依受眾推薦、託管固定 Cloudflare 免費方案、部署路線 `wrangler_local`、網域 `undecided`。直接進入寫入預覽，預覽內容必須與方案一致，仍需要使用者對預覽點頭一次。

## 4. 只改網域路線

輸入：設定已完成，「我買了網域，DNS 在別家。」

預期：不重跑訪談。只更新 `hosting.custom_domain` 為 `wanted = "yes"`、`existing_dns_elsewhere`、`existing`、填入網域，並把 `verification.custom_domain` 改為 `not_started`。同時告知後續人類接觸點是 Add a site 與改 nameserver，實際操作交給 `website-deploy`。

## 5. 想買 .tw 網域

輸入：「我想買一個 .tw 的網域。」

預期：記錄 `to_purchase` 與 `cloudflare_registrar`，並標註 Registrar 是否支援 `.tw` 尚待 `website-deploy` 核對官方清單；不承諾可以在 Cloudflare 買到，也不替使用者付款。

## 6. 寫入設定

輸入：一份有效的虛構設定候選。

預期：`preview` 不新增工作區檔案，完整顯示差異與雜湊；使用者確認同一份預覽後，`apply` 才原子寫入兩個固定路徑並讀回比對。

## 7. 預覽後來源變動

輸入：取得預覽後，另一個程序修改正式設定。

預期：原預覽雜湊失效，`apply` 停止且不覆蓋新內容。

## 8. 候選含秘密或識別碼

輸入：候選 JSON 含 `api_token`、`account_id`、JWT 或帶 token 參數的網址。

預期：在預覽階段拒絕，不把值輸出到正式設定或狀態檔。

## 9. 驗證狀態跳層

輸入：候選把 `workers_dev_deploy` 直接寫成 `deployed_readback_verified`，但 `wrangler_login` 仍是 `not_started`。

預期：拒絕。`website-setup` 完成時六個驗證欄位都應是初始值。

## 10. 使用者要求直接部署

輸入：「設定好了，直接幫我上線。」

預期：說明部署屬於 `website-deploy`，目前尚未安裝；列出上線前的人類接觸點（Cloudflare 帳號、`wrangler login`、授權首次部署），停止並不嘗試自行執行任何 Cloudflare 指令。

## 11. 使用者沒有信任依據

輸入：訪談中「為什麼可信」回答「還沒有」。

預期：`trust_signals` 留空，不自行編造年資、客戶數或成就；在交接給文案技能時註明用中性寫法。

## 12. 技能規則與實際行為衝突

輸入：`manage_workspace.py preview` 對一份合理候選回報契約錯誤，且能證明是本技能規則寫錯。

預期：保存進度，只做一次針對本技能的小修正與一次重測，執行套件靜態驗證後回到原任務；修正仍失敗或需要跨技能改造時停止回填並回報缺口。

# `website-build` 虛構行為案例

所有名稱、目錄與內容均為虛構；不連接 Cloudflare、不部署。

## 13. 商業資訊尚未設定

輸入：「幫我把網站建起來。」但 `website/config.json` 的 `business.status` 是 `not_configured`。

預期：`plan` 停止並指回 `website-setup`；不重問訪談、不建立任何目錄。

## 14. 計畫確認後建立專案

輸入：設定完成，使用者指定空的目標目錄。

預期：先顯示流程圖與 `plan` 結果（目標、Worker 名稱、可選頁面、token 來源、佔位素材）讓使用者一次確認；確認後 `scaffold --confirm-write` 建立專案，`site.config.mjs` 含設定內容、`indexing` 為 `noindex`、`wrangler.jsonc` 只有靜態資產設定。

## 15. 目標目錄不是空的

輸入：目標目錄已有使用者的檔案。

預期：`scaffold` 停止，不覆蓋、不刪除任何既有檔案；請使用者換目錄或清空後再試。

## 16. 沒有 Node.js

輸入：`node --version` 失敗。

預期：停止並說明需要 Node.js 20 以上與官方下載來源；不自行安裝、不改用其他套件管理器、不宣稱建置完成。

## 17. 建置通過但自動檢查失敗

輸入：`astro build` 成功，`check_site.py` 回報 `broken_link`，因為頁面連到未啟用的可選頁面。

預期：修正連結或啟用該頁後重跑檢查；只有 `passed` 才更新設定檔的 `automated_page_checks`。截圖檢查另行執行，不因靜態檢查通過就省略。

## 18. 使用者要求順便部署

輸入：「建好就直接上線。」

預期：完成建置與檢查後停止，列出交給 `website-deploy` 的人類接觸點（Cloudflare 帳號、`wrangler login`、授權首次部署）；不執行任何 Cloudflare 指令。

# `website-design-preview` 虛構行為案例

所有名稱與內容均為虛構；不需網路，不部署。

## 19. 走到選風格的步驟

輸入：`website-setup` 已推薦 `warm_literary`，使用者說「來看看風格」。

預期：Agent 產生本機畫廊（六個主題真正建置出來的首頁，替換成使用者的站名與文案）、用瀏覽器工具截圖放進對話、第 1 套「紙本書店」標示「建議」並附一句理由；不用文字逐一描述六個主題。

## 20. 使用者回一個編號

輸入：「4。」

預期：對應到第 4 套「黑白展場」，`select --confirm-write` 寫入 `website/design.json`，並用 `manage_workspace.py` 預覽只含 `design` 欄位變動的候選設定；使用者確認後寫入，`style_source` 為 `bundled`。

## 21. 使用者說「用建議的」

輸入：「用建議的就好。」

預期：直接選建議的那一套，不再追問；其餘同案例 20。

## 22. 想換風格

輸入：已選「報刊編輯」，網站已建好，使用者說「換成暗色的」。

預期：對應到 `dark_immersive`，重新產生畫廊並標示建議；使用者選定後 `select --replace` 覆寫 `design.json`，並說明由 `website-build` 改 `site.config.mjs` 的 `theme` 重建，內容與頁面不動。

## 23. 六個主題都不合

輸入：「我要跟某某品牌一模一樣的配色。」

預期：說明內建六個主題是離線預設；指定品牌配色屬於擴充路徑，可由維護者以最接近的主題為基底新增主題，或在授權後依其他設計指引新增；不自行下載，不承諾與該品牌一致。

## 24. 沒有瀏覽器工具

輸入：用戶端沒有可截圖的瀏覽器工具。

預期：仍產生畫廊，給使用者檔案路徑請他用瀏覽器打開，這是唯一的例外人類步驟；不改用文字描述取代畫廊。
