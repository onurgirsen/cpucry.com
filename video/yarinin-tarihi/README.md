# Yarının Tarihi · 2026 → 2120

2026'da doğan bir çocuğun ömrü boyunca (2030, 2040 … 2120) dünyanın nasıl
değişeceğini ve insanlığın hangi buluşları yapacağını anlatan 2:36'lık video.
Stil referansı: [@IterIntellectus'un "western civilization" videosu](https://x.com/IterIntellectus/status/2103212539895017864)
(parşömen üzerinde teknik çizimler → altın parıltılı karanlık uzay, köşelerde HUD,
kinetik serif tipografi).

**Çıktı:** [`yarinin-tarihi.mp4`](yarinin-tarihi.mp4) — 1920×1080, 30 fps, H.264 + AAC.

## Bölümler

| On yıl | Bölüm | Buluşlar |
|---|---|---|
| 2030 | I · Zekâ Çağı | Yapay genel zekâ, insansı robotlar, sürücüsüz ulaşım |
| 2040 | II · Yıldız Ateşi | Füzyon enerjisi, Mars'a ilk insan, kişiye özel kanser aşıları |
| 2050 | III · Denge | Net sıfır / karbon eğrisi, beyin–bilgisayar arayüzü, dikey tarım |
| 2060 | IV · Yaşam | Gen düzenleme, biyo-yazıcıyla organ, yaşlanmanın durdurulması |
| 2070 | V · Ay | Ay'da şehir, asteroit madenciliği, uzay asansörü |
| 2080 | VI · Kızıl Gezegen | Mars'ta bir milyon insan, teraforming, Dünya'nın iyileşmesi |
| 2090 | VII · Güneş | Dyson sürüsü, Mars'a 30 günde, karanlık madde |
| 2100 | VIII · Yeni Yüzyıl | Kardaşev Tip I, yıldızlara ilk ışık yelkeni |
| 2110 | IX · Yıldızlar | O'Neill silindirleri, Proxima b'nin fotoğrafı, biyoimza |
| 2120 | X · İnsan | "O, 94 yaşında… ve hâlâ genç." |

## Nasıl üretildi

Her şey koddan üretilir; hazır görsel ya da müzik kullanılmadı.

- `scenes.js` — senaryo ve zamanlama (80 BPM, 1 ölçü = 3 sn; kesmeler müziğin vuruşlarına denk gelir)
- `engine.js`, `ill_*.js` — kare kare çizim yapan canvas motoru ve illüstrasyonlar
- `render.cjs` — Chromium'u (Playwright) başsız çalıştırıp her kareyi yakalar
- `music.py` — numpy/scipy ile sentezlenen özgün müzik (org, arpej, yaylılar, koro, vuruşlar)
- `index.html` — tarayıcıda canlı önizleme (`build/music.wav` varsa müzikle)

```bash
./build.sh          # build/cues.json → build/music.wav → build/frames → yarinin-tarihi.mp4
```

Gereksinimler: Node + Playwright (Chromium), Python 3 + numpy/scipy/pyloudnorm, libx264'lü ffmpeg.

Fontlar (Cinzel, Cormorant Garamond, JetBrains Mono) SIL Open Font License ile `fonts/` altında;
kıta sınırları Natural Earth (kamu malı) verisidir.
