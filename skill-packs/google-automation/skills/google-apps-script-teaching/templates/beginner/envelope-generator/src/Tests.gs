/**
 * 正常測試：準備五筆假資料並依目前設定產生五頁信封文件。
 */
function testEnvelopeNormal() {
  logEnvelope_('開始', '準備執行批次信封正常測試');

  try {
    setupEnvelopeGenerator();
    ensureEnvelopeTestFixtures_();
    var result = generateEnvelopeDocuments();
    if (result.pageCount !== ENVELOPE_CONFIG_.normalTestPageCount) {
      throw new Error(
        '正常測試預期產生 ' + ENVELOPE_CONFIG_.normalTestPageCount + ' 頁信封。'
      );
    }
    logEnvelope_(
      '成功',
      '正常測試通過｜信封頁數=' + ENVELOPE_CONFIG_.normalTestPageCount
    );
  } catch (error) {
    logEnvelopeError_('正常測試失敗｜原因：' + error.message);
    throw error;
  }
}

/**
 * 橫式測試：暫時切換為橫式，產生五頁後恢復原本設定。
 */
function testEnvelopeLandscape() {
  logEnvelope_('開始', '準備執行批次信封橫式版面測試');

  var orientationCell = null;
  var originalOrientation = '';
  try {
    setupEnvelopeGenerator();
    ensureEnvelopeTestFixtures_();
    var spreadsheet = openEnvelopeSpreadsheet_();
    var senderSheet = spreadsheet.getSheetByName(
      ENVELOPE_CONFIG_.senderSheetName
    );
    if (!senderSheet) {
      throw new Error('找不到寄件人設定工作表。');
    }

    orientationCell = senderSheet.getRange('B4');
    originalOrientation = String(orientationCell.getValue() || '').trim();
    orientationCell.setValue('橫式');

    var result = generateEnvelopeDocuments();
    if (result.pageCount !== ENVELOPE_CONFIG_.normalTestPageCount) {
      throw new Error(
        '橫式測試預期產生 ' +
          ENVELOPE_CONFIG_.normalTestPageCount +
          ' 頁信封。'
      );
    }
    checkLandscapeEnvelopeFontSizes_(result.documentId);
    logEnvelope_(
      '成功',
      '橫式測試通過｜信封頁數=' +
        ENVELOPE_CONFIG_.normalTestPageCount +
        '｜寄件字體=24｜收件字體=28'
    );
  } catch (error) {
    logEnvelopeError_('橫式測試失敗｜原因：' + error.message);
    throw error;
  } finally {
    if (orientationCell) {
      // 測試只暫時切換方向，不永久改寫使用者原本設定。
      orientationCell.setValue(originalOrientation || '直式');
      logEnvelope_('進度', '已恢復原本的版面方向設定');
    }
  }
}

/**
 * 讀回實際 Google Docs，確認多行儲存格的每個可見字都套到指定字體。
 *
 * @param {string} documentId 輸出文件 ID。
 */
function checkLandscapeEnvelopeFontSizes_(documentId) {
  var outputDocument = DocumentApp.openById(documentId);
  try {
    var tables = outputDocument.getBody().getTables();
    if (tables.length === 0) {
      throw new Error('橫式文件沒有可檢查的信封表格。');
    }
    assertEnvelopeCellFontSize_(tables[0].getCell(0, 0), 24, '寄件資料');
    assertEnvelopeCellFontSize_(tables[0].getCell(1, 1), 28, '收件資料');
  } finally {
    outputDocument.saveAndClose();
  }
}

/**
 * 檢查儲存格內所有非空白字元的實際字體大小。
 *
 * @param {GoogleAppsScript.Document.TableCell} cell 待檢查儲存格。
 * @param {number} expectedSize 預期字體大小。
 * @param {string} label 紀錄檔(Log)使用的區塊名稱。
 */
function assertEnvelopeCellFontSize_(cell, expectedSize, label) {
  var text = cell.editAsText();
  var value = text.getText();
  for (var index = 0; index < value.length; index += 1) {
    if (/\s/.test(value.charAt(index))) {
      continue;
    }
    if (text.getFontSize(index) !== expectedSize) {
      throw new Error(label + '仍有文字不是 ' + expectedSize + ' 字。');
    }
  }
}

/**
 * 錯誤測試：缺少收件地址時不得建立或更新文件。
 */
function testEnvelopeInvalidAddress() {
  logEnvelope_('開始', '準備執行缺少收件地址錯誤測試');

  try {
    normalizeEnvelopeData_(
      [
        ['寄件人名稱', '教學寄件人'],
        ['寄件人地址', '教學測試地址'],
        ['版面方向', '直式']
      ],
      [[true, '教學收件人', '', '只在記憶體測試']]
    );
  } catch (error) {
    if (error.message.indexOf('沒有可產生的有效收件人') !== -1) {
      logEnvelope_('成功', '錯誤測試通過｜缺少地址的資料已在建立文件前被拒絕');
      return;
    }
    logEnvelopeError_('錯誤測試收到非預期結果｜原因：' + error.message);
    throw error;
  }

  var unexpectedError = new Error('錯誤測試失敗：缺少地址的資料沒有被拒絕。');
  logEnvelopeError_(unexpectedError.message);
  throw unexpectedError;
}

/**
 * 方向測試：確認頁面方向、郵遞區號與直排資料都符合預期。
 */
function testEnvelopeDirections() {
  logEnvelope_('開始', '準備執行信封版面方向測試');

  try {
    var portrait = resolveEnvelopePageSize_('直式');
    var landscape = resolveEnvelopePageSize_('橫式');
    var postalAddress = parseEnvelopePostalAddress_(
      '110204 臺北市信義區市府路1號'
    );
    var portraitLayout = resolvePortraitEnvelopeLayout_();
    var landscapeLayout = resolveLandscapeEnvelopeLayout_();
    if (
      portrait.width >= portrait.height ||
      landscape.width <= landscape.height ||
      portrait.width !== landscape.height ||
      portrait.height !== landscape.width
    ) {
      throw new Error('直式與橫式頁面尺寸不符合預期。');
    }
    if (
      postalAddress.postalCode !== '110204' ||
      postalAddress.address !== '臺北市信義區市府路1號' ||
      formatEnvelopePostalCode_(postalAddress.postalCode) !== '110‑204'
    ) {
      throw new Error('郵遞區號沒有從地址正確拆出。');
    }
    if (normalizeVerticalEnvelopeText_('臺 北\n1號') !== '臺北1號') {
      throw new Error('直排資料仍包含會干擾自然折行的空白或換行。');
    }
    var portraitWidth = portraitLayout.columnWidths.reduce(function (sum, width) {
      return sum + width;
    }, 0);
    var portraitHeight = portraitLayout.rowHeights.reduce(function (sum, height) {
      return sum + height;
    }, 0);
    if (
      portraitWidth !== 500 ||
      portraitHeight > portraitLayout.safeHeight
    ) {
      throw new Error('直式信封尺寸超出單頁安全範圍。');
    }
    var landscapeWidth = landscapeLayout.columnWidths.reduce(function (
      sum,
      width
    ) {
      return sum + width;
    }, 0);
    var landscapeHeight = landscapeLayout.rowHeights.reduce(function (
      sum,
      height
    ) {
      return sum + height;
    }, 0);
    if (
      landscapeWidth !== 750 ||
      landscapeHeight > landscapeLayout.safeHeight
    ) {
      throw new Error('橫式信封尺寸超出單頁安全範圍。');
    }
    var landscapeAddress = splitLandscapeEnvelopeAddress_(
      '臺中市西屯區臺灣大道三段99號'
    );
    if (
      landscapeAddress.length !== 2 ||
      landscapeAddress[0] !== '臺中市西屯區' ||
      landscapeAddress[1] !== '臺灣大道三段99號'
    ) {
      throw new Error('橫式地址沒有依行政區與門牌正確分行。');
    }
    logEnvelope_(
      '成功',
      '方向測試通過｜直式定稿、橫式分行與兩種單頁尺寸皆符合預期'
    );
  } catch (error) {
    logEnvelopeError_('方向測試失敗｜原因：' + error.message);
    throw error;
  }
}

/**
 * 重複執行測試：兩次產生都必須沿用同一份 Google Docs。
 */
function testEnvelopeRepeat() {
  logEnvelope_('開始', '準備執行批次信封重複測試');

  try {
    setupEnvelopeGenerator();
    ensureEnvelopeTestFixtures_();
    var first = generateEnvelopeDocuments();
    var second = generateEnvelopeDocuments();
    if (first.documentId !== second.documentId) {
      throw new Error('重複執行建立了不同文件，預期沿用同一份 Google Docs。');
    }
    logEnvelope_(
      '成功',
      '重複測試通過｜兩次執行沿用同一份 ' +
        ENVELOPE_CONFIG_.normalTestPageCount +
        ' 頁信封文件'
    );
  } catch (error) {
    logEnvelopeError_('重複測試失敗｜原因：' + error.message);
    throw error;
  }
}

/**
 * 寫入固定教學假資料；已存在時安全略過。
 */
function ensureEnvelopeTestFixtures_() {
  var spreadsheet = openEnvelopeSpreadsheet_();
  var senderSheet = spreadsheet.getSheetByName(ENVELOPE_CONFIG_.senderSheetName);
  var recipientSheet = spreadsheet.getSheetByName(ENVELOPE_CONFIG_.recipientSheetName);
  if (!senderSheet || !recipientSheet) {
    throw new Error('找不到必要工作表，請先執行 setupEnvelopeGenerator。');
  }

  var senderValues = senderSheet.getRange(2, 2, 3, 1).getValues();
  if (String(senderValues[0][0] || '').trim() === '') {
    senderSheet.getRange('B2').setValue('教學寄件人');
  }
  var currentSenderAddress = String(senderValues[1][0] || '').trim();
  if (
    currentSenderAddress === '' ||
    currentSenderAddress === '台北市教學路 1 號'
  ) {
    // 只遷移舊版固定教學地址；使用者自行修改的寄件地址保持不變。
    senderSheet
      .getRange('B3')
      .setValue('100001 臺北市中正區測試路一段1號');
  }
  if (String(senderValues[2][0] || '').trim() === '') {
    senderSheet.getRange('B4').setValue('直式');
  }

  var fixtures = [
    [
      true,
      '臺北市政府',
      '110204 臺北市信義區市府路1號',
      ENVELOPE_CONFIG_.fixtureNote + '｜虛構收件人：林予晴'
    ],
    [
      true,
      '新北市政府資訊中心',
      '220242 新北市板橋區中山路1段161號16樓',
      ENVELOPE_CONFIG_.fixtureNote + '｜虛構收件人：陳宇禾'
    ],
    [
      true,
      '桃園市政府',
      '330206 桃園市桃園區縣府路1號',
      ENVELOPE_CONFIG_.fixtureNote + '｜虛構收件人：張庭安'
    ],
    [
      true,
      '臺中市政府法制局',
      '407610 臺中市西屯區臺灣大道三段99號文心樓10樓',
      ENVELOPE_CONFIG_.fixtureNote + '｜虛構收件人：王品澄'
    ],
    [
      true,
      '高雄市政府人事處',
      '802721 高雄市苓雅區四維三路2號四維行政中心辦公大樓4樓',
      ENVELOPE_CONFIG_.fixtureNote + '｜虛構收件人：李沐言'
    ]
  ];
  var fixtureRows = [];
  var lastNonFixtureDataRow = 1;
  var lastDataRow = findLastRecipientDataRow_(recipientSheet);
  if (lastDataRow >= 2) {
    recipientSheet
      .getRange(2, 1, lastDataRow - 1, 4)
      .getValues()
      .forEach(function (row, index) {
        var note = String(row[3] || '');
        var rowNumber = index + 2;
        if (note.indexOf(ENVELOPE_CONFIG_.fixtureNote) === 0) {
          fixtureRows.push(rowNumber);
          return;
        }
        var hasUserContent = row.slice(1, 4).some(function (value) {
          return String(value || '').trim() !== '';
        });
        if (hasUserContent) {
          lastNonFixtureDataRow = rowNumber;
        }
      });
  }

  var targetStartRow = lastNonFixtureDataRow + 1;
  var targetEndRow = targetStartRow + fixtures.length - 1;
  recipientSheet
    .getRange(targetStartRow, 1, fixtures.length, 4)
    .setValues(fixtures);
  fixtureRows.forEach(function (rowNumber) {
    if (rowNumber < targetStartRow || rowNumber > targetEndRow) {
      // 只清除可辨識的舊教學假資料，不碰使用者自行輸入的內容。
      recipientSheet.getRange(rowNumber, 1, 1, 4).clearContent();
    }
  });
  logEnvelope_(
    '進度',
    '已整理 ' +
      fixtures.length +
      ' 筆公家機關教學假資料｜資料列=' +
      targetStartRow +
      '-' +
      targetEndRow
  );
}
