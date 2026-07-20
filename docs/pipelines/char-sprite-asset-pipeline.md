# 角色 Sprite 资产 Pipeline · 《幻世纪》FantacyCentry

> **这是什么**：把「一句角色 prompt」变成「Unity 里可用的角色战棋 sprite（8 方向 rotation + idle/walk/attack/knockback/knockout 动画）」的标准工序（SOP）。
> **适用范围**：**PixelLab 生成的像素角色**（我方 / 敌方单位、坐骑）。走 3-头身 chibi、side/low-top-down 视角。
> **不适用**：立绘 / 头像（走 [`portrait-asset-pipeline.md`](./portrait-asset-pipeline.md)）；地图物件 / 建筑（PixelLab map-objects，另说）；UI / tile。
> **真值源**：状态与方向 anchor 在 [`pixellab/character_status.yaml`](../../pixellab/character_status.yaml)。
>
> **开新 session 只需读这一篇 + character_status.yaml。**

---

## 0. 一句话链路

```
pixellab/character_status.yaml         ← 真值源：每角色的 prompt / character_id / anchor / 每动画 prompt+status
   │  PixelLab v2 API（订阅额度，非按次真金；token 在 repo 根 pixellabkey.txt，已 gitignore）
   │
   ├─①  create-character-v3  → 8 方向 rotation
   │        ▼
   │   ⚠️ 停下来：用户审核 rotation，按【视觉】人工敲定 6 槽 anchor（S/N/E/SE + 镜像 W/SW）
   │        ▼
   ├─②  characters/animations（v3）→ 每个锚定方向一套动画帧
   │        │   两条路径（见 §2 步骤4）：
   │        │   • 网页生成 → zip 干净 → pull → check → organize（从 zip）
   │        │   • 脚本生成 → 从 job.last_response.images 直接存（zip 会碎片化）
   │        ▼
   └─③  本地整理（按 anchor 把 pixellab 帧 copy+改名成【我们的方向】）
            ▼
pixellab/characters/<id>/
   ├── download/     ← 原始 zip + 解压件（GITIGNORED，可随时重下）
   ├── review/       ← 每动画逐帧对比 PNG（人工审用）
   ├── rotations/    ← 8 方向原图（pixellab 命名 south/east/...）+ _contact.png
   └── animations/<action>/<S|N|E|W|SE|SW>/frame_00N.png   ← 我们的方向命名（按 anchor 映射）
```

---

## 1. 黄金铁律（先记这几条）

1. **方向 mapping 每个角色独立，必须用户审核 rotation 后才能定，AI 绝不预设。**
   PixelLab 的 8 方向朝向**不稳定、每个角色随机**，**没有固定偏移公式**（历史上的「逆时针偏一格」是错的，已废弃）。
   **!!! 按【视觉】锚定，不认 pixellab 文件名**——一张名叫 `south` 的图视觉上可能是 SE，`east` 可能才是干净的 45°。文件名不可信，只看图里身体/武器的**真实朝向**。
   **强制流程**：① 只跑 rotation → 出 8 张图；② **用户看图**，指定每个【我们的方向】= 哪张 pixellab 图；③ anchor 写进 yaml；④ **anchor 定了之后**才允许跑 animation。
   一个角色的 anchor **不能套用**到别的角色。

2. **两套方向：地图 top-down + 战斗 45° 侧视。共 6 个游戏方向 S/N/E/W/SE/SW，只【生成】4 个源方向，其余镜像。**

   | 场景 | idle | walk | attack | react/hit/knockback/knockout |
   |---|---|---|---|---|
   | **地图**（top-down） | S | S N E W | — | — |
   | **战斗**（45° 侧视） | SE / SW | E W | SE / SW | SE / SW |

   - **生成的源** = `S`(视觉正面) / `N`(视觉背面) / `E`(视觉侧向, walk 用) / `SE`(视觉 45°, 战斗用)。
   - **镜像** = `W = flipX(E)`、`SW = flipX(SE)`；S/N 无镜像。哪一侧是真图、哪一侧镜像**由用户定**（别默认 W 一定是 E 的镜像）。
   - **E 可复用 SE**：若某角色没有干净的近侧脸（纯 90° profile），E 直接指向 45° 那张（E 和 SE 同一帧），**不增加生成量**（SuYao / cavalier 就是这样；captain 是唯一 E≠SE 的，有独立侧向）。

3. **F1 绝不写 idle。** PixelLab 一定把 rotation 帧作为 **frame_000（idle 静止起始）**，`frame_count=8` 落盘其实是 **9 帧**。所以动画描述的 8 帧要**直接从动作开始**，否则开头两帧不动（「前几帧僵」）。

4. **不用 "GBA" 等老式像素词，也别加 "modern/high-res pixel"。** 前者让人物粗糙、还强绑一撮翎羽；后者让模型乱长金犄角。删掉 GBA、rotation 尾巴走默认 `clean pixel art, vibrant colors, sharp silhouette` 最干净。`image_size` 保持 128。
   **!!! 动画 prompt 不再加 `Clean pixel art, sharp silhouette.` 尾巴（2026-07-19）** —— PixelLab 自己会控质量，加了没用，还占 1000 字符额度、污染 prompt。**新写的动画 prompt 一律不带这句尾巴**（已定稿的老 prompt 不动）。

5. **PixelLab API 收的是订阅额度（非按次真金）**，跟 GPT-Image 不同，**不需要每次调用前确认**（但留意 Tier1 2000/月额度）。rotation ≈ 3 gen，animation ≈ 8 gen/方向。

6. **sprite 上不烘焙 VFX。** attack/施法等**绝不**在 sprite 里画发光/闪光/法术光/粒子/能量——VFX 用独立 asset 叠加（baked-in 的没法控制）。prompt 里用**重否定词**（`NO glow, NO light, NO sparkles, NO flash, NO burst, NO particles`）并把法器/武器描述成 `plain / unlit`。只让**身体+道具**动。

7. **每次生成后必做 QA（两条硬指标，过不了就重出）：**
   1. **头长 45–48px**（发顶→下巴）。**头大小 > 头身比**——地图上大家 sprite 摆一样大，玩家第一眼扫的是头；头一致就像「同一套」，身高长短随意（女生矮、男主腿长都 OK）。友方主力必须落在 45–48；敌兵可略放宽。⚠️ **兜帽/头盔/发髻会把「发顶」虚高 3–4px**，比较时心里扣掉。快速粗筛用 `measure_head.py`（放大打网格 + 目测发顶/下巴线，±2–3px 误差）；**最终精确值用 Aseprite 手量**（`rotations/*.png` 直接拖进去，选框数发顶→下巴的行数）。
   2. **正 S / 正 N / 侧面 三向 rotation 无问题**——正对 / 正背 / 干净侧向，武器与身体朝向对、silhouette 没崩。这三向是地图与战斗的主力帧，必须干净（其余方向靠镜像或复用）。

---

## 2. 分步工序（SOP）

### 步骤 0 — 写 prompt（rotation）
- 结构：`Fire Emblem style chibi {enemy/ally} {archetype}, western fantasy, 3-head-tall super-deformed, short stout body, small hands and feet, {人物描述：身份/年龄/盔甲/配色/头盔/武器/披风/纹章}, clean pixel art, vibrant colors, sharp silhouette`
- **对着立绘走**（如果先有立绘）：盔型、盾纹章、披风、金饰都要对上，否则 sprite 和立绘打架。
- ⚠️ **PixelLab prompt 上限 1000 字符，很多时候不到 1000 也报错，务必精写**（captain rotation ≈ 616 字符）。
- 写进 `character_status.yaml` 的 `states[].prompt`。

### 步骤 1 — 跑 rotation
- `create_character_v3(description=prompt, name=...)` → 返回 `character_id` + `background_job_id`；轮询 `background-jobs/{id}` 到 completed。
- 下载 zip 解压，出一张 **8 方向对照图** 给用户。
- **生成后 QA（铁律 7）**：① 量头长是否 45–48px（`measure_head.py` 粗筛 → Aseprite 精量）；② 检查 正S/正N/侧面 三向干净。不达标 → 重出，别往下走。
- **停下来。** 等用户审方向。

### 步骤 2 — 用户审核 + 敲定 anchor（6 槽，按视觉）
- 用户逐张看（判断身体/武器**真实朝向**，不看脸、不认文件名），指定 4 个源方向 + 镜像：
  - `S` = 视觉正面（最稳）
  - `N` = 视觉背面（露盾/纹章的那张通常更好看）
  - `E` = 视觉侧向（walk 用；若没有干净近侧脸，直接复用 SE 那张）
  - `SE` = 视觉 45° 3/4（战斗用；FE 风格、表现力最好、也是 PixelLab 最稳的角度）
  - `W = mirror:E`，`SW = mirror:SE`（哪侧真图/哪侧镜像用户定）
- 写进 yaml 的 `anchor:`（6 槽）。**这一步没过，不许跑 animation。**

### 步骤 3 — 写动画 prompt（idle/walk/attack/knockback/knockout [+角色专属]）
- **通用基础动作集** = `idle / walk / attack / knockback / knockout`。角色可加专属（如 captain 的 `defense`、盾兵的 `shieldbash`）。
- 每个动画：`frame_count: 8`，`dirs`（游戏方向）、`prompt`（8 帧、F1 即动作）。
- 见 §3 的动作写法要点。

### 步骤 4 — 跑 animation（两条路径）
**路径 A：脚本生成**（`pixellab_gen_animations.py`）
- **一个动作一次 `create_animation_v3` call**（把该动作所有源方向一起提交）。
- **部分失败不重试**——完成的方向存下、失败/超时的方向跳过警告即可（反正总要人工审）。
- **取帧从每个 job 的 `last_response.images` 直接解**（9 张 rgba_bytes → `Image.frombytes('RGBA',(w,h),decode)`）落到 `animations/`。
- 镜像：按 anchor 里所有 `mirror:X` 项做（`W=flipX(E)`、`SW=flipX(SE)`）。
- ⚠️ 脚本生成的 **zip 会碎片化**（同名多 call → `walk`/`walk-<hash>`），所以**脚本路径不从 zip 组织**，job.images 就是真源。

**路径 B：网页生成**（用户在 PixelLab web 上把各方向合进一个动画）
- zip 干净 → `_refresh_download.py <Char>`（按 yaml char_id 重拉+解压 `download/`）→ `_organize_web.py <Char> idle walk ...`（从 download 按 anchor copy+改名+镜像）。
- **!!! 网页 walk 可能拆成两个文件夹**（如 `walk`[north-west] + `walk-<hash>`[east,south]）→ `_organize_web.py` 已加 **merge**：一个 action 收集所有同名/前缀文件夹、跨文件夹找源方向。
- ⚠️ **`pixellab_gen_animations.py` 每个动作开头会 `rmtree(animations/<action>)`** → 用 `--only-dirs` 补单方向会**误删同动作其它方向**。补单方向要用一次性单方向小脚本（**不 wipe**，create_animation_v3 单向 → 直接存对应 gamedir）。
- ⚠️ **动 `animations/` 的临时脚本先想清楚删了能不能恢复**：真实事故是「先 rmtree 再 copytree 旧 base」第二步失败把动画删了 —— 所幸 **API 生成的动画永远能从角色 zip 重拉回来**，重 organize 即恢复。

### 步骤 5 — 整理到角色文件夹 + 验证方向
- `download/`（原始，gitignored）、`review/`（逐帧对比图 + `_ALL_overview.png`）、`rotations/`、`animations/<action>/<S|N|E|W|SE|SW>/`。
- pixellab 向 → 我们的向**按该角色 anchor 映射**（脚本读 yaml 的 anchor，**不写死**）。
- **碎片兜底**：某源方向在规范 `<action>/` 里没有时，check/organize 会去**唯一的** `<action>-<hash>` 碎片里取；有多个碎片则报 `AMBIGUOUS` 不猜。
- 核对每动画方向齐全（idle=S,SE,SW；walk=S,N,E,W；attack/knockback/knockout=SE,SW）。

---

## 3. 动作写法要点（prompt 工程，实测）

### 3.1 通用
- **F1 直接进动作**（rotation 帧已是 idle 起始，见铁律 3）。
- 每帧写清主体动作 + 护栏：`Sword in right hand, kite shield in left hand, ... never dropped or swapped`（武器/盾每帧不丢不换手）、`no spinning, no jumping`。
- 结尾护栏：`clean pixel art, sharp silhouette`。

### 3.2 walk（要有律动）
- 强调**高抬膝 + 上下起伏(bob) + 每步重心转移 + 大跨步 + 披风摆动**、`continuous cycle, no idle pause, no sliding feet`。剑**压低不上抬**（`sword carried low, never raised`）。

### 3.3 attack（挥剑猛砍）
- F1 起手举剑过肩 → 举到头顶蓄力 → 下劈 → 顺势 → 收。`clear windup and hard impact`。

### 3.3b attack = 法师/牧师施法
- 不是扎枪：举杖蓄势 → 挥杖前送/前指 → 收。强调**身体+法杖**动作。
- **!!! 绝不烘焙 VFX**（见铁律 6）：蓝晶写 `plain unlit`，结尾堆重否定 `NO magic effects, NO glow, NO light, NO sparkles, NO flash, NO burst, NO particles — the crystal does NOT light up`。VFX 后期独立叠加。

### 3.4 !!! knockback（后仰）——最关键的实测发现
- **PixelLab 的「被打」先验是向前缩 / 前扑**（格斗受击帧多是前 flinch）。凡是用 **`smashed / violently / whips backward / knocked off his feet / falls / prone / to the ground`** 这类**灾难级 + 倒地词**，一律被掰成**向前栽**，方向词 "backward" 被无视。
- **能做出真·后仰的诀窍 = 措辞克制 + 结尾回正站立**（不倒地）。用户实测稳定的 Gemini 版：
  > Frame 1: Initial impact. Character **recoils, slightly bent backward**, expression of pain/surprise. Hands flinch, head jolts.
  > Frames 2-3: Arc of the backward lunge. Character is pushed further back, torso angled steeply, legs braced but slightly bent for balance.
  > Frames 4-5: Peak of the recoil. Most extreme backward position. May even slightly "skid" back. Torso fully arched.
  > Frames 6-7: Beginning of the return. Torso starts to straighten, head tilts back forward.
  > Frame 8: **Full return. Character is back in a stable, upright standing pose**, looking forward, recovered.
- 关键词：**"recoils / slightly bent backward"（低强度）+ "full return, upright"（回正、不倒）**；**忌** violently/smashed/fall/prone。
- 附带实测：**纯抬头（lookup）能做**；纯「上身后仰」中性词（leanback）只能做到抬头+直立、幅度小。所以「后仰」= 低强度 + 回正 才稳。

### 3.5 knockout（阵亡 / 倒地）
- 允许倒地（`falls to the ground, sprawled, defeated, does not get back up`）。PixelLab 会**向前**倒——做 KO/阵亡**可接受**。
- **!!! 简化写法（2026-07-19 定稿）**：knockout = 「**摔倒 → 趴地 → 双眼闭上不起来**」就完了。**去掉「武器散落」**（`weapon fallen near him` 之类效果不好），也**不加 `Clean pixel art` 尾巴**。最后一帧强调 `both eyes closed, not getting up`。

### 3.6 「被击退」的正确演出分工
- 想要强冲击的**击退**：sprite 用 knockback（或直立受击帧）+ **引擎位移（向后弹开）+ 屏震 + 打击特效**。**别指望 sprite 自己做大幅后飞**（跟位移会打架：人前栽、身子后飞）。
- **径向/居中特效**（爆炸/命中闪光）无朝向，任意角度通用；**定向特效**（火球飞/刀光）只活在侧视战斗场景做 1 向。

---

## 4. PixelLab API / 数据关键事实

- **rotation**：`POST /v2/create-character-v3`（从零：pixen 生南向 + v3 转 8 向）。返回 `character_id` + `background_job_id`。
- **animation**：`POST /v2/characters/animations`（mode v3）。一方向一 job，返回 `background_job_ids` + `directions`。
- **取完成帧**：`GET /v2/background-jobs/{id}` → `last_response.images`（9 张 rgba_bytes）。这是**唯一无歧义**的帧来源。
- **⚠️ 角色动画 API 不能改已有动画组**：请求体只有 `animation_name` + `directions`，**没有 `animation_group_id` / `replace_existing`**。同名重发 = **新建**动画（生成 `walk` / `walk-<hash>` 碎片）。网页 UI 能"组内加方向/重生成/镜像",**API 不行**。（对象 Objects 的 API 才有 `animation_group_id`。）
- **`group_id`**：多个 state（职业）靠共享 `group_id` 挂在同一网页。`GET /v2/characters?group_id=X` 的过滤**无效**（返回全部、分页 ~50），列一个组只能客户端自己按 group_id 过滤。
- **`keep_first_frame=false`** 可去掉自动 frame_000（只存 8 帧）——目前**不用**，保留 frame_000 作 idle 起始。
- **token**：`pixellab_gen_character` 的 `get_token` 读 `scripts/config.json` / 环境变量；但我们的 pipeline 脚本都**手动 `open('pixellabkey.txt')` 传进去**（token 在 repo 根，已 gitignore）。
- 轮询偶发 **503**，需重试（`get_job` 层重试；但动画**任务**级失败不重试，见步骤4）。

---

## 5. 目录约定

```
pixellab/
├── character_status.yaml            ← 真值源
└── characters/<id>/
    ├── download/                    ← 原始 zip + 解压件（GITIGNORED: pixellab/characters/*/download/）
    ├── review/                      ← 每动画逐帧对比 PNG（人工审）
    ├── rotations/                   ← 8 方向（pixellab 命名 south/east/north-west/...）
    └── animations/<action>/<S|N|E|W|SE|SW>/frame_000..008.png   ← 我们的方向命名（按 anchor 映射）
```

- `download/` 可随时由 `character_id` 重下，故 gitignore。
- `animations/` 的方向名**由该角色 anchor 决定**，脚本读 yaml，不写死。
- 备份旧版动画放 `animations/_backup/`。

### character_status.yaml 结构
```yaml
characters:
  - id: <UnitDisplayName>            # 内部 id
    team: enemy|ally
    group_id: <uuid|null>            # 跨 state 共享（PixelLab 组）
    portrait: art/portraits/<char>/<char>_full.png
    states:                          # 职业/形态；每个 = 独立 PixelLab character
      - state: base
        job: <class>
        prompt: >- ...               # rotation prompt（<1000 字符，精写）
        character_id: <uuid>         # 该 state 的 PixelLab id
        rotation: {status, dir}
        anchor:                        # 用户按【视觉】审核后填（6 槽）
          {S:<png>, N:<png>, E:<png>, SE:<png>, W: mirror:E, SW: mirror:SE}
        animations:
          idle:      {status, frame_count:8, dirs:[S,SE],  prompt}   # 地图S+战斗SE
          walk:      {status, frame_count:8, dirs:[S,N,E], prompt}
          attack:    {status, frame_count:8, dirs:[SE],    prompt}   # 战斗;法师=施法(§3.3b)
          knockback: {status, frame_count:8, dirs:[SE],    prompt}   # 后仰(§3.4)
          knockout:  {status, frame_count:8, dirs:[SE],    prompt}   # 倒地
          # + 角色专属（defense / shieldbash / ...）
```
- **`character_id` 在 state 层**，不在 char 层（换职业 = 新 PixelLab 生成 = 新 id）。char 层只放跨 state 不变的 id/team/group_id/portrait。

---

## 6. 脚本

| 脚本 | 用途 |
|---|---|
| `scripts/pixellab_gen_character.py` | 低层封装：`create_character_v3` / `create_animation_v3` / `get_job` / `download_character_zip` / `get_balance` / `unzip` |
| `scripts/pixellab_run_rotation.py` | 跑 rotation：读 yaml prompt → 生成 → 下载 → copy 到 `rotations/` → 出 `_contact.png` 供审 → 打印 character_id |
| `scripts/pixellab_gen_animations.py` | **路径A** 读 yaml 跑动画：一动作一 call、部分失败不重试 → 从 job.images 存帧 → 按 anchor `mirror:X` 镜像 → 出 GIF。选项 `--actions`、`--only-dirs`、`--submit-only`、`--gifs-only` |
| `scripts/pixellab_check_animations.py` | **路径B** 核对 download 是否覆盖每动作必须方向（含碎片兜底 + 帧数校验） |
| `scripts/pixellab_organize.py` | **路径B** 从 download zip 按 anchor copy+改名成我们的方向 + 镜像 + 出 review/GIF（含碎片兜底） |
| `scripts/measure_head.py` | **QA（铁律7）** 头长粗筛：读 `_head_roster.json`（每项 `{label,png,crown,chin,eye?}`，坐标=alpha-bbox-crop 空间）。`--gridsheet` 出网格表目测下线 → 填 crown/chin → `--one <label>` 出单角色叠线小图核对（<8000px，逐个来别出大图）。头长=chin−crown，另打印头身比。精确值仍以 Aseprite 为准 |

- 出图审阅：做**逐帧对比图**（每行=一个动画/方向，含 frame_000）比 GIF 更好判断动作（GIF 也可开 VS Code 直接播）。

---

## 7. 已定稿参考角色

**EmpireCaptain（帝国重甲队长 / 敌，路径B 网页生成）**
- `character_id` `e6084051-192e-4892-941e-2054a12b9d41`（no-GBA 版，无翎羽）。
- anchor（视觉）：`S=south, N=north-west(露盾+金鹰), E=east, SE=south-east, W=mirror:E, SW=mirror:SE`。**唯一 E≠SE**（有独立侧向 + 45°）。
- 动作：idle(S,SE,SW) / walk(S,N,E,W) / attack(SE,SW) / knockback(SE,SW 后仰) / knockout(SE,SW) / defense(SE,SW)。

**SuYao（苏瑶 / 我方牧师法师，路径A 脚本生成）**
- `character_id` `29bf913f-0fd6-49fc-8c4d-78259aadaef4`（8 版里选 #6；无兜帽、长银发、白金袍、蓝晶杖）。
- anchor（视觉）：`S=south, N=north, E=east, SE=east(E复用SE), W=mirror:E, SW=mirror:SE`。
- attack = **施法**（无烘焙 VFX）。
- 立绘不必被 sprite 绑死（可后期让 GPT-image 加辫子）；**别提 hood/cape**（提了必戴上，长发再钻进兜帽）。

**EmpireCavalier（帝国骑兵 / 敌，骑马长枪骑士）**
- `character_id` `1bdc21ba`（**07-20 换新**：旧 cav#2 `1debb144` 出图差、prompt 有问题 → 换成一个
  接近 EmpireHeavyCavalier 的**骑马翎盔长枪骑士**）。
- anchor（视觉）= **EmpireHeavyCavalier 的镜像**：干净 45° 帧（pixellab `south`）朝屏幕**左**，所以
  `S=east, N=west, W=south, SW=south, E=mirror:W, SE=mirror:SW`。真源方向是 W/SW，E/SE 才是 flipX。
- 动作 = 骑马版（idle/walk 马步态 + attack = 马上挺枪前刺 + knockback 马上后仰回正 + knockout 人从马上摔下），
  用新约定（无 `Clean pixel art` 尾巴、knockout 简化闭眼不散武器）。
- **选型教训**：旧批候选多是**半截枪/双枪/长枪穿模**——骑兵鲍/枪/马腿容易崩，必须逐版看、宁可重出。

---

> **一句话**：rotation → **用户按【视觉】审方向定 6 槽 anchor（S/N/E/SE + 镜像）** → 动画（F1 即动作、后仰用克制回正措辞、施法不烘焙 VFX）→ 脚本路径从 job.images 存帧 / 网页路径 pull-check-organize → 按 anchor 镜像 → 落 `pixellab/characters/<id>/`。方向 mapping **永远由用户拍板、按视觉不认文件名**，AI 不预设。
