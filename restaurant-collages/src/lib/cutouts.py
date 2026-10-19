"""cutouts — photographic cut-outs (RGBA, native resolution) from the AI source photos.

Outputs go to ROOT/assets/cut/ (+ index.json); the contact sheet to ROOT/build/contact/cutouts.jpg.
`assets/cut/geo/` belongs to another area and is never touched here.

Matting toolkit (all float32, 0..1, straight alpha):

* ``nfill``            multi-scale normalised-convolution fill: extrapolate the colours of a known
                       region into the unknown one (clean background plates / foreground colour)
* ``project_alpha``    alpha = projection of (I - B) onto (F - B)
* ``decontaminate``    foreground colour by inverting the over-operator where alpha is reliable,
                       the local F estimate where it is small (no light/dark fringe)
* ``roi_matte``        difference matte of an object inside a region of interest
* ``refine_band``      polygon/mask used as a trimap: projection matte in a narrow band
* ``trace_outline``    polar dynamic-programming silhouette trace (optionally around an ellipse
                       prior) with sub-pixel refinement
* ``poly_alpha``       anti-aliased polygon alpha (4x supersampled)
* ``cord_geometry`` / ``cord_width`` / ``tube_alpha``  thin pendant cords
* ``robust_polyfit`` / ``robust_ellipse``  outlier-robust model fits for clean geometric edges
* ``grabcut_refine``   GrabCut from a rough outline
* ``trim`` / ``save_rgba`` / ``triple`` / ``contact_sheet``  output + inspection

``build()`` regenerates every asset + index.json + contact sheet deterministically.
"""
from __future__ import annotations

import json
import os

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GEN = os.path.join(ROOT, 'assets', 'gen')
OUT = os.path.join(ROOT, 'assets', 'cut')
SCRATCH = os.path.join(ROOT, 'build', 'cutouts')
PREV = os.path.join(ROOT, 'build', 'preview', 'cutouts')
CONTACT = os.path.join(ROOT, 'build', 'contact', 'cutouts.jpg')

INK = (0x2B / 255, 0x24 / 255, 0x20 / 255)
BGS = {'linen': '#EFE6D6', 'grey': '#808080', 'indigo': '#262C45'}


def P(*parts):
    return os.path.join(ROOT, *parts)


def hexf(c):
    c = c.lstrip('#')
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


# --------------------------------------------------------------------------- #
# io
# --------------------------------------------------------------------------- #

def load_src(name, box=None):
    """Load an assets/gen photo as float32 RGB 0..1, optionally cropped to box=(x0,y0,x1,y1)."""
    im = Image.open(os.path.join(GEN, name)).convert('RGB')
    if box is not None:
        im = im.crop(tuple(int(v) for v in box))
    return np.asarray(im, np.float32) / 255.0


def lum(img):
    return 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]


def to_u8(x):
    return np.clip(np.asarray(x, np.float32) * 255.0 + 0.5, 0, 255).astype(np.uint8)


def save_rgba(path, rgb, alpha):
    """Write an 8-bit straight-alpha RGBA PNG. RGB under (near) zero alpha is filled with the
    nearest foreground colour so that later resampling never pulls in a dark/light fringe."""
    a8 = to_u8(alpha)
    rgb = np.asarray(rgb, np.float32)
    known = a8 > 0
    if (~known).any() and known.any():
        _, (iy, ix) = ndi.distance_transform_edt(~known, return_indices=True)
        rgb = rgb[iy, ix]
    out = np.dstack([to_u8(rgb), a8])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(out, 'RGBA').save(path, optimize=False, compress_level=6)
    return path


def save_preview(img, path, max_side=1600, quality=90):
    a = np.asarray(img)
    if a.dtype != np.uint8:
        a = to_u8(a)
    im = Image.fromarray(a)
    s = max_side / max(im.size)
    if s < 1:
        im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.convert('RGB').save(path, quality=quality)
    return path


# --------------------------------------------------------------------------- #
# filtering / fills
# --------------------------------------------------------------------------- #

def gblur(x, sigma):
    """Gaussian blur; sigmas > 6 px run on a downsampled copy (fast, memory-light)."""
    x = np.asarray(x, np.float32)
    if sigma <= 0:
        return x
    if sigma <= 6:
        return cv2.GaussianBlur(x, (0, 0), sigma, borderType=cv2.BORDER_REFLECT)
    f = int(max(1, sigma // 3))
    h, w = x.shape[:2]
    sw, sh = max(1, w // f), max(1, h // f)
    small = cv2.resize(x, (sw, sh), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), sigma / f, borderType=cv2.BORDER_REFLECT)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


def nfill(img, known, sigmas=(2, 4, 8, 16, 32, 64), wmin=0.02):
    """Normalised-convolution fill. Returns an image equal to `img` on `known` and, elsewhere,
    the Gaussian-weighted mean of known pixels at the smallest scale that has support
    (scales are blended smoothly, so no seams)."""
    img = np.asarray(img, np.float32)
    k = np.asarray(known, np.float32)
    multi = img.ndim == 3
    out = np.zeros_like(img)
    acc = np.zeros(k.shape, np.float32)  # how much of the pixel is already decided
    kk = k[..., None] if multi else k
    for s in sigmas:
        w = gblur(k, s)
        v = gblur(img * kk, s)
        est = v / np.maximum(w, 1e-6)[..., None] if multi else v / np.maximum(w, 1e-6)
        take = np.clip((w - wmin) / (4 * wmin), 0, 1) * (1 - acc)
        out += est * (take[..., None] if multi else take)
        acc += take
    if (acc < 0.999).any():  # global mean for anything still unresolved
        m = (img * kk).reshape(-1, img.shape[-1] if multi else 1).sum(0) / max(k.sum(), 1)
        rest = 1 - acc
        out += (m[None, None, :] * rest[..., None]) if multi else m[0] * rest
    return np.where(kk > 0.5, img, out)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def disk(r):
    r = int(r)
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def dilate(m, r):
    return cv2.dilate(m.astype(np.uint8), disk(r)) > 0 if r > 0 else m.astype(bool)


def erode(m, r):
    return cv2.erode(m.astype(np.uint8), disk(r)) > 0 if r > 0 else m.astype(bool)


def keep_connected(seed, region):
    """Pixels of `region` connected (8-conn.) to any `seed` pixel."""
    region = region.astype(np.uint8)
    n, lab = cv2.connectedComponents(region, connectivity=8)
    good = np.unique(lab[seed.astype(bool) & (region > 0)])
    good = good[good > 0]
    return np.isin(lab, good)


def geodesic_grow(seed, region, steps):
    """Grow `seed` through `region` by at most `steps` pixels (8-connected)."""
    cur = seed.astype(np.uint8)
    reg = region.astype(np.uint8) | cur
    k = np.ones((3, 3), np.uint8)
    for _ in range(int(steps)):
        nxt = cv2.dilate(cur, k) & reg
        if (nxt == cur).all():
            break
        cur = nxt
    return cur > 0


def fill_holes_smaller(mask, max_area):
    """Fill holes of `mask` whose area <= max_area (keeps real gaps)."""
    inv = (~mask.astype(bool)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    out = mask.astype(bool).copy()
    h, w = mask.shape
    for i in range(1, n):
        x, y, ww, hh, a = st[i]
        touches = x == 0 or y == 0 or x + ww == w or y + hh == h
        if a <= max_area and not touches:
            out |= lab == i
    return out


# --------------------------------------------------------------------------- #
# matting
# --------------------------------------------------------------------------- #

def project_alpha(I, F, B, floor=0.03):
    """alpha = <I-B, F-B> / |F-B|^2, clipped. `floor` = minimum |F-B| (avoid blow-ups)."""
    d = F - B
    n2 = np.maximum((d * d).sum(-1), floor * floor)
    return np.clip(((I - B) * d).sum(-1) / n2, 0, 1)


def decontaminate(I, alpha, B, F_est, lo=0.12, hi=0.55):
    """Foreground colour: exact over-operator inversion where alpha is reliable, the smooth
    local foreground estimate where it is not (kills light/dark fringes)."""
    a = alpha[..., None]
    inv = (I - (1 - a) * B) / np.maximum(a, 1e-3)
    inv = np.clip(inv, 0, 1)
    w = smoothstep(lo, hi, alpha)[..., None]
    return inv * w + F_est * (1 - w)


def refine_band(I, a_poly, band=7, lo=0.12, hi=0.6, min_contrast=0.0):
    """Use an anti-aliased polygon as a trimap: inside/outside known beyond +-band px, and in
    the band alpha = projection of I onto the local fg/bg colour line (nfill estimates);
    colours decontaminated. Returns alpha, rgb."""
    m = a_poly > 0.5
    fg = erode(m, band)
    bg = ~dilate(m, band)
    F = nfill(I, fg, (2, 4, 8, 16))
    B = nfill(I, bg, (2, 4, 8, 16))
    a = project_alpha(I, F, B, floor=0.08)
    a = cv2.GaussianBlur(a, (0, 0), 0.5)
    if min_contrast:  # only trust the projection where fg and bg colours really differ
        con = np.sqrt(((F - B) ** 2).sum(-1))
        t = smoothstep(min_contrast * 0.7, min_contrast * 1.3, con)
        a = a * t + a_poly * (1 - t)
    inb = ~fg & ~bg
    alpha = np.where(inb, a, a_poly).astype(np.float32)
    alpha = np.where(fg, 1.0, np.where(bg, 0.0, alpha)).astype(np.float32)
    rgb = decontaminate(I, alpha, B, F, lo, hi)
    rgb = np.where(fg[..., None], I, rgb)
    return alpha, rgb


def poly_alpha(points, h, w, ss=4):
    """Anti-aliased polygon alpha (float32) with sub-pixel vertex precision."""
    m = np.zeros((h * ss, w * ss), np.uint8)
    pts = np.round((np.asarray(points, np.float64) + 0.5) * ss - 0.5).astype(np.int32)
    cv2.fillPoly(m, [pts], 255, lineType=cv2.LINE_8)
    return cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0


def ellipse_pts(cx, cy, rx, ry, a0=0, a1=360, n=180, rot=0.0):
    t = np.radians(np.linspace(a0, a1, n))
    c, s = np.cos(np.radians(rot)), np.sin(np.radians(rot))
    x, y = rx * np.cos(t), ry * np.sin(t)
    return np.stack([cx + x * c - y * s, cy + x * s + y * c], 1)


# --------------------------------------------------------------------------- #
# trimming / compositing
# --------------------------------------------------------------------------- #

def trim(alpha, margin=4, thresh=1 / 255):
    ys, xs = np.nonzero(alpha > thresh)
    h, w = alpha.shape
    x0, y0 = max(0, xs.min() - margin), max(0, ys.min() - margin)
    x1, y1 = min(w, xs.max() + 1 + margin), min(h, ys.max() + 1 + margin)
    return x0, y0, x1, y1


def over(rgb, alpha, bg):
    bg = hexf(bg) if isinstance(bg, str) else np.asarray(bg, np.float32)
    a = alpha[..., None]
    return rgb * a + bg * (1 - a)


def load_cut(path):
    im = np.asarray(Image.open(path).convert('RGBA'), np.float32) / 255.0
    return im[..., :3], im[..., 3]


# --------------------------------------------------------------------------- #
# 1. diners silhouettes
# --------------------------------------------------------------------------- #

DINER_GROUPS = [  # (name, x-range of component centroids in source px, description)
    ('fig_couple_table', (0, 1000), 'seated couple at a bistro table with two red-wine glasses, '
                                     'plate, bentwood chairs both sides'),
    ('fig_waiter', (1000, 1450), 'walking waiter in waistcoat and apron carrying a tray'),
    ('fig_standing_pair', (1450, 2050), 'standing couple laughing, each holding a red-wine glass'),
    ('fig_woman_coffee', (2050, 2736), 'woman seated alone at a bistro table with a coffee cup, '
                                       'bentwood chair'),
]


def matte_diners(I):
    """Soft luminance/colour key of dark figures on the near-white studio background.
    Returns alpha, decontaminated rgb, group-label map (index into DINER_GROUPS, -1 = none)."""
    L = I.mean(2)
    h, w = L.shape
    dark = L < 0.85
    bgk = (L > 0.9) & ~dilate(dark, 8)
    B = nfill(I, bgk, (8, 16, 32, 64, 128))
    BL = B.mean(2)
    core = L < BL - 0.45                              # ~ L < 0.5 : definite figure
    # drop isolated specks (dust) further than 40 px from a real figure
    n, lab, st, cen = cv2.connectedComponentsWithStats(core.astype(np.uint8), connectivity=8)
    big = np.zeros(n, bool)
    big[1:] = st[1:, 4] > 50000
    bigmask = big[lab]
    near = dilate(bigmask, 40)
    small_ok = np.unique(lab[near & core & ~bigmask])
    keep = big.copy()
    keep[small_ok] = True
    keep[0] = False
    core0 = keep[lab]
    # alpha is forced to 1 only 2 px inside the dark region: the outer ring (upscaling/sharpening
    # transition, mixed with the white ground) is solved by projection, otherwise it would keep
    # its bg-contaminated light grey and draw a pale rim on dark grounds.
    core = erode(core0, 2)
    F = nfill(I, core, (1.5, 3, 6, 12, 24))
    a_raw = project_alpha(I, F, B)
    a_raw = np.clip((a_raw - 0.008) / 0.992, 0, 1)    # noise floor (bg sigma ~0.0027)
    # support: grow from the core through soft pixels (hair strands, glass stems, rims) but only
    # 2 px on the floor strip where soft pixels are contact shadows, not figure.
    floor = np.zeros_like(core)
    floor[1150:] = True
    soft = a_raw > 0.10
    far = geodesic_grow(core0, soft, 18)
    nearg = geodesic_grow(core0, soft, 2)
    sup = np.where(floor, nearg, far)
    sup = dilate(sup, 1)
    alpha = np.where(core, 1.0, a_raw * sup).astype(np.float32)
    rgb = decontaminate(I, alpha, B, F)
    rgb = np.where(core[..., None], I, rgb)
    # group assignment: nearest big figure component, groups by centroid x
    dists = []
    for gi, (_, (xa, xb), _) in enumerate(DINER_GROUPS):
        ids = [i for i in range(1, n) if big[i] and xa <= cen[i][0] < xb]
        gmask = np.isin(lab, ids)
        dists.append(cv2.distanceTransform((~gmask).astype(np.uint8), cv2.DIST_L2, 5))
    del lab
    dists = np.stack(dists, 0)
    group = np.argmin(dists, 0).astype(np.int8)
    group[alpha <= 0] = -1
    return alpha, rgb, group


def cut_diners(outdir=OUT, margin=4):
    I = load_src('diners_silhouettes.png')
    alpha, rgb, group = matte_diners(I)
    entries = []
    for gi, (name, _, desc) in enumerate(DINER_GROUPS):
        a = np.where(group == gi, alpha, 0).astype(np.float32)
        x0, y0, x1, y1 = trim(a, margin)
        ac, rc = a[y0:y1, x0:x1], rgb[y0:y1, x0:x1]
        save_rgba(os.path.join(outdir, name + '.png'), rc, ac)
        flat = np.broadcast_to(np.array(INK, np.float32), rc.shape)
        save_rgba(os.path.join(outdir, name + '_flat.png'), flat, ac)
        ys, xs = np.nonzero(ac > 0.5)
        entries.append(dict(name=name, desc=desc, size=[x1 - x0, y1 - y0], src_box=[x0, y0, x1, y1],
                            ground_y=int(ys.max()), x_extent=[int(xs.min()), int(xs.max())]))
    return entries


# --------------------------------------------------------------------------- #
# inspection
# --------------------------------------------------------------------------- #

def triple(rgb, alpha, scale=1.0, gap=8):
    """The cut-out composited over linen | grey | indigo, side by side (float RGB)."""
    if scale != 1.0:
        h, w = alpha.shape
        size = (max(1, round(w * scale)), max(1, round(h * scale)))
        pm = cv2.resize(rgb * alpha[..., None], size, interpolation=cv2.INTER_AREA)
        alpha = cv2.resize(alpha, size, interpolation=cv2.INTER_AREA)
        rgb = pm / np.maximum(alpha[..., None], 1e-5)
    panels = [over(rgb, alpha, c) for c in BGS.values()]
    h = alpha.shape[0]
    g = np.ones((h, gap, 3), np.float32)
    out = []
    for p in panels:
        out += [p, g]
    return np.concatenate(out[:-1], 1)


def crop_check(path, box, out, scale=1.0):
    rgb, a = load_cut(path)
    x0, y0, x1, y1 = box
    save_preview(triple(rgb[y0:y1, x0:x1], a[y0:y1, x0:x1], scale), out, max_side=2400)


def roi_matte(I, roi, seed, t_core=0.22, band_px=3, core_erode=1,
              B_sigmas=(2, 4, 8, 16, 32, 64), F_sigmas=(1.5, 3, 6, 12, 24)):
    """Generic difference matte inside a region of interest.

    The clean background plate B is extrapolated (normalised convolution) from everything OUTSIDE
    `roi`; pixels inside whose colour distance |I-B| > t_core and that are connected to `seed`
    form the core; alpha = projection of I-B onto F-B within `band_px` of the core.
    Returns alpha, rgb, core0 (undilated core)."""
    B = nfill(I, ~roi, B_sigmas)
    D = np.sqrt(((I - B) ** 2).sum(-1))
    core0 = keep_connected(seed, (D > t_core) & roi)
    core0 = fill_holes_smaller(core0, 400)
    band = dilate(core0, band_px) & roi
    core = erode(core0, core_erode) if core_erode else core0
    F = nfill(I, core, F_sigmas)
    a = project_alpha(I, F, B, floor=0.06) * band
    a = np.where(core, 1.0, a).astype(np.float32)
    rgb = decontaminate(I, a, B, F)
    rgb = np.where(core[..., None], I, rgb)
    return a, rgb, core0, B


# --------------------------------------------------------------------------- #
# 2. pendants
# --------------------------------------------------------------------------- #

def fit_ellipse_axis(pts):
    """Least-squares axis-aligned ellipse A x^2 + C y^2 + D x + E y = 1 -> (cx, cy, rx, ry)."""
    x, y = pts[:, 0].astype(np.float64), pts[:, 1].astype(np.float64)
    mx, my = x.mean(), y.mean()
    x, y = x - mx, y - my
    M = np.stack([x * x, y * y, x, y], 1)
    A, C, D, E = np.linalg.lstsq(M, np.ones_like(x), rcond=None)[0]
    cx, cy = -D / (2 * A), -E / (2 * C)
    k = 1 + A * cx * cx + C * cy * cy
    return cx + mx, cy + my, float(np.sqrt(k / A)), float(np.sqrt(k / C))


def _bulb(I, B, rim_y, cx, box_w=150, box_h=140, t=0.2):
    """Glass bulb hanging under a shade rim: segment by colour distance to the wall plate (the
    component under the axis), fit an axis-aligned ellipse to its lower outline + rim corners and
    return its anti-aliased alpha clipped to below the rim, plus the parameters."""
    h, w = I.shape[:2]
    x0, x1 = int(cx - box_w), int(cx + box_w)
    y0, y1 = int(np.ceil(rim_y)), int(min(h, rim_y + box_h))
    for it in range(3):  # segment, re-estimate the wall plate right around the blob, repeat
        D = np.sqrt(((I - B) ** 2).sum(-1))
        m = np.zeros((h, w), np.uint8)
        m[y0:y1, x0:x1] = D[y0:y1, x0:x1] > t
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, disk(3))
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, disk(2))
        m[y0:y0 + 3] = 0  # do not let the blob leak along the brim's anti-aliased lower edge
        n, lab = cv2.connectedComponents(m, connectivity=8)
        seedrow = lab[y0 + 3, int(cx) - 20:int(cx) + 21]
        ids, cnt = np.unique(seedrow[seedrow > 0], return_counts=True)
        blob = lab == ids[np.argmax(cnt)]
        blob = fill_holes_smaller(blob, 10 ** 6)
        if it < 2:
            known = np.zeros((h, w), bool)
            known[y0 + 4:y1 + 40, x0 - 40:x1 + 40] = True
            known &= ~dilate(blob, 5)
            B = nfill(I, known, (3, 6, 12, 24, 48))
    ys, xs = np.nonzero(blob)
    pts = []
    for x in range(xs.min() + 2, xs.max() - 1):   # lower outline
        col = ys[xs == x]
        if len(col) and col.max() > y0 + 8:
            pts.append((x, col.max() + 0.5))
    for y in range(y0 + 3, y0 + 12):              # side extents just under the brim
        row = xs[ys == y]
        if len(row):
            pts += [(row.min() - 0.5, y), (row.max() + 0.5, y)]
    ex, ey, rx, ry = fit_ellipse_axis(np.array(pts, np.float64))
    a = poly_alpha(ellipse_pts(ex, ey, rx, ry, n=360), h, w)
    a[:y0] = 0
    return a, dict(cx=float(ex), cy=float(ey), rx=rx, ry=ry, angle=0.0)


def _crossings(a_row, lo, hi, thr=0.5):
    """Sub-pixel positions of the outermost alpha=thr crossings of a 1-D profile in [lo, hi)."""
    lo, hi = max(0, int(lo)), min(len(a_row), int(hi))
    r = a_row[lo:hi]
    idx = np.nonzero(r >= thr)[0]
    if not len(idx):
        return None
    i0, i1 = idx[0], idx[-1]
    def interp(i, j):  # crossing between samples i (below) and j (above)
        ai, aj = r[i], r[j]
        return i + (thr - ai) / max(aj - ai, 1e-6) * (j - i)
    xl = interp(i0 - 1, i0) if i0 > 0 else float(i0)
    xr = interp(i1 + 1, i1) if i1 < len(r) - 1 else float(i1)
    return lo + xl, lo + xr


def cord_geometry(alpha, y0, y1, x_guess, search=30, deg=2):
    """Fit the centre line x(y) (polynomial) and per-row width (alpha-sum, median-smoothed) of a
    near-vertical cord between rows y0..y1. Returns (poly coeffs, widths array indexed y-y0)."""
    ys, xc, wd = [], [], []
    x = x_guess
    for y in range(int(y0), int(y1)):
        lo, hi = int(max(0, x - search)), int(min(alpha.shape[1], x + search))
        r = alpha[y, lo:hi]
        s = r.sum()
        if s < 2:
            continue
        cx = lo + (r * np.arange(len(r))).sum() / s
        ys.append(y); xc.append(cx); wd.append(s)
        x = cx
    ys, xc, wd = map(np.asarray, (ys, xc, wd))
    coef = np.polyfit(ys, xc, deg)
    for _ in range(3):  # robust refit
        res = np.abs(np.polyval(coef, ys) - xc)
        ok = res < max(1.0, 2.5 * np.median(res))
        coef = np.polyfit(ys[ok], xc[ok], deg)
    width = np.interp(np.arange(int(y0), int(y1)), ys, wd)
    width = ndi.median_filter(width, size=9, mode='nearest')
    return coef, width


def cord_width(L, coef, y0, y1, dark=0.15, search=20):
    """Robust per-row cord width from its dark core (count of L<dark pixels near the centre
    line): short median keeps real steps (sleeves), a long 75th-percentile window bridges rows
    where the cord is rim-lit and lighter."""
    h, w = L.shape
    xs = np.arange(w)
    out = []
    for y in range(int(y0), int(y1)):
        xc = np.polyval(coef, y)
        m = (np.abs(xs - xc) <= search) & (L[y] < dark)
        out.append(m.sum())
    out = np.asarray(out, np.float32)
    short = ndi.median_filter(out, size=9, mode='nearest')
    long = ndi.percentile_filter(out, 75, size=201, mode='nearest')
    return np.maximum(short, long)


def tube_alpha(h, w, coef, width, y0, pad=1.0):
    """Soft (1 px ramp) tube around a cord centre line: 1 inside |x-xc|<=width/2+pad."""
    t = np.zeros((h, w), np.float32)
    xs = np.arange(w, dtype=np.float32)
    for k, y in enumerate(range(int(y0), int(y0) + len(width))):
        xc = np.polyval(coef, y)
        t[y] = np.clip(width[k] / 2 + pad + 0.5 - np.abs(xs - xc), 0, 1)
    return t


def symmetric_profile(alpha, y0, y1, x_lo, x_hi, axis=None, med=5):
    """Half-width profile of a rotationally symmetric object (lamp shade) seen side-on:
    per row the outer alpha=0.5 crossings; the axis is the median mid-point; r(y) is the larger of
    the two half widths (robust to reflections biting into one side), median filtered.
    Returns (axis, ys, r)."""
    ys, xl, xr = [], [], []
    for y in range(int(y0), int(y1)):
        c = _crossings(alpha[y], int(x_lo), int(x_hi))
        if c is None:
            continue
        ys.append(y); xl.append(c[0]); xr.append(c[1])
    ys, xl, xr = map(np.asarray, (ys, xl, xr))
    if axis is None:
        axis = float(np.median((xl + xr) / 2))
    r = np.maximum(axis - xl, xr - axis)
    r = ndi.median_filter(r, size=med, mode='nearest')
    return axis, ys, r


def contour_alpha(a, y0, y1, axis=None, level=0.5):
    """Clean anti-aliased silhouette of the largest object in rows y0..y1 of a (noisy, holey)
    matte: sub-pixel iso-contour at `level` -> filled polygon. With `axis`, the silhouette is
    unioned with its mirror image (rotationally symmetric objects: fills reflection notches)."""
    from skimage import measure
    h, w = a.shape
    sub = np.zeros((h + 2, w + 2), np.float32)
    sub[1 + y0:1 + y1, 1:-1] = cv2.GaussianBlur(a, (0, 0), 0.7)[y0:y1]
    best, area = None, 0
    for c in measure.find_contours(sub, level):
        if len(c) < 20:
            continue
        x, y = c[:, 1] - 1, c[:, 0] - 1
        ar = 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
        if ar > area:
            best, area = np.stack([x, y], 1), ar
    out = poly_alpha(best, h, w)
    if axis is not None:
        M = np.float32([[-1, 0, 2 * axis], [0, 1, 0]])
        mir = cv2.warpAffine(out, M, (w, h), flags=cv2.INTER_LINEAR)
        out = np.maximum(out, mir)
    return out


def cut_pendant_festoon(side):
    """Black dome pendant with its cord to the top edge from festoon_valance.png ('L' or 'R')."""
    box = {'L': (1250, 0, 1900, 1990), 'R': (4430, 0, 5090, 1990)}[side]
    I = load_src('festoon_valance.png', box)
    L = lum(I)
    h, w = L.shape
    d = (L < 0.2).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(d, connectivity=8)
    i = 1 + int(np.argmax(st[1:, 4]))
    rough = lab == i
    # ceiling canopy (brown disc cut by the top edge, left pendant only)
    top = 24
    wall = np.median(I[:top], axis=1, keepdims=True)
    dtop = np.sqrt(((I[:top] - wall) ** 2).sum(-1)) > 0.12
    can = np.zeros_like(rough)
    can[:top] = dtop
    rough = keep_connected(rough, rough | can)
    widths = (rough & (L < 0.2)).sum(1)
    cord_w = np.median(widths[200:1200])
    wide = ndi.minimum_filter1d((widths > 1.6 * cord_w).astype(np.uint8), 15, origin=-7)
    neck = int(np.nonzero(wide[60:])[0][0]) + 60                # top of the shade cap
    # the shade's lit shoulders are dark grey, not black: grow the shade part of the ROI through
    # L < 0.42 so the background plate is never extrapolated from the shade itself
    shade_rough = keep_connected(rough, L < 0.42)
    shade_rough[:neck - 10] = False
    roi = dilate(rough, 9) | dilate(shade_rough, 10)
    a_m, rgb_m, core0, B = roi_matte(I, roi, rough, t_core=0.2)
    rim_y = int(np.nonzero(core0.sum(1) > 300)[0].max()) + 1    # first row below the brim
    xs_rim = np.nonzero(core0[rim_y - 1])[0]
    cx0 = 0.5 * (xs_rim.min() + xs_rim.max())
    can_rows = np.nonzero(core0[:40].sum(1) > 3 * cord_w)[0]
    can_y = int(can_rows.max()) + 1 if len(can_rows) else 0     # canopy rows (left pendant)

    # cord: fitted centre line + per-row width -> tube that clips the projection matte
    xg = float(np.mean(np.nonzero(core0[min(300, neck - 1)])[0]))
    coef, _ = cord_geometry(a_m, can_y, neck + 3, xg)
    wid = cord_width(L, coef, can_y, neck + 3)
    tube = tube_alpha(h, w, coef, wid, can_y, pad=1.5)
    a_cord = np.minimum(a_m, tube)
    a_cord[neck + 3:] = 0
    # canopy rows: keep the matte as is
    a_can = np.zeros_like(a_m)
    a_can[:can_y + 2] = a_m[:can_y + 2]
    # shade: symmetric profile polygon
    axis, ys, r = symmetric_profile(a_m, neck, rim_y, cx0 - 320, cx0 + 320)
    # brim underside: vertical crossing just outside the bulb, averaged
    cols = [int(axis - r[-1] + 12), int(axis - r[-1] + 40), int(axis + r[-1] - 40), int(axis + r[-1] - 12)]
    yb = []
    for c in cols:
        col = a_m[rim_y - 12:rim_y + 8, c]
        j = np.nonzero(col >= 0.5)[0].max()
        if j + 1 < len(col):
            yb.append(rim_y - 12 + j + (col[j] - 0.5) / max(col[j] - col[j + 1], 1e-6))
    y_bot = float(np.median(yb)) if yb else rim_y - 0.5
    a_shade = contour_alpha(a_m, neck, int(np.ceil(y_bot)) + 2)
    a_shade[int(np.ceil(y_bot)) + 1:] = 0
    F_sh = nfill(I, erode(a_shade > 0.99, 2) & (L < 0.35), (1.5, 3, 6, 12))
    # bulb (plate rebuilt without the bulb area)
    broi = roi.copy()
    broi[rim_y:rim_y + 150, int(axis - 160):int(axis + 160)] = True
    Bb = nfill(I, ~broi, (4, 8, 16, 32, 64))
    a_bulb, ell = _bulb(I, Bb, y_bot, axis)
    bulb_rgb = nfill(I, erode(a_bulb > 0.99, 2), (1.5, 3, 6))

    alpha = np.maximum.reduce([a_cord, a_can, a_shade, a_bulb])
    rgb = rgb_m.copy()
    sh_rgb = decontaminate(I, a_shade, B, F_sh)
    sh_rgb = np.where((a_shade > 0.999)[..., None], I, sh_rgb)
    rgb = np.where((a_shade >= np.maximum(a_cord, a_can))[..., None] & (a_shade > 0)[..., None], sh_rgb, rgb)
    rgb = np.where((a_bulb > a_shade)[..., None], bulb_rgb, rgb)

    x0, y0, x1, y1 = trim(alpha, 4)
    y0 = 0  # cord runs off the top edge: keep it flush
    a, c = alpha[y0:y1, x0:x1], rgb[y0:y1, x0:x1]
    name = f'pendant_valance_{side}'
    save_rgba(os.path.join(OUT, name + '.png'), c, a)
    return dict(name=name, size=[int(x1 - x0), int(y1 - y0)],
                src_box=[int(box[0] + x0), 0, int(box[0] + x1), int(y1)],
                cord_top=[round(float(np.polyval(coef, 0)) - x0, 1), 0],
                shade_axis_x=round(axis - x0, 1), shade_top_y=neck, brim_y=round(y_bot, 1),
                shade_half_width=round(float(r[-1]), 1),
                bulb=dict(cx=round(ell['cx'] - x0, 1), cy=round(ell['cy'], 1),
                          rx=round(ell['rx'], 1), ry=round(ell['ry'], 1)))


def lab_image(I, sigma=1.0):
    """CIE Lab (L 0..100) of a float RGB image, lightly smoothed."""
    lab = cv2.cvtColor(np.ascontiguousarray(I, np.float32), cv2.COLOR_RGB2LAB)
    return cv2.GaussianBlur(lab, (0, 0), sigma) if sigma else lab


def polar_points(cx, cy, th_deg, r):
    th = np.radians(np.asarray(th_deg, np.float64))
    return np.stack([cx + np.cos(th) * r, cy + np.sin(th) * r], 1)


def polar_sample(img, cx, cy, th_deg, rs):
    th = np.radians(np.asarray(th_deg, np.float64))
    X = (cx + np.cos(th)[:, None] * rs[None, :]).astype(np.float32)
    Y = (cy + np.sin(th)[:, None] * rs[None, :]).astype(np.float32)
    return cv2.remap(np.ascontiguousarray(img, np.float32), X, Y, cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REPLICATE)


def window_contrast(P, win=10, gap=1):
    """Per (ray, r): mean(P[r+gap : r+gap+win]) - mean(P[r-gap-win : r-gap]) — 'outside minus
    inside' contrast of a scalar feature along each ray (edge test robust to thin stripes)."""
    n, m = P.shape
    cs = np.concatenate([np.zeros((n, 1), np.float32), np.cumsum(P, 1, dtype=np.float64)], 1)
    j = np.arange(m)
    def mean(a, b):
        a, b = np.clip(a, 0, m), np.clip(b, 0, m)
        return (cs[:, b] - cs[:, a]) / np.maximum(b - a, 1)
    out = (mean(j + gap, j + gap + win) - mean(j - gap - win, j - gap)).astype(np.float32)
    e = win + gap
    out[:, :e] = -1e3   # windows not fully inside the band are invalid
    out[:, m - e:] = -1e3
    return out


def dp_path(score, max_step=1, init=None):
    """Maximum-score path through score[n, m] (one column per row) with |dj| <= max_step."""
    n, m = score.shape
    k = int(max_step)
    acc = score[0].copy() if init is None else score[0] + init
    back = np.zeros((n, m), np.int32)
    idx = np.arange(m)
    for i in range(1, n):
        best = np.full(m, -1e18)
        arg = np.zeros(m, np.int32)
        for s in range(-k, k + 1):
            sh = np.full(m, -1e18)
            if s >= 0:
                sh[s:] = acc[:m - s]
            else:
                sh[:s] = acc[-s:]
            better = sh > best
            best = np.where(better, sh, best)
            arg = np.where(better, idx - s, arg)
        acc = best + score[i]
        back[i] = arg
    j = int(np.argmax(acc))
    path = np.zeros(n, np.int32)
    for i in range(n - 1, -1, -1):
        path[i] = j
        j = back[i, j]
    return path


def subpixel_edge(P, path, rs, level=None):
    """Refine an integer edge path along rays to the sub-pixel crossing of the mid level between
    the inside (path-6..path-2) and outside (path+2..path+6) means of feature P."""
    n, m = P.shape
    out = np.zeros(n, np.float64)
    for i in range(n):
        j = path[i]
        a, b = max(0, j - 6), min(m, j + 7)
        seg = P[i, a:b]
        inside = P[i, max(0, j - 6):max(1, j - 1)].mean()
        outside = P[i, min(m - 1, j + 2):min(m, j + 7)].mean()
        mid = 0.5 * (inside + outside)
        s = np.sign(outside - inside) or 1
        f = (seg - mid) * s
        cross = np.nonzero((f[:-1] < 0) & (f[1:] >= 0))[0]
        if len(cross):
            c = cross[np.argmin(np.abs(cross + a - j))]
            t = -f[c] / (f[c + 1] - f[c] + 1e-9)
            out[i] = rs[0] + a + c + t
        else:
            out[i] = rs[0] + j
    return out


def trace_outline(feat, cx, cy, th_deg, r_lo, r_hi, win=10, max_step=2, sign=+1, med=9, sm=2.0,
                  prior=None):
    """Polar DP silhouette trace on a scalar 'background-ness' feature (outside > inside when
    sign=+1). With prior=(A, Bv) the search band r_lo..r_hi is an OFFSET (px) around the ellipse
    radius of semi-axes A (x) and Bv (y) at each angle. Returns smoothed radii."""
    rs = np.arange(r_lo, r_hi, 1.0)
    th = np.radians(np.asarray(th_deg, np.float64))
    base = np.zeros(len(th))
    if prior is not None:
        A, Bv = prior
        base = 1.0 / np.sqrt((np.cos(th) / A) ** 2 + (np.sin(th) / Bv) ** 2)
    X = (cx + np.cos(th)[:, None] * (base[:, None] + rs[None, :])).astype(np.float32)
    Y = (cy + np.sin(th)[:, None] * (base[:, None] + rs[None, :])).astype(np.float32)
    Pf = cv2.remap(np.ascontiguousarray(feat, np.float32), X, Y, cv2.INTER_LINEAR,
                   borderMode=cv2.BORDER_REPLICATE)
    S = window_contrast(Pf, win, 1) * sign
    path = dp_path(S, max_step)
    r = subpixel_edge(Pf, path, rs) + base
    r = ndi.median_filter(r, size=med, mode='nearest')
    if sm:
        r = ndi.gaussian_filter1d(r, sm, mode='nearest')
    return r


def cut_pendant_cabin():
    """Glossy black dome pendant + cord + ceiling rose from cabin_interior.png."""
    box = (2050, 0, 2820, 1480)
    I = load_src('cabin_interior.png', box)
    L = lum(I)
    h, w = L.shape
    lab = lab_image(I, 1.0)
    chroma = np.sqrt(lab[..., 1] ** 2 + lab[..., 2] ** 2)
    bgness = chroma + np.maximum(0, lab[..., 0] - 45)

    # --- lip (bright inner surface of the shade) -> axis, brim tips
    lipm = (L > 0.45) & (I[..., 0] > 0.6)
    lipm[:1300] = False
    n, lb, st, _ = cv2.connectedComponentsWithStats(lipm.astype(np.uint8), connectivity=8)
    li = 1 + int(np.argmax(st[1:, 4]))
    lx0, ly0, lw, lh = st[li, :4]
    ax = lx0 + (lw - 1) / 2
    a_brim = lw / 2 + 1
    y_lip = float(ly0)
    # bottom edge of the pale rim -> wood: per column first L>mid scanning upward, ellipse fit
    pts = []
    for x in range(int(lx0) + 25, int(lx0 + lw) - 25, 2):
        col = L[int(ly0):int(ly0 + lh) + 8, x]
        mid = 0.5                     # pale rim line ~0.75-0.95, wood below <= 0.36
        j = np.nonzero(col > mid)[0]
        if not len(j):
            continue
        j = j.max()
        if j + 1 < len(col):
            t = (col[j] - mid) / max(col[j] - col[j + 1], 1e-6)
            pts.append((x, ly0 + j + t))
    pts = np.array(pts)
    # lower rim = lower half of an ellipse with centre x = axis and semi-axis = brim half width:
    # y = ey + ery * sqrt(1 - ((x-ax)/a)^2), linear least squares in (ey, ery)
    sq = np.sqrt(np.clip(1 - ((pts[:, 0] - ax) / a_brim) ** 2, 0, 1))
    (ey, ery), *_ = np.linalg.lstsq(np.stack([np.ones_like(sq), sq], 1), pts[:, 1], rcond=None)
    th_b = np.linspace(0, 180, 361)
    bottom = np.stack([ax + a_brim * np.cos(np.radians(th_b)),
                       ey + ery * np.sin(np.radians(th_b))], 1)     # right tip -> left tip
    # --- cap (cylinder on top of the dome)
    dark = L < 0.15
    # cap rows: dark run width between the cord and the dome
    widths = np.array([(dark[y, int(ax) - 150:int(ax) + 150]).sum() for y in range(h)])
    cap_rows = np.nonzero(widths[900:1200] > 120)[0] + 900
    cap_top = int(cap_rows.min())
    cyc = cap_top + 70
    # cap axis = where the cord enters it (the cap sits a few px off the brim's axis); trace the
    # clean LEFT half (a dark groove hugs the right side) and mirror it
    rough_c = dark.copy()
    rough_c[:300] = False
    rough_c[cap_top + 6:] = False
    xg = float(np.mean(np.nonzero(rough_c[cap_top - 150])[0]))
    coef_c, _ = cord_geometry(np.where(rough_c, 1.0, 0.0).astype(np.float32), 300, cap_top + 6, xg)
    cax = float(np.polyval(coef_c, cap_top))
    th_c = np.linspace(150, 300, 301)
    r_c = trace_outline(bgness, cax, cyc, th_c, 25, 150, win=8)
    sel = th_c <= 258
    capL = polar_points(cax, cyc, th_c[sel], r_c[sel])
    # the cord enters off-centre: the cap's own axis is the mid-point between the traced left
    # edge and the right edge, which sits right before a dark wall groove (L<0.1) at mid height
    mids = []
    for y in range(cap_top + 30, cap_top + 100, 2):
        k = np.argmin(np.abs(capL[:, 1] - y))
        xl = capL[k, 0]
        x0r = int(cax) + 60
        row, crow = L[y, x0r:x0r + 80], chroma[y, x0r:x0r + 80]
        for j in range(1, len(row) - 8):
            # groove: >= 2 px of L < 0.1 starting at j, followed within 4 px by lit wood
            if row[j] < 0.1 and row[j + 1] < 0.1 and row[j - 1] >= 0.1:
                k2 = j + 2
                while k2 < len(row) - 3 and row[k2] < 0.1:
                    k2 += 1
                if (row[k2:k2 + 3] > 0.24).all() and (crow[k2:k2 + 3] > 27).all():
                    mids.append(0.5 * (xl + x0r + j - 0.5))
                    break
    cax = float(np.median(mids))
    capR = np.stack([2 * cax - capL[::-1, 0], capL[::-1, 1]], 1)
    cap = np.concatenate([capL, capR])
    # --- dome silhouette (chroma: wood is saturated orange, the shade is not), searched in a
    # band around an elliptical prior from the brim to the cap bottom
    y_dt = cap[:, 1].max()
    th_d = np.linspace(180, 360, 721)
    # wood = saturated orange; the shade's shoulders mirror the pale linen (bright, less chroma)
    woodness = chroma - 0.6 * np.maximum(0, lab[..., 0] - 42)
    r_d = trace_outline(woodness, ax, ey, th_d, -45, 55, prior=(a_brim - 6, ey - y_dt), sm=4.0)
    r_d = 0.5 * (r_d + r_d[::-1])                                       # symmetric about the axis
    dome = polar_points(ax, ey, th_d, r_d)
    # dome: drop the part hidden behind the cap
    cap_half = np.abs(cap[:, 0] - cax).max()
    keep = np.abs(dome[:, 0] - cax) > cap_half + 6
    keep_idx = np.nonzero(keep)[0]
    left = dome[keep_idx[keep_idx < len(dome) // 2]]
    right = dome[keep_idx[keep_idx >= len(dome) // 2]]
    dome_poly = np.concatenate([left, right, bottom])
    cap_poly = np.concatenate([cap, [[cax, cyc + 160]]])
    a_shade = np.maximum(poly_alpha(dome_poly, h, w), poly_alpha(cap_poly, h, w))

    # --- ceiling rose (dark disc, top hidden by fabric folds): ellipse fit on its visible edge
    rose = dark & (np.arange(h)[:, None] < 260)
    nr, lbr, str_, cen = cv2.connectedComponentsWithStats(rose.astype(np.uint8), connectivity=8)
    ri = 1 + int(np.argmax(str_[1:, 4]))
    rx0, ry0, rw, rh = str_[ri, :4]
    rcx, rcy = rx0 + rw / 2, ry0 + 0.45 * rh
    th_r = np.linspace(-20, 200, 441)
    r_r = trace_outline(L, rcx, rcy, th_r, 0.25 * rw, 0.75 * rw, win=8)
    rp = polar_points(rcx, rcy, th_r, r_r)
    rp = rp[rp[:, 1] > ry0 + 0.25 * rh]
    ecx, ecy, erx2, ery2 = fit_ellipse_axis(rp)
    a_rose = poly_alpha(ellipse_pts(ecx, ecy, erx2, ery2, n=360), h, w)
    # fabric folds hang over the top of the rose: per column, everything above the lowest bright
    # fabric pixel in the rose's upper half is occluded and gets reconstructed from the visible
    # (lower) part of the disc
    occl = np.zeros_like(dark)
    for x in range(int(ecx - erx2), int(ecx + erx2) + 1):
        col = L[int(ecy - ery2) - 2:int(ecy), x]
        j = np.nonzero(col > 0.28)[0]
        if len(j):
            occl[:int(ecy - ery2) - 2 + j.max() + 4, x] = True
    occl = cv2.dilate(occl.astype(np.uint8), np.ones((1, 9), np.uint8)) > 0
    rose_vis = erode(a_rose > 0.99, 2) & (L < 0.22) & ~occl
    rose_rgb = nfill(I, rose_vis, (2, 4, 8, 16, 32))

    # --- cord between rose and cap: projection matte clipped to a fitted tube
    cord_y0, cord_y1 = int(ecy + ery2 * 0.6), cap_top + 6
    rough = dark.copy()
    rough[:cord_y0] = False
    rough[cord_y1:] = False
    roi = dilate(rough, 9)
    a_m, rgb_m, core0, B = roi_matte(I, roi, rough, t_core=0.2)
    xg = float(np.mean(np.nonzero(core0[(cord_y0 + cord_y1) // 2])[0]))
    coef, _ = cord_geometry(a_m, cord_y0, cord_y1, xg)
    wid = cord_width(L, coef, cord_y0, cord_y1)
    a_cord = np.minimum(a_m, tube_alpha(h, w, coef, wid, cord_y0, pad=1.5))
    a_cord[:cord_y0] = 0

    # --- colours: shade/rose interiors from the photo, outer AA ring from the interior
    inner_sh = erode(a_shade > 0.99, 2)
    sh_rgb = nfill(I, inner_sh, (1.5, 3, 6, 12))
    sh_rgb = np.where(inner_sh[..., None], I, sh_rgb)
    alpha = np.maximum.reduce([a_shade, a_rose, a_cord])
    rgb = np.where((a_cord >= np.maximum(a_shade, a_rose))[..., None], rgb_m, 0)
    rgb = np.where((a_shade > a_cord)[..., None] & (a_shade >= a_rose)[..., None], sh_rgb, rgb)
    rgb = np.where((a_rose > np.maximum(a_cord, a_shade))[..., None],
                   np.where(rose_vis[..., None], I, rose_rgb), rgb)
    x0, y0, x1, y1 = trim(alpha, 4)
    a, c = alpha[y0:y1, x0:x1], rgb[y0:y1, x0:x1]
    save_rgba(os.path.join(OUT, 'pendant_cabin.png'), c, a)
    return dict(name='pendant_cabin', size=[int(x1 - x0), int(y1 - y0)],
                src_box=[int(box[0] + x0), int(y0), int(box[0] + x1), int(y1)],
                rose=dict(cx=round(ecx - x0, 1), cy=round(ecy - y0, 1), rx=round(erx2, 1), ry=round(ery2, 1)),
                cord_top=[round(float(np.polyval(coef, cord_y0)) - x0, 1), cord_y0 - y0],
                shade_axis_x=round(float(ax - x0), 1), cap_top_y=int(cap_top - y0),
                brim=dict(y=round(float(ey - y0), 1), half_width=round(float(a_brim), 1)),
                glow_center=[round(float(ax - x0), 1), round(float(ey - y0), 1)])


# --------------------------------------------------------------------------- #
# 3. cabin table top (+ leg)
# --------------------------------------------------------------------------- #

def robust_polyfit(x, y, deg, iters=6, k=2.5):
    ok = np.ones(len(x), bool)
    for _ in range(iters):
        c = np.polyfit(x[ok], y[ok], deg)
        res = np.abs(np.polyval(c, x) - y)
        mad = np.median(res[ok]) + 1e-6
        ok = res < max(1.0, k * 1.4826 * mad)
    return c, ok


# wine glasses on the cabin table (absolute source px of cabin_interior.png): far-rim top y,
# hand-measured outer half-width profile (y, r) and stem/bowl centre line (y, cx), read off
# 3x zooms; glass_outline() snaps them to the actual wall ridges.
CABIN_GLASSES = [
    dict(rim_top=2280.0,
         profile=[(2290.7, 63.7), (2300, 66.3), (2350, 73.7), (2400, 78.3), (2430, 80.5),
                  (2450, 79.0), (2475, 72.5), (2500, 59.0), (2525, 38.3), (2540, 20.8),
                  (2550, 12.5), (2570, 7.0), (2600, 5.0), (2700, 5.0)],
         centre=[(2290, 2280.4), (2450, 2281.0), (2550, 2282.0), (2700, 2282.0)]),
    dict(rim_top=2231.7,
         profile=[(2238, 61.5), (2250, 64.0), (2300, 71.5), (2350, 76.0), (2375, 76.5),
                  (2400, 72.0), (2425, 60.0), (2450, 39.0), (2462, 21.7), (2468, 11.0),
                  (2480, 7.5), (2500, 6.0), (2550, 3.9), (2700, 3.9)],
         centre=[(2238, 2803.3), (2400, 2804.0), (2470, 2805.5), (2500, 2805.7), (2550, 2803.7),
                 (2700, 2803.7)]),
]


def glass_outline(I, g, ox, oy, y_bot, snap=3, t_ridge=4.0):
    """Silhouette polygon of a stemmed wine glass from a measured profile `g` (see
    CABIN_GLASSES), snapped per row to the outermost wall ridge (Lab-L top-hat) within +-snap px
    of the measured half-width on each side; median + Gaussian smoothed; the top is closed by
    the rim ellipse. (ox, oy) = offset of image I in the source. Returns polygon (I coords)."""
    lab = lab_image(I, 0.8)
    Ll = lab[..., 0]
    ridge = np.maximum(0, Ll - cv2.GaussianBlur(Ll, (0, 0), 5))
    pf = np.array(g['profile'], float)
    cf = np.array(g['centre'], float)
    y_c = pf[0, 0]
    ys = np.arange(np.ceil(y_c), y_bot + oy)
    r_h = np.interp(ys, pf[:, 0], pf[:, 1])
    c_h = np.interp(ys, cf[:, 0], cf[:, 1])
    r = []
    for y, rh, ch in zip(ys, r_h, c_h):
        row = ridge[int(y - oy)]
        lm = (row[1:-1] >= row[:-2]) & (row[1:-1] >= row[2:]) & (row[1:-1] > t_ridge)
        xs = np.nonzero(lm)[0] + 1 + ox
        found = []
        for d in (ch - xs, xs - ch):
            cand = d[(d >= rh - snap) & (d <= rh + snap)]
            if len(cand):
                found.append(cand.max() + 1.0)        # ridge centre -> outer edge
        r.append(np.mean(found) if found else rh)
    r = np.asarray(r)
    # smooth only the deviation from the measured profile (keeps the fast bowl->stem taper)
    dev = ndi.gaussian_filter1d(ndi.median_filter(r - r_h, 11, mode='nearest'), 3.0, mode='nearest')
    r = np.maximum(r_h + dev, 3.0)
    b = max(2.0, y_c - g['rim_top'])
    th = np.linspace(180, 360, 91)
    rim = np.stack([c_h[0] + r[0] * np.cos(np.radians(th)), y_c + b * np.sin(np.radians(th))], 1)
    right = np.stack([c_h + r, ys], 1)
    left = np.stack([c_h - r, ys], 1)[::-1]
    poly = np.concatenate([rim, right, left]) - [ox, oy]
    return poly, dict(axis=float(c_h[0] - ox), rim_top=float(g['rim_top'] - oy), rim_radius=float(r[0]))


def ellipse_radial_residual(pts, e):
    cx, cy, rx, ry = e
    dx, dy = (pts[:, 0] - cx) / rx, (pts[:, 1] - cy) / ry
    rho = np.sqrt(dx * dx + dy * dy)
    rad = np.sqrt((pts[:, 0] - cx) ** 2 + (pts[:, 1] - cy) ** 2)
    return rad * (rho - 1) / np.maximum(rho, 1e-6)


def robust_ellipse(pts, iters=6, tol=3.0):
    ok = np.ones(len(pts), bool)
    for _ in range(iters):
        e = fit_ellipse_axis(pts[ok])
        res = np.abs(ellipse_radial_residual(pts, e))
        ok = res < tol
    return e, ok


def cut_cabin_table():
    """Round marble table top with glasses, candle, plates, napkins + optional pedestal leg."""
    box = (1600, 2100, 3600, 3552)
    I = load_src('cabin_interior.png', box)
    h, w = I.shape[:2]
    lab = lab_image(I, 1.0)
    dark = 100 - lab[..., 0]
    # table top silhouette: polar DP around the ellipse centre, prior ellipse, darkness contrast
    cx, cy, A, Bv = 2585 - box[0], 2785 - box[1], 852.0, 330.0
    th = np.linspace(-40, 400, 1761)
    r = trace_outline(dark, cx, cy, th, -70, 70, win=10, max_step=2, prior=(A, Bv), sm=2.0)
    keep = (th >= 0) & (th < 360)
    pts = polar_points(cx, cy, th[keep], r[keep])
    # the trace follows the TOP surface (plus plates/napkins bulging over the far edge). Fit the
    # top ellipse robustly, measure the slab thickness on the front centre column and take the
    # hull of the top ellipse and its downward translate (slab front/sides).
    (ecx, ecy, erx, ery), _ = robust_ellipse(pts)
    col = cv2.GaussianBlur(dark, (0, 0), 1.5)[:, int(ecx)]
    yb = int(ecy + ery)
    jump = col[yb + 22:yb + 130] - col[yb + 18:yb + 126]
    thick = float(np.argmax(jump) + 20)
    # slab underside edge (front half): DP around the translated ellipse
    th_b = np.linspace(-6, 186, 769)
    r_b = trace_outline(dark, ecx, ecy + thick, th_b, -28, 28, win=8, max_step=2,
                        prior=(erx, ery), sm=3.0)
    under = polar_points(ecx, ecy + thick, th_b, r_b)
    under = under[(th_b >= 14) & (th_b <= 166)]
    # the underside is a slightly smaller ellipse (seen from above, further away): fit it on the
    # reliable front part and use its whole front half; the slab ends become tapered sides
    # model: underside = top ellipse scaled by s, moved down by d (grid search, robust median)
    best = (1e9, 1.0, thick)
    for sc in np.linspace(0.96, 1.01, 51):
        for dd in np.arange(thick - 25, thick + 25.5, 0.5):
            res = np.median(np.abs(ellipse_radial_residual(under, (ecx, ecy + dd, sc * erx, sc * ery))))
            if res < best[0]:
                best = (res, sc, dd)
    _, sc, dd = best
    under = ellipse_pts(ecx, ecy + dd, sc * erx, sc * ery, a0=0, a1=180, n=361)
    thk = np.mod(th[keep], 360)
    far = pts[(thk >= 180) & (thk < 360)]
    slab = np.concatenate([under, far])
    a_top = np.maximum(poly_alpha(slab, h, w), poly_alpha(pts, h, w))
    # the polygon is a trimap: a projection matte in a +-7 px band snaps the alpha to the real
    # marble/velvet transition (rounded slab edge, perspective) with decontaminated colours
    # velvet pockets the far-edge trace may enclose (between plates/napkins and the edge):
    # dark saturated-red pixels in the far half within 40 px of the boundary, connected outside
    labv = lab_image(I, 1.5)
    velvet = (labv[..., 0] < 42) & (labv[..., 1] > 24)
    velvet[int(ecy):] = False
    rim = (a_top > 0.5) & ~erode(a_top > 0.5, 40)
    pocket = keep_connected(~(a_top > 0.5), (velvet & rim) | ~(a_top > 0.5)) & (a_top > 0.5)
    pocket = cv2.morphologyEx(pocket.astype(np.uint8), cv2.MORPH_OPEN, disk(2)) > 0
    a_top = np.where(pocket, 0.0, a_top).astype(np.float32)
    a_top, rgb_top = refine_band(I, a_top, band=6, min_contrast=0.3)
    # glasses (bowls rise above the far edge of the top)
    polys, ginfo = [], []
    for g in CABIN_GLASSES:
        far_y = cy - Bv
        p, inf = glass_outline(I, g, box[0], box[1], far_y + 70)
        polys.append(p)
        ginfo.append(inf)
    a_gl = np.maximum.reduce([poly_alpha(p, h, w) for p in polys])
    alpha = np.maximum(a_top, a_gl)
    rgb = np.where((a_gl > a_top)[..., None], I, rgb_top)
    x0, y0, x1, y1 = trim(alpha, 4)
    a, c = alpha[y0:y1, x0:x1], rgb[y0:y1, x0:x1]
    save_rgba(os.path.join(OUT, 'cabin_table_top.png'), c, a)
    info = dict(name='cabin_table_top', size=[int(x1 - x0), int(y1 - y0)],
                src_box=[int(box[0] + x0), int(box[1] + y0), int(box[0] + x1), int(box[1] + y1)],
                top_ellipse=dict(cx=round(ecx - x0, 1), cy=round(ecy - y0, 1), rx=round(erx, 1),
                                 ry=round(ery, 1)), slab_thickness=round(float(dd), 1),
                glasses=[dict(axis_x=round(g['axis'] - x0, 1), rim_top_y=round(g['rim_top'] - y0, 1))
                         for g in ginfo],
                candle_flame=[2584 - box[0] - x0, 2575 - box[1] - y0])
    return info


# --------------------------------------------------------------------------- #
# 4. tied-back sheer curtains (void_lookup_A.png)
# --------------------------------------------------------------------------- #

CURTAINS = {
    # name: (rough outline (abs px, clockwise from the header's top-left), header top line
    #        (two abs points), bottom cut y, description)
    'curtain_tieback_A': (
        [(932, 3413), (1080, 3428), (1250, 3445), (1462, 3463), (1450, 3505), (1400, 3570),
         (1330, 3660), (1262, 3760), (1205, 3840), (1165, 3872), (1170, 3930), (1178, 4100),
         (1182, 4290), (1025, 4290), (1060, 4100), (1100, 3930), (1105, 3872), (1060, 3790),
         (1000, 3690), (958, 3590), (938, 3490)],
        ((932, 3413), (1462, 3463)), 4288,
        'lower-level left curtain: pinch-pleat header, swag gathered by a tie-back, tail to the floor '
        '(tail cut straight just above a chair back)'),
    'curtain_tieback_B': (
        [(2640, 3455), (2800, 3452), (3000, 3449), (3225, 3443), (3222, 3520), (3180, 3650),
         (3140, 3760), (3100, 3840), (3062, 3888), (3075, 3990), (3110, 4100), (3160, 4203),
         (3030, 4203), (3020, 4100), (3005, 3990), (2995, 3888), (2960, 3850), (2880, 3770),
         (2800, 3700), (2730, 3620), (2670, 3530)],
        ((2640, 3455), (3225, 3443)), 4203,
        'lower-level right curtain: pinch-pleat header, swag and tie-back; tail cut straight where a '
        'table top occludes it'),
}


def grabcut_refine(I, poly_alpha_mask, inner=14, outer=16, iters=5, seed=7):
    """GrabCut initialised from a rough outline: definite fg = outline eroded by `inner`,
    definite bg = outside the outline dilated by `outer`, the ring between is probable."""
    m0 = poly_alpha_mask > 0.5
    gc = np.full(m0.shape, cv2.GC_BGD, np.uint8)
    gc[dilate(m0, outer)] = cv2.GC_PR_BGD
    gc[m0] = cv2.GC_PR_FGD
    gc[erode(m0, inner)] = cv2.GC_FGD
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.setRNGSeed(seed)
    cv2.grabCut(to_u8(I), gc, None, bgd, fgd, iters, cv2.GC_INIT_WITH_MASK)
    fg = (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)
    # clean: largest component, fill small holes, smooth the boundary a little
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg.astype(np.uint8), connectivity=8)
    fg = lab == (1 + int(np.argmax(st[1:, 4])))
    fg = fill_holes_smaller(fg, 2000)
    sm = cv2.GaussianBlur(fg.astype(np.float32), (0, 0), 1.5)
    return sm


def header_line(I, tl, tr, search=(-18, 28), dark=45):
    """Refine a curtain's header top edge: the curtain rod is a dark bar right above the pleated
    header. Per column the lower end of the first dark run (>= 5 px) near the guess line; robust
    quadratic fit (the rod follows the curved gallery). Returns a polyline from tl.x to tr.x."""
    Ll = lab_image(I, 0.7)[..., 0]
    xs, ys = [], []
    for x in range(int(tl[0]) + 8, int(tr[0]) - 8, 3):
        yg = tl[1] + (tr[1] - tl[1]) * (x - tl[0]) / (tr[0] - tl[0])
        a, b = int(yg + search[0]), int(yg + search[1])
        col = Ll[max(0, a):b, x] < dark
        run = 0
        for j, v in enumerate(col):
            run = run + 1 if v else 0
            if run >= 5 and (j + 1 >= len(col) or not col[j + 1]):
                xs.append(x); ys.append(max(0, a) + j + 1)
                break
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    gx = np.linspace(tl[0], tr[0], 60)
    if len(xs) < 10:
        return np.stack([gx, np.interp(gx, [tl[0], tr[0]], [tl[1], tr[1]])], 1)
    # the rod follows the curved gallery ring: quadratic, robust
    c, ok = robust_polyfit(xs, ys, 2, iters=6, k=2.0)
    return np.stack([gx, np.polyval(c, gx)], 1)


def curtain_polygon(m, head, y_bot, deg=4):
    """Clean outline of a tied-back curtain from a soft GrabCut mask: header line tl-tr, then
    each side edge as two robust degree-4 polynomials x(y) (swag above the tie-back, tail
    below), fitted to the per-row sub-pixel extents with outlier rejection in both directions
    (background bits and notches from dark pleat shadows are ignored)."""
    tl, tr = head[0], head[-1]
    ys, xl, xr = [], [], []
    for y in range(int(min(tl[1], tr[1])), int(y_bot)):
        c = _crossings(m[y], 0, m.shape[1])
        if c is None:
            continue
        ys.append(y); xl.append(c[0]); xr.append(c[1])
    ys, xl, xr = map(np.asarray, (ys, xl, xr))
    wdt = xr - xl
    mid = (ys > ys.min() + 0.3 * (ys.max() - ys.min())) & (ys < ys.min() + 0.75 * (ys.max() - ys.min()))
    y_tie = float(ys[mid][np.argmin(ndi.median_filter(wdt, 9)[mid])])

    def fit(v, ya, yb):
        sel = (ys >= ya) & (ys <= yb)
        t = (ys[sel] - ya) / max(1.0, yb - ya)
        c, _ = robust_polyfit(t, v[sel], deg, iters=8, k=2.0)
        yy = np.arange(np.ceil(ya), np.floor(yb) + 1)
        return np.stack([np.polyval(c, (yy - ya) / max(1.0, yb - ya)), yy], 1)

    r_sw = fit(xr, tr[1], y_tie)
    r_tl = fit(xr, y_tie, ys.max())
    l_sw = fit(xl, tl[1], y_tie)
    l_tl = fit(xl, y_tie, ys.max())
    right = np.concatenate([r_sw, r_tl])
    left = np.concatenate([l_sw, l_tl])[::-1]
    return np.concatenate([head, right, left]).astype(np.float64)


def cut_curtain(name):
    poly, top, ycut, desc = CURTAINS[name]
    poly = np.array(poly, np.float64)
    x0, y0 = int(poly[:, 0].min()) - 40, int(poly[:, 1].min()) - 40
    x1, y1 = int(poly[:, 0].max()) + 40, int(ycut) + 40
    I = load_src('void_lookup_A.png', (x0, y0, x1, y1))
    h, w = I.shape[:2]
    pl = poly - [x0, y0]
    a_rough = poly_alpha(pl, h, w)
    sm = grabcut_refine(I, a_rough)
    tp0 = (top[0][0] - x0, top[0][1] - y0)
    tp1 = (top[1][0] - x0, top[1][1] - y0)
    head = header_line(I, tp0, tp1)
    pg = curtain_polygon(sm, head, int(ycut - y0) + 2)
    a_pg = poly_alpha(pg, h, w)
    alpha, rgb = refine_band(I, a_pg, band=3, min_contrast=0.3)
    # geometric cuts: header top line, straight bottom cut
    tp = [tuple(head[0]), tuple(head[-1])]
    yy = np.arange(h, dtype=np.float32)[:, None]
    alpha = alpha * np.clip(ycut - y0 - yy + 0.5, 0, 1)
    alpha = alpha.astype(np.float32)
    bx0, by0, bx1, by1 = trim(alpha, 4)
    a, c = alpha[by0:by1, bx0:bx1], rgb[by0:by1, bx0:bx1]
    save_rgba(os.path.join(OUT, name + '.png'), c, a)
    return dict(name=name, desc=desc, size=[int(bx1 - bx0), int(by1 - by0)],
                src_box=[int(x0 + bx0), int(y0 + by0), int(x0 + bx1), int(y0 + by1)],
                header_line=[[round(tp[0][0] - bx0, 1), round(tp[0][1] - by0, 1)],
                             [round(tp[1][0] - bx0, 1), round(tp[1][1] - by0, 1)]],
                bottom_cut_y=int(ycut - y0 - by0))


# --------------------------------------------------------------------------- #
# 5. espresso cup + saucer (skimage.data.coffee(), CC0)
# --------------------------------------------------------------------------- #

def cut_espresso():
    from skimage import data
    I = data.coffee().astype(np.float32) / 255.0
    h, w = I.shape[:2]
    lab = lab_image(I, 0.8)
    L = lab[..., 0]
    # saucer: red glaze (a* ~45-55) against wood (a* ~26-32) and the dark contact shadow
    cx, cy = 278.0, 231.0
    th = np.linspace(-30, 390, 1681)
    r = trace_outline(lab[..., 1], cx, cy, th, -26, 26, win=6, max_step=2, sign=-1, med=7, sm=2.0,
                      prior=(200.0, 157.0))
    keep = (th >= 0) & (th < 360)
    saucer = polar_points(cx, cy, th[keep], r[keep])
    # cup: white rim rising above the saucer (upper half of its outer rim ellipse)
    ccx, ccy = 290.0, 112.0
    th2 = np.linspace(150, 390, 961)
    r2 = trace_outline(L, ccx, ccy, th2, -22, 22, win=5, max_step=2, sign=-1, med=7, sm=1.5,
                       prior=(118.0, 94.0))
    cup = np.concatenate([polar_points(ccx, ccy, th2, r2), [[ccx, ccy + 120]]])
    # spoon handle tip leaving the saucer (neutral metal against saturated wood)
    chroma = np.sqrt(lab[..., 1] ** 2 + lab[..., 2] ** 2)
    sp = np.zeros((h, w), bool)
    sp[55:140, 380:440] = (chroma[55:140, 380:440] < 38) & (L[55:140, 380:440] > 25)
    sp = cv2.morphologyEx(sp.astype(np.uint8), cv2.MORPH_OPEN, disk(2)) > 0
    sp = keep_connected(sp & (np.arange(h)[:, None] > 100), sp) if (sp[100:140].any()) else sp
    sp = fill_holes_smaller(sp, 400)
    a_sp = cv2.GaussianBlur(sp.astype(np.float32), (0, 0), 0.7)
    # both are ellipses in the photo: robust fits give clean, exact rims
    def outer_contour(mask):
        cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        return max(cs, key=cv2.contourArea)[:, 0].astype(np.float64)
    yy, xx = np.mgrid[0:h, 0:w]
    prior = (((xx - cx) / 225.0) ** 2 + ((yy - cy) / 180.0) ** 2) < 1
    red = ((lab[..., 1] > 34) & (L > 8) & prior).astype(np.uint8)
    red = cv2.morphologyEx(red, cv2.MORPH_OPEN, disk(3))
    red = cv2.morphologyEx(red, cv2.MORPH_CLOSE, disk(9))
    n_, lb_, st_, _ = cv2.connectedComponentsWithStats(red, connectivity=8)
    red = lb_ == 1 + int(np.argmax(st_[1:, 4]))
    es, _ = robust_ellipse(outer_contour(fill_holes_smaller(red, 10 ** 6)), tol=3.0)
    white = cv2.morphologyEx((L > 78).astype(np.uint8), cv2.MORPH_OPEN, disk(2))
    n_, lb_, st_, _ = cv2.connectedComponentsWithStats(white, connectivity=8)
    white = lb_ == 1 + int(np.argmax(st_[1:, 4]))
    wc = outer_contour(fill_holes_smaller(white, 10 ** 6))
    ec, _ = robust_ellipse(wc[wc[:, 1] < np.percentile(wc[:, 1], 60)], tol=2.0)
    a_poly = np.maximum.reduce([poly_alpha(ellipse_pts(*es, n=720), h, w),
                                poly_alpha(ellipse_pts(*ec, n=720), h, w), a_sp])
    alpha, rgb = refine_band(I, a_poly, band=2, min_contrast=0.35)
    x0, y0, x1, y1 = trim(alpha, 4)
    save_rgba(os.path.join(OUT, 'espresso_cc0.png'), rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1])
    return dict(name='espresso_cc0', size=[int(x1 - x0), int(y1 - y0)], src_box=[int(x0), int(y0), int(x1), int(y1)],
                cup_rim_ellipse=[round(ec[0] - x0, 1), round(ec[1] - y0, 1), round(ec[2], 1), round(ec[3], 1)],
                saucer_ellipse=[round(es[0] - x0, 1), round(es[1] - y0, 1), round(es[2], 1), round(es[3], 1)])


# --------------------------------------------------------------------------- #
# 6. tree in the void (void_lookup_B.png)
# --------------------------------------------------------------------------- #

TREE_BOX = (560, 560, 3110, 4576)      # canopy + trunk, source px
SKY_BOTTOM = 1700                       # lowest source row of the glazed skylight opening
LOW_CANOPY_Y = 2850                     # below: leaves seen against dark warm ceiling/walls
TRUNK_LEFT = [(2500, 1780), (3200, 1779), (3800, 1749), (4100, 1742), (4576, 1726)]
TRUNK_RIGHT = [(2500, 1850), (3200, 1861), (3800, 1859), (4576, 1857)]
TRUNK_TOP = 2500
# pale, sun-lit limbs above the fork: their bark is as light and neutral as the white shaft wall
# behind, so they get fitted outlines like the trunk: (y_top, y_bottom, left guide, right guide)
PALE_LIMBS = [
    (2245, 2420, [(2245, 1841), (2300, 1832), (2350, 1818), (2420, 1815)],
                 [(2245, 1867), (2300, 1856), (2350, 1856), (2420, 1857)]),
]


def _small(m, f):
    h, w = m.shape
    return cv2.resize(m.astype(np.float32), (w // f, h // f), interpolation=cv2.INTER_AREA)


def _big(m, shape):
    return cv2.resize(m.astype(np.float32), (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)


def tree_classes(I):
    """Per-pixel classes for the tree photo: returns (tree_conf, bg_conf, leaf, skylight)."""
    h, w = I.shape[:2]
    hsv = cv2.cvtColor(I, cv2.COLOR_RGB2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    yy = np.arange(h)[:, None]
    below_sky = yy > (SKY_BOTTOM - TREE_BOX[1])
    # leaves: yellow-green..green. Below the skylight warm lamp glow (H 40-50) is not a leaf.
    green = (H >= np.where(below_sky, 52, 42)) & (H <= 175) & (S > 0.25) & (V > 0.06)
    warm = (H < 50) | (H > 330)
    neutral_light = (S < 0.14) & (V > 0.45)
    warm_light = (V > 0.6) & warm & ~green
    # below the skylight pale lit bark (S<0.14, V 0.45-0.8) looks neutral too: only bright
    # neutrals (white walls, curtains) are confident background there
    bg_conf = (neutral_light & ~(below_sky & (V < 0.88))) | warm_light
    # skylight: the big neutral bright region (sky + glazing), hull (computed at 1/4 res)
    nb = _small(neutral_light & (V > 0.78), 4) > 0.5
    nb = cv2.morphologyEx(nb.astype(np.uint8), cv2.MORPH_CLOSE, disk(12))
    n, lab, st, _ = cv2.connectedComponentsWithStats(nb, connectivity=8)
    sky = lab == 1 + int(np.argmax(st[1:, 4]))
    hull = cv2.convexHull(np.argwhere(sky)[:, ::-1].astype(np.int32))
    skym = np.zeros(sky.shape, np.uint8)
    cv2.fillPoly(skym, [hull], 1)
    skylight = _big(cv2.erode(skym, disk(3)), (h, w)) > 0.5
    skylight[max(0, SKY_BOTTOM - TREE_BOX[1]):] = False   # white shaft walls below are not sky
    # leaf envelope (1/2 res closing)
    env = _small(green, 2) > 0.2
    env = cv2.morphologyEx(env.astype(np.uint8), cv2.MORPH_CLOSE, disk(14))
    env = cv2.dilate(env, disk(6))
    env = fill_holes_smaller(env > 0, 4000).astype(np.uint8)   # gaps inside the crown
    env = _big(env, (h, w)) > 0.5
    dark = (V < 0.5) & ~neutral_light & ~green
    # over the skylight everything that is not neutral sky/glazing is tree (leaves, twigs, pods)
    # glazing bar edges / sky tint; below the skylight only bright bluish (dark knots are bark)
    bluish = (H > 175) & (H < 280) & (skylight | (V > 0.45))
    tree_sky = skylight & ~bluish & ((S > 0.2) | ((V < 0.3) & (S > 0.12)))
    # elsewhere: green leaves + dark (branches, pods) inside the leaf envelope; in the lower part
    # thick dark blobs are ceiling/doorway shadow seen through the leaves -> rejected
    dark_w = dark & env & ~skylight
    # lower canopy: the backdrop is a dark warm ceiling/wall, as dark and brown as the twigs.
    # There only thin dark structures right next to leaves are kept (petioles, twigs).
    low = yy > (LOW_CANOPY_Y - TREE_BOX[1])
    thin = dark_w & ~(cv2.morphologyEx(dark_w.astype(np.uint8), cv2.MORPH_OPEN, disk(3)) > 0)
    # the dark wall right at a leaf edge is 'thin' too: only elongated thin structures that
    # survive removing the 1 px leaf-edge ring count (petioles, twigs)
    cand = (thin & low & dilate(green, 4) & ~dilate(green, 1)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(cand, connectivity=8)
    longc = np.zeros(n, bool)
    longc[1:] = (np.maximum(st[1:, 2], st[1:, 3]) >= 14) & (st[1:, 4] >= 20)
    twig = longc[lab]
    del lab
    twig = dilate(twig, 1) & thin
    dark_w = np.where(low, twig, dark_w)
    tree_conf = tree_sky | (green & ~skylight) | dark_w | (green & skylight)
    tree_conf &= ~bg_conf | (green & (S > 0.35))
    tree_conf &= ~(bluish & ~green)
    bg_conf = bg_conf | (bluish & ~green) | (skylight & (S < 0.12))
    return tree_conf, bg_conf, green, skylight


def trunk_edges_colour(I, y0, y1, xl_guess, xr_guess, search=30, deg=3, inset=0.7):
    """Trunk side edges from the bark's own colour: per row a bark model (median Lab of the
    middle half of the guessed trunk, pooled over +-12 rows), the colour distance profile
    across the row, and from the centre outwards the sub-pixel crossing of the mid level between
    bark and the background just outside the guess. Robust degree-`deg` polynomials x(y).
    Returns (ys, xl, xr) arrays."""
    lab = lab_image(I, 1.0)
    wts = np.array([1.0, 1.4, 1.4], np.float32)
    ys = np.arange(int(y0), int(y1))
    gl = np.array([xl_guess(y) for y in ys])
    gr = np.array([xr_guess(y) for y in ys])
    mid = 0.5 * (gl + gr)
    q = 0.25 * (gr - gl)
    models = np.array([np.median(lab[y, int(m - qq):int(m + qq) + 1], 0) for y, m, qq in zip(ys, mid, q)])
    models = ndi.uniform_filter1d(models, 25, axis=0, mode='nearest')
    res = {'l': [], 'r': []}
    for k, y in enumerate(ys):
        row = lab[y]
        D = np.sqrt((((row - models[k]) * wts) ** 2).sum(-1))
        D = np.convolve(D, np.ones(3) / 3, mode='same')
        for side, g, sgn in (('l', gl[k], -1), ('r', gr[k], 1)):
            cin = np.median(D[int(mid[k] - q[k]):int(mid[k] + q[k]) + 1])
            o0 = int(g + sgn * (search - 6))
            out = D[min(o0, o0 + sgn * 12):max(o0, o0 + sgn * 12) + 1]
            cout = np.median(out) if len(out) else cin + 20
            if cout - cin < 6:
                res[side].append(np.nan)
                continue
            lvl = 0.5 * (cin + cout)
            x = int(mid[k])
            lim = int(g + sgn * search)
            found = np.nan
            while (x - lim) * sgn < 0:
                if D[x + sgn] >= lvl > D[x] or (D[x] < lvl and D[x + sgn] >= lvl):
                    found = x + sgn * (lvl - D[x]) / max(D[x + sgn] - D[x], 1e-6)
                    break
                x += sgn
            res[side].append(found)
    out = []
    t = (ys - y0) / max(1, y1 - y0)
    for side, sgn in (('l', -1), ('r', 1)):
        v = np.array(res[side], float)
        ok = ~np.isnan(v)
        cf, _ = robust_polyfit(t[ok], v[ok], deg, iters=10, k=2.0)
        base = np.polyval(cf, t)
        # follow local shape: inliers (within 5 px of the global fit) median + Gaussian smoothed
        ok &= np.abs(np.nan_to_num(v, nan=1e9) - base) < 5
        loc = np.interp(np.arange(len(v)), np.nonzero(ok)[0], v[ok])
        loc = ndi.gaussian_filter1d(ndi.median_filter(loc, 21, mode='nearest'), 4, mode='nearest')
        out.append(loc - sgn * inset)
    return ys, out[0], out[1]


def cut_tree():
    """tree_B.png (whole tree) and tree_B_canopy_sky.png (canopy over the skylight only)."""
    bx0, by0, bx1, by1 = TREE_BOX
    I = load_src('void_lookup_B.png', TREE_BOX)
    h, w = I.shape[:2]
    tree, bg, green, skylight = tree_classes(I)
    # cleanup: keep what belongs to the main structure. Connectivity is evaluated on a 3 px
    # dilation so leaflets hanging on 1 px twigs stay attached; specks < 40 px are dropped.
    tree = tree.astype(bool)
    # canopy envelope from LEAF density only (rails, glazing bars and the gallery ring are not
    # green): 1/8-res density > 4 %, closed, largest blob, slightly dilated
    dens = _small(green, 8)
    env = (dens > 0.04).astype(np.uint8)
    env = cv2.morphologyEx(env, cv2.MORPH_CLOSE, disk(6))
    n, lab, st, _ = cv2.connectedComponentsWithStats(env, connectivity=8)
    env = (lab == 1 + int(np.argmax(st[1:, 4]))).astype(np.uint8)
    env = fill_holes_smaller(env > 0, 10 ** 6).astype(np.uint8)
    env = cv2.dilate(env, disk(2))
    env = _big(env, (h, w)) > 0.5
    tree &= env
    n, lab, st, _ = cv2.connectedComponentsWithStats(dilate(tree, 3).astype(np.uint8), connectivity=8)
    main = lab == 1 + int(np.argmax(st[1:, 4]))
    del lab
    tree &= main
    # pale lit bark (neutral, not bright) bridged by a small closing, above the lower canopy
    hsv = cv2.cvtColor(I, cv2.COLOR_RGB2HSV)
    pale = (hsv[..., 1] < 0.14) & (hsv[..., 2] < 0.88) & ~bg
    pale[LOW_CANOPY_Y - by0:] = False
    del hsv
    closed = cv2.morphologyEx(tree.astype(np.uint8), cv2.MORPH_CLOSE, disk(3)) > 0
    tree |= closed & pale
    # enclosed holes that contain (almost) no confident background are part of the tree
    # (bark knots, dark shadowed leaf overlaps)
    inv = (~tree).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    bgc = np.bincount(lab.ravel(), weights=bg.ravel().astype(np.float64), minlength=n)
    fillable = (st[:, 4] < 6000) & (bgc < 0.05 * st[:, 4])
    fillable[0] = False
    fillable[lab[0, 0]] = False
    tree |= fillable[lab]
    del lab
    n, lab, st, _ = cv2.connectedComponentsWithStats(tree.astype(np.uint8), connectivity=8)
    big = np.zeros(n, bool)
    big[1:] = st[1:, 4] >= 40
    tree = big[lab]
    del lab
    # trunk: fitted polygon from the fork down to the bottom edge
    tx0 = 1600 - bx0
    trunk_I = I[TRUNK_TOP - by0:, tx0:tx0 + 420]
    gl = np.array(TRUNK_LEFT, float)
    gr = np.array(TRUNK_RIGHT, float)
    ys_t, xl_t, xr_t = trunk_edges_colour(
        trunk_I, 0, trunk_I.shape[0],
        lambda y: np.interp(y + TRUNK_TOP, gl[:, 0], gl[:, 1]) - 1600,
        lambda y: np.interp(y + TRUNK_TOP, gr[:, 0], gr[:, 1]) - 1600)
    pg = np.concatenate([np.stack([xl_t, ys_t], 1), np.stack([xr_t, ys_t], 1)[::-1]])
    pg = pg + [tx0, TRUNK_TOP - by0]
    a_trunk = poly_alpha(pg, h, w)
    a_trunk[:TRUNK_TOP + 2 - by0] = 0
    for (ly0, ly1, lgl, lgr) in PALE_LIMBS:
        lgl, lgr = np.array(lgl, float), np.array(lgr, float)
        lx0 = int(min(lgl[:, 1].min(), lgr[:, 1].min())) - 40
        lI = I[ly0 - by0:ly1 - by0, lx0 - bx0:lx0 - bx0 + 160]
        ys_l, xl_l, xr_l = trunk_edges_colour(
            lI, 0, lI.shape[0],
            lambda y: np.interp(y + ly0, lgl[:, 0], lgl[:, 1]) - lx0,
            lambda y: np.interp(y + ly0, lgr[:, 0], lgr[:, 1]) - lx0, search=10, deg=2, inset=0.3)
        lp = np.concatenate([np.stack([xl_l, ys_l], 1), np.stack([xr_l, ys_l], 1)[::-1]])
        a_trunk = np.maximum(a_trunk, poly_alpha(lp + [lx0 - bx0, ly0 - by0], h, w))
    a_trunk_r, rgb_trunk = refine_band(I, a_trunk, band=2, min_contrast=0.3)
    tree |= a_trunk > 0.5
    # difference matte in a 2 px band: background plate from confident background, foreground
    # colour from confident tree pixels; projection gated by colour contrast
    core = erode(tree, 1)
    band = dilate(tree, 2) & ~core
    bgk = ~dilate(tree, 2)          # everything not tree is background (local plate)
    B = nfill(I, bgk, (1.5, 3, 6, 12, 24))
    F = nfill(I, core | (tree & ~dilate(~tree, 0)), (1.5, 3, 6, 12))
    a = project_alpha(I, F, B, floor=0.08)
    con = np.sqrt(((F - B) ** 2).sum(-1))
    soft = cv2.GaussianBlur(tree.astype(np.float32), (0, 0), 0.7)
    t = smoothstep(0.1, 0.22, con)
    a = a * t + soft * (1 - t)
    alpha = np.where(core, 1.0, np.where(band, a, 0.0)).astype(np.float32)
    rgb = decontaminate(I, alpha, B, F)
    rgb = np.where(core[..., None], I, rgb)
    alpha = np.maximum(alpha, a_trunk_r)
    rgb = np.where((a_trunk_r > 0.5)[..., None], rgb_trunk, rgb)
    del B, F, a, con, soft
    x0, y0, x1, y1 = trim(alpha, 4)
    save_rgba(os.path.join(OUT, 'tree_B.png'), rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1])
    info = dict(name='tree_B', size=[int(x1 - x0), int(y1 - y0)],
                src_box=[int(bx0 + x0), int(by0 + y0), int(bx0 + x1), int(by0 + y1)],
                trunk_base=[round(float(pg[:, 0][np.argmax(pg[:, 1])]) - x0, 1), int(y1 - y0 - 1)],
                trunk_polygon_top_y=int(TRUNK_TOP - by0 - y0))
    # canopy over the skylight only (cut at the skylight outline, anti-aliased)
    sk = cv2.GaussianBlur(skylight.astype(np.float32), (0, 0), 1.0)
    a_sky = alpha * sk * (1 - (a_trunk > 0.5))
    sx0, sy0, sx1, sy1 = trim(a_sky, 4)
    save_rgba(os.path.join(OUT, 'tree_B_canopy_sky.png'), rgb[sy0:sy1, sx0:sx1], a_sky[sy0:sy1, sx0:sx1])
    info_sky = dict(name='tree_B_canopy_sky', size=[int(sx1 - sx0), int(sy1 - sy0)],
                    src_box=[int(bx0 + sx0), int(by0 + sy0), int(bx0 + sx1), int(by0 + sy1)],
                    offset_in_tree_B=[int(sx0 - x0), int(sy0 - y0)])
    return info, info_sky


# --------------------------------------------------------------------------- #
# index + contact sheet + build
# --------------------------------------------------------------------------- #

def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return round(float(o), 2)
    return o


def _font(size):
    from PIL import ImageFont
    for p in (P('assets', 'fonts', 'IBMPlexMono-Regular.ttf'),
              '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


# hardest edges, 100 % crops: (file, (x0, y0, x1, y1) in that file's pixels, label)
CHECK_CROPS = [
    ('fig_woman_coffee.png', (330, 0, 590, 260), 'hair (woman with coffee)'),
    ('fig_standing_pair.png', (220, 150, 420, 330), 'wine glasses + stems (standing pair)'),
    ('fig_couple_table.png', (420, 180, 600, 360), 'glass stems on the bistro table'),
    ('fig_couple_table_flat.png', (420, 180, 600, 360), 'same, flat ink silhouette'),
    ('pendant_valance_R.png', (205, 250, 300, 600), 'cord over the lit valance'),
    ('pendant_valance_L.png', (0, 1640, 300, 1910), 'shade rim + bulb'),
    ('pendant_cabin.png', (100, 860, 420, 1150), 'cabin pendant cap/cord junction'),
    ('cabin_table_top.png', (480, 0, 740, 300), 'transparent wine-glass bowl'),
    ('curtain_tieback_B.png', (0, 120, 300, 420), 'curtain swag edge'),
    ('tree_B_canopy_sky.png', (560, 218, 860, 518), 'leaves over the skylight'),
    ('tree_B.png', (1500, 2050, 1800, 2350), 'lower canopy over the dark ceiling'),
    ('tree_B.png', (900, 1550, 1200, 1850), 'fork: pale bark, knots, leaves over wall'),
    ('tree_B.png', (1112, 2156, 1252, 2356), 'trunk edge against a lit pendant'),
    ('cabin_table_top.png', (1000, 0, 1180, 360), 'right wine glass, stem over velvet'),
]


def contact_sheet(entries, path=CONTACT, row_h=430, width=3000):
    """Every cut-out over linen | grey | indigo + 100 % crops of the hardest edges."""
    from PIL import ImageDraw
    pad, lab_h = 18, 52
    font, small = _font(24), _font(18)
    blocks = []
    for e in entries:
        rgb, a = load_cut(P(e['path']))
        hh, ww = a.shape
        s = min(row_h / hh, (width - 4 * pad) / 3 / ww, 1.0)
        t = triple(rgb, a, s, gap=pad)
        blocks.append((f"{os.path.basename(e['path'])}\n{ww}x{hh}", t))
    crops = []
    for f, (x0, y0, x1, y1), label in CHECK_CROPS:
        if not os.path.exists(os.path.join(OUT, f)):
            continue
        rgb, a = load_cut(os.path.join(OUT, f))
        x1, y1 = min(x1, a.shape[1]), min(y1, a.shape[0])
        crops.append((f'100%  {f}\n{label}', triple(rgb[y0:y1, x0:x1], a[y0:y1, x0:x1], 1.0, gap=8)))
    # layout: thumbnails in rows of as many as fit, then crops two per row
    rows, cur, cur_w = [], [], 0
    for lbl, t in blocks:
        if cur and cur_w + t.shape[1] + pad > width:
            rows.append(cur); cur, cur_w = [], 0
        cur.append((lbl, t)); cur_w += t.shape[1] + pad
    rows.append(cur)
    crow, cur, cur_w = [], [], 0
    for lbl, t in crops:
        if cur and cur_w + t.shape[1] + pad > width:
            crow.append(cur); cur, cur_w = [], 0
        cur.append((lbl, t)); cur_w += t.shape[1] + pad
    if cur:
        crow.append(cur)
    total_h = 70 + sum(max(t.shape[0] for _, t in r) + lab_h + pad for r in rows) + 60 + \
        sum(max(t.shape[0] for _, t in r) + lab_h + pad for r in crow)
    sheet = Image.new('RGB', (width, int(total_h)), (250, 248, 244))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 18), 'CUTOUTS - every asset over linen #EFE6D6 | grey #808080 | indigo #262C45',
           fill=(43, 36, 32), font=font)
    y = 70
    for group in (rows, None, crow):
        if group is None:
            d.text((pad, y + 14), '100 % CROPS OF THE HARDEST EDGES', fill=(43, 36, 32), font=font)
            y += 60
            continue
        for r in group:
            x = pad
            rh = max(t.shape[0] for _, t in r)
            for lbl, t in r:
                for li, line in enumerate(lbl.split('\n')):   # clip each line to the block width
                    while line and d.textlength(line, font=small) > t.shape[1]:
                        line = line[:-1]
                    d.text((x, y + 4 + 22 * li), line, fill=(43, 36, 32), font=small)
                sheet.paste(Image.fromarray(to_u8(t)), (x, y + lab_h))
                x += t.shape[1] + pad
            y += rh + lab_h + pad
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sheet.save(path, quality=90)
    return path


def build():
    """Regenerate every cut-out, index.json and the contact sheet (deterministic)."""
    os.makedirs(OUT, exist_ok=True)
    idx = []

    def add(info, desc, use, **extra):
        e = dict(path=f"assets/cut/{info['name']}.png", size=info['size'], description=desc,
                 suggested_use=use)
        e.update({k: v for k, v in info.items() if k not in ('name', 'size', 'desc')})
        e.update(extra)
        idx.append(e)

    src_d = 'assets/gen/diners_silhouettes.png'
    for info in cut_diners():
        add(info, info['desc'] + '. Photographic grey silhouette (soft luminance key, 2 px solved '
            'edge band, colours decontaminated against the white studio ground, floor contact '
            'shadows removed).',
            'shadow-play behind sheer linen, foreground diners; scale freely down, multiply or '
            'normal blend', source=src_d,
            anchors=dict(ground_y=info['ground_y'], x_extent=info['x_extent']))
        flat = dict(info, name=info['name'] + '_flat')
        add(flat, info['desc'] + '. Same alpha, RGB = ink #2B2420 (pure silhouette).',
            'shadow-play silhouettes, multiply at 20-60 % behind linen layers', source=src_d,
            anchors=dict(ground_y=info['ground_y'], x_extent=info['x_extent']))
    for side in 'LR':
        info = cut_pendant_festoon(side)
        add(info, f'black enamel dome pendant ({side} of the valance photo) with its full cord '
            'running off the top edge (y=0) and the warm amber bulb; cord matte = projection key '
            'clipped to a fitted tube, shade = sub-pixel contour, bulb = fitted ellipse.',
            'hang from a festoon ceiling; cord top sits flush with the image top edge; add a '
            'screen/linear-dodge glow at the bulb anchor', source='assets/gen/festoon_valance.png')
    info = cut_pendant_cabin()
    add(info, 'glossy black dome pendant from the cabin with cap, curved cord and dark ceiling '
        'rose (rose top was hidden by linen folds: completed as an ellipse, its colour '
        'reconstructed from the visible part); shade outline traced in polar DP and symmetrised; '
        'warm amber lip at the brim kept.',
        'cabin pendant; tuck the rose under a festoon/linen ceiling; glow_center = inside of the '
        'brim for a light cone', source='assets/gen/cabin_interior.png')
    info = cut_cabin_table()
    add(info, 'round marble table top (slab with its front edge) with two red-wine glasses '
        '(bowls + stems; glass keeps its own velvet tones inside the glass outline), candle in '
        'a glass, two plates, napkins and cutlery; no pedestal.',
        'cabin interior foreground / taste & smell zone; glasses rim tops listed for placement',
        source='assets/gen/cabin_interior.png')
    for n in CURTAINS:
        info = cut_curtain(n)
        add(info, info['desc'] + '. GrabCut from a hand outline, sides re-fitted as robust '
            'polynomials (no pleat-shadow notches or wall bits), header = curved rod line, '
            '3 px projection band where the contrast allows.',
            'sheer white tied-back curtain for the void / party-hall layers; screen or normal '
            'blend at 70-100 %', source='assets/gen/void_lookup_A.png')
    info = cut_espresso()
    add(info, 'espresso cup on saucer with spoon (skimage.data.coffee(), CC0). Source is only '
        '400x600 px: use small (<= ~350 px wide on the A3 canvas).',
        'coffee / smell annotation, bar side of collage 01', source='skimage.data.coffee() (CC0)',
        license='CC0 (scikit-image sample data)')
    t_all, t_sky = cut_tree()
    add(t_all, 'whole tree in the void (trunk + canopy) from void_lookup_B. Canopy over the '
        'skylight: clean difference key against the sky/glazing plate. Canopy over rails, '
        'curtains and walls: hue-based leaf classification + dark branch pixels inside the leaf '
        'envelope, morphological cleanup, 2 px projection band. Trunk: fitted polygon '
        '(robust edge polynomials). HONEST NOTE: the lower canopy (below the skylight) has '
        'occasional small background bits between leaves (warm wall/ceiling patches) and a few '
        'pale lit twigs are dropped; fine at collage scale, inspect before using > 60 %.',
        'hero tree of collage 01; trunk_base is where the trunk leaves the bottom edge',
        source='assets/gen/void_lookup_B.png')
    add(t_sky, 'only the canopy region over the glazed skylight (cut by the skylight outline, '
        'anti-aliased) - the cleanest leaf edges of the set.',
        'luminous green-gold canopy layer over the skylight / light plane',
        source='assets/gen/void_lookup_B.png')
    idx = _jsonable(idx)
    with open(os.path.join(OUT, 'index.json'), 'w') as f:
        json.dump(dict(area='cutouts', module='src/lib/cutouts.py', root_relative=True,
                       note='RGBA 8-bit straight alpha, native source resolution, trimmed with a '
                            '4 px margin. src_box = crop in the source photo (x0, y0, x1, y1). '
                            'All anchor coordinates are in the asset\'s own pixel space. '
                            'assets/cut/geo/ belongs to another area.',
                       assets=idx), f, indent=1)
    contact_sheet(idx)
    return idx


if __name__ == '__main__':
    build()
