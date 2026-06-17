# 《幻世纪》Unity SRPG — 设计规格书 v2（Demo → Steam）

> **日期**：2026-06-15
> **作者**：hualiang
> **状态**：现行版（active），取代 `2026-05-24-fantacy-centry-unity-design.md`
> **取代说明**：v1 的项目定位 / 架构 / 战斗系统 / 范围冻结仍然有效并在此继承；但 v1 §5「美术管线」整章作废（单张 AI 大图、48px tile、PixelLab-only 路线已被实践否定）。本 v2 用经过 20 天实验验证的「tile + 分层 + 多模型分工」管线替换，并新增「Demo → Steam」的里程碑与工时估算。
> **配套**：`docs/游戏大纲.md`（世界观/角色，仅参考）、`docs/developing_process/*.md`（每日实验日志，是本 spec 经验的一手出处）。

---

## 0. 这版改了什么（相对 v1 的 delta）

| 主题 | v1（2026-05-24） | v2（本版，已验证） |
|---|---|---|
| 战场地图 | 单张 AI 大图 / 48px Cainos tile | **64px tile + 分层（地面 tile / 物件 sprite / 逻辑 JSON 三层）** |
| 地图出图 | Flux + ControlNet 画整张战场 | **GPT-Image / Gemini 出单块 tile 与物件**，Flux/LoRA 做变种；**否定了"AI 画整张可玩战场"** |
| tile 边界 | 未涉及 | **Unity Rule Tile（autotile）+ Python 脚本自动无缝 / 自动合成边角** |
| 战斗演出 | 大地图原地（已定） | **维持原地结算，但明确做成 Domain 事件订阅者**，未来加"切战斗场景"是横向叠加、不改 Domain |
| 角色尺寸 | 48px sprite / PPU48 | **沿用，但补充方向约定**（S 静止 / 侧背走 / E=W 镜像偏 S） |
| 坐骑 | 未涉及 | **新增坐骑/神兽生成规律**（单一真实生物稳，合成神兽崩） |
| Demo 目标 | "序章 3 关跑通" | **村庄一关、3v5（我方 3 / 敌方 4 兵 + 1 骑），含近战/远程投掷/小型法术，目标上架 Steam** |
| 开发哲学 | 阶段依赖顺序 | **横向扩容优先：先做"灰盒可玩"打通所有系统，再统一换皮** |
| 工时 | "不估时间" | **给出客观工时区间与里程碑**（见 §10） |

---

## 1. 项目定位

### 1.1 一句话

用 Unity 做一款 **64px tile / 像素风战棋 SRPG**，参考火焰纹章的战斗循环、梦幻模拟战的兵种相克、FFT 的战术深度，配现代精致立绘；**第一个对外里程碑是一个能放上 Steam 商店页的可玩 Demo**。

### 1.2 Demo 范围（M1，冻结）

| 维度 | Demo 内容 |
|---|---|
| 场景 | **村庄战场一关**（已有 AI 概念图与逻辑网格雏形） |
| 我方 | **3 个角色**（陆离 剑士 / 苏瑶 法师 / 小 弓兵） |
| 敌方 | **5 个单位 = 4 步兵（3 斧 + 1 弓） + 1 骑兵** |
| 战斗类型 | **该有的都有**：近战肉搏、远程投掷物（弓/标枪）、小型法术（火球/单体或小范围） |
| 系统 | 回合制、移动范围、攻击范围、命中/暴击/反击、兵种相克、敌方 AI、胜负判定 |
| 表现 | 大地图原地演出、移动/攻击高亮、伤害飘字、血条、回合横幅、镜头跟随 |
| 周边 | 简单法术特效、音效、AI 音乐、至少 2 张立绘（已有部分）、像素 UI |
| 出口 | 能打、能赢能输、能在 Steam 商店页放截图/试玩而不露怯 |

### 1.3 核心哲学：横向扩容，而非纵向

> **Demo 不是"缩小的游戏"，是"完整系统的第一个实例"。**

- 系统基础（回合、单位、技能、伤害、AI、关卡、存档）一次性按"通用"设计，Demo 只是填了 3v5 的数据。
- 加角色 = 加 ScriptableObject 数据；加技能 = 加 SkillDef + 一个特效订阅者；加关卡 = 加 LevelDef + 一张逻辑网格。**都不改核心代码。**
- "切战斗场景""转职""第二关"全部是后期横向模块，Demo 阶段只留接口、不实现。

### 1.4 不在 Demo 范围内（防蔓延）

- ❌ 切战斗场景大动画（保留为未来订阅者，见 §6.3）
- ❌ 转职 / 多周目 / 好感度 / 永久死亡
- ❌ 联机、移动端、配音
- ❌ 大世界地图（Demo 只有一关，主菜单 → 战斗 → 结算即可）
- ❌ 完美数值平衡（"能玩通、有取舍"即可，发布前一次 pass）

### 1.5 成功标准（M1 出口，全部满足）

1. Windows 双击 exe 启动，能完整打完这场 3v5，分出胜负。
2. 没玩过的人不靠口头指导能上手。
3. 3 人盲测，**无人**说"美术像占位符"。
4. 回合节奏不明显差于 GBA 火纹。
5. 近战 / 远程投掷 / 法术三种攻击都可用且观感正确。
6. 我自己回头玩，不觉得"这套系统/手感必须推翻重做"。

---

## 2. 技术栈

| 类别 | 选择 | 说明 / 与 v1 差异 |
|---|---|---|
| 引擎 | Unity 6000.x（当前 6000.4.9f1） | 不变 |
| 渲染 | URP 2D Renderer + Pixel Perfect Camera | 不变。PPU 见 §7.1 |
| 语言 | C#，Domain 层纯 C#（禁 UnityEngine 依赖） | 不变，可单测 |
| 地图 | **Unity Tilemap + Grid** | v2 回归 tile 路线 |
| autotile | **2D Tilemap Extras 包的 Rule Tile** | v2 新增，解决边界 tile |
| 寻路/范围 | **自写 BFS/Dijkstra（格子）** | Unity 无内置格子寻路；NavMesh 是 3D 连续地形，不用 |
| 动画 | 自写帧播放器 `CharacterSpriteAnimator`（已有） | v1 已偏离 Unity Animator，刻意为之，可逆 |
| UI | **UI Toolkit**（菜单/HUD），世界空间飘字用 UGUI 或 sprite | 不变 |
| 数据 | ScriptableObject | 不变 |
| 存档 | JSON + 本地文件（Demo 可不做或极简） | Demo 一关，存档非必须 |
| 音频 | AudioSource + AudioMixer | 不变 |
| 版本控制 | Git + LFS；第三方受限素材 gitignore | 不变 |
| 出图（外部） | **GPT-Image / Gemini（主力，语义强）+ Flux/LoRA（变种）+ PixelLab（角色/坐骑 sprite）** | v2 核心变化，见 §7 |
| 出图工具仓库 | ComfyUI 在独立 repo `c:\Repo\FamilyArtGeneration`（**agent 不编辑**） | 既有铁律 |
| 像素编辑 | **Aseprite（可选，Demo 非前置）**；机械处理用 Python 脚本替代手绘 | 见 §7.6 |

---

## 3. 架构

### 3.1 分层

```
            ┌─────────────────────────────┐
            │  Game (启动/场景/全局状态)    │
            └─────────────────────────────┘
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
  ┌──────────┐     ┌──────────────┐    ┌──────────┐
  │  Domain  │     │     View      │    │   Data   │
  │ 纯 C#规则 │◄───►│ MonoBehaviour │◄──►│   SO     │
  │ 可单测    │事件 │  订阅 Domain   │    │ 角色/技能 │
  └──────────┘     └──────────────┘    └──────────┘
        │                 │
        ▼                 ▼
  ┌──────────┐     ┌──────────────┐
  │   AI     │     │ Input/Camera  │
  └──────────┘     └──────────────┘
```

### 3.2 铁律（继承 v1，不可违背）

1. **Domain 与 View 解耦**：`BattleState/Unit/DamageCalc/Pathfinding` 是纯 C#，不 `using UnityEngine`。Domain 抛事件（`UnitMoved/UnitDamaged/UnitDied/TurnChanged`），View 订阅播动画。
2. **数据驱动**：角色/职业/技能/敌人/关卡全是 ScriptableObject。
3. **回合状态机**：显式 `TurnPhase`，禁止隐式状态。
4. **命令模式**：玩家"移动→行动→目标→确认"序列化为 `BattleCommand`，供撤销 / AI 复用 / 未来回放。

### 3.3 目录结构（在现有基础上补 Domain）

```
Assets/Scripts/
├── Editor/        # 已有：导入后处理、Rig 生成、地图场景生成器
├── View/          # 已有：MapGrid/GridMover/CharacterSpriteAnimator/CameraFollow/YSort/...
├── Domain/        # ★新建：纯 C# 战斗核心
│   ├── Grid/          # GridPos, BattleMap, Terrain
│   ├── Units/         # Unit, Stats, Team, TurnState
│   ├── Turn/          # TurnSystem, TurnPhase
│   ├── Pathfinding/   # 移动范围 BFS、攻击范围、路径
│   ├── Combat/        # DamageCalc, HitCalc, Counter, Affinity(相克)
│   ├── Skills/        # SkillDef 执行、射程/AOE
│   ├── AI/            # 敌方决策
│   └── Events/        # Domain 事件定义
├── Battle/        # ★新建：View 与 Input 把 Domain 接到 Unity
│   ├── BattleView/    # 单位视图、范围高亮、飘字、血条
│   ├── Input/         # 光标、选格、命令构造
│   └── Effects/       # 投掷物、法术 VFX（独立 GameObject）
└── Data/          # ★新建：ScriptableObject 定义
    ├── Characters/ Jobs/ Skills/ Items/ Levels/
```

---

## 4. 战斗 Domain 设计

### 4.1 数据模型（纯 C#）

```csharp
public class Unit {
    public string Id;
    public CharacterDef Def;     // SO 引用
    public JobDef Job;
    public int Level;
    public int Hp, MaxHp, Mp, MaxMp;
    public Stats Stats;          // 力/魔/防/魔抗/速/移动/射程
    public WeaponType Weapon;    // 剑/斧/枪/弓/法 → 相克用
    public List<SkillDef> Skills;
    public GridPos Position;
    public Facing Facing;        // 复用 View/Facing.cs 的约定
    public Team Team;            // Player/Enemy/Ally
    public TurnState State;      // Idle/Moved/Acted/Done
}

public class BattleState {
    public BattleMap Map;        // 来自逻辑 JSON：尺寸 + 每格地形 + walkable + move_cost
    public List<Unit> Units;
    public int TurnNumber;
    public Team CurrentTeam;
    public TurnPhase Phase;
    public WinCondition Win;
    public LoseCondition Lose;
}
```

`BattleMap` 直接复用现有 `demo_map.json` 的网格语义（`G/R/D` 可走，`W/C/B/L/F` 阻挡；见地图章节）。Domain 只关心 walkable + move_cost + 地形修正，不关心像素。

### 4.2 回合流程

```
关卡开始 → [玩家回合]
  对每个我方单位（玩家自选顺序）：
    选中 → 显示移动范围(蓝, BFS 受 move_cost 限制)
    选移动格 → 显示攻击范围(红, 按武器 min/maxRange)
    选行动: 普攻 / 战技 / 法术 / 道具 / 待机
    选目标 → 命中/暴击/伤害预览
    确认 → 执行 → State=Done（Acted 前可撤销移动）
  全部 Done 或点"结束回合"
→ [敌方回合] AI 按速度顺序行动
→ [回合结算] 状态效果 tick、增益持续 -1
→ 判定胜负 → 否则 TurnNumber++ → [玩家回合]
```

### 4.3 移动范围与寻路

- **移动范围 = Dijkstra**（带地形 move_cost）从单位当前格扩散到 `Stats.Move` 预算内的所有可走格。
- **攻击范围 = 移动可达格的并集 ⊕ 武器 min/maxRange 环**。
- **路径 = A\***（移动到目标格时走最短代价路径，View 沿路点平滑移动）。
- 全部自写，格子 SRPG 规模下性能无忧（35×35 上限千格级）。

### 4.4 伤害 / 命中 / 暴击 / 反击（草案，数值后调）

```
物理伤害 = max(1, 力 × 武器系数 + 技能加成 - 守方防御)
魔法伤害 = max(1, 魔 × 法术系数 + 技能加成 - 守方魔抗)
命中率   = clamp(速×2 + 武器命中 - 守速×2 - 地形闪避, 10, 100)
暴击率   = clamp(武器暴击 + 角色暴击 - 守方抗暴, 0, 50)   暴击 ×1.5
反击     = 守方存活 且 反击距离覆盖 且 非"无法反击" → 反击 1 次
```

地形修正：防御格 受伤 ×0.8 / 命中 -10%；森林 闪避 +15%（注：Demo 森林不可走，作为阻挡掩体环绕战场）。

### 4.5 兵种相克（占位优先，梦战体系）

> **原则：相克本质就是个查表系数，现在不纠结数值。** `DamageCalc` 里留 `AffinityTable`（`AttackerClass/Weapon × DefenderClass → 系数`），**默认全 1.0**，乘进伤害公式。现在填不填值都不影响系统跑通。

梦战式相克环（写进**数据**，不写死代码）：

| 关系 | 说明 |
|---|---|
| **剑 > 枪 > 骑 （循环，骑 > 剑）** | 三角循环主克制 |
| **圣 > 暗** | 属性克制 |
| **弓 > 飞，且弓弱近战** | 弓克飞行/骑兵，但被贴脸吃亏 |
| **暗 对其他全体小克制** | 暗系普适小加成 |

倍率：克制方 输出 ×1.25 / 受击 ×0.75（可调）。

**武器差异占位**：`WeaponType` 枚举保留 `Axe`，但 Demo 阶段 **斧暂归剑系**（同一相克格）；后续用 `WeaponDef` 字段区分：斧 = 高伤/低命中，剑 = 高暴击。不急。

Demo 相克 showcase：我方**小（弓）克敌方骑兵** + 苏瑶（法）克重甲 + 陆离（剑）克敌斧（Demo 期斧归剑系，此点暂不生效，留接口）。

### 4.6 远程与法术（数据 + 独立特效）

射程/AOE 是 `SkillDef` 字段，与动画无关：

```csharp
public class SkillDef : ScriptableObject {
    public int minRange;     // 法术=2(不能贴脸), 弓=2
    public int maxRange;     // 法术=3, 弓=5
    public int areaOfEffect; // 单体=0, 3x3=1
    public DamageType type;  // Physical/Magical
    public int power;        // 系数/基值
    public ProjectileDef projectile; // 可空：近战无弹道
}
```

三类远程表现（独立 GameObject，攻击动画出手帧触发）：

| 类型 | 例 | 实现 |
|---|---|---|
| 实体弹道 | 弓箭 / 标枪 | 小 sprite 沿直线 Lerp 0.3–0.5s 命中 |
| 飞行法术 | 火球 | 本体循环帧飞行 + 命中爆炸一次性帧 |
| 直射冲击 | 光束/剑气 | sprite 从施法者拉伸到目标，0.2s 缩放淡出 |

### 4.7 AI（Demo 三档）

1. **冲锋型**（步兵/野兽）：朝最近我方寻路，够得着就打。
2. **驻守型**（守军）：进入感知范围（如 3 格）才出击。
3. **目标型**（护送/坚守用）：朝指定坐标移动。
Demo 的 5 敌：3 冲锋步兵 + 1 驻守步兵（守桥/守屋）+ 1 骑兵（高机动冲锋，演示弓克骑）。
后期横向加：聚焦残血、规避反击、保护友军等。

### 4.8 关卡数据

```csharp
[CreateAssetMenu]
public class LevelDef : ScriptableObject {
    public string LevelId;
    public TextAsset MapJson;          // 逻辑网格（= demo_map.json 这类，可为 35×35）
    public RectInt BattleBounds;       // 战斗子区域框（min/max 格）；spawn/移动/AI/镜头都 clamp 在此。空=全图
    public Sprite Background;          // 该关地面合成图（或纯 Tilemap）
    public List<UnitSpawn> PlayerSpawns;
    public List<UnitSpawn> EnemySpawns;
    public WinConditionDef Win;        // 歼灭/击杀首领/到达点/坚守N回合
    public LoseConditionDef Lose;      // 主角阵亡/限回合未达成
    public DialogueDef Pre, Post;
}
```

---

## 5. 角色与方向约定

### 5.1 尺寸（沿用已验证）

- 角色 sprite 48px，**PPU=48**，1 tile = 1 unit；角色视觉占 ~1.8 格（FFT/Tactics Ogre 观感）。
- 来源 PixelLab v3，逐帧独立 PNG，`frame_000` 是旋转参考帧 **跳过**，用 `001–008`。
- 导入：Point 滤镜 / Compression None / Wrap Clamp（已由 `PixelArtImportPostprocessor.cs` 自动处理）。

### 5.2 方向约定（v2 新定，火纹/梦战范式）

- **只做 S / N / E 三套，W = E 镜像翻转（flipX）。**
- **静止（idle）一律用 S（正面偏下）**——符合 FE / 梦战静止朝屏幕的惯例。
- **移动 / 攻击用侧面（E）和背面（N）**；W 镜像 E。
- **E/W 的侧面姿态可以稍微偏 S（3/4 侧）**，让人物更饱满（KOF 式 3/4 视角），并**规避 PixelLab 最易崩的纯正侧视角**。
- **已知偏差**：PixelLab 标注的 8 方向旋转文件名整体偏约 1 步（它标的 "S" 视觉常是 SE，"SW" 才接近正 S）；判断时看身体朝向不看脸。详见 `developing_process/2026-06-07` 映射表。我们的"不做纯侧、用偏 S 的 3/4 侧"正好绕开这个雷区。
- **镜像副作用**：E→W 翻面会让非对称细节（披风搭肩、持武器手、盾的左右）反向；chibi 小图肉眼难辨，Demo 接受，记录在案。

### 5.3 坐骑 / 神兽生成规律（v2 新增，2026-06-15 验证）

- **坐骑优先选"单一真实生物"**（马 / 飞马 / 鹰 / 狮 / 龙）：模型训练数据多，8 方向成功率高。
- **人形 + 骑乘 稳；纯四足兽 易崩**（腿部相位/透视见得少）。
- **合成神兽（狮鹫 / 奇美拉）几乎必崩**：小图抓不住"鹰头+狮身+翅膀"，会退化成它最熟的"带鬃毛的狮子"，且常丢翅膀。
- 对策：① 神兽多抽几次挑；② **拆层做**（狮身 sprite + 单独贴鹰头/翅膀图层）；③ 接受主角实际是"飞马/鹰骑士"，把狮鹫降级为后期精修目标。
- Demo 主力坐骑建议用质量最高的**飞马骑士**（粉发女骑士那张），狮鹫不入 Demo 关键路径。

---

## 6. 战斗演出策略

### 6.1 Demo：大地图原地结算（定）

攻击在大地图原地播放：出手动画 + 投掷物飞行 + 法术特效 + 受击闪白/退缩 + 伤害飘字 + 血条动画。**不切独立战斗场景。**

理由：切战斗场景 = 第二套表现系统（演出舞台、双方站位、运镜、每地形一张战斗背景、命中/闪避/暴击编排），轻松多吃 40–80h，且"原地结算"本身就是完整 SRPG（高级战争 / Into the Breach / 三角战略一部分）。

### 6.2 关键架构：结算是 Domain 事件，演出是订阅者

- Domain 只产出事件（`AttackResolved{attacker,target,damage,isCrit,isMiss,...}`）。
- 当前挂"大地图原地演出"订阅者。
- **未来加"切战斗场景"= 再加一个订阅者，Domain 一行不改**。这就是 §1.3 横向扩容的体现。

### 6.3 未来切战斗场景（不入 Demo，仅记接口 + 成本）

- **不需要新比例 sprite**：128px chibi 放大直接用（FE GBA 同款 chibi 放大演出）。
- **方向奇省（关键洞察）**：战斗演出永远是"我方在左打右、敌方在右打左"的**固定横向对峙**，所以战斗动作**只需一套朝右的 3/4 侧身 SE（偏 20–30°，KOF 角），敌方用镜像**。不需为战斗画面铺四向。
- **背景用 Flux 静态出图**：战斗背景是**静态、单张、不可走、无需逻辑网格** → 恰是 Flux 的强项，避开了我们否定它的理由（整张可玩战场不可编辑）。一地形一张，5–10 张搮定。
- **成本重估（较 v1 的 40–80h 下调）**：单朝向 + Flux 背景确实省掉了"方向铺设"与"背景制作"，但**真正的主成本是舞台系统 + 演出编排 + 更精细的战斗专用帧**，这些省不掉。净增约 **+25 ~ +50h**（舞台/转场 8–15h + 演出编排 10–20h + 战斗专用帧 10–25h + Flux 背景 4–8h − 省下的大地图精细攻击演出 8–15h）。是**净增，不是更小**，但边界清晰、可估算。
- **结论**：Demo 不切；未来切的路径已清晰（单朝向 SE + Flux 静态背景），且因为是 Domain 事件订阅者，现在选"不切"零成本、将来改主意不返工。

---

## 7. 美术管线 v2（核心重写）

> **指导原则**：玩家只审美、不手绘、不会 PS/Aseprite。**一切"机械操作"（切片 / 无缝 / 边角合成 / 导入设置）由 Python/Editor 脚本替代手工**；玩家只做"出图 + 挑选 + 把关"。

### 7.1 三层地图框架（取代单张大图）

| 层 | 内容 | 来源 | 编辑方式 |
|---|---|---|---|
| **逻辑层** | 每格地形字母（walkable/move_cost） | `demo_map.json`（已有） | 区域填充，可自动 |
| **地面层** | 草 / 土 / 路 / 水 / 桥 tile，64px | GPT/Gemini 出 base，Flux/LoRA 变种 | Unity Tilemap + Rule Tile 刷 |
| **物件层** | 房 / 树 / 石 / 井 / 栅栏 / 田，占 N×N 格的 sprite | GPT/Gemini 单张出图 | 当 sprite 摆放，YSort 遮挡 |

- **tile = 64px，PPU=64**；地面 1 cell = 1 unit，与角色 PPU=48 并存（角色比格子大，FFT 观感）。这条已在 06-14 记录验证。
- **物件不烤进地面**（可复用、可遮挡、跨关重用，类似角色）。AI 只负责"非交互的连续地面"。

### 7.2 为什么放弃"AI 画整张战场"

20 天实验结论（写死，避免重走）：

- Flux + ControlNet 画整张：strength 高 = 色块，低 = 布局跑乱；"最好的一张"仍与原始 JSON 布局差很多。
- 根因：**SRPG 本质是格子逻辑，整张大图不可编辑、不可复用、不 scalable**；玩家无法 visualize 去改 JSON，对齐成本极高（06-14 花一整天逐格校对就是症状）。
- GPT-Image / Gemini 语义遵从 **远强于 Flux**，画得也更美，但**底层仍是"每格干什么"**，直接当战场用还是要逐格编 JSON——同样不 scalable。
- **结论：大图只配当"概念参考"，可玩战场必须是 tile 拼。**

### 7.3 多模型分工

| 资产 | 主力 | 备注 |
|---|---|---|
| 角色 / 坐骑 sprite | **PixelLab** | 8 方向、风格统一；规律见 §5.3 |
| 地面 base tile（草/土/路/水/桥） | **GPT-Image / Gemini** | 语义强、纹理好看 |
| tile 变种（避免重复感） | **Flux / LoRA** | 小量变种，宽容型 tile 用 |
| 物件（房/树/石/田…） | **GPT-Image / Gemini** | 单张出图，同光照同调色板 |
| UI kit | **GPT-Image / Gemini** | 整套一次出图，见 §7.5 |
| 战斗 VFX（火球/闪电/剑气） | **现成 pixel VFX 素材库**（itch.io / kenney） | 抽象光效，混用不冲突；序列帧用现有帧播放器 |
| 立绘 | **GPT-Image / Gemini / MJ** | 已有部分在 `undecided_art` |
| 音乐 | **AI 生成** | Demo 够用 |
| 音效 | **现成 SFX 库** | freesound / kenney / 限免包 |

### 7.4 tile 的真正难点：无缝 + 边界（脚本兜底）

把 tile 分两类对待，这是 scalable 的关键：

- **宽容型 tile**（草 / 土 / 水体内部）：每格放一个变种 + 轻微旋转，**不需要完美边缘匹配**，变种反而减重复感。可随机填充。
  - **无缝化**：写 Python（offset + 边缘镜像/羽化融合）把 AI 纹理自动转无缝。玩家只挑好看的，**0 手绘**。
- **边界型 tile**（水岸 / 路沿 / 悬崖面 / 桥头）：**必须做方向过渡集**，不能随机填。
  - 用 **Unity Rule Tile（autotile）**：准备一套 47-blob 或简化 16-tile 边角，告诉规则"上草下水 → 上边缘 tile"，之后**只刷草和水，Unity 自动选边界**。
  - **边角 tile 自动合成**：写 Python 从"草纹理 + 水纹理"两张图用 mask 混合 + 描边自动生成边角过渡集。质量不如手绘大师，但 **Demo 级够用、100% 自动、可复用**。

> 风险登记：边界 tile 是整条管线唯一"纯生成最难"的环节；自动合成的精度上限有限，若 Demo 后要精修，再考虑学 Aseprite 补笔（见 §7.6）。

### 7.5 UI 出图规范

- **一次出整套 UI kit**（面板 + 按钮 + 血条 + 图标框 + 边框装饰）保证风格统一；**不要逐个按钮单独生成**（必然圆角/描边/高光对不上）。
- 流程：GPT/Gemini 出概念整图 → 玩家挑 → 脚本切片 → Unity 里做 **9-slice** 复用 → UI Toolkit 接线。
- 菜单/按钮必须像素风边框，杜绝 Unity 默认灰白控件。

### 7.6 玩家"只审美"可行性 & Aseprite

| 资产 | 纯生成 + 把关可行？ |
|---|---|
| 角色/立绘/物件/UI/VFX | ✅ 基本可行，脚本负责切片/导入，几乎不碰 Aseprite |
| 宽容型地面 tile | 🟡 可行，但需"无缝化"——**脚本做，0 手绘** |
| 边界过渡 tile | 🔴 最难——**脚本自动合成兜底**，Demo 够用 |

- **Demo 阶段：Aseprite 可不买不学**，机械处理全交脚本。
- **长期建议**：花约 **2–4 小时** 学 Aseprite 三件最基础的事（① 画笔补几个像素、② offset 看无缝、③ 调色板替换）。**不是学画画**，是"微调修补"，性价比最高，但**非 Demo 前置**。

### 7.7 既有受限素材规则（继承）

- Cainos「Pixel Art Top Down Basic」(免费但禁再分发) 与 `art/maps/demo_map.png` 等：相关目录已 gitignore，不提交。
- `c:\Repo\FamilyArtGeneration`（ComfyUI）是独立仓库，**agent 只管 `c:\Repo\FamilyGame`，不编辑那边**。

---

## 8. 地图生成管线现状（继承自 06-13/14，调整定位）

- JSON 单一真值源：`scripts/map/build_demo_map.py` 画布局 → `demo_map.json`；`render_map.py` 出控制图（seg/depth/canny/walkable/preview）。
- **新定位**：这套管线产出的"整张 AI 大图"降级为**概念参考**；可玩地面改走 §7.1 的 tile 拼接。逻辑 JSON 继续作为 Domain 的 `BattleMap` 真值源。
- 既有铁律保留：
  - `base` 每行必须严格等于 `grid_size`（35）字符，否则 `MapGrid.cs` 静默丢行；改完跑 `bad rows` 校验必须 `[]`。
  - 大图人工校对 = 分块放大 + 坐标叠加 + tracking JSON；不看整张缩略图、不信纯自动分类器。
  - 改格子前必 `read_file` 读真实原文；跨文件一致性改动列清单逐处同步。
- **35×35 偏大**（玩家已指出）：但**真正约束是可走走廊，不是网格维度**。中间一条河効开、外圈森林/悬崖全阻挡，实际站人区远小于 1225 格（尤其无飞兵）。
- **决定：网格保留 35×35不变（零美术返工），改用 `LevelDef.battleBounds` 框定战斗子区域。**
  - 整张 35×35 逻辑网格继续作为 `BattleMap` 真值源，一格不改（保住 06-14 逐格对齐成果）。
  - `LevelDef` 加 `battleBounds`（一个矩形 min/max 格），把 3v5 框定在中央村庄/桥那块可走走廊（约 **~16×16** 子矩阵）。双方出生点、移动范围、AI、镜头都 clamp 在此框；外圈天然当不可逾越的边界墙。
  - 参照系：GBA 火纹典型关 ~15×10–20×15；3v5 八单位有效区域 ~12×12–16×16 足够，再大是空旷感。
  - 未来做"飞兵跨河"大关时，35×35 全图随时可用——横向扩容。

---

## 9. 项目结构（现状 + 新增）

```
FamilyGame/                       # 既有工作区根（代码就在这里，不另开仓库）
├── Assets/
│   ├── Scripts/{Editor,View, ★Domain, ★Battle, ★Data}/
│   ├── Art/{Characters,Maps,Tilesets,★Objects,★UI,★VFX,Portraits}/
│   ├── Audio/{BGM,SFX}/
│   ├── Data/{Characters,Jobs,Skills,Items,Levels}/   # SO 实例
│   ├── Scenes/{SampleBattle, ★VillageDemo, MainMenu}/
│   └── Settings/
├── art/                          # 源美术（部分 gitignore）
├── scripts/map/                  # 出图/逻辑网格管线（Python，venv: .venv）
├── docs/{specs,developing_process,...}/
└── Packages/ ProjectSettings/
```

---

## 10. 里程碑与工时估算（客观）

> 下列是**总工作量**（含审查 + Unity 接线 + 测试 + 美术迭代），非纯敲键盘时间。代码我生成快，玩家时间主要花在审查 / 接线 / 美术筛选 / 调平衡 / 踩 Unity 坑。

### 10.1 模块工时

| 模块 | 内容 | 工时 |
|---|---|---|
| A. 战斗 Domain（纯 C#） | 网格/单位、回合状态机、移动范围、近战/远程/法术、伤害+命中+暴击+相克、AI、胜负 | 15–25h |
| B. 大地图表现/输入 | 选格光标、移动蓝格/攻击红格高亮、沿路径移动、攻击动画、投掷物、法术特效、飘字、血条、死亡、回合横幅、运镜 | 20–30h |
| C. UI（菜单系统） | 行动菜单、单位信息面板、回合提示、胜负界面、UI Toolkit 搭建+接线 | 12–20h |
| D. 美术生成+集成（瓶颈，方差大） | 地面 tile+无缝+autotile 边界、物件、3 我方+敌兵种 sprite、投掷/法术 VFX、立绘、UI kit | 30–50h |
| E. 音频 | SFX 筛选+接线、AI 音乐+接线 | 6–10h |
| F. 关卡搭建 | 村庄战场逻辑网格+刷 tile+摆物件、布阵、AI 参数、胜负、试玩+调平衡 | 12–20h |
| G. 集成/调 bug/收尾（永远被低估） | "最后 20%" | 15–25h |
| **合计** | | **110–180h** |

按"只有周末、有效产出 ~8h/周末"：

$$\frac{110\text{–}180\,h}{\sim 8\,h/\text{周末}} \approx 14\text{–}22\ \text{周末} \approx 3.5\text{–}5.5\ \text{个月}$$

### 10.2 推荐里程碑（关键：先灰盒，后换皮）

**里程碑 1 — 灰盒可玩**（Domain + 大地图表现 + 最简 UI + 占位色块/现有 LingShuang，完整 3v5 能打能赢能输）：
- **约 50–70h ≈ 6–9 周末 ≈ 2 个月**
- 价值：一次性拆掉所有系统风险，随时有"是个游戏"的东西；美术并行慢慢出、永不阻塞主线。

**里程碑 2 — 像样 Demo（换皮到 Steam 可展示）**（tile/物件/sprite/VFX/立绘/UI/音乐音效全上 + 调平衡 + 收尾）：
- **再约 60–110h**

### 10.3 风险（诚实）

- 方差最大：**D（美术迭代）+ autotile 边界**；"出多少张才挑到满意"取决于审美卡多严，无法精确预估。
- **G 收尾几乎必超**：把 110 当乐观下限、180 当现实、200+ 当美术反复返工的上限。
- 单人动力衰减：靠"每里程碑都有可玩产物"维持正反馈；灰盒一旦能打，士气会显著回升。

### 10.4 现金成本（到 Steam 上架）

> 原则：**固定月费压到最低，其余都是"用到才花"的点状支出**。多数订阅可以"做这块时开、做完暂停"。

| 项目 | 费用 | 类型 | 必需性 | 说明 |
|---|---|---|---|---|
| **PixelLab.ai** | **$12/月** | 订阅（可暂停） | **必需** | 角色 + 坐骑 sprite 主力，8 方向无替代。只在出 sprite 的月份订，出完暂停 |
| **图像生成（地面 tile / 物件 / UI / 立绘）** | **$0 起** | — | **必需（但可免费）** | **首选 Gemini 2.5 Flash Image（"Nano Banana"），Google AI Studio 有免费额度**，语义/一致性强 → 优先全用它 |
| ↳ 备选 GPT-Image | $20/月 (ChatGPT Plus) 或 API 按量 | 订阅/按量 | 可选 | 仅当 Gemini 不够用时临时开一个月，或走 OpenAI image API 按量 |
| ↳ 备选 Gemini API | 按量（很便宜） | 按量 | 可选 | 免费档不够频次时升按量，比 Plus 灵活 |
| **Flux + LoRA（tile 变种）** | **$0** | 本地 | 已具备 | 本地 5070Ti + ComfyUI（独立仓库 `FamilyArtGeneration`），无额外花费 |
| **AI 音乐（BGM）** | **~$10/月** | 订阅（可暂停） | 必需（点状） | Suno / Udio，只在做 BGM 的 1 个月订，做完暂停 |
| **音效 SFX** | **$0** | 素材库 | 必需 | freesound / kenney.nl / Asset Store 限免 |
| **战斗 VFX 素材包**（火球/闪电/剑气） | **$0–30** | 一次性 | 必需 | kenney 多为免费；itch.io 精品包 $5–15/套 |
| **Aseprite** | **$19.99** | 一次性买断 | **可选（Demo 非前置）** | 想自己微调 tile/补帧再买；非订阅 |
| **Unity** | **$0** | 免费 | 必需 | 个人版免费（年收入 < $200k 门槛） |
| **Git / Git LFS** | **$0** | 免费 | 必需 | LFS 大文件本地 + 远端配额内 |
| **Steam Direct 上架费** | **$100** | 一次性 / 每**游戏** | **仅正式发行才需** | 注册要发行的那个游戏(主 app)时付一次；达 $1000 销售额后可退。**免费 Demo 复用主 app、不额外收费**。只想小范围试玩可用本地 exe / itch.io 免费分发，连这 $100 都可暂不花 |

**成本场景估算**：

- **固定最省月费**：`PixelLab $12/月`（图像用 Gemini 免费档）。不出 sprite 的月份可降到 **$0**。
- **做美术冲刺的某个月（峰值）**：`PixelLab $12 + (可选 GPT Plus $20) + Suno $10 ≈ $42`，且只此一两个月。
- **一次性支出合计**：`Aseprite $20（可选）+ VFX 包 ~$20 + Steam $100（仅正式发行才付）≈ $140`。
- **只做可玩 Demo、还不正式上架**：约 **$30–80**（几个月 PixelLab + 可选音乐/VFX；图像走 Gemini 免费档；本地 exe 分发，免 Steam $100）。
- **到 Steam 正式上架的总现金（务实估）**：约 **$150–250**（含 Steam $100 + 美术冲刺几个月点状订阅）。

**省钱铁律**：① 订阅按"用到才开、用完即停"；② 图像优先 Gemini 免费档，GPT Plus 仅临时救场；③ VFX/SFX 先翻免费（kenney/freesound）再考虑付费包；④ Aseprite 与 Steam 费用拖到真正需要时再付。⑤ **免费 Demo 不单收费，$100 是正式发行那个游戏时才付的一次性费用，免费试玩可先走 itch.io / 本地 exe。**

---

## 11. 开发顺序（两条线并行）

> 不是日程表，是依赖与并行策略。**主线（代码）与美术线并行，互不阻塞，最后换皮对接。**

**主线（agent 主导，玩家审查）**
1. Domain：`Unit/BattleMap/Stats/DamageCalc`（纯 C# + 单测）+ 移动范围/A* + 回合状态机 → 最简"移动+普攻"。
2. Battle View/Input：选格→移动范围→移动→攻击范围→命中预览→确认→执行；飘字/血条/退缩/运镜（用占位色块或现有 LingShuang）。
3. 远程 + 法术 + 相克：弓/标枪弹道、火球、弓克骑兵。
4. AI：3 冲锋 + 1 驻守 + 1 骑兵跑通；敌方回合运镜与节奏停顿。
5. 关卡封装：村庄一关 LevelDef，胜负条件，前后对话（可极简）。
6. 最简 UI + 主菜单 + 胜负界面。
7. （里程碑 1 达成：灰盒 3v5 可玩）

**美术线（玩家主导，agent 写脚本/规范/导入）**
- a. 定 tile 规格（64px/调色板/光照方向）+ 写无缝脚本 + autotile 边角合成脚本。
- b. 出地面 base tile（草/土/路/水/桥）+ 物件（房/树/石/井/栅栏/田）。
- c. 出 3 我方 + 敌兵种 sprite（PixelLab，按 §5 方向约定）+ 投掷/法术 VFX（素材库）。
- d. 出 UI kit（整套一次）+ 立绘（已有部分补齐）。
- e. AI 音乐 + SFX 库筛选。

**收尾**
- 换皮对接（占位 → 真素材）→ 调平衡 → 3 人盲测 → 打包 Windows exe → Steam 商店页素材（截图/GIF/简介）。

**M1 出口**：满足 §1.5 全部 6 条。

---

## 12. 风险登记（v2）

| 风险 | 等级 | 缓解 |
|---|---|---|
| 美术迭代工时不可控 | **高** | 灰盒先行，美术不阻塞主线；脚本自动化机械步骤；审美标准对 Demo 适度放宽 |
| autotile 边界 tile 纯生成精度不足 | **中-高** | 脚本自动合成兜底 Demo；后期再考虑 Aseprite 补笔 |
| 合成神兽 sprite 崩 | 中 | 改用单一生物坐骑（飞马），狮鹫降级后期 |
| 范围蔓延（"再加一个角色/系统"） | **极高** | M1 冻结 3v5 一关；新需求进 backlog，M1 完成前不动 |
| 切战斗场景诱惑 | 中 | 明确推后；架构已做成事件订阅者，未来加不返工 |
| 单人动力衰减 | 高 | 里程碑 1（灰盒可玩）尽快达成换取正反馈 |
| Unity 隐性坑（解析丢行、Gizmos 误操作等） | 中 | 遵守既有铁律（行长度校验、先看 Console）；见 developing_process 经验 |
| 数值平衡耗时 | 中 | Demo 只求"能玩通、有取舍"，发布前一次 pass |

---

## 13. 决策日志（v2 增量）

| 日期 | 决策 | 理由 |
|---|---|---|
| 2026-06-15 | 战场地图从"单张 AI 大图"改为"64px tile + 分层" | 大图不可编辑/复用/scalable；20 天实验证明 Flux+CN 画整张对齐成本极高 |
| 2026-06-15 | 出图改为多模型分工（GPT/Gemini 主力，Flux/LoRA 变种，PixelLab sprite） | Gemini/GPT 语义遵从远强于 Flux；分工各取所长 |
| 2026-06-15 | 引入 Unity Rule Tile(autotile) + Python 自动无缝/边角合成 | 让"只审美、不手绘"的玩家也能产出可拼接 tile |
| 2026-06-15 | Demo 维持大地图原地结算，但做成 Domain 事件订阅者 | 省 40–80h；未来切战斗场景是横向叠加、不改 Domain |
| 2026-06-15 | 方向：S 静止 / 侧背走 / E=W 镜像偏 S，不做纯侧面 | 火纹/梦战范式；规避 PixelLab 纯侧视角易崩与方向标注偏差 |
| 2026-06-15 | 坐骑用单一真实生物（飞马），狮鹫等合成神兽降级后期 | 合成神兽小图必崩成狮子且丢翅膀 |
| 2026-06-15 | UI 一次出整套 kit + 9-slice，不逐个按钮生成 | 逐个生成风格必不统一 |
| 2026-06-15 | 开发策略：先"灰盒可玩"(50–70h)再换皮 | 一次性拆系统风险；美术并行不阻塞；尽快获得正反馈 |
| 2026-06-15 | Demo 目标定为"上 Steam 商店页可展示的 3v5 村庄关" | 给单人项目一个明确、可达、可对外的里程碑 |
| 2026-06-15 | Aseprite 对 Demo 非前置；机械处理交脚本 | 玩家只审美不手绘；建议长期投 2–4h 学微调 |
| 2026-06-15 | 图像生成首选 Gemini "Nano Banana"(免费档)，GPT Plus 仅临时救场 | 省固定月费；Gemini 语义/一致性已够强。固定月费压到 PixelLab $12 |
| 2026-06-15 | 第三个我方角色 = 小（弓兵） | 凑齐近战/远程/法术三类；与敌方骑兵构成"弓克骑"相克 showcase |
| 2026-06-15 | 相克改为占位系数(默认1.0) + 梦战表(剑>枪>骑/圣>暗/弓>飞弱近战/暗微克全体)，斧暂归剑系 | 相克本质是查表系数，不该现在纠结数值；枚举保留 Axe 接口 |
| 2026-06-15 | 未来切战斗画面 = 单朝向 SE + Flux 静态背景，净增 ~25–50h | 玩家洞察：战斗演出固定左打右，动作只需一侧身；Flux 适合静态背景。但舞台/编排/精细帧省不掉，仍净增 |
| 2026-06-15 | 地图保留 35×35，用 `LevelDef.BattleBounds` 框定 ~16×16 战斗子区域 | 真正约束是可走走廊不是网格维度；不重出图零返工；35×35 当世界、框当舞台，未来飞兵关扩容 |

---

## 14. 出口 → 下一步

本 spec 经 hualiang review 后：
1. 开 `Assets/Scripts/Domain/`，先写 `Unit / BattleMap / Stats / DamageCalc` + 单测，落地里程碑 1 第 1 步。
2. 美术线并行启动 §11 的 a/b（tile 规格 + 无缝脚本）。
3. 定下 Demo 地图尺寸（35×35 → 缩小？）与 3v5 具体布阵。
