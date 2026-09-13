/**
 * 執行最小專案健康檢查。
 *
 * 這個函式不讀取使用者資料，也不需要額外 OAuth 權限。
 *
 * @return {{ok: boolean, timestamp: string=, missing: string[]=}} 健康檢查結果。
 */
function healthCheck() {
  writeProjectLog_('開始', '執行專案健康檢查');

  var settings = checkProjectSettings();
  if (!settings.ok) {
    writeProjectLog_('失敗', '專案健康檢查未通過', '請先完成設定檢查');
    return {
      ok: false,
      missing: settings.missing,
    };
  }

  var result = {
    ok: true,
    // 使用 ISO 格式，避免不同地區的日期格式造成誤解。
    timestamp: new Date().toISOString(),
  };

  writeProjectLog_('成功', '專案健康檢查通過', '設定與基本執行均正常');
  return result;
}
