'use strict';
/* Illustrations, part A: prologue, year cards, 2030s–2040s.
   Every illustration draws around (0,0); the scene positions it. */
const ILL = {};
const DEG = Math.PI / 180;

function paperFill(th) { return th.dark ? '#0f1116' : '#e2d2ae'; }

function capsule(ctx, a, b, r1, r2) {
  const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
  ctx.beginPath();
  ctx.arc(a[0], a[1], r1, ang + Math.PI / 2, ang + 3 * Math.PI / 2);
  ctx.arc(b[0], b[1], r2, ang - Math.PI / 2, ang + Math.PI / 2);
  ctx.closePath();
}
function solid(ctx, th, pathFn, lw = 2.2, fill = true, stroke = true) {
  pathFn();
  if (fill) { ctx.fillStyle = paperFill(th); ctx.fill(); ctx.fillStyle = th.fill; ctx.fill(); }
  if (stroke) { ctx.lineWidth = lw; ctx.strokeStyle = th.ink; ctx.stroke(); }
}

// ------------------------------------------------------------ astrolabe
ILL.astrolabe = (ctx, th, sc, o = {}) => {
  const R = o.R || 430, p = o.prog ?? 1, t = sc.T;
  const A = o.alpha ?? 0.5;
  ctx.save();
  ctx.strokeStyle = th.ink; ctx.lineWidth = 1.2; ctx.globalAlpha = A;
  pl(ctx, circ(0, 0, R, 180, -Math.PI / 2, 1.5 * Math.PI), E.inOut(p));
  pl(ctx, circ(0, 0, R - 30, 180, Math.PI / 2, 2.5 * Math.PI), E.inOut(p));
  pl(ctx, circ(0, 0, R * 0.62, 150, 0.5, 0.5 + TAU), E.inOut(clamp(p * 1.3 - 0.2)));
  pl(ctx, circ(0, 0, R * 0.22, 60), E.inOut(clamp(p * 1.5 - 0.4)));
  const rot = t * 0.025;
  ctx.beginPath();
  for (let i = 0; i < 180; i++) {
    if (i / 180 > p) break;
    const a = rot + i / 180 * TAU, l = i % 18 === 0 ? 14 : i % 3 === 0 ? 8 : 4;
    ctx.moveTo(Math.cos(a) * (R - 30), Math.sin(a) * (R - 30));
    ctx.lineTo(Math.cos(a) * (R - 30 + l), Math.sin(a) * (R - 30 + l));
  }
  ctx.stroke();
  setFont(ctx, 'mono', 12, 500); ctx.letterSpacing = '2px'; ctx.fillStyle = th.ink; ctx.textAlign = 'center';
  for (let i = 0; i < 10; i++) {
    if ((i + 0.5) / 10 > p) break;
    const a = rot + (i + 0.5) / 10 * TAU;
    ctx.save(); ctx.translate(Math.cos(a) * (R - 11), Math.sin(a) * (R - 11)); ctx.rotate(a + Math.PI / 2);
    ctx.fillText(String(2030 + i * 10), 0, 4); ctx.restore();
  }
  for (let k = 0; k < 3; k++) {
    const rr = R * (0.36 + k * 0.17), rt = 0.35 + k * 0.55 + t * 0.02 * (k % 2 ? -1 : 1);
    ctx.globalAlpha = A * 0.75;
    pl(ctx, ell(0, 0, rr, rr * 0.36, rt, 90), E.inOut(clamp(p * 1.4 - 0.3 - k * 0.1)));
    const a = t * (0.1 / (k + 1)) * TAU + k * 2;
    const px = rr * Math.cos(a), py = rr * 0.36 * Math.sin(a);
    ctx.globalAlpha = A * clamp(p * 2 - 1);
    ctx.fillStyle = th.accent; ctx.beginPath();
    ctx.arc(px * Math.cos(rt) - py * Math.sin(rt), px * Math.sin(rt) + py * Math.cos(rt), 4, 0, TAU); ctx.fill();
  }
  ctx.globalAlpha = A * 0.45;
  pl(ctx, [[-R - 50, 0], [R + 50, 0]], E.inOut(p));
  pl(ctx, [[0, -R - 50], [0, R + 50]], E.inOut(p));
  ctx.restore();
};

// ------------------------------------------------------------ spark of the future
ILL.spark = (ctx, sc, x, y, s = 1, seed = 1) => {
  const t = sc.T;
  const fl = 0.88 + 0.12 * Math.sin(t * 9) * Math.sin(t * 5.3 + 1);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  glowDot(ctx, x, y, 300 * s * fl, '255,160,70', 0.3);
  glowDot(ctx, x, y, 110 * s * fl, '255,205,140', 0.75);
  glowDot(ctx, x, y, 30 * s, '255,250,235', 1);
  const g = ctx.createLinearGradient(x - 340 * s, y, x + 340 * s, y);
  g.addColorStop(0, 'rgba(255,200,140,0)'); g.addColorStop(0.5, `rgba(255,232,196,${0.8 * fl})`); g.addColorStop(1, 'rgba(255,200,140,0)');
  ctx.fillStyle = g; ctx.fillRect(x - 340 * s, y - 1.6 * s, 680 * s, 3.2 * s);
  const g2 = ctx.createLinearGradient(x, y - 160 * s, x, y + 160 * s);
  g2.addColorStop(0, 'rgba(255,200,140,0)'); g2.addColorStop(0.5, `rgba(255,232,196,${0.5 * fl})`); g2.addColorStop(1, 'rgba(255,200,140,0)');
  ctx.fillStyle = g2; ctx.fillRect(x - 1.2 * s, y - 160 * s, 2.4 * s, 320 * s);
  ctx.restore();
  embers(ctx, x, y, t, Math.round(46 * s), seed, 50 * s, 320 * s);
};

// ------------------------------------------------------------ baby footprint
const FOOT = (() => {
  const sole = bezPath([
    [0, 150], [30, 152], [50, 130], [50, 100],
    [52, 60], [60, 10], [66, -30],
    [70, -62], [68, -88], [48, -98],
    [24, -110], [-22, -112], [-50, -104],
    [-74, -98], [-72, -60], [-60, -30],
    [-46, 0], [-30, 40], [-36, 82],
    [-42, 122], [-26, 150], [0, 150],
  ], 14);
  const toes = [[-44, -136, 24, 28, -0.15], [-6, -150, 15, 18, 0], [22, -145, 13, 16, 0.1], [45, -132, 12, 14, 0.25], [61, -112, 9.5, 11.5, 0.4]];
  return { sole, toes };
})();
ILL.footprint = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? 1, s = o.scale ?? 1, mir = o.mirror ? -1 : 1;
  ctx.save();
  ctx.scale(s * mir, s);
  const k1 = E.inOut(clamp(p / 0.55));
  // soft ink fill (like a stamp)
  ctx.save();
  ctx.globalAlpha = 0.9 * clamp((p - 0.35) / 0.3);
  pathPoly(ctx, FOOT.sole); ctx.fillStyle = th.fillDeep; ctx.fill();
  ctx.clip();
  ctx.strokeStyle = th.ink; ctx.lineWidth = 1; ctx.globalAlpha *= 0.28;
  for (let r = 16; r < 150; r += 9) { ctx.beginPath(); ctx.ellipse(-4, -50, r * 0.8, r, 0.1, 0, TAU); ctx.stroke(); }
  for (let r = 10; r < 90; r += 9) { ctx.beginPath(); ctx.ellipse(0, 110, r, r * 0.8, 0, Math.PI, TAU); ctx.stroke(); }
  ctx.restore();
  ctx.strokeStyle = th.ink; ctx.lineWidth = 2.6 / s; ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  pl(ctx, FOOT.sole, k1);
  FOOT.toes.forEach((tt, i) => {
    const q = E.outBack(clamp((p - 0.4 - i * 0.06) / 0.2));
    if (q <= 0) return;
    ctx.save(); ctx.translate(tt[0], tt[1]); ctx.rotate(tt[4]); ctx.scale(q, q);
    ctx.beginPath(); ctx.ellipse(0, 0, tt[2], tt[3], 0, 0, TAU);
    ctx.fillStyle = th.fillDeep; ctx.fill(); ctx.stroke();
    ctx.globalAlpha = 0.3; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.ellipse(0, 2, tt[2] * 0.5, tt[3] * 0.5, 0, 0, TAU); ctx.stroke();
    ctx.restore();
  });
  ctx.restore();
  if (o.dims !== false) {
    const d = clamp((p - 0.6) / 0.4);
    dimLine(ctx, th, -140 * s, 152 * s, -140 * s, -180 * s, '7.8 CM', d);
    dimLine(ctx, th, -76 * s, 200 * s, 72 * s, 200 * s, '3.4 CM', clamp(d * 1.2 - 0.2), 36);
  }
};
ILL.stamp = (ctx, th, sc, x, y, txt, sub, k) => {
  if (k <= 0) return;
  ctx.save(); ctx.translate(x, y); ctx.rotate(-0.22);
  const s = lerp(1.6, 1, E.outExpo(k)); ctx.scale(s, s);
  ctx.globalAlpha = clamp(k * 2) * 0.85;
  ctx.strokeStyle = th.accent; ctx.fillStyle = th.accent;
  ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(0, 0, 62, 0, TAU); ctx.stroke();
  ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(0, 0, 53, 0, TAU); ctx.stroke();
  setFont(ctx, 'serif', 34, 900); ctx.letterSpacing = '1px'; ctx.textAlign = 'center';
  ctx.fillText(txt, 0, 12);
  setFont(ctx, 'mono', 10, 700); ctx.letterSpacing = '3px';
  ctx.fillText(sub, 0, -22); ctx.fillText('★ ★ ★', 0, 36);
  ctx.restore();
};
/* dashed path of decades starting at the footprint */
ILL.lifeTrail = (ctx, th, sc, k) => {
  if (k <= 0) return;
  const P = bezPath([[40, 300], [300, 400], [560, 200], [820, 40]], 60);
  ctx.save();
  ctx.strokeStyle = th.accent; ctx.lineWidth = 2.4; ctx.setLineDash([2, 12]); ctx.lineCap = 'round';
  pl(ctx, P, E.inOut(k));
  ctx.setLineDash([]);
  for (let i = 0; i < 10; i++) {
    const f = (i + 1) / 10.5, q = clamp((E.inOut(k) - f) * 12);
    if (q <= 0) continue;
    const idx = Math.round(f * (P.length - 1)), [x, y] = P[idx];
    ctx.globalAlpha = q;
    ctx.fillStyle = paperFill(th); ctx.strokeStyle = th.ink; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(x, y, 7, 0, TAU); ctx.fill(); ctx.stroke();
    monoText(ctx, th, String(2030 + i * 10), x + 4, y - 18, 13, { color: th.ink, spacing: 2, align: 'center', weight: 600 });
  }
  ctx.restore();
};

// ------------------------------------------------------------ year card
ILL.card = (ctx, th, sc, o) => {
  const t = sc.t;
  rays(ctx, th, 0, -20, 90, 150, 1300, th.dark ? 0.09 : 0.075, t * 0.03);
  ctx.save();
  ctx.strokeStyle = th.ink; ctx.globalAlpha = 0.3; ctx.lineWidth = 1.2;
  pl(ctx, circ(0, -20, 360, 180, -Math.PI / 2, 1.5 * Math.PI), E.out(ramp(t, 0, 1.0)));
  pl(ctx, circ(0, -20, 380, 180, Math.PI / 2, 2.5 * Math.PI), E.out(ramp(t, 0.1, 1.0)));
  ctx.beginPath();
  for (let i = 0; i < 120; i++) {
    if (i / 120 > E.out(ramp(t, 0.15, 1))) break;
    const a = -Math.PI / 2 + i / 120 * TAU, l = i % 10 === 0 ? 12 : 5;
    ctx.moveTo(Math.cos(a) * 360, -20 + Math.sin(a) * 360); ctx.lineTo(Math.cos(a) * (360 - l), -20 + Math.sin(a) * (360 - l));
  }
  ctx.stroke();
  ctx.restore();
  // rolling digits
  const size = 300;
  setFont(ctx, 'serif', size, 900); ctx.letterSpacing = '0px';
  const to = String(o.year), from = String(o.from ?? o.year);
  const dw = [...to].map(d => ctx.measureText(d).width), gap = 8;
  let x = -(dw.reduce((a, b) => a + b, 0) + gap * 3) / 2;
  const k = E.outExpo(ramp(t, 0.02, 0.75));
  const base = size * 0.33;
  for (let i = 0; i < to.length; i++) {
    const a = from[i], b = to[i];
    ctx.save();
    ctx.beginPath(); ctx.rect(x - 40, -size * 0.62, dw[i] + 80, size * 1.12); ctx.clip();
    ctx.fillStyle = th.dark ? '#eab65a' : th.accent;
    if (th.dark) { ctx.shadowColor = 'rgba(255,140,40,0.75)'; ctx.shadowBlur = 45; }
    if (a !== b && k < 1) {
      const off = k * size * 1.05;
      const blur = (1 - k) * 22;
      for (let j = 0; j < 4; j++) {
        ctx.globalAlpha = j === 0 ? 1 : 0.18;
        ctx.fillText(a, x, base - off - j * blur);
        ctx.fillText(b, x, base + size * 1.05 - off - j * blur);
      }
    } else {
      ctx.fillText(b, x, base);
    }
    ctx.restore();
    x += dw[i] + gap;
  }
  // chapter title
  const k2 = E.out(ramp(t, 0.35, 0.5));
  if (k2 > 0) {
    ctx.save(); ctx.globalAlpha = k2;
    setFont(ctx, 'serif', 44, 700); ctx.letterSpacing = '14px'; ctx.textAlign = 'center';
    ctx.fillStyle = th.text;
    if (th.dark) { ctx.shadowColor = 'rgba(255,220,170,0.6)'; ctx.shadowBlur = 20; }
    ctx.fillText(o.chapter, 7, -size * 0.52 - 20 + (1 - k2) * 12);
    ctx.restore();
  }
  const k3 = E.out(ramp(t, 0.7, 0.6));
  if (k3 > 0) {
    ctx.save(); ctx.globalAlpha = k3;
    setFont(ctx, 'italic', 62, 600); ctx.letterSpacing = '1px'; ctx.textAlign = 'center';
    ctx.fillStyle = th.text;
    const y = base + 118;
    ctx.fillText(o.sub, 0, y);
    const w = ctx.measureText(o.sub).width / 2 + 40;
    ctx.strokeStyle = th.accent; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(-w - 90 * k3, y - 18); ctx.lineTo(-w, y - 18); ctx.moveTo(w, y - 18); ctx.lineTo(w + 90 * k3, y - 18); ctx.stroke();
    ctx.restore();
  }
};

// ------------------------------------------------------------ 2030: neural network
ILL.neural = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 1.6), t = sc.T;
  const layers = [4, 7, 9, 7, 3], dx = 175, dy = 62;
  const N = layers.map((n, L) => Array.from({ length: n }, (_, i) => [-350 + L * dx, (i - (n - 1) / 2) * dy]));
  ctx.save();
  ctx.strokeStyle = th.ink; ctx.lineWidth = 1;
  ctx.globalAlpha = 0.2;
  pl(ctx, circ(0, 0, 420, 180, Math.PI, 3 * Math.PI), E.inOut(clamp(p * 1.5)));
  pl(ctx, circ(0, 0, 440, 180, 0, TAU), E.inOut(clamp(p * 1.5 - 0.2)));
  pl(ctx, [[-480, 0], [480, 0]], E.inOut(clamp(p * 2)));
  ctx.globalAlpha = 0.3;
  for (let L = 0; L < 4; L++) {
    const q = E.out(part(clamp(p * 1.4), L, 4, 1.3));
    if (q <= 0) continue;
    for (const a of N[L]) for (const b of N[L + 1]) pl(ctx, [a, b], q);
  }
  ctx.restore();
  // signals
  const sig = clamp((p - 0.45) / 0.3);
  if (sig > 0) {
    ctx.save(); ctx.fillStyle = th.accent;
    for (let s = 0; s < 46; s++) {
      const u = (t * 1.1 + hash(s) * 4) % 4, L = Math.floor(u), f = u - L;
      const i = Math.floor(hash(s * 3 + L) * layers[L]), j = Math.floor(hash(s * 7 + L + 1) * layers[L + 1]);
      const a = N[L][i], b = N[L + 1][j];
      ctx.globalAlpha = sig * Math.sin(f * Math.PI) * 0.95;
      ctx.beginPath(); ctx.arc(lerp(a[0], b[0], f), lerp(a[1], b[1], f), 4.2, 0, TAU); ctx.fill();
      if (th.dark) glowDot(ctx, lerp(a[0], b[0], f), lerp(a[1], b[1], f), 16, '255,190,100', 0.5 * sig);
    }
    ctx.restore();
  }
  // nodes
  N.forEach((layer, L) => layer.forEach(([x, y], i) => {
    const q = E.outBack(part(clamp(p * 1.25), L, 5, 1.2));
    if (q <= 0) return;
    ctx.save();
    ctx.beginPath(); ctx.arc(x, y, 14 * q, 0, TAU);
    ctx.fillStyle = paperFill(th); ctx.fill();
    ctx.lineWidth = 2.2; ctx.strokeStyle = th.ink; ctx.stroke();
    const act = sig * (0.5 + 0.5 * Math.sin(t * 5 + i * 1.7 + L * 2.3));
    ctx.globalAlpha = act; ctx.fillStyle = th.accent;
    ctx.beginPath(); ctx.arc(x, y, 7 * q, 0, TAU); ctx.fill();
    ctx.restore();
  }));
  const kl = clamp((p - 0.6) / 0.3);
  if (kl > 0) {
    ctx.save(); ctx.globalAlpha = kl;
    monoText(ctx, th, 'INPUT', -350, 318, 13, { align: 'center', color: th.soft });
    monoText(ctx, th, 'HIDDEN LAYERS', 0, 318, 13, { align: 'center', color: th.soft });
    monoText(ctx, th, 'OUTPUT', 350, 318, 13, { align: 'center', color: th.soft });
    monoText(ctx, th, '10¹⁵ PARAMETERS', 0, -330, 13, { align: 'center', color: th.soft });
    ctx.restore();
  }
};

// ------------------------------------------------------------ 2030: humanoid robot
ILL.robot = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 1.5), t = sc.T;
  const lt = sc.t ?? 0;
  ctx.save(); ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  const q = i => E.out(part(p, i, 6, 1.6));
  const A = (i) => { const v = q(i); ctx.globalAlpha = v; return v > 0; };
  if (A(4)) {
    ctx.save(); ctx.globalAlpha *= 0.5; ctx.fillStyle = th.fillDeep;
    ctx.beginPath(); ctx.ellipse(0, 322, 170, 16, 0, 0, TAU); ctx.fill(); ctx.restore();
    ctx.save(); ctx.strokeStyle = th.ink; ctx.lineWidth = 1.2; ctx.globalAlpha *= 0.5;
    ctx.beginPath(); ctx.moveTo(-300, 322); ctx.lineTo(300, 322); ctx.stroke(); ctx.restore();
  }
  // legs
  if (A(4)) {
    for (const s of [-1, 1]) {
      solid(ctx, th, () => capsule(ctx, [s * 40, 70], [s * 46, 176], 24, 20));
      solid(ctx, th, () => capsule(ctx, [s * 46, 192], [s * 48, 288], 19, 15));
      solid(ctx, th, () => { ctx.beginPath(); ctx.moveTo(s * 30, 292); ctx.lineTo(s * 66, 292); ctx.quadraticCurveTo(s * 92, 296, s * 94, 318); ctx.lineTo(s * 26, 318); ctx.closePath(); });
      solid(ctx, th, () => { ctx.beginPath(); ctx.arc(s * 46, 184, 18, 0, TAU); });
      ctx.fillStyle = th.accent; ctx.beginPath(); ctx.arc(s * 46, 184, 5, 0, TAU); ctx.fill();
      solid(ctx, th, () => { ctx.beginPath(); ctx.arc(s * 40, 64, 20, 0, TAU); });
    }
  }
  // pelvis + torso
  if (A(1)) {
    solid(ctx, th, () => { ctx.beginPath(); ctx.moveTo(-66, 4); ctx.lineTo(66, 4); ctx.lineTo(48, 56); ctx.lineTo(-48, 56); ctx.closePath(); });
    const torso = () => {
      ctx.beginPath(); ctx.moveTo(-112, -192); ctx.quadraticCurveTo(-128, -190, -122, -168);
      ctx.lineTo(-84, -20); ctx.quadraticCurveTo(-80, -6, -62, -6); ctx.lineTo(62, -6); ctx.quadraticCurveTo(80, -6, 84, -20);
      ctx.lineTo(122, -168); ctx.quadraticCurveTo(128, -190, 112, -192); ctx.closePath();
    };
    solid(ctx, th, torso, 2.4);
    hatch(ctx, () => { torso(); }, -130, -200, 0, 0, 7, -0.9, 0.25, th.ink);
    ctx.strokeStyle = th.ink; ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.moveTo(-96, -120); ctx.quadraticCurveTo(0, -84, 96, -120); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-70, -58); ctx.lineTo(70, -58); ctx.moveTo(-64, -34); ctx.lineTo(64, -34); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, -84); ctx.lineTo(0, -6); ctx.stroke();
    ctx.beginPath(); ctx.arc(0, -140, 22, 0, TAU); ctx.stroke();
    ctx.fillStyle = th.accent; ctx.globalAlpha *= 0.7 + 0.3 * Math.sin(t * 4);
    ctx.beginPath(); ctx.arc(0, -140, 11, 0, TAU); ctx.fill();
  }
  // head
  if (A(0)) {
    solid(ctx, th, () => { ctx.beginPath(); ctx.rect(-16, -224, 32, 34); }, 2);
    solid(ctx, th, () => { ctx.beginPath(); ctx.roundRect(-50, -342, 100, 120, 36); }, 2.4);
    ctx.fillStyle = th.ink; ctx.beginPath(); ctx.roundRect(-40, -306, 80, 40, 18); ctx.fill();
    ctx.strokeStyle = th.accent; ctx.lineWidth = 3.5;
    const sweep = Math.sin(t * 2.2) * 14;
    ctx.beginPath(); ctx.moveTo(-24 + sweep, -286); ctx.lineTo(24 + sweep, -286); ctx.stroke();
    if (th.dark) glowDot(ctx, sweep, -286, 40, '255,170,90', 0.6);
    ctx.strokeStyle = th.ink; ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.moveTo(-50, -250); ctx.lineTo(50, -250); ctx.stroke();
  }
  // arms
  if (A(2)) {
    for (const s of [-1, 1]) solid(ctx, th, () => { ctx.beginPath(); ctx.arc(s * 128, -168, 27, 0, TAU); });
    // left (hanging)
    solid(ctx, th, () => capsule(ctx, [-134, -148], [-146, -28], 19, 16));
    solid(ctx, th, () => capsule(ctx, [-146, -8], [-152, 96], 16, 13));
    solid(ctx, th, () => { ctx.beginPath(); ctx.arc(-146, -18, 17, 0, TAU); });
    solid(ctx, th, () => { ctx.beginPath(); ctx.roundRect(-168, 102, 32, 50, 10); });
    // right (waves)
    const wave = E.inOut(ramp(lt, 1.1, 0.6));
    const th1 = lerp(-0.08, -2.05, wave), th2 = wave * (0.25 + Math.sin(t * 7) * 0.32);
    ctx.save(); ctx.translate(128, -168); ctx.rotate(th1);
    solid(ctx, th, () => capsule(ctx, [6, 20], [16, 140], 19, 16));
    ctx.translate(18, 150); ctx.rotate(th2);
    solid(ctx, th, () => capsule(ctx, [0, 10], [4, 114], 16, 13));
    solid(ctx, th, () => { ctx.beginPath(); ctx.arc(0, 0, 17, 0, TAU); });
    solid(ctx, th, () => { ctx.beginPath(); ctx.roundRect(-12, 118, 32, 50, 10); });
    ctx.restore();
    for (const s of [-1, 1]) { ctx.fillStyle = th.accent; ctx.beginPath(); ctx.arc(s * 128, -168, 6, 0, TAU); ctx.fill(); }
  }
  ctx.restore();
  const kd = q(5);
  dimLine(ctx, th, -270, 318, -270, -342, '1.75 M', kd);
  if (kd > 0) {
    ctx.save(); ctx.globalAlpha = kd; ctx.strokeStyle = th.soft; ctx.lineWidth = 1;
    pl(ctx, [[-40, -300], [-120, -380], [-230, -380]], kd);
    monoText(ctx, th, 'VISION SENSOR', -236, -388, 12, { align: 'right', color: th.soft });
    pl(ctx, [[-128, -168], [-230, -250], [-300, -250]], kd);
    monoText(ctx, th, '42 JOINTS', -306, -258, 12, { align: 'right', color: th.soft });
    ctx.restore();
  }
};

// ------------------------------------------------------------ 3D box helpers
function boxVerts(x0, y0, z0, x1, y1, z1) {
  return [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]];
}
const BOX_E = [[0, 1], [1, 2], [2, 3], [3, 0], [4, 5], [5, 6], [6, 7], [7, 4], [0, 4], [1, 5], [2, 6], [3, 7]];
const BOX_F = [[0, 1, 2, 3], [5, 4, 7, 6], [4, 0, 3, 7], [1, 5, 6, 2], [3, 2, 6, 7], [4, 5, 1, 0]];
function boxEdges(v) { return BOX_E.map(([a, b]) => [v[a], v[b]]); }
/* shaded solid box: visible faces filled by light direction */
function solidBox(ctx, th, C, v, o = {}) {
  const P = v.map(p => proj(p, C));
  const faces = BOX_F.map(f => {
    const q = f.map(i => P[i]);
    const cross = (q[1][0] - q[0][0]) * (q[2][1] - q[0][1]) - (q[1][1] - q[0][1]) * (q[2][0] - q[0][0]);
    const z = q.reduce((s, p) => s + p[2], 0) / 4;
    return { f, q, cross, z };
  }).filter(F => F.cross < 0).sort((a, b) => b.z - a.z);
  const shades = o.shades || [0.1, 0.22, 0.04, 0.3, 0.02, 0.35];
  for (const F of faces) {
    const idx = BOX_F.indexOf(F.f);
    ctx.beginPath(); ctx.moveTo(F.q[0][0], F.q[0][1]); for (let i = 1; i < 4; i++) ctx.lineTo(F.q[i][0], F.q[i][1]); ctx.closePath();
    if (o.fill !== false) {
      ctx.fillStyle = paperFill(th); ctx.globalAlpha = o.alpha ?? 1; ctx.fill();
      ctx.fillStyle = th.dark ? `rgba(244,196,105,${shades[idx] * 0.35})` : `rgba(80,52,24,${shades[idx]})`; ctx.fill();
    }
    ctx.globalAlpha = o.lineAlpha ?? 1; ctx.strokeStyle = th.ink; ctx.lineWidth = o.lw ?? 1.8; ctx.stroke();
  }
  ctx.globalAlpha = 1;
  return P;
}

// ------------------------------------------------------------ 2030s: steering wheel in a museum case
ILL.museum = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 1.6), t = sc.T;
  const C = { rx: 0.3, ry: 0.62 + Math.sin(t * 0.25) * 0.06, dist: 1700, f: 1600, cx: 0, cy: 40 };
  ctx.save(); ctx.lineJoin = 'round';
  // spotlight cone
  const ks = E.out(clamp(p * 2 - 0.8));
  if (ks > 0) {
    ctx.save(); ctx.globalAlpha = 0.16 * ks; ctx.strokeStyle = th.ink; ctx.lineWidth = 1;
    const top = proj([0, 560, 0], C);
    for (let i = 0; i < 26; i++) {
      const a = i / 26 * TAU, b = proj([Math.cos(a) * 200, -60, Math.sin(a) * 200], C);
      ctx.beginPath(); ctx.moveTo(top[0], top[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    }
    ctx.restore();
  }
  // pedestal
  const k1 = E.out(clamp(p / 0.4));
  if (k1 > 0) {
    ctx.globalAlpha = k1;
    solidBox(ctx, th, C, boxVerts(-130, -330 + 270 * (1 - k1) * 0, -130, 130, -60, 130), { lw: 2.2 });
    solidBox(ctx, th, C, boxVerts(-150, -350, -150, 150, -330, 150), { lw: 1.8 });
    solidBox(ctx, th, C, boxVerts(-145, -60, -145, 145, -44, 145), { lw: 1.8 });
    // plaque
    const o0 = proj([-80, -140, 130], C), o1 = proj([80, -140, 130], C), o2 = proj([-80, -200, 130], C);
    ctx.save();
    ctx.setTransform(ctx.getTransform().multiply(new DOMMatrix([(o1[0] - o0[0]) / 160, (o1[1] - o0[1]) / 160, (o2[0] - o0[0]) / 60, (o2[1] - o0[1]) / 60, o0[0], o0[1]])));
    ctx.fillStyle = th.dark ? 'rgba(244,196,105,0.15)' : 'rgba(80,52,24,0.2)';
    ctx.strokeStyle = th.ink; ctx.lineWidth = 1.5; ctx.fillRect(0, 0, 160, 60); ctx.strokeRect(0, 0, 160, 60);
    setFont(ctx, 'mono', 13, 700); ctx.letterSpacing = '1px'; ctx.fillStyle = th.ink; ctx.textAlign = 'center';
    ctx.fillText('STEERING WHEEL', 80, 26); setFont(ctx, 'mono', 11, 500); ctx.fillText('1894 — 2035', 80, 46);
    ctx.restore();
  }
  // wheel
  const k2 = E.inOut(clamp((p - 0.3) / 0.45));
  if (k2 > 0) {
    ctx.globalAlpha = 1;
    const tilt = 0.55, cy = 110;
    const W3 = (x, y) => { const q = rotX([x, y, 0], tilt); return [q[0], q[1] + cy, q[2]]; };
    const ring = r => Array.from({ length: 97 }, (_, i) => { const a = i / 96 * TAU; return W3(Math.cos(a) * r, Math.sin(a) * r); });
    ctx.strokeStyle = th.ink; ctx.lineWidth = 2.6;
    pl(ctx, ring(104).map(p3 => proj(p3, C)), k2);
    pl(ctx, ring(88).map(p3 => proj(p3, C)), k2);
    ctx.lineWidth = 2.2;
    pl(ctx, ring(24).map(p3 => proj(p3, C)), k2);
    for (const a of [-Math.PI / 2, Math.PI / 6, Math.PI * 5 / 6]) {
      const a1 = W3(Math.cos(a) * 24, Math.sin(a) * 24), a2 = W3(Math.cos(a) * 88, Math.sin(a) * 88);
      pl(ctx, [proj(a1, C), proj(a2, C)], k2);
      const b1 = W3(Math.cos(a + 0.12) * 24, Math.sin(a + 0.12) * 24), b2 = W3(Math.cos(a + 0.08) * 88, Math.sin(a + 0.08) * 88);
      pl(ctx, [proj(b1, C), proj(b2, C)], k2);
    }
    const hub = proj(W3(0, 0), C);
    ctx.fillStyle = th.accent; ctx.globalAlpha = k2; ctx.beginPath(); ctx.arc(hub[0], hub[1], 8, 0, TAU); ctx.fill();
    ctx.strokeStyle = th.ink; ctx.lineWidth = 3;
    pl(ctx, [proj([0, -44, 0], C), proj(W3(0, -24), C)], k2);
  }
  // glass case
  const k3 = E.out(clamp((p - 0.15) / 0.5));
  if (k3 > 0) {
    ctx.globalAlpha = 1;
    const v = boxVerts(-140, -44, -140, 140, 290, 140);
    ctx.strokeStyle = th.ink; ctx.lineWidth = 1.7;
    wire(ctx, C, boxEdges(v), { prog: k3, back: 0.35 });
    const f0 = proj(v[4], C), f1 = proj(v[5], C), f2 = proj(v[6], C), f3 = proj(v[7], C);
    ctx.globalAlpha = 0.07 * k3; ctx.fillStyle = th.dark ? '#fff4d8' : '#ffffff';
    fillPoly(ctx, [f0, f1, f2, f3]);
    ctx.globalAlpha = 0.35 * k3; ctx.strokeStyle = th.dark ? '#fff4d8' : '#fffaf0'; ctx.lineWidth = 3;
    const L = (u1, v1, u2, v2) => { const a = proj([lerp(-140, 140, u1), lerp(-44, 290, v1), 140], C), b = proj([lerp(-140, 140, u2), lerp(-44, 290, v2), 140], C); pl(ctx, [a, b]); };
    L(0.15, 0.9, 0.45, 0.45); L(0.25, 0.95, 0.52, 0.55);
  }
  ctx.restore();
};

// ------------------------------------------------------------ 2040: tokamak (fusion)
ILL.tokamak = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 1.4), t = sc.T;
  const Rm = 250, rm = 104;
  const C = { rx: 0.5, ry: t * 0.18, dist: 1500, f: 1300, cx: 0, cy: 0 };
  const tor = (u, v, r = rm) => [(Rm + r * Math.cos(v)) * Math.cos(u), r * Math.sin(v), (Rm + r * Math.cos(v)) * Math.sin(u)];
  const lines = [];
  for (let i = 0; i < 30; i++) { const u = i / 30 * TAU; lines.push(Array.from({ length: 33 }, (_, j) => tor(u, j / 32 * TAU))); }
  for (let j = 0; j < 6; j++) { const v = j / 6 * TAU; lines.push(Array.from({ length: 97 }, (_, i) => tor(i / 96 * TAU, v))); }
  ctx.save();
  ctx.strokeStyle = th.accent; ctx.lineWidth = 1.2; ctx.globalAlpha = 0.55;
  wire(ctx, C, lines, { prog: E.inOut(clamp(p / 0.55)), seq: true, back: 0.18 });
  // D coils
  const coils = [];
  for (let i = 0; i < 16; i++) {
    const u = (i + 0.5) / 16 * TAU, pts = [];
    for (let j = 0; j <= 40; j++) { const f = -Math.PI / 2 + j / 40 * Math.PI; pts.push([Rm - 150 + 300 * Math.cos(f), 170 * Math.sin(f)]); }
    pts.push([Rm - 150, -170]);
    coils.push(pts.map(([rr, y]) => [rr * Math.cos(u), y, rr * Math.sin(u)]));
  }
  ctx.strokeStyle = th.ink; ctx.lineWidth = 2.6; ctx.globalAlpha = 0.75;
  wire(ctx, C, coils, { prog: E.inOut(clamp((p - 0.15) / 0.5)), seq: true, back: 0.12 });
  // central solenoid
  const sol = [];
  for (let i = 0; i < 10; i++) { const a = i / 10 * TAU; sol.push([[Math.cos(a) * 62, -230, Math.sin(a) * 62], [Math.cos(a) * 62, 230, Math.sin(a) * 62]]); }
  for (let j = 0; j <= 6; j++) { const y = -230 + j * 460 / 6; sol.push(Array.from({ length: 41 }, (_, i) => [Math.cos(i / 40 * TAU) * 62, y, Math.sin(i / 40 * TAU) * 62])); }
  ctx.lineWidth = 1.4; ctx.globalAlpha = 0.6;
  wire(ctx, C, sol, { prog: E.inOut(clamp((p - 0.2) / 0.4)), back: 0.25 });
  ctx.restore();
  // plasma
  const ig = clamp((p - 0.5) / 0.25);
  if (ig > 0) {
    const ring = Array.from({ length: 161 }, (_, i) => proj(tor(i / 160 * TAU, 0, 0), C));
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineJoin = 'round';
    const fl = 0.85 + 0.15 * Math.sin(t * 13) * Math.sin(t * 7.7);
    for (const [w, a, c] of [[70, 0.05, '255,120,170'], [36, 0.12, '255,140,180'], [16, 0.35, '255,190,210'], [6, 0.9, '255,240,245']]) {
      ctx.lineWidth = w; ctx.strokeStyle = `rgba(${c},${a * ig * fl})`; pl(ctx, ring);
    }
    for (let i = 0; i < 90; i++) {
      const u = (t * (0.8 + hash(i) * 1.2) + hash(i + 5) * TAU) % TAU, v = t * 6 + i;
      const q = proj(tor(u, v, 30 + hash(i + 9) * 40), C);
      ctx.fillStyle = `rgba(255,220,235,${0.8 * ig})`; ctx.beginPath(); ctx.arc(q[0], q[1], 1.6 + hash(i) * 1.6, 0, TAU); ctx.fill();
    }
    const flash = pulse(sc.t, 0.5 * 1.4 + 0.3, 0.12);
    if (flash > 0) glowDot(ctx, 0, 0, 900, '255,220,230', 0.55 * flash);
    ctx.restore();
    ctx.save(); ctx.globalAlpha = ig;
    monoText(ctx, th, '150,000,000 °C', 150, -320, 16, { color: th.accent, weight: 700 });
    ctx.strokeStyle = th.soft; ctx.lineWidth = 1; pl(ctx, [[144, -326], [60, -250], [40, -200]]);
    monoText(ctx, th, '10× HOTTER THAN THE SUN\'S CORE', 150, -296, 11, { color: th.soft });
    ctx.restore();
  }
};

// ------------------------------------------------------------ 2040s: bootprint on Mars
const BOOT = bezPath([
  [0, -232], [55, -234], [96, -205], [98, -150],
  [100, -100], [86, -50], [70, 0],
  [58, 40], [60, 90], [72, 130],
  [86, 175], [70, 238], [0, 240],
  [-70, 238], [-86, 175], [-72, 130],
  [-60, 90], [-58, 40], [-70, 0],
  [-86, -50], [-100, -100], [-98, -150],
  [-96, -205], [-55, -234], [0, -232],
], 12);
function bootPrint(ctx, th, k, fillK) {
  ctx.save();
  ctx.globalAlpha = fillK;
  pathPoly(ctx, BOOT.map(([x, y]) => [x * 1.12, y * 1.07]));
  ctx.fillStyle = th.fill; ctx.fill();
  ctx.setLineDash([3, 7]); ctx.strokeStyle = th.ink; ctx.lineWidth = 1.4; ctx.globalAlpha = fillK * 0.6; ctx.stroke(); ctx.setLineDash([]);
  ctx.globalAlpha = fillK;
  pathPoly(ctx, BOOT); ctx.fillStyle = th.fillDeep; ctx.fill();
  ctx.save(); pathPoly(ctx, BOOT); ctx.clip();
  for (let y = -214; y < 236; y += 25) {
    if (y > -8 && y < 30) continue;
    ctx.strokeStyle = th.ink; ctx.globalAlpha = fillK * 0.85; ctx.lineWidth = 9;
    ctx.beginPath(); ctx.moveTo(-110, y + 6); ctx.quadraticCurveTo(0, y - 4, 110, y + 6); ctx.stroke();
    ctx.strokeStyle = th.paper === '#dccaa6' ? '#efe2c4' : '#fff4d8'; ctx.globalAlpha = fillK * 0.55; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(-110, y + 1); ctx.quadraticCurveTo(0, y - 9, 110, y + 1); ctx.stroke();
  }
  ctx.restore();
  ctx.globalAlpha = 1; ctx.strokeStyle = th.accent; ctx.lineWidth = 3.4; ctx.lineJoin = 'round';
  pl(ctx, BOOT, k);
  ctx.restore();
}
ILL.marsPrint = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 1.5), t = sc.T;
  const R = rng(42), X0 = -250, X1 = 700, hz = -170;
  ctx.save();
  const hills = []; for (let i = 0; i <= 120; i++) { const x = X0 + i * (X1 - X0) / 120; hills.push([x, hz - 16 * noise1(i * 0.12 + 3) - 40 * Math.pow(noise1(i * 0.05 + 11), 2)]); }
  ctx.strokeStyle = th.ink; ctx.lineWidth = 1.8; pl(ctx, hills, E.inOut(clamp(p / 0.5)));
  ctx.globalAlpha = 0.28; ctx.lineWidth = 1;
  for (let k = 0; k < 6; k++) {
    const yy = hz + 22 + k * k * 11, line = [];
    for (let i = 0; i <= 60; i++) { const x = X0 + 40 + i * (X1 - X0 - 40) / 60; line.push([x, yy + Math.sin(i * 0.4 + k) * (2 + k)]); }
    pl(ctx, line, E.inOut(clamp(p * 1.6 - k * 0.05)));
  }
  ctx.globalAlpha = clamp(p * 2) * 0.35; ctx.fillStyle = th.ink;
  for (let i = 0; i < 1300; i++) {
    const f = Math.sqrt(R()), x = X0 + 30 + R() * (X1 - X0 - 30), y = hz + 8 + f * 520, r = 0.5 + f * 1.8;
    ctx.fillRect(x, y, r, r);
  }
  for (let i = 0; i < 12; i++) {
    const x = X0 + 60 + R() * (X1 - X0 - 60), f = 0.15 + R() * 0.85, y = hz + 24 + f * 440, s = 6 + f * 24 * (0.5 + R());
    if (x > -120 && x < 330 && y > -40) continue;
    const poly = Array.from({ length: 8 }, (_, j) => { const a = j / 8 * TAU; const r = s * (0.7 + R() * 0.5); return [x + Math.cos(a) * r, y + Math.sin(a) * r * 0.55]; });
    ctx.globalAlpha = clamp(p * 2 - 0.3);
    ctx.fillStyle = paperFill(th); fillPoly(ctx, poly); ctx.fillStyle = th.fill; fillPoly(ctx, poly);
    ctx.strokeStyle = th.ink; ctx.lineWidth = 1.4; pathPoly(ctx, poly); ctx.stroke();
    hatch(ctx, () => pathPoly(ctx, poly), x - s, y - s, x + s, y + s, 4, 0.8, 0.35, th.ink);
  }
  // Starship on the horizon
  const kr = E.inOut(clamp((p - 0.1) / 0.5));
  if (kr > 0) {
    ctx.globalAlpha = 1; ctx.strokeStyle = th.ink; ctx.lineWidth = 1.6;
    const rx = 520, ry = hz - 8, w = 16, h = 150;
    pl(ctx, [[rx - w, ry], [rx - w, ry - h], [rx - w + 2, ry - h - 22], [rx, ry - h - 34], [rx + w - 2, ry - h - 22], [rx + w, ry - h], [rx + w, ry]], kr);
    pl(ctx, [[rx - w, ry - 4], [rx - w - 12, ry + 6]], kr); pl(ctx, [[rx + w, ry - 4], [rx + w + 12, ry + 6]], kr);
    pl(ctx, [[rx - w, ry - h + 18], [rx - w - 8, ry - h + 40], [rx - w, ry - h + 44]], kr);
    pl(ctx, [[rx + w, ry - h + 18], [rx + w + 8, ry - h + 40], [rx + w, ry - h + 44]], kr);
    ctx.globalAlpha = 0.5 * kr; pl(ctx, [[rx - w, ry - 40], [rx + w, ry - 40]], kr); pl(ctx, [[rx - w, ry - 90], [rx + w, ry - 90]], kr);
    monoText(ctx, th, 'STARSHIP · 50 M', rx + 30, ry - h, 11, { color: th.soft, alpha: kr });
  }
  // sky
  ctx.globalAlpha = clamp(p * 2 - 0.6);
  ctx.strokeStyle = th.ink; ctx.lineWidth = 1.4;
  ctx.beginPath(); ctx.arc(640, -360, 22, 0, TAU); ctx.stroke();
  rays(ctx, th, 640, -360, 24, 30, 56, 0.9, 0);
  ctx.fillStyle = th.accent; ctx.beginPath(); ctx.arc(60, -330, 5, 0, TAU); ctx.fill();
  monoText(ctx, th, 'EARTH · 225 MILLION KM', 76, -326, 11, { color: th.soft });
  ctx.restore();
  // prints
  const k2 = E.inOut(clamp((p - 0.35) / 0.4));
  at(ctx, -170, 10, 1, () => { ctx.rotate(-0.42); ctx.scale(0.62, 0.62 * 0.5); bootPrint(ctx, th, k2, clamp((p - 0.45) / 0.3)); });
  const k1 = E.inOut(clamp((p - 0.2) / 0.45));
  at(ctx, 120, 230, 1, () => { ctx.rotate(-0.36); ctx.scale(1, 0.56); bootPrint(ctx, th, k1, clamp((p - 0.35) / 0.3)); });
  dimLine(ctx, th, 400, 120, 400, 360, '32 CM', clamp((p - 0.7) / 0.3));
};

// ------------------------------------------------------------ 2040s: cancer vaccine
ILL.cancer = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 2.2), t = sc.T;
  const cx = 110, cy = 40;
  const hit = clamp((p - 0.55) / 0.3);
  const shrink = 1 - 0.14 * E.inOut(hit);
  const memb = Array.from({ length: 181 }, (_, i) => {
    const a = i / 180 * TAU; const r = (175 + 12 * Math.sin(7 * a + 1) + 7 * Math.sin(13 * a + t * 0.8) + 5 * Math.sin(3 * a)) * shrink;
    return [cx + Math.cos(a) * r, cy + Math.sin(a) * r];
  });
  ctx.save(); ctx.lineJoin = 'round';
  const k1 = E.inOut(clamp(p / 0.4));
  ctx.globalAlpha = clamp(p / 0.3);
  pathPoly(ctx, memb); ctx.fillStyle = paperFill(th); ctx.fill(); ctx.fillStyle = th.fill; ctx.fill();
  hatch(ctx, () => pathPoly(ctx, memb), cx - 200, cy - 200, cx + 200, cy + 200, 9, 0.7, 0.18, th.ink);
  ctx.globalAlpha = 1;
  ctx.strokeStyle = th.ink; ctx.lineWidth = 2.6;
  if (hit > 0) ctx.setLineDash([22 * (1 - hit) + 8, 10 * hit + 0.01]);
  pl(ctx, memb, k1); ctx.setLineDash([]);
  // nucleus
  const nuc = Array.from({ length: 91 }, (_, i) => { const a = i / 90 * TAU, r = (70 + 8 * Math.sin(5 * a + 2)) * shrink; return [cx - 10 + Math.cos(a) * r, cy - 6 + Math.sin(a) * r]; });
  ctx.lineWidth = 2; pl(ctx, nuc, k1);
  ctx.globalAlpha = 0.5 * k1; ctx.lineWidth = 1;
  for (let i = 0; i < 6; i++) pl(ctx, bez([cx - 60, cy - 30 + i * 12], [cx - 20, cy - 60 + i * 20], [cx + 10, cy + i * 8], [cx + 40, cy - 20 + i * 10], 12), k1);
  // receptors
  ctx.globalAlpha = 1;
  for (let i = 0; i < 22; i++) {
    const a = i / 22 * TAU + 0.1, r0 = 180 * shrink, q = E.out(clamp(p * 2.2 - 0.3 - i * 0.02));
    if (q <= 0) continue;
    const x0 = cx + Math.cos(a) * r0, y0 = cy + Math.sin(a) * r0, x1 = cx + Math.cos(a) * (r0 + 22 * q), y1 = cy + Math.sin(a) * (r0 + 22 * q);
    ctx.strokeStyle = th.ink; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
    ctx.fillStyle = th.ink; ctx.beginPath(); ctx.arc(x1, y1, 4, 0, TAU); ctx.fill();
  }
  // antibodies / T-cells converge
  for (let i = 0; i < 9; i++) {
    const a = i / 9 * TAU + 0.35, travel = E.inOut(clamp((p - 0.2 - i * 0.02) / 0.45));
    if (travel <= 0) continue;
    const r = lerp(430, 214 * shrink, travel), x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
    ctx.save(); ctx.translate(x, y); ctx.rotate(a + Math.PI / 2);
    ctx.globalAlpha = clamp(travel * 3);
    ctx.strokeStyle = th.accent; ctx.lineWidth = 3.2; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(0, -26); ctx.lineTo(0, 2); ctx.lineTo(-14, 20); ctx.moveTo(0, 2); ctx.lineTo(14, 20); ctx.stroke();
    ctx.restore();
  }
  // cracks
  if (hit > 0) {
    ctx.strokeStyle = th.accent; ctx.lineWidth = 1.6; ctx.globalAlpha = hit;
    for (let i = 0; i < 5; i++) {
      const a = i / 5 * TAU + 0.6, pts = [[cx + Math.cos(a) * 170 * shrink, cy + Math.sin(a) * 170 * shrink]];
      for (let j = 1; j < 5; j++) { const rr = 170 * shrink - j * 22; pts.push([cx + Math.cos(a + (j % 2 ? 0.08 : -0.06)) * rr, cy + Math.sin(a + (j % 2 ? 0.08 : -0.06)) * rr]); }
      pl(ctx, pts, hit);
    }
  }
  ctx.restore();
  // syringe
  const ks = E.out(clamp(p / 0.35));
  ctx.save(); ctx.translate(-290, -250); ctx.rotate(0.62); ctx.globalAlpha = ks;
  ctx.strokeStyle = th.ink; ctx.lineWidth = 2.2; ctx.lineJoin = 'round';
  solid(ctx, th, () => { ctx.beginPath(); ctx.roundRect(-120, -26, 240, 52, 6); }, 2.2);
  ctx.fillStyle = th.accent; ctx.globalAlpha = ks * 0.75; ctx.fillRect(-20 + 100 * E.inOut(clamp((p - 0.2) / 0.5)), -22, 136 - 100 * E.inOut(clamp((p - 0.2) / 0.5)), 44);
  ctx.globalAlpha = ks;
  ctx.beginPath(); for (let i = 0; i < 9; i++) { ctx.moveTo(-100 + i * 24, -26); ctx.lineTo(-100 + i * 24, -14); } ctx.stroke();
  ctx.beginPath(); ctx.moveTo(-120, 0); ctx.lineTo(-190, 0); ctx.moveTo(-190, -30); ctx.lineTo(-190, 30); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(120, -10); ctx.lineTo(140, -10); ctx.lineTo(140, 10); ctx.lineTo(120, 10); ctx.moveTo(140, 0); ctx.lineTo(240, 0); ctx.stroke();
  setFont(ctx, 'mono', 16, 700); ctx.letterSpacing = '3px'; ctx.fillStyle = th.ink; ctx.textAlign = 'center';
  ctx.fillText('mRNA', -50, 7);
  ctx.restore();
};
