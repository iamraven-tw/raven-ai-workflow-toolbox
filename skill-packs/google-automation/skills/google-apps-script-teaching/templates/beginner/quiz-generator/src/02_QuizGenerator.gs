/**
 * 試算表開啟時建立測驗工具選單。
 *
 * @param {Object=} event Google Sheets 開啟事件。
 */
function onOpen(event) {
  SpreadsheetApp.getUi()
    .createMenu(QUIZ_CONFIG_.menuName)
    .addItem('建立或檢查題庫版面', 'setupQuizGenerator')
    .addItem('檢查題庫', 'checkQuizBank')
    .addItem('產生隨機測驗', 'generateQuizForm')
    .addItem('更新成績報表', 'updateScoreReport')
    .addToUi();
}

/**
 * 建立題庫、測驗設定與成績報表工作表。
 */
function setupQuizGenerator() {
  logQuiz_('開始', '準備建立教師隨機測驗與成績報表');

  try {
    var spreadsheet = openQuizSpreadsheet_();
    var questionResult = ensureQuizSheet_(
      spreadsheet,
      QUIZ_CONFIG_.questionSheetName,
      true
    );
    var settingsResult = ensureQuizSheet_(
      spreadsheet,
      QUIZ_CONFIG_.settingsSheetName,
      false
    );
    var reportResult = ensureQuizSheet_(
      spreadsheet,
      QUIZ_CONFIG_.reportSheetName,
      false
    );

    setupQuestionBankSheet_(questionResult.sheet, questionResult.created);
    setupQuizSettingsSheet_(settingsResult.sheet, settingsResult.created);
    setupQuizReportSheet_(reportResult.sheet, reportResult.created);

    logQuiz_('設定', '建立題庫版面不需要指令碼屬性');
    logQuiz_(
      '成功',
      '已建立題庫、測驗設定、成績報表與 100 題日本動漫教學題庫'
    );
  } catch (error) {
    logQuizError_('建立教師隨機測驗版面失敗｜原因：' + error.message);
    throw error;
  }
}

/**
 * 取得或建立指定工作表。
 *
 * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} spreadsheet 試算表。
 * @param {string} name 工作表名稱。
 * @param {boolean} mayRenameBlankSheet 是否可使用空白預設工作表。
 * @return {{sheet:GoogleAppsScript.Spreadsheet.Sheet,created:boolean}} 結果。
 */
function ensureQuizSheet_(spreadsheet, name, mayRenameBlankSheet) {
  var existing = spreadsheet.getSheetByName(name);
  if (existing) {
    return {sheet: existing, created: false};
  }

  var sheets = spreadsheet.getSheets();
  if (
    mayRenameBlankSheet &&
    sheets.length === 1 &&
    isBlankQuizSheet_(sheets[0])
  ) {
    sheets[0].setName(name);
    logQuiz_('進度', '已將空白預設工作表設定為 ' + name);
    return {sheet: sheets[0], created: true};
  }

  logQuiz_('進度', '正在建立 ' + name + ' 工作表');
  return {sheet: spreadsheet.insertSheet(name), created: true};
}

/**
 * 判斷工作表是否仍是全新的空白預設頁。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 工作表。
 * @return {boolean} 是否空白。
 */
function isBlankQuizSheet_(sheet) {
  return (
    sheet.getLastRow() <= 1 &&
    sheet.getLastColumn() <= 1 &&
    String(sheet.getRange('A1').getValue() || '').trim() === ''
  );
}

/**
 * 初始化題庫；日後重跑不覆寫老師已修改的題目或欄寬。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 題庫工作表。
 * @param {boolean} created 是否為新工作表。
 */
function setupQuestionBankSheet_(sheet, created) {
  var headerRange = sheet.getRange(1, 1, 1, QUIZ_CONFIG_.questionHeaders.length);
  var currentHeaders = headerRange.getValues()[0];
  var initialized = currentHeaders.join('|') ===
    QUIZ_CONFIG_.questionHeaders.join('|');

  if (!initialized) {
    headerRange.setValues([QUIZ_CONFIG_.questionHeaders]);
    headerRange
      .setFontWeight('bold')
      .setBackground('#d9ead3')
      .setHorizontalAlignment('center');
    sheet.setFrozenRows(1);
  }

  var dataRange = sheet.getRange(
    2,
    1,
    Math.max(sheet.getMaxRows() - 1, QUIZ_CONFIG_.fixtureCount),
    QUIZ_CONFIG_.questionHeaders.length
  );
  var existingRows = dataRange.getValues();
  var hasQuestionData = existingRows.some(function (row) {
    return row.slice(1).some(function (value) {
      return String(value || '').trim() !== '';
    });
  });

  if (!hasQuestionData) {
    var fixtures = buildQuizQuestionFixtures_();
    sheet
      .getRange(2, 1, fixtures.length, QUIZ_CONFIG_.questionHeaders.length)
      .setValues(fixtures);
    sheet.getRange(2, 1, fixtures.length, 1).insertCheckboxes();
  }

  // 只有第一次建立版面時設定初始欄寬，保留老師日後手動調整。
  if (created || !initialized) {
    [90, 80, 320, 90, 260, 110, 70, 240, 240].forEach(function (
      width,
      index
    ) {
      sheet.setColumnWidth(index + 1, width);
    });
  }
}

/**
 * 初始化測驗設定工作表。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 設定工作表。
 * @param {boolean} created 是否為新工作表。
 */
function setupQuizSettingsSheet_(sheet, created) {
  var labels = [
    ['項目', '值'],
    ['每次抽題數', QUIZ_CONFIG_.questionCount],
    ['及格百分比', QUIZ_CONFIG_.passingPercent],
    ['QUIZ_FORM_ID 狀態', readQuizFormId_() === '' ? '未設定' : '已設定'],
    ['測驗編輯網址', ''],
    ['測驗填寫網址', ''],
    ['最後產生時間', ''],
    ['最後抽題數', ''],
    ['最後更新成績時間', ''],
    ['成績筆數', '']
  ];

  if (String(sheet.getRange('A1').getValue() || '').trim() === '') {
    sheet.getRange(1, 1, labels.length, 2).setValues(labels);
    sheet.getRange('A1:B1').setFontWeight('bold').setBackground('#cfe2f3');
    sheet.setFrozenRows(1);
  } else {
    sheet.getRange('B2').setValue(QUIZ_CONFIG_.questionCount);
    sheet.getRange('B3').setValue(QUIZ_CONFIG_.passingPercent);
    sheet
      .getRange('B4')
      .setValue(readQuizFormId_() === '' ? '未設定' : '已設定');
  }

  // 只有第一次建立設定頁時給合理寬度，後續更新不重設。
  if (created) {
    sheet.setColumnWidth(1, 170);
    sheet.setColumnWidth(2, 520);
  }
}

/**
 * 初始化成績報表工作表。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 成績報表。
 * @param {boolean} created 是否為新工作表。
 */
function setupQuizReportSheet_(sheet, created) {
  var headerRange = sheet.getRange(1, 1, 1, QUIZ_CONFIG_.reportHeaders.length);
  var headers = headerRange.getValues()[0];
  if (headers.join('|') !== QUIZ_CONFIG_.reportHeaders.join('|')) {
    headerRange.setValues([QUIZ_CONFIG_.reportHeaders]);
    headerRange
      .setFontWeight('bold')
      .setBackground('#fce5cd')
      .setHorizontalAlignment('center');
    sheet.setFrozenRows(1);
  }

  // 日常更新成績只改內容，不改老師手動調整後的欄寬。
  if (created) {
    [150, 120, 120, 80, 80, 100, 100].forEach(function (width, index) {
      sheet.setColumnWidth(index + 1, width);
    });
  }
}

/**
 * 從題庫工作表讀取實際有題號或題目的列。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 題庫工作表。
 * @return {Array<Array<*>>} 題庫資料列。
 */
function readQuizQuestionRows_(sheet) {
  var maxRows = Math.max(sheet.getLastRow() - 1, 0);
  if (maxRows === 0) {
    return [];
  }

  var rows = sheet
    .getRange(2, 1, maxRows, QUIZ_CONFIG_.questionHeaders.length)
    .getValues();
  var lastDataIndex = -1;
  rows.forEach(function (row, index) {
    if (
      String(row[1] || '').trim() !== '' ||
      String(row[2] || '').trim() !== ''
    ) {
      lastDataIndex = index;
    }
  });
  return lastDataIndex < 0 ? [] : rows.slice(0, lastDataIndex + 1);
}

/**
 * 將一列題庫資料轉成可檢查物件。
 *
 * @param {Array<*>} row 原始資料列。
 * @param {number} rowNumber Sheets 列號。
 * @return {Object} 正規化題目。
 */
function normalizeQuizQuestionRow_(row, rowNumber) {
  var enabledText = String(row[0] || '').trim().toUpperCase();
  var enabled = row[0] === true || enabledText === 'TRUE' || enabledText === '是';
  var options = String(row[4] || '')
    .split('|')
    .map(function (value) {
      return value.trim();
    })
    .filter(function (value) {
      return value !== '';
    });

  return {
    rowNumber: rowNumber,
    enabled: enabled,
    id: String(row[1] || '').trim(),
    title: String(row[2] || '').trim(),
    type: String(row[3] || '').trim(),
    options: options,
    answer: String(row[5] || '').trim(),
    points: Number(row[6]),
    correctFeedback: String(row[7] || '').trim(),
    incorrectFeedback: String(row[8] || '').trim()
  };
}

/**
 * 驗證題庫並回傳所有啟用且有效的題目。
 *
 * @param {Array<Array<*>>} rows 原始資料列。
 * @param {number=} minimumCount 最少有效題數。
 * @return {Array<Object>} 有效題目。
 */
function validateQuizQuestionRows_(rows, minimumCount) {
  var requiredCount = minimumCount || QUIZ_CONFIG_.minimumQuestionCount;
  var seenIds = {};
  var questions = [];
  var errors = [];

  rows.forEach(function (row, index) {
    var question = normalizeQuizQuestionRow_(row, index + 2);
    if (!question.enabled) {
      return;
    }

    if (question.id === '') {
      errors.push('第 ' + question.rowNumber + ' 列缺少題號');
    } else if (seenIds[question.id]) {
      errors.push('題號重複：' + question.id);
    } else {
      seenIds[question.id] = true;
    }

    if (question.title === '') {
      errors.push('第 ' + question.rowNumber + ' 列缺少題目');
    }
    if (['單選題', '是非題'].indexOf(question.type) === -1) {
      errors.push('第 ' + question.rowNumber + ' 列題型只支援單選題或是非題');
    }
    if (question.options.length < 2) {
      errors.push('第 ' + question.rowNumber + ' 列至少需要兩個選項');
    }
    if (
      question.answer === '' ||
      question.options.indexOf(question.answer) === -1
    ) {
      errors.push('第 ' + question.rowNumber + ' 列的正確答案不在選項中');
    }
    if (
      !Number.isFinite(question.points) ||
      question.points <= 0 ||
      Math.floor(question.points) !== question.points
    ) {
      errors.push('第 ' + question.rowNumber + ' 列的分數必須是正整數');
    }

    questions.push(question);
  });

  if (questions.length < requiredCount) {
    errors.push('有效題目不足 ' + requiredCount + ' 題');
  }
  if (errors.length > 0) {
    throw new Error(errors.slice(0, 5).join('；'));
  }
  return questions;
}

/**
 * 檢查目前 Sheets 題庫。
 *
 * @return {Array<Object>} 有效題目。
 */
function checkQuizBank() {
  logQuiz_('開始', '準備檢查教師隨機測驗題庫');

  try {
    var spreadsheet = openQuizSpreadsheet_();
    var sheet = spreadsheet.getSheetByName(QUIZ_CONFIG_.questionSheetName);
    if (!sheet) {
      throw new Error('找不到題庫工作表，請先執行 setupQuizGenerator。');
    }
    var questions = validateQuizQuestionRows_(readQuizQuestionRows_(sheet));
    logQuiz_('設定', '本步驟不需要 QUIZ_FORM_ID');
    logQuiz_('成功', '題庫檢查通過｜有效題目=' + questions.length);
    return questions;
  } catch (error) {
    logQuizError_('題庫檢查未通過｜原因：' + error.message);
    throw error;
  }
}

/**
 * 不重複抽出指定數量題目。
 *
 * @param {Array<Object>} questions 所有有效題目。
 * @param {number} count 抽題數。
 * @param {function():number=} randomFunction 可替換的亂數函式。
 * @return {Array<Object>} 抽出的題目。
 */
function sampleQuizQuestions_(questions, count, randomFunction) {
  if (questions.length < count) {
    throw new Error('有效題目不足 ' + count + ' 題，無法產生測驗。');
  }
  var random = randomFunction || Math.random;
  var shuffled = questions.slice();
  for (var index = shuffled.length - 1; index > 0; index -= 1) {
    var swapIndex = Math.floor(random() * (index + 1));
    var temporary = shuffled[index];
    shuffled[index] = shuffled[swapIndex];
    shuffled[swapIndex] = temporary;
  }
  return shuffled.slice(0, count);
}

/**
 * 取得既有表單，或在第一次執行時建立一份新表單。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} settingsSheet 設定工作表。
 * @return {{form:GoogleAppsScript.Forms.Form,created:boolean}} 表單結果。
 */
function resolveQuizForm_(settingsSheet) {
  var formId = readQuizFormId_();
  if (formId !== '') {
    return {form: FormApp.openById(formId), created: false};
  }

  var existingEditUrl = String(settingsSheet.getRange('B5').getValue() || '')
    .trim();
  if (existingEditUrl !== '') {
    throw new Error(
      '已經建立第一份測驗，但尚未設定 QUIZ_FORM_ID；請先完成指令碼屬性設定，避免重複建立表單。'
    );
  }
  return {form: FormApp.create(QUIZ_CONFIG_.formTitle, true), created: true};
}

/**
 * 清除舊題目並建立本次全班共用的 20 題測驗。
 *
 * @param {GoogleAppsScript.Forms.Form} form 測驗表單。
 * @param {Array<Object>} questions 本次抽出的題目。
 */
function rewriteQuizForm_(form, questions) {
  var items = form.getItems();
  for (var index = items.length - 1; index >= 0; index -= 1) {
    form.deleteItem(index);
  }

  form
    .setTitle(QUIZ_CONFIG_.formTitle)
    .setDescription(
      '本測驗共 20 題。教學驗收請使用假姓名與假學號，不要填入真實學生資料。'
    )
    .setIsQuiz(true)
    .setCollectEmail(false)
    .setLimitOneResponsePerUser(false)
    .setProgressBar(true)
    .setPublishingSummary(false)
    .setShowLinkToRespondAgain(false)
    .setShuffleQuestions(false)
    .setConfirmationMessage('作答已送出，請等待老師公布成績。');

  if (typeof form.setPublished === 'function') {
    form.setPublished(true);
  }

  form
    .addTextItem()
    .setTitle(QUIZ_CONFIG_.nameFieldTitle)
    .setHelpText('例如：測試學生甲')
    .setRequired(true);

  var studentIdValidation = FormApp.createTextValidation()
    .setHelpText('請輸入 4 至 20 碼英文字母、數字或連字號。')
    .requireTextMatchesPattern('^[A-Za-z0-9-]{4,20}$')
    .build();
  form
    .addTextItem()
    .setTitle(QUIZ_CONFIG_.studentIdFieldTitle)
    .setHelpText('例如：TEST-001')
    .setValidation(studentIdValidation)
    .setRequired(true);

  questions.forEach(function (question) {
    var item = form
      .addMultipleChoiceItem()
      .setTitle('[' + question.id + '] ' + question.title)
      .setRequired(true)
      .setPoints(question.points)
      .showOtherOption(false);
    item.setChoices(
      question.options.map(function (option) {
        return item.createChoice(option, option === question.answer);
      })
    );
  });
}

/**
 * 從 100 題題庫隨機抽取 20 題並建立或更新同一份 Google Forms。
 *
 * @return {{formId:string,editUrl:string,publishedUrl:string,
 *   questionCount:number,created:boolean}} 測驗結果。
 */
function generateQuizForm() {
  logQuiz_('開始', '準備產生教師隨機測驗');

  try {
    setupQuizGenerator();
    var spreadsheet = openQuizSpreadsheet_();
    var settingsSheet = spreadsheet.getSheetByName(
      QUIZ_CONFIG_.settingsSheetName
    );
    var questions = checkQuizBank();
    var selected = sampleQuizQuestions_(
      questions,
      QUIZ_CONFIG_.questionCount
    );
    var formResult = resolveQuizForm_(settingsSheet);
    rewriteQuizForm_(formResult.form, selected);

    settingsSheet
      .getRange('B4')
      .setValue(readQuizFormId_() === '' ? '未設定' : '已設定');
    settingsSheet.getRange('B5').setValue(formResult.form.getEditUrl());
    settingsSheet.getRange('B6').setValue(formResult.form.getPublishedUrl());
    settingsSheet.getRange('B7').setValue(new Date());
    settingsSheet.getRange('B8').setValue(selected.length);

    if (formResult.created) {
      logQuiz_(
        '進度',
        '已建立第一份測驗；下一步需將 QUIZ_FORM_ID 存入指令碼屬性'
      );
    } else {
      logQuiz_('進度', '已更新原有測驗，沒有建立第二份表單');
    }
    logQuiz_('成功', '隨機測驗產生完成｜題目數=' + selected.length);
    return {
      formId: formResult.form.getId(),
      editUrl: formResult.form.getEditUrl(),
      publishedUrl: formResult.form.getPublishedUrl(),
      questionCount: selected.length,
      created: formResult.created
    };
  } catch (error) {
    logQuizError_('產生隨機測驗失敗｜原因：' + error.message);
    throw error;
  }
}

/**
 * 從表單作答中取得指定欄位答案。
 *
 * @param {GoogleAppsScript.Forms.ItemResponse[]} responses 單筆作答。
 * @param {string} title 欄位名稱。
 * @return {string} 作答內容。
 */
function findQuizResponseValue_(responses, title) {
  for (var index = 0; index < responses.length; index += 1) {
    if (responses[index].getItem().getTitle() === title) {
      return String(responses[index].getResponse() || '').trim();
    }
  }
  return '';
}

/**
 * 將 Forms 回覆整理成成績報表資料。
 *
 * @param {GoogleAppsScript.Forms.FormResponse[]} formResponses 表單回覆。
 * @param {number} maximumScore 目前測驗滿分。
 * @param {number} passingPercent 及格百分比。
 * @return {Array<Array<*>>} 成績報表資料。
 */
function buildQuizScoreRows_(formResponses, maximumScore, passingPercent) {
  return formResponses.map(function (response) {
    var itemResponses = response.getItemResponses();
    var score = response
      .getGradableItemResponses()
      .reduce(function (total, itemResponse) {
        var itemScore = Number(itemResponse.getScore());
        return total + (Number.isFinite(itemScore) ? itemScore : 0);
      }, 0);
    var ratio = maximumScore > 0 ? score / maximumScore : 0;
    return [
      response.getTimestamp(),
      findQuizResponseValue_(itemResponses, QUIZ_CONFIG_.nameFieldTitle),
      findQuizResponseValue_(itemResponses, QUIZ_CONFIG_.studentIdFieldTitle),
      score,
      maximumScore,
      ratio,
      ratio * 100 >= passingPercent ? '及格' : '未及格'
    ];
  });
}

/**
 * 讀取目前表單回覆並重建教師成績報表。
 *
 * @return {{responseCount:number,maximumScore:number}} 更新結果。
 */
function updateScoreReport() {
  logQuiz_('開始', '準備更新教師成績報表');

  try {
    setupQuizGenerator();
    var form = checkQuizFormSettings();
    var questions = form.getItems(FormApp.ItemType.MULTIPLE_CHOICE);
    var maximumScore = questions.reduce(function (total, item) {
      return total + item.asMultipleChoiceItem().getPoints();
    }, 0);
    var rows = buildQuizScoreRows_(
      form.getResponses(),
      maximumScore,
      QUIZ_CONFIG_.passingPercent
    );
    var spreadsheet = openQuizSpreadsheet_();
    var reportSheet = spreadsheet.getSheetByName(QUIZ_CONFIG_.reportSheetName);
    var settingsSheet = spreadsheet.getSheetByName(
      QUIZ_CONFIG_.settingsSheetName
    );

    if (reportSheet.getLastRow() > 1) {
      reportSheet
        .getRange(
          2,
          1,
          reportSheet.getLastRow() - 1,
          QUIZ_CONFIG_.reportHeaders.length
        )
        .clearContent();
    }
    if (rows.length > 0) {
      reportSheet
        .getRange(2, 1, rows.length, QUIZ_CONFIG_.reportHeaders.length)
        .setValues(rows);
      reportSheet.getRange(2, 1, rows.length, 1).setNumberFormat(
        'yyyy/mm/dd hh:mm:ss'
      );
      reportSheet.getRange(2, 6, rows.length, 1).setNumberFormat('0.00%');
    }

    settingsSheet.getRange('B9').setValue(new Date());
    settingsSheet.getRange('B10').setValue(rows.length);
    logQuiz_(
      '成功',
      rows.length === 0
        ? '成績報表已更新｜目前尚無測驗回覆'
        : '成績報表已更新｜作答筆數=' + rows.length
    );
    return {responseCount: rows.length, maximumScore: maximumScore};
  } catch (error) {
    logQuizError_('更新成績報表失敗｜原因：' + error.message);
    throw error;
  }
}
