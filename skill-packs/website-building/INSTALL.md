# 本機候選版安裝

目前安裝第一版全部五個技能：`website-setup`、`website-content-writing`、`website-design-preview`、`website-build` 與 `website-deploy`。安裝管理器不連網、不登入 Cloudflare、不安裝 Node 套件，也不建立任何網站專案。起始範本來源在技能包的 `template/`；manifest 指定將其完整複製至安裝後 `website-build/assets/template/`，與技能一起計算雜湊、更新、回復及可回復移除。畫廊讀取同層 website-build 的受管理範本，不依賴原下載位置或目前工作目錄。

舊版已安裝副本需先 status、預覽差異再明確 update；不要直接覆蓋私人已安裝檔。來源不同時 install 仍拒絕，人工修改過的技能或附帶範本都會擋下 update／remove。來源版維持根層 template 為唯一維護來源，不建立同步工具或 symlink；更新失敗會保留原副本。整個工作區搬移後 helper 的相對資產仍可用，但安裝狀態綁定原目標，須用新目標的正式 install/status 流程重新核對，不移植舊狀態假裝已驗證。

```mermaid
flowchart TD
    A[讀取 manifest 與本文件] --> B[唯讀預覽來源、目標與衝突]
    B --> C{使用者確認本機技能寫入}
    C -- 否 --> S[停止，不變更]
    C -- 是 --> D[安裝第一版五個技能]
    D --> E[雜湊與技能發現驗證]
    E --> F{要初始化工作區設定嗎}
    F -- 否 --> G[只回報已安裝層級]
    F -- 是 --> H[讀取既有設定當預設值並產生設定預覽]
    H --> I{使用者批次確認預覽}
    I -- 否 --> S
    I -- 是 --> J[寫入一般設定與非敏感狀態]
    J --> K[重新讀回並比對雜湊]
    K --> G
```

## 安裝前檢查

1. 閱讀 `AGENTS.md`、本文件、`install.manifest.toml` 與 `docs/verification-levels.md`。
2. 選擇明確的 Agent 技能目錄與位於技能掃描目錄外的狀態目錄。
3. 執行 `status` 做唯讀檢查，說明會新增的單一技能與所有同名衝突。
4. 取得使用者對「本機技能寫入」的明確確認後，才能執行 `install`。

範例路徑只使用佔位符：

```text
python3 scripts/manage_install.py status \
  --registration agents_workspace \
  --client-root <workspace>/.agents/skills \
  --state-root <local-state-root>
```

支援 `install`、`update`、`rollback`、`remove` 與 `status`。不同內容的同名入口、人工修改過的受管理技能、symlink 或損壞狀態一律停止；`remove` 只移至可回復隔離區。

## 工作區設定

`skills/website-setup/scripts/manage_workspace.py` 將預覽與寫入拆成兩個命令：

1. `preview` 驗證候選 JSON、列出差異並回傳預覽雜湊，不寫檔。
2. 使用者確認預覽後，`apply` 必須同時收到該雜湊與 `--confirm-write` 才能寫入。
3. 既有設定若在預覽後變動，雜湊會失效並停止。
4. 寫入後重新讀回；一般設定與非敏感狀態都明確標示不含憑證。

命令列旗標只是防誤用機制，不取代 Agent 在對話中取得使用者確認。

## 這個技能不做的事

Windows 本機測試以目前 interpreter 啟動 Python 子程序；假 Wrangler 的 .py 腳本可位於中文／空白路徑。部署 helper 解析 npx.cmd 並保留 Windows 必要環境；本次僅驗證 npx／npm 自身版本命令，未取得真實 Wrangler 登入或部署證據。沒有 symlink 建立權限的測試只針對 WinError 1314 明確略過，仍須在具權限 runner 補驗；Node 真實建置須另啟用 WEBSITE_NODE_ACCEPTANCE，不以略過當成功。

安裝與設定技能不會安裝 Node.js、Astro 或 Wrangler。`website-build` 會在使用者確認計畫後建立專案並執行 `npm ci`（從 npm registry 下載 lockfile 鎖定的套件），但不會建立 Cloudflare 帳號、不會執行 `wrangler login`、不會部署、不會購買或綁定網域。這些屬於 `website-deploy` 的外部關卡，各自需要預覽、明確授權與讀回驗證；`website-deploy` 只在使用者對同一份預覽明確授權後執行，且目前只有虛構測試，真實 Cloudflare 驗收尚未進行。
