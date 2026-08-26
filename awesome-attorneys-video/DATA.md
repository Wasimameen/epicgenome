# "The First Offer" — collected source data

Everything §2, §3 and §5 of the brief depend on, measured rather than assumed,
so the Stage build starts from real numbers. Nothing has been animated yet.

```
assets/voiceover.mp3          the VO, unmodified (exporter muxes this at t=0)
assets/brand-og-reference.png the site's OG card (wordmark rendered in Fraunces)
data/brief.md                 the original prompt, verbatim
data/vo_words.json            49 word-level timestamps
data/timing_reference.json    §5 table merged with measured onsets
data/timing_reference.md       ↳ same, as a table
data/brand_capture.json        the site's real palette, fonts, CTA, copy
data/transcribe.py             regenerates vo_words.json
data/extract_brand.py          regenerates brand_capture.json
data/build_timing.py           regenerates the timing reference
```

---

## 1. Audio — the brief's sentence boundaries are correct

`voiceover.mp3` is **20.036s**, 44.1kHz mono, MP3 CBR 128kbps. Against a 22.5s
Stage that leaves **2.464s** of end-card hold, not the 2.5s the brief assumes —
close enough that nothing needs to move, but the last Sprite should end at 22.5
exactly, not at `20.04 + 2.5`.

Every sentence boundary in §5 is confirmed within **0.02s** by ffmpeg
`silencedetect`:

| §5 pause | Measured | Error |
|---|---|---|
| 2.55–3.15 | 2.550–3.153 | +0.000 / +0.003 |
| 6.58–7.06 | 6.598–7.057 | +0.018 / −0.003 |
| 9.71–10.04 | 9.712–10.044 | +0.002 / +0.004 |
| 11.72–12.43 | 11.724–12.433 | +0.004 / +0.003 |
| 16.19–16.55 | 16.189–16.544 | −0.001 / −0.006 |

The opening silence is real too: RMS sits at −57dB until 0.078 and reaches
−17.9dB by 0.131, so speech starts at **0.118s**. The brief's `0.13` is right.

Two boundaries the brief doesn't list but that the build needs, both confirming
its own numbers: **17.370** ("Get Paid.") and **18.314** ("AwesomeAttorneys.com").

### Word-level timings

`data/timing_reference.md` has the full merged table. Two sources, used by
reliability: `silencedetect` is authoritative for sentence-initial onsets
(Whisper clamps a segment's first word to the segment start and reads up to
0.27s late after a pause — it put "The" at 0.00 when the true onset is 0.118);
Whisper's word timestamps are used mid-sentence, where no pause confuses it.

Recommended Stage time = measured onset − 0.05, per the brief's own
"hits land 0.05s before the word is heard".

**11 of 27 events want to move by more than 0.10s.** Three matter:

- **4.05 → 4.31 (+0.26), "open low"** — the accent is on *low*, but 4.05 is
  where *open* starts (3.98). "low" is at 4.360. The bar-chart beat fires late
  as written; it should fire at **4.31**.
- **14.70 → 14.27 (−0.43), "with a Phoenix"** and **15.50 → 15.09 (−0.41),
  "injury attorney"** — the whole brand beat is written slower than it is
  spoken. The sentence runs 12.42→16.06 and the last third is compressed.
  `skyline.png` and `phone.png` both enter ~0.4s late as written.
- **13.45 → 13.11 (−0.34), "matches you"** — same cause, same sentence.

The rest are ≤0.15s and are the ordinary drift the brief expected to nudge by
ear. Every accent word in the §7 scrub checklist lands within 0.12s of its
written time except "open low" above.

---

## 2. Brand — the red is right, most of the rest of the palette isn't

Chromium is blocked by this environment's egress policy (`ERR_CONNECTION_RESET`
on every navigation, via proxy or not — `curl` to the same URL returns 200), so
there are no screenshots. The brand data below is parsed from the live HTML and
its inline CSS, which is where the theme's real tokens live.

`<meta name="theme-color" content="#8A2326">` — **the brief's brand red is exact.**

The site is WordPress and publishes its full palette as theme presets. Six of
the brief's eight tokens are approximations of it:

| Brief token | Brief value | Site token | Site value | |
|---|---|---|---|---|
| `brand` | `#8A2326` | `oxblood` | **`#8A2326`** | ✅ exact |
| `white` | `#FFFFFF` | `white` | `#FFFFFF` | ✅ exact |
| `cream` | `#F6F3EC` | `base` | **`#FBF7EF`** | warmer, lighter |
| `ink` | `#111111` | `contrast` | **`#14110F`** | warmer |
| `grey` | `#8E8E8E` | `ink-soft` | **`#4A443C`** | much darker, warmer |
| `black` | `#0A0A0A` | — | — | ⚠️ not on the site |
| `brandBright` | `#E0393F` | — | — | ⚠️ invented |

`#0A0A0A` and `#E0393F` have no basis in the site. The black background is a
deliberate art-direction choice for the video and is fine to keep; but for the
accent-on-black problem the brief invented `brandBright` to solve, the site
already ships a better answer:

| Site token | Value | Use |
|---|---|---|
| `oxblood-deep` | `#5E1619` | link hover / depth under oxblood |
| `brass` | **`#B68A4E`** | the on-brand accent that reads on black |
| `brass-light` | `#D9B780` | |
| `brass-dark` | `#8C6A3A` | |
| `parchment` | `#F1E8D8` | |
| `sand` | `#E4D9C3` | |

Body text is `contrast` on `base`; links are `oxblood`, hovering to
`oxblood-deep`.

### Typography — the site has two families, not one

§2 says "one family, Inter (**or the site's font if web capture finds one**)".
It found them, and there are two:

- **Fraunces** (`Fraunces, "Fraunces Fallback", Georgia, serif`) — all headings
  and the wordmark, weight **600**, letter-spacing **−0.01em**, line-height 1.12.
- **Inter** (`Inter, "Inter Fallback", -apple-system, "Segoe UI", Roboto,
  sans-serif`) — body.

Both are self-hosted; there is no Google Fonts request. The natural mapping is
Fraunces for the hero/accent lines and the wordmark, Inter for labels and
supporting text — which also means the §6 font selector should offer
Fraunces/Inter, not Inter/"site font".

### Wordmark

There is **no logo image or SVG on the site.** The wordmark is live text:

```html
<p class="wp-block-site-title"><a href="https://awesomeattorneys.com">Awesome Attorneys</a></p>
```

styled Fraunces 600, −0.01em. So `logo.svg` in §3 should be set as text in
Fraunces rather than sourced as a file. `assets/brand-og-reference.png` shows it
rendered (it is served as WebP under a `.png` name; both forms are in `assets/`).

### Copy — all confirmed verbatim

| | |
|---|---|
| Tagline | "The independent attorney guide" |
| CTA | **"Get Matched"** → `/find-a-lawyer/` |
| Disclaimer | "Awesome Attorneys is not a law firm and does not provide legal advice." |
| Handle | @AwesomeAttys |
| Page title | "Find a Phoenix Personal Injury Lawyer \| Awesome Attorneys" |

The page title independently confirms the VO's Phoenix/injury positioning.
Site headlines, for tone: "Stop Searching. Start Choosing.", "Tell us what
happened.", "Five lists, one standard."

---

## 3. Cutout assets — none present

All eight §3 files are missing:

| File | Status |
|---|---|
| `check.png` `envelope.png` `release.png` `pen.png` | ❌ absent |
| `brace.png` `phone.png` `skyline.png` | ❌ absent |
| `logo.svg` | ❌ absent — and shouldn't exist; set as Fraunces text (above) |

Four images were pasted into the chat — a city skyline, a bag of money, a black
fountain pen, and a dollar bill under an umbrella — which look like intended
stand-ins for `skyline.png`, `pen.png` and the check/insurance beats. They
arrived as inline images, not files, so they aren't on disk and can't be wired
into the Stage. **Re-upload them as files** (named per §3) and they'll be used;
otherwise §3's fallback applies and all seven become flat-vector stand-ins.

Note that the pasted skyline is a generic blue-glass business district with a
mirrored reflection — not the Phoenix/Camelback silhouette §3 asks for, and not
a flat single-colour cutout. It would need to be re-cut to match.

---

## 4. What this changes for the build

1. Adopt the site's real tokens for `cream`/`ink`/`grey`; keep `#0A0A0A` as an
   art-direction choice; **replace `brandBright #E0393F` with `brass #B68A4E`**
   for accents on black.
2. Add Fraunces alongside Inter and split display/body between them.
3. Move the three timing events called out in §1; apply the ≤0.15s nudges or
   leave them to the §6 offset control.
4. Set `logo.svg` as Fraunces text.
5. Supply the seven cutouts as files, or accept vector stand-ins.
