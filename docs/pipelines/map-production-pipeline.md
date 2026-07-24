# 地图制作 Pipeline · 《幻世纪》FantacyCentry

> **这是什么**：Stage1 这类 SRPG 战棋地图从「概念图」到「可玩 JSON」再到「AI 手绘整图」的标准工序。
>
> **核心原则**：地图逻辑永远由 `stage1_map.json` / grid 决定；AI 只做视觉重绘，不决定 walkability、不改变格子语义。
>
> **当前最优结论**：整图重绘用 **Seedream 5.0 Pro**。GPT Image 2.0 更适合生成概念图和边缘 transition sheet，不适合作为最终整图保 layout 模型。
>
> **2026-07 更新**：主流程已从「dual-grid + edge sheet」演进到 **「marker 布局图 + 房子参考图 → Seedream 重绘 → 单张 baked HD 图（Build Battle Scene V2）」**，并新增**水面流动 shader**。§1–§5 是旧 dual-grid 流程（仍有效，作背景参考），**§6 起是当前主线**。§9 是未来设想（尚未实施）。

---

## 0. 一句话链路

```text
GPT / Gemini 画概念图，多张选 1
        ↓
用户在 Unity Stage1 Tilemap 里画可玩地图
        ↓
Export Stage1 JSON -> Assets/Art/Maps/stage1_map.json
        ↓
GPT 看 tilemap / JSON 布局，辅助微调结构更舒服
        ↓
根据 JSON 渲染 dual-grid 视觉图 / segmentation ref
        ↓
GPT / Gemini 生成当前地图接壤关系的 edge transition sheet
        ↓
Seedream 5.0 Pro：ref1=dual-grid segmentation，ref2=edge sheet
        ↓
输出同尺寸完整地图图（当前 1920x1920）
        ↓
棋盘格 / GIF / 红青边界验证 layout
```

---

## 1. 各阶段职责

### 1.1 GPT 画概念图，多张选 1

目的不是直接生产可玩地图，而是确定：

- 地图主题和气质。
- 河流 / 道路 / 村庄 / 森林 / 田地的大致关系。
- 美术目标是正俯视 SRPG 地图，而不是 isometric / 写实卫星图。

产物通常放在：

```text
art_undecided/maps/
```

注意：概念图只作为设计参考，不进入最终可玩逻辑。不要试图从概念图直接当 battle map 使用。

### 1.2 用户画 Tilemap，导出 JSON

用户在 Unity 里编辑：

```text
Assets/Scenes/SampleBattle.unity
  Grid
    Stage1
```

编辑时建议状态：

```text
Stage1 Tilemap Renderer: ON
DualGrid: OFF
concept_village: OFF
ScatteredProps: OFF（挡视线时）
```

画完以后选中 `Stage1`，执行：

```text
Tools > Map > Export Stage1 JSON
```

输出：

```text
Assets/Art/Maps/stage1_map.json
```

这个 JSON 是地图语义的源头，包含：

```text
G = Grass
R = Road
I = Dirt
W = Water
D = Bridge
S = Sand
B = Building / blocked
```

当前原则：

```text
JSON 是唯一真相。
JSON 里没有 D，就不应该自动生成桥。
```

因此 `MapGrid.inferBridgeCells` 默认必须为 `false`。

### 1.3 GPT 辅助微调 Tilemap 结构

Tilemap 初版出来后，可以把 raw 或 dual-grid dump 图给 GPT / 助手看，让它从设计角度提出：

- 路径是否太直。
- 河流是否太机械。
- 泥地是否太突兀。
- 村庄 / 农田 / 道路是否关系自然。
- 战棋可玩区域是否过于拥挤或空旷。

这一步只提供建议，最终还是用户在 Tile Palette 里改 `Stage1`。

改完再次导出 JSON。

### 1.4 从 JSON 渲染 dual-grid / segmentation 图

AI 不适合直接读 JSON。需要先把 JSON 变成视觉清晰的参考图。

当前主参考图：

```text
art/maps/map_raw/stage1_tilemap_dualgrid_1920.png
```

生成方式：

```text
Assets/Art/Maps/stage1_map.json
-> MapGrid
-> DualGridBuilder
-> MapImageDumper.DumpStage1DualGridFromJsonImage
-> 1920x1920 PNG
```

这个图的作用类似 segmentation / layout ref：

- 让 AI 清楚看见河流、道路、泥地、草地范围。
- 比 raw tilemap 边缘更自然，AI 更容易理解地形关系。
- 仍然严格来自 JSON，不来自手拖 scene 里的生成对象。

不要使用会先 `MapExporter.Export()` 的 dump 流程来生成这个参考图，否则可能把 scene 里的旧 Tilemap 反向覆盖最新 JSON。

### 1.5 GPT 出当前地图接壤 edge sheet

整图重绘不能只靠 layout ref，还需要告诉模型边缘应该怎么画。

当前推荐第二参考图：

```text
art/maps/map_raw/edge_transition_less_details.png
```

内容是当前地图需要的几类接壤关系：

- 草地 ↔ 水
- 草地 ↔ 道路
- 道路 ↔ 泥地
- 道路 ↔ 水

要求：

- 柔和日式手绘 SRPG 地图风格。
- 低到中等对比度。
- 不要太碎、不要花草地毯、不要高对比白边。
- 用来表达边缘材质语言，不要表达地图构图。

GPT Image / Gemini 在这一步很好用，因为 edge sheet 不要求严格地图 layout，只要求风格和材质。

### 1.6 Seedream 5.0 Pro 整图重绘

最终整图重绘用 Seedream 5.0 Pro。

推荐调用：

```powershell
$prompt = Get-Content art_undecided\maps\stage1_seedream_pro_prompt_cn_v6_full_multiref.txt -Raw

.\.venv\Scripts\python.exe scripts\volcengine_seedream_map.py `
  --model doubao-seedream-5-0-pro-260628 `
  --size 1920x1920 `
  --output-format png `
  --response-format url `
  --ref art\maps\map_raw\stage1_tilemap_dualgrid_1920.png `
  --ref art\maps\map_raw\edge_transition_less_details.png `
  --prompt $prompt `
  --out art_undecided\maps\sdmap\stage1_seedream5pro_stage1.png
```

为什么必须用 `response_format=url`：

```text
1920 PNG 的 b64_json 响应太大，曾经触发 IncompleteRead。
URL 返回只返回小 JSON，脚本再下载图片，更稳。
```

### 1.7 layout 验证

AI 出图以后必须验证，不要只看好不好看。

推荐三种验证图：

```text
1. 棋盘格 old/new：240px 一格交替显示。
2. 闪烁 GIF：old / new 交替闪。
3. 红青边界图：old edges = red，new edges = cyan。
```

判断标准：

- 河流主走向是否一致。
- 道路是否改道。
- 泥地区块是否漂移或扩大。
- 水岸柔化是否只发生在边缘窄范围。
- 是否新增了桥、树、房子、石头、角色、网格线、文字。

经验：

```text
棋盘格 + GIF 最适合看整体 layout。
红青边界最适合看边缘漂移。
diff heatmap 会把纹理变化也算进去，不适合作为唯一判断依据。
```

---

## 2. 文件位置约定

### 2.1 源文件

```text
Assets/Art/Maps/stage1_map.json
```

这是地图语义源文件，应该提交。

### 2.2 参考图

```text
art/maps/map_raw/stage1_tilemap_raw_1920.png
art/maps/map_raw/stage1_tilemap_dualgrid_1920.png
art/maps/map_raw/edge_transition_less_details.png
```

`stage1_tilemap_dualgrid_1920.png` 是给 Seedream 的第一参考图。

### 2.3 Prompt

```text
docs/prompts/map-prompts.md
art_undecided/maps/stage1_seedream_pro_prompt_cn_v6_full_multiref.txt
```

正式沉淀在 `docs/prompts/map-prompts.md`。实验时脚本直接读取 `art_undecided/...txt` 也可以，但两边要同步。

### 2.4 Seedream 输出

```text
art_undecided/maps/sdmap/
```

命名建议包含：

```text
stage1_seedream5pro_<map_version>_<edge_ref>_<size>_<timestamp>.png
```

### 2.5 Unity scene

不要把 `SampleBattle.unity` 里的生成态当源文件。

`SampleBattle.unity` 容易因为以下对象产生几万行 diff：

```text
DualGrid
ScatteredProps
BattleRunner
BattleCanvas
MapGrid
tree_* / stone_* generated props
```

如果 `stage1_map.json` 已经是最新，scene 里这些生成态 diff 可以 revert。

---

## 3. 模型选择结论

### 3.1 GPT Image 2.0

适合：

- 概念图。
- 边缘 transition sheet。
- 风格探索。

不适合：

- 要求严格保留 SRPG tile layout 的整图重绘。

原因：

- 画面完成度高，但会艺术化边界。
- `high` 质量更漂亮，但 layout 漂移也更明显。

### 3.2 Seedream 5.0 Lite

不推荐做最终整图。

问题：

- 曾经把窄河误解成大水域。
- 边缘容易有白边 / 亮边。
- 对结构的稳定性不如 Pro。

### 3.3 Seedream 5.0 Pro

推荐做最终整图。

优点：

- 多参考图下结构稳定。
- 能较好遵守第一参考图的河流、道路、泥地区块位置。
- 能利用第二参考图改善水岸和地形接壤语言。

当前最佳组合：

```text
model: doubao-seedream-5-0-pro-260628
ref1: art/maps/map_raw/stage1_tilemap_dualgrid_1920.png
ref2: art/maps/map_raw/edge_transition_less_details.png
prompt: docs/prompts/map-prompts.md §1.2
size: 1920x1920
output_format: png
response_format: url
watermark: false
```

---

## 4. 操作 checklist

地图大改后照这个顺序走：

- [ ] 用户在 Unity `Stage1` Tilemap 中改地图。
- [ ] 选中 `Stage1`，执行 `Tools > Map > Export Stage1 JSON`。
- [ ] 确认 `Assets/Art/Maps/stage1_map.json` 是最新。
- [ ] 用 JSON-only dump 生成 `stage1_tilemap_dualgrid_1920.png`。
- [ ] 确认没有自动桥：JSON 里没 `D` 就不能有桥。
- [ ] 用 `edge_transition_less_details.png` 作为第二参考跑 Seedream Pro。
- [ ] 使用 `response_format=url`。
- [ ] 生成后做棋盘格 / GIF / 红青边界验证。
- [ ] 如果 layout 过关，再考虑导入 Unity 做视觉层。
- [ ] 不提交 `SampleBattle.unity` 的生成态大 diff。

---

## 5. 当前风险和注意事项

1. **JSON 未保存 / 未导出时不要跑 AI。**
   Unity batch 和脚本只读磁盘文件；VS Code 缓冲区未保存会导致旧 JSON 被使用。

2. **不要让 MapGrid 自动推桥。**
   `inferBridgeCells` 默认必须为 false。桥必须在 JSON 里显式写 `D`。

3. **不要直接把 Seedream 图当逻辑图。**
   Seedream 图只是视觉结果，walkable 仍由 JSON 决定。

4. **不要用 `b64_json` 跑 1920 PNG。**
   统一用 URL 返回格式。

5. **概念图不是最终地图。**
   GPT 概念图只帮用户决定结构和风格，真正可玩地图必须由用户画 tilemap 并导出 JSON。

一句话总结：

```text
人设计地图，JSON 固化语义，dual-grid 转成 AI 可读布局，edge sheet 提供接壤语言，Seedream Pro 做最终手绘化。
```

---

## 6. 【当前主线】Marker 布局 → Seedream 重绘 → 单张 baked HD 图（Build Battle Scene V2）

> 详细实验记录见 `docs/developing_process/2026-07-22_process.md`。这里只沉淀「怎么做」。

### 6.1 为什么换掉 dual-grid + object sprite

老做法把**真的 object sprite**（房子/树…）摆到地图上，痛点：
- 房子 sprite 里**烘死了门口的路桩**，位置固定，多半不在格子中线。
- 想「门对齐 road」就得平移房子，一平移**房子就不占整格**。
- 本质矛盾：**刚性 sprite 的门**没法同时满足「footprint 贴整格」+「门对齐 road」。
- 且 PixelLab 生成的 object 和 HD 地图**融合不佳**。

### 6.2 破解思路：marker tile

不摆刚性 sprite，改成在网格上画「纯色带字母的 marker 方块」：
- **footprint 画整格 → 天生锁网格**（collider 仍从 JSON 走）。
- **门画在哪、怎么接路 → 交给模型现画**（柔性门，自动长到路那侧）。

marker 配色（`scripts/tiles/gen_marker_tiles.py`）：

| 对象 | 颜色 | 字母 |
|---|---|---|
| 房子 house | 深棕 (74,47,27) | H |
| 树 tree | 深绿 (28,74,38) | T |
| 石头 stone | 灰 (130,130,130) | S |
| 桥 bridge | 棕 (150,95,50) | B |

Unity 里用**带字母**那套画（好核对）；渲染出图用**纯色块 + 大字母**。

### 6.3 链路

```text
用户在 Unity 的 marker Tilemap 上画物件（H/T/S/B）
        ↓  Tools > Map > Export Marker Map
Assets/Art/Maps/stage1_marker_map.json（render-only，不碰真实 map JSON）
        ↓  scripts/render_marker_map.py
art/experiments/stage1_marker_render_1920.png（平铺地形 + 纯色 marker 块 + 大字母）
        ↓  Seedream 5.0 Pro：ref1=marker render，ref2=房子参考图，prompt=only-house
art/experiments/stage1_onlyhouse*_v*.png（1920²）
        ↓  W+H 红格 collider 叠图验证（见 6.5）
选定 → Copy 到 Assets/Art/Maps/stage1_hd.png
        ↓  scripts/water/gen_water_mask_flowmap.py（重生成水 mask/flowmap）
Tools > FantacyCentry > Build Battle Scene V2（MapGrid + 一张 HD sprite + 水材质）
```

### 6.4 房子参考图（ref2）的关键作用

- Seedream **无法**从纯文字生成正确「正俯视 + 横向」房子（文字容易出 45° isometric）。
- 必须喂一张**已经是正俯视横向**的房子参考图，模型才会跟着这个视角画全图的 H。
- 参考图切法：把一张 4 宫格房子图切成单栋/多栋（`sample_house_5/6/7/8`=左右上下半，`sample_house_9`=三栋并排），当 ref2。
- prompt：`art/experiments/stage1_only_house_ref_prompt.txt`——强调「ref2 只提供房子视角/风格，其它元素按文字自主画」「每栋 H 严格填满方格不出格」「门对齐相邻黄土路」「T 是统一矮树不要画成大森林」。

### 6.5 collider 校验（每张 AI 输出都做）

读 `stage1_marker_map.json`，在 W（水）+ H（房子）阻挡格上叠**红色半透明**（alpha 105）+ 淡黑网格，另存 `*_check.png`。看房子/水是否落在红格内、门有没有接上路。

### 6.6 Build Battle Scene V2 架构

- 只两层：**MapGrid（逻辑）+ 一张 HD sprite（视觉，sortingOrder -5000）**，不再有 DualGrid / object sprite（tilemap renderer 全 disable）。
- 1920px sprite @ PPU64 = 30 世界单位 = 30×30 grid，居中在 `grid.CenterWorld`。
- V1/V2 公共接线抽成 `WireBattle(grid)`（overlay/runner/stage/audio/input/canvas/camera）。
- `BattleSceneBuilder.cs` 里 `EnsureWaterMaterial()` 自动挂水面材质（见 §7）。

---

## 7. 水面流动 shader（flowmap water）

> 详见 `docs/developing_process/2026-07-22_process.md` §11。方案 = **A（单图 + 水 mask）+ 3（flowmap 相位混合）**。

### 7.1 关键前提

物件/影子都 bake 进一张平图后，仍能给水面加流动——只要 shader 知道**哪些像素是水**。
**不能**用 grid 的 W 格当 mask（AI 重绘把河岸挪柔化过，会错位），必须**从 HD 图本身分割**。

### 7.2 数据生成（`scripts/water/gen_water_mask_flowmap.py`，任意分辨率通用）

从 `stage1_hd.png` 一次产出、写在图旁边：
- `stage1_hd_watermask.png`——蓝色色键分割 + 连通域去杂 + 填洞 + 羽化（water=白）。
- `stage1_hd_flowmap.png`——**结构张量**求河道走向（沿河=minor 特征向量），强制 Y 朝下→水从上往下流，RG 编码方向，水区外中性 0.5。

### 7.3 Shader（`Assets/Art/Shaders/WaterFlow.shader`，URP sprite）

- **flowmap 相位混合**：两个半周期错开样本（`phase0=frac(t)`、`phase1=frac(t+0.5)`）三角波交叉淡入 → **滚动永不露接缝**，即使噪声本身不可平铺；水顺流向流。
- 程序化 value noise 当波纹（无贴图、无限、seam 被相位混合藏掉）。
- 轻微 UV 折射 + 细窄滚动高光（粼光）。只作用于 mask 水区，房子/影子/草地不动。
- **坑**：`UnityPerMaterial` 里放 `_MainTex_ST` 会触发「2D SRP Batcher 不支持 _TexelSize/_ST」并禁用批处理。地图是整张 sprite、UV 就是 0–1，**删掉 `_MainTex_ST`、用原始 `IN.uv`**。

### 7.4 调参：治「肥皂水」

第一版动静太大像肥皂油花。**主因是 Refraction**（UV 折射把蓝色搅成大块明暗带）；`Ripple Scale` 在折射归零后几乎无感。真正救回来的是**高光算法重写**（大块低频 crest → 细窄流动亮线）。稳妥默认值：

```text
Flow Speed 0.05 | Flow Advection 0.22 | Ripple Scale 30 | Ripple Height 0.5
Refraction 0.0015 | Sparkle Strength 0.14 | Sparkle Sharpness 14
```

> 流向存在 flowmap 贴图里（不是滑杆），Inspector 只能调速度/强度，改不了方向；要反向/分段横流得改脚本重生成 flowmap。

### 7.5 数据贴图导入设置

`BattleSceneBuilder.ConfigureDataTexture()` 自动把 mask/flowmap 设为 **linear / clamp / 无压缩 / 无 mip**（保方向和边缘）。

---

## 8. SD / GPT 使用经验（补充 §3）

### 8.1 Seedream 5.0 Pro（保 layout 主力）

- **强项**：多参考图下 layout 极稳；marker 布局图能被严格遵守（格子位置/大小/朝向不变）。
- **无法**从纯文字生成正确正俯视物件（房子会出 45° isometric）→ 必须给正俯视参考图定视角。
- **会跟着参考图的朝向画**：参考图横向，全图房子就横向。
- **单张过强的参考图 → 克隆**：只给 1 栋房子 ref，模型会把 3 栋画成一模一样；给多栋 ref + 明确「可有变化」才有区分。
- Chinese prompt 效果好；用 `--prompt-file` 避免 CJK shell 转义。
- **必须 `--response-format url`**：b64 1920² ~11MB 会 IncompleteRead。

### 8.2 GPT Image 2.0（概念/风格，不保 layout）

- 支持任意尺寸（长边 ≤3840、双边 16 倍数、比例 ≤3:1；1920² 合法但 >2K 实验性；**无透明底**）。
- 保 layout **漂移严重、画面更乱**，即使 HIGH 也不适合做最终整图。
- 定位：概念图 / 风格探索 / edge transition sheet。

### 8.3 本 session 测试地图产物

- marker tile：`Assets/Art/Tiles/markers/*.png`（8 张）
- 布局渲染：`art/experiments/stage1_marker_render_1920.png`
- Seedream 迭代：`stage1_onlyhouse{5,6,7,9}_v*`（+ `_check` collider 校验）
- **定稿**：`stage1_onlyhouse9_v5.png` → `Assets/Art/Maps/stage1_hd.png`
- 水面：`stage1_hd_watermask.png`、`stage1_hd_flowmap.png`、`Assets/Art/Shaders/WaterFlow.shader`、`Assets/Art/Materials/WaterFlow.mat`

---

## 9. 未来设想（尚未实施 · 只是方向，暂无精力做）

> 记录 2026-07-24 的讨论，等有精力再落地。核心思路：**baked 静态地面 + 上层「Props/FX 层」**。

### 9.1 分离线：什么 bake、什么做成对象

- **该 bake**（纯静态、容忍网格）：地形、道路、水底、农田、**房子**（门对齐已解决）。
- **该做成对象**（满足任一）：① 需交互/拾取 ② 需逐个单独动 ③ 需每个精确统一。

### 9.2 树对象化（根治「树偏大/不单独」）

- 根因：AI 把整片 T 区画成连成一坨的树丛，文字压不死。
- 方案：Seedream 画几个**统一小树**变体（抠图）→ T 格摆独立 sprite（Props 层）→ 每棵配阴影 + **顶点风摇（根锚定、冠摆动）**。
- 前提：baked 地面**不再画树**（renderer/prompt 把 T 当空草地），否则重影。石头同理。

### 9.3 可交互摆件（稻草人 = 练剑对象 + 秘密宝箱）

- 交互/可拾取物**必须是独立 GameObject**（自带 collider/交互，在 MapGrid 登记阻挡/可交互），不能 bake。
- 阴影同树共用。

### 9.4 阴影方案（树/摆件通用）

1. **Blob 阴影**：脚下软椭圆暗斑（Multiply/Alpha）。最便宜万能。
2. **投影剪影阴影**：复制 sprite → 压扁 + 按光向 skew + 染黑降透明 + 模糊。更有方向感，**对齐 baked 图的光向**。

### 9.5 让地图「活起来」（上层 FX，不动 baked 图）

- **烟囱冒烟**：每烟囱一个 2D 粒子系统（软烟上升+飘+淡出）。廉价高回报。
- **水车**：sprite 脚本 `transform.Rotate` 或翻页帧 + 落水小水花粒子。
- **顺手加**：云影缓慢掠过全图（电影感、近零成本）、萤火虫/蝴蝶粒子、偶尔飞鸟、河面泡沫/鱼跃涟漪、花草摇曳、火把闪烁。

### 9.6 分辨率与缩放策略（结论）

- 缩放锁**整数三档**：**1X**（30 格/屏，64px/格，1:1）｜**2X**（15 格，128px/格）｜**3X**（10 格，192px/格）。
- 整数缩放的好处：**真像素小人**正好被放大 ×1/×2/×3 → 像素永远锐利（连续无级缩放会非整数拉伸导致抖动/糊）。
- 采样：像素小人 **Point**，HD 背景 **Bilinear**。
- 分辨率：**1920² 足够 1X–2X**；3X 会略软。**若 3X 常用**再**原生出 3840²**（不是 ESRGAN 放大——放大会磨掉水彩笔触）。mask/flowmap 脚本任意分辨率零成本跟上。
- **不做全图 4K/ESRGAN**：显存贵（7680² RGBA ~236MB）、对干净 AI 手绘增益小还可能塑料感。