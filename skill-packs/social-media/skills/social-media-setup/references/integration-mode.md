# 平台整合初始化模式

## 決策單位與預設授權

驗證仍以「平台 × 功能」為單位，例如「Instagram 發布」或「YouTube 公開留言」，不要把整個平台標成一次完成。功能分成：`account_read`、`publish`、`public_comments`、`analytics`、`direct_messages`。`account_read` 只用於驗證登入帳號與平台資源，不能替代其他四種功能的驗收。

授權則依 [平台權限選擇契約](permission-selection.md) 處理：使用者選取平台且沒有主動縮小範圍時，預設提出該平台所有已支援核心功能的完整 permission／scope；不是只開目前第一個任務的權限。使用者可在 OAuth 前刪減，刪減後不阻擋仍可完成的明確任務。

## 規劃與執行路由

1. 從明確任務辨識平台與資源；無法辨識時一次只問一題。若選取 Meta 旗下任一平台，再詢問是否於同一次初始化一併設定 Facebook、Instagram 與 Threads。
2. 只讀被選取平台的參考文件，重新確認官方文件日期與目前限制。
3. 列出完整核心權限、相依權限、平台自動附帶權限及相鄰延伸權限，記錄帳號前提、官方介面、App Review／稽核需求、人工步驟與可驗證結果。
4. 依正式 API、官方連接器、可靠 CLI、受控登入瀏覽器、Computer Use、手動預覽的順序選介面。無法採用較前路線時，記錄原因。
5. 將工作拆成以下獨立狀態，不跨級推論：
   - 本機準備
   - API／開發者 App 準備
   - 使用者登入／OAuth 同意
   - 平台讀取驗證
   - 遠端寫入驗證
6. 使用者只要求規劃時，交付權限與執行預覽並停在 `planned`。使用者授權外部整合後，Agent 要實際建立與設定開發者 App、OAuth、已確認權限及 API 讀取，不能改成交給使用者自行照文件操作。
7. Agent 先檢查可用受控瀏覽器、callback 與秘密儲存。專案初始化的 OpenCLI 準備依 `opencli-initialization.md`，先告知作者來源及影響，在核准範圍內由 Agent 下載與驗證；不把「已有 CLI」當成 Bridge 已連線。使用者未指定秘密管理工具時，依 `local-credential-storage.md` 預設採 macOS Keychain 或 Windows Credential Manager，並把 backend 與憑證名稱列入外部變更預覽；任一必要條件缺少時停止於取得 Secret 或 Token 之前。
8. Agent 開啟官方後台、填寫欄位、選 use case／產品、設定 redirect URI 與啟動 OAuth。只在登入／2FA／Passkey、法律條款、OAuth 同意及平台強制驗證時把控制權交回使用者。
9. OAuth 完成後由 Agent 交換並安全保存 Token。callback 可取得的值直接寫入原生憑證庫；只有平台強制由人取得的 Secret／API key 才交由使用者在可見 Terminal 的隱藏提示貼上一次。保存後再用正式 API 分別讀回目標資源與實際授予權限；要求清單、OAuth 畫面與讀回結果不一致時停止。
10. 只有實際讀回符合預期的帳號、資源、權限或遠端結果，才能標為 `verified`；只有設定畫面或成功送出請求時使用較低狀態。

## 最小人工作業契約

一般情況只安排兩個瀏覽器人工關卡：

1. 使用者完成登入、安全驗證、首次開發者條款或帳號選擇。
2. 使用者在 OAuth 畫面檢查權限與資源並同意。

外部 App 建立與一般設定寫入仍各有一次對話確認，但使用者不必親自操作技術後台。Agent 不得要求使用者手動尋找設定頁、貼上授權碼、執行 API 指令或解讀原始 JSON。平台只允許人類看到 Secret／API key 時，可增加一個 Terminal 隱藏輸入關卡；Agent 先開好 Terminal 與提示，使用者只貼上一次，值不進入對話、命令歷史或程序參數。平台臨時要求的重新驗證另計並明確標示。

選取 Facebook、Instagram 或 Threads 時，另外讀 `meta-api-setup.md`。三者可在同一次設定工作中規劃、預覽及依序代辦，但 Facebook Pages、Instagram Login、Facebook Login 與 Threads use case 的帳號關係、OAuth、App ID／Secret、Token、審查與驗證證據不得互相推定。

## 私訊邊界

平台有正式管理介面且本技能包已記載實作路徑時，`direct_messages` 屬於預設完整核心權限。權限預覽必須同時揭露帳號類型、使用者是否必須先發起對話、回覆時限、審查、Webhook、資料保留與自動化政策；使用者可在 OAuth 前移除。平台沒有正式私訊介面時標示不支援，不得用公開留言冒充。

## 憑證

一般設定只記錄意圖、偏好介面與狀態，不記錄 Token、secret、Cookie、真實帳號識別碼或檔案位置。依 `local-credential-storage.md` 處理實際值與非敏感參照；若環境沒有支援的安全儲存，停止並說明缺口。
