# 地图制作 Pipeline · 《幻世纪》FantacyCentry

> **这是什么**：Stage1 这类 SRPG 战棋地图从「概念图」到「可玩 JSON」再到「AI 手绘整图」的标准工序。
>
> **核心原则**：地图逻辑永远由 `stage1_map.json` / grid 决定；AI 只做视觉重绘，不决定 walkability、不改变格子语义。
>
> **当前最优结论**：整图重绘用 **Seedream 5.0 Pro**。GPT Image 2.0 更适合生成概念图和边缘 transition sheet，不适合作为最终整图保 layout 模型。

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