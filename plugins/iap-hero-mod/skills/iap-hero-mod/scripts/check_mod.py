#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Mirako
"""Static checks for an Idle Abyss Princesses hero mod folder, before you test it in the game or upload it.

  python check_mod.py MOD_DIR

Catches the mistakes that do not show up as errors in the game but still ship broken:
portraits that get pixelated, placeholder images that win over the real ones, chibi atlases whose
frame sizes do not match the images, legend / set keys without the mod id prefix, descriptions the game
truncates, a preview image over the Workshop limit, symlinks the uploader refuses. Exit code 1 if
there is an ERROR. It does not run your code: test in the game afterwards.
"""
import json, re, sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit('check_mod.py needs Pillow:  pip install pillow')

ID_RE = re.compile(r'^[a-z][a-z0-9_]{1,31}$')
EXPRS = {'idle', 'fight', 'skill', 'hurt', 'low', 'win', 'down', 'sleep', 'blink'}
IMG = ('.png', '.webp', '.jpg', '.jpeg')
out = {'ERROR': 0, 'WARN': 0}


def say(level, msg):
    if level in out: out[level] += 1
    print(f'{level:5} {msg}')


def texts(v):
    return v.items() if isinstance(v, dict) else [('zh', v)] if isinstance(v, str) else []


def check_manifest(mod):
    p = mod / 'mod.json'
    if not p.exists(): say('ERROR', 'mod.json is missing'); return None
    try: m = json.loads(p.read_text('utf-8-sig'))
    except Exception as e: say('ERROR', f'mod.json is not valid JSON: {e}'); return None
    mid = m.get('id', '')
    if not ID_RE.match(str(mid)): say('ERROR', f'id {mid!r}: lowercase letters, digits and _, 2-32 characters, starting with a letter')
    if mod.name not in (mid, 'mod'): print(f'note  folder name {mod.name!r} differs from id {mid!r}: install it as mods/{mid}/')
    for lang, s in texts(m.get('name')):
        if len(s) > 40: say('ERROR', f'name[{lang}] is {len(s)} characters; the game cuts it at 40')
    for lang, s in texts(m.get('description')):
        if len(s) > 300: say('ERROR', f'description[{lang}] is {len(s)} characters; the game cuts it at 300 (keep the credits inside the limit)')
    if not m.get('description'): say('WARN', 'no description: say what the hero is, and credit the art')
    api = m.get('api', 1)
    if api < 2: say('WARN', f'api {api}: use 3 for MOD.data, MOD.files, IAP.onReady / IAP.ui and IAP.ai')
    scripts = m.get('scripts', ['main.js'])
    total = 0
    for s in scripts:
        f = mod / s
        if not f.exists(): say('ERROR', f'script {s} listed in mod.json does not exist'); continue
        total += f.stat().st_size
    if total > 4 * 1024 * 1024: say('ERROR', f'scripts total {total // 1024} KB; the limit is 4 MB')
    if (mod / 'art_icons.js').exists() and 'art_icons.js' in scripts and 'hero.js' in scripts and scripts.index('art_icons.js') > scripts.index('hero.js'):
        say('ERROR', 'art_icons.js must come before hero.js in "scripts" (hero.js reads MOD.shared.itemArt when it runs)')
    for lang, rel in (m.get('i18n') or {}).items():
        f = mod / rel
        if not f.exists(): say('ERROR', f'i18n {lang}: {rel} does not exist'); continue
        try:
            d = json.loads(f.read_text('utf-8-sig'))
            if not isinstance(d, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in d.items()): say('ERROR', f'{rel}: must be {{ "中文": "translation" }} with string values')
            elif not d: say('WARN', f'{rel} is empty: untranslated Chinese is split into single characters in that language')
        except Exception as e: say('ERROR', f'{rel}: invalid JSON: {e}')
    if not m.get('i18n'): say('WARN', 'no i18n files: write at least English')
    return m


def check_portraits(mod):
    found = [p for p in mod.glob('portrait.*') if p.suffix.lower() in IMG]
    if not found and not (mod / 'portraits').exists(): say('WARN', 'no portrait: the hero gets a generated placeholder portrait')
    exts = {p.suffix.lower() for p in found}
    if '.png' in exts and len(exts) > 1: say('ERROR', 'portrait.png and another portrait.* both exist; the game uses portrait.png first (delete the template placeholder)')
    imgs = found + [p for p in (mod / 'portraits').glob('*') if p.suffix.lower() in IMG] if (mod / 'portraits').exists() else found
    for p in imgs:
        rel = p.relative_to(mod)
        if p.parent.name == 'portraits' and not re.fullmatch(r't[0-2]_(%s)' % '|'.join(sorted(EXPRS)), p.stem): say('WARN', f'{rel}: name should be t<0-2>_<expression>')
        try: w, h = Image.open(p).size
        except Exception as e: say('ERROR', f'{rel}: cannot read image: {e}'); continue
        n = w / 120
        if n == int(n) and h == 192 * n:
            if n >= 2: say('ERROR', f'{rel} is {w}x{h}, an exact multiple of 120x192: the game draws it as PIXEL ART (nearest neighbour). Export 450x720 for a smooth portrait')
        elif abs(w / h - 120 / 192) > .02: say('WARN', f'{rel} is {w}x{h}, not 5:8: it will be letterboxed (fit inside, bottom-aligned)')
        elif w < 240: say('WARN', f'{rel} is only {w}px wide: it will look soft')


def check_chibi(mod):
    mf = mod / 'chibi' / 'manifest.json'
    if not mf.exists(): say('WARN', 'no chibi/manifest.json: the hero uses the generated pixel sprite in battle'); return
    try: c = json.loads(mf.read_text('utf-8-sig'))
    except Exception as e: say('ERROR', f'chibi/manifest.json: invalid JSON: {e}'); return
    anims = c.get('anims', {}); ext = c.get('ext', 'png')
    need = {'idle', 'walk', 'hurt'}
    if not need <= set(anims) or not ({'attack', 'cast'} & set(anims)): say('ERROR', 'chibi needs idle, walk, hurt and attack or cast')
    for s, sc in (c.get('scales') or {}).items():
        for a, an in anims.items():
            f = mod / 'chibi' / (f'sheet_x{s}.{ext}' if c.get('sheet') else f'{a}_x{s}.{ext}')
            if not f.exists(): say('ERROR', f'chibi/{f.name} is missing'); continue
            if c.get('sheet'): continue
            w, h = Image.open(f).size
            if (w, h) != (an['n'] * sc['fw'], sc['fh']): say('ERROR', f'chibi/{f.name} is {w}x{h}, expected {an["n"]}x{sc["fw"]} by {sc["fh"]} (n x fw, fh)')
    if c.get('doll'):
        d = next((mod / 'chibi' / f'doll.{e}' for e in ('png', 'webp') if (mod / 'chibi' / f'doll.{e}').exists()), None)
        if not d: say('ERROR', 'manifest lists a doll but chibi/doll.png / doll.webp is missing')


def check_code(mod, mid):
    hero = mod / 'hero.js'
    if not hero.exists(): say('WARN', 'no hero.js (fine if your hero lives in another script)'); return
    src = hero.read_text('utf-8-sig')
    if 'registerHero(' not in src: say('ERROR', 'hero.js does not call registerHero')
    for k in re.findall(r"\bk:\s*['\"]([^'\"]+)['\"]", src):
        if k.startswith('#'): continue      # a sprite palette colour called k, not a legendary
        if not k.startswith(mid + '_'): say('ERROR', f"legendary key {k!r} must start with '{mid}_'")
    for k in re.findall(r"\bkey:\s*['\"]([^'\"]+)['\"]", src):
        if not k.startswith(mid + '_'): say('ERROR', f"set key {k!r} must start with '{mid}_'")
    if not re.search(r'\bface:\s*\[', src): say('WARN', 'no face: [x, y]: the hero picker crops the avatar at the default spot (portrait_export.py --face prints the value)')
    if (mod / 'art_icons.js').exists() and 'MOD.shared.itemArt' not in src: say('WARN', 'art_icons.js exists but hero.js does not use itemArt: MOD.shared.itemArt')
    if re.search(r'^(?:if\s*\(.*\bVFX\b.*\)\s*)?VFX\.[A-Za-z_$][\w$]*\s*=', src, re.M):      # column 0 = top level of the script
        say('WARN', 'hero.js assigns VFX.<kind> at the top level: mod scripts run before the game scripts, so VFX does not exist yet. Register it inside IAP.onReady or when first used')
    if re.search(r'(?<![\w.])H[XY]\s*(?:[-+*/]?=)(?!=)', src):
        say('WARN', 'hero.js assigns HX / HY: the hero teleports with no movement. Use c.dash / c.blink (game 3.1.1+, references/hero-code.md 4)')
    if re.search(r'\bform\s*:\s*\{', src):
        if not re.search(r'\bwhen\s*:', src): say('ERROR', 'sprite.form needs when: h => …; without it the whole mod fails to load (references/transform.md)')
        say('WARN', 'sprite.form needs game 3.1.1+ (older games drop it when sprite.base is used): say so in the description')


def check_files(mod):
    total = 0
    for p in mod.rglob('*'):
        rel = p.relative_to(mod)
        if p.is_symlink(): say('ERROR', f'{rel} is a symlink; the Workshop uploader refuses folders with links')
        if any(part.startswith('.') for part in rel.parts) and not str(rel).startswith('.iap'): say('WARN', f'{rel}: hidden files are not uploaded')
        if p.is_file(): total += p.stat().st_size
    if total > 100 * 1024 * 1024: say('ERROR', f'the folder is {total // 1048576} MB; the Workshop limit is 100 MB')
    for name in ('preview.png', 'preview.jpg'):
        p = mod / name
        if p.exists() and p.stat().st_size >= 1024 * 1024: say('ERROR', f'{name} is {p.stat().st_size // 1024} KB; the Workshop preview must be under 1 MB')
    if not any((mod / n).exists() for n in ('preview.png', 'preview.jpg')): say('WARN', 'no preview.png / preview.jpg for the Workshop (make_preview.py)')
    print(f'      {total / 1048576:.1f} MB in total')


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mod_dir', help='the mod folder (the one with mod.json)')
    mod = Path(ap.parse_args().mod_dir)
    if not mod.is_dir(): sys.exit(f'{mod} is not a folder')
    m = check_manifest(mod)
    check_portraits(mod); check_chibi(mod)
    if m: check_code(mod, m.get('id', ''))
    check_files(mod)
    print(f"\n{out['ERROR']} error(s), {out['WARN']} warning(s)")
    sys.exit(1 if out['ERROR'] else 0)


if __name__ == '__main__':
    main()
