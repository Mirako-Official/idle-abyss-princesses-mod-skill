#!/usr/bin/env python3
"""Turn a small pixel-art PNG into the game's sprite grid (rows + pal), e.g. for a transformation form.

The game draws pixel battle sprites from a character grid: every character is a palette key, '.' is
transparent, and a 1-pixel dark outline (#0b080a) is added around the shape automatically. Draw the
form at 1x (one pixel = one game pixel) in any pixel editor (Aseprite, Piskel, LibreSprite) on a
transparent background, then run:

    python form_sprite.py art/form.png --out work/form

It prints a JS object to paste into hero.js (fill in your own `when`):

    form: { when: h => h.myid_formT > 0, rows: [...], pal: {...} }

and writes <out>_preview.png: the sprite as the game builds it (outline added), its two walk frames,
scaled up. The centre of your canvas is the hero's position and the lowest drawn row is where the
feet stand: empty rows above and below are trimmed, empty columns are trimmed equally on both sides.
Legs only animate when the two middle columns of the bottom rows (up to 7) are empty, i.e. there is
a gap between the legs.

Options: --scale N (preview zoom, default 8), --max-colors N (warn above it, default 24),
--no-crop (keep every transparent margin), --var NAME (print `const NAME = {...};` instead).
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image

KEYS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
OUTLINE = (11, 8, 10, 255)      # #0b080a, core.js buildSprite


def grid_from_png(path, crop=True):
    im = Image.open(path).convert('RGBA')
    if crop:      # rows: trim to the drawing (the bottom row is where the feet stand); columns: trim the same amount on both sides, so the centre stays where it was drawn
        bbox = im.getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox()
        if not bbox:
            sys.exit(f'{path}: the image is fully transparent')
        side = min(bbox[0], im.width - bbox[2])
        im = im.crop((side, bbox[1], im.width - side, bbox[3]))
    w, h = im.size
    px = im.load()
    count = {}
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a >= 128:
                count[(r, g, b)] = count.get((r, g, b), 0) + 1
    if len(count) > len(KEYS):
        sys.exit(f'{path}: {len(count)} colours; the grid has {len(KEYS)} keys at most. Reduce the palette')
    order = sorted(count, key=lambda c: (-count[c], c))
    key = {c: KEYS[i] for i, c in enumerate(order)}
    rows = []
    for y in range(h):
        s = ''
        for x in range(w):
            r, g, b, a = px[x, y]
            s += key[(r, g, b)] if a >= 128 else '.'
        rows.append(s)
    pal = {key[c]: '#%02x%02x%02x' % c for c in order}
    return rows, pal


def walk_rows(rows, frame):
    """Same as the game's walkRows (gfx.js): lift the left (1) or right (2) half of the leg rows by one pixel."""
    if not frame:
        return rows
    h, w = len(rows), max(len(r) for r in rows)
    mid = w // 2
    gap = lambda j: (rows[j][mid - 1] if mid - 1 < len(rows[j]) else '.') == '.' and (rows[j][mid] if mid < len(rows[j]) else '.') == '.'
    top = h
    while top > h - 7 and top > 0 and gap(top - 1):
        top -= 1
    if top >= h:
        return rows
    out = list(rows)
    a, b = (0, mid) if frame == 1 else (mid, w)
    for j in range(top, h):
        below = rows[j + 1] if j + 1 < h else ''
        out[j] = ''.join((below[i] if i < len(below) else '.') if a <= i < b else (rows[j][i] if i < len(rows[j]) else '.') for i in range(w))
    return out


def build_sprite(rows, pal):
    """Same as the game's buildSprite (core.js): 1-pixel border, dark outline around opaque pixels."""
    h, w = len(rows), max(len(r) for r in rows)
    im = Image.new('RGBA', (w + 2, h + 2), (0, 0, 0, 0))
    f = lambda i, j: 0 <= j < h and 0 <= i < len(rows[j]) and rows[j][i] != '.' and rows[j][i] in pal
    for j in range(-1, h + 1):
        for i in range(-1, w + 1):
            if not f(i, j) and (f(i - 1, j) or f(i + 1, j) or f(i, j - 1) or f(i, j + 1)):
                im.putpixel((i + 1, j + 1), OUTLINE)
    for j in range(h):
        for i, ch in enumerate(rows[j]):
            if ch != '.' and ch in pal:
                c = pal[ch].lstrip('#')
                im.putpixel((i + 1, j + 1), (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), 255))
    return im


def preview(rows, pal, scale):
    frames = [build_sprite(walk_rows(rows, f), pal) for f in (0, 1, 2)]
    fw, fh = frames[0].size
    sheet = Image.new('RGBA', (fw * 3 + 4, fh), (42, 38, 52, 255))
    for i, fr in enumerate(frames):
        sheet.alpha_composite(fr, (i * (fw + 2), 0))
    return sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('png', help='pixel art at 1x, transparent background')
    ap.add_argument('--out', help='write <out>.json (rows + pal) and <out>_preview.png')
    ap.add_argument('--scale', type=int, default=8)
    ap.add_argument('--max-colors', type=int, default=24)
    ap.add_argument('--no-crop', action='store_true')
    ap.add_argument('--var', help='print `const VAR = { rows, pal };` instead of a form: {...} line')
    a = ap.parse_args()
    rows, pal = grid_from_png(a.png, crop=not a.no_crop)
    h, w = len(rows), len(rows[0])
    walks = walk_rows(rows, 1) != rows
    if len(pal) > a.max_colors:
        print(f'WARN {len(pal)} colours: pixel sprites read better with a small palette (the official ones use 10-16)', file=sys.stderr)
    if w > 40 or h > 40:
        print(f'WARN {w}x{h} is very large on a 272x156 battlefield (the human hero is 12x19, the dragon 22x19)', file=sys.stderr)
    if not walks:
        print('NOTE no walk animation: leave the two middle columns empty between the legs in the bottom rows if you want one', file=sys.stderr)
    body = '{ rows: ' + json.dumps(rows, ensure_ascii=False) + ', pal: ' + json.dumps(pal) + ' }'
    print(f'const {a.var} = {body};' if a.var else 'form: { when: h => h.myid_formT > 0, rows: ' + json.dumps(rows) + ', pal: ' + json.dumps(pal) + ' },')
    if a.out:
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.with_suffix('.json').write_text(json.dumps({'rows': rows, 'pal': pal}, indent=1), 'utf-8')
        preview(rows, pal, a.scale).save(str(out) + '_preview.png')
        print(f'wrote {out.with_suffix(".json")} and {out}_preview.png ({w}x{h}, {len(pal)} colours, walk animation: {"yes" if walks else "no"})', file=sys.stderr)


if __name__ == '__main__':
    main()
