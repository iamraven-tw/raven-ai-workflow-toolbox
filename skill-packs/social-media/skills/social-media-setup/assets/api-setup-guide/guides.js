"use strict";
// 共用的是教學內容，不是授權狀態。已讀、切換步驟均不得寫成 API 驗證成功。
(() => {
const meta="https://developers.facebook.com/apps/";
const cloud="https://console.cloud.google.com/";
const waitingMeta="這部分尚未完成全流程實拍。文字依官方文件整理；選項不同時先停下來，不自行改選相近項目。";
const waitingGoogle="這一步仍缺完整實拍；請依文字與官方文件操作。Google Cloud 本輪已恢復可讀，但尚未完成所有畫面補拍。";
const sources={
  igMedia:{title:"Meta：Instagram 媒體修改與刪除限制",url:"https://developers.facebook.com/documentation/instagram-platform/reference/instagram-media"},
  threadsDelete:{title:"Meta：Threads 刪除自己的貼文",url:"https://developers.facebook.com/documentation/threads/posts/delete-posts"},
  facebookPosts:{title:"Meta：粉絲專頁貼文管理",url:"https://developers.facebook.com/documentation/pages-api/posts"},
  googleExpiry:{title:"Google：OAuth 權杖到期條件",url:"https://developers.google.com/identity/protocols/oauth2"},
  youtubeUpload:{title:"Google：影片上傳與未審核專案限制",url:"https://developers.google.com/youtube/v3/docs/videos/insert"},
  googleScopes:{title:"Google：OAuth 權限範圍",url:"https://developers.google.com/identity/protocols/oauth2/scopes"},
  googleSecrets:{title:"Google：管理 OAuth 用戶端與一次性秘密顯示",url:"https://support.google.com/cloud/answer/15549257"},
  metaCreate:{title:"Meta：建立應用程式",url:"https://developers.facebook.com/documentation/development/create-an-app"},
  facebook:{title:"Meta：Pages API 入門",url:"https://developers.facebook.com/documentation/pages-api/getting-started"},
  instagram:{title:"Meta：Instagram Login",url:"https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login"},
  igSetup:{title:"Meta：設定 Instagram 應用程式",url:"https://developers.facebook.com/documentation/instagram-platform/create-an-instagram-app"},
  threads:{title:"Meta：Threads API 入門",url:"https://developers.facebook.com/documentation/threads/get-started"},
  threadsSetup:{title:"Meta：Threads 使用案例",url:"https://developers.facebook.com/documentation/development/create-an-app/threads-use-case"},
  youtube:{title:"Google：YouTube 授權",url:"https://developers.google.com/youtube/v3/guides/authentication"},
  youtubeStart:{title:"Google：YouTube Data API 入門",url:"https://developers.google.com/youtube/v3/getting-started"},
  analytics:{title:"Google：YouTube Analytics 授權",url:"https://developers.google.com/youtube/reporting/guides/registering_an_application"},
  consent:{title:"Google：OAuth 同意畫面設定",url:"https://developers.google.com/workspace/guides/configure-oauth-consent"},
  clients:{title:"Google：建立憑證",url:"https://developers.google.com/workspace/guides/create-credentials"},
  desktop:{title:"Google：桌面應用程式 OAuth",url:"https://developers.google.com/youtube/v3/guides/auth/installed-apps"}
};
const step=(title,intro,actions,expected,help,source,extra={})=>({title,intro,actions,expected,help,source,owner:"由你操作；Agent 提供資料與檢查",...extra});
function prepare(platform,source,extra=[]) {
  return step("開始前，先備齊資料",`${platform} 的帳號登入、應用程式設定與 API 授權是不同的事情。先確認要連接的帳號和功能。`,[
    "告訴 Agent 要管理的帳號。自用管理範圍可包含內容新增、修改、刪除、單篇與帳號成效、留言及私訊；已有決定就沿用，不必重新填問卷。Agent 要分開說明平台支援、工具已實作及尚未驗證的功能。",
    ...extra,
    "先讓 Agent 檢查既有連線；可用就直接接續工作，不重建 App 或重複取得秘密。只缺部分設定時，跳到該步驟。",
    "請 Agent 列出本次必要權限、用途與安全儲存入口。只有選定的授權方式需要回呼時才準備網址；不要求先設定廣告、商店或其他未選功能。"
  ],"你知道要設定哪個帳號、採哪條登入路線，以及本次允許的功能。","不要因為教學有列出全部平台，就替自己建立全部平台的 App。只做你已選擇的部分。",source,{owner:"你確認目標；Agent 整理設定清單"});
}
function createMeta(useCase) {
  const overview=useCase.includes("Instagram")?"instagramCreateOverview":useCase.includes("粉絲專頁")?"facebookCreateOverview":"metaCreateOverview";
  return step("建立或選用 Meta App","App 是這次整合的設定容器，不等於你的社群帳號。",[
    "開啟 Meta App 主控板，由本人登入、註冊開發人員並完成必要驗證。已有相符 App 時先沿用。",
    "需要新 App 時，按「建立應用程式」，填入自己的 App 名稱與聯絡信箱，再按「繼續」。不要照抄示例名稱或他人的信箱。",
    `切換左側「內容管理」，選擇「${useCase}」，再按「繼續」。只選本次需要的平台。`,
    "依用途選擇適用的商家資產管理組合；若畫面允許且本次不需連結，可選「我還不想連結商家資產管理組合」。不要為了照圖而連結別人的商家。",
    "閱讀「要求」後按「下一步」，在總覽核對資料。最終「建立應用程式」包含同意條款，必須由本人閱讀並操作。一般資料填寫與換頁可由已獲授權的 Agent 代辦。"
  ],"本人完成最終建立後，主控板顯示預期的 App 和使用案例；到達總覽並不代表已建立。","新版與舊版建立流程可能不同。找不到使用案例時，讓 Agent 先核對官方路線；不要先建空白 App 或刪掉舊 App。", "metaCreate",{entry:meta,owner:"Agent 可代填一般資料；本人登入、驗證與同意條款",images:["metaCreateDetails","metaCreateCases","metaCreateBusiness","metaCreateRequirements",overview,"metaDashboard"],capture:"已拍到建立精靈五個階段，但未送出最終建立。商家與要求圖以 Threads 為共用示例；三平台已各自走到總覽，皆暫不連結商家。這次顯示無要求，不代表其他用途免審查。最後一張是另一個既有 App 的主控板，並非這次示例的建立結果。"});
}
function secret(source,route="") {
  const youtube=source==="desktop", threads=source==="threadsSetup", ig=source==="igSetup"&&route!=="facebook_login";
  const credential=youtube?"OAuth Client ID 與 Client Secret（不是 API key）":threads?"Threads App ID 與 Threads App Secret":ig?"Instagram App ID 與 Instagram App Secret":"Meta App ID 與 App Secret";
  const locate=youtube?[
    "開啟 Google Cloud → Google Auth Platform →「用戶端」，點選本次的電腦版用戶端。需要的是 OAuth 憑證，不是 API 和服務中的 API key。",
    "新建用戶端時，完整 Client Secret 只在建立當下顯示。先讓 Agent 備妥安全終端機，再由你取得並保存；不要先關閉一次性顯示畫面。",
    "既有用戶端頁只能核對 Client ID 與密鑰狀態，無法重新查看或下載完整舊秘密。已有保存值就沿用；遺失時告訴 Agent 評估新增密鑰的影響，不自行刪除、重設或按 Add secret。"
  ]:threads?[
    "開啟 Meta App 主控板 →「使用案例」→「存取 Threads API」→「設定」。",
    "找到上方「Threads 應用程式編號」與「Threads 應用程式密鑰」。需要時由你按右側「顯示」並完成本人驗證；不要誤用一般 Meta App 的密鑰，也不要按下方產生存取權杖。"
  ]:ig?[
    "開啟 Meta App 主控板 →「使用案例」→ Instagram API →「含有 Instagram 登入的 API 設定」。",
    "找到上方「Instagram 應用程式編號」與「Instagram 應用程式密鑰」，需要時由你按右側「顯示」並完成本人驗證。這組不是一般 Meta App 的密鑰，也不是下方產生的存取權杖。"
  ]:[
    "開啟 Meta App 主控板 → 左側「應用程式設定」→「基本資料」。",
    "找到頁面最上方「應用程式編號」與「應用程式密鑰」，需要時由你按右側「顯示」並完成本人驗證。Facebook 與 Instagram 的 Facebook Login 路線使用這組，不使用下方 Threads 密鑰。"
  ];
  return step("本人輸入並儲存秘密",`本路線需要：${credential}。已有可用憑證就沿用；已複製好秘密可直接從「我準備好輸入了」接續，不必重開後台。`,[
    ...locate,
    "已複製秘密後，只告訴 Agent「我準備好輸入了」，不要貼出秘密。Agent 會開啟安全的終端機視窗，明確說明本次要輸入哪一項憑證。",
    "在終端機貼上並按 Enter 完成確認儲存；輸入不回顯，也不另要求你重複確認。不要貼進聊天、教學網頁、一般設定檔或命令列參數。",
    "告訴 Agent「已輸入完畢」。Agent 檢查不含秘密的儲存結果，再接續已授權的驗證；不要求你自己執行後續指令。"
  ],"終端機只顯示憑證類別與儲存結果；Agent 分別回報保存是否成功、平台驗證是否通過。","沒有可互動且不回顯的終端機，或系統憑證庫不可用時，先停在取得秘密之前。OAuth 程式交換、刷新產生的 Token 可在已授權範圍內直接保存，不需要你再複製或確認。",youtube?"googleSecrets":source,{owner:"Agent 開啟終端機；本人貼上並按 Enter；Agent 接續驗證",entry:youtube?cloud+"auth/clients":meta,images:youtube?["youtubeDesktop","youtubeSecretLocation"]:[threads?"threadsSecretLocation":ig?"instagramSecretLocation":"metaSecretLocation"],capture:youtube?"已實拍建立表單與舊密鑰無法再顯示的管理頁；建立當下的一次性秘密畫面尚未拍攝，不為補拍產生真實憑證。":null});
}
function authorize(source,platform) {
  return step("本人同意，再由 Agent 驗證",`完成後台設定後，才進行 ${platform} 的使用者授權。`,[
    "請 Agent 先核對回呼、系統憑證庫及本次授權範圍。後台 Secret 由你貼入終端機；OAuth 程式產生的 Token 由程式直接保存，不增加逐次人工確認。",
    "由你開啟 Agent 提供的短期授權連結，核對帳號、資源與權限後親自同意。出現未列明權限或帳號不符時不要繼續。",
    "程式將交換、刷新產生的 Token 存入系統憑證庫並讀回比對。Agent 接續正式 API 唯讀檢查，只回報帳號是否相符、可用功能與缺口，不顯示秘密。"
  ],"Agent 分別回報後台設定、OAuth、唯讀驗證與仍待處理事項；不只是說「已登入」。","授權逾時或結果不明時，請 Agent 查既有狀態，不重用授權碼、不重新建立 App、不嘗試發布測試貼文。",source,{owner:"本人同意 OAuth；程式保存 Token；Agent 驗證",...(platform==="Instagram via Facebook Login"?{images:["instagramConsentAccount","instagramConsentPermissions"],capture:"已實拍 Facebook Login 的 IG 帳號選擇與基本讀取權限確認；帳號、名稱與識別資料已遮蔽。只選目前帳號，不包含所有未來帳號。本圖尚未送出最終授權，亦非發布、留言、私訊或刪文的完整權限驗收。"}:{})});
}
function metaPermissions(source,items,image) {
  return step("依確認清單設定權限","有權限不代表 Agent 可以立即發布、回覆或刪除。",[
    "在 App 的「使用案例」進入對應案例的自訂頁面，查看權限與功能。",
    `逐項對照 Agent 已說明的權限清單：${items}。只加入已同意的項目；遇到強制相依權限，先讓 Agent 說明影響。`,
    "核對儲存後的清單。需要應用程式審查或商家驗證的功能，先標記待處理，不為了測試直接發布 App。"
  ],"設定的權限與本次確認範圍一致；測試角色與一般外部使用者的資格分開記錄。","官方總表包含本技能尚未實作的功能；不要全部勾選。權限名稱不符或被迫擴權時，先停下來核對。",source,{entry:meta,image,capture:image?null:waitingMeta});
}
function callback(source,direct=false) {
  return step("需要重新授權時：設定回呼","本頁適用目前套件的 Meta 授權碼流程，不是所有自用操作的共同前提。已有可用連線時跳過；採其他官方取權杖方式時，先由 Agent 確認套件是否支援，不自行略過必要驗證。",[
    direct?"開啟「含有 Instagram 登入的 API 設定」，展開「設定 Instagram 商家登入」，按「商家登入設定」。":source==="threadsSetup"?"在「存取 Threads API」使用案例中，開啟左側「設定」。":"展開側欄「商家專用 Facebook 登入」，選擇「快速入門」上方的第一個「設定」。下方同名項目是組態管理，不是回呼設定。",
    "貼上 Agent 已準備並檢查可用的 HTTPS 回呼網址，完整保留路徑與結尾；不可拿別人的範例網址代替。",
    "取消授權、資料刪除或隱私權網址，只在這條路線的實際平台要求適用時設定；由 Agent 說明原因與準備方案，不因範例有欄位就全部照填。保存後重新載入核對。"
  ],"後台保存的回呼網址與 Agent 接收器預期完全一致。","尚未有可用 HTTPS 入口，或需要新網域、主機、付費服務時先停下來。OAuth 回呼和 Webhook 通知入口不是同一件事。",source,{entry:meta,image:direct?"instagramCallback":source==="threadsSetup"?"threadsSettings":"facebookCallback"});
}
// 先揭露能力與執行器缺口，避免走完申請才發現無法完成使用者目標。
function capabilities(platform,source,items) {
  return step("確認功能與使用條件","官方提供 API，不代表這份套件已完成每一項操作。以下是本次自用管理的選路依據。",items,
    "Agent 在申請前列出可用、待實作、待驗證及平台不支援的項目。",
    "不要為驗證設定而試發、試刪或傳送私訊。留言與私訊先採按需讀取；只有確定需要即時通知時才另評估 Webhook，不先要求部署網站或建立試算表。",source,{owner:"Agent 說明限制；你確認仍要啟用的功能"});
}
function tokenHandoff(platform) {
  const threads=platform==="Threads";
  return step(threads?"本人取得並安全輸入存取權杖":"取得並安全輸入 Page Token",`${!threads?"已選擇 HTTPS OAuth 者跳過此頁；不要兩條都做。":""}${platform} 此分支交接的是 ${threads?"Threads User Access Token":"Facebook Page Access Token"}，不是 API key，也不能只交 App Secret。`,[
    "先告訴 Agent「我準備好輸入了」。Agent 必須先確認原生憑證庫、隱藏輸入入口與相容匯入程式均可用；未備妥就停在取得秘密之前。",
    threads?"在 Meta App → 使用案例 → 存取 Threads API → 設定，找到「用戶權杖產生器」。由本人選擇已接受邀請的 Threads 帳號，核對權限並完成同意後複製權杖。不要按上方 App Secret 的顯示鈕來代替。":"僅在 Agent 確認相容匯入器已完成時，才使用官方 Graph API Explorer 或 App 後台的專頁權杖入口；核對自己的 App、目標專頁與已同意權限。不要把一般 User Token 當 Page Token。",
    "由 Agent 開啟安全終端機，你貼上並按 Enter 確認儲存，再告訴 Agent「已輸入完畢」。不要貼進聊天、網頁或命令列參數；Agent 不讀取剪貼簿、不顯示秘密。",
    "Agent 只讀取非敏感儲存收據並接續唯讀 API 驗證，核對帳號、權限及到期狀態。保存成功不是所有管理功能都已完成。"
  ],"本人保存後，Agent 分別列出憑證儲存與 API 讀取結果。",
  threads?"後台 Token 先由你存入原生庫；匯入器再於可信程序內驗證並整理同一筆已保存 Token，不從瀏覽器搬運秘密。身分或權限不符時停止，不自動重取。":"此流程另需同一 App 的 App Secret 驗證權杖所屬 App；兩項秘密都先由本人安全輸入。不開 HTTPS 回呼，也不自動覆寫既有連線。",
  threads?"threadsSetup":"facebook",{owner:"Agent 備妥終端機；本人取得、貼上與按 Enter；Agent 驗證",entry:threads?meta:"https://developers.facebook.com/tools/explorer/",images:threads?["threadsTokenLocation"]:["facebookExplorer"],capture:threads?"已沿用去識別化實拍標出下方權杖產生器入口；本人同意、產生後與保存結果尚未補拍。安全入口及匯入器未備妥前不要按產生。":"前一步已補帳號、專頁選擇、權限確認與連結結果實拍。此頁舊選單只供辨識入口，不代表其捷徑可用；本次尚未完成 Page Token 取得與原生保存驗收。"});
}
function facebookConsentGuide() {
  return step("選擇帳號、專頁與授權範圍","先備妥安全輸入入口，再開始授權。以下實拍示範兩項讀取權限，不是完整管理權限清單。",[
    "確認 App 已加入「管理粉絲專頁的所有內容」。從該 App 的測試整合工具開啟 Explorer，確認 App 正確，在 Permissions 加入本次已確認權限；每項都必須實際出現在已選清單，再按 Generate Access Token。",
    "核對身分確認頁的帳號與 App，正確才按「繼續」。專頁範圍選「選擇只能使用目前的粉絲專頁」，只勾選本次要管理的資產；不要預設涵蓋所有未來專頁。",
    "核對權限確認頁與所選專頁。本圖只有閱讀內容、顯示專頁清單；若需要貼文、留言或私訊管理，須在前一步加入相應已確認權限，不能把這張圖當完整授權。核對後按「儲存」。",
    "看到連結成功後按「知道了」。回到 Explorer 若顯示「用戶權杖」，仍不是 Page Token。下拉選單列出已授權專頁時才選取目標；秘密不要貼進對話或截圖。",
    "若專頁清單為空，先以 GET me/permissions 核對權限為 granted，再以 GET me/accounts?fields=id,name 查清單。必要時用 GET 專頁ID?fields=id,name 核對指定專頁；空清單與直接讀取成功可同時發生，原因仍需查驗，不重建 App 或擴權。這些查詢不要求回傳 access_token。"
  ],"已確認授權帳號、專頁與範圍；Page Token 的取得、安全保存與有效性另外驗證。","若捷徑回報 Invalid Scopes: manage_pages，不重按同一捷徑；回到 App 專屬 Explorer 的 Permissions 核對當前權限。直接讀到專頁名稱不證明擁有管理權限，也不能替代 Page Token 驗證。","facebook",{owner:"本人核對與同意；Agent 提供權限清單及安全入口",images:["facebookConsentIdentity","facebookConsentPages","facebookConsentPermissions","facebookConsentConnected"],capture:"使用者提供的真實授權截圖，私人區域已不透明遮蔽。已到連結成功；未拍攝秘密、未證明取得 Page Token 或完成原生保存。"});
}
// Facebook 匯入不需要回呼；App Secret 仍是本套件驗證權杖的相依條件。
function facebookRoute(importToken) {
  return {platform:"facebook",id:importToken?"page_token":"pages",label:importToken?"Page Token（免回呼匯入）":"HTTPS OAuth（備援路線）",description:importToken?"先沿用有效連線；新匯入需本人安全輸入 Page Token 與同一 App Secret，再由程式驗證。不需要設定 HTTPS 回呼。":"僅在明確選定授權碼流程時使用；需要 HTTPS 接收器及 Meta App Secret。本人同意 OAuth 後，程式直接保存 Token。",steps:[
    prepare("Facebook","facebook",["確認你的 Facebook 帳號具有目標粉絲專頁所需的工作權限；登入社群網站本身不代表可以管理該專頁。"]),
    capabilities("Facebook","facebookPosts",["官方支援專頁發文、刪文與修改；修改限本 App 建立的貼文，不保證能修改所有舊文章。留言可讀取、回覆、隱藏及刪除；不能任意改寫別人的留言。","私訊使用 Messenger 的 Page Token 與 pages_messaging，受收件者先互動、一般 24 小時回覆時限及平台例外規則限制。單篇成效使用該貼文的 insights，不拿帳號統計冒充。","套件有發布、留言讀取／回覆、私訊與帳號成效基礎；文字修改與已發布貼文刪除已接入預覽、一次送出與獨立讀回，使用前由 Agent 檢查連線與操作權限。留言進階管理與 Meta 單篇成效尚待補齊。","先沿用有效連線；匯入新 Page Token 另需同一 App Secret 驗證來源。匯入不設定 HTTPS 回呼；只有明確選定授權碼路線才設定回呼，不能一律要求架設網站。"]),
    createMeta("管理粉絲專頁的所有內容"),
    metaPermissions("metaCreate","列出專頁 pages_show_list、讀取互動 pages_read_engagement、使用者內容 pages_read_user_content；貼文 pages_manage_posts、留言 pages_manage_engagement、成效 read_insights、私訊 pages_messaging。現有私訊執行器另要求 pages_manage_metadata，Agent 須揭露此相依與用途，不把它等同必須部署 Webhook","facebookPermissions"),
    step("確認測試角色與專頁","App 角色和粉絲專頁權限都要具備。",["在 App 角色頁確認本次登入者具有適用的管理員、開發人員或測試角色。","新增測試人員時，由對方本人接受邀請；粉絲專頁本身的管理權限也要另外確認。","若需服務未具備 App 角色的外部使用者，請 Agent 列出審查與驗證需求，再安排後續處理。"],"測試人員已接受邀請，且能操作指定專頁。","看不到專頁時不要先擴大全部商家權限。先檢查登入帳號、專頁工作權限、邀請與授權選取資源。","facebook",{entry:meta,image:"metaRoles",capture:"目前有 App 角色頁實拍；Facebook 邀請接受與粉絲專頁工作權限的畫面尚未補齊。"}),
    ...(importToken?[secret("facebook"),facebookConsentGuide(),tokenHandoff("Facebook")]:[callback("metaCreate"),secret("facebook"),authorize("facebook","Facebook Pages")])
  ]};
}
const routes=[
  facebookRoute(true),facebookRoute(false),
  {platform:"instagram",id:"instagram_login",label:"Instagram Login（不含 API 刪文）",description:"不需 Facebook 專頁，但無法涵蓋本次完整管理目標；僅在接受限制或沿用既有連線時選取。",steps:[
    prepare("Instagram","instagram",["確認 Instagram 是商家或創作者專業帳號。這條路線不必先連接 Facebook 粉絲專頁。"]),
    capabilities("Instagram","igMedia",["這條路線可申請發布、留言、成效與私訊能力，但目前官方媒體刪除端點限 Facebook Login。若必須由 API 刪文，改選 Facebook Login 主線；不要在這裡加上不相容的 instagram_manage_contents。","官方媒體更新只有 comment_enabled 等支援欄位，不能承諾可修改已發布 caption。套件目前也沒有完整留言隱藏／刪除及單篇成效執行器。","私訊限符合平台規則的既有互動，不是任意主動群發。已有直接登入連線先保留，由 Agent 說明差異，不擅自遷移或刪掉憑證。"]),
    createMeta("管理 Instagram 的訊息和內容"),
    step("選擇 Instagram 登入設定","不要將兩種 Instagram 登入路線的 ID、Secret 和 Token 混用。",["在 App 的 Instagram 設定中選擇「含有 Instagram 登入的 API 設定」。","若你的舊版主控板是產品列表，在 Instagram 產品按「設定」。","核對這條路線的 Instagram App ID；秘密先不顯示，等安全輸入入口準備好。"],"設定頁明確標示 Instagram Login 路線。","若原本工作區已使用 Facebook Login，先保留原路線，不自行遷移憑證。","igSetup",{entry:meta,image:"instagramLogin"}),
    metaPermissions("igSetup","instagram_business_basic、instagram_business_content_publish、instagram_business_manage_comments、instagram_business_manage_insights、instagram_business_manage_messages 等依選定功能提出","instagramPermissions"),
    callback("igSetup",true),
    step("加入測試 Instagram 帳號","新增帳號和授權必須由本人處理。",["先在「應用程式角色」→「角色」按「新增用戶」，選擇 Instagram 測試人員；再依 Instagram 設定的新增帳號入口接續。","由本人登入並完成必要測試邀請；若後台進入產生 Token 畫面，先確認安全保存入口已備妥。","目前官方測試帳號流程要求帳號公開；不符合時先停止，不由 Agent 改變帳號隱私設定。"],"目標測試帳號出現在正確 App 的 Instagram 設定中。","不要把加入帳號成功當成留言、成效或私訊都已可用。這些功能之後還要各自驗證。","igSetup",{entry:meta,images:["metaRoles","instagramAddRole"],capture:"已拍到角色入口與選擇視窗；Instagram 本人的邀請接受、登入與帳號加入流程尚未全程實拍。"}),
    secret("igSetup"),authorize("instagram","Instagram Login")
  ]},
  {platform:"instagram",id:"facebook_login",label:"Facebook Login（含 API 刪文的主線）",description:"專業帳號需連結 Facebook 粉絲專頁；需要透過 API 刪文時選擇這條路線。",steps:[
    prepare("Instagram via Facebook","igSetup",["確認 Instagram 專業帳號已連到目標 Facebook 粉絲專頁，而且本次 Facebook 登入者具備所需專頁權限。"]),
    capabilities("Instagram","igMedia",["官方可發布、刪除自己的適用媒體、管理留言及查成效；不能用媒體更新 API 改寫已發布 caption。刪除不包含廣告媒體，也不能只刪輪播中的一張。","刪文必須使用 Facebook Login 的 Facebook User Token，並具備 instagram_basic 與 instagram_manage_contents；其他現有功能使用相應 Page Token。兩種 Token 不可混用。","套件已補 Facebook Login 刪文執行器；授權包含 instagram_manage_contents 時另存並驗證 Facebook User Token，其他功能仍使用 Page Token。目前涵蓋貼文、Reels 與整組輪播，不含限時動態。舊連線缺少 User Token 時需重新授權，不以 Page Token 代替。留言進階管理與單篇成效仍待補齊。","私訊採 Instagram 訊息能力，只回覆符合平台規則的互動。先按需查詢留言／對話，不強制 Webhook；有即時通知需求才另評估。"]),
    createMeta("管理 Instagram 的訊息和內容"),
    step("改選含 Facebook 登入的設定","此路線使用 Facebook 授權與對應的 Page Token，不使用直接 Instagram Login 的 Token。",["在 Instagram 產品設定中，選擇「含有 Facebook 登入的 API 設定」。","核對已連結的專頁與 Instagram 專業帳號。","請 Agent 依這條路線重新核對所需權限及回呼；不要直接複製 instagram_business_* 的清單。"],"路線、專頁與 Instagram 帳號關係一致。","看不到連結帳號時，先由本人檢查專頁連結與帳號權限；不要改走直接登入來繞過錯誤。","igSetup",{entry:meta,image:"instagramFacebookLogin"}),
    metaPermissions("metaCreate","instagram_basic、pages_show_list、pages_read_engagement；發布 instagram_content_publish、刪文 instagram_manage_contents、留言 instagram_manage_comments、成效 instagram_manage_insights、私訊 instagram_manage_messages。現有私訊執行器另要求 pages_manage_metadata；特殊商家角色的相依權限由 Agent 查核，不直接套用 instagram_business_*","instagramPermissions"),
    callback("igSetup"),secret("igSetup","facebook_login"),authorize("igSetup","Instagram via Facebook Login")
  ]},
  {platform:"threads",id:"threads",label:"Threads 自用權杖匯入",description:"先沿用連線；自有測試帳號優先評估官方用戶權杖產生器，不要求 HTTPS 回呼或先取得 App Secret。",steps:[
    prepare("Threads","threads",["準備要連接的 Threads 帳號；App 中的 Threads 專用識別資料要與一般 Meta App 識別資料分開。"]),
    capabilities("Threads","threadsDelete",["官方可新增與刪除自己的貼文、讀取／回覆／管理公開回覆，以及查詢單篇成效。刪文另需 threads_delete，不是只有原本五項權限。","目前查核未找到修改已發布文字或管理私訊的官方端點；公開 conversation 是回覆串，不是私訊。這兩項不可列為已支援。","套件有發布、回覆及帳號成效基礎；刪文須由 Agent 核對權限及目標貼文。進階回覆管理與單篇成效仍待實作。官方測試權杖匯入不需要 HTTPS 回呼；匯入本身不要求你交 App Secret。"]),
    createMeta("存取 Threads API"),
    metaPermissions("threadsSetup","threads_basic、threads_content_publish、threads_read_replies、threads_manage_replies、threads_manage_insights、threads_delete。圖為既有權限示例，新增的刪文權限須另核對實際後台","threadsPermissions"),
    step("新增測試人員並接受邀請","送出邀請不是完成，對方還要在 Threads 接受。",["在 App 主控板開啟「應用程式角色」→「角色」，按「新增用戶」，選擇「Threads 測試人員」，加入指定帳號。","由該帳號本人開啟 Threads 設定的「網站權限」，切到邀請分頁（Invites）。","確認 App 名稱正確後，按「接受」（Accept）。回到 App 角色頁確認結果。"],"測試角色成立，而且 Threads 的邀請已接受。","搜尋不到帳號時先核對 Threads 使用者名稱；不要因為一般 Tester 角色存在，就認為 Threads Tester 邀請也已完成。","threads",{entry:"https://www.threads.com/settings/account",entryLabel:"開啟 Threads 帳號設定",images:["metaRoles","threadsAddRole","threadsTesters"]}),
    tokenHandoff("Threads"),
    step("由 Agent 驗證並交接","匯入不是第二次 OAuth，也不是內容管理已全數可用。",["本人輸入後，Agent 檢查非敏感收據，再核對權杖的 App、帳號、範圍與有效期限。","Agent 用唯讀請求分別驗證身分、內容、回覆及成效，沒有資料就標記證據不足，不發測試貼文。","刷新產生的 Token 可由已授權程式直接保存；只有需要新的後台秘密或重新登入同意時才交回本人，不索取這條路線不需要的 App Secret。"],"憑證保存、各功能讀取與未完成程式分開列出。","原生庫保存失敗、權限不符或刷新結果不明時停止，不自動重送、不把秘密改存一般檔案。","threads",{owner:"Agent 驗證；本人僅處理後台秘密或重新同意"})
  ]},
  {platform:"youtube",id:"desktop",label:"YouTube 桌面應用程式 OAuth",description:"Data API 與 Analytics API 分開啟用；使用者資料需要 OAuth，不是只有 API key。",steps:[
    prepare("YouTube","youtube",["確認要連接的 YouTube 頻道和管理它的 Google 帳號。已有適用 Cloud 專案時先沿用；不要另建重複專案。"]),
    capabilities("YouTube","youtubeUpload",["官方支援影片上傳、修改標題／說明等中繼資料、刪除、留言讀取／回覆／管理及影片成效；修改不等於替換已上傳影片檔案。YouTube Data API 沒有一般私訊管理功能。","本機 Desktop OAuth 使用本機 HTTP loopback 與 PKCE，不需要公開 HTTPS 回呼，也不需要另申請 API key。","2020-07-28 後建立且未通過審核的 API 專案，上傳影片會受限為私人；解除需要 YouTube API 合規審核，與 OAuth 驗證不是同一件事。先告知限制，不用實際上傳來測試。","套件目前有發布與留言回覆基礎；影片標題／說明修改與刪除須由 Agent 核對權限及目標影片。修改不替換影片檔案；既有 defaultAudioLanguage 非空時目前停止修改，以免誤刪欄位。進階留言管理仍待補齊。Analytics 低層可帶影片篩選，但上層驗證目前拒絕非空 filters，單篇成效尚不能宣告可用。"]),
    step("選擇 Cloud 專案","同一套設定都在同一個專案內完成。",["開啟 Google Cloud Console，核對右上角登入的 Google 帳號。","從上方專案選單選取已確認的專案。沒有適用專案才由本人建立並命名。","接下來每個 API 與 Google Auth Platform 頁面都確認是這個專案。"],"頁面上方顯示本次使用的專案。","專案無法選取時先檢查帳號和專案權限；不要先開啟付款或變更組織政策。","clients",{entry:cloud,image:"youtubeProjectPicker",capture:"已補專案選單實拍；私人名稱與 ID 已替換為遮蔽文字，尚未選取或建立專案。"}),
    step("啟用兩個 YouTube API","內容資料與成效資料使用不同 API。",["開啟「API 和服務」→「程式庫」，搜尋 YouTube Data API v3，進入產品頁後按「啟用」。","回到程式庫，搜尋 YouTube Analytics API，同樣進入產品頁並啟用。","若頁面顯示「管理」或已啟用，不必重做；回到已啟用 API 清單核對兩者。"],"同一專案的啟用清單包含 Data API 與 Analytics API；使用者明確延後的項目另記缺口。","名稱相似的 Reporting API 不是 Analytics API。若只看到空白或錯誤頁，不要重複點擊建立或啟用。","youtubeStart",{entry:cloud+"apis/library",images:["youtubeData","youtubeAnalytics"]}),
    step("設定品牌與聯絡資料","Google Auth Platform 管理使用者看到的授權資訊。",["開啟 Google Auth Platform →「品牌」（Branding）。若看到「開始使用」，先進入初始化。","依畫面填寫 App 名稱、支援信箱與聯絡信箱，選擇適用的目標對象。","由本人閱讀並確認平台政策；建立後再核對品牌資料。"],"品牌設定已建立，名稱與聯絡信箱正確。","已有品牌設定就檢查沿用，不重新初始化。平台要求本人同意的內容不能交給 Agent 代按。","consent",{entry:cloud+"auth/branding",image:"youtubeBranding",capture:"此圖是既有品牌設定，不是首次初始化精靈；政策同意畫面仍待補拍。"}),
    step("選擇測試或長期使用","自用不等於應選 Internal；也不能把 External 測試模式當成長期免維護方案。",["開啟「目標對象」（Audience），核對 External 或符合組織資格的 Internal。已有合適狀態就沿用。","短期試用採 External Testing 時，加入稍後授權的 Google 帳號為測試使用者。本次 YouTube 權限不屬純個人資料例外，refresh token 通常 7 天到期。","要長期使用時，請 Agent 先說明切換正式狀態與可能的 OAuth 驗證要求，再由你確認是否進行；不是自動發布 App，也不是每個自用情境都一律要求完整審查。"],"你知道目前是短期測試還是長期使用，以及何時可能需要重新授權。","access_denied 先核對帳號和名單；不要為了排除錯誤擅自發布。OAuth 狀態也不會自動解除 YouTube 上傳私人限制。","googleExpiry",{entry:cloud+"auth/audience",images:["youtubeTestAudience","youtubeTestAdd","youtubeAudience"],capture:"已實拍既有測試名單、空白新增表單與正式狀態對照，沒有切換狀態或新增使用者。"}),
    step("核對內容、留言與成效權限","本次是管理內容與留言，不只讀取影片清單。",["開啟「資料存取權」（Data Access），按新增或移除範圍的入口。","內容及留言管理核對 https://www.googleapis.com/auth/youtube.force-ssl；成效核對 https://www.googleapis.com/auth/yt-analytics.readonly。由 Agent 按實際端點說明用途後才加入。","目前套件的 OAuth 驗證器另硬性要求 youtube.readonly；程式未調整前須揭露這個相依，不可宣稱只有上述兩項就已能跑完整流程。只做唯讀者則使用唯讀範圍，不索取管理權限。"],"官方功能需求與目前套件相依分開列出，儲存後重新核對。","找不到範圍先確認 API 已啟用。權限足夠不代表修改／刪除或單篇成效執行器已完成。","googleScopes",{entry:cloud+"auth/scopes",images:["youtubeScopes","youtubeScopePicker"],capture:"現有圖片是範圍選擇入口，不是本次完整管理權限已選取或保存的證據。"}),
    step("建立桌面用戶端","這個技能採本機回呼的 Desktop App，不是 Web App 或服務帳戶。",["先請 Agent 準備安全輸入入口；接著開啟「用戶端」（Clients）→「建立用戶端」。","應用程式類型選「電腦版應用程式」（Desktop app），輸入易辨認的名稱，再由本人完成建立。","若出現 client secret，只由本人處理。不要把憑證 JSON 下載到技能包或貼到對話；接著依下一步安全保存。"],"用戶端類型是 Desktop app；已有相符用戶端時沿用，不重建。","若誤選 Web application，先停止讓 Agent 核對，不照著不相容教學填 localhost。桌面路線使用 loopback 與 PKCE，不用舊式手動貼授權碼。","clients",{entry:cloud+"auth/clients",image:"youtubeDesktop",capture:"已拍到電腦版應用程式表單，未按建立、產生或下載憑證。"}),
    secret("desktop"),
    step("本人授權並分別驗證兩個 API","兩項唯讀驗證都通過，才知道內容與成效整合可用。",["Client Secret 已由你安全保存後，Agent 準備短期桌面 OAuth 連結。","由本人選擇正確 Google 帳號與頻道、核對範圍並同意。程式交換及日後刷新產生的 Token 直接存入系統憑證庫，不再要求你複製或確認儲存。","Agent 分別執行 Data API 的 channels.list 與 Analytics API 的 reports.query，只回報非敏感結果；沒有成效資料不等於已證明每種報表可用。"],"頻道身分相符；內容與成效讀取結果分開列出。不以實際上傳影片來測試設定。","逾時、撤銷或測試模式限制可能需要本人重新授權。不要要求使用者貼 code；保存或讀回失敗時停止，不改用明文備援。","desktop",{owner:"本人同意 OAuth；程式保存 Token；Agent 驗證"})
  ]}
];
// 共用交接圖附在實際輸入步驟，不額外增加使用者必跑的設定頁。
// 首次初始化四頁來自獨立測試專案，沒有送出品牌設定或同意政策。
const brandImages={};
for (const [key,file,alt,marks] of [
  ["youtubeBrandFirst","youtube-brand-first.png","首次品牌設定：應用程式資訊",[{x:28.5,y:21,w:40,h:4,label:"步驟 1：填寫自己的 App 名稱。"},{x:28.5,y:29,w:40,h:6,label:"步驟 2：選可接收使用者聯絡的支援信箱，再按下一步。"}]],
  ["youtubeBrandAudience","youtube-brand-audience.png","首次品牌設定：目標對象",[{x:28.5,y:38,w:41,h:14,label:"步驟 3：個人 Google 帳戶選外部，先使用測試模式；不必為自用切換正式環境。"}]],
  ["youtubeBrandContact","youtube-brand-contact.png","首次品牌設定：聯絡資訊",[{x:28.5,y:34.5,w:40,h:6,label:"步驟 4：填寫自己收得到通知的信箱，不要照抄示例。"}]],
  ["youtubeBrandPolicy","youtube-brand-policy.png","首次品牌設定：使用者資料政策",[{x:28.5,y:40.5,w:34,h:4,label:"步驟 5：本人閱讀政策，理解並同意後勾選。"},{x:24.5,y:46,w:10,h:10,label:"步驟 6：按繼續，再建立；本圖未勾選或送出。"}]]
]) brandImages[key]={file,width:1200,height:1000,source:"consent",kind:"Google Cloud 首次設定實拍（私人區域已隱藏）",captured:"2026-09-13",alt,marks,note:"只顯示真正的初始化表單；首次品牌設定未送出，沒有啟用 API、連結帳務或取得權杖。"};
for (const route of routes) {
  for (const item of route.steps) {
    if (route.platform==="youtube" && item.title==="設定品牌與聯絡資料") {
      item.images=["youtubeBrandFirst","youtubeBrandAudience","youtubeBrandContact","youtubeBrandPolicy","youtubeBranding"];
      item.capture="已補首次品牌初始化的四頁實拍，並保留既有品牌管理頁供對照；已有品牌設定就跳過初始化，不重建。";
    }
    if (item.actions.some(action=>action.includes("已輸入完畢"))) {
      item.images=[...(item.images||(item.image?[item.image]:[])),"secureHandoff"];
    }
  }
}
// 完整自用管理包含刪文：新設定預設 Facebook Login；既有路線的深連結仍有效。
const instagramRoutes=routes.filter(route=>route.platform==="instagram");
routes.splice(routes.findIndex(route=>route.platform==="instagram"),instagramRoutes.length,
  instagramRoutes.find(route=>route.id==="facebook_login"),instagramRoutes.find(route=>route.id==="instagram_login"));
// 拍攝頁只記錄公開入口；不把含私人 App ID 的完整後台網址帶入公開包。
const live=(file,source,alt,marks,height=1000,note="")=>({file,width:1440,height,source,alt,marks,kind:"Meta 後台實拍（已去識別化）",captured:"2026-09-13",capturePage:meta,note:"名稱、帳號、識別碼與私人欄位已遮蔽；秘密未開啟。畫面是既有測試 App 的例子，不是你的設定或應套用的預設值。"+note});
// 示範精靈與既有 App 分開標記；只有最終送出才算建立。
const creation=(file,alt,marks,note)=>({...live(file,"metaCreate",alt,marks),capturePage:"https://developers.facebook.com/apps/creation/",note:"真實建立精靈；私人資料已遮蔽。尚未建立 App、同意條款或產生憑證。"+note});
// Google 圖片使用獨立來源與狀態，不沿用 Meta 描述。
const googleCapture=(file,alt,source,page,marks,height=1000,note="")=>({file,width:1440,height,source,alt,marks,kind:"Google Cloud 後台實拍（已去識別化）",captured:"2026-09-13",capturePage:cloud+page,note:"帳號、專案及私人欄位已遮蔽；未修改平台設定或取得秘密。"+note});
// 私人原圖不進入公開套件；只收錄經遮蔽且逐張檢視的像素結果。
const facebookConsent=(name,alt,marks)=>({file:`facebook-consent-${name}.png`,width:600,height:720,source:"facebook",alt,marks,kind:"使用者提供的 Facebook 授權實拍（私人區域已遮蔽）",captured:"2026-09-13",note:"姓名、頭像、App 與專頁名稱、ID 以不透明色塊遮蔽；未包含權杖。此組只示範兩項讀取權限，並非完整管理或 Page Token 保存驗收。"});
window.SETUP_GUIDE={checked:"2026-09-13",status:"已補 Facebook／Instagram 帳號與資產選擇、Threads 同意與權杖結果，以及 Google 首次品牌設定、一次性秘密和帳戶授權圖。尚未完成各平台完整權限、原生保存與管理功能的實機驗收；YouTube 本次未出現獨立頻道選單。",sources,routes,images:{
  facebookConsentIdentity:facebookConsent("identity","Facebook 帳號身分確認與繼續按鈕",[{x:47.8,y:20.7,w:38,h:5,label:"步驟 1：核對你的帳號及 App 後按繼續；私人文字已遮蔽。"}]),
  instagramConsentAccount:{file:"instagram-consent-account.png",width:900,height:900,source:"igSetup",alt:"Facebook Login 授權頁中只選擇目前的 Instagram 帳號",kind:"Meta 授權頁實拍（已去識別化）",captured:"2026-09-13",note:"App 名稱與 IG 帳號名稱已替換為示例，ID、頭像已遮蔽。僅勾選一個現有帳號，未送出最終同意。",marks:[{x:5.5,y:22.8,w:52,h:5,label:"步驟 1：選擇只使用目前的 Instagram 帳號。"},{x:8,y:32.8,w:50,h:6,label:"步驟 2：只勾選本次管理的帳號，再按繼續。"}]},
  instagramConsentPermissions:{file:"instagram-consent-permissions.png",width:900,height:900,source:"igSetup",alt:"Instagram 基本讀取與 Facebook 專頁讀取權限確認",kind:"Meta 授權頁實拍（已去識別化）",captured:"2026-09-13",note:"App 名稱已替換為示例、頭像已遮蔽。此圖只有 instagram_basic、pages_show_list、pages_read_engagement，不代表完整管理授權；未按最終儲存。",marks:[{x:5.7,y:13.6,w:51,h:17.5,label:"步驟 3：逐項核對權限與資產數量；圖中僅有基本讀取，不含刪文或私訊。"},{x:41,y:67.5,w:16,h:4.5,label:"核對本次完整清單後才儲存。這不是將秘密保存到電腦。"}]},
  facebookConsentPages:facebookConsent("pages","只授權目前選取的一個粉絲專頁",[{x:8.5,y:28.8,w:53,h:4,label:"步驟 2：只選目前的粉絲專頁，不預設授權未來新增的資產。"},{x:12.7,y:40.8,w:74,h:7.5,label:"步驟 3：只勾選目標專頁；此圖選取一項，名稱及 ID 已遮蔽。"},{x:62,y:84.3,w:24,h:5.2,label:"核對後按繼續。"}]),
  facebookConsentPermissions:facebookConsent("permissions","Facebook 所選專頁的兩項讀取權限確認",[{x:9,y:17,w:75,h:14,label:"步驟 4：核對權限。此圖只有讀取內容與專頁清單，不含發文或私訊管理。"},{x:61.6,y:84.7,w:24,h:5.2,label:"核對後按儲存：保存平台授權，不是保存 Token 到電腦。"}]),
  facebookConsentConnected:facebookConsent("connected","Facebook 連結結果與知道了按鈕",[{x:37,y:84.7,w:49,h:5.4,label:"步驟 5：連結結果確認後按知道了。返回後仍須確認權杖類型。"}]),
  secureHandoff:{file:"secure-handoff-demo.png",width:1440,height:1050,source:"desktop",alt:"四平台共用安全輸入交接：告知準備好、Agent 開啟終端機、本人貼上按 Enter、Agent 檢查保存並接續驗證",kind:"本專案自有流程示意圖（非平台或作業系統實拍）",captured:"2026-09-13",note:"由隨附 secure-handoff-demo.html 呈現的教學示意；沒有真實秘密、輸入功能或憑證庫連線。四步編號已寫在圖內，回報文字僅為範例，不是實際保存成功的證據。",marks:[]},
  youtubeProjectPicker:googleCapture("youtube-project-picker.png","Google Cloud 專案選單的搜尋、專案列與新增專案入口","clients","projectselector2/home/dashboard",[
    {x:23.3,y:29.5,w:53.5,h:3.7,label:"步驟 1：搜尋已確認的專案名稱或 ID。"},
    {x:24,y:39.7,w:51.5,h:3,label:"步驟 2：核對名稱及 ID 後選取；不要照抄遮蔽文字。"},
    {x:69,y:24.2,w:8,h:3,label:"沒有適用專案時才新增；已有專案不必重建。"}
  ],1000,"專案名稱、ID 與背景已遮蔽；未選取、建立或刪除專案。"),
  facebookExplorer:{...live("facebook-explorer.png","facebook","Graph API Explorer 專頁權杖入口",[
    {x:68,y:30,w:29,h:3,label:"步驟 1：選擇你自己的 Meta App；此名稱已替換為教學示例。"},
    {x:68,y:35.5,w:29,h:3,label:"步驟 2：開啟「用戶或粉絲專頁」下拉選單。"},
    {x:68,y:40,w:29,h:12,label:"依 Agent 已確認清單核對權限；目前畫面的 public_profile 不是完整管理權限。"},
    {x:68,y:20.3,w:29,h:6.9,label:"完成本人授權後，由本人複製權杖至安全終端機；值全程遮蔽。"}
  ],1100),capturePage:"https://developers.facebook.com/tools/explorer/"},
  facebookExplorerMenu:{...live("facebook-explorer-menu.png","facebook","Graph API Explorer 取得粉絲專頁權杖選單",[
    {x:62,y:49,w:24,h:3.3,label:"步驟 3：選「取得粉絲專頁存取權杖」，不是上方的一般用戶或應用程式權杖。"},
    {x:68,y:30,w:29,h:3,label:"先核對 App 正確，再由本人進行後續帳號、專頁與權限同意。"}
  ],1100,"本次只展開選單，沒有點選取得權杖或送出同意。"),capturePage:"https://developers.facebook.com/tools/explorer/"},
  // 建立精靈尚未送出；不要沿用既有 App 實拍的狀態說明。
  metaCreateDetails:{...live("meta-create-details.png","metaCreate","Meta 建立應用程式精靈的詳細資料頁",[
    {x:15.7,y:26.3,w:67.6,h:3.8,label:"填寫你自己的應用程式名稱；畫面上限為 30 字元。"},
    {x:15.7,y:37.2,w:67.6,h:3.7,label:"確認本人會定期查看的聯絡信箱；此圖已遮蔽欄位內容。"},
    {x:79.1,y:42.3,w:4.3,h:3.9,label:"填妥後按「繼續」；這張圖尚未填寫或送出。"}
  ]),capturePage:"https://developers.facebook.com/apps/creation/",note:"此張拍攝時尚未填寫；後續以教學用名稱代填並沿用已遮蔽的預填信箱，前進到總覽，未完成建立。"},
  metaCreateCases:creation("meta-create-cases.png","內容管理分類中的三平台使用案例",[
    {x:15.8,y:39.2,w:9.8,h:3.2,label:"先切換「內容管理」，不用在預設精選清單反覆尋找。"},
    {x:27.7,y:25.8,w:55.6,h:7.6,label:"Threads 選「存取 Threads API」。"},
    {x:27.7,y:34.2,w:55.6,h:7.6,label:"Instagram 選「管理 Instagram 的訊息和內容」。"},
    {x:27.7,y:58.2,w:55.6,h:6.4,label:"Facebook 選「管理粉絲專頁的所有內容」。"},
    {x:79.1,y:66.2,w:4.2,h:3.7,label:"只選本次需要的案例，再按「繼續」。"}
  ],"此圖尚未勾選，後續示例只選 Threads；不要求一次選三個平台。"),
  metaCreateBusiness:creation("meta-create-business.png","建立精靈的商家選擇頁",[
    {x:15.7,y:30.5,w:32,h:11.1,label:"需要連結時，核對自己有權使用的商家；私人名稱已遮蔽。"},
    {x:15.7,y:42.5,w:36,h:3.1,label:"本示例選擇暫不連結；實際用途需要商家驗證時不能用此步驟繞過。"},
    {x:79.1,y:51.2,w:4.2,h:3.7,label:"選妥後按「繼續」。"}
  ],"Threads 示範路線；商家資格與實際資料存取權仍須另行確認。"),
  metaCreateRequirements:creation("meta-create-requirements.png","Threads 示例的要求頁",[
    {x:15.7,y:29.8,w:67.6,h:5.4,label:"閱讀自己畫面的要求；本例顯示找不到條件，不代表所有 App 都免審查。"},
    {x:78.1,y:38.4,w:5.2,h:3.7,label:"核對後按「下一步」，進入總覽。"}
  ],"這只是目前示例選項的結果；新增使用案例或改變用途可能出現不同要求。"),
  metaCreateOverview:creation("meta-create-overview.png","Threads 示例的建立前總覽與條款關卡",[
    {x:15.7,y:30.6,w:67.6,h:13.9,label:"核對 App 名稱與信箱；名稱是教學示例，請換成自己的資料。"},
    {x:15.7,y:48.9,w:67.6,h:28.4,label:"核對使用案例、商家與要求；本圖僅示範 Threads。"},
    {x:15.7,y:78.7,w:67.6,h:3,label:"本人閱讀條款；Agent 不代為同意。"},
    {x:75.2,y:82.5,w:8.1,h:3.7,label:"準備正式建立時才由本人按此鈕；本次拍攝未按下。"}
  ],"AI Workflow API Guide Test 是虛構教學名稱，不是已建立的 App。"),
  facebookCreateOverview:creation("facebook-create-overview.png","Facebook 建立前總覽",[
    {x:15.7,y:25,w:67.6,h:13.9,label:"核對示例名稱與自己的聯絡信箱。"},
    {x:15.7,y:43.3,w:67.6,h:7.2,label:"確認是管理粉絲專頁，而非 Threads 或 Instagram。"},
    {x:15.7,y:64.6,w:67.6,h:9.5,label:"依自己的用途核對要求與條款；不能把本例當成免審查保證。"},
    {x:75.2,y:75.2,w:8.1,h:3.7,label:"最終建立包含同意條款，交由本人操作；本次未按。"}
  ],"Facebook 單一案例、未連結商家的示例；沒有建立 App。"),
  instagramCreateOverview:creation("instagram-create-overview.png","Instagram 建立前總覽",[
    {x:15.7,y:25,w:67.6,h:13.9,label:"核對示例名稱與自己的聯絡信箱。"},
    {x:15.7,y:43.3,w:67.6,h:7.2,label:"確認是管理 Instagram 的訊息和內容；登入路線於後續設定再區分。"},
    {x:15.7,y:64.6,w:67.6,h:9.5,label:"核對要求與條款，不因本例沒有要求就略過後續資格檢查。"},
    {x:75.2,y:75.2,w:8.1,h:3.7,label:"最終建立由本人閱讀條款後操作；本次未按。"}
  ],"Instagram 單一案例、未連結商家的示例；沒有建立 App。"),
  youtubeTestAudience:googleCapture("youtube-test-audience.png","測試模式的測試使用者入口","consent","auth/audience",[
    {x:20.5,y:15.8,w:19,h:8,label:"核對發布狀態是測試；不需要按發布應用程式。"},
    {x:20.5,y:34.2,w:19,h:8,label:"外部測試路線才依此設定測試名單。"},
    {x:20.5,y:81,w:8.2,h:3.3,label:"在測試使用者下按 Add users（新增使用者）。"},
    {x:20.5,y:91.5,w:35.6,h:6,label:"保存後回到此處核對名單；這裡是既有名單，不是本次新增結果。"}
  ],1000,"既有測試專案實拍，帳號與專案已遮蔽。"),
  youtubeTestAdd:googleCapture("youtube-test-add.png","新增測試使用者的空白表單","consent","auth/audience",[
    {x:49.6,y:19.3,w:35.5,h:3.7,label:"填入稍後親自進行 OAuth 的 Google 帳號信箱；不是 App 的名稱。"},
    {x:49.6,y:26.5,w:3.6,h:3.2,label:"核對受邀帳號與授權範圍後才儲存；本次沒有輸入或提交。"}
  ],1000,"此操作會修改測試名單；一般信箱可由已獲授權的 Agent 代填，OAuth 同意仍由本人處理。"),
  youtubeScopePicker:googleCapture("youtube-scope-picker.png","更新所選範圍面板","consent","auth/scopes",[
    {x:49.6,y:14,w:48.7,h:3.2,label:"使用篩選條件尋找所需 API 或範圍；不要勾選全部服務。"},
    {x:49.6,y:17.3,w:48.7,h:3,label:"逐項比對完整範圍名稱與用途，只選已確認項目。"},
    {x:49.6,y:77.5,w:48.7,h:4.4,label:"找不到時可依官方清單手動輸入完整範圍；不接受猜測的名稱。"},
    {x:49.6,y:89,w:3.6,h:2.7,label:"更新面板後仍需在主頁核對並儲存，再重新載入檢查。"}
  ],1200,"此圖為尚未選取的通用列表，非 YouTube 已授權清單；沒有按更新或 Save。"),
  metaSecretLocation:live("meta-app-secret.png","facebook","Facebook 與 Instagram Facebook Login 使用的 App Secret 位置",[
    {x:0.6,y:73.8,w:19.7,h:7.1,label:"應用程式設定 → 基本資料。"},
    {x:26.9,y:10,w:31.9,h:5.4,label:"核對上方的一般 App ID，不是下方 Threads ID。"},
    {x:59.9,y:10,w:27.2,h:5.7,label:"這裡是 App Secret；圖片已遮蔽。"},
    {x:87.6,y:12.3,w:4.2,h:3.4,label:"必要時由本人按顯示並驗證；複製後告訴 Agent 準備好輸入。"}
  ],1100,"沒有按顯示，也沒有取得或保存秘密。"),
  instagramSecretLocation:live("instagram-login.png","igSetup","Instagram Login 專用 App Secret 位置",[
    {x:9.7,y:29,w:19.2,h:4,label:"Instagram 案例 → 含有 Instagram 登入的 API 設定。"},
    {x:58.4,y:36.4,w:16,h:7,label:"這是 Instagram 專用 App ID。"},
    {x:75.5,y:36.4,w:16.3,h:6.7,label:"Instagram 應用程式密鑰在此；右側顯示由本人操作。"}
  ],1000,"沿用同一張實拍，針對取得憑證重新標示；未按顯示。"),
  threadsSecretLocation:live("threads-settings.png","threadsSetup","Threads 專用 App Secret 位置",[
    {x:9.7,y:20.1,w:19.2,h:3.8,label:"選存取 Threads API。"},
    {x:9.7,y:29,w:19.2,h:4,label:"開啟設定。"},
    {x:32.2,y:21.7,w:29.2,h:5.8,label:"核對 Threads 專用 App ID。"},
    {x:62.6,y:21.7,w:29.2,h:5.8,label:"Threads 密鑰及顯示按鈕在這裡；不要改用下方權杖產生器。"}
  ],1000,"沿用同一張實拍，針對取得憑證重新標示；未按顯示。"),
  threadsTokenLocation:live("threads-settings.png","threadsSetup","Threads 自用權杖產生器入口",[
    {x:9.7,y:19,w:19.2,h:14,label:"存取 Threads API → 設定。"},
    {x:32.2,y:74.8,w:41.5,h:6.7,label:"往下找到用戶權杖產生器；本圖要求公開的 Threads 測試帳號，不能代改帳號隱私。"},
    {x:75.3,y:77.3,w:16.5,h:4.3,label:"還沒有測試帳號時，依前一步新增角色並由本人接受邀請。"},
    {x:72.4,y:87.4,w:8.2,h:3.9,label:"安全入口與相容匯入器備妥後，才由本人按產生存取權杖；不是上方 App Secret 的顯示。"}
  ],1000,"這張只顯示入口；後續同意與產生結果另有實拍，安全交接另見共用操作圖。"),
  youtubeSecretLocation:googleCapture("youtube-client-secret.png","Google 既有桌面用戶端與秘密顯示限制","googleSecrets","auth/clients",[
    {x:0.3,y:21.9,w:17.5,h:3.3,label:"用戶端 → 選擇本次的電腦版用戶端。"},
    {x:65.5,y:19.4,w:31.7,h:4.5,label:"Client ID 在右側資訊欄；圖片中的值已遮蔽。"},
    {x:65.5,y:49.2,w:31.7,h:7.3,label:"完整舊 Client Secret 無法再次查看或下載；建立當下必須安全保存。"},
    {x:65.5,y:70.7,w:8.5,h:3,label:"遺失時先找 Agent 評估，不要為照圖自行新增密鑰。"}
  ],1100,"既有用戶端實拍，沒有按 Add secret、重設、刪除或下載。"),
  youtubeData:googleCapture("youtube-data.png","YouTube Data API 已啟用頁","youtubeStart","apis/library/youtube.googleapis.com",[
    {x:14.4,y:12.7,w:30,h:3.5,label:"核對產品是 YouTube Data API v3。"},
    {x:14.4,y:29.5,w:21.3,h:3.4,label:"已啟用時顯示管理與狀態，不需要停用後重啟；尚未啟用才按啟用。"}
  ],1000,"這是既有已啟用狀態，不表示本次啟用或 OAuth 驗證成功。"),
  youtubeAnalytics:googleCapture("youtube-analytics.png","YouTube Analytics API 啟用入口","analytics","apis/library/youtubeanalytics.googleapis.com",[
    {x:14.4,y:12.7,w:31,h:3.5,label:"核對 Analytics API；不要選成 Reporting API。"},
    {x:14.4,y:27.2,w:3.7,h:3.3,label:"核對專案並取得啟用授權後才按此鈕；本次只拍攝，沒有啟用。"}
  ]),
  youtubeDesktop:googleCapture("youtube-desktop-client.png","電腦版 OAuth 用戶端建立表單","clients","auth/clients/create",[
    {x:0.3,y:24.1,w:17.5,h:3.6,label:"從用戶端進入建立用戶端。"},
    {x:20.6,y:23.6,w:35.5,h:3.6,label:"選電腦版應用程式（Desktop app），不是網頁應用程式。"},
    {x:20.6,y:29.4,w:35.5,h:3.6,label:"輸入易辨認的一般名稱；Agent 可依授權代填。"},
    {x:20.6,y:44.2,w:3.6,h:3.3,label:"安全保存入口備妥才建立；後續秘密交本人處理。本次未按建立。"}
  ]),
  youtubeBranding:googleCapture("youtube-branding.png","Google Auth Platform 品牌設定","consent","auth/branding",[
    {x:0.3,y:14.1,w:17.5,h:3,label:"開啟品牌；既有設定可沿用，不必重建。"},
    {x:20.6,y:19.3,w:35.5,h:3,label:"填寫使用者在授權畫面會看到的名稱。"},
    {x:20.6,y:26.2,w:35.5,h:3,label:"核對支援信箱；此圖已遮蔽。"},
    {x:20.6,y:60.5,w:35.5,h:16.1,label:"依實際需求填寫首頁、隱私權與服務條款；不使用假的正式網址。"}
  ],1200,"既有品牌畫面，不是初次建立精靈；沒有修改或儲存。"),
  youtubeAudience:googleCapture("youtube-audience.png","既有正式狀態的目標對象頁","consent","auth/audience",[
    {x:0.3,y:20.5,w:17.5,h:3.6,label:"開啟目標對象。"},
    {x:20.6,y:15.9,w:17,h:11.6,label:"先讀發布狀態；本圖為實際運作中，不要為照圖而發布或切回測試。"},
    {x:20.6,y:31.3,w:15,h:8,label:"核對使用者類型；自用不等於符合內部資格。"}
  ],1000,"只有狀態入口實拍；測試名單表單尚未拍攝，也未變更發布狀態。"),
  youtubeScopes:googleCapture("youtube-scopes.png","資料存取權與範圍設定入口","consent","auth/scopes",[
    {x:0.3,y:25.2,w:17.5,h:3.3,label:"開啟資料存取權。"},
    {x:21.4,y:31.8,w:8.7,h:3,label:"按新增或移除範圍，依已確認清單選取，不全選。"},
    {x:20.6,y:92.3,w:3.8,h:3,label:"核對後才儲存；本圖沒有更動，按鈕不可用。"}
  ],1100,"空清單不等於 OAuth 沒有或已具備權限；實際功能仍需獨立驗證。"),
  metaDashboard:live("meta-dashboard.png","metaCreate","Meta App 主控板與已加入的 Threads、Instagram、Facebook 使用案例",[
    {x:0.7,y:7.5,w:19.5,h:3.8,label:"先核對目前選用的 App。這裡的名稱已遮蔽。"},
    {x:1,y:21.2,w:11,h:3.8,label:"從「使用案例」進入設定，或使用右側現有案例入口。"},
    {x:29.5,y:19.8,w:63,h:15.7,label:"選擇本次平台對應的案例；不需要設定其他未選平台。"}
  ],1000,"此圖只展示建立後的主控板，不能代替新建 App 的精靈畫面。"),
  threadsPermissions:live("threads-permissions.png","threadsSetup","Threads 使用案例的權限與功能清單",[
    {x:9.7,y:20.1,w:19.2,h:3.8,label:"核對使用案例是「存取 Threads API」。"},
    {x:9.8,y:24.9,w:19,h:3.9,label:"開啟「權限和功能」，逐項核對已同意的清單。"},
    {x:80.7,y:42.2,w:5.8,h:3.8,label:"需要且已同意的權限才按「新增」；畫面上的每一列不是都必須加入。"}
  ]),
  threadsSettings:live("threads-settings.png","threadsSetup","Threads 專用識別欄位及三個回呼網址的設定頁",[
    {x:9.8,y:29,w:19,h:4,label:"在 Threads 案例中選「設定」。"},
    {x:32.2,y:41.5,w:59.6,h:6,label:"填入 Agent 準備的重新導向回呼網址。"},
    {x:32.2,y:49.1,w:59.6,h:13.6,label:"依要求補齊解除安裝與刪除回呼網址；不要使用假的網址。"},
    {x:86.5,y:65.3,w:4.3,h:3.9,label:"核對本次欄位後由本人儲存，再重新載入檢查。"}
  ],1000,"上方的 Threads 專用 ID／Secret 不等於一般 Meta App 的那組；不要按顯示來拍攝秘密。"),
  instagramLogin:live("instagram-login.png","igSetup","Instagram Login 設定入口與已遮蔽的 Instagram App 識別區域",[
    {x:9.7,y:29,w:19.2,h:4,label:"選「含有 Instagram 登入的 API 設定」。"},
    {x:58.4,y:36.4,w:16,h:7,label:"核對這條路線的 Instagram App ID；實拍中的值已遮蔽。"},
    {x:33.4,y:65.5,w:20.7,h:4,label:"使用此入口檢查權限與功能，不必在這一步產生 Token。"}
  ],1000,"歡迎區的概括文案不作為功能限制的唯一依據；以本次官方功能文件及實際權限清單核對。"),
  instagramPermissions:live("instagram-permissions.png","igSetup","Instagram 權限清單中同時存在兩條登入路線的權限",[
    {x:32.1,y:11,w:26.8,h:46.5,label:"直接 Instagram Login 使用 instagram_business_*；只選本次功能需要的項目。"},
    {x:32.1,y:63,w:26.8,h:7,label:"instagram_content_publish 是另一條登入路線的權限，不可混用。"},
    {x:67.2,y:14.4,w:7,h:43.6,label:"「可供測試」只表示後台權限狀態，不等於使用者授權或功能驗證成功。"}
  ],1000,"畫面已捲至中段；回到清單上方可核對基本權限。不要照抄範例的 API 呼叫次數或啟用狀態。"),
  instagramFacebookLogin:live("instagram-facebook-login.png","igSetup","透過 Facebook 登入的 Instagram 設定頁",[
    {x:9.7,y:37.4,w:19.2,h:4,label:"選「含有 Facebook 登入的 API 設定」。"},
    {x:32.2,y:20.7,w:60.5,h:9,label:"先確認 Instagram 專業帳號與 Facebook 粉絲專頁的連結前提。"},
    {x:33.4,y:56.7,w:17.5,h:3.8,label:"這是批次加入內容權限的按鈕；未核對完整影響前不要直接按。"}
  ],1000,"概覽文案與正式 permission 名稱可能不一致；應回到「權限和功能」逐項核對，不把此圖當可直接複製的權限清單。"),
  instagramCallback:live("instagram-callback.png","igSetup","Instagram 商家登入的 OAuth 回呼設定視窗",[
    {x:30.3,y:29.2,w:39.4,h:5.7,label:"填入 OAuth 重新導向 URI；灰色區域與既有網址已遮蔽。"},
    {x:30.3,y:36.6,w:39.4,h:13.6,label:"依平台要求填入取消授權與資料刪除網址。"},
    {x:65.5,y:51.5,w:4.4,h:4,label:"確定資料正確後儲存。拍攝只查看表單，沒有變更或儲存設定。"}
  ]),
  facebookPermissions:live("facebook-permissions.png","metaCreate","Facebook Pages 使用案例中的內容與互動權限",[
    {x:32.1,y:31.8,w:26.6,h:6,label:"留言管理先核對 pages_manage_engagement。"},
    {x:32.1,y:56,w:26.6,h:6,label:"發布貼文需要的 pages_manage_posts 與讀取權限分開選。"},
    {x:32.1,y:68.1,w:26.6,h:9,label:"依清單核對讀取互動權限；向下繼續核對 pages_show_list 等項目。"},
    {x:67.2,y:34.2,w:7,h:41,label:"已是「可供測試」就核對沿用；不要重複新增，也不要當成 OAuth 已成功。"}
  ]),
  facebookCallback:live("facebook-callback.png","metaCreate","商家專用 Facebook 登入的 OAuth 回呼與資料刪除設定",[
    {x:0.6,y:19.1,w:19.5,h:2.1,label:"選「快速入門」上方的第一個「設定」，不是下方同名的組態頁。"},
    {x:27,y:39.3,w:65.8,h:5.9,label:"在「有效的 OAuth 重新導向 URI」填入完整回呼，不是填上方的 URI 檢查工具。"},
    {x:27,y:63.3,w:65.8,h:13.2,label:"核對取消授權與資料刪除要求網址。其他開關依已確認方案處理，不照抄圖中狀態。"},
    {x:85.4,y:78.4,w:8.6,h:2.5,label:"核對後由本人按 Save Changes，重新載入確認；本次拍攝未儲存任何變更。"}
  ],1600),
  metaRoles:live("meta-roles.png","metaCreate","Meta App 的角色入口與已遮蔽的角色名單",[
    {x:0.6,y:76.9,w:19.4,h:7.6,label:"展開「應用程式角色」，進入「角色」。"},
    {x:85.2,y:16.4,w:7.8,h:4,label:"需要新增時按「新增用戶」；已有適用角色就沿用。"},
    {x:52,y:32.5,w:25.5,h:12.5,label:"Instagram 與 Threads 測試角色分開；本人仍要接受對應平台邀請。"}
  ]),
  instagramAddRole:live("meta-add-role.png","igSetup","新增角色視窗中的 Instagram 測試人員選項",[
    {x:30.2,y:56,w:37.2,h:4.8,label:"Instagram 測試帳號選這一項，不要給不需要的管理員權限。"}
  ],1000,"未選角色、未輸入帳號、未送出新增。角色說明可能保留舊產品文案，不能視為 Basic Display API 仍受本技能支援。"),
  threadsAddRole:live("meta-add-role.png","threads","新增角色視窗中的 Threads 測試人員選項",[
    {x:30.2,y:62.4,w:37.2,h:4.8,label:"選 Threads 測試人員；不要拿一般測試人員角色代替。"}
  ],1000,"本次僅拍攝未選取的表單，未加入或移除任何人員。"),
  threadsTesters:{file:"threads-testers.png",width:1440,height:960,kind:"官方文件示例的瀏覽器截圖",captured:"2026-09-13",source:"threads",alt:"Meta 官方文件中的 Threads Tester 選項，以及 Threads 網站權限的邀請分頁和接受按鈕",note:"圖中的帳號與 App 為官方示例，不是你的帳號；畫面位置可能因版本改變。紅框為本教學的網頁疊加標示。",marks:[
    {x:36.5,y:62.4,w:20.7,h:5,label:"在新增角色畫面選 Threads Tester。"},
    {x:59.8,y:77.3,w:7.3,h:5,label:"由帳號本人到網站權限的 Invites 分頁。"},
    {x:59.3,y:84.7,w:7,h:4.3,label:"核對邀請的 App 後，按 Accept 接受。"}
  ]}
}};
// 新增的實拍只補足畫面證據，不表示已完成 API 或憑證庫驗證。
Object.assign(window.SETUP_GUIDE.images, {
  ...brandImages,
  youtubeAccountConsent:{file:"youtube-account-consent.png",width:1200,height:900,source:"desktop",kind:"Google OAuth 實拍（已去識別化）",captured:"2026-09-13",alt:"Google OAuth 選擇帳戶畫面",note:"姓名、信箱與 App 名稱已替換為示例，頭像已隱藏。這是 Google 帳戶選擇，不是 YouTube 頻道已驗證。",marks:[{x:51,y:37,w:32,h:8,label:"步驟 1：選擇擁有目標 YouTube 頻道的 Google 帳戶。"}]},
  youtubeTestingWarning:{file:"youtube-testing-warning.png",width:1200,height:900,source:"consent",kind:"Google OAuth 實拍",captured:"2026-09-13",alt:"Google 測試中應用程式的未驗證提醒",note:"只適用於本人建立、核對過且已列為測試使用者的 App；陌生 App 應取消。",marks:[{x:51,y:36,w:31,h:10,label:"步驟 2：確認是自己的測試 App；不認識或資訊不符就返回安全的位置。"}]},
  youtubeOAuthConsent:{file:"youtube-oauth-consent.png",width:1200,height:1000,source:"desktop",kind:"Google OAuth 實拍（已去識別化）",captured:"2026-09-13",alt:"Google 已有部分 YouTube 存取權的授權確認",note:"此例已有 youtube.readonly；沒有送出最後繼續，也沒有交換或保存 Token。完整管理應依功能清單核對所需權限，不能只用此圖的讀取權限。",marks:[{x:51.5,y:26.5,w:31,h:9,label:"步驟 3：展開服務清單，核對實際權限；圖中是已有讀取授權。"},{x:67,y:70,w:15,h:4.5,label:"步驟 4：Agent 已啟動本機授權接收程式後，才繼續完成。"}]},
  threadsConsent:{file:"threads-consent.png",width:1000,height:1200,source:"threads",kind:"Threads 授權頁實拍（已去識別化）",captured:"2026-09-13",alt:"Threads 權杖產生器的權限同意畫面",note:"App 與帳號名稱已替換為示例；此次已完成同意。圖中不含 threads_delete，不代表已授予刪文權限。",marks:[{x:5,y:18,w:90,h:32,label:"步驟 1：核對本次功能需要的權限；可進入編輯管理權限調整。"},{x:5,y:80,w:89,h:7,label:"步驟 2：確認帳號正確後繼續。"}]},
  threadsTokenResult:{file:"threads-token-result.png",width:1000,height:900,source:"threadsSetup",kind:"Meta 權杖產生結果實拍（已遮蔽）",captured:"2026-09-13",alt:"Threads 產生權杖後的安全提示與複製位置",note:"帳號已替換、權杖欄位已遮蔽；未複製或匯入此次權杖。產生成功不等於已保存到系統憑證庫。",marks:[{x:21.5,y:44.5,w:14,h:3,label:"步驟 3：閱讀安全提示，再勾選我瞭解。"},{x:21.5,y:48.5,w:57,h:4.5,label:"步驟 4：由本人複製到 Agent 已開啟的不回顯終端機，不貼聊天。"}]},
  youtubeClientCreated:{file:"youtube-client-created.png",width:1200,height:1000,source:"googleSecrets",kind:"Google Cloud 建立結果實拍（秘密已遮蔽）",captured:"2026-09-13",alt:"桌面 OAuth 用戶端建立後的一次性秘密位置",note:"ID 與秘密已替換為遮蔽文字；本次為補拍建立的測試用戶端，拍攝後已刪除，不可沿用。沒有下載 JSON 或保存秘密。",marks:[{x:30.5,y:41,w:39,h:3.5,label:"步驟 1：本人取得用戶端 ID。"},{x:30.5,y:47.2,w:39,h:6.2,label:"步驟 2：注意一次性顯示提醒，先完成安全保存再關閉。"},{x:30.5,y:54.5,w:39,h:3.5,label:"步驟 3：本人取得用戶端密碼，貼入 Agent 開啟的不回顯終端機。"}]}
});
for (const route of routes) {
  for (const item of route.steps) {
    if (route.platform==="youtube" && item.owner==="本人同意 OAuth；程式保存 Token；Agent 驗證") {
      item.images=["youtubeAccountConsent","youtubeTestingWarning","youtubeOAuthConsent"];
      item.capture="已實拍 Google 帳戶選擇、測試 App 提醒及既有讀取授權確認；尚未出現獨立頻道選擇畫面。Agent 仍須在授權後核對實際頻道，不以登入帳戶代替頻道驗證。";
    }
    if (item.images?.includes("threadsTokenLocation")) {
      item.images.push("threadsConsent", "threadsTokenResult");
      item.capture="已補權杖產生器的官方同意及產生結果實拍，權杖已遮蔽。安全保存另見共用操作圖；本次未匯入或驗證真實 Token。";
    }
    if (route.platform==="youtube" && item.images?.includes("youtubeSecretLocation")) {
      item.images.splice(1,0,"youtubeClientCreated");
      item.capture="已補桌面用戶端建立後的一次性秘密位置；圖片中的秘密與 ID 已遮蔽。拍攝用戶端已刪除，請使用自己的有效設定。";
    }
  }
}
})();
