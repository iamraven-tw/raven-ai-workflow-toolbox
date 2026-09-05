// 導覽連結與行動呼籲的共用資料；各主題的 Header／Footer 只負責版面。
import { site } from '../../site.config.mjs';

const optionalLabels: Record<string, { label: string; href: string }> = {
  portfolio: { label: '作品集', href: '/portfolio' },
  case_studies: { label: '案例', href: '/case-studies' },
  pricing: { label: '價目', href: '/pricing' },
  faq: { label: '常見問題', href: '/faq' },
  newsletter: { label: '電子報', href: '/newsletter' },
};

export const navLinks = [
  { label: '首頁', href: '/' },
  { label: '關於', href: '/about' },
  { label: '服務', href: '/services' },
  { label: '文章', href: '/blog' },
  ...site.pages.optional.map((page) => optionalLabels[page]).filter(Boolean),
  { label: '聯絡', href: '/contact' },
];

export const footerLinks = [
  { label: '關於', href: '/about' },
  { label: '服務', href: '/services' },
  { label: '文章', href: '/blog' },
  { label: '聯絡', href: '/contact' },
  { label: 'RSS', href: '/rss.xml' },
];

export const ctaHref = site.cta.kind === 'form_later' ? '/contact' : site.cta.target ?? '/contact';
export const ctaExternal = site.cta.kind === 'external_link';
export const ctaAttrs = ctaExternal ? { target: '_blank', rel: 'noopener noreferrer' } : {};
