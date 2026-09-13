# 教學程式模板

這個目錄保存已完成工程測試與使用者 UI 驗收的 Apps Script 教材程式。教學開始時，Agent 應直接取用這些模板，不得依教案重新生成同一套業務程式。

## 目錄

- `catalog.json`：模板狀態、來源版本與應包含的檔案。
- `beginner/`：第一階段五個生活應用的完整已驗收程式。
- `activity-registration/`：第二階段「活動報名與通知系統」逐課累積快照。

第一階段模板只包含可公開重用的 `.claspignore`、`.gs` 與 `appsscript.json`。不包含 `.clasp.json`、OAuth 憑證、Script Properties 實際值、私人網址或 Google 資源 ID。

## 使用方式

由 Agent 在 Toolbox 的 `skill-packs/google-automation/` 目錄執行：

```bash
python3 skills/google-apps-script-teaching/scripts/materialize_template.py \
  --template beginner/expense-tracker \
  --destination /絕對路徑/GoogleAppsScript/expense-tracker
```

工具只複製登錄在 `catalog.json` 的程式檔。若目的地已有內容相同的檔案會安全略過；若同一路徑已有不同內容則停止，不會覆寫。

第二階段第 1 課也使用上面的一般複製。第 2 至第 8 課不得把下一課完整快照直接蓋到學生專案，而要指定相鄰前課：

```bash
python3 skills/google-apps-script-teaching/scripts/materialize_template.py \
  --upgrade-from activity-registration/lesson-01 \
  --template activity-registration/lesson-02 \
  --destination /絕對路徑/GoogleAppsScript/activity-registration
```

這是受控升級：工具會先確認 `.claspignore` 與 `src/` 完整符合前課已驗收快照，全部通過後才更新有變動的檔案並加入下一課檔案。檔案遭修改、缺少、`src/` 有快照外檔案、目標未驗收或課次不相鄰時，會在任何寫入前停止，不會猜測合併、刪除學員內容或跳課。同一個已完成的升級命令重跑時只會安全略過。

課程進度不附著在任一案例模板。學員第一次選擇第一或第二階段時，Agent 另外在 `GoogleAppsScript/learn-gas-course` 執行 `scripts/update_course_progress.py --select-phase`，自動建立或讀取涵蓋兩階段的統一進度。第一階段五個專案彼此獨立，由學員自由選擇；第二階段八課則共用累積專案並依序完成。統一進度可避免五個獨立專案各自產生互相矛盾的進度檔。

例如選擇第一階段時，由 Agent 執行：

```bash
python3 skills/google-apps-script-teaching/scripts/update_course_progress.py \
  --destination /絕對路徑/GoogleAppsScript/learn-gas-course \
  --select-phase 1
```

選擇第二階段時改用 `--select-phase 2`。這些都是本機進度操作，不會建立或修改任何 Google 遠端資源。

若 Agent 已經取得遠端建立確認，並由 `clasp create` 產生全新的空白 `src/Code.gs` 與初始 `src/appsscript.json`，可在先用 `--dry-run` 核對後增加：

```bash
--replace-clasp-bootstrap
```

這個選項只接受可辨識的空白 `myFunction()`、沒有進階服務或額外設定的初始 manifest，而且 `src/` 不能有其他程式。條件不符就停止，不會把既有專案誤當成空白專案。

模板只準備本機程式。建立遠端 Google 檔案、`clasp push`、觸發器、部署與 GitHub 發布仍需依個別確認規則處理。

## 維護規則

1. 已有 `validated` 模板時，教學專案必須先取用模板，再執行本機與遠端驗收；不得重新撰寫同名案例。
2. 修正模板時，先在獨立學生專案完成回歸與 UI 驗收，再更新模板、來源 commit 與驗證器。
3. 第二階段每課完成全部驗收後，將當時完整的累積 `src/` 快照收錄為 `activity-registration/lesson-XX`；一般學習流程從第 1 課開始，再以受控升級依序套用至目前課次，不直接跳到較後快照。
4. `pending` 代表尚未完成真實驗收，不能當成可發放模板，也不能用草稿程式冒充。
5. 統一課程進度由選階段流程首次建立、受控進度工具持續更新；測試必須涵蓋開始前自由選擇、第一階段案例可不按編號選取、第二階段順序鎖定、中斷恢復、首次建立、相同狀態重跑與私人資料拒絕。
6. 模板工具的回歸測試必須實際完成第二階段第 1 至第 8 課連續升級，並涵蓋安全重跑、學員修改、額外檔案、未驗收模板與跳課拒絕。
7. 原 Learn-GAS 教材保留 MIT 授權；後續新增或修改內容在公開前，仍須檢查測試題庫、範例資料與第三方參考內容的公開使用條件。
