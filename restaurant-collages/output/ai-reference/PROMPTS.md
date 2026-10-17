# AI image prompts with layout references

Each collage has four reference images in this folder:

| file | use it for |
|---|---|
| `…_ai-sketch.png` | Line art. ControlNet *lineart* / *canny* in Stable Diffusion, or as the image prompt in other tools. Locks the composition. |
| `…_ai-colour.png` | Flat colour block-in. Image-to-image, style or colour reference. Locks the colour zones and light. |
| `…_ai-labelled.png` | Colour block-in with labels. Upload it to ChatGPT / Gemini, which read the labels. |
| `…_ai-photo.jpg` | The rendered scene without text or legend. The strongest reference if you want to stay close to the current look. |

AI tools garble lettering, so add titles and captions afterwards in Photoshop.

---

## Collage 1 — From the void, looking out

**ChatGPT / Gemini** (upload `collage-01-from-the-void_ai-labelled.png`, then paste):

```
Use the attached image as the exact layout. Keep every element where it is: the round double-height void in the centre with the tree, the bar on the left, the glass-block wall and glazed door on the right, the festoon valance across the top, the tree pit at the bottom. Ignore the white label boxes. They only name each element; do not draw them.

Create a refined architectural atmosphere collage of a restaurant interior at blue hour, A3 landscape. We stand beneath a slender tree with feathery lime-green leaves rising through a circular double-height void, looking up through a round glass skylight to a deep dusk-blue sky, with a stainless steel balustrade and sheer white linen curtains around the void. Across the top, an ivory linen festoon valance with soft scalloped swags. Right: a glass-block wall with a rainy blue-hour street glowing through it and a glazed steel entrance door with raindrops and warm street lamps. Left: a warm amber bar with fluted oak, a glass-brick back wall, brass dome pendants, a steel counter and bar stools. A low terrazzo kerb around the tree, cream terrazzo floor. Layered 2.5D paper-cut collage on warm linen paper with soft drop shadows. Colour intensifies where spaces overlap: violet where the void meets the street, honey-amber where it meets the bar, glowing green-gold at the core. Poetic, editorial, high detail, no text.
```

**Midjourney** (upload `collage-01-from-the-void_ai-photo.jpg` or `_ai-sketch.png`, paste its link first):

```
<image link> architectural atmosphere collage, restaurant interior at blue hour, slender tree rising through a circular double-height void, round glass skylight with deep dusk-blue sky, steel balustrade and sheer linen curtains, ivory linen festoon valance with scalloped swags above, glass-block wall and glazed door with rainy street at dusk on the right, warm amber bar with fluted oak, glass bricks, dome pendants and stools on the left, terrazzo floor, layered 2.5D paper-cut collage on warm linen paper, soft shadows, violet and honey-amber colour where spaces overlap, green-gold glow at the core, poetic editorial, no text --ar 99:70 --iw 2 --style raw
```

**Stable Diffusion + ControlNet:** use `_ai-sketch.png` with lineart or canny at weight 0.8–1.0 and the Midjourney text above as the prompt.

---

## Collage 2 — Towards the cabins, from a distance

**ChatGPT / Gemini** (upload `collage-02-towards-the-cabins_ai-labelled.png`, then paste):

```
Use the attached image as the exact layout. Keep every element where it is: the draped linen ceiling across the top, the festoon swag valance below it, the row of four cabins across the middle with a pendant in each, the glass-brick screen on the left edge, the dining couple in the left foreground, the waiter, the circular zoom view on the right, the terrazzo floor. Ignore the white label boxes. They only name each element; do not draw them.

Create a refined architectural atmosphere collage of a restaurant, A3 landscape, looking across the dining room towards four private dining cabins: curved fluted-oak partitions 2.4 m high, open above, each with a terracotta velvet banquette, a round table and a black dome pendant hanging from the ceiling. A lofty ceiling of draped ivory linen in soft swags, with a continuous scalloped festoon valance across the room. Foreground: a couple dining at a bistro table as a soft dark silhouette behind a sheer linen veil, a waiter carrying a tray towards the cabins, a glass-brick screen at the left edge. A cream terrazzo floor recedes in perspective. The colour deepens from cabin to cabin: pale linen, amber, terracotta, then deep oxblood in the last cabin. A circular zoom on the right shows the intimate interior of cabin 04: a candlelit marble table, red wine, fluted oak and a warm pendant glow. Layered 2.5D paper-cut collage on warm linen paper with soft drop shadows. Warm, intimate, editorial, high detail, no text.
```

**Midjourney** (upload `collage-02-towards-the-cabins_ai-photo.jpg` or `_ai-sketch.png`):

```
<image link> architectural atmosphere collage, restaurant dining room looking towards four private dining cabins, curved fluted-oak partitions open above, terracotta velvet banquettes, round tables, black dome pendants, lofty draped ivory linen ceiling with a scalloped festoon valance, couple dining in soft silhouette behind sheer linen, waiter with tray, glass-brick screen on the left, cream terrazzo floor in perspective, colour deepening from linen to amber to terracotta to oxblood, circular zoom view into a candlelit cabin, layered 2.5D paper-cut collage on warm linen paper, soft shadows, warm intimate editorial, no text --ar 99:70 --iw 2 --style raw
```

---

## Changing the vibe

Keep the layout reference and swap the style words in the prompts:

- **Immersive photo-collage:** replace "layered 2.5D paper-cut collage on warm linen paper" with "photorealistic immersive eye-level collage, full bleed, cinematic lighting, people cut-outs".
- **Artistic / graphic:** "flat graphic collage, cut-paper shapes, muted risograph colours, minimal, abstract".
- **Light and airy:** "soft pastel daylight, airy, dreamy, washed colours".
- **Dark and moody:** "low-key lighting, deep shadows, candlelight, cinematic".

**Negative prompt** (if supported): `text, letters, labels, watermark, logo, cartoon, plastic 3D render, oversaturated, deformed people, blurry`
