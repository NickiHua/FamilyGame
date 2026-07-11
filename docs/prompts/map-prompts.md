# 地图 Prompt · 《幻世纪》FantacyCentry

> **用途**：保存 Stage1 地图整图重绘用的 prompt。当前主路线是用 Unity 从 `stage1_map.json` 渲染出的 dual-grid 视觉图锁布局，再用边缘 sheet 锁地形接壤风格，交给 Seedream 5.0 Pro 重绘整张 1920 地图。
>
> **当前结论**：整图重绘用 **Seedream 5.0 Pro**，不要用 GPT Image 2.0 做最终整图。GPT Image / Gemini 更适合生成边缘 transition sheet。

---

## 1. Stage1 Seedream Pro 整图重绘 Prompt

### 1.1 参考图约定

当前 Stage1 整图重绘使用两张参考图：

```text
第一参考图（严格布局 / segmentation / 地形语义）：
art/maps/map_raw/stage1_tilemap_dualgrid_1920.png

第二参考图（边缘材质 / 接壤语言 / 柔和程度）：
art/maps/map_raw/edge_transition_less_details.png
```

第一参考图由 Unity 根据当前地图 JSON 生成：

```text
Assets/Art/Maps/stage1_map.json
-> MapGrid
-> DualGridBuilder
-> art/maps/map_raw/stage1_tilemap_dualgrid_1920.png
```

因此 **第一参考图只负责锁定地形布局**：河流、道路、草地、泥地、地图边界、正俯视比例。第二参考图只负责锁定边缘风格，不允许影响地图构图。

生成参数建议：

```text
model: doubao-seedream-5-0-pro-260628
size: 1920x1920
output_format: png
response_format: url
watermark: false
```

注意：1920 PNG 不建议用 `b64_json` 返回，响应体太大，曾经触发 `http.client.IncompleteRead`。统一用 `response_format=url`，让脚本下载图片。

### 1.2 Prompt 正文

```text
请以第一张参考图作为严格的主布局来源，生成一张完整的正俯视 SRPG 战棋地图地形图。第一张参考图中的河流走向、道路位置、草地范围、泥土范围、整体比例、地图边界和正俯视镜头必须保持一致。不要移动、旋转、缩放、增删河流、道路或主要地形块，不要改变可游玩地图的格子语义。

第一张参考图是地图结构参考，不是风格上限。请保留它的地形分布和轮廓关系，但把规则的 tilemap / dual-grid 地形边缘重绘成更自然统一的日式手绘 SRPG 地图质感。整体仍然要像一张完整可用的战棋地图地表图，而不是概念画、风景画或参考图拼贴。

允许对地形视觉边缘做很小幅度的自然化处理：水陆边缘、草地与道路边缘、道路与泥地边缘可以在原边界附近有轻微不规则起伏、柔和侵入和手绘过渡，幅度控制在很窄范围内，只用于打破过于规则的 dual-grid 轮廓。不要让河流明显变宽或变窄，不要让道路改道，不要让任何地形块整体漂移。

第二张参考图只用于参考地形边缘的材质语言、柔和程度、色彩关系和细节密度。请参考其中的自然水岸、浅色岸边、低饱和沙滩或浅泥滩、湿润土色、碎草、草根、小石子、沙砾、道路边缘颗粒感和柔和渐变。不要参考第二张图的构图、地形形状、视角、分格排版或具体物体。不要把第二张参考图画成 sheet，也不要把它的局部样例直接复制到地图上。

水陆交界处是重点。请把第一张参考图中规则的硬河岸改成更自然的手绘河岸：水边可以有柔和的浅泥滩或窄沙滩，但沙滩颜色要压低亮度和饱和度，不要纯白，不要亮黄色，不要像海滩白边。沙滩 / 浅泥滩应从水边自然过渡到草地，边缘断续、柔和、有少量碎草、草根、小石子和沙砾，但不能形成一整圈高对比描边。

水面要自然安静。靠近岸边应有浅蓝、青蓝和透明感变化，河心略深；波纹顺着河流方向连续流动，深浅变化柔和。不要让水面过亮，不要电光感，不要现代海浪特效，不要密集重复条纹，不要把河流画成海面。

草地需要更自然，但整体安静统一。可以加入大面积柔和明暗变化、轻微整体阴影、低饱和色块和细微草纹，让草地不再像单调平铺 tile；但不要密集噪声，不要花草地毯，不要过强碎斑，不要让草地抢过道路和水面。草地颜色要和道路、水面、泥地处在同一个柔和手绘风格里。

道路与草地、道路与泥地区域也要自然过渡。道路边缘可以被草地轻微侵入，有柔和的泥土颗粒、浅色磨损和不规则边界；道路和泥地之间也要有细腻的颜色过渡，不要硬切成直线。必须保持道路原来的位置和大致宽度，不要改道，不要变成石路、砖路、铺装路或现代道路。

泥地区域应保持第一张参考图里的位置和范围，颜色比道路更深、更粗糙，但不要过脏、过黑或高对比。泥地边缘可以和草地、道路有柔和过渡，但不要扩大成新的地形块。

整体风格要求：柔和的日式手绘 SRPG 地图地表风格，正俯视，低到中等对比度，颜色自然统一，边缘柔和但地形关系清晰。不要像真实卫星图，不要像照片，不要像 3D 渲染，不要像欧美写实地图，不要强描边，不要过度锐化，不要过度细节化。

不要加入任何树、房子、桥、石头堆、角色、怪物、道具、装饰物、UI、网格线、文字、标记、图标、水印、边框或签名。只输出完整方形地形图，只包含地面和水面。
```

---

## 2. 调用示例

```powershell
$prompt = Get-Content docs\prompts\map-prompts.md -Raw

# 实际调用时不要直接把整篇 markdown 当 prompt；复制 §1.2 的 prompt 正文，
# 或使用 art_undecided/maps/stage1_seedream_pro_prompt_cn_v6_full_multiref.txt。
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

推荐实际 prompt 源文件：

```text
art_undecided/maps/stage1_seedream_pro_prompt_cn_v6_full_multiref.txt
```

如果修改了正式 prompt，记得同步更新本文件。

---

## 3. 使用注意

- 先确认 `stage1_map.json` 是最新的地图语义。
- 不要从 Unity scene 里的旧 Tilemap 反向覆盖 JSON。
- 如果只想根据 JSON 生成主参考图，使用 `MapImageDumper.DumpStage1DualGridFromJsonImage`。
- `MapGrid.inferBridgeCells` 默认必须保持关闭；JSON 里没有 `D` 就不应自动生成桥。
- Seedream 输出后必须做 layout 验证：棋盘格、闪烁 GIF、红青边界图。
- `SampleBattle.unity` 里的 `DualGrid` / `ScatteredProps` / battle objects 是生成态，不要因为预览而提交巨大 scene diff。