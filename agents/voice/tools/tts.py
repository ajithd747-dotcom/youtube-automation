"""Text-to-speech engines behind one interface, always returning word timings.

    synthesize(text, engine="kokoro"|"edge", voice=None, speed=1.0, out="x.wav") -> {path, duration, words, engine, voice}

kokoro : local neural TTS (Kokoro-82M, Apache-2.0, ~330 MB, runs on CPU, very natural, word timestamps from the model)
edge   : Microsoft neural voices through edge-tts (free online service; unofficial API - fine for drafts, check terms before
         monetising); word boundaries from the service
Both write 24 kHz (kokoro) / mp3 (edge); callers convert with ffmpeg as needed.
"""
import asyncio
import re
import sys
from pathlib import Path

import numpy as np

KOKORO_VOICES = {  # name -> (gender, character)
    "am_michael": ("m", "warm, natural, mid-low"), "am_adam": ("m", "deep, calm"), "am_fenrir": ("m", "authoritative"),
    "am_puck": ("m", "playful, bright"), "am_echo": ("m", "clear"), "am_eric": ("m", "neutral"), "am_liam": ("m", "young"),
    "af_heart": ("f", "warm, expressive"), "af_bella": ("f", "smooth"), "af_nicole": ("f", "soft, calm"), "af_sarah": ("f", "clear"),
    "af_sky": ("f", "light"), "bm_george": ("m", "british, calm"), "bm_lewis": ("m", "british, deep"), "bf_emma": ("f", "british, clear"),
}
EDGE_VOICES = {"default": "en-US-AndrewNeural", "energetic": "en-US-GuyNeural", "serious": "en-US-ChristopherNeural",
               "narrative": "en-US-EricNeural", "warm_female": "en-US-AriaNeural", "energetic_female": "en-US-JennyNeural"}

_PIPE = {}


def _kokoro_pipe(lang="a"):
    if lang not in _PIPE:
        from kokoro import KPipeline
        _PIPE[lang] = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M")
    return _PIPE[lang]


def kokoro(text, voice="am_michael", speed=1.0, out="out.wav"):
    import soundfile as sf
    chunks, words, off = [], [], 0.0
    lang = "b" if voice.startswith("b") else "a"
    for r in _kokoro_pipe(lang)(text, voice=voice, speed=speed):
        a = r.audio.numpy() if hasattr(r.audio, "numpy") else np.asarray(r.audio)
        for tk in (r.tokens or []):
            if tk.start_ts is not None and tk.end_ts is not None and re.search(r"\w", tk.text):
                words.append({"text": tk.text, "start": round(off + tk.start_ts, 3), "end": round(off + tk.end_ts, 3)})
        chunks.append(a)
        off += len(a) / 24000
    y = np.concatenate(chunks) if chunks else np.zeros(2400, np.float32)
    sf.write(str(out), y, 24000)
    return {"path": str(out), "duration": len(y) / 24000, "words": words, "engine": "kokoro", "voice": voice}


def edge(text, voice=None, speed=1.0, out="out.mp3", pitch_hz=0):
    import edge_tts
    voice = EDGE_VOICES.get(voice, voice) or EDGE_VOICES["default"]
    rate = f"{int(round((speed - 1) * 100)):+d}%"
    words = []

    async def go():
        com = edge_tts.Communicate(text, voice, rate=rate, pitch=f"{pitch_hz:+d}Hz", boundary="WordBoundary")
        with open(out, "wb") as fh:
            async for ev in com.stream():
                if ev["type"] == "audio":
                    fh.write(ev["data"])
                elif ev["type"] == "WordBoundary":
                    s = ev["offset"] / 1e7
                    words.append({"text": ev["text"], "start": round(s, 3), "end": round(s + ev["duration"] / 1e7, 3)})

    for attempt in range(4):
        try:
            words.clear()
            asyncio.run(go())
            break
        except Exception as e:  # the service sometimes returns "No audio was received"
            if attempt == 3:
                raise
    import subprocess
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)], capture_output=True, text=True)
    return {"path": str(out), "duration": float(d.stdout.strip()), "words": words, "engine": "edge", "voice": voice}


def synthesize(text, engine="kokoro", voice=None, speed=1.0, out="out.wav", **kw):
    text = re.sub(r"\s+", " ", text).strip()
    if engine == "kokoro":
        return kokoro(text, voice or "am_michael", speed, out)
    return edge(text, voice, speed, out, **kw)
