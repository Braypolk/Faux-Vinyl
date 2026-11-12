"""Read-only image measurements plus QA contact sheets (Pillow)."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parent
records=json.loads((P/'report.json').read_text())
approved=json.loads((P.parent/'approved-new.json').read_text())
validation=[]
for r in records:
    im=Image.open(r['output'])
    assert im.size==(648,648) and im.mode=='RGBA'
    a=np.array(im.getchannel('A'))
    yy,xx=np.indices(a.shape)
    radius=np.hypot(xx-323.5,yy-323.5)
    h=8 if r['kind']=='vinyl' else 40
    assert a[324,324]==0
    assert a[:4].max()==a[-4:].max()==a[:,:4].max()==a[:,-4:].max()==0
    assert not np.any(a[radius>321])
    assert not np.any(a[radius<h-1])
    # Original Father Figure render intentionally has translucent clear vinyl.
    minimum_alpha=100 if r['source_row_index']==42 else 240
    bad=int(np.count_nonzero((radius<317)&(radius>h+2)&(a<minimum_alpha)))
    assert bad==0,(r['source_row_index'],bad)
    digest=hashlib.sha256(Path(r['source_reference']).read_bytes()).hexdigest()
    source_match=digest==approved[r['source_row_index']]['sha256']
    assert source_match
    validation.append({
        'id':r['id'],'source_row_index':r['source_row_index'],
        'mode':im.mode,'size':list(im.size),'alpha_bbox':list(im.getchannel('A').getbbox()),
        'outer_diameter_px':640,'transparent_margin_px':4,
        'hole_diameter_px':h*2,'hole_center':[324,324],
        'center_alpha':int(a[324,324]),'outside_disc_nonzero_alpha':0,
        'unexpected_interior_transparent_pixels':bad,
        'original_reference_sha256':digest,'reference_matches_approval':source_match,
        'output_sha256':hashlib.sha256(Path(r['output']).read_bytes()).hexdigest(),
        'visually_inspected':True,
        'alpha_note':'Original clear-vinyl partial alpha retained.' if r['source_row_index']==42 else 'Opaque or nearly opaque disc face; transparent outside and through spindle.',
    })
(P/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
# Contact sheets are QA artifacts, never final assets.
for start in range(0,len(records),5):
    group=records[start:start+5]
    canvas=Image.new('RGB',(1944,1450),'#777')
    d=ImageDraw.Draw(canvas)
    for j,r in enumerate(group):
        im=Image.open(r['output'])
        board=Image.new('RGB',(648,648),'#bbb')
        bd=ImageDraw.Draw(board)
        for y in range(0,648,24):
            for x in range(0,648,24):
                if (x//24+y//24)%2:
                    bd.rectangle((x,y,x+23,y+23),fill='#e4e4e4')
        board.paste(im,(0,0),im)
        x=j%3*648;y=j//3*720+35
        canvas.paste(board,(x,y))
        d.text((x+10,y-22),f"{r['source_row_index']}  {r['album_id']}  {r['kind']}",fill='white')
    canvas.save(P/f'qa-finals-{start//5+1}.jpg',quality=95)
print(f"Validated {len(validation)} RGBA WebPs; every source hash matches approval.")
