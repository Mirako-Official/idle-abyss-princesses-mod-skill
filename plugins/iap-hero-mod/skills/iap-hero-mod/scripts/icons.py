#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Mirako
"""Build the hand-drawn 16 x 16 item / skill icons of an Idle Abyss Princesses hero mod.

You draw icons as character grids in a JSON file; this script checks them, renders a preview sheet
the way the game draws them (palette, 1 px dark outline, rarity frames) and writes the mod script
that hands them to the game:

  python icons.py build icons.json MOD_DIR/art_icons.js [--sheet preview.png] [--names names.json]

icons.json
  {
    "leg:<legend key>":          { "pal": { "1": "#5a92f0" }, "rows": [16 strings of 16 chars] },
    "set:<set key>:<slot>":      { ... },      slot: helm shoulders armor gloves pants belt boots
    "court:<slot>":              { ... },      court items: helm shoulders armor gloves pants weapon offhand belt boots
    "skill:<skill id>":          { ... }
  }
  '.' is transparent. Other characters are looked up in the item's "pal" first, then in the game's
  shared palette ART_PAL (copied below: steel S s t d, leather L l m, bone/cloth B b n, gold G g h,
  wood W w Z, red R r q, fire F f o, ice I c C, blood v V, lightning Y y z, wind/jade a A x,
  arcane p P j, gem glow e E, plants/poison N i K, pink H J M, shadow T D, extra O X, ink k u).
  Leave a 1 px gap around the shape: the game draws a dark outline around every icon.

art_icons.js (generated, do not edit) sets MOD.shared.itemArt; in hero.js write
  itemArt: MOD.shared.itemArt
and list "art_icons.js" before "hero.js" in mod.json "scripts".

Checks: 16 x 16 grids, known characters only (the game silently skips unknown ones), #rrggbb colours,
valid keys, no two identical icons. Needs Python 3 and Pillow.
"""
import argparse, json, re, sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit('icons.py needs Pillow:  pip install pillow')

ART_PAL = {      # the game's shared icon palette (web/js/item_art.js)
    'k': '#1a1216', 'u': '#2e2a36',
    'S': '#f4f8fc', 's': '#c0c8d4', 't': '#8a94a4', 'd': '#565e6e',
    'L': '#d8a46c', 'l': '#a06a3c', 'm': '#664222',
    'B': '#f6eed8', 'b': '#d4c8a0', 'n': '#968860',
    'G': '#fff2a8', 'g': '#e2b442', 'h': '#a0701e',
    'W': '#b8824a', 'w': '#7a4c2a', 'Z': '#4a3424',
    'R': '#ff8c64', 'r': '#d4422e', 'q': '#7c1c1a',
    'F': '#fff4a8', 'f': '#ffa236', 'o': '#e0481a',
    'I': '#eafcff', 'c': '#90d8ff', 'C': '#3c7cd8',
    'v': '#ff4a5a', 'V': '#a01428',
    'Y': '#fffbd0', 'y': '#a8c8ff', 'z': '#4a6aff',
    'a': '#a8ffe0', 'A': '#44c89c', 'x': '#1e7a64',
    'p': '#e0b0ff', 'P': '#9a5ad8', 'j': '#4a2478',
    'e': '#7af0ff', 'E': '#ffffff',
    'N': '#c8f080', 'i': '#6ab040', 'K': '#2e6a2a',
    'H': '#ffc0d8', 'J': '#e870a0', 'M': '#8a2a58',
    'T': '#7a6a9a', 'D': '#3e3456',
    'O': '#ffb070', 'X': '#ff6ad8',
}
OUTLINE = (20, 12, 16, 255)
SLOTS = {'helm', 'shoulders', 'armor', 'gloves', 'pants', 'belt', 'boots', 'weapon', 'offhand', 'ring', 'amulet'}
KEY_RE = re.compile(r'^(leg:[a-z][a-z0-9_]{1,63}|set:[a-z][a-z0-9_]{1,63}:[a-z]+|court:[a-z]+|skill:[A-Za-z0-9_]{1,64})$')
FRAME = {'leg': (255, 140, 40), 'set': (60, 200, 80), 'court': (170, 110, 255), 'skill': (150, 150, 160)}


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def check(icons):
    errs, seen = [], {}
    for key, v in icons.items():
        if key.startswith('_'): continue
        if not KEY_RE.match(key): errs.append(f'{key}: key must look like leg:<k>, set:<set>:<slot>, court:<slot> or skill:<id>'); continue
        if key.startswith('set:') and key.split(':')[2] not in SLOTS: errs.append(f'{key}: unknown slot')
        if isinstance(v, list): v = {'rows': v}
        rows, pal = v.get('rows'), v.get('pal', {})
        if not isinstance(rows, list) or len(rows) != 16: errs.append(f'{key}: needs 16 rows'); continue
        for name, col in pal.items():
            if len(name) != 1 or not re.fullmatch(r'#[0-9a-fA-F]{6}', str(col)): errs.append(f'{key}: pal entry {name!r}: {col!r} must be one character -> #rrggbb')
        full = dict(ART_PAL, **pal)
        for j, r in enumerate(rows):
            if not isinstance(r, str) or len(r) != 16: errs.append(f'{key}: row {j} must be 16 characters, got {len(r) if isinstance(r, str) else type(r).__name__}'); continue
            bad = sorted({ch for ch in r if ch != '.' and ch not in full})
            if bad: errs.append(f'{key}: row {j} uses characters not in the palette: {"".join(bad)} (the game would skip them)')
        sig = '\n'.join(rows) + json.dumps(pal, sort_keys=True)
        if sig in seen: errs.append(f'{key}: identical to {seen[sig]} (every item needs its own icon)')
        seen[sig] = key
        if all(ch == '.' for r in rows for ch in r): errs.append(f'{key}: empty icon')
    return errs


def render(v, scale):
    if isinstance(v, list): v = {'rows': v}
    pal = dict(ART_PAL, **v.get('pal', {})); rows = v['rows']
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0)); px = im.load()
    for j in range(16):
        for i in range(16):
            ch = rows[j][i]
            if ch != '.' and ch in pal: px[i, j] = hexrgb(pal[ch]) + (255,)
    op = [[px[i, j][3] > 0 for i in range(16)] for j in range(16)]
    for j in range(16):
        for i in range(16):
            if op[j][i]: continue
            if (i > 0 and op[j][i - 1]) or (i < 15 and op[j][i + 1]) or (j > 0 and op[j - 1][i]) or (j < 15 and op[j + 1][i]): px[i, j] = OUTLINE
    return im.resize((16 * scale, 16 * scale), Image.NEAREST)


def sheet(icons, names, out):
    keys = [k for k in icons if not k.startswith('_')]
    cols, cell, S = 8, 96, 4
    rows = (len(keys) + cols - 1) // cols
    W, H = cols * cell + 16, rows * (cell + 30) + 16 + 60
    im = Image.new('RGBA', (W, H), (24, 20, 28, 255)); d = ImageDraw.Draw(im)
    try: font = ImageFont.truetype('NotoSansCJK-Regular.ttc', 11)
    except Exception:
        try: font = ImageFont.truetype('msyh.ttc', 11)
        except Exception: font = ImageFont.load_default()
    for n, k in enumerate(keys):
        x, y = 8 + (n % cols) * cell, 8 + (n // cols) * (cell + 30)
        fr = FRAME[k.split(':')[0]]
        d.rectangle([x + 8, y, x + 8 + 16 * S + 7, y + 16 * S + 7], fill=(40, 34, 46, 255), outline=fr + (255,), width=2)
        im.alpha_composite(render(icons[k], S), (x + 12, y + 4))
        d.text((x + 4, y + 16 * S + 10), names.get(k) or k.split(':', 1)[1][-17:], fill=(230, 220, 200, 255), font=font)
    y = 8 + rows * (cell + 30); x = 8      # actual size strip (x1 and x2) in rarity frames
    for k in keys:
        fr = FRAME[k.split(':')[0]]
        d.rectangle([x, y, x + 35, y + 35], fill=(40, 34, 46, 255), outline=fr + (255,), width=1); im.alpha_composite(render(icons[k], 2), (x + 2, y + 2))
        x += 38
        if x > W - 40: x = 8; y += 38
    im.convert('RGB').save(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build'); b.add_argument('icons_json'); b.add_argument('out_js'); b.add_argument('--sheet'); b.add_argument('--names', help='JSON { key: display name } for the sheet')
    c = sub.add_parser('check'); c.add_argument('icons_json')
    a = ap.parse_args()
    icons = json.loads(Path(a.icons_json).read_text('utf-8-sig'))
    errs = check(icons)
    for e in errs: print('ERROR', e)
    n = len([k for k in icons if not k.startswith('_')])
    if errs: sys.exit(f'{len(errs)} problem(s) in {n} icons')
    if a.cmd == 'check': print(f'{n} icons OK'); return
    clean = {}
    for k, v in icons.items():
        if k.startswith('_'): continue
        v = v if isinstance(v, dict) else {'rows': v}
        used = {ch for r in v['rows'] for ch in r}
        clean[k] = {'pal': {c: col for c, col in v.get('pal', {}).items() if c in used}, 'rows': v['rows']}      # drop unused colours
    js = ("'use strict';\n/* Generated by icons.py from " + Path(a.icons_json).name + ": edit the JSON and rebuild, not this file. */\n"
          'MOD.shared.itemArt = ' + json.dumps(clean, ensure_ascii=False, indent=1) + ';\n')
    Path(a.out_js).parent.mkdir(parents=True, exist_ok=True); Path(a.out_js).write_text(js, 'utf8')
    print(f'{n} icons OK -> {a.out_js}')
    if a.sheet:
        names = json.loads(Path(a.names).read_text('utf-8-sig')) if a.names else icons.get('_names', {})
        sheet(clean, names, a.sheet); print('sheet', a.sheet)


if __name__ == '__main__':
    main()
