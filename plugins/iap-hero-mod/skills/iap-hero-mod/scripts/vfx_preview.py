#!/usr/bin/env python3
"""Preview a hero's skill effects outside the game: cast each skill on training dummies and save
every frame, a contact sheet and a GIF, so you can judge an effect the way a pixel artist would
(render, look, fix the worst thing, render again).

It runs the game you installed, in a headless browser, with a fixed seed and a fixed clock:
the same command gives the same pictures. Nothing touches your saves.

Needs:  pip install playwright pillow numpy   then once:  python -m playwright install chromium

Examples
  python vfx_preview.py --mod mod                          # every skill of the mod's hero
  python vfx_preview.py --mod mod --skill mh_strike --secs 2
  python vfx_preview.py --mod mod --skill mh_strike --ref mage:meteor   # side by side with an official skill
  python vfx_preview.py --hero warrior --skill whirl       # an official hero, no mod
  python vfx_preview.py --mod mod --lowfx                  # what players see with 降低特效 (reduce effects) on

Output (default work/vfx/<skill>/): frames/0001.png …, contact.png (every 2nd frame with the time),
anim.gif (real speed), and report.txt (casts, effect kinds, errors, Math.random misuse).
Effects that throw inside the game are silently dropped there; this script prints the error instead.
"""
import argparse, asyncio, base64, hashlib, io, json, os, re, struct, sys, threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit('Pillow is missing: pip install pillow')

ASSET_TYPES = {'.png': 'image/png', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif',
               '.ogg': 'audio/ogg', '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.json': 'application/json'}
CANVAS = (272, 156)      # the battle canvas in game pixels (index.html #cv)


# ---------------------------------------------------------------- find the game
def steam_roots():
    home = Path.home()
    roots = [Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Steam', Path(r'C:\Program Files\Steam'),
             home / 'Library/Application Support/Steam', home / '.steam/steam', home / '.local/share/Steam',
             home / '.var/app/com.valvesoftware.Steam/.local/share/Steam']
    out = []
    for r in roots:
        if not (r / 'steamapps').is_dir():
            continue
        out.append(r)
        vdf = r / 'steamapps/libraryfolders.vdf'
        if vdf.is_file():      # other Steam libraries (second drive, SD card)
            for p in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text('utf-8', 'ignore')):
                out.append(Path(p.replace('\\\\', '\\')))
    return out


def find_asar(given):
    """A path to app.asar, the game's install folder, the .app bundle, or a folder with web/index.html."""
    cands = []
    if given:
        p = Path(given).expanduser()
        if p.is_file() and p.suffix == '.asar':
            return p, None
        if (p / 'index.html').is_file() and (p / 'js/vfx.js').is_file():
            return None, p
        if (p / 'web/index.html').is_file():
            return None, p / 'web'
        cands += [p / 'resources/app.asar', p / 'Contents/Resources/app.asar'] + list(p.glob('*.app/Contents/Resources/app.asar'))
    else:
        for root in steam_roots():
            for d in (root / 'steamapps/common').glob('*'):
                if (d / 'IdleAbyssPrincesses.exe').exists() or list(d.glob('IdleAbyssPrincesses.app')) or (d / 'IdleAbyssPrincesses').exists():
                    cands += [d / 'resources/app.asar'] + list(d.glob('*.app/Contents/Resources/app.asar'))
    for c in cands:
        if c.is_file():
            return c, None
    sys.exit('Could not find the game. Pass --game <install folder> (Steam: right-click the game > Manage > Browse local files).')


def extract_web(asar):
    """Unpack only web/ from the game's app.asar into a cache folder (once per game version)."""
    st = asar.stat()
    key = hashlib.sha1(f'{asar.resolve()}|{st.st_size}|{int(st.st_mtime)}'.encode()).hexdigest()[:12]
    out = Path.home() / '.cache/iap-vfx-preview' / key
    if (out / 'web/index.html').is_file():
        return out / 'web'
    with open(asar, 'rb') as f:
        head = f.read(16)
        header_size = struct.unpack('<I', head[4:8])[0]
        json_len = struct.unpack('<I', head[12:16])[0]
        header = json.loads(f.read(json_len).decode('utf-8'))
        base = 8 + header_size
        web = header['files'].get('web')
        if not web:
            sys.exit(f'{asar} has no web/ folder: is this the right game?')
        tmp = out.with_name(key + '.part')

        def walk(node, rel):
            for name, e in node.get('files', {}).items():
                path = rel / name
                if 'files' in e:
                    walk(e, path)
                    continue
                dst = tmp / path
                dst.parent.mkdir(parents=True, exist_ok=True)
                if e.get('unpacked'):
                    src = Path(str(asar) + '.unpacked') / path
                    dst.write_bytes(src.read_bytes())
                else:
                    f.seek(base + int(e['offset']))
                    dst.write_bytes(f.read(e['size']))
        walk(web, Path('web'))
    tmp.replace(out) if not out.exists() else None
    return out / 'web'


# ---------------------------------------------------------------- the mod listing (same shape the game's desktop build passes in)
def load_mod(folder):
    folder = Path(folder)
    man = json.loads((folder / 'mod.json').read_text('utf-8-sig'))
    api = man.get('api', 1)
    late = man.get('lateScripts', []) if api >= 3 else []
    names = man.get('scripts', [] if (man.get('content') is not None and api >= 2) or late else ['main.js'])
    files = sorted(str(p.relative_to(folder)).replace(os.sep, '/') for p in folder.rglob('*')
                   if p.is_file() and p.suffix.lower() in ASSET_TYPES and not any(x.startswith('.') for x in p.relative_to(folder).parts))
    i18n = {lang: json.loads((folder / rel).read_text('utf-8-sig')) for lang, rel in (man.get('i18n') or {}).items()}
    return {'id': man['id'], 'name': man.get('name', man['id']), 'version': man.get('version', ''), 'api': api,
            'author': man.get('author', ''), 'description': man.get('description', ''), 'source': 'dev', 'workshopId': '',
            'scripts': [{'file': n, 'code': (folder / n).read_text('utf-8-sig')} for n in names],
            'files': files, 'i18n': i18n, 'error': '', 'enabled': True, 'base': f"/__mods__/{man['id']}/",
            'dataPack': not names and not late, 'content': {}, 'warnings': [], 'hash': 'preview-' + man['id'],
            'late': [{'file': n, 'code': (folder / n).read_text('utf-8-sig')} for n in late],
            'settings': man.get('settings', []) if api >= 3 else []}


def serve(web, mods):
    class H(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            path = unquote(self.path.split('?')[0])
            if path.startswith('/__mods__/'):
                mid, _, rel = path[len('/__mods__/'):].partition('/')
                root = mods.get(mid)
                file = (root / rel).resolve() if root else None
                if not file or root.resolve() not in file.parents or not file.is_file() or file.suffix.lower() not in ASSET_TYPES:
                    return self.send_error(404)
                body = file.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', ASSET_TYPES[file.suffix.lower()])
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path == '/favicon.ico':
                self.send_response(204)
                self.end_headers()
                return
            return super().do_GET()
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), partial(H, directory=str(web)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


# ---------------------------------------------------------------- in the page
# Seeded Math.random, a clock that only moves when we step, manual timers, no rAF, in-memory storage.
INIT = r'''(seed) => {
  let s = seed >>> 0; const timers = new Map(); let tid = 0, ticks = 0;
  window.__rand = { n: 0, inVfx: 0, vfxCalls: 0 };
  Math.random = () => { __rand.n++; if (__rand.inVfx) __rand.vfxCalls++; s = (s + 0x6D2B79F5) >>> 0; let n = s; n = Math.imul(n ^ n >>> 15, n | 1); n ^= n + Math.imul(n ^ n >>> 7, n | 61); return ((n ^ n >>> 14) >>> 0) / 4294967296; };
  const now = () => ticks * 1000 / 30, ND = Date, epoch = 1790640000000;
  window.Date = class extends ND { constructor(...a) { super(...(a.length ? a : [epoch + now()])); } static now() { return epoch + now(); } };
  Object.defineProperty(performance, 'now', { value: now });
  window.requestAnimationFrame = () => 0; window.cancelAnimationFrame = () => {};
  const sch = (fn, d, rep, args) => { const id = ++tid; timers.set(id, { fn, due: now() + Math.max(0, +d || 0), rep, args }); return id; };
  window.setTimeout = (fn, d, ...a) => sch(fn, d, 0, a); window.setInterval = (fn, d, ...a) => sch(fn, d, Math.max(1, +d || 1), a);
  window.clearTimeout = window.clearInterval = id => timers.delete(id);
  window.__simTick = () => { ticks++; for (const [id, t] of [...timers]) { if (!timers.has(id) || t.due > now()) continue; if (t.rep) t.due += t.rep; else timers.delete(id); if (typeof t.fn === 'function') try { t.fn(...t.args); } catch (e) { console.error(e); } } };
  const mem = () => { const m = new Map(); return { get length() { return m.size; }, key: i => [...m.keys()][i] ?? null, getItem: k => m.has(String(k)) ? m.get(String(k)) : null, setItem: (k, v) => m.set(String(k), String(v)), removeItem: k => m.delete(String(k)), clear: () => m.clear() }; };
  for (const n of ['localStorage', 'sessionStorage']) Object.defineProperty(window, n, { value: mem(), configurable: true });
  Object.defineProperty(window, 'indexedDB', { value: undefined, configurable: true });
  window.AudioContext = window.webkitAudioContext = undefined;
}'''

SETUP = r'''(o) => {
  const out = { errors: [] };
  if (!HEROES[o.hero]) { out.errors.push(`hero "${o.hero}" is not registered (mod failed to load? see the errors above)`); out.heroes = Object.keys(HEROES); return out; }
  if (typeof heroLocked === 'function' && heroLocked(o.hero) && HEROES[o.hero].dlc && typeof DLC === 'object') DLC[HEROES[o.hero].dlc].owned = true;
  choose(o.hero); if (typeof GAME === 'object') GAME.running = true;
  if (typeof closeModal === 'function') try { closeModal(); } catch (e) {}
  const t = document.getElementById('title'); if (t) t.classList.remove('on');
  SETTINGS.heroArt = o.art; SETTINGS.lowFx = !!o.lowfx; SETTINGS.zoom = o.zoom;
  S.level = 70; S.skills.eq = [o.skill, null, null]; refreshStats(true);
  R.mons = []; R.zones = []; R.pets = R.pets.filter(p => !p.temp); R.hero.hp = R.st.maxLife; R.hero.cds = R.hero.cds.map(() => 0); R.hero.ww = 0;
  const n = o.mons;
  for (let i = 0; i < n; i++) {
    const gx = HX + o.dist + (i % 3) * .7, gy = HY - .7 + Math.floor(i / 3) * .7 + (i % 3) * .2;
    const m = spawnMon({ t: 'skeleton', n: 'Dummy', hp: 1, dmg: 0, spd: 0, cd: 1e9, ele: 'phys' }, { gx, gy });
    m.hp = m.max = 1e300; m.atk = 0; if (!MON_SPR[m.spr || m.type]) m.spr = 'skel';
  }
  /* diagnostics: effect kinds spawned, effects that throw, Math.random inside effect code */
  window.__diag = { kinds: {}, fails: [], skillVfxErr: [], casts: [] };
  const vfx0 = vfx; vfx = (k, p) => { __diag.kinds[k] = (__diag.kinds[k] || 0) + 1; if (!VFX[k]) __diag.fails.push(`vfx("${k}") — no such effect kind`); return vfx0(k, p); };
  const fail0 = vfxFail; vfxFail = e => { __diag.fails.push(`effect kind "${e.kind}" threw while drawing/ticking`); return fail0(e); };
  const draw0 = drawVfx; drawVfx = (c, l) => { __rand.inVfx++; try { return draw0(c, l); } finally { __rand.inVfx--; } };
  const tick0 = vfxTick; vfxTick = dt => { __rand.inVfx++; try { return tick0(dt); } finally { __rand.inVfx--; } };
  const f = SKILL_VFX[o.skill];
  if (f) SKILL_VFX[o.skill] = () => { __rand.inVfx++; try { f(); } catch (e) { __diag.skillVfxErr.push(String(e && (e.stack || e.message) || e)); } finally { __rand.inVfx--; } };
  out.hasVfx = !!f; out.skillName = SKILLS[o.skill] ? SKILLS[o.skill].n : null; out.cd = SKILLS[o.skill] ? SKILLS[o.skill].cd : null;
  out.skills = CLASS_SKILLS[o.hero] || [];
  render();
  const [hx, hy] = iso(HX, HY), pts = [[hx, hy]].concat(R.mons.map(m => iso(m.gx, m.gy)));
  out.box = [Math.min(...pts.map(p => p[0])), Math.min(...pts.map(p => p[1])), Math.max(...pts.map(p => p[0])), Math.max(...pts.map(p => p[1]))];
  return out;
}'''

STEP = r'''(n) => {
  const shots = [];
  for (let i = 0; i < n.count; i++) {
    const cd0 = R.hero.cds[0] || 0;
    __simTick(); update(1 / 30); render();
    if ((R.hero.cds[0] || 0) > cd0 + .5) __diag.casts.push(+(R.t).toFixed(3));
    shots.push(document.getElementById('cv').toDataURL('image/png'));
  }
  return shots;
}'''


def skill_list(page, hero):
    return page.evaluate('(h) => CLASS_SKILLS[h] || []', hero)


async def record(browser, url, opt, hero, skill, mods_listing, errors_out):
    z = opt.zoom
    ctx = await browser.new_context(viewport={'width': 640 * z, 'height': 360 * z}, device_scale_factor=1, locale='zh-CN')
    page = await ctx.new_page()
    errs = []
    page.on('pageerror', lambda e: errs.append(f'page error: {e}'))
    page.on('console', lambda m: errs.append(f'console {m.type}: {m.text}') if m.type == 'error' else None)
    await page.add_init_script(f'({INIT})({opt.seed});')
    await page.add_init_script(f'window.__IAP_MODS__ = {json.dumps({"safe": False, "reason": "", "list": mods_listing}, ensure_ascii=False)};')
    await page.goto(url + 'index.html?nodlc', wait_until='load')
    for _ in range(5):
        await page.evaluate('() => __simTick()')
    info = await page.evaluate(SETUP, {'hero': hero, 'skill': skill, 'art': opt.art, 'lowfx': opt.lowfx, 'zoom': z, 'mons': opt.mons, 'dist': opt.dist})
    if info.get('errors'):
        errors_out += errs + info['errors']
        await ctx.close()
        return None, info
    total = round(opt.secs * 30)
    shots = []
    while len(shots) < total:
        shots += await page.evaluate(STEP, {'count': min(15, total - len(shots))})
    diag = await page.evaluate('() => ({ ...__diag, randInVfx: __rand.vfxCalls })')
    await ctx.close()
    frames = [Image.open(io.BytesIO(base64.b64decode(s.split(',', 1)[1]))).convert('RGB') for s in shots]
    errors_out += errs
    return frames, {**info, **diag}


def crop_box(info, size, opt):
    w, h = size
    s = w / CANVAS[0]
    if opt.crop == 'full':
        return (0, 0, w, h)
    if opt.crop != 'auto':
        x, y, cw, ch = (float(v) for v in opt.crop.split(','))
        return tuple(int(v * s) for v in (x, y, x + cw, y + ch))
    x0, y0, x1, y1 = info['box']
    x0, y0, x1, y1 = x0 - 40, y0 - 52, x1 + 40, y1 + 18
    return (max(0, int(x0 * s)), max(0, int(y0 * s)), min(w, int(x1 * s)), min(h, int(y1 * s)))


def label(img, text):
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=max(10, img.width // 18))
    except TypeError:
        font = ImageFont.load_default()
    d.rectangle((0, 0, img.width, font.size + 4 if hasattr(font, 'size') else 14), fill=(0, 0, 0))
    d.text((3, 1), text, fill=(255, 255, 255), font=font)
    return img


def contact(frames, every, cols, title):
    picks = list(range(0, len(frames), every))
    fw, fh = frames[0].size
    rows = (len(picks) + cols - 1) // cols
    head = 30
    sheet = Image.new('RGB', (cols * (fw + 2) + 2, rows * (fh + 2) + 2 + head), (24, 24, 32))
    try:
        hf = ImageFont.load_default(size=20)
    except TypeError:
        hf = ImageFont.load_default()
    ImageDraw.Draw(sheet).text((6, 4), title, fill=(255, 255, 255), font=hf)
    for n, i in enumerate(picks):
        cell = label(frames[i].copy(), f'{i + 1}  {i / 30:.2f}s')
        sheet.paste(cell, (2 + (n % cols) * (fw + 2), head + 2 + (n // cols) * (fh + 2)))
    return sheet


def scale_frames(frames, k):
    return [f.resize((f.width * k, f.height * k), Image.NEAREST) for f in frames] if k > 1 else frames


def side_by_side(a, b):
    out = []
    for i in range(max(len(a), len(b))):
        fa, fb = a[min(i, len(a) - 1)], b[min(i, len(b) - 1)]
        im = Image.new('RGB', (fa.width + fb.width + 4, max(fa.height, fb.height)), (24, 24, 32))
        im.paste(fa, (0, 0)); im.paste(fb, (fa.width + 4, 0))
        out.append(im)
    return out


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mod', action='append', default=[], help='mod folder (the one with mod.json); repeat for dependencies')
    ap.add_argument('--hero', help='hero id (default: the hero the mod registers)')
    ap.add_argument('--skill', default='all', help='skill id, comma list, or "all" (default)')
    ap.add_argument('--ref', help='official skill to show next to yours, as hero:skill (e.g. mage:meteor)')
    ap.add_argument('--game', help='game install folder or app.asar (default: look in the Steam libraries)')
    ap.add_argument('--out', default='work/vfx', help='output folder (default work/vfx)')
    ap.add_argument('--secs', type=float, default=1.6, help='seconds to record from the first cast (default 1.6)')
    ap.add_argument('--zoom', type=int, default=3, help='game zoom = output pixels per game pixel (default 3)')
    ap.add_argument('--art', choices=['chibi', 'pixel'], default='chibi', help='battle sprite style (设置 → 战斗小人)')
    ap.add_argument('--lowfx', action='store_true', help='record with 降低特效 (reduce effects) on')
    ap.add_argument('--mons', type=int, default=5, help='number of training dummies (default 5)')
    ap.add_argument('--dist', type=float, default=1.6, help='tiles from the hero to the nearest dummy (default 1.6)')
    ap.add_argument('--crop', default='auto', help='"auto" (hero and dummies), "full", or x,y,w,h in game pixels')
    ap.add_argument('--every', type=int, default=2, help='contact sheet shows every Nth frame (default 2)')
    ap.add_argument('--cols', type=int, default=6, help='contact sheet columns (default 6)')
    ap.add_argument('--seed', type=int, default=7)
    opt = ap.parse_args()
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        sys.exit('Playwright is missing: pip install playwright  then  python -m playwright install chromium')

    asar, web = find_asar(opt.game)
    if asar:
        print(f'game: {asar}')
        web = extract_web(asar)
    print(f'web: {web}')
    mods, listing = {}, []
    for m in opt.mod:
        entry = load_mod(m)
        mods[entry['id']] = Path(m).resolve()
        listing.append(entry)
    httpd = serve(web, mods)
    url = f'http://127.0.0.1:{httpd.server_address[1]}/'
    out_root = Path(opt.out)
    errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        hero = opt.hero
        if not hero:
            ctx = await browser.new_context()
            pg = await ctx.new_page()
            pg.on('pageerror', lambda e: errors.append(f'page error: {e}'))
            await pg.add_init_script(f'({INIT})({opt.seed});')
            await pg.add_init_script(f'window.__IAP_MODS__ = {json.dumps({"safe": False, "reason": "", "list": listing}, ensure_ascii=False)};')
            await pg.goto(url + 'index.html?nodlc', wait_until='load')
            found = await pg.evaluate('() => Object.keys(HEROES).filter(k => HEROES[k].mod)')
            mod_err = await pg.evaluate('() => (typeof MODS === "object" && MODS && MODS.list ? MODS.list : []).filter(m => m.error).map(m => m.id + ": " + m.error)')
            await ctx.close()
            if not found:
                for e in errors + mod_err:
                    print('  ' + e)
                sys.exit('No mod hero was registered. Pass --mod <folder> (or --hero <id> for an official hero).')
            hero = found[0]
            if len(found) > 1:
                print(f'mod heroes: {found}; using {hero} (pick with --hero)')
        ref = None
        if opt.ref:
            rh, _, rs = opt.ref.partition(':')
            ref_frames, ref_info = await record(browser, url, opt, rh, rs, listing, errors)
            if ref_frames:
                ref = (rh, rs, ref_frames, ref_info)
        # which skills
        ctx = await browser.new_context()
        pg = await ctx.new_page()
        await pg.add_init_script(f'({INIT})({opt.seed});')
        await pg.add_init_script(f'window.__IAP_MODS__ = {json.dumps({"safe": False, "reason": "", "list": listing}, ensure_ascii=False)};')
        await pg.goto(url + 'index.html?nodlc', wait_until='load')
        all_sk = await pg.evaluate('(h) => CLASS_SKILLS[h] || []', hero)
        await ctx.close()
        skills = all_sk if opt.skill == 'all' else [s.strip() for s in opt.skill.split(',') if s.strip()]
        bad = [s for s in skills if s not in all_sk]
        if bad:
            sys.exit(f'{hero} has no skill {bad}; its skills: {all_sk}')
        for sk in skills:
            errs = []
            frames, info = await record(browser, url, opt, hero, sk, listing, errs)
            folder = out_root / sk
            (folder / 'frames').mkdir(parents=True, exist_ok=True)
            lines = [f'hero {hero}  skill {sk} ({info.get("skillName")})  cd {info.get("cd")} s  seed {opt.seed}  art {opt.art}  lowfx {opt.lowfx}']
            if frames is None:
                lines += errs
                (folder / 'report.txt').write_text('\n'.join(lines) + '\n', 'utf-8')
                print('\n'.join(lines))
                continue
            box = crop_box(info, frames[0].size, opt)
            frames = [f.crop(box) for f in frames]
            scale = opt.zoom if opt.art == 'pixel' else 1      # pixel mode draws a 1x canvas
            frames = scale_frames(frames, scale)
            for i, f in enumerate(frames):
                f.save(folder / 'frames' / f'{i + 1:04d}.png')
            show = frames
            title = f'{hero}:{sk}'
            if ref:
                rf = [f.crop(crop_box(ref[3], f.size, opt)) for f in ref[2]]
                rf = scale_frames(rf, scale)
                show = side_by_side(frames, rf)
                title += f'   |   right: reference {ref[0]}:{ref[1]}'
            contact(show, opt.every, opt.cols, title).save(folder / 'contact.png')
            show[0].save(folder / 'anim.gif', save_all=True, append_images=show[1:], duration=33, loop=0, disposal=1)
            lines.append(f'casts at (game seconds): {info["casts"] or "none — the skill never fired (no target in range? returned false?)"}')
            lines.append(f'registered vfx entry: {"yes" if info["hasVfx"] else "no (the game draws the generic effect for its element)"}')
            lines.append('effect kinds spawned: ' + (', '.join(f'{k}×{v}' for k, v in sorted(info['kinds'].items())) or 'none'))
            for e in info['skillVfxErr']:
                lines.append('ERROR in your vfx function (the game swallows this and shows nothing): ' + e.splitlines()[0])
            for e in sorted(set(info['fails'])):
                lines.append('ERROR: ' + e)
            if info['randInVfx']:
                lines.append(f'ERROR: effect code called Math.random {info["randInVfx"]} times; use vrnd(lo, hi) (Math.random in effects changes combat results)')
            lines += sorted(set(errs))
            lines.append(f'output: {folder}/contact.png, anim.gif, frames/ ({len(frames)} frames, 30 fps)')
            (folder / 'report.txt').write_text('\n'.join(lines) + '\n', 'utf-8')
            print('\n'.join(lines) + '\n')
        await browser.close()
    httpd.shutdown()
    for e in sorted(set(errors)):
        print(e)


if __name__ == '__main__':
    asyncio.run(main())
