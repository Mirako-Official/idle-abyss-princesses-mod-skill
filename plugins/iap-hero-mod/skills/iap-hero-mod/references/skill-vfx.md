# Skill effects (VFX)

How to give every skill a signature effect that looks hand-made, how to look at it without playing,
and how to use the open-source pixel art effect library **pixelfx**. Working code:
`examples/stella/fx.js` (custom kinds, a sprite-sheet player) and the `vfx` field of
`examples/stella/hero.js`.

## Contents
1. How effects run
2. The game's effect kinds
3. Your own kinds
4. The loop: draft, look, fix (`scripts/vfx_preview.py`)
5. The quality bar
6. pixelfx: learning from it and using its effects
7. Checklist

## 1. How effects run

- After every successful cast the game calls your `vfx[skillId]()` (the hero's `vfx` field). No entry →
  a generic effect in the hero's element colour. An **empty entry** (`stella_dive: () => {}`) turns the
  generic one off when the skill draws its effect elsewhere.
- Inside it you spawn effects: `vfx(kind, opts)` returns the effect object or `null` when effects are
  off. Pick targets the same way the skill does: `vNear()`, `vDense(r)`, `vLow()`, `vLive()`, and
  `vAt(m)` → `{ gx, gy }` (the hero's feet for `null`).
- From hero code (inside `cast`, `later`, `end()` of a dash) wrap effect calls in `vfxTry(() => …)`:
  it returns `false` and does nothing when effects are off or the code throws.
- **Draw only.** Effects never change combat. Random numbers only from `vrnd(lo, hi)`, never
  `Math.random` (it is the combat stream: an effect that calls it changes fights and replays).
- Effects are off while the game simulates in the background, with 设置 → 降低特效 (reduce effects), and
  in the desktop widget. The game must look complete without them: keep a plain hit flash or ring in
  the skill itself if the player needs to see where it landed.
- An effect that throws is silently removed in the game. `scripts/vfx_preview.py` prints the error.

Screen space: the battle canvas is **272 × 156 game pixels**. The battle hero is about **20 px tall**
(chibi) or 19 rows (pixel sprite). The floor is isometric: one tile is 16 px wide and 8 px tall on
screen, so a ring on the floor is an ellipse with a 2:1 ratio (`GRX = 11.31`, `GRY = 5.66` pixels per
tile of radius). `iso(gx, gy)` gives the screen point of a grid position.

## 2. The game's effect kinds

Common options: `d` duration (s), `c` colour, `c2` second colour, and a position: `follow: true` (on the
hero), `gx, gy` (grid) or `x, y` (screen). `until: () => bool` ends it early.

| Kind | Layers | Options | Looks like |
|---|---|---|---|
| `shock` | ground | r (tiles), c, c2 | flat shockwave ring expanding on the floor |
| `crack` | ground | n, len, c | cracks opening from the centre, glowing |
| `arc` | air | r, a0, sweep, w, sq, ox, oy, c, core | a crescent slash |
| `spin` | ground, air | c, c2 | two slashes circling the hero |
| `aura` | ground, air | c, rate, acc | breathing ring + rising motes (buffs) |
| `pillar` | ground, air | h, w, c | a column of light from the floor |
| `rune` | ground | r, c, c2, a, spin | magic circle with turning runes |
| `bubble` | air | c, c2 | hex shield around the hero |
| `burst` | air | n, cs (colours), sp [min,max], g, up, oy | particles bursting out and falling |
| `flash` | air | r, c, oy | a hit flash |
| `beam` | air | x1, y1, x2, y2, w, c | a thick beam between two screen points |
| `spikes` | air | n, r, sp, c, c2 | spikes erupting from the floor |
| `wave` | ground | r, n, c | thin rings rippling out |
| `stream` | air | tgt / ang, rate, c, c2 | a jet of particles (breath, flame) |
| `charge` | air | c | motes gathering in front of the hero |
| `vortex` | ground | r, c | spiral arms pulling in |
| `aimline` | air | x1, y1, x2, y2, c, arcs | a charging aim line |
| `xcut` | air | at, h, c | crossed slashes |
| `gather` | air | n, st, c | gold lines gathering to a sword |

`vfxBlast(x, y, rTiles, c, c2)` = shock + flash + burst, for explosions.
The official heroes' files (`web/js/vfx_<hero>.js` in the game) show how they combine these.

## 3. Your own kinds

A kind is an object with any of these functions; `k` is progress 0..1 (`e.t / e.d`):

```js
VFX.myid_star = {
  init(e) { e.rot = vrnd(0, .6); },              // once, when spawned: roll every random number here
  tick(e, dt) { },                                // every frame (optional)
  ground(c, e, k) { },                            // under characters, darkened by the dungeon
  air(c, e, k) { },                               // over everything, after the darkness: glows
  light(e, k) { return [x, y, radius, strength, colour]; },   // lights up the dark (array of lights allowed)
};
```

- Register kinds in `IAP.onReady(() => { VFX.myid_star = … })`: at the top level of a mod script `VFX`
  does not exist yet. Prefix every name with your hero id.
- Helpers from the game: `vPos(e)` (screen point of the effect), `vPx(c, x, y, size)` (a pixel block),
  `vRing(c, x, y, rx, ry, col, w, from, to)` (pixel ellipse), `vDisc(c, x, y, rx, ry, col, alpha)`
  (soft filled ellipse), `vEase(k)` (fast in, slow out), `vHex(col, a)`, `pline(c, x0, y0, x1, y1, col)`.
- Draw in game pixels and round positions (`Math.round`): the canvas is scaled up without smoothing,
  so half pixels smear.
- `ground` is dimmed by the dungeon darkness away from the hero; anything that should glow goes in
  `air`, plus a `light`.
- Stella's `stella_star` (a glint at the target) and `stella_fall` (a star falling on the hero:
  streak → white frame → ring) are complete examples with anticipation, impact and decay.

## 4. The loop: draft, look, fix

One-shot effects are mediocre; effects you look at and fix three times are good. You cannot judge
motion from code, and playing the game to wait for a cooldown is slow, so use the preview script:

```
pip install playwright pillow numpy
python -m playwright install chromium
python $SKILL/scripts/vfx_preview.py --mod mod --skill myid_strike
python $SKILL/scripts/vfx_preview.py --mod mod --skill myid_strike --ref mage:meteor   # next to an official skill
python $SKILL/scripts/vfx_preview.py --mod mod --lowfx                                 # what 降低特效 players see
```

It finds the installed game (or `--game <folder>`), casts the skill on training dummies in a headless
copy with a fixed seed and clock (same command, same pictures; saves are never touched), and writes
`work/vfx/<skill>/contact.png` (every 2nd frame with its time), `anim.gif` (real speed), `frames/`
and `report.txt`. The report lists the casts, the effect kinds spawned, errors your effect code threw
(the game hides them) and any `Math.random` inside effect code.

Then:
1. **Say it in one line** with art direction: "a star streaks down onto her, white flash on impact, a
   ring spreads on the floor and fades".
2. **Draft** with the game's kinds first; write your own kind when they cannot say it.
3. **Render and look** at `contact.png` (open the image), then `anim.gif` for the motion.
4. **Compare** with `--ref` against an official skill of the same weight. If the official one has more
   detail, light or life at the same size, yours is not done.
5. **Fix the worst thing**, render again. Three rounds minimum. Show the player the contact sheets.
6. Check `--lowfx` (the skill still reads without effects) and `--art pixel`.

## 5. The quality bar

Adapted from pixelfx's authoring guide (§6) to this game's size:

1. **Lines and light, not fills.** 1 px rims, rings, trails and sparks; white-hot core, tinted middle,
   deep colour only at the edges. Big flat areas of saturated colour look cheap.
2. **Phases.** Anticipation (something gathers or falls), release (1–2 frames of white, a flash, a
   light), spread, a hold (glints, embers), a long decay. Fast in, slow out (`vEase`).
3. **Timing.** Hits 0.3–0.8 s; big skills 1–2 s; buffs as long as the buff (`until`). The release
   should land on the frame the damage happens.
4. **Light.** A `light` on every bright effect: a big soft pool at low strength, a flare at impact that
   falls away.
5. **Depth.** Floor rings are 2:1 ellipses on the `ground` layer; things in the air go in `air`.
6. **Variety.** Every particle differs a little (size, speed, delay) via `vrnd` in `init`.
7. **Reads at 1×** with one focal point. At 20 px per hero, fewer bigger shapes beat many tiny ones.
8. **Fits the field.** The whole battle is 272 × 156; an ultimate may fill a third of it, a basic
   skill should not.

| You see | Fix |
|---|---|
| mush at 1× | fewer colours, one focal point, bigger shapes |
| floaty, no punch | shorter, `vEase` in, a 1–2 frame white flash at impact, a `light` flare |
| stiff | vary each particle; add secondary motion (sparks, a ring, falling bits) |
| washed out | less glow, darker edges, white only in the core |
| a sticker pasted on the field | anticipation before the hit and a decay after it; a floor ring or crack ties it to the ground |
| invisible in the dark | move it from `ground` to `air`, add a `light` |
| smears | round coordinates; draw whole pixels |

## 6. pixelfx: learning from it and using its effects

[pixelfx](https://github.com/patch-gg/pixelfx) (by Patch, MIT; the method and part of the code by
Hugo Duprez, see its NOTICE.md) is a library of 244 pixel art effects written as code (fire,
explosions, ice, lightning, holy, shadow, impacts, projectiles, status, …) with a gallery at
<https://patch-gg.github.io/pixelfx/>. It is the best free reference for this kind of work:

- **Learn from it.** Read its `docs/AUTHORING.md` ("The bar" and "The method") and the three
  reference effects it names (`melee/sword-slash`, `ice/frost-nova`, `explosions/small-explosion`).
  The same ideas work in this game: seeded randomness, a colour layer plus a light layer (our
  `air` + `light`), choreography in phases, render-look-fix. To borrow a technique, read its source and
  rewrite it as one of your kinds with `vrnd` and the helpers above.
- **Use its effects as sprite sheets.** Pick one in the gallery, then:

```
git clone https://github.com/patch-gg/pixelfx          # Node 18+, no install step
cd pixelfx
node tools/render.mjs explosions/small-explosion --sheet --no-actor --opts '{"size":0.5}' --out ../pfx
cd ..
python $SKILL/scripts/sheet_pack.py --json pfx/explosions/small-explosion/small-explosion.json --mod mod --name boom --every 2 --secs 1.4 --light 36,.8,6,#ffb060
```

  `sheet_pack.py` trims the frames, drops every other frame (`--every 2`), cuts a long smoke tail with a
  fade (`--secs`), and writes `mod/fx/boom.png` and `mod/fx/sheets.js`. Add `"fx/sheets.js"` before your
  effect script in `mod.json` `scripts`, copy the sheet player from `examples/stella/fx.js`
  (`stella_sheet` kind + `MOD.shared.sheet`) and play it: `vfxTry(() => MOD.shared.sheet('boom', { gx, gy }))`.
  Stella's 流星 dash plays the pixelfx explosion where she lands.

What to watch:
- **Size.** pixelfx's stand-in character is 24 × 38 px; ours is about 20 px tall, so its effects are
  roughly twice our scale. Make them smaller with the effect's own options (`--opts`: `size`, `reach`,
  `radius`, … listed in each effect's `meta.options`), never by scaling the image by a fraction (it
  ruins the pixels). Big explosions and ultimates can stay large.
- **View.** pixelfx is drawn from the side; floor rings there are very flat. Air effects (explosions,
  impacts, flashes, sparks, lightning, projectiles, status icons) fit best. For a ring on our floor draw
  it yourself with `vRing` at 2:1.
- **Colour.** Recolour at export with `--opts '{"palette":["#102","#215","#43a","#8cf","#fff"]}'` (dark
  to bright). One sheet = one colour; export several for several elements.
- **Timing.** Its acts have wind-ups and hit-stops; a mod cannot freeze combat (effects are draw only).
  Start the sheet when the damage happens, or skip the wind-up frames with `sheet_pack.py --start`.
- **File size.** Keep a sheet under ~300 KB (`--every 2`, `--secs`). Every player downloads it.
- **Credit.** MIT requires the notice: put "Effects from pixelfx (https://github.com/patch-gg/pixelfx),
  MIT License, Copyright (c) 2026 Patch, Copyright (c) 2026 Hugo Duprez" in your mod's README and the
  Workshop description. Don't recreate a specific game's sprites with it, as its own rules say.

## 7. Checklist

- [ ] Every skill has a `vfx` entry (or an empty one when it draws elsewhere).
- [ ] Kinds registered in `IAP.onReady`, names prefixed with the hero id.
- [ ] Only `vrnd` in effect code; random numbers rolled in `init`; the preview report shows no errors
      and no `Math.random`.
- [ ] Looked at every skill with `vfx_preview.py`, at least three rounds on the big ones, compared
      with an official skill (`--ref`).
- [ ] The skill still reads with `--lowfx`.
- [ ] Sprite sheets: whole-pixel scale, under ~300 KB, credit in README and description.
