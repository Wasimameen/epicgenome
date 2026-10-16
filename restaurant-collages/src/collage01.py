"""Collage 01 — FROM THE VOID, LOOKING OUT.

Brief part 1: looking from within the chosen area (the double-height void with
the tree) to the outside views (the skylight above, the blue-hour street beyond
the glass-block entrance facade).

Run from src/:  python3 collage01.py            (preview render)
                python3 collage01.py --final    (PSD + JPEG + verification)
"""
from __future__ import annotations

import json
import sys
import time
import numpy as np

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from lib import compose as C
from lib import sensory as S
from lib.collage_common import (Builder, asset, have, INK, PAL, W, H, scallop_hem_mask, card_edge,
                                local, colour_rgba, grade)

LINEN = PAL['linen']
SLUG = 'restaurant-collage-01-from-the-void-looking-out'

# --------------------------------------------------------------------------- #
# layout (canvas px, A3 landscape 4961 x 3508 @ 300 ppi)
# --------------------------------------------------------------------------- #
VOID_C = (2330, 1640)          # centre of the circular void "window"
VOID_R = 1210
VB_S = 2 * VOID_R / 3664       # void_lookup_B -> circle scale
VB_OX = VOID_C[0] - VOID_R
VB_OY = VOID_C[1] - VOID_R - (4576 * VB_S - 2 * VOID_R) * 0.30   # crop 30 % from the top
TREE_SRC = (686, 1094)         # tree_B.png top-left inside void_lookup_B.png (template-matched)

OUT_BOX = (3080, 420, W, 2980)          # outside / facade panel (bleeds right)
WIN_X = (3760, 4230)                    # clear glazing strip in the facade
BAR_BOX = (150, 1330, 1390, 2600)       # glass-brick bar back wall
COUNTER_BOX = (90, 2600, 1520, 2900)    # fluted oak counter front
CEIL_H = 640                            # festoon band incl. scalloped hem
FLOOR_Y = 2950                          # floor horizon
SOIL_Y = 3215                           # where the trunk enters the planter


def vb(x, y):
    """void_lookup_B source px -> canvas px."""
    return VB_OX + x * VB_S, VB_OY + y * VB_S


def tree_layer():
    tree = C.resize(C.load('assets/cut/tree_B.png'), VB_S)
    tx, ty = vb(*TREE_SRC)
    ta = tree[..., 3]
    row = int(round(SOIL_Y - ty)) - 1
    cols = np.nonzero(ta[row] > 0.5)[0]
    return tree, tx, ty, tx + cols.mean()


def build():
    B = Builder('Restaurant — Atmosphere collage 01 — From the void, looking out')
    tree, tx, ty, trunk_x = tree_layer()

    # ================================================================ 00 paper
    g = B.group('00 · Paper', label='gray')
    B.px(g, 'Paper · warm linen ground', S.paper(H, W, color=PAL['paper'], seed=101), 0, 0)

    # ================================================================ 05 drawing underlay
    g = B.group('05 · Drawing underlay — section A-A', label='violet')
    sec = C.load('assets/lines/section_AA.png')
    s = 0.62
    secs = C.resize(sec, s)
    del sec
    # section trunk (x 2392 at ground FFL y 4228.5) on our trunk axis and floor line
    B.px(g, 'Drawing · section A-A (on the paper, under the photos)', secs,
         trunk_x - 2392 * s, FLOOR_Y - 4228.5 * s + 6, blend='multiply', opacity=0.6)
    del secs

    # ================================================================ 10 outside
    g = B.group('10 · Outside — blue-hour street', label='blue')
    ox0, oy0, ox1, oy1 = OUT_BOX
    ow, oh = ox1 - ox0, oy1 - oy0
    B.shadow(g, 'Shadow · facade panel', np.ones((oh, ow), np.float32), ox0, oy0, dx=-24, dy=30,
             sigma=40, opacity=0.36)
    B.px(g, 'Outside · panel (clipping base)', C.solid(oh, ow, PAL['indigo']), ox0, oy0)
    street = C.cover(C.load('assets/outside/street_dusk.png', 'RGB'), ow, oh, (0.66, 0.55))
    B.px(g, 'Outside · street at blue hour', street, ox0, oy0, clip=True)
    del street
    B.fill(g, 'Outside · dusk haze', PAL['dusk'], C.rect_mask(ox0, oy0, ox1, oy1),
           blend='soft light', opacity=0.3, clip=True)

    # ================================================================ 20 threshold
    g = B.group('20 · Threshold — glass-block facade', label='blue')
    # the photographed glass-block wall graded to blue hour, stacked at a measured mortar joint
    # (rows y 0-3236 + y 17-2756) so its blocks match the scale of the bar's glass-brick wall
    gbd = C.load('assets/outside/glassblock_A_dusk_grade.png', 'RGB')
    gbd = np.concatenate([gbd[0:3236], gbd[17:2756]], 0)
    gbd = C.cover(gbd, ow, oh, (0.12, 0.5))
    win = C.rect_mask(WIN_X[0], oy0, WIN_X[1], oy1)
    B.photo(g, 'Facade · glass blocks, street refracted', gbd, ox0, oy0,
            mask_alpha=C.rect_mask(ox0, oy0, ox1, oy1) * (1 - win))
    del gbd
    frame = np.clip(C.rect_mask(WIN_X[0] - 16, oy0, WIN_X[0], oy1) + C.rect_mask(WIN_X[1], oy0, WIN_X[1] + 16, oy1)
                    + C.rect_mask(WIN_X[0], 1560, WIN_X[1], 1574), 0, 1)
    a, x, y = local(frame)
    B.px(g, 'Facade · steel window frame', colour_rgba(a, '#353A45'), x, y, opacity=0.95)
    if have('outside', 'rain_on_glass.png'):
        rain = C.cover(C.load('assets/outside/rain_on_glass.png'), WIN_X[1] - WIN_X[0], oh, (0.5, 0.5))
        B.px(g, 'Facade · rain on the glass', rain, WIN_X[0], oy0, blend='screen', opacity=0.9)

    # ================================================================ 30 interior bar
    g = B.group('30 · Interior — bar & glass-brick wall', label='orange')
    bx0, by0, bx1, by1 = BAR_BOX
    bw, bh = bx1 - bx0, by1 - by0
    B.shadow(g, 'Shadow · bar wall', np.ones((bh, bw), np.float32), bx0, by0, dx=24, dy=30, sigma=36,
             opacity=0.40)
    gba = C.cover(C.load('assets/gen/glassblock_wall_A.png', 'RGB'), bw, bh, (0.25, 0.40))
    B.px(g, 'Bar · glass-brick back wall (warm)', gba, bx0, by0)
    del gba
    cx0, cy0, cx1, cy1 = COUNTER_BOX
    cw, ch = cx1 - cx0, cy1 - cy0
    flutes = C.texture_fill(C.load('assets/mat/oak_fluted.png', 'RGB'), ch, cw, scale=0.42)
    flutes = np.clip(flutes * np.linspace(1.06, 0.80, ch, dtype=np.float32)[:, None, None], 0, 1)
    B.shadow(g, 'Shadow · counter', np.ones((ch, cw), np.float32), cx0, cy0, dx=20, dy=26, sigma=28,
             opacity=0.45)
    B.px(g, 'Bar · fluted oak counter front', flutes, cx0, cy0)
    top = C.solid(24, cw + 34, PAL['steel'])
    top[..., :3] *= np.linspace(1.15, 0.74, 24, dtype=np.float32)[:, None, None]
    B.px(g, 'Bar · brushed steel counter top', np.clip(top, 0, 1), cx0 - 17, cy0 - 20)
    cup = C.resize(C.load('assets/cut/espresso_cc0.png'), 0.66)
    cux, cuy = 1110, cy0 - 20 - cup.shape[0] + 12
    B.shadow(g, 'Shadow · espresso cup', cup[..., 3], cux, cuy, dx=10, dy=8, sigma=10, opacity=0.35)
    B.px(g, 'Bar · espresso cup (CC0 photo)', cup, cux, cuy)
    pl = C.load('assets/cut/pendant_valance_L.png')
    pr = C.load('assets/cut/pendant_valance_R.png')
    shade_pts = []
    for i, (p, s_, xc, yb) in enumerate([(pl, 0.62, 400, 1395), (pr, 0.68, 800, 1480), (pl[:, ::-1], 0.56, 1180, 1360)]):
        pi = C.resize(p, s_)
        B.px(g, f'Bar · dome pendant {i + 1}', pi, xc - pi.shape[1] / 2, yb - pi.shape[0])
        shade_pts.append((xc, yb))

    # ================================================================ 40 ceiling
    g = B.group('40 · First-floor ceiling — festoon drapery', label='yellow')
    band = C.cover(C.load('assets/gen/ceiling_lookup_A.png', 'RGB'), W, CEIL_H + 40, (0.5, 0.58))
    band = grade(band, lift=0.05, sat=0.66, gamma=1.06)
    hem = scallop_hem_mask(0, W, 0, CEIL_H - 105, 100, 470, phase=0.2, jitter=0.1, seed=4)
    ha, _, _ = local(hem)
    B.shadow(g, 'Shadow · festoon hem on the page', ha, 0, 0, dx=0, dy=30, sigma=26, opacity=0.40)
    B.photo(g, 'Ceiling · festoon swags seen from below (photo, scalloped mask)', band, 0, 0, mask_alpha=hem)
    del band

    # ================================================================ 50 ground (behind the tree)
    g = B.group('50 · Ground — terrazzo floor & planter', label='gray')
    floor_poly = [(trunk_x - 830, FLOOR_Y), (trunk_x + 900, FLOOR_Y), (trunk_x + 1330, H), (trunk_x - 1250, H)]
    floor = C.poly_mask(floor_poly)
    a, flx, fly = local(floor)
    tz = C.texture_fill(C.load('assets/mat/terrazzo_cream.png', 'RGB'), a.shape[0], a.shape[1], scale=0.24)
    tz = grade(tz, lift=0.04, sat=0.72)
    tz = tz * np.linspace(0.93, 1.02, a.shape[0], dtype=np.float32)[:, None, None]
    B.shadow(g, 'Shadow · floor plane', a, flx, fly, dx=0, dy=-12, sigma=20, opacity=0.2)
    B.photo(g, 'Floor · cream terrazzo', np.clip(tz, 0, 1), flx, fly, mask_alpha=a, mask_xy=(flx, fly))
    B.gen(g, 'Floor · leaf-shadow dapple',
          S.dapple(size=(a.shape[1], a.shape[0]), at=(flx, fly), leaf_size=40, density=0.34, opacity=0.5,
                   angle=-18, edge_fade=0.10, seed=12), blend='multiply', opacity=0.6)
    soil = C.ellipse_mask(trunk_x, SOIL_Y, 380, 74)
    sa, sx, sy = local(soil)
    rng = np.random.default_rng(7)
    sl = colour_rgba(sa, '#3B3127')
    grain_ = C.blur(rng.standard_normal(sa.shape).astype(np.float32), 1.2) * 0.06
    sl[..., :3] = np.clip(sl[..., :3] * (1 + grain_[..., None])
                          * np.linspace(0.75, 1.15, sa.shape[0], dtype=np.float32)[:, None, None], 0, 1)
    B.px(g, 'Planter · damp soil', sl, sx, sy, opacity=0.97)
    back = np.clip(C.ellipse_mask(trunk_x, SOIL_Y + 4, 450, 104) - C.ellipse_mask(trunk_x, SOIL_Y, 384, 76), 0, 1)
    back[int(SOIL_Y):] = 0
    ra, rx, ry = local(back)
    B.px(g, 'Planter · sage rim (far half)', colour_rgba(ra, '#7D8962'), rx, ry)

    # ================================================================ 60 void
    g = B.group('60 · The void — looking up to the skylight', label='green', opened=True)
    vbs = C.resize(C.load('assets/gen/void_lookup_B.png', 'RGB'), VB_S)
    circle = C.ellipse_mask(VOID_C[0], VOID_C[1], VOID_R, VOID_R)
    cl, clx, cly = local(circle)
    B.shadow(g, 'Shadow · void disc', cl, clx, cly, dx=34, dy=46, sigma=50, opacity=0.5)
    B.px(g, 'Void · paper rim', card_edge(cl, width=12), clx - 12, cly - 12)
    B.photo(g, 'Void · looking up the void (photo, circular mask)', vbs, VB_OX, VB_OY, mask_alpha=circle)
    del vbs
    geo = json.load(open(asset('cut', 'geo', 'void_lookup_B', 'geometry.json')))
    skx, sky = vb(*geo['ellipses']['skylight']['centre'])
    B.gen(g, 'Light · skylight bloom', S.glow(at=(skx, sky), radius=820, color=PAL['honey'], intensity=0.5,
                                               ratio=0.75), blend='screen', opacity=0.7)

    # ================================================================ 70 tree
    g = B.group('70 · Tree — rising through the void', label='green', opened=True)
    ta = tree[..., 3]
    B.shadow(g, 'Shadow · tree cut-out', ta * (np.arange(ta.shape[0])[:, None] + ty < SOIL_Y), tx, ty,
             dx=28, dy=16, sigma=16, opacity=0.32)
    keep = C.rect_mask(0, 0, W, SOIL_Y + 6) + C.ellipse_mask(trunk_x, SOIL_Y, 300, 30)
    B.photo(g, 'Tree · cut-out, registered to the void photo', tree, tx, ty,
            mask_alpha=np.clip(keep, 0, 1) * C.rect_mask(tx, ty, tx + tree.shape[1], ty + tree.shape[0]))
    del tree, ta
    front = np.clip(C.ellipse_mask(trunk_x, SOIL_Y + 4, 450, 104) - C.ellipse_mask(trunk_x, SOIL_Y, 384, 76), 0, 1)
    front[: int(SOIL_Y)] = 0
    ra, rx, ry = local(front)
    B.shadow(g, 'Shadow · planter rim', ra, rx, ry, dx=0, dy=16, sigma=12, opacity=0.35)
    rim = colour_rgba(ra, PAL['sage'])
    rim[..., :3] = np.clip(rim[..., :3] * np.linspace(1.18, 0.82, ra.shape[0], dtype=np.float32)[:, None, None], 0, 1)
    B.px(g, 'Planter · sage rim (near half)', rim, rx, ry)

    # ================================================================ 80 light & colour intensity
    g = B.group('80 · Light & colour intensity', label='yellow', opened=True)
    B.gen(g, 'Light · daylight shaft down the void',
          S.light_beam(apex=(skx, sky - 80), angle=90, length=SOIL_Y - sky + 140, spread=8, aperture=480,
                       color=PAL['honey'], intensity=0.38, dust=200, seed=21), blend='screen', opacity=0.85)
    for i, (xc, yb_) in enumerate(shade_pts):
        B.gen(g, f'Light · pendant glow {i + 1}', S.glow(at=(xc, yb_ + 8), radius=430, color=PAL['amber'],
                                                         intensity=0.7, ratio=0.85), blend='screen', opacity=0.85)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

    def blob(cx, cy, rx, ry, k=1.5):
        return np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) * k)

    B.fill(g, 'Intensity · green-gold core (canopy + daylight)', PAL['canopy'],
           blob(VOID_C[0], VOID_C[1] - 220, 820, 880), blend='soft light', opacity=0.55)
    B.fill(g, 'Intensity · honey light pooling on the floor', PAL['honey'],
           blob(trunk_x, SOIL_Y - 120, 900, 300), blend='soft light', opacity=0.7)
    B.fill(g, 'Intensity · amber warmth at the bar', PAL['amber'], blob(760, 2050, 900, 1000, 1.3),
           blend='soft light', opacity=0.62)
    B.fill(g, 'Intensity · blue hour beyond the glass', PAL['dusk'],
           blob(4380, 1700, 1100, 1500, 1.1) * C.rect_mask(*OUT_BOX), blend='soft light', opacity=0.6)
    B.fill(g, 'Intensity · violet threshold (warm meets cool)', PAL['violet'],
           blob(3330, 1900, 360, 1150), blend='soft light', opacity=0.55)
    del xx, yy

    # ================================================================ 90 senses
    g = B.group('90 · Senses — sound · smell · taste · touch', label='red', opened=True)
    rings = np.zeros((H, W, 4), np.float32)
    steps = [(2760, 420), (2520, 620), (2270, 820), (2010, 1030), (1740, 1250), (1460, 1470), (1170, 1690)]
    for k, (yc, r) in enumerate(steps):
        rg, (x, y) = S.sound_rings(at=(VOID_C[0], yc), r_max=r, r_min=r, n=1, ratio=0.30, width=4.2,
                                   color='#FFFFFF', alpha=0.95 - k * 0.09, decay=1.0, wobble=0.004,
                                   breaks=2, seed=k)
        h_, w_ = rg.shape[:2]
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w_), min(H, y + h_)
        sub = rg[y0 - y:y1 - y, x0 - x:x1 - x]
        dst = rings[y0:y1, x0:x1]
        a_ = sub[..., 3:4]
        dst[..., 3:4] = a_ + dst[..., 3:4] * (1 - a_)
    inside = C.ellipse_mask(VOID_C[0], VOID_C[1], VOID_R - 4, VOID_R - 4)
    ri = rings.copy()
    ri[..., :3] = np.array([1.0, 0.93, 0.80], np.float32)          # warm linen-white inside the photo
    B.photo(g, 'Sound · voices rising up the void (inside the void)', ri, 0, 0, mask_alpha=inside, opacity=0.9)
    ro = rings
    ro[..., :3] = np.array([0.66, 0.31, 0.18], np.float32)          # terracotta ink where they escape
    B.photo(g, 'Sound · voices escaping the void (on the page)', ro, 0, 0, mask_alpha=1 - inside, opacity=0.85)
    del rings, ri, ro, inside
    B.gen(g, 'Sound · espresso hiss travelling to the void',
          S.waveform([(1300, 2470), (1560, 2400), (1820, 2300), (2080, 2190)], amplitude=48, wavelength=26,
                     width=2.4, color=PAL['ember'], decay_start=0.25, decay_end=0.95, seed=5), opacity=0.95)
    B.gen(g, 'Sound · rain on the glass, muffled',
          S.waveform([(WIN_X[0] + 60, 700), (WIN_X[0] + 70, 1300), (WIN_X[0] + 55, 1900), (WIN_X[0] + 65, 2500)],
                     amplitude=26, wavelength=16, width=1.8, color=PAL['glass'], decay_start=0.15,
                     decay_end=0.85, style='bars', seed=9), opacity=0.85)
    B.gen(g, 'Smell · roasted coffee rising from the bar',
          S.wisp(at=(cux + cup.shape[1] * 0.45, cuy + 30), height=1250, ribbons=3, width=110,
                 color=PAL['honey'], color_top=LINEN, opacity=1.0, lean=0.55, seed=31), blend='screen')
    B.gen(g, 'Smell · green leaf & damp soil at the planter',
          S.wisp(at=(trunk_x - 250, SOIL_Y - 30), height=780, ribbons=2, width=60, color=PAL['leaf'],
                 color_top=PAL['canopy'], opacity=0.8, lean=-0.14, seed=33))
    B.gen(g, 'Smell · petrichor drifting in from the street',
          S.wisp(at=(4560, 2930), height=900, ribbons=2, width=64, color=PAL['celadon'],
                 color_top=PAL['glass'], opacity=0.7, lean=-0.22, seed=35), blend='screen')

    # ================================================================ 95 key plan & palette
    g = B.group('95 · Key plan & palette', label='violet')
    plan = C.load('assets/lines/plan_ground.png')
    px0, py0, px1, py1 = 3480, 260, 6752, 2846
    ps = 0.155
    pc = C.resize(C.crop(plan, px0, py0, px1, py1), ps)
    del plan
    kx, ky = 3880, 3050
    B.px(g, 'Key plan · ground floor (client drawing)', pc, kx, ky, opacity=0.95)
    vcx, vcy = kx + (4948.8 - px0) * ps, ky + (1607.9 - py0) * ps
    ha, hx, hy = local(C.ellipse_mask(vcx, vcy, 500.2 * ps, 500.2 * ps))
    B.px(g, 'Key plan · the void (highlight)', colour_rgba(ha, PAL['canopy']), hx, hy, opacity=0.5, blend='multiply')
    B.gen(g, 'Key plan · view cone (from the void out to the street)',
          S.view_cone(apex=(vcx, vcy), direction=-8, fov=70, length=(6650 - 4948.8) * ps + 60,
                      color=PAL['terracotta'], fill=0.22), opacity=0.95)
    B.gen(g, 'Key plan · north point', S.north_arrow(at=(kx + pc.shape[1] + 70, ky + 60), size=90))
    B.text(g, 'KEY PLAN — GROUND FLOOR', 'mono', 19, kx, ky - 22, tracking=120)
    chips = [('linen', 'LINEN'), ('honey', 'HONEY'), ('amber', 'AMBER'), ('canopy', 'CANOPY'),
             ('steel', 'STEEL'), ('glass', 'GLASS'), ('dusk', 'DUSK'), ('indigo', 'INDIGO')]
    cx_ = 3842
    for key, lab in chips:
        B.gen(g, f'Palette · {lab.lower()} {PAL[key]}',
              S.swatch_chip(fill=PAL[key], at=(cx_, 3346), size=(112, 46), label=lab, sublabel=PAL[key],
                            label_size=19, label_gap=16))
        cx_ += 136

    # ================================================================ 98 type
    g = B.group('98 · Type — title & annotations', label='gray', opened=True)
    tx0 = 168
    B.text(g, 'RESTAURANT  ·  ATMOSPHERE STUDY  ·  01 / 02', 'mono', 28, tx0, 3040, tracking=140,
           color=PAL['terracotta'])
    B.text(g, 'From the void,', 'italic', 150, tx0 - 6, 3192)
    B.text(g, 'looking out', 'italic', 150, tx0 - 6, 3334)
    B.text(g, 'GROUND FLOOR  ·  THE DOUBLE-HEIGHT VOID', 'mono-light', 21, tx0, 3418, tracking=100)

    B.tag(g, 'SOUND · 01', 'voices from both floors\nrise and soften in the void', 1180, 700,
          phrase_size=50, label_size=24)
    B.card(g, 'At the bar', [('SOUND · 02', 'the hiss of the espresso machine,\na clink of glass'),
                             ('SMELL · 01', 'roasted coffee drifting from the bar'),
                             ('TASTE', 'bitter espresso, burnt sugar')],
           150, 1780, phrase_size=44, label_size=21, gap=30)
    B.tag(g, 'OUTSIDE · BLUE HOUR', 'rain on the street,\nsoftened by glass block', 4330, 720,
          phrase_size=46, label_size=22)
    B.tag(g, 'COLOUR', 'amber within → green-gold core\n→ blue hour beyond', 3150, 2380,
          phrase_size=44, label_size=22)
    B.tag(g, 'TEXTURE', 'cool glass block · brushed steel rail\nsmooth bark · soft linen overhead', 150, 790,
          phrase_size=42, label_size=21)
    B.tag(g, 'SMELL · 02', 'green leaf, damp soil', trunk_x - 1180, 3020, phrase_size=42, label_size=21)
    B.tag(g, 'LIGHT', 'daylight pours down the void', trunk_x + 330, 3020, phrase_size=42, label_size=21)
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
        C.save_preview(comp, C.P('build', 'preview', 'main', 'c01_full_preview.jpg'), max_side=2000)
        C.save_preview(comp[600:2400, 0:2600], C.P('build', 'preview', 'main', 'c01_crop_left.jpg'), max_side=1600)
        C.save_preview(comp[2400:3508, 1000:4961], C.P('build', 'preview', 'main', 'c01_crop_bottom.jpg'),
                       max_side=1600)
    print('done', round(time.time() - t, 1), 's')


if __name__ == '__main__':
    main()
