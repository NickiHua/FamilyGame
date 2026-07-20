# PixelLab objects — by category

Generated map-object sprites live here, one folder per category. The prompt +
PixelLab call for each is recorded in `../object_status.yaml`.

- `houses/`   — buildings (high top-down, isolated, no grass base)
- `bridges/`  — bridges (no water/grass baked in; composites over the river)
- `trees/`    — trees / foliage

Approved sprites get copied into `Assets/Art/Objects/<Category>/` (with a `.meta`)
for Unity. Source of truth for placement is `Assets/Art/Maps/stage1_objects.json`
(via the `Tools/FantacyCentry/Export|Build Placed Objects` round-trip).

Production endpoint = `POST /v2/map-objects` (cheap, ~1 generation) via
`scripts/pixellab_map_object.py`. The website "create-object" creator is the
expensive Pro path (20-40 generations) — use only when you want its review grid.
