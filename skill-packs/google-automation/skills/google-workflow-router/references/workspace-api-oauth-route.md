# Workspace API 與 OAuth 路線

## 先選身分模式

依 [Google Workspace 憑證選擇](https://developers.google.com/workspace/guides/create-credentials) 判斷：

| 情況 | 常見身分模式 | 重要限制 |
|---|---|---|
| 只讀取公開資料 | API key | 不能代表使用者存取私人資料 |
| 代表使用者讀寫 Workspace 資料 | OAuth client | 需要同意、redirect URI 與最小 scope |
| 應用程式擁有或被明確分享的資料 | 服務帳戶 | 服務帳戶不是一般使用者，不會自動取得使用者檔案 |
| Google Cloud 內的工作負載 | 附加的服務帳戶／工作負載身分 | 優先避免可下載的長期服務帳戶金鑰 |

網域層級委派與 Admin SDK 需要管理員與專門安全設計，不在本 MVP。

## OAuth 關卡

1. 列出實際需要的 API 與最小 scope。
2. 說明內部／外部受眾、測試使用者與正式環境差異。
3. 建立 Cloud Project、啟用 API、設定同意畫面、建立 OAuth client 分別列入遠端變更計畫。
4. client secret 與 Token 只存於適合的本機秘密儲存或部署平台，不貼入對話、不進 Git、不進 Toolbox 狀態。
5. 敏感或受限 scope 可能需要正式驗證；查閱 [OAuth 政策](https://developers.google.com/identity/protocols/oauth2/policies) 與 [敏感 scope 驗證](https://developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification)。

服務帳戶金鑰會增加外洩風險。部署在 Google Cloud 時，依 [服務帳戶最佳實務](https://cloud.google.com/iam/docs/best-practices-service-accounts) 優先使用附加身分、模擬或 Workload Identity Federation，而不是產生長期 JSON 金鑰。

## 本機可先完成

- API 與資料模型選擇。
- scope 清單與威脅／錯誤情境。
- 使用虛構 fixture 的 client 邊界、重試、分頁與冪等測試。
- `.env.example` 或欄位名稱；不得包含真實值。
- OAuth callback、Token 儲存與移除的設計。

上述完成不等於使用者已登入、已授權或遠端 API 已啟用。
