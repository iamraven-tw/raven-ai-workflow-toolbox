# API 權杖生命週期維護

平台 OAuth 成功且憑證已安全保存後讀取本文件。目標是避免長期未使用的連線在使用者不知情時到期；這是平台整合的一部分，不是內容發布排程。

## 預設結果

凡連線使用會到期、可刷新、可撤銷或受資料存取期限影響的權杖，Agent 必須在同一次整合預覽中列出維護排程。使用者確認平台整合及持續憑證取用後，Agent 應建立排程並立即執行一次驗證。除非使用者明確拒絕排程，否則只有 API／OAuth、平台讀取及維護排程都驗證成功，才能將整合標為完整完成。

使用目前環境正式提供的 recurring automation／scheduled task；需要本機工作區、原生憑證庫或程式時，排程必須在保存憑證的同一臺電腦與同一作業系統使用者下執行。若環境沒有可用排程器，將 `credential_maintenance` 標為 `not_configured`，清楚說明斷線風險及唯一下一步，不用聊天提醒冒充自動刷新。

## 平台差異

不要假設所有平台都是每 60 天直接換一枚權杖：

| 路線 | 排程行為 |
|---|---|
| YouTube Desktop OAuth | 定期呼叫既有 Runtime；短效 access token 到期時使用已保存 refresh token 更新，並驗證頻道身分。refresh token 被撤銷或失效時通知本人重新 OAuth。 |
| Instagram Login | 每次先驗證身分；長期 User Token 仍有效、取得至少 24 小時且進入 Runtime 的最後七天窗口時刷新。過期後不可刷新。 |
| Threads | 每次以官方 debugger 與 `/me` 核對；長期 User Token 仍有效、取得至少 24 小時且進入最後七天窗口時刷新。測試權杖匯入也沿用相同 Runtime，但不能把刷新說成 callback 已驗收。 |
| Facebook Pages | 每次核對 Page Token、App、scope、Page 身分、可判斷的權杖期限與資料存取期限。`expires_at=0` 只代表沒有排定的權杖到期時間；沒有通用的 IG／Threads 式刷新。失效或資料存取期限逼近時通知本人重新 OAuth。 |
| Instagram via Facebook Login | 使用 Page Token，處理方式同 Facebook Pages；不得套用 Instagram Login 的刷新端點。 |

所有到期日以正式回應為準，不硬編碼 60 天。刷新只延續既有帳號、App、scope 與連線，不增加 permission、不切換資源、不建立新 App。

## 建立排程

預設每天在使用者時區的低干擾時段執行一次；已有相同工作區與連線的維護排程時更新原排程，不建立重複項目。排程使用已安裝技能中的：

```text
python <skill-directory>/scripts/token_maintenance.py \
  --workspace-root <workspace> \
  --platform instagram --platform threads --platform facebook --platform youtube \
  --connection main --confirm-read --allow-refresh
```

只列入本次已完成且使用者同意持續維護的平台。`--allow-refresh` 是同一份整合預覽內的持續刷新授權；不授權重新登入、重新 OAuth、增加權限或其他遠端寫入。排程提示必須包含：

- 正常且沒有變化時保持安靜。
- 刷新成功時回報平台與新的非敏感期限摘要。
- `reauth_required`、`expired`、`permission_mismatch`、`target_mismatch`、`refresh_required`、資料存取期限逼近、秘密庫不可用或連續執行失敗時通知使用者。
- `remote_result_unknown`、`storage_incomplete`、`recovery_required` 或本人操作需求出現時停止，不重送、不自行開 OAuth。
- 不輸出 Token、secret、私人 ID、原始平台回應或秘密庫內容。
- 不發布內容、不回覆、不傳送私訊、不刪除資料、不變更平台設定。

本機排程需要電腦開機、網路可用、排程產品保持執行，且工作區仍在原位置。建立後立即手動執行一次；讀回排程名稱、狀態、頻率、目標工作區及首次非敏感結果。排程存在但首次執行失敗，狀態只能是 `partial`。

## 回報與狀態

新增獨立層級 `credential_maintenance`：

- `not_applicable`：沒有 OAuth 權杖或平台不提供可維護的連線。
- `not_configured`：需要維護但尚未建立排程。
- `declined`：使用者明確拒絕；同時回報預期中斷風險與手動處理方式。
- `scheduled_unverified`：排程已建立，尚未完成首次執行。
- `verified`：排程已讀回且首次維護檢查成功。
- `attention_required`：權杖、資料存取期限、排程或本機條件需要處理。

通知只包含平台、連線代稱、狀態、是否刷新、非敏感期限與下一步。正常的每日執行不需要產生訊息；避免使用者因重複無變化通知忽略真正的失效警示。
