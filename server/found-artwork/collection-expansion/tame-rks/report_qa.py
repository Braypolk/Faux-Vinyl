from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
p=Path(__file__).resolve().parent
validation=[];sheet=Image.new('RGB',(1320,710),'#d8d4cd');draw=ImageDraw.Draw(sheet)
for i,(name,hole) in enumerate([('slow-rush-vinyl.webp',16),('slow-rush-cd.webp',80),('freefall-vinyl.webp',16),('freefall-cd.webp',80)]):
 im=Image.open(p/name);a=np.asarray(im.getchannel('A'));y,x=np.where(a>127);box=[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)];yy,xx=np.mgrid[:648,:648];r=np.hypot(xx-323.5,yy-323.5)
 assert im.size==(648,648) and im.mode=='RGBA' and box==[4,4,644,644],(name,box)
 assert not a[:4,:].any() and not a[-4:,:].any() and not a[:,:4].any() and not a[:,-4:].any()
 assert np.all(a[r<hole/2-1]==0) and np.all(a[(r>hole/2+2)&(r<318)]==255),name
 validation.append({'file':name,'size':[648,648],'mode':'RGBA','alpha_bbox':box,'center':[324,324],'hole_diameter':hole,'opaque_annulus':True,'file_bytes':(p/name).stat().st_size})
 bg=Image.new('RGBA',im.size,'#ddd7cd');bg.alpha_composite(im);bg=bg.convert('RGB');bg.thumbnail((320,320));sheet.paste(bg,(i*330,0));draw.text((i*330+4,325),name,fill='black')
for i,name in enumerate(['slow-rush-front.webp','slow-rush-back.webp','freefall-front.webp','freefall-back.webp']):
 im=Image.open(p/name);im.thumbnail((320,320));sheet.paste(im.convert('RGB'),(i*330,360));draw.text((i*330+4,687),name,fill='black')
sheet.save(p/'finals-contact.jpg');(p/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
sources=json.loads((p/'download-sources.json').read_text());dm=json.loads((p/'rks-discogs-main.json').read_text());cd=json.loads((p/'11859663-discogs.json').read_text())
def item(file,source,method,notes=''):return {'path':str(p/file),'source':source,'method':method,'notes':notes}
report=[]
for stem,slug,date in [('slow-rush','the-slow-rush','2020-02-14'),('freefall','how-to-friend-love-freefall','2018-04-06')]:
 d=json.loads((p/(stem+'-spotify.json')).read_text())
 a={'id':slug,'title':d['title'],'artist':d['subtitle'],'uri':d['uri'],'release_date':date,'songs':[x['title'] for x in d['trackList']],'metadata_sources':['https://open.spotify.com/album/'+d['id']],'front':item(stem+'-front.webp',sources[stem+'-front.jpg'],'PhotoCraft lossily optimized official Spotify front artwork'),'discs':[]}
 if stem=='slow-rush':
  a['metadata_sources']+=['https://interscope.com/products/the-slow-rush-2lp']
  a['back']=item('slow-rush-back.webp','https://coverartarchive.org/release/1cf564b9-4e24-4362-89fb-1aa702ff60f2/46047919208.jpg','PhotoCraft optimized original CD back scan','Physical rectangular CD back artwork retained without inventing square edges.')
  a['discs']=[{'id':'slow-rush-red-vinyl','kind':'vinyl','label':'Red vinyl · Side A',**item('slow-rush-vinyl.webp','https://eu.rarevinyl.com/de/products/tame-impala-the-slow-rush-red-and-blue-vinyl-plus-bonus-7-plus-shrink-uk-2-lp-vinyl-record-double-0846007-810213','PhotoCraft ellipse/spindle rectification and circular alpha cutout','Actual red vinyl pressing with blue side-A label; source surface marks and subtle edge reflections retained. No generated content.'),'prompt':None},{'id':'slow-rush-red-cd','kind':'cd','label':'CD',**item('slow-rush-cd.webp','https://coverartarchive.org/release/452ccdb4-d6f5-4ac2-9eea-3eb2df8e5bb6/27821463908.jpg','PhotoCraft ellipse/spindle rectification and circular alpha cutout','Genuine Japanese CD scan. Complete printed design and clear/white hub pixels retained around normalized80px hole. No generated content.'),'prompt':None}]
 else:
  a['metadata_sources']+=['https://shop.rksband.com/products/how-to-friend-love-freefall-lp']
  a['back']=item('freefall-back.webp','https://www.discogs.com/release/11825457-Rainbow-Kitten-Surprise-How-To-Friend-Love-Freefall','PhotoCraft optimized original vinyl back scan','Clean full physical LP rear artwork, image index1 from Discogs original2018 vinyl release.')
  a['discs']=[{'id':'freefall-purple-vinyl','kind':'vinyl','label':'Purple vinyl · Side B',**item('freefall-vinyl.webp','https://www.turntablelab.com/products/rainbow-kitten-surprise-how-to-friend-love-freefall-indie-exclusive-colored-vinyl-vinyl-lp','PhotoCraft projective ellipse/spindle rectification and circular alpha cutout','Complete foreground purple LP extracted from retailer photo. Corrected oblique perspective using measured outer ellipse and actual spindle, preserving all original label/surface pixels. Photographic lighting highlights retained. This is sideB as printed; no generated content.'),'prompt':None},{'id':'freefall-cd','kind':'cd','label':'CD',**item('freefall-cd.webp','https://www.discogs.com/release/11859663-Rainbow-Kitten-Surprise-How-To-Friend-Love-Freefall','PhotoCraft ellipse/spindle rectification and circular alpha cutout','Actual full CD photograph from original European2018 release image index2. Some original lighting/scan texture retained; printed Jupiter artwork preserved. No generated content.'),'prompt':None}]
 report.append(a)
(p/'report.json').write_text(json.dumps(report,indent=2)+'\n')
