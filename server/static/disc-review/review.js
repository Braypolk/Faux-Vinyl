'use strict';
(()=>{
 const catalogue=JSON.parse(document.querySelector('#catalogue').textContent),albums=catalogue.albums;
 const key='fauxvinyl-disc-art-review-v1',allOptions=new Map(),byAlbum=new Map(albums.map(a=>[a.id,a]));
 albums.forEach(a=>a.candidates.forEach(c=>allOptions.set(c.id,{album:a,candidate:c})));
 let decisions=Object.fromEntries((catalogue.approved||[]).map(id=>[id,'approved'])),notes={},storageOK=true,active=null;
 const $=s=>document.querySelector(s),make=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e};
 try{const saved=JSON.parse(localStorage.getItem(key)||'{}');decisions={...decisions,...saved.decisions};notes=saved.notes||{}}catch{storageOK=false}
 function save(){try{localStorage.setItem(key,JSON.stringify({decisions,notes,updated:new Date().toISOString()}));$('#save-message').textContent='Saved in this browser. Export decisions to share them.'}catch{storageOK=false;$('#save-message').textContent='Browser saving is unavailable. Export decisions before closing this page.'}}
 function state(id){return ['approved','denied'].includes(decisions[id])?decisions[id]:'pending'}
 function approvedFormats(a){return new Set(a.candidates.filter(c=>state(c.id)==='approved').map(c=>c.kind))}
 function needsFormat(a){const formats=approvedFormats(a);return !formats.has('vinyl')||!formats.has('cd')}
 function counts(a){const s={approved:0,denied:0,pending:0};a.candidates.forEach(c=>s[state(c.id)]++);return s}
 function decide(id,value){decisions[id]=state(id)===value?'pending':value;save();update()}
 const elements=new Map(),sections=new Map();
 function showImage(id){active=id;const {album:a,candidate:c}=allOptions.get(id);$('#dialog-title').textContent=a.album+' · '+c.label;$('#dialog-image').src=c.inspect||c.preview;$('#dialog-image').alt=a.artist+' — '+a.album+' '+c.kind+' artwork';$('#dialog-caption').textContent=[c.note,c.edition].filter(Boolean).join(' · ');$('#dialog-original').href=c.original;updateDialog();if(!$('#inspect').open)$('#inspect').showModal()}
 function updateDialog(){if(!active)return;$('#dialog-approve').textContent=state(active)==='approved'?'Approved ✓':'Approve';$('#dialog-deny').textContent=state(active)==='denied'?'Denied ✓':'Deny';$('#dialog-approve').setAttribute('aria-pressed',String(state(active)==='approved'));$('#dialog-deny').setAttribute('aria-pressed',String(state(active)==='denied'))}
 function shiftImage(delta){const {album:a,candidate:c}=allOptions.get(active);const i=a.candidates.indexOf(c);showImage(a.candidates[(i+delta+a.candidates.length)%a.candidates.length].id)}
 for(const a of albums){
  const section=make('section','album');section.id='album-'+a.id;sections.set(a.id,section);
  const heading=make('div','album-heading');if(a.cover){const im=make('img','album-cover');im.src=a.cover;im.alt='';im.loading='lazy';heading.append(im)}
  const title=make('div');title.append(make('h2','album-title',a.album),make('div','artist',a.artist));heading.append(title,make('div','album-status'));section.append(heading);
  const options=make('div','options');
  a.candidates.forEach(c=>{
   const card=make('article','candidate'),photo=make('button','photo');photo.type='button';photo.setAttribute('aria-label','Inspect '+a.album+' '+c.label);
   const im=make('img');im.src=c.preview;im.alt=c.label;im.loading='lazy';im.width=im.height=300;im.addEventListener('error',()=>{photo.replaceChildren(make('span','broken','Image unavailable — open original'))});photo.append(im);photo.addEventListener('click',()=>showImage(c.id));card.append(photo);
   const info=make('div','candidate-info'),badges=make('div','badges');badges.append(make('span','badge '+c.kind,c.kind==='vinyl'?'VINYL':'CD'));
   if(c.user_reference)badges.append(make('span','badge','YOUR FIND'));
   if(c.broader_search)badges.append(make('span','badge','NEW'));
   if(c.quality==='full')badges.append(make('span','badge','FULL DISC'));
   if(c.quality==='mockup')badges.append(make('span','badge warning','MOCKUP'));
   if(c.quality==='partial')badges.append(make('span','badge warning','PARTIAL DISC'));
   if(c.status&&c.status!=='Official')badges.append(make('span','badge warning',c.status.toUpperCase()));
   if(c.quality==='label')badges.append(make('span','badge warning','LABEL ONLY'));
   if(c.quality==='packaging')badges.append(make('span','badge warning','PACKAGING'));
   info.append(badges,make('p','quality',c.note||c.label),make('p','edition',c.edition||''));
   const links=make('p','sources');for(const [label,url]of [['Source ↗',c.source],['Original ↗',c.original]]){const link=make('a','',label);link.href=url;link.target='_blank';link.rel='noopener';links.append(link)}info.append(links);card.append(info);
   const controls=make('div','decisions'),approve=make('button','approve','Approve'),deny=make('button','deny','Deny');approve.type=deny.type='button';approve.addEventListener('click',()=>decide(c.id,'approved'));deny.addEventListener('click',()=>decide(c.id,'denied'));controls.append(approve,deny);card.append(controls);options.append(card);elements.set(c.id,{card,approve,deny});
  });
  if(a.candidates.length){section.append(options);for(const kind of ['vinyl','cd'])if(!a.candidates.some(c=>c.kind===kind))section.append(make('div','empty','No '+(kind==='cd'?'CD':'vinyl')+' artwork found yet.'))}else section.append(make('div','empty',a.missing_reason||'No disc images found after checking the available vinyl and CD galleries.'));
  const footer=make('div','album-footer');if(a.candidates.length){const none=make('button','','None of these');none.type='button';none.addEventListener('click',()=>{a.candidates.forEach(c=>decisions[c.id]='denied');save();update()});footer.append(none)}
  const note=make('textarea');note.rows=1;note.maxLength=500;note.placeholder='Optional note';note.setAttribute('aria-label','Note for '+a.album);note.value=notes[a.id]||'';note.addEventListener('input',()=>{notes[a.id]=note.value;save()});footer.append(note);section.append(footer);
  const report=make('p','search-report');report.textContent=a.report||'';if(a.group){report.append(document.createTextNode(' · '));const link=make('a','','Release group ↗');link.href='https://musicbrainz.org/release-group/'+a.group;link.target='_blank';link.rel='noopener';report.append(link)}section.append(report);$('#albums').append(section);
 }
 catalogue.playlists.forEach(p=>$('#playlists').append(make('span','',p.title)));
 const vinyl=albums.filter(a=>a.candidates.some(c=>c.kind==='vinyl')).length,cdOnly=albums.filter(a=>a.candidates.length&&!a.candidates.some(c=>c.kind==='vinyl')).length;
 for(const [n,label]of [[albums.length,'albums'],[vinyl,'with vinyl options'],[cdOnly,'CD only'],[albums.filter(a=>!a.candidates.length).length,'without options'],[allOptions.size,'options']]){const item=make('div');item.append(make('strong','',String(n)),make('span','',label));$('#stats').append(item)}
 $('#research-summary').textContent=catalogue.summary||'';
 function update(){
  let n=0;for(const [id,e]of elements){const s=state(id);e.card.dataset.state=s;e.approve.setAttribute('aria-pressed',String(s==='approved'));e.deny.setAttribute('aria-pressed',String(s==='denied'));e.approve.textContent=s==='approved'?'Approved ✓':'Approve';e.deny.textContent=s==='denied'?'Denied ✓':'Deny';if(s!=='pending')n++}
  const remaining=albums.filter(needsFormat).length;$('#progress').textContent=remaining+' albums need vinyl or CD · '+(albums.length-remaining)+' complete';
  const q=$('#search').value.toLocaleLowerCase().trim(),filter=$('#filter').value;let visible=0;
  for(const a of albums){const c=counts(a),section=sections.get(a.id);const formats=approvedFormats(a),missing=['vinyl','cd'].filter(kind=>!formats.has(kind)).map(kind=>kind==='cd'?'CD':'vinyl');section.querySelector('.album-status').textContent=a.candidates.length?(missing.length?'Needs '+missing.join(' + '):'Both approved'):'No results';let match=needsFormat(a)&&(a.artist+' '+a.album).toLocaleLowerCase().includes(q);if(filter==='new')match&&=a.candidates.some(option=>option.broader_search);for(const option of a.candidates)elements.get(option.id).card.hidden=filter==='new'&&!option.broader_search;if(filter==='pending')match&&=c.pending>0;if(filter==='approved')match&&=c.approved>0;if(filter==='vinyl')match&&=a.candidates.some(c=>c.kind==='vinyl');if(filter==='cd')match&&=a.candidates.length>0&&!a.candidates.some(c=>c.kind==='vinyl');if(filter==='missing')match&&=['vinyl','cd'].some(kind=>!a.candidates.some(option=>option.kind===kind));section.hidden=!match;if(match)visible++}
  $('.no-results').hidden=visible>0;updateDialog();
 }
 $('#search').addEventListener('input',update);$('#filter').addEventListener('change',update);
 $('#export').addEventListener('click',()=>{
  const result={type:'fauxvinyl-disc-art-review',version:1,catalogue:catalogue.id,exported_at:new Date().toISOString(),albums:albums.map(a=>({id:a.id,uri:a.uri,artist:a.artist,album:a.album,notes:notes[a.id]||'',candidates:a.candidates.map(c=>({id:c.id,decision:state(c.id),kind:c.kind,image_id:c.image_id,release_id:c.release_id,original:c.original,source:c.source,preview:c.preview,status:c.status,quality:c.quality}))}))};
  const blob=new Blob([JSON.stringify(result,null,2)+'\n'],{type:'application/json'}),url=URL.createObjectURL(blob),link=make('a');link.href=url;link.download='fauxvinyl-disc-art-decisions.json';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);$('#save-message').textContent='Decisions exported. This does not apply artwork to the shelf.';
 });
 $('#import').addEventListener('click',()=>$('#import-file').click());$('#import-file').addEventListener('change',async()=>{try{const file=$('#import-file').files[0];if(!file)return;const d=JSON.parse(await file.text());if(d.type!=='fauxvinyl-disc-art-review'||!Array.isArray(d.albums))throw new Error('Choose a FauxVinyl decisions export.');let n=0;for(const a of d.albums){if(!byAlbum.has(a.id))continue;if(typeof a.notes==='string')notes[a.id]=a.notes.slice(0,500);for(const c of a.candidates||[])if(allOptions.has(c.id)&&['approved','denied','pending'].includes(c.decision)){decisions[c.id]=c.decision;n++}}document.querySelectorAll('.album textarea').forEach(t=>{t.value=notes[t.closest('.album').id.slice(6)]||''});save();update();$('#save-message').textContent='Imported '+n+' decisions.'}catch(e){$('#save-message').textContent=e.message}finally{$('#import-file').value=''}});
 $('#close-dialog').addEventListener('click',()=>$('#inspect').close());$('#inspect').addEventListener('click',e=>{if(e.target===$('#inspect'))$('#inspect').close()});$('#dialog-prev').addEventListener('click',()=>shiftImage(-1));$('#dialog-next').addEventListener('click',()=>shiftImage(1));$('#dialog-approve').addEventListener('click',()=>decide(active,'approved'));$('#dialog-deny').addEventListener('click',()=>decide(active,'denied'));$('#inspect').addEventListener('keydown',e=>{if(e.key==='ArrowRight'){e.preventDefault();shiftImage(1)}if(e.key==='ArrowLeft'){e.preventDefault();shiftImage(-1)}});
 if(!storageOK)$('#save-message').textContent='Browser saving is unavailable. Export decisions before closing.';
 update();
})();
