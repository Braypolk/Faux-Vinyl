"""PhotoCraft-only image preparation; Pillow/NumPy inspect and validate only."""
import json,math,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
OUT=Path(__file__).resolve().parent
CLI='/Applications/PhotoCraft.app/Contents/MacOS/photocraft-cli'
G={
 'harry-vinyl':('harry-vinyl.jpg',[0,4,597,594],[300.2,306.7],16),
 'olivia-vinyl':('olivia-vinyl.jpg',[2,3,592,591],[298,301],16),
 'harry-cd':('harry-discogs-cd-uri.jpg',[10,10,581,581],[300,299],80),
 'olivia-cd':('olivia-exclusive-cd-product-0.png',[998,1365,333,332],[1164,1531.5],80),
}
def run(src,steps,dst):
 args=[CLI,'run',str(src)]
 for cmd,params in steps:args+=['--cmd',cmd,'--params',json.dumps(params)]
 args+=['--out',str(dst),'--metadata','none']
 r=subprocess.run(args,capture_output=True,text=True);(OUT/(dst.stem+'-commands.json')).write_text(json.dumps(steps,indent=2));(OUT/(dst.stem+'-photocraft.log')).write_text(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
def prepare(name):
 f,box,sp,hole=G[name];x,y,w,h=box
 v=np.array([2*(sp[0]-x)/w-1,2*(sp[1]-y)/h-1]);gamma=1/math.sqrt(1-float(v@v));norm=float(v@v);A=np.eye(2)+(gamma-1)*np.outer(v,v)/norm if norm else np.eye(2);quad=[]
 for p in [(-1,-1),(1,-1),(1,1),(-1,1)]:
  p=np.array(p);q=(A@p-gamma*v)/(gamma*(1-float(v@p)));quad.append(((q+1)*320).tolist())
 steps=[('layer.new.layerFromBackground',{'ifPresent':True}),('image.crop',{'x':x,'y':y,'width':w,'height':h,'targetWidth':640,'targetHeight':640,'resample':'lanczos'}),('edit.transform',{'rect':[0,0,640,640],'quad':quad,'interpolation':'bicubic'}),('select.rect',{'x':0,'y':0,'width':640,'height':640,'ellipse':True}),('select.rect',{'x':320-hole/2,'y':320-hole/2,'width':hole,'height':hole,'ellipse':True,'mode':'subtract'}),('layer.layerMask.revealSelection',{}),('select.deselect',{}),('image.canvasSize',{'width':648,'height':648,'anchor':'center','extensionColor':'transparent'})]
 if name=='olivia-cd':
  steps=[('tools.setColors',{'background':'#252d1f'}),('layer.new.backgroundFromLayer',{})]+steps
 run(OUT/f,steps,OUT/(name+'-final.webp'))
for name in G:prepare(name)
validation=[]
for name in G:
 im=Image.open(OUT/(name+'-final.webp')).convert('RGBA');a=np.array(im)[:,:,3];yy,xx=np.indices((648,648));r=np.sqrt((xx-323.5)**2+(yy-323.5)**2);hole=G[name][3];ann=(r>hole/2+3)&(r<317);v={'name':name,'size':im.size,'mode':im.mode,'alpha_bbox':im.getchannel('A').getbbox(),'hole_alpha_max':int(a[r<hole/2-2].max()),'annulus_alpha_min':int(a[ann].min()),'exterior_alpha_max':int(a[r>321].max())};validation.append(v)
(OUT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n');print(json.dumps(validation,indent=2))
# QA-only contact sheet; final assets above are modified solely by PhotoCraft.
qa=Image.new('RGB',(2*700,2*720),'#cccccc');d=ImageDraw.Draw(qa)
for i,name in enumerate(G):
 x=(i%2)*700;y=(i//2)*720;im=Image.open(OUT/(name+'-final.webp')).convert('RGBA');qa.paste(im,(x+20,y+40),im);d.text((x+20,y+10),name,fill='black')
qa.save(OUT/'contact-qa.jpg',quality=92)
