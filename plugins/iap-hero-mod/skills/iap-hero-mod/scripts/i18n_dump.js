/* SPDX-License-Identifier: MIT
   Copyright (c) 2026 Mirako

   Idle Abyss Princesses: list every text of a mod hero exactly as the game renders it (numbers from
   your balance table included) and which languages still have no translation for it.

   Why: mod translations are { "Chinese source": "translation" } maps keyed by the WHOLE rendered
   sentence. Skill descriptions are template strings filled from numbers at load time, so the key is
   "造成 1400% 伤害", not the source code. Reading the strings out of the running game is the only
   reliable way to get the keys right.

   How:
     1. Start the game with the launch option  --devtools  (Steam: right-click the game > Properties >
        Launch options). The mod must be enabled and loaded (Settings > Mods shows it as loaded).
     2. In the DevTools console, paste this whole file and press Enter.
     3. Run  iapDump('your_hero_id')   (or iapDump() while playing that hero).
        The JSON is copied to the clipboard: paste it into work/strings.json for the assistant.
   Texts your code builds at run time (floating combat text, chat windows, banners) are not in the
   game's tables: search your scripts for Chinese inside function calls and translate those too. */
(() => {
  const CJK = /[㐀-鿿豈-﫿]/;
  window.iapDump = (id) => {
    id = id || (typeof S !== 'undefined' && S && S.cls);
    const H = typeof HEROES === 'object' && HEROES[id];
    if (!H) { console.warn('Unknown hero id', id, '- mod heroes:', Object.keys(HEROES).filter(k => HEROES[k].mod)); return null; }
    const found = new Map();
    const add = (s, where) => { if (typeof s === 'string' && CJK.test(s) && !found.has(s)) found.set(s, where); };
    for (const k of ['n', 'hero', 'desc', 'pass', 'bio']) add(H[k], k);
    (H.weapons || []).forEach(s => add(s, 'weapon name')); (H.offhands || []).forEach(s => add(s, 'offhand name'));
    for (const [k, arr] of Object.entries(H.lines || {})) (arr || []).forEach(s => add(s, 'line ' + k));
    for (const [k, sk] of Object.entries(SKILLS)) if (sk.cls === id) {
      add(sk.n, 'skill ' + k); if (typeof sk.desc === 'string') add(sk.desc, 'skill ' + k + ' description'); (sk.say || []).forEach(s => add(s, 'skill ' + k + ' shout'));
    }
    for (const tree of (TALENTS[id] || [])) {
      add(tree.n, 'talent tree');
      for (const nd of tree.nodes || []) {
        add(nd.n, 'talent ' + nd.id); if (typeof nd.desc === 'string') add(nd.desc, 'talent ' + nd.id + ' description');
        for (const o of nd.opts || []) { add(o.n, 'talent ' + nd.id + ' choice'); add(o.desc, 'talent ' + nd.id + ' choice description'); }
      }
    }
    for (const [k, L] of Object.entries(LEG)) if (L.cls === id) { add(L.name, 'legendary ' + k); add(L.desc, 'legendary ' + k + ' power'); add(L.fl, 'legendary ' + k + ' flavour'); }
    for (const [k, st] of Object.entries(SETS)) if (st.cls === id) {
      add(st.name, 'set ' + k); Object.values(st.pieces || {}).forEach(p => add(p, 'set ' + k + ' piece')); (st.b || []).forEach(b => add(b[1], 'set ' + k + ' bonus'));
    }
    const ct = H.court;
    if (ct) {
      add(ct.setName, 'court set'); Object.values(ct.pieces || {}).forEach(p => add(p, 'court piece'));
      for (const v of Object.values(ct.items || {})) { if (typeof v === 'string') add(v, 'court item'); else if (v) { add(v.name, 'court item'); add(v.power, 'court power'); } }
    }
    try { if (H.resource && S && S.cls === id && R.hero && R.st) { const rs = H.resource(R.hero, R.st); if (rs) add(rs.label, 'resource bar label'); } } catch (e) { }
    const langs = Object.keys(I18N).filter(l => l !== 'zh');
    const mine = ((typeof MODS === 'object' && MODS.list || []).find(m => m.id === H.mod) || {}).i18n || {};
    const strings = [...found.entries()].map(([zh, where]) => ({ zh, where, missing: langs.filter(l => !(I18N[l] && I18N[l][zh])) }));
    /* mod translations never override the game's own dictionary: when both have the sentence and they differ, the game wins */
    const conflicts = [];
    for (const x of strings) for (const l of langs) {
      const m = mine[l] && mine[l][x.zh], g = I18N[l] && I18N[l][x.zh];
      if (m && g && m !== g) conflicts.push({ zh: x.zh, lang: l, yours: m, game: g });
    }
    const res = { hero: id, mod: H.mod || null, total: strings.length,
      missing: Object.fromEntries(langs.map(l => [l, strings.filter(x => x.missing.includes(l)).length])), conflicts, strings };
    const text = JSON.stringify(res, null, 1);
    try { copy(text); console.log(`iapDump: ${strings.length} texts copied to the clipboard`); } catch (e) { console.log(text); }
    console.table(res.missing);
    if (conflicts.length) console.warn(`iapDump: ${conflicts.length} of your translations are shadowed by the game's dictionary (see "conflicts"): reword those Chinese texts`);
    return res;
  };
  console.log("iapDump ready: run iapDump('your_hero_id')");
})();
