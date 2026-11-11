---
name: iap-hero-mod
description: Make a complete custom hero (角色) mod for the Steam game 深渊放置姬 / Idle Abyss Princesses and get it ready for the Steam Workshop — character design, portrait and expression art, Q 版 chibi battle sprites, 16×16 item and skill icons, hero.js (skill design, legendary and set effect design, talents, three routes, court items), skill effects (VFX) with an out-of-game preview and pixelfx sprite sheets, translations, balance in the in-game 角色实验室 hero lab, an optional chat-with-the-hero feature through the player's own AI service (IAP.ai), and the Workshop upload. The player chooses how art is made (their own drawings, an OpenAI-compatible image API, NovelAI, local Stable Diffusion, or another tool). Use this skill whenever someone wants to create, port, fix or finish a hero / character mod, 角色模组, 自定义角色, 工坊角色, OC or fan character for Idle Abyss Princesses — even if they only ask about one piece, such as chibi sprites for their mod, a pixelated mod portrait, mod translations, a hero failing the lab, designing skills or legendary effects, making skill effects look better, or uploading a hero to the Workshop.
---

# Idle Abyss Princesses: custom hero mod

You are helping a player turn a character into a playable hero mod: a folder the game loads from its
`mods/` directory and the player can upload to the Steam Workshop. The finished mod has a portrait
(with optional expressions and outfit tiers), battle sprites, icons, a `hero.js` that registers the
hero, translations, a lab-tested balance, and a Workshop preview.

**Running the scripts.** Below, `$SKILL` is this skill's folder (the one containing this SKILL.md).
The scripts need Python 3 with `pip install pillow numpy` (`vfx_preview.py` also needs `pip install playwright`
and `python -m playwright install chromium`). Run them from the player's work folder
with full paths, e.g. `python $SKILL/scripts/check_mod.py mod`; each one prints its usage with `--help`.

The game ships its own authoritative modding docs (the **Author Kit**). Read them for API details of
the installed version; this skill gives the workflow, the tools, and the lessons from shipping a
hero mod. Talk to the player in their language. Many players are not programmers: explain what you
are about to do in plain words, and show pictures (previews, screenshots) rather than file dumps.

## 1. Start with a short interview

Ask in one message, offer defaults, and do not block on details you can decide later:
1. **The character**: name, look, personality, the jokes or themes the character should show off. Original, or
   fan art of someone else's character? (Fan art needs the artist's permission and credits.)
2. **Art source and image provider**: own drawings / commission / another tool, or one of the
   providers `scripts/gen_image.py` supports (openai-compatible, novelai, sdwebui). Which assets:
   portrait (needed), expressions (optional), outfit tiers (optional), chibi (recommended).
   Read `references/image-providers.md` before using any provider.
3. **Gameplay idea**: melee or ranged, main stat, element, a resource or gimmick (a transformation
   like the Dragon Princess's dragon form? dashes and leaps?), skills, three routes.
4. **Languages**: Chinese is the source language of the game; at least English is strongly advised;
   Japanese, Korean and Traditional Chinese are supported.
5. **Optional AI chat** with the hero through the player's own AI key (needs game 3.0.2+ desktop).
6. **Their OS and game install**, to find the game's folders.

Never ask the player to paste API keys into the chat. Keys go into environment variables on their
machine; the scripts read them from there.

## 2. Find the game's folders and read the Author Kit

`<userData>` is `%APPDATA%\IdleAbyssPrincesses` (Windows), `~/Library/Application Support/IdleAbyssPrincesses`
(macOS), `~/.config/IdleAbyssPrincesses` (Linux) or, under Proton / Steam Deck,
`~/.steam/steam/steamapps/compatdata/5335850/pfx/drive_c/users/steamuser/AppData/Roaming/IdleAbyssPrincesses`.
Inside: `mods/` (installed mods), `modkit/` (the Author Kit), `logs/main.log`.

If `modkit/` is missing, ask the player to open Settings → 模组 → 作者工具 → 作者资料 once; the game
copies the kit there. Then read, in this order: `docs/MODDING.md` (or `MODDING.en.md` / `.ja.md`)
chapters 2–5 and 7 (plus 14.14 for AI chat), `docs/HEROES.md`, `web/heroes/_template.js`, and the full
example `modding/examples/yoru/`. The kit matches the installed game version, so trust it over this
skill when they disagree.

## 3. Set up the work folder

Keep work outside the game folder:
```
<id>-mod/
  DESIGN.md   the design (copy $SKILL/templates/DESIGN.md)
  mod/        the mod itself: copied to <userData>/mods/<id>/ for testing
  art/        sources, candidates, masters (not shipped)
  work/       previews, screenshots, notes
```
Create `mod/` from the official hero template: copy `modkit/modding/templates/hero/` and replace
`{{id}}` and `{{name}}` in every file (in-game alternative: Settings → 模组 → 作者工具 → 新建模组 →
角色). What to do with the template's files:
- `hero.js`: a small working hero (two skills, one legendary, one set, `{{id}}_` keys). Use it to see
  the shape, then replace its content with your design; keep the `<id>_` key prefixes.
- `portrait.png`: a placeholder. Delete it once you export your portrait (it would win over
  `portrait.webp`).
- `jsconfig.json` (+ `.iap/` the game adds): code completion in VS Code. Keep, not shipped as assets.
- `README.md`: replace with your own (what the hero is, credits).
- `mod.json`: set `"api": 3` (needed for `IAP.onReady`, `IAP.ui`, `MOD.data`, `IAP.ai`; works on any
  current game), a version, author, and the descriptions.
The mod id is lowercase letters, digits and `_`, 2–32 characters.

## 4. Design together

Fill `DESIGN.md` with the player: identity, resource, six skills, three routes (each with a 7-piece
set and two route legendaries in different slots), court items, voice lines, art plan. Make the
personality do the work: the skills, item flavour lines and voice lines are where a character
becomes fun. Agree on the design before writing code; it is much cheaper to change here.
- Skills: read `references/skill-design.md` (the six-skill kit, official cooldowns and damage ranges,
  building blocks, routes).
- Legendaries and sets: read `references/item-effects.md` (seven legendary patterns with official
  examples, which hook for which trigger, typical numbers, 2/4/6-piece sets, estimate).
- Effects: one line of art direction per skill in DESIGN.md (`references/skill-vfx.md`).
- `examples/stella/` is a complete example hero where each skill and each legendary is one pattern,
  tested in the game. Copy from it.

## 5. Make the art

Follow `references/art-pipeline.md`:
- portrait master → `scripts/portrait_export.py` (450×720 WebP; `--face X,Y` takes the face centre
  in pixels of the SOURCE image you pass as `--idle` and prints `face: [x, y]` for registerHero)
- optional expressions: edit the face with the player's provider → `scripts/expr_composite.py`
  (pastes back only the face, so expressions do not jump)
- optional chibi master → `scripts/chibi_frames.py` (battle atlas + character-page doll)
- icons: draw 16×16 grids in `art/icons.json` → `scripts/icons.py build` (no image models: they
  cannot make clean 16 px icons, and the game's own icons are hand-made)
- Workshop preview → `scripts/make_preview.py`

Show the player every candidate and preview sheet and let them choose. Respect their decisions about
the look (for example "keep the outfit unchanged in every tier").

## 6. Write hero.js

Start from the template and the yoru example, then read `references/hero-code.md` (structure,
patterns, and the traps that do not throw errors). Key points:
- one balance table at the top; every description built from it
- prefixed ids; 3 talent trees × 7 nodes; per route a 6+ piece set and two route legendaries
- `itemArt: MOD.shared.itemArt`, `face: [x, y]`, `bio` with the art credits, voice `lines`
- nothing at the top level of a script may touch game UI or renderer globals: they do not exist
  yet when mod scripts run (use `IAP.onReady` or register lazily)
- dashes, charges and leaps: `c.dash` / `c.blink` (`references/hero-code.md` 4), never write `HX` / `HY`
- a transformation (a timed form with its own numbers and sprite, like the dragon): follow
  `references/transform.md`; draw a form sprite with `scripts/form_sprite.py` or borrow the dragon
- signature effects: `references/skill-vfx.md`. Draft, then look at each skill with
  `scripts/vfx_preview.py` (contact sheet + GIF from the installed game, `--ref hero:skill` puts an
  official skill next to it) and fix the worst thing, three rounds at least. Ready-made pixel art
  effects: pixelfx (https://github.com/patch-gg/pixelfx, MIT) → `scripts/sheet_pack.py`; credit it.

## 7. Translate

Translation files are `{ "Chinese source": "translation" }` and the keys must match the rendered text
exactly, numbers included. Get the real strings from the running game: start it with `--devtools`,
paste `scripts/i18n_dump.js` into the console, run `iapDump('<id>')`, and have the player paste the
clipboard into `work/strings.json`. It also lists which languages are missing what. It also lists **conflicts**: Chinese
texts the game's own dictionary already translates; the game's entry wins over yours, so rename those
(a different wording in Chinese) if you want your own translation. Add the texts your code builds at
run time by searching the scripts: arguments of your floating-text helper, labels returned by
`resource()`, banner or log lines, chat UI strings.
Before the game is available you can already translate names, voice lines and flavour text by reading
the source; sentences with numbers must be checked against the dump. Keep the jokes in translation;
prefer natural phrasing over literal.

## 8. Check, install, test

Run `python scripts/check_mod.py mod` until it shows no ERROR. Then install (copy `mod/` to
`<userData>/mods/<id>/`), restart the game, and go through the in-game checklist in
`references/workshop.md` with the player: picker card and avatar, portrait, battle sprite, skills,
floating text, resource bar, items and icons, every language, zero errors in Settings → 模组.

## 9. Balance in the hero lab

Settings → 角色实验室 (or "test in lab" next to the hero in the mod list). Read
`references/balance.md` for what each checkpoint measures and which numbers move it. Iterate until
every route is Standard (标准), unless the player deliberately wants a joke or challenge hero.

## 10. Optional: AI chat

If the player wants it, copy `templates/ai_chat.js`, edit its `CONFIG`, and follow
`references/ai-chat.md` (untrusted replies, capped bonus, disclosure in the description).

## 11. Upload

The player uploads from the game: Settings → 模组 → the mod → 上传到创意工坊. See
`references/workshop.md` for what the uploader checks, the description and credits, tags (Balance
comes from the lab; tick AI Art when an image model touched any art) and visibility. Descriptions in
`mod.json` are cut at 300 characters per language: keep the credits inside.

## 12. Keep it maintainable

Leave `DESIGN.md`, the balance table, `art/icons.json` and the source images in the work folder, and
note in DESIGN.md what was decided and why. The next update (rebalance after a game patch, a new
expression, a fixed translation) then takes minutes.

## Lessons from shipping a hero mod

- A 360×576 portrait (exactly 3× 120×192) is drawn as pixel art and looks blocky; export 450×720.
- The template's `portrait.png` placeholder wins over your `portrait.webp`; delete it.
- Normal mod scripts run before the game's scripts: `VFX`, `showModal` and friends are undefined at
  the top level. Code that registers things there silently does nothing.
- Floating text drawn in `drawAura` is dimmed by the dungeon darkness; draw it in a VFX air-layer kind.
- A near-white resource bar makes its white label unreadable; use a mid-tone colour.
- Untranslated Chinese is split into fragments and half-translated ("这问题有points难"): translate
  every whole sentence, including run-time labels.
- Keep `mod.json` names ≤ 40 and descriptions ≤ 300 characters per language.
- The source art can be any size; only the exported portrait must avoid exact multiples of 120×192
  (the export script handles it).
- Image model edits drift: composite only the face back, and compare all frames side by side.
- Mods cannot use the network; the only exception is the player's own AI service through `IAP.ai`.
- Writing `HX` / `HY` teleports the hero with no movement; `c.dash` moves it over time and can hit
  everything on the way (game 3.1.1+).
- A transforming hero needs the uptime in `estimate`, or the lab shows a big panel error.
- Effects that throw are silently dropped in the game, and `Math.random` in effect code changes combat:
  `vfx_preview.py`'s report catches both.
- Effect kinds registered at the top level of a script never exist (VFX is not defined yet): use
  `IAP.onReady`.
