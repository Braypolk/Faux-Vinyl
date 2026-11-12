from pathlib import Path
import json, subprocess
from PIL import Image
import numpy as np

HERE=Path(__file__).resolve().parent
CLI='/Applications/PhotoCraft.app/Contents/MacOS/photocraft-cli'
rows=json.loads((HERE.parent/'approved-new.json').read_text())
# Ellipses measured from generated alpha, centered on the photographed/reconstructed hub.
# Slight inset removes generated fringe speckles and leaves an uninterrupted rim.
geometry={31:([20,36,1204,1204],[622,638],52),33:([108,29,1096,1106],[656,582],200),34:([25,16,1210,1220],[630,626],48),40:([14,20,1220,1214],[624,627],44),43:([42,52,1162,1162],[623,633],196)}
records=[]
for index,(box,center,patchdiam) in geometry.items():
 row=rows[index]; src=HERE/f'{index}-generated.png'
 im=Image.open(src); ar=np.asarray(im)
 cx,cy=center
 # Sample the existing hub/label immediately outside its generated aperture.
 yy,xx=np.indices(ar.shape[:2]);rr=((xx-cx)**2+(yy-cy)**2)**.5
 samples=ar[(rr>patchdiam*.50)&(rr<patchdiam*.58)&(ar[:,:,3]>250),:3]
 color=[int(v) for v in np.median(samples,axis=0)]
 outer=dict(zip(['x','y','width','height'],box))
 commands=[('layer.new.layerFromBackground',{'ifPresent':True}),('layer.new.layer',{'name':'Smooth hub repair backing','position':'below'}),('select.rect',{'x':cx-patchdiam//2,'y':cy-patchdiam//2,'width':patchdiam,'height':patchdiam,'ellipse':True}),('edit.fill',{'contents':'color','color':'#'+''.join(f'{v:02x}' for v in color)}),('select.deselect',{}),('layer.selectAbove',{}),('layer.mergeDown',{}),('image.crop',outer|{'targetWidth':640,'targetHeight':640,'resample':'lanczos'}),('image.canvasSize',{'width':648,'height':648,'anchor':'center','extensionColor':'transparent'})]
 if index==43:
  commands += [('select.rect',{'x':4,'y':4,'width':640,'height':640,'ellipse':True}),('select.rect',{'x':5,'y':5,'width':638,'height':638,'ellipse':True,'mode':'subtract'}),('edit.fill',{'contents':'color','color':'#bcbcbc'}),('select.deselect',{})]
 commands += [('select.rect',{'x':4,'y':4,'width':640,'height':640,'ellipse':True})]
 hole=16 if row['kind']=='vinyl' else 80
 commands += [('select.rect',{'x':324-hole//2,'y':324-hole//2,'width':hole,'height':hole,'ellipse':True,'mode':'subtract'}),('layer.layerMask.revealSelection',{}),('select.deselect',{})]
 dst=HERE/(row['image_id']+'-final.webp')
 args=[CLI,'run',str(src)]
 for cmd,params in commands:args+=['--cmd',cmd,'--params',json.dumps(params)]
 args+=['--out',str(dst),'--quality','95']
 res=subprocess.run(args,capture_output=True,text=True)
 if res.returncode:raise RuntimeError(res.stdout+res.stderr)
 (HERE/f'{index}-photocraft-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 processing='Built-in image_gen reference reconstruction, followed by PhotoCraft smooth hub backing, centered measured crop/resample, 640px circular alpha rim, exact centered '+str(hole)+'px aperture, and transparent 4px canvas margin.'
 notes={31:'Fine label credits/track timings are not reliably recoverable from the perspective photograph and were not invented; label text is reconstructed. Orange-red label and blue side one retained.',33:'Smooth silver hub reconstructed from a tray-obscured center. First generation retained tray spokes and was rejected; second prompt corrects them. Tiny legal text is approximate.',34:'PVC seams/glare removed; eight printed pink head views preserved. Tiny circular legal text is approximate, not a verified transcription.',40:'Clear vinyl rendered with a neutral frosted/silver groove appearance. Sleeve logos removed. Tiny label legal text is approximate.',43:'Source CD is only about 240px across; family-photo detail, small emblem and fine credits are reconstructed approximations. Smooth hub replaces retaining spindle. Peripheral generated fringe was inset for a clean concentric rim.'}[index]
 prompt=(HERE/('33-prompt-v2.txt' if index==33 else f'{index}-prompt.txt')).read_text().rstrip()
 records.append({'id':row['id'],'image_id':row['image_id'],'album_id':row['album_id'],'kind':row['kind'],'output':str(dst),'method':'reference-reconstruction','processing':processing,'prompt':prompt,'source_reference':row['reference_path'],'notes':notes})
 print(index,dst.name,flush=True)
(HERE/'report.json').write_text(json.dumps(records,indent=2,ensure_ascii=False)+'\n')
