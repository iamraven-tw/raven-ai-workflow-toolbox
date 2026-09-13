/** 個人化批次郵件寄送器的固定欄位與安全限制。 */
var BATCH_MAILER_CONFIG_ = {
  sheetName: '待寄郵件',
  headers: ['Email', '姓名', '預計主旨', '預計內容', '寄送狀態', '寄送時間', '錯誤原因'],
  maxBatchSize: 10,
  statusSending: '寄送中',
  statusSent: '已寄出'
};

/**
 * 檢查 Email 是否符合本案例需要的基本格式。
 *
 * @param {*} value 待檢查的值。
 * @return {boolean} 是否可作為測試收件地址。
 */
function isValidBatchMailerEmail_(value) {
  var email = String(value || '').trim();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/**
 * 建立固定格式的個人化主旨與內文。
 *
 * @param {string} name 收件人姓名。
 * @param {string} plannedSubject 使用者填寫的預計主旨。
 * @param {string} plannedBody 使用者填寫的預計內容。
 * @return {{subject:string,body:string}} 實際寄送內容。
 */
function buildPersonalizedEmail_(name, plannedSubject, plannedBody) {
  var normalizedName = String(name || '').trim();
  var normalizedSubject = String(plannedSubject || '').trim();
  var normalizedBody = String(plannedBody || '').trim();

  return {
    subject: normalizedName + '您好｜' + normalizedSubject,
    body: normalizedName + '您好：\n\n' + normalizedBody
  };
}

/**
 * 將工作表資料分成可寄送、錯誤、寄送中與已寄出。
 * 這是無 Google 遠端副作用的純邏輯，方便 Agent 在本機測試。
 *
 * @param {Array<Array<*>>} rows 不含標題列的工作表資料。
 * @param {number} startRow 第一筆資料在工作表中的列號。
 * @return {Object} 分類後的批次計畫。
 */
function classifyBatchMailerRows_(rows, startRow) {
  var result = {
    pendingCount: 0,
    valid: [],
    invalid: [],
    inProgress: [],
    skippedSent: 0,
    skippedBlank: 0,
    skippedUnknownStatus: []
  };

  rows.forEach(function (row, index) {
    var rowNumber = startRow + index;
    var email = String(row[0] || '').trim();
    var name = String(row[1] || '').trim();
    var plannedSubject = String(row[2] || '').trim();
    var plannedBody = String(row[3] || '').trim();
    var status = String(row[4] || '').trim();
    var isEntirelyBlank = [email, name, plannedSubject, plannedBody, status].every(function (value) {
      return value === '';
    });

    if (isEntirelyBlank) {
      result.skippedBlank += 1;
      return;
    }
    if (status === BATCH_MAILER_CONFIG_.statusSent) {
      result.skippedSent += 1;
      return;
    }
    if (status === BATCH_MAILER_CONFIG_.statusSending) {
      result.inProgress.push({
        rowNumber: rowNumber,
        reason: '此列目前為「寄送中」，請先到 Gmail 的寄件備份查證，不會自動重寄。'
      });
      return;
    }
    if (status !== '') {
      result.skippedUnknownStatus.push({
        rowNumber: rowNumber,
        reason: '寄送狀態不是空白、已寄出或寄送中，為避免重寄已略過。'
      });
      return;
    }

    result.pendingCount += 1;
    var reasons = [];
    if (email === '') {
      reasons.push('缺少 Email');
    } else if (!isValidBatchMailerEmail_(email)) {
      reasons.push('Email 格式不正確');
    }
    if (name === '') {
      reasons.push('缺少姓名');
    }
    if (plannedSubject === '') {
      reasons.push('缺少預計主旨');
    }
    if (plannedBody === '') {
      reasons.push('缺少預計內容');
    }

    if (reasons.length > 0) {
      result.invalid.push({
        rowNumber: rowNumber,
        reason: reasons.join('；')
      });
      return;
    }

    var personalized = buildPersonalizedEmail_(name, plannedSubject, plannedBody);
    result.valid.push({
      rowNumber: rowNumber,
      email: email,
      subject: personalized.subject,
      body: personalized.body
    });
  });

  return result;
}

/**
 * 檢查批次筆數與 Gmail 剩餘配額是否允許開始寄送。
 *
 * @param {number} validCount 本次可寄送筆數。
 * @param {number} remainingQuota MailApp 回報的剩餘收件人配額。
 * @return {{ok:boolean,reason:string}} 安全檢查結果。
 */
function checkBatchMailerSendSafety_(validCount, remainingQuota) {
  if (validCount <= 0) {
    return { ok: false, reason: '本次沒有可寄送的郵件。' };
  }
  if (validCount > BATCH_MAILER_CONFIG_.maxBatchSize) {
    return {
      ok: false,
      reason: '本次可寄送筆數超過 10 封上限，已在第一封寄出前停止。'
    };
  }
  if (remainingQuota < validCount) {
    return {
      ok: false,
      reason: '今天剩餘的 Gmail 收件人配額不足，已在第一封寄出前停止。'
    };
  }
  return { ok: true, reason: '' };
}
