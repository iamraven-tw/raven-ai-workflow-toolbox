// 手機選單開合：所有主題共用同一段行為，只要按鈕 id 為 mobile-menu-button、選單 id 為 mobile-menu。
const button = document.getElementById('mobile-menu-button');
const menu = document.getElementById('mobile-menu');
button?.addEventListener('click', () => {
  const open = menu?.classList.toggle('hidden') === false;
  button.setAttribute('aria-expanded', String(open));
  button.setAttribute('aria-label', open ? '關閉選單' : '開啟選單');
});
