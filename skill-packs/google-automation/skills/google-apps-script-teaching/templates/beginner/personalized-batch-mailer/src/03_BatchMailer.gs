/**
 * 開啟試算表時建立日常使用的郵件工具選單。
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('郵件工具')
    .addItem('批次寄送郵件', 'sendPersonalizedBatchEmails')
    .addToUi();
}

/**
 * 從 Sheets 自訂選單執行的真實寄送入口。
 * 程式先顯示筆數，再由使用者確認是否開始寄信。
 */
function sendPersonalizedBatchEmails() {
  logBatchMailer_('開始', '準備檢查個人化批次郵件');

  var lock = LockService.getDocumentLock();
  if (!lock.tryLock(1000)) {
    logBatchMailer_('警告', '另一個寄送流程仍在執行，本次沒有寄出郵件');
    SpreadsheetApp.getUi().alert('另一個寄送流程仍在執行，請稍後再試。');
    return;
  }

  try {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = spreadsheet && spreadsheet.getSheetByName(BATCH_MAILER_CONFIG_.sheetName);
    if (!sheet) {
      throw new Error('找不到待寄郵件工作表，請先執行 setupPersonalizedBatchMailer。');
    }

    var rows = readBatchMailerRows_(sheet);
    var plan = classifyBatchMailerRows_(rows, 2);
    writeBatchMailerPreflightResults_(sheet, rows, plan);

    logBatchMailer_(
      '進度',
      '待檢查筆數=' + plan.pendingCount +
        '｜可寄送筆數=' + plan.valid.length +
        '｜錯誤筆數=' + plan.invalid.length +
        '｜寄送中待查筆數=' + plan.inProgress.length +
        '｜已寄出略過筆數=' + plan.skippedSent
    );

    var remainingQuota = MailApp.getRemainingDailyQuota();
    var safety = checkBatchMailerSendSafety_(plan.valid.length, remainingQuota);
    if (!safety.ok) {
      logBatchMailer_('警告', safety.reason);
      SpreadsheetApp.getUi().alert('本次未寄送', safety.reason, SpreadsheetApp.getUi().ButtonSet.OK);
      return;
    }

    var ui = SpreadsheetApp.getUi();
    var confirmation = ui.alert(
      '確認批次寄送',
      '本次待檢查 ' + plan.pendingCount + ' 筆；可寄送 ' + plan.valid.length +
        ' 筆；資料錯誤 ' + plan.invalid.length + ' 筆；寄送中待查 ' +
        plan.inProgress.length + ' 筆。\n\n確定要寄出可寄送的郵件嗎？',
      ui.ButtonSet.YES_NO
    );
    if (confirmation !== ui.Button.YES) {
      logBatchMailer_('略過', '使用者取消本次寄送，沒有寄出郵件');
      return;
    }

    var result = sendBatchMailerPlan_(sheet, plan.valid);
    var message = '成功寄出 ' + result.sent + ' 封。';
    if (result.uncertain > 0) {
      message += '\n有 ' + result.uncertain +
        ' 封結果不確定，狀態保留為「寄送中」。請先到 Gmail 的寄件備份查證。';
    }
    ui.alert('批次寄送完成', message, ui.ButtonSet.OK);
    logBatchMailer_(
      '成功',
      '批次寄送流程結束｜成功筆數=' + result.sent + '｜結果不確定筆數=' + result.uncertain
    );
  } catch (error) {
    logBatchMailerError_('批次寄送失敗｜原因：' + error.message);
    SpreadsheetApp.getUi().alert('批次寄送失敗', error.message, SpreadsheetApp.getUi().ButtonSet.OK);
    throw error;
  } finally {
    lock.releaseLock();
  }
}

/**
 * 讀取不含標題列的資料；沒有資料時回傳空陣列。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 待寄郵件工作表。
 * @return {Array<Array<*>>} 待檢查資料。
 */
function readBatchMailerRows_(sheet) {
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    return [];
  }
  return sheet.getRange(2, 1, lastRow - 1, BATCH_MAILER_CONFIG_.headers.length).getValues();
}

/**
 * 寫回資料檢查結果，只更新錯誤原因欄並保留欄寬。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 待寄郵件工作表。
 * @param {Array<Array<*>>} rows 原始資料。
 * @param {Object} plan 批次分類結果。
 */
function writeBatchMailerPreflightResults_(sheet, rows, plan) {
  if (rows.length === 0) {
    return;
  }

  var errors = rows.map(function (row) {
    return [row[6] || ''];
  });
  plan.valid.forEach(function (item) {
    errors[item.rowNumber - 2][0] = '';
  });
  plan.invalid.concat(plan.inProgress, plan.skippedUnknownStatus).forEach(function (item) {
    errors[item.rowNumber - 2][0] = item.reason;
  });

  sheet.getRange(2, 7, errors.length, 1).setValues(errors);
}

/**
 * 實際寄出已通過檢查的郵件。
 * 若 MailApp 回報錯誤，保留「寄送中」避免自動重寄，並停止後續寄送。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 待寄郵件工作表。
 * @param {Array<Object>} validItems 已通過檢查的寄送項目。
 * @return {{sent:number,uncertain:number}} 寄送結果。
 */
function sendBatchMailerPlan_(sheet, validItems) {
  var result = { sent: 0, uncertain: 0 };

  for (var index = 0; index < validItems.length; index += 1) {
    var item = validItems[index];
    sheet.getRange(item.rowNumber, 5, 1, 3).setValues([[
      BATCH_MAILER_CONFIG_.statusSending,
      '',
      ''
    ]]);
    SpreadsheetApp.flush();

    try {
      MailApp.sendEmail({
        to: item.email,
        subject: item.subject,
        body: item.body
      });
      sheet.getRange(item.rowNumber, 5, 1, 3).setValues([[
        BATCH_MAILER_CONFIG_.statusSent,
        new Date(),
        ''
      ]]);
      result.sent += 1;
      logBatchMailer_('進度', '已完成第 ' + (index + 1) + ' 封郵件');
    } catch (error) {
      sheet.getRange(item.rowNumber, 5, 1, 3).setValues([[
        BATCH_MAILER_CONFIG_.statusSending,
        '',
        '寄送結果不確定，請先到 Gmail 的寄件備份查證，再交由除錯流程處理。'
      ]]);
      result.uncertain += 1;
      logBatchMailerError_(
        '第 ' + (index + 1) + ' 封寄送結果不確定，已停止後續寄送｜原因：' + error.message
      );
      break;
    }
  }

  return result;
}
