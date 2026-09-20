# WordPress MCP 工作流

這個技能包讓 AI Agent 透過 WordPress.com 官方 MCP 連接網站，並提供三個可分開觸發的技能：

- `wordpress-mcp-workflow`：OAuth 連線、網站辨識、讀寫權限、風險分級與驗證。
- `wordpress-customize-theme`：根據真實參考網站提出視覺方向，並以 MCP 修改佈景主題、全站樣式與版型。
- `wordpress-publish-article`：把已完成文章整理成 WordPress 欄位，依使用者要求儲存為草稿、排程、正式發布或更新。

## 適用範圍

這份公開包不包含任何客戶信箱、網站清單、OAuth 網址、授權碼、Token、Cookie、Chrome 設定檔或真實內容。OAuth 必須由每位使用者在自己的瀏覽器中完成；Agent 只驗證去識別化的連線結果。

安裝技能只會複製本機檔案，不會登入 WordPress、不會建立文章，也不會修改網站。實際操作時，必須先從 MCP 重新取得網站清單與工具結構，不能使用維護者的舊紀錄推定使用者網站。

## 已驗證與尚未驗證

- 已驗證：三個技能格式、公開內容去識別化、隔離安裝、相同版本重跑、衝突保護、更新、回復與可復原移除。
- 維護者環境曾驗證：WordPress.com MCP 讀取、寫入後重新讀取與瀏覽器視覺檢查的完整分層流程。
- 尚未驗證：學員自己的 OAuth、帳號權限、方案限制、MCP 工具清單、主題相容性及正式網站寫入。

所以本包目前是可安裝的外部驗收候選版，不代表每個 WordPress.com 帳號或方案都已正式支援。

## 開始使用

先讓具備本機檔案操作能力的 Agent 閱讀 [`INSTALL.md`](INSTALL.md) 與 [`install.manifest.toml`](install.manifest.toml)，執行唯讀 `status`，再由使用者確認安裝位置。安裝後，在新對話中提出「連接我的 WordPress.com 並先做唯讀驗證」。

ChatGPT 使用者可依 `wordpress-mcp-workflow` 的 onboarding 文件安裝官方 WordPress.com 外掛；Codex、Claude Code 與 Antigravity 則需在各自支援的 MCP 設定中加入官方端點。不同產品的入口可能改版，遇到差異時應以當下介面與官方文件為準。
