/**
 * 設定第一次檢查的時間基準，避免把歷史活動當成新上傳。
 */
function initializeUploadBaseline() {
  logInfo_('開始', '準備初始化檔案上傳檢查起點');

  try {
    readDriveUploadSettings_();
    var now = new Date().toISOString();
    var properties = PropertiesService.getScriptProperties();
    properties.setProperty(UPLOAD_LOGGER_CONFIG_.baselineProperty, now);
    properties.setProperty(UPLOAD_LOGGER_CONFIG_.lastCheckProperty, now);
    logInfo_('設定', '檢查起點已保存，未輸出實際時間值');
    logInfo_('成功', '初始化完成，之後只處理這個時間點以後的新上傳');
  } catch (error) {
    throw logAndBuildError_('初始化檢查起點失敗', error);
  }
}

/**
 * 查詢新的外部上傳活動並寫入紀錄表。
 *
 * @param {Object=} event Apps Script 觸發事件；日常選單不會傳入。
 */
function checkNewDriveUploads(event) {
  // 舊版曾直接把本函式設為時間觸發器；升級後先安全停止，
  // 避免舊的每 5 分鐘觸發器在背景持續執行。
  if (event && event.triggerUid) {
    stopLegacyUploadCheckTrigger_();
    logWarning_(
      '警告',
      '已停止舊版定時觸發器，請從試算表選單重新啟用教學模式'
    );
    return;
  }

  logInfo_('開始', '準備檢查指定資料夾的新上傳檔案');

  try {
    var settings = readDriveUploadSettings_();
    var properties = PropertiesService.getScriptProperties();
    var baseline = properties.getProperty(
      UPLOAD_LOGGER_CONFIG_.baselineProperty
    );
    var lastCheck = properties.getProperty(
      UPLOAD_LOGGER_CONFIG_.lastCheckProperty
    );

    if (!baseline || !lastCheck) {
      throw new Error(
        '尚未初始化檢查起點，請先執行 initializeUploadBaseline。'
      );
    }

    var startedAt = new Date();
    var queryStart = buildQueryStartTime_(baseline, lastCheck);
    var activities = queryDriveUploadActivities_(
      settings.folderId,
      queryStart
    );
    var candidates = extractUploadRecordsFromActivities_(activities);
    var directUploads = enrichAndFilterDirectUploads_(
      candidates,
      settings.folderId,
      startedAt
    );
    var spreadsheet = SpreadsheetApp.openById(settings.spreadsheetId);
    var sheet = spreadsheet.getSheetByName(
      UPLOAD_LOGGER_CONFIG_.logSheetName
    );

    if (!sheet) {
      throw new Error('找不到「上傳紀錄」工作表，請先執行版面設定函式。');
    }

    var written = appendUniqueUploadRecords_(sheet, directUploads);
    properties.setProperty(
      UPLOAD_LOGGER_CONFIG_.lastCheckProperty,
      startedAt.toISOString()
    );

    if (written === 0) {
      logInfo_('成功', '檢查完成，目前沒有需要新增的上傳紀錄');
      return;
    }

    logInfo_('成功', '檢查完成，已新增 ' + written + ' 筆上傳紀錄');
  } catch (error) {
    throw logAndBuildError_('檢查新上傳失敗', error);
  }
}

/**
 * 查詢 Drive Activity，保留分頁以避免資料量較大時漏記。
 *
 * @param {string} folderId 資料夾 ID。
 * @param {string} queryStart RFC 3339 起點。
 * @return {Object[]} Drive 活動。
 */
function queryDriveUploadActivities_(folderId, queryStart) {
  var activities = [];
  var pageToken = '';
  var pageCount = 0;

  do {
    var request = {
      ancestorName: 'items/' + folderId,
      pageSize: 100,
      filter:
        'detail.action_detail_case:CREATE time > "' + queryStart + '"',
      consolidationStrategy: {
        none: {}
      }
    };

    if (pageToken) {
      request.pageToken = pageToken;
    }

    var response = DriveActivity.Activity.query(request);
    activities = activities.concat(response.activities || []);
    pageToken = response.nextPageToken || '';
    pageCount += 1;
  } while (pageToken && pageCount < 10);

  if (pageToken) {
    logWarning_('警告', '活動資料超過本次安全分頁上限，請稍後再次檢查');
  }

  logInfo_('進度', 'Drive Activity 查詢完成，共取得 ' + activities.length + ' 筆候選活動');
  return activities;
}

/**
 * 從 Drive Activity 擷取明確標示為外部 upload 的建立事件。
 *
 * @param {Object[]} activities Drive 活動。
 * @return {Object[]} 尚未讀取 Drive 檔案細節的紀錄。
 */
function extractUploadRecordsFromActivities_(activities) {
  var records = [];

  (activities || []).forEach(function (activity) {
    var actions = resolveActivityActions_(activity);

    actions.forEach(function (action) {
      if (!isExternalUploadAction_(action.detail)) {
        return;
      }

      var target = action.target || {};
      var driveItem = target.driveItem;
      if (!driveItem || driveItem.driveFolder) {
        return;
      }

      var fileId = extractDriveItemId_(driveItem.name);
      var activityTime = getActionTime_(action, activity);
      if (!fileId || !activityTime) {
        return;
      }

      records.push({
        uploader: formatDriveActor_(action.actor),
        title: driveItem.title || '',
        mimeType: driveItem.mimeType || '',
        fileId: fileId,
        uploadAt: activityTime,
        activityKey: buildUploadActivityKey_(fileId, activityTime)
      });
    });
  });

  return deduplicateUploadRecords_(records, {});
}

/**
 * 補齊 Action 省略的共用操作者、目標與動作資訊。
 *
 * Drive Activity 會把共用欄位只放在整體活動，個別 Action 可能留空。
 *
 * @param {Object} activity Drive 活動。
 * @return {Object[]} 可獨立判讀的 Action。
 */
function resolveActivityActions_(activity) {
  var actions = activity.actions || [];
  if (actions.length === 0) {
    return buildFallbackActions_(activity);
  }

  var actors = activity.actors || [];
  var targets = activity.targets || [];

  return actions.map(function (action, index) {
    return {
      detail: action.detail || activity.primaryActionDetail || {},
      actor: action.actor || actors[index] || actors[0] || {},
      target: action.target || targets[index] || targets[0] || {},
      timestamp: action.timestamp,
      timeRange: action.timeRange
    };
  });
}

/**
 * 在個別 Action 缺少時，從活動最上層欄位建立可判讀的替代項目。
 *
 * @param {Object} activity Drive 活動。
 * @return {Object[]} 替代 Action。
 */
function buildFallbackActions_(activity) {
  var actions = [];
  var actors = activity.actors || [{}];
  var targets = activity.targets || [];

  targets.forEach(function (target, index) {
    actions.push({
      detail: activity.primaryActionDetail || {},
      actor: actors[index] || actors[0] || {},
      target: target,
      timestamp: activity.timestamp,
      timeRange: activity.timeRange
    });
  });

  return actions;
}

/**
 * 判斷是否為外部上傳，而不是新建、複製或移動。
 *
 * @param {Object} detail ActionDetail。
 * @return {boolean} 是否為外部上傳。
 */
function isExternalUploadAction_(detail) {
  var create = detail && detail.create;
  return Boolean(
    create &&
      Object.prototype.hasOwnProperty.call(create, 'upload')
  );
}

/**
 * 取得 Action 或整體活動的發生時間。
 *
 * @param {Object} action 個別 Action。
 * @param {Object} activity 整體活動。
 * @return {string} RFC 3339 時間。
 */
function getActionTime_(action, activity) {
  if (action.timestamp) {
    return action.timestamp;
  }
  if (action.timeRange && action.timeRange.endTime) {
    return action.timeRange.endTime;
  }
  if (activity.timestamp) {
    return activity.timestamp;
  }
  if (activity.timeRange && activity.timeRange.endTime) {
    return activity.timeRange.endTime;
  }
  return '';
}

/**
 * 依 Drive Activity 可提供的資訊顯示上傳者，不猜測姓名或 Email。
 *
 * @param {Object} actor Drive Activity Actor。
 * @return {string} 適合寫入私人試算表的身分文字。
 */
function formatDriveActor_(actor) {
  if (!actor) {
    return '無法辨識';
  }

  if (actor.user && actor.user.knownUser) {
    var knownUser = actor.user.knownUser;
    if (knownUser.isCurrentUser) {
      return '目前登入帳號';
    }
    if (knownUser.personName) {
      return '已辨識使用者（' + knownUser.personName + '）';
    }
  }

  if (actor.anonymous) {
    return '匿名使用者';
  }
  if (actor.system) {
    return 'Google 系統';
  }
  if (actor.administrator) {
    return '系統管理員';
  }
  return '無法辨識';
}

/**
 * 從 items/FILE_ID 取出 ID。
 *
 * @param {string} itemName Drive Activity item name。
 * @return {string} 檔案 ID。
 */
function extractDriveItemId_(itemName) {
  var match = String(itemName || '').match(/^items\/(.+)$/);
  return match ? match[1] : '';
}

/**
 * 讀取 Drive 檔案並排除子資料夾、垃圾桶或無法開啟的項目。
 *
 * @param {Object[]} candidates 候選活動。
 * @param {string} folderId 指定資料夾 ID。
 * @param {Date} detectedAt 偵測時間。
 * @return {Object[]} 可寫入的紀錄。
 */
function enrichAndFilterDirectUploads_(candidates, folderId, detectedAt) {
  var results = [];

  candidates.forEach(function (candidate) {
    try {
      var file = DriveApp.getFileById(candidate.fileId);
      if (file.isTrashed() || !hasDirectParent_(file, folderId)) {
        return;
      }

      var mimeType = candidate.mimeType || file.getMimeType();
      results.push({
        uploader: candidate.uploader,
        title: candidate.title || file.getName(),
        readableType: getReadableFileType_(mimeType),
        mimeType: mimeType,
        uploadAt: new Date(candidate.uploadAt),
        detectedAt: new Date(detectedAt.getTime()),
        url: file.getUrl(),
        fileId: candidate.fileId,
        status: '已記錄',
        activityKey: candidate.activityKey
      });
    } catch (error) {
      logWarning_('略過', '有 1 筆候選活動的檔案已無法開啟');
    }
  });

  return results;
}

/**
 * 判斷檔案目前是否直接位於指定資料夾。
 *
 * @param {GoogleAppsScript.Drive.File} file Drive 檔案。
 * @param {string} folderId 指定資料夾 ID。
 * @return {boolean} 是否為直接子項目。
 */
function hasDirectParent_(file, folderId) {
  var parents = file.getParents();
  while (parents.hasNext()) {
    if (parents.next().getId() === folderId) {
      return true;
    }
  }
  return false;
}

/**
 * 將 MIME type 轉成容易閱讀的中文類型。
 *
 * @param {string} mimeType MIME type。
 * @return {string} 中文檔案類型。
 */
function getReadableFileType_(mimeType) {
  var type = String(mimeType || '').toLowerCase();
  var exactMatches = {
    'application/pdf': 'PDF',
    'application/zip': '壓縮檔',
    'application/vnd.google-apps.document': 'Google 文件',
    'application/vnd.google-apps.spreadsheet': 'Google 試算表',
    'application/vnd.google-apps.presentation': 'Google 簡報',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
      'Word 文件',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
      'Excel 試算表',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation':
      'PowerPoint 簡報'
  };

  if (exactMatches[type]) {
    return exactMatches[type];
  }
  if (type.indexOf('image/') === 0) {
    return '圖片';
  }
  if (type.indexOf('video/') === 0) {
    return '影片';
  }
  if (type.indexOf('audio/') === 0) {
    return '音訊';
  }
  if (type.indexOf('text/') === 0) {
    return '文字檔';
  }
  return '其他';
}

/**
 * 追加尚未出現的紀錄，不重設欄寬。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 紀錄工作表。
 * @param {Object[]} records 待寫入紀錄。
 * @return {number} 實際新增筆數。
 */
function appendUniqueUploadRecords_(sheet, records) {
  var existingKeys = readExistingActivityKeys_(sheet);
  var uniqueRecords = deduplicateUploadRecords_(records, existingKeys);

  if (uniqueRecords.length === 0) {
    return 0;
  }

  var rows = uniqueRecords.map(function (record) {
    return [
      record.uploader,
      record.title,
      record.readableType,
      record.mimeType,
      record.uploadAt,
      record.detectedAt,
      record.url,
      record.fileId,
      record.status,
      record.activityKey
    ];
  });

  var startRow = findNextDataRow_(sheet);
  sheet.getRange(startRow, 1, rows.length, rows[0].length).setValues(rows);
  sheet.getRange(startRow, 5, rows.length, 2).setNumberFormat(
    'yyyy/mm/dd hh:mm:ss'
  );
  return rows.length;
}

/**
 * 讀取已存在的活動識別。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 紀錄工作表。
 * @return {Object<string, boolean>} 已存在集合。
 */
function readExistingActivityKeys_(sheet) {
  var existing = {};
  var lastRow = findLastRealDataRow_(sheet);
  if (lastRow < 2) {
    return existing;
  }

  sheet
    .getRange(2, 10, lastRow - 1, 1)
    .getDisplayValues()
    .forEach(function (row) {
      var key = String(row[0] || '').trim();
      if (key) {
        existing[key] = true;
      }
    });
  return existing;
}

/**
 * 依活動識別去除重複項目。
 *
 * @param {Object[]} records 紀錄。
 * @param {Object<string, boolean>} existingKeys 已存在集合。
 * @return {Object[]} 未重複紀錄。
 */
function deduplicateUploadRecords_(records, existingKeys) {
  var seen = Object.assign({}, existingKeys || {});
  return (records || []).filter(function (record) {
    var key = String(record.activityKey || '');
    if (!key || seen[key]) {
      return false;
    }
    seen[key] = true;
    return true;
  });
}

/**
 * 產生活動識別。
 *
 * @param {string} fileId 檔案 ID。
 * @param {string} uploadAt 活動時間。
 * @return {string} 活動識別。
 */
function buildUploadActivityKey_(fileId, uploadAt) {
  return String(fileId || '') + '|' + String(uploadAt || '');
}

/**
 * 用實際資料欄判斷最後一列，避免空白控制欄干擾。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 工作表。
 * @return {number} 最後一筆真實資料列。
 */
function findLastRealDataRow_(sheet) {
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    return 1;
  }

  var values = sheet.getRange(2, 1, lastRow - 1, 10).getDisplayValues();
  for (var index = values.length - 1; index >= 0; index -= 1) {
    if (values[index].some(function (value) {
      return String(value || '').trim() !== '';
    })) {
      return index + 2;
    }
  }
  return 1;
}

/**
 * 取得下一個可寫入資料列。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 工作表。
 * @return {number} 下一列。
 */
function findNextDataRow_(sheet) {
  return Math.max(2, findLastRealDataRow_(sheet) + 1);
}

/**
 * 保留查詢重疊區間，並且不早於初始化基準。
 *
 * @param {string} baseline 初始化時間。
 * @param {string} lastCheck 最近檢查時間。
 * @return {string} RFC 3339 查詢起點。
 */
function buildQueryStartTime_(baseline, lastCheck) {
  var baselineTime = new Date(baseline).getTime();
  var lastCheckTime = new Date(lastCheck).getTime();

  if (!isFinite(baselineTime) || !isFinite(lastCheckTime)) {
    throw new Error('檢查時間設定格式不正確，請重新初始化檢查起點。');
  }

  var overlap =
    lastCheckTime - UPLOAD_LOGGER_CONFIG_.queryOverlapMinutes * 60 * 1000;
  return new Date(Math.max(baselineTime, overlap)).toISOString();
}
