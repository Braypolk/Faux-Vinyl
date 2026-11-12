from pathlib import Path
import json
P=Path(__file__).resolve().parent
source={x['name']:x for x in json.loads((P/'selected-sources.json').read_text())}
prompts=json.loads((P/'prompts.json').read_text())
dates={'1989':'2014-10-27','folklore':'2020-07-24','thank-u-next':'2019-02-08'}
date_sources={
 '1989':'https://music.apple.com/us/album/1989/1440935467',
 'folklore':'https://open.spotify.com/album/2fenSS68JI1h4Fo296JfGr',
 'thank-u-next':'https://music.apple.com/us/album/thank-u-next/1450330588'}
labels={
 '1989':('Vinyl · original 2014 black pressing, side A','CD · original 2014'),
 'folklore':('Vinyl · in the trees, beige, side 1','CD · in the weeds'),
 'thank-u-next':('Vinyl · black, side 1','CD · pink')}
rows=[]
for name in dates:
 spotify=json.loads((P/(name+'-spotify.json')).read_text())
 uri=spotify['uri'];url='https://open.spotify.com/album/'+uri.split(':')[-1]
 frontsource=url if name!='thank-u-next' else 'https://musicbrainz.org/release/f180cef1-c7b6-4933-92b9-d7292ad1f15c/cover-art'
 row={'id':name,'title':spotify['title'],'artist':spotify['subtitle'],'uri':uri,
      'release_date':dates[name],'songs':'\n'.join(x['title'] for x in spotify['trackList']),
      'tracks':[{'title':x['title'],'artists':x['subtitle'],'uri':x['uri']} for x in spotify['trackList']],
      'metadata_sources':{'spotify':url,'original_release_date':date_sources[name]},
      'front':{'path':str(P/(name+'-front-final.webp')),'source':frontsource,
               'method':'original-scan' if name=='thank-u-next' else 'spotify-official-artwork',
               'reference_path':str(P/(name+('-front-caa-source.jpg' if name=='thank-u-next' else '-front-source.jpg')))},
      'back':{'path':str(P/(name+'-back-final.webp')),'source':source[name+'-back']['source'],
              'download':source[name+'-back']['download'],'method':'photocraft-perspective-correction' if name=='folklore' else 'photocraft-original-scan',
              'reference_path':str(P/(name+'-back-source.jpg'))},'discs':[]}
 if name=='folklore':row['back']['notes']='Actual in-the-trees physical sleeve back includes bonus track the lakes; Spotify URI and searchable tracklist use the original 16-track album. PhotoCraft corner rectification removed photographed tabletop.'
 if name=='thank-u-next':row['front']['notes']='Original black-background physical CD cover; Spotify URI has regional pink cover art.';row['back']['notes']='Original CD rear tray scan cropped to remove side spines. Small text and wear retain source limitations.'
 vsource=source['1989-vinyl-b'] if name=='1989' else source['folklore-vinyl'] if name=='folklore' else {
    'source':'https://www.urbanoutfitters.com/en-gb/shop/ariana-grande-thank-u-next-lp',
    'download':'https://imageseu.urbndata.com/is/image/UrbanOutfittersEU/0550434962525_000_d?$xlarge$=&fit=constrain&qlt=95&wid=1600'}
 ref='1989-vinyl-b-source.jpg' if name=='1989' else 'folklore-vinyl-source.jpg' if name=='folklore' else 'thank-u-next-vinyl-uo-source.jpg'
 if name=='folklore':
    prompt=prompts['beige_surface'];note='Grooved beige surface reconstructed from the physical in-the-trees pressing to remove strong window-grid reflections. Original printed forest label pixels were rectified and composited, including real text. Plastic tint and groove field remain an approximation of the photographed pressing.'
 else:
    prompt=prompts['black_initial']+'\n\nFOLLOW-UP SURFACE EDIT:\n'+prompts['black_surface']
    note='Complete black vinyl groove field is reconstructed; authentic photographed printed label pixels were perspective-corrected and composited at 212px diameter, with no generated lettering. The groove plate is shared with the other reconstructed black record; detailed groove positions are approximate.'
    if name=='thank-u-next':note+=' Retailer reference shows only a partial record, so the outer record geometry was completed using the black material plate; original pink side-1 printing is retained.'
 row['discs'].append({'id':name+'-vinyl','kind':'vinyl','label':labels[name][0],
     'path':str(P/(name+'-vinyl-final.webp')),'source':vsource['source'],'download':vsource['download'],
     'reference_path':str(P/ref),'method':'reference-reconstruction','prompt':prompt,'notes':note,
     'geometry':{'size':[648,648],'disc_diameter':640,'label_diameter':212,'hole_diameter':16,'center':[324,324]},
     'generated_original':str(P/('beige-vinyl-surface-generated.png' if name=='folklore' else 'black-vinyl-surface-generated.png'))})
 csource=source[name+'-cd'];note='Actual physical CD scan; PhotoCraft ellipse/spindle correction, circular alpha and centered 80px hole. Original photographed printing and ordinary surface highlights retained.'
 if name=='folklore':note+=' This is the official in-the-weeds alternate art edition (Brazil pressing), accurately labeled as that variant.'
 row['discs'].append({'id':name+'-cd','kind':'cd','label':labels[name][1],
      'path':str(P/(name+'-cd-final.webp')),'source':csource['source'],'download':csource['download'],
      'reference_path':str(P/(name+'-cd-source.jpg')),'method':'photocraft-cutout','prompt':None,'notes':note,
      'geometry':{'size':[648,648],'disc_diameter':640,'hole_diameter':80,'center':[324,324]}})
 rows.append(row)
(P/'report.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
print('Prepared',len(rows),'albums,',sum(2+len(x['discs']) for x in rows),'final assets.')
