"""process_sheet — lay the clay axonometric (build/v2/render/process_axo.png) on cream paper with a
caption: output/v2/process-3d-model-of-the-design.jpg (A4 landscape, 300 ppi).

    python3 src/v2/process_sheet.py
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SRC = os.path.join(ROOT, 'build', 'v2', 'render', 'process_axo.png')
OUT = os.path.join(ROOT, 'output', 'v2', 'process-3d-model-of-the-design.jpg')
FONTS = os.path.join(ROOT, 'assets', 'fonts')
W, H = 3508, 2480                       # A4 landscape @ 300 ppi
CREAM = (236, 230, 218)
INK = (42, 36, 32)
SOFT = (107, 98, 90)


def tracked(d, xy, text, font, fill, tracking):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + tracking


def main():
    axo = Image.open(SRC).convert('RGBA')
    page = Image.new('RGB', (W, H), CREAM)
    s = min((W - 400) / axo.width, (H - 620) / axo.height)
    axo = axo.resize((int(axo.width * s), int(axo.height * s)), Image.LANCZOS)
    # soft contact shadow under the model
    a = np.asarray(axo)[..., 3].astype(np.float32) / 255
    sh = Image.fromarray((a * 60).astype(np.uint8)).filter(__import__('PIL.ImageFilter', fromlist=['x']).GaussianBlur(30))
    x0 = (W - axo.width) // 2
    y0 = 360 + (H - 620 - axo.height) // 2
    page.paste(Image.new('RGB', axo.size, (90, 70, 55)), (x0 + 18, y0 + 26), sh)
    page.paste(axo, (x0, y0), axo)
    d = ImageDraw.Draw(page)
    title = ImageFont.truetype(os.path.join(FONTS, 'CormorantGaramond-Regular.ttf'), 80)
    ital = ImageFont.truetype(os.path.join(FONTS, 'CormorantGaramond-Italic.ttf'), 46)
    hand = ImageFont.truetype(os.path.join(FONTS, 'hand', 'NothingYouCouldDo.ttf'), 58)
    tracked(d, (230, 170), 'THE 3D MODEL BEHIND BOTH COLLAGES', title, INK, 11)
    tracked(d, (234, 280), 'built from your plans, sections and elevations  ·  rendered in Blender  ·  no AI imagery',
            ital, SOFT, 6)
    d.text((W - 1350, H - 190), 'roof + first floor lifted off', font=hand, fill=SOFT)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    icc = open(os.path.join(ROOT, 'src', 'sRGB.icc'), 'rb').read()
    page.save(OUT, quality=93, dpi=(300, 300), icc_profile=icc, subsampling=0)
    print('process sheet ->', OUT)


if __name__ == '__main__':
    main()
