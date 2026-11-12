"""Validate prepared batches, then merge public catalogue assets deterministically."""
import hashlib,json,re,shutil
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BATCHES=['noah','taylor-ariana','rihanna-beyonce','tame-rks','harry-olivia']
def read(path):return json.loads(path.read_text())
def save(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inspect_disc(path,kind):
 with Image.open(path) as im:
  assert im.size==(648,648),(path,im.size)
  assert im.mode=='RGBA' and im.format=='WEBP',(path,im.mode,im.format)
  a=im.getchannel('A');assert a.getbbox()==(4,4,644,644),(path,a.getbbox())
  assert a.getpixel((324,324))==0 and a.getpixel((324,20))>200,(path,'hole or rim missing')
  assert all(a.getpixel(p)==0 for p in [(0,0),(647,647),(324,0),(0,324),(647,324),(324,647)]),(path,'background not transparent')
  # Full, smoothly normalized annulus and concentric aperture: no white corners,
  # missing sections, tray spindle or accidental opaque padding.
  import math
  hole=40 if kind=='cd' else 8
  for angle in range(0,360,3):
   theta=math.radians(angle)
   for r in [hole+6,100,180,260,315]:
    x,y=round(323.5+r*math.cos(theta)),round(323.5+r*math.sin(theta))
    assert a.getpixel((x,y))>200,(path,'missing annulus',angle,r)
   for r in [0,max(1,hole-3)]:
    x,y=round(323.5+r*math.cos(theta)),round(323.5+r*math.sin(theta))
    assert a.getpixel((x,y))<20,(path,'off-center aperture',angle,r)
reports=[]
for batch in BATCHES:
 data=read(HERE/batch/'report.json')
 if isinstance(data,dict):data=data.get('albums',data.get('entries'))
 assert isinstance(data,list),(batch,'report must be list')
 reports.extend(data)
assert len(reports)==11,len(reports)
uris=set();ids=set()
for album in reports:
 uri=album['uri'];assert re.fullmatch(r'spotify:album:[A-Za-z0-9]{22}',uri),uri
 assert uri not in uris,uri;uris.add(uri)
 assert album['title'] and album['artist']
 discs=album['discs'];assert {'vinyl','cd'}<={d['kind'] for d in discs},album['title']
 for disc in discs:
  p=Path(disc['path']);assert p.is_file(),p;assert disc['source'] and disc['method']
  inspect_disc(p,disc['kind'])
 for side in ['front','back']:
  if side in album:
   p=Path(album[side]['path']);assert p.is_file(),p
   with Image.open(p) as im:assert im.format=='WEBP' and im.width>=300 and im.height>=300,(p,im.size,im.format)
seed=read(ROOT/'seed-cards.json');art=read(ROOT/'artwork.json');discs=read(ROOT/'disc-artwork.json');sources=read(ROOT/'disc-artwork-sources.json');metadata=read(ROOT/'search-metadata.json');dates=read(ROOT/'release-dates.json');names=read(ROOT/'catalogue-names.json')
existing_requested={'spotify:album:69BqE1V8Bzb9GCyeP1fFeR','spotify:album:3WZZF72ihlKPZBS4zSsNHl'}
old_discs=sum(map(len,discs.values()));added=[];integrated=[]
for album in reports:
 uri=album['uri'];base=re.sub(r'[^a-z0-9]+','-',album['id'].lower()).strip('-');assert base
 record={k:album[k] for k in ['title','uri']};record['id']=base
 existing=next((c for c in seed if c['uri']==uri),None)
 if existing is None:
  assert record['id'] not in {c['id'] for c in seed}
  seed.append(record)
  songs=album.get('songs','');songs='\n'.join(songs) if isinstance(songs,list) else songs
  assert songs and len(songs.encode())<64000,(uri,'missing songs')
  metadata[uri]={'artist':album['artist'],'album':album['title'],'songs':songs}
  date=album['release_date'];assert re.fullmatch(r'\d{4}-\d{2}-\d{2}',date),date
  dates[uri]={'date':date,'artist':album['artist'],'album':album['title'],'source':album.get('release_source',album.get('source','https://open.spotify.com/album/'+uri.split(':')[-1]))}
  names['entries'].append({**record,'previous_title':record['title'],'artist':album['artist'],'source':'https://open.spotify.com/album/'+uri.split(':')[-1]})
 if uri not in existing_requested:added.append(record)
 merged={**album,'assets':{}}
 for side in ['front','back']:
  if side not in album:continue
  item=album[side];src=Path(item['path']);name=f'covers/collection/{base}.{side}.{digest(src)[:12]}.webp';dst=ROOT/'static'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
  art.setdefault(uri,{})[side]=name;merged['assets'][side]='/static/'+name
 for item in album['discs']:
  src=Path(item['path']);image_id='collection-'+base+'-'+item['kind']
  if sum(d['kind']==item['kind'] for d in album['discs'])>1:image_id+='-'+re.sub(r'[^a-z0-9]+','-',item['id'].lower()).strip('-')
  assert image_id not in ids;ids.add(image_id)
  filename=image_id+'.'+digest(src)[:12]+'.webp';dst=ROOT/'static/discs'/filename;shutil.copy2(src,dst);url='/static/discs/'+filename
  label=({'vinyl':'Vinyl','cd':'CD'}[item['kind']] if sum(d['kind']==item['kind'] for d in album['discs'])==1 else item.get('label') or item['kind'].title())
  option={'id':image_id,'kind':item['kind'],'label':label,'image':url}
  existing=discs.setdefault(uri,[]);existing[:]=[d for d in existing if d['id']!=image_id];existing.append(option)
  source={**item,'id':base+':'+image_id,'image_id':image_id,'album_id':base,'album':album['title'],'artist':album['artist'],'uri':uri,'output':url,'sha256':digest(src)}
  sources[:]=[s for s in sources if s.get('image_id')!=image_id];sources.append(source)
  merged['assets'][item['kind']]=url
 integrated.append(merged)
assert len(added)==9,[(c['id'],c['title']) for c in added]
for filename,obj in [('seed-cards.json',seed),('artwork.json',art),('disc-artwork.json',discs),('disc-artwork-sources.json',sources),('search-metadata.json',metadata),('release-dates.json',dates),('catalogue-names.json',names)]:save(ROOT/filename,obj)
save(HERE/'cards.json',added);save(HERE/'integrated.json',integrated)
save(HERE/'prompts.json',[{'album':a['title'],'kind':d['kind'],'prompt':d.get('prompt'),'notes':d.get('notes')} for a in reports for d in a['discs'] if d.get('prompt')])
print(json.dumps({'added_albums':len(added),'seed_records':len(seed),'dated_albums':len(dates),'disc_options_before':old_discs,'disc_options_after':sum(map(len,discs.values())),'albums_with_disc_options':len(discs),'new_disc_assets':len(ids)},indent=2))
