"""Batch A only. Pillow reads/QA; all asset mutations use PhotoCraft."""
import json, math, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent
CLI = '/Applications/PhotoCraft.app/Contents/MacOS/photocraft-cli'
ROWS = json.loads((OUT/'assigned.json').read_text())
# Individually measured ellipse extrema and spindle coordinates on a 600x600
# inspection grid. Width and height are scaled independently to source pixels.
G = {
 0: ([15,12,570,575],[302.5,293.5]),
 2: ([8,1,587,595],[301,298.5]),
 3: ([0,1,599,588],[293.5,281.5]),
 4: ([57,61,522,523],[316.2,321.3]),
 5: ([37,70,494,506],[281.8,319]),
 8: ([8,6,585,587],[299.5,298.5]),
 10: ([14,11,571,575],[300.7,295.8]),
 11: ([6,17,585,576],[297,302]),
 15: ([24,49,539,530],[294.5,311.5]),
 17: ([8,9,582,580],[298,296]),
 20: ([43,68,509,509],[291.5,318.5]),
 21: ([13,139,323,323],[174.5,300.5]),
 23: ([270.54,342.54,287,235.4],[413,442.5]),
 25: ([31,144,256,332],[159,310.5]),
}
GENERATED = {0:([20.19,30.36,1205.11,1198.98],[622.29,630.13],173.171),3:([17.33,27.71,1212.36,1202.17],[621.6,627.25],-85.332),15:([25.65,32.34,1196.24,1189.63],[623.56,630.41],-85.106)}
LABELS = {0:([209,198,188,188],[302.5,291.5],212),3:([193,188,200,195],[293,285],214),15:([1039,1121,895,892],[1484,1570],214)}

def run(src, steps, dst):
    args=[CLI,'run',str(src)]
    for cmd,params in steps: args += ['--cmd',cmd,'--params',json.dumps(params)]
    args += ['--out',str(dst),'--metadata','none']
    p=subprocess.run(args,capture_output=True,text=True)
    (OUT/(dst.stem+'-commands.json')).write_text(json.dumps(steps,indent=2))
    (OUT/(dst.stem+'-photocraft.log')).write_text(p.stdout+p.stderr)
    if p.returncode: raise RuntimeError(f'{dst}: {p.stderr} {p.stdout}')

def quad_for(ellipse,spindle,source_size,diameter=640,theta=0):
    x,y,w,h=ellipse; cx=x+w/2;cy=y+h/2
    t=math.radians(theta); co=math.cos(t);si=math.sin(t)
    # Symmetric conic square-root: deproject rotated ellipse without rotating art.
    R=np.array([[co,-si],[si,co]])
    E=R@np.diag([w/2,h/2])@R.T
    inv=np.linalg.inv(E)
    p=inv@(np.array(spindle)-[cx,cy]); s=float(p@p)
    gamma=1/math.sqrt(1-s)
    A=np.eye(2)+(gamma-1)*np.outer(p,p)/s if s>1e-12 else np.eye(2)
    B=np.eye(3);B[:2,:2]=A;B[:2,2]=-gamma*p;B[2,:2]=-gamma*p;B[2,2]=gamma
    N=np.eye(3);N[:2,:2]=inv;N[:2,2]=-inv@np.array([cx,cy])
    D=np.array([[diameter/2,0,324],[0,diameter/2,324],[0,0,1]])
    H=D@B@N
    corners=np.array([[0,0,1],[source_size[0],0,1],[source_size[0],source_size[1],1],[0,source_size[1],1]]).T
    q=H@corners;q=(q[:2]/q[2]).T
    return q.tolist()

def prepare(src,ellipse,spindle,dst,diameter=640,theta=0,matte=None):
    with Image.open(src) as im: size=im.size
    q=quad_for(ellipse,spindle,size,diameter,theta)
    m=(648-diameter)//2
    steps=[]
    if matte:
        steps += [('tools.setColors',{'background':matte}),('layer.new.backgroundFromLayer',{})]
    steps += [('layer.new.layerFromBackground',{'ifPresent':True}),
       ('edit.transform',{'rect':[0,0,*size],'quad':q,'interpolation':'bicubic'}),
       ('image.crop',{'x':0,'y':0,'width':648,'height':648}),
       ('select.rect',{'x':m,'y':m,'width':diameter,'height':diameter,'ellipse':True}),
       ('select.rect',{'x':316,'y':316,'width':16,'height':16,'ellipse':True,'mode':'subtract'}),
       ('layer.layerMask.revealSelection',{}),('select.deselect',{})]
    run(src,steps,dst)

def main():
    prompts=json.loads((OUT/'prompts.json').read_text()); reports=[];geom=[]
    for c in ROWS:
        idx=c['index'];src=Path(c['reference_path']);dst=OUT/(c['image_id']+'-final.webp')
        box,sp=G[idx]
        with Image.open(src) as im: w,h=im.size
        ellipse=np.array(box)*[w/600,h/600,w/600,h/600];spindle=np.array(sp)*[w/600,h/600]
        if idx in GENERATED:
            gen=OUT/f'row-{idx}-surface.png';b,s,t=GENERATED[idx]
            plate=OUT/f'row-{idx}-surface-prepared.png';prepare(gen,b,s,plate,theta=t,matte='#0099c5' if idx==0 else '#101010')
            b,s,d=LABELS[idx];label=OUT/f'row-{idx}-original-label.png';prepare(src,b,s,label,d)
            run(plate,[('file.placeEmbedded',{'path':str(label),'fit':False,'scale':100,'center':[324,324],'smartObject':False}),('layer.mergeVisible',{}),('select.rect',{'x':316,'y':316,'width':16,'height':16,'ellipse':True}),('edit.clear',{}),('select.deselect',{})],dst)
            method='reference-reconstruction'
            processing='Built-in image_gen reflection-free vinyl surface; PhotoCraft matched-color backing removes incidental near-opaque generated alpha inside the disc, followed by original printed label cutout/composite at measured physical proportion. PhotoCraft projective ellipse/spindle rectification, circular alpha and 16px centered spindle hole. 648px lossless RGBA WebP with 640px disc and 4px margin.'
            prompt=prompts[str(idx)]['initial']+'\n\nFOLLOW-UP SURFACE PLATE EDIT:\n'+prompts[str(idx)]['surface']
            notes='Grooved vinyl surface reconstructed to remove camera/person/hand reflections. All printed label pixels are from the approved original, including its source resolution/lighting and small surface marks.'
        else:
            prepare(src,ellipse,spindle,dst,theta=15.867 if idx==23 else 0)
            method='photocraft-cutout';prompt=None
            processing='PhotoCraft individually measured ellipse and spindle projective rectification; original source pixels retained, circular alpha mask, centered 16px spindle hole; 648px lossless RGBA WebP, 640px disc and 4px transparent margin.'
            notes='Source resolution, surface texture and ordinary non-person lighting reflections retained.'
            if idx==21: notes+=' Selected the fully visible foreground left side-A splatter record; promotional rendering.'
            if idx==23: notes+=' Selected the fully unobscured foreground right record; corrected its oblique ellipse.'
            if idx==25: notes+=' Selected left record 1-B; official promotional photo.'
            if idx==2: notes+=' Clear vinyl retains the photographed pale appearance; only outside and spindle are transparent.'
            if idx==10: notes+=' Milky-clear vinyl retains its photographed light-gray appearance.'
        reports.append({k:c[k] for k in ['id','image_id','album_id','kind']}|{'output':str(dst),'method':method,'processing':processing,'prompt':prompt,'source_reference':str(src),'notes':notes})
        geom.append({'index':idx,'image_id':c['image_id'],'outer_ellipse_normalized_600':box,'spindle_normalized_600':sp,'output_diameter':640,'hole_diameter':16})
        print(idx,c['album_id'],method,flush=True)
    (OUT/'report.json').write_text(json.dumps(reports,indent=2)+'\n')
    (OUT/'geometry.json').write_text(json.dumps(geom,indent=2)+'\n')
    qa(reports)

def qa(reports):
    stats=[];sheet=Image.new('RGB',(4*340,4*365),'#dedede');draw=ImageDraw.Draw(sheet)
    for n,c in enumerate(reports):
        im=Image.open(c['output']);a=np.asarray(im.getchannel('A'))
        assert im.mode=='RGBA' and im.size==(648,648)
        assert not a[:4,:].any() and not a[-4:,:].any() and not a[:,:4].any() and not a[:,-4:].any()
        assert a[324,324]==0
        y,x=np.where(a>127);bbox=[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
        assert bbox==[4,4,644,644],(c['image_id'],bbox)
        yy,xx=np.mgrid[:648,:648];rad=np.sqrt((xx-323.5)**2+(yy-323.5)**2)
        assert np.all(a[rad<7]==0)
        assert np.all(a[(rad>10)&(rad<318)]==255),c['image_id']
        stats.append({'image_id':c['image_id'],'size':list(im.size),'mode':im.mode,'alpha_bbox':bbox,'hole_center':[324,324],'spindle_clear':True,'complete_opaque_disc_annulus':True})
        # QA contact sheet only; never used as an output asset.
        bg=Image.new('RGBA',(648,648));bd=ImageDraw.Draw(bg)
        for j in range(0,648,24):
            for i in range(0,648,24):bd.rectangle((i,j,i+23,j+23),fill=('#999' if (i//24+j//24)%2 else '#ccc'))
        bg.alpha_composite(im);bg=bg.convert('RGB').resize((328,328))
        px=n%4*340;py=n//4*365;sheet.paste(bg,(px,py));draw.text((px+2,py+331),c['album_id'],fill='black');draw.text((px+2,py+346),c['method'],fill='black')
    sheet.save(OUT/'finals-contact.jpg')
    (OUT/'validation.json').write_text(json.dumps(stats,indent=2)+'\n')

if __name__=='__main__':main()
