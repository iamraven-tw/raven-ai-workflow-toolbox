# Google 工具自動化安裝

0.2.0 起，五個技能與共用術語都由本包提供。只需取得 Toolbox 的本技能包，不需要其他技能包、Git 或 Learn-GAS clone。Python 3.11 以上即可執行安裝管理器。本版為可安裝候選，尚未正式支援。

## 1. 唯讀預檢與安裝範圍

Agent 讀取本文件、`install.manifest.toml`、`THIRD_PARTY_NOTICES.md` 與 [相容性](docs/compatibility.md)，依實際用戶端判斷目的地，不依模型名稱猜測。

| 註冊 ID | 用戶端與範圍 | 技能目錄 |
|---|---|---|
| agents_workspace | Codex／Antigravity 工作區 | `<workspace>/.agents/skills` |
| claude_workspace | Claude Code 工作區 | `<workspace>/.claude/skills` |
| codex_user | Codex 全域 | `$HOME/.agents/skills` |
| claude_user | Claude Code 全域 | `$HOME/.claude/skills` |
| antigravity_user | Antigravity 桌面版全域 | `$HOME/.gemini/config/skills` |

Agent 顯示 Toolbox 版本、目標技能根目錄、技能掃描範圍之外的狀態目錄、六個入口及回復方式。確認使用者的安裝要求涵蓋此範圍後執行。一次只安裝指定用戶端，不更動 shell、Google 帳號或 Apps Script 專案。

## 2. 驗證本包來源

在本技能包目錄執行：

```bash
python3 tests/validate_package.py
python3 scripts/validate_upstream.py
```

第一項驗證 manifest、五個技能、授權、連結與 `bundle.lock.json`。第二項在暫存副本驗證原 Learn-GAS 教材及程式；Windows 只有建立 symlink 遇到 WinError 1314 時明確列為 skipped，其他錯誤仍失敗。

安裝時不得執行 `lock_bundle.py` 來消除雜湊錯誤；該工具僅供維護者修改、審查、驗證新版本時重建鎖定檔。鎖定檔驗證內容一致性，不取代可信發行來源。

## 3. 註冊技能

下列命令由 Agent 代入核對過的路徑。`<pack>` 為本技能包。

```bash
python3 <pack>/scripts/manage_install.py install --manifest <pack>/install.manifest.toml --registration agents_workspace --client-root <workspace>/.agents/skills --state-root <state-root>
```

不再傳入 `--learn-gas-source`。其他用戶端依上表選 registration 與路徑。Windows 可改用 `python`，命令使用單行。

受管理入口是 `google-workflow-router`、`google-apps-script-project-development`、`google-apps-script-teaching`、`google-apps-script-debugging`、`google-docs-layout` 與 `learner-facing-terminology.md`。四個原 Learn-GAS 技能各自攜帶完整 MIT LICENSE；共用術語亦含原授權聲明。

安裝器先驗證來源與全部目標。未知內容、symlink、人工修改或部分既有入口都會停止；全部相同可安全重跑。

## 4. 從舊版轉換

已由 Toolbox 0.1.0 管理的安裝，沿用同一 registration、client-root、state-root，改用本版 manifest：

```bash
python3 <pack>/scripts/manage_install.py update --manifest <pack>/install.manifest.toml --registration <registration> --client-root <client-root> --state-root <state-root>
```

管理器讀取原 schema 1 狀態，核對舊版六個入口，保留完整備份後更新。舊 Learn-GAS clone 即使已不存在也不影響更新或回復。歷史 ref 只供追溯，不是新版下載要求。

直接安裝 Learn-GAS、沒有 Toolbox 狀態檔時，優先在新空白工作區驗證新版，保留現有全域安裝。若要沿用原位置，Agent 先辨識四個舊技能與共用術語、展示差異和引用關係，取得該範圍更新確認後，將精確五個入口移至掃描範圍外的備份，再首次安裝。不得新建狀態檔冒認未知內容，也不得刪除整個技能根目錄。新安裝失敗時還原備份；不改學員專案或課程進度。

## 5. 更新、回復與移除

後續更新只取 Toolbox 新版本並執行 `update`。人工修改的受管理入口會停止。

```bash
python3 <pack>/scripts/manage_install.py rollback --registration <registration> --client-root <client-root> --state-root <state-root>
python3 <pack>/scripts/manage_install.py status --registration <registration> --client-root <client-root> --state-root <state-root>
python3 <pack>/scripts/manage_install.py remove --registration <registration> --client-root <client-root> --state-root <state-root>
```

`rollback` 只還原已驗證備份；`remove` 僅在使用者要求移除時執行，受管理入口保存在可復原隔離區。來源、其他技能、Apps Script、Google OAuth、使用者知識庫與課程進度均不在管理範圍。

## 6. 技能發現與完成狀態

在隔離工作區重新載入用戶端，確認五個技能實際出現在技能清單，並核對來源路徑。無法列舉、未登入或未執行模型測試時，分開回報結構驗證與實際發現待驗。

技能出現在清單中不等於 Google 已登入、OAuth 已授權或任何遠端部署成功。正常、錯誤、重跑、更新、回復與移除測試在本包 `tests/`；實機驗收見 [驗收清單](tests/acceptance-checklist.md)。
