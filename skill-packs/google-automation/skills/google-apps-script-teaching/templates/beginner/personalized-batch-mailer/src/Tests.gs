/**
 * Agent 使用的不寄信工程測試總入口。
 * 所有資料只存在記憶體，不讀取工作表，也不呼叫任何真實寄信服務。
 */
function runBatchMailerDryRunTests() {
  logBatchMailer_('開始', '準備執行個人化批次郵件寄送器的不寄信工程測試');

  try {
    testBatchMailerZeroRows_();
    testBatchMailerOneValidRow_();
    testBatchMailerMixedRows_();
    testBatchMailerRepeatProtection_();
    testBatchMailerSafetyLimits_();
    logBatchMailer_('成功', '不寄信工程測試全部通過｜共 5 組');
  } catch (error) {
    logBatchMailerError_('不寄信工程測試失敗｜原因：' + error.message);
    throw error;
  }
}

/** 驗證零筆資料。 */
function testBatchMailerZeroRows_() {
  var plan = classifyBatchMailerRows_([], 2);
  assertBatchMailerTest_(plan.valid.length === 0, '零筆資料不應產生可寄送郵件。');
}

/** 驗證一筆有效資料與個人化格式。 */
function testBatchMailerOneValidRow_() {
  var plan = classifyBatchMailerRows_([
    ['self@example.com', '測試同學', '課程提醒', '明天記得帶資料。', '', '', '']
  ], 2);
  assertBatchMailerTest_(plan.valid.length === 1, '一筆有效資料應列入寄送計畫。');
  assertBatchMailerTest_(
    plan.valid[0].subject === '測試同學您好｜課程提醒',
    '主旨沒有正確加入個人化稱呼。'
  );
  assertBatchMailerTest_(
    plan.valid[0].body === '測試同學您好：\n\n明天記得帶資料。',
    '內文沒有正確加入個人化稱呼。'
  );
}

/** 驗證多筆有效與錯誤資料可以安全分類。 */
function testBatchMailerMixedRows_() {
  var plan = classifyBatchMailerRows_([
    ['one@example.com', '測試甲', '提醒一', '內容一', '', '', ''],
    ['格式錯誤', '測試乙', '提醒二', '內容二', '', '', ''],
    ['three@example.com', '', '提醒三', '內容三', '', '', ''],
    ['four@example.com', '測試丁', '', '內容四', '', '', ''],
    ['five@example.com', '測試戊', '提醒五', '', '', '', '']
  ], 2);
  assertBatchMailerTest_(plan.valid.length === 1, '混合資料應只有一筆可寄送。');
  assertBatchMailerTest_(plan.invalid.length === 4, '四種錯誤資料都必須被拒絕。');
}

/** 驗證已寄出與寄送中資料不會自動重寄。 */
function testBatchMailerRepeatProtection_() {
  var plan = classifyBatchMailerRows_([
    ['sent@example.com', '測試已寄', '主旨', '內容', '已寄出', new Date(), ''],
    ['sending@example.com', '測試待查', '主旨', '內容', '寄送中', '', '']
  ], 2);
  assertBatchMailerTest_(plan.valid.length === 0, '已寄出或寄送中資料都不得重寄。');
  assertBatchMailerTest_(plan.skippedSent === 1, '應略過一筆已寄出資料。');
  assertBatchMailerTest_(plan.inProgress.length === 1, '應保留一筆寄送中待查資料。');
}

/** 驗證每批上限與剩餘配額會在寄送前擋下。 */
function testBatchMailerSafetyLimits_() {
  assertBatchMailerTest_(
    checkBatchMailerSendSafety_(10, 10).ok,
    '10 封且配額足夠時應允許進入確認。'
  );
  assertBatchMailerTest_(
    !checkBatchMailerSendSafety_(11, 20).ok,
    '超過 10 封時必須停止。'
  );
  assertBatchMailerTest_(
    !checkBatchMailerSendSafety_(2, 1).ok,
    '剩餘配額不足時必須停止。'
  );
}

/**
 * 測試斷言，失敗時提供繁體中文原因。
 *
 * @param {boolean} condition 是否符合預期。
 * @param {string} message 不符合時的訊息。
 */
function assertBatchMailerTest_(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}
