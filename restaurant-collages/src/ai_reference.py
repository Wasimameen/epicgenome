"""ai_reference — layout guides of the two collages for AI image generators.

For each sheet the scene is rendered WITHOUT the presentation furniture (title, tags, legend, key
plan, sensory graphics, sightlines, ghosted drawings), then turned into three guides:

  <slug>_ai-sketch.png       clean line art (black on white) - for ControlNet lineart / canny or as an
                             image prompt: fixes the composition
  <slug>_ai-colour.png       flat colour block-in - fixes the colour zones and light
  <slug>_ai-labelled.png     the colour block-in with plain labels - for chat-based generators that
                             read text in images (ChatGPT / Gemini)

Run from src/:  python3 ai_reference.py      -> ROOT/output/ai-reference/
"""
from __future__ import annotations

import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import compose as C  # noqa: E402

OUT = C.P('output', 'ai-reference')
WIDE = 1600                       # guides are 1600 x 1131 (A3 proportion), what AI tools ingest best

HIDE = {
    '01': ('85', '90', '94', '98', '95', '!!'),
    '02': ('70', '98', '95', '!!'),
}

LABELS = {   # canvas px (4961 x 3508) -> label
    '01': [
        ((2480, 230), 'draped ivory linen festoon valance (ceiling)'),
        ((2280, 830), 'round skylight, deep blue-hour sky'),
        ((2280, 1500), 'slender tree rising through a round double-height void'),
        ((2280, 2420), 'steel balustrade + sheer white curtains around the void'),
        ((3500, 1650), 'glass-block wall, rainy street glowing through'),
        ((4250, 1950), 'glazed entrance door, wet street at dusk'),
        ((640, 1900), 'warm bar: fluted oak, glass bricks, dome pendants'),
        ((640, 2700), 'steel counter + bar stools'),
        ((2280, 3150), 'tree pit with low terrazzo kerb'),
        ((2280, 3420), 'cream terrazzo floor'),
    ],
    '02': [
        ((2600, 480), 'lofty draped ivory linen ceiling'),
        ((2600, 1230), 'continuous festoon swag valance'),
        ((2200, 1640), 'black dome pendant hanging into each cabin'),
        ((2300, 2050), 'four curved fluted-oak cabins, 2.4 m, open above, velvet banquettes'),
        ((320, 1400), 'glass-brick screen'),
        ((1150, 2550), 'couple dining, soft silhouette behind sheer linen'),
        ((2580, 2250), 'waiter with tray'),
        ((4316, 2045), 'zoom: inside cabin 04'),
        ((2500, 2830), 'cream terrazzo floor receding in perspective'),
    ],
}


def scene(sheet):
    mod = __import__(f'collage{sheet}')
    B = mod.build()
    for n in B.doc.root.children:
        if n.name.startswith(HIDE[sheet]):
            n.hidden = True
    comp = B.doc.render()
    rgb = np.clip(comp[..., :3], 0, 1)
    return cv2.resize(rgb, (WIDE, int(round(WIDE * C.H / C.W))), interpolation=cv2.INTER_AREA)


def line_art(rgb):
    """XDoG pencil line art: clean black lines on white, texture noise suppressed."""
    g8 = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    g8 = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(10, 10)).apply(g8)    # edges in dark booths too
    L = g8.astype(np.float32) / 255
    L = cv2.bilateralFilter(L, 9, 0.10, 6)
    g1 = cv2.GaussianBlur(L, (0, 0), 1.1)
    g2 = cv2.GaussianBlur(L, (0, 0), 1.1 * 1.6)
    d = g1 - 0.985 * g2
    e = np.where(d >= -0.004, 1.0, 1.0 + np.tanh(120 * (d + 0.004)))
    e = np.clip(e, 0, 1)
    # drop isolated specks (photo grain) but keep strokes
    ink = (e < 0.6).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink, 8)
    keep = np.isin(lab, np.flatnonzero(st[:, cv2.CC_STAT_AREA] >= 14)) & (lab > 0)
    e = np.where(ink & ~keep, 1.0, e)
    return np.dstack([e, e, e])


def colour_blocks(rgb):
    u8 = (rgb * 255).astype(np.uint8)
    u8 = cv2.pyrMeanShiftFiltering(cv2.cvtColor(u8, cv2.COLOR_RGB2BGR), 14, 28)
    u8 = cv2.cvtColor(u8, cv2.COLOR_BGR2RGB)
    Z = u8.reshape(-1, 3).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, lab, cen = cv2.kmeans(Z, 18, None, crit, 2, cv2.KMEANS_PP_CENTERS)
    out = cen[lab.ravel()].reshape(u8.shape).astype(np.uint8)
    out = cv2.medianBlur(out, 5)
    return out.astype(np.float32) / 255


def labelled(blocks, sheet):
    im = Image.fromarray((blocks * 255).astype(np.uint8)).convert('RGB')
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(C.P('assets', 'fonts', 'IBMPlexMono-Medium.ttf'), 17)
    s = WIDE / C.W
    for (x, y), text in LABELS[sheet]:
        X, Y = x * s, y * s
        tw, th = d.textbbox((0, 0), text, font=font)[2:]
        bx0, by0 = X - tw / 2 - 8, Y - th / 2 - 5
        bx0 = min(max(bx0, 12), im.width - tw - 28)          # keep every label inside the page
        d.rectangle([bx0, by0, bx0 + tw + 16, by0 + th + 12], fill=(255, 255, 255), outline=(30, 30, 30))
        d.text((bx0 + 8, by0 + 4), text, fill=(20, 20, 20), font=font)
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    slugs = {'01': 'collage-01-from-the-void', '02': 'collage-02-towards-the-cabins'}
    for sheet in ('01', '02'):
        rgb = scene(sheet)
        slug = slugs[sheet]
        Image.fromarray((line_art(rgb) * 255).astype(np.uint8)).save(os.path.join(OUT, f'{slug}_ai-sketch.png'))
        blocks = colour_blocks(rgb)
        Image.fromarray((blocks * 255).astype(np.uint8)).save(os.path.join(OUT, f'{slug}_ai-colour.png'))
        labelled(blocks, sheet).save(os.path.join(OUT, f'{slug}_ai-labelled.png'))
        Image.fromarray((rgb * 255).astype(np.uint8)).save(os.path.join(OUT, f'{slug}_ai-photo.jpg'), quality=90)
        print('done', sheet)


if __name__ == '__main__':
    main()
