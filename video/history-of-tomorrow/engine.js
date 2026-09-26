'use strict';
/* A History of Tomorrow — deterministic canvas renderer.
   Every frame is a pure function of time t (seconds): renderFrame(t). */

const W = 1920, H = 1080, FPS = 30;
const BPM = 80, BEAT = 60 / BPM, BAR = 4 * BEAT;
const TAU = Math.PI * 2;

// ---------------------------------------------------------------- math
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, t) => a + (b - a) * t;
const smooth = t => { t = clamp(t); return t * t * (3 - 2 * t); };
const E = {
  out: t => 1 - Math.pow(1 - clamp(t), 3),
  in: t => Math.pow(clamp(t), 3),
  inOut: t => { t = clamp(t); return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; },
  outExpo: t => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * clamp(t))),
  outBack: t => { t = clamp(t); const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
};
const ramp = (t, a, d) => clamp((t - a) / d);           // 0 → 1 over [a, a+d]
const pulse = (t, a, d) => clamp((t - a) / d) * clamp((a + 2 * d - t) / d);

function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const hash = n => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };
const noise1 = x => { const i = Math.floor(x), f = x - i; return lerp(hash(i), hash(i + 1), smooth(f)); };

function mk(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }

// ---------------------------------------------------------------- fonts
const FAM = { serif: '"Cinzel"', italic: '"Cormorant Garamond"', mono: '"JetBrains Mono"' };
function setFont(ctx, fam, size, weight = 700, style = 'normal') {
  ctx.font = `${fam === 'italic' ? 'italic' : style} ${weight} ${size}px ${FAM[fam]}`;
}

// ---------------------------------------------------------------- themes
const THEMES = {
  parchment: {
    name: 'parchment', dark: false,
    ink: '#2a2017', soft: 'rgba(42,32,23,0.55)', faint: 'rgba(42,32,23,0.2)',
    accent: '#a3241a', accentSoft: 'rgba(163,36,26,0.5)',
    text: '#1f1811', caption: 'rgba(42,32,23,0.62)',
    hud: 'rgba(42,32,23,0.82)', hudFaint: 'rgba(42,32,23,0.46)', hudBar: '#a3241a',
    fill: 'rgba(120,86,46,0.13)', fillDeep: 'rgba(90,62,32,0.28)', paper: '#dccaa6',
  },
  dark: {
    name: 'dark', dark: true,
    ink: '#eadcbd', soft: 'rgba(234,220,189,0.55)', faint: 'rgba(234,220,189,0.16)',
    accent: '#f4c469', accentSoft: 'rgba(244,196,105,0.5)',
    text: '#f3e9d2', caption: 'rgba(236,224,198,0.62)',
    hud: 'rgba(236,226,202,0.82)', hudFaint: 'rgba(236,226,202,0.32)', hudBar: '#f4c469',
    fill: 'rgba(244,196,105,0.06)', fillDeep: 'rgba(244,196,105,0.14)', paper: '#0c0e13',
  },
};
THEMES.cosmic = Object.assign({}, THEMES.dark, { name: 'cosmic' });

function col(th, c) {
  if (!c || c === 'text') return th.text;
  if (c === 'accent') return th.accent;
  if (c === 'ink') return th.ink;
  if (c === 'soft') return th.soft;
  return c;
}

// ---------------------------------------------------------------- textures (built once)
const TEX = {};
function buildTextures() {
  // parchment
  {
    const c = mk(W + 160, H + 160), x = c.getContext('2d'), R = rng(7);
    x.fillStyle = '#d9c7a1'; x.fillRect(0, 0, c.width, c.height);
    const octave = (gw, gh, blur, alpha, mode, lo, hi) => {
      const s = mk(gw, gh), sx = s.getContext('2d'), id = sx.createImageData(gw, gh);
      for (let i = 0; i < id.data.length; i += 4) {
        const v = lo + R() * (hi - lo);
        id.data[i] = v; id.data[i + 1] = v * 0.86; id.data[i + 2] = v * 0.66; id.data[i + 3] = 255;
      }
      sx.putImageData(id, 0, 0);
      x.save(); x.globalAlpha = alpha; x.globalCompositeOperation = mode;
      x.imageSmoothingEnabled = true; x.imageSmoothingQuality = 'high';
      x.filter = `blur(${blur}px)`;
      x.drawImage(s, -blur * 3, -blur * 3, c.width + blur * 6, c.height + blur * 6);
      x.restore();
    };
    octave(14, 9, 60, 0.55, 'multiply', 170, 255);
    octave(48, 28, 22, 0.35, 'multiply', 190, 255);
    octave(160, 90, 5, 0.18, 'multiply', 200, 255);
    for (let i = 0; i < 90; i++) {              // stains
      const px = R() * c.width, py = R() * c.height, r = 20 + R() * 160;
      const g = x.createRadialGradient(px, py, 0, px, py, r);
      const a = 0.03 + R() * 0.07;
      g.addColorStop(0, `rgba(110,72,34,${a})`); g.addColorStop(0.7, `rgba(110,72,34,${a * 0.5})`); g.addColorStop(1, 'rgba(110,72,34,0)');
      x.fillStyle = g; x.fillRect(px - r, py - r, 2 * r, 2 * r);
    }
    x.lineCap = 'round';
    for (let i = 0; i < 3500; i++) {            // fibres
      const px = R() * c.width, py = R() * c.height, a = R() * TAU, l = 4 + R() * 26;
      x.strokeStyle = R() < 0.5 ? `rgba(80,52,24,${0.03 + R() * 0.05})` : `rgba(255,248,230,${0.04 + R() * 0.06})`;
      x.lineWidth = 0.6 + R() * 0.8;
      x.beginPath(); x.moveTo(px, py); x.quadraticCurveTo(px + Math.cos(a + 0.4) * l * 0.5, py + Math.sin(a + 0.4) * l * 0.5, px + Math.cos(a) * l, py + Math.sin(a) * l); x.stroke();
    }
    for (let i = 0; i < 5000; i++) {            // specks
      x.fillStyle = `rgba(60,38,18,${0.05 + R() * 0.22})`;
      const r = R() * 1.3 + 0.2; x.fillRect(R() * c.width, R() * c.height, r, r);
    }
    // warm centre light
    const g = x.createRadialGradient(c.width / 2, c.height * 0.45, 50, c.width / 2, c.height / 2, c.width * 0.62);
    g.addColorStop(0, 'rgba(255,246,222,0.35)'); g.addColorStop(1, 'rgba(255,246,222,0)');
    x.fillStyle = g; x.fillRect(0, 0, c.width, c.height);
    TEX.parchment = c;
  }
  // stars (two layers)
  for (const [key, n, seed, big] of [['stars1', 1400, 11, 1.2], ['stars2', 260, 12, 2.4]]) {
    const c = mk(W + 400, H + 400), x = c.getContext('2d'), R = rng(seed);
    for (let i = 0; i < n; i++) {
      const px = R() * c.width, py = R() * c.height, m = Math.pow(R(), 3);
      const r = 0.4 + m * big, a = 0.2 + m * 0.8;
      const tint = R();
      x.fillStyle = tint < 0.15 ? `rgba(255,214,170,${a})` : tint < 0.3 ? `rgba(190,210,255,${a})` : `rgba(255,250,240,${a})`;
      x.beginPath(); x.arc(px, py, r, 0, TAU); x.fill();
      if (m > 0.55) {
        const g = x.createRadialGradient(px, py, 0, px, py, r * 7);
        g.addColorStop(0, `rgba(255,240,220,${a * 0.35})`); g.addColorStop(1, 'rgba(255,240,220,0)');
        x.fillStyle = g; x.fillRect(px - r * 7, py - r * 7, r * 14, r * 14);
      }
    }
    TEX[key] = c;
  }
  // nebula
  {
    const c = mk(W, H), x = c.getContext('2d'), R = rng(21);
    for (let i = 0; i < 26; i++) {
      const px = R() * W, py = R() * H, r = 150 + R() * 420;
      const hue = R() < 0.5 ? '70,90,160' : R() < 0.5 ? '140,80,60' : '90,60,130';
      const g = x.createRadialGradient(px, py, 0, px, py, r);
      g.addColorStop(0, `rgba(${hue},${0.05 + R() * 0.06})`); g.addColorStop(1, `rgba(${hue},0)`);
      x.fillStyle = g; x.fillRect(0, 0, W, H);
    }
    TEX.nebula = c;
  }
  // grain tiles (half-res noise, upscaled at draw time)
  TEX.grain = [];
  for (let k = 0; k < 6; k++) {
    const c = mk(480, 270), x = c.getContext('2d'), id = x.createImageData(480, 270), R = rng(100 + k);
    for (let i = 0; i < id.data.length; i += 4) {
      const v = 128 + (R() + R() + R() - 1.5) * 90;
      id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 255;
    }
    x.putImageData(id, 0, 0); TEX.grain.push(c);
  }
  // vignettes
  for (const [key, rgb, a] of [['vigP', '70,40,12', 0.62], ['vigD', '0,0,0', 0.78]]) {
    const c = mk(W, H), x = c.getContext('2d');
    const g = x.createRadialGradient(W / 2, H / 2, H * 0.32, W / 2, H / 2, W * 0.72);
    g.addColorStop(0, `rgba(${rgb},0)`); g.addColorStop(0.55, `rgba(${rgb},${a * 0.35})`); g.addColorStop(1, `rgba(${rgb},${a})`);
    x.fillStyle = g; x.fillRect(0, 0, W, H);
    TEX[key] = c;
  }
  TEX.bloomA = mk(W / 4, H / 4);
  TEX.bloomB = mk(W / 8, H / 8);
}

// ---------------------------------------------------------------- backgrounds
function drawBackground(ctx, th, t, sc) {
  if (th.name === 'parchment') {
    const k = sc ? sc.i : 0;
    ctx.drawImage(TEX.parchment, -80 + Math.round((hash(k) - 0.5) * 60), -80 + Math.round((hash(k + 7) - 0.5) * 40));
  } else {
    const g = ctx.createRadialGradient(W * 0.55, H * 0.45, 40, W / 2, H / 2, W * 0.75);
    if (th.name === 'cosmic') { g.addColorStop(0, '#0d1019'); g.addColorStop(1, '#030407'); }
    else { g.addColorStop(0, '#16171c'); g.addColorStop(1, '#060708'); }
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    if (th.name === 'cosmic') {
      ctx.globalAlpha = 0.9; ctx.drawImage(TEX.nebula, 0, 0);
      const d = sc ? sc.t : t;
      ctx.globalAlpha = 1;
      ctx.drawImage(TEX.stars1, -200 - d * 4, -200 - d * 1.5);
      ctx.drawImage(TEX.stars2, -200 - d * 9, -200 - d * 3);
    } else {
      ctx.globalAlpha = 0.35; ctx.drawImage(TEX.stars1, -200, -200); ctx.globalAlpha = 1;
    }
  }
}

// sunburst rays (parchment: ink lines, dark: light shafts)
function rays(ctx, th, cx, cy, n, r0, r1, alpha, rot = 0) {
  ctx.save();
  if (th.dark) {
    ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < n; i++) {
      const a = rot + (i / n) * TAU + hash(i) * 0.05, w = 0.006 + hash(i + 9) * 0.02;
      const g = ctx.createRadialGradient(cx, cy, r0, cx, cy, r1);
      g.addColorStop(0, `rgba(255,214,150,${alpha * (0.4 + hash(i + 3) * 0.6)})`); g.addColorStop(1, 'rgba(255,214,150,0)');
      ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, r1, a - w, a + w); ctx.closePath(); ctx.fill();
    }
  } else {
    ctx.strokeStyle = th.ink; ctx.lineWidth = 1;
    for (let i = 0; i < n; i++) {
      const a = rot + (i / n) * TAU;
      ctx.globalAlpha = alpha * (0.4 + hash(i + 1) * 0.6);
      ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0);
      ctx.lineTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1); ctx.stroke();
    }
  }
  ctx.restore();
}

// ---------------------------------------------------------------- post
function bloom(ctx, canvas, strength, threshold = 1.45) {
  const a = TEX.bloomA, ax = a.getContext('2d');
  const b = TEX.bloomB, bx = b.getContext('2d');
  ax.clearRect(0, 0, a.width, a.height);
  ax.filter = `brightness(0.82) contrast(${threshold}) blur(5px)`;
  ax.drawImage(canvas, 0, 0, a.width, a.height); ax.filter = 'none';
  bx.clearRect(0, 0, b.width, b.height);
  bx.filter = 'blur(9px)'; bx.drawImage(a, 0, 0, b.width, b.height); bx.filter = 'none';
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
  ctx.globalAlpha = strength * 0.65; ctx.drawImage(a, 0, 0, W, H);
  ctx.globalAlpha = strength; ctx.drawImage(b, 0, 0, W, H);
  ctx.restore();
}

/* film grain: one static pattern per scene (per-frame noise is very costly to encode) */
function grain(ctx, th, seed) {
  const tile = TEX.grain[seed % TEX.grain.length];
  ctx.save();
  ctx.imageSmoothingEnabled = false;
  const ox = -Math.floor(hash(seed) * 60), oy = -Math.floor(hash(seed + 99) * 40);
  if (th.dark) { ctx.globalCompositeOperation = 'soft-light'; ctx.globalAlpha = 0.14; }
  else { ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = 0.12; }
  ctx.drawImage(tile, ox, oy, W + 120, H + 80);
  ctx.restore();
}

function vignette(ctx, th) {
  ctx.save();
  ctx.globalCompositeOperation = th.dark ? 'source-over' : 'multiply';
  ctx.drawImage(th.dark ? TEX.vigD : TEX.vigP, 0, 0);
  ctx.restore();
}

// ---------------------------------------------------------------- text
function drawWord(ctx, th, word, x, y, k, L) {
  const c = col(th, L.color);
  const e = E.out(k);
  const glow = th.dark && L.glow !== false;
  ctx.save();
  ctx.fillStyle = c;
  const fx = L.fx || 'rise';
  let dx = 0, dy = 0;
  if (fx === 'smear') {            // slides in from the right with a motion trail
    dx = (1 - e) * L.size * 0.7;
    for (let j = 5; j >= 1; j--) {
      ctx.globalAlpha = e * 0.1 * (1 - k) * (6 - j);
      ctx.fillText(word, x + dx + j * L.size * 0.16 * (1 - e), y);
    }
  } else if (fx === 'rise') {
    dy = (1 - e) * L.size * 0.28;
  } else if (fx === 'drop') {
    dy = -(1 - E.outBack(k)) * L.size * 0.5;
  } else if (fx === 'zoom') {
    const s = lerp(1.35, 1, E.outExpo(k));
    ctx.translate(x, y); ctx.scale(s, s); ctx.translate(-x, -y);
  }
  if (glow) {
    ctx.shadowColor = L.glowColor || (L.color === 'accent' ? 'rgba(255,150,40,0.9)' : 'rgba(255,214,150,0.55)');
    ctx.shadowBlur = L.size * (L.glowSize || (L.color === 'accent' ? 0.5 : 0.32));
    ctx.globalAlpha = e;
    ctx.fillText(word, x + dx, y + dy);
    ctx.shadowBlur = L.size * 0.12;
    ctx.fillText(word, x + dx, y + dy);
    ctx.shadowBlur = 0; ctx.shadowColor = 'transparent';
  }
  ctx.globalAlpha = e * (L.alpha ?? 1);
  ctx.fillText(word, x + dx, y + dy);
  ctx.restore();
}

/* spec = { x, y, align, lines:[{text,size,weight,fam,color,spacing,at,stagger,fx,lead}], caption:{text,at,gap} , out } */
function headline(ctx, th, sc, spec) {
  let y = spec.y;
  const fadeOut = spec.out != null ? 1 - ramp(sc.t, spec.out * BEAT, 0.3) : 1;
  if (fadeOut <= 0) return;
  ctx.save();
  ctx.globalAlpha = fadeOut;
  ctx.textBaseline = 'alphabetic';
  let maxW = 0;
  for (const L of spec.lines) {
    setFont(ctx, L.fam || 'serif', L.size, L.weight ?? 700);
    ctx.letterSpacing = (L.spacing ?? Math.round(L.size * 0.06)) + 'px';
    const words = L.text.split(' ');
    const spaceW = ctx.measureText(' ').width + (L.spacing ?? Math.round(L.size * 0.06)) * 0.2;
    const widths = words.map(w => ctx.measureText(w).width);
    const total = widths.reduce((a, b) => a + b, 0) + spaceW * (words.length - 1);
    maxW = Math.max(maxW, total);
    let x = spec.align === 'center' ? spec.x - total / 2 : spec.align === 'right' ? spec.x - total : spec.x;
    y += L.size * (L.lead ?? 0.92);
    words.forEach((w, i) => {
      const t0 = ((L.at ?? 0) + i * (L.stagger ?? 0.34)) * BEAT;
      const k = clamp((sc.t - t0) / (L.dur ?? 0.42));
      if (k > 0) { ctx.save(); ctx.globalAlpha *= 1; drawWord(ctx, th, w, x, y, k, L); ctx.restore(); }
      x += widths[i] + spaceW;
    });
    y += L.size * (L.gap ?? 0.16);
  }
  if (spec.caption) {
    const C = spec.caption;
    const k = clamp((sc.t - C.at * BEAT) / 0.5);
    if (k > 0) {
      setFont(ctx, 'mono', C.size || 17, 500);
      ctx.letterSpacing = (C.spacing ?? 5) + 'px';
      ctx.fillStyle = th.caption;
      ctx.globalAlpha = fadeOut * E.out(k);
      const cy = y + (C.gap ?? 26);
      const txt = C.text.slice(0, Math.ceil(C.text.length * clamp(k * 1.6)));
      let x = spec.align === 'center' ? spec.x : spec.x;
      ctx.textAlign = spec.align === 'center' ? 'center' : 'left';
      ctx.fillText(txt, x, cy);
      if (C.rule !== false && spec.align !== 'center') {
        ctx.globalAlpha = fadeOut * E.out(k) * 0.6;
        ctx.strokeStyle = th.accent; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(x, cy + 16); ctx.lineTo(x + 70 * E.out(k), cy + 16); ctx.stroke();
      }
    }
  }
  ctx.restore();
  return { bottom: y, width: maxW };
}

function monoText(ctx, th, txt, x, y, size = 14, opts = {}) {
  ctx.save();
  setFont(ctx, 'mono', size, opts.weight || 500);
  ctx.letterSpacing = (opts.spacing ?? 3) + 'px';
  ctx.fillStyle = opts.color || th.caption;
  ctx.globalAlpha *= opts.alpha ?? 1;
  ctx.textAlign = opts.align || 'left';
  ctx.textBaseline = opts.baseline || 'alphabetic';
  ctx.fillText(txt, x, y);
  ctx.restore();
}

// ---------------------------------------------------------------- HUD
const Y0 = 2026, Y1 = 2120;
const KPTS = [[2026, 0.728], [2030, 0.732], [2040, 0.745], [2050, 0.761], [2060, 0.783], [2070, 0.812], [2080, 0.851], [2090, 0.912], [2100, 1.0], [2110, 1.068], [2120, 1.137]];
function kardashev(y) {
  if (y <= KPTS[0][0]) return KPTS[0][1];
  for (let i = 1; i < KPTS.length; i++) {
    if (y <= KPTS[i][0]) {
      const [xa, ya] = KPTS[i - 1], [xb, yb] = KPTS[i];
      return lerp(ya, yb, (y - xa) / (xb - xa));
    }
  }
  return KPTS[KPTS.length - 1][1];
}

function drawHUD(ctx, th, info) {
  if (info.alpha <= 0) return;
  ctx.save();
  ctx.globalAlpha = info.alpha;
  const m = 54, arm = 26;
  ctx.strokeStyle = th.hudFaint; ctx.lineWidth = 1.5;
  for (const [cx, cy, sx, sy] of [[m, m, 1, 1], [W - m, m, -1, 1], [m, H - m, 1, -1], [W - m, H - m, -1, -1]]) {
    ctx.beginPath(); ctx.moveTo(cx, cy + sy * arm); ctx.lineTo(cx, cy); ctx.lineTo(cx + sx * arm, cy); ctx.stroke();
  }
  // top-left chapter
  monoText(ctx, th, info.chapter, 96, 92, 17, { color: th.hud, spacing: 4, weight: 600 });
  // top-right brand
  monoText(ctx, th, 'A HISTORY OF TOMORROW', W - 96, 92, 17, { color: th.hud, spacing: 4, weight: 700, align: 'right' });
  monoText(ctx, th, '2026 — 2120 · ONE HUMAN LIFETIME', W - 96, 116, 11, { color: th.hudFaint, spacing: 3, align: 'right' });
  // bottom-left year + age
  monoText(ctx, th, 'YEAR', 96, H - 122, 12, { color: th.hudFaint, spacing: 4 });
  monoText(ctx, th, String(info.year), 96, H - 84, 32, { color: th.hud, spacing: 3, weight: 600 });
  if (info.age != null) {
    monoText(ctx, th, 'AGE', 262, H - 122, 12, { color: th.hudFaint, spacing: 4 });
    monoText(ctx, th, String(info.age), 262, H - 84, 32, { color: th.hud, spacing: 3, weight: 600 });
  }
  // timeline
  const x0 = 610, x1 = 1310, ty = H - 86;
  const pos = clamp((info.yearF - Y0) / (Y1 - Y0));
  ctx.strokeStyle = th.hudFaint; ctx.lineWidth = 1.2;
  ctx.beginPath(); ctx.moveTo(x0, ty); ctx.lineTo(x1, ty); ctx.stroke();
  for (let yy = 2030; yy <= 2120; yy += 10) {
    const xx = lerp(x0, x1, (yy - Y0) / (Y1 - Y0));
    ctx.beginPath(); ctx.moveTo(xx, ty); ctx.lineTo(xx, ty - (yy % 20 === 10 ? 9 : 6)); ctx.stroke();
    if (yy % 20 === 10) monoText(ctx, th, String(yy), xx, ty - 16, 11, { color: th.hudFaint, spacing: 2, align: 'center' });
  }
  ctx.strokeStyle = th.hudBar; ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.moveTo(x0, ty + 5); ctx.lineTo(lerp(x0, x1, pos), ty + 5); ctx.stroke();
  const mx = lerp(x0, x1, pos);
  ctx.fillStyle = th.hudBar;
  ctx.beginPath(); ctx.moveTo(mx, ty + 1); ctx.lineTo(mx - 6, ty - 9); ctx.lineTo(mx + 6, ty - 9); ctx.closePath(); ctx.fill();
  // kardashev
  const k = kardashev(info.yearF);
  monoText(ctx, th, 'KARDASHEV', W - 96, H - 122, 12, { color: th.hudFaint, spacing: 4, align: 'right' });
  monoText(ctx, th, 'K ' + k.toFixed(3), W - 96, H - 84, 32, { color: th.hud, spacing: 3, weight: 600, align: 'right' });
  const kx0 = W - 330, kx1 = W - 96, ky = H - 64;
  ctx.strokeStyle = th.hudFaint; ctx.lineWidth = 1.2;
  ctx.beginPath(); ctx.moveTo(kx0, ky); ctx.lineTo(kx1, ky); ctx.stroke();
  for (let i = 0; i <= 4; i++) { const xx = lerp(kx0, kx1, i / 4); ctx.beginPath(); ctx.moveTo(xx, ky); ctx.lineTo(xx, ky - 5); ctx.stroke(); }
  ctx.strokeStyle = th.hudBar; ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.moveTo(kx0, ky + 4); ctx.lineTo(lerp(kx0, kx1, clamp((k - 0.7) / 0.5)), ky + 4); ctx.stroke();
  ctx.restore();
}

// ---------------------------------------------------------------- drawing helpers
function polyLen(P) { let L = 0; for (let i = 1; i < P.length; i++) L += Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]); return L; }
/* stroke polyline up to fraction `prog` of its length */
function pl(ctx, P, prog = 1) {
  if (prog <= 0 || P.length < 2) return;
  ctx.beginPath(); ctx.moveTo(P[0][0], P[0][1]);
  if (prog >= 1) { for (let i = 1; i < P.length; i++) ctx.lineTo(P[i][0], P[i][1]); ctx.stroke(); return; }
  let rem = polyLen(P) * prog;
  for (let i = 1; i < P.length; i++) {
    const d = Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]);
    if (rem >= d) { ctx.lineTo(P[i][0], P[i][1]); rem -= d; }
    else { const f = d > 0 ? rem / d : 0; ctx.lineTo(lerp(P[i - 1][0], P[i][0], f), lerp(P[i - 1][1], P[i][1], f)); break; }
  }
  ctx.stroke();
}
function fillPoly(ctx, P) { ctx.beginPath(); ctx.moveTo(P[0][0], P[0][1]); for (let i = 1; i < P.length; i++) ctx.lineTo(P[i][0], P[i][1]); ctx.closePath(); ctx.fill(); }
function pathPoly(ctx, P, close = true) { ctx.beginPath(); ctx.moveTo(P[0][0], P[0][1]); for (let i = 1; i < P.length; i++) ctx.lineTo(P[i][0], P[i][1]); if (close) ctx.closePath(); }
const circ = (cx, cy, r, n = 72, a0 = 0, a1 = TAU) => Array.from({ length: n + 1 }, (_, i) => { const a = a0 + (a1 - a0) * i / n; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; });
const ell = (cx, cy, rx, ry, rot = 0, n = 72, a0 = 0, a1 = TAU) => Array.from({ length: n + 1 }, (_, i) => {
  const a = a0 + (a1 - a0) * i / n, x = rx * Math.cos(a), y = ry * Math.sin(a);
  return [cx + x * Math.cos(rot) - y * Math.sin(rot), cy + x * Math.sin(rot) + y * Math.cos(rot)];
});
function bez(p0, p1, p2, p3, n = 20) {
  const out = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n, u = 1 - t;
    out.push([u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
              u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1]]);
  }
  return out;
}
/* chain of cubic segments: [p0, c1, c2, p1, c3, c4, p2, ...] */
function bezPath(pts, n = 16) {
  const out = [];
  for (let i = 0; i + 3 < pts.length; i += 3) {
    const seg = bez(pts[i], pts[i + 1], pts[i + 2], pts[i + 3], n);
    if (out.length) seg.shift();
    out.push(...seg);
  }
  return out;
}
const rectP = (x, y, w, h) => [[x, y], [x + w, y], [x + w, y + h], [x, y + h], [x, y]];
/* progress of the i-th of n staggered parts */
const part = (p, i, n, spread = 1.6) => clamp((p * (n - 1 + spread) - i) / spread);

function hatch(ctx, clipFn, x0, y0, x1, y1, spacing, angle, alpha, color) {
  ctx.save();
  clipFn(); ctx.clip();
  ctx.strokeStyle = color; ctx.globalAlpha *= alpha; ctx.lineWidth = 1;
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, R = Math.hypot(x1 - x0, y1 - y0) / 2 + 4;
  const ca = Math.cos(angle), sa = Math.sin(angle);
  ctx.beginPath();
  for (let d = -R; d <= R; d += spacing) {
    ctx.moveTo(cx + ca * -R - sa * d, cy + sa * -R + ca * d);
    ctx.lineTo(cx + ca * R - sa * d, cy + sa * R + ca * d);
  }
  ctx.stroke();
  ctx.restore();
}

function arrowHead(ctx, x, y, ang, s = 9) {
  ctx.beginPath(); ctx.moveTo(x, y);
  ctx.lineTo(x - Math.cos(ang - 0.4) * s, y - Math.sin(ang - 0.4) * s);
  ctx.lineTo(x - Math.cos(ang + 0.4) * s, y - Math.sin(ang + 0.4) * s);
  ctx.closePath(); ctx.fill();
}
function dimLine(ctx, th, x1, y1, x2, y2, label, prog = 1, off = 0) {
  if (prog <= 0) return;
  ctx.save();
  ctx.strokeStyle = th.soft; ctx.fillStyle = th.soft; ctx.lineWidth = 1.2;
  const ang = Math.atan2(y2 - y1, x2 - x1), e = E.out(prog);
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
  const ax = lerp(mx, x1, e), ay = lerp(my, y1, e), bx = lerp(mx, x2, e), by = lerp(my, y2, e);
  ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke();
  if (prog > 0.95) { arrowHead(ctx, x2, y2, ang, 8); arrowHead(ctx, x1, y1, ang + Math.PI, 8); }
  const nx = -Math.sin(ang) * 8, ny = Math.cos(ang) * 8;
  ctx.beginPath(); ctx.moveTo(x1 - nx, y1 - ny); ctx.lineTo(x1 + nx, y1 + ny); ctx.moveTo(x2 - nx, y2 - ny); ctx.lineTo(x2 + nx, y2 + ny); ctx.stroke();
  if (label && prog > 0.5) {
    ctx.translate(mx, my); ctx.rotate(Math.abs(ang) > Math.PI / 2 ? ang + Math.PI : ang);
    ctx.globalAlpha *= ramp(prog, 0.5, 0.5);
    setFont(ctx, 'mono', 13, 500); ctx.letterSpacing = '2px'; ctx.textAlign = 'center';
    ctx.fillText(label, 0, -10 + off);
  }
  ctx.restore();
}

// ---------------------------------------------------------------- 3D
function rotX(p, a) { const c = Math.cos(a), s = Math.sin(a); return [p[0], p[1] * c - p[2] * s, p[1] * s + p[2] * c]; }
function rotY(p, a) { const c = Math.cos(a), s = Math.sin(a); return [p[0] * c + p[2] * s, p[1], -p[0] * s + p[2] * c]; }
function rotZ(p, a) { const c = Math.cos(a), s = Math.sin(a); return [p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2]]; }
/* camera: {rx, ry, rz, dist, f, cx, cy} ; y up in world, down on screen */
function proj(p, C) {
  let q = p;
  if (C.rz) q = rotZ(q, C.rz);
  if (C.ry) q = rotY(q, C.ry);
  if (C.rx) q = rotX(q, C.rx);
  const z = q[2] + C.dist, s = C.f / z;
  return [C.cx + q[0] * s, C.cy - q[1] * s, z];
}
/* draw 3D polylines with depth-faded alpha.
   opts.prog: 0..1 ; opts.seq: stagger lines in order ; opts.back: alpha at the far side */
function wire(ctx, C, lines, opts = {}) {
  const prog = opts.prog ?? 1, n = lines.length;
  const P = lines.map(l => l.map(p => proj(p, C)));
  let zmin = Infinity, zmax = -Infinity;
  for (const l of P) for (const p of l) { if (p[2] < zmin) zmin = p[2]; if (p[2] > zmax) zmax = p[2]; }
  const span = Math.max(1e-6, zmax - zmin);
  const a0 = ctx.globalAlpha;
  for (let i = 0; i < n; i++) {
    const q = opts.seq ? part(prog, i, n, opts.spread ?? Math.max(1, n * 0.25)) : prog;
    if (q <= 0) continue;
    const l = P[i];
    let zm = 0; for (const p of l) zm += p[2]; zm /= l.length;
    ctx.globalAlpha = a0 * lerp(1, opts.back ?? 0.3, (zm - zmin) / span);
    pl(ctx, l, q);
  }
  ctx.globalAlpha = a0;
  return P;
}

// ---------------------------------------------------------------- particles
function embers(ctx, cx, cy, t, n, seed, spread = 60, rise = 260, color = '255,190,110') {
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (let i = 0; i < n; i++) {
    const life = 1.6 + hash(seed + i) * 2.2;
    const ph = ((t + hash(seed + i * 3) * life) % life) / life;
    const x = cx + (hash(seed + i * 7) - 0.5) * spread + Math.sin(t * 2 + i) * 14 * ph;
    const y = cy - ph * rise * (0.6 + hash(seed + i * 5) * 0.8);
    const a = Math.sin(ph * Math.PI) * (0.4 + hash(i + seed) * 0.6);
    const r = 1 + hash(seed + i * 11) * 2.2;
    ctx.fillStyle = `rgba(${color},${a})`;
    ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
  }
  ctx.restore();
}
function glowDot(ctx, x, y, r, color = '255,220,160', a = 1) {
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, `rgba(${color},${a})`); g.addColorStop(0.25, `rgba(${color},${a * 0.45})`); g.addColorStop(1, `rgba(${color},0)`);
  ctx.fillStyle = g; ctx.fillRect(x - r, y - r, 2 * r, 2 * r);
}
