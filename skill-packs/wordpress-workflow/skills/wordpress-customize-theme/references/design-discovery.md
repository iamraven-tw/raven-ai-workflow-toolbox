# Design discovery and example curation

Read this reference for the first visual-design conversation, when the user lacks a reference, or when an unsuitable reference requires alternatives.

## Ask in the user's language

Keep the first interaction short. Ask only questions whose answers cannot be derived from the site:

1. “有沒有一定要保留的 Logo、品牌色、字體、版面或功能？沒有的話回答『沒有』即可。”
2. “有沒有喜歡或不喜歡的網站？有的話貼網址並指出喜歡或不喜歡哪裡。沒有也沒關係，我可以替你找。”
3. “範例只看免費主題，還是也可以包含付費主題作為視覺參考？如果你已購買主題，也可以提供名稱或合法取得的安裝檔。”

Ask “這次要修改哪一個網站？” only when multiple live sites are plausible. Ask “網站主要用來放文章、作品、公司服務、商品，還是其他內容？” only when a new or empty site does not reveal its content type.

Do not ask users to provide hex colors, exact font names, grid measurements, border radii, shadow values, breakpoints, or design tokens.

## Give places to browse

When asking for a reference, offer these starting points with direct links:

- [WordPress.com Themes](https://wordpress.com/themes): prefer for WordPress.com installation candidates.
- [WordPress.org Theme Directory](https://wordpress.org/themes/): browse community themes, especially free options.
- [WordPress Pattern Directory](https://wordpress.org/patterns/): browse individual headers, galleries, calls to action, and other sections without changing an entire theme.
- [ThemeForest WordPress Themes](https://themeforest.net/category/wordpress): browse commercial themes and demos; payment and licensing remain the user's responsibility.

Tell the user to open Preview, Live Preview, or Demo; paste the actual demo URL when possible; and point out the homepage, header, palette, typography, article cards, article page, or other part they like. Accept a non-WordPress website as a visual reference.

Always offer this low-effort response:

> 請根據我的網站替我找三個適合的範例，並幫我選一個。

## Inspect references

- Open the actual demo and inspect more than the hero section.
- Capture or show useful views of the homepage and a representative inner page when available. Include a mobile view when it materially differs.
- Analyze color roles, typography hierarchy, content width, grid, spacing rhythm, borders, radii, shadows, imagery, cards, header, navigation, footer, archive, article layout, and responsive behavior.
- Separate stable design language from demo-specific text, stock images, plugins, animations, and features.
- Check the source, current availability, price class, license requirements, WordPress.com plan requirements, block or classic theme type, builder dependencies, and recent compatibility using live authoritative information.
- Do not infer installability from appearance or a sales page alone.

## Present three options

When the user has no firm reference, provide exactly three distinct directions. Each option should contain:

- A short non-technical label such as “極簡專業,” “現代雜誌,” or “大膽科技.”
- Screenshot or preview image when available.
- Direct demo URL and provider.
- What makes the option visually distinct.
- Why it suits the site's existing content and constraints.
- Which parts to reproduce and which parts to avoid.
- Free, included, or paid status and any known builder or plugin dependency.
- “Installation candidate” or “style reference only.”

Recommend one option and explain the reason in plain language. End with one low-effort question:

> A、B、C 哪個最接近你喜歡的感覺？你也可以說「A 的版面搭配 B 的顏色」、「都不喜歡」或「你決定」。

If the user chooses “你決定,” continue with the recommendation. If they reject all three, use their disliked elements to curate a new set.

## Explain purchase versus reconstruction

Whenever a selected reference is a commercial theme, include this short reminder in the user's language before implementation:

> 如果希望成果最接近這個 Demo，較理想的方式是合法購買原主題，再由 ChatGPT 依你的品牌客製化。這樣能使用原主題的模板、功能與更新。若不購買，我也可以參考它的配色、排版與視覺語言重新製作，但版型細節、互動效果、行動版呈現及主題專屬功能可能會有一些落差。

Do not pressure the user to buy. Follow the reminder with a recommendation based on the actual desired elements:

- Recommend purchase when the desired result depends on the original theme's code, templates, widgets, builder components, demo system, or support.
- Recommend reconstruction when the desired result is mainly color, typography, spacing, imagery, cards, and ordinary WordPress layouts that can be created cleanly with the current theme and blocks.
- State that ChatGPT or an agent subscription does not include a third-party theme license. Payments and account checkout must be completed by the user.
