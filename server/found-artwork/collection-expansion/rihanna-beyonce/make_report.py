import json
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np
HERE=Path(__file__).resolve().parent
P=lambda name:str(HERE/name)
def load(name):return json.loads((HERE/name).read_text())
def discog_source(prefix,index):return {'release_page':f'https://www.discogs.com/release/{20978806 if prefix=="anti" else 5890382}','image_url':load(prefix+'-discogs.json')['images'][index]['uri']}
def caa_source(prefix,image_id):
 gallery=load(prefix+'-cd-gallery.json')
 row=next(x for x in gallery['images'] if str(x['id'])==str(image_id))
 return {'release_page':gallery['release'],'image_url':row['image'].replace('http:','https:')}
def art(prefix,which,idx):return {'path':P(prefix+'-'+which+'.webp'),'source':discog_source(prefix,idx),'method':'Original physical sleeve photograph retained and converted with PhotoCraft; no generated imagery.','notes':'Small native scan resolution and lighting/embossing retained; no AI relettering.'}
def disc(prefix,kind,source,notes,reconstruct=False):
 return {'id':prefix+'-'+kind+'-collection-v1','kind':kind,'label':'Red vinyl' if prefix=='anti' and kind=='vinyl' else kind.upper() if kind=='cd' else 'Black vinyl','path':P(prefix+'-'+kind+'.webp'),'source':source,'method':'reference-reconstruction-original-label' if reconstruct else 'photocraft-cutout','prompt':(HERE/'beyonce-vinyl-prompt.txt').read_text().strip() if reconstruct else None,'notes':notes,'processing':'PhotoCraft measured ellipse normalization, circle-preserving spindle alignment, opaque 640px circular annulus, centered transparent '+('16px' if kind=='vinyl' else '80px')+' aperture, centered 648px RGBA lossless WebP with 4px transparent margin.','reference_path':P('beyonce-discogs-4.jpg') if reconstruct else P('anti-discogs-3.jpg' if prefix=='anti' and kind=='vinyl' else 'anti-cd-24278005176.jpg' if prefix=='anti' else 'beyonce-cd-37516036127.jpg')}
report=[]
for prefix,title,artist,date in [('anti','ANTI','Rihanna','2016-01-28'),('beyonce','BEYONCÉ','Beyoncé','2013-12-13')]:
 spotify=load(prefix+'-spotify.json')
 record={'id':prefix,'title':title,'artist':artist,'uri':spotify['uri'],'release_date':date,'songs':'\n'.join(x['title'] for x in spotify['trackList']),'tracks':[{'name':x['title'],'uri':x['uri'],'artists':x['subtitle']} for x in spotify['trackList']],'metadata_sources':[f'https://open.spotify.com/album/{spotify["id"]}', 'https://www.rihannanow.com/music/anti/' if prefix=='anti' else 'https://open.spotify.com/track/2BruZeV86mhihFs4wVuKSt'],'front':art(prefix,'front',1 if prefix=='anti' else 0),'back':art(prefix,'back',2 if prefix=='anti' else 3)}
 if prefix=='anti':
  record['notes']='Spotify playback uses the 16-track Deluxe album; sorting uses the original ANTI album release date Jan 28, 2016, rather than the Deluxe Jan 29 date or vinyl repress date.'
  record['discs']=[disc(prefix,'vinyl',discog_source(prefix,3),'Actual red opaque 2021 RIH-ISSUE pressing, side A. Original printed cream label and photographed disc surface retained; sleeve/background removed. No generated image.'),disc(prefix,'cd',caa_source(prefix,24278005176),'Actual white ANTI CD scan. Original printed face, lettering, reflective rim and plastic hub retained. No generated image.')]
 else:
  record['notes']='Original 14-track album; sorting uses Dec 13, 2013 rather than the later Spotify catalogue/reissue date.'
  record['discs']=[disc(prefix,'vinyl',discog_source(prefix,4),'Full black groove field/rim reconstructed with built-in image_gen using the official vinyl side A label reference. The original photographed printed label is composited back at 240px diameter with PhotoCraft, retaining title, track lettering and surface texture. A 26px central hub region was filled near-black before the 16px hole to remove the photographed background/large aperture. Groove reflections are approximate; final is explicitly a reconstruction, not an authentic full-disc scan.',True),disc(prefix,'cd',caa_source(prefix,37516036127),'Actual original black/pink BEYONCÉ CD scan. Original printed face, lettering, silver rim and plastic hub retained. No generated image.')]
 report.append(record)
(HERE/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
qa=[]
for record in report:
 for d in record['discs']:
  im=Image.open(d['path']);a=np.array(im)[:,:,3];y,x=np.indices(a.shape);r=np.sqrt((x-323.5)**2+(y-323.5)**2);h=8 if d['kind']=='vinyl' else 40
  q={'id':d['id'],'mode':im.mode,'size':list(im.size),'alpha_bbox':list(im.getbbox()),'annulus_alpha_min':int(a[(r>h+2)&(r<318)].min()),'hole_alpha_max':int(a[r<h-2].max()),'outside_alpha_max':int(a[r>322].max()),'visual_inspection':'passed individually'}
  assert q['mode']=='RGBA' and q['size']==[648,648] and q['alpha_bbox']==[4,4,644,644] and q['annulus_alpha_min']==255 and q['hole_alpha_max']==0 and q['outside_alpha_max']==0
  qa.append(q)
(HERE/'validation.json').write_text(json.dumps(qa,indent=2)+'\n')
canvas=Image.new('RGB',(4*330,2*370),'#e7e2d7');draw=ImageDraw.Draw(canvas)
for i,record in enumerate(report):
 for j,item in enumerate([record['front'],record['back']]+record['discs']):
  im=Image.open(item['path']).convert('RGBA');im.thumbnail((310,330));x=j*330+(330-im.width)//2;y=i*370+26;canvas.paste(im,(x,y),im);draw.text((j*330+12,i*370+8),record['title']+' '+(['front','back','vinyl','CD'][j]),fill='#111111')
canvas.save(HERE/'final-contact.jpg',quality=90)
print('Report saved:',len(report),'albums,',len(qa),'validated discs')
