import json, subprocess, math
from pathlib import Path
from PIL import Image

BASE=Path(__file__).resolve().parent
CLI='/Applications/PhotoCraft.app/Contents/MacOS/photocraft-cli'
rows=json.loads((BASE/'assigned-rows.json').read_text())
geometry={13:(626,622,604,'#22211e'),16:(624,627,596,'#ab5f3f'),18:(624,628,595,'#453c3e'),22:(617,629,596,'#2a6e31'),28:(624,626,588,None)}
commands_log=[]
for row in rows:
    idx=row['row_index'];mid=row['image_id'];cx,cy,r,color=geometry[idx]
    src=BASE/(mid+('-generated-v2.png' if idx==28 else '-generated.png'))
    outer={'x':cx-r,'y':cy-r,'width':r*2,'height':r*2}
    d=2*r*(.125 if idx==28 else .025)
    hole={'x':cx-d/2,'y':cy-d/2,'width':d,'height':d}
    cmds=[('layer.new.layerFromBackground',{'ifPresent':True})]
    if color:
        # Restore only the tiny generated spindle fringe, then cut a precise physical hole.
        cmds += [('select.rect',{'x':cx-22,'y':cy-22,'width':44,'height':44,'ellipse':True}),('edit.fill',{'contents':'color','color':color,'opacity':100,'preserveTransparency':False}),('select.deselect',{})]
    cmds += [('select.rect',outer|{'ellipse':True}),('select.rect',hole|{'ellipse':True,'mode':'subtract'}),('layer.layerMask.revealSelection',{}),('select.deselect',{}),('image.crop',outer|{'targetWidth':640,'targetHeight':640,'resample':'lanczos'}),('image.canvasSize',{'width':648,'height':648,'anchor':'center','extensionColor':'transparent'})]
    if idx==28:
        # Precision circular silver perimeter continues the photographed CD rim.
        cmds += [('select.rect',{'x':4,'y':4,'width':640,'height':640,'ellipse':True}),('edit.stroke',{'width':2,'color':'#b9bfc4','location':'inside','opacity':100,'preserveTransparency':True}),('select.deselect',{})]
    intermediate=BASE/(mid+'-standardized.png')
    argv=[CLI,'run',str(src)]
    for name,params in cmds:argv += ['--cmd',name,'--params',json.dumps(params)]
    argv += ['--out',str(intermediate)]
    completed=subprocess.run(argv,capture_output=True,text=True)
    if completed.returncode:raise RuntimeError(completed.stderr+completed.stdout)
    if idx==28:
        # Flattened round-trip confines the antialiased stroke to the exact final rim.
        remasked=BASE/(mid+'-rim-masked.png')
        precise=[('layer.new.layerFromBackground',{'ifPresent':True}),('select.rect',{'x':4,'y':4,'width':640,'height':640,'ellipse':True}),('select.rect',{'x':284,'y':284,'width':80,'height':80,'ellipse':True,'mode':'subtract'}),('layer.layerMask.revealSelection',{}),('select.deselect',{})]
        argv=[CLI,'run',str(intermediate)]
        for name,params in precise:argv += ['--cmd',name,'--params',json.dumps(params)]
        argv += ['--out',str(remasked)]
        completed=subprocess.run(argv,capture_output=True,text=True)
        if completed.returncode:raise RuntimeError(completed.stderr+completed.stdout)
        intermediate=remasked
        cmds += [('flattened-remask',precise)]
    dst=BASE/(mid+'-final.webp')
    completed=subprocess.run([CLI,'convert',str(intermediate),str(dst),'--metadata','none'],capture_output=True,text=True)
    if completed.returncode:raise RuntimeError(completed.stderr+completed.stdout)
    commands_log.append({'row_index':idx,'source':str(src),'commands':cmds,'output':str(dst)})
    with Image.open(dst) as im:
        assert im.size==(648,648) and im.mode=='RGBA'
        assert im.getpixel((324,324))[3]==0
        assert im.getpixel((0,0))[3]==0
        print(idx,mid,im.size,im.mode,im.getchannel('A').getbbox(),flush=True)
(BASE/'photocraft-commands.json').write_text(json.dumps(commands_log,indent=2)+'\n')
