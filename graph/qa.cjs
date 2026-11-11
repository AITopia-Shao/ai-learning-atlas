/* Browser QA using Chromium's DevTools pipe, no npm or localhost server. */
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),{spawn}=require('node:child_process'),{pathToFileURL}=require('node:url'),{StringDecoder}=require('node:string_decoder');
const dir=__dirname,out=path.join(dir,'qa-progress');fs.mkdirSync(out,{recursive:true});
const caches=[path.join(os.homedir(),'AppData','Local','ms-playwright'),path.join(process.env.LOCALAPPDATA||os.homedir(), 'ms-playwright')];
const bundled=caches.filter(x=>fs.existsSync(x)).flatMap(cache=>fs.readdirSync(cache).filter(x=>x.startsWith('chromium_headless_shell-')).sort().reverse().map(x=>path.join(cache,x,'chrome-headless-shell-win64','chrome-headless-shell.exe'))).find(x=>fs.existsSync(x));
const systemBrowsers=['C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe','C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe','/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser','/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'];
const edge=process.env.GRAPH_BROWSER||bundled||systemBrowsers.find(file=>fs.existsSync(file));
if(!edge||!fs.existsSync(edge))throw Error('Chromium browser not found. Set GRAPH_BROWSER to the executable path.');
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'ai-learning-graph-qa-'));
const child=spawn(edge,['--headless=new','--no-sandbox','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-pipe','--user-data-dir='+profile,'--window-size=1440,1000','about:blank'],{windowsHide:true,stdio:['ignore','ignore','pipe','pipe','pipe']});
let browserLog='';child.stderr.on('data',d=>browserLog+=d.toString());child.on('error',e=>browserLog+=String(e));
let completed=false;child.on('exit',code=>{if(!completed){console.error('Browser exited before QA completed: '+code+' '+browserLog);process.exitCode=1;}});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let ws;const results=[],errors=[],requests=[];
function assert(ok,name,details){results.push({name,passed:!!ok,details});if(!ok)throw new Error(name+': '+JSON.stringify(details));}
(async()=>{
 let serial=0,sessionId,buffer='';const pending=new Map(),decoder=new StringDecoder('utf8');
 child.stdio[4].on('data',d=>{buffer+=decoder.write(d);let i;while((i=buffer.indexOf('\0'))!==-1){const raw=buffer.slice(0,i);buffer=buffer.slice(i+1);if(!raw)continue;const m=JSON.parse(raw);if(m.id){const p=pending.get(m.id);pending.delete(m.id);if(p)m.error?p.reject(m.error):p.resolve(m.result);}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);else if(m.method==='Network.requestWillBeSent')requests.push(m.params.request.url);else if(m.method.startsWith('Browser.download'))fs.appendFileSync(path.join(out,'download-events.log'),JSON.stringify(m)+'\n');}});
 const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++serial;pending.set(id,{resolve,reject});const message={id,method,params};if(sessionId&&!/^(Browser|Target)\./.test(method))message.sessionId=sessionId;child.stdio[3].write(JSON.stringify(message)+'\0');});
 const target=await send('Target.createTarget',{url:'about:blank'});sessionId=(await send('Target.attachToTarget',{targetId:target.targetId,flatten:true})).sessionId;
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const click=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
 const change=(id,value)=>evaluate(`document.getElementById(${JSON.stringify(id)}).value=${JSON.stringify(value)};document.getElementById(${JSON.stringify(id)}).dispatchEvent(new Event('change',{bubbles:true}))`);
 const shot=async name=>{await evaluate(`document.getElementById('toast').hidden=true`);const s=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(out,name+'.png'),Buffer.from(s.data,'base64'));};
 const settled=()=>evaluate(`new Promise(r=>{let i=0;const t=setInterval(()=>{if(document.body.dataset.layoutSettled==='true'||i++>60){clearInterval(t);r(true)}},100)})`);
 const state=()=>evaluate('learningGraph.getState()');
 await send('Page.enable');await send('Runtime.enable');await send('Network.enable');await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
 await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url:pathToFileURL(path.join(dir,'..','AI学习图谱.html')).href});
 for(let i=0;i<40;i++){await sleep(150);if(await evaluate(`document.body?.dataset.ready==='true'`))break;}
 await require("./browser-checks.cjs")({send,evaluate,click,change,shot,state,assert,sleep,out,errors,requests});
 const report={passed:results.length,results,errors,remoteRequests:requests.filter(u=>/^https?:/.test(u)),testedAt:new Date().toISOString()};
 fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({passed:results.length,screenshots:fs.readdirSync(out).filter(n=>n.endsWith('.png')),errors},null,2));
 completed=true;await send('Browser.close');
})().catch(e=>{fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({results,errors,error:String(e)},null,2));console.error(e);if(ws)ws.close();child.kill();process.exitCode=1;});
