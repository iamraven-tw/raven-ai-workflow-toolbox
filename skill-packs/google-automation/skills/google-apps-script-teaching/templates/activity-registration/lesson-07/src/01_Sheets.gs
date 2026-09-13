const LESSON01_CONFIG_ = Object.freeze({
  sheetName: '活動報名資料',
  headers: ['姓名', 'Email', '活動場次', '處理狀態'],
  fixtureDefinitions: [
    ['小明', '上午場'],
    ['小美', '下午場'],
  ],
  legacyFixtureEmails: Object.freeze({
    小明: 'xiaoming@example.com',
    小美: 'xiaomei@example.com',
  }),
  initialColumnWidths: [120, 240, 110, 110],
});

/**
 * 保留第 1 課設定檢查入口，並改用目前累積課程的設定規則。
 *
 * @return {boolean} 本課設定是否可繼續。
 */
function checkLesson01Settings() {
  return checkLesson02Settings();
}

/**
 * 建立或安全更新「活動報名資料」工作表。
 *
 * 學生只需要從 Sheets 的「活動報名工具」選單執行這個入口。
 *
 * @return {{
 *   changed: boolean,
 *   created: boolean,
 *   dataRowCount: number,
 *   insertedCount: number,
 *   updatedCount: number
 * }} 執行結果。
 */
function setupLessonSheet() {
  const learnerEmail = getLesson01LearnerEmail_();
  const fixtureRows = buildLesson01FixtureRows_(learnerEmail);
  return setupLessonSheet_(LESSON01_CONFIG_.sheetName, fixtureRows);
}

/**
 * Agent 工程測試：驗證空白資料可以產生完整表頭與兩筆假資料。
 */
function testLesson01Normal() {
  writeLessonLog_('開始', '執行第 1 課正常測試');

  const fixtureRows = buildLesson01FixtureRows_('learner@example.com');
  const plan = planLesson01Rows_([], fixtureRows);
  const expected = buildLesson01ExpectedValues_(fixtureRows);

  assertLesson01_(
    JSON.stringify(plan.finalValues) === JSON.stringify(expected),
    '正常測試沒有產生預期的表頭與兩筆假資料',
  );
  assertLesson01_(plan.insertedCount === 2, '正常測試應新增兩筆假資料');

  writeLessonLog_('成功', '第 1 課正常測試通過｜資料筆數=2');
}

/**
 * Agent 工程測試：驗證錯誤輸入會在任何 Sheets 寫入前停止。
 */
function testLesson01Error() {
  writeLessonLog_('開始', '執行第 1 課錯誤測試');

  try {
    validateLesson01SheetName_('   ');
  } catch (error) {
    writeLessonLog_('成功', '第 1 課錯誤測試通過｜空白名稱已被拒絕');
    return;
  }

  throw new Error('錯誤測試失敗：空白工作表名稱沒有被拒絕');
}

/**
 * Agent 工程測試：驗證重複處理不會新增重複資料或刪除既有資料。
 */
function testLesson01Repeat() {
  writeLessonLog_('開始', '執行第 1 課重複測試');

  const existingRows = [
    LESSON01_CONFIG_.headers.slice(),
    ['王小華', 'wang@example.com', '上午場', '自行保留'],
  ];
  const fixtureRows = buildLesson01FixtureRows_('learner@example.com');
  const firstPlan = planLesson01Rows_(existingRows, fixtureRows);
  const secondPlan = planLesson01Rows_(
    firstPlan.finalValues,
    fixtureRows,
  );

  assertLesson01_(
    secondPlan.writes.length === 0,
    '重複執行後仍準備寫入重複資料',
  );
  assertLesson01_(
    secondPlan.finalValues[1][1] === 'wang@example.com',
    '重複執行不應刪除原有資料',
  );

  writeLessonLog_('成功', '第 1 課重複測試通過｜沒有新增重複資料');
}

/**
 * 實際建立或更新指定工作表。
 *
 * @param {string} sheetName 工作表名稱。
 * @param {Array<Array<string>>} fixtureRows 使用學員信箱的教學資料。
 * @return {{
 *   changed: boolean,
 *   created: boolean,
 *   dataRowCount: number,
 *   insertedCount: number,
 *   updatedCount: number
 * }} 執行結果。
 */
function setupLessonSheet_(sheetName, fixtureRows) {
  writeLessonLog_('開始', '準備建立活動報名資料工作表');

  try {
    // 先驗證不可信輸入，避免錯誤資料碰觸試算表。
    validateLesson01SheetName_(sheetName);
    // 第 2 課起先驗證指令碼屬性，再碰觸任何工作表資料。
    const spreadsheet = openCourseSpreadsheet_();
    writeLesson02SettingsLog_(true);

    let sheet = spreadsheet.getSheetByName(sheetName);
    const created = sheet === null;

    if (created) {
      sheet = spreadsheet.insertSheet(sheetName);
    }

    const currentValues = readLesson01Values_(sheet);
    const plan = planLesson01Rows_(currentValues, fixtureRows);

    applyLesson01Plan_(sheet, plan);

    // 只有第一次初始化版面時設定欄寬；日後重跑保留手動調整。
    if (created || currentValues.length === 0) {
      applyLesson01InitialLayout_(sheet);
    }

    if (plan.writes.length === 0) {
      writeLessonLog_('略過', '工作表已符合本課內容｜沒有新增重複資料');
    } else {
      writeLessonLog_(
        '成功',
        '已完成活動報名資料工作表｜資料筆數=2｜其他資料保持不變',
      );
    }

    return {
      changed: plan.writes.length > 0,
      created,
      dataRowCount: fixtureRows.length,
      insertedCount: plan.insertedCount,
      updatedCount: plan.updatedCount,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    writeLessonLog_(
      '失敗',
      `無法建立活動報名資料工作表｜原因=${message}｜請先停止並檢查執行記錄`,
    );
    throw error;
  }
}

/**
 * 驗證工作表名稱。
 *
 * @param {string} sheetName 工作表名稱。
 */
function validateLesson01SheetName_(sheetName) {
  if (typeof sheetName !== 'string' || sheetName.trim() === '') {
    throw new Error('工作表名稱不可空白');
  }
}

/**
 * 讀取 A 到 D 欄的實際資料，忽略其他欄位造成的空白尾列。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 工作表。
 * @return {Array<Array<string>>} 目前 A 到 D 欄資料。
 */
function readLesson01Values_(sheet) {
  const lastRow = sheet.getLastRow();
  if (lastRow < 1) {
    return [];
  }

  const values = sheet
    .getRange(1, 1, lastRow, LESSON01_CONFIG_.headers.length)
    .getDisplayValues();

  while (
    values.length > 0 &&
    values[values.length - 1].every((value) => String(value).trim() === '')
  ) {
    values.pop();
  }

  return values;
}

/**
 * 規劃最小必要寫入，只更新表頭與可明確辨識的兩筆假資料。
 *
 * 不相關的既有資料列會完整保留，也不會因重跑而重複追加假資料。
 *
 * @param {Array<Array<string>>} currentValues 目前 A 到 D 欄資料。
 * @param {Array<Array<string>>} fixtureRows 使用學員信箱的教學資料。
 * @return {{
 *   finalValues: Array<Array<string>>,
 *   writes: Array<{row: number, values: Array<string>}>,
 *   insertedCount: number,
 *   updatedCount: number
 * }} 寫入計畫。
 */
function planLesson01Rows_(currentValues, fixtureRows) {
  validateLesson01FixtureRows_(fixtureRows);
  const finalValues = currentValues.map((row) =>
    LESSON01_CONFIG_.headers.map((_header, index) =>
      index < row.length ? row[index] : '',
    ),
  );
  const writes = [];
  let insertedCount = 0;
  let updatedCount = 0;

  if (
    finalValues.length === 0 ||
    !lesson01RowsEqual_(finalValues[0], LESSON01_CONFIG_.headers)
  ) {
    finalValues[0] = LESSON01_CONFIG_.headers.slice();
    writes.push({ row: 1, values: LESSON01_CONFIG_.headers.slice() });
    updatedCount += 1;
  }

  for (const fixtureRow of fixtureRows) {
    const existingIndex = findLesson01FixtureRowIndex_(
      finalValues,
      fixtureRow,
    );

    if (existingIndex < 0) {
      finalValues.push(fixtureRow.slice());
      const newIndex = finalValues.length - 1;
      writes.push({ row: newIndex + 1, values: fixtureRow.slice() });
      insertedCount += 1;
      continue;
    }

    // 課程進度已推進時保留處理狀態，只更新可辨識的教學姓名、信箱與場次。
    const existingStatus = String(
      finalValues[existingIndex][3] || '',
    ).trim();
    const updatedRow = fixtureRow.slice();
    if (existingStatus !== '') {
      updatedRow[3] = existingStatus;
    }

    if (!lesson01RowsEqual_(finalValues[existingIndex], updatedRow)) {
      finalValues[existingIndex] = updatedRow;
      writes.push({ row: existingIndex + 1, values: updatedRow.slice() });
      updatedCount += 1;
    }
  }

  return {
    finalValues,
    writes,
    insertedCount,
    updatedCount,
  };
}

/**
 * 將規劃好的最小變更寫入工作表。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 工作表。
 * @param {{
 *   writes: Array<{row: number, values: Array<string>}>
 * }} plan 寫入計畫。
 */
function applyLesson01Plan_(sheet, plan) {
  for (const write of plan.writes) {
    sheet
      .getRange(write.row, 1, 1, LESSON01_CONFIG_.headers.length)
      .setValues([write.values]);
  }
}

/**
 * 只在第一次初始化時建立容易閱讀的基本版面。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 工作表。
 */
function applyLesson01InitialLayout_(sheet) {
  sheet
    .getRange(1, 1, 1, LESSON01_CONFIG_.headers.length)
    .setFontWeight('bold')
    .setBackground('#d9ead3');
  sheet.setFrozenRows(1);

  LESSON01_CONFIG_.initialColumnWidths.forEach((width, index) => {
    sheet.setColumnWidth(index + 1, width);
  });
}

/**
 * 建立本課完整預期資料。
 *
 * @param {Array<Array<string>>} fixtureRows 使用學員信箱的教學資料。
 * @return {Array<Array<string>>} 表頭與兩筆假資料。
 */
function buildLesson01ExpectedValues_(fixtureRows) {
  return [
    LESSON01_CONFIG_.headers.slice(),
    ...fixtureRows.map((row) => row.slice()),
  ];
}

/**
 * 取得目前授權執行 Apps Script 的 Google 帳號信箱。
 *
 * 實際地址只會寫入學員自己的練習試算表，不會進入紀錄檔(Log)或 Git。
 *
 * @return {string} 已驗證的學員 Email。
 */
function getLesson01LearnerEmail_() {
  const user = Session.getEffectiveUser();
  const email = normalizeLesson01Email_(
    user && typeof user.getEmail === 'function' ? user.getEmail() : '',
  );
  const emailPattern = /^[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+$/;

  if (!emailPattern.test(email)) {
    throw new Error(
      '無法取得目前執行者的 Google 帳號 Email｜請從試算表選單重新授權後再試',
    );
  }
  return email;
}

/**
 * 建立兩筆可安全接收後續教學通知的假報名資料。
 *
 * @param {string} learnerEmail 學員自己的 Email。
 * @return {Array<Array<string>>} 教學假資料。
 */
function buildLesson01FixtureRows_(learnerEmail) {
  const email = normalizeLesson01Email_(learnerEmail);
  const emailPattern = /^[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+$/;
  if (!emailPattern.test(email)) {
    throw new Error('教學資料需要可收信的學員 Email');
  }

  return LESSON01_CONFIG_.fixtureDefinitions.map(([name, session]) => [
    name,
    email,
    session,
    '待處理',
  ]);
}

/**
 * 驗證規劃函式收到兩筆完整教學資料。
 *
 * @param {Array<Array<string>>} fixtureRows 教學資料。
 */
function validateLesson01FixtureRows_(fixtureRows) {
  if (
    !Array.isArray(fixtureRows) ||
    fixtureRows.length !== LESSON01_CONFIG_.fixtureDefinitions.length ||
    fixtureRows.some(
      (row) =>
        !Array.isArray(row) ||
        row.length !== LESSON01_CONFIG_.headers.length,
    )
  ) {
    throw new Error('第 1 課教學資料格式不正確');
  }
}

/**
 * 以課程保留姓名與場次辨識固定教學資料，不以 Email 當唯一鍵。
 *
 * @param {Array<*>} row 資料列。
 * @return {string} 固定教學資料鍵值。
 */
function buildLesson01FixtureKey_(row) {
  const name = String((row || [])[0] || '').trim();
  const session = String((row || [])[2] || '').trim();
  return name === '' || session === '' ? '' : `${name}|${session}`;
}

/**
 * 只把目前學員 Email 或舊版固定 example.com 地址視為同一筆教材資料。
 *
 * 這項限制避免碰巧同名、同場次的真實報名者被初始化流程改寫。
 *
 * @param {Array<Array<*>>} values 目前資料。
 * @param {Array<*>} fixtureRow 預期教材資料。
 * @return {number} 找到的索引；不存在時為 -1。
 */
function findLesson01FixtureRowIndex_(values, fixtureRow) {
  const expectedKey = buildLesson01FixtureKey_(fixtureRow);
  const expectedEmail = normalizeLesson01Email_(fixtureRow[1]);
  const legacyEmail = normalizeLesson01Email_(
    LESSON01_CONFIG_.legacyFixtureEmails[fixtureRow[0]],
  );

  for (let index = 1; index < values.length; index += 1) {
    const row = values[index];
    const email = normalizeLesson01Email_(row[1]);
    if (
      buildLesson01FixtureKey_(row) === expectedKey &&
      (email === expectedEmail || email === legacyEmail)
    ) {
      return index;
    }
  }
  return -1;
}

/**
 * 比較兩列資料是否完全一致。
 *
 * @param {Array<string>} actual 實際資料。
 * @param {Array<string>} expected 預期資料。
 * @return {boolean} 是否一致。
 */
function lesson01RowsEqual_(actual, expected) {
  return expected.every(
    (value, index) => String(actual[index] || '') === String(value),
  );
}

/**
 * 將 Email 轉成可穩定比對的格式。
 *
 * @param {*} value 原始值。
 * @return {string} 正規化後的 Email。
 */
function normalizeLesson01Email_(value) {
  return String(value || '').trim().toLowerCase();
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
