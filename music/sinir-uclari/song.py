"""
song.py - "Sinir Uçları" (Nerve Endings), composed and rendered in code.

    python3 song.py            # full render -> out/sinir-uclari.wav + .mp3 + stems
    python3 song.py mix        # re-mix / re-master from the saved stems

F minor, 108 BPM.  The story, section by section:

  Nabız        heartbeat, a filtered pad, a music box hums the hope motif
  Tek Başına   chromatic lament bass (F-E-Eb-D-Db-C), the robot voice sings;
               a D-natural flickers like light, then falls back to Db
  Panik        phonk: distorted 808, cowbell riff in C Hicaz (Phrygian
               dominant) over a dominant pedal, then a tape-stop blackout
  Bir Gün Daha French-house drop; the dominant resolves *deceptively* to Db,
               the melody climbs, and a 4-3 suspension lands on A-natural:
               F major, the first time the song sees the light
  Nefes        the light goes out again; filter-house build, a breath
  Işık         the drop returns with a choir, an octave higher
  Yavaşla      half-time, "slowed" coda
  Sabah        F major; the motif returns with A instead of Ab
"""
import json
import os
import time

import numpy as np

import instruments as I
import synth as S
from synth import SR, db, hz, midi, nsamp

BPM = 108.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
STEP = BEAT / 4

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')


def T(bar, beat=0.0):
    """Absolute time (s) of `beat` within 1-based `bar`."""
    return (bar - 1) * BAR + beat * BEAT


SECTIONS = [
    ('Nabız', 1, 8),
    ('Tek Başına', 9, 16),
    ('Panik', 25, 8),
    ('Bir Gün Daha', 33, 16),
    ('Nefes', 49, 8),
    ('Işık', 57, 16),
    ('Yavaşla', 73, 4),
    ('Sabah', 77, 8),
]
END_BAR = 85
TAIL = 7.5
LEAD_IN = 0.5   # seconds of silence before bar 1
LENGTH = T(END_BAR) + TAIL

# tape-stop blackout before the first drop, and the breath before the second
STOP_AT, STOP_LEN = T(32, 2.5), 1.05 * BEAT
GASP_AT = T(56, 3.0)

# --------------------------------------------------------------------------
# Harmony
# --------------------------------------------------------------------------

CH = {
    # home / drop
    'Fm9': ('F1', ['Ab3', 'C4', 'Eb4', 'G4']),
    'Dbmaj9': ('Db2', ['F3', 'Ab3', 'C4', 'Eb4']),
    'Eb6': ('Eb2', ['G3', 'Bb3', 'C4', 'Eb4']),
    'Cm7': ('C2', ['G3', 'Bb3', 'Eb4', 'G4']),
    'Fsus4': ('F1', ['F3', 'Bb3', 'C4', 'F4']),
    'Fadd9': ('F1', ['F3', 'A3', 'C4', 'G4']),
    'C7sus4': ('C2', ['Bb3', 'C4', 'F4', 'G4']),
    'C7': ('C2', ['Bb3', 'C4', 'E4', 'G4']),
    # lament: the bass falls chromatically F-E-Eb-D-Db-C
    'Fm': ('F2', ['Ab3', 'C4', 'F4']),
    'Fm/F1': ('F1', ['Ab3', 'C4', 'F4']),
    'C/E': ('E2', ['G3', 'C4', 'E4']),
    'Fm/Eb': ('Eb2', ['Ab3', 'C4', 'F4']),
    'Bb/D': ('D2', ['Bb3', 'D4', 'F4']),
    'Bbm/Db': ('Db2', ['Bb3', 'Db4', 'F4']),
    'Fm/C': ('C2', ['Ab3', 'C4', 'F4']),
    # panic: everything over a C pedal
    'Fm/C2': ('C2', ['Ab3', 'C4', 'F4']),
    'Db/C': ('C2', ['Ab3', 'Db4', 'F4']),
    'Bbm/C': ('C2', ['Bb3', 'Db4', 'F4']),
    'C7b9': ('C2', ['Bb3', 'Db4', 'E4', 'G4']),
    # morning
    'Db/F': ('F1', ['F3', 'Ab3', 'Db4']),
    'Bbm/F': ('F1', ['F3', 'Bb3', 'Db4']),
    'Bbm6/F': ('F1', ['F3', 'G3', 'Bb3', 'Db4']),
    'F': ('F1', ['F3', 'A3', 'C4', 'F4']),
}

PROG_INTRO = ['Fm9', 'Fm9', 'Dbmaj9', 'Dbmaj9', 'Fm9', 'Fm9', 'Dbmaj9', ('C7sus4', 'C7')]
PROG_LAMENT = ['Fm', 'C/E', 'Fm/Eb', 'Bb/D', 'Bbm/Db', 'Fm/C', ('C7sus4', 'C7'), 'Fm/F1']
PROG_PANIC = ['Fm/C2', 'Db/C', 'Bbm/C', 'C7b9'] * 2
PROG_DROP = ['Dbmaj9', 'Eb6', 'Cm7', 'Fm9', 'Dbmaj9', 'Eb6', 'Fsus4', 'Fadd9']
PROG_BREAK = ['Fm', 'C/E', 'Fm/Eb', 'Bb/D', 'Bbm/Db', 'Fm/C', 'C7sus4', 'C7']
PROG_TAG = ['Dbmaj9', 'Eb6', 'Fsus4', 'Fadd9']
PROG_OUTRO = ['Fadd9', 'Db/F', 'Fadd9', 'Db/F', 'Bbm/F', 'Fadd9', 'Bbm6/F', 'F']


def chord_events(prog, start_bar):
    """-> list of (t0, dur, chord_name) in absolute time."""
    ev = []
    for i, c in enumerate(prog):
        b = start_bar + i
        if isinstance(c, tuple):
            ev.append((T(b), 2 * BEAT, c[0]))
            ev.append((T(b, 2), 2 * BEAT, c[1]))
        else:
            ev.append((T(b), BAR, c))
    return ev


# --------------------------------------------------------------------------
# Melodies: (bar within phrase (1-based), beat, beats, note, vowel)
# --------------------------------------------------------------------------

MEL_DROP = [
    (1, 0, 1.5, 'Ab4', 'a'), (1, 1.5, 0.5, 'Bb4', 'a'), (1, 2, 1.75, 'C5', 'a'),
    (2, 0, 1.5, 'Bb4', 'a'), (2, 1.5, 0.5, 'C5', 'a'), (2, 2, 1.75, 'Db5', 'o'),
    (3, 0, 1.5, 'C5', 'a'), (3, 1.5, 0.5, 'Db5', 'a'), (3, 2, 1.75, 'Eb5', 'e'),
    (4, 0, 1.5, 'F5', 'a'), (4, 1.5, 0.5, 'Eb5', 'a'), (4, 2, 1.5, 'C5', 'o'),
    (5, 0, 1.5, 'F5', 'a'), (5, 1.5, 0.5, 'Eb5', 'a'), (5, 2, 1.0, 'Db5', 'a'), (5, 3, 0.9, 'C5', 'o'),
    (6, 0, 1.5, 'Eb5', 'a'), (6, 1.5, 0.5, 'Db5', 'a'), (6, 2, 1.0, 'C5', 'a'), (6, 3, 0.9, 'Bb4', 'o'),
    (7, 0, 1.0, 'C5', 'a'), (7, 1, 3.0, 'Bb4', 'a'),
    (8, 0, 3.5, 'A4', 'a'),
]

MEL_V1 = [
    (1, 1, 0.5, 'F4', 'o'), (1, 1.5, 0.5, 'Ab4', 'a'), (1, 2, 2.0, 'C5', 'a'),
    (2, 0, 1.0, 'Db5', 'a'), (2, 1, 1.0, 'C5', 'a'), (2, 2, 0.5, 'Bb4', 'a'), (2, 2.5, 1.25, 'G4', 'o'),
    (3, 0, 1.5, 'Ab4', 'a'), (3, 1.5, 0.5, 'G4', 'a'), (3, 2, 1.75, 'F4', 'o'),
    (4, 0, 0.5, 'F4', 'a'), (4, 0.5, 0.5, 'Bb4', 'a'), (4, 1, 2.0, 'D5', 'e'), (4, 3, 0.9, 'C5', 'o'),
    (5, 0, 2.5, 'Db5', 'a'), (5, 2.5, 0.5, 'C5', 'a'), (5, 3, 0.9, 'Bb4', 'o'),
    (6, 0, 1.5, 'C5', 'a'), (6, 1.5, 0.5, 'Ab4', 'a'), (6, 2, 1.75, 'F4', 'o'),
    (7, 0, 2.0, 'F4', 'a'), (7, 2, 1.0, 'E4', 'e'), (7, 3, 0.9, 'G4', 'o'),
    (8, 0, 3.0, 'Ab4', 'a'),
]

MEL_V2 = MEL_V1[:13] + [
    (5, 0, 1.5, 'F5', 'a'), (5, 1.5, 0.5, 'Eb5', 'a'), (5, 2, 1.75, 'Db5', 'o'),
    (6, 0, 1.0, 'C5', 'a'), (6, 1, 0.5, 'Db5', 'a'), (6, 1.5, 0.5, 'C5', 'a'), (6, 2, 1.75, 'Ab4', 'o'),
    (7, 0, 1.0, 'Bb4', 'a'), (7, 1, 0.5, 'Ab4', 'a'), (7, 1.5, 0.5, 'G4', 'a'),
    (7, 2, 1.0, 'E4', 'e'), (7, 3, 0.9, 'G4', 'o'),
    (8, 0, 3.5, 'F4', 'o'),
]

MEL_BREAK = [
    (5, 0, 3.5, 'Db5', 'a'),
    (6, 0, 1.75, 'C5', 'a'), (6, 2, 1.75, 'Eb5', 'a'),
    (7, 0, 3.75, 'F5', 'a'),
    (8, 0, 2.5, 'E5', 'e'),
]

MEL_TAG = [
    (1, 0, 1.5, 'F5', 'a'), (1, 1.5, 0.5, 'Eb5', 'a'), (1, 2, 1.0, 'Db5', 'a'), (1, 3, 0.9, 'C5', 'o'),
    (2, 0, 1.5, 'Eb5', 'a'), (2, 1.5, 0.5, 'Db5', 'a'), (2, 2, 1.0, 'C5', 'a'), (2, 3, 0.9, 'Bb4', 'o'),
    (3, 0, 1.0, 'C5', 'a'), (3, 1, 3.0, 'Bb4', 'a'),
    (4, 0, 4.0, 'A4', 'a'),
]

# the "hope" motif on the music box: minor at the start, major at the end
BELL_INTRO = [(5, 0, 1.5, 'Ab5'), (5, 1.5, 0.5, 'Bb5'), (5, 2, 2.0, 'C6'),
              (7, 0, 1.5, 'Ab5'), (7, 1.5, 0.5, 'Bb5'), (7, 2, 1.0, 'Db6'), (7, 3, 1.0, 'C6')]
BELL_OUTRO = [(1, 0, 1.5, 'A5'), (1, 1.5, 0.5, 'Bb5'), (1, 2, 2.0, 'C6'),
              (2, 0, 1.5, 'Db6'), (2, 1.5, 0.5, 'C6'), (2, 2, 2.0, 'Ab5'),
              (3, 0, 1.5, 'A5'), (3, 1.5, 0.5, 'G5'), (3, 2, 2.0, 'F5'),
              (4, 0, 4.0, 'F5'),
              (5, 0, 2.0, 'Db6'), (5, 2, 2.0, 'C6'),
              (6, 0, 4.0, 'A5'),
              (7, 0, 2.0, 'G5'), (7, 2, 2.0, 'Bb5'),
              (8, 0, 1.0, 'F5'), (8, 0.5, 1.0, 'A5'), (8, 1.0, 1.0, 'C6'), (8, 1.5, 3.0, 'F6')]

# cowbell riff in C Phrygian dominant (the Hicaz colour): 2 bars of 16ths
COWBELL = [
    (0, 'C5'), (2, 'C5'), (3, 'Db5'), (4, 'E5'), (6, 'F5'), (7, 'E5'), (8, 'Db5'),
    (10, 'C5'), (11, 'Db5'), (12, 'E5'), (14, 'Db5'),
    (16, 'C5'), (18, 'C5'), (19, 'Db5'), (20, 'E5'), (22, 'G5'), (23, 'F5'), (24, 'E5'),
    (26, 'Db5'), (28, 'C5'), (29, 'Bb4'), (30, 'C5'),
]


def mel_events(mel, start_bar, transpose=0, dur_scale=1.0):
    return [(T(start_bar + b - 1, bt), d * BEAT * dur_scale, midi(nt) + transpose, v)
            for (b, bt, d, nt, v) in mel]


# --------------------------------------------------------------------------
# Mixer
# --------------------------------------------------------------------------

class Mix:
    """A time window of the song with named stereo buses."""

    def __init__(self, t0, t1, tail=6.0):
        self.t0, self.t1 = t0, t1
        self.n = nsamp(t1 - t0 + tail)
        self.bus = {}
        self.kicks = []

    def owns(self, t):
        return self.t0 - 1e-6 <= t < self.t1 - 1e-6

    def add(self, name, x, t, gain=1.0, pan=0.0, sends=None, force=False):
        if not force and not self.owns(t):
            return
        if x.ndim == 1:
            x = S.pan(x, pan)
        s = nsamp(t - self.t0)
        if s < 0:  # starts before this window: keep only the part inside it
            x, s = x[:, -s:], 0
        if s >= self.n or x.shape[1] == 0:
            return
        m = min(x.shape[1], self.n - s)
        for b, g in [(name, gain)] + list((sends or {}).items()):
            if b not in self.bus:
                self.bus[b] = np.zeros((2, self.n))
            self.bus[b][:, s:s + m] += x[:, :m] * (gain if b == name else gain * g)


def build(mix):
    """Place every note of the song into `mix` (events outside its window
    are ignored by Mix.add)."""
    rng = np.random.default_rng(99)

    def hum(v=0.08):
        return 1.0 + rng.uniform(-v, v)

    def jit(ms=3.0):
        return rng.uniform(-ms, ms) * 1e-3

    # ---------------------------------------------------------------- kick
    def kick_at(t, vel=1.0, kind='house', sc=True):
        if kind == 'house':
            x = I.kick(vel)
        elif kind == 'soft':
            x = I.kick(vel, decay=0.22, punch=120.0, click=0.1, drive=1.3)
        else:  # phonk: short, knocking, leaves room for the 808
            x = I.kick(vel, decay=0.16, punch=190.0, click=0.3, drive=2.2)
        mix.add('kick', x, t, 1.0)
        if mix.owns(t) and sc:
            mix.kicks.append((t, 1.0 if kind == 'house' else 0.35))

    # ---------------------------------------------------------------- pads
    def pads(prog_ev, cut, vel=1.0, attack=0.35, release=1.1, detune=0.16,
             octave=0, hall=0.35, seed=0, bus='pads'):
        for i, (t0, d, c) in enumerate(prog_ev):
            if not mix.owns(t0):
                continue
            notes = [midi(n) + 12 * octave for n in CH[c][1]]
            x = I.supersaw(notes, d, attack=attack, release=release,
                           cutoff=(lambda tt, t0=t0: cut(t0 + tt)), detune=detune,
                           vel=vel, seed=seed + i)
            mix.add(bus, x, t0, 1.0, sends={'hall': hall})

    def choir_part(prog_ev, vel=1.0, octave=0, top=None, hall=0.5, vowel='a'):
        for i, (t0, d, c) in enumerate(prog_ev):
            if not mix.owns(t0):
                continue
            notes = [midi(n) + 12 * octave for n in CH[c][1]]
            if top is not None and i == 0:
                notes = notes + [midi(top)]
            x = I.choir(notes, d, vowel=vowel, vel=vel, seed=500 + i)
            mix.add('choir', x, t0, 1.0, sends={'hall': hall})

    def ep_part(prog_ev, vel=0.75, rhythm=((0, 2.0, 1.0), (2.5, 1.5, 0.75)), hall=0.3):
        for (t0, d, c) in prog_ev:
            if not mix.owns(t0):
                continue
            notes = CH[c][1]
            for (b, dd, v) in rhythm:
                if b * BEAT >= d - 1e-6:
                    continue
                for k, n in enumerate(notes):
                    x = I.ep(n, min(dd * BEAT, d - b * BEAT), vel * v * hum(0.06))
                    mix.add('keys', x, t0 + b * BEAT + k * 0.012 + jit(2), 0.9,
                            pan=(-0.25 + 0.5 * k / max(1, len(notes) - 1)),
                            sends={'hall': hall})

    def bells(notes_, start_bar, vel=0.6, transpose=0, hall=0.55, delay=0.25):
        for (b, bt, d, nt) in notes_:
            if not mix.owns(T(start_bar + b - 1, bt)):
                continue
            x = I.bell(midi(nt) + transpose, vel * hum(0.1), length=max(2.0, d * BEAT + 1.5))
            mix.add('keys', x, T(start_bar + b - 1, bt), 0.8, pan=rng.uniform(-0.3, 0.3),
                    sends={'hall': hall, 'delay': delay})

    # ------------------------------------------------------------- lead
    def lead(mel_ev, bus='lead', gain=1.0, hall=0.3, delay=0.22, **kw):
        if not mel_ev:
            return
        t0 = min(e[0] for e in mel_ev)
        t1 = max(e[0] + e[1] for e in mel_ev)
        if not (mix.owns(t0) or mix.owns(t1 - 1e-3)):
            return
        ev = [(e[0] - t0, e[1], e[2], e[3]) for e in mel_ev]
        x = I.voice_line(ev, t1 - t0 + 1.2, **kw)
        mix.add(bus, x, t0, gain, sends={'hall': hall, 'delay': delay}, force=True)

    # ------------------------------------------------------------- bass
    def sub_part(prog_ev, vel=0.9):
        for (t0, d, c) in prog_ev:
            if not mix.owns(t0):
                continue
            mix.add('bass', I.sub(CH[c][0], d - 0.02, vel), t0)

    def b808(notes_, t0, vel=1.0, tone=2600.0):
        """notes_: (t_abs, dur_s, note, slide)."""
        if not notes_:
            return
        start = notes_[0][0]
        if not mix.owns(start):
            return
        ev = [(t - start, d, n, sl) for (t, d, n, sl) in notes_]
        length = ev[-1][0] + ev[-1][1] + 0.2
        mix.add('bass', I.bass808(ev, length, tone=tone) * vel, start, force=True)

    def funk_part(prog_ev, vel=1.0, peak=1500.0, pattern=None):
        pattern = pattern or [(2, 2, 0), (6, 2, 0), (10, 1, 0), (11, 1, 12), (14, 2, 0)]
        for (t0, d, c) in prog_ev:
            if not mix.owns(t0):
                continue
            root = midi(CH[c][0])
            for (st, ln, oct_) in pattern:
                if st * STEP >= d - 1e-6:
                    continue
                x = I.funk_bass(root + oct_, ln * STEP * 0.92, vel * hum(0.05), peak=peak)
                mix.add('bass', x, t0 + st * STEP, 1.0)

    # ------------------------------------------------------------- arp
    def arp(prog_ev, octave=1, vel=0.7, peak=3000.0, pattern=(0, 1, 2, 3, 2, 1),
            every=1, delay=0.3, hall=0.15, span=2):
        k = 0
        for (t0, d, c) in prog_ev:
            if not mix.owns(t0):
                k += int(round(d / STEP)) // every
                continue
            tones = sorted(midi(n) + 12 * octave for n in CH[c][1])
            pool = tones + [x + 12 for x in tones][:span]
            steps = int(round(d / STEP))
            for st in range(0, steps, every):
                nt = pool[pattern[k % len(pattern)] % len(pool)]
                k += 1
                v = vel * (1.0 if st % 4 == 0 else 0.8) * hum(0.06)
                x = I.pluck(nt, STEP * every * 0.85, v, peak=peak)
                mix.add('arp', x, t0 + st * STEP, 1.0, pan=0.35 * np.sin(k * 0.9),
                        sends={'delay': delay, 'hall': hall})

    # ------------------------------------------------------------- drums
    def house_bar(b, open_hat=True, clap_=True, shaker_=True, kick_=True, vel=1.0,
                  tamb=False):
        if not mix.owns(T(b)):
            return
        for q in range(4):
            if kick_:
                kick_at(T(b, q), vel)
        if clap_:
            for q in (1, 3):
                mix.add('drums', I.clap(0.9 * vel * hum()), T(b, q) + jit(2), 0.8,
                        sends={'room': 0.25, 'hall': 0.08})
                mix.add('drums', I.snare(0.5 * vel), T(b, q), 0.45, sends={'room': 0.2})
        if open_hat:
            for q in range(4):
                mix.add('drums', I.hat(0.6 * vel * hum(), open_=True, decay=0.16),
                        T(b, q + 0.5) + jit(2), 0.5, pan=0.2, sends={'room': 0.1})
        if shaker_:
            for s in range(16):
                acc = (0.55, 0.3, 0.8, 0.35)[s % 4]
                sw = 0.018 if s % 2 else 0.0
                mix.add('drums', I.shaker(acc * vel * hum(0.12)), T(b) + s * STEP + sw * BEAT,
                        0.35, pan=-0.3)
        if tamb:
            for s in range(2, 16, 4):
                mix.add('drums', I.hat(0.45 * vel * hum(), decay=0.06), T(b) + s * STEP,
                        0.35, pan=0.45, sends={'room': 0.1})

    def halftime_bar(b, vel=1.0, hats16=False, roll=False, snare_vel=1.0, kick_steps=(0, 11)):
        if not mix.owns(T(b)):
            return
        for st in kick_steps:
            kick_at(T(b) + st * STEP, vel * (1.0 if st == 0 else 0.8), kind='soft')
        mix.add('drums', I.snare(0.9 * snare_vel), T(b, 2), 0.8, sends={'room': 0.3, 'hall': 0.25})
        mix.add('drums', I.clap(0.7 * snare_vel), T(b, 2) + 0.004, 0.55, sends={'hall': 0.3})
        step = 1 if hats16 else 2
        for s in range(0, 16, step):
            if roll and s >= 12:
                continue
            v = (0.7 if s % 4 == 0 else 0.45) * hum(0.15)
            mix.add('drums', I.hat(v * vel), T(b) + s * STEP + jit(3), 0.42, pan=0.25,
                    sends={'room': 0.08})
        if roll:  # trap triplet roll into the next bar
            for k in range(9):
                t = T(b, 3) + k * (BEAT / 9)
                mix.add('drums', I.hat((0.35 + 0.05 * k) * vel), t, 0.42, pan=0.25)

    def phonk_bar(b, vel=1.0, roll=False):
        if not mix.owns(T(b)):
            return
        for st in (0, 6, 10):
            kick_at(T(b) + st * STEP, vel, kind='phonk', sc=False)
        for q in (1, 3):
            mix.add('drums', I.snare(0.95 * vel, tone=200.0, bright=1.2), T(b, q), 0.85,
                    sends={'room': 0.25})
            mix.add('drums', I.clap(0.8 * vel), T(b, q) + 0.003, 0.6, sends={'room': 0.2})
        for s in range(16):
            if roll and s in (14, 15):
                for k in range(2):
                    mix.add('drums', I.hat(0.4 * vel, dark=True), T(b) + (s + k / 2) * STEP,
                            0.4, pan=0.3)
                continue
            v = (0.75 if s % 2 == 0 else 0.45) * hum(0.12)
            mix.add('drums', I.hat(v * vel, dark=True), T(b) + s * STEP + jit(2), 0.45, pan=0.3)

    def snare_roll(b0, bars, end_beat=4.0, vel0=0.25, vel1=1.0, pitch_up=True, start_beat=0.0):
        """8ths -> 16ths -> 32nds, rising in level and pitch."""
        t_start, t_end = T(b0, start_beat), T(b0 + bars - 1, end_beat)
        t = t_start
        while t < t_end - 1e-6:
            u = (t - t_start) / (t_end - t_start)
            div = 2 if u < 0.4 else (4 if u < 0.75 else 8)
            v = vel0 + (vel1 - vel0) * u ** 1.3
            tone = 190.0 * (2 ** (u * 0.7) if pitch_up else 1.0)
            if mix.owns(t):
                mix.add('drums', I.snare(v, tone=tone, noise_decay=0.08), t, 0.7,
                        sends={'room': 0.2, 'hall': 0.1})
            t += BEAT / div

    def crash_at(t, vel=1.0):
        if mix.owns(t):
            mix.add('drums', I.crash(vel), t, 0.45, sends={'hall': 0.2})

    def light(b, vel=1.0):
        """F major arrives (the song's first A-natural): a cymbal breathes in
        and the music box answers with the new colour."""
        if not mix.owns(T(b)):
            return
        rc = I.crash(0.8, length=BAR)[:, ::-1]
        rc *= np.linspace(0, 1, rc.shape[1])[None, :] ** 3
        mix.add('fx', rc, T(b) - rc.shape[1] / SR, 0.3 * vel, sends={'hall': 0.3}, force=True)
        for k, nt in enumerate(('F5', 'A5', 'C6', 'F6', 'A6')):
            mix.add('keys', I.bell(nt, 0.45 * vel * hum(0.1)), T(b, 0.5 * k), 0.8,
                    pan=-0.5 + 0.25 * k, sends={'hall': 0.5, 'delay': 0.3})

    def heart(b0, bars, every_beats=2.0, vel=1.0, fade_to=None):
        t, t_end = T(b0), T(b0 + bars)
        while t < t_end - 1e-6:
            u = (t - T(b0)) / (t_end - T(b0))
            v = vel if fade_to is None else vel + (fade_to - vel) * u
            gap = 0.2 if every_beats >= 2 else 0.15
            if mix.owns(t):
                mix.add('fx', I.heartbeat(v, gap), t, 0.9, sends={'hall': 0.12})
            t += every_beats * BEAT

    def vinyl_part(b0, bars, gain, extra=0.0, fade_in=0.0):
        if mix.owns(T(b0)):
            v = I.vinyl(bars * BAR + extra, seed=b0)
            if fade_in:
                k = nsamp(fade_in)
                v[:, :k] *= np.linspace(0, 1, k)[None, :] ** 2
            mix.add('vinyl', v, T(b0), gain)

    vinyl_part(1, 8, 1.0, fade_in=2.5)
    for (b0, bars, g) in ((9, 16, 0.55), (25, 8, 0.25), (49, 8, 0.7), (73, 4, 0.35)):
        vinyl_part(b0, bars, g)
    vinyl_part(77, 8, 1.0, extra=TAIL)

    # ====================================================================
    # 1. NABIZ  (bars 1-8)
    # ====================================================================
    ev = chord_events(PROG_INTRO, 1)

    def intro_cut(t):
        u = np.clip(t / T(9), 0, 1)
        return 260.0 * (2600.0 / 260.0) ** (u ** 1.3)
    pads(ev, intro_cut, vel=0.8, attack=1.2, release=1.6, hall=0.55, seed=10)
    heart(1, 8, 2.0, 0.9)
    bells(BELL_INTRO, 1, vel=0.55)
    for k in range(18):
        t = T(1) + rng.uniform(0.5, T(9) - 1.0)
        nt = rng.choice(['F6', 'Ab6', 'C7', 'Eb6', 'Bb6', 'C6'])
        mix.add('fx', I.blip(nt, 0.25 * rng.uniform(0.4, 1.0)), t, 0.5,
                pan=rng.uniform(-0.8, 0.8), sends={'delay': 0.5, 'hall': 0.4})
    rc = I.crash(0.7)[:, ::-1] if mix.owns(T(8)) else np.zeros((2, 10))
    mix.add('fx', rc * np.linspace(0, 1, rc.shape[1]) ** 2, T(9) - rc.shape[1] / SR, 0.35,
            sends={'hall': 0.3})

    # ====================================================================
    # 2. TEK BAŞINA  (bars 9-24): lament x2
    # ====================================================================
    ev1 = chord_events(PROG_LAMENT, 9)
    ev2 = chord_events(PROG_LAMENT, 17)
    mix.add('fx', I.boom(0.6), T(9), 0.6, sends={'hall': 0.2})
    heart(9, 2, 2.0, 0.6, fade_to=0.2)
    ep_part(ev1, vel=0.7)
    pads(ev1, lambda t: 1400.0, vel=0.45, attack=0.8, release=1.2, hall=0.4, seed=40)
    sub_part(ev1, 0.42)
    lead(mel_events(MEL_V1, 9), gain=0.85, hall=0.38, delay=0.2, seed=1)
    for b in range(13, 17):
        halftime_bar(b, vel=0.75, snare_vel=0.7, kick_steps=(0,) if b < 15 else (0, 11))

    ep_part(ev2, vel=0.8)
    pads(ev2, lambda t: 2400.0, vel=0.6, attack=0.5, release=1.2, hall=0.4, seed=60)
    # 808 walks the lament down, sliding into every new bass note
    n808 = []
    for i, (t0, d, c) in enumerate(ev2):
        note = CH[c][0]
        slide = i > 0
        n808.append((t0, 1.75 * BEAT if d > 2 * BEAT else d * 0.9, note, slide))
        if d > 2 * BEAT:
            n808.append((t0 + 2.75 * BEAT, 1.25 * BEAT, note, False))
    b808(n808, T(17), vel=0.6)
    lead(mel_events(MEL_V2, 17), gain=0.85, hall=0.38, delay=0.22, seed=2)
    bells([(b, bt, d, nt) for (b, bt, d, nt, v) in MEL_V2], 17, vel=0.22, transpose=12,
          hall=0.5, delay=0.15)
    for b in range(17, 25):
        halftime_bar(b, vel=0.95, hats16=True, roll=(b % 4 == 0), snare_vel=0.95,
                     kick_steps=(0, 6, 11))
    heart(23, 2, 1.0, 0.25, fade_to=0.8)

    # ====================================================================
    # 3. PANİK  (bars 25-32)
    # ====================================================================
    ev = chord_events(PROG_PANIC, 25)
    pads(ev, lambda t: 900.0 * (5.0 ** np.clip((t - T(25)) / (8 * BAR), 0, 1)),
         vel=0.55, attack=0.05, release=0.6, detune=0.22, hall=0.3, seed=80)
    for b in range(25, 33):
        phonk_bar(b, vel=0.95, roll=(b % 2 == 0))
        for (st, nt) in COWBELL:
            if (b - 25) % 2 != st // 16:
                continue
            t = T(b) + (st % 16) * STEP
            if b == 32 and t >= STOP_AT:
                continue
            mix.add('perc', I.cowbell(hz(nt), 0.8 * hum(0.1)), t, 0.8,
                    pan=0.15, sends={'room': 0.15, 'delay': 0.08})
    n808 = []
    for b in range(25, 33):
        pat = [(0, 6, 'C2', False), (6, 4, 'C2', False), (10, 4, 'Db2', True), (14, 2, 'Bb1', True)]
        if b % 4 == 0:
            pat = [(0, 6, 'C2', False), (6, 4, 'C2', False), (10, 2, 'E2', True), (12, 4, 'C2', True)]
        for (st, ln, nt, sl) in pat:
            n808.append((T(b) + st * STEP, ln * STEP, nt, sl))
    b808(n808, T(25), vel=0.72, tone=3200.0)
    arp_ev = [(t0, d, c) for (t0, d, c) in ev]
    arp(arp_ev[:4], octave=0, vel=0.55, peak=1800.0, pattern=(0, 1, 2, 3), delay=0.25)
    arp(arp_ev[4:], octave=1, vel=0.7, peak=3200.0, pattern=(0, 1, 2, 3), delay=0.25)
    heart(25, 8, 1.0, 0.7)
    mix.add('fx', I.riser(4 * BAR - 1.5 * BEAT, seed=3), T(29), 0.5)
    snare_roll(31, 2, end_beat=2.5, vel0=0.2, vel1=0.9)

    # ====================================================================
    # 4. BİR GÜN DAHA  (bars 33-48)
    # ====================================================================
    ev = chord_events(PROG_DROP * 2, 33)
    crash_at(T(33))
    crash_at(T(41), 0.8)
    mix.add('fx', I.boom(1.0), T(33), 0.8, sends={'hall': 0.15})
    pads(ev, lambda t: 6500.0, vel=1.2, attack=0.03, release=0.5, hall=0.18, seed=100)
    funk_part(ev, vel=1.0)
    lead(mel_events(MEL_DROP, 33), gain=1.0, hall=0.22, delay=0.22, seed=3)
    lead(mel_events(MEL_DROP, 41), gain=1.0, hall=0.22, delay=0.22, seed=4)
    arp(ev[:8], octave=2, vel=0.45, peak=1600.0, pattern=(0, 2, 1, 3, 2, 4), delay=0.3)
    arp(ev[8:], octave=2, vel=0.6, peak=2600.0, pattern=(0, 2, 1, 3, 2, 4), delay=0.3)
    bells([(b, bt, d, nt) for (b, bt, d, nt, v) in MEL_DROP], 41, vel=0.25, transpose=12,
          hall=0.4, delay=0.2)
    for b in range(33, 49):
        house_bar(b, vel=1.0)
    light(40, 0.8)
    light(48, 1.0)

    # ====================================================================
    # 5. NEFES  (bars 49-56)
    # ====================================================================
    ev = chord_events(PROG_BREAK, 49)
    mix.add('fx', I.downlifter(2 * BAR, seed=4), T(49), 0.35, sends={'hall': 0.3})
    crash_at(T(49), 0.6)
    pads(ev, lambda t: 1600.0 + 2400.0 * np.clip((t - T(53)) / (4 * BAR), 0, 1) ** 2,
         vel=0.7, attack=0.6, release=1.4, hall=0.55, seed=140)
    ep_part(ev[:4], vel=0.6, rhythm=((0, 3.5, 1.0),))
    bells([(b, bt, d, nt) for (b, bt, d, nt, v) in MEL_V1 if b <= 4], 49, vel=0.6,
          transpose=12, hall=0.65, delay=0.3)
    sub_part(ev[:6], 0.35)
    choir_part(ev[4:], vel=0.55, hall=0.6)
    lead(mel_events(MEL_BREAK, 49), gain=0.9, hall=0.45, delay=0.25, seed=5)
    for b in range(53, 57):
        for q in range(4):
            if b == 56 and q == 3:
                continue
            v = 0.55 + 0.45 * (b - 53 + q / 4) / 4
            mix.add('buildkick', I.kick(v), T(b, q), 1.0)
            if mix.owns(T(b, q)):
                mix.kicks.append((T(b, q), 0.6))
    funk_part(chord_events(PROG_BREAK[6:], 55), vel=0.8, peak=900.0)
    mix.add('fx', I.riser(4 * BAR - BEAT, seed=6), T(53), 0.55)
    snare_roll(55, 2, end_beat=3.0, vel0=0.2, vel1=1.0)

    # the breath: the drop's first chord, reverb-only and reversed
    if mix.owns(GASP_AT):
        dry = I.choir([midi(n) for n in CH['Dbmaj9'][1]] + [midi('F5')], BEAT * 0.5,
                      vel=1.0, attack=0.01, release=0.2, seed=7)
        ir = S.make_ir(seconds=2.2, t60=1.6, seed=8)
        wet = S.reverb(np.pad(dry, ((0, 0), (0, ir.shape[1]))), ir)
        wet = wet[:, :nsamp(BEAT * 1.0)][:, ::-1]
        wet *= np.linspace(0, 1, wet.shape[1])[None, :] ** 1.5
        mix.add('fx', wet / (np.max(np.abs(wet)) + 1e-9), T(57) - wet.shape[1] / SR, 0.5,
                force=True)

    # ====================================================================
    # 6. IŞIK  (bars 57-72)
    # ====================================================================
    ev = chord_events(PROG_DROP * 2, 57)
    crash_at(T(57), 1.0)
    crash_at(T(65), 0.9)
    mix.add('fx', I.boom(1.0), T(57), 0.85, sends={'hall': 0.15})
    pads(ev, lambda t: 8000.0, vel=1.2, attack=0.03, release=0.5, hall=0.18, seed=200)
    pads(ev, lambda t: 7000.0, vel=0.5, attack=0.05, release=0.6, hall=0.25, seed=220,
         octave=1)
    choir_part(ev[:8], vel=0.55, top='F5', octave=0, hall=0.5)
    choir_part(ev[8:], vel=0.65, octave=0, hall=0.5)
    funk_part(ev, vel=1.05, peak=1800.0)
    lead(mel_events(MEL_DROP, 57), gain=1.0, hall=0.22, delay=0.22, seed=6)
    lead(mel_events(MEL_DROP, 65), gain=1.0, hall=0.22, delay=0.22, seed=7)
    hi = [m for m in MEL_DROP if m[0] >= 5]
    lead(mel_events(hi, 57, transpose=12), bus='lead2', gain=0.5, hall=0.35, delay=0.3,
         formant=False, sub_oct=0.0, seed=8)
    lead(mel_events(MEL_DROP, 65, transpose=12), bus='lead2', gain=0.55, hall=0.35,
         delay=0.3, formant=False, sub_oct=0.0, seed=9)
    arp(ev, octave=2, vel=0.62, peak=3000.0, pattern=(0, 2, 1, 3, 2, 4), delay=0.3)
    bells([(b, bt, d, nt) for (b, bt, d, nt, v) in MEL_DROP], 65, vel=0.3, transpose=12,
          hall=0.4, delay=0.2)
    for b in range(57, 73):
        house_bar(b, vel=1.05, tamb=b >= 65)
    light(64, 1.0)
    light(72, 1.1)
    snare_roll(72, 1, end_beat=4.0, vel0=0.25, vel1=0.7, start_beat=2.0)

    # ====================================================================
    # 7. YAVAŞLA  (bars 73-76): half-time, slowed
    # ====================================================================
    ev = chord_events(PROG_TAG, 73)
    crash_at(T(73), 0.9)
    mix.add('fx', I.boom(0.8), T(73), 0.7, sends={'hall': 0.2})
    pads(ev, lambda t: 3200.0 - 1400.0 * np.clip((t - T(73)) / (4 * BAR), 0, 1),
         vel=0.8, attack=0.1, release=1.6, hall=0.5, seed=300)
    choir_part(ev, vel=0.6, hall=0.6)
    n808 = [(T(73), BAR, 'Db2', False), (T(74), BAR, 'Eb2', True),
            (T(75), BAR, 'F2', True), (T(76), 3.9 * BEAT, 'F1', True)]
    b808(n808, T(73), vel=0.6)
    lead(mel_events(MEL_TAG, 73), gain=1.0, hall=0.5, delay=0.3, seed=10)
    lead(mel_events(MEL_TAG[-4:], 73, transpose=12), bus='lead2', gain=0.4, hall=0.5,
         delay=0.3, formant=False, sub_oct=0.0, seed=11)
    for b in range(73, 77):
        halftime_bar(b, vel=0.9, hats16=False, snare_vel=1.0, kick_steps=(0, 10))
    light(76, 0.9)

    # ====================================================================
    # 8. SABAH  (bars 77-84)
    # ====================================================================
    ev = chord_events(PROG_OUTRO, 77)
    last = ev[-1]
    ev[-1] = (last[0], last[1] + 3.0, last[2])
    pads(ev, lambda t: 2200.0 * (0.35 ** np.clip((t - T(77)) / (9 * BAR), 0, 1)),
         vel=0.7, attack=0.8, release=2.5, hall=0.6, seed=400)
    choir_part(ev[:4], vel=0.35, hall=0.7, vowel='o')
    ep_part(ev, vel=0.55, rhythm=((0, 3.8, 1.0),))
    bells(BELL_OUTRO, 77, vel=0.55, hall=0.6, delay=0.3)
    sub_part(ev, 0.3)
    heart(81, 4, 2.0, 0.5, fade_to=0.15)
    for k in range(14):
        t = T(77) + rng.uniform(0.5, 8 * BAR)
        nt = rng.choice(['F6', 'A6', 'C7', 'G6', 'C6'])
        mix.add('fx', I.blip(nt, 0.2 * rng.uniform(0.4, 1.0)), t, 0.5,
                pan=rng.uniform(-0.8, 0.8), sends={'delay': 0.5, 'hall': 0.4})


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

LEVELS = {  # bus faders (dB)
    'kick': -3.0, 'buildkick': -6.0, 'drums': 0.5, 'perc': 0.0, 'bass': -4.5,
    'pads': -7.5, 'choir': -8.0, 'keys': -10.0, 'lead': -5.0, 'lead2': -9.0,
    'arp': 0.0, 'fx': -9.0, 'vinyl': -1.0, 'hall': -10.0, 'room': -12.0, 'delay': -6.0,
}

DUCK = {  # sidechain depth per bus (0..1)
    'bass': 0.85, 'pads': 0.6, 'choir': 0.45, 'arp': 0.6, 'keys': 0.25, 'hall': 0.45,
    'delay': 0.3, 'lead': 0.12, 'lead2': 0.2,
}


def sidechain(kicks, t0, n, release=0.8 * BEAT):
    """Envelope in [0, 1]: 1 right on a kick, recovering over `release`."""
    duck = np.zeros(n)
    r = nsamp(release)
    pre = nsamp(0.004)
    shape = np.concatenate([np.linspace(0, 1, pre, endpoint=False),
                            (1 - np.linspace(0, 1, r)) ** 2])
    for k, w in kicks:
        s = nsamp(k - t0) - pre
        a, b = max(0, s), min(n, s + shape.shape[0])
        if b > a:
            duck[a:b] = np.maximum(duck[a:b], w * shape[a - s:b - s])
    return duck


def render_window(t0, t1, tail):
    mix = Mix(t0, t1, tail)
    build(mix)
    n = mix.n
    B = mix.bus
    duck = sidechain(mix.kicks, t0, n)
    hall_ir = S.make_ir(seconds=5.0, t60=3.8, predelay=0.03, dark=1200.0, seed=1)
    room_ir = S.make_ir(seconds=1.4, t60=0.9, predelay=0.008, bright=11000.0,
                        dark=3000.0, seed=2)

    # --- bus processing
    if 'pads' in B:
        B['pads'] = S.chorus(S.eq(B['pads'], ('hp', 170, 0.7), ('peak', 350, 1.0, -2.5)),
                             mix=0.35)
    if 'choir' in B:
        B['choir'] = S.eq(B['choir'], ('hp', 200, 0.7), ('highshelf', 6000, 0.7, -3.0))
    if 'keys' in B:
        k = S.eq(B['keys'], ('hp', 110, 0.7), ('peak', 300, 1.0, -2.0))
        B['keys'] = S.chorus(k, mix=0.4, rate=0.5, depth_ms=1.6)
    for ln in ('lead', 'lead2'):
        if ln in B:
            B[ln] = S.eq(B[ln], ('hp', 170, 0.7), ('peak', 2600, 0.9, 1.0),
                         ('peak', 480, 1.2, -2.0), ('lp', 11000, 0.7))
            B[ln] = np.tanh(1.2 * B[ln]) / 1.2
    if 'bass' in B:
        B['bass'] = S.eq(B['bass'], ('hp', 28, 0.7), ('lp', 6000, 0.7))
    if 'arp' in B:
        B['arp'] = S.eq(B['arp'], ('hp', 260, 0.7))
    if 'perc' in B:
        B['perc'] = S.eq(B['perc'], ('hp', 350, 0.7))
    if 'drums' in B:
        B['drums'] = S.eq(B['drums'], ('hp', 90, 0.7))
    if 'buildkick' in B:  # filter-house: the kick comes up through a closed filter
        t = t0 + np.arange(n) / SR
        u = np.clip((t - T(53)) / (T(56, 3) - T(53)), 0, 1)
        B['buildkick'] = S.lp(B['buildkick'], 120.0 * (18000.0 / 120.0) ** (u ** 2.2), 0.9)

    # --- tape feel on the melodic material
    for seed, name in enumerate(('pads', 'keys', 'choir')):
        if name in B:
            B[name] = S.wow_flutter(B[name], seed=seed + 3)

    # --- sends
    wet = {}
    if 'hall' in B:
        h = S.eq(B['hall'], ('hp', 220, 0.7), ('lp', 7500, 0.7))
        wet['hall'] = S.reverb(h, hall_ir)
    if 'room' in B:
        wet['room'] = S.reverb(S.eq(B['room'], ('hp', 250, 0.7)), room_ir)
    if 'delay' in B:
        d = S.pingpong(B['delay'], 0.75 * BEAT, feedback=0.5, lp_hz=4200.0, hp_hz=300.0)
        wet['delay'] = d
        # the delays get a little of the hall too
        wet['hall'] = wet.get('hall', 0) + 0.3 * S.reverb(d, hall_ir)

    stems = {k: v for k, v in B.items() if k not in ('hall', 'room', 'delay')}
    stems.update(wet)
    for name in stems:
        if name in DUCK:
            stems[name] = stems[name] * (1 - DUCK[name] * duck)[None, :]
    return stems


def render():
    """-> dict of full-length, pre-fader stereo stems."""
    t_start = time.time()
    n = nsamp(LENGTH)
    stems = {}

    def place(st, t0, cut=None):
        s0 = nsamp(t0)
        for name, v in st.items():
            m = min(v.shape[1], n - s0)
            y = v[:, :m].copy()
            if cut is not None:
                k, f = nsamp(cut - t0), nsamp(0.02)
                y[:, k:k + f] *= np.linspace(1, 0, f)[None, :]
                y[:, k + f:] = 0
            if name not in stems:
                stems[name] = np.zeros((2, n), dtype=np.float32)
            stems[name][:, s0:s0 + m] += y

    # window A: intro -> panic, ending in the tape-stop blackout
    sa = render_window(0.0, T(33), tail=6.0)
    for name, v in sa.items():
        sa[name] = S.tape_stop(v, STOP_AT, STOP_LEN)
    place(sa, 0.0)
    del sa
    # window B: first drop + breakdown, cut dead at the breath
    place(render_window(T(33), GASP_AT, tail=6.0), T(33), cut=GASP_AT)
    # window C: the breath onward
    place(render_window(GASP_AT, LENGTH, tail=0.5), GASP_AT)
    print(f'rendered in {time.time() - t_start:.1f}s')
    return stems


# A hand on the master fader: quiet, close verses; the drops open up.
RIDE = [
    (0.0, 0.0),
    (T(9) - 0.05, 0.0), (T(9), -3.5),        # alone: intimate
    (T(16), -3.5), (T(17), -2.0),           # second verse lifts
    (T(24), -2.0), (T(25), -2.0),           # panic climbs...
    (T(32, 2.5), -0.5), (T(33), 0.0),       # ...into the first drop
    (T(49) - 0.05, 0.0), (T(49), -3.5),     # breath: the light goes out
    (T(53), -3.5), (T(56, 3), -0.5),        # filter-house build
    (T(57), 0.8),                           # second drop, the biggest
    (T(73) - 0.05, 0.8), (T(73), 0.0),      # slowed coda
    (T(77) - 0.05, 0.0), (T(77), -1.5),     # morning
    (LENGTH, -1.5),
]


def ride(n):
    t = np.arange(n) / SR
    pts = np.array(RIDE)
    return db(np.interp(t, pts[:, 0], pts[:, 1]))


def mixdown(stems, levels=None):
    levels = levels or LEVELS
    n = next(iter(stems.values())).shape[1]
    out = np.zeros((2, n))
    for name, v in stems.items():
        out += v * db(levels.get(name, -12.0))
    return out * ride(n)[None, :]


def master(x):
    import pyloudnorm as pyln
    x = x * db(-16.0 - pyln.Meter(SR).integrated_loudness(x.T))
    x = S.eq(x, ('hp', 24, 0.7), ('lowshelf', 90, 0.7, 0.5), ('highshelf', 9500, 0.7, 2.0))
    x, gr = S.compress(x, thresh_db=-13.0, ratio=1.8, attack_ms=25.0, release_ms=220.0,
                       knee_db=8.0)
    x = S.softclip(x * db(2.0), 1.1) * db(-2.0)
    return x


def finish(x, target_lufs=-11.0, ceiling=-1.0):
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    for _ in range(5):
        y, g = S.limiter(x, ceiling_db=ceiling, lookahead_ms=5.0, release_ms=80.0)
        lufs = meter.integrated_loudness(y.T)
        if abs(lufs - target_lufs) < 0.1:
            break
        x = x * db(target_lufs - lufs)
    # make sure the song ends in true silence
    f = nsamp(2.5)
    y[:, -f:] *= np.linspace(1, 0, f)[None, :] ** 2
    return y, lufs, S.true_peak_db(y), g


def write_outputs(y, name='sinir-uclari'):
    import lameenc
    import soundfile as sf
    os.makedirs(OUT, exist_ok=True)
    y = np.concatenate([np.zeros((2, nsamp(LEAD_IN))), y], axis=1)
    wav = os.path.join(OUT, name + '.wav')
    sf.write(wav, y.T.astype(np.float32), SR, subtype='PCM_24')
    pcm = (np.clip(y.T, -1, 1) * 32767).astype(np.int16)
    enc = lameenc.Encoder()
    enc.set_bit_rate(256)
    enc.set_in_sample_rate(SR)
    enc.set_channels(2)
    enc.set_quality(2)
    mp3 = enc.encode(pcm.tobytes()) + enc.flush()
    path = os.path.join(OUT, name + '.mp3')
    with open(path, 'wb') as f:
        f.write(mp3)
    return wav, path


def sections_json():
    return [{'name': n, 'start': round(LEAD_IN + T(b), 3), 'end': round(LEAD_IN + T(b + k), 3)}
            for (n, b, k) in SECTIONS]


if __name__ == '__main__':
    import sys
    stem_dir = os.path.join(OUT, 'stems')
    os.makedirs(stem_dir, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == 'mix':
        stems = {f[:-4]: np.load(os.path.join(stem_dir, f))
                 for f in sorted(os.listdir(stem_dir)) if f.endswith('.npy')}
    else:
        stems = render()
        for f in os.listdir(stem_dir):
            os.remove(os.path.join(stem_dir, f))
        for name, v in stems.items():
            np.save(os.path.join(stem_dir, name + '.npy'), v.astype(np.float32))
    y, lufs, tp, g = finish(master(mixdown(stems)))
    wav, mp3 = write_outputs(y)
    with open(os.path.join(OUT, 'sections.json'), 'w') as f:
        json.dump({'bpm': BPM, 'length': LENGTH, 'sections': sections_json()}, f,
                  ensure_ascii=False, indent=1)
    print(f'LUFS {lufs:.2f}  true peak {tp:.2f} dBTP  max limiter GR '
          f'{20 * np.log10(g.min()):.1f} dB')
    print(wav, mp3)
