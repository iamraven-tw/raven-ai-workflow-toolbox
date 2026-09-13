var QUIZ_CONFIG_ = Object.freeze({
  questionSheetName: '題庫',
  settingsSheetName: '測驗設定',
  reportSheetName: '成績報表',
  menuName: '測驗工具',
  formIdProperty: 'QUIZ_FORM_ID',
  formTitle: '教師隨機測驗（教學測試）',
  questionCount: 20,
  minimumQuestionCount: 20,
  passingPercent: 60,
  fixtureCount: 100,
  nameFieldTitle: '姓名（請使用測試假姓名）',
  studentIdFieldTitle: '學號（請使用測試假學號）',
  questionHeaders: [
    '是否啟用',
    '題號',
    '題目',
    '題型',
    '選項（使用 | 分隔）',
    '正確答案',
    '分數',
    '答對說明',
    '答錯說明'
  ],
  reportHeaders: [
    '提交時間',
    '姓名',
    '學號',
    '得分',
    '滿分',
    '百分比',
    '是否及格'
  ]
});

/**
 * 取得目前綁定的教學試算表。
 *
 * @return {GoogleAppsScript.Spreadsheet.Spreadsheet} 教學試算表。
 */
function openQuizSpreadsheet_() {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  if (!spreadsheet) {
    throw new Error('目前程式沒有綁定可使用的 Google Sheets。');
  }
  return spreadsheet;
}

/**
 * 讀取測驗表單 ID；只回傳值，不寫入紀錄檔(Log)。
 *
 * @return {string} 已設定的表單 ID，未設定時為空字串。
 */
function readQuizFormId_() {
  return String(
    PropertiesService.getScriptProperties().getProperty(
      QUIZ_CONFIG_.formIdProperty
    ) || ''
  ).trim();
}

/**
 * 檢查已設定的測驗表單是否可以開啟。
 *
 * @return {GoogleAppsScript.Forms.Form} 已核對的測驗表單。
 */
function checkQuizFormSettings() {
  logQuiz_('開始', '準備檢查教師隨機測驗設定');

  try {
    var formId = readQuizFormId_();
    if (formId === '') {
      throw new Error(
        '缺少 QUIZ_FORM_ID，請先產生第一份測驗，再到專案設定的指令碼屬性新增後重試。'
      );
    }

    var form = FormApp.openById(formId);
    logQuiz_('設定', 'QUIZ_FORM_ID 已設定且可以開啟測驗表單');
    logQuiz_('成功', '教師隨機測驗設定檢查通過');
    return form;
  } catch (error) {
    logQuizError_('設定檢查未通過｜原因：' + error.message);
    throw error;
  }
}
