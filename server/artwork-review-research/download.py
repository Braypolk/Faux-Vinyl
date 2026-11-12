"""Download unedited review thumbnails; retain exact provenance and dimensions."""
import concurrent.futures as cf,hashlib,json,time
from pathlib import Path
from io import BytesIO
import requests
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent;OUT=Path(__file__).resolve().parent;DEST=ROOT/'static/disc-review/images'
UA='FauxVinylArtworkReview/0.1 (personal artwork research; https://bray.dev)'
def run():
 data=json.loads((OUT/'inventory.json').read_text());unique={}
 for a in data:
  for c in a.get('candidate_images',[]):
   if c['image_id'] not in unique:unique[c['image_id']]=c
 def get(c):
  imid=c['image_id'];meta=DEST/(imid+'.json')
  if meta.exists():return imid,json.loads(meta.read_text())
  url=c['thumbnails'].get('500')or c['thumbnails'].get('large')or c['original'];error=''
  for n in range(3):
   try:
    response=requests.get(url,timeout=35,headers={'User-Agent':UA});response.raise_for_status();raw=response.content
    image=Image.open(BytesIO(raw));width,height=image.size;fmt=image.format.lower();ext={'jpeg':'jpg'}.get(fmt,fmt)
    if ext not in ['jpg','png','webp','gif']:ext='jpg'
    name=imid+'.'+ext;(DEST/name).write_bytes(raw)
    record={'file':name,'url':url,'width':width,'height':height,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};meta.write_text(json.dumps(record));return imid,record
   except Exception as e:error=str(e);time.sleep(n+1)
  return imid,{'error':error,'url':url}
 results={}
 with cf.ThreadPoolExecutor(max_workers=5)as ex:
  for n,(imid,r)in enumerate(ex.map(get,unique.values()),1):
   results[imid]=r
   if n%30==0:print('Downloaded',n,'/',len(unique),flush=True);(OUT/'downloads.json').write_text(json.dumps(results,indent=2))
 (OUT/'downloads.json').write_text(json.dumps(results,indent=2));print('DOWNLOAD COMPLETE',len(results),'errors',sum('error'in r for r in results.values()),flush=True)
if __name__=='__main__':run()
