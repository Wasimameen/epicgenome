"""outside — the view out of the restaurant: a blue-hour street, glass-block refraction, rain.

Everything is procedural (fixed seeds) except the pedestrians, which are luminance-keyed from
assets/gen/diners_silhouettes.png, and the scenes refracted through the glass blocks
(assets/gen/cabins_row.png, assets/gen/void_lookup_B.png, the street built here).

Public functions
----------------
build_street(out_dir)                      blue-hour street (5400x3800) + its 14 RGBA layers
composite_layers(layers)                   exact psdkit-compatible recombination of those layers
glassblock_refract(scene_rgb, cols, rows, block_px, mortar_px, seed, tint, ...)
                                           a wavy pressed-glass block wall refracting a scene
grade_blue_hour(rgb)                       cool violet-blue grade that keeps warm points amber
rain_on_glass(w, h, seed)                  RGBA overlay of fine droplets + a few runs
key_silhouettes()                          the diners silhouettes as clean RGBA cut-outs
build()                                    regenerate every asset + index.json + contact sheet

All colour work that involves light (blur, bloom, glow, refraction) is done in linear light and
converted to sRGB at the end.  Street layers are authored at half resolution (everything out
there is soft-focus) and upscaled + grained at full resolution.
"""
from __future__ import annotations

import json
import os
import time

import cv2
import numpy as np
from PIL import Image

import psdkit
from psdkit import hex_rgb

Image.MAX_IMAGE_PIXELS = None
cv2.setNumThreads(2)

F32 = np.float32
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'assets', 'outside')
SCRATCH = os.path.join(ROOT, 'build', 'outside')
PREVIEW = os.path.join(ROOT, 'build', 'preview', 'outside')
CONTACT = os.path.join(ROOT, 'build', 'contact', 'outside.jpg')


def P(*parts):
    return os.path.join(ROOT, *parts)


# =========================================================================== #
# colour / maths helpers
# =========================================================================== #

def srgb_to_lin(x):
    x = np.asarray(x, F32)
    return np.where(x <= 0.04045, x / 12.92, np.power((np.maximum(x, 0) + 0.055) / 1.055, 2.4)).astype(F32)


def lin_to_srgb(x):
    x = np.clip(np.asarray(x, F32), 0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055).astype(F32)


def lin(c, scale=1.0):
    """'#RRGGBB' (sRGB) -> linear RGB float32 triple (times scale)."""
    return srgb_to_lin(np.array(hex_rgb(c), F32) / 255.0) * F32(scale)


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, F32) - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def mixv(a, b, t):
    return a + (b - a) * t


def lum(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def q8(a):
    return psdkit._q8(a)


def value_noise(h, w, cx, cy=None, rng=None):
    """Smooth value noise in 0..1 with cell size cx (horizontal) x cy (vertical) pixels."""
    cy = cx if cy is None else cy
    cx, cy = max(1, int(round(cx))), max(1, int(round(cy)))
    gh, gw = h // cy + 4, w // cx + 4
    g = rng.random((gh, gw), dtype=F32)
    up = cv2.resize(g, (gw * cx, gh * cy), interpolation=cv2.INTER_CUBIC)
    return np.ascontiguousarray(up[cy:cy + h, cx:cx + w])


def fbm(h, w, cell, octaves, rng, gain=0.5, aniso=1.0):
    """Fractal value noise, z-normalised (mean 0, std 1)."""
    tot = np.zeros((h, w), F32)
    amp = 1.0
    for i in range(octaves):
        c = cell / (2 ** i)
        if c < 1.5:
            break
        tot += F32(amp) * value_noise(h, w, c * aniso, c, rng)
        amp *= gain
    tot -= tot.mean()
    tot /= max(1e-6, float(tot.std()))
    return tot


def gblur(img, sigma, sy=None):
    sy = sigma if sy is None else sy
    if sigma <= 0 and sy <= 0:
        return img
    kx = int(sigma * 3) * 2 + 1 if sigma > 0 else 1
    ky = int(sy * 3) * 2 + 1 if sy > 0 else 1
    return cv2.GaussianBlur(img, (kx, ky), sigmaX=max(sigma, 1e-3), sigmaY=max(sy, 1e-3),
                            borderType=cv2.BORDER_REFLECT)


def disc_kernel(r, rim=0.0):
    """Anti-aliased lens disc (optionally with a brighter rim, like real bokeh)."""
    n = int(np.ceil(r)) + 1
    yy, xx = np.mgrid[-n:n + 1, -n:n + 1].astype(F32)
    d = np.sqrt(xx * xx + yy * yy)
    k = np.clip(r + 0.5 - d, 0, 1)
    if rim:
        k = k * (1 + rim * smoothstep(r * 0.55, r, d))
    return (k / k.sum()).astype(F32)


def lens_blur(img, r, rim=0.0):
    if r <= 0.35:
        return img
    return cv2.filter2D(img, -1, disc_kernel(r, rim), borderType=cv2.BORDER_REFLECT)


def box_cov(a, b, start, n):
    """Coverage of pixels [start, start+n) by the real interval [a, b)."""
    p = np.arange(start, start + n, dtype=F32)
    return np.clip(np.minimum(p + 1, b) - np.maximum(p, a), 0, 1)


def save_rgba(arr_u8, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(arr_u8, 'RGBA' if arr_u8.shape[2] == 4 else 'RGB').save(path, compress_level=6)


def preview(img, name, max_side=1600, bg='#EFE6D6', quality=88):
    """Write a downscaled JPEG preview (float 0..1 or uint8, RGB or RGBA flattened on bg)."""
    a = np.asarray(img)
    if a.dtype != np.uint8:
        a = q8(a)
    if a.ndim == 2:
        a = np.dstack([a] * 3)
    if a.shape[2] == 4:
        al = a[..., 3:4].astype(F32) / 255
        b = np.array(hex_rgb(bg), F32)
        a = (a[..., :3].astype(F32) * al + b * (1 - al) + 0.5).astype(np.uint8)
    h, w = a.shape[:2]
    s = max_side / max(h, w)
    if s < 1:
        a = cv2.resize(a, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
    path = os.path.join(PREVIEW, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(a).save(path, quality=quality)
    return path


# =========================================================================== #
# pedestrians: luminance key of assets/gen/diners_silhouettes.png
# =========================================================================== #

# connected components of the source (x, y, w, h) and the y of the feet / floor
SIL_BOXES = {
    'couple_table': (30, 520, 980, 775),
    'waiter': (986, 295, 500, 990),
    'man': (1515, 318, 245, 970),
    'woman': (1773, 368, 254, 918),
    'woman_table': (2054, 564, 665, 734),
}
SIL_FEET_Y = 1276          # common floor line of all figures in the source
_SIL_CACHE = {}


def key_silhouettes():
    """Key the dark figures off the near-white backdrop -> {name: float RGBA (straight)}.

    alpha = max(soft luminance key, eroded solid core); the light shirt of the waiter is kept
    opaque by the core term.  RGB keeps the figure's own (dark) tones for optional use."""
    if _SIL_CACHE:
        return _SIL_CACHE
    im = np.asarray(Image.open(P('assets', 'gen', 'diners_silhouettes.png')).convert('RGB'), F32) / 255
    L = lum(srgb_to_lin(im))
    L = lin_to_srgb(L)
    bg = cv2.medianBlur((L * 255).astype(np.uint8), 31).astype(F32) / 255
    bg = np.maximum(bg, 0.9)
    soft = np.clip((bg - L - 0.01) / (bg - 0.30), 0, 1)
    core = (L < 0.80).astype(np.uint8)
    core = cv2.erode(core, np.ones((3, 3), np.uint8), iterations=2).astype(F32)
    alpha = np.maximum(soft, core)
    # the faint contact shadow under the feet is not part of the figures
    alpha[SIL_FEET_Y - 4:] = core[SIL_FEET_Y - 4:]
    for name, (x, y, w_, h_) in SIL_BOXES.items():
        a = alpha[y:y + h_, x:x + w_].copy()
        # keep only the components that belong to this box (drop neighbours' fragments)
        n, lab, st, _ = cv2.connectedComponentsWithStats((a > 0.02).astype(np.uint8), connectivity=8)
        big = st[1:, 4].max() if n > 1 else 0
        keep = np.zeros(n, bool)
        for i in range(1, n):
            touches = st[i, 0] == 0 or st[i, 0] + st[i, 2] >= w_
            if st[i, 4] > 0.04 * big and not (touches and st[i, 4] < 0.2 * big):
                keep[i] = True
        a *= keep[lab]
        rgb = im[y:y + h_, x:x + w_]
        _SIL_CACHE[name] = (np.dstack([rgb, a]).astype(F32), SIL_FEET_Y - y)
    # a pedestrian variant of the waiter without the tray (tray = right of the raised hand)
    wa, fy = _SIL_CACHE['waiter']
    wa = wa.copy()
    yy, xx = np.mgrid[0:wa.shape[0], 0:wa.shape[1]]
    wa[..., 3] *= ~(((xx > 262) & (yy > 195) & (yy < 288)) | ((xx > 348) & (yy < 318)))
    _SIL_CACHE['walker'] = (wa, fy)
    return _SIL_CACHE


def silhouette_alpha(name, height_px, flip=False):
    """Alpha of a silhouette scaled so the standing height is height_px; returns (a, feet_y)."""
    rgba, fy = key_silhouettes()[name]
    a = rgba[..., 3]
    ref = 980.0                                   # standing figure height in the source (px)
    sc = height_px / ref
    out = cv2.resize(a, (max(1, round(a.shape[1] * sc)), max(1, round(a.shape[0] * sc))),
                     interpolation=cv2.INTER_AREA)
    if flip:
        out = out[:, ::-1]
    return np.ascontiguousarray(out), fy * sc


# =========================================================================== #
# A — BLUE-HOUR STREET
# =========================================================================== #
#
# Camera: seated diner (eye 1.3 m) looking straight across the street, focal 3600 px.
# A point at depth D (m) and height h (m) projects to y = HZ - FOC * (h - EYE) / D.
# Depths: opposite facades 55 m, far kerb ~50 m, tram on the far track 25 m,
# mid skyline ~220 m, far skyline ~700 m.  Vanishing point (2700, HZ).

SW, SH = 5400, 3800
K = 0.5                      # internal render scale of the street layers
HZ, EYE, FOC = 2250.0, 1.3, 3600.0
VPX = 2700.0
D_FAC, D_KERB, D_TRAM, D_LAMP, D_TREE, D_FIG = 55.0, 50.0, 25.0, 50.5, 52.0, 53.0
LENS_R = 7.0                 # soft-focus disc radius in full-res px (scene out of focus)

STREET_ORDER = [  # bottom -> top; (name, blend)
    ('sky', 'normal'),
    ('buildings_far', 'normal'),
    ('buildings_near', 'normal'),
    ('ground', 'normal'),
    ('windows_lights', 'screen'),
    ('street_glow', 'screen'),
    ('reflections', 'screen'),
    ('mist', 'screen'),
    ('trees', 'normal'),
    ('lamps', 'normal'),
    ('lamp_halos', 'screen'),
    ('figures', 'normal'),
    ('tram', 'normal'),
    ('bokeh', 'screen'),
]


def y_at(D, h):
    """Full-res image y of a point h metres high at depth D metres."""
    return HZ - FOC * (h - EYE) / D


def y_ground(D):
    return HZ + FOC * EYE / D


def depth_of_row(y):
    """Depth (m) of the ground plane at full-res image row(s) y (> HZ)."""
    return FOC * EYE / np.maximum(np.asarray(y, F32) - HZ, 1e-3)


class Layer:
    """Premultiplied linear-light RGBA at internal resolution (K)."""

    def __init__(self, h, w):
        self.rgb = np.zeros((h, w, 3), F32)
        self.a = np.zeros((h, w), F32)

    def paint(self, cov, color, y0=0, x0=0, alpha=1.0):
        """Normal-blend a colour (lin RGB triple or HxWx3) through coverage cov at (y0, x0)."""
        h, w = cov.shape
        sl = (slice(y0, y0 + h), slice(x0, x0 + w))
        c = np.clip(cov * F32(alpha), 0, 1)
        col = np.asarray(color, F32)
        if col.ndim == 1:
            col = col[None, None, :]
        self.rgb[sl] = self.rgb[sl] * (1 - c[..., None]) + col * c[..., None]
        self.a[sl] = self.a[sl] * (1 - c) + c

    def over(self, other):
        """Composite another premultiplied layer on top of this one."""
        t = 1 - other.a
        self.rgb = other.rgb + self.rgb * t[..., None]
        self.a = other.a + self.a * t

    def blur(self, r, rim=0.0):
        st = np.dstack([self.rgb, self.a])
        st = lens_blur(st, r, rim)
        self.rgb, self.a = np.ascontiguousarray(st[..., :3]), np.ascontiguousarray(st[..., 3])

    def gblur(self, sx, sy=None):
        st = gblur(np.dstack([self.rgb, self.a]), sx, sy)
        self.rgb, self.a = np.ascontiguousarray(st[..., :3]), np.ascontiguousarray(st[..., 3])


def _bbox_of(pts_list, k, shape, pad):
    a = np.concatenate([np.asarray(p, np.float64).reshape(-1, 2) for p in pts_list]) * k
    x0 = max(0, int(np.floor(a[:, 0].min())) - pad)
    y0 = max(0, int(np.floor(a[:, 1].min())) - pad)
    x1 = min(shape[1], int(np.ceil(a[:, 0].max())) + pad + 1)
    y1 = min(shape[0], int(np.ceil(a[:, 1].max())) + pad + 1)
    return x0, y0, x1, y1


def _aa_mask(shape, polys, k=K):
    """Anti-aliased union of polygons given in full-res coords, rendered at scale k."""
    out = np.zeros(shape, F32)
    if not len(polys):
        return out
    x0, y0, x1, y1 = _bbox_of(polys, k, shape, 2)
    if x1 <= x0 or y1 <= y0:
        return out
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    off = np.array([x0, y0], np.float64)
    pts = [np.round((np.asarray(p, np.float64) * k - off) * 16).astype(np.int32) for p in polys]
    cv2.fillPoly(m, pts, 255, lineType=cv2.LINE_AA, shift=4)
    out[y0:y1, x0:x1] = m.astype(F32) / 255
    return out


def _aa_lines(shape, segs, width, k=K, ss=4):
    """Anti-aliased polylines (full-res coords, width in full-res px) at scale k.
    Drawn supersampled inside the segments' bounding box, then area-downsampled."""
    out = np.zeros(shape, F32)
    if not len(segs):
        return out
    pad = int(width * k) + 3
    x0, y0, x1, y1 = _bbox_of(segs, k, shape, pad)
    if x1 <= x0 or y1 <= y0:
        return out
    m = np.zeros(((y1 - y0) * ss, (x1 - x0) * ss), np.uint8)
    th = max(1, int(round(width * k * ss)))
    off = np.array([x0, y0], np.float64)
    for sg in segs:
        p = np.round((np.asarray(sg, np.float64) * k - off) * ss * 16).astype(np.int32)
        cv2.polylines(m, [p], False, 255, thickness=th, lineType=cv2.LINE_AA, shift=4)
    out[y0:y1, x0:x1] = cv2.resize(m.astype(F32) / 255, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    return out


# --------------------------------------------------------------------------- #
# sky
# --------------------------------------------------------------------------- #

SKY_STOPS = [(0, '#151A30'), (380, '#1F2641'), (820, '#2B3556'), (1180, '#3A4669'),
             (1450, '#4A4D75'), (1640, '#5A4E7A'), (1820, '#715A7E'), (1960, '#8C687F'),
             (2090, '#A87B7C'), (2200, '#B98A7A'), (2600, '#BE8F7B')]


def sky_column(yf):
    ys = np.array([s[0] for s in SKY_STOPS], F32)
    cols = np.stack([lin(s[1]) for s in SKY_STOPS])
    return np.stack([np.interp(yf, ys, cols[:, c]) for c in range(3)], -1).astype(F32)


def street_sky(rng):
    h, w = int(SH * K), int(SW * K)
    yf = (np.arange(h, dtype=F32) + 0.5) / K
    xf = (np.arange(w, dtype=F32) + 0.5) / K
    col = sky_column(yf)[:, None, :] * np.ones((1, w, 1), F32)
    # afterglow is brighter towards the left (west), city glow lifts the low sky
    X, Y = np.meshgrid(xf, yf)
    glow = 1 + 0.16 * np.exp(-((X - 300) / 3200) ** 2) * smoothstep(900, 2100, Y)
    col *= glow[..., None]
    # thin stratus streaks: dark against the upper sky, warm-lit near the band
    n = fbm(h, w, 900 * K, 6, rng, gain=0.55, aniso=5.0)
    n2 = fbm(h, w, 260 * K, 4, rng, gain=0.5, aniso=3.0)
    dens = smoothstep(0.35, 1.9, n + 0.45 * n2) * smoothstep(150, 700, Y) * (1 - smoothstep(1650, 2050, Y))
    dens *= 0.55
    cloud_hi = lin('#272D49')
    cloud_lo = lin('#8A6A86')
    ccol = mixv(cloud_hi[None, None], cloud_lo[None, None], smoothstep(700, 1800, Y)[..., None])
    col = mixv(col, ccol, dens[..., None])
    # very soft large mottling so the gradient never looks digital
    m = fbm(h, w, 1400 * K, 3, rng)
    col *= (1 + 0.025 * m)[..., None]
    L = Layer(h, w)
    L.rgb = gblur(col, 2.0)
    L.a[:] = 1
    return L


# --------------------------------------------------------------------------- #
# skylines (far + mid depth)
# --------------------------------------------------------------------------- #

def _skyline_polys(rng, D, x_from, x_to, h_choices, w_range, tower_p=0.15, tower_h=(60, 160),
                   special=()):
    """Return list of (polygon, top_y, x0, x1) for a skyline band at depth D."""
    s = FOC / D
    yb = y_ground(D) + 20
    out = []
    x = x_from
    while x < x_to:
        wm = rng.uniform(*w_range)
        if rng.random() < tower_p:
            hm = rng.uniform(*tower_h)
            wm *= rng.uniform(0.6, 1.0)
        else:
            hm = rng.choice(h_choices) + rng.uniform(-3, 3)
        x0, x1 = x, x + wm * s
        yt = y_at(D, hm)
        style = rng.random()
        pts = [(x0, yb)]
        if style < 0.12 and hm < 50:            # pitched roof seen side-on
            ridge = yt - rng.uniform(3, 7) * s
            pts += [(x0, yt), ((x0 + x1) / 2, ridge), (x1, yt)]
        elif style < 0.30:                    # setback / stepped top
            inset = (x1 - x0) * rng.uniform(0.12, 0.3)
            step = rng.uniform(3, 8) * s
            pts += [(x0, yt), (x0 + inset, yt), (x0 + inset, yt - step), (x1 - inset, yt - step),
                    (x1 - inset, yt), (x1, yt)]
        elif style < 0.42:                    # rooftop plant boxes
            bx0 = x0 + (x1 - x0) * rng.uniform(0.1, 0.5)
            bx1 = bx0 + (x1 - x0) * rng.uniform(0.15, 0.35)
            bh = rng.uniform(2, 4.5) * s
            pts += [(x0, yt), (bx0, yt), (bx0, yt - bh), (bx1, yt - bh), (bx1, yt), (x1, yt)]
        else:
            pts += [(x0, yt), (x1, yt)]
        pts += [(x1, yb)]
        out.append((pts, yt, x0, x1))
        # thin mast on some towers
        if hm > 55 and rng.random() < 0.45:
            mx = (x0 + x1) / 2 + rng.uniform(-0.2, 0.2) * (x1 - x0)
            mh = rng.uniform(6, 20) * s
            mw = max(1.6, 0.6 * s)
            out.append(([(mx - mw / 2, yt + 2), (mx - mw / 2, yt - mh), (mx + mw / 2, yt - mh),
                         (mx + mw / 2, yt + 2)], yt - mh, mx - mw, mx + mw))
        x = x1 + (0 if rng.random() < 0.7 else rng.uniform(1, 6) * s)
    for sp in special:
        out.append(sp)
    return out


def _spire(cx, D, h_base, h_tip, w_m):
    s = FOC / D
    yb = y_ground(D) + 20
    yt = y_at(D, h_base)
    ytip = y_at(D, h_tip)
    hw = w_m * s / 2
    pts = [(cx - hw, yb), (cx - hw, yt), (cx - hw * 0.7, yt), (cx, ytip), (cx + hw * 0.7, yt),
           (cx + hw, yt), (cx + hw, yb)]
    return (pts, ytip, cx - hw, cx + hw)


def _dome(cx, D, h_base, w_m):
    s = FOC / D
    yb = y_ground(D) + 20
    yt = y_at(D, h_base)
    r = w_m * s / 2
    t = np.linspace(np.pi, 2 * np.pi, 40)
    arc = [(cx + r * np.cos(a), yt + 0.9 * r * np.sin(a)) for a in t]
    lant = [(cx - r * 0.12, yt - 0.9 * r), (cx - r * 0.12, yt - 1.25 * r), (cx, yt - 1.45 * r),
            (cx + r * 0.12, yt - 1.25 * r), (cx + r * 0.12, yt - 0.9 * r)]
    arc_l = [p for p in arc if p[0] <= cx - r * 0.12]
    arc_r = [p for p in arc if p[0] >= cx + r * 0.12]
    pts = [(cx - r * 1.05, yb), (cx - r * 1.05, yt + 2)] + arc_l + lant + arc_r + \
          [(cx + r * 1.05, yt + 2), (cx + r * 1.05, yb)]
    return (pts, yt - 1.45 * r, cx - r * 1.05, cx + r * 1.05)


def street_skylines(rng, sky):
    """buildings_far: two depth bands (700 m and 220 m) + their tiny lit windows (returned)."""
    h, w = sky.a.shape
    yf = (np.arange(h, dtype=F32) + 0.5) / K
    Y = yf[:, None] * np.ones((1, w), F32)
    skycol = sky.rgb  # opaque, so premul == straight
    layer = Layer(h, w)
    win_far = np.zeros((h, w, 3), F32)
    bands = [
        # depth, haze (0 = building colour, 1 = sky), building colour, heights, widths, towers
        dict(D=600.0, haze=0.60, col='#262A44', hs=[45, 55, 62, 70, 80], wr=(22, 55), tp=0.30,
             th=(120, 250), special=[_spire(2350, 600.0, 70, 175, 14), _dome(4180, 600.0, 62, 40)],
             seed=11),
        dict(D=200.0, haze=0.33, col='#1D2134', hs=[30, 36, 42, 48, 55], wr=(14, 32), tp=0.16,
             th=(60, 78), special=[], seed=12),
    ]
    for b in bands:
        r = np.random.default_rng(b['seed'])
        polys = _skyline_polys(r, b['D'], -150, SW + 150, b['hs'], b['wr'], b['tp'], b['th'],
                               b['special'])
        m = _aa_mask((h, w), [p[0] for p in polys])
        # building colour: hazed toward the sky colour at that height, lighter + warmer near the
        # base (city glow / mist), a faint darker top edge so silhouettes read crisply
        base = lin(b['col'])
        yg = y_ground(b['D'])
        mist = smoothstep(yg - 900 * (220 / b['D']) ** 0.3, yg, Y)
        haze = np.clip(b['haze'] + 0.35 * mist, 0, 0.92)
        city = lin('#B98A7A') * 0.55
        col = mixv(base[None, None], skycol, haze[..., None])
        col = col + city[None, None] * (mist ** 2 * 0.35)[..., None]
        # per-building tonal variation (each block catches the afterglow a little differently)
        var = np.ones((h, w), F32)
        for pts, yt, x0, x1 in polys:
            ix0, ix1 = max(0, int(x0 * K)), min(w, int(np.ceil(x1 * K)))
            if ix1 > ix0:
                var[:, ix0:ix1] = r.uniform(0.88, 1.10)
        var = gblur(var, 1.0, 0.1)
        col *= var[..., None]
        L = Layer(h, w)
        L.paint(m, col)
        layer.over(L)
        win_far *= (1 - m)[..., None]           # this band hides the windows of the band behind
        # tiny lit windows: regular grids inside each building rect, sparse + dim
        s = FOC / b['D']
        for pts, yt, x0, x1 in polys:
            if x1 - x0 < 3 * s:
                continue
            fl = 3.3 * s
            bay = r.uniform(2.6, 3.6) * s
            ww, wh = max(1.4, 0.75 * s), max(1.8, 1.35 * s)
            p_lit = r.uniform(0.03, 0.14) * (1.3 if b['D'] < 300 else 1.0)
            ys = np.arange(yt + fl * 0.8, yg - fl * 1.2, fl)
            xs = np.arange(x0 + bay * 0.5, x1 - bay * 0.4, bay)
            if not len(ys) or not len(xs):
                continue
            lit = r.random((len(ys), len(xs))) < p_lit
            # lit windows cluster in vertical/horizontal runs (offices, flats)
            if r.random() < 0.35:              # whole office floors left on
                lit |= (r.random(len(ys)) < 0.10)[:, None] & (r.random((len(ys), len(xs))) < 0.8)
            for iy, wy in enumerate(ys):
                for ix, wx in enumerate(xs):
                    if not lit[iy, ix]:
                        continue
                    warm = r.random() < 0.75
                    c = lin('#FFB45E') if warm else lin('#CFE0FF')
                    inten = r.uniform(0.05, 0.22) * (1 - 0.6 * b['haze'])
                    X0, Y0, X1, Y1 = wx * K, wy * K, (wx + ww) * K, (wy + wh) * K
                    ix0, iy0 = int(X0), int(Y0)
                    cx = box_cov(X0, X1, ix0, int(np.ceil(X1)) - ix0 + 1)
                    cy = box_cov(Y0, Y1, iy0, int(np.ceil(Y1)) - iy0 + 1)
                    if iy0 < 0 or ix0 < 0 or iy0 + len(cy) > h or ix0 + len(cx) > w:
                        continue
                    win_far[iy0:iy0 + len(cy), ix0:ix0 + len(cx)] += \
                        (np.outer(cy, cx)[..., None] * c * inten) * m[iy0:iy0 + len(cy), ix0:ix0 + len(cx), None]
    return layer, win_far


# --------------------------------------------------------------------------- #
# near facades (opposite side of the street, D = 55 m) + the side street
# --------------------------------------------------------------------------- #

S_FAC = FOC / D_FAC                     # px per metre on the facades
GF_H, FL_H = 4.2, 3.2                   # ground-floor / upper-floor heights (m)
LAMP_X = [430.0, 2790.0, 5060.0]        # street lamps on the far kerb
TREE_X = [1560.0, 3960.0, 5330.0]       # street trees on the far sidewalk
GAP = (2960.0, 3500.0)                  # side street opening

E_SKY = lin('#4A62AA') * 0.16           # blue-hour sky light on a vertical wall
E_WARM = lin('#FFB06A') * 0.36          # shop / street uplight at ground-floor level
E_LAMP = lin('#FFC27E') * 0.30

NEAR_BUILDINGS = [
    dict(x0=-60, x1=1180, floors=4, roof='mansard', style='stone', col='#BCB09A', bay=3.3,
         balcony=(1, 4), shops=[(0.04, 0.47, 'bakery'), (0.53, 0.96, 'closed')]),
    dict(x0=1180, x1=2120, floors=2, roof='mansard', style='brick', col='#8C6556', bay=3.0,
         balcony=(), shops=[(0.06, 0.94, 'wine')]),
    dict(x0=2120, x1=2960, floors=3, roof='flat', style='stucco', col='#A4AA9C', bay=3.1,
         balcony=(3,), shops=[(0.05, 0.60, 'cafe'), (0.66, 0.95, 'door')]),
    dict(x0=3500, x1=4480, floors=3, roof='mansard', style='stone', col='#C2B59E', bay=3.4,
         balcony=(1,), shops=[(0.05, 0.95, 'restaurant')]),
    dict(x0=4480, x1=5470, floors=4, roof='flat', style='shutters', col='#C3A27A', bay=3.2,
         balcony=(), shops=[(0.04, 0.52, 'books'), (0.58, 0.96, 'cafe')]),
]


def facade_light(Y, X, facing='front'):
    """Illumination (linear RGB, HxWx3) on the facade plane at full-res coords (Y, X)."""
    hm = (HZ - Y) * D_FAC / FOC + EYE                      # metres above the pavement
    xm = (X - VPX) * D_FAC / FOC                            # metres along the street
    up = np.exp(-np.maximum(hm - 3.4, 0) / 2.4) * smoothstep(-0.3, 2.0, hm)
    lamp = np.zeros_like(hm)
    for lx in LAMP_X:
        dx = xm - (lx - VPX) * D_FAC / FOC
        d2 = 25.0 + dx * dx + (hm - LANTERN_H) ** 2           # lamp 5 m in front of the wall
        lamp = lamp + 125.0 / d2 ** 1.5                         # cosine x inverse square
    sky = 1.0
    if facing == 'up':          # ledges, sills, cornice tops: open to the whole sky
        sky, up = 2.3, up * 0.25
    elif facing == 'down':      # soffits: only bounce + uplight
        sky, up = 0.35, up * 1.25
    return (E_SKY[None, None] * sky + E_WARM[None, None] * up[..., None] +
            E_LAMP[None, None] * (0.75 * lamp)[..., None])


class NearCtx:
    """Shared state while drawing the near facades."""

    def __init__(self, h, w):
        self.h, self.w = h, w
        self.layer = Layer(h, w)
        self.windows = []          # dicts: x0,y0,x1,y1 (full res), kind, floor, building
        self.shops = []            # dicts: x0,y0,x1,y1, kind, fascia (y0, y1), awning
        self.occl = np.zeros((h, w), F32)   # railings etc. in front of windows (hide emission)
        self.rng = None

    # rect helpers in full-res coords --------------------------------------
    def cov(self, x0, y0, x1, y1):
        X0, Y0, X1, Y1 = x0 * K, y0 * K, x1 * K, y1 * K
        ix0, iy0 = max(0, int(np.floor(X0))), max(0, int(np.floor(Y0)))
        ix1, iy1 = min(self.w, int(np.ceil(X1))), min(self.h, int(np.ceil(Y1)))
        if ix1 <= ix0 or iy1 <= iy0:
            return None
        c = np.outer(box_cov(Y0, Y1, iy0, iy1 - iy0), box_cov(X0, X1, ix0, ix1 - ix0))
        return iy0, ix0, c

    def grid(self, iy0, ix0, hh, ww):
        ys = (np.arange(iy0, iy0 + hh, dtype=F32) + 0.5) / K
        xs = (np.arange(ix0, ix0 + ww, dtype=F32) + 0.5) / K
        return np.meshgrid(ys, xs, indexing='ij')

    def rect(self, x0, y0, x1, y1, albedo, facing='front', mult=1.0, alpha=1.0, occl=False):
        r = self.cov(x0, y0, x1, y1)
        if r is None:
            return
        iy0, ix0, c = r
        Y, X = self.grid(iy0, ix0, *c.shape)
        alb = albedo if isinstance(albedo, np.ndarray) and albedo.ndim == 3 else np.asarray(albedo, F32)
        col = alb * facade_light(Y, X, facing) * (mult[..., None] if isinstance(mult, np.ndarray) else mult)
        self.layer.paint(c, col, iy0, ix0, alpha)
        if occl:
            sl = (slice(iy0, iy0 + c.shape[0]), slice(ix0, ix0 + c.shape[1]))
            self.occl[sl] = np.maximum(self.occl[sl], c * alpha)

    def emit_rect(self, x0, y0, x1, y1, color, alpha=1.0):
        """Paint a self-lit / unlit-glass colour (no facade lighting)."""
        r = self.cov(x0, y0, x1, y1)
        if r is None:
            return
        iy0, ix0, c = r
        self.layer.paint(c, color, iy0, ix0, alpha)

    def ledge(self, x0, x1, y, depth_m, albedo, shadow_m=None):
        """A projecting horizontal ledge at full-res row y: lit top line, front face, shadow."""
        s = S_FAC
        top = max(1.2, 0.05 * s)
        face = depth_m * s
        sh = (shadow_m if shadow_m is not None else depth_m * 1.4) * s
        self.rect(x0, y - top, x1, y, albedo, 'up')
        self.rect(x0, y, x1, y + face, albedo, 'front', 0.92)
        r = self.cov(x0, y + face, x1, y + face + sh)
        if r is not None:
            iy0, ix0, c = r
            t = np.linspace(0, 1, c.shape[0], dtype=F32)[:, None]
            Y, X = self.grid(iy0, ix0, *c.shape)
            col = np.asarray(albedo, F32) * facade_light(Y, X, 'down') * 0.6
            self.layer.paint(c * (1 - t) ** 1.6 * 0.75, col, iy0, ix0)


def _floor_y(i, top=False):
    """Full-res y of the floor line of storey i (0 = ground floor); top=True: ceiling."""
    hm = (GF_H + FL_H * (i - 1) if i >= 1 else 0.0) + ((GF_H if i == 0 else FL_H) if top else 0.0)
    return y_at(D_FAC, hm)


def _glass(ctx, x0, y0, x1, y1):
    """Unlit window glass: reflects the twilight sky (lighter at the top) + a little street."""
    r = ctx.cov(x0, y0, x1, y1)
    if r is None:
        return
    iy0, ix0, c = r
    t = np.linspace(0, 1, c.shape[0], dtype=F32)[:, None, None]
    top = sky_column(np.array([900.0], F32))[0] * 0.42
    bot = lin('#1A1A22') * 0.9
    col = mixv(top[None, None], bot[None, None], t ** 0.8) * np.ones((1, c.shape[1], 1), F32)
    ctx.layer.paint(c, col, iy0, ix0)


def _draw_building(ctx, b, rng):
    s = S_FAC
    x0, x1 = float(b['x0']), float(b['x1'])
    nf = b['floors']
    alb = lin(b['col'])
    yg = y_ground(D_FAC)
    h_cornice = GF_H + FL_H * nf
    y_cor = y_at(D_FAC, h_cornice)
    body_top = y_cor - 0.75 * s
    # ---- body with stucco / stone / brick texture -------------------------
    r = ctx.cov(x0, body_top, x1, yg + 2)
    iy0, ix0, c = r
    Y, X = ctx.grid(iy0, ix0, *c.shape)
    hh, ww = c.shape
    tex = 1 + 0.035 * fbm(hh, ww, 60 * K, 4, rng) + 0.02 * fbm(hh, ww, 6, 2, rng)
    # weathering: soft vertical streaks darkening below sills
    tex *= 1 - 0.05 * smoothstep(0.2, 2.2, fbm(hh, ww, 120 * K, 3, rng, aniso=0.12))
    if b['style'] == 'stone':     # ashlar joints (faint horizontal coursing)
        course = 0.55 * s * K
        ph = (np.arange(hh, dtype=F32) + iy0) % course
        tex *= (1 - 0.07 * np.exp(-((ph - 0.5) / 0.7) ** 2))[:, None]
    if b['style'] == 'brick':
        course = 0.22 * s * K
        ph = (np.arange(hh, dtype=F32) + iy0) % course
        tex *= (1 - 0.10 * np.exp(-((ph - 0.5) / 0.6) ** 2))[:, None]
        tex *= 1 + 0.05 * fbm(hh, ww, 10, 2, rng, aniso=3)
    col = alb * facade_light(Y, X) * tex[..., None]
    ctx.layer.paint(c, col, iy0, ix0)
    # building edge: a hairline party-wall shadow + downpipe
    ctx.rect(x0, body_top, x0 + 0.12 * s, yg, alb, mult=0.55)
    px = x1 - 0.35 * s
    ctx.rect(px, body_top + 0.6 * s, px + 0.11 * s, yg - 0.2 * s, lin('#3A3D44'), mult=0.8)
    # ---- ground floor: shopfronts --------------------------------------
    y_gf_top = _floor_y(0, top=True)
    ctx.ledge(x0, x1, y_gf_top, 0.25, alb * 0.95)
    for (f0, f1, kind) in b['shops']:
        sx0, sx1 = x0 + (x1 - x0) * f0, x0 + (x1 - x0) * f1
        sy1 = yg - 0.08 * s
        fascia = (y_at(D_FAC, 3.95), y_at(D_FAC, 3.25))
        sy0 = fascia[1] + 0.05 * s
        # timber shopfront frame + fascia board (painted, dark)
        paint = lin(rng.choice(['#2F3A33', '#3A2B2A', '#262C36', '#40342A']))
        ctx.rect(sx0 - 0.16 * s, fascia[0], sx1 + 0.16 * s, sy1 + 0.05 * s, paint * 1.4)
        ctx.ledge(sx0 - 0.22 * s, sx1 + 0.22 * s, fascia[0], 0.08, paint * 1.6, 0.1)
        # glazing (dark; the lit interior is added by the street_glow layer)
        ctx.emit_rect(sx0, sy0, sx1, sy1, lin('#0E0F14'))
        ctx.rect(sx0, sy1 - 0.45 * s, sx1, sy1, paint * 1.3)          # stall riser
        awning = kind in ('cafe', 'restaurant', 'florist') and rng.random() < 0.9
        ctx.shops.append(dict(x0=sx0, y0=sy0, x1=sx1, y1=sy1 - 0.45 * s, kind=kind,
                              fascia=fascia, awning=awning, paint=paint))
    # piers between / beside shops in the facade material
    # ---- upper floors -----------------------------------------------------
    nb = max(1, int(round((x1 - x0) / (b['bay'] * s))))
    bayw = (x1 - x0) / nb
    for f in range(1, nf + 1):
        y_floor = _floor_y(f)
        # sill-level string course
        if b['style'] in ('stone', 'stucco') or f == 1:
            ctx.ledge(x0, x1, y_floor - 0.02 * s, 0.10, alb * 1.02, 0.18)
        win_h = 2.05 if b['style'] in ('stone', 'shutters') else 1.75
        if f == nf and b['style'] == 'stone':
            win_h = 1.75
        win_w = 1.25 if b['style'] != 'brick' else 1.1
        sill_h = 0.55 if b['style'] in ('stone', 'shutters') else 0.85
        wy1 = y_at(D_FAC, GF_H + FL_H * (f - 1) + sill_h)
        wy0 = y_at(D_FAC, GF_H + FL_H * (f - 1) + sill_h + win_h)
        for i in range(nb):
            cx = x0 + bayw * (i + 0.5)
            wx0, wx1 = cx - win_w * s / 2, cx + win_w * s / 2
            # surrounds
            if b['style'] == 'stone':
                ctx.rect(wx0 - 0.16 * s, wy0 - 0.16 * s, wx1 + 0.16 * s, wy1, alb * 1.07)
                ctx.ledge(wx0 - 0.3 * s, wx1 + 0.3 * s, wy0 - 0.22 * s, 0.07, alb * 1.08, 0.16)
            if b['style'] == 'brick':      # stone lintel + sill
                ctx.rect(wx0 - 0.1 * s, wy0 - 0.28 * s, wx1 + 0.1 * s, wy0, lin('#B9AE9B'))
            if b['style'] == 'shutters':   # open louvred shutters either side
                shc = lin(rng.choice(['#3E5A4C', '#45584A', '#5B6A5A']))
                for sx in (wx0 - 0.66 * s, wx1 + 0.04 * s):
                    r2 = ctx.cov(sx, wy0, sx + 0.62 * s, wy1)
                    if r2 is not None:
                        jy, jx, cc = r2
                        lou = 0.80 + 0.2 * np.cos((np.arange(cc.shape[0]) + jy) * 2 * np.pi / (0.11 * s * K)) ** 2
                        Yq, Xq = ctx.grid(jy, jx, *cc.shape)
                        ctx.layer.paint(cc, shc * facade_light(Yq, Xq) * lou[:, None, None], jy, jx)
            # opening: reveal shadow, dark glass, sill
            ctx.rect(wx0, wy0, wx1, wy1, alb, mult=0.45)                    # reveal
            _glass(ctx, wx0 + 0.07 * s, wy0 + 0.1 * s, wx1 - 0.07 * s, wy1 - 0.02 * s)
            ctx.rect(wx0 - 0.06 * s, wy1 - 0.02 * s, wx1 + 0.06 * s, wy1 + 0.05 * s, alb * 1.05, 'up')
            ctx.windows.append(dict(x0=wx0 + 0.07 * s, y0=wy0 + 0.1 * s, x1=wx1 - 0.07 * s,
                                    y1=wy1 - 0.02 * s, floor=f, style=b['style'],
                                    french=sill_h < 0.7))
            # balconies: stone slab + wrought-iron railing in front of the window
            if f in b['balcony']:
                full = b['style'] == 'stone' and f in (1, 4)
                bx0, bx1 = (x0 + 0.1 * s, x1 - 0.1 * s) if full else (wx0 - 0.25 * s, wx1 + 0.25 * s)
                if full and i > 0:
                    pass
                elif True:
                    ys_ = y_at(D_FAC, GF_H + FL_H * (f - 1) + 0.05)
                    ctx.ledge(bx0, bx1, ys_ - 0.04 * s, 0.16, alb * 1.05, 0.35)
                    _railing(ctx, bx0, bx1, ys_ - 0.06 * s, ys_ - 1.0 * s)
    # ---- cornice + roof ---------------------------------------------------
    ctx.ledge(x0 - 0.15 * s, x1 + 0.15 * s, y_cor - 0.05 * s, 0.45, alb * 1.05, 0.7)
    ctx.rect(x0 - 0.15 * s, body_top, x1 + 0.15 * s, y_cor - 0.05 * s, alb * 1.02)
    if b['roof'] == 'mansard':
        _mansard(ctx, b, x0, x1, body_top, nb, bayw, rng)
    else:
        # parapet + roof clutter
        ctx.rect(x0, body_top - 0.9 * s, x1, body_top, alb * 0.95)
        ctx.ledge(x0 - 0.05 * s, x1 + 0.05 * s, body_top - 0.9 * s, 0.08, alb, 0.1)
        for _ in range(rng.integers(1, 3)):
            cxx = rng.uniform(x0 + 0.15 * (x1 - x0), x1 - 0.15 * (x1 - x0))
            ww_, hh_ = rng.uniform(1.0, 3.0) * s, rng.uniform(1.2, 2.6) * s
            ctx.rect(cxx - ww_ / 2, body_top - 0.9 * s - hh_, cxx + ww_ / 2, body_top - 0.9 * s,
                     alb * 0.8)


def _railing(ctx, x0, x1, y_bot, y_top):
    """Wrought-iron railing: rails + balusters + scroll band; marks the window occluder mask."""
    s = S_FAC
    iron = lin('#121318')
    ctx.rect(x0, y_top, x1, y_top + 0.06 * s, iron, occl=True)            # handrail
    ctx.rect(x0, y_bot - 0.05 * s, x1, y_bot, iron, occl=True)            # bottom rail
    ctx.rect(x0, y_top + 0.22 * s, x1, y_top + 0.26 * s, iron, occl=True)
    r = ctx.cov(x0, y_top, x1, y_bot)
    if r is None:
        return
    iy0, ix0, c = r
    hh, ww = c.shape
    xs = (np.arange(ww, dtype=F32) + ix0 + 0.5) / K
    ys = (np.arange(hh, dtype=F32) + iy0 + 0.5) / K
    pitch = 0.13 * s
    bal = np.clip(1.3 - np.abs(((xs - x0) % pitch) - pitch / 2) / (0.018 * s * 0.5 + 0.35 / K), 0, 1)
    bal = np.clip(1.0 - (np.abs(((xs - x0) % pitch) - pitch / 2) - 0.012 * s) * K, 0, 1)
    # scroll band: a sinuous pattern between the two upper rails
    yy = (ys - y_top) / s
    sc = (yy > 0.06) & (yy < 0.22)
    scroll = np.clip(1.0 - (np.abs(np.sin((xs[None, :] - x0) / pitch * np.pi) * 0.08 -
                                   (yy[:, None] - 0.14)) - 0.012) * s * K, 0, 1) * sc[:, None]
    m = np.maximum(bal[None, :] * np.ones((hh, 1), F32), scroll) * c * 0.92
    ctx.layer.paint(m, iron, iy0, ix0)
    sl = (slice(iy0, iy0 + hh), slice(ix0, ix0 + ww))
    ctx.occl[sl] = np.maximum(ctx.occl[sl], m)


def _mansard(ctx, b, x0, x1, base_y, nb, bayw, rng):
    s = S_FAC
    hm = 3.7
    y_top = base_y - hm * s * 0.98
    inset_b, inset_t = 0.25 * s, 1.05 * s
    poly = [(x0 + inset_b, base_y + 1), (x0 + inset_t, y_top), (x1 - inset_t, y_top),
            (x1 - inset_b, base_y + 1)]
    m = _aa_mask((ctx.h, ctx.w), [poly])
    yy0, yy1 = int(y_top * K) - 2, int(base_y * K) + 3
    sub = m[yy0:yy1]
    hh = sub.shape[0]
    ys = (np.arange(yy0, yy1, dtype=F32) + 0.5) / K
    xs = (np.arange(ctx.w, dtype=F32) + 0.5) / K
    t = np.clip((ys - y_top) / (base_y - y_top), 0, 1)[:, None]
    # zinc/slate: reflects the sky near the top (shiny, tilted up), darker low down,
    # standing seams every 0.5 m
    zinc = lin('#3E4456')
    skyref = sky_column(np.full_like(ys, 600.0))[:, None, :] * 1.35
    seam = 1 - 0.18 * (np.abs(((xs - x0) % (0.5 * s)) - 0.25 * s) < 0.035 * s)[None, :]
    col = mixv(skyref * 0.42, zinc[None, None] * 0.12, t[..., None] ** 0.5) * seam[..., None]
    col = col * (1 + 0.04 * fbm(hh, ctx.w, 30, 3, rng))[..., None]
    ctx.layer.paint(sub, col, yy0, 0)
    # dormers
    for i in range(nb):
        cx = x0 + bayw * (i + 0.5)
        dw, dh = 1.15 * s, 1.75 * s
        dx0, dx1 = cx - dw / 2, cx + dw / 2
        dy1 = base_y - 0.25 * s
        dy0 = dy1 - dh
        alb = lin(b['col'])
        ctx.rect(dx0 - 0.18 * s, dy0, dx1 + 0.18 * s, dy1, alb * 0.95)
        # pediment (arched cap)
        cap = []
        for a in np.linspace(np.pi, 2 * np.pi, 24):
            cap.append((cx + (dw / 2 + 0.3 * s) * np.cos(a), dy0 + 0.05 * s + 0.45 * s * np.sin(a)))
        cm = _aa_mask((ctx.h, ctx.w), [cap + [(cx + dw / 2 + 0.3 * s, dy0 + 0.1 * s),
                                              (cx - dw / 2 - 0.3 * s, dy0 + 0.1 * s)]])
        r = ctx.cov(cx - dw, dy0 - 0.6 * s, cx + dw, dy0 + 0.2 * s)
        if r is not None:
            iy0, ix0, c = r
            sub = cm[iy0:iy0 + c.shape[0], ix0:ix0 + c.shape[1]]
            Y, X = ctx.grid(iy0, ix0, *c.shape)
            ctx.layer.paint(sub, alb * facade_light(Y, X, 'up') * 0.8, iy0, ix0)
        ctx.rect(dx0, dy0 + 0.15 * s, dx1, dy1, alb, mult=0.45)
        _glass(ctx, dx0 + 0.07 * s, dy0 + 0.22 * s, dx1 - 0.07 * s, dy1 - 0.05 * s)
        ctx.windows.append(dict(x0=dx0 + 0.07 * s, y0=dy0 + 0.22 * s, x1=dx1 - 0.07 * s,
                                y1=dy1 - 0.05 * s, floor=99, style='dormer', french=False))
    # chimney stacks with pots
    for _ in range(2):
        cx = rng.uniform(x0 + 0.15 * (x1 - x0), x1 - 0.15 * (x1 - x0))
        cw = rng.uniform(1.0, 1.8) * s
        ch = rng.uniform(1.4, 2.4) * s
        alb = lin(b['col']) * 0.8
        ctx.rect(cx - cw / 2, y_top - ch, cx + cw / 2, y_top + 2, alb)
        ctx.rect(cx - cw / 2 - 0.08 * s, y_top - ch - 0.12 * s, cx + cw / 2 + 0.08 * s, y_top - ch, alb, 'up')
        npots = max(1, int(cw / (0.35 * s)))
        for j in range(npots):
            px_ = cx - cw / 2 + (j + 0.5) * cw / npots
            ctx.rect(px_ - 0.08 * s, y_top - ch - 0.5 * s, px_ + 0.08 * s, y_top - ch - 0.1 * s,
                     lin('#8A5A44') * 0.8)


def _side_street(ctx, rng):
    """Receding facades along the right-hand side of the side street (seen through GAP).

    The wall plane sits at world X = Xw metres right of the optical axis; a point (D, h) on it
    projects to (VPX + FOC*Xw/D, y_at(D, h)).  Returns perspective quads for the windows layer
    [(quad, haze, kind)] with kind 'win' or 'shop'."""
    s = S_FAC
    Xw = (GAP[1] - VPX) / s
    px = lambda D: VPX + FOC * Xw / D
    segs, D = [], D_FAC + 13.0
    while D < 260:
        L_ = rng.uniform(10, 22)
        h_ = float(rng.choice([13.8, 17.0, 17.0, 20.2, 23.4])) + 0.7
        segs.append((D, D + L_, h_))
        D += L_
    out = []
    ys = (np.arange(ctx.h, dtype=F32) + 0.5) / K
    for (d0, d1, h_) in segs[::-1]:                       # far to near (painter's order)
        quad = [(px(d0), y_ground(d0) + 2), (px(d0), y_at(d0, h_)), (px(d1), y_at(d1, h_)),
                (px(d1), y_ground(d1) + 2)]
        m = _aa_mask((ctx.h, ctx.w), [quad])
        dm = 0.5 * (d0 + d1)
        haze = float(np.clip((dm - 55) / 260, 0, 0.7))
        alb = lin(rng.choice(['#B8AC98', '#A99F8E', '#C0A585', '#9EA39A']))
        hmz = (HZ - ys) * dm / FOC + EYE
        up = np.exp(-np.maximum(hmz - 3.4, 0) / 2.6)[:, None, None]
        lit = alb * (E_SKY * 0.6 + E_WARM * 0.85 * up) * np.ones((1, ctx.w, 1), F32)
        skyc = sky_column(np.array([1650.0], F32))[0] * 0.75
        col = mixv(lit, skyc[None, None], haze)
        ctx.layer.paint(m, col)
        # floor lines + cornice converging to the vanishing point
        lines_up, lines_dn = [], []
        nflo = int((h_ - GF_H) / FL_H)
        for f in range(nflo + 1):
            hk = GF_H + FL_H * f if f < nflo else h_ - 0.6
            lines_up.append([(px(d0), y_at(d0, hk)), (px(d1), y_at(d1, hk))])
            lines_dn.append([(px(d0), y_at(d0, hk) + 0.18 * FOC / d0), (px(d1), y_at(d1, hk) + 0.18 * FOC / d1)])
        wpx = max(1.5, 0.10 * FOC / d0)
        lm = _aa_lines((ctx.h, ctx.w), lines_up, wpx) * m
        ctx.layer.paint(lm, mixv(alb * E_SKY * 1.6, skyc, haze), 0, 0, 0.8)
        lm = _aa_lines((ctx.h, ctx.w), lines_dn, wpx * 1.3) * m
        ctx.layer.paint(lm, mixv(alb * E_SKY * 0.3, skyc * 0.9, haze), 0, 0, 0.6)
        # windows (dark recess here; lit ones are added to the windows layer)
        nb = max(1, int(round((d1 - d0) / 3.3)))
        wquads = []
        for f in range(1, nflo + 1):
            for i in range(nb):
                za = d0 + (d1 - d0) * (i + 0.32) / nb
                zb = d0 + (d1 - d0) * (i + 0.68) / nb
                ha = GF_H + FL_H * (f - 1) + 0.75
                hb = ha + 1.8
                q = [(px(za), y_at(za, hb)), (px(zb), y_at(zb, hb)), (px(zb), y_at(zb, ha)),
                     (px(za), y_at(za, ha))]
                wquads.append(q)
                out.append((q, haze, 'win'))
        if wquads:
            wm = _aa_mask((ctx.h, ctx.w), wquads)
            gl = sky_column(np.array([900.0], F32))[0] * 0.35
            ctx.layer.paint(wm, mixv(gl, skyc, haze))
        q = [(px(d0), y_ground(d0)), (px(d0), y_at(d0, 3.2)), (px(d1), y_at(d1, 3.2)),
             (px(d1), y_ground(d1))]
        out.append((q, haze, 'shop'))
    return out


def street_near(rng):
    h, w = int(SH * K), int(SW * K)
    ctx = NearCtx(h, w)
    ctx.rng = rng
    side_windows = _side_street(ctx, rng)
    for i, b in enumerate(NEAR_BUILDINGS):
        _draw_building(ctx, b, np.random.default_rng(100 + i))
    # building D's flank: the visible side wall turning into the side street
    s = S_FAC
    Xw = (GAP[1] - VPX) / s
    b = NEAR_BUILDINGS[3]
    hc = GF_H + FL_H * b['floors'] + 0.75
    d0, d1 = D_FAC, D_FAC + 13.0
    xa, xb = GAP[1], VPX + FOC * Xw / d1
    hc = hc + 3.7          # the mansard profile seen end-on
    quad = [(xa, y_ground(d0) + 2), (xa, y_at(d0, hc)), (xb, y_at(d1, hc)), (xb, y_ground(d1) + 2)]
    m = _aa_mask((h, w), [quad])
    ys = (np.arange(h, dtype=F32) + 0.5) / K
    hmz = (HZ - ys) * (d0 + 6) / FOC + EYE
    up = np.exp(-np.maximum(hmz - 3.4, 0) / 2.4)[:, None, None]
    alb = lin(b['col'])
    tex = 1 + 0.04 * fbm(h, w, 50 * K, 4, rng)
    col = alb * (E_SKY * 0.55 + E_WARM * up * 0.8) * tex[..., None]
    ctx.layer.paint(m, col)
    ctx.side_windows = side_windows
    ctx.flank = (quad, d0, d1, Xw)
    return ctx


# --------------------------------------------------------------------------- #
# lit windows (screen layer)
# --------------------------------------------------------------------------- #

WARM_WIN = ['#FF9C45', '#FFB062', '#FFA24E', '#FFC27E', '#FF9038', '#FFB873', '#FFD3A0']


def _bar(t, t0, half_px, scale_px):
    """AA bar mask across normalised coordinate t at t0 (half width in px, scale = px per unit)."""
    return np.clip(half_px + 0.5 - np.abs(t - t0) * scale_px, 0, 1)


def _window_glazing(u, v, wpx, hpx, style):
    """Frame + glazing-bar mask (1 = opaque bar) for a window in local coords."""
    fr = 0.055 * S_FAC * K                     # frame width in internal px
    bars = np.zeros_like(u)
    edge = np.minimum(np.minimum(u * wpx, (1 - u) * wpx), np.minimum(v * hpx, (1 - v) * hpx))
    bars = np.maximum(bars, np.clip(fr + 0.5 - edge, 0, 1))
    bars = np.maximum(bars, _bar(u, 0.5, fr * 0.8, wpx))
    gb = fr * 0.45
    if style in ('stone', 'shutters', 'dormer'):
        for t in (1 / 3, 2 / 3):
            bars = np.maximum(bars, _bar(v, t, gb, hpx))
    elif style == 'brick':
        bars = np.maximum(bars, _bar(v, 0.5, fr * 0.7, hpx))
        for t in (0.25, 0.75):
            bars = np.maximum(bars, _bar(u, t, gb, wpx))
    else:
        bars = np.maximum(bars, _bar(v, 0.22, fr * 0.7, hpx))
    return bars


def _interior(u, v, rng, kind, wpx, hpx):
    """Brightness pattern of a lit room seen from the street below (ceiling brightest)."""
    g = 0.42 + 0.58 * smoothstep(0.7, 0.0, v) ** 1.3
    ul = rng.uniform(0.2, 0.8)
    g *= 0.78 + 0.22 * (1 - np.abs(u - ul))
    if kind == 'warm':
        if rng.random() < 0.35:                    # pendant / ceiling lamp
            vl = rng.uniform(0.08, 0.28)
            g += 1.6 * np.exp(-((u - ul) ** 2 * wpx ** 2 + (v - vl) ** 2 * hpx ** 2) / (2 * (0.05 * wpx) ** 2))
        if rng.random() < 0.45:                    # tall furniture against the back wall
            a = rng.uniform(-0.1, 0.6)
            b = a + rng.uniform(0.25, 0.5)
            top = rng.uniform(0.35, 0.65)
            m = smoothstep(a - 0.03, a + 0.03, u) * (1 - smoothstep(b - 0.03, b + 0.03, u)) * smoothstep(top - 0.02, top + 0.02, v)
            g *= 1 - 0.75 * m
        if rng.random() < 0.10:                    # someone in the room
            px, py = rng.uniform(0.25, 0.75), rng.uniform(0.45, 0.6)
            head = np.exp(-(((u - px) * wpx) ** 2 + ((v - py) * hpx) ** 2) / (2 * (0.07 * wpx) ** 2))
            body = smoothstep(py + 0.08, py + 0.14, v) * np.exp(-(((u - px) * wpx) ** 2) / (2 * (0.17 * wpx) ** 2))
            g *= 1 - 0.85 * np.clip(head * 1.8 + body * 1.4, 0, 1)
        if rng.random() < 0.15:                    # plant on the sill
            px = rng.uniform(0.2, 0.8)
            blob = np.exp(-(((u - px) * wpx) ** 2 + ((v - 0.92) * hpx * 0.8) ** 2) / (2 * (0.16 * wpx) ** 2))
            g *= 1 - 0.8 * np.clip(blob * 2, 0, 1)
        if rng.random() < 0.40:                    # sheer side curtains (glow brighter + folds)
            folds = 0.85 + 0.15 * np.sin(u * wpx / max(2.0, 0.09 * wpx) * 1.7)
            side = np.maximum(smoothstep(0.24, 0.1, u), smoothstep(0.76, 0.9, u))
            g = mixv(g, 0.95 * folds, side * 0.85)
    return np.maximum(g, 0)


def street_windows(ctx, win_far):
    """Emission (linear, internal res) of every lit window, far to near, with bloom."""
    rng = np.random.default_rng(201)
    h, w = ctx.h, ctx.w
    E = win_far * (1 - ctx.layer.a)[..., None]
    for wd in ctx.windows:
        r = ctx.cov(wd['x0'], wd['y0'], wd['x1'], wd['y1'])
        if r is None:
            continue
        iy0, ix0, c = r
        hh, ww = c.shape
        Y, X = ctx.grid(iy0, ix0, hh, ww)
        u = (X - wd['x0']) / (wd['x1'] - wd['x0'])
        v = (Y - wd['y0']) / (wd['y1'] - wd['y0'])
        wpx, hpx = (wd['x1'] - wd['x0']) * K, (wd['y1'] - wd['y0']) * K
        p = rng.random()
        attic = wd['floor'] == 99
        lit_p = 0.62 if attic else 0.56
        if p > lit_p:
            kind = 'dark'
        else:
            q = rng.random()
            kind = ('warm' if q < 0.58 else 'curtain' if q < 0.74 else 'blinds' if q < 0.86 else
                    'cool' if q < 0.94 else 'tv')
        if kind == 'dark':
            if rng.random() < 0.3:      # reflection of a street light in the dark glass
                px_, py_ = rng.uniform(0.2, 0.8), rng.uniform(0.55, 0.9)
                em = lin('#FFC890') * rng.uniform(0.02, 0.06) * np.exp(
                    -(((u - px_) * wpx) ** 2 + ((v - py_) * hpx) ** 2) / (2 * (0.12 * wpx) ** 2))[..., None]
            else:
                continue
        else:
            col = lin(WARM_WIN[rng.integers(len(WARM_WIN))])
            inten = float(np.clip(rng.lognormal(np.log(0.42), 0.55), 0.08, 1.4))
            if kind == 'warm':
                g = _interior(u, v, rng, 'warm', wpx, hpx)
            elif kind == 'curtain':
                nf = rng.uniform(5, 9)
                g = 0.62 + 0.18 * np.sin(u * nf * 2 * np.pi + rng.uniform(0, 6)) + 0.2 * smoothstep(0.9, 0.1, v)
                inten *= 0.75
                col = col * lin('#FFE0C0') * 1.3
            elif kind == 'blinds':
                vb = rng.uniform(0.35, 1.0)
                slat = 0.45 + 0.55 * (0.5 + 0.5 * np.cos(v * hpx * 2 * np.pi / max(2.2, 0.075 * S_FAC * K))) ** 2
                g = np.where(v < vb, slat * 0.8, _interior(u, v, rng, 'plain', wpx, hpx))
            elif kind == 'cool':
                col = lin('#E2EAFF')
                g = _interior(u, v, rng, 'plain', wpx, hpx)
                inten *= 0.75
            else:   # tv flicker: dim blue, brighter low in the room
                col = lin('#8FA6FF')
                g = 0.35 + 0.65 * smoothstep(0.2, 0.8, v) * (0.7 + 0.3 * np.sin(u * 7 + rng.uniform(0, 6)))
                inten *= 0.4
            em = col * inten * g[..., None]
        bars = _window_glazing(u, v, wpx, hpx, 'dormer' if wd['floor'] == 99 else wd['style'])
        sl = (slice(iy0, iy0 + hh), slice(ix0, ix0 + ww))
        E[sl] += em * (c * (1 - bars) * (1 - ctx.occl[sl]))[..., None]
    # side-street windows (perspective quads)
    lit_q, lit_c = [], []
    for q, haze, kind in ctx.side_windows:
        if kind == 'win' and rng.random() < 0.42:
            lit_q.append(q)
            col = lin(WARM_WIN[rng.integers(len(WARM_WIN))]) * rng.uniform(0.2, 0.6) * (1 - 0.6 * haze)
            lit_c.append(col)
    for q, col in zip(lit_q, lit_c):
        m = _aa_mask((h, w), [q])
        E += m[..., None] * col
    return E


# --------------------------------------------------------------------------- #
# shopfront glow (screen layer) + awnings (painted into the near layer)
# --------------------------------------------------------------------------- #

SHOP_KIND = {
    'bakery': dict(col='#FFC57A', I=0.58, shelves=True, people=1),
    'closed': dict(col='#93A9CC', I=0.045, shelves=True, people=0),
    'wine': dict(col='#FF9A48', I=0.46, bottles=True, people=3),
    'cafe': dict(col='#FFAE5C', I=0.50, pendants=True, people=4),
    'door': dict(col='#FFC07E', I=0.36, people=0),
    'restaurant': dict(col='#FFA452', I=0.48, pendants=True, people=5),
    'books': dict(col='#FFCB8C', I=0.50, shelves=True, people=2),
}
AWNING_FABRIC = {'cafe': '#4A1A26', 'restaurant': '#2F4536'}


def _shop_interior(u, v, wpx, hpx, spec, rng):
    """Brightness of a lit shop interior seen through its glazing (local coords 0..1)."""
    X, Yp = u * wpx, v * hpx
    g = 0.06 + 0.14 * smoothstep(0.62, 0.05, v) + 0.05 * np.sin(u * 2.3 + rng.uniform(0, 6))
    n = max(2, int(round(wpx / 34)))
    for i in range(n):
        cx = (i + 0.5) / n * wpx + rng.uniform(-0.15, 0.15) * wpx / n
        g = g + rng.uniform(0.4, 1.15) * np.exp(-(((X - cx) / (0.36 * wpx / n)) ** 2 +
                                                   ((Yp - 0.40 * hpx) / (0.45 * hpx)) ** 2))
        if spec.get('pendants'):
            py = rng.uniform(0.10, 0.22) * hpx
            d2 = (X - cx) ** 2 + (Yp - py) ** 2
            g = g + 3.2 * np.exp(-d2 / (2 * 1.7 ** 2)) + 0.5 * np.exp(-d2 / (2 * 6.5 ** 2))
            g = g * (1 - 0.6 * _bar(X, cx, 0.3, 1.0) * (Yp < py - 1.5))
        else:
            d2 = (X - cx) ** 2 + (Yp - 0.035 * hpx) ** 2
            g = g + 1.8 * np.exp(-d2 / (2 * 1.5 ** 2))
    g = g * (1 - 0.6 * smoothstep(0.62, 1.0, v))
    if spec.get('shelves'):
        for t in (0.34, 0.5, 0.66, 0.82):
            g = g * (1 - 0.5 * _bar(v, t, 0.8, hpx))
        spines = 0.72 + 0.28 * np.sin(X * 1.9 + np.sin(Yp * 0.37) * 3) ** 2
        g = g * np.where((v > 0.3) & (v < 0.86), spines, 1.0)
    if spec.get('bottles'):
        for t in (0.36, 0.52):
            band = smoothstep(t - 0.09, t - 0.07, v) * (1 - smoothstep(t - 0.005, t, v))
            stubs = np.cos(X * 2 * np.pi / 3.2) ** 8
            g = g * (1 - 0.6 * band * (1 - stubs))
        g = g * (1 - 0.55 * smoothstep(0.66, 0.70, v))          # bar counter
    if rng.random() < 0.5:                                      # a potted plant by the glass
        px = rng.choice([0.08, 0.92]) * wpx
        blob = np.exp(-(((X - px) / (0.07 * wpx + 3)) ** 2 + ((Yp - 0.82 * hpx) / (0.22 * hpx)) ** 2))
        g = g * (1 - 0.8 * np.clip(blob * 1.6, 0, 1))
    return np.maximum(g, 0)


def _paste_alpha(dst, a, x, y):
    """Max-paste alpha a (local) into dst at integer offset (x, y), clipped."""
    h, w = dst.shape
    ah, aw = a.shape
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(w, x + aw), min(h, y + ah)
    if x1 <= x0 or y1 <= y0:
        return
    dst[y0:y1, x0:x1] = np.maximum(dst[y0:y1, x0:x1], a[y0 - y:y1 - y, x0 - x:x1 - x])


SHOP_PATRONS = ['couple_table', 'man', 'woman', 'woman_table', 'walker', 'waiter']


def street_glow(ctx):
    rng = np.random.default_rng(301)
    h, w = ctx.h, ctx.w
    E = np.zeros((h, w, 3), F32)
    s = S_FAC
    awn_occ = np.zeros((h, w), F32)
    for sh in ctx.shops:
        spec = SHOP_KIND[sh['kind']]
        r = ctx.cov(sh['x0'], sh['y0'], sh['x1'], sh['y1'])
        if r is None:
            continue
        iy0, ix0, c = r
        hh, ww = c.shape
        Y, X = ctx.grid(iy0, ix0, hh, ww)
        u = (X - sh['x0']) / (sh['x1'] - sh['x0'])
        v = (Y - sh['y0']) / (sh['y1'] - sh['y0'])
        wpx, hpx = (sh['x1'] - sh['x0']) * K, (sh['y1'] - sh['y0']) * K
        g = _shop_interior(u, v, wpx, hpx, spec, rng)
        # patrons inside: real silhouettes, 1-2 m behind the glass, feet hidden by the riser
        occ = np.zeros((hh, ww), F32)
        Dp = D_FAC + 2.0
        fy = y_ground(Dp) * K - iy0
        for _ in range(spec.get('people', 0)):
            nm = SHOP_PATRONS[rng.integers(len(SHOP_PATRONS))]
            a, fyl = silhouette_alpha(nm, 1.74 * FOC / Dp * K, flip=rng.random() < 0.5)
            px = int(rng.uniform(-0.1, 0.9) * ww)
            _paste_alpha(occ, a, px, int(round(fy - fyl)))
        occ = gblur(occ, 0.6)
        g = g * (1 - 0.93 * occ)
        # mullions: panes ~1.6 m wide, a fanlight transom, the door frame
        npn = max(2, int(round((sh['x1'] - sh['x0']) / (1.6 * s))))
        bars = np.clip(0.06 * s * K + 0.5 - np.minimum(u * wpx, (1 - u) * wpx), 0, 1)
        for i in range(1, npn):
            bars = np.maximum(bars, _bar(u, i / npn, 0.035 * s * K, wpx))
        bars = np.maximum(bars, _bar(v, 0.17, 0.035 * s * K, hpx))
        em = lin(spec['col']) * spec['I'] * (g * (1 - 0.92 * bars))[..., None]
        em = em + lin('#8494BC')[None, None] * (0.012 * (1.2 - v))[..., None]   # sky sheen on the glass
        sl = (slice(iy0, iy0 + hh), slice(ix0, ix0 + ww))
        E[sl] += em * c[..., None]
        if spec['I'] < 0.1:
            continue
        # gooseneck lamps over the fascia + gilt lettering in their pool of light
        fy0, fy1 = sh['fascia']
        nl = max(2, int((sh['x1'] - sh['x0']) / (2.2 * s)))
        for i in range(nl):
            lx = sh['x0'] + (sh['x1'] - sh['x0']) * (i + 0.5) / nl
            rr = ctx.cov(lx - 1.2 * s, fy0 - 0.25 * s, lx + 1.2 * s, fy1 + 0.1 * s)
            if rr is None:
                continue
            jy, jx, cc = rr
            Yq, Xq = ctx.grid(jy, jx, *cc.shape)
            pool = np.exp(-(((Xq - lx) / (0.8 * s)) ** 2 + ((Yq - fy0) / (0.55 * s)) ** 2))
            E[jy:jy + cc.shape[0], jx:jx + cc.shape[1]] += (lin('#FFD7A0') * 0.10) * pool[..., None]
            d2 = ((Xq - lx) ** 2 + (Yq - (fy0 - 0.12 * s)) ** 2) * K * K
            E[jy:jy + cc.shape[0], jx:jx + cc.shape[1]] += lin('#FFF1D6') * (1.4 * np.exp(-d2 / 2.0))[..., None]
        # (no lettering: legible-looking fake text reads as fake)
        nchar = 0
        cw = 0.32 * s
        x_start = (sh['x0'] + sh['x1']) / 2 - nchar * cw * 0.55
        for i in range(nchar):
            if rng.random() < 0.12:
                continue
            gx = x_start + i * cw * 1.1
            rr = ctx.cov(gx, fy0 + 0.2 * s, gx + cw * rng.uniform(0.55, 0.9), fy1 - 0.2 * s)
            if rr is not None:
                jy, jx, cc = rr
                E[jy:jy + cc.shape[0], jx:jx + cc.shape[1]] += lin('#E9C98A') * 0.16 * cc[..., None]
        # awning (dark fabric, warm-lit underside) painted into the near layer
        if sh['kind'] in AWNING_FABRIC:
            fab = lin(AWNING_FABRIC[sh['kind']])
            y_back = fy1 + 0.02 * s
            y_front = y_at(D_FAC - 1.5, 2.45)
            y_val = y_front + 0.3 * FOC / (D_FAC - 1.5)
            ax0, ax1 = sh['x0'] - 0.15 * s, sh['x1'] + 0.15 * s
            ru = ctx.cov(ax0, y_back, ax1, y_front)
            if ru is not None:
                jy, jx, cc = ru
                t = np.linspace(0, 1, cc.shape[0], dtype=F32)[:, None, None]
                under = fab * 0.5 + lin(spec['col']) * (0.035 + 0.05 * t)
                ctx.layer.paint(cc, under * np.ones((1, cc.shape[1], 1), F32), jy, jx)
                awn_occ[jy:jy + cc.shape[0], jx:jx + cc.shape[1]] = np.maximum(
                    awn_occ[jy:jy + cc.shape[0], jx:jx + cc.shape[1]], cc)
            # valance with scallops
            rv = ctx.cov(ax0, y_front, ax1, y_val + 0.12 * s)
            if rv is not None:
                jy, jx, cc = rv
                Yq, Xq = ctx.grid(jy, jx, *cc.shape)
                sc_w = 0.45 * s
                ph = ((Xq - ax0) % sc_w) / sc_w - 0.5
                edge = y_val + 0.10 * s * np.sqrt(np.clip(1 - 4 * ph * ph, 0, 1))
                m = cc * np.clip((edge - Yq) * K + 0.5, 0, 1)
                stripe = 1.0 if sh['kind'] != 'cafe' else 1
                col = fab * facade_light(Yq, Xq) * 2.2 * stripe + lin(spec['col']) * 0.02
                ctx.layer.paint(m, col, jy, jx)
                awn_occ[jy:jy + cc.shape[0], jx:jx + cc.shape[1]] = np.maximum(
                    awn_occ[jy:jy + cc.shape[0], jx:jx + cc.shape[1]], m)
        # light spilling out onto the far pavement in front of the shop
        yg = y_ground(D_FAC)
        rp = ctx.cov(sh['x0'] - 1.5 * s, yg - 2, sh['x1'] + 1.5 * s, y_ground(D_KERB) + 4)
        if rp is not None:
            jy, jx, cc = rp
            Yq, Xq = ctx.grid(jy, jx, *cc.shape)
            fall = smoothstep(sh['x0'] - 1.5 * s, sh['x0'] + 0.5 * s, Xq) * (1 - smoothstep(sh['x1'] - 0.5 * s, sh['x1'] + 1.5 * s, Xq))
            E[jy:jy + cc.shape[0], jx:jx + cc.shape[1]] += lin(spec['col']) * (spec['I'] * 0.12 * fall * cc)[..., None]
    E *= (1 - awn_occ)[..., None]
    # side-street shop glow, dimmer with distance
    for q, haze, kind in ctx.side_windows:
        if kind == 'shop' and rng.random() < 0.7:
            m = _aa_mask((h, w), [q])
            E += m[..., None] * lin('#FFB060') * rng.uniform(0.25, 0.6) * (1 - 0.55 * haze)
    ctx.awn_occ = awn_occ
    return E


# --------------------------------------------------------------------------- #
# tram (moving right on the far track, motion-blurred)
# --------------------------------------------------------------------------- #

TRAM_NOSE = 1800.0           # full-res x of the nose
TRAM_BLUR = 84.0             # motion blur length (full-res px)
S_TRAM = FOC / D_TRAM


def tone(e):
    """Soft photographic shoulder for emitted light (linear in, linear out, <= 1)."""
    return 1 - np.exp(-np.maximum(e, 0))


def street_tram():
    rng = np.random.default_rng(401)
    h, w = int(SH * K), int(SW * K)
    s = S_TRAM
    yT = lambda hm: y_at(D_TRAM, hm)
    xb = lambda m: TRAM_NOSE - m * s
    L = Layer(h, w)
    E = np.zeros((h, w, 3), F32)
    ys = (np.arange(h, dtype=F32) + 0.5) / K
    xs = (np.arange(w, dtype=F32) + 0.5) / K
    hm = EYE + (HZ - ys) * D_TRAM / FOC                       # height (m) of each row
    xm = (TRAM_NOSE - xs) / s                                  # metres behind the nose
    HM, XM = np.meshgrid(hm, xm, indexing='ij')
    # ---------------- silhouette ----------------
    prof = [(0.32, 0.20), (0.10, 0.30), (0.02, 0.55), (0.0, 0.85), (0.03, 1.10), (0.16, 1.42),
            (0.50, 2.35), (0.78, 2.95), (1.05, 3.28), (1.45, 3.44)]
    body = [(xb(m), yT(hh)) for m, hh in prof] + [(-500, yT(3.44)), (-500, yT(0.20))]
    m_body = _aa_mask((h, w), [body])
    # roof equipment fairings
    roof = []
    for (m0, m1, top) in [(1.9, 4.6, 3.80), (5.2, 8.6, 3.74), (9.4, 11.2, 3.78), (12.4, 16, 3.80)]:
        r_ = 0.22
        roof.append([(xb(m1), yT(3.42)), (xb(m1) + 0.05 * s, yT(top - r_)), (xb(m1) + r_ * s, yT(top)),
                     (xb(m0) - r_ * s, yT(top)), (xb(m0) - 0.05 * s, yT(top - r_)), (xb(m0), yT(3.42))])
    m_roof = _aa_mask((h, w), roof)
    # underbody: bogies + deep shadow between rail and skirt
    under = [(xb(0.45), yT(0.21)), (-500, yT(0.21)), (-500, yT(0.03)), (xb(0.45), yT(0.03))]
    m_under = _aa_mask((h, w), [under])
    # ---------------- livery + light ----------------
    ivory, charcoal = lin('#DDD2BE'), lin('#24262B')
    alb = np.where((HM < 0.36)[..., None], lin('#4A4C52'), ivory)
    alb = np.where(((HM > 0.86) & (HM < 0.95))[..., None], lin('#A9502F'), alb)
    band = (HM > 0.95) & (HM < 2.62)
    alb = np.where(band[..., None], charcoal, alb)
    light = (E_SKY * 0.42)[None, None] * (0.75 + 0.6 * smoothstep(2.4, 3.44, HM))[..., None] + \
        (lin('#FFC890') * 0.085)[None, None] * (1.1 - 0.25 * smoothstep(0.3, 3.4, HM))[..., None]
    col = alb * light
    # glossy paint: sky in the curved shoulder, streaks of our side's lights low down
    shoulder = np.exp(-((HM - 3.33) / 0.07) ** 2)
    col += (sky_column(np.array([800.0], F32))[0] * 0.55)[None, None] * shoulder[..., None]
    streak = smoothstep(0.4, 2.0, fbm(1, w, 160 * K, 3, rng))[0]
    col += (lin('#FFB878') * 0.05)[None, None] * (np.exp(-((HM - 0.66) / 0.09) ** 2)[..., None] * streak[None, :, None])
    # front glazing (raked windscreen) + cab side window: dark, faint dashboard glow
    ws = [(xb(0.17), yT(1.42)), (xb(0.50), yT(2.35)), (xb(0.76), yT(2.92)), (xb(1.05), yT(2.92)),
          (xb(1.05), yT(1.40))]
    m_ws = _aa_mask((h, w), [ws])
    cab = [(xb(1.15), yT(1.25)), (xb(1.15), yT(2.80)), (xb(1.85), yT(2.80)), (xb(1.85), yT(1.25))]
    m_cab = _aa_mask((h, w), [cab])
    glass_dark = lin('#1A1F2E') * 1.2 + E_SKY * 0.3
    col = mixv(col, glass_dark[None, None] + (lin('#FFB070') * 0.03)[None, None] *
               np.exp(-((HM - 1.45) / 0.15) ** 2)[..., None], np.maximum(m_ws, m_cab)[..., None])
    # ---------------- passenger saloon: windows + doors ----------------
    win_m = []                       # (m0, m1, h0, h1, door)
    m = 2.05
    plan = ['door', 'w', 'w', 'w', 'w', 'door', 'bellows', 'w', 'w', 'w', 'w', 'door']
    for item in plan:
        if item == 'door':
            win_m.append((m, m + 1.30, 0.45, 2.42, True)); m += 1.30 + 0.16
        elif item == 'bellows':
            win_m.append((m, m + 0.45, 0.30, 3.30, 'bellows')); m += 0.45 + 0.16
        else:
            win_m.append((m, m + 1.32, 0.98, 2.55, False)); m += 1.32 + 0.14
    interior = np.zeros((h, w, 3), F32)
    win_cov = np.zeros((h, w), F32)
    warmwhite = lin('#FFDCAA') * 0.85
    for (m0, m1, h0, h1, door) in win_m:
        if door == 'bellows':
            q = [(xb(m1), yT(h1)), (xb(m0), yT(h1)), (xb(m0), yT(h0)), (xb(m1), yT(h0))]
            mb = _aa_mask((h, w), [q])
            pleat = 0.55 + 0.45 * np.cos(XM * 2 * np.pi / 0.06) ** 2
            col = mixv(col, (lin('#15161A') * pleat[..., None] + E_SKY * 0.2), mb[..., None])
            continue
        q = [(xb(m1), yT(h1)), (xb(m0), yT(h1)), (xb(m0), yT(h0)), (xb(m1), yT(h0))]
        mw = _aa_mask((h, w), [q])
        win_cov = np.maximum(win_cov, mw)
    # interior seen through the glazing (one field for the whole saloon)
    ceiling = np.exp(-((HM - 2.42) / 0.05) ** 2) * 2.6 + 0.9 * smoothstep(1.6, 2.4, HM)
    farside = smoothstep(1.05, 1.15, HM) * (1 - smoothstep(2.25, 2.32, HM))
    far_pillars = 0.5 + 0.5 * smoothstep(0.03, 0.09, np.abs(((XM - 0.4) % 1.46) - 0.73) - 0.6)
    outside_blobs = 0.35 + 0.65 * smoothstep(0.2, 1.6, fbm(h, w, 60 * K, 3, rng))
    g = 0.34 + ceiling - farside * (0.26 - 0.16 * outside_blobs) * far_pillars
    g = g * (1 - 0.45 * smoothstep(1.15, 0.6, HM))           # lower saloon in shadow (seat backs)
    # passengers (real silhouettes) + yellow grab poles
    occ = np.zeros((h, w), F32)
    floor_y = yT(0.42) * K
    for i in range(14):
        mpos = rng.uniform(2.2, 18.0)
        nm = ['man', 'woman', 'walker', 'man', 'woman'][rng.integers(5)]
        a, fyl = silhouette_alpha(nm, 1.72 * S_TRAM * K * rng.uniform(0.92, 1.06), flip=rng.random() < 0.5)
        seated = rng.random() < 0.45
        dy = 0.45 * S_TRAM * K if seated else 0
        _paste_alpha(occ, a * rng.uniform(0.75, 0.95), int(xb(mpos) * K - a.shape[1] / 2),
                     int(round(floor_y - fyl + dy)))
    occ = gblur(occ, 0.7)
    g = g * (1 - 0.85 * occ)
    poles = np.zeros(w, F32)
    for i in range(10):
        px = xb(rng.uniform(2.3, 18.0)) * K
        poles = np.maximum(poles, np.clip(1.2 - np.abs(np.arange(w) + 0.5 - px), 0, 1))
    pole_v = smoothstep(0.5, 0.6, HM) * (1 - smoothstep(2.38, 2.45, HM))
    interior = warmwhite[None, None] * g[..., None]
    interior = mixv(interior, (lin('#F2B640') * 1.3)[None, None], (poles[None, :] * pole_v * 0.85)[..., None])
    # door leaves: central seal + frames
    for (m0, m1, h0, h1, door) in win_m:
        if door is True:
            for mm in (m0 + 0.04, (m0 + m1) / 2, m1 - 0.04):
                q = [(xb(mm) - 0.035 * s, yT(h1 + 0.05)), (xb(mm) + 0.035 * s, yT(h1 + 0.05)),
                     (xb(mm) + 0.035 * s, yT(h0 - 0.05)), (xb(mm) - 0.035 * s, yT(h0 - 0.05))]
                win_cov = win_cov * (1 - 0.9 * _aa_mask((h, w), [q]))
    # glazing reflections (faint sky sheen, stronger at the top of each pane)
    sheen = (E_SKY * 0.9)[None, None] * smoothstep(1.6, 2.6, HM)[..., None]
    col = mixv(col, tone(interior * 1.15) + sheen, win_cov[..., None])
    E += interior * 0.9 * win_cov[..., None]
    # side destination display (amber LEDs) above the front door
    q = [(xb(3.2), yT(2.86)), (xb(2.2), yT(2.86)), (xb(2.2), yT(2.66)), (xb(3.2), yT(2.66))]
    md = _aa_mask((h, w), [q])
    leds = 0.45 + 0.55 * (fbm(h, w, 6, 1, rng) > 0.1)
    amber = lin('#FFA43A') * 1.6
    col = mixv(col, tone(amber[None, None] * leds[..., None]), md[..., None])
    E += amber[None, None] * (md * leds)[..., None]
    # front destination display sliver + marker lights + headlight
    q = [(xb(0.82), yT(3.22)), (xb(0.95), yT(3.30)), (xb(1.10), yT(3.30)), (xb(1.10), yT(3.05)), (xb(0.72), yT(3.02))]
    md = _aa_mask((h, w), [q])
    col = mixv(col, tone(amber[None, None] * 1.4), md[..., None])
    E += (amber * 1.4)[None, None] * md[..., None]
    for (mm, hh_, r_, inten, c_) in [(0.06, 0.82, 0.10, 9.0, '#FFF2DA'), (0.30, 0.82, 0.07, 3.0, '#FFF2DA'),
                                    (0.95, 3.12, 0.05, 2.5, '#FFF6E8')]:
        cxp, cyp = xb(mm) * K, yT(hh_) * K
        d2 = ((xs * K - cxp) ** 2)[None, :] + ((ys * K - cyp) ** 2)[:, None]
        spot = np.exp(-d2 / (2 * (r_ * s * K) ** 2))
        col = mixv(col, tone(lin(c_) * inten)[None, None], np.clip(spot * 1.5, 0, 1)[..., None])
        E += lin(c_)[None, None] * (inten * spot)[..., None]
    # paint body, roof fairings, underbody
    Lb = Layer(h, w)
    Lb.paint(m_body, col)
    rcol = ivory * (E_SKY * 1.25 + lin('#FFC890') * 0.03) + sky_column(np.array([700.0], F32))[0] * 0.25
    Lb.paint(m_roof, rcol[None, None] * (0.9 + 0.1 * smoothstep(3.5, 3.8, HM))[..., None])
    Lb.paint(m_under, lin('#121317'))
    # pantograph (half-pantograph, Z-shaped) up to the contact wire
    mp = 6.6
    wire_h = 5.9
    pant = [[(xb(mp + 0.5), yT(3.78)), (xb(mp - 0.6), yT(3.78))],
            [(xb(mp + 0.3), yT(3.80)), (xb(mp - 0.9), yT(4.95))],
            [(xb(mp - 0.9), yT(4.95)), (xb(mp + 0.15), yT(wire_h - 0.06))],
            [(xb(mp + 0.55), yT(wire_h - 0.04)), (xb(mp - 0.25), yT(wire_h - 0.04))],
            [(xb(mp + 0.55), yT(wire_h - 0.04)), (xb(mp + 0.65), yT(wire_h - 0.16))],
            [(xb(mp - 0.25), yT(wire_h - 0.04)), (xb(mp - 0.35), yT(wire_h - 0.16))]]
    mpant = _aa_lines((h, w), pant, 0.045 * s)
    Lb.paint(mpant, lin('#1B1D22'))
    L.over(Lb)
    # motion blur: uniform box along x (the tram moves; the street does not)
    n = int(round(TRAM_BLUR * K))
    st = np.dstack([L.rgb, L.a])
    st = cv2.blur(st, (n, 1), borderType=cv2.BORDER_CONSTANT)
    L.rgb, L.a = np.ascontiguousarray(st[..., :3]), np.ascontiguousarray(st[..., 3])
    E = cv2.blur(E, (n, 1), borderType=cv2.BORDER_CONSTANT)
    return L, E


# --------------------------------------------------------------------------- #
# street lamps, catenary wires, halos
# --------------------------------------------------------------------------- #

S_LAMP = FOC / D_LAMP
LANTERN_H = 7.45             # lantern centre height (m)


def lamp_centres():
    """Full-res (x, y) of every lantern centre (anchor for halos / glows)."""
    return [(lx, y_at(D_LAMP, LANTERN_H)) for lx in LAMP_X]


def street_lamps():
    rng = np.random.default_rng(501)
    h, w = int(SH * K), int(SW * K)
    s = S_LAMP
    yl = lambda hm: y_at(D_LAMP, hm)
    L = Layer(h, w)
    halo = np.zeros((h, w, 3), F32)
    iron = lin('#15171D')
    warm = lin('#FFC680')
    ys = (np.arange(h, dtype=F32) + 0.5) / K
    xs = (np.arange(w, dtype=F32) + 0.5) / K
    for lx in LAMP_X:
        # post: plinth, fluted base, tapering shaft, collar, lantern, cap, finial
        prof = [(0.00, 0.23), (0.22, 0.23), (0.25, 0.17), (0.55, 0.15), (0.75, 0.19), (1.05, 0.12),
                (1.15, 0.085), (6.85, 0.06), (6.9, 0.10), (7.0, 0.10), (7.0, 0.07)]
        left = [(lx - r_ * s, yl(hh)) for hh, r_ in prof]
        right = [(lx + r_ * s, yl(hh)) for hh, r_ in prof[::-1]]
        post = _aa_mask((h, w), [left + right])
        hm = EYE + (HZ - ys) * D_LAMP / FOC
        lit = warm[None, :] * (0.03 * np.exp(-np.abs(hm - LANTERN_H) / 0.6))[:, None]     # (h, 3)
        rim = np.clip(1 - np.abs(xs - (lx - 0.05 * s)) / (0.05 * s), 0, 1)[None, :]
        colp = iron[None, None] + (E_SKY * 0.35)[None, None] * rim[..., None] + lit[:, None, :]
        L.paint(post, colp)
        # lantern: inverted trapezoid of glass with dark frame, pyramid cap
        g0, g1 = 7.02, 7.86
        glass = [(lx - 0.15 * s, yl(g0)), (lx - 0.22 * s, yl(g1)), (lx + 0.22 * s, yl(g1)), (lx + 0.15 * s, yl(g0))]
        mg = _aa_mask((h, w), [glass])
        HMg = hm[:, None] * np.ones((1, w), F32)
        frame = np.maximum(np.clip(1.6 - np.abs(xs - lx)[None, :] / (0.02 * s), 0, 1),
                           np.clip(1.4 - np.abs(HMg - 7.44) / 0.025, 0, 1))
        gl = tone(warm * 3.2)[None, None] * (1 - 0.85 * frame)[..., None] + iron[None, None] * frame[..., None]
        L.paint(mg, gl)
        cap = [(lx - 0.28 * s, yl(g1)), (lx - 0.06 * s, yl(8.15)), (lx + 0.06 * s, yl(8.15)), (lx + 0.28 * s, yl(g1)),
               (lx + 0.26 * s, yl(g1 - 0.04)), (lx - 0.26 * s, yl(g1 - 0.04))]
        L.paint(_aa_mask((h, w), [cap]), iron + warm * 0.04)
        fin = [(lx - 0.02 * s, yl(8.12)), (lx, yl(8.35)), (lx + 0.02 * s, yl(8.12))]
        L.paint(_aa_mask((h, w), [fin]), iron)
        # halos: lantern core, near glow, wide mist scattering, faint downward cone, light pool
        cx, cy = lx * K, yl(LANTERN_H) * K
        d2 = ((xs * K - cx) ** 2)[None, :] + ((ys * K - cy) ** 2)[:, None]
        hal = (2.2 * np.exp(-d2 / (2 * (0.16 * s * K) ** 2)) + 0.28 * np.exp(-d2 / (2 * 30.0 ** 2)) +
               0.05 * np.exp(-d2 / (2 * 110.0 ** 2)) + 0.01 * np.exp(-d2 / (2 * 330.0 ** 2)))
        dyp = (ys * K - cy)[:, None]
        cone = np.clip(dyp / (5.5 * s * K), 0, 1) * np.exp(-(((xs * K - cx)[None, :]) ** 2) /
                                                          (2 * (12 + 0.45 * np.maximum(dyp, 0)) ** 2))
        cone *= (1 - smoothstep(4.5 * s * K, 7.4 * s * K, dyp))
        hal = hal + 0.045 * cone
        yg = y_ground(D_LAMP) * K
        pool = np.exp(-(((xs * K - cx) / (3.2 * s * K)) ** 2)[None, :] - (((ys * K - yg) / 2.0) ** 2)[:, None])
        hal = hal + 0.35 * pool
        halo += warm[None, None] * hal[..., None]
    # --- overhead line: contact + messenger wires for both tracks, droppers, span wires --
    segs_thin, segs_span = [], []
    xs_span = [VPX + (lx - VPX) * D_LAMP / D_TRAM for lx in LAMP_X]
    for D, ch, mh in [(D_TRAM, 5.9, 6.75), (20.0, 5.9, 6.75)]:
        sp = FOC / D
        anchors = sorted(set([VPX + (lx - VPX) * D_LAMP / D for lx in LAMP_X] + [-600.0, SW + 600.0]))
        for a0, a1 in zip(anchors[:-1], anchors[1:]):
            t = np.linspace(0, 1, 40)
            xx = a0 + (a1 - a0) * t
            sag = 0.35 * 4 * t * (1 - t)
            segs_thin.append(np.stack([xx, y_at(D, ch) + 0 * t], 1))
            segs_thin.append(np.stack([xx, y_at(D, mh - sag)], 1))
            nd = max(1, int((a1 - a0) / (6.0 * sp)))
            for j in range(1, nd + 1):
                tt = j / (nd + 1)
                xd = a0 + (a1 - a0) * tt
                segs_thin.append([(xd, y_at(D, ch)), (xd, y_at(D, mh - 0.35 * 4 * tt * (1 - tt)))])
    for lx in LAMP_X:            # span wires run from the posts towards the viewer (radial)
        if abs(lx - VPX) < 800:
            continue
        p0 = np.array([lx, y_at(D_LAMP, 7.6)])
        dirv = p0 - np.array([VPX, HZ])
        dirv /= np.linalg.norm(dirv)
        segs_span.append([tuple(p0), tuple(p0 + dirv * 5000)])
    mw = _aa_lines((h, w), segs_thin, 1.8)
    ms = _aa_lines((h, w), segs_span, 3.0)
    L.paint(np.clip(mw * 0.85 + ms * 0.8, 0, 1), lin('#101218'))
    return L, halo


# --------------------------------------------------------------------------- #
# street trees
# --------------------------------------------------------------------------- #

def _tree(h, w, cx, D, rng, height_m=10.5, crown_m=6.6):
    """One street tree (trunk, limbs, clumped leaf mass) -> (alpha, colour) full-frame arrays."""
    s = FOC / D
    ss = 2                                                    # supersampling of the local canvas
    yg = y_ground(D)
    top = y_at(D, height_m)
    y_fork = y_at(D, rng.uniform(2.6, 3.1))
    crown_bot = y_at(D, 3.3)
    lean = rng.normal(0, 0.10) * s
    ccx, ccy = cx + lean * 1.6, (top + crown_bot) / 2
    rx, ry = crown_m / 2 * s, (crown_bot - top) / 2
    bx0, bx1 = ccx - rx * 1.35, ccx + rx * 1.35
    by0, by1 = top - 0.4 * ry, yg + 2
    X0, Y0 = int(bx0 * K) - 2, int(by0 * K) - 2
    lw, lh = int((bx1 - bx0) * K) + 5, int((by1 - by0) * K) + 5
    can = np.zeros((lh * ss, lw * ss), np.uint8)
    f = K * ss
    P2 = lambda x, y: (int(round((x * K - X0) * ss * 16)), int(round((y * K - Y0) * ss * 16)))
    # clumps of foliage around the crown (an irregular, gappy mass rather than a ball)
    clumps = []
    for k in range(rng.integers(6, 10)):
        ang = rng.uniform(0, 2 * np.pi)
        rr = rng.uniform(0.25, 0.75)
        cxk = ccx + np.cos(ang) * rr * rx * 0.8
        cyk = ccy + np.sin(ang) * rr * ry * 0.75 - 0.1 * ry
        clumps.append((cxk, cyk, rx * rng.uniform(0.35, 0.55), ry * rng.uniform(0.30, 0.48)))
    # limbs: from the fork to each clump centre, with a kink; twigs stay inside the leaves
    segs = [((cx, yg), (cx + lean, y_fork), 0.34, 0.26)]
    for (cxk, cyk, rxk, ryk) in clumps:
        mx = (cx + lean + cxk) / 2 + rng.normal(0, 0.25) * s
        my = (y_fork + cyk) / 2 + rng.normal(0, 0.2) * s
        segs.append(((cx + lean, y_fork), (mx, my), 0.17, 0.11))
        segs.append(((mx, my), (cxk, cyk), 0.11, 0.05))
    for (p0, p1, w0, w1) in segs:
        n = 6
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            a_ = (p0[0] + (p1[0] - p0[0]) * t0, p0[1] + (p1[1] - p0[1]) * t0)
            b_ = (p0[0] + (p1[0] - p0[0]) * t1, p0[1] + (p1[1] - p0[1]) * t1)
            wd = (w0 + (w1 - w0) * (t0 + t1) / 2) * s * f
            cv2.line(can, P2(*a_), P2(*b_), 255, max(1, int(round(wd))), cv2.LINE_AA, 4)
    # leaves: gaussian-distributed sprays inside each clump -> ragged edges and sky holes
    for (cxk, cyk, rxk, ryk) in clumps:
        n = int(rxk * ryk / (s * s) * 420)
        px = cxk + rng.normal(0, 0.45, n) * rxk
        py = cyk + rng.normal(0, 0.45, n) * ryk
        for (lx, ly) in zip(px, py):
            r1 = rng.uniform(0.045, 0.085) * s * f
            r2 = r1 * rng.uniform(0.45, 0.8)
            cv2.ellipse(can, P2(lx, ly), (max(1, int(r1 * 16)), max(1, int(r2 * 16))),
                        rng.uniform(0, 180), 0, 360, 255, -1, cv2.LINE_AA, 4)
    a_loc = cv2.resize(can.astype(F32) / 255, (lw, lh), interpolation=cv2.INTER_AREA)
    alpha = np.zeros((h, w), F32)
    yy0, xx0 = max(0, Y0), max(0, X0)
    yy1, xx1 = min(h, Y0 + lh), min(w, X0 + lw)
    alpha[yy0:yy1, xx0:xx1] = a_loc[yy0 - Y0:yy1 - Y0, xx0 - X0:xx1 - X0]
    # colour: near-black green; the underside of the crown warm-lit by the shops and lamps,
    # a cool sky rim on top; trunk dark with a faint warm side
    ys = (np.arange(h, dtype=F32) + 0.5) / K
    xs = (np.arange(w, dtype=F32) + 0.5) / K
    under = smoothstep(ccy - 0.2 * ry, crown_bot + 0.1 * ry, ys)[:, None] * \
        np.exp(-((xs - ccx) / (rx * 1.1)) ** 2)[None, :]
    under = under * (ys < crown_bot + 0.2 * ry)[:, None]
    topc = (1 - smoothstep(top, top + 0.5 * ry, ys))[:, None]
    nz = 1 + 0.12 * fbm(h, w, 4, 2, rng) + 0.1 * fbm(h, w, 40, 2, rng)
    col = (lin('#0B0E0D')[None, None] * nz[..., None] +
           (lin('#8C7A3C') * 0.075)[None, None] * (under ** 1.6 * nz)[..., None] +
           (E_SKY * 0.35)[None, None] * topc[..., None])
    return alpha, col


def street_trees():
    rng = np.random.default_rng(601)
    h, w = int(SH * K), int(SW * K)
    L = Layer(h, w)
    specs = [(TREE_X[0], D_TREE, 10.6, 6.8), (TREE_X[1], D_TREE, 10.2, 6.4), (TREE_X[2], D_TREE, 10.9, 7.0),
             (VPX + FOC * ((GAP[1] - VPX) / S_FAC - 2.6) / 92.0, 92.0, 8.5, 5.2)]
    for cx, D, hm_, cm in sorted(specs, key=lambda t: -t[1]):       # far to near
        a, col = _tree(h, w, cx, D, rng, hm_, cm)
        if D > 60:
            col = mixv(col, sky_column(np.array([1700.0], F32))[0][None, None] * 0.55, 0.45)
        Lt = Layer(h, w)
        Lt.paint(a, col)
        L.over(Lt)
    return L


# --------------------------------------------------------------------------- #
# pedestrians (keyed silhouettes, small + cool)
# --------------------------------------------------------------------------- #

FIGURES = [  # (silhouette, x centre full-res, depth m, flip)
    ('couple_table', 2390.0, D_FIG, False),
    ('waiter', 2665.0, D_FIG - 0.6, True),
    ('man', 3725.0, D_FIG, False),
    ('woman', 3800.0, D_FIG, False),
    ('walker', 4290.0, D_FIG - 1.2, True),
    ('woman_table', 5215.0, D_FIG, False),
    ('walker', VPX + FOC * 10.4 / 88.0, 88.0, False),
    ('man', VPX + FOC * 10.8 / 120.0, 120.0, True),
]


def street_figures():
    h, w = int(SH * K), int(SW * K)
    L = Layer(h, w)
    for name, cx, D, flip in sorted(FIGURES, key=lambda t: -t[2]):
        rgba, fy = key_silhouettes()[name]
        sc = 1.74 * FOC / D * K / 980.0
        nw, nh = max(1, round(rgba.shape[1] * sc)), max(1, round(rgba.shape[0] * sc))
        pm = np.dstack([rgba[..., :3] * rgba[..., 3:], rgba[..., 3:]])
        r = cv2.resize(pm, (nw, nh), interpolation=cv2.INTER_AREA)
        if flip:
            r = r[:, ::-1]
        a = r[..., 3]
        src = np.where(a > 1e-3, lum(r[..., :3]) / np.maximum(a, 1e-3), 0)
        haze = float(np.clip((D - 55) / 200, 0, 0.6))
        col = mixv(lin('#10131C')[None, None], lin('#1E2333')[None, None], np.clip(src * 4, 0, 1)[..., None])
        col = mixv(col, sky_column(np.array([1700.0], F32))[0][None, None] * 0.6, haze)
        x0 = int(round(cx * K - nw / 2))
        y0 = int(round(y_ground(D) * K - fy * sc))
        hh, ww = a.shape
        cy0, cx0 = max(0, -y0), max(0, -x0)
        cy1, cx1 = min(hh, h - y0), min(ww, w - x0)
        Lf = Layer(h, w)
        Lf.paint(a[cy0:cy1, cx0:cx1], col[cy0:cy1, cx0:cx1], y0 + cy0, x0 + cx0)
        L.over(Lf)
    return L


# --------------------------------------------------------------------------- #
# wet ground + reflections
# --------------------------------------------------------------------------- #

Y_KERB_FAR = y_ground(D_KERB)
Y_KERB_NEAR = HZ + FOC * (EYE - 0.12) / 6.0            # top edge of the near kerb (sidewalk +12 cm)
Y_KERB_NEAR_B = HZ + FOC * (EYE - 0.12) / 5.7


def _mirror(arr, y_axis, h):
    """Mirror an internal-res image about full-res row y_axis (rows below it get the image above)."""
    ys = (np.arange(h, dtype=F32) + 0.5) / K
    src = (2 * y_axis - ys) * K - 0.5
    mapy = np.repeat(src[:, None], arr.shape[1], 1).astype(F32)
    mapx = np.repeat((np.arange(arr.shape[1], dtype=F32))[None, :], h, 0)
    out = cv2.remap(arr, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    out[ys < y_axis] = 0
    return out


def _wet_reflectance(h, w, rng):
    """Per-pixel reflectance of the wet street (Fresnel at grazing angles x puddle pattern)."""
    ys = (np.arange(h, dtype=F32) + 0.5) / K
    D = np.where(ys > Y_KERB_NEAR, FOC * (EYE - 0.12) / np.maximum(ys - HZ, 1), depth_of_row(ys))
    hcam = np.where(ys > Y_KERB_NEAR, EYE - 0.12, EYE)
    cos_t = hcam / np.sqrt(hcam * hcam + D * D)
    fres = 0.02 + 0.98 * (1 - cos_t) ** 5
    # puddles: patches of mirror water, stretched along the street by perspective
    pud = fbm(h, w, 90 * K, 4, rng, aniso=4.0)
    wet = 0.45 + 0.55 * smoothstep(-0.3, 1.2, pud)
    near = ys > Y_KERB_NEAR
    wet = np.where(near[:, None], 0.12 + 0.6 * smoothstep(0.6, 1.6, pud), wet)
    return (fres[:, None] * wet).astype(F32), D


def street_ground(scene_far, near, trees, tram, lamps):
    """Opaque ground layer (pavements + road) with the mirrored scene in the wet surface."""
    rng = np.random.default_rng(701)
    h, w = near.a.shape
    ys = (np.arange(h, dtype=F32) + 0.5) / K
    xs = (np.arange(w, dtype=F32) + 0.5) / K
    # ---- mirrored scene (per depth about its own ground line), painter's order --------------
    M = _mirror(scene_far.rgb, y_ground(400.0), h)
    for lay, yax in [(near, y_ground(D_FAC)), (trees, y_ground(D_TREE)), (lamps, y_ground(D_LAMP)),
                     (tram, y_ground(D_TRAM))]:
        mr = _mirror(lay.rgb, yax, h)
        ma = _mirror(lay.a, yax, h)
        M = mr + M * (1 - ma[..., None])
    R, D = _wet_reflectance(h, w, rng)
    # roughness: reflections smear vertically, more so close to the camera
    near_w = smoothstep(2450, 3200, ys)[:, None, None]
    Mb = mixv(gblur(M, 4.0, 18), gblur(M, 7.0, 48), near_w)
    # ---- diffuse surface -----------------------------------------------------------------
    asphalt = lin('#2B2C30')
    pav = lin('#3E3D40')
    kerb = lin('#77777A')
    alb = np.empty((h, w, 3), F32)
    alb[:] = asphalt
    far_sw = (ys < Y_KERB_FAR)[:, None]
    alb = np.where(far_sw[..., None], pav, alb)
    alb = np.where(((ys >= Y_KERB_NEAR) & (ys < Y_KERB_NEAR_B))[:, None, None], kerb, alb)
    alb = np.where((ys >= Y_KERB_NEAR_B)[:, None, None], pav, alb)
    grain = 1 + 0.10 * fbm(h, w, 2.0, 2, rng) + 0.10 * fbm(h, w, 70 * K, 4, rng, aniso=3)
    # tyre-polished lanes: faint horizontal bands
    lanes = 1 + 0.05 * np.sin((1 / np.maximum(ys - HZ, 1)) * 4.0e4)[:, None]
    alb = alb * (grain * lanes)[..., None]
    # paving joints on the near sidewalk (perspective grid, 0.6 m slabs) + kerb joints
    joints = []
    for k in range(1, 9):
        Dj = 5.7 - 0.6 * k
        if Dj <= 2.0:
            break
        yj = HZ + FOC * (EYE - 0.12) / Dj
        joints.append([(-100, yj), (SW + 100, yj)])
    for j in range(-40, 41):
        X = 0.6 * j + 0.13
        joints.append([(VPX + FOC * X / 5.7, Y_KERB_NEAR_B), (VPX + FOC * X / 2.2, HZ + FOC * (EYE - 0.12) / 2.2)])
    for j in range(-25, 26):
        X = 1.0 * j + 0.4
        joints.append([(VPX + FOC * X / 6.0, Y_KERB_NEAR), (VPX + FOC * X / 5.7, Y_KERB_NEAR_B)])
    mj = _aa_lines((h, w), joints, 4.0)
    alb = alb * (1 - 0.7 * mj)[..., None]
    # road paint (worn, wet): solid tram-lane edge, dashed lane line, a zebra crossing
    paint = []
    for Dl in (23.4, 27.2):
        yl = y_ground(Dl)
        paint.append([(-100, yl - 0.07 * FOC * EYE / Dl ** 2), (-100, yl + 0.07 * FOC * EYE / Dl ** 2),
                      (SW + 100, yl + 0.07 * FOC * EYE / Dl ** 2), (SW + 100, yl - 0.07 * FOC * EYE / Dl ** 2)])
    Dl = 14.0
    for X0 in np.arange(-60, 60, 9.0):
        xa, xb_ = VPX + FOC * X0 / Dl, VPX + FOC * (X0 + 4.5) / Dl
        yl = y_ground(Dl)
        dy = 0.08 * FOC * EYE / Dl ** 2
        paint.append([(xa, yl - dy), (xb_, yl - dy), (xb_, yl + dy), (xa, yl + dy)])
    Dz = 7.2
    while Dz < 40:
        Dz2 = Dz + 0.5
        for (Xa, Xb) in [(1.2, 4.8)]:
            q = [(VPX + FOC * Xa / Dz2, y_ground(Dz2)), (VPX + FOC * Xb / Dz2, y_ground(Dz2)),
                 (VPX + FOC * Xb / Dz, y_ground(Dz)), (VPX + FOC * Xa / Dz, y_ground(Dz))]
            paint.append(q)
        Dz += 1.0
    mp = _aa_mask((h, w), paint)
    wear = np.clip(0.80 + 0.22 * fbm(h, w, 40, 3, rng), 0, 1)
    alb = mixv(alb, lin('#A9A7A0')[None, None] * grain[..., None], (mp * wear * 0.9)[..., None])
    # lighting: sky ambient, lamp pools on the far side, our own restaurant's warm spill
    E = (E_SKY * 1.45)[None, None] * np.ones((h, w, 1), F32)
    for lx in LAMP_X:
        Dl = D
        dx = (xs[None, :] - VPX) * Dl[:, None] / FOC - (lx - VPX) * D_LAMP / FOC
        dz = Dl[:, None] - D_LAMP
        E = E + E_LAMP[None, None] * (2.2 * 30 / (30 + dx * dx + dz * dz * 1.0 + 49))[..., None]
    spill = smoothstep(Y_KERB_NEAR - 160, SH, ys)[:, None] ** 1.6
    # the light comes out through the glass-block facade: a soft grid of brighter patches
    Dn = np.maximum(D, 0.5)
    Xw = (xs[None, :] - VPX) * Dn[:, None] / FOC
    grid = 0.75 + 0.25 * (np.cos(Xw * 2 * np.pi / 0.62) * np.cos(Dn[:, None] * 2 * np.pi / 0.62)) ** 2
    E = E + (lin('#FFB46A') * 0.16)[None, None] * (spill * grid)[..., None]
    diffuse = alb * E
    col = diffuse * (1 - R[..., None]) + Mb * (R * 0.34)[..., None]
    # tram rails (steel catches the light) and their grooves
    rails = []
    for Dr in (24.6, 26.0, 19.3, 20.7):
        yr = y_ground(Dr)
        rails.append([(-100, yr), (SW + 100, yr)])
    mr = _aa_lines((h, w), rails, 1.8)
    mg = _aa_lines((h, w), [[(a[0][0], a[0][1] + 2.5), (a[1][0], a[1][1] + 2.5)] for a in rails], 1.6)
    railc = Mb * 0.9 + (E_SKY * 1.2)[None, None]
    col = mixv(col, col * 0.35, mg[..., None] * 0.8)
    col = mixv(col, railc, mr[..., None] * 0.85)
    # near-kerb arris catches light
    ma = _aa_lines((h, w), [[(-100, Y_KERB_NEAR + 1), (SW + 100, Y_KERB_NEAR + 1)]], 2.4)
    col = mixv(col, col * 1.6 + (E_SKY * 0.8)[None, None], ma[..., None] * 0.7)
    a = smoothstep(y_ground(D_FAC) - 6, y_ground(D_FAC) - 1, ys)[:, None] * np.ones((1, w), F32)
    L = Layer(h, w)
    L.rgb = col * a[..., None]
    L.a = a
    return L, R


def street_reflections(R, E_win, E_glow, E_tram, halo, tram, lamps_a):
    """Screen layer: lights mirrored in the wet street, streaked by its roughness."""
    h, w = R.shape
    ys = (np.arange(h, dtype=F32) + 0.5) / K
    xs = (np.arange(w, dtype=F32) + 0.5) / K
    tram_m = _mirror(tram.a, y_ground(D_TRAM), h)
    Ef = _mirror(E_win + E_glow, y_ground(D_FAC), h)
    El = _mirror(halo * (lamps_a[..., None] > -1), y_ground(D_LAMP), h)
    Et = _mirror(E_tram, y_ground(D_TRAM), h)
    Em = (Ef + El * 0.6) * (1 - tram_m)[..., None] + Et * 0.6
    near_w = smoothstep(2500, 3300, ys)[:, None, None]
    streak = mixv(gblur(Em, 2.5, 10) * 0.55 + gblur(Em, 4.0, 40) * 0.45,
                  gblur(Em, 4.5, 28) * 0.5 + gblur(Em, 7.0, 80) * 0.5, near_w)
    # broken by the texture of the wet asphalt (ripples run along the street)
    rng = np.random.default_rng(801)
    rip = 0.6 + 0.4 * smoothstep(-1.2, 1.2, fbm(h, w, 14, 3, rng, aniso=5))
    out = streak * (R * 1.35 * rip)[..., None]
    # direct light on the road: tram windows spill + headlight pool ahead of the tram
    yt = y_ground(D_TRAM)
    xn = TRAM_NOSE
    spill = np.exp(-((ys - (yt + 18)) / 26) ** 2)[:, None] * (xs < xn - 40)[None, :]
    pool = np.exp(-(((xs - (xn + 520)) / 520) ** 2)[None, :] - (((ys - (yt + 12)) / 18) ** 2)[:, None])
    out += (lin('#FFE0B4') * 0.05)[None, None] * spill[..., None] + (lin('#FFF0D8') * 0.45)[None, None] * pool[..., None]
    return out * smoothstep(y_ground(D_FAC) - 2, y_ground(D_FAC) + 4, ys)[:, None, None]


# --------------------------------------------------------------------------- #
# mist (screen) + bokeh / halation (screen)
# --------------------------------------------------------------------------- #

def street_mist(E_all):
    rng = np.random.default_rng(901)
    h, w = E_all.shape[:2]
    ys = (np.arange(h, dtype=F32) + 0.5) / K
    band = np.exp(-((ys - 2150) / 420) ** 2) * 0.9 + 0.25 * smoothstep(400, 2200, ys)
    n = 0.65 + 0.35 * smoothstep(-1.5, 1.5, fbm(h, w, 700 * K, 4, rng, aniso=3.0))
    fog = (lin('#6E80B4') * 0.014)[None, None] * (band[:, None] * n)[..., None]
    scatter = gblur(E_all, 40) * 0.018 + gblur(E_all, 140) * 0.016
    return fog + scatter


def street_bokeh(base_rgb):
    """Defocused reflections of the restaurant's own lights on the window + halation."""
    rng = np.random.default_rng(1001)
    h, w = base_rgb.shape[:2]
    E = np.zeros((h, w, 3), F32)
    discs = []
    # the restaurant's own pendants reflected in the window: a receding row of soft discs
    for row, (y_a, y_b, r_a, r_b, n, x_a, x_b) in enumerate([(0.60, 0.50, 105, 52, 6, 0.06, 0.62),
                                                             (0.86, 0.80, 80, 44, 4, 0.70, 1.02)]):
        for i in range(n):
            t = i / max(1, n - 1)
            r = (r_a + (r_b - r_a) * t) * K * rng.uniform(0.95, 1.05)
            x = (x_a + (x_b - x_a) * t ** 0.85) * w + rng.normal(0, 4)
            y = (y_a + (y_b - y_a) * t) * h + rng.normal(0, 3)
            discs.append((x, y, r, lin('#FFB767') * rng.uniform(0.05, 0.075) * (1 - 0.35 * t)))
    for i in range(7):                        # strays: candles, a far car, a cool LED
        r = rng.uniform(18, 50) * K
        x = rng.uniform(0.05, 0.95) * w
        y = rng.uniform(0.55, 0.98) * h
        c = lin(['#FFC98A', '#E8A050', '#B8C8FF'][rng.choice(3, p=[.5, .35, .15])])
        discs.append((x, y, r, c * rng.uniform(0.03, 0.07)))
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    for (x, y, r, c) in discs:
        x0, x1 = int(max(0, x - r - 3)), int(min(w, x + r + 4))
        y0, y1 = int(max(0, y - r - 3)), int(min(h, y + r + 4))
        if x1 <= x0 or y1 <= y0:
            continue
        d = np.sqrt((xx[y0:y1, x0:x1] - x) ** 2 + (yy[y0:y1, x0:x1] - y) ** 2)
        disc = np.clip(r + 0.5 - d, 0, 1)
        # cat's-eye vignetting towards the frame edges + brighter rim + faint onion rings
        ex, ey = (x / w - 0.5) * 2, (y / h - 0.5) * 2
        off = np.array([ex, ey]) * r * 0.45
        d2 = np.sqrt((xx[y0:y1, x0:x1] - (x - off[0])) ** 2 + (yy[y0:y1, x0:x1] - (y - off[1])) ** 2)
        disc *= np.clip(r * 1.05 + 0.5 - d2, 0, 1)
        prof = 0.75 + 0.35 * smoothstep(0.55 * r, r, d) + 0.04 * np.sin(d / max(r, 1) * 18)
        E[y0:y1, x0:x1] += (disc * prof)[..., None] * c
    E = gblur(E, 1.0)
    # halation: bright parts of the scene bleed softly (film / lens glow)
    hi = np.maximum(base_rgb - 0.45, 0)
    E += gblur(hi, 8) * 0.14 + gblur(hi, 30) * 0.05
    return E


# --------------------------------------------------------------------------- #
# finalisation: internal res -> full res 8-bit RGBA with grain; exact recombination
# --------------------------------------------------------------------------- #

def _grain(h, w, rng, amp):
    n = rng.standard_normal((h, w), dtype=F32)
    n = cv2.GaussianBlur(n, (3, 3), 0.55)
    return n * F32(amp / 0.62)


def _upscale_strips(src, fn, band=200, margin=4):
    """Upscale an internal-res array by 1/K in horizontal strips; fn(strip_full, y0_full, i)
    returns the uint8 output strip.  Keeps peak memory small."""
    h = src.shape[0]
    outs = []
    f = int(round(1 / K))
    for i, r0 in enumerate(range(0, h, band)):
        r1 = min(h, r0 + band)
        a0, a1 = max(0, r0 - margin), min(h, r1 + margin)
        up = cv2.resize(src[a0:a1], (src.shape[1] * f, (a1 - a0) * f), interpolation=cv2.INTER_CUBIC)
        up = up[(r0 - a0) * f:(r0 - a0 + r1 - r0) * f]
        outs.append(fn(up, r0 * f, i))
    return np.concatenate(outs, 0)


def finalize_layer(name, L=None, E=None, blur_r=LENS_R, grain=0.010, seed=0):
    """Normal layers: L (premultiplied linear).  Screen layers: E (linear emission).
    Lens-blur at internal res, convert to sRGB, upscale to full res, add film grain.
    Returns the full-res uint8 RGBA (straight alpha) exactly as stored in the PNG."""
    if L is not None:
        st = np.dstack([L.rgb, L.a])
        if blur_r:
            st = lens_blur(st, blur_r * K)
        a = np.clip(st[..., 3], 0, 1)
        rgb = np.where(a[..., None] > 1e-5, st[..., :3] / np.maximum(a, 1e-5)[..., None], 0)
        pm = np.dstack([lin_to_srgb(np.clip(rgb, 0, 1)) * a[..., None], a]).astype(F32)
        del st, rgb

        def fn(up, y0, i):
            rng = np.random.default_rng(10000 * (seed + 1) + i)
            a = np.clip(up[..., 3], 0, 1)
            c = np.where(a[..., None] > 1e-4, up[..., :3] / np.maximum(a, 1e-4)[..., None], 0)
            g = _grain(up.shape[0], up.shape[1], rng, grain)
            c = c + g[..., None] * (0.6 + 0.8 * c)
            c = c + _grain(up.shape[0], up.shape[1], rng, grain * 0.35)[..., None] * np.array([1, -0.6, 0.8], F32)
            return q8(np.dstack([np.clip(c, 0, 1), a]))
        return _upscale_strips(pm, fn)
    e = E
    if blur_r:
        e = lens_blur(e, blur_r * K)
    e_s = lin_to_srgb(tone(e)).astype(F32)

    def fn(up, y0, i):
        rng = np.random.default_rng(10000 * (seed + 1) + i)
        up = np.clip(up, 0, 1)
        g = _grain(up.shape[0], up.shape[1], rng, grain)
        up = np.clip(up + g[..., None] * np.sqrt(up) * 0.9, 0, 1)
        a8 = q8(up.max(axis=2))
        a = a8.astype(F32) / 255
        c = np.where(a[..., None] > 0, up / np.maximum(a, 1 / 255)[..., None], 0)
        return np.dstack([q8(np.clip(c, 0, 1)), a8])
    return _upscale_strips(e_s, fn)


def composite_layers(layers, canvas=None):
    """Recombine [(uint8 RGBA array or PNG path, blend), ...] bottom->top exactly like
    psdkit.Document.render (white canvas, straight alpha, cb += a*(B(cb, cs) - cb), clip).
    Returns float32 RGB 0..1."""
    for arr, blend in layers:
        if isinstance(arr, str):
            arr = np.asarray(Image.open(arr))
        h, w = arr.shape[:2]
        if canvas is None:
            canvas = np.ones((h, w, 3), F32)
        for y0 in range(0, h, 400):
            y1 = min(h, y0 + 400)
            sub = arr[y0:y1].astype(np.float32) / 255.0
            a = sub[..., 3] * 1.0
            psdkit.Document._blend_into(canvas[y0:y1], sub[..., :3], a, blend)
    return canvas


def _preview_layer(arr, name, blend):
    if blend == 'screen':
        a = arr[..., 3:4].astype(F32) / 255
        rgb = arr[..., :3].astype(F32) / 255 * a
        preview(rgb, name)
    else:
        preview(arr, name, bg='#7A7A7A')


def build_street(out_dir=OUT):
    """Generate the blue-hour street, its 14 layers (PNG) and the exact composite."""
    t0 = time.time()
    os.makedirs(out_dir, exist_ok=True)
    ldir = os.path.join(out_dir, 'street_layers')
    os.makedirs(ldir, exist_ok=True)
    log = lambda m: print(f'  [street {time.time() - t0:6.1f}s] {m}', flush=True)
    paths = {}

    def emit(name, arr):
        blend = dict(STREET_ORDER)[name]
        pth = os.path.join(ldir, f'{name}.png')
        save_rgba(arr, pth)
        _preview_layer(arr, f'layer_{name}.jpg', blend)
        paths[name] = pth
        log(f'{name} saved')

    rng = np.random.default_rng(1)
    sky = street_sky(rng)
    far, win_far = street_skylines(rng, sky)
    scene_far = Layer(*sky.a.shape)
    scene_far.over(sky)
    scene_far.over(far)
    emit('sky', finalize_layer('sky', L=sky, blur_r=0, grain=0.008, seed=1))
    del sky
    emit('buildings_far', finalize_layer('buildings_far', L=far, grain=0.009, seed=2))
    del far
    ctx = street_near(rng)
    E_win = street_windows(ctx, win_far)
    del win_far
    E_glow = street_glow(ctx)
    log('near + emission built')
    tram, E_tram = street_tram()
    lamps, halo = street_lamps()
    trees = street_trees()
    figs = street_figures()
    log('objects built')
    ground, R = street_ground(scene_far, ctx.layer, trees, tram, lamps)
    del scene_far
    emit('buildings_near', finalize_layer('buildings_near', L=ctx.layer, grain=0.010, seed=3))
    emit('ground', finalize_layer('ground', L=ground, grain=0.012, seed=4))
    del ground
    emit('windows_lights', finalize_layer('windows_lights', E=E_win + E_win * 0 + bloom(E_win), grain=0.010, seed=5))
    emit('street_glow', finalize_layer('street_glow', E=E_glow + bloom(E_glow), grain=0.010, seed=6))
    refl = street_reflections(R, E_win, E_glow, E_tram, halo, tram, lamps.a)
    emit('reflections', finalize_layer('reflections', E=refl, grain=0.012, seed=7))
    del refl, R
    mist = street_mist(E_win + E_glow + halo + E_tram)
    emit('mist', finalize_layer('mist', E=mist, blur_r=0, grain=0.006, seed=8))
    del mist, E_win, E_glow
    emit('trees', finalize_layer('trees', L=trees, grain=0.010, seed=9))
    emit('lamps', finalize_layer('lamps', L=lamps, grain=0.010, seed=10))
    emit('lamp_halos', finalize_layer('lamp_halos', E=halo, grain=0.008, seed=11))
    emit('figures', finalize_layer('figures', L=figs, blur_r=LENS_R * 0.8, grain=0.010, seed=12))
    emit('tram', finalize_layer('tram', L=tram, blur_r=LENS_R * 0.7, grain=0.010, seed=13))
    del trees, lamps, halo, figs, tram, E_tram, ctx
    # bokeh + halation are computed from the exact composite of everything below them
    comp = composite_layers([(paths[n], b) for n, b in STREET_ORDER if n != 'bokeh'])
    small = cv2.resize(comp, (int(SW * K), int(SH * K)), interpolation=cv2.INTER_AREA)
    del comp
    emit('bokeh', finalize_layer('bokeh', E=street_bokeh(srgb_to_lin(small)), blur_r=0, grain=0.006, seed=14))
    comp = composite_layers([(paths[n], b) for n, b in STREET_ORDER])
    out = q8(comp)
    del comp
    save_rgba(np.dstack([out, np.full(out.shape[:2], 255, np.uint8)]), os.path.join(out_dir, 'street_dusk.png'))
    preview(out, 'street_dusk.jpg')
    log('street_dusk.png composited')
    return paths


def bloom(E):
    """Soft glow around emitters (lens + atmosphere)."""
    return gblur(E, 8) * 0.07 + gblur(E, 30) * 0.025


# =========================================================================== #
# B — GLASS-BLOCK REFRACTION
# =========================================================================== #
#
# Model of one pressed-glass block (all distances scale with the block size, reference 566 px,
# measured on assets/gen/glassblock_wall_A.png where a block is ~560-600 px with ~28 px joints):
#
#   mortar | outer rim (rounded arris, flat flank)  | groove | inner rim | bevel | patterned face
#          0 ........................................ e1 ......... e2 ...... e3 ............ centre
#
# * The face refracts the scene behind it through a height field = pillow dome + rippled waves
#   (domain-warped sinusoids, a different pattern per block); displacement = -k * grad(height),
#   with a slightly different k per channel (chromatic hint).
# * The rims show the scene squeezed and smeared (light travelling through the thick side
#   walls), lifted and tinted green-blue, crossed by thin bright / dark lines at the steps.
# * Specular glints come from the same height field; a Fresnel term adds reflected room light on
#   steep slopes.  Mortar is light grey, finely textured, with a dark crevice at the glass.

def _rounded_rect_sdf(lx, ly, w, h, r):
    """Inward distance (px) from the edge of a w x h rounded rectangle (local coords)."""
    qx = np.abs(lx - w / 2) - (w / 2 - r)
    qy = np.abs(ly - h / 2) - (h / 2 - r)
    out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) + np.minimum(np.maximum(qx, qy), 0) - r
    return -out


def _gauss_line(d, d0, width):
    return np.exp(-0.5 * ((d - d0) / width) ** 2)


def _smin(a, b, k):
    """Smooth minimum (soft corners of the rim structure)."""
    return -k * np.logaddexp(-a / k, -b / k)


def glassblock_refract(scene_rgb, cols, rows, block_px, mortar_px, seed=0, tint='#A9C4BC',
                       mortar='#BEB8B0', light='#FFE2B8', light_level=1.0, mortar_level=1.0,
                       scene_blur=1.5, focus=(0.5, 0.5), parallax=0.9, distortion=1.0,
                       return_masks=False):
    """Render a wall of wavy pressed-glass blocks refracting `scene_rgb` (the view behind it).

    scene_rgb    float 0..1 or uint8 HxWx3 (sRGB) — what is behind the wall; cover-fitted
    cols, rows   number of blocks; block_px int or (w, h); mortar_px joint width (px)
    seed         pattern seed (each block gets its own ripple pattern)
    tint         glass body colour; tints the faces lightly and the rims strongly
    mortar       joint colour as lit; mortar_level scales it
    light        colour of the room light caught by glints / rims; light_level scales it
    parallax     how much the inner side walls widen towards the wall edges (camera centred)
    distortion   scales the ripple + pillow refraction
    Returns float32 RGBA (alpha = 1, straight) of size
    (rows*bh + (rows+1)*m) x (cols*bw + (cols+1)*m); with return_masks=True also a dict of
    float masks {'glass', 'mortar', 'face'}."""
    rng = np.random.default_rng(seed)
    bw, bh = (block_px, block_px) if np.isscalar(block_px) else block_px
    m = mortar_px
    W = cols * bw + (cols + 1) * m
    H = rows * bh + (rows + 1) * m
    bs = min(bw, bh) / 566.0
    # ---- scene behind the wall: cover-fit, linear light, slight softening ------------------
    sc = np.asarray(scene_rgb)
    sc = sc.astype(F32) / 255 if sc.dtype == np.uint8 else sc.astype(F32)
    sc = sc[..., :3]
    ih, iw = sc.shape[:2]
    s_ = max(W / iw, H / ih)
    nw, nh = max(W, round(iw * s_)), max(H, round(ih * s_))
    sc = cv2.resize(sc, (nw, nh), interpolation=cv2.INTER_AREA if s_ < 1 else cv2.INTER_CUBIC)
    ox, oy = int(round((nw - W) * focus[0])), int(round((nh - H) * focus[1]))
    sc = np.ascontiguousarray(sc[oy:oy + H, ox:ox + W])
    scene = srgb_to_lin(np.clip(sc, 0, 1))
    del sc
    if scene_blur:
        scene = gblur(scene, scene_blur * bs)
    scene_rim = gblur(scene, 2.0 * bs)
    small = cv2.resize(scene, (max(1, W // 8), max(1, H // 8)), interpolation=cv2.INTER_AREA)
    scene_mean = cv2.resize(gblur(small, 30 * bs / 8), (W, H), interpolation=cv2.INTER_LINEAR)
    scene_big = cv2.resize(gblur(small, 150 * bs / 8), (W, H), interpolation=cv2.INTER_LINEAR)
    del small
    tint_l = lin(tint)
    tint_n = tint_l / float(tint_l.max())
    light_l = lin(light) * light_level
    mortar_l = lin(mortar) * mortar_level
    # ---- per-block parameters ---------------------------------------------------------------
    nb = rows * cols
    ang = np.where(rng.random(nb) < 0.55, rng.normal(0, 0.25, nb), np.pi / 2 + rng.normal(0, 0.25, nb))
    lam = rng.uniform(0.17, 0.30, nb) * min(bw, bh)
    amp = rng.uniform(0.028, 0.050, nb) * min(bw, bh) * distortion
    ph = rng.uniform(0, 2 * np.pi, nb)
    ang2 = ang + np.pi / 2 + rng.normal(0, 0.3, nb)
    lam2 = lam * rng.uniform(0.6, 1.1, nb)
    amp2 = amp * rng.uniform(0.2, 0.5, nb)
    ph2 = rng.uniform(0, 2 * np.pi, nb)
    pillow = rng.uniform(0.030, 0.060, nb) * min(bw, bh) * distortion
    ang3 = ang + rng.normal(0, 0.5, nb)                    # fine ripple of the pressing
    lam3 = rng.uniform(0.05, 0.085, nb) * min(bw, bh)
    amp3 = rng.uniform(0.006, 0.012, nb) * min(bw, bh) * distortion
    ang3, lam3, amp3 = [np.asarray(q, F32) for q in (ang3, lam3, amp3)]
    # parallax: rim width factors per side (left, right, top, bottom) from the block offset
    bxc = (np.arange(cols) + 0.5) / cols * 2 - 1
    byc = (np.arange(rows) + 0.5) / rows * 2 - 1
    BX, BY = np.meshgrid(bxc, byc)
    BX, BY = BX.ravel(), BY.ravel()
    fL = 1 + parallax * np.maximum(0, -BX) + rng.normal(0, 0.04, nb)
    fR = 1 + parallax * np.maximum(0, BX) + rng.normal(0, 0.04, nb)
    fT = 1 + parallax * np.maximum(0, -BY) + rng.normal(0, 0.04, nb)
    fB = 1 + parallax * np.maximum(0, BY) + rng.normal(0, 0.04, nb)
    (ang, lam, amp, ph, ang2, lam2, amp2, ph2, pillow, fL, fR, fT, fB) = [
        np.asarray(q, F32) for q in (ang, lam, amp, ph, ang2, lam2, amp2, ph2, pillow, fL, fR, fT, fB)]
    # wall-wide warp fields (organic wobble of the ripples) + face-edge waviness
    warp_x = fbm(H, W, 0.42 * min(bw, bh), 3, rng, gain=0.45)
    warp_y = fbm(H, W, 0.42 * min(bw, bh), 3, rng, gain=0.45)
    edge_wav = fbm(H, W, 0.09 * min(bw, bh), 2, rng)
    # rim geometry (px, before the per-side parallax scaling)
    r_c = 7 * bs
    e1, e2, e3 = 30 * bs, 52 * bs, 66 * bs
    k_chroma = np.array([0.982, 1.0, 1.02], F32)
    out = np.zeros((H, W, 3), F32)
    mask_glass = np.zeros((H, W), F32)
    mask_face = np.zeros((H, W), F32)
    Lv = np.array([-0.45, -0.6, 0.66], F32)
    Lv /= np.linalg.norm(Lv)
    Hv = Lv + np.array([0, 0, 1], F32)
    Hv /= np.linalg.norm(Hv)
    period_y = bh + m
    for r in range(rows + 1):
        # strip: the joint above block-row r plus the block row (last strip: bottom joint)
        y0 = r * period_y
        y1 = min(H, y0 + period_y + (m if r == rows - 1 else 0))
        if r == rows:
            y0, y1 = rows * period_y, H
        if y1 <= y0:
            continue
        hh = y1 - y0
        yy = np.arange(y0, y1, dtype=F32)[:, None] + 0.5
        xx = np.arange(W, dtype=F32)[None, :] + 0.5
        ci = np.clip(np.floor((xx - m) / (bw + m)), 0, cols - 1).astype(np.int32)
        ri = np.clip(np.floor((yy - m) / (bh + m)), 0, rows - 1).astype(np.int32)
        lx = (xx - m - ci * (bw + m)) * np.ones((hh, 1), F32)
        ly = (yy - m - ri * (bh + m)) * np.ones((1, W), F32)
        bi = (ri * cols + ci) * np.ones((hh, W), np.int32)
        d_geo = _rounded_rect_sdf(lx, ly, bw, bh, r_c)          # true inward distance (<0 mortar)
        glass = np.clip(d_geo + 0.5, 0, 1)
        # parallax-scaled "structure distance": each side's rim widens by its factor
        dl, dr = lx / fL[bi], (bw - lx) / fR[bi]
        dt, db = ly / fT[bi], (bh - ly) / fB[bi]
        dxm = np.minimum(dl, dr)
        dym = np.minimum(dt, db)
        d = _smin(dxm, dym, 3.0 * bs)
        d = np.minimum(d, np.maximum(d_geo, 0) * 4 + d_geo)       # keep the true outer edge
        side_x = dxm < dym                                         # nearest edge is vertical
        nxg = np.where(side_x, np.where(dl < dr, -1.0, 1.0), 0.0).astype(F32)   # outward normal
        nyg = np.where(~side_x, np.where(dt < db, -1.0, 1.0), 0.0).astype(F32)
        # wavy border of the patterned face (as in the pressed originals)
        df = d + edge_wav[y0:y1] * 3.2 * bs
        face = smoothstep(e3 - 2 * bs, e3 + 26 * bs, df)
        face_hard = smoothstep(e3 - 1.2, e3 + 1.2, df)
        # ---- height field of the face: pillow + two warped ripple families -------------------
        u = (lx - bw / 2) / (bw / 2)
        v = (ly - bh / 2) / (bh / 2)
        X = xx * np.ones((hh, 1), F32) + warp_x[y0:y1] * lam[bi] * 0.55
        Y = yy * np.ones((1, W), F32) + warp_y[y0:y1] * lam[bi] * 0.55
        s1 = X * np.cos(ang[bi]) + Y * np.sin(ang[bi])
        s2 = X * np.cos(ang2[bi]) + Y * np.sin(ang2[bi])
        s3 = X * np.cos(ang3[bi]) + Y * np.sin(ang3[bi])
        hf = (amp[bi] * lam[bi] / (2 * np.pi) * np.sin(2 * np.pi * s1 / lam[bi] + ph[bi]) +
              amp2[bi] * lam2[bi] / (2 * np.pi) * np.sin(2 * np.pi * s2 / lam2[bi] + ph2[bi]) +
              amp3[bi] * lam3[bi] / (2 * np.pi) * np.sin(2 * np.pi * s3 / lam3[bi] + ph[bi] * 1.7))
        hp = pillow[bi] * (bw / 2) / (np.pi / 2) * np.cos(np.clip(u, -1, 1) * np.pi / 2) * \
            np.cos(np.clip(v, -1, 1) * np.pi / 2)
        Hf = ((hf + hp) * face).astype(F32)
        gy, gx = np.gradient(Hf)
        # ---- rim profile (heights in px): arris, flank, groove, inner rim, bevel -------------
        prof = (6 * bs * smoothstep(0, 8 * bs, d) - 3 * bs * _gauss_line(d, e1, 2.5 * bs)
                + 2 * bs * smoothstep(e1, e2, d) - 12 * bs * smoothstep(e2 + 3 * bs, e3, df))
        pgy, pgx = np.gradient(prof.astype(F32))
        # geometric surface slope: refraction offset ~ 0.33 * thickness * slope, with an
        # effective glass thickness of ~80 px per 566 px block
        tgx = gx / (80 * bs) + pgx * (1 - face)
        tgy = gy / (80 * bs) + pgy * (1 - face)
        # ---- refracted face ------------------------------------------------------------------
        col_face = np.empty((hh, W, 3), F32)
        bx = (xx - 0.5) * np.ones((hh, 1), F32)
        by = (yy - 0.5) * np.ones((1, W), F32)
        for c in range(3):
            col_face[..., c] = cv2.remap(np.ascontiguousarray(scene[..., c]),
                                         (bx - k_chroma[c] * gx).astype(F32), (by - k_chroma[c] * gy).astype(F32),
                                         cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # light concentration of the main waves (smooth, low gain; fine ripple excluded)
        lap = cv2.Laplacian(gblur(Hf, 10 * bs), cv2.CV_32F, ksize=3)
        col_face *= (1 - 0.16 * np.tanh(lap * 1.2))[..., None]
        # ---- rims: the scene squeezed through the thick side walls ---------------------------
        dd = np.clip(e3 - d, 0, None)
        push = dd * 3.4 + 4 * bs
        rim = np.dstack([cv2.remap(np.ascontiguousarray(scene_rim[..., c]),
                                   (bx + nxg * push).astype(F32), (by + nyg * push).astype(F32),
                                   cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT) for c in range(3)])
        lvl = lum(scene_mean[y0:y1])[..., None]
        lvb = lum(scene_big[y0:y1])[..., None]
        # thick glass gathers light from all around: rims glow, usually brighter than the face
        inner = smoothstep(e1 - 2 * bs, e1 + 2 * bs, d)[..., None]          # inner rim brighter
        rim = tint_n * (rim * (0.50 + 0.15 * inner) + (0.015 + 0.85 * lvb) * (0.85 + 0.45 * inner)
                        + 0.10 * light_l * (0.6 + 0.6 * inner))
        stri = 1 + 0.06 * np.sin(d / (2.4 * bs) * 2 * np.pi) + 0.04 * np.sin(d / (5.7 * bs) * 2 * np.pi + 1)
        rim *= stri[..., None]
        # ---- lines at the steps (bright arrises, dark grooves) ------------------------------
        lines = (-0.60 * _gauss_line(d_geo, 1.0 * bs, 1.0 * bs) + 0.55 * _gauss_line(d, 4.5 * bs, 1.3 * bs)
                 - 0.40 * _gauss_line(d, e1 - 2.5 * bs, 1.5 * bs) + 0.75 * _gauss_line(d, e1 + 1.2 * bs, 1.0 * bs)
                 + 0.45 * _gauss_line(d, e2 - 2 * bs, 1.6 * bs) + 0.80 * _gauss_line(df, e2 + 5 * bs, 1.2 * bs)
                 - 0.55 * _gauss_line(df, e3 - 2.5 * bs, 2.2 * bs) + 0.70 * _gauss_line(df, e3 + 0.8 * bs, 0.9 * bs))
        lift = (0.04 + 0.9 * lvb + 0.12 * light_l) * (0.6 * tint_n + 0.4)
        rim = rim + lift * np.maximum(lines, 0)[..., None]
        rim = rim * (1 + 0.8 * np.minimum(lines, 0))[..., None]
        # ---- combine face + rim, tint toward the edges, glints, Fresnel ---------------------
        tint_amt = 0.08 + 0.22 * (1 - smoothstep(e3, 0.5 * min(bw, bh), df))
        col_face = col_face * mixv(np.ones((1, 1, 3), F32), tint_n[None, None], tint_amt[..., None])
        col = mixv(rim, col_face, face_hard[..., None])
        nrm = np.dstack([-tgx, -tgy, np.ones_like(tgx)])
        nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
        ndh = np.clip(nrm @ Hv, 0, 1)
        spec = ndh ** 140 * 1.0 + ndh ** 22 * 0.05
        slope2 = tgx * tgx + tgy * tgy
        fres = 0.04 + 0.96 * (1 - 1 / np.sqrt(1 + slope2)) ** 5
        col = col * (1 - fres[..., None]) + (fres * (0.15 + 0.5 * lvb[..., 0]))[..., None] * light_l + \
            (spec * (0.3 + 0.7 * lvl[..., 0]) * glass)[..., None] * light_l
        # ---- specks (tiny bubbles in the glass) ----------------------------------------------
        nsp = int(W * hh * 6e-5)
        if nsp:
            sx = rng.integers(0, W, nsp)
            sy = rng.integers(0, hh, nsp)
            sp = np.zeros((hh, W), F32)
            sp[sy, sx] = rng.uniform(0.3, 1.0, nsp)
            sp = gblur(sp, 0.6) * 4.0
            col += (sp * glass)[..., None] * light_l * (0.12 + 0.5 * lvl)
        # ---- mortar: textured, darker in the crevice next to the glass --------------------
        dm = np.maximum(-d_geo, 0)
        mt = 1 + 0.06 * fbm(hh, W, 1.2, 2, rng) + 0.035 * fbm(hh, W, 9 * bs, 3, rng)
        ao = 1 - 0.38 * np.exp(-dm / (2.2 * bs)) - 0.12 * np.exp(-dm / (8 * bs))
        mcol = mortar_l[None, None] * (mt * ao)[..., None] + (0.05 * lvb) * tint_n
        col = mixv(mcol, col, glass[..., None])
        out[y0:y1] = col
        mask_glass[y0:y1] = glass
        mask_face[y0:y1] = face_hard * glass
    rgb = np.clip(lin_to_srgb(np.clip(out, 0, None)), 0, 1)
    del out
    g = _grain(H, W, rng, 0.008)
    rgb = np.clip(rgb + g[..., None] * (0.5 + 0.5 * rgb), 0, 1)
    res = np.dstack([rgb, np.ones((H, W), F32)]).astype(F32)
    if return_masks:
        return res, {'glass': mask_glass, 'mortar': 1 - mask_glass, 'face': mask_face}
    return res


# --------------------------------------------------------------------------- #
# blue-hour grade of the photographed wall (warm points stay amber)
# --------------------------------------------------------------------------- #

GRADE_MAP = [(0.00, '#0B0E1C'), (0.18, '#1A2040'), (0.36, '#2A3562'), (0.55, '#45508A'),
             (0.72, '#7378B0'), (0.88, '#AEB8E0'), (1.00, '#E0E6F6')]


def grade_blue_hour(rgb, strength=1.0, keep_warm=True):
    """Cool violet-blue blue-hour grade of an sRGB image (float 0..1 or uint8, HxWx3).

    Mid-tones and shadows go to indigo / dusk / violet (a gradient map blended with a cooled
    channel mix so texture and hue differences survive); the brightest warm points (lamps,
    hot reflections) are kept amber.  Processed in strips; returns float32 sRGB."""
    a = np.asarray(rgb)
    a = a.astype(F32) / 255 if a.dtype == np.uint8 else a.astype(F32)
    a = a[..., :3]
    out = np.empty_like(a)
    xs = np.array([t for t, _ in GRADE_MAP], F32)
    cs = np.stack([lin(c) for _, c in GRADE_MAP])
    M = np.array([[0.46, 0.14, 0.06], [0.10, 0.58, 0.12], [0.16, 0.34, 0.95]], F32)  # cooling mix
    for y0 in range(0, a.shape[0], 256):
        s = a[y0:y0 + 256]
        l_ = srgb_to_lin(s)
        Y = lum(l_)
        Ys = lin_to_srgb(Y)
        gm = np.stack([np.interp(Ys, xs, cs[:, c]) for c in range(3)], -1).astype(F32)
        mix = (l_ @ M.T) * 0.62
        cool = mixv(mix, gm, 0.62) * 0.95
        if keep_warm:
            warmth = np.clip((l_[..., 0] - l_[..., 2]) / (l_[..., 0] + l_[..., 2] + 1e-4), 0, 1)
            keep = smoothstep(0.16, 0.55, Y) * smoothstep(0.30, 0.7, warmth)
            amber = l_ * np.array([1.08, 0.80, 0.48], F32) * 1.1
            cool = mixv(cool, amber, keep[..., None])
        res = mixv(l_, cool, strength)
        out[y0:y0 + 256] = lin_to_srgb(res)
    return np.clip(out, 0, 1)


# =========================================================================== #
# C — RAIN ON GLASS
# =========================================================================== #

def _stamp(canvas, x0, y0, rgba_pm):
    """Premultiplied 'over' of a small patch into the canvas (clipped)."""
    h, w = canvas.shape[:2]
    ph, pw = rgba_pm.shape[:2]
    cx0, cy0 = max(0, x0), max(0, y0)
    cx1, cy1 = min(w, x0 + pw), min(h, y0 + ph)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    p = rgba_pm[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
    dst = canvas[cy0:cy1, cx0:cx1]
    dst *= (1 - p[..., 3:4])
    dst += p


def _droplet(r, rng, elong=1.0):
    """One droplet as a premultiplied RGBA patch: dark refractive rim, light body, caustic
    crescent at the bottom (light focused through the lens) and a specular highlight."""
    n = int(np.ceil(r * elong + 3))
    yy, xx = np.mgrid[-n:n + 1, -n:n + 1].astype(F32)
    yy = yy + 0.25 * r * (elong - 1)
    ry = r * elong
    # slightly flattened at the bottom (gravity)
    d = np.sqrt((xx / r) ** 2 + (yy / ry) ** 2 * np.where(yy > 0, 1.15, 0.95))
    edge = np.clip((1 - d) * r + 0.5, 0, 1)
    pm = np.zeros(xx.shape + (4,), F32)

    def over(alpha, col):
        a = np.clip(alpha, 0, 1)[..., None]
        pm[...] = pm * (1 - a) + np.concatenate([np.asarray(col, F32) * a, a], -1)

    over(edge * 0.07, (0.86, 0.90, 0.96))
    over(edge * smoothstep(0.5, 0.97, d) * (0.42 + 0.15 * (yy < 0)), (0.03, 0.04, 0.07))
    cres = edge * smoothstep(0.15, 0.75, (0.25 * xx / r + 0.97 * yy / ry)) * (1 - smoothstep(0.72, 0.95, d))
    over(cres * 0.28, (1.0, 0.93, 0.80))
    hx, hy = -0.32 * r, -0.40 * ry
    hr = max(0.55, 0.20 * r)
    hl = np.exp(-(((xx - hx) / hr) ** 2 + ((yy - hy) / (hr * 0.8)) ** 2))
    over(hl * edge * 0.9, (1.0, 1.0, 1.0))
    return pm


def rain_on_glass(w=3000, h=3600, seed=7, density=1.0, runs=9):
    """RGBA overlay (straight alpha, float32): fine droplets + a few runs, subtle.
    Put it in 'normal' blend over a window view (optionally a second copy in 'screen')."""
    rng = np.random.default_rng(seed)
    pm = np.zeros((h, w, 4), F32)
    # ---- runs: wandering vertical trails that cleared the small drops ------------------------
    trail = np.zeros((h * 2, w * 2), np.uint8)
    paths = []
    for i in range(runs):
        x = rng.uniform(0.05, 0.95) * w
        y_top = rng.uniform(-0.1, 0.5) * h
        L = rng.uniform(0.25, 0.65) * h
        n = int(L / 6)
        dx = np.cumsum(gblur(rng.normal(0, 1.8, n).astype(F32)[None, :], 4)[0])
        dx += gblur(np.cumsum(np.where(rng.random(n) < 0.03, rng.normal(0, 10, n), 0)).astype(F32)[None, :], 6)[0]
        ys = y_top + np.arange(n) * 6.0
        xs = x + dx
        wd = np.clip(np.linspace(2.2, 5.5, n) + rng.normal(0, 0.4, n), 1.5, 7)
        paths.append((xs, ys, wd))
        for j in range(n - 1):
            p0 = (int(xs[j] * 2 * 16), int(ys[j] * 2 * 16))
            p1 = (int(xs[j + 1] * 2 * 16), int(ys[j + 1] * 2 * 16))
            cv2.line(trail, p0, p1, 255, max(1, int(wd[j] * 2)), cv2.LINE_AA, 4)
    tm = cv2.resize(trail.astype(F32) / 255, (w, h), interpolation=cv2.INTER_AREA)
    del trail
    clear = cv2.dilate(tm, np.ones((9, 9), np.uint8))           # no small drops near a run
    # trail shading: water film edges (dark left rim, bright right rim), a faint body
    gx = cv2.Sobel(gblur(tm, 0.8), cv2.CV_32F, 1, 0, ksize=3)
    rim_d = np.clip(gx, 0, None) * 0.9
    rim_l = np.clip(-gx, 0, None) * 0.9
    for alpha, col in [(tm * 0.05, (0.85, 0.9, 0.95)), (rim_d * 0.38, (0.03, 0.04, 0.07)),
                       (rim_l * 0.20, (1.0, 0.97, 0.92))]:
        a = np.clip(alpha, 0, 1)[..., None]
        pm[...] = pm * (1 - a) + np.concatenate([np.broadcast_to(np.asarray(col, F32), a.shape[:2] + (3,)) * a, a], -1)
    # ---- droplets: power-law sizes, none on the cleared runs --------------------------------
    area = w * h / 1e6
    counts = [(int(900 * area * density), 0.9, 2.2), (int(380 * area * density), 2.2, 4.5),
              (int(90 * area * density), 4.5, 9.0), (int(14 * area * density), 9.0, 16.0)]
    drops = []
    for cnt, r0, r1 in counts:
        for _ in range(cnt):
            r = r0 * (r1 / r0) ** rng.random()
            x, y = rng.uniform(0, w), rng.uniform(0, h)
            if clear[int(min(h - 1, y)), int(min(w - 1, x))] > 0.05:
                continue
            drops.append((x, y, r))
    # beads left behind along each run + a heavy head at its end
    for xs, ys, wd in paths:
        for j in range(0, len(xs), int(rng.integers(9, 16))):
            if rng.random() < 0.6:
                drops.append((xs[j] + rng.normal(0, 1), ys[j], wd[j] * rng.uniform(0.6, 1.0)))
        drops.append((xs[-1], ys[-1] + 4, wd[-1] * 1.9))
    cache = {}
    for x, y, r in sorted(drops, key=lambda t: t[2]):
        key = round(r * 4) / 4
        el = 1.0 + 0.12 * min(1, r / 10)
        if key not in cache:
            cache[key] = _droplet(key, rng, el)
        p = cache[key]
        n = (p.shape[0] - 1) // 2
        _stamp(pm, int(round(x)) - n, int(round(y)) - n, p)
    a = np.clip(pm[..., 3], 0, 1)
    rgb = np.where(a[..., None] > 1e-5, pm[..., :3] / np.maximum(a, 1e-5)[..., None], 0)
    return np.dstack([np.clip(rgb, 0, 1), a]).astype(F32)


# =========================================================================== #
# build: assets, index.json, contact sheet
# =========================================================================== #

GB_COLS, GB_ROWS, GB_BLOCK, GB_MORTAR = 5, 6, 566, 28


def _gb_rects(cols=GB_COLS, rows=GB_ROWS, b=GB_BLOCK, m=GB_MORTAR):
    return [[m + c * (b + m), m + r * (b + m), m + c * (b + m) + b, m + r * (b + m) + b]
            for r in range(rows) for c in range(cols)]


def _load_rgb(path):
    return np.asarray(Image.open(path).convert('RGB'))


def _save_mask(m, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(q8(m), 'L').save(path, compress_level=6)


def build_glass(out_dir=OUT):
    """glassblock_dusk / _warm / _canopy (+ glass and face masks) and the graded wall A."""
    res = {}
    t0 = time.time()
    log = lambda m_: print(f'  [glass {time.time() - t0:6.1f}s] {m_}', flush=True)
    jobs = [
        ('glassblock_dusk', lambda: _load_rgb(os.path.join(out_dir, 'street_dusk.png')),
         dict(seed=21, tint='#A9C4BC', mortar='#B6A998', mortar_level=0.42, light='#FFC890',
              light_level=0.75, scene_blur=1.0, focus=(0.47, 0.5))),
        ('glassblock_warm', lambda: _warm_scene(),
         dict(seed=22, tint='#A9C4BC', mortar='#C4BCB2', mortar_level=0.95, light='#FFD9A8',
              light_level=1.0, scene_blur=0.0, focus=(0.36, 0.5))),
        ('glassblock_canopy', lambda: _canopy_scene(),
         dict(seed=23, tint='#A9C4BC', mortar='#C6C1BA', mortar_level=1.0, light='#FFF0DC',
              light_level=1.1, scene_blur=1.0, focus=(0.5, 0.5))),
    ]
    for name, scene_fn, kw in jobs:
        scene = scene_fn()
        out, masks = glassblock_refract(scene, GB_COLS, GB_ROWS, GB_BLOCK, GB_MORTAR, return_masks=True, **kw)
        del scene
        save_rgba(q8(out), os.path.join(out_dir, f'{name}.png'))
        _save_mask(masks['glass'], os.path.join(out_dir, f'{name}_mask_glass.png'))
        _save_mask(masks['face'], os.path.join(out_dir, f'{name}_mask_face.png'))
        preview(out, f'{name}.jpg')
        res[name] = out.shape[:2]
        del out, masks
        log(name)
    wa = _load_rgb(P('assets', 'gen', 'glassblock_wall_A.png'))
    g = grade_blue_hour(wa)
    del wa
    out = np.dstack([q8(g), np.full(g.shape[:2], 255, np.uint8)])
    save_rgba(out, os.path.join(out_dir, 'glassblock_A_dusk_grade.png'))
    preview(out, 'glassblock_A_dusk_grade.jpg')
    log('glassblock_A_dusk_grade')
    return res


def _warm_scene():
    """cabins_row softened (seen out of focus through the blocks)."""
    a = _load_rgb(P('assets', 'gen', 'cabins_row.png')).astype(F32) / 255
    a = cv2.resize(a, (a.shape[1] // 2, a.shape[0] // 2), interpolation=cv2.INTER_AREA)
    a = lin_to_srgb(gblur(srgb_to_lin(a), 13.0))
    return a


def _canopy_scene():
    """void_lookup_B: the tree canopy and the round skylight above it."""
    a = _load_rgb(P('assets', 'gen', 'void_lookup_B.png'))
    return a[260:3560, 520:3150]


def build_rain(out_dir=OUT):
    r = rain_on_glass(3000, 3600, seed=7)
    save_rgba(q8(r), os.path.join(out_dir, 'rain_on_glass.png'))
    preview(r, 'rain_on_glass.jpg', bg='#20263A')
    return r.shape[:2]


# --------------------------------------------------------------------------- #
# contact sheet
# --------------------------------------------------------------------------- #

def _font(size, light=True):
    from PIL import ImageFont
    f = P('assets', 'fonts', 'IBMPlexMono-Light.ttf' if light else 'IBMPlexMono-Regular.ttf')
    try:
        return ImageFont.truetype(f, size)
    except OSError:
        return ImageFont.load_default()


def _thumb(path_or_arr, w, h=None, bg=(122, 122, 122), screen=False):
    a = np.asarray(Image.open(path_or_arr)) if isinstance(path_or_arr, str) else path_or_arr
    if a.dtype != np.uint8:
        a = q8(a)
    if a.ndim == 2:
        a = np.dstack([a] * 3)
    if a.shape[2] == 4:
        al = a[..., 3:4].astype(F32) / 255
        if screen:
            a = (a[..., :3].astype(F32) * al).astype(np.uint8)
        else:
            a = (a[..., :3].astype(F32) * al + np.array(bg, F32) * (1 - al)).astype(np.uint8)
    hh = h or round(a.shape[0] * w / a.shape[1])
    return Image.fromarray(cv2.resize(np.ascontiguousarray(a[..., :3]), (w, hh), interpolation=cv2.INTER_AREA))


def build_contact(out_dir=OUT, path=CONTACT):
    from PIL import ImageDraw
    Wc = 3600
    pad = 40
    f_t, f_l, f_s = _font(46, False), _font(26), _font(20)
    tiles = []          # (image, label, sublabel)
    sheet_rows = []
    # row 1: street composite
    sheet_rows.append([(_thumb(os.path.join(out_dir, 'street_dusk.png'), 2300),
                        'street_dusk.png  5400x3800', 'blue-hour street, exact recombination of the 14 layers')])
    # row 2/3: layers
    lay = []
    for name, blend in STREET_ORDER:
        pth = os.path.join(out_dir, 'street_layers', f'{name}.png')
        lay.append((_thumb(pth, 480, screen=blend == 'screen'),
                    f'{name}', f'{blend}' + (' (shown on black)' if blend == 'screen' else ' (on grey)')))
    sheet_rows.append(lay[:7])
    sheet_rows.append(lay[7:])
    # row 4: glass walls + grade + rain
    row = []
    for nm in ('glassblock_dusk', 'glassblock_warm', 'glassblock_canopy'):
        row.append((_thumb(os.path.join(out_dir, f'{nm}.png'), 600), f'{nm}.png', '2998x3592  5x6 blocks'))
    row.append((_thumb(os.path.join(out_dir, 'glassblock_A_dusk_grade.png'), 900),
                'glassblock_A_dusk_grade.png', '4736x3552 (graded source)'))
    row.append((_thumb(os.path.join(out_dir, 'rain_on_glass.png'), 600, bg=(32, 38, 58)),
                'rain_on_glass.png', '3000x3600 RGBA (on dusk blue)'))
    sheet_rows.append(row)
    # row 5: 100 % crops — ours vs. the real wall A
    A = np.asarray(Image.open(P('assets', 'gen', 'glassblock_wall_A.png')).convert('RGB'))
    crops = []
    for nm, (x, y) in [('glassblock_warm', (606, 606)), ('glassblock_canopy', (1200, 1200)),
                       ('glassblock_dusk', (10, 1800))]:
        a = np.asarray(Image.open(os.path.join(out_dir, f'{nm}.png')).convert('RGB'))[y:y + 640, x:x + 640]
        crops.append((Image.fromarray(np.ascontiguousarray(a)), f'OURS 100% · {nm}', f'crop x{x} y{y} 640x640'))
    for (x, y) in [(870, 1160), (1690, 1790), (2700, 2330)]:
        crops.append((Image.fromarray(np.ascontiguousarray(A[y:y + 640, x:x + 640])),
                      'REFERENCE 100% · glassblock_wall_A', f'crop x{x} y{y} 640x640'))
    sheet_rows.append(crops[:3])
    sheet_rows.append(crops[3:])
    # row 6: street 100 % crops
    S = np.asarray(Image.open(os.path.join(out_dir, 'street_dusk.png')).convert('RGB'))
    sc = []
    for (x, y, lab) in [(1350, 1850, 'tram + cafe terrace'), (3350, 1500, 'restaurant, tree, figures'),
                        (2850, 1050, 'side street'), (3200, 2330, 'wet road, zebra, reflections')]:
        sc.append((Image.fromarray(np.ascontiguousarray(S[y:y + 800, x:x + 800])), f'street 100% · {lab}', f'x{x} y{y}'))
    del S, A
    sheet_rows.append(sc)
    # layout
    blocks = []
    for r in sheet_rows:
        tw = sum(t[0].width for t in r) + pad * (len(r) - 1)
        sc_ = min(1.0, (Wc - 2 * pad) / tw)
        rr = [(t[0].resize((max(1, round(t[0].width * sc_)), max(1, round(t[0].height * sc_))), Image.LANCZOS),
               t[1], t[2]) for t in r]
        blocks.append(rr)
    Hc = 130 + sum(max(t[0].height for t in r) + 110 for r in blocks) + pad
    sheet = Image.new('RGB', (Wc, Hc), (238, 229, 211))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 34), 'OUTSIDE — blue-hour street · glass-block refraction · rain on glass', fill=(43, 36, 32), font=f_t)
    y = 130
    for rr in blocks:
        x = pad
        hmax = max(t[0].height for t in rr)
        for im, lab, sub in rr:
            sheet.paste(im, (x, y))
            d.text((x, y + im.height + 10), lab, fill=(43, 36, 32), font=f_l)
            d.text((x, y + im.height + 44), sub, fill=(110, 100, 92), font=f_s)
            x += im.width + pad
        y += hmax + 110
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sheet.save(path, quality=88)
    return path


# --------------------------------------------------------------------------- #
# index.json
# --------------------------------------------------------------------------- #

def _size(p):
    with Image.open(p) as im:
        return list(im.size)


def write_index(out_dir=OUT):
    rel = lambda p: os.path.relpath(p, ROOT)
    O = lambda *a: os.path.join(out_dir, *a)
    lamps = [[round(x), round(y)] for x, y in lamp_centres()]
    items = []
    items.append(dict(
        path=rel(O('street_dusk.png')), size=_size(O('street_dusk.png')),
        description='Blue-hour city street seen from inside the restaurant (seated eye height 1.3 m, '
                    'looking straight across): indigo->dusk->violet sky with a faint warm band, two '
                    'hazed skyline depths (600 m, 200 m) + the opposite Haussmann-style facades '
                    '(55 m) with lit windows, shopfronts with patrons, a side street receding to the '
                    'vanishing point, street lamps with halos, overhead tram wires, a motion-blurred '
                    'tram, street trees, small cool pedestrian silhouettes, wet road with streaked '
                    'reflections, a zebra crossing, interior pendant reflections as bokeh. Soft focus '
                    '(lens disc ~7 px), film grain. Opaque RGBA.',
        anchors=dict(horizon_y=HZ, vanishing_point=[VPX, HZ], facade_ground_y=round(y_ground(D_FAC), 1),
                     far_kerb_y=round(Y_KERB_FAR, 1), near_kerb_y=round(Y_KERB_NEAR, 1),
                     tram_nose_x=TRAM_NOSE, tram_body_y=[round(y_at(D_TRAM, 3.44)), round(y_at(D_TRAM, 0.2))],
                     lamp_lantern_centres=lamps, side_street_gap_x=list(GAP),
                     tree_trunks_x=TREE_X, figures=[dict(name=n, x=round(x), depth_m=d_) for n, x, d_, f in FIGURES],
                     ground_y_of_depth='y = 2250 + 4680 / D  (D metres)'),
        suggested_use='Collage 01 outside view (behind / through the glass-block facade) or as a cool '
                      'blue-hour plate; rebuild it in the PSD from street_layers/ to tweak each depth.'))
    layers = []
    for i, (name, blend) in enumerate(STREET_ORDER):
        p = O('street_layers', f'{name}.png')
        layers.append(dict(order=i, name=name, path=rel(p), size=_size(p), blend=blend, opacity=1.0,
                           x=0, y=0, description=LAYER_DESC[name]))
    items.append(dict(
        path=rel(O('street_layers')), kind='layer stack',
        description='The 14 full-canvas (5400x3800) RGBA layers of street_dusk.png, bottom -> top. '
                    'Stacking them at (0,0) with the listed blend modes (normal / screen, 100 %, '
                    'straight alpha, Photoshop formulas as in src/psdkit.py) reproduces street_dusk.png '
                    'exactly (verified bit-exact with outside.composite_layers / psdkit).',
        layers=layers,
        suggested_use='psdkit: Pixel(name, rgba, 0, 0, blend=blend) for each, in order, inside a group '
                      '"OUTSIDE · street"; screen layers can be dimmed by opacity to tune the mood.'))
    rects = _gb_rects()
    gb_common = dict(grid=dict(cols=GB_COLS, rows=GB_ROWS, block_px=GB_BLOCK, mortar_px=GB_MORTAR,
                               block_rects_xyxy=rects,
                               note='block (c, r) = [28 + c*594, 28 + r*594, +566, +566]; outer mortar 28 px'))
    for nm, desc, use in [
        ('glassblock_dusk', 'street_dusk seen through a 5x6 wall of wavy pressed glass blocks: blue street '
                            'in the faces, warm interior light caught in the celadon rims, mortar lit low '
                            'from inside.', 'Collage 01: the glass-block facade between the void and the street.'),
        ('glassblock_warm', 'A softened cabins_row (amber oak, terracotta velvet) seen through the blocks.',
         'Collage 02: the glass-block screen at the edge of the dining room / cabins.'),
        ('glassblock_canopy', 'void_lookup_B tree canopy + round skylight seen through the blocks '
                              '(green-gold, bright).', 'Collage 01: glass blocks glowing with the void core.')]:
        p = O(f'{nm}.png')
        items.append(dict(path=rel(p), size=_size(p), description=desc + ' Opaque RGBA (alpha 255).',
                          anchors=gb_common, suggested_use=use,
                          masks=dict(glass=rel(O(f'{nm}_mask_glass.png')),
                                     face=rel(O(f'{nm}_mask_face.png')),
                                     note='8-bit L, white = glass (incl. rims) / white = patterned face only; '
                                          'invert glass for the mortar grid')))
        for mk in ('glass', 'face'):
            mp = O(f'{nm}_mask_{mk}.png')
            items.append(dict(path=rel(mp), size=_size(mp), kind='mask',
                              description=f'{mk} mask of {nm}.png (white = {mk})',
                              suggested_use='layer mask / clipping base for tints inside the glass or on the mortar'))
    p = O('glassblock_A_dusk_grade.png')
    items.append(dict(path=rel(p), size=_size(p),
                      description='assets/gen/glassblock_wall_A.png graded to blue hour at native size: cool '
                                  'indigo / dusk / violet mid-tones, celadon-blue rims, the brightest warm '
                                  'points (pendants, hot reflections) kept amber. Opaque RGBA.',
                      anchors=dict(same_pixel_grid_as='assets/gen/glassblock_wall_A.png'),
                      suggested_use='Drop-in replacement for wall A where the scene is at blue hour (collage 01 facade).'))
    p = O('rain_on_glass.png')
    items.append(dict(path=rel(p), size=_size(p),
                      description='Rain on a window: ~10k fine droplets (dark refractive rim, soft body, '
                                  'caustic crescent, specular point) + 9 wandering runs with beads and heads. '
                                  'Straight-alpha RGBA, mostly transparent.',
                      suggested_use='Normal blend over any window view at 60-100 %; a duplicate in screen '
                                    'at 30 % adds sparkle. Scale freely (designed at ~glass-block size).'))
    idx = dict(area='outside', module='src/lib/outside.py', build='python3 -c "from lib import outside; outside.build()"  (run from src/)',
               contact_sheet=rel(CONTACT), items=items)
    with open(O('index.json'), 'w') as f:
        json.dump(idx, f, indent=1)
    return idx


LAYER_DESC = {
    'sky': 'opaque sky gradient (indigo #151A30 top -> dusk -> violet -> faint warm band at the horizon) + thin stratus, grain',
    'buildings_far': 'two hazed skyline bands (600 m with spire + dome, 200 m), cooler/lighter with distance',
    'buildings_near': 'opposite facades (55 m): stone / brick / stucco / shuttered, mansards, chimneys, balconies, unlit glass, awnings, side-street walls',
    'ground': 'opaque wet pavements + road: asphalt texture, tram rails, worn paint + zebra crossing, mirrored scene in the water film, restaurant light spill at the bottom',
    'windows_lights': 'emission of lit windows (warm, curtains, blinds, cool, TV) incl. tiny far-skyline windows, with bloom',
    'street_glow': 'shop interiors with silhouetted patrons, gooseneck fascia lamps, light spill on the far pavement, side-street shops',
    'reflections': 'lights mirrored in the wet street, streaked vertically; tram headlight pool',
    'mist': 'low blue street-level fog + atmospheric scattering of all lights',
    'trees': 'four street trees (one in the side street), dark crowns warm-lit from below',
    'lamps': 'cast-iron lamp posts with glowing lanterns + overhead tram wires (contact, messenger, droppers, span wires)',
    'lamp_halos': 'lantern halos, mist cones and light pools',
    'figures': 'pedestrians keyed from diners_silhouettes.png: cafe-terrace couple, waiter, standing couple, walker, woman with coffee, two in the side street',
    'tram': 'low-floor tram (nose at x=1800) moving right, 84 px motion blur, lit saloon with passenger silhouettes',
    'bokeh': 'out-of-focus reflections of the restaurant pendants in the window + halation of the bright parts',
}


def verify_street_exact(out_dir=OUT, box=(1200, 1600, 2400, 2800)):
    """Check that psdkit.Document renders the layer stack to exactly street_dusk.png (on a crop)."""
    x0, y0, x1, y1 = box
    doc = psdkit.Document(x1 - x0, y1 - y0)
    for name, blend in STREET_ORDER:
        a = np.asarray(Image.open(os.path.join(out_dir, 'street_layers', f'{name}.png')))[y0:y1, x0:x1]
        doc.add(psdkit.Pixel(name, a, 0, 0, blend=blend))
    r = q8(doc.render())
    ref = np.asarray(Image.open(os.path.join(out_dir, 'street_dusk.png')))[y0:y1, x0:x1, :3]
    return int(np.abs(r.astype(int) - ref.astype(int)).max())


def build():
    """Regenerate every asset of the 'outside' area, index.json and the contact sheet."""
    os.makedirs(OUT, exist_ok=True)
    build_street(OUT)
    print('  exactness check (max abs diff, psdkit vs street_dusk.png):', verify_street_exact(OUT))
    build_glass(OUT)
    build_rain(OUT)
    write_index(OUT)
    build_contact(OUT)
    print('  contact sheet:', CONTACT)


if __name__ == '__main__':
    build()
