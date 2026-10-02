/* Run against the actual local app. npm install --prefix tests; node tests/browser_smoke.cjs */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const base=process.env.APP_URL||'http://127.0.0.1:5073';
const output=process.env.TEST_OUTPUT||path.resolve('evaluation/browser');fs.mkdirSync(output,{recursive:true});
const checks=[],failures=[],errors=[],requests=[];
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROME_EXECUTABLE?{executablePath:process.env.CHROME_EXECUTABLE}:{}),args:['--enable-unsafe-swiftshader']});
 const context=await browser.newContext({viewport:{width:1440,height:960}});const page=await context.newPage();
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push({url:r.url(),method:r.method()}));
 async function check(name,fn){try{await fn();checks.push({name,passed:true});console.log('PASS',name);}catch(e){failures.push({name,error:e.message});console.error('FAIL',name,e.message);}}
 const card=id=>page.locator('#symptomCards [data-evidence-id="'+id+'"]');
 await check('actual artifact ready',async()=>assert.equal((await (await page.request.get(base+'/api/health')).json()).ready,true));
 await check('home and interview are lazy',async()=>{
   await page.goto(base);await page.screenshot({path:path.join(output,'home-desktop.png'),fullPage:true});await page.goto(base+'/predict');
   assert.equal(requests.some(r=>r.url.includes('/body-map/')),false);assert.equal(await page.locator('iframe').count(),0);
   assert.equal(await page.locator('input[type=radio][value=unknown]:checked').count()>=8,true);
 });
 await check('Present and Absent survive actual prediction, ranked results',async()=>{
   await card('E_201').locator('input[value=present]').check();await card('E_91').locator('input[value=absent]').check();
   await page.locator('#seeResults').click();await page.locator('#resultsPanel .condition-card').first().waitFor();
   assert.equal(await page.locator('#resultsPanel .condition-card').count(),3);
   assert.equal((await page.locator('#resultsPanel').innerText()).includes('%'),false);
   await page.screenshot({path:path.join(output,'results-desktop.png'),fullPage:true});await page.locator('#editResults').click();
   assert.equal(await card('E_201').locator('input[value=present]').isChecked(),true);
   assert.equal(await card('E_91').locator('input[value=absent]').isChecked(),true);
 });
 await check('follow-up Unknown skip does not repeat',async()=>{
   await page.locator('#nextQuestion').click();await page.locator('#followupCard fieldset').waitFor();
   const field=page.locator('#followupCard fieldset'),id=await field.getAttribute('data-evidence-id');
   const radios=field.locator('input[value=unknown]');if(await radios.count())await radios.click();
   else if(await field.locator('select').count()){await field.locator('select').selectOption('');await field.locator('select').dispatchEvent('change');}
   else await field.getByRole('button',{name:'Unknown',exact:true}).click();
   await page.locator('#nextQuestion').click();await page.locator('#followupCard fieldset').waitFor();
   assert.notEqual(await page.locator('#followupCard fieldset').getAttribute('data-evidence-id'),id);
 });
 await check('parent change clears categorical zero and dependent answers',async()=>{
   await page.locator('#symptomSearch').fill('E_53');await card('E_53').locator('input[value=present]').check();
   await page.locator('#symptomSearch').fill('E_56');const select=card('E_56').locator('select');
   assert.equal(await select.locator('option[value="0"]').count(),1);await select.selectOption('0');
   await page.locator('#symptomSearch').fill('E_53');await card('E_53').locator('input[value=absent]').check();
   assert.equal(await page.locator('#answerChangeNotice').isVisible(),true);
   assert.equal((await page.locator('#answerSummary').innerText()).includes('How intense is the pain?'),false);
   await page.locator('#symptomSearch').fill('E_56');assert.equal(await card('E_56').count(),0);
   await page.locator('#symptomSearch').fill('');
 });
 await check('controlled text requires confirmation, input is escaped',async()=>{
   await page.locator('#resetAnswers').click();await page.locator('#textMode').click();
   await page.locator('#symptomText').fill('I have a cough, but no sore throat. <img src=x onerror="window.textInjected=true">');
   await page.locator('#extractText').click();await page.locator('#textSuggestions .suggestion').first().waitFor();
   assert.equal((await page.locator('#answerCounts').innerText()).includes('0 reviewed'),true);
   assert.equal(await page.evaluate(()=>window.textInjected),undefined);
   await page.locator('#textSuggestions .suggestion').filter({hasText:'Do you have a cough?'}).getByRole('button').click();
   assert.equal((await page.locator('#answerCounts').innerText()).includes('1 reviewed'),true);
 });
 await check('incomplete multi-choice contributes only after explicit completion',async()=>{
   await page.locator('#symptomSearch').fill('E_53');await card('E_53').locator('input[value=present]').check();
   const before=Number((await page.locator('#answerCounts').innerText()).match(/(\d+) reviewed/)[1]);
   await page.locator('#symptomSearch').fill('E_55');await card('E_55').locator('input[value="V_14"]').check();
   assert.equal((await page.locator('#answerCounts').innerText()).includes(before+' reviewed'),true);
   assert.equal((await page.locator('#answerSummary').innerText()).includes('Incomplete selection'),true);
   await card('E_55').getByRole('button',{name:'Confirm complete selection'}).click();
   assert.equal((await page.locator('#answerCounts').innerText()).includes((before+1)+' reviewed'),true);
   assert.equal((await page.locator('#answerSummary').innerText()).includes('Incomplete selection'),false);
   await page.locator('#symptomSearch').fill('');
 });
 await check('viewer actually renders; forged message is rejected; selection preserves answers',async()=>{
   const before=await page.locator('#answerCounts').innerText();await page.locator('#openExplorer').click();
   await page.waitForFunction(()=>document.getElementById('explorerStatus').textContent.startsWith('Select anatomy'),{},{timeout:90000});
   assert.equal(await page.locator('#explorerDialog').evaluate(e=>e.open),true);
   await page.screenshot({path:path.join(output,'atlas-desktop.png')});
   await page.evaluate(()=>{const nav=JSON.parse(document.getElementById('navigationData').textContent);const [id,c]=Object.entries(nav.concepts)[0];window.dispatchEvent(new MessageEvent('message',{origin:location.origin,source:window,data:{type:'symptosphere:anatomy-select',version:1,concept_id:id,part_ids:c.part_ids}}));});
   assert.equal(await page.locator('#explorerDialog').evaluate(e=>e.open),true);
   const frame=page.frameLocator('#explorerFrame iframe');assert.equal(await frame.locator('canvas').count(),1);
   await frame.getByRole('button',{name:'Search anatomy'}).click();
  await frame.getByRole('combobox').fill('heart');await frame.getByRole('option').filter({hasText:/^heart/i}).first().click();
  await frame.locator('.selection-label').waitFor();assert.equal((await frame.locator('.selection-label').innerText()).toLowerCase().includes('heart'),true);
  assert.equal(await page.locator('#explorerDialog').evaluate(e=>e.open),true);await page.locator('#closeExplorer').click();
   assert.equal(await page.locator('iframe').count(),0);assert.equal(await page.locator('#answerCounts').innerText(),before);
   assert.equal(await page.locator('[data-region=chest]').getAttribute('aria-pressed'),'true');
 });
 await check('urgent safety interrupts model results',async()=>{
   await page.locator('#safetyDetails summary').click();await page.locator('input[name="safety:sudden_arm_weakness_24h"][value=present]').check();
   await page.locator('#urgentNotice').waitFor();assert.equal(await page.locator('#nextQuestion').isDisabled(),true);
   await page.locator('#seeResults').click();await page.getByRole('heading',{name:'Seek urgent medical help now.'}).waitFor();
   assert.equal(await page.locator('#resultsPanel .condition-card').count(),0);
 });
 await check('360px mobile, Hindi labels, keyboard and reduced motion',async()=>{
   await page.setViewportSize({width:360,height:800});await page.emulateMedia({reducedMotion:'reduce'});await page.goto(base+'/predict');
   await page.locator('#languageToggle').click();await page.waitForFunction(()=>document.documentElement.lang==='hi');
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true);
   await page.locator('#symptomSearch').focus();await page.keyboard.type('cough');assert.equal(await card('E_201').count(),1);
   await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement!==document.body),true);
   await page.screenshot({path:path.join(output,'interview-mobile.png'),fullPage:true});
 });
 await check('service failure preserves editable evidence',async()=>{
   await page.goto(base+'/predict');await card('E_201').locator('input[value=present]').check();
   await page.route('**/api/predict',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:{message:'Test outage: model unavailable'}})}));
   await page.locator('#seeResults').click();await page.locator('#appError').waitFor();assert.equal(await card('E_201').locator('input[value=present]').isChecked(),true);
   await page.unroute('**/api/predict');
 });
 await check('answers changed in flight reject stale rankings',async()=>{
   await page.goto(base+'/predict');await card('E_201').locator('input[value=present]').check();
   let release;const gate=new Promise(resolve=>release=resolve);let intercepted;
   const started=new Promise(resolve=>intercepted=resolve);
   await page.route('**/api/predict',async route=>{intercepted();await gate;await route.continue();});
   await page.locator('#seeResults').click();await started;await card('E_91').locator('input[value=present]').check();release();
   await page.locator('#appError').waitFor();assert.equal((await page.locator('#appError').innerText()).includes('answers changed'),true);
   assert.equal(await page.locator('#resultsPanel').isVisible(),false);await page.unroute('**/api/predict');
 });
 await check('no-WebGL fallback, frame close, evidence retained',async()=>{
   const fallback=await context.newPage();await fallback.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind,...args){return String(kind).includes('webgl')?null:original.call(this,kind,...args);};});
   await fallback.goto(base+'/predict');await fallback.locator('#openExplorer').click();
   const frame=fallback.frameLocator('#explorerFrame iframe');await frame.getByText('This browser could not start the 3D viewer.',{exact:false}).waitFor();
   await fallback.locator('#closeExplorer').click();assert.equal(await fallback.locator('iframe').count(),0);await fallback.close();
 });
 await check('no-JavaScript form and SSR rankings',async()=>{
   const nojs=await browser.newContext({javaScriptEnabled:false});const p=await nojs.newPage();await p.goto(base+'/predict');
   await p.locator('select[name="evidence:E_201"]').selectOption('present');await p.locator('noscript form button').click();await p.waitForURL('**/results');await p.locator('.condition-card').first().waitFor();
   assert.equal(await p.locator('.condition-card').count(),3);await nojs.close();
 });
 assert.equal(await page.evaluate(()=>localStorage.length),0);assert.deepEqual(await context.cookies(),[]);
 await browser.close();
 fs.writeFileSync(path.join(output,'browser_report.json'),JSON.stringify({checks,failures,page_errors:errors,requests,passed:failures.length===0&&errors.length===0,privacy_check:{localStorage_entries:0,cookies:0},browser_version:browser.version()},null,2));
 console.log('RESULT',checks.length,'passed;',failures.length,'failed;',errors.length,'page errors');
 if(failures.length||errors.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exit(1)});
