# 深渊放置姬 · 角色模组 Skill / Idle Abyss Princesses Hero Mod Skill

[中文](#中文) · [English](#english)

---

## 中文

一个给 AI 编程助手（Claude Code 等）用的 **skill**：带着玩家把一个角色做成《深渊放置姬》能玩的**角色模组**，并准备好上传 Steam 创意工坊。

助手会一步步带你完成：
- **设计**：身份、资源机制、6 个技能、3 个流派（每个流派一套 7 件套装 + 2 件流派传奇）、王庭装备、台词。技能怎么分工、官方技能的冷却和伤害范围、传奇效果的 7 种常见写法、2/4/6 件套怎么配，都有带代码的说明和一个在游戏里测过的示例角色「星缀」
- **技能特效**：游戏自带的特效种类、自己写特效、在游戏外逐帧预览（帧总览图 + GIF，可以和官方技能并排对比）；可以用 [pixelfx](https://github.com/patch-gg/pixelfx) 的像素特效
- **美术**：立绘、表情差分、Q 版战斗小人（5 种动作帧 + 角色页纸娃娃）、16×16 专属图标、工坊预览图
- **代码**：`hero.js`（技能、天赋、套装、传奇、王庭）、五种语言翻译
- **变身和位移**（游戏 3.1.1 起）：像龙姬变龙那样的变身角色（借龙姬的龙换颜色，或者自己画一个像素形态），冲刺、突进、闪现
- **测试与平衡**：用游戏里的「角色实验室」把每个流派调到「标准」
- **可选**：通过玩家自己的 AI 服务和角色聊天（游戏 3.0.2 起的 `IAP.ai`）
- **上传**：用游戏内置的上传工具发到创意工坊

**生图模型由你自己选**：自己画 / 约稿，或者 OpenAI 兼容接口（gpt-image 等）、NovelAI、本地 Stable Diffusion WebUI。密钥只放在你电脑的环境变量里，不会发进聊天，也不会写进任何文件。

### 安装

**Claude Code（推荐）**
```
/plugin install iap-hero-mod --marketplace Mirako-Official/idle-abyss-princesses-mod-skill
```
旧版本 Claude Code 分两步：
```
/plugin marketplace add Mirako-Official/idle-abyss-princesses-mod-skill
/plugin install iap-hero-mod@mirako-iap
```
**已经装过、要更新**（更新后重启 Claude Code）：
```
claude plugin marketplace update mirako-iap
claude plugin update iap-hero-mod@mirako-iap
```

**手动安装**：把 `plugins/iap-hero-mod/skills/iap-hero-mod/` 整个文件夹复制到 `~/.claude/skills/`（个人）或项目里的 `.claude/skills/`。其他支持 skill 的助手同理；不支持的，让它先读 `SKILL.md`。

**需要**
- 《深渊放置姬》桌面版（Steam）。第一次用之前，在游戏里点「设置 → 模组 → 作者工具 → 作者资料」，游戏会把官方模组文档、模板和示例复制到存档目录的 `modkit/`
- Python 3 和两个库：`pip install pillow numpy`；预览技能特效还要 `pip install playwright` 和 `python -m playwright install chromium`
- 用 AI 生图时：对应服务的账号和密钥（见 `references/image-providers.md`）

### 怎么用

直接跟助手说，比如：
> 帮我做一个深渊放置姬的角色模组：一个用冰锤的熊猫厨师，懒洋洋的，立绘我用 NovelAI 画。

它会先问几个问题（角色、美术来源、玩法、语言），再按流程走。

### 里面有什么

| 路径 | 作用 |
|---|---|
| `SKILL.md` | 流程主线（助手读的） |
| `references/` | 生图服务、美术流程、hero.js 写法与坑、技能设计、装备特效设计、技能特效、变身角色、平衡、AI 聊天、测试与上传 |
| `examples/stella/` | 示例角色「星缀」：每个技能、每件传奇都是一种常用写法，含自定义特效和 pixelfx 精灵图表特效 |
| `scripts/gen_image.py` | 统一的生图 / 改图命令（openai / novelai / sdwebui） |
| `scripts/portrait_export.py` | 立绘导出（450×720，自动算 `face`） |
| `scripts/expr_composite.py` | 只把改过的脸贴回原图（表情差分不跳） |
| `scripts/chibi_frames.py` | 一张 Q 版图 → 战斗动作帧图集 + 纸娃娃 |
| `scripts/icons.py` | 16×16 字符格图标 → 检查、预览、`art_icons.js` |
| `scripts/form_sprite.py` | 像素图 → 战斗小人的字符格（变身形态用），预览和游戏里一模一样 |
| `scripts/i18n_dump.js` | 在游戏控制台里导出角色的全部文字和缺的译文 |
| `scripts/vfx_preview.py` | 在游戏外放技能、逐帧截图：帧总览图、GIF、报错和随机数检查（`--ref` 和官方技能并排） |
| `scripts/sheet_pack.py` | 把 pixelfx 导出的（或自己画的）特效帧打包成模组能播的精灵图表 |
| `scripts/check_mod.py` | 上传前的静态检查 |
| `scripts/make_preview.py` | 工坊预览图 |
| `templates/` | 设计稿模板、AI 聊天脚本模板 |

### 像素特效推荐学习：pixelfx

[patch-gg/pixelfx](https://github.com/patch-gg/pixelfx)（MIT，作者 Patch，方法和部分代码来自 Hugo Duprez）是 244 个用代码写的像素特效，[在线图库](https://patch-gg.github.io/pixelfx/)可以直接看。`references/skill-vfx.md` 第 6 节讲怎么学它的做法、怎么把它的特效导出成精灵图表放进模组；用了要在模组简介和 README 里保留它的 MIT 署名。

### 注意

- 只用你自己的、或有授权的美术。别人角色的二创要原作者同意，并在简介里署名（工坊规则第 2 条）。用了 AI 生图要勾 `AI Art` 标签。
- 这个仓库不包含游戏本体和官方模组文档；官方文档随游戏提供，以你安装的版本为准。

许可证：MIT。由 Mirako 维护。

---

## English

A **skill** for AI coding assistants (Claude Code and others) that walks a player through turning a
character into a playable **hero mod** for *Idle Abyss Princesses* and getting it ready for the
Steam Workshop: design, portrait and expressions, chibi battle sprites, 16×16 icons, `hero.js`
(skills, talents, three routes with sets and legendaries, court items), translations, balance in the
in-game hero lab, an optional chat with the hero through the player's own AI service (`IAP.ai`,
game 3.0.2+), and the Workshop upload. Since game 3.1.1 it also covers transforming heroes (like the
Dragon Princess turning into a dragon: borrow and recolour her dragon, or draw your own pixel form)
and dashes, charges and blinks. Skill design, legendary and set effect design (seven patterns with
official examples and typical numbers) and skill effects come with a tested example hero
(`examples/stella/`), an out-of-game effect preview (`scripts/vfx_preview.py`: contact sheet and GIF,
side by side with an official skill) and a packer for pixel art effects from
[pixelfx](https://github.com/patch-gg/pixelfx) (MIT, by Patch; method and part of the code by Hugo
Duprez), the effect library we recommend learning from.

**You choose the image model**: your own art or a commission, or an OpenAI-compatible Images API,
NovelAI, or a local Stable Diffusion WebUI. Keys stay in environment variables on your machine.

### Install

Claude Code (2.1.275 or later):
```
/plugin install iap-hero-mod --marketplace Mirako-Official/idle-abyss-princesses-mod-skill
```
Older versions:
```
/plugin marketplace add Mirako-Official/idle-abyss-princesses-mod-skill
/plugin install iap-hero-mod@mirako-iap
```
Update an installed copy (then restart Claude Code):
```
claude plugin marketplace update mirako-iap
claude plugin update iap-hero-mod@mirako-iap
```
Manual: copy `plugins/iap-hero-mod/skills/iap-hero-mod/` to `~/.claude/skills/` (or a project's
`.claude/skills/`).

Requirements: the desktop game (open Settings → Mods → Author Tools → Author Kit once, so the game
copies its modding docs and templates to `modkit/` in its data folder); Python 3 with
`pip install pillow numpy` (effect preview: also `pip install playwright` and
`python -m playwright install chromium`); for AI images, an account and key for the provider you pick.

### Use

Ask your assistant, for example: *"Make an Idle Abyss Princesses hero mod: a lazy panda chef with an
ice hammer. I'll make the art with NovelAI."* It asks a few questions, then follows the workflow.

### Notes

Use only art you own or have permission to use; credit fan art and tick the `AI Art` tag when an
image model was involved. The game and its official modding docs are not part of this repository.

License: MIT. Maintained by Mirako.
