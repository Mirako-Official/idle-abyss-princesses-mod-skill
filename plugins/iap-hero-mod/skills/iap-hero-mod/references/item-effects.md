# Designing item effects: legendaries and sets

How to design and implement what a hero's legendaries and set bonuses do. Every pattern below is
implemented in `examples/stella/hero.js` and was checked in the game (each one changes the combat
result; nothing breaks with effects off). Official examples are quoted from the game's 243 legendaries.

## Contents
1. Where item effects live
2. Seven legendary patterns
3. Which hook for which trigger
4. Numbers: what the official items use
5. Sets: 2 / 4 / 6 pieces
6. Panel estimate
7. Writing the text
8. Checklist and traps

## 1. Where item effects live

- A legendary is data: `{ k: '<id>_x', t: slot, route, name, desc, fl }`. Its effect is **your code**,
  reading a flag that is `true` while the item is worn:
  - in a skill: `c.L.<k>` (skill context),
  - in hooks without a context (`hitMultiplier`, `onKill`, `onBasicHit`, `update` …): `R.st.L.<k>`
    (or `st.L` / `c.L` when the hook gets them),
  - in `estimate(K)` and skill `mul` / `cdMul`: `K.L.<k>` / `k.L.<k>`.
- A set bonus is either stats (`{ crit: 6, intPct: 8 }`) or a flag (`{ fx: '<id>_x4' }`) that shows up
  in `c.FX` / `R.st.FX` / `K.FX` and that you implement the same way.
- Court (王庭) items are generated with official effects; you only name them (MODDING 3.5).
- The hero lab needs, per route, **two route legendaries in different slots** (no `minStage`) and a set
  with at least six pieces. Extra legendaries are fine (Stella has seven).
- Mod items only drop for their own hero; legendary keys must start with `<hero id>_`.

## 2. Seven legendary patterns

A good legendary changes **how the hero plays** or **what to aim for**, not only a number. Give each
route one of each kind: something that changes a skill, and something that adds a condition or a
resource.

| Pattern | Stella item | How it is built | Official examples |
|---|---|---|---|
| **A. Changes a skill** | `stella_staff` 分光星杖: 星矢 also shoots 2 more targets | `if (c.L.stella_staff) …` inside the skill's `cast` | 狂风之刃 (Whirlwind lasts twice as long and pulses), 星陨法杖 (Meteor drops 2 more), 无常索 (the chain bounces), 裂风肩铠 (Lacerate becomes a spin) |
| **B. Skill numbers** | `stella_crown` 连星之冠: 星链 ×2, cooldown ×0.7 | the skill's `mul: k => …` and `cdMul: k => …` | 战神肩铠 (+150 % Whirlwind), 大法师之冠 (Meteor −40 % cd, +50 %) |
| **C. Proc on an event** | `stella_gloves` 落星手套: basic hits have 20 % to drop a star (120 % around the target) | `onBasicHit(m, st)` + `chance(p)` | 雷霆之怒 (15 % lightning on attack), 灼热之握 (25 % ignite), 灵魂收割者 (kills explode) |
| **D. Conditional damage** | `stella_ring` 定星指环: ×1.4 against stunned or slowed enemies | `hitMultiplier(m, src, opt)` + `hasStatus(m, 'stun')` | 处刑者之链 (Execute ×2 under 30 % life), 枷锁之环 (+25 % vs controlled), 忘川石 (+30 % vs frozen) |
| **E. Stacks** | `stella_boots` 追星之靴: +4 % per kill, max 10, gone after 6 s without a kill | a counter on `R.hero` in `onKill`, decay in `update`, read in `hitMultiplier`; optional `resource` bar | 屠王之刃 (stacks on the same elite), 勾魂腰牌, 痛苦之链 (stacks from being hit, spent by Execute) |
| **F. Automatic / periodic** | `stella_amulet` 星图坠饰: a free 星域 every 8 s | a timer on `R.hero` in `update(c, dt)` | 招魂幡 (a lantern every 8 s), 大地之心 (auto slam after standing 3 s), 神盾束带 (shield every 10 s) |
| **G. Defensive** | `stella_belt` 星幕腰带: damage taken ×0.8 while shielded | `hurtMultiplier(h, st)` | 奈何桥石 (−25 % in the lantern), 血盟之环, 嗜血战靴 (heal on Execute) |

The code, short (full versions in `examples/stella/hero.js`):

```js
// A. inside stella_bolt.cast(c)
if (c.L.stella_staff) for (const m of list.slice(1, 1 + SL.stella_staff.extra)) shoot(m, 'orb', SB.bolt.coef * SL.stella_staff.coef, 'ww', null, { sk: c.id });
// B. on the skill
mul: k => stellaSet6(k, 'stella_chain') * (k.L.stella_crown ? SL.stella_crown.mul : 1),
cdMul: k => k.L.stella_crown ? SL.stella_crown.cd : 1,
// C.
onBasicHit(m, st) {
  if (!st.L.stella_gloves || m.dead || !chance(SL.stella_gloves.chance)) return;
  for (const o of targetable(live()).filter(o => Math.hypot(o.gx - m.gx, o.gy - m.gy) < SL.stella_gloves.r)) hit(o, SL.stella_gloves.coef, 'proc');
},
// D. + E. (one hitMultiplier for everything)
hitMultiplier(m, src, opt) {
  const h = R.hero, L = R.st.L; let k = 1;
  if (L.stella_ring && (hasStatus(m, 'stun') || hasStatus(m, 'slow'))) k *= SL.stella_ring.mul;
  if (L.stella_boots && h.stella_stars) k *= 1 + SL.stella_boots.per * h.stella_stars;
  return k;
},
onKill(m) { if (!R.st.L.stella_boots) return; const h = R.hero; h.stella_stars = Math.min(10, (h.stella_stars || 0) + 1); h.stella_starT = 6; },
// E. decay + F. timer
update(c, dt) {
  const h = c.h;
  if (h.stella_starT > 0 && (h.stella_starT -= dt) <= 0) h.stella_stars = 0;
  if (c.L.stella_amulet && c.mons.length && (h.stella_amuletT = (h.stella_amuletT || 0) + dt) >= 8) { h.stella_amuletT = 0; /* addZone(...) */ }
},
reset(h) { h.stella_stars = 0; h.stella_starT = 0; h.stella_amuletT = 0; },   // death, stage change, rifts
// G.
hurtMultiplier(h, st) { return st.L.stella_belt && h.shield > 0 ? SL.stella_belt.taken : 1; },
```

Source tags for `hit`: `'ww'` = skill damage (takes skill damage %, the skill's `mul` via `{ sk }`),
`'proc'` = an item proc (no skill bonuses, monsters cannot dodge it), `'atk'` = basic attack.

## 3. Which hook for which trigger

| "When …" | Hook | Notes |
|---|---|---|
| a skill is cast | inside `cast(c)`; or `onCast(id, st)` for any skill | `onCast` runs after a successful cast |
| a basic attack hits | `onBasicHit(m, st)` | the right place for "attacks have X % to …" |
| any hit lands | `onHit(m, d, src, opt)` | `src`: `'atk'`, `'ww'`, `'proc'`, `'pet'` … |
| a hit crits | `onCrit(m, d, src, opt)` | |
| an enemy dies | `onKill(m)` | `m.boss`, `m.elite` |
| the hero is hit | `onHurt(d, src)`; block: `onBlock(src, raw)`; lethal: `onFatal(h, st)` | |
| every frame | `update(c, dt)` | timers, auras, periodic effects |
| damage dealt changes | `hitMultiplier(m, src, opt)`; ticks: `dotMultiplier(m, key)` | runs on every hit: keep it cheap |
| damage taken changes | `hurtMultiplier(h, st)` | before shields |
| a cooldown changes | skill `cdMul` / `cdAdd`, or `skillCooldown(id, st)` | `cdMul` also shows on the skill pane |
| a status lasts longer | `statusTime(key, t, m)`; stack cap: `statusMax(key, max)` | |
| state resets (death, new stage, rift) | `reset(h)` | clear every timer and counter you keep on `R.hero` |

## 4. Numbers: what the official items use

Typical sizes across the official legendaries (use them as a start, then the lab decides):
- Procs: 15–25 % chance, 60–300 % damage; an area proc 1.5–2.5 tiles. Internal cooldown when it could
  fire many times a second ("同一敌人每秒一次").
- Skill buffs: +50–150 % or ×1.5–2.5 on one skill; cooldown −30–50 %.
- Conditions: ×1.3–1.4 or +25–40 % ("vs frozen", "under 30 % life", "vs elites").
- Stacks: 2–5 % per stack (up to 20 % per stack when spent at once), 10–20 stacks, lost after 6–10 s.
- Periodic: every 8–10 s.
- Defence: −20–30 % damage taken, shields of 20–30 % of life.
A legendary that only adds a flat stat ("+10 % damage") is the weakest kind: players skip it.

## 5. Sets: 2 / 4 / 6 pieces

The official pattern, which the hero lab expects:
- **2 pieces: stats.** Two small stats from the list in HEROES.md (`crit`, `critDmg`, `ias`, `skill`, `ele`,
  `lifePct`, `armorPct`, `dmgRed`, `intPct` / `strPct` / `dexPct` …). Not `dmgPct`.
- **4 pieces: a mechanic** (`{ fx: '<id>_x4' }`) that makes the route play differently, or stats if the
  route needs survival.
- **6 pieces: ×mul on the route's two main skills**, read in those skills' `mul`. This is the main
  balance knob; the lab's advice line ("raise damage ×1.4") is about it. The example values (×40, yoru
  ×52–72) are placeholders until the lab has run.
- Seven pieces exist (helm shoulders armor gloves pants belt boots); 6 is the top bonus.

```js
const stellaSet6 = (k, id) => Object.entries(SB.sets).reduce((m, [name, o]) => m * (k.FX['stella_' + name + '6'] && o.skills.includes(id) ? o.mul : 1), 1);
// skill: mul: k => stellaSet6(k, 'stella_bolt'),
// set:   b: [[2, '…', SB.sets.star.b2], [4, '…', { fx: 'stella_star4' }], [6, '…', { fx: 'stella_star6' }]]
```

## 6. Panel estimate

Item effects that are not in a skill's `mul` must be modelled in `estimate(K)`, or the lab shows a large
panel error. Model the average: uptime of timers, average stacks, the share of time a condition holds,
procs as extra DPS divided by `K.eff`. Stella's `estimate` does all seven patterns (ward uptime,
ring share, average boots stacks, gloves procs from `K.dps`, amulet fields from `K.avg`, belt as `ehp`).
Keep it free of side effects; tune the guesses (`STELLA_BAL.est`) until the lab's panel error is within
±20 %.

## 7. Writing the text

- `desc`: what it does, with the numbers from the balance table, one sentence. Trigger first, then the
  effect, then limits: "普通攻击有 20% 几率砸下小星，对目标周围 1.5 格造成 120% 伤害。"
- `fl`: one short in-character line (the joke goes here): "手一滑，星就掉了。"
- Name the item after what it does, so players remember it (分光星杖 splits the bolt).
- Every legendary, set piece and court item needs its own 16×16 icon (`scripts/icons.py`).

## 8. Checklist and traps

- [ ] Each route: one legendary that changes a skill, one that adds a condition / stacks / timer.
- [ ] Effects read `c.L` / `R.st.L` / `K.L` flags; set mechanics read `FX` flags you named `<id>_…`.
- [ ] Combat randomness only through `chance` / `rnd` / `pick`; effect code only `vrnd`.
- [ ] Every timer or counter on `R.hero` is cleared in `reset(h)`.
- [ ] Hooks that run per hit read live state (`R.st`, `R.hero`), never saved data (`MOD.data.get()`).
- [ ] Delayed code (`later`) checks `R.encounter` and the hero being alive.
- [ ] `estimate` models every effect that is not in a skill `mul`.
- [ ] Descriptions are built from the balance table and match what the code does.
