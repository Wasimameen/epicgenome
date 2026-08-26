"""Word-level forced alignment of voiceover.mp3 for the §5 timing table."""
import json, os, sys
from faster_whisper import WhisperModel

AUDIO = os.path.join(os.path.dirname(__file__), "..", "assets", "voiceover.mp3")
OUT = os.path.join(os.path.dirname(__file__), "vo_words.json")

model = WhisperModel("small.en", device="cpu", compute_type="int8")
segments, info = model.transcribe(
    AUDIO,
    language="en",
    word_timestamps=True,
    vad_filter=False,
    beam_size=5,
)

words, segs = [], []
for s in segments:
    segs.append({"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip()})
    for w in s.words or []:
        words.append({
            "word": w.word.strip(),
            "start": round(w.start, 3),
            "end": round(w.end, 3),
            "prob": round(w.probability, 3),
        })

json.dump({"duration": round(info.duration, 3), "segments": segs, "words": words},
          open(OUT, "w"), indent=2)

print(f"duration={info.duration:.3f}s  segments={len(segs)}  words={len(words)}")
for w in words:
    print(f"{w['start']:6.2f} -> {w['end']:6.2f}  {w['word']}")
