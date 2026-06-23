"""Install the 12 cut Gemini icons into the art master folder and Unity Assets.

- Copies all 12 cut PNGs to art/ui/icon/ (master, outside Assets).
- Copies all 12 into Assets/Art/UI/icons/.
- For icons whose name already exists in Assets, keeps the existing .meta (so the
  GUID and any references survive) but flips filterMode to Bilinear.
- For new icon names, writes a .meta cloned from an existing icon meta with a fresh
  GUID and Bilinear filtering so Unity imports them as Sprites.
"""
import os
import re
import shutil
import uuid

CUT = "art_undecided/ui/icon/cut"
MASTER = "art/ui/icon"
ASSETS = "Assets/Art/UI/icons"
TEMPLATE_META = os.path.join(ASSETS, "icon_attack.png.meta")

ICONS = [
    "icon_frame_empty", "icon_attack", "icon_skill", "icon_magic",
    "icon_defend", "icon_wait", "icon_item", "icon_move",
    "icon_transform", "icon_equip", "icon_status", "icon_summon",
]


def set_bilinear(meta_text):
    return re.sub(r"filterMode: 0", "filterMode: 1", meta_text, count=1)


def main():
    os.makedirs(MASTER, exist_ok=True)
    with open(TEMPLATE_META, "r", encoding="utf-8") as f:
        template = f.read()

    for name in ICONS:
        src = os.path.join(CUT, name + ".png")
        # master copy
        shutil.copy2(src, os.path.join(MASTER, name + ".png"))
        # assets png
        dst_png = os.path.join(ASSETS, name + ".png")
        dst_meta = dst_png + ".meta"
        shutil.copy2(src, dst_png)

        if os.path.exists(dst_meta):
            # existing icon: keep GUID, just ensure bilinear
            with open(dst_meta, "r", encoding="utf-8") as f:
                t = f.read()
            t = set_bilinear(t)
            with open(dst_meta, "w", encoding="utf-8") as f:
                f.write(t)
            action = "overwrite (kept meta, bilinear)"
        else:
            # new icon: clone template meta with fresh GUID + bilinear + renamed sprite
            t = template
            t = re.sub(r"guid: [0-9a-f]{32}", "guid: " + uuid.uuid4().hex, t, count=1)
            t = t.replace("icon_attack", name)
            t = set_bilinear(t)
            with open(dst_meta, "w", encoding="utf-8") as f:
                f.write(t)
            action = "new (meta authored, bilinear)"
        print(f"{name:18s} -> {action}")

    print("\ndone. master:", MASTER, "| assets:", ASSETS)


if __name__ == "__main__":
    main()
