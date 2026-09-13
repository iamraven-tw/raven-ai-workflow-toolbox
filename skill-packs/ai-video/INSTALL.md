# AI 剪片工作流安裝

本套件是**可安裝的外部驗收候選版**，不是正式支援版本。預期由具備本機檔案與終端機操作能力的 AI Agent 執行；使用者不需要自行判斷要下載官方 Video-Use 還是 fork。Agent 必須依 `install.manifest.toml` 取得固定的 [Raven Video-Use v0.1.1](https://github.com/iamraven-tw/video-use/releases/tag/v0.1.1)。

## Agent 必須遵守的界線

- 基本安裝不下載 Qwen 或 CKIP 模型，也不啟用付費 API。
- 下載、安裝 Homebrew 共用套件、建立技能入口及下載模型前，分別顯示來源、版本、容量、位置與回復方式，再取得使用者同意。
- 遇到未知來源、人工修改、實體檔案／目錄衝突或 Homebrew 版本不符時停止；不自動覆寫、升降版或移除。
- 不修改 shell 設定檔，不移動或刪除使用者的素材、逐字稿、EDL、字幕及成品。
- 安裝候選版不等於正式支援；最後仍要由使用者在另一臺電腦完成 D 節驗收。

## 1. 唯讀預檢

**先依作業系統分流：Windows x64 使用 [Windows 安裝契約](docs/windows-install.md)，不執行下列 Homebrew／symlink 步驟。macOS 14+ Apple Silicon 維持本文件的固定版本路線。** `compatibility_overlay` 另外鎖定共用程式的移植差異；原 Release 與 macOS 依賴雜湊維持不變。

Agent 先讀本文件、`install.manifest.toml` 與 fork 解壓後的 `install.md`，再檢查：

1. `uname -m` 必須是 `arm64`；macOS 主版本必須是 14 或更新。
2. 使用者指定的影片專案目錄，以下稱 `<target-workspace>`。
3. 可用磁碟空間、Homebrew、uv、Python、OpenCC、FFmpeg-full、libass、FFprobe 與既有技能入口。
4. `<target-workspace>/.agents/skills/video-use` 與 `<target-workspace>/.claude/skills/video-use`：不存在可新增；已指向本版可重跑；指向其他版本視為更新；實體檔案、實體目錄或失效連結都先停止。

建議的版本化位置如下。使用者可以指定其他位置，但 Agent 必須在下載前顯示實際絕對路徑：

```text
$HOME/Library/Application Support/ai-workflow-toolbox/
  components/video-use/v0.1.1/
  tools/uv/0.12.7/
  runtimes/python/

$HOME/Library/Caches/ai-workflow-toolbox/
  video-use/v0.1.1/asr/
  video-use/v0.1.1/ckip/
```

若系統已有不同版本的 `opencc`、`ffmpeg-full` 或 `libass`，本候選版停止安裝。Agent 只回報實際版本與需求，不替使用者改動共用 Homebrew 環境。

## 2. 顯示安裝計畫並取得同意

基本安裝計畫必須列出：

- Video-Use v0.1.1 Release 資產、MIT 授權、下載位置與 SHA-256。
- 必要時使用官方 standalone uv 0.12.7，以及 uv 管理的 CPython 3.12.14；兩者的資產網址與 SHA-256 以 manifest 為準。
- OpenCC 1.4.2、FFmpeg-full 9.0.1_1 與 libass 0.17.5 的 Homebrew 影響。
- 主要 Python 環境與離線 ASR runtime；此階段不下載模型權重。
- 要替哪些 Agent 建立哪一個專案層級技能入口。
- 更新時保留舊版本，失敗時把技能入口切回舊版本。

Qwen 兩個模型約 6.54 GB；CKIP 兩個模型權重合計約 814 MB，另有 Python 套件與快取。這兩組下載必須到實際需要時另外確認。

## 3. 取得並驗證 Video-Use

Agent 從 manifest 的 `release_asset_url` 下載 `raven-video-use-v0.1.1.tar.gz` 到新建的暫存目錄，先核對：

```text
SHA-256  21c53a9001abfc30eb08ef2e3ad7931e5364c95e0110eb1dce57545466b2a9f8
根目錄   raven-video-use-v0.1.1/
```

解壓前檢查封包不得含絕對路徑、`..` 跳脫項目或 symlink。核對成功後才解壓到新的版本目錄；若目標已存在，驗證 manifest 中的 `skill_sha256`、`uv_lock_sha256`、ASR lock 與 CKIP lock。相符才重用，不相符就停止，不覆寫。

## 4. 安裝固定 runtime 與系統能力

依 fork 的 `install.md` 執行平台、uv、Python、Homebrew、主要環境、ASR runtime 與驗證步驟，但有兩項 Toolbox 規則優先：

1. 略過 fork 文件的「註冊給目前的 AI Agent」一節，改用下一節的現行用戶端路徑。
2. ASR 與 CKIP runtime 使用本次計畫顯示的版本化快取位置；基本安裝不加 `--download-models`。

Homebrew 安裝前，Agent 要用即時 `brew info --json=v2` 核對 formula 版本與目前 macOS 對應的 bottle SHA-256。資料與 manifest 不一致就停止。若鎖定版本已安裝，驗證 `opencc --version`、`ffprobe -version` 及 `ffmpeg -hide_banner -h filter=subtitles`；若缺少套件，顯示 Homebrew 將改動的項目並另行取得同意後才安裝。

## 5. 註冊給 AI Agent

必須連結整個已驗證的 Video-Use 版本目錄，不能只複製 `SKILL.md`，因為技能會讀取相鄰的 `helpers/`、`references/` 與 lock 檔。

| 用戶端 | 專案層級入口 | 本機驗證狀態 |
|---|---|---|
| Codex | `<target-workspace>/.agents/skills/video-use` | 已用 Codex CLI 發現技能 |
| Claude Code | `<target-workspace>/.claude/skills/video-use` | 已用 Claude Code `/skills` 發現技能 |
| Google Antigravity | `<target-workspace>/.agents/skills/video-use` | 官方工作區路徑與結構已核對；實際登入後發現留給外部驗收 |

Codex 與 Antigravity 使用同一個 `.agents` 入口，不要建立兩份副本。建立連結後，先確認目標不存在，再建立指向版本目錄的 directory symlink，最後重新讀取連結、`SKILL.md` 與相鄰 helper。Toolbox 不使用舊的 `$HOME/.codex/skills` 路徑。

## 6. 自動驗證

Agent 至少執行：

1. fork 的 94 項自動測試與三個主要 helper 的 `--help`。
2. Python 3.12.14、uv 0.12.7、OpenCC、FFprobe 與 FFmpeg `subtitles` filter 的能力檢查。
3. 本套件的 `tests/validate_package.py`。
4. 本套件的 `tests/run_public_smoke_test.py`，以程式產生的色塊、音調及中性逐字稿完成正式字幕與渲染；不使用維護者素材。
5. 已選用 Agent 的實際技能發現；若用戶端需要登入而目前未登入，標示為外部驗收待辦，不假裝通過。

公開套件驗證入口的參數如下；`<ffmpeg-full-prefix>` 是通過前一步版本與能力檢查的實際 keg 路徑：

```bash
VIDEO_USE_DIR="<已驗證的 Video-Use v0.1.1 絕對路徑>"
python3 tests/validate_package.py
python3 tests/run_public_smoke_test.py \
  --video-use-dir "$VIDEO_USE_DIR" \
  --ffmpeg-bin "<ffmpeg-full-prefix>/bin/ffmpeg" \
  --ffprobe-bin "<ffmpeg-full-prefix>/bin/ffprobe"
```

公開 smoke test 不含可辨識的真人聲音，也不取代 Qwen 的語音辨識驗收。下載固定 Qwen 模型並以使用者有權使用的影片完成轉錄，屬最後外部電腦驗收。

## 7. 第一次轉錄與正式中文字幕

第一次需要離線轉錄時，Agent 先說明兩個固定 Qwen 模型、revision、Apache-2.0 授權、約 6.54 GB 下載量與快取位置，取得同意後才依 fork `install.md` 加上 `--download-models`。

第一次輸出正式臺灣繁體中文字幕時，CKIP 是必要條件。Agent 先說明 GPL-3.0、隔離 runtime、兩個固定 model revision、約 814 MB 權重與快取位置，取得同意後才安裝並產生本次影片的詞彙快取。使用者不同意時，只能交付清楚標示的預覽字幕，不能宣稱正式字幕完成。

## 8. 重跑、更新、回復與移除

- **重跑：** 先重驗 Release 與 lock 雜湊；相同版本與相同技能連結保留。`uv sync --frozen`、ASR setup 與 CKIP `uv pip sync --require-hashes --strict` 只依 lock 補回缺件，不追最新版。
- **更新：** 新版安裝到另一個版本目錄，全部驗證通過後，才在使用者同意下把技能連結切向新版；舊版保留。
- **回復：** 新版失敗時，只把已確認的 symlink 切回仍保留且已驗證的舊版。runtime、模型與影片工作區不跟著移動。
- **移除技能：** 先以唯讀方式確認 symlink 的實際目標，再經同意只 `unlink` 該入口。實體目錄或未知連結一律停止。
- **移除資料：** 版本目錄、ASR runtime、CKIP runtime、模型快取及 Homebrew 套件是不同目標，必須逐項列出、逐項取得同意。永遠不刪除影片素材、逐字稿、EDL、字幕或成品。

## 9. 完成狀態

安裝報告只記錄版本、路徑、checksum、建立的技能入口、驗證結果與仍待外部驗收項目；不保存 Token、Cookie、帳號內容、素材名稱、逐字稿或影片雜湊。

本機自動驗證完成後，狀態為「已安裝的外部驗收候選版」，不是「正式支援」。使用者之後在另一臺電腦完成 [`tests/acceptance-checklist.md`](tests/acceptance-checklist.md) D 節，才決定是否把該環境加入正式支援矩陣。
