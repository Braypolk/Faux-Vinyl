"""Temporary research only: inventory and raw MusicBrainz/CAA candidates; no shelf writes."""
import concurrent.futures as cf
import hashlib,json,re,sqlite3,threading,time,unicodedata
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent.parent
OUT=Path(__file__).resolve().parent
CACHE=OUT/'cache'
UA='FauxVinylArtworkReview/0.1 (personal artwork research; https://bray.dev)'
lock=threading.Lock();mb_last=0

def fetch(url,params=None,mb=False):
 global mb_last
 key=hashlib.sha256((url+json.dumps(params or {},sort_keys=True)).encode()).hexdigest()
 p=CACHE/(key+'.json')
 if p.exists():return json.loads(p.read_text())
 for attempt in range(4):
  try:
   if mb:
    with lock:
     time.sleep(max(0,1.15-(time.monotonic()-mb_last)));mb_last=time.monotonic()
     r=requests.get(url,params=params,headers={'User-Agent':UA},timeout=35)
   else:r=requests.get(url,params=params,headers={'User-Agent':UA},timeout=35)
   if r.status_code==404:
    d={'_missing':True};p.write_text(json.dumps(d));return d
   if r.status_code in [429,500,502,503,504]:time.sleep(2*(attempt+1));continue
   r.raise_for_status();d=r.json();p.write_text(json.dumps(d));return d
  except Exception as e:
   if attempt==3:return {'_error':str(e),'url':url}
   time.sleep(2*(attempt+1))
 return {'_error':'HTTP retries exhausted','url':url}

def norm(s):return re.sub('[^a-z0-9]+','',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower())
def clean(s):
 s=re.sub(r'\s*\([^)]*(?:deluxe|remaster|expanded)[^)]*\)','',s,flags=re.I)
 s=re.sub(r':?\s*Deluxe Edition','',s,flags=re.I)
 return s.strip()

def discover():
 conn=sqlite3.connect('file:'+str(ROOT/'.dev-data/fauxvinyl.sqlite3')+'?mode=ro',uri=True);conn.row_factory=sqlite3.Row
 md=json.loads((ROOT/'search-metadata.json').read_text())
 inventory=[]
 for row in conn.execute('select id,title,uri from cards order by rowid'):
  a=dict(row);m=md.get(a['uri'],{});a.update(artist=m.get('artist','').split('\n')[0],album=m.get('album',a['title']),is_album=':album:' in a['uri'],groups=[],research_errors=[])
  inventory.append(a)
 (OUT/'inventory.json').write_text(json.dumps(inventory,indent=2))
 for a in inventory:
  if not a['is_album']:continue
  title=clean(a['album']);artist=a['artist']
  if a['id']=='seal':title='Seal'
  q=f'releasegroup:"{title}" AND artist:"{artist}"'
  result=fetch('https://musicbrainz.org/ws/2/release-group/',{'query':q,'fmt':'json','limit':12},True)
  groups=result.get('release-groups',[])
  if not groups:
   result=fetch('https://musicbrainz.org/ws/2/release-group/',{'query':f'"{title}" AND artist:"{artist}"','fmt':'json','limit':12},True);groups=result.get('release-groups',[])
  if result.get('_error'):a['research_errors'].append(result['_error'])
  def rank(g):
   score=int(g.get('score',0));score+=200 if g.get('primary-type')=='Album' else 0;score+=60 if norm(clean(g['title']))==norm(title) else 0
   ac=' '.join(x.get('name',x.get('artist',{}).get('name','')) for x in g.get('artist-credit',[]) if isinstance(x,dict))
   score+=30 if norm(artist) in norm(ac) else 0
   if a['id']=='seal':score+=100 if g.get('first-release-date','').startswith('1994') else -100
   return score
  groups.sort(key=rank,reverse=True)
  if a['uri']=='spotify:album:0S0KGZnfBGSIssfF54WSJh':
   groups.sort(key=lambda g:g['id']=='72375978-a9a1-4254-b957-85565c716b7e',reverse=True)
  # One actual album group; variants/deluxe releases are browsed inside it.
  if groups:
   g=groups[0];a['group']={k:g.get(k) for k in ['id','title','first-release-date','score','primary-type']}
   a['group_alternatives']=[{k:g.get(k) for k in ['id','title','score','first-release-date']} for g in groups[1:4]]
   releases=[];offset=0
   while True:
    data=fetch('https://musicbrainz.org/ws/2/release',{'release-group':g['id'],'inc':'media','fmt':'json','limit':100,'offset':offset},True)
    if data.get('_error'):a['research_errors'].append(data['_error']);break
    releases.extend(data.get('releases',[]));offset+=100
    if offset>=data.get('release-count',0):break
   a['release_count']=len(releases)
   a['releases']=[{'id':r['id'],'title':r['title'],'date':r.get('date',''),'country':r.get('country',''),'status':r.get('status',''),'edition':r.get('disambiguation',''),'formats':[m.get('format') or '' for m in r.get('media',[])], 'art_count':r.get('cover-art-archive',{}).get('count',0)} for r in releases]
  else:a['research_errors'].append('No matching MusicBrainz release group')
  (OUT/'inventory.json').write_text(json.dumps(inventory,indent=2))
  print('MATCH',a['id'],a.get('group',{}),'releases',a.get('release_count',0),flush=True)
 return inventory

def collect(inventory):
 tasks=[]
 for a in inventory:
  if not a['is_album']:continue
  a['candidate_images']=[];a['checked_vinyl']=0;a['checked_cd']=0
  for r in a.get('releases',[]):
   vinyl=any('Vinyl' in f for f in r['formats']);cd=any('CD'==f or 'Enhanced CD'==f for f in r['formats'])
   if (vinyl or cd) and r['art_count']:
    tasks.append((a,r,'vinyl' if vinyl else 'cd'))
 print('Scanning',len(tasks),'physical release galleries',flush=True)
 def gallery(t):
  a,r,kind=t;return t,fetch('https://coverartarchive.org/release/'+r['id'])
 with cf.ThreadPoolExecutor(max_workers=4) as ex:
  for n,(t,d) in enumerate(ex.map(gallery,tasks),1):
   a,r,kind=t;a['checked_'+kind]+=1
   if d.get('_error'):a['research_errors'].append({'release':r['id'],'error':d['_error']})
   for im in d.get('images',[]):
    types=im.get('types',[])
    if 'Medium' not in types and not (kind=='vinyl' and (not types or 'Other' in types)):continue
    if not im.get('approved',True):continue
    a['candidate_images'].append({'image_id':str(im['id']),'types':types,'comment':im.get('comment',''),'original':im['image'].replace('http:','https:'),'thumbnails':{k:v.replace('http:','https:') for k,v in im.get('thumbnails',{}).items()},'kind':kind,'release':r})
   if n%20==0:print('GALLERIES',n,'/',len(tasks),'medium images',sum(len(x.get('candidate_images',[])) for x in inventory),flush=True);(OUT/'inventory.json').write_text(json.dumps(inventory,indent=2))
 (OUT/'inventory.json').write_text(json.dumps(inventory,indent=2))
 print('CATALOGUES COMPLETE',sum(len(a.get('candidate_images',[]))for a in inventory),'raw candidates',flush=True)

if __name__=='__main__':
 import sys
 if '--collect' in sys.argv:inventory=json.loads((OUT/'inventory.json').read_text())
 else:inventory=discover()
 collect(inventory)
