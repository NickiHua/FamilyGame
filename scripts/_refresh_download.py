"""Refresh a character's download/: wipe it, re-pull the fresh zip (with new
animations) from the server, and unzip. Usage: _refresh_download.py <CharId>"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yaml
from pixellab_gen_character import download_character_zip, unzip  # noqa: E402

char_id = sys.argv[1]
d = yaml.safe_load(open('pixellab/character_status.yaml', encoding='utf-8'))
cid = None
for c in d['characters']:
    if c['id'] == char_id:
        cid = c['states'][0]['character_id']
        break
if not cid:
    raise SystemExit(f'{char_id} not found')

token = Path('pixellabkey.txt').read_text().strip()
folder = Path('pixellab/characters') / char_id.lower()
dl = folder / 'download'
if dl.exists():
    shutil.rmtree(dl)
dl.mkdir(parents=True)
zp = dl / f'{cid}.zip'
download_character_zip(token, cid, zp)
unzip(zp, dl)
print(f'{char_id}: refreshed download/ from {cid}')
