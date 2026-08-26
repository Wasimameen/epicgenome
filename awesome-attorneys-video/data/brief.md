# Claude Design prompt — "The First Offer" (Awesome Attorneys, 9:16, 22.5s, dynamic 2D motion graphics with animated cutout images)

**Before you paste:** upload these into the Claude Design project first — the voice-over renamed to `voiceover.mp3`, the cutout PNGs listed in §3 (as many as you have), and, if you have them, your logo SVG/PNG. Then paste everything below the line.

---

Build an animated 9:16 video for **Awesome Attorneys** (awesomeattorneys.com) in the "dynamic 2D motion graphics" style: word-by-word text synced to a voice-over, one accent word per phrase, backgrounds that flip between cream and black on sentence boundaries, and real cutout images (a check, a release form, a pen, a phone) that slide, rotate and float **with** the graphics, never sitting still. Extremely smooth. Professional. Nothing decorative that isn't doing a job.

## 1. Hard technical requirements (the exporter depends on these)

- Build it as an animated video on the `animations.jsx` Stage starter: call `copy_starter_component` with kind `"animations.jsx"`; do not hand-roll a timeline.
- One `<Stage width={1080} height={1920} duration={22.5} fps={60}>` wrapping everything.
- Drive ALL motion from `useTime()` or `<Sprite start end>` windows, tweened with `interpolate()` + `Easing`. Every frame must be a pure function of the playhead: no CSS `@keyframes` / `animation` / `transition` on animated elements, no `Date.now()`, `performance.now()`, `Math.random()`, `setTimeout`, `setInterval`, or `requestAnimationFrame` for timing. Any "random-looking" float or scatter is a seeded function of time.
- Put `data-export-hide` on every in-canvas control (play/scrub UI, the audio element, debug toggles).
- Wire `voiceover.mp3` to the Stage playhead for preview (play/pause/seek with the timeline) so I can check sync in the browser. The export tool muxes `voiceover.mp3` from the project folder at t=0, so the animation's t=0 must equal the audio's t=0. Do not trim or offset the audio.
- Total Stage duration 22.5s: the VO is 20.04s and the last 2.5s hold the end card.
- Keep every `<Sprite>` end time ≤ 22.5. Scrubbing to any time must produce the same pixels on refresh.

## 2. Brand (pull it from the site, don't invent it)

Use the web capture tool on https://awesomeattorneys.com/ to grab the logo/wordmark, the "Get Matched" button, and the exact red. What I know: theme color is **#8A2326** (deep brand red), the site calls itself *"The independent attorney guide"*, the primary CTA reads **Get Matched**, and the footer disclaimer is *"Awesome Attorneys is not a law firm and does not provide legal advice."* Social handle: **@AwesomeAttys**.

Palette:

| Token | Value | Use |
|---|---|---|
| `cream` | `#F6F3EC` | Light background |
| `black` | `#0A0A0A` | Dark background |
| `ink` | `#111111` | Text on cream |
| `white` | `#FFFFFF` | Text on black (with a soft glow: `0 0 18px rgba(255,255,255,0.35)`) |
| `brand` | `#8A2326` | Accent word on cream, brand beat background, stamp |
| `brandBright` | `#E0393F` | Accent word on black (brand red is too dark on black; use this there) |
| `grey` | `#8E8E8E` | The winding road path, secondary labels |
| `grid` | `rgba(0,0,0,0.10)` | Dotted grid pattern on cream (on black: `rgba(255,255,255,0.10)`) |

Typography: **one family**, Inter (or the site's font if web capture finds one). Body words weight 500; the accent word weight 800 in `brand`/`brandBright`; small labels 600 uppercase with +0.14em tracking. Hero lines 88–104px, supporting lines 60–72px, labels 30–34px. Text always sits inside a 90px side margin and clear of the top 14% / bottom 20% (platform UI).

## 3. Cutout images (uploaded PNGs with transparent backgrounds; use exactly these names)

Each one enters, floats, and exits with the graphics. If a file is missing, build a clean flat-vector stand-in in the same style, don't drop the beat.

| File | What it shows | Where it's used |
|---|---|---|
| `check.png` | A settlement check, photorealistic, blank payee, slightly 3/4 angle | Beat 1 |
| `envelope.png` | An opened insurance envelope with a letter peeking out | Beat 2 |
| `release.png` | A one-page "Release of All Claims" document, slight perspective | Beat 3 |
| `pen.png` | A pen, angled, tip toward lower-left | Beat 3 |
| `brace.png` | A neck brace or an X-ray on a lightbox (treatment still ongoing) | Beat 3b |
| `phone.png` | A phone with the awesomeattorneys.com "Find a lawyer" page on screen (web-capture the page and mount it in the phone if there's no screenshot) | Beat 4 |
| `skyline.png` | Phoenix skyline / Camelback silhouette, flat cutout, single color | Beat 4 |
| `logo.svg` | Awesome Attorneys wordmark | Beats 4–5 |

Image treatment: a soft drop shadow (`0 24px 48px rgba(0,0,0,0.25)`) on cream, a subtle rim glow on black; slight rotation (−8° to +8°) so nothing is square to the frame; scale so the object occupies 45–60% of frame width. Images never overlap live text.

## 4. Motion system (this is what "extremely smooth" means here)

- **Easing**: slides and reveals use expo-out (`cubic-bezier(0.16, 1, 0.3, 1)`); exits use expo-in (`0.7, 0, 0.84, 0`); the few "pops" (accent words, stamps, the CTA lines) use a back-out with ≤ 8% overshoot. Never linear. Never opacity-only: every appearance pairs opacity with a translate, scale (0.92→1) or rotation.
- **Word-by-word text**: each word pops in on its timestamp (see §5) with translateY 18px → 0 and scale 0.94 → 1 over 0.22s; the accent word arrives 0.06s later with the overshoot pop. Previous words of the same sentence stay; the sentence leaves as a block with the background flip.
- **Images**: enter over 0.45s from off-frame (slide + rotate from ±14° to their rest angle + scale 0.85 → 1). While on screen they **float**: translateY ±6px on a 3.2s sine and rotate ±1.5° on a 4.7s sine, both read from `useTime()` so they're deterministic. They exit with the sentence (slide out the way they came, 0.3s expo-in) or are wiped by the transition.
- **Background pattern**: the dotted grid drifts at 8px per second diagonally (parallax: it moves at ~30% of the speed of foreground slides during transitions).
- **The road**: a thick grey winding path (SVG, 26px stroke, round caps) lives in beats 2–3. It draws on with `stroke-dashoffset` over 0.6s when it first appears and keeps a slow 0.5px/s drift; objects sit on or beside it.
- **Transitions**: hard cut + background flip on sentence boundaries; one **circle wipe** (a black circle expanding from center to cover the frame, 0.45s expo-in-out) going into the brand beat; a **top-down card slide** (the new background slides in over the old, 0.4s) into the CTA.
- **Continuity**: something is always moving, but only one thing is *fast* at a time. Camera-style breathing on the whole stage: scale 1.00 → 1.02 across each beat, reset on the cut.
- Keep any single move ≥ 0.25s; at 60fps that stays smooth without motion blur.

## 5. Timing (measured from `voiceover.mp3`; sentence boundaries are exact, word times inside a sentence are estimates — nudge them by ear in preview)

Hits land **0.05s before** the word is heard.

| Time | Voice | Visual event |
|---|---|---|
| 0.00–0.13 | (silence) | Cream background, grid, small logo watermark top-left, `@AwesomeAttys` bottom-right. Nothing else. |
| 0.13 | The first | "The first" pops in, upper-middle. `check.png` slides in from bottom-right to center-right, rotated −8°. |
| 0.55 | offer | "offer" |
| 0.85 | is almost | "is almost" |
| 1.30 | never | accent **never** (brand red, overshoot pop). The check shrinks 6% and a red outline "FIRST OFFER" stamp (rotated −12°) slaps onto it. |
| 1.60 | the best | "the best" |
| 2.05 | offer | "offer." The stamp settles. |
| 2.55–3.15 | (pause) | Hold. Check floats. |
| 3.15 | Insurance companies | **Flip to black.** White glowing text "Insurance companies", `envelope.png` slides in from the left, lower third. The road path begins drawing from the bottom-left. |
| 4.05 | open low, | accent **low** (`brandBright`). A short bar chart to the right of the envelope: one stubby bar rises a little and stops. |
| 4.75 | because most people | "because most people" |
| 5.65 | accept | accent **accept**; a pinned note card (grey, red pushpin) drops onto the road: title "Their offer", then three lines with icons check in one by one: "Low number", "Short deadline", "Hoping you sign". |
| 6.15 | early. | "early." Third note line lands. |
| 6.58–7.06 | (pause) | Hold. Envelope floats, note card sways 1°. |
| 7.06 | And once you | **Flip to cream.** The road continues across the cut. `release.png` slides in from the right, upper-middle, rotated +6°; `pen.png` follows 0.12s later, tip near the signature line. |
| 7.65 | sign | accent **sign**: a signature draws on the document (SVG path, 0.5s). |
| 8.05 | that release, | "that release," |
| 8.60 | your case | "your case" |
| 9.35 | is over | accent **over**: a red "CASE CLOSED" stamp slaps the document, document tilts 3°, pen falls out of frame. |
| 9.71–10.04 | (pause) | Hold. |
| 10.04 | even if your | "even if your" (new line, lower). |
| 10.65 | treatment | accent **treatment**: `brace.png` slides in from the left with a small progress bar beneath it reading "TREATMENT · 40%", the bar visibly still filling. |
| 11.20 | isn't. | "isn't." The progress bar keeps moving; the closed document does not. That contrast is the point. |
| 11.72–12.43 | (pause) | **Circle wipe** to the brand beat (black circle expands from center, 0.45s). |
| 12.43 | Awesome Attorneys | Background `brand` red. The wordmark scales in center; a thin white circle draws around it (0.5s). |
| 13.45 | matches you | "matches you" white; two dots labeled YOU / ATTORNEY appear left and right. |
| 13.95 | directly | accent **directly** (white, overshoot): a line snaps between the dots; two faint middle dots vanish. |
| 14.70 | with a Phoenix | `skyline.png` rises into the bottom 22% as a flat cutout; "with a Phoenix" |
| 15.50 | injury attorney. | `phone.png` slides in from the right, center, showing the site; "injury attorney." Circle around the wordmark fades. |
| 16.19–16.55 | (pause) | **Card slide** to cream. |
| 16.55 | Get Matched. | "GET MATCHED." hero line, ink, back-out pop. |
| 17.38 | Get Paid. | "GET PAID." beneath, `brand` red, same pop. |
| 18.32 | AwesomeAttorneys dot com. | Both lines ease up 80px and scale to 70%; "AwesomeAttorneys.com" appears beneath in ink with "Attorneys" in `brand`; the site's **Get Matched** button scales in under it and breathes (scale 1.00–1.03, 1.6s sine). |
| 20.04–22.5 | (end card hold) | Wordmark, URL, button, and the small disclaimer line at the bottom safe area: "Awesome Attorneys is not a law firm and does not provide legal advice." Last 0.5s completely still. |

## 6. Controls panel (data-export-hide)

Give me a small control panel next to the canvas: an accent color swatch (`brand`), a font selector (Inter / site font), a "captions size" slider, a text field for the disclaimer, and a global "timing offset" number (±0.3s) that shifts every visual event so I can dial in sync against the voice without editing code. Also a "show safe zones" toggle.

## 7. Quality checks before you hand it back

1. Scrub to 1.30, 5.65, 7.65, 9.35, 10.65, 13.95, 16.55, 17.38 and 18.32: the accent event must be *starting* at each of those times.
2. Play with the voice: no word appears after it's spoken; nothing pops on at t=0; nothing moves in the last 0.5s.
3. At any time, only one element is moving fast; images are always floating; no element is ever perfectly static except in the end card.
4. Nothing inside the top 14% / bottom 20%; no text overlapping an image; smallest text ≥ 30px.
5. Refresh and scrub to the same time twice: identical frame.

Then tell me: which cutouts you found vs. stood in for, any timestamp you moved by more than 0.1s and why, and the three frames you'd pick as thumbnails.
