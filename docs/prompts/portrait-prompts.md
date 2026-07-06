# 立绘 / 头像 Prompt 源 · 《幻世纪》FantacyCentry

> **配套工序**：[`docs/pipelines/portrait-asset-pipeline.md`](../pipelines/portrait-asset-pipeline.md)。
> **模型入口**：`scripts/gpt_transparent_image_generation.py`（Image API，**不 rewrite prompt → 逐字使用 → 用英文**）。
>
> **结构**：§1 公用风格后缀 → §2 概念图版式（公用）→ §3 各角色概念图 prompt → §4 立绘子 prompt（公用，`--ref` 概念图）→ §5 胸像子 prompt（公用，`--ref` 概念图）。
>
> **透明规则（务必记住，2026-07-04 A/B 修正）**：
> - **全部 `--background opaque`**（概念图 / 立绘 / 胸像都是）。
> - ⚠️ `background=transparent` **会掉质量 + 把白袍等浅色区域掏透明**（实测）；更别把「transparent background」写进 prompt 文本（伤脸）。
> - **透明由事后 rembg（`isnet-anime` 模型）抠**：白底白袍不能颜色 flood-fill，rembg 语义分割干净,发丝/软边也好。
> - **胸像走 §5 的 2×2 网格**一次出 4 表情（分开单出会衣着漂移）。

---

## 1. 公用风格后缀（`_PORTRAIT_STYLE` · 追加到每条末尾）

```
Classic modern Japanese SRPG / commercial JRPG character-art style: clean and refined, smooth
natural lineart, soft cel-shading with a light painterly touch, soft unified lighting, vivid but
not oversaturated colours. Slender natural body proportions, tasteful Japanese-anime facial
aesthetics, an elegant yet practical fantasy costume that is restrained (not over-decorated, not
gaudy). Strong class identity and character identity, cohesive with a single unified party art
direction so every character reads as one commercial JRPG cast. High-quality, commercial-grade
illustration. NO text, NO labels, NO logo, NO watermark, NO signature, NO border, NO UI elements.
```

---

## 2. 概念图版式（`_PORTRAIT_CONCEPT_LAYOUT` · 公用 · 1024x1024 · 不透明）

> 出一张设定图：**右=全身立绘，左=5 表情胸像列**（正常/开心/悲伤/愤怒/疑惑）。中性灰底，当风格 + 身份锚。

```
A high-quality character design reference sheet for an original, commercial Japanese tactical RPG
(SRPG). FIXED LAYOUT: on the RIGHT, ONE complete full-body character portrait — the ENTIRE figure
from the very top of the head down to the feet must be FULLY inside the frame, standing upright in
a dignified natural pose, drawn SMALL enough that there is clear empty margin ABOVE the head and
BELOW the feet; absolutely nothing cropped (do not let the head, hair, held staff or feet touch or
run off any edge). On the LEFT, a single vertical column of FIVE face / bust expression headshots of
the SAME character, evenly stacked top to bottom in this order: neutral, happy, sad, angry, puzzled.
Plain flat neutral light-grey studio background.
FRAMING CONSTRAINT (obey strictly, framing priority over aesthetics): frame as a full-body long
shot; the entire head, hair, both feet and every expression headshot must sit fully inside the
canvas with clear empty padding above and below; NO cinematic or fashion crop; if anything does not
fit, ZOOM THE CAMERA OUT until it fully fits.
```

> **裁脸防坦 (重要)**：gpt-image-1.5 **1:1 正方形 + low 最容易裁头/脸**（Reddit r/OpenAI 实测 + 我们自己踩坑验证），且此时文字取景约束**常被忽略**。真正管用的是 **用非正方形尺寸**（设定图用横版 1536x1024 装「左5头像+右全身」，立绘用竖版 1024x1536）+ **提质量到 medium/high**。相机约束块是辅助。

---

## 3. 各角色概念图 prompt

### 3.1 苏瑶 SuYao — 牧师 / 圣职治疗（法系辅助）✅ 首个

> Domain id = `SuYao`。队伍法系辅助：治疗 + 神圣辅助 + 少量攻击法术（Lightning / IceSpike / Heal）。
> **完整 prompt = §2 版式 + 下面角色描述 + §1 风格后缀**（脚本 `suyao-concept` 预设已拼好）。

```
CHARACTER — Su Yao, the party's priest / holy healer (gentle magic support).
AGE / GENDER: an 18-year-old girl.
BUILD: slender and youthful, about 6.5 heads tall — NOT chibi, NOT a tall adult.
HAIR: long straight silver hair flowing past the waist, centre-parted with soft bangs framing the face.
EYES: clear blue.
FACE: delicate gentle features with a calm, warm, kindly, trustworthy expression.
OUTFIT (white-and-gold priestess): a floor-length long-sleeved white robe / dress with gold hem trim
and a decorative gold front panel, cinched by a gold waist sash; a short white shoulder cape edged
with fine gold scrollwork, fastened at the throat with a small gem clasp; the head is bare (NO hood,
NO veil) so the silver hair shows fully; white-and-gold slippers.
PALETTE: white + pale gold, silver hair, a single blue gem accent — restrained, holy, lightweight.
SIGNATURE STAFF: one elegant holy staff — a slender silver shaft topped with an ornate gold head that
holds a faceted blue teardrop crystal flanked by a pair of small white angel wings; a healing /
sacred implement, NOT an aggressive weapon.
CLASS READ: unmistakably a priest / healer — holy robe + staff, carries no weapon; dignified, calm,
non-aggressive posture.
DETAIL: keep the whole design CLEAN and RESTRAINED — flat cel-shading, controlled gold trim, NO busy
over-detailing, no cluttered ornament, no heavy painterly noise.
```

> 肤色故意不写（日式西幻 JRPG 默认偏白）。上述特征锁定自已认可的 medium 概念图。

> 跑法（**调 API 前必确认**）：
> ```
> .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py suyao-concept
> ```
> 默认 `--background opaque --size 1024x1024`，输出落 `art_undecided/portraits/suyao/`。

### 3.2 LingShuang — 枪战士 / 前线近战（Lancer）

> Domain id = `LingShuang`。前线长枪近战：力量 + 速度 + 优雅。**sprite**：粉发白蝴蝶结高马尾 / 白银轻铠 / 蓝披风 / 长枪 / 蓝眼。
> 比苏瑶更**成熟高挑**（25 岁 vs 18）→ build 约 7 头身。完整 prompt = §2 版式 + 下面角色描述 + §1 风格后缀。

```
CHARACTER — Ling Shuang, the party's front-line lancer / spear knight.
AGE / GENDER: a 25-year-old woman.
BUILD: tall, mature and athletic, about 7 heads tall — a poised adult warrior, clearly taller and
more grown-up than the young priest, NOT chibi.
HAIR: long pink hair worn in a high PONYTAIL tied with a large white bow, soft bangs framing the
face; the ponytail is long and flowing, kept as a CLEAN, COHESIVE shape with smooth strands — avoid
lots of messy, scattered flyaway strands.
EYES: clear blue.
FACE: beautiful, mature features with a confident, determined, spirited and gallant expression;
reliable and dignified.
OUTFIT (light fantasy knight): sleek, elegant, finely-crafted LIGHT PLATE knight armour — mainly
white and silver with subtle pink accents — refined with delicate engraved trim, classic
Japanese-fantasy, practical and NOT revealing; well-shaped cuirass, pauldrons, gauntlets and greaves
over a fitted underlayer. NO cape, NO cloak.
PALETTE: white + silver armour, pink hair with pink accents — clean and knightly.
SIGNATURE WEAPON: one long, slender, elegant SPEAR / lance with a refined silver blade, held upright;
natural realistic weapon proportions befitting an elite lancer (a real spear, not oversized).
CLASS READ: unmistakably a front-line spear knight — light armour + long spear, standing upright in a
confident, disciplined yet elegant stance.
DETAIL: keep the design CLEAN and COHESIVE — flat cel-shading; refined, tasteful armour detailing is
welcome but no chaotic clutter and no heavy painterly noise.
```

> 跑法（**调 API 前必确认**）：
> ```
> .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py lingshuang-concept
> ```
> 默认 `--background opaque --size 1536x1024`，输出落 `art_undecided/portraits/lingshuang/`。

### 3.3 LuLi 陆离 — 剑士（Swordsman，男主）— **合并版式**（右立绘 + 左 4 胸像）

> Domain id = `LuLi`。**新方法**：立绘 + 4 胸像**同一张图一次生成** → 衣着必然一致（解决分开出的漂移问题）。
> 版式 `_PORTRAIT_SHEET_4`：**右=全身立绘，左=4 个腰部以上胸像**（表情用 `--busts` 定），1536×1024 横版 opaque。之后右边切立绘、左列切 4 胸像。
> 褐发 / 蓝眼 / 深蓝披风（按 sprite），砍掉「英雄气质」类虚词，只留具体视觉。

```
CHARACTER — Lu Li, the party's protagonist swordsman.
AGE / GENDER: a 20-year-old young man.
BUILD: slender, athletic and fit, tall, about 7.5 heads.
HAIR: short brown hair, tidy with natural bangs.
EYES: clear blue.
FACE: handsome youthful features with a bright, confident, genuine look and an easy natural smile.
OUTFIT: white LIGHT knight armour with a DEEP BLUE cape; refined and practical, flexible yet
protective, classic Japanese-fantasy, NOT over-complex and NOT gaudy; clean and crisp.
PALETTE: white + silver armour, a deep blue cape, brown hair — clean and knightly.
SIGNATURE WEAPON: an elegant LONG SWORD worn at the waist in a simple refined scabbard with a clean
guard; natural proportions befitting a young kingdom swordsman.
CLASS READ: unmistakably a melee swordsman — light armour + sheathed long sword, standing upright in
a confident, relaxed stance, one hand resting naturally near the sword hilt.
DETAIL: keep the design CLEAN and RESTRAINED — flat cel-shading, NO busy over-detailing, no heavy
painterly noise.
```

> 跑法（**调 API 前必确认**），4 胸像 = 微笑 / 平静 / 愤怒 / 难过：
> ```
> .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py luli-sheet ^
>   --quality medium ^
>   --busts "a warm genuine smile|calm and composed, NOT smiling|angry, frowning and stern|sad and sorrowful"
> ```
> 输出落 `art_undecided/portraits/luli/`。切图：右全身→立绘，左列 4 等分→4 胸像，各自 rembg。

### 敌方设计通则（§3.4–3.6）

> **配色**：帝国军统一 **深青绿(teal-green) + 钢灰 + 黄铜 + 棕皮** 的暗沉军色，和主角团(白/金/银/粉/蓝)**明确拉开**。
> **眼睛/脸(已定)**：杂鱼 = **冷峻小眼**(可见但小而锐利、阴冷,**非**主角大眼)；队长 = **闭合面甲、整脸藏盔里(无脸无眼)**。参考 PixelLab `docs/pixellab/character-prompt-v3.md` §2.1 的帝国配色/装备语言。
> **版式/胸像(已定)**：每个敌人 = **一张 `_PORTRAIT_SHEET_1`**(右全身立绘 + 左 1 个平常态胸像)。杂鱼用 **medium**,队长用 **high**。预设：`empirearcher-sheet` / `empireaxe-sheet` / `empirecaptain-sheet`。

### 3.4 EmpireArcher 帝国弓箭手（杂鱼）

```
CHARACTER — a generic Empire foot archer: a faceless rank-and-file enemy mook, NOT a named hero.
AGE / GENDER / BUILD: a lean, wiry man in his 20s, ordinary soldier build, about 7 heads.
FACE / EYES: small, narrow, dull, mean eyes — a coarse, common, unremarkable soldier face; low-brow
and slightly brutish, NOT noble, NOT heroic, NOT the big righteous eyes of the heroes.
OUTFIT (imperial): an open-faced steel nasal / kettle-hat helmet topped with a short dark-green
feather PLUME / crest on top; a dark TEAL-GREEN tabard over brown leather and chainmail light armour;
brass and leather trim; a bracer on the left forearm.
PALETTE: dark teal-green + steel grey + brown leather + brass — drab imperial military colours (NOT
the bright white/gold of the heroes).
SIGNATURE WEAPON: a recurved wooden longbow with brass-bound limbs held in hand, and a brown leather
quiver of arrows on the back.
CLASS READ: a plain imperial foot archer.
DETAIL: CLEAN and RESTRAINED, flat cel-shading; grim, plain, anonymous — no individual-hero focus.
```

### 3.5 EmpireAxe 帝国斧兵（杂鱼）

```
CHARACTER — a generic Empire axe infantryman: a faceless rank-and-file enemy mook, NOT a named hero.
AGE / GENDER / BUILD: a burly, broad, gruff man, heavy soldier build, about 6.5–7 heads.
FACE / EYES: cold, small, narrow, hard eyes — grim and mean, deliberately NOT big hero eyes; a thick
beard and a hard scowling mouth; a plain anonymous soldier face.
OUTFIT (imperial): a steel helmet with small angular side ornaments; a dark TEAL-GREEN tabard over
steel and chainmail armour; brass trim and brown leather straps.
PALETTE: dark teal-green + steel + brass + brown leather.
SIGNATURE WEAPON: a one-handed steel battle axe in one hand, and a round wooden shield with a steel
boss on the other arm.
CLASS READ: a plain imperial axe infantry soldier.
DETAIL: CLEAN and RESTRAINED, flat cel-shading; grim, plain, anonymous.
```

### 3.6 EmpireCaptain 帝国队长（精英 / 小 BOSS，新角色）

```
CHARACTER — an Empire Captain: an elite enemy officer / mini-boss, more imposing and characterful
than the rank-and-file mooks, but still a grim antagonist.
AGE / GENDER / BUILD: a tall, imposing armoured man with a commanding presence, about 7.5 heads.
FACE / EYES: he wears a CLOSED VISORED steel helm — the face is fully hidden behind the visor, an
intimidating faceless elite (only a dark narrow eye-slit, no visible eyes).
OUTFIT (imperial elite): heavier, finer SILVER full plate armour with dark TEAL-GREEN and brass trim
and a captain's insignia; a dark green cape / cloak from the shoulders; clearly more ornate than the
common soldiers.
PALETTE: silver steel + dark teal-green + brass + a dark green cape.
SIGNATURE WEAPON: an elegant steel longsword in one hand and a heater / kite shield bearing the
imperial emblem on the other arm.
CLASS READ: an armoured imperial captain / knight-officer — plainly a cut above the mooks.
DETAIL: refined but grim; imposing, disciplined, sinister authority; flat cel-shading, no clutter.
```

---

## 4. 立绘子 prompt（`_PORTRAIT_FULL` · 公用 · 竖版 1024x1536 · **透明参数** · `--ref` 概念图）

> 全身立绘，拿概念图当身份 + 风格参考，保持同一张脸 / 发 / 服装 / 配色。
> 通过 `--background transparent` 出真 alpha —— **prompt 里不提透明**。

```
Using the attached image as the exact character and style reference, generate ONE single COMPLETE
FULL-BODY character portrait (tachie / 立绘) of the SAME character — full length from head to toe,
both feet fully visible, standing upright in an elegant natural pose, the whole figure centred with
generous empty margin on all four sides and nothing cropped or touching any edge. Keep the IDENTICAL
face, hairstyle, hair colour, costume, colours and props (including the staff) as the reference
character.
FRAMING CONSTRAINT (obey strictly, framing priority over aesthetics): frame as a full-body long
shot; the entire head, hair, held staff and both feet must sit fully inside the canvas with clear
empty padding above the head and below the feet; NO cinematic or fashion crop; if anything does not
fit, ZOOM THE CAMERA OUT until it fully fits.
[+ 该角色 §3 描述 + §1 风格后缀]
```

> 立绘用**竖版 1024x1536**(天然适配站姿全身,也避开 1:1 裁脸)。

> 苏瑶跑法：
> ```
> .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py suyao-full ^
>     --ref art/portraits/suyao/concept.png
> ```

---

## 5. 胸像子 prompt（`_PORTRAIT_BUST` · 公用 · 方版 1024x1024 · **透明参数** · `--ref` 概念图）

> 半身胸像（胸部以上，正面），逐表情各出一张。身份由 `--ref` 概念图保证，故此 prompt **角色无关、全队通用**。
> `{expression}` 由 `--expression` 填（`neutral` / `happy` / `sad` / `angry` / `puzzled`）。

```
Using the attached image as the exact character and style reference, generate ONE single half-body
bust portrait (head and chest, facing the viewer) of the SAME character showing a clear, distinct
{expression} facial expression. Keep the IDENTICAL face, hairstyle, hair colour, costume and colours
as the reference character. Frame the bust centred with the ENTIRE head and hair fully inside the
canvas and clear empty space above the head — never crop the top of the head or hair; nothing
cropped.
[+ §1 风格后缀]
```

> 苏瑶「开心」表情跑法：
> ```
> .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py portrait-bust ^
>     --ref art/portraits/suyao/concept.png --type suyao --expression happy
> ```
> 5 个表情各跑一次（每次都是付费调用，**逐次确认**）。

---

## 6. 备注

- **概念图不满意就重出概念图**，别在崩脸的立绘上补救 —— 锚不稳，下游全歪。
- **表情词**建议就用英文单词（neutral/happy/sad/angry/puzzled）；要更细可在 `--expression` 里写短语（如 `a soft gentle smile`）。
- 生产资产（立绘/胸像）出图后**必做 alpha 清噪 + 裁 bbox**（见 pipeline §5）。
- 队伍其他角色（陆离 LuLi 剑士 / 小 Xiao 弓手 / 敌方）照 §3 加一节角色描述即可复用 §2/§4/§5。
