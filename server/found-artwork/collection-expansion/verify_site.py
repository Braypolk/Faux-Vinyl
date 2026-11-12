"""Read-only post-update verification; never sends playback actions."""
import argparse,hashlib,http.cookiejar,json,re
from html.parser import HTMLParser
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--cookies',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();s=requests.Session()
if a.cookies:
 jar=http.cookiejar.MozillaCookieJar(str(a.cookies));jar.load(ignore_discard=True,ignore_expires=True);s.cookies.update(jar)
def get(path):
 r=s.get(a.base+path,timeout=45);r.raise_for_status();return r
class Shelf(HTMLParser):
 def __init__(self,raw):super().__init__();self.records=[];self.feed(raw)
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if 'data-record-id' in d:self.records.append(d)
reports=json.loads((Path(__file__).parent/'integrated.json').read_text());dates=json.loads((ROOT/'release-dates.json').read_text());result={'records':0,'new_albums':9,'artwork_albums':len(reports),'checked_assets':0,'playback_triggered':False}
for order,reverse in [('newest',True),('oldest',False)]:
 page=get('/?sort='+order).text;records=Shelf(page).records;assert len(records)==63,len(records);result['records']=len(records)
 ordered=[dates[c['data-disc-key']]['date'] for c in records if c['data-disc-key'] in dates];assert len(ordered)==54;assert ordered==sorted(ordered,reverse=reverse)
 assert all(c['data-disc-key'].startswith('spotify:playlist:') for c in records[-9:])
 if order=='oldest':continue
 for album in reports:
  found=[c for c in records if c['data-disc-key']==album['uri']];assert len(found)==1,album['title'];c=found[0]
  assert c['data-front'] and c['data-back'],album['title']
  opts=json.loads(c['data-disc-options']);assert {'vinyl','cd'}<={o['kind'] for o in opts},album['title']
  urls=[c['data-front'],c['data-back']]+[o['image'] for o in opts]
  for url in urls:
   assert url.startswith('/static/'),url
   raw=get(url).content;local=ROOT/url.lstrip('/')
   assert hashlib.sha256(raw).digest()==hashlib.sha256(local.read_bytes()).digest(),url
   result['checked_assets']+=1
  edit=get(c['data-edit']).text;assert 'name="release_date" value="'+dates[album['uri']]['date']+'"' in edit
  nfc=get(c['data-play']).text;assert 'data-record-browser' in nfc and 'data-autoplay-id="'+c['data-record-id']+'"' in nfc
result['original_date_sorting']=True;result['both_formats_for_every_requested_album']=True;a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
