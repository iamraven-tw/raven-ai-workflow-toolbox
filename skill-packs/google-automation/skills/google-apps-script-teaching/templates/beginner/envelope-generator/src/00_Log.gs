/**
 * 輸出可供初學者判讀的繁體中文執行記錄。
 *
 * @param {string} level 狀態標記，例如「開始」或「成功」。
 * @param {string} message 不含姓名、地址、私人 ID 或秘密的訊息。
 */
function logEnvelope_(level, message) {
  console.info('[' + level + '] ' + message);
}

/**
 * 輸出失敗紀錄，保留繁體中文脈絡。
 *
 * @param {string} message 不含姓名、地址、私人 ID 或秘密的失敗訊息。
 */
function logEnvelopeError_(message) {
  console.error('[失敗] ' + message);
}
