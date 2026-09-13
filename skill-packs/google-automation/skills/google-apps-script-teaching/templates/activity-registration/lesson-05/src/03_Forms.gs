const LESSON03_CONFIG_ = Object.freeze({
  formTitle: '活動報名表單',
  formDescription:
    '本表單供 Apps Script 教學與實際流程驗收使用。會進入寄信測試的資料，請填寫你能親自收信的 Email。',
  confirmationMessage: '報名資料已送出。本課尚未啟用自動處理。',
  sessions: Object.freeze(['上午場', '下午場']),
  pendingStatus: '待處理',
  fields: Object.freeze([
    Object.freeze({
      key: 'name',
      title: '姓名',
      type: 'TEXT',
      helpText: '請使用測試假姓名，例如：測試學員。',
    }),
    Object.freeze({
      key: 'email',
      title: 'Email',
      type: 'TEXT',
      helpText: '寄信驗收請填寫你能親自收信的 Email；錯誤格式測試不會送出。',
    }),
    Object.freeze({
      key: 'session',
      title: '活動場次',
      type: 'MULTIPLE_CHOICE',
      helpText: '請選擇一個活動場次。',
    }),
  ]),
});

/**
 * 學生入口：檢查試算表與表單門牌號碼是否都可安全使用。
 *
 * 本函式只讀取設定與遠端資源資訊，不修改表單或試算表。
 *
 * @return {boolean} 設定是否通過。
 */
function checkLesson03Settings() {
  writeLessonLog_('開始', '準備檢查第 3 課設定');

  try {
    const resources = openLesson03Resources_();
    writeLesson03SettingsLog_(resources.config);
    writeLessonLog_('成功', '第 3 課設定可開啟指定的試算表與表單');
    return true;
  } catch (error) {
    const config = getScriptConfig_();
    const message = error instanceof Error ? error.message : String(error);
    writeLesson03SettingsLog_(config);
    writeLessonLog_('失敗', `${message}｜未修改表單或試算表資料`);
    throw error;
  }
}

/**
 * 學生入口：安全設定活動報名表單並連結既有練習試算表。
 *
 * 重複執行只核對同一份表單，不建立新表單、不新增重複欄位，
 * 也不重設已經正確的回覆目的地。
 *
 * @return {{
 *   changed: boolean,
 *   itemCount: number,
 *   destinationLinked: boolean
 * }} 設定結果。
 */
function setupLesson03Form() {
  writeLessonLog_('開始', '準備活動報名表單');

  try {
    const resources = openLesson03Resources_();
    const form = resources.form;
    const spreadsheet = resources.spreadsheet;
    writeLesson03SettingsLog_(resources.config);

    const destinationPlan = planLesson03Destination_(
      readLesson03DestinationId_(form),
      spreadsheet.getId(),
    );
    const items = form.getItems();
    const itemSummaries = summarizeLesson03Items_(items);
    const itemPlan = planLesson03Items_(itemSummaries);
    const metadataPlan = planLesson03Metadata_({
      title: form.getTitle(),
      description: form.getDescription(),
      confirmationMessage: form.getConfirmationMessage(),
      acceptingResponses: form.isAcceptingResponses(),
      collectsEmail: form.collectsEmail(),
    });

    if (
      (itemPlan.existingCorrections.length > 0 ||
        itemPlan.recoverableBlankItemIndex !== null) &&
      form.getResponses().length > 0
    ) {
      throw new Error(
        '表單已有回覆且既有欄位設定不符｜為避免破壞回覆，未自動修改',
      );
    }

    applyLesson03Metadata_(form, metadataPlan);
    applyLesson03Items_(form, items, itemPlan);
    if (destinationPlan.action === 'link') {
      form.setDestination(
        FormApp.DestinationType.SPREADSHEET,
        spreadsheet.getId(),
      );
    }

    const changed =
      metadataPlan.changed ||
      itemPlan.changed ||
      destinationPlan.action === 'link';
    const itemCount = form.getItems().length;

    if (changed) {
      writeLessonLog_(
        '成功',
        `活動報名表單已可使用｜欄位數=${itemCount}｜回覆已連結練習試算表`,
      );
    } else {
      writeLessonLog_(
        '略過',
        `活動報名表單已符合設定｜欄位數=${itemCount}｜沒有新增重複欄位`,
      );
    }

    return {
      changed,
      itemCount,
      destinationLinked: true,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    writeLessonLog_(
      '失敗',
      `無法設定活動報名表單｜原因=${message}｜請停止並檢查設定`,
    );
    throw error;
  }
}

/**
 * Agent 工程測試：正常假資料應通過第二層驗證並規劃一筆結果。
 */
function testLesson03Normal() {
  writeLessonLog_('開始', '執行第 3 課正常資料測試');

  const registration = buildLesson03Registration_('test-response-001', {
    name: '測試學員',
    email: 'student@example.com',
    session: '上午場',
  });
  const result = planLesson03Registration_([], registration);

  assertLesson03_(result.changed, '正常資料應規劃新增一筆結果');
  assertLesson03_(result.records.length === 1, '正常資料結果筆數應為一筆');
  assertLesson03_(
    result.records[0].status === LESSON03_CONFIG_.pendingStatus,
    '正常資料應建立待處理狀態',
  );

  writeLessonLog_('成功', '第 3 課正常資料測試通過｜結果筆數=1');
}

/**
 * Agent 工程測試：Email 格式錯誤時不得進入後續處理。
 */
function testLesson03InvalidEmail() {
  writeLessonLog_('開始', '執行第 3 課錯誤 Email 測試');

  try {
    const registration = buildLesson03Registration_('test-response-002', {
      name: '測試學員',
      email: 'not-an-email',
      session: '下午場',
    });
    planLesson03Registration_([], registration);
  } catch (error) {
    writeLessonLog_(
      '失敗',
      '報名資料驗證失敗｜欄位=Email｜原因=格式不正確｜未進入後續處理',
    );
    writeLessonLog_('成功', '第 3 課錯誤 Email 測試通過');
    return;
  }

  throw new Error('錯誤 Email 測試失敗：無效資料沒有被拒絕');
}

/**
 * Agent 工程測試：相同報名編號重跑時只保留一筆業務結果。
 */
function testLesson03Repeat() {
  writeLessonLog_('開始', '執行第 3 課重複資料測試');

  const registration = buildLesson03Registration_('test-response-003', {
    name: '測試學員',
    email: 'repeat@example.com',
    session: '上午場',
  });
  const first = planLesson03Registration_([], registration);
  const second = planLesson03Registration_(first.records, registration);

  assertLesson03_(!second.changed, '重複報名編號不應再次新增結果');
  assertLesson03_(
    second.records.length === 1,
    '重複執行後應只保留一筆業務結果',
  );

  writeLessonLog_('略過', '報名編號已存在｜沒有重複新增');
}

/**
 * 開啟並核對第 3 課指定的試算表與表單。
 *
 * @return {{
 *   config: {spreadsheetId: string, formId: string},
 *   spreadsheet: GoogleAppsScript.Spreadsheet.Spreadsheet,
 *   form: GoogleAppsScript.Forms.Form
 * }} 已核對的資源。
 */
function openLesson03Resources_() {
  const config = getScriptConfig_();
  validateRequiredProperties_(config);
  validateLesson03FormSetting_(config);

  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  if (!spreadsheet) {
    throw new Error('目前專案沒有綁定可使用的 Google Sheets');
  }
  validateCourseSpreadsheetMatch_(config.spreadsheetId, spreadsheet.getId());

  let form;
  try {
    form = FormApp.openById(config.formId);
  } catch (error) {
    throw new Error('FORM_ID 無法開啟指定表單｜請檢查設定與存取權');
  }
  validateLesson03FormIdentity_(form);

  return { config, spreadsheet, form };
}

/**
 * 驗證 FORM_ID 已設定。
 *
 * @param {{formId: string}} config 集中式設定。
 * @return {boolean} 是否通過。
 */
function validateLesson03FormSetting_(config) {
  if (!config || normalizeLesson02Setting_(config.formId) === '') {
    throw new Error(
      `缺少必要的指令碼屬性｜名稱=${COURSE_PROPERTY_NAMES_.formId}`,
    );
  }
  return true;
}

/**
 * 核對表單名稱，避免在錯誤資源上繼續。
 *
 * @param {GoogleAppsScript.Forms.Form} form 表單。
 * @return {boolean} 是否通過。
 */
function validateLesson03FormIdentity_(form) {
  if (!form || form.getTitle() !== LESSON03_CONFIG_.formTitle) {
    throw new Error('FORM_ID 指向的表單名稱不符｜已停止後續修改');
  }
  return true;
}

/**
 * 只顯示設定狀態，不輸出實際門牌號碼。
 *
 * @param {{spreadsheetId: string, formId: string}} config 集中式設定。
 */
function writeLesson03SettingsLog_(config) {
  const spreadsheetConfigured =
    normalizeLesson02Setting_(config && config.spreadsheetId) !== '';
  const formConfigured =
    normalizeLesson02Setting_(config && config.formId) !== '';

  writeLessonLog_(
    '設定',
    `SPREADSHEET_ID=${spreadsheetConfigured ? '已設定' : '未設定'}` +
      `｜FORM_ID=${formConfigured ? '已設定' : '未設定'}｜實際值不顯示`,
  );
}

/**
 * 安全讀取回覆目的地。
 *
 * Google Forms 在第一次尚未連結目的地時會丟出特定例外；這是可繼續
 * 建立連結的正常狀態。其他服務錯誤仍要原樣拋出，不能掩蓋問題。
 *
 * @param {GoogleAppsScript.Forms.Form} form 表單。
 * @return {string} 目前目的地 ID；尚未連結時為空字串。
 */
function readLesson03DestinationId_(form) {
  try {
    return normalizeLesson02Setting_(form.getDestinationId());
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (message.includes('no response destination')) {
      return '';
    }
    throw error;
  }
}

/**
 * 規劃回覆目的地；既有目的地不符時停止，不自動改綁。
 *
 * @param {*} currentDestinationId 目前目的地 ID。
 * @param {*} expectedSpreadsheetId 預期試算表 ID。
 * @return {{action: 'link'|'keep'}} 設定計畫。
 */
function planLesson03Destination_(
  currentDestinationId,
  expectedSpreadsheetId,
) {
  const current = normalizeLesson02Setting_(currentDestinationId);
  const expected = normalizeLesson02Setting_(expectedSpreadsheetId);

  if (expected === '') {
    throw new Error('找不到可連結的練習試算表');
  }
  if (current === '') {
    return { action: 'link' };
  }
  if (current !== expected) {
    throw new Error('表單已連結其他回覆試算表｜未自動改綁');
  }
  return { action: 'keep' };
}

/**
 * 將既有表單欄位轉成不含私人資料的設定摘要。
 *
 * @param {Array<GoogleAppsScript.Forms.Item>} items 表單欄位。
 * @return {Array<Object>} 欄位摘要。
 */
function summarizeLesson03Items_(items) {
  return items.map((item) => {
    const type = String(item.getType());
    let required = false;
    let helpText = '';
    let choices = [];

    if (type === 'TEXT') {
      const textItem = item.asTextItem();
      required = textItem.isRequired();
      helpText = textItem.getHelpText();
    } else if (type === 'MULTIPLE_CHOICE') {
      const choiceItem = item.asMultipleChoiceItem();
      required = choiceItem.isRequired();
      helpText = choiceItem.getHelpText();
      choices = choiceItem.getChoices().map((choice) => choice.getValue());
    }

    return {
      index: item.getIndex(),
      title: item.getTitle(),
      type,
      required,
      helpText,
      choices,
    };
  });
}

/**
 * 規劃三個表單欄位，拒絕未知、重複、錯誤型別或錯誤順序。
 *
 * @param {Array<Object>} summaries 既有欄位摘要。
 * @return {{
 *   changed: boolean,
 *   missingKeys: Array<string>,
 *   existingCorrections: Array<string>,
 *   recoverableBlankItemIndex: number|null
 * }} 欄位計畫。
 */
function planLesson03Items_(summaries) {
  // 首次失敗版本可能留下唯一一個未命名文字欄位；只接受這個精確狀態。
  const recoverableBlankItem =
    summaries.length === 1 &&
    summaries[0].title === '' &&
    summaries[0].type === 'TEXT' &&
    summaries[0].required === false &&
    summaries[0].helpText === '' &&
    summaries[0].choices.length === 0
      ? summaries[0]
      : null;
  const summariesToValidate = recoverableBlankItem ? [] : summaries;
  const byTitle = {};
  let previousExpectedIndex = -1;

  summariesToValidate.forEach((summary) => {
    const expectedIndex = LESSON03_CONFIG_.fields.findIndex(
      (field) => field.title === summary.title,
    );
    if (expectedIndex === -1) {
      throw new Error(`表單含有非本課欄位｜名稱=${summary.title || '未命名'}`);
    }
    if (byTitle[summary.title]) {
      throw new Error(`表單含有重複欄位｜名稱=${summary.title}`);
    }
    if (expectedIndex < previousExpectedIndex) {
      throw new Error('表單欄位順序不符｜為避免破壞回覆，未自動重排');
    }

    const expected = LESSON03_CONFIG_.fields[expectedIndex];
    if (summary.type !== expected.type) {
      throw new Error(`表單欄位型別不符｜名稱=${summary.title}`);
    }

    byTitle[summary.title] = summary;
    previousExpectedIndex = expectedIndex;
  });

  const missingKeys = [];
  const existingCorrections = [];
  LESSON03_CONFIG_.fields.forEach((field) => {
    const summary = byTitle[field.title];
    if (!summary) {
      missingKeys.push(field.key);
      return;
    }

    const choicesCorrect =
      field.type !== 'MULTIPLE_CHOICE' ||
      lesson03ArraysEqual_(summary.choices, LESSON03_CONFIG_.sessions);
    if (
      !summary.required ||
      summary.helpText !== field.helpText ||
      !choicesCorrect
    ) {
      existingCorrections.push(field.key);
    }
  });

  return {
    changed:
      missingKeys.length > 0 ||
      existingCorrections.length > 0 ||
      recoverableBlankItem !== null,
    missingKeys,
    existingCorrections,
    recoverableBlankItemIndex: recoverableBlankItem
      ? recoverableBlankItem.index
      : null,
  };
}

/**
 * 套用欄位計畫；不刪除任何既有欄位。
 *
 * @param {GoogleAppsScript.Forms.Form} form 表單。
 * @param {Array<GoogleAppsScript.Forms.Item>} originalItems 原有欄位。
 * @param {Object} plan 欄位計畫。
 */
function applyLesson03Items_(form, originalItems, plan) {
  const itemsByTitle = {};
  originalItems.forEach((item) => {
    itemsByTitle[item.getTitle()] = item;
  });

  LESSON03_CONFIG_.fields.forEach((field) => {
    let item = itemsByTitle[field.title];
    if (
      field.key === 'name' &&
      plan.recoverableBlankItemIndex !== null
    ) {
      item = originalItems[plan.recoverableBlankItemIndex];
    }
    if (!item) {
      item =
        field.type === 'TEXT'
          ? form.addTextItem()
          : form.addMultipleChoiceItem();
    }

    if (
      plan.missingKeys.includes(field.key) ||
      plan.existingCorrections.includes(field.key)
    ) {
      configureLesson03Item_(item, field);
    }
  });
}

/**
 * 設定一個表單欄位。
 *
 * `Form.getItems()` 回傳通用 Item，需要轉型；`Form.addTextItem()` 與
 * `Form.addMultipleChoiceItem()` 已直接回傳具體型別，不提供 asXxxItem。
 *
 * @param {GoogleAppsScript.Forms.Item|GoogleAppsScript.Forms.TextItem|GoogleAppsScript.Forms.MultipleChoiceItem} item 表單欄位。
 * @param {Object} field 預期欄位設定。
 */
function configureLesson03Item_(item, field) {
  if (field.type === 'TEXT') {
    const textItem =
      typeof item.asTextItem === 'function' ? item.asTextItem() : item;
    textItem
      .setTitle(field.title)
      .setHelpText(field.helpText)
      .setRequired(true);

    if (field.key === 'email') {
      const validation = FormApp.createTextValidation()
        .requireTextIsEmail()
        .setHelpText(
          '請輸入有效且能由你親自收信的 Email；錯誤格式測試不會送出。',
        )
        .build();
      textItem.setValidation(validation);
    }
    return;
  }

  const choiceItem =
    typeof item.asMultipleChoiceItem === 'function'
      ? item.asMultipleChoiceItem()
      : item;
  choiceItem
    .setTitle(field.title)
    .setHelpText(field.helpText)
    .setChoiceValues(LESSON03_CONFIG_.sessions.slice())
    .setRequired(true);
}

/**
 * 規劃表單基本文字與回覆開關。
 *
 * @param {Object} current 目前設定。
 * @return {Object} 各欄位是否需要更新。
 */
function planLesson03Metadata_(current) {
  const plan = {
    title: current.title !== LESSON03_CONFIG_.formTitle,
    description: current.description !== LESSON03_CONFIG_.formDescription,
    confirmationMessage:
      current.confirmationMessage !== LESSON03_CONFIG_.confirmationMessage,
    acceptingResponses: current.acceptingResponses !== true,
    collectsEmail: current.collectsEmail !== false,
  };
  plan.changed =
    plan.title ||
    plan.description ||
    plan.confirmationMessage ||
    plan.acceptingResponses ||
    plan.collectsEmail;
  return plan;
}

/**
 * 只套用需要改變的表單基本設定。
 *
 * @param {GoogleAppsScript.Forms.Form} form 表單。
 * @param {Object} plan 更新計畫。
 */
function applyLesson03Metadata_(form, plan) {
  if (plan.title) {
    form.setTitle(LESSON03_CONFIG_.formTitle);
  }
  if (plan.description) {
    form.setDescription(LESSON03_CONFIG_.formDescription);
  }
  if (plan.confirmationMessage) {
    form.setConfirmationMessage(LESSON03_CONFIG_.confirmationMessage);
  }
  if (plan.acceptingResponses) {
    form.setAcceptingResponses(true);
  }
  if (plan.collectsEmail) {
    form.setCollectEmail(false);
  }
}

/**
 * 由來源回覆識別值產生不含原值的穩定報名編號。
 *
 * @param {*} sourceId Google 回覆來源識別值；不得寫入紀錄檔(Log)。
 * @return {string} 只保留雜湊結果的安全報名編號。
 */
function createLesson03RegistrationId_(sourceId) {
  const source = String(sourceId || '').trim();
  if (source === '') {
    throw new Error('無法建立報名編號｜來源識別值不可空白');
  }

  // 使用穩定的 FNV-1a 雜湊，避免把原始 Google 回覆 ID 寫入業務結果。
  let hash = 2166136261;
  for (let index = 0; index < source.length; index += 1) {
    hash ^= source.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return `REG-${(hash >>> 0).toString(16).toUpperCase().padStart(8, '0')}`;
}

/**
 * 將表單回覆來源與欄位值組成待驗證的報名資料。
 *
 * @param {*} sourceId Google 回覆來源識別值。
 * @param {Object} values 表單欄位值。
 * @return {Object} 含安全報名編號的資料。
 */
function buildLesson03Registration_(sourceId, values) {
  return {
    registrationId: createLesson03RegistrationId_(sourceId),
    name: values && values.name,
    email: values && values.email,
    session: values && values.session,
  };
}

/**
 * 驗證並正規化一筆報名資料。
 *
 * @param {Object} registration 報名資料。
 * @return {{
 *   registrationId: string,
 *   name: string,
 *   email: string,
 *   session: string
 * }} 安全的報名資料。
 */
function validateRegistration_(registration) {
  const normalized = {
    registrationId: String(registration && registration.registrationId || '')
      .trim(),
    name: String(registration && registration.name || '').trim(),
    email: String(registration && registration.email || '')
      .trim()
      .toLowerCase(),
    session: String(registration && registration.session || '').trim(),
  };

  if (!/^REG-[A-Za-z0-9-]+$/.test(normalized.registrationId)) {
    throw new Error('欄位=報名編號｜原因=格式不正確');
  }
  if (normalized.name === '') {
    throw new Error('欄位=姓名｜原因=不可空白');
  }
  if (!isLesson03EmailValid_(normalized.email)) {
    throw new Error('欄位=Email｜原因=格式不正確');
  }
  if (!LESSON03_CONFIG_.sessions.includes(normalized.session)) {
    throw new Error('欄位=活動場次｜原因=不在允許選項中');
  }
  return normalized;
}

/**
 * 規劃業務結果，讓相同報名編號只產生一筆。
 *
 * 本課只測試這個純函式；表單送出後自動呼叫留到第 7 課。
 *
 * @param {Array<Object>} existingRecords 既有業務結果。
 * @param {Object} registration 新報名資料。
 * @return {{changed: boolean, action: string, records: Array<Object>}} 計畫。
 */
function planLesson03Registration_(existingRecords, registration) {
  const normalized = validateRegistration_(registration);
  const records = (existingRecords || []).map((record) =>
    Object.assign({}, record),
  );
  const exists = records.some(
    (record) =>
      String(record.registrationId || '').trim() ===
      normalized.registrationId,
  );

  if (exists) {
    return { changed: false, action: 'skip', records };
  }

  records.push({
    registrationId: normalized.registrationId,
    name: normalized.name,
    email: normalized.email,
    session: normalized.session,
    status: LESSON03_CONFIG_.pendingStatus,
  });
  return { changed: true, action: 'insert', records };
}

/**
 * 驗證基本 Email 格式。
 *
 * @param {string} email 正規化後的 Email。
 * @return {boolean} 是否符合基本格式。
 */
function isLesson03EmailValid_(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/**
 * 比較兩個字串陣列。
 *
 * @param {Array<string>} actual 實際值。
 * @param {Array<string>} expected 預期值。
 * @return {boolean} 是否一致。
 */
function lesson03ArraysEqual_(actual, expected) {
  return (
    actual.length === expected.length &&
    expected.every((value, index) => actual[index] === value)
  );
}

/**
 * 第 3 課最小斷言。
 *
 * @param {boolean} condition 是否符合預期。
 * @param {string} message 失敗訊息。
 */
function assertLesson03_(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}
