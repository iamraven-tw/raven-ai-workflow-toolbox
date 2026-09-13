# Windows 安裝與測試計畫

制定日期：2026-09-07。基準為 Toolbox commit `b580820c0004b67ca303dc78aaef6cd93d7d5ade`，不以後續 main 變更覆蓋本次結果。

## 提交內容隔離驗證（2026-09-13）

本次提交僅納入知識庫／社群／官網 Windows 修復、官網安裝範本定位與 symlink 補驗；AI 剪片、Google 及權杖維護的其他工作區變更保留未提交。下方相關歷史工作區驗證不代表這些變更已隨本提交發布。

從 Git 暫存區匯出隔離副本，未帶入其他未提交檔案，重新驗證：三包靜態 validator、17 個技能格式檢查與 diff 空白檢查通過；知識庫 24 tests／1 skipped、社群 424 tests／8 skipped、官網 49 tests／4 skipped，皆 0 failures／0 errors。此輪一般帳號執行，社群啟用 Windows 原生唯讀驗收並具 Pillow／tzdata；略過為 12 個 symlink 案例及 1 個未再次啟用的 Node 真實建置案例。symlink 與 Node 的獨立補驗證據見下方，不把略過直接算成通過。社群與先前工作區的 429 項相差 5 項，來自未納入本提交的權杖維護測試，不是刪除測試。

## 一次性 UAC symlink 補驗（2026-09-13 追加）

使用者明確授權後，以一次性 UAC 管理員程序執行嚴格補驗程式；Windows 原生 Python 3.12.14，沿用既有 Pillow／tzdata 環境，沒有安裝依賴。真實 symlink 前置建立成功，程序 exit 0 並已結束。

| 套件 | tests | failures | errors | skipped |
|---|---:|---:|---:|---:|
| AI 知識庫 | 1 | 0 | 0 | 0 |
| 社群媒體 | 8 | 0 | 0 | 0 |
| 官網打造 | 3 | 0 | 0 | 0 |
| 合計 | 12 | 0 | 0 | 0 |

以上僅重跑先前受權限阻擋的 12 個指定案例，不是以管理員身分重跑全部套件。下方完整回歸中的 symlink 略過已有這次獨立通過證據；歷史數字保留。原始報告保存於本機 `.local/windows-symlink-elevated-20260913-102222.json`，不納入公開來源。

未開啟開發人員模式、未修改永久 symlink 權限；測試只操作隔離虛構資料，沒有平台登入、發布、部署或真實憑證操作。提權程序結束後，以一般帳號重跑前置檢查仍為 WinError 1314／blocked（本機報告 `.local/windows-symlink-standard-after-uac-20260913.json`），確認沒有因此取得持續建立 symlink 的能力。此結果不代替 Google／其他套件或 macOS 的補驗。

## Pillow／Node／安裝範本補驗（2026-09-12 再追加）

本節優先於下方同日與歷史基準。Pillow 沿用本機既有隔離 Python 3.12.14、Pillow 12.3.0、tzdata 2026.3，未重新下載或修改該環境；不把私人 runtime 路徑寫入公開來源。

- 社群完整回歸：429 tests、0 failures、0 errors、8 skipped，剩餘略過全部是實際 symlink 建立權限不足。圖片測試不再因 Pillow 缺件整組略過；拆分圖片檔連結與輸出父目錄連結為兩個獨立案例。
- Windows 原生補驗：SOCIAL_NATIVE_ACCEPTANCE=1，以 Windows Credential Manager 原生 API 唯讀查詢隨機不存在目標通過。沒有列舉、讀取、建立或刪除真實憑證。原 macOS 案例改為依目前平台選原生 backend；Windows 通過不代替 macOS 實機。
- Node 真實補驗：Node 22.18.0／npm 10.9.3、WEBSITE_NODE_ACCEPTANCE=1、遙測關閉；隔離安裝技能後由已安裝 scaffold 建專案，以 lockfile 執行 npm ci、Astro build 及已安裝 check_site。全部六主題、可選頁面及文案／文章層通過。不登入或部署 Cloudflare。
- 官網完整回歸（含上述 Node 補驗）：49 tests、0 failures、0 errors、3 skipped，三項略過皆為 symlink 權限；社群與官網靜態 validator、官網五技能格式驗證及 git diff --check 通過。
- WIN-04 已修復：manifest 明列將根層 template 隨 website-build 組合至 assets/template，計算合成雜湊並在暫存複製後核對；更新、回復、收養相同副本與可回復移除都涵蓋範本，修改過的範本會阻擋 update/remove。來源版不新增重複維護副本或同步機制。
- 已驗證來源移走、不同 cwd、工作區搬到中文空白路徑後，安裝副本仍可 list 六主題、render 畫廊與 scaffold。缺失範本會停止，不偷偷取用維護者來源。舊版無附帶範本的副本經明確 update 才升級；私人現有安裝未變更。

### symlink 補驗方式與當時阻擋（已於 2026-09-13 補驗）

目前一般帳號 token 沒有 SeCreateSymbolicLinkPrivilege。嚴格補驗程式
[run_symlink_acceptance.py](../scripts/run_symlink_acceptance.py)
會先以真實 symlink 做前置檢查，再執行三包共 12 個指定案例（知識庫 1、社群 8、官網 3），任何 skip 都回傳失敗，不以 junction、mock 或 WSL 取代 Windows 證據。
一般帳號前置檢查已取得 WinError 1314、blocked、exit 2。當時一次性管理員／UAC 補驗尚待使用者同意，未啟動提權程序；後續授權與完成結果見上方 2026-09-13 紀錄。

選用已具 Pillow 的 Python，在已獲授權且具 symlink 權限的環境執行（report 必須是 .local 下尚不存在的新檔）：

```powershell
& $pythonExe scripts/run_symlink_acceptance.py --report .local/windows-symlink-acceptance.json
```

### 實機範圍不得混淆

上述是本機 Python／原生 OS API／Node 實測，不是社群發布、Cloudflare 部署或 AI 生圖服務驗收。既有 [Facebook Windows 驗收](../skill-packs/social-media/docs/facebook-windows-live-verification.md) 已記錄另一輪核准的 OAuth／Page／成效／Messenger 唯讀樣本，不能泛稱所有平台皆未測，也不能把樣本升成完整期間或發布成功。
新的遠端驗收仍需明確帳號、測試內容、讀寫範圍及必要的人類登入同意；本輪未執行。中文字形與圖片逐字視覺、瀏覽器響應式、另一臺電腦與 macOS 亦不由本機程式通過推定。

## 知識庫／社群／官網修復後驗證（2026-09-12 追加）

本節記錄本次使用者指定的三包測試修復；下方歷史基準保持不變。本次在 Windows 原生 Python 3.14.2 執行，社群使用隔離 venv 及固定 tzdata 2026.3，不更動全域 Python 或已安裝技能。

| 套件 | 修復前 tests／failures／errors／skipped | 修復後 tests／failures／errors／skipped |
|---|---|---|
| AI 知識庫 | 24／0／1／0 | 24／0／0／1 |
| 社群媒體 | 418／5／67／20 | 428／0／0／23 |
| 官網打造 | 43／2／3／1 | 46／0／0／4 |

三包 validator 全部通過；5＋7＋5 個技能的 quick_validate 全部通過；git diff --check 通過。格式驗證使用既有含 PyYAML 的隔離 Python，不為此安裝新依賴。
社群新增 10 項來自拆分混合測試及時區／ACL／錯誤分類回歸；官網新增 3 項命令解析、環境过滤與啟動失敗回歸。測試數增加不是略過原本失敗流程。

### 修復內容與界線

- 知識庫：僅在建立測試 symlink 回傳 WinError 1314 時略過；其他例外照常失敗。不提升權限、不改安裝器對未知連結的拒絕規則。
- 社群 WIN-02：發布 ledger／receipt、留言／私訊 handoff、人工審查及成效證據使用 POSIX 相對路徑序列化；外部輸入仍拒絕反斜線、跳脫與 symlink。Windows 虛構完整流程通過。
- 社群 WIN-03：manifest 與隨技能安裝的 requirements.txt 固定 tzdata 2026.3、wheel SHA-256 與來源。隔離安裝約 340 KiB，驗證 UTC、Asia/Taipei、America/New_York 冬夏及 DST 切換／fold；缺資料回報 timezone_data_missing，不以 UTC 偷換指定時區。四週期及匯入證據回歸通過。
- 社群 WIN-07：POSIX 檢查 0600；Windows 先於空的虛構目錄設定受限 DACL，再檢查原子寫入的證據及 handoff ACL，並用 Everyone 可讀反例確認測試會失敗。OWNER RIGHTS 只有在檔案擁有者等於目前使用者時才接受。實際私人工作區仍須另外確認 ACL，未自動改權限。
- 官網 WIN-06：假 .py CLI 由目前 Python 以 UTF-8 啟動，中文／空白路徑測試通過。正式命令解析 npx.cmd，環境名稱不區分大小寫並保留必要 Windows 目錄，不傳遞 Token。原生 npx.cmd／npm.cmd 在中文空白暫存目錄的自身 --version 命令 exit 0（10.9.3）；這不是實際 Wrangler／部署成功證據。
- 三包的 symlink 缺權限只明確列為 skip。社群原本混在同一方法的鎖／路徑跳脫／公開根目錄拒絕測試已拆開，不因 symlink skip 隱藏其他防護。
- 額外修正 OAuth 測試的偶發誤判：短 ID 可能偶然出現在隨機 SHA-256；只排除格式已驗證的 preview_digest，仍檢查其他輸出不可洩漏 ID／URI。

### 尚未完成

知識庫 1 項略過是 symlink；社群 23 項為 Pillow 缺件 15、symlink 權限 7、未啟用 macOS 原生憑證驗收 1；官網 4 項為 symlink 3、未啟用 Node 真實建置 1。略過不算通過，需在相應環境補驗。
本次沒有更新私人已安裝副本，沒有平台登入、OAuth、發布、Cloudflare 部署或第二臺電腦驗收，也未執行 commit／push。
官網已安裝入口的範本定位問題 WIN-04 不在本次列出的五項測試錯誤內，仍待獨立修復；不得因來源目錄測試通過宣稱官網安裝後全流程已可用。

重跑時在 Toolbox 根目錄使用 PYTHONUTF8=1 與 PYTHONDONTWRITEBYTECODE=1：

```powershell
python -m unittest discover -s skill-packs/ai-knowledge-base/tests -p 'test_*.py'
# 以下使用自己建立的隔離 venv；依社群成效技能的 Python 執行期文件準備。
& .local/social-windows-venv/Scripts/python.exe -m unittest discover -s skill-packs/social-media/tests -p 'test_*.py'
python -m unittest discover -s skill-packs/website-building/tests -p 'test_*.py'
```

## Google／AI 剪片修復後驗證（同日追加）

以下原始基準表保留第一次安裝結果；本節優先反映使用者指定的 Google 與 AI 剪片修復。

| 檢查 | Windows 原生結果 | macOS 狀態 |
|---|---|---|
| Google 固定上游驗證 | 原 validator 通過；43 tests，1 skipped（無 symlink 權限） | 同一 wrapper；有權限時測試照常執行，未於 Mac 實跑 |
| Google Toolbox 回歸 | 9 tests，1 skipped；新增確認不吞其他錯誤的案例 | 測試可直接執行，原生待驗 |
| Google 註冊 | 五個技能＋共用術語檔已安裝 | 原目錄複製機制保留 |
| Video-Use 來源 | 固定 v0.1.1 Release＋逐檔 hash 補丁 | 原始 Release 與依賴 pin 保留 |
| Video-Use 引擎測試 | 98 tests 全通過，包含 Windows／Mac 路徑與平台閘門 | Mac 分支為模擬回歸，非原生實測 |
| Toolbox 補丁／工具防護 | 6 tests 全通過；來源漂移、輸出 hash、未知檔案、跳脫、工具修改皆拒絕 | 純 Python 測試可執行 |
| Windows runtime | uv 0.12.7、Python 3.12.14、FFmpeg 9.0.1、OpenCC 1.4.2；ASR 93 套件、CKIP 27 套件 hash sync 成功 | 原 Homebrew／macOS lock 不變 |
| Qwen／CKIP | import、CPU tensor 運算通過；未下載模型或跑推論 | 此輪未驗 |
| 字幕與輸出 | 中文＋空白目錄；QA 無 hard failures；1920×1080、有音訊、超過五秒；繁體字形可見 | 原生渲染待驗 |
| 安裝／重跑 | 完整副本註冊，無 symlink；相同版本重跑核對並重新驗證 | 保留既有連結流程 |
| Codex CLI 技能發現 | 29/29 工作區技能精確路徑匹配，無模型請求 | 本輪未原生實測 |

### 發布前必跑矩陣

1. Windows 11 x64 標準帳號：空工作區安裝、重跑、未知同名技能拒絕、修改 helper／工具後拒絕、中文與空白路徑渲染、來源與副本 hash 一致。
2. Windows 具 symlink 權限帳號：Google 的兩個 symlink 防護案例必須實際執行，不能 skipped；確認工作區外檔案不被修改。
3. macOS 14+ Apple Silicon：重新執行 Google wrapper／9 tests；依原 pin 安裝 Video-Use，並用 `prepare_source.py` 準備補丁副本跑 98 tests、OpenCC CLI、MPS 選擇、實際字幕渲染及技能發現。
4. 兩平台另行核准模型下載後：固定 Qwen／ForcedAligner／CKIP revision、離線重跑、詞級時間、詞界保護、真實授權影片及人工觀看／聆聽。
5. Windows ARM64、Intel Mac、CUDA 不由這次結果推定支援；若加入，另建依賴 lock 與實機矩陣。

本次修復聚焦 Google 與 AI 剪片。下列原始表所列社群媒體、官網等其他包的 Windows 問題並未因這兩包通過而自動解除；整個 Toolbox 仍不能宣稱已完成所有 Windows 工作流驗收。

## 目標與本次範圍

確認一般使用者在 **Windows 原生 PowerShell、一般帳號** 下，可以取得固定來源、安裝技能、由 Agent 發現，並完成各技能包宣告的本機流程。Windows、WSL、Git Bash 與 macOS 的結果分開記錄。

本次已執行來源取得、六包靜態驗證、五包既有 Python 測試、Learn-GAS 上游驗證、四包實際安裝與重跑，以及 Codex CLI 技能發現。登入、OAuth、平台發布、部署、真實秘密庫、模型下載與真人影片驗收留在後續階段。本文件是測試計畫，不是 Windows 正式支援宣告。

安裝範圍採目前工作區的 `.agents/skills`，registration 為 `agents_workspace`；狀態與第三方來源放在工作區 `.local/ai-workflow-toolbox`，位於技能掃描目錄外。實際絕對路徑與原始日誌只保存於本機報告，不寫入公開文件。

## 基準環境

| 項目 | 本次實測 |
|---|---|
| OS | Windows 11 Home 25H2，build 26200.9168，x64 |
| 記憶體／可用磁碟 | 約 15.8 GiB／290.7 GiB（預檢時） |
| Shell | PowerShell 7.6.5 |
| Python | 3.14.2；`python`、`python3` 均可解析；`py` launcher 可用 |
| Node.js／npm | 22.18.0／10.9.3 |
| Git | 2.50.1.windows.1；系統 `core.autocrlf=true` |
| Codex CLI | 0.153.4 |
| symlink 建立 | 一般帳號回傳 WinError 1314；未修改系統權限 |
| 額外 Python 套件 | 本次 Python 沒有 Pillow、tzdata；uv、Graphify、NotebookLM 未安裝 |
| 測試環境變數 | `PYTHONUTF8=1`、`PYTHONDONTWRITEBYTECODE=1`；未啟用兩個實機 acceptance opt-in |

第三方 clone 使用 repository 層級 `core.autocrlf=false` 保留來源位元組；未更改系統或使用者的 Git 預設。

## 來源與安裝結果

| 技能包 | 固定候選／來源 | 目前結果 |
|---|---|---|
| AI 知識庫 | 核心 0.1.0 | 五技能安裝、重跑及 CLI 發現通過；工作區初始化與選配 provider 未執行 |
| 社群媒體 | 0.7.0 | 七技能安裝、重跑及 CLI 發現通過；功能回歸仍有 Windows 缺口 |
| 官網打造 | 0.5.0 | 五技能安裝、重跑及 CLI 發現通過；安裝位置的範本定位失敗，尚不可視為完整可用 |
| Agent 盤點 | wrapper 0.1.0；上游 v0.2.1 | 六技能安裝、重跑及 CLI 發現通過；已設定 repoRoot，未掃描實際規則 |
| Google 自動化 | wrapper 0.1.0；固定 Learn-GAS | 來源已取得，commit／tree／LICENSE 驗證通過；上游必要測試失敗，依 INSTALL 停在技能註冊前 |
| AI 剪片 | Raven Video-Use v0.1.1 | 安裝前即因 macOS ARM64 契約停止；未安裝 runtime、技能或模型 |

固定第三方來源：

- Learn-GAS：commit `7d50a7bfcfbe41ea9d88c2aef8f11200871433a3`，tree `ef6e45626d59ae18745eb5c7245de0b3f2e48cc9`，MIT，LICENSE SHA-256 `39106e322b00c852430a6e6fca5f93b1465b24a6abd8a6d723df99ae9d2eaa15`。
- agent-inventory：tag `v0.2.1`，commit `c162b0adce4d1519b60f76de15bc00df85d611ce`，tree `9ccdd73635bb74b95e6d2a111c994758602f5a23`，MIT，LICENSE SHA-256 `8e30b10020d068a10bf4376e97df27bf34c9a52b01de5c3d0f6e26f594353dac`。

## 已執行的基準測試

六個 Toolbox 靜態驗證器全部 exit 0。Learn-GAS 的 `validate_skills.py` exit 1：內含的課程進度 symlink 測試因權限不足失敗。

| 原始測試套件 | testsRun | failures | errors | skipped | 結果 |
|---|---:|---:|---:|---:|---|
| AI 知識庫 | 24 | 0 | 1 | 0 | 未通過：symlink 權限 |
| Google 自動化 | 6 | 0 | 1 | 0 | 未通過：symlink 權限 |
| 社群媒體 | 382 | 5 | 69 | 17 | 未通過：路徑、時區、權限與測試前置條件 |
| 官網打造 | 43 | 2 | 3 | 1 | 未通過：Windows 程序啟動與 symlink 權限 |
| Agent 盤點 | 9 | 0 | 0 | 0 | 通過 |
| Learn-GAS 上游 | 43 | 0 | 1 | 0 | 未通過：symlink 權限 |

合計執行 507 個測試。數字依 unittest 原始摘要；errors 可能包含同一方法的多個 subTest，**不可用 testsRun 減去 errors 推算通過方法數**。社群 17 個 skip 是缺少既有 Pillow 的 15 個案例、一個已正確偵測權限的 symlink 案例與 macOS 原生憑證案例；官網 1 個 skip 是未啟用 Node 真實建置。

四包實際安裝共 23 技能，同版本重跑均為 `noop`。`codex debug prompt-input` 以技能根目錄 alias 還原實際來源，再逐項核對名稱與 SKILL.md 路徑，23/23 可發現；未送模型請求。這項證據不代替 Codex 桌面 UI 或技能行為測試。

## 優先缺口與重現方式

P0：阻擋安裝或主要本機流程；P1：阻擋可靠驗收或特定能力；P2：文件／擴充環境一致性。

| ID | 優先 | 已觀察問題與影響 | 修正後通過標準 |
|---|---|---|---|
| WIN-01 | P0（剪片包） | [剪片 INSTALL](../skill-packs/ai-video/INSTALL.md) 要求 macOS 14+、arm64、Homebrew；manifest 的 uv／CPython 資產為 apple-darwin | Windows x64 使用獨立且鎖定雜湊的 runtime／FFmpeg／OpenCC 來源；能力未完成前維持 Windows 不可安裝 |
| WIN-02 | P0 | [publish_job.py](../skill-packs/social-media/skills/social-content-publishing/scripts/publish_job.py) 第 280 行將 `str(relative_to(...))` 傳回拒絕反斜線的 `local()`，正常 Windows 工作流出現 `path_invalid`；其他 coordinator 亦有相同序列化模式 | 所有持久化相對路徑使用一致格式；發布、留言、私訊、成效的虛構完整流程在 Windows 通過；仍拒絕跳脫路徑 |
| WIN-03 | P0（成效功能） | [performance_review.py](../skill-packs/social-media/skills/social-performance-analysis/scripts/performance_review.py) 呼叫 ZoneInfo；此 Python 缺少 IANA tzdata，連 UTC 都出現 ZoneInfoNotFoundError | manifest／環境契約宣告並鎖定 Windows 時區資料依賴；UTC、Asia/Taipei、America/New_York 與 DST 邊界通過 |
| WIN-04 | P0（安裝後官網） | [scaffold_site.py](../skill-packs/website-building/skills/website-build/scripts/scaffold_site.py)、[style_gallery.py](../skill-packs/website-building/skills/website-design-preview/scripts/style_gallery.py) 沿父目錄找 template；安裝器只複製技能，安裝後解析到 `.agents/template` | 從已安裝技能及另一個 cwd，可列出六主題、產生畫廊、scaffold；不仰賴維護者目錄布局 |
| WIN-05 | P1（Google 安裝前置阻擋） | Learn-GAS 與多包測試只判斷有無 `os.symlink`，沒有偵測建立權限，出現 WinError 1314 | 一般帳號的非 symlink 案例正常跑；無能力案例明確 skip／blocked；另在具 symlink 能力的受控 Windows runner 跑完拒絕連結測試，不能以 skip 宣稱通過 |
| WIN-06 | P1 | 官網部署測試將帶 shebang 的假 Python 檔當成原生 executable，WinError 193；正式程式直接呼叫 `npx`，並以 POSIX 名稱篩選環境變數 | 假 CLI 使用 Windows 可執行方式；實際 npx/npm.cmd 啟動、空白路徑與必要 Windows 環境可用；兩類證據分開 |
| WIN-07 | P1 | 社群測試假定 `st_mode & 0o777 == 0o600`，以及在 `str(Path)` 中尋找 `/`，Windows 斷言失敗 | 路徑斷言比較 Path 或 as_posix；資料存取控制以 Windows ACL 驗證，不能只移除 Unix 斷言後宣稱隱私通過 |
| WIN-08 | P1 | 社群圖片測試缺少 Pillow 而略過；manifest 目前明列 Pillow 新安裝契約 `installable=false` | 維持圖片能力未驗收；補齊固定版本、授權與安裝契約後，在新環境確認繁中字形、溢位與輸出尺寸 |
| WIN-09 | P2 | 官網 package.json 宣告 Node >=20，但 lockfile 的 Astro 6.0.8 要求 >=22.12，Wrangler 要求 >=22；本機 22.18 符合 | 安裝預檢依實際依賴引擎要求停止過舊 Node，文件一致 |
| WIN-10 | P2 | 上游技能仍含 Bash 的 `$(...)`、`[ -z ]`、`$REPO`；測試大量硬寫 python3，其他 Windows 安裝未必提供此名稱 | PowerShell 範例及 sys.executable 路徑一致；從乾淨 Windows shell 執行，不借用 WSL 結果 |

WIN-03 的依賴判斷符合 [Python zoneinfo 官方資料來源說明](https://docs.python.org/3/library/zoneinfo.html#data-sources)：Windows 等環境可能沒有 IANA 資料庫，跨平台專案應宣告 tzdata。symlink 前置條件參照 [Python os.symlink](https://docs.python.org/3/library/os.html#os.symlink)。

WIN-04 已做對照：來源版 `style_gallery.py list` exit 0、六主題；安裝版 exit 2、沒有主題。安裝版 scaffold `plan` 的預設範本 exit 2；明確加 `--template <toolbox>/skill-packs/website-building/template` 後 exit 0。這只確認 scaffold 計畫的暫行解法，未解決畫廊、未建置網站。

## 分階段執行

### T0：固定來源與環境預檢（本次已完成基準）

- 記錄 commit、OS／架構、shell、Python 實際路徑、Node／npm、Git、Agent 版本、磁碟空間。
- 檢查全部 manifest 的 installable、平台、固定 ref、授權與 checksum；任何不符停在下載或寫入之前。
- 檢查 Agent 目錄衝突，狀態／來源不在技能掃描目錄內。
- 比較 Git autocrlf 開關下的 checkout 與 LICENSE 位元組；固定來源雜湊不能因行尾轉換誤報。

通過條件：可重現環境與來源；不同平台的資產不會被安裝到 Windows。

### T1：先修復 Windows 核心缺口

建議順序：WIN-02 路徑 → WIN-03 時區依賴 → WIN-04 範本定位 → WIN-05／06／07 測試與程序啟動。剪片 WIN-01 視為獨立移植工作，可與其他技能包的驗收分開排程。

每次修正只重跑對應失敗案例，再跑該包既有 validator 與整包回歸。保留原始失敗日誌；修正環境與來源後用新的 run ID，不覆蓋本次 baseline。跨包修正完成後重跑全部本機測試。

### T2：安裝生命週期與檔案系統

| ID | 測試步驟 | 預期結果 |
|---|---|---|
| INS-01 | 新空目錄安裝各包，再執行 status | 技能數量正確、雜湊相符、來源完整、無非預期寫入 |
| INS-02 | 同版本重跑；前後比對檔案 hash／mtime | noop，內容與既有檔案不重寫 |
| INS-03 | 在隔離目錄放未知同名檔案／目錄、人工改過的技能、缺檔狀態 | 明確停止；原檔原樣保留 |
| INS-04 | 隔離候選更新 → rollback → remove → reinstall | 可回復狀態一致；移除只進 quarantine，私人工作資料保留 |
| INS-05 | 注入複製中斷、狀態寫入失敗、檔案被另一程序持有 | 交易回復或可辨識未完成狀態；重跑不留下半套技能 |
| INS-06 | 中文、空白、不同磁碟、長路徑、磁碟大小寫；另測 UNC／OneDrive | 支援的情境正常；不支援的情境在寫入前清楚停止 |
| INS-07 | symlink、junction、reparse point、父目錄連結、路徑跳脫 | 不跟隨至測試工作區外；有／無權限的 runner 分別留下證據 |
| INS-08 | 關閉 Agent，再開新程序讀 status；來源移動／消失 | 可回復或清楚報告來源失聯；不靜默改用其他版本 |

INS-03～08 一律只在新建的虛構暫存工作區操作，不移除實際已安裝的技能。移動／清理測試目錄前驗證完整目標仍在該次測試根目錄內。

### T3：已安裝技能與 Agent 行為

- 從 Toolbox repository 外的專案執行；核對每個技能的名稱、描述與實際入口，不能只確認來源目錄有 SKILL.md。
- Codex CLI 已有 23/23 列舉證據；補 Codex Desktop 技能選擇器與真實觸發測試。
- Google 包解除上游測試阻擋並註冊後，預期總數變為 28；剪片另有獨立平台門檻。
- Claude Code、Antigravity Desktop、Antigravity CLI 各自安裝與驗證，不能共用「已通過」標記。未測用戶端維持 not_run。
- 逐技能用虛構需求確認選路、相鄰 reference／script／template 可讀、一次訪談、預覽綁定與外部操作停止點。
- 工作區安裝必須只在目標工作區可見；使用者層級安裝另用乾淨測試 profile，不覆寫本機既有技能。

### T4：各包本機端到端流程

| 技能包 | 虛構案例與成功標準 |
|---|---|
| AI 知識庫 | 空白工作區 merge-missing 初始化、重跑、保留既有筆記；書摘追加、來源引用、Socratic 討論；缺 provider 時仍使用本機資料且明示限制。Graphify 0.9.35 與 notebooklm-py 0.8.0 另在固定版本隔離環境驗證安裝、版本與專案技能，未登入時只測本機層。 |
| Google 自動化 | Learn-GAS 43 項測試；教學範本實體化、課程進度保存、Webhook 虛構測試；五種 router 使用者故事正確分流。離線階段不能觸發 clasp push 或 Cloud 資源建立。 |
| 社群媒體 | 七技能按設定 → 規劃 → 撰寫 → 圖片 → 發布 → 互動 → 成效串接。虛構 adapter 驗證預覽雜湊、跨平台去重、claim、讀回中斷恢復、unknown 不重送；週／月／季／年、UTC／臺北／DST、真正零與資料缺失分離。圖片補依賴後驗證繁中、溢位、hash、尺寸。 |
| 官網打造 | 從已安裝的入口設定、文案、六主題畫廊、scaffold → npm ci → build → check_site；每主題 375／768／1440 寬度驗證首頁、服務、文章列表／內頁、聯絡、404、手機選單、reduced motion、內部連結與 noindex。 |
| Agent 盤點 | AGENT_INVENTORY_CONFIG 指向虛構設定、只掃測試 fixture；六工具 adapter、去重、摘要／流程圖 JSON、127.0.0.1 網頁與離線 editor fallback。Windows 開啟檔案與回收桶行為只用虛構檔案測，安裝階段不掃真實使用者資料。 |
| AI 剪片 | Windows manifest／runtime 就緒後，先無模型的 helper／FFmpeg subtitles filter／OpenCC／色塊音調 smoke；再按固定 revision 下載模型，驗證 CPU／可用 GPU、轉錄、對齊、繁中斷詞、字幕燒錄、橫直版輸出與中斷恢復。最後以合法素材做人工觀看與聆聽。 |

### T5：外部實機與最終驗收

本機 P0 缺口解除後，按每個測試案例的具體目標、帳號、權限、內容與讀回方式安排登入／外部操作。所有外部寫入的核准都以可預覽的實際內容為單位。

- 社群直接延用 [集中實機驗收手冊](../skill-packs/social-media/docs/live-acceptance-runbook.md) 與其結果範本：工具、Windows Credential Manager、OAuth、唯讀、發布、互動與成效逐層記錄。原生秘密庫只用一次性虛構秘密開始，包含跨程序讀回及指定測試項目的清理。
- Google 使用專用測試專案與資源；同步、實際執行、結果讀回各自留證據。寄信／排程不隨其他測試自動執行。
- 官網在測試 Worker 驗證登入、workers.dev 部署、讀回與回復；自訂網域、公開收錄與購買分開安排。
- Notebook 由使用者登入，再驗證 auth check --test 與遠端資料讀取；不保存登入狀態內容到報告。
- 剪片記錄輸出規格及真人驗收結果；模型容量、授權與硬體需求按 Windows 契約事先明列。

### T6：第二套乾淨 Windows 環境

最低必要矩陣：

| 軸 | 必測 | 擴充／條件測 |
|---|---|---|
| OS | 本機 Windows 11 x64、另一乾淨 Windows 11 x64 | Windows ARM64／WSL 僅在宣告支援時另測 |
| 權限 | 一般帳號，不要求管理員即可安裝複製型技能 | 具 symlink 能力的受控 runner 測連結防護 |
| Shell | Windows PowerShell 5.1、PowerShell 7 | Git Bash 另列，不代替 PowerShell |
| Python | 最低宣告版本 3.11 與本機 3.14 | 剪片依 Windows lock 的指定版本獨立測 |
| Node | lockfile 所需最低可用版本與本機 22.18 | 新的受支援版本依相容性策略增加 |
| 位置 | ASCII、中文＋空白、與來源不同 cwd | 長路徑、不同磁碟、UNC、OneDrive |
| 網路 | 線上首次取得、離線重跑 | 中斷下載、錯誤 checksum、proxy／憑證環境 |
| 用戶端 | Codex CLI＋Desktop | 宣告支援的 Claude／Antigravity 各自驗收 |

## 可重現命令

以下在 Toolbox 根目錄執行；PowerShell 使用陣列與獨立參數，不使用 Bash heredoc、反斜線換行或 `export`。選定 Python 後，子程序也應使用同一個 interpreter；本次原始測試仍硬寫 python3，已記錄此差異。

```powershell
$pythonExe = (Get-Command python).Source
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'

& $pythonExe skill-packs/ai-knowledge-base/tests/validate_repository.py
& $pythonExe skill-packs/ai-video/tests/validate_package.py
& $pythonExe skill-packs/google-automation/tests/validate_package.py
& $pythonExe skill-packs/social-media/tests/validate_package.py
& $pythonExe skill-packs/website-building/tests/validate_package.py
& $pythonExe skill-packs/agent-inventory/tests/validate_package.py

$packs = @('ai-knowledge-base', 'google-automation', 'social-media', 'website-building', 'agent-inventory')
foreach ($pack in $packs) {
    & $pythonExe -m unittest discover -s "skill-packs/$pack/tests" -p 'test_*.py' -v
    # 每個 exit code 都要保存；不可把迴圈最後一個 exit 0 當作全部成功。
    Write-Output "$pack exit_code=$LASTEXITCODE"
}

# 在實際安裝工作區執行；只列舉，不呼叫模型。
codex debug prompt-input 'Windows skill discovery check'
```

有 Learn-GAS clone 時，Google validator 應另加 `--learn-gas-source <固定來源路徑>`，並在該來源執行 `python scripts/validate_skills.py` 與 `python -m unittest discover -s skills/google-apps-script-teaching/scripts -p 'test_*.py' -v`。

命令輸出可能包含本機路徑；原始紀錄只保留本機，分享前去識別化。現有 baseline runner 位於本次工作區 `.local/ai-workflow-toolbox/run_baseline.py`，可用 `static` 或 `unit` 群組重跑；先將舊 reports 另存新 run ID，避免覆蓋證據。

## 結果格式與完成門檻

每例至少記錄：test_id、run_id、來源 commit、OS／shell／interpreter、前置條件、精確命令、預期、實際、exit code、狀態、證據路徑、缺口 ID。外部案例另記核准範圍與讀回證據；秘密值不進入任何報告。

狀態使用 `passed`、`failed`、`blocked`、`not_run`、`skipped`。未執行、因依賴缺件略過、只做結構檢查都不能記為功能通過。

Windows 候選驗收完成須同時滿足：

1. 所宣告支援的包沒有未處理的 P0；其他包在支援矩陣明確排除並安全拒絕安裝。
2. 一般帳號可乾淨安裝、重跑、更新、回復，且不碰既有使用者資料。
3. 從安裝目錄與來源目錄外完成技能發現及端到端流程；不依賴維護者路徑。
4. 所有必要測試通過；環境能力造成的 skip 必須在對應 runner 補足，不能當成通過。
5. 至少另一套乾淨 Windows 環境重現，外部功能具有獨立的登入、執行、讀回與人工驗收證據。
6. 更新 Windows 安裝文件、依賴 manifest 與相容性紀錄後，才由維護者決定支援／發行狀態。
