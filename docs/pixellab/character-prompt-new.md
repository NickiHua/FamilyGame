# PixelLab 角色 Prompt（草稿 / 未验证）

> **文档目的**：存放**还没投到 PixelLab 实际生成验证**的 prompt 草稿。
> **与 `character-prompt.md` 的区别**：那边的全部是 6/1 之前已经在 PixelLab 上跑出 8 方向 + 全帧、人工逐帧审过的**已验证**版本；本文件是新角色 / 新动画的**待验证**初稿。
> **流程**：本文件 prompt → PixelLab 生成 → 逐帧验收 → 通过后**整段搬到** `character-prompt.md` 对应章节，并从本文件删除。

---

## 待验证清单

| 角色 | 阵营 | Rotation | Idle | Walking | Attack | Reaction | 状态 |
|---|---|---|---|---|---|---|---|
| 帝国弓箭手 EmpireArcher | 敌 | ⏳ 草稿 | ⏳ 草稿 | ⏳ 草稿 | ⏳ 草稿 | — | 未投 PixelLab |
| 帝国牧师（女）EmpirePriestess | 敌 | ⏳ 草稿 | ⏳ 草稿 | ⏳ 草稿 | ⏳ 草稿 | — | 未投 PixelLab |
| 帝国法师 EmpireMage | 敌 | ⏳ 草稿 | ⏳ 草稿 | ⏳ 草稿 | ⏳ 草稿 | — | 未投 PixelLab |
| 帝国刺客 EmpireAssassin | 敌 | ⏳ 草稿 | ⏳ 草稿 | ⏳ 草稿 | ⏳ 草稿 | — | 未投 PixelLab |
| 帝国剑客 EmpireSwordsman | 敌 | ⏳ 草稿 | ⏳ 草稿 | ⏳ 草稿 | ⏳ 草稿 | — | 未投 PixelLab |
| 凌霜 LingShuang（粉发枪手 / 未来狮鹫骑士） | 我 | ✅ 已验证 | ✅ 已验证 | ✅ 已验证 | ✅ 已验证 | ✅ 已验证 | LingShuang base = `920fcb19-261b-46a2-b3b4-465f7983e812` |
| 赵铁柱 ZhaoTieZhu（重甲巨斧） | 我 | ⏳ 草稿 | ⏳ 草稿 | ⏳ 草稿 | ⏳ 草稿 | — | 未投 PixelLab |
| 陆离 LuLi（我方剑士 / 主角） | 我 | ⏳ 草稿（重做） | ⏳ 草稿（重做） | ⏳ 草稿（重做） | ⏳ 草稿（重做） | ⏳ 草稿 | 待 3-head chibi 重做 |
| 苏瑶 SuYao（我方法师 / 兜帽女主） | 我 | ⏳ 草稿（重做） | ⏳ 草稿（重做） | ⏳ 草稿（重做） | ⏳ 草稿（重做） | ⏳ 草稿 | 待 3-head chibi 重做 + hood UP |
| 帝国斧兵 EmpireAxeSoldier（基础斧+盾杂兵） | 敌 | ⏳ 草稿（重做） | ⏳ 草稿（重做） | ⏳ 草稿（重做） | ⏳ 草稿（重做） | ⏳ 草稿 | 待 3-head chibi 重做 |

---

## 一、帝国弓箭手（Empire Archer）— 草稿

> 沿用 `character-prompt.md` §2.3 / §3.3 帝国斧兵的西式 + teal/brass 风格锚定，保证两兵种放一起像同阵营。
> 全局设置（Tier 1 / v3 / Humanoid / 8 方向 / Custom V3 / 8 帧 + Keep First Frame）参见 `character-prompt.md` §一。

### 1.1 Rotation（基础 / 角色定义）

- **Character folder（建议）**: `EmpireArcher/Fire_Emblem_GBA_style_enemy/`
- **Canvas**: 96×96（与帝国斧兵一致，给弓的横向尺寸留余量）
- **配色**: 青绿 + 黄铜 + 暗钢（杂兵敌方阵营，同帝国斧兵）

```
Fire Emblem GBA style enemy archer, european medieval fantasy,
generic imperial foot archer,
lean wiry soldier in his 20s with sharp focused face partially visible,
dark teal green tabard over leather and chainmail light armor,
classic western soldier style,
brass and leather trim accents,
open-faced steel nasal helmet (kettle hat style) with no horns and no plume,
brown leather quiver full of arrows strapped on back,
unstrung longbow shape, recurved wooden longbow held in left hand,
bracer on left forearm, leather glove on right hand,
no shield,
clean pixel art, sharp silhouette
```

**风格锚定要点（设计依据，验证完可精简）**：
- 与帝国斧兵共享 `european medieval` + `kettle hat` + `teal/brass` 三组锚点，确保两兵种放一起像同阵营
- `lean wiry` 区别于斧兵的 `stocky stern`（弓手轻甲 + 体型偏瘦是 FE 弓兵标准刻画）
- `no shield` 显式排除盾（否则 AI 看到 teal kettle hat 容易脑补成斧兵）
- `recurved wooden longbow` + `quiver on back` 是弓手身份的双锚，缺一容易被 AI 简化成投枪兵
- `brown leather quiver` 显式给箭袋指定棕色，避免被青绿 tabard 同化看不清

**验收重点**：
- [ ] 8 方向都能看到弓 + 箭袋
- [ ] E/W 方向弓不会被 AI 简化成棍子或换成斧/剑
- [ ] 头盔保持 kettle hat 平顶造型，不长角不长羽毛
- [ ] tabard 颜色和帝国斧兵肉眼一致

---

### 1.2 Idle — Archer Breathing（草稿）

**Folder（生成后填回真实 hash）**: `Archer_stands_in_idle_breathing_pose._F1_idle_sta-XXXX/`

```
Archer stands in idle breathing pose.
F1: idle stance, recurved longbow held vertically in left hand at side, right hand relaxed at side, quiver of arrows visible on back.
F2-3: chest gently rises with breath, shoulders lift slightly.
F4: peak inhale, body slightly taller.
F5-6: chest gently falls, shoulders settle.
F7: deepest exhale.
F8: returns to neutral idle.
Feet stay planted, no walking, no spinning.
Recurved longbow in left hand and brown leather quiver on back both visible every frame, never disappear, never dropped, never swapped.
Kettle hat helmet stays on head. Teal green tabard over light armor.
Bow stays identical across all frames: wooden recurved longbow, undrawn.
Clean pixel art, sharp silhouette.
```

---

### 1.3 Walking — Archer Marches Forward Armed（草稿）

**Folder（生成后填回真实 hash）**: `Archer_marches_forward_armed._F1_idle_bow_in_left-XXXX/`

```
Archer marches forward armed.
F1: idle, recurved longbow in left hand at side, quiver of arrows on back, right hand at side.
F2: right foot lifts slightly, weight on left.
F3: right foot peak lift, knee bent.
F4: right foot plants forward.
F5: left foot lifts slightly.
F6: left foot peak lift.
F7: left foot plants forward.
F8: returns to idle.
Kettle hat stays on head. Teal tabard sways with steps.
No spinning, no jumping.
Bow and quiver visible every frame, never dropped or swapped, bow stays in left hand throughout.
Bow stays identical across all frames: wooden recurved longbow, undrawn, held vertical.
Quiver stays identical: brown leather, full of feathered arrows, on back.
Clean pixel art, sharp silhouette.
```

---

### 1.4 Attack — Draw and Release Arrow（草稿）

**Folder（生成后填回真实 hash）**: `Archer_draws_bow_and_releases_arrow._F1_idle_bow-XXXX/`

```
Archer draws bow and releases an arrow in a clean shot.
F1: idle stance, recurved longbow held vertical in left hand at side, quiver of arrows on back.
F2: raises bow up in front of body with left arm, right hand reaches back over right shoulder to grab an arrow from the quiver.
F3: nocks arrow on bowstring, both hands now on the bow, left arm extends forward holding the bow.
F4: begins drawing the string back with right hand, body squares to target, weight shifts to back foot.
F5: full draw at peak, bowstring pulled back to anchor point near right cheek, arrow horizontal pointing forward, body coiled with tension.
F6: releases the arrow, bowstring snaps forward, right hand opens and pulls back past the ear in follow-through, arrow shown leaving the bow forward.
F7: lowers bow arm, body relaxes from the shot.
F8: returns to idle stance with bow vertical in left hand at side.
Feet planted, no spinning, no jumping, no walking.
Bow stays in left hand throughout, never dropped, never swapped to right hand.
Bow and quiver visible every frame.
Bow stays identical across all frames: wooden recurved longbow with visible string.
Kettle hat stays on head. Teal tabard, light armor.
Strong weighted archery motion, clear draw and release, clean pixel art, sharp silhouette.
```

**关键点拆解**（弓兵特有，供后续投枪兵 / 弩兵复用）：

| 元素 | 作用 |
|---|---|
| F2 `reaches back over right shoulder to grab an arrow` | 抽箭动作，给"弓兵"身份判定帧 |
| F3 `nocks arrow on bowstring` | 上弦，避免 AI 跳过这步直接出现满弓 |
| F5 `full draw at peak, bowstring pulled back to anchor point near right cheek` | 满弓蓄力峰值，描述具体到 anchor point 防止 AI 画"半拉"姿势 |
| F6 `bowstring snaps forward ... follow-through` | 放箭 + 余势，是打击感来源 |
| `bow stays in left hand throughout, never swapped to right hand` | 硬护栏，AI 在拉弓 / 收势之间最容易换手 |
| `arrow shown leaving the bow forward` | 显式让 F6 出箭矢，否则 PixelLab 经常漏画飞行中的箭 |
| `no walking` | 弓兵 attack 容易被 AI 误解成"边走边射"，必须明确禁 |

**预期补强**：箭飞行轨迹 + 命中粒子建议放 Unity 端（与法术投射物同方案，见 `character-prompt.md` §5.5），PixelLab 只负责出手姿态。

---

## 二、帝国牧师（Empire Priestess）— 草稿

> 同阵营 teal/brass 锚定，但走 `church robe` 而非 `tabard over chainmail`，与帝国战斗兵种拉开造型距离。
> 与我方苏瑶（白蓝长银发 + 蓝 orb 法杖，gentle young）的区分锚点：**深色发 + 棕白色僧袍 + 黄铜十字法杖 + stern 30s**。

### 2.1 Rotation

- **Character folder（建议）**: `EmpirePriestess/Fire_Emblem_GBA_style_enemy/`
- **Canvas**: 96×96
- **配色**: 米白 + 深青绿（faction 色，仅作披肩 / 滚边）+ 黄铜

```
Fire Emblem GBA style enemy battle priestess, european medieval fantasy,
generic imperial church cleric serving the empire,
stern serious woman in her early 30s with sharp focused face partially visible,
cream off-white robe down to ankles with dark teal green mantle over shoulders and dark teal trim on hem and sleeves,
brass trim accents on collar and belt,
classic western church style,
dark brown hair tied in low bun at the back of head, no hood,
short white veil pinned by simple brass circlet on forehead, face fully visible,
tall wooden staff with brass cap and small upright brass cross emblem on top, held vertically in right hand,
small leather satchel of healing supplies at left hip,
no armor plates, no shield, no helmet,
clean pixel art, sharp silhouette
```

**风格锚定要点**：
- `church cleric` + `classic western church` 把她绑到欧式教士造型，远离女巫 / 修女惊悚向
- `no hood` + `face fully visible` 显式排除兜帽，避免 SuYao 那次 E/W 修女化的坑
- `brass cross emblem` 替代 SuYao 的 `blue orb` 作为法杖头部识别符
- 头发用 `dark brown` 显式与苏瑶的 `silver` 拉开
- 米白底色 + 深青绿披肩：站在帝国队伍里一眼看出是同阵营（披肩同色），但又不会被误认成杂兵

### 2.2 Idle — Priestess Breathing

```
Priestess stands in idle breathing pose.
F1: idle stance, wooden staff with brass cross held vertically in right hand at side, left hand resting on satchel at hip.
F2-3: chest gently rises with breath, shoulders lift slightly, mantle settles.
F4: peak inhale, body slightly taller.
F5-6: chest gently falls, shoulders settle.
F7: deepest exhale.
F8: returns to neutral idle.
Feet stay planted, no walking, no spinning.
Wooden staff with brass cross on top visible every frame in right hand, never disappears, never dropped.
White veil and brass circlet stay on head every frame, no hood.
Dark teal green mantle drapes over shoulders, cream robe to ankles.
Staff stays identical across all frames: wooden haft, brass cap, small upright brass cross emblem on top.
Clean pixel art, sharp silhouette.
```

### 2.3 Walking — Priestess Walks Holding Staff

```
Priestess walks forward holding staff.
F1: idle, wooden staff with brass cross vertical in right hand, left hand at hip.
F2: right foot lifts slightly, robe and mantle flow.
F3: right foot peak lift.
F4: right foot plants forward.
F5: left foot lifts slightly.
F6: left foot peak lift.
F7: left foot plants forward.
F8: returns to idle.
Veil and brass circlet stay on head every frame, no hood.
Cream robe with dark teal mantle flows with steps.
No spinning, no jumping.
Staff visible every frame, never dropped.
Staff stays identical across all frames: wooden haft, brass cross emblem on top.
Clean pixel art, sharp silhouette.
```

### 2.4 Attack — Heal / Blessing Cast

> 牧师在 SRPG 里通常是治疗友军；Unity 端可同一动画驱动"光柱治疗"（友方）与"圣光打击"（对玩家）。

```
Priestess raises her staff to cast a healing blessing.
F1: idle stance, staff vertical at right side, left hand at hip.
F2-3: she lifts the staff up with both hands in front of her chest, head tilts slightly down in prayer.
F4: staff held high above head at peak, brass cross on top glows brightly, free left hand extends forward with open palm in blessing.
F5-6: she lowers the staff forward and down with a soft gesture, releasing the blessing, body leans slightly forward.
F7-8: pulls staff back to vertical resting position at right side, returns to idle.
Feet stay planted, no spinning, no jumping, no walking.
Staff and brass cross visible every frame, never dropped.
Veil and brass circlet stay on head, no hood, face stays visible.
Robe and mantle flow naturally with the casting motion.
Soft weighted blessing animation, clean pixel art, sharp silhouette.
```

**关键点**：
- 节奏与苏瑶 Spell Cast 一致（蓄力 F2-4 → 释放 F5-6 → 收势 F7-8），但动作幅度更小、更收敛（牧师不是攻击型法师）
- `brass cross glows brightly` 在 F4 加发光，Unity 端绑"治疗光柱"粒子触发帧
- `head tilts slightly down in prayer` 与苏瑶的 `leaning slightly back, gathering magical energy` 区分情绪：祈祷 vs 蓄魔

---

## 三、帝国法师（Empire Mage）— 草稿

> 走 FE 经典"敌方暗法师"路线：tome（书）系而非法杖系，与我方苏瑶（staff/orb 系）完全错开。
> 关键决策：**hood DOWN**（参考 SuYao E/W 修女化教训），用"梳得很整齐的黑发 + 阴沉脸"替代兜帽阴影来实现 sinister 感。

### 3.1 Rotation

- **Character folder（建议）**: `EmpireMage/Fire_Emblem_GBA_style_enemy/`
- **Canvas**: 96×96
- **配色**: 深青绿 + 黑 + 黄铜

```
Fire Emblem GBA style enemy dark mage sorcerer, european medieval fantasy,
sinister imperial battlemage,
gaunt severe man in his 40s with sharp cheekbones and grim cold face partially visible,
dark teal green long robe down to ankles with black inner lining and brass trim,
black leather belt with brass buckle at waist, dark teal sash over right shoulder,
classic western sorcerer wizard style,
slicked back jet black hair, no beard, no hood,
heavy leather-bound spellbook tome with brass clasps and brass corners, held open in left hand at chest height,
right hand raised to shoulder height with fingers spread in a casting gesture,
small dark amulet hanging on chest,
no armor, no shield, no helmet, no staff,
clean pixel art, sharp silhouette
```

**风格锚定要点**：
- `sorcerer wizard` + `classic western sorcerer wizard style` 锚到欧式法师而非东方道士
- `no hood` 主动声明（破除 mage 必带兜帽的 SD 偏置），改用 `slicked back jet black hair` 给阴沉感
- `tome held open in left hand` + `no staff` 把武器锁定为书，与苏瑶的法杖系完全错开
- `fingers spread in a casting gesture` 给一个有辨识度的手势 silhouette，让 rotation 的 8 方向都能立刻识别"这个家伙在施法"
- 颜色与帝国斧兵共享 teal/brass，但用黑色内衬 + 黑腰带强化"暗法师"调性

### 3.2 Idle — Mage Breathing with Tome

```
Dark mage stands in idle breathing pose.
F1: idle stance, spellbook tome held open in left hand at chest, right hand at side, hair slicked back.
F2-3: chest gently rises with breath, shoulders lift slightly, robe settles.
F4: peak inhale, body slightly taller.
F5-6: chest gently falls, shoulders settle.
F7: deepest exhale.
F8: returns to neutral idle.
Feet stay planted, no walking, no spinning.
Spellbook tome held open in left hand visible every frame, never closed, never dropped, never disappears.
Slicked back black hair stays the same every frame, no hood at any point.
Dark teal robe with black lining and brass trim, dark teal sash over right shoulder.
Tome stays identical across all frames: leather-bound, brass clasps, brass corners, held open.
Clean pixel art, sharp silhouette.
```

### 3.3 Walking — Mage Walks Holding Tome

```
Dark mage walks forward holding spellbook.
F1: idle, spellbook open in left hand at chest, right hand at side.
F2: right foot lifts slightly, robe and sash flow.
F3: right foot peak lift.
F4: right foot plants forward.
F5: left foot lifts slightly.
F6: left foot peak lift.
F7: left foot plants forward.
F8: returns to idle.
Slicked back black hair stays the same every frame, no hood.
Dark teal robe with black lining flows with steps.
No spinning, no jumping.
Spellbook tome visible every frame, never closed, never dropped, stays in left hand throughout.
Tome stays identical across all frames: leather-bound, brass clasps, held open.
Clean pixel art, sharp silhouette.
```

### 3.4 Attack — Dark Spell Cast from Tome

```
Dark mage casts a dark spell from his open tome.
F1: idle stance, tome open in left hand at chest, right hand at side.
F2-3: he raises the tome higher with left hand, right hand sweeps up and back gathering dark magical energy, body leans slightly back.
F4: peak charge, tome held forward in left hand with pages glowing dark purple, right hand pulled back near right shoulder with dark energy gathered in palm.
F5-6: he thrusts the right hand forward with palm open toward the target, releasing the dark spell, body leans forward with the cast, tome stays raised in left hand.
F7-8: pulls right hand back to side, tome lowered to chest height, returns to idle stance.
Feet stay planted on the ground throughout, no spinning, no jumping, no walking.
Tome stays open in left hand every single frame, never closed, never dropped.
Right hand is the casting hand, tome hand stays as anchor.
Slicked back black hair stays the same every frame, no hood appears at any point.
Robe flows naturally with the casting motion.
Sinister weighted dark casting animation, clean pixel art, sharp silhouette.
```

**关键点**：
- 左手书 + 右手施法的"双手分工"是 FE 暗法师标志性动作，必须每帧锚死左手位置
- F4 `pages glowing dark purple` + `dark energy gathered in palm` 是 Unity 暗系粒子触发帧
- 与苏瑶的 staff 双手举的施法节奏正好相反（她是双手举杖、自由手前推；他是左手定锚、右手抡出），保证两边法师 silhouette 不撞

---

## 四、帝国刺客（Empire Assassin）— 草稿

> western thief/rogue 锚定，避免被 AI 滑向 ninja。
> hood 处理：**hood DOWN onto shoulders**（披在肩上而非套在头上），上半脸全露、下半脸用 `cloth scarf` 遮，既保留刺客剪影又规避 E/W 兜帽失效问题。

### 4.1 Rotation

- **Character folder（建议）**: `EmpireAssassin/Fire_Emblem_GBA_style_enemy/`
- **Canvas**: 96×96
- **配色**: 深青绿 + 黑 + 暗钢

```
Fire Emblem GBA style enemy assassin rogue, european medieval fantasy,
lean swift imperial assassin,
sharp-faced man in his late 20s with cold narrow eyes and dark stubble partially visible,
dark teal green and black light leather armor over dark grey tunic,
classic western thief rogue style not ninja,
short messy black hair, dark cloth hood lowered down onto shoulders as a cowl behind the neck,
dark cloth scarf wrapped around neck and pulled up over the nose covering lower half of face, eyes and forehead fully visible,
two short steel daggers, one held in each hand in reverse ice-pick grip,
brass buckles and crossed dark leather belts over chest, leather bracers on both forearms,
no helmet, no shield, no plate armor, no cape,
clean pixel art, sharp silhouette
```

**风格锚定要点**：
- `western thief rogue style not ninja` — 主动用 `not ninja` 屏蔽日式 SD 偏置（per 6/1 教训，否定词不可靠，但作为补充防线 OK）
- `hood lowered down onto shoulders as a cowl behind the neck` 明确兜帽位置在背后，避免被 AI 自动拉起来盖住脸
- `cloth scarf ... pulled up over the nose` 给一个西式刺客（参考 Assassin's Creed / Skyrim 暗影兄弟会）的下半脸遮挡，是刺客 silhouette 的精髓
- `two short steel daggers ... reverse ice-pick grip` 双匕首反握，FE Jaffar / 暗杀者经典持械法
- `no cape` 显式禁披风，让剪影更利落（刺客不需要披风甩动）

### 4.2 Idle — Assassin Crouched Ready

```
Assassin stands in idle ready pose, slightly crouched.
F1: idle stance, two daggers held in reverse grip one in each hand at sides, body slightly crouched and tense.
F2-3: shoulders lift slightly with breath, body sways subtly forward.
F4: peak inhale, body fully alert.
F5-6: shoulders settle, body sways back slightly.
F7: deepest exhale.
F8: returns to neutral crouched ready idle.
Feet stay planted, no walking, no spinning.
Two steel daggers visible every frame in reverse grip, one in each hand, never dropped, never swapped to forward grip.
Cloth scarf stays pulled up over nose, eyes visible. Hood stays lowered behind neck as a cowl, never up over head.
Dark teal and black leather armor.
Daggers stay identical across all frames: short steel blades, dark leather grips.
Clean pixel art, sharp silhouette.
```

### 4.3 Walking — Assassin Sneaks Forward

```
Assassin moves forward in a low quick step, daggers ready.
F1: idle, two daggers in reverse grip one in each hand, body slightly crouched.
F2: right foot lifts slightly, weight on left, body stays low.
F3: right foot peak lift, knee bent.
F4: right foot plants forward silently.
F5: left foot lifts slightly.
F6: left foot peak lift.
F7: left foot plants forward silently.
F8: returns to idle ready stance.
Body stays low and crouched throughout, no upright marching.
Cloth scarf stays pulled up over nose, eyes visible. Hood stays lowered behind neck, never up.
No spinning, no jumping.
Two daggers visible every frame in reverse grip, never dropped or swapped.
Daggers stay identical across all frames.
Clean pixel art, sharp silhouette.
```

### 4.4 Attack — Cross Dagger Slash

```
Assassin lunges forward with a fast cross slash using both daggers.
F1: idle ready stance, two daggers in reverse grip at sides.
F2: crouches lower, both arms pull back wide for wind up, daggers cocked outward.
F3: starts to spring forward, weight shifts to front foot, daggers come around.
F4: peak of forward lunge, body leaned in, both daggers crossed in front of chest in an X shape just before the strike.
F5: snaps both daggers outward in a sharp crossing slash, right dagger slashes from upper-left down to lower-right, left dagger slashes from upper-right down to lower-left, arms fully extended outward in a wide X.
F6: arms past the slash, daggers held wide apart at hip height, body fully forward.
F7: pulls daggers back inward toward body, recovers to upright.
F8: returns to crouched ready idle stance.
Feet planted on the ground at landing, no spinning, no jumping in air.
Both daggers stay in reverse grip throughout, one in each hand, never dropped, never swapped to forward grip.
Cloth scarf stays up over nose, hood stays lowered behind neck, never up.
Fast snappy weighted slash motion, clean pixel art, sharp silhouette.
```

**关键点**：
- F4 "X 字交叉"再 F5"反向 X 字甩开"是双匕首攻击经典节奏（参考 FE 暗杀职业 / Octopath Traveler 盗贼）
- `reverse ice-pick grip` 一直锁死，否则 AI 在挥砍中段最容易翻成 forward grip
- `no spinning, no jumping in air` 防 AI 脑补"刺客必空翻"

---

## 五、帝国剑客（Empire Swordsman）— 草稿

> 定位：比基础斧兵更精英的单挑型剑士。
> 与陆离（我方剑士）区分锚点：**敌方 teal 调色 + 没有披风 + 脸上有疤 + 战术姿态而非英姿姿态**。
> 与基础斧兵区分锚点：**没有盾、没有 kettle hat（改露头）、轻一点的甲、单手长剑**。

### 5.1 Rotation

- **Character folder（建议）**: `EmpireSwordsman/Fire_Emblem_GBA_style_enemy/`
- **Canvas**: 96×96
- **配色**: 深青绿 + 暗钢 + 黄铜（同帝国阵营）

```
Fire Emblem GBA style enemy swordsman duelist, european medieval fantasy,
skilled imperial duelist swordmaster,
lean confident man in his late 20s with sharp jaw and a thin diagonal scar across left cheek partially visible,
dark teal green tabard over dark steel breastplate and chainmail sleeves, brass trim accents,
classic western soldier swordmaster style,
no helmet, short cropped dark brown hair swept back,
one-handed steel longsword held in right hand pointed down at side in a ready guard,
empty left hand at side,
brown leather belt with brass buckle, leather bracers on both forearms,
no shield, no cape, no kettle hat,
clean pixel art, sharp silhouette
```

**风格锚定要点**：
- `no helmet` + `short cropped dark brown hair` 与基础斧兵 `kettle hat` 立刻拉开剪影差异，远看就能识别"这是个精英剑士"
- `thin diagonal scar across left cheek` 加一个非对称面部特征作为辨识符，免得 8 方向只有色块没有记忆点
- `no shield, no cape, no kettle hat` 三连显式禁，把所有可能让他变成"斧兵换皮"或"陆离敌方版"的元素都排除
- `tabard over dark steel breastplate and chainmail sleeves`：比基础斧兵的 chainmail 多一层 breastplate（精英），但比赵铁柱的 full plate 轻（不是重装）

### 5.2 Idle — Swordsman Breathing

```
Swordsman stands in idle breathing pose.
F1: idle stance, longsword held in right hand pointed down at side, left hand at side.
F2-3: chest gently rises with breath, shoulders lift slightly.
F4: peak inhale, body slightly taller.
F5-6: chest gently falls, shoulders settle.
F7: deepest exhale.
F8: returns to neutral idle.
Feet stay planted, no walking, no spinning.
Longsword visible in right hand every frame, never dropped, never sheathed.
No helmet every frame, short dark brown hair stays the same.
Dark teal tabard over dark steel breastplate.
Sword stays identical across all frames: one-handed steel longsword, brown grip, simple crossguard.
Clean pixel art, sharp silhouette.
```

### 5.3 Walking — Swordsman Marches Forward

```
Swordsman walks forward in a steady step, sword in hand.
F1: idle, longsword in right hand at side pointed down, left hand at side.
F2: right foot lifts slightly, weight on left.
F3: right foot peak lift, knee bent.
F4: right foot plants forward.
F5: left foot lifts slightly.
F6: left foot peak lift.
F7: left foot plants forward.
F8: returns to idle.
No helmet, short dark brown hair stays the same every frame.
Dark teal tabard sways slightly with steps.
No spinning, no jumping.
Longsword visible in right hand every frame, never dropped, never swapped to left hand.
Sword stays identical across all frames.
Clean pixel art, sharp silhouette.
```

### 5.4 Attack — Forward Lunge Thrust

> 选 thrust 而非 slash，与陆离的对角下劈（diagonal arc downward）拉开攻击 silhouette，让玩家"看一眼挥剑动作就知道是敌方剑客而非陆离"。

```
Swordsman performs a precise forward lunging thrust with his longsword.
F1: idle stance, longsword in right hand pointed down at side, left hand at side.
F2-3: pulls the sword back near right hip, blade pointed forward horizontally, body coils on back foot, left hand raises slightly for balance.
F4: peak wind up, sword fully cocked back at right hip blade horizontal, body fully coiled on back foot.
F5: explodes forward in a deep lunge, right leg extends forward, sword thrusts straight forward at chest height blade horizontal, left hand pulls back for balance.
F6: peak extension, sword fully extended forward, body fully lunged, right leg bent at front, left leg extended straight back.
F7: pulls sword back toward body, body starts to recover from the lunge.
F8: returns to upright idle stance with sword at right side.
Feet stay on the ground throughout the lunge, no spinning, no jumping in air.
Longsword stays in right hand throughout, never dropped, never swapped to left hand.
No helmet, hair stays the same every frame.
Sword stays identical across all frames.
Sharp precise weighted thrust motion, clean pixel art, sharp silhouette.
```

**关键点**：
- `pulls the sword back near right hip, blade pointed forward horizontally` 是西式直刺的标准蓄势（区别于陆离的 over-shoulder wind up）
- F5-F6 lunge 是技术流剑士的辨识动作，比挥砍更难画好，所以分了两帧细描述
- `feet stay on the ground` 防 AI 把 lunge 画成空翻刺

---

## 六、凌霜 LingShuang（我方枪兵 / 未来狮鹫骑士）— 草稿

> **粉发风险**：5/31 spike 里"没加锚点 → 粉发弓箭手 Q 版离群"是已知坑。
> **解决方案**：用 `Fire Emblem GBA style ally pegasus knight` 直接召唤 FE7 Florina / Fiora 的训练数据档案（她们就是粉/淡紫发的西式飞马骑士），并用 `pale pink` 而非饱和 `pink`，进一步避开 Q 版 / 卡哇伊调色。
> 未来骑狮鹫：装备 = 长枪 + 轻甲 + 半披风，就是 FE pegasus/wyvern knight 标配，落地步兵和上鹫飞兵造型可直接复用。

### 6.1 Rotation

- **Character folder（建议）**: `LingShuang/Fire_Emblem_GBA_style_pegasus/`
- **Canvas**: 92×92（与陆离/苏瑶我方角色一致）
- **配色**: 银 + 蓝 + 白（我方阵营 + 飞兵白色辅色）

```
Fire Emblem GBA style ally pegasus knight lance fighter, western fantasy,
graceful alert lance fighter,
young woman early 20s, slender athletic build,
shoulder length pale pink hair tied at the back of head with a single white ribbon, long bangs framing face,
light silver chest plate over white tunic and blue knee-length skirt with armored side panels,
blue half cape pinned at left shoulder flowing behind,
slim silver pauldrons, silver greaves over white boots, white leather gloves,
long western steel cavalry lance held vertically in right hand, lance as tall as her body,
no helmet, alert poised posture,
clean pixel art, vibrant colors, sharp silhouette
```

**风格锚定要点**：
- `Fire Emblem GBA style ally pegasus knight` 是 FE7/FE8 训练数据里粉/淡紫发女枪兵的精确召唤词，整个 silhouette（光甲 + 长枪 + 半披风 + 飘逸长发）都靠这一行锚定
- `pale pink` 不是 `pink`：饱和粉是 vocaloid 风险词，淡粉对齐 Florina
- `long western steel cavalry lance ... as tall as her body` 锁定长度，否则 AI 容易画成短矛或骑枪
- 服装与陆离同阵营色（银 + 蓝）但飞兵特征用"白色辅色 + 半披风"区分（不是全披风，半披风是 FE 飞兵习语）
- `no helmet`：FE pegasus knight 全员不戴盔，留头发飘逸

### 6.2 Idle — Pegasus Knight Breathing

```
Pegasus knight stands in idle breathing pose.
F1: idle stance, long cavalry lance held vertically in right hand at side, lance tall as her body, left hand at side.
F2-3: chest gently rises with breath, shoulders lift slightly, hair and half cape stir faintly.
F4: peak inhale, body slightly taller.
F5-6: chest gently falls, shoulders settle.
F7: deepest exhale.
F8: returns to neutral idle.
Feet stay planted, no walking, no spinning.
Long cavalry lance held vertically in right hand visible every frame, never disappears, never dropped.
No helmet every frame, pale pink hair tied with white ribbon stays the same.
Blue half cape sways gently from left shoulder.
Lance stays identical across all frames: long steel spearhead, wooden haft, tall as her body.
Clean pixel art, sharp silhouette.
```

### 6.3 Walking — Pegasus Knight Walks with Lance

```
Pegasus knight walks forward holding her lance.
F1: idle, long cavalry lance vertical in right hand, left hand at side.
F2: right foot lifts slightly, half cape and skirt flow.
F3: right foot peak lift.
F4: right foot plants forward.
F5: left foot lifts slightly.
F6: left foot peak lift.
F7: left foot plants forward.
F8: returns to idle.
No helmet every frame, pale pink hair with white ribbon stays the same.
Blue half cape flows with steps from left shoulder.
No spinning, no jumping.
Lance visible every frame in right hand, never dropped, never swapped to left hand, stays vertical.
Lance stays identical across all frames: long steel spearhead, wooden haft, tall as her body.
Clean pixel art, sharp silhouette.
```

### 6.4 Attack — Lance Thrust

```
Pegasus knight performs a strong forward thrust with her cavalry lance.
F1: idle stance, lance vertical in right hand at side.
F2-3: brings lance down from vertical and pulls it back at hip height with both hands, spearhead pointed forward horizontally, body coils on back foot.
F4: peak wind up, lance fully cocked back at right hip with both hands, spearhead horizontal pointed forward, body coiled on back foot, left foot forward braced.
F5: thrusts the lance straight forward with both hands explosively, body weight shifts forward onto front foot, hips drive into the thrust.
F6: peak extension, lance fully extended forward horizontal, both arms straight, body leaned forward.
F7: pulls the lance back toward body, body recovers upright.
F8: returns to idle stance with lance vertical in right hand at side.
Feet stay on the ground throughout, no spinning, no jumping in air.
Lance visible every frame, never dropped, both hands grip the lance during the thrust.
No helmet, pale pink hair with white ribbon stays the same every frame.
Blue half cape flows with the thrust motion.
Lance stays identical across all frames: long steel spearhead, wooden haft.
Sharp weighted spear thrust motion, clean pixel art, sharp silhouette.
```

**关键点**：
- 双手持枪 thrust 与帝国剑客的单手剑 thrust 在 silhouette 上不撞（左手抓杆位置不一样）
- `lance fully cocked back at right hip with both hands` 锁双手持枪，防 AI 退化成单手投枪
- `feet stay on the ground` + `no jumping in air`：未来上鹫之后才有空中位移，落地步兵阶段必须钉地
- Unity 端：未来做"上鹫"骑乘版本时，这套 idle/walking/attack 的躯干 + 持枪 pose 可直接挂到狮鹫骨架上当骑士部分

---

## 七、赵铁柱 ZhaoTieZhu（我方重甲巨斧）— 草稿（深蓝重甲 + 露头）

> **东方人形象 + 巨斧最大风险**：6/1 记录里 `dark crimson and black armor + horned helmet` → 出来日式武将。所以这次铁柱的**装备全部锁西式**（silver plate + 深蓝 tabard + western great axe），"东方感"只通过**脸 + 黑发 + 低马尾 + 短胡**实现，**严格禁用** `samurai / topknot / katana / kimono / oni / horned`。
> **2026-06-07 修订**：
> - 阵营色从"普通蓝"改为"深蓝（deep navy）"，与陆离的"亮蓝披风"区分层次。两人远看：陆离 = 亮银+亮蓝（轻骑兵感），铁柱 = 亮银+深蓝（重装老兵感）。
> - 显式 `no helmet on head, head fully bare` — 之前 prompt 里没写头盔约束，AI 看到 `heavy plate armor` 容易自动加盔（重装兵刻板印象），把头发盖住。
> - 黑发设定：`jet black hair` + `small low ponytail at the nape of the neck` + `short trimmed black beard`。低马尾不是 topknot（避免武士联想），短络腮胡是西式 berserker 标配（参考 FE Hawkeye / Geitz）。

### 7.1 Rotation

- **Character folder（建议）**: `ZhaoTieZhu/Fire_Emblem_GBA_style_hero/`
- **Canvas**: 128×128（chibi 3 头身 + 大斧 padding，与新阵容统一）
- **配色**: 银 + **深蓝（deep navy / midnight blue）** + 黄铜（与陆离的亮蓝拉开层次，但仍属我方阵营银+蓝家族）

```
Fire Emblem GBA style chibi hero heavy axe warrior, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
sturdy powerful two-handed axe fighter, broad shouldered build,
tall man in his early 30s with east asian face and strong jaw,
no helmet on head, head fully bare and exposed,
short jet black hair tied back in a small low ponytail at the nape of the neck, short trimmed black beard,
heavy silver full plate armor with DEEP NAVY BLUE tabard over the chest and brass rivets along the trim,
large silver pauldrons, silver gauntlets, silver greaves,
DEEP NAVY BLUE half cape from the back of the shoulders, nearly midnight blue color,
massive two-handed western great axe with wide double-bladed steel head and long wooden haft, held resting on right shoulder with both hands,
confident grounded stance with feet planted apart,
black ponytail drawn IN FRONT OF and OVER the deep navy blue half cape, hair never tucked under any cloth layer,
clean pixel art, vibrant colors, sharp silhouette
```

**风格锚定要点**：
- **`no helmet on head, head fully bare and exposed`** 是 2026-06-07 新增的硬护栏。`heavy plate armor` 在 SD 训练集里和 `full helm` 高度耦合，不显式禁就会加盔盖住黑马尾。需要正反两句双保险
- **`DEEP NAVY BLUE` 全大写 + 两处独立强调（tabard + half cape）+ `nearly midnight blue color` 三连**：颜色是 SD 模型最难精准控制的维度之一，常规 `dark blue` 经常被画成普通蓝。全大写 + 二次重复 + 颜色描述词替换三层叠加才能拉到"明显比陆离深"
- 东方感锚点只放三处：`east asian face`、`jet black hair tied back in a small low ponytail`、`short trimmed black beard`。**没用** `topknot`（武士联想强）、`samurai`、`katana`、`kimono`
- `Fire Emblem GBA style hero` 与陆离共用 archetype，保证两人放一起像同阵营英雄
- 武器明确写 `western great axe with wide double-bladed steel head`，排除"中式偃月刀"或"日式薙刀"。`wide double-bladed` 与帝国斧兵的 `single curved blade` 显式拉开，远看也能区分友我斧头
- `held resting on right shoulder with both hands` 是重斧标准 idle 持法，比"垂手提斧"更有重量感、也让大斧每帧都明显
- 头发-披风穿戴关系沿用 LingShuang 验证过的 `hair IN FRONT OF and OVER the cape`，防 AI 把马尾塞进披风里

### 7.2 Idle — Heavy Warrior Breathing

```
Heavy axe warrior stands in idle breathing pose.
F1: idle stance, massive two-handed great axe resting on right shoulder with both hands on the haft, feet planted apart.
F2-3: chest rises with breath, shoulders lift slightly under heavy armor.
F4: peak inhale, body slightly taller.
F5-6: chest falls, shoulders settle.
F7: deepest exhale.
F8: returns to neutral idle.
Feet stay planted, no walking, no spinning.
Massive two-handed great axe visible every frame on right shoulder with both hands gripping the haft, never dropped, never swapped.
No helmet every frame, head fully bare, short black hair tied in low ponytail and short black beard stay the same every frame.
Heavy silver full plate armor with DEEP NAVY BLUE tabard, DEEP NAVY BLUE half cape from back nearly midnight blue.
Black ponytail stays IN FRONT OF and OVER the deep navy blue half cape every frame.
Axe stays identical across all frames: wide double-bladed steel head, long wooden haft.
Clean pixel art, sharp silhouette.
```

### 7.3 Walking — Heavy Warrior Marches Forward

```
Heavy axe warrior marches forward with great axe on shoulder.
F1: idle, great axe resting on right shoulder gripped with both hands, feet planted apart.
F2: right foot lifts slightly, weight on left, armor sways slightly.
F3: right foot peak lift, knee bent under weight of armor.
F4: right foot plants forward heavily.
F5: left foot lifts slightly.
F6: left foot peak lift.
F7: left foot plants forward heavily.
F8: returns to idle.
No helmet every frame, head fully bare, short black hair in low ponytail and black beard stay the same every frame.
DEEP NAVY BLUE tabard and deep navy blue half cape sway with heavy steps.
No spinning, no jumping.
Great axe stays on right shoulder gripped with both hands every frame, never dropped, never swapped to one hand.
Black ponytail stays IN FRONT OF and OVER the deep navy blue half cape every frame.
Axe stays identical across all frames.
Heavy weighted marching motion, clean pixel art, sharp silhouette.
```

### 7.4 React — Heavy Stagger

> 重装老兵的反应：不是"被打飞"，是"震一下站稳"。8 帧节奏比普通 flinch 慢一拍。

```
Heavy axe warrior takes a heavy hit and staggers backward, great axe still on shoulder.
F1: idle stance, great axe resting on right shoulder gripped with both hands.
F2: hit lands hard, body jolts backward at the chest, head snaps back slightly.
F3: peak stagger, back foot slides back heavily to brace, body bent backward at the waist, both hands keep axe on shoulder.
F4: holds the staggered wincing pose, armor plates clatter.
F5-6: body slowly straightens up, weight shifts back over center.
F7: shoulders settle, half cape falls back into place.
F8: returns to neutral idle stance.
Feet stay on the ground throughout, no falling down, no spinning, no jumping.
Both hands stay on the haft of the great axe every single frame, axe stays on right shoulder, never one-handed, never dropped.
No helmet every frame, head fully bare, short black hair in low ponytail and black beard stay the same every frame.
Black ponytail stays IN FRONT OF and OVER the deep navy blue half cape every frame.
Axe stays identical across all frames.
Heavy slow weighted stagger hit-reaction motion, clean pixel art, sharp silhouette.
```

### 7.5 Attack — Heavy Two-Handed Overhead Cleave

> 区别于帝国斧兵的单手斧砍：铁柱是**双手大斧**，幅度更大、收招更重，silhouette 更接近 FE GBA Berserker 系（Hawkeye / Geitz）。

```
Heavy axe warrior swings his two-handed great axe in a powerful overhead cleave.
F1: idle stance, great axe resting on right shoulder gripped with both hands.
F2-3: lifts the great axe up and back high over the head with both hands, body coils, weight shifts to back foot.
F4: great axe at peak overhead with both hands gripping the haft, body fully coiled, weight on back foot, axe head pointed straight up.
F5: swings the great axe down forward in a powerful vertical cleave with both hands, weight shifts forward onto front foot, body leans in with the swing.
F6: great axe at bottom of the swing, fully extended forward and down in front of body, both hands gripping the haft, body leaned forward.
F7: pulls the great axe back up using both hands, body recovers upright.
F8: returns to idle stance with great axe back on right shoulder.
Feet stay planted on the ground throughout, no spinning, no jumping.
Both hands stay on the haft of the great axe every single frame, never one-handed, never dropped, never swapped.
No helmet every frame, head fully bare, short black hair in low ponytail and black beard stay the same every frame.
DEEP NAVY BLUE tabard and deep navy blue half cape flow with the heavy swing, ponytail stays IN FRONT OF and OVER the cape.
Axe stays identical across all frames.
Heavy slow weighted two-handed cleave motion, clean pixel art, sharp silhouette.
```

**关键点**：
- `both hands stay on the haft ... every single frame, never one-handed` 是关键护栏，AI 在挥砍中段最容易让一只手脱手
- `No helmet every frame, head fully bare` 在每个动画里都重申一次（不是只在 rotation 锁），动作中段最容易触发"AI 自动加盔"
- 节奏比帝国斧兵的单手 overhead chop 慢一拍（蓄力 F2-4 占 3 帧、收势 F7 多一帧），强化"重武器"质感
- silhouette 上：陆离对角斜砍（亮蓝披风）、帝国斧兵单手垂直劈（teal+kettle hat）、铁柱双手过顶大劈（深蓝披风+露头黑马尾），三人攻击动作 + 颜色 + 头部全部不撞

---

## 八、陆离 LuLi（我方剑士 / 主角）— 草稿（chibi 重做版，剑挂腰间）

> **重做动机**：旧 `character-prompt.md` §2.1 / §3.1 的 LuLi 是 2-head Q 版 + 简短 prompt，与现在 3-head chibi 阵容（LingShuang / ZhaoTieZhu 等）头身比不一致，并肩站会矮一截。
> **2026-06-07 修订**：**剑从背后改到腰间左侧**。原因见 `character-prompt-v2.md` §2.1：v1 验证过"背剑 + 披风"是死亡组合 — E/W 方向披风把剑挡得只剩剑柄一截。已知坑不要再踩一次。
> **关键差异化锚点**（区分敌方 EmpireSwordsman）：**剑在腰间剑鞘不在手上**（idle/walk 都不持剑） + **蓝披风** + **无面部疤痕** + **friendly determined** 表情。
> 与赵铁柱（同阵营银+深蓝）的区分：**轻甲、单手剑、卷发** vs 铁柱 **重甲、双手大斧、马尾+胡子+深蓝色**。

### 8.1 Rotation

- **Character folder（建议）**: `LuLi/Fire_Emblem_GBA_style_hero/`
- **Canvas**: 128×128（v2 已实验过 248 在 E/W 方向标签会塌，128 是甜点）
- **配色**: 银 + 蓝 + 白（我方阵营标准色，与 LingShuang 共享；与 ZhaoTieZhu 的深蓝拉开层次）

```
Fire Emblem GBA style chibi ally hero swordsman, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
balanced young swordsman not heavy, confident grounded stance,
young man early 20s with friendly determined face,
short messy brown hair, no helmet,
light silver plate armor with leather straps over a white tunic, brass buckle accents,
blue cape pinned at the neck flowing behind on the back,
silver pauldrons, silver greaves over brown boots, leather gloves,
one-handed steel longsword in a brown leather scabbard hanging at the LEFT HIP, scabbard clearly visible at the waist on the left side, sword hilt sticking out forward at the left hip, sword NOT on the back, sword NOT in hand,
empty hands at sides,
brown messy hair drawn IN FRONT OF and OVER the blue cape, hair never tucked under any cloth layer,
clean pixel art, vibrant colors, sharp silhouette
```

**风格锚定要点**：
- **腰挂剑** 是 v2 验证过的修复（`character-prompt-v2.md` §2.1）：v1 背剑 + 披风组合在 E/W 方向只露剑柄一截，物理上把剑搬到披风之外才解决。`scabbard clearly visible at the waist on the left side` + `sword hilt sticking out forward at the left hip` 给两道独立锚定（剑鞘位置 + 剑柄朝向），降低任一句被忽略的风险
- `sword NOT on the back, sword NOT in hand` 三连否定锁死：既不背、也不持。`sword NOT in hand` 是与 EmpireSwordsman（剑在手）的核心区分
- 披风 `flowing behind on the back` 明确披风在背后 — 剑在腰、披风在背，两个独立平面互不干涉
- `friendly determined face` 与 EmpireSwordsman 的 `sharp jaw and a thin diagonal scar` 拉开气质：温和主角 vs 冷峻敌方
- `light silver plate armor` 比 ZhaoTieZhu 的 `heavy silver full plate` 减一档，silhouette 更瘦
- 头发-披风穿戴关系沿用 LingShuang 验证过的 `hair IN FRONT OF and OVER the cape`

### 8.2 Idle — Hero Breathing

```
Hero swordsman stands in idle breathing pose.
F1: idle stance, longsword in brown scabbard hanging at left hip with hilt sticking out forward at the waist, both hands at sides.
F2-3: chest gently rises with breath, shoulders lift slightly, blue cape stirs faintly behind on the back.
F4: peak inhale, body slightly taller.
F5-6: chest gently falls, shoulders settle.
F7: deepest exhale.
F8: returns to neutral idle.
Feet stay planted, no walking, no spinning.
Longsword stays SHEATHED at the LEFT HIP every frame, scabbard visible at the waist on the left side, never drawn, never moved to the back, never falls off.
Short brown messy hair stays the same every frame, no helmet at any point.
Light silver plate armor with leather straps over white tunic.
Blue cape sways gently from the shoulders behind on the back.
Brown hair stays IN FRONT OF and OVER the blue cape every frame.
Hip scabbard and sword stay identical across all frames.
Clean pixel art, sharp silhouette.
```

### 8.3 Walking — Hero Walks Forward

```
Hero swordsman walks forward in a steady step.
F1: idle, longsword in scabbard at left hip with hilt visible at waist, hands at sides.
F2: right foot lifts slightly, blue cape flows behind on the back.
F3: right foot peak lift, knee bent.
F4: right foot plants forward.
F5: left foot lifts slightly.
F6: left foot peak lift.
F7: left foot plants forward.
F8: returns to idle.
Short brown messy hair stays the same every frame, no helmet.
Blue cape flows naturally with steps behind on the back.
No spinning, no jumping.
Longsword stays SHEATHED at the LEFT HIP every frame, scabbard visible at the waist on the left side, never drawn, never moved to the back.
Brown hair stays IN FRONT OF and OVER the blue cape every frame.
Hip scabbard and sword stay identical across all frames.
Clean pixel art, sharp silhouette.
```

### 8.4 React — Hero Recoils

> 与 LingShuang / ZhaoTieZhu 一致的 8 帧 flinch 模板。

```
Hero swordsman takes a hit and recoils sharply.
F1: idle stance, sword sheathed at left hip with hilt visible at waist, hands at sides.
F2: hit lands, body jolts backward at the chest, head snaps back slightly, both arms fling out for balance, cape flares behind.
F3: peak recoil, back foot slides back to brace, body bent backward at the waist, eyes squeezed in pain.
F4: holds the bent-back wincing pose, cape flares behind on the back.
F5-6: body slowly straightens, arms settle back to sides.
F7: shoulders relax, cape settles back into place.
F8: returns to neutral idle stance.
Feet stay on the ground throughout, no falling down, no spinning, no jumping.
Longsword stays SHEATHED at the LEFT HIP every frame, scabbard visible at the waist on the left side, never drawn, never moved to the back, never dropped.
Short brown messy hair stays the same every frame, no helmet.
Brown hair stays IN FRONT OF and OVER the blue cape every frame.
Hip scabbard and sword stay identical across all frames.
Sharp weighted hit-reaction flinch motion, clean pixel art, sharp silhouette.
```

### 8.5 Attack — Draw from Hip + Diagonal Slash + Sheathe

> 与 EmpireSwordsman 的"全程持剑直刺"完全错开：LuLi 是**从腰间剑鞘拔→砍→收回腰间**的完整 sequence。silhouette 上一眼区分两人攻击动作。
> 拔剑手势从"右手反手摸背"（v1）改为"右手横身去摸左腰"，更自然，PixelLab 也更容易画对。

```
Hero swordsman draws his longsword from the hip and performs a strong diagonal slash.
F1: idle stance, sword sheathed at left hip with hilt visible at waist, hands at sides.
F2: right hand crosses over the body to grip the sword hilt at the left hip, body coils slightly.
F3: draws the longsword out of the hip scabbard with right hand sweeping up and across the body, sword now in right hand raised high to the right behind the head, body wound up, weight on back foot, empty scabbard still visible at left hip.
F4: peak wind up, longsword fully raised over head and back to the right, body fully coiled, weight on back foot, left hand extended forward for balance, empty scabbard still at left hip.
F5: swings the longsword down forward in a strong diagonal arc from upper-right to lower-left across the body, weight shifts forward onto front foot, body leans into the slash.
F6: longsword at bottom of the arc, extended forward and down to the left side of the body, body fully leaned forward, blade horizontal pointing left-forward.
F7: pulls the sword back upright in front of the body in a ready guard, right hand at chest height holding sword vertical, body recovers upright.
F8: returns to upright idle stance, sword sheathed back into the scabbard at the left hip with hilt visible at the waist.
Feet stay on the ground throughout, no spinning, no jumping in air.
Sword starts in HIP scabbard (F1), gets drawn from the HIP (F2-3), slashes (F4-6), then re-sheathes back to the HIP scabbard (F7-8). Sword is NEVER on the back at any frame. Right hand grips the sword throughout the drawn portion, never swapped to left hand. Empty scabbard stays visible at left hip during the slash frames.
Short brown messy hair stays the same every frame, no helmet.
Blue cape flows with the slash motion behind on the back.
Brown hair stays IN FRONT OF and OVER the blue cape every frame.
Longsword stays identical across all frames when visible: one-handed steel blade, brown grip, simple crossguard.
Sharp powerful weighted diagonal slash motion, clean pixel art, sharp silhouette.
```

**关键点**：
- `Sword is NEVER on the back at any frame` 是关键护栏 — AI 在拔剑动作上有训练偏置会自动 fallback 到背剑（FE/JRPG 主角默认背剑姿势），必须每帧重申剑鞘在腰
- F2 横身摸左腰拔剑（cross-draw）+ F8 收剑形成"拔→砍→收"完整 SRPG 动作单元，比 v1 背抽更自然
- `Empty scabbard stays visible at left hip during the slash frames` 强制空鞘在画面里 — 防 AI 在 F5-F6 直接把鞘忘掉，那样收剑帧 F8 会无处可收

---

## 九、苏瑶 SuYao（我方法师 / 兜帽女主）— 草稿（chibi 重做版 + hood UP）

> **重做动机 + 历史**：
> - 5/31 用 `hood down` 版本 → E/W 兜帽自动戴上 → 修女化
> - 6/1 强化 `hood down` 加锚 → 全 4 方向稳定（旧 `character-prompt.md` §2.2 / §3.2 已存档）
> - **本次重做改成 `hood UP` 设计**：玩家希望兜帽戴起来（更神秘 / 更"少话主角"气质），但要求银发只露脸侧两缕、不漏出兜帽外其他位置。已上一次试出 silhouette 不错但**头身比变成 2.5 头身**（chibi 锚点被密集的 hood 约束挤掉权重）。
> - 本次方案：把 chibi proportion 锚点**前置 + 加密**，并显式声明"长袍下面的身体仍是 chibi 矮身"，破除 AI 看到 long robe 就拉成 adult 比例的偏置。
> **与 EmpirePriestess 的区分锚点**：苏瑶 = **银发 + 蓝 orb 法杖 + hood up + young gentle**；牧师 = **dark brown bun + brass cross + no hood + stern 30s**。

### 9.1 Rotation

- **Character folder（建议）**: `SuYao/Fire_Emblem_GBA_style_female/`
- **Canvas**: 92×92
- **配色**: 白 + 蓝 + 金（我方法师标识，与旧版一致）

```
Fire Emblem GBA style chibi female mage cleric, western fantasy,
3-head-tall super-deformed proportions, total body height equals 3 head heights stacked,
large head with big expressive eyes, short body, small hands and feet, stubby short limbs,
small chibi body underneath the long robe, NOT a slender adult, the figure is short and stout in chibi proportions even though the robe is long,
young woman early 20s, gentle calm pose,
wearing white and blue hooded robe with gold trim, robe falls to ankles,
hood pulled UP over head, hood completely covers top of head and hairline,
no hair on top of head, no hair on the hood surface, no hair behind the hood,
silver hair only visible as two short locks framing the face at the cheeks below the hood opening,
silver hair flowing down from below the hood opening to chest level only, no hair extending past the chest,
wooden staff with a large round blue crystal orb on top held vertically in right hand,
eyes nose and mouth visible inside the hood opening,
no armor, no shield, no helmet,
clean pixel art, vibrant colors, sharp silhouette
```

**头身比修复策略（针对上一次 2.5 头身问题）**：

| 加固层 | Prompt 句 |
|---|---|
| 起手定调 | `3-head-tall super-deformed proportions, total body height equals 3 head heights stacked,` |
| 体型描述 | `large head with big expressive eyes, short body, small hands and feet, stubby short limbs,` |
| **关键反偏置句** | `small chibi body underneath the long robe, NOT a slender adult, the figure is short and stout in chibi proportions even though the robe is long,` |

第 3 句是核心：直接告诉 AI"长袍下面不要画 adult 身材"，破除 AI 看到 ankle-length robe 就自动拉成 1.6m 修女比例的训练偏置。

**hood 约束（保留上一版有效部分，只 reformat）**：
- `hood pulled UP` / `hood completely covers top of head and hairline`
- `no hair on top of head` / `no hair on the hood surface` / `no hair behind the hood`
- 银发只允许出现在 **cheeks → chest** 这一段：`two short locks framing the face at the cheeks below the hood opening` + `flowing down ... to chest level only, no hair extending past the chest`

**验收重点**：
- [ ] 8 方向都是 3 头身（量一下：头高 × 3 ≈ 全身高）
- [ ] hood 在 N/S/E/W 都不掉
- [ ] 银发只在脸侧两缕 + 胸前往下不超过 chest
- [ ] orb 法杖每帧可见

### 9.2 Idle — Mage Breathing (hood up)

```
Mage cleric stands in idle breathing pose.
F1: idle stance, wooden staff with large blue crystal orb held vertically in right hand at side, left hand resting at side, hood pulled up over head.
F2-3: chest gently rises with breath, shoulders lift slightly, robe settles softly.
F4: peak inhale, body slightly taller.
F5-6: chest gently falls, shoulders settle.
F7: deepest exhale.
F8: returns to neutral idle.
Feet stay planted, no walking, no spinning.
Wooden staff with large blue crystal orb visible every frame in right hand, never disappears, never dropped.
Hood stays UP over head every frame, hairline always covered, no hair on top of head.
Silver hair only visible as two short locks framing the face at cheeks, never grows long or extends past chest.
White and blue robe with gold trim, robe falls to ankles.
Body inside the robe stays chibi short proportion every frame, NOT slender adult.
Staff stays identical across all frames: wooden haft, large round glowing blue crystal orb on top.
Clean pixel art, sharp silhouette.
```

### 9.3 Walking — Mage Walks Forward

```
Mage cleric walks forward holding staff.
F1: idle, wooden staff with blue crystal orb vertical in right hand, left hand at side, hood up.
F2: right foot lifts slightly, robe flows softly.
F3: right foot peak lift.
F4: right foot plants forward.
F5: left foot lifts slightly.
F6: left foot peak lift.
F7: left foot plants forward.
F8: returns to idle.
Hood stays UP every frame, hairline always covered.
Silver hair only visible as two short locks at cheeks every frame, never extending past chest.
White and blue robe with gold trim flows with steps.
Body inside the robe stays chibi short proportion every frame.
No spinning, no jumping.
Staff visible every frame in right hand, never dropped, stays vertical.
Staff stays identical across all frames: wooden haft, large round glowing blue crystal orb on top.
Clean pixel art, sharp silhouette.
```

### 9.4 React — Mage Recoils (hood stays on)

```
Mage cleric takes a hit and recoils backward gently.
F1: idle stance, staff vertical in right hand, left hand at side, hood up.
F2: hit lands, body jolts backward at the chest, free left hand jerks up to chest reflexively, staff tilts slightly.
F3: peak flinch, back foot slides back to brace, body bent backward at the waist, head bowed slightly in pain inside the hood.
F4: holds the bent-back wincing pose, robe flares behind.
F5-6: body slowly straightens, left hand falls back to side, staff returns to vertical.
F7: shoulders settle, robe falls back into place.
F8: returns to neutral idle stance.
Feet stay on the ground throughout, no falling down, no spinning, no jumping.
Staff stays in right hand every frame, never dropped.
Hood stays UP every frame, hairline always covered, hood never falls back from the head even during the flinch.
Silver hair only visible as two short locks at cheeks, never extending past chest.
Body inside the robe stays chibi short proportion every frame.
Staff stays identical across all frames.
Sharp weighted hit-reaction flinch motion, clean pixel art, sharp silhouette.
```

### 9.5 Attack — Spell Cast (hood stays on)

```
Mage cleric casts a powerful spell with her staff.
F1: idle stance, staff vertical in right hand at side, left hand at side, hood up.
F2-3: she raises the staff up in front of body with both hands gripping it, body leans slightly back gathering magical energy, head tilts up slightly inside the hood.
F4: staff held high above the head with both hands at peak, large blue crystal orb on top glows brightly with bright blue magical light, free left hand extends forward with open palm toward the target.
F5-6: she thrusts the staff forward and down with a strong casting motion, releasing the spell, body leans forward with the cast, orb still glowing bright blue.
F7-8: pulls the staff back to vertical resting position at the right side, returns to idle stance.
Feet stay planted on the ground throughout, no spinning, no jumping, no walking.
Staff and large blue crystal orb visible every single frame, never dropped.
Hood stays UP every frame, hairline always covered, hood never falls back even during the casting motion.
Silver hair only visible as two short locks at cheeks, never extending past chest.
Body inside the robe stays chibi short proportion every frame, NOT slender adult.
Robe and hood flow naturally with the casting motion but the hood stays on the head.
Staff stays identical across all frames: wooden haft, large round blue crystal orb on top.
Smooth weighted casting animation, clean pixel art, sharp silhouette.
```

**关键点**：
- 旧 6/1 验证版 cast 动画 silhouette 已经 OK，**这次只加 hood-stays-on 护栏**（cast 时身体大动作最容易把 hood 甩飞）
- F4 orb glow 帧仍是 Unity 蓝色法术粒子触发点
- chibi proportion 句**每帧都重复**——和 hood 一样作为硬护栏，避免动画过程中身体被拉长

---

## 十、帝国斧兵 EmpireAxeSoldier（基础斧+盾杂兵）— 草稿（chibi 重做版）

> **重做动机**：旧 `character-prompt.md` §2.3 / §3.3 帝国斧兵是 6/1 阶段已验证的非 chibi 版本，与现在 chibi 阵容并肩站时头身比不匹配。
> **本角色的定位**：基础斧+盾杂兵，FE 中"挡线的成本最低的敌人"。在帝国阵营 5 个差异化兵种（弓 / 牧 / 法 / 刺 / 剑）之外作为**第 6 个 + 最常见**的杂兵。
> **与 EmpireSwordsman 的区分锚点**：本斧兵 = **kettle hat 头盔 + 圆盾 + 单手斧 + 35 岁老兵 + 胡茬**；剑客 = **不戴头盔 + 无盾 + 单手长剑 + 28 岁精英 + 脸上有疤**。silhouette 立刻区分。
> **与 ZhaoTieZhu 的区分锚点**：杂兵 = **单手小斧 + 圆盾 + 杂兵帝国配色**；铁柱 = **双手大斧 + 无盾 + 我方银蓝配色 + 东方脸**。

### 10.1 Rotation

- **Character folder（建议）**: `EmpireAxeSoldier/Fire_Emblem_GBA_style_enemy/`
- **Canvas**: 96×96（与其它帝国兵种一致）
- **配色**: 青绿 + 黄铜 + 暗钢（杂兵敌方阵营）

```
Fire Emblem GBA style chibi enemy axe soldier, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
generic imperial foot trooper with shield and axe in european medieval setting,
stocky stern soldier in his 30s with dark stubble and grim face partially visible,
dark teal green tabard over chainmail and dull steel plate armor on chest,
classic western soldier style,
brass and leather trim accents,
open-faced steel nasal helmet (kettle hat style) with no horns and no plume,
large round wooden shield painted teal green with iron rim and central iron boss, raised in left hand at chest height,
single-handed steel battle axe with single curved blade and wooden haft held in right hand at side, blade pointed down,
brown leather belt with brass buckle, leather bracers on both forearms,
no cape, no two-handed weapon, no longsword,
clean pixel art, vibrant colors, sharp silhouette
```

**风格锚定要点**：
- `kettle hat` + `large round wooden shield` + `single-handed steel battle axe` 是基础斧兵的三件套，与 EmpireSwordsman 的 `no helmet + no shield + longsword` 形成完整剪影反向
- `single curved blade` 显式定义斧头是单刃，与 ZhaoTieZhu `wide double-bladed steel head` 反向，避免两人斧头撞型
- `no two-handed weapon, no longsword` 显式禁，AI 看到 teal soldier 容易脑补成"全帝国都拿一样的剑"
- `stocky stern soldier in his 30s with dark stubble` 沿用 6/1 已验证的西式杂兵气质（不是日式武将、不是英武剑客）
- 沿用 6/1 验证有效的"`crimson + horned` 是日式武将偏置词"教训，全程不出现这两个词

### 10.2 Idle — Axe Soldier Breathing

```
Axe soldier stands in idle breathing pose.
F1: idle stance, battle axe held in right hand at side blade pointed down, round teal shield raised in left hand at chest height.
F2-3: chest gently rises with breath, shoulders lift slightly.
F4: peak inhale, body slightly taller.
F5-6: chest gently falls, shoulders settle.
F7: deepest exhale.
F8: returns to neutral idle.
Feet stay planted, no walking, no spinning.
Battle axe in right hand and round teal shield in left hand both visible every frame, never disappear, never dropped, never swapped between hands.
Kettle hat helmet stays on head every frame.
Dark teal green tabard over chainmail and steel plate.
Axe stays identical across all frames: single-bladed curved steel head, wooden haft.
Shield stays identical: round, teal-painted wooden face, iron rim, central iron boss.
Clean pixel art, sharp silhouette.
```

### 10.3 Walking — Axe Soldier Marches Forward Armed

```
Axe soldier marches forward armed.
F1: idle, steel battle axe in right hand at side blade pointed down, round teal shield raised in left hand at chest.
F2: right foot lifts slightly, weight on left.
F3: right foot peak lift, knee bent.
F4: right foot plants forward.
F5: left foot lifts slightly.
F6: left foot peak lift.
F7: left foot plants forward.
F8: returns to idle.
Kettle hat helmet stays on head every frame.
Dark teal tabard sways slightly with steps.
No spinning, no jumping.
Battle axe in right hand and round teal shield in left hand both visible every frame, never dropped, never swapped.
Axe stays identical across all frames: single-bladed curved steel head, wooden haft.
Shield stays identical: round, teal face, iron rim, central iron boss.
Clean pixel art, sharp silhouette.
```

### 10.4 React — Shield Brace Recoil

> 6/1 验证：AI 解读为"举盾防御"而非"身体后退"。对盾兵来说**合理**（"打不动"的视觉直觉），保留这个解读方向，但补 chibi 锚点。

```
Axe soldier takes a hit and braces with his shield.
F1: idle stance, axe in right hand at side, shield raised in left hand at chest.
F2: hit lands, body jolts backward at the chest, shield raises higher to brace, head tilts back slightly.
F3: peak recoil, back foot slides back to brace, shield held high covering chest and lower face, axe arm flings outward for balance, body bent backward.
F4: holds the braced wincing pose, shield still raised high.
F5-6: body slowly straightens, shield lowers back to chest height, axe arm returns to side.
F7: shoulders relax, breath catches.
F8: returns to neutral idle stance.
Feet stay on the ground throughout, no falling down, no spinning, no jumping.
Battle axe stays in right hand every frame, round teal shield stays in left hand every frame, neither dropped, never swapped.
Kettle hat helmet stays on head every frame.
Axe and shield stay identical across all frames.
Sharp weighted hit-reaction with defensive shield brace, clean pixel art, sharp silhouette.
```

### 10.5 Attack — Single-Hand Diagonal Chop (shield up)

> 与赵铁柱的双手过顶大劈区分：本兵是**单手斧斜砍 + 盾全程举着**。silhouette 完全不撞。

```
Axe soldier swings his battle axe in a single-handed diagonal chop, shield held up for guard.
F1: idle stance, axe in right hand at side, round teal shield raised in left hand at chest.
F2-3: pulls the axe up and back over right shoulder with single right hand, body coils, weight shifts to back foot, shield stays raised in left hand.
F4: peak wind up, axe fully cocked back behind right shoulder with single right hand, body coiled on back foot, shield still raised in left hand covering chest.
F5: swings the axe down and forward in a strong diagonal chop from upper-right to lower-left with single right hand, weight shifts forward onto front foot, body leans into the swing, shield stays up.
F6: axe at bottom of the chop, fully extended forward and down across the body to lower left, single-handed grip, shield still raised in left hand.
F7: pulls the axe back up to right side, body recovers upright, shield stays raised throughout.
F8: returns to idle stance with axe at right side, shield raised in left hand at chest.
Feet stay planted on the ground throughout, no spinning, no jumping.
Axe stays in right hand throughout the entire swing, ONE-HANDED, never gripped with both hands.
Round teal shield stays raised in left hand every single frame, never lowered to the ground, never dropped, never swapped to right hand.
Kettle hat helmet stays on head every frame.
Axe stays identical across all frames: single-bladed curved steel head, wooden haft.
Shield stays identical: round, teal face, iron rim, central iron boss.
Sharp weighted single-handed chop motion with shield guard maintained, clean pixel art, sharp silhouette.
```

**关键点**：
- `ONE-HANDED, never gripped with both hands` + `shield stays raised in left hand every single frame` 这两句是关键护栏：AI 在挥砍峰值帧最容易把另一只手也搭上斧（变成双手砍）或者把盾甩下来腾出空间
- 6/1 验证过的 motion blur 拖影应该会继承下来（PixelLab Custom V3 在斧砍类动作上自带）
- silhouette 区分清单：单手斧 + 盾 vs 铁柱（双手大斧）vs 弓兵（弓）vs 剑客（剑） vs 牧师（杖+十字）vs 法师（书）vs 刺客（双匕首）— 帝国 6 兵种 silhouette 全互斥

---

## 十一、验证后搬迁 checklist

每条 prompt 通过 PixelLab 实跑 + 8 方向逐帧审核后：

1. 把 prompt **原文**（不要改字）从本文件复制到 `character-prompt.md` 对应章节：
   - Rotation → §二 末尾追加新的 `2.x`（弓箭手 = 2.4，牧师 = 2.5，法师 = 2.6，刺客 = 2.7，剑客 = 2.8，凌霜 = 2.9，铁柱 = 2.10）
   - Idle / Walking / Attack → §三 末尾追加新的 `3.x`（编号对齐上面 Rotation 的 2.x → 3.x）
2. 把每个 Folder 的 `XXXX` 占位符换成 PixelLab 生成出来的真实 hash 目录名
3. 把 `metadata.json` 里的 rotation prompt 也同步存盘（路径：`art/characters/<character>/metadata.json` 的 `.states[0].character.prompt`）
4. 从本文件**删除**已搬走的章节，并把"待验证清单"对应行状态改成 ✅ 已验证
5. 在 `character-prompt.md` §七 TODO 划掉对应项

**搬迁顺序建议**：rotation 先全部跑完 8 方向通过审核，再开始做动画（per `character-prompt.md` §5.3：rotation 错 → 所有动画都错）。
