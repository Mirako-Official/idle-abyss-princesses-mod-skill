# Image providers: let the player choose

The player decides how the art is made. Ask once, early, and remember the answer. Never pick a paid
service for them, and never ask them to paste an API key into the chat: keys go into environment
variables on their own machine (`export NAME=...` / `setx NAME ...`), which `scripts/gen_image.py` reads.

| Choice | Good at | Transparent background | Edits (expressions, outfit tiers) | Cost |
|---|---|---|---|---|
| **Own art / commission / another tool** (ComfyUI, Midjourney, Krita…) | full control, no AI disclosure needed if no AI was used | depends | redraw or edit by hand | — |
| **openai** — any OpenAI-compatible Images API (gpt-image models, many relays) | following instructions, keeping a character consistent, "change only the face" edits | yes (`--transparent`) | yes, best of the three | per image |
| **novelai** — NovelAI image API | anime style, crisp line art, consistent "game art" look | no → remove afterwards | img2img / inpaint with a mask (costs Anlas) | Opus plan: text-to-image ≤ 1 MP and ≤ 28 steps is free |
| **sdwebui** — local Stable Diffusion WebUI (A1111 / Forge, started with `--api`) | free, any checkpoint / LoRA, private | no → remove afterwards | img2img / inpaint with a mask | free (own GPU) |

## Environment variables

```
openai   OPENAI_API_KEY   [OPENAI_BASE_URL=https://api.openai.com/v1] [OPENAI_IMAGE_MODEL=gpt-image-1]
novelai  NAI_TOKEN=pst-…  [NAI_MODEL=nai-diffusion-5-full] [HTTPS_PROXY=…]
sdwebui  [SD_URL=http://127.0.0.1:7860]
```

Model names change over time; if a provider rejects the model, ask the player which model their
account offers and pass `--model`.

## Commands

```
python $SKILL/scripts/gen_image.py generate --provider openai  --prompt "..." --size 1024x1536 --transparent -n 2 --out art/portrait/cand.png
python $SKILL/scripts/gen_image.py edit     --provider openai  --image art/portrait/t0_idle.png --prompt "..." --out art/work/t0_win_raw.png
python $SKILL/scripts/gen_image.py generate --provider novelai --prompt "1girl, ..." --negative "..." --size 832x1216 --out art/cand.png
python $SKILL/scripts/gen_image.py edit     --provider sdwebui --image art/master.png --mask art/face_mask.png --strength .5 --prompt "..." --out art/work/win_raw.png
```
(run from the work folder; `$SKILL` is this skill's folder)

Every output gets `<file>.json` next to it with the provider, model and prompt (never the key): keep
them, they are the record for the AI disclosure and for redoing a frame.

Notes from real use:
- Some OpenAI-compatible relays ignore `--size` and keep the input's aspect ratio (a 1086×1448 input
  came back 1037×1516). The scripts that use the results resize to the master, so this is fine.
- NovelAI blocks requests without a browser-like User-Agent (the script sends one) and answers 429
  when you go too fast: stop and wait, do not loop. Where NovelAI is unreachable, set HTTPS_PROXY.
- An edit request can take 1–3 minutes. Run a few in parallel at most (2–3), not dozens.

## Background removal (novelai, sdwebui, photos of drawings)

- Easiest: generate on a plain, flat background (`simple white background` / `green background`) and
  let the export scripts key it out: `portrait_export.py --bg auto`, `chibi_frames.py --bg auto`. This
  removes the flat colour connected to the image border, so white inside the outfit survives.
- Soft or busy backgrounds: use a real remover first, e.g. `pip install rembg` then
  `rembg i in.png out.png`, or the WebUI's rembg extension. Check the hair edges at 100 %.
- openai with `--transparent` needs none of this.

## Prompt recipes

Write prompts in English for openai / novelai / sdwebui (tags for NovelAI and most SD checkpoints).
Describe the character the same way every time (hair colour and length, eyes, outfit pieces,
signature accessories) so pieces match.

**Portrait master (t0 idle)** — full body, standing, slight 3/4 view, the whole figure inside the
canvas with a little space above the head and under the feet, neutral friendly expression, hands
visible, plain background, 2:3 portrait canvas (1024×1536 / 832×1216). Clean anime illustration,
flat cel shading, clear line art (it is shown about 240 px tall in game).

**Expression edit** (from the idle master, same canvas; use him / her / them to match the character):
`Edit this illustration. Change ONLY her facial expression (eyebrows, eyes, mouth, cheeks) to: <words>.
Keep everything else exactly identical: same character, face shape, hair, accessories, pose, outfit,
hands. Same style, line weight and colours, same framing and position.`
Expression words that work: fight = `serious, determined, closed mouth, slight frown, focused eyes`;
skill = `shouting, open mouth, v-shaped eyebrows, intense eyes`; hurt = `wince, one eye closed,
clenched teeth, small tear`; low = `exhausted, sweat drops, half-closed teary eyes`; win = `very happy,
big open smile, eyes closed in happy arcs, blush`; down = `eyes closed, unconscious, dizzy, tears`.
Then paste only the face back with `scripts/expr_composite.py` (see art-pipeline.md).

**Outfit tiers t1 / t2 (optional)** — same edit wording but "change ONLY her outfit from the neck
down to <richer version of the same outfit>; keep face, hair, pose, hands". Skip tiers if the player
wants one look (the game falls back to t0 for every tier).

**Chibi master** — `chibi, super deformed, about 2.5 heads tall, full body, standing, facing right
(3/4 view to the right), feet visible and flat on the ground, arms slightly away from the body,
holding <weapon> small, plain background`, square or 2:3 canvas. Same outfit and colours as the
portrait. If the player has a three-view sheet, crop the front or right-facing figure and edit it
into a clean single figure. `chibi_frames.py` animates it: separate legs and a clear neck help.

**Icons are not generated** — draw them as 16×16 character grids (icons.md section of
art-pipeline.md). Image models cannot make clean 16 px icons, and the game's own icons are all
hand-made pixel art.

## Rights and disclosure

- Use only art the player made, commissioned with rights, or has written permission to use. Fan art
  of someone else's character needs the artist's permission (Workshop rule 2) and credits in the
  description, `bio` and README.
- If any AI model generated or edited an image, tick the Workshop `AI Art` tag when uploading.
