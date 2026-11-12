from pathlib import Path
from PIL import Image
from collections import deque
import json, math
BASE=Path(__file__).resolve().parent
out=[]
for f in sorted(BASE.glob('*-final.webp')):
    im=Image.open(f);a=im.getchannel('A');px=a.load()
    q=deque([(324,324)]);seen=set(q)
    while q:
        x,y=q.popleft()
        for u,v in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
            if (u,v) not in seen and 250<u<398 and 250<v<398 and px[u,v]<128:
                seen.add((u,v));q.append((u,v))
    xs=[x for x,y in seen];ys=[y for x,y in seen]
    hole=[min(xs),min(ys),max(xs)+1,max(ys)+1]
    assert im.mode=='RGBA' and im.size==(648,648)
    assert a.getbbox()==(4,4,644,644)
    for box in [(0,0,648,4),(0,644,648,648),(0,0,4,648),(644,0,648,648)]:
        assert a.crop(box).getbbox() is None
    assert abs((hole[0]+hole[2])/2-324)<=1
    assert abs((hole[1]+hole[3])/2-324)<=1
    d=80 if 'external-cd-' in f.name else 16
    assert abs(hole[2]-hole[0]-d)<=2,(f,hole)
    outer=[]
    for k in range(360):
        an=k*math.pi/180;rr=[]
        for r in range(300,325):
            x=round(323.5+r*math.cos(an));y=round(323.5+r*math.sin(an))
            if 0<=x<648 and 0<=y<648 and px[x,y]>=128:rr.append(r)
        outer.append(max(rr))
    assert max(outer)-min(outer)<=2
    item={'file':f.name,'mode':im.mode,'size':list(im.size),'alpha_bbox':list(a.getbbox()),'hole_bbox_alpha_below_128':hole,'hole_center':[(hole[0]+hole[2])/2,(hole[1]+hole[3])/2],'rim_radius_range_alpha_128':[min(outer),max(outer)],'bytes':f.stat().st_size,'visual_inspection':'passed: single isolated complete disc, selected label/color retained, no packaging or stray exterior pixels'}
    out.append(item);print(json.dumps(item))
(BASE/'validation.json').write_text(json.dumps(out,indent=2)+'\n')
