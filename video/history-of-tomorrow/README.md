# A History of Tomorrow · 2026 → 2120

2026'da doğan bir çocuğun ömrü boyunca (2030, 2040 … 2120) dünyanın nasıl
değişeceğini ve insanlığın hangi buluşları yapacağını anlatan, İngilizce
metinli 2:36'lık video. Stil referansı:
[@IterIntellectus'un "western civilization" videosu](https://x.com/IterIntellectus/status/2103212539895017864)
(parşömen üzerinde teknik çizimler → altın parıltılı karanlık uzay, köşelerde HUD,
kinetik serif tipografi).

**Çıktı:** [`history-of-tomorrow.mp4`](history-of-tomorrow.mp4) — 1920×1080, 30 fps, H.264 + AAC.

## Bölümler

| On yıl | Bölüm | Ekrandaki başlıklar |
|---|---|---|
| 2030 | I · The Age of Minds | Machines learned to think · In every home, a robot · The steering wheel retired |
| 2040 | II · Starfire | We bottled a star · The first footprint on Mars · We beat cancer |
| 2050 | III · Balance | We bent the curve · We speak by thinking · The farms rose into the sky |
| 2060 | IV · Life | Genetic disease erased · We print hearts · We stopped aging |
| 2070 | V · The Moon | The first city on the Moon · We mine asteroids · To orbit by elevator |
| 2080 | VI · The Red Planet | One million Martians · The red planet turns green · Earth breathes again |
| 2090 | VII · The Sun | We wrapped the Sun · Earth to Mars in 30 days · Dark matter solved |
| 2100 | VIII · A New Century | Kardashev Type I · First sail to the stars |
| 2110 | IX · The Stars | Hundreds of cities in orbit · First photo of another world · We are not alone |
| 2120 | X · Human | "The child is 94. …And still young." → "The future isn't predicted. It's built." |

## Nasıl üretildi

Her şey koddan üretilir; hazır görsel ya da müzik kullanılmadı.

- `scenes.js` — senaryo, metinler ve zamanlama (80 BPM, 1 ölçü = 3 sn; kesmeler müziğin vuruşlarına denk gelir)
- `engine.js`, `ill_*.js` — kare kare çizim yapan canvas motoru ve illüstrasyonlar
- `render.cjs` — Chromium'u (Playwright) başsız çalıştırıp her kareyi yakalar
- `music.py` — numpy/scipy ile sentezlenen özgün müzik (org, arpej, yaylılar, koro, vuruşlar)
- `index.html` — tarayıcıda canlı önizleme (`build/music.wav` varsa müzikle)

```bash
./build.sh          # build/cues.json → build/music.wav → build/frames → history-of-tomorrow.mp4
```

Gereksinimler: Node + Playwright (Chromium), Python 3 + numpy/scipy/pyloudnorm, libx264'lü ffmpeg.

Fontlar (Cinzel, Cormorant Garamond, JetBrains Mono) SIL Open Font License ile `fonts/` altında;
kıta sınırları Natural Earth (kamu malı) verisidir.
