var UPLOAD_LOGGER_CONFIG_ = {
  folderProperty: 'WATCH_FOLDER_ID',
  spreadsheetProperty: 'LOG_SPREADSHEET_ID',
  baselineProperty: 'UPLOAD_BASELINE_AT',
  lastCheckProperty: 'UPLOAD_LAST_CHECK_AT',
  settingsSheetName: '教學設定',
  logSheetName: '上傳紀錄',
  testFolderName: '檔案上傳測試資料夾（教學測試）',
  triggerFunctionName: 'runUploadCheckByTimer',
  legacyTriggerFunctionName: 'checkNewDriveUploads',
  triggerExpiresAtProperty: 'UPLOAD_TRIGGER_EXPIRES_AT',
  triggerIntervalMinutes: 1,
  triggerDurationMinutes: 10,
  queryOverlapMinutes: 10,
  timeZone: 'Asia/Taipei'
};

/**
 * 檢查指定資料夾與紀錄試算表設定。
 */
function checkDriveUploadSettings() {
  logInfo_('開始', '準備檢查檔案上傳紀錄器設定');

  try {
    var settings = readDriveUploadSettings_();
    DriveApp.getFolderById(settings.folderId).getName();
    SpreadsheetApp.openById(settings.spreadsheetId).getName();
    logInfo_('設定', 'WATCH_FOLDER_ID 與 LOG_SPREADSHEET_ID 已設定且可以開啟');
    logInfo_('成功', '檔案上傳紀錄器設定檢查通過');
  } catch (error) {
    throw logAndBuildError_('設定檢查未通過', error);
  }
}

/**
 * 讀取並驗證必要的指令碼屬性。
 *
 * @return {{folderId: string, spreadsheetId: string}} 設定值。
 */
function readDriveUploadSettings_() {
  var properties = PropertiesService.getScriptProperties();
  return validateDriveUploadSettings_({
    folderId: properties.getProperty(UPLOAD_LOGGER_CONFIG_.folderProperty),
    spreadsheetId: properties.getProperty(
      UPLOAD_LOGGER_CONFIG_.spreadsheetProperty
    )
  });
}

/**
 * 驗證設定值，讓測試不需要修改真實指令碼屬性。
 *
 * @param {{folderId: string, spreadsheetId: string}} settings 待驗證設定。
 * @return {{folderId: string, spreadsheetId: string}} 整理後設定。
 */
function validateDriveUploadSettings_(settings) {
  var folderId = String(settings.folderId || '').trim();
  var spreadsheetId = String(settings.spreadsheetId || '').trim();

  if (!folderId) {
    throw new Error(
      '缺少 WATCH_FOLDER_ID，請到專案設定的指令碼屬性新增後再執行。'
    );
  }

  if (!spreadsheetId) {
    throw new Error(
      '缺少 LOG_SPREADSHEET_ID，請到專案設定的指令碼屬性新增後再執行。'
    );
  }

  if (!isLikelyGoogleResourceId_(folderId)) {
    throw new Error('WATCH_FOLDER_ID 格式不正確，請確認只填入資料夾 ID。');
  }

  if (!isLikelyGoogleResourceId_(spreadsheetId)) {
    throw new Error(
      'LOG_SPREADSHEET_ID 格式不正確，請確認只填入試算表 ID。'
    );
  }

  return {
    folderId: folderId,
    spreadsheetId: spreadsheetId
  };
}

/**
 * 做不洩漏內容的 Google 資源 ID 基本格式檢查。
 *
 * @param {string} value ID。
 * @return {boolean} 是否符合常見格式。
 */
function isLikelyGoogleResourceId_(value) {
  return /^[A-Za-z0-9_-]{20,}$/.test(String(value || ''));
}
