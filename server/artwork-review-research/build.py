"""Build a separate, disposable disc-art approval board. Never edit shelf assets/state."""
import hashlib,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;OUT=Path(__file__).resolve().parent;WEB=ROOT/'static/disc-review'
def run():
 data=json.loads((OUT/'inventory.json').read_text());downloads=json.loads((OUT/'downloads.json').read_text());overrides=json.loads((OUT/'curation.json').read_text())if(OUT/'curation.json').exists()else{}
 supplemental=OUT/'broader-review-candidates.json'
 broader=json.loads(supplemental.read_text())if supplemental.exists()else[]
 art=json.loads((ROOT/'artwork.json').read_text());playlists=[];albums=[]
 import sqlite3
 conn=sqlite3.connect('file:'+str(ROOT/'.dev-data/fauxvinyl.sqlite3')+'?mode=ro',uri=True)
 custom={}
 for row in conn.execute('select card_id,side,filename from card_artwork'):custom.setdefault(row[0],{})[row[1]]=row[2]
 for a in data:
  if not a['is_album']:playlists.append({k:a[k]for k in ['id','title','uri']});continue
  item={k:a[k]for k in ['id','title','uri','artist','album']};item['group']=a.get('group',{}).get('id');item['candidates']=[]
  cover=custom.get(a['id'],{}).get('front')
  source=ROOT/'.dev-data/artwork'/cover if cover else ROOT/'static'/art.get(a['uri'],{}).get('front','')
  if source.is_file():
   name='cover-'+a['id']+source.suffix;shutil.copyfile(source,WEB/'images'/name);item['cover']='images/'+name
  options=[];seen=set()
  for c in a.get('candidate_images',[]):
   image_id=c['image_id'];local=downloads.get(image_id,{})
   if not local.get('file'):continue
   signature=(c['kind'],local['sha256'])
   if signature in seen:continue
   seen.add(signature)
   rule=overrides.get(image_id,{})
   if rule.get('exclude') or rule.get('quality') != 'full':continue
   types=c['types'];quality=rule.get('quality','unreviewed')
   if quality=='unreviewed' and 'Matrix/Runout'in types:quality='label'
   if quality=='unreviewed' and len(types)>1 and any(x in types for x in ['Front','Back','Tray','Panel','Spine']):quality='packaging'
   release=c['release'];edition=' · '.join(x for x in [release.get('edition'),release.get('country'),release.get('date'),' / '.join(release['formats'])]if x)
   note=rule.get('note')or c.get('comment')or ('Full record scan'if quality=='full'else 'Inspect before choosing')
   options.append({'id':a['id']+':'+image_id,'image_id':image_id,'release_id':release['id'],'kind':c['kind'],'label':('Vinyl'if c['kind']=='vinyl'else'CD')+' · '+(c.get('comment')or'Option'),'note':note,'quality':quality,'edition':edition,'status':release.get('status'),'preview':'images/'+local['file'],'inspect':'images/'+local['file'],'original':c['original'],'source':'https://musicbrainz.org/release/'+release['id']+'/cover-art','user_reference':image_id=='30672682790'})
  # Show the complete curated set of vinyl choices; CDs are included as fallbacks.
  for c in broader:
   if c['album_id']!=a['id']:continue
   signature=(c['kind'],c['sha256'])
   if signature in seen:continue
   seen.add(signature);options.append(c)
  options.sort(key=lambda c:(c['kind']!='vinyl',{'full':0,'mockup':1,'packaging':2,'partial':3,'label':4}.get(c['quality'],5),not c['user_reference'],c['status']!='Official',not c.get('broader_search',False),c['edition'],c['image_id']))
  item['candidates']=options
  extra=sum(bool(c.get('broader_search'))for c in options)
  item['report']=str(len(a.get('releases',[])))+' editions in release group · '+str(a.get('checked_vinyl',0))+' vinyl galleries and '+str(a.get('checked_cd',0))+' CD galleries with artwork checked'
  if extra:item['report']+=' · '+str(extra)+' broader-search options'
  if a.get('research_errors'):item['report']+=' · '+str(len(a['research_errors']))+' release galleries unavailable'
  failed=sum(not downloads.get(c['image_id'],{}).get('file')for c in a.get('candidate_images',[]))
  if failed:item['report']+=' · '+str(failed)+' source images unavailable'
  item['missing_reason']=overrides.get('album:'+a['id'],{}).get('missing_reason','No full-disc artwork found in the available vinyl and CD galleries. The shelf stays unchanged.')
  albums.append(item)
 albums.sort(key=lambda a:(0 if any(c['kind']=='vinyl'for c in a['candidates'])else 1 if a['candidates']else 2))
 catalogue={'id':'disc-review-20261111-v1','created':'2026-11-11','albums':albums,'playlists':playlists,'summary':'Expanded search: MusicBrainz, Discogs, artist and label stores, and retailer galleries. Clean full-disc images come first within each format; mockups, packaging, partial records and label-only fallbacks are marked. Backgrounds are untouched. Approval does not apply artwork automatically.'}
 approved=ROOT/'found-artwork/approved-discs/approved-decisions.json'
 catalogue['approved']=[c['id']for c in json.loads(approved.read_text())]if approved.exists()else[]
 encoded=json.dumps(catalogue,ensure_ascii=False).replace('<','\\u003c')
 template=(OUT/'review-template.html').read_text();html=template.replace('__CATALOGUE__',encoded)
 # The existing app blocks inline JS/CSS. Serve independent prototype files.
 css=re.search(r'<style>(.*?)</style>',html,re.S).group(1)
 js=re.search(r'<script>\n(.*?)</script>',html,re.S).group(1)
 served=re.sub(r'<style>.*?</style>','<link rel="stylesheet" href="review.css">',html,flags=re.S)
 served=re.sub(r'<script>\n.*?</script>','<script defer src="review.js"></script>',served,flags=re.S)
 (WEB/'index.html').write_text(served);(WEB/'review.css').write_text(css);(WEB/'review.js').write_text(js);(WEB/'catalogue.json').write_text(json.dumps(catalogue,indent=2,ensure_ascii=False)+'\n')
 (OUT/'inline-review.html').write_text(html)
 print('Built',len(albums),'albums,',sum(len(a['candidates'])for a in albums),'options,',len(playlists),'playlists')
if __name__=='__main__':run()
