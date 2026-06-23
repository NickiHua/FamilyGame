# 《幻世纪》UI 出图 Prompt 集

> **用途**：给 GPT-Image / Gemini「Nano Banana」出像素风 UI 件，再脚本抠图 + Unity 9-slice + UI Toolkit 接线。
> **配套 spec**：`docs/specs/2026-06-15-fantacy-centry-demo-to-steam-design.md` §7.5（UI 出图规范）。
> **状态**：本文件经 2026-06-16 实战出图迭代，已固化「定调图 → 逐件精修」工作流与全部踩坑修正。
>
> ⚠️ **两条并行路线，别混用：**
> - **§1–§7 = 像素 UI 路线（旧）**：refined pixel art、Point 滤波。范围格仍走这里（脚本生成）。
> - **§8 = HD 非像素装饰路线（新，2026-06-20）**：战斗 UX 改走「uGUI 掌布局 + 美术只做 HD 装饰底」后的主路线。面板金框 / 横幅端帽 / 按钮金框走这里，**平滑非像素**、Bilinear 导入。**现在的战斗面板用 §8。**

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

---

## 8. HD 非像素装饰路线（2026-06-20 新增 · 战斗 UX 主路线）

> **为什么有这一节**：战斗 UX 已改为「**uGUI 掌控全部布局 + 文字 + 血条，美术只做装饰底**」（美术与布局解耦）。所以**不需要一整套像素 kit**，只需要 3–4 张 **HD 平滑金框**垫在 uGUI 背后。像素路线（§1–§7）的「先出整套定调图」在这里**不适用**。
>
> **和 §1–§7 的关键区别**：
> | | §1–§7 像素路线 | §8 HD 路线 |
> |---|---|---|
> | 质感 | refined **pixel art**、硬边、无抗锯齿 | **平滑 HD**、抗锯齿、矢量感卷草纹 |
> | 导入 | Point 滤波、无 mipmap | **Bilinear + mipmap**（放大不糊）→ 放 `Assets/Art/UI/hd/` |
> | 用途 | 范围格（脚本）、旧像素件 | 面板金框 / 横幅端帽 / 按钮金框 |
> | 文字/数字 | 留空 | 留空（同样不烤字） |

### 8.0 工作流（轻量套件 = 1 张锚件）

```
① 先只出「① 面板金框」这一张 HD 锚件，定死风格（金色厚度 / 卷草繁简 / 高光程度）
② 满意后，把这张当参考图喂回模型，出 ②横幅端帽 / ③按钮金框 → 风格自动统一
③ Python strip_magenta.py 抠品红底 → 透明 PNG → 放 Assets/Art/UI/hd/
④ Unity 9-slice（角固定、中段拉伸）；横幅走「端帽固定 + 中缎带拉伸」结构
```

> **模型**：HD 平滑卷草纹 **GPT-Image 不弱**（旧结论「GPT 不适合 UI」只针对像素件）。Gemini 也可。两者都出，挑**扁平、无塑料立体高光**的那版。

### 8.1 全局后缀（HD 路线专用 · 追加到每条末尾）

```
High-resolution SMOOTH digital painting, clean anti-aliased vector-like rendering, crisp smooth
gradients, ~2048px. This is a UI decoration FRAME ONLY — empty hollow center, NO text, NO letters,
NO numbers, NO icons, NO characters, NO portrait. Flat even lighting, NO 3D plastic gloss, NO heavy
drop shadow, NOT pixel art, no jagged or chunky pixels, no watermark, no signature.
Flat solid magenta (#FF00FF) background.
```

### 8.2 ① 面板金框（锚件 · 先出这张）✅ 先出

> 信息面板背景，9-slice 友好。对应 uGUI 面板 W≈780 H≈200（约 4:1 宽横条）。
>
> **2026-06-22 改版（关键）**：旧版角花太 heavy、太醒目。新方向参考梦战 `art/uiconcept/charpanel.png` + 自家认可的细金边按钮：**细金边 + 四角小装饰 + navy 实心中心**，金色不抢戏。
> - **用 `--ref art/ui/button/button_normal_long.png` 当风格锚**（那张已是 4:1 细金边，模型不会被方形带偏）。
> - **中心出 navy 实心**（不 hollow）：免「navy 矩形层盖不住圆角」漏色，免漏绿。
> - **换色 / 纯白底 / 凹槽图标区 / alpha 清噪 一律不写进 prompt** —— 全是下游 Python+uGUI 的活（见 `docs/pipelines/ui-asset-pipeline.md` §5b）。prompt 只管「细金边 + navy 实心 + 简角花 + 能切片」。
> - 4:1 是期望，**最终任意比例靠 9-slice**，不强求出图精确。

```
Using the attached image as the exact style reference for the gold border (same THIN delicate gold
line, same SMALL simple corner flourishes — do NOT make the gold thicker or more ornate), generate
ONE single wide horizontal UI panel frame for a Japanese fantasy tactical RPG, isolated and
centered, and NOTHING ELSE, roughly 4:1 (wide) aspect with rounded corners. The interior is a
SOLID, FLAT, EVENLY filled deep NAVY-BLUE (completely opaque, NOT hollow, NOT transparent, NOT a
window). The thin gold border runs cleanly around all four sides with ONE small simple gold
flourish at each of the four corners, minimal and understated. The four straight edges are plain
thin gold lines so it can be 9-sliced (corners fixed, navy center and edges stretch). The wide
middle is plain flat navy with NO ornament, so engine text sits on top. Lightweight and clean —
the gold must NOT dominate.
High-resolution SMOOTH digital painting, clean anti-aliased vector-like rendering, crisp smooth
gradients. Flat even lighting, NO 3D plastic gloss, NO heavy drop shadow, NOT pixel art, no jagged
or chunky pixels. NO text, NO letters, NO numbers, NO icons, NO characters, NO portrait, no
watermark, no signature. The background MUST be fully transparent — render ONLY the panel shape on
a transparent background, nothing else.
```

> 跑法（**调 API 前必确认**）：
> ```
> .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py panel ^
>     --ref art/ui/button/button_normal_long.png
> ```
> 输出落 `art_undecided/ui/panel/`。

> <details><summary>旧版 prompt（baroque 繁角花，已弃用，存档）</summary>
>
> ```
> Generate ONE single ornate horizontal UI panel frame for a Japanese fantasy tactical RPG, isolated
> and centered, and NOTHING ELSE. A wide rounded rectangular plate, roughly 4:1 (wide) aspect.
> Deep translucent navy-blue interior that is FLAT and EMPTY (hollow), framed by an elegant SMOOTH
> gold filigree border with refined baroque scrollwork — four distinct ornate gold CORNERS and four
> clean straight EDGES, so it can be 9-sliced (corners stay fixed, the navy center and edges stretch).
> Subtle inner gold pinstripe. Elegant, restrained, not too busy. NO inner dividers, NO portrait box,
> NO bars.
> [§8.1 全局后缀]
> ```
> </details>

### 8.3 ② 回合横幅端帽（喂 panel_info_frame 当参考）✅ 完整可粘贴

> 结构：左右**定宽简组金角端帽** + 中间**实心纯色缎带**可拉伸。
> **两个踩坑修正（第一批翻车）：**
> 1. **端帽要简**。上一批叫“以面板金框为参考”，但金框角花本来就繁，模型照着堆了一堃巫克力卷草 → 太复杂。banner 端帽应比面板**更简**，只要一个小金角点缀。
> 2. **中心实心，不要镶空**。banner 是整屏飘过的临时遮罩，文字直接叠上面——中心该是**实心深 navy**（实心反而好扣，只扣品红边；镶空才难扣）。**不**要 panel 那种 hollow。
> 尺寸对标现有像素横幅 ≈ 1315×276（约 4.8:1）。蓝（player）/ 红（enemy）各一。可不附参考图（避免被金框角花带繁），文字描述里已锁细金。
>
> **蓝（PLAYER PHASE）：**

```
Generate ONE long horizontal ornamental phase BANNER for a Japanese fantasy tactical RPG and
NOTHING ELSE, roughly 4.8:1 (very wide) aspect, isolated and centered. The whole banner is a SOLID
filled deep NAVY-BLUE horizontal bar (the center is SOLID navy, completely filled, NOT hollow, NOT
transparent, NOT a window). On the far left and far right place a SMALL, SIMPLE, restrained gold
corner accent each — just a single thin elegant gold flourish, MINIMAL scrollwork, NOT a big ornate
baroque block, NOT busy, NOT dense filigree. A thin clean gold pinstripe runs along the top and
bottom edges of the whole bar. The wide middle is plain, flat, even solid navy with NO ornament, so
engine text can sit on top of it. Refined, elegant, mostly empty, understated.
High-resolution SMOOTH digital painting, clean anti-aliased vector-like rendering, crisp smooth
gradients, ~2048px. Flat even lighting, NO 3D plastic gloss, NO heavy drop shadow, NOT pixel art,
no jagged pixels. NO text, NO letters, NO numbers, NO icons, NO characters, NO portrait, no
watermark, no signature. Flat solid magenta (#FF00FF) background only OUTSIDE the banner shape.
```

> **红（ENEMY PHASE）：** 同上，只把主体颜色换成深红。

```
Generate ONE long horizontal ornamental phase BANNER for a Japanese fantasy tactical RPG and
NOTHING ELSE, roughly 4.8:1 (very wide) aspect, isolated and centered. The whole banner is a SOLID
filled deep CRIMSON-RED horizontal bar (the center is SOLID red, completely filled, NOT hollow, NOT
transparent, NOT a window). On the far left and far right place a SMALL, SIMPLE, restrained gold
corner accent each — just a single thin elegant gold flourish, MINIMAL scrollwork, NOT a big ornate
baroque block, NOT busy, NOT dense filigree. A thin clean gold pinstripe runs along the top and
bottom edges of the whole bar. The wide middle is plain, flat, even solid red with NO ornament, so
engine text can sit on top of it. Refined, elegant, mostly empty, understated.
High-resolution SMOOTH digital painting, clean anti-aliased vector-like rendering, crisp smooth
gradients, ~2048px. Flat even lighting, NO 3D plastic gloss, NO heavy drop shadow, NOT pixel art,
no jagged pixels. NO text, NO letters, NO numbers, NO icons, NO characters, NO portrait, no
watermark, no signature. Flat solid magenta (#FF00FF) background only OUTSIDE the banner shape.
```

### 8.4 ③ 按钮金框（喂 panel_info_frame 当参考）✅ 完整可粘贴

> 只出**框**（按钮背景底），9-slice。框内的攻击/防御/移动**图标 + 文字由 uGUI 实时叠**，绝不烤进框（见 §8.7）。
> 风格统一**细金**。一张图里横排出 **3 个状态**：Normal / Hover / Pressed，方便一次抠三张。
> 尺寸约 **3:1**（宽命令按钮，截图里左下竖排那种）；图标会放在框左侧、文字在右侧，所以中心必须空。

```
Using the attached gold-frame image as the exact style reference, generate THREE small COMPACT
command BUTTON frames in a horizontal row and NOTHING ELSE, each roughly 3:1 (wide) aspect, on the
same sheet, clearly separated. All three share the SAME thin, refined, smooth GOLD edge (delicate
thin gold line with small simple corner accents, NOT thick metallic, NOT large flourishes) around a
rounded NAVY-BLUE rectangle with a flat EMPTY hollow center so it can be 9-sliced (thin fixed gold
caps on all four sides, plain stretchable navy middle). The three states differ ONLY by the navy
fill and gold brightness, left to right:
1) NORMAL — deep flat navy, soft thin gold edge.
2) HOVER — slightly brighter navy with a faint inner gold glow, brighter gold edge.
3) PRESSED — darker, slightly inset/recessed navy, dim gold edge.
Keep them small and simple, no long banner shape, no centered highlight, no ornament in the middle.
High-resolution SMOOTH digital painting, clean anti-aliased vector-like rendering, crisp smooth
gradients, ~2048px. These are UI decoration FRAMES ONLY — empty hollow centers, NO text, NO letters,
NO numbers, NO icons, NO characters, NO portrait. Flat even lighting, NO 3D plastic gloss, NO heavy
drop shadow, NOT pixel art, no jagged or chunky pixels, no watermark, no signature.
Flat solid magenta (#FF00FF) background.
```

> **抠图后切三张**：strip_magenta.py 去品红 → 按行切成 `button_normal.png` / `button_hover.png` / `button_pressed.png` → 放 `Assets/Art/UI/hd/`（已接线，见 BattleHud 三态槽）。

### 8.5 出图后处理（HD 路线）

| 步骤 | 工具 | 备注 |
|---|---|---|
| 抠品红底 | `scripts/ui/strip_magenta.py` | 同旧管线；HD 件边缘软、容差抠 |
| 放置 | 手动 | → `Assets/Art/UI/hd/`（**新目录**，走 Bilinear+mipmap 导入，不与像素件混） |
| 导入 | `PixelArtImportPostprocessor.cs` | 需加 `Assets/Art/UI/hd/` → Bilinear + mipmap + 压缩允许 + 9-slice border |
| 9-slice | Unity Sprite Editor 或脚本 spriteBorder | 面板/按钮角固定；横幅走端帽固定+中缎带 |
| 接线 | uGUI（已就绪） | 文字/数字/血条全由 BattleHud.cs 渲染，绝不烤进图 |

### 8.6 HD 路线挑图 checklist

- [ ] **平滑无像素块**（抗锯齿、矢量感），不是 pixel art？
- [ ] **中心空 hollow**，没烤任何文字/数字/分隔线/头像框/血条？
- [ ] **扁平打光**，没有 3D 塑料高光 / 厚重投影？
- [ ] 面板/按钮：**四角金花纹固定、中段可拉伸**（能 9-slice）？
- [ ] 横幅：**端帽定宽 + 中缎带纯色可拉**？
- [ ] 品红底干净、无水印/星标？
- **纯几何 + 真 alpha 的件（范围格/选格框）一律脚本生成**，不喂 AI（见 §2.5）。
```

### 8.7 命令系统三件（2026-06-22 · 透明底脚本 preset）

> 这三条已写进 `scripts/gpt_transparent_image_generation.py` 的 preset，**透明底直出**（不走品红抠图）。
> **调 API 前必确认**。输出落 `art_undecided/ui/<type>/`，审核后才进 `art/ui/<type>/` + `Assets`。
> 设计背景：取消独立的 WAIT 指令框 —— **待机是「角色指令面板」里的一个 button**。点角色 → 弹角色指令面板（复用主 `panel.png` 9-slice）→ 里面排 6 个小动作按钮（§8.7c）。END TURN / 角色指令行的长条按钮 = §8.7a 的素金边 button。

**a) `button` —— 素金边按钮三态（改版：去掉角花）**

> 旧 §8.4 的「带小角花」按钮**作废**，改成**纯一条细金边**圆角矩形，中心 hollow（引擎叠图标/文字）。一张图横排出 Normal / Hover / Pressed。复用于：角色指令面板的每行按钮、END TURN。
> 跑法：
> ```
> .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py button
> ```
> 可选 `--ref art/ui/button/button_normal_long.png` 当细金边锚（让模型别加料）。

**b) `select-frame` —— 选中格金角框（HD 版）**

> 替换老像素 `art/ui/range/select_frame.png`：四角金括号 + 中间**全镂空透明**，盖单格。
> **要不要参考图？要 —— 必带 `--ref art/ui/range/select_frame.png`。** 理由：这件的灵魂就是「四角括号 + 中空」布局，纯文字描述模型容易画成整圈实边或把中心填上；老像素图正好把「括号位置 + 中空」摆给它看，HD 重绘只换质感。（注意区别 §2.5：范围**填充格**才不喂 AI 走脚本；这件是**装饰金角**，有美术内容，适合 AI。）
> 跑法：
> ```
> .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py select-frame ^
>     --ref art/ui/range/select_frame.png
> ```

**c) `action-icons` —— 6 个小动作按钮（金边 + 实心 + 图标）**

> ⚠️ **已作废（2026-06-22），改用 §8.8 的 Gemini 12 图标整图。** 下面这条 GPT 方案因中心偏置切图/少画 + 透明 PNG 难抠被弃，保留仅作记录。

> 一排 6 个小方按钮：金边 + 小角花（保留花纹，因为只有一格大、不抢镜）+ **实心 navy 底（不镂空）** + 中心烤一个金色动作符号。顺序：攻击(剑) / 技能(星) / 魔法(法杖) / 移动(靴) / 待机(沙漏) / 道具(药瓶)。
> **要不要参考图？我的建议：不强需，但想让 6 个金角花和家族统一，可选喂 `--ref art/ui/range/select_frame.png`（你喜欢它的角花）当风格锚 —— 模型只抄金角风，符号照描述自由发挥。** 不喂也行,描述已锁死风格;先不喂跑一版,角花不够再补 `--ref`。
> 注意:这件与其它 preset 不同,**故意保留内部符号**(用 `_ICON_TAIL`,只禁文字/数字,不禁 icon)。
> 跑法：
> ```
> .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py action-icons
> # 想统一角花再加： --ref art/ui/range/select_frame.png
> ```

### 8.8 命令图标：Gemini 12 图标整图（2026-06-22 · ✅ 最终采用，取代 §8.7c）

> **§8.7c 的 GPT `action-icons` 方案作废。** GPT-Image 一排画多个图标有**强中心偏置**：会切掉最左边、或少画（要 7 出 6），而且它的「透明 PNG」是**羽化渐变 alpha**，边界糊、难抠。
>
> **最终采用 Gemini**：让它在**不透明纯黑底**上画一张 **2×6 网格、12 个图标**的整图 —— **硬边 + 几乎无外发光**，反而比 GPT 的现成透明 PNG **好抠得多**。抠图走 `scripts/cut_gemini_icons.py`（从「框内内沿种子 + 外边框」flood-fill 黑底 → 透明，金框/物体保留，物体内部暗部不误删）。
>
> **关键认知**：**「好抠的资产 = 干净硬边 + 发光分离」**。AI 在纯黑上画硬边图标，比直接出羽化透明 PNG 可控。`erode` 是抠图的解药、不是现象名；框外那圈淡色叫 **Outer Glow / Bloom**，专业管线把它单独成层、本体保持干净剪影。

**实际用的 Gemini prompt（出当前 12 图标，已验证好抠）：**

```
A game asset sprite sheet of 12 modern HD fantasy UI icons, arranged in a perfect 2x6 grid layout.

Each of the 12 icons features an identical square shape and a matching polished golden metallic border with minimalist gold ornaments on the four corners.

The inside contents of the 12 borders are: 1. empty slot, 2. silver sword , 3. two silver swords cross, 4. ancient spellbook, 5. sturdy knight shield, 6. hourglass, 7. red health potion, 8. leather boot, 9. golden silhouette of a demon with red eyes, 10. A silver ring, 11. golden silhouette of a human, 12. aggressive werewolf head. 2D vector art, clean sharp details, game graphic design, solid flat pitch black background, completely isolated, no shadows, no background glow, no text, no typography
```

**为什么这条 prompt 好用（抄它的套路）：**
- `solid flat pitch black background` + `no shadows, no background glow` —— **逼出硬边、压掉外发光** → 好抠。
- `identical square shape` + `matching ... border` + `minimalist gold ornaments on the four corners` —— 12 个框**统一**（角花对称、不抢镜）。空框（第 1 格）= **模板母版** `icon_frame_empty`，以后新图标贴它即可。
- `2x6 grid` —— 一张出全套；网格规整，`cut_gemini_icons.py` 用「金量投影」量网格再逐格抠。（Gemini 偶尔多画一行重复，取前两行即可。）
- 内容逐格点名（剑/双剑/书/盾/沙漏/药水/靴/角/戒指/人/狼）—— 内容明确，风格交给前半段统一描述。

> **落地**：`cut_gemini_icons.py` 抠 → 审 → `install_icons.py` 进 `art/ui/icon/` + `Assets/Art/UI/icons/`（Bilinear，旧名覆盖保留 GUID）。新增图标可直接在这张整图里加格重出、或把单个 glyph 居中贴进 `icon_frame_empty`。
