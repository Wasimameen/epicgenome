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
from scipy import ndimage

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
VOID_C = (2280, 1730)           # clear of the floor line (bottom 2810) and the swag bellies (top 650)
VOID_R = 1080
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
CTR_X0, CTR_X1 = MARGIN - 6, 1185            # counter >= 300 px clear of the void; carries the machine
PEND_X = (282, 546, 810, 1074)               # four dome pendants (elevation 01), clear of the void
PEND_S = 0.34

# festoon valance overhead (festoon_valance.png, real fabric mask)
VAL_S = 0.9
VAL_SX0, VAL_SY0 = 454, 449                  # source px at canvas (0, 0)

# the tree pit: a low terrazzo kerb (the plan's ~1.6 m ring), the floor turned up
PL_CX, PL_CY = TRUNK_X, 3170                 # centre of the kerb's top ellipse
PL_RX, PL_RY = 470, 150
PL_RIM = 40                                  # kerb width (plan)
PL_FACE = 70                                 # visible height of the kerb face (lowest point 3390)
PL_SOIL_DROP = 14
SOIL_TOP = PL_CY + PL_SOIL_DROP - 24         # where the soil meets the front of the trunk

# floor plane (visible cut) and its perspective quad (texture warp)
FLOOR_POLY = [(1300, FLOOR_Y), (3060, FLOOR_Y), (3020, H + 60), (1780, H + 60), (1290, 3100)]   # clear of the subline
LEGEND_X = 3100                              # shared legend block: keep art clear of x >= 3100, y >= 2980
FLOOR_FEATHER = 70                           # the floor's sides dissolve into the paper
FLOOR_WARP = [(1290, FLOOR_Y - 20), (3300, FLOOR_Y - 20), (3960, H + 40), (520, H + 40)]

# one branch reaching out of the void towards the street: a real branch of the same tree (tree_B px),
# whole leaflets selected inside an outline (no straight or dissolve cuts), its base slipped UNDER
# the photographed crown at a real branch, so it visibly grows out of the tree
TWIG = dict(box=(1640, 1290, 2287, 1610), base=(1652, 1556), scale=1.1, angle=34.0, target=(2450, 1290),
            outline=[(1640, 1535), (1700, 1492), (1800, 1428), (1868, 1362), (1950, 1306), (2050, 1294),
                     (2160, 1298), (2287, 1318), (2287, 1476), (2200, 1506), (2080, 1548), (1985, 1500),
                     (1880, 1458), (1760, 1545), (1690, 1600), (1640, 1600)])

NEAR_MAX_Y = 700                 # near leaves stay above the tag row

# viewer + sightlines
VIEWER = (TRUNK_X + 560, PL_CY + 120)        # on the terrazzo beside the kerb


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
    """The entrance wall: street_dusk refracted through pressed glass blocks (outside.py); each block
    carries smeared lamp light.  Returns (rgba, glass mask) — the glass mask separates the glass
    (faces + rims) from the mortar, for the blue-hour / lamplight grades."""
    p_rgb = os.path.join(CACHE, 'facade_glassblock_street_v4.png')
    p_face = os.path.join(CACHE, 'facade_glassblock_street_v4_glass.png')
    if not (os.path.exists(p_rgb) and os.path.exists(p_face)):
        from PIL import Image
        sc = street_scene()
        lum_ = C.lum(sc)[..., None]
        sc = np.clip(lum_ + (sc - lum_) * 2.2, 0, 1)        # glass concentrates the colour of the dusk
        out, masks = O.glassblock_refract(sc, GB_COLS, GB_ROWS, GB_B, GB_M, seed=31, tint='#8DB2C4',
                                          mortar='#B8BCBD', mortar_level=0.66, light='#FFC27E', light_level=0.75,
                                          scene_blur=2.5, parallax=0.6, distortion=0.9, return_masks=True)
        os.makedirs(CACHE, exist_ok=True)
        Image.fromarray(np.clip(np.floor(out * 255 + 0.5), 0, 255).astype(np.uint8), 'RGBA').save(p_rgb, compress_level=6)
        Image.fromarray(np.clip(np.floor(masks['glass'] * 255 + 0.5), 0, 255).astype(np.uint8), 'L').save(p_face, compress_level=6)
        del sc, out, masks
    return C.load(p_rgb), C.load(p_face, 'L')


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


def inpaint_fringes(rgb, thresh=0.2):
    """Violet chromatic-aberration fringes healed by inpainting (TELEA, radius 2) instead of a mere
    desaturation (which leaves dark navy outlines).  Returns (healed rgb, alpha of the healed pixels)."""
    m = (defringe_mask(rgb) > thresh).astype(np.uint8)
    m = cv2.dilate(m, np.ones((3, 3), np.uint8))
    u8 = np.clip(rgb[..., :3] * 255 + 0.5, 0, 255).astype(np.uint8)
    healed = cv2.inpaint(np.ascontiguousarray(u8), m, 2, cv2.INPAINT_TELEA).astype(np.float32) / 255
    return healed, np.clip(C.blur(m.astype(np.float32), 0.7) * 1.3, 0, 1)


def select_leaves(a, outline, box):
    """Keep whole leaflets (and the thin stems between them) inside an outline drawn through the gaps
    of the foliage: leaflets are separated by a small erosion and kept or dropped as a whole, so no leaf
    is ever cut by a straight or dissolving edge."""
    bx0, by0 = box[:2]
    h, w = a.shape
    inside = C.poly_mask([(x - bx0, y - by0) for x, y in outline], h, w)
    ell = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))  # noqa: E731
    solid = (a > 0.5).astype(np.uint8)
    core = cv2.erode(solid, ell(2))
    n, lab = cv2.connectedComponents(core, connectivity=8)
    frac = ndimage.mean(inside, lab, index=np.arange(1, n))
    kept = np.isin(lab, np.flatnonzero(np.asarray(frac) > 0.6) + 1).astype(np.uint8)
    bodies = cv2.dilate(core, ell(4)).astype(np.float32)
    keep = np.clip(cv2.dilate(kept, ell(4)).astype(np.float32) + (1 - bodies) * (inside > 0.5), 0, 1)
    return a * C.blur(keep, 0.6)


def drop_small(al, min_area, thresh=0.08):
    """Remove isolated specks (connected components smaller than min_area px)."""
    n, lab, st, _ = cv2.connectedComponentsWithStats((al > thresh).astype(np.uint8), connectivity=8)
    small = np.flatnonzero(st[1:, cv2.CC_STAT_AREA] < min_area) + 1
    if len(small):
        al = al * (1 - np.isin(lab, small))
    return al


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
    hem = np.array(geo['hem_every_16px'])
    left_tail = (1 - smoothstep(500, 540, xs))[None, :]
    m *= 1 - left_tail * smoothstep(1090, 1110, ys)[:, None]
    # right side tail: no stub hanging below the swags — cut along the last swag's own hem, rising to
    # a gathered cusp at the end (like the jabot)
    hx = np.interp(xs, hem[:, 0], hem[:, 1])
    rise = smoothstep(5880, 5990, xs)
    ycut_r = hx * (1 - rise) + 860.0 * rise
    m *= 1 - smoothstep(5760, 5790, xs)[None, :] * np.clip(ys[:, None] - ycut_r[None, :] + 0.5, 0, 1)
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
    """The tree pit: a low terrazzo kerb (the floor turned up: top face, front face, far inner wall),
    damp soil, and the soil 'lip' that swallows the trunk base (with a wider contact and a low
    mound).  Returns local RGBA layers + their origin."""
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
    t = np.linspace(0, np.pi, 200)
    arc = np.stack([cx + PL_RX * np.cos(t), cy + PL_RY * np.sin(t)], 1)
    face = np.clip(C.poly_mask(np.vstack([arc, arc[::-1] + [0, PL_FACE]]), h, w) - outer, 0, 1)
    wall_in = np.clip(inner - soil, 0, 1)
    # material: the floor's terrazzo, finer and half-desaturated (a polished kerb)
    mos = terrazzo_mosaic()
    tz = C.resize(mos[300:300 + 2 * h, 600:600 + 2 * w, :3], 0.5)
    del mos
    lz = C.lum(tz)[..., None]
    tz = np.clip(lz + (tz - lz) * 0.5, 0, 1)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = np.clip((xx - cx) / PL_RX, -1, 1)
    arc_y = cy + PL_RY * np.sqrt(np.clip(1 - u * u, 0, 1))          # near edge of the top face
    top_sh = 1.04 + 0.04 * (-u)
    face_v = np.clip((yy - arc_y) / PL_FACE, 0, 1)
    face_sh = (0.80 - 0.12 * face_v) * (0.84 + 0.16 * np.sqrt(np.clip(1 - u * u, 0, 1))) * (1 + 0.05 * (-u))
    in_sh = 0.56 + 0.08 * np.clip((cy - yy) / ryi, 0, 1)
    rgb = np.zeros((h, w, 3), np.float32)
    a = np.zeros((h, w), np.float32)
    for m_, sh in ((wall_in, in_sh), (face, face_sh), (rim_top, top_sh)):
        rgb = rgb * (1 - m_[..., None]) + tz * sh[..., None] * m_[..., None]
        a = np.maximum(a, m_)
    # a polished arris catching the light, a 3 px dark line under the top face, contact at the foot
    lit = np.clip(1 - np.abs(yy - arc_y + 2.0) / 1.2, 0, 1) * (yy > cy)
    dark = np.clip(1 - np.abs(yy - arc_y - 1.5) / 1.8, 0, 1) * (yy > cy)
    rgb = rgb * (1 + 0.10 * lit[..., None]) * (1 - 0.40 * dark[..., None])
    foot = smoothstep(PL_FACE - 16, PL_FACE, yy - arc_y) * face
    rgb = rgb * (1 - 0.30 * foot[..., None])
    inner_lip = np.clip(1 - np.abs(np.sqrt(((xx - cx) / rxi) ** 2 + ((yy - cy) / ryi) ** 2) - 1) * rxi / 2.0, 0, 1)
    rgb = rgb * (1 - 0.25 * (inner_lip * (yy < cy + 2))[..., None])
    # damp soil: dark loam, fine crumbs, a few pale grit stones, darker towards the kerb
    rng = np.random.default_rng(41)
    n1 = C.blur(rng.standard_normal((h, w)).astype(np.float32), 0.9)
    n2 = C.blur(rng.standard_normal((h, w)).astype(np.float32), 3.0)
    loam = rgb01('#463628') * (1 + 0.20 * n1 + 0.22 * n2)[..., None]
    grit = (C.blur((rng.random((h, w)) > 0.9975).astype(np.float32), 1.1) * 3.0).clip(0, 1)
    loam = loam * (1 - grit[..., None]) + rgb01('#9C8C78') * grit[..., None]
    sd = np.sqrt(((xx - cx) / (rxi - 2)) ** 2 + ((yy - cy - PL_SOIL_DROP) / (ryi - 1)) ** 2)
    loam *= (1.0 - 0.35 * smoothstep(0.55, 1.0, sd))[..., None]
    tdist = np.sqrt(((xx - (TRUNK_X - x0)) / 110) ** 2 + ((yy - (cy + PL_SOIL_DROP - 6)) / 26) ** 2)
    loam *= (1 - 0.28 * (1 - smoothstep(0.6, 1.2, tdist)))[..., None]       # moist collar
    rgb = rgb * (1 - soil[..., None]) + np.clip(loam, 0, 1) * soil[..., None]
    a = np.maximum(a, soil)
    back = np.dstack([np.clip(rgb, 0, 1), a])
    # the lip: soil in front of the trunk on a low crumbly mound, meeting the trunk along the front half
    # of a small ellipse round it
    tx = TRUNK_X - x0
    xs_ = np.arange(w, dtype=np.float32)
    u_ = np.clip((xs_ - tx) / 82.0, -1, 1)
    contact = (SOIL_TOP - y0) - 13 + 13 * np.sqrt(1 - u_ * u_)
    mound = 40 * (1 - smoothstep(70, 170, np.abs(xs_ - tx)))
    edge_y = np.where(np.abs(xs_ - tx) < 82, contact, cy + PL_SOIL_DROP - mound)
    edge_y = C.blur(edge_y[None, :], 3.0)[0]
    edge_y = edge_y + 5.0 * C.blur(rng.standard_normal((1, w)).astype(np.float32), 2.5)[0] \
        + 1.6 * C.blur(rng.standard_normal((1, w)).astype(np.float32), 0.8)[0]
    lip = soil * np.clip(yy - edge_y[None, :] + 0.5, 0, 1) * (1 - smoothstep(170, 200, np.abs(xx - tx)))
    # a few loose crumbs heaped against the bark, just above the soil line
    crumbs = np.zeros((h, w), np.float32)
    for _ in range(46):
        cx_ = tx + rng.uniform(-70, 70)
        cy_ = np.interp(cx_, xs_, edge_y) - rng.uniform(-1, 9)
        r_ = rng.uniform(2.0, 5.5)
        crumbs = np.maximum(crumbs, np.clip(r_ + 0.5 - np.hypot(xx - cx_, (yy - cy_) * 1.25), 0, 1))
    lip = np.maximum(lip, crumbs * soil)
    crest = np.clip(1 - (yy - edge_y[None, :]) / 8.0, 0, 1) * (yy >= edge_y[None, :] - 0.5)
    tone = 1 + 0.16 * crest + 0.10 * crumbs * C.blur(rng.standard_normal((h, w)).astype(np.float32), 1.0)
    lip_rgba = np.dstack([np.clip(back[..., :3] * tone[..., None], 0, 1), lip])
    return back, lip_rgba, (x0, y0)


def trunk_retouch(vbs, ta, tpos):
    """Heal most of the stamped crescent 'eye' knots on the lower trunk (an AI-bark tell) by cloning
    bark from 45-75 px above / below, keeping three irregularly spaced ones.  vbs = void photo at
    canvas scale (placed at VB_OX, VB_OY), ta = tree alpha at canvas scale placed at tpos.
    Returns (rgba patch, x, y, healed rgb strip, strip alpha) in canvas px."""
    X0, X1, Y0, Y1 = int(TRUNK_X) - 110, int(TRUNK_X) + 110, 2400, 3304
    rgb = vbs[Y0 - VB_OY:Y1 - VB_OY, X0 - VB_OX:X1 - VB_OX].copy()
    a = np.zeros((Y1 - Y0, X1 - X0), np.float32)
    tx, ty = tpos
    sub = ta[Y0 - ty:Y1 - ty, X0 - tx:X1 - tx]
    a[:sub.shape[0], :sub.shape[1]] = sub
    trunk = cv2.erode((a > 0.95).astype(np.uint8), np.ones((7, 7), np.uint8))
    L = C.lum(rgb)
    bg = ndimage.median_filter(L, size=(81, 3))
    knots = (((bg - L) > 0.045) & (trunk > 0)).astype(np.uint8)
    knots = cv2.morphologyEx(knots, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    knots = cv2.dilate(knots, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    n, lab, st, cen = cv2.connectedComponentsWithStats(knots, connectivity=8)
    comps = sorted([i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 80], key=lambda i: cen[i][1])
    keep = {comps[k] for k in (1, 4, 6) if k < len(comps)}         # three, irregularly spaced
    # trunk lean (centre x per row) for the clone offset
    rows = np.flatnonzero((a > 0.5).sum(1) > 20)
    cx_row = np.array([np.flatnonzero(a[r] > 0.5).mean() for r in rows])
    lean = np.polyfit(rows, cx_row, 1)[0] if len(rows) > 10 else 0.0
    out = rgb.copy()
    heal = np.zeros_like(L)
    for i in comps:
        if i in keep:
            continue
        m = (lab == i)
        x, y, w_, h_ = st[i, 0], st[i, 1], st[i, 2], st[i, 3]
        best = None
        for dy in (-60, 60, -48, 48, -75, 75):
            ys0, ys1 = y + dy, y + dy + h_
            if ys0 < 0 or ys1 > rgb.shape[0]:
                continue
            dx = int(round(dy * lean))
            if x + dx < 0 or x + dx + w_ > rgb.shape[1]:
                continue
            cover = knots[ys0:ys1, x + dx:x + dx + w_][m[y:y + h_, x:x + w_]].mean()
            if best is None or cover < best[0]:
                best = (cover, dy, dx)
        if best is None:
            continue
        _, dy, dx = best
        src = rgb[y + dy:y + dy + h_, x + dx:x + dx + w_]
        dst = rgb[y:y + h_, x:x + w_]
        ring = cv2.dilate(m[y:y + h_, x:x + w_].astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) \
            & ~m[y:y + h_, x:x + w_]
        g = (C.lum(dst)[ring].mean() + 1e-4) / (C.lum(src)[ring].mean() + 1e-4) if ring.any() else 1.0
        out[y:y + h_, x:x + w_] = np.where(m[y:y + h_, x:x + w_, None], np.clip(src * g, 0, 1),
                                           out[y:y + h_, x:x + w_])
        heal[y:y + h_, x:x + w_] = np.maximum(heal[y:y + h_, x:x + w_], m[y:y + h_, x:x + w_])
    alpha = C.blur(heal, 2.5) * (a > 0.5)
    patch = np.dstack([out, np.clip(alpha * 1.15, 0, 1)])
    healed = rgb * (1 - alpha[..., None]) + out * alpha[..., None]
    return patch, X0, Y0, healed, a, len(comps) - len(keep)


def bark_grade(rgb, w):
    """Numeric twin of the 'Grade · lower trunk' fills (colour #6F6658 at 0.45, saturation 0.30) with
    per-pixel weight w (0..1) — used for pixels that sit outside the clipping base (the root flare)."""
    import psdkit
    c = np.broadcast_to(rgb01('#6F6658'), rgb.shape).astype(np.float32)
    g = np.broadcast_to(np.float32(0.5), rgb.shape).astype(np.float32)
    out = rgb + (psdkit.BLEND['color'](rgb, c) - rgb) * (0.45 * w)[..., None]
    out = out + (psdkit.BLEND['saturation'](out, g) - out) * (0.30 * w)[..., None]
    return np.clip(out, 0, 1)


def root_flare(healed, a, X0, Y0, flare=26.0, height=140):
    """A root flare at the soil: each row of the trunk just above the soil is stretched sideways by up
    to `flare` px (more towards the soil), so the base widens into the ground instead of standing in it
    like a stick.  Returns (rgba, x, y) in canvas px (placed under the cut-out: only the flanks show)."""
    yb = int(SOIL_TOP) + 6
    yt = yb - height
    r0, r1 = yt - Y0, yb - Y0
    h, w = r1 - r0, healed.shape[1]
    out = np.zeros((h, w, 4), np.float32)
    xs = np.arange(w, dtype=np.float32) + 0.5
    for k, r in enumerate(range(r0, r1)):
        cols = np.flatnonzero(a[r] > 0.5)
        if len(cols) < 10:
            continue
        xl, xr = cols.min() + 0.5, cols.max() + 0.5
        f = flare * ((k + 1) / h) ** 2.2
        tl, tr = xl - f, xr + f
        u = np.clip((xs - tl) / (tr - tl), 0, 1)
        sx = xl + u * (xr - xl)
        for c in range(3):
            out[k, :, c] = np.interp(sx, np.arange(w) + 0.5, healed[r, :, c])
        cov = np.clip(xs - tl + 0.5, 0, 1) * np.clip(tr - xs + 0.5, 0, 1)
        edge = np.minimum(xs - tl, tr - xs)
        out[k, :, :3] *= (0.72 + 0.28 * smoothstep(0, 14, edge))[:, None]
        out[k, :, 3] = cov
    out[..., :3] = bark_grade(out[..., :3], np.ones((h, w), np.float32))
    return out, X0, yt


def leaf_piece(box, scale, angle, flip=False, blur=0.0, anchor=(0.0, 0.0), outline=None, tame_red=False):
    """A crop of the tree (void_lookup_B pixels + tree_B alpha) scaled / turned (deg CCW) / optionally
    mirrored.  box is in tree_B cut coordinates; anchor a point of the crop (tree_B px).  The violet
    fringes are inpainted first; with `outline` only whole leaflets inside it are kept.  With blur the
    piece becomes out-of-focus near foliage with opaque cores.  Returns (rgb, alpha, anchor_xy)."""
    bx0, by0, bx1, by1 = box
    sx0, sy0 = TREE_BOX[0], TREE_BOX[1]
    v = C.load('assets/gen/void_lookup_B.png', 'RGB')[sy0 + by0:sy0 + by1, sx0 + bx0:sx0 + bx1].copy()
    a = C.load('assets/cut/tree_B.png')[by0:by1, bx0:bx1, 3].copy()
    v, _ = inpaint_fringes(v)
    # un-mix the white skylight from the partial-alpha leaf edges (else they glow against a blue sky)
    sky_w = (a < 0.03).astype(np.float32)
    bgw = C.blur(sky_w, 12)
    bgc = np.where(bgw[..., None] > 1e-3, C.blur(v * sky_w[..., None], 12) / np.maximum(bgw, 1e-3)[..., None],
                   v[sky_w > 0].mean(0) if sky_w.any() else 0.9)
    part = ((a > 0.02) & (a < 0.98))[..., None]
    v = np.where(part, np.clip((v - (1 - a[..., None]) * bgc) / np.maximum(a, 0.25)[..., None], 0, 1), v)
    del sky_w, bgw, bgc, part
    if outline is not None:
        a = select_leaves(a, outline, box)
    h, w = a.shape
    ax, ay = anchor[0] - bx0, anchor[1] - by0
    if flip:
        v, a, ax = v[:, ::-1], a[:, ::-1], w - ax
    if tame_red:
        # the red seed clusters blur into magenta blots: take their saturation down
        hsv = cv2.cvtColor(np.ascontiguousarray(v), cv2.COLOR_RGB2HSV)
        red = ((hsv[..., 0] >= 330) | (hsv[..., 0] <= 20)) & (hsv[..., 1] > 0.15)
        hsv[..., 1] = np.where(red, hsv[..., 1] * 0.15, hsv[..., 1])
        v = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
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
    if blur:
        al = smoothstep(0.15, 0.55, al)                 # opaque cores, soft rims: near, not see-through
    # opaque, edge-extended RGB (leaf colour bleeds outwards) so the layer mask alone cuts the piece
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
    skx, sky_y = sky_c
    zones = {}

    # ============================================================ 00 paper
    g = B.group('00 · Paper', label='gray')
    B.px(g, 'Paper · warm linen ground', C.load('assets/mat/paper_linen_A3.png', 'RGB'), 0, 0, locked=True)

    # ============================================================ 10 outside
    g = B.group('10 · Outside — the street at blue hour', label='blue')
    a, x, y = local(fac_rect)
    B.shadow(g, 'Shadow · entrance facade on the page', a, x, y, depth=16, opacity=0.30)
    st = C.resize(C.load('assets/outside/street_dusk.png', 'RGB'), STREET_S)
    B.photo(g, 'Outside · street at blue hour (photo)', st, GB_X - STREET_CROP[0], GB_Y - STREET_CROP[1],
            mask_alpha=glazing, margin=160)
    del st
    B.fill(g, 'Grade · lift the shadows', '#4A5578', None, blend='screen', opacity=0.45, clip=True)
    wet = (smoothstep(1900, 2500, yy_canvas())) * glazing
    B.fill(g, 'Grade · warm wet street', PAL['honey'], wet, blend='soft light', opacity=0.5, clip=True)
    del wet

    # ============================================================ 20 entrance facade
    g = B.group('20 · Entrance — glass block & door', label='blue')
    fb, face = facade_blocks()
    blocks_mask = fac_rect * (1 - glazing)
    B.photo(g, 'Facade · glass blocks, street refracted', fb, GB_X, GB_Y, mask_alpha=blocks_mask, margin=60)
    del fb
    B.fill(g, 'Grade · glass sheen (celadon)', PAL['glass'], None, blend='screen', opacity=0.25, clip=True)
    fmask = np.zeros((H, W), np.float32)
    fh, fw_ = face.shape
    fmask[GB_Y:GB_Y + fh, GB_X:GB_X + fw_] = face[:H - GB_Y, :W - GB_X]
    del face
    yc = yy_canvas()
    B.fill(g, 'Grade · glass depth (dusk, not mortar)', PAL['dusk'],
           fmask * blocks_mask * (1 - smoothstep(1700, 2500, yc)), blend='multiply', opacity=0.25, clip=True)
    B.fill(g, 'Grade · lamplight in the low courses', PAL['honey'], fmask * blocks_mask * smoothstep(1900, 2700, yc),
           blend='soft light', opacity=0.75, clip=True)
    del yc
    zones['facade blocks outside disc'] = (blocks_mask > 0.5) & (circle < 0.5)
    zones['facade glass outside disc'] = zones['facade blocks outside disc'] & (fmask > 0.5)
    del fmask
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
    hx0, hy0_ = int(round(hx0)), int(round(hy0_))
    hb = fr[hy0_:hy0_ + hcov.shape[0], hx0:hx0 + hcov.shape[1]]
    np.maximum(hb, hcov, out=hb)
    door_solid = fr                                    # frame + handle: the rain falls behind them
    del a

    # ============================================================ 30 the bar, behind us
    g = B.group('30 · Behind you — the bar (elevation 01)', label='orange')
    bar_all = np.clip(bar_plane + box_alpha(CTR_X0 - 10, CTR_Y - 26, BAR_X1, FLOOR_Y), 0, 1)
    a, x, y = local(bar_all)
    B.shadow(g, 'Shadow · bar planes on the page', a, x, y, depth=20, opacity=0.34)
    # fluted oak bulkhead with the painted sign panel between two fluted panels (elevation 01)
    bw_ = BAR_X1 - BAR_X0
    bh_ = BULK_Y1 - BULK_Y0
    oak = C.texture_fill(C.load('assets/mat/oak_fluted.png', 'RGB'), bh_ + 40, bw_ + 40, scale=0.44)
    B.photo(g, 'Bar · fluted oak bulkhead (sign band)', oak, BAR_X0 - 20, BULK_Y0 - 20,
            mask_alpha=box_alpha(BAR_X0, BULK_Y0, BAR_X1, BULK_Y1), margin=20)
    del oak
    sp_x0, sp_x1 = el(437, 0)[0], el(1565, 0)[0]
    sp_y1 = el(0, 765)[1]
    panel = box_alpha(sp_x0, BULK_Y0, sp_x1, sp_y1)
    B.fill(g, 'Bar · sign panel (painted)', '#E9DFCF', panel, clip=True)
    pl = C.texture_fill(C.load('assets/mat/plaster_warm.png', 'RGB'), BULK_Y1 - BULK_Y0, int(sp_x1 - sp_x0) + 2,
                        scale=0.6)
    B.photo(g, 'Bar · sign panel, limewash texture', pl, sp_x0, BULK_Y0, mask_alpha=panel, blend='multiply',
            opacity=0.55, clip=True)
    del pl
    shade = smoothstep(BULK_Y0, BULK_Y1, yy_canvas()) * box_alpha(BAR_X0, BULK_Y0, BAR_X1, BULK_Y1)
    B.fill(g, 'Shade · bulkhead, darker at the soffit', '#6B4A2E', shade, blend='multiply', opacity=0.35,
           clip=True)
    del shade
    inset = np.clip(cv2.dilate(panel, np.ones((5, 5), np.uint8)) - panel, 0, 1)
    a, x, y = local(inset)
    B.px(g, 'Bar · sign panel joint', colour_rgba(a, '#5A3E26'), x, y, opacity=0.55)
    del panel, inset
    scx_, scy_ = el(1005, 678)
    B.text(g, 'RESTAURANT', 'mono-medium', 56, scx_, scy_, anchor='origin', align='center', tracking=200,
           color=INK, name='TXT · bar sign RESTAURANT (elev. 01)')
    # glass-brick back wall (proposed in place of the decorative brick); it runs down to the floor
    # (its photographed sill) where the counter does not hide it
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
        B.cutout(g, f'Bar · dome pendant {i + 1} (photo cut-out)', nm, PEND_S, x_, y_, margin=30, alpha_fn=trim)
        b = info['bulb']
        pend_bulbs.append((x_ + b['cx'] * PEND_S, y_ + b['cy'] * PEND_S))
    B.text(g, 'GLASS BRICK PROPOSED\nIN PLACE OF DECORATIVE BRICK', 'mono', LABEL, BAR_X0 + 24, 2412, tracking=90,
           leading=1.55, color=LINEN, name='TXT · note, glass brick proposal')
    # counter: fluted oak front + brushed steel top (top face, edge, specular line)
    cw_ = CTR_X1 - CTR_X0
    ch_ = FLOOR_Y - CTR_Y
    front = C.texture_fill(C.load('assets/mat/oak_fluted.png', 'RGB'), ch_ + 40, cw_ + 40, scale=0.5)
    B.photo(g, 'Bar · fluted oak counter front', front, CTR_X0 - 20, CTR_Y - 20,
            mask_alpha=box_alpha(CTR_X0, CTR_Y + 12, CTR_X1, FLOOR_Y), margin=20)
    del front
    shade = smoothstep(CTR_Y, FLOOR_Y + 60, yy_canvas()) * box_alpha(CTR_X0, CTR_Y, CTR_X1, FLOOR_Y)
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
    # the espresso machine and the stools: silhouettes traced from elevation 01
    ev_a = C.load('assets/lines/elev01_bar.png')[..., 3]

    def silhouette(x0_, y0_, x1_, y1_, close=5):
        sb = (ev_a[y0_:y1_, x0_:x1_] > 0.3).astype(np.uint8)
        sil = ndimage.binary_fill_holes(cv2.morphologyEx(sb, cv2.MORPH_CLOSE, np.ones((close, close), np.uint8)))
        return C.resize(C.blur(sil.astype(np.float32), 0.6), EL_K)
    mach = silhouette(1286, 1400, 1614, 1558, close=7)
    mx0, my0 = el(1286, 1400)
    B.fill_local(g, 'Bar · espresso machine (elev. 01)', INK, mach, mx0, my0, opacity=0.55)
    hiss_at = el(1600, 1440)
    sil = silhouette(763 - 110, 1640, 763 + 110, 2060)
    for k, scx in enumerate((355, 763, 1171)):
        ox_, oy_ = el(scx - 110, 1640)
        foot = np.zeros((40, sil.shape[1] + 60), np.float32)
        cv2.ellipse(foot, (foot.shape[1] // 2, 20), (int(sil.shape[1] * 0.42), 9), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        B.shadow(g, f'Shadow · stool {k + 1} on the floor', foot, ox_ - 30, FLOOR_Y - 20, depth=6, sigma=8,
                 opacity=0.45)
        B.fill_local(g, f'Bar · stool {k + 1} silhouette (elev. 01)', INK, sil, ox_, oy_, opacity=0.78)
    del ev_a
    # espresso on the counter at true scale (CC0 photo, non-destructive cut-out) with a contact shadow
    ci = cut_info('espresso_cc0.png')
    cs_ = 0.17
    sx_, sy_, srx, sry = ci['saucer_ellipse']
    cup_x = 840 - sx_ * cs_
    cup_y = CTR_Y - top_h * 0.45 - (sy_ + sry * 0.92) * cs_
    ca = np.zeros((int(sry * cs_ * 0.5) + 24, int(srx * 2 * cs_) + 30), np.float32)
    cv2.ellipse(ca, (ca.shape[1] // 2, 12), (int(srx * cs_ * 0.95), max(2, int(sry * cs_ * 0.18))), 0, 0, 360,
                1.0, -1, cv2.LINE_AA)
    B.shadow(g, 'Shadow · cup contact on the steel', ca, cup_x + sx_ * cs_ - ca.shape[1] / 2,
             cup_y + (sy_ + sry * 0.9) * cs_ - 12, depth=2, sigma=2.5, opacity=0.55)
    lay, (cux, cuy, cuw, cuh) = B.cutout(g, 'Bar · espresso cup (CC0 photo cut-out)', 'espresso_cc0.png',
                                         cs_, cup_x, cup_y, margin=12)
    sm = np.zeros((int(np.ceil(cuh)) + 2, int(np.ceil(cuw)) + 2), np.float32)
    cv2.ellipse(sm, (int(sx_ * cs_), int(sy_ * cs_)), (int(srx * cs_ + 2), int(sry * cs_ + 2)), 0, 0, 360, 1.0, -1,
                cv2.LINE_AA)
    rx_, ry_, rrx, rry = ci['cup_rim_ellipse']
    cv2.ellipse(sm, (int(rx_ * cs_), int(ry_ * cs_)), (int(rrx * cs_ + 1), int(rry * cs_ + 1)), 0, 0, 360, 0.0,
                -1, cv2.LINE_AA)
    B.fill_local(g, 'Grade · saucer desaturated', '#808080', C.blur(sm, 1), cux, cuy, blend='saturation',
                 opacity=0.35, clip=True)
    cup_steam = (cux + rx_ * cs_, cuy + ry_ * cs_)

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
    depth_fade = (1 - smoothstep(FLOOR_Y, FLOOR_Y + 420, yy_canvas())) * floor
    B.fill(g, 'Grade · floor recedes into shade', '#6E6458', depth_fade, blend='multiply', opacity=0.35, clip=True)
    del depth_fade
    dap = S.dapple(size=(fa.shape[1], fa.shape[0]), at=(fx, fy), leaf_size=42, density=0.30, opacity=0.5,
                   angle=-20, edge_fade=0.12, seed=12)
    B.photo(g, 'Floor · leaf-shadow dapple', dap[0], dap[1][0], dap[1][1], mask_alpha=floor, blend='multiply',
            opacity=0.30)
    del dap
    # the tree pit (back): far inner wall, soil, kerb — the trunk stands in front of this
    g = B.group('45 · Tree pit — terrazzo kerb & soil', label='green')
    back, lip, (plx, ply) = planter_parts()
    sh = np.zeros((back.shape[0], back.shape[1]), np.float32)
    cv2.ellipse(sh, (int(PL_CX - plx), int(PL_CY - ply + PL_FACE - 6)), (int(PL_RX + 8), int(PL_RY + 6)), 0, 0,
                360, 1.0, -1, cv2.LINE_AA)
    B.shadow(g, 'Shadow · kerb on the terrazzo', sh, plx, ply, depth=10, sigma=10, opacity=0.45)
    B.px(g, 'Tree pit · terrazzo kerb & damp soil', back, plx, ply)

    # ============================================================ 50 the void
    g = B.group('50 · The void — looking up', label='green', opened=True)
    cl, clx, cly = local(circle)
    B.shadow(g, 'Shadow · void disc', cl, clx, cly, depth=24, opacity=0.25)
    rim, pad = card_edge(cl, width=5)
    B.px(g, 'Void · paper rim', rim, clx - pad, cly - pad)
    vbs = C.resize(C.load('assets/gen/void_lookup_B.png', 'RGB'), VB_S)
    B.photo(g, 'Void · looking up (photo, disc mask)', vbs, VB_OX, VB_OY, mask_alpha=cl,
            mask_xy=(clx, cly), margin=200)
    # violet chromatic-aberration fringes healed by inpainting (the photo and the tree share pixels)
    by0, by1 = max(0, cly - 210 - VB_OY), min(vbs.shape[0], cly + cl.shape[0] + 210 - VB_OY)
    bx0, bx1 = max(0, clx - 210 - VB_OX), min(vbs.shape[1], clx + cl.shape[1] + 210 - VB_OX)
    healed, ha = inpaint_fringes(vbs[by0:by1, bx0:bx1])
    B.px(g, 'Retouch · fringes healed (photo)', np.dstack([healed, ha]), VB_OX + bx0, VB_OY + by0, clip=True)
    glz = C.resize(C.load('assets/cut/geo/void_lookup_B/skylight_glazing.png', 'L'), VB_S)
    # --- the tree, registered on its own photograph
    gt = B.group('55 · Tree — rising through the void', label='green', parent=g, opened=True)
    ta = C.resize(C.load('assets/cut/tree_B.png')[..., 3], VB_S)
    tx_, ty_ = vb(TREE_BOX[0], TREE_BOX[1])
    tpos = (int(round(tx_)), int(round(ty_)))
    hh_, ww_ = ta.shape
    tav = np.zeros((H, W), np.float32)
    tav[tpos[1]:tpos[1] + hh_, tpos[0]:tpos[0] + ww_] = ta[:H - tpos[1], :W - tpos[0]]
    outside_disc = 1 - circle[tpos[1]:tpos[1] + hh_, tpos[0]:tpos[0] + ww_]
    B.shadow(gt, 'Shadow · tree on the page', ta[:outside_disc.shape[0], :outside_disc.shape[1]] * outside_disc,
             tpos[0], tpos[1], depth=16, opacity=0.30)
    del outside_disc
    # one branch reaching out of the void towards the street; its base slips under the crown
    rgb_, al_, q = leaf_piece(TWIG['box'], TWIG['scale'], TWIG['angle'], anchor=TWIG['base'],
                              outline=TWIG['outline'])
    px0, py0 = int(round(TWIG['target'][0] - q[0])), int(round(TWIG['target'][1] - q[1]))
    th_, tw_ = al_.shape
    twig_alpha = np.zeros((H, W), np.float32)
    twig_alpha[py0:py0 + th_, px0:px0 + tw_] = al_
    off = 1 - circle[py0:py0 + th_, px0:px0 + tw_]
    B.shadow(gt, 'Shadow · branch breaking out (page)', al_ * off, px0, py0, depth=14, opacity=0.30)
    B.photo(gt, 'Tree · branch breaking out of the void', rgb_, px0, py0, mask_alpha=al_, mask_xy=(px0, py0))
    del rgb_, off
    # root flare under the cut-out (only its flanks show), graded like the lower trunk
    patch, kx, ky, healed_trunk, trunk_a, n_healed = trunk_retouch(vbs, ta, tpos)
    flare, fx_, fy_ = root_flare(healed_trunk, trunk_a, kx, ky)
    B.px(gt, 'Tree · root flare at the soil (bark)', flare, fx_, fy_)
    B.cutout(gt, 'Tree · cut-out (registered on its photo)', 'tree_B.png', VB_S, tx_, ty_, margin=TREE_MARGIN)
    # the cut-out carries the same pixels as the photo: same healed fringes, then the trunk retouch
    tbx0, tby0 = tpos[0] - VB_OX - bx0, tpos[1] - VB_OY - by0
    hsub = healed[max(0, tby0):tby0 + hh_, max(0, tbx0):tbx0 + ww_]
    asub = ha[max(0, tby0):tby0 + hh_, max(0, tbx0):tbx0 + ww_]
    B.px(gt, 'Retouch · leaf fringes healed', np.dstack([hsub, asub]), VB_OX + bx0 + max(0, tbx0),
         VB_OY + by0 + max(0, tby0), clip=True)
    del healed, ha, hsub, asub
    B.px(gt, f'Retouch · trunk knots healed ({n_healed})', patch, kx, ky, clip=True)
    del patch, healed_trunk, trunk_a
    trunk_band = box_alpha(TRUNK_X - 85, 2380, TRUNK_X + 85, 3320) * smoothstep(2450, 2700, yy_canvas())
    B.fill(gt, 'Grade · lower trunk to grey bark', '#6F6658', trunk_band, blend='color', opacity=0.45, clip=True)
    B.fill(gt, 'Grade · lower trunk desaturated', '#808080', trunk_band, blend='saturation', opacity=0.30,
           clip=True)
    del trunk_band
    ao = np.zeros((90, 220), np.float32)
    ao[:, :] = smoothstep(0, 90, np.arange(90, dtype=np.float32))[:, None] ** 1.5
    B.fill_local(gt, 'Shade · trunk base darkens into the soil', '#2E241C', ao, TRUNK_X - 110,
                 SOIL_TOP - 84, blend='multiply', opacity=0.55, clip=True)
    # leaves of the photo that the tree cut-out does not carry (they are not sky either)
    hsv = cv2.cvtColor(np.ascontiguousarray(vbs), cv2.COLOR_RGB2HSV)
    leafy = (((hsv[..., 0] > 45) & (hsv[..., 0] < 175) & (hsv[..., 1] > 0.16)) | (hsv[..., 2] < 0.30))
    leafy = C.blur(cv2.dilate(leafy.astype(np.uint8) * (glz > 0.3).astype(np.uint8), np.ones((3, 3), np.uint8))
                   .astype(np.float32), 0.8)
    del hsv, vbs
    # --- sky at blue hour, behind the leaves (crown and branch excluded)
    sky = np.zeros((H, W), np.float32)
    gh_, gw_ = glz.shape
    sky[VB_OY:VB_OY + gh_, VB_OX:VB_OX + gw_] = glz[:H - VB_OY, :W - VB_OX]
    tav[VB_OY:VB_OY + gh_, VB_OX:VB_OX + gw_] = np.maximum(tav[VB_OY:VB_OY + gh_, VB_OX:VB_OX + gw_],
                                                           leafy[:H - VB_OY, :W - VB_OX])
    del glz, leafy
    sky_m = sky
    tree_m = np.maximum(tav, twig_alpha)
    del tav
    sky = sky_m * (1 - np.clip((tree_m - 0.5) / 0.45, 0, 1)) * circle     # leaf edges take the dusk too
    B.fill(g, 'Sky · blue hour (multiply)', PAL['dusk'], sky, blend='multiply', opacity=0.60)
    B.fill(g, 'Sky · blue hour (colour)', '#3A4D86', sky, blend='color', opacity=0.65)
    B.fill(g, 'Sky · deepen (soft light)', '#2E3A5C', sky, blend='soft light', opacity=0.30)
    sb = C.bbox(sky)
    rb = C.cover(rain_beads(), sb[2] - sb[0], sb[3] - sb[1], (0.6, 0.6))
    B.photo(g, 'Sky · rain beads on the skylight', rb, sb[0], sb[1], mask_alpha=sky, blend='screen', opacity=0.6)
    zones['skylight (visible sky)'] = sky > 0.5
    del sky, rb

    # ============================================================ 60 tree pit front
    g = B.group('60 · Tree pit — soil lip round the trunk', label='green')
    cs = np.zeros(lip.shape[:2], np.float32)
    cv2.ellipse(cs, (int(TRUNK_X - plx + 4), int(SOIL_TOP - ply - 2)), (70, 9), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
    B.shadow(g, 'Shadow · trunk contact on the soil', cs, plx, ply, depth=2, sigma=5, opacity=0.35)
    B.px(g, 'Tree pit · soil swallowing the trunk', lip, plx, ply)
    del back, lip

    # ============================================================ 70 ceiling: festoon valance
    g = B.group('70 · Overhead — the festoon valance', label='orange')
    v, m, (vsx, vsy), patches = valance_parts()
    vx, vy = (vsx - VAL_SX0) * VAL_S, (vsy - VAL_SY0) * VAL_S
    vs = C.resize(v, VAL_S)
    ms = C.resize(m, VAL_S)
    del v, m
    B.shadow(g, 'Shadow · valance hem on the page', ms, vx, vy, depth=26, opacity=0.36)
    B.photo(g, 'Valance · swags (photo, fabric mask)', vs, vx, vy, mask_alpha=ms, mask_xy=(vx, vy),
            keep_offcanvas=True)
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
            ('top left', (0, 1100, 720, 1700), -38.0, True, (720, 1400), (-260, -90)),
            ('top right', (1700, 1100, 2287, 1640), 38.0, True, (1700, 1370), (W + 240, -90))):
        rgb_, al_, q = leaf_piece(box_, 1.5, ang, flip, blur=7.0, anchor=anc, tame_red=True)
        px0, py0 = int(round(target[0] - q[0])), int(round(target[1] - q[1]))
        al_ = al_ * np.clip((NEAR_MAX_Y - (np.arange(al_.shape[0])[:, None] + py0)) / 120.0, 0, 1)
        al_ = drop_small(al_, 4000)
        B.shadow(g, f'Shadow · near leaves ({side})', al_, px0, py0, depth=70, sigma=45, opacity=0.20)
        B.photo(g, f'Near · leaves overhead ({side})', rgb_, px0, py0, mask_alpha=al_, mask_xy=(px0, py0))
        B.fill(g, f'Grade · backlit, in shade ({side})', '#3E4A30', None, blend='multiply', opacity=0.62, clip=True)
        del rgb_, al_

    # ============================================================ 80 light & colour intensity
    g = B.group('80 · Light & colour intensity', label='yellow', opened=True)
    B.gen(g, 'Light · last blue light down the void',
          S.light_beam(apex=(skx + 20, sky_y - 60), angle=-90, length=SOIL_TOP - sky_y + 80, spread=3.5, aperture=560,
                       color=PAL['glass'], intensity=0.65, core=0.3, rays=0.25, dust=170, dust_color='#F4F7F2',
                       seed=21), blend='screen', opacity=0.75)
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

    lens_fac = C.blur(circle * fac_rect, 18) * (1 - sky_m) * (1 - tree_m)
    lens_bar = C.blur(circle * bar_plane, 18) * (1 - tree_m)
    sky_vis = sky_m * (1 - tree_m)
    core = blob(2262, 1330, 760, 740, 1.25) * np.clip(circle + twig_alpha, 0, 1) * (1 - 0.9 * sky_vis) \
        * (1 - lens_fac) * (1 - lens_bar)
    B.fill(g, 'Intensity · green-gold core (soft light)', GREEN_GOLD, core, blend='soft light', opacity=0.85)
    B.fill(g, 'Intensity · green-gold core (saturation)', '#9ED22E', core * np.clip(tree_m * 1.3, 0, 1),
           blend='saturation', opacity=0.30)
    cg, (cgx, cgy) = S.glow(at=(2262, 1310), radius=940, color=GREEN_GOLD, intensity=0.5, ratio=0.95)
    B.photo(g, 'Light · canopy glow', cg, cgx, cgy, mask_alpha=np.clip(1 - 0.85 * sky_vis, 0, 1),
            blend='screen', opacity=0.40)
    del cg, sky_vis
    # where the void overlaps the street and the bar, colour intensifies (soft-edged lenses)
    B.fill(g, 'Intensity · void x street (colour)', '#6C4BC8', lens_fac, blend='color', opacity=0.55)
    B.fill(g, 'Intensity · void x street (light)', '#7A5BC4', lens_fac, blend='soft light', opacity=0.45)
    B.fill(g, 'Intensity · void x bar (honey)', PAL['honey'], lens_bar, blend='overlay', opacity=0.60)
    zones['lens street'] = (circle * fac_rect > 0.5) & (lens_fac > 0.5)
    zones['lens bar'] = (circle * bar_plane > 0.5) & (lens_bar > 0.5)
    zones['void ring outside lenses'] = (circle > 0.5) & (fac_rect < 0.5) & (bar_plane < 0.5) & (sky_m < 0.5) \
        & (tree_m < 0.5)
    del lens_fac, lens_bar
    B.fill(g, 'Intensity · amber warmth at the bar', PAL['amber'], blob(700, 2250, 820, 620, 1.3) * (1 - circle),
           blend='soft light', opacity=0.45)
    B.fill(g, 'Intensity · terracotta to the cabins', PAL['terracotta'], blob(-80, 2150, 520, 900, 1.2) * bar_all,
           blend='soft light', opacity=0.55)
    del xx, yy, core, bar_all

    # ============================================================ 85 senses
    g = B.group('85 · Senses — sound & smell', label='red', opened=True)
    # SOUND 01: voices rise and echo in the void — three calm rings centred on the skylight
    RINGS = ((300, 3.2, 0.90), (510, 2.8, 0.75), (730, 2.4, 0.60))
    ro_x, ro_y = int(skx) - 760, int(sky_y) - 760
    rings = np.zeros((1520, 1520, 4), np.float32)
    for k, (r, wd, al) in enumerate(RINGS):
        rg, (rx0, ry0) = S.sound_rings(at=(skx, sky_y), r_max=r, r_min=r, n=1, width=wd, color=PAL['honey'],
                                       alpha=al, decay=1.0, wobble=0.0, seed=k)
        hh_, ww_ = rg.shape[:2]
        sub = rings[ry0 - ro_y:ry0 - ro_y + hh_, rx0 - ro_x:rx0 - ro_x + ww_]
        a_ = rg[..., 3:4]
        sub[..., :3] = rg[..., :3] * a_ + sub[..., :3] * (1 - a_)
        sub[..., 3:4] = a_ + sub[..., 3:4] * (1 - a_)
    B.photo(g, 'Sound · voices rise up the void', rings, ro_x, ro_y,
            mask_alpha=disc(VOID_C[0], VOID_C[1], VOID_R - 8, feather=6), blend='multiply', opacity=0.85)
    del rings
    # where the SOUND 01 leader lands: the visible point of the r=510 ring (open sky) nearest the tag
    vis = C.blur(sky_m * (1 - tree_m) * disc(VOID_C[0], VOID_C[1], VOID_R - 60), 6)
    best = None
    for th in np.radians(np.arange(-10, 80, 1.0)):
        px_, py_ = skx + 510 * np.cos(th), sky_y - 510 * np.sin(th)
        v_ = vis[int(py_), int(px_)]
        if v_ > 0.97:
            d_ = np.hypot(px_ - 3420, py_ - 880)
            if best is None or d_ < best[0]:
                best = (d_, px_, py_)
    ring_pt = (best[1], best[2]) if best else (skx + 510 * 0.87, sky_y - 255)
    del vis
    # SOUND 02: espresso hiss from the machine, fading arcs towards the void
    B.gen(g, 'Sound · espresso hiss, fading arcs', S.sound_rings(at=hiss_at, r_max=300, r_min=60, n=4,
                                                                 arc=(-30, 75), width=3.0, color=INK,
                                                                 alpha=0.9, decay=0.78, thin=0.92, spacing=1.15,
                                                                 end_fade=18, seed=7), blend='multiply')
    # rain outside: short slanted dashes in the clear glazing, behind the steel frame and handle
    rd = rain_dashes(gw, gh, 520, 9)
    B.photo(g, 'Sound · rain, slanted dashes', colour_rgba(rd, PAL['glass']), gx0, gy0,
            mask_alpha=glazing * (1 - door_solid), blend='screen', opacity=0.85)
    del rd, door_solid
    # SMELL
    B.gen(g, 'Smell · roasted coffee from the cup',
          S.wisp(at=(cup_steam[0], cup_steam[1] - 2), height=300, ribbons=2, width=40, color=PAL['honey'],
                 color_top=LINEN, opacity=1.0, lean=-0.15, seed=31), blend='screen')
    leaf_wisp = (TRUNK_X - 250, PL_CY + 22)
    B.gen(g, 'Smell · green leaf & damp soil',
          S.wisp(at=leaf_wisp, height=600, ribbons=2, width=56, color=PAL['oat'],
                 color_top=LINEN, opacity=0.9, lean=-0.12, seed=33), opacity=0.45)
    B.gen(g, 'Smell · petrichor at the door',
          S.wisp(at=(DOOR_X0 + 420, FLOOR_Y + 12), height=560, ribbons=2, width=54, color=PAL['celadon'],
                 color_top=PAL['glass'], opacity=0.7, lean=-0.45, seed=35), blend='screen', opacity=0.45)

    # ============================================================ 90 drawings
    g = B.group('90 · Drawings — client linework', label='violet')
    # (a) the stair to the gallery, from section B-B, registered on the trunk axis and the floor line:
    #     both flights with treads and risers (black linework only; grey furniture and poché dropped)
    sec = C.load('assets/lines/section_BB_right.png')
    kb = 0.52
    al = sec[..., 3]
    thick = cv2.morphologyEx((al > 0.35).astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    black = cv2.dilate((al > 0.8).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32)
    sec[..., 3] = al * black * (1 - cv2.dilate(thick, np.ones((5, 5), np.uint8)).astype(np.float32))
    del al, thick, black
    secs = C.resize(LW.thicken(sec, 0.95 / kb), kb)
    del sec
    bx0_, by0_ = TRUNK_X - 3168.1 * kb, FLOOR_Y - 4226.5 * kb
    st_box = (bx0_ + 4040 * kb, by0_ + 1880 * kb, bx0_ + 6060 * kb, by0_ + 4250 * kb)
    keep = box_alpha(*st_box) * np.clip(box_alpha(FAC_X0 + 6, FAC_Y0 + 6, DOOR_X0 - 16, FLOOR_Y - 2)
                                         - disc(VOID_C[0], VOID_C[1], VOID_R + 24), 0, 1)
    keep = C.blur(keep, 4) * keep
    B.photo(g, 'Drawing · stair to the gallery (B-B)', secs, bx0_, by0_, mask_alpha=keep, blend='multiply',
            opacity=0.55, locked=True)
    stair_mid = (bx0_ + 5300 * kb, by0_ + 2700 * kb)
    del secs, keep
    # (b) elevation 01: the leaf logo beside the sign, the counter front and the stools (ghost)
    ev = C.load('assets/lines/elev01_bar.png')
    evs = C.resize(LW.thicken(ev, 0.4 / EL_K), EL_K)
    del ev
    ex0, ey0 = EL_X0, EL_Y0
    nodisc = 1 - disc(VOID_C[0], VOID_C[1], VOID_R + 30, feather=8)
    keep = box_alpha(*el(540, 395), *el(735, 560)) * nodisc
    B.photo(g, 'Drawing · elev. 01 leaf logo (ghost)', evs, ex0, ey0, mask_alpha=keep, blend='multiply',
            opacity=0.55, locked=True)
    keep = np.clip(box_alpha(BAR_X0 - 4, CTR_Y + 20, 1060, FLOOR_Y + 4)
                   + box_alpha(*el(1280, 1395), *el(1620, 1560)), 0, 1) * nodisc
    B.photo(g, 'Drawing · elev. 01 stools & machine', evs, ex0, ey0, mask_alpha=keep,
            blend='multiply', opacity=0.45, locked=True)
    del evs, keep, nodisc

    # ============================================================ 94 viewpoint
    g = B.group('94 · Viewpoint — where we stand & look')
    # the planes the void overlaps, continued as dashed hairlines inside the disc
    hl = np.zeros((H, W), np.float32)
    inner = lambda x, y: (x - VOID_C[0]) ** 2 + (y - VOID_C[1]) ** 2 < (VOID_R - 6) ** 2  # noqa: E731

    def seg_in_disc(p0, p1):
        n = int(np.hypot(p1[0] - p0[0], p1[1] - p0[1]))
        ts_ = np.linspace(0, 1, n)
        pts = [(p0[0] + t * (p1[0] - p0[0]), p0[1] + t * (p1[1] - p0[1])) for t in ts_]
        pts = [p for p in pts if inner(*p)]
        if len(pts) > 2:
            aa_line(hl, [pts[0], pts[-1]], width=2.0, alpha=1.0, dash=(14.0, 10.0))
    seg_in_disc((FAC_X0, FAC_Y0), (W, FAC_Y0))                 # facade top
    seg_in_disc((FAC_X0, FAC_Y0), (FAC_X0, FLOOR_Y))           # facade side
    seg_in_disc((0, BULK_Y0), (BAR_X1, BULK_Y0))               # bar top
    seg_in_disc((BAR_X1, BULK_Y0), (BAR_X1, FLOOR_Y))          # bar side
    hl *= (1 - tree_m)
    a, x, y = local(hl)
    B.px(g, 'Hairline · street & bar planes behind', colour_rgba(a, LINEN), x, y, opacity=0.7)
    del hl
    vx_, vy_ = VIEWER
    out_end = (DOOR_X0 + 300, 2140)
    up_dir = np.array([skx + 140 - vx_, sky_y + 120 - vy_], np.float64)
    up_dir /= np.linalg.norm(up_dir)
    up_chip_bottom = sky_y - 64                                  # the chip sits inside the inner ring
    up_end = (vx_ + up_dir[0] * (up_chip_bottom + 12 - vy_) / up_dir[1], up_chip_bottom + 12)
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
    del sky_m, tree_m

    # ============================================================ 95 legend & key plan (shared)
    B.legend(B.doc.root, '01', [('colour', 'amber', 'AMBER'), ('colour', GREEN_GOLD, 'GREEN-GOLD'),
                                ('colour', 'violet', 'VIOLET'), ('colour', 'dusk', 'DUSK'),
                                ('mat', 'steel_brushed', 'STEEL'), ('mat', 'linen_plain', 'LINEN'),
                                ('mat', 'terrazzo_cream', 'TERRAZZO'), ('mat', 'glassblock', 'GLASS BLOCK')])

    # ============================================================ 98 type
    g = B.group('98 · Type — title & annotations', opened=True)
    B.title_block(g, 'RESTAURANT  ·  ATMOSPHERE STUDY  ·  01 / 02', ['From the void,', 'looking out'],
                  'GROUND FLOOR  ·  BENEATH THE TREE, UP TO THE SKY AND OUT TO THE STREET')
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
    B.tag(g, 'TEXTURE', 'cool glass block · brushed steel rail ·\nsmooth bark · soft linen overhead', 742, ROW1)
    bar_entries = [('SOUND · 02', 'the hiss of the espresso machine, a clink of glass'),
                   ('SMELL · 01', 'roasted coffee, warm and bitter'),
                   ('TASTE', 'espresso, burnt sugar, a twist of orange')]
    B.card(g, 'At the bar', bar_entries, MARGIN, box[3] + 22 + 64)
    cap_y = BULK_Y0 - 30
    B.text(g, '←  TO THE CABINS (02)', 'mono', LABEL, MARGIN, cap_y - 46, tracking=110, color=PAL['terracotta'],
           name='TXT · pointer to the cabins (02)')
    B.text(g, 'BEHIND YOU  ·  THE BAR', 'mono', LABEL, MARGIN, cap_y, tracking=110,
           name='TXT · behind you, the bar')
    # right column, on paper above the entrance
    hh = tag_size('SOUND · 01', 'voices from both floors\nrise and soften in the void', hero=True)[1]
    hbox = B.tag(g, 'SOUND · 01', 'voices from both floors\nrise and soften in the void', 3420, ROW1, hero=True)
    B.leader(g, 'Leader · sound 01 to the rings', [(hbox[0], ROW1 + hh * 0.62), ring_pt],
             width=2.0, dot_at_end=True, opacity=0.85)
    lw_ = tag_size('LIGHT', 'the last blue light falls down the void;\nthe pendants answer in amber')[0]
    B.tag(g, 'LIGHT', 'the last blue light falls down the void;\nthe pendants answer in amber', W - MARGIN - lw_,
          ROW1)
    B.text(g, 'ENTRANCE  ·  GLAZED END', 'mono', LABEL, DOOR_X0, FAC_Y0 - 34, tracking=110,
           name='TXT · entrance, glazed end')
    # the stair, labelled on the paper above the facade
    sl_x = 3300
    B.text(g, 'STAIR TO THE GALLERY\nSECTION B-B', 'mono', LABEL, sl_x, FAC_Y0 - 80, tracking=110, leading=1.7,
           name='TXT · stair to the gallery, section B-B')
    B.leader(g, 'Leader · stair label to the flights', [(sl_x + 40, FAC_Y0 - 22), stair_mid], width=2.0,
             dot_at_end=True, opacity=0.85)
    # the view out, inside the glass
    ob = B.tag(g, 'OUTSIDE · BLUE HOUR', 'rain on the street,\nsoftened by glass block', DOOR_X0 + 54, TRANSOM_Y + 70)
    B.leader(g, 'Leader · outside to the rain', [(ob[0] + 96, ob[3]), (ob[0] + 120, ob[3] + 190)],
             width=2.0, color=LINEN, dot_at_end=True, opacity=0.85)
    # the leaf-and-soil smell, on the terrazzo beside the tree pit, pointing at the soil
    sb_ = B.tag(g, 'SMELL · 02', 'green leaf, damp soil', 1420, 2930)
    B.leader(g, 'Leader · smell 02 to the soil', [(sb_[2], (sb_[1] + sb_[3]) / 2 + 20), (leaf_wisp[0] - 8,
                                                                                          leaf_wisp[1] - 4)],
             width=2.0, dot_at_end=True, opacity=0.85)
    # sightline labels at the arrival points
    chip(B, g, 'LOOKING OUT  ·  TO THE STREET', DOOR_X0 + 54, 2450, 'looking out')
    cw_, ch_ = chip_size('LOOKING UP\nTO THE SKY')
    chip(B, g, 'LOOKING UP\nTO THE SKY', skx - cw_ / 2, up_chip_bottom - ch_, 'looking up')
    B.readme(TITLE)
    B.zones = zones
    return B


def chip_size(text, pad=(22, 16)):
    _, m = T.text_rgba(text, 'mono', LABEL, tracking=110, leading=1.45)
    ix0, iy0, ix1, iy1 = m['ink_box']
    return int(round(ix1 - ix0 + 2 * pad[0])), int(round(iy1 - iy0 + 2 * pad[1]))


def chip(B, parent, text, x, y, short, pad=(22, 16)):
    """A small paper label (mono caps only) with its own shadow, in its own group."""
    from psdkit import Group
    g = Group(f'Tag · {short}', opened=False)
    parent.add(g)
    rgba, m = T.text_rgba(text, 'mono', LABEL, tracking=110, leading=1.45)
    ix0, iy0, ix1, iy1 = m['ink_box']
    w, h = chip_size(text, pad)
    x, y = int(round(x)), int(round(y))
    rng = np.random.default_rng(len(text))
    paper = C.solid(h, w, '#F4EEE2')
    paper[..., :3] *= (1 + 0.012 * rng.standard_normal((h, w, 1))).astype(np.float32)
    B.shadow(g, f'Shadow · label {short}', np.ones((h, w), np.float32), x, y, depth=12, opacity=0.36)
    B.px(g, f'Paper · label {short}', np.clip(paper, 0, 1), x, y)
    ox, oy = m['anchors']['baseline_left']
    B.text(g, text, 'mono', LABEL, x + pad[0] - ix0 + ox, y + pad[1] - iy0 + oy, tracking=110, leading=1.45,
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


def measure(comp, zones):
    """CIELab statistics per zone (L*, mean per-pixel C*, hue of the mean a*b*), as the reviewers measure."""
    lab = cv2.cvtColor(np.ascontiguousarray(comp.astype(np.float32)), cv2.COLOR_RGB2LAB)
    A_, B_ = lab[..., 1], lab[..., 2]
    for nm, m in zones.items():
        if nm.startswith('lens') or nm.startswith('void ring'):
            m = m & (A_ >= -5)
        if not m.any():
            continue
        h = np.degrees(np.arctan2(B_[m].mean(), A_[m].mean())) % 360
        print(f'  {nm:30s} L*={lab[..., 0][m].mean():5.1f}  C*={np.hypot(A_[m], B_[m]).mean():5.1f}  h={h:4.0f}'
              f'  n={int(m.sum())}')
    fz = zones.get('facade blocks outside disc')
    if fz is not None:
        yy = np.arange(H)[:, None]
        for nm, band in (('facade upper courses', yy < FAC_Y0 + 450), ('facade lower courses', yy > FLOOR_Y - 500)):
            m = fz & band
            h = np.degrees(np.arctan2(B_[m].mean(), A_[m].mean())) % 360
            print(f'  {nm:30s} L*={lab[..., 0][m].mean():5.1f}  C*={np.hypot(A_[m], B_[m]).mean():5.1f}  h={h:4.0f}')
    del lab


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
    mx = np.clip(comp * 255 + 0.5, 0, 255).astype(np.uint8).max(-1)
    print(f'  crushed (< 25) on the sheet: {100 * float((mx < 25).mean()):5.2f} %')


CROPS = {
    'trunk': (1950, 2350, 2650, 3420),
    'lens_street': (2600, 1150, 3500, 2150),
    'door': (3700, 1050, 4800, 2950),
    'hem_centre': (1700, 0, 3100, 900),
    'near_left': (0, 0, 1300, 900),
    'near_right': (3800, 0, 4961, 900),
    'bar_sign': (168, 1450, 1500, 2200),
    'bar_counter': (100, 2250, 1650, 2950),
    'tree_pit': (1300, 2850, 3100, 3508),
    'tags_top_right': (3200, 650, 4961, 1300),
    'twig': (2300, 600, 3300, 1500),
    'canopy_core': (1700, 650, 2900, 1650),
    'lens_bar': (1100, 1500, 1750, 2650),
    'stair': (2650, 1150, 3850, 2950),
    'title': (100, 2900, 1800, 3508),
    'facade_right': (4400, 1250, 4961, 2880),
    'valance_right': (4300, 200, 4961, 700),
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
    measure(comp, B.zones)
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
