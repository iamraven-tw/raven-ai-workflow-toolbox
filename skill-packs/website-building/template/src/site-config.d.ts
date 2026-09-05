// site.config.mjs 的型別定義，讓 .astro 檔案取得欄位提示。
export type OptionalPage = 'portfolio' | 'case_studies' | 'pricing' | 'faq' | 'newsletter';
export type ThemeId = 'nightlight' | 'darkroom' | 'whitebox' | 'daylight' | 'sunrise' | 'weekly';

export interface Offering {
  name: string;
  summary: string;
}

export interface CallToAction {
  kind: 'mailto' | 'external_link' | 'form_later';
  label: string;
  target: string | null;
}

export interface ContactChannel {
  kind: 'email' | 'messaging_link' | 'social_profile' | 'external_page';
  label: string;
  target: string;
}

export interface SiteConfig {
  url: string;
  theme: ThemeId;
  /** google：載入各主題指定的 Google Fonts；system：只用系統字型 */
  fonts: 'google' | 'system';
  name: string;
  positioning: string;
  audience: string;
  language: 'zh-TW' | 'en';
  offerings: Offering[];
  trustSignals: string[];
  cta: CallToAction;
  contacts: ContactChannel[];
  pages: { optional: OptionalPage[] };
  indexing: 'noindex' | 'index';
}
