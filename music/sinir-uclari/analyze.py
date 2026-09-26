"""analyze.py - objective checks on a render (levels, balance, spectrum)."""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
SR = 44100


def lufs(meter, x):
    try:
        return meter.integrated_loudness(x.T)
    except Exception:
        return float('nan')


def main(tag=''):
    y, sr = sf.read(os.path.join(OUT, 'sinir-uclari.wav'), always_2d=True)
    y = y.T
    meta = json.load(open(os.path.join(OUT, 'sections.json')))
    meter = pyln.Meter(SR)
    up = signal.resample_poly(y, 4, 1, axis=-1)
    print(f'length {y.shape[1] / SR:.1f}s  sample peak {20 * np.log10(np.abs(y).max()):.2f} dBFS'
          f'  true peak {20 * np.log10(np.abs(up).max()):.2f} dBTP  LUFS-I {lufs(meter, y):.2f}')
    corr = np.corrcoef(y[0], y[1])[0, 1]
    side = (y[0] - y[1]) / 2
    mid = (y[0] + y[1]) / 2
    print(f'L/R correlation {corr:.3f}   side/mid rms {20 * np.log10(np.std(side) / np.std(mid)):.1f} dB')

    sys.path.insert(0, HERE)
    from song import LEVELS, LEAD_IN
    sd = os.path.join(OUT, 'stems')
    stems = {f[:-4]: np.load(os.path.join(sd, f)) * 10 ** (LEVELS.get(f[:-4], -12) / 20)
             for f in os.listdir(sd) if f.endswith('.npy')}
    names = sorted(stems)
    print('\nsection            LUFS   peak   ' + ' '.join(f'{n[:6]:>6s}' for n in names))
    for s in meta['sections']:
        a, b = int(s['start'] * SR), int(s['end'] * SR)
        seg = y[:, a:b]
        row = f"{s['name']:<16s} {lufs(meter, seg):6.1f} {20 * np.log10(np.abs(seg).max() + 1e-12):6.1f}   "
        cells = []
        sa, sb = a - int(LEAD_IN * SR), b - int(LEAD_IN * SR)
        for n in names:
            v = stems[n][:, sa:sb].astype(np.float64)
            l = lufs(meter, v) if np.abs(v).max() > 1e-5 else float('nan')
            cells.append(f'{l:6.1f}' if np.isfinite(l) else '     -')
        print(row + ' '.join(cells))

    # spectrogram
    mono = y.mean(axis=0)
    f, t, Z = signal.stft(mono, SR, nperseg=4096, noverlap=3072)
    P = 20 * np.log10(np.abs(Z) + 1e-9)
    fig, ax = plt.subplots(3, 1, figsize=(18, 13), gridspec_kw={'height_ratios': [3, 1, 1.4]})
    ax[0].pcolormesh(t, f, P, vmin=-100, vmax=-10, shading='auto', cmap='magma')
    ax[0].set_yscale('symlog', linthresh=200)
    ax[0].set_ylim(25, 18000)
    for s in meta['sections']:
        ax[0].axvline(s['start'], color='cyan', lw=0.8)
        ax[0].text(s['start'] + 0.5, 12000, s['name'], color='cyan', fontsize=9)
    ax[0].set_title('spectrogram (mono)')
    # short-term loudness curve
    win, hop = 3 * SR, SR // 2
    st = []
    for a in range(0, y.shape[1] - win, hop):
        st.append(lufs(meter, y[:, a:a + win]))
    ax[1].plot(np.arange(len(st)) * hop / SR + 1.5, st)
    ax[1].set_ylim(-40, -5)
    ax[1].grid(alpha=0.3)
    ax[1].set_title('short-term loudness (LUFS, 3 s)')
    for s in meta['sections']:
        ax[1].axvline(s['start'], color='gray', lw=0.6)
    # average spectrum per section (1/6 octave smoothed)
    for s in meta['sections']:
        a, b = int(s['start'] * SR), int(s['end'] * SR)
        ff, pxx = signal.welch(mono[a:b], SR, nperseg=8192)
        cen = np.geomspace(25, 18000, 120)
        sm = [10 * np.log10(np.mean(pxx[(ff > c / 2 ** (1 / 12)) & (ff < c * 2 ** (1 / 12))]) + 1e-20)
              for c in cen]
        ax[2].semilogx(cen, sm, label=s['name'])
    ax[2].legend(fontsize=8, ncol=4)
    ax[2].grid(alpha=0.3, which='both')
    ax[2].set_title('average spectrum per section (dB)')
    plt.tight_layout()
    path = os.path.join(OUT, f'analysis{tag}.png')
    plt.savefig(path, dpi=70)
    print('\n' + path)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '')
