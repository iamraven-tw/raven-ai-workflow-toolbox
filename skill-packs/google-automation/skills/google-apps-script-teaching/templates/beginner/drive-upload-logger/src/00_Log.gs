/**
 * 輸出統一格式的繁體中文資訊紀錄。
 *
 * @param {string} stage 階段名稱。
 * @param {string} message 安全且不含個資的訊息。
 */
function logInfo_(stage, message) {
  console.info('[' + stage + '] ' + message);
}

/**
 * 輸出統一格式的繁體中文警告紀錄。
 *
 * @param {string} stage 階段名稱。
 * @param {string} message 安全且不含個資的訊息。
 */
function logWarning_(stage, message) {
  console.warn('[' + stage + '] ' + message);
}

/**
 * 將錯誤轉成初學者可理解的繁體中文訊息。
 *
 * @param {string} action 失敗的動作。
 * @param {*} error 原始錯誤。
 * @return {Error} 可重新拋出的錯誤。
 */
function logAndBuildError_(action, error) {
  var reason = error && error.message ? error.message : String(error);
  console.error('[失敗] ' + action + '｜原因：' + reason);
  return new Error(reason);
}
