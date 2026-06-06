# PixelLab 角色 Prompt 总览

> **文档目的**：整合陆离 / 苏瑶 / 帝国兵三个角色在 PixelLab 上**已验证有效**的全部 prompt，供后续角色生成 + 现有角色重做使用。
> **状态日期**：2026-06-06（基于 5/31 + 6/1 实验数据）
> **来源**：`art/characters/*/metadata.json`（rotation prompts）+ `docs/conversation-till-june6.md`（动画 prompts 从对话记录里挖出来的）

---

## ✅ 数据完整性

| 类别 | 数量 | 状态 |
|---|---|---|
| Rotation prompts | 3 | ✅ 完整（`metadata.json` 存盘） |
| Attack 动画 prompts（Custom V3） | 3 | ✅ 完整（对话记录恢复） |
| Idle / Walking / Reaction 动画 prompts | 9 | ✅ 完整（对话记录恢复，2026-06-06 找回） |

**恢复方法**：把整个 VS Code Copilot Chat 的 JSONL transcript 转成 markdown 存到 `docs/conversation-till-june6.md`（13421 行 / 680KB），然后按"文件夹名前缀就是 prompt 第一句"的规律 grep 出每个 prompt 的全文。原则：**同一动画出现多次时取最后一个**（对话里反复打磨，最后一版才是实际投到 PixelLab 的）。

---

## 一、全局设置（所有角色锁定）

| 项 | 值 | 备注 |
|---|---|---|
| Tier | Tier 1（$12/月，2000 gen/月） | 单月预算充足 |
| Sprite Size | 48px | 角色本体尺寸 |
| Canvas Size | 92×92（陆离/苏瑶）/ 96×96（帝国兵） | PixelLab 自动 padding 给动画位移空间 |
| Camera View | Low Top-Down | SRPG 标准视角 |
| Generation Mode | **v3** | 不用 Standard |
| Template | Humanoid (mannequin) | 全角色统一 |
| Directions | 8（生成全套） | Unity 内 WEST 用 `flipX` 复用 EAST，但**生成时还是 8 全做**便于审查 |
| Animation Mode | **Custom V3**（统一） | 6/1 教训：预设 Idle/Walking/Reaction 对持械角色 E/W 容错差，全部改 Custom V3 |
| Frames | **8 帧标准**（实际文件 F0-F8 共 9 个） | 勾 "Keep First Frame" |
| Keep First Frame | **勾上** | F0 = rotation 参考帧，F1-F8 = 动画 |

### Style anchor（rotation prompt 必含）

```
Fire Emblem GBA style [archetype], western fantasy, [description],
clean pixel art, sharp silhouette
```

实验验证（5/31 spike）：加此锚点 → 3 角色头身比/渲染风格一致；没加 → 出现"粉发弓箭手"Q版离群。

---

## 二、Rotation Prompts（角色定义）

所有 rotation prompt 都已存入 `art/characters/<character>/metadata.json` 的 `.states[0].character.prompt`。

### 2.1 陆离（Hero Swordsman）

- **Character folder**: `LuLi/Fire_Emblem_GBA_style_hero/`
- **Canvas**: 92×92
- **配色**: 银 + 蓝（我方阵营标准色）

```
Fire Emblem GBA style hero swordsman, western fantasy,
balanced fighter not heavy,
brown short messy hair,
light silver plate armor with leather straps, blue cape,
one-handed longsword sheathed on back, confident posture,
young man early 20s,
clean pixel art, vibrant colors, sharp silhouette
```

### 2.2 苏瑶（Female Mage / Cleric）

- **Character folder**: `SuYao/Fire_Emblem_GBA_style_female/`
- **Canvas**: 92×92
- **配色**: 白 + 蓝 + 金（我方法师标识）

```
Fire Emblem GBA style female mage cleric, western fantasy,
gentle elegant pose,
long silver hair flowing past waist,
white and blue robe with gold trim,
hood down, wooden staff with blue crystal,
young woman early 20s,
soft features, clean pixel art, vibrant colors, sharp silhouette
```

**已知陷阱**：早期版本 hood-up 容易让 E/W 视角变成"修女/幽灵"造型。**`hood down` 必须保留**且 6/1 已验证全 4 方向稳定。

### 2.3 帝国兵（Empire Axe Soldier）

- **Character folder**: `EmpireAxeSoldier/Fire_Emblem_GBA_style_enemy/`
- **Canvas**: 96×96
- **配色**: 青绿 + 黄铜 + 暗钢（杂兵敌方阵营，参考幻世录 Langrisser）

```
Fire Emblem GBA style enemy soldier, european medieval fantasy,
generic imperial foot trooper,
stocky stern soldier in his 30s with stubble and grim face partially visible,
dark teal green tabard over chainmail and dull steel plate armor,
classic western soldier style,
brass and leather trim accents,
open-faced steel nasal helmet (kettle hat style) with no horns and no plume,
large round wooden shield painted teal green with iron rim and central iron boss,
single-handed steel battle axe in right hand,
clean pixel art, sharp silhouette
```

**历史教训**：第 1 版用 `dark crimson and black armor + horned helmet` → 出来日式武将（红甲带角，类似战国武士）。诊断：`horned / crimson / plume` 在 SD 训练集里和"Samurai/武将"高度耦合。第 2 版改成上面这个西式锚定 + 平顶钢盔 prompt → 6/1 验证全方向稳定。

---

## 三、动画 Prompts（全部 Custom V3，全部恢复全文）

所有动画都是 **8 帧 + Keep First Frame** 设置（实际文件 F0-F8 共 9 个）。

---

### 3.1 陆离（LuLi）

#### Idle — Breathing Pose
**Folder**: `Hero_stands_in_idle_breathing_pose._F1_idle_stance-cd42d21c/`

```
Hero stands in idle breathing pose.
F1: idle stance, longsword sheathed on back, hands at sides.
F2-3: chest rises with breath, shoulders lift slightly.
F4: peak inhale, body slightly taller, cape settles.
F5-6: chest falls, shoulders settle.
F7: deepest exhale.
F8: returns to neutral idle.
Feet stay planted, no walking, no spinning.
Sword stays sheathed on back visible every frame, never drawn.
Blue cape sways gently.
Brown messy hair. Silver plate armor with leather straps.
Cape and sword stay identical across all frames.
Clean pixel art, sharp silhouette.
```

#### Walking — Steady Step Forward
**Folder**: `Hero_walks_forward_in_a_steady_step._F1_idle_longs-71a3d5b1/`

```
Hero walks forward in a steady step.
F1: idle, longsword sheathed on back, hands at sides.
F2: right foot lifts slightly, cape flows.
F3: right foot peak lift.
F4: right foot plants forward.
F5: left foot lifts slightly.
F6: left foot peak lift.
F7: left foot plants forward.
F8: returns to idle.
Sword stays sheathed on back, visible every frame, never drawn.
Blue cape flows with steps.
Brown messy hair. Silver plate armor with leather straps.
No spinning, no jumping.
Cape and sword design stay identical across all frames.
Clean pixel art, sharp silhouette.
```

#### Attack — Horizontal Sword Slash
**Folder**: `Character_raises_sword_from_idle_stance_up_and_bac-647ec2ed/`

```
Character raises sword from idle stance up and back over right shoulder to wind up,
then swings the sword in a strong diagonal arc downward across the body from upper-right to lower-left,
leaning forward with body weight during the slash,
then settles back to a balanced ready stance with sword held forward.
Powerful one-handed sword slash, clear motion with no spinning or jumping,
feet stay planted on ground.
```

**关键点拆解**（供新动作复用）：

| 元素 | 作用 |
|---|---|
| `raises sword ... wind up` | 起手蓄力（F2-3） |
| `swings in a strong diagonal arc downward` | 主挥砍命中帧（F4-5） |
| `leaning forward ... body weight` | 重心前移给打击感 |
| `settles back to a balanced ready stance` | 收招（F7-8） |
| `no spinning or jumping` + `feet stay planted` | 硬护栏，否则 AI 会脑补跳劈 |

#### Reaction — Take a Hit and Recoil
**Folder**: `Hero_takes_a_hit_and_recoils_sharply._F1_idle_stan-9d09519f/`

```
Hero takes a hit and recoils sharply.
F1: idle stance, hands at sides.
F2: struck, body jolts backward, head tilts back, arms fling out for balance.
F3: deeper recoil, leaning back, cape flares from impact.
F4: peak recoil, body fully leaned back, eyes closed in pain.
F5: starts to recover, body returns toward upright.
F6: arms settle back.
F7: nearly back to idle.
F8: full idle stance restored.
Feet stay planted, no falling, no spinning.
Sword stays sheathed on back every frame, never dropped.
Blue cape flows with motion.
Exaggerated reaction, clear visible flinch, clean pixel art.
```

**实际结果**：N/S 戏剧（下蹲拔剑应激防御）；E/W 退化成"boxer guard"（双手护头），剑入鞘。E/W 用 Unity 闪白+震屏+飘字补强。

---

### 3.2 苏瑶（SuYao）

#### Idle — Mage Breathing Stance
**Folder**: `Mage_stands_in_idle_breathing_pose._F1_idle_stance-7a173933/`

```
Mage stands in idle breathing pose.
F1: idle stance, staff held vertically in right hand at side, hood down.
F2-3: chest gently rises with breath, shoulders lift slightly, hair stirs faintly.
F4: peak inhale, body slightly taller.
F5-6: chest gently falls, shoulders settle.
F7: deepest exhale.
F8: returns to neutral idle.
Feet stay planted, no walking, no spinning.
Gold staff with large blue orb held in right hand visible every frame, never disappears, never dropped.
Hood stays down showing face and silver hair, never goes up.
Clean pixel art, sharp silhouette.
```

#### Walking — Walk Holding Staff
**Folder**: `Mage_walks_forward_holding_staff._F1_idle_gold_sta-f2161e4c/`

```
Mage walks forward holding staff.
F1: idle, gold staff vertical in right hand, hood down.
F2: right foot lifts slightly, robe flows.
F3: right foot peak lift.
F4: right foot plants forward.
F5: left foot lifts slightly.
F6: left foot peak lift.
F7: left foot plants forward.
F8: returns to idle.
Hood stays down every frame showing silver hair and face.
White-blue robe with gold trim flows with steps.
No spinning, no jumping.
Staff visible every frame, never dropped.
Staff stays identical across all frames: golden haft, large round glowing blue orb on top.
Clean pixel art, sharp silhouette.
```

#### Attack — Spell Cast with Staff
**Folder**: `Character_casts_a_magic_spell_with_her_staff._Fram-79cc4982/`

```
Character casts a magic spell with her staff.
Frame 1: idle stance holding staff vertical at side.
Frame 2-3: she raises the staff above her head with both hands, leaning slightly back, gathering magical energy.
Frame 4: staff held high at peak, orb glows brightly, free hand extends forward with open palm toward the target.
Frame 5-6: she thrusts the staff forward and down with a strong casting motion, releasing the spell, body leans forward with the cast.
Frame 7-8: she pulls staff back to vertical resting position at her side, returning to idle.
Feet stay planted on the ground throughout, no spinning, no jumping, no walking.
Staff and orb remain clearly visible in every frame.
Robe and hood flow naturally with the casting motion.
Smooth weighted casting animation, clean pixel art.
```

**关键点**：
- 强调 `casting` 而非 `swinging`，否则 AI 会让她拿杖当棍子打
- `orb glows brightly` 在 peak 帧加发光，是法师标志（PixelLab 自带打击特效）
- `free hand extends forward with open palm` — 真正的"出招"判定帧
- 法术节奏：蓄力(F2-4) → 释放(F5-6) → 收势(F7-8)，比挥剑慢一点

#### Reaction — Mage Recoils
**Folder**: `Mage_takes_a_hit_and_recoils_sharply._F1_idle_stan-bf723c7a/`

```
Mage takes a hit and recoils sharply.
F1: idle stance, staff vertical in right hand.
F2: struck, body jolts backward, head tilts back, staff swings up.
F3: deeper recoil, leaning back, staff tilted, free arm flings out for balance.
F4: peak recoil, body fully leaned back.
F5: starts to recover, body returns toward upright.
F6: staff settles back down toward vertical.
F7: nearly back to idle.
F8: full idle stance restored.
Feet stay planted, no falling, no spinning.
Gold staff with large blue orb held in right hand visible every frame, never dropped.
Hood stays down. Exaggerated reaction, clean pixel art.
```

---

### 3.3 帝国兵（EmpireAxeSoldier）

#### Idle — Soldier Breathing
**Folder**: `Soldier_stands_in_idle_breathing_pose._F1_idle_sta-c1653f01/`

```
Soldier stands in idle breathing pose.
F1: idle stance, battle axe held in right hand at side, round shield raised in left hand at chest.
F2-3: chest gently rises with breath, shoulders lift slightly.
F4: peak inhale, body slightly taller.
F5-6: chest gently falls, shoulders settle.
F7: deepest exhale.
F8: returns to neutral idle.
Feet stay planted, no walking, no spinning.
Battle axe in right hand and round shield in left hand both visible every frame, never disappear, never dropped, never swapped.
Kettle hat helmet stays on head. Teal green tabard over chainmail.
Clean pixel art, sharp silhouette.
```

#### Walking — Soldier Marches Forward Armed
**Folder**: `Soldier_marches_forward_armed._F1_idle_steel_axe_i-edb65a67/`

```
Soldier marches forward armed.
F1: idle, steel axe in right hand at side, round teal shield in left hand at chest.
F2: right foot lifts slightly, weight on left.
F3: right foot peak lift, knee bent.
F4: right foot plants forward.
F5: left foot lifts slightly.
F6: left foot peak lift.
F7: left foot plants forward.
F8: returns to idle.
Kettle hat stays on head. Teal tabard sways with steps.
No spinning, no jumping.
Axe and shield visible every frame, never dropped or swapped.
Axe stays identical across all frames: single-bladed steel head, wooden haft.
Shield stays identical: round, teal face, iron rim, central boss.
Clean pixel art, sharp silhouette.
```

#### Attack — Heavy Overhead Chop
**Folder**: `Soldier_swings_battle_axe_in_heavy_overhead_chop.-0e547b83/`

```
Soldier swings battle axe in heavy overhead chop.
F1: idle, axe at right side, round shield raised in left hand at chest.
F2-3: lifts axe up and back over right shoulder, winding up, weight on back foot, shield stays up.
F4: axe at peak overhead, body coiled.
F5: swings axe down and forward in vertical chop, weight shifts forward.
F6: axe at bottom, fully extended forward, body leaned in.
F7-8: pulls axe back up to side, returns to idle.
Feet planted, no spinning, no jumping.
Shield stays in left hand throughout, never dropped.
Axe and shield visible every frame. Heavy weighted swing.
```

**6/1 实际效果**：自带青色 motion blur 拖影（PixelLab Custom V3 隐藏 buff），Unity 不用再加打击特效。

#### Reaction — Soldier Recoils
**Folder**: `Soldier_takes_a_hit_and_recoils_sharply._F1_idle_s-5e2c468d/`

```
Soldier takes a hit and recoils sharply.
F1: idle stance, axe in right hand, shield in left hand at chest.
F2: struck, body jolts backward, head tilts back, shield raises to brace.
F3: deeper recoil, leaning back, axe arm flings out for balance.
F4: peak recoil, body fully leaned back.
F5: starts to recover, body returns toward upright.
F6: arms settle back.
F7: nearly back to idle.
F8: full idle stance restored.
Feet stay planted, no falling, no spinning.
Battle axe in right hand and round shield in left hand both visible every frame, never dropped.
Exaggerated reaction, clean pixel art.
```

**6/1 实际效果**：AI 解读为"举盾防御"而非"身体后退"。对盾兵来说**合理**（重甲杂兵"打不动"的视觉直觉），保留不修。

---

## 四、通用 Custom V3 模板（生成新角色用）

### 4.1 结构模板（5/31 + 6/1 验证）

```
[一句话总结动作]
F1: [起始姿势，明确武器位置]
F2-3: [起动 / 蓄力]
F4: [动作峰值]
F5-6: [发力 / 释放]
F7-8: [收势 / 回到 idle]

Feet stay planted, no walking, no spinning, no jumping.
[武器约束：weapon X visible every frame, never dropped, never disappears]
[服装约束：例 "Hood stays down" / "Cape flows with motion"]
[一致性约束：weapon stays identical across all frames]
Clean pixel art, sharp silhouette.
```

### 4.2 字符限制与压缩

- PixelLab Custom V3 prompt 字符上限 **1000**，建议 ≤ 600 留余量
- **优先用长形式**（`Frame 1:` 比 `F1:` 详细），6/1 实测长形式效果更稳定
- 真的撑爆 1000 时再压缩：
  - 完整句变短语（`he lifts` → `lifts`）
  - `Frame 1` → `F1`
  - 同类禁令合并一行

### 4.3 Prompt 写作铁律（验证过的）

| 教训 | 例子 |
|---|---|
| 否定词不可靠 | `no horns` 弱，AI 仍画出角 |
| 用正向替换否定 | ✅ `plain steel kettle hat helmet` 替代 `no horns` |
| 文化锚定强于装饰词 | ✅ `european medieval` + `classic western` 比单纯描述配色更稳 |
| 配色与文化绑定 | crimson + horned → 日式；teal/brass → 西式 |
| 重复关键词增加权重 | `axe and shield visible every frame` 比只在开头说一次更稳 |
| 武器位置每帧明确 | ❌ `attacks with sword` → ✅ `F4: sword at peak overhead, body coiled` |
| **强制视觉一致性** | `staff stays identical across all frames` / `axe stays identical: single-bladed steel head` 防 AI 中途换武器 |
| **Reaction 必须 `exaggerated`** | 否则 AI 按"现实主义"出几乎看不出的轻反应 |

---

## 五、关键经验

### 5.1 预设模板 ≠ Custom V3（6/1 关键发现）

- **PixelLab 预设 Idle / Walking / Reactions** 对持械角色（带剑/法杖/盾）E/W 容错差，会丢武器或简化造型
- **解决**：所有持械动画**都用 Custom V3 + 详细分镜 + 武器约束**
- **代价**：每个动画 prompt 要写 ~400-600 字符，但风格 + 武器可控
- **例外**：完全裸手的人型（村民、NPC）可以用预设

### 5.2 "Keep First Frame" 的双刃剑

- **勾上**（推荐）：得到 9 帧（F0-F8），F0 = rotation 模板原图
- **F0 视角跳变陷阱**：E/W 的 F0 是纯侧视，F1-F8 是 3/4 view → 循环播放会"咔哒"
- **Unity 解法**：E/W 动画切片只用 F1-F8（8 帧循环），N/S 用 F0-F8（9 帧）
- 详见 spec §5.7 + 6/1 dev log §4.2

### 5.3 Rotation 是基础设施

- **rotation 错 → 所有方向的所有动画都错**
- 流程：先生成 rotation → 8 方向逐张验收 → 再做动画
- 如果某方向 rotation 不行，先修 rotation，再重做该方向所有动画

### 5.4 逐帧人工审查不可省

- 5/31 之前的脑补"top-down 看不出"被自己打脸过
- 6/1 验收标准：5 帧/方向（F0/F2/F4/F6/F8）× 4 方向 = 20 帧/动画
- 单批 ≤ 20 张（view_image API 上限）

### 5.5 PixelLab 局限与游戏补强分工

| PixelLab 弱项 | Unity 补强方案（FE/Langrisser 标准） |
|---|---|
| Reaction 反应仍偏轻（E/W 尤其） | 闪白 shader（0.05s 全身白）+ 后退 tween（4-6 px，0.1s 回弹）+ 镜头微震 + 红色伤害飘字 |
| 命中无打击感 | hit-stop（0.05s 暂停）+ 粒子爆点 |
| 法术无投射物 | F4（orb 最亮帧）触发独立粒子/弹道 GameObject |
| 死亡无动画 | 用 Reaction 最后一帧 + 黑白渐变 + 像素消散粒子（M2 加） |

### 5.6 Prompt 不要再丢失

**教训**：6/1 当天动画 prompt 没存档，6/6 靠 grep VS Code transcript 才找回。**规则**：从今天起，**所有 PixelLab prompt 投出去之前先粘贴进 git**。可选地点：
- 本 doc §3（更新 prompt 时直接覆盖对应章节）
- 或建 `prompts-archive/<date>-<character>-<animation>.txt`

---

## 六、配色阶层（spec §5.1 同步）

| 阵营 | 主色 | 辅色 | 用途 |
|---|---|---|---|
| 我方 | 银 | 蓝 | 陆离、基友 |
| 我方法师 | 白 + 蓝 | 金 | 苏瑶 |
| 杂兵敌方 | 青绿 | 黄铜 + 暗钢 | 帝国兵（参考幻世录 Langrisser） |
| 精英敌方 | 深红 | 金 | 帝国骑兵长官（M2+ 角色） |
| 中立 | 棕 | 米色 | 平民、NPC |

---

## 七、后续 TODO

- [x] ~~找回 6/1 丢失的 9 个动画 prompt~~ — 已完成（6/6 用 transcript grep）
- [ ] 6/7 起：所有动画生成**当场把完整 prompt 复制粘贴存档**（贴到本 doc §3 取代旧版，或建 `prompts-archive/<date>-<character>-<animation>.txt`）
- [ ] 新角色（精英敌方 / 平民 / 队友 2）走本 doc §2 + §4 模板
- [ ] 把本 doc 引用关系登记到 spec `docs/specs/2026-05-24-fantacy-centry-unity-design.md` §5
