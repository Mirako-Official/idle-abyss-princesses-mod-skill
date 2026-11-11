'use strict';
/* Example hero for the iap-hero-mod skill: 星缀 Stella, a star mage.
   Not a finished hero: a pattern library you can copy from. Every skill shows one way to build a skill,
   every legendary one kind of item effect, and fx.js shows custom effect kinds and a pixelfx sprite sheet.
   references/skill-design.md, item-effects.md and skill-vfx.md walk through this file.
   All numbers live in STELLA_BAL; every description is built from it. */
const STELLA_BAL = {
  bolt:  { lv: 1,  cd: 5,  coef: 3.2, lock: .2, range: 7 },                       // 星矢: single target
  quake: { lv: 8,  cd: 9,  coef: 2.6, r: 2.6, stun: 1, lock: .35 },                // 坠星: area + control
  field: { lv: 18, cd: 14, coef: .5, every: .5, r: 1.8, t: 5, slow: .6 },          // 星域: ground zone
  chain: { lv: 30, cd: 7,  coef: 2.4, jumps: 4, fall: .85, gap: .08, r: 3.5 },    // 星链: bounces with delays
  ward:  { lv: 42, cd: 18, t: 6, shield: .2, dmg: .25, lock: .3 },                 // 星幕: buff
  dive:  { lv: 50, cd: 12, coef: 4, pass: 1.2, dur: .25 },                         // 流星: dash
  passive: { lifePct: 20, dmgRed: 5 },
  legends: {
    stella_staff:  { extra: 2, coef: .6 },                 // changes a skill: bolt splits
    stella_crown:  { mul: 2, cd: .7 },                     // numbers on a skill: chain ×2, cd ×0.7
    stella_gloves: { chance: .2, coef: 1.2, r: 1.5 },      // proc on basic hit
    stella_ring:   { mul: 1.4 },                           // conditional: stunned or slowed targets
    stella_boots:  { per: .04, max: 10, keep: 6 },         // stacks from kills, lost after 6 s
    stella_amulet: { every: 8 },                           // periodic: a free 星域 every 8 s
    stella_belt:   { taken: .8 },                          // defensive: less damage while shielded
  },
  sets: {
    star:  { b2: { crit: 6, intPct: 8 }, b4: { jumps: 2 }, mul: 40, skills: ['stella_bolt', 'stella_chain'] },
    earth: { b2: { armorPct: 30, intPct: 8 }, b4: { delay: .8, dmg: .5 }, mul: 40, skills: ['stella_quake', 'stella_field'] },
    veil:  { b2: { lifePct: 15, intPct: 8 }, b4: { heal: .1 }, mul: 40, skills: ['stella_dive', 'stella_bolt'] },
  },
  talents: { cap: true },
  est: { targets: 2, stunShare: .11, bootStacks: 5, amuletShare: .5 },
};
const sp = v => pv(v * 100);
const SB = STELLA_BAL, SL = SB.legends;
/* 6-piece: the route's two skills deal ×mul (read through each skill's mul hook, so combat and panel agree). */
const stellaSet6 = (k, id) => Object.entries(SB.sets).reduce((m, [name, o]) => m * (k.FX['stella_' + name + '6'] && o.skills.includes(id) ? o.mul : 1), 1);
const byDist = list => list.slice().sort((a, b) => hdist(a) - hdist(b));

/* 星链 bounce: one hit now, the next one gap seconds later. Delayed code re-checks that the fight is the same one. */
function stellaChain(from, left, coef, hitSet, id) {
  const enc = R.encounter;
  hit(from, coef, 'ww', { sk: id }); hitSet.add(from);
  if (left <= 0) return;
  later(SB.chain.gap, () => {
    if (enc !== R.encounter || R.hero.dead > 0) return;
    const next = byDist(targetable(live()).filter(m => !hitSet.has(m) && Math.hypot(m.gx - from.gx, m.gy - from.gy) < SB.chain.r))[0];
    if (!next) return;
    vfxTry(() => { const [x1, y1] = iso(from.gx, from.gy), [x2, y2] = iso(next.gx, next.gy); vfx('beam', { x1, y1: y1 - 8, x2, y2: y2 - 8, c: '#9ad8ff', w: 2, d: .18 }); });
    const fall = R.st.FX.stella_cap ? 1 : SB.chain.fall;
    stellaChain(next, left - 1, coef * fall, hitSet, id);
  });
}

registerHero({
  api: 2,
  id: 'stella',
  n: '星术师', hero: '星缀',
  main: 'int', ele: 'cold', range: 5.5, tint: '#8fc8ff',
  weapons: ['星屑短杖', '观星杖', '银河杖', '天穹杖', '星轨权杖', '星海之杖', '万象星杖'],
  offhands: ['星图', '星砂瓶', '星盘', '星核'],
  offKind: 'orb', ban: ['str', 'dex'],
  desc: '示例角色：每个技能、每件传奇都是一种常用写法。',
  pass: `生命 +${SB.passive.lifePct}%，受到的伤害 -${SB.passive.dmgRed}%`,
  bio: '技能书里的示例角色。照着她改就能做自己的角色。',
  face: [60, 46],
  lines: { skill: ['星星，落下来。'], hurt: ['唔。'], low: ['星光不够了…'], win: ['观测完毕。'], boss: ['大星座。'], elite: ['亮星。'], down: ['熄灭了…'], sleep: ['zzz…'], legend: ['是流星！'], set: ['星座连上了。'], gacha: ['许个愿。'] },
  attack: { proj: 'orb', sfx: 'zap' },
  weaponStyle: 'staff',
  icons: { weapon: 'staff', offhand: 'orb' },
  sprite: { base: 'mage', pal: { h: '#c8d8ff', H: '#8aa0d8', a: '#3a4a8a', A: '#26306a' } },
  passive(a) { a.lifePct += SB.passive.lifePct; a.dmgRed += SB.passive.dmgRed; },
  bal: STELLA_BAL,

  skills: {
    /* 1. Single target, short cast lock. A legendary changes what it does (stella_staff). */
    stella_bolt: { n: '星矢', lv: SB.bolt.lv, cd: SB.bolt.cd, icon: 'sk_chain', sfx: 'zap', tags: ['skill'],
      est: SB.bolt.coef, mul: k => stellaSet6(k, 'stella_bolt'),
      desc: `向最近的敌人射出星矢，造成 ${sp(SB.bolt.coef)}% 伤害。`,
      cast(c) {
        const list = byDist(c.near(SB.bolt.range)); if (!list.length) return false;
        c.h.ww = SB.bolt.lock;
        shoot(list[0], 'orb', SB.bolt.coef, 'ww', null, { sk: c.id });
        if (c.L.stella_staff) for (const m of list.slice(1, 1 + SL.stella_staff.extra)) shoot(m, 'orb', SB.bolt.coef * SL.stella_staff.coef, 'ww', null, { sk: c.id });
      } },
    /* 2. Area around the hero + control. The 4-piece adds a delayed second hit. */
    stella_quake: { n: '坠星', lv: SB.quake.lv, cd: SB.quake.cd, icon: 'sk_nova', sfx: 'boom', tags: ['skill'],
      est: SB.quake.coef * SB.est.targets, mul: k => stellaSet6(k, 'stella_quake'),
      desc: `召下一颗星砸向身边，对 ${SB.quake.r} 格内的敌人造成 ${sp(SB.quake.coef)}% 伤害并晕眩 ${SB.quake.stun} 秒。`,
      cast(c) {
        const nb = c.near(SB.quake.r); if (!nb.length) return false;
        c.h.ww = SB.quake.lock;
        for (const m of nb) hit(m, SB.quake.coef, 'ww', { sk: c.id, stun: SB.quake.stun });
        if (c.FX.stella_earth4) { const enc = R.encounter, b4 = SB.sets.earth.b4;
          later(b4.delay, () => { if (enc !== R.encounter || R.hero.dead > 0) return;
            for (const m of targetable(live()).filter(m => hdist(m) < SB.quake.r)) hit(m, SB.quake.coef * b4.dmg, 'ww', { sk: 'stella_quake' }); }); }
      } },
    /* 3. Ground zone: the engine ticks it (every, coef, slow). */
    stella_field: { n: '星域', lv: SB.field.lv, cd: SB.field.cd, icon: 'sk_barrier', sfx: 'cast', tags: ['skill', 'zone'],
      est: SB.field.coef * SB.field.t / SB.field.every * SB.est.targets, mul: k => stellaSet6(k, 'stella_field'),
      desc: `在敌人最密处展开 ${SB.field.t} 秒星域，每 ${SB.field.every} 秒对其中的敌人造成 ${sp(SB.field.coef)}% 伤害并减速。`,
      cast(c) {
        const t = c.densest(c.mons, SB.field.r); if (!t) return false;
        addZone({ x: t.gx, y: t.gy, r: SB.field.r, t: SB.field.t, every: SB.field.every, coef: SB.field.coef, sk: c.id, c: '#8fc8ff', slow: SB.field.slow });
      } },
    /* 4. Bounces with later(): see stellaChain above. Cap talent and 4-piece change it. */
    stella_chain: { n: '星链', lv: SB.chain.lv, cd: SB.chain.cd, icon: 'sk_chain', sfx: 'zap', tags: ['skill'],
      est: SB.chain.coef * 3.2, mul: k => stellaSet6(k, 'stella_chain') * (k.L.stella_crown ? SL.stella_crown.mul : 1),
      cdMul: k => k.L.stella_crown ? SL.stella_crown.cd : 1,
      desc: `星光在敌人之间弹跳 ${SB.chain.jumps} 次，第一下造成 ${sp(SB.chain.coef)}% 伤害，之后每次 ×${SB.chain.fall}。`,
      cast(c) {
        const t = byDist(c.near(6))[0]; if (!t) return false;
        stellaChain(t, SB.chain.jumps + (c.FX.stella_star4 ? SB.sets.star.b4.jumps : 0), SB.chain.coef, new Set(), c.id);
      } },
    /* 5. Buff: a timer on R.hero, read by hitMultiplier. hold() waits while the buff is still up. */
    stella_ward: { n: '星幕', lv: SB.ward.lv, cd: SB.ward.cd, icon: 'sk_barrier', sfx: 'cast', buff: 1, tags: ['buff'],
      desc: `${SB.ward.t} 秒内伤害 +${sp(SB.ward.dmg)}%，并获得吸收 ${sp(SB.ward.shield)}% 最大生命的护盾。`,
      hold(c) { return (c.h.stella_wardT || 0) > 1; },
      cast(c) {
        if (!c.mons.length) return false;
        c.h.ww = SB.ward.lock; c.h.stella_wardT = SB.ward.t;
        c.h.shield = Math.max(c.h.shield || 0, c.st.maxLife * SB.ward.shield);
        if (c.FX.stella_veil4) healHero(c.st.maxLife * SB.sets.veil.b4.heal, { maxLife: c.st.maxLife });
      } },
    /* 6. Dash: c.dash moves the hero over time and hits what it passes. */
    stella_dive: { n: '流星', lv: SB.dive.lv, cd: SB.dive.cd, icon: 'sk_execute', sfx: 'crit', tags: ['skill'],
      est: SB.dive.coef + SB.dive.pass, mul: k => stellaSet6(k, 'stella_dive'),
      desc: `化作流星冲向敌人最密处，沿途造成 ${sp(SB.dive.pass)}% 伤害，落地造成 ${sp(SB.dive.coef)}% 伤害。`,
      cast(c) {
        const t = c.densest(c.mons, 2); if (!t) return false;
        return c.dash(t, { dur: SB.dive.dur, col: '#b8e0ff',
          pass: m => hit(m, SB.dive.pass, 'ww', { sk: c.id }),
          end: () => { for (const m of targetable(live()).filter(m => hdist(m) < 1.6)) hit(m, SB.dive.coef, 'ww', { sk: c.id });
            vfxTry(() => { const [x, y] = iso(HX, HY); return MOD.shared.sheet('boom', { x, y }); }); } });
      } },
  },

  /* ---- item effects that are not inside a skill ---- */
  reset(h) { h.stella_wardT = 0; h.stella_stars = 0; h.stella_starT = 0; h.stella_amuletT = 0; },
  update(c, dt) {
    const h = c.h;
    if (h.stella_wardT > 0) h.stella_wardT = Math.max(0, h.stella_wardT - dt);
    if (h.stella_starT > 0 && (h.stella_starT -= dt) <= 0) h.stella_stars = 0;          // boots: stacks fall off
    if (c.L.stella_amulet && c.mons.length && (h.stella_amuletT = (h.stella_amuletT || 0) + dt) >= SL.stella_amulet.every) {
      h.stella_amuletT = 0;                                                               // amulet: a free 星域
      const t = c.densest(c.mons, SB.field.r);
      if (t) addZone({ x: t.gx, y: t.gy, r: SB.field.r, t: SB.field.t, every: SB.field.every, coef: SB.field.coef, sk: 'stella_field', c: '#8fc8ff', slow: SB.field.slow });
    }
  },
  onKill(m) {
    const h = R.hero; if (!R.st.L.stella_boots) return;
    h.stella_stars = Math.min(SL.stella_boots.max, (h.stella_stars || 0) + 1); h.stella_starT = SL.stella_boots.keep;
  },
  onBasicHit(m, st) {
    if (!st.L.stella_gloves || m.dead || !chance(SL.stella_gloves.chance)) return;     // combat randomness: chance()/rnd() only
    for (const o of targetable(live()).filter(o => Math.hypot(o.gx - m.gx, o.gy - m.gy) < SL.stella_gloves.r)) hit(o, SL.stella_gloves.coef, 'proc');
    vfxTry(() => vfx('flash', { gx: m.gx, gy: m.gy, r: 10, c: '#b8e0ff', d: .16, oy: -6 }));
  },
  hitMultiplier(m, src, opt) {
    const h = R.hero, L = R.st.L; let k = 1;
    if (h.stella_wardT > 0) k *= 1 + SB.ward.dmg;
    if (L.stella_ring && (hasStatus(m, 'stun') || hasStatus(m, 'slow'))) k *= SL.stella_ring.mul;
    if (L.stella_boots && h.stella_stars) k *= 1 + SL.stella_boots.per * h.stella_stars;
    return k;
  },
  hurtMultiplier(h, st) { return st.L.stella_belt && h.shield > 0 ? SL.stella_belt.taken : 1; },
  resource: (h, st) => st.L.stella_boots ? { v: h.stella_stars || 0, max: SL.stella_boots.max, c: '#5a8ad8', label: '星辉' } : null,

  /* Panel estimate: average uptime of everything above. No side effects. */
  estimate(K) {
    const E = SB.est; let dmg = 1;
    if (K.eq.includes('stella_ward')) dmg *= 1 + SB.ward.dmg * Math.min(1, SB.ward.t / K.skCd('stella_ward'));
    if (K.L.stella_ring) dmg *= 1 + (SL.stella_ring.mul - 1) * (K.eq.includes('stella_field') ? .6 : E.stunShare);
    if (K.L.stella_boots) dmg *= 1 + SL.stella_boots.per * E.bootStacks;
    if (K.L.stella_gloves && K.eff > 0) dmg *= 1 + K.dps * SL.stella_gloves.chance * SL.stella_gloves.coef * E.targets / K.eff;
    if (K.L.stella_amulet && K.eff > 0) dmg *= 1 + K.avg * SB.field.coef * SB.field.t / SB.field.every * E.targets * E.amuletShare / SL.stella_amulet.every / K.eff;
    const ehp = K.L.stella_belt && K.eq.includes('stella_ward') ? 1 / (1 - (1 - SL.stella_belt.taken) * .5) : 1;
    return { dmg, ehp };
  },

  talents: [
    { n: '星矢', route: 'star', skills: ['stella_bolt', 'stella_chain', 'stella_ward'], c: '#8fc8ff',
      nodes: transitionNodes(T('stella_t1', '星芒', { crit: 1.5 }, 't_eye'), T('stella_t2', '星辉', { skill: 8 }, 't_rune'), T('stella_t3', '流光', { cdr: 3 }, 't_hourglass'),
        CAP('stella_t4', '永不衰减', 'stella_cap', '星链每次弹跳的伤害不再衰减。')) },
    { n: '坠星', route: 'earth', skills: ['stella_quake', 'stella_field', 'stella_ward'], c: '#c8a8ff',
      nodes: transitionNodes(T('stella_t5', '引力', { area: 6 }, 't_rune'), T('stella_t6', '星尘', { ele: 6 }, 't_drop'), T('stella_t7', '沉重', { eliteDmg: 6 }, 't_skull'),
        CAP('stella_t8', '星辰之怒', 'skillcrit', '技能的暴击几率 +20%。')) },
    { n: '星幕', route: 'veil', skills: ['stella_dive', 'stella_bolt', 'stella_ward'], c: '#b8e0ff',
      nodes: transitionNodes(T('stella_t9', '护佑', { lifePct: 5 }, 't_heart'), T('stella_t10', '星甲', { armorPct: 8 }, 't_shield'), T('stella_t11', '流转', { ls: .4 }, 't_drop'),
        CAP('stella_t12', '不屈', 'unbreak', '受到致命伤害时保留 1 点生命。')) },
  ],
  legends: [
    { k: 'stella_staff',  t: 'weapon', route: 'star',  name: '分光星杖', desc: `星矢同时射向另外 ${SL.stella_staff.extra} 个敌人，造成 ${sp(SL.stella_staff.coef)}% 的伤害。`, fl: '一颗星，三道光。' },
    { k: 'stella_crown',  t: 'helm',   route: 'star',  name: '连星之冠', desc: `星链伤害 ×${SL.stella_crown.mul}，冷却 ×${SL.stella_crown.cd}。`, fl: '把星星连起来，就是星座。' },
    { k: 'stella_gloves', t: 'gloves', route: 'earth', name: '落星手套', desc: `普通攻击有 ${sp(SL.stella_gloves.chance)}% 几率砸下小星，对目标周围 ${SL.stella_gloves.r} 格造成 ${sp(SL.stella_gloves.coef)}% 伤害。`, fl: '手一滑，星就掉了。' },
    { k: 'stella_ring',   t: 'ring',   route: 'earth', name: '定星指环', desc: `对晕眩或减速中的敌人伤害 ×${SL.stella_ring.mul}。`, fl: '别动，让我看清楚。' },
    { k: 'stella_boots',  t: 'boots',  route: 'veil',  name: '追星之靴', desc: `每次击杀获得 1 层星辉（最多 ${SL.stella_boots.max} 层），每层伤害 +${sp(SL.stella_boots.per)}%；${SL.stella_boots.keep} 秒没有击杀就清空。`, fl: '追着流星跑。' },
    { k: 'stella_amulet', t: 'amulet', route: 'veil',  name: '星图坠饰', desc: `每 ${SL.stella_amulet.every} 秒自动在敌人最密处展开一次星域（不占冷却）。`, fl: '星图会自己转。' },
    { k: 'stella_belt',   t: 'belt',   route: 'veil',  name: '星幕腰带', desc: `有护盾时受到的伤害 ×${SL.stella_belt.taken}。`, fl: '星光也能挡刀。' },
  ],
  sets: [
    { key: 'stella_star', name: '星矢之装', route: 'star', pieces: { helm: '星矢头冠', shoulders: '星矢肩饰', armor: '星矢法袍', gloves: '星矢手套', pants: '星矢长裙', belt: '星矢腰带', boots: '星矢短靴' },
      b: [[2, `暴击几率 +${SB.sets.star.b2.crit}%，智力 +${SB.sets.star.b2.intPct}%`, SB.sets.star.b2], [4, `星链多弹跳 ${SB.sets.star.b4.jumps} 次`, { fx: 'stella_star4' }], [6, `星矢、星链伤害 ×${SB.sets.star.mul}`, { fx: 'stella_star6' }]] },
    { key: 'stella_earth', name: '坠星之装', route: 'earth', pieces: { helm: '坠星头冠', shoulders: '坠星肩饰', armor: '坠星法袍', gloves: '坠星手套', pants: '坠星长裙', belt: '坠星腰带', boots: '坠星短靴' },
      b: [[2, `护甲 +${SB.sets.earth.b2.armorPct}%，智力 +${SB.sets.earth.b2.intPct}%`, SB.sets.earth.b2], [4, `坠星 ${SB.sets.earth.b4.delay} 秒后再砸一次，造成 ${sp(SB.sets.earth.b4.dmg)}% 的伤害`, { fx: 'stella_earth4' }], [6, `坠星、星域伤害 ×${SB.sets.earth.mul}`, { fx: 'stella_earth6' }]] },
    { key: 'stella_veil', name: '星幕之装', route: 'veil', pieces: { helm: '星幕头冠', shoulders: '星幕肩饰', armor: '星幕法袍', gloves: '星幕手套', pants: '星幕长裙', belt: '星幕腰带', boots: '星幕短靴' },
      b: [[2, `生命 +${SB.sets.veil.b2.lifePct}%，智力 +${SB.sets.veil.b2.intPct}%`, SB.sets.veil.b2], [4, `星幕同时回复 ${sp(SB.sets.veil.b4.heal)}% 最大生命`, { fx: 'stella_veil4' }], [6, `流星、星矢伤害 ×${SB.sets.veil.mul}`, { fx: 'stella_veil6' }]] },
  ],

  /* Signature effects, called after each successful cast (draw only: vrnd, never Math.random). */
  vfx: {
    stella_bolt:  () => { const m = vNear(); if (m) vfx('stella_star', { ...vAt(m), c: '#b8e0ff', d: .45 }); },
    stella_quake: () => { vfx('stella_fall', { follow: true, c: '#c8a8ff', d: .55 }); vfx('crack', { follow: true, c: '#c8a8ff', n: 6, len: 2.2, d: .7 }); },
    stella_field: () => { const m = vDense(SB.field.r); if (m) vfx('rune', { ...vAt(m), r: SB.field.r, c: '#8fc8ff', c2: '#e8f4ff', d: SB.field.t }); },
    stella_chain: () => { const m = vNear(); if (m) vfx('flash', { ...vAt(m), r: 9, c: '#9ad8ff', d: .16, oy: -8 }); },
    stella_dive:  () => { },        // empty on purpose: the explosion plays from end() where she lands; an entry also turns off the generic effect
    stella_ward:  () => { vfx('bubble', { follow: true, c: '#8fc8ff', c2: '#ffffff', d: SB.ward.t, until: () => R.hero.stella_wardT > 0 }); vfx('aura', { follow: true, c: '#b8e0ff', d: SB.ward.t, rate: 6 }); },
  },
});
