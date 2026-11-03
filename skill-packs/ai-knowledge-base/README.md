# My Real Second Brain

原 Learn-GAS 與 My Real Second Brain 的公開核心，今後只在 `raven-ai-workflow-toolbox` 維護；舊儲存庫不再提供後續功能更新。

> 讓第二大腦服務第一大腦，而不是取代第一大腦。

`My Real Second Brain` 是一套由 AI Agent 協助維護的個人知識系統。它把本地端知識、讀書筆記、知識圖譜與在你電腦上執行的原文搜尋（本地 RAG）接在一起，但最終的閱讀、理解、判斷與選擇，始終由人類負責。

目前版本是「可供外部驗收」的本機候選版，不是正式支援。五個自有技能、安裝生命週期與空白工作區可在本機驗證；第三方乾淨安裝、本地 RAG 與另一臺電腦實測仍是分開的驗收關卡。

## 核心理念

第一大腦是使用者本人。第二大腦只負責保存、整理、連結、檢索與提醒，不把「AI 找得到」誤認為「人類已經理解」。

只有經過使用者親自閱讀、思考，或與 AI 討論後確認的內容，才會進入本地端核心知識庫。尚未閱讀或仍不熟悉的長篇外部原文，可以先放進本地 RAG 查詢，但預設知識優先度較低。

這個「較低」不是指外部原文必然不正確，而是它尚未經過第一大腦充分吸收。遇到可驗證事實時，仍應比較來源品質、時間與證據，不能用個人筆記自動覆蓋較新的第一方資料。

```mermaid
flowchart TD
    A["尚未熟悉或閱讀的外部原文"] --> B["本地 RAG<br/>在你電腦上查原文與出處"]
    B --> C["第一大腦<br/>閱讀、判斷、與 AI 討論"]
    D["書籍、文章、經驗與既有知識"] --> C
    C --> E["本地端核心知識庫<br/>已吸收與消化"]
    E --> F["Graphify<br/>找出關係與提供導覽"]
    E --> G["寫作、研究與決策"]
    F --> G
```

## 知識層級

### 1. 本地端核心知識庫

本地端保存使用者已經親自接觸並消化過的內容，包括：

- 讀過的書籍與讀書心得。
- 閱讀過的文章與研究資料。
- 使用者與 AI 討論後形成的理解。
- 使用者自己的經驗、觀點、疑問與判斷。
- 經過確認的決策與工作方法。

這些內容具有最高的個人知識優先度。外部檢索結果不能直接覆蓋它；發生衝突時，系統應並列差異、保留引用，再交由使用者判斷。

### 2. 本地 RAG（查原文）

PDF 或 6000 字以上的長篇外部資料，會放進 `sources/external/`，並切成約 700 字的小段建立索引。需要原文、出處、精確數字或引用時，AI 會在你的電腦上搜尋這些片段，回答時標出檔案與段落標題。

- 全部在本機執行：不上傳、不需要登入任何帳號，安裝後不需要網路。
- 使用 Ollama 與 `qwen3-embedding:4b` 向量模型，匯入或查詢時約佔 3.1 GB 記憶體，閒置約 2 分鐘後自動釋放（只剩約 40 MB）。建議 16 GB 記憶體以上的 Mac。
- 匯入與查詢速度依電腦而定；維護者單機的參考數字見 [`docs/integrations/local-rag.md`](docs/integrations/local-rag.md) 的「參考紀錄：維護者單機實測」，只供參考、不是保證。
- 只接受 PDF、Markdown、純文字（UTF-8）與 HTML；Word、簡報、圖片等格式會留在收件匣並告訴你原因。
- 一般問題先看 Wiki 與 Graphify；本地 RAG 是查原文時才用的補充工具。

外部原文屬於探索性知識。重要內容經使用者閱讀與確認後，才能整理進本地端核心知識庫。

### 3. Graphify

Graphify 負責分析本地資料之間的關係，產生可查詢的知識圖譜、報告與互動式 HTML 網頁。

Graphify 是關係分析與導覽工具，不是最高事實來源。圖譜中的推論必須保留信心標記，重要結論仍應回到原始文件與使用者的實際理解。

### 4. LLM Wiki

本專案採用 LLM Wiki 的持續累積觀念：保存原始來源、由 Agent 維護可演化的 Wiki，並以明確規則約束匯入、查詢、引用與維護。每次閱讀、討論與研究，都應留下未來可以再次使用的成果。

## 用說的，降低記錄門檻

這個專案強烈鼓勵使用者用口說記錄知識。讀完一章或一本書後，不必先整理成完整文章；可以打開 Typeless 這類語音轉文字工具，直接說出剛讀完的感受、疑問、同意與不同意之處，再交給 AI 保存和整理。

建議流程很簡單：

1. 趁內容還有印象時，先用自己的話說出來。
2. 將語音轉成文字後，檢查書名、人名與專有名詞是否正確。
3. 讓 `book-notes` 優先保留接近原話的內容，再另外整理核心觀點。
4. 只有使用者確認過的整理結果，才視為第二大腦中的正式知識。

Typeless 只是推薦範例，不是必要依賴，也不是本專案的官方整合；任何可靠的語音轉文字工具都可以使用。第三方工具可能會處理使用者的音訊或文字，使用前應自行確認隱私政策，不要口述不適合交給外部服務的敏感資訊。

## 第一次啟動與一人公司設定

如果使用者第一次啟動時沒有提出其他明確任務，而且 `sources/strategy/solopreneur-profile.md` 尚未完成，`solopreneur-profile` 會用一次一題的方式協助建立一人公司的長期設定。

設定內容包括目前階段、目標使用者、核心問題、產品與價值、取得客戶的方法、已有資產、限制、近期優先事項與仍待確認的假設。AI 會先顯示準備寫入的內容，取得確認後才更新檔案。

使用者已提出明確任務時，設定流程不會擋住工作。之後遇到創業方向、定位、客群、產品或優先順序問題，AI 才先讀設定檔與既有知識，再依需要啟動蘇格拉底式對話。

社群策略、內容規劃、平台角色、互動原則與成效判斷另外使用 `sources/strategy/social-media-strategy-and-insights.md`。公開版只提供 `not_configured` 空白範本；逐期報告先與使用者討論並加入使用者判斷，確認後才可把長期洞察寫入。

## 資料會存在哪裡

只有一個收件匣：`sources/inbox/`。你要放進知識庫的檔案，直接交給 AI Agent 就好；檔案原本在其他資料夾時，Agent 會**複製**一份進收件匣，絕不搬走或刪除你的原檔。

Agent 會執行匯入腳本，自動分流：

1. **PDF，或 6000 字以上的長文**：原檔搬到 `sources/external/`，切成約 700 字的片段存進本地索引，並在 `sources/wiki/` 建立一頁 `ext_<檔名>.md` 摘要頁；Agent 接著補寫三到五行摘要與關鍵詞，摘要頁會連回原檔。
2. **其他檔案（你自己的筆記、短文）**：Agent 依規則整理進 Wiki、讀書筆記或次級資料。
3. 處理完後收件匣會清空；失敗的檔案留著並告訴你原因。

```mermaid
flowchart TD
    A["你交給 Agent 的檔案"] --> B["複製到 sources/inbox/<br/>原檔不動"]
    B --> C{"PDF 或 6000 字以上？"}
    C -- "是" --> D["sources/external/ 原文<br/>+ 本地 RAG 索引"]
    D --> E["wiki/ext_*.md 摘要頁<br/>Agent 補寫摘要與關鍵詞"]
    C -- "否" --> F["Agent 整理進 wiki/、book-notes/ 或 references/"]
    E --> G["清空收件匣"]
    F --> G
```

| 資料或情況 | 預設位置 | 儲存原則 |
|---|---|---|
| 使用者確認的一人公司方向、客群、價值、限制與優先事項 | `sources/strategy/solopreneur-profile.md` | 第一次無明確任務且尚未設定時逐步建立；任何寫入先預覽並取得確認。 |
| 使用者確認的社群策略、平台角色與長期洞察 | `sources/strategy/social-media-strategy-and-insights.md` | 讀取成效報告後先與使用者討論；只把經確認的結論寫入，原始數據留在實際工作區。 |
| 使用者直接說出的讀書心得、觀點與判斷 | `sources/book-notes/` | 保存接近使用者原話的內容；同一本書持續追加到同一份 Markdown。 |
| 要放進知識庫、還沒分類的檔案 | `sources/inbox/` | 唯一的收件匣；處理完清空。 |
| PDF 或 6000 字以上的長篇外部原文 | `sources/external/` | 由匯入腳本搬入並建立本地 RAG 索引；每份都有 `wiki/ext_*.md` 摘要頁。 |
| 一般篇幅的作者文章、軟體文件或網路來源紀錄 | `sources/references/` | 保存可追溯的次級資料；不得把作者原文當成使用者心得。 |
| 已存在於其他本機位置、只想問一下的單一文件 | 原始位置 | 直接從原位置讀取；沒有要求納入知識庫就不複製。 |
| 只供本次討論或研究使用的附件 | 不建立永久副本 | 完成當次任務後不自動納入第二大腦；需要長期保存時再由使用者指定。 |
| 知識詰問中臨時搜尋的網路資料 | 不建立永久副本 | 當次回答附上可核對的原始網址；只有使用者明確要求長期保存時才寫入。 |
| Agent 根據心得與來源整理出的可演化知識頁 | `sources/wiki/` | 保存結構化整理與引用，不取代原始來源或使用者判斷。 |
| 本地 RAG 的程式、Python 環境與索引 | `sources/rag/` | 程式隨範本提供；`.venv/` 與 `lancedb/` 可重建，不進版本控制。 |
| Graphify 或其他知識結構 Provider 產生的圖譜、報告與互動網頁 | `sources/graphify-out/` | 視為可重建的衍生輸出，不作為唯一事實來源。 |

查詢時的順序：

1. 先看 Wiki（含外部原文摘要頁）與 Graphify。
2. 只有你要原文、出處、精確數字或引用，或 Wiki 不夠詳細時，才查本地 RAG；回答一律標出檔案與段落。
3. 重要內容只有在使用者閱讀、討論與確認後，才能升級為本地端核心知識。

Graphify 只讀整理過的知識：`wiki/` 裡只有 `ext_*.md` 摘要頁進入圖譜，讓圖譜知道「有哪些原文可查」；收件匣、外部原文與 RAG 索引都不進圖譜（規則在 `sources/.graphifyignore`）。

## 技能組與底層工具

本專案自行維護五個協調技能：

| 技能 | 用途 |
|---|---|
| `my-real-second-brain-setup` | 管理五個自有技能的安裝、更新、回復與移除，安全初始化工作區；取得同意後才安裝 Graphify 與本地 RAG，也處理從 NotebookLM 舊版升級。 |
| `solopreneur-profile` | 第一次無明確任務時逐步建立一人公司設定，並在創業問題中提供長期脈絡。 |
| `book-notes` | 優先保存使用者直接說出的第一大腦想法，再將閱讀與 AI 討論整理成一書一檔。 |
| `knowledge-source-retrieval` | 先查 Wiki、Graphify 與核心知識，需要原文時才查本地 RAG；處理收件匣匯入，整合來源、引用與知識圖譜視覺化。 |
| `socratic-dialogue` | 先從第二大腦找出既有觀點，資料不足、過時或缺少反方時再搜尋網路，以白話的一問一答與階段摘要協助使用者形成共同理解。 |

底層實際操作由外部工具負責：

| 外部能力 | 用途 | 本專案的處理方式 |
|---|---|---|
| 本地 RAG：Ollama、`qwen3-embedding:4b`、lancedb 等 Python 套件 | 在本機建立原文索引、查詢並回傳檔案與段落 | 匯入與查詢腳本是自有程式；外部元件在使用者同意後由 AI Agent 安裝，不封存進本倉庫。 |
| Graphify | 建立、查詢與視覺化本地知識圖譜 | 使用者同意後，AI Agent 才依固定版本安裝上游套件與技能；本專案定義使用及 HTML 交付規則。 |

Graphify 與本地 RAG 是目前的預設後端，不是系統本身。詳細邊界與替換契約請見 `docs/providers.md` 及 `docs/integrations/`。

## 公開核心與實際案例

本 repository 保存通用技能、安裝契約與空白工作區範本；私人知識庫則保存自己的專案規則、筆記、索引與研究資料。兩邊不會自動同步。只有維護者日後明確選定的改進，才會在去識別化、一般化與候選版驗證後納入新的公開版本。完整規則見 `docs/development-workflow.md`。

## 外部專案與概念來源

本專案不是下列專案或服務的官方產品，也不代表它們提供背書。

| 名稱 | 本專案中的角色 | 關係與授權 |
|---|---|---|
| [Graphify](https://github.com/Graphify-Labs/graphify) | 本地知識圖譜、關聯分析與 HTML 視覺化 | 預設但可替換的外部後端；目前主體採 Apache-2.0，部分早期內容保留 MIT 條款。 |
| [Ollama](https://github.com/ollama/ollama) | 在本機執行向量模型 | 本地 RAG 的外部元件；MIT License。 |
| [Qwen3-Embedding-4B](https://huggingface.co/Qwen/Qwen3-Embedding-4B) | 把文字轉成向量 | 本地 RAG 使用的模型；Apache-2.0。 |
| [LanceDB](https://github.com/lancedb/lancedb) | 本機向量與全文索引 | 本地 RAG 的外部元件；Apache-2.0。 |
| [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | 原始來源、持續演化 Wiki 與規則層的概念啟發 | 僅引用概念並重新實作，不重製原始文件。 |
| [Capacities](https://capacities.io/) | 物件、類型與關聯式知識整理的概念參考 | 專有產品；本專案不包含其程式、介面、圖片、商標或文件內容。 |

完整來源與授權說明請見 `THIRD_PARTY_NOTICES.md`。

## 專案結構

```text
My Real Second Brain/
├── README.md
├── INSTALL.md
├── LICENSE
├── THIRD_PARTY_NOTICES.md
├── install.manifest.toml
├── scripts/
│   └── manage_install.py
├── AGENTS.md
├── CLAUDE.md
├── docs/
│   ├── architecture.md
│   ├── client-compatibility.md
│   ├── development-workflow.md
│   ├── installation.md
│   ├── providers.md
│   └── integrations/
│       ├── graphify.md
│       └── local-rag.md
├── skills/
│   ├── book-notes/
│   ├── knowledge-source-retrieval/
│   ├── my-real-second-brain-setup/
│   ├── solopreneur-profile/
│   └── socratic-dialogue/
└── template/
    ├── AGENTS.md
    ├── CLAUDE.md
    └── sources/
        ├── strategy/
        ├── book-notes/
        ├── inbox/
        ├── external/
        ├── rag/scripts/
        ├── references/
        ├── wiki/
        └── graphify-out/
```

## 由 AI Agent 安裝

使用者不需要分別研究或手動下載 Graphify、Ollama 或任何套件，也不需要自己輸入指令。下載本專案後，將以下要求交給具備本機操作能力的 AI Agent：

```text
請閱讀 AGENTS.md 與 INSTALL.md，依 install.manifest.toml 安裝並驗證
My Real Second Brain。任何外部下載或覆蓋前，先向我說明並取得同意。
```

取得對應授權後，AI Agent 會：

1. 檢查環境與既有安裝，不先改動系統。
2. 說明即將下載的上游套件、固定版本與影響範圍。
3. 以可重跑、可更新、可回復且可移除的本機管理器安裝五個自有技能。
4. 先預覽第二大腦工作區，再只補上 `template/` 中缺少的項目；既有檔案保持不變。
5. 另行取得同意後，才安裝 Graphify 與該工作區範圍的上游技能。
6. 安裝本地 RAG：用 Homebrew 安裝 Ollama 並設為開機自動啟動、下載 `qwen3-embedding:4b` 向量模型、在工作區建立 Python 環境。
7. 分別驗證工作區、技能發現、Graphify 與本地 RAG，留下不含憑證或知識內容的本機狀態。

完整流程請見 `INSTALL.md`。第一次安裝需要網路，但使用者不必另行造訪任何上游網站。

三種目標用戶端的規則入口、已驗證版本與已知限制，請見 `docs/client-compatibility.md`。

`install.manifest.toml` 是機器可讀的單一安裝入口，明確列出五個必要技能、來源路徑、預設範圍、provider 與本地 RAG 元件，以及安裝與驗證順序。

## 從舊版（NotebookLM）升級

先前版本使用 NotebookLM 與 `notebooklm-py`；新版改用本地 RAG。已安裝舊版的使用者只要告訴 Agent「幫我升級 AI 知識庫」：

- Agent 會先告訴你 NotebookLM 已不再使用，**你在 NotebookLM 裡的資料不會被刪除**。
- Agent 會更新技能、補上 `sources/inbox/`、`sources/external/` 與 `sources/rag/`，安裝 Ollama（開機自動啟動）、向量模型與 Python 環境；你原本的檔案都會保留。
- 可選：Agent 可以協助把 NotebookLM 的原始來源下載到收件匣，再匯入本地 RAG。
- 電腦上原本安裝的 `notebooklm-py` 可以留著，不會被強制移除。

詳細步驟見 `docs/installation.md` 第 8 節。

## 本機維護驗證

候選版的靜態契約與虛構資料生命週期測試可直接執行：

```bash
python3 tests/validate_repository.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

第一個命令檢查 manifest、固定版本、五個技能、用戶端登錄、範本、連結、隱私邊界與 symlink；第二個命令實際建立暫存技能包與工作區，驗證正常安裝、重跑、衝突、更新、回復、移除、安全停止、模板保留與技能責任契約。兩者都不會安裝第三方套件、下載模型或連線外部服務。

## 授權

本專案自行撰寫的內容依買家授權條款（根目錄 LICENSE）提供。外部專案仍各自適用原有授權與條款。
