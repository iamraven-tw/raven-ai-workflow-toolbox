/**
 * 正常測試：建立兩筆當月假資料並更新月度統計。
 * 執行前必須先完成 MONTHLY_BUDGET 設定。
 */
function testExpenseTrackerNormal() {
  logExpenseTracker_('開始', '準備執行家庭支出記錄表正常測試');

  try {
    checkExpenseTrackerSettings();
    setupExpenseTracker();
    var added = ensureExpenseTestFixtures_();
    updateMonthlySummary();
    logExpenseTracker_('成功', '正常測試通過｜本次新增教學假資料=' + added);
  } catch (error) {
    logExpenseTrackerError_('正常測試失敗｜原因：' + error.message);
    throw error;
  }
}

/**
 * 錯誤測試：確認非數字金額會被拒絕，且不寫入工作表。
 */
function testExpenseTrackerInvalidAmount() {
  logExpenseTracker_('開始', '準備執行非數字金額錯誤測試');

  var timeZone = Session.getScriptTimeZone();
  var monthKey = Utilities.formatDate(new Date(), timeZone, 'yyyy-MM');
  var invalidRows = [[new Date(), '教學測試-錯誤金額', '其他', '不是數字', '現金', '只在記憶體測試']];

  try {
    summarizeExpenses_(invalidRows, monthKey, timeZone);
  } catch (error) {
    if (error.message.indexOf('金額必須是') !== -1) {
      logExpenseTracker_('成功', '錯誤測試通過｜非數字金額已在寫入前被拒絕');
      return;
    }
    logExpenseTrackerError_('錯誤測試收到非預期結果｜原因：' + error.message);
    throw error;
  }

  var unexpectedError = new Error('錯誤測試失敗：非數字金額沒有被拒絕。');
  logExpenseTrackerError_(unexpectedError.message);
  throw unexpectedError;
}

/**
 * 重複執行測試：確認工作表與固定教學假資料不會重複。
 * 執行前必須先完成 MONTHLY_BUDGET 設定。
 */
function testExpenseTrackerRepeat() {
  logExpenseTracker_('開始', '準備執行家庭支出記錄表重複測試');

  try {
    checkExpenseTrackerSettings();
    setupExpenseTracker();
    ensureExpenseTestFixtures_();
    var beforeCount = countExpenseTestFixtures_();

    setupExpenseTracker();
    var addedOnRepeat = ensureExpenseTestFixtures_();
    updateMonthlySummary();
    var afterCount = countExpenseTestFixtures_();

    if (beforeCount !== 2 || afterCount !== 2 || addedOnRepeat !== 0) {
      throw new Error('教學假資料重跑後出現重複，預期固定維持 2 筆。');
    }

    logExpenseTracker_('成功', '重複測試通過｜工作表與 2 筆教學假資料皆未重複');
  } catch (error) {
    logExpenseTrackerError_('重複測試失敗｜原因：' + error.message);
    throw error;
  }
}

/**
 * 寫入固定的當月教學假資料；已存在時安全略過。
 *
 * @return {number} 本次新增筆數。
 */
function ensureExpenseTestFixtures_() {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = spreadsheet.getSheetByName(EXPENSE_TRACKER_CONFIG_.expenseSheetName);
  if (!sheet) {
    throw new Error('找不到支出紀錄工作表，請先執行 setupExpenseTracker。');
  }

  var existingItems = {};
  readExpenseRows_(sheet).forEach(function (row) {
    if (row[5] === EXPENSE_TRACKER_CONFIG_.fixtureNote) {
      existingItems[String(row[1])] = true;
    }
  });

  var now = new Date();
  var fixtures = [
    [new Date(now.getFullYear(), now.getMonth(), 5), '教學測試-午餐', '餐飲', 120, '現金', EXPENSE_TRACKER_CONFIG_.fixtureNote],
    [new Date(now.getFullYear(), now.getMonth(), 8), '教學測試-交通', '交通', 60, '電子支付', EXPENSE_TRACKER_CONFIG_.fixtureNote]
  ];
  var missing = fixtures.filter(function (row) {
    return !existingItems[row[1]];
  });

  if (missing.length === 0) {
    logExpenseTracker_('略過', '2 筆教學假資料已存在');
    return 0;
  }

  sheet.getRange(sheet.getLastRow() + 1, 1, missing.length, EXPENSE_TRACKER_CONFIG_.expenseHeaders.length)
    .setValues(missing);
  logExpenseTracker_('進度', '已新增教學假資料筆數=' + missing.length);
  return missing.length;
}

/**
 * 計算固定教學假資料筆數，不輸出任何使用者資料。
 *
 * @return {number} 教學假資料筆數。
 */
function countExpenseTestFixtures_() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet()
    .getSheetByName(EXPENSE_TRACKER_CONFIG_.expenseSheetName);
  if (!sheet) {
    return 0;
  }

  return readExpenseRows_(sheet).filter(function (row) {
    return row[5] === EXPENSE_TRACKER_CONFIG_.fixtureNote;
  }).length;
}
