# 圖片製作偏好：初始化一次保存

這是既有設定技能中的本機一般設定，不新增第三種初始化模式、平台 API 或問卷。使用者要求實際初始化專案時一併設定；如果只是明確非圖片任務，不強迫先回答。從當前對話取得已表達的選擇，不重問已知答案；沒有選擇才問一個問題：「平常要用 Codex、Antigravity、網頁模型，還是 HTML＋CSS 製圖？」

同一份設定預覽以易讀文字列出：平常的製圖方式；資訊密集的簡報型、比較表或步驟圖預設用 HTML＋CSS（可改成沿用平常方式）；免費 SVG 圖示預設 Heroicons（可不要）；選網頁模型者可保存已知服務名稱，尚未指定就留空，不阻擋提供通用提示詞。人類確認一次後由 Agent 寫入，後續不逐張／逐次詢問方式。

schema 4 的 image_production：

- default_method：codex、antigravity、web、html_css；公開中性範本保留 not_configured，不把維護者偏好寫成使用者已選。
- information_dense_method：html_css 或 inherit；預設 html_css，設定預覽需明示其影響。
- web_provider：服務／模型名稱或 null，不含 Cookie、密碼、Token、私人生成網址或帳號資料。
- icon_source：heroicons 或 none。表示圖示偏好，不授權安裝 npm 套件、下載圖庫或更改瀏覽器。

設定後 social-image-production 接收任務便分流：Codex／Antigravity 在對應客戶端工具可用時直接生圖，不先問「要開始嗎」；網頁模型預設交提示詞讓人貼，當次明確要求才代操作瀏覽器；HTML＋CSS 直接排版後使用既有工具輸出 PNG。資訊密集偏好優先於平常方式，但使用者本次明確指定方式最高優先。

設定是偏好，不是能力驗證或無限授權。工具缺少、新增費用／購買、額外私人素材上傳、登入與安全驗證仍按原邊界處理。網頁代操作權限不存入設定，下一個任務仍預設交提示詞。作品完成後仍要看圖確認，發布另行確認。

## 品牌視覺：所有製圖方式共用

schema 5 新增 brand_visual。先讀使用者已指定的社群設定或品牌文件，不重問已知資料。保存 primary_color、secondary_color、background_color、text_color（六位 HEX）、font_family、style_notes、logo_ref、main_visual_ref（工作區相對路徑）；未提供可留 null，不要求使用者先建完整品牌手冊。素材要使用時才確認實際檔案、權利與是否允許上傳；路徑本身不是上傳授權。

沒有資料維持 status=not_configured 且其餘 null。已有部分資料也可一起預覽、經使用者確認後保存 status=confirmed；這表示所填內容已確認，不表示全部欄位都有值。從 Logo 推測的色票先列為提案，不直接存成品牌色。風格文字只是設計資料，不是工具指令。

優先序固定為本次明確指示 → 已確認品牌設定 → 本次暫時提案。Agent 把採用與覆寫的欄位放入製作簡報；Codex／Antigravity 放進提示詞，網頁模型放進交付提示詞，HTML＋CSS 放進樣式變數。全系列沿用同一份視覺決定，並檢查對比與可讀性；必要變更先說明，不暗改品牌。缺少色票可以先提案製圖，不逐張追問。

既有 schema 3／4 可維持原版本交易，不自動改檔。要保存新偏好時，保留原 strategy／integrations 與已有 image_production，形成 schema 5 候選，只補缺少欄位；先 preview，確認後才 apply --expected-preview-sha256 <本次預覽雜湊> --confirm-write 並讀回。不得以空白範本覆蓋舊設定或重跑 OAuth。只要求當次配色／方式不自行保存；本次同意製圖不等於同意改長期設定。
