# 草稿交付與媒體分流

## 先給人看，不先給問卷

用 [草稿範本](../assets/draft-template.md) 呈現完整成品、來源和待解問題。AI 自己整理紀錄；使用者只看文案、必要媒體需求與修改差異。每平台只做被選取形式，不自動增加版本或五平台全套。

每份預覽至少含：平台／形式、標題（適用時）、實際完整正文與 CTA、語氣依據、字元數／需要時 UTF-8 bytes、來源／待查主張、媒體狀態。備註不得混入可貼出的文字。無實際網址時將 CTA 標為待補，不製造真實帳號連結；有待補內容的版本不能交給發布。

## 媒體需求包

| kind | 必備簡報 | 交接 |
|---|---|---|
| image | visual、exact_text（逐張精確圖上文字，可空）、aspect_ratio（已選比例或待製作端確認）、alt_text（依現有證據／設計意圖） | social-image-production；預設 AI 生圖路徑，沒有模型權限時由該技能評估程式排版；本技能不生成 |
| edit_video | script、shots、duration_target、aspect_ratio，以及至少一個既有素材參照 | 環境中已安裝的 video-use／既有 AI 剪片工作流；不重做剪片能力 |
| record_video | script、shots、duration_target、aspect_ratio | 人類錄製需求包；素材到齊後才交剪輯 |
| generate_video | script、shots、duration_target、aspect_ratio | 只保留分鏡／生成需求；工具能力、資料上傳、價格和生成授權另確認，不視為既有剪片已支援 |

腳本可以是口播稿；shots 是逐鏡頭目的與畫面描述，不代表已生成分鏡圖。duration_target 是目標，不保證實際講完時間；已有素材不得編造時間碼。圖片若多張，exact_text 順序與視覺簡報必須一致，不把「第 3 張稍後補」當完整成品。

素材需列權利來源與人物／商標使用限制，核准文字不等於核准成圖、影片或配樂。實際檔案尺寸、長度、格式與 AI 生成揭露由製作／發布端依選取平台重新核對。媒體缺少或權利不明不阻擋先寫草稿，但必須明列；生成新影片不能默默換成下載網路片段。

## 最小 draft.json

只在保存／交接需要時使用。所有內容留私人工作區，程式只讀 JSON，不讀其中的來源路徑、取秘密、連網或呼叫工具。

- schema_version: 1。
- input: kind 為 planning 或 direct_user；evidence_ref 是可定位的私人規劃決定／使用者請求參照。Agent 必須讀原始證據；程式不能驗證本人意圖。planning 入口先核對規劃已確認，不能用新紀錄繞過原本關卡。
- drafts: 一筆一個可單獨核准的版本，包含 id、platform、format、title、body、cta_goal、voice_basis、sources（參照文字陣列）、unresolved（待查／缺件陣列）、media、status 與 approval。
- title 可空，但 YouTube／Substack 不可空；body 必須包含實際完整 CTA／連結／標籤，不以 cta_goal 代替成品。額外 subtitle、系列順序等欄位會一併納入雜湊。
- media: kind 為上表值、status 為 needed 或 provided、references 為素材／權利參照陣列、rights 為已知權利或待核對文字、brief 為上表必備欄位。provided 需有參照，但只是有人提供資料，不是已審核、平台合格或已發布；來源與檔案仍須由 Agent 人工語意核對。
- status 預設 draft、approval 為 null。使用者真正看過目前完整預覽並核准後，才設 approved，approval 包含 scope: copy_only、digest、user_response、evidence_ref、confirmed_at（有時區 ISO 時間）。

以本技能 scripts/check_drafts.py 的絕對路徑執行 `python3 <script> <draft.json>`，回傳各 id 的 digest、長度、警告。核准綁定 input 參照及整筆內容，排除 status／approval；任一文案或媒體簡報變動使舊核准失效。digest 只供一致性檢查，不能證明人類批准。不要要求人類輸入雜湊。

交接前加 `--handoff --ids <已核准id> [其他id]`；未列 ids 則檢查全部草稿。只可選真正核准的版本，未核准／有 unresolved 的版本不能混入交接。成功仍固定回報 publishing_authorized: false；媒體待製作可交需求包，但進發布前須由人審核實際成品並經發布技能重新預覽確認。不能以此程式授權付費生成、下載、錄製或發布。

MVP 的已知硬限制為本輪官方核實的 YouTube title／description、Instagram 指定 API 路線 caption 與 Threads 基本正文。Facebook、Substack 的未核實上限回報警告；不得將「字數檢查通過」說成所有平台格式已驗收。數字過長先改寫，不無聲截斷字元或改移到尚未支援的附件。
