# 立绘 / 头像 资产 Pipeline · 《幻世纪》FantacyCentry

> **这是什么**：把「一句 prompt」变成「Unity 里可用的角色立绘 / 表情胸像」的标准工序（SOP）。
> **适用范围**：**角色立绘（全身 tachie）+ 头像胸像（不同表情）+ 角色概念设定图**。
> **不适用**：UI / HUD 装饰件（面板金框、横幅、按钮、图标）→ 走 [`ui-asset-pipeline.md`](./ui-asset-pipeline.md)（硬边几何，抠图方式完全不同）。
> **配套**：prompt 源在 [`docs/prompts/portrait-prompts.md`](../prompts/portrait-prompts.md)。
>
> **开新 session 只需读这一篇**：照下面的目录约定和工序走即可。

---

## 0. 一句话链路

```
docs/prompts/portrait-prompts.md   ← prompt 源（公用风格 + 每角色概念 + 立绘/胸像子 prompt）
   │  GPT-Image API  ⚠️ 收费，调用前必须先跟用户确认；一律 opaque / 白底或浅底
        ▼
art_undecided/portraits/<char>/    ← ① 原始产出（待审：概念图 / 立绘+胸像同图 sheet）
        │  用户审核 ✔
        ▼
art/portraits/<char>/             ← ② master：最终 full/bust + _opaque_source
   │  Real-ESRGAN x4 → Photopea 高分辨率抠图 → 缩回 → Aseprite 点修
        ▼
art/portraits/<char>/<char>_*.png  ← ③ 最终透明 master
   │  import/copy
        ▼
Assets/Art/UI/portraits/           ← ④ Unity 实际导入的副本
```

### 0.1 工具分工（2026-07-08 实测）

| 工具 | 最适合 | 不适合 / 风险 | 当前结论 |
|---|---|---|---|
| **GPT Image 1.5 high** | 新角色主立绘、第一张高完成度概念、审美定调 | 严格同一角色动作差分；服装结构、腰带、腿甲、披风剪影会漂 | **主立绘首选** |
| **Seedream 5.0 reference image** | 同一角色姿势 / 武器 / 剧情立绘差分 | 单张绘画完成度和动作表现不一定强于 GPT | **角色一致性惊艳，差分首选** |
| **即梦交互编辑 inpainting** | 云端 mask 局部重绘、表情候选 | 语义惯性强：高兴易露齿，难过易落泪；仍需人工挑选 | **有 mask，优于旧 inpaint** |
| **旧 `i2i_inpainting_edit`** | 仅历史兼容 / 粗草稿 | 文档标「下线中」，身份漂移严重，返回 JPEG/RGB 无 alpha | **淘汰** |
| **local ComfyUI + FaceDetailer** | 本地批量表情差分、只改脸 | 需要本地工作流和人工筛选 | **表情生产线最接近正解** |
| **火山 `saliency_seg` 抠图** | 快速 alpha 粗抠图 | 边缘羽化偏重，不如 X4 + 手工抠图 | **可作预览，不作最终上限** |

一句话：**GPT 定主立绘美术上限，Seedream 做同角色动作差分，Comfy/即梦做表情候选，最终仍由 Photopea/PS/Aseprite 锁一致性和边缘质量。**

---

## 1. 黄金铁律（先记这六条）

1. **最终角色资产从一张高质量 opaque sheet 开始。**
   立绘和胸像尽量放在**同一张 1536×1024 横版图**里生成：右侧 full-body / full portrait，左侧 bust。这样脸、发型、服装、盔甲细节、配色在一次生成内锁住，避免「立绘一套衣服、胸像另一套衣服」的漂移。概念图仍可作为 `--ref` 风格锚，但最终 sheet 才是角色 master 的直接来源。

2. **不要让 GPT 直接生成透明立绘。**
   - **一律 `--background opaque`**，通常用白底 / 近白干净背景。
   - ⚠️ `background=transparent` 会显著掉质量：脸、线条、盔甲和头发层次变糊，白袍 / 银甲 / 浅色区域还可能被误判成透明洞。
   - ⚠️ prompt 文本里也不要写「transparent background」。这会把模型带向低质贴纸/素材图分布。
   - 品红底也不是答案：底色会污染人物边缘，白发、银甲、浅色高光尤其明显。

3. **透明不是靠“完美抠图算法”，而是靠 4× 超采样做视觉 alpha。**
   JPG/opaque RGB 里没有原始 alpha，数学上无法唯一反推出真实透明度。最终生产流程是：白底高质量图 → Real-ESRGAN x4 → 高分辨率魔术棒/选择边缘 → 导出透明 PNG → 缩回目标尺寸，让降采样把细发丝和亚像素边缘变成自然半透明像素。

4. **二次元线稿是关键先验，断线处用 lasso 人工补约束。**
   白发 / 银发不是硬伤，因为日式立绘通常有发束线、蓝灰阴影和外轮廓线；魔术棒是在选「边缘连通的纯白背景」，不是单纯按颜色找白。真正的 edge case 是 AI 外轮廓线断掉：白底会从缺口连通到枪尖、银甲、高光或发丝内部。遇到这种情况，先用 polygon lasso 框住保护区 / 隔离区，再魔术棒选背景。

5. **`art/` 是 master，`Assets/Art/UI/portraits/` 是 Unity 副本。**
   Unity 只能从 `Assets/` 导入。最终文件底本必须在 `art/portraits/<char>/` 顶层，再拷贝到 `Assets/Art/UI/portraits/`。opaque 源图和 x4 工作图保留在 `art/portraits/<char>/_opaque_source/`，方便返修。

6. **GPT-Image API = 真金白银，每次调用前先跟用户确认。**
   `scripts/gpt_transparent_image_generation.py` / image generation 脚本的每次 generate / `--ref` 都是付费调用。本地处理（超分、切图、缩图、导入）可以直接做；只有发 API 这一步必须停下来确认。

---

## 2. 工序

| 步 | 动作 | 位置 | 谁做 |
|---|---|---|---|
| **① 源图生成** | 用 portrait-prompts 出 `--quality high --background opaque` 源图；需要时先概念锚，再出 full + bust 同图 sheet | → `art_undecided/portraits/<char>/` | Agent（**先确认**） |
| **② 审核** | 看画风：脸好？职业辨识度？服装统一？可作为最终底本？ | 看 `art_undecided/portraits/<char>/` | **用户** |
| **③ 归档 source** | 通过的最终 opaque source 移进 `_opaque_source`；当前统一命名为 `<char>_concept.png` | → `art/portraits/<char>/_opaque_source/<char>_concept.png` | Agent |
| **④ 4× 超分** | Real-ESRGAN x4 放大 approved source | → `art/portraits/<char>/_opaque_source/<char>_concept_x4.png` | Agent |
| **⑤ 高分辨率抠图** | Photopea 魔术棒 + Extend；断线处 polygon lasso 保护 | → 透明 PNG 工作图 | **用户**（Agent 可辅助缩图/检查） |
| **⑥ 缩回 + 点修** | LANCZOS 缩回目标尺寸；Aseprite 修少量 outlier | → `art/portraits/<char>/<char>_full.png` / `<char>_bust_base.png` | 用户 + Agent |
| **⑦ 导入** | 把成品**拷贝**进 Unity | → `Assets/Art/UI/portraits/` | Agent |

---

## 3. 目录约定（照抄）

```
docs/prompts/portrait-prompts.md              prompt 源
art_undecided/portraits/<char>/               ① 原始产出（待审）
art/portraits/<char>/_opaque_source/          opaque 源图 / x4 工作源备份
art/portraits/<char>/_opaque_source/<char>_concept.png
art/portraits/<char>/_opaque_source/<char>_concept_x4.png
art/portraits/<char>/<char>_full.png          最终透明立绘 master
art/portraits/<char>/<char>_bust_base.png     最终透明胸像 master
art/portraits/<char>/<char>_<表情>.png        可选：人工微调出的表情胸像
Assets/Art/UI/portraits/<Id>_full.png         Unity 导入副本（立绘）
Assets/Art/UI/portraits/<Id>_bust.png         Unity 导入副本（胸像）
```

> **`<char>` vs `<Id>`**：`<char>` 是 `art/portraits/` 下的小写资源目录名，如 `luli` / `suyao` / `lingshuang` / `empirearcher` / `empireaxesoldier` / `empirecaptain`。`<Id>` 是 Domain `DisplayName` / Unit id 的 PascalCase 名，如 `LuLi` / `SuYao` / `LingShuang` / `EmpireArcher` / `EmpireAxeSoldier` / `EmpireCaptain`。Unity 副本必须用 `<Id>_bust.png` + `<Id>_full.png`，因为 `BattleHud.PortraitFor(unit.DisplayName)` / detail overlay 靠这个查图。

> **当前历史例外**：`art/portraits/empireaxesoldier/_opaque_source/` 里源文件仍叫 `empireaxe_concept.png` / `empireaxe_concept_x4.png`，这是早期 `empireaxe` 命名留下的 source 备份；最终 master 和 Unity 副本仍以 `empireaxesoldier` / `EmpireAxeSoldier` 为准。

---

## 4. 生成步骤细节（GPT-Image）

- **脚本**：`scripts/gpt_transparent_image_generation.py`。
- **概念 / source**：`<char>-concept` 预设，`--background opaque`，建议 `--size 1536x1024`（角色卡 / 全身 / 表情参考都可放下）。通过审核、作为最终底本的 opaque source 归档为 `art/portraits/<char>/_opaque_source/<char>_concept.png`。
- **最终 sheet**：需要二次生成时用 `<char>-sheet` 预设，`--background opaque`，`--size 1536x1024`，**`--ref art/portraits/<char>/_opaque_source/<char>_concept.png`**。推荐布局：右侧 full-body / full portrait，左侧 bust。当前生产只需要 `<char>_full.png` + `<char>_bust_base.png`；不同表情后续由人基于 bust 微调。
- **质量**：正式进入 pipeline 的概念图 / 最终 sheet 一律 `--quality high`。`low` 往往会显得细节更多、信息量更大，但这些细节经常是不可控的碎线、伪纹样、假文字 / 框线和随机装饰，粗看丰富，细看 AI 味重。`high` 的价值不是单纯“细节更多”，而是更克制、更可控，更容易保持脸、服装轮廓、材质逻辑和角色间风格一致。低 / 中质量只用于明确的付费试稿，不能作为最终抠图底本。
- **角色识别度**：主角团 / 主要角色可以保留清晰大眼、明亮高光和高辨识脸。杂兵 / 大众脸不要画成主角脸：眼睛可以更小、更窄，眉眼压低，眼部适当加阴影或被头盔/刘海压暗，降低个体识别度；但仍要能看清阵营、职业和武器。
- **模型**：默认 `gpt-image-1.5`（通常质量 / 价格更合适；虽支持透明，但本 pipeline 不使用透明出图）。需时可 `--model gpt-image-1` 回退。
- **语言**：走 Image API **不会 rewrite**（不同于 ChatGPT 网页 / Responses API 工具），prompt **逐字使用** → 用**英文** prompt 最稳（portrait-prompts.md 已是英文精简版）。
- ⚠️ **调用前停下来跟用户确认**（每次 generate / `--ref` 都付费）。

### 4.1 Seedream 5.0：同一角色动作 / 武器 / 姿势差分

Seedream 5.0 不一定是主立绘审美上限，但实测在**参考图一致性**上非常强。陆离、凌霜实验中，它能保住：

```text
脸型 / 发型 / 发色 / 眼色 / 主要服装分区 / 披风轮廓 / 腰带 / 甲片 / 角色体型
```

适合做：

```text
拔剑 / 持枪 / 跪地 / 挥剑 / 受伤 / 低落 / 剧情姿势差分
```

不适合做：

```text
主立绘首图审美定调（GPT Image high 仍更强）
严格局部修脸（走 Comfy / 即梦）
```

调用方式：

```text
Endpoint: https://ark.cn-beijing.volces.com/api/v3/images/generations
Auth: Bearer Ark API Key（本地 volcenginekey.txt）
model: doubao-seedream-5-0-260128
field: image = data:image/png;base64,...  # 单张参考图
size: 1664x2496 或按角色比例指定
output_format: jpeg
response_format: url  # 避免大 b64_json 响应被截断
```

本地脚本：

```text
scripts/volcengine_seedream_ref_portrait.py
```

推荐 prompt 结构：

```text
参考图中的人物形象、脸型、发型、眼色、服装结构、配色、职业气质和画风。
必须生成同一个角色；不要换脸、不要换发型、不要改变发色眼色、不要改变主配色、不要过度华丽。
竖版全身立绘，完整人物从头到脚可见，留安全边距。
动作：<具体动作/武器/情绪姿势>。
```

生产建议：

```text
GPT 主立绘 / concept sheet
   → 裁出单独 full-body 参考图（不要整张 sheet）
   → Seedream 参考图生图生成动作差分
   → 横向对比检查服装结构是否跳
   → 通过后再走 X4 + 手工抠图
```

### 4.2 表情差分：Comfy FaceDetailer / 即梦 inpainting

表情差分的目标不是“画一张更好看的脸”，而是切换表情时玩家仍觉得是同一张脸。审核重点：

```text
眼睛大小不跳
眉毛粗细不跳
嘴线粗细不跳
鼻子位置不跳
脸型边界不跳
颜色不跳
```

#### A. 首选：local ComfyUI + FaceDetailer

用户本地实测可行工作流：

```text
LoadImage 原全身图
CheckpointLoader: Illustrious-XL
正向提示词: 身份锚点 + 表情
负向提示词
YOLO 脸检测
SAM 精细分割
FaceDetailer
SaveImage
```

优点：

- 只处理脸部检测区域，blast radius 小。
- 不污染身体、披风、盔甲、角色外轮廓。
- 本地批量抽候选，无云端 API 成本。

FaceDetailer 的本质是：

```text
detector 找到区域 → crop / mask → inpaint/detail → 贴回原图
```

默认常接 face detector，但并非只能画脸；接手部 / 人物 / 自定义 bbox 或 mask 时也能处理其他局部。

#### B. 备选：即梦 AI 交互编辑 inpainting

文档：`https://www.volcengine.com/docs/85621/1976207?lang=zh`

```text
Endpoint: https://visual.volcengineapi.com
Action: CVSync2AsyncSubmitTask / CVSync2AsyncGetResult
Version: 2022-08-31
Region: cn-north-1
Service: cv
Auth: AK/SK 签名（volcengineak.txt + volcenginesk.txt）
req_key: jimeng_image2image_dream_inpaint
binary_data_base64: [原图, mask]
mask: 黑色 0 = 保持，白色 255 = 待重绘
prompt: 必填，建议 <=120 字
seed: 默认 101
```

本地脚本：

```text
scripts/volcengine_jimeng_inpaint.py
```

实测结论：

- 比旧 `i2i_inpainting_edit` 强很多。
- 表情读法明显，mask 真实可用。
- 但语义惯性强：`高兴` 容易露齿笑，`难过` 容易落泪。
- 否定词不稳：`不要露牙` / `不要眼泪` 可能仍失败。
- 正向写法更好：`闭唇微笑`、`脸颊干净`、`沉默低落`。

推荐 prompt 写法：

```text
日式战棋RPG立绘，干净赛璐璐，克制商业手游画风。
只编辑mask内脸部表情；保持角色身份、脸型轮廓、蓝眼睛、发色、肤色、服装颜色和未遮罩区域一致；
只允许眉毛角度、眼睑开合、嘴角弧度小幅变化。
目标：<轻微表情，使用正向描述>。
```

推荐表情词：

```text
微笑：一点笑意 / 浅浅微笑 / 闭唇微笑 / 嘴角小幅上扬
低落：沉默低落 / 温和遗憾 / 眼神向下 / 脸颊干净
生气：轻微生气 / 眉毛内压 / 嘴巴紧闭
疑惑：轻微疑惑 / 一侧眉毛略抬 / 嘴巴闭合
```

避免：

```text
大笑、伤心、哭、强烈生气、夸张表情
```

因为模型会自动放大这些语义。

### 4.3 旧火山 inpaint 与抠图服务定位

旧 prompt inpaint：

```text
req_key: i2i_inpainting_edit
状态: 文档标记「下线中」
问题: 身份漂移、面罩/黄眼等严重重绘、返回 JPEG/RGB 无 alpha
```

不再作为主流程，只保留历史脚本用于对照。

主体分割抠图：

```text
req_key: saliency_seg
only_mask: 3/4
rgb: [-1,-1,-1]
```

可返回真 RGBA 透明图，但边缘羽化偏重。最终立绘透明资产仍走：

```text
Real-ESRGAN x4 → Photopea / PS 手工抠图 → 缩回 → Aseprite 点修
```

---

## 5. 出图后处理

| 步骤 | 工具 | 备注 |
|---|---|---|
| 分切 sheet | Photopea / Python | 从 approved opaque sheet 切出 full、bust 工作图；保留原始 sheet 备份。 |
| 4× 超分 | Real-ESRGAN | 对 JPG/PNG 原图做 x4。目标不是“无损”，而是把 1px 内的发丝、枪尖、描边和镂空结构展开到可编辑尺度。 |
| 背景选择 | Photopea 魔术棒 | 在 x4 图上选边缘连通的白底 / 浅底。容差按图调，常见起点约 32；比原尺寸稳定得多。 |
| Extend | Photopea | 魔术棒选区后 Extend 1px。在 x4 下等价于最终图约 0.25px，缩回后边缘自然，不会像原尺寸 1px 那样粗暴吃细节。 |
| 断线保护 | Photopea polygon lasso | AI 外轮廓线断掉时，先用 lasso 框住枪尖、银甲、发丝等保护区，再选背景；防止白底从缺口连进主体。 |
| 导出透明工作图 | Photopea | 导出 PNG。宁可多留一点可点修边缘，也不要让选择吃进人物结构。 |
| 缩回目标尺寸 | Python / 图像工具 | LANCZOS 缩回 1024 高或项目目标尺寸；RGB 和 alpha 分通道缩放，避免透明边缘颜色渗入。缩小会把高分辨率细发丝平均成自然半透明。 |
| 最后点修 | Aseprite | 只修几个 outlier：孤立白点、脏点、断裂边缘。不要大面积手补渐变，AI 边缘颜色变化太细。 |
| 导入 Unity | 脚本 / 手写 .meta | Sprite、Bilinear、PPU 100、alphaIsTransparency、Uncompressed。立绘是高清 UI 件，不走像素角色的 Point 规则。 |

> 这条线的目标是「视觉生产级」，不是恢复数学真实 alpha。只要在黑底、深色 UI、实际战斗背景上没有明显白边 / 脏边，就算通过。

---

## 6. Photopea 操作速查

### 6.1 基础设置

- 打开 x4 工作图后，先确认正在编辑的是**人物图层**，不是黑底检查图层。
- 如果图层是锁住的 `Background`，先双击图层解锁 / 转普通图层；否则删除背景可能变成填白色，而不是透明。
- Magic Wand 建议起点：`Tolerance` 约 32，`Contiguous` 开，`Anti-alias` 可开，`Sample All Layers` 通常关（尤其有黑底检查层时）。按图微调，不要死守数值。
- 常用视图：`Ctrl + +` 放大，`Ctrl + -` 缩小，`Space` 拖动画布，`Ctrl + 0` 适配窗口。

### 6.2 选择 / 多重选择

- **反选**：`Ctrl + Shift + I`。
- **取消选择**：`Ctrl + D`。
- **多次加选背景**：Magic Wand 点第一块背景后，按住 `Shift` 再点其他背景块，等价于 Add to selection。
- **从选区扣掉误选区域**：按住 `Alt` 用 Lasso / Polygonal Lasso / Magic Wand 操作，等价于 Subtract from selection。
- **交集选择**：按住 `Shift + Alt`，或更稳妥地直接点顶部选项栏的 `Intersect with selection` 图标。
- Photopea 顶部选项栏有四种模式：New / Add / Subtract / Intersect。快捷键不顺手时，直接点图标，少犯错。

### 6.3 矩形限制 + Magic Wand

这是处理枪尖、发丝、银甲高光、局部断线时最常用的办法。

1. 用 Rectangular Marquee 框住一个局部区域。
2. 切到 Magic Wand。
3. 选择顶部模式 `Intersect with selection`，再点区域内的白底。
4. 得到的选区只会保留“矩形范围内的魔术棒结果”。这适合只清某个局部背景，不让选择跑到全图。

如果要处理矩形**外部**：先框住要保护的区域，`Ctrl + Shift + I` 反选，再用 Magic Wand 的 `Intersect with selection` 清外侧背景。也可以先 Magic Wand 选全局背景，再用 `Alt + Polygonal Lasso` 把要保护的枪尖 / 发丝 / 盔甲从背景选区里扣掉。

### 6.4 标准抠图动作

1. Magic Wand 选边缘连通的白底。
2. `Shift` 多点几次，把未连通的背景块加进选区。
3. 如果选区吃进主体，用 `Alt + Polygonal Lasso` 把主体区域从选区扣掉。
4. `Select > Modify > Expand...`，通常 Expand 1px。
5. 按 `Delete` / `Backspace` 删除背景，确认出现透明棋盘格。
6. `File > Export As > PNG` 导出透明工作图。

原则：宁可多留一点边缘，缩回后 / Aseprite 再点修；不要让选区吃进发丝、枪尖、脸缘、盔甲轮廓。

### 6.5 黑底 / 深色底检查

1. 新建图层：点 Layers 面板底部 `New Layer`。
2. 把新图层拖到人物图层下面。
3. 选中这个新图层，`Shift + F5` 打开 Fill。
4. 填 `Black` 或 `#000000`。
5. 也可以再建一个深蓝 / 深绿检查层，模拟游戏 UI 和战斗背景。
6. 导出最终 PNG 前，隐藏或删除这些检查层。

黑底检查专门看白边、灰边、孤立白点；透明棋盘格上看不出来的问题，黑底通常一眼暴露。

### 6.6 铅笔 / 橡皮 / 局部修补

- Pencil 在 Brush 工具组里：长按 Brush 图标，切 Pencil；快捷键通常是 `B`，再从工具组里选 Pencil。
- 用 Eyedropper (`I`) 从附近边缘取色，再用 1-3px Pencil 小范围补断点。
- Eraser (`E`) 用硬边小尺寸，100% opacity，清孤立白点 / 脏点。
- 不要大面积用画笔补 AI 渐变。AI 立绘边缘每个像素的颜色都在变，手补一大片很容易变脏；Photopea 只做局部结构修复。

---

## 7. Aseprite 点修速查

- 适合修最后几个像素级 outlier：孤立白点、透明脏点、断裂的 1-2px 边缘、枪尖小缺口。
- 放大到能看清单个像素后再动手；不要在正常缩放下凭感觉刷。
- 选像素：用 Rectangular Marquee / Lasso / Magic Wand 选小范围，`Ctrl + D` 取消选择。
- 删除像素：选中脏点后 `Delete`，或用 Eraser (`E`) 1px 硬擦。
- 替换像素：Eyedropper (`I`) 吸附近正确颜色，Pencil (`B`) 设 1px、Opacity 100%，逐点覆盖。
- 如果颜色/透明度刷不实，检查 Ink 模式，优先用 `Copy Color` / `Copy Color+Alpha` 一类的直接替换模式，避免半透明像素被继续叠色。
- 临时检查底：可以新建底层，Paint Bucket (`G`) 填黑 / 深蓝；导出最终 PNG 前隐藏或删除。
- 不要在 Aseprite 里大面积重画发丝渐变。它适合像素点修，不适合恢复 AI 生成的细腻连续渐变。

---

## 8. 审核 checklist（用户把关）

- [ ] **脸没崩**：五官干净、对称、无畸变？
- [ ] **识别度符合定位**：主角 / 主要角色有清晰眼神和角色脸；杂兵 / 大众脸眼睛更小、更窄或带阴影，不抢主角团辨识度？
- [ ] **服装一致**：立绘和胸像来自同一 sheet，盔甲 / 袍子 / 披风 / 武器细节没有跨图漂移？
- [ ] **透明边缘可上线**：背景全透，发丝 / 枪尖 / 银甲边缘干净，无白点、灰底残留、明显 halo？
- [ ] **多背景预览**：透明棋盘格、黑底、深蓝/深绿底、实际战斗 UI 背景都看过？
- [ ] **风格统一**：与概念图 / 队伍其他角色同一画风、比例、上色、光照？
- [ ] **职业 / 角色辨识度**：一眼看出职业 + 是这个角色？
- [ ] **构图**：立绘全身不裁脚、不贴边、居中留白？
- [ ] 无文字 / logo / 水印 / 边框 / UI？

---

## 9. 为什么这样定（背景，给未来的自己）

- **为什么不再用 GPT 透明**：A/B 实测同 prompt 同 ref，transparent 版本整体质量下降，五官、线条、头发、盔甲都更糊；浅色衣服还会被误打透明洞。opaque 白底图质量稳定得多。
- **为什么不再把 rembg 当最终方案**：removebg / rembg / flood-fill / 魔术棒在原尺寸上都会留下边缘污染。白底 JPG/PNG 只有 RGB，没有原始 alpha；边缘像素已经是「人物色 + 背景白」的混合，算法无法唯一知道真实前景色和透明度。
- **为什么 x4 超分有效**：Real-ESRGAN 会把二次元线稿、发丝和亚像素边缘展开成更清晰的结构。Photopea 在 4× 尺寸下 Extend 1px，只相当于最终 0.25px；缩回时降采样自然生成半透明边缘，类似 supersampling。
- **为什么白发 / 银发也能做**：二次元白发通常不是纯白块，而是由描边、蓝灰阴影、发束线和高光组成。魔术棒选的是边缘连通的纯白背景；只要外轮廓结构还在，银发可以保住。
- **为什么要 lasso 保护断线**：AI 图常有局部轮廓线不连续。魔术棒只懂连通区域，枪尖 / 银甲 / 白布高光一旦从断线处连到背景，就会被吃掉。polygon lasso 是给算法补一个几何边界，人工成本低，收益高。
- **为什么概念图当锚**：一次锁死脸 / 发 / 服装 / 配色，后续 final sheet 用它当 `--ref`，跨图一致性由参考图保证，不靠反复描述。
- **为什么英文 prompt**：Image API 不改写 prompt，逐字使用；英文对画风术语命中最稳（中文能用但抽象词是废 token）。
