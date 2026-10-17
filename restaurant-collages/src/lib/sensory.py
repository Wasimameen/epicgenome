"""sensory — procedural sensory graphics for the atmosphere collages (sound, smell, light,
shade, intensity zones, plan markers, annotation hardware).

Every generator is parametric, deterministic (seeded), anti-aliased (analytic box-filter
coverage or supersampling) and returns

    (rgba, (x, y))   rgba = float32 (H, W, 4) straight alpha, single-colour or graded;
                     (x, y) = integer canvas position of rgba's top-left corner, so
                     `compose.pixel(name, rgba, x, y)` puts the graphic where it was asked.

Positions / sizes are canvas pixels on the A3 @ 300 ppi page (4961 x 3508): 1 mm = 11.81 px,
so a 2 px hairline = 0.17 mm.  Angles are degrees, counter-clockwise on screen, 0 = +x.
Colours are hex strings (defaults from the ART_DIRECTION palette, PAL).

Generators
    sound_rings      concentric ripples / partial arcs (ellipse ratio, decay, dash, echo)
    waveform         sound wave following a curve, amplitude decaying to a flat line
    wisp             rising aroma / smoke: curl-noise ribbons of fine silky filaments
    light_beam       volumetric shaft from an apex/aperture, soft edges, rays, dust motes
    glow             radial glow with a hot core and long halation tail
    dapple           leaf-shadow gobo field (pinnate twigs, depth-layered penumbra)
    intensity_field  smooth multi-blob intensity zones -> colour ramp (+ isolines / field)
    view_cone        plan view-cone marker        north_arrow   plan north point
    arrow            hairline arrow (open / filled / half barb)
    dotted_path      dots along a smooth path      swatch_chip   colour/texture chip + label
    scale_bar        alternating-block scale bar with mono numerals
    paper            warm linen paper ground with fibre grain (opaque RGB)
build() installs the fonts and renders the contact sheet build/contact/sensory.jpg.
"""
from __future__ import annotations

import math
import os

import cv2
import numpy as np
from PIL import Image

from lib import typeset as ts
from lib.typeset import stroke_polyline, fill_contours, catmull_rom, resample, disc_coverage, over

ROOT = ts.ROOT
W_A3, H_A3 = 4961, 3508

PAL = {
    'ink': '#2B2420', 'linen': '#EFE6D6', 'oat': '#DCCDB4', 'sand': '#C9B391',
    'honey': '#E8B062', 'amber': '#D98A3D', 'ember': '#C2602E', 'terracotta': '#A9502F',
    'oxblood': '#6B2430', 'wine': '#4A1A26', 'oak': '#B07A45', 'sage': '#8E9A72',
    'leaf': '#4F6B3A', 'canopy': '#7FA35A', 'glass': '#C8DAD3', 'celadon': '#A9C4BC',
    'dusk': '#3D4A6B', 'indigo': '#262C45', 'violet': '#5A4E7A', 'steel': '#B8BCBD',
    'paper': '#EEE5D3',
}
INK = PAL['ink']


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #

def C(c):
    """Colour -> float32 RGB 0..1 (accepts palette names, hex, 0..255 or 0..1 tuples)."""
    if isinstance(c, str) and not c.startswith('#'):
        c = PAL[c]
    return ts._rgb(c)


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _grid(x0, y0, w, h):
    """Pixel-centre coordinates of a window: gx (1, w), gy (h, 1), float32."""
    gx = (np.arange(w, dtype=np.float32) + x0 + 0.5)[None, :]
    gy = (np.arange(h, dtype=np.float32) + y0 + 0.5)[:, None]
    return gx, gy


def _dither(a, seed, amount=1.0):
    """Triangular-PDF dither of +-1 LSB so smooth 8-bit ramps do not band."""
    rng = np.random.default_rng(seed + 7919)
    n = (rng.random(a.shape, dtype=np.float32) - rng.random(a.shape, dtype=np.float32)) * (amount / 255.0)
    return np.clip(a + n * (a > 0), 0, 1)


def _solid_rgba(alpha, color):
    out = np.empty(alpha.shape + (4,), np.float32)
    out[..., :3] = C(color)
    out[..., 3] = alpha
    return out


def _graded_rgba(alpha, c0, c1, t):
    """RGBA whose colour runs c0 -> c1 with the per-pixel parameter t (0..1)."""
    out = np.empty(alpha.shape + (4,), np.float32)
    a, b = C(c0), C(c1)
    t = np.clip(t, 0, 1)[..., None]
    out[..., :3] = a + (b - a) * t
    out[..., 3] = alpha
    return out


def _ramp(stops, t):
    """Piecewise-linear colour ramp; stops = [colour, ...] evenly spaced or [(pos, colour)]."""
    if all(isinstance(s, str) for s in stops):
        stops = [(i / (len(stops) - 1), s) for i, s in enumerate(stops)]
    pos = np.array([p for p, _ in stops], np.float32)
    cols = np.stack([C(c) for _, c in stops])
    t = np.clip(t, 0, 1)
    out = np.empty(t.shape + (3,), np.float32)
    for ch in range(3):
        out[..., ch] = np.interp(t, pos, cols[:, ch])
    return out


def smooth_noise(h, w, scale, seed, octaves=3, persistence=0.5):
    """Smooth value noise (bicubic-upsampled random lattices), roughly -1..1, float32."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot, sc = 1.0, 0.0, float(scale)
    for _ in range(octaves):
        gh, gw = max(2, int(h / sc) + 3), max(2, int(w / sc) + 3)
        g = rng.standard_normal((gh, gw)).astype(np.float32)
        up = cv2.resize(g, (int(gw * sc), int(gh * sc)), interpolation=cv2.INTER_CUBIC)
        oy, ox = int(rng.integers(0, max(1, up.shape[0] - h))), int(rng.integers(0, max(1, up.shape[1] - w)))
        out += amp * up[oy:oy + h, ox:ox + w]
        tot += amp
        amp *= persistence
        sc /= 2.0
        if sc < 2:
            break
    return out / (tot * 0.9)


def noise1d(u, seed, freq=4.0, octaves=4):
    """Smooth 1-D noise ~ -1..1 on parameter u (array), freq = cycles per unit."""
    rng = np.random.default_rng(seed)
    u = np.asarray(u, np.float64)
    out = np.zeros_like(u)
    tot = 0.0
    for o in range(octaves):
        f = freq * (2 ** o) * rng.uniform(0.75, 1.3)
        a = 0.55 ** o
        out += a * np.sin(2 * np.pi * f * u + rng.uniform(0, 2 * np.pi))
        tot += a
    return out / tot * 1.4


class CurlField:
    """Divergence-free 2-D velocity from a random Fourier stream function (curl noise)."""

    def __init__(self, seed, scale=400.0, modes=12, octave_spread=1.9):
        rng = np.random.default_rng(seed)
        ang = rng.uniform(0, 2 * np.pi, modes)
        mag = 2 * np.pi / scale * np.exp(rng.uniform(0, np.log(octave_spread), modes))
        self.k = np.stack([np.cos(ang) * mag, np.sin(ang) * mag], 1)
        self.ph = rng.uniform(0, 2 * np.pi, modes)
        self.a = 1.0 / (mag * math.sqrt(modes / 2))

    def __call__(self, x, y):
        x = np.asarray(x, np.float64)[..., None]
        y = np.asarray(y, np.float64)[..., None]
        c = np.cos(self.k[:, 0] * x + self.k[:, 1] * y + self.ph) * self.a
        dpx = (c * self.k[:, 0]).sum(-1)
        dpy = (c * self.k[:, 1]).sum(-1)
        return dpy, -dpx


def _splat(xs, ys, wts, x0, y0, w, h):
    """Bilinear point splat of weights into a (h, w) float32 grid (window top-left x0, y0)."""
    fx = xs - x0 - 0.5
    fy = ys - y0 - 0.5
    ix = np.floor(fx).astype(np.int64)
    iy = np.floor(fy).astype(np.int64)
    tx = fx - ix
    ty = fy - iy
    acc = np.zeros(h * w, np.float64)
    for dx, dy, ww in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                       (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        jx, jy = ix + dx, iy + dy
        ok = (jx >= 0) & (jx < w) & (jy >= 0) & (jy < h)
        acc += np.bincount((jy[ok] * w + jx[ok]), weights=(wts * ww)[ok], minlength=h * w)
    return acc.reshape(h, w).astype(np.float32)


def _gauss1d(v, sigma):
    """Gaussian smoothing of a 1-D sequence with edge-preserving ends (reflect)."""
    if sigma <= 0:
        return v
    r = int(sigma * 3) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    vp = np.concatenate([2 * v[0] - v[r:0:-1], v, 2 * v[-1] - v[-2:-r - 2:-1]])
    return np.convolve(vp, k, mode='valid')


def _blur(a, sigma):
    if sigma <= 0:
        return a
    k = int(sigma * 3.5) * 2 + 1
    return cv2.GaussianBlur(a, (k, k), sigma, borderType=cv2.BORDER_CONSTANT)


def _edge_window(w, h, frac):
    """(h, w) window that rises smoothly from 0 at the borders to 1 over `frac` of the size."""
    xs = np.arange(w, dtype=np.float32) + 0.5
    ys = np.arange(h, dtype=np.float32) + 0.5
    ex = _smoothstep(0, frac * w, np.minimum(xs, w - xs))[None, :]
    ey = _smoothstep(0, frac * h, np.minimum(ys, h - ys))[:, None]
    return (ex * ey).astype(np.float32)


def _soft_window(w, h, frac, p=4.0):
    """Soft rounded-rectangle (superellipse) window: 1 inside, 0 at the borders."""
    xs = np.abs((np.arange(w, dtype=np.float32) + 0.5) / w * 2 - 1)[None, :]
    ys = np.abs((np.arange(h, dtype=np.float32) + 0.5) / h * 2 - 1)[:, None]
    r = (xs ** p + ys ** p) ** (1 / p)
    return (1 - _smoothstep(1 - 2 * frac, 1.0, r)).astype(np.float32)


def _rotm(deg):
    t = math.radians(deg)
    return np.array([[math.cos(t), math.sin(t)], [-math.sin(t), math.cos(t)]])


def _unit(deg):
    t = math.radians(deg)
    return np.array([math.cos(t), -math.sin(t)])  # screen coords (y down)


def _stamp_max(dst, src, x, y):
    """dst = max(dst, src) with src's top-left at (x, y) in dst, clipped."""
    h, w = src.shape
    H, W = dst.shape
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 > x0 and y1 > y0:
        sub = dst[y0:y1, x0:x1]
        np.maximum(sub, src[y0 - y:y1 - y, x0 - x:x1 - x], out=sub)


def _crop_alpha(rgba, x, y, pad=2):
    """Trim fully transparent margins (keeps `pad` px) and shift the offset accordingly."""
    a = rgba[..., 3]
    nz = np.nonzero(a > 1.0 / 512)
    if not len(nz[0]):
        return rgba[:1, :1], (x, y)
    y0, y1 = max(0, nz[0].min() - pad), min(a.shape[0], nz[0].max() + 1 + pad)
    x0, x1 = max(0, nz[1].min() - pad), min(a.shape[1], nz[1].max() + 1 + pad)
    return np.ascontiguousarray(rgba[y0:y1, x0:x1]), (x + int(x0), y + int(y0))


# --------------------------------------------------------------------------- #
# SOUND
# --------------------------------------------------------------------------- #

def sound_rings(at=(0, 0), r_max=600.0, n=7, r_min=None, ratio=1.0, angle=0.0, width=2.2,
                color=INK, color_outer=None, alpha=0.85, decay=0.8, thin=0.94, spacing=1.18,
                arc=None, end_fade=14.0, breaks=0, break_len=(6.0, 22.0), dash=None,
                echo=0.0, echo_alpha=0.4, wobble=0.0, center_dot=0.0, seed=1):
    """Concentric sound ripples.

    at          centre (canvas px)            r_max / r_min  outer / inner radius (major axis)
    n           number of rings               ratio          minor/major (1 = circles)
    angle       ellipse rotation (deg)        width          stroke width of the inner ring
    alpha/decay ring k has alpha * decay**k   thin           ring k width = width * thin**k
    spacing     >1 = rings open out with radius (ripple), 1 = even
    arc         (start, end) deg in the ellipse frame -> partial arcs (e.g. (-55, 55))
    end_fade    soft fade length (deg) at arc ends and breaks
    breaks      random gaps per ring          break_len      gap length range (deg)
    dash        (on, off) px along each ring  echo           px offset of a fainter twin ring
    wobble      0..0.03 low-frequency radial irregularity (organic, hand-drawn)
    color_outer optional colour of the outermost ring (linear blend through the rings)
    center_dot  radius of a source dot (0 = none)
    """
    rng = np.random.default_rng(seed)
    cx, cy = at
    r_min = r_max * 0.12 if r_min is None else r_min
    k = float(ratio)
    margin = width + 4 + abs(echo) + r_max * wobble * 1.5
    R = r_max * max(1.0, k) + margin
    x0, y0 = int(math.floor(cx - R)), int(math.floor(cy - R))
    w = h = int(math.ceil(2 * R)) + 2
    gx, gy = _grid(x0, y0, w, h)
    X = np.broadcast_to(gx - cx, (h, w)).ravel()
    Y = np.broadcast_to(-(gy - cy), (h, w)).ravel()
    t = math.radians(angle)
    u = X * math.cos(t) + Y * math.sin(t)
    v = -X * math.sin(t) + Y * math.cos(t)
    del X, Y
    rho = np.sqrt(u * u + (v / k) ** 2) + 1e-6
    gmax = max(1.0, 1.0 / k)
    # premultiplied accumulation; every ring is evaluated only inside its own thin band
    acc_c = np.zeros((h * w, 3), np.float32)
    acc_a = np.zeros(h * w, np.float32)
    ca = C(color)
    cb = C(color_outer) if color_outer is not None else ca
    for i in range(n):
        f = i / max(1, n - 1)
        r = r_min + (r_max - r_min) * f ** spacing
        wi = width * thin ** i
        ai = alpha * decay ** i
        band = (wi + 1) / 2 + 2 + abs(echo) + r * wobble * 1.6
        idx = np.flatnonzero(np.abs(rho - r) < band * gmax)
        if not len(idx):
            continue
        ui, vi, ri = u[idx], v[idx], rho[idx]
        grad = np.sqrt(ui * ui + vi * vi / k ** 4) / ri + 1e-6
        theta = np.degrees(np.arctan2(vi / k, ui)).astype(np.float32)
        vis = np.ones_like(theta)
        if arc is not None:
            a0, a1 = arc
            span = (a1 - a0) % 360 or 360
            rel = (theta - a0) % 360
            ef = min(end_fade, span / 2.5)
            vis = _smoothstep(0, ef, rel) * _smoothstep(0, ef, span - rel) * (rel <= span)
        for _ in range(breaks):
            bc = rng.uniform(0, 360) if arc is None else rng.uniform(arc[0], arc[0] + ((arc[1] - arc[0]) % 360))
            bl = rng.uniform(*break_len)
            dd = np.abs(((theta - bc) + 180) % 360 - 180)
            vis = vis * _smoothstep(bl / 2, bl / 2 + end_fade * 0.6, dd)
        rr = r
        if wobble:
            ph = rng.uniform(0, 2 * np.pi, 3)
            th = np.radians(theta)
            rr = r * (1 + wobble * (0.6 * np.sin(2 * th + ph[0]) + 0.3 * np.sin(3 * th + ph[1])
                                    + 0.2 * np.sin(5 * th + ph[2])))
        rings = [(0.0, wi, ai)]
        if echo:  # twin ring at a constant *pixel* offset (signed distance), not in ellipse space
            rings.append((echo, wi * 0.6, ai * echo_alpha))
        col = ca + (cb - ca) * f
        sd = (ri - rr) / grad
        for off, ww, aa in rings:
            d = np.abs(sd - off)
            cov = np.clip((ww + 1) / 2 - d, 0, min(ww, 1.0))
            if dash is not None:
                s_ = np.radians(theta) * (r + off)
                per = dash[0] + dash[1]
                s_ = s_ % per
                cov = cov * np.maximum(np.clip(np.minimum(s_ + 0.5, dash[0] + 0.5 - s_), 0, 1),
                                       np.clip(s_ - per + 0.5, 0, 1))
            a = (cov * vis * aa).astype(np.float32)
            nz = a > 0
            j, a = idx[nz], a[nz]
            acc_c[j] = col[None, :] * a[:, None] + acc_c[j] * (1 - a[:, None])
            acc_a[j] = a + acc_a[j] * (1 - a)
    del u, v, rho
    out = np.zeros((h, w, 4), np.float32)
    out[..., 3] = acc_a.reshape(h, w)
    out[..., :3] = (acc_c / np.maximum(acc_a, 1e-6)[:, None]).reshape(h, w, 3)
    del acc_c, acc_a
    if center_dot:
        a = disc_coverage(cx, cy, center_dot, h, w, x0, y0) * alpha
        over(out, _solid_rgba(a, color))
    return _crop_alpha(out, x0, y0)


def waveform(path, amplitude=60.0, wavelength=46.0, width=2.0, color=INK, alpha=0.9,
             decay_start=0.35, decay_end=0.85, decay_curve=1.6, strands=3, strand_amp=0.42,
             strand_alpha=0.55, modulation=0.65, mod_freq=2.6, style='line', bar_step=10.0,
             bar_width=None, axis_width=1.1, axis_alpha=0.6, attack=0.05, seed=3):
    """A sound wave travelling along a curve whose amplitude decays to a flat line (sound
    absorbed into the linen / the void).

    path        canvas points the wave follows (smoothed with a centripetal Catmull-Rom spline)
    amplitude   peak half-height (px)          wavelength  px per cycle
    decay_*     amplitude envelope fades between these fractions of the length (curve power)
    modulation  0..1 voice-like amplitude bursts (syllables); mod_freq bursts per length
    style       'line'  -> `strands` interfering sine strands (oscilloscope look)
                'bars'  -> perpendicular hairline bars every bar_step px (audio-file look)
                           over a thin axis line; bars shrink to dots on the flat tail
    """
    P = catmull_rom(np.asarray(path, np.float64), spacing=1.0) if len(path) > 2 else \
        resample(np.asarray(path, np.float64), 1.0)
    seg = np.diff(P, axis=0)
    L = np.concatenate([[0], np.cumsum(np.hypot(seg[:, 0], seg[:, 1]))])
    Ltot = L[-1]
    T = np.gradient(P, axis=0)
    T /= np.maximum(np.hypot(T[:, 0], T[:, 1]), 1e-9)[:, None]
    N = np.stack([-T[:, 1], T[:, 0]], 1)
    u = L / Ltot
    env = _smoothstep(0, attack, u) * (1 - _smoothstep(decay_start, decay_end, u)) ** decay_curve
    mod = 1 - modulation * (0.5 + 0.5 * noise1d(u, seed, mod_freq, 3))
    A = amplitude * env * mod
    margin = amplitude + width + 6
    x0 = int(math.floor(P[:, 0].min() - margin))
    y0 = int(math.floor(P[:, 1].min() - margin))
    x1 = int(math.ceil(P[:, 0].max() + margin))
    y1 = int(math.ceil(P[:, 1].max() + margin))
    box = (x0, y0, x1, y1)
    cov = np.zeros((y1 - y0, x1 - x0), np.float32)
    rng = np.random.default_rng(seed)
    if style == 'line':
        for j in range(strands):
            fj = 1.0 if j == 0 else strand_amp ** (0.5 + 0.5 * j) * rng.uniform(0.85, 1.15)
            lam = wavelength * (1.0 if j == 0 else rng.uniform(0.62, 1.45))
            ph = 0.0 if j == 0 else rng.uniform(0, 2 * np.pi)
            off = A * fj * np.sin(2 * np.pi * L / lam + ph)
            Q = P + N * off[:, None]
            aj = 1.0 if j == 0 else strand_alpha * (0.85 ** (j - 1))
            wj = width if j == 0 else width * 0.72
            c, _ = stroke_polyline(Q, wj, alpha=aj, box=box)
            np.maximum(cov, c, out=cov)
    elif style == 'bars':
        bw = bar_width or width
        ax, _ = stroke_polyline(P, axis_width, alpha=axis_alpha, box=box)
        np.maximum(cov, ax, out=cov)
        tex = 0.35 + 0.65 * np.abs(noise1d(u, seed + 11, Ltot / (wavelength * 0.9), 3)).clip(0, 1)
        for s in np.arange(bar_step * 0.5, Ltot, bar_step):
            i = int(np.searchsorted(L, s))
            i = min(i, len(P) - 1)
            hh = A[i] * tex[i]
            p, nn = P[i], N[i]
            if hh < 0.5:
                seg_pts = np.array([p, p + nn * 0.01])
            else:
                seg_pts = np.array([p - nn * hh, p + nn * hh])
            c, (bx, by) = stroke_polyline(seg_pts, bw)
            _stamp_max(cov, c, bx - x0, by - y0)
    else:
        raise ValueError(style)
    return _crop_alpha(_solid_rgba(cov * alpha, color), x0, y0)


# --------------------------------------------------------------------------- #
# SMELL — rising wisps
# --------------------------------------------------------------------------- #

def wisp(at=(0, 0), height=1300.0, ribbons=3, width=70.0, color=PAL['honey'], color_top=None,
         opacity=0.7, filaments=150, curl_scale=380.0, turbulence=1.0, lean=0.0, twist=1.3,
         spread=1.0, billow=0.9, silk=0.55, haze=0.35, filament_width=1.0, gain=0.8, thickness=0.09,
         fade_in=0.05, fade_out=0.4, seed=7):
    """Rising aroma / smoke: `ribbons` translucent curling ribbons.  Each ribbon is a sheet
    of many fine filaments whose centre-line is advected through a curl-noise flow field
    (laminar at the source, increasingly turbulent with height).  The sheet twists, so it
    folds into bright edge-on lines and opens into faint silky faces; it billows and fans
    out coherently towards the top and fades away.  A soft veil surrounds the filaments.

    at          source point (bottom of the wisp)     height      rise (px)
    width       ribbon width (px) once developed      filaments   filaments per ribbon
    curl_scale  flow-noise wavelength (px)            turbulence  0.4 calm .. 1.6 agitated
    lean        horizontal drift (fraction of rise, + = right)    twist  folds per ribbon
    spread      lateral separation of the ribbons     billow      coherent sheet deformation
    silk        0..1 visibility of the fine striations (vs a smooth sheet)
    thickness   sheet thickness relative to its width (width of the edge-on fold lines)
    haze        soft veil amount   gain  optical density of a face-on sheet
    color / color_top  colour at the source / at the top (None = single colour)
    """
    rng = np.random.default_rng(seed)
    sx, sy = at
    field = CurlField(seed, curl_scale, 12)
    ds = 2.0
    lines = []  # (xs, ys, weights, u)
    for r in range(ribbons):
        fr = CurlField(seed * 31 + r * 7 + 1, curl_scale * 0.7, 8)
        p = np.array([sx + rng.normal(0, width * 0.06), sy + rng.uniform(0, width * 0.1)])
        pts = [p.copy()]
        max_len = height * rng.uniform(0.9, 1.3)
        tot = 0.0
        side = (r - (ribbons - 1) / 2) * spread * 0.35

        def vel(q):
            hgt = np.clip((sy - q[1]) / height, 0, 1.5)
            tb = turbulence * (0.12 + 0.88 * _smoothstep(0.0, 0.55, hgt))
            v0 = np.array(field(q[0], q[1]))
            v1 = np.array(fr(q[0], q[1]))
            v = np.array([lean + side * hgt, -1.0]) + tb * (v0 + 0.55 * v1)
            return v / max(np.hypot(*v), 0.35)
        while tot < max_len:
            v = vel(p)
            v = vel(p + 0.5 * ds * v)
            p = p + ds * v
            pts.append(p.copy())
            tot += ds
            if sy - p[1] > height * 1.08:
                break
        Cl = resample(np.array(pts), 0.45)
        n = len(Cl)
        if n < 10:
            continue
        s = np.arange(n) * 0.45
        u = s / s[-1]
        # normals from a smoothed centre-line so tight turns never flip the sheet
        sig = max(4.0, width * 0.35) / 0.45
        Cs = np.stack([_gauss1d(Cl[:, 0], sig), _gauss1d(Cl[:, 1], sig)], 1)
        Tg = np.gradient(Cs, axis=0)
        Tg /= np.maximum(np.hypot(Tg[:, 0], Tg[:, 1]), 1e-9)[:, None]
        Nm = np.stack([-Tg[:, 1], Tg[:, 0]], 1)
        rw = rng.uniform(0.7, 1.15)
        Wd = width * rw * (0.05 + 0.95 * _smoothstep(0.0, 0.42, u)) * (0.8 + 0.55 * u) \
            * (1 + 0.3 * noise1d(u, seed + r * 13, 1.4, 2))
        th = rng.uniform(0, 2 * np.pi) + 2 * np.pi * twist * rng.uniform(0.7, 1.3) * u \
            + 0.9 * noise1d(u, seed + r * 17, 1.1, 2)
        fold, edge = np.cos(th), np.sin(th)
        fade = _smoothstep(0, fade_in, u) * (1 - _smoothstep(1 - fade_out, 1.0, u))
        rib_w = rng.uniform(0.75, 1.0)
        ph_c = rng.uniform(0, 2 * np.pi)
        fq = rng.uniform(1.0, 1.8)
        for j in range(filaments):
            uj = -1 + 2 * (j + rng.uniform(0.1, 0.9)) / filaments
            vj = rng.uniform(-1, 1)  # depth inside the sheet (gives the folds a thickness)
            lj = rng.uniform(0.7, 1.0)
            fj = fade * (1 - _smoothstep(lj - fade_out * 0.7, lj, u)) if lj < 0.98 else fade
            wj = (0.25 + 0.75 * rng.random() ** 1.5) * rib_w
            # coherent billow: neighbouring filaments move together, the sheet fans and ripples
            coh = np.sin(2 * np.pi * fq * u + ph_c + 1.9 * uj) * 0.6 + \
                noise1d(u + 0.08 * uj, seed + 1000 * r + 3, 2.2, 2) * 0.4
            ind = noise1d(u, seed + 1000 * r + 11 + j, rng.uniform(2.0, 4.0), 2)
            drift = billow * width * u ** 1.5 * (coh + 0.6 * uj * u) + 0.08 * width * u ** 2 * ind
            br = 0.6 + 0.4 * _smoothstep(-0.3, 0.6, noise1d(u, seed + 5000 + 97 * r + j, 2.0, 2))
            off = 0.5 * Wd * (uj * fold + thickness * vj * edge) + drift
            F = Cl + Nm * off[:, None]
            dl = np.hypot(*np.diff(F, axis=0).T)
            dl = np.minimum(np.concatenate([dl, dl[-1:]]), 3.0)
            lines.append((F[:, 0], F[:, 1], dl * fj * wj * br, u))
    if not lines:
        return np.zeros((1, 1, 4), np.float32), (int(sx), int(sy))
    xs = np.concatenate([l[0] for l in lines])
    ys = np.concatenate([l[1] for l in lines])
    wt = np.concatenate([l[2] for l in lines])
    uu = np.concatenate([l[3] for l in lines])
    pad = int(width * 1.2 + 40)
    x0, y0 = int(math.floor(xs.min())) - pad, int(math.floor(ys.min())) - pad
    w, h = int(math.ceil(xs.max())) - x0 + pad, int(math.ceil(ys.max())) - y0 + pad
    D = _splat(xs, ys, wt, x0, y0, w, h) * (width / filaments)
    fine = _blur(D, max(0.5, 0.5 * filament_width))
    soft = _blur(D, max(2.5, width * 0.06))
    veil = _blur(D, max(10.0, width * 0.7))
    dens = silk * fine + (1 - silk) * soft + haze * veil * 1.5
    a = opacity * (1 - np.exp(-gain * dens))
    a = _dither(a.astype(np.float32), seed)
    if color_top is None:
        rgba = _solid_rgba(a, color)
    else:
        t = _blur(_splat(xs, ys, wt * uu, x0, y0, w, h) * (width / filaments), 8.0) / \
            np.maximum(_blur(D, 8.0), 1e-6)
        rgba = _graded_rgba(a, color, color_top, _smoothstep(0.05, 0.9, t))
    return _crop_alpha(rgba, x0, y0)


# --------------------------------------------------------------------------- #
# LIGHT
# --------------------------------------------------------------------------- #

def light_beam(apex=(0, 0), angle=-90.0, length=2000.0, spread=12.0, aperture=0.0,
               color=PAL['honey'], intensity=0.55, edge_softness=0.45, falloff=1.1, fade_in=0.08,
               fade_out=0.25, core=0.25, rays=0.2, ray_count=12, dust=140, dust_size=(0.9, 4.0),
               dust_alpha=0.75, dust_color=None, seed=11):
    """Volumetric light shaft from an apex (or an aperture of width `aperture`, e.g. a
    skylight) in direction `angle` (deg CCW, -90 = straight down the page).

    spread        half-angle (deg)              edge_softness  0..1 of the half-width
    falloff       intensity decay power along the length; fade_in / fade_out ends
    core          extra brightness on the axis  rays           strength of soft internal streaks
    dust          number of motes (more in the bright core), sizes px, alpha, colour
    """
    rng = np.random.default_rng(seed)
    d = _unit(angle)
    nrm = np.array([-d[1], d[0]])
    ax, ay = apex
    tg = math.tan(math.radians(spread))
    hw0 = aperture / 2
    hw1 = hw0 + length * tg
    corners = np.array([[ax, ay] + nrm * hw0, [ax, ay] - nrm * hw0,
                        np.array([ax, ay]) + d * length + nrm * hw1,
                        np.array([ax, ay]) + d * length - nrm * hw1])
    x0, y0 = np.floor(corners.min(0) - 8).astype(int)
    x1, y1 = np.ceil(corners.max(0) + 8).astype(int)
    w, h = x1 - x0, y1 - y0
    gx, gy = _grid(x0, y0, w, h)
    X, Y = gx - ax, gy - ay
    t = X * d[0] + Y * d[1]
    q = X * nrm[0] + Y * nrm[1]
    del X, Y
    hw = hw0 + np.maximum(t, 0) * tg + 1e-3
    xn = q / hw
    u = t / length
    soft = max(1e-3, edge_softness)
    across = _smoothstep(1.0, 1.0 - soft, np.abs(xn)) * (1 + core * (1 - np.minimum(1, np.abs(xn))) ** 2)
    along = _smoothstep(0, fade_in, u) * np.clip(1 - u, 0, 1) ** falloff * (1 - _smoothstep(1 - fade_out, 1, u))
    beam = across * along
    if rays:
        # soft streaks fixed to the beam's angular coordinate, slowly breaking up along it
        # irregular streaks: 1-D noise across the beam (radiating from the apex), sampled on
        # a lookup table and cross-faded with a second set along the length so they break up
        xa = np.clip(xn, -1.2, 1.2)
        lut_x = np.linspace(-1.2, 1.2, 2048)
        n1 = noise1d(lut_x, seed + 1, ray_count / 2.4, 4)
        n2 = noise1d(lut_x, seed + 2, ray_count / 2.0, 4)
        idx = np.clip(((xa + 1.2) / 2.4 * 2047).astype(np.int32), 0, 2047)
        mixw = _smoothstep(0.1, 0.9, u)
        st = (n1[idx] * (1 - mixw) + n2[idx] * mixw).astype(np.float32)
        beam = beam * (1 + rays * st)
    beam = np.clip(beam, 0, None) * intensity
    del t, q, hw, across, along
    a = 1 - np.exp(-1.6 * beam)  # soft saturation
    a = a / (1 - math.exp(-1.6 * max(intensity, 1e-3) * (1 + core))) * min(1.0, intensity * 1.15)
    a = np.clip(a, 0, 1).astype(np.float32)
    rgba = _solid_rgba(_dither(a, seed), color)
    if dust:
        # sample motes where the beam is bright (rejection sampling on the beam field)
        m = np.zeros((h, w), np.float32)
        n_try = dust * 8
        uu = rng.uniform(0.05, 0.92, n_try)
        xx = rng.uniform(-0.95, 0.95, n_try)
        keep = rng.random(n_try) < (1 - np.abs(xx)) ** 1.5 * (1 - uu) ** 0.6
        uu, xx = uu[keep][:dust], xx[keep][:dust]
        hwm = hw0 + uu * length * tg
        px = ax + d[0] * uu * length + nrm[0] * xx * hwm
        py = ay + d[1] * uu * length + nrm[1] * xx * hwm
        sizes = dust_size[0] + (dust_size[1] - dust_size[0]) * rng.random(len(px)) ** 3
        bright = rng.uniform(0.35, 1.0, len(px))
        for x_, y_, r_, b_ in zip(px, py, sizes, bright):
            rr = int(r_ * 3 + 3)
            bx0, by0 = int(x_) - rr - x0, int(y_) - rr - y0
            bx1, by1 = bx0 + 2 * rr + 1, by0 + 2 * rr + 1
            if bx0 < 0 or by0 < 0 or bx1 > w or by1 > h:
                continue
            lx, ly = _grid(bx0 + x0, by0 + y0, bx1 - bx0, by1 - by0)
            dd = np.sqrt((lx - x_) ** 2 + (ly - y_) ** 2)
            if r_ < 1.6:
                g = np.clip(r_ + 0.5 - dd, 0, 1) * (r_ / 1.6)
            else:  # larger motes are out of focus: soft-edged, dimmer discs
                g = _smoothstep(r_ + 1.2, r_ * 0.35, dd) * (1.6 / r_) ** 0.6
            sub = m[by0:by1, bx0:bx1]
            np.maximum(sub, (g * b_).astype(np.float32), out=sub)
        m *= dust_alpha
        dc = dust_color or _mix_hex(color, '#FFFFFF', 0.55)
        over(rgba, _solid_rgba(m, dc))
    return _crop_alpha(rgba, int(x0), int(y0))


def _mix_hex(a, b, t):
    ca, cb = C(a), C(b)
    c = ca + (cb - ca) * t
    return '#%02X%02X%02X' % tuple(int(round(v * 255)) for v in c)


def glow(at=(0, 0), radius=400.0, color=PAL['honey'], intensity=0.8, ratio=1.0, angle=0.0,
         core=0.16, core_strength=0.55, hot_color=None, tail=1.0, seed=13):
    """Radial glow: a hot core (gaussian, `core` x radius) plus a long halation tail that
    reaches exactly zero at `radius`.  ratio/angle make it elliptical; hot_color tints the
    centre (e.g. '#FFF4DC' for a lamp).  Use with 'screen' / 'linear dodge' / normal."""
    cx, cy = at
    k = float(ratio)
    R = radius * max(1.0, k) + 4
    x0, y0 = int(math.floor(cx - R)), int(math.floor(cy - R))
    w = h = int(math.ceil(2 * R)) + 1
    gx, gy = _grid(x0, y0, w, h)
    X, Y = gx - cx, -(gy - cy)
    t = math.radians(angle)
    u = X * math.cos(t) + Y * math.sin(t)
    v = -X * math.sin(t) + Y * math.cos(t)
    r = np.sqrt(u * u + (v / k) ** 2) / radius
    halo = np.exp(-3.2 * r ** 2 / tail) * (1 - _smoothstep(0.55, 1.0, r))
    hot = np.exp(-(r / core) ** 2)
    a = np.clip(intensity * ((1 - core_strength) * halo + core_strength * hot), 0, 1).astype(np.float32)
    a = _dither(a, seed)
    if hot_color is None:
        rgba = _solid_rgba(a, color)
    else:
        rgba = _graded_rgba(a, color, hot_color, hot ** 0.7)
    return _crop_alpha(rgba, x0, y0)


# --------------------------------------------------------------------------- #
# SHADE — leaf-shadow gobo
# --------------------------------------------------------------------------- #

def _leaf_poly(base, direction, length, width, bend=0.0, tip=1.0, n=30):
    """Elliptic-lanceolate leaflet outline: rounded base, drawn-out pointed tip, the midrib
    bent by `bend` (fraction of length)."""
    t = np.linspace(0, 1, n)
    half = width / 2 * np.sin(np.pi * t ** 0.8) ** 0.85 * (1 - 0.2 * t ** 4) ** tip
    d = np.asarray(direction, float)
    d = d / np.linalg.norm(d)
    nm = np.array([-d[1], d[0]])
    mid = base[None, :] + d[None, :] * (t * length)[:, None] + nm[None, :] * (bend * length * t * t)[:, None]
    left = mid + nm[None, :] * half[:, None]
    right = mid - nm[None, :] * half[:, None]
    return np.vstack([left, right[::-1]])


def _rot2(v, a):
    c, s_ = math.cos(a), math.sin(a)
    return np.array([c * v[0] - s_ * v[1], s_ * v[0] + c * v[1]])


def _pinnate_twig(rng, start, direction, Ls, n_pairs, droop, polys, twigs):
    """One compound leaf / twig: a gently curving rachis with paired leaflets that vary in
    size, angle and foreshortening, plus a terminal leaflet."""
    gap = Ls * rng.uniform(0.55, 0.75)
    curv = rng.normal(0, 0.06)
    d = direction / np.linalg.norm(direction)
    rach = [np.asarray(start, float)]
    for _ in range(n_pairs + 1):
        d = _rot2(d, curv + droop * 0.04 * np.sign(d[0] or 1))
        d = d / np.linalg.norm(d)
        rach.append(rach[-1] + d * gap * rng.uniform(0.9, 1.1))
    rach = np.array(rach)
    twigs.append(rach)
    grav = np.array([0.0, 1.0])
    for k in range(1, len(rach)):
        p = rach[k]
        tdir = rach[k] - rach[k - 1]
        tdir /= np.linalg.norm(tdir)
        nm = np.array([-tdir[1], tdir[0]])
        size_k = 0.7 + 0.3 * math.sin(math.pi * min(1.0, k / (len(rach) - 0.5)))  # mid leaflets largest
        for sgn in (-1, 1):
            if rng.random() < 0.1:
                continue
            la = Ls * size_k * rng.uniform(0.75, 1.2)
            ang = math.radians(rng.uniform(38, 72))
            ld = tdir * math.cos(ang) + sgn * nm * math.sin(ang)
            ld = ld + droop * grav * rng.uniform(0.2, 0.7) + rng.normal(0, 0.14, 2)
            fore = rng.uniform(0.22, 0.46) if rng.random() > 0.15 else rng.uniform(0.08, 0.2)
            polys.append(_leaf_poly(p + sgn * nm * 1.5, ld, la, la * fore, bend=rng.normal(0, 0.12)))
    polys.append(_leaf_poly(rach[-1], tdir + rng.normal(0, 0.1, 2), Ls * rng.uniform(0.95, 1.2),
                            Ls * rng.uniform(0.32, 0.42), bend=rng.normal(0, 0.1)))


def dapple(size=(2400, 1600), at=(0, 0), leaf_size=64.0, density=0.42, color='#3A3024', opacity=0.6,
           layers=4, penumbra=(2.5, 7.0, 18.0, 42.0), layer_strength=(1.0, 0.92, 0.78, 0.6),
           twig_width=3.2, droop=0.6, angle=-25.0, light=False, light_color=PAL['honey'],
           light_gamma=1.6, breathing=0.18, edge_fade=0.0, seed=5):
    """Leaf-shadow (gobo) field for multiply layers, after the void's pinnate-leaved tree.

    Branches carry twigs (compound leaves) of paired lanceolate leaflets that vary in size,
    angle, droop and foreshortening.  Leaves sit on `layers` depth planes: the near plane
    casts nearly crisp shadows, farther planes are spread by an elliptical sun-disc kernel
    (`penumbra` = kernel radius per plane, px) so gaps between them become the soft round
    light-flecks of real dappled light.

    density     0..1 leaf coverage            leaf_size   leaflet length (px)
    angle       mean branch direction (deg)   droop       0..1 leaflets hanging down
    light       True -> the light that passes (light_color, for screen / soft-light layers);
                use a dense canopy (density ~1.4) so only flecks come through; light_gamma
                concentrates the light into the brightest gaps
    breathing   large-scale open/dense variation
    edge_fade   fraction of the size over which the pattern fades out at the borders (0 = off)
    Returns (rgba, at)."""
    W, H = size
    rng = np.random.default_rng(seed)
    trans = np.ones((H, W), np.float32)
    for li in range(layers):
        depth = li / max(1, layers - 1)
        sc = 1.0 + 0.35 * depth
        Ls = leaf_size * sc
        polys, twigs = [], []
        target = density * W * H / layers * (1.15 - 0.3 * depth)
        area = 0.0
        guard = 0
        # stratified (jittered-grid) anchor points so the canopy covers the field evenly
        cell = max(Ls * 5.0, min(W, H) / 4.0)
        gxs = np.arange(-0.5, W / cell + 0.5)
        gys = np.arange(-0.5, H / cell + 0.5)
        anchors = np.array([(x, y) for y in gys for x in gxs], float)
        anchors = (anchors + rng.uniform(0, 1, anchors.shape)) * cell
        anchors = anchors[rng.permutation(len(anchors))]
        while area < target and guard < 600:
            # a branch passes through the next anchor and carries several twigs
            ang = math.radians(angle + rng.normal(0, 30))
            bdir = np.array([math.cos(ang), -math.sin(ang)])
            p = anchors[guard % len(anchors)] - bdir * rng.uniform(3, 6) * Ls
            guard += 1
            blen = rng.uniform(5, 11) * Ls
            bp = [p]
            for _ in range(10):
                bdir = _rot2(bdir, rng.normal(0, 0.12))
                bp.append(bp[-1] + bdir * blen / 10)
            bp = np.array(bp)
            twigs.append(bp)
            n_tw = int(rng.integers(3, 7))
            for k in range(n_tw):
                f = (k + rng.uniform(0.3, 0.9)) / n_tw
                i = min(len(bp) - 2, int(f * (len(bp) - 1)))
                base = bp[i] + (bp[i + 1] - bp[i]) * rng.random()
                tdir = bp[i + 1] - bp[i]
                tdir = _rot2(tdir / np.linalg.norm(tdir), (1 if k % 2 else -1) * math.radians(rng.uniform(25, 60)))
                npairs = int(rng.integers(3, 7))
                n0 = len(polys)
                _pinnate_twig(rng, base, tdir, Ls * rng.uniform(0.85, 1.1), npairs, droop, polys, twigs)
                for pl in polys[n0:]:  # only leaf area that lands inside the field counts
                    cx_, cy_ = pl.mean(0)
                    if 0 <= cx_ < W and 0 <= cy_ < H:
                        area += 0.6 * Ls * Ls * 0.3
        ss = 4 if li == 0 else 2
        m = fill_contours(polys, H, W, ss=ss)
        for tw in twigs:
            P = catmull_rom(tw, spacing=3.0)
            wv = np.linspace(twig_width * sc * 1.3, twig_width * sc * 0.5, len(P))
            c, (tx, ty) = stroke_polyline(P, wv)
            _stamp_max(m, c, tx, ty)
        pen = penumbra[min(li, len(penumbra) - 1)]
        if pen >= 1.5:
            r = int(round(pen))
            ker = np.zeros((2 * r + 1, 2 * r + 1), np.float32)
            cv2.ellipse(ker, (r, r), (r, max(1, int(r * 0.86))), 20, 0, 360, 1.0, -1, cv2.LINE_AA)
            ker /= ker.sum()
            m = cv2.filter2D(m, -1, ker, borderType=cv2.BORDER_CONSTANT)
        m = _blur(m, 0.8 + 0.12 * pen)
        st = layer_strength[min(li, len(layer_strength) - 1)]
        trans *= (1 - st * np.clip(m, 0, 1))
    S = 1 - trans
    if breathing:
        S *= np.clip(1 - breathing + breathing * (0.5 + 0.5 * smooth_noise(H, W, max(W, H) / 2.5, seed + 99, 2)),
                     0, 1)
    if edge_fade:
        S = S * _edge_window(W, H, edge_fade)
    S = np.clip(S, 0, 1).astype(np.float32)
    if light:
        Lt = (1 - S) ** light_gamma
        return _solid_rgba(_dither(Lt * opacity, seed), light_color), (int(at[0]), int(at[1]))
    return _solid_rgba(_dither(S * opacity, seed), color), (int(at[0]), int(at[1]))


# --------------------------------------------------------------------------- #
# INTENSITY ZONES
# --------------------------------------------------------------------------- #

def intensity_field(size=(2000, 1400), at=(0, 0), blobs=None, n=5,
                    ramp=('linen', 'honey', 'amber', 'terracotta', 'oxblood'), warp=0.12, gamma=1.0,
                    alpha_mode='field', alpha_max=0.9, contours=0, contour_width=1.4, contour_color=INK,
                    contour_alpha=0.45, edge_fade=0.12, seed=9, return_field=False):
    """Smooth multi-blob intensity zones mapped through a colour ramp.

    blobs       [(x, y, rx, ry, angle_deg, weight), ...] in local px (None -> n random)
    warp        organic domain warp (fraction of the field size)
    gamma       field shaping (>1 tightens the hot cores)
    alpha_mode  'field' (alpha = field, for colour washes / masks) or 'opaque'
    contours    number of hairline isolines (0 = none) — sound/scent contour diagram look
    edge_fade   width (fraction of the size) of a soft rounded-rectangle window applied to the
                alpha and isolines only, so the layer never ends in a hard edge; 0 = off
    return_field  also return the float field (H, W) 0..1 (use it directly as a layer mask)
    Returns (rgba, at[, field])."""
    W, H = size
    rng = np.random.default_rng(seed)
    if blobs is None:
        blobs = []
        for _ in range(n):
            blobs.append((rng.uniform(0.22, 0.78) * W, rng.uniform(0.22, 0.78) * H,
                          rng.uniform(0.1, 0.24) * W, rng.uniform(0.1, 0.24) * H,
                          rng.uniform(0, 180), rng.uniform(0.5, 1.0)))
    # the field is smooth: evaluate it on a coarse grid and upsample (bicubic)
    q = max(1, int(math.ceil(max(W, H) / 1100)))
    w_, h_ = int(math.ceil(W / q)) + 2, int(math.ceil(H / q)) + 2
    gx, gy = _grid(0, 0, w_, h_)
    gx = np.broadcast_to(gx * q, (h_, w_)).astype(np.float32)
    gy = np.broadcast_to(gy * q, (h_, w_)).astype(np.float32)
    if warp:
        sc = max(W, H) * 0.35 / q
        gx = gx + warp * max(W, H) * 0.5 * smooth_noise(h_, w_, sc, seed + 1, 2)
        gy = gy + warp * max(W, H) * 0.5 * smooth_noise(h_, w_, sc, seed + 2, 2)
    F = np.zeros((h_, w_), np.float32)
    for (bx, by, rx, ry, ba, wt) in blobs:
        t = math.radians(ba)
        X, Y = gx - bx, gy - by
        u = X * math.cos(t) + Y * math.sin(t)
        v = -X * math.sin(t) + Y * math.cos(t)
        F += wt * np.exp(-((u / rx) ** 2 + (v / ry) ** 2))
    del gx, gy
    F = 1 - np.exp(-1.6 * F)
    F = F / max(F.max(), 1e-6)
    if q > 1:
        F = cv2.resize(F, (w_ * q, h_ * q), interpolation=cv2.INTER_CUBIC)
        sh = (q - 1) / 2.0  # align coarse sample centres with the fine grid
        M = np.float32([[1, 0, sh], [0, 1, sh]])
        F = cv2.warpAffine(F, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    F = np.ascontiguousarray(np.clip(F[:H, :W], 0, 1) ** gamma, dtype=np.float32)
    win = _soft_window(W, H, edge_fade) if edge_fade else None
    lut = _ramp(list(ramp), np.linspace(0, 1, 1024, dtype=np.float32))
    rgba = np.empty((H, W, 4), np.float32)
    rgba[..., :3] = lut[np.clip((F * 1023 + 0.5).astype(np.int32), 0, 1023)]
    rgba[..., 3] = (F * alpha_max) if alpha_mode == 'field' else 1.0
    if win is not None:
        rgba[..., 3] *= win
    rgba[..., 3] = _dither(rgba[..., 3], seed)
    if contours:
        levels = np.linspace(0, 1, contours + 2)[1:-1]
        cc = C(contour_color)
        band = 512
        for y0 in range(0, H, band):
            a0, a1 = max(0, y0 - 1), min(H, y0 + band + 1)
            Fb = F[a0:a1]
            gyF, gxF = np.gradient(Fb)
            g = np.sqrt(gxF ** 2 + gyF ** 2) + 1e-6
            cov = np.zeros_like(Fb)
            for lv in levels:
                c = np.clip((contour_width + 1) / 2 - np.abs(Fb - lv) / g, 0, min(1.0, contour_width))
                np.maximum(cov, c, out=cov)
            sl = slice(y0 - a0, y0 - a0 + min(band, H - y0))
            cov = cov[sl] * contour_alpha
            if win is not None:
                cov *= win[y0:y0 + cov.shape[0]]
            dst = rgba[y0:y0 + cov.shape[0]]
            sa = cov[..., None]
            da = dst[..., 3:4]
            oa = sa + da * (1 - sa)
            dst[..., :3] = (cc * sa + dst[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6)
            dst[..., 3:4] = oa
    if return_field:
        return rgba, (int(at[0]), int(at[1])), (F * win if win is not None else F)
    return rgba, (int(at[0]), int(at[1]))


# --------------------------------------------------------------------------- #
# PLAN MARKERS + ANNOTATION HARDWARE
# --------------------------------------------------------------------------- #

def view_cone(apex=(0, 0), direction=0.0, fov=60.0, length=900.0, color=INK, fill=0.16,
              fill_falloff=1.4, edge_width=1.8, edge_alpha=0.85, edge_dash=None, arc=True,
              arc_dash=(2.0, 9.0), arc_width=1.6, apex_dot=7.0, apex_ring=14.0, seed=17):
    """Plan view cone: graded translucent wedge (fades with distance), hairline edges
    (optionally dashed), a dotted arc at the far end and an eye-point dot + ring."""
    ax, ay = apex
    half = math.radians(fov / 2)
    R = length + 12
    x0, y0 = int(math.floor(ax - R)), int(math.floor(ay - R))
    w = h = int(math.ceil(2 * R)) + 1
    gx, gy = _grid(x0, y0, w, h)
    X, Y = gx - ax, -(gy - ay)
    r = np.sqrt(X * X + Y * Y)
    th = np.arctan2(Y, X) - math.radians(direction)
    th = (th + np.pi) % (2 * np.pi) - np.pi
    # analytic AA at the straight edges: perpendicular distance to the edge ray
    dist_edge = r * np.sin(half - np.abs(th))
    inside = np.clip(dist_edge + 0.5, 0, 1) * np.clip(length - r + 0.5, 0, 1)
    grad = np.clip(1 - r / length, 0, 1) ** fill_falloff
    a = (inside * grad * fill).astype(np.float32)
    rgba = _solid_rgba(_dither(a, seed), color)
    box = (x0, y0, x0 + w, y0 + h)
    cov = np.zeros((h, w), np.float32)
    for sgn in (-1, 1):
        e = np.array([ax, ay]) + _unit(direction + sgn * fov / 2) * length
        c, _ = stroke_polyline(np.array([[ax, ay], e]), edge_width,
                               alpha=np.array([edge_alpha, edge_alpha * 0.55]), dash=edge_dash, box=box)
        np.maximum(cov, c, out=cov)
    if arc:
        tt = np.linspace(direction - fov / 2, direction + fov / 2, max(16, int(length * math.radians(fov) / 3)))
        pts = np.array([np.array([ax, ay]) + _unit(t) * length for t in tt])
        c, _ = stroke_polyline(pts, arc_width, alpha=edge_alpha * 0.8, dash=arc_dash, box=box)
        np.maximum(cov, c, out=cov)
    if apex_ring:
        c, _ = stroke_polyline(ts._circle(ax, ay, apex_ring, 120), 1.4, closed=True, box=box)
        np.maximum(cov, c * edge_alpha, out=cov)
    if apex_dot:
        np.maximum(cov, disc_coverage(ax, ay, apex_dot, h, w, x0, y0), out=cov)
    over(rgba, _solid_rgba(cov, color))
    return _crop_alpha(rgba, x0, y0)


def north_arrow(at=(0, 0), size=180.0, angle=0.0, color=INK, width=1.6, label='N',
                font='mono', label_size=None, upright_label=True, ring=True):
    """Plan north point: hairline circle, slender half-filled needle, mono 'N' at the tip.
    angle rotates north counter-clockwise from page-up."""
    cx, cy = at
    R = size / 2
    rot = lambda p: np.asarray(p) @ _rotm(angle).T + np.array([cx, cy])  # noqa: E731
    tip = np.array([0, -R * 1.18])
    tail = np.array([0, R * 0.92])
    wing = R * 0.2
    left = np.array([-wing, R * 0.08])
    right = np.array([wing, R * 0.08])
    mid = np.array([0, R * 0.08 - wing * 0.35])
    pad = int(R * 1.6 + 40)
    x0, y0 = int(cx - pad), int(cy - pad)
    w = h = 2 * pad
    box = (x0, y0, x0 + w, y0 + h)
    cov = np.zeros((h, w), np.float32)
    # filled west half of the north needle
    poly = rot(np.array([tip, left, mid])) - np.array([x0, y0])
    np.maximum(cov, fill_contours([poly], h, w, ss=8), out=cov)
    outline = rot(np.array([tip, right, mid, tip]))
    c, _ = stroke_polyline(outline, width, box=box)
    np.maximum(cov, c, out=cov)
    c, _ = stroke_polyline(rot(np.array([tip, left, mid])), width, closed=True, box=box)
    np.maximum(cov, c, out=cov)
    # south half: hairline needle
    c, _ = stroke_polyline(rot(np.array([left, tail, right])), width * 0.8, box=box)
    np.maximum(cov, c * 0.8, out=cov)
    if ring:
        c, _ = stroke_polyline(ts._circle(cx, cy, R, 180), width, closed=True, box=box)
        np.maximum(cov, c, out=cov)
    np.maximum(cov, disc_coverage(cx, cy, width * 1.6, h, w, x0, y0), out=cov)
    rgba = _solid_rgba(cov, color)
    if label:
        ls = label_size or size * 0.2
        txt, m = ts.text_rgba(label, font, ls, color, tracking=0, align='center',
                              angle=0 if upright_label else angle)
        tp = rot(tip + np.array([0, -ls * 1.05]))
        # centre the cap height on the point above the tip
        ax_, ay_ = m['origin']
        px = int(round(tp[0] - ax_)) - x0
        py = int(round(tp[1] - ay_ + m['cap_height'] / 2)) - y0 if upright_label else \
            int(round(tp[1] - ay_)) - y0
        over(rgba, txt, px, py)
    return _crop_alpha(rgba, x0, y0)


def arrow(points, width=2.0, color=INK, head='open', head_len=None, head_angle=20.0,
          smooth=True, dash=None, tail_dot=0.0, opacity=1.0):
    """Hairline arrow along points (smooth spline when > 2 points).
    head: 'open' (two hairline barbs), 'filled' (slender barbed triangle), 'half' (single
    barb, architectural) or None."""
    P = np.asarray(points, np.float64)
    P = catmull_rom(P, spacing=1.5) if (smooth and len(P) > 2) else resample(P, 1.5)
    hl = head_len or (8 * width + 14)
    tipp = P[-1]
    Ls = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))])
    j = int(np.searchsorted(Ls, Ls[-1] - hl * 0.9))
    dvec = tipp - P[max(0, j - 1)]
    dvec /= max(np.linalg.norm(dvec), 1e-9)
    nm = np.array([-dvec[1], dvec[0]])
    ha = math.radians(head_angle)
    b1 = tipp - hl * (dvec * math.cos(ha) + nm * math.sin(ha))
    b2 = tipp - hl * (dvec * math.cos(ha) - nm * math.sin(ha))
    shaft = P
    if head == 'filled':
        cut = Ls[-1] - hl * 0.55
        shaft = P[Ls <= cut]
    m = hl + width + tail_dot + 6
    x0, y0 = int(math.floor(P[:, 0].min() - m)), int(math.floor(P[:, 1].min() - m))
    x1, y1 = int(math.ceil(P[:, 0].max() + m)), int(math.ceil(P[:, 1].max() + m))
    box = (x0, y0, x1, y1)
    h, w = y1 - y0, x1 - x0
    cov, _ = stroke_polyline(shaft, width, dash=dash, box=box)
    if head == 'open':
        for b in (b1, b2):
            c, _ = stroke_polyline(np.array([b, tipp]), width, box=box)
            np.maximum(cov, c, out=cov)
    elif head == 'half':
        c, _ = stroke_polyline(np.array([b1, tipp]), width, box=box)
        np.maximum(cov, c, out=cov)
    elif head == 'filled':
        back = tipp - dvec * hl * 0.72
        poly = np.array([tipp, b1, back, b2]) - np.array([x0, y0])
        np.maximum(cov, fill_contours([poly], h, w, ss=8), out=cov)
    if tail_dot:
        np.maximum(cov, disc_coverage(P[0, 0], P[0, 1], tail_dot, h, w, x0, y0), out=cov)
    return _crop_alpha(_solid_rgba(cov * opacity, color), x0, y0)


def dotted_path(points, spacing=14.0, dot_r=2.2, color=INK, smooth=True, alpha=(1.0, 1.0),
                grow=(1.0, 1.0), opacity=1.0, phase=0.0):
    """Evenly spaced anti-aliased dots along a smooth path; alpha / radius interpolate from
    the start value to the end value (e.g. alpha=(1, 0.2) fades the trail)."""
    P = np.asarray(points, np.float64)
    P = catmull_rom(P, spacing=1.0) if (smooth and len(P) > 2) else resample(P, 1.0)
    Ls = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))])
    s = np.arange(phase, Ls[-1] + 1e-6, spacing)
    xs = np.interp(s, Ls, P[:, 0])
    ys = np.interp(s, Ls, P[:, 1])
    f = s / max(Ls[-1], 1e-6)
    al = alpha[0] + (alpha[1] - alpha[0]) * f
    rr = dot_r * (grow[0] + (grow[1] - grow[0]) * f)
    m = rr.max() + 3
    x0, y0 = int(math.floor(xs.min() - m)), int(math.floor(ys.min() - m))
    x1, y1 = int(math.ceil(xs.max() + m)), int(math.ceil(ys.max() + m))
    cov = np.zeros((y1 - y0, x1 - x0), np.float32)
    for x_, y_, r_, a_ in zip(xs, ys, rr, al):
        k = int(r_ + 3)
        bx0, by0 = int(x_) - k - x0, int(y_) - k - y0
        sub = cov[by0:by0 + 2 * k + 1, bx0:bx0 + 2 * k + 1]
        d = disc_coverage(x_, y_, r_, sub.shape[0], sub.shape[1], bx0 + x0, by0 + y0) * a_
        np.maximum(sub, d, out=sub)
    return _crop_alpha(_solid_rgba(cov * opacity, color), x0, y0)


def swatch_chip(fill=PAL['terracotta'], at=(0, 0), size=(240, 170), label='auto', sublabel='auto',
                shape='rect', border=1.2, border_color=INK, border_alpha=0.55, label_size=24,
                label_font='mono', sub_font='mono-light', label_color=INK, label_gap=22,
                tracking=110, radius=None):
    """Colour or texture chip with a mono label beneath.
    fill     hex / palette name, or an RGB(A) float array (cover-cropped into the chip)
    shape    'rect' | 'round' (rounded corners) | 'circle' | 'arch' (round-headed)
    label    'auto' -> the palette name for palette fills; None for no label
    sublabel 'auto' -> the hex value for colour fills; None for none
    at       top-left of the chip (canvas px).  Returns (rgba, (x, y))."""
    cw, ch = size
    if isinstance(fill, str) and not fill.startswith('#'):
        name = fill.upper()
        fill = PAL[fill]
    else:
        name = None
    if label == 'auto':
        label = name
    # chip geometry (local coords)
    if shape == 'circle':
        poly = ts._circle(cw / 2, ch / 2, min(cw, ch) / 2, 240)
    elif shape == 'arch':
        r = cw / 2
        t = np.linspace(np.pi, 2 * np.pi, 120)
        top = np.stack([cw / 2 + r * np.cos(t), r + r * np.sin(t)], 1)
        poly = np.vstack([[[0, ch]], top, [[cw, ch]]])
    elif shape == 'round':
        rr = radius or min(cw, ch) * 0.12
        pts = []
        for (ccx, ccy, a0) in ((cw - rr, rr, -90), (cw - rr, ch - rr, 0), (rr, ch - rr, 90), (rr, rr, 180)):
            t = np.radians(np.linspace(a0, a0 + 90, 16))
            pts.append(np.stack([ccx + rr * np.cos(t), ccy + rr * np.sin(t)], 1))
        poly = np.vstack(pts)
    else:
        poly = np.array([[0, 0], [cw, 0], [cw, ch], [0, ch]], float)
    pad = 4
    lab_h = 0
    texts = []
    if label:
        t1, m1 = ts.text_rgba(label, label_font, label_size, label_color, tracking=tracking, uppercase=True)
        texts.append((t1, m1, label_gap + m1['cap_height']))
        lab_h = label_gap + m1['cap_height'] + m1['descender'] * 0.3
    sub = None
    if sublabel == 'auto' and isinstance(fill, str):
        sub = fill.upper()
    elif sublabel and sublabel != 'auto':
        sub = sublabel
    if sub:
        t2, m2 = ts.text_rgba(sub, sub_font, label_size * 0.82, label_color, tracking=tracking * 0.8,
                              uppercase=True, opacity=0.8)
        yb = lab_h + label_size * 0.5 + m2['cap_height'] if label else label_gap + m2['cap_height']
        texts.append((t2, m2, yb))
        lab_h = yb + m2['descender'] * 0.3
    tw = max([t[0].shape[1] for t in texts], default=0)
    W = int(max(cw, tw) + 2 * pad)
    H = int(ch + lab_h + 2 * pad + 8)
    out = np.zeros((H, W, 4), np.float32)
    P = poly + pad
    m = fill_contours([P], H, W, ss=8)
    if isinstance(fill, str):
        out[..., :3] = C(fill)
        out[..., 3] = m
    else:
        arr = np.asarray(fill, np.float32)
        if arr.max() > 1.0:
            arr = arr / 255.0
        if arr.shape[2] == 3:
            arr = np.dstack([arr, np.ones(arr.shape[:2], np.float32)])
        ih, iw = arr.shape[:2]
        s = max(cw / iw, ch / ih)
        rs = cv2.resize(arr, (max(1, round(iw * s)), max(1, round(ih * s))),
                        interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LANCZOS4)
        oy, ox = (rs.shape[0] - ch) // 2, (rs.shape[1] - cw) // 2
        crop = np.clip(rs[oy:oy + ch, ox:ox + cw], 0, 1)
        out[pad:pad + ch, pad:pad + cw] = crop
        out[..., 3] = out[..., 3] * m
    if border:
        bc, _ = stroke_polyline(P, border, closed=True, box=(0, 0, W, H))
        bc = bc * border_alpha
        over(out, _solid_rgba(bc, border_color))
    for t, mm, yb in texts:
        ox_, oy_ = mm['origin']
        over(out, t, pad - ox_, int(round(pad + ch + yb)) - oy_)
    return out, (int(at[0]) - pad, int(at[1]) - pad)


def scale_bar(at=(0, 0), px_per_unit=118.11, ticks=(0, 1, 2, 5), unit='m', height=12.0,
              width=1.5, color=INK, label_size=24, font='mono-light', title=None, title_size=None,
              tracking=60):
    """Architectural scale bar: alternating filled / open blocks between `ticks` (in units),
    mono numerals centred over each tick, the unit after the last.  at = left end of the
    bar's top edge.  px_per_unit default = 1 m at 1:100 on a 300 ppi page."""
    ax, ay = at
    xs = [ax + t * px_per_unit for t in ticks]
    pad = int(label_size * 3 + 20)
    x0, y0 = int(ax - pad), int(ay - pad - (title_size or label_size) * 3)
    x1, y1 = int(xs[-1] + pad + label_size * 3), int(ay + height + pad)
    w, h = x1 - x0, y1 - y0
    box = (x0, y0, x1, y1)
    cov = np.zeros((h, w), np.float32)
    for i in range(len(xs) - 1):
        if i % 2 == 0:
            poly = np.array([[xs[i], ay], [xs[i + 1], ay], [xs[i + 1], ay + height], [xs[i], ay + height]]) \
                - np.array([x0, y0])
            np.maximum(cov, fill_contours([poly], h, w, ss=8), out=cov)
    outline = np.array([[xs[0], ay], [xs[-1], ay], [xs[-1], ay + height], [xs[0], ay + height]])
    c, _ = stroke_polyline(outline, width, closed=True, box=box)
    np.maximum(cov, c, out=cov)
    for x in xs[1:-1]:
        c, _ = stroke_polyline(np.array([[x, ay], [x, ay + height]]), width, box=box)
        np.maximum(cov, c, out=cov)
    rgba = _solid_rgba(cov, color)
    for i, (t, x) in enumerate(zip(ticks, xs)):
        s = f'{t:g}'
        tx, m = ts.text_rgba(s, font, label_size, color, tracking=tracking, align='center')
        ox_, oy_ = m['origin']
        over(rgba, tx, int(round(x - ox_)) - x0, int(round(ay - label_size * 0.45 - oy_)) - y0)
        if i == len(ticks) - 1 and unit:
            tu, mu = ts.text_rgba(unit, font, label_size, color, tracking=tracking)
            ox2, oy2 = mu['origin']
            over(rgba, tu, int(round(x + m['width'] / 2 + label_size * 0.45 - ox2)) - x0,
                 int(round(ay - label_size * 0.45 - oy2)) - y0)
    if title:
        tsz = title_size or label_size
        tt, mt = ts.text_rgba(title, font, tsz, color, tracking=110, uppercase=True)
        ox_, oy_ = mt['origin']
        cap = ts.measure('0', font, label_size)['cap_height']
        over(rgba, tt, int(round(ax - ox_)) - x0,
             int(round(ay - label_size * 0.45 - cap - tsz * 0.95 - oy_)) - y0)
    return _crop_alpha(rgba, x0, y0)


# --------------------------------------------------------------------------- #
# paper ground (contact sheets, previews)
# --------------------------------------------------------------------------- #

def paper(h, w, color=PAL['paper'], seed=21, fibres=1.0, mottle=1.0):
    """Opaque warm linen paper (float32 RGB): gentle mottling, fine grain and sparse fibres."""
    rng = np.random.default_rng(seed)
    base = C(color)
    lum = 1 + 0.006 * mottle * smooth_noise(h, w, 420, seed, 3)
    grain = _blur(rng.standard_normal((h, w)).astype(np.float32), 0.7) * 0.012
    lum = lum + grain
    if fibres:
        n = int(h * w / 9000 * fibres)
        xs, ys, wt = [], [], []
        for _ in range(n):
            L = rng.uniform(14, 90)
            a = rng.uniform(0, np.pi)
            bend = rng.normal(0, 0.15)
            t = np.arange(0, L, 0.5)
            px = rng.uniform(0, w) + np.cos(a) * t + np.cos(a + np.pi / 2) * bend * t * t / L
            py = rng.uniform(0, h) + np.sin(a) * t + np.sin(a + np.pi / 2) * bend * t * t / L
            xs.append(px)
            ys.append(py)
            wt.append(np.full(len(t), rng.choice([-1.0, 1.0], p=[0.35, 0.65]) * rng.uniform(0.2, 0.6) * 0.5))
        F = _splat(np.concatenate(xs), np.concatenate(ys), np.concatenate(wt), 0, 0, w, h)
        lum = lum + _blur(F, 0.5) * 0.05
    return np.clip(base[None, None, :] * lum[..., None], 0, 1).astype(np.float32)


def ground(h, w, kind='linen', seed=21):
    if kind == 'linen':
        return paper(h, w, PAL['paper'], seed)
    return paper(h, w, PAL['indigo'], seed, fibres=0.6, mottle=1.4)


def composite(bg, rgba, x, y, blend='normal', opacity=1.0):
    """Blend straight-alpha rgba onto an opaque float RGB background in place (preview use)."""
    h, w = rgba.shape[:2]
    H, W = bg.shape[:2]
    sx0, sy0, dx0, dy0 = max(0, -x), max(0, -y), max(0, x), max(0, y)
    ww, hh = min(w - sx0, W - dx0), min(h - sy0, H - dy0)
    if ww <= 0 or hh <= 0:
        return bg
    s = rgba[sy0:sy0 + hh, sx0:sx0 + ww]
    d = bg[dy0:dy0 + hh, dx0:dx0 + ww]
    cs, a = s[..., :3], s[..., 3:4] * opacity
    if blend == 'multiply':
        b = d * cs
    elif blend == 'screen':
        b = d + cs - d * cs
    elif blend == 'soft light':
        b = np.where(cs <= 0.5, 2 * d * cs + d * d * (1 - 2 * cs), np.sqrt(d) * (2 * cs - 1) + 2 * d * (1 - cs))
    elif blend == 'linear dodge':
        b = np.minimum(1, d + cs)
    else:
        b = cs
    d += a * (b - d)
    return bg


def save_rgba(path, rgba):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    a = np.clip(np.floor(rgba * 255 + 0.5), 0, 255).astype(np.uint8)
    Image.fromarray(a, 'RGBA').save(path)
    return path


# --------------------------------------------------------------------------- #
# contact sheet + build
# --------------------------------------------------------------------------- #

CONTACT = os.path.join(ROOT, 'build', 'contact', 'sensory.jpg')
PREVIEW_DIR = os.path.join(ROOT, 'build', 'preview', 'sensory')


def _tiles():
    """(title, caption, fn(kind) -> [(rgba, (x, y), blend, opacity)]) for the contact sheet;
    every tile is 1100 x 1100 px at print resolution (93 x 93 mm)."""
    def ink(k):
        return INK if k == 'linen' else PAL['linen']

    def acc(k):
        return PAL['terracotta'] if k == 'linen' else PAL['honey']

    def t_rings(k):
        a, o = sound_rings((550, 560), r_max=480, n=8, width=2.4, color=ink(k), decay=0.82, wobble=0.006,
                           seed=2, center_dot=6)
        return [(a, o, 'normal', 1)]

    def t_arcs(k):
        a, o = sound_rings((170, 640), r_max=860, n=9, ratio=0.55, angle=8, arc=(-48, 52), breaks=1, width=2.6,
                           color=acc(k), spacing=1.25, echo=7, seed=4, center_dot=7)
        b, ob = sound_rings((860, 250), r_max=200, n=5, dash=(10, 8), width=2.0, color=ink(k), decay=0.75, seed=5)
        return [(a, o, 'normal', 1), (b, ob, 'normal', 1)]

    def t_wave(k):
        a, o = waveform([(70, 330), (400, 250), (750, 360), (1040, 290)], amplitude=70, wavelength=40,
                        color=ink(k), seed=3)
        b, ob = waveform([(70, 820), (520, 720), (1040, 840)], amplitude=95, style='bars', bar_step=9,
                         color=acc(k), seed=6, width=2.2)
        return [(a, o, 'normal', 1), (b, ob, 'normal', 1)]

    def t_wisp(k):
        if k == 'linen':
            a, o = wisp((430, 1070), height=950, width=60, color=PAL['amber'], color_top=PAL['oak'], seed=7)
        else:
            a, o = wisp((430, 1070), height=950, width=60, color=PAL['honey'], color_top=PAL['linen'], seed=7)
        return [(a, o, 'normal', 1)]

    def t_wisp2(k):
        L = []
        for i, (x, sd) in enumerate(((260, 21), (560, 22), (850, 23))):
            c = (PAL['oak'], PAL['ink'], PAL['terracotta'])[i] if k == 'linen' else \
                (PAL['honey'], PAL['linen'], PAL['celadon'])[i]
            a, o = wisp((x, 1060), height=760, width=40, ribbons=2, turbulence=1.25, color=c,
                        opacity=0.55 if k == 'linen' else 0.6, seed=sd)
            L.append((a, o, 'normal', 1))
        return L

    def t_beam(k):
        a, o = light_beam((470, -60), angle=-78, length=1180, spread=12, aperture=70, color=PAL['honey'],
                          intensity=0.55, dust=170, seed=11)
        return [(a, o, 'normal' if k == 'linen' else 'screen', 1)]

    def t_glow(k):
        if k == 'linen':
            a, o = glow((550, 550), radius=430, color=PAL['amber'], intensity=0.7, seed=3)
            b, ob = glow((300, 300), radius=160, color=PAL['ember'], intensity=0.6, ratio=0.6, angle=30, seed=4)
            return [(a, o, 'multiply', 1), (b, ob, 'multiply', 1)]
        a, o = glow((550, 550), radius=430, color=PAL['amber'], hot_color='#FFF2D8', intensity=0.85, seed=3)
        b, ob = glow((300, 300), radius=160, color=PAL['honey'], intensity=0.6, ratio=0.6, angle=30, seed=4)
        return [(a, o, 'screen', 1), (b, ob, 'screen', 1)]

    def t_dapple(k):
        if k == 'linen':
            a, o = dapple((1100, 1100), seed=5)
            return [(a, o, 'multiply', 1)]
        a, o = dapple((1100, 1100), seed=6, light=True, density=1.2, opacity=0.8)
        return [(a, o, 'screen', 1)]

    def t_field(k):
        if k == 'linen':
            a, o = intensity_field((1100, 1100), n=5, contours=6, seed=9)
            return [(a, o, 'multiply', 1)]
        a, o = intensity_field((1100, 1100), n=5, contours=6, seed=9,
                               ramp=('indigo', 'violet', 'ember', 'amber', 'honey'), contour_color=PAL['linen'],
                               contour_alpha=0.35)
        return [(a, o, 'normal', 1)]

    def t_plan(k):
        L = []
        a, o = view_cone((200, 700), direction=22, fov=58, length=560, color=acc(k))
        L.append((a, o, 'normal', 1))
        a, o = view_cone((820, 980), direction=118, fov=40, length=380, color=ink(k), fill=0.1, edge_dash=(10, 7),
                         apex_ring=0)
        L.append((a, o, 'normal', 1))
        a, o = north_arrow((860, 220), size=170, color=ink(k))
        L.append((a, o, 'normal', 1))
        a, o = north_arrow((620, 200), size=110, angle=-18, color=ink(k), ring=False)
        L.append((a, o, 'normal', 1))
        return L

    def t_lines(k):
        L = []
        a, o = arrow([(80, 160), (420, 90), (760, 170), (1020, 120)], color=ink(k), head='open')
        L.append((a, o, 'normal', 1))
        a, o = arrow([(80, 300), (1020, 300)], color=ink(k), head='filled', width=2.2)
        L.append((a, o, 'normal', 1))
        a, o = arrow([(80, 440), (500, 400), (1020, 470)], color=ink(k), head='half', dash=(12, 8))
        L.append((a, o, 'normal', 1))
        a, o = dotted_path([(80, 760), (300, 600), (560, 820), (780, 640), (1030, 700)], spacing=16, dot_r=2.8,
                           color=acc(k), alpha=(1, 0.2), grow=(1.25, 0.6))
        L.append((a, o, 'normal', 1))
        a, o = ts.leader([(140, 1010), (380, 900), (640, 900)], width=1.8, color=ink(k), dot_at_end=True)
        L.append((a, o, 'normal', 1))
        a, o = ts.leader([(700, 1010), (820, 900), (1020, 900)], width=1.6, color=acc(k), ring_at_end=True,
                         dot_r=9)
        L.append((a, o, 'normal', 1))
        return L

    def t_chips(k):
        L = []
        names = ['honey', 'amber', 'terracotta', 'oxblood', 'sage', 'celadon']
        shapes = ['rect', 'round', 'arch', 'circle', 'rect', 'arch']
        for i, n in enumerate(names):
            a, o = swatch_chip(n, at=(70 + i % 3 * 340, 70 + i // 3 * 360), size=(260, 190), shape=shapes[i],
                               label_color=ink(k), border_color=ink(k))
            L.append((a, o, 'normal', 1))
        rng = np.random.default_rng(3)
        tex = np.clip(C('terracotta')[None, None] * (0.85 + 0.15 * smooth_noise(260, 420, 30, 4, 3)[..., None])
                      + rng.normal(0, 0.012, (260, 420, 1)), 0, 1)
        a, o = swatch_chip(tex, at=(70, 790), size=(420, 200), label='terracotta velvet',
                           sublabel='cabin banquette', label_color=ink(k), border_color=ink(k))
        L.append((a, o, 'normal', 1))
        a, o = swatch_chip('dusk', at=(600, 790), size=(170, 200), shape='arch', label_color=ink(k),
                           border_color=ink(k))
        L.append((a, o, 'normal', 1))
        a, o = swatch_chip('glass', at=(830, 790), size=(170, 200), shape='round', label_color=ink(k),
                           border_color=ink(k))
        L.append((a, o, 'normal', 1))
        return L

    def t_labels(k):
        L = []
        rg, m = ts.label_block('Sound · 01', 'voices rise and soften\nin the void', color=ink(k),
                               label_color=acc(k), phrase_size=64, label_size=28, rule=46)
        L.append((rg, ts.place(m, 150, 190, 'label_baseline'), 'normal', 1))
        rg, m = ts.label_block('Smell · 02', 'beeswax candle · warm sourdough\n· rosemary', color=ink(k),
                               label_color=acc(k), phrase_size=52, label_size=26, phrase_key='italic-medium')
        L.append((rg, ts.place(m, 150, 520, 'label_baseline'), 'normal', 1))
        a, o = ts.leader([(150 + 10, 640), (150 + 10, 700), (420, 760)], width=1.6, color=ink(k), dot_at_end=True)
        L.append((a, o, 'normal', 1))
        rg, m = ts.label_block('Taste', 'red wine, olive oil, sea salt', color=ink(k), label_color=acc(k),
                               phrase_size=46, label_size=24, phrase_key='italic-light', angle=8)
        L.append((rg, ts.place(m, 520, 890, 'label_baseline'), 'normal', 1))
        a, o = scale_bar((150, 1010), px_per_unit=118.11, ticks=(0, 1, 2, 5), color=ink(k), title='scale 1:100',
                         label_size=22)
        L.append((a, o, 'normal', 1))
        return L

    return [
        ('sound_rings', 'full rings · n=8 · decay .82 · wobble .006 · centre dot', t_rings),
        ('sound_rings', 'partial arcs ratio .55 + echo 7 px · dashed set', t_arcs),
        ('waveform', "style='line' (3 strands) · style='bars' — decays to a flat line", t_wave),
        ('wisp', 'curl-noise ribbons · colour graded base -> top', t_wisp),
        ('wisp', 'three thin wisps · turbulence 1.25', t_wisp2),
        ('light_beam', 'aperture 70 · spread 12 · rays · dust motes  (indigo: screen)', t_beam),
        ('glow', 'linen: multiply · indigo: screen with hot core', t_glow),
        ('dapple', 'linen: shadow, multiply · indigo: light=True, screen', t_dapple),
        ('intensity_field', 'warm ramp + 6 isolines · indigo: night ramp', t_field),
        ('view_cone + north_arrow', 'graded wedge, dotted arc, eye point · half-filled needle', t_plan),
        ('arrow · dotted_path · leader', "heads 'open' 'filled' 'half' · fading dots · dot / ring ends", t_lines),
        ('swatch_chip', 'rect / round / arch / circle · texture chip', t_chips),
        ('label_block · scale_bar', 'mono label + italic phrase, rotated 8 deg · 1:100 bar', t_labels),
    ]


def _u8(a):
    return np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8)


def _paste_text(canvas, rgba, x, y):
    """Composite a text RGBA onto a uint8 canvas region (straight over)."""
    h, w = rgba.shape[:2]
    region = canvas[y:y + h, x:x + w].astype(np.float32) / 255
    a = rgba[:region.shape[0], :region.shape[1], 3:4]
    region = region * (1 - a) + rgba[:region.shape[0], :region.shape[1], :3] * a
    canvas[y:y + h, x:x + w] = _u8(region)


def _type_specimen(width, ground_kind='linen'):
    """Type specimen block (float RGB) on linen: every font / weight with sensory phrases."""
    ink = INK if ground_kind == 'linen' else PAL['linen']
    acc = PAL['terracotta'] if ground_kind == 'linen' else PAL['honey']
    rows = [
        ('cg-400i', 'Cormorant Garamond Italic 400', [('voices rise and soften in the void', 132, 0, False)]),
        ('cg-500i', 'Cormorant Garamond Medium Italic 500',
         [('beeswax candle · warm sourdough · rosemary', 84, 0, False)]),
        ('cg-300i', 'Cormorant Garamond Light Italic 300',
         [('sound dims and softens into the linen — “café”, 21 °C …', 64, 0, False)]),
        ('cg-400', 'Cormorant Garamond Regular 400',
         [('01 — FROM THE VOID, LOOKING OUT', 96, 60, True), ('the luminous core → the blue-hour street', 56, 0, False)]),
        ('cg-600', 'Cormorant Garamond SemiBold 600', [('SOUND  SMELL  TASTE  TEXTURE', 160, 50, True)]),
        ('plex-300', 'IBM Plex Mono Light 300', [('01 — From the void, looking out', 40, 120, True),
                                                  ('02 — towards the cabins', 28, 120, True)]),
        ('plex-400', 'IBM Plex Mono Regular 400',
         [('Sound · Smell · Taste · Texture → colour', 36, 100, True)]),
        ('plex-500', 'IBM Plex Mono Medium 500', [('A3 · 4961 × 3508 px · 300 ppi · 1:100', 30, 80, True)]),
    ]
    blocks = []
    for key, name, samples in rows:
        cap, cm = ts.text_rgba(f'{key}  ·  {name}', 'plex-400', 24, acc, tracking=90, uppercase=True)
        cov, cvm = ts.text_rgba('glyphs  · — – ’ ‘ “ ” … é → ← × °', key, 40, ink, tracking=20)
        items = [(cap, cm)]
        for text, size, trk, up in samples:
            items.append(ts.text_rgba(text, key, size, ink, tracking=trk, uppercase=up))
        items.append((cov, cvm))
        blocks.append(items)
    # layout: caption, then samples stacked by their own line heights
    y = 120
    placements = []
    # size waterfall 160 -> 28 px on one baseline, as the words would be set on the collage
    wf = [('SOUND', 'cg-400', 160, 40, True), ('smell', 'cg-400i', 120, 0, False),
          ('TASTE', 'cg-600', 96, 60, True), ('texture', 'cg-500i', 72, 0, False),
          ('SOUND', 'plex-400', 48, 120, True), ('SMELL · TASTE · TEXTURE', 'plex-300', 28, 140, True)]
    cap, cm = ts.text_rgba('size waterfall  ·  160 · 120 · 96 · 72 · 48 · 28 px', 'plex-400', 24, acc,
                           tracking=90, uppercase=True)
    y += int(cm['cap_height'] + 14)
    placements.append((cap, cm, 140, y))
    y += 200
    x = 140
    for text, key, size, trk, up in wf:
        img, m = ts.text_rgba(text, key, size, ink, tracking=trk, uppercase=up)
        placements.append((img, m, x, y))
        x += int(m['width'] + max(50, size * 0.45))
    y += 110
    for items in blocks:
        for i, (img, m) in enumerate(items):
            asc = m['cap_height'] if i == 0 else m['ascender'] * 0.78
            y += int(asc + (14 if i == 0 else 26))
            placements.append((img, m, 140, y))
            y += int(m['descender'] + 10 + m['line_height'] * (len(m['lines']) - 1))
        y += 70
    H = y + 80
    bg = ground(H, width, ground_kind, seed=31)
    for img, m, x, yb in placements:
        px, py = ts.place(m, x, yb)
        composite(bg, img, px, py)
    return bg


def _sensory_labels(width, kind):
    """Annotation set as it would sit on the collage: label blocks with leaders and markers."""
    ink = INK if kind == 'linen' else PAL['linen']
    acc = PAL['terracotta'] if kind == 'linen' else PAL['honey']
    H = 1250
    bg = ground(H, width, kind, seed=41)
    sets = [('SOUND', 'voices rise and soften in the void', 'italic'),
            ('SMELL', 'beeswax candle · warm sourdough · rosemary', 'italic'),
            ('TASTE', 'red wine · olive oil · sea salt', 'italic-medium'),
            ('TEXTURE', 'fluted oak · terracotta velvet · sheer linen', 'italic-light')]
    for i, (lab, ph, key) in enumerate(sets):
        x = 140 + i * (width - 280) // 4
        rg, m = ts.label_block(f'{lab} · 0{i + 1}', ph, label_size=28, phrase_size=58, phrase_key=key,
                               color=ink, label_color=acc, max_width=(width - 280) // 4 - 90, rule=0)
        px, py = ts.place(m, x, 260, 'label_baseline')
        composite(bg, rg, px, py)
        pb = m['anchors']['phrase_last_baseline']
        lx = x + 6
        ly = 260 + (pb[1] - m['anchors']['label_baseline'][1]) + 40
        a, o = ts.leader([(lx, ly), (lx, ly + 220), (lx + 120, ly + 340)], width=1.6, color=ink)
        composite(bg, a, o[0], o[1])
        mk = [lambda: sound_rings((lx + 150, ly + 380), r_max=90, n=4, width=1.8, color=acc, center_dot=4),
              lambda: wisp((lx + 150, ly + 470), height=260, width=22, ribbons=2, color=acc, opacity=0.8, seed=5),
              lambda: glow((lx + 150, ly + 370), radius=90, color=acc, intensity=0.75),
              lambda: swatch_chip('terracotta', at=(lx + 110, ly + 320), size=(110, 80), label=None,
                                  sublabel=None, border_color=ink)][i]()
        composite(bg, mk[0], mk[1][0], mk[1][1], 'normal' if (i != 2 or kind == 'linen') else 'screen')
    t, m = ts.text_rgba('01 — FROM THE VOID, LOOKING OUT', 'cg-400', 72, ink, tracking=60, uppercase=True)
    px, py = ts.place(m, 140, 140)
    composite(bg, t, px, py)
    return bg


def contact_sheet(path=CONTACT, scale=0.5):
    """Render every generator on linen paper and on indigo + the type specimen; saves the
    sheet (downscaled by `scale`) and a few 100 % crops to build/preview/sensory/."""
    tile, gap, margin = 1100, 40, 140
    pair_w = 2 * tile + gap
    Wd = 2 * pair_w + 3 * gap + 2 * margin - gap
    tiles = _tiles()
    rows = (len(tiles) + 1) // 2
    cap_h = 130
    head = 420
    spec_l = _type_specimen(Wd - 2 * margin, 'linen')
    lab_l = _sensory_labels(Wd - 2 * margin, 'linen')
    lab_i = _sensory_labels(Wd - 2 * margin, 'indigo')
    Ht = head + rows * (tile + cap_h + gap) + 200 + spec_l.shape[0] + lab_l.shape[0] + lab_i.shape[0] + 3 * gap + margin
    sheet = np.empty((Ht, Wd, 3), np.uint8)
    sheet[:] = (np.array(C('#E2D8C6')) * 255 + 0.5).astype(np.uint8)
    t, m = ts.text_rgba('Sensory — procedural library', 'italic', 150, INK)
    _paste_text(sheet, t, *ts.place(m, margin, 230))
    t, m = ts.text_rgba('src/lib/sensory.py · src/lib/typeset.py · every generator on linen paper and on '
                        'indigo · tiles 1100 px = 93 mm at 300 ppi', 'plex-300', 30, INK, tracking=80, uppercase=True)
    _paste_text(sheet, t, *ts.place(m, margin, 330))
    crops = {}
    for i, (title, caption, fn) in enumerate(tiles):
        r, c = divmod(i, 2)
        x0 = margin + c * (pair_w + 2 * gap)
        y0 = head + r * (tile + cap_h + gap)
        t, m = ts.text_rgba(f'{i + 1:02d}  {title}', 'plex-500', 30, INK, tracking=60)
        _paste_text(sheet, t, *ts.place(m, x0, y0 + 46))
        t, m = ts.text_rgba(caption, 'plex-300', 24, INK, tracking=40, max_width=pair_w)
        _paste_text(sheet, t, *ts.place(m, x0, y0 + 90))
        for j, kind in enumerate(('linen', 'indigo')):
            bg = ground(tile, tile, kind, seed=50 + i)
            for rgba, (x, y), blend, op in fn(kind):
                composite(bg, rgba, x, y, blend, op)
            sheet[y0 + cap_h:y0 + cap_h + tile, x0 + j * (tile + gap):x0 + j * (tile + gap) + tile] = _u8(bg)
            crops[f'{i + 1:02d}_{title.split()[0]}_{kind}'] = bg
    y = head + rows * (tile + cap_h + gap) + 100
    t, m = ts.text_rgba('Type — Cormorant Garamond + IBM Plex Mono (SIL OFL)', 'italic', 96, INK)
    _paste_text(sheet, t, *ts.place(m, margin, y + 40))
    y += 100
    for blk in (spec_l, lab_l, lab_i):
        sheet[y:y + blk.shape[0], margin:margin + blk.shape[1]] = _u8(blk)
        y += blk.shape[0] + gap
    crops['type_specimen'] = spec_l
    crops['labels_linen'] = lab_l
    crops['labels_indigo'] = lab_i
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im = Image.fromarray(sheet[:y + margin - gap])
    if scale != 1:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    im.save(path, quality=90)
    # previews for inspection (<= 1600 px) and 100 % crops of difficult detail
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    full = Image.fromarray(sheet[:y + margin - gap])
    n_parts = 4
    ph = full.height // n_parts + 1
    for k in range(n_parts):
        part = full.crop((0, k * ph, full.width, min(full.height, (k + 1) * ph)))
        s = 1600 / max(part.size)
        part.resize((round(part.width * s), round(part.height * s)), Image.LANCZOS).save(
            os.path.join(PREVIEW_DIR, f'contact_part{k + 1}.jpg'), quality=88)
    return path, crops


_API_NOTES = {
    'sound_rings': ('concentric sound ripples / partial arcs', 'normal (ink) or screen (light) at 60-100 %'),
    'waveform': ('sound wave along a curve decaying to a flat line', 'normal'),
    'wisp': ('rising aroma / smoke ribbons', 'normal or screen over photos; soft light for subtle'),
    'light_beam': ('volumetric light shaft with rays + dust', 'screen / linear dodge over photos, normal on paper'),
    'glow': ('radial glow, hot core + halation tail', 'screen / linear dodge; multiply for warm stains on paper'),
    'dapple': ('leaf-shadow gobo (or light flecks with light=True)', 'multiply 40-70 % (shadow) / screen (light)'),
    'intensity_field': ('smooth multi-blob intensity zones -> colour ramp (+ isolines, + field for masks)',
                        'multiply / soft light / color; return_field=True -> layer mask'),
    'view_cone': ('plan view cone marker', 'normal'),
    'north_arrow': ('plan north point', 'normal'),
    'arrow': ('hairline arrow', 'normal'),
    'dotted_path': ('dots along a smooth path (movement, scent trail)', 'normal'),
    'swatch_chip': ('colour / texture chip with mono label', 'normal'),
    'scale_bar': ('architectural scale bar', 'normal'),
    'paper': ('opaque linen paper ground (RGB)', 'background'),
}


def write_api_index():
    """Add the generator API (signatures, purpose, suggested blend) to assets/fonts/index.json."""
    import inspect
    import json
    p = os.path.join(ts.FONT_DIR, 'index.json')
    with open(p) as fh:
        idx = json.load(fh)
    gens = []
    for name, (purpose, blend) in _API_NOTES.items():
        fn = globals()[name]
        gens.append({'function': f'lib.sensory.{name}{inspect.signature(fn)}', 'purpose': purpose,
                     'returns': '(rgba float32 HxWx4 straight alpha, (x, y) canvas top-left)'
                     if name != 'paper' else 'float32 HxWx3', 'suggested_blend': blend})
    tsf = []
    for name in ('text_rgba', 'label_block', 'leader', 'place', 'measure', 'fill_contours', 'stroke_polyline'):
        fn = getattr(ts, name)
        tsf.append({'function': f'lib.typeset.{name}{inspect.signature(fn)}',
                    'purpose': (fn.__doc__ or '').strip().split('\n')[0]})
    idx['sensory_generators'] = gens
    idx['typeset_functions'] = tsf
    idx['palette'] = PAL
    idx['contact_sheet'] = os.path.relpath(CONTACT, ROOT)
    with open(p, 'w') as fh:
        json.dump(idx, fh, indent=1, ensure_ascii=False)
    return idx


def build():
    """Install the fonts (assets/fonts + index.json) and render build/contact/sensory.jpg."""
    ts.build()
    write_api_index()
    path, crops = contact_sheet()
    for name in ('01_sound_rings_linen', '04_wisp_indigo', '06_light_beam_indigo', '08_dapple_linen',
                 '10_view_cone_linen', '11_arrow_linen', '13_label_block_linen'):
        if name in crops:
            a = crops[name]
            h, w = a.shape[:2]
            Image.fromarray(_u8(a[h // 2 - 400:h // 2 + 400, w // 2 - 400:w // 2 + 400])).save(
                os.path.join(PREVIEW_DIR, f'crop100_{name}.png'))
    sp = crops['type_specimen']
    Image.fromarray(_u8(sp[:800, :1600])).save(os.path.join(PREVIEW_DIR, 'crop100_type_specimen.png'))
    return path


if __name__ == '__main__':
    print(build())
