const LESSON07_CONFIG_ = Object.freeze({
  batchSize: 1,
  intervalMinutes: 5,
  durationMinutes: 30,
  formHandler: 'onRegistrationFormSubmit',
  timerHandler: 'processPendingRegistrationsByTimer',
  expiryProperty: 'LESSON07_TRIGGER_EXPIRES_AT',
  timerAttemptProperty: 'LESSON07_TIMER_ATTEMPTED_AT',
});

/**
 * Sheets 日常入口：只讀檢查第 7 課需要的資源與安全上限。
 *
 * 本函式不建立觸發器、不建立文件、不寄信，也不修改工作表。
 *
 * @return {boolean} 設定是否通過。
 */
function checkLesson07Settings() {
  writeLessonLog_('開始', '檢查第 7 課設定');

  try {
    openLesson07Resources_();
    writeLesson07SettingsLog_(getScriptConfig_());
    writeLessonLog_(
      '成功',
      '第 7 課可安全使用前六課資源｜尚未建立觸發器｜尚未寄信',
    );
    return true;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    writeLesson07SettingsLog_(getScriptConfig_());
    writeLessonLog_(
      '失敗',
      `${message}｜未建立觸發器｜未建立文件｜未寄送郵件`,
    );
    throw error;
  }
}

/**
 * Sheets 日常入口：顯示目前兩種教學觸發器與安全期限狀態。
 *
 * @return {Object} 不含觸發器識別碼(ID)的狀態摘要。
 */
function checkLesson07Triggers() {
  const summary = summarizeLesson07Triggers_(
    ScriptApp.getProjectTriggers(),
  );
  const expiry = readLesson07Expiry_();
  const expiryState = describeLesson07Expiry_(expiry, new Date());

  writeLessonLog_(
    '設定',
    `教學觸發器｜表單提交=${summary.formCount}｜時間驅動=${summary.timerCount}｜安全期限=${expiryState.label}`,
  );

  SpreadsheetApp.getUi().alert(
    '第 7 課觸發器狀態',
    [
      `表單提交：${summary.formCount}`,
      `時間驅動：${summary.timerCount}`,
      `安全期限：${expiryState.display}`,
      '',
      '畫面不顯示觸發器識別碼(ID)。',
    ].join('\n'),
    SpreadsheetApp.getUi().ButtonSet.OK,
  );

  return {
    formCount: summary.formCount,
    timerCount: summary.timerCount,
    expiryState: expiryState.label,
  };
}

/**
 * Sheets 日常入口：經學生確認後建立表單提交觸發器。
 *
 * @return {Object} 建立或略過結果。
 */
function confirmLesson07FormTriggerSetup() {
  const ui = SpreadsheetApp.getUi();
  const response = ui.alert(
    '啟用表單提交自動處理',
    [
      '這會建立一個試算表表單提交觸發器(trigger)。',
      '新回覆只會被驗證並加入「活動報名資料」，不建立文件，也不寄信。',
      '觸發器會以目前執行者的 Google 帳號權限在背景執行。',
      '安全期限為 30 分鐘。確定繼續嗎？',
    ].join('\n'),
    ui.ButtonSet.YES_NO,
  );

  if (response !== ui.Button.YES) {
    writeLessonLog_('略過', '使用者取消啟用表單提交自動處理');
    return { createdCount: 0, cancelled: true };
  }

  const result = createLesson07FormTrigger_();
  ui.alert(
    '表單提交自動處理',
    result.createdCount === 1
      ? `已啟用。安全期限：${formatLesson07Expiry_(result.expiresAt)}`
      : '相同觸發器已存在，沒有重複建立。',
    ui.ButtonSet.OK,
  );
  return result;
}

/**
 * Sheets 日常入口：經學生確認後建立短暫時間觸發器。
 *
 * @return {Object} 建立或略過結果。
 */
function confirmLesson07TimeTriggerSetup() {
  const ui = SpreadsheetApp.getUi();
  const response = ui.alert(
    '啟用短暫時間處理',
    [
      '這會建立每 5 分鐘檢查一次的時間觸發器(trigger)。',
      '整次啟用只會嘗試處理 1 筆，可能在畫面未開啟時建立 1 份文件，並寄 1 封信到該筆報名資料的 Email。',
      '完成一次處理或遇到不確定結果後會自動停止；30 分鐘期限是額外保護。',
      '確定繼續嗎？',
    ].join('\n'),
    ui.ButtonSet.YES_NO,
  );

  if (response !== ui.Button.YES) {
    writeLessonLog_('略過', '使用者取消啟用短暫時間處理');
    return { createdCount: 0, cancelled: true };
  }

  const result = createLesson07TimeTrigger_();
  ui.alert(
    '短暫時間處理',
    result.createdCount === 1
      ? [
          '已啟用。',
          '間隔：5 分鐘',
          '整次啟用上限：1 筆',
          '處理後：自動停止時間處理',
          `安全期限：${formatLesson07Expiry_(result.expiresAt)}`,
        ].join('\n')
      : '相同觸發器已存在，沒有重複建立。',
    ui.ButtonSet.OK,
  );
  return result;
}

/**
 * Sheets 日常入口：只在確認後停止本課兩個已知觸發器。
 *
 * @return {Object} 刪除或取消結果。
 */
function confirmLesson07StopAutomation() {
  const ui = SpreadsheetApp.getUi();
  const response = ui.alert(
    '停止第 7 課自動化',
    [
      '這會刪除本課的「表單提交」與「短暫時間處理」觸發器。',
      '不會刪除同專案其他觸發器，也不會刪除工作表、文件或郵件。',
      '確定繼續嗎？',
    ].join('\n'),
    ui.ButtonSet.YES_NO,
  );

  if (response !== ui.Button.YES) {
    writeLessonLog_('略過', '使用者取消停止第 7 課自動化');
    return { deletedCount: 0, cancelled: true };
  }

  const result = stopLesson07Automation_();
  ui.alert(
    '第 7 課自動化已停止',
    `已刪除本課觸發器：${result.deletedCount} 個。`,
    ui.ButtonSet.OK,
  );
  return result;
}

/**
 * 安裝型觸發器回呼：把本次表單回覆驗證後加入業務工作表。
 *
 * 本函式不建立文件也不寄信，且不應從函式選單手動執行。
 *
 * @param {GoogleAppsScript.Events.SheetsOnFormSubmit} e 真實提交事件。
 * @return {Object} 新增、無效或重複略過結果。
 */
function onRegistrationFormSubmit(e) {
  writeLessonLog_('開始', '收到試算表表單提交事件');

  validateLesson07FormEventShape_(e);
  if (stopLesson07IfExpired_(new Date())) {
    return { insertedCount: 0, expired: true };
  }

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) {
    writeLessonLog_(
      '警告',
      '另一個表單事件正在處理｜本次沒有寫入｜交由觸發器錯誤紀錄追蹤',
    );
    throw new Error('目前無法取得第 7 課處理鎖');
  }

  try {
    const resources = openLesson07FormResources_();
    const eventData = readLesson07FormEvent_(e, resources.spreadsheet);
    const values = readLesson04SheetValues_(resources.sheet);
    const plan = planLesson07RegistrationAppend_(
      values,
      eventData.sourceKey,
      eventData.response,
      new Date(),
    );

    if (plan.action === 'skip') {
      writeLessonLog_('略過', '相同表單事件已處理｜沒有重複新增');
      return { insertedCount: 0, duplicate: true };
    }

    appendLesson07RegistrationRow_(resources.sheet, plan.row);
    if (plan.action === 'invalid') {
      writeLessonLog_(
        '警告',
        '表單回覆未通過驗證｜資料有誤=1｜沒有建立文件｜沒有寄信',
      );
      return { insertedCount: 1, invalidCount: 1 };
    }

    writeLessonLog_(
      '成功',
      '表單回覆已驗證｜待處理=1｜沒有建立文件｜沒有寄信',
    );
    return { insertedCount: 1, invalidCount: 0 };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    writeLessonLog_(
      '失敗',
      `${message}｜未建立文件｜未寄送郵件`,
    );
    throw error;
  } finally {
    lock.releaseLock();
  }
}

/**
 * 安裝型觸發器回呼：整次啟用最多嘗試一筆文件與通知流程。
 *
 * 業務動作前先留下單次嘗試記號，完成、結果不確定或錯誤時都停止本課
 * 時間觸發器。缺少真實時間事件或已超過安全期限時不執行業務動作。
 *
 * @param {GoogleAppsScript.Events.TimeDriven} e 真實時間觸發事件。
 * @return {Object} 文件與寄送數量。
 */
function processPendingRegistrationsByTimer(e) {
  writeLessonLog_(
    '開始',
    `時間觸發器開始處理｜批次上限=${LESSON07_CONFIG_.batchSize}`,
  );

  validateLesson07TimeEvent_(e);
  if (stopLesson07IfExpired_(new Date())) {
    return { documentCount: 0, sentCount: 0, expired: true };
  }
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) {
    writeLessonLog_(
      '警告',
      '另一個業務流程正在執行｜未建立文件｜未寄送郵件',
    );
    return { documentCount: 0, sentCount: 0, busy: true };
  }

  try {
    if (hasLesson07TimerAttempt_()) {
      const stopResult = stopLesson07TimerTrigger_();
      writeLessonLog_(
        '略過',
        `本次教學時間處理已執行過｜未再次建立文件｜未再次寄信` +
          `｜時間處理已自動停止=${stopResult.deletedCount}`,
      );
      return {
        documentCount: 0,
        sentCount: 0,
        alreadyAttempted: true,
        timerStopped: true,
      };
    }

    const resources = openLesson07Resources_();
    const values = readLesson04SheetValues_(resources.sheet);
    const action = planLesson07TimerAction_(values);
    let documentCount = 0;
    let sentCount = 0;
    let skippedCount = 0;

    if (action !== 'skip') {
      markLesson07TimerAttempt_(new Date());
    }

    if (action === 'blocked') {
      const result = executeLesson06RegistrationEmailSend_();
      const stopResult = stopLesson07TimerTrigger_();
      writeLessonLog_(
        '警告',
        `存在寄送結果尚未確認的資料｜未建立新文件｜未再次寄信` +
          `｜時間處理已自動停止=${stopResult.deletedCount}`,
      );
      return {
        documentCount: 0,
        sentCount: Number(result.sentCount || 0),
        uncertain: true,
        timerStopped: true,
      };
    }

    if (action === 'send') {
      const result = executeLesson06RegistrationEmailSend_();
      sentCount = Number(result.sentCount || 0);
      skippedCount = Number(result.skippedCount || 0);
    } else if (action === 'create-and-send') {
      const documentResult =
        createLesson07LatestRegistrationDocument_(resources);
      documentCount = Number(documentResult.createdCount || 0);
      if (documentCount === 1) {
        const sendResult = executeLesson06RegistrationEmailSend_();
        sentCount = Number(sendResult.sentCount || 0);
        skippedCount = Number(sendResult.skippedCount || 0);
      }
    }

    if (action === 'skip') {
      writeLessonLog_('略過', '沒有可處理的報名｜未建立文件｜未寄送郵件');
    } else {
      const stopResult = stopLesson07TimerTrigger_();
      writeLessonLog_(
        '成功',
        `時間批次處理完成｜文件=${documentCount}｜寄送=${sentCount}` +
          `｜略過=${skippedCount}｜時間處理已自動停止=${stopResult.deletedCount}`,
      );
      return {
        documentCount,
        sentCount,
        skippedCount,
        timerStopped: true,
      };
    }
    return { documentCount, sentCount, skippedCount };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    let stoppedCount = 0;
    try {
      stoppedCount = stopLesson07TimerTrigger_().deletedCount;
    } catch (stopError) {
      // 保留原始業務錯誤；停止失敗會由後續管理入口再次處理。
    }
    writeLessonLog_(
      '失敗',
      `時間批次處理停止｜原因=${message}` +
        `｜時間處理已自動停止=${stoppedCount}｜請先檢查工作表狀態`,
    );
    throw error;
  } finally {
    lock.releaseLock();
  }
}

/**
 * Agent 工程測試總入口：只執行純函式，不使用任何遠端服務。
 *
 * @return {boolean} 六項測試是否全部通過。
 */
function runLesson07ManualTests() {
  writeLessonLog_('開始', '執行第 7 課無遠端副作用工程測試');

  const base = [LESSON04_CONFIG_.headers.slice()];
  const valid = planLesson07RegistrationAppend_(
    base,
    'test-sheet|101',
    {
      name: '第7課測試學員',
      email: 'lesson07@example.com',
      session: '上午場',
    },
    new Date('2026-01-01T00:00:00.000Z'),
  );
  assertLesson07_(valid.action === 'insert', '有效事件應建立一筆待辦');
  assertLesson07_(
    valid.row[3] === LESSON05_CONFIG_.readyStatus,
    '有效事件應進入待產生文件狀態',
  );

  let missingEventRejected = false;
  try {
    validateLesson07TimeEvent_({});
  } catch (error) {
    missingEventRejected = true;
  }
  assertLesson07_(missingEventRejected, '缺少真實事件必須停止');

  assertLesson07_(
    LESSON07_CONFIG_.batchSize === 1,
    '程式內建批次上限必須固定為 1',
  );

  assertLesson07_(
    describeLesson07Expiry_(
      new Date('2026-01-01T00:00:00.000Z'),
      new Date('2026-01-01T00:00:01.000Z'),
    ).label === '已到期',
    '超過期限時必須辨識為已到期',
  );

  const duplicateSummary = summarizeLesson07Triggers_([
    buildLesson07TestTrigger_(
      LESSON07_CONFIG_.formHandler,
      ScriptApp.EventType.ON_FORM_SUBMIT,
      ScriptApp.TriggerSource.SPREADSHEETS,
    ),
    buildLesson07TestTrigger_(
      LESSON07_CONFIG_.formHandler,
      ScriptApp.EventType.ON_FORM_SUBMIT,
      ScriptApp.TriggerSource.SPREADSHEETS,
    ),
  ]);
  assertLesson07_(
    duplicateSummary.formCount === 2,
    '重複觸發器必須可被偵測',
  );

  const otherTrigger = buildLesson07TestTrigger_(
    'otherAutomation',
    ScriptApp.EventType.CLOCK,
    ScriptApp.TriggerSource.CLOCK,
  );
  const ownTimerTrigger = buildLesson07TestTrigger_(
    LESSON07_CONFIG_.timerHandler,
    ScriptApp.EventType.CLOCK,
    ScriptApp.TriggerSource.CLOCK,
  );
  const cleanupTargets = selectLesson07TriggersToDelete_([
    otherTrigger,
    ownTimerTrigger,
  ]);
  assertLesson07_(
    cleanupTargets.length === 1 && cleanupTargets[0] !== otherTrigger,
    '清理只能選取本課已知觸發器',
  );
  const timerCleanupTargets = selectLesson07TimerTriggersToDelete_([
    otherTrigger,
    ownTimerTrigger,
  ]);
  assertLesson07_(
    timerCleanupTargets.length === 1 &&
      timerCleanupTargets[0] === ownTimerTrigger,
    '單次處理後只能停止本課時間觸發器',
  );

  writeLessonLog_(
    '成功',
    '手動測試完成｜通過=6｜沒有修改遠端資料',
  );
  return true;
}

/**
 * 開啟並核對第 7 課累積流程需要的所有資源。
 *
 * @return {Object} 已通過檢查的設定、試算表與工作表。
 */
function openLesson07Resources_() {
  const resources = openLesson07FormResources_();
  const documentResources = openLesson05Resources_(resources.config);
  validateLesson05Template_(
    documentResources.templateDocument.getBody().getText(),
  );
  return resources;
}

/**
 * 只開啟表單提交與工作表待辦需要的資源。
 *
 * 表單提交事件不需要開啟文件範本或輸出資料夾，因此不會因為後段服務
 * 暫時不可用而遺失新回覆。
 *
 * @return {Object} 已通過檢查的設定、表單、試算表與工作表。
 */
function openLesson07FormResources_() {
  const config = getScriptConfig_();
  validateLesson07RequiredProperties_(config);
  const formResources = openLesson03Resources_();
  const destination = readLesson03DestinationId_(formResources.form);
  const destinationPlan = planLesson03Destination_(
    destination,
    formResources.spreadsheet.getId(),
  );
  if (destinationPlan.action !== 'keep') {
    throw new Error('活動報名表單尚未連結練習試算表');
  }

  const sheet = getLesson04Sheet_(formResources.spreadsheet);
  validateLesson05Headers_(readLesson05Headers_(sheet));

  return {
    config,
    form: formResources.form,
    spreadsheet: formResources.spreadsheet,
    sheet,
  };
}

/**
 * 為最新一筆待產生文件資料建立確認文件。
 *
 * 第 7 課優先處理剛由表單觸發器加入的資料，避免較早的課程假資料讓
 * 學生誤判本次表單到郵件的串接結果。每次仍只建立一份。
 *
 * @param {Object} resources 已核對的第 7 課資源。
 * @return {{createdCount: number, skippedCount: number}} 建立結果。
 */
function createLesson07LatestRegistrationDocument_(resources) {
  const values = readLesson04SheetValues_(resources.sheet);
  const plan = planLesson07LatestDocumentCandidate_(values);
  if (!plan.candidate) {
    return { createdCount: 0, skippedCount: plan.skippedCount };
  }

  const documentResources = openLesson05Resources_(resources.config);
  validateLesson05Template_(
    documentResources.templateDocument.getBody().getText(),
  );
  const documentId = createRegistrationDocument_(
    plan.candidate.registration,
    documentResources,
  );
  try {
    writeLesson05Result_(
      resources.sheet,
      plan.candidate,
      documentId,
      new Date(),
    );
  } catch (error) {
    throw new Error(
      '確認文件已建立但工作表寫回失敗｜請勿重跑並人工檢查輸出資料夾',
    );
  }

  writeLessonLog_('成功', '已建立報名確認文件｜建立數量=1');
  return { createdCount: 1, skippedCount: plan.skippedCount };
}

/**
 * 從後往前選出最新一筆待產生文件資料。
 *
 * @param {Array<Array<*>>} values 活動報名資料。
 * @return {{candidate: Object|null, skippedCount: number}} 候選計畫。
 */
function planLesson07LatestDocumentCandidate_(values) {
  validateLesson05Headers_(values && values[0]);
  let skippedCount = 0;

  for (let index = values.length - 1; index >= 1; index -= 1) {
    const row = Array.isArray(values[index]) ? values[index] : [];
    if (isLesson04BlankRow_(row)) {
      continue;
    }
    if (
      normalizeLesson02Setting_(row[3]) !==
        LESSON05_CONFIG_.readyStatus ||
      normalizeLesson02Setting_(row[6]) !== ''
    ) {
      skippedCount += 1;
      continue;
    }

    return {
      candidate: {
        rowNumber: index + 1,
        row: row.slice(),
        registration: validateRegistration_({
          registrationId: row[4],
          name: row[0],
          email: row[1],
          session: row[2],
        }),
      },
      skippedCount,
    };
  }
  return { candidate: null, skippedCount };
}

/**
 * 驗證第 7 課沿用的資源設定。
 *
 * 每次只處理一筆是程式內建的安全限制，不要求學員另外設定
 * 指令碼屬性(Script Properties)。
 *
 * @param {Object} config 集中式設定。
 * @return {boolean} 是否通過。
 */
function validateLesson07RequiredProperties_(config) {
  validateLesson05RequiredProperties_(config);
  validateLesson03FormSetting_(config);
  return true;
}

/**
 * 只顯示設定狀態與安全上限，不輸出任何資源實際值。
 *
 * @param {Object} config 集中式設定。
 */
function writeLesson07SettingsLog_(config) {
  const isConfigured = (field) =>
    normalizeLesson02Setting_(config && config[field]) !== '';

  writeLessonLog_(
    '設定',
    `SPREADSHEET_ID=${isConfigured('spreadsheetId') ? '已設定' : '未設定'}` +
      `｜FORM_ID=${isConfigured('formId') ? '已設定' : '未設定'}` +
      `｜DOC_TEMPLATE_ID=${isConfigured('docTemplateId') ? '已設定' : '未設定'}` +
      `｜OUTPUT_FOLDER_ID=${isConfigured('outputFolderId') ? '已設定' : '未設定'}` +
      `｜批次上限=${LESSON07_CONFIG_.batchSize}` +
      '｜收件來源=報名資料｜實際值不顯示',
  );
}

/**
 * 建立唯一的表單提交觸發器；已有一個時安全略過。
 *
 * @return {Object} 建立結果與安全期限。
 */
function createLesson07FormTrigger_() {
  const resources = openLesson07Resources_();
  const triggers = ScriptApp.getProjectTriggers();
  assertLesson07KnownTriggerState_(triggers, 'form');
  const before = summarizeLesson07Triggers_(triggers);
  if (before.formCount === 1) {
    const expiresAt = ensureLesson07Expiry_(new Date());
    writeLessonLog_('略過', '表單提交觸發器已存在｜沒有重複建立');
    return { createdCount: 0, alreadyExists: true, expiresAt };
  }

  let createdTrigger;
  try {
    createdTrigger = ScriptApp
      .newTrigger(LESSON07_CONFIG_.formHandler)
      .forSpreadsheet(resources.spreadsheet)
      .onFormSubmit()
      .create();
    const expiresAt = writeNewLesson07Expiry_(new Date());
    const after = summarizeLesson07Triggers_(
      ScriptApp.getProjectTriggers(),
    );
    if (after.formCount !== 1) {
      throw new Error('無法確認表單提交觸發器建立結果');
    }
    writeLessonLog_(
      '成功',
      '表單提交自動處理已啟用｜觸發器數量=1｜尚未寄信',
    );
    return { createdCount: 1, expiresAt };
  } catch (error) {
    if (createdTrigger) {
      ScriptApp.deleteTrigger(createdTrigger);
      PropertiesService
        .getScriptProperties()
        .deleteProperty(LESSON07_CONFIG_.expiryProperty);
    }
    throw error;
  }
}

/**
 * 建立唯一的短暫時間觸發器；已有一個時安全略過。
 *
 * @return {Object} 建立結果與安全期限。
 */
function createLesson07TimeTrigger_() {
  openLesson07Resources_();
  const triggers = ScriptApp.getProjectTriggers();
  assertLesson07KnownTriggerState_(triggers, 'timer');
  const before = summarizeLesson07Triggers_(triggers);
  if (before.timerCount === 1) {
    const expiresAt = ensureLesson07Expiry_(new Date());
    writeLessonLog_('略過', '時間觸發器已存在｜沒有重複建立');
    return { createdCount: 0, alreadyExists: true, expiresAt };
  }

  let createdTrigger;
  try {
    clearLesson07TimerAttempt_();
    createdTrigger = ScriptApp
      .newTrigger(LESSON07_CONFIG_.timerHandler)
      .timeBased()
      .everyMinutes(LESSON07_CONFIG_.intervalMinutes)
      .create();
    const expiresAt = writeNewLesson07Expiry_(new Date());
    const after = summarizeLesson07Triggers_(
      ScriptApp.getProjectTriggers(),
    );
    if (after.timerCount !== 1) {
      throw new Error('無法確認時間觸發器建立結果');
    }
    writeLessonLog_(
      '成功',
      `短暫時間處理已啟用｜間隔分鐘=${LESSON07_CONFIG_.intervalMinutes}｜批次上限=${LESSON07_CONFIG_.batchSize}`,
    );
    return { createdCount: 1, expiresAt };
  } catch (error) {
    clearLesson07TimerAttempt_();
    if (createdTrigger) {
      ScriptApp.deleteTrigger(createdTrigger);
      PropertiesService
        .getScriptProperties()
        .deleteProperty(LESSON07_CONFIG_.expiryProperty);
    }
    throw error;
  }
}

/**
 * 檢查指定類型是否出現重複或錯誤事件型別。
 *
 * @param {Array<Object>} triggers 專案觸發器。
 * @param {'form'|'timer'} target 目標種類。
 */
function assertLesson07KnownTriggerState_(triggers, target) {
  const summary = summarizeLesson07Triggers_(triggers);
  const count = target === 'form' ? summary.formCount : summary.timerCount;
  const invalidCount =
    target === 'form'
      ? summary.invalidFormCount
      : summary.invalidTimerCount;
  if (count > 1 || invalidCount > 0) {
    throw new Error('偵測到重複或類型不符的第 7 課觸發器｜請先停止並檢查');
  }
}

/**
 * 將觸發器依本課回呼函式與事件類型分類，不讀取或輸出識別碼(ID)。
 *
 * @param {Array<Object>} triggers 專案觸發器。
 * @return {Object} 分類數量。
 */
function summarizeLesson07Triggers_(triggers) {
  const summary = {
    formCount: 0,
    timerCount: 0,
    invalidFormCount: 0,
    invalidTimerCount: 0,
  };

  (triggers || []).forEach((trigger) => {
    const handler = trigger.getHandlerFunction();
    const eventType = trigger.getEventType();
    const source = trigger.getTriggerSource();
    if (handler === LESSON07_CONFIG_.formHandler) {
      if (
        eventType === ScriptApp.EventType.ON_FORM_SUBMIT &&
        source === ScriptApp.TriggerSource.SPREADSHEETS
      ) {
        summary.formCount += 1;
      } else {
        summary.invalidFormCount += 1;
      }
    } else if (handler === LESSON07_CONFIG_.timerHandler) {
      if (
        eventType === ScriptApp.EventType.CLOCK &&
        source === ScriptApp.TriggerSource.CLOCK
      ) {
        summary.timerCount += 1;
      } else {
        summary.invalidTimerCount += 1;
      }
    }
  });
  return summary;
}

/**
 * 解析真實 Sheets 表單提交事件，不保留完整事件或來源識別值。
 *
 * @param {Object} e 觸發事件。
 * @param {Object} expectedSpreadsheet 預期試算表。
 * @return {{sourceKey: string, response: Object}} 安全事件資料。
 */
function readLesson07FormEvent_(e, expectedSpreadsheet) {
  validateLesson07FormEventShape_(e);

  const sourceSheet = e.range.getSheet();
  const sourceSpreadsheet =
    e.source && typeof e.source.getId === 'function'
      ? e.source
      : sourceSheet.getParent();
  validateCourseSpreadsheetMatch_(
    expectedSpreadsheet.getId(),
    sourceSpreadsheet.getId(),
  );
  if (
    sourceSheet.getName() === LESSON04_CONFIG_.sheetName ||
    Number(e.range.getRow()) < 2
  ) {
    throw new Error('觸發事件不是活動報名表單的新回覆');
  }

  const response = extractLesson07Response_(e, sourceSheet);
  const sourceKey = [
    'spreadsheet-form-submit',
    sourceSheet.getSheetId(),
    e.range.getRow(),
  ].join('|');
  return { sourceKey, response };
}

/**
 * 在任何期限清理或遠端讀寫前，先確認這是真實表單提交事件。
 *
 * @param {Object} e 觸發事件。
 * @return {boolean} 是否具有必要事件欄位。
 */
function validateLesson07FormEventShape_(e) {
  if (
    !e ||
    normalizeLesson02Setting_(e.triggerUid) === '' ||
    !e.range ||
    typeof e.range.getSheet !== 'function'
  ) {
    throw new Error('缺少真實觸發事件');
  }
  return true;
}

/**
 * 優先從具名欄位讀取回覆，必要時才依回覆分頁表頭配對。
 *
 * @param {Object} e 表單提交事件。
 * @param {Object} sourceSheet 表單回覆分頁。
 * @return {{name: *, email: *, session: *}} 原始回覆。
 */
function extractLesson07Response_(e, sourceSheet) {
  const named = e.namedValues || {};
  const first = (value) =>
    Array.isArray(value) ? value[0] : value;
  if (
    Object.prototype.hasOwnProperty.call(named, '姓名') &&
    Object.prototype.hasOwnProperty.call(named, 'Email') &&
    Object.prototype.hasOwnProperty.call(named, '活動場次')
  ) {
    return {
      name: first(named['姓名']),
      email: first(named['Email']),
      session: first(named['活動場次']),
    };
  }

  if (!Array.isArray(e.values) || e.values.length === 0) {
    throw new Error('表單提交事件缺少必要欄位');
  }
  const width = e.values.length;
  const headers = sourceSheet
    .getRange(1, 1, 1, width)
    .getDisplayValues()[0]
    .map((value) => normalizeLesson02Setting_(value));
  const valueFor = (header) => {
    const index = headers.indexOf(header);
    if (index < 0) {
      throw new Error(`表單回覆分頁缺少欄位｜名稱=${header}`);
    }
    return e.values[index];
  };
  return {
    name: valueFor('姓名'),
    email: valueFor('Email'),
    session: valueFor('活動場次'),
  };
}

/**
 * 規劃一筆表單回覆的新增結果；相同來源只產生同一報名編號。
 *
 * @param {Array<Array<*>>} values 活動報名資料。
 * @param {string} sourceKey 不寫入紀錄檔(Log)的來源鍵。
 * @param {Object} response 表單欄位。
 * @param {Date} now 本次處理時間。
 * @return {{action: string, row?: Array<*>}} 新增計畫。
 */
function planLesson07RegistrationAppend_(
  values,
  sourceKey,
  response,
  now,
) {
  if (!Array.isArray(values) || values.length === 0) {
    throw new Error('活動報名資料不可為空');
  }
  validateLesson05Headers_(values[0]);
  const registrationId = createLesson03RegistrationId_(sourceKey);
  const exists = values.slice(1).some(
    (row) =>
      normalizeLesson02Setting_(row && row[4]) === registrationId,
  );
  if (exists) {
    return { action: 'skip' };
  }

  const baseRow = [
    normalizeLesson02Setting_(response && response.name),
    normalizeLesson02Setting_(response && response.email).toLowerCase(),
    normalizeLesson02Setting_(response && response.session),
    LESSON05_CONFIG_.readyStatus,
    registrationId,
    '',
    '',
    '',
    new Date(now.getTime()),
  ];
  try {
    const registration = validateRegistration_({
      registrationId,
      name: baseRow[0],
      email: baseRow[1],
      session: baseRow[2],
    });
    baseRow[0] = registration.name;
    baseRow[1] = registration.email;
    baseRow[2] = registration.session;
    return { action: 'insert', row: baseRow };
  } catch (error) {
    baseRow[3] = LESSON04_CONFIG_.invalidStatus;
    baseRow[5] = error instanceof Error ? error.message : String(error);
    return { action: 'invalid', row: baseRow };
  }
}

/**
 * 新增單一報名資料列，不覆寫既有資料或欄寬。
 *
 * @param {Object} sheet 活動報名資料工作表。
 * @param {Array<*>} row 完整資料列。
 */
function appendLesson07RegistrationRow_(sheet, row) {
  const values = [row.slice(0, LESSON04_CONFIG_.headers.length)];
  const range = sheet.getRange(
    Math.max(sheet.getLastRow(), 1) + 1,
    1,
    1,
    LESSON04_CONFIG_.headers.length,
  );
  validateLesson04WriteShape_(
    values,
    range.getNumRows(),
    range.getNumColumns(),
  );
  range.setValues(values);
}

/**
 * 驗證時間回呼來自真實安裝型觸發器。
 *
 * @param {Object} e 時間事件。
 * @return {boolean} 是否通過。
 */
function validateLesson07TimeEvent_(e) {
  if (!e || normalizeLesson02Setting_(e.triggerUid) === '') {
    writeLessonLog_('失敗', '缺少真實觸發事件｜未執行後續處理');
    throw new Error('缺少真實觸發事件');
  }
  return true;
}

/**
 * 每次只選擇一種動作，確保最多推進一筆報名。
 *
 * @param {Array<Array<*>>} values 活動報名資料。
 * @return {'blocked'|'send'|'create-and-send'|'skip'} 動作。
 */
function planLesson07TimerAction_(values) {
  validateLesson05Headers_(values && values[0]);
  const statuses = (values || [])
    .slice(1)
    .filter((row) => !isLesson04BlankRow_(row || []))
    .map((row) => normalizeLesson02Setting_(row[3]));

  if (statuses.includes(LESSON06_CONFIG_.sendingStatus)) {
    return 'blocked';
  }
  if (statuses.includes(LESSON06_CONFIG_.pendingStatus)) {
    return 'send';
  }
  if (statuses.includes(LESSON05_CONFIG_.readyStatus)) {
    return 'create-and-send';
  }
  return 'skip';
}

/**
 * 超過期限時停止業務並精準刪除本課觸發器。
 *
 * @param {Date} now 現在時間。
 * @return {boolean} 是否已停止。
 */
function stopLesson07IfExpired_(now) {
  const expiry = readLesson07Expiry_();
  const state = describeLesson07Expiry_(expiry, now);
  if (state.label === '有效') {
    return false;
  }

  stopLesson07Automation_();
  writeLessonLog_(
    '警告',
    state.label === '已到期'
      ? '教學自動化已到期並停止｜未建立文件｜未寄送郵件'
      : '教學自動化缺少安全期限並停止｜未建立文件｜未寄送郵件',
  );
  return true;
}

/**
 * 完成一次處理或遇到不確定結果後，只停止本課時間觸發器。
 *
 * 表單提交觸發器會保留到學生完成整課後再依確認清理，避免超出本次
 * 「一份文件、一封通知」的授權範圍。
 *
 * @return {{deletedCount: number}} 刪除結果。
 */
function stopLesson07TimerTrigger_() {
  const targets = selectLesson07TimerTriggersToDelete_(
    ScriptApp.getProjectTriggers(),
  );
  targets.forEach((trigger) => ScriptApp.deleteTrigger(trigger));
  return { deletedCount: targets.length };
}

/**
 * 只刪除本課兩個已知回呼函式的觸發器。
 *
 * @return {{deletedCount: number}} 刪除結果。
 */
function stopLesson07Automation_() {
  const targets = selectLesson07TriggersToDelete_(
    ScriptApp.getProjectTriggers(),
  );
  targets.forEach((trigger) => ScriptApp.deleteTrigger(trigger));
  PropertiesService
    .getScriptProperties()
    .deleteProperty(LESSON07_CONFIG_.expiryProperty);
  clearLesson07TimerAttempt_();
  writeLessonLog_(
    '成功',
    `第 7 課教學觸發器已停止｜刪除數量=${targets.length}`,
  );
  return { deletedCount: targets.length };
}

/**
 * @param {Array<Object>} triggers 專案觸發器。
 * @return {Array<Object>} 只屬於第 7 課的觸發器。
 */
function selectLesson07TriggersToDelete_(triggers) {
  return (triggers || []).filter((trigger) =>
    [
      LESSON07_CONFIG_.formHandler,
      LESSON07_CONFIG_.timerHandler,
    ].includes(trigger.getHandlerFunction()),
  );
}

/**
 * @param {Array<Object>} triggers 專案觸發器。
 * @return {Array<Object>} 只屬於第 7 課的時間觸發器。
 */
function selectLesson07TimerTriggersToDelete_(triggers) {
  return (triggers || []).filter(
    (trigger) =>
      trigger.getHandlerFunction() === LESSON07_CONFIG_.timerHandler,
  );
}

/**
 * 在業務動作前留下「本次已嘗試」記號，避免背景排程重複寄信。
 *
 * @param {Date} now 本次嘗試時間。
 */
function markLesson07TimerAttempt_(now) {
  PropertiesService
    .getScriptProperties()
    .setProperty(
      LESSON07_CONFIG_.timerAttemptProperty,
      now.toISOString(),
    );
}

/**
 * @return {boolean} 本次教學時間處理是否已經嘗試過。
 */
function hasLesson07TimerAttempt_() {
  return normalizeLesson02Setting_(
    PropertiesService
      .getScriptProperties()
      .getProperty(LESSON07_CONFIG_.timerAttemptProperty),
  ) !== '';
}

/**
 * 清除上一輪教學的單次處理記號。
 */
function clearLesson07TimerAttempt_() {
  PropertiesService
    .getScriptProperties()
    .deleteProperty(LESSON07_CONFIG_.timerAttemptProperty);
}

/**
 * 寫入新的 30 分鐘安全期限。
 *
 * @param {Date} now 現在時間。
 * @return {Date} 新期限。
 */
function writeNewLesson07Expiry_(now) {
  const expiresAt = new Date(
    now.getTime() + LESSON07_CONFIG_.durationMinutes * 60 * 1000,
  );
  PropertiesService
    .getScriptProperties()
    .setProperty(
      LESSON07_CONFIG_.expiryProperty,
      expiresAt.toISOString(),
    );
  return expiresAt;
}

/**
 * 已有有效期限時沿用；缺少或已到期時建立新期限。
 *
 * @param {Date} now 現在時間。
 * @return {Date} 可用期限。
 */
function ensureLesson07Expiry_(now) {
  const current = readLesson07Expiry_();
  const state = describeLesson07Expiry_(current, now);
  return state.label === '有效'
    ? current
    : writeNewLesson07Expiry_(now);
}

/**
 * @return {Date|null} 安全期限；未設定或格式無效時為 null。
 */
function readLesson07Expiry_() {
  const value = PropertiesService
    .getScriptProperties()
    .getProperty(LESSON07_CONFIG_.expiryProperty);
  const timestamp = Date.parse(normalizeLesson02Setting_(value));
  return Number.isFinite(timestamp) ? new Date(timestamp) : null;
}

/**
 * @param {Date|null} expiry 安全期限。
 * @param {Date} now 現在時間。
 * @return {{label: string, display: string}} 狀態與學生可讀文字。
 */
function describeLesson07Expiry_(expiry, now) {
  if (!(expiry instanceof Date) || Number.isNaN(expiry.getTime())) {
    return { label: '未設定', display: '未設定' };
  }
  if (expiry.getTime() <= now.getTime()) {
    return {
      label: '已到期',
      display: `${formatLesson07Expiry_(expiry)}（已到期）`,
    };
  }
  return { label: '有效', display: formatLesson07Expiry_(expiry) };
}

/**
 * @param {Date} date 日期時間。
 * @return {string} 台北時區顯示文字。
 */
function formatLesson07Expiry_(date) {
  return Utilities.formatDate(
    date,
    'Asia/Taipei',
    'yyyy/MM/dd HH:mm:ss',
  );
}

/**
 * 建立只供純函式工程測試使用的假觸發器。
 *
 * @param {string} handler 回呼函式名稱。
 * @param {*} eventType 事件類型。
 * @param {*} source 事件來源。
 * @return {Object} 假觸發器。
 */
function buildLesson07TestTrigger_(handler, eventType, source) {
  return {
    getHandlerFunction: () => handler,
    getEventType: () => eventType,
    getTriggerSource: () => source,
  };
}

/**
 * 第 7 課工程測試斷言。
 *
 * @param {boolean} condition 條件。
 * @param {string} message 失敗說明。
 */
function assertLesson07_(condition, message) {
  if (!condition) {
    throw new Error(`第 7 課測試失敗：${message}`);
  }
}
