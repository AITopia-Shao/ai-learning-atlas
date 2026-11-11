(() => {
'use strict';
const DATA=JSON.parse(document.getElementById('curriculum-data').textContent),P=LearningProgress,model=P.createModel(DATA);
const $=id=>document.getElementById(id),NS='http://www.w3.org/2000/svg',nodes=model.nodes,byId=id=>nodes.get(id);
const domains=DATA.nodes.filter(n=>n.type==='domain'),rank={domain:1,course:2,topic:3,resource:4};
const children=new Map(),parents=new Map();for(const e of DATA.edges)if(e.type==='contains'){if(!children.has(e.source))children.set(e.source,[]);children.get(e.source).push(e.target);if(!parents.has(e.target))parents.set(e.target,[]);parents.get(e.target).push(e.source);}
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>Number(n.toFixed(1)).toString(),courseOf=n=>{while(n&&n.type!=='course')n=byId(n.parent);return n;};
const pathTo=id=>{const p=[];let n=byId(id);while(n){p.unshift(n);n=byId(n.parent);}return p;};
function descendants(id){const set=new Set();const visit=k=>{for(const c of children.get(k)||[])if(!set.has(c)){set.add(c);visit(c);}};visit(id);return set;}
const state={depth:innerWidth<=760?1:2,layout:'network',domain:'all',pre:true,related:false,optional:true,selected:null,expanded:new Set(),collapsed:new Set(),paused:matchMedia('(prefers-reduced-motion: reduce)').matches};
let progress,storageBlocked=false,storageDirty=false,visible=[],visibleSet=new Set(),edges=[],positions=new Map(),elements=new Map(),edgeElements=[],W=800,H=700,transform={x:0,y:0,k:1},hovered=null,raf=0,iteration=0,initial=true,stagedImport=null;
const svg=$('graph'),viewport=$('viewport');
function toast(msg){$('toast').textContent=msg;$('toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').hidden=true,3500);}
function saveNotice(message,error=false){$('saveStatus').textContent=message;$('saveStatus').classList.toggle('error',error);}
function readStored(){const text=localStorage.getItem(P.KEY);return text?model.validate(JSON.parse(text)):{};}
try{model.replace(readStored());}catch{storageBlocked=true;saveNotice('本机记录无法读取，请使用导出备份',true);}
progress=model.calculate();
function refreshProgress(){
 progress=model.calculate();
 // Keep the inputs themselves mounted while saving: clicking the completion
 // box immediately after entering a score must not lose that click on blur.
 for(const row of $('outline').querySelectorAll('[data-row]')){const id=row.dataset.row,r=model.record(id),s=progress.get(id);row.classList.toggle('complete',s.complete);row.style.setProperty('--score',s.complete?P.scoreColor(s.score):'var(--muted)');row.querySelector('[data-done]').checked=r.completed;row.querySelector('[data-score]').value=r.score===null?'':r.score;}
 for(const input of $('outline').querySelectorAll('[data-hours]'))input.value=model.record(input.dataset.hours).hours;
 for(const el of $('outline').querySelectorAll('[data-aggregate]')){const s=progress.get(el.dataset.aggregate);el.classList.toggle('done',s.complete);el.style.setProperty('--score',s.complete?P.scoreColor(s.score):'var(--dim)');el.textContent=s.complete?'✓ '+fmt(s.score):s.done+'/'+s.count;}
 for(const el of $('outline').querySelectorAll('[data-total]')){const s=progress.get(el.dataset.total);el.textContent=`预计 ${fmt(s.hours)} h · 已完成 ${fmt(s.progress*100)}%`;}
 paintProgress();
}
function persist(){
 if(storageBlocked){storageDirty=true;saveNotice('仅保留在本次页面，请导出备份',true);return;}
 try{localStorage.setItem(P.KEY,JSON.stringify(model.snapshot()));storageDirty=false;saveNotice('已保存 · '+new Date().toLocaleTimeString('zh-CN',{hour12:false}));}
 catch{storageDirty=true;saveNotice('保存失败，请导出记录备份',true);}
}
function commit(id,update){
 try{
  model.validateRecord(id,{...model.record(id),...update});
  // Rebase on the latest storage snapshot so another tab's edits to other
  // chapters are not overwritten. Never replace unsaved in-memory edits.
  if(!storageBlocked&&!storageDirty)model.replace(readStored());
  model.patch(id,update);persist();refreshProgress();
 }catch(e){toast(e.message.replace(id,byId(id)?.label||id));drawOutline();return false;}return true;
}
function saveView(){const q=new URLSearchParams({depth:state.depth});if(state.selected)q.set('n',state.selected);if(state.layout!=='network')q.set('layout',state.layout);if(state.domain!=='all')q.set('domain',state.domain);if(!state.pre)q.set('pre','0');if(state.related)q.set('related','1');if(!state.optional)q.set('optional','0');if(state.expanded.size)q.set('expand',[...state.expanded].join(','));if(state.collapsed.size)q.set('collapse',[...state.collapsed].join(','));try{history.replaceState(null,'','#'+q);}catch{}}
function restoreView(){const q=new URLSearchParams(location.hash.slice(1));state.depth=Math.min(4,Math.max(1,Number(q.get('depth'))||(innerWidth<=760?1:2)));state.selected=nodes.has(q.get('n'))?q.get('n'):null;state.layout=q.get('layout')==='tree'?'tree':'network';state.domain=domains.some(n=>n.id===q.get('domain'))?q.get('domain'):'all';state.pre=q.get('pre')!=='0';state.related=q.get('related')==='1';state.optional=q.get('optional')!=='0';for(const [key,param] of [['expanded','expand'],['collapsed','collapse']])state[key]=new Set((q.get(param)||'').split(',').filter(id=>nodes.has(id)));}
function aggregate(n){const s=progress.get(n.id);return s?.count?`<span data-aggregate="${n.id}" class="aggregate ${s.complete?'done':''}" style="--score:${s.complete?P.scoreColor(s.score):'var(--dim)'}" title="完成全部章节后显示按预计学时加权的分数">${s.complete?'✓ '+fmt(s.score):s.done+'/'+s.count}</span>`:'';}
function nodeButton(n){return `<button class="name" data-node="${n.id}">${esc(n.label)}</button>`;}
function topicRow(n){const r=model.record(n.id),s=progress.get(n.id),active=state.selected===n.id;
 return `<div class="topic-row ${s.complete?'complete':''} ${active?'active':''}" data-row="${n.id}" style="--score:${s.complete?P.scoreColor(s.score):'var(--muted)'}"><input class="completion" type="checkbox" data-done="${n.id}" ${r.completed?'checked':''} aria-label="完成 ${esc(n.label)}">${nodeButton(n)}<input class="score-input" type="number" min="0" max="100" step="0.1" placeholder="分数" value="${r.score===null?'':r.score}" data-score="${n.id}" aria-label="${esc(n.label)} 分数 0 到 100"></div>${active?`<div class="topic-editor"><label>预计学时 <input class="hours-input" type="number" min="0.01" max="100000" step="any" value="${r.hours}" data-hours="${n.id}" aria-label="${esc(n.label)} 预计学时"> h</label><div class="actions"><button data-info="${n.id}">资料与联系</button><button data-expand="${n.id}">${(children.get(n.id)||[]).every(c=>visibleSet.has(c))?'收起链接':'显示链接'}</button></div></div>`:''}`;
}
function parentEditor(n){if(state.selected!==n.id)return '';const s=progress.get(n.id);return `<div class="parent-editor"><span data-total="${n.id}">预计 ${fmt(s.hours)} h · 已完成 ${fmt(s.progress*100)}%</span><button data-expand="${n.id}">展开 / 收起图节点</button><button data-info="${n.id}">资料</button></div>`;}
function drawOutline(){
 const scroll=$('outline').scrollTop,open=new Set([...$('outline').querySelectorAll('details[open]')].map(d=>d.dataset.group));
 if(!$('outline').children.length)for(const d of domains)open.add(d.id);
 for(const n of pathTo(state.selected))if(n.type==='domain'||n.type==='course')open.add(n.id);
 $('outline').innerHTML=domains.filter(d=>state.domain==='all'||state.domain===d.id).map(d=>`<details class="domain-group ${state.selected===d.id?'active':''}" data-group="${d.id}" ${open.has(d.id)?'open':''}><summary><span class="disclosure">›</span>${nodeButton(d)}${aggregate(d)}</summary>${parentEditor(d)}${(children.get(d.id)||[]).map(byId).filter(c=>state.optional||c.priority!=='选修').map(c=>`<details class="course-group ${courseOf(byId(state.selected))?.id===c.id?'active':''}" data-group="${c.id}" ${open.has(c.id)?'open':''}><summary><span class="disclosure">›</span>${nodeButton(c)}${aggregate(c)}<button class="info" data-info="${c.id}" aria-label="${esc(c.label)} 资料">⋯</button></summary>${parentEditor(c)}${(children.get(c.id)||[]).map(byId).filter(t=>t.trackable).map(topicRow).join('')}</details>`).join('')}</details>`).join('');
 $('outline').scrollTop=scroll;
}
function allowedDomain(n){return (state.domain==='all'||n.domain===state.domain)&&(state.optional||courseOf(n)?.priority!=='选修');}
function computeVisible(){
 const ids=new Set();
 for(const n of DATA.nodes){if(!allowedDomain(n))continue;if(n.id.endsWith('.materials')&&state.depth<4)continue;if(pathTo(n.id).slice(0,-1).some(p=>state.collapsed.has(p.id)))continue;
  if(rank[n.type]<=state.depth||state.expanded.has(n.parent)||n.type==='resource'&&(parents.get(n.id)||[]).some(id=>state.expanded.has(id)))ids.add(n.id);
 }
 for(const id of state.expanded)if(ids.has(id))for(const child of children.get(id)||[])if(byId(child).type==='resource')ids.add(child);
 visible=DATA.nodes.filter(n=>ids.has(n.id));visibleSet=ids;
 const rep=id=>{let n=byId(id);if(!allowedDomain(n))return null;while(n){if(ids.has(n.id))return n.id;n=byId(n.parent);}return null;};
 const groups=new Map();
 for(const e of DATA.edges){
  if(e.type==='pre'&&!state.pre||e.type==='related'&&!state.related)continue;
  let s,t,type=e.type;
  if(type==='contains'){
   if(!ids.has(e.source)||!ids.has(e.target))continue;
   if(byId(e.target).referenceOnly||byId(e.source).referenceOnly){s=e.source;t=e.target;type='reference';}
   else{s=e.target;t=e.source;type='parent';}
  }else{
   s=rep(e.source);t=rep(e.target);if(!s||!t)continue;
   // Coarse views keep prerequisite arrows at the same level. Coloring uses
   // the displayed source's true aggregate, never one completed hidden child.
   const level=Math.min(rank[byId(s).type],rank[byId(t).type]);
   while(s&&rank[byId(s).type]>level)s=rep(byId(s).parent);
   while(t&&rank[byId(t).type]>level)t=rep(byId(t).parent);
  }
  if(!s||!t||s===t)continue;
  const key=type==='related'?[s,t].sort().join('~')+'~related':s+'~'+t+'~'+type;
  if(!groups.has(key))groups.set(key,{source:s,target:t,type,members:[],key});groups.get(key).members.push(e);
 }
 edges=[...groups.values()];
}
function element(tag,attrs={}){const el=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);return el;}
function size(n){return n.type==='domain'?13:n.type==='course'?8:n.type==='topic'?5:4;}
function shortLabel(n){let s=n.label.replace(/^(MIT |Stanford |Berkeley |Harvard |CMU )/,'');return s.length>27?s.slice(0,26)+'…':s;}
function svgBuild(){
 $('nodes').replaceChildren();$('links').replaceChildren();$('markers').replaceChildren();elements.clear();edgeElements=[];
 edges.forEach((e,i)=>{const hit=element('path',{class:'edge-hit'}),path=element('path',{class:'edge '+e.type,'data-source':e.source,'data-target':e.target});let arrow;
  if(e.type==='parent'||e.type==='pre'){const marker=element('marker',{id:'arrow-'+i,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:6,markerHeight:6,orient:'auto',markerUnits:'userSpaceOnUse'});arrow=element('path',{d:'M0 0L10 5L0 10Z'});marker.append(arrow);$('markers').append(marker);path.setAttribute('marker-end',`url(#arrow-${i})`);}
  const title=element('title');title.textContent=(e.type==='parent'?'子节点 → 母节点':e.type==='pre'?'先修 → 后续节点':e.type==='reference'?'资料链接':'知识关联')+'：'+byId(e.source).label+' → '+byId(e.target).label;hit.append(title);hit.addEventListener('click',ev=>{ev.stopPropagation();showEdge(e);});$('links').append(hit,path);edgeElements.push({e,hit,path,arrow});
 });
 for(const n of visible){const g=element('g',{class:'node '+n.type,'data-id':n.id}),hit=element('circle',{r:20,class:'hit'}),r=size(n),ring=element('circle',{r:r+5,class:'selection-ring'}),mark=n.type==='resource'?element('path',{d:`M0 ${-r-1}L${r+1} 0L0 ${r+1}L${-r-1} 0Z`,class:'mark'}):element('circle',{r,class:'mark'}),label=element('text',{'text-anchor':'middle'}),title=element('title');g.append(hit,ring,mark,label,title);g.addEventListener('pointerenter',()=>{hovered=n.id;highlight();});g.addEventListener('pointerleave',()=>{hovered=null;highlight();});g.addEventListener('pointerdown',ev=>startPointer(ev,n.id));$('nodes').append(g);elements.set(n.id,{g,hit,ring,mark,label,title});}
 paintProgress();renderPositions();highlight();
}
function paintProgress(){
 for(const [id,el] of elements){const n=byId(id),s=progress.get(id),complete=!!s?.complete;el.g.classList.toggle('complete',complete);el.g.style.setProperty('--node-color',complete?P.scoreColor(s.score):'var(--node)');el.g.dataset.completed=String(complete);el.label.textContent=shortLabel(n)+(complete?' ✓ '+fmt(s.score):'');el.title.textContent=n.label+(s.count?'\n'+(complete?'已完成 · '+fmt(s.score)+' 分':s.done+' / '+s.count+' 章完成')+' · 预计 '+fmt(s.hours)+' h':'\n资料入口，不重复计分');}
 for(const el of edgeElements){const s=progress.get(el.e.source),complete=!!s?.complete,c=complete?P.scoreColor(s.score):'var(--edge)';el.path.style.stroke=c;el.path.classList.toggle('complete',complete);el.path.dataset.completed=String(complete);if(el.arrow)el.arrow.style.fill=c;}
 updateLabels();
}
/*__LAYOUT__*/
function rebuild({fresh=false,autofit=true}={}){stop();computeVisible();iteration=0;if(state.selected&&!visibleSet.has(state.selected))state.selected=pathTo(state.selected).reverse().find(n=>visibleSet.has(n.id))?.id||null;if(state.layout==='tree')treeLayout();else{networkLayout(fresh);simulate(state.paused?160:70);}svgBuild();if(autofit)fit();document.body.dataset.layoutSettled=String(state.paused||state.layout==='tree');if(!state.paused&&state.layout==='network')raf=requestAnimationFrame(tick);$('empty').hidden=visible.length>0;syncControls();drawOutline();saveView();}
function syncControls(){for(const k of ['depth','layout','domain'])$(k).value=state[k];for(const k of ['pre','related','optional'])$(k).checked=state[k];$('motion').textContent=state.paused?'动态':'暂停';}
function select(id,{locate=false,fromGraph=false}={}){
 if(!nodes.has(id))return;const n=byId(id);state.selected=id;
 if(!allowedDomain(n)){state.domain='all';state.optional=true;}
 if(!visibleSet.has(id)){for(const p of pathTo(id).slice(0,-1)){state.collapsed.delete(p.id);state.expanded.add(p.id);}if(n.id.endsWith('.materials'))state.depth=4;rebuild({autofit:false});}
 drawOutline();highlight();saveView();
 if(locate){const p=positions.get(id);if(p){transform.k=Math.max(transform.k,.8);transform.x=W/2-p.x*transform.k;transform.y=H/2-p.y*transform.k;updateTransform();}}
 if(n.type==='resource'){showInfo(id);return;}
 if(fromGraph){if(innerWidth<=760)openSidebar();requestAnimationFrame(()=>{const row=$('outline').querySelector(`[data-row="${id}"]`)||$('outline').querySelector(`[data-group="${id}"]>summary`);row?.scrollIntoView({block:'nearest'});});}
}
function expand(id){const n=byId(id);if(!n||n.type==='resource')return;const kids=(children.get(id)||[]).filter(k=>!byId(k).id.endsWith('.materials'));if(kids.length&&kids.every(k=>visibleSet.has(k))){state.collapsed.add(id);state.expanded.delete(id);for(const d of descendants(id))state.expanded.delete(d);}else{state.collapsed.delete(id);state.expanded.add(id);for(const p of pathTo(id))state.collapsed.delete(p.id);}state.selected=id;rebuild();}
function resetView(){state.depth=innerWidth<=760?1:2;state.domain='all';state.layout='network';state.pre=true;state.related=false;state.optional=true;state.selected=null;state.expanded.clear();state.collapsed.clear();hovered=null;$('search').value='';$('searchResults').hidden=true;rebuild({fresh:true});closeSidebar();}
function resource(n){return `<a class="resource-link" href="${esc(n.url)}" target="_blank" rel="noopener noreferrer">${esc(n.label)} ↗<small>${esc(n.resourceKind)} · ${esc(new URL(n.url).hostname)}</small></a>`;}
function relation(e){return `<div class="relation"><button data-node="${e.source}">${esc(byId(e.source).label)}</button> ${e.type==='pre'?'→':'↔'} <button data-node="${e.target}">${esc(byId(e.target).label)}</button><p>${esc(e.reason)}</p></div>`;}
function showInfo(id){const n=byId(id),desc=descendants(id),refs=n.type==='resource'?[n]:[...desc].map(byId).filter(x=>x.type==='resource'),rels=DATA.edges.filter(e=>e.type!=='contains'&&(e.source===id||e.target===id));$('detailTitle').textContent=n.label;$('detailBody').innerHTML=`<p>${esc(n.description||'')}</p>${n.edition?`<p class="muted">${esc(n.edition)}</p>`:''}${refs.map(resource).join('')}${rels.length?'<h3>先修与知识联系</h3>'+rels.map(relation).join(''):''}${n.doc?`<a class="source-link" href="${encodeURI(n.doc)}" target="_blank" rel="noopener">完整原文 ↗</a>`:''}`;$('details').showModal();}
function showEdge(e){$('detailTitle').textContent=e.type==='parent'?'子节点 → 母节点':e.type==='pre'?'前置知识 → 后续节点':e.type==='reference'?'学习资料':'知识关联';const s=progress.get(e.source);$('detailBody').innerHTML=`<p>${esc(byId(e.source).label)} → ${esc(byId(e.target).label)}</p>${e.type==='parent'?`<p>${s.complete?'子节点已完成，箭头使用 '+fmt(s.score)+' 分的颜色。':'子节点未完成，箭头保持灰色。'}母节点必须在全部学习子节点完成后才点亮。</p>`:e.members.map(m=>`<div class="relation"><p>${esc(m.label)}：${esc(m.reason)}</p><p class="muted">${esc(byId(m.source).label)} → ${esc(byId(m.target).label)}</p></div>`).join('')}`;$('details').showModal();}
function search(){const q=$('search').value.trim().toLowerCase();if(!q){$('searchResults').hidden=true;return;}const terms=q.split(/\s+/),found=DATA.nodes.filter(n=>terms.every(t=>[n.label,n.description,courseOf(n)?.label,...(n.aliases||[])].join(' ').toLowerCase().includes(t))).sort((a,b)=>(a.label.toLowerCase().includes(q)?0:1)-(b.label.toLowerCase().includes(q)?0:1)||rank[a.type]-rank[b.type]);$('searchResults').hidden=false;$('searchResults').innerHTML=`<div class="search-count">${found.length?found.length+' 个结果':'没有匹配结果'}</div>`+found.slice(0,50).map(n=>`<button data-node="${n.id}">${esc(n.label)}<small>${esc(byId(n.domain).label)}</small></button>`).join('');}
function openSidebar(){$('sidebar').classList.add('open');$('scrim').hidden=false;}
function closeSidebar(){$('sidebar').classList.remove('open');$('scrim').hidden=true;}
function downloadRecords(){const url=URL.createObjectURL(new Blob([JSON.stringify(model.snapshot(),null,2)],{type:'application/json;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download='AI学习记录-'+new Date().toISOString().slice(0,10)+'.json';a.hidden=true;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}
async function prepareImport(file){try{if(file.size>2e6)throw Error('文件过大，请选择学习记录 JSON');stagedImport=model.validate(JSON.parse(await file.text()));const count=Object.keys(stagedImport).length,done=Object.values(stagedImport).filter(r=>r.completed).length,overlap=Object.keys(stagedImport).filter(id=>Object.hasOwn(model.snapshot().records,id)).length;if(!count)throw Error('文件中没有学习记录');$('importPreview').textContent=`${count} 个章节，${done} 个已完成；${overlap} 个同名记录将被覆盖。`;$('importDialog').showModal();}catch(e){stagedImport=null;toast('未导入：'+e.message);}}
document.addEventListener('click',ev=>{
 const close=ev.target.closest('[data-close]');if(close){$(close.dataset.close).close();return;}
 const info=ev.target.closest('[data-info]');if(info){ev.preventDefault();showInfo(info.dataset.info);return;}
 const ex=ev.target.closest('[data-expand]');if(ex){expand(ex.dataset.expand);return;}
 const b=ev.target.closest('[data-node]');if(b){ev.preventDefault();if(b.closest('#searchResults')){$('search').value='';$('searchResults').hidden=true;$('settings').hidden=true;$('settingsToggle').setAttribute('aria-expanded','false');}$('details').close();select(b.dataset.node,{locate:true});}
});
$('outline').addEventListener('change',ev=>{const el=ev.target;
 if(el.dataset.score){const id=el.dataset.score,v=el.value.trim(),r=model.record(id);if(v===''&&r.completed){toast('已完成章节必须有分数；可先取消完成');drawOutline();return;}commit(id,{score:v===''?null:Number(v)});}
 if(el.dataset.done){const id=el.dataset.done,r=model.record(id);if(el.checked&&r.score===null){el.checked=false;toast('请先填写 0–100 分，再勾选完成');$('outline').querySelector(`[data-score="${id}"]`)?.focus();return;}commit(id,{completed:el.checked});}
 if(el.dataset.hours)commit(el.dataset.hours,{hours:Number(el.value)});
});
$('outline').addEventListener('click',ev=>{if(ev.target.matches('input'))ev.stopPropagation();});
for(const k of ['depth','layout','domain'])$(k).addEventListener('change',()=>{state[k]=k==='depth'?Number($(k).value):$(k).value;if(k==='depth'){state.expanded.clear();state.collapsed.clear();}rebuild({fresh:k==='layout'||k==='domain'});});
for(const k of ['pre','related','optional'])$(k).addEventListener('change',()=>{state[k]=$(k).checked;rebuild();});
$('settingsToggle').onclick=()=>{$('settings').hidden=!$('settings').hidden;$('settingsToggle').setAttribute('aria-expanded',String(!$('settings').hidden));};
$('search').addEventListener('input',search);$('search').addEventListener('keydown',e=>{if(e.key==='Enter'){$('searchResults').querySelector('[data-node]')?.click();}});
$('resetView').onclick=resetView;$('emptyReset').onclick=resetView;$('fit').onclick=fit;$('zoomIn').onclick=()=>zoom(1.25);$('zoomOut').onclick=()=>zoom(.8);
$('motion').onclick=()=>{if(state.layout==='tree'){toast('层次布局保持固定；切换网络布局可启用动态');return;}state.paused=!state.paused;if(state.paused)stop();else{iteration=80;raf=requestAnimationFrame(tick);}syncControls();};
$('mobileMenu').onclick=openSidebar;$('closeSidebar').onclick=closeSidebar;$('scrim').onclick=closeSidebar;$('help').onclick=()=>$('helpDialog').showModal();
$('exportProgress').onclick=downloadRecords;$('importProgress').onclick=()=>{$('importFile').value='';$('importFile').click();};$('importFile').onchange=()=>{if($('importFile').files[0])prepareImport($('importFile').files[0]);};
$('confirmImport').onclick=()=>{if(!stagedImport)return;try{if(!storageBlocked&&!storageDirty)model.replace(readStored());model.replace({...model.snapshot().records,...stagedImport});persist();refreshProgress();$('importDialog').close();stagedImport=null;toast('学习记录已合并');}catch(e){toast('未导入：'+e.message);}};
addEventListener('storage',e=>{if(e.key===P.KEY&&!storageDirty&&!storageBlocked){try{model.replace(readStored());refreshProgress();saveNotice('已同步本机其他页面的记录');}catch{saveNotice('检测到无效记录，当前页面未覆盖',true);}}});
document.addEventListener('keydown',e=>{const editing=/INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName);if(e.key==='Escape'){for(const d of document.querySelectorAll('dialog[open]'))d.close();closeSidebar();return;}if(editing||document.querySelector('dialog[open]'))return;if(e.key==='/'){e.preventDefault();if(innerWidth<=760)openSidebar();$('search').focus();}if(e.key==='+'||e.key==='='){e.preventDefault();zoom(1.2);}if(e.key==='-'){e.preventDefault();zoom(1/1.2);}if(e.key==='Home'){e.preventDefault();fit();}if(document.activeElement===svg&&e.key.startsWith('Arrow')){e.preventDefault();transform.x+=e.key==='ArrowLeft'?40:e.key==='ArrowRight'?-40:0;transform.y+=e.key==='ArrowUp'?40:e.key==='ArrowDown'?-40:0;updateTransform();}});
document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else if(!state.paused&&state.layout==='network'&&iteration<240)raf=requestAnimationFrame(tick);});
addEventListener('hashchange',()=>{restoreView();rebuild({fresh:true});});
new ResizeObserver(()=>{const r=$('stage').getBoundingClientRect();W=r.width;H=r.height;if(!initial)fit();}).observe($('stage'));
for(const d of domains){const op=document.createElement('option');op.value=d.id;op.textContent=d.label;$('domain').append(op);}
restoreView();const rect=$('stage').getBoundingClientRect();W=rect.width;H=rect.height;rebuild({fresh:true});initial=false;document.body.dataset.ready='true';
window.learningGraph={data:DATA,getState:()=>({...state,expanded:[...state.expanded],collapsed:[...state.collapsed],visible:visible.map(n=>n.id),zoom:transform.k,edges:edges.map(e=>({source:e.source,target:e.target,type:e.type}))}),getProgress:()=>Object.fromEntries(progress),getRecords:()=>model.snapshot(),getPositions:()=>Object.fromEntries([...positions].map(([id,p])=>[id,{x:p.x,y:p.y}]))};
})();
