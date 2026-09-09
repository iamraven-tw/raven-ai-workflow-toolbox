# Threads 官方測試權杖匯入

查證日期：2026-09-09。只用於本人持有 App、已接受 Threads 測試角色且後台提供用戶權杖產生器的情況；不代表公開使用者 OAuth 或回呼設定通過。

## 流程

1. 依主技能沿用已確認的 App、目標 username、確切 scope、原生保存與讀取／刷新範圍。需要的新權限只確認差異，不因更換取得方式重新詢問相同範圍。
2. 確認 Windows Credential Manager 或 macOS Keychain 可用；用 `credential_terminal.py launch --workspace-root <私人工作區> --platform threads --name dashboard-token --confirm-store` 準備隱藏輸入。
3. 在 Threads 設定的用戶權杖產生器選定測試帳號。本人完成官方同意畫面，將產生的 Token 貼入隱藏輸入視窗；Agent 不讀取 Token 畫面、剪貼簿或秘密欄，不要求貼進對話。若瀏覽器無法開啟產生器視窗，交接此按鈕，不修改安全設定或拼湊內部請求。
4. 收據 `verified` 只證明暫存原生項目可讀。執行下列匯入命令；參數只含私人識別資料及 scope，不包含 Token。

```text
python scripts/threads_token_import.py --workspace-root <私人工作區> --client-id <Threads專用AppID> --username <已確認帳號> --graph-version v1.0 --scope threads_basic --scope threads_manage_insights --source-ref dashboard-token --confirm-read --confirm-store
```

範例唯讀 scope 不取代使用者已確認清單；依實際同意畫面與任務提供全部 scope。匯入拒絕少授予或多出未核准的 scope，不自動擴權。不得透過反覆重新產生 Token 來猜權限。

5. 程式只使用官方 `debug_token` 與 `/v1.0/me`：要求明確 App ID、相符的 user ID 和 username、精確權限及超過一天的剩餘有效期。缺 App 證據或期限就停止，不自行推定 60 天。期限取自 debugger；匯入時間作為保守的刷新等待起點，至少再等 24 小時。
6. 全部驗證通過後才保存 `callback_mode=token_import` 的私人連線設定與 bundle，沿用 runtime 原生分段保存和讀回；不覆蓋任何既有連線。`oauth_callback.py run` 拒絕此模式。下游仍經 `Runtime.access()` 核對並按已核准政策刷新；另行驗證內容及 insights 端點。
7. `dashboard-token` 是原生庫中的來源副本，不供下游直接繞過 runtime 使用；不含在公開檔案中。清理原生副本需依既有刪除契約處理。中斷保存保持 `storage_incomplete`，不得當作成功或盲目重送；人工核對恢復前不交付連線。

## 驗證與來源

`tests/test_threads_token_import.py` 使用虛構庫與回應測試 App／帳號／scope／期限不符、缺授權、禁止覆寫、保存後跨 runtime 取用及 callback 拒絕。此程式的虛構測試不代表已完成真實 Threads API 驗收。

- 官方後台 Threads 設定畫面明列測試人員的長效權杖產生器；只有當次畫面提供且帳號符合資格時採用。
- [Meta 官方 debugger](https://www.postman.com/meta/threads/request/34203612-e9a7f46e-e48c-4987-a203-22fb25a4b604)
- [Meta 官方 OAuth 範例](https://github.com/fbsamples/threads_api)：使用專用 Threads App 識別資料；不以一般 Meta App ID 代替。
