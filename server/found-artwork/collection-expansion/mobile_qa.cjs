const {webkit}=require('playwright');
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
(async()=>{const reports=JSON.parse(fs.readFileSync(path.join(__dirname,'integrated.json')));const b=await webkit.launch({headless:true});try{
for(const width of [320,390,430]){
 const context=await b.newContext({viewport:{width,height:844},isMobile:true,hasTouch:true});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('http://127.0.0.1:18787/?sort=custom');await page.waitForSelector('.is-selected');assert.equal(await page.locator('[data-record-id]').count(),63);
 for(const album of reports){
  const card=page.locator('[data-disc-key="'+album.uri+'"]');await card.locator('.album-artwork').click();await page.waitForTimeout(80);
  const options=JSON.parse(await card.getAttribute('data-disc-options'));assert.ok(options.some(o=>o.kind==='vinyl')&&options.some(o=>o.kind==='cd'));
  for(const kind of ['vinyl','cd']){const option=options.find(o=>o.kind===kind);await page.locator('.disc-choice[data-disc-id="'+option.id+'"]').click();await page.waitForFunction(url=>[...document.querySelectorAll('.record-disc-image')].some(i=>i.getAttribute('src')===url&&i.complete&&i.naturalWidth===648),option.image);assert.equal(await page.locator('.disc-choice[data-disc-id="'+option.id+'"]').getAttribute('aria-pressed'),'true');}
  const geometry=await page.evaluate(()=>{const r=document.querySelector('.crate-shell').getBoundingClientRect();return{overflow:document.documentElement.scrollWidth>innerWidth,bottom:r.bottom,height:innerHeight};});assert.equal(geometry.overflow,false,album.title);assert.ok(geometry.bottom<=geometry.height,album.title+' '+JSON.stringify(geometry));
 }
 const last=reports.at(-1);const record=page.locator('[data-disc-key="'+last.uri+'"]');await page.locator('.selected-play').click();await page.waitForSelector('.record-disc.is-spinning');await page.waitForSelector('.now-playing:not([hidden])');assert.equal(new URL(page.url()).pathname,'/');assert.deepEqual(errors,[]);
 if(width===390){await page.waitForTimeout(750);await page.screenshot({path:'/tmp/fauxvinyl-expanded-shelf-mobile.png'});}console.log('WebKit '+width+'px: 63 records fit; all 11 albums switch vinyl/CD, artwork loads, playback spins and header stays stable.');await context.close();
}
}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1});
