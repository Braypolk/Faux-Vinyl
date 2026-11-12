"""Exclusive cleanup-b batch. All image mutations are PhotoCraft commands."""
import json, math, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CLI = '/Applications/PhotoCraft.app/Contents/MacOS/photocraft-cli'
ROWS = [14,19,24,26,27,29,30,32,35,36,37,38,39,41,42]
APPROVED = json.loads((HERE.parent/'approved-new.json').read_text())
PROMPTS = json.loads((HERE/'prompts.json').read_text())
# Individually measured native-pixel outer ellipse x,y,w,h and physical spindle.
GEOMETRY = {
14: ([5,9,587,582], [298,300]),
19: ([7,12,584,577], [298,300]),
24: ([3,5,594,586], [300,298]),
26: ([28,22,553,554], [305,299]),
27: ([14,14,578,574], [305,299]),
29: ([162,165,677,677], [500,500]),
30: ([0,1,1999,1998], [1006,1035]),
32: ([33,187,636,636], [350,504]),
35: ([5,5,586,589], [298,298]),
36: ([19,25,1210,1210], [623,632]),
37: ([24,28,1204,1204], [626,628]),
38: ([0,0,600,600], [298,297]),
39: ([5,5,580,587], [295,298]),
41: ([7,12,578,577], [295,300]),
42: ([743,387,938,938], [1208,849]),
}
LOG = []
def run(src, dest, commands):
    args = [CLI,'run',str(src)]
    for command, params in commands:
        args += ['--cmd',command,'--params',json.dumps(params)]
    args += ['--out',str(dest),'--metadata','none']
    result = subprocess.run(args,capture_output=True,text=True)
    LOG.append(dict(source=str(src),output=str(dest),commands=commands,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr))
    if result.returncode:
        (HERE/'photocraft-log.json').write_text(json.dumps(LOG,indent=2))
        raise RuntimeError(str(dest)+': '+result.stderr+result.stdout)

def ellipse(box, **extra):
    return dict(zip(['x','y','width','height'],box)) | {'ellipse':True} | extra

def normalize(i):
    row = APPROVED[i]
    source = HERE/f'{i}-generated.png' if i in (36,37) else Path(row['reference_path'])
    box, spindle = GEOMETRY[i]
    x,y,w,h = box
    # A circle-preserving projectivity maps the measured spindle to the
    # output's exact center while preserving a circular silhouette. This
    # corrects the small physical-center/ellipse-center offset from perspective.
    v = np.array([2*(spindle[0]-x)/w-1, 2*(spindle[1]-y)/h-1])
    gamma = 1/math.sqrt(1-float(v@v))
    norm2 = float(v@v)
    linear = np.eye(2)+(gamma-1)*np.outer(v,v)/norm2 if norm2 else np.eye(2)
    quad=[]
    for p in [(-1,-1),(1,-1),(1,1),(-1,1)]:
        p=np.array(p)
        q=(linear@p-gamma*v)/(gamma*(1-float(v@p)))
        quad.append(((q+1)*320).tolist())
    hole = 16 if row['kind']=='vinyl' else 80
    commands = [
        ('layer.new.layerFromBackground',{'ifPresent':True}),
        ('image.crop',dict(zip(['x','y','width','height'],box))|{'targetWidth':640,'targetHeight':640,'resample':'lanczos'}),
        ('edit.transform',{'rect':[0,0,640,640],'quad':quad,'interpolation':'bicubic'}),
        ('select.rect',ellipse([0,0,640,640])),
        ('select.rect',ellipse([320-hole//2,320-hole//2,hole,hole],mode='subtract')),
        ('layer.layerMask.revealSelection',{}),
        ('select.deselect',{}),
        ('image.canvasSize',{'width':648,'height':648,'anchor':'center','extensionColor':'transparent'}),
    ]
    dest=HERE/(row['image_id']+'-final.webp')
    if i in (36,37):
        base=HERE/f'{i}-reconstructed-base.png'
        run(source,base,commands)
        # Preserve only the original printed label. The generated black label
        # border forms a seamless backing without a discolored photographic
        # ring. Feathering touches only the outside black label boundary.
        patchbox, size = (([212,135,152,152],220) if i==36 else ([194,196,204,204],218))
        labelmask = [214,141,146,144] if i==36 else [194,198,201,201]
        patch=HERE/f'{i}-original-label-patch.png'
        patch_commands=[
            ('layer.new.layerFromBackground',{'ifPresent':True}),
            ('select.rect',ellipse(labelmask,feather=0.7)),
            ('layer.layerMask.revealSelection',{}),
            ('select.deselect',{}),
            ('image.crop',dict(zip(['x','y','width','height'],patchbox))|{'targetWidth':size,'targetHeight':size,'resample':'lanczos'}),
        ]
        run(row['reference_path'],patch,patch_commands)
        # Cut a centered 16px hole in the patch before compositing.
        perforated=HERE/f'{i}-original-label-perforated.png'
        run(patch,perforated,[
            ('layer.new.layerFromBackground',{'ifPresent':True}),
            ('select.rect',{'x':0,'y':0,'width':size,'height':size}),
            ('select.rect',ellipse([size//2-8,size//2-8,16,16],mode='subtract')),
            ('layer.layerMask.revealSelection',{}),
            ('select.deselect',{}),
        ])
        run(base,dest,[('file.placeEmbedded',{'path':str(perforated),'fit':False,'smartObject':False,'scale':100,'center':[324,324]})])
    else:
        run(source,dest,commands)
    notes = []
    if i in (36,37):
        notes.append('Unprinted groove field/rim reconstructed using built-in image_gen; original photographed printed center label composited back with PhotoCraft. Fine label detail remains limited by the native source resolution. A narrow reconstructed black border remains around the original label.')
    if i==36:
        notes.append('Photographer/room reflection removed through reconstruction; original label photo is retained intentionally.')
    if i==37:
        notes.append('Clipped source rim reconstructed; source printed sleeve arrows/text excluded.')
    if i==27:
        notes.append('Retains warm photographed amber tone and the approved unofficial side A; no claim of official pressing.')
    if i==30:
        notes.append('Preserved photographed grey marble and lighting; original spindle offset corrected geometrically.')
    if i==38:
        notes.append('Source circumference touches image bounds; a centered circular mask retains the full available printed face and red groove field.')
    if i==42:
        notes.append('Official clear-vinyl mockup retained. Native alpha edge had a slight rectangular trim; individually inset geometric mask removes that trim and surrounding shadow. White/clear appearance remains as rendered in source.')
    if i==29:
        notes.append('Official blue-vinyl render retained; original small spindle enlarged to physical vinyl scale.')
    if i in (14,19,24,35,39,41):
        notes.append('Original silver/clear hub ring retained outside the centered 80px CD aperture; scanner texture/surface marks remain.')
    return {
        'id':row['id'],'image_id':row['image_id'],'album_id':row['album_id'],'kind':row['kind'],
        'output':str(dest),'method':'reference-reconstruction' if i in (36,37) else 'photocraft-cutout',
        'processing':f'PhotoCraft: individually measured native outer ellipse {box}, spindle {spindle}; crop and Lanczos resample to 640px; circle-preserving projective spindle alignment; circular alpha mask and centered {hole}px hole; centered 648px canvas with 4px transparent margin; lossless RGBA WebP.' + (' Original label patch composited over reconstructed groove field.' if i in (36,37) else ' Original artwork pixels retained.'),
        'prompt':PROMPTS[str(i)] if i in (36,37) else '',
        'source_reference':row['reference_path'],'notes':' '.join(notes),
        'source_row_index':i,'outer_ellipse':box,'source_spindle':spindle,
    }

if __name__=='__main__':
    records=[]
    for i in ROWS:
        records.append(normalize(i))
        print(i, APPROVED[i]['album_id'], 'prepared', flush=True)
    (HERE/'report.json').write_text(json.dumps(records,indent=2)+'\n')
    (HERE/'photocraft-log.json').write_text(json.dumps(LOG,indent=2)+'\n')
