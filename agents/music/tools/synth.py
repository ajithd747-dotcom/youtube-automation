"""Small numpy synthesiser: pads, bass, plucks, bells, drums, risers, impacts, reverb. No samples or downloads needed.
All voices return float32 mono arrays at SR unless stated; `stereo()` spreads them.
"""
import numpy as np
from scipy import signal

SR = 44100
RNG = np.random.default_rng(7)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def t_axis(n):
    return np.arange(n) / SR


def adsr(n, a=0.01, d=0.1, s=0.7, r=0.1):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    a, d, r = min(a, n), min(d, max(n - a, 0)), min(r, n)
    env = np.ones(n) * s
    env[:a] = np.linspace(0, 1, a, endpoint=False) if a else env[:a]
    if d:
        env[a:a + d] = np.linspace(1, s, d)
    if r:
        env[n - r:] *= np.linspace(1, 0, r)
    return env


def saw(f, n):
    return 2 * ((t_axis(n) * f) % 1.0) - 1


def lp(x, fc, order=2):
    fc = min(fc, SR * 0.45)
    return signal.sosfilt(signal.butter(order, fc, "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, max(fc, 20), "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [max(lo, 20), min(hi, SR * 0.45)], "band", fs=SR, output="sos"), x)


def pad(midis, dur, cutoff=1800, voices=4, detune=0.007, attack=0.5, release=0.6):
    n = int(dur * SR)
    out = np.zeros(n)
    for m in midis:
        for v in range(voices):
            out += saw(hz(m) * (1 + detune * (v - (voices - 1) / 2)), n) * 0.5 / voices
    out = lp(out, cutoff, 2) * adsr(n, attack, 0.2, 0.85, release)
    return out / max(len(midis), 1) ** 0.5


def bass(midi, dur, cutoff=420, drive=1.6):
    n = int(dur * SR)
    x = saw(hz(midi), n) * 0.6 + np.sin(2 * np.pi * hz(midi) * t_axis(n)) * 0.7
    x = np.tanh(lp(x, cutoff, 2) * drive)
    return x * adsr(n, 0.005, 0.08, 0.7, 0.06)


def pluck(midi, dur, cutoff=3200, decay=0.22):
    n = int(dur * SR)
    x = saw(hz(midi), n) * 0.5 + saw(hz(midi) * 1.004, n) * 0.5
    return lp(x, cutoff, 2) * np.exp(-t_axis(n) / decay) * adsr(n, 0.002, 0.02, 1.0, 0.02)


def bell(midi, dur, index=2.5):
    n = int(dur * SR)
    t = t_axis(n)
    mod = np.sin(2 * np.pi * hz(midi) * 3.5 * t) * index * np.exp(-t / 0.5)
    return np.sin(2 * np.pi * hz(midi) * t + mod) * np.exp(-t / (dur * 0.5))


def kick(punch=1.0):
    n = int(0.42 * SR)
    t = t_axis(n)
    f = 45 + 110 * np.exp(-t / 0.035)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    x += RNG.standard_normal(n) * np.exp(-t / 0.004) * 0.25 * punch
    return np.tanh(x * 1.6)


def snare(tone=190):
    n = int(0.35 * SR)
    t = t_axis(n)
    noise = hp(RNG.standard_normal(n), 1400) * np.exp(-t / 0.09)
    body = np.sin(2 * np.pi * tone * t) * np.exp(-t / 0.05)
    return np.tanh((noise * 0.9 + body * 0.7) * 1.4)


def clap():
    n = int(0.3 * SR)
    t = t_axis(n)
    x = bp(RNG.standard_normal(n), 900, 3800)
    env = sum(np.exp(-np.clip(t - d, 0, None) / 0.03) * (t >= d) for d in (0, 0.012, 0.024)) * np.exp(-t / 0.12)
    return x * env * 0.9


def hat(open_=False):
    n = int((0.28 if open_ else 0.06) * SR)
    return hp(RNG.standard_normal(n), 7000) * np.exp(-t_axis(n) / (0.09 if open_ else 0.018)) * 0.5


def taiko(freq=70, dur=0.7):
    n = int(dur * SR)
    t = t_axis(n)
    f = freq * (1 + 0.6 * np.exp(-t / 0.05))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.28)
    x += hp(RNG.standard_normal(n), 400) * np.exp(-t / 0.02) * 0.4
    return np.tanh(x * 1.4)


def riser(dur, f0=300, f1=6000):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    noise = RNG.standard_normal(n)
    # filtered noise whose brightness rises (blockwise sweep) + rising tone
    out = np.zeros(n)
    blocks = 24
    for b in range(blocks):
        s, e = b * n // blocks, (b + 1) * n // blocks
        fc = f0 * (f1 / f0) ** (b / blocks)
        out[s:e] = bp(noise[s:e], fc * 0.6, fc * 1.4)[: e - s]
    tone = np.sin(2 * np.pi * np.cumsum(f0 * (f1 / f0) ** (t * 0.6)) / SR) * 0.15
    return (out * 0.9 + tone) * (t ** 2.2)


def impact(dur=2.4):
    n = int(dur * SR)
    t = t_axis(n)
    sub = np.sin(2 * np.pi * np.cumsum(38 + 90 * np.exp(-t / 0.12)) / SR) * np.exp(-t / 0.9)
    boom = lp(RNG.standard_normal(n), 900) * np.exp(-t / 0.35) * 0.9
    crack = hp(RNG.standard_normal(n), 2500) * np.exp(-t / 0.05) * 0.8
    return np.tanh((sub * 1.2 + boom + crack) * 1.3)


def reverb(x, decay=1.8, wet=0.25, pre=0.012):
    n = int(decay * SR)
    ir = RNG.standard_normal(n) * np.exp(-np.arange(n) / (SR * decay / 4.5))
    ir = lp(ir, 5500, 1)
    ir[: int(pre * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum()) + 1e-9
    wetsig = signal.fftconvolve(x, ir)[: len(x)]
    return x * (1 - wet) + wetsig * wet * 3.0


def place(master, x, t, gain=1.0, pan=0.0):
    """Add mono x into stereo master at time t (seconds); pan -1..1."""
    i = int(t * SR)
    if i >= master.shape[1] or i + len(x) <= 0:
        return
    s = max(0, -i)
    e = min(len(x), master.shape[1] - i)
    seg = x[s:e] * gain
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    master[0, i + s:i + e] += seg * l
    master[1, i + s:i + e] += seg * r
