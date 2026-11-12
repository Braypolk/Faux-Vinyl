import json
from prepare import run,normalize,HERE
run('beyonce-vinyl-generated-original.png','beyonce-vinyl-opaque.png',[
 ('layer.newFillLayer.solidColor',{'color':'#080808'}),('layer.arrange.sendToBack',{}),('layer.flattenImage',{})])
normalize('beyonce-vinyl-opaque.png','beyonce-vinyl-base.webp',[42,40,1166,1174],[624,627],16)
normalize('beyonce-discogs-4.jpg','beyonce-original-label-normalized.png',[0,0,600,600],[296,298],16)
run('beyonce-original-label-normalized.png','beyonce-original-label.png',[
 ('image.crop',{'x':4,'y':4,'width':640,'height':640,'targetWidth':240,'targetHeight':240,'resample':'lanczos'}),
 ('select.rect',{'x':107,'y':107,'width':26,'height':26,'ellipse':True}),
 ('edit.fill',{'contents':'color','color':'#202020'}),('select.deselect',{}),
 ('select.rect',{'x':0,'y':0,'width':240,'height':240,'ellipse':True}),
 ('select.rect',{'x':112,'y':112,'width':16,'height':16,'ellipse':True,'mode':'subtract'}),
 ('layer.layerMask.revealSelection',{}),('select.deselect',{})])
run('beyonce-vinyl-base.webp','beyonce-vinyl.webp',[
 ('file.placeEmbedded',{'path':str(HERE/'beyonce-original-label.png'),'fit':False,'smartObject':False,'scale':100,'center':[324,324]})])
