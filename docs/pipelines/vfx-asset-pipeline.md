# VFX 资产 Pipeline · 《幻世纪》FantacyCentry

> **这是什么**：把「一个技能特效想法」变成「Unity 里可用的 VFX 逐帧序列（`Assets/Art/VFX/<key>/frameN.png`）」的标准工序(SOP)。
> **适用范围**：所有**战斗技能/法术特效** —— 火球、闪电、冰锥、剑气、治疗、爆炸、打击等。
> **不适用**：角色 sprite 动作（施法/受击 pose 是**角色层**，走 [`char-sprite-asset-pipeline.md`](./char-sprite-asset-pipeline.md)）；地图物件；UI；tile。
> **本地模型**：Wan 2.2（视频）、FLUX / SDXL（静态图）都在本地跑；GPT-Image / Seedream 为云端备选。
> **来由**：VFX 出图实验（GPT-Image 12帧连拍效果一般 → 转 Wan 视频抽帧路线）+ 2026-07-03 process §一的切图/抠底教训。
>
> **开新 session 只需读这一篇。** 状态台账（各技能用哪几段、状态）记在文末的登记表。

---

## 0. 一句话链路

```
① 峰值关键帧（FLUX/SDXL，静态）      ← 把"最难的爆发瞬间"画死
        │  I2V：拿关键帧当首帧喂给 Wan
        ▼
② Wan 2.2 视频（5s，只演平滑运动/余波，固定机位、纯黑底）
        │  ffmpeg 抽帧（掐你要的那段区间，不用全 5 秒）
        ▼
③ 抽帧 → 抠底（黑/品红 flood-fill）→ pixel 化（下采样 + 统一调色板）
        │  统一画布对齐（着地类底对齐 / 飞行类居中）
        ▼
art/vfx/<category>/<key>/frameN.png       ← master（逐帧序列 + _preview_<key>.gif 审核）
        │  人工审 GIF；用户定稿
        ▼
Assets/Art/VFX/<key>/frameN.png           ← Unity 实际导入副本（Point / PPU=64 / alphaIsTransparency）
```

游戏侧怎么吃（**已实装**，别改约定）：
- `BattleSceneBuilder` 用 `LoadFrames("Assets/Art/VFX/<key>/")` 把**扁平帧目录**读成 `Sprite[]`，塞进 `BattleStageDirector.<key>Frames`。
- `BattleStageDirector.BankFor(vfxKey)` 按 **key 子串匹配**（`sword`/`light`/`ice`/`fire`/`heal`）。
- `PlayVfx` 播这一串：**贴地 pivot(0.5,0)**；`travelFromX` = 把 x 从施法者 lerp 到目标（飞行）；`impactFrac` = 第几帧算命中触发打击；`speedMul` = 播放倍速。

---

## 1. 黄金铁律（先记这几条）

1. **两个层分清：角色动作 ≠ VFX。**
   - **层 A 角色 sprite**（抬手/举杖/挥剑的 pose）= 角色图集，走角色 pipeline，**不在这里做**。
   - **层 B VFX** = 本文档的产物，叠在角色上播。Wan **只画层 B**。

2. **位移在代码里做，不烘进美术。**
   VFX 素材只画**"原地的形变与生命周期"**；飞行/命中时机由引擎 `travelFromX`/`impactFrac` 驱动。所以一个"原地燃烧的火球 loop"能被任意射程、多个技能复用。**让 Wan 画"火球飞行"= 跟代码抢位移，必打架。**

3. **"3 段"是菜单/上限模板，不是每个技能都凑齐三段。**
   | 段 | 内容 | 锚点 | 循环? | 何时要 |
   |---|---|---|---|---|
   | ①发射/muzzle（可选） | 起手光圈/聚能 | 施法者身上 | 播一次 | 多数技能可跳过 |
   | ②飞行/projectile | 原地燃烧的火球本体、旋转剑气 | 自身中心 | **无缝 loop** | **有"可变距离飞行"才要** |
   | ③命中/impact | 爆炸、炸裂、落地爆闪 | **底部贴地对齐** | 播一次 | 几乎都要 |

   - **投射类**（火球/剑气/弓箭）= ②飞行 loop + ③命中。
   - **即时着地类**（闪电/冰锥/治疗）= **只有 ③**，一个 clip 贴地播一次（劈下+爆闪烘在一起，因为没有可变飞行距离可拆）。

4. **复用只发生在同系、同风格之间。** 火球爆炸可复用给别的**火系**；闪电落地是电火花、跨系**不复用**火球爆炸。

5. **Wan 是"平滑持续运动"发生器，不是"瞬间爆发"发生器。**
   视频扩散模型被优化成时间连贯，**天生抗拒剧烈突变**，会把爆炸摊平成慢 morph。5 秒对一个 VFX 节拍（真实爆炸 ~0.5s）**太长**。破解 = **把爆发峰值用 FLUX/SDXL 画成首帧**，让 Wan 只做它擅长的**平滑扩散/消散/循环**。

6. **着地/落地类必须底对齐**（`oy=Hc-pad-h`），不能 bbox 居中，否则地面线逐帧漂移。切图后 contact sheet 画红色地面线验证（07-03 教训）。

7. **别让 Wan 画镜头。** prompt 删一切运动/镜头词（`flying/moving/camera/tracking/arc`），强调 `static camera / in place / centered / no camera movement`。

---

## 2. 工序表（SOP）

| 步 | 动作 | 位置 | 谁做 |
|---|---|---|---|
| **① 峰值关键帧** | FLUX/SDXL 出"爆发峰值/火球本体"静态图（纯黑或品红底） | 本地 → `art/vfx/_gen/<key>/key_*.png` | Agent + 用户审 |
| **② Wan I2V** | 关键帧当首帧，Wan 出 5s 视频（只演余波/循环，固定机位） | 本地 → `art/vfx/_gen/<key>/*.mp4` | 用户（本地跑）|
| **③ 抽帧** | `ffmpeg` 抽帧，**掐要用的区间**（不用全 5s） | → `art/vfx/_gen/<key>/raw/` | Agent |
| **④ 抠底** | 黑/品红 flood-fill 抠透明（复用草地抠底那套） | 覆盖 raw | Agent |
| **⑤ pixel 化** | 下采样到目标像素密度 + 统一调色板量化 | → `art/vfx/_gen/<key>/px/` | Agent |
| **⑥ 挑帧+对齐** | 抽到 **8–16 帧**；投射类居中/着地类底对齐；进统一画布 | → `art/vfx/<category>/<key>/frameN.png` | Agent + 用户 |
| **⑦ 审核** | 拼 `_preview_<key>.gif`（深底）+ 编号 contact sheet；飞行段验无缝 loop | 看 gif | 用户定稿 |
| **⑧ 入库** | 拷进 `Assets/Art/VFX/<key>/`，写 `.meta`（Point/PPU64/alphaIsTransparency）| Assets | Agent |
| **⑨ 接线** | 若是**新** key：`BattleSceneBuilder.LoadFrames` + `BankFor` + `Ability.VfxKey` | 代码 | Agent |

---

## 3. Wan prompt 工程（实测要点）

### 3.1 通用护栏（每条都加）
- `static camera, no camera movement, in place, centered, plain solid black background`
- 删：`flying / moving forward / projectile / camera pans / tracking shot / arc`。
- 节奏词把动作往前挤：`erupts instantly / sudden rapid burst`（因为你只留爆发那零点几秒）。

### 3.2 ②飞行 loop（Wan 强项，直接出）
- 只描述**本体原地翻滚**：
  > `a single fireball hovering in place, flames churning and licking outward, embers rising, seamless looping, static camera, centered, plain black background`
- 抽帧后**首尾接一起验证无缝**（对照 `_preview_*.gif`）。

### 3.3 ③爆炸/命中（Wan 弱项 → 峰值首帧策略）
- **不要**让 Wan 从"聚起来砰"开始。用 FLUX/SDXL 画一张**已经在爆炸峰值**的首帧，I2V 让 Wan 只演扩散+消散（平滑=它擅长）：
  > Wan prompt：`the explosion expanding and rolling outward then dissipating into smoke and embers, static camera, ground at bottom, plain black background`
- 实在炸不出的极端瞬间（碎裂定帧）→ 关键帧用 FLUX/SDXL 甚至 GPT-Image 直接出，过渡帧再交给 Wan。

### 3.4 即时着地类（闪电/冰锥，一个 clip）
- 闪电：`a lightning bolt striking straight down onto the ground in place, blue-white electric flash and sparks bursting on impact then fading, static camera, ground at bottom, plain black background`
- 冰锥：`ice spikes erupting upward from the ground in place then shattering into frozen shards, static camera, ground at bottom, plain black background`

---

## 4. 抽帧 / 抠底 / pixel 化 / 对齐（本地处理，已验证的坑）

1. **抽帧掐区间**：`ffmpeg -i in.mp4 -vf "select='between(t,1.2,2.0)'" -vsync 0 raw/f%03d.png`（只取爆发段）。
2. **抠底**：纯黑/品红底做**边缘 flood-fill**（tol 40–48 + 1px 膨胀吃边缘晕）；发光边缘 alpha 渐变别一刀切。
3. **pixel 化**：下采样到目标像素密度（VFX 一般比 tile 略高），再**统一调色板量化**（同一批 VFX 过同一 palette，避免每技能色调乱跳）。
4. **挑帧**：视频帧多，抽到 **8–16 帧**够（SRPG 演出快）。loop 段选首尾接得上的区间；impact 段掐"起爆→消散"。
5. **统一画布对齐**：每帧 tight-crop alpha bbox → 放进 `max(W,H)+pad` 同尺寸画布：
   - **飞行/投射类** → bbox 居中（`travelFromX` 会搬运）。
   - **着地/命中类** → **底对齐** `oy=Hc-pad-h`（贴地不漂）。
6. **别 bake 帧号/网格线**：Wan 不会带，但若参考图带了，先涂空再切（07-03 lightning2 踩过 baked-in 数字）。
7. **审核产物**：`_preview_<key>.gif`（深底 30,30,38，duration 90，disposal 2）+ 编号 contact sheet（着地类画红色地面线 `y=Hc-pad` 验证）。GIF 已 gitignore。

---

## 5. 目录约定

```
art/vfx/
  _gen/<key>/               ← 中间产物（关键帧/mp4/raw/px，GITIGNORED，可重跑）
    key_*.png               ← FLUX/SDXL 峰值关键帧
    *.mp4                    ← Wan 视频
    raw/  px/               ← 抽帧 / pixel 化中间帧
  <category>/<key>/         ← master 逐帧（category = magic/attack/…）
    frame0.png … frameN.png
  _preview_<key>.gif        ← 审核 GIF（gitignored）

Assets/Art/VFX/<key>/       ← Unity 导入副本（扁平帧，LoadFrames 直接读）
  frame0.png … frameN.png
```

- **`<key>` 命名要能被 `BankFor` 子串匹配**：含 `fire`/`light`/`ice`/`sword`/`heal`。新元素要加匹配分支。
- 一个技能若拆多段：现阶段代码是**单 bank/技能**，先把最能代表的那段（投射类=飞行 loop，着地类=命中）落成 `<key>/`；**多段分离播放是后续代码升级**（见 NEXT），届时目录扩成 `<key>/{projectile,impact}/`。

---

## 6. 现有技能登记表（真值源）

| key | 类型 | 段 | 现状 | Wan 策略 |
|---|---|---|---|---|
| `fireball` | 投射(火) | ②飞行loop +（③爆炸复用火系）| 已有 GPT 切帧，待 Wan 重做 | 飞行=直接 Wan；爆炸=FLUX峰值首帧 |
| `swordwave` | 投射(物理) | ②飞行loop | 已有 | 直接 Wan 原地旋转新月 |
| `lightning` | 即时着地(电) | ③单clip | 已有 | 一个 clip 劈下+爆闪 |
| `icespike` | 即时着地(冰) | ③单clip | 已有 | 一个 clip 升起+炸裂 |
| `heal` | 贴身(自然) | 单clip | 已有 | 原地绿光上升循环 |

> 首个 Wan 试验目标 = **fireball**：走「FLUX 峰值首帧 → Wan 演余波 → 抽帧 → 分段（飞行loop / 爆炸）」全流程验证。

---

## 7. NEXT（待办 / 后续代码升级）

- **fireball 全流程试跑**（明天）：验证「峰值首帧 → Wan 余波」比 GPT 12帧连拍好多少。
- **多段分离播放**（代码）：`PlayVfx` 现在单 bank；升级成能顺序播 `muzzle → projectile(loop, travel) → impact(one-shot, ground)`，目录扩 `<key>/{projectile,impact}/`。
- **统一 VFX palette**：定一版全技能共用调色板，量化时统一。
- **本地脚本**：`scripts/vfx_extract.py`（ffmpeg 抽帧 + 抠底 + pixel 化 + 统一画布 + preview gif），把 §4 固化成一键。
</content>
</invoke>
