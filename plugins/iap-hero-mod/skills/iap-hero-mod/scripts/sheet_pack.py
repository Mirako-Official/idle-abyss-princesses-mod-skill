#!/usr/bin/env python3
"""Pack an effect animation into a small sprite sheet a hero mod can play (references/skill-vfx.md §6).

Input, either:
  * a pixelfx sprite sheet: the .json that `node tools/render.mjs <id> --sheet` writes next to its .png
    (https://github.com/patch-gg/pixelfx, MIT: keep its credit in your mod's README), or
  * your own frames: a folder of PNGs (sorted by name) plus --fps and --pivot.

It trims every frame to the area any frame uses, can drop frames (--every 2 halves the frame rate and the
file), and writes <mod>/fx/<name>.png plus an entry in <mod>/fx/sheets.js:
    MOD.shared.sheets = { <name>: { file, w, h, cols, frames, fps, px, py, light } }
List fx/sheets.js in mod.json "scripts" before the script that plays it (examples/stella/fx.js).

Never scale pixel art by a fraction. Pick the effect's size in pixelfx (its --opts knobs such as reach,
radius, size) so it fits the game: the battle hero is about 20 px tall, pixelfx's stand-in is 38.

Examples
  python sheet_pack.py --json records/explosions/small-explosion/small-explosion.json --mod mod --name boom --every 2 --light 40,.8,6,#ffb060
  python sheet_pack.py --frames art/fx/slash --fps 20 --pivot 24,40 --mod mod --name slash
"""
import argparse, json, re, sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit('Pillow is missing: pip install pillow')


def load_pixelfx(path):
    meta = json.loads(Path(path).read_text('utf-8'))
    sheet = Image.open(Path(path).with_name(meta['meta']['image'])).convert('RGBA')
    px = meta['meta'].get('pixelfx', {})
    frames = [sheet.crop((f['frame']['x'], f['frame']['y'], f['frame']['x'] + f['frame']['w'], f['frame']['y'] + f['frame']['h'])) for f in meta['frames']]
    fps = px.get('fps') or round(1000 / (meta['frames'][0].get('duration') or 33))
    pivot = px.get('pivot') or [frames[0].width // 2, frames[0].height]
    return frames, fps, pivot, px.get('id', Path(path).stem)


def load_folder(folder, fps, pivot):
    files = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() == '.png')
    if not files:
        sys.exit(f'no PNG frames in {folder}')
    frames = [Image.open(p).convert('RGBA') for p in files]
    if any(f.size != frames[0].size for f in frames):
        sys.exit('all frames must have the same size')
    return frames, fps, pivot, Path(folder).name


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--json', help='pixelfx sheet JSON (from render.mjs --sheet)')
    src.add_argument('--frames', help='folder of PNG frames')
    ap.add_argument('--fps', type=float, help='frames per second (needed with --frames)')
    ap.add_argument('--pivot', help='x,y of the anchor in the frame: feet / point of impact (needed with --frames)')
    ap.add_argument('--mod', required=True, help='mod folder (the one with mod.json)')
    ap.add_argument('--name', required=True, help='sheet name used in code, e.g. boom (letters, digits, _)')
    ap.add_argument('--every', type=int, default=1, help='keep every Nth frame (2 = half the frames and fps)')
    ap.add_argument('--start', type=int, default=0, help='skip this many frames at the start (a wind-up you play yourself)')
    ap.add_argument('--secs', type=float, help='cut the effect after this many seconds (long smoke tails); the last 0.3 s fade out')
    ap.add_argument('--cols', type=int, default=0, help='columns in the packed sheet (default: about square)')
    ap.add_argument('--light', help='glow while it plays: radius,strength,lift,#colour (e.g. 40,.8,6,#ffb060)')
    ap.add_argument('--alpha', type=int, default=8, help='pixels with alpha below this count as empty when trimming')
    opt = ap.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_]{1,32}', opt.name):
        sys.exit('--name: letters, digits and _ only')

    if opt.json:
        frames, fps, pivot, src_id = load_pixelfx(opt.json)
    else:
        if not opt.fps or not opt.pivot:
            sys.exit('--frames needs --fps and --pivot')
        frames, fps, pivot, src_id = load_folder(opt.frames, opt.fps, [int(v) for v in opt.pivot.split(',')])
    frames = frames[opt.start::max(1, opt.every)]
    fps = fps / max(1, opt.every)
    if opt.secs and len(frames) > opt.secs * fps:
        frames = frames[:max(1, int(opt.secs * fps))]
        n_fade = max(1, round(.3 * fps))
        for i in range(max(0, len(frames) - n_fade), len(frames)):
            k = (len(frames) - i) / (n_fade + 1)
            a = frames[i].getchannel('A').point(lambda v, k=k: int(v * k))
            frames[i] = frames[i].copy(); frames[i].putalpha(a)
    # drop the empty tail (pixelfx one-shots end on an empty frame), keep one
    while len(frames) > 1 and frames[-1].getchannel('A').point(lambda a: 255 if a >= opt.alpha else 0).getbbox() is None:
        frames.pop()
    box = None
    for f in frames:
        b = f.getchannel('A').point(lambda a: 255 if a >= opt.alpha else 0).getbbox()
        if b:
            box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    if box is None:
        sys.exit('every frame is empty')
    frames = [f.crop(box) for f in frames]
    w, h = frames[0].size
    cols = opt.cols or max(1, round((len(frames) * h / w) ** .5))
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new('RGBA', (cols * w, rows * h), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.paste(f, ((i % cols) * w, (i // cols) * h))
    mod = Path(opt.mod)
    if not (mod / 'mod.json').is_file():
        sys.exit(f'{mod} has no mod.json')
    (mod / 'fx').mkdir(exist_ok=True)
    out = mod / 'fx' / f'{opt.name}.png'
    sheet.save(out, optimize=True)
    entry = {'file': f'fx/{opt.name}.png', 'w': w, 'h': h, 'cols': cols, 'frames': len(frames), 'fps': round(fps, 3),
             'px': pivot[0] - box[0], 'py': pivot[1] - box[1], 'src': src_id}
    if opt.light:
        r, s, lift, col = opt.light.split(',')
        entry['light'] = [float(r), float(s), float(lift), col]
    reg = mod / 'fx' / 'sheets.js'
    sheets = {}
    if reg.is_file():
        m = re.search(r'Object\.assign\(MOD\.shared\.sheets \|\| \{\}, (\{.*\})\);', reg.read_text('utf-8'), re.S)
        if m:
            sheets = json.loads(m.group(1))
    sheets[opt.name] = entry
    reg.write_text("'use strict';\n/* Generated by scripts/sheet_pack.py: sprite-sheet effects this mod plays (fx.js). */\n"
                   f"MOD.shared.sheets = Object.assign(MOD.shared.sheets || {{}}, {json.dumps(sheets, ensure_ascii=False, indent=1)});\n", 'utf-8')
    kb = out.stat().st_size / 1024
    print(f'{out}: {len(frames)} frames of {w}x{h} at {entry["fps"]} fps ({len(frames) / fps:.2f} s), pivot ({entry["px"]}, {entry["py"]}), {kb:.0f} KB')
    print(f'{reg}: {", ".join(sheets)}')
    if w > 160 or h > 120:
        print(f'note: {w}x{h} is large next to a ~20 px hero; the battle field is 272x156. Make the effect smaller in pixelfx (--opts) rather than scaling it.')
    if kb > 400:
        print('note: over 400 KB; try --every 2 or a shorter effect.')
    if not any(s.endswith('fx/sheets.js') for s in json.loads((mod / 'mod.json').read_text('utf-8-sig')).get('scripts', [])):
        print('add "fx/sheets.js" to mod.json "scripts", before the script that plays the sheet')


if __name__ == '__main__':
    main()
