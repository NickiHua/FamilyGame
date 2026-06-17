# 《幻世纪》UI 出图 Prompt 集

> **用途**：给 GPT-Image / Gemini「Nano Banana」出像素风 UI 件，再脚本抠图 + Unity 9-slice + UI Toolkit 接线。
> **配套 spec**：`docs/specs/2026-06-15-fantacy-centry-demo-to-steam-design.md` §7.5（UI 出图规范）。
> **状态**：本文件经 2026-06-16 实战出图迭代，已固化「定调图 → 逐件精修」工作流与全部踩坑修正。

---

## 0. 工作流（先读这段，否则会白干）

```
① 出一张「概念整图」定调（GPT/Gemini，列全所有件）   → 锁定视觉方向
② 把概念图作为「参考图 / init image」喂回模型，逐件精修 → 每件单独、干净、可 9-slice
③ Python 脚本抠品红底 → 透明 PNG，进 Assets/Art/UI/    → 0 手绘
④ Unity 里做 9-slice（Sprite Editor Border）+ 接线     → 文字由引擎渲染，不烤进图
```

**两条关键认知（血泪）：**

1. **概念整图 ≠ 成品素材，基本「不能直接切」**。AI 概念图像素不规整、有糊边、边框花纹未必能平铺，直接切进像素相机会糊/抖。它的价值是**锁死风格 + 当 init image**，不是拿来切。
2. **逐件精修才是主流程**，但**必须先有定调图**。没有定调图凭空逐件生成 → 每件风格漂移（spec §7.5 反对的就是这个）；有了定调图当参考再逐件 → 风格统一 + 像素干净 + 可 9-slice，两头好处都拿。这正是 spec「出概念整图 → 切片」与「逐件生成」之间的**正解**。

> **Flux 不碰 UI**：Flux 更不可控、UI 比 GPT/Gemini 弱，只负责 tile 变种。
> **兜底路线**：若逐件精修精度仍不够，立刻转买 itch.io / Kenney 现成像素 UI 包（$0–15，已做好 9-slice），别死磕——UI 不是本作卖点。

---

## 1. 已定调（2026-06-16 锁定，不要再改）

| 项 | 值 |
|---|---|
| **主色调** | **深蓝半透明面板（dark navy translucent）+ 华丽金边（ornate gold trim）** |
| 风格 | 精致像素（refined pixel art），FE GBA / 梦战 / 八方旅人 菜单气质 |
| 视角 | 正面平面（flat front-facing），非透视、非 3D |
| 背景 | **纯品红 #FF00FF**（脚本 color-key 抠图） |
| 文字 | **一律留空**（no letters / no numbers），文字由引擎渲染 |
| HP/MP 色 | 血条红、蓝条蓝；范围格：移动蓝、攻击红 |

> **概念整图 prompt（定调用，已验证出好图，是后续所有件的 init image 来源）：**
>
> ```
> Create a pixel art UI kit concept sheet for a Japanese fantasy tactical RPG / SRPG.
> Style: refined pixel art; dark navy translucent panels; ornate gold trim; clean readable tactical
> game UI; elegant but not too busy; suitable for a top-down indie SRPG with chibi pixel characters.
> Include separate examples of: square unit info panel; rectangular action menu panel; attack
> preview panel; normal button; hover button; pressed button; HP bar frame; small command icons
> (attack, skill, item, wait); 64x64 movement range tile overlay; 64x64 attack range tile overlay;
> selected tile cursor frame; phase banner with empty center.
> Important: no readable text; no letters; no numbers; no characters; no full gameplay screenshot;
> each component visually separated; transparent or plain background.
> ```

---

## 2. 逐件精修 prompt（主流程 · 每条都把上面的概念图当参考图/init 一起喂）

> **用法**：GPT-Image 上传概念图为参考；Gemini 把概念图贴进对话再发 prompt。
> **件级铁律（踩坑总结）**：
> - 每条必写 **`ONLY ... and NOTHING ELSE` + `Do NOT draw panels/bars/icons/kit`** —— 否则模型会「好心」把整套 kit 又画一遍（按钮三态那次就翻车）。
> - 背景统一 **flat magenta (#FF00FF)**。
> - **`no letters, no numbers`** 必带 —— 模型爱烤「HP/MP」字母进图。
> - 全局后缀（追加到每条末尾）：
>   ```
>   Match the attached reference exactly (dark navy translucent, ornate gold trim, refined pixel art).
>   Clean pixel art, hard edges, no anti-aliasing, no blur, no watermark, no signature, no text,
>   no letters, no numbers. Flat magenta (#FF00FF) background.
>   ```

### 2.1 主面板（9-slice 核心）✅ 已验证可用

```
Using the attached image as the exact style reference, generate ONE single menu panel, large and
centered, isolated, and NOTHING ELSE. Requirements: 9-slice ready — four distinct ornate gold
CORNERS, the four straight EDGES repeatable so they tile when stretched, a flat translucent navy
CENTER that scales to any size. No icons inside.
[全局后缀]
```
> **9-slice 提示**：四边金花纹是对称构图、非严格可平铺单元 → 做法是**四边当固定装饰边、只拉伸中心 navy**，不依赖边能否无缝重复，Demo 够用。要拉超宽才会变形，届时再修。

### 2.2 命令按钮三态 ✅ 已验证可用（关键：COMPACT + 无大角花 + 无居中高光）

```
Using the attached image ONLY for palette reference (dark navy, gold), generate ONLY ONE small
COMPACT command button shown in THREE states (a column or row) and NOTHING ELSE: Normal (navy, thin
gold bevel), Hover (blue outer glow, lit gold edge), Pressed (darker, inset). Keep it SIMPLE and
SMALL — a plain rounded navy rectangle with a THIN gold edge, minimal ornament, NO large corner
flourishes, NO long banner shape, NO centered highlight that would stretch. Must 9-slice
horizontally to any width (thin fixed left/right caps, plain repeatable middle).
Do NOT draw panels, bars, icons or a kit — only the three button states.
[全局后缀]
```
> **踩坑**：不写「COMPACT / 无大角花 / 无长横幅形 / 无居中高光」时，模型会出成华丽长横幅（那批反而适合当回合横幅）。
> **抠图注意**：Hover 的蓝色外发光要**软抠**（保留半透明渐变），不能硬阈值一刀切。

### 2.3 血条 / 蓝条（框 + 填充分离）✅ 已验证可用

```
Using the attached image as the exact style reference, generate a stat bar set and NOTHING ELSE: an
empty navy+gold beveled bar FRAME, plus a SEPARATE solid RED fill strip (HP) and a SEPARATE solid
BLUE fill strip (MP). The fills must be horizontally tileable so they can be clipped to any
percentage. Show frame and fills as separate isolated pieces.
[全局后缀]
```
> **现状**：实出常给「整根实心框条」而非严格分离。Demo 可接受 —— 把红/蓝中段按百分比遮罩裁剪，金框像素留着即可。

### 2.4 命令图标组 ✅ 已验证可用

```
Using the attached image as the exact style reference, generate a set of small square command icons
in matching navy+gold frames and NOTHING ELSE: sword (attack), spark/magic (skill), potion (item),
hourglass (wait), shield (defend), boot (move). Each icon isolated in its own square slot, arranged
in a neat row with gaps.
[全局后缀]
```
> 这是「带框图标」，Demo 够用。若要图标与槽分离（图标叠不同状态槽位），以后单出无框图标。

### 2.5 移动 / 攻击范围格 ✅ 改用脚本生成（不走 AI）

> **结论（2026-06-16 定）**：范围格**不要用 AI**。AI 给不了真 alpha——它只会画个浅色实心块、加噪点、加星标，且死守 init 图里的「4×4 带框块」跳不出来（喂参考图反而是包袱）。范围格就是「半透明纯色 + 1px 边线 + 真 alpha」的几何件，Python 几行 100% 正确。
>
> **脚本**：`scripts/ui/gen_range_tiles.py` → 输出 64×64 真 alpha PNG 到 `Assets/Art/UI/range/`：
> - `move_tile.png`（蓝，~35% alpha，1px 深蓝边）
> - `attack_tile.png`（红，~35% alpha，1px 深红边）
> - `select_frame.png`（金色四角括号，中心全透明 —— 选格框也一并脚本生成）
>
> 跑法（venv 带 Pillow）：`python scripts/ui/gen_range_tiles.py`。透明度/边色想调就改脚本里的 `fill_alpha` / `edge_rgb` 重跑。
>
> **教训**：alpha 叠加层、纯几何件 → 脚本生成，别跟模型较劲。AI 只做「有美术内容」的件。

### 2.6 选格框（选中格高亮）✅ 已验证可用

```
Using the attached image as the exact style reference, generate ONE gold selected-tile cursor frame
and NOTHING ELSE: four corner brackets with a hollow transparent center, sized to overlay a single
64x64 battle map cell.
[全局后缀]
```

### 2.7 单位信息卡 + 攻击预览卡 ✅ 已验证可用

```
Using the attached image as the exact style reference, generate TWO panels side by side in matching
navy+gold 9-slice style and NOTHING ELSE: (1) a unit info card with a square portrait-frame slot on
the left and blank stat rows + an empty HP-bar slot on the right; (2) an attack-preview card with a
left attacker box, a right defender box, and an arrow between them. All fields blank.
[全局后缀]
```

### 2.8 回合横幅 Phase Banner（蓝 / 红变体）✅ 已验证可用

```
Using the attached image as the exact style reference, generate ornamental horizontal phase banners
and NOTHING ELSE: one blue-tinted and one red-tinted variant (player / enemy phase), navy center
with gold trim and distinct decorative end caps, flat blank center for engine text.
[全局后缀]
```
> 之前「华丽长横幅」那批（误当按钮出的）也归这里用。**横幅风格挑一套统一，别混用繁简两版。**

---

## 3. 当前 UI 件清单（2026-06-16）

| 件 | 状态 | 备注 |
|---|---|---|
| 主面板（9-slice） | ✅ | 四边固定、拉中心 |
| 命令按钮三态 | ✅ | compact 版，Hover 发光软抠 |
| 血条 / 蓝条 | ✅ | 整根，按百分比裁剪 |
| 命令图标组（剑/星/药/沙漏/盾/靴） | ✅ | 带框图标 |
| 选格框（金角） | ✅ | |
| 单位信息卡 / 攻击预览卡 | ✅ | 有的烤了 HP 字母，可重出去字 |
| 回合横幅（蓝/红） | ✅ | 风格挑一套统一 |
| **移动 / 攻击范围格 + 选格框** | ✅ | **脚本生成**（`scripts/ui/gen_range_tiles.py`），非 AI |
| 标题装饰 / 胜负横幅 | ⏳ 待出 | 见 §4 |

---

## 4. 主菜单 / 标题 / 结算界面（待出，同走 §2 逐件法）

### 4.1 标题 logo 底板 + 装饰

```
Using the attached image as the exact style reference, generate ONE title-screen decorative frame
and NOTHING ELSE: ornamental gold corner flourishes, a banner ribbon area left blank for the title,
subtle fantasy motifs (swords/wings) in the corners.
[全局后缀]
```

### 4.2 胜利 / 失败界面横幅

```
Using the attached image as the exact style reference, generate TWO result banners side by side and
NOTHING ELSE: a golden "victory" ornamental plate and a darker "defeat" plate, each a wide
decorative frame with a blank center for engine text.
[全局后缀]
```

---

## 5. 出图后机械处理（脚本 + Unity，玩家不手绘）

| 步骤 | 工具 | 备注 |
|---|---|---|
| 切片（概念图/sheet → 各件） | Python / Unity Sprite Editor | 件间留间距，按区域 crop |
| 抠图（去品红底） | Python（color-key #FF00FF → alpha） | **品红常非纯 #FF00FF**（压缩噪点/半透边），用**容差**判定（红高/绿低/蓝高），非精确匹配 |
| 硬抠 vs 软抠 | Python | 硬边件硬抠；**发光件（Hover）软抠保留半透明渐变** |
| **9-slice 标定**（四角/四边/中心 Border） | Unity Sprite Editor | 面板/按钮/条/卡都要 |
| 导入设置（Point/None/Clamp） | `PixelArtImportPostprocessor.cs` | UI 同样像素锐利 |
| 接线（UI Toolkit / UGUI） | Unity | 文字用引擎渲染，**不烤进图** |

> **已有脚本**：`scripts/ui/gen_range_tiles.py` —— 脚本生成范围格/选格框（真 alpha）。
> **计划脚本**：`scripts/ui/extract_ui.py` —— 读图 → 容差 color-key 抠底（可选切片）→ 输出 `Assets/Art/UI/`。

---

## 6. 挑图 checklist（玩家把关用）

- [ ] 风格是否与**定调图（深蓝 + 金边）一致**？
- [ ] 模型有没有**多画了别的件**（件级 prompt 必须 `ONLY...NOTHING ELSE`）？
- [ ] 面板/按钮是否**能 9-slice**（角固定、中段可平铺/拉伸）？按钮够不够 **compact**、有没有夸张角花/居中高光？
- [ ] 血条/蓝条**填充能否按百分比裁剪**？
- [ ] 范围格是否**无厚边框、半透明、可平铺**？
- [ ] 背景干净品红、便于抠图？发光件记得**软抠**。
- [ ] **文字区留空**？有没有烤进 HP/MP 字母？
- [ ] 有没有混进**水印/星标/签名**（Gemini 常在右下角加星标）？
- [ ] 放进 Unity 像素相机后边缘**锐利无糊边**？

---

## 7. 一致性铁律

- **先出 §1 定调图，再走 §2 逐件**；逐件时**永远把定调图当参考图/init 喂进去**，比纯文字稳得多（尤其 Gemini「Nano Banana」贴参考图效果好）。
- 件级 prompt **必带 `ONLY ... NOTHING ELSE` + `Do NOT draw ... kit`**，否则模型重画整套。
- 按钮 = **compact / thin gold edge / 无大角花 / 无长横幅形 / 无居中高光**；范围格 = **无边框 / 半透明 / 可平铺**。
- 想换主色/质感就**整张定调图重出**，不要混搭单件。
- 精度死磕不动就**转买现成像素 UI 包**，UI 不是本作卖点。
- **模型选择（2026-06-16 验证）**：UI 主力用 **Gemini「Nano Banana」**——扁平、干净、深蓝金边稳。**GPT-Image 不如它**：爱烤乱码假字（"Hover"/"Pressed Button"/"Unft Infe Panel"）、偏 3D 塑料光泽、范围格仍出 4×4 带框块。GPT 的 UI 产出留作参考，不进生产。
- **纯几何 + 真 alpha 的件（范围格/选格框）一律脚本生成**，不喂 AI（见 §2.5）。
```