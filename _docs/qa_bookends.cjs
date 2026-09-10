// 参照版と新作を同じ操作・同じサイズで確認。外部システムへの書き込みなし。
const {chromium}=require('/Users/kagohashiyu-ki/.npm-global/lib/node_modules/@browserbasehq/browse-cli/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const OUT=path.join(__dirname,'qa');
const times=[1.8,6.8,11,15.9,16.93,17.2,219.8,220.12,224.5,227.8,230,232.1];
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const result={errors:[],reference:[],new:[]};
 for(const [name,url] of [['reference','http://127.0.0.1:4321/'],['new','http://127.0.0.1:4322/']]){
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  page.on('pageerror',e=>result.errors.push({name,error:e.message}));
  await page.goto(url,{waitUntil:'networkidle'});
  await page.waitForFunction(()=>document.querySelector('audio').readyState>=3);
  await page.locator('#poster').click();await page.locator('#play').click();
  const box=await page.locator('#scrub').boundingBox();
  for(const t of times){
   await page.mouse.click(box.x+box.width*t/232.2,box.y+box.height/2);
   await page.waitForTimeout(1700);
   const info=await page.evaluate(()=>{
    const a=document.querySelector('audio'),sc=document.querySelector('.scene.on');
    const on=e=>!!e&&getComputedStyle(e).opacity==='1';
    return {time:a.currentTime,duration:a.duration,readyState:a.readyState,audioError:a.error?.message,
     sceneCount:document.querySelectorAll('.scene.on').length,start:+sc.dataset.start,end:+sc.dataset.end,
     diagram:!!sc.querySelector('.gt'),logo:on(sc.querySelector('.end-title.in')),
     humanBars:[...sc.querySelectorAll('.gt-bar.human.in')].length,
     title:sc.querySelector('.tc-title')?.textContent,caption:document.querySelector('#cap').textContent};
   });
   assert.equal(info.sceneCount,1);assert.equal(info.duration,232.2);assert.equal(info.audioError,undefined);
   result[name].push({target:t,...info});
   if(![16.93,17.2,219.8,220.12,232.1].includes(t))
    await page.locator('#stage').screenshot({path:path.join(OUT,`bookends-${name}-${t}.png`)});
  }
  if(name==='new'){
   // 2つの接続位置を1倍速で実再生。シーク後の音声再開も確認。
   result.playback=[];
   for(const [from,until] of [[15.2,18.2],[218.8,221.2],[225.7,232.2]]){
    await page.mouse.click(box.x+box.width*from/232.2,box.y+box.height/2);
    await page.locator('#play').click();
    for(let i=0;i<Math.ceil((until-from)*4);i++){
     await page.waitForTimeout(250);
     const info=await page.evaluate(()=>({time:document.querySelector('audio').currentTime,
      paused:document.querySelector('audio').paused,scenes:[...document.querySelectorAll('.scene.on')].map(s=>+s.dataset.start)}));
     result.playback.push(info);
     if(info.time<232.18) assert.equal(info.scenes.length,1);
    }
    const time=await page.locator('audio').evaluate(a=>a.currentTime);
    assert.ok(time>=until-.4,`実再生が進まない: ${time} / ${until}`);
    if(time<232.18)await page.locator('#play').click();
   }
  }
  await page.close();
 }
 assert.equal(result.errors.length,0);
 fs.writeFileSync(path.join(OUT,'bookends.json'),JSON.stringify(result,null,2));
 console.log(JSON.stringify({errors:result.errors,referenceSamples:result.reference.length,newSamples:result.new.length,playbackSamples:result.playback.length,finished:result.playback.at(-1)}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
