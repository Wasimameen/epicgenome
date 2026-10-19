# Restaurant — Atmospheric Collages · Art Direction & Build Conventions

Two A3 Photoshop collages (2.5D layered "atmosphere" studies) for a student restaurant
design (architecture/interior studio brief). Everything is built in code (Python + numpy/PIL/
OpenCV/scipy/scikit-image) and exported to a layered, non-destructive PSD via `src/psdkit.py`
(compositor) + `src/write_psd.js` (ag-psd writer). A flattened JPEG/PNG is rendered from the
same layers.

## The brief (client's words, condensed)
> Two Photoshop collages of sound, colour, smell, taste, texture… layers overlapping to build a
> general understanding of the place. 1) Looking FROM WITHIN the chosen area of the restaurant TO
> OUTSIDE views. 2) Looking TOWARDS the chosen area FROM A DISTANCE. Reflect spatial, material and
> atmospheric qualities. 2.5D visual collages of a feeling. Compose layers of colours, shapes,
> patterns on the A3 page to create 2.5-dimensional depth. Increase intensity of colour to
> communicate feelings in particular zones within the overlap of these spaces. Communicate
> smells / sounds / tastes / textures / colours.
> Client loves: the **draped ceiling / blinds** (festoon swags, sheer linen) and **glass brick walls**.
> Chosen areas: **the double-height void with the tree** and **the private cabins (booths)**.

## The design (from the client's drawings, `assets/client_RESTAURANT_drawings.pdf`)
Long rectangular two-storey restaurant. Ground floor: kitchen strip along the top, **four private
cabins** in a row (round sofa seating inside a curved shell; elevation 02 shows four arched cabins
under festoon ceiling draping with a pendant in each), dining area, party hall with curtains,
**bar** (brick/"decorative brick" back wall with 4 dome pendants and a fluted counter front),
**circular open void (double height) with a single slender tree** in the middle, stairs, glazed
entrance facade at the right-hand end. First floor: void ringed by a **stainless steel rail**,
cabins with planters, first-floor bar. Ceilings everywhere: **festoon/swag "ceiling draping"**.
Sheets (rendered at 300 dpi in `assets/drawings/sheet-{1..4}.png`, 9933×7016 px each):
1 = floor plans (ground + first), 2 = sections A-A and B-B, 3 = interior elevations
(01 ground bar, 02 ground private cabins, 03 first floor bar, 04 party hall), 4 = exploded axo.

## The two collages
**01 — FROM THE VOID, LOOKING OUT** (brief part 1: within → outside). Standing at the foot of the
tree in the double-height void. The eye travels from the luminous green-gold core (tree, skylight
pouring down the round void, steel rail ring, linen swags on the upper floor) outward through the
glass-block facade to the cool blue-hour street beyond. Warm amber bar + espresso on one side.
Sound rises and echoes up the void; smell of coffee, leaves, damp soil, rain outside.

**02 — TOWARDS THE CABINS** (brief part 2: from a distance → chosen area). From the open dining
floor looking across at the row of four arched, fluted-oak cabins glowing with terracotta velvet
and pendant light, under the festoon-draped ceiling; foreground blurred tables, diners in shadow-
play behind sheer linen, a glass-block screen at the edge. Colour intensity deepens as you enter
the cabins (pale linen → amber → terracotta → oxblood). Sound dims and softens into the linen;
smell of beeswax candle, sourdough, rosemary; taste of red wine, olive oil, sea salt.

## Canvas & technical
* A3 landscape **4961 × 3508 px @ 300 ppi**, 8-bit RGB, sRGB. (A3 = 420 × 297 mm.)
* Layers are 8-bit RGBA (straight alpha). Use `src/psdkit.py` classes (`Document`, `Group`,
  `Pixel`, `Fill`, `Mask`). Read its docstring. Supported blend modes are listed in `BLEND`.
  Groups are always pass-through at 100 %. Clipping: put `clip=True` on layers directly above a
  pixel/fill base layer.
* Non-destructive means: textures are **clipped** into shape layers, cut-outs use **layer masks**
  (not erased pixels) wherever practical, colour washes are **Solid Color fill layers** with masks,
  shadows are separate layers, everything clearly named and grouped, colour-labelled.
* Python: `python3` has numpy, Pillow, scipy, opencv-python-headless (cv2), scikit-image, fonttools.
  Node 22 is available (`npm` works: registry.npmjs.org is reachable). General internet image hosts
  are blocked; storage.googleapis.com works (used for AI generations, already downloaded).
* Machine: 4 CPUs, 15 GB RAM. Keep peak memory sensible (float32, crop to bounding boxes).
* Viewing images: use the Read tool on downscaled JPEG previews (≤ 1600 px long side) written to
  `build/preview/` — never Read the 30 MB originals.

## Folder layout (repo: `restaurant-collages/`)
```
ART_DIRECTION.md          this file
src/psdkit.py             layer model + Photoshop-compatible compositor (do not change API)
src/write_psd.js          manifest -> PSD writer (do not change)
src/lib/                  asset-library modules (one per area, see below)
assets/gen/               AI-generated source photos (royalty-free, ours) — read only
assets/drawings/          client drawings @300 dpi — read only
assets/client_*           client-supplied files — read only
assets/cut/ assets/mat/ assets/lines/ assets/outside/ assets/fonts/   library outputs
build/                    scratch, previews, contact sheets (build/contact/<area>.jpg)
output/                   final deliverables
```
Every library module must: expose reusable functions, have a `build()` that (re)generates its
assets deterministically (fixed seeds), write an `index.json` in its asset folder describing every
file (path, pixel size, what it is, key coordinates / anchor points, suggested use), and write a
labelled contact sheet `build/contact/<area>.jpg` that you inspect visually before finishing.

## Source photo inventory (`assets/gen/`, all generated for this project = royalty-free)
| file | size | content |
|---|---|---|
| glassblock_wall_A.png | 4736×3552 | straight-on wall of wavy clear glass blocks (≈10 cols × 8 rows incl. half rows), warm amber light, plants + 2 pendants refracted behind, grey mortar, terrazzo sill at bottom |
| festoon_valance.png | 6256×2688 | straight-on ivory linen festoon swag valance (≈9 swags) along the top on a warm plaster wall, side tails, two black dome pendants on cords, timber skirting near bottom |
| ceiling_lookup_A.png | 5456×3072 | looking up at a ceiling fully covered in glowing festoon swags, many black dome pendants — honey/gold |
| ceiling_lookup_B.png | 5456×3072 | same idea, more perspective, sheer curtains + windows on the right, pendants |
| cabins_row.png | 6256×2688 | ★ four arched fluted-oak cabin shells with terracotta velvet round banquettes, round tables, pendants, festoon ceiling band across the top, blurred dining tables in the foreground — matches elevation 02 |
| cabin_interior.png | 4736×3552 | ★ inside one cabin: curved velvet banquette, round marble table with 2 red wine glasses + candle + plates, fluted oak walls, glossy black pendant, gathered linen ceiling |
| void_lookup_A.png | 3664×4576 | looking up in a double-height atrium: slender tree through a round opening to a skylight, stainless rails on 2 levels, tied-back sheer curtains, planter with plants, pendants |
| void_lookup_B.png | 3664×4576 | ★ looking straight up the round void: tree trunk rising to a circular glazed skylight, stainless rail ring, swagged curtains around the upper floor, amber pendants |
| diners_silhouettes.png | 2736×1536 | dark grey silhouettes on near-white: couple at bistro table with wine (left), waiter with tray, standing couple with wine glasses laughing, woman seated alone with coffee (right); chairs/tables included |
Client files: `assets/client_drape_reference.png` (380×470, sheer drapes + swagged ceiling, the
client's mood reference — low-res, use soft/overlay only), `assets/client_RESTAURANT_drawings.pdf`.
Also allowed: scikit-image's bundled CC0 sample `skimage.data.coffee()` (400×600 espresso cup).

## Palette (use these; hex)
| role | hex | | role | hex |
|---|---|---|---|---|
| ink (lines/text) | #2B2420 | | linen | #EFE6D6 |
| oat | #DCCDB4 | | sand / plaster | #C9B391 |
| honey | #E8B062 | | amber | #D98A3D |
| ember | #C2602E | | terracotta | #A9502F |
| oxblood | #6B2430 | | wine | #4A1A26 |
| oak | #B07A45 | | sage | #8E9A72 |
| leaf | #4F6B3A | | canopy | #7FA35A |
| glass | #C8DAD3 | | celadon | #A9C4BC |
| dusk | #3D4A6B | | indigo | #262C45 |
| violet | #5A4E7A | | steel | #B8BCBD |
Paper ground: warm linen paper (#EEE5D3 with subtle fibre grain).

## Typography
* Display / poetic sensory phrases: **Cormorant Garamond** (Italic 400/500, Regular) — OFL.
* Labels / technical captions / numbers: **IBM Plex Mono** (Light 300 / Regular 400), tracked +60–120,
  uppercase for labels — OFL.
* Fonts are installed to `assets/fonts/` as .ttf (from npm `@fontsource/*` packages, converted with
  fontTools) together with their OFL licence texts.
* Text is rendered to raster layers named `TXT · <the text>` (Photoshop text-engine data is not
  generated, so rasterised text guarantees an identical look on any machine).

## Look & feel
Refined, quiet, tactile — an architecture-school atmosphere collage, not a stock mood board.
Photographic fragments cut with clean geometric or torn-paper edges, stacked as planes with soft
drop shadows (paper-cut 2.5D depth); translucent colour planes (multiply / soft light / screen)
that intensify colour in the "feeling zones"; the client's own linework (sections, elevation,
plan) ghosted in ink on top, aligned to the photographic content; sensory annotations in small
italic serif + mono labels with hairline leaders; sound as concentric rings / waveforms; smell as
soft rising wisps; light as beams and glows. Generous negative space of linen paper. No clip-art,
no emoji, no drop-shadowed text, no neon.
