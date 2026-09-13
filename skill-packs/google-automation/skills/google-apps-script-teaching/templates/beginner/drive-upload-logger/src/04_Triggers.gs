/**
 * 經使用者確認後，建立教學用每分鐘時間觸發器。
 *
 * 重複執行只會延長同一個觸發器的教學期限，不會建立第二個。
 */
function setupUploadCheckTrigger() {
  logInfo_('開始', '準備啟用教學用每分鐘自動檢查');

  try {
    readDriveUploadSettings_();
    var properties = PropertiesService.getScriptProperties();
    if (
      !properties.getProperty(UPLOAD_LOGGER_CONFIG_.baselineProperty) ||
      !properties.getProperty(UPLOAD_LOGGER_CONFIG_.lastCheckProperty)
    ) {
      throw new Error(
        '尚未初始化檢查起點，請先從「上傳工具」選擇「初始化檢查起點」。'
      );
    }

    var existing = getUploadCheckTriggers_();

    if (existing.length > 1) {
      throw new Error(
        '發現重複的檔案上傳定時觸發器，請先使用「停止自動檢查」。'
      );
    }

    var expiresAt = calculateUploadTriggerExpiresAt_(new Date());

    if (
      existing.length === 1 &&
      existing[0].getHandlerFunction() ===
        UPLOAD_LOGGER_CONFIG_.triggerFunctionName
    ) {
      properties.setProperty(
        UPLOAD_LOGGER_CONFIG_.triggerExpiresAtProperty,
        expiresAt.toISOString()
      );
      logInfo_('略過', '每分鐘觸發器已存在，沒有重複建立');
      logInfo_('成功', '已重新開始 10 分鐘教學期限');
      showUploadTriggerToast_(
        '每分鐘檢查已重新計時。完成驗證後請選擇「停止自動檢查」。'
      );
      return;
    }

    if (existing.length === 1) {
      ScriptApp.deleteTrigger(existing[0]);
      logInfo_('進度', '已移除舊版定時觸發器');
    }

    var createdTrigger = ScriptApp.newTrigger(
      UPLOAD_LOGGER_CONFIG_.triggerFunctionName
    )
      .timeBased()
      .everyMinutes(UPLOAD_LOGGER_CONFIG_.triggerIntervalMinutes)
      .create();

    try {
      properties.setProperty(
        UPLOAD_LOGGER_CONFIG_.triggerExpiresAtProperty,
        expiresAt.toISOString()
      );
    } catch (propertyError) {
      // 安全期限保存失敗時回收剛建立的觸發器，避免無期限執行。
      ScriptApp.deleteTrigger(createdTrigger);
      throw propertyError;
    }

    logInfo_('成功', '已啟用每分鐘檢查，約 10 分鐘後會自動停止');
    logWarning_('警告', '完成教學驗證後，請立即選擇「停止自動檢查」');
    showUploadTriggerToast_(
      '教學模式已啟用。每分鐘檢查，約 10 分鐘後自動停止；驗證後仍請立即關閉。'
    );
  } catch (error) {
    throw logAndBuildError_('啟用每分鐘自動檢查失敗', error);
  }
}

/**
 * 由時間觸發器呼叫的背景入口。
 *
 * @param {Object} event Apps Script 時間觸發事件。
 */
function runUploadCheckByTimer(event) {
  logInfo_('開始', '教學用每分鐘自動檢查已啟動');

  try {
    if (!event || !event.triggerUid) {
      throw new Error(
        '這個函式只供背景觸發器使用，請改用試算表的「上傳工具」。'
      );
    }

    var properties = PropertiesService.getScriptProperties();
    var expiresAtValue = properties.getProperty(
      UPLOAD_LOGGER_CONFIG_.triggerExpiresAtProperty
    );
    var status = buildUploadTriggerStatus_(
      getUploadCheckTriggers_().length,
      expiresAtValue,
      new Date()
    );

    if (status.state !== 'active') {
      var removed = deleteUploadCheckTriggers_();
      properties.deleteProperty(
        UPLOAD_LOGGER_CONFIG_.triggerExpiresAtProperty
      );
      logWarning_(
        '警告',
        status.state === 'expired'
          ? '10 分鐘教學期限已到，正在自動停止'
          : '找不到有效的安全期限，為避免持續耗用額度已自動停止'
      );
      logInfo_('成功', '已自動移除 ' + removed + ' 個教學觸發器');
      return;
    }

    checkNewDriveUploads();

    // 若本次查詢跨過安全期限，完成寫入後便立即停止。
    if (new Date().getTime() >= status.expiresAt.getTime()) {
      var removedAfterCheck = deleteUploadCheckTriggers_();
      properties.deleteProperty(
        UPLOAD_LOGGER_CONFIG_.triggerExpiresAtProperty
      );
      logInfo_(
        '成功',
        '本次檢查完成且教學期限已到，已移除 ' +
          removedAfterCheck +
          ' 個觸發器'
      );
    }
  } catch (error) {
    throw logAndBuildError_('每分鐘自動檢查失敗', error);
  }
}

/**
 * 檢查時間觸發器是否存在、沒有重複且仍在安全期限內。
 */
function checkUploadCheckTrigger() {
  logInfo_('開始', '準備查看檔案上傳自動檢查狀態');

  try {
    var triggers = getUploadCheckTriggers_();
    var properties = PropertiesService.getScriptProperties();
    var status = buildUploadTriggerStatus_(
      triggers.length,
      properties.getProperty(
        UPLOAD_LOGGER_CONFIG_.triggerExpiresAtProperty
      ),
      new Date()
    );

    if (status.state === 'inactive') {
      logInfo_('成功', '自動檢查目前為關閉狀態');
      showUploadTriggerToast_('自動檢查目前為關閉狀態。');
      return;
    }

    if (status.state === 'duplicate') {
      throw new Error('發現重複的檔案上傳定時觸發器，請先人工檢查。');
    }

    if (status.state === 'unsafe') {
      logWarning_('警告', '觸發器沒有有效的 10 分鐘安全期限');
      showUploadTriggerToast_(
        '安全期限遺失，請立即選擇「停止自動檢查」。'
      );
      return;
    }

    if (status.state === 'expired') {
      logWarning_('警告', '10 分鐘期限已到，下次背景執行會自動停止');
      showUploadTriggerToast_(
        '教學期限已到，請選擇「停止自動檢查」。'
      );
      return;
    }

    logInfo_(
      '成功',
      '每分鐘自動檢查執行中，安全期限約剩 ' +
        status.remainingMinutes +
        ' 分鐘'
    );
    showUploadTriggerToast_(
      '每分鐘自動檢查執行中，約剩 ' +
        status.remainingMinutes +
        ' 分鐘。'
    );
  } catch (error) {
    throw logAndBuildError_('查看自動檢查狀態失敗', error);
  }
}

/**
 * 移除本案例的自動檢查觸發器與安全期限。
 */
function removeUploadCheckTrigger() {
  logInfo_('開始', '準備停止檔案上傳自動檢查');

  try {
    var removed = deleteUploadCheckTriggers_();
    PropertiesService.getScriptProperties().deleteProperty(
      UPLOAD_LOGGER_CONFIG_.triggerExpiresAtProperty
    );
    logInfo_('成功', '自動檢查已關閉，共移除 ' + removed + ' 個觸發器');
    showUploadTriggerToast_('自動檢查已關閉。');
  } catch (error) {
    throw logAndBuildError_('停止自動檢查失敗', error);
  }
}

/**
 * 計算教學觸發器的安全期限。
 *
 * @param {Date} startedAt 啟用時間。
 * @return {Date} 安全期限。
 */
function calculateUploadTriggerExpiresAt_(startedAt) {
  return new Date(
    startedAt.getTime() +
      UPLOAD_LOGGER_CONFIG_.triggerDurationMinutes * 60 * 1000
  );
}

/**
 * 整理觸發器狀態，讓 Agent 可在不建立真實觸發器時完成測試。
 *
 * @param {number} triggerCount 相符觸發器數量。
 * @param {string} expiresAtValue 指令碼屬性中的安全期限。
 * @param {Date} now 判斷時間。
 * @return {{
 *   state: string,
 *   expiresAt: Date|null,
 *   remainingMinutes: number
 * }} 狀態摘要。
 */
function buildUploadTriggerStatus_(triggerCount, expiresAtValue, now) {
  if (triggerCount === 0) {
    return {
      state: 'inactive',
      expiresAt: null,
      remainingMinutes: 0
    };
  }

  if (triggerCount > 1) {
    return {
      state: 'duplicate',
      expiresAt: null,
      remainingMinutes: 0
    };
  }

  var expiresAt = new Date(String(expiresAtValue || ''));
  if (!isFinite(expiresAt.getTime())) {
    return {
      state: 'unsafe',
      expiresAt: null,
      remainingMinutes: 0
    };
  }

  var remainingMilliseconds = expiresAt.getTime() - now.getTime();
  if (remainingMilliseconds <= 0) {
    return {
      state: 'expired',
      expiresAt: expiresAt,
      remainingMinutes: 0
    };
  }

  return {
    state: 'active',
    expiresAt: expiresAt,
    remainingMinutes: Math.ceil(remainingMilliseconds / 60000)
  };
}

/**
 * 找出本案例目前及舊版使用的時間觸發器。
 *
 * @return {GoogleAppsScript.Script.Trigger[]} 相符觸發器。
 */
function getUploadCheckTriggers_() {
  var handlerNames = [
    UPLOAD_LOGGER_CONFIG_.triggerFunctionName,
    UPLOAD_LOGGER_CONFIG_.legacyTriggerFunctionName
  ];

  return ScriptApp.getProjectTriggers().filter(function (trigger) {
    return (
      handlerNames.indexOf(trigger.getHandlerFunction()) >= 0 &&
      trigger.getEventType() === ScriptApp.EventType.CLOCK
    );
  });
}

/**
 * 移除本案例目前及舊版使用的全部時間觸發器。
 *
 * @return {number} 移除數量。
 */
function deleteUploadCheckTriggers_() {
  var triggers = getUploadCheckTriggers_();
  triggers.forEach(function (trigger) {
    ScriptApp.deleteTrigger(trigger);
  });
  return triggers.length;
}

/**
 * 舊版觸發器意外執行時，只移除舊版入口。
 */
function stopLegacyUploadCheckTrigger_() {
  ScriptApp.getProjectTriggers()
    .filter(function (trigger) {
      return (
        trigger.getHandlerFunction() ===
          UPLOAD_LOGGER_CONFIG_.legacyTriggerFunctionName &&
        trigger.getEventType() === ScriptApp.EventType.CLOCK
      );
    })
    .forEach(function (trigger) {
      ScriptApp.deleteTrigger(trigger);
    });
}

/**
 * 在試算表右下角顯示不含私人資料的操作結果。
 *
 * @param {string} message 顯示訊息。
 */
function showUploadTriggerToast_(message) {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  if (spreadsheet) {
    spreadsheet.toast(message, '上傳工具', 8);
  }
}
