const LESSON08_CONFIG_ = Object.freeze({
  requestHeader: 'Webhook 請求編號',
  expectedSource: 'learn-gas-lesson-08',
  maximumBodyLength: 10000,
  minimumTokenLength: 24,
  maximumTokenLength: 200,
  lockWaitMilliseconds: 5000,
  remoteRequestId: 'LESSON08-DEMO-REQUEST-001',
});

/**
 * 網頁應用程式(Web App)的瀏覽器入口。
 *
 * 只回傳公開狀態，不讀取或顯示帳號、設定值、資料筆數及內部錯誤。
 *
 * @return {GoogleAppsScript.Content.TextOutput} JSON 狀態。
 */
function doGet(e) {
  return createLesson08JsonOutput_({
    ok: true,
    code: 'READY',
    message: '活動報名測試入口已準備完成',
  });
}

/**
 * 網路回呼(Webhook)入口：驗證後將一筆假報名加入既有工作表。
 *
 * @param {Object} e Apps Script 傳入的 POST 事件。
 * @return {GoogleAppsScript.Content.TextOutput} 不含內部資訊的 JSON 回應。
 */
function doPost(e) {
  let lock;
  let acquired = false;
  let result;

  try {
    const request = parseLesson08PostEvent_(e);
    const config = getScriptConfig_();
    validateLesson08TokenSetting_(config.webhookToken);

    if (!lesson08SecretsEqual_(request.token, config.webhookToken)) {
      throw createLesson08Error_(
        'INVALID_TOKEN',
        'Webhook 驗證失敗',
      );
    }

    const registration = normalizeLesson08Registration_(request);
    lock = LockService.getScriptLock();
    acquired = lock.tryLock(LESSON08_CONFIG_.lockWaitMilliseconds);
    if (!acquired) {
      throw createLesson08Error_(
        'BUSY',
        '系統正在處理另一筆資料，請稍後重試',
      );
    }

    result = storeLesson08Registration_(
      registration,
      config.spreadsheetId,
    );
  } catch (error) {
    result = lesson08FailureFromError_(error);
  } finally {
    if (lock && acquired) {
      lock.releaseLock();
    }
  }

  writeLesson08ResponseLog_(result);
  return createLesson08JsonOutput_(result);
}

/**
 * Sheets 日常入口：檢查第 8 課部署前後需要的設定。
 *
 * 部署前允許 WEB_APP_URL 尚未設定；本函式不寫入資料也不送出 HTTP。
 *
 * @return {{readyForDeployment: boolean, readyForRemoteTest: boolean}} 設定狀態。
 */
function checkLesson08Settings() {
  writeLessonLog_('開始', '檢查第 8 課設定');

  try {
    const config = getScriptConfig_();
    openCourseSpreadsheet_();
    validateLesson08TokenSetting_(config.webhookToken);

    const hasUrl = config.webAppUrl !== '';
    if (hasUrl) {
      validateLesson08WebAppUrl_(config.webAppUrl);
    }

    writeLesson08SettingsLog_(config);
    const message = hasUrl
      ? '第 8 課設定完成｜準備遠端測試'
      : '第 8 課部署前設定完成｜準備部署';
    writeLessonLog_('成功', `${message}｜尚未送出 HTTP 請求`);

    SpreadsheetApp.getUi().alert(
      '第 8 課設定',
      hasUrl
        ? '設定檢查通過，已準備遠端測試。'
        : '設定檢查通過，已準備建立網頁應用程式部署。',
      SpreadsheetApp.getUi().ButtonSet.OK,
    );

    return {
      readyForDeployment: true,
      readyForRemoteTest: hasUrl,
    };
  } catch (error) {
    const config = getScriptConfig_();
    writeLesson08SettingsLog_(config);
    const message = error instanceof Error ? error.message : String(error);
    writeLessonLog_(
      '失敗',
      `${message}｜未送出 HTTP 請求｜未寫入資料`,
    );
    throw error;
  }
}

/**
 * Agent 工程測試：只測純函式，不讀寫遠端資源或送出 HTTP。
 *
 * @return {boolean} 是否全部通過。
 */
function runLesson08LocalTests() {
  writeLessonLog_('開始', '執行第 8 課本機安全測試');

  const tests = [
    testLesson08ValidRequest_,
    testLesson08InvalidJson_,
    testLesson08InvalidToken_,
    testLesson08InvalidData_,
    testLesson08Duplicate_,
  ];
  tests.forEach((testFunction) => testFunction());

  writeLessonLog_('成功', '本機測試完成｜通過=5｜沒有遠端副作用');
  return true;
}

/**
 * Agent 遠端測試入口：依序對版本化 /exec 網址送出四個 POST。
 *
 * 這個函式會送出真實網路請求，只有在使用者另行確認後才能執行。
 *
 * @return {Array<Object>} 四次安全回應摘要。
 */
function runLesson08RemoteTests() {
  writeLessonLog_('開始', '準備執行實際 Webhook 測試｜請求數=4');

  const config = getScriptConfig_();
  openCourseSpreadsheet_();
  validateLesson08TokenSetting_(config.webhookToken);
  validateLesson08WebAppUrl_(config.webAppUrl);

  const validPayload = {
    token: config.webhookToken,
    requestId: LESSON08_CONFIG_.remoteRequestId,
    name: '第8課 Webhook 範例',
    email: 'lesson08@example.com',
    session: '上午場',
    source: LESSON08_CONFIG_.expectedSource,
  };
  const requests = [
    '{',
    JSON.stringify(Object.assign({}, validPayload, {
      token: `${config.webhookToken}-wrong`,
    })),
    JSON.stringify(validPayload),
    JSON.stringify(validPayload),
  ];

  const results = requests.map((payload) =>
    fetchLesson08Webhook_(config.webAppUrl, payload),
  );
  const expectedCodes = ['INVALID_JSON', 'INVALID_TOKEN'];
  expectedCodes.forEach((expected, index) => {
    if (results[index].code !== expected) {
      throw new Error(
        `遠端測試結果不符｜順序=${index + 1}｜code=${results[index].code}`,
      );
    }
  });
  if (!['OK', 'DUPLICATE'].includes(results[2].code)) {
    throw new Error(`遠端正常測試結果不符｜code=${results[2].code}`);
  }
  if (results[3].code !== 'DUPLICATE') {
    throw new Error(`遠端重送測試結果不符｜code=${results[3].code}`);
  }

  results.forEach((result) => writeLesson08ResponseLog_(result));
  writeLessonLog_(
    '成功',
    `實際 Webhook 測試完成｜請求數=4｜正常=${results[2].code}｜重送=${results[3].code}`,
  );
  return results;
}

/**
 * 解析並限制 POST 事件，不把原始本文寫入紀錄檔(Log)。
 *
 * @param {Object} event POST 事件。
 * @return {Object} JSON 物件。
 */
function parseLesson08PostEvent_(event) {
  const postData = event && event.postData;
  const contents = String(postData && postData.contents || '');
  const contentType = String(postData && postData.type || '')
    .split(';')[0]
    .trim()
    .toLowerCase();
  const reportedLength = Number(
    postData && postData.length !== undefined
      ? postData.length
      : contents.length,
  );

  if (contents === '') {
    throw createLesson08Error_('INVALID_DATA', '缺少 POST 本文');
  }
  if (contentType !== 'application/json') {
    throw createLesson08Error_(
      'INVALID_DATA',
      '只接受 application/json 格式',
    );
  }
  if (
    !Number.isFinite(reportedLength) ||
    reportedLength < 0 ||
    reportedLength > LESSON08_CONFIG_.maximumBodyLength ||
    contents.length > LESSON08_CONFIG_.maximumBodyLength
  ) {
    throw createLesson08Error_('INVALID_DATA', 'POST 本文大小不符合限制');
  }

  let parsed;
  try {
    parsed = JSON.parse(contents);
  } catch (error) {
    throw createLesson08Error_('INVALID_JSON', 'Webhook JSON 格式不正確');
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw createLesson08Error_('INVALID_DATA', 'Webhook 資料格式不正確');
  }
  return parsed;
}

/**
 * 驗證並正規化外部報名資料。
 *
 * @param {Object} request 已解析請求。
 * @return {Object} 可寫入工作表的安全資料。
 */
function normalizeLesson08Registration_(request) {
  const requestId = String(request && request.requestId || '').trim();
  const source = String(request && request.source || '').trim();

  if (!/^[A-Za-z0-9][A-Za-z0-9_-]{5,63}$/.test(requestId)) {
    throw createLesson08Error_(
      'INVALID_DATA',
      'requestId 格式不正確',
    );
  }
  if (source !== LESSON08_CONFIG_.expectedSource) {
    throw createLesson08Error_('INVALID_DATA', '資料來源不正確');
  }

  let registration;
  try {
    registration = validateRegistration_({
      registrationId: createLesson03RegistrationId_(
        `webhook|${requestId}`,
      ),
      name: request && request.name,
      email: request && request.email,
      session: request && request.session,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw createLesson08Error_('INVALID_DATA', message);
  }

  if (registration.name.length > 50) {
    throw createLesson08Error_('INVALID_DATA', '欄位=姓名｜原因=長度過長');
  }
  if (/[\r\n]/.test(registration.name)) {
    throw createLesson08Error_(
      'INVALID_DATA',
      '欄位=姓名｜原因=不可包含換行',
    );
  }

  return Object.assign({}, registration, { requestId, source });
}

/**
 * 規劃 requestId 是否需要新增。
 *
 * @param {Array<*>} existingRequestIds 已存在的請求編號。
 * @param {Object} registration 已驗證資料。
 * @return {{action: string, registration: Object}} 寫入或略過計畫。
 */
function planLesson08Write_(existingRequestIds, registration) {
  const requestId = String(registration && registration.requestId || '').trim();
  const exists = (existingRequestIds || []).some(
    (value) => String(value || '').trim() === requestId,
  );
  return {
    action: exists ? 'duplicate' : 'insert',
    registration: Object.assign({}, registration),
  };
}

/**
 * 在已取得指令碼鎖定後寫入一筆資料。
 *
 * @param {Object} registration 已驗證資料。
 * @param {string} spreadsheetId 第 2 課已核對的試算表識別值。
 * @return {{ok: boolean, code: string, message: string}} 寫入結果。
 */
function storeLesson08Registration_(registration, spreadsheetId) {
  const spreadsheet = openLesson08Spreadsheet_(spreadsheetId);
  const sheet = getLesson04Sheet_(spreadsheet);
  ensureLesson08RequestHeader_(sheet);

  const lastRow = Math.max(sheet.getLastRow(), 1);
  const existingRequestIds = lastRow > 1
    ? sheet.getRange(2, 10, lastRow - 1, 1).getValues().flat()
    : [];
  const plan = planLesson08Write_(existingRequestIds, registration);

  if (plan.action === 'duplicate') {
    return {
      ok: true,
      code: 'DUPLICATE',
      message: '這筆測試請求已處理，沒有重複新增',
    };
  }

  const row = [
    registration.name,
    registration.email,
    registration.session,
    LESSON04_CONFIG_.readyStatus,
    registration.registrationId,
    '',
    '',
    '',
    new Date(),
    registration.requestId,
  ];
  sheet.getRange(lastRow + 1, 1, 1, row.length).setValues([row]);

  return {
    ok: true,
    code: 'OK',
    message: '已收到測試報名資料',
  };
}

/**
 * Web App 沒有目前開啟的試算表情境，必須用既有設定明確開啟。
 *
 * @param {string} spreadsheetId 第 2 課已核對的試算表識別值。
 * @return {GoogleAppsScript.Spreadsheet.Spreadsheet} 指定試算表。
 */
function openLesson08Spreadsheet_(spreadsheetId) {
  const value = String(spreadsheetId || '').trim();
  if (value === '') {
    throw createLesson08Error_(
      'INVALID_DATA',
      `缺少必要的指令碼屬性｜名稱=${COURSE_PROPERTY_NAMES_.spreadsheetId}`,
    );
  }
  return SpreadsheetApp.openById(value);
}

/**
 * 補上學員可見的 Webhook 請求編號欄位；不使用 Script Properties 儲存。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 報名工作表。
 */
function ensureLesson08RequestHeader_(sheet) {
  const headers = sheet
    .getRange(1, 1, 1, LESSON04_CONFIG_.headers.length)
    .getValues()[0];
  validateLesson05Headers_(headers);

  const current = String(sheet.getRange(1, 10).getValue() || '').trim();
  if (
    current !== '' &&
    current !== LESSON08_CONFIG_.requestHeader
  ) {
    throw createLesson08Error_(
      'INVALID_DATA',
      'Webhook 請求編號欄位不相容',
    );
  }
  if (current === '') {
    sheet.getRange(1, 10).setValue(LESSON08_CONFIG_.requestHeader);
  }
}

/**
 * 驗證學生私下設定的 Webhook Token，不顯示實際值。
 *
 * @param {*} token 指令碼屬性中的驗證值。
 */
function validateLesson08TokenSetting_(token) {
  const value = String(token || '').trim();
  if (value === '') {
    throw new Error(
      `缺少必要的指令碼屬性｜名稱=${COURSE_PROPERTY_NAMES_.webhookToken}`,
    );
  }
  if (
    value.length < LESSON08_CONFIG_.minimumTokenLength ||
    value.length > LESSON08_CONFIG_.maximumTokenLength ||
    /[\r\n]/.test(value)
  ) {
    throw new Error('WEBHOOK_TOKEN 長度或格式不符合安全要求');
  }
}

/**
 * 只接受 Apps Script 版本化 /exec 網址。
 *
 * @param {*} url 指令碼屬性中的網址。
 */
function validateLesson08WebAppUrl_(url) {
  const value = String(url || '').trim();
  if (value === '') {
    throw new Error(
      `缺少必要的指令碼屬性｜名稱=${COURSE_PROPERTY_NAMES_.webAppUrl}`,
    );
  }
  if (
    !/^https:\/\/script\.google\.com\/macros\/s\/[A-Za-z0-9_-]+\/exec$/.test(
      value,
    )
  ) {
    throw new Error('WEB_APP_URL 必須是版本化且以 /exec 結尾的網址');
  }
}

/**
 * 使用固定時間比較兩個驗證字串，避免提早回傳相符前綴。
 *
 * @param {*} received 請求帶入值。
 * @param {*} expected 指令碼屬性值。
 * @return {boolean} 是否完全相同。
 */
function lesson08SecretsEqual_(received, expected) {
  const left = String(received || '');
  const right = String(expected || '');
  const length = Math.max(left.length, right.length);
  let difference = left.length ^ right.length;

  for (let index = 0; index < length; index += 1) {
    difference |=
      (left.charCodeAt(index) || 0) ^
      (right.charCodeAt(index) || 0);
  }
  return difference === 0;
}

/**
 * 對實際 Web App 送出單一 JSON POST 並解析安全回應。
 *
 * @param {string} url 版本化 /exec 網址。
 * @param {string} payload JSON 字串或錯誤 JSON 測試值。
 * @return {Object} 安全回應。
 */
function fetchLesson08Webhook_(url, payload) {
  const response = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    payload,
    followRedirects: true,
    muteHttpExceptions: true,
  });
  const content = String(response.getContentText() || '');
  if (content.length > 2000) {
    throw new Error('Webhook 回應內容超過教學安全限制');
  }

  let parsed;
  try {
    parsed = JSON.parse(content);
  } catch (error) {
    throw new Error('Webhook 回應不是可辨識的 JSON');
  }
  if (
    !parsed ||
    typeof parsed.ok !== 'boolean' ||
    typeof parsed.code !== 'string' ||
    typeof parsed.message !== 'string'
  ) {
    throw new Error('Webhook 回應缺少必要欄位');
  }
  return {
    ok: parsed.ok,
    code: parsed.code,
    message: parsed.message,
  };
}

/**
 * 建立不含內部資訊的 JSON 輸出。
 *
 * @param {Object} value 安全回應。
 * @return {GoogleAppsScript.Content.TextOutput} JSON 輸出。
 */
function createLesson08JsonOutput_(value) {
  return ContentService
    .createTextOutput(JSON.stringify({
      ok: Boolean(value && value.ok),
      code: String(value && value.code || 'INVALID_DATA'),
      message: String(value && value.message || '目前無法處理資料'),
    }))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * 建立帶有公開錯誤代碼的內部例外。
 *
 * @param {string} code 對外代碼。
 * @param {string} message 繁體中文安全說明。
 * @return {Error} 可安全轉換的例外。
 */
function createLesson08Error_(code, message) {
  const error = new Error(message);
  error.lesson08Code = code;
  return error;
}

/**
 * 將例外轉成固定回應，不顯示堆疊、檔名或原始服務錯誤。
 *
 * @param {*} error 原始例外。
 * @return {{ok: boolean, code: string, message: string}} 安全失敗回應。
 */
function lesson08FailureFromError_(error) {
  const allowedCodes = [
    'INVALID_JSON',
    'INVALID_TOKEN',
    'INVALID_DATA',
    'BUSY',
  ];
  const code = error && allowedCodes.includes(error.lesson08Code)
    ? error.lesson08Code
    : 'INVALID_DATA';
  const safeMessage = error && allowedCodes.includes(error.lesson08Code)
    ? String(error.message || '目前無法處理資料')
    : '目前無法處理資料';
  return { ok: false, code, message: safeMessage };
}

/**
 * 只記錄回應代碼與中文結果，不記錄 URL、Token 或請求本文。
 *
 * @param {Object} result 安全回應。
 */
function writeLesson08ResponseLog_(result) {
  const level = result && result.ok
    ? (result.code === 'DUPLICATE' ? '略過' : '成功')
    : '失敗';
  writeLessonLog_(
    level,
    `${String(result && result.message || '目前無法處理資料')}` +
      `｜code=${String(result && result.code || 'INVALID_DATA')}` +
      `｜${result && result.code === 'OK' ? '新增=1' : '沒有重複或未寫入資料'}`,
  );
}

/**
 * 只顯示三項設定的有無，不顯示 Token 或完整 URL。
 *
 * @param {Object} config 集中式設定。
 */
function writeLesson08SettingsLog_(config) {
  const isSet = (value) => String(value || '').trim() !== '';
  writeLessonLog_(
    '設定',
    `SPREADSHEET_ID=${isSet(config && config.spreadsheetId) ? '已設定' : '未設定'}` +
      `｜WEBHOOK_TOKEN=${isSet(config && config.webhookToken) ? '已設定' : '未設定'}` +
      `｜WEB_APP_URL=${isSet(config && config.webAppUrl) ? '已設定' : '未設定'}` +
      '｜實際值不顯示',
  );
}

/**
 * 以下五個測試只使用假事件與純函式。
 */
function testLesson08ValidRequest_() {
  const request = parseLesson08PostEvent_(
    createLesson08TestEvent_(JSON.stringify({
      token: 'test-token-value-1234567890',
      requestId: 'LESSON08-TEST-001',
      name: '測試學員',
      email: 'learner@example.com',
      session: '上午場',
      source: LESSON08_CONFIG_.expectedSource,
    })),
  );
  const registration = normalizeLesson08Registration_(request);
  assertLesson08_(registration.requestId === 'LESSON08-TEST-001', '正常資料應通過');
}

function testLesson08InvalidJson_() {
  assertLesson08ErrorCode_(
    () => parseLesson08PostEvent_(createLesson08TestEvent_('{')),
    'INVALID_JSON',
  );
}

function testLesson08InvalidToken_() {
  assertLesson08_(
    !lesson08SecretsEqual_('wrong-token', 'test-token-value-1234567890'),
    '錯誤 Token 不得通過',
  );
}

function testLesson08InvalidData_() {
  assertLesson08ErrorCode_(
    () => normalizeLesson08Registration_({
      requestId: 'LESSON08-TEST-002',
      name: '測試學員',
      email: 'invalid-email',
      session: '上午場',
      source: LESSON08_CONFIG_.expectedSource,
    }),
    'INVALID_DATA',
  );
}

function testLesson08Duplicate_() {
  const registration = {
    requestId: 'LESSON08-TEST-003',
  };
  assertLesson08_(
    planLesson08Write_([], registration).action === 'insert',
    '第一次請求應規劃新增',
  );
  assertLesson08_(
    planLesson08Write_(['LESSON08-TEST-003'], registration).action ===
      'duplicate',
    '相同 requestId 重送不得新增',
  );
}

/**
 * 建立不接觸遠端服務的 POST 假事件。
 *
 * @param {string} contents 測試本文。
 * @return {Object} 假事件。
 */
function createLesson08TestEvent_(contents) {
  return {
    postData: {
      contents,
      length: contents.length,
      type: 'application/json',
    },
  };
}

/**
 * 驗證測試應丟出指定公開代碼。
 *
 * @param {Function} callback 測試函式。
 * @param {string} expectedCode 預期代碼。
 */
function assertLesson08ErrorCode_(callback, expectedCode) {
  try {
    callback();
  } catch (error) {
    assertLesson08_(
      error && error.lesson08Code === expectedCode,
      `預期錯誤代碼=${expectedCode}`,
    );
    return;
  }
  throw new Error(`第 8 課測試失敗：未出現錯誤代碼=${expectedCode}`);
}

/**
 * 第 8 課最小斷言工具。
 *
 * @param {boolean} condition 是否成立。
 * @param {string} message 失敗訊息。
 */
function assertLesson08_(condition, message) {
  if (!condition) {
    throw new Error(`第 8 課測試失敗：${message}`);
  }
}
