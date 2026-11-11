# 星缀 Stella: example hero for the iap-hero-mod skill

A pattern library, not a finished or balanced hero (no portrait, no chibi, no translations, numbers not
graded in the hero lab). Copy the parts you need.

| File | What it shows |
|---|---|
| `hero.js` | Six skills, each one way to build a skill (projectile, area + stun, ground zone, bounces with delays, buff, dash); seven legendaries, each one kind of item effect (changes a skill, skill numbers, proc, condition, stacks, periodic, defence); 2/4/6-piece sets; a custom talent flag; an `estimate` that models all of it |
| `fx.js` | Two hand-written effect kinds (`stella_star`, `stella_fall`) and a sprite-sheet player (`stella_sheet`, `MOD.shared.sheet`) |
| `fx/boom.png`, `fx/sheets.js` | An explosion from pixelfx, packed by `scripts/sheet_pack.py`; 流星 plays it where she lands |

Walkthroughs: `references/skill-design.md`, `references/item-effects.md`, `references/skill-vfx.md`.
Try it: copy this folder to `<userData>/mods/stella/` and restart the game, or look at the effects
without playing: `python scripts/vfx_preview.py --mod examples/stella`.

## Credits

`fx/boom.png` is rendered from pixelfx's `explosions/small-explosion` (https://github.com/patch-gg/pixelfx):

MIT License. Copyright (c) 2026 Patch. Copyright (c) 2026 Hugo Duprez.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the
following conditions: The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF
ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
