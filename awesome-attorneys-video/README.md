# The First Offer — 9:16 reel

`the-first-offer.mp4` — 1080×1920, 22.5s, 60fps, H.264, voice-over muxed at t=0.

```
reel.html      the animation. Open it directly to scrub, tune and preview with audio.
render.py      renders reel.html to frames and encodes the MP4.
check.py       runs the §7 quality checks that can be verified mechanically.
DATA.md        the measured source data this was built from.
assets/        voiceover.mp3, the embedded Fraunces + Inter subsets, brand reference.
```

Regenerate: `python3 render.py` (≈6 min). Probe a handful of key frames instead
with `python3 render.py probe`. Verify with `python3 check.py`.

## How this differs from the brief, and why

**The renderer.** §1 requires `copy_starter_component` with kind `animations.jsx`.
That tool belongs to Claude Design and isn't available in this environment, so the
animation is a deterministic `render(t)` page rendered frame-by-frame through
headless Chromium and encoded with ffmpeg. Every constraint behind that
requirement still holds and is enforced: one 1080×1920 / 22.5s / 60fps timeline,
every frame a pure function of the playhead, all motion tweened with
`interpolate`-style easing off `useTime()`-equivalent `t`, no CSS
animation/transition, no `Date.now`, `performance.now`, `Math.random`,
`setTimeout`, `setInterval`, or rAF-derived timing anywhere in the frame
function. The float and breathing "randomness" is a seeded sine of `t`.
`reel.html` is a drop-in reference if you later rebuild it on the Stage starter.

**Two typefaces, not one.** §2 says "one family, Inter (or the site's font if web
capture finds one)". Web capture found two — Fraunces (headings, wordmark) and
Inter (body) — so display copy is Fraunces 600 and labels are Inter 600. See
DATA.md.

**Palette.** The brief's `#8A2326` is confirmed exactly by the site's
`theme-color`. Six of its other seven tokens were approximations of the site's
real theme presets, so cream is `#FBF7EF`, ink `#14110F` and secondary
`#4A443C`. The invented `brandBright #E0393F` is replaced by the site's own
`brass #B68A4E` for accents on black; `#0A0A0A` is kept as an art-direction
choice since the site has no true-black surface.

**`logo.svg`.** The site has no logo file — the wordmark is live text in a
`wp-block-site-title`. It is set as Fraunces 600 text throughout, which is what
the site actually renders.

## Cutouts: found vs stood in for

**None of the seven §3 PNGs were supplied**, so all seven are flat-vector
stand-ins drawn in one consistent style, per §3's fallback rule:

| File | Stand-in |
|---|---|
| `check.png` | settlement cheque, oxblood banner, blank payee, signature rule |
| `envelope.png` | opened envelope with the letter rising out of it |
| `release.png` | one-page "Release of All Claims" with a signature rule |
| `pen.png` | angled pen, brass bands, tip toward lower-left |
| `brace.png` | X-ray on a lightbox (the §3 alternative to a neck brace) |
| `phone.png` | phone showing the site's Find-a-lawyer list and Get Matched button |
| `skyline.png` | flat single-colour Phoenix skyline with Camelback at left |

Four images pasted into the chat — a skyline, a money bag, a fountain pen and a
dollar-under-umbrella — arrived as inline images rather than files, so they
aren't on disk and could not be wired in. Supply them as files named per §3 and
`reel.html` will pick them up in place of the stand-ins.

## Timestamps moved by more than 0.1s

Every §5 sentence boundary was confirmed correct to within 0.02s and left alone.
The word times inside sentences were estimates, and eleven moved once measured;
the eight that moved by more than 0.1s:

| Brief | Now | Δ | Why |
|---|---|---|---|
| 4.05 | **4.31** | +0.26 | The accent is *low*, but 4.05 is where *open* starts. "low" is at 4.360. The bar chart was firing before the word. |
| 14.70 | **14.27** | −0.43 | "with" starts at 14.320. The whole brand beat is written slower than spoken. |
| 15.50 | **15.09** | −0.41 | "Injury" starts at 15.140 — `phone.png` was entering ~0.4s late. |
| 13.45 | **13.11** | −0.34 | "matches" starts at 13.160, same compressed sentence. |
| 11.20 | **11.05** | −0.15 | "isn't" starts at 11.100. |
| 8.60 | **8.73** | +0.13 | "your" starts at 8.780 after a sub-threshold breath. |
| 0.55 / 0.85 | **0.43 / 0.73** | −0.12 | "offer" 0.480, "is" 0.780. |
| 6.15 | **6.03** | −0.12 | "early" starts at 6.080. |

Three more moved by ≤0.11 ("never" 1.30→1.19, "directly" 13.95→13.83, "because"
4.75→4.65). All are reachable without editing code via the timing-offset control.

## Three frames for thumbnails

1. **t≈9.3** — the pen finishing the signature on "Release of All Claims" as
   CASE CLOSED lands. The single clearest image of the stakes.
2. **t≈15.4** — the wordmark ringed on brand red, phone and Phoenix skyline
   below. The most on-brand frame and the only one carrying the product.
3. **t≈1.45** — "never" in oxblood over the settlement cheque with the FIRST
   OFFER stamp. Best hook frame: it states the claim in three words.

## Controls

Open `reel.html` for a panel (excluded from the export) with play/scrub against
the voice-over, a global ±0.3s timing offset, accent swatch, Fraunces/Inter
selector, captions-size slider, a disclaimer field and a safe-zone overlay.
