# Source art

Drop the supplied images in here using these exact filenames, then run
`npm run sync-assets` from `video/`. The manifest at `src/assets.ts` is
regenerated from whatever is present, and any file still missing falls back to a
procedural stand-in rather than breaking the render.

| Filename | Image |
| --- | --- |
| `franklin.jpg` | Macro of Franklin's eyes on a $100 bill — full-frame plate for the hook |
| `walmart-logo.png` | Walmart wordmark + spark lockup |
| `walmart-spark.png` | Spark mark on its own |
| `cash-stacks.jpg` | Banded bundles under the banker's lamp |
| `falling-bills.png` | Falling bills, pre-keyed on white |
| `cart.png` | Loaded shopping cart cutout |
| `grandma.png` | Elderly woman cutout |

Until `franklin.jpg` and `walmart-logo.png` are supplied, scene 01 renders a
generated engraved-banknote texture and a redrawn Walmart lockup. The redrawn
wordmark is set in Archivo, not Walmart's licensed Bogle, so it is close but not
exact — supplying the real logo file replaces it automatically.
