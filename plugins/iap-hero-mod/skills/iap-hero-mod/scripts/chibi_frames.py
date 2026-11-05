#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Mirako
"""Turn ONE chibi character image into the battle sprite atlas of an Idle Abyss Princesses hero mod.

Writes <MOD_DIR>/chibi/:  manifest.json, <anim>_x<scale>.webp (frames side by side),
doll.webp (static big picture for the character page).

The master is treated as a paper puppet: head (with ponytail) rotates around the neck and nods,
torso swells when breathing, the two legs lift separately below the hem (robes that hide the legs
do not lift), then a whole-body transform (hop, lean, squash and stretch) is layered on top. Every
frame is resampled from the master by inverse mapping, so frames are consistent and do not flicker.
Each scale is shrunk with LANCZOS in premultiplied alpha, then gets a 1 px dark outline.

The character must face RIGHT (use --flip otherwise). Needs only Python 3, Pillow (with WebP) and numpy.

  python chibi_frames.py MASTER.png MOD_DIR [--scales 2,3,4,6] [--flip] [--hc 24]
                         [--bg auto|none|#rrggbb] [--preview out.png]
                         [--clean-r 6] [--keep .002] [--neck .5] [--no-legs]
"""
import argparse, json, math, sys
from collections import deque
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit('chibi_frames.py needs Pillow and numpy:  pip install pillow numpy')

WORK = 600            # working resolution while deforming (character height in pixels)
DOLL_H = 378          # doll height in physical pixels (63 CSS px x 6)
QUALITY = 95
ANIM_LIST = ('idle', 'walk', 'attack', 'cast', 'hurt')


# ---------- small image-morphology toolkit (numpy only, replaces scipy.ndimage) ----------
def disk_offsets(r):
    return [(dy, int(math.floor(math.sqrt(r * r - dy * dy)))) for dy in range(-r, r + 1)]


def _hdilate(m, w):
    """Horizontal dilation by +-w using a running sum."""
    if w == 0:
        return m
    p = np.pad(m.astype(np.int32), ((0, 0), (w + 1, w)))
    c = np.cumsum(p, axis=1)
    return (c[:, 2 * w + 1:] - c[:, :-(2 * w + 1)]) > 0


def dilate_disk(m, r):
    if r <= 0:
        return m.copy()
    out = np.zeros_like(m, dtype=bool)
    H = m.shape[0]
    for dy, w in disk_offsets(r):
        h = _hdilate(m, w)
        if dy >= 0:
            out[dy:] |= h[:H - dy]
        else:
            out[:H + dy] |= h[-dy:]
    return out


def erode_disk(m, r):
    return ~dilate_disk(~m, r)


def open_disk(m, r):
    return dilate_disk(erode_disk(m, r), r)


def dilate_cross(m):
    o = m.copy()
    o[1:] |= m[:-1]; o[:-1] |= m[1:]; o[:, 1:] |= m[:, :-1]; o[:, :-1] |= m[:, 1:]
    return o


def label(m):
    """4-connected component labelling. Returns (labels, count); labels are 1..count, 0 = background."""
    H, W = m.shape
    lab = np.zeros((H, W), np.int32)
    flat_m = m.ravel()
    flat_l = lab.ravel()
    n = 0
    for start in np.flatnonzero(flat_m):
        if flat_l[start]:
            continue
        n += 1
        flat_l[start] = n
        q = deque([start])
        while q:
            i = q.popleft()
            y, x = divmod(i, W)
            for j, ok in ((i - W, y > 0), (i + W, y < H - 1), (i - 1, x > 0), (i + 1, x < W - 1)):
                if ok and flat_m[j] and not flat_l[j]:
                    flat_l[j] = n
                    q.append(j)
    return lab, n


def gaussian(a, sigma):
    r = max(1, int(4 * sigma + .5))
    x = np.arange(-r, r + 1)
    k = np.exp(-x * x / (2 * sigma * sigma)); k /= k.sum()
    for ax in (0, 1):
        p = np.pad(a, [(r, r) if i == ax else (0, 0) for i in range(2)], mode='constant')
        a = sum(k[i] * np.take(p, range(i, i + a.shape[ax]), axis=ax) for i in range(len(k)))
    return a.astype(np.float32)


def smooth(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def sample_bilinear(img, QX, QY):
    """Bilinear sampling of img (H,W,C) at float coords, zero outside (like map_coordinates mode=constant)."""
    H, W = img.shape[:2]
    p = np.pad(img, ((1, 1), (1, 1), (0, 0)))
    x = np.clip(QX + 1, 0, W + 1 - 1e-3); y = np.clip(QY + 1, 0, H + 1 - 1e-3)
    x0 = np.floor(x).astype(np.int32); y0 = np.floor(y).astype(np.int32)
    fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    return (p[y0, x0] * (1 - fx) * (1 - fy) + p[y0, x0 + 1] * fx * (1 - fy)
            + p[y0 + 1, x0] * (1 - fx) * fy + p[y0 + 1, x0 + 1] * fx * fy)


# ---------- input handling ----------
def key_background(rgba, bg):
    """Make a flat background transparent. bg: 'auto' (corner colour) or '#rrggbb'."""
    if bg == 'auto':
        c = rgba[[0, 0, -1, -1], [0, -1, 0, -1], :3].astype(int)
        col = np.median(c, axis=0)
        if np.abs(c - col).max() > 24:
            sys.exit('error: --bg auto: the four corners are not one flat colour; pass --bg #rrggbb')
    else:
        h = bg.lstrip('#')
        if len(h) != 6:
            sys.exit('error: --bg must be auto, none or #rrggbb')
        col = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)])
    d = np.abs(rgba[..., :3].astype(int) - col).max(-1)
    # flood from the border so inner colours matching the background survive
    cand = d <= 28
    lab, n = label(cand)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bgm = np.isin(lab, list(border))
    out = rgba.copy()
    soft = np.clip((d - 18) / 30.0, 0, 1)                      # soften the fringe next to the keyed area
    edge = dilate_cross(bgm) & ~bgm
    out[bgm, 3] = 0
    out[edge, 3] = np.minimum(out[edge, 3], np.round(soft[edge] * 255)).astype(np.uint8)
    return out


def load_master(path, bg, flip):
    try:
        im = Image.open(path)
    except Exception as e:
        sys.exit(f'error: cannot open {path}: {e}')
    has_alpha = im.mode in ('RGBA', 'LA', 'PA') or 'transparency' in im.info
    rgba = np.asarray(im.convert('RGBA')).copy()
    if bg != 'none':
        rgba = key_background(rgba, bg)
    elif not has_alpha or rgba[..., 3].min() == 255:
        sys.exit('error: the image has no transparency. Use a PNG with a transparent background, '
                 'or pass --bg auto (corner colour) / --bg #rrggbb to key out a flat background.')
    if (rgba[..., 3] > 8).sum() < 100:
        sys.exit('error: the image is empty (almost nothing is opaque).')
    if flip:
        rgba = rgba[:, ::-1].copy()
    return rgba


def clean(rgba, r=6, keep=.002):
    """Drop wisps and isolated specks along the edge of the cut-out (same idea as the official tool)."""
    a = rgba[..., 3].astype(np.float32) / 255
    lab, n = label(a > .5)
    if n == 0:
        sys.exit('error: the image is empty after thresholding alpha.')
    sizes = np.bincount(lab.ravel(), minlength=n + 1)[1:].astype(float)
    main = int(np.argmax(sizes)) + 1
    if r > 0:
        core = open_disk(lab == main, r)
        lab2, n2 = label(core)
        if n2:
            s2 = np.bincount(lab2.ravel(), minlength=n2 + 1)[1:]
            core = np.isin(lab2, [i + 1 for i, v in enumerate(s2) if v >= .01 * s2.max()])
        else:
            core = lab == main
    else:
        core = lab == main
    w = np.clip(gaussian(dilate_disk(core, 9).astype(np.float32), 1.2) * 1.15, 0, 1)
    parts = np.isin(lab, [i + 1 for i, v in enumerate(sizes) if i + 1 != main and v >= keep * sizes.max()])
    if parts.any():
        w = np.maximum(w, np.clip(gaussian(dilate_disk(parts, 3).astype(np.float32), 1) * 1.2, 0, 1))
    out = rgba.copy()
    out[..., 3] = np.round(a * w * 255).astype(np.uint8)
    return out


def landmarks(a, neck=.5, legs=True):
    """Feet, leg split, hem (where the legs start to part) and neck height. a: 0..1 alpha, cropped."""
    m = a > .5
    ys, xs = np.where(m)
    top, bot = ys.min(), ys.max()
    H = bot - top
    band = m[int(bot - .16 * H):bot + 1]
    col = band.sum(0).astype(float)
    cx0 = (col * np.arange(len(col))).sum() / col.sum()
    lo, hi = max(0, int(cx0 - .09 * H)), min(len(col), int(cx0 + .09 * H))
    seg = col[lo:hi]
    if len(seg) < 12:
        split = int(cx0)
    else:
        sm = np.convolve(np.pad(seg, (4, 4), mode='edge'), np.ones(9) / 9, mode='valid')
        split = lo + int(np.argmin(sm))
    gap = m[:, max(0, split - 4):split + 5].any(1)
    hem = bot
    while hem > top and not gap[hem]:
        hem -= 1
    # robes that hide the legs: the parted part is too short, so no leg lifting
    legs = legs and (bot - hem) >= .06 * H
    if not legs:
        hem = bot
    return dict(top=int(top), bot=int(bot), H=int(H), split=int(split), hem=int(hem),
                neck=int(top + neck * H), cx=float(split if legs else cx0), legs=bool(legs))


def premul(rgba):
    f = rgba.astype(np.float32) / 255
    f[..., :3] *= f[..., 3:4]
    return f


def unpremul(f):
    out = f.copy()
    a = out[..., 3:4]
    out[..., :3] = np.where(a > 1e-4, out[..., :3] / np.maximum(a, 1e-4), 0)
    return np.clip(np.round(out * 255), 0, 255).astype(np.uint8)


# ---------- paper-puppet deformation ----------
class Puppet:
    def __init__(self, rgba, lm, canvas, origin):
        self.src = premul(rgba)
        self.lm = lm
        self.FW, self.FH = canvas
        self.ox, self.oy = origin

    def local(self, X, Y, p):
        lm = self.lm
        dx = np.zeros_like(X); dy = np.zeros_like(Y)
        bump = smooth(lm['neck'] - .05 * lm['H'], lm['neck'] + .1 * lm['H'], Y) * (1 - smooth(lm['hem'] - .15 * lm['H'], lm['hem'], Y))
        dx += (X - lm['cx']) * p.get('chest', 0) * bump
        up = 1 - smooth(lm['hem'] - .04 * lm['H'], lm['hem'] + .02 * lm['H'], Y)
        dy += (lm['hem'] - Y) * p.get('sink', 0) * up
        wh = 1 - smooth(lm['neck'] - .06 * lm['H'], lm['neck'] + .1 * lm['H'], Y)
        th = math.radians(p.get('head', 0))
        px_, py_ = lm['cx'], lm['neck']
        rx = px_ + math.cos(th) * (X - px_) - math.sin(th) * (Y - py_)
        ry = py_ + math.sin(th) * (X - px_) + math.cos(th) * (Y - py_)
        dx += wh * (rx - X)
        dy += wh * (ry - Y + p.get('heady', 0) * lm['H'])
        if not lm['legs']:
            return dx, dy
        wl = smooth(lm['hem'], lm['hem'] + .55 * (lm['bot'] - lm['hem']), Y)
        left = X < lm['split']
        lift = np.where(left, p.get('liftL', 0), p.get('liftR', 0)) * lm['H']
        fwd = np.where(left, p.get('fwdL', 0), p.get('fwdR', 0)) * lm['H']
        dx += wl * fwd
        dy -= wl * lift
        return dx, dy

    def frame(self, p):
        lm = self.lm
        Yc, Xc = np.mgrid[0:self.FH, 0:self.FW].astype(np.float32)
        X = Xc - self.ox; Y = Yc - self.oy
        fx, fy = lm['cx'], float(lm['bot'])
        X = X - p.get('tx', 0) * lm['H']; Y = Y - p.get('ty', 0) * lm['H']
        a = -math.radians(p.get('tilt', 0))
        dx_, dy_ = X - fx, Y - fy
        X = fx + math.cos(a) * dx_ - math.sin(a) * dy_
        Y = fy + math.sin(a) * dx_ + math.cos(a) * dy_
        sy = p.get('sy', 1); sx = p.get('sx', 1 / math.sqrt(sy))
        X = fx + (X - fx) / sx; Y = fy + (Y - fy) / sy
        QX, QY = X.copy(), Y.copy()
        for _ in range(4):                       # inverse of the local displacement: fixed-point iteration
            ddx, ddy = self.local(QX, QY, p)
            QX, QY = X - ddx, Y - ddy
        return sample_bilinear(self.src, QX, QY)


def ease(t):
    return .5 - .5 * math.cos(math.pi * min(1, max(0, t)))


def keyed(keys, t):
    for (t0, k0), (t1, k1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = ease((t - t0) / (t1 - t0))
            base = {'sy': 1}
            return {n: k0.get(n, base.get(n, 0)) * (1 - u) + k1.get(n, base.get(n, 0)) * u for n in set(k0) | set(k1)}
    return dict(keys[-1][1])


def anim_idle(i, n):
    ph = 2 * math.pi * i / n
    b = .5 - .5 * math.cos(ph)
    return {'sink': .022 * b, 'chest': .018 * b, 'heady': .006 * math.sin(ph - .9),
            'head': 1.6 * math.sin(ph - .5), 'sy': 1 - .006 * b, 'sx': 1 + .004 * b}


def anim_walk(i, n):
    ph = 2 * math.pi * i / n
    s = math.sin(ph)
    hop = abs(s)
    land = (1 - hop) ** 3
    return {'ty': -.05 * hop, 'sy': 1 - .045 * land + .02 * hop, 'sx': 1 + .03 * land,
            'tilt': 5 + 2.5 * s, 'head': -3 * s + 1.5, 'heady': .01 * land,
            'liftL': .055 * max(0, s), 'liftR': .055 * max(0, -s),
            'fwdL': .02 * max(0, s), 'fwdR': .02 * max(0, -s), 'sink': .01 * land}


ATTACK = [(0, {}),
          (.22, {'tilt': -9, 'tx': -.03, 'sy': .94, 'head': -4, 'sink': .02}),
          (.45, {'tilt': 13, 'tx': .07, 'ty': -.015, 'sy': 1.05, 'head': 6, 'liftR': .04}),
          (.7, {'tilt': 9, 'tx': .05, 'sy': .97, 'head': 3}),
          (1, {})]
CAST = [(0, {}),
        (.25, {'tilt': -5, 'tx': -.015, 'sy': .97, 'head': -2, 'sink': .015}),
        (.45, {'tilt': 7, 'tx': .03, 'sy': 1.03, 'head': 3}),
        (.7, {'tilt': -3, 'tx': -.01, 'sy': .99, 'head': -1}),
        (1, {})]
HURT = [(0, {}), (.25, {'tilt': -11, 'tx': -.04, 'sy': .95, 'head': -7, 'heady': .01}),
        (.6, {'tilt': -5, 'tx': -.02, 'sy': .99, 'head': -2}), (1, {})]
# durations match the game: basic swing .22 s, hurt .3 s
ANIMS = {
    'idle': dict(n=12, dur=1.5, loop=True, fn=anim_idle),
    'walk': dict(n=8, dur=.5, loop=True, fn=anim_walk),
    'attack': dict(n=8, dur=.22, loop=False, fn=lambda i, n: keyed(ATTACK, i / (n - 1))),
    'cast': dict(n=8, dur=.22, loop=False, fn=lambda i, n: keyed(CAST, i / (n - 1))),
    'hurt': dict(n=6, dur=.3, loop=False, fn=lambda i, n: keyed(HURT, i / (n - 1))),
}


# ---------- output ----------
def shrink(f, w, h):
    """Premultiplied float frame -> RGBA of the target size (LANCZOS in premultiplied alpha, no halos)."""
    im = Image.fromarray(unpremul(f), 'RGBA').convert('RGBa')
    return im.resize((w, h), Image.LANCZOS, reducing_gap=3.0).convert('RGBA')


def outline(im, rgb=(26, 14, 20), alpha=200, thr=60):
    """1 px dark outline so the sprite stands out from the ground at small sizes."""
    a = np.asarray(im)
    m = a[..., 3] > thr
    ring = dilate_cross(m) & ~m
    base = np.zeros_like(a)
    base[ring] = (*rgb, alpha)
    out = Image.fromarray(base, 'RGBA')
    out.alpha_composite(im)
    return out


def build(rgba, mod_dir, scales, hc, clean_r, keep, neck, legs, preview):
    rgba = clean(rgba, clean_r, keep)
    ys, xs = np.where(rgba[..., 3] > 8)
    rgba = rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    lm0 = landmarks(rgba[..., 3] / 255, neck, legs)
    s0 = WORK / lm0['H']
    im = Image.fromarray(rgba, 'RGBA').convert('RGBa')
    im = im.resize((max(1, round(im.width * s0)), max(1, round(im.height * s0))), Image.LANCZOS).convert('RGBA')
    master = np.asarray(im)
    lm = landmarks(master[..., 3] / 255, neck, legs)
    Hh = lm['H']
    mx, mt, mb = int(.32 * Hh), int(.12 * Hh), int(.03 * Hh)
    FW, FH = master.shape[1] + 2 * mx, master.shape[0] + mt + mb
    pup = Puppet(master, lm, (FW, FH), (mx, mt))
    frames = {name: [pup.frame(d['fn'](i, d['n'])) for i in range(d['n'])] for name, d in ANIMS.items()}
    union = np.zeros((FH, FW), bool)           # one crop box for all frames: the feet never jump between animations
    for fs in frames.values():
        for f in fs:
            union |= f[..., 3] > 1 / 255
    uy, ux = np.where(union)
    x0, x1, y0, y1 = max(0, ux.min() - 3), min(FW, ux.max() + 4), max(0, uy.min() - 3), min(FH, uy.max() + 4)
    ax, ay = mx + lm['cx'] - x0, mt + lm['bot'] - y0
    d = Path(mod_dir) / 'chibi'
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob('*.webp'):
        old.unlink()
    man = {'ext': 'webp', 'sheet': False, 'hc': hc, 'scales': {},
           'anims': {n: dict(n=a['n'], dur=a['dur'], loop=a['loop']) for n, a in ANIMS.items()}}
    prev = {}
    for k in scales:
        sc = hc * k / Hh
        w, h = max(1, round((x1 - x0) * sc)), max(1, round((y1 - y0) * sc))
        for name, fs in frames.items():
            sheet = Image.new('RGBA', (w * len(fs), h))
            for i, f in enumerate(fs):
                sheet.paste(outline(shrink(f[y0:y1, x0:x1], w, h)), (i * w, 0))
            sheet.save(d / f'{name}_x{k}.webp', 'WEBP', quality=QUALITY, method=6)
            if k == 4:
                prev[name] = sheet
        man['scales'][str(k)] = dict(fw=w, fh=h, ax=round(ax * w / (x1 - x0), 2), ay=round(ay * h / (y1 - y0), 2))
    my, mxs = np.where(master[..., 3] > 8)
    crop = master[my.min():my.max() + 1, mxs.min():mxs.max() + 1]
    dw = round(crop.shape[1] * DOLL_H / crop.shape[0])
    shrink(premul(crop), dw, DOLL_H).save(d / 'doll.webp', 'WEBP', quality=QUALITY, method=6)
    man['doll'] = [dw, DOLL_H]
    (d / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n', 'utf8')
    if preview:
        write_preview(prev, preview, man['scales'].get('4'))
    return man, lm


def write_preview(prev, path, s4):
    if not prev:
        print('preview skipped: scale 4 not requested')
        return
    names = [n for n in ANIM_LIST if n in prev]
    W = max(p.width for p in prev.values()); h = s4['fh']
    pad = 6
    sheet = Image.new('RGBA', (W + 2 * pad, len(names) * (h + pad) + pad), (0, 0, 0, 255))
    yy, xx = np.mgrid[0:sheet.height, 0:sheet.width]
    chk = (((yy // 8) + (xx // 8)) % 2).astype(np.uint8)
    bg = np.where(chk[..., None] == 1, np.array([46, 44, 56, 255]), np.array([34, 32, 42, 255])).astype(np.uint8)
    sheet = Image.fromarray(bg, 'RGBA')
    for r, n in enumerate(names):
        y = pad + r * (h + pad)
        sheet.alpha_composite(prev[n], (pad, y))
        # foot anchor guide
        for x in range(pad, pad + prev[n].width, s4['fw']):
            ax = x + int(round(s4['ax'])); ay = y + int(round(s4['ay']))
            if ay < sheet.height and ax < sheet.width:
                sheet.putpixel((ax, ay), (255, 60, 60, 255))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sheet.convert('RGB').save(path)


def main():
    ap = argparse.ArgumentParser(description='Chibi image -> IAP hero mod battle atlas (chibi/).')
    ap.add_argument('master', help='character image, facing right, transparent background')
    ap.add_argument('mod_dir', help='mod folder; files go to <mod_dir>/chibi/')
    ap.add_argument('--scales', default='2,3,4,6', help='comma list of atlas scales (default 2,3,4,6)')
    ap.add_argument('--flip', action='store_true', help='mirror the image (it faces left)')
    ap.add_argument('--hc', type=int, default=24, help='character height in game pixels (default 24)')
    ap.add_argument('--bg', default='none', help='none (default) | auto (corner colour) | #rrggbb: key out a flat background')
    ap.add_argument('--preview', metavar='PNG', help='write a contact sheet of all frames at x4')
    ap.add_argument('--clean-r', type=int, default=6, help='speck cleanup radius; use 2 for thin weapons (default 6, 0 = off)')
    ap.add_argument('--keep', type=float, default=.002, help='keep detached parts bigger than this fraction of the body (default .002)')
    ap.add_argument('--neck', type=float, default=.5, help='neck height as a fraction of the figure from the top (default .5)')
    ap.add_argument('--no-legs', action='store_true', help='never lift legs (robes, ghosts)')
    a = ap.parse_args()
    try:
        scales = sorted({int(x) for x in a.scales.split(',') if x.strip()})
    except ValueError:
        sys.exit('error: --scales must be integers like 2,3,4,6')
    if not scales or any(s < 1 or s > 8 for s in scales):
        sys.exit('error: --scales values must be 1..8')
    if not (8 <= a.hc <= 64):
        sys.exit('error: --hc must be between 8 and 64')
    rgba = load_master(a.master, a.bg, a.flip)
    man, lm = build(rgba, a.mod_dir, scales, a.hc, a.clean_r, a.keep, a.neck, not a.no_legs, a.preview)
    out = Path(a.mod_dir) / 'chibi'
    kb = sum(f.stat().st_size for f in out.glob('*.webp')) // 1024
    top = str(max(scales))
    s = man['scales'][top]
    print(f'wrote {out}  ({len(list(out.glob("*.webp")))} webp + manifest.json, {kb} KB)')
    print(f'legs: {"lifted" if lm["legs"] else "not lifted"}; scales {",".join(map(str, scales))}; '
          f'frame {s["fw"]}x{s["fh"]} at x{top}; anchor ({s["ax"]}, {s["ay"]}); doll {man["doll"][0]}x{man["doll"][1]}')
    if a.preview:
        print(f'preview: {a.preview}')


if __name__ == '__main__':
    main()
