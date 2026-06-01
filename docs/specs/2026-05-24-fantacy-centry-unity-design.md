# 《幻世纪》Unity 版 — 设计规格书

> **日期**：2026-05-24
> **作者**：hualiang
> **状态**：草案 v1，待若干 TODO 调研结果回填
> **取代**：`FamilyGame/src/game/FantacyCentry/` 下的 Python/Pygame 原型（保留为设计参考，不再继续开发）

---

## 1. 项目定位

### 1.1 一句话目标

用 Unity 制作一款 **48×48 像素风战棋 SRPG**，参考火焰纹章的战斗循环、梦幻模拟战的兵种相克与转职、FFT 的战术深度，配以现代精致立绘。

### 1.2 范围

| 维度 | 最终目标 | 垂直切片 (M1) |
|------|---------|-------------|
| 关卡数 | 20 关主线（从原大纲 35 关砍掉部分练级/支线） | **序章 3 关** |
| 可招募角色 | 10 人（沿用 [游戏大纲.md](../../src/game/FantacyCentry/游戏大纲.md)） | **2 人**（陆离 + 苏瑶） |
| 职业 | 10 基础职业 + 转职 | **2 基础职业**（剑士、法师），不含转职 |
| 单周目时长 | 25-40 小时 | 30-60 分钟 |
| 美术 | 精致 48×48 像素 + 高清立绘 | **同等品质**（垂直切片就是品质标杆） |

### 1.3 不在范围内（明确排除，防止蔓延）

- ❌ 多周目继承、好感度系统、隐藏角色、隐藏结局
- ❌ 永久死亡（角色 HP 归 0 仅当回合退场，关卡结束复活）
- ❌ 联机/合作
- ❌ 移动端适配（首发 PC，Steam Deck 兼容是 bonus）
- ❌ 战斗切场景大动画（FFT/FE 那种独立战斗画面）—— **全部在大地图上小人挥剑**
- ❌ 配音
- ❌ 工艺/合成/料理/钓鱼等支线玩法

### 1.4 成功标准（垂直切片 M1）

完成时必须满足**全部**以下：

1. 可在 Windows 上双击 exe 启动，跑完序章 3 关，进入"通关"画面
2. 朋友（不告诉他们这是 demo）能上手玩，无需口头指导
3. 任意 3 人盲测后，**没有人**说"美术像占位符"
4. 战斗节奏（一个回合内的等待感）不显著差于 GBA 火纹
5. 有存档/读档，关闭重开不丢进度
6. 我自己回头玩，不会觉得"这界面/手感我必须重做"

---

## 2. 技术栈

| 类别 | 选择 | 理由 |
|------|------|------|
| 引擎 | **Unity 6 LTS** (6000.0.x) | 像素 SRPG 生态最成熟；URP 2D 渲染管线对像素友好 |
| 语言 | C# | Unity 一等公民 |
| 渲染管线 | **URP 2D Renderer** | 支持 2D 光照、后处理；性能足够 |
| 像素相机 | URP Pixel Perfect Camera | 防像素抖动 |
| UI | **UI Toolkit**（HUD 与菜单），UGUI 兜底（复杂战斗 UI 如有需要） | UI Toolkit 是 Unity 未来方向，但对话/伤害飘字这种世界空间 UI 仍可能用 UGUI |
| 寻路 | 自实现 A*（网格寻路） | Unity NavMesh 不适合离散网格；自己写约 200 行 |
| Tilemap | Unity Tilemap | 标配 |
| 动画 | Animator + 帧动画（Animation Clip） | 不用 Spine（成本高且像素美术不需要骨骼） |
| 存档 | JSON（Newtonsoft.Json）+ 本地文件 | 简单可靠；不需要云存 |
| 配置数据 | **ScriptableObject** | Unity 最佳实践，可视化编辑角色/职业/技能/敌人 |
| 本地化 | Unity Localization Package | 一开始只做中文，但接口预留 |
| 音频 | Unity AudioSource + AudioMixer | 标配 |
| 版本控制 | Git + Git LFS（美术资源） | 标配 |
| IDE | Rider 或 VS Code + C# Dev Kit | 自选 |

---

## 3. 架构

### 3.1 模块划分（高层）

```
┌────────────────────────────────────────────────┐
│             Game (启动/场景流转/全局状态)        │
└────────────────────────────────────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────┐      ┌──────────────┐    ┌──────────┐
│ Meta 层  │      │  Battle 层    │    │ Asset 层 │
│ (大地图/  │◄────►│ (战斗场景核心) │◄──►│ (素材加载) │
│ 存档/UI)  │      │               │    │           │
└──────────┘      └──────────────┘    └──────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   ┌────────┐      ┌─────────┐      ┌─────────┐
   │ 规则   │      │  表现   │      │  AI     │
   │ Domain │      │  View   │      │ Service │
   └────────┘      └─────────┘      └─────────┘
```

### 3.2 关键设计原则

1. **Domain（规则）与 View（表现）解耦**
   - `BattleState`、`Unit`、`Skill`、`DamageCalc` 是纯 C# 类，**不依赖 UnityEngine**，可单元测试
   - `BattleView`、`UnitView`、`HUDView` 是 MonoBehaviour，监听 Domain 事件做表现
   - 沟通方式：Domain 抛事件（如 `UnitMoved`、`UnitDamaged`），View 订阅并播动画
2. **数据驱动**：所有角色/职业/技能/敌人/关卡均为 ScriptableObject 资产，避免硬编码
3. **回合状态机**：明确的 `TurnPhase`（玩家回合 / 敌方回合 / 中立回合 / 结算）状态转换，禁止隐式状态
4. **命令模式**：玩家的"移动→选行动→选目标→确认"序列化为 `BattleCommand`，便于撤销、AI 复用、回放

### 3.3 模块清单（垂直切片所需）

| 模块 | 职责 | 文件归属（建议） |
|------|------|----------------|
| `Game.Boot` | 启动、场景加载、全局服务定位 | `Assets/Scripts/Boot/` |
| `Game.Save` | 存档读写 | `Assets/Scripts/Save/` |
| `Game.Meta` | 章节选择、关卡前剧情、关卡结算 | `Assets/Scripts/Meta/` |
| `Battle.Domain` | 战斗规则纯逻辑 | `Assets/Scripts/Battle/Domain/` |
| `Battle.View` | 战斗表现（角色/地图/UI） | `Assets/Scripts/Battle/View/` |
| `Battle.View.Effects` | **弹道、命中特效、buff 圈等 VFX**（与角色 sprite 独立的 GameObject）| `Assets/Scripts/Battle/View/Effects/` |
| `Battle.Input` | 玩家输入与命令构造 | `Assets/Scripts/Battle/Input/` |
| `Battle.AI` | 敌方 AI 决策 | `Assets/Scripts/Battle/AI/` |
| `Battle.Pathfinding` | A* 网格寻路 | `Assets/Scripts/Battle/Pathfinding/` |
| `Data` | ScriptableObject 数据定义 | `Assets/Scripts/Data/` |
| `Dialogue` | 对话/剧情播放 | `Assets/Scripts/Dialogue/` |
| `Audio` | 音乐与音效管理 | `Assets/Scripts/Audio/` |
| `UI.Common` | 通用 UI 组件（飘字、菜单） | `Assets/Scripts/UI/` |

---

## 4. 核心系统设计

### 4.1 数据模型（Domain 层 C# 类）

```csharp
// 纯数据，无 Unity 依赖
public class Unit {
    public string Id;
    public CharacterDef Def;          // SO 引用
    public JobDef Job;                // 当前职业
    public int Level;
    public int Hp, MaxHp, Mp, MaxMp;
    public Stats Stats;               // 力/魔/防/魔抗/速/移动
    public List<SkillDef> Skills;
    public EquipmentSet Equipment;
    public GridPos Position;
    public Facing Facing;
    public Team Team;                 // Player / Enemy / Ally
    public TurnState TurnState;       // Idle / Moved / Acted / Done
}

public class BattleState {
    public BattleMap Map;
    public List<Unit> Units;
    public int TurnNumber;
    public Team CurrentTeam;
    public TurnPhase Phase;
    public WinCondition WinCondition;
    public LoseCondition LoseCondition;
}
```

### 4.2 战斗回合流程

```
关卡开始
  ↓
[玩家回合]
  ↓ 对每个我方单位（玩家自由选择顺序）
  ├─ 选中单位 → 显示移动范围（蓝）
  ├─ 选择移动目标格 → 显示攻击范围（红）
  ├─ 选择行动：普攻 / 战技 / 魔法 / 道具 / 待机
  ├─ 选择目标 → 显示命中/暴击/伤害预览
  ├─ 确认 → 执行 → 该单位 TurnState = Done
  └─ （可撤销至 Moved 之前的状态，但不可撤销 Acted）
  ↓ 所有单位 Done 或玩家点击"结束回合"
[敌方回合] — AI 按速度顺序行动
  ↓
[中立回合]（如有）
  ↓
[回合结束结算] — 状态效果 tick、增益减益持续时间 -1
  ↓
检查胜负条件 → 是否结束
  ↓ 否
TurnNumber++ → 返回 [玩家回合]
```

### 4.3 伤害公式（草案，可调）

```
物理伤害 = max(1, (攻方力量 × 武器系数 + 技能加成) - 守方防御)
魔法伤害 = max(1, (攻方魔力 × 法术系数 + 技能加成) - 守方魔抗)

兵种相克倍率：
  克制方造成 × 1.25，受到 × 0.75
  被克制方造成 × 0.75，受到 × 1.25

地形修正：
  防御格：受到伤害 × 0.8，命中 -10%
  森林：闪避 +15%
  高地（如有）：射程 +1，命中 +10%

命中率 = clamp(攻方速度 × 2 + 武器命中 - 守方速度 × 2 - 地形闪避, 10, 100)
暴击率 = clamp(武器暴击 + 角色暴击 - 守方暴击抵抗, 0, 50)，暴击 × 1.5 伤害

反击：
  守方存活 + 反击距离覆盖 + 未陷入"无法反击"状态 → 反击 1 次
```

> 数值平衡是另一个长期话题，垂直切片用上面的公式跑通即可，后期专门做平衡 pass。

### 4.4 兵种相克（简化版，先做出感觉）

| 克制方 | 被克方 |
|--------|--------|
| 剑 | 斧 |
| 斧 | 枪 |
| 枪 | 剑 |
| 弓 | 飞行单位 |
| 魔法 | 重甲 |
| 物理 | 法师（脆皮） |

垂直切片只需"剑士 vs 法师"，相克可以先不触发，但**接口要预留**。

### 4.5 AI（垂直切片版）

垂直切片只做 3 档 AI：

1. **冲锋型**（盗贼、野兽）：每回合朝最近的我方单位寻路移动，能攻击就攻击
2. **驻守型**（守军）：玩家进入感知范围（如 3 格）才主动出击，否则站桩
3. **目标型**（保护/护送场景需要）：朝指定坐标移动

后期再加：聚焦弱势目标、优先治疗友军、走位规避反击等。

### 4.6 关卡数据格式

每关一个 ScriptableObject + 一个 Tilemap 场景：

```csharp
[CreateAssetMenu]
public class LevelDef : ScriptableObject {
    public string LevelId;
    public string DisplayName;
    public SceneReference BattleScene;     // 含 Tilemap 的场景
    public List<UnitSpawn> PlayerSpawns;   // 起始位置（玩家可重排）
    public List<UnitSpawn> EnemySpawns;
    public WinConditionDef WinCondition;   // 击败全部 / 击败首领 / 到达点 / 坚守 N 回合
    public LoseConditionDef LoseCondition; // 主角阵亡 / N 回合内未达成 / NPC 全灭
    public DialogueDef PreBattleDialogue;
    public DialogueDef PostBattleDialogue;
    public RewardDef Rewards;
}
```

### 4.7 存档

- 槽位：3 个手动 + 1 个自动（关卡开始时自动存）
- 内容：当前章节进度、队伍角色状态（等级/装备/技能）、金钱、剧情标记
- **不支持战斗内存档**（垂直切片）

---

## 5. 美术管线 ★（项目最大风险点，2026-05-25 修订）

### 5.1 风格基准 —— PixelLab 主力工作流

**锁定的技术规格（任何角色生成都不准改）**：

| 项 | 值 | 说明 |
|---|---|---|
| 工具 | **PixelLab.ai Tier 1**（$12/月）| 商业授权，2000 图/月 |
| Sprite Size | **48px** | UI 选定的是角色本体尺寸 |
| Canvas Size | **~88×88 或 92×92**（PixelLab 自动 padding）| 为动画位移预留空间，不是角色本体变大 |
| Camera View | **Low Top-Down** | SRPG 标准俯视角度 |
| Generation Mode | **v3**（含自动 8 方向旋转）| 不用 Standard |
| Character Type | Humanoid | 杰兵、人型怪都走这个 |
| Tile Size | **48×48**（决定 TODO-T2）| 与 sprite 本体 1:1，角色占一格但 sprite 占 ~1.8 格还原 FFT / Tactics Ogre 观感 |

**必需的 prompt 锁风格锰点（所有角色 prompt 都要以此开头）**：

```
Fire Emblem GBA style [archetype], western fantasy, [角色描述...], clean pixel art, sharp silhouette
```

实验验证（PixelLab spike 2026-05-25）：加了此锰点 → 3 个角色头身比/渲染风格明显一致；没加 → 出现"粉发弓箭手" 这种 Q 版头身比离群点。

**立绘**：高清（建议 1024×1024 半身），现代精致风格（参考《风花雪月》《圣兽之王》水彩感）。生成工具 TBD（TODO-A2）。

**统一性底线**：所有像素角色风格一致，所有立绘画风一致。一旦发现漂移角色 → 用 PixelLab "Create from Reference" 贴上陆离 sprite 作为参考重生成；反复抢救仍失败 → 考虑升级 Scenario.gg LoRA。

### 5.2 单角色所需资源清单（2026-05-25 大幅瘦身）

**动画集（1 State × 4 Animations × 4 Directions）**：

| 动作 | 帧数 | 方向 | 实际产出 |
|---|---|---|---|
| Idle | ~2 帧循环 | S/E/N（W 由 E 水平翻转）| 3 组 sprite sheet |
| Walking | 4 帧 | S/E/N | 3 组 |
| Attack（用 Custom 或 Punching/Kicking） | 4 帧 | S/E/N | 3 组 |
| Reactions（受击） | 2 帧 | S/E/N | 3 组 |

**小计：~12 组动画 / 角色，~50 张 PixelLab 生成额度**。Tier 1 2000 张/月 → 单月能生产 ~40 个角色，远超项目需求。

**省略的动画**：
- 8 方向→只做 4 方向（SRPG 网格本身就是上下左右，FE/Langrisser/FFT 都是 4 方向）
- W 方向在 Unity 里用 `flipX = true` 复用 E 方向 sprite，**不生成**
- Running / Jumping / Crouching 等 PixelLab 提供的其他动作 **不做**，与战棋无关
- 胜利姿势、死亡动画 → **推到 M2**（M1 用 Reactions 最后一帧作为倒下帧即可）

**立绘侧（每个角色）**：
- 1 张标准立绘
- 2-3 种表情差分（普通/愤怒/受伤/微笑）
- 头像（对话框用，64×64 切自立绘即可）

**地图素材**：
- 平原 / 森林 / 山地 / 水域 / 道路 / 墙 / 门 / 村庄 房屋等
- 序章只需"村庄+荒野+森林"
- 可以与 PixelLab tileset 生成或 itch.io 买现成包组合，取決于 A1 验证结果

### 5.3 资源获取策略（按优先级，2026-05 修订）

> **重要修订**：2026 年 5 月的 web 调研发现，专业像素 AI 工具（PixelLab.ai、Retro Diffusion、Scenario.gg）已经成熟到可作为主力生产工具，不再是"辅助"。Ubisoft、Mighty Bear、InnoGames 等公司已大规模使用 Scenario.gg 训练自己的 LoRA 生产生产环境素材。

1. **首选（主力）**：**AI 像素生成工具**
   - **PixelLab.ai**（$12/月起）：文字 → 角色 sprite sheet，一键 4/8 方向旋转，骨骼动画，风格一致性 inpainting，tileset/UI 生成。商业授权。**对单人项目最合适**
   - **Retro Diffusion**（按用量计费）：专门的 "Walking & Idle" 和 "Four Angle Walking" 动画模型，pixel-grid 精确
   - **Scenario.gg**（$30+/月）：训练你自己的风格 LoRA，把陆离/苏瑶等角色画风锁定，多角色一致性最佳方案。如果 PixelLab 风格漂移控制不住，升级到这条
2. **次选**：购买现成统一风格素材包（itch.io / Unity Asset Store / Booth），主要用于 AI 不擅长的复杂 tileset、UI 装饰
3. **立绘**：MidJourney / Gemini / SDXL 生成 + Photoshop 润色（2026 立绘 AI 已极成熟，~90 分）
4. **委托外包**：仅在 AI 和素材包都搞不定的极少数情况（如关键 BOSS 立绘）
5. **绝对避免**：拼接多个画风明显不同的素材包；让多种 AI 工具输出混用而不做风格锁定

**风格统一性策略**：
- 选定 1 个主工具（推荐 PixelLab）作为"风格之源"
- 第一张角色（陆离）生成满意后，将其作为后续所有角色/UI/tile 的**视觉锚点**（reference image / LoRA 训练集）
- 任何新素材出来都和锚点对比，画风偏了就重做或修图


### 5.4 动画与表现要求（垂直切片必须达到）

- 角色移动是"走过去"，不是"瞬移"
- 攻击时有挥剑动画 + 受击方有闪白和后退一格的退缩
- HP 变化是"条动画 + 飘字"，不是"数字突变"
- 击杀有黑屏淡出/像素粒子消散
- 镜头会跟随当前行动单位
- 选中单位时有呼吸光圈
- 攻击范围 / 移动范围有半透明颜色覆盖 + 边缘高亮
- 命中预览面板（伤害 / 命中率 / 暴击率）显示在屏幕一角，不挡视野
- **菜单/UI 也要有像素风格的边框装饰，不能是 Unity 默认灰白按钮**

### 5.5 远程攻击与特效（弹道/VFX）

**架构原则**：弹道、命中特效、buff 圈是**独立于角色 sprite 的 GameObject**，不是角色动画的一部分。角色 attack 动画只负责"出手姿势"，出手帧触发后独立实例化 Projectile/Effect Prefab。

**三类远程攻击**：

| 类型 | 示例 | 实现 |
|---|---|---|
| 实体弹道 | 弓箭 | 独立 Arrow sprite（~16×4），沿直线 Lerp 0.3-0.5s 飞到目标 |
| 飞行法术 | 火球 | 火球本体 4-8 帧循环 + 命中 6-10 帧一次性爆炸 |
| 直射/冲击 | 光束 | 一条 sprite 从施法者拉到目标，0.2s 缩放淑出 |

**资源获取分工**：

| 资产类型 | 推荐源 | 原因 |
|---|---|---|
| 角色 sprite | PixelLab | 主力 |
| **弹道 / 命中 VFX / buff 圈** | **itch.io / kenney.nl 买现成 pixel VFX 包** | 有专业像素 VFX 艺术家做这个，$5-10 一整套覆盖所有元素；VFX 是抽象火光电波，混用 PixelLab 不会风格冲突 |

**射程与区域数据**：纯为 `SkillDef` 上的字段，与动画/特效无关。示例：
```csharp
public class SkillData : ScriptableObject {
    public int minRange;      // 法师法术 = 2（不能贴脸）
    public int maxRange;      // 法师 = 3，弓箭手 = 5
    public int areaOfEffect;  // 单体 = 0，3x3 = 1
}
```

### 5.6 Unity 导入设置规范（像素游戏必遵）

PixelLab 导出 **PNG sprite sheet**（不是 GIF，Unity 不支持 GIF 动画导入）。文件命名约定：`{character}_{action}_{direction}.png`，例 `luli_attack_south.png`。

**所有像素 PNG 必须的导入设置**（不改会变糊）：

| 设置 | 默认 | 必须改为 | 原因 |
|---|---|---|---|
| Texture Type | Default | **Sprite (2D and UI)** | 作为 sprite 使用 |
| Sprite Mode | Single | **Multiple** | 一张图切多帧 |
| Pixels Per Unit | 100 | **48**（= tile size）| 1 unity unit = 1 tile |
| **Filter Mode** | Bilinear | **Point (no filter)** | **最关键，不改会糊成马赛克** |
| Compression | Normal | **None** | 防颜色失真 |
| Wrap Mode | Repeat | Clamp | 防边缘伪影 |

**切帧流程**：Inspector → Sprite Editor → Slice → Grid By Cell Size → 输入 PixelLab 画布尺寸（~88 或 92）。

**项目级优化**：阶段 1 进 Unity 后写一个 `AssetPostprocessor` 脚本（约 20 行），让 `Assets/Art/Characters/` 下所有 PNG 自动应用以上设置，免手动重复。

---

## 6. 项目结构

```
FantacyCentry-Unity/                  # 新仓库（或 FamilyGame 下新目录）
├── Assets/
│   ├── Scripts/                      # 见 §3.3 模块清单
│   ├── Art/
│   │   ├── Characters/               # 角色像素 sprite + Animator
│   │   ├── Portraits/                # 立绘
│   │   ├── Tilesets/                 # 地形 tile
│   │   ├── UI/                       # UI 装饰
│   │   └── VFX/                      # 特效
│   ├── Audio/
│   │   ├── BGM/
│   │   └── SFX/
│   ├── Data/                         # ScriptableObject 资产实例
│   │   ├── Characters/
│   │   ├── Jobs/
│   │   ├── Skills/
│   │   ├── Items/
│   │   └── Levels/
│   ├── Scenes/
│   │   ├── Boot.unity
│   │   ├── MainMenu.unity
│   │   ├── WorldMap.unity
│   │   └── Battles/
│   │       ├── Prologue_01_VillageRaid.unity
│   │       ├── Prologue_02_FireEscape.unity
│   │       └── Prologue_03_BanditAmbush.unity
│   └── Settings/                     # URP 配置、Input Actions 等
├── ProjectSettings/
├── Packages/
├── docs/
│   ├── specs/                        # 设计规格
│   ├── data/                         # 数值表、平衡 doc
│   └── art/                          # 美术规范、素材来源台账
└── .gitignore + .gitattributes (LFS)
```

---

## 7. 开发顺序（M1 垂直切片）

> 不是周计划（因为我不估时间）。是依赖顺序，**必须按顺序完成**，不要并行打架。

**阶段 0：风格闭环验证（开工门槛，不通过不进入阶段 1）**

> 这一阶段的产出物不是代码，是**一张让自己满意的截图**和**一套已付款的素材清单**。

调研顺序按风险从大到小（**2026-05 修订：AI 工具优先**）：

1. **PixelLab.ai spike（首选路径）**：用 free trial 生成 1 个陆离 sprite（idle+walk+attack）+ 4 方向旋转 + 1 块 tileset + 1 套 UI。**满意则订阅 Tier 1 ($12/月) 作为主力工具，跳到第 4 步**。不满意：
   - 风格漂移严重 → 考虑升级到 Scenario.gg 训练自己的 LoRA
   - 质量根本不够 → 退回传统素材包路线（第 2 步）
2. **（仅 fallback）传统素材包调研**：在 itch.io / Unity Asset Store / Booth 找 2-3 个候选 48×48 角色素材包，列出覆盖范围/价格/授权
3. **立绘方案**：MJ / Gemini / SDXL 试 5-10 个 prompt，选定与第 1 步主力工具产出风格协调的立绘画风，产出 1 张陆离立绘草样
4. **风格协调性测试（关键判定）**：把第 1 步产出 + 立绘 + UI **拼贴在一张图**（PS/Krita/PPT 均可），自我审判：
   - 像素和立绘画风冲突吗？（避免"Q版小人 + 写实立绘"）
   - 色调统一吗？
   - UI 和整体氛围搭吗？
   - 割裂感强 → 回到第 1 或 3 步换方案
5. **付款订阅/购入**确定的工具与素材
6. **Unity 静态 spike**：新建 Unity 项目，配置 URP 2D + Pixel Perfect Camera + Git LFS；在场景里搭出一张**静态画面**：
   - Tilemap 一小块地图
   - 1 个像素角色站在地图上（不需要动画，静态 sprite 即可）
   - 屏幕一角一个像素风对话框 + 立绘 + 几行文字
   - 屏幕另一角一个像素风 HP/MP 条 + 一个像素风菜单按钮
7. **最终判定（开工闸门）**：截图，自问：
   > **"如果这是 Steam 商店页第一张图，我愿意点进去吗？"**
   - 愿意 → 通过，进入阶段 1
   - 不愿意/将就 → **回到第 1 步**，**绝对不进入代码阶段**

> 这个判定看起来很主观，但正是 SRPG 项目最关键的一道闸门。一旦带着"将就"的美术进入系统开发，后期重做的代价是 10 倍。

**阶段 1：美术管线打通（最重要的关卡）**
- 把 1 个角色（陆离）的待机/行走/攻击/受击动画在 Unity 里跑起来
- 用 Tilemap 拼一张静态测试地图
- Pixel Perfect Camera 配置无抖动
- 角色能在 Tilemap 上以网格为单位走 A→B（带动画、带行走轨迹平滑）
- **如果到这里就觉得美术达不到预期，停下来重新选素材，不要继续**

**阶段 2：战斗 Domain**
- 实现 `Unit`、`BattleState`、`BattleMap`、`Stats`、`DamageCalc`（纯 C#，写单元测试）
- 实现 A* 寻路（带障碍、带地形消耗）
- 实现回合状态机
- 实现 1 个最简单的命令：移动 + 普攻

**阶段 3：战斗 View 与 Input**
- 玩家可点击我方单位 → 显示移动范围 → 点目标格移动 → 显示攻击范围 → 点敌人 → 命中预览 → 确认 → 执行
- 表现：角色走过去、挥剑、伤害飘字、HP 条动画、敌人受击退缩
- 镜头跟随
- 屏幕 UI：当前回合数、当前队伍指示、单位信息面板

**阶段 4：战技 / 魔法 / 兵种相克**
- 苏瑶的"火球"魔法（消耗 MP + 范围特效）
- 陆离的"破甲斩"战技（消耗 SP + 单体高伤）
- 兵种相克倍率应用

**阶段 5：AI**
- 敌方"冲锋型"AI 跑通
- 敌方回合的相机自动跟随
- 单位行动间的节奏停顿

**阶段 6：关卡封装**
- 把序章第 1 关（猎村突袭）装成完整关卡：起始对话 → 战斗 → 结束对话 → 结算
- 胜利条件（击败全部敌人）+ 失败条件（陆离阵亡）
- 经验值与升级

**阶段 7：Meta 层**
- 主菜单
- 简化版章节选择（3 个节点的小地图）
- 关卡间过渡
- 存档/读档

**阶段 8：剩余 2 关**
- 序章第 2 关（烈火逃亡，逃脱型，限回合数）
- 序章第 3 关（荒野伏击，地形利用教学）

**阶段 9：润色与盲测**
- 音效（攻击/受击/UI/脚步声/BGM）—— 哪怕用免费音效包
- 平衡（让 3 关都不简单也不挫败）
- 找 3 个朋友盲测，根据反馈修
- 打包 Windows exe

**M1 出口**：满足 §1.4 全部 6 条成功标准。

---

## 8. 待调研 TODO（spec 完稿前需回填）

> 这些是 spec 中的"未知数"，需在进入实施前由 hualiang 调研后回填到本文档。

- [ ] **TODO-A1**（最高优先级，半天到一天可出结论）：**PixelLab.ai 风格验证 spike**。先用 free trial（40 张图）尝试以下产出，判断画风是否符合期望：
  - 1 个陆离（中式剑士）的 idle + walk + attack sprite sheet
  - 一键 4 方向旋转
  - 1 块小村庄 tileset
  - 1 套像素风 UI（对话框 + HP 条 + 菜单按钮）
  - 满意 → 订 Tier 1（$12/月），定为主力工具
  - 不满意 → 升级试 Scenario.gg LoRA 方案 或 退回素材包路线
- [ ] **TODO-A2**：立绘工作流。MJ / Gemini / SDXL 生成陆离立绘 + 试 2-3 种风格，选定 1 种与 PixelLab 像素画风协调的方案，写入 `docs/art/portrait-pipeline.md`（含 prompt 模板、后处理流程）
- [ ] **TODO-A3**：AI 兜底 —— 如果 PixelLab 出的 UI / tile 不够好，调研 itch.io / Asset Store 的像素 UI 装饰素材包作为补充
- [ ] **TODO-A4**：调研免费/低价 BGM/SFX 包（kenney.nl、freesound、Asset Store 限免）
- [ ] **TODO-A5**：如果 A1 决定走 Scenario.gg LoRA 路线，准备 LoRA 训练集（5-100 张参考图，定义"幻世纪" 视觉 DNA）
- [ ] **TODO-T1**：决定项目代码仓库位置 —— 在 `FamilyGame/` 下新开 `FantacyCentry-Unity/` 子目录，还是开独立 git 仓库？
- [x] ~~**TODO-T2**~~：定为 **48×48 tile + ~88 sprite canvas**（FFT/Tactics Ogre 风，PixelLab 默认输出匹配）
- [x] ~~**TODO-T3**~~：定为 **4 方向生成**（S/E/N，W 由 E 翻转）
- [ ] **TODO-S1**：原大纲 35 关 → 20 关的具体取舍（哪些关砍掉，哪些合并），单独出文档
- [ ] **TODO-D1**：序章 3 关的对话剧本初稿
- [ ] **TODO-D2**：陆离、苏瑶两人的具体技能列表（垂直切片每人 2-3 个技能即可）

---

## 9. 风险登记

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| 美术风格不统一 / 多角色画风飘移 | **中**（2026-05-25 再下调，静态 sprite 验证有效）| 锁定 prompt 锰点 `Fire Emblem GBA style`；飘移角色用 `Create from Reference` 重生；需要时升级 Scenario.gg LoRA |
| AI 工具动画质量不达自审标准（Attack/React）| **高**（当前主要未知）| PixelLab Tier 1 订阅后第一件事就是验证 Attack/Reactions；软绵绵则需 Aseprite 手补关键帧，或考虑 RetroDiffusion 专用动画模型 |
| Unity 学习曲线超预期 | 中 | 资深工程师，2-4 周可达成基本生产力；卡住的部分优先 YouTube 教程而非啃文档 |
| 范围蔓延（"再加一个职业就好了"） | **极高** | M1 严格冻结在 2 角色 / 3 关；任何新需求记到 backlog，M1 完成前不动 |
| 数值平衡耗时 | 中 | M1 不追求完美平衡，"能玩通"即可，发布前做专门 pass |
| 单人项目动力衰减 | 高 | 阶段产出物可见（每阶段都有可玩的东西）；垂直切片完成后强制找朋友盲测获取正反馈 |
| 存档兼容性（后期改数据结构破坏旧存档） | 低 | M1 不重要；M2 之后存档结构加版本号 |

---

## 10. 决策日志

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-05-24 | 换 Unity，弃 Pygame 原型 | 表现力天花板低，且原型为 1 小时 AI 生成，无保留价值 |
| 2026-05-24 | 战斗在大地图演出，不做切场景动画 | 减少美术工作量；火纹 FE6/7/8 也都有"快速战斗"模式证明可行 |
| 2026-05-24 | 不做永久死亡 | 降低叙事和数值设计难度；放低玩家压力 |
| 2026-05-24 | 关卡数 35 → 20 | 单人完整作品的现实工作量 |
| 2026-05-24 | 垂直切片必须美术达标，不接受占位符 | 否则"互砍 demo" 无意义，参见用户认知 |
| 2026-05-24 | M1 范围冻结：2 角色 / 3 关 / 2 职业 / 无转职 | 控制工作量，先打通完整管线 |
| 2026-05-24 | 增加阶段 0「风格闭环验证」作为开工硬闸门 | 单点风险是美术风格协调而非"找到素材"；通过一张静态截图自我审判，未通过禁止进入代码阶段 |
| 2026-05-24 | 美术资源策略反转：AI 工具为主力，素材包退为兜底 | Web 调研 2026-05 状态：PixelLab.ai 已支持文字生成动画 + 一键 4/8 方向 + 风格一致 inpainting；Retro Diffusion 有专门动画模型；Scenario.gg 被 Ubisoft 等大厂用于生产环境。AI 已从"辅助"升级为"主力候选"，对单人项目尤其经济（$12/月 vs 数千元委托）|
| 2026-05-25 | PixelLab spike 初步成功，锁定为主力工具候选 | 用陆离/苏瑶/帝国兵 3 个 prompt 生成静态 sprite，加 `Fire Emblem GBA style` 锰点后风格一致。动画质量仍需验证（Idle/Walk/Attack/React）|
| 2026-05-25 | T2 定：48×48 tile，~88 sprite canvas | PixelLab 默认输出匹配，免重做；FFT 风观感 |
| 2026-05-25 | T3 定：4 方向生成（W 由 E 翻转）| SRPG 网格本身 4 方向；生成量减半 |
| 2026-05-25 | 动画集锁定 4 种（Idle/Walk/Attack/React），胜利/死亡推后M2 | 控制单角色产出到 ~50 张 PixelLab 额度 |
| 2026-05-25 | 弹道/VFX 走 itch.io 素材包，不用 PixelLab | 专业 VFX 素材包质量高且低价；VFX 抽象性高，与角色画风不冲突 |
| 2026-05-25 | Unity 导入规范入 spec（PNG、Point滤镜、PPU=48）| 防止后期忘记设置导致像素变糊 |

---

## 11. 出口条件 → 下一步

本 spec 由 hualiang review 通过后：
1. 完成 §8 的 TODO 调研，回填本文档
2. 进入实施计划编写（writing-plans 流程），把 §7 的阶段拆成具体可执行任务
3. 阶段 0 启动
