/* Pure progress rules shared by the offline page and Node tests. */
(function(root){
'use strict';
const SCHEMA=1,KEY='ai-learning-progress-v1';
function scoreColor(score){if(typeof score!=='number'||!Number.isFinite(score)||score<0||score>100)throw new Error('分数必须在 0–100 之间');return `hsl(${Number((score*1.2).toFixed(4))} 65% 58%)`;}
function createModel(data){
 const nodes=new Map(data.nodes.map(n=>[n.id,n])),units=data.nodes.filter(n=>n.trackable),unitIds=new Set(units.map(n=>n.id));
 const childMap=new Map();for(const n of data.nodes){if(n.parent&&n.type!=='resource'&&!n.referenceOnly){if(!childMap.has(n.parent))childMap.set(n.parent,[]);childMap.get(n.parent).push(n.id);}}
 let records={};
 function validateRecord(id,r){
  if(!unitIds.has(id))throw new Error('未知学习章节：'+id);
  if(!r||typeof r!=='object'||Array.isArray(r)||typeof r.completed!=='boolean')throw new Error('完成状态格式错误：'+id);
  if(r.score!==null&&(typeof r.score!=='number'||!Number.isFinite(r.score)||r.score<0||r.score>100))throw new Error('分数必须为 0–100：'+id);
  if(r.completed&&r.score===null)throw new Error('完成的章节必须有分数：'+id);
  if(typeof r.hours!=='number'||!Number.isFinite(r.hours)||r.hours<=0||r.hours>100000)throw new Error('预计学时必须大于 0：'+id);
  return {completed:r.completed,score:r.score,hours:r.hours,updatedAt:typeof r.updatedAt==='string'?r.updatedAt:''};
 }
 function validate(payload){
  if(!payload||payload.schemaVersion!==SCHEMA||payload.app!=='ai-learning-graph'||payload.granularity!=='topic')throw new Error('这不是兼容的学习记录文件');
  if(!payload.records||typeof payload.records!=='object'||Array.isArray(payload.records))throw new Error('学习记录结构错误');
  const clean={};for(const [id,r] of Object.entries(payload.records))clean[id]=validateRecord(id,r);return clean;
 }
 function record(id){if(!unitIds.has(id))throw new Error('此节点由子章节自动汇总');return records[id]||{completed:false,score:null,hours:nodes.get(id).estimatedHours,updatedAt:''};}
 function replace(clean){const next={};for(const [id,r] of Object.entries(clean))next[id]=validateRecord(id,r);records=next;}
 function patch(id,update){const next=validateRecord(id,{...record(id),...update,updatedAt:new Date().toISOString()});records={...records,[id]:next};return next;}
 function snapshot(){return {app:'ai-learning-graph',schemaVersion:SCHEMA,granularity:'topic',exportedAt:new Date().toISOString(),curriculumDate:data.meta.updated,records:JSON.parse(JSON.stringify(records))};}
 function calculate(){
  const result=new Map();
  function get(id){
   if(result.has(id))return result.get(id);const n=nodes.get(id);let r;
   if(unitIds.has(id)){const v=record(id);r={complete:v.completed,score:v.completed?v.score:null,hours:v.hours,doneHours:v.completed?v.hours:0,count:1,done:v.completed?1:0};}
   else {const children=(childMap.get(id)||[]).map(get).filter(x=>x.count>0),hours=children.reduce((s,x)=>s+x.hours,0),doneHours=children.reduce((s,x)=>s+x.doneHours,0),count=children.reduce((s,x)=>s+x.count,0),done=children.reduce((s,x)=>s+x.done,0),complete=count>0&&children.every(x=>x.complete);
    r={complete,score:complete?children.reduce((s,x)=>s+x.score*x.hours,0)/hours:null,hours,doneHours,count,done};
   }r.progress=r.hours?r.doneHours/r.hours:0;result.set(id,r);return r;
  }
  for(const n of data.nodes)get(n.id);return result;
 }
 return {nodes,units,unitIds,childMap,record,validate,validateRecord,replace,patch,snapshot,calculate};
}
const api={SCHEMA,KEY,scoreColor,createModel};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.LearningProgress=api;
})(typeof globalThis!=='undefined'?globalThis:this);
