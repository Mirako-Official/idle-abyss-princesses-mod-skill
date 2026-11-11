'use strict';
/* Stella's own effect kinds (references/skill-vfx.md).
   - Kinds are added to the game's VFX table once the game has loaded (IAP.onReady): at the top level of a
     mod script VFX does not exist yet.
   - Draw only. Random numbers only from vrnd(lo, hi). Coordinates are game pixels; iso(gx, gy) turns grid
     tiles into the screen point on the floor; vPos(e) does that for an effect (follow / gx, gy / x, y).
   - Layers: ground (under the characters, darkened by the dungeon), air (after the darkness: glows),
     light(e, k) returns [x, y, radius, strength 0..1, colour] and lights up the dark around it.
   - k = e.t / e.d is the progress 0..1. */

/* A four-point star glint at the target: fast in (k < .15 white-hot), slow out, a ring that expands. */
function stellaStarKind() {
  return {
    init(e) { e.rot = vrnd(0, .6); e.sparks = Array.from({ length: 6 }, () => ({ a: vrnd(0, 6.28), v: vrnd(18, 34), s: vrnd(.6, 1) })); },
    air(c, e, k) {
      const p = vPos(e), x = Math.round(p.x), y = Math.round(p.y - 9);
      const grow = k < .15 ? k / .15 : 1, fade = k < .15 ? 1 : 1 - (k - .15) / .85;
      const arm = Math.round(2 + 7 * grow * (1 - k * .6));
      c.globalAlpha = fade; c.fillStyle = e.c;
      c.fillRect(x - arm, y, arm * 2 + 1, 1); c.fillRect(x, y - arm, 1, arm * 2 + 1);       // long cross in the colour
      c.fillStyle = '#ffffff'; const core = Math.max(1, Math.round(arm / 2.5));
      c.fillRect(x - core, y, core * 2 + 1, 1); c.fillRect(x, y - core, 1, core * 2 + 1);  // white-hot middle
      if (k < .15) c.fillRect(x - 1, y - 1, 3, 3);                                           // 1–2 frame hero flash
      c.globalAlpha = fade * .8; vRing(c, x, y + 9, 4 + 14 * vEase(k), 2 + 7 * vEase(k), e.c); // floor ring, flat 2:1 like the grid
      for (const s of e.sparks) { const d = s.v * vEase(k); c.globalAlpha = fade * s.s; c.fillStyle = s.s > .8 ? '#ffffff' : e.c;
        vPx(c, x + Math.cos(s.a) * d, y + Math.sin(s.a) * d * .6 + 6 * k * k); }               // sparks fly out and drop
    },
    light(e, k) { const p = vPos(e); return [p.x, p.y - 9, 26, (1 - k) * .7, e.c]; },
  };
}

/* A star falling on the hero: a streak from the sky (anticipation), impact flash, then a shock ring on the floor. */
function stellaFallKind() {
  const HIT = .28;                                   // impact time as a share of the effect
  return {
    ground(c, e, k) {
      if (k < HIT) { const p = vPos(e), a = k / HIT; c.globalAlpha = .25 + .35 * a; vRing(c, p.x, p.y, 8 + 10 * a, 4 + 5 * a, e.c); return; }   // target circle grows before the hit
      const p = vPos(e), u = (k - HIT) / (1 - HIT), r = 6 + 34 * vEase(u);
      vDisc(c, p.x, p.y, r, r / 2, e.c, .25 * (1 - u)); c.globalAlpha = 1 - u; vRing(c, p.x, p.y, r, r / 2, '#ffffff', u < .2 ? 2 : 1);
    },
    air(c, e, k) {
      const p = vPos(e);
      if (k < HIT) { const a = k / HIT, y = p.y - 60 + 52 * a * a, x = p.x + 18 * (1 - a);     // accelerating fall
        for (let i = 0; i < 10; i++) { c.globalAlpha = (1 - i / 10) * .9; c.fillStyle = i < 2 ? '#ffffff' : e.c; vPx(c, x + i * 1.8, y - i * 3.6, i < 3 ? 3 : 2); }
        return; }
      const u = (k - HIT) / (1 - HIT);
      if (u < .12) { c.globalAlpha = 1; c.fillStyle = '#ffffff'; vPx(c, p.x, p.y - 6, 9 - u * 40); }   // white impact frame
    },
    light(e, k) { const p = vPos(e); return k < HIT ? [p.x, p.y - 20, 18, .4, e.c] : [p.x, p.y - 4, 48, (1 - k) * .9, e.c]; },
  };
}

/* Sprite sheets exported from pixelfx (or drawn by hand) and packed by scripts/sheet_pack.py.
   MOD.shared.sheets comes from fx/sheets.js; images are loaded once the game is ready. */
const STELLA_IMG = {};
function stellaSheetKind() {
  return {
    air(c, e) {
      const s = MOD.shared.sheets[e.s], img = STELLA_IMG[e.s];
      if (!s || !img || !img.complete || !img.naturalWidth) return;          // not loaded yet: draw nothing
      const f = Math.min(s.frames - 1, Math.floor(e.t * s.fps)), sx = (f % s.cols) * s.w, sy = Math.floor(f / s.cols) * s.h;
      const p = vPos(e);
      c.imageSmoothingEnabled = false;
      c.translate(Math.round(p.x), Math.round(p.y)); if (e.flip) c.scale(-1, 1);
      c.drawImage(img, sx, sy, s.w, s.h, -s.px, -s.py, s.w, s.h);           // 1 sheet pixel = 1 game pixel, never a fractional scale
    },
    light(e, k) { const s = MOD.shared.sheets[e.s], p = vPos(e); return s && s.light ? [p.x, p.y - (s.light[2] || 0), s.light[0], (1 - k) * s.light[1], s.light[3] || '#ffffff'] : null; },
  };
}
/* Play a sheet at a screen point (x, y) or grid point (gx, gy). Returns false when effects are off. */
MOD.shared.sheet = (name, at) => {
  const s = MOD.shared.sheets && MOD.shared.sheets[name]; if (!s) return false;
  return !!vfx('stella_sheet', { ...at, s: name, d: s.frames / s.fps });
};

IAP.onReady(() => {
  if (typeof VFX !== 'object' || !VFX) return;
  VFX.stella_star = stellaStarKind();
  VFX.stella_fall = stellaFallKind();
  VFX.stella_sheet = stellaSheetKind();
  for (const [name, s] of Object.entries(MOD.shared.sheets || {})) { const img = new Image(); img.src = MOD.asset(s.file); STELLA_IMG[name] = img; }
});
