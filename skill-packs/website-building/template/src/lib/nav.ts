// 導覽連結與行動呼籲的共用資料；各主題的 Header／Footer 只負責版面。
import { site } from '../../site.config.mjs';

const optionalLabels: Record<string, { label: string; href: string }> = {
  portfolio: { label: '作品集', href: '/portfolio' },
  case_studies: { label: '案例', href: '/case-studies' },
  pricing: { label: '價目', href: '/pricing' },
  faq: { label: '常見問題', href: '/faq' },
  newsletter: { label: '電子報', href: '/newsletter' },
};

// 舊六頁範例保持相容；新工作區由設定明確列出已選頁面。
export const hasPage = (page: string) => (site.pages.required ?? ['home', 'about', 'services', 'blog', 'contact', 'not_found']).includes(page);
const enabledLink = (link: { href: string }) => {
  const page = link.href.split('/')[1];
  return !['about', 'services', 'blog', 'contact', 'rss.xml'].includes(page) || hasPage(page === 'rss.xml' ? 'blog' : page);
};
export const navLinks = [
  { label: '首頁', href: '/' },
  { label: '關於', href: '/about' },
  { label: '服務', href: '/services' },
  { label: '文章', href: '/blog' },
  ...site.pages.optional.map((page) => optionalLabels[page]).filter(Boolean),
  { label: '聯絡', href: '/contact' },
].filter(enabledLink);

export const footerLinks = [
  { label: '關於', href: '/about' },
  { label: '服務', href: '/services' },
  { label: '文章', href: '/blog' },
  { label: '聯絡', href: '/contact' },
  { label: 'RSS', href: '/rss.xml' },
].filter(enabledLink);

export const ctaHref = site.cta.kind === 'form_later' ? '/contact' : site.cta.target ?? (hasPage('contact') ? '/contact' : '/');
export const ctaExternal = site.cta.kind === 'external_link';
export const ctaAttrs = ctaExternal ? { target: '_blank', rel: 'noopener noreferrer' } : {};
