# Balance with the in-game hero lab (角色实验室)

Balance is not a fixed set of numbers: the game compares your hero with the official heroes of the
same game version. The hero lab runs the official measuring method on each of your routes and grades
it **标准 Standard / 偏弱 Weak / 超标 Overtuned**. The Workshop uploader takes the balance tag from the
lab result, so a hero needs a complete lab run before upload. Aim for Standard on every route unless
the player wants a joke hero (that is allowed, it just gets labelled).

## Running it

Settings → 角色实验室 (or the "test in lab" button next to the hero in Settings → Mods). Pick the
hero, run the full test. It takes minutes and runs in a hidden copy of the game, so it never touches
saves. Ask the player to run it and to paste or screenshot the result table and the advice lines.
Re-run after every balance change; the result is tied to the mod's content hash.

## The checkpoints and what moves them

| Checkpoint | Measures | Main knobs |
|---|---|---|
| Farming 开荒 | 30 min of idle play from level 1: stage reached, deaths | early skills (unlock level 1–8) coefficients and cooldowns, passive, base attack, how much time cast locks waste early |
| Mid game 中期 | level 60, route set (6 pieces) + 2 route legendaries, two dummies: DPS, toughness, panel error | skill coefficients, 2/4-piece bonuses, legendaries |
| Endgame 大毕业 | standard maxed gear: single / pack DPS, toughness, highest rift | 6-piece ×mul, pet scaling, AoE (splash radius, number of targets) |
| Court 王庭 | full court gear, solo, 7 epic bosses: total time | single-target burst, survivability |
| Ultra 超高难 | in a standard team with shadow allies: total time | single-target, `bal.shadow` |
| Legend rift 传奇秘境 | court gear / myth gear: highest floor | sustained DPS and toughness at the top end |
| Encore 最后的最后 | team heart rate reached | team contribution, `bal.shadow` |

The lab shows the official range for each checkpoint and an advice line ("raise damage ×1.4"). Fix
the earliest failing checkpoint first: farming problems come from early numbers, endgame ones from
set multipliers and AoE.

## How to tune

- Change one thing at a time, in the balance table, and re-run. Keep notes in DESIGN.md.
- Prefer coefficients, cooldowns, set `mul` and legendary effects over a flat global damage %.
- Down-time mechanics (wind-up, naps, channels) are fine; pay them back in the coefficient so the
  route still reaches the range.
- Panel error over ±20 % means `estimate()` does not match combat: model uptime, cast-lock time, pet
  count and resource level (hero-code.md section 5).
- AoE matters for pack DPS and rifts: a single-target route can get a small splash on its big hit.
- Extra permanent bonuses (such as a chat "feeding" bonus) are not measured by the lab (saved data
  is empty there). Cap them (e.g. +30 %) so a maxed player is still near the range.

Example from a shipped hero (three routes, all Standard after two passes): main nuke coef 10 → 14 and
cd 10 → 9 s plus a 3.5-cell 80 % splash; pet coef 0.7 → 1.2 and attack interval 1.1 → 1.0 s; pet
route 6-piece ×40 → ×160; rice route 6-piece ×40 → ×90.
