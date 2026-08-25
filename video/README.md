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

## Voiceover sync

`src/timeline.ts` is derived from word-level timestamps of `public/audio/vo.mp3`
(62.04s), not estimated. Scene boundaries come from `BOUNDS`, and inside a scene
every cue is written as `cue('sceneId', <seconds into the VO>)` so it reads
against the script rather than as a magic frame number.

Titles are placed a few frames *ahead* of the word they illustrate — a title
landing exactly on its read feels late.

If the voiceover is re-recorded, re-derive the timings rather than nudging them:

```bash
pip install faster-whisper
python3 -c "
from faster_whisper import WhisperModel
m = WhisperModel('base.en', device='cpu', compute_type='int8')
segs, _ = m.transcribe('public/audio/vo.mp3', word_timestamps=True)
for s in segs:
    for w in s.words: print(f'{w.start:6.2f} {w.word}')
"
```

## Live footage

`public/video/capitol.mp4` is the supplied Capitol dome plate, used in the
appeal and verdict beats. It is 720x1080 daylight on blue sky, so `FootagePlate`
both upscales it to cover 9:16 and crushes/warms it into the reel's palette —
dropped in raw it tears a hole in a dark cut. Its own audio track is stripped;
only the voiceover sits on the timeline.

## Transparent / alpha version

`ReelAlpha` is the same timeline with every background-only layer dropped —
ground fills, the money plate, the Capitol footage, the vignette and the grain.
Additive passes (bloom, rays, dust, glows, flashes) are kept, since those are
graphics rather than ground. Scenes read `useTransparent()` from `src/alpha.ts`.

```bash
# ProRes 4444 master with alpha (~2.5 GB for 62.5s)
npx remotion render ReelAlpha out/reel-alpha.mov \
  --codec=prores --prores-profile=4444 \
  --pixel-format=yuva444p10le --image-format=png

# Smaller alpha file for review / web
npx remotion render ReelAlpha out/reel-alpha.webm \
  --codec=vp8 --image-format=png
```

**`--pixel-format=yuva444p10le` is required.** Without it Remotion writes a
ProRes 4444 file whose pixel format is `yuv422p12le` — the profile says 4444 but
there is no alpha plane, and the result is silently opaque. Verify any alpha
render before shipping it:

```bash
ffprobe -v error -show_entries stream=pix_fmt -of csv=p=0 out/reel-alpha.mov
# must report yuva444p10le / yuva444p12le, not yuv422p12le
```

Alternative alpha codecs, measured on this reel: QuickTime Animation
(`-c:v qtrle -pix_fmt argb`) lands around 1.9 GB, VP9 WebM around 25 MB.
