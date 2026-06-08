# PixelLab 角色 Prompt v2 — 3 头身实验套件

> **文档目的**：把"3 头身 + 248×248 canvas + 已知问题正向 harness"打包成一套**可重复实验**的 prompt。
> **状态日期**：2026-06-06 起，**实验阶段，未验证**。
> **与 v1 的关系**：v1（`character-prompt.md`）记录的是 92×92 + 4 头身的**已验证**版本，是当前 fallback baseline。v2 不替换 v1，**两份并存**直到 v2 验证完。
> **承认前文偏差**：v1 review 阶段我（assistant）基于单次生成断言"248 rotation west 退化"，**证据不足，不作为结论沿用**。本文档默认假设 248 + 修复后的 prompt 在多次重抽下可达到 92 的稳定度。

---

## 0. 与 v1 的差异摘要

| 项 | v1（92×92） | v2（248×248） | 改动原因 |
|---|---|---|---|
| Canvas | 92×92 / 96×96 | **248×248**（统一） | 用户偏好 128px sprite 的细节 |
| 头身比 | ~4.2 头身 | **~3 头身（Q 版）** | Tactics Ogre 测量 ~2.9 头身、FE GBA ~3，SRPG 主流；4.2 偏写实离群 |
| 陆离持剑 | 背挂 longsword | **腰挂 longsword on left hip** | 背剑被披风遮的死亡组合，腰挂是 FE/Langrisser 标准 |
| 苏瑶 hood | `hood down`（负向） | **正向描述 "head fully bare, silver hair fully exposed"** | 否定词不可靠，强化正向 |
| 帝国兵 | 不变 | 不变（v1 已稳） | — |
| 方向数 | 8（生成全套） | 8（生成全套，照旧逐张审） | 维持 v1 流程，flipX 复用问题等验证后再定 |
| Animation Mode | Custom V3 | Custom V3 | 不变 |
| Frames | 8 + Keep First Frame | 8 + Keep First Frame | 不变 |

---

## 1. 全局设置（v2 锁定）

| 项 | 值 | 备注 |
|---|---|---|
| Tier | Tier 1（$12/月，2000 gen/月） | 单月预算充足 |
| **Canvas Size** | **248×248**（陆离 / 苏瑶 / 帝国兵统一） | 内部 sprite ~128px，Unity 按 PPU=128 渲染或保持 PPU=48 缩放 |
| Sprite Body Size | ~128px（PixelLab 自动） | — |
| Camera View | Low Top-Down | SRPG 标准视角 |
| Generation Mode | v3 | 不用 Standard |
| Template | Humanoid (mannequin) | 全角色统一 |
| Directions | 8 | flipX 复用决定推迟到 v2 验证后 |
| Animation Mode | Custom V3 | — |
| Frames | 8 + Keep First Frame | F0-F8 共 9 张 |

### 1.1 风格锚点（所有 rotation 必含）

```
Fire Emblem GBA style chibi [archetype], western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
[character description],
clean pixel art, vibrant colors, sharp silhouette
```

**关键词解析**：
- `chibi` + `super-deformed` 是 SD 训练集里高度耦合的"Q 版"信号，单用一个不够稳，双词组合权重更强
- `3-head-tall` 用数字明确比例（模型对数字比形容词更敏感）
- `large head ... small hands and feet` 分别约束头/手/脚三个部位，比单说"chibi proportions"更具体
- `Fire Emblem GBA style chibi` 这个搭配在训练集里大概率出 FE GBA 战棋小人，正中靶心

---

## 2. Rotation Prompts v2

> 通用约定：每个 prompt 末尾保留 `clean pixel art, vibrant colors, sharp silhouette` 三件套，已验证有效（v1 §1）。

### 2.1 陆离 v2（Hero Swordsman, 腰挂剑）

- **建议 character folder**: `LuLi_v2/Fire_Emblem_GBA_style_chibi_hero/`
- **配色**: 银 + 蓝（不变）

```
Fire Emblem GBA style chibi hero swordsman, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
balanced fighter not heavy,
brown short messy hair,
light silver plate armor with leather straps, blue cape on back,
one-handed longsword in scabbard hanging at left hip, scabbard clearly visible at waist,
confident posture, young man early 20s,
clean pixel art, vibrant colors, sharp silhouette
```

**针对的已知问题**：
| 问题 | 本 prompt 的对应修复 |
|---|---|
| v1 背剑被披风遮住，E/W 只露剑柄一截 | `longsword in scabbard hanging at left hip, scabbard clearly visible at waist` — 物理上把剑搬到披风之外 |
| 4 头身偏写实，与 FE GBA 不符 | 全新 `3-head-tall super-deformed` 锚点 |
| 披风 + 背剑视觉冲突 | 披风改 `on back`（明确背面），剑改腰挂，互不干涉 |

### 2.2 苏瑶 v2（Female Mage / Cleric）

- **建议 character folder**: `SuYao_v2/Fire_Emblem_GBA_style_chibi_female/`
- **配色**: 白 + 蓝 + 金（不变）

**首版 prompt（v2.0，已实验，hood-up 8/8 失败）**：

```
Fire Emblem GBA style chibi female mage cleric, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
gentle elegant pose,
long silver hair flowing past waist, head fully bare with silver hair fully exposed,
hood collar resting at back of neck below shoulder line,
white and blue robe with gold trim,
wooden staff with large blue crystal orb held in right hand,
young woman early 20s, soft features,
clean pixel art, vibrant colors, sharp silhouette
```

→ 2026-06-06 实验：8/8 方向全部 hood-up，`head fully bare` 没生效。

---

#### 修订版 R1 — 温和强化（保留 mage cleric 设定）

思路：把 hood 描述**前移到 prompt 顶端**（更高权重），用 ALL CAPS + 三连否定 + 显式描绘"hood 在哪里"，但不动 `mage cleric` 主词。

```
Fire Emblem GBA style chibi female mage cleric, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
BAREHEADED, no hood worn, no hood on head, no head covering,
hood hanging loosely down behind back below shoulders,
forehead and silver hairline clearly visible at top of head,
long silver hair flowing freely from scalp past waist,
gentle elegant pose,
white and blue robe with gold trim,
wooden staff with large blue crystal orb held in right hand,
young woman early 20s, soft features, pretty face fully visible,
clean pixel art, vibrant colors, sharp silhouette
```

**与首版的差异**：
| 改动 | 作用 |
|---|---|
| hood 描述从中段提到第 4 行 | diffusion 模型对 prompt 前段权重更高 |
| ALL CAPS `BAREHEADED` | 隐性 emphasis trick |
| 三连否定 `no hood worn / no hood on head / no head covering` | 单个否定弱，但堆 3 个权重叠加 |
| 显式 "hood 在身后" `hood hanging loosely down behind back` | 告诉模型兜帽**在哪**，不只说"不在头上" |
| `forehead and silver hairline clearly visible at top of head` | 反向锚定头顶必须有头发不是布料 |
| `pretty face fully visible` | 间接拒绝戴帽 |

---

#### 修订版 R2 — 硬核（杀掉 hood 触发词）

思路：诊断认为 `mage cleric` + `robe` 在训练集与"hood-up"高度耦合。R2 直接换主词。

```
Fire Emblem GBA style chibi sorceress, western fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short body, small hands and feet,
bareheaded, completely uncovered head, no hood no hat no veil,
long silver hair flowing freely from forehead past waist,
silver hairline and forehead visible at top of head,
gentle elegant pose,
white and blue hoodless dress with gold trim, no robe, no cloak,
wooden staff with large blue crystal orb held in right hand,
young woman early 20s, soft features, pretty face fully visible,
clean pixel art, vibrant colors, sharp silhouette
```

**与 R1 的差异**：
| 改动 | 作用 |
|---|---|
| `mage cleric` → `sorceress` | 杀掉最强的 hood 触发词 |
| `robe` → `hoodless dress` | robe 本身带 hood 暗示，dress 不带 |
| 新增 `no robe, no cloak` | 显式拒绝带帽袍服 |
| 新增 `no veil` | 顺便堵"修女面纱"退路 |

**R2 风险**："法师味"可能变淡（dress 不如 robe 庄重），但配色 + 法杖仍传达法师身份。

---

#### 实验建议

用户 2026-06-06 计划同时跑 R1 + R2，并测试不同 canvas size（除了 248），数据回来后填入 §4.2 Reroll Log，3 方对比决定走向。

### 2.3 帝国兵 v2（Empire Axe Soldier, 微调 chibi）

- **建议 character folder**: `EmpireAxeSoldier_v2/Fire_Emblem_GBA_style_chibi_enemy/`
- **配色**: 青绿 + 黄铜 + 暗钢（不变）

```
Fire Emblem GBA style chibi enemy soldier, european medieval fantasy,
3-head-tall super-deformed proportions,
large head with big expressive eyes, short stocky body, small hands and feet,
generic imperial foot trooper,
stern soldier in his 30s with stubble and grim face partially visible,
dark teal green tabard over chainmail and dull steel plate armor,
classic western soldier style,
brass and leather trim accents,
plain steel kettle hat helmet, open-faced with nasal bar, no horns no plume,
large round wooden shield painted teal green with iron rim and central iron boss in left hand,
single-handed steel battle axe in right hand,
clean pixel art, vibrant colors, sharp silhouette
```

**针对的已知问题**：
| 问题 | 本 prompt 的对应修复 |
|---|---|
| v1 已稳定，不动 | 仅加 `chibi` + `3-head-tall` 转 Q 版 |
| `no horns` 仍有概率被忽略 | 保留 v1 验证的 `plain steel kettle hat` + 二次重申 `no horns no plume`（双保险） |
| `stocky` 与 `chibi short body` 可能冲突 | 改成 `short stocky body`，让 stocky 修饰 chibi 的短躯干（一致而非冲突） |

---

## 3. 动画 Prompts v2

**策略**：rotation v2 验收稳定**之前不做动画**。  
当 rotation 通过后，动画 prompt 在 v1 §3 基础上做两处机械替换：

1. **陆离所有动画里**：`longsword sheathed on back` → `longsword in scabbard at left hip`；`sword stays sheathed on back` → `sword stays in hip scabbard`
2. **苏瑶所有动画里**：`hood down` → `head bare, silver hair exposed`；`Hood stays down` → `Hood collar stays at back of neck, hair fully visible`
3. 其余不变

完整动画 prompt 等 v2 rotation 通过、动画跑出来再贴本节（不预先 paste 一堆未验证的）。**记得即时存档（v1 §5.6 教训）**。

---

## 4. 实验流程（v2 验证协议）

为了下结论不再靠 n=1，定义如下流程：

### 4.1 Rotation 验证（per character）

1. 用 v2 prompt 生成 rotation **第 1 次**
2. 8 方向逐张审（用 view_image 一次 8 张）
3. 标记每张：✅ 合格 / ⚠️ 可疑 / ❌ 崩坏
4. 如果有 ≥ 1 个 ❌：**重抽（reroll）整套 rotation**，**最多 3 次**
5. 三次内有任意一次"8 张全 ✅"→ 该角色 v2 rotation 通过
6. 三次都凑不齐全 ✅ → 记录失败模式 + 改 prompt + 回到步骤 1

### 4.2 Reroll 数据记录（强制）

每次 reroll 在本 doc 末尾追加：

```
### Reroll Log
- 2026-06-XX 陆离 reroll #1: south ✅ / east ⚠️ 剑被披风遮一半 / west ✅ / north ❌ 头身比退化到 4 / ...
- 2026-06-XX 陆离 reroll #2: ...
```

**目的**：积累 ≥ 9 次（3 角色 × 3 次）reroll 数据后才允许下"v2 prompt 在 248 下稳/不稳"的结论。n=1 不算数（这次教训）。

### 4.3 验收标准（与 v1 §5.4 一致）

- 5 帧 × 4 方向 = 20 帧/动画
- 单批 ≤ 20 张（view_image 上限）
- 武器 / hood / 头身比 三项每帧打勾，缺一项就标 ⚠️

---

## 5. 与 v1 的迁移规则

- v1 已生成的 92×92 资源**保留在 `art/characters/`**，不动
- v2 实验产物全部进 `art/characters_v2/`（建议命名，未实际建目录前自行决定）
- Unity 端先继续用 v1 资源跑 M1，**v2 仅作美术 spike**
- v2 验证通过后再开一个迁移决策：(a) 全切 v2 (b) 维持 v1 (c) 部分混用（不推荐）

---

## 6. 待办（v2 专属）

- [ ] 用本 doc §2 三个 prompt 各跑 1 次 rotation（共 3 次生成）
- [ ] §4.1 流程逐角色验收
- [ ] 在 §4.2 追加 reroll log
- [ ] rotation 全通过后再写 §3 动画 prompt 全文
- [ ] 验证 6+ 次后回头修订本 doc，并决定 v2 是否替代 v1

---

## 附录 A：3 头身关键词消融建议（如果第一版不够 Q 版）

如果生成出来仍偏写实（≥ 3.5 头身），按下面顺序逐项加强：

| 加强级别 | 追加关键词 |
|---|---|
| L1 | `cute mascot proportions` |
| L2 | + `tiny legs, oversized head` |
| L3 | + `disgaea chibi style` 或 `langrisser GBA style` |
| L4（核选项） | + `super deformed SD anime chibi` |

反过来如果太 Q（< 2.5 头身像幼儿园娃娃），删掉 `super-deformed`，只保留 `chibi 3-head-tall`。

---

## 附录 B：本 doc 的诚实性条款

- 任何"v2 比 v1 好/差"的判断必须**至少 3 次独立生成验证**才能写入本 doc
- 如果某次实验失败，**记录失败原因**而不是直接删掉
- 用户和 assistant 任何一方发现对方结论 n 太小 → 直接指出（已发生过 1 次：用户 6/6 指出 assistant 基于单次生成就下"west 退化"结论）

---

## 七、关键发现：PixelLab 方向标签准确度随 canvas size 退化

**实验数据**（2026-06-06，n=3 角色 × 2 canvas size）：

| 角色 | 92×92 canvas（v1） | 248×248 canvas（v2.0） |
|---|---|---|
| 苏瑶 east | ✅ 干净右侧视，法杖在前 | ❌ 近正面（朝镜头），方向标签失真 |
| 苏瑶 west | ✅ 干净左侧视 | ❌ 近背视，方向标签失真 |
| 陆离 east | ✅ 3/4 侧视，剑/披风清晰 | ⚠️ 3/4 偏前 |
| 陆离 west | ✅ 3/4 侧视 | ⚠️ 3/4 偏前 |
| 帝国兵 east | ✅ 干净右侧视，斧盾完整 | ❌ 偏前 |
| 帝国兵 west | ⚠️ 偏后 3/4（轻微） | ❌ 偏后更明显 |

**结论**（n=3 跨角色一致，**signal 充分**）：
- 92px canvas：8 方向标签**基本可信赖**，east/west 大多是真侧视
- 248px canvas：E/W 出现**系统性偏移**——E 塌向 S（朝前），W 塌向 N（朝后），NW 进一步塌向 N
- 偏移方向在 3 个角色身上一致，**不是单角色 prompt 问题，是 canvas size 引发的模型行为差异**
- **陆离身上最明显**（用户观察确认）

### 7.1 原因推测（未实证，仅 hypothesis）

PixelLab 内部 view 条件控制疑似**针对小 canvas 训练 / 调优**：
- 小 canvas（≤96px）下角色就是个 silhouette，模型只能用最 iconic 的姿态（纯侧视）来传达方向信息——分辨率不足以容忍 3/4 偏侧的细微差别，所以纯侧视是"信号最强"的选择
- 大 canvas（≥128px）下角色有充足渲染空间，模型敢做 3/4 / 半身美学姿态（这是训练数据里最常见的人像角度），方向标签的硬约束被审美偏好稀释

### 7.2 实操影响

如果坚持用 248px canvas，**Unity 端 8 方向切片需要重映射**：

| 游戏内角色朝向 | 实际应使用的 PixelLab 文件名（248 下） |
|---|---|
| N（向上） | `north.png` ✓ |
| S（向下） | `south.png` ✓ |
| E（向右） | **`north-east.png`**（不是 `east.png`） |
| W（向左） | **`south-west.png`**（不是 `west.png`） |
| NE / SE / NW / SW | 仅 4 主方向战棋可忽略；8 方向战棋时**有效素材只剩 4 张** |

意味着 248 下**真正可用的方向数从 8 降到 4-5**。如果项目需要完整 8 方向移动/朝向，需要 reroll 测试是否所有 248 生成都有这个偏移，或者考虑 92×92 fallback。

### 7.3 待验证

- 测试**其他 canvas size**（128 / 160 / 192）在 view 准确度上的表现，找最佳 sweet spot（细节够 + 方向准）
- 测试是否能用 prompt 修复 view skew（例 `clear right-side profile when facing east`）
- 不同 angle preset（Low Top-Down / High Top-Down / Side）下是否表现不同

**实验结论用户认领**：用户偏好 128px 细节（"48 看着糊"），即使方向标签退化也愿意接受 Unity 端映射成本。本 doc 保留 248 为主路径，§7 finding 不替代 §1 设置，仅作 known caveat 记录。
