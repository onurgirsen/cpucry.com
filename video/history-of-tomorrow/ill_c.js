'use strict';
/* Illustrations, part C: 2070s–2120 (space) + finale. */

// ------------------------------------------------------------ orthographic globe helpers
function sph(lon, lat, G, r = 1) {
  const la = lat * DEG, lo = (lon - G.lon0) * DEG;
  const x = Math.cos(la) * Math.sin(lo), y = Math.sin(la), z = Math.cos(la) * Math.cos(lo);
  const c = Math.cos(G.tilt), s = Math.sin(G.tilt);
  const y2 = y * c - z * s, z2 = y * s + z * c;
  return [G.cx + x * G.R * r, G.cy - y2 * G.R * r, z2];
}
function limb(p, G) {
  if (p[2] >= 0) return p;
  const dx = p[0] - G.cx, dy = p[1] - G.cy, r = Math.hypot(dx, dy) || 1;
  return [G.cx + dx / r * G.R, G.cy + dy / r * G.R, 0];
}
function globeLand(ctx, G, fill, stroke, lw) {
  for (const ring of LAND) {
    const P = ring.map(([lo, la]) => sph(lo, la, G));
    let vis = false; for (const p of P) if (p[2] > 0) { vis = true; break; }
    if (!vis) continue;
    if (fill) {
      ctx.beginPath();
      P.forEach((p, i) => { const q = limb(p, G); i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1]); });
      ctx.closePath(); ctx.fillStyle = fill; ctx.fill();
    }
    if (stroke) {
      ctx.strokeStyle = stroke; ctx.lineWidth = lw;
      ctx.beginPath(); let pen = false;
      for (const p of P) { if (p[2] > 0.02) { pen ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]); pen = true; } else pen = false; }
      ctx.stroke();
    }
  }
}
function graticule(ctx, G, step, stroke, lw) {
  ctx.strokeStyle = stroke; ctx.lineWidth = lw;
  ctx.beginPath();
  const run = (pts) => { let pen = false; for (const p of pts) { if (p[2] > 0) { pen ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]); pen = true; } else pen = false; } };
  for (let lon = -180; lon < 180; lon += step) run(Array.from({ length: 61 }, (_, i) => sph(lon, -90 + i * 3, G)));
  for (let lat = -90 + step; lat < 90; lat += step) run(Array.from({ length: 121 }, (_, i) => sph(-180 + i * 3, lat, G)));
  ctx.stroke();
}
function sphereSpot(ctx, G, lon, lat, rad, fill) {
  // small circle of angular radius `rad` degrees around (lon, lat)
  const pts = [];
  if (Math.abs(lat) > 89) {
    for (let i = 0; i <= 36; i++) pts.push(sph(i * 10, Math.sign(lat) * (90 - rad), G));
    if (!pts.some(p => p[2] > 0)) return;
    ctx.beginPath(); pts.forEach((p, i) => { const q = limb(p, G); i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1]); });
    ctx.closePath(); ctx.fillStyle = fill; ctx.fill();
    return;
  }
  const la = lat * DEG, lo = lon * DEG, r = rad * DEG;
  for (let i = 0; i <= 28; i++) {
    const b = i / 28 * TAU;
    const lat2 = Math.asin(Math.sin(la) * Math.cos(r) + Math.cos(la) * Math.sin(r) * Math.cos(b));
    const lon2 = lo + Math.atan2(Math.sin(b) * Math.sin(r) * Math.cos(la), Math.cos(r) - Math.sin(la) * Math.sin(lat2));
    pts.push(sph(lon2 / DEG, lat2 / DEG, G));
  }
  if (!pts.some(p => p[2] > 0)) return;
  ctx.beginPath(); pts.forEach((p, i) => { const q = limb(p, G); i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1]); });
  ctx.closePath(); ctx.fillStyle = fill; ctx.fill();
}
function shadeSphere(ctx, G, lightX = -0.55, lightY = -0.45, night = 0.82) {
  const g = ctx.createRadialGradient(G.cx + lightX * G.R, G.cy + lightY * G.R, G.R * 0.1, G.cx + lightX * G.R * 0.4, G.cy + lightY * G.R * 0.4, G.R * 1.55);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(0.55, `rgba(0,0,0,${night * 0.35})`); g.addColorStop(1, `rgba(0,0,0,${night})`);
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(G.cx, G.cy, G.R + 1, 0, TAU); ctx.fill();
}
function atmosphere(ctx, G, rgb, a = 0.5, w = 0.14) {
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const g = ctx.createRadialGradient(G.cx, G.cy, G.R * 0.92, G.cx, G.cy, G.R * (1 + w));
  g.addColorStop(0, `rgba(${rgb},0)`); g.addColorStop(0.35, `rgba(${rgb},${a})`); g.addColorStop(1, `rgba(${rgb},0)`);
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(G.cx, G.cy, G.R * (1 + w), 0, TAU); ctx.fill();
  ctx.restore();
}
function earthGlobe(ctx, th, G, o = {}) {
  ctx.save();
  ctx.beginPath(); ctx.arc(G.cx, G.cy, G.R, 0, TAU); ctx.clip();
  const g = ctx.createRadialGradient(G.cx - G.R * 0.4, G.cy - G.R * 0.4, 0, G.cx, G.cy, G.R);
  g.addColorStop(0, o.ocean0 || '#1f5588'); g.addColorStop(1, o.ocean1 || '#071a30');
  ctx.fillStyle = g; ctx.fillRect(G.cx - G.R, G.cy - G.R, 2 * G.R, 2 * G.R);
  graticule(ctx, G, 20, 'rgba(234,220,189,0.10)', 1);
  globeLand(ctx, G, o.land || 'rgba(104,122,78,0.88)', o.coast || 'rgba(240,226,190,0.7)', o.lw || 1.2);
  if (o.shade !== false) shadeSphere(ctx, G, -0.5, -0.4, o.night ?? 0.85);
  ctx.restore();
  atmosphere(ctx, G, o.atmo || '110,170,255', o.atmoA ?? 0.45, o.atmoW ?? 0.12);
}

// ------------------------------------------------------------ 2070: a city on the Moon
ILL.moon = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 1.8), t = sc.T;
  const R = rng(77);
  ctx.save();
  // Earth rising
  const ke = E.out(clamp(p / 0.6));
  if (ke > 0) {
    ctx.globalAlpha = ke;
    earthGlobe(ctx, th, { cx: -330, cy: -300 + (1 - ke) * 40, R: 78, lon0: 20 + t * 4, tilt: 0.3 }, { lw: 0.8, night: 0.9 });
    ctx.globalAlpha = 1;
  }
  // surface
  const cy0 = 1700, Rm = 1660;
  const kh = E.inOut(clamp(p / 0.35));
  ctx.save();
  ctx.beginPath(); ctx.arc(0, cy0, Rm, 0, TAU);
  const sg = ctx.createLinearGradient(0, 40, 0, 520); sg.addColorStop(0, '#26252a'); sg.addColorStop(1, '#0b0b0d');
  ctx.fillStyle = sg; ctx.globalAlpha = kh; ctx.fill();
  ctx.clip();
  for (let i = 0; i < 26; i++) {
    const x = -760 + R() * 1520, f = Math.pow(R(), 0.8), y = 60 + f * 420, rx = 10 + f * 70 * (0.4 + R());
    ctx.globalAlpha = kh * 0.9;
    ctx.fillStyle = 'rgba(0,0,0,0.35)'; ctx.beginPath(); ctx.ellipse(x, y, rx, rx * 0.26, 0, 0, TAU); ctx.fill();
    ctx.strokeStyle = th.ink; ctx.lineWidth = 1; ctx.globalAlpha = kh * 0.45;
    ctx.beginPath(); ctx.ellipse(x, y, rx, rx * 0.26, 0, Math.PI * 1.05, Math.PI * 1.95); ctx.stroke();
    ctx.globalAlpha = kh * 0.2; ctx.beginPath(); ctx.ellipse(x, y, rx, rx * 0.26, 0, 0.1, Math.PI - 0.1); ctx.stroke();
  }
  ctx.restore();
  ctx.strokeStyle = th.ink; ctx.lineWidth = 1.8; ctx.globalAlpha = 0.9;
  pl(ctx, circ(0, cy0, Rm, 400, -Math.PI / 2 - 0.5, -Math.PI / 2 + 0.5), kh);
  // domes
  const domes = [[-220, 86, 62], [-50, 74, 96], [160, 68, 140], [380, 80, 88], [540, 96, 58]];
  const kd = clamp((p - 0.2) / 0.5);
  // tubes
  ctx.globalAlpha = kd;
  for (let i = 0; i < domes.length - 1; i++) {
    const [x1, y1, r1] = domes[i], [x2, y2, r2] = domes[i + 1];
    ctx.strokeStyle = th.ink; ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.moveTo(x1 + r1 * 0.9, y1 - 12); ctx.lineTo(x2 - r2 * 0.9, y2 - 12); ctx.moveTo(x1 + r1 * 0.9, y1 - 2); ctx.lineTo(x2 - r2 * 0.9, y2 - 2); ctx.stroke();
  }
  domes.forEach(([x, y, r], i) => {
    const q = E.outBack(clamp(kd * 1.6 - i * 0.12));
    if (q <= 0) return;
    const rr = r * q;
    ctx.save(); ctx.globalAlpha = 1;
    ctx.beginPath(); ctx.ellipse(x, y, rr, rr, 0, Math.PI, TAU); ctx.closePath();
    ctx.fillStyle = 'rgba(14,16,22,0.92)'; ctx.fill();
    ctx.save(); ctx.clip();
    ctx.globalCompositeOperation = 'lighter';
    const lit = clamp((p - 0.5 - i * 0.04) / 0.2) * (0.85 + 0.15 * Math.sin(t * 3 + i));
    glowDot(ctx, x, y - rr * 0.2, rr * 1.2, '255,180,90', 0.55 * lit);
    for (let k = 0; k < 14; k++) {
      const wx = x + (hash(i * 31 + k) - 0.5) * rr * 1.4, wy = y - 6 - hash(i * 17 + k) * rr * 0.55;
      ctx.fillStyle = `rgba(255,214,150,${0.9 * lit})`; ctx.fillRect(wx, wy, 3, 2);
    }
    ctx.restore();
    ctx.strokeStyle = th.ink; ctx.lineWidth = 1.6;
    ctx.beginPath(); ctx.ellipse(x, y, rr, rr, 0, Math.PI, TAU); ctx.stroke();
    ctx.lineWidth = 0.9; ctx.globalAlpha = 0.55;
    for (const f of [-0.6, -0.25, 0.25, 0.6]) { ctx.beginPath(); ctx.ellipse(x, y, Math.abs(f) * rr, rr, 0, Math.PI, TAU); ctx.stroke(); }
    for (const f of [0.35, 0.7]) { const yy = y - f * rr, w = Math.sqrt(1 - f * f) * rr; ctx.beginPath(); ctx.ellipse(x, yy, w, w * 0.18, 0, 0, TAU); ctx.stroke(); }
    ctx.globalAlpha = 1; ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.ellipse(x, y, rr, rr * 0.16, 0, 0, TAU); ctx.stroke();
    ctx.restore();
  });
  // solar arrays + lander
  const ks = clamp((p - 0.45) / 0.3);
  ctx.globalAlpha = ks; ctx.strokeStyle = th.ink; ctx.lineWidth = 1.2;
  for (let i = 0; i < 5; i++) {
    const x = -330 + i * 46, y = 150 + i * 3;
    ctx.fillStyle = 'rgba(244,196,105,0.18)';
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 34, y - 26); ctx.lineTo(x + 34, y - 6); ctx.lineTo(x, y + 20); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x + 17, y - 3); ctx.lineTo(x + 17, y + 22); ctx.stroke();
  }
  const lx = 690, ly = 130;
  ctx.beginPath(); ctx.ellipse(lx, ly + 8, 70, 12, 0, 0, TAU); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(lx - 12, ly); ctx.lineTo(lx - 12, ly - 110); ctx.lineTo(lx, ly - 136); ctx.lineTo(lx + 12, ly - 110); ctx.lineTo(lx + 12, ly); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(lx - 12, ly - 4); ctx.lineTo(lx - 26, ly + 8); ctx.moveTo(lx + 12, ly - 4); ctx.lineTo(lx + 26, ly + 8); ctx.stroke();
  ctx.globalAlpha = clamp((p - 0.6) / 0.3);
  monoText(ctx, th, 'SOUTH POLE · POP. 12,000', 160, 200, 13, { align: 'center', color: th.soft });
  ctx.restore();
};

// ------------------------------------------------------------ 2070s: asteroid mining
ILL.asteroid = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 1.6), t = sc.T;
  const cx = 110, cy = 40, rot = t * 0.08;
  const shape = Array.from({ length: 121 }, (_, i) => {
    const a = i / 120 * TAU;
    const r = 235 * (1 + 0.12 * Math.sin(3 * a + 1) + 0.07 * Math.sin(5 * a + 2) + 0.04 * Math.sin(9 * a + 0.5) + 0.02 * Math.sin(17 * a));
    return [cx + Math.cos(a + rot) * r, cy + Math.sin(a + rot) * r * 0.82];
  });
  ctx.save(); ctx.lineJoin = 'round';
  const k = E.inOut(clamp(p / 0.45));
  ctx.globalAlpha = clamp(p / 0.3);
  pathPoly(ctx, shape); ctx.fillStyle = '#18171a'; ctx.fill();
  ctx.save(); pathPoly(ctx, shape); ctx.clip();
  const lg = ctx.createRadialGradient(cx - 120, cy - 110, 10, cx, cy, 300);
  lg.addColorStop(0, 'rgba(244,210,150,0.28)'); lg.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = lg; ctx.fillRect(cx - 320, cy - 320, 640, 640);
  hatch(ctx, () => pathPoly(ctx, shape), cx - 300, cy - 300, cx + 300, cy + 300, 7, 0.9, 0.08, th.ink);
  const craters = [[-80, -60, 40], [60, 40, 55], [120, -90, 28], [-120, 80, 34], [10, -140, 22], [-20, 30, 18], [150, 110, 24]];
  for (const [x, y, r] of craters) {
    const a = Math.atan2(y, x) + rot, d = Math.hypot(x, y);
    const X = cx + Math.cos(a) * d, Y = cy + Math.sin(a) * d * 0.82;
    ctx.fillStyle = 'rgba(0,0,0,0.45)'; ctx.beginPath(); ctx.ellipse(X, Y, r, r * 0.7, rot, 0, TAU); ctx.fill();
    ctx.strokeStyle = th.ink; ctx.globalAlpha = 0.5; ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.ellipse(X, Y, r, r * 0.7, rot, Math.PI * 0.9, Math.PI * 2.0); ctx.stroke();
    ctx.globalAlpha = 1;
  }
  ctx.strokeStyle = th.accent; ctx.lineWidth = 1.6; ctx.globalAlpha = 0.6;
  for (let i = 0; i < 5; i++) {
    const pts = []; let a = hash(i) * TAU, x = cx + Math.cos(a) * 40, y = cy + Math.sin(a) * 30;
    for (let j = 0; j < 7; j++) { pts.push([x, y]); a += (hash(i * 9 + j) - 0.5) * 1.2; x += Math.cos(a) * 26; y += Math.sin(a) * 22; }
    pl(ctx, pts, k);
  }
  ctx.restore();
  ctx.globalAlpha = 1; ctx.strokeStyle = th.ink; ctx.lineWidth = 2.2;
  pl(ctx, shape, k);
  // ship
  const ks = E.out(clamp((p - 0.2) / 0.35));
  const sx = -330, sy = -250;
  if (ks > 0) {
    ctx.save(); ctx.translate(sx, sy); ctx.rotate(0.5); ctx.scale(ks, ks);
    ctx.strokeStyle = th.ink; ctx.lineWidth = 1.8; ctx.fillStyle = '#101218';
    ctx.beginPath(); ctx.moveTo(-60, -20); ctx.lineTo(40, -20); ctx.lineTo(70, 0); ctx.lineTo(40, 20); ctx.lineTo(-60, 20); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-20, -20); ctx.lineTo(-20, 20); ctx.moveTo(10, -20); ctx.lineTo(10, 20); ctx.stroke();
    for (const s of [-1, 1]) {
      ctx.beginPath(); ctx.rect(-50, s * 26 + (s < 0 ? -70 : 0), 60, 70); ctx.fillStyle = 'rgba(244,196,105,0.12)'; ctx.fill(); ctx.stroke();
      ctx.lineWidth = 0.8; ctx.beginPath();
      for (let i = 1; i < 4; i++) { ctx.moveTo(-50 + i * 15, s * 26 + (s < 0 ? -70 : 0)); ctx.lineTo(-50 + i * 15, s * 26 + (s < 0 ? 0 : 70)); }
      for (let i = 1; i < 5; i++) { const yy = s * 26 + (s < 0 ? -70 : 0) + i * 14; ctx.moveTo(-50, yy); ctx.lineTo(10, yy); }
      ctx.stroke(); ctx.lineWidth = 1.8;
    }
    ctx.restore();
  }
  // laser + debris
  const kl = clamp((p - 0.45) / 0.1);
  if (kl > 0) {
    const tip = [sx + Math.cos(0.5) * 70, sy + Math.sin(0.5) * 70];
    const hit = [cx - 150, cy - 120];
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    const fl = 0.8 + 0.2 * Math.sin(t * 40);
    for (const [w, a] of [[16, 0.08], [7, 0.25], [2.5, 0.9]]) {
      ctx.strokeStyle = `rgba(255,150,70,${a * kl * fl})`; ctx.lineWidth = w;
      ctx.beginPath(); ctx.moveTo(tip[0], tip[1]); ctx.lineTo(hit[0], hit[1]); ctx.stroke();
    }
    glowDot(ctx, hit[0], hit[1], 90, '255,170,90', 0.8 * kl);
    for (let i = 0; i < 70; i++) {
      const life = 0.8 + hash(i) * 1.2, ph = ((t + hash(i + 3) * life) % life) / life;
      const a = -2.2 + (hash(i + 7) - 0.5) * 2.2, d = ph * (60 + hash(i + 11) * 200);
      ctx.fillStyle = `rgba(255,${190 + hash(i) * 60 | 0},120,${(1 - ph) * kl})`;
      ctx.beginPath(); ctx.arc(hit[0] + Math.cos(a) * d, hit[1] + Math.sin(a) * d, 1 + hash(i + 5) * 2.2, 0, TAU); ctx.fill();
    }
    ctx.restore();
    // cargo drones
    for (let i = 0; i < 4; i++) {
      const ph = ((t * 0.35 + i / 4) % 1);
      const x = lerp(hit[0] - 10, sx + 20, ph), y = lerp(hit[1] - 10, sy + 40, ph) - Math.sin(ph * Math.PI) * 40;
      ctx.strokeStyle = th.ink; ctx.lineWidth = 1.2; ctx.globalAlpha = kl * Math.sin(ph * Math.PI);
      ctx.strokeRect(x - 6, y - 6, 12, 12);
    }
    ctx.globalAlpha = 1;
  }
  const kt = clamp((p - 0.55) / 0.3);
  ctx.globalAlpha = kt; ctx.strokeStyle = th.soft; ctx.lineWidth = 1;
  pl(ctx, [[cx + 60, cy + 190], [cx + 120, cy + 270], [cx + 360, cy + 270]], kt);
  monoText(ctx, th, '16 PSYCHE', cx + 360, cy + 258, 16, { color: th.accent, weight: 700, align: 'right' });
  monoText(ctx, th, 'EST. VALUE: $10,000 QUADRILLION', cx + 360, cy + 296, 11, { color: th.soft, align: 'right' });
  ctx.restore();
};

// ------------------------------------------------------------ 2070s: space elevator
ILL.elevator = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 1.6), t = sc.T;
  ctx.save();
  const G = { cx: 0, cy: 1180, R: 1000, lon0: 30 + t * 1.5, tilt: -0.15 };
  earthGlobe(ctx, th, G, { lw: 1.4, night: 0.55, atmoA: 0.6, atmoW: 0.07 });
  const base = [0, G.cy - G.R], topY = -620;
  const kt = E.inOut(clamp(p / 0.5));
  const yTop = lerp(base[1], topY, kt);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (const [w, a] of [[12, 0.06], [5, 0.18], [1.8, 0.95]]) {
    ctx.strokeStyle = `rgba(255,220,160,${a})`; ctx.lineWidth = w;
    ctx.beginPath(); ctx.moveTo(0, base[1]); ctx.lineTo(0, yTop); ctx.stroke();
  }
  ctx.restore();
  // ticks + labels
  const marks = [[130, '100 KM'], [20, '1,000 KM'], [-140, '10,000 KM']];
  ctx.strokeStyle = th.ink; ctx.lineWidth = 1.2;
  for (const [y, lab] of marks) {
    if (y < yTop) continue;
    ctx.globalAlpha = 0.8; ctx.beginPath(); ctx.moveTo(-10, y); ctx.lineTo(10, y); ctx.stroke();
    monoText(ctx, th, lab, -22, y + 4, 12, { align: 'right', color: th.soft });
  }
  ctx.globalAlpha = 1;
  // GEO station
  const kg = clamp((p - 0.4) / 0.25);
  if (kg > 0) {
    const gy = -340;
    ctx.save(); ctx.globalAlpha = kg; ctx.strokeStyle = th.ink; ctx.lineWidth = 1.8;
    ctx.beginPath(); ctx.ellipse(0, gy, 110, 26, 0, 0, TAU); ctx.stroke();
    ctx.beginPath(); ctx.ellipse(0, gy, 80, 18, 0, 0, TAU); ctx.stroke();
    for (let i = 0; i < 6; i++) { const a = t * 0.3 + i / 6 * TAU; ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(Math.cos(a) * 110, gy + Math.sin(a) * 26); ctx.stroke(); }
    ctx.fillStyle = '#0f1116'; ctx.beginPath(); ctx.roundRect(-22, gy - 34, 44, 68, 8); ctx.fill(); ctx.stroke();
    ctx.globalCompositeOperation = 'lighter'; glowDot(ctx, 0, gy, 60, '255,200,120', 0.5);
    ctx.restore();
    monoText(ctx, th, '35,786 KM · GEO STATION', 130, gy + 4, 13, { color: th.accent, weight: 700, alpha: kg });
  }
  // climbers
  const kc = clamp((p - 0.35) / 0.2);
  for (let i = 0; i < 2; i++) {
    const ph = (t * 0.22 + i * 0.5) % 1;
    const y = lerp(base[1] - 20, -380, ph);
    if (y < yTop) continue;
    ctx.save(); ctx.globalAlpha = kc;
    ctx.fillStyle = '#12141a'; ctx.strokeStyle = th.ink; ctx.lineWidth = 1.6;
    ctx.beginPath(); ctx.roundRect(-11, y - 20, 22, 40, 6); ctx.fill(); ctx.stroke();
    ctx.globalCompositeOperation = 'lighter'; glowDot(ctx, 0, y, 36, '255,190,110', 0.9);
    ctx.restore();
  }
  ctx.restore();
};

// ------------------------------------------------------------ 2080s: Mars (cities, then terraforming)
const MARS_DARK = [[70, 10, 15], [-30, 45, 17], [-40, -25, 19], [0, -5, 10], [145, -20, 17], [110, 45, 19], [-90, -28, 8], [30, -45, 14], [-160, 10, 12], [180, -35, 15]];
const MARS_CITIES = [[-40, 20], [10, 5], [60, -15], [-80, -10], [100, 25], [-10, 40], [140, 0]];
ILL.mars = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 2.2), t = sc.T;
  const R0 = 300;
  const G = { cx: 0, cy: 0, R: R0, lon0: -10 + t * 6, tilt: 0.32 };
  ctx.save();
  // orbit ring behind
  const ring = (front) => {
    ctx.save(); ctx.strokeStyle = th.ink; ctx.lineWidth = 1.2; ctx.globalAlpha = 0.35;
    ctx.beginPath(); ctx.ellipse(0, 0, 470, 96, -0.22, front ? 0 : Math.PI, front ? Math.PI : TAU); ctx.stroke();
    for (let i = 0; i < 16; i++) {
      const a = t * 0.25 + i / 16 * TAU, x = 470 * Math.cos(a), y = 96 * Math.sin(a);
      if ((Math.sin(a) > 0) !== front) continue;
      const X = x * Math.cos(-0.22) - y * Math.sin(-0.22), Y = x * Math.sin(-0.22) + y * Math.cos(-0.22);
      ctx.globalAlpha = 0.9; ctx.fillStyle = th.accent; ctx.fillRect(X - 2, Y - 2, 4, 4);
    }
    ctx.restore();
  };
  ring(false);
  ctx.save();
  ctx.beginPath(); ctx.arc(0, 0, R0, 0, TAU); ctx.clip();
  const g = ctx.createRadialGradient(-R0 * 0.35, -R0 * 0.35, 10, 0, 0, R0);
  g.addColorStop(0, '#c98c62'); g.addColorStop(0.5, '#9b5a3a'); g.addColorStop(1, '#3a170c');
  ctx.fillStyle = g; ctx.fillRect(-R0, -R0, 2 * R0, 2 * R0);
  ctx.filter = 'blur(9px)';
  for (const [lo, la, r] of MARS_DARK) sphereSpot(ctx, G, lo, la, r, 'rgba(58,28,16,0.3)');
  for (const [lo, la, r] of [[-110, 5, 20], [40, 25, 16], [170, 40, 18]]) sphereSpot(ctx, G, lo, la, r, 'rgba(236,180,130,0.12)');
  ctx.filter = 'none';
  for (let i = 0; i < 40; i++) {
    const q = sph(hash(i) * 360 - 180, hash(i + 40) * 140 - 70, G);
    if (q[2] < 0.2) continue;
    const r = (2 + hash(i + 80) * 7) * q[2];
    ctx.strokeStyle = 'rgba(40,16,8,0.35)'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.ellipse(q[0], q[1], r * Math.max(0.3, q[2]), r, 0, 0, TAU); ctx.stroke();
  }
  // valles marineris
  ctx.strokeStyle = 'rgba(60,18,6,0.7)'; ctx.lineWidth = 3;
  ctx.beginPath(); let pen = false;
  for (let lo = -100; lo <= -35; lo += 2) { const q = sph(lo, -8 + Math.sin(lo * 0.2) * 2, G); if (q[2] > 0) { pen ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1]); pen = true; } else pen = false; }
  ctx.stroke();
  const olympus = sph(-134, 18, G); if (olympus[2] > 0) { ctx.strokeStyle = 'rgba(255,220,190,0.4)'; ctx.lineWidth = 2; ctx.beginPath(); ctx.ellipse(olympus[0], olympus[1], 16 * olympus[2], 16, 0, 0, TAU); ctx.stroke(); }
  // terraforming
  if (o.green) {
    const kg = E.inOut(clamp((sc.t - 0.2) / 2.3));
    ctx.filter = 'blur(3px)';
    sphereSpot(ctx, G, -20, 42, 30 * kg, 'rgba(24,62,128,0.92)');
    sphereSpot(ctx, G, 70, -42, 18 * kg, 'rgba(28,70,140,0.9)');
    sphereSpot(ctx, G, -60, 14, 10 * kg, 'rgba(28,70,140,0.85)');
    for (const [lo, la, r] of [[-70, 32, 14], [-10, 30, 13], [30, 12, 16], [95, 22, 13], [-110, -2, 12], [15, -22, 11], [140, 32, 15], [-40, -10, 9], [60, -12, 10]]) sphereSpot(ctx, G, lo, la, r * kg, 'rgba(70,112,58,0.85)');
    ctx.filter = 'blur(8px)';
    for (let i = 0; i < 9; i++) sphereSpot(ctx, G, -170 + i * 40 + t * 3, -10 + Math.sin(i * 2) * 30, 7 * kg, `rgba(255,255,255,${0.35 * kg})`);
    ctx.filter = 'none';
  }
  sphereSpot(ctx, G, 0, 90, 11, 'rgba(255,246,236,0.9)');
  graticule(ctx, G, 30, 'rgba(255,230,200,0.10)', 1);
  shadeSphere(ctx, G, -0.55, -0.45, 0.9);
  // city lights
  if (o.lights) {
    ctx.globalCompositeOperation = 'lighter';
    const kl = o.green ? 1 : clamp((sc.t - 0.2) / 1.6);
    MARS_CITIES.forEach(([lo, la], ci) => {
      const n = 22 + (ci % 3) * 8;
      for (let k = 0; k < n; k++) {
        if (hash(ci * 50 + k) > kl) continue;
        const q = sph(lo + (hash(ci * 7 + k) - 0.5) * 12, la + (hash(ci * 13 + k) - 0.5) * 9, G);
        if (q[2] <= 0.05) continue;
        const night = clamp((q[0] + q[1] * 0.4) / R0 + 0.35);
        const a = (0.15 + 0.85 * night) * (0.8 + 0.2 * Math.sin(t * 5 + k));
        ctx.fillStyle = `rgba(255,210,140,${a})`; ctx.fillRect(q[0] - 1.6, q[1] - 1.6, 3.2, 3.2);
        if (k % 3 === 0 && night > 0.6) glowDot(ctx, q[0], q[1], 16, '255,180,100', 0.45 * a * night);
      }
    });
    ctx.globalCompositeOperation = 'source-over';
  }
  ctx.restore();
  atmosphere(ctx, G, o.green ? '130,190,255' : '255,150,90', o.green ? 0.45 : 0.3, 0.1);
  ctx.strokeStyle = 'rgba(255,220,190,0.35)'; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(0, 0, R0, 0, TAU); ctx.stroke();
  ring(true);
  // phobos
  const pa = t * 0.5 + 1;
  const px = 380 * Math.cos(pa), py = -150 + 40 * Math.sin(pa);
  ctx.fillStyle = '#8a6a55'; ctx.beginPath(); ctx.ellipse(px, py, 11, 8, 0.4, 0, TAU); ctx.fill();
  ctx.restore();
};

// ------------------------------------------------------------ 2080s: the Earth breathes again
ILL.earth = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 2.4), t = sc.T;
  const breath = 1 + 0.035 * Math.sin(sc.t * 2.6);
  const G = { cx: 0, cy: 0, R: 300, lon0: -20 + t * 7, tilt: 0.35 };
  const kg = E.inOut(clamp((sc.t - 0.3) / 2.0));
  const land = `rgba(${Math.round(lerp(150, 70, kg))},${Math.round(lerp(128, 150, kg))},${Math.round(lerp(80, 72, kg))},0.92)`;
  ctx.save();
  atmosphere(ctx, { cx: 0, cy: 0, R: 300 * breath }, '120,200,255', 0.55, 0.2);
  earthGlobe(ctx, th, G, { land, coast: 'rgba(235,240,220,0.6)', lw: 1, night: 0.8, atmoA: 0.4 });
  // clouds
  ctx.save(); ctx.beginPath(); ctx.arc(0, 0, 300, 0, TAU); ctx.clip();
  shadeSphere(ctx, G, -0.5, -0.4, 0.55);
  ctx.restore();
  // CO2 readout
  const ppm = Math.round(lerp(404, 350, kg));
  ctx.globalAlpha = clamp((p - 0.2) / 0.3);
  monoText(ctx, th, `CO₂ ${ppm} PPM`, 250, 330, 18, { color: '#9fd0ff', weight: 700 });
  monoText(ctx, th, 'BACK TOWARD PRE-INDUSTRIAL', 250, 356, 11, { color: th.soft });
  ctx.strokeStyle = th.soft; ctx.lineWidth = 1; pl(ctx, [[244, 322], [200, 240]]);
  ctx.restore();
};

// ------------------------------------------------------------ 2090s: Dyson swarm
const SWARM = [
  { r: 205, inc: 1.2, yaw: 0.3, n: 150 },
  { r: 255, inc: -1.05, yaw: 1.2, n: 180 },
  { r: 318, inc: 0.38, yaw: -0.4, n: 220 },
  { r: 392, inc: -0.22, yaw: 2.2, n: 260 },
];
ILL.dyson = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 2.4), t = sc.T;
  const C = { rx: 0.25, ry: 0, dist: 3000, f: 3000, cx: 0, cy: 0 };
  const Rs = 108;
  const pts = [];
  SWARM.forEach((S, si) => {
    const nv = Math.floor(S.n * clamp(p * 1.35 - si * 0.12));
    const w = 0.35 * Math.pow(200 / S.r, 1.5);
    for (let i = 0; i < nv; i++) {
      const a = i / S.n * TAU + t * w;
      let q = [S.r * Math.cos(a), 0, S.r * Math.sin(a)];
      q = rotX(q, S.inc); q = rotY(q, S.yaw);
      const tg = rotY(rotX([-Math.sin(a), 0, Math.cos(a)], S.inc), S.yaw);
      const P = proj(q, C), P2 = proj([q[0] + tg[0] * 12, q[1] + tg[1] * 12, q[2] + tg[2] * 12], C);
      pts.push({ P, P2, z: P[2] - C.dist, si });
    }
  });
  const orbit = (S, back) => {
    const L = [];
    for (let i = 0; i <= 120; i++) { const a = i / 120 * TAU; let q = rotY(rotX([S.r * Math.cos(a), 0, S.r * Math.sin(a)], S.inc), S.yaw); L.push(proj(q, C)); }
    ctx.beginPath(); let pen = false;
    for (const q of L) { const behind = q[2] > C.dist; if (behind === back) { pen ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1]); pen = true; } else pen = false; }
    ctx.stroke();
  };
  ctx.save();
  ctx.strokeStyle = 'rgba(244,196,105,0.16)'; ctx.lineWidth = 1;
  SWARM.forEach((S, si) => { if (p * 1.35 - si * 0.12 > 0) orbit(S, true); });
  const drawPanels = (back) => {
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineWidth = 3; ctx.lineCap = 'round';
    for (const q of pts) {
      if ((q.z > 0) !== back) continue;
      if (back && Math.hypot(q.P[0], q.P[1]) < Rs + 6) continue;
      const tw = 0.55 + 0.45 * Math.sin(t * 3 + q.P[0] * 0.05);
      ctx.strokeStyle = `rgba(255,${200 + (q.si * 12)},${130 + q.si * 20},${(back ? 0.45 : 0.95) * tw})`;
      ctx.beginPath(); ctx.moveTo(q.P[0], q.P[1]); ctx.lineTo(q.P2[0], q.P2[1]); ctx.stroke();
    }
    ctx.restore();
  };
  drawPanels(true);
  // sun
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  glowDot(ctx, 0, 0, 560, '255,150,60', 0.4);
  glowDot(ctx, 0, 0, 250, '255,200,120', 0.7);
  ctx.restore();
  rays(ctx, th, 0, 0, 60, Rs, 520, 0.12, t * 0.05);
  const sg = ctx.createRadialGradient(-20, -20, 0, 0, 0, Rs);
  sg.addColorStop(0, '#fffdf2'); sg.addColorStop(0.7, '#ffe2a0'); sg.addColorStop(1, '#ffb257');
  ctx.fillStyle = sg; ctx.beginPath(); ctx.arc(0, 0, Rs, 0, TAU); ctx.fill();
  ctx.strokeStyle = 'rgba(244,196,105,0.16)'; ctx.lineWidth = 1;
  SWARM.forEach((S, si) => { if (p * 1.35 - si * 0.12 > 0) orbit(S, false); });
  drawPanels(false);
  const kl = clamp((p - 0.55) / 0.3);
  ctx.globalAlpha = kl;
  ctx.strokeStyle = th.soft; ctx.lineWidth = 1; pl(ctx, [[230, 270], [290, 340], [330, 340]], kl);
  monoText(ctx, th, 'TARGET: 0.001% OF THE SUN', 150, 372, 14, { color: th.accent, weight: 700 });
  monoText(ctx, th, '= TODAY\'S ENERGY USE × 190,000,000', 150, 396, 11, { color: th.soft });
  ctx.restore();
};

// ------------------------------------------------------------ 2090s: Mars in 30 days
ILL.rocket = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 2.6), t = sc.T;
  const sx = -60, sy = 80;
  const orb = (rx, ry, a) => [sx + rx * Math.cos(a), sy + ry * Math.sin(a)];
  ctx.save();
  const ko = E.inOut(clamp(p / 0.3));
  ctx.strokeStyle = th.ink; ctx.lineWidth = 1.2; ctx.globalAlpha = 0.45;
  pl(ctx, ell(sx, sy, 270, 100, 0, 160), ko);
  pl(ctx, ell(sx, sy, 470, 175, 0, 200), ko);
  ctx.globalAlpha = 1;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  glowDot(ctx, sx, sy, 160, '255,180,90', 0.8); glowDot(ctx, sx, sy, 40, '255,245,220', 1);
  ctx.restore();
  const aE = 2.35, aM = 0.35;
  const E0 = orb(270, 100, aE), M0 = orb(470, 175, aM);
  // old way (Hohmann, 7 months) dashed
  const kh = clamp((p - 0.15) / 0.3);
  if (kh > 0) {
    ctx.save(); ctx.setLineDash([4, 9]); ctx.strokeStyle = th.soft; ctx.lineWidth = 1.2;
    const hoh = bezPath([E0, [E0[0] - 60, E0[1] + 300], [M0[0] + 180, M0[1] + 300], [M0[0] + 60, M0[1] + 40], [M0[0] + 30, M0[1] + 20], [M0[0] + 10, M0[1] + 8], M0], 30);
    pl(ctx, hoh, kh); ctx.restore();
    monoText(ctx, th, 'CHEMICAL ROCKET · 7 MONTHS', 250, 340, 12, { color: th.soft, alpha: kh });
  }
  // fast transfer
  const path = bezPath([E0, [E0[0] + 180, E0[1] - 170], [M0[0] - 200, M0[1] - 150], M0], 90);
  const kf = E.inOut(clamp((p - 0.25) / 0.6));
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
  for (const [w, a] of [[10, 0.07], [4, 0.22], [1.8, 0.9]]) { ctx.strokeStyle = `rgba(255,205,130,${a})`; ctx.lineWidth = w; pl(ctx, path, kf); }
  if (kf > 0 && kf < 1) {
    const idx = Math.min(path.length - 2, Math.floor(kf * (path.length - 1)));
    const a = path[idx], b = path[idx + 1];
    const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
    const f = kf * (path.length - 1) - idx, x = lerp(a[0], b[0], f), y = lerp(a[1], b[1], f);
    glowDot(ctx, x, y, 70, '255,210,150', 0.9);
    ctx.strokeStyle = 'rgba(160,200,255,0.9)'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - Math.cos(ang) * 60, y - Math.sin(ang) * 60); ctx.stroke();
    ctx.restore(); ctx.save();
    ctx.translate(x, y); ctx.rotate(ang); ctx.fillStyle = '#f5ecd8';
    ctx.beginPath(); ctx.moveTo(14, 0); ctx.lineTo(-10, -5); ctx.lineTo(-10, 5); ctx.closePath(); ctx.fill();
  }
  ctx.restore();
  // planets
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  glowDot(ctx, E0[0], E0[1], 34, '120,180,255', 0.8); glowDot(ctx, M0[0], M0[1], 30, '255,130,80', 0.8);
  ctx.restore();
  ctx.fillStyle = '#6fa8ff'; ctx.beginPath(); ctx.arc(E0[0], E0[1], 9, 0, TAU); ctx.fill();
  ctx.fillStyle = '#e0643a'; ctx.beginPath(); ctx.arc(M0[0], M0[1], 8, 0, TAU); ctx.fill();
  monoText(ctx, th, 'EARTH', E0[0], E0[1] + 32, 12, { align: 'center', color: th.ink, weight: 700 });
  monoText(ctx, th, 'MARS', M0[0], M0[1] + 30, 12, { align: 'center', color: th.ink, weight: 700 });
  const day = Math.max(1, Math.round(30 * kf));
  monoText(ctx, th, `DAY ${String(day).padStart(2, '0')}`, 150, -300, 44, { color: th.accent, weight: 700, spacing: 4 });
  monoText(ctx, th, 'FUSION DRIVE · 1 G THRUST', 152, -264, 12, { color: th.soft });
  ctx.restore();
};

// ------------------------------------------------------------ 2090s: dark matter solved
const GALAXY = (() => {
  const R = rng(5), pts = [];
  for (let i = 0; i < 3400; i++) {
    const arm = i % 2, r = 24 + 340 * Math.pow(R(), 0.75);
    const th0 = arm * Math.PI + 2.4 * Math.log(r / 24) + (R() - 0.5) * 0.6 * (1 + 50 / r);
    const c = R();
    pts.push({ r, th0, s: 0.5 + Math.pow(R(), 3) * 2.2, c, j: R() });
  }
  return pts;
})();
ILL.galaxy = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 2.4), t = sc.T;
  const tilt = 0.42, rot = -0.35;
  ctx.save();
  // halo
  const kh = clamp((p - 0.3) / 0.35);
  if (kh > 0) {
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    const hg = ctx.createRadialGradient(0, 0, 60, 0, 0, 560);
    hg.addColorStop(0, `rgba(150,120,255,${0.16 * kh})`); hg.addColorStop(0.7, `rgba(120,100,230,${0.07 * kh})`); hg.addColorStop(1, 'rgba(120,100,230,0)');
    ctx.fillStyle = hg; ctx.beginPath(); ctx.ellipse(0, 0, 560, 440, rot, 0, TAU); ctx.fill();
    ctx.restore();
    ctx.save(); ctx.setLineDash([3, 10]); ctx.strokeStyle = 'rgba(190,175,255,0.6)'; ctx.lineWidth = 1.2;
    for (const [rx, ry] of [[480, 380], [540, 425]]) pl(ctx, ell(0, 0, rx, ry, rot, 140), kh);
    ctx.restore();
    ctx.globalAlpha = kh; ctx.strokeStyle = th.soft; ctx.lineWidth = 1;
    pl(ctx, [[-330, -300], [-420, -380], [-520, -380]], kh);
    monoText(ctx, th, 'DARK MATTER HALO', -528, -390, 13, { align: 'right', color: '#c9bcff', weight: 700 });
    monoText(ctx, th, '85% OF ALL MATTER', -528, -368, 11, { align: 'right', color: th.soft });
    ctx.globalAlpha = 1;
  }
  // stars
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const kr = E.out(clamp(p / 0.5));
  for (const s of GALAXY) {
    if (s.j > kr) continue;
    const w = 0.12 * 100 / Math.max(60, s.r);
    const a = s.th0 + t * w;
    const x = s.r * Math.cos(a), y = s.r * Math.sin(a) * tilt;
    const X = x * Math.cos(rot) - y * Math.sin(rot), Y = x * Math.sin(rot) + y * Math.cos(rot);
    const core = clamp(1 - s.r / 160);
    const col = s.c < 0.08 ? '255,150,170' : core > 0.3 ? '255,226,170' : '190,210,255';
    ctx.fillStyle = `rgba(${col},${0.35 + 0.5 * (s.s / 2.7)})`;
    ctx.fillRect(X - s.s / 2, Y - s.s / 2, s.s, s.s);
  }
  glowDot(ctx, 0, 0, 130, '255,220,170', 0.65 * kr);
  glowDot(ctx, 0, 0, 40, '255,248,230', 0.85 * kr);
  ctx.restore();
  // rotation curve inset
  const ki = clamp((p - 0.45) / 0.35);
  if (ki > 0) {
    const gx = 210, gy = 190, gw = 250, gh = 130;
    ctx.globalAlpha = ki; ctx.strokeStyle = th.ink; ctx.lineWidth = 1.2;
    pl(ctx, [[gx, gy], [gx, gy + gh], [gx + gw, gy + gh]]);
    monoText(ctx, th, 'ROTATION CURVE', gx, gy - 12, 11, { color: th.ink, weight: 700 });
    const exp = [], obs = [];
    for (let i = 0; i <= 50; i++) {
      const r = i / 50, x = gx + 6 + r * (gw - 10);
      exp.push([x, gy + gh - gh * 0.9 * Math.min(1, 3 * r) * (r < 0.33 ? 1 : Math.sqrt(0.33 / r))]);
      obs.push([x, gy + gh - gh * 0.9 * Math.min(1, 3 * r) * (r < 0.33 ? 1 : 1 - 0.05 * (r - 0.33))]);
    }
    ctx.setLineDash([4, 6]); ctx.strokeStyle = th.soft; pl(ctx, exp, ki); ctx.setLineDash([]);
    ctx.strokeStyle = th.accent; ctx.lineWidth = 2.4; pl(ctx, obs, ki);
    monoText(ctx, th, 'OBSERVED', gx + gw - 4, gy + 30, 10, { align: 'right', color: th.accent });
    monoText(ctx, th, 'EXPECTED', gx + gw - 4, gy + gh - 34, 10, { align: 'right', color: th.soft });
    ctx.globalAlpha = 1;
  }
  ctx.restore();
};

// ------------------------------------------------------------ 2100: Kardashev type I
const HUBS = [[29, 41], [-74, 40.7], [139.7, 35.7], [2.3, 48.8], [-46.6, -23.5], [77.2, 28.6], [18.4, -33.9], [151.2, -33.8], [-99.1, 19.4], [116.4, 39.9], [31.2, 30], [37.6, 55.7], [-122.4, 37.8], [103.8, 1.3], [-58.4, -34.6], [3.4, 6.5], [55.3, 25.2], [-3.7, 40.4]];
const LINKS = [[0, 3], [0, 10], [0, 5], [0, 11], [0, 16], [1, 3], [1, 12], [1, 8], [2, 9], [2, 12], [2, 7], [3, 17], [3, 15], [4, 14], [4, 15], [5, 13], [5, 16], [6, 15], [6, 4], [7, 13], [8, 14], [9, 13], [10, 15], [11, 9], [16, 13], [12, 8], [17, 1]];
function slerpLL(a, b, s) {
  const v = ([lo, la]) => [Math.cos(la * DEG) * Math.cos(lo * DEG), Math.sin(la * DEG), Math.cos(la * DEG) * Math.sin(lo * DEG)];
  const A = v(a), B = v(b);
  const d = Math.acos(clamp(A[0] * B[0] + A[1] * B[1] + A[2] * B[2], -1, 1)) || 1e-6;
  const k1 = Math.sin((1 - s) * d) / Math.sin(d), k2 = Math.sin(s * d) / Math.sin(d);
  const x = A[0] * k1 + B[0] * k2, y = A[1] * k1 + B[1] * k2, z = A[2] * k1 + B[2] * k2;
  return [Math.atan2(z, x) / DEG, Math.asin(clamp(y, -1, 1)) / DEG, d];
}
ILL.typeI = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 4.5), t = sc.T;
  const G = { cx: 0, cy: 0, R: 290, lon0: 10 + t * 5, tilt: 0.38 };
  ctx.save();
  earthGlobe(ctx, th, G, { ocean0: '#153a5e', ocean1: '#040d18', land: 'rgba(90,80,50,0.9)', coast: 'rgba(244,196,105,0.8)', lw: 1.1, night: 0.7, atmo: '255,200,120', atmoA: 0.35 });
  // grid glow
  ctx.save(); ctx.beginPath(); ctx.arc(0, 0, G.R, 0, TAU); ctx.clip();
  ctx.globalCompositeOperation = 'lighter';
  graticule(ctx, G, 15, `rgba(244,196,105,${0.2 * clamp(p * 2)})`, 1);
  ctx.restore();
  // arcs
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
  LINKS.forEach(([i, j], n) => {
    const q = E.inOut(clamp(p * 2.2 - n * 0.045));
    if (q <= 0) return;
    const A = HUBS[i], B = HUBS[j];
    const pts = [];
    for (let s = 0; s <= 40; s++) {
      const u = s / 40 * q; const [lo, la, d] = slerpLL(A, B, u);
      const h = 1 + 0.18 * Math.sin(Math.PI * s / 40) * Math.min(1, d);
      pts.push(sph(lo, la, G, h));
    }
    ctx.beginPath(); let pen = false;
    for (const P of pts) {
      const vis = P[2] > 0 || Math.hypot(P[0], P[1]) > G.R;
      if (vis) { pen ? ctx.lineTo(P[0], P[1]) : ctx.moveTo(P[0], P[1]); pen = true; } else pen = false;
    }
    ctx.strokeStyle = 'rgba(255,200,120,0.25)'; ctx.lineWidth = 5; ctx.stroke();
    ctx.strokeStyle = 'rgba(255,230,180,0.9)'; ctx.lineWidth = 1.6; ctx.stroke();
    const head = pts[pts.length - 1];
    if (q < 1 && (head[2] > 0 || Math.hypot(head[0], head[1]) > G.R)) glowDot(ctx, head[0], head[1], 16, '255,230,190', 0.9);
  });
  for (const h of HUBS) { const P = sph(h[0], h[1], G); if (P[2] > 0) glowDot(ctx, P[0], P[1], 12, '255,210,140', 0.9 * clamp(p * 3)); }
  ctx.restore();
  // gauge
  const kg = clamp((p - 0.1) / 0.3);
  if (kg > 0) {
    const Rg = 390, a0 = Math.PI * 0.8, a1 = Math.PI * 2.2;
    const kval = lerp(0.912, 1.0, E.inOut(clamp((p - 0.25) / 0.35)));
    const ang = v => lerp(a0, a1, (v - 0.7) / 0.4);
    ctx.save(); ctx.globalAlpha = kg; ctx.strokeStyle = th.ink; ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.arc(0, 0, Rg, a0, a1); ctx.stroke();
    for (let v = 0.7; v <= 1.1001; v += 0.01) {
      const a = ang(v), major = Math.abs(v * 10 - Math.round(v * 10)) < 1e-6;
      ctx.lineWidth = major ? 2 : 1; ctx.beginPath(); ctx.moveTo(Math.cos(a) * Rg, Math.sin(a) * Rg); ctx.lineTo(Math.cos(a) * (Rg + (major ? 18 : 8)), Math.sin(a) * (Rg + (major ? 18 : 8))); ctx.stroke();
      if (major) monoText(ctx, th, v.toFixed(1), Math.cos(a) * (Rg + 40), Math.sin(a) * (Rg + 40) + 5, 13, { align: 'center', color: Math.abs(v - 1) < 1e-6 ? th.accent : th.soft, weight: 700 });
    }
    ctx.strokeStyle = th.accent; ctx.lineWidth = 5; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.arc(0, 0, Rg, a0, ang(kval)); ctx.stroke();
    const a = ang(kval);
    ctx.globalCompositeOperation = 'lighter';
    glowDot(ctx, Math.cos(a) * Rg, Math.sin(a) * Rg, 50, '255,200,110', 0.9);
    ctx.restore();
  }
  ctx.restore();
};

// ------------------------------------------------------------ 2100s: first sail to the stars
ILL.sail = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 2.8), t = sc.T;
  const spd = E.in(clamp(sc.t / 3));
  ctx.save();
  // star streaks
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
  const dir = [0.82, -0.57];
  for (let i = 0; i < 140; i++) {
    const x = (hash(i) - 0.5) * 1700, y = (hash(i + 50) - 0.5) * 1000;
    const L = 4 + spd * (40 + hash(i + 9) * 160);
    const off = (sc.t * 400 * spd * (0.5 + hash(i + 3))) % 1700;
    const X = ((x - off * dir[0] + 850) % 1700 + 1700) % 1700 - 850, Y = ((y - off * dir[1] + 500) % 1000 + 1000) % 1000 - 500;
    ctx.strokeStyle = `rgba(220,230,255,${0.25 + 0.5 * hash(i + 7)})`; ctx.lineWidth = 1 + hash(i + 2);
    ctx.beginPath(); ctx.moveTo(X, Y); ctx.lineTo(X - dir[0] * L, Y - dir[1] * L); ctx.stroke();
  }
  ctx.restore();
  // target star
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  glowDot(ctx, 420, -300, 120, '255,230,190', 0.8); glowDot(ctx, 420, -300, 16, '255,255,255', 1);
  ctx.fillStyle = 'rgba(255,240,210,0.7)'; ctx.fillRect(420 - 90, -301, 180, 2); ctx.fillRect(419, -300 - 60, 2, 120);
  ctx.restore();
  monoText(ctx, th, 'ALPHA CENTAURI', 420, -240, 13, { color: th.ink, weight: 700, align: 'center' });
  // sail position
  const u = E.in(clamp(sc.t / 3.2));
  const cx = lerp(-60, 330, u), cy = lerp(160, -110, u);
  // lasers
  const kl = clamp(sc.t / 0.4);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 6; i++) {
    const sx = -900 + i * 36, sy = 520 - i * 10;
    const fl = 0.7 + 0.3 * Math.sin(t * 30 + i);
    const g = ctx.createLinearGradient(sx, sy, cx, cy);
    g.addColorStop(0, `rgba(255,90,60,${0.05 * kl})`); g.addColorStop(1, `rgba(255,140,90,${0.55 * kl * fl})`);
    ctx.strokeStyle = g; ctx.lineWidth = 2.2;
    ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(cx, cy + 10); ctx.stroke();
  }
  ctx.restore();
  // sail
  ctx.save(); ctx.translate(cx, cy); ctx.rotate(-0.6 + Math.sin(t) * 0.05); ctx.scale(1, 0.62);
  const S = 150, bil = 18;
  const edge = (x0, y0, x1, y1) => { ctx.quadraticCurveTo((x0 + x1) / 2 + (y1 - y0) * bil / (2 * S), (y0 + y1) / 2 - (x1 - x0) * bil / (2 * S), x1, y1); };
  ctx.beginPath(); ctx.moveTo(-S, -S); edge(-S, -S, S, -S); edge(S, -S, S, S); edge(S, S, -S, S); edge(-S, S, -S, -S);
  const sg = ctx.createLinearGradient(-S, -S, S, S);
  sg.addColorStop(0, 'rgba(255,236,200,0.38)'); sg.addColorStop(0.5, 'rgba(244,196,105,0.12)'); sg.addColorStop(1, 'rgba(255,236,200,0.3)');
  ctx.fillStyle = sg; ctx.fill();
  ctx.strokeStyle = th.accent; ctx.lineWidth = 2; ctx.stroke();
  ctx.strokeStyle = 'rgba(244,196,105,0.35)'; ctx.lineWidth = 1;
  ctx.beginPath(); for (let i = -2; i <= 2; i++) { ctx.moveTo(i * S / 3, -S); ctx.lineTo(i * S / 3, S); ctx.moveTo(-S, i * S / 3); ctx.lineTo(S, i * S / 3); } ctx.stroke();
  ctx.restore();
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; glowDot(ctx, cx, cy, 40, '255,240,210', 1); ctx.restore();
  const v = 0.2 * E.inOut(clamp(sc.t / 2.6));
  monoText(ctx, th, `SPEED ${v.toFixed(2)} c`, -420, -300, 34, { color: th.accent, weight: 700, spacing: 3 });
  monoText(ctx, th, '20% OF LIGHT SPEED · ARRIVES 2126', -418, -268, 12, { color: th.soft });
  ctx.restore();
};

// ------------------------------------------------------------ 2110s: O'Neill cylinders
ILL.oneill = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 2.0), t = sc.T;
  const C = { rx: 0.32, ry: -0.62, rz: 0.12, dist: 2600, f: 2300, cx: 0, cy: 0 };
  const L = 470, Rc = 150, spin = t * 0.35;
  const P3 = (x, a, r = Rc) => [x, r * Math.cos(a + spin), r * Math.sin(a + spin)];
  const k = E.inOut(clamp(p / 0.55));
  ctx.save();
  const lines = [];
  for (let i = 0; i < 12; i++) { const a = i / 12 * TAU; lines.push([P3(-L, a), P3(L, a)]); }
  for (let j = 0; j <= 8; j++) { const x = -L + j * 2 * L / 8; lines.push(Array.from({ length: 49 }, (_, i) => P3(x, i / 48 * TAU))); }
  ctx.strokeStyle = th.ink; ctx.lineWidth = 1.3; ctx.globalAlpha = 0.8;
  wire(ctx, C, lines, { prog: k, seq: true, back: 0.12 });
  // window strips glow
  const kw = clamp((p - 0.35) / 0.3);
  if (kw > 0) {
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let s = 0; s < 3; s++) {
      const a = s / 3 * TAU + TAU / 12;
      for (let x = -L + 20; x < L; x += 22) {
        for (const da of [-0.12, 0, 0.12]) {
          const q = proj(P3(x, a + da), C), n = rotX(rotY([0, Math.cos(a + da + spin), Math.sin(a + da + spin)], C.ry), C.rx);
          if (n[2] > 0.1) continue;
          ctx.fillStyle = `rgba(255,214,150,${0.8 * kw})`; ctx.fillRect(q[0] - 1.5, q[1] - 1.5, 3, 3);
        }
      }
    }
    ctx.restore();
  }
  // mirrors
  const km = clamp((p - 0.45) / 0.3);
  if (km > 0) {
    for (let s = 0; s < 3; s++) {
      const a = s / 3 * TAU + TAU / 12;
      const A = proj(P3(-L, a), C), B = proj(P3(L, a), C);
      const open = 0.3 * km;
      const Cq = proj(P3(L, a + open, Rc + 170 * km), C), D = proj(P3(-L, a + open, Rc + 170 * km), C);
      ctx.fillStyle = 'rgba(244,196,105,0.05)'; fillPoly(ctx, [A, B, Cq, D]);
      ctx.strokeStyle = th.ink; ctx.globalAlpha = 0.28; ctx.lineWidth = 1; pathPoly(ctx, [A, B, Cq, D]); ctx.stroke(); ctx.globalAlpha = 1;
    }
  }
  // end caps
  for (const x of [-L, L]) {
    const cap = Array.from({ length: 49 }, (_, i) => proj(P3(x, i / 48 * TAU), C));
    ctx.strokeStyle = th.ink; ctx.lineWidth = 2; pl(ctx, cap, k);
    for (let i = 0; i < 6; i++) { const a = i / 6 * TAU; pl(ctx, [proj([x, 0, 0], C), proj(P3(x, a), C)], k); }
  }
  const hub = proj([L + 40, 0, 0], C);
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; glowDot(ctx, hub[0], hub[1], 50, '255,200,120', 0.8 * k); ctx.restore();
  // ships
  for (let i = 0; i < 3; i++) {
    const ph = (t * 0.12 + i / 3) % 1;
    const q = proj([lerp(900, L + 60, ph), 40 * Math.sin(i * 2), 30 * i], C);
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; glowDot(ctx, q[0], q[1], 14, '255,230,190', 0.9 * Math.sin(ph * Math.PI)); ctx.restore();
  }
  const kl = clamp((p - 0.6) / 0.3);
  monoText(ctx, th, 'Ø 8 KM · 32 KM LONG · POP. 1,000,000', 0, 360, 13, { align: 'center', color: th.soft, alpha: kl });
  ctx.restore();
};

// ------------------------------------------------------------ 2110s: first photo of another world
let PLANET = null;
function vnoise3(x, y, z) {
  const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z);
  const xf = x - xi, yf = y - yi, zf = z - zi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf), w = zf * zf * (3 - 2 * zf);
  const h = (a, b, c) => { const s = Math.sin(a * 157.31 + b * 113.97 + c * 271.13) * 43758.5453; return s - Math.floor(s); };
  const l = (a, b, s) => a + (b - a) * s;
  return l(l(l(h(xi, yi, zi), h(xi + 1, yi, zi), u), l(h(xi, yi + 1, zi), h(xi + 1, yi + 1, zi), u), v),
           l(l(h(xi, yi, zi + 1), h(xi + 1, yi, zi + 1), u), l(h(xi, yi + 1, zi + 1), h(xi + 1, yi + 1, zi + 1), u), v), w);
}
function fbm3(x, y, z, oct = 5) { let s = 0, a = 0.5, f = 1, n = 0; for (let i = 0; i < oct; i++) { s += a * vnoise3(x * f, y * f, z * f); n += a; a *= 0.5; f *= 2.03; } return s / n; }
function buildPlanet() {
  const N = 400, c = mk(N, N), x = c.getContext('2d'), id = x.createImageData(N, N);
  const L = [-0.75, -0.25, 0.6], ll = Math.hypot(...L); L[0] /= ll; L[1] /= ll; L[2] /= ll;
  for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
    const nx = (i + 0.5) / N * 2 - 1, ny = (j + 0.5) / N * 2 - 1, d = nx * nx + ny * ny, o = (j * N + i) * 4;
    if (d > 1) { id.data[o + 3] = 0; continue; }
    const nz = Math.sqrt(1 - d);
    const lam = Math.max(0, nx * L[0] + ny * L[1] + nz * L[2]);
    const h = fbm3(nx * 2.2 + 3, ny * 2.2, nz * 2.2 + 7);
    let r, g, b;
    if (h > 0.53) { const e = (h - 0.53) * 6; r = 150 + e * 60; g = 118 + e * 30; b = 70; if (h > 0.6) { r = 96; g = 120; b = 66; } }
    else { const e = h / 0.53; r = 20 + e * 20; g = 60 + e * 50; b = 90 + e * 60; }
    const cl = fbm3(nx * 3.5 + 11, ny * 5 + 2, nz * 3.5, 4);
    const cloud = clamp((cl - 0.52) * 4);
    r = lerp(r, 245, cloud); g = lerp(g, 240, cloud); b = lerp(b, 235, cloud);
    const shade = 0.08 + 0.92 * Math.pow(lam, 0.8);
    const rim = Math.pow(1 - nz, 3) * 0.6;
    id.data[o] = Math.min(255, r * shade * 1.05 + rim * 60);
    id.data[o + 1] = Math.min(255, g * shade * 0.88 + rim * 110);
    id.data[o + 2] = Math.min(255, b * shade * 0.75 + rim * 160);
    id.data[o + 3] = 255;
  }
  x.putImageData(id, 0, 0);
  return c;
}
ILL.proxima = (ctx, th, sc, o = {}) => {
  if (!PLANET) PLANET = buildPlanet();
  const p = o.prog ?? clamp(sc.t / 2.6), t = sc.T;
  const S = 470, x0 = -S / 2 + 30, y0 = -S / 2;
  ctx.save();
  const kf = E.out(clamp(p / 0.25));
  ctx.strokeStyle = th.ink; ctx.lineWidth = 2; ctx.globalAlpha = kf;
  const br = 36;
  for (const [cx, cy, sx, sy] of [[x0, y0, 1, 1], [x0 + S, y0, -1, 1], [x0, y0 + S, 1, -1], [x0 + S, y0 + S, -1, -1]]) {
    ctx.beginPath(); ctx.moveTo(cx, cy + sy * br); ctx.lineTo(cx, cy); ctx.lineTo(cx + sx * br, cy); ctx.stroke();
  }
  ctx.globalAlpha = kf * 0.25; ctx.lineWidth = 1;
  ctx.strokeRect(x0, y0, S, S);
  // image
  const steps = [4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 400];
  const q = clamp((p - 0.12) / 0.7);
  const res = steps[Math.min(steps.length - 1, Math.floor(q * steps.length))];
  const img = mk(res, res), ix = img.getContext('2d');
  ix.imageSmoothingEnabled = true; ix.imageSmoothingQuality = 'high';
  ix.drawImage(PLANET, 0, 0, res, res);
  ctx.globalAlpha = kf;
  ctx.imageSmoothingEnabled = res >= 400;
  const pad = 30;
  ctx.drawImage(img, x0 + pad, y0 + pad, S - 2 * pad, S - 2 * pad);
  ctx.imageSmoothingEnabled = true;
  if (q < 1) {
    const sy = y0 + ((t * 1.3) % 1) * S;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.strokeStyle = 'rgba(244,196,105,0.5)'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(x0, sy); ctx.lineTo(x0 + S, sy); ctx.stroke(); ctx.restore();
  }
  ctx.globalAlpha = kf * 0.35; ctx.strokeStyle = th.ink; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(x0 + S / 2, y0 + 10); ctx.lineTo(x0 + S / 2, y0 + 40); ctx.moveTo(x0 + S / 2, y0 + S - 10); ctx.lineTo(x0 + S / 2, y0 + S - 40);
  ctx.moveTo(x0 + 10, y0 + S / 2); ctx.lineTo(x0 + 40, y0 + S / 2); ctx.moveTo(x0 + S - 10, y0 + S / 2); ctx.lineTo(x0 + S - 40, y0 + S / 2); ctx.stroke();
  ctx.globalAlpha = kf;
  monoText(ctx, th, 'PROXIMA CENTAURI b', x0, y0 - 16, 13, { color: th.ink, weight: 700 });
  monoText(ctx, th, '4.24 LIGHT-YEARS', x0 + S, y0 - 16, 13, { align: 'right', color: th.soft });
  monoText(ctx, th, `RESOLUTION ${res >= 400 ? 'FULL' : res + ' × ' + res}`, x0, y0 + S + 28, 12, { color: th.soft });
  const blink = q < 1 ? (Math.floor(t * 3) % 2 ? 'RECEIVING DATA' : '') : 'COMPLETE';
  monoText(ctx, th, blink, x0 + S, y0 + S + 28, 12, { align: 'right', color: th.accent, weight: 700 });
  ctx.restore();
};

// ------------------------------------------------------------ 2110s: we are not alone
ILL.spectrum = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 2.4), t = sc.T;
  const X0 = -420, X1 = 420, by = 90, bh = 64;
  const lines = [[0.93, 'O₂', 10], [0.83, 'H₂O', 8], [0.62, 'CH₄', 6], [0.46, 'O₃', 5]];
  ctx.save();
  const kb = E.inOut(clamp(p / 0.35));
  ctx.save(); ctx.beginPath(); ctx.rect(X0, by, (X1 - X0) * kb, bh); ctx.clip();
  const g = ctx.createLinearGradient(X0, 0, X1, 0);
  [[0, '#5a2fd6'], [0.14, '#2f5cff'], [0.3, '#1fb6e8'], [0.45, '#35d86c'], [0.6, '#dbe840'], [0.74, '#ffb03a'], [0.88, '#ff4a2a'], [1, '#9e1010']].forEach(([s, c]) => g.addColorStop(s, c));
  ctx.globalAlpha = 0.85; ctx.fillStyle = g; ctx.fillRect(X0, by, X1 - X0, bh);
  ctx.globalAlpha = 1;
  lines.forEach(([f, , w], i) => {
    const q = clamp((p - 0.38 - i * 0.1) / 0.08);
    if (q <= 0) return;
    ctx.fillStyle = `rgba(4,4,8,${0.92 * q})`; ctx.fillRect(lerp(X0, X1, f) - w / 2, by, w, bh);
  });
  ctx.restore();
  ctx.strokeStyle = th.ink; ctx.lineWidth = 1.2; ctx.globalAlpha = kb; ctx.strokeRect(X0, by, X1 - X0, bh);
  for (let nm = 400; nm <= 800; nm += 100) {
    const x = lerp(X0, X1, (nm - 380) / 420);
    ctx.beginPath(); ctx.moveTo(x, by + bh); ctx.lineTo(x, by + bh + 8); ctx.stroke();
    monoText(ctx, th, String(nm), x, by + bh + 28, 12, { align: 'center', color: th.soft });
  }
  monoText(ctx, th, 'WAVELENGTH · NM', X1, by + bh + 54, 11, { align: 'right', color: th.soft });
  // intensity curve with dips
  const kc = E.inOut(clamp((p - 0.1) / 0.4));
  const pts = [];
  for (let i = 0; i <= 300; i++) {
    const f = i / 300, x = lerp(X0, X1, f);
    let v = 0.25 + 0.6 * Math.exp(-Math.pow((f - 0.42) / 0.38, 2)) + 0.03 * Math.sin(f * 90) * Math.sin(f * 17);
    lines.forEach(([lf, , w], li) => { const q = clamp((p - 0.38 - li * 0.1) / 0.08); v -= q * 0.42 * Math.exp(-Math.pow((f - lf) / (w / 1400), 2)); });
    pts.push([x, by - 30 - v * 260]);
  }
  ctx.globalAlpha = 1; ctx.strokeStyle = th.ink; ctx.lineWidth = 2; pl(ctx, pts, kc);
  lines.forEach(([f, lab], i) => {
    const q = clamp((p - 0.38 - i * 0.1) / 0.08);
    if (q <= 0) return;
    const x = lerp(X0, X1, f);
    ctx.globalAlpha = q; ctx.strokeStyle = th.accent; ctx.lineWidth = 1.2; ctx.setLineDash([3, 5]);
    ctx.beginPath(); ctx.moveTo(x, by - 4); ctx.lineTo(x, -300); ctx.stroke(); ctx.setLineDash([]);
    monoText(ctx, th, lab, x, -312, 22, { align: 'center', color: th.accent, weight: 700, spacing: 1 });
  });
  ILL.stamp(ctx, th, sc, 330, 300, 'LIFE', 'DETECTED', clamp((p - 0.82) / 0.1));
  ctx.restore();
};

// ------------------------------------------------------------ 2120: ...and still young
ILL.ecg = (ctx, th, sc, o = {}) => {
  const t = sc.t;
  ctx.save();
  ctx.strokeStyle = 'rgba(234,220,189,0.06)'; ctx.lineWidth = 1;
  ctx.beginPath();
  for (let x = -900; x <= 900; x += 40) { ctx.moveTo(x, -200); ctx.lineTo(x, 200); }
  for (let y = -200; y <= 200; y += 40) { ctx.moveTo(-900, y); ctx.lineTo(900, y); }
  ctx.stroke();
  const beat = x => {
    const u = ((x % 420) + 420) % 420 / 420;
    let y = 0;
    y -= 14 * Math.exp(-Math.pow((u - 0.12) / 0.03, 2));
    y += 18 * Math.exp(-Math.pow((u - 0.26) / 0.008, 2));
    y -= 120 * Math.exp(-Math.pow((u - 0.29) / 0.012, 2));
    y += 40 * Math.exp(-Math.pow((u - 0.32) / 0.01, 2));
    y -= 30 * Math.exp(-Math.pow((u - 0.5) / 0.05, 2));
    return y;
  };
  const head = -880 + t * 560;
  const pts = [];
  for (let x = -880; x <= Math.min(head, 880); x += 3) pts.push([x, beat(x + 160)]);
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineJoin = 'round';
  for (const [w, a] of [[12, 0.06], [5, 0.2], [2.2, 1]]) { ctx.strokeStyle = `rgba(255,200,120,${a})`; ctx.lineWidth = w; pl(ctx, pts); }
  if (pts.length) { const h = pts[pts.length - 1]; glowDot(ctx, h[0], h[1], 50, '255,230,180', 1); }
  ctx.restore();
  const k = clamp((t - 0.8) / 0.4);
  monoText(ctx, th, 'CALENDAR AGE · 94', -460, 150, 24, { color: th.ink, weight: 600, alpha: k, align: 'center', spacing: 5 });
  monoText(ctx, th, 'BIOLOGICAL AGE · 30', 460, 150, 24, { color: th.accent, weight: 700, alpha: clamp((t - 1.3) / 0.4), align: 'center', spacing: 5 });
  ctx.restore();
};

// ------------------------------------------------------------ 2120: a hundred years in medallions
const MEDALS = [
  ['neural', 0.17], ['robot', 0.13], ['tokamak', 0.2], ['marsPrint', 0.17], ['dna', 0.16], ['organ', 0.16],
  ['clock', 0.2], ['moon', 0.12], ['mars', 0.2], ['dyson', 0.15], ['sail', 0.12], ['oneill', 0.14],
];
ILL.medallions = (ctx, th, sc, o = {}) => {
  const t = sc.T, lt = sc.t;
  ctx.save();
  ILL.spark(ctx, sc, 0, 80, 0.9, 8);
  const N = MEDALS.length, rot = lt * 0.12;
  const items = MEDALS.map(([name, s], i) => {
    const a = rot + i / N * TAU;
    return { name, s, a, x: Math.cos(a) * 610, y: 90 + Math.sin(a) * 180, d: Math.sin(a), i };
  }).sort((u, v) => u.d - v.d);
  const fake = { t: 6, T: t, p: 1, dur: 3 };
  for (const it of items) {
    const k = E.outBack(clamp((lt - 0.1 - it.i * 0.08) / 0.4));
    if (k <= 0) continue;
    const sc2 = lerp(0.72, 1.18, (it.d + 1) / 2) * k, r = 84;
    ctx.save(); ctx.translate(it.x, it.y); ctx.scale(sc2, sc2);
    ctx.globalAlpha = lerp(0.45, 1, (it.d + 1) / 2);
    ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.fillStyle = '#0c0e13'; ctx.fill();
    ctx.save(); ctx.clip(); ctx.scale(it.s * 0.95, it.s * 0.95);
    ILL[it.name](ctx, th, fake, it.name === 'mars' ? { lights: true, prog: 1 } : { prog: 1 });
    ctx.restore();
    ctx.strokeStyle = th.accent; ctx.lineWidth = 2.2; ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.stroke();
    ctx.lineWidth = 1; ctx.globalAlpha *= 0.6; ctx.beginPath(); ctx.arc(0, 0, r + 8, 0, TAU); ctx.stroke();
    ctx.restore();
  }
  ctx.restore();
};

// ------------------------------------------------------------ finale: the future is built
ILL.build = (ctx, th, sc, o = {}) => {
  const lt = sc.t, t = sc.T;
  const C = { rx: 0.42, ry: 0.5 + lt * 0.05, dist: 2600, f: 1500, cx: 0, cy: 330 };
  ctx.save();
  rays(ctx, th, 0, -40, 80, 100, 1300, 0.12 * E.out(clamp(lt / 1.5)), t * 0.02);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  glowDot(ctx, 0, -40, 700, '255,170,80', 0.28 * E.out(clamp(lt / 1.2)));
  ctx.restore();
  const g = [];
  for (let i = -8; i <= 8; i++) { g.push([[i * 120, 0, -960], [i * 120, 0, 960]]); g.push([[-960, 0, i * 120], [960, 0, i * 120]]); }
  ctx.strokeStyle = 'rgba(244,196,105,0.5)'; ctx.lineWidth = 1;
  wire(ctx, C, g, { prog: E.out(clamp(lt / 1.0)), back: 0.05 });
  const bld = [];
  for (let i = -5; i <= 5; i++) for (let j = -5; j <= 5; j++) {
    const h = hash(i * 31 + j * 7);
    if (h < 0.35) continue;
    const d = Math.hypot(i, j);
    const H = (80 + Math.pow(hash(i * 13 + j * 3), 2) * 560) * (1.2 - d / 8);
    if (H <= 30) continue;
    bld.push({ i, j, H, d });
  }
  bld.sort((a, b) => proj([b.i * 120, 0, b.j * 120], C)[2] - proj([a.i * 120, 0, a.j * 120], C)[2]);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (const b of bld) {
    const grow = E.out(clamp((lt - 0.2 - b.d * 0.12) / 1.2));
    if (grow <= 0) continue;
    const x0 = b.i * 120 - 40, x1 = b.i * 120 + 40, z0 = b.j * 120 - 40, z1 = b.j * 120 + 40;
    const v = boxVerts(x0, 0, z0, x1, b.H * grow, z1);
    ctx.strokeStyle = `rgba(255,205,130,${0.5})`; ctx.lineWidth = 1.2;
    wire(ctx, C, boxEdges(v), { back: 0.3 });
    for (let y = 30; y < b.H * grow - 10; y += 34) {
      const q = proj([x1, y, (z0 + z1) / 2], C);
      ctx.fillStyle = `rgba(255,220,160,${0.5 * (0.5 + 0.5 * Math.sin(y + b.i * 3 + t * 2))})`; ctx.fillRect(q[0] - 2, q[1] - 1, 4, 2);
    }
  }
  ctx.restore();
  embers(ctx, 0, 380, t, 90, 21, 1400, 700);
  ctx.restore();
};
