"""PhotoCraft-only image mutations; Pillow/NumPy are read/QA only."""
import json,math,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parent
CLI='/Applications/PhotoCraft.app/Contents/MacOS/photocraft-cli'
def run(src,steps,dst):
 args=[CLI,'run',str(P/src)]
 for cmd,params in steps:args+=['--cmd',cmd,'--params',json.dumps(params)]
 args+=['--out',str(P/dst),'--metadata','none']
 r=subprocess.run(args,capture_output=True,text=True)
 (P/(dst+'-commands.json')).write_text(json.dumps(steps,indent=2));(P/(dst+'-photocraft.log')).write_text(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
def quad_for(e,sp,size):
 x,y,w,h=e;c=np.array([x+w/2,y+h/2]);inv=np.diag([2/w,2/h]);p=inv@(np.array(sp)-c);s=float(p@p);g=1/math.sqrt(1-s)
 a=np.eye(2)+(g-1)*np.outer(p,p)/s if s>1e-12 else np.eye(2)
 b=np.eye(3);b[:2,:2]=a;b[:2,2]=-g*p;b[2,:2]=-g*p;b[2,2]=g
 n=np.eye(3);n[:2,:2]=inv;n[:2,2]=-inv@c
 d=np.array([[320,0,324],[0,320,324],[0,0,1]])
 h=d@b@n;corn=np.array([[0,0,1],[size[0],0,1],[size[0],size[1],1],[0,size[1],1]]).T;q=h@corn
 return (q[:2]/q[2]).T.tolist()
D=[
 ('divide-vinyl.webp','the-great-divide-american-rust-vinyl-1.png',[35,35,1430,1430],[750,750],16,'#d0aa51'),
 ('divide-cd.webp','divide-discogs-photo-6-uri.jpg',[20,22,570,566],[307,298],80,None),
 ('stick-vinyl.webp','stick-discogs-27318180-2.jpg',[14,16,571,566],[300,300],16,None),
 ('stick-cd.webp','stick-discogs-24957121-2.jpg',[5,3,590,594],[299,301],80,None),
]
for dst,src,e,sp,hole,matte in D:
 size=Image.open(P/src).size;steps=[]
 if matte:steps+=[('tools.setColors',{'background':matte}),('layer.new.backgroundFromLayer',{})]
 steps+=[('layer.new.layerFromBackground',{'ifPresent':True}),('edit.transform',{'rect':[0,0,*size],'quad':quad_for(e,sp,size),'interpolation':'bicubic'}),('image.crop',{'x':0,'y':0,'width':648,'height':648}),('select.rect',{'x':4,'y':4,'width':640,'height':640,'ellipse':True}),('select.rect',{'x':324-hole/2,'y':324-hole/2,'width':hole,'height':hole,'ellipse':True,'mode':'subtract'}),('layer.layerMask.revealSelection',{}),('select.deselect',{})]
 run(src,steps,dst);print(dst,flush=True)
for prefix in ['divide','stick']:run(prefix+'-front-ref.jpg',[],prefix+'-front.webp')
run('stick-season-vinyl-standard-black-6.png',[('image.crop',{'x':171,'y':174,'width':658,'height':652})],'stick-back.webp')
# Correct only the light camera skew on the physical CD back photograph.
src='divide-discogs-photo-2-uri.jpg';im=Image.open(P/src);w,h=im.size
# Four measured print corners. Homography projects those to a flat 600x550 rectangle.
a=np.array([[7,6],[595,5],[599,543],[0,545]],float);b=np.array([[0,0],[600,0],[600,550],[0,550]],float)
A=[];B=[]
for (x,y),(u,v) in zip(a,b):A += [[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]];B += [u,v]
hh=np.r_[np.linalg.solve(A,B),1].reshape(3,3);cc=np.array([[0,0,1],[w,0,1],[w,h,1],[0,h,1]]).T;q=hh@cc;q=(q[:2]/q[2]).T.tolist()
run(src,[('layer.new.layerFromBackground',{'ifPresent':True}),('edit.transform',{'rect':[0,0,w,h],'quad':q,'interpolation':'bicubic'}),('image.crop',{'x':0,'y':0,'width':600,'height':550})],'divide-back.webp')
qa=[]
for dst,src,e,sp,hole,matte in D:
 im=Image.open(P/dst);alpha=np.array(im.getchannel('A'));yy,xx=np.mgrid[:648,:648];rad=np.sqrt((xx-323.5)**2+(yy-323.5)**2);ys,xs=np.where(alpha>127);bbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
 assert im.mode=='RGBA' and im.size==(648,648)
 assert bbox==[4,4,644,644],(dst,bbox)
 assert not alpha[:4].any() and not alpha[-4:].any() and not alpha[:,:4].any() and not alpha[:,-4:].any()
 assert np.all(alpha[(rad>hole/2+2)&(rad<318)]==255),dst
 assert np.all(alpha[rad<hole/2-1]==0),dst
 qa.append({'path':str(P/dst),'mode':im.mode,'size':list(im.size),'alpha_bbox':bbox,'hole_diameter':hole,'opaque_annulus':True,'source_outer_ellipse':e,'source_spindle':sp})
(P/'validation.json').write_text(json.dumps(qa,indent=2))
