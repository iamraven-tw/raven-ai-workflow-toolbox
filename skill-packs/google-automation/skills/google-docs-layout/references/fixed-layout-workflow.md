# Google Docs 固定版面工作流程

## 一、先把參考圖變成驗收條件

不要直接從「看起來像」開始調數字。先列出：

- 紙張寬高、直式或橫式，以及四邊留白。
- 每一個資料區相對於頁面的上、下、左、右與置中關係。
- 各資料區的字體、粗體、斜體、水平對齊、垂直對齊與行距。
- 一筆資料要占幾頁，資料之間如何分頁。
- 最長名稱、地址、編號或備註的測試資料。
- 哪些結果能由程式檢查，哪些一定要開啟 Google Docs 目視確認。

參考圖已由使用者提供時，以該圖為主要位置基準；有官方書寫規範時，再用官方規範核對資料區意義。

## 二、使用一個無框線表格作為一頁的座標骨架

Google Docs 不是精密桌面排版軟體。固定版面優先把每一頁拆成列與欄，再以一個表格承載該頁全部主要資料區：

```javascript
/**
 * 建立一頁固定版面。
 *
 * @param {GoogleAppsScript.Document.Body} body 文件本文。
 * @param {Object} data 本頁資料。
 */
function renderFixedPage_(body, data) {
  var layout = resolveFixedLayout_();
  var table = body.appendTable([
    [data.sender, '', data.stampLabel],
    ['', data.recipient, ''],
    ['', '', '']
  ]);

  table.setBorderWidth(0);
  layout.columnWidths.forEach(function (width, columnIndex) {
    table.setColumnWidth(columnIndex, width);
  });
  layout.rowHeights.forEach(function (height, rowIndex) {
    table.getRow(rowIndex).setMinimumHeight(height);
  });
}
```

同一頁不要把頁首、主要內容與頁尾拆成多個相鄰表格。獨立表格之間可能被 Google Docs 插入分頁，導致原本應在同一頁的編號或地址掉到下一頁。

固定版面優先用現有寬欄與留白欄控制位置，不要先用 `merge()`。合併儲存格會改變後續 `getCell(row, column)` 的索引認知與欄跨度，版面調整時容易把內容移到意外位置。

## 三、集中管理頁面與版面尺寸

Google Docs 的尺寸單位是 point。頁面、邊界、欄寬、列高與內距要集中管理，避免魔術數字散落：

```javascript
/**
 * 回傳固定版面尺寸。
 *
 * @return {{page:Object,margins:Object,columnWidths:Array<number>,
 *   rowHeights:Array<number>,safeHeight:number}} 版面設定。
 */
function resolveFixedLayout_() {
  return {
    page: {width: 792, height: 612},
    margins: {top: 36, right: 42, bottom: 36, left: 42},
    columnWidths: [270, 360, 120],
    rowHeights: [120, 290, 70],
    safeHeight: 500
  };
}
```

設定頁面時要同時明確指定寬、高與四邊留白：

```javascript
// 頁面方向只處理紙張，內容位置仍由表格設定。
body
  .setPageWidth(layout.page.width)
  .setPageHeight(layout.page.height)
  .setMarginTop(layout.margins.top)
  .setMarginRight(layout.margins.right)
  .setMarginBottom(layout.margins.bottom)
  .setMarginLeft(layout.margins.left);
```

`setMinimumHeight()` 只保證最小列高。文字、行距、段落與儲存格內距仍可能增加實際高度，因此 `safeHeight` 只能用來在本機阻擋明顯超標，不能宣稱實際文件一定只有一頁。

## 四、不同方向使用不同排版函式

直式與橫式的資料區關係不同時，使用：

- `renderPortrait..._()` 與 `resolvePortrait...Layout_()`。
- `renderLandscape..._()` 與 `resolveLandscape...Layout_()`。

共用函式只保留真正相同的文字處理、樣式套用與資料解析。某一方向經使用者目視驗收後，記為版面基線；開發另一方向時不可順手改動其欄寬、列高或位置。

## 五、中文直排使用窄欄自然折行

Apps Script 的 Google Docs 服務沒有原生中文直書設定。需要直排中文時：

1. 先移除資料內原有的空白與換行。
2. 把文字放進足以容納單一中文字的窄欄。
3. 讓 Google Docs 自然折行。
4. 用欄位置決定資料區在頁面的左、中、右，不只設定段落置中。

不要把字串改成「每個字後加 `\n`」。手動換行會形成多個段落，增加段落間距、讓第一個字後出現不自然空白，也更容易把內容推到下一頁。

## 六、整格字體與逐段排版要分開處理

以 `cell.getChild(0).asParagraph().editAsText()` 設定字體，只會改到第一個段落。多行內容可能仍保留 Google Docs 預設的 9 號字。

正確做法是先處理整格文字，再逐段處理段落屬性：

```javascript
/**
 * 套用固定版面儲存格樣式。
 *
 * @param {GoogleAppsScript.Document.TableCell} cell 儲存格。
 * @param {GoogleAppsScript.Document.HorizontalAlignment} horizontal 水平對齊。
 * @param {GoogleAppsScript.Document.VerticalAlignment} vertical 垂直對齊。
 * @param {number} fontSize 字體大小。
 * @param {number} lineSpacing 行距。
 */
function styleFixedCell_(cell, horizontal, vertical, fontSize, lineSpacing) {
  cell
    .setVerticalAlignment(vertical)
    .setPaddingTop(2)
    .setPaddingRight(2)
    .setPaddingBottom(2)
    .setPaddingLeft(2);

  // 字體屬性一次套用整個儲存格，避免只有第一段被修改。
  cell
    .editAsText()
    .setFontSize(fontSize)
    .setBold(false)
    .setItalic(false);

  // 對齊、段距與行距屬於段落，必須逐段設定。
  for (var index = 0; index < cell.getNumChildren(); index += 1) {
    var child = cell.getChild(index);
    if (child.getType() !== DocumentApp.ElementType.PARAGRAPH) {
      continue;
    }
    child
      .asParagraph()
      .setAlignment(horizontal)
      .setSpacingBefore(0)
      .setSpacingAfter(0)
      .setLineSpacing(lineSpacing);
  }
}
```

## 七、保護不可拆文字與長資料

- 郵遞區號、識別碼與固定編號要有足夠欄寬。
- 需要顯示 `3+3` 郵遞區號時，可使用不可斷行連字號 `‑`，避免在連字號後換行。
- 不要為了塞入長文字，直接縮小已確認的字體。優先調整資料分行、行距、欄寬、列高與內距。
- 地址可依語意分行，例如「縣市＋行政區」與「道路門牌」，不要只按照固定字數任意截斷。
- 測試要包含比日常資料更長的名稱與地址。

## 八、一筆一頁與分頁

每筆資料先完整建立在同一個表格，再於兩筆資料之間加入明確的 `PageBreak`。不要在同一筆資料的多個區塊之間加入分頁。

程式可以檢查：

- 每筆資料建立一個主要表格。
- 預定列高總和不超過安全高度。
- 每兩筆資料之間建立一個分頁。

程式無法可靠取代的檢查：

- 實際渲染後是否剛好一頁。
- 長文字是否造成表格變高。
- 編號、頁首或頁尾是否被推到下一頁。

這些項目必須由使用者打開實際文件目視確認。

## 九、遠端讀回實際文字樣式

來源碼寫了 `setFontSize(28)`，不代表每個段落都真的變成 28。測試要重新開啟產出的文件，逐一檢查非空白字元：

```javascript
/**
 * 確認儲存格內所有可見字元的實際字體。
 *
 * @param {GoogleAppsScript.Document.TableCell} cell 儲存格。
 * @param {number} expectedSize 預期字體。
 * @param {string} label 區塊名稱。
 */
function assertCellFontSize_(cell, expectedSize, label) {
  var text = cell.editAsText();
  var value = text.getText();

  for (var index = 0; index < value.length; index += 1) {
    if (/\s/.test(value.charAt(index))) {
      continue;
    }
    if (text.getFontSize(index) !== expectedSize) {
      throw new Error(label + '仍有文字不是 ' + expectedSize + ' 字。');
    }
  }
}
```

遠端測試至少讀回第一個代表頁；高風險版面可抽樣第一頁、最長資料頁與最後一頁。測試結束後要 `saveAndClose()`。

## 十、測試矩陣

本機測試：

- 頁面方向、欄寬總和、列高總和與安全高度。
- 文字正規化不插入逐字換行。
- 不可斷行字元與地址分行。
- 一筆資料只建立一個主要表格。
- 多行儲存格會對整格套用字體，且每個段落都套用對齊與行距。
- 已定稿方向的尺寸常數沒有被其他方向修改。

遠端程式測試：

- 文件可建立或安全重寫。
- 實際表格數與資料筆數符合預期。
- 代表儲存格逐字讀回正確字體。
- 正常、錯誤、長資料與重複執行案例通過。

使用者目視驗收：

- 紙張方向。
- 資料區相對位置。
- 字體大小、粗體與斜體。
- 每筆資料只有一頁。
- 長名稱、長地址、郵遞區號沒有截斷、分離或跑位。
- 列印前的預覽仍符合參考圖。

## 十一、常見症狀與修正方向

| 症狀 | 優先檢查 |
|---|---|
| 多行文字仍是 9 號字 | 是否只修改第一個段落，而沒有對 `cell.editAsText()` 套用字體 |
| 第一個中文字後出現大空隙 | 是否用逐字 `\n` 模擬直排，造成多個段落 |
| 郵遞區號掉到下一頁 | 是否把同一頁拆成多個表格、欄寬不足或使用一般連字號 |
| 合併後內容位置突然改變 | 儲存格索引與欄跨度是否因 `merge()` 改變 |
| 程式測試通過但文件跑位 | 是否只驗證常數，未讀回實際樣式，也未執行目視驗收 |
| 開發橫式後直式變壞 | 是否共用同一組欄寬、列高或順手重構已定稿基線 |

## 官方 API 參考

- [Body：頁面大小與邊界](https://developers.google.com/apps-script/reference/document/body)
- [Table：欄寬與表格設定](https://developers.google.com/apps-script/reference/document/table)
- [TableCell：內距、垂直對齊與 editAsText](https://developers.google.com/apps-script/reference/document/table-cell)
- [Text：setFontSize 與 getFontSize](https://developers.google.com/apps-script/reference/document/text)
