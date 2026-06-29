# Tile 资产 Pipeline · 《幻世纪》FantacyCentry

> **这是什么**：把「一句 prompt」变成「Unity 里可用的**像素地面 tile**」的标准工序(SOP)。
> **适用范围**：所有**宽容型地面 base tile** —— 草 / 路 / 泥 / 水 / 桥面 等可平铺地面纹理。
> **不适用**：UI 装饰件 → 走 [`ui-asset-pipeline.md`](./ui-asset-pipeline.md)；立绘/头像 → 走 portrait pipeline；**边界过渡 / 悬崖墙 autotile** 是另一条(后期,见文末)。
> **配套**：prompt 源在 [`docs/prompts/tile-prompts.md`](../prompts/tile-prompts.md)。
> **来由**：2026-06-26 的 tile 出图实验矩阵(见 `docs/developing_process/2026-06-26_process.md` §六)。
>
> **开新 session 只需读这一篇**：照下面的目录约定和工序走即可。

---

## 0. 一句话链路

```
docs/prompts/tile-prompts.md            ← prompt 源（调 API 前先更新此文件）
        │  GPT-Image API  ⚠️ 收费，调用前必须先跟用户确认
        ▼
art_undecided/tiles/<size>_<quality>/<kind>/   ← ① 原始 1024 产出（待审）
        │  Python 下采样 + 拼九宫格
        ├─ <size>_<quality>/_64/    （下采样到 64 的真 tile）
        └─ <size>_<quality>/_3x3/   （同一 tile 3×3 平铺，看接缝/重复）
        │  Agent 审 → 推荐；用户审 → 结合推荐定稿
        ▼
art/tiles/<kind>/                        ← ② master：
        ├─ <kind>_base.png            （选中那张，64×64）
        └─ <kind>_base_original.png   （对应 1024 原图，留作 init/重导底本）
        │  （可选）Aseprite 精修
        │  （可选）以 _original 为 init 出 variant（回 ① 走一遍）
        ▼
Assets/Art/Tiles/<kind>/                 ← ③ Unity 实际导入副本（Point / PPU=64）
```

---

## 1. 黄金铁律（先记这四条）

1. **prompt 里的「尺寸词」是「画得多 chunky」的杠杆，不是最终 tile 尺寸。**
   实测：**`chunky 32x32` 的 prompt 比 `64x64` 的更有像素感**(64 偏细、偏 HD)；颗粒/整洁度 **high > medium > low**。
   **标准做法 = `32-prompt` + `quality=high` + Python 下采样到 64。** 最终 tile **统一 64×64**(配 128 sprite 正好 2:1)。

2. **`art/tiles/` 是 master，`Assets/Art/Tiles/` 是副本。**
   Unity 只能从 `Assets/` 导入。master 同时存**两份**：`<kind>_base.png`(64,实际用)+ `<kind>_base_original.png`(1024,留作 variant 的 init / 将来重导)。

3. **GPT-Image API = 真金白银，每次调用前先跟用户确认。**
   每次 generate / `--ref` 都是付费(low≈1 分、medium 数倍、high≈1–2 角/张)。本地处理(下采样、拼图、量化、无缝、拷贝)随便做，**只有发 API 这一步停下来确认**。

4. **调 API 前先更新 `tile-prompts.md`。**
   让该文件 = 即将调用的真实 prompt(留批次留痕)。**别凭记忆改写 prompt。**

---

## 2. 工序表

| 步 | 动作 | 位置 | 谁做 |
|---|---|---|---|
| **① 生成** | 用 `32-prompt` 调 GPT-Image 出 1024 原图(每种 3 张) | → `art_undecided/tiles/<size>_<quality>/<kind>/` | Agent(**先确认**) |
| **②a 下采样** | Python 缩到 64 | → `…/_64/<kind>_<i>_64.png` | Agent |
| **②b 拼九宫格** | 同 tile 3×3 平铺(×N 放大看像素/接缝) | → `…/_3x3/<kind>_<i>_3x3.png` | Agent |
| **③ Agent 审 + 推荐** | 看像素脆度 / 平铺无缝&重复 / 与邻地形区分 / 整洁度 → 给 Top 推荐 | 看 `_3x3/` | Agent |
| **④ 用户审 + 定稿** | 结合 Agent 推荐拍板每种主力 | | **用户** |
| **⑤ 入 master** | 选中件 → `<kind>_base.png`(64) + 原图 → `<kind>_base_original.png`(1024) | → `art/tiles/<kind>/` | Agent |
| **⑥ 精修**(按需) | Aseprite 量化/修边/去显眼瑕疵/无缝 | 改 `<kind>_base.png` | **用户** |
| **⑦ 变体**(按需) | 以 `<kind>_base_original.png` 为 **init** 出 variant，回 ①~④ 走一遍 | | Agent(**先确认**) |
| **⑧ 导入** | 把 master 的 64 件**拷贝**进 Unity | → `Assets/Art/Tiles/<kind>/` | Agent |

> **⑦ 与 ⑧ 不冲突**：可以先把一张 base 导进 Assets 开用，再回头做变体。

---

## 3. 目录约定（照抄）

```
docs/prompts/tile-prompts.md                    prompt 源（调 API 前更新）
art_undecided/tiles/<size>_<quality>/<kind>/    ① 原始 1024 产出（待审）
art_undecided/tiles/<size>_<quality>/_64/       ②a 下采样 64
art_undecided/tiles/<size>_<quality>/_3x3/      ②b 九宫格预览（看接缝）
art/tiles/<kind>/<kind>_base.png                ② master：选中件 64×64
art/tiles/<kind>/<kind>_base_original.png       ② master：对应 1024 原图
Assets/Art/Tiles/<kind>/                         ③ Unity 导入副本
```

- `<size>` = prompt 里写的尺寸词(`32` / `64`)——**只标 prompt，不代表图的真实尺寸**。
- `<quality>` = `low` / `medium` / `high`(GPT quality)。
- `<kind>` = `grass` / `road` / `dirt` / `water` / `bridge` …
- **标准批次** = `32_high/`（32-prompt + high）。

---

## 4. 生成步骤细节（GPT-Image）

- **脚本**：`scripts/gpt_transparent_image_generation.py custom`，传 `--type tile --background opaque --quality high --size 1024x1024 --n 3 --out art_undecided\tiles\32_high\<kind>\<kind>.png --prompt "..."`。
- **prompt**：从 `tile-prompts.md` **逐字复制**对应地形那条(含 `chunky 32x32`)。
- **背景 opaque**(地面是满幅纹理，不要透明)。
- **速率限制 5 张/min**：要一次跑多批，写**带自动重试(429→等 20s)的临时驱动**(用完即删，见 §5)。
- **下采样统一用 `Image.BOX`**(面积平均，缩 1024→64 干净)；预览九宫格放大用 `Image.NEAREST`(保像素硬边)。
- ⚠️ **调用前停下来跟用户确认**(每次 generate / `--ref` 都付费)。

### 变体(⑦)
- **以 `<kind>_base_original.png`(1024) 为 `--ref` init**，**不要**用 64 的(信息太少、效果差)。
- prompt：`"Same exact pixel-art style, palette and brightness as the reference <kind> tile, but a DIFFERENT arrangement of … Seamless tileable, no anti-aliasing, no blur, no text."`

---

## 5. 临时脚本规范

- 下采样、拼九宫格、批量出图驱动等**临时活**可写内联 python 或临时脚本(`scripts/tiles/_xxx.py`，下划线开头),**随手跑随手删**。
- 若某段处理**值得复用**(下采样+九宫格、无缝化、量化),**先问用户**，同意后再正式加进 `scripts/tiles/`(带 docstring + usage)。
- **不要把一次性脚本留在 `scripts/` 里积灰。**

---

## 6. 审核 checklist（③④ 用，看 `_3x3/`）

- [ ] **像素脆度**：缩 64 后块状/硬边够不够？还是糊？(不够 → high / 后期量化)
- [ ] **平铺无缝**：3×3 有没有**硬接缝线**？(水尤其看**上下**缝)
- [ ] **抗重复**：显眼物(草丛/花/大石)会不会**每 64px 规律重复**？(会 → 选更匀的变体 / 显眼物挪 decal / 靠旋转镜像)
- [ ] **与邻地形区分**：泥 vs 路(更深更红 vs 更亮 tan)？水够蓝？
- [ ] **方向性**：有没有不该有的**斜纹/竖纹**(路最容易出木纹)？
- [ ] **桥**：竖板方向对吗？有没有出**白边框**(框成一格格)？
- [ ] 无文字/水印/签名？

---

## 7. 为什么这样定（背景，给未来的自己）

- **为什么 32-prompt 缩 64**：GPT 不守尺寸、天生 AA，直接出真像素走不通。`32` 的 prompt 让它**画得更 chunky**，再下采样到 64 = **像素味 + 64 细节容量**。prompt 尺寸词和最终 tile 尺寸是**两件事**(解耦)。
- **为什么 high**：颗粒/整洁 high>med>low；base tile 量小(5 种 × 1~2 张)，high 花得起。
- **为什么 art/ 和 Assets/ 都留**：Unity 只认 `Assets/`，但那里混 .meta、会被导入设置改写；`art/` 留干净底本(64 用 + 1024 原图),便于重导、回滚、出变体、换皮。
- **为什么留 1024 原图**：variant 的 init 要信息多的原图(64 太小效果差)；将来想换 32/48/96 尺寸也能从原图重导。
- **为什么不靠 Python 烤整图当游戏画面**：游戏是 Unity 实时铺 tile；Python 渲染只是开发期沙盒(比过渡、验布局)，不进 shipping。
- **为什么不用「大图切块」**(2026-06-28 实测否决)：试过出 1024 大图直接切 64、或缩 512/256 再切。**chunky prompt 能找回像素感、同源变种一致**，但通病是**细节糊**(缩 256 仍糊)且**一个 64 块常含一坨大特征**(一颗大石/一丛大草)→ 铺开**pattern 极明显**。GPT 不按 tile 尺度作画，切块抓到随机尺度细节。**不如 32-prompt 当整张 tile 设计 + 缩 64**。→ 弃。

---

## 6.5 出图后处理（脚本收尾，玩家不手绘）

- **flatten**(`scripts/tiles/flatten_tile.py`)：去 GPT 烤进的右下角渐暗(角落网格)，wrap 模式保持可平铺。**所有地面 tile 都过一遍。**
- **uniformize**(压中频)：把 ~16–32px 的大斑压平、只留细颗粒 → 防大块重复。**仅 road/sand/dirt 这类该匀的用；grass 不用**(会压平草丛)。
- **接缝 = 手工 Aseprite**：Tiled Mode + 克隆/涂**真纹理**过缝；**别用「平均/羽化」式自动补缝**(会留平滑软线)。

---

## 8. 下游(本 pipeline 之外，后期)

- **抗重复层**：摆放随机旋转/镜像 + 平滑宏观明暗层 + 非对齐 decal(草丛/花/石)。**别用逐格亮度抖动**(出方块棋盘)。
- **水动画**：Unity **Animated Tile + 2~4 帧**(高光逐帧挪)或调色板循环；shader 偏 HD 暂不上。
- **边界过渡**：dual-grid(16 角查表) —— 搬 Unity 后期做，先看「平 tile + decal」够不够。
- **悬崖立面**：单独的**方向性墙 autotile**(直墙段 + 内外拐角)，只在朝镜头的落差边渲染；**不进 dual-grid**。
- **桥=结构件**：单格桥用一张(上下都带横梁)；**多格宽桥**拆纵向 3 件 **cap/mid/cap**(top=上梁+板 / mid=纯板可竖向平铺 / bottom=板+下梁),横向所有件照旧左右接。
- **Unity 摆图**：TerrainTile(ScriptableTile，带 walkable/moveCost) + Tile Palette + MapExporter(导出 `demo_map.json`)，概念图当半透明描图底。
