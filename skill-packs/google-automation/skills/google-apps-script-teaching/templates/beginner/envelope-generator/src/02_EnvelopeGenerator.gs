/**
 * 開啟試算表時建立操作選單。
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('信封工具')
    .addItem('產生信封文件', 'generateEnvelopeDocuments')
    .addToUi();
}

/**
 * 建立寄件人、收件人與產生結果工作表。
 * 初次建立時設定合理欄寬，重複執行不覆蓋使用者後續調整。
 */
function setupEnvelopeGenerator() {
  logEnvelope_('開始', '準備建立批次信封版面產生器');

  try {
    var spreadsheet = openEnvelopeSpreadsheet_();
    logEnvelope_('設定', 'SPREADSHEET_ID 已設定且可以開啟');

    var senderResult = getOrCreateEnvelopeSheet_(
      spreadsheet,
      ENVELOPE_CONFIG_.senderSheetName,
      true
    );
    var recipientResult = getOrCreateEnvelopeSheet_(
      spreadsheet,
      ENVELOPE_CONFIG_.recipientSheetName,
      false
    );
    var outputResult = getOrCreateEnvelopeSheet_(
      spreadsheet,
      ENVELOPE_CONFIG_.resultSheetName,
      false
    );

    ensureSenderSheet_(senderResult.sheet);
    ensureRecipientSheet_(recipientResult.sheet);
    ensureResultSheet_(outputResult.sheet);

    logEnvelope_(
      '成功',
      '已建立寄件人設定、收件人清單與產生結果；重新開啟試算表後會載入信封工具選單'
    );
  } catch (error) {
    logEnvelopeError_('建立批次信封版面產生器失敗｜原因：' + error.message);
    throw error;
  }
}

/**
 * 讀取勾選資料，產生或更新同一份 Google Docs 信封文件。
 *
 * @return {{documentId:string,url:string,pageCount:number,skipped:number,created:boolean}} 產生結果。
 */
function generateEnvelopeDocuments() {
  logEnvelope_('開始', '準備產生批次信封文件');

  try {
    var spreadsheet = openEnvelopeSpreadsheet_();
    logEnvelope_('設定', 'SPREADSHEET_ID 已設定且可以開啟');

    var input = readEnvelopeInput_(spreadsheet);
    logEnvelope_(
      '進度',
      '已讀取有效收件人｜筆數=' + input.recipients.length + '｜未勾選=' + input.unselected
    );
    if (input.skipped > 0) {
      logEnvelope_('警告', '已略過資料不完整的勾選列｜筆數=' + input.skipped);
    }

    var documentResult = openOrCreateEnvelopeDocument_();
    renderEnvelopeDocument_(documentResult.document, input);
    var documentUrl = documentResult.document.getUrl();
    var documentId = documentResult.document.getId();
    documentResult.document.saveAndClose();

    writeEnvelopeResult_(
      spreadsheet,
      documentUrl,
      input.recipients.length,
      input.skipped
    );

    logEnvelope_(
      '成功',
      (documentResult.created ? '已建立' : '已更新') +
        '信封文件｜頁數=' + input.recipients.length +
        '｜略過筆數=' + input.skipped
    );

    return {
      documentId: documentId,
      url: documentUrl,
      pageCount: input.recipients.length,
      skipped: input.skipped,
      created: documentResult.created
    };
  } catch (error) {
    logEnvelopeError_('產生批次信封文件失敗｜原因：' + error.message);
    throw error;
  }
}

/**
 * 取得或建立指定工作表。
 *
 * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} spreadsheet 資料試算表。
 * @param {string} name 工作表名稱。
 * @param {boolean} reuseBlank 是否可沿用唯一空白預設工作表。
 * @return {{sheet:GoogleAppsScript.Spreadsheet.Sheet,created:boolean}} 工作表與建立狀態。
 */
function getOrCreateEnvelopeSheet_(spreadsheet, name, reuseBlank) {
  var existing = spreadsheet.getSheetByName(name);
  if (existing) {
    logEnvelope_('略過', name + ' 工作表已存在');
    return { sheet: existing, created: false };
  }

  var sheets = spreadsheet.getSheets();
  if (
    reuseBlank &&
    sheets.length === 1 &&
    sheets[0].getLastRow() === 0 &&
    sheets[0].getLastColumn() === 0
  ) {
    sheets[0].setName(name);
    logEnvelope_('進度', '已將空白預設工作表設定為 ' + name);
    return { sheet: sheets[0], created: true };
  }

  logEnvelope_('進度', '正在建立 ' + name + ' 工作表');
  return { sheet: spreadsheet.insertSheet(name), created: true };
}

/**
 * 建立或驗證寄件人設定工作表。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 寄件人設定工作表。
 */
function ensureSenderSheet_(sheet) {
  var range = sheet.getRange(1, 1, 4, 2);
  var rows = range.getValues();
  var isEmpty = rows.every(function (row) {
    return row.every(function (value) {
      return value === '';
    });
  });

  if (isEmpty) {
    range.setValues([
      ENVELOPE_CONFIG_.senderHeaders,
      [ENVELOPE_CONFIG_.senderKeys[0], ''],
      [ENVELOPE_CONFIG_.senderKeys[1], ''],
      [ENVELOPE_CONFIG_.senderKeys[2], '直式']
    ]);
    sheet.setFrozenRows(1);
    sheet.getRange('A1:B1').setFontWeight('bold');
    sheet.setColumnWidth(1, 140);
    sheet.setColumnWidth(2, 320);
    return;
  }

  var expectedKeys = [
    ENVELOPE_CONFIG_.senderHeaders[0],
    ENVELOPE_CONFIG_.senderKeys[0],
    ENVELOPE_CONFIG_.senderKeys[1],
    ENVELOPE_CONFIG_.senderKeys[2]
  ];
  var labelsMatch = expectedKeys.every(function (label, index) {
    return rows[index][0] === label;
  });
  if (rows[0][1] !== ENVELOPE_CONFIG_.senderHeaders[1] || !labelsMatch) {
    throw new Error('寄件人設定欄位與教材不同，為避免覆寫資料已停止。');
  }
}

/**
 * 建立或驗證收件人清單工作表。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 收件人清單工作表。
 */
function ensureRecipientSheet_(sheet) {
  var headers = ENVELOPE_CONFIG_.recipientHeaders;
  var existing = sheet.getRange(1, 1, 1, headers.length).getValues()[0];
  var isEmpty = existing.every(function (value) {
    return value === '';
  });

  if (isEmpty) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    // 只加入核取方塊規則，不預先填入 99 筆 false，避免空白列被誤算成資料。
    var checkboxRule = SpreadsheetApp.newDataValidation()
      .requireCheckbox()
      .build();
    sheet.getRange(2, 1, 99, 1).setDataValidation(checkboxRule);
    sheet.setFrozenRows(1);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
    sheet.setColumnWidth(1, 100);
    sheet.setColumnWidth(2, 160);
    sheet.setColumnWidth(3, 320);
    sheet.setColumnWidth(4, 180);
    return;
  }

  var matches = headers.every(function (header, index) {
    return existing[index] === header;
  });
  if (!matches) {
    throw new Error('收件人清單欄位與教材不同，為避免覆寫資料已停止。');
  }
}

/**
 * 建立或驗證產生結果工作表。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 產生結果工作表。
 */
function ensureResultSheet_(sheet) {
  var headers = ENVELOPE_CONFIG_.resultHeaders;
  var existing = sheet.getRange(1, 1, 1, headers.length).getValues()[0];
  var isEmpty = existing.every(function (value) {
    return value === '';
  });

  if (isEmpty) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.setFrozenRows(1);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
    sheet.setColumnWidth(1, 170);
    sheet.setColumnWidth(2, 360);
    sheet.setColumnWidth(3, 90);
    sheet.setColumnWidth(4, 100);
    return;
  }

  var matches = headers.every(function (header, index) {
    return existing[index] === header;
  });
  if (!matches) {
    throw new Error('產生結果欄位與教材不同，為避免覆寫資料已停止。');
  }
}

/**
 * 只依名稱、地址與備註判斷最後資料列。
 * 核取方塊欄的 FALSE 不代表該列已有收件人資料。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet 收件人清單工作表。
 * @return {number} 最後一筆實際資料列；沒有資料時回傳標題列 1。
 */
function findLastRecipientDataRow_(sheet) {
  var lastSheetRow = sheet.getLastRow();
  if (lastSheetRow < 2) {
    return 1;
  }

  var contentRows = sheet.getRange(2, 2, lastSheetRow - 1, 3).getValues();
  for (var index = contentRows.length - 1; index >= 0; index -= 1) {
    var hasContent = contentRows[index].some(function (value) {
      return String(value || '').trim() !== '';
    });
    if (hasContent) {
      return index + 2;
    }
  }
  return 1;
}

/**
 * 從 Sheets 讀取並整理信封資料。
 *
 * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} spreadsheet 資料試算表。
 * @return {{sender:Object,recipients:Array<Object>,skipped:number,unselected:number}} 整理後資料。
 */
function readEnvelopeInput_(spreadsheet) {
  var senderSheet = spreadsheet.getSheetByName(ENVELOPE_CONFIG_.senderSheetName);
  var recipientSheet = spreadsheet.getSheetByName(ENVELOPE_CONFIG_.recipientSheetName);
  if (!senderSheet || !recipientSheet) {
    throw new Error('找不到必要工作表，請先執行 setupEnvelopeGenerator。');
  }

  var senderRows = senderSheet.getRange(2, 1, 3, 2).getValues();
  var lastDataRow = findLastRecipientDataRow_(recipientSheet);
  var recipientRows = lastDataRow < 2
    ? []
    : recipientSheet.getRange(2, 1, lastDataRow - 1, 4).getValues();

  return normalizeEnvelopeData_(senderRows, recipientRows);
}

/**
 * 驗證並整理信封資料，讓純邏輯可以在本機測試。
 *
 * @param {Array<Array<*>>} senderRows 寄件人設定列。
 * @param {Array<Array<*>>} recipientRows 收件人資料列。
 * @return {{sender:Object,recipients:Array<Object>,skipped:number,unselected:number}} 整理後資料。
 */
function normalizeEnvelopeData_(senderRows, recipientRows) {
  var senderMap = {};
  senderRows.forEach(function (row) {
    senderMap[String(row[0] || '').trim()] = String(row[1] || '').trim();
  });

  var senderName = senderMap[ENVELOPE_CONFIG_.senderKeys[0]] || '';
  var senderAddress = senderMap[ENVELOPE_CONFIG_.senderKeys[1]] || '';
  var orientation = senderMap[ENVELOPE_CONFIG_.senderKeys[2]] || '';
  if (senderName === '') {
    throw new Error('寄件人名稱不可空白。');
  }
  if (senderAddress === '') {
    throw new Error('寄件人地址不可空白。');
  }
  resolveEnvelopePageSize_(orientation);

  var recipients = [];
  var skipped = 0;
  var unselected = 0;
  recipientRows.forEach(function (row) {
    if (!isEnvelopeRowSelected_(row[0])) {
      unselected += 1;
      return;
    }

    var name = String(row[1] || '').trim();
    var address = String(row[2] || '').trim();
    var note = String(row[3] || '').trim();
    if (name === '' || address === '') {
      skipped += 1;
      return;
    }
    recipients.push({
      name: name,
      address: address,
      note: note
    });
  });

  if (recipients.length === 0) {
    throw new Error('沒有可產生的有效收件人，請勾選資料並確認姓名與地址。');
  }

  return {
    sender: {
      name: senderName,
      address: senderAddress,
      orientation: orientation
    },
    recipients: recipients,
    skipped: skipped,
    unselected: unselected
  };
}

/**
 * 判斷收件人資料列是否勾選。
 *
 * @param {*} rawValue 核取方塊或文字值。
 * @return {boolean} 是否產生。
 */
function isEnvelopeRowSelected_(rawValue) {
  if (rawValue === true) {
    return true;
  }
  var value = String(rawValue || '').trim().toLowerCase();
  return value === 'true' || value === '是' || value === '1' || value === 'y';
}

/**
 * 取得 A4 直式或橫式頁面尺寸。
 *
 * @param {string} orientation 直式或橫式。
 * @return {{width:number,height:number}} 頁面尺寸（點）。
 */
function resolveEnvelopePageSize_(orientation) {
  var portrait = { width: 595.28, height: 841.89 };
  if (orientation === '直式') {
    return portrait;
  }
  if (orientation === '橫式') {
    return { width: portrait.height, height: portrait.width };
  }
  throw new Error('版面方向必須是「直式」或「橫式」。');
}

/**
 * 開啟既有輸出文件；第一次執行時建立並記住同一份文件。
 *
 * @return {{document:GoogleAppsScript.Document.Document,created:boolean}} 文件與建立狀態。
 */
function openOrCreateEnvelopeDocument_() {
  var properties = PropertiesService.getScriptProperties();
  var documentId = properties.getProperty(ENVELOPE_CONFIG_.outputDocumentProperty);

  if (documentId) {
    try {
      return {
        document: DocumentApp.openById(documentId),
        created: false
      };
    } catch (error) {
      throw new Error(
        '找不到先前產生的信封文件，為避免建立重複文件已停止。請檢查 ENVELOPE_DOCUMENT_ID。'
      );
    }
  }

  var document = DocumentApp.create('批次信封版面（教學測試）');
  properties.setProperty(ENVELOPE_CONFIG_.outputDocumentProperty, document.getId());
  return {
    document: document,
    created: true
  };
}

/**
 * 重寫程式專用的輸出文件，並依設定套用直式或橫式版面。
 *
 * @param {GoogleAppsScript.Document.Document} document 輸出文件。
 * @param {{sender:Object,recipients:Array<Object>}} input 信封資料。
 */
function renderEnvelopeDocument_(document, input) {
  var body = document.getBody();
  var pageSize = resolveEnvelopePageSize_(input.sender.orientation);
  body.clear();
  body.setPageWidth(pageSize.width);
  body.setPageHeight(pageSize.height);
  body.setMarginTop(36);
  body.setMarginBottom(36);
  body.setMarginLeft(42);
  body.setMarginRight(42);

  input.recipients.forEach(function (recipient, index) {
    if (input.sender.orientation === '直式') {
      renderPortraitEnvelopePage_(body, input.sender, recipient);
    } else {
      renderLandscapeEnvelopePage_(body, input.sender, recipient);
    }

    if (index < input.recipients.length - 1) {
      body.appendPageBreak();
    }
  });
}

/**
 * 依中華郵政國內直式信封位置，建立一頁直排信封。
 * Google 文件沒有原生中文直書，因此以窄欄自動折行模擬直排。
 *
 * @param {GoogleAppsScript.Document.Body} body 文件本文。
 * @param {{name:string,address:string}} sender 寄件人。
 * @param {{name:string,address:string,note:string}} recipient 收件人。
 */
function renderPortraitEnvelopePage_(body, sender, recipient) {
  var senderAddress = parseEnvelopePostalAddress_(sender.address);
  var recipientAddress = parseEnvelopePostalAddress_(recipient.address);
  var recipientPerson = extractEnvelopeRecipientPerson_(recipient.note);
  var layout = resolvePortraitEnvelopeLayout_();
  var table = body.appendTable([
    [
      '',
      '',
      '貼郵票處',
      '',
      formatEnvelopePostalCode_(recipientAddress.postalCode),
      ''
    ],
    [
      normalizeVerticalEnvelopeText_(sender.name + '緘'),
      normalizeVerticalEnvelopeText_(senderAddress.address),
      '',
      normalizeVerticalEnvelopeText_(
        recipient.name +
          (recipientPerson === '' ? '' : recipientPerson) +
          '收'
      ),
      '',
      normalizeVerticalEnvelopeText_(recipientAddress.address)
    ],
    ['', '', formatEnvelopePostalCode_(senderAddress.postalCode), '', '', '']
  ]);

  // 每位收件人只使用一個表格，避免三個區塊被 Google Docs 拆到不同頁。
  table.setBorderWidth(0);
  layout.columnWidths.forEach(function (width, columnIndex) {
    table.setColumnWidth(columnIndex, width);
  });
  layout.rowHeights.forEach(function (height, rowIndex) {
    table.getRow(rowIndex).setMinimumHeight(height);
  });

  // 郵遞區號直接使用寬留白欄，不合併儲存格，避免欄位位置被重排。
  styleEnvelopeCell_(
    table.getCell(0, 2),
    DocumentApp.HorizontalAlignment.LEFT,
    DocumentApp.VerticalAlignment.TOP,
    24
  );
  styleEnvelopeCell_(
    table.getCell(0, 4),
    DocumentApp.HorizontalAlignment.RIGHT,
    DocumentApp.VerticalAlignment.TOP,
    20
  );
  styleEnvelopeCell_(
    table.getCell(1, 0),
    DocumentApp.HorizontalAlignment.CENTER,
    DocumentApp.VerticalAlignment.BOTTOM,
    24
  );
  styleEnvelopeCell_(
    table.getCell(1, 1),
    DocumentApp.HorizontalAlignment.CENTER,
    DocumentApp.VerticalAlignment.BOTTOM,
    24
  );
  styleEnvelopeCell_(
    table.getCell(1, 3),
    DocumentApp.HorizontalAlignment.CENTER,
    DocumentApp.VerticalAlignment.CENTER,
    28
  );
  styleEnvelopeCell_(
    table.getCell(1, 5),
    DocumentApp.HorizontalAlignment.CENTER,
    DocumentApp.VerticalAlignment.TOP,
    28
  );
  styleEnvelopeCell_(
    table.getCell(2, 2),
    DocumentApp.HorizontalAlignment.LEFT,
    DocumentApp.VerticalAlignment.BOTTOM,
    20
  );
  // 郵遞區號靠外側不留內距，讓收件碼更靠右、寄件碼更靠左。
  table.getCell(0, 4).setPaddingRight(0);
  table.getCell(2, 2).setPaddingLeft(0);
}

/**
 * 集中管理直式信封尺寸，讓本機測試能驗證單頁安全範圍。
 *
 * @return {{columnWidths:Array<number>,rowHeights:Array<number>,safeHeight:number}} 版面尺寸。
 */
function resolvePortraitEnvelopeLayout_() {
  return {
    // 中央收件人欄的中心點落在頁面中央，地址欄維持最右側。
    columnWidths: [30, 30, 172, 39, 197, 32],
    // 總高度保留額外空間，避免表格加上內距後被自動分頁。
    rowHeights: [48, 590, 45],
    safeHeight: 700
  };
}

/**
 * 依中華郵政國內橫式信封位置，建立一頁橫排信封。
 *
 * @param {GoogleAppsScript.Document.Body} body 文件本文。
 * @param {{name:string,address:string}} sender 寄件人。
 * @param {{name:string,address:string,note:string}} recipient 收件人。
 */
function renderLandscapeEnvelopePage_(body, sender, recipient) {
  var layout = resolveLandscapeEnvelopeLayout_();
  var table = body.appendTable([
    [buildLandscapeSenderText_(sender), '', '貼郵票處'],
    ['', buildLandscapeRecipientText_(recipient), ''],
    ['', '', '']
  ]);

  // 橫式使用獨立的單一表格，不共用已定稿的直式欄寬。
  table.setBorderWidth(0);
  layout.columnWidths.forEach(function (width, columnIndex) {
    table.setColumnWidth(columnIndex, width);
  });
  layout.rowHeights.forEach(function (height, rowIndex) {
    table.getRow(rowIndex).setMinimumHeight(height);
  });

  styleEnvelopeCell_(
    table.getCell(0, 0),
    DocumentApp.HorizontalAlignment.LEFT,
    DocumentApp.VerticalAlignment.TOP,
    24,
    1
  );
  styleEnvelopeCell_(
    table.getCell(0, 2),
    DocumentApp.HorizontalAlignment.CENTER,
    DocumentApp.VerticalAlignment.TOP,
    24,
    1
  );
  styleEnvelopeCell_(
    table.getCell(1, 1),
    DocumentApp.HorizontalAlignment.LEFT,
    DocumentApp.VerticalAlignment.CENTER,
    28,
    1.05
  );
  table.getCell(0, 0).setPaddingTop(4).setPaddingLeft(4);
  table.getCell(0, 2).setPaddingTop(4).setPaddingRight(0);
  table.getCell(1, 1).setPaddingLeft(12);
}

/**
 * 集中管理橫式信封尺寸，與直式版面完全分開。
 *
 * @return {{columnWidths:Array<number>,rowHeights:Array<number>,safeHeight:number}} 版面尺寸。
 */
function resolveLandscapeEnvelopeLayout_() {
  return {
    columnWidths: [270, 360, 120],
    rowHeights: [120, 290, 70],
    safeHeight: 500
  };
}

/**
 * 組合橫式寄件人區塊。
 *
 * @param {{name:string,address:string}} sender 寄件人。
 * @return {string} 郵遞區號、地址與寄件人名稱。
 */
function buildLandscapeSenderText_(sender) {
  var parsed = parseEnvelopePostalAddress_(sender.address);
  return [
    formatEnvelopePostalCode_(parsed.postalCode)
  ]
    .concat(splitLandscapeEnvelopeAddress_(parsed.address))
    .concat([sender.name + '　緘'])
    .filter(function (line) {
      return line !== '';
    })
    .join('\n');
}

/**
 * 組合橫式收件人區塊。
 *
 * @param {{name:string,address:string,note:string}} recipient 收件人。
 * @return {string} 郵遞區號、地址與收件人名稱。
 */
function buildLandscapeRecipientText_(recipient) {
  var parsed = parseEnvelopePostalAddress_(recipient.address);
  var person = extractEnvelopeRecipientPerson_(recipient.note);
  var recipientLine =
    recipient.name +
    (person === '' ? '' : '　' + person) +
    '　啟';

  return [
    formatEnvelopePostalCode_(parsed.postalCode)
  ]
    .concat(splitLandscapeEnvelopeAddress_(parsed.address))
    .concat([recipientLine])
    .filter(function (line) {
      return line !== '';
    })
    .join('\n');
}

/**
 * 將臺灣地址優先分成「縣市＋行政區」與其餘門牌兩行。
 *
 * @param {string} rawAddress 不含郵遞區號的地址。
 * @return {Array<string>} 一至兩行橫式地址。
 */
function splitLandscapeEnvelopeAddress_(rawAddress) {
  var value = String(rawAddress || '').replace(/[\s　]+/g, '');
  if (value === '') {
    return [];
  }

  var matched = value.match(/^(.+?[市縣])(.+?[區鄉鎮市])(.+)$/);
  if (matched) {
    return [matched[1] + matched[2], matched[3]];
  }

  var characters = Array.from(value);
  if (characters.length > 16) {
    var middle = Math.ceil(characters.length / 2);
    return [
      characters.slice(0, middle).join(''),
      characters.slice(middle).join('')
    ];
  }
  return [value];
}

/**
 * 統一直式信封表格儲存格的留白、對齊與文字樣式。
 *
 * @param {GoogleAppsScript.Document.TableCell} cell 表格儲存格。
 * @param {GoogleAppsScript.Document.HorizontalAlignment} horizontal 水平對齊。
 * @param {GoogleAppsScript.Document.VerticalAlignment} vertical 垂直對齊。
 * @param {number} fontSize 字體大小。
 * @param {number=} lineSpacing 行距；未提供時使用直式的緊密行距。
 */
function styleEnvelopeCell_(cell, horizontal, vertical, fontSize, lineSpacing) {
  cell
    .setVerticalAlignment(vertical)
    .setPaddingTop(2)
    .setPaddingBottom(2)
    .setPaddingLeft(2)
    .setPaddingRight(2);

  // 一次套用整個儲存格文字，避免多行內容只有第一段改到字體。
  var cellText = cell.editAsText();
  cellText
    .setFontSize(fontSize)
    .setBold(false)
    .setItalic(false);

  // Google Docs 可能把換行拆成多個段落，逐段套用對齊與行距。
  for (var childIndex = 0; childIndex < cell.getNumChildren(); childIndex += 1) {
    var child = cell.getChild(childIndex);
    if (child.getType() !== DocumentApp.ElementType.PARAGRAPH) {
      continue;
    }
    child
      .asParagraph()
      .setAlignment(horizontal)
      .setSpacingBefore(0)
      .setSpacingAfter(0)
      .setLineSpacing(lineSpacing || 0.8);
  }
}

/**
 * 從地址前方拆出臺灣 3+3 郵遞區號。
 *
 * @param {string} rawAddress 含或不含郵遞區號的地址。
 * @return {{postalCode:string,address:string}} 郵遞區號與純地址。
 */
function parseEnvelopePostalAddress_(rawAddress) {
  var value = String(rawAddress || '').trim();
  var matched = value.match(/^(\d{3})[\s\-－]?(\d{3})\s*(.*)$/);
  if (!matched) {
    return {
      postalCode: '',
      address: value
    };
  }
  return {
    postalCode: matched[1] + matched[2],
    address: matched[3].trim()
  };
}

/**
 * 將 6 碼郵遞區號顯示為中華郵政常見的 3+3 格式。
 * 使用不可斷行連字號，避免 Google Docs 在連字號後自動換行。
 *
 * @param {string} postalCode 六碼郵遞區號。
 * @return {string} 例如 110‑204；沒有資料時回傳空字串。
 */
function formatEnvelopePostalCode_(postalCode) {
  var value = String(postalCode || '').replace(/\D/g, '');
  return value.length === 6
    ? value.substring(0, 3) + '‑' + value.substring(3)
    : value;
}

/**
 * 清除會干擾窄欄自然折行的空白與手動換行。
 *
 * @param {string} rawValue 原始文字。
 * @return {string} 可放入窄欄自動直排的連續文字。
 */
function normalizeVerticalEnvelopeText_(rawValue) {
  return String(rawValue || '').replace(/[\s　]+/g, '');
}

/**
 * 從教學備註取出虛構收件人；一般資料沒有這段標記時不額外顯示。
 *
 * @param {string} note 收件人備註。
 * @return {string} 虛構收件人姓名或空字串。
 */
function extractEnvelopeRecipientPerson_(note) {
  var matched = String(note || '').match(/虛構收件人[：:]\s*([^｜|]+)/);
  return matched ? matched[1].trim() : '';
}

/**
 * 寫入最新結果，不變更使用者調整的欄寬。
 *
 * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} spreadsheet 資料試算表。
 * @param {string} documentUrl Google Docs 文件網址。
 * @param {number} pageCount 頁數。
 * @param {number} skipped 略過筆數。
 */
function writeEnvelopeResult_(spreadsheet, documentUrl, pageCount, skipped) {
  var sheet = spreadsheet.getSheetByName(ENVELOPE_CONFIG_.resultSheetName);
  if (!sheet) {
    throw new Error('找不到產生結果工作表，請先執行 setupEnvelopeGenerator。');
  }

  sheet.getRange(2, 1, 1, 4).setValues([
    [new Date(), documentUrl, pageCount, skipped]
  ]);
  sheet.getRange('A2').setNumberFormat('yyyy-mm-dd hh:mm:ss');
}
