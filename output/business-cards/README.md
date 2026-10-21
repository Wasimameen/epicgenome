# Simply Done – business cards

Double-sided business card for Simone Lebherz-Kann, built from the clean vector
Simply Done logo (`../../simply-done-logo/`). The layout follows the client's
old cards; the artwork and all details are new.

## Files

| File | Use |
|---|---|
| `business-card-print.pdf` | **Send to the printer.** 2 pages (front, back), CMYK, text outlined, crop marks |
| `business-card-print-no-marks.pdf` | Same, page = 97 × 61 mm exactly with no marks, for online printers that reject crop marks |
| `business-card-front.svg` | Front, editable with live text (Illustrator / Inkscape / Affinity) |
| `business-card-front-outlined.svg` | Front with text as shapes; use this if the fonts aren't installed (e.g. Photoshop) |
| `business-card-back.svg` | Back, editable (it has no text of its own; the logo is outlined) |
| `business-card-front.png`, `business-card-back.png` | 300 DPI previews at trim size, 1075 × 650 px |
| `business-card-mockup.png` | Both cards together, for presenting to the client |
| `qa-zoom-400.png` | 400 % zoom check rendered from the print PDF |

## Print specs

| | |
|---|---|
| Trim | 91 × 55 mm, landscape (Australian standard) |
| Bleed | 3 mm all sides (97 × 61 mm); both backgrounds run fully into the bleed |
| Safe zone | Everything is at least 4 mm inside the trim (front: 4.3 mm min, back: 7.8 mm min) |
| PDF boxes | `business-card-print.pdf`: page 111 × 75 mm (room for crop marks), BleedBox 97 × 61, TrimBox 91 × 55. `-no-marks`: page = BleedBox 97 × 61, TrimBox 91 × 55 |
| Colour | CMYK, converted with Ghostscript (ICC). Text, icons, grey details and crop marks are black-only (K) ink; large black logo letters are rich black C60 M40 Y40 K100; max ink 240 % |
| Content | 100 % vector, no fonts, no images; transparency blends in CMYK |

## Colours

| Element | RGB (SVG) | CMYK (print PDF) |
|---|---|---|
| Back background | `#F0186A` | C0 M98 Y35 K0 |
| Logo pink (front) | `#FF1461` | C0 M98 Y43 K0 |
| Name, contact lines, icons | `#333333` | K80 |
| Title | `#6B6B6B` | K58 |
| Black logo letters | `#0F0E0E` | C60 M40 Y40 K100 |
| Logo tagline | `#181816` | K100 |

Pink is out of the CMYK range, so it will print slightly duller than on screen; a
hard proof from the printer is recommended.

## Type

| Line | Font | Size |
|---|---|---|
| Name | Zilla Slab SemiBold | 11 pt |
| OWNER / OPERATOR | Montserrat Regular, tracking 180 | 6 pt |
| Phone, email, website, ABN | Montserrat Regular | 6.75 pt |

To edit `business-card-front.svg`, install **Zilla Slab** and **Montserrat**
from Google Fonts. The print PDF and `business-card-front-outlined.svg` need no
fonts.

## Logo on the cards

- Front: full-colour logo, rotated +10.7° so the lettering sits level (as on the
  old cards), 37 mm wide (41 % of the card). It's slightly smaller than 45–50 %
  so the four contact lines fit inside the safe zone.
- Back: the white variant (`simply-done-logo-white-variant.*`), 62 mm wide (68 %).
- On the cards, the glint glows are stacked semi-transparent circles and the
  window glass is a flat grey, so the CMYK conversion stays 100 % vector (no
  rasterised gradients). They look the same at card size.
