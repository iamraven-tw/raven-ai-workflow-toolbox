const COURSE_PROPERTY_NAMES_ = Object.freeze({
  spreadsheetId: 'SPREADSHEET_ID',
  formId: 'FORM_ID',
});

/**
 * 取得目前專案的集中式設定。
 *
 * 實際值只存在 Apps Script 的指令碼屬性，不會寫入程式、紀錄檔(Log)或 Git。
 *
 * @return {{spreadsheetId: string, formId: string}} 已正規化的設定。
 */
function getScriptConfig_() {
  const properties = PropertiesService.getScriptProperties().getProperties();
  return {
    spreadsheetId: normalizeLesson02Setting_(
      properties[COURSE_PROPERTY_NAMES_.spreadsheetId],
    ),
    formId: normalizeLesson02Setting_(
      properties[COURSE_PROPERTY_NAMES_.formId],
    ),
  };
}

/**
 * 學生入口：檢查門牌號碼是否存在，且與目前綁定的試算表相符。
 *
 * 這個函式只讀取設定與檔案資訊，不修改指令碼屬性或工作表資料。
 *
 * @return {boolean} 設定是否通過檢查。
 */
function checkLesson02Settings() {
  writeLessonLog_('開始', '準備檢查第 2 課設定');

  try {
    openCourseSpreadsheet_();
    writeLesson02SettingsLog_(true);
    writeLessonLog_('成功', '設定與目前綁定的練習試算表相符');
    return true;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const isMissing = message.includes('缺少必要的指令碼屬性');
    writeLesson02SettingsLog_(!isMissing);
    writeLessonLog_('失敗', `${message}｜未執行資料寫入`);
    throw error;
  }
}

/**
 * Agent 工程測試：正常設定應通過必要欄位與綁定試算表比對。
 */
function testLesson02Normal() {
  writeLessonLog_('開始', '執行第 2 課正常測試');

  const config = { spreadsheetId: 'test-bound-spreadsheet-id' };
  validateRequiredProperties_(config);
  validateCourseSpreadsheetMatch_(
    config.spreadsheetId,
    'test-bound-spreadsheet-id',
  );

  writeLessonLog_('成功', '第 2 課正常測試通過｜設定值未輸出');
}

/**
 * Agent 工程測試：缺少設定時必須在任何資料寫入前停止。
 */
function testLesson02MissingSetting() {
  writeLessonLog_('開始', '執行第 2 課缺少設定測試');

  try {
    validateRequiredProperties_({ spreadsheetId: '' });
  } catch (error) {
    writeLessonLog_('成功', '缺少設定測試通過｜資料尚未寫入');
    return;
  }

  throw new Error('缺少設定測試失敗：空白設定沒有被拒絕');
}

/**
 * Agent 工程測試：填入其他試算表的門牌號碼時必須停止。
 */
function testLesson02WrongSpreadsheet() {
  writeLessonLog_('開始', '執行第 2 課錯誤門牌號碼測試');

  try {
    validateCourseSpreadsheetMatch_(
      'test-other-spreadsheet-id',
      'test-bound-spreadsheet-id',
    );
  } catch (error) {
    writeLessonLog_('成功', '錯誤門牌號碼測試通過｜資料尚未寫入');
    return;
  }

  throw new Error('錯誤門牌號碼測試失敗：不相符設定沒有被拒絕');
}

/**
 * Agent 工程測試：重複檢查不會改變設定或工作表資料。
 */
function testLesson02Repeat() {
  writeLessonLog_('開始', '執行第 2 課重複檢查測試');

  const config = Object.freeze({
    spreadsheetId: 'test-bound-spreadsheet-id',
  });
  validateRequiredProperties_(config);
  validateCourseSpreadsheetMatch_(
    config.spreadsheetId,
    'test-bound-spreadsheet-id',
  );
  validateRequiredProperties_(config);
  validateCourseSpreadsheetMatch_(
    config.spreadsheetId,
    'test-bound-spreadsheet-id',
  );

  writeLessonLog_('略過', '設定已驗證｜重複檢查不會改變資料');
}

/**
 * 只用目前綁定的試算表，避免為了門牌號碼擴大 OAuth 權限。
 *
 * @return {GoogleAppsScript.Spreadsheet.Spreadsheet} 已通過設定比對的試算表。
 */
function openCourseSpreadsheet_() {
  const config = getScriptConfig_();
  validateRequiredProperties_(config);

  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  if (!spreadsheet) {
    throw new Error('目前專案沒有綁定可使用的 Google Sheets');
  }

  validateCourseSpreadsheetMatch_(config.spreadsheetId, spreadsheet.getId());
  return spreadsheet;
}

/**
 * 驗證必要設定是否存在。
 *
 * @param {{spreadsheetId: string}} config 要檢查的設定。
 * @return {boolean} 是否通過檢查。
 */
function validateRequiredProperties_(config) {
  if (!config || normalizeLesson02Setting_(config.spreadsheetId) === '') {
    throw new Error(
      `缺少必要的指令碼屬性｜名稱=${COURSE_PROPERTY_NAMES_.spreadsheetId}`,
    );
  }
  return true;
}

/**
 * 驗證設定指向目前綁定的試算表，不在錯誤檔案上繼續工作。
 *
 * @param {*} configuredId 指令碼屬性中的預期門牌號碼。
 * @param {*} boundId 目前綁定試算表的門牌號碼。
 * @return {boolean} 是否相符。
 */
function validateCourseSpreadsheetMatch_(configuredId, boundId) {
  const expected = normalizeLesson02Setting_(configuredId);
  const actual = normalizeLesson02Setting_(boundId);

  if (expected === '' || actual === '' || expected !== actual) {
    throw new Error('SPREADSHEET_ID 與目前綁定的練習試算表不相符');
  }
  return true;
}

/**
 * 只顯示設定狀態，不輸出實際門牌號碼。
 *
 * @param {boolean} isConfigured 是否已設定。
 */
function writeLesson02SettingsLog_(isConfigured) {
  writeLessonLog_(
    '設定',
    `SPREADSHEET_ID=${isConfigured ? '已設定' : '未設定'}｜實際值不顯示`,
  );
}

/**
 * 將設定值轉成可穩定檢查的字串。
 *
 * @param {*} value 原始設定值。
 * @return {string} 去除前後空白後的設定值。
 */
function normalizeLesson02Setting_(value) {
  return String(value || '').trim();
}
