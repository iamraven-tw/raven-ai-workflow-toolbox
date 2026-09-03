# 第三方專案與概念來源

本文件記錄 `My Real Second Brain` 使用、整合或參考的外部專案。除非另有明確說明，本專案不會把這些專案的原始程式碼直接收進倉庫。

## Graphify

- 專案：https://github.com/Graphify-Labs/graphify
- 作者／維護者：Graphify Labs、Safi Shamsi 與貢獻者
- 本專案中的用途：本地知識圖譜、跨文件關聯、群聚分析、查詢與互動式 HTML 視覺化
- 整合方式：可替換的預設後端；使用者同意後才由 AI Agent 依 `install.manifest.toml` 安裝固定版本；上游通用技能不複製到本倉庫
- 候選固定版本：`graphifyy==0.9.35`；[PyPI 版本頁](https://pypi.org/project/graphifyy/0.9.35/)；[上游發行頁](https://github.com/Graphify-Labs/graphify/releases/tag/v0.9.35)
- 授權：目前產品主體採 Apache License 2.0；NOTICE 說明部分重新授權前的內容仍保留 MIT 條款
- 固定版本 NOTICE：https://github.com/Graphify-Labs/graphify/blob/v0.9.35/NOTICE
- 固定版本 LICENSE：https://github.com/Graphify-Labs/graphify/blob/v0.9.35/LICENSE
- 固定版本 MIT 歷史條款：https://github.com/Graphify-Labs/graphify/blob/v0.9.35/LICENSE-MIT

若未來把 Graphify 程式碼或衍生內容納入本倉庫，必須保留適用的 LICENSE、NOTICE、著作權與修改聲明。

## notebooklm-py

- 專案：https://github.com/teng-lin/notebooklm-py
- 作者／維護者：Teng Lin 與貢獻者
- 本專案中的用途：建立及管理 Notebook、加入來源、查詢資料與取得引用
- 整合方式：可替換的預設後端；使用者同意後才由 AI Agent 依 `install.manifest.toml` 安裝固定版本；上游通用技能不複製到本倉庫
- 候選固定版本：`notebooklm-py[browser]==0.8.0`；[PyPI 版本頁](https://pypi.org/project/notebooklm-py/0.8.0/)；[上游發行頁](https://github.com/teng-lin/notebooklm-py/releases/tag/v0.8.0)
- 授權：MIT License
- 固定版本 LICENSE：https://github.com/teng-lin/notebooklm-py/blob/v0.8.0/LICENSE

`notebooklm-py` 是非官方社群專案，使用可能隨時變動的未公開 Google 介面。本專案不代表 Google，也不保證外部介面持續相容。

若未來把 `notebooklm-py` 程式碼或其實質部分納入本倉庫，必須保留原始著作權與 MIT 授權聲明。

## LLM Wiki

- 原始筆記：https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- 作者：Andrej Karpathy
- 本專案中的用途：原始資料、持續演化 Wiki 與規則層的架構概念；以及 ingest、query、lint、index、log 等操作觀念
- 整合方式：概念啟發；本專案使用自己的文字、目錄與技能重新實作

原始 Gist 未標示標準開源授權。本專案不重製或重新授權該文件；README 與文件只做必要的來源標示及概念說明。

## Capacities

- 產品：https://capacities.io/
- 文件：https://docs.capacities.io/
- 維護者：Capacities Labs GmbH
- 本專案中的用途：物件、類型、屬性與關聯式知識整理的概念參考
- 整合方式：概念啟發

Capacities 是專有產品。本專案不包含其程式碼、介面、圖片、Logo、商標、範本或文件文字，也不代表與 Capacities Labs 有合作關係。
