# Simply Done logo (vector, matched to the original)

Clean vector rebuild of the Simply Done "No Mess. No Stress." logo, matched
to the original PNG for print (car wrap). Every shape is built from straight
lines and a few smooth Bézier curves; positions were measured from the
original with least-squares edge fits. Nothing is image-traced. The lettering
is real Montserrat type.

| File | Use |
|---|---|
| `simply-done-logo.svg` | Master editable file: **live text**, named groups (Illustrator, Inkscape, Affinity, Figma) |
| `simply-done-logo-outlined.svg` | Same artwork with all text converted to paths (no fonts needed) |
| `simply-done-logo.pdf` | Vector, made from the outlined SVG. Send this one to the wrap printer |
| `simply-done-logo.eps` | Vector, made from the outlined SVG. For legacy sign/print software |
| `simply-done-logo-300dpi.png` | 5000 × 4035 px, transparent, 300 DPI |
| `simply-done-logo.psd` | Layered Photoshop file, one layer per group, 5000 × 4035 px, 300 DPI |
| `preview/comparison.png` | Original vs previous version vs this version |
| `preview/qa-zoom-400.png` | 400 % zoom checks (roof, valley, S + glint, sparkle, chimney, fist) |

## Groups / layers (bottom to top)

| Group | Contents |
|---|---|
| Background | hidden, empty |
| Hand & Tools | squeegee, glove cuff + fist, broom; white faces with a dark extruded side to the lower left |
| Roof | pink roof + chimney, dark-pink underside, white bevel (with the open gap on the steep slopes), grey shadow line |
| Windows | two arched windows (dark frame, graded glass, sill) |
| Sparkles | 8 pink 4-point stars, one shared path reused with `<use>` |
| Text – Simply Done | SIMPLY / DONE, Montserrat Bold 104.2 pt, horizontal scale 113.7 % |
| Glints | 14 lens-flare glints (glow + thin rays), clipped to the letters |
| Tagline | NO MESS. NO STRESS., Montserrat ExtraBold 29.7 pt on an editable arc (`#tagline-arc`) |

Sparkles, Text, Glints and Tagline sit inside a parent group `Lettering`
rotated −10.7°, the tilt measured on the original.

## Colours (sampled from the original)

| Swatch | Hex |
|---|---|
| Pink (roof, SIM / ONE, sparkles) | `#FF1461` |
| Dark pink roof underside | `#881152` |
| Black (PLY, D) | `#0F0E0E` |
| Tagline | `#181816` |
| White (bevel, hand & tools) | `#E8EBF0` |
| Roof shadow line | `#5C5B5F` |
| Tool shadow | `#4B4B4F` |
| Window frame | `#2E3032` |

The files are RGB. Ask the wrap printer for their CMYK or vinyl match for the
pink before printing.

## Fonts (only for the live-text SVG)

Install **Montserrat** (Bold and ExtraBold weights) from Google Fonts:
https://fonts.google.com/specimen/Montserrat. If you can't install fonts, use
`simply-done-logo-outlined.svg`, the PDF or the EPS instead; they don't need
fonts.
