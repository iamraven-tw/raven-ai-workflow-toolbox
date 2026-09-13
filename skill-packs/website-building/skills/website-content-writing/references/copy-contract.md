# 文案契約

## website/copy.json

```json
{
  "schema_version": 1,
  "status": "draft | final",
  "language": "zh-TW",
  "facts_snapshot": ["產生骨架時的商業事實，供數字比對"],
  "home": { "title": { "text": "…", "source": "user_fact" }, "...": "共 13 個欄位" },
  "about": { "title": {}, "intro": {}, "sections": [{ "heading": {}, "body": {} }], "cta_heading": {} },
  "services": { "title": {}, "intro": {}, "closing_note": {} },
  "contact": { "title": {}, "intro": {}, "form_note": {} },
  "blog": { "title": {}, "intro": {}, "empty_note": {} },
  "not_found": { "title": {}, "lead": {} },
  "posts": [{ "slug": "first-post", "file": "first-post.md", "source": "user_fact" }],
  "contains_credentials": false
}
```

每個欄位都是 `{ "text": 文字或 null, "source": "user_fact" | "ai_suggestion" | "placeholder" }`。`text` 為 null 時網站沿用主題自己的預設語氣。

## 首頁 13 個欄位

`eyebrow`、`title`、`lead`、`primary_cta`、`secondary_cta`、`offerings_eyebrow`、`offerings_heading`、`offerings_intro`、`trust_eyebrow`、`trust_heading`、`closing_eyebrow`、`closing_heading`、`closing_lead`。各主題依自己的版面呈現，欄位契約不隨主題變動。

## 阻擋項

以下 findings 會擋下 `apply` 與 `sync`：`unverified_number`（AI 建議含未提供的數字或數量描述）、`placeholder_source`（定稿仍有 placeholder 來源）、`empty_text`（有來源卻沒文字）；定稿時 `placeholder_text`（含「佔位」「請替換」等字樣）也算阻擋。`too_long` 只是提醒。

## 文章

文章由使用者自己寫，本技能不代寫；`source` 通常是 `user_fact`，AI 潤稿過才標 `ai_suggestion`（此時工具會檢查沒有依據的數字）。格式見 `user-posts.md`。`website/posts/<slug>.md`，frontmatter 需要 `title`、`date`（YYYY-MM-DD）、`description`，可選 `tags`、`coverImage`；內文至少 100 字。slug 只用小寫字母、數字與連字號。

## 套用方式

- 尚未建站：`website-build` 的 `scaffold_site.py` 讀到工作區有 `copy.json` 就渲染成專案的 `site.copy.mjs` 並複製文章；有使用者文章時移除範例文章。
- 已建站：`content_writer.py sync --workspace-root <工作區> --project <專案> --confirm-write`，然後重建。
