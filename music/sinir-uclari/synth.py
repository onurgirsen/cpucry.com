"""
synth.py - the small DSP / synthesis engine behind "Sinir Uçları".

Every sound in the track is computed here from maths alone: no samples,
no presets.  Oscillators are band-limited (PolyBLEP), filters are
zero-delay-feedback designs, and the reverb is a convolution with a
synthetic impulse response.
"""
import re

import numpy as np
from numba import njit
from scipy import signal
from scipy.ndimage import minimum_filter1d, uniform_filter1d

SR = 44100

_NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5,
         'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10,
         'Bb': 10, 'B': 11}


def midi(name):
    """'Db5' -> 73. Numbers pass through unchanged."""
    if not isinstance(name, str):
        return name
    m = re.fullmatch(r'([A-G][b#]?)(-?\d)', name)
    return 12 * (int(m.group(2)) + 1) + _NOTE[m.group(1)]


def hz(note):
    return 440.0 * 2.0 ** ((midi(note) - 69) / 12.0)


def db(x):
    return 10.0 ** (x / 20.0)


def nsamp(seconds):
    return max(1, int(round(seconds * SR)))


def tvec(n):
    return np.arange(n) / SR


# --------------------------------------------------------------------------
# Oscillators
# --------------------------------------------------------------------------

@njit(cache=True, fastmath=True)
def _blep(t, dt):
    if t < dt:
        t /= dt
        return t + t - t * t - 1.0
    elif t > 1.0 - dt:
        t = (t - 1.0) / dt
        return t * t + t + t + 1.0
    return 0.0


@njit(cache=True, fastmath=True)
def saw(freq, phase=0.0):
    n = freq.shape[0]
    out = np.empty(n)
    ph = phase
    for i in range(n):
        dt = freq[i] / SR
        out[i] = 2.0 * ph - 1.0 - _blep(ph, dt)
        ph += dt
        ph -= np.floor(ph)
    return out


@njit(cache=True, fastmath=True)
def pulse(freq, width, phase=0.0):
    n = freq.shape[0]
    out = np.empty(n)
    ph = phase
    for i in range(n):
        dt = freq[i] / SR
        w = width[i]
        v = 1.0 if ph < w else -1.0
        v += _blep(ph, dt)
        t2 = ph - w
        if t2 < 0.0:
            t2 += 1.0
        v -= _blep(t2, dt)
        out[i] = v - (2.0 * w - 1.0)
        ph += dt
        ph -= np.floor(ph)
    return out


def phase_of(freq, phase=0.0):
    """Running phase (radians) of a frequency trajectory, starting at `phase`."""
    acc = np.concatenate(([0.0], np.cumsum(freq[:-1])))
    return phase + 2.0 * np.pi * acc / SR


def sine(freq, phase=0.0):
    return np.sin(phase_of(freq, phase))


def const(value, n):
    return np.full(n, float(value))


# --------------------------------------------------------------------------
# Filters
# --------------------------------------------------------------------------

@njit(cache=True, fastmath=True)
def svf(x, fc, q, mode):
    """TPT state-variable filter with per-sample cutoff/Q.

    mode 0 = low-pass, 1 = band-pass (unity gain at centre), 2 = high-pass.
    """
    n = x.shape[0]
    y = np.empty(n)
    ic1 = 0.0
    ic2 = 0.0
    lim = 0.49 * SR
    for i in range(n):
        f = fc[i]
        if f > lim:
            f = lim
        elif f < 5.0:
            f = 5.0
        g = np.tan(np.pi * f / SR)
        k = 1.0 / q[i]
        a1 = 1.0 / (1.0 + g * (g + k))
        a2 = g * a1
        a3 = g * a2
        v3 = x[i] - ic2
        v1 = a1 * ic1 + a2 * v3
        v2 = ic2 + a2 * ic1 + a3 * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        if mode == 0:
            y[i] = v2
        elif mode == 1:
            y[i] = k * v1
        else:
            y[i] = x[i] - k * v1 - v2
    return y


@njit(cache=True, fastmath=True)
def ladder(x, fc, res, drive):
    """Four-pole transistor-ladder style low-pass with tanh input stage."""
    n = x.shape[0]
    y = np.empty(n)
    s1 = 0.0
    s2 = 0.0
    s3 = 0.0
    s4 = 0.0
    fb = 0.0
    lim = 0.45 * SR
    for i in range(n):
        f = fc[i]
        if f > lim:
            f = lim
        elif f < 10.0:
            f = 10.0
        g = np.tan(np.pi * f / SR)
        G = g / (1.0 + g)
        u = np.tanh(drive * (x[i] - res[i] * fb))
        v = (u - s1) * G
        y1 = v + s1
        s1 = y1 + v
        v = (y1 - s2) * G
        y2 = v + s2
        s2 = y2 + v
        v = (y2 - s3) * G
        y3 = v + s3
        s3 = y3 + v
        v = (y3 - s4) * G
        y4 = v + s4
        s4 = y4 + v
        fb = y4
        y[i] = y4 * (1.0 + 0.5 * res[i]) / drive
    return y


def lp(x, fc, q=0.707):
    n = x.shape[-1]
    fc = np.broadcast_to(np.asarray(fc, float), (n,)).copy()
    q = np.broadcast_to(np.asarray(q, float), (n,)).copy()
    if x.ndim == 2:
        return np.stack([svf(x[c], fc, q, 0) for c in range(x.shape[0])])
    return svf(x, fc, q, 0)


def hp(x, fc, q=0.707):
    n = x.shape[-1]
    fc = np.broadcast_to(np.asarray(fc, float), (n,)).copy()
    q = np.broadcast_to(np.asarray(q, float), (n,)).copy()
    if x.ndim == 2:
        return np.stack([svf(x[c], fc, q, 2) for c in range(x.shape[0])])
    return svf(x, fc, q, 2)


def bp(x, fc, q=1.0):
    n = x.shape[-1]
    fc = np.broadcast_to(np.asarray(fc, float), (n,)).copy()
    q = np.broadcast_to(np.asarray(q, float), (n,)).copy()
    if x.ndim == 2:
        return np.stack([svf(x[c], fc, q, 1) for c in range(x.shape[0])])
    return svf(x, fc, q, 1)


def biquad(kind, f0, q=0.707, gain_db=0.0):
    """RBJ cookbook biquad as one SOS row."""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * f0 / SR
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2 * q)
    if kind == 'lp':
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == 'hp':
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == 'peak':
        b = [1 + alpha * A, -2 * cw, 1 - alpha * A]
        a = [1 + alpha / A, -2 * cw, 1 - alpha / A]
    elif kind == 'lowshelf':
        sq = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) - (A - 1) * cw + sq), 2 * A * ((A - 1) - (A + 1) * cw),
             A * ((A + 1) - (A - 1) * cw - sq)]
        a = [(A + 1) + (A - 1) * cw + sq, -2 * ((A - 1) + (A + 1) * cw),
             (A + 1) + (A - 1) * cw - sq]
    elif kind == 'highshelf':
        sq = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) + (A - 1) * cw + sq), -2 * A * ((A - 1) + (A + 1) * cw),
             A * ((A + 1) + (A - 1) * cw - sq)]
        a = [(A + 1) - (A - 1) * cw + sq, 2 * ((A - 1) - (A + 1) * cw),
             (A + 1) - (A - 1) * cw - sq]
    else:
        raise ValueError(kind)
    b = np.array(b) / a[0]
    a = np.array(a) / a[0]
    return np.concatenate([b, a])[None, :]


def eq(x, *bands):
    """Static EQ: eq(x, ('hp', 120), ('peak', 2500, 1.0, 3.0), ...)."""
    sos = np.vstack([biquad(*b) for b in bands])
    return signal.sosfilt(sos, x, axis=-1)


# --------------------------------------------------------------------------
# Envelopes & helpers
# --------------------------------------------------------------------------

def adsr(n, a, d, s, r, gate):
    """Linear-attack / exponential-decay ADSR. `gate` is note length in s.
    Returns n samples (n should cover gate + r)."""
    t = tvec(n)
    env = np.where(t < a, t / max(a, 1e-4),
                   s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    g = min(gate, t[-1])
    gi = min(n - 1, int(g * SR))
    lvl = env[gi]
    rel = lvl * np.exp(-(t - g) / max(r, 1e-4) * 3.0)
    env = np.where(t < g, env, rel)
    return env


def fade(x, fin=0.002, fout=0.005):
    """Short fades to guarantee click-free edges."""
    x = np.array(x, dtype=float, copy=True)
    n = x.shape[-1]
    a = min(n // 2, nsamp(fin))
    b = min(n // 2, nsamp(fout))
    if a > 0:
        x[..., :a] *= np.linspace(0, 1, a)
    if b > 0:
        x[..., -b:] *= np.linspace(1, 0, b)
    return x


def pan(x, p):
    """Equal-power pan of a mono signal; p in [-1, 1]. Centre = unity."""
    ang = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(ang), x * np.sin(ang)]) * np.sqrt(2)


def smooth(x, ms):
    """One-pole smoother (used for control signals)."""
    a = np.exp(-1.0 / (ms * 1e-3 * SR))
    return signal.lfilter([1 - a], [1, -a], x, zi=[x[0] * a])[0]


def softclip(x, drive=1.0):
    return np.tanh(drive * x) / np.tanh(drive)


# --------------------------------------------------------------------------
# Effects
# --------------------------------------------------------------------------

def make_ir(seconds=4.5, t60=3.6, predelay=0.025, bright=9000.0, dark=1400.0,
            seed=1, early=True):
    """Synthetic stereo hall impulse response: decorrelated noise with
    frequency-dependent decay (high end dies first) and a few early taps."""
    rng = np.random.default_rng(seed)
    n = nsamp(seconds)
    t = tvec(n)
    env = 10 ** (-3 * t / t60) * (1 - np.exp(-t / 0.012))
    fc = dark + (bright - dark) * np.exp(-t / (t60 * 0.28))
    q = np.full(n, 0.6)
    ir = np.zeros((2, n))
    for c in range(2):
        nz = rng.standard_normal(n)
        ir[c] = svf(nz, fc, q, 0) * env
    if early:
        for _ in range(14):
            d = rng.uniform(0.004, 0.075)
            k = nsamp(d)
            ir[rng.integers(0, 2), k] += rng.uniform(-1, 1) * 0.5 * np.exp(-d / 0.05)
    pd = nsamp(predelay)
    ir = np.concatenate([np.zeros((2, pd)), ir[:, :n - pd]], axis=1)
    ir /= np.sqrt(np.mean(np.sum(ir ** 2, axis=1)))
    return ir


def reverb(x, ir):
    """Convolution reverb: each input channel into its own IR channel plus a
    little cross-feed for a wide, enveloping tail."""
    n = x.shape[-1]
    out = np.zeros((2, n))
    for c in range(2):
        out[c] += signal.oaconvolve(x[c], ir[c])[:n] * 0.8
        out[1 - c] += signal.oaconvolve(x[c], ir[1 - c])[:n] * 0.2
    return out


@njit(cache=True, fastmath=True)
def _pingpong(xm, d, fb, lpc, hpc):
    n = xm.shape[0]
    yl = np.zeros(n)
    yr = np.zeros(n)
    bl = np.zeros(d)
    br = np.zeros(d)
    idx = 0
    l1 = 0.0
    l2 = 0.0
    h1 = 0.0
    h2 = 0.0
    for i in range(n):
        dl = bl[idx]
        dr = br[idx]
        yl[i] = dl
        yr[i] = dr
        il = xm[i] + dr * fb
        ir = dl * fb
        l1 += lpc * (il - l1)
        l2 += lpc * (ir - l2)
        h1 += hpc * (l1 - h1)
        h2 += hpc * (l2 - h2)
        bl[idx] = l1 - h1
        br[idx] = l2 - h2
        idx += 1
        if idx >= d:
            idx = 0
    return yl, yr


def pingpong(x, delay_s, feedback=0.55, lp_hz=4500.0, hp_hz=250.0):
    xm = x.mean(axis=0) if x.ndim == 2 else x
    lpc = 1 - np.exp(-2 * np.pi * lp_hz / SR)
    hpc = 1 - np.exp(-2 * np.pi * hp_hz / SR)
    yl, yr = _pingpong(np.ascontiguousarray(xm), nsamp(delay_s), feedback, lpc, hpc)
    return np.stack([yl, yr])


def mod_delay(x, base_ms, depth_ms, rate, phase=0.0, jitter=None):
    """Delay line with a sinusoidally modulated read head (linear interp)."""
    n = x.shape[-1]
    idx = np.arange(n, dtype=float)
    lfo = np.sin(2 * np.pi * rate * idx / SR + phase)
    d = (base_ms + depth_ms * lfo) * 1e-3 * SR
    if jitter is not None:
        d = d + jitter
    return np.interp(idx - d, idx, x, left=0.0)


def chorus(x, mix=0.45, rate=0.35, depth_ms=2.2, base_ms=11.0):
    """Stereo chorus: two modulated taps per side, opposite LFO phases."""
    out = np.empty_like(x)
    for c in range(2):
        ph = 0.0 if c == 0 else np.pi / 2
        w = 0.5 * (mod_delay(x[c], base_ms, depth_ms, rate, ph) +
                   mod_delay(x[c], base_ms * 1.37, depth_ms * 0.8, rate * 1.31, ph + 2.0))
        out[c] = x[c] * (1 - mix) + w * mix
    return out


def wow_flutter(x, wow_ms=0.9, wow_rate=0.45, flutter_ms=0.035, flutter_rate=6.3,
                seed=3):
    """Tape-style pitch drift: slow wow + fast flutter + a little random drift."""
    rng = np.random.default_rng(seed)
    n = x.shape[-1]
    idx = np.arange(n, dtype=float)
    drift = smooth(rng.standard_normal(n), 400.0)
    drift = drift / (np.max(np.abs(drift)) + 1e-9)
    d = (4.0 + wow_ms * np.sin(2 * np.pi * wow_rate * idx / SR)
         + flutter_ms * np.sin(2 * np.pi * flutter_rate * idx / SR)
         + 0.5 * wow_ms * drift) * 1e-3 * SR
    return np.stack([np.interp(idx - d, idx, x[c], left=0.0) for c in range(2)])


@njit(cache=True, fastmath=True)
def _comp_gain(det_db, thresh, ratio, knee, att, rel):
    n = det_db.shape[0]
    out = np.empty(n)
    g = 0.0
    slope = 1.0 / ratio - 1.0
    for i in range(n):
        over = det_db[i] - thresh
        if 2.0 * over < -knee:
            gr = 0.0
        elif 2.0 * abs(over) <= knee:
            gr = slope * (over + knee / 2.0) ** 2 / (2.0 * knee)
        else:
            gr = slope * over
        if gr < g:
            g = att * g + (1.0 - att) * gr
        else:
            g = rel * g + (1.0 - rel) * gr
        out[i] = g
    return out


def compress(x, thresh_db=-18.0, ratio=2.0, attack_ms=20.0, release_ms=200.0,
             knee_db=6.0, makeup_db=0.0, detector=None):
    det = detector if detector is not None else np.max(np.abs(x), axis=0)
    det = uniform_filter1d(det, nsamp(0.002))  # short peak-ish window
    det_db = 20 * np.log10(np.maximum(det, 1e-9))
    att = np.exp(-1.0 / (attack_ms * 1e-3 * SR))
    rel = np.exp(-1.0 / (release_ms * 1e-3 * SR))
    gdb = _comp_gain(det_db, thresh_db, ratio, knee_db, att, rel)
    return x * db(gdb + makeup_db), gdb


@njit(cache=True, fastmath=True)
def _release(g, rel):
    n = g.shape[0]
    out = np.empty(n)
    s = 1.0
    for i in range(n):
        if g[i] < s:
            s = g[i]
        else:
            s = rel * s + (1.0 - rel) * g[i]
        out[i] = s
    return out


def limiter(x, ceiling_db=-1.0, lookahead_ms=4.0, release_ms=90.0, oversample=4):
    """Look-ahead brick-wall limiter (gain computed from future peaks,
    smoothed so it ramps down before the peak arrives).  Peaks are measured
    on a 4x oversampled copy, so inter-sample (true) peaks are caught too."""
    c = db(ceiling_db)
    la = nsamp(lookahead_ms * 1e-3)
    n = x.shape[-1]
    if oversample > 1:
        up = signal.resample_poly(x, oversample, 1, axis=-1)[:, :n * oversample]
        peak = np.abs(up).reshape(x.shape[0], n, oversample).max(axis=2).max(axis=0)
        del up
    else:
        peak = np.max(np.abs(x), axis=0)
    need = np.minimum(1.0, c / np.maximum(peak, 1e-12))
    # Hold the lowest required gain for +-la samples, then average over a
    # centred window of <= la samples: every sample in that window already
    # holds a gain <= the one needed here, so peaks can never get through,
    # while the gain ramps smoothly into each peak.
    gmin = minimum_filter1d(need, size=2 * la + 1)
    gs = uniform_filter1d(gmin, size=la if la % 2 else la + 1)
    rel = np.exp(-1.0 / (release_ms * 1e-3 * SR))
    g = _release(np.ascontiguousarray(gs), rel)
    y = x * g
    return np.clip(y, -c, c), g


def true_peak_db(x):
    up = signal.resample_poly(x, 4, 1, axis=-1)
    return 20 * np.log10(np.max(np.abs(up)) + 1e-12)


def tape_stop(x, start, dur, curve=1.6):
    """Slow a stereo buffer to a halt from `start` over `dur` seconds
    (vinyl/tape brake). Everything after the stop is silent."""
    s = nsamp(start)
    m = nsamp(dur)
    u = np.arange(m) / m
    rate = (1 - u) ** curve
    pos = s + np.cumsum(rate)
    out = x.copy()
    idx = np.arange(x.shape[-1], dtype=float)
    seg = np.stack([np.interp(pos, idx, x[c]) for c in range(2)])
    seg *= np.clip((1 - u) * 6, 0, 1) ** 0.5
    out[:, s:s + m] = seg
    out[:, s + m:] = 0.0
    return out
