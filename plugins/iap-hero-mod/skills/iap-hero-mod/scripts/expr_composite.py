#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Mirako
"""Paste only the changed FACE of an edited image back onto the master portrait.

Image models asked to "change only the expression" usually also nudge the hair, the outfit, the line
weight or the whole picture by a few pixels. Portraits switch expressions in place, so any drift shows
as a jump. This keeps the master everywhere except where the face really changed:

  1. look only inside the head window (default: the top 22 % of the figure, as wide as the hair there),
     and only inside an ellipse around the face (--face X,Y and --radius, or the middle of the head window),
     so slightly redrawn hair edges, ribbons or a raised hand keep the master's pixels
  2. find the small shift (up to --search px) that best aligns the edit with the master in that window
  3. mask = pixels whose colour changed by more than --threshold, cleaned (opening + closing),
     grown by --grow px and feathered by --feather px
  4. out = master * (1 - mask) + shifted edit * mask   (alpha included)

  python expr_composite.py MASTER.png EDITED.png OUT.png [--face 520,250 --radius 110] [--head x0,y0,x1,y1] [--threshold 28]
                           [--grow 8] [--feather 5] [--search 8] [--mask-out mask.png] [--preview check.png]

Check the preview: the red overlay is what was taken from the edit. If it covers too little (eyes
missing) lower --threshold or raise --radius / --grow; if it eats hair or outfit, give --face and a smaller --radius.
Needs Python 3, Pillow and numpy.
"""
import argparse, sys

try:
    import numpy as np
    from PIL import Image, ImageFilter
except ImportError:
    sys.exit('expr_composite.py needs Pillow and numpy:  pip install pillow numpy')


def head_window(alpha):
    fg = alpha > 16; ys, xs = np.nonzero(fg)
    if not len(ys): sys.exit('the master image is empty (no opaque pixels)')
    top = int(ys.min()); h = int(ys.max()) - top
    band = max(1, int(h * .22)); cols = np.nonzero(fg[top:top + band].any(axis=0))[0]
    cx = float(np.median(cols)); hw = float(cols.max() - cols.min() + 1)
    return int(max(0, cx - hw * .5)), top, int(min(alpha.shape[1], cx + hw * .5)), int(min(alpha.shape[0], top + band * 1.5))


def best_shift(m, e, box, search):
    """Brute-force the integer (dx, dy) that minimises the mean colour difference inside the head box (at half size)."""
    x0, y0, x1, y1 = box
    a = m[y0:y1, x0:x1, :3].astype(np.float32)[::2, ::2]
    best, arg = None, (0, 0)
    for dy in range(-search, search + 1, 2):
        for dx in range(-search, search + 1, 2):
            ys, xs = max(0, y0 - dy), max(0, x0 - dx)
            b = e[ys:ys + (y1 - y0), xs:xs + (x1 - x0), :3].astype(np.float32)[::2, ::2]
            if b.shape != a.shape: continue
            d = np.abs(a - b).mean()
            if best is None or d < best: best, arg = d, (dx, dy)
    return arg


def shift(img, dx, dy):
    out = np.zeros_like(img); H, W = img.shape[:2]
    ys0, ys1 = max(0, dy), min(H, H + dy); xs0, xs1 = max(0, dx), min(W, W + dx)
    out[ys0:ys1, xs0:xs1] = img[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('master'); ap.add_argument('edited'); ap.add_argument('out')
    ap.add_argument('--head', help='x0,y0,x1,y1 in master pixels (default: automatic head window)')
    ap.add_argument('--face', help='X,Y face centre in master pixels (default: middle of the head window)')
    ap.add_argument('--radius', type=float, help='face radius in pixels (default: about a fifth of the head window width)')
    ap.add_argument('--threshold', type=int, default=28); ap.add_argument('--grow', type=int, default=8)
    ap.add_argument('--feather', type=float, default=5); ap.add_argument('--search', type=int, default=8)
    ap.add_argument('--mask-out'); ap.add_argument('--preview')
    a = ap.parse_args()
    M = Image.open(a.master).convert('RGBA'); E = Image.open(a.edited).convert('RGBA')
    if E.size != M.size:
        print(f'note: edit is {E.size[0]}x{E.size[1]}, master {M.size[0]}x{M.size[1]}; resizing the edit')
        E = E.resize(M.size, Image.LANCZOS)
    m = np.asarray(M).astype(np.int16); e = np.asarray(E).astype(np.int16)
    box = tuple(int(v) for v in a.head.split(',')) if a.head else head_window(m[..., 3])
    dx, dy = best_shift(m, e, box, a.search); e = shift(e, dx, dy)
    x0, y0, x1, y1 = box
    diff = np.abs(m - e).max(axis=2)
    raw = np.zeros(diff.shape, np.uint8); raw[y0:y1, x0:x1] = (diff[y0:y1, x0:x1] > a.threshold) * 255
    if a.face: fx, fy = (float(v) for v in a.face.split(',')); rx = a.radius or (x1 - x0) * .22; ry = rx * 1.25
    else: fx, fy = (x0 + x1) / 2, y0 + (y1 - y0) * .5; rx = a.radius or (x1 - x0) * .22; ry = rx * 1.25
    yy, xx = np.mgrid[0:diff.shape[0], 0:diff.shape[1]]
    raw[((xx - fx) / rx) ** 2 + ((yy - fy) / ry) ** 2 > 1] = 0      # only around the face
    mk = Image.fromarray(raw, 'L')
    mk = mk.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))            # opening: drop specks
    mk = mk.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))            # closing: fill small holes
    if a.grow: mk = mk.filter(ImageFilter.MaxFilter(2 * a.grow + 1))
    if a.feather: mk = mk.filter(ImageFilter.GaussianBlur(a.feather))
    w = np.asarray(mk).astype(np.float32)[..., None] / 255
    out = (m * (1 - w) + e * w).round().clip(0, 255).astype(np.uint8)
    Image.fromarray(out, 'RGBA').save(a.out)
    cover = float((np.asarray(mk) > 127).mean() * 100)
    print(f'{a.out}: head box {box}, edit shifted by ({dx:+d}, {dy:+d}), mask covers {cover:.1f}% of the image')
    if a.mask_out: mk.save(a.mask_out)
    if a.preview:
        pv = Image.fromarray(out, 'RGBA').convert('RGB'); red = Image.new('RGB', pv.size, (255, 40, 40))
        pv = Image.composite(Image.blend(pv, red, .45), pv, mk.point(lambda v: 255 if v > 60 else 0))
        pv.crop((max(0, x0 - 40), max(0, y0 - 40), min(pv.width, x1 + 40), min(pv.height, y1 + 40))).save(a.preview)
        print('preview', a.preview)


if __name__ == '__main__':
    main()
