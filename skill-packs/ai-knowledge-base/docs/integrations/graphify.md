# Graphify 整合邊界

## 角色

Graphify 是 `My Real Second Brain` 目前的預設知識結構後端。它將本地來源整理成可查詢的關係圖譜、群聚報告與互動式 HTML，協助使用者看見跨文件關係，但不取代原始文件、第一大腦心得或使用者判斷。

候選版固定 `graphifyy==0.9.35`，套件名稱是雙 `y`，CLI 命令仍是 `graphify`。版本、tag、commit、發行檔雜湊與授權來源以 `install.manifest.toml` 為準。本次查到的[最新正式版為 `0.9.53`](https://github.com/Graphify-Labs/graphify/releases/tag/v0.9.53)，但沒有在未取得同意的情況下下載或升級；正式支援前仍需隔離相容性測試。

## 輸出用途

- `graph.json`：供 Agent 查詢節點、關係與信心標記。
- `graph.html`：供使用者互動探索整體關係。
- `SOURCES_OVERVIEW.md` 與報告：供索引與品質檢查。

實際檔名與輸出內容可能隨上游版本改變，使用前應以 [Graphify 上游文件](https://github.com/Graphify-Labs/graphify) 為準。

## HTML 交付規則

一般單一事實查詢直接回答即可。遇到以下情況時，應主動提供 `graph.html`：

- 三個以上重要節點的關係。
- 跨文件、跨主題群或概念路徑。
- 核心節點、群聚結構或意外連結。
- 使用者明確要求查看整體架構或知識地圖。

提供 HTML 時，仍要在回答中整理結論、引用與最值得查看的節點，不能只把網頁丟給使用者自行判讀。

## 更新與信心邊界

- 保留 `EXTRACTED`、`INFERRED`、`AMBIGUOUS` 等信心標記。
- 圖譜過期時要清楚標示，不把舊關係當成最新狀態。
- 不為了交付 HTML 而盲目重建圖譜。
- manifest、環境或大量變更異常時，停止更新並回報。
- Graphify 的圖譜與推論只負責關係、路徑與導覽；回答重要事實時要回到原始檔案、可追溯來源與使用者確認內容。
- Graphify 不存在、執行失敗或圖譜過期時，仍以本機索引與原始檔案回答目前可支持的部分，並說明沒有圖譜輔助。

## 安裝與移除界線

- 使用者同意後才可安裝套件或註冊上游技能。
- 專案範圍的通用 Agent Skills 可使用 `graphify install --project --platform agents`；Codex 專用註冊可使用 `--platform codex`。Antigravity 的專屬命令另有 `graphify antigravity install`，不得假設所有平台參數相同。
- `graphify uninstall` 只處理上游註冊；預設不得使用會連同 `graphify-out/` 一起刪除的 `--purge`。
- 套件移除、技能移除與刪除圖譜輸出是三個不同操作，皆須分開確認。
