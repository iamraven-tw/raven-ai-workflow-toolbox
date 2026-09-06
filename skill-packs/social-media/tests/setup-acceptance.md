# social-media-setup 單技能驗收

本入口只測試設定技能的工作區交易、憑證、Terminal、OAuth 與 OpenCLI 來源契約，不執行其他社群技能。從 Toolbox 根目錄執行；也可使用腳本絕對路徑，無須切到 tests 目錄。

```powershell
python skill-packs/social-media/tests/run_setup_tests.py
python skill-packs/social-media/tests/validate_package.py
```

macOS 可使用同一支腳本與當前 Python 解譯器。測試子程序沿用 `sys.executable`，不假設 Windows 有 `python3` 別名。測試 fixture 使用中文與空白工作區路徑，涵蓋 preview 不寫入、apply 後讀回、錯誤雜湊、秘密拒絕、憑證中斷與鎖競爭。

Windows 無 symlink 建立權限（WinError 1314）時，明確 skipped 該連結防護案例；其他 OSError 仍失敗。同時寫入的鎖競爭獨立執行，不因連結權限而漏測。具備 symlink 權限的 Windows 與 macOS 必須讓對應案例實際執行。

## 原生 Windows 憑證驗收

經核准的本機測試可以額外執行：

```powershell
$env:SOCIAL_NATIVE_ACCEPTANCE = '1'
python skill-packs/social-media/tests/run_setup_tests.py
Remove-Item Env:SOCIAL_NATIVE_ACCEPTANCE
```

這會在臨時工作區的唯一 namespace 寫入一次性虛構值，用新 Python 程序讀回並比對雜湊，再移除本測試建立的項目。只輸出驗證結果；不接觸既有帳號憑證、不登入平台。預設不啟用。macOS 原生測試仍有自己的平台閘門，Windows 成功不代表 macOS 已實測。

## 人工流程

1. 選定虛構情境、工作區與策略；已提供的答案不重問。
2. 產生完整候選與 preview；展示每個實際欄位及平台尚未驗證狀態，不能只有摘要。
3. 使用者確認同一份預覽後才 apply；讀回設定及狀態，核對 hashes_match、contains_credentials=false。
4. 展示交接資訊與尚未驗證部分。此技能確認正確後，才由使用者決定下一技能。

OpenCLI 來源契約的單元測試不等於已下載、建置或啟用 Bridge；虛構 OAuth 不等於真實 App、登入與平台讀取。這些必須分開驗收，不由一般設定套用推定成功。
