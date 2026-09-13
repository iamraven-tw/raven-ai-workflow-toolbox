const COURSE_MENU_NAME_ = '活動報名工具';

/**
 * Sheets 簡單觸發器：每次開啟試算表時建立日常操作選單。
 *
 * 本函式只建立 UI，不讀寫資料，也不執行任何業務功能。第 7 課需要的
 * 可安裝觸發器仍依該課的獨立確認與驗收流程處理。
 */
function onOpen(e) {
  buildActivityRegistrationMenu_(SpreadsheetApp.getUi());
}

/**
 * 建立目前累積課程可用的 Sheets 選單。
 *
 * 工程測試與底線結尾的內部函式不得加入。後續課程只追加真正的日常
 * 操作入口，不要求一般使用者進入 Apps Script 編輯器選函式。
 *
 * @param {GoogleAppsScript.Base.Ui} ui Sheets 使用者介面。
 * @return {number} 顯示的功能數量。
 */
function buildActivityRegistrationMenu_(ui) {
  if (!ui || typeof ui.createMenu !== 'function') {
    throw new Error('無法建立活動報名工具選單');
  }

  const menu = ui.createMenu(COURSE_MENU_NAME_);
  const items = getActivityRegistrationMenuItems_();

  items.forEach((item, index) => {
    if (item.separator) {
      if (index > 0 && index < items.length - 1) {
        menu.addSeparator();
      }
      return;
    }
    menu.addItem(item.label, item.handler);
  });
  menu.addToUi();
  return items.filter((item) => !item.separator).length;
}

/**
 * 取得目前課次已完成的日常入口。
 *
 * @return {Array<{label?: string, handler?: string, separator?: boolean}>} 選單項目。
 */
function getActivityRegistrationMenuItems_() {
  const items = [];
  const settingsHandler = getLatestCourseSettingsHandler_();

  if (settingsHandler !== '') {
    items.push({
      label: '檢查系統設定',
      handler: settingsHandler,
    });
  }
  if (typeof setupLessonSheet === 'function') {
    items.push({
      label: '初始化活動報名資料',
      handler: 'setupLessonSheet',
    });
  }
  if (typeof setupLesson03Form === 'function') {
    items.push({
      label: '設定活動報名表單',
      handler: 'setupLesson03Form',
    });
  }

  if (
    items.length > 0 &&
    typeof processPendingRegistrations === 'function'
  ) {
    items.push({ separator: true });
  }
  if (typeof processPendingRegistrations === 'function') {
    items.push({
      label: '批次處理待處理報名',
      handler: 'processPendingRegistrations',
    });
  }
  if (typeof createPendingRegistrationDocuments === 'function') {
    items.push({
      label: '建立報名確認文件',
      handler: 'createPendingRegistrationDocuments',
    });
  }
  if (typeof confirmLesson06RegistrationEmailSend === 'function') {
    items.push({
      label: '寄送報名確認郵件',
      handler: 'confirmLesson06RegistrationEmailSend',
    });
  }
  if (typeof confirmLesson06UnsentRecovery === 'function') {
    items.push({
      label: '確認未寄出並重設',
      handler: 'confirmLesson06UnsentRecovery',
    });
  }
  if (typeof checkLesson07Triggers === 'function') {
    items.push({ separator: true });
    items.push({
      label: '檢查觸發器狀態',
      handler: 'checkLesson07Triggers',
    });
  }
  if (typeof confirmLesson07FormTriggerSetup === 'function') {
    items.push({
      label: '啟用表單提交自動處理',
      handler: 'confirmLesson07FormTriggerSetup',
    });
  }
  if (typeof confirmLesson07TimeTriggerSetup === 'function') {
    items.push({
      label: '啟用短暫時間處理',
      handler: 'confirmLesson07TimeTriggerSetup',
    });
  }
  if (typeof confirmLesson07StopAutomation === 'function') {
    items.push({
      label: '停止第 7 課自動化',
      handler: 'confirmLesson07StopAutomation',
    });
  }

  return items;
}

/**
 * 只顯示目前累積專案中最新的設定檢查，不讓選單堆疊前課入口。
 *
 * @return {string} 最新設定檢查函式名稱；沒有時為空字串。
 */
function getLatestCourseSettingsHandler_() {
  if (typeof checkLesson08Settings === 'function') {
    return 'checkLesson08Settings';
  }
  if (typeof checkLesson07Settings === 'function') {
    return 'checkLesson07Settings';
  }
  if (typeof checkLesson06Settings === 'function') {
    return 'checkLesson06Settings';
  }
  if (typeof checkLesson05Settings === 'function') {
    return 'checkLesson05Settings';
  }
  if (typeof checkLesson04Settings === 'function') {
    return 'checkLesson04Settings';
  }
  if (typeof checkLesson03Settings === 'function') {
    return 'checkLesson03Settings';
  }
  if (typeof checkLesson02Settings === 'function') {
    return 'checkLesson02Settings';
  }
  if (typeof checkLesson01Settings === 'function') {
    return 'checkLesson01Settings';
  }
  return '';
}
