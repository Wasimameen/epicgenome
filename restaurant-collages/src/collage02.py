"""Collage 02 — TOWARDS THE CABINS.

Brief part 2: looking towards the chosen area (the four private cabins) from a
distance — across the dining room, under the festoon ceiling, past diners in
shadow-play behind sheer linen and the glass-brick screen — and finally into
one cabin, where colour, sound and scent all intensify.

Run from src/:  python3 collage02.py            (preview render)
                python3 collage02.py --final    (PSD + JPEG + verification)
"""
from __future__ import annotations

import json
import sys
import time
import numpy as np

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from lib import compose as C
from lib import sensory as S
from lib.collage_common import (Builder, asset, have, INK, PAL, W, H, card_edge, local, colour_rgba, grade)

LINEN = PAL['linen']
SLUG = 'restaurant-collage-02-towards-the-cabins'

# --------------------------------------------------------------------------- #
# layout (canvas px, A3 landscape 4961 x 3508 @ 300 ppi)
# --------------------------------------------------------------------------- #
CR_S = 0.70                     # cabins_row.png -> canvas scale
CR_X, CR_Y = 300, 740           # canvas position of cabins_row.png (0, 0)
EL_K = (5329.42 - 1011.65) / (4896.5 - 758.0)   # photo px per elevation-02 px (cabin 1 -> 4 centres)
INSET = (3610, 1210, 4840, 2990)  # the cabin we walk into (arch-topped card)
SCREEN = (0, 560, 640, 3060)      # glass-brick screen, foreground left
FLOOR_Y = CR_Y + 2500 * CR_S      # floor line under the cabins


def cr(x, y):
    """cabins_row source px -> canvas px."""
    return CR_X + x * CR_S, CR_Y + y * CR_S


def blob_field(cx, cy, rx, ry, k=1.5):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    return np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) * k)


def build():
    B = Builder('Restaurant — Atmosphere collage 02 — Towards the cabins')
    geo = json.load(open(asset('cut', 'geo', 'cabins_row', 'geometry.json')))
    arches = geo['arches']

    # ================================================================ 00 paper
    g = B.group('00 · Paper', label='gray')
    B.px(g, 'Paper · warm linen ground', C.load('assets/mat/paper_linen_A3.png', 'RGB'), 0, 0)

    # ================================================================ 05 drawing underlay
    g = B.group('05 · Drawing underlay — elevation 02 (cabins)', label='violet')
    el = C.load('assets/lines/elev02_cabins.png')
    es = EL_K * CR_S
    els = C.resize(el, es)
    del el
    ex0, ey0 = cr(1011.65 - 758.0 * EL_K, 2500 - 2124.5 * EL_K)
    B.px(g, 'Drawing · elevation 02, registered to the photographed cabins', els, ex0, ey0,
         blend='multiply', opacity=0.7)
    del els

    # ================================================================ 10 ceiling
    g = B.group('10 · Ceiling — festoon drapery', label='yellow')
    band_h = 760
    band = C.cover(C.load('assets/gen/ceiling_lookup_B.png', 'RGB'), W, band_h, (0.42, 0.40))
    band = grade(band, lift=0.05, sat=0.7, gamma=1.05)
    fade = np.clip((band_h - np.arange(band_h, dtype=np.float32)) / 260.0, 0, 1)[:, None] * np.ones((1, W), np.float32)
    B.photo(g, 'Ceiling · swags overhead (photo, soft lower edge)', band, 0, 0,
            mask_alpha=fade, mask_xy=(0, 0))
    del band

    # ================================================================ 20 cabins (the chosen area, seen from afar)
    g = B.group('20 · The cabins — seen across the room', label='orange', opened=True)
    row = C.resize(C.load('assets/gen/cabins_row.png', 'RGB'), CR_S)
    shells = C.load('assets/cut/geo/cabins_row/shells_all.png', 'L')
    archm = C.load('assets/cut/geo/cabins_row/arches_all.png', 'L')
    cut = C.resize(np.clip(shells + archm, 0, 1), CR_S)
    del shells
    B.shadow(g, 'Shadow · cabins on the page', cut, CR_X, CR_Y, dx=26, dy=30, sigma=34, opacity=0.45)
    B.photo(g, 'Cabins · four fluted-oak cabins (photo, cut to the shells)', row, CR_X, CR_Y,
            mask_alpha=cut, mask_xy=(CR_X, CR_Y), margin=160)
    # colour intensity inside each arch, deepening towards the cabin we walk into
    am = C.resize(archm, CR_S)
    del archm
    for i, a in enumerate(arches):
        x0, y0 = cr(a['left_x'] - 8, a['crown_y'] - 8)
        x1, y1 = cr(a['right_x'] + 8, a['bottom_y'])
        sub = np.zeros((H, W), np.float32)
        lx0, ly0 = int(x0 - CR_X), int(y0 - CR_Y)
        lx1, ly1 = int(x1 - CR_X), int(y1 - CR_Y)
        sub[int(y0):int(y0) + (ly1 - ly0), int(x0):int(x0) + (lx1 - lx0)] = am[ly0:ly1, lx0:lx1]
        B.fill(g, f'Intensity · inside cabin {i + 1}', PAL['oxblood'], sub, blend='soft light',
               opacity=0.30 + 0.16 * i)
    del row, cut, am

    # ================================================================ 25 festoon hem
    g = B.group('25 · Festoon swag hem (nearer plane)', label='yellow')
    fv = C.load('assets/gen/festoon_valance.png', 'RGB')
    fm = C.load('assets/cut/geo/festoon_valance/valance_fabric.png', 'L')
    vx0, vx1, vy0, vy1 = 430, 5990, 250, 1160
    fs = 0.52
    fv = grade(C.resize(C.crop(fv, vx0, vy0, vx1, vy1), fs), lift=0.03, sat=0.85)
    fm = C.resize(C.crop(fm, vx0, vy0, vx1, vy1), fs)
    # the second copy starts on the first copy's last gather, so the join hides inside a gathered column
    g_first, g_last = (993.5 - vx0) * fs, (5404.5 - vx0) * fs
    hx1, hy = -90, 470
    hx2 = hx1 + g_last - g_first
    xs_ = np.arange(fm.shape[1], dtype=np.float32)
    keep1 = np.clip((g_last + 8 - xs_) / 16, 0, 1)[None, :]
    keep2 = np.clip((xs_ - (g_first - 8)) / 16, 0, 1)[None, :]
    for k, (hx, keep) in enumerate(((hx1, keep1), (hx2, keep2))):
        m_ = fm * keep
        B.shadow(g, f'Shadow · swag hem {k + 1}', m_, hx, hy, dx=0, dy=36, sigma=30, opacity=0.40)
        B.photo(g, f'Festoon · ivory linen swags {k + 1} (photo, fabric mask)', fv, hx, hy,
                mask_alpha=m_, mask_xy=(hx, hy))
    del fv, fm

    # ================================================================ 30 the cabin we walk into
    g = B.group('30 · Into the cabin — the chosen area up close', label='red', opened=True)
    ix0, iy0, ix1, iy1 = INSET
    iw, ih = ix1 - ix0, iy1 - iy0
    ci = C.cover(C.load('assets/gen/cabin_interior.png', 'RGB'), iw, ih, (0.52, 0.62))
    arch = C.arch_mask(0, iw, iw / 2, ih, h=ih, w=iw)
    B.shadow(g, 'Shadow · cabin card', arch, ix0, iy0, dx=36, dy=48, sigma=52, opacity=0.55)
    B.px(g, 'Cabin card · paper rim', card_edge(arch, width=14), ix0 - 14, iy0 - 14)
    B.photo(g, 'Cabin · inside the private cabin (photo, arch mask)', ci, ix0, iy0, mask_alpha=arch,
            mask_xy=(ix0, iy0))
    del ci
    inside = np.zeros((H, W), np.float32)
    inside[iy0:iy1, ix0:ix1] = arch
    B.fill(g, 'Intensity · deepest warmth inside the cabin', PAL['oxblood'], inside * blob_field(
        (ix0 + ix1) / 2, iy0 + ih * 0.72, iw * 0.7, ih * 0.5, 1.2), blend='soft light', opacity=0.65)
    # candle + pendant glow inside the cabin (cabin_interior: candle ~ (2400, 2350), shade ~ (2420, 1430))
    sc = max(iw / 4736, ih / 3552)
    offx = (4736 * sc - iw) * 0.52
    offy = (3552 * sc - ih) * 0.62

    def ci2c(x, y):
        return ix0 + x * sc - offx, iy0 + y * sc - offy

    candle = ci2c(2560, 2240)
    shade = ci2c(2460, 1480)
    B.gen(g, 'Light · candle glow', S.glow(at=candle, radius=360, color=PAL['honey'], intensity=0.85,
                                           core=0.1, hot_color='#FFF2D6'), blend='screen', opacity=0.9)
    B.gen(g, 'Light · pendant pool over the table', S.light_beam(apex=shade, angle=90, length=700, spread=26,
                                                                  aperture=300, color=PAL['amber'], intensity=0.35,
                                                                  dust=60, seed=7), blend='screen', opacity=0.8)
    del inside

    # ================================================================ 40 foreground: screen, sheer, diners
    g = B.group('40 · Foreground — glass-brick screen, sheer linen, diners', label='blue', opened=True)
    # diners in shadow-play behind a sheer linen veil
    cpl = C.resize(C.load('assets/cut/fig_couple_table_flat.png'), 1.16)
    wtr = C.resize(C.load('assets/cut/fig_waiter_flat.png'), 1.14)
    cpx, cpy = 600, FLOOR_Y + 420 - cpl.shape[0]
    wx, wy = 2010, FLOOR_Y + 380 - wtr.shape[0]
    for im_ in (cpl, wtr):
        im_[..., 3] = C.blur(im_[..., 3], 2.2)
    B.px(g, 'Diners · couple at a table (silhouette, shadow-play)', cpl, cpx, cpy, blend='multiply', opacity=0.82)
    B.px(g, 'Diners · waiter walking towards the cabins (silhouette)', wtr, wx, wy, blend='multiply', opacity=0.78)
    veil = C.load('assets/mat/client_drape_sheer.png')
    vw, vh = 2250, 1980
    veil = C.cover(veil, vw, vh, (0.5, 0.75))
    vx, vy = 380, 1330
    xs_ = np.arange(vw, dtype=np.float32)
    ys_ = np.arange(vh, dtype=np.float32)
    vm = np.clip(np.minimum(np.minimum(ys_ / 260, (vh - ys_) / 360)[:, None],
                            np.minimum(xs_ / 220, (vw - xs_) / 420)[None, :]), 0, 1)
    B.photo(g, 'Sheer · client drape as a linen veil (client photo)', veil, vx, vy, mask_alpha=vm, mask_xy=(vx, vy),
            opacity=0.62)
    # the bar's glass-brick screen in the near foreground
    sx0, sy0, sx1, sy1 = SCREEN
    sw, sh = sx1 - sx0, sy1 - sy0
    gba = C.load('assets/gen/glassblock_wall_A.png', 'RGB')
    gba = np.concatenate([gba[0:3236], gba[17:2756]], 0)
    gba = C.cover(gba, sw, sh, (0.06, 0.5))
    B.shadow(g, 'Shadow · glass-brick screen', np.ones((sh, sw), np.float32), sx0, sy0, dx=34, dy=30, sigma=40,
             opacity=0.5)
    B.px(g, 'Screen · glass-brick wall at the bar (photo)', gba, sx0, sy0)
    del gba

    # ================================================================ 50 floor drawing
    g = B.group('50 · Floor — the cabins in plan, laid on the floor', label='violet')
    pl = C.load('assets/lines/plan_ground_cabins.png')
    k = (arches[3]['centre_x'] - arches[0]['centre_x']) * CR_S / (2485.3 - 399.3)   # plan px -> canvas px
    c1x = cr(arches[0]['centre_x'], 0)[0]
    tlx, trx = c1x - 399.3 * k, c1x - 399.3 * k + pl.shape[1] * k
    top_y, bot_y = FLOOR_Y + 30, H - 40
    mid = (tlx + trx) / 2
    flare = 1.32
    quad = [(tlx, top_y), (trx, top_y), (mid + (trx - mid) * flare, bot_y), (mid - (mid - tlx) * flare, bot_y)]
    warped, wx0, wy0 = C.warp_quad(pl, quad)
    del pl
    keep = np.clip(1 - C.rect_mask(110, 2950, 1460, 3490, feather=50)       # keep the title clear
                   - C.rect_mask(3200, 3000, W, H, feather=50), 0, 1)       # and the key plan + materials
    B.photo(g, 'Drawing · ground-floor plan of the four cabins (perspective, client drawing)', warped, wx0, wy0,
            mask_alpha=keep, blend='multiply', opacity=0.36)
    del warped
    B.fill(g, 'Floor · warm spill from the cabins', PAL['amber'],
           blob_field(2450, FLOOR_Y + 60, 1900, 380, 1.0) * C.poly_mask(quad), blend='multiply', opacity=0.22)

    # ================================================================ 60 foreground table (taste)
    g = B.group('60 · Taste — the table we are walking to', label='red')
    tt = C.resize(C.load('assets/cut/cabin_table_top.png'), 0.74)
    tx, ty = 1520, H - tt.shape[0] - 120
    B.shadow(g, 'Shadow · table top', tt[..., 3], tx, ty, dx=24, dy=34, sigma=30, opacity=0.5)
    B.px(g, 'Table · marble top, red wine, candle (photo cut-out)', tt, tx, ty)

    # ================================================================ 70 light & colour intensity
    g = B.group('70 · Light & colour intensity', label='yellow', opened=True)
    for i, a in enumerate(arches):
        px_, py_ = cr(a['centre_x'], a['spring_y'] + 300)
        B.gen(g, f'Light · pendant glow, cabin {i + 1}',
              S.glow(at=(px_, py_), radius=420, color=PAL['amber'], intensity=0.6 + 0.08 * i, ratio=0.85),
              blend='screen', opacity=0.75)
    B.fill(g, 'Intensity · pale linen where we stand', LINEN, blob_field(900, 2600, 1300, 1100, 1.2),
           blend='soft light', opacity=0.5)
    B.fill(g, 'Intensity · amber across the cabins', PAL['amber'], blob_field(2700, 1800, 1900, 900, 1.2),
           blend='soft light', opacity=0.45)
    B.fill(g, 'Intensity · terracotta → oxblood towards the cabin', PAL['terracotta'],
           blob_field(4200, 2050, 1000, 1100, 1.3), blend='soft light', opacity=0.5)

    # ================================================================ 80 senses
    g = B.group('80 · Senses — sound · smell · taste · touch', label='red', opened=True)
    a2 = arches[1]
    thr2 = cr(a2['centre_x'] - 120, 1900)
    B.gen(g, 'Sound · conversation dims as it enters cabin 2',
          S.waveform([(1300, 2060), (1650, 1980), (2000, 1930), (thr2[0], thr2[1])], amplitude=56, wavelength=30,
                     width=3.0, color=LINEN, decay_start=0.35, decay_end=0.98, seed=11), opacity=0.95)
    a3 = arches[2]
    thr3 = cr(a3['centre_x'], 1980)
    B.gen(g, 'Sound · cutlery and low laughter fading towards cabin 3',
          S.waveform([(2300, 2300), (2650, 2240), (thr3[0], thr3[1])], amplitude=40, wavelength=22, width=2.2,
                     color=LINEN, decay_start=0.2, decay_end=0.95, style='bars', seed=13), opacity=0.9)
    ccx, ccy = candle
    B.gen(g, 'Sound · a hush inside the cabin (muffled rings)',
          S.sound_rings(at=(ccx, ccy - 40), r_max=560, n=5, ratio=0.42, width=3.0, color=LINEN, alpha=0.75,
                        decay=0.7, dash=(26.0, 18.0), seed=3), opacity=0.85)
    B.gen(g, 'Smell · rosemary and warm sourdough',
          S.wisp(at=(ccx - 30, ccy - 70), height=760, ribbons=2, width=46, color=PAL['honey'], color_top=LINEN,
                 opacity=0.9, lean=-0.55, seed=41), blend='screen')
    # table-top candle in the foreground: tt candle at ~ (870, 330) in the cut-out (scaled)
    B.gen(g, 'Smell · beeswax candle on our table',
          S.wisp(at=(tx + 0.46 * tt.shape[1], ty + 0.36 * tt.shape[0]), height=900, ribbons=3, width=70,
                 color=PAL['amber'], color_top=PAL['oat'], opacity=0.85, lean=0.2, seed=43))

    # ================================================================ 90 key plan + materials
    g = B.group('90 · Key plan & materials', label='violet')
    plan = C.load('assets/lines/plan_ground.png')
    px0, py0, px1, py1 = 300, 380, 4500, 2846
    ps = 0.15
    pc = C.resize(C.crop(plan, px0, py0, px1, py1), ps)
    del plan
    kx, ky = W - 170 - pc.shape[1], 3080
    B.px(g, 'Key plan · ground floor (client drawing)', pc, kx, ky, opacity=0.95)
    for cxp in (1163.3, 1865.3, 2566.4, 3249.3):
        ha, hx_, hy_ = local(C.ellipse_mask(kx + (cxp - px0) * ps, ky + (1124.1 - py0) * ps, 300 * ps, 300 * ps))
        B.px(g, f'Key plan · cabin highlight {int(cxp)}', colour_rgba(ha, PAL['terracotta']), hx_, hy_,
             opacity=0.45, blend='multiply')
    B.gen(g, 'Key plan · view cone (from the dining room to the cabins)',
          S.view_cone(apex=(kx + (2300 - px0) * ps, ky + (2240 - py0) * ps), direction=-95, fov=78,
                      length=(2240 - 1124) * ps + 40, color=PAL['terracotta'], fill=0.22), opacity=0.95)
    B.gen(g, 'Key plan · north point', S.north_arrow(at=(kx - 70, ky + 60), size=90))
    B.text(g, 'KEY PLAN — GROUND FLOOR', 'mono', 19, kx, ky - 22, tracking=120)
    mats = [('velvet_terracotta', 'VELVET'), ('oak_fluted', 'FLUTED OAK'), ('marble', 'MARBLE'),
            ('linen_plain', 'LINEN'), ('glassblock', 'GLASS BLOCK'), ('terrazzo_cream', 'TERRAZZO')]
    for i, (key, lab) in enumerate(mats):
        tex = C.cover(C.load(f'assets/mat/{key}.png'), 236, 140)
        mx, my = 3300 + (i % 3) * 205, 3110 + (i // 3) * 190
        B.gen(g, f'Material · {lab.lower()}', S.swatch_chip(fill=tex, at=(mx, my), size=(160, 96),
                                                             label=lab, sublabel='', label_size=18))

    # ================================================================ 98 type
    g = B.group('98 · Type — title & annotations', label='gray', opened=True)
    tx0 = 168
    B.text(g, 'RESTAURANT  ·  ATMOSPHERE STUDY  ·  02 / 02', 'mono', 28, tx0, 3060, tracking=140,
           color=PAL['terracotta'])
    B.text(g, 'Towards the cabins', 'italic', 150, tx0 - 6, 3236)
    B.text(g, 'GROUND FLOOR  ·  FROM THE DINING ROOM', 'mono-light', 21, tx0, 3330, tracking=100)

    B.tag(g, 'SOUND · 01', 'conversation dims\nas it enters the cabins', 1460, 1140, phrase_size=48, label_size=23)
    B.leader(g, 'Leader · sound 01', [(1700, 1320), (1800, 1560), thr2], dot_at_end=True, color=LINEN, width=2.6)
    B.tag(g, 'SOUND · 02', 'linen swallows the echo', 3260, 130, phrase_size=46, label_size=22)
    B.tag(g, 'SOUND · 03', 'cutlery, low laughter,\na chair drawn back', 150, 2560, phrase_size=44, label_size=21)
    B.card(g, 'At our table', [('SMELL', 'beeswax candle · warm sourdough · rosemary'),
                               ('TASTE', 'red wine, olive oil, sea salt')], 2920, 2540, phrase_size=42,
           label_size=21, gap=26)
    B.tag(g, 'LIGHT', 'a low pendant over every table', 2560, 900, phrase_size=44, label_size=22)
    box = B.tag(g, 'COLOUR', 'intensity deepens inward —\nlinen → amber → terracotta → oxblood', 3560, 880,
                phrase_size=42, label_size=21, pad=(34, 26))
    bw_, bh_ = box[2] - box[0], 26
    stops = [PAL['linen'], PAL['amber'], PAL['terracotta'], PAL['oxblood']]
    cols = np.array([[int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)] for c in stops], np.float32)
    t = np.linspace(0, len(stops) - 1, bw_)
    i0 = np.clip(np.floor(t).astype(int), 0, len(stops) - 2)
    f = (t - i0)[:, None]
    grad = np.ones((bh_, bw_, 4), np.float32)
    grad[..., :3] = (cols[i0] * (1 - f) + cols[i0 + 1] * f)[None, :, :]
    B.px(g, 'Colour · intensity scale (linen → amber → terracotta → oxblood)', grad, box[0], box[3])
    B.text(g, 'TEXTURE', 'mono', 19, 3300, 3082, tracking=120)
    return B


def main():
    t = time.time()
    B = build()
    print('built', B.doc.layer_count(), 'layers in', round(time.time() - t, 1), 's')
    if '--final' in sys.argv:
        from finalize import finalize
        rep = finalize(B.doc, SLUG)
        print(json.dumps(rep, indent=1))
    else:
        comp = B.doc.render()
        C.save_preview(comp, C.P('build', 'preview', 'main', 'c02_full_preview.jpg'), max_side=2000)
    print('done', round(time.time() - t, 1), 's')


if __name__ == '__main__':
    main()
