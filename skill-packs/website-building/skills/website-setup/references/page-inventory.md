# 頁面清單

## 依需求選頁（六頁保留為範例，不強制全選）

| 識別 | 頁面 | 內容來源 |
|---|---|---|
| `home` | 首頁：價值主張、服務摘要、信任依據、行動呼籲 | `business.*` |
| `about` | 關於：一句話定位、背景、為什麼做這件事 | `business.one_line_positioning`、`business.trust_signals` |
| `services` | 服務或產品：每項名稱、一段說明、行動呼籲 | `business.offerings` |
| `blog` | 部落格列表與單篇文章 | 網站專案內的 Markdown |
| `contact` | 聯絡：聯絡管道與行動呼籲 | `business.contact_channels`、`business.primary_call_to_action` |
| `not_found` | 404 | 固定 |

新設定只預選首頁與技術用 404；關於、服務、聯絡可留在首頁區塊，需要獨立網址才加入 `pages.required`。此欄沿用舊名稱，語意是本次已選核心頁面，舊六頁設定仍有效。

部落格只有需要經營文章時才選；RSS 隨部落格啟用，sitemap 依實際頁面產生。不建立沒有需求的文章或要求使用者先寫文章。需要表單／服務串接時，把目前串接器需要的聯絡頁納入同一份提案，不能到後面才多問一次。

## 可選頁面

| 識別 | 何時加入 |
|---|---|
| `portfolio` | 使用者提到作品、設計或影片集 |
| `case_studies` | 使用者提到客戶案例或成果 |
| `pricing` | 使用者明確想公開價格 |
| `faq` | 使用者提到常被問的問題 |
| `newsletter` | 使用者有電子報且想在官網收訂閱；hosted 訂閱入口由 `website-service-integration` 串接 |

可選頁面只在使用者提到對應內容時加入，不主動推銷。
