"use strict";
// 不使用帳號欄位、儲存空間或網路請求；網址片段只記錄平台、路線與步驟。
const data = window.SETUP_GUIDE;
const $ = (id) => document.getElementById(id);
const platforms = {facebook:"Facebook",instagram:"Instagram",threads:"Threads",youtube:"YouTube"};
function readRoute() {
  const parts = location.hash.slice(1).split("/");
  const platform = Object.hasOwn(platforms, parts[0]) ? parts[0] : "facebook";
  const routes = data.routes.filter(r => r.platform === platform);
  const route = routes.find(r => r.id === parts[1]) || routes[0];
  const index = /^\d{1,3}$/.test(parts[2] || "") ? Math.min(Number(parts[2]), route.steps.length - 1) : 0;
  return {platform, route, index};
}
function link(label, href) { const a=document.createElement("a");a.textContent=label;a.href=href;return a; }
function scrollActiveNavigation() {
  // 只移動導覽列；不因旋轉螢幕或視窗縮放而關閉圖片或重設內文。
  for(const id of ["platforms","steps"]){const nav=$(id),active=nav.querySelector("[aria-current]");if(active&&nav.scrollWidth>nav.clientWidth)nav.scrollLeft+=active.getBoundingClientRect().left-nav.getBoundingClientRect().left-12;}
}
function screenshot(asset) {
  const box=document.createElement("div");box.className="screenshot";
  const img=document.createElement("img");img.src=asset.file;img.alt=asset.alt;img.width=asset.width;img.height=asset.height;box.append(img);
  for (const [i, mark] of asset.marks.entries()) {
    const area=document.createElement("div");area.className="mark";area.setAttribute("aria-hidden","true");
    Object.assign(area.style,{left:`${mark.x}%`,top:`${mark.y}%`,width:`${mark.w}%`,height:`${mark.h}%`});
    const n=document.createElement("span");n.textContent=String(i+1);area.append(n);box.append(area);
  }
  return box;
}
function render() {
  const {platform,route,index}=readRoute();const step=route.steps[index];
  $("platforms").replaceChildren(...Object.entries(platforms).map(([id,name])=>{const a=link(name,`#${id}`);if(id===platform)a.setAttribute("aria-current","page");return a;}));
  $("route").replaceChildren(...data.routes.filter(r=>r.platform===platform).map(r=>{const o=document.createElement("option");o.value=r.id;o.textContent=r.label;return o;}));
  $("route").value=route.id;$("route").disabled=data.routes.filter(r=>r.platform===platform).length<2;
  $("route-description").textContent=route.description;
  // 教學頁只顯示操作資訊；開發與驗收進度留在維護紀錄。
  $("coverage").hidden=true;
  $("coverage").textContent="";
  $("steps").replaceChildren(...route.steps.map((s,i)=>{const a=link("",`#${platform}/${route.id}/${i}`);const n=document.createElement("span");n.textContent=String(i+1).padStart(2,"0");a.append(n,document.createTextNode(s.title));if(i===index)a.setAttribute("aria-current","step");return a;}));
  $("step-number").textContent=String(index+1).padStart(2,"0");$("owner").textContent=step.owner;$("step-title").textContent=step.title;
  document.title=`${platforms[platform]}｜${step.title}｜社群 API 設定教學`;
  $("intro").textContent=step.intro;$("expected").textContent=step.expected;$("help").textContent=step.help;$("trouble").open=false;
  $("actions").replaceChildren(...step.actions.map(t=>{const li=document.createElement("li");li.textContent=t;return li;}));
  const source=data.sources[step.source];$("source").href=source.url;$("source").title=source.title;
  $("entry").hidden=!step.entry;$("entry").href=step.entry||"#";$("entry").textContent=step.entryLabel||"開啟官方設定入口";
  const visual=$("visual");visual.replaceChildren();
  // 同一步可包含操作入口與結果畫面；各圖保留獨立來源與放大功能。
  for(const imageId of step.images || (step.image ? [step.image] : [])) {
    const asset=data.images[imageId];const figure=document.createElement("figure");figure.append(screenshot(asset));
    const caption=document.createElement("figcaption");caption.textContent=asset.kind;figure.append(caption);
    const details=document.createElement("details");const summary=document.createElement("summary");summary.textContent="圖片來源與拍攝說明";const provenance=document.createElement("p");provenance.textContent=`擷取日期 ${asset.captured}。${asset.note}`;details.append(summary,provenance);figure.append(details);visual.append(figure);
    const legend=document.createElement("ol");legend.className="legend";for(const m of asset.marks){const li=document.createElement("li");li.textContent=m.label;legend.append(li);}visual.append(legend);
    const expand=document.createElement("button");expand.type="button";expand.textContent="放大截圖與標示";expand.onclick=()=>{$("zoom-image").replaceChildren(screenshot(asset));$("zoom").showModal();};visual.append(expand);
  }
  // capture 為維護用拍攝紀錄，不當成使用者的待辦或警告顯示。
  $("previous").disabled=index===0;$("next").disabled=index===route.steps.length-1;
  $("position").textContent=`${index+1} / ${route.steps.length} 步驟`;
  // 窄螢幕的水平導覽跟隨目前步驟，不捲動整個頁面。
  scrollActiveNavigation();
}
$("route").onchange=()=>{location.hash=`${readRoute().platform}/${$("route").value}/0`;};
for(const [id,delta] of [["previous",-1],["next",1]])$(id).onclick=()=>{const {platform,route,index}=readRoute();location.hash=`${platform}/${route.id}/${index+delta}`;};
$("close-zoom").onclick=()=>$("zoom").close();
window.addEventListener("hashchange",()=>{render();$("step-title").focus({preventScroll:true});});
window.addEventListener("resize",scrollActiveNavigation);
render();
