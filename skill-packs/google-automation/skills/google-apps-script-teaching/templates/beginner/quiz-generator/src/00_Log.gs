/**
 * 輸出教師測驗案例的繁體中文執行紀錄。
 *
 * @param {string} status 狀態名稱。
 * @param {string} message 不含個資的訊息。
 */
function logQuiz_(status, message) {
  var text = '[' + status + '] ' + message;
  if (status === '失敗') {
    console.error(text);
    return;
  }
  if (status === '警告' || status === '略過') {
    console.warn(text);
    return;
  }
  console.info(text);
}

/**
 * 輸出失敗紀錄。
 *
 * @param {string} message 不含姓名、學號或表單 ID 的錯誤訊息。
 */
function logQuizError_(message) {
  logQuiz_('失敗', message);
}
