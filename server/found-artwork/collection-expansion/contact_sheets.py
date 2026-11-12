"""Read-only artwork contact sheets for visual review; does not change assets."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
albums=json.loads((HERE/'integrated.json').read_text());root=HERE.parents[1]
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',15)
for group in range(0,len(albums),4):
 rows=albums[group:group+4];canvas=Image.new('RGB',(920,270*len(rows)),(243,240,232));draw=ImageDraw.Draw(canvas)
 for y,album in enumerate(rows):
  draw.text((12,y*270+7),album['artist']+' — '+album['title'],fill='#24251f',font=font)
  for col,side in enumerate(['front','back','vinyl','cd']):
   url=album['assets'].get(side)
   if not url:
    art=json.loads((root/'artwork.json').read_text());url='/static/'+art[album['uri']][side]
   with Image.open(root/url.lstrip('/')) as im:
    im=im.convert('RGBA');im.thumbnail((210,210))
    tile=Image.new('RGBA',(210,210),(221,221,217,255));td=ImageDraw.Draw(tile)
    for xx in range(0,210,14):
     for yy in range(0,210,14):
      if (xx//14+yy//14)%2:td.rectangle((xx,yy,xx+13,yy+13),fill=(249,249,245,255))
    tile.alpha_composite(im,((210-im.width)//2,(210-im.height)//2));canvas.paste(tile.convert('RGB'),(10+col*230,y*270+34))
   draw.text((12+col*230,y*270+246),side,fill='#24251f',font=font)
 path=HERE/f'contact-{group//4+1}.jpg';canvas.save(path,quality=92);print(path)
