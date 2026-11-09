# Transforming heroes (like the Dragon Princess turning into a dragon)

Needs game **3.1.1 or newer**. The Author Kit's `docs/MODDING.md` 3.13 is the authoritative short
version; this file is the full workflow. On older games a mod that writes `sprite: { base: …, form }`
loads but never changes its look (the form was dropped), so say "needs 3.1.1+" in the description.

## Contents
1. What a transformation is
2. Design it first
3. Code recipe
4. The pieces one by one
5. The look: borrow the dragon or draw your own
6. Panel estimate and the hero lab
7. Pitfalls checklist

## 1. What a transformation is

A timed state on `R.hero` that (a) changes numbers through the damage hooks, (b) swaps the battle
sprite through `sprite.form`, and optionally (c) changes skills, the resource bar, an aura and VFX.
Nothing new to register: it is ordinary hooks plus one sprite field.

The official Dragon Princess (`dragonkin`): Dragon Blood fills from hits (+2) and from being hit (+5);
at 100 she becomes a dragon for 12 s with +40 % damage on hits and damage over time, damage taken
×0.8, the sprite turns into a red winged dragon, her halberd disappears, her breath skill changes
shape, and her ultimate's cooldown resets when she transforms.

## 2. Design it first

Write it into `DESIGN.md` with the player before coding:
- **Trigger.** A resource that fills from hits, hits taken, kills or crits fits an idle game best (it
  happens on its own). A buff skill that starts the form is fine too. No manual button.
- **Duration and uptime.** e.g. 12 s of form for every ~20–30 s of charging → about 30–40 % uptime.
  Write the expected uptime down: the panel estimate needs it.
- **What changes.** Damage (hits, damage over time), damage taken, attack speed, one or two skills
  that behave differently, an aura. Change a few things strongly rather than everything a little.
- **Look.** Borrow the dragon and recolour it, or draw an own pixel form (section 5). The portrait
  does not change; use voice `lines` and a banner for flavour.
- **The joke.** The transformation is the character's big moment: give it a banner text, a voice
  line and a flavour line on the item that extends it.

## 3. Code recipe

Rename `myid` to your hero id. The same code is in MODDING 3.13 and the game's tests run it.

```js
const MY_FORM = { cap: 100, hit: 2, hurt: 5, t: 12, dmg: .4, taken: .8 };
function myCharge(n) {                          // charge; transform when full
  const h = R.hero; if (h.myid_formT > 0) return;
  h.myid_en = Math.min(MY_FORM.cap, (h.myid_en || 0) + n);
  if (h.myid_en < MY_FORM.cap) return;
  h.myid_en = 0; h.myid_formT = MY_FORM.t;
  banner('变身', '#ff8a2a'); shake(.3); sfx('boss');
}
registerHero({
  id: 'myid', /* …the other fields */
  onHit(m, d, src) { if (d > 0 && (src === 'atk' || src === 'ww')) myCharge(MY_FORM.hit); },      // basic attacks and skills
  onHurt(d) { if (d > 0) myCharge(MY_FORM.hurt); },                                                // being hit
  update(c, dt) { if (c.h.myid_formT > 0) c.h.myid_formT = Math.max(0, c.h.myid_formT - dt); },   // count down every frame
  hitMultiplier(m, src, opt) { return R.hero.myid_formT > 0 ? 1 + MY_FORM.dmg : 1; },              // direct hits (pets too)
  dotMultiplier(m, key) { return R.hero.myid_formT > 0 ? 1 + MY_FORM.dmg : 1; },                   // burn / bleed / poison ticks
  hurtMultiplier(h) { return h.myid_formT > 0 ? MY_FORM.taken : 1; },                              // damage taken
  resource: h => h.myid_formT > 0 ? { v: h.myid_formT, max: MY_FORM.t, c: '#ffb040', label: '变身' }
                                   : { v: h.myid_en || 0, max: MY_FORM.cap, c: '#e0402a', label: '能量' },
  reset(h) { h.myid_en = 0; h.myid_formT = 0; },                                                   // death, raid death, character switch
  sprite: { base: 'hunter', pal: { h: '#3a3050' },
    form: { base: 'dragonkin', when: h => h.myid_formT > 0, pal: { R: '#3a6ad0', r: '#1a2a6a' } } },
});
```

Put the numbers into your balance table (`MH_BAL.form = {...}`) and build the descriptions from it,
like every other number (`references/hero-code.md` 2).

## 4. The pieces one by one

- **State.** Fields on `R.hero`, prefixed with your id (`h.myid_formT`, `h.myid_en`). Runtime only,
  never saved. The dragon uses `h.formT`; an unprefixed name could collide with official code.
- **Charging.** `onHit(m, d, src, opt)`: `src` is `'atk'` (basic attack), `'ww'` (skill), `'proc'`,
  `'pet'`, `'thorns'`… Also `onHurt(d, src)`, `onKill(m)`, `onCrit(m)`. Do not let damage that only
  happens in form refill the bar, or the form never ends (the dragon's ultimate gives no blood).
- **The moment of transformation.** `banner(text, colour)`, `shake(.3)`, `sfx('boss')`; a ring:
  `if (!R.quiet) { const [x, y] = iso(HX, HY); R.rings.push({ x, y: y - 8, t: 0, max: .7, c: '#ff8a2a', r: 40 }); }`.
  Reset a skill's cooldown: `const i = S.skills.eq.indexOf('myid_ult'); if (i >= 0 && R.hero.cds) R.hero.cds[i] = 0;`.
- **Timer.** `update(c, dt)` runs every frame with a context; count down there. Do not use
  `later()` for the end of the form: deaths and stage changes would leave it hanging.
- **Numbers.** `hitMultiplier(m, src, opt)` every direct hit (and your pets', `src === 'pet'`);
  `dotMultiplier(m, key, fx)` every damage-over-time tick; `hurtMultiplier(h, st)` damage taken;
  `attackSpeedMultiplier(st, h)` attack speed. They run on every hit: read `R.hero` / `R.st`, nothing
  slow.
- **Resource bar.** `resource(h, st)` returns `{ v, max, c, label }`. Show the charge normally and
  the remaining seconds in form. Both labels are run-time text: translate them.
- **Skills in form.** In `cast(c)`, branch on `c.h.myid_formT > 0`: bigger area, another shape,
  another coefficient. The dragon's breath sprays in all directions in form.
- **Aura and VFX.** `drawAura(c, sx, sy, h)` draws under the hero's feet (keep it small: it sits
  under the dungeon darkness). Your `vfx` entries can read `R.hero.myid_formT` to change colour or
  size; VFX code is draw-only (never change the state there; it is off under reduced effects).
- **Movement.** Charges and leaps use the movement API (`c.dash`, `c.blink`; `references/hero-code.md` 4).
- **Determinism.** Combat code may use `chance` / `rnd`; VFX only `vrnd`.

## 5. The look: borrow the dragon or draw your own

`sprite.form: { when(h), base | rows + pal, weapon? }`. While `when(h)` is true the battle sprite is
this pixel image. `when` is called every frame: only read `R.hero` fields.

**Q 版 (chibi) mode.** While transformed, the chibi is replaced by the pixel form, like the dragon.
The player's setting 设置 → 龙化外观 → 保持Q版 ("Stay chibi") keeps the chibi for every transforming
hero. A separate chibi atlas for the form is not supported yet.

**Weapon.** The game's default code-drawn weapon is hidden in form (claws instead of a halberd).
`form.weapon: true` keeps it. If you wrote your own `drawWeapon(c, o)`, it decides: return early when
`o.h.myid_formT > 0`.

**Borrow the dragon.** `form: { base: 'dragonkin', when, pal: { … } }` copies the dragon's rows and
palette; your `pal` overrides single letters. The dragon is 22×19 (the human hero is 12×19). Letters:

| Letter | Part | Dragon colour |
|---|---|---|
| `R` | body scales | `#c83a2a` |
| `r` | body shadow, jaw, tail edge | `#8a1a2a` |
| `W` | wing membrane | `#ff8a2a` |
| `w` | wing frame and ribs | `#8a1a2a` |
| `B` / `b` | belly plates / their shadow | `#ffb040` / `#d8802a` |
| `S` | wing joint | `#ffb040` |
| `y` | horns | `#e8dcc0` |
| `e` | eye | `#ffe080` |
| `k` | teeth and claws | `#e8e0d0` |
| `f` | flame at the tail tip | `#ffe080` |

A blue frost dragon: `pal: { R: '#3a6ad0', r: '#1a2a6a', W: '#7ac8ff', w: '#1a2a6a', B: '#d8f0ff', b: '#9ac0e0', S: '#d8f0ff', f: '#bff0ff' }`.

**Draw your own.** Same grid format as `sprite.rows` / `sprite.pal`: one string per row, one
character per pixel, every character a key of `pal`, `.` transparent. The game adds a 1-pixel dark
outline (`#0b080a`) around the shape, centres the sprite on the hero's position and puts its bottom
row on the ground. It may be bigger than the human (keep it under ~32×32 on a 272×156 field).
Legs animate only when the two middle columns of the bottom rows (up to 7) are empty, i.e. there is a
gap between the legs; otherwise the form slides without steps (like the dragon).

Workflow: draw at 1× in a pixel editor (Aseprite, Piskel, LibreSprite) on a transparent canvas, keep
the hero's feet at the bottom and the body centred, 8–16 colours. Then:
```
python $SKILL/scripts/form_sprite.py art/form.png --out work/form
```
It prints the `form: { when: …, rows: [...], pal: {...} },` line for hero.js and writes
`work/form_preview.png`: the sprite exactly as the game builds it (outline added) with its walk
frames. Show the preview to the player. Image models cannot make clean pixel sprites at this size;
draw them, or have the player draw them.

## 6. Panel estimate and the hero lab

The panel's damage and toughness must include the form, or the hero lab reports a large panel error
and may grade the route wrongly. Model the charge rate from the panel numbers, then the share of time
in form (`up`):
```js
estimate(K) {
  const casts = K.eq.reduce((n, id) => n + 1 / K.skCd(id), 0);                 // skill casts per second
  const perSec = (K.aps + casts * 2) * MY_FORM.hit + MY_FORM.hurt;              // ~2 targets per skill, ~1 hit taken per second
  const up = Math.min(.6, MY_FORM.t / (MY_FORM.t + MY_FORM.cap / perSec));      // share of time in form
  return { dmg: 1 + MY_FORM.dmg * up, ehp: 1 / (1 - up * (1 - MY_FORM.taken)) };
},
```
`K.aps` is attacks per second, `K.eq` the equipped skill ids, `K.skCd(id)` a skill's real cooldown.
The dragon caps its estimated uptime at 60 % too. The lab runs real fights, so transformations happen
there; its grade reflects the uptime the hero really gets. Tune `cap`, `hit`, `hurt` and `t` until
every route is Standard (`references/balance.md`).

## 7. Pitfalls checklist

- [ ] Game 3.1.1+ stated in the description (older games drop the form when `sprite.base` is used).
- [ ] `when`, and `rows` + `pal` (or `base`), present: otherwise the whole mod fails to load with
      "sprite.form 需要 when(h)、rows 和 pal".
- [ ] State fields prefixed with your id; cleared in `reset(h)`.
- [ ] The timer counts down in `update`, not with `later()`.
- [ ] Damage that only exists in form does not refill the bar.
- [ ] Both resource labels translated.
- [ ] Your own `drawWeapon` returns early in form (or the weapon floats over the dragon).
- [ ] The estimate includes the uptime; the lab panel error stays within ±20 %.
- [ ] No state changes inside VFX code.
- [ ] Shadow teammates in 最后的最后 do not transform: their numbers come from `bal.shadow`.
