/**
 * 輸出統一格式的第 1 課繁體中文紀錄檔(Log)。
 *
 * @param {string} status 紀錄檔(Log)狀態。
 * @param {string} message 給初學者閱讀的訊息。
 * @return {string} 實際輸出的完整文字。
 */
function writeLessonLog_(status, message) {
  const text = `[${status}] ${message}`;

  if (status === '失敗') {
    console.error(text);
  } else if (status === '略過' || status === '警告') {
    console.warn(text);
  } else {
    console.info(text);
  }

  return text;
}
