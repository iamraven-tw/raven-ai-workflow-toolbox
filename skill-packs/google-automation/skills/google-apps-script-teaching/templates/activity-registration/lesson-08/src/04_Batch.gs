const LESSON04_CONFIG_ = Object.freeze({
  sheetName: '活動報名資料',
  headers: Object.freeze([
    '姓名',
    'Email',
    '活動場次',
    '處理狀態',
    '報名編號',
    '錯誤原因',
    '文件 ID',
    '通知編號',
    '最後更新時間',
  ]),
  pendingStatus: '待處理',
  readyStatus: '待產生文件',
  invalidStatus: '資料有誤',
  practiceRows: Object.freeze([
    Object.freeze([
      '第4課錯誤範例',
      'invalid-email',
      '上午場',
      '待處理',
      '',
      '',
      '',
      '',
      '',
    ]),
    Object.freeze([
      '第4課已處理範例',
      'lesson04-done@example.com',
      '下午場',
      '已完成',
      'REG-DEMO0001',
      '',
      '',
      '',
      '',
    ]),
  ]),
});

/**
 * 學生入口：只讀檢查第 4 課需要的試算表設定與基本欄位。
 *
 * 本課不需要 FORM_ID，也不會在設定檢查時修改任何工作表。
 *
 * @return {boolean} 設定是否通過。
 */
function checkLesson04Settings() {
  writeLessonLog_('開始', '準備檢查第 4 課設定');

  try {
    const spreadsheet = openCourseSpreadsheet_();
    writeLesson02SettingsLog_(true);
    const sheet = getLesson04Sheet_(spreadsheet);
    validateLesson04BaseHeaders_(readLesson04BaseHeaders_(sheet));
    writeLessonLog_('成功', '第 4 課可安全使用活動報名資料工作表');
    return true;
  } catch (error) {
    const config = getScriptConfig_();
    const message = error instanceof Error ? error.message : String(error);
    writeLesson02SettingsLog_(
      normalizeLesson02Setting_(config.spreadsheetId) !== '',
    );
    writeLessonLog_('失敗', `${message}｜未執行批次資料寫入`);
    throw error;
  }
}

/**
 * 學生入口：整批讀取、驗證並一次寫回報名處理狀態。
 *
 * 本函式只處理「活動報名資料」工作表，不修改表單回覆分頁。第一次
 * 執行會補齊後續課程共用欄位及兩筆可辨識、可重複使用的教學假資料。
 *
 * @return {{
 *   changed: boolean,
 *   readCount: number,
 *   validCount: number,
 *   invalidCount: number,
 *   skippedCount: number
 * }} 批次處理結果。
 */
function processPendingRegistrations() {
  writeLessonLog_('開始', '準備批次處理報名資料');

  try {
    const spreadsheet = openCourseSpreadsheet_();
    writeLesson02SettingsLog_(true);
    const sheet = getLesson04Sheet_(spreadsheet);
    const currentValues = readLesson04SheetValues_(sheet);
    const plan = planLesson04Batch_(currentValues, new Date(), {
      includePracticeRows: true,
    });

    writeLessonLog_('進度', `已讀取待檢查資料｜筆數=${plan.readCount}`);

    if (plan.changed) {
      writeLesson04BatchValues_(sheet, plan.finalValues);
    }

    if (plan.pendingCount === 0) {
      writeLessonLog_(
        '略過',
        `沒有待處理資料｜已略過=${plan.skippedCount}`,
      );
    } else {
      writeLessonLog_(
        '成功',
        `批次處理完成｜有效=${plan.validCount}｜無效=${plan.invalidCount}｜略過=${plan.skippedCount}`,
      );
    }

    return {
      changed: plan.changed,
      readCount: plan.readCount,
      validCount: plan.validCount,
      invalidCount: plan.invalidCount,
      skippedCount: plan.skippedCount,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    writeLessonLog_(
      '失敗',
      `批次處理停止｜原因=${message}｜未完成批次結果`,
    );
    throw error;
  }
}

/**
 * Agent 工程測試總入口：不讀寫真實 Google Sheets。
 *
 * 學生不需要執行這個函式；學生只操作設定檢查與主要批次功能。
 */
function runLesson04Tests() {
  writeLessonLog_('開始', '執行第 4 課批次工程測試');

  const tests = [
    ['零筆', testLesson04Zero_],
    ['一筆', testLesson04One_],
    ['多筆', testLesson04Many_],
    ['錯誤', testLesson04Error_],
    ['重複', testLesson04Repeat_],
  ];

  tests.forEach(([name, testFunction]) => {
    testFunction();
    writeLessonLog_('成功', `第 4 課${name}測試通過`);
  });

  writeLessonLog_('成功', '第 4 課工程測試全部通過｜項目=5');
}

/**
 * Agent 內部測試：零筆資料不建立空白業務結果。
 */
function testLesson04Zero_() {
  const plan = planLesson04Batch_(
    [LESSON04_CONFIG_.headers.slice()],
    new Date('2026-01-01T00:00:00.000Z'),
    { includePracticeRows: false },
  );

  assertLesson04_(plan.readCount === 0, '零筆測試不應讀到資料');
  assertLesson04_(plan.pendingCount === 0, '零筆測試不應有待處理資料');
  assertLesson04_(!plan.changed, '零筆測試不應建立空白結果');
}

/**
 * Agent 內部測試：一筆有效資料得到待產生文件狀態。
 */
function testLesson04One_() {
  const plan = planLesson04Batch_(
    [
      LESSON04_CONFIG_.headers.slice(),
      [
        '測試學員',
        'one@example.com',
        '上午場',
        '待處理',
        '',
        '',
        '',
        '',
        '',
      ],
    ],
    new Date('2026-01-01T00:00:00.000Z'),
    { includePracticeRows: false },
  );

  assertLesson04_(plan.validCount === 1, '一筆測試應有一筆有效資料');
  assertLesson04_(
    plan.finalValues[1][3] === LESSON04_CONFIG_.readyStatus,
    '有效資料狀態應為待產生文件',
  );
}

/**
 * Agent 內部測試：同一批資料可同時得到有效、無效與略過結果。
 */
function testLesson04Many_() {
  const plan = planLesson04Batch_(
    [
      LESSON04_CONFIG_.headers.slice(),
      [
        '有效學員',
        'valid@example.com',
        '下午場',
        '待處理',
        '',
        '',
        '',
        '',
        '',
      ],
      [
        '無效學員',
        'invalid-email',
        '上午場',
        '待處理',
        '',
        '',
        '',
        '',
        '',
      ],
      [
        '已處理學員',
        'done@example.com',
        '上午場',
        '待產生文件',
        'REG-DONE0001',
        '',
        '',
        '',
        '',
      ],
    ],
    new Date('2026-01-01T00:00:00.000Z'),
    { includePracticeRows: false },
  );

  assertLesson04_(plan.validCount === 1, '多筆測試應有一筆有效資料');
  assertLesson04_(plan.invalidCount === 1, '多筆測試應有一筆無效資料');
  assertLesson04_(plan.skippedCount === 1, '多筆測試應略過一筆資料');
  assertLesson04_(
    String(plan.finalValues[2][5]).includes('Email'),
    '無效資料應保留中文欄位原因',
  );
}

/**
 * Agent 內部測試：列數或欄數不一致時必須在寫回前停止。
 */
function testLesson04Error_() {
  try {
    validateLesson04WriteShape_(
      [
        ['欄一', '欄二'],
        ['只有一欄'],
      ],
      2,
      2,
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    assertLesson04_(
      message.includes('資料欄位數與寫入範圍不一致'),
      '錯誤測試應指出範圍大小不一致',
    );
    return;
  }

  throw new Error('第 4 課錯誤測試失敗：不一致資料沒有被拒絕');
}

/**
 * Agent 內部測試：已完成批次結果重跑時只略過，不再增加結果。
 */
function testLesson04Repeat_() {
  const first = planLesson04Batch_(
    [
      LESSON04_CONFIG_.headers.slice(),
      [
        '重複測試',
        'repeat@example.com',
        '下午場',
        '待處理',
        '',
        '',
        '',
        '',
        '',
      ],
    ],
    new Date('2026-01-01T00:00:00.000Z'),
    { includePracticeRows: false },
  );
  const second = planLesson04Batch_(
    first.finalValues,
    new Date('2026-01-02T00:00:00.000Z'),
    { includePracticeRows: false },
  );

  assertLesson04_(first.validCount === 1, '第一次應處理一筆有效資料');
  assertLesson04_(second.validCount === 0, '重跑不應再次處理有效資料');
  assertLesson04_(second.skippedCount === 1, '重跑應略過已處理資料');
  assertLesson04_(!second.changed, '重跑不應改變已完成結果');
}

/**
 * 取得第 4 課唯一會修改的工作表。
 *
 * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} spreadsheet 試算表。
 * @return {GoogleAppsScript.Spreadsheet.Sheet} 活動報名資料工作表。
 */
function getLesson04Sheet_(spreadsheet) {
  const sheet = spreadsheet.getSheetByName(LESSON04_CONFIG_.sheetName);
  if (!sheet) {
    throw new Error(`找不到工作表｜名稱=${LESSON04_CONFIG_.sheetName}`);
  }
  return sheet;
}

/**
 * 設定檢查只讀取前四個既有欄位。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 工作表。
 * @return {Array<*>} 前四個欄位。
 */
function readLesson04BaseHeaders_(sheet) {
  return sheet
    .getRange(1, 1, 1, LESSON01_CONFIG_.headers.length)
    .getDisplayValues()[0];
}

/**
 * 驗證前課建立的基本欄位仍完整且順序正確。
 *
 * @param {Array<*>} headers 表頭。
 * @return {boolean} 是否通過。
 */
function validateLesson04BaseHeaders_(headers) {
  const actual = (headers || []).map((value) => String(value || '').trim());
  if (!lesson03ArraysEqual_(actual, LESSON01_CONFIG_.headers)) {
    throw new Error('活動報名資料基本欄位不符｜未執行欄位升級');
  }
  return true;
}

/**
 * 一次讀取本課工作表使用中的完整資料範圍。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 工作表。
 * @return {Array<Array<*>>} 工作表值。
 */
function readLesson04SheetValues_(sheet) {
  const rowCount = Math.max(sheet.getLastRow(), 1);
  const columnCount = Math.max(
    sheet.getLastColumn(),
    LESSON04_CONFIG_.headers.length,
  );
  return sheet.getRange(1, 1, rowCount, columnCount).getValues();
}

/**
 * 規劃欄位升級、教學假資料與整批狀態，不直接操作 Google Sheets。
 *
 * @param {Array<Array<*>>} currentValues 目前工作表資料。
 * @param {Date} now 本次處理時間。
 * @param {{includePracticeRows: boolean}=} options 測試資料選項。
 * @return {Object} 完整批次計畫。
 */
function planLesson04Batch_(currentValues, now, options) {
  if (!Array.isArray(currentValues)) {
    throw new Error('批次資料必須是二維陣列');
  }

  const includePracticeRows = Boolean(
    options && options.includePracticeRows,
  );
  const originalRows = currentValues.length > 0 ? currentValues : [[]];
  const width = Math.max(
    LESSON04_CONFIG_.headers.length,
    ...originalRows.map((row) => (Array.isArray(row) ? row.length : 0)),
  );
  const finalValues = originalRows.map((row) => {
    if (!Array.isArray(row)) {
      throw new Error('批次資料必須是二維陣列');
    }
    const normalized = row.slice(0, width);
    while (normalized.length < width) {
      normalized.push('');
    }
    return normalized;
  });

  const headerChanged = upgradeLesson04HeadersInMemory_(finalValues[0]);
  const practiceInsertedCount = includePracticeRows
    ? appendLesson04PracticeRows_(finalValues, width)
    : 0;
  let validCount = 0;
  let invalidCount = 0;
  let skippedCount = 0;
  let pendingCount = 0;
  let readCount = 0;
  let dataChanged = false;

  for (let index = 1; index < finalValues.length; index += 1) {
    const row = finalValues[index];
    if (isLesson04BlankRow_(row)) {
      continue;
    }
    readCount += 1;

    const status = String(row[3] || '').trim();
    if (status !== LESSON04_CONFIG_.pendingStatus) {
      skippedCount += 1;
      continue;
    }
    pendingCount += 1;

    const sourceKey = [
      'sheet-row',
      index + 1,
      String(row[0] || '').trim(),
      String(row[1] || '').trim().toLowerCase(),
      String(row[2] || '').trim(),
    ].join('|');
    const registrationId =
      String(row[4] || '').trim() ||
      createLesson03RegistrationId_(sourceKey);
    row[4] = registrationId;

    try {
      const registration = validateRegistration_({
        registrationId,
        name: row[0],
        email: row[1],
        session: row[2],
      });
      row[0] = registration.name;
      row[1] = registration.email;
      row[2] = registration.session;
      row[3] = LESSON04_CONFIG_.readyStatus;
      row[5] = '';
      row[8] = new Date(now.getTime());
      validCount += 1;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      row[3] = LESSON04_CONFIG_.invalidStatus;
      row[5] = message;
      row[8] = new Date(now.getTime());
      invalidCount += 1;
    }
    dataChanged = true;
  }

  return {
    changed:
      headerChanged || practiceInsertedCount > 0 || dataChanged,
    finalValues,
    readCount,
    pendingCount,
    validCount,
    invalidCount,
    skippedCount,
    practiceInsertedCount,
  };
}

/**
 * 在記憶體中補齊共用欄位；遇到不相容欄位就停止。
 *
 * @param {Array<*>} headerRow 表頭列。
 * @return {boolean} 是否有欄位變更。
 */
function upgradeLesson04HeadersInMemory_(headerRow) {
  validateLesson04BaseHeaders_(
    headerRow.slice(0, LESSON01_CONFIG_.headers.length),
  );

  let changed = false;
  LESSON04_CONFIG_.headers.forEach((expected, index) => {
    const current = String(headerRow[index] || '').trim();
    const isLegacyMailIdHeader =
      index === 7 && current === '郵件 ID' && expected === '通知編號';
    if (current !== '' && current !== expected && !isLegacyMailIdHeader) {
      throw new Error(`共用欄位不相容｜欄位=${index + 1}｜未覆寫既有資料`);
    }
    if (current !== expected) {
      headerRow[index] = expected;
      changed = true;
    }
  });
  return changed;
}

/**
 * 加入兩筆可辨識教學資料，讓 UI 可看見無效與已略過狀態。
 *
 * 同名資料已存在時安全略過，不會碰觸表單回覆分頁。
 *
 * @param {Array<Array<*>>} values 工作表資料。
 * @param {number} width 工作表欄數。
 * @return {number} 新增筆數。
 */
function appendLesson04PracticeRows_(values, width) {
  const existingNames = new Set(
    values
      .slice(1)
      .map((row) => String(row[0] || '').trim())
      .filter((name) => name !== ''),
  );
  let insertedCount = 0;

  LESSON04_CONFIG_.practiceRows.forEach((fixture) => {
    const fixtureName = fixture[0];
    if (existingNames.has(fixtureName)) {
      return;
    }
    const row = fixture.slice();
    while (row.length < width) {
      row.push('');
    }
    values.push(row);
    existingNames.add(fixtureName);
    insertedCount += 1;
  });
  return insertedCount;
}

/**
 * 判斷資料列是否完全空白。
 *
 * @param {Array<*>} row 資料列。
 * @return {boolean} 是否空白。
 */
function isLesson04BlankRow_(row) {
  return row
    .slice(0, LESSON04_CONFIG_.headers.length)
    .every((value) => String(value || '').trim() === '');
}

/**
 * 一次寫回完整批次結果，寫入前先核對範圍大小。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 工作表。
 * @param {Array<Array<*>>} values 完整批次結果。
 */
function writeLesson04BatchValues_(sheet, values) {
  const rowCount = values.length;
  const columnCount = values[0].length;
  validateLesson04WriteShape_(values, rowCount, columnCount);

  const range = sheet.getRange(1, 1, rowCount, columnCount);
  validateLesson04WriteShape_(
    values,
    range.getNumRows(),
    range.getNumColumns(),
  );
  range.setValues(values);
}

/**
 * 寫回前檢查二維陣列與目標範圍大小完全一致。
 *
 * @param {Array<Array<*>>} values 寫入值。
 * @param {number} expectedRows 目標列數。
 * @param {number} expectedColumns 目標欄數。
 * @return {boolean} 是否通過。
 */
function validateLesson04WriteShape_(
  values,
  expectedRows,
  expectedColumns,
) {
  const rowsMatch =
    Array.isArray(values) && values.length === expectedRows;
  const columnsMatch =
    rowsMatch &&
    values.every(
      (row) =>
        Array.isArray(row) && row.length === expectedColumns,
    );

  if (!rowsMatch || !columnsMatch) {
    throw new Error('資料欄位數與寫入範圍不一致｜未寫入任何結果');
  }
  return true;
}

/**
 * 第 4 課工程測試斷言。
 *
 * @param {boolean} condition 條件。
 * @param {string} message 失敗說明。
 */
function assertLesson04_(condition, message) {
  if (!condition) {
    throw new Error(`第 4 課測試失敗：${message}`);
  }
}
