/**
 * 輸出格式一致、可由使用者判讀的繁體中文紀錄檔(Log)。
 *
 * @param {string} level 紀錄檔(Log)等級，例如「開始」或「成功」。
 * @param {string} message 給使用者看的中文說明。
 * @param {string=} details 不含敏感資料的補充資訊。
 * @return {string} 實際輸出的紀錄檔(Log)文字。
 */
function writeProjectLog_(level, message, details) {
  var suffix = details ? '｜' + details : '';
  var line = '[' + level + '] ' + message + suffix;

  if (level === '失敗') {
    console.error(line);
  } else if (level === '警告') {
    console.warn(line);
  } else {
    console.info(line);
  }

  return line;
}
