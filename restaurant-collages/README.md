# Restaurant — two A3 atmosphere collages

Two layered Photoshop atmosphere collages of the client's restaurant design (RESTAURANT.pdf, four A1 sheets).

## Version 2 (current): material collages, no AI imagery

After the client's feedback ("like this vibe but not AI … needs to have the materials on it like a collage of the space"), both sheets were rebuilt in the style of her reference: a perspective view of the space with torn and cut material fragments laid over and behind it, handwritten notes with arrows, and a serif title on cream paper.

| | Sheet (A3 portrait) | Brief |
|---|---|---|
| **1** | *Looking from within*: chosen area to outside views | Standing in the double-height void under the olive tree, looking out past the festoon drapes, glass blocks and split-face stone piers to the sunlit street. |
| **2** | *Looking towards*: chosen area from a distance | From the void, across the dining room under the layered swag ceiling, past the glass-block screen, to the four fluted-oak private cabins. |

**How the images were made.** No AI-generated images and no stock photographs are used.
- **The views** are 3D renders of the client's own design. The design was modelled from her plans, sections and elevations in Blender 5.2 (Cycles):
  - the circular void with the stainless rail and rooflight, and a procedurally grown olive tree;
  - the ceiling draping (catenary swags, festoon valances, a festoon ring);
  - glass-block walls, curved fluted-oak cabins with velvet sofas, marble tables and dome pendants;
  - split-face stone piers, a travertine floor and painted white brick.
- **The material fragments** are close-up renders of the same materials. Every material is procedural (shader nodes, or stone height and colour maps synthesised in numpy), made for this project.
- **Fonts:** Nothing You Could Do (handwriting) and Cormorant Garamond, both SIL OFL.

The notes name her design (ceiling draping, glass brick, the void and olive tree, the private cabins, fluted oak curve walls). Each sense is labelled (*sound*, *smell + taste*, *colour*); texture is carried by the material fragments.

Both sheets still answer the brief:
- **2.5D depth:** fragments in front of and behind the view, each with its own shadow.
- **The senses:** sound, smell, taste, texture and colour, in the handwritten notes.
- **Colour intensity where spaces overlap:** the "50 Overlap intensity" group of fills warms wherever a fragment overlaps the view.
  - Sheet 1: a terracotta glow on the table in the void, where it meets the street.
  - Sheet 2: the cabins, lifted forward as a cut piece and warmed.

### Deliverables (`output/v2/`)

| file | what |
|---|---|
| `restaurant-collage-01-looking-from-within.psd`, `restaurant-collage-02-looking-towards.psd` | **Layered masters.** A3 portrait, 3508 × 4961 px at 300 ppi, sRGB with embedded ICC. Not in git (over GitHub's 100 MB limit); delivered separately. |
| `….jpg` | Flattened, quality 95, 4:4:4, ICC, 300 ppi |
| `restaurant-collages-01-02-side-by-side_A3.jpg` | Both sheets side by side on one A3 landscape page, as in the client's reference |
| `…_preview.jpg`, `…_layers.txt` | 2000 px preview; full layer tree |
| `fonts-to-install.zip` | Nothing You Could Do and Cormorant Garamond, with licences |
| `process-3d-model-of-the-design.jpg` | A clay axonometric of the 3D model behind both views, roof lifted off, as evidence that they are renders of her design and not generated images |

### Editing the v2 PSDs
- **Groups, back to front:**
  - `00 Paper`
  - `10 Fragments behind`
  - `20 Main view`
  - `30 Echo patches`
  - `40 Fragments in front`
  - `50 Overlap intensity`
  - `60 Notes`
  - `90 Title and key line`
  - a hidden `!! READ ME`
- **Each fragment** is the full material image under a tear mask. Paint the mask to re-tear it. The shadow and the white paper-core rim are separate layers.
- **Grain and tone:**
  - `45 - Print grain` (soft light) makes the render and swatches read as prints on one stock.
  - `Tone - main view` (saturation) calms the render; hide it for the raw render.
- **Notes and titles** are live type. Show the hidden `EDIT - …` layer to retype, then hide the raster twin. Install the fonts first.

### Rebuilding v2
```bash
cd src/v2/scene
python3 textures.py                       # split-face stone maps -> build/v2/tex/
python3 render.py --view 1 --res 2700 3600 --samples 56 --out ../../../build/v2/render/view1.png
python3 render.py --view 2 --res 2700 3600 --samples 56 --out ../../../build/v2/render/view2.png
python3 swatches.py                       # 13 material swatches -> build/v2/swatch/
python3 process.py                        # clay axonometric of the model
cd ../../..
python3 src/v2/compose.py --sheet all --final && python3 src/v2/compose.py --combined
```
`pip install bpy==5.2.2` provides Blender as a Python module. Page layout data lives in `src/v2/layout.py`.

---

## Version 1 (superseded)

| | Sheet | Brief |
|---|---|---|
| **01** | *From the void, looking out* | Looking from within the chosen area (the double-height void with the tree) out to the views: the sky through the skylight, and the blue-hour street beyond the glazed glass-block entrance. |
| **02** | *Towards the cabins* | Looking towards the chosen area (the four private cabins) from a distance: across the dining room, under the festoon ceiling, past diners in shadow-play, then into cabin 04. |

Both sheets show **sound, smell, taste, texture and colour** in image and words, use **2.5D paper-cut layering** (one light direction, cast shadows, near / middle / far planes) and **raise colour intensity where spaces overlap**:
- 01: the void ∩ facade lens, the void ∩ bar lens and the green-gold core.
- 02: cabin 01 → 04 deepening linen → amber → terracotta → oxblood, and the oxblood zone where the approach meets cabin 04.

### Deliverables (`output/`)

| file | what |
|---|---|
| `restaurant-collage-0N-….psd` | **Layered master.** A3 landscape, 4961 × 3508 px at 300 ppi, 8-bit RGB, embedded sRGB IEC61966-2.1 profile, maximised compatibility (full composite + version info). About 130–200 MB each, so it is **not in git** (GitHub's limit is 100 MB per file) and is delivered separately. |
| `fonts-to-install.zip` | The free fonts the live type uses (Cormorant Garamond and IBM Plex Mono, all weights shipped) and their SIL OFL licences |
| `restaurant-collage-0N-….jpg` | Flattened file at trim size: quality 95, 4:4:4, sRGB ICC, 300 ppi |
| `restaurant-collage-0N-…_print-3mm-bleed.jpg` | The same with 3 mm mirrored bleed on every edge (5033 × 3580 px) for a print shop that trims |
| `restaurant-collage-0N-…_preview.jpg` | 2000 px web preview |
| `restaurant-collage-0N-…_layers.txt` | The full layer tree (top of the Layers panel first) and the build stamp |

### Editing the PSDs

- **Groups** are numbered from the back (`00 - Paper`) to the front (`98 - Type`).
  - Colour labels: grey = paper, violet = client drawings and key plan, blue = outside and far planes, orange = interior photo planes, green = the chosen area, yellow = light and colour intensity, red = senses.
  - A hidden top group, **`!! READ ME`**, repeats these notes inside the file.
- **Nothing is erased.** Every photo cut-out is the original photo with a **layer mask**. Paint the mask to refine an edge.
- **Shadows** are separate `Shadow - …` layers. Move them together with their object.
- **Colour washes, intensities, grades and silhouettes** are **Solid Color fill layers**. Double-click the thumbnail to recolour.
  - Layers marked *clipped* only act inside the layer beneath them.
  - Photo grades are clipped fills too (`Grade - …`). Hide one to see the ungraded photo.
- **Type is editable.**
  - Every `TXT - …` raster layer has a hidden live type layer `EDIT - …` above it, with the same font, size, tracking and position.
  - To change wording: show the EDIT layer (a tag has two: label and phrase), type, then hide the TXT layer. Photoshop may ask to update text layers; click *Update*.
  - Each tag or card is its own sub-group (`Tag - …` / `Card - …`) holding its paper, shadow, type and leader, so it moves as one.
  - Legend palette chips are Solid Color fills and their labels are live type too.
- **Fonts** (free, SIL Open Font License): install them from `fonts-to-install.zip` before editing type. The live type uses CormorantGaramond-Italic, IBMPlexMono-Regular, IBMPlexMono-Light and IBMPlexMono-Medium; the zip also carries the other weights.
- **Locked layers.** The paper, the client drawings and the key plan are locked (position and pixels) to prevent accidental edits. Unlock them in the Layers panel.

### Sources and licensing

- **Client material:** RESTAURANT.pdf (plans, sections, elevations; linework extracted from the vector PDF, annotations removed) and the client's drape photograph (used as the sheer-linen veil and a material swatch).
- **Photographs generated for this project** with FLUX (via ElevenLabs): cabins row, cabin interior, festoon valance, two draped-ceiling views, two void views, glass-block wall and diner silhouettes. No third-party photographs or stock imagery are used.
  - **Disclosure:** these are AI-generated images. If your school has a policy on AI-generated imagery, check it and acknowledge it where required, e.g. "photographic textures AI-generated, composed by the author".
- **Espresso cup:** scikit-image sample image *coffee* (CC0).
- **Made for this file:** street at dusk, glass refraction, materials, paper, sound / smell / light graphics, key plan styling.
- **Fonts:** Cormorant Garamond and IBM Plex Mono (SIL OFL 1.1). The licences are in `assets/fonts/`.
- **Colour profile:** sRGB IEC61966-2.1 v2 profile from the ocrmypdf project ("no copyright, use freely").

### Rebuilding

```bash
cd src
npm --prefix ../tools install      # ag-psd + pngjs (PSD writer)
python3 collage02.py               # preview -> build/preview/main/
python3 collage02.py --final       # PSD + JPEG + preview + layer tree + verification
python3 collage01.py --final
```

- `psdkit.py` is a small layered-document model with a Photoshop-equivalent compositor. Its blend modes match psd-tools' Photoshop-verified implementations.
- `write_psd.js` writes the PSD (ag-psd). It covers:
  - groups, masks, clipping, Solid Color fills, live type layers, locks, version info;
  - and `finalize.py` inserts the ICC profile afterwards.
- `collage02_prep.py` derives the cleaned cabins plate (foreground chairs removed, partitions cut flat at 2.4 m, pendant masks) and the seamless festoon frieze, cached in `build/c02/`.
- `finalize.py` verifies every export and writes `build/<slug>/report.json`:
  - it re-opens the PSD with psd-tools;
  - it checks the ICC profile, the type layers and the resolution;
  - it compares the embedded composite and an independent re-render against our render;
  - it stamps a sha1 of the sheet's build sources (and whether they were committed) into `_layers.txt`, and refuses to export if a source changes during the run.
- The AI source photos (`assets/gen/*.png`, about 30 MB each) are not in git. Keep them locally to rebuild.
