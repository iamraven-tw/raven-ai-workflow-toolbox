# 第三方聲明

本技能包本身只包含 Toolbox 自有的安裝管理器、測試與文件，全部只使用 Python 標準函式庫，不綑綁、不下載、不安裝任何第三方程式碼。

## 上游技能包

| 項目 | 內容 |
|---|---|
| 名稱 | agent-inventory |
| 上游 | <https://github.com/iamraven-tw/agent-inventory> |
| 固定版本 | tag `v0.2.1`，commit `c162b0adce4d1519b60f76de15bc00df85d611ce` |
| Tree | `9ccdd73635bb74b95e6d2a111c994758602f5a23` |
| 授權 | MIT，LICENSE 的 SHA-256 為 `8e30b10020d068a10bf4376e97df27bf34c9a52b01de5c3d0f6e26f594353dac` |
| 是否綑綁 | 否。由 Agent 在使用者同意後從上游 clone，安裝器只核對雜湊並複製其中六個技能目錄 |
| 執行需求 | Python 3.9 以上標準函式庫；不安裝任何套件 |

上游的 MIT 授權文字隨 clone 一併取得，不在本 repository 重製。安裝器複製的六個技能目錄各只有一個 `SKILL.md`，內容維持上游原樣，不改寫。

## 上游在執行時的外部資源

| 項目 | 用途 | 說明 |
|---|---|---|
| CodeMirror 6（透過 `esm.sh`） | 網站抽屜的「在網頁上編輯」 | 由使用者的瀏覽器在開啟編輯器時載入，屬對外請求；離線時上游退回內建純文字編輯器。程式碼不包含在本技能包或上游 repository 內 |

上游的本機網站只綁定 `127.0.0.1`，掃描與摘要不連網，也不上傳任何內容。

## 商標

Claude Code、Codex、Google Antigravity、Cursor、OpenClaw、Hermes Agent 等名稱僅用於標示被盤點的工具，不代表相關公司背書。
