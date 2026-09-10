// ローカルブラウザで、実際の再生コントロールを使った確認。
const {chromium}=require('/Users/kagohashiyu-ki/.npm-global/lib/node_modules/@browserbasehq/browse-cli/node_modules/playwright');
const fs=require('node:fs');const path=require('node:path');
const OUT=path.join(__dirname,'qa');fs.mkdirSync(OUT,{recursive:true});
(async()=>{
  const browser=await chromium.launch({channel:'chrome',headless:true});
  const context=await browser.newContext();const page=await context.newPage();
  await page.setViewportSize({width:1440,height:1040});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:4322/',{waitUntil:'networkidle'});
  await page.locator('#poster').click();await page.locator('#play').click();
  const samples=process.env.QA_TIMES?process.env.QA_TIMES.split(',').map(Number):[1,6.5,10.8,15,18,22,29.5,36.5,42.5,49.5,55.9,61.8,67.5,75,79.8,86,91,96,100,104.5,109.7,116.9,120.5,125.5,127.5,134,139.7,144.8,147.9,150.5,154,156.8,160.5,164.8,172,176.8,180.8,184,189.8,196.8,201.4,207.2,211.6,215.8,218,224,229.8];
  const report=[];const box=await page.locator('#scrub').boundingBox();
  for(const t of samples){
    await page.mouse.click(box.x+box.width*t/232.2,box.y+box.height/2);await page.waitForTimeout(420);
    const info=await page.evaluate(()=>{
      const a=document.querySelector('audio'),sc=document.querySelector('.scene.on');
      const stage=document.querySelector('#stage').getBoundingClientRect();
      const visible=e=>{for(let n=e;n&&n!==sc;n=n.parentElement){const st=getComputedStyle(n);if(st.display==='none'||+st.opacity<.5)return false;}return true;};
      const over=[...sc.querySelectorAll('.btn,.res,.field,.panel')].filter(visible).filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&(r.right>stage.right+5||r.bottom>stage.bottom-60)}).map(e=>e.textContent.trim().slice(0,55));
      return {t:a.currentTime,scene:sc.dataset.nav||'title',start:sc.dataset.start,caption:document.querySelector('#cap').textContent,over};
    });
    report.push({target:t,...info});
    await page.locator('#stage').screenshot({path:path.join(OUT,`${String(t).padStart(5,'0')}.png`)});
  }
  fs.writeFileSync(path.join(OUT,process.env.QA_REPORT||'samples.json'),JSON.stringify({errors,samples:report},null,2));
  console.log(JSON.stringify({errors,samples:report.length,overflow:report.filter(r=>r.over.length).map(r=>({t:r.target,over:r.over}))}));
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
