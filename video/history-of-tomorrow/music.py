#!/usr/bin/env python3
"""Original procedural soundtrack for "A History of Tomorrow".

80 BPM, 4/4 (1 bar = 3 s), A minor → A major.  Every event is placed on the
same bar grid as the visuals (see scenes.js), so cuts, year cards and the
finale land on the music.  Output: build/music.wav (48 kHz, stereo, 16-bit).
"""
import json
import os
import sys

import numpy as np
from scipy import signal

SR = 48000
BPM = 80
BEAT = 60 / BPM
BAR = 4 * BEAT
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")

cues = json.load(open(os.path.join(BUILD, "cues.json")))
TOTAL = cues["total"] + 2.0
N = int(TOTAL * SR)
rng = np.random.default_rng(2120)

dry = np.zeros((2, N))
wet = np.zeros((2, N))          # reverb send


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def place(sig, t0, pan=0.0, gain=1.0, send=0.3):
    """Mix a mono (or stereo) signal at time t0 with equal-power pan."""
    i0 = int(round(t0 * SR))
    if i0 >= N:
        return
    if sig.ndim == 1:
        a = (pan + 1) * np.pi / 4
        st = np.vstack([sig * np.cos(a), sig * np.sin(a)])
    else:
        st = sig
    st = st * gain
    n = min(st.shape[1], N - i0)
    if i0 < 0:
        st = st[:, -i0:]
        n = min(st.shape[1], N)
        i0 = 0
    dry[:, i0:i0 + n] += st[:, :n]
    wet[:, i0:i0 + n] += st[:, :n] * send


def env_adsr(n, a, d, s, r_start, r):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), 1.0)
    e = np.where((t >= a) & (t < a + d), 1 - (1 - s) * (t - a) / max(d, 1e-4), e)
    e = np.where((t >= a + d), s, e)
    rel = np.clip(1 - (t - r_start) / max(r, 1e-4), 0, 1)
    return e * np.where(t >= r_start, rel, 1.0)


# ---------------------------------------------------------------- instruments
def organ(m, dur, amp=0.1, attack=0.12, release=0.9, bright=1.0, vib=0.0, sub=0.45):
    f = mtof(m)
    n = int((dur + release) * SR)
    t = np.arange(n) / SR
    tw = t + vib * 0.0045 * np.sin(2 * np.pi * 5.2 * t) / (2 * np.pi * 5.2)
    bars = [(0.5, sub), (1, 1.0), (2, 0.6 * bright), (3, 0.32 * bright), (4, 0.26 * bright), (6, 0.12 * bright), (8, 0.08 * bright)]
    sig = np.zeros(n)
    for h, a in bars:
        if f * h > 15000:
            continue
        for det, g in ((1.0, 1.0), (1.0017, 0.55)):
            sig += a * g * np.sin(2 * np.pi * f * h * det * tw + h * 1.3)
    e = env_adsr(n, attack, 0.3, 0.85, dur, release)
    trem = 1 + 0.04 * np.sin(2 * np.pi * 5.6 * t)
    return sig * e * trem * amp


def pluck(m, amp=0.1, decay=1.0, bright=1.0):
    f = mtof(m)
    n = int(1.6 * decay * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for k in range(1, 12):
        if f * k > 14000:
            break
        sig += (1 / k ** 1.25) * np.sin(2 * np.pi * f * k * t + k) * np.exp(-t * (2.2 + 1.6 * k / bright) / decay)
    att = np.clip(t / 0.003, 0, 1)
    return sig * att * amp


def musicbox(m, amp=0.1):
    f = mtof(m)
    n = int(2.6 * SR)
    t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) * np.exp(-t * 1.6)
           + 0.35 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 3.0)
           + 0.16 * np.sin(2 * np.pi * f * 3.0 * t) * np.exp(-t * 5.0)
           + 0.10 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 9.0))
    att = np.clip(t / 0.002, 0, 1)
    return sig * att * amp


def supersaw(m, dur, amp=0.1, attack=0.9, release=1.4, cutoff=2600, voices=5, spread=0.012):
    f = mtof(m)
    n = int((dur + release) * SR)
    t = np.arange(n) / SR
    out = np.zeros((2, n))
    for v in range(voices):
        d = 1 + spread * (v - (voices - 1) / 2) / ((voices - 1) / 2)
        ph = (f * d * t + rng.random()) % 1.0
        saw = 2 * ph - 1
        pan = -0.8 + 1.6 * v / (voices - 1)
        a = (pan + 1) * np.pi / 4
        out[0] += saw * np.cos(a)
        out[1] += saw * np.sin(a)
    sos = signal.butter(2, cutoff, fs=SR, output="sos")
    out = signal.sosfilt(sos, out, axis=1)
    e = env_adsr(n, attack, 0.5, 0.9, dur, release)
    return out * e * amp / voices


def bass(m, dur, amp=0.2, release=0.6):
    f = mtof(m)
    n = int((dur + release) * SR)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t)
    e = env_adsr(n, 0.04, 0.4, 0.8, dur, release)
    return np.tanh(1.4 * sig * e) * amp


def choir(m, dur, amp=0.08, attack=1.0, release=1.6, vowel=(750, 1150, 2800)):
    f = mtof(m)
    n = int((dur + release) * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for v in range(4):
        vib = 1 + 0.006 * np.sin(2 * np.pi * (4.8 + v * 0.3) * t + v)
        ph = np.cumsum(f * (1 + 0.004 * (v - 1.5)) * vib) / SR
        src = 2 * (ph % 1.0) - 1
        voice = np.zeros(n)
        for fc, bw, g in zip(vowel, (90, 110, 160), (1.0, 0.55, 0.25)):
            b, a = signal.iirpeak(fc, fc / bw, fs=SR)
            voice += g * signal.lfilter(b, a, src)
        out += voice
    e = env_adsr(n, attack, 0.5, 0.9, dur, release)
    return out * e * amp / 4


def noise(n):
    return rng.standard_normal(n)


def boom(amp=0.8, size=1.0):
    n = int(3.5 * SR)
    t = np.arange(n) / SR
    fr = 30 + 62 * np.exp(-t * 3.2 / size)
    sub = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 1.1 / size)
    nz = noise(n)
    body = signal.sosfilt(signal.butter(2, [60, 500], "bandpass", fs=SR, output="sos"), nz) * np.exp(-t * 5)
    click = signal.sosfilt(signal.butter(2, 3000, fs=SR, output="sos"), nz) * np.exp(-t * 60)
    return np.tanh(1.6 * (sub + 0.5 * body + 0.35 * click)) * amp


def riser(dur, amp=0.25):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = t / dur
    nz = signal.sosfilt(signal.butter(2, 1500, "highpass", fs=SR, output="sos"), noise(n))
    sweep = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (2.6 * x)) / SR)
    return (nz * 0.8 + sweep * 0.35) * (x ** 2.2) * amp


def whoosh(amp=0.08, dur=0.9):
    n = int(dur * SR)
    t = np.arange(n) / SR
    nz = signal.sosfilt(signal.butter(2, [300, 3000], "bandpass", fs=SR, output="sos"), noise(n))
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return nz * e * amp


def tick(amp=0.05, hi=True):
    n = int(0.08 * SR)
    t = np.arange(n) / SR
    f = 3200 if hi else 2100
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 90) + 0.6 * signal.sosfilt(signal.butter(2, 2500, "highpass", fs=SR, output="sos"), noise(n)) * np.exp(-t * 300)
    return s * amp


def tom(amp=0.3, f0=110):
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    fr = f0 * (0.62 + 0.38 * np.exp(-t * 18))
    s = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 5.5)
    s += 0.25 * signal.sosfilt(signal.butter(2, [100, 1200], "bandpass", fs=SR, output="sos"), noise(n)) * np.exp(-t * 25)
    return np.tanh(1.3 * s) * amp


def kick(amp=0.35):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    fr = 45 + 110 * np.exp(-t * 30)
    return np.tanh(2.0 * np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 7)) * amp


def hat(amp=0.03, open_=False):
    n = int((0.35 if open_ else 0.09) * SR)
    t = np.arange(n) / SR
    nz = signal.sosfilt(signal.butter(2, 7000, "highpass", fs=SR, output="sos"), noise(n))
    return nz * np.exp(-t * (12 if open_ else 60)) * amp


def crash(amp=0.12, dur=3.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    nz = signal.sosfilt(signal.butter(2, 3500, "highpass", fs=SR, output="sos"), noise(n))
    return nz * np.exp(-t * 1.6) * np.clip(t / 0.004, 0, 1) * amp


def heartbeat(amp=0.5):
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    def thump(t0, a):
        tt = np.clip(t - t0, 0, None)
        return a * np.sin(2 * np.pi * (48 + 30 * np.exp(-tt * 25)) * tt) * np.exp(-tt * 16) * (t >= t0)
    return np.tanh(2 * (thump(0.0, 1.0) + thump(0.2, 0.6))) * amp


def reverse_cymbal(dur=1.5, amp=0.18):
    n = int(dur * SR)
    t = np.arange(n) / SR
    nz = signal.sosfilt(signal.butter(2, 4000, "highpass", fs=SR, output="sos"), noise(n))
    return nz * (t / dur) ** 3 * amp


# ---------------------------------------------------------------- score
CH = {  # bass note, pad voicing, arp tones
    "Am": (45, [57, 60, 64, 71], [57, 60, 64, 69, 72, 76]),
    "F": (41, [53, 57, 60, 64], [53, 57, 60, 65, 69, 72]),
    "C": (48, [55, 60, 64, 74], [55, 60, 64, 67, 72, 76]),
    "G": (43, [55, 59, 62, 69], [55, 59, 62, 67, 71, 74]),
    "E": (40, [52, 56, 59, 64], [52, 56, 59, 64, 68, 71]),
    "Esus": (40, [52, 57, 59, 64], [52, 57, 59, 64, 69, 71]),
    "A": (45, [57, 61, 64, 69], [57, 61, 64, 69, 73, 76]),
}
LOOP = ["Am", "F", "C", "G"]
chords = ["Am", "Am", "Am", "F", "C", "G"]                 # bars 0-5: intro, title, birth
for d in range(7):                                       # 2030–2090
    chords += LOOP
chords += ["Am", "F", "C", "G"]                          # 2100
chords += ["Am", "F", "C", "E"]                          # 2110
chords += ["Am", "F", "C", "G", "Esus", "A", "A", "A", "A"]  # 2120 … end
NB = len(chords)
assert NB == 51, NB

# intensity per bar (0..1)
inten = np.zeros(NB)
inten[0:2] = 0.22; inten[2:4] = 0.42; inten[4:6] = 0.3
for d in range(7):
    inten[6 + 4 * d: 10 + 4 * d] = 0.4 + d * 0.075
inten[34:38] = 0.95; inten[38:42] = 1.0
inten[42] = 0.14; inten[43] = 0.12; inten[44] = 0.4; inten[45] = 0.62; inten[46] = 0.3
inten[47:49] = 1.0; inten[49:51] = 0.4

ARP = [0, 1, 2, 3, 4, 3, 2, 1, 0, 1, 2, 3, 4, 5, 4, 3]
CARDS = [6, 10, 14, 18, 22, 26, 30, 34, 38, 42]
MEL_A = [[(76, 4)], [(77, 2), (81, 2)], [(79, 4)], [(74, 2), (71, 2)]]
MEL_B = [[(84, 2), (83, 2)], [(81, 4)], [(79, 2), (76, 2)], [(74, 4)]]
MEL_E = [[(76, 4)], [(77, 2), (81, 2)], [(79, 4)], [(80, 2), (83, 2)]]


def T(bar, beat=0.0):
    return bar * BAR + beat * BEAT


for b, name in enumerate(chords):
    root, pad, arp = CH[name]
    I = inten[b]
    t0 = T(b)
    # organ pad (always)
    for k, m in enumerate(pad):
        place(organ(m, BAR, amp=0.022 + 0.05 * I, attack=0.25 if b else 1.8, bright=0.5 + 0.7 * I, sub=0.3), t0, pan=(-0.5 + k / 3), gain=1, send=0.55)
    # organ drone on the root (no sub-octave rumble)
    place(organ(root, BAR, amp=0.03 + 0.04 * I, attack=0.3 if b else 2.5, bright=0.35, sub=0.0), t0, pan=0, send=0.4)
    if b in (42, 43, 46):
        pass
    # bass
    if 6 <= b <= 41 or 44 <= b <= 48:
        place(bass(root - 12, BAR * 0.98, amp=0.05 + 0.1 * I), t0, pan=0, send=0.05)
    # strings
    if 10 <= b <= 41 or 44 <= b <= 50:
        for k, m in enumerate(pad):
            place(supersaw(m, BAR, amp=0.025 + 0.1 * I, cutoff=1800 + 5200 * I), t0, gain=1, send=0.45)
    # arpeggio (16ths)
    if 4 <= b <= 41 or b in (44, 45, 47, 48):
        oct_up = 12 if b >= 34 else 0
        for s in range(16):
            if b in (4, 5) and s % 2:          # birth: gentler 8ths
                continue
            m = arp[ARP[s]] + oct_up
            acc = 1.0 if s % 4 == 0 else 0.72
            place(pluck(m, amp=(0.02 + 0.065 * I) * acc, decay=0.7 + 0.5 * I, bright=0.8 + I), t0 + s * BEAT / 4,
                  pan=(-0.45 if s % 2 else 0.45), send=0.35)
            if b >= 26 and s % 2 == 0:       # sparkle an octave up in the late decades
                place(pluck(m + 12, amp=0.018 * I * acc, decay=0.6, bright=2.0), t0 + s * BEAT / 4, pan=(0.6 if s % 4 else -0.6), send=0.5)
    # melody (lead organ) from 2060
    if 18 <= b <= 41:
        blk = (b - 6) // 4
        mel = MEL_E if b >= 38 else (MEL_B if blk % 2 else MEL_A)
        beat = 0
        for m, L in mel[(b - 6) % 4]:
            place(organ(m, L * BEAT * 0.98, amp=0.03 + 0.03 * I, attack=0.08, release=0.7, bright=1.1, vib=1.0), t0 + beat * BEAT, pan=0.1, send=0.6)
            beat += L
    # choir at the climax + finale
    if 34 <= b <= 41 or 47 <= b <= 50:
        for m in pad[:3]:
            place(choir(m + 12 if m < 60 else m, BAR, amp=0.05 + 0.03 * I), t0, pan=0, send=0.6)
    # ticking clock (quarter notes) from birth to 2120
    if 4 <= b <= 46:
        for q in range(4):
            place(tick(amp=0.02 + 0.025 * min(1, I), hi=q % 2 == 0), t0 + q * BEAT, pan=0.25 if q % 2 else -0.25, send=0.08)
    # drums
    if 22 <= b <= 41 or b in (47, 48):
        for bt in (0, 1.5, 2, 3):
            place(tom(amp=0.12 + 0.12 * I, f0=95 if bt == 0 else 120), t0 + bt * BEAT, pan=-0.1 if bt % 1 else 0.1, send=0.25)
    if 30 <= b <= 41 or b in (47, 48):
        for bt in range(4):
            place(kick(amp=0.18 + 0.12 * I), t0 + bt * BEAT, send=0.05)
    if 26 <= b <= 41 or b in (47, 48):
        for e8 in range(8):
            place(hat(amp=(0.012 + 0.02 * I) * (1.0 if e8 % 2 else 0.6), open_=(e8 % 4 == 3)), t0 + e8 * BEAT / 2, pan=0.35, send=0.12)

# ---------------------------------------------------------------- hits & transitions
for b in CARDS:
    if b >= 22 and b != 42:
        place(crash(amp=0.05 + 0.05 * inten[b]), T(b), pan=0.2, send=0.4)
    size = 1.3 if b in (34, 42) else 1.0
    place(boom(amp=0.6 if b != 42 else 0.5, size=size), T(b), send=0.35)
    place(reverse_cymbal(1.5, amp=0.12 + 0.04 * inten[b - 1]), T(b) - 1.5, pan=0, send=0.3)
    place(riser(1.5, amp=0.08), T(b) - 1.5, pan=0, send=0.3)
# title + birth + final + end
place(boom(amp=0.65, size=1.4), T(2), send=0.5)
place(reverse_cymbal(2.2, amp=0.15), T(2) - 2.2, send=0.4)
place(boom(amp=0.35, size=0.8), T(4), send=0.5)
place(reverse_cymbal(1.2, amp=0.1), T(4) - 1.2, send=0.3)
place(riser(3.0, amp=0.16), T(47) - 3.0, send=0.4)
place(reverse_cymbal(3.0, amp=0.22), T(47) - 3.0, send=0.4)
place(boom(amp=0.8, size=1.8), T(47), send=0.5)
place(crash(amp=0.14, dur=4.0), T(47), pan=-0.2, send=0.5)
place(boom(amp=0.45, size=1.6), T(49), send=0.6)
# soft whooshes on content cuts
for sc in cues["scenes"]:
    if sc["cue"] == "cut":
        place(whoosh(amp=0.05), sc["start"] - 0.35, pan=rng.uniform(-0.4, 0.4), send=0.3)
# music box: birth (bars 4-5), "still young" (bar 43), end card (49-50)
BOX = [(4, [(84, 0), (79, 1), (76, 2), (72, 3)]), (5, [(74, 0), (79, 1), (83, 2), (86, 3)]),
       (43, [(84, 0), (81, 0.5), (77, 1), (81, 1.5), (84, 2), (88, 2.5), (84, 3), (81, 3.5)]),
       (49, [(88, 0), (85, 1), (81, 2), (76, 3)]), (50, [(81, 0)])]
for b, notes in BOX:
    for m, bt in notes:
        place(musicbox(m, amp=0.11), T(b, bt), pan=0.15, send=0.7)
# heartbeat under "…and still young." (ECG spikes land on the beats)
for q in range(4):
    place(heartbeat(amp=0.45), T(43, q), send=0.15)
# intro shimmer
n = int(6 * SR)
tt = np.arange(n) / SR
shimmer = sum(np.sin(2 * np.pi * mtof(m) * tt) * (0.5 + 0.5 * np.sin(2 * np.pi * (0.3 + k * 0.17) * tt)) for k, m in enumerate([88, 91, 95, 100]))
place(shimmer * np.clip(tt / 4, 0, 1) * np.clip((6 - tt) / 1.5, 0, 1) * 0.012, 0.0, send=0.9)


# ---------------------------------------------------------------- reverb + master
def make_ir(sec=3.6, rt60=3.0):
    n = int(sec * SR)
    t = np.arange(n) / SR
    ir = np.zeros((2, n))
    for c in range(2):
        lo = signal.sosfilt(signal.butter(1, 5000, fs=SR, output="sos"), rng.standard_normal(n))
        hi = rng.standard_normal(n)
        ir[c] = lo * np.exp(-6.9 * t / rt60) + 0.25 * hi * np.exp(-6.9 * t / (rt60 * 0.35))
    pre = int(0.022 * SR)
    ir = np.pad(ir, ((0, 0), (pre, 0)))[:, :n]
    return ir / np.sqrt((ir ** 2).sum(axis=1, keepdims=True))


ir = make_ir()
rev = np.vstack([signal.fftconvolve(wet[c], ir[c])[:N] for c in range(2)])
mix = dry + 0.55 * rev
mix = signal.sosfilt(signal.butter(2, 34, "highpass", fs=SR, output="sos"), mix, axis=1)


def shelf(x, f0, gain_db, high=True, q=0.707):
    """RBJ biquad shelving EQ."""
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / SR
    alpha = np.sin(w0) / (2 * q)
    c = np.cos(w0)
    sA = 2 * np.sqrt(A) * alpha
    if high:
        b = [A * ((A + 1) + (A - 1) * c + sA), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sA)]
        a = [(A + 1) - (A - 1) * c + sA, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sA]
    else:
        b = [A * ((A + 1) - (A - 1) * c + sA), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sA)]
        a = [(A + 1) + (A - 1) * c + sA, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sA]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=1)


mix = shelf(mix, 2600, 5.0, high=True)
mix = shelf(mix, 75, -4.0, high=False)

# fade in/out
fade_in = np.clip(np.arange(N) / (0.8 * SR), 0, 1)
end = cues["total"]
t_all = np.arange(N) / SR
fade_out = np.clip((end + 1.5 - t_all) / 4.0, 0, 1)
mix *= fade_in * fade_out

# loudness: normalise to about -14 LUFS with a soft ceiling
try:
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    loud = meter.integrated_loudness(mix.T)
    mix *= 10 ** ((-14.5 - loud) / 20)
except Exception as e:  # pragma: no cover
    print("pyloudnorm unavailable, peak-normalising:", e, file=sys.stderr)
    mix *= 0.5 / np.max(np.abs(mix))
ceiling = 10 ** (-1.0 / 20)
mix = np.tanh(mix / ceiling) * ceiling

pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2").T.copy()
out = os.path.join(BUILD, "music.wav")
import wave
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", out, f"{N / SR:.1f}s", "peak", float(np.max(np.abs(mix))))
