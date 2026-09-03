# 公開合成 smoke test

這個 fixture 只包含為 AI Workflow Toolbox 撰寫的中性文字、詞級時間軸、EDL 與字幕詞彙資料，採根專案的 Apache-2.0 授權。

`tests/run_public_smoke_test.py` 會在暫存目錄以 FFmpeg 產生純色畫面與固定音調，再複製這些 JSON 檔完成正式字幕與渲染。repository 不包含真人聲音、實際影片、維護者品牌、集數、私人路徑或第三方媒體。

固定音調無法驗證語音辨識準確率；Qwen 的首次模型下載與實際語音轉錄保留給外部電腦驗收。
