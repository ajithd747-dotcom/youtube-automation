"""Real-instrument engine: MusicPlan -> General MIDI file (mido) -> FluidSynth + free GeneralUser GS soundfont -> wav.

FluidSynth (LGPL) and GeneralUser GS (permissive licence, commercial use allowed) live in agents/tools_bin/. Cinematic FX
(risers, impacts) still come from the numpy synth and are layered on top by the agent.
"""
import subprocess
from pathlib import Path

import mido
import numpy as np

import compose as C

BIN = Path(__file__).resolve().parents[2] / "tools_bin"
SOUNDFONT = BIN / "GeneralUser-GS.sf2"

# GM programs per style: (pad, choir, bass, arp, bell)
PROGRAMS = {
    "cinematic-action": dict(pad=48, choir=52, bass=38, arp=45, bell=8, drums="epic"),
    "uplifting": dict(pad=49, choir=52, bass=33, arp=46, bell=9, drums="pop"),
    "tense": dict(pad=48, choir=91, bass=32, arp=45, bell=14, drums="epic"),
    "ambient": dict(pad=89, choir=91, bass=32, arp=46, bell=98, drums="none"),
    "comedy": dict(pad=51, choir=52, bass=32, arp=10, bell=11, drums="pop"),
    "neon": dict(pad=90, choir=94, bass=39, arp=80, bell=98, drums="pop"),
}


def find_fluidsynth():
    for p in BIN.rglob("fluidsynth"):
        if p.is_file():
            return p
    return None


def available():
    return find_fluidsynth() is not None and SOUNDFONT.exists()


def build_midi(plan: C.MusicPlan, path):
    """Translate the same musical logic as compose.render into GM notes. Returns the .mid path."""
    prog = PROGRAMS.get(plan.style, PROGRAMS["cinematic-action"])
    st = C.STYLES.get(plan.style, C.STYLES["cinematic-action"])
    ppq = 480
    tempo = mido.bpm2tempo(plan.bpm)
    beat = 60.0 / plan.bpm
    step = beat / 4
    tick = lambda t: int(round(t / beat * ppq))
    events = []  # (tick, order, msg)
    for ch, pr in ((0, prog["pad"]), (1, prog["choir"]), (2, prog["bass"]), (3, prog["arp"]), (4, prog["bell"]), (5, 47)):
        events.append((0, 0, mido.Message("program_change", channel=ch, program=pr, time=0)))

    def note(ch, n, t, dur, vel):
        n = int(max(0, min(127, n)))
        events.append((tick(t), 2, mido.Message("note_on", channel=ch, note=n, velocity=int(max(1, min(127, vel))), time=0)))
        events.append((tick(t + dur), 1, mido.Message("note_off", channel=ch, note=n, velocity=0, time=0)))

    rng = np.random.default_rng(plan.seed)
    prog_deg = C.PROGRESSIONS.get(plan.scale, C.PROGRESSIONS["minor"])
    for i in range(int(plan.duration / step)):
        t = i * step
        bar, pos = divmod(i, 16)
        deg = prog_deg[bar % len(prog_deg)]
        ch = C.chord(plan, deg)
        inten = C.intensity_at(plan, t)
        if pos == 0:
            for n in ch + [ch[0] + 12]:
                note(0, n, t, beat * 4, 45 + 45 * inten)
            if inten > 0.7:
                for n in ch:
                    note(1, n + 12, t, beat * 4, 40 + 30 * inten)
        if inten > 0.25 and pos % 2 == 0:
            note(2, ch[0] - 24 + (12 if pos in (6, 14) and inten > 0.7 else 0), t, step * 1.8, (60 + 40 * inten) * min(plan.low_boost, 1.3))
        if st["arp"] and inten > 0.45:
            note(3, ch[(i * 3 + bar) % 3] + 12 * (1 + (i // 4) % 2), t, step * 1.6, 50 + 35 * inten)
        if st["bell"] and inten > 0.3 and pos in (0, 8) and bar % 2 == 0:
            note(4, ch[2] + 24, t, beat * 2, 55)
        # drums on channel 9 (GM percussion map)
        if prog["drums"] != "none":
            if st["kick"] and inten > 0.35 and (pos in (0, 8) or (inten > 0.75 and pos in (6, 10, 14))):
                note(9, 36, t, 0.1, 90 + 30 * inten)
            if st["snare"] != "none" and inten > 0.5 and pos in (4, 12):
                note(9, 39 if st["snare"] == "clap" else 38, t, 0.1, 75 + 40 * inten)
            if st["hats"] and inten > 0.4 and pos % (1 if (st["hats"] == 16 and inten > 0.6) else 2) == 0:
                note(9, 46 if pos % 8 == 6 else 42, t, 0.06, int(45 + 25 * rng.random()))
            if st["taiko"] and inten > 0.7 and pos in (0, 3, 8, 11):
                note(9, 41 if pos in (0, 8) else 45, t, 0.2, 100)
    for t, kind in plan.hits:
        note(5, plan.root - 24, t, 1.2, 120 if kind == "impact" else 95)      # timpani
        note(9, 49, t, 1.0, 118 if kind == "impact" else 85)                   # crash cymbal
        if kind == "impact":
            note(9, 36, t, 0.1, 127)
    mid = mido.MidiFile(ticks_per_beat=ppq)
    tr = mido.MidiTrack()
    tr.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
    last = 0
    for tk, _, msg in sorted(events, key=lambda e: (e[0], e[1])):
        msg = msg.copy(time=tk - last)
        last = tk
        tr.append(msg)
    mid.tracks.append(tr)
    mid.save(str(path))
    return Path(path)


def render_wav(mid_path, wav_path, sr=44100, gain=0.8):
    fs = find_fluidsynth()
    r = subprocess.run([str(fs), "-ni", "-g", str(gain), "-r", str(sr), "-R", "1", "-C", "1", "-F", str(wav_path), str(SOUNDFONT), str(mid_path)],
                       capture_output=True, text=True, timeout=300)
    if not Path(wav_path).exists():
        raise RuntimeError("fluidsynth failed: " + (r.stderr or r.stdout)[-400:])
    return Path(wav_path)
