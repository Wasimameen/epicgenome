# AA40K — "40% At Fault" kinetic-typography overlay

A transparent-background motion-graphics overlay built in Remotion. Output is
Apple ProRes 4444 `.mov` with a real alpha channel, designed to sit on the track
above your own B-roll.

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
