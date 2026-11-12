"""PhotoCraft-only asset edits; Pillow/NumPy are used only for read/QA/math."""
from pathlib import Path
import json, math, subprocess, hashlib
import numpy as np
from PIL import Image, ImageDraw

OUT=Path(__file__).resolve().parent
CLI='/Applications/PhotoCraft.app/Contents/MacOS/photocraft-cli'

def run(src, steps, dst, quality=None):
    args=[CLI,'run',str(src)]
    for cmd,params in steps: args+=['--cmd',cmd,'--params',json.dumps(params)]
    args+=['--out',str(dst),'--metadata','none']
    if quality: args+=['--quality',str(quality)]
    p=subprocess.run(args,capture_output=True,text=True)
    (OUT/(dst.stem+'-commands.json')).write_text(json.dumps(steps,indent=2)+'\n')
    (OUT/(dst.stem+'-photocraft.log')).write_text(p.stdout+p.stderr)
    if p.returncode: raise RuntimeError(str(dst)+'\n'+p.stdout+p.stderr)

def quad(ellipse,spindle,size,diameter=640,theta=0):
    x,y,w,h=ellipse; center=np.array([x+w/2,y+h/2]);t=math.radians(theta)
    R=np.array([[math.cos(t),-math.sin(t)],[math.sin(t),math.cos(t)]])
    inv=np.linalg.inv(R@np.diag([w/2,h/2])@R.T)
    p=inv@(np.array(spindle)-center);s=float(p@p);g=1/math.sqrt(1-s)
    A=np.eye(2)+(g-1)*np.outer(p,p)/s if s>1e-12 else np.eye(2)
    B=np.eye(3);B[:2,:2]=A;B[:2,2]=-g*p;B[2,:2]=-g*p;B[2,2]=g
    N=np.eye(3);N[:2,:2]=inv;N[:2,2]=-inv@center
    D=np.array([[diameter/2,0,324],[0,diameter/2,324],[0,0,1]])
    H=D@B@N
    corners=np.array([[0,0,1],[size[0],0,1],[size[0],size[1],1],[0,size[1],1]]).T
    q=H@corners
    return (q[:2]/q[2]).T.tolist()

def prepare(src,ellipse,spindle,dst,diameter=640,hole=16,theta=0,matte=None):
    size=Image.open(src).size;m=(648-diameter)//2
    steps=[]
    if matte: steps += [('tools.setColors',{'background':matte}),('layer.new.backgroundFromLayer',{})]
    steps += [('layer.new.layerFromBackground',{'ifPresent':True}),
       ('edit.transform',{'rect':[0,0,*size],'quad':quad(ellipse,spindle,size,diameter,theta),'interpolation':'bicubic'}),
       ('image.crop',{'x':0,'y':0,'width':648,'height':648}),
       ('select.rect',{'x':m,'y':m,'width':diameter,'height':diameter,'ellipse':True}),
       ('select.rect',{'x':324-hole/2,'y':324-hole/2,'width':hole,'height':hole,'ellipse':True,'mode':'subtract'}),
       ('layer.layerMask.revealSelection',{}),('select.deselect',{})]
    run(src,steps,dst)

def covers():
    for name in ['1989','folklore','thank-u-next']:
        src=OUT/(name+('-front-caa-source.jpg' if name=='thank-u-next' else '-front-source.jpg'))
        run(src,[],OUT/(name+'-front-final.webp'),90)
    run(OUT/'1989-back-source.jpg',[],OUT/'1989-back-final.webp',90)
    run(OUT/'thank-u-next-back-source.jpg',[('image.crop',{'x':37,'y':1,'width':675,'height':592})],OUT/'thank-u-next-back-final.webp',90)
    # Map actual printed sleeve corners to a square, removing the photographed tabletop.
    source=np.array([[40,23],[1165,19],[1173,1152],[46,1140]],float)
    target=np.array([[0,0],[1200,0],[1200,1200],[0,1200]],float)
    rows=[]; vals=[]
    for (x,y),(u,v) in zip(source,target):
        rows.extend([[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]]);vals.extend([u,v])
    H=np.r_[np.linalg.solve(np.array(rows),np.array(vals)),1].reshape(3,3)
    c=np.array([[0,0,1],[1200,0,1],[1200,1181,1],[0,1181,1]]).T;q=H@c;q=(q[:2]/q[2]).T.tolist()
    run(OUT/'folklore-back-source.jpg',[
      ('layer.new.layerFromBackground',{'ifPresent':True}),
      ('edit.transform',{'rect':[0,0,1200,1181],'quad':q,'interpolation':'bicubic'}),
      ('image.crop',{'x':0,'y':0,'width':1200,'height':1200})],OUT/'folklore-back-final.webp',90)

def cds():
    for name,e,s in [
      ('1989',[1,1,596,601],[298,300]),
      ('folklore',[5,9,787,781],[398,400]),
      ('thank-u-next',[2,2,589,590],[296,298])]:
        prepare(OUT/(name+'-cd-source.jpg'),e,s,OUT/(name+'-cd-final.webp'),hole=80)

def vinyls():
    prepare(OUT/'black-vinyl-surface-generated.png',[15,18,1222,1226],[623.17,633.39],OUT/'black-vinyl-surface-prepared.png',matte='#101010')
    # All label pixels are photographed originals, never generated lettering.
    labels=[('1989','1989-vinyl-b-source.jpg',[14,14,572,572],[300,300],0),
            ('thank-u-next','thank-u-next-vinyl-uo-source.jpg',[173,564,686,548],[516,826],8),
            ('folklore','folklore-vinyl-source.jpg',[393,409,386,384],[587,601],0)]
    # Beige generated plate geometry is recorded after inspecting the generated original.
    geom=json.loads((OUT/'beige-geometry.json').read_text())
    prepare(OUT/'beige-vinyl-surface-generated.png',geom['ellipse'],geom['spindle'],OUT/'beige-vinyl-surface-prepared.png',matte='#9f8e78')
    for name,source,e,s,t in labels:
        label=OUT/(name+'-original-label.png')
        prepare(OUT/source,e,s,label,diameter=212,theta=t)
        plate=OUT/('beige-vinyl-surface-prepared.png' if name=='folklore' else 'black-vinyl-surface-prepared.png')
        run(plate,[('file.placeEmbedded',{'path':str(label),'fit':False,'scale':100,'center':[324,324],'smartObject':False}),
           ('layer.mergeVisible',{}),('select.rect',{'x':316,'y':316,'width':16,'height':16,'ellipse':True}),
           ('edit.clear',{}),('select.deselect',{})],OUT/(name+'-vinyl-final.webp'))

def qa():
    stats=[]; sheet=Image.new('RGB',(4*332,3*360),'#dedede');draw=ImageDraw.Draw(sheet)
    for n,src in enumerate(sorted(OUT.glob('*-final.webp'))):
        im=Image.open(src);a=np.array(im.convert('RGBA'))[:,:,3];disc='-vinyl-' in src.name or '-cd-' in src.name
        item={'file':str(src),'mode':im.mode,'size':list(im.size),'bytes':src.stat().st_size}
        if disc:
            assert im.size==(648,648) and im.mode=='RGBA'
            y,x=np.where(a>127);bbox=[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
            assert bbox==[4,4,644,644],(src,bbox)
            hole=40 if '-cd-' in src.name else 8
            yy,xx=np.mgrid[:648,:648];r=np.sqrt((xx-323.5)**2+(yy-323.5)**2)
            assert np.all(a[r<hole-1]==0),src
            assert np.all(a[(r>hole+2)&(r<318)]==255),src
            assert not a[:4].any() and not a[-4:].any() and not a[:,:4].any() and not a[:,-4:].any(),src
            item.update({'alpha_bbox':bbox,'hole_diameter':hole*2,'center':[324,324],'opaque_annulus':True})
        assert max(im.size)<=1200
        stats.append(item)
        bg=Image.new('RGBA',im.size,'#bbb');bg.alpha_composite(im.convert('RGBA'));thumb=bg.convert('RGB');thumb.thumbnail((324,324))
        x=n%4*332;y=n//4*360;sheet.paste(thumb,(x,y));draw.text((x+2,y+326),src.name,fill='black')
    sheet.save(OUT/'finals-contact.jpg');(OUT/'validation.json').write_text(json.dumps(stats,indent=2)+'\n')
    originals={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*source.jpg')}
    (OUT/'source-sha256.json').write_text(json.dumps(originals,indent=2)+'\n')

if __name__=='__main__':
    import sys
    mode=sys.argv[1] if len(sys.argv)>1 else 'all'
    if mode in ['all','covers']: covers()
    if mode in ['all','cds']: cds()
    if mode in ['all','vinyls']: vinyls()
    if mode in ['all','qa']: qa()
