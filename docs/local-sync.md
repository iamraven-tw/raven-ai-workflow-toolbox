# 本機共用套件同步

公開 repository 不保存維護者的實際工作區路徑。需要同時維護獨立專案、Toolbox 發行副本與私人實際案例時，使用忽略的 `.local/sync-manifest.toml` 描述關係。

## 三種角色

- **canonical**：通用核心的主要來源。
- **mirror**：Toolbox 內可獨立下載的完整發行副本。
- **runtime consumer**：實際使用的私人工作區，只透過本機 symlink 使用通用技能，並保留自己的資料與個案設定。

## 安全規則

- `status`、`plan` 與 `verify` 只讀，不修改檔案。
- `record` 只有兩邊完全一致時才建立本機基準。
- `sync` 預設只顯示預覽；必須加上 `--apply` 才會寫入。
- `runtime-link` 預設只預覽技能入口；必須加上 `--apply` 才會建立或替換 symlink。
- 寫入前備份所有將被覆寫或刪除的目標檔案。
- 兩邊都在上次基準後修改且內容不同時回報 `conflict`，不自動選邊。
- manifest 的 `exclude_roots` 必須排除實際資料、秘密、登入狀態與工具暫存。
- 同步只改本機檔案，不自動 commit、push 或發布。

## 指令

先從 `config/sync-manifest.example.toml` 建立不進 Git 的本機 manifest。

```bash
python3 tools/knowledge_base_sync.py \
  --manifest .local/sync-manifest.toml status

python3 tools/knowledge_base_sync.py \
  --manifest .local/sync-manifest.toml plan

python3 tools/knowledge_base_sync.py \
  --manifest .local/sync-manifest.toml verify

python3 tools/knowledge_base_sync.py \
  --manifest .local/sync-manifest.toml record
```

啟用 manifest 的 `[runtime]` 後，先預覽技能農場。共用技能會指向 canonical；`local_skills_dir` 中其他含 `SKILL.md` 的技能仍指向私人工作區原本的技能資料夾：

```bash
python3 tools/knowledge_base_sync.py \
  --manifest .local/sync-manifest.toml runtime-link

python3 tools/knowledge_base_sync.py \
  --manifest .local/sync-manifest.toml runtime-link --apply
```

工具只管理 runtime 技能農場與 `client_links`；不會刪除或改寫 `local_skills_dir` 中的原始技能。若預定位置已有實體檔案或目錄，工具會停止，不會覆寫。

只有人工或 AI 已確認正確方向時才同步：

```bash
python3 tools/knowledge_base_sync.py \
  --manifest .local/sync-manifest.toml \
  sync --from canonical

python3 tools/knowledge_base_sync.py \
  --manifest .local/sync-manifest.toml \
  sync --from canonical --apply
```

從 mirror 回饋 canonical 時同理使用 `--from mirror`。完成後必須重新執行套件驗證、技能驗證與 `verify`，再由維護者決定如何建立本機 Git commit。

## AI 修改規則

AI 從 canonical、mirror 或 runtime consumer 任一位置開始工作時：

1. 先讀專案規則。
2. 發現 `.local/sync-manifest.toml` 後讀取角色與排除範圍。
3. 共用能力優先修改 canonical；若已在 mirror 發生修改，先檢查狀態再回饋 canonical。
4. runtime consumer 的個案設定與實際資料只留在私人工作區。
5. runtime 新增或移除私人技能後重新執行 `runtime-link --apply`，讓三種用戶端看到相同技能清單。
6. 完成前執行 `verify`，不得把「只改了一邊」宣稱為完成。
