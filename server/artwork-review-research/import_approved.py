"""Import only positive decisions; download source images without changing originals."""
import argparse
import concurrent.futures as cf
import hashlib
import html
import json
from pathlib import Path
import requests
from PIL import Image
from io import BytesIO

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'found-artwork'/'approved-discs'
OUT.mkdir(parents=True,exist_ok=True)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('decisions',nargs='?',type=Path,default=OUT/'decisions-export.json')
ATTACHMENT=parser.parse_args().decisions
decisions=json.loads(ATTACHMENT.read_text())
catalogue=json.loads((ROOT/'static/disc-review/catalogue.json').read_text())
known={c['id']:(a,c)for a in catalogue['albums']for c in a['candidates']}
inventory=json.loads((ROOT/'artwork-review-research/inventory.json').read_text())
raw={c['image_id']:c for a in inventory for c in a.get('candidate_images',[])}
approved=[]
for album in decisions['albums']:
 for option in album['candidates']:
  if option['decision']!='approved':continue
  original_album,candidate=known[option['id']]
  assert original_album['uri']==album['uri'] and candidate['image_id']==option['image_id']
  approved.append({**candidate,'album_id':album['id'],'uri':album['uri'],'album':album['album'],'artist':album['artist']})
assert len({x['id']for x in approved})==len(approved)
(OUT/'approved-decisions.json').write_text(json.dumps(approved,indent=2,ensure_ascii=False)+'\n')

def get(c):
 mid=c['image_id'];dest=OUT/(mid+'-source.jpg');meta=OUT/(mid+'-source.json')
 if dest.exists() and meta.exists():return c|json.loads(meta.read_text())
 urls=[raw[mid]['thumbnails'].get('1200'),c['original']]
 errors=[]
 for url in dict.fromkeys(u for u in urls if u):
  try:
   response=requests.get(url,timeout=30,headers={'User-Agent':'FauxVinyl/1.0 (personal artwork collection; https://bray.dev)'})
   response.raise_for_status();data=response.content;im=Image.open(BytesIO(data));im.verify()
   dest.write_bytes(data)
   with Image.open(dest)as im:width,height=im.size
   result={'download_url':url,'source_file':dest.name,'width':width,'height':height,'sha256':hashlib.sha256(data).hexdigest()}
   meta.write_text(json.dumps(result,indent=2)+'\n');print(mid,width,height,flush=True)
   return c|result
  except Exception as e:errors.append(str(e))
 # Retain the exact approved scan if the archive cannot deliver a larger copy.
 old=ROOT/'static/disc-review'/c['preview'];data=old.read_bytes();dest.write_bytes(data)
 with Image.open(dest)as im:width,height=im.size
 result={'download_url':str(c['preview']),'source_file':dest.name,'width':width,'height':height,'sha256':hashlib.sha256(data).hexdigest(),'larger_source_unavailable':errors}
 meta.write_text(json.dumps(result,indent=2)+'\n');print(mid,'approved preview fallback',flush=True);return c|result

if __name__=='__main__':
 with cf.ThreadPoolExecutor(max_workers=5)as ex:results=list(ex.map(get,approved))
 (OUT/'sources.json').write_text(json.dumps(results,indent=2,ensure_ascii=False)+'\n')
 s='<html><style>body{margin:0;background:white;font:11px sans-serif}.grid{display:grid;grid-template-columns:repeat(6,1fr);gap:8px}img{width:100%;aspect-ratio:1;object-fit:contain;background:#ddd}p{margin:3px 0 12px;font-size:10px}</style><div class="grid">'
 for i,c in enumerate(results):s+='<div><img src="'+str(OUT/c['source_file'])+'"><p>'+html.escape(f"{i}: {c['album_id']} / {c['image_id']} / {c['kind']} / {c['width']}×{c['height']}")+'</p></div>'
 (OUT/'sources-review.html').write_text(s+'</div></html>')
 print('Complete:',len(results),'approved images.',flush=True)
