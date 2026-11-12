import json,math,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
OUT=Path(__file__).resolve().parent
CLI='/Applications/PhotoCraft.app/Contents/MacOS/photocraft-cli'
def run(src,steps,dst,quality=None):
 args=[CLI,'run',str(src)]
 for c,p in steps:args+=['--cmd',c,'--params',json.dumps(p)]
 args+=['--out',str(dst),'--metadata','none']
 if quality:args+=['--quality',str(quality)]
 r=subprocess.run(args,capture_output=True,text=True);(OUT/(dst.stem+'-commands.json')).write_text(json.dumps(steps,indent=2));(OUT/(dst.stem+'-photocraft.log')).write_text(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
def quad_for(ellipse,spindle,size):
 x,y,w,h=ellipse;cx=x+w/2;cy=y+h/2
 inv=np.diag([2/w,2/h]);p=inv@(np.array(spindle)-[cx,cy]);s=float(p@p);gamma=1/math.sqrt(1-s)
 A=np.eye(2)+(gamma-1)*np.outer(p,p)/s if s>1e-12 else np.eye(2)
 B=np.eye(3);B[:2,:2]=A;B[:2,2]=-gamma*p;B[2,:2]=-gamma*p;B[2,2]=gamma
 N=np.eye(3);N[:2,:2]=inv;N[:2,2]=-inv@np.array([cx,cy]);D=np.array([[320,0,324],[0,320,324],[0,0,1]]);H=D@B@N
 corners=np.array([[0,0,1],[size[0],0,1],[size[0],size[1],1],[0,size[1],1]]).T;q=H@corners;return (q[:2]/q[2]).T.tolist()
rows=[('slow-rush-vinyl-blue.jpg','slow-rush-vinyl.webp',[5,5,1270,1274],[638,642],16),('slow-rush-cd-2.jpg','slow-rush-cd.webp',[3,2,594,598],[300,302],80),('freefall-vinyl-cropped.png','freefall-vinyl.webp',[51.75,49.5,826.875,511.875],[464.625,253.125],16),('11859663-2.jpg','freefall-cd.webp',[0,0,587,592],[287.5,298],80)]
for source,final,e,s,hole in rows:
 src=OUT/source;size=Image.open(src).size;q=quad_for(e,s,size);m=324-hole/2
 steps=[('layer.new.layerFromBackground',{'ifPresent':True}),('edit.transform',{'rect':[0,0,*size],'quad':q,'interpolation':'bicubic'}),('image.crop',{'x':0,'y':0,'width':648,'height':648}),('select.rect',{'x':4,'y':4,'width':640,'height':640,'ellipse':True}),('select.rect',{'x':m,'y':m,'width':hole,'height':hole,'ellipse':True,'mode':'subtract'}),('layer.layerMask.revealSelection',{}),('select.deselect',{})]
 run(src,steps,OUT/final);print(final,flush=True)
for source,final in [('slow-rush-front.jpg','slow-rush-front.webp'),('slow-rush-clean-back.jpg','slow-rush-back.webp'),('freefall-front.jpg','freefall-front.webp'),('11825457-1.jpg','freefall-back.webp')]:
 run(OUT/source,[],OUT/final,90);print(final,flush=True)
(OUT/'geometry.json').write_text(json.dumps(rows,indent=2))
