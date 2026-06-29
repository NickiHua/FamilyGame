# 《幻世纪》Tile 出图 Prompt 集

> **用途**：给 GPT-Image / Gemini「Nano Banana」/ Flux 出**可拼接的 64px 像素地面 tile 与物件 sprite**。
> **配套 spec**：`docs/specs/2026-06-15-fantacy-centry-demo-to-steam-design.md` §7（美术管线 v2）。
> **铁律**：玩家只「出图 + 挑选 + 把关」，切片/无缝/边角合成交 Python 脚本。本文件只负责「让 AI 把图出对」。

---

## 0. 全局规格（每条 prompt 都默认遵守）

| 项 | 值 | 说明 |
|---|---|---|
| tile 尺寸 | **64×64 px** | 地面 1 cell = 1 unit（PPU=64） |
| 视角 | **正俯视 top-down（垂直俯视，无倾斜/无透视）** | 战棋格子要对齐，禁等距 isometric、禁 tilt-shift |
| 光照方向 | **统一从左上方打光（top-left light）** | 全套素材必须一致，否则拼接出戏 |
| 调色板 | **统一有限色板（pixel art limited palette）** | 同一关所有 tile/物件共用一套色 |
| 风格 | **复古像素 SRPG（FE GBA / 梦幻模拟战 / FFT 气质）** | 干净、不脏、不写实、不卡通过头 |
| 背景 | **纯透明 或 纯品红 #FF00FF（物件用）** | 方便脚本抠图；地面 tile 满幅不留边 |
| 禁止 | 文字、水印、签名、描边外光晕、3D 渲染感、照片质感、模糊、抗锯齿 | Flux CFG=1 下把禁止项写成正向陈述（见 §5） |

> **复制时把下面这段「全局后缀」追加到每条 prompt 末尾：**
>
> ```
> 64x64 pixel art tile, strict top-down orthographic view (no isometric, no perspective tilt),
> consistent top-left light source, limited retro palette, clean readable pixels, sharp edges,
> no anti-aliasing, no text, no watermark, no signature, no drop shadow halo, no photorealism.
> Style: 16-bit SRPG (Fire Emblem GBA / Langrisser / Final Fantasy Tactics) ground tile.
> ```

---

## ★ 当前批次 · 2026-06-25 · 32px chunky「清爽版」（本次 API 调用用这套）

> **约定**：每次调 GPT-Image **前**先更新此段，使文件 = 即将调用的真实 prompt。
> **本批**：`gpt-image-1`、`quality=low`、`background=opaque`、5 地形 × 3 张 = 15 张 →
> 下采样到 **32**，落 `art_undecided/tiles/32_low/{grass,road,dirt,bridge,water}/`。
> **相对 06-22 64 版的改动**：①更清爽、花纹更少（之前略凌乱）②目标 32 chunky ③新增 泥土/桥，泥土≠道路。
> **桥**：横向桥 → **竖木板并排** + 上下横梁，左右无缝（竖向不平铺，桥仅 1 格高）。

**草地 grass**
```
16-bit JRPG pixel-art GRASS terrain tile, top-down orthographic flat view. Clean green grassland,
MOSTLY UNIFORM medium green with only a FEW subtle darker/lighter pixel patches and very sparse
tiny tufts - keep it clean and calm, minimal speckle, NOT busy. Designed to read as a chunky
32x32 pixel-art tile. Crisp hard-edged pixels, limited palette of a few greens, NO anti-aliasing,
no blur, no gradients, no outlines. Flat even lighting, no shadows, no perspective. Seamless
tileable on all four edges. Fills the whole frame, no border, no grid lines, no text.
```

**道路 road（夯土路，traveled）**
```
16-bit JRPG pixel-art DIRT ROAD / packed travel PATH tile, top-down orthographic flat view. Light
tan / sandy-brown packed road, fairly UNIFORM with faint packed wheel-rut texture and only a
couple of tiny pebbles - clean, not cluttered. Lighter and tidier than raw soil (this is a used
path). Designed to read as a chunky 32x32 pixel-art tile. Crisp hard-edged pixels, limited tan
palette, NO anti-aliasing, no blur, no gradients, no outlines. Flat even lighting, no shadows, no
perspective. Seamless tileable on all four edges. Fills the whole frame, no border, no grid lines,
no text.
```

**泥土 dirt（裸土/泥地，≠道路：更深更糙、无铺装）**
```
16-bit JRPG pixel-art BARE DIRT / MUD GROUND tile, top-down orthographic flat view. Natural raw
earth, DARKER reddish-brown soil, MOSTLY UNIFORM with a few subtle tone patches and maybe one or
two tiny cracks - NOT a built path, no pebbles laid out, rougher and darker than a road. Designed
to read as a chunky 32x32 pixel-art tile. Crisp hard-edged pixels, limited brown palette, NO
anti-aliasing, no blur, no gradients, no outlines. Flat even lighting, no shadows, no perspective.
Seamless tileable on all four edges. Fills the whole frame, no border, no grid lines, no text.
```

**水 water（强调上下也无缝）**
```
16-bit JRPG pixel-art WATER tile, top-down orthographic flat view. Calm blue water, MOSTLY UNIFORM
blue with only a FEW simple lighter ripple-highlight lines - clean and calm, NOT busy. Designed to
read as a chunky 32x32 pixel-art tile. Crisp hard-edged pixels, limited blue palette, NO
anti-aliasing, no blur, no gradients, no outlines, no foam border. Flat even lighting, no shadows,
no perspective. MUST tile seamlessly on all four edges, ESPECIALLY top-to-bottom (ripples wrap
vertically with no seam). Fills the whole frame, no border, no grid lines, no text.
```

**桥面 bridge（横桥 / 竖板 + 上下横梁）**
```
16-bit JRPG pixel-art WOODEN BRIDGE DECK tile for a horizontal (left-right) bridge, top-down
orthographic flat view. Several VERTICAL wooden planks side by side (plank seams are vertical
lines), weathered warm brown wood with subtle grain and a couple of small nail dots, plus a darker
wooden support BEAM running along the TOP edge and the BOTTOM edge. Clean and simple, not
cluttered. Designed to read as a chunky 32x32 pixel-art tile. Crisp hard-edged pixels, limited
wood-brown palette, NO anti-aliasing, no blur, no gradients, no outlines. Flat even lighting, no
shadows, no perspective. Seamless tileable LEFT-TO-RIGHT (the deck repeats horizontally). Fills
the whole frame, no border, no text.
```

---

## ★ 当前批次 B · 2026-06-25 · 32px「自然细节版」（**去掉**清爽强调，做 A/B 对比）

> 与上面 A 批同地形/同规格，唯一区别：**删掉所有 "MOSTLY UNIFORM / minimal / NOT busy / clean&calm" 之类的抑制词**，让纹理自然丰富，用来和 A 的清爽版对比。
> 落 `art_undecided/tiles/32_detail/{grass,road,dirt,bridge,water}/`，同样 quality=low、opaque、5×3=15 张、下采样到 32。

**草地 grass（自然）**
```
16-bit JRPG pixel-art GRASS terrain tile, top-down orthographic flat view. Green grassland with
grass-blade clusters, small tufts and a few tiny flowers, several shades of green forming natural
patches. Designed to read as a chunky 32x32 pixel-art tile. Crisp hard-edged pixels, limited
palette, NO anti-aliasing, no blur, no gradients, no outlines. Flat even lighting, no shadows, no
perspective. Seamless tileable on all four edges. Fills the whole frame, no border, no grid lines,
no text.
```

**道路 road（自然）**
```
16-bit JRPG pixel-art DIRT ROAD / packed travel PATH tile, top-down orthographic flat view. Light
tan / sandy-brown packed road with scattered pebbles and natural soil mottling, a well-traveled
dirt path. Designed to read as a chunky 32x32 pixel-art tile. Crisp hard-edged pixels, limited tan
palette, NO anti-aliasing, no blur, no gradients, no outlines. Flat even lighting, no shadows, no
perspective. Seamless tileable on all four edges. Fills the whole frame, no border, no grid lines,
no text.
```

**泥土 dirt（自然）**
```
16-bit JRPG pixel-art BARE DIRT / MUD GROUND tile, top-down orthographic flat view. Natural raw
earth, darker reddish-brown soil with clumps, small cracks and tone variation, rough untended
ground (not a built path). Designed to read as a chunky 32x32 pixel-art tile. Crisp hard-edged
pixels, limited brown palette, NO anti-aliasing, no blur, no gradients, no outlines. Flat even
lighting, no shadows, no perspective. Seamless tileable on all four edges. Fills the whole frame,
no border, no grid lines, no text.
```

**水 water（自然）**
```
16-bit JRPG pixel-art WATER tile, top-down orthographic flat view. Blue water with rippling wave
highlights and layered blue tones, lively surface. Designed to read as a chunky 32x32 pixel-art
tile. Crisp hard-edged pixels, limited blue palette, NO anti-aliasing, no blur, no gradients, no
outlines, no foam border. Flat even lighting, no shadows, no perspective. MUST tile seamlessly on
all four edges, especially top-to-bottom (ripples wrap vertically with no seam). Fills the whole
frame, no border, no grid lines, no text.
```

**桥面 bridge（自然）**
```
16-bit JRPG pixel-art WOODEN BRIDGE DECK tile for a horizontal (left-right) bridge, top-down
orthographic flat view. Several VERTICAL wooden planks side by side with vertical plank seams,
weathered brown wood with grain, knots and nail heads, plus a darker support BEAM along the TOP
edge and the BOTTOM edge. Designed to read as a chunky 32x32 pixel-art tile. Crisp hard-edged
pixels, limited wood-brown palette, NO anti-aliasing, no blur, no gradients, no outlines. Flat
even lighting, no shadows, no perspective. Seamless tileable LEFT-TO-RIGHT. Fills the whole frame,
no border, no text.
```

---

## ★ 当前批次 C / D · 2026-06-25 · quality=MEDIUM 对照（32-prompt vs 64-prompt）

> 实验目的：在 **medium** 画质下，比较 prompt 写 `chunky 32x32` 还是 `64x64` 的效果。
> 用 **B 批的「自然细节」5 条 prompt**，唯一变量是句中的**尺寸短语 `{SIZE}`**：
> - **C**：`{SIZE}` = `chunky 32x32` → `art_undecided/tiles/32_med/`
> - **D**：`{SIZE}` = `64x64` → `art_undecided/tiles/64_med/`
> 均 `gpt-image-1`、`quality=medium`、opaque、5×3=15 张/组（共 30）。原图 1024，再按需缩 64。
> **追加 E/F（仅草地，quality=HIGH 试水）**：同 grass prompt，`{SIZE}`=`chunky 32x32`→`32_high/`、`64x64`→`64_high/`，各 3 张。
> **追加 G（2026-06-26）**：`32_high/` 补齐其余 4 地形（road/dirt/water/bridge），同 B 批 prompt + `chunky 32x32` + quality=HIGH，各 3 张 → 全套 32-high。**定为 finals 标准：32-prompt + HIGH + 缩到 64。**

```
grass : 16-bit JRPG pixel-art GRASS terrain tile, top-down orthographic flat view. Green grassland
        with grass-blade clusters, small tufts and a few tiny flowers, several shades of green
        forming natural patches. Designed to read as a {SIZE} pixel-art tile. Crisp hard-edged
        pixels, limited palette, NO anti-aliasing, no blur, no gradients, no outlines. Flat even
        lighting, no shadows, no perspective. Seamless tileable on all four edges. Fills the whole
        frame, no border, no grid lines, no text.
road  : 16-bit JRPG pixel-art DIRT ROAD / packed travel PATH tile, top-down orthographic flat view.
        Light tan / sandy-brown packed road with scattered pebbles and natural soil mottling, a
        well-traveled dirt path. Designed to read as a {SIZE} pixel-art tile. Crisp hard-edged
        pixels, limited tan palette, NO anti-aliasing, no blur, no gradients, no outlines. Flat
        even lighting, no shadows, no perspective. Seamless tileable on all four edges. Fills the
        whole frame, no border, no grid lines, no text.
dirt  : 16-bit JRPG pixel-art BARE DIRT / MUD GROUND tile, top-down orthographic flat view. Natural
        raw earth, darker reddish-brown soil with clumps, small cracks and tone variation, rough
        untended ground (not a built path). Designed to read as a {SIZE} pixel-art tile. Crisp
        hard-edged pixels, limited brown palette, NO anti-aliasing, no blur, no gradients, no
        outlines. Flat even lighting, no shadows, no perspective. Seamless tileable on all four
        edges. Fills the whole frame, no border, no grid lines, no text.
water : 16-bit JRPG pixel-art WATER tile, top-down orthographic flat view. Blue water with rippling
        wave highlights and layered blue tones, lively surface. Designed to read as a {SIZE}
        pixel-art tile. Crisp hard-edged pixels, limited blue palette, NO anti-aliasing, no blur,
        no gradients, no outlines, no foam border. Flat even lighting, no shadows, no perspective.
        MUST tile seamlessly on all four edges, especially top-to-bottom. Fills the whole frame,
        no border, no grid lines, no text.
bridge: 16-bit JRPG pixel-art WOODEN BRIDGE DECK tile for a horizontal (left-right) bridge, top-down
        orthographic flat view. Several VERTICAL wooden planks side by side with vertical plank
        seams, weathered brown wood with grain, knots and nail heads, plus a darker support BEAM
        along the TOP edge and the BOTTOM edge. Designed to read as a {SIZE} pixel-art tile. Crisp
        hard-edged pixels, limited wood-brown palette, NO anti-aliasing, no blur, no gradients, no
        outlines. Flat even lighting, no shadows, no perspective. Seamless tileable LEFT-TO-RIGHT.
        Fills the whole frame, no border, no text.
```

---

## ★ 当前批次 H · 2026-06-27 · sand 海滩/浅滩（草↔水之间的第三材质）

> 用途：海岸线第三地形（沙），夹在草和水之间(见 tile pipeline §8 / dual-grid 思路)。
> 同 32-prompt + `chunky 32x32`，**只出 32**。出 **high×3 → `32_high/sand/`**、**medium×3 → `32_med/sand/`**。
> 要点：**浅 tan、细沙、干净**，比 road(夯土路)更浅更细、比 dirt(红棕裸土)更亮不发红 —— 三者要区分。

```
16-bit JRPG pixel-art SAND / BEACH SHORE terrain tile, top-down orthographic flat view. Pale sandy
tan, mostly soft FINE grain with a few tiny darker speckles and maybe one small pebble, light and
clean - a beach / riverbank sand, LIGHTER and FINER than a dirt road and NOT reddish like bare
soil. Designed to read as a chunky 32x32 pixel-art tile. Crisp hard-edged pixels, limited pale-sand
palette, NO anti-aliasing, no blur, no gradients, no outlines. Flat even lighting, no shadows, no
perspective. Seamless tileable on all four edges. Fills the whole frame, no border, no grid lines,
no text.
```

---

## ★ 批次 I · 2026-06-28 · 「大图切块」实验（big-image → crop tiles）

> 实验:出**大图**再切 64 tile(同源 → 变种一致、匀纹理切块更无缝)。对比 ①加不加 chunky 词 ②切前缩到 1024/512/256。
> 4 张 `gpt-image-1` / **quality=high** / opaque / 1024² → `art_undecided/tiles/_bigcrop/`:
> grass×2(plain / chunky)、road×2(plain / chunky)。后处理:1024直切 / 512缩后切 / 256缩后切,各切 64 + 3×3 看无缝与脆度。

**grass_plain**（不加像素限制）
```
A large top-down view of a lush green grassland ground texture filling the entire frame, seen
straight from above (flat orthographic, no perspective), with natural variation in grass shades,
scattered tufts and small details across the whole field. Even flat daylight, no horizon, no
objects, no characters. Painterly fantasy RPG map ground. Fills the whole frame, no border, no text.
```
**grass_chunky**（加像素限制）= grass_plain + 句尾追加：
```
Rendered as 16-bit PIXEL ART with CHUNKY hard-edged pixels, a limited palette, NO anti-aliasing,
no blur, no gradients.
```
**road_plain**
```
A large top-down view of a packed dirt road / bare earth ground texture filling the entire frame,
seen straight from above (flat orthographic, no perspective), tan and brown soil with scattered
pebbles and natural mottling across the whole field. Even flat daylight, no objects, no characters.
Fills the whole frame, no border, no text.
```
**road_chunky** = road_plain + 同上 chunky 句尾。

---

## 1. 地面 base tile（宽容型，可随机填充 + 脚本无缝化）

> 这类只需「内部纹理好看」，**不需要完美边缘匹配**，脚本会做无缝 + 加变种。每种出 1 张 base + 2~3 张变种即可。

### 1.1 草地 grass（已迭代为 chunky 版，2026-06-16）

```
A single seamless tileable top-down GRASS GROUND TEXTURE for a 16-bit SRPG, filling the ENTIRE
frame edge to edge (this is one repeating ground tile, NOT a landscape scene, NOT a field with
sparse blades). Medium-density grass made of CHUNKY readable pixel clusters (each blade-cluster a
few pixels, like Fire Emblem GBA / Final Fantasy Tactics terrain), 3-4 shades of green forming soft
patches of lighter and darker grass, gentle top-left light, NO large flat empty areas, NO single
sparse blades on emptiness.
[全局后缀]
```
> **踩坑**：旧版「subtle blade detail」→ GPT 出**太碎的噪点地毯**、Gemini 出**稀疏草叶的风景画**。改成 **chunky pixel clusters / 3-4 shades / soft patches + 明确 "one tile NOT a landscape" + "NO sparse blades on emptiness"** 后，GPT 出图达标。
> **另**：程序化无缝版见 `scripts/tiles/gen_base_tiles.py`（灰盒用，保证无缝）。

### 1.2 泥土 / 裸地 dirt

```
A single seamless top-down dirt/soil ground tile, packed earth with small pebbles and
subtle cracks, warm brown limited palette, gentle top-left lighting, tileable on all sides.
[全局后缀]
```

### 1.3 道路 / 石板路 road / cobblestone

```
A single seamless top-down cobblestone path tile, irregular grey-brown stones with mortar gaps,
worn smooth, slight top-left highlight on each stone, tileable, suitable as a village road.
[全局后缀]
```

### 1.4 水面 water（内部，岸边另出，见 §2）

```
A single seamless top-down shallow water tile, calm blue-teal surface with faint ripple
highlights and subtle depth shading, gentle reflective glints, no shoreline, tileable.
[全局后缀]
```

### 1.5 木桥面 bridge plank

```
A single top-down wooden bridge plank tile, horizontal weathered timber boards with nail heads
and grain detail, warm brown, top-left lighting, designed to tile along its length.
[全局后缀]
```

### 1.6 农田 field（村庄关用）

```
A single seamless top-down farmland tile, plowed soil in even furrow rows with small green
sprouts, earthy palette, top-left light, tileable as a crop field.
[全局后缀]
```

---

## 2. 边界 / 过渡 tile（边界型，必须方向集 → 喂 Unity Rule Tile autotile）

> ⚠️ 这是整条管线**最难**的一环。**优先方案：脚本用「草纹理 + 水纹理 + mask」自动合成边角集**（见 spec §7.4）。
> 下面 prompt 仅用于「让 AI 出参考边角」或脚本兜底质量不够时手挑。**出图时务必明确「过渡方向」**。

### 2.1 草→水 直边（顶边是草，底边是水）

```
A single 64x64 top-down transition tile: the upper half is grass meeting the lower half of
shallow water, with a natural muddy/sandy shoreline edge between them, small wet pebbles at the
waterline, top-left light. Grass on TOP edge, water on BOTTOM edge. Tileable horizontally.
[全局后缀]
```

> 同理派生 8 向：上/下/左/右 四条直边 + 四个外角（如「左上是水、其余是草」）+ 四个内角。**出图时只改方位描述**（"water on LEFT edge", "water in the TOP-LEFT corner only" 等）。

### 2.2 草→路 路沿

```
A single 64x64 top-down tile where a cobblestone path meets grass along one edge, soft worn
border where stones give way to grass tufts, top-left light. Path on BOTTOM, grass on TOP.
[全局后缀]
```

### 2.3 桥头（桥面接岸）

```
A single 64x64 top-down tile of a wooden bridge end meeting a grassy/dirt bank, last plank row
with a short step down to ground, top-left light. Bridge on one side, bank on the other.
[全局后缀]
```

> **挑图标准**：边界 tile 看「过渡是否落在 tile 边缘的正确位置」，而非「单张好不好看」。落错位置无法 autotile，直接弃。

---

## 3. 物件 sprite（占 N×N 格，独立摆放，YSort 遮挡，不烤进地面）

> 物件**不无缝**，是独立 sprite，像角色一样复用。背景出**纯品红 #FF00FF 或透明**，脚本抠图。
> **关键**：同一关物件必须**同光照、同调色板、同视角**，所以**一次出一组**比单出更稳。

### 3.1 村屋 house（约 2×2 ~ 3×3 格）

```
A single top-down pixel-art village house sprite for a tactics RPG, thatched or tiled roof seen
slightly from above (top-down with just enough roof angle to read as a building), stone/wood
walls, small door and windows, warm cozy palette, top-left light casting a short soft shadow to
the lower-right. Isolated object on a flat magenta (#FF00FF) background, no ground texture.
Style: 16-bit SRPG building. No text, no watermark.
```

### 3.2 树 tree（1×1 ~ 2×2 格，作掩体/阻挡）

```
A single top-down pixel-art tree sprite, round leafy canopy viewed from above with a hint of
trunk, layered green clusters with top-left highlights and darker underside, short shadow to the
lower-right. Isolated on flat magenta (#FF00FF) background. 16-bit SRPG style. No text.
```

### 3.3 一组物件（推荐：一次出整套保证一致）

```
A clean sprite sheet of top-down pixel-art village props in ONE consistent 16-bit SRPG style,
shared limited palette and top-left lighting: a well, a wooden fence segment, a stack of crates,
a barrel, a small rock, a haystack, a signpost, a market stall. Each object isolated with spacing
on a flat magenta (#FF00FF) background, arranged in a neat grid, no overlap, no text, no watermark.
```

> 出 sheet 后脚本按格切片即可，**风格天然统一**。

---

## 4. 变种生成（Flux / LoRA，降低重复感）

> base tile 选定后，用 Flux img2img 低 denoise 生成同款变种（仅宽容型 tile）。

```
[同 §1 对应 base 的描述]
Generate 3 subtle variations of this exact grass tile: same palette, same lighting, same scale,
only rearrange the small highlights/tufts so they don't look identical when tiled. Keep it
seamless and top-down.
```

> Flux 提示：**CFG=1 下负向提示被忽略**，所有「不要 X」改写成「it is Y」正向陈述（见 §5）。出图 ~1MP（1024²）甜点，避免 1440+ 崩图。

---

## 5. Flux 专用注意（来自实验日志）

- **负向提示无效**：Flux guidance distillation 在 CFG=1 下忽略 negative prompt。把排除项写成正向：
  - ❌ `no isometric` → ✅ `strict flat top-down orthographic view, camera pointing straight down`
  - ❌ `no blur` → ✅ `crisp sharp pixel edges, clean hard outlines`
- **LoRA 会引入倾斜**：工作流里的 Tilt-Shift / Cozy Tiltshift LoRA 在低 ControlNet 强度时会让画面变等距/倾斜。出**正俯视 tile** 时调低这些 LoRA 权重或走 GPT/Gemini。
- **尺寸**：1024×1024 出图，再 4x-UltraSharp 放大后缩到目标分辨率。

---

## 6. 出图后机械处理（脚本，玩家不手绘）

| 步骤 | 工具 | 备注 |
|---|---|---|
| 切片（sheet → 单 tile/物件） | Python / Unity Sprite Editor | 64px 网格自动切 |
| 无缝化（宽容型 tile） | Python（offset + 边缘镜像/羽化融合） | 玩家只挑，0 手绘 |
| 边角集自动合成 | Python（两纹理 + mask 混合 + 描边） | 喂 Unity Rule Tile |
| 抠图（物件去品红底） | Python（color key #FF00FF → alpha） | |
| 导入设置（Point/None/Clamp/PPU=64） | `PixelArtImportPostprocessor.cs` | 已自动 |

---

## 7. 挑图 checklist（玩家把关用）

- [ ] **正俯视**？有没有偷偷变等距/带透视？
- [ ] 光照方向是不是**统一左上**？
- [ ] 调色板和同关其它素材**一致**吗？
- [ ] 宽容型 tile：内部纹理够不够看、**重复填充会不会出明显接缝/规律**？
- [ ] 边界 tile：**过渡是否落在 tile 边缘正确位置**（能不能 autotile）？
- [ ] 物件：背景是不是干净品红/透明、**阴影方向对不对**、放大后边缘锐不锐？
- [ ] 有没有混进**文字/水印/签名**？
```