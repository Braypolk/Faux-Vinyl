import json,html,sys
from pathlib import Path
p=Path(__file__).resolve().parent;root=p.parent;items=json.loads((p/'inventory.json').read_text());cur=json.loads((p/'curation.json').read_text())if(p/'curation.json').exists()else{}
kind=sys.argv[1]if len(sys.argv)>1 else'vinyl';entries=[];seen=set()
for a in items:
 for c in a.get('candidate_images',[]):
  mid=c['image_id'];meta=root/'static/disc-review/images'/(mid+'.json')
  if c['kind']!=kind or not meta.exists()or mid in seen:continue
  if mid in cur:continue
  m=json.loads(meta.read_text());seen.add(mid);entries.append((a,c,m['file']))
for n in range(0,len(entries),30):
 s='<html><style>html,body{margin:0;font:10px sans-serif;background:#fff}.grid{display:grid;grid-template-columns:repeat(6,1fr);gap:8px}.im{aspect-ratio:1;width:100%;object-fit:contain;background:#e8e5de}p{margin:3px 0 8px;font-size:10px;overflow-wrap:anywhere}</style><div class="grid">'
 for a,c,f in entries[n:n+30]:s+='<div><img class="im" src="'+str(root/'static/disc-review/images'/f)+'"><p>'+html.escape(a['id']+' / '+c['image_id']+' / '+str(c['types'])+' / '+c.get('comment',''))+'</p></div>'
 s+='</div></html>';name=f'qa-{kind}-{n//30}.html';(p/name).write_text(s);print(name)
print('COUNT',len(entries))
