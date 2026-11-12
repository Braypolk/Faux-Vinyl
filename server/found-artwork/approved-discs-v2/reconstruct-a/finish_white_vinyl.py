"""PhotoCraft-only material reconstruction with the exact photographed printed label."""
import importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('geometry',HERE.parent/'cleanup-a/process_batch.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
g.OUT=HERE
rows=json.loads((HERE.parent/'approved-new.json').read_text());row=rows[6]
src=Path(row['reference_path'])
# Actual photographed label: rotated ellipse and the visible physical spindle.
label=HERE/'6-original-label.png'
g.prepare(src,[942,263,332,265],[1108,389],label,diameter=212,theta=25)
steps=[('layer.new.layerFromBackground',{'ifPresent':True}),('image.crop',{'x':0,'y':0,'width':648,'height':648}),('select.all',{}),('edit.clear',{}),('select.deselect',{}),('select.rect',{'x':4,'y':4,'width':640,'height':640,'ellipse':True}),('edit.fill',{'contents':'color','color':'#d4d4c9'}),('select.deselect',{})]
# Fine neutral concentric grooves restore the obscured unprinted white material.
for r in range(122,313,3):
 steps += [('select.rect',{'x':324-r,'y':324-r,'width':2*r,'height':2*r,'ellipse':True}),('select.rect',{'x':325-r,'y':325-r,'width':2*r-2,'height':2*r-2,'ellipse':True,'mode':'subtract'}),('edit.fill',{'contents':'color','color':'#cecec3' if r%2 else '#d9d9cf'}),('select.deselect',{})]
steps += [('file.placeEmbedded',{'path':str(label),'fit':False,'scale':100,'center':[324,324],'smartObject':False}),('layer.mergeVisible',{}),('select.rect',{'x':316,'y':316,'width':16,'height':16,'ellipse':True}),('edit.clear',{}),('select.deselect',{})]
dst=HERE/(row['image_id']+'-final.webp');g.run(src,steps,dst)
report=json.loads((HERE/'report.json').read_text())
item=next(c for c in report if c['id']==row['id'])
item.update(output=str(dst),method='manual-reconstruction',processing='PhotoCraft: original photographed rotated label/spindle projectively rectified without generative edits; label composited over a manually restored off-white circular groove field; centered 16px aperture, 640px disc, 648px RGBA lossless WebP.',prompt='',notes='Original Epic/Essential Michael Jackson side-B printing retained as photographed. Sleeve-obscured white groove material manually approximated with fine concentric grooves; this is a reconstruction, not an untouched scan. Built-in ImageGen rejected the source; no further generation or generation fallback used.')
(HERE/'report.json').write_text(json.dumps(report,indent=2)+'\n')
notes=(HERE/'notes.md').read_text();(HERE/'notes.md').write_text(notes+'\nRoot completion: row 6 is now a PhotoCraft-only manual white-vinyl reconstruction retaining the actual original photographed label. No generation fallback. See finish_white_vinyl.py and report.json. All five rows now have final assets.\n')
print(dst)
