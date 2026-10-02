(() => {
  'use strict';
  const initial=document.getElementById('initialState');if(!initial)return;
  let state=JSON.parse(initial.textContent), catalogue=JSON.parse(document.getElementById('catalogueData').textContent),navigation=JSON.parse(document.getElementById('navigationData').textContent);
  const byId=Object.fromEntries(catalogue.map(q=>[q.id,q]));
  const $=id=>document.getElementById(id), esc=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const t=(key,fallback)=>window.SymptoI18n?.t(key)||fallback;
  let region='all',limit=8,pending=false,followup=null,adaptivePrompts=0,moreAllowed=false,explorerTimer=null,revision=0;
  const answer=k=>state.answers[k]||{state:'unknown',values:[],complete:true};
  const applicable=q=>!q.parent||answer(q.parent).state==='present';
  const known=()=>Object.entries(state.answers).filter(([,a])=>a.state!=='unknown'&&a.complete);
  const safetyQuestions=[
    ['chest_pain','Do you have chest pain?'],
    ['sudden_persistent_chest_pain','Do you have sudden chest pain or discomfort that does not go away?'],
    ['radiating_chest_pain','Do you have chest pain spreading to either arm, neck, jaw, stomach or back?'],
    ['chest_pain_with_sweat_sickness_lightheadedness_breathlessness','Do you have chest pain together with sweating, sickness, lightheadedness or breathlessness?'],
    ['sudden_face_weakness_24h','Within the last 24 hours, has one side of your face suddenly become weak or drooped, even if it stopped?'],
    ['sudden_arm_weakness_24h','Within the last 24 hours, have you suddenly been unable to lift both arms because of weakness or numbness in one arm, even if it stopped?'],
    ['sudden_speech_problem_24h','Within the last 24 hours, have you suddenly had slurred speech or sounded confused, even if it stopped?']];
  const isUrgent=()=>safetyQuestions.slice(1).some(([id])=>state.safety_answers[id]==='present');
  function triState(group,value,handler){
    const div=document.createElement('div');div.className='tri-state';
    for(const [v,label] of [['present',t('present','Present')],['absent',t('absent','Absent')],['unknown',t('unknown','Unknown')]]){
      const l=document.createElement('label'),input=document.createElement('input'),span=document.createElement('span');
      input.type='radio';input.name=group;input.value=v;input.checked=value===v;span.textContent=label;
      input.addEventListener('change',()=>handler(v));l.append(input,span);div.append(l);
      input.addEventListener('click',()=>{if(v==='unknown')handler(v);});
    }return div;
  }
  function renderSafety(){
    $('safetyQuestions').replaceChildren();
    safetyQuestions.forEach(([id,label])=>{const f=document.createElement('fieldset');f.className='question-card';const l=document.createElement('legend');l.textContent=label;f.append(l,triState('safety:'+id,state.safety_answers[id]||'unknown',v=>{revision++;state.safety_answers[id]=v;renderSafety();updateUrgent();}));$('safetyQuestions').append(f);});
  }
  function updateUrgent(){
    const urgent=isUrgent();$('urgentNotice').hidden=!urgent;
    $('urgentNotice').textContent=urgent?'Seek urgent medical help now. Contact local emergency services. Do not wait for this tool or drive yourself.':'';
    $('nextQuestion').disabled=urgent||pending;$('seeResults').disabled=pending;
    if(urgent){$('safetyDetails').open=true;$('followupSection').hidden=true;}
  }
  function invalidate(key){
    let removed=[];
    $('answerChangeNotice').hidden=true;
    for(const q of catalogue)if(q.parent===key&&answer(key).state!=='present'){
      if(state.answers[q.id])removed.push(q.label);delete state.answers[q.id];state.skipped_questions=state.skipped_questions.filter(k=>k!==q.id);
    }
    if(removed.length){const message='Dependent answers were cleared because their parent changed. Review them again if you restore the parent answer.';$('appStatus').textContent=message;$('answerChangeNotice').textContent=message;$('answerChangeNotice').hidden=false;}
  }
  function setAnswer(key,a){
    revision++;
    state.answers[key]=a;state.skipped_questions=state.skipped_questions.filter(k=>k!==key);
    if(a.state==='unknown')state.skipped_questions.push(key);
    invalidate(key);renderCards();renderSummary();
    if(followup===key){if(a.complete){followup=null;$('followupSection').hidden=true;$('appStatus').textContent='Answer reviewed. Ask another follow-up or see possible conditions.';}else{$('followupCard').replaceChildren(questionCard(byId[key],'followup'));}}
  }
  function questionCard(q,where='list'){
    const f=document.createElement('fieldset');f.className='question-card';f.dataset.evidenceId=q.id;
    const legend=document.createElement('legend');legend.textContent=q.label;f.append(legend);
    const meta=document.createElement('div');meta.className='question-meta';meta.textContent=q.history?'Medical history · Unknown / prefer not to answer is available':q.parent?'Dependent answer · '+byId[q.parent].label:'Symptom';f.append(meta);
    let a=answer(q.id);
    if(q.type==='B')f.append(triState(where+':'+q.id,a.state,v=>setAnswer(q.id,{state:v,values:[],complete:true})));
    else if(q.type==='C'){
      const select=document.createElement('select');select.setAttribute('aria-label',q.label);
      const unknown=document.createElement('option');unknown.value='';unknown.textContent=t('unknown','Unknown');select.append(unknown);
      for(const o of q.options){const option=document.createElement('option');option.value=String(o.value);option.textContent=o.label;select.append(option);}
      select.value=a.state==='known'?String(a.values[0]):'';
      select.addEventListener('change',()=>setAnswer(q.id,select.value===''?{state:'unknown',values:[],complete:true}:{state:'known',values:[q.options.find(o=>String(o.value)===select.value).value],complete:true}));f.append(select);
    }else{
      const box=document.createElement('div');box.className='multi-options';
      let vals=a.state==='known'?[...a.values]:[];
      for(const o of q.options){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.value=String(o.value);input.checked=vals.some(v=>String(v)===String(o.value));input.addEventListener('change',()=>{
        if(input.checked){if(String(o.value)===String(q.default))vals=[q.default];else vals=vals.filter(v=>String(v)!==String(q.default)).concat(o.value);}else vals=vals.filter(v=>String(v)!==String(o.value));
        // Draft choices remain incomplete and make no model contribution.
        setAnswer(q.id,vals.length?{state:'known',values:vals,complete:false}:{state:'unknown',values:[],complete:true});
      });const span=document.createElement('span');span.textContent=o.label;label.append(input,span);box.append(label);}f.append(box);
      const complete=document.createElement('button');complete.type='button';complete.className='button small secondary';complete.style.marginTop='10px';complete.textContent=a.complete&&a.state==='known'?'Complete answer reviewed':'Confirm complete selection';complete.disabled=!vals.length;
      complete.addEventListener('click',()=>setAnswer(q.id,{state:'known',values:vals,complete:true}));f.append(complete);
      const skip=document.createElement('button');skip.type='button';skip.className='text-button';skip.style.marginLeft='14px';skip.textContent=t('unknown','Unknown');skip.addEventListener('click',()=>setAnswer(q.id,{state:'unknown',values:[],complete:true}));f.append(skip);
    }return f;
  }
  function renderCards(){
    const term=$('symptomSearch').value.toLowerCase().trim();
    const common=['E_201','E_91','E_97','E_66','E_181','E_53','E_148','E_129','E_151','E_94','E_89','E_214'];
    const filtered=catalogue.filter(q=>applicable(q)&&(!term?q.type==='B'||q.parent:true)&&
      (region==='history'?q.history:region==='all'?(!q.history||!!term):q.regions.includes(region)&&!q.history)&&
      (!term||q.label.toLowerCase().includes(term)||q.id.toLowerCase()===term))
      .sort((a,b)=>(common.indexOf(a.id)<0?100:common.indexOf(a.id))-(common.indexOf(b.id)<0?100:common.indexOf(b.id))||a.id.localeCompare(b.id));
    $('symptomCards').replaceChildren(...filtered.slice(0,limit).map(q=>questionCard(q)));
    $('showMore').hidden=filtered.length<=limit;$('filterStatus').textContent=filtered.length?`${Math.min(limit,filtered.length)} of ${filtered.length} supported questions. Unanswered stays unknown.`:'No supported questions match. Try general search or mark your complaint not covered.';
  }
  function renderSummary(){
    const entries=Object.entries(state.answers);let yes=0,no=0,completed=0;
    entries.forEach(([k,a])=>{if(a.state==='present')yes++;if(a.state==='absent')no++;if(a.state!=='unknown'&&a.complete)completed++;});
    $('answerCounts').innerHTML=`<span>${yes} ${esc(t('present','Present'))}</span><span>${no} ${esc(t('absent','Absent'))}</span><span>${completed} reviewed</span><span>${state.skipped_questions.length} skipped</span>`;
    const div=$('answerSummary');div.replaceChildren();
    for(const [k,a] of entries){if(a.state==='unknown')continue;const p=document.createElement('div');p.className='summary-line';p.textContent=byId[k].label;const status=document.createElement('span');status.className='pill';status.textContent=a.complete?a.state:'Incomplete selection';const edit=document.createElement('button');edit.className='text-button';edit.textContent='Edit';edit.addEventListener('click',()=>{region='all';limit=20;$('symptomSearch').value=byId[k].label;renderCards();$('symptomSearch').focus();$('symptomSearch').scrollIntoView({block:'center'});});p.append(document.createElement('br'),status,edit);div.append(p);}
    if(!entries.some(([,a])=>a.state!=='unknown'))div.innerHTML='<p class="muted">Your reviewed answers will appear here. Unanswered questions remain unknown.</p>';
    updateUrgent();
  }
  function syncContext(){
    const before=JSON.stringify([state.demographics,state.complaint_scope]);
    const age=$('age').value;state.demographics.age=age===''?null:Number(age);state.demographics.dataset_sex=$('datasetSex').value;state.complaint_scope=$('complaintScope').value;
    state.language=document.documentElement.lang==='hi'?'hi':'en';
    if(before!==JSON.stringify([state.demographics,state.complaint_scope]))revision++;
  }
  async function call(path,payload){
    if(pending)throw new Error('A request is already in progress.');
    const requestRevision=revision;
    pending=true;$('extractText').disabled=true;$('appError').hidden=true;renderSummary();$('appStatus').textContent='Processing your reviewed answers…';
    try{const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(60000)});const data=await r.json();if(!r.ok)throw new Error(data.error?.message||'Service unavailable. Your answers remain editable.');if(path!=='/api/extract-symptoms'&&revision!==requestRevision)throw new Error('Your answers changed during this request. Review them and try again.');return data;}
    catch(e){$('appError').textContent=e.name==='TimeoutError'?'The request timed out. Your answers are still here; try again.':e.message;$('appError').hidden=false;$('appError').focus();throw e;}
    finally{pending=false;$('extractText').disabled=false;renderSummary();$('appStatus').textContent='Ready';}
  }
  $('symptomSearch').addEventListener('input',()=>{limit=20;renderCards();});
  $('showMore').addEventListener('click',()=>{limit+=20;renderCards();});
  document.querySelectorAll('[data-region]').forEach(button=>button.addEventListener('click',()=>{region=button.dataset.region;limit=8;$('symptomSearch').value='';document.querySelectorAll('[data-region]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',b===button);});renderCards();}));
  ['age','datasetSex','complaintScope'].forEach(id=>$(id).addEventListener('change',syncContext));
  $('searchMode').addEventListener('click',()=>{$('textInput').hidden=true;mode(false);});$('textMode').addEventListener('click',()=>{$('textInput').hidden=false;mode(true);});
  function mode(text){$('textMode').classList.toggle('active',text);$('searchMode').classList.toggle('active',!text);$('textMode').setAttribute('aria-pressed',text);$('searchMode').setAttribute('aria-pressed',!text);}
  $('extractText').addEventListener('click',async()=>{try{const data=await call('/api/extract-symptoms',{text:$('symptomText').value});const box=$('textSuggestions');box.replaceChildren();
    if(!data.suggestions.length){box.textContent='No allowlisted symptom phrase matched. Use search, or mark your complaint not covered.';return;}
    for(const s of data.suggestions){const div=document.createElement('div');div.className='suggestion';const p=document.createElement('p');p.textContent=s.label;const quote=document.createElement('p');quote.textContent=s.matches.map(m=>`“${m.phrase}”`).join(', ');const button=document.createElement('button');button.className='button small secondary';button.textContent='Confirm '+s.suggested_state;button.addEventListener('click',()=>{setAnswer(s.id,{state:s.suggested_state,values:[],complete:true});button.textContent='Reviewed';button.disabled=true;});div.append(p,quote,button);box.append(div);}
  }catch{}});
  $('nextQuestion').addEventListener('click',async()=>{syncContext();if(!moreAllowed&&adaptivePrompts>=7){$('moreQuestions').hidden=false;$('followupSection').hidden=false;$('followupCard').replaceChildren();$('questionRationale').textContent='Seven follow-up prompts reached. You can review possibilities or choose to answer more.';return;}
    try{const data=await call('/api/next-question',state);if(data.safety?.urgent){updateUrgent();return;}const q=data.question;
      $('followupSection').hidden=false;if(!q){$('followupCard').replaceChildren();$('questionRationale').textContent=data.status==='insufficient_information'?'Mark at least one supported symptom Present before starting follow-up questions.':'No further question is available in this state. Review your scope and answers.';$('moreQuestions').hidden=false;return;}
      followup=q.id;adaptivePrompts++;$('questionRationale').textContent=q.rationale;$('followupCard').replaceChildren(questionCard(byId[q.id],'followup'));$('followupSection').scrollIntoView({block:'center'});$('followupCard').querySelector('input,select')?.focus();
    }catch{}});
  $('moreQuestions').addEventListener('click',()=>{moreAllowed=true;$('moreQuestions').hidden=true;$('nextQuestion').click();});
  $('resetAnswers').addEventListener('click',()=>{revision++;state={schema_version:state.schema_version,demographics:{age:null,dataset_sex:'unknown'},answers:{},skipped_questions:[],safety_answers:{},language:'en',complaint_scope:'supported'};adaptivePrompts=0;moreAllowed=false;followup=null;$('age').value='';$('datasetSex').value='unknown';$('complaintScope').value='supported';$('symptomText').value='';$('textSuggestions').replaceChildren();$('followupSection').hidden=true;$('resultsPanel').hidden=true;$('interviewPanel').hidden=false;$('interviewHeading').hidden=false;renderSafety();renderCards();renderSummary();});
  $('seeResults').addEventListener('click',async()=>{syncContext();try{const result=await call('/api/predict',state);renderResults(result);}catch{}});
  function renderResults(result){
    const panel=$('resultsPanel');panel.hidden=false;
    let html='<div class="page-heading"><div><div class="eyebrow">YOUR EXPLORATION SUMMARY</div><h1>Possible conditions, with context.</h1><p>Ranked model matches. These are not diagnoses or clinical risk estimates.</p></div><button id="editResults" class="button secondary">← Edit answers</button></div>';
    html+='<aside class="scope-banner"><span class="scope-icon">i</span><div><strong>Limited information. Limited condition coverage.</strong><p>'+esc(result.safety.message)+'</p>'+result.limitations.map(l=>'<p>'+esc(l)+'</p>').join('')+'</div></aside>';
    if(result.safety.urgent)html+='<div class="safety-alert" role="alert"><h2>Seek urgent medical help now.</h2><p>'+esc(result.safety.message)+'</p>'+result.safety.sources.map(url=>'<a href="'+esc(url)+'" target="_blank" rel="noreferrer">Safety source ↗</a> ').join('')+'</div>';
    if(result.status==='ok'){
      html+='<div class="results-grid"><section>'+result.ranked_conditions.map(c=>{
        const line=e=>'<p class="evidence-line">'+esc(e.label)+'<small>'+esc(e.answer.state)+(e.answer.values.length?' · '+esc(e.answer.values.map(v=>byId[e.evidence_id].options.find(o=>String(o.value)===String(v))?.label||v).join(', ')):'')+'</small></p>';
        const e=c.explanation||{};
        return '<article class="condition-card"><div class="condition-head"><span class="rank">'+c.rank+'</span><div><span class="eyebrow">POSSIBLE CONDITION</span><h2>'+esc(c.name)+'</h2></div><span class="pill">Ranked match</span></div><p>Different conditions can share symptoms. A clinician may need further history, examination or testing.</p><div class="evidence-columns"><div><h3>Answers that increased the model match</h3>'+(e.supporting?.length?e.supporting.map(line).join(''):'<p class="muted">No meaningful supporting answer effect was found.</p>')+'</div><div><h3>Answers that reduced the model match</h3>'+(e.contradicting?.length?e.contradicting.map(line).join(''):'<p class="muted">No meaningful opposing answer effect was found.</p>')+'</div></div><p class="small-note">Whole-answer removal measures model effects, not medical causes.</p><div class="care-navigation"><strong>'+esc(c.recommended_specialty)+'</strong><p>'+esc(c.care_navigation)+'</p><a href="'+esc(c.reference.url)+'" target="_blank" rel="noreferrer">Source & dataset scope ↗</a><p class="small-note">'+esc(c.content_status)+'</p></div></article>';
      }).join('')+'</section><aside class="card"><h2>Connect answers to anatomy.</h2><p>Explore the regions relevant to your reviewed symptoms. A structure selection filters questions only.</p><button id="resultExplorer" class="button secondary full">Open relevant 3D anatomy ↗</button><div class="region-filters">'+[...new Set(known().filter(([k,a])=>a.state==='present').flatMap(([k])=>byId[k].regions))].map(r=>'<span class="pill">'+esc(navigation.regions[r].name)+'</span>').join('')+'</div><p class="small-note">Adult male reference anatomy. Different conditions can affect the same region.</p></aside></div>';
    }else html+='<section class="card"><h2>'+esc(result.status.replaceAll('_',' '))+'</h2><p>'+(result.status==='unsupported_scope'?'Your complaint is outside or uncertain within this limited catalogue. We will not force a condition match. Discuss your symptoms with a qualified clinician.':'Confirm at least one supported symptom Present. Unknown-only or absent-only input cannot establish useful possibilities.')+'</p></section>';
    html+='<div class="results-tools"><button id="nextFromResults" class="button secondary">Answer another question</button><form id="htmlResultsForm" method="post" action="/results"><input type="hidden" name="state" value="'+esc(JSON.stringify(state))+'"><button class="button secondary">Open printable summary</button></form></div>';
    panel.innerHTML=html;$('interviewPanel').hidden=true;$('interviewHeading').hidden=true;
    $('editResults').addEventListener('click',()=>{panel.hidden=true;$('interviewPanel').hidden=false;$('interviewHeading').hidden=false;});$('nextFromResults').addEventListener('click',()=>{$('editResults').click();$('nextQuestion').click();});$('resultExplorer')?.addEventListener('click',openExplorer);
    panel.scrollIntoView({block:'start'});$('editResults').focus();
  }
  function closeExplorer(){
    clearTimeout(explorerTimer);$('explorerDialog').close();$('explorerFrame').replaceChildren();$('openExplorer').focus();
  }
  function openExplorer(){
    $('explorerFrame').replaceChildren();$('explorerStatus').textContent='Loading anatomy… Roughly 33 MB of compressed geometry. Text regions remain available.';
    const frame=document.createElement('iframe');frame.title='Optional 3D adult male anatomy navigation';frame.src='/static/body-map/index.html';frame.referrerPolicy='no-referrer';$('explorerFrame').append(frame);$('explorerDialog').showModal();$('closeExplorer').focus();
    explorerTimer=setTimeout(()=>{$('explorerStatus').textContent='Anatomy loading is taking longer than expected. Close this viewer and use text regions; your answers are preserved.';},95000);
  }
  $('openExplorer').addEventListener('click',openExplorer);$('closeExplorer').addEventListener('click',closeExplorer);$('explorerDialog').addEventListener('cancel',e=>{e.preventDefault();closeExplorer();});
  window.addEventListener('message',event=>{
    const frame=$('explorerFrame').querySelector('iframe');if(!frame||event.origin!==location.origin||event.source!==frame.contentWindow)return;
    const data=event.data;if(!data||typeof data!=='object'||data.version!==1)return;
    if(data.type==='symptosphere:viewer-ready'){
      clearTimeout(explorerTimer);$('explorerStatus').textContent='Select anatomy to filter questions. Your model answers change only after you confirm them.';
      const relevant=[...new Set(known().filter(([k,a])=>a.state==='present').flatMap(([k])=>byId[k].regions))];
      const entry=Object.entries(navigation.concepts).find(([,c])=>relevant.includes(c.region));if(entry)frame.contentWindow.postMessage({type:'symptosphere:region-context',version:1,concept_id:entry[0]},location.origin);return;
    }
    if(data.type!=='symptosphere:anatomy-select'||typeof data.concept_id!=='string'||!Array.isArray(data.part_ids)||data.part_ids.length<1||data.part_ids.length>3000||new Set(data.part_ids).size!==data.part_ids.length||data.part_ids.some(id=>typeof id!=='string'))return;
    if(Object.keys(data).some(k=>!['type','version','concept_id','part_ids'].includes(k)))return;
    const c=navigation.concepts[data.concept_id];if(c&&!data.part_ids.every(id=>c.part_ids.includes(id)))return;
    region=c?.region||'general';$('symptomSearch').value='';limit=8;renderCards();
    $('appStatus').textContent=(c?.label||'Unmapped anatomy')+' selected for navigation. No symptom answer was changed.';
    closeExplorer();$('resultsPanel').hidden=true;$('interviewPanel').hidden=false;$('interviewHeading').hidden=false;$('symptomSearch').focus();
    document.querySelectorAll('[data-region]').forEach(b=>{const active=b.dataset.region===region;b.classList.toggle('active',active);b.setAttribute('aria-pressed',active);});
  });
  $('age').value=state.demographics.age??'';$('datasetSex').value=state.demographics.dataset_sex;$('complaintScope').value=state.complaint_scope||'supported';
  renderSafety();renderCards();renderSummary();
  document.addEventListener('sympto:language',()=>{renderSafety();renderCards();renderSummary();});
})();
