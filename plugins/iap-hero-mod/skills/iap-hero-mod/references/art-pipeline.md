# Art pipeline: portrait, expressions, chibi, icons, preview

Run every command from the player's work folder (the one holding `mod/`, `art/`, `work/`), calling
the scripts by full path: `$SKILL` is this skill's folder. Keep sources and candidates in `art/`;
only exported files go into `mod/`. Every script prints its options with `--help`.

## 1. Portrait

Spec (the game draws portraits into a 120×192 = 5:8 frame, fit and bottom-aligned):
- transparent background, full body, feet near the bottom
- export **450×720** WebP. An exact multiple of 120×192 (360×576, 480×768…) is treated as upscaled
  pixel art and drawn with nearest-neighbour: the left panel portrait looks blocky. The export
  script avoids this.
- `portrait.webp` (the base) + `portraits/t0_<expr>.webp`. Expressions: idle fight skill hurt low
  win down (sleep, blink optional). Missing frames fall back (expression → idle; tier → lower tier →
  portrait), so a single idle portrait is already complete.
- The template's placeholder `portrait.png` beats `portrait.webp`: delete it.

```
python $SKILL/scripts/portrait_export.py mod --idle art/portrait/t0_idle.png \
    --expr fight=art/portrait/t0_fight.png --expr win=art/portrait/t0_win.png \
    --face 521,252 --preview work/portraits.png
```
`mod` is the mod folder (positional); `--idle` and each `--expr name=file` are source images.
`--face X,Y` is the centre of the face (between the eyes and the mouth) in **pixels of the idle
source image**, whatever its size. The script converts it and prints `face: [x, y]` (120×192 frame
coordinates) for `registerHero`; the hero picker crops the avatar there (the default [60, 44] lands
on the neck of a full-body portrait). The source may be any size, even an exact multiple of
120×192: only the exported files must not be, and the script always writes 450×720.
Look at the preview and at the game: the portrait is about 240 px tall in the left panel.

Outfit tiers: run again with `--tier 1 --idle art/portrait/t1_idle.png ...` (and `--tier 2`). Ask the
player whether the outfit should change at all; many want one look.

## 2. Expressions (optional)

1. Edit the idle master with an edit-capable provider (image-providers.md, "Expression edit").
2. Paste back only the face:
```
python $SKILL/scripts/expr_composite.py art/portrait/t0_idle.png art/work/t0_win_raw.png art/portrait/t0_win.png \
    --face 521,252 --radius 120 --preview work/check_win.png
```
(`--face` again in source pixels; `--radius` about half the face width.)
   The red overlay in the preview is what was taken from the edit. Too little (eyes missing): lower
   `--threshold` or raise `--radius`. Too much (hair, ribbons, hands): smaller `--radius`.
3. Look at the six faces side by side at full size before exporting. Typical misses: the model
   redrew the whole face shape, added a tear on the wrong side, or changed the eye colour.

## 3. Chibi battle sprites (optional, recommended)

Without them the hero uses a small generated pixel sprite. With them the hero looks like the official
heroes in battle and on the character page.

Master: one clean full-body chibi, facing RIGHT, transparent (or a flat background with `--bg`),
legs visible, about 2.5 heads tall. Then:
```
python $SKILL/scripts/chibi_frames.py art/chibi/master.png mod --preview work/chibi_frames.png
```
Writes `mod/chibi/manifest.json`, idle / walk / attack / cast / hurt strips at scales 2 3 4 6 and
`doll.webp` (about 70 s; WebP encoding is the slow part). Options: `--flip` (master faces left),
`--clean-r 2` (thin weapons or hair strands get eaten by the default cleanup), `--neck .45` (head
pivot height), `--no-legs` (the whole lower body moves as one). The script prints whether it found legs
("legs: lifted"); if the outfit covers the legs to the ankles (robe, long dress) and the walk frames
in the preview tear the hem or show stretched boots, rerun with `--no-legs`. Check the preview: feet on the red
anchor dot, nothing clipped, no flicker between frames. Then check in game: the sprite stands on its
shadow and is about as tall as an official hero.

## 4. Icons (16×16, hand-made)

Every legendary, set piece, court item and skill gets its own icon (the game's rule for official
items too). Draw them as character grids in `art/icons.json`:
```json
{ "leg:myhero_blade": { "pal": { "1": "#5a92f0" }, "rows": ["................", "....", "... 16 rows of 16 chars"] },
  "set:myhero_cot:helm": { "pal": {}, "rows": [ ... ] },
  "court:weapon": { ... }, "skill:mh_strike": { ... } }
```
- `.` transparent; other characters come from the item's `pal` or the game palette ART_PAL (listed
  in `icons.py --help`): steel `S s t d`, leather `L l m`, gold `G g h`, wood `W w Z`, red `R r q`,
  fire `F f o`, ice `I c C`, lightning `Y y z`, wind/jade `a A x`, arcane `p P j`, poison/plants
  `N i K`, pink `H J M`, shadow `T D`, bone/cloth `B b n`, gem glow `e E`.
- Leave 1 px free around the shape: the game adds a dark outline.
- One set shares one palette and one emblem; each piece still gets its own shape (headband, cape,
  dress, gloves, skirt, belt, shoes…). Legendaries show their idea at a glance (a bowl with a whirl
  for "bottomless"). Skills read as small symbols.
- Drawing 30–40 grids by hand is slow; writing a small helper that composes them from primitives
  (outline, fill, emblem stamped on each piece) is fine, as long as every piece still gets its own
  shape: a headband looks like a headband, a belt like a belt. Different sets should not reuse the same
  shapes with only new colours.
- Build, check and preview:
```
python $SKILL/scripts/icons.py build art/icons.json mod/art_icons.js --sheet work/icons.png
```
  `mod.json` scripts must list `art_icons.js` before `hero.js`, and hero.js says
  `itemArt: MOD.shared.itemArt`.
- Draw a few, look at the sheet at 1× and 2× (the strip at the bottom), fix, continue. Blocky blobs
  at 1× mean too many colours or details smaller than 2 px.

## 5. Workshop preview

```
python $SKILL/scripts/make_preview.py --portrait art/portrait/t0_idle.png --doll mod/chibi/doll.webp \
    --top '#163a70' --bottom '#040a1a' --out mod/preview.jpg
```
640×640 JPG under 1 MB, no text. Match the gradient to the character's colours.
