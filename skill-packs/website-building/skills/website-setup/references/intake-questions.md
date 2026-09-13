# 一次訪談題目

原則：一次列出所有仍缺的題目，每題附 Agent 推得的預設答案與來源；使用者只回答或修正。已有答案的欄位不重問。

## 核心五題（必問，除非既有來源已有答案）

| 題目 | 對應欄位 | 可推得的來源 |
|---|---|---|
| 這個網站要服務誰？他們遇到什麼問題？ | `business.audience_summary` | 一人公司設定檔「想服務的人」；社群設定 `strategy.audience_summary` |
| 你提供什麼產品或服務？請列一到三項，各一句話。 | `business.offerings` | 一人公司設定檔「產品與價值」 |
| 訪客為什麼應該相信你？（經歷、案例、數字，沒有就留空） | `business.trust_signals` | 一人公司設定檔「已有資產」 |
| 你希望訪客看完做什麼？（寫信、加社群、預約、購買） | `business.primary_call_to_action` | 社群設定 `strategy.primary_goal` 可作提示，不能直接當答案 |
| 訪客可以怎麼聯絡你？（信箱、通訊軟體連結、社群帳號） | `business.contact_channels` | 無，必問 |

## 補充題（只在會改變內容或路線時問）

| 題目 | 對應欄位 | 何時問 |
|---|---|---|
| 網站名稱要用什麼？ | `business.site_name` | 一人公司設定檔沒有品牌名時 |
| 一句話介紹你自己或公司？ | `business.one_line_positioning` | 一人公司設定檔「一句話方向」缺少時 |
| 網站主要語言？ | `business.language` | 預設 `zh-TW`，使用者受眾是海外時才問 |
| 現在有沒有網域？在哪裡買的？DNS 在不在 Cloudflare？ | `hosting.custom_domain` | 必問，但可以一句話帶過 |
| 有沒有 Cloudflare 帳號？ | 不寫入設定，只影響部署階段的人類接觸點 | 必問 |
| 有沒有 Logo 或照片想用？ | 不寫入設定，交接給 `website-build` | 可選 |
| 網站可以載入 Google Fonts 嗎？（會向 Google 發請求；不要就用系統字型） | `design.fonts` | 放在批次確認裡一句話帶過，預設 `google` |
| 有哪些內容需要獨立頁面？是否需要部落格、作品集、案例、價目、常見問題或電子報？ | `pages.optional` | 使用者提到對應內容時 |

## 不要問的題目

- 技術選型（框架、託管商、部署方式）。這些由套件決定，使用者不需要理解。
- 顏色、字型、版面細節。由 `website-design-preview` 用預覽讓使用者選，不用文字問。
- 任何要使用者貼上 Token、密碼或 API key 的問題。
