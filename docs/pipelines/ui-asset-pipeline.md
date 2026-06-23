# UI 资产 Pipeline · 《幻世纪》FantacyCentry

> **这是什么**：把「一句 prompt」变成「Unity 里可用的 UI 资产」的标准工序（SOP）。
> **适用范围**：所有 **UI / HUD 装饰件** —— 面板金框、回合横幅、按钮框、命令图标、血条框、名牌等**硬边几何**件。
> **不适用**：角色立绘 / 头像 → 走 [`portrait-asset-pipeline.md`](./portrait-asset-pipeline.md)（另一条，抠图方式完全不同）。
> **配套**：prompt 源在 [`docs/prompts/ui-prompts.md`](../prompts/ui-prompts.md) §8（HD 非像素路线）。
>
> **开新 session 只需读这一篇**：照下面的目录约定和工序走即可，不用翻 process log。

---

## 0. 一句话链路

```
docs/prompts/ui-prompts.md   ← prompt 源（§8 HD 路线）
        │  GPT-Image API  ⚠️ 收费，调用前必须先跟用户确认
        ▼
art_undecided/ui/<件>/       ← ① 原始产出（待审）
        │  用户审核 ✔
        ▼
art/ui/<件>/                 ← ② 通过的原始件（master 底本）
        │  （若需剪裁/抠图/拼接）
        ▼
art/ui/<件>/edited/          ← ③ 处理后成品（master 底本）
        │  拷贝一份
        ▼
Assets/Art/UI/<复数名>/      ← ④ Unity 实际导入的副本
```

---

## 1. 黄金铁律（先记这三条）

1. **生成走 GPT-Image，原生透明，不事后抠。**
   UI 是硬边几何（利落直边 + 内部镂空），必须在**生成阶段**就用 `background="transparent"` 出真 alpha。
   **不要**用 rembg（语义分割会把利落直边糊掉、误判镂空）——那是立绘 pipeline 的工具。
   **不走像素 UI**（旧 §1–§7 像素路线已废弃，老 pixel 件已删）。

2. **`art/` 是 master，`Assets/Art/UI/` 是副本。**
   Unity 只能从 `Assets/` 导入。所以**导入 Unity 的那个文件，底本必须在 `art/ui/<件>/` 或 `art/ui/<件>/edited/`**，再**拷一份**进 `Assets/Art/UI/<复数名>/`。两边都有，`art/` 永远是真源。

3. **GPT-Image API = 真金白银，每次调用前先跟用户确认。**
   `scripts/gpt_transparent_image_generation.py` 的每次 generate / `--ref` 都是付费调用（~$0.25/张 high）。本地处理（剪裁、抠图、拷贝、改导入）随便做，**只有发 API 这一步停下来确认**。

---

## 2. 五步工序

| 步 | 动作 | 位置 | 谁做 |
|---|---|---|---|
| **① 生成** | 用 §8 prompt 调 GPT-Image API 出透明 PNG | → `art_undecided/ui/<件>/` | Agent（**先确认**） |
| **② 审核** | 看品质：透明干净？镂空对？能 9-slice？ | 看 `art_undecided/ui/<件>/` | **用户** |
| **③ 入库** | 通过的原始件移进 master 区 | → `art/ui/<件>/` | Agent |
| **④ 处理**（按需） | 剪裁 / 切多态 / 量 9-slice border / 拼接 | → `art/ui/<件>/edited/` | Agent |
| **⑤ 导入** | 把 ③ 或 ④ 的成品**拷贝**进 Unity | → `Assets/Art/UI/<复数名>/` | Agent |

> **不需要处理时**：跳过 ④，直接把 `art/ui/<件>/` 里的原始件拷进 `Assets/`。
> **需要处理时**：成品落 `art/ui/<件>/edited/`，导入的是 edited 里的。
> 无论哪种，**`art/` 里都留着将被导入的那个文件**（铁律 2）。

---

## 3. 目录约定（照抄）

```
docs/prompts/ui-prompts.md          prompt 源（§8）
art_undecided/ui/<件>/              ① GPT-Image 原始产出（顶层，与 art/ 并排，待审）
art/ui/<件>/                        ② 通过的原始件（master）
art/ui/<件>/edited/                 ③ 处理后成品（master）
Assets/Art/UI/<复数名>/             ④ Unity 导入副本
```

**`<件>`（art 侧，单数） ↔ `<复数名>`（Assets 侧，Unity 现状）映射：**

| 件 `art/ui/<件>/` | Unity `Assets/Art/UI/<复数名>/` |
|---|---|
| `panel/` | `panels/` |
| `banner/` | `banners/` |
| `button/` | `buttons/` |
| `icon/` | `icons/` |
| `bar/` | `bars/` |
| `nameplate/` | `nameplates/` |

> HD 平滑件在 Unity 侧也可继续用现有 `Assets/Art/UI/hd/`（Bilinear + mipmap 导入）——按 `PixelArtImportPostprocessor.cs` 的 hd 规则走。
> 纯几何 + 真 alpha 件（范围格 `range/`）仍**脚本生成**，不走本 pipeline（见 ui-prompts §2.5）。

---

## 4. 生成步骤细节（GPT-Image）

- **脚本**：`scripts/gpt_transparent_image_generation.py`，默认 `model="gpt-image-1"`、`background="transparent"`、`quality="high"`。
- **prompt**：从 `docs/prompts/ui-prompts.md` §8 **逐字复制**对应件的 prompt（§8.2 面板 / §8.3 横幅 / §8.4 按钮），**不要凭记忆改写**。
- **风格统一**：先出 §8.2 面板金框当**锚件**，满意后用 `--ref <锚件>` 出横幅/按钮，风格自动一致。
- **输出**：`--out art_undecided/ui/<件>/<件名>_<时间戳>.png`。
- ⚠️ **调用前停下来跟用户确认**（每次 generate 或 `--ref` 都是付费）。

---

## 5. 临时脚本规范

- 处理过程中（剪裁、量 border、拼对比图等）可**临时写内联 python**或临时脚本，随手跑随手删。
- 若某段处理**值得复用**（会反复用到），**先问用户**，同意后再正式加进 `scripts/`（带 docstring + usage）。
- **不要把一次性脚本留在 `scripts/` 里积灰**——要么提炼成复用件，要么用完删掉。

---

## 5b. 换色 / 圆角 / 中心填充原则（重要，踩坑总结）

### 圆角 panel 的中心填充：烤进 PNG，不要用单独矩形层

- panel 是**圆角**。若用一层**矩形** uGUI 色块当背景，永远贴不合圆角：铺满 bbox → 四角凸出到金边圆弧外（漏色）；缩进安全矩形 → 圆角附近盖不到（透明缝）。矩形 ≠ 圆角，几何死结。
- **正解：中心实心直接做进 PNG**（panel 自带圆角填充），`panelSolidCenter=true` 时 `BattleHud` 跳过 NavyFill 层。圆角由 PNG 的 alpha 保证，完美贴合。
- 只有**直角**矩形件才可以用单独矩形色层。

### `Image.color` 是「乘法」不是「替换」——所以中心要做成纯白

- uGUI 渲染：`最终色 = PNG像素 × Image.color`（逐通道相乘）。相乘只会**变暗**，永不变亮（`a×b ≤ min(a,b)`）。
- **白底 (1,1,1)** × 任意色 = 那个色本身 → **能染成任意鲜艳色**（看起来像“替换”）。
- **深色底（navy 0.09,0.13,0.20）** × 红(1,0,0) = (0.09,0,0) 近黑暗红 → **只能压更暗 / 微调**，染不出比自身亮或更鲜艳的色。
- **结论**：要换色自由（navy→紫→红随意）→ PNG 中心做**纯白**，用 `Image.color` 染；只要 navy 一种顶多压暗 → 直接烤 navy 也行。
- （真正的“替换颜色”需要 shader 把底色当 mask，uGUI 默认 Image 做不到，只有乘法 tint。）

### 纯白靠 Python 归一化，别指望 AI

- AI **保证不了**均匀纯白——它一定带细微渐变/高光/明暗。拿不均匀的白去 tint，染出来也不均匀。
- **正解：AI 出形 + 金边 + 大致实心中心（填什么色无所谓）→ Python 后处理把“明确属于内部”的像素 RGB 强制刷成纯白 (255,255,255)，保留 alpha。**
  - 纯白由代码保证，100% 均匀，AI 抖动无所谓；
  - 圆角仍来自 PNG 自带 alpha，完美；
  - 金边与中心交界留一条抗锯齿过渡带**不刷**（只刷明确内部像素），别破坏金边软边。
- **内部判定按颜色、不按连通**：用 flood-fill 从中心填白会被角花卷草挡住、进不去被包围的小孔（同抠图死穴）。改成**逐像素判**「alpha 够高 **且** 颜色接近 navy」就刷白——这样角花的透明孔（alpha 低，跳过）、金色实体（非 navy，跳过）都不误伤，被角花包围的 navy 也照刷。刷白区再**向内收缩 1–2px (erode)** 让出金边交界过渡带，避免白边。
- 这一步若定为常用，提炼成复用脚本（见 §5 规范，先问用户）。

### AI 透明输出带噪点 → 出图收尾做 alpha 阈值清零

- GPT-Image 的 `background="transparent"` 大面积是**严格 alpha=0**，但透明区总散着 ~1–2% 的 **alpha 1–7 极淡噪点**（肉眼也呈棋盘格，但不是严格 0）。「看图软件显示透明格 ≠ 每个像素都是 0」。
- **出图后标准收尾：`alpha < 阈值(≈8) → alpha = 0`**，把近透明噪点压成严格透明。当 init/`--ref` 用无所谓，当**生产资产**必须清。
- 记忆口径：alpha=0 全透明、255 实心、中间是半透明；判“实心内部”看高 alpha，判“透明背景”看 alpha≈0。

---

## 6. 审核 checklist（用户把关，对应 ui-prompts §8.6）

- [ ] **真透明**：背景全透，无残底、无品红边、无黑 halo？
- [ ] **平滑非像素**：抗锯齿、矢量感卷草，不是 pixel art？
- [ ] **中心空 hollow**（面板/按钮），没烤文字/数字/分隔线/头像框/血条？
- [ ] **扁平打光**，无 3D 塑料高光 / 厚重投影？
- [ ] 面板/按钮：**四角金花纹固定、中段可拉伸**（能 9-slice）？
- [ ] 横幅：**端帽定宽 + 中缎带纯色可拉**？
- [ ] 无水印 / 星标 / 签名？

---

## 7. 为什么这样定（背景，给未来的自己）

- **为什么不用 rembg 抠 UI**：rembg 是语义分割（软边、进发缝），擅长有机体；UI 要利落硬边和干净内部镂空，软分割反而糊边、误判镂空。**镂空要在生成阶段就透明**，事后抠（无论 rembg 还是 flood-fill）都治不了被主体包围的内部孤岛。
- **为什么不走像素 UI**：战斗 UX 已改「uGUI 掌布局 + 文字 + 血条，美术只做 HD 装饰底」，不需要整套像素 kit，只要几张 HD 平滑金框。老 pixel 件已删。
- **为什么 art/ 和 Assets/ 都留一份**：Unity 只认 `Assets/`，但 `Assets/` 里混着 .meta、会被导入设置改写；`art/` 留干净底本，便于重导、回滚、换皮。
