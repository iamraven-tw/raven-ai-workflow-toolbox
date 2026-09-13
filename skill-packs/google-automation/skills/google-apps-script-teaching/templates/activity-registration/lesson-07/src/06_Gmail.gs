const LESSON06_CONFIG_ = Object.freeze({
  pendingStatus: '待寄送郵件',
  sendingStatus: '寄送中',
  sentStatus: '郵件已寄出',
  subjectPrefix: '[活動報名確認]',
  notificationHeader: '通知編號',
  legacyNotificationHeader: '郵件 ID',
  legacyFixtureEmails: Object.freeze({
    小明: 'xiaoming@example.com',
    小美: 'xiaomei@example.com',
  }),
});

/**
 * 學生入口：只讀檢查第 6 課的報名資料與第五課確認文件。
 *
 * 本函式不寄信、不建立草稿，也不修改工作表。收件人直接來自報名
 * 資料；紀錄檔(Log)不顯示實際地址。
 *
 * @return {boolean} 設定是否通過檢查。
 */
function checkLesson06Settings() {
  writeLessonLog_('開始', '準備檢查第 6 課設定');

  try {
    const spreadsheet = openCourseSpreadsheet_();
    const sheet = getLesson04Sheet_(spreadsheet);
    const values = readLesson04SheetValues_(sheet);
    validateLesson05Headers_(values[0]);
    const plan = planLesson06Candidate_(values);

    if (plan.candidate) {
      openLesson06Pdf_(plan.candidate.documentId);
    } else if (plan.uncertainCandidate) {
      openLesson06Pdf_(plan.uncertainCandidate.documentId);
    }

    writeLesson06SettingsLog_();
    writeLessonLog_(
      '成功',
      '第 6 課可安全使用報名資料與第五課確認文件｜尚未寄送郵件',
    );
    return true;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    writeLesson06SettingsLog_();
    writeLessonLog_('失敗', `${message}｜未寄送郵件｜未修改工作表`);
    throw error;
  }
}

/**
 * Sheets 日常入口：清楚說明實際收件來源，確認後才寄出一封郵件。
 *
 * @return {Object} 使用者取消或寄送函式的結果。
 */
function confirmLesson06RegistrationEmailSend() {
  const ui = SpreadsheetApp.getUi();
  const response = ui.alert(
    '寄送報名確認郵件',
    '這一步會從「活動報名資料」選出一筆待寄送資料，將確認文件真實寄到該列的 Email。本次只寄一封，寄件人是目前執行 Apps Script 的 Google 帳號。確定繼續嗎？',
    ui.ButtonSet.YES_NO,
  );

  if (response !== ui.Button.YES) {
    writeLessonLog_('略過', '使用者取消寄送｜未寄送郵件');
    return {
      sentCount: 0,
      cancelled: true,
    };
  }
  return sendLesson06RegistrationEmail_();
}

/**
 * Sheets 日常入口：只有使用者已確認郵件沒有寄出，才重設不確定狀態。
 *
 * 這個動作不寄信。舊版教學的「小明／小美」資料若仍使用 example.com，
 * 會一併改為目前授權執行者的 Email，其他真實報名者地址保持不變。
 *
 * @return {Object} 使用者取消或修復結果。
 */
function confirmLesson06UnsentRecovery() {
  const ui = SpreadsheetApp.getUi();
  const response = ui.alert(
    '確認未寄出並重設',
    '只有在你已確認收件匣與可用的寄送證據都沒有這封郵件時，才能繼續。這個動作只會重設一筆「寄送中」資料，不會寄信。確定繼續嗎？',
    ui.ButtonSet.YES_NO,
  );

  if (response !== ui.Button.YES) {
    writeLessonLog_('略過', '使用者取消重設｜未修改資料｜未寄送郵件');
    return {
      recoveredCount: 0,
      cancelled: true,
    };
  }
  return recoverLesson06UnsentRegistration_();
}

/**
 * 內部寄送入口：以指令碼鎖保護同一筆資料不會並行寄出兩封。
 *
 * @return {{
 *   sentCount: number,
 *   skippedCount?: number,
 *   uncertain?: boolean
 * }} 執行結果。
 */
function sendLesson06RegistrationEmail_() {
  writeLessonLog_('開始', '準備寄送報名確認郵件｜預計寄送=1');

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) {
    writeLessonLog_(
      '警告',
      '另一個寄送流程正在執行｜未寄送郵件｜請稍後檢查工作表狀態',
    );
    return {
      sentCount: 0,
      uncertain: true,
    };
  }

  try {
    return executeLesson06RegistrationEmailSend_();
  } finally {
    lock.releaseLock();
  }
}

/**
 * 在單一指令碼鎖內完成讀取、寄送與寫回。
 *
 * @return {{
 *   sentCount: number,
 *   skippedCount?: number,
 *   uncertain?: boolean
 * }} 執行結果。
 */
function executeLesson06RegistrationEmailSend_() {
  let sheet;
  let candidate;

  try {
    const spreadsheet = openCourseSpreadsheet_();
    sheet = getLesson04Sheet_(spreadsheet);
    const values = readLesson04SheetValues_(sheet);
    validateLesson05Headers_(values[0]);
    writeLesson06SettingsLog_();

    const plan = planLesson06Candidate_(values);
    if (plan.uncertainCandidate) {
      writeLessonLog_(
        '警告',
        '上次寄送結果尚未確認｜未再次寄信｜請先向收件人確認，再使用重設功能',
      );
      return {
        sentCount: 0,
        skippedCount: plan.skippedCount,
        uncertain: true,
      };
    }
    if (!plan.candidate) {
      if (plan.sentCount > 0) {
        writeLessonLog_('略過', '這筆報名已寄送完成｜沒有重複寄信');
      } else {
        writeLessonLog_('略過', '沒有待寄送郵件的報名｜未寄送郵件');
      }
      return {
        sentCount: 0,
        skippedCount: plan.skippedCount,
      };
    }

    candidate = plan.candidate;
    const pdf = openLesson06Pdf_(candidate.documentId);
    validateLesson06RemainingQuota_(MailApp.getRemainingDailyQuota());
    migrateLesson06NotificationHeader_(sheet, values[0]);

    const notificationId = createLesson06NotificationId_();
    writeLesson06State_(
      sheet,
      candidate,
      LESSON06_CONFIG_.sendingStatus,
      notificationId,
      new Date(),
    );
    SpreadsheetApp.flush();

    try {
      sendRegistrationConfirmationEmail_(
        candidate.registration,
        pdf,
        notificationId,
      );
    } catch (sendError) {
      const safeReason = summarizeLesson06SendError_(sendError);
      writeLessonLog_(
        '警告',
        `寄送結果無法確認｜原因=${safeReason}｜未再次寄信｜請先確認收件結果再使用重設功能`,
      );
      throw new Error(
        `寄送結果無法確認｜原因=${safeReason}｜請勿直接重跑`,
      );
    }

    try {
      writeLesson06State_(
        sheet,
        candidate,
        LESSON06_CONFIG_.sentStatus,
        notificationId,
        new Date(),
      );
    } catch (writeError) {
      const safeReason = summarizeLesson06SendError_(writeError);
      writeLessonLog_(
        '警告',
        `郵件可能已寄出但工作表寫回失敗｜原因=${safeReason}｜請勿重跑並向收件人確認`,
      );
      throw new Error('郵件寄送結果待人工確認｜請勿直接重跑');
    }

    writeLessonLog_('成功', '報名確認郵件已寄出｜寄送數量=1');
    return {
      sentCount: 1,
      skippedCount: plan.skippedCount,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (
      !message.includes('寄送結果無法確認') &&
      !message.includes('寄送結果待人工確認')
    ) {
      writeLessonLog_('失敗', `${message}｜未寄送郵件`);
    }
    throw error;
  }
}

/**
 * 重設一筆已由使用者確認「沒有寄出」的資料；本函式不呼叫寄信服務。
 *
 * @return {{recoveredCount: number, fixtureEmailUpdatedCount: number}} 修復結果。
 */
function recoverLesson06UnsentRegistration_() {
  writeLessonLog_('開始', '準備重設未完成的寄送資料｜不會寄信');

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) {
    writeLessonLog_(
      '警告',
      '另一個流程正在執行｜未修改資料｜未寄送郵件',
    );
    return {
      recoveredCount: 0,
      fixtureEmailUpdatedCount: 0,
      uncertain: true,
    };
  }

  try {
    const spreadsheet = openCourseSpreadsheet_();
    const sheet = getLesson04Sheet_(spreadsheet);
    const values = readLesson04SheetValues_(sheet);
    validateLesson05Headers_(values[0]);
    const plan = planLesson06Candidate_(values);

    if (!plan.uncertainCandidate) {
      writeLessonLog_('略過', '沒有需要重設的「寄送中」資料｜未修改資料');
      return {
        recoveredCount: 0,
        fixtureEmailUpdatedCount: 0,
      };
    }

    const legacyRows = findLesson06LegacyFixtureRows_(values);
    let fixtureEmailUpdatedCount = 0;
    let learnerEmail = '';
    if (legacyRows.length > 0) {
      learnerEmail = getLesson01LearnerEmail_();
      fixtureEmailUpdatedCount = applyLesson06FixtureEmailUpdates_(
        sheet,
        values,
        legacyRows,
        learnerEmail,
      );
    }

    migrateLesson06NotificationHeader_(sheet, values[0]);

    const candidate = plan.uncertainCandidate;
    const updatedCandidate = {
      ...candidate,
      row: candidate.row.slice(),
    };
    const matchingLegacy = legacyRows.find(
      (item) => item.rowNumber === candidate.rowNumber,
    );
    if (matchingLegacy) {
      updatedCandidate.row[1] = learnerEmail;
    }
    writeLesson06State_(
      sheet,
      updatedCandidate,
      LESSON06_CONFIG_.pendingStatus,
      '',
      new Date(),
    );

    writeLessonLog_(
      '成功',
      `未完成寄送已重設｜重設筆數=1｜教學信箱更新=${fixtureEmailUpdatedCount}｜未寄送郵件`,
    );
    return {
      recoveredCount: 1,
      fixtureEmailUpdatedCount,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    writeLessonLog_(
      '失敗',
      `重設未完成｜原因=${message}｜未寄送郵件`,
    );
    throw error;
  } finally {
    lock.releaseLock();
  }
}

/**
 * Agent 工程測試：錯誤資料與不確定狀態都必須在寄送前停止。
 */
function runLesson06ErrorTests() {
  writeLessonLog_('開始', '執行第 6 課錯誤與不確定狀態測試');

  let rejectedInvalidEmail = false;
  try {
    validateLesson06Email_('invalid-email');
  } catch (error) {
    rejectedInvalidEmail = true;
  }
  assertLesson06_(rejectedInvalidEmail, '無效報名 Email 應被拒絕');

  let rejectedMissingDocument = false;
  try {
    validateLesson06DocumentId_('');
  } catch (error) {
    rejectedMissingDocument = true;
  }
  assertLesson06_(rejectedMissingDocument, '缺少文件 ID 應被拒絕');

  const uncertainPlan = planLesson06Candidate_([
    LESSON04_CONFIG_.headers.slice(),
    buildLesson06TestRow_(LESSON06_CONFIG_.sendingStatus, 'test-document'),
  ]);
  assertLesson06_(
    Boolean(uncertainPlan.uncertainCandidate) &&
      !uncertainPlan.candidate,
    '寄送中資料必須停止且不得成為寄送候選',
  );

  writeLessonLog_(
    '成功',
    '第 6 課錯誤測試全部通過｜無效Email=未寄送｜缺少文件=未寄送｜寄送中=未重寄',
  );
}

/**
 * Agent 工程測試：已寄送資料重跑時不得再次成為候選。
 */
function testLesson06Repeat() {
  writeLessonLog_('開始', '執行第 6 課重複寄送測試');

  const plan = planLesson06Candidate_([
    LESSON04_CONFIG_.headers.slice(),
    buildLesson06TestRow_(
      LESSON06_CONFIG_.sentStatus,
      'test-document',
      'NOTICE-EXISTING',
    ),
  ]);
  assertLesson06_(!plan.candidate, '已寄送資料不應再次成為候選');
  assertLesson06_(plan.sentCount === 1, '應辨識一筆已寄送資料');

  writeLessonLog_('成功', '第 6 課重複測試通過｜未呼叫寄信服務');
}

/**
 * 只記錄資料來源與執行身分，不顯示任何實際 Email。
 */
function writeLesson06SettingsLog_() {
  writeLessonLog_(
    '設定',
    '收件來源=活動報名資料｜寄件帳號=目前執行者｜實際地址不顯示',
  );
}

/**
 * 驗證報名資料中的單一基本 Email 格式。
 *
 * @param {*} value 報名資料 Email。
 * @return {boolean} 是否通過。
 */
function validateLesson06Email_(value) {
  const email = normalizeLesson02Setting_(value).toLowerCase();
  const emailPattern = /^[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+$/;
  if (!emailPattern.test(email)) {
    throw new Error('報名資料 Email 格式不正確');
  }
  return true;
}

/**
 * 寄送前確認今天至少還能寄給一位收件人。
 *
 * @param {*} remaining 剩餘收件人配額。
 * @return {boolean} 是否可寄送。
 */
function validateLesson06RemainingQuota_(remaining) {
  if (!Number.isFinite(Number(remaining)) || Number(remaining) < 1) {
    throw new Error('今天的郵件收件人配額不足');
  }
  return true;
}

/**
 * 規劃第一筆待寄送資料；任何「寄送中」資料都優先要求人工確認。
 *
 * @param {Array<Array<*>>} values 工作表完整資料。
 * @return {{
 *   candidate: Object|null,
 *   uncertainCandidate: Object|null,
 *   sentCount: number,
 *   skippedCount: number
 * }} 本次寄送計畫。
 */
function planLesson06Candidate_(values) {
  if (!Array.isArray(values) || values.length === 0) {
    throw new Error('活動報名資料不可為空');
  }
  validateLesson05Headers_(values[0]);

  let candidate = null;
  let uncertainCandidate = null;
  let sentCount = 0;
  let skippedCount = 0;

  for (let index = 1; index < values.length; index += 1) {
    const row = Array.isArray(values[index]) ? values[index] : [];
    if (isLesson04BlankRow_(row)) {
      continue;
    }

    const status = normalizeLesson02Setting_(row[3]);
    if (status === LESSON06_CONFIG_.sendingStatus) {
      uncertainCandidate = buildLesson06Candidate_(row, index + 1);
      break;
    }
    if (status === LESSON06_CONFIG_.sentStatus) {
      sentCount += 1;
      skippedCount += 1;
      continue;
    }
    if (status !== LESSON06_CONFIG_.pendingStatus) {
      skippedCount += 1;
      continue;
    }
    if (!candidate) {
      candidate = buildLesson06Candidate_(row, index + 1);
      continue;
    }
    skippedCount += 1;
  }

  return {
    candidate: uncertainCandidate ? null : candidate,
    uncertainCandidate,
    sentCount,
    skippedCount,
  };
}

/**
 * 將工作表列轉成已驗證的寄送候選。
 *
 * @param {Array<*>} row 工作表資料列。
 * @param {number} rowNumber 實際列號。
 * @return {Object} 寄送候選。
 */
function buildLesson06Candidate_(row, rowNumber) {
  const documentId = normalizeLesson02Setting_(row[6]);
  validateLesson06DocumentId_(documentId);

  const registration = validateRegistration_({
    registrationId: row[4],
    name: row[0],
    email: row[1],
    session: row[2],
  });
  validateLesson06Email_(registration.email);
  return {
    rowNumber,
    row: row.slice(),
    documentId,
    registration,
  };
}

/**
 * 驗證第五課文件 ID 已存在。
 *
 * @param {*} value 文件 ID。
 * @return {boolean} 是否通過。
 */
function validateLesson06DocumentId_(value) {
  if (normalizeLesson02Setting_(value) === '') {
    throw new Error('找不到第五課確認文件');
  }
  return true;
}

/**
 * 開啟第五課 Google 文件並即時轉成 PDF，不建立額外檔案。
 *
 * @param {string} documentId 文件 ID；不得寫入紀錄檔(Log)。
 * @return {GoogleAppsScript.Base.Blob} PDF 附件。
 */
function openLesson06Pdf_(documentId) {
  validateLesson06DocumentId_(documentId);

  try {
    const file = DriveApp.getFileById(documentId);
    if (file.getMimeType() !== MimeType.GOOGLE_DOCS) {
      throw new Error('指定檔案不是 Google 文件');
    }
    return file
      .getAs(MimeType.PDF)
      .setName('活動報名確認.pdf');
  } catch (error) {
    throw new Error('找不到第五課確認文件｜請檢查工作表的文件 ID');
  }
}

/**
 * 唯一寄信邊界：使用只能寄信、不能讀取 Gmail 信箱的 MailApp。
 *
 * @param {Object} registration 已驗證的報名資料。
 * @param {GoogleAppsScript.Base.Blob} pdf PDF 附件。
 * @param {string} notificationId 本次通知編號。
 */
function sendRegistrationConfirmationEmail_(
  registration,
  pdf,
  notificationId,
) {
  validateLesson06Email_(registration.email);
  const subject =
    `${LESSON06_CONFIG_.subjectPrefix} ${registration.registrationId}｜${notificationId}`;
  const body = [
    '您好，以下是你的活動報名確認資料。',
    '',
    `姓名：${registration.name}`,
    `活動場次：${registration.session}`,
    `報名編號：${registration.registrationId}`,
    `通知編號：${notificationId}`,
    '',
    '附件為本次活動的報名確認 PDF。',
  ].join('\n');

  MailApp.sendEmail(
    registration.email,
    subject,
    body,
    {
      attachments: [pdf],
      name: '活動報名與通知系統',
    },
  );
}

/**
 * 建立不含個資、可在工作表與郵件主旨互相核對的通知編號。
 *
 * @return {string} 通知編號。
 */
function createLesson06NotificationId_() {
  const suffix = String(Utilities.getUuid() || '')
    .replace(/[^a-zA-Z0-9]/g, '')
    .slice(0, 12)
    .toUpperCase();
  if (suffix === '') {
    throw new Error('無法建立通知編號');
  }
  return `NOTICE-${suffix}`;
}

/**
 * 將舊版「郵件 ID」欄位安全改名為「通知編號」。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 工作表。
 * @param {Array<*>} headers 現有表頭。
 * @return {boolean} 是否修改。
 */
function migrateLesson06NotificationHeader_(sheet, headers) {
  validateLesson05Headers_(headers);
  const current = normalizeLesson02Setting_(headers[7]);
  if (current === LESSON06_CONFIG_.notificationHeader) {
    return false;
  }
  if (current !== LESSON06_CONFIG_.legacyNotificationHeader) {
    throw new Error('通知欄位不相容｜未修改工作表');
  }
  sheet
    .getRange(1, 8, 1, 1)
    .setValues([[LESSON06_CONFIG_.notificationHeader]]);
  headers[7] = LESSON06_CONFIG_.notificationHeader;
  return true;
}

/**
 * 找出舊版小明／小美資料；只接受教材原本的固定 example.com 地址。
 *
 * @param {Array<Array<*>>} values 工作表資料。
 * @return {Array<{rowNumber: number, name: string}>} 待更新列。
 */
function findLesson06LegacyFixtureRows_(values) {
  const rows = [];
  for (let index = 1; index < values.length; index += 1) {
    const row = Array.isArray(values[index]) ? values[index] : [];
    const name = normalizeLesson02Setting_(row[0]);
    const email = normalizeLesson01Email_(row[1]);
    const expected = LESSON06_CONFIG_.legacyFixtureEmails[name];
    if (expected && email === expected) {
      rows.push({
        rowNumber: index + 1,
        name,
      });
    }
  }
  return rows;
}

/**
 * 只更新可明確辨識的舊版教學資料 Email，不碰觸其他報名者。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 工作表。
 * @param {Array<Array<*>>} values 工作表資料。
 * @param {Array<{rowNumber: number}>} legacyRows 待更新列。
 * @param {string} learnerEmail 目前授權執行者 Email。
 * @return {number} 更新筆數。
 */
function applyLesson06FixtureEmailUpdates_(
  sheet,
  values,
  legacyRows,
  learnerEmail,
) {
  const email = normalizeLesson01Email_(learnerEmail);
  validateLesson06Email_(email);

  legacyRows.forEach(({ rowNumber }) => {
    sheet.getRange(rowNumber, 2, 1, 1).setValues([[email]]);
    values[rowNumber - 1][1] = email;
  });
  return legacyRows.length;
}

/**
 * 寄送前後一次寫回狀態、通知編號與時間。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 工作表。
 * @param {Object} candidate 寄送候選。
 * @param {string} status 新狀態。
 * @param {string} notificationId 通知編號；重設時為空白。
 * @param {Date} now 寫回時間。
 */
function writeLesson06State_(
  sheet,
  candidate,
  status,
  notificationId,
  now,
) {
  const row = candidate.row.slice();
  while (row.length < LESSON04_CONFIG_.headers.length) {
    row.push('');
  }
  row[3] = status;
  row[5] = '';
  row[7] = normalizeLesson02Setting_(notificationId);
  row[8] = new Date(now.getTime());

  const values = [row.slice(3, 9)];
  const range = sheet.getRange(candidate.rowNumber, 4, 1, 6);
  validateLesson04WriteShape_(
    values,
    range.getNumRows(),
    range.getNumColumns(),
  );
  range.setValues(values);
  candidate.row = row;
}

/**
 * 將寄信服務錯誤整理成不含 Email 與長識別碼的繁體中文診斷訊息。
 *
 * @param {*} error 原始例外。
 * @return {string} 可安全放進紀錄檔(Log)的原因。
 */
function summarizeLesson06SendError_(error) {
  const original = error instanceof Error ? error.message : String(error);
  const sanitized = String(original || '未知錯誤')
    .replace(/[^\s@]+@[^\s@]+/g, '[Email已隱藏]')
    .replace(/\b[a-zA-Z0-9_-]{24,}\b/g, '[識別碼已隱藏]')
    .slice(0, 180);
  let category = '郵件服務發生錯誤';

  if (/authoriz|permission|oauth|scope/i.test(original)) {
    category = 'Google 授權不足或已失效';
  } else if (/quota|limit|too many/i.test(original)) {
    category = '寄信配額不足';
  } else if (/disabled|not enabled|has not been used/i.test(original)) {
    category = '郵件服務尚未啟用或無法使用';
  } else if (/invalid.*email|recipient|address/i.test(original)) {
    category = '收件地址無法使用';
  }

  return `${category}｜原始訊息=${sanitized}`;
}

/**
 * 建立只供 Apps Script 內部測試使用的假資料列。
 *
 * @param {string} status 處理狀態。
 * @param {string} documentId 假文件 ID。
 * @param {string=} notificationId 假通知編號。
 * @return {Array<*>} 假資料列。
 */
function buildLesson06TestRow_(status, documentId, notificationId) {
  return [
    '第6課測試學員',
    'lesson06@example.com',
    '上午場',
    status,
    'REG-LESSON0601',
    '',
    documentId,
    notificationId || '',
    '',
  ];
}

/**
 * 第 6 課工程測試斷言。
 *
 * @param {boolean} condition 條件。
 * @param {string} message 失敗說明。
 */
function assertLesson06_(condition, message) {
  if (!condition) {
    throw new Error(`第 6 課測試失敗：${message}`);
  }
}
