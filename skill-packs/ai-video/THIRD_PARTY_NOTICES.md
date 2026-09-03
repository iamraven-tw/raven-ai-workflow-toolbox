# 第三方專案與模型

本文件記錄 AI 剪片工作流使用的外部元件。套件目前是可安裝的外部驗收候選版；所有外部元件仍依 manifest 固定來源與版本，未列入 manifest 的內容不得進入公開安裝流程。

## Video-Use

- 上游：https://github.com/browser-use/video-use
- 維護者：Browser Use 與貢獻者
- 用途：素材轉錄、逐字稿導向剪輯、EDL、渲染與 QA 的工程基礎
- 上游授權：MIT License
- MVP 整合方式：[Raven 非官方 fork v0.1.1](https://github.com/iamraven-tw/video-use/releases/tag/v0.1.1)
- Release commit：`da344098518230f69ff70f78a4860d4904e9e6cb`
- Release 資產：`raven-video-use-v0.1.1.tar.gz`
- SHA-256：`21c53a9001abfc30eb08ef2e3ad7931e5364c95e0110eb1dce57545466b2a9f8`
- Raven 補強：離線臺灣中文轉錄、繁體正規化、詞彙保護、中文語意斷句與相關驗證
- 未來方向：官方 Video-Use＋獨立 Raven 臺灣中文擴充套件

fork 發布時必須保留上游 LICENSE、著作權聲明、上游網址與修改說明。本 Toolbox 不直接複製完整 Video-Use 原始碼。

## uv 與 Python runtime

- uv 上游：https://github.com/astral-sh/uv
- 固定版本：官方 standalone `uv 0.12.7`，Apache-2.0 或 MIT
- Apple Silicon macOS 資產：https://github.com/astral-sh/uv/releases/download/0.12.7/uv-aarch64-apple-darwin.tar.gz
- SHA-256：`127ebdda7ad953cdf198e964b570ea5771b85467ea93eb7cb6d6f8e6f55408f3`
- Python 上游：https://github.com/python/cpython；Python Software Foundation License Version 2
- 固定 runtime：CPython `3.12.14`，由 uv 0.12.7 管理的 `python-build-standalone` build `20260825`
- Apple Silicon macOS 資產：https://github.com/astral-sh/python-build-standalone/releases/download/20260825/cpython-3.12.14%2B20260825-aarch64-apple-darwin-install_only_stripped.tar.gz
- SHA-256：`8b0f1fa71eab7ca644e482c631807a1116fa848491051cd1c8d9429491de63a6`
- 散布方式：Toolbox 與 fork 都不包含 uv 或 Python binary；Agent 必須先顯示來源、完整性資料與寫入位置，使用者同意後才下載，並保留 Python build 內附的第三方授權聲明

## Qwen3-ASR runtime 與模型

- 上游：https://github.com/QwenLM/Qwen3-ASR
- 維護者：Qwen 團隊與貢獻者
- Python runtime：`qwen-asr==0.0.6`，Apache-2.0；wheel SHA-256 `b9c55a38413298f3a990a4475467399daec6e8f4172363053fc42e2166c2dfd3`
- v0.1.1 runtime lock：Python 3.12.14、`torch==2.13.0` 與全部間接依賴；lock SHA-256 `1ced8120cefd86c1a7a5a3a4fd97f820cc872aef79b2bc5c9d8acf5fb216f046`
- ASR 模型：https://huggingface.co/Qwen/Qwen3-ASR-1.7B
  - 固定 revision：`7278e1e70fe206f11671096ffdd38061171dd6e5`
  - 授權：Apache-2.0
  - 模型 repository 約 4.7 GB
- Forced Aligner 模型：https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B
  - 固定 revision：`c7cbfc2048c462b0d63a45797104fc9db3ad62b7`
  - 授權：Apache-2.0
  - 模型 repository 約 1.84 GB
- 用途：離線語音辨識與詞級時間對齊
- 打包政策：不把模型權重、快取或虛擬環境提交到 Toolbox

模型來源、revision、授權與 runtime lock 已完成審查並隨 fork v0.1.1 公開；只有使用者明確選擇下載模型時才可取得權重。Toolbox 基本安裝不下載模型。

## OpenCC

- 上游：https://github.com/BYVoid/OpenCC
- 授權：Apache-2.0
- 用途：轉為臺灣繁體中文用字
- macOS MVP：Homebrew Core `opencc 1.4.2`，Apache-2.0
- 上游 source SHA-256：`8e5f5cf7fe195bd9b9be851adc9738c1ef7dc5c24441dd5878a56db4087a9a70`
- Homebrew formula commit：`9f847f78fd2f72e8e1d703b9124734feedaf7d2d`；formula SHA-256 `3f83c600e2000402ff5253a33bac7acc113db67ea6ac533b0d570161717ac214`
- Apple Silicon bottle SHA-256：macOS 14 `25644bad6d717f0aa881606c7bc0b1d2b741980805c0fd498158f0afbcc573da`；macOS 15 `2c624b20369b7b59f090e9843f63885f83dbcbaacca1a1ad14b83dcc5913eb2e`；macOS 26 `bbfaf3efb79e2c3f5c28164da7fac4392e37f92d2bd6c29f90b2f56e524f4e46`
- 散布方式：Toolbox 與 fork 不包含 OpenCC 本體；安裝時只有當 Homebrew metadata 與 manifest 相符才繼續

## CKIP Transformers

- 上游：https://github.com/ckiplab/ckip-transformers
- 授權：GPL-3.0
- 用途：建立正式中文字幕時，產生本次影片必要的中文詞彙與語意片語快取
- Python 套件：`ckip-transformers==0.3.4`；wheel SHA-256 `5e79fc0b4af7ad7742e8e10c091ce4fafb02f14ac0ae2ba3c9917875e1ff3c54`
- v0.1.1 runtime lock：Python 3.12.14、`torch==2.13.0`、`transformers==4.57.6` 與全部間接依賴；lock SHA-256 `a4f2c87aa2cdc6ef9dc317db2285ef1a0ebc32bc81d7b059a46c27b43ba03486`
- 固定模型：`ckiplab/bert-base-chinese-ws@60c22ced1c0ec221242906e8f9fbdf90fb560b77` 與 `ckiplab/bert-base-chinese-pos@c3f173670d4793f00ce5d23381cbeffa17e4e197`；兩份 PyTorch 權重合計約 814 MB
- 散布方式：不放入預設環境，也不散布套件或模型；一般預覽可延後安裝，但正式中文字幕必須在使用者同意後以隔離環境取得。不同意時只能停在預覽字幕

若未來散布包含 CKIP 的整合映像檔、安裝包或商業產品，發布者必須另外檢查 GPL-3.0 的散布義務。

## FFmpeg 與 libass

- FFmpeg 官方授權說明：https://ffmpeg.org/legal.html
- libass 上游：https://github.com/libass/libass；ISC License
- 用途：影片與音訊處理、成品輸出及中文字幕合成
- macOS MVP：Homebrew Core `ffmpeg-full 9.0.1_1`，GPL-3.0-or-later、keg-only；包含 `libass 0.17.5`，ISC License
- FFmpeg source SHA-256：`cf38e0e28c7e5605942c4a77755349b0145804a397af37eb1fb4c77cb237f635`；formula SHA-256 `bb93f7059f200431221f56f653ea4c269097264d938a51d1819bc2a9acf54afc`
- `ffmpeg-full` Apple Silicon bottle SHA-256：macOS 14 `a12d53f94b4e386a94b444ac5116671aed70f9fc732c779368fe1e98311beb42`；macOS 15 `84785c5d016434fdc036a7dea309e0cfef872de4bd7e86e428aa36b3cb280a72`；macOS 26 `4e281c5770f8fb5d8354ac82eec967155b95f70a49de85f2c6f63ff8b934ac7d`
- libass source SHA-256：`2dca25c0e0c837ddf00b52011b3f82cac1e4ddd3ad018227806b0c2288864acc`；formula SHA-256 `4ee934d7ece81986bc23a214237b37800b6a23fdaf57227a8efc6ef6efa984be`
- libass Apple Silicon bottle SHA-256：macOS 14 `a14b9e2407d406f58b7a83c7c22d9332b69ba68dca53dd7e61d7e0afa0468ed4`；macOS 15 `3600420037feb1403141c0f6d07f135dcd79649cafa420ace2750468981664ec`；macOS 26 `47e1f2d60c97628331593c00673e03d00e675c2462c1267f1e459ba17a41129e`
- 能力要求：實際 FFmpeg build 必須包含 libass 提供的 `subtitles` filter
- 散布方式：Toolbox 與 fork 不包含 FFmpeg 或 libass binary；安裝時只有當 Homebrew metadata 與 manifest 相符才繼續

以上版本與完整性資料已鎖定；隔離安裝、重複安裝、衝突、回復與移除測試已完成。鎖定 Homebrew 套件的乾淨系統實際安裝仍是外部電腦驗收項目，不能由 bottle 雜湊驗證推定為已通過。

## 公開 smoke test 素材

`tests/fixtures/synthetic-project/` 的文字、時間軸、EDL 與詞彙資料是為本 Toolbox 撰寫的中性測試內容，適用根專案 Apache-2.0。測試影片由 FFmpeg 在暫存目錄產生純色畫面與固定音調，不含第三方媒體或可辨識聲音，因此沒有額外素材授權。
