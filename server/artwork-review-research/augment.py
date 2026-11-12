"""Check untyped/Other vinyl images and retry the five unavailable galleries."""
import json,concurrent.futures as cf
from pathlib import Path
from gather import fetch,OUT
items=json.loads((OUT/'inventory.json').read_text());tasks=[]
for a in items:
 for r in a.get('releases',[]):
  if not r['art_count']:continue
  vinyl=any('Vinyl'in f for f in r['formats']);cd=any('CD'in f for f in r['formats'])
  if vinyl or cd:tasks.append((a,r,'vinyl'if vinyl else'cd'))
def get(t):return t,fetch('https://coverartarchive.org/release/'+t[1]['id'])
added=0
with cf.ThreadPoolExecutor(max_workers=4)as ex:
 for (a,r,kind),d in ex.map(get,tasks):
  if d.get('_error'):continue
  a['research_errors']=[e for e in a.get('research_errors',[])if not(isinstance(e,dict)and e.get('release')==r['id'])]
  known={(c['image_id'],c['release']['id'])for c in a['candidate_images']}
  for im in d.get('images',[]):
   types=im.get('types',[])
   if 'Medium'not in types and not(not types or'Other'in types):continue
   if not im.get('approved',True)or(str(im['id']),r['id'])in known:continue
   a['candidate_images'].append({'image_id':str(im['id']),'types':types,'comment':im.get('comment',''),'original':im['image'].replace('http:','https:'),'thumbnails':{k:v.replace('http:','https:')for k,v in im.get('thumbnails',{}).items()},'kind':kind,'release':r});added+=1
(OUT/'inventory.json').write_text(json.dumps(items,indent=2));print('Supplemental candidates',added,'remaining failed galleries',sum(len(a.get('research_errors',[]))for a in items),flush=True)
