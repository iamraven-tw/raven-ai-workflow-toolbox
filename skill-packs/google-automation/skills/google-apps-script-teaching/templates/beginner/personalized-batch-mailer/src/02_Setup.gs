/**
 * 建立個人化批次郵件寄送器需要的工作表與欄位。
 * 重複執行不會新增重複工作表或覆寫既有資料。
 */
function setupPersonalizedBatchMailer() {
  logBatchMailer_('開始', '準備建立個人化批次郵件寄送器');

  try {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    if (!spreadsheet) {
      throw new Error('找不到目前綁定的 Google Sheets，請從練習試算表開啟 Apps Script。');
    }

    var sheet = getOrCreateBatchMailerSheet_(spreadsheet);
    ensureBatchMailerHeaders_(sheet);

    logBatchMailer_('設定', '本案例沒有必要的指令碼屬性');
    logBatchMailer_('成功', '已建立待寄郵件工作表與 7 個欄位');
  } catch (error) {
    logBatchMailerError_('建立個人化批次郵件寄送器失敗｜原因：' + error.message);
    throw error;
  }
}

/**
 * 取得或建立待寄郵件工作表。
 *
 * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} spreadsheet 目前試算表。
 * @return {GoogleAppsScript.Spreadsheet.Sheet} 待寄郵件工作表。
 */
function getOrCreateBatchMailerSheet_(spreadsheet) {
  var existing = spreadsheet.getSheetByName(BATCH_MAILER_CONFIG_.sheetName);
  if (existing) {
    logBatchMailer_('略過', '待寄郵件工作表已存在');
    return existing;
  }

  var sheets = spreadsheet.getSheets();
  if (
    sheets.length === 1 &&
    sheets[0].getLastRow() === 0 &&
    sheets[0].getLastColumn() === 0
  ) {
    sheets[0].setName(BATCH_MAILER_CONFIG_.sheetName);
    logBatchMailer_('進度', '已將空白預設工作表設定為待寄郵件');
    return sheets[0];
  }

  logBatchMailer_('進度', '正在建立待寄郵件工作表');
  return spreadsheet.insertSheet(BATCH_MAILER_CONFIG_.sheetName);
}

/**
 * 建立或驗證欄位。只有第一次建立版面時才設定初始欄寬。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 待寄郵件工作表。
 */
function ensureBatchMailerHeaders_(sheet) {
  var headers = BATCH_MAILER_CONFIG_.headers;
  var existing = sheet.getRange(1, 1, 1, headers.length).getValues()[0];
  var isEmpty = existing.every(function (value) {
    return value === '';
  });

  if (isEmpty) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
    sheet.setFrozenRows(1);
    sheet.setColumnWidths(1, 2, 160);
    sheet.setColumnWidth(3, 220);
    sheet.setColumnWidth(4, 360);
    sheet.setColumnWidths(5, 3, 150);
    sheet.getRange('F:F').setNumberFormat('yyyy-MM-dd HH:mm:ss');
    return;
  }

  var matches = headers.every(function (header, index) {
    return existing[index] === header;
  });
  if (!matches) {
    throw new Error('第一列欄位與教材不同，為避免覆寫資料已停止。');
  }
}
