// Package the complete disposable board for the conversation renderer.
const fs=require('node:fs'),path=require('node:path'),{JSDOM}=require('jsdom');
const root=path.resolve(__dirname,'..'),web=path.join(root,'static/disc-review');
const script=fs.readFileSync(path.join(web,'review.js'),'utf8');
const dom=new JSDOM(fs.readFileSync(path.join(web,'index.html'),'utf8'),{url:'http://127.0.0.1:18787/static/disc-review/',runScripts:'outside-only'});
dom.window.eval(script);
const d=dom.window.document;
d.querySelector('script[src]').remove();
d.querySelector('link[rel=stylesheet]').remove();
for(const im of d.querySelectorAll('img[src]'))im.setAttribute('src',path.join(web,im.getAttribute('src')));
let hydrated=script.replace(/ for\(const a of albums\)\{\n  const section[\s\S]*? \$\('#research-summary'\)\.textContent=catalogue\.summary\|\|'';/,`
 for(const a of albums){
  const section=document.getElementById('album-'+a.id);sections.set(a.id,section);
  const cards=section.querySelectorAll('.candidate');
  a.candidates.forEach((c,i)=>{const card=cards[i],approve=card.querySelector('.approve'),deny=card.querySelector('.deny');elements.set(c.id,{card,approve,deny});approve.addEventListener('click',()=>decide(c.id,'approved'));deny.addEventListener('click',()=>decide(c.id,'denied'));card.querySelector('.photo').addEventListener('click',()=>showImage(c.id))});
  const none=section.querySelector('.album-footer button');if(none)none.addEventListener('click',()=>{a.candidates.forEach(c=>decisions[c.id]='denied');save();update()});
  const note=section.querySelector('textarea');note.value=notes[a.id]||'';note.addEventListener('input',()=>{notes[a.id]=note.value;save()});
 }
`);
hydrated=hydrated.replace("$('#dialog-image').src=c.inspect||c.preview","$('#dialog-image').src=elements.get(id).card.querySelector('img').src");
const css=d.createElement('style');css.textContent=fs.readFileSync(path.join(web,'review.css'),'utf8').replaceAll('94dvh','900px').replaceAll('65dvh','600px')+`
:root{background:transparent;color:var(--foreground);font-family:var(--font-sans);--ink:var(--foreground);--muted:var(--muted-foreground);--line:var(--border);--green:var(--success);--red:var(--destructive)}html,body{background:transparent}header,main,.toolbar-inner{padding-inline:0}header{padding-top:0}header .eyebrow,header h1{display:none}.toolbar{background:var(--background)}.candidate{background:var(--card)}button,input,select,textarea,.toolbar input[type=search],.toolbar select,.album-footer textarea{background:var(--card);color:var(--foreground)}button:hover{background:var(--secondary)}.empty{background:var(--secondary)}#albums{max-height:1300px;overflow:auto;padding-right:4px}.photo{background:var(--secondary)}.quality{color:var(--foreground)}.badge{color:var(--muted-foreground);border-color:var(--border)}dialog{background:var(--card)}.export{background:var(--primary);color:var(--primary-foreground)}.candidate[data-state=denied]{background:var(--destructive-surface)}@media(max-width:600px){header,main,.toolbar-inner{padding-inline:0}}
`;
d.head.append(css);
const js=d.createElement('script');js.textContent=hydrated;d.body.append(js);
fs.writeFileSync(path.join(__dirname,'conversation-review.html'),dom.serialize());
console.log('Packaged complete board for inline review.');
dom.window.close();
