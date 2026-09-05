# 資料與憑證邊界

## 可以寫入一般設定

- 策略初始化狀態、主要目標、受眾摘要、內容主題與各平台角色。
- 使用者選取的平台功能、偏好介面與整合進度摘要。
- API／App、使用者授權、平台讀取與遠端寫入四個互不代替的驗證狀態。
- 相對於工作區的策略來源路徑。

## 只能留在本機私有狀態或秘密儲存

- Token、Cookie、密碼、API key、OAuth client secret、授權碼與 session。
- App、Page、Channel、Account 等真實識別碼，以及私人發布網址。
- 真實平台資料、歷史貼文、留言、私訊、成效原始值與逐期報告。
- 憑證檔案路徑、帳號電子郵件、私人品牌規則與排程。

`manage_workspace.py` 會拒絕常見秘密欄位與 Token 形狀。這是最低限度防線，不代表可以把一般設定檔當成秘密儲存。

平台整合執行時，使用者沒有另行指定就預設採目前作業系統帳號的 macOS Keychain 或 Windows Credential Manager。App ID、資產 ID、App Secret 與 Token 可依需要保存在該秘密儲存，但不得把值輸出到對話、一般設定、安裝狀態、憑證參照檔或公開套件。`.local/social-media/credential-references.json` 只保存隨機 namespace、backend、平台／憑證名稱與驗證狀態。其他作業系統或原生儲存不可用時，應在取得或顯示秘密前停止，不退回明文檔案。

平台只允許人類取得 Secret／API key 時，Agent 可在可見 Terminal 啟動技能內的隱藏輸入程式，讓使用者貼上一次。OAuth callback 可由 Agent 安全取得的 Token 則直接寫入，不要求人工複製。原生憑證庫只提供作業系統使用者層級保護；可取用憑證不等於授權發布或其他遠端寫入。

## 公開與私人快照

Terminal 交接的 `.local/social-media/credential-input/` 只保存一次性非敏感收據；`credential-store.lock` 只供程序互斥。憑證參照中的 `pending_write`／`pending_delete` 不是可用憑證；未知結果不得重送。完整規則見 [本機憑證儲存](../skills/social-media-setup/references/local-credential-storage.md)。

OAuth 程式另外使用 `oauth-runtime.lock` 與 `.local/social-media/oauth/` 的非敏感狀態。連線設定及分段 token bundle 留在原生庫，不在狀態檔保存私人 ID、URL、scope 回應、授權碼或 Token。舊世代不自動刪除，清理需另行確認。完整路徑與失效／中斷處理見 [OAuth 執行契約](../skills/social-media-setup/references/oauth-runtime.md)。

公開套件只提供中性範本。任何私人工作區都獨立演進；更新公開技能不自動同步私人設定，私人改動也不自動回流公開 repository。
