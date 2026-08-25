# Awesome Attorneys — motion graphics

Remotion project for the Walmart verdict spot.

## Running

```bash
npm install
npm run dev              # Remotion Studio
npm run render Scene01Hook out/scene01-hook.mp4
npm run sync-assets      # after adding art to public/assets
```

## Compositions

| ID | Duration | Format | Covers |
| --- | --- | --- | --- |
| `Scene01Hook` | 5s (150f @ 30fps) | 1080x1920 | "Nearly seventeen million dollars… because a grandmother went shopping at Walmart." |

## Scene 01 beat map

Frame numbers live in `BEAT` at the top of `src/scenes/Scene01Hook.tsx`. Visuals
intentionally lead the voiceover by a few frames — a title landing exactly on its
word reads as late.

| Frame | Beat |
| --- | --- |
| 0–12 | Fade up on the money plate, slow push-in begins |
| 8–56 | `NEARLY` + figure counts up, lands hard on 56 |
| 56–74 | Figure holds still under "…dollars" |
| 74–86 | Figure recedes and blurs out |
| 78 | `BECAUSE A GRANDMOTHER` rises word by word |
| 104 | `WENT SHOPPING AT` |
| 114 | Walmart lockup snaps in, single specular sweep, blue wash creeps up |

## Notes

- **Fonts are self-hosted** in `public/fonts` (Anton, Archivo). The render browser
  does not trust this environment's proxy CA, so pulling from Google's CDN fails
  mid-render; self-hosting keeps renders offline and deterministic.
- **Rendering needs Remotion's own browser** — `npx remotion browser ensure`. The
  preinstalled Playwright Chromium has old-headless removed and will not launch.
- The headline figure is set to `17_000_000` in `Scene01Hook.tsx` to match the
  "nearly seventeen million" read. Change the `target` prop for the exact verdict.
