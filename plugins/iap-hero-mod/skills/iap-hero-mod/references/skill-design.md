# Designing skills

How to design a hero's six skills so they feel good in an idle game, sit in the same range as the
official heroes, and are easy to balance. Code for every pattern is in `examples/stella/hero.js`
(tested in the game: each skill fires, each item effect changes the result, and combat is identical
with effects on and off). API details: `references/hero-code.md` and the Author Kit's `docs/HEROES.md`.

## Contents
1. How skills run in this game
2. The six-skill kit
3. Numbers: what the official heroes use
4. Building blocks (with code)
5. Routes: skills, talents and gear together
6. Descriptions and tags
7. Design checklist

## 1. How skills run in this game

- The player never presses a skill. Three skill slots open at levels 1, 8 and 50 (`S.skills.eq`);
  every frame the game tries each equipped skill whose cooldown is ready, in slot order.
- `cast(c)` runs. Return `false` when there is nothing to do (no target in range): the cooldown is not
  spent and the game tries again next frame. Anything else counts as a cast: cooldown starts, the
  signature effect plays, the voice line and sound play.
- `c.h.ww = seconds` is a cast lock: no basic attacks and no other skills for that long. It is the
  price of a big hit. Official values are 0.2–0.4 s.
- Buffs (`buff: 1`) may define `hold(c)`: return `true` to wait while the buff is still running and
  recasting would give nothing (the player can turn this off in the skill pane).
- Three skills of the six are equipped at a time. Each route (talent tree) recommends three
  (`talents[i].skills`), and auto-allocation swaps them in. So design **per route**: three skills that
  work together, with the other three still usable.
- Damage numbers scale from the hero's average hit (`c.st.avg`): `hit(m, 3.2, 'ww', { sk: c.id })` deals
  320 % of an average hit before multipliers. Everything a skill does is a multiple of `avg`.

## 2. The six-skill kit

The official heroes unlock skills at levels **1, 8, 18, 30, 42, 50** and give them these jobs:

| Unlock | Job | Official examples | Notes |
|---|---|---|---|
| 1 | Bread and butter: the hero's main way to kill packs early | 旋风斩 Whirlwind, 陨石术 Meteor, 多重射击 Multishot, 御剑术 Flying Swords | Decides the lab's **farming** checkpoint. Short cooldown (5–8 s), hits several enemies |
| 8 | Second damage skill, other shape (area if lv1 is single, or the reverse) | 震地猛击 Ground Slam, 冰霜新星 Frost Nova, 爆裂箭 Explosive Arrow | Second slot opens here: the first two skills carry the early game |
| 18 | Buff, summon or zone | 战吼 Battle Cry, 猎鹰突袭 Falcon, 剑阵 Sword Array | Often a route's identity piece |
| 30 | Signature damage skill | 斩杀 Execute, 连锁闪电 Chain Lightning, 天堂之拳 Fist of Heaven | Usually the main skill of one route |
| 42 | Defence or second buff | 奥术屏障 Arcane Barrier, 孟婆汤, 调息 | Gives tanky routes something to build on |
| 50 | Ultimate: long cooldown (15–30 s), a big moment | 血怒 Bloodrage, 一剑开天, 焚世, 亡者行军 | Third slot opens at 50. Make it look and sound big |

Every hero has a mix of shapes: at least one **area** skill (packs and rifts), one strong
**single-target** skill (bosses, the court and the ultra raid), one **buff or defence**. Two skills that
do the same thing in the same shape make the third slot boring.

## 3. Numbers: what the official heroes use

From the game data (version 3.1.2). `est` is the skill's total damage per cast in average hits, as the
panel counts it (reference scene: two enemies close together); `est/cd` is damage per second from that
skill in average hits, before talents, gear and set multipliers.

| Hero | Skills (unlock: cooldown s, est/cd) |
|---|---|
| Warrior | 1 Whirlwind 8 s 0.5 · 8 Slam 10 s 0.6 · 18 Cry 20 s buff · 30 Execute 6 s 1.0 · 42 Lacerate 5 s 1.0 · 50 Bloodrage 25 s buff |
| Mage | 1 Meteor 8 s 0.7 · 8 Nova 10 s 0.24 · 18 Chain 6 s 0.5 · 30 Barrier 18 s buff · 42 Flame 4 s 1.6 · 50 Field 15 s 1.2 |
| Hunter | 1 Multishot 6 s 1.2 · 8 Explosive 7 s 0.9 · 18 Falcon 20 s pet · 30 Rain 12 s 0.6 · 42 Hawk Cry 16 s buff · 50 Trap 8 s 0.95 |
| Paladin | 1 Holy 8 s 0.8 · 8 Hammer 6 s 4.2 · 18 Shield 20 s buff · 30 Fist 8 s 1.4 · 42 Hallow 14 s 2.1 · 50 Precept 12 s buff |
| Machinist | 1 Turret 8 s 2.2 · 8 Rail 7 s 1.5 · 18 Forcefield 18 s buff · 30 Prism 6 s 0.8 · 42 Gravity 10 s 1.4 · 50 Overclock 25 s buff |
| Cultivator | 1 Swords 6 s 3.4 · 8 Cloud Step 9 s 4.5 · 18 Array 18 s 0.7 · 30 Thunder 12 s 3.4 · 42 Breath 20 s buff · 50 Heaven Split 30 s 1.5 |

Read these as **ranges, not targets**:
- Cooldowns: damage skills 4–12 s, buffs 16–25 s, ultimates 15–30 s. Under 4 s feels like a basic attack.
- Damage skills sit around **0.5–1.5 average hits per second** each; newer heroes run higher
  (2–4.5) because their basic attack is weaker. A hero's total matters, not one skill.
- Most of a route's endgame power comes from the **6-piece set multiplier** on its main skills (×4 to ×70
  depending on how the base numbers are set). That is the knob the hero lab tells you to turn
  (`references/balance.md`), so the base numbers mainly decide how the hero feels early and how the
  damage is split between skills.
- Control on bosses and elites is reduced (`CONTROL_DR`: bosses ×0.5, elites ×0.75 duration). A route
  built on stuns is weaker on bosses than it looks; give it something else for single targets.
- Start a new hero with: lv1 skill est/cd ≈ 1, coefficient 2–4 per enemy hit, cooldown 5–8 s. Then let
  the lab move it.

## 4. Building blocks

Each line is a pattern in `examples/stella/hero.js`; copy the skill and rename.

| Pattern | Stella skill | Core calls | Use for |
|---|---|---|---|
| Single target / projectile | `stella_bolt` 星矢 | `byDist(c.near(r))[0]`, `shoot(m, 'orb', coef, 'ww', null, { sk: c.id })` | Boss damage, a ranged hero's main skill |
| Area around the hero + control | `stella_quake` 坠星 | `c.near(r)`, `hit(m, coef, 'ww', { sk, stun })` | Packs, melee heroes, stun routes |
| Ground zone | `stella_field` 星域 | `addZone({ x, y, r, t, every, coef, sk, c, slow })` | Damage over time in an area; `pull`, `heal`, `guard`, `on(m, z)` exist too |
| Bounces / delayed hits | `stella_chain` 星链 | `later(s, fn)` with the `R.encounter` check | Chains, combos, "explodes after 1 s" |
| Buff | `stella_ward` 星幕 | a timer on `R.hero` + `hitMultiplier`; shield via `c.h.shield`; `hold(c)` | Damage windows, defence |
| Dash | `stella_dive` 流星 | `c.dash(target, { dur, pass, end })` | Melee gap closers, "crash into the pack" ultimates |
| Damage over time | (yoru example) | `applyStatus(m, 'burn' | 'bleed', { t, dps, stacks })` | Poison and bleed routes; tag `dot` |
| Summons | (HEROES.md) | `addPet(ttl)`, `petCount(K)`, `petStats` | Pet routes; tag `pet` |
| Transformation | `references/transform.md` | a timed form on `R.hero` + `sprite.form` | A big state change, like the dragon |

Rules that keep them correct:
- **Targets**: `c.near(r)` (enemies within r tiles, already filtered to targetable ones),
  `c.densest(list, r)`, `c.mons` (all alive). Sort with `hdist(m)` for nearest/farthest.
- **Delayed code** must check the fight is still the same one and look targets up again:
  `const enc = R.encounter; later(t, () => { if (enc !== R.encounter || R.hero.dead > 0) return; … })`.
- **Random numbers** in combat code: only the game's `chance(p)` / `rnd(a, b)` / `pick(list)`. Never
  `Math.random` in effects (use `vrnd`), and never consume randomness in effect code.
- **Per-skill multipliers** belong in the skill's `mul: k => …` (6-piece, legendaries): the panel and
  the combat both read it. A global damage stat (`dmgPct`) adds to the player's gear affixes and makes
  them worthless; avoid it.
- **Movement** only through `c.dash` / `c.blink` (never write `HX` / `HY`).

## 5. Routes: skills, talents and gear together

A route is three skills + a talent tree + a 7-piece set + two route legendaries. Design them as one
idea ("the falling-star route: big area hits that stun, then punish stunned enemies"):
- The **6-piece** multiplies the route's two main skills (`stellaSet6`).
- The **4-piece** changes how a skill behaves (`stella_earth4`: 坠星 hits again 0.8 s later). Flags
  you invent (`{ fx: 'myid_x4' }`) appear in `c.FX` / `R.st.FX`; you implement them.
- The **two legendaries** push the same idea from two sides (one changes a skill, one adds a
  condition): see `references/item-effects.md`.
- The **talent cap** and pick options can use your own flags too (`CAP('id', '名字', 'myid_cap', '说明')`,
  then `c.FX.myid_cap` / `R.st.FX.myid_cap`). Stella's `stella_cap` stops 星链 from losing damage per
  bounce.

## 6. Descriptions and tags

- Build every description from the balance table (`` `造成 ${sp(B.coef)}% 伤害` ``). Say what it does,
  where, and how much, in one or two short sentences. Numbers as Arabic digits.
- `tags` must be true: `skill` (direct skill damage), `atk` (basic attack damage), `dot`, `pet`, `zone`,
  `buff`. They only label the skill in the UI but players read them to pick gear.
- `say` lines on the skill and the hero's `lines` give personality; keep them short.

## 7. Design checklist

- [ ] Each skill has one clear job; no two skills share job and shape.
- [ ] At least one area skill, one single-target skill, one buff/defence.
- [ ] The level-1 skill alone can farm (the lab's farming checkpoint).
- [ ] Every route has three skills that work together, a 4-piece that changes behaviour and a 6-piece
      that multiplies two skills.
- [ ] Cooldowns in range (damage 4–12 s, buffs 16–25 s, ultimate 15–30 s); cast locks ≤ 0.4 s unless
      the skill pays for it.
- [ ] `cast` returns `false` when nothing happened; delayed code checks `R.encounter`.
- [ ] Each skill has a signature effect (`references/skill-vfx.md`) and you looked at it with
      `scripts/vfx_preview.py`.
- [ ] Descriptions and tags built from the balance table and true.
