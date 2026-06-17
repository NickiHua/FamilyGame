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