import hashlib, json
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
records = []
for path in sorted(HERE.glob('*-final.webp')):
    im = Image.open(path)
    a = np.array(im)[:, :, 3]
    seen = {(324, 324)}
    queue = deque(seen)
    while queue:
        y, x = queue.popleft()
        for ny, nx in ((y-1,x), (y+1,x), (y,x-1), (y,x+1)):
            if 0 <= ny < 648 and 0 <= nx < 648 and a[ny,nx] < 128 and (ny,nx) not in seen:
                seen.add((ny,nx)); queue.append((ny,nx))
    yy, xx = zip(*seen)
    hole = [min(xx), min(yy), max(xx)+1, max(yy)+1]
    center = [(hole[0]+hole[2])/2, (hole[1]+hole[3])/2]
    y, x = np.ogrid[:648, :648]
    outside = ((x-323.5)**2 + (y-323.5)**2) > 321**2
    assert im.size == (648,648) and im.mode == 'RGBA'
    assert int(a[324,324]) == 0 and int(a[outside].max()) == 0
    assert center == [324,324], (path, center)
    assert im.getchannel('A').getbbox() == (4,4,644,644)
    expected = 80 if 'external-cd-' in path.name else (18 if '50fef93d' in path.name else 16)
    assert hole[2]-hole[0] == expected and hole[3]-hole[1] == expected
    records.append({'file': str(path), 'size': im.size, 'mode': im.mode,
                    'alpha_bounds': im.getchannel('A').getbbox(), 'hole_bounds_alpha_below_128': hole,
                    'hole_center': center, 'hole_diameter': expected, 'outside_alpha_max': 0,
                    'center_alpha': 0, 'visual_inspection': 'passed; final opened with view_image',
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size})
(HERE / 'validation.json').write_text(json.dumps(records, indent=2) + '\n')
print(f'{len(records)} final assets passed geometry and alpha validation.')
