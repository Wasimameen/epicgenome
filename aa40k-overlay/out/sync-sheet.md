# Sync sheet — "40% At Fault" overlay

Frame **0 of the .mov is the first frame of the voice-over**. Line the overlay's
in-point up with the VO's in-point in your timeline and everything below is
where it says it is.

- **Frame rate:** 30 fps (`FPS` in `src/Root.tsx` — change it there and nothing else)
- **Total length:** 18.00s = 540 frames
- **Lead:** every visual lands **3 frames before** its word is spoken
- **Timing source:** **fallback table (spec §4.2)** — no `assets-in/vo.mp3` was supplied. Drop the final VO there, run `npm run vo`, then re-render; every beat re-derives with no other edit.

## Key words

| Beat | Key | Spoken | Time | TC (mm:ss:ff) | Spoken frame | **Visual lands** |
|---|---|---|---|---|---|---|
| 1 | `adjuster` | adjuster | 0.55s | 00:00:17 | 17 | **14** |
| 1 | `youre` | you're | 1.25s | 00:01:08 | 38 | **35** |
| 1 | `forty` | forty | 1.60s | 00:01:18 | 48 | **45** |
| 1 | `percent` | percent | 2.00s | 00:02:00 | 60 | **57** |
| 1 | `fault` | fault | 2.65s | 00:02:19 | 80 | **77** |
| 2 | `thats` | that's | 3.60s | 00:03:18 | 108 | **105** |
| 2 | `opening` | opening | 4.40s | 00:04:12 | 132 | **129** |
| 2 | `position` | position | 4.90s | 00:04:27 | 147 | **144** |
| 2 | `not` | not | 5.80s | 00:05:24 | 174 | **171** |
| 2 | `legal` | legal | 6.10s | 00:06:03 | 183 | **180** |
| 2 | `finding` | finding | 6.40s | 00:06:12 | 192 | **189** |
| 3 | `awesome` | Awesome (Attorneys) | 7.40s | 00:07:12 | 222 | **219** |
| 3 | `matches` | matches | 8.50s | 00:08:15 | 255 | **252** |
| 3 | `directly` | directly | 9.20s | 00:09:06 | 276 | **273** |
| 3 | `phoenix` | Phoenix | 10.20s | 00:10:06 | 306 | **303** |
| 3 | `injury` | injury | 10.70s | 00:10:21 | 321 | **318** |
| 3 | `attorney` | attorney | 11.10s | 00:11:03 | 333 | **330** |
| 4 | `getMatched` | Matched (Get Matched.) | 12.45s | 00:12:13 | 374 | **371** |
| 4 | `getPaid` | Paid (Get Paid.) | 13.50s | 00:13:15 | 405 | **402** |
| 4 | `url` | AwesomeAttorneys dot com | 14.60s | 00:14:18 | 438 | **435** |
| end | `end` | — end of VO, card holds — | 15.40s | 00:15:12 | 462 | **462** |

## Beat windows

| Beat | Start | End | Start frame | End frame | Length |
|---|---|---|---|---|---|
| 1 — deflated | 0.00s | 3.40s | 0 | 102 | 3.40s |
| 2 — knowing | 3.40s | 7.20s | 102 | 216 | 3.80s |
| 3 — warm, energetic | 7.20s | 12.00s | 216 | 360 | 4.80s |
| 4 — decisive + end card | 12.00s | 18.00s | 360 | 540 | 6.00s |

## Checking alignment in the editor

1. Put the overlay `.mov` on the track above your footage, both starting on the
   VO's first frame.
2. Park on a **Visual lands** frame from the table. The move for that word should
   have *started* on it and be settled about six frames later.
3. If the whole thing reads late or early, your VO in-point is off by that many
   frames — nudge the overlay, don't re-render.
