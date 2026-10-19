"""Collage 02 — TOWARDS THE CABINS.

Brief part 2: looking towards the chosen area (the four private cabins) from a distance —
across the dining room, under the lofty festoon ceiling, past diners in shadow-play behind
sheer linen and a glass-brick screen — and finally into cabin 04, where colour, sound and
scent all intensify.

The cabins follow elevation 02 / section B-B: 2.4 m fluted-oak partitions, straight openings,
OPEN ABOVE to the draped ceiling, a pendant dropping from the swags into each booth.

Run from src/:  python3 collage02.py            (preview render)
                python3 collage02.py --final    (PSD + JPEG + verification)
"""
from __future__ import annotations

import json
import math
import sys
import time

import cv2  # noqa: F401
import numpy as np

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from lib import compose as C
from lib import sensory as S
from lib import typeset as T
from lib.collage_common import (Builder, INK, PAL, W, H, MARGIN, LABEL, card_edge, local, colour_rgba,
                                aa_line, terrazzo_mosaic)
import collage02_prep as PREP

LINEN = PAL['linen']
SLUG = 'restaurant-collage-02-towards-the-cabins'
TITLE = 'Restaurant - Atmosphere collage 02 - Towards the cabins'

# --------------------------------------------------------------------------- #
# layout (canvas px, A3 landscape 4961 x 3508 @ 300 ppi)
# --------------------------------------------------------------------------- #
CR_S = 0.62                     # cabins_row.png -> canvas scale
CR_X, CR_Y = 330, 880           # canvas position of cabins_row.png (0, 0)
VAL_TOP = 1010                  # canvas y of the festoon heading (drapery 1.23 m deep, elevation 02)
VAL_S = 0.5                     # festoon_valance.png -> canvas scale
CEIL_H = 1100                   # ceiling photo band (overhead, looking up)
SCREEN = (0, 0, 640, 2860)      # glass-brick screen, nearest plane, bleeds off top / left
INSET_C = (4316, 2045)          # 'inside cabin 04' lens (rim on the 4793 right margin)
INSET_R = 470
CI_S = 0.315                    # cabin_interior.png -> canvas scale inside the lens
CI_FOCUS = (2450, 1820)         # cabin_interior.png point at the lens centre
DROP = 155                      # pendants hang ~0.18 m into the booths (elevation 02), not above them


def cr(x, y):
    """cabins_row source px -> canvas px."""
    return CR_X + x * CR_S, CR_Y + y * CR_S


def ci2c(x, y):
    """cabin_interior source px -> canvas px."""
    return INSET_C[0] + (x - CI_FOCUS[0]) * CI_S, INSET_C[1] + (y - CI_FOCUS[1]) * CI_S


YCUT_C = cr(0, PREP.YCUT)[1]     # partition tops on the canvas


def blob(cx, cy, rx, ry, k=1.5):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    return np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) * k)


def tangent_points(p, c, r):
    """Tangent points on circle (c, r) seen from point p -> (upper, lower) by y."""
    dx, dy = p[0] - c[0], p[1] - c[1]
    d = math.hypot(dx, dy)
    a = math.atan2(dy, dx)
    b = math.acos(r / d)
    t1 = (c[0] + r * math.cos(a + b), c[1] + r * math.sin(a + b))
    t2 = (c[0] + r * math.cos(a - b), c[1] + r * math.sin(a - b))
    return tuple(sorted((t1, t2), key=lambda t: t[1]))


def build():
    B = Builder(TITLE)
    rgb_cr, cut_cr, pen_cr, shades, geo = PREP.cabins_plate()
    arches = geo['arches']

    # ================================================================ 00 paper
    g = B.group('00 - Paper', label='gray')
    B.px(g, 'Paper - warm linen ground', C.load('assets/mat/paper_linen_A3.png', 'RGB'), 0, 0, locked=True)

    # ================================================================ 10 ceiling (overhead, looking up)
    g = B.group('10 - Ceiling - festoon drapery overhead', label='orange')
    src = C.load('assets/gen/ceiling_lookup_B.png', 'RGB')[170:1500]
    band = C.cover(src, W + 240, CEIL_H + 120, (0.5, 0.0))
    del src
    B.photo(g, 'Ceiling - linen swags overhead (photo)', band, -120, 0,
            mask_alpha=C.rect_mask(0, 0, W, CEIL_H), margin=None)
    del band
    B.fill(g, 'Grade - ceiling to linen (colour)', LINEN, C.rect_mask(0, 0, W, CEIL_H), blend='color',
           opacity=0.30, clip=True)
    B.fill(g, 'Grade - ceiling lift', LINEN, C.rect_mask(0, 0, W, CEIL_H), blend='screen', opacity=0.16, clip=True)
    haze = np.clip(0.35 + 0.65 * (np.arange(H, dtype=np.float32)[:, None] / CEIL_H) ** 1.6, 0, 1) * np.ones((1, W), np.float32)
    haze[CEIL_H:] = 0
    B.fill(g, 'Atmosphere - linen haze', '#F3ECDF', haze, opacity=0.42, clip=True)
    del haze

    # ================================================================ 15 festoon frieze above the cabins
    g = B.group('15 - Festoon swags above the cabins', label='orange')
    need = int(math.ceil((W + 200) / VAL_S))
    fr, fm, gathers = PREP.valance_frieze(10200)
    fr, fm = fr[:, :need], fm[:, :need]
    frs = C.resize(fr, VAL_S)
    fms = C.resize(fm, VAL_S)
    del fr, fm
    vx = -90
    heading = int(round((280 - PREP.V_Y0) * VAL_S))         # heading top row inside the frieze
    vy = VAL_TOP - heading
    hh = fms.shape[0]
    top_soft = np.clip((np.arange(hh, dtype=np.float32) - heading + 2) / 34.0, 0, 1)[:, None]
    fmask = fms * top_soft
    B.shadow(g, 'Shadow - swags on the ceiling and wall', fmask, vx, vy, depth=26, opacity=0.34)
    cords = np.zeros((H, W), np.float32)
    for s_ in shades:
        x_, y_ = cr(*s_['cap_top'])
        aa_line(cords, [(x_, VAL_TOP + 30), (x_, y_ + DROP + 4)], width=3.0)
    B.fill(g, 'Pendants - cords from the ceiling', '#231C18', cords)
    del cords
    B.photo(g, 'Festoon - ivory linen swags (photo, fabric mask)', frs, vx, vy, mask_alpha=fmask,
            mask_xy=(vx, vy))
    vb = (vx, vy, vx + frs.shape[1], vy + frs.shape[0])
    del frs
    full = np.zeros((H, W), np.float32)
    x0, y0 = max(0, vx), max(0, vy)
    full[y0:vb[3], x0:min(W, vb[2])] = fmask[y0 - vy:, x0 - vx:x0 - vx + min(W, vb[2]) - x0]
    B.fill(g, 'Grade - swags desaturate', '#8C8C8C', full, blend='saturation', opacity=0.42, clip=True)
    B.fill(g, 'Grade - swags to linen (colour)', LINEN, full, blend='color', opacity=0.25, clip=True)
    B.fill(g, 'Grade - swags lift', LINEN, full, blend='screen', opacity=0.14, clip=True)
    hem_y = vy + int(np.nonzero(fms.max(1) > 0.5)[0].max())
    del full, fms

    # ================================================================ 20 floor (behind the cabins)
    g = B.group('20 - Floor - terrazzo receding to the cabins', label='orange')
    base_y = cr(0, 2440)[1]                               # cabin bases (sides) on the canvas
    vp = (cr(5329, 0)[0], 1900)                          # vanishing point on cabin 04, at standing eye level
    far_y = base_y - 10
    near_y = 3020
    def on_ray(xn):                                       # floor line through (xn, near_y) towards vp
        t = (far_y - near_y) / (vp[1] - near_y)
        return xn + (vp[0] - xn) * t
    xl_n, xr_n = -4600, W + 4600
    quad = [(on_ray(xl_n), far_y), (on_ray(xr_n), far_y), (xr_n, near_y), (xl_n, near_y)]
    plate = terrazzo_mosaic(C.P('build', 'c02', 'terrazzo_floor_plate_v1.png'), Wm=7000, Hm=1600,
                            tile_scale=0.16, n=420, seed=31)          # ~2.5:1 near-edge foreshortening
    warped, wx0, wy0 = C.warp_quad(plate[..., :3], quad)
    del plate
    fy = np.arange(warped.shape[0], dtype=np.float32) + wy0
    fade = np.clip((2990 - fy) / 260.0, 0, 1) * np.clip((fy - far_y + 6) / 30.0, 0, 1)
    fa = warped[..., 3] * fade[:, None]
    B.photo(g, 'Floor - cream terrazzo (perspective)', warped[..., :3], wx0, wy0, mask_alpha=fa,
            mask_xy=(wx0, wy0), opacity=0.42)
    del warped
    B.fill(g, 'Grade - terrazzo desaturate', '#8C8C8C', C.poly_mask(quad), blend='saturation', opacity=0.45,
           clip=True)
    # joints converging on cabin 04
    jl = np.zeros((H, W), np.float32)
    for xn in np.arange(-4600, W + 4600, 900):
        p0 = (on_ray(xn), far_y)
        aa_line(jl, [p0, (xn, near_y)], width=1.6)
    for yv in (2540, 2680, 2860):
        aa_line(jl, [(0, yv), (W, yv)], width=1.6)
    yy = np.arange(H, dtype=np.float32)[:, None]
    jl *= np.clip((2990 - yy) / 260.0, 0, 1) * (yy > far_y)
    B.fill(g, 'Floor - joints towards cabin 04', '#9C8B76', jl, blend='multiply', opacity=0.5)
    del jl
    # the cabin plan, laid on the floor in perspective (client drawing, labels removed)
    pl = C.load('assets/lines/plan_ground_cabins_notext.png')
    pr = geo['arches']
    c1x, c4x = cr(pr[0]['centre_x'], 0)[0], cr(pr[3]['centre_x'], 0)[0]
    k = (c4x - c1x) / (2485.3 - 399.3)
    tlx = c1x - 399.3 * k
    trx = tlx + pl.shape[1] * k
    ptop, pbot = base_y + 40, 2960
    def ray_at(xt, y):
        t = (y - ptop) / (pbot - ptop)
        xb = vp[0] + (xt - vp[0]) * (pbot - vp[1]) / (ptop - vp[1])
        return xt + (xb - xt) * t
    pquad = [(tlx, ptop), (trx, ptop), (ray_at(trx, pbot), pbot), (ray_at(tlx, pbot), pbot)]
    pw, pwx, pwy = C.warp_quad(pl, pquad)
    del pl
    py_ = np.arange(pw.shape[0], dtype=np.float32) + pwy
    pa = pw[..., 3] * np.clip((2930 - py_) / 220.0, 0, 1)[:, None]
    B.fill_local(g, 'Drawing - cabin plan on the floor', INK, pa, pwx, pwy, blend='multiply',
                 opacity=0.24)
    del pw
    B.fill(g, 'Floor - warm spill from the cabins', PAL['amber'],
           blob(2300, base_y + 40, 2100, 300, 1.0) * C.poly_mask(quad), blend='multiply', opacity=0.20)

    # ================================================================ 30 the cabins (the chosen area, from afar)
    g = B.group('30 - The cabins - seen across the room', label='green', opened=True)
    rgb_s = C.resize(rgb_cr, CR_S)
    cut_s = C.resize(cut_cr, CR_S)
    del rgb_cr
    B.shadow(g, 'Shadow - cabins on the floor and wall', cut_s, CR_X, CR_Y, depth=30, opacity=0.42)
    cab = B.photo(g, 'Cabins - four oak cabins, open above (photo)', rgb_s, CR_X, CR_Y,
                  mask_alpha=cut_s, mask_xy=(CR_X, CR_Y), margin=120)
    # colour intensity rising cabin by cabin (clipped to the cabins photo)
    steps = [[(LINEN, 'screen', 0.20)],
             [(PAL['amber'], 'soft light', 0.45)],
             [(PAL['terracotta'], 'soft light', 0.70), ('#FF4A12', 'saturation', 0.22)],
             [(PAL['oxblood'], 'soft light', 0.90), (PAL['oxblood'], 'hue', 0.70)]]
    words = [['linen'], ['amber'], ['terracotta', 'vermilion'], ['oxblood', 'oxblood hue']]
    opening_m = []
    Hs, Ws = cut_cr.shape
    for i, (a, fills) in enumerate(zip(arches, steps)):
        # parametric (amodal) opening: the photo's 'visible opening' masks have holes where the
        # defocused foreground chairs were, which would leave chair-shaped ghosts in the washes
        am = C.arch_mask(a['left_x'] + 2, a['right_x'] - 2, a['spring_y'], a['bottom_y'] + 40, a['crown_y'],
                         h=Hs, w=Ws) * cut_cr
        am = C.resize(am, CR_S)
        full = np.zeros((H, W), np.float32)
        hh_, ww_ = am.shape
        full[CR_Y:CR_Y + hh_, CR_X:CR_X + ww_] = am[:H - CR_Y, :W - CR_X]
        full[:int(YCUT_C)] = 0
        full = C.blur(full, 6)
        opening_m.append(full)
        for j, (col, mode, op) in enumerate(fills):
            B.fill(g, f'Intensity - cabin {i + 1} {words[i][j]} ({mode})', col, full, blend=mode,
                   opacity=op, clip=True)
    del am
    yy_ = np.arange(H, dtype=np.float32)[:, None]
    lower = np.clip((yy_ - (YCUT_C + 330)) / 260.0, 0, 1)
    B.fill(g, 'Grade - lift booth shadows 03-04', LINEN, (opening_m[2] + opening_m[3]) * lower, blend='screen',
           opacity=0.16, clip=True)
    del opening_m, full, lower
    B.fill(g, 'Grade - cabins warm lift', PAL['honey'], C.rect_mask(0, int(YCUT_C), W, H), blend='soft light',
           opacity=0.18, clip=True)
    # the four dome pendants, dropped into the booths (separate layer: move them freely)
    pen_s = C.resize(pen_cr, CR_S)
    B.shadow(g, 'Shadow - pendants', pen_s, CR_X, CR_Y + DROP, depth=16, opacity=0.35)
    B.photo(g, 'Pendants - four dome shades (photo)', rgb_s, CR_X, CR_Y + DROP, mask_alpha=pen_s,
            mask_xy=(CR_X, CR_Y + DROP), margin=24)
    del rgb_s, pen_s

    # ================================================================ 40 foreground (diners, sheer, screen)
    g = B.group('40 - Foreground - diners, sheer, glass brick', label='orange', opened=True)
    # a waiter crossing towards cabin 03 (small: far away)
    wtr_l, (wx, wy, ww, wh) = B.cutout(g, 'Diners - waiter crossing to cabin 03', 'fig_waiter.png',
                                       0.56, 2330, base_y + 90 - 984 * 0.56,
                                       alpha_fn=lambda a: C.blur(a, 1.2), flat_color='#2E2622', opacity=0.82)
    # the couple at a table, near us
    cpl_s = 1.18
    cpx, cpy = 640, 2795 - 761 * cpl_s
    _, (cx_, cy_, cw_, ch_) = B.cutout(g, 'Diners - couple at a table', 'fig_couple_table.png', cpl_s,
                                       cpx, cpy, alpha_fn=lambda a: C.blur(a, 2.0), flat_color='#2E2622',
                                       opacity=1.0)
    # client's sheer drape as a linen veil: over the shells and the diners, not over the booths
    veil = C.load('assets/mat/client_drape_sheer.png')
    vw, vh = 2050, 1320
    veil = C.cover(veil, vw, vh, (0.5, 0.7))
    vx_, vy_ = 300, 1600
    xs_ = np.arange(vw, dtype=np.float32)
    ys_ = np.arange(vh, dtype=np.float32)
    vm = np.clip(np.minimum(np.minimum(ys_ / 300, (vh - ys_) / 280)[:, None],
                            np.minimum(xs_ / 200, (vw - xs_) / 480)[None, :]), 0, 1)
    openings = np.zeros((vh, vw), np.float32)
    for a in arches[:3]:
        am = C.arch_mask(*(cr(a['left_x'] + 10, 0)[0] - vx_, cr(a['right_x'] - 10, 0)[0] - vx_),
                         cr(0, a['spring_y'])[1] - vy_, cr(0, a['bottom_y'])[1] - vy_, h=vh, w=vw)
        openings = np.maximum(openings, am)
    ca = C.resize(C.blur(C.load('assets/cut/fig_couple_table.png')[..., 3], 2.0), cpl_s)
    ca_v = np.zeros((vh, vw), np.float32)
    ox_, oy_ = int(round(cpx)) - vx_, int(round(cpy)) - vy_
    hc, wc = min(ca.shape[0], vh - oy_), min(ca.shape[1], vw - ox_)
    ca_v[oy_:oy_ + hc, ox_:ox_ + wc] = ca[:hc, :wc]
    vm = vm * (1 - 0.85 * C.blur(openings, 18) * (1 - C.blur(ca_v, 6)))   # veil spares the booths, not the couple
    del ca, ca_v
    B.photo(g, 'Sheer - client drape as a veil (client)', veil, vx_, vy_, mask_alpha=vm,
            mask_xy=(vx_, vy_), opacity=0.40)
    del veil
    # glass-brick screen: nearest plane, one photograph (no stacking seam)
    sx0, sy0, sx1, sy1 = SCREEN
    sw, sh = sx1 - sx0, sy1 - sy0
    gba = C.cover(C.load('assets/gen/glassblock_wall_A.png', 'RGB'), sw + 160, sh, (1.0, 0.5))
    B.shadow(g, 'Shadow - glass-brick screen', np.ones((sh, sw), np.float32), sx0, sy0, depth=46, opacity=0.5)
    B.photo(g, 'Screen - glass-brick screen (photo)', gba, sx0 - 160, sy0,
            mask_alpha=C.rect_mask(sx0, sy0, sx1, sy1), margin=None)
    del gba
    B.fill(g, 'Grade - screen cooler', PAL['glass'], C.rect_mask(sx0, sy0, sx1, sy1),
           blend='soft light', opacity=0.35, clip=True)

    # ================================================================ 50 into the cabin (cabin 04 up close)
    g = B.group('50 - Into cabin 04 - up close', label='green', opened=True)
    a4 = arches[3]
    oL, oR = cr(a4['left_x'], 0)[0], cr(a4['right_x'], 0)[0]
    oT, oB = YCUT_C, cr(0, a4['bottom_y'])[1]
    zA, zB = (oL - 22, oT - 22), (oL - 22, oB + 26)
    tu, _ = tangent_points(zA, INSET_C, INSET_R)
    _, tl = tangent_points(zB, INSET_C, INSET_R)
    cone = C.poly_mask([zA, tu, (INSET_C[0] + INSET_R, INSET_C[1]), tl, zB])
    cone = np.clip(cone - C.ellipse_mask(INSET_C[0], INSET_C[1], INSET_R, INSET_R), 0, 1)
    cab_m = np.zeros((H, W), np.float32)
    hh_, ww_ = cut_s.shape
    cab_m[CR_Y:CR_Y + hh_, CR_X:CR_X + ww_] = cut_s[:H - CR_Y, :W - CR_X]
    del cut_s
    B.fill(g, 'Intensity - oxblood, approach to cabin 04', PAL['oxblood'], C.blur(cone * cab_m, 4),
           blend='soft light', opacity=0.5)
    B.fill(g, 'Zoom - cone onto the paper', PAL['ember'], C.blur(cone * (1 - cab_m), 2), blend='multiply',
           opacity=0.10)
    del cab_m
    zl = np.zeros((H, W), np.float32)
    for p_, q_ in ((zA, tu), (zB, tl)):
        aa_line(zl, [p_, q_], width=1.8)
    for (px_, py_), sx_, sy_ in ((zA, 1, 1), (zB, 1, -1)):           # corner brackets on cabin 04
        aa_line(zl, [(px_, py_ + 40 * sy_), (px_, py_), (px_ + 40 * sx_, py_)], width=1.8)
    B.fill(g, 'Zoom - hairlines to the lens', INK, zl, opacity=0.75)
    del zl
    # the lens itself
    lens = C.ellipse_mask(INSET_C[0], INSET_C[1], INSET_R, INSET_R)
    la, lx, ly = local(lens)
    B.shadow(g, 'Shadow - lens', la, lx, ly, depth=40, opacity=0.40)
    rim, pad = card_edge(la, width=7, color='#F6F0E4')
    B.px(g, 'Lens - paper rim', rim, lx - pad, ly - pad)
    ci = C.load('assets/gen/cabin_interior.png', 'RGB')
    m_ = 160
    sx0_ = int(CI_FOCUS[0] - (INSET_R + m_) / CI_S)
    sy0_ = int(CI_FOCUS[1] - (INSET_R + m_) / CI_S)
    sx1_ = int(CI_FOCUS[0] + (INSET_R + m_) / CI_S)
    sy1_ = int(CI_FOCUS[1] + (INSET_R + m_) / CI_S)
    sx0_, sy0_ = max(0, sx0_), max(0, sy0_)
    sx1_, sy1_ = min(ci.shape[1], sx1_), min(ci.shape[0], sy1_)
    cis = C.resize(ci[sy0_:sy1_, sx0_:sx1_], CI_S)
    del ci
    px_, py_ = ci2c(sx0_, sy0_)
    B.photo(g, 'Cabin 04 - inside the booth (photo)', cis, px_, py_, mask_alpha=lens)
    del cis
    yl = np.arange(H, dtype=np.float32)[:, None]
    canopy = lens * np.clip(((INSET_C[1] - 170) - yl) / 120.0, 0, 1)
    B.fill(g, 'Grade - canopy to linen (desaturate)', '#8C8C8C', canopy, blend='saturation', opacity=0.45, clip=True)
    B.fill(g, 'Grade - canopy to linen (colour)', LINEN, canopy, blend='color', opacity=0.25, clip=True)
    B.fill(g, 'Intensity - deepest warmth in the booth', PAL['oxblood'], lens * np.clip((yl - (INSET_C[1] - 200)) / 260.0, 0, 1),
           blend='soft light', opacity=0.55, clip=True)
    B.fill(g, 'Intensity - booth chroma', '#FF3A10', lens * np.clip((yl - (INSET_C[1] - 160)) / 260.0, 0, 1),
           blend='saturation', opacity=0.45, clip=True)
    del canopy, yl
    candle = ci2c(2538, 2664)
    shade = ci2c(2427, 1460)
    B.gen(g, 'Light - candle glow', S.glow(at=candle, radius=230, color=PAL['honey'], intensity=0.8,
                                           core=0.1, hot_color='#FFF2D6'), blend='screen', opacity=0.85)
    B.gen(g, 'Light - pendant pool over the table',
          S.light_beam(apex=shade, angle=90, length=330, spread=24, aperture=150, color=PAL['amber'],
                       intensity=0.32, dust=40, seed=7), blend='screen', opacity=0.8)
    del lens

    # ================================================================ 60 light & colour intensity
    g = B.group('60 - Light & colour intensity', label='yellow', opened=True)
    for i, s in enumerate(shades):
        x_, y_ = cr(*s['rim'])
        y_ += DROP
        B.gen(g, f'Light - pendant glow, cabin {i + 1}',
              S.glow(at=(x_, y_ + 70), radius=230 + 25 * i, color=PAL['amber'], intensity=0.5 + 0.1 * i,
                     ratio=0.7), blend='screen', opacity=0.8)
    B.fill(g, 'Intensity - pale linen where we stand', LINEN, blob(900, 2500, 1300, 1000, 1.2), blend='soft light',
           opacity=0.45)
    B.fill(g, 'Intensity - amber across the cabins', PAL['amber'], blob(2600, 2050, 1800, 600, 1.2),
           blend='soft light', opacity=0.40)

    # ================================================================ 70 senses
    g = B.group('70 - Senses - sound & smell', label='red', opened=True)
    a2 = arches[1]
    # SOUND 01: conversation travels from the couple's table into cabin 02, thinning as it enters
    src_s = (cx_ + 0.52 * cw_, cy_ + 0.30 * ch_)
    tgt = cr(a2['centre_x'], 1900)
    ang = math.degrees(math.atan2(-(tgt[1] - src_s[1]), tgt[0] - src_s[0]))
    dist = math.hypot(tgt[0] - src_s[0], tgt[1] - src_s[1])
    arcs_kw = dict(at=src_s, r_max=dist + 40, r_min=150, n=7, ratio=1.0, angle=ang, arc=(-26, 26), alpha=1.0,
                   decay=0.82, spacing=1.0, end_fade=12, seed=5)
    B.gen(g, 'Sound - conversation drifting into cabin 02',
          S.sound_rings(width=3.0, thin=0.92, color=LINEN, **arcs_kw), opacity=1.0)
    # SOUND 03: cutlery and laughter at the couple's table (just above their glasses)
    tbl = (cx_ + 0.50 * cw_, cy_ + 0.44 * ch_)
    r3kw = dict(at=tbl, r_max=330, r_min=90, n=4, ratio=0.28, alpha=1.0, decay=0.74, spacing=1.15,
                wobble=0.015, breaks=3, break_len=(20.0, 50.0), seed=9)      # ripples across the table top
    B.gen(g, 'Sound - cutlery, laughter at the table', S.sound_rings(width=2.6, color=LINEN, **r3kw),
          opacity=0.95)
    # SOUND 02: the linen ceiling swallows the echo (rings dissolving into the fabric)
    B.gen(g, 'Sound - echo dissolving into the linen',
          S.sound_rings(at=(2240, 640), r_max=560, r_min=80, n=5, ratio=0.5, angle=-5, width=3.0, color=INK,
                        alpha=0.7, decay=0.64, dash=(24.0, 14.0), spacing=1.15, wobble=0.02, breaks=3,
                        break_len=(14.0, 40.0), seed=4), opacity=0.9)
    # inside the booth: a hush
    hush = S.sound_rings(at=(candle[0], candle[1] - 30), r_max=300, r_min=70, n=4, ratio=0.42, width=2.2,
                         color=LINEN, alpha=0.6, decay=0.62, dash=(16.0, 12.0), seed=3)
    B.gen(g, 'Sound - a hush inside the booth', hush, opacity=0.85)
    # SMELL: bread and rosemary trailing behind the waiter's tray; beeswax in the booth
    tray = (wx + 0.80 * ww, wy + 0.255 * wh)
    B.gen(g, 'Smell - sourdough & rosemary from the tray',
          S.wisp(at=tray, height=520, ribbons=2, width=40, color=PAL['honey'], color_top=LINEN, opacity=0.95,
                 lean=0.15, seed=41), blend='screen')
    B.gen(g, 'Smell - beeswax candle in the booth',
          S.wisp(at=(candle[0], candle[1] - 18), height=360, ribbons=2, width=26, color=PAL['honey'],
                 color_top=LINEN, opacity=0.85, lean=0.12, seed=43), blend='screen')

    # ================================================================ 95 legend
    B.legend(B.doc.root, '02', [('colour', 'linen', 'LINEN'), ('colour', 'amber', 'AMBER'),
                        ('colour', 'terracotta', 'TERRACOTTA'), ('colour', 'oxblood', 'OXBLOOD'),
                        ('mat', 'velvet_terracotta', 'VELVET'), ('mat', 'oak_fluted', 'FLUTED OAK'),
                        ('mat', 'linen_plain', 'SHEER'), ('mat', 'glassblock', 'GLASS BLOCK')])

    # ================================================================ 98 type
    gt = B.group('98 - Type - title & annotations', opened=True)
    B.title_block(gt, 'RESTAURANT  ·  ATMOSPHERE STUDY  ·  02 / 02', ['Towards the cabins,', 'from a distance'],
                  'GROUND FLOOR  ·  ACROSS THE DINING ROOM TO THE FOUR CABINS')
    # tags
    hb = B.tag(gt, 'SOUND · 01', 'conversation dims\nas it enters the cabins', 1720, 2600, hero=True)
    B.leader(hb.group, 'Leader - sound 01 to the arcs', [(hb[0] + 120, hb[1]), (1880, 2330)], dot_at_end=True,
             width=2.0)
    B.tag(gt, 'SOUND · 02', 'linen swallows the echo', 2700, 300)
    lb = B.tag(gt, 'LIGHT', 'a low pendant over every table', 2780, 1450)
    r3 = cr(*shades[2]['rim'])
    r3 = (r3[0], r3[1] + DROP)                                       # the shade as hung (dropped)
    hw3 = shades[2]['half_width'] * CR_S
    B.leader(lb.group, 'Leader - light to pendant 3', [(lb[0] + 28, lb[3]), (r3[0] + 0.8 * hw3, r3[1] - 34)],
             dot_at_end=True, width=2.0)
    box = B.tag(gt, 'COLOUR', 'intensity deepens inward —\nlinen → amber → terracotta → oxblood', 3330, 300)
    bw_, bh_ = box[2] - box[0], 22
    stops = [PAL['linen'], PAL['amber'], PAL['terracotta'], PAL['oxblood']]
    cols = np.array([[int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)] for c in stops], np.float32)
    t_ = np.linspace(0, len(stops) - 1, bw_)
    i0 = np.clip(np.floor(t_).astype(int), 0, len(stops) - 2)
    f_ = (t_ - i0)[:, None]
    grad = np.ones((bh_, bw_, 4), np.float32)
    grad[..., :3] = (cols[i0] * (1 - f_) + cols[i0 + 1] * f_)[None, :, :]
    B.px(box.group, 'Colour - intensity scale, cabin 01 to 04', grad, box[0], box[3])
    sb = B.tag(gt, 'SOUND · 03', 'cutlery, low laughter,\na chair drawn back', 168, 1880)
    B.leader(sb.group, 'Leader - sound 03 to the table', [(sb[2], (sb[1] + sb[3]) / 2), (tbl[0] - 10, tbl[1] + 6)],
             dot_at_end=True, width=2.0)
    B.card(gt, 'Inside cabin 04', [('SMELL', 'beeswax candle · warm sourdough · rosemary'),
                                   ('TASTE', 'red wine, olive oil, sea salt'),
                                   ('TEXTURE', 'crushed velvet · ribbed oak · cool veined marble')],
           3150, 2570)
    # zoom label
    B.text(gt, 'CABIN 04 — INSIDE', 'mono', LABEL, INSET_C[0] - INSET_R + 30, INSET_C[1] - INSET_R - 36,
           tracking=120, color=PAL['terracotta'], name='TXT - lens label cabin 04')
    # cabin numbers on the partition tops
    for i, s_ in enumerate(shades):
        x_, _ = cr(*s_['rim'])
        y_ = YCUT_C - 46                                            # one baseline above the partition tops
        B.text(gt, f'0{i + 1}', 'mono', LABEL, x_ - s_['half_width'] * CR_S - 22, y_, anchor='origin',
               tracking=80, color=INK, name=f'TXT - cabin number 0{i + 1}', align='right')
    # partition height
    j1 = cr(arches[1]['right_x'], 0)[0] + 60                        # free oak between cabins 02 and 03
    dim = np.zeros((H, W), np.float32)
    y_a, y_b = YCUT_C + 2, cr(0, 2453)[1]
    aa_line(dim, [(j1, y_a), (j1, y_b)], width=1.8)
    for yv in (y_a, y_b):
        aa_line(dim, [(j1 - 14, yv + 14), (j1 + 14, yv - 14)], width=1.8)
    B.fill(gt, 'Dim - partition height 2400', LINEN, dim, opacity=0.9)
    B.text(gt, '2400 · OPEN ABOVE', 'mono', LABEL, j1 + 18, (y_a + y_b) / 2, tracking=100, color=LINEN, angle=90,
           anchor='origin', align='center', name='TXT - dim 2400 open above')
    # pointer to sheet 01
    B.text(gt, 'TO THE VOID (01)  →', 'mono', LABEL, W - MARGIN, 2600, anchor='origin', tracking=110,
           color=PAL['terracotta'], align='right', name='TXT - pointer to the void (01)')

    B.readme('Atmosphere collage 02 - Towards the cabins', sources=(
        '- Client: elevation 02 and the ground-floor plan (RESTAURANT.pdf), and the drape reference photo (sheer veil).\n'
        '- Photographs generated for this project with FLUX (via ElevenLabs): cabins row, cabin interior, festoon\n'
        '  valance, draped ceiling, glass-brick wall, diner silhouettes - AI-generated, no third-party photos.\n'
        '- Terrazzo, paper, sound and smell graphics: made for this file.'))
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
        out = C.P('build', 'preview', 'main')
        C.save_preview(comp, out + '/c02_full_preview.jpg', max_side=2000)
        from skimage.color import rgb2lab
        geo = json.load(open(C.P('assets', 'cut', 'geo', 'cabins_row', 'geometry.json')))
        rgb = comp[..., :3]

        def stats(region, name):
            lab = rgb2lab(np.clip(region, 0, 1))
            dark = (region.max(-1) < 25 / 255).mean() * 100
            print(f"{name}: L* {lab[..., 0].mean():.1f}  C* {np.hypot(lab[..., 1], lab[..., 2]).mean():.1f}  "
                  f"dark {dark:.1f}%")
        for a in geo['arches']:
            x0, x1 = int(cr(a['left_x'] + 30, 0)[0]), int(cr(a['right_x'] - 30, 0)[0])
            y0, y1 = int(YCUT_C + 20), int(cr(0, a['bottom_y'] - 30)[1])
            stats(rgb[y0:y1, x0:x1], f"cabin {a['id']}")
        cx, cy, r = INSET_C[0], INSET_C[1], INSET_R
        stats(rgb[int(cy - r * 0.6):int(cy + r * 0.6), int(cx - r * 0.6):int(cx + r * 0.6)], 'lens')
        if '--crops' in sys.argv:
            for nm, (x0, y0, x1, y1) in {'lens': (3300, 1450, 4900, 2650), 'top': (0, 0, 2480, 1700),
                                         'topR': (2480, 0, 4961, 1700),
                                         'mid': (0, 1500, 2480, 3100), 'midR': (2480, 1500, 4961, 3100),
                                         'bottom': (0, 2700, 4961, 3508)}.items():
                C.save_preview(comp[y0:y1, x0:x1], out + f'/c02_crop_{nm}.jpg', max_side=1800)
    print('done', round(time.time() - t, 1), 's')


if __name__ == '__main__':
    main()
