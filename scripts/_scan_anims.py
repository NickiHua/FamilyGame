"""Scan each character's download/ for animation actions and classify them
into our base set (idle/walk/attack/knockback/knockout [+other]).

Action folders are named by the animation prompt's first words, often
fragmented per-direction with a `-<hash>` suffix. We group by classified
action and union the 8 directions found.
"""
import re
import yaml
from pathlib import Path

DIRS = {"south", "south-east", "east", "north-east",
        "north", "north-west", "west", "south-west"}

# keyword -> our action (checked in order; first match wins). NOTE: walk/attack/
# knockback verbs are checked BEFORE idle, because walk/etc folder names often
# contain "F1 idle ..." as a frame descriptor which must NOT match idle.
RULES = [
    ('walk',      ['walks', 'walk ', 'marches', 'march ', 'steps forward', 'steady step',
                   'advances', 'strides', 'marching', 'walk']),
    ('attack',    ['draws', 'slash', 'swings', 'swing ', 'casts', 'cast ', 'spell', 'thrust',
                   'stab', 'strike', 'shoots', 'shoot ', 'fires', 'lance', 'chop', 'overhead',
                   'releases an arrow', 'battle axe', 'preparing the', 'attack']),
    ('knockback', ['recoil', 'takes a hit', 'takes a sharp hit', 'flinch', 'knockback',
                   'staggers', 'braces with', 'hit and']),
    ('knockout',  ['collapse', 'defeat', 'falls', 'slams onto', 'down on the ground', 'dies',
                   'lurches', 'knocked out', 'knockout']),
    ('defense',   ['raises his shield', 'raises her shield', 'defensive stance', 'guard stance',
                   'defense', 'block']),
    ('idle',      ['breathing', 'idle breathing', 'stands in idle', 'guard breath', 'idle']),
]


def classify(name: str):
    low = name.lower().replace('_', ' ')
    for action, kws in RULES:
        if any(k in low for k in kws):
            return action
    return None


def base_name(folder_name: str) -> str:
    # strip trailing -<8 hex> fragment suffix
    return re.sub(r'-[0-9a-f]{8}$', '', folder_name)


d = yaml.safe_load(open('pixellab/character_status.yaml', encoding='utf-8'))
ACTIONS = ['idle', 'walk', 'attack', 'knockback', 'knockout', 'defense']

print(f'{"character":20s} ' + ' '.join(f'{a[:5]:>6s}' for a in ACTIONS) + '   other')
for c in d['characters']:
    name = c['id']
    dl = Path(f'pixellab/characters/{name.lower()}/download')
    found = {a: set() for a in ACTIONS}
    other = {}
    if dl.exists():
        anim_dirs = [p for p in dl.rglob('*') if p.is_dir() and p.parent.name == 'animations']
        for ad in anim_dirs:
            act = classify(ad.name)
            dset = {p.parent.name for p in ad.rglob('*.png')} & DIRS
            if act:
                found[act] |= dset
            else:
                other.setdefault(base_name(ad.name)[:28], set()).update(dset)
    cells = []
    for a in ACTIONS:
        n = len(found[a])
        cells.append(f'{n}/8' if n else '  -')
    othertxt = ','.join(sorted(other)) if other else ''
    print(f'{name:20s} ' + ' '.join(f'{x:>6s}' for x in cells) + ('   ' + othertxt if othertxt else ''))
