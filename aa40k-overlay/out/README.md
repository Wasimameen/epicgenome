# "40% At Fault"

Two families of output, for two different jobs.

### A — the finished video

`aa40k_9x16_full.mp4` and `aa40k_16x9_full.mp4`. The photography, the type and
the end card, all composed. Nothing to assemble — post it as it is.

The background is not a still. Every shot pushes in or pulls back across its
whole life, alternating direction so two consecutive shots never drift the same
way; and it is driven by the **same camera that flies between the words**, at
about a twentieth of the travel, so when the camera whips to "OPENING" the
photograph leans with it. The three 1-frame frame punches land on it too. The
type and the picture read as one shot rather than two layers.

Two of the three transitions you never see at all:

- **Franklin → Supreme Court** cross-fades entirely underneath the opaque
  "NOT / A LEGAL FINDING" plate. The Court is simply *there* when the card
  wipes away.
- **Courtroom → end card** is covered by the gold "GET MATCHED." slam.

Only the first, eye → Franklin, is an exposed dissolve, and it sits in beat 1's
still hold where it becomes the thing that keeps the hold alive.

### B — the alpha overlay

`aa40k_9x16_30fps_alpha.mov` and friends. **No background at all** — apart from
the card beats every pixel is graphics or transparent, so it drops on top of
your own B-roll. Use these if you want to art-direct the footage yourself.

Everything from §1 down is about family B.

---

## 1. Which file goes on which track

Bottom to top in your timeline:

| Track | File | Notes |
|---|---|---|
| 1 (bottom) | **your footage** | see §5 for what each beat was designed over |
| 2 | `aa40k_9x16_30fps_alpha.mov` | the overlay — type, icons, card plates |
| 3 (optional) | `frame_9x16_alpha.mov` | vignette. Add it per cut, or not at all |

For 16:9 use `aa40k_16x9_30fps_alpha.mov` and `frame_16x9_alpha.mov`. The 16:9
frame layer also carries **2.39:1 letterbox bars**; the 9:16 one is vignette only.

The frame layer is completely static — frame 0 is identical to the last frame —
so you can trim it, hold it or loop it to any length without a visible seam.

### The files

| File | What it is |
|---|---|
| `aa40k_9x16_full.mp4` | **the finished video.** 1080×1920, photography baked in, ready to post |
| `aa40k_16x9_full.mp4` | 1920×1080, same |
| `aa40k_9x16_30fps_alpha.mov` | the overlay on its own. 1080×1920, ProRes 4444, real alpha |
| `aa40k_16x9_30fps_alpha.mov` | 1920×1080, same piece re-laid-out (not a crop) |
| `frame_9x16_alpha.mov` | vignette only |
| `frame_16x9_alpha.mov` | vignette + 2.39 bars |
| `aa40k_9x16_4k_alpha.mov` | 2160×3840, for punching in on the timeline |
| `aa40k_9x16_30fps_alpha.webm` | VP9 + alpha fallback, if your editor drops the `.mov` alpha |
| `stills/` | three reference frames, plus grey-composited copies |
| `sync-sheet.md` | every key word → timestamp → frame |

---

## 2. Lining it up with the voice-over

**Frame 0 of the `.mov` is the first frame of the voice-over.** Put the overlay's
in-point on the VO's in-point and everything is in sync — there is no offset to
dial in and no handle to trim.

To check: park on any **Visual lands** frame in `sync-sheet.md`. The move for that
word should have *started* on that frame and be settled about six frames later.
Every visual deliberately leads its word by **3 frames**, because a graphic that
lands exactly on the syllable reads late.

If the whole piece feels uniformly early or late, your VO in-point is off by that
many frames — nudge the overlay clip, don't re-render.

---

## 3. Changing things

All three of these are props on the composition. Set them in the Remotion Studio
sidebar (`npm run dev`), or pass `--props` on the command line.

### `cards` — the opaque colour plates

`true` (default) keeps the three card beats: the ink **NOT / A LEGAL FINDING**
plate, the gold **GET MATCHED.** plate and the ink **GET PAID.** / end card. These
are the only fully opaque frames in the file.

`false` removes the plates entirely. The same type plays over your footage with
its shadows, the ink-coloured type is re-coloured white so it still reads, and the
end card gains a bottom scrim gradient so the URL survives any grade.

```bash
npx remotion render AA40K-9x16 out/aa40k_9x16_nocards.mov \
  --props='{"aspect":"9x16","cards":false,"tone":"mixed","disclaimer":"Attorney matching service. Not a law firm. Not legal advice."}' \
  --codec=prores --prores-profile=4444 --image-format=png --pixel-format=yuva444p10le --muted
```

### `tone` — shadow strength for your footage

Every piece of type over footage carries a two-part shadow. `tone` scales it:

- `dark` — footage is dark; lighter shadow, less halo
- `mixed` — **default**; the shadow the piece was designed with
- `light` — bright footage (a white sky, a snow plate); doubles the shadow

If white type is losing against a bright shot, raise `tone`, don't raise the font
size.

### `disclaimer`

The bottom line on the end card. Pass any string; it wraps inside the safe area.

### `accent`

Optional. Overrides the gold (`#E4B85A`) everywhere at once — the accent word, the
match line, the pin, the pill, the particles.

### Frame rate

`FPS` in `src/Root.tsx` is the **only** frame-rate constant in the project. Change
it to 24 or 60 and nothing else needs editing: every duration in the piece is
authored in seconds, and each composition's length is derived from it.

```ts
export const FPS = 24;   // src/Root.tsx
```

Then `npm run sync-sheet` (the sheet re-derives its frame numbers) and re-render.

---

## 4. Re-rendering after a new `vo.mp3`

Timing is derived from the voice-over, not typed in. Drop the new read in and the
whole piece re-times with no other edit:

```bash
cp /path/to/new-vo.mp3 assets-in/vo.mp3

npm run assets       # copies assets-in/ -> public/, refreshes brand + font
npm run vo           # transcribes with whisper.cpp (medium.en), writes src/timing/vo-words.json
npm run sync-sheet   # rewrites out/sync-sheet.md from the new timings
npm run render:all   # all six outputs
npm run stills       # the three reference stills
```

`npm run vo` downloads whisper.cpp and the `medium.en` model on first run
(~1.5 GB) and needs network access; everything else runs offline — the typeface is
vendored into `public/fonts/`.

If the transcription can't find all 20 key words it says so and **nothing is
overwritten**: the piece keeps the fallback timing table rather than half-syncing.

### Individual renders

```bash
npm run render:9x16         # the primary deliverable
npm run render:16x9
npm run render:frame-9x16
npm run render:frame-16x9
npm run render:full         # both finished videos
npm run render:full-9x16    # just the vertical one
npm run render:4k           # 2160x3840, --scale=2
npm run render:webm         # VP9 + alpha fallback (transcoded from the 9:16 master)
```

`render:webm` transcodes the ProRes master rather than re-rendering. Remotion
refuses to render when a ProRes profile is set and the codec isn't ProRes, and
the profile that makes a Studio export default to 4444 (i.e. to having alpha at
all) can't be unset per-command. Transcoding is the better answer anyway: the
webm comes out frame-identical to the master in a fraction of the time. It needs
`render:9x16` to have run first.

Or the raw commands, if you'd rather not go through npm:

```bash
npx remotion render AA40K-9x16 out/aa40k_9x16_30fps_alpha.mov \
  --codec=prores --prores-profile=4444 --image-format=png --pixel-format=yuva444p10le --muted
npx remotion render AA40K-16x9 out/aa40k_16x9_30fps_alpha.mov \
  --codec=prores --prores-profile=4444 --image-format=png --pixel-format=yuva444p10le --muted
npx remotion render FrameLayer-9x16 out/frame_9x16_alpha.mov \
  --codec=prores --prores-profile=4444 --image-format=png --pixel-format=yuva444p10le --muted
npx remotion render FrameLayer-16x9 out/frame_16x9_alpha.mov \
  --codec=prores --prores-profile=4444 --image-format=png --pixel-format=yuva444p10le --muted
npx remotion render AA40K-9x16 out/aa40k_9x16_4k_alpha.mov --scale=2 \
  --codec=prores --prores-profile=4444 --image-format=png --pixel-format=yuva444p10le --muted
npx remotion ffmpeg -y -i out/aa40k_9x16_30fps_alpha.mov \
  -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 28 -row-mt 1 -an \
  out/aa40k_9x16_30fps_alpha.webm
```

---

## 5. The shot list

What plays behind each beat in the finished video. The timings live in
`src/timing/backdrops.ts`, expressed against the voice-over rather than frame
numbers, so a new VO re-cuts the background along with everything else.

| Shot | Roughly | What it is | Move |
|---|---|---|---|
| `adjuster` | 0 – 3.7s | the eye through the torn banknote — the adjuster sizing you up through money | pushes in, settles |
| `silenced` | 3.1 – 6.9s | Franklin gagged — what their "opening position" is really doing to you | pulls back the other way |
| `court` | 6.4 – 9.0s | the Supreme Court — what an actual *legal finding* looks like | pushes in, drifts left |
| `counsel` | 8.4 – 12.4s | counsel on his feet — the attorney you get matched with | pulls back toward him |
| end card | 14.5 – 18.0s | the signature card | slow push, dead still for the last 0.5s |

To re-cut: rename the files in `assets-in/bg/` to change which photograph plays
which role, or edit the one table in `src/timing/backdrops.ts` to change when.

**If you are using the alpha overlay instead**, the beats were designed assuming
this underneath: beat 1 a claim letter or a damaged bumper, slow and desaturated;
beat 2 a person looking up, resolved, warmer; beat 3 Phoenix at golden hour, with
the overlay staying airy so the footage carries it. Between **11.93s and 12.35s**
the overlay is deliberately empty — a hard cut back to bare footage before the
closing card. Put something worth seeing there.

---

## 6. Checking the alpha yourself

```bash
# pixel format must be yuva444p10le
node scripts/qa.mjs probe out/aa40k_9x16_30fps_alpha.mov

# frame sets: raw RGBA, alpha matte, and composites over grey / white / near-black
node scripts/qa.mjs frames out/aa40k_9x16_30fps_alpha.mov 0 45,130,200,300,400 out/qa/f
```

The matte (`fN_alpha.png`) should be **black wherever the frame is empty**, show
only the graphics on footage beats, and be **fully white only inside a card
beat**. Frame 0 is entirely black.

**On the `.webm`:** VP9 stores alpha as a separate container-level layer, not in
the stream's pixel format — so `ffprobe` reports `pix_fmt=yuv420p` and the alpha
is flagged by the `alpha_mode=1` tag instead. `qa.mjs probe` knows this. If you
check it by hand, decode with `-c:v libvpx-vp9`; ffmpeg's *native* VP9 decoder
silently throws the alpha layer away and every matte comes out solid white.

### Safe zones, measured

```bash
npm run safe-zones -- out/aa40k_9x16_30fps_alpha.mov 9x16
npm run safe-zones -- out/aa40k_16x9_30fps_alpha.mov 16x9
```

This reads each frame's alpha channel and finds the bounding box of *solid*
pixels (alpha ≥ 0.85 — above the ambient particles and the shadows, so only real
type and icons are counted), then checks it against the safe box: clear of the
top 14% and bottom 22% on 9:16, 5% all round on 16:9. Frames that are a full card
plate are reported as `CARD` and skipped, and empty frames as `EMPTY`. It exits
non-zero if anything is out.

Pass your own frame list as a third argument if you want to check a specific
moment: `npm run safe-zones -- out/aa40k_9x16_30fps_alpha.mov 9x16 45,130,300`.

### Motion blur, measured

```bash
npm run motion-check -- 9x16
npm run motion-check -- 16x9
```

The stage's motion is pure and deterministic, so this evaluates it straight out
of the source — no render needed. For every frame it computes the stage's
screen-space speed and the motion blur that would be applied, and fails if
anything moves faster than 40px/frame without blur. It also prints the frame
ranges of every fast move, which is a useful map of where to scrub if you want
to eyeball the whips.

---

## 7. Regenerating the video files

The `.mov` files are **not in git** — an 18-second 1080×1920 ProRes 4444 file is
about 270 MB and the 4K one is over a gigabyte. Everything needed to rebuild them
byte-identically *is* committed, including the vendored typeface, so:

```bash
npm install
npm run render:all && npm run stills
```

Renders are deterministic: seeded `random()`, no timers, no `Math.random()`, no
network fetches at render time. The same commit produces the same frames on any
machine.
