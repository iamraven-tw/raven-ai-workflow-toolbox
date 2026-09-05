---
name: website-content-writing
description: "引導一人公司創業者填寫官網各頁文案。當使用者要填首頁標題、關於頁、聯絡頁，或想把範本的佔位句換成自己的話時使用。Agent 依 website/config.json 列出每頁必填與可選欄位、每欄的用途與一個虛構範例，讓使用者自己寫；使用者沒空的欄位 AI 先填起點並標 ai_suggestion，明講建議親自改過一遍。不編造數字、客戶或成就；建站階段不寫部落格文章，文章由使用者自己寫。確認後寫入 website/copy.json，由 website-build 帶進專案或用 sync 同步。不建置、不部署。"
---

# 官網文案填寫

這是官網打造工作流的第二個技能。AI 寫的文案通常不像本人、也容易寫出沒有依據的句子，所以本技能的重點是**引導使用者自己填**：清楚告訴他哪些欄位一定要有文字、每欄出現在網站哪裡、讀者要從它得到什麼、可以怎麼寫。AI 的句子只是起點，每一句都要能回答「這是誰說的」。

## 責任

- 讀 `website/config.json` 的商業事實：站名、定位、受眾、服務、信任依據、行動呼籲。這些是唯一可以當事實寫的來源；沒有寫在裡面的數字、客戶名稱、年資與成就一律不得出現。
- 用 `scripts/content_writer.py draft` 產生文案骨架，事實欄位已標 `user_fact`。
- 用 `scripts/content_writer.py guide --candidate <候選>` 取得欄位指南（`assets/field-guide.json`）：每欄的位置、用途、字數、一個虛構範例、目前狀態。**必填五欄**：首頁主標題、首頁導言、關於頁導言、關於頁至少一段、聯絡頁導言；其餘可留空沿用主題預設。
- 把整份指南一次列給使用者，從必填開始請他自己寫。使用者說「你先寫」時才代填，填的每一句標 `ai_suggestion`，並明講「這些是範例，建議你自己改過一遍」。
- 每個欄位標記來源：`user_fact`（使用者自己寫的或來自設定檔）、`ai_suggestion`（AI 起點，需要使用者決定採用、改寫或刪除）、`placeholder`（尚未填）。
- **不寫部落格文章。** 建站階段不需要文章，文章由使用者自己用 Markdown 寫；本技能只在他寫好後檢查格式並登錄，見 `references/user-posts.md`。不主動提議「我幫你寫幾篇」。
- `validate` 與 `preview`：工具會擋下 AI 建議裡使用者沒提供的數字與數量描述、定稿仍含佔位字樣、空白來源、定稿時必填欄位沒有文字。
- **批次確認**：把整份預覽表列給使用者，重點是每一條 `ai_suggestion` 他要採用、改寫還是刪除。使用者說「用你的範例就好」時尊重決定，但預覽與上線報告都要列出哪些欄位仍是 AI 範例。
- 確認後 `apply --confirm-write` 寫入 `website/copy.json`。網站尚未建立時交給 `website-build`（scaffold 會自動套用）；已建立時 `sync --confirm-write` 同步進專案，再由 `website-build` 重建與檢查。

本技能不決定風格、不建立專案、不建置、不部署。`site.config.mjs` 裡的事實欄位（站名、服務名稱與說明、聯絡方式）由 `website-setup` 管理，本技能不改它們；要改事實就回 `website-setup`。

## 輸入

- `website/config.json`（必要，`business.status` 不得是 `not_configured`）。
- 可選：使用者另外提供的素材，例如自我介紹、既有文章、社群貼文；知識庫套件的 `sources/` 若存在也可讀，作為語氣參考。取自素材但經 AI 改寫的句子仍標 `ai_suggestion`。
- 可選：既有的 `website/copy.json`，修改時以它為底。
- 可選：使用者自己寫好的文章 `website/posts/*.md`。

不讀取任何憑證、環境變數或瀏覽器資料。

## 啟動流程

這是多階段技能。開始執行前，用 Mermaid 向使用者呈現本次採用的分支、確認關卡與停止位置。

1. 唯讀檢查設定檔與既有 `website/copy.json`。已有文案時先摘要目前狀態，問這次要改哪些頁。
2. 沒有既有文案：`draft --config <workspace>/website/config.json --out <暫存>/copy.json`。
3. `guide --candidate <暫存>/copy.json`，把欄位指南完整列給使用者：先必填、再可選；每欄用「在哪裡、給讀者什麼、字數、範例」四件事說明，不長篇大論。說明可選欄位留空會沿用主題預設，不影響上線。
4. 使用者自己寫的文字寫進候選 JSON 標 `user_fact`。他請 AI 先填的欄位標 `ai_suggestion`，並依 `references/writing-rules.md` 的語氣寫；寫完立刻提醒「建議定稿前自己改過一遍」。
5. 使用者有自己寫好的文章時，依 `references/user-posts.md` 檢查並登錄到候選 JSON 的 `posts`；沒有就跳過，不提議代寫。
6. `validate` 修到沒有 `blocking`；`preview` 取得預覽表與雜湊。
7. 批次確認：把預覽表（欄位、來源、文字）完整列給使用者，逐條 `ai_suggestion` 請他決定；不要只給摘要。
8. 使用者確認後，若要定稿就把 `status` 改成 `final` 再 `preview` 一次；然後 `apply --confirm-write --expected-preview-sha256 <雜湊>`。
9. 網站已建立時：`sync --workspace-root <workspace> --project <專案> --confirm-write`，再請 `website-build` 執行 `npm run build` 與 `check_site.py`。
10. 回報並交接。

命令旗標不是對話核准。使用者沒有看過完整指南與預覽表前不得 `apply` 或 `sync`。

## 事實邊界

- 只有設定檔與使用者素材裡出現過的數字、名稱、成就可以寫進文案；工具會比對 `ai_suggestion` 裡的數字與「N 位／家／年／案例」這類數量描述，沒有依據就阻擋。
- 信任依據為空時，不寫「多年經驗」「眾多客戶」這類暗示性字眼；改寫工作方式與可以承諾的事。
- 回覆時間、價格、保證成果都是承諾，使用者說過才寫。
- 不用「業界領先」「最專業」等無法驗證的形容；不用 emoji。
- 使用者要求加入新事實時，先請他確認那是真的，然後回 `website-setup` 更新設定檔，再回來改文案。

## 寫入範圍

- `website/copy.json`：各頁文案與來源標記。
- 用 `sync` 時：專案的 `site.copy.mjs` 與 `src/content/posts/`（有使用者文章時複製並移除範例文章 `hello-world.md`）。

不得寫入技能目錄、範本目錄、`website/config.json`、`site.config.mjs` 或任何外部服務；不代寫 `website/posts/`。

## 執行錯誤最小回填

實際執行出錯，或可觀察行為與本技能規則衝突時，原任務優先：

1. 先保存使用者已確認的文案。
2. 若 `references/troubleshooting.md` 已存在，只讀與目前症狀相關的段落；不存在時不要先建立空檔。
3. 只有能證明錯誤來自本技能、修正限於同一個由使用者管理的技能來源、不新增依賴或外部授權，且重跑原失敗步驟通過時，才立即回填：流程更新本 `SKILL.md`，欄位指南更新 `assets/field-guide.json`，寫作規則更新 `references/writing-rules.md`，特定環境才建立或更新 `references/troubleshooting.md`。
4. 只做一次小修正、一次針對性重測，再執行本技能最快的既有格式／契約驗證，隨即回到原任務。
5. 一次修正仍失敗、需要改範本的文案欄位、需要跨技能改造時，停止回填並簡短回報缺口。

不得修改已安裝快取、內建技能、外掛或第三方來源。使用者的真實文案、品牌語氣與素材不得進入公開技能。回填不授權 commit、push、發布或部署。

## 輸出與交接

每次輸出至少包含：

- 欄位指南：必填欄位的完成狀態、仍是 AI 範例待改的欄位。
- 預覽表：每個欄位的路徑、來源、文字；`ai_suggestion` 與 `user_fact` 的數量。
- 使用者文章清單（若有）與格式檢查結果。
- 工具的 findings 與是否有阻擋項。
- 寫入結果：`copy.json` 路徑與雜湊、`sync` 結果。
- 下一個唯一建議動作：尚未建站交給 `website-build`；已建站則由 `website-build` 重建並檢查。

## 停止條件

- 商業資訊尚未設定。
- 使用者要求寫入設定檔沒有的數字、客戶或成就，且不願回 `website-setup` 確認為事實。
- 預覽有阻擋項（未驗證的數字、空白來源、定稿仍含佔位、定稿時必填欄位沒有文字）。
- 使用者未看過完整指南與預覽表。
- `sync` 的目標專案不是 `website-build` 建立的結構。

停止時保留候選檔與既有文案，不覆寫。

## 驗證

公開候選版以虛構工作區驗證：未設定停止、骨架把事實標 `user_fact`、`guide` 列出必填與狀態、定稿時必填欄位空白被阻擋、AI 建議含未提供的數字被阻擋、定稿含佔位被阻擋、`preview` 不寫檔、`apply` 需要旗標與同一雜湊、使用者文章 frontmatter 與長度檢查、`sync` 產生 `site.copy.mjs` 並複製文章與移除範例文章、`scaffold_site.py` 自動套用工作區文案、空欄位沿用主題預設。實際文案品質由使用者自己判斷與修改，虛構測試不涵蓋。
