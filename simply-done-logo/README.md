# Simply Done logo (hand-built vector)

Clean vector rebuild of the Simply Done "No Mess. No Stress." logo, for print
(car wrap). Every shape is drawn as a vector path made of straight lines and
smooth Bézier curves. Nothing is image-traced. The lettering is real
Montserrat type.

| File | Use |
|---|---|
| `simply-done-logo.svg` | Master editable file: **live text**, named groups (Illustrator, Inkscape, Affinity, Figma) |
| `simply-done-logo-outlined.svg` | Same artwork with all text converted to paths (no fonts needed) |
| `simply-done-logo.pdf` | Vector, made from the outlined SVG. Send this one to the wrap printer |
| `simply-done-logo.eps` | Vector, made from the outlined SVG. For legacy sign/print software |
| `simply-done-logo-300dpi.png` | 5000 × 4035 px, transparent, 300 DPI |
| `simply-done-logo.psd` | Layered Photoshop file, one layer per group, 5000 × 4035 px, 300 DPI |
| `preview/comparison.png` | Original vs previous traced version vs this rebuild |
| `preview/qa-zoom-400.png` | 400 % zoom checks (roof edge, valley, letter S, sparkle) |

## Groups / layers (bottom to top)

| Group | Contents |
|---|---|
| Background | hidden, empty |
| Hand & Tools | squeegee, gloved fist, broom (flat white shapes + one grey shadow each) |
| Roof | pink roof with chimney, white bevel band of even thickness, grey shadow line |
| Windows | two arched windows |
| Sparkles | 8 pink 4-point stars, one shared path reused with `<use>` |
| Text – Simply Done | SIMPLY / DONE, Montserrat Black 106 pt |
| Glints | 14 white 4-point stars with a soft glow, on top of the letters |
| Tagline | NO MESS. NO STRESS., Montserrat ExtraBold 30 pt on an editable arc (`#tagline-arc`) |

Sparkles, Text, Glints and Tagline sit inside a parent group `Lettering`
rotated −10.7°, so the text stays editable.

## Colours

| Swatch | Hex |
|---|---|
| Pink (roof, SIM / ONE, sparkles) | `#F0186A` |
| Black (PLY, D, tagline, window frames) | `#111111` |
| Mid grey shadow | `#5E5E63` |
| White (bevel, hand & tools) | `#F2F3F7` |
| Window glass | `#E6E7EB` |
| Glints | `#FFFFFF` |

The files are RGB. Ask the wrap printer for their CMYK or vinyl match for the
pink before printing.

## Fonts (only for the live-text SVG)

Install **Montserrat** (Black and ExtraBold weights) from Google Fonts:
https://fonts.google.com/specimen/Montserrat. If you can't install fonts, use
`simply-done-logo-outlined.svg`, the PDF or the EPS instead; they don't need
fonts.
