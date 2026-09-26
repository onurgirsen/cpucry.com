# Sinir Uçları

An electronic track composed and synthesized entirely in code: no samples,
no presets. It plays at [`/sinir-uclari/`](../../web/sinir-uclari/) on the site.

F minor, 108 BPM, 3:15. Heartbeat intro → chromatic lament verse → phonk
panic (cowbell in C Hicaz over a dominant pedal, tape-stop blackout) →
French-house drop that resolves deceptively to D♭ and reaches F major →
breakdown and a held breath → the drop again with a choir → half-time coda →
the opening music-box motif, now in major.

## Regenerate

    pip install numpy scipy numba soundfile pyloudnorm lameenc matplotlib
    python3 song.py        # full render (~2 min): out/sinir-uclari.{wav,mp3} + stems
    python3 song.py mix    # re-mix / re-master from the saved stems (seconds)
    python3 viz.py         # visual features for the web page -> web/sinir-uclari/viz.bin
    cp out/sinir-uclari.mp3 ../../web/sinir-uclari/

## Files

- `synth.py`: DSP. PolyBLEP oscillators, TPT state-variable and ladder
  filters, convolution reverb with a synthetic IR, ping-pong delay, chorus,
  tape wow/flutter, compressor, true-peak look-ahead limiter, tape stop.
- `instruments.py`: drums, 808, bass, supersaw, FM electric piano,
  music box, talk-box style voice (formant filter bank), choir, FX.
- `song.py`: score, arrangement, mix and master.
- `analyze.py`, `zoom.py`: loudness/balance tables and spectrogram checks.
- `viz.py`: precomputed visual features for the page's visualizer.
