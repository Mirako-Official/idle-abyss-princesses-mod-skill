#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Mirako
"""Export hero portraits for an Idle Abyss Princesses mod.

The game shows a portrait in a 120 x 192 (5:8) frame, scaled to fit and bottom-aligned. This script
crops every image of one outfit tier with the SAME 5:8 box (taken from the idle image, so expressions
line up when they switch), resizes to 450 x 720 and writes WebP files:

  MOD_DIR/portraits/t<tier>_<expr>.webp      expr: idle fight skill hurt low win down (sleep blink optional)
  MOD_DIR/portrait.webp                       the base portrait (tier 0 idle)

Why 450 x 720: the game treats a portrait whose size is an exact multiple of 120 x 192 (360 x 576,
480 x 768, ...) as upscaled PIXEL ART and shrinks it with nearest-neighbour, which looks blocky. Any
other size of 240 px width or more is drawn smoothly as a high-resolution portrait.

Missing frames fall back in the game (expression -> idle, tier -> lower tier -> portrait), so one idle
image is already a complete portrait set. Outfit tiers t1 / t2 are optional.

  python portrait_export.py MOD_DIR --idle art/t0_idle.png [--expr win=art/t0_win.png ...]
                            [--tier 0] [--face 540,250] [--bg none|auto|#rrggbb] [--pad-top .03] [--preview sheet.png]

--face X,Y  the centre of the face in the idle SOURCE image (pixels). Prints the value for
            registerHero({ face: [x, y] }) in 120 x 192 coordinates; the hero picker crops the avatar there.
--bg        remove a flat background colour connected to the image border (auto = corner colour) when
            the source has no transparency. For soft backgrounds use a real background remover first.
"""
import argparse, sys
from collections import deque
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit('portrait_export.py needs Pillow and numpy:  pip install pillow numpy')

FW, FH = 120, 192
OUT_W, OUT_H = 450, 720
EXPRS = ['idle', 'fight', 'skill', 'hurt', 'low', 'win', 'down', 'sleep', 'blink']


def key_background(im, spec):
    """Make the flat background transparent: flood-fill from the border over pixels close to the key colour."""
    a = np.asarray(im.convert('RGBA')).copy()
    if spec == 'auto':
        corners = np.array([a[0, 0, :3], a[0, -1, :3], a[-1, 0, :3], a[-1, -1, :3]], dtype=int)
        key = np.median(corners, axis=0)
    else:
        h = spec.lstrip('#'); key = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)])
    near = np.abs(a[..., :3].astype(int) - key).max(axis=2) <= 24
    H, W = near.shape; seen = np.zeros_like(near); q = deque()
    for x in range(W):
        for y in (0, H - 1):
            if near[y, x] and not seen[y, x]: seen[y, x] = True; q.append((y, x))
    for y in range(H):
        for x in (0, W - 1):
            if near[y, x] and not seen[y, x]: seen[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and near[ny, nx] and not seen[ny, nx]: seen[ny, nx] = True; q.append((ny, nx))
    a[seen, 3] = 0
    return Image.fromarray(a, 'RGBA')


def load(path, bg):
    im = Image.open(path).convert('RGBA')
    alpha = np.asarray(im)[..., 3]
    if bg != 'none': im = key_background(im, bg)
    elif alpha.min() == 255: sys.exit(f'{path}: no transparency. Remove the background first, or pass --bg auto / --bg #rrggbb')
    return im


def crop_box(im, pad_top):
    al = np.asarray(im)[..., 3]; ys, xs = np.nonzero(al > 16)
    if not len(ys): sys.exit('the idle image is empty after background removal')
    top = ys.min() - pad_top * al.shape[0]; bottom = ys.max() + 4
    cw = xs.max() - xs.min() + 1; ch = bottom - top
    w = max(cw, ch * FW / FH); h = w * FH / FW; cx = (xs.min() + xs.max()) / 2
    return int(round(cx - w / 2)), int(round(bottom - h)), int(round(cx + w / 2)), int(round(bottom))      # feet on the bottom edge


def crop_pad(im, box):
    x0, y0, x1, y1 = box
    out = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0))
    out.paste(im.crop((max(0, x0), max(0, y0), min(im.width, x1), min(im.height, y1))), (max(0, -x0), max(0, -y0)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mod_dir'); ap.add_argument('--idle', required=True)
    ap.add_argument('--expr', action='append', default=[], help='name=path, e.g. win=art/t0_win.png')
    ap.add_argument('--tier', type=int, default=0, choices=[0, 1, 2])
    ap.add_argument('--face', help='X,Y of the face centre in the idle source image')
    ap.add_argument('--bg', default='none'); ap.add_argument('--pad-top', type=float, default=.03)
    ap.add_argument('--quality', type=int, default=92); ap.add_argument('--preview')
    a = ap.parse_args()
    mod = Path(a.mod_dir); out = mod / 'portraits'; out.mkdir(parents=True, exist_ok=True)
    items = [('idle', a.idle)]
    for e in a.expr:
        if '=' not in e: sys.exit(f'--expr expects name=path, got {e}')
        k, v = e.split('=', 1)
        if k not in EXPRS: sys.exit(f'unknown expression {k}; use one of {", ".join(EXPRS)}')
        items.append((k, v))
    idle = load(a.idle, a.bg); box = crop_box(idle, a.pad_top)
    written = []
    for k, path in items:
        im = idle if k == 'idle' else load(path, a.bg)
        if im.size != idle.size:
            print(f'note: {path} is {im.size[0]}x{im.size[1]}, the idle is {idle.size[0]}x{idle.size[1]}; resizing to match (expressions should be edits of the idle image)')
            im = im.resize(idle.size, Image.LANCZOS)
        frame = crop_pad(im, box).resize((OUT_W, OUT_H), Image.LANCZOS)
        dst = out / f't{a.tier}_{k}.webp'; frame.save(dst, 'WEBP', quality=a.quality, method=6); written.append((k, frame, dst))
        if a.tier == 0 and k == 'idle': frame.save(mod / 'portrait.webp', 'WEBP', quality=a.quality, method=6)
    print(f'crop box {box} -> {OUT_W}x{OUT_H}; wrote ' + ', '.join(str(d.relative_to(mod)) for _, _, d in written) + (', portrait.webp' if a.tier == 0 else ''))
    for stray in ('portrait.png', 'portrait.jpg', 'portrait.jpeg'):
        if (mod / stray).exists(): print(f'WARNING: {stray} exists and is used before portrait.webp. Delete it if it is a template placeholder.')
    if a.face:
        fx, fy = (float(v) for v in a.face.split(','))
        s = FW / (box[2] - box[0])
        print(f'face: [{round((fx - box[0]) * s)}, {round((fy - box[1]) * s)}]   (put this in registerHero)')
    if a.preview:
        tiles = [f for _, f, _ in written]; W = len(tiles) * (OUT_W // 2 + 8) + 8
        sheet = Image.new('RGBA', (W, OUT_H // 2 + 16), (34, 26, 40, 255)); x = 8
        for t in tiles:
            sheet.alpha_composite(t.resize((OUT_W // 2, OUT_H // 2), Image.LANCZOS), (x, 8)); x += OUT_W // 2 + 8
        if a.face:
            d = ImageDraw.Draw(sheet); px, py = 8 + (fx - box[0]) * (OUT_W // 2) / (box[2] - box[0]), 8 + (fy - box[1]) * (OUT_H // 2) / (box[3] - box[1])
            d.ellipse([px - 5, py - 5, px + 5, py + 5], outline=(255, 70, 70, 255), width=2)
        sheet.convert('RGB').save(a.preview); print('preview', a.preview)


if __name__ == '__main__':
    main()
