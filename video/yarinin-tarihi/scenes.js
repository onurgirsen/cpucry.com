'use strict';
/* Storyboard. 80 BPM → 1 bar = 3 s. Scene text timings are in beats. */

function at(ctx, x, y, s, fn) { ctx.save(); ctx.translate(x, y); if (s !== 1) ctx.scale(s, s); fn(); ctx.restore(); }
function ill(name, ctx, th, sc, x, y, s = 1, o) {
  if (!ILL[name]) return;
  at(ctx, x, y, s, () => ILL[name](ctx, th, sc, o));
}

const STY = {
  s: { size: 58, weight: 700, color: 'text', fx: 'rise', spacing: 6 },
  m: { size: 84, weight: 800, color: 'text', fx: 'rise', spacing: 5 },
  b: { size: 118, weight: 900, color: 'accent', fx: 'smear', spacing: 3, lead: 1.0 },
};
/* left-aligned kinetic headline: rows = [[text, style, overrides?]] */
function T(rows, caption, o = {}) {
  const beats = o.beats ?? 0.62, start = o.start ?? 0;
  const lines = rows.map(([text, k, ov], i) => Object.assign({ text, at: start + i * beats }, STY[k], ov || {}));
  const hgt = lines.reduce((s, L) => s + L.size * ((L.lead ?? 0.92) + 0.16), 0);
  return {
    x: o.x ?? 120, y: o.y ?? Math.round(505 - hgt / 2), align: o.align || 'left', lines,
    caption: caption ? { text: caption, at: o.capAt ?? start + rows.length * beats + 0.3 } : null,
    out: o.out,
  };
}
function TC(rows, caption, o = {}) { return T(rows, caption, Object.assign({ x: W / 2, align: 'center' }, o)); }

const CH = {
  0: '0 · ÖNSÖZ', 1: 'I · ZEKÂ ÇAĞI', 2: 'II · YILDIZ ATEŞİ', 3: 'III · DENGE', 4: 'IV · YAŞAM', 5: 'V · AY',
  6: 'VI · KIZIL GEZEGEN', 7: 'VII · GÜNEŞ', 8: 'VIII · YENİ YÜZYIL', 9: 'IX · YILDIZLAR', 10: 'X · İNSAN',
};

function card(n, year, theme) {
  const from = year === 2030 ? 2026 : year - 10;
  return {
    id: 'card' + year, bars: 1, theme, card: true, chapter: CH[n], years: [from, year], trans: 'flash', cue: 'card',
    focus: [W / 2, H / 2], zoom: 0.06, bloom: theme === 'parchment' ? 0 : 0.3,
    draw: (ctx, th, sc) => at(ctx, W / 2, H / 2 - 20, 1, () =>
      ILL.card(ctx, th, sc, { year, from, chapter: CH[n], sub: `O, ${year - 2026} yaşında.` })),
  };
}
/* standard content scene: illustration on the right, headline on the left.
   The drawing gets a short pre-roll so the first frame after a cut is never empty. */
const PRE = 0.45;
function S(id, n, theme, years, illName, rows, caption, o = {}) {
  const [x, y, s] = o.pos || [1270, 520, 1];
  return Object.assign({
    id, bars: 1, theme, chapter: CH[n], years, cue: 'cut', focus: [x, y],
    draw: (ctx, th, sc) => ill(illName, ctx, th, Object.assign({}, sc, { t: sc.t + PRE, p: clamp((sc.t + PRE) / sc.dur) }), x, y, s, o.illOpt),
    text: T(rows, caption, o.text || {}),
  }, o.scene || {});
}

const SCENES = [
  // ---------------------------------------------------------------- prologue
  {
    id: 'intro', bars: 2, theme: 'cosmic', chapter: CH[0], years: [2026, 2026], hud: 0, trans: 'black', transDur: 1.5,
    cue: 'intro', focus: [W / 2, H / 2], zoom: 0.07, bloom: 1.0,
    draw: (ctx, th, sc) => {
      at(ctx, W / 2, 560, 1, () => ILL.astrolabe(ctx, th, sc, { prog: E.inOut(clamp(sc.t / 5)), alpha: 0.32 }));
      ILL.spark(ctx, sc, W / 2, 700, lerp(0.15, 0.6, E.out(clamp(sc.t / 5.5))), 3);
    },
    text: TC([['BU, HENÜZ YAŞANMAMIŞ', 's', { at: 1.2, stagger: 0.55, spacing: 12 }], ['BİR TARİH.', 'b', { at: 4.0, fx: 'zoom', size: 124, spacing: 10 }]], null, { y: 300 }),
  },
  {
    id: 'title', bars: 2, theme: 'cosmic', chapter: CH[0], years: [2026, 2026], hud: 0, cue: 'title',
    focus: [W / 2, H / 2], zoom: 0.09, bloom: 1.1, outWhite: 0.45,
    draw: (ctx, th, sc) => {
      rays(ctx, th, W / 2, H / 2, 70, 80, 1200, 0.08 * E.out(clamp(sc.t / 2)), sc.T * 0.02);
      at(ctx, W / 2, H / 2, 1.25, () => ILL.astrolabe(ctx, th, sc, { prog: 1, alpha: 0.26 }));
      ILL.spark(ctx, sc, W / 2, 700, 0.6 + 0.25 * E.out(clamp(sc.t / 3)), 3);
    },
    text: TC([['YARININ', 's', { size: 92, spacing: 34, at: 0 }], ['TARİHİ', 'b', { size: 230, spacing: 18, at: 0.5, fx: 'zoom', dur: 0.9 }]],
      '2026 → 2120  ·  BİR İNSAN ÖMRÜ', { y: 290, capAt: 2.2 }),
  },
  {
    id: 'birth', bars: 2, theme: 'parchment', chapter: CH[0], years: [2026, 2026], hud: sc => E.out(clamp(sc.t / 1.2)),
    trans: 'flash', cue: 'birth', focus: [1250, 470], zoom: 0.05,
    draw: (ctx, th, sc) => {
      rays(ctx, th, 1250, 440, 90, 230, 950, 0.07, sc.T * 0.015);
      at(ctx, 1250, 440, 1, () => {
        ILL.footprint(ctx, th, sc, { prog: clamp(sc.t / 2.2), scale: 1.3 });
        ILL.stamp(ctx, th, sc, 270, -170, '2026', 'DOĞUM', ramp(sc.t, 2.1, 0.35));
        ILL.lifeTrail(ctx, th, sc, ramp(sc.t, 3.4, 2.2));
      });
    },
    text: [
      T([['2026.', 'b', { size: 160, fx: 'drop', at: 0.2 }], ['BİR ÇOCUK DOĞDU.', 's', { at: 1.3 }]], null, { y: 360, out: 3.7 }),
      T([['BU, ONUN GÖRECEĞİ', 's', { at: 4.15 }], ['DÜNYA.', 'b', { size: 160, at: 4.9 }]], null, { y: 360 }),
    ],
  },

  // ---------------------------------------------------------------- 2030 · intelligence
  card(1, 2030, 'parchment'),
  S('neural', 1, 'parchment', [2030, 2031], 'neural', [['MAKİNELER', 's'], ['DÜŞÜNMEYİ', 'b'], ['ÖĞRENDİ.', 's']], 'YAPAY GENEL ZEKÂ · 2030', { pos: [1390, 500, 0.85] }),
  S('robot', 1, 'parchment', [2032, 2034], 'robot', [['HER EVE', 's'], ['BİR ROBOT.', 'b']], 'İNSANSI ROBOTLAR · 2033', { pos: [1330, 560, 0.92] }),
  S('museum', 1, 'parchment', [2035, 2038], 'museum', [['DİREKSİYON', 's'], ['MÜZELİK', 'b'], ['OLDU.', 's']], 'SÜRÜCÜSÜZ ULAŞIM · 2037', { pos: [1320, 500, 0.86] }),

  // ---------------------------------------------------------------- 2040 · star fire
  card(2, 2040, 'parchment'),
  S('tokamak', 2, 'dark', [2040, 2042], 'tokamak', [['BİR YILDIZI', 's'], ['ŞİŞEYE', 'b'], ['KOYDUK.', 's']], 'FÜZYON ENERJİSİ · 2041', { pos: [1290, 540, 1.05], scene: { bloom: 1.0 } }),
  S('marsprint', 2, 'parchment', [2043, 2045], 'marsPrint', [["MARS'TA İLK", 's'], ['AYAK İZİ.', 'b']], 'İLK İNSANLI İNİŞ · 2044', { pos: [1190, 520, 1], text: { y: 250 } }),
  S('cancer', 2, 'parchment', [2046, 2049], 'cancer', [['KANSER', 's'], ['YENİLDİ.', 'b']], 'KİŞİYE ÖZEL mRNA AŞILARI · 2048', { pos: [1300, 560, 1.18] }),

  // ---------------------------------------------------------------- 2050 · balance
  card(3, 2050, 'parchment'),
  S('carbon', 3, 'parchment', [2050, 2052], 'carbon', [['KARBON EĞRİSİ', 's'], ['BÜKÜLDÜ.', 'b']], 'NET SIFIR EMİSYON · 2050', { pos: [1300, 500, 1] }),
  S('bci', 3, 'parchment', [2053, 2055], 'bci', [['DÜŞÜNCEYLE', 's'], ['KONUŞUYORUZ.', 'b', { size: 94 }]], 'BEYİN–BİLGİSAYAR ARAYÜZÜ · 2053', { pos: [1330, 640, 0.86] }),
  S('vfarm', 3, 'parchment', [2056, 2059], 'vfarm', [['TARLALAR', 's'], ['GÖĞE', 'b'], ['YÜKSELDİ.', 's']], 'DİKEY TARIM · 2057', { pos: [1320, 480, 1.08] }),

  // ---------------------------------------------------------------- 2060 · life
  card(4, 2060, 'parchment'),
  S('dna', 4, 'parchment', [2060, 2062], 'dna', [['KALITSAL HASTALIK', 's'], ['KALMADI.', 'b']], 'GEN DÜZENLEME · 2061', { pos: [1300, 500, 1] }),
  S('organ', 4, 'parchment', [2063, 2065], 'organ', [['ORGANLAR', 's'], ['BASILIYOR.', 'b']], 'BİYO-YAZICILAR · 2064', { pos: [1320, 530, 1] }),
  S('clock', 4, 'parchment', [2066, 2069], 'clock', [['YAŞLANMAYI', 's'], ['DURDURDUK.', 'b']], 'UZUN ÖMÜR TEDAVİLERİ · 2068', { pos: [1320, 520, 1] }),

  // ---------------------------------------------------------------- 2070 · moon
  card(5, 2070, 'dark'),
  S('moon', 5, 'cosmic', [2070, 2072], 'moon', [["AY'DA", 's'], ['İLK ŞEHİR.', 'b']], 'SHACKLETON KRATERİ · 2071', { pos: [1250, 600, 1] }),
  S('asteroid', 5, 'cosmic', [2073, 2075], 'asteroid', [['ASTEROİTLERDE', 's'], ['MADENCİLİK.', 'b', { size: 108 }]], '16 PSYCHE · DEMİR · NİKEL · 2074', { pos: [1300, 520, 1] }),
  S('elevator', 5, 'cosmic', [2076, 2079], 'elevator', [['YÖRÜNGEYE', 's'], ['ASANSÖRLE.', 'b']], 'UZAY ASANSÖRÜ · 2078', { pos: [1300, 540, 1] }),

  // ---------------------------------------------------------------- 2080 · red planet
  card(6, 2080, 'dark'),
  S('mars1m', 6, 'cosmic', [2080, 2083], 'mars', [["MARS'TA", 's'], ['BİR MİLYON', 'b'], ['İNSAN.', 's']], 'YEDİ ŞEHİR · 2082', { pos: [1320, 520, 1], illOpt: { lights: true } }),
  S('marsgreen', 6, 'cosmic', [2084, 2087], 'mars', [['KIZIL GEZEGEN', 's'], ['YEŞERİYOR.', 'b', { color: '#9fd6a0' }]], 'TERAFORMİNG · 2086', { pos: [1320, 520, 1], illOpt: { lights: true, green: true } }),
  S('earth', 6, 'cosmic', [2088, 2089], 'earth', [['DÜNYA', 's'], ['NEFES ALIYOR.', 'b', { size: 100, color: '#9fd0ff' }]], 'ORMANLAR GERİ DÖNDÜ · 2089', { pos: [1330, 520, 1] }),

  // ---------------------------------------------------------------- 2090 · sun
  card(7, 2090, 'dark'),
  S('dyson', 7, 'cosmic', [2090, 2093], 'dyson', [["GÜNEŞ'İN ETRAFINA", 's'], ['AYNALAR', 'b'], ['ÖRDÜK.', 's']], 'DYSON SÜRÜSÜ · İLK HALKA · 2091', { pos: [1300, 520, 1], scene: { bloom: 1.0 } }),
  S('rocket', 7, 'cosmic', [2094, 2096], 'rocket', [["MARS'A", 's'], ['30 GÜNDE.', 'b']], 'FÜZYON ROKETLERİ · 2095', { pos: [1330, 540, 1] }),
  S('galaxy', 7, 'cosmic', [2097, 2099], 'galaxy', [['KARANLIK MADDE', 's'], ['ÇÖZÜLDÜ.', 'b']], 'EVRENİN KAYIP KÜTLESİ · 2098', { pos: [1300, 520, 1] }),

  // ---------------------------------------------------------------- 2100 · new century
  card(8, 2100, 'cosmic'),
  S('typeI', 8, 'cosmic', [2100, 2102], 'typeI', [['KARDAŞEV', 'm'], ['TİP I.', 'b', { size: 210, fx: 'zoom', dur: 0.8 }]], 'GEZEGENİN TÜM ENERJİSİ · 10¹⁶ W', { pos: [1330, 520, 1], scene: { bars: 2, cue: 'big', bloom: 1.05 }, text: { beats: 1.0, start: 0.4 } }),
  S('sail', 8, 'cosmic', [2103, 2105], 'sail', [['YILDIZLARA', 's'], ['İLK YELKEN.', 'b']], 'ALPHA CENTAURI · 4,37 IŞIK YILI', { pos: [1300, 520, 1] }),

  // ---------------------------------------------------------------- 2110 · stars
  card(9, 2110, 'cosmic'),
  S('oneill', 9, 'cosmic', [2110, 2113], 'oneill', [['YÖRÜNGEDE', 's'], ['YÜZLERCE', 'b'], ['ŞEHİR.', 's']], "O'NEILL SİLİNDİRLERİ · 2112", { pos: [1390, 520, 0.84] }),
  S('proxima', 9, 'cosmic', [2114, 2116], 'proxima', [['BAŞKA BİR DÜNYANIN', 's'], ['FOTOĞRAFI.', 'b']], 'PROXIMA CENTAURI b · 2116', { pos: [1330, 520, 1] }),
  S('spectrum', 9, 'cosmic', [2117, 2119], 'spectrum', [['YALNIZ', 's'], ['DEĞİLİZ.', 'b', { size: 140 }]], 'BİYOİMZA: O₂ · H₂O · CH₄ · 2118', { pos: [1300, 540, 1], scene: { bloom: 0.4 } }),

  // ---------------------------------------------------------------- 2120 · human
  card(10, 2120, 'cosmic'),
  {
    id: 'young', bars: 1, theme: 'cosmic', chapter: CH[10], years: [2120, 2120], cue: 'young', focus: [W / 2, H / 2], zoom: 0.04, trans: 'black', transDur: 0.3,
    draw: (ctx, th, sc) => ill('ecg', ctx, th, sc, W / 2, 700, 1),
    text: TC([['…VE HÂLÂ', 's', { size: 70, spacing: 14 }], ['GENÇ.', 'b', { size: 190, fx: 'zoom', dur: 0.7 }]], null, { y: 250, beats: 1.0, start: 0.3 }),
  },
  {
    id: 'medallions', bars: 2, theme: 'cosmic', chapter: CH[10], years: [2120, 2120], cue: 'medal', focus: [W / 2, H / 2], zoom: 0.05, bloom: 1.0,
    draw: (ctx, th, sc) => ill('medallions', ctx, th, sc, W / 2, 560, 1),
    text: TC([['YÜZ YILDA', 's', { size: 64, spacing: 12 }], ['BİN YILLIK YOL.', 'b', { size: 128 }]], null, { y: 120, beats: 1.0, start: 1.2 }),
  },
  {
    id: 'future', bars: 1, theme: 'cosmic', chapter: CH[10], years: [2120, 2120], cue: 'future', focus: [W / 2, H / 2], zoom: 0.05, trans: 'black', transDur: 0.25,
    draw: (ctx, th, sc) => { at(ctx, W / 2, H / 2, 1.5, () => ILL.astrolabe(ctx, th, sc, { prog: 1, alpha: 0.16 })); },
    text: TC([['GELECEK', 'm', { size: 130, spacing: 16, color: 'text', fx: 'rise' }], ['GELMEZ.', 'm', { size: 130, spacing: 16, at: 1.4, fx: 'rise' }]], null, { y: 330, beats: 1.2, start: 0.1 }),
  },
  {
    id: 'final', bars: 2, theme: 'cosmic', chapter: CH[10], years: [2120, 2120], cue: 'final', focus: [W / 2, H / 2], zoom: 0.07, bloom: 1.25, trans: 'flash',
    draw: (ctx, th, sc) => ill('build', ctx, th, sc, W / 2, H / 2, 1),
    text: TC([['İNŞA', 'b', { size: 230, spacing: 24, fx: 'zoom', dur: 0.8 }], ['EDİLİR.', 'b', { size: 230, spacing: 24, fx: 'zoom', dur: 0.8 }]], null, { y: 250, beats: 1.0, start: 0.0 }),
  },
  {
    id: 'end', bars: 2, theme: 'cosmic', chapter: CH[10], years: [2120, 2120], hud: sc => 1 - E.out(clamp(sc.t / 1.2)), cue: 'end',
    focus: [W / 2, H / 2], zoom: 0.03, outBlack: 2.2, trans: 'black', transDur: 0.8,
    draw: (ctx, th, sc) => ILL.spark(ctx, sc, W / 2, 690, 0.35, 5),
    text: TC([['YARININ TARİHİ', 'm', { size: 96, spacing: 22, color: 'accent', at: 0.4 }], ['bir insan ömrü · yüz yıl · sonsuz ihtimal', 's', { fam: 'italic', weight: 600, size: 50, spacing: 1, at: 1.6, fx: 'rise' }]],
      '2026 — 2120', { y: 360, capAt: 2.4 }),
  },
];
