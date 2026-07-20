"""Organize a char's prompt-named download animation folders into official
animations/<action>/<OURDIR>/ using the yaml anchor. For web-generated sets
whose folders are named by prompt prefix (not 'idle'/'walk'/...).
Usage: _organize_web.py <CharId> [action ...]
"""
import shutil
import sys
from pathlib import Path
import yaml
from PIL import Image

DIRS = {"south", "south-east", "east", "north-east", "north", "north-west", "west", "south-west"}
RULES = [
    ('walk', ['walks', 'marches', 'march', 'steps forward', 'rides', 'walk']),
    ('attack', ['draws', 'slash', 'swing', 'cast', 'thrust', 'strike', 'shoot', 'releases an arrow', 'battle axe', 'sword held', 'attack']),
    ('knockback', ['recoil', 'takes a hit', 'takes a sharp hit', 'flinch', 'braces with', 'hit and', 'knockback']),
    ('knockout', ['collapse', 'falls', 'slams onto', 'down on the ground', 'lurches', 'stumbles', 'knockout']),
    ('idle', ['breathing', 'stands in idle', 'calm idle', 'sits mounted', 'idle']),
]


def classify(name):
    low = name.lower().replace('_', ' ')
    for act, kws in RULES:
        if any(k in low for k in kws):
            return act
    return None


char_id = sys.argv[1]
data = yaml.safe_load(open('pixellab/character_status.yaml', encoding='utf-8'))
st = next(c['states'][0] for c in data['characters'] if c['id'] == char_id)
anchor = st['anchor']
anims = st['animations']
# per-action target game dirs, derived from the yaml (anchor-generic): the real
# (non-mirror) sources are `dirs`; mirror targets are added from the anchor.
gamedirs = {}
for act, cfg in anims.items():
    real = list(cfg['dirs'])
    mirrors = [x for x, v in anchor.items()
               if isinstance(v, str) and v.startswith('mirror:') and v.split(':', 1)[1] in real]
    gamedirs[act] = real + mirrors
only = set(sys.argv[2:]) or set(gamedirs)
root = Path('pixellab/characters') / char_id.lower()
dl = root / 'download'

# classify download action folders -> {action: [folders...]} (merge fragments)
folders = {}
for p in dl.rglob('*'):
    if p.is_dir() and p.parent.name == 'animations':
        act = classify(p.name)
        if act:
            folders.setdefault(act, []).append(p)


def find_src(action, px):
    for f in folders.get(action, []):
        if (f / px).is_dir():
            return f / px
    return None


def copyf(src, dst, flip=False):
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for f in sorted(src.glob('*.png')):
        im = Image.open(f)
        if flip:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        im.save(dst / f.name)
    return len(list(dst.glob('*.png')))


for action in [a for a in gamedirs if a in only]:
    if action not in folders:
        print(f'{action}: no download folder, skip')
        continue
    real = list(anims[action]['dirs'])
    made = []
    for g in real:
        px = anchor[g]
        sdir = find_src(action, px)
        if sdir is None:
            print(f'  !! {action}/{g}<-{px} missing in download')
            continue
        n = copyf(sdir, root / 'animations' / action / g)
        made.append(f'{g}<-{px}({n})')
    # mirrors
    for mdir, val in anchor.items():
        if isinstance(val, str) and val.startswith('mirror:'):
            srcg = val.split(':', 1)[1]
            if srcg in real and (root / 'animations' / action / srcg).is_dir():
                n = copyf(root / 'animations' / action / srcg, root / 'animations' / action / mdir, flip=True)
                made.append(f'{mdir}=flip{srcg}({n})')
    print(f'{action:10s} {made}')
