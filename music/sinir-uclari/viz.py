"""
viz.py - precompute the web page's visual features from the render.

Writes web/sinir-uclari/viz.bin: 30 frames per second, 24 bytes per frame
  0-15  spectrum of the final mix, 16 log-spaced bands (50 Hz - 12 kHz)
  16    kick        17  bass        18  drums + perc   19  lead level
  20    lead pitch (0 = silent)     21  pads + choir   22  overall level
  23    keys (EP, bells)
Every channel is scaled to 0..255 against its own range, so the page gets
a balanced, already-musical picture without touching Web Audio.
"""
import os
import sys

import numpy as np
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from song import (LEAD_IN, LEVELS, MEL_BREAK, MEL_DROP, MEL_TAG, MEL_V1, MEL_V2,  # noqa: E402
                  OUT, SR, mel_events)

FPS = 30
HOP = SR // FPS
WEB = os.path.join(HERE, '..', '..', 'web', 'sinir-uclari')

LEAD_PARTS = [(MEL_V1, 9), (MEL_V2, 17), (MEL_DROP, 33), (MEL_DROP, 41),
              (MEL_BREAK, 49), (MEL_DROP, 57), (MEL_DROP, 65), (MEL_TAG, 73)]


def frame_rms(x, n_frames):
    m = x.mean(axis=0) if x.ndim == 2 else x
    m = np.pad(m, (0, n_frames * HOP - m.shape[0] + HOP))
    fr = m[:n_frames * HOP].reshape(n_frames, HOP)
    return np.sqrt(np.mean(fr ** 2, axis=1))


def scale(v_db, lo_pct=8, hi_pct=99.5, floor=-60.0):
    lo = max(np.percentile(v_db, lo_pct), floor)
    hi = np.percentile(v_db, hi_pct)
    return np.clip((v_db - lo) / max(hi - lo, 1e-6), 0, 1)


def to_db(x):
    return 20 * np.log10(np.maximum(x, 1e-7))


def main():
    y, _ = sf.read(os.path.join(OUT, 'sinir-uclari.wav'), always_2d=True)
    y = y.T
    n_frames = int(np.ceil(y.shape[1] / HOP))
    feats = np.zeros((n_frames, 24))

    # --- spectrum bands of the final mix
    mono = y.mean(axis=0)
    f, t, Z = signal.stft(mono, SR, nperseg=4096, noverlap=4096 - HOP, boundary='even')
    P = np.abs(Z) ** 2
    edges = np.geomspace(50, 12000, 17)
    bands = np.stack([P[(f >= a) & (f < b)].mean(axis=0) for a, b in zip(edges[:-1], edges[1:])])
    bands = bands[:, :n_frames]
    if bands.shape[1] < n_frames:
        bands = np.pad(bands, ((0, 0), (0, n_frames - bands.shape[1])))
    for k in range(16):
        feats[:, k] = scale(10 * np.log10(bands[k] + 1e-14), lo_pct=15, floor=-120)

    # --- stems (they start at bar 1; the wav has LEAD_IN of silence first)
    sd = os.path.join(OUT, 'stems')
    lead_in = int(LEAD_IN * SR)

    def stem(*names):
        acc = 0
        for n in names:
            p = os.path.join(sd, n + '.npy')
            if os.path.exists(p):
                acc = acc + np.load(p).astype(np.float64) * 10 ** (LEVELS.get(n, -12) / 20)
        return np.concatenate([np.zeros((2, lead_in)), acc], axis=1)

    for col, names in ((16, ('kick', 'buildkick')), (17, ('bass',)), (18, ('drums', 'perc')),
                       (19, ('lead',)), (21, ('pads', 'choir')), (23, ('keys',))):
        feats[:, col] = scale(to_db(frame_rms(stem(*names), n_frames)))
    feats[:, 22] = scale(to_db(frame_rms(y, n_frames)))

    # --- lead pitch straight from the score
    pitch = np.zeros(n_frames)
    for mel, bar in LEAD_PARTS:
        for (t0, dur, m, _v) in mel_events(mel, bar):
            a = int((t0 + LEAD_IN) * FPS)
            b = int((t0 + dur + LEAD_IN) * FPS)
            pitch[a:b] = np.clip((m - 60) / 20.0, 0.02, 1.0)
    feats[:, 20] = pitch * (feats[:, 19] > 0.05)

    data = np.round(feats * 255).astype(np.uint8)
    os.makedirs(WEB, exist_ok=True)
    path = os.path.join(WEB, 'viz.bin')
    data.tofile(path)
    print(f'{n_frames} frames -> {path} ({os.path.getsize(path) / 1024:.0f} KB)')


if __name__ == '__main__':
    main()
