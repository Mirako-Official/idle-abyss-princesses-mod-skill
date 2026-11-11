# <Hero name> — hero mod design

> Mod id / hero id: `<id>` (lowercase, 2–32 chars). Legendary `k` and set `key` start with `<id>_`; prefix skill and talent ids too (`<short>_`), they are global.
> Art source and credits: <who drew / generated what; permission; "AI Art" if any image model touched it>.

## 0. One line
<Who the character is and what makes them fun to watch, in one sentence. Jokes and personality go into skills, lines and item flavour.>

## 1. Identity
| Field | Value |
|---|---|
| `n` (class name) / `hero` (name) | <class> / <name> (+ en / ja / ko / zh-Hant) |
| `main` / `ele` | str / dex / int — phys / fire / cold / light / poison / holy … |
| `range` / `attack` | melee `0`, ranged about 5–6.5 (official heroes); `attack: { proj: 'orb' \| 'arrow' \| null, sfx }` |
| `weapons` / `offhands` / `offKind` / `weaponStyle` | 7 weapon names (weak → strong), 4 offhand names |
| `tint` | main colour `#rrggbb` |
| `desc` / `pass` / `bio` | one line / passive text from numbers / two sentences of background (+ art credit) |

## 2. Resource (optional)
<Name, range, how it fills and drains, what it does. Shown with resource(h, st) → { v, max, c, label }; pick a mid-tone colour so the white label stays readable.>

## 3. Skills (6)
Jobs by unlock level (references/skill-design.md): 1 bread and butter · 8 second damage, other shape · 18 buff / summon / zone · 30 signature · 42 defence / buff · 50 ultimate.
| id | name | unlock lv | job and shape | what it does | cd | tags | effect, one line of art direction |
|---|---|---|---|---|---|---|---|
| `<x>_a` | | 1 | area, farming | | 6 | skill | |
| … | | | | | | | |
Numbers live in one `<X>_BAL` table; descriptions are built from it.

## 4. Passive
<a.lifePct, a.dmgRed, ... — small, flavourful.>

## 5. Three routes (talent trees)
| Route | `route` | idea in one line | skills | set (2 stats / 4 mechanic / 6 ×mul on two skills) | two route legendaries (slot, pattern A–G, effect) |
|---|---|---|---|---|---|
| | | | 3 skills | name, piece names, bonuses | slot + pattern + effect, slot + pattern + effect |
Legendary patterns (references/item-effects.md): A changes a skill · B skill numbers · C proc · D condition · E stacks · F periodic · G defence.
The hero lab needs, per route: a set with at least 6 pieces and two route legendaries in different slots without `minStage`.

## 6. Court (王庭) items
Set name; five pieces (helm shoulders armor gloves pants); class items weapon (+ power), offhand, belt, boots.

## 7. Lines
skill / hurt / low / win / boss / elite / down / sleep / legend / set / gacha — two or three each, in character.

## 8. Art plan
| Asset | Source (own art / openai / novelai / sdwebui / other) | Status |
|---|---|---|
| Portrait idle (t0) | | |
| Expressions fight skill hurt low win down | | optional |
| Outfit tiers t1 / t2 | | optional |
| Chibi master (full body, facing right, transparent) | | optional, recommended |
| Icons 16×16 (legendaries, set pieces, court, skills) | hand-made grids (icons.py) | |
| Workshop preview | make_preview.py | |

## 9. Optional AI chat
<yes / no; character sheet for the persona; feeding bonus numbers.>
