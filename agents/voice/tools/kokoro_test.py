import time, sys
t = time.time()
from kokoro import KPipeline
import numpy as np, soundfile as sf
pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
print("load s", round(time.time() - t, 1), flush=True)
text = "What if a few clever tweaks could transform your animation into a cinematic masterpiece? Curious how? Stick around."
t = time.time()
chunks, words = [], []
off = 0.0
for r in pipe(text, voice="am_michael", speed=1.0):
    a = r.audio.numpy() if hasattr(r.audio, "numpy") else np.asarray(r.audio)
    for tk in (r.tokens or []):
        if tk.start_ts is not None and tk.end_ts is not None:
            words.append((tk.text, round(off + tk.start_ts, 2), round(off + tk.end_ts, 2)))
    chunks.append(a); off += len(a) / 24000
y = np.concatenate(chunks)
sf.write("kokoro_test.wav", y, 24000)
print("synth s", round(time.time() - t, 1), "audio s", round(len(y) / 24000, 1), "words", words[:6])
