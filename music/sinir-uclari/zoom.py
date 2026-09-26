"""zoom.py - close-up plots of key moments of the render."""
import os, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np, soundfile as sf
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from song import T as T0, LEVELS, SR, OUT, LEAD_IN
def T(b, bt=0.0): return T0(b, bt) + LEAD_IN

y, _ = sf.read(os.path.join(OUT, 'sinir-uclari.wav'), always_2d=True); y = y.T
sd = os.path.join(OUT, 'stems')
def stem(n):
    v = np.load(os.path.join(sd, n + '.npy')).astype(float) * 10 ** (LEVELS.get(n, -12) / 20)
    return np.concatenate([np.zeros((2, int(LEAD_IN * SR))), v], axis=1)

fig, ax = plt.subplots(3, 2, figsize=(18, 12))
def spec(a, t0, t1, title, x=None):
    x = y.mean(0) if x is None else x
    seg = x[int(t0 * SR):int(t1 * SR)]
    f, t, Z = signal.stft(seg, SR, nperseg=2048, noverlap=1792)
    a.pcolormesh(t + t0, f, 20 * np.log10(np.abs(Z) + 1e-9), vmin=-110, vmax=-20, shading='auto', cmap='magma')
    a.set_yscale('symlog', linthresh=200); a.set_ylim(30, 18000); a.set_title(title)
spec(ax[0, 0], T(32), T(33) + 1.5, 'tape stop -> drop 1')
spec(ax[0, 1], T(56), T(57) + 1.5, 'breath -> drop 2')
# pumping: rms envelope of pads & bass in drop 1 bars 33-34
t0, t1 = T(35), T(37)
for n in ('pads', 'bass', 'kick', 'lead'):
    s_ = stem(n)[:, int(t0 * SR):int(t1 * SR)].mean(0)
    env = np.sqrt(signal.lfilter([1 / 441] * 441, [1], s_ ** 2))
    ax[1, 0].plot(np.arange(len(env)) / SR + t0, 20 * np.log10(env + 1e-9), label=n)
ax[1, 0].set_ylim(-60, 0); ax[1, 0].legend(); ax[1, 0].set_title('drop envelopes (10 ms rms, dB)'); ax[1, 0].grid(alpha=.3)
# lead: spectrum of a held note (drop 1, bar 39 Bb4 held from beat 1.3 to 3.8)
L = stem('lead').mean(0)
a, b = int(T(39, 1.6) * SR), int(T(39, 3.8) * SR)
f, p = signal.welch(L[a:b], SR, nperseg=8192)
ax[1, 1].semilogx(f, 10 * np.log10(p + 1e-20)); ax[1, 1].set_xlim(80, 16000); ax[1, 1].grid(alpha=.3, which='both')
ax[1, 1].set_title('lead spectrum, held Bb4 (vowel a)')
for fr in (730, 1090, 2440, 3400): ax[1, 1].axvline(fr, color='r', alpha=.4)
spec(ax[2, 0], T(33), T(37), 'drop 1 first 4 bars')
spec(ax[2, 1], T(39), T(41), 'lead alone: bars 39-40 (Bb4 -> A4, the light)', x=L)
plt.tight_layout(); plt.savefig(os.path.join(OUT, 'zoom.png'), dpi=65); print('ok')
