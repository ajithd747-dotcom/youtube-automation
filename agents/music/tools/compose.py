"""Compose background music from a MusicPlan (tempo, key, intensity sections, hit cues). Deterministic for a given seed."""
import json
from dataclasses import asdict, dataclass, field

import numpy as np

import synth as S

SCALES = {"minor": [0, 2, 3, 5, 7, 8, 10], "major": [0, 2, 4, 5, 7, 9, 11], "dorian": [0, 2, 3, 5, 7, 9, 10], "phrygian": [0, 1, 3, 5, 7, 8, 10]}
PROGRESSIONS = {  # scale-degree roots (0-based) per bar
    # minor = i-iv-VII-i: the old i-VI-III-VII was heard as the relative major (D minor planned -> F major measured, 2026-09-21)
    "minor": [0, 3, 6, 0], "major": [0, 4, 5, 3], "dorian": [0, 3, 0, 6], "phrygian": [0, 1, 0, 6]}
STYLES = {  # per-style character
    "cinematic-action": dict(kick=True, taiko=True, arp=True, bell=False, hats=16, pad_cut=2400, bass_cut=520, snare="clap"),
    "uplifting": dict(kick=True, taiko=False, arp=True, bell=True, hats=8, pad_cut=3200, bass_cut=420, snare="snare"),
    "tense": dict(kick=False, taiko=True, arp=False, bell=False, hats=8, pad_cut=1400, bass_cut=300, snare="clap"),
    "ambient": dict(kick=False, taiko=False, arp=False, bell=True, hats=0, pad_cut=2600, bass_cut=300, snare="none"),
    "comedy": dict(kick=True, taiko=False, arp=True, bell=True, hats=8, pad_cut=3800, bass_cut=500, snare="snare"),
    "neon": dict(kick=True, taiko=False, arp=True, bell=False, hats=16, pad_cut=2800, bass_cut=560, snare="clap"),
}


@dataclass
class MusicPlan:
    bpm: float = 100.0
    root: int = 57            # MIDI note of the tonic (A3)
    scale: str = "minor"
    duration: float = 30.0
    style: str = "cinematic-action"
    sections: list = field(default_factory=lambda: [(0.0, 30.0, 0.5)])  # (t0, t1, intensity 0..1)
    hits: list = field(default_factory=list)                           # (time, kind: impact|swell|hit), risers are added before impacts
    brightness: float = 1.0   # multiplies filter cutoffs (reference-matching knob)
    low_boost: float = 1.0    # multiplies sub/bass level
    seed: int = 7
    swing: float = 0.0

    def to_json(self):
        return json.dumps(asdict(self), indent=1)


def intensity_at(plan, t):
    for a, b, v in plan.sections:
        if a <= t < b:
            return v
    return plan.sections[-1][2] if plan.sections else 0.5


def chord(plan, degree, size=3):
    sc = SCALES[plan.scale]
    return [plan.root + sc[(degree + 2 * k) % 7] + 12 * ((degree + 2 * k) // 7) for k in range(size)]


def render(plan: MusicPlan, sr=S.SR, only=None):
    """only: iterable of layer names to synthesise ('pad','bass','arp','drums','fx'); default all."""
    S.RNG = np.random.default_rng(plan.seed)
    st = STYLES.get(plan.style, STYLES["cinematic-action"])
    n = int(plan.duration * sr)
    tracks = {k: np.zeros((2, n), np.float32) for k in ("pad", "bass", "arp", "drums", "fx")}
    beat = 60.0 / plan.bpm
    step = beat / 4
    prog = PROGRESSIONS.get(plan.scale, PROGRESSIONS["minor"])
    n_steps = int(plan.duration / step)
    rng = np.random.default_rng(plan.seed)
    for i in range(n_steps):
        t = i * step + (step * plan.swing if i % 2 else 0)
        bar, pos = divmod(i, 16)
        deg = prog[bar % len(prog)]
        inten = intensity_at(plan, t)
        ch = chord(plan, deg)
        # ---- pad: one chord per bar, always present, louder with intensity
        if pos == 0:
            notes = ch + [ch[0] + 12]
            S.place(tracks["pad"], S.pad(notes, beat * 4 + 0.6, cutoff=st["pad_cut"] * plan.brightness * (0.6 + 0.6 * inten)), t, 0.55 + 0.35 * inten)
        # ---- bass: 8ths, from intensity 0.25
        if inten > 0.25 and pos % 2 == 0:
            root = ch[0] - 24 + (12 if pos in (6, 14) and inten > 0.7 else 0)
            S.place(tracks["bass"], S.bass(root, step * 1.8, st["bass_cut"] * plan.brightness), t, (0.5 + 0.4 * inten) * plan.low_boost)
        # ---- arpeggio 16ths above 0.45
        if st["arp"] and inten > 0.45:
            tone = ch[(i * 3 + bar) % 3] + 12 * (1 + (i // 4) % 2)
            S.place(tracks["arp"], S.pluck(tone, step * 2, 3200 * plan.brightness), t, 0.22 + 0.2 * inten, pan=((i % 4) - 1.5) * 0.3)
        # ---- drums
        if st["kick"] and inten > 0.35 and (pos in (0, 8) or (inten > 0.75 and pos in (6, 10, 14))):
            S.place(tracks["drums"], S.kick(), t, 0.7 + 0.25 * inten)
        if st["snare"] != "none" and inten > 0.5 and pos in (4, 12):
            S.place(tracks["drums"], S.clap() if st["snare"] == "clap" else S.snare(), t, 0.5 + 0.3 * inten)
        if st["hats"] and inten > 0.4:
            every = 1 if (st["hats"] == 16 and inten > 0.6) else 2
            if pos % every == 0:
                S.place(tracks["drums"], S.hat(open_=(pos % 8 == 6)), t, 0.28 * (0.6 + 0.4 * rng.random()), pan=0.3)
        if st["taiko"] and inten > 0.7 and pos in (0, 3, 8, 11):
            S.place(tracks["drums"], S.taiko(62 + 6 * (pos == 8)), t, 0.65)
        if st["bell"] and inten > 0.3 and pos in (0, 8) and bar % 2 == 0:
            S.place(tracks["arp"], S.bell(ch[2] + 24, 2.2), t, 0.16)
    # ---- cues: riser into every impact, plus the impact itself
    for t, kind in plan.hits:
        if kind == "impact":
            r = min(1.6, max(0.5, t))
            S.place(tracks["fx"], S.riser(r), max(0.0, t - r), 0.55)
            S.place(tracks["fx"], S.impact(), t, 0.9)
        elif kind == "swell":
            S.place(tracks["fx"], S.riser(1.0, 200, 3000), max(0.0, t - 1.0), 0.35)
        else:
            S.place(tracks["fx"], S.impact(1.2), t, 0.55)
    mix = np.zeros((2, n), np.float32)
    lv = {"pad": 0.55, "bass": 0.8, "arp": 0.5, "drums": 0.9, "fx": 0.8}
    for k, tr in tracks.items():
        if only is not None and k not in only:
            continue
        wet = {"pad": 0.4, "arp": 0.3, "fx": 0.35, "drums": 0.08, "bass": 0.0}[k]
        for c in range(2):
            x = tr[c]
            mix[c] += (S.reverb(x, 2.2 if k != "drums" else 0.8, wet) if wet else x) * lv[k]
    peak = np.abs(mix).max() + 1e-9
    mix = np.tanh(mix / peak * 1.6) / np.tanh(1.6) * 0.85  # soft limiter
    return mix
