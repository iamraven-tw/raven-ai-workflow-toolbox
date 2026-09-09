# Facebook 初始化 Windows 實機驗收

日期：2026-09-09。仍屬於 `social-media-setup`，不代表選題、報表或發布技能整段已驗收。使用獨立測試 App 與本人可管理的已確認 Page；公開紀錄不含真實帳號、ID、貼文、指標數值、憑證或私人路徑。

| 層級 | 結果 |
|---|---|
| 後台設定 | 七項 Pages 核心 permission 可供測試；一般／用戶權杖的 Business Login 組態與既有本機 HTTPS callback 已讀回 |
| App Secret | Windows Credential Manager 保存讀回與官方 App 身分核對通過 |
| OAuth | 本人同意後，以 `config_id`、state 與 HTTPS callback 完成；短／長 User Token 的 App、類型、使用者及精確 scope 核對通過 |
| Page Token | 完整 `/me/accounts` 回傳空清單；官方指定 Page 路徑取得 Token，PAGE 類型、App、scope、期限及 Page 身分核對通過，原生保存後新 Runtime 可取用 |
| 內容 | 官方 Page posts 回傳 HTTP 200 與非空貼文樣本；有下一頁，coverage 僅為 sample_only |
| 成效 | 共用連線 adapter 成功讀取 Page 帳號層單一 metric 的日資料與官方說明；coverage 仍是 unknown，未推定期間完整或產生成長率 |
| Messenger／寫入 | 後續補驗已完成 Messenger scope、OAuth 與 Conversations 唯讀樣本；未發布、回覆、訂閱 Webhook 或傳送私訊 |
| macOS／另一臺電腦／公開使用者 | 未實機驗收；App 角色測試不等於 App Review、Business Verification 或正式公開支援 |

實測修正：時間戳 proof 預留 60 秒；完整 Page 清單缺目標時查詢已確認 ID；Insights 明確選取 `description_from_api_doc`。最後一項保留原先嚴格指標契約，修正的是請求漏選必要欄位。見 [OAuth 契約](../skills/social-media-setup/references/oauth-runtime.md)、[疑難排解](../skills/social-media-setup/references/troubleshooting.md)與 [Facebook 成效](../skills/social-performance-analysis/references/platforms/facebook.md)。

僅保存選定 Page Token；短／長 User Token 與診斷回應只在程序記憶體，不持久保存。診斷程序已結束。一般檔案中的狀態及公開證據均不含秘密。

針對性回歸：OAuth Runtime 35 項、Instagram via Facebook Login 18 項、正式成效 adapter 9 項、指標目錄 6 項，共 68 項通過；套件靜態驗證與差異空白檢查通過。虛構測試涵蓋指定 Page 路徑成功、錯目標、缺 Token、列舉失敗不降級，以及成效請求必須選取官方說明欄位。

## Messenger 後台設定補驗

2026-09-09 接續同一初始化技能：從 App 的新增使用案例之「商務式訊息」分類加入 Messenger，讀回 `pages_messaging` 為可供測試；修改原有一般／用戶權杖組態，保存後展開確認七項 Pages 核心加上 Messenger 共八項明列權限。`public_profile` 仍由 Facebook Login 隱含提供，沒有加入廣告、付費行銷或企業資產權限。

首次等待逾時後，查核原生庫確認 Facebook App Secret 仍可用，沒有要求重貼。以新 state 沿用使用者已確認的既有授權完成 OAuth；八項明列 scope 加上隱含 `public_profile`、PAGE Token、App／Page 身分及期限核對通過，原生保存後新程序可取用。官方 `GET /{page-id}/conversations?platform=messenger&fields=id,updated_time&limit=1` 回傳 HTTP 200 與非空樣本，有下一頁，只記為 sample_only。未讀取訊息正文或發送訊息，也未部署／訂閱公開 Webhook。

新增 scope 後，舊預設測試連線的嚴格 scope 檢查實際回報 `permission_mismatch`。唯讀核對確認兩個 connection 為同一獨立測試 App 與同一 Page、唯一差異為已核准的 `pages_messaging`，才將已驗證的新 bundle 和清單交接至預設 main；舊世代保留。預設 Runtime、原有 posts 與 insights 讀取重新通過。不能因另一個 connection 成功就假設下游預設連線也已更新。
