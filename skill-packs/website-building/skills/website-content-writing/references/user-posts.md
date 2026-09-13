# 使用者自己的文章

部落格是選配；沒有文章需求就略過。使用者可提供既有 Markdown，也可明確要求 Agent 依確認過的素材撰稿，再批次審閱，不能因建站而強迫人類寫文章。

## 使用者怎麼寫

一篇文章一個 `.md` 檔，放在工作區的 `website/posts/`，檔名就是網址的 slug（小寫字母、數字、連字號）。開頭的 frontmatter：

```markdown
---
title: "文章標題"
date: "2026-01-15"
description: "一句話摘要，會顯示在列表與搜尋結果"
tags: ["自動化", "筆記"]
coverImage: "/images/posts/my-first-post/cover.jpg"
---

## 第一個小標

內文用 Markdown 寫。段落、清單、引言、程式碼區塊都會套用主題的閱讀排版。
```

- `title`、`date`、`description` 必填；`tags`、`coverImage` 可選。
- 內文至少 100 字，工具會擋太短的檔。
- 封面圖放專案的 `public/images/posts/<slug>/`，建議 1200×630、200KB 以內；沒有封面就不放，文章頁不會顯示預設圖。

## Agent 做什麼

- 使用者寫好後，在候選文案的 `posts` 登錄 `{slug, file, source: "user_fact"}`。
- `validate` 檢查 frontmatter、日期格式、長度；不改內容、不潤稿，除非使用者要求。
- `apply` 後由 `website-build` 帶進專案；有使用者文章時範例文章 `hello-world.md` 會被移除。已建站用 `sync`。
- 使用者想要 AI 幫忙潤稿時可以做，但改過的段落標 `ai_suggestion`，並提醒他再看一次。

## Agent 不做什麼

- 不主動提議「我幫你寫三篇」。
- 不編造案例、客戶故事或成果數字。
- 不因為沒有文章就阻擋上線；正式上線前由 Agent 排除範例文章，未提供文章時保留空列表，不要求人類補稿。
