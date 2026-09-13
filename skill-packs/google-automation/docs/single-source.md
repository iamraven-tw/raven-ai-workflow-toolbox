# Google 技能包單一來源政策

0.2.0 起，原 Learn-GAS 的四個技能、共用術語、範例、教材、工具與測試由 raven-ai-workflow-toolbox 持續維護。舊 repository 是歷史來源，不再下載、同步或回填。

歷史基線：Learn-GAS `7d50a7bfcfbe41ea9d88c2aef8f11200871433a3`，Git tree `ef6e45626d59ae18745eb5c7245de0b3f2e48cc9`。這些值不隨 Toolbox 日後的功能修改改寫。

原程式、技能與衍生內容保留 MIT 授權；[完整聲明](../LICENSE.learn-gas)及各技能的 LICENSE 隨安裝提供。路由與安裝器沿用 Apache-2.0。

`bundle.lock.json` 記錄五個技能與共用術語的雜湊。維護者完成來源修改與版本更新後，執行 `PYTHONDONTWRITEBYTECODE=1 python3 scripts/lock_bundle.py` 及本包驗證。安裝器只驗證並複製，不連線舊來源。

所有 Issue、Pull Request 與後續發行都集中至 [raven-ai-workflow-toolbox](https://github.com/iamraven-tw/raven-ai-workflow-toolbox)。兩個舊專案只做最後搬遷公告與封存，保留既有 commit、tag 和網址。
