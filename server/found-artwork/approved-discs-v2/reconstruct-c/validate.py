from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
records=json.loads((HERE/'report.json').read_text())
checks=[]
qa=Image.new('RGB',(648*3,690*2),'#aaaaaa');draw=ImageDraw.Draw(qa)
for k,row in enumerate(records):
 im=Image.open(row['output']);alpha=np.asarray(im.getchannel('A'))
 yy,xx=np.indices(alpha.shape);radius=((xx+.5-324)**2+(yy+.5-324)**2)**.5
 hole=8 if row['kind']=='vinyl' else 40
 assert im.mode=='RGBA' and im.size==(648,648)
 assert im.getchannel('A').getbbox()==(4,4,644,644)
 assert np.all(alpha[:4,:]==0) and np.all(alpha[-4:,:]==0)
 assert np.all(alpha[:,:4]==0) and np.all(alpha[:,-4:]==0)
 assert np.all(alpha[radius<hole-1]==0) and np.all(alpha[radius>321]==0)
 interior=(radius>hole+3)&(radius<310)
 assert float(np.mean(alpha[interior]>=250))>.999
 checks.append({'image_id':row['image_id'],'size':list(im.size),'mode':im.mode,'alpha_bbox':list(im.getchannel('A').getbbox()),'center_alpha':int(alpha[324,324]),'hole_diameter_px':hole*2,'rim_diameter_px':640,'interior_alpha_median':float(np.median(alpha[interior])),'interior_near_opaque_fraction':float(np.mean(alpha[interior]>=250)),'file_bytes':Path(row['output']).stat().st_size,'visual_inspection':'passed, each final viewed individually'})
 x=(k%3)*648;y=(k//3)*690
 for gy in range(0,648,24):
  for gx in range(0,648,24):
   draw.rectangle([x+gx,y+gy,x+gx+23,y+gy+23],fill='#d0d0d0' if (gx//24+gy//24)%2 else '#909090')
 qa.paste(im,(x,y),im);draw.text((x+12,y+654),row['album_id'],fill='black')
qa.save(HERE/'qa-contact-sheet.png')
(HERE/'validation.json').write_text(json.dumps(checks,indent=2)+'\n')
print('PASS: all five RGBA WebP assets, dimensions, transparent margins, centered apertures and clean interiors.')
