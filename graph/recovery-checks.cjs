module.exports=async({send,evaluate,click,assert,sleep})=>{
 const waitFor=async(check)=>{for(let i=0;i<80;i++){if(await check())return;await sleep(50);}throw Error('Timed out waiting for review page');};
 const uploadExpression=payload=>`(()=>{const file=new File([${JSON.stringify(JSON.stringify(payload))}],'review-backup.json',{type:'application/json'});const dt=new DataTransfer();dt.items.add(file);const el=document.getElementById('importFile');el.files=dt.files;el.dispatchEvent(new Event('change',{bubbles:true}));})()`;
 const backup={...await evaluate('learningGraph.getRecords()'),records:{}};
 const record=score=>({completed:true,score,hours:12,updatedAt:''});
 await evaluate(`localStorage.setItem(LearningProgress.KEY,'{broken json')`);
 await send('Page.reload');await waitFor(()=>evaluate(`document.body?.dataset.ready==='true'`));
 assert(await evaluate(`document.getElementById('saveStatus').classList.contains('error')`),'Tab A starts with unreadable storage');
 await click('#outline [data-node="la.eigen"]');
 await evaluate(`const el=document.querySelector('[data-score="la.eigen"]');el.value='88';el.dispatchEvent(new Event('change',{bubbles:true}))`);
 const url=await evaluate('location.href');
 const target=await send('Target.createTarget',{url:'about:blank'});
 const b=(await send('Target.attachToTarget',{targetId:target.targetId,flatten:true})).sessionId;
 const inB=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true},b);if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 await send('Page.enable',{},b);await send('Runtime.enable',{},b);
 await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]},b);
 await send('Page.navigate',{url},b);await waitFor(()=>inB(`document.body?.dataset.ready==='true'`));
 await inB(uploadExpression({...backup,records:{'python.basics':record(93),'la.eigen':record(12)}}));
 await waitFor(()=>inB(`document.getElementById('importDialog').open`));
 await inB(`document.getElementById('confirmImport').click()`);
 await waitFor(()=>evaluate(`JSON.parse(localStorage.getItem(LearningProgress.KEY)).records['python.basics']?.score===93`));
 const before=await evaluate(`JSON.parse(localStorage.getItem(LearningProgress.KEY)).records`);
 assert(before['python.basics'].score===93,'Tab B successfully recovers a completed Python chapter');
 await evaluate(uploadExpression({...backup,records:{'la.space':record(70)}}));
 await waitFor(()=>evaluate(`document.getElementById('importDialog').open`));
 const preview=await evaluate(`document.getElementById('importPreview').textContent`);
 await click('#confirmImport');
 const after=await evaluate(`JSON.parse(localStorage.getItem(LearningProgress.KEY)).records`);
 const toast=await evaluate(`document.getElementById('toast').textContent`);

 assert(after['python.basics']?.score===93,'Recovery must preserve another tab\'s unrelated persisted chapter',{before,after,preview,toast});
 assert(after['la.eigen']?.score===88,'Recovery preserves unsaved local chapter edits');
 assert(after['la.space']?.score===70,'Recovery applies the imported chapter');
 assert(!preview.includes('本机原记录无法读取'),'Preview recognizes storage restored by another tab');
 await send('Page.reload');await waitFor(()=>evaluate(`document.body?.dataset.ready==='true'`));
 assert((await evaluate('learningGraph.getRecords()')).records['python.basics']?.score===93,'Merged multi-tab recovery survives reload');
 // A failed ordinary write leaves a stale snapshot containing other chapters.
 // Only local edits may win over the newer storage, not that whole snapshot.
 await click('#outline [data-node="la.eigen"]');
 await evaluate(`window.originalSet=Storage.prototype.setItem;Storage.prototype.setItem=function(){throw new DOMException('Denied','SecurityError')};const el=document.querySelector('[data-score="la.eigen"]');el.value='89';el.dispatchEvent(new Event('change',{bubbles:true}));Storage.prototype.setItem=window.originalSet`);
 await inB(uploadExpression({...backup,records:{'python.basics':record(96)}}));
 await waitFor(()=>inB(`document.getElementById('importDialog').open`));
 await inB(`document.getElementById('confirmImport').click()`);
 await waitFor(()=>evaluate(`JSON.parse(localStorage.getItem(LearningProgress.KEY)).records['python.basics']?.score===96`));
 await evaluate(uploadExpression({...backup,records:{'la.space':record(71)}}));
 await waitFor(()=>evaluate(`document.getElementById('importDialog').open`));
 await click('#confirmImport');
 const retried=await evaluate(`JSON.parse(localStorage.getItem(LearningProgress.KEY)).records`);
 assert(retried['python.basics']?.score===96,"Import after a failed write preserves another tab's newer chapter");
 assert(retried['la.eigen']?.score===89&&retried['la.space']?.score===71,'Import after a failed write retains pending edits and applies backup');
 // After saving, earlier local edits must no longer override newer remote edits.
 await inB(uploadExpression({...backup,records:{'la.eigen':record(97)}}));
 await waitFor(()=>inB(`document.getElementById('importDialog').open`));await inB(`document.getElementById('confirmImport').click()`);
 await evaluate(uploadExpression({...backup,records:{'la.space':record(72)}}));
 await waitFor(()=>evaluate(`document.getElementById('importDialog').open`));await click('#confirmImport');
 assert(await evaluate(`JSON.parse(localStorage.getItem(LearningProgress.KEY)).records['la.eigen'].score===97`),'Successful save clears pending edits before the next import');
 await send('Target.closeTarget',{targetId:target.targetId});
};
