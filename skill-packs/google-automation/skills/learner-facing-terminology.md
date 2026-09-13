# 初學者術語規則

本規則套用到本技能包的教學、專案開發、除錯與文件排版流程。只要是面向一般使用者或初學者的說明、確認、進度、結果與操作指示，都必須遵守。

## 強制格式

1. 技術術語第一次出現時，先用一句白話說明它在目前步驟的用途，再使用「中文名稱(English)」。
2. 後續面向使用者時仍以完整的「中文名稱(English)」為主，不得只留下英文術語或縮寫。
3. 中文與英文之間使用半形括號，不寫成全形括號，也不把英文放在中文前面。
4. 沒有穩定中文譯名時，先用白話描述用途，再保留原始名稱；不得自行創造會讓使用者誤解的中文產品名稱。
5. Google 產品名稱、畫面上的正式名稱、終端命令、程式碼、函式名稱、屬性名稱與檔名必須保持原文。向使用者展示前，另用中文說明其用途。例如保留 `Logger.log()`、`SPREADSHEET_ID` 與 `00_Log.gs`，但說明它們分別是寫入紀錄、指定試算表及集中管理紀錄功能的程式識別字。

## 常用固定名稱

| 中文名稱(English) | 用途 |
| --- | --- |
| 紀錄檔(Log) | 程式執行時留下的步驟、成功或錯誤訊息。不得只用英文稱呼。 |
| 函式(function) | AI 代理(Agent)已寫好、可以被呼叫的一個「有名字的動作」。 |
| 指令碼屬性(Script Properties) | Apps Script 專案內用來保存可變設定的位置。 |
| 使用者介面(UI) | 使用者實際看見並操作的畫面。 |
| 識別碼(ID) | 讓程式找到指定 Google 資源的「門牌號碼」。 |
| 網址(URL) | 可開啟指定網頁或 Google 資源的位址。 |
| 電子郵件(Email) | 寄件或收件使用的郵件地址與訊息。 |
| 應用程式介面(API) | 讓程式呼叫另一項服務的規則與入口。 |
| 授權機制(OAuth) | 由使用者同意程式可使用哪些 Google 資源的授權流程。 |
| 觸發器(trigger) | 在指定事件或時間自動呼叫函式的機制。 |
| 部署(deployment) | 把特定版本發布成可供外部使用的形式。 |
| 資訊清單(manifest) | `appsscript.json` 中描述 Apps Script 專案設定與權限的檔案。 |
| 網路應用程式(Web App) | 透過網址提供 Apps Script 功能的發布形式。 |
| 網路回呼(Webhook) | 其他系統用網路請求通知 Apps Script 的入口。 |
| 版本控制(Git) | AI 代理(Agent)用來保存本機程式修改歷史的工具。 |
| 本機版本提交(commit) | 把一組已驗證的本機修改保存成一個版本。 |
| AI 代理(Agent) | 負責寫程式、測試、管理本機檔案及引導驗收的 AI。 |

「推送到Apps Script(clasp push)」另依既有固定規則處理：先解釋它只會把本機已驗證的程式與資訊清單同步到指定 Apps Script 專案，不等於執行程式、寄信、建立觸發器或部署，再取得當次遠端操作確認。

## 例外界線

- 程式碼與終端命令必須保持可執行的原文，不把中文翻譯寫進命令或識別字。
- Google 畫面的正式繁體中文名稱以實際介面為準，不為了套用本表而改寫按鈕名稱。
- AI 代理(Agent)的內部工程記錄可以使用必要原文；只要轉成學員說明，就必須回到「中文名稱(English)」格式。

## 原始來源授權

MIT License

Copyright (c) 2026 iamraven-tw

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
