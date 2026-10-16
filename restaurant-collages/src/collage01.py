"""Collage 01 — FROM THE VOID, LOOKING OUT.

Brief part 1: looking FROM WITHIN the chosen area (standing beneath the tree in the
double-height void) TO the outside views — up through the skylight to the last blue
light, and out through the glazed glass-block entrance to the street at blue hour.

Spatial story (near -> far, nested):
  near   blurred leaves overhead, the festoon valance of the ground-floor ceiling
  here   the planter at our feet, the tree, the round void (the chosen area)
  behind the bar (west, behind the viewer)
  far    the glass-block entrance facade, the street beyond it

Run from src/:  python3 collage01.py              preview render -> build/preview/main/
                python3 collage01.py --crops      + 100 % crops of the delicate areas
                python3 collage01.py --check      + toggle test of every fill (>= 6 levels)
                python3 collage01.py --final      PSD + JPEG + verification (finalize)
"""
from __future__ import annotations

import json
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import compose as C  # noqa: E402
from lib import linework as LW  # noqa: E402
from lib import outside as O  # noqa: E402
from lib import sensory as S  # noqa: E402
from lib import typeset as T  # noqa: E402
from lib.collage_common import (Builder, INK, PAL, W, H, MARGIN, LABEL, HERO, PHRASE, card_edge,  # noqa: E402
                                local, colour_rgba, cut_info, aa_line)

SLUG = 'restaurant-collage-01-from-the-void-looking-out'
TITLE = 'Restaurant - Atmosphere collage 01 - From the void, looking out'
CACHE = C.P('build', 'c01')
PREVIEW = C.P('build', 'preview', 'main')

LINEN = PAL['linen']
GREEN_GOLD = '#B9D46A'          # between honey and canopy: the colour of the chosen area
STEEL_DARK = '#30343B'          # anodised steel of the entrance frame

# --------------------------------------------------------------------------- #
# layout (canvas px, A3 landscape 4961 x 3508 @ 300 ppi)
# --------------------------------------------------------------------------- #
FLOOR_Y = 2880                  # one floor line for bar, floor plane and facade

# the void disc: void_lookup_B at exactly 2/3 so B.cutout('tree_B.png') resamples to the
# very same pixels as the void photo (crop origins land on whole output pixels)
VOID_C = (2280, 1700)
VOID_R = 1150
VB_S = 2.0 / 3.0
VB_OX, VB_OY = 1067, 253        # canvas position of void_lookup_B (0, 0)
TREE_MARGIN = 41                # (668-41)*2/3 and (794-41)*2/3 are whole pixels


def vb(x, y):
    """void_lookup_B source px -> canvas px."""
    return VB_OX + x * VB_S, VB_OY + y * VB_S


TREE_BOX = cut_info('tree_B.png')['src_box']                  # [668, 794, 2955, 4576]
TRUNK_X = vb(1791, 0)[0]                                      # trunk axis at the photo's bottom edge

# entrance facade: procedural glass blocks on a regular coursing (snap everything to it)
GB_X, GB_Y = 2566, 1000         # canvas position of the block render
GB_B, GB_M = 125, 9             # block / mortar px  (190 mm + 10 mm at ~0.67 px/mm)
GB_P = GB_B + GB_M
GB_COLS, GB_ROWS = 19, 15


def gb_x(k):
    """Canvas x of vertical mortar centre line k."""
    return GB_X + GB_M / 2 + GB_P * k


def gb_y(r):
    return GB_Y + GB_M / 2 + GB_P * r


FAC_X0, FAC_Y0 = gb_x(1), gb_y(2)            # 2704.5, 1272.5 (top below the sky: the far wall reads lower)
FAC_Y1 = FLOOR_Y
DOOR_X0, DOOR_X1, SIDE_X1 = gb_x(9), gb_x(14), gb_x(16)   # door leaf 5 blocks, sidelight 2 blocks
TRANSOM_Y = gb_y(3)                          # door head: 11 courses above the floor
STREET_S = 0.75                              # street_dusk scale behind the facade
STREET_CROP = (441, 538)                     # (x, y) of the facade render origin in the scaled street

# the bar behind us, registered to elevation 01 (drawing px -> canvas)
EL_K = 0.62
EL_X0 = MARGIN - 18 * EL_K
EL_Y0 = FLOOR_Y - 2052.5 * EL_K


def el(x, y):
    return EL_X0 + x * EL_K, EL_Y0 + y * EL_K


BAR_X0, BAR_X1 = MARGIN, 1600                # the void overlaps the bar decisively
BULK_Y0 = round(el(0, 17.5)[1])              # top of the fluted bulkhead (sign band)
BULK_Y1 = round(el(0, 828)[1])               # bulkhead soffit = top of the glass-brick wall
CTR_Y = round(el(0, 1561)[1])                # counter top
CTR_X0, CTR_X1 = MARGIN - 6, 1150            # counter >= 300 px clear of the void
PEND_X = (282, 546, 810, 1074)               # four dome pendants (elevation 01), clear of the void
PEND_S = 0.34

# festoon valance overhead (festoon_valance.png, real fabric mask)
VAL_S = 0.9
VAL_SX0, VAL_SY0 = 454, 449                  # source px at canvas (0, 0)

# planter at our feet
PL_CX, PL_CY = TRUNK_X, 3140                 # centre of the rim's top ellipse
PL_RX, PL_RY = 600, 190                      # big and near: its front bleeds off the page, we stand at its rim
PL_RIM = 62                                  # rim width (plan)
PL_FACE = 190                                # visible height of the front face
PL_SOIL_DROP = 14

# floor plane (visible cut) and its perspective quad (texture warp)
FLOOR_POLY = [(1300, FLOOR_Y), (3060, FLOOR_Y), (3020, H + 60), (1370, H + 60)]
LEGEND_X = 3100                              # shared legend block: keep art clear of x >= 3100, y >= 2980
FLOOR_FEATHER = 70                           # the floor's sides dissolve into the paper
FLOOR_WARP = [(1290, FLOOR_Y - 20), (3300, FLOOR_Y - 20), (3960, H + 40), (520, H + 40)]

# twigs reaching out of the void (same tree, a step nearer): (side, tree_B box, angle, anchor in box,
# canvas target of the anchor) — the anchor (stem end) sits on the crown's edge
TWIG_S = 1.05
TWIGS = (('left', (0, 1080, 640, 1470), -57.0, (640, 230), (1792, 1155)),     # angle: deg CCW on the page
         ('right', (1700, 1090, 2287, 1480), 52.0, (0, 220), (2592, 1129)))   # anchors sit inside the crown

NEAR_MAX_Y = 700                 # near leaves stay above the tag row

# viewer + sightlines
VIEWER = (TRUNK_X + 150, PL_CY + PL_RY * 0.968 - PL_RIM * 0.5)   # on the planter's near rim, by the trunk


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #

def rgb01(hexc):
    c = hexc.lstrip('#')
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def cached_png(name, fn, mode='RGBA'):
    """Load build/c01/<name> or create it with fn() (float RGBA / L, deterministic)."""
    path = os.path.join(CACHE, name)
    if os.path.exists(path):
        return C.load(path, mode)
    arr = fn()
    os.makedirs(CACHE, exist_ok=True)
    from PIL import Image
    q = np.clip(np.floor(arr * 255 + 0.5), 0, 255).astype(np.uint8)
    Image.fromarray(q, 'RGBA' if q.ndim == 3 else 'L').save(path, compress_level=6)
    return C.load(path, mode)


def disc(cx, cy, r, feather=0.0):
    return C.ellipse_mask(cx, cy, r, r, feather=feather)


def box_alpha(x0, y0, x1, y1):
    return C.rect_mask(x0, y0, x1, y1)


def tag_size(label, phrase, hero=False, pad=(36, 28)):
    _, m = T.label_block(label, phrase, label_size=LABEL, phrase_size=HERO if hero else PHRASE)
    ix0, iy0, ix1, iy1 = m['ink_box']
    return int(round(ix1 - ix0 + 2 * pad[0])), int(round(iy1 - iy0 + 2 * pad[1]))


_YY = None


def yy_canvas():
    global _YY
    if _YY is None:
        _YY = np.arange(H, dtype=np.float32)[:, None] * np.ones((1, W), np.float32)
    return _YY


def soft_noise(h, w, scale, seed, octaves=3):
    return S.smooth_noise(h, w, scale, seed, octaves=octaves).astype(np.float32)


# --------------------------------------------------------------------------- #
# derived assets (cached in build/c01/, deterministic)
# --------------------------------------------------------------------------- #

def street_scene():
    """street_dusk at STREET_S, cropped to the facade block render (the view behind the wall),
    with the same lift / warm-wet grade as the 'Grade ·' fills on the street layer."""
    st = C.resize(C.load('assets/outside/street_dusk.png', 'RGB'), STREET_S)
    ox, oy = STREET_CROP
    w, h = GB_COLS * GB_B + (GB_COLS + 1) * GB_M, GB_ROWS * GB_B + (GB_ROWS + 1) * GB_M
    sc = st[oy:oy + h, ox:ox + w].copy()
    del st
    sc = street_grade(sc, GB_Y)
    return sc


def street_grade(rgb, y_top):
    """Numeric twin of the street's clipped grade fills (screen lift + soft-light warm street)."""
    lift = rgb01('#4A5578') * 0.45
    out = 1 - (1 - rgb) * (1 - lift)
    yy = (np.arange(rgb.shape[0], dtype=np.float32) + y_top)[:, None]
    wet = (smoothstep(1900, 2500, yy) * 0.5)[..., None]
    cs = rgb01(PAL['honey'])
    d = np.where(out <= 0.25, ((16 * out - 12) * out + 4) * out, np.sqrt(np.clip(out, 0, 1)))
    sl = np.where(cs <= 0.5, out - (1 - 2 * cs) * out * (1 - out), out + (2 * cs - 1) * (d - out))
    return np.clip(out + (sl - out) * wet, 0, 1).astype(np.float32)


def facade_blocks():
    """The entrance wall: street_dusk refracted through pressed glass blocks (outside.py)."""
    def make():
        sc = street_scene()
        out = O.glassblock_refract(sc, GB_COLS, GB_ROWS, GB_B, GB_M, seed=31, tint='#B4C8C6', mortar='#B8BCBD',
                                   mortar_level=0.66, light='#FFD8A8', light_level=0.55, scene_blur=1.0,
                                   parallax=0.6, distortion=1.35)
        return out
    return cached_png('facade_glassblock_street_v2.png', make)


def terrazzo_mosaic():
    """Aperiodic terrazzo: the seamless tile texture-bombed into Voronoi cells (random offset +
    dihedral turn per cell, 2 px seams), so no repeat shows once perspective-warped."""
    def make():
        tile = C.resize(C.load('assets/mat/terrazzo_cream.png', 'RGB'), 0.32)
        T_ = tile.shape[0]
        variants = [tile, np.rot90(tile, 1), np.rot90(tile, 2), np.rot90(tile, 3),
                    tile[:, ::-1], np.rot90(tile[:, ::-1], 1), tile[::-1], np.rot90(tile[::-1], 1)]
        variants = [np.ascontiguousarray(v) for v in variants]
        Wm, Hm = 3600, 1900
        rng = np.random.default_rng(23)
        n = 150
        seeds = np.stack([rng.uniform(-200, Wm + 200, n), rng.uniform(-200, Hm + 200, n)], 1)
        from scipy.spatial import cKDTree
        yy, xx = np.mgrid[0:Hm, 0:Wm]
        pts = np.stack([xx.ravel(), yy.ravel()], 1).astype(np.float32)
        tree = cKDTree(seeds)
        d, idx = tree.query(pts, k=2)
        idx0 = idx[:, 0].reshape(Hm, Wm)
        seam = (d[:, 1] - d[:, 0]).reshape(Hm, Wm).astype(np.float32)
        del pts, d, idx
        var = rng.integers(0, 8, n)
        offx = rng.integers(0, T_, n)
        offy = rng.integers(0, T_, n)
        out = np.zeros((Hm, Wm, 3), np.float32)
        for v in range(8):
            cells = np.flatnonzero(var == v)
            if not len(cells):
                continue
            sel = np.isin(idx0, cells)
            ys, xs = np.nonzero(sel)
            cid = idx0[ys, xs]
            out[ys, xs] = variants[v][(ys + offy[cid]) % T_, (xs + offx[cid]) % T_]
        # soften the seams a hair (2 px) so cut chips read as irregular chips, not lines
        bl = cv2.GaussianBlur(out, (0, 0), 1.2)
        k = smoothstep(0.0, 3.0, seam)[..., None]
        out = out * k + bl * (1 - k)
        return np.dstack([out, np.ones((Hm, Wm), np.float32)])
    return cached_png('terrazzo_floor_mosaic_v1.png', make)


def defringe_mask(rgb):
    """Violet chromatic-aberration fringes (hue 245-310 deg, saturated, next to strong edges)."""
    hsv = cv2.cvtColor(np.ascontiguousarray(rgb[..., :3]), cv2.COLOR_RGB2HSV)
    h, s = hsv[..., 0], hsv[..., 1]
    vio = ((h >= 245) & (h <= 310) & (s > 0.10)).astype(np.float32)
    L = C.blur(C.lum(rgb), 0.8)
    g = np.hypot(cv2.Sobel(L, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(L, cv2.CV_32F, 0, 1, ksize=3))
    edge = cv2.dilate((g > 0.25).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
    return C.blur(vio * edge, 0.7)


# --------------------------------------------------------------------------- #
# pieces
# --------------------------------------------------------------------------- #

def valance_parts():
    """festoon_valance photo crop (+ spare), its real fabric mask with the jabot tail and side
    tails taken out, and two clone-retouch patches that remove the pendant cords."""
    sx0, sy0, sx1, sy1 = 300, 280, 6150, 1420
    v = C.load('assets/gen/festoon_valance.png', 'RGB')[sy0:sy1, sx0:sx1].copy()
    m = C.load('assets/cut/geo/festoon_valance/valance_fabric.png', 'L')[sy0:sy1, sx0:sx1].copy()
    geo = json.load(open(C.P('assets', 'cut', 'geo', 'festoon_valance', 'geometry.json')))
    xs = np.arange(sx0, sx1, dtype=np.float32)
    ys = np.arange(sy0, sy1, dtype=np.float32)
    # side tails out (they hang to the floor) — keep the swag span only
    m *= (smoothstep(424, 436, xs) * (1 - smoothstep(5984, 5996, xs)))[None, :]
    tails = np.maximum(1 - smoothstep(500, 540, xs), smoothstep(5800, 5840, xs))[None, :]
    m *= 1 - tails * smoothstep(1090, 1110, ys)[:, None]          # the tails' hanging ends cut at the hem
    # jabot tail: cut along a gather cusp drawn into the neighbouring hems
    xl, xc_, xr = 3560.0, 3706.0, 3905.0
    yl = float(np.interp(xl, *np.array(geo['hem_every_16px']).T))
    yr = float(np.interp(xr, *np.array(geo['hem_every_16px']).T))
    yc = 712.0
    ycut = np.full_like(xs, 1e9)
    left = (xs >= xl) & (xs <= xc_)
    right = (xs > xc_) & (xs <= xr)
    ycut[left] = yc + (yl - yc) * ((xc_ - xs[left]) / (xc_ - xl)) ** 0.62
    ycut[right] = yc + (yr - yc) * ((xs[right] - xc_) / (xr - xc_)) ** 0.62
    cut = np.clip(ycut[None, :] - ys[:, None] + 0.5, 0, 1)
    m *= cut
    # the fabric mask leaves a slit where each cord crosses the cloth: close it from both sides
    for cd in geo['pendant_cords']:
        for yi in range(m.shape[0]):
            xc = int(round(cd['a'] + cd['b'] * (yi + sy0))) - sx0
            m[yi, xc - 13:xc + 14] = min(m[yi, xc - 16], m[yi, xc + 16])
    # cord retouch (heal): low frequencies interpolated across the strip, texture borrowed
    # from 34 px to the side; returned as separate patches for 'Retouch ·' layers
    hp = v - cv2.GaussianBlur(v, (0, 0), 2.0)
    patches = []
    for cd in geo['pendant_cords']:
        yy = np.arange(sy0, min(sy1, 1240))
        xc = cd['a'] + cd['b'] * yy
        half, feather, rows = 10, 5, yy - sy0
        xmin = int(np.floor(xc.min())) - half - feather - 2 - sx0
        xmax = int(np.ceil(xc.max())) + half + feather + 3 - sx0
        pw = xmax - xmin
        patch = np.zeros((len(yy), pw, 4), np.float32)
        Lc = np.stack([v[rows, np.round(xc - half - feather - k).astype(int) - sx0] for k in range(1, 4)]).mean(0)
        Rc = np.stack([v[rows, np.round(xc + half + feather + k).astype(int) - sx0] for k in range(1, 4)]).mean(0)
        for j in range(pw):
            xj = xmin + j + sx0
            dx = xj - xc
            t = np.clip((dx + half + feather) / (2 * (half + feather)), 0, 1)[:, None]
            base = Lc * (1 - t) + Rc * t
            src = np.clip(np.round(xj + 34).astype(int) - sx0, 0, v.shape[1] - 1)
            tex = hp[rows, src]
            a = 1 - smoothstep(half, half + feather, np.abs(dx))
            patch[:, j, :3] = np.clip(base + tex, 0, 1)
            patch[:, j, 3] = a
        patches.append((patch, xmin + sx0, sy0))
    return v, m, (sx0, sy0), patches


def planter_parts():
    """Concrete planter ring (top annulus + front face + far inner wall), damp soil, and the
    soil 'lip' that swallows the trunk base.  Returns local RGBA layers + their origin."""
    pad = 40
    x0 = int(PL_CX - PL_RX - pad)
    y0 = int(PL_CY - PL_RY - pad)
    w = int(2 * (PL_RX + pad))
    h = int(2 * PL_RY + PL_FACE + 2 * pad)
    cx, cy = PL_CX - x0, PL_CY - y0
    rxi = PL_RX - PL_RIM
    ryi = PL_RY - PL_RIM * PL_RY / PL_RX
    E = lambda ccx, ccy, rx, ry: C.ellipse_mask(ccx, ccy, rx, ry, h=h, w=w)  # noqa: E731
    outer = E(cx, cy, PL_RX, PL_RY)
    inner = E(cx, cy, rxi, ryi)
    soil = E(cx, cy + PL_SOIL_DROP, rxi - 2, ryi - 1) * inner
    rim_top = np.clip(outer - inner, 0, 1)
    # front face: the outer ellipse swept down by PL_FACE (lower half only)
    t = np.linspace(0, np.pi, 200)
    arc = np.stack([cx + PL_RX * np.cos(t), cy + PL_RY * np.sin(t)], 1)
    face_poly = np.vstack([arc, arc[::-1] + [0, PL_FACE]])
    face = np.clip(C.poly_mask(face_poly, h, w) - outer, 0, 1)
    wall_in = np.clip(inner - soil, 0, 1)
    # textures
    plaster = C.load('assets/mat/plaster_warm.png', 'RGB')
    plaster = plaster[:h, :w] if plaster.shape[0] >= h and plaster.shape[1] >= w else C.texture_fill(plaster, h, w)
    pl_l = C.lum(plaster)
    pits = 0.30 * (pl_l - C.blur(pl_l, 6))[..., None]
    mott = soft_noise(h, w, 90, 5)[..., None]
    rng0 = np.random.default_rng(17)
    agg = C.blur((rng0.random((h, w)) > 0.985).astype(np.float32), 0.8) * rng0.uniform(-1, 1, (h, w)).astype(np.float32)
    base = rgb01('#B9B2A6')
    conc = np.clip(base * (1 + 1.1 * pits + 0.08 * (mott - 0.5) + 0.35 * agg[..., None]), 0, 1)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # rain-streak staining down the front face (very faint, vertical)
    streak = C.blur(rng0.standard_normal((1, w)).astype(np.float32), 3.0) * np.ones((h, 1), np.float32)
    conc = conc * (1 + 0.035 * streak[..., None])
    u = np.clip((xx - cx) / PL_RX, -1, 1)
    # light from the upper left: top face bright, front face shaded like a cylinder
    top_sh = 1.06 + 0.05 * (-u)
    face_v = np.clip((yy - (cy + PL_RY * np.sqrt(np.clip(1 - u * u, 0, 1)))) / PL_FACE, 0, 1)
    face_sh = (0.84 - 0.16 * face_v) * (0.80 + 0.20 * np.sqrt(np.clip(1 - u * u, 0, 1))) * (1 + 0.06 * (-u))
    in_sh = 0.56 + 0.10 * np.clip((cy - yy) / ryi, 0, 1)
    rgb = np.zeros((h, w, 3), np.float32)
    a = np.zeros((h, w), np.float32)
    for m_, sh in ((wall_in, in_sh), (face, face_sh), (rim_top, top_sh)):
        rgb = rgb * (1 - m_[..., None]) + conc * sh[..., None] * m_[..., None]
        a = np.maximum(a, m_)
    # arris highlight along the near edge of the top face; contact darkening at the face's foot
    arc_y = cy + PL_RY * np.sqrt(np.clip(1 - u * u, 0, 1))
    near_edge = np.clip(1 - np.abs(yy - arc_y + 1.5) / 1.4, 0, 1) * (yy > cy)
    rgb = rgb + (near_edge * 0.16)[..., None] * a[..., None]
    foot = smoothstep(PL_FACE - 22, PL_FACE, yy - arc_y) * face
    rgb = rgb * (1 - 0.30 * foot[..., None])
    inner_lip = np.clip(1 - np.abs(np.sqrt(((xx - cx) / rxi) ** 2 + ((yy - cy) / ryi) ** 2) - 1) * rxi / 2.0, 0, 1)
    rgb = rgb * (1 - 0.25 * (inner_lip * (yy < cy + 2))[..., None])
    # damp soil: dark loam, fine crumbs, a few pale grit stones, darker towards the rim
    rng = np.random.default_rng(41)
    n1 = C.blur(rng.standard_normal((h, w)).astype(np.float32), 0.9)
    n2 = C.blur(rng.standard_normal((h, w)).astype(np.float32), 3.0)
    loam = rgb01('#463628') * (1 + 0.20 * n1 + 0.22 * n2)[..., None]
    grit = (C.blur((rng.random((h, w)) > 0.9975).astype(np.float32), 1.1) * 3.0).clip(0, 1)
    loam = loam * (1 - grit[..., None]) + rgb01('#9C8C78') * grit[..., None]
    sd = np.sqrt(((xx - cx) / (rxi - 2)) ** 2 + ((yy - cy - PL_SOIL_DROP) / (ryi - 1)) ** 2)
    loam *= (1.0 - 0.35 * smoothstep(0.55, 1.0, sd))[..., None]
    # moist collar around the trunk base
    tdist = np.sqrt(((xx - (TRUNK_X - x0)) / 95) ** 2 + ((yy - (cy + PL_SOIL_DROP + 2)) / 22) ** 2)
    loam *= (1 - 0.28 * (1 - smoothstep(0.6, 1.2, tdist)))[..., None]
    rgb = rgb * (1 - soil[..., None]) + np.clip(loam, 0, 1) * soil[..., None]
    a = np.maximum(a, soil)
    back = np.dstack([np.clip(rgb, 0, 1), a])
    # the lip: the soil in front of the trunk, irregular crumb edge
    tx = TRUNK_X - x0
    # a low crumbly mound rises around the trunk and swallows its base
    # the soil meets the trunk along the front half of a small ellipse round it (lowest in front),
    # with a crumbly, irregular line; a low mound around the base
    xs_ = np.arange(w, dtype=np.float32)
    u_ = np.clip((xs_ - tx) / 62.0, -1, 1)
    contact = cy + PL_SOIL_DROP - 38 + 13 * np.sqrt(1 - u_ * u_)
    mound = 28 * (1 - smoothstep(60, 150, np.abs(xs_ - tx)))
    edge_y = np.where(np.abs(xs_ - tx) < 62, contact, cy + PL_SOIL_DROP - mound) \
        + 2.4 * C.blur(rng.standard_normal((1, w)).astype(np.float32), 1.0)[0]
    lip = soil * np.clip(yy - edge_y[None, :] + 0.5, 0, 1) * (1 - smoothstep(140, 170, np.abs(xx - tx)))
    # the mound's crumbly crest catches a little light; its foot sinks into shade
    crest = np.clip(1 - (yy - edge_y[None, :]) / 5.0, 0, 1) * (yy >= edge_y[None, :] - 0.5)
    back[..., :3] = back[..., :3] * (1 + 0.10 * crest[..., None] * (lip > 0)[..., None])
    lip_rgba = np.dstack([back[..., :3], lip])
    return back, lip_rgba, (x0, y0)


def leaf_piece(box, scale, angle, flip=False, blur=0.0, anchor=(0.0, 0.0), feather=0):
    """A crop of the tree (void_lookup_B pixels + tree_B alpha) scaled / turned (deg CCW) /
    optionally mirrored.  box is in tree_B cut coordinates; anchor is a point of the crop
    (crop px, before mirroring).  Returns (rgb, alpha, anchor_xy_in_result)."""
    bx0, by0, bx1, by1 = box
    sx0, sy0 = TREE_BOX[0], TREE_BOX[1]
    v = C.load('assets/gen/void_lookup_B.png', 'RGB')[sy0 + by0:sy0 + by1, sx0 + bx0:sx0 + bx1].copy()
    a = C.load('assets/cut/tree_B.png')[by0:by1, bx0:bx1, 3].copy()
    h, w = a.shape
    ax, ay = anchor
    if feather:
        # no straight crop edges: the twig dissolves leaf by leaf towards the box sides (a noise
        # threshold, not a ghosting fade), most on the anchor side where it merges into the crown
        xs, ys = np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32)
        fx = smoothstep(0, feather, np.abs(xs - ax)) if ax in (0, w) else np.ones(w, np.float32)
        far = smoothstep(0, feather * 0.35, np.minimum(xs, w - 1 - xs))
        fy = smoothstep(0, feather * 0.35, np.minimum(ys, h - 1 - ys))
        ramp = (fx * far)[None, :] * fy[:, None]
        n = soft_noise(h, w, 24, int(bx0 + by0), octaves=2)
        n = (n - n.min()) / max(1e-6, float(n.max() - n.min()))
        a = a * smoothstep(n - 0.06, n + 0.06, ramp * 1.12 - 0.06)
    if flip:
        v, a, ax = v[:, ::-1], a[:, ::-1], w - ax
    # colour of the leaves only (pull leaf colour over the white-sky edge contamination)
    pm = cv2.GaussianBlur(v * a[..., None], (0, 0), 1.5)
    aa = cv2.GaussianBlur(a, (0, 0), 1.5)
    fill = np.where(aa[..., None] > 1e-4, pm / np.maximum(aa[..., None], 1e-4), v)
    k = np.clip(a * 1.6 - 0.3, 0, 1)[..., None]
    v = v * k + fill * (1 - k)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
    cs_, sn_ = abs(M[0, 0]), abs(M[0, 1])
    nw, nh = int(np.ceil(h * sn_ + w * cs_)) + 4, int(np.ceil(h * cs_ + w * sn_)) + 4
    M[0, 2] += nw / 2 - w / 2
    M[1, 2] += nh / 2 - h / 2
    interp = cv2.INTER_AREA if scale < 0.8 else cv2.INTER_LINEAR
    rgb = cv2.warpAffine(np.ascontiguousarray(v * a[..., None]), M, (nw, nh), flags=interp)
    al = cv2.warpAffine(np.ascontiguousarray(a), M, (nw, nh), flags=interp)
    if blur:
        rgb = cv2.GaussianBlur(rgb, (0, 0), blur)
        al = cv2.GaussianBlur(al, (0, 0), blur)
    rgb = np.where(al[..., None] > 1e-4, rgb / np.maximum(al[..., None], 1e-4), 0)
    # opaque, edge-extended RGB (leaf colour bleeds outwards) so the layer mask alone cuts the twig
    pm_b = cv2.GaussianBlur(rgb * al[..., None], (0, 0), 24)
    al_b = cv2.GaussianBlur(al, (0, 0), 24)[..., None]
    mean = (rgb * al[..., None]).reshape(-1, 3).sum(0) / max(1e-4, float(al.sum()))
    ext = np.where(al_b > 1e-3, pm_b / np.maximum(al_b, 1e-3), mean[None, None, :])
    k = np.clip(al * 4.0, 0, 1)[..., None]
    rgb = rgb * k + ext * (1 - k)
    q = M @ np.array([ax, ay, 1.0])
    return np.clip(rgb, 0, 1).astype(np.float32), np.clip(al, 0, 1).astype(np.float32), (float(q[0]), float(q[1]))


def rain_beads():
    """rain_on_glass.png without its long runs (they read as cracks): beads only."""
    def make():
        r = C.load('assets/outside/rain_on_glass.png')
        a = r[..., 3]
        body = (a > 0.04).astype(np.uint8)
        runs = cv2.morphologyEx(body, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 41)))
        runs = cv2.dilate(runs, np.ones((7, 9), np.uint8)).astype(np.float32)
        r[..., 3] = a * (1 - C.blur(runs, 1.5))
        return r
    return cached_png('rain_beads_no_runs_v1.png', make)


def rain_dashes(w, h, n, seed, length=(14, 40), angle=8.0, width=(1.6, 2.2), alpha=(0.25, 0.7)):
    """Short slanted dashes (rain falling outside), exact anti-aliased coverage (aa_line)."""
    rng = np.random.default_rng(seed)
    cov = np.zeros((h, w), np.float32)
    th = np.radians(angle)
    d = np.array([np.sin(th), np.cos(th)])
    for _ in range(n):
        c = np.array([rng.uniform(0, w), rng.uniform(0, h)])
        L = rng.uniform(*length)
        aa_line(cov, [c - d * L / 2, c + d * L / 2], width=rng.uniform(*width), alpha=rng.uniform(*alpha))
    return cov


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #

def build():
    B = Builder(TITLE)
    circle = disc(VOID_C[0], VOID_C[1], VOID_R)              # full-canvas void disc
    fac_rect = box_alpha(FAC_X0, FAC_Y0, W + 2, FAC_Y1)
    glazing = box_alpha(DOOR_X0, FAC_Y0, SIDE_X1, FAC_Y1)
    bar_plane = box_alpha(BAR_X0, BULK_Y0, BAR_X1, CTR_Y)
    geo_void = json.load(open(C.P('assets', 'cut', 'geo', 'void_lookup_B', 'geometry.json')))
    sky_c = vb(*geo_void['ellipses']['skylight']['centre'])

    # ============================================================ 00 paper
    g = B.group('00 · Paper', label='gray')
    B.px(g, 'Paper · warm linen ground', C.load('assets/mat/paper_linen_A3.png', 'RGB'), 0, 0, locked=True)

    # ============================================================ 10 outside
    g = B.group('10 · Outside — the street at blue hour', label='blue')
    a, x, y = local(fac_rect)
    B.shadow(g, 'Shadow · entrance facade on the page', a, x, y, depth=16, opacity=0.30)
    st = C.resize(C.load('assets/outside/street_dusk.png', 'RGB'), STREET_S)
    B.photo(g, 'Outside · street at blue hour (photo)', st, GB_X - STREET_CROP[0], GB_Y - STREET_CROP[1],
            mask_alpha=glazing, margin=220)
    del st
    B.fill(g, 'Grade · lift the shadows', '#4A5578', None, blend='screen', opacity=0.45, clip=True)
    yy = np.arange(H, dtype=np.float32)[:, None]
    wet = (smoothstep(1900, 2500, yy) * np.ones((1, W), np.float32)) * glazing
    B.fill(g, 'Grade · warm wet street', PAL['honey'], wet, blend='soft light', opacity=0.5, clip=True)
    del wet

    # ============================================================ 20 entrance facade
    g = B.group('20 · Entrance — glass block & door', label='blue')
    fb = facade_blocks()
    blocks_mask = fac_rect * (1 - glazing)
    B.photo(g, 'Facade · glass blocks, street refracted', fb, GB_X, GB_Y, mask_alpha=blocks_mask, margin=60)
    del fb
    B.fill(g, 'Grade · glass sheen (celadon)', PAL['glass'], None, blend='screen', opacity=0.18, clip=True)
    B.fill(g, 'Grade · desaturate outside the void', '#808080', np.clip(fac_rect - circle, 0, 1),
           blend='saturation', opacity=0.85, clip=True)
    # clear glazing: reflection sheen + rain on the glass
    gx0, gx1 = int(DOOR_X0), int(SIDE_X1)
    gy0, gy1 = int(FAC_Y0), int(FAC_Y1)
    gw, gh = gx1 - gx0, gy1 - gy0
    yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32)
    sheen = np.clip(1 - np.abs((xx * 0.62 + yy * 0.38) - gw * 0.58) / (gw * 0.10), 0, 1) ** 2 * 0.5
    sheen += np.clip(1 - np.abs((xx * 0.62 + yy * 0.38) - gw * 0.80) / (gw * 0.035), 0, 1) ** 2 * 0.35
    B.px(g, 'Glazing · reflection on the glass', colour_rgba(sheen, LINEN), gx0, gy0, blend='screen',
         opacity=0.22)
    del sheen, yy, xx
    rain = C.cover(rain_beads(), gw, gh, (0.4, 0.3))
    B.px(g, 'Glazing · rain beads on the glass', rain, gx0, gy0, opacity=0.8)
    del rain
    # steel frame: jambs, door / sidelight mullion, transom, door stiles + kick rail
    fr = np.zeros((H, W), np.float32)
    def bar_(x0_, y0_, x1_, y1_):
        np.maximum(fr, box_alpha(x0_, y0_, x1_, y1_), out=fr)
    fw = 18
    bar_(DOOR_X0 - fw / 2, FAC_Y0, DOOR_X0 + fw / 2, FAC_Y1)
    bar_(DOOR_X1 - fw / 2, FAC_Y0, DOOR_X1 + fw / 2, FAC_Y1)
    bar_(SIDE_X1 - fw / 2, FAC_Y0, SIDE_X1 + fw / 2, FAC_Y1)
    bar_(DOOR_X0, TRANSOM_Y - fw / 2, SIDE_X1, TRANSOM_Y + fw / 2)
    bar_(DOOR_X0 + fw / 2, TRANSOM_Y, DOOR_X0 + fw / 2 + 26, FAC_Y1)            # door stiles
    bar_(DOOR_X1 - fw / 2 - 26, TRANSOM_Y, DOOR_X1 - fw / 2, FAC_Y1)
    bar_(DOOR_X0, FAC_Y1 - 70, DOOR_X1, FAC_Y1)                                  # kick rail
    bar_(DOOR_X1, FAC_Y1 - 24, SIDE_X1, FAC_Y1)                                  # sidelight sill
    a, x, y = local(fr)
    del fr
    B.shadow(g, 'Shadow · door frame on the glass', a, x, y, depth=6, sigma=5, opacity=0.35)
    frame = colour_rgba(a, STEEL_DARK)
    hl = np.clip(a - np.roll(np.roll(a, 2, 0), 2, 1), 0, 1)                      # lit upper-left edges
    frame[..., :3] = frame[..., :3] + hl[..., None] * 0.22
    B.px(g, 'Door · anodised steel frame', frame, x, y)
    # pull handle: brushed steel bar on two stand-offs, on the lock stile
    hx, hy0, hy1 = DOOR_X1 - 92, 1965, 2385
    hw = 16
    hcov = np.zeros((hy1 - hy0 + 60, 70), np.float32)
    hcov[30:-30, 27:27 + hw] = 1
    hcov[44:56, 22:48] = 1
    hcov[-56:-44, 22:48] = 1
    hcov = C.blur(hcov, 0.6)
    hrgb = np.ones(hcov.shape + (3,), np.float32) * rgb01('#9AA0A4')
    grad = np.linspace(1.35, 0.62, hw, dtype=np.float32)
    hrgb[30:-30, 27:27 + hw] *= grad[None, :, None]
    hx0, hy0_ = hx - 27 - hw // 2, hy0 - 30
    B.shadow(g, 'Shadow · pull handle', hcov, hx0, hy0_, depth=8, sigma=4, opacity=0.5)
    B.px(g, 'Door · pull handle (brushed steel)', np.dstack([np.clip(hrgb, 0, 1), hcov]), hx0, hy0_)

    # ============================================================ 30 the bar, behind us
    g = B.group('30 · Behind you — the bar (elevation 01)', label='orange')
    bar_all = np.clip(bar_plane + box_alpha(CTR_X0 - 10, CTR_Y - 26, BAR_X1, FLOOR_Y), 0, 1)
    a, x, y = local(bar_all)
    B.shadow(g, 'Shadow · bar planes on the page', a, x, y, depth=20, opacity=0.34)
    # fluted oak bulkhead with the sign panel (elevation 01 sign band)
    bw_, bh_ = BAR_X1 - BAR_X0, BULK_Y1 - BULK_Y0
    oak = C.texture_fill(C.load('assets/mat/oak_fluted.png', 'RGB'), bh_ + 40, bw_ + 40, scale=0.44)
    B.photo(g, 'Bar · fluted oak bulkhead (sign band)', oak, BAR_X0 - 20, BULK_Y0 - 20,
            mask_alpha=box_alpha(BAR_X0, BULK_Y0, BAR_X1, BULK_Y1), margin=20)
    del oak
    sy = np.arange(H, dtype=np.float32)[:, None]
    shade = (smoothstep(BULK_Y0, BULK_Y1, sy) * np.ones((1, W), np.float32)) * box_alpha(BAR_X0, BULK_Y0, BAR_X1, BULK_Y1)
    B.fill(g, 'Shade · bulkhead, darker at the soffit', '#6B4A2E', shade, blend='multiply', opacity=0.35,
           clip=True)
    del shade
    scx_, scy_ = el(990, 655)
    B.text(g, 'RESTAURANT', 'mono', 32, scx_, scy_, anchor='origin', align='center', tracking=200, color=LINEN,
           opacity=0.35, name='TXT · bar sign RESTAURANT (elev. 01)')
    # glass-brick back wall (proposed in place of the decorative brick)
    # the wall runs down to the floor (its photographed sill) where the counter does not hide it
    ww_, wh_ = BAR_X1 - BAR_X0, FLOOR_Y - BULK_Y1
    gba = C.load('assets/gen/glassblock_wall_A.png', 'RGB')[1195:3330]       # rows below the refracted pendants
    gba = C.cover(gba, ww_ + 160, wh_ + 160, (0.30, 0.85))
    B.photo(g, 'Bar · glass-brick back wall (photo)', gba, BAR_X0 - 80, BULK_Y1 - 80,
            mask_alpha=box_alpha(BAR_X0, BULK_Y1, BAR_X1, FLOOR_Y), margin=80)
    del gba
    B.fill(g, 'Grade · warm amber bar light', PAL['amber'], None, blend='soft light', opacity=0.55, clip=True)
    B.shadow(g, 'Shadow · bulkhead soffit on the wall', np.ones((14, bw_), np.float32), BAR_X0, BULK_Y1,
             depth=10, sigma=10, opacity=0.45)
    # the bulkhead's underside, seen from below and lit by the pendants (it projects towards us)
    sof = C.poly_mask([(BAR_X0, BULK_Y1 - 1), (BAR_X1, BULK_Y1 - 1), (BAR_X1 - 10, BULK_Y1 + 22),
                       (BAR_X0 + 10, BULK_Y1 + 22)])
    sa, sx, sy = local(sof)
    srgb = colour_rgba(sa, '#C99A68')
    srgb[..., :3] *= np.linspace(1.12, 0.86, sa.shape[0], dtype=np.float32)[:, None, None]
    B.px(g, 'Bar · bulkhead underside (warm lit)', np.clip(srgb, 0, 1), sx, sy)
    # four dome pendants hanging from the soffit (cord hidden above it)
    pinfo = [cut_info('pendant_valance_L.png'), cut_info('pendant_valance_R.png')]
    pend_bulbs = []
    for i, px_ in enumerate(PEND_X):
        info = pinfo[i % 2]
        nm = 'pendant_valance_L.png' if i % 2 == 0 else 'pendant_valance_R.png'
        shade_top = BULK_Y1 + 46
        cx_ = info['shade_axis_x'] * PEND_S
        y_ = shade_top - info['shade_top_y'] * PEND_S
        x_ = px_ - cx_
        cut_row = int((BULK_Y1 + 4 - y_) / PEND_S)

        def trim(al, r=cut_row):
            al = al.copy()
            al[:max(0, r)] = 0
            return al
        lay, (lx, ly, lw, lh) = B.cutout(g, f'Bar · dome pendant {i + 1} (photo cut-out)', nm, PEND_S, x_, y_,
                                         margin=30, alpha_fn=trim)
        b = info['bulb']
        pend_bulbs.append((x_ + b['cx'] * PEND_S, y_ + b['cy'] * PEND_S))
    # counter: fluted oak front + brushed steel top (top face, edge, specular line)
    cw_ = CTR_X1 - CTR_X0
    ch_ = FLOOR_Y - CTR_Y
    front = C.texture_fill(C.load('assets/mat/oak_fluted.png', 'RGB'), ch_ + 40, cw_ + 40, scale=0.5)
    B.photo(g, 'Bar · fluted oak counter front', front, CTR_X0 - 20, CTR_Y - 20,
            mask_alpha=box_alpha(CTR_X0, CTR_Y + 12, CTR_X1, FLOOR_Y), margin=20)
    del front
    shade = (smoothstep(CTR_Y, FLOOR_Y + 60, sy) * np.ones((1, W), np.float32)) * box_alpha(CTR_X0, CTR_Y, CTR_X1, FLOOR_Y)
    B.fill(g, 'Shade · counter front, under the top', '#4A3020', shade, blend='multiply', opacity=0.30, clip=True)
    B.fill(g, 'Grade · lift the oak', LINEN, None, blend='screen', opacity=0.22, clip=True)
    del shade
    B.shadow(g, 'Shadow · counter top overhang', np.ones((12, cw_), np.float32), CTR_X0, CTR_Y + 12, depth=8,
             sigma=7, opacity=0.5)
    top_h, edge_h = 40, 18
    steel = C.texture_fill(C.load('assets/mat/steel_brushed.png', 'RGB'), top_h + edge_h + 20, cw_ + 60, scale=0.6)
    tq = C.poly_mask([(CTR_X0 + 14, CTR_Y - top_h), (CTR_X1 - 8, CTR_Y - top_h), (CTR_X1 + 12, CTR_Y),
                      (CTR_X0 - 10, CTR_Y)])
    eq = box_alpha(CTR_X0 - 10, CTR_Y, CTR_X1 + 12, CTR_Y + edge_h)
    B.photo(g, 'Bar · brushed steel counter top', steel, CTR_X0 - 30, CTR_Y - top_h - 10,
            mask_alpha=np.clip(tq + eq, 0, 1), margin=10)
    del steel
    B.fill(g, 'Shade · steel edge in shade', '#5E6670', eq, blend='multiply', opacity=0.45, clip=True)
    B.fill(g, 'Shade · far edge of the top recedes', '#5E6670',
           (1 - smoothstep(CTR_Y - top_h, CTR_Y - 4, yy_canvas())) * tq, blend='multiply', opacity=0.30, clip=True)
    spec = box_alpha(CTR_X0 - 8, CTR_Y - 1, CTR_X1 + 10, CTR_Y + 1.6)
    B.fill(g, 'Light · specular line on the steel arris', '#FFFFFF', spec, blend='screen', opacity=0.85)
    del tq, eq, spec
    # espresso on the counter (CC0 photo, non-destructive cut-out), seated with a contact shadow
    ci = cut_info('espresso_cc0.png')
    cs_ = 0.56
    sx_, sy_, srx, sry = ci['saucer_ellipse']
    cup_x = 668 - sx_ * cs_
    cup_y = CTR_Y - top_h * 0.45 - (sy_ + sry * 0.92) * cs_
    ca = np.zeros((int(sry * cs_ * 0.5) + 30, int(srx * 2 * cs_) + 40), np.float32)
    cv2.ellipse(ca, (ca.shape[1] // 2, 15), (int(srx * cs_ * 0.95), int(sry * cs_ * 0.18)), 0, 0, 360, 1.0, -1,
                cv2.LINE_AA)
    B.shadow(g, 'Shadow · cup contact on the steel', ca, cup_x + sx_ * cs_ - ca.shape[1] / 2,
             cup_y + (sy_ + sry * 0.9) * cs_ - 15, depth=4, sigma=4, opacity=0.55)
    lay, (cux, cuy, cuw, cuh) = B.cutout(g, 'Bar · espresso cup (CC0 photo cut-out)', 'espresso_cc0.png',
                                         cs_, cup_x, cup_y, margin=12)
    sm = np.zeros((cuh, cuw), np.float32)
    cv2.ellipse(sm, (int(sx_ * cs_), int(sy_ * cs_)), (int(srx * cs_ + 4), int(sry * cs_ + 4)), 0, 0, 360, 1.0, -1,
                cv2.LINE_AA)
    rx_, ry_, rrx, rry = ci['cup_rim_ellipse']
    cv2.ellipse(sm, (int(rx_ * cs_), int(ry_ * cs_)), (int(rrx * cs_ + 2), int(rry * cs_ + 2)), 0, 0, 360, 0.0,
                -1, cv2.LINE_AA)
    B.fill_local(g, 'Grade · saucer desaturated', '#808080', C.blur(sm, 2), cux, cuy, blend='saturation',
                 opacity=0.35, clip=True)
    cup_steam = (cux + rx_ * cs_, cuy + ry_ * cs_)
    # two bar stools in front of the counter: silhouettes traced from elevation 01
    ev_a = C.load('assets/lines/elev01_bar.png')[..., 3]
    sx0_, sy0_ = 763 - 110, 1640
    sb = (ev_a[sy0_:2060, sx0_:sx0_ + 220] > 0.3).astype(np.uint8)
    del ev_a
    from scipy import ndimage
    sil = ndimage.binary_fill_holes(cv2.morphologyEx(sb, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)))
    sil = C.resize(C.blur(sil.astype(np.float32), 0.6), EL_K)
    for k, scx in enumerate((355, 763)):
        ox_, oy_ = el(scx - 110, sy0_)
        foot = np.zeros((40, sil.shape[1] + 60), np.float32)
        cv2.ellipse(foot, (foot.shape[1] // 2, 20), (int(sil.shape[1] * 0.42), 9), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        B.shadow(g, f'Shadow · stool {k + 1} on the floor', foot, ox_ - 30, FLOOR_Y - 20, depth=6, sigma=8,
                 opacity=0.45)
        B.fill_local(g, f'Bar · stool {k + 1} silhouette (elevation 01)', INK, sil, ox_, oy_, opacity=0.78)

    # ============================================================ 40 ground
    g = B.group('40 · Ground — terrazzo floor', label='orange')
    floor = C.blur(C.poly_mask(FLOOR_POLY), FLOOR_FEATHER / 2.5)
    floor[:FLOOR_Y] = 0
    floor = floor * smoothstep(FLOOR_Y - 1, FLOOR_Y + 3, yy_canvas())
    floor[:, LEGEND_X - 6:] = 0
    fa, fx, fy = local(floor)
    mos = terrazzo_mosaic()
    tz, tx0, ty0 = C.warp_quad(mos, FLOOR_WARP)
    del mos
    B.photo(g, 'Floor · cream terrazzo (perspective)', tz, tx0, ty0, mask_alpha=floor, margin=60)
    del tz
    B.fill(g, 'Grade · terrazzo softened', '#808080', None, blend='saturation', opacity=0.85, clip=True)
    depth_fade = (1 - smoothstep(FLOOR_Y, FLOOR_Y + 420, yy_canvas())) * floor
    B.fill(g, 'Grade · floor recedes into shade', '#6E6458', depth_fade, blend='multiply', opacity=0.35, clip=True)
    del depth_fade
    dap = S.dapple(size=(fa.shape[1], fa.shape[0]), at=(fx, fy), leaf_size=42, density=0.30, opacity=0.5,
                   angle=-20, edge_fade=0.12, seed=12)
    B.photo(g, 'Floor · leaf-shadow dapple', dap[0], dap[1][0], dap[1][1], mask_alpha=floor, blend='multiply',
            opacity=0.30)
    del dap
    # planter (back): far inner wall, soil, rim and face — the trunk stands in front of this
    g = B.group('45 · Planter — concrete ring & damp soil', label='green')
    back, lip, (plx, ply) = planter_parts()
    sh = np.zeros((back.shape[0], back.shape[1]), np.float32)
    cv2.ellipse(sh, (int(PL_CX - plx), int(PL_CY - ply + PL_FACE - 6)), (int(PL_RX + 10), int(PL_RY + 8)), 0, 0,
                360, 1.0, -1, cv2.LINE_AA)
    B.shadow(g, 'Shadow · planter on the terrazzo', sh, plx, ply, depth=14, sigma=14, opacity=0.5)
    B.px(g, 'Planter · concrete ring & damp soil', back, plx, ply)

    # ============================================================ 50 the void
    g = B.group('50 · The void — looking up', label='green', opened=True)
    cl, clx, cly = local(circle)
    B.shadow(g, 'Shadow · void disc', cl, clx, cly, depth=24, opacity=0.25)
    rim, pad = card_edge(cl, width=5)
    B.px(g, 'Void · paper rim', rim, clx - pad, cly - pad)
    vbs = C.resize(C.load('assets/gen/void_lookup_B.png', 'RGB'), VB_S)
    B.photo(g, 'Void · looking up (photo, disc mask)', vbs, VB_OX, VB_OY, mask_alpha=cl,
            mask_xy=(clx, cly), margin=200)
    fr_m = defringe_mask(vbs)
    B.fill_local(g, 'Retouch · defringe violet edges', '#808080', fr_m, VB_OX, VB_OY, blend='saturation',
                 opacity=0.85, clip=True)
    del fr_m
    glz = C.resize(C.load('assets/cut/geo/void_lookup_B/skylight_glazing.png', 'L'), VB_S)
    del vbs
    # --- the tree, registered on its own photograph
    gt = B.group('55 · Tree — rising through the void', label='green', parent=g, opened=True)
    ta = C.resize(C.load('assets/cut/tree_B.png')[..., 3], VB_S)
    tx_, ty_ = vb(TREE_BOX[0], TREE_BOX[1])
    outside_disc = 1 - disc(VOID_C[0], VOID_C[1], VOID_R + 2)[int(round(ty_)):int(round(ty_)) + ta.shape[0],
                                                                int(round(tx_)):int(round(tx_)) + ta.shape[1]]
    B.shadow(gt, 'Shadow · tree on the page', ta * outside_disc, round(tx_), round(ty_), depth=16,
             opacity=0.30)
    B.shadow(gt, 'Shadow · tree lifted off its photograph', ta * (1 - outside_disc), round(tx_), round(ty_), depth=8,
             sigma=7, opacity=0.18)
    B.cutout(gt, 'Tree · cut-out (registered on its photo)', 'tree_B.png', VB_S, tx_, ty_, margin=TREE_MARGIN)
    # the tree carries the same violet fringes as the photo
    tsrc = C.resize(C.load('assets/gen/void_lookup_B.png', 'RGB')[TREE_BOX[1]:TREE_BOX[3], TREE_BOX[0]:TREE_BOX[2]],
                    VB_S)
    B.fill_local(gt, 'Retouch · defringe leaf edges', '#808080', defringe_mask(tsrc) * ta[:tsrc.shape[0], :tsrc.shape[1]],
                 round(tx_), round(ty_), blend='saturation', opacity=0.85, clip=True)
    del tsrc
    ao = np.zeros((90, 200), np.float32)
    ao[:, :] = smoothstep(0, 90, np.arange(90, dtype=np.float32))[:, None] ** 1.5
    B.fill_local(gt, 'Shade · trunk base darkens into the soil', '#2E241C', ao, TRUNK_X - 100,
                 PL_CY + PL_SOIL_DROP - 110, blend='multiply', opacity=0.55, clip=True)
    # --- sky at blue hour, behind the leaves
    tav = np.zeros((H, W), np.float32)
    iy, ix = int(round(ty_)), int(round(tx_))
    hh_, ww_ = ta.shape
    tav[iy:iy + hh_, ix:ix + ww_] = ta[:min(hh_, H - iy), :min(ww_, W - ix)]
    sky = np.zeros((H, W), np.float32)
    gh_, gw_ = glz.shape
    sky[VB_OY:VB_OY + gh_, VB_OX:VB_OX + gw_] = glz[:H - VB_OY, :W - VB_OX]
    sky_m = sky.copy()
    sky = sky * (1 - tav) * circle
    del glz, ta
    B.fill(g, 'Sky · blue hour (multiply)', PAL['dusk'], sky, blend='multiply', opacity=0.55)
    B.fill(g, 'Sky · blue hour (colour)', PAL['dusk'], sky, blend='color', opacity=0.55)
    sb = C.bbox(sky)
    rb = C.cover(rain_beads(), sb[2] - sb[0], sb[3] - sb[1], (0.6, 0.6))
    B.photo(g, 'Sky · rain beads on the skylight', rb, sb[0], sb[1], mask_alpha=sky, blend='screen', opacity=0.6)
    del sky, rb
    # --- twigs reaching out of the void (same tree, a step nearer), above the blue-hour sky
    gtw = B.group('57 · Tree — twigs breaking out', label='green', parent=g, opened=True)
    twig_alpha = np.zeros((H, W), np.float32)
    for side, box_, ang, anc, target in TWIGS:
        rgb_, al_, q = leaf_piece(box_, TWIG_S, ang, anchor=anc, feather=90)
        px0, py0 = int(round(target[0] - q[0])), int(round(target[1] - q[1]))
        hh_, ww_ = al_.shape
        off = 1 - circle[max(0, py0):py0 + hh_, max(0, px0):px0 + ww_]
        sh_ = np.zeros_like(al_)
        sh_[max(0, -py0):max(0, -py0) + off.shape[0], max(0, -px0):max(0, -px0) + off.shape[1]] = off
        B.shadow(gtw, f'Shadow · twig breaking out ({side})', al_ * sh_, px0, py0, depth=14, opacity=0.30)
        B.photo(gtw, f'Tree · twig breaking out ({side})', rgb_, px0, py0, mask_alpha=al_,
                mask_xy=(px0, py0))
        hh_, ww_ = al_.shape
        sub = twig_alpha[max(0, py0):py0 + hh_, max(0, px0):px0 + ww_]
        np.maximum(sub, al_[max(0, -py0):max(0, -py0) + sub.shape[0], max(0, -px0):max(0, -px0) + sub.shape[1]],
                   out=sub)
    tree_m = np.maximum(tav, twig_alpha)
    del tav

    # ============================================================ 60 planter front
    g = B.group('60 · Planter — soil lip around the trunk', label='green')
    cs = np.zeros(lip.shape[:2], np.float32)
    cv2.ellipse(cs, (int(TRUNK_X - plx + 6), int(PL_CY - ply + PL_SOIL_DROP - 22)), (82, 16), 0, 0, 360, 1.0, -1,
                cv2.LINE_AA)
    B.px(g, 'Planter · soil swallowing the trunk base', lip, plx, ply)
    B.shadow(g, 'Shadow · trunk contact on the soil', cs, plx, ply, depth=2, sigma=5, opacity=0.55)
    del back, lip

    # ============================================================ 70 ceiling: festoon valance
    g = B.group('70 · Overhead — the festoon valance', label='orange')
    v, m, (vsx, vsy), patches = valance_parts()
    vx, vy = (vsx - VAL_SX0) * VAL_S, (vsy - VAL_SY0) * VAL_S
    vs = C.resize(v, VAL_S)
    ms = C.resize(m, VAL_S)
    del v, m
    B.shadow(g, 'Shadow · valance hem on the page', ms, vx, vy, depth=26, opacity=0.36)
    B.photo(g, 'Valance · swags (photo, fabric mask)', vs, vx, vy, mask_alpha=ms, mask_xy=(vx, vy))
    for k, (patch, px0, py0) in enumerate(patches):
        ps = C.resize(patch, VAL_S)
        B.px(g, f'Retouch · pendant cord {k + 1} removed (heal)', ps, (px0 - VAL_SX0) * VAL_S,
             (py0 - VAL_SY0) * VAL_S, clip=True)
    B.fill(g, 'Grade · desaturate', '#8C8C8C', None, blend='saturation', opacity=0.42, clip=True)
    B.fill(g, 'Grade · to palette linen (colour)', LINEN, None, blend='color', opacity=0.45, clip=True)
    B.fill(g, 'Grade · lift', LINEN, None, blend='screen', opacity=0.16, clip=True)
    del vs, ms

    # ============================================================ 75 near leaves
    g = B.group('75 · Near — leaves overhead', label='green')
    for side, box_, ang, flip, anc, target in (
            ('top left', (0, 1100, 720, 1700), -38.0, True, (720, 300), (-90, -60)),
            ('top right', (1700, 1100, 2287, 1640), 38.0, True, (0, 270), (W + 90, -60))):
        rgb_, al_, q = leaf_piece(box_, 1.5, ang, flip, blur=7.0, anchor=anc)
        px0, py0 = int(round(target[0] - q[0])), int(round(target[1] - q[1]))
        al_ = al_ * np.clip((NEAR_MAX_Y - (np.arange(al_.shape[0])[:, None] + py0)) / 120.0, 0, 1)
        B.shadow(g, f'Shadow · near leaves ({side})', al_, px0, py0, depth=70, sigma=45, opacity=0.20)
        B.photo(g, f'Near · leaves overhead ({side})', rgb_, px0, py0, mask_alpha=al_,
                mask_xy=(px0, py0))
        B.fill(g, f'Grade · backlit, in shade ({side})', '#3E4A30', None, blend='multiply', opacity=0.62, clip=True)

    # ============================================================ 80 light & colour intensity
    g = B.group('80 · Light & colour intensity', label='yellow', opened=True)
    skx, sky_y = sky_c
    B.gen(g, 'Light · last blue light down the void',
          S.light_beam(apex=(skx + 20, sky_y - 60), angle=-90, length=PL_CY - sky_y + 120, spread=3.5, aperture=560,
                       color=PAL['glass'], intensity=0.42, core=0.3, rays=0.25, dust=170, dust_color='#F4F7F2',
                       seed=21), blend='screen', opacity=0.6)
    for i, (bx, by) in enumerate(pend_bulbs):
        B.gen(g, f'Light · pendant {i + 1} glow (amber)', S.glow(at=(bx, by + 4), radius=330, color=PAL['amber'],
                                                                 intensity=0.8, hot_color='#FFE9C4', ratio=0.85),
              blend='screen', opacity=0.85)
    for i, (bx, by) in enumerate(pend_bulbs):
        B.gen(g, f'Light · pool on the counter {i + 1}', S.glow(at=(bx, CTR_Y - 14), radius=230, color=PAL['honey'],
                                                               intensity=0.75, ratio=0.30), blend='screen',
              opacity=0.8)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

    def blob(cx, cy, rx, ry, k=1.5):
        return np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) * k)

    core = blob(2262, 1320, 780, 760, 1.25) * np.clip(circle + twig_alpha, 0, 1)
    B.fill(g, 'Intensity · green-gold core (soft light)', GREEN_GOLD, core, blend='soft light', opacity=0.85)
    B.fill(g, 'Intensity · green-gold core (saturation)', '#9ED22E', core * np.clip(tree_m * 1.3, 0, 1),
           blend='saturation', opacity=0.30)
    B.gen(g, 'Light · canopy glow', S.glow(at=(2262, 1300), radius=980, color=GREEN_GOLD, intensity=0.5, ratio=0.95),
          blend='screen', opacity=0.40)
    lens_fac = circle * fac_rect * (1 - sky_m) * (1 - tree_m)
    B.fill(g, 'Intensity · void x street (violet)', PAL['violet'], lens_fac, blend='overlay',
           opacity=0.72)
    lens_bar = circle * bar_plane * (1 - tree_m)
    B.fill(g, 'Intensity · void x bar (honey)', PAL['honey'], lens_bar, blend='overlay',
           opacity=0.60)
    del lens_fac, lens_bar, sky_m
    B.fill(g, 'Intensity · amber warmth at the bar', PAL['amber'], blob(700, 2250, 820, 620, 1.3) * (1 - circle),
           blend='soft light', opacity=0.45)
    B.fill(g, 'Intensity · terracotta to the cabins', PAL['terracotta'],
           blob(-80, 2150, 420, 900, 1.2), blend='soft light', opacity=0.55)
    del xx, yy, core, tree_m

    # ============================================================ 85 senses
    g = B.group('85 · Senses — sound & smell', label='red', opened=True)
    # SOUND 01: voices rise and echo in the void — three calm rings centred on the skylight
    rings = None
    for k, (r, wd, al) in enumerate(((300, 3.2, 0.85), (510, 2.8, 0.62), (730, 2.4, 0.42))):
        rg, (rx0, ry0) = S.sound_rings(at=(skx, sky_y), r_max=r, r_min=r, n=1, width=wd, color=PAL['honey'],
                                       alpha=al, decay=1.0, wobble=0.0, seed=k)
        if rings is None:
            rings = np.zeros((H, W, 4), np.float32)
        hh_, ww_ = rg.shape[:2]
        sub = rings[max(0, ry0):ry0 + hh_, max(0, rx0):rx0 + ww_]
        src = rg[max(0, -ry0):max(0, -ry0) + sub.shape[0], max(0, -rx0):max(0, -rx0) + sub.shape[1]]
        a_ = src[..., 3:4]
        sub[..., :3] = src[..., :3] * a_ + sub[..., :3] * (1 - a_)
        sub[..., 3:4] = a_ + sub[..., 3:4] * (1 - a_)
    B.photo(g, 'Sound · voices rise up the void', rings, 0, 0,
            mask_alpha=disc(VOID_C[0], VOID_C[1], VOID_R - 8, feather=6), blend='multiply', opacity=0.75)
    del rings
    # SOUND 02: espresso hiss and a clink, fading arcs from the machine towards the void
    mx_, my_ = el(1365, 1440)
    B.gen(g, 'Sound · espresso hiss, fading arcs', S.sound_rings(at=(mx_, my_), r_max=300, r_min=70, n=4,
                                                                 arc=(-35, 70), width=2.2, color=PAL['ember'],
                                                                 alpha=0.85, decay=0.68, thin=0.92, spacing=1.15,
                                                                 end_fade=18, seed=7), opacity=0.85)
    # rain outside: short slanted dashes in the clear glazing
    rd = rain_dashes(gw, gh, 520, 9)
    B.photo(g, 'Sound · rain, slanted dashes', colour_rgba(rd, PAL['glass']), gx0, gy0,
            mask_alpha=glazing, blend='screen', opacity=0.85)
    del rd
    # SMELL
    B.gen(g, 'Smell · roasted coffee from the cup',
          S.wisp(at=(cup_steam[0], cup_steam[1] - 6), height=760, ribbons=3, width=86, color=PAL['honey'],
                 color_top=LINEN, opacity=1.0, lean=0.42, seed=31), blend='screen')
    B.gen(g, 'Smell · green leaf & damp soil',
          S.wisp(at=(TRUNK_X + 300, PL_CY + 40), height=640, ribbons=2, width=58, color=PAL['oat'],
                 color_top=LINEN, opacity=0.9, lean=-0.18, seed=33), opacity=0.45)
    B.gen(g, 'Smell · petrichor at the door',
          S.wisp(at=(DOOR_X0 + 420, FLOOR_Y - 30), height=560, ribbons=2, width=54, color=PAL['celadon'],
                 color_top=PAL['glass'], opacity=0.7, lean=-0.45, seed=35), blend='screen', opacity=0.45)

    # ============================================================ 90 drawings
    g = B.group('90 · Drawings — client linework', label='violet')
    # (a) the stair, from section B-B, registered on the trunk axis and the floor line
    sec = C.load('assets/lines/section_BB_right.png')
    kb = 0.52
    thick = cv2.morphologyEx((sec[..., 3] > 0.35).astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    sec[..., 3] *= 1 - cv2.dilate(thick, np.ones((5, 5), np.uint8)).astype(np.float32)   # lines only: no poché
    secs = C.resize(LW.thicken(sec, 0.45 / kb), kb)
    del sec, thick
    bx0_, by0_ = TRUNK_X - 3168.1 * kb, FLOOR_Y - 4226.5 * kb
    tri = [(bx0_ + x_ * kb, by0_ + y_ * kb) for x_, y_ in ((4040, 4250), (6060, 3070), (6060, 2380), (4420, 1440))]
    keep = C.poly_mask(tri) * np.clip(box_alpha(FAC_X0 + 6, FAC_Y0 + 6, DOOR_X0 - 16, FLOOR_Y - 2)
                                      - disc(VOID_C[0], VOID_C[1], VOID_R + 24), 0, 1)
    keep = C.blur(keep, 5) * keep
    B.photo(g, 'Drawing · stair, section B-B (ghost)', LW.recolor(secs, LINEN), bx0_, by0_,
            mask_alpha=keep, opacity=0.62, locked=True)
    del secs, keep
    # (b) elevation 01: bulkhead sign, counter-top machines and stools, ghosted on the bar
    ev = C.load('assets/lines/elev01_bar.png')
    evs = C.resize(LW.thicken(ev, 0.4 / EL_K), EL_K)
    del ev
    ex0, ey0 = EL_X0, EL_Y0
    nodisc = 1 - disc(VOID_C[0], VOID_C[1], VOID_R + 30, feather=8)
    lx0_, ly0_ = el(560, 500)
    lx1_, ly1_ = el(1420, 700)
    keep = np.clip(box_alpha(el(430, 0)[0], BULK_Y0 - 4, el(1575, 0)[0], BULK_Y1 - 30)
                   - box_alpha(lx0_, ly0_, lx1_, ly1_), 0, 1) * nodisc
    B.photo(g, 'Drawing · elev. 01 sign band (ghost)', LW.recolor(evs, LINEN), ex0, ey0, mask_alpha=keep,
            opacity=0.30, locked=True)
    keep = box_alpha(BAR_X0 - 4, el(0, 1380)[1], el(1500, 0)[0], FLOOR_Y + 4) * nodisc   # stools 1-3
    B.photo(g, 'Drawing · elev. 01 stools (ghost)', evs, ex0, ey0, mask_alpha=keep,
            blend='multiply', opacity=0.45, locked=True)
    del evs, keep, nodisc

    # ============================================================ 94 viewpoint
    g = B.group('94 · Viewpoint — where we stand & look')
    vx_, vy_ = VIEWER
    out_end = (DOOR_X0 + 300, 2140)
    up_end = (vx_ - 70, 790)
    for nm, end in (('out', out_end), ('up', up_end)):
        pts = [(vx_, vy_), end]
        casing = S.arrow(pts, width=6.0, color=LINEN, head='open', head_len=40, dash=(20.0, 12.0), smooth=False)
        line = S.arrow(pts, width=2.6, color=INK, head='open', head_len=38, dash=(20.0, 12.0), smooth=False)
        B.gen(g, f'Sightline · casing ({nm})', casing, opacity=0.7)
        B.gen(g, f'Sightline · looking {nm} (dashed ink)', line)
    gx_, gy_ = int(vx_) - 48, int(vy_) - 48
    yy, xx = np.mgrid[0:96, 0:96].astype(np.float32)
    rr = np.hypot(xx + 0.5 - (vx_ - gx_), yy + 0.5 - (vy_ - gy_))
    halo = np.clip(36.5 - rr, 0, 1)
    glyph = np.maximum(np.clip(1.3 - np.abs(rr - 23), 0, 1), np.clip(9.5 - rr, 0, 1))
    B.px(g, 'Viewer · paper halo', colour_rgba(halo, LINEN), gx_, gy_, opacity=0.85)
    B.px(g, 'Viewer · you stand here (eye point)', colour_rgba(glyph, INK), gx_, gy_)

    # ============================================================ 96 legend & key plan
    B.legend(B.doc.root, '01', [('colour', 'amber', 'AMBER'), ('colour', GREEN_GOLD, 'GREEN-GOLD'),
                                ('colour', 'violet', 'VIOLET'), ('colour', 'dusk', 'DUSK'),
                                ('mat', 'steel_brushed', 'STEEL'), ('mat', 'linen_plain', 'LINEN'),
                                ('mat', 'terrazzo_cream', 'TERRAZZO'), ('mat', 'glassblock', 'GLASS BLOCK')])

    # ============================================================ 98 type
    g = B.group('98 · Type — title & annotations', opened=True)
    B.title_block(g, 'RESTAURANT  ·  ATMOSPHERE STUDY  ·  01 / 02', ['From the void,', 'looking out'],
                  'STANDING BENEATH THE TREE  ·  LOOKING OUT TO THE STREET')
    ROW1 = 760
    # left column, on paper above the bar
    col_phr = 'amber within → green-gold core\n→ blue hour beyond'
    box = B.tag(g, 'COLOUR', col_phr, MARGIN, ROW1)
    stops = [PAL['amber'], GREEN_GOLD, PAL['violet'], PAL['dusk']]
    bw_ = box[2] - box[0]
    tt = np.linspace(0, len(stops) - 1, bw_)
    i0 = np.clip(np.floor(tt).astype(int), 0, len(stops) - 2)
    f = (tt - i0)[:, None]
    cols = np.stack([rgb01(c) for c in stops])
    strip = np.ones((22, bw_, 4), np.float32)
    strip[..., :3] = (cols[i0] * (1 - f) + cols[i0 + 1] * f)[None]
    B.px(g, 'Colour · intensity scale (gradient)', strip, box[0], box[3])
    bar_entries = [('SOUND · 02', 'the hiss of the espresso machine, a clink of glass'),
                   ('SMELL · 01', 'roasted coffee, warm and bitter'),
                   ('TASTE', 'espresso, burnt sugar, a twist of orange')]
    card_y = box[3] + 22 + 64
    B.card(g, 'At the bar', bar_entries, MARGIN, card_y)
    cap_y = BULK_Y0 - 30
    B.text(g, '←  TO THE CABINS (02)', 'mono', LABEL, MARGIN, cap_y - 46, tracking=110, color=PAL['terracotta'],
           name='TXT · pointer to the cabins (02)')
    B.text(g, 'BEHIND YOU  ·  THE BAR', 'mono', LABEL, MARGIN + 470, cap_y - 46, tracking=110,
           name='TXT · behind you, the bar')
    B.text(g, 'GLASS BRICK PROPOSED IN PLACE OF DECORATIVE BRICK', 'mono-light', LABEL, MARGIN, cap_y,
           tracking=90, name='TXT · note, glass brick proposal')
    # right column, on paper above the entrance
    hh = tag_size('SOUND · 01', 'voices from both floors\nrise and soften in the void', hero=True)[1]
    hx0 = 3420
    hbox = B.tag(g, 'SOUND · 01', 'voices from both floors\nrise and soften in the void', hx0, ROW1, hero=True)
    B.leader(g, 'Leader · sound 01 to the rings', [(hbox[0] + 40, hbox[3]), (skx + 730 * 0.866, sky_y + 730 * 0.5)],
             width=2.0, dot_at_end=True, opacity=0.85)
    lw_ = tag_size('LIGHT', 'the last blue light falls down the void;\nthe pendants answer in amber')[0]
    B.tag(g, 'LIGHT', 'the last blue light falls down the void;\nthe pendants answer in amber', W - MARGIN - lw_,
          ROW1)
    B.text(g, 'ENTRANCE  ·  GLAZED END', 'mono', LABEL, DOOR_X0, FAC_Y0 - 34, tracking=110,
           name='TXT · entrance, glazed end')
    # the view out, inside the glass
    ob = B.tag(g, 'OUTSIDE · BLUE HOUR', 'rain on the street,\nsoftened by glass block', DOOR_X0 + 54, TRANSOM_Y + 70)
    B.leader(g, 'Leader · outside to the rain', [(ob[0] + 96, ob[3]), (ob[0] + 120, ob[3] + 190)],
             width=2.0, color=LINEN, dot_at_end=True, opacity=0.85)
    # materials beside COLOUR on the top row; the leaf-and-soil smell on the planter itself
    B.tag(g, 'TEXTURE', 'cool glass block · brushed steel rail ·\nsmooth bark · soft linen overhead', 742, ROW1)
    B.tag(g, 'SMELL · 02', 'green leaf, damp soil', 1790, 3072)
    # sightline labels at the arrival points
    chip(B, g, 'LOOKING OUT  ·  TO THE STREET', DOOR_X0 + 44, out_end[1] + 70, 'looking out')
    cw_ = chip_size('LOOKING UP  ·  TO THE SKY')[0]
    chip(B, g, 'LOOKING UP  ·  TO THE SKY', up_end[0] - cw_ / 2, up_end[1] - 96, 'looking up')
    B.readme(TITLE)
    return B


def chip_size(text, pad=(22, 16)):
    _, m = T.text_rgba(text, 'mono', LABEL, tracking=110)
    ix0, iy0, ix1, iy1 = m['ink_box']
    return int(round(ix1 - ix0 + 2 * pad[0])), int(round(iy1 - iy0 + 2 * pad[1]))


def chip(B, parent, text, x, y, short, pad=(22, 16)):
    """A small paper label (mono caps only) with its own shadow, in its own group."""
    from psdkit import Group
    g = Group(f'Tag · {short}', opened=False)
    parent.add(g)
    rgba, m = T.text_rgba(text, 'mono', LABEL, tracking=110)
    ix0, iy0, ix1, iy1 = m['ink_box']
    w, h = chip_size(text, pad)
    x, y = int(round(x)), int(round(y))
    rng = np.random.default_rng(len(text))
    paper = C.solid(h, w, '#F4EEE2')
    paper[..., :3] *= (1 + 0.012 * rng.standard_normal((h, w, 1))).astype(np.float32)
    B.shadow(g, f'Shadow · label {short}', np.ones((h, w), np.float32), x, y, depth=12, opacity=0.36)
    B.px(g, f'Paper · label {short}', np.clip(paper, 0, 1), x, y)
    ox, oy = m['anchors']['baseline_left']
    B.text(g, text, 'mono', LABEL, x + pad[0] - ix0 + ox, y + pad[1] - iy0 + oy, tracking=110,
           name=f'TXT · {short}')
    return (x, y, x + w, y + h)


# --------------------------------------------------------------------------- #
# checks & previews
# --------------------------------------------------------------------------- #

def _node_alpha(node):
    """Full-canvas effective alpha of a Pixel / Fill node (pixel alpha x layer mask)."""
    from psdkit import Pixel
    a = np.zeros((H, W), np.float32)
    if isinstance(node, Pixel):
        x0, y0, x1, y1 = node.bounds
        X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if X1 > X0 and Y1 > Y0:
            a[Y0:Y1, X0:X1] = node.rgba[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0, 3] / 255.0
    else:
        a[:] = 1.0
    if node.mask is not None:
        a *= node.mask.sample(0, 0, W, H)
    return a


def check_fills(doc, comp):
    """Toggle test: every Solid Color fill must change its effective area (its mask, intersected
    with the clipping base for clipped fills) by >= 6 levels on average."""
    from psdkit import Fill, Group
    rows = []

    def walk(group):
        base = None
        for node in group.children:
            if isinstance(node, Group):
                walk(node)
                base = None
                continue
            if not node.clip:
                base = node
            if not isinstance(node, Fill) or node.hidden:
                continue
            area = _node_alpha(node)
            if node.clip and base is not None:
                area *= _node_alpha(base)
            sel = area > 0.5
            if not sel.any():
                rows.append((node.name, 0.0, 0.0))
                continue
            ys, xs = np.nonzero(sel)
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            node.hidden = True
            alt = doc.render()
            node.hidden = False
            d = np.abs(comp[y0:y1, x0:x1] - alt[y0:y1, x0:x1]).max(-1) * 255
            del alt
            m = sel[y0:y1, x0:x1]
            rows.append((node.name, round(float(d[m].mean()), 1), round(float(d[m].max()), 1)))
            print(f'  {"OK " if rows[-1][1] >= 6 else "LOW"} {rows[-1][1]:6.1f} mean / {rows[-1][2]:5.1f} max   '
                  f'{node.name}', flush=True)

    walk(doc.root)
    return rows


ZONES = {
    'void core': (1700, 800, 2850, 1800), 'lens bar': (1130, 1618, 1600, 2450),
    'lens street': (2704, 1272, 3430, 2600), 'facade': (2704, 1272, 4961, 2880),
    'door': (3776, 1272, 4714, 2880), 'bar': (168, 1618, 1150, 2880), 'near leaves L': (0, 0, 1000, 700),
    'near leaves R': (3960, 0, 4961, 700), 'planter': (1661, 2950, 2861, 3508), 'valance': (0, 0, 4961, 600),
}


def audit(doc, comp):
    """Names <= 40 chars, no 86-99 % opacities, dark-pixel share per zone (< 5 % max channel < 25)."""
    from psdkit import Text
    for node in doc.root.iter_layers():
        if isinstance(node, Text):
            continue
        if len(node.name) > 40:
            print('  NAME > 40:', len(node.name), node.name)
        if 0.855 < node.opacity < 0.999:
            print('  OPACITY  :', node.opacity, node.name)
    u8 = np.clip(comp * 255 + 0.5, 0, 255).astype(np.uint8)
    for nm, (x0, y0, x1, y1) in ZONES.items():
        z = u8[y0:y1, x0:x1].max(-1)
        print(f'  dark {nm:14s} {100 * float((z < 25).mean()):5.2f} %   mean L {float(z.mean()):5.1f}')


CROPS = {
    'trunk_disc_bottom': (1950, 2500, 2650, 3420),
    'void_rim_right': (3150, 1250, 3700, 1950),
    'door': (3700, 1050, 4800, 2900),
    'hem_centre': (1700, 0, 3100, 900),
    'hem_left': (0, 0, 1400, 1000),
    'bar_pendants': (168, 1550, 1500, 2350),
    'bar_counter': (100, 2300, 1500, 2950),
    'planter': (1750, 3050, 2850, 3508),
    'tags_top_right': (3200, 650, 4961, 1200),
    'tags_top_left': (100, 650, 1500, 1700),
    'legend': (3250, 2950, 4961, 3508),
    'title': (100, 2900, 1700, 3508),
    'canopy_core': (1700, 700, 2900, 1700),
    'twig_left': (1000, 700, 1900, 1500),
    'twig_right': (2600, 700, 3500, 1500),
    'near_left': (0, 0, 1400, 900),
    'lens_left': (1100, 1500, 1700, 2500),
    'near_right': (3900, 0, 4961, 900),
    'floor': (1150, 2850, 3350, 3508),
    'stair': (2704, 1272, 3800, 2880),
}


def main():
    t = time.time()
    B = build()
    print('built', B.doc.layer_count(), 'layers in', round(time.time() - t, 1), 's', flush=True)
    if '--final' in sys.argv:
        from finalize import finalize
        rep = finalize(B.doc, SLUG)
        print(json.dumps(rep, indent=1))
        return
    comp = B.doc.render()
    print('rendered', round(time.time() - t, 1), 's', flush=True)
    audit(B.doc, comp)
    C.save_preview(comp, os.path.join(PREVIEW, 'c01_full_preview.jpg'), max_side=1800)
    sm = cv2.resize(comp, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
    C.save_preview(cv2.GaussianBlur(sm, (0, 0), 3), os.path.join(PREVIEW, 'c01_squint.jpg'), max_side=800)
    if '--crops' in sys.argv:
        for nm, (x0, y0, x1, y1) in CROPS.items():
            C.save_preview(comp[y0:y1, x0:x1], os.path.join(PREVIEW, f'c01_crop_{nm}.jpg'), max_side=1100)
    if '--check' in sys.argv:
        check_fills(B.doc, comp)
    print('done', round(time.time() - t, 1), 's')


if __name__ == '__main__':
    main()
