"""Image mutation is exclusively PhotoCraft; Pillow/NumPy are for read-only QA."""
import json,math,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent
CLI='/Applications/PhotoCraft.app/Contents/MacOS/photocraft-cli'
LOG=[]
def run(src,dest,commands):
 args=[CLI,'run',str(HERE/src)]
 for cmd,params in commands: args+=['--cmd',cmd,'--params',json.dumps(params)]
 args+=['--out',str(HERE/dest),'--metadata','none']
 p=subprocess.run(args,capture_output=True,text=True)
 LOG.append(dict(source=src,output=dest,commands=commands,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
 (HERE/(Path(sys.argv[0]).stem+'-photocraft-log.json')).write_text(json.dumps(LOG,indent=2))
 if p.returncode:raise RuntimeError(p.stderr+p.stdout)
def normalize(src,dest,box,spindle,hole):
 x,y,w,h=box
 v=np.array([2*(spindle[0]-x)/w-1,2*(spindle[1]-y)/h-1]);g=1/math.sqrt(1-float(v@v)); n=float(v@v)
 a=np.eye(2)+(g-1)*np.outer(v,v)/n if n else np.eye(2)
 quad=[]
 for p in [(-1,-1),(1,-1),(1,1),(-1,1)]:
  p=np.array(p);q=(a@p-g*v)/(g*(1-float(v@p)));quad.append(((q+1)*320).tolist())
 run(src,dest,[('layer.new.layerFromBackground',{'ifPresent':True}),('image.crop',dict(zip(['x','y','width','height'],box))|{'targetWidth':640,'targetHeight':640,'resample':'lanczos'}),('edit.transform',{'rect':[0,0,640,640],'quad':quad,'interpolation':'bicubic'}),('select.rect',{'x':0,'y':0,'width':640,'height':640,'ellipse':True}),('select.rect',{'x':320-hole//2,'y':320-hole//2,'width':hole,'height':hole,'ellipse':True,'mode':'subtract'}),('layer.layerMask.revealSelection',{}),('select.deselect',{}),('image.canvasSize',{'width':648,'height':648,'anchor':'center','extensionColor':'transparent'})])
if __name__=='__main__':
 normalize('anti-discogs-3.jpg','anti-vinyl.webp',[5,6,590,590],[300,299],16)
 normalize('anti-cd-24278005176.jpg','anti-cd.webp',[0,1,1187,1198],[592,602],80)
 normalize('beyonce-cd-37516036127.jpg','beyonce-cd.webp',[1,7,1180,1183],[587,599],80)
 for src,dest in [('anti-discogs-1.jpg','anti-front.webp'),('anti-discogs-2.jpg','anti-back.webp'),('beyonce-discogs-0.jpg','beyonce-front.webp'),('beyonce-discogs-3.jpg','beyonce-back.webp')]:
  run(src,dest,[])
 print('Prepared three direct disc cutouts and four sleeve scans.')
