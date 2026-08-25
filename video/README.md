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
| `Reel` | 62.04s (1861f @ 30fps) | 1080x1920 | Full spot, voiceover attached |
| `Scene01Hook` | 6.1s (183f @ 30fps) | 1080x1920 | Opening beat alone, for fast iteration |

## Timing

Scene boundaries are not estimated — they were derived from the supplied
voiceover by running silence detection at -34dB and cutting on the long pauses,
so every transition lands in a breath rather than over a word. Internal hits
within each scene sit on that scene's own shorter pauses.

Retime by editing `src/timeline.ts` alone. The voiceover is laid across the
whole timeline in `Reel.tsx` rather than per scene, so the read stays continuous
however the boundaries are nudged.

## Look

Shared atmosphere runs under every scene: airborne dust, volumetric shafts,
film grain and a heavy vignette. Impacts add decaying camera shake and RGB
fringing; both decay to nothing, because shake that never settles reads as a
broken camera rather than a hit.

The collision beat opens under a surveillance treatment — timecode, REC blink,
scanlines, tracking tears — which drops away on impact. It is staging as much as
motion: the line is "security tries to stop a shoplifter", so that is what the
moment looked like from the store's side.

The supplied Capitol footage carries the appeal beat, graded down hard
(desaturated, crushed, warmed) so daylight-on-blue-sky sits inside a dark cut.
It is withheld until the escalation lands — the building appearing at that exact
moment is the point.

## Notes

- **Fonts are self-hosted** in `public/fonts` (Anton, Archivo). The render browser
  does not trust this environment's proxy CA, so pulling from Google's CDN fails
  mid-render; self-hosting keeps renders offline and deterministic.
- **Rendering needs Remotion's own browser** — `npx remotion browser ensure`. The
  preinstalled Playwright Chromium has old-headless removed and will not launch.
- The headline figure is set to `17_000_000` in `Scene01Hook.tsx` to match the
  "nearly seventeen million" read. Change the `target` prop for the exact verdict.
