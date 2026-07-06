"""Generate VFX sprite-sheet candidates via the OpenAI Images API.

Reads the API key from openaikey.txt (never printed). Writes PNGs to art/vfx/_gen/.
4 prompts x 2 images = 8 files. quality=medium, transparent background.
"""
import base64
import json
import os
import sys
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "art", "vfx", "_gen")
os.makedirs(OUT, exist_ok=True)

with open(os.path.join(ROOT, "openaikey.txt"), "r", encoding="utf-8") as f:
    KEY = f.read().strip()

JOBS = [
    ("icespike", "1024x1536",
     "2D pixel art sprite sheet of an ice spike magic spell, 12 frames of animation "
     "arranged in a clean, evenly-spaced 3x4 grid, read left-to-right, top-to-bottom. "
     "Each frame centered in its own equal-size cell, identical scale, with the ice "
     "spike rising from the SAME ground baseline at the bottom of every cell. "
     "Sequence: a tiny ice crystal forming, growing into a large sharp ice spike, "
     "shattering violently, dissolving into small frozen fragments. "
     "Clean 16-bit pixel art, vibrant icy blue and white, crisp sprite with a soft "
     "inner glow, side view. Transparent background. "
     "No text, no numbers, no labels, no grid lines, no borders."),

    ("fireball", "1024x1024",
     "2D pixel art sprite sheet of a fireball explosion magic spell, 16 frames of "
     "animation arranged in a clean, evenly-spaced 4x4 grid, read left-to-right, "
     "top-to-bottom. Each frame centered in its own equal-size cell, identical scale. "
     "Sequence: a small fireball forming, flying forward, then detonating into a large "
     "violent fiery explosion with a bright white-hot blast core, expanding flames, "
     "flying embers and rolling smoke, then fading out. "
     "Clean 16-bit pixel art, vibrant orange-red and yellow fire with a soft inner glow, "
     "side view. Transparent background. "
     "No text, no numbers, no labels, no grid lines, no borders."),

    ("lightning", "1024x1536",
     "2D pixel art sprite sheet of a lightning strike magic spell, 12 frames of "
     "animation arranged in a clean, evenly-spaced 3x4 grid, read left-to-right, "
     "top-to-bottom. Each frame centered in its own equal-size cell, identical scale, "
     "with the strike hitting the SAME ground baseline at the bottom of every cell. "
     "Sequence: a bright bolt of lightning striking down from above onto the ground, "
     "a brilliant electric flash, a ground impact shockwave with crackling blue-white "
     "sparks, then dissipating energy. "
     "Clean 16-bit pixel art, vibrant electric blue and white with a soft glow, "
     "side view. Transparent background. "
     "No text, no numbers, no labels, no grid lines, no borders."),

    ("heal", "1024x1536",
     "2D pixel art sprite sheet of a nature healing magic spell, 12 frames of "
     "animation arranged in a clean, evenly-spaced 3x4 grid, read left-to-right, "
     "top-to-bottom. Each frame centered in its own equal-size cell, identical scale, "
     "with the effect rising from the SAME ground baseline at the bottom of every cell. "
     "Sequence: a soft green glow appearing on the ground, blooming into rising motes "
     "of green light and small leaves and petals swirling upward, a gentle radiant ring "
     "of restorative light expanding, then softly fading. "
     "Clean 16-bit pixel art, vibrant fresh green and soft white with a warm gentle glow, "
     "side view. Transparent background. "
     "No text, no numbers, no labels, no grid lines, no borders."),
]

MODELS = ["gpt-image-1.5", "gpt-image-1"]
URL = "https://api.openai.com/v1/images/generations"


def generate(model, prompt, size):
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "n": 2,
        "size": size,
        "quality": "medium",
        "background": "transparent",
        "output_format": "png",
    }).encode("utf-8")
    req = urllib.request.Request(URL, data=body, method="POST")
    req.add_header("Authorization", "Bearer " + KEY)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    model = MODELS[0]
    for name, size, prompt in JOBS:
        for attempt, m in enumerate([model] + [x for x in MODELS if x != model]):
            try:
                print(f"[{name}] generating with {m} ({size}) ...", flush=True)
                data = generate(m, prompt, size)
                model = m  # stick with the one that worked
                imgs = data.get("data", [])
                for i, item in enumerate(imgs):
                    b64 = item.get("b64_json")
                    if not b64:
                        continue
                    path = os.path.join(OUT, f"{name}_{chr(97+i)}.png")
                    with open(path, "wb") as fo:
                        fo.write(base64.b64decode(b64))
                    print(f"    saved {path}", flush=True)
                break
            except urllib.error.HTTPError as e:
                msg = e.read().decode("utf-8", "ignore")
                print(f"    HTTP {e.code} with {m}: {msg[:300]}", flush=True)
                # only fall back to another model on model-not-found style errors
                if e.code in (404,) or "model" in msg.lower():
                    continue
                else:
                    print(f"    non-model error, skipping {name}", flush=True)
                    break
            except Exception as e:  # noqa
                print(f"    error with {m}: {e}", flush=True)
                continue
    print("done.", flush=True)


if __name__ == "__main__":
    main()
