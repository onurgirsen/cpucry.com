"""
instruments.py - the voices of "Sinir Uçları".

Each function returns a mono (n,) or stereo (2, n) float array that starts
at the note onset.  Nothing here is sampled: drums are shaped noise and
swept sines, keys are FM, the lead "sings" through a formant filter bank
the way a talk box shapes a synth with a mouth.
"""
import numpy as np

import synth as S
from synth import SR, const, hz, midi, nsamp, tvec

RNG = np.random.default_rng(2026)


def _noise(n, rng=RNG):
    return rng.standard_normal(n)


# Pre-rendered metallic noise (six detuned squares, like the 808 hat
# circuit) - sliced at random offsets so every hit is a little different.
_HAT_F = np.array([205.3, 304.4, 369.6, 522.7, 540.0, 800.0])


def _metal_bank(seconds=3.0, tone=1.0, seed=11):
    rng = np.random.default_rng(seed)
    n = nsamp(seconds)
    m = np.zeros(n)
    for f in _HAT_F * tone:
        m += S.pulse(const(f, n), const(0.5, n), rng.random())
    m /= len(_HAT_F)
    return 0.65 * m + 0.45 * rng.standard_normal(n)


_METAL = S.eq(_metal_bank(), ('hp', 6500, 0.7), ('peak', 10500, 1.0, 5.0),
              ('lp', 16000, 0.7))
_METAL_DARK = S.eq(_metal_bank(tone=0.8, seed=12), ('hp', 4000, 0.7),
                   ('peak', 7500, 0.9, 4.0), ('lp', 12000, 0.7))


def _slice(bank, n, rng=RNG):
    s = rng.integers(0, bank.shape[0] - n - 1)
    return bank[s:s + n].copy()


# ==========================================================================
# Drums
# ==========================================================================

def kick(vel=1.0, tail='F1', decay=0.33, punch=165.0, click=0.22, length=0.62,
         drive=1.7):
    n = nsamp(length)
    t = tvec(n)
    f0 = hz(tail)
    f = f0 + (punch - f0) * np.exp(-t / 0.028) + 110.0 * np.exp(-t / 0.0035)
    amp = (1 - np.exp(-t / 0.0005)) * np.exp(-t / decay)
    body = np.sin(S.phase_of(f)) * amp
    # the beater click is band-limited and added after the saturation, so
    # it stays a tick instead of turning into spiky distorted noise
    nz = S.eq(_noise(n), ('hp', 1500, 0.7), ('lp', 6500, 0.7)) * np.exp(-t / 0.0025)
    x = np.tanh(drive * body) / np.tanh(drive) + click * 0.5 * nz
    return S.fade(x * vel, 0.0003, 0.03)


def snare(vel=1.0, tone=188.0, length=0.42, noise_decay=0.14, body_decay=0.075,
          bright=1.0):
    n = nsamp(length)
    t = tvec(n)
    f = tone * (1 + 0.28 * np.exp(-t / 0.01))
    body = np.sin(S.phase_of(f)) * np.exp(-t / body_decay)
    nz = S.eq(_noise(n), ('hp', 1300, 0.7), ('peak', 4200 * bright, 0.8, 3.0),
              ('lp', 11000, 0.7))
    nz *= np.exp(-t / noise_decay) * (1 - np.exp(-t / 0.0008))
    x = 0.55 * body + 0.9 * nz / (np.max(np.abs(nz)) + 1e-9)
    x = np.tanh(1.6 * x) / np.tanh(1.6)
    return S.fade(x * vel, 0.0003, 0.02)


def clap(vel=1.0, length=0.5, tone=1.0):
    n = nsamp(length)
    t = tvec(n)
    env = np.zeros(n)
    for k, off in enumerate((0.0, 0.0085, 0.0175, 0.027)):
        s = nsamp(off)
        env[s:] += np.exp(-(t[s:] - off) / 0.0042) * (0.75 if k < 3 else 1.0)
    env += np.where(t > 0.027, np.exp(-(t - 0.027) / 0.115), 0.0) * 0.5
    nz = _noise(n)
    x = S.bp(nz, 1180.0 * tone, 0.9) + 0.45 * S.hp(nz, 2800.0)
    x *= env
    x /= np.max(np.abs(x)) + 1e-9
    return S.fade(x * vel, 0.0003, 0.02)


def hat(vel=1.0, open_=False, decay=None, dark=False):
    decay = decay or (0.24 if open_ else 0.030)
    n = nsamp(min(1.4, decay * 5.5))
    t = tvec(n)
    bank = _METAL_DARK if dark else _METAL
    x = _slice(bank, n) * np.exp(-t / decay) * (1 - np.exp(-t / 0.0004))
    x /= np.max(np.abs(x)) + 1e-9
    return S.fade(x * vel, 0.0002, 0.01)


def shaker(vel=1.0):
    n = nsamp(0.14)
    t = tvec(n)
    x = S.bp(_noise(n), 7800.0, 1.3)
    x *= (1 - np.exp(-t / 0.007)) * np.exp(-t / 0.032)
    x /= np.max(np.abs(x)) + 1e-9
    return S.fade(x * vel, 0.001, 0.01)


def crash(vel=1.0, length=3.8):
    n = nsamp(length)
    t = tvec(n)
    out = np.zeros((2, n))
    tiled = np.tile(_METAL, int(np.ceil(n / _METAL.shape[0])) + 1)
    for c in range(2):
        off = RNG.integers(0, _METAL.shape[0])
        x = S.hp(0.7 * _noise(n) + 0.6 * tiled[off:off + n], 3500.0)
        fc = 7000 + 9000 * np.exp(-t / 0.6)
        x = S.lp(x, fc, 0.6)
        env = (1 - np.exp(-t / 0.0008)) * (0.4 * np.exp(-t / 0.1) + 0.6 * np.exp(-t / 1.15))
        out[c] = x * env
    out /= np.max(np.abs(out)) + 1e-9
    return S.fade(out * vel, 0.0002, 0.3)


def cowbell(freq, vel=1.0, length=0.32):
    """808-style cowbell (two squares a 'tritone-ish' 1.48 apart), pitched."""
    n = nsamp(length)
    t = tvec(n)
    w = const(0.5, n)
    x = S.pulse(const(freq, n), w, 0.0) + 0.75 * S.pulse(const(freq * 1.4815, n), w, 0.3)
    x = S.eq(x, ('hp', freq * 0.9, 0.7), ('peak', freq * 2.6, 1.2, 5.0), ('lp', 6500, 0.7))
    env = (1 - np.exp(-t / 0.0006)) * (0.72 * np.exp(-t / 0.016) + 0.28 * np.exp(-t / 0.10))
    x = np.tanh(1.3 * x * env)
    x /= np.max(np.abs(x)) + 1e-9
    return S.fade(x * vel, 0.0003, 0.02)


def heartbeat(vel=1.0, gap=0.2):
    def thump(a, pitch):
        n = nsamp(0.32)
        t = tvec(n)
        f = pitch + 30 * np.exp(-t / 0.028)
        x = np.sin(S.phase_of(f)) * (1 - np.exp(-t / 0.004)) * np.exp(-t / 0.08)
        x += 0.35 * S.lp(_noise(n), 160.0) * np.exp(-t / 0.025)
        return a * np.tanh(2.2 * x) / np.tanh(2.2)
    lub = thump(1.0, 44.0)
    dub = thump(0.62, 50.0)
    out = np.zeros(nsamp(gap) + dub.shape[0])
    out[:lub.shape[0]] += lub
    out[nsamp(gap):] += dub
    return S.fade(out * vel, 0.001, 0.02)


# ==========================================================================
# Bass
# ==========================================================================

def bass808(notes, length, drive=2.3, glide=0.085, decay=1.6, tone=2600.0):
    """Monophonic 808 line.

    notes: list of (t0, dur, note, slide) with t0 relative to the returned
    buffer.  A sliding note glides from the previous pitch instead of
    re-triggering, the signature phonk / trap move.
    """
    n = nsamp(length)
    f = np.full(n, 30.0)
    amp = np.zeros(n)
    level = 0.0
    for i, (t0, dur, note, slide) in enumerate(notes):
        s = nsamp(t0)
        e = min(n, nsamp(t0 + dur))
        if e <= s:
            continue
        lt = tvec(e - s)
        target = hz(note)
        prev = hz(notes[i - 1][2]) if i > 0 else target
        touching = i > 0 and abs(t0 - (notes[i - 1][0] + notes[i - 1][1])) < 1e-3
        if slide and touching:      # legato glide, no new attack
            f[s:e] = target * (prev / target) ** np.exp(-lt / (glide / 3))
            a = level * np.exp(-lt / decay)
        elif slide:                 # re-attack, but swoop in from the last pitch
            f[s:e] = target * (prev / target) ** np.exp(-lt / (glide / 3))
            a = (1 - np.exp(-lt / 0.0012)) * np.exp(-lt / decay)
        else:
            f[s:e] = target * (1 + 0.85 * np.exp(-lt / 0.011))
            a = (1 - np.exp(-lt / 0.0012)) * np.exp(-lt / decay)
        nxt = notes[i + 1] if i + 1 < len(notes) else None
        legato_out = nxt is not None and nxt[3] and abs(nxt[0] - (t0 + dur)) < 1e-3
        if not legato_out:
            r = min(e - s, nsamp(0.035))
            a[-r:] *= np.linspace(1, 0, r) ** 1.5
        amp[s:e] = a
        level = a[-1]
    x = np.sin(S.phase_of(f)) * amp
    x = np.tanh(drive * x) / np.tanh(drive)
    return S.lp(x, tone, 0.6)


def sub(note, dur, vel=1.0, attack=0.04, release=0.25):
    f = hz(note)
    n = nsamp(dur + release)
    t = tvec(n)
    x = np.sin(2 * np.pi * f * t)
    env = S.adsr(n, attack, 1.0, 1.0, release, dur)
    x = np.tanh(1.4 * x * env) / np.tanh(1.4)
    return S.fade(x * vel, 0.002, 0.02)


def funk_bass(note, dur, vel=1.0, peak=1500.0, res=2.3):
    """Rubbery filtered-saw house bass (+ clean sine underneath)."""
    f = hz(note)
    n = nsamp(dur + 0.04)
    t = tvec(n)
    x = 0.8 * S.saw(const(f, n), RNG.random()) + 0.3 * S.pulse(const(f, n), const(0.5, n))
    fc = 170.0 + peak * vel * np.exp(-t / 0.10)
    y = S.ladder(x, fc, const(res, n), 1.6)
    s = np.sin(2 * np.pi * f * t)
    env = np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.008)) * (1 - np.exp(-t / 0.0015))
    return S.fade((0.9 * y + 0.55 * s) * env * vel, 0.001, 0.008)


# ==========================================================================
# Keys
# ==========================================================================

def supersaw(notes, dur, attack=0.35, release=1.0, cutoff=3000.0, q=0.75,
             voices=7, detune=0.16, width=0.9, vel=1.0, seed=None):
    """Detuned-saw chord. `cutoff` is Hz or a function of local time (s)."""
    rng = np.random.default_rng(seed)
    n = nsamp(dur + release)
    t = tvec(n)
    out = np.zeros((2, n))
    for note in notes:
        f0 = hz(note)
        for v in range(voices):
            sp = (v / (voices - 1)) * 2 - 1
            cents = sp * detune * 100 + rng.normal(0, 1.5)
            x = S.saw(const(f0 * 2 ** (cents / 1200), n), rng.random())
            ang = (sp * width + 1) * np.pi / 4
            out[0] += x * np.cos(ang)
            out[1] += x * np.sin(ang)
    out *= np.sqrt(2) / np.sqrt(voices * len(notes))
    fc = cutoff(t) if callable(cutoff) else const(cutoff, n)
    out = S.lp(out, fc, q)
    env = S.adsr(n, attack, 1.0, 1.0, release, dur)
    return S.fade(out * env * vel, 0.002, 0.05)


def ep(note, dur, vel=0.8, release=0.4):
    """FM electric piano (tine + body), a DX-style Rhodes."""
    f = hz(note)
    tau = 1.8 * (261.6 / f) ** 0.4
    n = nsamp(dur + release)
    t = tvec(n)
    ph = 2 * np.pi * f * t
    i1 = (0.5 + 1.9 * vel) * np.exp(-t / 0.55) + 0.22
    body = np.sin(ph + i1 * np.sin(ph))
    i2 = (1.2 + 2.2 * vel) * np.exp(-t / 0.016)
    tine = np.sin(1.0007 * ph + i2 * np.sin(14.0 * ph)) * np.exp(-t / 0.35)
    x = body * np.exp(-t / tau) + 0.32 * tine
    x *= 1 - np.exp(-t / 0.0015)
    x *= np.where(t < dur, 1.0, np.exp(-(t - dur) / (release / 4)))
    return S.fade(x * vel, 0.001, 0.02)


def bell(note, vel=0.7, length=2.6):
    """Music-box / celesta: free-bar partials with fast upper decays."""
    f = hz(note)
    n = nsamp(length)
    t = tvec(n)
    x = np.zeros(n)
    for ratio, amp, dec in ((1.0, 1.0, 1.25), (2.0, 0.16, 0.7), (2.76, 0.28, 0.32),
                            (5.40, 0.12, 0.12), (8.93, 0.05, 0.05)):
        if f * ratio < 0.45 * SR:
            x += amp * np.sin(2 * np.pi * f * ratio * t + RNG.random() * 6.28) * np.exp(-t / dec)
    x *= 1 - np.exp(-t / 0.0012)
    x += 0.15 * S.hp(_noise(n), 5000.0) * np.exp(-t / 0.002)
    return S.fade(x * vel, 0.0005, 0.05)


def pluck(note, dur, vel=0.8, peak=3200.0, base=450.0, res=1.5, fdecay=0.09,
          adecay=0.28, seed=None):
    """Tron-ish arpeggio pluck: saw+pulse through a snappy ladder filter."""
    f = hz(note)
    n = nsamp(dur + 0.06)
    t = tvec(n)
    x = 0.6 * S.saw(const(f, n), RNG.random()) + \
        0.4 * S.pulse(const(f * 1.003, n), const(0.32, n), RNG.random())
    fc = base + peak * vel * np.exp(-t / fdecay)
    y = S.ladder(x, fc, const(res, n), 1.3)
    env = (1 - np.exp(-t / 0.0015)) * np.exp(-t / adecay)
    env *= np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.012))
    return S.fade(y * env * vel, 0.0005, 0.01)


# ==========================================================================
# The voice: a talk-box style singing lead
# ==========================================================================

# formant centre (Hz) and relative gains for a neutral adult voice
VOWELS = {
    'a': ((730, 1090, 2440, 3400), (1.0, 0.95, 0.75, 0.40)),
    'o': ((570, 840, 2410, 3400), (1.0, 0.85, 0.35, 0.18)),
    'u': ((320, 870, 2240, 3300), (1.0, 0.50, 0.18, 0.08)),
    'e': ((530, 1840, 2480, 3500), (1.0, 0.85, 0.70, 0.35)),
    'i': ((290, 2290, 3010, 3600), (1.0, 0.60, 0.75, 0.40)),
}
FORMANT_Q = (6.0, 9.0, 12.0, 13.0)


def voice_line(notes, length, glide=0.075, vib_rate=5.2, vib_depth=0.28,
               shift=1.0, sub_oct=0.3, formant=True, breath=0.04, bright=1.0,
               seed=0):
    """Render a monophonic sung line.

    notes: list of (t0, dur, note, vowel) with t0 relative to the buffer.
    Notes that touch (gap < 30 ms) are sung legato: the pitch glides and the
    mouth only half-closes between them.  A fresh phrase opens from "u" to
    the vowel, the "wah" of a talk box.
    """
    rng = np.random.default_rng(seed)
    n = nsamp(length)
    pitch = np.zeros(n)
    amp = np.zeros(n)
    since = np.full(n, 10.0)
    ftrg = np.zeros((4, n))
    gtrg = np.zeros((4, n))
    notes = sorted(notes, key=lambda x: x[0])

    # group into legato phrases
    phrases, cur = [], []
    for nt in notes:
        if cur and nt[0] - (cur[-1][0] + cur[-1][1]) > 0.03:
            phrases.append(cur)
            cur = []
        cur.append(nt)
    if cur:
        phrases.append(cur)

    rel = 0.16
    last_pitch = midi(notes[0][2]) if notes else 60
    for ph in phrases:
        p0 = nsamp(ph[0][0])
        pe = min(n, nsamp(ph[-1][0] + ph[-1][1]))
        pr = min(n, pe + nsamp(rel * 4))
        # amplitude: open, hold, close
        seg = np.arange(pr - p0) / SR
        a = np.minimum(1.0, seg / 0.028)
        tail = seg >= (pe - p0) / SR
        a[tail] = np.exp(-(seg[tail] - (pe - p0) / SR) / rel * 1.2)
        amp[p0:pr] = np.maximum(amp[p0:pr], a)
        for j, (t0, dur, note, vowel) in enumerate(ph):
            s = nsamp(t0)
            e = pr if j == len(ph) - 1 else min(n, nsamp(t0 + dur))
            if e <= s:
                continue
            lt = np.arange(e - s) / SR
            m = midi(note)
            if j > 0:
                prev = midi(ph[j - 1][2])
                pitch[s:e] = m + (prev - m) * np.exp(-lt / (glide / 3))
            else:
                pitch[s:e] = m - 0.45 * np.exp(-lt / 0.035)
            since[s:e] = lt
            fr, gn = VOWELS[vowel]
            onset = 'u' if j == 0 else 'o'
            ofr, ogn = VOWELS[onset]
            k = min(e - s, nsamp(0.05 if j == 0 else 0.03))
            for q in range(4):
                ftrg[q, s:e] = fr[q]
                gtrg[q, s:e] = gn[q]
                ftrg[q, s:s + k] = ofr[q]
                gtrg[q, s:s + k] = ogn[q]
            last_pitch = m
    # fill silent regions with the neighbouring pitch so the oscillator
    # never jumps while inaudible
    silent = amp <= 0
    if silent.any():
        idx = np.where(~silent, np.arange(n), 0)
        np.maximum.accumulate(idx, out=idx)
        pitch = pitch[idx]
        pitch[pitch == 0] = last_pitch
        for q in range(4):
            ftrg[q] = ftrg[q][idx]
            gtrg[q] = gtrg[q][idx]
        ftrg[ftrg == 0] = 700.0

    # delayed vibrato, with a little random rate drift
    ramp = np.clip((since - 0.2) / 0.4, 0, 1)
    rate = vib_rate * (1 + 0.06 * S.smooth(rng.standard_normal(n), 300.0))
    vib = vib_depth * ramp * np.sin(np.cumsum(2 * np.pi * rate / SR))
    drift = 0.04 * S.smooth(rng.standard_normal(n), 120.0)
    f = 440.0 * 2 ** ((pitch + vib + drift - 69) / 12)

    src = S.saw(f, 0.0) + 0.45 * S.pulse(f * 1.0021, const(0.3, n), 0.5)
    if sub_oct:
        src += sub_oct * S.saw(f * 0.5, 0.25)
    src += breath * S.hp(rng.standard_normal(n), 2500.0)
    # envelope the source *before* the mouth: the oscillators start with a
    # jump, and filtering that jump first would leave a tick on every entry
    src *= amp

    if formant:
        # a talk box has little fundamental and a bright, buzzy source: thin
        # the bottom and lift the top before the "mouth" shapes it
        src = S.eq(src, ('hp', 550, 0.7), ('highshelf', 1500, 0.7, 3.0))
        out = 0.03 * src
        for q in range(4):
            fq = np.exp(S.smooth(np.log(ftrg[q] * shift), 22.0))
            gq = S.smooth(gtrg[q], 22.0)
            out += gq * S.svf(src, fq, const(FORMANT_Q[q], n), 1)
        out *= 1.6
    else:
        out = S.lp(src, 5200.0 * bright, 0.7) * 0.55
    return out


def choir(notes, dur, vowel='a', attack=0.6, release=1.4, vel=1.0, seed=None,
          shift=1.0):
    """Synthetic 'aah' choir: a soft supersaw pushed through vowel formants."""
    rng = np.random.default_rng(seed)
    n = nsamp(dur + release)
    t = tvec(n)
    out = np.zeros((2, n))
    fr, gn = VOWELS[vowel]
    for note in notes:
        f0 = hz(note)
        for v in range(4):
            sp = (v / 3) * 2 - 1
            vib = 0.12 * np.sin(2 * np.pi * rng.uniform(4.6, 5.6) * t + rng.random() * 6.28)
            f = f0 * 2 ** ((sp * 9 + rng.normal(0, 2)) / 1200 + vib / 12)
            x = S.saw(f, rng.random())
            y = 0.05 * x
            for q in range(4):
                y += gn[q] * S.svf(x, const(fr[q] * shift, n), const(FORMANT_Q[q] * 0.8, n), 1)
            ang = (sp * 0.8 + 1) * np.pi / 4
            out[0] += y * np.cos(ang)
            out[1] += y * np.sin(ang)
    out *= 1.8 / np.sqrt(4 * len(notes))
    env = S.adsr(n, attack, 1.0, 1.0, release, dur)
    return S.fade(out * env * vel, 0.002, 0.05)


# ==========================================================================
# FX & atmosphere
# ==========================================================================

def riser(dur, f0=300.0, f1=9000.0, seed=None):
    rng = np.random.default_rng(seed)
    n = nsamp(dur)
    t = tvec(n)
    u = t / dur
    fc = f0 * (f1 / f0) ** (u ** 1.4)
    out = np.zeros((2, n))
    for c in range(2):
        out[c] = S.svf(rng.standard_normal(n), fc * (1.0 + 0.03 * c), const(2.2, n), 1)
    sw = 0.0
    for d in (-0.1, 0.1):
        sw = sw + S.saw(110.0 * 2 ** (u * 2.5 + d / 12), rng.random())
    sw = S.lp(sw, 400 + 5000 * u ** 2, 0.8) * 0.25
    out += np.stack([sw, sw])
    out *= (u ** 2.4)[None, :]
    return S.fade(out / (np.max(np.abs(out)) + 1e-9), 0.01, 0.01)


def downlifter(dur, seed=None):
    rng = np.random.default_rng(seed)
    n = nsamp(dur)
    t = tvec(n)
    u = t / dur
    fc = 7000.0 * (250.0 / 7000.0) ** (u ** 0.7)
    out = np.stack([S.svf(rng.standard_normal(n), fc, const(1.5, n), 1) for _ in range(2)])
    out *= ((1 - u) ** 2 * (1 - np.exp(-t / 0.01)))[None, :]
    return S.fade(out / (np.max(np.abs(out)) + 1e-9), 0.005, 0.05)


def boom(vel=1.0, length=2.4):
    n = nsamp(length)
    t = tvec(n)
    f = 31.0 + 85.0 * np.exp(-t / 0.11)
    x = np.sin(S.phase_of(f)) * np.exp(-t / 0.75) * (1 - np.exp(-t / 0.002))
    x = np.tanh(1.8 * x) / np.tanh(1.8)
    x += 0.25 * S.lp(_noise(n), 900.0) * np.exp(-t / 0.05)
    return S.fade(x * vel, 0.001, 0.2)


def blip(note, vel=0.5):
    f = hz(note)
    n = nsamp(0.09)
    t = tvec(n)
    x = np.sin(S.phase_of(f * (1 + 0.04 * np.exp(-t / 0.01)))) * np.exp(-t / 0.022)
    x += 0.2 * S.pulse(const(f * 2, n), const(0.5, n)) * np.exp(-t / 0.008)
    return S.fade(x * vel, 0.0005, 0.01)


def vinyl(length, density=9.0, hiss=0.011, seed=5):
    """Record crackle: sparse, heavy-tailed clicks + soft band-limited hiss."""
    rng = np.random.default_rng(seed)
    n = nsamp(length)
    out = np.zeros((2, n))
    count = int(length * density)
    pos = rng.integers(0, n - 64, count)
    amp = np.minimum(rng.pareto(2.2, count) * 0.25, 0.9) * rng.choice([-1, 1], count)
    ch = rng.integers(0, 2, count)
    np.add.at(out, (ch, pos), amp)
    np.add.at(out, (1 - ch, pos), amp * 0.4)
    out = S.eq(out, ('hp', 700, 0.7), ('peak', 2500, 0.8, 4.0), ('lp', 7000, 0.7))
    h = S.eq(rng.standard_normal((2, n)), ('hp', 2500, 0.7), ('lp', 9000, 0.7))
    return out + hiss * h
