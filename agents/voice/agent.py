"""Voice agent - chooses the narrator (engine, voice, speed, pitch) from the content and skills, produces word-timed narration,
matches a reference voice (pitch + speaking rate), and builds word-highlight captions."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE / "tools"))
from core import Agent  # noqa: E402

import captions as CAP  # noqa: E402
import measure as MEA  # noqa: E402
import tts as TTS  # noqa: E402

STYLE_DEFAULTS = {  # style -> (kokoro voice, speed, edge voice)
    "explainer": ("am_michael", 1.0, "default"), "tutorial": ("am_michael", 1.02, "default"), "calm": ("am_adam", 0.92, "narrative"),
    "psychology": ("am_adam", 0.92, "narrative"), "comedy": ("am_puck", 1.08, "energetic"), "news": ("am_fenrir", 1.0, "serious"),
    "story": ("bm_george", 0.98, "narrative"), "kids": ("af_sky", 1.05, "energetic_female"), "warm": ("af_heart", 1.0, "warm_female"),
}
CAL_TEXT = "The quick brown fox jumps over the lazy dog while the animation renders frame after frame."
CACHE = HERE / "cache" / "voices.json"


class VoiceAgent(Agent):
    """Narration with word timings; see agents/voice/skills."""

    def choose(self, text, style=None, engine="kokoro"):
        low = text.lower()
        if not style:
            style = ("comedy" if any(w in low for w in ("joke", "funny", "haha", "lol", "stickman")) else
                     "psychology" if any(w in low for w in ("feel", "believe", "yourself", "mind", "doubt")) else "explainer")
        k, speed, e = STYLE_DEFAULTS.get(style, STYLE_DEFAULTS["explainer"])
        hits = self.skills(f"{style} {text[:200]}", k=2)
        return {"style": style, "engine": engine, "voice": k if engine == "kokoro" else e, "speed": speed, "skills": [s.id for _, s in hits]}

    def speak(self, text, out, engine="kokoro", voice=None, speed=1.0, pitch_semitones=0.0):
        r = TTS.synthesize(text, engine, voice, speed, out)
        if abs(pitch_semitones) > 0.05:
            r = self.pitch_shift(r, pitch_semitones)
        return r

    def pitch_shift(self, r, semitones):
        """Shift pitch with ffmpeg (asetrate + atempo keeps duration): word timings stay valid."""
        src = Path(r["path"])
        sr = 24000 if r["engine"] == "kokoro" else 24000
        f = 2 ** (semitones / 12.0)
        dst = src.with_name(src.stem + "_ps.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", f"asetrate={int(sr * f)},aresample={sr},atempo={1 / f:.5f}", str(dst)], check=True)
        return dict(r, path=str(dst), pitch_semitones=semitones)

    def narrate(self, segments, out_dir, engine="kokoro", style=None, voice=None, speed=None, pitch_semitones=0.0, pad=0.35):
        """segments: list of text. Returns [{path, duration, words, ...}] with word times relative to each clip."""
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        choice = self.choose(" ".join(segments), style, engine)
        v, sp = voice or choice["voice"], speed or choice["speed"]
        res = []
        for i, text in enumerate(segments):
            ext = "wav" if engine == "kokoro" else "mp3"
            r = self.speak(text, out_dir / f"nar{i:02d}.{ext}", engine, v, sp, pitch_semitones)
            r["duration"] += 0.0
            res.append(r)
        return res

    def calibrate_voices(self, voices=None, force=False):
        """Measure f0 and speaking rate of each candidate voice on a fixed sentence (cached)."""
        cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() and not force else {}
        CACHE.parent.mkdir(exist_ok=True)
        for v in voices or [k for k, (g, _) in TTS.KOKORO_VOICES.items() if g == "m"]:
            if v in cache:
                continue
            r = TTS.kokoro(CAL_TEXT, v, 1.0, CACHE.parent / f"cal_{v}.wav")
            cache[v] = MEA.stats(r["path"], words=r["words"])
            CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
        return cache

    def match_reference(self, ref_audio, ref_words=None, voices=None):
        """Pick the Kokoro voice + speed + pitch shift that best reproduces a reference narrator's pitch and pace."""
        ref = MEA.stats(ref_audio, words=ref_words)
        cal = self.calibrate_voices(voices)
        best = min(cal.items(), key=lambda kv: abs((kv[1]["f0_median"] or 0) - (ref["f0_median"] or 0)))
        v, m = best
        speed = (ref.get("wpm_speaking") or m["wpm_speaking"]) / m["wpm_speaking"]
        semis = 12 * __import__("math").log2((ref["f0_median"] or m["f0_median"]) / m["f0_median"]) if ref["f0_median"] else 0.0
        return {"reference": ref, "voice": v, "speed": round(max(0.7, min(1.4, speed)), 3), "pitch_semitones": round(max(-4, min(4, semis)), 2), "voice_stats": m}

    def captions(self, words, out_ass, w, h, style="karaoke", offset=0.0):
        return CAP.write_ass(out_ass, words, w, h, offset, style)

    def run(self, task="", **kw):
        return {"task": task, "choice": self.choose(task)}
