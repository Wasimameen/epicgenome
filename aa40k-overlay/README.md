# AA40K — "40% At Fault" kinetic typography

Built in Remotion. Renders two ways from one source:

- **the finished video** — `AA40K-9x16-Full` / `AA40K-16x9-Full`, with the
  moving photographic background composed in. H.264 MP4, ready to post.
- **the overlay on its own** — `AA40K-9x16` / `AA40K-16x9`, ProRes 4444 with a
  real alpha channel, for dropping onto your own B-roll.

The only difference between them is the `backdrop` prop.

**If you just want to use the files, read [`out/README.md`](out/README.md).** This
file is about the code.

```bash
npm install
npm run dev            # Remotion Studio
npm run render:all     # every deliverable
```

## The idea

Words live at fixed positions in a 3D world and a camera flies between them.
That's the whole architecture — everything else follows from it.

- **One world, one camera.** `src/stage/flight.ts` declares where every word *is*
  and where the camera goes. Beats render type at those poses; `<Camera3D>` flies
  between the same ones. A word and the camera can never disagree.
- **Authored in screen pixels.** A pose is written as the screen offset a word
  should hold when the camera rests on it; `poseFromScreen()` inverts the
  perspective projection. That is what makes the safe zones checkable numbers
  instead of guesses.
- **Everything is seconds.** No scene names a frame. `beats.ts` holds sync points
  in seconds; `useSec()` / `useHit()` convert using the composition's fps. One
  constant — `FPS` in `Root.tsx` — re-times the entire piece.

## Layout

```
src/
  Root.tsx              the four compositions + the single FPS constant
  Overlay.tsx           layer order: particles -> 3D stage -> card plates
  FrameLayer.tsx        the optional vignette / letterbox pass
  theme.ts              colour, type scale, safe zones, per-aspect layout tokens
  types.ts              BeatProps / OverlayProps
  font.ts               GENERATED — vendored typeface + delayRender gate
  brand.generated.ts    GENERATED — from assets-in/brand.json
  timing/
    vo-words.json       whisper output, or the fallback marker
    beats.ts            typed sync points, beat windows, LEAD
  stage/
    Camera3D.tsx        perspective root + inverse transform, flights, FramePunch
    flight.ts           poses, flight plan, drifts, punches, motion-blur hints
    Word.tsx            Posed (3D citizen with arrive/demote/leave) and Word
    CardPlate.tsx       opaque plates + the end-card scrim
  beats/                Beat1..Beat4 — one per line of the script
  parts/                StampBox Strike MatchLine Pin Chip Wordmark Pill
                        Particles Disclaimer
  overlays/lib.tsx      useSec, useHit, useInOut, MaskReveal, Reveal, useLoop,
                        useBreath, SpeedTrail, easings, spring configs
scripts/
  prepare-assets.mjs    assets-in/ -> public/, regenerates brand.generated.ts
  vendor-fonts.mjs      downloads the typeface into public/fonts/
  transcribe-vo.mjs     whisper.cpp -> src/timing/vo-words.json
  sync-sheet.mjs        out/sync-sheet.md
  stills.mjs            the three reference stills
  qa.mjs                alpha probe, frame extraction, plate composites
```

## The moving background

`src/parts/Backdrop.tsx` + `src/timing/backdrops.ts`. Three things happen at
once, and together they are what stops a photograph behind type reading as
wallpaper:

1. **Ken Burns** — every shot pushes in or pulls back across its whole life,
   alternating direction so two consecutive shots never drift the same way.
2. **Camera parallax** — the backdrop is driven by the *same* camera that flies
   between the words, at about a twentieth of the travel. When the camera whips
   to "OPENING" the photograph leans with it, so the type and the picture read
   as one shot rather than two layers.
3. **The frame punch** — it sits inside `<FramePunch>`, so the three 1-frame
   hits land on the photograph too.

Everything is then graded down — desaturated, darkened, ink-tinted, vignetted —
so the palette stays white/gold/ink and the type keeps its contrast.

Two of the three transitions are hidden entirely: `silenced` → `court`
cross-fades underneath the opaque "NOT / A LEGAL FINDING" plate, and
`counsel` → end card is covered by the gold "GET MATCHED." slam. A cut you
never see is the most seamless kind.

With no images in `assets-in/bg/` the same moves play over procedural
gradients, so the timing can be judged before the photography lands.

## Two decisions worth knowing about

**Motion blur is `<Trail>`, driven by measured speed.** `<Trail>` stacks frozen
copies of its children *behind* the live one, so when nothing moves the copies sit
exactly under it and the component is a visual no-op. That means it can stay
mounted for the whole piece and never pop in or out — `SpeedTrail` just ramps
`trailOpacity` with the stage's actual px/frame. `CameraMotionBlur` was the
obvious alternative but it composites with `mix-blend-mode: plus-lighter`, which
the alpha rules rule out.

**The typeface is vendored, not fetched.** `@remotion/google-fonts` still supplies
the family name and the woff2 URL, but `vendor-fonts.mjs` downloads the file into
`public/fonts/` and `font.ts` loads it from disk behind a `delayRender()`. Renders
are then offline-safe and byte-identical between machines — worth more than the
convenience of a runtime fetch when the piece will be re-rendered every time the
voice-over changes.

## Rules the code holds itself to

- No background anywhere except the card plates and the end-card scrim.
- No `backdrop-filter`, no `mix-blend-mode` — nothing blends with your footage at
  render time. Glows are real pixels.
- Compound entrances only: mask, translate and scale together. Never an
  opacity-only fade.
- Transforms only. Nothing animates `left` / `top`, and nothing is snapped to
  whole pixels mid-motion.
- Deterministic: seeded `random()`, no timers, no CSS transitions or animations,
  no `Math.random()`.
- Overdamped springs for entrances, expo-in for exits, expo-in-out for camera
  flights. Exactly three overshoot springs in the piece: the "40%" slam and the
  two card slams.
