// 文案層：各頁面的標題、導言、段落與按鈕文字。
// 由 website-content-writing 產生；欄位為 null 時沿用主題自己的預設語氣。
// 這份檔案的內容全部是虛構佔位；不要寫入任何秘密或私人識別碼。

/** @type {import('./src/site-copy').SiteCopy} */
export const copy = {
  home: {
    eyebrow: null,
    title: null,
    lead: null,
    primary_cta: null,
    secondary_cta: null,
    offerings_eyebrow: null,
    offerings_heading: null,
    offerings_intro: null,
    trust_eyebrow: null,
    trust_heading: null,
    closing_eyebrow: null,
    closing_heading: null,
    closing_lead: null,
  },
  about: {
    title: null,
    intro: null,
    sections: [
      { heading: '我服務的對象', body: null },
      { heading: '我怎麼工作', body: '先釐清目標，再決定做法；每一步都交付可以自己維護的成果。這段文案是佔位，請依實際情況改寫。' },
    ],
    cta_heading: null,
  },
  services: {
    title: null,
    intro: null,
    closing_note: null,
  },
  contact: {
    title: null,
    intro: '選一個你方便的方式，我通常會在兩個工作天內回覆。這句是佔位文案，請依實際情況改寫。',
    form_note: null,
  },
  blog: {
    title: null,
    intro: '記錄工作方法、案例與想法。這句是佔位文案，請依實際情況改寫。',
    empty_note: null,
  },
  not_found: {
    title: null,
    lead: null,
  },
};
