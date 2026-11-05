#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Mirako
"""Make the Steam Workshop preview image of a hero mod: 640 x 640 JPG under 1 MB, no text
(the Workshop grid shows the title under it anyway). Portrait on the left, optional chibi doll on the
right, on a vertical gradient with a soft rim light so dark outfits do not melt into the background.

  python make_preview.py --portrait art/portrait/t0_idle.png [--doll MOD/chibi/doll.webp]
                         [--top #163a70 --bottom #040a1a] [--out MOD/preview.jpg]

Put the file in the mod folder as preview.jpg: the in-game uploader picks it up and does not upload
it as mod content. Needs Python 3 and Pillow.
"""
import argparse, random, sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    sys.exit('make_preview.py needs Pillow:  pip install pillow')

S = 640


def rgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def background(top, bottom, seed):
    im = Image.new('RGB', (S, S)); d = ImageDraw.Draw(im)
    for y in range(S):
        k = (y / (S - 1)) ** .8
        d.line([(0, y), (S, y)], fill=tuple(round(top[i] * (1 - k) + bottom[i] * k) for i in range(3)))
    im = im.convert('RGBA'); rnd = random.Random(seed)
    rays = Image.new('RGBA', (S, S), (0, 0, 0, 0)); rd = ImageDraw.Draw(rays)
    for _ in range(4):
        x0, w = rnd.uniform(40, 560), rnd.uniform(40, 90)
        rd.polygon([(x0, -10), (x0 + w, -10), (x0 + w + 160, S), (x0 + 60, S)], fill=(255, 255, 255, rnd.randint(14, 24)))
    im.alpha_composite(rays.filter(ImageFilter.GaussianBlur(18)))
    return im


def trim(im):
    box = im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()
    if not box: sys.exit('an input image is empty or fully transparent')
    return im.crop(box)


def fit_h(im, h): return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


def glow(dst, im, xy, col, a, r):
    m = Image.new('L', (S, S), 0); m.paste(im.getchannel('A'), xy)
    m = m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(r)).point(lambda v: v * a // 255)
    g = Image.new('RGBA', (S, S), (0, 0, 0, 0)); g.paste(Image.new('RGBA', (S, S), col + (255,)), (0, 0), m); dst.alpha_composite(g)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--portrait', required=True); ap.add_argument('--doll')
    ap.add_argument('--top', default='#163a70'); ap.add_argument('--bottom', default='#040a1a'); ap.add_argument('--rim', default='#8cc8ff')
    ap.add_argument('--seed', type=int, default=5); ap.add_argument('--out', default='preview.jpg')
    a = ap.parse_args()
    im = background(rgb(a.top), rgb(a.bottom), a.seed); rim = rgb(a.rim)
    por = fit_h(trim(Image.open(a.portrait).convert('RGBA')), 626)
    cx = 232 if a.doll else S // 2
    pxy = (max(-20, cx - por.width // 2), S - por.height); glow(im, por, pxy, rim, 150, 10); im.alpha_composite(por, pxy)
    if a.doll:
        doll = fit_h(trim(Image.open(a.doll).convert('RGBA')), 300)
        sh = Image.new('RGBA', (S, S), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse([425, 612, 585, 636], fill=(0, 0, 0, 110))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
        dxy = (505 - doll.width // 2, 626 - doll.height); glow(im, doll, dxy, rim, 120, 8); im.alpha_composite(doll, dxy)
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    for q in (90, 82, 74):
        im.convert('RGB').save(out, quality=q, optimize=True)
        if out.stat().st_size < 1024 * 1024: break
    print(out, out.stat().st_size // 1024, 'KB')


if __name__ == '__main__':
    main()
