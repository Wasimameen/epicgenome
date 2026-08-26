# Drop your inputs here

Nothing in this folder is required — every input has a documented default, and
`npm run assets` prints exactly which placeholders are still in play.

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
npm run render:all
```

`brand.json` font names must be a Google Font that publishes weights 500, 700 and
800 — those are the three the design system uses. The name is matched the way
`@remotion/google-fonts` spells it (`"Inter Tight"`, `"Manrope"`).
