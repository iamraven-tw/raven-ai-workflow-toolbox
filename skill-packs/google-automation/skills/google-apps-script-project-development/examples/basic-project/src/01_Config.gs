/**
 * 專案需要的 Script Properties 清單。
 *
 * 這個最小範例沒有必要的屬性。實際專案新增設定時，只記錄名稱與用途，
 * 不得把真實值寫進程式或 Git。
 */
var PROJECT_PROPERTY_SPECS = [];

/**
 * 檢查目前專案需要的 Script Properties。
 *
 * @return {{ok: boolean, missing: string[]}} 設定檢查結果。
 */
function checkProjectSettings() {
  writeProjectLog_('開始', '檢查專案設定');

  var properties = PropertiesService.getScriptProperties().getProperties();
  var result = validateProjectSettings_(properties, PROJECT_PROPERTY_SPECS);

  if (!result.ok) {
    writeProjectLog_(
      '失敗',
      '缺少必要的指令碼屬性，未繼續執行',
      '名稱=' + result.missing.join(', ') + '｜請到「專案設定」的「指令碼屬性」補齊',
    );
    return result;
  }

  if (PROJECT_PROPERTY_SPECS.length === 0) {
    writeProjectLog_(
      '設定',
      '本功能沒有必要的 Script Properties',
      '程式未硬寫私人 ID 或秘密',
    );
  } else {
    writeProjectLog_(
      '設定',
      '必要的指令碼屬性均已設定',
      '數量=' + PROJECT_PROPERTY_SPECS.length,
    );
  }

  return result;
}

/**
 * 驗證傳入的設定物件，讓錯誤測試不必修改真實 Script Properties。
 *
 * @param {Object<string, string>} properties 測試或實際設定。
 * @param {{name: string, required: boolean}[]} specs 設定規格。
 * @return {{ok: boolean, missing: string[]}} 驗證結果。
 */
function validateProjectSettings_(properties, specs) {
  var missing = specs
    .filter(function (spec) {
      if (!spec.required) {
        return false;
      }

      var value = properties[spec.name];
      return value === undefined || value === null || String(value).trim() === '';
    })
    .map(function (spec) {
      return spec.name;
    });

  return {
    ok: missing.length === 0,
    missing: missing,
  };
}
