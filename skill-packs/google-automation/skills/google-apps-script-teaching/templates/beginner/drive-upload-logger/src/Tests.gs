/**
 * 驗收只有外部上傳會被辨識。
 */
function testDriveUploadNormal() {
  logInfo_('開始', '準備執行檔案上傳正常測試');

  try {
    var time = '2026-07-29T01:00:00Z';
    var activities = [
      buildMockDriveActivity_('file-upload', time, {
        upload: {}
      }),
      buildMockDriveActivity_('file-new', time, {
        new: {}
      }),
      buildMockDriveActivity_('file-copy', time, {
        copy: {}
      }),
      buildMockTopLevelDriveActivity_('file-top-level', time)
    ];
    var records = extractUploadRecordsFromActivities_(activities);

    assertUploadTest_(records.length === 2, '應辨識 2 筆外部上傳');
    assertUploadTest_(
      records[0].fileId === 'file-upload',
      '應保留外部上傳的檔案 ID'
    );
    assertUploadTest_(
      records[0].uploader === '目前登入帳號',
      '應正確標示目前登入帳號'
    );
    assertUploadTest_(
      records[1].fileId === 'file-top-level',
      'Action 省略共用欄位時仍應辨識上傳'
    );
    assertUploadTest_(
      getReadableFileType_('application/pdf') === 'PDF',
      'PDF 類型轉換錯誤'
    );

    logInfo_('成功', '正常測試通過｜外部上傳=2｜新建與複製已略過');
  } catch (error) {
    throw logAndBuildError_('正常測試失敗', error);
  }
}

/**
 * 驗收缺少設定、格式錯誤與非上傳事件都會被拒絕。
 */
function testDriveUploadErrors() {
  logInfo_('開始', '準備執行檔案上傳錯誤測試');

  try {
    assertThrowsUploadTest_(
      function () {
        validateDriveUploadSettings_({
          folderId: '',
          spreadsheetId: 'A2345678901234567890'
        });
      },
      'WATCH_FOLDER_ID'
    );
    assertThrowsUploadTest_(
      function () {
        validateDriveUploadSettings_({
          folderId: 'A2345678901234567890',
          spreadsheetId: ''
        });
      },
      'LOG_SPREADSHEET_ID'
    );
    assertThrowsUploadTest_(
      function () {
        validateDriveUploadSettings_({
          folderId: '不是正確格式',
          spreadsheetId: 'A2345678901234567890'
        });
      },
      '格式不正確'
    );
    assertUploadTest_(
      isExternalUploadAction_({ create: { new: {} } }) === false,
      '新建空白 Google 檔案不應視為上傳'
    );
    assertUploadTest_(
      isExternalUploadAction_({ move: {} }) === false,
      '移入既有 Drive 檔案不應視為上傳'
    );
    var triggerStartedAt = new Date('2026-07-29T01:00:00Z');
    assertUploadTest_(
      calculateUploadTriggerExpiresAt_(triggerStartedAt).toISOString() ===
        '2026-07-29T01:10:00.000Z',
      '教學觸發器應在 10 分鐘後到期'
    );
    assertUploadTest_(
      buildUploadTriggerStatus_(
        1,
        '2026-07-29T01:10:00Z',
        new Date('2026-07-29T01:10:00Z')
      ).state === 'expired',
      '到期的教學觸發器應停止背景檢查'
    );

    logInfo_(
      '成功',
      '錯誤測試通過｜缺少設定、非上傳事件與到期觸發器均被拒絕'
    );
  } catch (error) {
    throw logAndBuildError_('錯誤測試失敗', error);
  }
}

/**
 * 驗收重複活動不會寫入兩次，且日常更新保留欄寬。
 */
function testDriveUploadRepeat() {
  logInfo_('開始', '準備執行檔案上傳重複測試');

  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var testSheetName = '__測試_檔案上傳重複';
  var existing = spreadsheet.getSheetByName(testSheetName);
  if (existing) {
    spreadsheet.deleteSheet(existing);
  }
  var sheet = spreadsheet.insertSheet(testSheetName);

  try {
    sheet
      .getRange(1, 1, 1, 10)
      .setValues([[
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
      ]]);
    sheet.setColumnWidth(2, 333);

    var record = {
      uploader: '測試使用者',
      title: '教學測試檔案.pdf',
      readableType: 'PDF',
      mimeType: 'application/pdf',
      uploadAt: new Date('2026-07-29T01:00:00Z'),
      detectedAt: new Date('2026-07-29T01:01:00Z'),
      url: 'https://example.com/test-file',
      fileId: 'test-file-id',
      status: '已記錄',
      activityKey: 'test-file-id|2026-07-29T01:00:00Z'
    };

    var firstWritten = appendUniqueUploadRecords_(sheet, [record]);
    var secondWritten = appendUniqueUploadRecords_(sheet, [record]);

    assertUploadTest_(firstWritten === 1, '第一次應寫入 1 筆');
    assertUploadTest_(secondWritten === 0, '第二次不應重複寫入');
    assertUploadTest_(findLastRealDataRow_(sheet) === 2, '結果應只有 1 筆資料');
    assertUploadTest_(sheet.getColumnWidth(2) === 333, '日常更新應保留欄寬');

    logInfo_('成功', '重複測試通過｜只保留 1 筆｜欄寬保留');
  } catch (error) {
    throw logAndBuildError_('重複測試失敗', error);
  } finally {
    spreadsheet.deleteSheet(sheet);
  }
}

/**
 * 建立 Drive Activity 測試替身。
 *
 * @param {string} fileId 測試檔案 ID。
 * @param {string} timestamp 活動時間。
 * @param {Object} createOrigin create 的來源。
 * @return {Object} 測試活動。
 */
function buildMockDriveActivity_(fileId, timestamp, createOrigin) {
  return {
    actions: [
      {
        detail: {
          create: createOrigin
        },
        actor: {
          user: {
            knownUser: {
              isCurrentUser: true
            }
          }
        },
        target: {
          driveItem: {
            name: 'items/' + fileId,
            title: '教學測試檔案',
            mimeType: 'application/pdf',
            driveFile: {}
          }
        },
        timestamp: timestamp
      }
    ]
  };
}

/**
 * 建立 Action 省略共用欄位的 Drive Activity 測試替身。
 *
 * @param {string} fileId 測試檔案 ID。
 * @param {string} timestamp 活動時間。
 * @return {Object} 測試活動。
 */
function buildMockTopLevelDriveActivity_(fileId, timestamp) {
  return {
    primaryActionDetail: {
      create: {
        upload: {}
      }
    },
    actors: [
      {
        user: {
          knownUser: {
            isCurrentUser: true
          }
        }
      }
    ],
    targets: [
      {
        driveItem: {
          name: 'items/' + fileId,
          title: '整體活動教學測試檔案',
          mimeType: 'application/pdf',
          driveFile: {}
        }
      }
    ],
    timestamp: timestamp,
    actions: [
      {
        detail: {
          create: {
            upload: {}
          }
        }
      }
    ]
  };
}

/**
 * 簡易測試斷言。
 *
 * @param {boolean} condition 是否通過。
 * @param {string} message 失敗訊息。
 */
function assertUploadTest_(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

/**
 * 驗證函式會拋出包含指定文字的錯誤。
 *
 * @param {Function} callback 測試動作。
 * @param {string} expectedText 預期錯誤文字。
 */
function assertThrowsUploadTest_(callback, expectedText) {
  var thrown = false;
  try {
    callback();
  } catch (error) {
    thrown = String(error.message || error).indexOf(expectedText) >= 0;
  }
  if (!thrown) {
    throw new Error('預期出現錯誤文字：' + expectedText);
  }
}
