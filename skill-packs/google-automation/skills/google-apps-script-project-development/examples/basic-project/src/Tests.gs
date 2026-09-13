/**
 * 一次執行最小專案的正常、錯誤與重複執行測試。
 */
function runProjectTests() {
  writeProjectLog_('開始', '執行專案測試');

  try {
    testProjectNormal();
    testProjectError();
    testProjectRepeat();
    writeProjectLog_('成功', '專案測試全部通過', '正常、錯誤與重複執行均符合預期');
  } catch (error) {
    writeProjectLog_(
      '失敗',
      '專案測試未通過',
      '原因=' + error.message + '｜請依失敗項目檢查程式',
    );
    throw error;
  }
}

/**
 * 驗證設定完整時，健康檢查可以正常完成。
 */
function testProjectNormal() {
  writeProjectLog_('開始', '執行正常測試');

  var result = healthCheck();
  assertProject_(result.ok === true, '健康檢查應該成功');

  writeProjectLog_('成功', '正常測試通過', '健康檢查回傳成功');
}

/**
 * 使用測試替身驗證缺少設定時會安全停止，不修改真實屬性。
 */
function testProjectError() {
  writeProjectLog_('開始', '執行錯誤測試');

  var result = validateProjectSettings_(
    {},
    [{name: 'REQUIRED_TEST_SETTING', required: true}],
  );

  assertProject_(result.ok === false, '缺少必要設定時應該失敗');
  assertProject_(
    result.missing[0] === 'REQUIRED_TEST_SETTING',
    '錯誤結果應指出缺少的測試屬性名稱',
  );

  writeProjectLog_(
    '成功',
    '錯誤測試通過',
    '缺少設定已被拒絕，且未修改真實 Script Properties',
  );
}

/**
 * 驗證同一個入口重跑時不會建立重複業務結果。
 */
function testProjectRepeat() {
  writeProjectLog_('開始', '執行重複執行測試');

  var firstResult = healthCheck();
  var secondResult = healthCheck();

  assertProject_(firstResult.ok === true, '第一次執行應該成功');
  assertProject_(secondResult.ok === true, '第二次執行應該成功');

  writeProjectLog_(
    '成功',
    '重複執行測試通過',
    '健康檢查沒有建立資料、文件、郵件或觸發器',
  );
}

/**
 * 讓測試失敗時顯示初學者可理解的中文原因。
 *
 * @param {boolean} condition 必須成立的條件。
 * @param {string} message 失敗原因。
 */
function assertProject_(condition, message) {
  if (!condition) {
    throw new Error('測試失敗：' + message);
  }
}
