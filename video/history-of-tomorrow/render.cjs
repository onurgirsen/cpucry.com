#!/usr/bin/env node
/* Headless frame capture for index.html.
   node render.cjs --frames            render every frame to build/frames (parallel)
   node render.cjs --frames 120:240    render a frame range
   node render.cjs --stills 1.5,7,33   render single moments to build/stills/*.png
   node render.cjs --cues              write build/cues.json (scene timing for the soundtrack) */
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const ROOT = __dirname;
const BUILD = path.join(ROOT, 'build');
const FPS = 30;
const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i < 0 ? null : (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true); };
const WORKERS = parseInt(opt('--workers') || '4', 10);

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.ttf': 'font/ttf', '.wav': 'audio/wav', '.json': 'application/json' };
function serve() {
  return new Promise(resolve => {
    const srv = http.createServer((req, res) => {
      const u = decodeURIComponent(req.url.split('?')[0]);
      const f = path.join(ROOT, u === '/' ? 'index.html' : u);
      if (!f.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }
      fs.readFile(f, (err, data) => {
        if (err) { res.writeHead(404); res.end(); return; }
        res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
        res.end(data);
      });
    });
    srv.listen(0, '127.0.0.1', () => resolve(srv));
  });
}

async function openPage(url) {
  const browser = await chromium.launch({ args: ['--disable-gpu', '--disable-dev-shm-usage', '--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.error('[page]', m.text()); });
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  await page.goto(url);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 120000 });
  return { browser, page };
}

async function main() {
  const srv = await serve();
  const url = `http://127.0.0.1:${srv.address().port}/index.html?capture=1`;
  fs.mkdirSync(BUILD, { recursive: true });

  if (opt('--cues')) {
    const { browser, page } = await openPage(url);
    const info = await page.evaluate(() => ({ total: window.TOTAL, fps: 30, bpm: BPM, scenes: window.SCENE_LIST }));
    fs.writeFileSync(path.join(BUILD, 'cues.json'), JSON.stringify(info, null, 1));
    console.log('scenes:', info.scenes.length, 'total:', info.total.toFixed(2), 's');
    await browser.close();
  }

  const stills = opt('--stills');
  if (stills) {
    const dir = path.join(BUILD, 'stills'); fs.mkdirSync(dir, { recursive: true });
    const { browser, page } = await openPage(url);
    for (const s of String(stills).split(',')) {
      const t = parseFloat(s);
      const t0 = Date.now();
      const b64 = await page.evaluate(tt => { renderFrame(tt); return document.getElementById('c').toDataURL('image/png'); }, t);
      const f = path.join(dir, `t_${t.toFixed(2).padStart(7, '0')}.png`);
      fs.writeFileSync(f, Buffer.from(b64.split(',')[1], 'base64'));
      console.log(f, `${Date.now() - t0}ms`);
    }
    await browser.close();
  }

  const frames = opt('--frames');
  if (frames) {
    const dir = path.join(BUILD, 'frames'); fs.mkdirSync(dir, { recursive: true });
    const probe = await openPage(url);
    const total = await probe.page.evaluate(() => window.TOTAL);
    await probe.browser.close();
    const N = Math.ceil(total * FPS);
    let a = 0, b = N;
    if (typeof frames === 'string') { const [x, y] = frames.split(':').map(Number); a = x; b = Math.min(N, y); }
    console.log(`rendering frames ${a}..${b - 1} of ${N} with ${WORKERS} workers`);
    let next = a, done = 0; const t0 = Date.now();
    const worker = async () => {
      const { browser, page } = await openPage(url);
      while (true) {
        const f = next++;
        if (f >= b) break;
        const b64 = await page.evaluate(tt => { renderFrame(tt); return document.getElementById('c').toDataURL('image/jpeg', 0.95); }, f / FPS);
        fs.writeFileSync(path.join(dir, `f_${String(f).padStart(6, '0')}.jpg`), Buffer.from(b64.split(',')[1], 'base64'));
        done++;
        if (done % 150 === 0) {
          const el = (Date.now() - t0) / 1000;
          console.log(`${done}/${b - a} frames  ${(done / el).toFixed(1)} fps  eta ${((b - a - done) / (done / el)).toFixed(0)}s`);
        }
      }
      await browser.close();
    };
    await Promise.all(Array.from({ length: WORKERS }, worker));
    console.log(`done in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  srv.close();
}
main().catch(e => { console.error(e); process.exit(1); });
