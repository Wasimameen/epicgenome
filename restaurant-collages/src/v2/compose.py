#!/usr/bin/env python3
"""compose (v2) — data-driven page composer for the two A3 PORTRAIT atmosphere collages.

The v2 look (client reference): warm cream paper; a tracked serif title + tiny italic subtitle
top-left; ONE perspective render of the space behind a broken, stepped outline; torn-paper and
cut-rectangle MATERIAL fragments overlapping it in front and behind (2.5D, soft warm shadows,
white paper-core rims on the torn edges); "echo" patches cut from the render itself; a subtle
colour-intensity wash where spaces overlap; thin handwritten notes with hand-drawn curved arrows.

Everything is placed from plain data in src/v2/layout.py (PROVISIONAL until the real renders
exist).  The PSD is fully layered and non-destructive: every fragment is the full swatch crop
with a layer MASK for its tear, its own shadow layer and rim layer, in its own group; the
intensity washes and the paper tone are Solid Color fills; every piece of type is a raster
layer with a hidden live-type twin ('EDIT - ...').

Run from restaurant-collages/:
    python3 src/v2/compose.py --sheet 1             preview  -> build/v2/preview/sheet1.jpg
    python3 src/v2/compose.py --sheet 2 --crops     + 100 % detail crops in build/v2/preview/crops/
    python3 src/v2/compose.py --sheet all --final   PSD + JPEG + preview + layer tree + verification
    python3 src/v2/compose.py --combined            A3 landscape side-by-side of the two final JPEGs
    python3 src/v2/compose.py --combined --from-preview      the same from the previews (for review)

Inputs (missing -> clearly named placeholder in previews; --final REFUSES to run):
    build/v2/render/view{1,2}.png    RGB render, about 2700 x 3600
    build/v2/swatch/<name>.png       RGB material swatch, about 1600 x 2000 (names: SWATCHES)
Outputs (--final): output/v2/<slug>.psd / .jpg / _preview.jpg / _layers.txt, build/v2/final/<slug>/report.json
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import math
import os
import subprocess
import sys
import time

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
ROOT = os.path.dirname(SRC)
for _p in (SRC, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import psdkit  # noqa: E402
from psdkit import Document, Group, Pixel, Fill, Text  # noqa: E402
from lib import compose as C  # noqa: E402  (load / resize / blur helpers; its W, H are v1 landscape - unused)
from lib import typeset as T  # noqa: E402
from lib.collage_common import Builder, PS_FONT  # noqa: E402
import layout as LAYOUT  # noqa: E402  (src/v2/layout.py)

Image.MAX_IMAGE_PIXELS = None
cv2.setNumThreads(4)

# --------------------------------------------------------------------------------------------- #
# page, palette, type
# --------------------------------------------------------------------------------------------- #
PW, PH, DPI = 3508, 4961, 300            # A3 portrait @ 300 ppi
INK = '#2A2420'                           # title + notes
INK_SOFT = '#6B625A'                      # subtitle + sensory notes
INK_FOOT = '#8A8178'                      # footer key line
CREAM = '#ECE6DA'                         # target paper colour (after the fibre layer)
SHADOW = '#3A2A1F'                        # warm dark for every drop shadow
RIM = '#F6F2EA'                           # torn paper core
INTENSITY_COLOR = '#C27A3E'

HAND = 'hand'                             # Nothing You Could Do (OFL), assets/fonts/hand/
T._FONT_SPECS.setdefault(HAND, (None, None, os.path.join('hand', 'NothingYouCouldDo'),
                                'Nothing You Could Do', 'normal', 400))
PS_V2 = dict(PS_FONT, hand='NothingYouCouldDo')
NOTE_STYLE = {
    'note':  {'size': 78, 'color': INK, 'tracking': 30, 'leading': 1.02, 'opacity': 1.0},
    'sense': {'size': 60, 'color': INK_SOFT, 'tracking': 40, 'leading': 1.05, 'opacity': 1.0},
}
ARROW = {'width': 2.8, 'head': 26.0, 'opacity': 0.92, 'gap': 22.0, 'halo': 3.0, 'halo_opacity': 0.45}

# torn edge: 1-D fractal displacement along each torn side, (sigma px, amplitude px) per octave
TEAR = ((85.0, 12.0), (24.0, 5.0), (6.5, 2.0), (1.8, 0.8))
RIM_W = (2.0, 6.0)                        # paper-core rim width range, px
SHADOW_DEFAULT = (4, 6, 12, 0.20)         # (dx, dy, blur sigma, opacity) - per fragment overridable
SHADOW_BEHIND = (3, 4, 9, 0.14)

# --------------------------------------------------------------------------------------------- #
# files
# --------------------------------------------------------------------------------------------- #
V2_BUILD = os.path.join(ROOT, 'build', 'v2')
RENDER_DIR = os.path.join(V2_BUILD, 'render')
SWATCH_DIR = os.path.join(V2_BUILD, 'swatch')
PREVIEW_DIR = os.path.join(V2_BUILD, 'preview')
FINAL_BUILD = os.path.join(V2_BUILD, 'final')
OUT_DIR = os.path.join(ROOT, 'output', 'v2')
ICC_PATH = os.path.join(SRC, 'sRGB.icc')

SWATCHES = ('split_face_stone', 'travertine', 'concrete', 'dark_timber', 'white_brick', 'breccia_marble',
            'glass_block', 'sheer_fabric', 'linen_drape', 'brass', 'velvet', 'olive_leaves', 'fluted_oak')
SLUGS = {1: 'restaurant-collage-01-looking-from-within', 2: 'restaurant-collage-02-looking-towards'}
TITLES = {1: 'Restaurant - Atmosphere collage 01 - Looking from within',
          2: 'Restaurant - Atmosphere collage 02 - Looking towards'}
COMBINED_SLUG = 'restaurant-collages-01-02-side-by-side_A3'

# TEST-ONLY stand-ins (never allowed in --final): existing project images, cropped / toned
PLACEHOLDER_RENDER = {1: ('assets/gen/void_lookup_A.png', (116, 0, 3548, 4576)),
                      2: ('assets/gen/cabins_row.png', (1880, 0, 3896, 2688))}
PLACEHOLDER_SWATCH = {
    'split_face_stone': ('plaster_warm', dict(contrast=2.6, sat=0.45, gain=0.93, relief=1.0)),
    'travertine':       ('plaster_warm', dict(contrast=1.5, sat=0.85, gain=1.02, streaks=True)),
    'concrete':         ('plaster_warm', dict(contrast=1.7, sat=0.12, gain=0.86)),
    'dark_timber':      ('oak_fluted', dict(contrast=1.25, sat=0.6, gain=0.42)),
    'white_brick':      ('plaster_warm', dict(contrast=1.2, sat=0.35, gain=1.10, brick=True)),
    'breccia_marble':   ('marble', dict(contrast=1.6, sat=1.3, gain=0.92)),
    'glass_block':      ('glassblock', dict()),
    'sheer_fabric':     ('client_drape_sheer', dict(gain=1.0, bg='#A8977F')),
    'linen_drape':      ('client_drape_soft', dict(gain=1.02)),
    'brass':            ('steel_brushed', dict(tint='#9A8262', contrast=1.3, gain=0.9)),
    'velvet':           ('velvet_terracotta', dict(sat=0.75, gain=0.8)),
    'olive_leaves':     ('greenery', dict(sat=0.55, gain=0.9)),
    'fluted_oak':       ('oak_fluted', dict(sat=0.8)),
}
TEST_RENDER = {1: 'v1_g.png', 2: 'v2_f.png'}   # preview stand-ins: low-res renders of the final cameras
SWATCH_SIZE = (1600, 2000)                # (w, h) of a real swatch; placeholders are fitted to it


def rel(p):
    return os.path.relpath(p, ROOT)


def render_path(sheet):
    return os.path.join(RENDER_DIR, f'view{sheet}.png')


def swatch_path(name):
    return os.path.join(SWATCH_DIR, f'{name}.png')


class MissingInputs(RuntimeError):
    pass


def load_rgb(path, bg='#EEE8DD'):
    """Any 8/16-bit PNG/JPEG (gray, RGB, RGBA) -> float32 RGB 0..1.  An alpha channel is
    composited over the warm off-white `bg` (inputs are expected to be opaque)."""
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    a = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if a is None:
        raise IOError(f'cannot read {path}')
    scale = 65535.0 if a.dtype == np.uint16 else 255.0
    alpha = None
    if a.ndim == 2:
        a = np.repeat(a[..., None], 3, axis=2)
    elif a.shape[2] == 4:
        alpha = a[..., 3:4].astype(np.float32) / scale
        a = a[..., :3]
    rgb = cv2.cvtColor(a, cv2.COLOR_BGR2RGB).astype(np.float32) / scale
    if alpha is not None and alpha.min() < 1.0:
        b = np.array(psdkit.hex_rgb(bg), np.float32) / 255
        rgb = rgb * alpha + b * (1 - alpha)
    return rgb


def sha1_file(path, n=1 << 20):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(n), b''):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------------------------- #
# inputs (real file or test-only placeholder)
# --------------------------------------------------------------------------------------------- #

def _ph_adjust(img, contrast=1.0, sat=1.0, gain=1.0, tint=None, relief=0.0, streaks=False, brick=False):
    rgb = img.copy()
    m = rgb.mean(axis=(0, 1), keepdims=True)
    rgb = m + (rgb - m) * contrast
    if relief:
        l = rgb.mean(2)
        gx = cv2.Sobel(cv2.GaussianBlur(l, (0, 0), 3), cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(cv2.GaussianBlur(l, (0, 0), 3), cv2.CV_32F, 0, 1, ksize=3)
        rgb = rgb * (1 + relief * 2.5 * (gx + gy))[..., None]
    if streaks:
        rng = np.random.default_rng(3)
        band = gaussian_filter1d(rng.standard_normal(rgb.shape[0]), 6)
        rgb = rgb * (1 + 0.05 * band / band.std())[:, None, None]
    l = rgb.mean(2, keepdims=True)
    rgb = l + (rgb - l) * sat
    if tint is not None:
        t = np.array(psdkit.hex_rgb(tint), np.float32) / 255
        rgb = rgb.mean(2, keepdims=True) * t / t.mean() * 1.05
    rgb = rgb * gain
    if brick:                                  # quick stand-in brick bond (mortar joints)
        h, w = rgb.shape[:2]
        course, length, joint = 150, 330, 13
        yy, xx = np.mgrid[0:h, 0:w]
        row = yy // course
        xo = (xx + (row % 2) * length // 2) % length
        jm = ((yy % course) < joint) | (xo < joint)
        jm = cv2.GaussianBlur(jm.astype(np.float32), (0, 0), 1.6)
        rgb = rgb * (1 - 0.22 * jm[..., None])
    return np.clip(rgb, 0, 1).astype(np.float32)


class Sources:
    """Loads the sheet's render and swatches.  Real files under build/v2 win; otherwise (preview
    only) a test placeholder is used and recorded.  final=True raises MissingInputs instead."""

    def __init__(self, sheet, final=False):
        self.sheet, self.final = sheet, final
        self.used = {}
        self._sw = {}
        self._render = None

    def render(self):
        if self._render is None:
            p = render_path(self.sheet)
            if os.path.exists(p):
                self._render = load_rgb(p)
                self.used['render'] = {'path': rel(p), 'placeholder': False}
            else:
                if self.final:
                    raise MissingInputs([rel(p)])
                test = os.path.join(ROOT, 'build', 'v2', 'test', TEST_RENDER[self.sheet])
                if os.path.exists(test):            # low-res test render of the same camera
                    img = load_rgb(test)
                    self._render = cv2.resize(img, (2700, 3600), interpolation=cv2.INTER_CUBIC)
                    self.used['render'] = {'path': rel(test), 'placeholder': True}
                    return self._render
                src, (x0, y0, x1, y1) = PLACEHOLDER_RENDER[self.sheet]
                img = load_rgb(src)[y0:y1, x0:x1]
                s = min(1.0, 2700 / img.shape[1], 3600 / img.shape[0])
                self._render = C.resize(img, s) if s < 1 else img
                self.used['render'] = {'path': src, 'placeholder': True}
        return self._render

    def swatch(self, name):
        if name not in self._sw:
            p = swatch_path(name)
            if os.path.exists(p):
                self._sw[name] = load_rgb(p)
                self.used[name] = {'path': rel(p), 'placeholder': False}
            else:
                if self.final:
                    raise MissingInputs([rel(p)])
                if name not in PLACEHOLDER_SWATCH:
                    raise KeyError(f'unknown swatch {name!r}; known: {", ".join(SWATCHES)}')
                test = os.path.join(ROOT, 'build', 'v2', 'test', 'swatch', f'{name}.png')
                if os.path.exists(test):            # low-res test render of the same swatch
                    self._sw[name] = cv2.resize(load_rgb(test), SWATCH_SIZE, interpolation=cv2.INTER_CUBIC)
                    self.used[name] = {'path': rel(test), 'placeholder': True}
                    return self._sw[name]
                mat, adj = PLACEHOLDER_SWATCH[name]
                adj = dict(adj)
                img = load_rgb(os.path.join('assets', 'mat', mat + '.png'), bg=adj.pop('bg', '#EEE8DD'))
                img = C.cover(img, *SWATCH_SIZE)
                self._sw[name] = _ph_adjust(img, **adj)
                self.used[name] = {'path': f'assets/mat/{mat}.png', 'placeholder': True}
        return self._sw[name]

    @property
    def placeholders(self):
        return sorted(k for k, v in self.used.items() if v['placeholder'])


def sheet_inputs(sheet):
    """Every real input file the sheet needs (render + swatches its layout references)."""
    lay = LAYOUT.SHEETS[sheet]
    names = sorted({_frag(f)['swatch'] for f in lay.get('fragments', [])})
    return [render_path(sheet)] + [swatch_path(n) for n in names]


def missing_inputs(sheet):
    return [rel(p) for p in sheet_inputs(sheet) if not os.path.exists(p)]


# --------------------------------------------------------------------------------------------- #
# layout normalisation (tuples or dicts)
# --------------------------------------------------------------------------------------------- #

def _frag(f):
    if isinstance(f, dict):
        d = dict(f)
    else:
        keys = ('swatch', 'crop', 'target', 'rot', 'edge', 'z', 'seed')
        d = dict(zip(keys, f[:7]))
        if len(f) > 7 and f[7]:
            d.update(f[7])
    d.setdefault('rot', 0.0)
    d.setdefault('edge', 'torn')
    d.setdefault('z', 'front')
    d.setdefault('seed', 0)
    if d['z'] not in ('front', 'behind'):
        raise ValueError(f"fragment z must be 'front' or 'behind', got {d['z']!r}")
    return d


def _echo(e):
    if isinstance(e, dict):
        d = dict(e)
    else:
        keys = ('src', 'scale', 'offset', 'rot', 'edge', 'seed')
        d = dict(zip(keys, e[:6]))
        if len(e) > 6 and e[6]:
            d.update(e[6])
    d.setdefault('scale', 1.08)
    d.setdefault('offset', (0, 0))
    d.setdefault('rot', 0.0)
    d.setdefault('edge', 'torn')
    d.setdefault('seed', 0)
    return d


def _note(n):
    if isinstance(n, dict):
        d = dict(n)
    else:
        keys = ('text', 'at', 'rot', 'to', 'bend')
        d = dict(zip(keys, n[:5]))
        if len(n) > 5 and n[5]:
            d.update(n[5])
    d.setdefault('rot', 0.0)
    d.setdefault('to', None)
    d.setdefault('bend', 0.25)
    d.setdefault('style', 'note')
    return d


def _edges(spec):
    """'torn' | 'cut' | e.g. 'LB'  ->  torn flags for the quad edges (T, R, B, L)."""
    if spec in (True, 'torn', 'all'):
        return [True] * 4
    if spec in (False, None, 'cut', ''):
        return [False] * 4
    s = str(spec).upper()
    bad = set(s) - set('TRBL')
    if bad:
        raise ValueError(f'edge spec {spec!r}: use torn, cut or a combination of T R B L')
    return ['T' in s, 'R' in s, 'B' in s, 'L' in s]


def rect_quad(x, y, w, h, rot=0.0):
    """Page rectangle rotated about its centre by rot degrees counter-clockwise -> (tl, tr, br, bl)."""
    cx, cy = x + w / 2.0, y + h / 2.0
    pts = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], np.float64) - (cx, cy)
    t = math.radians(rot)
    c, s = math.cos(t), math.sin(t)
    R = np.array([[c, s], [-s, c]])          # visual CCW in y-down coordinates
    return pts @ R.T + (cx, cy)


def target_quad(target, rot):
    t = np.asarray(target, np.float64)
    if t.shape == (4, 2):
        return t
    if t.shape == (4,):
        return rect_quad(*t, rot=rot)
    raise ValueError(f'target must be (x, y, w, h) or 4 (x, y) points, got {target!r}')


def _quad_size(q):
    w = (np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / 2
    h = (np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1])) / 2
    return w, h


def fit_crop(crop, img_w, img_h, aspect):
    """Normalised crop box -> pixel box widened / heightened about its centre to `aspect` (w/h),
    kept inside the image.  crop=None: centred box at about 1:1 scale chosen by the caller."""
    u0, v0, u1, v1 = crop
    x0, y0, x1, y1 = u0 * img_w, v0 * img_h, u1 * img_w, v1 * img_h
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = max(8.0, x1 - x0), max(8.0, y1 - y0)
    if w / h < aspect:
        w = h * aspect
    else:
        h = w / aspect
    s = min(1.0, img_w / w, img_h / h)        # never larger than the image
    w, h = w * s, h * s
    cx = min(max(cx, w / 2), img_w - w / 2)
    cy = min(max(cy, h / 2), img_h - h / 2)
    return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2


# --------------------------------------------------------------------------------------------- #
# raster helpers
# --------------------------------------------------------------------------------------------- #

def page_box(x0, y0, x1, y1):
    return (max(0, int(math.floor(x0))), max(0, int(math.floor(y0))),
            min(PW, int(math.ceil(x1))), min(PH, int(math.ceil(y1))))


def page_pixel(name, img, x, y, **kw):
    """psdkit Pixel layer from float RGB(A), cropped to the portrait page."""
    if img.shape[2] == 3:
        img = C.rgba(img)
    x, y = int(x), int(y)
    h, w = img.shape[:2]
    cx0, cy0 = max(0, -x), max(0, -y)
    cx1, cy1 = min(w, PW - x), min(h, PH - y)
    if cx1 <= cx0 or cy1 <= cy0:
        raise ValueError(f'layer {name!r} is entirely off the page')
    return Pixel(name, img[cy0:cy1, cx0:cx1], x + cx0, y + cy0, **kw)


def page_mask(alpha, x, y):
    """psdkit Mask from a local float alpha at page (x, y), cropped to the page and its content."""
    h, w = alpha.shape
    cx0, cy0 = max(0, -x), max(0, -y)
    cx1, cy1 = min(w, PW - x), min(h, PH - y)
    return C.mask_for(alpha[cy0:cy1, cx0:cx1], x + cx0, y + cy0)


def colour_layer(alpha, color):
    out = np.empty(alpha.shape + (4,), np.float32)
    out[..., :3] = np.array(psdkit.hex_rgb(color), np.float32) / 255
    out[..., 3] = alpha
    return out


def fast_blur(a, sigma):
    """Gaussian blur; large sigmas run on a 4x reduced copy (same look, a fraction of the time)."""
    if sigma <= 0:
        return a
    if sigma < 10:
        return cv2.GaussianBlur(a, (0, 0), sigma)
    f = 4
    h, w = a.shape[:2]
    small = cv2.resize(a, (max(1, w // f), max(1, h // f)), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), sigma / f)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def _n1(n, sigma, rng):
    """1-D smooth noise of feature size ~sigma, unit std."""
    pad = int(4 * sigma) + 4
    v = gaussian_filter1d(rng.standard_normal(n + 2 * pad), sigma)[pad:pad + n]
    return v / (v.std() + 1e-9)


def _n2(h, w, sigma, rng):
    n = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), sigma)
    return n / (n.std() + 1e-8)


def paste_max(acc, alpha, x, y):
    """acc[y:, x:] = max(acc, alpha) for a local alpha at page (x, y)."""
    h, w = alpha.shape
    X0, Y0, X1, Y1 = max(0, x), max(0, y), min(acc.shape[1], x + w), min(acc.shape[0], y + h)
    if X1 > X0 and Y1 > Y0:
        sub = acc[Y0:Y1, X0:X1]
        np.maximum(sub, alpha[Y0 - y:Y1 - y, X0 - x:X1 - x], out=sub)


# --------------------------------------------------------------------------------------------- #
# torn / cut shapes
# --------------------------------------------------------------------------------------------- #

def shape_fields(polys, box, seed, tear=1.0, rim=True, fibres=1.0, px_pad=40):
    """Alpha fields of a union of convex polygons with per-edge torn / cut sides.

    polys  [(pts (N, 2) page px, [torn flag per edge]), ...]; edge i runs pts[i] -> pts[i+1]
    box    (x0, y0, x1, y1) page window to evaluate
    A torn edge is the straight edge displaced along its normal by 1-D fractal noise of the
    position along it (TEAR octaves: long drift, mid jaggies, fine serration), plus a little 2-D
    roughness; anti-aliased by the exact gradient of the displaced distance.  With rim=True a
    paper-core band of 2-6 px (RIM_W, smoothly varying) lies inside the torn line, with sparse
    hair-like fibres poking out beyond it.  Cut edges stay mathematically straight.
    Returns dict (all (h, w) float32 in the box):
      inner  layer mask of the photo (inside the rim)
      outer  full silhouette incl. rim + fibres (casts the shadow)
      rim    alpha of the paper-core rim layer;  frac  0 outer -> 1 inner across the rim
      pixel  coverage for the photo pixels (shape grown by px_pad, so the mask can be painted out)"""
    x0, y0, x1, y1 = box
    h, w = y1 - y0, x1 - x0
    xs = (np.arange(x0, x1, dtype=np.float32) + 0.5)[None, :]
    ys = (np.arange(y0, y1, dtype=np.float32) + 0.5)[:, None]
    rng = np.random.default_rng(seed)
    rough = None
    D_out = D_in = D_cut = None
    fib = np.zeros((h, w), np.float32)
    for pts, torn in polys:
        P = np.asarray(pts, np.float64)
        n = len(P)
        area = 0.5 * sum(P[i, 0] * P[(i + 1) % n, 1] - P[(i + 1) % n, 0] * P[i, 1] for i in range(n))
        sgn = 1.0 if area > 0 else -1.0
        e_out, e_in, e_cut, info = [], [], [], []
        for i in range(n):
            a, b = P[i], P[(i + 1) % n]
            L = float(np.linalg.norm(b - a))
            tx, ty = (b - a) / L
            nx, ny = ty * sgn, -tx * sgn           # outward normal
            d = ((xs - a[0]) * nx + (ys - a[1]) * ny).astype(np.float32)
            e_cut.append(d)
            if torn[i] and tear > 0:
                s = ((xs - a[0]) * tx + (ys - a[1]) * ty).astype(np.float32)
                pad_s = 600.0
                m = int(L + 2 * pad_s) + 2
                disp = sum(amp * tear * _n1(m, sig, rng) for sig, amp in TEAR)
                slope = np.gradient(disp)
                idx = np.arange(m, dtype=np.float32) - pad_s
                dsp = np.interp(s, idx, disp).astype(np.float32)
                slp = np.interp(s, idx, slope).astype(np.float32)
                if rough is None:
                    rough = 0.45 * tear * _n2(h, w, 0.9, rng)
                Di = (d + dsp) / np.sqrt(1.0 + slp * slp) + rough
                if rim:
                    rw = RIM_W[0] + (RIM_W[1] - RIM_W[0]) * np.clip(0.5 + 0.38 * _n1(m, 34, rng)
                                                                      + 0.12 * _n1(m, 5, rng), 0, 1)
                    Dii = Di + np.interp(s, idx, rw).astype(np.float32)
                    spikes = fibres * 7.5 * np.clip(_n1(m, 0.9, rng) - 1.75, 0, None)
                    info.append((len(e_out), np.interp(s, idx, spikes).astype(np.float32)))
                else:
                    Dii = Di
                e_out.append(Di)
                e_in.append(Dii)
            else:
                e_out.append(d)
                e_in.append(d)
        Dk = functools.reduce(np.maximum, e_out)
        Dik = functools.reduce(np.maximum, e_in)
        Dck = functools.reduce(np.maximum, e_cut)
        for i, flen in info:
            others = functools.reduce(np.maximum, [e for j, e in enumerate(e_out) if j != i])
            c = np.clip(flen - e_out[i] + 0.5, 0, 1) * np.clip(flen, 0, 1) * (others < -1.0)
            np.maximum(fib, c, out=fib)
        D_out = Dk if D_out is None else np.minimum(D_out, Dk)
        D_in = Dik if D_in is None else np.minimum(D_in, Dik)
        D_cut = Dck if D_cut is None else np.minimum(D_cut, Dck)
    inner = np.clip(0.5 - D_in, 0, 1)
    outer = np.clip(0.5 - D_out, 0, 1)
    fib *= np.clip(D_out + 0.5, 0, 1)                 # fibres only beyond the torn line
    rim_a = np.clip(outer - inner, 0, 1)
    np.maximum(rim_a, 0.8 * fib, out=rim_a)
    frac = np.clip(-D_out / np.maximum(D_in - D_out, 0.5), 0, 1)
    pixel = np.clip(0.5 - (D_cut - px_pad), 0, 1)
    return {'inner': inner.astype(np.float32), 'outer': np.maximum(outer, 0.8 * fib).astype(np.float32),
            'rim': rim_a.astype(np.float32), 'frac': frac.astype(np.float32), 'pixel': pixel.astype(np.float32)}


def rim_rgba(F, seed):
    """Paper-core rim layer: warm off-white, a touch greyer where it meets the photo."""
    rng = np.random.default_rng(seed + 7)
    h, w = F['rim'].shape
    tone = 1.0 - 0.075 * F['frac'] ** 1.5 + 0.012 * _n2(h, w, 1.2, rng)
    rgb = np.array(psdkit.hex_rgb(RIM), np.float32) / 255
    out = np.empty((h, w, 4), np.float32)
    out[..., :3] = np.clip(rgb[None, None, :] * tone[..., None], 0, 1)
    out[..., 3] = F['rim'] * 0.97
    return out


def shadow_rgba(alpha, dx, dy, blur, contact=0.4):
    """Soft drop shadow of a local alpha: a wide soft shadow + a tight contact shadow (paper lift).
    Returns (rgba, ox, oy): place at (x + ox, y + oy) for an alpha placed at (x, y)."""
    pad = int(math.ceil(3 * blur)) + int(max(abs(dx), abs(dy))) + 4
    P = np.pad(alpha.astype(np.float32), pad)
    H_, W_ = P.shape

    def shifted(ddx, ddy):
        M = np.float32([[1, 0, ddx], [0, 1, ddy]])
        return cv2.warpAffine(P, M, (W_, H_), flags=cv2.INTER_LINEAR)
    big = fast_blur(shifted(dx, dy), blur)
    small = cv2.GaussianBlur(shifted(dx * 0.25, dy * 0.25), (0, 0), max(1.2, blur * 0.12))
    a = np.clip(0.82 * big + contact * small, 0, 1)
    return colour_layer(a, SHADOW), -pad, -pad


def warp_into(img, crop_px, quad, box):
    """Perspective-map the pixel box crop_px of img onto quad (page px), rendered over the page
    window `box`; areas beyond the crop show the rest of the image (reflected at its borders).
    Downscaling is pre-filtered (INTER_AREA) so fine textures never alias."""
    x0, y0, x1, y1 = box
    cx0, cy0, cx1, cy1 = crop_px
    q = np.asarray(quad, np.float64)
    qw, qh = _quad_size(q)
    s = math.sqrt((qw * qh) / max(1.0, (cx1 - cx0) * (cy1 - cy0)))
    if s < 0.85:
        img = C.resize(img, s)
        cx0, cy0, cx1, cy1 = cx0 * s, cy0 * s, cx1 * s, cy1 * s
    src = np.float32([[cx0, cy0], [cx1, cy0], [cx1, cy1], [cx0, cy1]])
    dst = (q - (x0, y0)).astype(np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    out = cv2.warpPerspective(img, M, (x1 - x0, y1 - y0), flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REFLECT_101)
    return np.clip(out, 0, 1)


# --------------------------------------------------------------------------------------------- #
# hand-drawn arrows
# --------------------------------------------------------------------------------------------- #

def _bezier(p0, p1, p2, p3, n):
    t = np.linspace(0, 1, n)[:, None]
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


def arrow_rgba(p0, p3, bend=0.25, seed=0, width=ARROW['width'], head=ARROW['head'], c1=None, c2=None,
               color=INK, opacity=ARROW['opacity'], ss=3, halo=ARROW['halo']):
    """Thin, slightly wobbly cubic curve p0 -> p3 with an open 'V' arrowhead at p3.
    The stroke tapers in from the pen-down point; drawn at ss x and box-downsampled (anti-aliased).
    Returns (rgba, (x, y))."""
    rng = np.random.default_rng(seed)
    p0, p3 = np.asarray(p0, np.float64), np.asarray(p3, np.float64)
    v = p3 - p0
    L = float(np.linalg.norm(v))
    nrm = np.array([-v[1], v[0]]) / max(L, 1e-6)
    c1 = p0 + v * 0.28 + nrm * bend * L if c1 is None else np.asarray(c1, np.float64)
    c2 = p0 + v * 0.70 + nrm * bend * L * 0.8 if c2 is None else np.asarray(c2, np.float64)
    n = max(48, int(L / 2.5))
    P = _bezier(p0, c1, c2, p3, n)
    tg = np.gradient(P, axis=0)
    tg /= np.maximum(np.linalg.norm(tg, axis=1, keepdims=True), 1e-9)
    nn = np.stack([-tg[:, 1], tg[:, 0]], 1)
    t = np.linspace(0, 1, n)
    wob = (0.9 * _n1(n, n / 7.0, rng) + 0.35 * _n1(n, max(2.0, n / 40.0), rng)) * np.sin(np.pi * t) ** 0.6
    P = P + nn * wob[:, None] * min(1.6, L / 160)
    wv = width * (0.42 + 0.58 * smoothstep(0.0, 0.2, t)) * (1.0 - 0.12 * t)
    strokes = [(P, wv)]
    # open V head: two short strokes from the tip, back along the final tangent
    u = P[-1] - P[-min(len(P) - 1, max(3, int(n * 0.06)))]
    u /= max(np.linalg.norm(u), 1e-9)
    tip = P[-1]
    for k, sgn in enumerate((1, -1)):
        ang = math.radians(27 + rng.uniform(-3, 4)) * sgn
        ca, sa = math.cos(ang), math.sin(ang)
        d = -np.array([u[0] * ca - u[1] * sa, u[0] * sa + u[1] * ca])
        ln = head * (1.0 + rng.uniform(-0.12, 0.08) - 0.06 * k)
        s_ = np.linspace(0, 1, 18)[:, None]
        side = np.array([-d[1], d[0]]) * sgn
        barb = tip + d * ln * s_ + side * (0.07 * ln) * (s_ ** 2)     # a hint of curl
        strokes.append((barb, width * np.linspace(0.92, 0.62, len(barb))))
    allp = np.concatenate([s_[0] for s_ in strokes])
    m = width + 4 + 2 * halo
    bx0, by0 = int(math.floor(allp[:, 0].min() - m)), int(math.floor(allp[:, 1].min() - m))
    bx1, by1 = int(math.ceil(allp[:, 0].max() + m)), int(math.ceil(allp[:, 1].max() + m))
    cov = np.zeros(((by1 - by0) * ss, (bx1 - bx0) * ss), np.float32)
    for pts, wv_ in strokes:
        c, _ = T.stroke_polyline((pts - (bx0, by0)) * ss, np.asarray(wv_) * ss,
                                 box=(0, 0, cov.shape[1], cov.shape[0]))
        np.maximum(cov, c, out=cov)
    cov = cv2.resize(cov, (bx1 - bx0, by1 - by0), interpolation=cv2.INTER_AREA)
    ink = np.clip(cov, 0, 1) * opacity
    if halo:
        # soft cream under-stroke so the hairline still reads where it crosses dark parts of the view
        hal = cv2.dilate(np.clip(cov, 0, 1), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(2 * halo) | 1,) * 2))
        hal = cv2.GaussianBlur(hal, (0, 0), halo * 0.5) * ARROW['halo_opacity']
        a = ink + hal * (1 - ink)
        ci = np.array(psdkit.hex_rgb(color), np.float32) / 255
        ch = np.array(psdkit.hex_rgb(RIM), np.float32) / 255
        rgb = (ink[..., None] * ci + (hal * (1 - ink))[..., None] * ch) / np.maximum(a, 1e-6)[..., None]
        return np.dstack([rgb, a]).astype(np.float32), (bx0, by0)
    return colour_layer(ink, color), (bx0, by0)


# --------------------------------------------------------------------------------------------- #
# builder
# --------------------------------------------------------------------------------------------- #

def dedupe_names(doc):
    """Make every layer / group name unique (Photoshop allows twins, but the export check does not)."""
    seen = {}
    for n in doc.root.iter_layers():
        key = psdkit.ascii_name(n.name)
        k = seen.get(key, 0)
        seen[key] = k + 1
        if k:
            n.name = f'{n.name} ({k + 1})'


class SheetBuilder(Builder):
    """collage_common.Builder on an A3 portrait page (its text() / live-twin mechanism reused)."""

    def __init__(self, title):                      # noqa: super().__init__ makes a landscape doc
        self.doc = Document(PW, PH, DPI, title)

    def px(self, g, name, img, x, y, **kw):
        layer = page_pixel(name, img, int(round(x)), int(round(y)), **kw)
        g.add(layer)
        return layer

    def _live(self, g, name, text, font, size, x, y, color, tracking=0, leading=None, justification='left',
              angle=0.0):
        g.add(Text(name, text, PS_V2.get(font, font), size, x, y, color=color, tracking=tracking,
                   leading=leading, justification=justification, angle=angle))


class Composer:
    def __init__(self, sheet, final=False, log=print):
        self.sheet = sheet
        self.lay = LAYOUT.SHEETS[sheet]
        self.src = Sources(sheet, final=final)
        self.B = SheetBuilder(TITLES[sheet])
        self.log = log
        self.acc = {k: np.zeros((PH, PW), np.float32) for k in ('view', 'front', 'behind', 'echo')}
        self.view_map = None

    # ------------------------------------------------------------------ pieces
    def piece(self, g, label, img, crop_px, quad, edges, seed, rim=True, tear=1.0, shadow=SHADOW_DEFAULT,
              tone=None, acc=None, extra_polys=None):
        """One fragment group: shadow, photo (full crop + tear mask), optional clipped tone, rim."""
        polys = [(quad, edges)] + list(extra_polys or [])
        allp = np.concatenate([np.asarray(p, np.float64) for p, _ in polys])
        pad = int(math.ceil(sum(a for _, a in TEAR) * max(tear, 0.3))) + 48
        box = page_box(*(allp.min(0) - pad), *(allp.max(0) + pad))
        x0, y0, x1, y1 = box
        if x1 - x0 < 4 or y1 - y0 < 4:
            raise ValueError(f'{label}: entirely off the page')
        F = shape_fields(polys, box, seed, tear=tear, rim=rim and any(any(e) for _, e in polys))
        rgb = warp_into(img, crop_px, quad, box)
        sg = Group(label, opened=False)
        g.add(sg)
        if shadow:
            dx, dy, blur, op = shadow
            srgba, ox, oy = shadow_rgba(F['outer'], dx, dy, blur)
            self.B.px(sg, f'Shadow - {label}', srgba, x0 + ox, y0 + oy, blend='multiply', opacity=op)
        rgba = np.dstack([rgb, F['pixel']])
        self.B.px(sg, f'Image - {label}', rgba, x0, y0, mask=page_mask(F['inner'], x0, y0))
        if tone:
            sg.add(Fill(f'Tone - {label}', tone.get('color', '#B98B5E'), clip=True,
                        blend=tone.get('blend', 'soft light'), opacity=tone.get('opacity', 0.2)))
        if F['rim'].max() > 0.02:
            self.B.px(sg, f'Rim - {label}', rim_rgba(F, seed), x0, y0)
        if acc is not None:
            paste_max(self.acc[acc], F['outer'], x0, y0)
        return F, box

    # ------------------------------------------------------------------ paper
    def paper(self):
        B = self.B
        g = B.group('00 - Paper', label='gray')
        tex = load_rgb(os.path.join('assets', 'mat', 'paper_linen_A3.png'))       # landscape 4961 x 3508
        tex = np.ascontiguousarray(np.rot90(tex, -1))                              # -> portrait
        lum = tex @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        del tex
        ref = float(np.percentile(lum, 99.6))
        ratio = 1.0 - 0.85 * (1.0 - np.clip(lum / ref, 0, 1))                     # fibre + mottle, darken only
        mean = float(ratio.mean())
        base = np.array(psdkit.hex_rgb(CREAM), np.float32) / mean
        base_hex = '#%02X%02X%02X' % tuple(int(round(min(255, v))) for v in base)
        g.add(Fill(f'Paper - cream {base_hex} (double-click to recolour)', base_hex, locked=True))
        grey = np.repeat(ratio[..., None], 3, axis=2)
        del lum, ratio
        B.px(g, 'Paper - fibre and mottle', grey, 0, 0, blend='multiply', locked=True)
        del grey
        yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
        r = np.sqrt(((xx - PW / 2) / (PW * 0.58)) ** 2 + ((yy - PH * 0.48) / (PH * 0.58)) ** 2)
        vig = smoothstep(0.55, 1.35, r) ** 1.4
        del xx, yy, r
        g.add(Fill('Paper - vignette', '#9C8668', mask=C.canvas_mask('v', vig), blend='multiply', opacity=0.07,
                   locked=True))
        return g

    # ------------------------------------------------------------------ main view
    def view(self):
        v = self.lay['view']
        img = self.src.render()
        rh, rw = img.shape[:2]
        rects = v['outline']
        ob = np.array([r[:4] for r in rects], np.float64)
        frame = v.get('frame') or (ob[:, 0].min(), ob[:, 1].min(), ob[:, 2].max(), ob[:, 3].max())
        fx0, fy0, fx1, fy1 = frame
        fw, fh = fx1 - fx0, fy1 - fy0
        s = max(fw / rw, fh / rh) * v.get('zoom', 1.0)
        foc = v.get('focus', (0.5, 0.5))
        ox = fx0 - (rw * s - fw) * foc[0]
        oy = fy0 - (rh * s - fh) * foc[1]
        self.view_map = (s, ox, oy)
        # the visible image is the union of the outline rectangles, each with its own torn sides
        polys = [(rect_quad(x0, y0, x1 - x0, y1 - y0), _edges(sides)) for x0, y0, x1, y1, sides in rects]
        tag = ' PLACEHOLDER' if self.src.used['render']['placeholder'] else ''
        g = self.B.group('20 - Main view', label='blue')
        sg = Group(f'Main view{tag}', opened=True)
        g.add(sg)
        allp = np.concatenate([p for p, _ in polys])
        pad = int(math.ceil(sum(a for _, a in TEAR) * v.get('tear', 1.0))) + 48
        box = page_box(*(allp.min(0) - pad), *(allp.max(0) + pad))
        x0, y0, x1, y1 = box
        seed = v.get('seed', 1)
        F = shape_fields(polys, box, seed, tear=v.get('tear', 1.0), rim=v.get('rim', True))
        rgb = warp_into(img, (0, 0, rw, rh), rect_quad(ox, oy, rw * s, rh * s), box)
        dx, dy, blur, op = v.get('shadow', (12, 16, 30, 0.30))
        srgba, sx, sy = shadow_rgba(F['outer'], dx, dy, blur)
        self.B.px(sg, 'Shadow - main view', srgba, x0 + sx, y0 + sy, blend='multiply', opacity=op)
        self.B.px(sg, f'Main view - render{tag}', np.dstack([rgb, F['pixel']]), x0, y0,
                  mask=page_mask(F['inner'], x0, y0))
        if v.get('tone'):
            tn = v['tone']
            sg.add(Fill('Tone - main view', tn.get('color', '#B98B5E'), clip=True,
                        blend=tn.get('blend', 'soft light'), opacity=tn.get('opacity', 0.2)))
        if F['rim'].max() > 0.02:
            self.B.px(sg, 'Rim - main view torn edge', rim_rgba(F, seed), x0, y0)
        paste_max(self.acc['view'], F['inner'], x0, y0)
        return g

    def page_to_render(self, x, y):
        s, ox, oy = self.view_map
        return (x - ox) / s, (y - oy) / s

    # ------------------------------------------------------------------ fragments + echoes
    def fragments(self, z):
        items = [(i, _frag(f)) for i, f in enumerate(self.lay.get('fragments', []))]
        items = [(i, f) for i, f in items if f['z'] == z]
        name = '10 - Fragments behind' if z == 'behind' else '40 - Fragments in front'
        g = self.B.group(name, label='orange')
        for i, f in items:
            img = self.src.swatch(f['swatch'])
            ih, iw = img.shape[:2]
            quad = target_quad(f['target'], f['rot'])
            qw, qh = _quad_size(quad)
            crop = f.get('crop')
            if crop is None:
                crop = (0.5 - qw / iw / 2, 0.5 - qh / ih / 2, 0.5 + qw / iw / 2, 0.5 + qh / ih / 2)
            crop_px = fit_crop(crop, iw, ih, qw / qh)
            edges = _edges(f['edge'])
            kind = 'torn' if all(edges) else ('cut' if not any(edges) else 'torn ' + ''.join(
                c for c, e in zip('TRBL', edges) if e))
            ph = ' PLACEHOLDER' if self.src.used[f['swatch']]['placeholder'] else ''
            label = f.get('name') or f"Frag {i + 1:02d} - {f['swatch'].replace('_', ' ')} ({kind}){ph}"
            shadow = f.get('shadow', SHADOW_BEHIND if z == 'behind' else SHADOW_DEFAULT)
            self.piece(g, label, img, crop_px, quad, edges, f['seed'], rim=f.get('rim', False),
                       tear=f.get('tear', 0.5), shadow=shadow, tone=f.get('tone'), acc=z)
        return g

    def echoes(self):
        items = [_echo(e) for e in self.lay.get('echoes', [])]
        g = self.B.group('30 - Echo patches (cut from the view)', label='blue')
        img = self.src.render()
        tag = ' PLACEHOLDER' if self.src.used['render']['placeholder'] else ''
        for i, e in enumerate(items):
            x0, y0, x1, y1 = e['src']
            r0 = self.page_to_render(x0, y0)
            r1 = self.page_to_render(x1, y1)
            sc = e['scale']
            w, h = (x1 - x0) * sc, (y1 - y0) * sc
            cx, cy = (x0 + x1) / 2 + e['offset'][0], (y0 + y1) / 2 + e['offset'][1]
            quad = rect_quad(cx - w / 2, cy - h / 2, w, h, e['rot'])
            label = e.get('name') or f'Echo {i + 1:02d} - view patch x{sc:.2f}{tag}'
            self.piece(g, label, img, (*r0, *r1), quad, _edges(e['edge']), e['seed'], rim=e.get('rim', True),
                       tear=e.get('tear', 1.0), shadow=e.get('shadow', SHADOW_DEFAULT), acc='echo')
        return g

    # ------------------------------------------------------------------ intensity
    def grain(self):
        """Print grain over everything that is 'photo' (view, fragments, echoes), so the render and
        the swatches read as prints on one stock, not pristine pixels."""
        content = functools.reduce(np.maximum, [self.acc[k] for k in ('view', 'front', 'behind', 'echo')])
        ys, xs = np.nonzero(content > 0.01)
        if not len(ys):
            return
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        rng = np.random.default_rng(100 + self.sheet)
        n = rng.standard_normal((y1 - y0, x1 - x0)).astype(np.float32)
        n = cv2.GaussianBlur(n, (0, 0), 0.7)
        n = 0.5 + n / (n.std() + 1e-6) * (10 / 255)
        g = self.B.group('45 - Print grain', label='gray')
        self.B.px(g, 'Print grain (soft light)', np.dstack([n, n, n, content[y0:y1, x0:x1]]), int(x0), int(y0),
                  blend='soft light', opacity=0.5)
        return g

    def intensity(self):
        spec = self.lay.get('intensity') or {}
        g = self.B.group('50 - Overlap intensity (colour where spaces overlap)', label='yellow')
        ov = spec.get('overlap')
        if ov:
            top = np.maximum(self.acc['front'], self.acc['echo'])
            over = top * self.acc['view']
            if ov.get('feather', 0):           # soft gradient across the view edge, kept inside the fragments
                over = np.clip(fast_blur(over, ov['feather']), 0, 1) * top
            del top
            g.add(Fill('Intensity - fragments over the view', ov.get('color', INTENSITY_COLOR),
                       mask=C.canvas_mask('o', over), blend=ov.get('blend', 'soft light'),
                       opacity=ov.get('opacity', 0.35)))
            del over
        content = functools.reduce(np.maximum, [self.acc[k] for k in ('view', 'front', 'behind', 'echo')])
        for k, glow in enumerate(spec.get('glows', [])):
            (cx, cy), R, color, blend, op = glow
            bx = page_box(cx - 2 * R, cy - 2 * R, cx + 2 * R, cy + 2 * R)
            yy, xx = np.mgrid[bx[1]:bx[3], bx[0]:bx[2]].astype(np.float32)
            m = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (R * R)) * 2.0)
            m *= content[bx[1]:bx[3], bx[0]:bx[2]]
            g.add(Fill(f'Intensity - chosen area glow {k + 1}', color, mask=C.mask_for(m, bx[0], bx[1]),
                       blend=blend, opacity=op))
        return g

    # ------------------------------------------------------------------ type
    def notes(self):
        g = self.B.group('60 - Notes (handwritten)', label='red')
        for i, n in enumerate(self.lay.get('notes', [])):
            n = _note(n)
            st = dict(NOTE_STYLE[n['style']])
            for k in ('size', 'color', 'tracking', 'leading', 'opacity'):
                if k in n:
                    st[k] = n[k]
            short = n['text'].replace('\n', ' ')
            pre = 'Sense' if n['style'] == 'sense' else 'Note'
            sg = Group(f'{pre} - {short}', opened=False)
            g.add(sg)
            x, y = n['at']
            meta, (px, py) = self.B.text(sg, n['text'], HAND, st['size'], x, y, anchor='baseline_left',
                                         color=st['color'], name=f'TXT - {short}', opacity=st['opacity'],
                                         tracking=st['tracking'], leading=st['leading'], angle=n['rot'],
                                         align=n.get('align', 'left'))
            if n['to'] is None:
                continue
            ib = meta['ink_box']
            bx0, by0, bx1, by1 = ib[0] + px, ib[1] + py, ib[2] + px, ib[3] + py
            gap = n.get('gap', ARROW['gap'])
            tx, ty = n['to']
            fr = n.get('from', 'auto')
            cxm, cym = (bx0 + bx1) / 2, (by0 + by1) / 2
            if fr == 'auto':
                dx_, dy_ = tx - cxm, ty - cym
                fr = (('right' if dx_ > 0 else 'left') if abs(dx_) / max(1, bx1 - bx0) > abs(dy_) / max(1, by1 - by0)
                      else ('below' if dy_ > 0 else 'above'))
            anchors = {
                'below': (cxm, by1 + gap), 'above': (cxm, by0 - gap),
                'left': (bx0 - gap, cym), 'right': (bx1 + gap, cym),
                'below_left': (bx0 + 0.25 * (bx1 - bx0), by1 + gap), 'below_right': (bx1 - 0.25 * (bx1 - bx0), by1 + gap),
                'above_left': (bx0 + 0.25 * (bx1 - bx0), by0 - gap), 'above_right': (bx1 - 0.25 * (bx1 - bx0), by0 - gap),
            }
            if isinstance(fr, str) and fr == 'end':
                lb = meta['anchors']['last_baseline_left']
                lw = meta['line_widths'][-1]
                p0 = (px + lb[0] + lw + gap, py + lb[1] - meta['x_height'] * 0.5)
            elif isinstance(fr, str):
                p0 = anchors[fr]
            else:
                p0 = tuple(fr)
            if 'from_offset' in n:
                p0 = (p0[0] + n['from_offset'][0], p0[1] + n['from_offset'][1])
            rgba, (ax, ay) = arrow_rgba(p0, (tx, ty), bend=n['bend'], seed=1000 + 17 * i + self.sheet,
                                        head=n.get('head', ARROW['head']), c1=n.get('c1'), c2=n.get('c2'),
                                        color=st['color'])
            self.B.px(sg, f'Arrow - {short}', rgba, ax, ay)
        return g

    def title(self):
        B = self.B
        g = B.group('90 - Title and key line')
        t = self.lay['title']
        tsize, ttrk = t.get('size', 96), t.get('tracking', 140)
        meta, (px, py) = B.text(g, t['text'], 'serif', tsize, t['x'], t['y'], anchor='cap_top_left', color=INK,
                                name=f"TXT - title {t['text'].strip()}", tracking=ttrk)
        base_x, base_y = px + meta['anchors']['baseline_left'][0], py + meta['anchors']['baseline_left'][1]
        st = self.lay.get('subtitle')
        if st:
            dx = st.get('dx', 'auto')
            if dx == 'auto':
                txt = t['text']
                k = next((i for i, ch in enumerate(txt) if ch.isalpha()), 0)
                if k:
                    w_all = T.measure(txt[:k] + 'X', 'serif', tsize, ttrk)['width']
                    w_x = T.measure('X', 'serif', tsize, ttrk)['width']
                    dx = w_all - w_x
                else:
                    dx = 0
            B.text(g, st['text'], 'italic', st.get('size', 40), base_x + dx, base_y + st.get('dy', 72),
                   color=INK_SOFT, name=f"TXT - subtitle {st['text']}", tracking=st.get('tracking', 300))
        for k, (txt, (x, y), align) in enumerate(self.lay.get('footer', [])):
            B.text(g, txt, 'italic', 34, x, y, color=INK_FOOT, name=f'TXT - key line {k + 1}', tracking=120,
                   align=align, anchor='origin')
        return g

    def readme(self):
        fonts = sorted({n.font for n in self.B.doc.root.iter_layers() if getattr(n, 'kind', '') == 'text'})
        txt = README_V2.format(title=TITLES[self.sheet], fonts=', '.join(fonts),
                               sources=self.lay.get('sources', '').strip())
        rgba, meta = T.text_rgba(txt, 'mono', 30, color=INK, leading=1.45, max_width=2700)
        h, w = rgba.shape[:2]
        bg = C.solid(h + 160, w + 160, '#F7F2E8')
        a = rgba[..., 3:4]
        bg[80:80 + h, 80:80 + w, :3] = rgba[..., :3] * a + bg[80:80 + h, 80:80 + w, :3] * (1 - a)
        g = Group('!! READ ME - how this file is built', hidden=True, opened=False)
        self.B.doc.root.add(g)
        g.add(page_pixel('READ ME - notes (hide group to view)', bg, 160, 400))
        return g

    # ------------------------------------------------------------------ all
    def build(self):
        t0 = time.time()
        self.paper()
        self.fragments('behind')
        self.view()
        self.echoes()
        self.fragments('front')
        self.grain()
        self.intensity()
        self.notes()
        self.title()
        self.readme()
        dedupe_names(self.B.doc)
        self.acc.clear()
        self.log(f'sheet {self.sheet}: {self.B.doc.layer_count()} layers/groups in {time.time() - t0:.1f} s')
        return self.B.doc


README_V2 = """{title}

HOW THIS FILE IS BUILT (v2 composer src/v2/compose.py, layout data src/v2/layout.py)
- A3 portrait, 3508 x 4961 px at 300 ppi, sRGB IEC61966-2.1 (embedded), 8-bit RGB.
- Groups from the back: 00 Paper > 10 Fragments behind > 20 Main view > 30 Echo patches >
  40 Fragments in front > 50 Overlap intensity > 60 Notes > 90 Title and key line.
- Nothing is erased. Every material fragment is its own group: 'Shadow - ...' (multiply), the
  material photo with a LAYER MASK for its torn or cut edge (paint the mask to change the edge -
  the photo extends beyond it), and 'Rim - ...' = the white paper core of the torn edge.
  Move the whole group to move a fragment with its shadow.
- The main view is the render behind a stepped LAYER MASK; its shadow and torn-edge rim are
  separate layers. Echo patches are pieces of the same render, enlarged and laid over its edge.
- Overlap intensity washes, the paper colour and the vignette are SOLID COLOR fill layers:
  double-click the thumbnail to recolour, lower the opacity to calm them.
- TYPE: each 'TXT - ...' layer is the rendered text. The hidden 'EDIT - ...' layer directly
  above it is live type with the same font, size, tracking, rotation and position. To reword:
  show EDIT, type, then hide TXT. Arrows are separate pixel layers ('Arrow - ...') in the same
  note group, so a note moves with its arrow.
- Fonts (free, SIL OFL; install before editing type): {fonts}.
  All of them are in fonts-to-install.zip, delivered beside this file.
- Paper layers are locked to avoid accidental edits; unlock them in the Layers panel.

SOURCES
- {sources}
- Paper texture, torn edges, shadows, arrows: made for this file.

Hide this group (eye icon) to see the collage.
"""


# --------------------------------------------------------------------------------------------- #
# outputs
# --------------------------------------------------------------------------------------------- #

def to_u8(comp):
    return np.clip(np.floor(comp * 255.0 + 0.5), 0, 255).astype(np.uint8)


def save_preview(comp8, path, height=1600, quality=90):
    im = Image.fromarray(comp8)
    s = height / im.height
    im = im.resize((round(im.width * s), height), Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, quality=quality)
    return path


CROPS = {'title': (0, 0, 1800, 1300), 'left': (0, 900, 1400, 2700), 'right': (2300, 300, 3508, 2100),
         'bottom_left': (0, 3500, 1800, 4961), 'bottom_right': (1700, 3500, 3508, 4961)}


def fingerprint(sheet, inputs):
    """sha1 over the v2 build sources, the shared toolchain, the fonts and every input image."""
    files = sorted([os.path.join(HERE, f) for f in os.listdir(HERE) if f.endswith('.py')]
                   + [os.path.join(SRC, f) for f in ('psdkit.py', 'write_psd.js', 'finalize.py')]
                   + [os.path.join(SRC, 'lib', f) for f in ('compose.py', 'typeset.py', 'collage_common.py')])
    h = hashlib.sha1()
    for p in files:
        h.update(rel(p).encode())
        h.update(open(p, 'rb').read())
    data = sorted(set(list(inputs) + [os.path.join(ROOT, 'assets', 'mat', 'paper_linen_A3.png'),
                                      os.path.join(ROOT, 'assets', 'fonts', 'hand', 'NothingYouCouldDo.ttf'),
                                      os.path.join(ROOT, 'assets', 'fonts', 'CormorantGaramond-Regular.ttf'),
                                      os.path.join(ROOT, 'assets', 'fonts', 'CormorantGaramond-Italic.ttf')]))
    for p in data:
        h.update(rel(p).encode())
        h.update(sha1_file(p).encode())
    try:
        head = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, capture_output=True,
                              text=True).stdout.strip()
    except Exception:       # noqa: BLE001
        head = 'unknown'
    return {'sources_sha1': h.hexdigest()[:16], 'git_head_at_export': head,
            'files': [rel(p) for p in files], 'inputs': {rel(p): sha1_file(p)[:12] for p in inputs}}


def verify_psd(psd_path, comp8, doc, icc, build_dir):
    """Re-open the PSD with psd-tools (independent reader + compositor) - finalize.py's checks."""
    import io
    from psd_tools import PSDImage
    from psd_tools.constants import Resource
    rep = {}
    psd = PSDImage.open(psd_path)
    rep['psd_size'] = list(psd.size)
    rep['psd_layers_read'] = sum(1 for _ in psd.descendants())
    icc_res = psd.image_resources.get_data(Resource.ICC_PROFILE)
    rep['psd_icc_bytes'] = len(icc_res) if icc_res else 0
    rep['psd_has_version_info'] = psd.image_resources.get_data(Resource.VERSION_INFO) is not None
    rep['psd_type_layers'] = sum(1 for l in psd.descendants() if l.kind == 'type')
    traw = psd.image_resources.get_data(Resource.THUMBNAIL_RESOURCE)
    try:
        ti = Image.open(io.BytesIO(bytes(traw.data)))
        ti.load()
        rep['psd_thumbnail'] = [traw.fmt, ti.format, *ti.size]
    except Exception as e:      # noqa: BLE001
        rep['psd_thumbnail'] = f'unreadable: {e}'
    ri = psd.image_resources.get_data(Resource.RESOLUTION_INFO)
    rep['psd_resolution_ppi'] = round(getattr(ri, 'horizontal', 0) / 65536, 2) if ri else None
    n_text = sum(1 for n in doc.root.iter_layers() if n.kind == 'text')
    assert rep['psd_size'] == [PW, PH], f"PSD size {rep['psd_size']}"
    assert rep['psd_icc_bytes'] == len(icc), 'ICC profile missing from PSD'
    assert isinstance(rep['psd_thumbnail'], list), 'PSD thumbnail missing or unreadable'
    assert rep['psd_resolution_ppi'] == DPI, 'PSD resolution is not 300 ppi'
    assert rep['psd_type_layers'] == n_text, f"{rep['psd_type_layers']} type layers read, {n_text} written"
    assert rep['psd_layers_read'] == doc.layer_count(), 'layer count differs'
    embedded = np.asarray(psd.composite().convert('RGB'), np.int16)
    rep['embedded_composite_maxdiff'] = int(np.abs(embedded - comp8).max())
    assert rep['embedded_composite_maxdiff'] == 0, 'embedded composite differs from the render'
    del embedded
    rerender = np.asarray(psd.composite(force=True).convert('RGB'), np.int16)
    d = np.abs(rerender - comp8.astype(np.int16))
    rep['rerender_mean_diff'] = round(float(d.mean()), 3)
    rep['rerender_p99_diff'] = float(np.percentile(d, 99))
    rep['rerender_max_diff'] = int(d.max())
    heat = Image.fromarray(np.clip(d.max(axis=2) * 8, 0, 255).astype(np.uint8))
    heat.thumbnail((1600, 1600))
    heat.save(os.path.join(build_dir, 'verify_diff_x8.png'))
    return rep


def export_final(sheet, doc, sources, log=print):
    """finalize.py adapted to v2: A3 portrait, output/v2, v2 slugs, input-aware build stamp."""
    import finalize as FIN                     # src/finalize.py (v1, unchanged): ICC injection, layer tree, names
    t0 = time.time()
    if sources.placeholders:
        raise MissingInputs(sources.placeholders)
    slug = SLUGS[sheet]
    inputs = sheet_inputs(sheet)
    stamp0 = fingerprint(sheet, inputs)
    build_dir = os.path.join(FINAL_BUILD, slug)
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(build_dir, exist_ok=True)
    comp = doc.render()
    doc.export(build_dir, composite=comp)
    del comp
    comp8 = np.asarray(Image.open(os.path.join(build_dir, 'composite.png')).convert('RGB'))
    th = Image.fromarray(comp8)
    th.thumbnail((160, 160), Image.LANCZOS)
    th.save(os.path.join(build_dir, 'thumb.jpg'), quality=85)
    psd_path = os.path.join(OUT_DIR, f'{slug}.psd')
    res = subprocess.run(['node', os.path.join(SRC, 'write_psd.js'), build_dir, psd_path, '--icc', ICC_PATH],
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError('write_psd failed:\n' + res.stdout + res.stderr)
    writer = json.loads(res.stdout.strip().splitlines()[-1])
    icc = open(ICC_PATH, 'rb').read()
    FIN.inject_icc(psd_path, icc)
    stamp = fingerprint(sheet, inputs)
    if stamp['sources_sha1'] != stamp0['sources_sha1']:
        raise RuntimeError('build sources or inputs changed during the export - re-run')
    try:
        dirty = subprocess.run(['git', 'status', '--porcelain', '--'] + stamp['files'], cwd=ROOT,
                               capture_output=True, text=True).stdout.split('\n')
        stamp['uncommitted_source_files'] = [ln[3:] for ln in dirty if ln.strip()]
    except Exception:       # noqa: BLE001
        stamp['uncommitted_source_files'] = None
    im = Image.fromarray(comp8)
    jpg_path = os.path.join(OUT_DIR, f'{slug}.jpg')
    im.save(jpg_path, quality=95, subsampling=0, dpi=(DPI, DPI), icc_profile=icc, optimize=True)
    prev = im.copy()
    prev.thumbnail((2000, 2000), Image.LANCZOS)
    prev.save(os.path.join(OUT_DIR, f'{slug}_preview.jpg'), quality=90, icc_profile=icc)
    tree = FIN._tree_lines(doc.root.children)
    dirty = stamp.get('uncommitted_source_files')
    with open(os.path.join(OUT_DIR, f'{slug}_layers.txt'), 'w') as f:
        f.write(f'{doc.title}\n{doc.width} x {doc.height} px @ {doc.dpi} ppi (A3 portrait), sRGB, 8-bit RGB\n')
        f.write(f'{doc.layer_count()} layers/groups - top of the Layers panel first\n')
        f.write(f"build stamp: sources+inputs {stamp['sources_sha1']} - git {stamp['git_head_at_export']}"
                + (' (clean)' if dirty == [] else f' + {len(dirty or [])} uncommitted source files') + '\n')
        f.write('inputs: ' + ', '.join(f'{k} {v}' for k, v in stamp['inputs'].items()) + '\n\n')
        f.write('\n'.join(tree) + '\n')
    bad, dups = FIN.check_names(doc)
    report = {'slug': slug, 'psd': rel(psd_path), 'jpg': rel(jpg_path), 'psd_mb': writer['mb'],
              'jpg_mb': round(os.path.getsize(jpg_path) / 1048576, 1), 'layers_total': doc.layer_count(),
              'writer': writer, 'bad_names': bad, 'duplicate_names': dups, 'stamp': stamp}
    log(f'  wrote {rel(psd_path)} ({writer["mb"]} MB), verifying with psd-tools ...')
    report.update(verify_psd(psd_path, comp8, doc, icc, build_dir))
    report['seconds'] = round(time.time() - t0, 1)
    with open(os.path.join(build_dir, 'report.json'), 'w') as f:
        json.dump(report, f, indent=1)
    if bad or dups:
        raise RuntimeError(f'layer names: bad {bad}, duplicates {dups}')
    return report


FONT_FILES = ('assets/fonts/hand/NothingYouCouldDo.ttf', 'assets/fonts/hand/OFL-NothingYouCouldDo.txt',
              'assets/fonts/CormorantGaramond-Regular.ttf', 'assets/fonts/CormorantGaramond-Italic.ttf',
              'assets/fonts/OFL-CormorantGaramond.txt')


def write_fonts_zip(log=print):
    """output/v2/fonts-to-install.zip: the fonts the live type uses + their SIL OFL licences."""
    import zipfile
    out = os.path.join(OUT_DIR, 'fonts-to-install.zip')
    os.makedirs(OUT_DIR, exist_ok=True)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in FONT_FILES:
            z.write(os.path.join(ROOT, f), os.path.basename(f))
    log(f'  fonts -> {rel(out)}')
    return out


def combined(from_preview=False, log=print):
    """Both portrait sheets side by side on one A3 landscape (A-series: two A3 portraits scaled by
    1/sqrt(2) exactly fill it), like the client's reference spread."""
    icc = open(ICC_PATH, 'rb').read()
    if from_preview:
        srcs = [os.path.join(PREVIEW_DIR, f'sheet{n}.jpg') for n in (1, 2)]
        W_, H_ = 2263, 1600
        out = os.path.join(PREVIEW_DIR, 'combined.jpg')
    else:
        srcs = [os.path.join(OUT_DIR, f'{SLUGS[n]}.jpg') for n in (1, 2)]
        W_, H_ = PH, PW                         # 4961 x 3508
        out = os.path.join(OUT_DIR, f'{COMBINED_SLUG}.jpg')
    miss = [rel(p) for p in srcs if not os.path.exists(p)]
    if miss:
        raise MissingInputs(miss)
    canvas = Image.new('RGB', (W_, H_), CREAM)
    half = W_ / 2
    for k, p in enumerate(srcs):
        im = Image.open(p).convert('RGB')
        x0, x1 = int(round(k * half)), int(round((k + 1) * half))
        canvas.paste(im.resize((x1 - x0, H_), Image.LANCZOS), (x0, 0))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if from_preview:
        canvas.save(out, quality=90)
    else:
        canvas.save(out, quality=95, subsampling=0, dpi=(DPI, DPI), icc_profile=icc, optimize=True)
    log(f'combined sheet -> {rel(out)} ({W_} x {H_})')
    return out


# --------------------------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------------------------- #

def run_sheet(sheet, final=False, crops=False):
    t0 = time.time()
    if final:
        miss = missing_inputs(sheet)
        if miss:
            raise MissingInputs(miss)
    comp_ = Composer(sheet, final=final)
    doc = comp_.build()
    if comp_.src.placeholders:
        print(f'  PLACEHOLDERS (preview only): {", ".join(comp_.src.placeholders)}')
    if final:
        rep = export_final(sheet, doc, comp_.src)
        write_fonts_zip()
        keep = ('psd', 'jpg', 'psd_mb', 'layers_total', 'psd_type_layers', 'embedded_composite_maxdiff',
                'rerender_mean_diff', 'rerender_p99_diff', 'rerender_max_diff', 'seconds')
        print(json.dumps({k: rep.get(k) for k in keep}, indent=1))
        return
    comp8 = to_u8(doc.render())
    p = save_preview(comp8, os.path.join(PREVIEW_DIR, f'sheet{sheet}.jpg'))
    print(f'  preview -> {rel(p)}')
    if crops:
        for nm, (x0, y0, x1, y1) in CROPS.items():
            q = os.path.join(PREVIEW_DIR, 'crops', f'sheet{sheet}_{nm}.jpg')
            os.makedirs(os.path.dirname(q), exist_ok=True)
            im = Image.fromarray(comp8[y0:y1, x0:x1])
            im.thumbnail((1600, 1600), Image.LANCZOS)
            im.save(q, quality=90)
        for nm, (cx, cy) in {'detail_a': (900, 1300), 'detail_b': (3150, 2700), 'detail_c': (1300, 4150)}.items():
            q = os.path.join(PREVIEW_DIR, 'crops', f'sheet{sheet}_{nm}_100pct.png')
            Image.fromarray(comp8[cy - 400:cy + 400, cx - 400:cx + 400]).save(q)
        print(f'  crops -> {rel(os.path.join(PREVIEW_DIR, "crops"))}/')
    print(f'  done in {time.time() - t0:.1f} s')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--sheet', default=None, help="1, 2 or 'all'")
    ap.add_argument('--final', action='store_true', help='layered PSD + JPEG deliverables (no placeholders)')
    ap.add_argument('--combined', action='store_true', help='A3 landscape side-by-side of both sheets')
    ap.add_argument('--from-preview', action='store_true', help='with --combined: use the previews (review only)')
    ap.add_argument('--crops', action='store_true', help='also write detail crops of the preview')
    a = ap.parse_args(argv)
    if a.sheet is None and not a.combined:
        ap.error('give --sheet 1|2|all and/or --combined')
    sheets = [] if a.sheet is None else ([1, 2] if a.sheet == 'all' else [int(a.sheet)])
    try:
        for s in sheets:
            if s not in LAYOUT.SHEETS:
                ap.error(f'unknown sheet {s}')
            print(f'sheet {s}{" (final)" if a.final else " (preview)"}')
            run_sheet(s, final=a.final, crops=a.crops)
        if a.combined:
            combined(from_preview=a.from_preview)
    except MissingInputs as e:
        print('REFUSED: these real input files are missing (placeholders are never exported):', file=sys.stderr)
        for p in e.args[0]:
            print('   ' + p, file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
