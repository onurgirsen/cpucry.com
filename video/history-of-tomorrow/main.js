'use strict';
/* Timeline layout + per-frame compositor. */
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
const TAIL = 3.5;              // seconds of black after the last scene (music tail)
let TOTAL = 0;

function layout() {
  let t = 0;
  for (const s of SCENES) { s.start = t; s.dur = s.bars * BAR; t += s.dur; }
  TOTAL = t + TAIL;
}

function sceneAt(t) {
  for (let i = SCENES.length - 1; i >= 0; i--) if (t >= SCENES[i].start) return i;
  return 0;
}

function hudInfo(S, sc) {
  const [y0, y1] = S.years;
  const yf = S.card ? lerp(y0, y1, E.outExpo(ramp(sc.t, 0.02, 0.75))) : lerp(y0, y1, sc.p);
  const year = Math.floor(yf + 1e-6);
  const alpha = typeof S.hud === 'function' ? S.hud(sc) : (S.hud ?? 1);
  return { chapter: S.chapter, year, yearF: yf, age: year - 2026, alpha };
}

function renderFrame(t) {
  const last = SCENES[SCENES.length - 1];
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'; ctx.filter = 'none';
  ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.letterSpacing = '0px';
  if (t >= last.start + last.dur) { ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H); return; }
  const i = sceneAt(t), S = SCENES[i], th = THEMES[S.theme];
  const sc = { t: t - S.start, dur: S.dur, p: clamp((t - S.start) / S.dur), T: t, frame: Math.round(t * FPS), S, i };
  drawBackground(ctx, th, t, sc);
  if (S.bg) { ctx.save(); S.bg(ctx, th, sc); ctx.restore(); }
  ctx.save();
  const z = 1 + (S.zoom ?? 0.035) * sc.p;
  const [fx, fy] = S.focus || [W * 0.66, H * 0.5];
  ctx.translate(fx, fy); ctx.scale(z, z); ctx.translate(-fx, -fy);
  if (S.draw) S.draw(ctx, th, sc);
  ctx.restore();
  const bl = S.bloom ?? (th.dark ? 0.85 : 0);
  if (bl > 0) bloom(ctx, canvas, bl);
  if (S.text) {
    ctx.save();
    const tz = 1 + 0.012 * sc.p;
    ctx.translate(W / 2, H / 2); ctx.scale(tz, tz); ctx.translate(-W / 2, -H / 2);
    for (const spec of [].concat(typeof S.text === 'function' ? S.text(sc) : S.text)) headline(ctx, th, sc, spec);
    ctx.restore();
  }
  if (S.over) { ctx.save(); S.over(ctx, th, sc); ctx.restore(); }
  vignette(ctx, th);
  drawHUD(ctx, th, hudInfo(S, sc));
  grain(ctx, th, sc.i);
  // transitions
  if (S.trans === 'flash') {
    const a = Math.pow(1 - clamp(sc.t / 0.5), 2.2);
    if (a > 0) { ctx.fillStyle = th.dark ? `rgba(255,236,205,${a * 0.78})` : `rgba(255,251,240,${a * 0.92})`; ctx.fillRect(0, 0, W, H); }
  } else if (S.trans === 'black') {
    const a = 1 - E.out(clamp(sc.t / (S.transDur ?? 0.4)));
    if (a > 0) { ctx.fillStyle = `rgba(0,0,0,${a})`; ctx.fillRect(0, 0, W, H); }
  }
  if (S.outBlack) {
    const a = E.inOut(clamp((sc.t - (S.dur - S.outBlack)) / S.outBlack));
    if (a > 0) { ctx.fillStyle = `rgba(0,0,0,${a})`; ctx.fillRect(0, 0, W, H); }
  }
  if (S.outWhite) {
    const a = E.in(clamp((sc.t - (S.dur - S.outWhite)) / S.outWhite));
    if (a > 0) { ctx.fillStyle = `rgba(255,248,232,${a})`; ctx.fillRect(0, 0, W, H); }
  }
}

async function boot() {
  const faces = ['400 40px Cinzel', '700 40px Cinzel', '900 40px Cinzel', 'italic 600 40px "Cormorant Garamond"',
    '500 20px "JetBrains Mono"', '600 20px "JetBrains Mono"', '700 20px "JetBrains Mono"'];
  await Promise.all(faces.map(f => document.fonts.load(f, 'AZaz0123456789·…→')));
  await document.fonts.ready;
  buildTextures();
  layout();
  if (typeof prepare === 'function') await prepare();
  window.TOTAL = TOTAL;
  window.SCENE_LIST = SCENES.map(s => ({ id: s.id, start: s.start, dur: s.dur, bars: s.bars, cue: s.cue || null, card: !!s.card, theme: s.theme }));
  window.renderFrame = renderFrame;
  window.READY = true;
  const q = new URLSearchParams(location.search);
  if (q.has('t')) renderFrame(parseFloat(q.get('t')));
  else if (!q.has('capture')) {       // live preview
    const audio = document.getElementById('music');
    let t0 = performance.now();
    if (audio) { audio.currentTime = 0; audio.play().catch(() => {}); }
    const loop = () => {
      const t = audio && !audio.paused ? audio.currentTime : (performance.now() - t0) / 1000;
      renderFrame(t % TOTAL);
      requestAnimationFrame(loop);
    };
    loop();
  }
}
boot();
