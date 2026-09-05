// 站點設定：所有品牌、文案、聯絡資訊與主題都從這裡讀取。
// 這份檔案的內容全部是虛構佔位；website-build 會依 website/config.json 重新產生。
// 不要把 API Token、帳號識別碼或任何秘密寫進這裡。

/** @type {import('./src/site-config').SiteConfig} */
export const site = {
  url: 'https://example.invalid',
  theme: 'bookshop',
  fonts: 'google',
  name: '範例工作室',
  positioning: '幫小型團隊把重複的工作交給自動化流程',
  audience: '沒有技術團隊、想把時間留給核心工作的一人公司與小型工作室',
  language: 'zh-TW',
  offerings: [
    { name: '流程盤點諮詢', summary: '一次會談找出最值得自動化的三個流程，並給出可執行的順序。' },
    { name: '自動化建置', summary: '把盤點結果做成實際運作的流程，交付時附操作說明與維護方式。' },
    { name: '每月維護', summary: '定期檢查流程是否正常，並依需求調整。' },
  ],
  trustSignals: ['虛構的三年顧問經驗', '虛構的二十個完成案例'],
  cta: { kind: 'mailto', label: '寫信討論', target: 'mailto:hello@example.invalid' },
  contacts: [
    { kind: 'email', label: 'Email', target: 'mailto:hello@example.invalid' },
  ],
  pages: { optional: [] },
  indexing: 'noindex',
};
