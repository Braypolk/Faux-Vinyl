"""Precise PhotoCraft normalization of built-in imagegen reconstructions."""
import json, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLI = '/Applications/PhotoCraft.app/Contents/MacOS/photocraft-cli'
GEOMETRY = {
    'external-cd-fc41f1c0bae028461520': (622, 622, 598, 150),
    'external-cd-a0a6fd323f9dfea9c512': (626, 626, 607, 158),
    'external-vinyl-4c8f03255fc4579b35f8': (626, 626, 594, None),
    'external-vinyl-50fef93d2965b6ed2e41': (626, 629, 589, None),
}
log = []

def run(source, commands, dest):
    args = [CLI, 'run', str(source)]
    for name, params in commands:
        args += ['--cmd', name, '--params', json.dumps(params)]
    args += ['--out', str(dest), '--quality', '95']
    result = subprocess.run(args, capture_output=True, text=True)
    log.append({'source': str(source), 'commands': commands, 'destination': str(dest), 'returncode': result.returncode})
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)

for mid, (cx, cy, radius, patch_size) in GEOMETRY.items():
    source = HERE / (mid + '-generated.png')
    if patch_size:
        # Resize the generated clear/silver annulus only, to bring its hole to
        # physical CD proportions while retaining the generated ring pixels.
        patch = HERE / (mid + '-hub-normalized.png')
        half = 180 if mid == 'external-cd-a0a6fd323f9dfea9c512' else 200
        run(source, [
            ('select.rect', {'x': cx-half, 'y': cy-half, 'width': half*2, 'height': half*2, 'ellipse': True}),
            ('layer.layerMask.revealSelection', {}),
            ('select.deselect', {}),
            ('image.crop', {'x': cx-half, 'y': cy-half, 'width': half*2, 'height': half*2, 'targetWidth': patch_size, 'targetHeight': patch_size, 'resample': 'lanczos'}),
        ], patch)
    commands = [
        ('image.crop', {'x': cx-radius, 'y': cy-radius, 'width': radius*2, 'height': radius*2, 'targetWidth': 640, 'targetHeight': 640, 'resample': 'lanczos'}),
        ('image.canvasSize', {'width': 648, 'height': 648, 'anchor': 'center', 'extensionColor': 'transparent'}),
    ]
    if patch_size:
        commands += [
            ('file.placeEmbedded', {'path': str(patch), 'fit': False, 'scale': 100, 'smartObject': False, 'center': [324, 324]}),
            ('layer.mergeDown', {}),
        ]
    hole = 80 if patch_size else (18 if mid == 'external-vinyl-50fef93d2965b6ed2e41' else 16)
    commands += [
        ('select.rect', {'x': 4, 'y': 4, 'width': 640, 'height': 640, 'ellipse': True}),
        ('select.rect', {'x': 324-hole/2, 'y': 324-hole/2, 'width': hole, 'height': hole, 'ellipse': True, 'mode': 'subtract'}),
        ('layer.layerMask.revealSelection', {}),
        ('select.deselect', {}),
    ]
    run(source, commands, HERE / (mid + '-final.webp'))
    print(mid, 'ready', flush=True)
(HERE / 'photocraft-processing.json').write_text(json.dumps(log, indent=2) + '\n')
