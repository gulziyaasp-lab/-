import json, sys
from faster_whisper import WhisperModel
m = WhisperModel(sys.argv[1], device="cpu", compute_type="int8")
import numpy as np, wave
wf = wave.open(sys.argv[2]); a = np.frombuffer(wf.readframes(wf.getnframes()), "<i2").astype(np.float32)/32768
segs, info = m.transcribe(a, language="ru", word_timestamps=True, beam_size=5, vad_filter=False)
words = []
for s in segs:
    print(f"[{s.start:.2f}-{s.end:.2f}] {s.text}")
    for w in s.words:
        words.append({"w": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3), "p": round(w.probability, 2)})
json.dump(words, open(sys.argv[3], "w"), ensure_ascii=False, indent=1)
