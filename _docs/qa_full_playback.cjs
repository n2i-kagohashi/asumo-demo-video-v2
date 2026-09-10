const {chromium}=require('/Users/kagohashiyu-ki/.npm-global/lib/node_modules/@browserbasehq/browse-cli/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const tl=JSON.parse(fs.readFileSync(path.join(__dirname,'../_audio/timeline_v2.json')));
(async()=>{
  const b=await chromium.launch({channel:'chrome',headless:true});
  const p=await b.newPage({viewport:{width:1440,height:1040}});const errors=[];
  p.on('pageerror',e=>errors.push(e.message));
  await p.goto('http://127.0.0.1:4322/',{waitUntil:'networkidle'});
  await p.evaluate(()=>document.querySelector('audio').volume=.15);
  await p.locator('#poster').click();
  await p.waitForTimeout(750);await p.locator('#play').click();
  const paused=await p.evaluate(()=>document.querySelector('audio').currentTime);
  await p.waitForTimeout(600);const paused2=await p.evaluate(()=>document.querySelector('audio').currentTime);
  if(Math.abs(paused2-paused)>.05)errors.push('Pause audio drift');
  const box=await p.locator('#scrub').boundingBox();
  for(const t of [180,14,145,0]){
    await p.mouse.click(box.x+box.width*t/tl.total,box.y+box.height/2);await p.waitForTimeout(400);
    const real=await p.evaluate(()=>document.querySelector('audio').currentTime);
    if(Math.abs(real-t)>.05)errors.push('Seek mismatch '+t+' '+real);
  }
  for(const rate of [1.25,1.5,2,1]){
    await p.locator(`[data-speed="${rate}"]`).click();
    const real=await p.evaluate(()=>document.querySelector('audio').playbackRate);
    if(real!==rate)errors.push('Speed mismatch '+rate);
  }
  await p.locator('#play').click();
  const samples=[];let lastLog=-20;const start=Date.now();
  while(Date.now()-start<245000){
    await p.waitForTimeout(900);
    const info=await p.evaluate(()=>{
      const a=document.querySelector('audio');const s=document.querySelectorAll('.scene.on');
      return {t:a.currentTime,paused:a.paused,ended:a.ended,audioReady:a.readyState,sceneCount:s.length,scene:s[0]?.dataset.start,caption:document.querySelector('#cap').textContent,hide:document.querySelector('#subs').classList.contains('hide'),control:document.querySelector('#play').textContent};
    });
    const cap=tl.rows.find(r=>r.kind==='cut'&&info.t>=r.start+.07&&info.t<r.end-.07);
    if(info.sceneCount!==1)errors.push('Active scene count '+info.t);
    if(cap&&!info.hide&&info.caption.replace(/\s/g,'')!==cap.cap.replace(/\s/g,''))errors.push('Caption mismatch '+info.t);
    if(info.audioReady<3)errors.push('Audio buffer low '+info.t);
    samples.push(info);
    if(info.t-lastLog>=20){console.log(`再生確認 ${info.t.toFixed(1)} / ${tl.total} 秒`);lastLog=info.t;}
    if(info.ended||info.control==='↺')break;
  }
  const final=samples.at(-1);if(final.t<tl.total-.05)errors.push('Did not reach end');
  await p.locator('#stage').screenshot({path:path.join(__dirname,'qa','full-playback-end.png')});
  const report={pass:errors.length===0,errors,pauseDelta:paused2-paused,seekAndSpeedChecked:true,wallSeconds:(Date.now()-start)/1000,final,sampleCount:samples.length,samples};
  fs.writeFileSync(path.join(__dirname,'qa','full-playback.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify({...report,samples:undefined}));await b.close();
  if(errors.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exit(1)});
