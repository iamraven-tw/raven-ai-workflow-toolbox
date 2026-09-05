// site.copy.mjs 的型別定義。所有欄位可為 null，null 代表沿用主題預設。
export interface AboutSection {
  heading: string;
  body: string | null;
}

export interface SiteCopy {
  home: {
    eyebrow: string | null;
    title: string | null;
    lead: string | null;
    primary_cta: string | null;
    secondary_cta: string | null;
    offerings_eyebrow: string | null;
    offerings_heading: string | null;
    offerings_intro: string | null;
    trust_eyebrow: string | null;
    trust_heading: string | null;
    closing_eyebrow: string | null;
    closing_heading: string | null;
    closing_lead: string | null;
  };
  about: { title: string | null; intro: string | null; sections: AboutSection[]; cta_heading: string | null };
  services: { title: string | null; intro: string | null; closing_note: string | null };
  contact: { title: string | null; intro: string | null; form_note: string | null };
  blog: { title: string | null; intro: string | null; empty_note: string | null };
  not_found: { title: string | null; lead: string | null };
}
