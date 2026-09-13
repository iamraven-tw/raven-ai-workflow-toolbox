const LESSON05_CONFIG_ = Object.freeze({
  readyStatus: '待產生文件',
  createdStatus: '待寄送郵件',
  documentNamePrefix: '活動報名確認',
  templateTokens: Object.freeze([
    Object.freeze({
      label: '姓名',
      pattern: '\\{\\{姓名\\}\\}',
      marker: '{{姓名}}',
    }),
    Object.freeze({
      label: '活動場次',
      pattern: '\\{\\{活動場次\\}\\}',
      marker: '{{活動場次}}',
    }),
    Object.freeze({
      label: '報名編號',
      pattern: '\\{\\{報名編號\\}\\}',
      marker: '{{報名編號}}',
    }),
  ]),
});

/**
 * 學生入口：只讀檢查第 5 課需要的試算表、文件範本與輸出資料夾。
 *
 * 本函式不建立文件、不修改工作表，也不輸出任何實際資源 ID。
 *
 * @return {boolean} 設定是否通過檢查。
 */
function checkLesson05Settings() {
  writeLessonLog_('開始', '準備檢查第 5 課設定');

  try {
    const config = getScriptConfig_();
    validateLesson05RequiredProperties_(config);
    const spreadsheet = openCourseSpreadsheet_();
    const sheet = getLesson04Sheet_(spreadsheet);
    validateLesson05Headers_(readLesson05Headers_(sheet));
    const resources = openLesson05Resources_(config);
    validateLesson05Template_(resources.templateDocument.getBody().getText());
    writeLesson05SettingsLog_(config);
    writeLessonLog_(
      '成功',
      '第 5 課可安全使用指定的文件範本與輸出資料夾',
    );
    return true;
  } catch (error) {
    const config = getScriptConfig_();
    const message = error instanceof Error ? error.message : String(error);
    writeLesson05SettingsLog_(config);
    writeLessonLog_('失敗', `${message}｜未建立文件｜未修改工作表`);
    throw error;
  }
}

/**
 * Sheets 日常入口：為第一筆待產生文件的報名建立確認文件。
 *
 * 每次最多建立一份，讓一般使用者能清楚核對產出；文件建立成功後，才
 * 將文件 ID 與下一步狀態一次寫回同一列。
 *
 * @return {{createdCount: number, skippedCount: number}} 執行結果。
 */
function createPendingRegistrationDocuments() {
  writeLessonLog_('開始', '準備建立報名確認文件');

  try {
    const config = getScriptConfig_();
    validateLesson05RequiredProperties_(config);
    const spreadsheet = openCourseSpreadsheet_();
    const sheet = getLesson04Sheet_(spreadsheet);
    const values = readLesson04SheetValues_(sheet);
    validateLesson05Headers_(values[0]);
    const resources = openLesson05Resources_(config);
    validateLesson05Template_(resources.templateDocument.getBody().getText());
    writeLesson05SettingsLog_(config);

    const plan = planLesson05Candidate_(values);
    if (!plan.candidate) {
      if (plan.existingDocumentCount > 0) {
        writeLessonLog_('略過', '這筆報名已有文件｜沒有重複建立');
      } else {
        writeLessonLog_('略過', '沒有待產生文件的報名｜未建立文件');
      }
      return {
        createdCount: 0,
        skippedCount: plan.skippedCount,
      };
    }

    const documentId = createRegistrationDocument_(
      plan.candidate.registration,
      resources,
    );

    try {
      writeLesson05Result_(
        sheet,
        plan.candidate,
        documentId,
        new Date(),
      );
    } catch (writeError) {
      const writeMessage =
        writeError instanceof Error ? writeError.message : String(writeError);
      writeLessonLog_(
        '失敗',
        `確認文件已建立，但工作表寫回失敗｜原因=${writeMessage}｜請勿重跑並人工檢查輸出資料夾`,
      );
      throw new Error(`工作表寫回失敗｜${writeMessage}`);
    }

    writeLessonLog_('成功', '已建立報名確認文件｜建立數量=1');
    return {
      createdCount: 1,
      skippedCount: plan.skippedCount,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (!message.includes('工作表寫回失敗')) {
      writeLessonLog_('失敗', `${message}｜本次流程已停止`);
    }
    throw error;
  }
}

/**
 * Agent 工程測試總入口：只測純資料規則，不存取真實 Docs 或 Drive。
 */
function runLesson05Tests() {
  writeLessonLog_('開始', '執行第 5 課文件工程測試');

  const tests = [
    ['正常', testLesson05Normal],
    ['缺少資料夾', testLesson05MissingFolder],
    ['重複', testLesson05Repeat],
  ];

  tests.forEach(([name, testFunction]) => {
    testFunction();
    writeLessonLog_('成功', `第 5 課${name}測試通過`);
  });

  writeLessonLog_('成功', '第 5 課工程測試全部通過｜項目=3');
}

/**
 * Agent 工程測試：正常資料可選為本次唯一候選。
 */
function testLesson05Normal() {
  const values = [
    LESSON04_CONFIG_.headers.slice(),
    [
      '測試學員',
      'lesson05@example.com',
      '上午場',
      LESSON05_CONFIG_.readyStatus,
      'REG-LESSON0501',
      '',
      '',
      '',
      '',
    ],
  ];
  const plan = planLesson05Candidate_(values);

  assertLesson05_(Boolean(plan.candidate), '正常資料應成為文件候選');
  assertLesson05_(
    plan.candidate.registration.name === '測試學員',
    '候選資料應保留姓名',
  );
}

/**
 * Agent 工程測試：缺少輸出資料夾時必須在建立文件前停止。
 */
function testLesson05MissingFolder() {
  try {
    validateLesson05RequiredProperties_({
      spreadsheetId: 'test-spreadsheet',
      docTemplateId: 'test-template',
      outputFolderId: '',
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    assertLesson05_(
      message.includes('OUTPUT_FOLDER_ID'),
      '缺少資料夾測試應指出設定名稱',
    );
    return;
  }

  throw new Error('第 5 課缺少資料夾測試失敗：空白設定沒有被拒絕');
}

/**
 * Agent 工程測試：已有文件 ID 的報名重跑時不再成為候選。
 */
function testLesson05Repeat() {
  const values = [
    LESSON04_CONFIG_.headers.slice(),
    [
      '重複測試',
      'repeat@example.com',
      '下午場',
      LESSON05_CONFIG_.readyStatus,
      'REG-LESSON0502',
      '',
      'existing-document-id',
      '',
      '',
    ],
  ];
  const plan = planLesson05Candidate_(values);

  assertLesson05_(!plan.candidate, '已有文件 ID 時不應再次建立文件');
  assertLesson05_(
    plan.existingDocumentCount === 1,
    '重複測試應辨識一筆既有文件',
  );
}

/**
 * 驗證第 5 課所有設定都存在，且在任何 Drive 建立動作前完成。
 *
 * @param {Object} config 集中式設定。
 * @return {boolean} 是否通過。
 */
function validateLesson05RequiredProperties_(config) {
  const required = [
    ['spreadsheetId', COURSE_PROPERTY_NAMES_.spreadsheetId],
    ['docTemplateId', COURSE_PROPERTY_NAMES_.docTemplateId],
    ['outputFolderId', COURSE_PROPERTY_NAMES_.outputFolderId],
  ];

  required.forEach(([field, propertyName]) => {
    if (!config || normalizeLesson02Setting_(config[field]) === '') {
      throw new Error(
        `缺少必要的指令碼屬性｜名稱=${propertyName}`,
      );
    }
  });
  return true;
}

/**
 * 只顯示三項設定是否完成，不輸出實際值。
 *
 * @param {Object} config 集中式設定。
 */
function writeLesson05SettingsLog_(config) {
  const status = (field) =>
    config && normalizeLesson02Setting_(config[field]) !== ''
      ? '已設定'
      : '未設定';

  writeLessonLog_(
    '設定',
    `SPREADSHEET_ID=${status('spreadsheetId')}｜DOC_TEMPLATE_ID=${status('docTemplateId')}｜OUTPUT_FOLDER_ID=${status('outputFolderId')}｜實際值不顯示`,
  );
}

/**
 * 取得並檢查指定的文件範本與輸出資料夾。
 *
 * @param {Object} config 已通過必要欄位檢查的設定。
 * @return {{
 *   templateFile: GoogleAppsScript.Drive.File,
 *   outputFolder: GoogleAppsScript.Drive.Folder,
 *   templateDocument: GoogleAppsScript.Document.Document
 * }} 已核對的資源。
 */
function openLesson05Resources_(config) {
  let templateFile;
  let templateDocument;
  let outputFolder;

  try {
    templateFile = DriveApp.getFileById(config.docTemplateId);
    if (templateFile.getMimeType() !== MimeType.GOOGLE_DOCS) {
      throw new Error('指定範本不是 Google 文件');
    }
    templateDocument = DocumentApp.openById(config.docTemplateId);
  } catch (error) {
    throw new Error(
      '找不到可使用的指定文件範本｜請檢查 DOC_TEMPLATE_ID',
    );
  }

  try {
    outputFolder = DriveApp.getFolderById(config.outputFolderId);
    outputFolder.getName();
  } catch (error) {
    throw new Error(
      '找不到指定輸出資料夾｜未建立文件｜請檢查 OUTPUT_FOLDER_ID',
    );
  }

  return {
    templateFile,
    outputFolder,
    templateDocument,
  };
}

/**
 * 讀取第 5 課需要的完整表頭。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 工作表。
 * @return {Array<*>} 表頭。
 */
function readLesson05Headers_(sheet) {
  return sheet
    .getRange(1, 1, 1, LESSON04_CONFIG_.headers.length)
    .getDisplayValues()[0];
}

/**
 * 驗證第 4 課累積欄位仍完整，避免把結果寫到錯誤欄位。
 *
 * @param {Array<*>} headers 表頭。
 * @return {boolean} 是否通過。
 */
function validateLesson05Headers_(headers) {
  const actual = (headers || [])
    .slice(0, LESSON04_CONFIG_.headers.length)
    .map((value) => String(value || '').trim());
  const legacyHeaders = LESSON04_CONFIG_.headers.slice();
  legacyHeaders[7] = '郵件 ID';

  if (
    !lesson03ArraysEqual_(actual, LESSON04_CONFIG_.headers) &&
    !lesson03ArraysEqual_(actual, legacyHeaders)
  ) {
    throw new Error('活動報名資料欄位不符｜請先完成第 4 課批次處理');
  }
  return true;
}

/**
 * 驗證範本包含本課所有替換記號。
 *
 * @param {*} text 範本純文字。
 * @return {boolean} 是否通過。
 */
function validateLesson05Template_(text) {
  const templateText = String(text || '');
  const missing = LESSON05_CONFIG_.templateTokens
    .filter((token) => !templateText.includes(token.marker))
    .map((token) => token.label);

  if (missing.length > 0) {
    throw new Error(
      `文件範本缺少必要記號｜欄位=${missing.join('、')}｜未建立文件`,
    );
  }
  return true;
}

/**
 * 從整批資料選出第一筆待產生文件且尚無文件 ID 的報名。
 *
 * @param {Array<Array<*>>} values 工作表完整資料。
 * @return {{
 *   candidate: Object|null,
 *   existingDocumentCount: number,
 *   skippedCount: number
 * }} 本次候選計畫。
 */
function planLesson05Candidate_(values) {
  if (!Array.isArray(values) || values.length === 0) {
    throw new Error('活動報名資料不可為空');
  }
  validateLesson05Headers_(values[0]);

  let existingDocumentCount = 0;
  let skippedCount = 0;

  for (let index = 1; index < values.length; index += 1) {
    const row = Array.isArray(values[index]) ? values[index] : [];
    if (isLesson04BlankRow_(row)) {
      continue;
    }

    const documentId = normalizeLesson02Setting_(row[6]);
    if (documentId !== '') {
      existingDocumentCount += 1;
      skippedCount += 1;
      continue;
    }
    if (
      normalizeLesson02Setting_(row[3]) !==
      LESSON05_CONFIG_.readyStatus
    ) {
      skippedCount += 1;
      continue;
    }

    const registration = validateRegistration_({
      registrationId: row[4],
      name: row[0],
      email: row[1],
      session: row[2],
    });
    return {
      candidate: {
        rowNumber: index + 1,
        row: row.slice(),
        registration,
      },
      existingDocumentCount,
      skippedCount,
    };
  }

  return {
    candidate: null,
    existingDocumentCount,
    skippedCount,
  };
}

/**
 * 從範本複製並完成一份報名確認文件。
 *
 * @param {Object} registration 已驗證的報名資料。
 * @param {Object} resources 已核對的 Docs／Drive 資源。
 * @return {string} 新文件 ID；呼叫端不得寫入紀錄檔(Log)。
 */
function createRegistrationDocument_(registration, resources) {
  const documentName = buildLesson05DocumentName_(registration);
  let newFile;

  try {
    newFile = resources.templateFile.makeCopy(
      documentName,
      resources.outputFolder,
    );
    const documentId = newFile.getId();
    const document = DocumentApp.openById(documentId);
    const body = document.getBody();
    const replacements = {
      姓名: registration.name,
      活動場次: registration.session,
      報名編號: registration.registrationId,
    };

    LESSON05_CONFIG_.templateTokens.forEach((token) => {
      body.replaceText(
        token.pattern,
        escapeLesson05Replacement_(replacements[token.label]),
      );
    });
    document.saveAndClose();
    return documentId;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (newFile) {
      throw new Error(
        `文件副本已建立但內容處理失敗｜原因=${message}｜請勿重跑並人工檢查輸出資料夾`,
      );
    }
    throw error;
  }
}

/**
 * 產生不含 Email、且可辨識來源的文件名稱。
 *
 * @param {Object} registration 已驗證的報名資料。
 * @return {string} 文件名稱。
 */
function buildLesson05DocumentName_(registration) {
  const safeName = String(registration.name || '')
    .replace(/[\\/:*?"<>|]/g, '_')
    .slice(0, 40);
  const safeRegistrationId = String(registration.registrationId || '')
    .replace(/[\\/:*?"<>|]/g, '_')
    .slice(0, 40);
  return `${LESSON05_CONFIG_.documentNamePrefix}_${safeName}_${safeRegistrationId}`;
}

/**
 * 跳脫 Document Body.replaceText() 替換字串中的特殊字元。
 *
 * @param {*} value 替換值。
 * @return {string} 可安全使用的替換字串。
 */
function escapeLesson05Replacement_(value) {
  return String(value || '').replace(/\\/g, '\\\\').replace(/\$/g, '\\$');
}

/**
 * 一次寫回文件 ID、下一步狀態與最後更新時間。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 工作表。
 * @param {Object} candidate 本次候選。
 * @param {string} documentId 新文件 ID。
 * @param {Date} now 寫回時間。
 */
function writeLesson05Result_(sheet, candidate, documentId, now) {
  const row = candidate.row.slice();
  while (row.length < LESSON04_CONFIG_.headers.length) {
    row.push('');
  }
  row[3] = LESSON05_CONFIG_.createdStatus;
  row[5] = '';
  row[6] = documentId;
  row[8] = new Date(now.getTime());

  const values = [row.slice(3, 9)];
  const range = sheet.getRange(candidate.rowNumber, 4, 1, 6);
  validateLesson04WriteShape_(
    values,
    range.getNumRows(),
    range.getNumColumns(),
  );
  range.setValues(values);
}

/**
 * 第 5 課工程測試斷言。
 *
 * @param {boolean} condition 條件。
 * @param {string} message 失敗說明。
 */
function assertLesson05_(condition, message) {
  if (!condition) {
    throw new Error(`第 5 課測試失敗：${message}`);
  }
}
