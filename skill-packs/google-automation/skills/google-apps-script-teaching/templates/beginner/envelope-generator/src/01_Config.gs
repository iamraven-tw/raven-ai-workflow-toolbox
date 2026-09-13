/** 批次信封版面產生器的固定設定。 */
var ENVELOPE_CONFIG_ = {
  spreadsheetProperty: 'SPREADSHEET_ID',
  outputDocumentProperty: 'ENVELOPE_DOCUMENT_ID',
  senderSheetName: '寄件人設定',
  recipientSheetName: '收件人清單',
  resultSheetName: '產生結果',
  senderHeaders: ['設定項目', '值'],
  senderKeys: ['寄件人名稱', '寄件人地址', '版面方向'],
  recipientHeaders: ['是否產生', '收件人名稱', '收件人地址', '備註'],
  resultHeaders: ['最後更新時間', '文件連結', '頁數', '略過筆數'],
  fixtureNote: '教學測試資料',
  normalTestPageCount: 5
};

/**
 * 檢查必要設定，不輸出實際 ID。
 *
 * @return {GoogleAppsScript.Spreadsheet.Spreadsheet} 練習試算表。
 */
function checkEnvelopeSettings() {
  logEnvelope_('開始', '準備檢查批次信封版面產生器設定');

  try {
    var spreadsheet = openEnvelopeSpreadsheet_();
    logEnvelope_('設定', 'SPREADSHEET_ID 已設定且可以開啟');
    logEnvelope_('成功', '批次信封版面產生器設定檢查通過');
    return spreadsheet;
  } catch (error) {
    logEnvelopeError_('設定檢查未通過｜原因：' + error.message);
    throw error;
  }
}

/**
 * 從指令碼屬性開啟資料試算表。
 *
 * @return {GoogleAppsScript.Spreadsheet.Spreadsheet} 練習試算表。
 */
function openEnvelopeSpreadsheet_() {
  var spreadsheetId = PropertiesService.getScriptProperties()
    .getProperty(ENVELOPE_CONFIG_.spreadsheetProperty);
  var normalizedId = normalizeSpreadsheetId_(spreadsheetId);

  try {
    return SpreadsheetApp.openById(normalizedId);
  } catch (error) {
    throw new Error('SPREADSHEET_ID 無法開啟，請確認設定值與目前帳號權限。');
  }
}

/**
 * 驗證試算表 ID，讓純邏輯可以在本機測試。
 *
 * @param {string|null} rawValue 指令碼屬性原始值。
 * @return {string} 去除空白後的 ID。
 */
function normalizeSpreadsheetId_(rawValue) {
  var value = rawValue === null ? '' : String(rawValue).trim();
  if (value === '') {
    throw new Error('缺少 SPREADSHEET_ID，請到專案設定的指令碼屬性新增後再執行。');
  }
  return value;
}
