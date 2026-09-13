/** 家庭支出記錄表的固定名稱與欄位。 */
var EXPENSE_TRACKER_CONFIG_ = {
  expenseSheetName: '支出紀錄',
  summarySheetName: '月度統計',
  monthlyBudgetProperty: 'MONTHLY_BUDGET',
  expenseHeaders: ['日期', '支出項目', '分類', '金額', '付款方式', '備註'],
  fixtureNote: '教學測試資料'
};

/**
 * 開啟試算表時建立操作選單。
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('支出工具')
    .addItem('更新本月統計', 'updateMonthlySummary')
    .addToUi();
}

/**
 * 建立家庭支出記錄表需要的工作表、欄位與自訂選單。
 * 重複執行不會新增重複工作表或標題列。
 */
function setupExpenseTracker() {
  logExpenseTracker_('開始', '準備建立家庭支出記錄表');

  try {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    if (!spreadsheet) {
      throw new Error('找不到目前綁定的 Google Sheets，請從練習試算表開啟 Apps Script。');
    }

    var expenseSheet = getOrCreateSheet_(spreadsheet, EXPENSE_TRACKER_CONFIG_.expenseSheetName);
    ensureExpenseHeaders_(expenseSheet);
    prepareSummarySheet_(spreadsheet);
    onOpen();

    logExpenseTracker_('設定', '本步驟沒有必要的指令碼屬性');
    logExpenseTracker_('成功', '已建立支出紀錄、月度統計與支出工具選單');
  } catch (error) {
    logExpenseTrackerError_('建立家庭支出記錄表失敗｜原因：' + error.message);
    throw error;
  }
}

/**
 * 檢查本月預算設定，不輸出實際值。
 *
 * @return {number} 經驗證的本月預算。
 */
function checkExpenseTrackerSettings() {
  logExpenseTracker_('開始', '準備檢查家庭支出記錄表設定');

  try {
    var budget = readMonthlyBudget_();
    logExpenseTracker_('設定', 'MONTHLY_BUDGET 已設定且格式正確');
    logExpenseTracker_('成功', '家庭支出記錄表設定檢查通過');
    return budget;
  } catch (error) {
    logExpenseTrackerError_('設定檢查未通過｜原因：' + error.message);
    throw error;
  }
}

/**
 * 依目前月份更新月度統計。
 */
function updateMonthlySummary() {
  logExpenseTracker_('開始', '準備更新本月支出統計');

  try {
    var budget = readMonthlyBudget_();
    logExpenseTracker_('設定', 'MONTHLY_BUDGET 已設定且格式正確');

    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var expenseSheet = spreadsheet.getSheetByName(EXPENSE_TRACKER_CONFIG_.expenseSheetName);
    var summarySheet = spreadsheet.getSheetByName(EXPENSE_TRACKER_CONFIG_.summarySheetName);
    if (!expenseSheet || !summarySheet) {
      throw new Error('找不到必要工作表，請先執行 setupExpenseTracker。');
    }

    var rows = readExpenseRows_(expenseSheet);
    var timeZone = Session.getScriptTimeZone();
    var monthKey = Utilities.formatDate(new Date(), timeZone, 'yyyy-MM');
    var summary = summarizeExpenses_(rows, monthKey, timeZone);

    writeMonthlySummary_(summarySheet, monthKey, budget, summary);
    logExpenseTracker_('成功', '已更新本月統計｜有效筆數=' + summary.count + '｜略過空白筆數=' + summary.skipped);
  } catch (error) {
    logExpenseTrackerError_('更新本月統計失敗｜原因：' + error.message);
    throw error;
  }
}

/**
 * 取得或建立指定工作表。
 *
 * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} spreadsheet 目前試算表。
 * @param {string} name 工作表名稱。
 * @return {GoogleAppsScript.Spreadsheet.Sheet} 工作表。
 */
function getOrCreateSheet_(spreadsheet, name) {
  var sheet = spreadsheet.getSheetByName(name);
  if (sheet) {
    logExpenseTracker_('略過', name + ' 工作表已存在');
    return sheet;
  }

  // 第一個教學步驟直接沿用唯一的空白預設工作表，避免留下多餘分頁。
  var sheets = spreadsheet.getSheets();
  if (
    name === EXPENSE_TRACKER_CONFIG_.expenseSheetName &&
    sheets.length === 1 &&
    sheets[0].getLastRow() === 0 &&
    sheets[0].getLastColumn() === 0
  ) {
    sheets[0].setName(name);
    logExpenseTracker_('進度', '已將空白預設工作表設定為 ' + name);
    return sheets[0];
  }

  logExpenseTracker_('進度', '正在建立 ' + name + ' 工作表');
  return spreadsheet.insertSheet(name);
}

/**
 * 建立或驗證支出紀錄標題列，不覆寫不相符的既有欄位。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 支出紀錄工作表。
 */
function ensureExpenseHeaders_(sheet) {
  var headers = EXPENSE_TRACKER_CONFIG_.expenseHeaders;
  var existing = sheet.getRange(1, 1, 1, headers.length).getValues()[0];
  var isEmpty = existing.every(function (value) {
    return value === '';
  });

  if (isEmpty) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.setFrozenRows(1);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
    sheet.autoResizeColumns(1, headers.length);
    return;
  }

  var matches = headers.every(function (header, index) {
    return existing[index] === header;
  });
  if (!matches) {
    throw new Error('支出紀錄的第一列欄位與教材不同，為避免覆寫資料已停止。');
  }
}

/**
 * 建立月度統計的初始說明。
 *
 * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} spreadsheet 目前試算表。
 */
function prepareSummarySheet_(spreadsheet) {
  var sheet = getOrCreateSheet_(spreadsheet, EXPENSE_TRACKER_CONFIG_.summarySheetName);
  if (sheet.getRange('A1').getValue() === '') {
    sheet.getRange('A1:B2').setValues([
      ['家庭支出月度統計', '尚未更新'],
      ['操作方式', '設定 MONTHLY_BUDGET 後執行 updateMonthlySummary']
    ]);
    sheet.getRange('A1:A2').setFontWeight('bold');
    sheet.autoResizeColumns(1, 2);
  }
}

/**
 * 讀取並驗證 MONTHLY_BUDGET。
 *
 * @return {number} 本月預算。
 */
function readMonthlyBudget_() {
  var rawValue = PropertiesService.getScriptProperties()
    .getProperty(EXPENSE_TRACKER_CONFIG_.monthlyBudgetProperty);
  return parseMonthlyBudget_(rawValue);
}

/**
 * 驗證預算格式，讓純邏輯可以在本機測試。
 *
 * @param {string|null} rawValue 指令碼屬性原始值。
 * @return {number} 有效預算。
 */
function parseMonthlyBudget_(rawValue) {
  if (rawValue === null || String(rawValue).trim() === '') {
    throw new Error('缺少 MONTHLY_BUDGET，請到專案設定的指令碼屬性新增後再執行。');
  }

  var budget = Number(rawValue);
  if (!Number.isFinite(budget) || budget < 0) {
    throw new Error('MONTHLY_BUDGET 必須是大於或等於 0 的數字。');
  }

  return budget;
}

/**
 * 讀取支出紀錄的資料列。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 支出紀錄工作表。
 * @return {Array<Array<*>>} 不含標題列的資料。
 */
function readExpenseRows_(sheet) {
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    return [];
  }

  return sheet.getRange(2, 1, lastRow - 1, EXPENSE_TRACKER_CONFIG_.expenseHeaders.length).getValues();
}

/**
 * 彙整指定月份支出；遇到格式錯誤時在寫入前停止。
 *
 * @param {Array<Array<*>>} rows 支出資料列。
 * @param {string} monthKey 目標月份，格式為 yyyy-MM。
 * @param {string} timeZone Apps Script 專案時區。
 * @return {{total:number,count:number,skipped:number,categories:Object<string,number>}} 統計結果。
 */
function summarizeExpenses_(rows, monthKey, timeZone) {
  var summary = {
    total: 0,
    count: 0,
    skipped: 0,
    categories: {}
  };

  rows.forEach(function (row, index) {
    var isBlank = row.every(function (value) {
      return value === '';
    });
    if (isBlank) {
      summary.skipped += 1;
      return;
    }

    var rowNumber = index + 2;
    var dateValue = row[0];
    var item = String(row[1] || '').trim();
    var category = String(row[2] || '').trim();
    var rawAmount = row[3];
    var amount = Number(rawAmount);

    if (!(dateValue instanceof Date) || Number.isNaN(dateValue.getTime())) {
      throw new Error('第 ' + rowNumber + ' 列的日期不是有效日期。');
    }
    if (item === '') {
      throw new Error('第 ' + rowNumber + ' 列缺少支出項目。');
    }
    if (category === '') {
      throw new Error('第 ' + rowNumber + ' 列缺少分類。');
    }
    if (rawAmount === '' || !Number.isFinite(amount) || amount < 0) {
      throw new Error('第 ' + rowNumber + ' 列的金額必須是大於或等於 0 的數字。');
    }

    var rowMonth = Utilities.formatDate(dateValue, timeZone, 'yyyy-MM');
    if (rowMonth !== monthKey) {
      return;
    }

    summary.total += amount;
    summary.count += 1;
    summary.categories[category] = (summary.categories[category] || 0) + amount;
  });

  return summary;
}

/**
 * 將統計結果一次寫回月度統計工作表。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 月度統計工作表。
 * @param {string} monthKey 目標月份。
 * @param {number} budget 本月預算。
 * @param {{total:number,count:number,skipped:number,categories:Object<string,number>}} summary 統計結果。
 */
function writeMonthlySummary_(sheet, monthKey, budget, summary) {
  var remaining = budget - summary.total;
  var status = remaining >= 0 ? '預算內' : '已超支';
  var categoryRows = Object.keys(summary.categories)
    .sort()
    .map(function (category) {
      return [category, summary.categories[category]];
    });

  sheet.clearContents();
  sheet.getRange('A1:B6').setValues([
    ['統計月份', monthKey],
    ['本月總支出', summary.total],
    ['每月預算', budget],
    ['剩餘預算', remaining],
    ['預算狀態', status],
    ['有效支出筆數', summary.count]
  ]);
  sheet.getRange('A1:A6').setFontWeight('bold');

  sheet.getRange('A8:B8').setValues([['分類', '支出金額']]).setFontWeight('bold');
  if (categoryRows.length > 0) {
    sheet.getRange(9, 1, categoryRows.length, 2).setValues(categoryRows);
  } else {
    sheet.getRange('A9:B9').setValues([['本月尚無支出', 0]]);
  }

  sheet.getRange('B2:B4').setNumberFormat('#,##0.00');
  // 更新統計時只改內容與格式，保留使用者手動設定的欄寬。
}
