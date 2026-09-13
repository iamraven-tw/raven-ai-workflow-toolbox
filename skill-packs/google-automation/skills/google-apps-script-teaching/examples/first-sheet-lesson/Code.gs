/**
 * 檢查第 1 課是否需要 Script Properties。
 */
function checkLesson01Settings() {
  console.info('[開始] 準備檢查第 1 課設定');
  console.info(
    '[設定] 本課不需要 Script Properties｜未在程式中硬寫私人 ID 或秘密',
  );
  return true;
}

/**
 * 建立第一個 Google Sheets 自動化練習。
 *
 * 重複執行時會重設同一張練習工作表，因此不會一直新增重複資料。
 */
function setupLessonSheet() {
  return setupLessonSheet_(
    '活動報名資料',
    getLesson01LearnerEmail_(),
  );
}

/**
 * 執行第 1 課正常案例。
 */
function testLesson01Normal() {
  console.info('[開始] 執行第 1 課正常測試');
  checkLesson01Settings();
  const result = setupLessonSheet();
  assertLesson01_(result.dataRowCount === 2, '正常測試應產生兩筆假資料');
  console.info('[成功] 第 1 課正常測試通過｜資料筆數=2');
}

/**
 * 執行第 1 課錯誤案例，不碰觸真實工作表內容。
 */
function testLesson01Error() {
  console.info('[開始] 執行第 1 課錯誤測試');

  try {
    setupLessonSheet_('   ', 'learner@example.com');
  } catch (error) {
    console.info('[成功] 第 1 課錯誤測試通過｜空白名稱已被拒絕');
    return;
  }

  throw new Error('錯誤測試失敗：空白工作表名稱沒有被拒絕');
}

/**
 * 執行第 1 課重複測試。
 */
function testLesson01Repeat() {
  console.info('[開始] 執行第 1 課重複測試');
  setupLessonSheet();
  const secondResult = setupLessonSheet();
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = spreadsheet.getSheetByName('活動報名資料');

  assertLesson01_(sheet !== null, '找不到活動報名資料工作表');
  assertLesson01_(sheet.getLastRow() === 3, '重複執行後資料列數不是三列');
  assertLesson01_(
    secondResult.dataRowCount === 2,
    '重複執行後假資料不是兩筆',
  );
  console.info('[成功] 第 1 課重複測試通過｜沒有新增重複資料');
}

/**
 * 建立或更新指定的練習工作表。
 *
 * @param {string} sheetName 工作表名稱。
 * @param {string} learnerEmail 目前執行者的 Google 帳號 Email。
 * @return {{dataRowCount: number, changed: boolean}} 執行結果。
 */
function setupLessonSheet_(sheetName, learnerEmail) {
  console.info(`[開始] 準備建立活動報名資料工作表｜名稱=${sheetName}`);

  try {
    validateLesson01SheetName_(sheetName);

    // 取得這個綁定型 Apps Script 專案所屬的試算表。
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();

    // 優先沿用既有工作表；找不到時才建立新的工作表。
    const sheet =
      spreadsheet.getSheetByName(sheetName) ||
      spreadsheet.insertSheet(sheetName);

    const values = [
      ['姓名', 'Email', '活動場次', '處理狀態'],
      ['小明', learnerEmail, '上午場', '待處理'],
      ['小美', learnerEmail, '下午場', '待處理'],
    ];

    if (lesson01SheetMatches_(sheet, values)) {
      console.info(
        '[略過] 工作表已符合本課內容｜沒有新增重複資料',
      );
      return { dataRowCount: values.length - 1, changed: false };
    }

    // 只清除 A 到 D 欄的既有教學內容，避免影響其他欄位。
    const rowsToClear = Math.max(sheet.getLastRow(), values.length);
    sheet.getRange(1, 1, rowsToClear, values[0].length).clearContent();

    // 一次寫入二維陣列，讓重複執行得到相同結果。
    sheet.getRange(1, 1, values.length, values[0].length).setValues(values);

    console.info(
      `[成功] 已完成活動報名資料工作表｜資料筆數=${values.length - 1}`,
    );
    return { dataRowCount: values.length - 1, changed: true };
  } catch (error) {
    // 加上中文脈絡後再拋出，讓執行記錄保留可診斷的錯誤。
    const message = error instanceof Error ? error.message : String(error);
    console.error(
      `[失敗] 無法建立活動報名資料工作表｜原因=${message}｜未寫入任何資料`,
    );
    throw error;
  }
}

/**
 * 取得目前執行者的 Google 帳號 Email。
 *
 * 實際地址只寫入學員自己的試算表，不輸出到紀錄檔(Log)。
 *
 * @return {string} 已驗證的 Email。
 */
function getLesson01LearnerEmail_() {
  const user = Session.getEffectiveUser();
  const email = String(
    user && typeof user.getEmail === 'function' ? user.getEmail() : '',
  )
    .trim()
    .toLowerCase();
  if (!/^[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+$/.test(email)) {
    throw new Error(
      '無法取得目前執行者的 Google 帳號 Email｜請重新授權後再試',
    );
  }
  return email;
}

/**
 * 驗證工作表名稱，並在任何 Sheets 寫入前阻擋錯誤輸入。
 *
 * @param {string} sheetName 工作表名稱。
 */
function validateLesson01SheetName_(sheetName) {
  if (typeof sheetName !== 'string' || sheetName.trim() === '') {
    throw new Error('工作表名稱不可空白');
  }
}

/**
 * 檢查目前 A 到 D 欄是否已符合本課內容。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 工作表。
 * @param {Array<Array<string>>} expectedValues 預期二維陣列。
 * @return {boolean} 是否完全相符。
 */
function lesson01SheetMatches_(sheet, expectedValues) {
  if (sheet.getLastRow() !== expectedValues.length) {
    return false;
  }

  const actualValues = sheet
    .getRange(1, 1, expectedValues.length, expectedValues[0].length)
    .getDisplayValues();
  return JSON.stringify(actualValues) === JSON.stringify(expectedValues);
}

/**
 * 提供不依賴外部測試框架的最小斷言。
 *
 * @param {boolean} condition 是否符合預期。
 * @param {string} message 失敗時的繁體中文訊息。
 */
function assertLesson01_(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}
