# Source art

Drop the supplied images in here using these exact filenames, then run
`npm run sync-assets` from `video/`. The manifest at `src/assets.ts` is
regenerated from whatever is present; any file still missing falls back to a
drawn stand-in rather than breaking the render.

| Filename | Image | Used in |
| --- | --- | --- |
| `franklin.jpg` | Macro of Franklin's eyes on a $100 bill | Scenes 01, 08 (full-frame plate) |
| `walmart-logo.png` | Walmart wordmark + spark lockup | Scenes 01, 06 |
| `walmart-spark.png` | Spark mark alone | accents |
| `cash-stacks.jpg` | Banded bundles under the banker's lamp | Scene 07 |
| `bill.png` | ONE bill, cut out on transparency | Scenes 02, 08, 09 cash fall |
| `falling-bills.png` | Falling bills sheet | optional full-frame overlay |
| `cart.png` | Loaded shopping cart cutout | Scenes 03, 04 |
| `grandma.png` | Elderly woman cutout | Scenes 03, 04 |
| `brand-logo.png` | Awesome Attorneys logo | Scene 09 |

## Cutouts must be transparent

`cart.png`, `grandma.png` and `bill.png` are composited over dark scenes and are
rotated in flight. Anything supplied on a white background will show as a white
box. If the originals have white behind them, they need keying first.

`bill.png` should be a **single** note, not a sheet of them — the cash fall
places, rotates and flips each bill individually, which a pre-composed sheet
cannot do.
