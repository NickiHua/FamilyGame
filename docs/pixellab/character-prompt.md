# PixelLab 角色 Prompt 总览

> **文档目的**：整合陆离 / 苏瑶 / 帝国兵三个角色在 PixelLab 上**已验证有效**的全部 prompt，供后续角色生成 + 现有角色重做使用。  
> **状态日期**：2026-06-06（整理于 6/6，基于 5/31 + 6/1 实验数据）  
> **来源**：5/31 dev log §3 + 6/1 dev log §4 + `art/characters/*/metadata.json`（rotation prompts）

---

## ⚠️ 数据完整性说明

| 类别 | 数量 | 是否有全文 |
|---|---|---|
| Rotation prompts | 3 | ✅ 全部完整（`metadata.json` 存盘） |
| Attack 动画 prompts（Custom V3） | 3 | ✅ 全部完整（5/31 文档保留） |
| **Idle / Walking / Reaction 6/1 重做版 prompts** | **9** | ❌ **全文未存档**，只有文件夹名前 ~50 字 |

**为什么动画 prompt 丢了**：`metadata.json` 只存 character（rotation）的 prompt，不存 animation 的 prompt。6/1 当天在 PixelLab Web UI 输入的动画 prompt 没单独保存到 git。

**补救**：对每个丢失 prompt 给出：
1. 已知部分（文件夹名前缀 ≈ prompt 第一句）
2. 基于 6/1 验证方法 + 5/31 §4.3 结构的**可复刻模板**（拿这个去重新生成会得到风格一致的结果，但**不保证 byte-for-byte 复现 6/1 那一版**）

如果以后还要查 6/1 原版，去 PixelLab Web Dashboard → 历史记录里翻 2026-06-01 当天的生成记录。

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
| Animation Mode | **Custom V3**（统一） | 不再用 Idle/Walking/Reaction 预设（6/1 教训：预设对持械角色 E/W 容错差） |
| Frames | **8 帧标准**（实际文件 F0-F8 共 9 个） | 勾 "Keep First Frame" |
| Keep First Frame | **勾上** | F0 = rotation 参考帧，F1-F8 = 动画 |

### Style anchor（所有 prompt 必含）

```
Fire Emblem GBA style [archetype], western fantasy, [description],
clean pixel art, sharp silhouette
```

实验验证（5/31 spike）：加此锚点 → 3 角色头身比/渲染风格一致；没加 → 出现"粉发弓箭手"Q版离群。

---

## 二、Rotation Prompts（角色定义）

所有 rotation prompt 都已存入 `art/characters/<character>/metadata.json` 的 `.states[0].character.prompt`，下面是格式化后的全文。

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

## 三、Animation Prompts

### 3.1 Attack（Custom V3）— ✅ 全文已存档

#### 陆离 Attack — Horizontal Sword Slash

- **文件夹**: `Character_raises_sword_from_idle_stance_up_and_bac-647ec2ed/`
- **6/1 状态**: ✅ 9/9 帧剑可见，蓄→劈→收节奏好（与 5/31 同 prompt）

```
Character raises sword from idle stance up and back over shoulder,
winds up, then swings down in horizontal slash across body,
body weight shifts forward with the swing, returns to idle.
Feet stay planted, no spinning, no jumping.
Sword visible every frame.
```

#### 帝国兵 Attack — Heavy Overhead Chop

- **文件夹**: `Soldier_swings_battle_axe_in_heavy_overhead_chop.-0e547b83/`
- **6/1 状态**: ✅ 全方向，自带青色 motion blur 拖影（PixelLab Custom V3 隐藏 buff）

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

#### 苏瑶 Attack — Spell Cast with Staff

- **文件夹**: `Character_casts_a_magic_spell_with_her_staff._Fram-79cc4982/`
- **6/1 状态**: ✅ orb 巨大发光，N/S 戏剧拉满（可作为宣传图）
- **⚠️ 注意**：文件夹名第一个词是 `Character`（不是 `Mage`），与 5/31 §3.2 文档版略有出入。6/1 实际用的 prompt 可能微调过，下面是 5/31 文档版（基础结构正确，复刻够用）：

```
Mage casts spell with staff.
F1: idle, staff vertical at side.
F2-3: raises staff above head with both hands, leans slightly back, gathering energy.
F4: staff at peak overhead, orb glows brightly, free hand extends forward palm open toward target.
F5-6: thrusts staff forward and down in strong cast, body leans forward, releasing the spell.
F7-8: pulls staff back to vertical rest at side, returns to idle.
Feet planted, no spinning, no jumping, no walking.
Staff and orb visible every frame.
Robe and hood flow with motion.
Smooth weighted casting, clean pixel art.
```

复刻时可把开头 `Mage` 换成 `Character`（与文件夹名一致）。

---

### 3.2 Idle / Walking / Reaction — ⚠️ 6/1 全文未存档，提供文件名片段 + 复刻模板

> 以下 9 套 prompt 在 6/1 全部从预设切换到 **Custom V3**，并按 5/31 §4.3 结构 + 6/1 强化点（3/4 view + 武器重复约束）写。实际文本未存档，下面给"片段 + 模板"。

#### 6/1 强化点（所有动画都加）

每个 prompt 都包含这些约束：
1. `3/4 front view, not pure side profile` — 强制 E/W 用 3/4 视角而非纯侧视
2. **每帧明确武器位置**（F1: ... F8: ...）
3. 末尾重复 `Weapon visible every frame, never dropped, never hidden`
4. `Feet planted, no spinning, no jumping` 硬护栏
5. 风格收尾 `clean pixel art, sharp silhouette`

---

#### 陆离 Idle — Breathing Stance

- **文件夹**: `Hero_stands_in_idle_breathing_pose._F1_idle_stance-cd42d21c/`
- **已知开头**: `Hero stands in idle breathing pose. F1 idle stance ...`
- **6/1 状态**: ✅ 全 4 方向稳定，剑稳定挂背

**复刻模板**：
```
Hero stands in idle breathing pose.
F1: idle stance, longsword sheathed on back, arms relaxed at sides, weight on both feet.
F2-3: chest rises slightly with breath, shoulders lift, cape stirs gently.
F4: peak inhale, chest fully expanded.
F5-6: chest falls back down, shoulders settle.
F7-8: return to F1 pose, micro-sway for loop continuity.
3/4 front view, not pure side profile.
Feet planted, no spinning, no jumping, no walking.
Sword sheathed and visible on back every frame.
Subtle breathing only, minimal motion. Clean pixel art, sharp silhouette.
```

#### 陆离 Walking — Steady Step Forward

- **文件夹**: `Hero_walks_forward_in_a_steady_step._F1_idle_longs-71a3d5b1/`
- **已知开头**: `Hero walks forward in a steady step. F1 idle longs[word ...]`
- **6/1 状态**: ✅ 优秀，腿交替清晰，披风飘，剑稳

**复刻模板**：
```
Hero walks forward in a steady step.
F1: idle, longsword sheathed on back, feet together.
F2: right leg lifts forward, left foot planted.
F3: right foot lands, weight shifts forward.
F4: left leg lifts forward, body upright.
F5: left foot lands, hips level.
F6: right leg lifts again (cycle midpoint).
F7-8: complete step cycle and return to F1.
Cape flows with each step. Arms swing naturally counter to legs.
3/4 front view, not pure side profile.
No spinning, no jumping.
Sword sheathed on back, visible every frame.
Clean pixel art, sharp silhouette.
```

#### 陆离 Reaction — Take a Hit and Recoil

- **文件夹**: `Hero_takes_a_hit_and_recoils_sharply._F1_idle_stan-9d09519f/`
- **已知开头**: `Hero takes a hit and recoils sharply. F1 idle stan[ce ...]`
- **6/1 状态**: ⚠️ E/W 被 AI 解读为"boxer guard"（双手护头），剑入鞘；N/S 戏剧（下蹲拔剑应激防御）

**复刻模板**（含 E/W 修正尝试）：
```
Hero takes a hit and recoils sharply.
F1: idle stance, longsword sheathed on back.
F2: hit impact, body twists away from impact, head jerks back.
F3-4: recoil peak, body leaned back, one foot stepped back, one arm raised defensively.
F5: brief stagger, hand on sword hilt as if drawing.
F6-7: recover, return to balanced stance.
F8: back to idle.
3/4 front view, not pure side profile.
Do not boxer guard, do not raise both fists.
Hand reaches for sword hilt during recoil. Sword visible on back every frame.
Feet planted, no spinning, no jumping. Clean pixel art, sharp silhouette.
```

---

#### 苏瑶 Idle — Mage Breathing Stance

- **文件夹**: `Mage_stands_in_idle_breathing_pose._F1_idle_stance-7a173933/`
- **已知开头**: `Mage stands in idle breathing pose. F1 idle stance ...`
- **6/1 状态**: ✅ **修复**（5/31 痛点：E/W 兜帽 + 丢杖 → 修女幽灵）

**复刻模板**：
```
Mage stands in idle breathing pose.
F1: idle stance, wooden staff with blue crystal held vertically in right hand beside body, hood down, free hand at side.
F2-3: chest rises with breath, robe sways gently, staff stays vertical.
F4: peak inhale, robe lifts slightly.
F5-6: chest falls, robe settles.
F7-8: return to F1.
3/4 front view, not pure side profile.
Hood always down showing face and long silver hair.
Staff with blue crystal visible in right hand every frame, never dropped, never hidden behind body.
Feet planted, no spinning, no jumping. Subtle breathing only.
Clean pixel art, sharp silhouette.
```

#### 苏瑶 Walking — Walk Holding Staff

- **文件夹**: `Mage_walks_forward_holding_staff._F1_idle_gold_sta-f2161e4c/`
- **已知开头**: `Mage walks forward holding staff. F1 idle gold sta[ff ...]` （注：folder 写 `gold staff`，可能是 6/1 加的视觉强调；rotation 是 `wooden staff with blue crystal`，prompt 里可能也用了"gold staff with blue orb"作为强化）
- **6/1 状态**: ✅ **修复**，杖全帧可见

**复刻模板**：
```
Mage walks forward holding staff.
F1: idle, gold staff with large glowing blue orb held vertically in right hand, hood down.
F2: right leg lifts forward, staff still vertical at side.
F3: right foot lands, weight shifts.
F4: left leg lifts.
F5: left foot lands.
F6: right leg lifts (cycle midpoint).
F7-8: complete cycle, return to F1.
Robe and long silver hair flow with each step.
3/4 front view, not pure side profile. Hood always down.
Staff with blue orb in right hand visible every frame, never dropped.
No spinning, no jumping. Clean pixel art, sharp silhouette.
```

#### 苏瑶 Reaction — Mage Recoils

- **文件夹**: `Mage_takes_a_hit_and_recoils_sharply._F1_idle_stan-bf723c7a/`
- **已知开头**: `Mage takes a hit and recoils sharply. F1 idle stan[ce ...]`
- **6/1 状态**: ✅ **修复**，杖在手举起防御，N/S 戏剧

**复刻模板**：
```
Mage takes a hit and recoils sharply.
F1: idle stance, staff vertical in right hand, hood down.
F2: impact, body twists away, head jerks back.
F3-4: recoil peak, leans back, staff raised across body as defensive guard, free hand up.
F5: stagger, weight on back foot.
F6-7: recover, staff lowers back toward vertical.
F8: return to idle.
3/4 front view, not pure side profile. Hood always down.
Staff visible in right hand every frame, never dropped.
Feet planted, no spinning, no jumping. Clean pixel art, sharp silhouette.
```

---

#### 帝国兵 Idle — Soldier Breathing

- **文件夹**: `Soldier_stands_in_idle_breathing_pose._F1_idle_sta-c1653f01/`
- **已知开头**: `Soldier stands in idle breathing pose. F1 idle sta[nce ...]`
- **6/1 状态**: ✅ **修复**，斧+盾全方向可见

**复刻模板**：
```
Soldier stands in idle breathing pose.
F1: idle stance, steel battle axe in right hand at side, round teal shield in left hand at chest level, kettle hat helmet on head.
F2-3: chest rises with breath under chainmail and plate, shoulders lift slightly.
F4: peak inhale.
F5-6: chest falls, body settles.
F7-8: return to F1.
3/4 front view, not pure side profile.
Axe in right hand and shield in left hand both visible every frame, never dropped, shield does not cover face or axe.
Feet planted, no spinning, no jumping. Heavy stoic posture, subtle breathing only.
Clean pixel art, sharp silhouette.
```

#### 帝国兵 Walking — Soldier Marches Forward Armed

- **文件夹**: `Soldier_marches_forward_armed._F1_idle_steel_axe_i-edb65a67/`
- **已知开头**: `Soldier marches forward armed. F1 idle steel axe i[n right hand ...]`
- **6/1 状态**: ✅ **修复**，斧全帧可见

**复刻模板**：
```
Soldier marches forward armed.
F1: idle, steel axe in right hand at side, round teal shield in left hand at chest.
F2: right leg lifts forward, weapons stable.
F3: right foot lands, heavy step.
F4: left leg lifts.
F5: left foot lands.
F6: right leg lifts again (cycle midpoint).
F7-8: complete cycle, return to F1.
Tabard sways with each step. Heavy weighted march.
3/4 front view, not pure side profile.
Axe in right hand and shield in left hand both visible every frame, never dropped.
No spinning, no jumping. Clean pixel art, sharp silhouette.
```

#### 帝国兵 Reaction — Soldier Recoils

- **文件夹**: `Soldier_takes_a_hit_and_recoils_sharply._F1_idle_s-5e2c468d/`
- **已知开头**: `Soldier takes a hit and recoils sharply. F1 idle s[tance ...]`
- **6/1 状态**: ⚠️ AI 解读为"举盾防御"而非"身体后退"。**对盾兵来说合理**（重甲杂兵"打不动"的视觉直觉），保留

**复刻模板**：
```
Soldier takes a hit and recoils sharply.
F1: idle stance, axe in right hand, shield in left hand at chest.
F2: impact, body twists slightly, shield raises higher to block.
F3-4: recoil peak, shield fully raised in front of face, axe pulled back, one foot stepped back.
F5: stagger, weight on back foot.
F6-7: recover, shield lowers back to chest.
F8: return to idle.
3/4 front view, not pure side profile.
Axe and shield both visible every frame, never dropped.
Feet planted, no spinning, no jumping. Heavy weighted recoil.
Clean pixel art, sharp silhouette.
```

---

## 四、通用 Custom V3 模板（用于生成新角色）

### 4.1 结构模板（5/31 §4.3 验证 + 6/1 强化）

```
[一句话总结动作]
F1: [起始姿势，明确武器位置]
F2-3: [起动 / 蓄力]
F4: [动作峰值]
F5-6: [发力 / 释放]
F7-8: [收势 / 回到 idle]

3/4 front view, not pure side profile.
[特定动作约束，如 "Feet planted, no spinning, no jumping"]
[武器约束：Weapon X in [hand], visible every frame, never dropped, never hidden]
[服装约束：例 "Hood always down" / "Cape flows with motion"]
Clean pixel art, sharp silhouette.
```

### 4.2 字符限制与压缩

- PixelLab Custom V3 prompt 字符上限 **1000**，建议 ≤ 600 留余量
- 压缩技巧：
  - 完整句变短语（`he lifts` → `lifts`）
  - `Frame 1` → `F1`
  - 同类禁令合并一行
  - 删弱形容词，留最强的

### 4.3 Prompt 写作五条铁律（5/31 §4.2 + 6/1 验证）

| 教训 | 例子 |
|---|---|
| 否定词不可靠 | `no horns` 弱，AI 仍画出角 |
| 用正向替换否定 | ✅ `plain steel kettle hat helmet` 替代 `no horns` |
| 文化锚定强于装饰词 | ✅ `european medieval` + `classic western` 比单纯描述配色更稳 |
| 配色与文化绑定 | crimson + horned → 日式；teal/brass → 西式 |
| 重复关键词增加权重 | `axe and shield visible every frame` 比只在开头说一次更稳 |
| **武器位置必须每帧明确** | ❌ `attacks with sword` → ✅ `F4: sword at peak overhead, body coiled` |
| **强制 3/4 view** | E/W 不写 `3/4 front view` 会变纯侧视 → 易丢武器 |

---

## 五、关键经验（避免重复踩坑）

### 5.1 预设模板 ≠ Custom V3（6/1 关键发现）

- **PixelLab 的 Idle / Walking / Reactions 预设**对持械角色（带剑/法杖/盾）E/W 容错差，会丢武器或简化造型
- **解决**：所有持械动画**都用 Custom V3 + 详细分镜 + 武器约束**
- **代价**：每个动画 prompt 要写 ~300-600 字符，但风格 + 武器可控
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
| Reaction 反应太轻 | 闪白 shader（0.05s 全身白）+ 后退 tween（4-6 px，0.1s 回弹）+ 镜头微震 + 红色伤害飘字 |
| 命中无打击感 | hit-stop（0.05s 暂停）+ 粒子爆点 |
| 法术无投射物 | F4（orb 最亮帧）触发独立粒子/弹道 GameObject |
| 死亡无动画 | 用 Reaction 最后一帧 + 黑白渐变 + 像素消散粒子（M2 加） |

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

- [ ] 6/2~ 起：所有动画生成**当场把完整 prompt 复制粘贴存档**（贴到本 doc §3.2 取代复刻模板，或建 `prompts-archive/<date>-<character>-<animation>.txt`）
- [ ] 如果重新生成 Idle/Walking/Reaction（例如 polish 阶段），把 6/1 实际效果与本 doc 模板做 A/B 对照，记录哪些 prompt 句改善哪些指标
- [ ] 新角色（精英敌方 / 平民 / 队友 2）走本 doc §2 + §4 模板
- [ ] 把本 doc 引用关系登记到 spec `docs/specs/2026-05-24-fantacy-centry-unity-design.md` §5
