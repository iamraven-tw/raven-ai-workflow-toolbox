/**
 * 輸出可供初學者判讀的繁體中文執行記錄。
 *
 * @param {string} level 狀態標記，例如「開始」或「成功」。
 * @param {string} message 不含秘密或個資的訊息。
 */
function logBatchMailer_(level, message) {
  console.info('[' + level + '] ' + message);
}

/**
 * 輸出失敗紀錄，保留繁體中文脈絡。
 *
 * @param {string} message 不含秘密或個資的失敗訊息。
 */
function logBatchMailerError_(message) {
  console.error('[失敗] ' + message);
}
