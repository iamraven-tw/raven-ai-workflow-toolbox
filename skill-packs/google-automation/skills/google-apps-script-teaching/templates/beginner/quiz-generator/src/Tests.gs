/**
 * 正常測試：驗證已由 Sheets 選單建立並完成設定的 20 題測驗。
 *
 * 第一份表單必須先由使用者從「測驗工具」選單建立，再將
 * QUIZ_FORM_ID 存入指令碼屬性；本函式不得搶先建立第一份表單。
 */
function testQuizNormal() {
  logQuiz_('開始', '準備執行教師隨機測驗正常測試');

  try {
    checkQuizFormSettings();
    setupQuizGenerator();
    var questions = checkQuizBank();
    if (questions.length !== QUIZ_CONFIG_.fixtureCount) {
      throw new Error('正常測試預期題庫有 100 題有效題目。');
    }

    var result = generateQuizForm();
    var form = FormApp.openById(result.formId);
    if (
      form.getItems().length !== QUIZ_CONFIG_.questionCount + 2 ||
      form.getItems(FormApp.ItemType.TEXT).length !== 2 ||
      form.getItems(FormApp.ItemType.MULTIPLE_CHOICE).length !==
        QUIZ_CONFIG_.questionCount
    ) {
      throw new Error('測驗欄位或題目數量不符合預期。');
    }
    logQuiz_(
      '成功',
      '正常測試通過｜題庫=100｜抽題=20｜姓名與學號欄位=2'
    );
  } catch (error) {
    logQuizError_('正常測試失敗｜原因：' + error.message);
    throw error;
  }
}

/**
 * 將本案例恢復到「題庫檢查通過、尚未建立測驗」的驗收狀態。
 *
 * 這是教學流程重跑工具，不會刪除題庫。既有表單只會改名並停止
 * 接受回覆，不會永久刪除；其後清除表單 ID 與測驗設定中的網址。
 */
function resetQuizTeachingRun() {
  logQuiz_('開始', '準備重置教師隨機測驗教學驗收狀態');

  try {
    setupQuizGenerator();
    var spreadsheet = openQuizSpreadsheet_();
    var settingsSheet = spreadsheet.getSheetByName(
      QUIZ_CONFIG_.settingsSheetName
    );
    var formId = readQuizFormId_();
    if (formId === '') {
      formId = extractQuizFormIdFromEditUrl_(
        settingsSheet.getRange('B5').getValue()
      );
    }

    if (formId !== '') {
      var form = FormApp.openById(formId);
      form
        .setTitle(QUIZ_CONFIG_.formTitle + '【流程重跑前作廢】')
        .setAcceptingResponses(false);
      logQuiz_('進度', '既有教學測驗已改名並停止接受回覆');
    } else {
      logQuiz_('略過', '目前沒有需要作廢的既有教學測驗');
    }

    PropertiesService.getScriptProperties().deleteProperty(
      QUIZ_CONFIG_.formIdProperty
    );
    settingsSheet.getRange('B4').setValue('未設定');
    settingsSheet.getRange('B5:B10').clearContent();
    logQuiz_(
      '成功',
      '教學驗收狀態已重置｜題庫保留｜下一步從 Sheets 選單建立第一份測驗'
    );
  } catch (error) {
    logQuizError_('重置教學驗收狀態失敗｜原因：' + error.message);
    throw error;
  }
}

/**
 * 從 Google Forms 編輯網址取出表單 ID。
 *
 * @param {*} editUrl Google Forms 編輯網址。
 * @return {string} 表單 ID；不是可辨識網址時回傳空字串。
 */
function extractQuizFormIdFromEditUrl_(editUrl) {
  var match = String(editUrl || '').match(
    /^https:\/\/docs\.google\.com\/forms\/d\/([A-Za-z0-9_-]+)\/edit/
  );
  return match ? match[1] : '';
}

/**
 * 錯誤測試：驗證題庫不足、題號重複、答案錯誤及分數錯誤。
 */
function testQuizErrors() {
  logQuiz_('開始', '準備執行題庫錯誤測試');

  try {
    var fixtures = buildQuizQuestionFixtures_();
    assertQuizValidationError_(
      fixtures.slice(0, 19),
      '有效題目不足 20 題',
      '題庫不足'
    );

    var duplicateRows = fixtures.slice(0, 20).map(function (row) {
      return row.slice();
    });
    duplicateRows[1][1] = duplicateRows[0][1];
    assertQuizValidationError_(
      duplicateRows,
      '題號重複',
      '題號重複'
    );

    var wrongAnswerRows = fixtures.slice(0, 20).map(function (row) {
      return row.slice();
    });
    wrongAnswerRows[0][5] = '不在選項中的答案';
    assertQuizValidationError_(
      wrongAnswerRows,
      '正確答案不在選項中',
      '答案錯誤'
    );

    var wrongPointsRows = fixtures.slice(0, 20).map(function (row) {
      return row.slice();
    });
    wrongPointsRows[0][6] = 0;
    assertQuizValidationError_(
      wrongPointsRows,
      '分數必須是正整數',
      '分數錯誤'
    );

    logQuiz_('成功', '錯誤測試通過｜四種錯誤都在建立表單前被拒絕');
  } catch (error) {
    logQuizError_('錯誤測試失敗｜原因：' + error.message);
    throw error;
  }
}

/**
 * 確認題庫資料會收到指定錯誤。
 *
 * @param {Array<Array<*>>} rows 測試題庫。
 * @param {string} expectedMessage 預期錯誤片段。
 * @param {string} label 測試名稱。
 */
function assertQuizValidationError_(rows, expectedMessage, label) {
  try {
    validateQuizQuestionRows_(rows);
  } catch (error) {
    if (error.message.indexOf(expectedMessage) !== -1) {
      return;
    }
    throw new Error(label + '收到非預期錯誤：' + error.message);
  }
  throw new Error(label + '沒有被題庫檢查拒絕。');
}

/**
 * 重複測試：兩次產生都更新同一份表單，題目不會累加。
 */
function testQuizRepeat() {
  logQuiz_('開始', '準備執行教師隨機測驗重複測試');

  try {
    var formId = readQuizFormId_();
    if (formId === '') {
      throw new Error(
        '缺少 QUIZ_FORM_ID，請先完成第一份測驗的指令碼屬性設定。'
      );
    }

    var spreadsheet = openQuizSpreadsheet_();
    var questionSheet = spreadsheet.getSheetByName(
      QUIZ_CONFIG_.questionSheetName
    );
    var widthsBefore = [];
    for (
      var column = 1;
      column <= QUIZ_CONFIG_.questionHeaders.length;
      column += 1
    ) {
      widthsBefore.push(questionSheet.getColumnWidth(column));
    }

    var first = generateQuizForm();
    var second = generateQuizForm();
    var form = FormApp.openById(formId);
    if (
      first.formId !== formId ||
      second.formId !== formId ||
      form.getItems().length !== QUIZ_CONFIG_.questionCount + 2
    ) {
      throw new Error('重複執行沒有沿用同一份 20 題測驗。');
    }

    var widthsAfter = [];
    for (
      var index = 1;
      index <= QUIZ_CONFIG_.questionHeaders.length;
      index += 1
    ) {
      widthsAfter.push(questionSheet.getColumnWidth(index));
    }
    if (JSON.stringify(widthsBefore) !== JSON.stringify(widthsAfter)) {
      throw new Error('重複執行改變了老師手動調整的題庫欄寬。');
    }

    logQuiz_(
      '成功',
      '重複測試通過｜沿用同一份表單｜題目總數=20｜欄寬保留'
    );
  } catch (error) {
    logQuizError_('重複測試失敗｜原因：' + error.message);
    throw error;
  }
}
