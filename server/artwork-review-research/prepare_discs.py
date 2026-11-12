"""Use PhotoCraft masks/crops to preserve approved scans, with no generated pixels."""
import hashlib,json,subprocess,html
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'found-artwork/approved-discs'
DEST=ROOT/'static/discs';DEST.mkdir(exist_ok=True)
CLI='/Applications/PhotoCraft.app/Contents/MacOS/photocraft-cli'
# Measured elliptical extents and spindle centers in a normalized 600×600 canvas.
# CD holes are 1/8 of the physical disc diameter; vinyl holes ~2.5%.
geometry={
 '27957331583':([1,0,598,600],[301,305]),
 '37031212075':([35,21,539,540],[303,296]),
 '11290212496':([4,3,592,594],[300,304]),
 '46301834535':([1,4,598,592],[300,300]),
 '43055865331':([29,28,542,542],[300,298]),
 '31525003400':([31,34,535,533],[300,300]),
 '27308702840':([2,3,595,595],[300,300]),
 '30672682790':([3,3,594,594],[301,299]),
 '30439409589':([48,56,505,504],[300,308]),
 '36353783387':([11,0,578,580],[295,290]),
 '40754684609':([33,26,535,537],[300,293]),
 '20296732042':([14,14,574,573],[301,300]),
 '31475350562':([27,27,546,546],[300,300]),
}
# Tighten white/black scan margins to the actual plastic edge.
for mid,box in {
 '46282183260':[8,3,585,592], '41378810856':[2,3,592,590],
 '31525054943':[13,16,578,579], '43587718872':[2,4,590,589],
 '30664206604':[5,7,590,582], '30674242009':[15,11,565,577],
 '41013457802':[23,24,556,549], '29116227297':[12,7,570,582],
 '17875300867':[12,12,582,584], '43331545565':[16,17,568,568],
 '17876783569':[22,25,542,548], '29608518514':[15,3,581,593],
 '29608649345':[2,2,574,589], '31475350562':[24,25,554,553],
 '40470700521':[16,20,562,555], '8907960564':[9,4,578,587],
 '45418833805':[5,4,579,592], '10710753514':[22,24,563,563],
}.items():geometry[mid]=(box,[300,300])
sources=json.loads((OUT/'sources.json').read_text());manifest={};records=[];counts={}
for c in sources:
 mid=c['image_id'];bounds,center=geometry.get(mid,([5,5,590,590],[300,300]))
 sx,sy=c['width']/600,c['height']/600
 outer=dict(zip(['x','y','width','height'],[round(bounds[0]*sx),round(bounds[1]*sy),round(bounds[2]*sx),round(bounds[3]*sy)]))
 diameter=min(bounds[2:])*(.025 if c['kind']=='vinyl' else .125)
 hole={'x':round((center[0]-diameter/2)*sx),'y':round((center[1]-diameter/2)*sy),'width':max(2,round(diameter*sx)),'height':max(2,round(diameter*sy))}
 dst=OUT/(mid+'-cutout.webp');commands=[('layer.new.layerFromBackground',{'ifPresent':True}),('select.rect',outer|{'ellipse':True}),('select.rect',hole|{'ellipse':True,'mode':'subtract'}),('layer.layerMask.revealSelection',{}),('select.deselect',{}),('image.crop',outer|{'targetWidth':640,'targetHeight':640,'resample':'lanczos'}),('image.canvasSize',{'width':648,'height':648,'anchor':'center','extensionColor':'transparent'})]
 args=[CLI,'run',str(OUT/c['source_file'])]
 for command,params in commands:args+=['--cmd',command,'--params',json.dumps(params)]
 args+=['--out',str(dst),'--quality','88']
 result=subprocess.run(args,capture_output=True,text=True)
 if result.returncode:raise RuntimeError(mid+': '+result.stderr+result.stdout)
 # PhotoCraft's lossy WebP stores alpha uncompressed. Repack the decoded
 # cutout losslessly so the alpha compresses, retaining all prepared pixels.
 packed=OUT/(mid+'-web.webp')
 converted=subprocess.run([CLI,'convert',str(dst),str(packed),'--metadata','none'],capture_output=True,text=True)
 if converted.returncode:raise RuntimeError(mid+': '+converted.stderr)
 dst=packed
 with Image.open(dst)as im:
  assert im.mode=='RGBA' and im.size==(648,648),(mid,im.mode,im.size)
  assert im.getpixel((0,0))[3]==0
 digest=hashlib.sha256(dst.read_bytes()).hexdigest()[:12];name=mid+'.'+digest+'.webp';(DEST/name).write_bytes(dst.read_bytes())
 uri=c['uri'];counts[(uri,c['kind'])]=counts.get((uri,c['kind']),0)+1
 label='Vinyl'if c['kind']=='vinyl'else'CD';n=counts[(uri,c['kind'])]
 if n>1:label+=' '+str(n)
 option={'id':mid,'kind':c['kind'],'label':label,'image':'/static/discs/'+name}
 manifest.setdefault(uri,[]).append(option)
 records.append(c|{'outer_ellipse':outer,'spindle_hole':hole,'output':option['image'],'processing':'PhotoCraft elliptical layer mask, crop, 640px resample, 4px transparent rim; original printing retained.'})
 print(mid,label,'prepared',flush=True)
(ROOT/'disc-artwork.json').write_text(json.dumps(manifest,indent=2)+'\n')
(OUT/'processed.json').write_text(json.dumps(records,indent=2,ensure_ascii=False)+'\n')
s='<html><style>body{margin:0;font:11px sans-serif;background:#eee}.grid{display:grid;grid-template-columns:repeat(6,1fr);gap:8px}.photo{background:repeating-conic-gradient(#aaa 0% 25%,#ddd 0% 50%)0 0/18px 18px}img{width:100%;aspect-ratio:1;object-fit:contain}p{margin:3px 0 12px;font-size:10px}</style><div class="grid">'
for i,c in enumerate(records):s+='<div><div class="photo"><img src="'+str(ROOT/c['output'].lstrip('/'))+'"></div><p>'+html.escape(f"{i}: {c['album_id']} / {c['image_id']}")+'</p></div>'
(OUT/'cutouts-review.html').write_text(s+'</div></html>')
print('Prepared',len(records),'approved cutouts for',len(manifest),'albums.',flush=True)
