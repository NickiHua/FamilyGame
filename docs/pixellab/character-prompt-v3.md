# PixelLab 角色 Prompt v3（批量自动化 / 8 角色 × 5 动作）

> **文档目的**：本文是 `scripts/prompts/characters.yaml` 的**真值源**。脚本只读 yaml，但 yaml 的 prompt 字段必须与本文 §2 / §3 完全一致；改 prompt 时**先改本文**再同步到 yaml。
>
> **与 v1 / v2 / -new 的关系**：
> - v1 (`character-prompt.md`)：6/1 前已验证的 LuLi / SuYao / 帝国斧兵。
> - v2 (`character-prompt-v2.md`)：6/4-6/6 的 cowl / mantle 风格回归实验记录。
> - -new (`character-prompt-new.md`)：7 角色 96×96 + 4-头身的人工初稿。
> - **v3（本文）**：**全部 8 角色 × 5 动作**，采用 6/7 自动化批跑工作流：**128 image_size → 244 canvas**，**3-头身 chibi 锚点**，**禁用 "hood" 词**，明确 z-order 与方向偏置规则。

---

## 0. 与 v2 / -new 的关键差异

| 维度 | v2 / -new | v3（本文） |
|---|---|---|
| Image size | 96×96（落到 ~192 canvas） | **128×128**（落到 ~232-248 canvas） |
| 人体比例 | 4-头身 SD | **3-头身 super-deformed chibi**（每条 rotation prompt 必带锚点） |
| 兜帽词 | `hood lowered down`（v2 验证仍偶尔被 AI 拉起） | **完全禁用 "hood"**，改用 `cowl behind neck` / `shoulder mantle` / `cloth wrap` |
| 长发层级 | 未显式 | **z-order 显式**：`hair drawn IN FRONT OF and OVER the cape/mantle` |
| 方向锚 | 未提示 | **PixelLab `south` = 实际 SW**（整个轮盘逆时针 off-by-one），Unity 映射时记得偏移；prompt 本身不写方向 |
| 角色数 | 7 | **8**（新增啸 Xiao：野性男神箭手皮甲猎人） |
| 动作数 | 4（rotation/idle/walking/attack） | **5**（+react 受击踉跄） |
| 落盘 | 手工跑 + 手贴 prompt | `scripts/pixellab_batch.py` 全自动，按角色名分文件夹、按动作名分子目录 |

---

## 1. 全局设置（写死在 `scripts/pixellab_gen_character.py`）

| 字段 | 值 | 来源 |
|---|---|---|
| `template_id` | `mannequin` | 唯一人形模板 |
| `model` | v3（隐含，POST `/create-character-v3`） | v3 比 v2 在 chibi 头身上更稳 |
| `image_size` | 128×128 | 6/7 决定（结果 canvas 232-248） |
| `view` | `low top-down` | SRPG 等距视角 |
| `detail` | `highly detailed` | v3 doc 默认是 medium；显式调高保住面部细节 |
| `outline` | `single color black outline` | v3 锚点（v3 不强保证 outline 风格） |
| `no_background` | `True` | 透明背景 |
| `enhance_prompt` | `False` | 我们自己写 prompt，禁用 PixelLab 二次扩写 |
| 动画 mode | `v3`（Custom V3） | 不用 built-in template 动画 |
| 动画 frame_count | `8`（偶数 4-16） | 与 v1/v2 一致 |
| 动画 directions | 8 方向全跑 | 见 `pixellab_gen_character.ALL_DIRECTIONS` |
| 轮询间隔 | 60s | 6/7 决定（5s 太频，1 分钟够） |

### 1.1 风格锚点块（每条 rotation prompt **必带**）

```
Fire Emblem GBA style chibi {archetype}, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
{character description},
clean pixel art, vibrant colors, sharp silhouette
```

`{archetype}` 槽位示例：`enemy archer` / `enemy battle priestess` / `ally pegasus knight lance fighter` / `hero heavy axe warrior` / `ally hunter ranger`。

### 1.2 关键护栏（每个角色都吃这套）

1. **禁用 "hood" 词**。需要颈部布料剪影时用 `cowl behind the neck`（披在背后的兜状布）；需要肩部布料时用 `shoulder mantle` / `short cape` / `half cape`。
2. **长发 z-order**：任何有长发 + 任何披风/披肩组合的角色，prompt 末尾必带：
   `hair drawn IN FRONT OF and OVER the shoulder mantle and cape, hair never tucked under any cloth layer.`
3. **武器锚帧**：rotation 描述里同时给出"在哪只手"+"持械方式"+"武器外观"三要素。例：`recurved wooden longbow held in left hand` + `unstrung shape, undrawn` + `brass-bound limbs`。
4. **西式锚点**：所有"东方人"角色（赵铁柱）只通过 `east asian face` + `black hair tied in low ponytail` 表达东方感，**装备 100% 西式**；显式禁用 `samurai / topknot / katana / kimono / oni / horned`。
5. **粉发角色**：用 `pale pink` 而非 `pink`，并显式 `Fire Emblem GBA style ally pegasus knight` 召唤 FE7 Florina 训练样本。

### 1.3 PixelLab 方向偏置（Unity 映射表）

实测 6/6 batches 均确认 PixelLab 的 8 文件方向名与 SRPG 真实朝向有**逆时针 off-by-one**偏移。本文 prompt **不写方向词**（v3 模型自动从 south 输出推 8 方向），但下游 Unity 端导入时按下表映射：

| PixelLab 文件名 | 实际朝向 | Unity 应映射到 |
|---|---|---|
| `south.png` | 实际西南 | SW |
| `south-east.png` | 实际南 | S |
| `east.png` | 实际东南 | SE |
| `north-east.png` | 实际东 | E |
| `north.png` | 实际东北 | NE |
| `north-west.png` | 实际北 | N |
| `west.png` | 实际西北 | NW |
| `south-west.png` | 实际西 | W |

参见 `docs/developing_process/2026-06-07_process.md` §2.5。

---

## 2. Rotation Prompts

### 2.1 帝国弓箭手 EmpireArcher

```
Fire Emblem GBA style chibi enemy archer, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
generic imperial foot archer in european medieval setting,
lean wiry soldier in his 20s with sharp focused face partially visible,
dark teal green tabard over leather and chainmail light armor,
classic western soldier style,
brass and leather trim accents,
open-faced steel nasal helmet (kettle hat style) with no horns and no plume,
brown leather quiver full of arrows strapped on back,
recurved wooden longbow held vertically in left hand, undrawn, brass-bound limbs,
bracer on left forearm, leather glove on right hand, no shield,
clean pixel art, vibrant colors, sharp silhouette
```

### 2.2 帝国牧师 EmpirePriestess

```
Fire Emblem GBA style chibi enemy battle priestess, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
generic imperial church cleric serving the empire in european medieval setting,
stern serious woman in her early 30s with sharp focused face partially visible,
cream off-white robe down to ankles with dark teal green shoulder mantle and dark teal trim on hem and sleeves,
brass trim accents on collar and belt,
classic western church style,
dark brown hair tied in low bun at the back of head,
short white veil pinned by simple brass circlet on forehead, face fully visible,
tall wooden staff with brass cap and small upright brass cross emblem on top, held vertically in right hand,
small leather satchel of healing supplies at left hip,
hair and veil drawn IN FRONT OF and OVER the shoulder mantle, hair never tucked under any cloth layer,
no armor plates, no shield, no helmet,
clean pixel art, vibrant colors, sharp silhouette
```

### 2.3 帝国法师 EmpireMage

```
Fire Emblem GBA style chibi enemy dark mage sorcerer, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
sinister imperial battlemage in european medieval setting,
gaunt severe man in his 40s with sharp cheekbones and grim cold face partially visible,
dark teal green long robe down to ankles with black inner lining and brass trim,
black leather belt with brass buckle at waist, dark teal sash over right shoulder,
classic western sorcerer wizard style,
slicked back jet black hair, no beard,
heavy leather-bound spellbook tome with brass clasps and brass corners, held open in left hand at chest height,
right hand raised to shoulder height with fingers spread in a casting gesture,
small dark amulet hanging on chest,
no armor, no shield, no helmet, no staff,
clean pixel art, vibrant colors, sharp silhouette
```

### 2.4 帝国刺客 EmpireAssassin

```
Fire Emblem GBA style chibi enemy assassin rogue, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
lean swift imperial assassin in european medieval setting,
sharp-faced man in his late 20s with cold narrow eyes and dark stubble partially visible,
dark teal green and black light leather armor over dark grey tunic,
classic western thief rogue style, not ninja,
short messy black hair, dark cloth cowl draped behind the neck across the shoulders,
dark cloth scarf wrapped around neck and pulled up over the nose covering lower half of face, eyes and forehead fully visible,
two short steel daggers, one held in each hand in reverse ice-pick grip,
brass buckles and crossed dark leather belts over chest, leather bracers on both forearms,
no helmet, no shield, no plate armor, no cape,
clean pixel art, vibrant colors, sharp silhouette
```

### 2.5 帝国剑客 EmpireSwordsman

```
Fire Emblem GBA style chibi enemy swordsman duelist, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
skilled imperial duelist swordmaster in european medieval setting,
lean confident man in his late 20s with sharp jaw and a thin diagonal scar across left cheek partially visible,
dark teal green tabard over dark steel breastplate and chainmail sleeves, brass trim accents,
classic western soldier swordmaster style,
short cropped dark brown hair swept back,
one-handed steel longsword held in right hand pointed down at side in a ready guard,
empty left hand at side,
brown leather belt with brass buckle, leather bracers on both forearms,
no helmet, no shield, no cape, no kettle hat,
clean pixel art, vibrant colors, sharp silhouette
```

### 2.6 凌霜 LingShuang

```
Fire Emblem GBA style chibi ally pegasus knight lance fighter, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
graceful alert lance fighter,
young woman early 20s, slender athletic build,
shoulder length pale pink hair tied at the back of head with a single white ribbon, long bangs framing face,
light silver chest plate over white tunic and blue knee-length skirt with armored side panels,
blue half cape pinned at left shoulder flowing behind,
slim silver pauldrons, silver greaves over white boots, white leather gloves,
long western steel cavalry lance held vertically in right hand, lance as tall as her body,
pale pink hair drawn IN FRONT OF and OVER the blue half cape, hair never tucked under any cloth layer,
no helmet, alert poised posture,
clean pixel art, vibrant colors, sharp silhouette
```

### 2.7 赵铁柱 ZhaoTieZhu

```
Fire Emblem GBA style chibi hero heavy axe warrior, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
sturdy powerful two-handed axe fighter,
broad shouldered tall man in his early 30s with east asian face and strong jaw,
short jet black hair tied back in a small low ponytail at the nape of the neck, short trimmed black beard,
heavy silver full plate armor with blue tabard over the chest and brass rivets along the trim,
large silver pauldrons, silver gauntlets, silver greaves,
dark blue half cape from the back of the shoulders,
massive two-handed western great axe with wide double-bladed steel head and long wooden haft, held resting on right shoulder with both hands,
confident grounded stance with feet planted apart,
black ponytail drawn IN FRONT OF and OVER the dark blue half cape, hair never tucked under any cloth layer,
clean pixel art, vibrant colors, sharp silhouette
```

### 2.8 啸 Xiao（新角色：野性男神箭手 / 皮甲猎人）

```
Fire Emblem GBA style chibi ally hunter ranger archer, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
wild rugged forest hunter and master archer,
sharp-eyed man in his late 20s with weather-tanned skin, sharp focused face, light stubble, and a long thin diagonal scar across right cheek,
long messy dark brown hair tied back in a loose low ponytail with a small leather cord, untamed wild bangs framing face,
dark forest green and brown leather hunter armor: leather chest cuirass over dark green sleeveless tunic, brown leather pauldrons reinforced with bone studs, dark green forearm wraps over leather bracers, brown leather belt with brass buckle, brown leather hunting boots,
small grey wolf fur pelt draped over left shoulder as a short shoulder mantle, no hood,
necklace of small carved bone beads at the collar,
recurved wooden hunter longbow with brass-bound limbs held vertically in left hand, undrawn, slightly taller than him,
brown leather quiver full of feathered arrows on back, single hunting knife sheathed at right hip,
dark brown ponytail drawn IN FRONT OF and OVER the grey wolf fur shoulder mantle, hair never tucked under any cloth layer,
no helmet, no plate armor, no shield, no cape,
clean pixel art, vibrant colors, sharp silhouette
```

**风格锚定要点**（啸 = 新角色）：

- `ally hunter ranger archer` 锚到 FE 系列 ranger 职业（FE10 Astrid / FE13 Virion），剪影更"林地猎人"而非"军队弓兵"，与帝国弓箭手（kettle hat + tabard 制服感）拉开距离
- `weather-tanned skin` + `light stubble` + `long messy hair` 三连"野性"锚点，让 chibi 化以后仍有粗犷感
- `grey wolf fur pelt as a short shoulder mantle` 是猎人 silhouette 的关键，且 `no hood` 显式排除（用毛皮披肩代替兜帽功能）
- 武器与啸的师承设定：`recurved wooden hunter longbow with brass-bound limbs`，与帝国弓箭手共享"recurved longbow + 棕色箭袋"基本款，但材质改 `hunter` 调性（无金属装饰，强调木 + 骨 + 皮）
- `bone studs on pauldrons` + `bone beads necklace` 给野性感加细节，比"全皮甲"更有信息密度
- 与帝国弓箭手的区分锚点：**无 kettle hat（露头露脸）**、**狼毛肩披而非 tabard**、**棕绿色（森林系）而非青绿色（帝国军色）**

---

## 3. 动画 Prompts

> **共用约束**（所有 8 帧动画都隐含）：
>
> - `Feet stay planted, no walking, no spinning, no jumping in air.`（idle / attack 类）
> - `Weapon visible every frame, never dropped, never swapped to the other hand.`
> - 长发 + 披肩组合的角色：`Hair stays drawn IN FRONT OF and OVER the cape/mantle every frame.`
> - 任何有兜帽词风险的角色：`Cowl stays behind neck, never up over head at any point.`
> - 风格收尾：`Clean pixel art, sharp silhouette.`
>
> 为节省篇幅，下面只列 8 帧关键动作描述，共用约束不重复（脚本会原样推送，护栏由 prompt 文本自身保证）。

### 3.1 帝国弓箭手 EmpireArcher

**Idle — Archer Breathing**

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

**Walking — Archer Marches Forward Armed**

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
Bow and quiver visible every frame, bow stays in left hand throughout, never dropped or swapped.
Bow stays identical across all frames: wooden recurved longbow, undrawn, held vertical.
Quiver stays identical: brown leather, full of feathered arrows, on back.
Clean pixel art, sharp silhouette.
```

**React — Archer Flinches Backward from Hit**

```
Archer takes a sharp hit and flinches backward.
F1: idle stance, longbow vertical in left hand at side.
F2: hit lands, body jolts backward at the chest, head snaps back slightly, free right hand jerks up reflexively toward chest.
F3: peak flinch, back foot slides back to brace, body bent backward at the waist, eyes squeezed.
F4: holds the bent-back pose, face winces in pain.
F5-6: body slowly straightens up, right hand falls back to side.
F7: shoulders relax, breath catches.
F8: returns to neutral idle stance with bow in left hand at side.
Feet stay on the ground throughout, no falling down, no spinning, no jumping.
Longbow stays in left hand every frame, never dropped, never swapped to right hand.
Kettle hat stays on head. Quiver stays on back.
Bow stays identical across all frames.
Sharp weighted hit-reaction flinch motion, clean pixel art, sharp silhouette.
```

**Attack — Draw and Release Arrow**

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

### 3.2 帝国牧师 EmpirePriestess

**Idle — Priestess Breathing**

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
White veil and brass circlet stay on head every frame.
Dark teal green shoulder mantle drapes over shoulders, cream robe to ankles.
Hair stays drawn IN FRONT OF and OVER the shoulder mantle every frame.
Staff stays identical across all frames: wooden haft, brass cap, small upright brass cross emblem on top.
Clean pixel art, sharp silhouette.
```

**Walking — Priestess Walks Holding Staff**

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
Veil and brass circlet stay on head every frame.
Cream robe with dark teal shoulder mantle flows with steps.
No spinning, no jumping.
Staff visible every frame, never dropped.
Hair stays IN FRONT OF and OVER the shoulder mantle every frame.
Staff stays identical across all frames.
Clean pixel art, sharp silhouette.
```

**React — Priestess Flinches from Hit**

```
Priestess takes a hit and flinches backward.
F1: idle stance, staff vertical in right hand at side, left hand at hip.
F2: hit lands, body jolts backward at the chest, free left hand jerks up to chest reflexively.
F3: peak flinch, back foot slides back to brace, head bows down slightly in pain, eyes squeezed.
F4: holds the bent-back wincing pose.
F5-6: body slowly straightens, left hand falls back to hip.
F7: shoulders relax, breath catches.
F8: returns to neutral idle stance.
Feet stay on the ground, no falling down, no spinning, no jumping.
Staff stays in right hand every frame, never dropped.
Veil and circlet stay on head. Hair stays IN FRONT OF and OVER the mantle every frame.
Staff stays identical across all frames.
Sharp weighted hit-reaction flinch motion, clean pixel art, sharp silhouette.
```

**Attack — Heal / Blessing Cast**

```
Priestess raises her staff to cast a healing blessing.
F1: idle stance, staff vertical at right side, left hand at hip.
F2-3: she lifts the staff up with both hands in front of her chest, head tilts slightly down in prayer.
F4: staff held high above head at peak, brass cross on top glows brightly, free left hand extends forward with open palm in blessing.
F5-6: she lowers the staff forward and down with a soft gesture, releasing the blessing, body leans slightly forward.
F7-8: pulls staff back to vertical resting position at right side, returns to idle.
Feet stay planted, no spinning, no jumping, no walking.
Staff and brass cross visible every frame, never dropped.
Veil and brass circlet stay on head, face stays visible.
Hair stays IN FRONT OF and OVER the shoulder mantle every frame.
Robe and mantle flow naturally with the casting motion.
Soft weighted blessing animation, clean pixel art, sharp silhouette.
```

### 3.3 帝国法师 EmpireMage

**Idle — Mage Breathing with Tome**

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
Slicked back black hair stays the same every frame.
Dark teal robe with black lining and brass trim, dark teal sash over right shoulder.
Tome stays identical across all frames: leather-bound, brass clasps, brass corners, held open.
Clean pixel art, sharp silhouette.
```

**Walking — Mage Walks Holding Tome**

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
Slicked back black hair stays the same every frame.
Dark teal robe with black lining flows with steps.
No spinning, no jumping.
Spellbook tome visible every frame, never closed, never dropped, stays in left hand throughout.
Tome stays identical across all frames.
Clean pixel art, sharp silhouette.
```

**React — Mage Flinches from Hit**

```
Dark mage takes a hit and stumbles back.
F1: idle stance, tome open in left hand at chest, right hand at side.
F2: hit lands, body jolts backward, right hand jerks up to head reflexively.
F3: peak flinch, back foot slides back to brace, head twists aside in pain, eyes squeezed.
F4: holds the bent-back wincing pose.
F5-6: body slowly straightens, right hand falls back to side.
F7: shoulders settle, sash flutters back into place.
F8: returns to neutral idle with tome open in left hand.
Feet stay on the ground, no falling down, no spinning, no jumping.
Tome stays open in left hand every frame, never closed, never dropped.
Slicked back black hair stays the same every frame.
Tome stays identical across all frames.
Sharp weighted hit-reaction flinch motion, clean pixel art, sharp silhouette.
```

**Attack — Dark Spell Cast from Tome**

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
Slicked back black hair stays the same every frame.
Robe flows naturally with the casting motion.
Sinister weighted dark casting animation, clean pixel art, sharp silhouette.
```

### 3.4 帝国刺客 EmpireAssassin

**Idle — Assassin Crouched Ready**

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
Cloth scarf stays pulled up over nose, eyes visible.
Cowl stays behind neck across the shoulders, never up over head at any point.
Dark teal and black leather armor.
Daggers stay identical across all frames: short steel blades, dark leather grips.
Clean pixel art, sharp silhouette.
```

**Walking — Assassin Sneaks Forward**

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
Cloth scarf stays pulled up over nose, eyes visible.
Cowl stays behind neck across the shoulders, never up over head.
No spinning, no jumping.
Two daggers visible every frame in reverse grip, never dropped or swapped.
Daggers stay identical across all frames.
Clean pixel art, sharp silhouette.
```

**React — Assassin Flinches from Hit**

```
Assassin takes a hit and recoils backward in a sharp crouch.
F1: idle ready stance, two daggers in reverse grip at sides.
F2: hit lands, body jerks backward, both arms swing outward wide for balance.
F3: peak recoil, body bent backward in a deeper crouch, back foot slides back, head snaps to one side in pain.
F4: holds the deep crouched wincing pose, daggers held wide.
F5-6: body slowly recovers from the crouch, arms pull back in toward body.
F7: shoulders settle, daggers return to sides.
F8: returns to neutral crouched ready idle.
Feet stay on the ground throughout, no falling down, no spinning, no jumping.
Both daggers stay in reverse grip every frame, one in each hand, never dropped, never swapped to forward grip.
Cloth scarf stays up over nose, cowl stays behind neck across the shoulders, never up.
Daggers stay identical across all frames.
Sharp snappy weighted hit-reaction flinch motion, clean pixel art, sharp silhouette.
```

**Attack — Cross Dagger Slash**

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
Cloth scarf stays up over nose, cowl stays behind neck across the shoulders, never up.
Fast snappy weighted slash motion, clean pixel art, sharp silhouette.
```

### 3.5 帝国剑客 EmpireSwordsman

**Idle — Swordsman Breathing**

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
Short dark brown hair stays the same every frame, no helmet at any point.
Dark teal tabard over dark steel breastplate.
Sword stays identical across all frames: one-handed steel longsword, brown grip, simple crossguard.
Clean pixel art, sharp silhouette.
```

**Walking — Swordsman Marches Forward**

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
Short dark brown hair stays the same every frame, no helmet.
Dark teal tabard sways slightly with steps.
No spinning, no jumping.
Longsword visible in right hand every frame, never dropped, never swapped to left hand.
Sword stays identical across all frames.
Clean pixel art, sharp silhouette.
```

**React — Swordsman Flinches from Hit**

```
Swordsman takes a hit and flinches backward, sword still in hand.
F1: idle stance, longsword in right hand at side pointed down.
F2: hit lands, body jolts backward at the chest, left hand jerks up to chest reflexively.
F3: peak flinch, back foot slides back to brace, body bent backward at the waist, scar-side face winces.
F4: holds the bent-back wincing pose, sword tip dips slightly toward ground.
F5-6: body slowly straightens, left hand falls back to side.
F7: shoulders relax, breath catches.
F8: returns to neutral idle stance with sword at right side.
Feet stay on the ground throughout, no falling down, no spinning, no jumping.
Longsword stays in right hand every frame, never dropped, never swapped to left hand.
Short dark brown hair stays the same every frame, no helmet.
Sword stays identical across all frames.
Sharp weighted hit-reaction flinch motion, clean pixel art, sharp silhouette.
```

**Attack — Forward Lunge Thrust**

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
Short dark brown hair stays the same every frame, no helmet.
Sword stays identical across all frames.
Sharp precise weighted thrust motion, clean pixel art, sharp silhouette.
```

### 3.6 凌霜 LingShuang

**Idle — Pegasus Knight Breathing**

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
Pale pink hair tied with white ribbon stays the same every frame, no helmet.
Blue half cape sways gently from left shoulder.
Hair stays IN FRONT OF and OVER the blue half cape every frame.
Lance stays identical across all frames: long steel spearhead, wooden haft, tall as her body.
Clean pixel art, sharp silhouette.
```

**Walking — Pegasus Knight Walks with Lance**

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
Pale pink hair with white ribbon stays the same every frame, no helmet.
Blue half cape flows with steps from left shoulder.
No spinning, no jumping.
Lance visible every frame in right hand, never dropped, never swapped to left hand, stays vertical.
Hair stays IN FRONT OF and OVER the blue half cape every frame.
Lance stays identical across all frames.
Clean pixel art, sharp silhouette.
```

**React — Pegasus Knight Flinches from Hit**

```
Pegasus knight takes a hit and flinches backward, lance still in hand.
F1: idle stance, lance vertical in right hand at side, left hand at side.
F2: hit lands, body jolts backward at the chest, left hand jerks up to chest reflexively, lance tilts slightly.
F3: peak flinch, back foot slides back to brace, body bent backward at the waist, hair and half cape thrown back.
F4: holds the bent-back wincing pose, lance tip dips slightly.
F5-6: body slowly straightens, left hand falls back to side.
F7: shoulders relax, half cape settles.
F8: returns to neutral idle stance.
Feet stay on the ground throughout, no falling down, no spinning, no jumping.
Lance stays in right hand every frame, never dropped, never swapped to left hand.
Pale pink hair with white ribbon stays the same every frame, no helmet.
Hair stays IN FRONT OF and OVER the blue half cape every frame.
Lance stays identical across all frames.
Sharp weighted hit-reaction flinch motion, clean pixel art, sharp silhouette.
```

**Attack — Lance Thrust**

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
Pale pink hair with white ribbon stays the same every frame, no helmet.
Blue half cape flows with the thrust motion, hair stays IN FRONT OF and OVER it.
Lance stays identical across all frames.
Sharp weighted spear thrust motion, clean pixel art, sharp silhouette.
```

### 3.7 赵铁柱 ZhaoTieZhu

**Idle — Heavy Warrior Breathing**

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
Short black hair tied in low ponytail and short black beard stay the same every frame.
Heavy silver full plate armor with blue tabard, dark blue half cape from back.
Black ponytail stays IN FRONT OF and OVER the dark blue half cape every frame.
Axe stays identical across all frames: wide double-bladed steel head, long wooden haft.
Clean pixel art, sharp silhouette.
```

**Walking — Heavy Warrior Marches Forward**

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
Short black hair in low ponytail and black beard stay the same every frame.
Blue tabard and dark blue half cape sway with heavy steps.
No spinning, no jumping.
Great axe stays on right shoulder gripped with both hands every frame, never dropped, never swapped to one hand.
Black ponytail stays IN FRONT OF and OVER the dark blue half cape every frame.
Axe stays identical across all frames.
Heavy weighted marching motion, clean pixel art, sharp silhouette.
```

**React — Heavy Warrior Flinches from Hit**

```
Heavy axe warrior takes a heavy hit and staggers backward, great axe still on shoulder.
F1: idle stance, great axe resting on right shoulder gripped with both hands.
F2: hit lands hard, body jolts backward at the chest, head snaps back slightly.
F3: peak stagger, back foot slides back heavily to brace, body bent backward at the waist, free balance from both hands keeping axe on shoulder.
F4: holds the staggered wincing pose, armor plates clatter.
F5-6: body slowly straightens up, weight shifts back over center.
F7: shoulders settle, half cape falls back into place.
F8: returns to neutral idle stance.
Feet stay on the ground throughout, no falling down, no spinning, no jumping.
Both hands stay on the haft of the great axe every single frame, axe stays on right shoulder, never one-handed, never dropped.
Short black hair in low ponytail and black beard stay the same every frame.
Black ponytail stays IN FRONT OF and OVER the dark blue half cape every frame.
Axe stays identical across all frames.
Heavy slow weighted stagger hit-reaction motion, clean pixel art, sharp silhouette.
```

**Attack — Heavy Two-Handed Overhead Cleave**

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
Short black hair in low ponytail and black beard stay the same every frame.
Blue tabard and dark blue half cape flow with the heavy swing, ponytail stays IN FRONT OF and OVER the cape.
Axe stays identical across all frames.
Heavy slow weighted two-handed cleave motion, clean pixel art, sharp silhouette.
```

### 3.8 啸 Xiao

**Idle — Hunter Ranger Breathing**

```
Hunter ranger stands in idle breathing pose.
F1: idle stance, recurved hunter longbow held vertically in left hand at side, right hand relaxed at side, quiver of arrows visible on back.
F2-3: chest gently rises with breath, shoulders lift slightly, wolf fur mantle settles.
F4: peak inhale, body slightly taller.
F5-6: chest gently falls, shoulders settle.
F7: deepest exhale.
F8: returns to neutral idle.
Feet stay planted, no walking, no spinning.
Recurved hunter longbow in left hand and brown leather quiver on back both visible every frame, never disappear, never dropped, never swapped.
Long dark brown ponytail and wild bangs stay the same every frame, no helmet.
Grey wolf fur shoulder mantle drapes over left shoulder.
Hair stays IN FRONT OF and OVER the wolf fur shoulder mantle every frame.
Bow stays identical across all frames: wooden recurved hunter longbow with brass-bound limbs, undrawn.
Clean pixel art, sharp silhouette.
```

**Walking — Hunter Ranger Stalks Forward**

```
Hunter ranger moves forward in a quiet stalking step, bow in left hand.
F1: idle, recurved hunter longbow in left hand at side, quiver on back, right hand at side.
F2: right foot lifts slightly, weight on left, body stays slightly low.
F3: right foot peak lift, knee bent.
F4: right foot plants forward softly.
F5: left foot lifts slightly.
F6: left foot peak lift.
F7: left foot plants forward softly.
F8: returns to idle.
Long dark brown ponytail and wild bangs stay the same every frame, no helmet.
Wolf fur mantle and forearm wraps sway with steps.
No spinning, no jumping.
Bow and quiver visible every frame, bow stays in left hand throughout, never dropped or swapped.
Hair stays IN FRONT OF and OVER the wolf fur shoulder mantle every frame.
Bow stays identical across all frames: wooden recurved hunter longbow, undrawn, held vertical.
Quiver stays identical: brown leather, full of feathered arrows, on back.
Clean pixel art, sharp silhouette.
```

**React — Hunter Ranger Flinches from Hit**

```
Hunter ranger takes a hit and twists backward in a wild flinch.
F1: idle stance, hunter longbow vertical in left hand at side.
F2: hit lands, body jolts backward at the chest, free right hand jerks up reflexively to chest, ponytail and wolf fur mantle thrown back.
F3: peak flinch, back foot slides back to brace, body twisted backward at the waist, sharp wincing face.
F4: holds the twisted bent-back pose.
F5-6: body slowly straightens up, right hand falls back to side.
F7: shoulders relax, mantle settles back.
F8: returns to neutral idle stance with bow in left hand at side.
Feet stay on the ground throughout, no falling down, no spinning, no jumping.
Hunter longbow stays in left hand every frame, never dropped, never swapped to right hand.
Long dark brown ponytail and wild bangs stay the same every frame, no helmet.
Hair stays IN FRONT OF and OVER the wolf fur shoulder mantle every frame.
Bow stays identical across all frames.
Sharp wild weighted hit-reaction flinch motion, clean pixel art, sharp silhouette.
```

**Attack — Hunter Snap Shot**

```
Hunter ranger draws bow and releases an arrow in a fast snap shot.
F1: idle stance, recurved hunter longbow held vertical in left hand at side, quiver of arrows on back.
F2: raises bow up in front of body with left arm, right hand reaches back over right shoulder to grab an arrow from the quiver.
F3: nocks arrow on bowstring, both hands now on the bow, left arm extends forward holding the bow.
F4: begins drawing the string back with right hand quickly, body squares to target, weight shifts to back foot, focused predator gaze.
F5: full draw at peak, bowstring pulled back to anchor point near right cheek, arrow horizontal pointing forward, body coiled with wild tension.
F6: releases the arrow, bowstring snaps forward, right hand opens and pulls back past the ear in follow-through, arrow shown leaving the bow forward.
F7: lowers bow arm, body relaxes from the shot, wolf fur mantle settles.
F8: returns to idle stance with bow vertical in left hand at side.
Feet planted, no spinning, no jumping, no walking.
Bow stays in left hand throughout, never dropped, never swapped to right hand.
Bow and quiver visible every frame.
Long dark brown ponytail and wild bangs stay the same every frame.
Hair stays IN FRONT OF and OVER the wolf fur shoulder mantle every frame.
Bow stays identical across all frames: wooden recurved hunter longbow with visible string.
Fast wild weighted snap shot motion, clean pixel art, sharp silhouette.
```

---

## 4. yaml 同步约定

- `scripts/prompts/characters.yaml` 是脚本的输入，**字段值必须与本文 §2 / §3 的代码块逐字一致**。
- 修改 prompt 时：**先改本文 → 再改 yaml → 跑 batch**。如果不一致，本文为准。
- `character_id`、`status`、`job_ids`、`failed_jobs` 是脚本运行时回写到 yaml 的，本文不维护这些字段。
- 重新生成单个动作：把对应 action 的 `status` 改成 `new` 或加 `--force <action>` 跑 batch。

## 5. TODO

- [ ] 8 角色 rotation 全部跑完一轮、人工审 8 方向
- [ ] 通过的 rotation 才开下游 4 个动作（per 既定经验：rotation 错则动画必错）
- [ ] react 动作首次落地，验证"踉跄"vs"飞出去"的尺度
- [ ] 启 batch 前先 `--dry-run` 看 plan
- [ ] 跑完后把方向偏置映射（§1.3）正式落到 Unity sprite import 配置
