# Drop your inputs here

Nothing in this folder is required — every input has a documented default, and
`npm run assets` prints exactly which placeholders are still in play.

## The five files that matter most right now

The moving background and the signature end card are built and running on
placeholders. Drop these in and they become the real thing:

```
assets-in/
  bg/
    adjuster.jpg     the eye through the torn banknote
    silenced.jpg     Franklin gagged
    court.jpg        the Supreme Court
    counsel.jpg      the attorney on his feet in court
  endcard.png        the signature end card
```

Then:

```bash
npm run assets          # copies them in, samples the end card's maroon
npm run render:full     # the finished video, both aspects
```

**Naming.** Role names are matched first (`court.jpg`), so you can name them
however you like as long as the role word starts the filename. If none match,
the four images are taken in **alphabetical order** and mapped to the roles in
the order above — so `01.jpg 02.jpg 03.jpg 04.jpg` also works. `.jpg`, `.jpeg`,
`.png` and `.webp` are all fine.

**All four are needed** before the photography switches on. With fewer, the
backdrop keeps playing procedural gradients — the moves and the timing are
identical either way, so nothing else changes when they land.

**Which shot plays when** is in `src/timing/backdrops.ts`, expressed against the
voice-over rather than against frame numbers. Swapping the order is a matter of
renaming files; re-cutting the shots is a matter of editing that one table.

**Resolution.** They are scaled to *cover* the frame and then pushed in by up to
30%, so give them some headroom: 2000px on the long edge is comfortable for
1080p, 4000px if you want them to hold up in the 4K render.

**The end card** is placed, not rebuilt — nothing is drawn over it and it is
never cropped. `prepare-assets` samples its background colour and paints the
final "GET PAID." plate the same shade, so the plate becoming the card is a
dissolve of the content only and the join cannot be seen. 9:16 fills the frame;
16:9 centres the portrait card on its own colour rather than cropping it.

## Everything else

| File | What it does | If it's missing |
|---|---|---|
| `vo.mp3` | Final voice-over. `npm run vo` transcribes it and the whole piece re-times to the real read. | The spec §4.2 fallback timing table |
| `brand.json` | `{ "font": "...", "gold": "#RRGGBB", "ink": "#RRGGBB" }` | Manrope / `#E4B85A` / `#0B1220` |
| `logo.svg` or `logo.png` | Wordmark, used at the same height as the typographic one. Needs a transparent background. | Typographic: AWESOME white 800 over ATTORNEYS gold 800 |
| `reference.mp4` | Style reference. Build a contact sheet before changing the design: `ffmpeg -i assets-in/reference.mp4 -vf "fps=2,scale=320:-1,tile=6x6" -frames:v 1 ref.png` | The design as built |
| `broll/*.mp4` | Sample footage, **for legibility QA only** — never rendered into the overlay. | QA composites over flat grey / white / near-black plates |

After adding anything:

```bash
npm run assets       # copies into public/, regenerates brand + font
npm run vo           # only if you added vo.mp3
npm run sync-sheet
npm run render:all   # alpha overlays + finished videos
```

`brand.json` font names must be a Google Font that publishes weights 500, 700
and 800 — those are the three the design system uses. The name is matched the
way `@remotion/google-fonts` spells it (`"Inter Tight"`, `"Manrope"`).
