"""Merge the brief's §5 table with measured audio data into one timing reference.

Two measurement sources, used according to their reliability:

  * ffmpeg silencedetect  -> authoritative for SENTENCE-INITIAL onsets. Whisper
    clamps a segment's first word to the segment start, so it reads late (by up
    to 0.27s) after a pause. Verified at t=0: RMS is -57dB until 0.078 and
    -17.9dB by 0.131, so true speech onset is 0.118 -- not Whisper's 0.00.
  * faster-whisper word timestamps -> used for MID-SENTENCE words, where there
    is no pause to confuse the aligner.

The brief states hits land 0.05s BEFORE the word is heard, so the recommended
Stage time for each event is (measured onset - 0.05).
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
LEAD = 0.05  # §5: "Hits land 0.05s before the word is heard."

words = json.load(open(os.path.join(HERE, "vo_words.json")))["words"]

# ffmpeg silence_end -> true onset of each sentence-initial word (seconds)
SENTENCE_ONSETS = {
    0:  0.118,   # "The"        (RMS-verified)
    9:  3.153,   # "Insurance"
    18: 7.052,   # "And"
    28: 10.040,  # "Even"
    33: 12.423,  # "Awesome"
    43: 16.542,  # "Get" (matched)
    45: 17.370,  # "Get" (paid)
    47: 18.314,  # "AwesomeAttorneys"
}

def onset(i):
    """Measured onset for word index i."""
    return SENTENCE_ONSETS.get(i, words[i]["start"])

# (brief_time, voice text, anchor word index, accent?, visual note)
EVENTS = [
    (0.13,  "The first",              0,  False, "check.png slides in; 'The first' pops"),
    (0.55,  "offer",                  2,  False, ""),
    (0.85,  "is almost",              3,  False, ""),
    (1.30,  "never",                  5,  True,  "ACCENT never + FIRST OFFER stamp"),
    (1.60,  "the best",               6,  False, ""),
    (2.05,  "offer.",                 8,  False, "stamp settles"),
    (3.15,  "Insurance companies",    9,  False, "FLIP TO BLACK; envelope.png; road draws"),
    (4.05,  "open low,",             12,  True,  "ACCENT low + bar chart"),
    (4.75,  "because most people",   13,  False, ""),
    (5.65,  "accept",                16,  True,  "ACCENT accept + pinned note card"),
    (6.15,  "early.",                17,  False, "third note line"),
    (7.06,  "And once you",          18,  False, "FLIP TO CREAM; release.png + pen.png"),
    (7.65,  "sign",                  21,  True,  "ACCENT sign + signature draws"),
    (8.05,  "that release,",         23,  False, ""),
    (8.60,  "your case",             24,  False, ""),
    (9.35,  "is over",               27,  True,  "ACCENT over + CASE CLOSED stamp"),
    (10.04, "even if your",          28,  False, "new lower line"),
    (10.65, "treatment",             31,  True,  "ACCENT treatment + brace.png + 40% bar"),
    (11.20, "isn't.",                32,  False, "bar keeps filling"),
    (12.43, "Awesome Attorneys",     33,  False, "CIRCLE WIPE done; brand red; wordmark"),
    (13.45, "matches you",           35,  False, "YOU / ATTORNEY dots"),
    (13.95, "directly",              37,  True,  "ACCENT directly + line snaps"),
    (14.70, "with a Phoenix",        38,  False, "skyline.png rises"),
    (15.50, "injury attorney.",      41,  False, "phone.png slides in"),
    (16.55, "Get Matched.",          43,  True,  "CARD SLIDE to cream; hero line"),
    (17.38, "Get Paid.",             45,  True,  "second hero line, brand red"),
    (18.32, "AwesomeAttorneys dot com.", 47, True, "lines ease up; URL + button"),
]

rows = []
for brief_t, voice, idx, accent, note in EVENTS:
    m = onset(idx)
    rec = round(m - LEAD, 3)
    rows.append({
        "brief_time": brief_t,
        "voice": voice,
        "anchor_word": words[idx]["word"],
        "measured_onset": round(m, 3),
        "recommended_stage_time": rec,
        "delta_vs_brief": round(rec - brief_t, 3),
        "accent": accent,
        "source": "silencedetect" if idx in SENTENCE_ONSETS else "whisper",
        "visual": note,
    })

json.dump({"lead": LEAD, "vo_duration": 20.036, "stage_duration": 22.5, "events": rows},
          open(os.path.join(HERE, "timing_reference.json"), "w"), indent=2)

# ---- markdown ----------------------------------------------------------
L = ["| Brief | Voice | Anchor | Measured onset | Recommended | Δ | Src |",
     "|---|---|---|---|---|---|---|"]
for r in rows:
    flag = " ⚠️" if abs(r["delta_vs_brief"]) > 0.10 else ""
    acc = "**" if r["accent"] else ""
    L.append(f"| {r['brief_time']:.2f} | {acc}{r['voice']}{acc} | `{r['anchor_word']}` | "
             f"{r['measured_onset']:.3f} | **{r['recommended_stage_time']:.2f}** | "
             f"{r['delta_vs_brief']:+.3f}{flag} | {r['source'][:4]} |")
open(os.path.join(HERE, "timing_reference.md"), "w").write("\n".join(L) + "\n")

big = [r for r in rows if abs(r["delta_vs_brief"]) > 0.10]
print("\n".join(L))
print(f"\n{len(big)} of {len(rows)} events move by more than 0.10s:")
for r in big:
    print(f"  {r['brief_time']:>5.2f} -> {r['recommended_stage_time']:>5.2f} "
          f"({r['delta_vs_brief']:+.3f})  {r['voice']!r}  [{r['visual']}]")
