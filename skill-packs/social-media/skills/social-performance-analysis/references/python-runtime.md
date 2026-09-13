# Python 與時區資料

成效程式使用 Python 3.11+ 的 zoneinfo，但標準函式庫不包含 IANA 資料庫。
Windows 通常沒有系統 IANA 資料；缺少時回報 timezone_data_missing 並停止，不把指定時區替換成 UTC，也不連平台補資料。
[Python 官方說明](https://docs.python.org/3/library/zoneinfo.html) 建議跨平台程式宣告 tzdata。

## 準備與驗證

先用實際執行 helper 的 Python 檢查 UTC、Asia/Taipei 及設定指定的時區。
能讀既有系統資料庫就不必安裝；不能讀時，Agent 先告知下列固定來源，再於本次已授權範圍內安裝。

- 來源：[Python 官方 tzdata 2026.3](https://pypi.org/project/tzdata/2026.3/)，wheel 348168 bytes，Apache-2.0；IANA 資料依上游說明為公共領域。保留 wheel 內授權聲明。
- CPU 即可，不需 GPU、模型、帳號或管理員權限，無使用費；下載需要網路。
- 版本與 wheel SHA-256 在技能的 requirements.txt 固定；完整來源記錄在套件 install.manifest.toml。不下載浮動最新版或原始碼建置。
- 只在使用者選定的隔離 Python venv 安裝，不變更全域 Python、不覆寫既有可用環境。技能檔案安裝器本身仍完全離線。

以套件根為目前目錄，以下 PowerShell 範例由 Agent 執行；venv 位置需放在不提交的私人目錄：

```powershell
python -m venv .local/performance-venv
& .local/performance-venv/Scripts/python.exe -m pip install --require-hashes --only-binary=:all: --no-deps -r skills/social-performance-analysis/requirements.txt
& .local/performance-venv/Scripts/python.exe -c "from zoneinfo import ZoneInfo; print([ZoneInfo(k).key for k in ('UTC', 'Asia/Taipei', 'America/New_York')])"
```

macOS／Linux 使用同一 venv 的 bin/python。後續 collector、review 與測試子程序都須沿用這支 Python，不能另叫全域 python3。
更新時先修改固定版本／雜湊，在新 venv 驗證 UTC、臺北與美國夏令時間及完整虛構成效測試；舊 venv 保留供回復。
移除只處理經確認由本次建立的 venv，不刪私人報告或其他共用環境；拒絕下載時停止成效功能，其餘技能不受影響。

## Windows 私人資料

POSIX 0600 不等於 Windows ACL。執行前需確認私人工作區及產物的 DACL，只允許已授權主體存取。
程式沿用目錄 ACL，不自動修改使用者工作區權限；不能確認時停止保存私人資料並回報。
測試會在新建的隔離目錄設定僅目前使用者、SYSTEM 與 Administrators 可存取，再檢查證據／handoff 的繼承 ACL。
這只驗證指定測試目錄，不替任意工作區背書。
