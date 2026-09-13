# Google 工具自動化安裝

本套件是**可安裝的外部驗收候選版**，不是正式支援版本。`install.manifest.toml` 的 `status = "ready_for_external_acceptance"` 與 `installable = true` 只代表 A～C 的 Agent 端門檻已通過；仍須完成 D 節外部實機驗收。

安裝流程預期由具備本機檔案與終端機能力的 AI Agent 執行。使用者只需選擇工作區或使用者層級；不需要自行複製技能、判斷 Learn-GAS 版本或操作終端機。

## Agent 必須遵守的界線

- 安裝只處理本機技能入口與不含秘密的狀態檔，不登入 Google、不執行 OAuth、不建立 Cloud Project、不啟用 API、不部署，也不執行 `clasp push`。
- 取得公開 repository、建立技能入口或修改現有入口前，先顯示來源、固定版本、目標路徑、變更與回復方式，再取得使用者同意。
- 不把 Token、Cookie、OAuth client secret、`.clasprc.json`、`.clasp.json`、Script ID、Cloud Project ID、帳號或真實 Google 資源網址放進技能目錄、狀態檔或安裝報告。
- 未知檔案、實體目錄、symlink、人工修改、來源或雜湊不符時停止；不自動覆寫。
- 不追蹤 Learn-GAS `main`，只安裝 manifest 的完整 commit。

## 1. 唯讀預檢

Agent 先讀本文件、`install.manifest.toml`、`THIRD_PARTY_NOTICES.md` 與 [`docs/compatibility.md`](docs/compatibility.md)，再確認：

1. Python 3.11 以上與 Git 可用。
2. 目標是工作區或使用者層級；工作區通常較容易隔離與回復。
3. 實際技能根目錄、狀態目錄與 Learn-GAS 下載位置。
4. 六個受管理入口是否不存在、與本版相同、屬舊版受管理內容，或存在未知衝突。
5. 狀態目錄位於所有 Agent 技能掃描目錄之外。

目前官方路徑如下：

| 註冊 ID | 用戶端 | 技能根目錄 |
|---|---|---|
| `agents_workspace` | Codex＋Antigravity 共用工作區入口 | `<workspace>/.agents/skills` |
| `claude_workspace` | Claude Code 工作區入口 | `<workspace>/.claude/skills` |
| `codex_user` | Codex 使用者入口 | `$HOME/.agents/skills` |
| `claude_user` | Claude Code 使用者入口 | `$HOME/.claude/skills` |
| `antigravity_user` | Antigravity 使用者入口 | `$HOME/.gemini/config/skills` |

Codex 與 Antigravity 在同一工作區共用 `agents_workspace`，不要重複安裝。不得使用舊的 `$HOME/.codex/skills`。路徑來源見 [Codex](https://learn.chatgpt.com/docs/build-skills)、[Claude Code](https://code.claude.com/docs/en/slash-commands) 與 [Antigravity](https://antigravity.google/docs/skills) 官方文件。

## 2. 顯示計畫並取得同意

安裝計畫必須列出：

- Toolbox 候選版本與 `google-workflow-router` 來源。
- Learn-GAS repository、完整 commit、Git tree、MIT License 與下載位置。
- 每個要建立的技能入口與狀態目錄。
- 網路下載、磁碟寫入、未知衝突時的停止方式。
- 更新前備份、回復與可復原移除方式。

這項同意只涵蓋本機取得與技能註冊，不包含 Google 登入、OAuth、`clasp push`、Google Cloud 或部署。

## 3. 取得並驗證 Learn-GAS

使用新的空白目錄取得公開 repository，切到 manifest 固定 commit。不要在現有不明目錄直接切 branch 或清除內容。

驗證結果必須同時符合：

```text
commit          7d50a7bfcfbe41ea9d88c2aef8f11200871433a3
tree            ef6e45626d59ae18745eb5c7245de0b3f2e48cc9
LICENSE SHA-256 39106e322b00c852430a6e6fca5f93b1465b24a6abd8a6d723df99ae9d2eaa15
Git 狀態        無修改、無未追蹤檔案
```

再從 Toolbox 根目錄執行（Windows 與 macOS 使用同一驗證入口）：

```bash
python skill-packs/google-automation/scripts/validate_upstream.py --learn-gas-source <learn-gas-source>
```

任何一步失敗就停止。不得因公開 `main` 有新 commit 而自動改用新版。

驗證器先核對原始 commit、tree、LICENSE 與乾淨狀態，再於暫存副本執行原上游驗證器和 43 項測試。唯一調整是 symlink 測試建立連結時若得到 Windows `WinError 1314`，回報明確的 `skipped`；其他錯誤仍失敗。macOS 與具備權限的 Windows 會實際執行同一項防護測試。安裝仍複製未修改的固定來源，不需要管理員、Developer Mode 或 symlink 權限。

Windows PowerShell 使用 `python` 與單行參數，或 PowerShell 反引號續行；不要直接貼上後續 Bash 範例的反斜線續行。clone 時使用 repository 專屬 `-c core.autocrlf=false`，避免 Git 在 checkout 改變鎖定檔案的位元組；不修改全域 Git 設定。

## 4. 註冊技能

以下範例由 Agent 代入已核對的絕對路徑；使用者不需要自行執行。`<toolbox-google-pack>` 是本目錄，`<learn-gas-source>` 是通過前一步的乾淨 clone。

```bash
python3 <toolbox-google-pack>/scripts/manage_install.py install \
  --manifest <toolbox-google-pack>/install.manifest.toml \
  --registration agents_workspace \
  --client-root <workspace>/.agents/skills \
  --state-root <state-root> \
  --learn-gas-source <learn-gas-source>
```

Claude Code 工作區使用 `claude_workspace` 與 `<workspace>/.claude/skills`。若使用者明確選擇使用者層級，再使用對應的 `codex_user`、`claude_user` 或 `antigravity_user`。

管理器會：

1. 再次驗證 manifest、Learn-GAS commit、tree、LICENSE 與乾淨 Git 狀態。
2. 驗證註冊 ID 與目標根目錄的 basename 結構。
3. 計算一個 Toolbox 路由技能、四個 Learn-GAS 技能及共用術語檔的內容雜湊。
4. 目標全空時建立入口；全部相同時安全重跑；只要有未知或人工修改內容就停止。
5. 只在技能掃描目錄外保存路徑、版本、雜湊、備份與驗證狀態。

## 5. 本機驗證

Agent 至少執行：

```bash
python3 <toolbox-google-pack>/tests/validate_package.py \
  --learn-gas-source <learn-gas-source>
python3 -m unittest \
  <toolbox-google-pack>/tests/test_install_lifecycle.py -v
```

再於新的暫存工作區使用安裝管理器建立 `agents_workspace` 與 `claude_workspace` 入口，驗證：

- 五個 `SKILL.md` 可讀，共用術語與路由參考檔完整。
- Codex、Claude Code 與 Antigravity 依目前官方路徑發現技能；用戶端未登入或沒有本機列舉介面時，分開標示「結構通過」與「實際發現待外部驗收」。
- 不發送模型請求、不建立登入工作階段，也不變更真實使用者全域技能。

## 6. 重複安裝、更新、回復與移除

### 重複安裝

對相同來源重跑 `install`。來源與目標雜湊都相同時應回報 `noop`，不重寫檔案。

### 更新

只有 manifest 已由維護者更新並通過相同測試時，才對新的乾淨來源執行：

```bash
python3 <toolbox-google-pack>/scripts/manage_install.py update \
  --manifest <new-toolbox-google-pack>/install.manifest.toml \
  --registration <same-registration> \
  --client-root <same-client-root> \
  --state-root <same-state-root> \
  --learn-gas-source <new-learn-gas-source>
```

管理器先保存目前六個入口，再以已驗證的新來源替換。未知修改時停止，舊內容不動。

### 回復

```bash
python3 <toolbox-google-pack>/scripts/manage_install.py rollback \
  --registration <same-registration> \
  --client-root <same-client-root> \
  --state-root <same-state-root>
```

只還原最近一個雜湊相符的歷史版本。Google 專案、OAuth、Cloud 資源與使用者工作目錄不會跟著改動。

### 移除

```bash
python3 <toolbox-google-pack>/scripts/manage_install.py remove \
  --registration <same-registration> \
  --client-root <same-client-root> \
  --state-root <same-state-root>
```

只有目前六個入口仍與狀態雜湊相符時，管理器才把它們移到狀態目錄的隔離區。Learn-GAS clone、Toolbox、使用者 Apps Script 專案與所有 Google 資源都保留；刪除這些其他位置必須另外指定精確目標與取得同意。

## 7. 完成狀態

安裝報告只記錄版本、路徑、雜湊、建立入口、測試與未完成項目。技能出現在清單中不等於 Google 已登入、OAuth 已授權或任何遠端部署成功。

Agent 端 A～C 門檻完成後，只能回報「可安裝的外部驗收候選版」。使用者完成 [`tests/acceptance-checklist.md`](tests/acceptance-checklist.md) D 節前，不得宣稱正式支援。
