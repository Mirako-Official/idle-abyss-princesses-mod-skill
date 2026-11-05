#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Mirako
"""Generate or edit images with the provider the player picked. One CLI, three backends:

  openai   any OpenAI-compatible Images API (gpt-image models, many relays). Supports edits and
           transparent backgrounds, which makes it the easiest for portraits and expression edits.
  novelai  NovelAI image API (anime style). Text-to-image on an Opus plan at <= 1 MP / <= 28 steps
           costs no Anlas; img2img / inpaint (edit) costs Anlas. No transparency: remove the
           background afterwards.
  sdwebui  a local Stable Diffusion WebUI (AUTOMATIC1111 / Forge) started with --api.
           Free, any checkpoint / LoRA. No transparency: remove the background afterwards.

Players who draw their own art, or use another tool (ComfyUI, Midjourney, a commission), skip this
script and drop their PNGs into art/ instead.

Keys come only from environment variables, never from arguments or files written by this script:
  openai:  OPENAI_API_KEY, optional OPENAI_BASE_URL (default https://api.openai.com/v1),
           OPENAI_IMAGE_MODEL (default gpt-image-1)
  novelai: NAI_TOKEN (persistent token, starts with pst-), optional NAI_MODEL
           (default nai-diffusion-5-full), HTTPS_PROXY if NovelAI needs a proxy where you are
  sdwebui: optional SD_URL (default http://127.0.0.1:7860)

Examples:
  python gen_image.py generate --provider openai --prompt "full body anime girl ..." --size 1024x1536 --transparent --out art/portrait/cand.png -n 2
  python gen_image.py edit --provider openai --image art/portrait/t0_idle.png --prompt "change only her expression to ..." --out art/work/win.png
  python gen_image.py generate --provider novelai --prompt "1girl, maid, ..." --negative "lowres, ..." --size 832x1216 --out art/cand.png
  python gen_image.py edit --provider sdwebui --image master.png --mask face_mask.png --strength .55 --prompt "smile" --out win.png

Each output gets a sidecar <out>.json with the provider, model, size and prompt (no keys).
"""
import argparse, base64, io, json, os, random, sys, time, uuid, urllib.error, urllib.request, zipfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit('gen_image.py needs Pillow:  pip install pillow')


BROWSER_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36'


def die(msg):
    sys.exit('gen_image.py: ' + msg)


def png_bytes(path_or_img):
    im = Image.open(path_or_img) if not isinstance(path_or_img, Image.Image) else path_or_img
    buf = io.BytesIO(); im.convert('RGBA').save(buf, 'PNG'); return buf.getvalue()


def http(url, data=None, headers=None, timeout=600, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method or ('POST' if data is not None else 'GET'))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:      # no connection, DNS, proxy refused, timeout
        return 0, f'cannot reach {url.split("/")[2]}: {getattr(e, "reason", e)} (check the address, your network or HTTPS_PROXY)'.encode()


def multipart(fields, files):
    b = uuid.uuid4().hex; out = io.BytesIO()
    for k, v in fields.items():
        out.write(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, name, data in files:
        out.write(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\nContent-Type: image/png\r\n\r\n'.encode())
        out.write(data); out.write(b'\r\n')
    out.write(f'--{b}--\r\n'.encode())
    return out.getvalue(), f'multipart/form-data; boundary={b}'


# ---------------------------------------------------------------- openai-compatible
def openai_call(args, edit):
    key = os.environ.get('OPENAI_API_KEY', '')
    if not key: die('set OPENAI_API_KEY (and OPENAI_BASE_URL for a relay)')
    base = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    model = args.model or os.environ.get('OPENAI_IMAGE_MODEL', 'gpt-image-1')
    fields = {'model': model, 'prompt': args.prompt, 'n': '1', 'size': args.size}
    if args.transparent: fields['background'] = 'transparent'
    if args.quality: fields['quality'] = args.quality
    if edit:
        files = [('image' if len(args.image) == 1 else 'image[]', Path(p).name, png_bytes(p)) for p in args.image]
        if args.mask: files.append(('mask', Path(args.mask).name, png_bytes(args.mask)))
        body, ctype = multipart(fields, files)
        st, data = http(base + '/images/edits', body, {'Authorization': f'Bearer {key}', 'Content-Type': ctype})
    else:
        js = dict(fields, n=1)
        st, data = http(base + '/images/generations', json.dumps(js).encode(), {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
    if st != 200: return None, f'HTTP {st}: {data[:300].decode("utf8", "replace")}'
    d = json.loads(data)['data'][0]
    if d.get('b64_json'): return Image.open(io.BytesIO(base64.b64decode(d['b64_json']))), model
    if d.get('url'):
        st2, raw = http(d['url']);  return (Image.open(io.BytesIO(raw)), model) if st2 == 200 else (None, f'download HTTP {st2}')
    return None, 'no image in the reply'


# ---------------------------------------------------------------- novelai
def novelai_call(args, edit):
    """Request body as used for the official portraits (2026): image.novelai.net, V4-style prompt objects are required
    (both v4_prompt and v4_negative_prompt, or the server answers 500). Edits are img2img, optionally with a mask."""
    tok = os.environ.get('NAI_TOKEN', '')
    if not tok: die('set NAI_TOKEN to your NovelAI persistent token (pst-...)')
    model = args.model or os.environ.get('NAI_MODEL', 'nai-diffusion-5-full')
    w, h = (int(x) for x in args.size.lower().split('x'))
    seed = args.seed if args.seed is not None else random.randint(1, 2 ** 31 - 2)
    neg = args.negative or 'lowres, bad anatomy, bad hands, extra fingers, text, watermark, signature, blurry, jpeg artifacts'
    p = {'params_version': 4, 'width': w, 'height': h, 'scale': args.cfg or 5, 'sampler': 'k_euler_ancestral', 'steps': args.steps or 28,
         'seed': seed, 'n_samples': 1, 'ucPreset': 3, 'qualityToggle': False, 'sm': False, 'sm_dyn': False, 'dynamic_thresholding': False,
         'controlnet_strength': 1, 'legacy': False, 'add_original_image': False, 'cfg_rescale': 0, 'noise_schedule': 'karras',
         'legacy_v3_extend': False, 'uncond_scale': 1, 'negative_prompt': neg, 'prompt': args.prompt,
         'reference_image_multiple': [], 'reference_information_extracted_multiple': [], 'reference_strength_multiple': [], 'extra_noise_seed': seed,
         'v4_prompt': {'use_coords': False, 'use_order': False, 'caption': {'base_caption': args.prompt, 'char_captions': []}},
         'v4_negative_prompt': {'use_coords': False, 'use_order': False, 'caption': {'base_caption': neg, 'char_captions': []}}}
    action = 'generate'
    if edit:
        src = Image.open(args.image[0]).convert('RGB')
        if src.size != (w, h): src = src.resize((w, h), Image.LANCZOS)
        p.update({'image': base64.b64encode(png_bytes(src)).decode(), 'strength': args.strength, 'noise': 0})
        if args.mask: p['mask'] = base64.b64encode(png_bytes(Image.open(args.mask).convert('L').resize((w, h)))).decode()
        action = 'img2img'
    body = json.dumps({'input': args.prompt, 'model': model, 'action': action, 'parameters': p}).encode()
    st, data = http('https://image.novelai.net/ai/generate-image', body,
                    {'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json', 'Accept': '*/*', 'User-Agent': BROWSER_UA,
                     'Origin': 'https://novelai.net', 'Referer': 'https://novelai.net/'}, timeout=300)      # the default Python UA gets a Cloudflare page
    if st == 429: die('NovelAI 429 (rate limited): wait a while before trying again; do not retry in a loop')
    if st != 200 or not data.startswith(b'PK'):
        head = data[:300].decode('utf8', 'replace')
        if '<html' in head.lower(): head = 'an HTML page came back (blocked by a firewall or Cloudflare; try another network or HTTPS_PROXY)'
        return None, f'HTTP {st}: {head}'
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = sorted(n for n in z.namelist() if n.lower().endswith('.png'))
        if not names: return None, 'no png in the reply'
        return Image.open(io.BytesIO(z.read(names[0]))), model


# ---------------------------------------------------------------- stable diffusion webui
def sdwebui_call(args, edit):
    url = os.environ.get('SD_URL', 'http://127.0.0.1:7860').rstrip('/')
    w, h = (int(x) for x in args.size.lower().split('x'))
    js = {'prompt': args.prompt, 'negative_prompt': args.negative or '', 'width': w, 'height': h, 'steps': args.steps or 28,
          'cfg_scale': args.cfg or 6, 'sampler_name': args.sampler or 'Euler a', 'seed': args.seed if args.seed is not None else -1, 'batch_size': 1}
    if args.model: js['override_settings'] = {'sd_model_checkpoint': args.model}
    path = '/sdapi/v1/txt2img'
    if edit:
        js['init_images'] = [base64.b64encode(png_bytes(args.image[0])).decode()]
        js['denoising_strength'] = args.strength
        if args.mask: js['mask'] = base64.b64encode(png_bytes(Image.open(args.mask).convert('L'))).decode(); js['inpainting_fill'] = 1; js['mask_blur'] = 4
        path = '/sdapi/v1/img2img'
    st, data = http(url + path, json.dumps(js).encode(), {'Content-Type': 'application/json'}, timeout=900)
    if st != 200: return None, f'HTTP {st}: {data[:300].decode("utf8", "replace")} (is the WebUI running with --api?)'
    imgs = json.loads(data).get('images') or []
    if not imgs: return None, 'no image in the reply'
    return Image.open(io.BytesIO(base64.b64decode(imgs[0].split(',', 1)[-1]))), args.model or 'current checkpoint'


CALL = {'openai': openai_call, 'novelai': novelai_call, 'sdwebui': sdwebui_call}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['generate', 'edit'])
    ap.add_argument('--provider', required=True, choices=sorted(CALL))
    ap.add_argument('--prompt', required=True)
    ap.add_argument('--out', required=True, help='output PNG; with -n > 1 writes OUT_1.png, OUT_2.png, ...')
    ap.add_argument('--image', action='append', default=[], help='input image for edit (openai accepts several)')
    ap.add_argument('--mask', help='edit only where the mask is white (openai: transparent = edit; see references/image-providers.md)')
    ap.add_argument('--size', default='1024x1536', help='WxH. openai: 1024x1024 / 1024x1536 / 1536x1024; novelai: e.g. 832x1216')
    ap.add_argument('-n', type=int, default=1)
    ap.add_argument('--model'); ap.add_argument('--negative'); ap.add_argument('--seed', type=int)
    ap.add_argument('--steps', type=int); ap.add_argument('--cfg', type=float); ap.add_argument('--sampler')
    ap.add_argument('--strength', type=float, default=.55, help='img2img strength for novelai / sdwebui edits')
    ap.add_argument('--transparent', action='store_true', help='ask for a transparent background (openai only)')
    ap.add_argument('--quality', help='openai quality: low / medium / high')
    a = ap.parse_args()
    edit = a.mode == 'edit'
    if edit and not a.image: die('edit needs --image')
    if a.transparent and a.provider != 'openai':
        print('note: only the openai provider can return a transparent background; remove it afterwards (see references/image-providers.md)', file=sys.stderr)
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    targets = [out] if a.n == 1 else [out.with_name(f'{out.stem}_{i}{out.suffix}') for i in range(1, a.n + 1)]
    for dst in targets:
        t0 = time.time(); im, info = CALL[a.provider](a, edit)
        if im is None:
            print(f'FAILED {dst.name}: {info}', file=sys.stderr); continue
        im.save(dst)
        meta = {'provider': a.provider, 'model': info, 'mode': a.mode, 'size': list(im.size), 'prompt': a.prompt, 'negative': a.negative,
                'images': a.image, 'mask': a.mask, 'strength': a.strength if edit else None}
        dst.with_suffix('.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1), 'utf8')
        print(f'{dst}  {im.size[0]}x{im.size[1]}  {time.time() - t0:.0f}s')
        if a.provider == 'novelai': time.sleep(2)      # be polite: one at a time


if __name__ == '__main__':
    main()
