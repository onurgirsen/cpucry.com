'use strict';
/* Illustrations, part B: 2050s–2060s (Earth & life). */

// Catmull-Rom interpolation through [x, y] keypoints
function catmull(pts, x) {
  if (x <= pts[0][0]) return pts[0][1];
  for (let i = 0; i < pts.length - 1; i++) {
    if (x <= pts[i + 1][0]) {
      const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
      const t = (x - p1[0]) / (p2[0] - p1[0]), t2 = t * t, t3 = t2 * t;
      return 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3);
    }
  }
  return pts[pts.length - 1][1];
}

// ------------------------------------------------------------ 2050: the carbon curve bends
const CO2 = [[1958, 315], [1970, 325.7], [1980, 338.8], [1990, 354.4], [2000, 369.7], [2010, 389.9], [2020, 414.2], [2026, 427],
  [2032, 436], [2040, 443], [2048, 446], [2056, 443], [2064, 434], [2072, 420], [2080, 404], [2090, 386], [2100, 368]];
ILL.carbon = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 2.1);
  const X0 = -430, X1 = 430, Yt = -240, Yb = 230;
  const gx = y => lerp(X0, X1, (y - 1950) / 150), gy = v => lerp(Yb, Yt, (v - 300) / 160);
  ctx.save();
  ctx.lineCap = 'round';
  const ka = E.inOut(clamp(p / 0.3));
  ctx.strokeStyle = th.ink; ctx.lineWidth = 1.8;
  pl(ctx, [[X0, Yt - 20], [X0, Yb], [X1 + 20, Yb]], ka);
  ctx.globalAlpha = 0.22 * ka; ctx.lineWidth = 1; ctx.setLineDash([2, 6]);
  for (const v of [350, 400, 450]) pl(ctx, [[X0, gy(v)], [X1, gy(v)]]);
  for (let y = 1975; y <= 2100; y += 25) pl(ctx, [[gx(y), Yb], [gx(y), Yt]]);
  ctx.setLineDash([]); ctx.globalAlpha = ka;
  for (let y = 1950; y <= 2100; y += 25) {
    monoText(ctx, th, String(y), gx(y), Yb + 30, 12, { align: 'center', color: th.soft });
    pl(ctx, [[gx(y), Yb], [gx(y), Yb + 8]]);
  }
  for (const v of [300, 350, 400, 450]) {
    monoText(ctx, th, String(v), X0 - 16, gy(v) + 4, 12, { align: 'right', color: th.soft });
    pl(ctx, [[X0 - 8, gy(v)], [X0, gy(v)]]);
  }
  monoText(ctx, th, 'CO₂ · PPM', X0, Yt - 34, 13, { color: th.ink, weight: 700 });
  // today marker
  const kt = clamp((p - 0.3) / 0.2);
  if (kt > 0) {
    ctx.globalAlpha = kt; ctx.strokeStyle = th.ink; ctx.lineWidth = 1.2; ctx.setLineDash([6, 6]);
    pl(ctx, [[gx(2026), Yb], [gx(2026), Yt + 10]]); ctx.setLineDash([]);
    monoText(ctx, th, 'TODAY', gx(2026) + 8, Yt + 24, 12, { color: th.ink, weight: 700 });
  }
  // curve
  const kc = clamp((p - 0.12) / 0.7);
  const hist = [], fut = [];
  for (let y = 1958; y <= 2100; y += 0.25) {
    const season = 1.1 * Math.sin(y * TAU) * (y <= 2026 ? 1 : Math.max(0, 1 - (y - 2026) / 20));
    const pt = [gx(y), gy(catmull(CO2, y) + season)];
    if (y <= 2026) hist.push(pt); else fut.push(pt);
  }
  fut.unshift(hist[hist.length - 1]);
  const split = (2026 - 1958) / (2100 - 1958);
  ctx.globalAlpha = 1;
  ctx.strokeStyle = th.ink; ctx.lineWidth = 1.8;
  pl(ctx, hist, clamp(kc / split));
  ctx.strokeStyle = th.accent; ctx.lineWidth = 4;
  pl(ctx, fut, clamp((kc - split) / (1 - split)));
  // peak
  const kp = clamp((kc - 0.66) / 0.12);
  if (kp > 0) {
    const px = gx(2048), py = gy(446);
    ctx.globalAlpha = kp; ctx.fillStyle = paperFill(th); ctx.strokeStyle = th.accent; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(px, py, 10 * E.outBack(kp), 0, TAU); ctx.fill(); ctx.stroke();
    ctx.lineWidth = 1.2; pl(ctx, [[px, py - 14], [px, py - 60]], kp);
    monoText(ctx, th, 'PEAK · 2048', px, py - 72, 13, { align: 'center', color: th.accent, weight: 700 });
  }
  const kd = clamp((kc - 0.9) / 0.1);
  if (kd > 0) {
    ctx.globalAlpha = kd;
    ctx.fillStyle = th.accent;
    arrowHead(ctx, fut[fut.length - 1][0] + 6, fut[fut.length - 1][1] + 3, 0.45, 16);
  }
  ctx.restore();
};

// ------------------------------------------------------------ 2050s: brain–computer interface
const HEAD = bezPath([
  [-95, 280], [-92, 220], [-100, 170], [-130, 120],
  [-190, 60], [-215, -60], [-180, -150],
  [-140, -250], [-20, -300], [70, -262],
  [140, -232], [180, -170], [182, -95],
  [184, -70], [176, -58], [182, -45],
  [196, -10], [224, 30], [230, 48],
  [232, 60], [214, 66], [200, 66],
  [206, 76], [210, 86], [204, 94],
  [196, 100], [208, 108], [204, 118],
  [200, 140], [196, 168], [170, 178],
  [140, 186], [100, 186], [80, 200],
  [66, 214], [64, 250], [70, 280],
], 14);
const BRAIN = bezPath([
  [-160, -60], [-200, -120], [-150, -230], [-60, -250],
  [20, -270], [120, -240], [140, -170],
  [160, -120], [140, -70], [100, -60],
  [60, -40], [0, -60], [-40, -40],
  [-90, -20], [-140, -30], [-160, -60],
], 16);
ILL.bci = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 2.0), t = sc.T;
  ctx.save(); ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  const kh = E.inOut(clamp(p / 0.45));
  ctx.globalAlpha = clamp(p / 0.3);
  pathPoly(ctx, HEAD, false); ctx.lineTo(-95, 280); ctx.closePath();
  ctx.fillStyle = paperFill(th); ctx.fill(); ctx.fillStyle = th.fill; ctx.fill();
  hatch(ctx, () => { pathPoly(ctx, HEAD); }, -220, -300, 240, 290, 8, -0.8, 0.12, th.ink);
  ctx.globalAlpha = 1; ctx.strokeStyle = th.ink; ctx.lineWidth = 2.8;
  pl(ctx, HEAD, kh);
  // ear, eye
  const kf = clamp((p - 0.3) / 0.3);
  ctx.globalAlpha = kf; ctx.lineWidth = 2;
  pl(ctx, bezPath([[-6, -34], [22, -40], [34, 10], [18, 40], [8, 60], [-10, 58], [-14, 44]], 12), kf);
  pl(ctx, bezPath([[4, -10], [16, -12], [18, 12], [4, 20]], 10), kf);
  pl(ctx, bezPath([[132, -40], [146, -52], [162, -50], [170, -40]], 10), kf);
  pl(ctx, bezPath([[128, -70], [146, -84], [168, -80], [178, -70]], 10), kf);
  // brain + lace
  const kb = clamp((p - 0.2) / 0.4);
  if (kb > 0) {
    ctx.globalAlpha = kb * 0.8; ctx.lineWidth = 1.8; ctx.strokeStyle = th.ink;
    pl(ctx, BRAIN, E.inOut(kb));
    ctx.save(); pathPoly(ctx, BRAIN); ctx.clip();
    ctx.globalAlpha = kb * 0.35; ctx.lineWidth = 1.3;
    for (let i = 0; i < 9; i++) {
      const pts = []; const y0 = -240 + i * 24;
      for (let j = 0; j <= 30; j++) { const x = -190 + j * 12; pts.push([x, y0 + Math.sin(j * 0.9 + i * 1.7) * 9 + Math.sin(j * 0.33 + i) * 6]); }
      pl(ctx, pts, E.inOut(kb));
    }
    // neural lace
    const R = rng(9), nodes = [];
    for (let gy = -250; gy <= -40; gy += 30) for (let gx = -190; gx <= 150; gx += 32) nodes.push([gx + (R() - 0.5) * 16 + (gy / 30 % 2) * 12, gy + (R() - 0.5) * 12]);
    const kl = clamp((p - 0.4) / 0.3);
    ctx.globalAlpha = kl * 0.75; ctx.strokeStyle = th.accent; ctx.lineWidth = 1.1;
    ctx.beginPath();
    for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
      const d = Math.hypot(nodes[i][0] - nodes[j][0], nodes[i][1] - nodes[j][1]);
      if (d < 44) { ctx.moveTo(nodes[i][0], nodes[i][1]); ctx.lineTo(nodes[j][0], nodes[j][1]); }
    }
    ctx.stroke();
    nodes.forEach((n, i) => {
      const f = 0.5 + 0.5 * Math.sin(t * 6 + i * 2.1);
      ctx.globalAlpha = kl * (0.4 + 0.6 * f); ctx.fillStyle = th.accent;
      ctx.beginPath(); ctx.arc(n[0], n[1], 2 + 1.8 * f, 0, TAU); ctx.fill();
    });
    ctx.restore();
  }
  // implant
  const ki = clamp((p - 0.45) / 0.2);
  if (ki > 0) {
    ctx.globalAlpha = ki; ctx.save(); ctx.translate(40, -268); ctx.rotate(0.18);
    ctx.fillStyle = th.ink; ctx.beginPath(); ctx.roundRect(-22, -8, 44, 14, 4); ctx.fill();
    ctx.fillStyle = th.accent; ctx.fillRect(-4, -5, 8, 8);
    ctx.restore();
  }
  // thought waves toward the text box
  const kw = clamp((p - 0.5) / 0.2);
  if (kw > 0) {
    ctx.strokeStyle = th.accent; ctx.lineWidth = 2.2;
    for (let i = 0; i < 4; i++) {
      const ph = ((t * 0.9 + i / 4) % 1);
      ctx.globalAlpha = kw * (1 - ph) * 0.9;
      ctx.beginPath(); ctx.arc(60, -280, 40 + ph * 150, -1.15, -0.35); ctx.stroke();
    }
    // box
    const bx = 110, by = -470, bw = 340, bh = 104;
    ctx.globalAlpha = kw;
    ctx.fillStyle = paperFill(th); ctx.strokeStyle = th.ink; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.roundRect(bx, by, bw, bh, 10); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(bx + 40, by + bh); ctx.lineTo(bx + 20, by + bh + 26); ctx.lineTo(bx + 70, by + bh); ctx.fillStyle = paperFill(th); ctx.fill();
    ctx.beginPath(); ctx.moveTo(bx + 40, by + bh); ctx.lineTo(bx + 20, by + bh + 26); ctx.lineTo(bx + 70, by + bh); ctx.stroke();
    const msg = 'hello, world.';
    const n = Math.floor(clamp((p - 0.58) / 0.28) * msg.length);
    const cur = Math.floor(t * 3) % 2 ? '▌' : ' ';
    monoText(ctx, th, '> ' + msg.slice(0, n) + cur, bx + 22, by + 50, 24, { color: th.ink, spacing: 1, weight: 600 });
    monoText(ctx, th, 'THOUGHT → TEXT · 0.2 S', bx + 22, by + 82, 11, { color: th.soft, spacing: 3 });
  }
  ctx.restore();
};

// ------------------------------------------------------------ 2050s: vertical farms
ILL.vfarm = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 2.0), t = sc.T;
  const C = { rx: 0.26, ry: -0.6, dist: 2300, f: 2000, cx: 0, cy: 150 };
  const ground = -300;
  const towers = [
    { x0: -420, x1: -260, z0: -60, z1: 100, h: 430, d: 0.1 },
    { x0: -90, x1: 90, z0: -90, z1: 90, h: 640, d: 0 },
    { x0: 200, x1: 340, z0: -150, z1: -10, h: 330, d: 0.2 },
  ];
  ctx.save(); ctx.lineJoin = 'round';
  // ground grid
  const kg = E.inOut(clamp(p / 0.4));
  ctx.strokeStyle = th.ink; ctx.lineWidth = 1; ctx.globalAlpha = 0.25;
  const gl = [];
  for (let i = -6; i <= 6; i++) { gl.push([[i * 100, ground, -600], [i * 100, ground, 600]]); gl.push([[-600, ground, i * 100], [600, ground, i * 100]]); }
  wire(ctx, C, gl, { prog: kg, back: 0.1 });
  ctx.globalAlpha = 1;
  // sort towers back-to-front
  const order = towers.map((T, i) => ({ T, z: proj([(T.x0 + T.x1) / 2, 0, (T.z0 + T.z1) / 2], C)[2] })).sort((a, b) => b.z - a.z);
  for (const { T } of order) {
    const g = E.out(clamp((p - T.d) / 0.55));
    if (g <= 0) continue;
    const top = ground + T.h * g;
    const v = boxVerts(T.x0, ground, T.z0, T.x1, top, T.z1);
    solidBox(ctx, th, C, v, { lw: 2 });
    // floors + plants on visible faces
    const faces = [[4, 5], [1, 5], [0, 4], [0, 1]];
    for (const [a, b] of faces) {
      const A = v[a], B = v[b];
      // visible when the face midpoint is nearer to the camera than the box centre
      const mid = proj([(A[0] + B[0]) / 2, ground, (A[2] + B[2]) / 2], C), cen = proj([(T.x0 + T.x1) / 2, ground, (T.z0 + T.z1) / 2], C);
      if (mid[2] > cen[2]) continue;
      for (let y = ground + 45; y < top - 10; y += 45) {
        const L1 = proj([A[0], y, A[2]], C), L2 = proj([B[0], y, B[2]], C);
        ctx.strokeStyle = th.ink; ctx.lineWidth = 1.1; ctx.globalAlpha = 0.7;
        ctx.beginPath(); ctx.moveTo(L1[0], L1[1]); ctx.lineTo(L2[0], L2[1]); ctx.stroke();
        const n = 9;
        for (let k = 1; k < n; k++) {
          const q = proj([lerp(A[0], B[0], k / n), y, lerp(A[2], B[2], k / n)], C);
          const s = C.f / q[2] * 1.1;
          ctx.globalAlpha = 0.75;
          ctx.beginPath(); ctx.ellipse(q[0] - 4 * s, q[1] - 6 * s, 3 * s, 7 * s, -0.6, 0, TAU); ctx.stroke();
          ctx.beginPath(); ctx.ellipse(q[0] + 4 * s, q[1] - 6 * s, 3 * s, 7 * s, 0.6, 0, TAU); ctx.stroke();
          if (hash(k * 13 + y + T.x0) > 0.62) { ctx.fillStyle = th.accent; ctx.globalAlpha = 0.9; ctx.beginPath(); ctx.arc(q[0], q[1] - 13 * s, 2.6 * s, 0, TAU); ctx.fill(); }
        }
      }
      ctx.globalAlpha = 1;
    }
    // roof extras
    if (g > 0.98) {
      const rc = proj([(T.x0 + T.x1) / 2, top, (T.z0 + T.z1) / 2], C);
      if (T.h > 600) {
        const hub = proj([(T.x0 + T.x1) / 2, top + 160, (T.z0 + T.z1) / 2], C);
        ctx.strokeStyle = th.ink; ctx.lineWidth = 2.2;
        ctx.beginPath(); ctx.moveTo(rc[0], rc[1]); ctx.lineTo(hub[0], hub[1]); ctx.stroke();
        for (let k = 0; k < 3; k++) {
          const a = t * 2.2 + k * TAU / 3;
          ctx.beginPath(); ctx.moveTo(hub[0], hub[1]); ctx.lineTo(hub[0] + Math.cos(a) * 70, hub[1] + Math.sin(a) * 70); ctx.stroke();
        }
        ctx.fillStyle = th.accent; ctx.beginPath(); ctx.arc(hub[0], hub[1], 5, 0, TAU); ctx.fill();
      } else {
        const a = proj([T.x0 + 20, top + 2, T.z0 + 20], C), b = proj([T.x1 - 20, top + 2, T.z0 + 20], C), c = proj([T.x1 - 20, top + 2, T.z1 - 20], C), d = proj([T.x0 + 20, top + 2, T.z1 - 20], C);
        ctx.fillStyle = th.fillDeep; fillPoly(ctx, [a, b, c, d]);
        hatch(ctx, () => pathPoly(ctx, [a, b, c, d]), Math.min(a[0], d[0]), Math.min(a[1], b[1]) - 10, Math.max(b[0], c[0]), Math.max(c[1], d[1]) + 10, 5, 0.3, 0.6, th.ink);
      }
    }
  }
  // sun
  ctx.globalAlpha = clamp(p * 2 - 0.2);
  ctx.strokeStyle = th.ink; ctx.lineWidth = 1.6;
  ctx.beginPath(); ctx.arc(-430, -330, 34, 0, TAU); ctx.stroke();
  rays(ctx, th, -430, -330, 28, 44, 84, 0.9, t * 0.1);
  ctx.globalAlpha = clamp((p - 0.6) / 0.3);
  monoText(ctx, th, '1 TOWER = 250 ACRES', 320, -170, 13, { color: th.ink, weight: 700 });
  monoText(ctx, th, '95% LESS WATER', 320, -146, 12, { color: th.soft });
  ctx.restore();
};

// ------------------------------------------------------------ 2060: gene editing
ILL.dna = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 1.8), t = sc.T;
  const A = [-420, 230], B = [430, -250];
  const ax = B[0] - A[0], ay = B[1] - A[1], al = Math.hypot(ax, ay);
  const nx = -ay / al, ny = ax / al;
  const R = 92, turns = 3.1, spin = t * 1.3;
  const pos = (u, ph) => {
    const phi = u * turns * TAU + spin + ph;
    const c = Math.cos(phi), s = Math.sin(phi);
    const sc2 = 1 + 0.08 * s;
    return [A[0] + ax * u + nx * R * c * sc2, A[1] + ay * u + ny * R * c * sc2, s];
  };
  const reveal = E.inOut(clamp(p / 0.6));
  const umax = reveal;
  ctx.save(); ctx.lineCap = 'round';
  // rungs
  const N = 44, rungs = [];
  for (let i = 0; i <= N; i++) {
    const u = i / N; if (u > umax) break;
    const a = pos(u, 0), b = pos(u, Math.PI);
    rungs.push({ i, a, b, z: (a[2] + b[2]) / 2 });
  }
  const edit = 26;
  const kEdit = clamp((p - 0.5) / 0.15);
  rungs.sort((r1, r2) => r1.z - r2.z);
  for (const r of rungs) {
    const m = [(r.a[0] + r.b[0]) / 2, (r.a[1] + r.b[1]) / 2];
    const al2 = lerp(0.3, 1, (r.z + 1) / 2);
    ctx.lineWidth = lerp(2, 4.5, (r.z + 1) / 2);
    ctx.globalAlpha = al2;
    ctx.strokeStyle = th.ink; ctx.beginPath(); ctx.moveTo(r.a[0], r.a[1]); ctx.lineTo(m[0], m[1]); ctx.stroke();
    ctx.strokeStyle = (r.i === edit && kEdit > 0) ? th.accent : (r.i % 3 === 0 ? th.accent : th.soft);
    ctx.beginPath(); ctx.moveTo(m[0], m[1]); ctx.lineTo(r.b[0], r.b[1]); ctx.stroke();
  }
  // strands (back segments first)
  const segs = [];
  for (const ph of [0, Math.PI]) {
    let prev = null;
    for (let i = 0; i <= 240; i++) {
      const u = i / 240; if (u > umax) break;
      const q = pos(u, ph);
      if (prev) segs.push({ a: prev, b: q, z: (prev[2] + q[2]) / 2 });
      prev = q;
    }
  }
  segs.sort((s1, s2) => s1.z - s2.z);
  ctx.strokeStyle = th.ink;
  for (const s of segs) {
    ctx.globalAlpha = lerp(0.35, 1, (s.z + 1) / 2);
    ctx.lineWidth = lerp(2.2, 6, (s.z + 1) / 2);
    ctx.beginPath(); ctx.moveTo(s.a[0], s.a[1]); ctx.lineTo(s.b[0], s.b[1]); ctx.stroke();
  }
  // edit marker
  if (kEdit > 0) {
    const u = edit / N, c = pos(u, 0), d = pos(u, Math.PI);
    const m = [(c[0] + d[0]) / 2, (c[1] + d[1]) / 2];
    ctx.globalAlpha = kEdit; ctx.strokeStyle = th.accent; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(m[0], m[1], 30 + 60 * (1 - E.out(kEdit)), 0, TAU); ctx.stroke();
    ctx.lineWidth = 1.2; pl(ctx, [[m[0] - 22, m[1] - 26], [m[0] - 120, m[1] - 170], [m[0] - 250, m[1] - 170]], kEdit);
    monoText(ctx, th, 'CRISPR · ONE LETTER', m[0] - 256, m[1] - 180, 13, { color: th.accent, weight: 700, align: 'right' });
  }
  // sequence
  const seq = 'ATGCCTAGGATCCGAAG';
  const ks = clamp((p - 0.25) / 0.3);
  if (ks > 0) {
    setFont(ctx, 'mono', 26, 600); ctx.letterSpacing = '0px'; ctx.textAlign = 'center';
    const x0 = -300, y0 = 350, step = 38;
    for (let i = 0; i < seq.length; i++) {
      const q = clamp(ks * seq.length * 1.3 - i);
      if (q <= 0) continue;
      let ch = seq[i];
      ctx.globalAlpha = q * 0.85; ctx.fillStyle = th.ink;
      if (i === 8) {
        const f = clamp((p - 0.55) / 0.12), sy = Math.abs(Math.cos(f * Math.PI));
        ch = f < 0.5 ? 'T' : 'C';
        ctx.save(); ctx.translate(x0 + i * step, y0 - 9); ctx.scale(1, sy || 0.01);
        ctx.fillStyle = f > 0 ? th.accent : th.ink; ctx.fillText(ch, 0, 9); ctx.restore();
        ctx.strokeStyle = th.accent; ctx.lineWidth = 2; ctx.globalAlpha = q;
        ctx.strokeRect(x0 + i * step - 17, y0 - 30, 34, 42);
        continue;
      }
      ctx.fillText(ch, x0 + i * step, y0);
    }
  }
  ctx.restore();
};

// ------------------------------------------------------------ 2060s: bioprinted organs
const HEART = bezPath([
  [-120, -60], [-160, 20], [-120, 150], [-40, 232],
  [20, 200], [150, 110], [150, -20],
  [160, -80], [120, -120], [70, -110],
  [30, -100], [-20, -110], [-60, -100],
  [-90, -95], [-110, -80], [-120, -60],
], 18);
ILL.organ = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 2.6), t = sc.T;
  const top = -270, bot = 236;
  const layerY = lerp(bot, top, E.inOut(clamp((p - 0.1) / 0.85)));
  ctx.save(); ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  // frame
  const kf = E.inOut(clamp(p / 0.25));
  ctx.strokeStyle = th.ink; ctx.lineWidth = 2.4;
  pl(ctx, [[-300, 300], [-300, -330], [300, -330], [300, 300]], kf);
  ctx.lineWidth = 1.2; ctx.globalAlpha = 0.5;
  pl(ctx, [[-286, 300], [-286, -316], [286, -316], [286, 300]], kf);
  ctx.globalAlpha = 1;
  solid(ctx, th, () => { ctx.beginPath(); ctx.rect(-330, 262, 660, 26); }, 2.2);
  hatch(ctx, () => { ctx.beginPath(); ctx.rect(-330, 262, 660, 26); }, -330, 262, 330, 288, 6, 0.8, 0.5, th.ink);
  // ghost model
  const vessels = (fn) => {
    fn(bezPath([[10, -104], [0, -170], [-20, -230], [40, -252], [100, -270], [140, -220], [132, -160]], 16), 36);
    fn(bezPath([[-50, -100], [-60, -150], [-80, -180], [-120, -200]], 16), 30);
    fn([[92, -110], [92, -250]], 30);
  };
  ctx.save(); ctx.setLineDash([5, 8]); ctx.globalAlpha = 0.35; ctx.lineWidth = 1.4;
  pl(ctx, HEART); vessels((P) => pl(ctx, P));
  ctx.restore();
  // printed part (below the current layer)
  ctx.save();
  ctx.beginPath(); ctx.rect(-400, layerY, 800, 600); ctx.clip();
  vessels((P, w) => { ctx.strokeStyle = th.ink; ctx.lineWidth = w + 5; pl(ctx, P); ctx.strokeStyle = paperFill(th); ctx.lineWidth = w; pl(ctx, P); ctx.strokeStyle = th.fillDeep; pl(ctx, P); });
  pathPoly(ctx, HEART); ctx.fillStyle = paperFill(th); ctx.fill(); ctx.fillStyle = th.fillDeep; ctx.fill();
  ctx.save(); pathPoly(ctx, HEART); ctx.clip();
  ctx.strokeStyle = th.ink; ctx.globalAlpha = 0.28; ctx.lineWidth = 1;
  ctx.beginPath(); for (let y = bot; y > -140; y -= 6) { ctx.moveTo(-200, y); ctx.lineTo(200, y); } ctx.stroke();
  ctx.restore();
  ctx.globalAlpha = 1; ctx.strokeStyle = th.ink; ctx.lineWidth = 2.6; pl(ctx, HEART);
  ctx.strokeStyle = th.accent; ctx.lineWidth = 2.2;
  pl(ctx, bezPath([[60, -96], [30, -20], [60, 60], [10, 170]], 16));
  pl(ctx, bezPath([[-20, -90], [-60, -10], [-90, 60], [-60, 150]], 16));
  pl(ctx, bezPath([[100, -60], [120, 0], [90, 60], [100, 100]], 16));
  ctx.restore();
  // active layer + nozzle
  if (p < 0.97) {
    const xs = Math.sin(t * 7) * 150;
    ctx.strokeStyle = th.accent; ctx.lineWidth = 3; ctx.globalAlpha = 0.9;
    ctx.beginPath(); ctx.moveTo(-170, layerY); ctx.lineTo(170, layerY); ctx.stroke();
    ctx.globalAlpha = 1; ctx.strokeStyle = th.ink; ctx.lineWidth = 2.4;
    ctx.beginPath(); ctx.moveTo(xs, -330); ctx.lineTo(xs, layerY - 40); ctx.stroke();
    solid(ctx, th, () => { ctx.beginPath(); ctx.rect(xs - 30, -350, 60, 34); }, 2);
    solid(ctx, th, () => { ctx.beginPath(); ctx.moveTo(xs - 16, layerY - 46); ctx.lineTo(xs + 16, layerY - 46); ctx.lineTo(xs + 3, layerY - 6); ctx.lineTo(xs - 3, layerY - 6); ctx.closePath(); }, 2);
    ctx.fillStyle = th.accent; ctx.beginPath(); ctx.arc(xs, layerY - 2, 4, 0, TAU); ctx.fill();
    ctx.strokeStyle = th.soft; ctx.lineWidth = 1; pl(ctx, [[xs + 20, layerY - 30], [340, -200], [380, -200]]);
    monoText(ctx, th, 'CELL INK', 388, -196, 12, { color: th.soft });
  }
  const layer = Math.round(lerp(1, 2000, E.inOut(clamp((p - 0.1) / 0.85))));
  monoText(ctx, th, `LAYER ${String(layer).padStart(4, '0')} / 2000`, 0, 342, 14, { align: 'center', color: th.ink, weight: 700 });
  ctx.restore();
};

// ------------------------------------------------------------ 2060s: the clock runs backwards
function gear(ctx, cx, cy, r, teeth, rot) {
  ctx.beginPath();
  for (let i = 0; i <= teeth * 4; i++) {
    const a = rot + i / (teeth * 4) * TAU, k = i % 4, rr = (k === 1 || k === 2) ? r + 12 : r;
    const x = cx + Math.cos(a) * rr, y = cy + Math.sin(a) * rr;
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  }
  ctx.closePath();
}
ILL.clock = (ctx, th, sc, o = {}) => {
  const p = o.prog ?? clamp(sc.t / 1.4), lt = sc.t, t = sc.T;
  ctx.save(); ctx.lineJoin = 'round';
  const kg = E.out(clamp(p / 0.5));
  ctx.globalAlpha = kg * 0.8;
  for (const [gx, gy, r, n, dir] of [[-250, 200, 120, 18, 1], [260, -210, 90, 14, -1.35], [300, 170, 60, 10, 2]]) {
    const rot = dir * lt * 0.9;
    gear(ctx, gx, gy, r, n, rot);
    ctx.fillStyle = paperFill(th); ctx.fill(); ctx.fillStyle = th.fill; ctx.fill();
    ctx.strokeStyle = th.ink; ctx.lineWidth = 1.8; ctx.stroke();
    ctx.beginPath(); ctx.arc(gx, gy, r * 0.62, 0, TAU); ctx.stroke();
    ctx.beginPath(); ctx.arc(gx, gy, r * 0.14, 0, TAU); ctx.stroke();
    for (let k = 0; k < 5; k++) { const a = rot + k / 5 * TAU; ctx.beginPath(); ctx.moveTo(gx + Math.cos(a) * r * 0.14, gy + Math.sin(a) * r * 0.14); ctx.lineTo(gx + Math.cos(a) * r * 0.62, gy + Math.sin(a) * r * 0.62); ctx.stroke(); }
  }
  ctx.globalAlpha = 1;
  // face
  const kc = E.inOut(clamp(p / 0.45));
  ctx.beginPath(); ctx.arc(0, 0, 250, 0, TAU); ctx.fillStyle = paperFill(th); ctx.globalAlpha = kc; ctx.fill();
  ctx.fillStyle = th.fill; ctx.fill(); ctx.globalAlpha = 1;
  ctx.strokeStyle = th.ink; ctx.lineWidth = 3; pl(ctx, circ(0, 0, 250, 160, -Math.PI / 2, 1.5 * Math.PI), kc);
  ctx.lineWidth = 1.2; pl(ctx, circ(0, 0, 236, 160, -Math.PI / 2, 1.5 * Math.PI), kc);
  ctx.beginPath();
  for (let i = 0; i < 60; i++) {
    if (i / 60 > kc) break;
    const a = -Math.PI / 2 + i / 60 * TAU, l = i % 5 === 0 ? 22 : 9;
    ctx.moveTo(Math.cos(a) * 234, Math.sin(a) * 234); ctx.lineTo(Math.cos(a) * (234 - l), Math.sin(a) * (234 - l));
  }
  ctx.lineWidth = 2; ctx.stroke();
  const ROM = ['XII', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI'];
  setFont(ctx, 'serif', 30, 700); ctx.letterSpacing = '1px'; ctx.textAlign = 'center'; ctx.fillStyle = th.ink;
  ROM.forEach((r, i) => {
    const q = clamp(kc * 12 - i); if (q <= 0) return;
    const a = -Math.PI / 2 + i / 12 * TAU;
    ctx.globalAlpha = q; ctx.fillText(r, Math.cos(a) * 180, Math.sin(a) * 180 + 11);
  });
  ctx.globalAlpha = 1;
  // hands spin backwards and settle
  const k = E.out(clamp((lt - 0.2) / 2.3));
  const mAng = -Math.PI / 2 + TAU * (10 / 60) - 16 * Math.PI * (1 - k);
  const hAng = -Math.PI / 2 + TAU * (10 / 12 + 10 / 720) - 16 * Math.PI * (1 - k) / 12;
  const sAng = -Math.PI / 2 - 30 * Math.PI * (1 - k) + t * 0.0;
  const hand = (a, len, w, c) => { ctx.strokeStyle = c; ctx.lineWidth = w; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(-Math.cos(a) * 24, -Math.sin(a) * 24); ctx.lineTo(Math.cos(a) * len, Math.sin(a) * len); ctx.stroke(); };
  ctx.globalAlpha = clamp(p * 3 - 0.6);
  hand(hAng, 118, 9, th.ink); hand(mAng, 186, 5, th.ink); hand(sAng, 205, 2.2, th.accent);
  ctx.fillStyle = th.accent; ctx.beginPath(); ctx.arc(0, 0, 9, 0, TAU); ctx.fill();
  // motion arcs while spinning
  if (k < 0.95) {
    ctx.strokeStyle = th.accent; ctx.lineWidth = 3; ctx.globalAlpha = (1 - k) * 0.8;
    ctx.beginPath(); ctx.arc(0, 0, 150, mAng, mAng + 1.2); ctx.stroke();
    arrowHead(ctx, Math.cos(mAng) * 150, Math.sin(mAng) * 150, mAng - Math.PI / 2, 14);
  }
  ctx.globalAlpha = clamp((p - 0.6) / 0.3);
  monoText(ctx, th, 'BIOLOGICAL AGE · PAUSED', 0, 320, 15, { align: 'center', color: th.ink, weight: 700, spacing: 5 });
  ctx.restore();
};
