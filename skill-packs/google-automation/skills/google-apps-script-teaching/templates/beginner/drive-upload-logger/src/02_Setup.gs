/**
 * 試算表開啟時建立日常操作選單。
 *
 * @param {Object} event 試算表開啟事件。
 */
function onOpen(event) {
  SpreadsheetApp.getUi()
    .createMenu('上傳工具')
    .addItem('建立／檢查版面', 'setupDriveUploadLogger')
    .addItem('檢查設定', 'checkDriveUploadSettings')
    .addSeparator()
    .addItem('初始化檢查起點', 'initializeUploadBaseline')
    .addItem('檢查新上傳', 'checkNewDriveUploads')
    .addSeparator()
    .addItem(
      '啟用每分鐘檢查（教學 10 分鐘）',
      'setupUploadCheckTrigger'
    )
    .addItem('停止自動檢查', 'removeUploadCheckTrigger')
    .addItem('查看自動檢查狀態', 'checkUploadCheckTrigger')
    .addToUi();
}

/**
 * 建立教學工作表、初始欄寬及專用測試資料夾。
 */
function setupDriveUploadLogger() {
  logInfo_('開始', '準備建立指定資料夾檔案上傳紀錄器');

  try {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    if (!spreadsheet) {
      throw new Error('找不到綁定的教學試算表。');
    }

    spreadsheet.setSpreadsheetTimeZone(UPLOAD_LOGGER_CONFIG_.timeZone);
    var logSheet = ensureUploadLogSheet_(spreadsheet);
    var settingsSheet = ensureUploadSettingsSheet_(spreadsheet);
    var folder = ensureTeachingUploadFolder_(settingsSheet);

    writeTeachingSettings_(settingsSheet, spreadsheet, folder);
    logSheet.setFrozenRows(1);

    logInfo_('設定', '本步驟只建立可見設定，尚未寫入指令碼屬性');
    logInfo_('成功', '已建立上傳紀錄、教學設定與專用測試資料夾');
  } catch (error) {
    throw logAndBuildError_('建立檔案上傳紀錄器失敗', error);
  }
}

/**
 * 建立或沿用上傳紀錄工作表。
 *
 * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} spreadsheet 試算表。
 * @return {GoogleAppsScript.Spreadsheet.Sheet} 工作表。
 */
function ensureUploadLogSheet_(spreadsheet) {
  var sheet = spreadsheet.getSheetByName(UPLOAD_LOGGER_CONFIG_.logSheetName);
  var isNew = false;

  if (!sheet) {
    var sheets = spreadsheet.getSheets();
    var firstSheet = sheets[0];
    var isBlankDefault =
      sheets.length === 1 &&
      firstSheet.getLastRow() === 0 &&
      firstSheet.getLastColumn() === 0;

    if (isBlankDefault) {
      firstSheet.setName(UPLOAD_LOGGER_CONFIG_.logSheetName);
      sheet = firstSheet;
    } else {
      sheet = spreadsheet.insertSheet(UPLOAD_LOGGER_CONFIG_.logSheetName);
    }
    isNew = true;
  }

  var headers = [
    '上傳者',
    '檔案名稱',
    '檔案類型',
    'MIME type',
    '上傳時間',
    '偵測時間',
    '檔案網址',
    '檔案 ID',
    '處理狀態',
    '活動識別'
  ];
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  sheet
    .getRange(1, 1, 1, headers.length)
    .setFontWeight('bold')
    .setBackground('#d9ead3');

  if (isNew) {
    var widths = [150, 220, 110, 190, 150, 150, 260, 210, 110, 250];
    widths.forEach(function (width, index) {
      sheet.setColumnWidth(index + 1, width);
    });
  }

  return sheet;
}

/**
 * 建立或沿用教學設定工作表。
 *
 * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} spreadsheet 試算表。
 * @return {GoogleAppsScript.Spreadsheet.Sheet} 工作表。
 */
function ensureUploadSettingsSheet_(spreadsheet) {
  var sheet = spreadsheet.getSheetByName(
    UPLOAD_LOGGER_CONFIG_.settingsSheetName
  );
  var isNew = false;

  if (!sheet) {
    sheet = spreadsheet.insertSheet(UPLOAD_LOGGER_CONFIG_.settingsSheetName);
    isNew = true;
  }

  if (isNew) {
    sheet.setColumnWidth(1, 210);
    sheet.setColumnWidth(2, 520);
  }

  return sheet;
}

/**
 * 建立或沿用教學測試資料夾。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} settingsSheet 設定工作表。
 * @return {GoogleAppsScript.Drive.Folder} 資料夾。
 */
function ensureTeachingUploadFolder_(settingsSheet) {
  var existingId = String(settingsSheet.getRange('B5').getValue() || '').trim();

  if (existingId) {
    try {
      var existingFolder = DriveApp.getFolderById(existingId);
      existingFolder.getName();
      logInfo_('略過', '已沿用先前建立的專用測試資料夾');
      return existingFolder;
    } catch (error) {
      logWarning_('警告', '先前的資料夾已無法開啟，將建立新的教學資料夾');
    }
  }

  logInfo_('進度', '正在建立專用 Drive 測試資料夾');
  return DriveApp.createFolder(UPLOAD_LOGGER_CONFIG_.testFolderName);
}

/**
 * 將學生稍後要使用的網址與 ID 寫入私人教學試算表。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 設定工作表。
 * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} spreadsheet 試算表。
 * @param {GoogleAppsScript.Drive.Folder} folder 測試資料夾。
 */
function writeTeachingSettings_(sheet, spreadsheet, folder) {
  var rows = [
    ['指定資料夾檔案上傳紀錄器（教學測試）', ''],
    ['', ''],
    ['測試資料夾名稱', folder.getName()],
    ['測試資料夾網址', folder.getUrl()],
    ['WATCH_FOLDER_ID', folder.getId()],
    ['紀錄試算表網址', spreadsheet.getUrl()],
    ['LOG_SPREADSHEET_ID', spreadsheet.getId()],
    [
      '下一步',
      '請將 WATCH_FOLDER_ID 與 LOG_SPREADSHEET_ID 存入 Apps Script 指令碼屬性'
    ]
  ];

  sheet.getRange('A1:B1').breakApart();
  sheet.getRange(1, 1, rows.length, 2).setValues(rows);
  sheet.getRange('A1:B1').merge().setValue(rows[0][0]);
  sheet
    .getRange('A1:B1')
    .setFontWeight('bold')
    .setFontSize(14)
    .setBackground('#cfe2f3');
  sheet.getRange('A3:A8').setFontWeight('bold').setBackground('#f3f3f3');
  sheet.getRange('B4').setFormula('=HYPERLINK("' + folder.getUrl() + '","開啟測試資料夾")');
  sheet
    .getRange('B6')
    .setFormula('=HYPERLINK("' + spreadsheet.getUrl() + '","開啟紀錄試算表")');
  sheet.getRange('B5').setNumberFormat('@');
  sheet.getRange('B7').setNumberFormat('@');
}
