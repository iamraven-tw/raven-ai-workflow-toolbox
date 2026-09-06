# AI Agent 規則與技能盤點技能包維護規則

本目錄是公開、去識別化的技能包來源。它只負責安裝與說明上游 [iamraven-tw/agent-inventory](https://github.com/iamraven-tw/agent-inventory)，不含任何實際掃描程式。

## 修改邊界

- `install.manifest.toml` 是固定版本、受管理技能、註冊目標與安裝狀態的唯一機器可讀來源。
- 不得把上游原始碼複製進本目錄。本套件沒有 `skills/`；受管理入口全部來自已驗證的上游 clone。
- 上游版本一律鎖定 tag 與完整 commit，並記錄 tree 與 LICENSE 的 SHA-256；不得追蹤未鎖定的 `main`，也不得因上游有新版就自動升級。
- 升級上游時：先更新 `[integration.agent_inventory]` 的 tag、ref、tree 與授權雜湊，重跑本套件測試，再更新 `[[readiness_gates]]`。
- 不得在安裝流程中執行掃描、讀取使用者規則內容、產生摘要或修改任何既有技能。
- 上游具備刪除檔案、改寫原檔與啟動外部程式的能力。這些必須維持在 `[human_authorization_gates]` 明列，且文件不得暗示安裝器會代為執行。
- 上游對外的網路行為（網頁編輯器從 `esm.sh` 載入 CodeMirror 6）必須保留在隱私文件中，不得省略。
- 不得寫入維護者的真實路徑、帳號、掃描結果或任何本機盤點內容。上游的 `PLAN.md` 未公開，不得引用其內容。

## 驗證規則

任何完成宣告都要分開回報：靜態結構、上游固定版本與雜湊、本機安裝生命週期、用戶端技能發現、實際盤點執行、另一臺電腦驗收與正式公開支援。只有實際執行並取得證據的層級才能標示通過。

修改套件後執行 `tests/validate_package.py` 與 `python3 -m unittest discover -s tests -p 'test_*.py'`。
