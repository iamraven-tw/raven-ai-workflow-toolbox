# 人類接觸點清單

這是本技能包對使用者的承諾。第一版完成時，人類需要親自做的事只有下列項目；其餘由 Agent 完成。每一項都寫明為什麼 Agent 不能代辦，避免日後因為方便而把工作推回給人。

| 接觸點 | 類型 | 頻率 | 為何不能由 Agent 代辦 | 負責技能 |
|---|---|---|---|---|
| 回答商業資訊訪談（服務對象、提供什麼、為何可信、希望訪客做什麼、聯絡方式） | 提供事實 | 一次 | 只有使用者知道 | `website-setup` |
| 確認頁面清單、風格與文案的預設方案，或說「全部用預設」 | 決定 | 每個技能一次批次確認 | 品牌取捨屬於使用者 | `website-setup`、`website-content-writing`、`website-design-preview` |
| 建立 Cloudflare 帳號 | 帳號 | 一次 | Agent 不得建立帳號 | `website-deploy` |
| 在瀏覽器完成 `wrangler login` 的 OAuth 同意 | 登入 | 一次，Token 到期後再一次 | 登入與同意必須由本人操作 | `website-deploy` |
| 決定 `workers.dev` 帳號子網域名稱（首次啟用時） | 決定 | 一次 | 名稱屬於品牌取捨 | `website-deploy` |
| 授權首次部署到 `workers.dev` | 授權 | 一次 | 建立公開連結 | `website-deploy` |
| 購買網域（若要自訂網域） | 付費 | 一次 | 付費操作，Agent 不得輸入付款資料 | `website-deploy` |
| 在 Cloudflare 後台「Add a site」加入網域並選免費方案（只在網域不是向 Cloudflare 購買時） | 外部帳號 | 一次 | Wrangler 的 OAuth 沒有建立 zone 的權限；改用 API Token 同樣要人進後台建立，人直接加入反而較省 | `website-deploy` |
| 在網域註冊商改 nameserver 指向 Cloudflare（只在網域不是向 Cloudflare 購買時） | 外部帳號 | 一次 | 註冊商後台需要本人登入 | `website-deploy` |
| 授權綁定自訂網域與正式公開（移除 `noindex`） | 授權 | 一次 | 公開發布 | `website-deploy` |
| 提供 Logo、個人照片等自有素材 | 提供事實 | 可選 | Agent 可先用佔位圖，使用者想換再提供 | `website-build` |

## 不自訂網域時的最小路徑

人類只做四件事：回答訪談、批次確認、`wrangler login` 同意、授權首次部署。

## 使用規則

- 技能不得新增本清單以外的人類步驟。真的需要時，先更新本清單與 ADR，說明為何無法由 Agent 代辦。
- 每次只交回一個當下必要的人工作業，說明完成後如何把控制權交回 Agent。
- 平台額外要求重新驗證密碼、身分或付款資料時，標示為平台強制的額外關卡；不要承諾固定點擊次數。
