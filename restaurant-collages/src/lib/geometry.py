"""geometry — precise masks + parametric geometry fitted to the AI source photos.

Every mask is full source-image size, 8-bit L PNG (white = keep), analytically anti-aliased
(signed-distance coverage) wherever the shape is parametric. Coordinates are source-image
pixels, x right / y down; pixel (i, j) covers [i, i+1) x [j, j+1), so its centre is (i+.5, j+.5)
and a boundary at x = 100.0 splits pixels 99 | 100 exactly.

Seeds (rough positions read off zoomed previews) only say WHICH edge is meant; every boundary
is then located automatically (sub-pixel edge search along normals, robust line / ellipse /
spline fits, edge-contrast maximisation, GrabCut + colour unmixing for organic edges).

Regenerate everything:  cd src && python3 -c "from lib import geometry; geometry.build()"
"""
from __future__ import annotations

import json
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'assets', 'cut', 'geo')
SCRATCH = os.path.join(ROOT, 'build', 'geometry')
PREV = os.path.join(ROOT, 'build', 'preview', 'geometry')
CONTACT = os.path.join(ROOT, 'build', 'contact', 'geometry.jpg')


def P(*parts):
    return os.path.join(ROOT, *parts)


# --------------------------------------------------------------------------- #
# io
# --------------------------------------------------------------------------- #

def load_src(name):
    """uint8 RGB array of assets/gen/<name>.png (cached as .npy under build/geometry)."""
    cache = os.path.join(SCRATCH, f'src_{name}.npy')
    if os.path.exists(cache):
        return np.load(cache)
    a = np.asarray(Image.open(P('assets', 'gen', f'{name}.png')).convert('RGB'))
    os.makedirs(SCRATCH, exist_ok=True)
    np.save(cache, a)
    return a


def gray(rgb):
    return rgb.astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def save_mask(m, rel):
    """Save float 0..1 (or uint8) mask as 8-bit L PNG at ROOT/<rel>."""
    path = P(rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if m.dtype != np.uint8:
        m = np.clip(m * 255.0 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(m, 'L').save(path, optimize=False, compress_level=6)
    return rel


def save_label16(lab, rel):
    path = P(rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(lab.astype(np.uint16)).save(path)
    return rel


# --------------------------------------------------------------------------- #
# analytic anti-aliased coverage (signed distance -> coverage)
# --------------------------------------------------------------------------- #

def _grid(h, w, box=None):
    """Pixel-centre coordinate grids for the (x0, y0, x1, y1) sub-box."""
    x0, y0, x1, y1 = box if box is not None else (0, 0, w, h)
    ys = np.arange(y0, y1, dtype=np.float32) + 0.5
    xs = np.arange(x0, x1, dtype=np.float32) + 0.5
    return xs[None, :], ys[:, None]


def cov(sd):
    """Coverage from signed distance (negative inside), 1 px box filter."""
    return np.clip(0.5 - sd, 0.0, 1.0).astype(np.float32)


def sd_ellipse(X, Y, cx, cy, rx, ry, angle=0.0):
    """Approximate signed distance to an ellipse (angle in degrees, CW in image)."""
    t = np.deg2rad(angle)
    c, s = np.cos(t), np.sin(t)
    dx, dy = X - cx, Y - cy
    u = (dx * c + dy * s) / rx
    v = (-dx * s + dy * c) / ry
    r = np.sqrt(u * u + v * v) + 1e-9
    gu, gv = u / (rx * r), v / (ry * r)
    return (r - 1.0) / np.sqrt(gu * gu + gv * gv + 1e-12)


def sd_halfplane_x(X, x0, keep='right'):
    return (x0 - X) if keep == 'right' else (X - x0)


def sd_halfplane_y(Y, y0, keep='below'):
    return (y0 - Y) if keep == 'below' else (Y - y0)


def sd_curve_y(X, Y, fy, keep='below', dfy=None):
    """Signed distance to the graph y = fy(x) (vectorised callable), slope-corrected."""
    yx = fy(X)
    if dfy is None:
        e = 0.5
        dfy = (fy(X + e) - fy(X - e)) / (2 * e)
    else:
        dfy = dfy(X)
    k = 1.0 / np.sqrt(1.0 + dfy * dfy)
    d = (yx - Y) * k
    return d if keep == 'below' else -d


def sd_union(*ds):
    return np.minimum.reduce(ds)


def sd_inter(*ds):
    return np.maximum.reduce(ds)


def ellipse_mask(h, w, cx, cy, rx, ry, angle=0.0, box=None):
    X, Y = _grid(h, w, box)
    return cov(sd_ellipse(X, Y, cx, cy, rx, ry, angle))


def place(full_shape, sub, box):
    out = np.zeros(full_shape, np.float32)
    x0, y0, x1, y1 = box
    out[y0:y1, x0:x1] = sub
    return out


def clipbox(box, h, w, pad=4):
    x0, y0, x1, y1 = box
    return (max(0, int(np.floor(x0)) - pad), max(0, int(np.floor(y0)) - pad),
            min(w, int(np.ceil(x1)) + pad), min(h, int(np.ceil(y1)) + pad))


# --------------------------------------------------------------------------- #
# edge sampling + robust fits
# --------------------------------------------------------------------------- #

def sample_bilinear(img, xs, ys):
    """Bilinear sample a float32 2-D image at arbitrary float coords (pixel-centre = i+0.5)."""
    mx = (np.asarray(xs, np.float32) - 0.5)
    my = (np.asarray(ys, np.float32) - 0.5)
    shp = mx.shape
    n = mx.size
    cols = 1024
    rows = -(-n // cols)
    fx = np.zeros(rows * cols, np.float32)
    fy = np.zeros(rows * cols, np.float32)
    fx[:n], fy[:n] = mx.ravel(), my.ravel()
    out = cv2.remap(np.ascontiguousarray(img, np.float32), fx.reshape(rows, cols), fy.reshape(rows, cols),
                    cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return out.ravel()[:n].reshape(shp)


def edge_offsets(img, pts, nrm, search, step=0.25, sign=0, smooth=1.0, prefer=None):
    """For each point/normal, find the sub-pixel offset t in [-search, search] of the
    strongest step along the normal (derivative of img sampled along the normal).
    sign=+1 wants img increasing along the normal, -1 decreasing, 0 either.
    Returns (offsets, strength)."""
    t = np.arange(-search, search + step / 2, step, dtype=np.float32)
    px = pts[:, 0:1] + nrm[:, 0:1] * t[None]
    py = pts[:, 1:2] + nrm[:, 1:2] * t[None]
    prof = sample_bilinear(img, px, py)
    if smooth:
        k = int(round(3 * smooth / step)) * 2 + 1
        prof = cv2.GaussianBlur(prof, (k, 1), smooth / step)
    d = np.gradient(prof, step, axis=1)
    s = d * sign if sign else np.abs(d)
    if prefer is not None:  # gaussian prior around 0 offset
        s = s * np.exp(-0.5 * (t / prefer) ** 2)[None]
    i = np.argmax(s, axis=1)
    # parabolic refinement
    i0 = np.clip(i, 1, len(t) - 2)
    a, b, c = s[np.arange(len(i0)), i0 - 1], s[np.arange(len(i0)), i0], s[np.arange(len(i0)), i0 + 1]
    den = a - 2 * b + c
    sub = np.where(np.abs(den) > 1e-9, 0.5 * (a - c) / den, 0)
    off = t[i0] + np.clip(sub, -1, 1) * step
    return off.astype(np.float32), s[np.arange(len(i)), i]


def fit_poly_robust(s, v, deg=2, iters=5, k=2.5):
    """Robust polynomial v = c0 + c1*s + c2*s^2 ... (coefficients low -> high order)."""
    s, v = np.asarray(s, np.float64), np.asarray(v, np.float64)
    m = np.ones(len(v), bool)
    for _ in range(iters):
        c = np.polynomial.polynomial.polyfit(s[m], v[m], deg)
        r = v - np.polynomial.polynomial.polyval(s, c)
        sd = 1.4826 * np.median(np.abs(r[m])) + 1e-6
        m = np.abs(r) < max(k * sd, 0.75)
    return [float(x) for x in c], float(np.sqrt(np.mean(r[m] ** 2))), m


def fit_line_x_of_y(ys, xs, iters=4, k=2.5):
    """Robust x = a + b*y fit (iteratively trimmed). Returns (a, b, resid_rms, inlier_mask)."""
    ys, xs = np.asarray(ys, np.float64), np.asarray(xs, np.float64)
    m = np.ones(len(xs), bool)
    for _ in range(iters):
        A = np.stack([np.ones(m.sum()), ys[m]], 1)
        coef, *_ = np.linalg.lstsq(A, xs[m], rcond=None)
        r = xs - (coef[0] + coef[1] * ys)
        s = 1.4826 * np.median(np.abs(r[m])) + 1e-6
        m = np.abs(r) < max(k * s, 0.75)
    rms = float(np.sqrt(np.mean(r[m] ** 2)))
    return float(coef[0]), float(coef[1]), rms, m


def fit_ellipse_aa(xs, ys, w=None):
    """Axis-aligned ellipse LSQ: A x^2 + C y^2 + D x + E y = 1 -> (cx, cy, rx, ry)."""
    x, y = np.asarray(xs, np.float64), np.asarray(ys, np.float64)
    mx, my = x.mean(), y.mean()
    x, y = x - mx, y - my
    M = np.stack([x * x, y * y, x, y, np.ones_like(x)], 1)
    if w is not None:
        M = M * w[:, None]
    # homogeneous: minimise |M p| with |p| = 1
    _, _, vt = np.linalg.svd(M, full_matrices=False)
    A, C, D, E, F = vt[-1]
    cx, cy = -D / (2 * A), -E / (2 * C)
    G = A * cx * cx + C * cy * cy - F
    return cx + mx, cy + my, float(np.sqrt(G / A)), float(np.sqrt(G / C))


def fit_ellipse_general(xs, ys):
    """General conic ellipse fit (cv2.fitEllipseDirect). Returns cx, cy, rx, ry, angle(deg)."""
    pts = np.stack([xs, ys], 1).astype(np.float32)
    (cx, cy), (d1, d2), ang = cv2.fitEllipseDirect(pts)
    return float(cx), float(cy), float(d1 / 2), float(d2 / 2), float(ang)


def ellipse_points(cx, cy, rx, ry, angle=0.0, t=None, n=720):
    if t is None:
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    a = np.deg2rad(angle)
    ca, sa = np.cos(a), np.sin(a)
    ex, ey = rx * np.cos(t), ry * np.sin(t)
    x = cx + ex * ca - ey * sa
    y = cy + ex * sa + ey * ca
    # outward normals
    nx, ny = np.cos(t) / rx, np.sin(t) / ry
    nxr, nyr = nx * ca - ny * sa, nx * sa + ny * ca
    nn = np.hypot(nxr, nyr)
    return np.stack([x, y], 1), np.stack([nxr / nn, nyr / nn], 1)


def ellipse_residual(xs, ys, cx, cy, rx, ry, angle=0.0):
    return sd_ellipse(np.asarray(xs, np.float32), np.asarray(ys, np.float32), cx, cy, rx, ry, angle)


def grad_images(L, sigma=1.5):
    """Gaussian-derivative gradients (gx, gy) of a float image."""
    Ls = cv2.GaussianBlur(L, (0, 0), sigma) if sigma else L
    gx = cv2.Sobel(Ls, cv2.CV_32F, 1, 0, ksize=3, scale=1 / 8)
    gy = cv2.Sobel(Ls, cv2.CV_32F, 0, 1, ksize=3, scale=1 / 8)
    return gx, gy


def contour_contrast(gx, gy, pts, nrm, sign=+1, offset=(0, 0), clip=None):
    """Mean signed derivative along normals (sign=+1: image brighter in +normal dir)."""
    x = pts[:, 0] - offset[0]
    y = pts[:, 1] - offset[1]
    d = sample_bilinear(gx, x, y) * nrm[:, 0] + sample_bilinear(gy, x, y) * nrm[:, 1]
    d = d * sign
    if clip is not None:
        d = np.clip(d, -clip, clip)
    return float(np.mean(d))


def refine_vertical_edge(L, x_seed, y0, y1, win=3.0, sign=0, sigma=0.7, ystep=2):
    """Row-wise sub-pixel step-edge search near x_seed, then robust line x = a + b*y.
    sign=+1: brighter to the right. Returns dict(a, b, rms, n, x_at(y))."""
    ys = np.arange(int(y0), int(y1), ystep, dtype=np.float32) + 0.5
    pts = np.stack([np.full_like(ys, x_seed), ys], 1)
    nrm = np.tile(np.array([[1.0, 0.0]], np.float32), (len(ys), 1))
    off, st = edge_offsets(L, pts, nrm, win, step=0.125, sign=sign, smooth=sigma)
    xs = x_seed + off
    a, b, rms, m = fit_line_x_of_y(ys, xs)
    return dict(a=a, b=b, rms=rms, n=int(m.sum()), frac=float(m.mean()))


def refine_horizontal_edge_curve(L, xs, y_seed, win, sign=0, sigma=0.8):
    """Column-wise sub-pixel step-edge search near y_seed(x) (array). Returns ys, strength."""
    pts = np.stack([xs, y_seed], 1).astype(np.float32)
    nrm = np.tile(np.array([[0.0, 1.0]], np.float32), (len(xs), 1))
    off, st = edge_offsets(L, pts, nrm, win, step=0.125, sign=sign, smooth=sigma)
    return y_seed + off, st


def pattern_search(score, p0, steps, scale=None):
    """Deterministic coordinate pattern search maximising score(p)."""
    p = np.array(p0, np.float64)
    sc = np.ones(len(p)) if scale is None else np.asarray(scale, np.float64)
    best = score(p)
    for st in steps:
        improved = True
        while improved:
            improved = False
            for k in range(len(p)):
                for d in (st, -st):
                    q = p.copy()
                    q[k] += d * sc[k]
                    s = score(q)
                    if s > best + 1e-7:
                        p, best, improved = q, s, True
    return p, best


def ransac_linear(F, y, tol=2.0, n_iter=400, seed=0, min_frac=0.2):
    """Robust y ~ F @ c (F: (n, p) design). Deterministic RANSAC + LSQ refit on inliers.
    Returns (c, inlier_mask, rms)."""
    rng = np.random.default_rng(seed)
    n, p = F.shape
    best_m, best_n = None, -1
    for _ in range(n_iter):
        idx = rng.choice(n, p, replace=False)
        try:
            c = np.linalg.solve(F[idx], y[idx])
        except np.linalg.LinAlgError:
            continue
        m = np.abs(F @ c - y) < tol
        if m.sum() > best_n:
            best_n, best_m = m.sum(), m
    m = best_m
    for _ in range(3):
        c, *_ = np.linalg.lstsq(F[m], y[m], rcond=None)
        m = np.abs(F @ c - y) < tol
    r = F @ c - y
    return c, m, float(np.sqrt(np.mean(r[m] ** 2)))


def arc_design(xs, xc, hw):
    u = (np.asarray(xs, np.float64) - xc) / hw
    return np.stack([np.ones_like(u), np.sqrt(np.clip(1 - u * u, 0, 1))], 1)


# --------------------------------------------------------------------------- #
# raster helpers
# --------------------------------------------------------------------------- #

def poly_coverage(polys, h, w, ss=4, box=None):
    """Anti-aliased coverage of polygon(s) (list of (N,2) float arrays, even-odd = union of
    outlines filled with fillPoly) by ss x ss supersampling inside box (x0,y0,x1,y1).
    Returns float32 (h, w) full-size array."""
    if box is None:
        allp = np.concatenate(polys, 0)
        box = clipbox((allp[:, 0].min(), allp[:, 1].min(), allp[:, 0].max(), allp[:, 1].max()), h, w, 3)
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    big = np.zeros((bh * ss, bw * ss), np.uint8)
    pts = [np.round((np.asarray(p, np.float64) - [x0, y0]) * ss * 16 - 8).astype(np.int32) for p in polys]
    cv2.fillPoly(big, pts, 1, lineType=cv2.LINE_8, shift=4)
    sub = big.reshape(bh, ss, bw, ss).mean((1, 3), dtype=np.float32)
    out = np.zeros((h, w), np.float32)
    out[y0:y1, x0:x1] = sub
    return out


def masked_mean(v, m, sigma):
    """Normalised Gaussian convolution: local mean of v over pixels where m."""
    m = m.astype(np.float32)
    num = cv2.GaussianBlur(v * m, (0, 0), sigma)
    den = cv2.GaussianBlur(m, (0, 0), sigma)
    return num / np.maximum(den, 1e-4), den


def unmix_matte(L, region, band=2.0, sigma=5.0, min_contrast=8.0):
    """Turn a binary region into a soft matte by local linear unmixing of luminance L in a
    narrow band around the region boundary (fg/bg levels estimated just inside/outside).
    Works on a crop; returns float32 alpha."""
    region = region.astype(bool)
    k = int(np.ceil(band)) * 2 + 1
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    inner = cv2.erode(region.astype(np.uint8), ker).astype(bool)
    outer = cv2.erode((~region).astype(np.uint8), ker).astype(bool)
    F, _ = masked_mean(L, inner, sigma)
    B, _ = masked_mean(L, outer, sigma)
    d = F - B
    al = np.where(np.abs(d) > min_contrast, (L - B) / np.where(np.abs(d) > 1e-3, d, 1), region.astype(np.float32))
    al = np.clip(al, 0, 1)
    alpha = region.astype(np.float32)
    bandm = ~(inner | outer)
    alpha[bandm] = al[bandm]
    return alpha.astype(np.float32)


def smooth_periodic_correction(t, off, order=6, w=None):
    """Least-squares fit of off(t) by sum_k c_k sin(k*pi*u), u = (t-t0)/(t1-t0) (zero at ends)."""
    u = (t - t.min()) / (t.max() - t.min())
    B = np.stack([np.sin(k * np.pi * u) for k in range(1, order + 1)], 1)
    if w is not None:
        c, *_ = np.linalg.lstsq(B * w[:, None], off * w, rcond=None)
    else:
        c, *_ = np.linalg.lstsq(B, off, rcond=None)
    return c


def eval_sin_series(c, u):
    return sum(ck * np.sin((k + 1) * np.pi * u) for k, ck in enumerate(c))


# =========================================================================== #
# 1. cabins_row.png — four arched fluted-oak cabin shells
# =========================================================================== #
# Seeds (x of vertical edges at mid height, crown y) were read off 4x zoom tiles;
# every one of them is refined automatically (row-wise sub-pixel edge search +
# robust line / ellipse fits) — they only pick WHICH edge is meant.
CAB_SEEDS = dict(
    inner=[(647.5, 1373.5), (2037.0, 2797.5), (3502.5, 4285.5), (4919.0, 5739.5)],   # front-face hole
    outer=[(632.5, 1388.5), (2020.5, 2814.5), (3485.5, 4302.0), (4900.5, 5756.5)],   # outer edge of frame
    reveal=[('L', 694.0), ('L', 2057.0), ('R', 4258.0), ('R', 5691.0)],               # back edge of jamb reveal
    crown_inner=[684, 661, 661, 663],
    crown_outer=[669.5, 645, 645, 649],
    shell=[(441.5, 1748.0), (1771.5, 3131.0), (3140.0, 4537.0), (4555.0, 5979.5)],
)


def _line_x(ln, y):
    return ln['a'] + ln['b'] * y


def _fit_arch_arc(L, gx, gy, lnL, lnR, crown_seed, sign, correct=True):
    """Fit the elliptical head of an arch whose jambs are the lines lnL / lnR:
    centre x and semi-axis rx follow from the jambs at the spring line, (spring_y, ry)
    maximise edge contrast; then a smooth sine-series normal correction (zero at the
    springs) takes up the small deviations of the AI-drawn curve from a true ellipse."""
    sy = crown_seed + 380
    t_fit = np.linspace(np.pi + 0.25, 2 * np.pi - 0.25, 300)
    for _ in range(3):
        xl, xr = _line_x(lnL, sy), _line_x(lnR, sy)
        cx, rx = (xl + xr) / 2, (xr - xl) / 2

        def sc(q):
            pts, nrm = ellipse_points(cx, q[0], rx, q[1], 0, t_fit)
            return contour_contrast(gx, gy, pts, nrm, sign, clip=25)
        best = None
        for f in (0.85, 0.95, 1.05):
            p, s = pattern_search(sc, (crown_seed + rx * f, rx * f), (4, 1, 0.25, 0.0625))
            if best is None or s > best[1]:
                best = (p, s)
        (sy, ry), score = best
    res = dict(cx=float(cx), spring_y=float(sy), rx=float(rx), ry=float(ry), crown_y=float(sy - ry),
               left_x=float(cx - rx), right_x=float(cx + rx), score=float(score), corr=[])
    t = np.linspace(np.pi + np.deg2rad(3), 2 * np.pi - np.deg2rad(3), 700)
    pts, nrm = ellipse_points(cx, sy, rx, ry, 0, t)
    off, st = edge_offsets(L, pts, nrm, 6, step=0.125, sign=sign, smooth=0.8)
    from scipy.ndimage import median_filter
    med = median_filter(off, 15, mode='nearest')
    ok = np.abs(off - med) < 1.0
    res['raw_resid_rms'] = float(np.sqrt(np.mean(off[ok] ** 2)))
    if correct:
        c = smooth_periodic_correction(t[ok], off[ok], order=8)
        u = (t - t.min()) / (t.max() - t.min())
        fitted = eval_sin_series(c, u)
        res['corr'] = [float(v) for v in c]
        res['corr_t'] = [float(t.min()), float(t.max())]
        res['resid_rms'] = float(np.sqrt(np.mean((off[ok] - fitted[ok]) ** 2)))
        res['max_corr'] = float(np.abs(fitted).max())
    return res


def arch_head_points(a, n=900):
    """Dense head outline (left spring -> crown -> right spring) incl. sine correction."""
    t = np.linspace(np.pi, 2 * np.pi, n)
    pts, nrm = ellipse_points(a['cx'], a['spring_y'], a['rx'], a['ry'], 0, t)
    if a.get('corr'):
        t0, t1 = a['corr_t']
        u = np.clip((t - t0) / (t1 - t0), 0, 1)
        d = eval_sin_series(a['corr'], u)
        pts = pts + nrm * d[:, None]
    return pts


def arc_y(c, xc, hw, x):
    u = (np.asarray(x, np.float64) - xc) / hw
    return c[0] + c[1] * np.sqrt(np.clip(1 - u * u, 0, 1))


def cabins_fit(save=True):
    a = load_src('cabins_row')
    L = gray(a)
    del a
    gx, gy = grad_images(L, 1.0)
    S = CAB_SEEDS
    lines = {}
    for i in range(4):
        for side, k in ((0, 'L'), (1, 'R')):
            lines[f'a{i}{k}'] = refine_vertical_edge(L, S['inner'][i][side], 1120, 1700, win=2.5)
            lines[f'o{i}{k}'] = refine_vertical_edge(L, S['outer'][i][side], 1120, 1700, win=2.5)
            lines[f's{i}{k}'] = refine_vertical_edge(L, S['shell'][i][side], 900, 2200, win=2.5)
        side, x = S['reveal'][i]
        lines[f'b{i}{side}'] = refine_vertical_edge(L, x, 1120, 1700, win=2.5)
    arches, frames, shells = [], [], []
    for i in range(4):
        arches.append(_fit_arch_arc(L, gx, gy, lines[f'a{i}L'], lines[f'a{i}R'], S['crown_inner'][i], +1))
        frames.append(_fit_arch_arc(L, gx, gy, lines[f'o{i}L'], lines[f'o{i}R'], S['crown_outer'][i], -1,
                                    correct=False))
    # floor line (bottom edge of the stainless kick plate) per shell: y = c0 + k*sqrt(1-u^2)
    floors = []
    for i in range(4):
        xl, xr = _line_x(lines[f's{i}L'], 2000), _line_x(lines[f's{i}R'], 2000)
        xc, hw = (xl + xr) / 2, (xr - xl) / 2
        al, ar = _line_x(lines[f'a{i}L'], 2400), _line_x(lines[f'a{i}R'], 2400)
        xs = np.arange(xl + 8, xr - 8, 1.0)
        xs = xs[(xs < al - 20) | (xs > ar + 20)]
        Fd = arc_design(xs, xc, hw)
        best = None
        for c0 in (2435, 2450, 2465):
            for k in (60, 80, 100):
                yf, _ = refine_horizontal_edge_curve(L, xs, c0 + k * Fd[:, 1], 14, sign=-1, sigma=1.2)
                cf, mf, rf = ransac_linear(Fd, yf, tol=1.2)
                if best is None or mf.sum() > best[1].sum():
                    best = (cf, mf, rf, yf)
        floors.append(dict(xc=xc, hw=hw, c=best[0].tolist(), inl=float(best[1].mean()), rms=best[2], xs=xs, ys=best[3]))
    ks = np.array([f['c'][1] for f in floors])
    kmed = float(np.median(ks))
    for f in floors:   # occluded shells: share the curvature, fit the level only
        if f['inl'] < 0.2 or abs(f['c'][1] - kmed) > 25:
            Fd = arc_design(f['xs'], f['xc'], f['hw'])
            c0, m, r = ransac_linear(np.ones((len(f['xs']), 1)), f['ys'] - kmed * Fd[:, 1], tol=1.2)
            f['c'] = [float(c0[0]), kmed]
            f['shared_k'] = True
    out = dict(lines=lines, arches=arches, frames=frames,
               floors=[{k: v for k, v in f.items() if k not in ('xs', 'ys')} for f in floors])
    if save:
        with open(os.path.join(SCRATCH, 'cabins_fit.json'), 'w') as fh:
            json.dump(out, fh, indent=1)
    return out


def drape_ceiling_alpha(rgb, y_max=640, b_min=40.0, br_min=0.27):
    """Soft matte of the festoon drapery band hanging from the top edge (cabins_row).
    Key: linen is the only surface with a high blue/red ratio (oak b/r ~0.1, gaps dark);
    the band is a height field from the top; edge alpha by blue-channel unmixing."""
    sub = rgb[:y_max].astype(np.float32)
    Ab = cv2.GaussianBlur(sub, (0, 0), 1.0)
    D = ((Ab[..., 2] > b_min) & (Ab[..., 2] > br_min * Ab[..., 0])).astype(np.uint8)
    n, lab = cv2.connectedComponents(D, connectivity=8)
    top = np.unique(lab[0][lab[0] > 0])
    C = np.isin(lab, top)
    hem = np.where(C.any(0), y_max - 1 - np.argmax(C[::-1], axis=0), -1)
    R = np.arange(y_max)[:, None] <= hem[None, :]
    al = unmix_matte(sub[..., 2], R, band=2.0, sigma=4.0)
    out = np.zeros(rgb.shape[:2], np.float32)
    out[:y_max] = al
    return out, hem


def unmix_matte_rgb(rgb, region, band=6, sigma=8.0, min_contrast=20.0):
    """RGB version of unmix_matte for soft (defocused) edges: alpha = projection of the
    pixel onto the local bg->fg colour axis inside a band around the binary boundary."""
    region = region.astype(bool)
    k = int(np.ceil(band)) * 2 + 1
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    inner = cv2.erode(region.astype(np.uint8), ker).astype(bool)
    outer = cv2.erode((~region).astype(np.uint8), ker).astype(bool)
    I = rgb.astype(np.float32)
    F = np.dstack([masked_mean(I[..., c], inner, sigma)[0] for c in range(3)])
    B = np.dstack([masked_mean(I[..., c], outer, sigma)[0] for c in range(3)])
    d = F - B
    dd = (d * d).sum(2)
    al = ((I - B) * d).sum(2) / np.maximum(dd, 1e-3)
    al = np.where(dd > min_contrast ** 2, np.clip(al, 0, 1), region.astype(np.float32))
    alpha = region.astype(np.float32)
    bandm = ~(inner | outer)
    alpha[bandm] = al[bandm]
    return alpha


# Hand-placed seeds for the defocused foreground of cabins_row (full-res px). FG seeds sit
# well inside each object, BG seeds on open floor / shells; GrabCut + colour unmixing find
# the actual (soft) silhouettes.
CAB_FG_SEEDS = dict(
    y0=2150,
    fg=[[(20, 2330), (460, 2300), (520, 2400), (560, 2688), (20, 2688)],            # beige chair L
        [(320, 2545), (1900, 2575), (1900, 2688), (320, 2688)],                      # table L
        [(770, 2390), (950, 2390), (950, 2688), (770, 2688)],                        # glasses L
        [(2310, 2480), (2610, 2460), (2640, 2688), (2310, 2688)],                    # leather chair
        [(2710, 2420), (2990, 2400), (3030, 2688), (2730, 2688)],                    # beige chair R
        [(3910, 2360), (3975, 2340), (4100, 2500), (4170, 2688), (3965, 2688), (3895, 2460)],  # chair diag
        [(4580, 2545), (6256, 2540), (6256, 2688), (4580, 2688)],                    # table R
        [(5205, 2340), (5285, 2340), (5285, 2540), (5205, 2540)],                    # glasses R
        [(5360, 2400), (5440, 2400), (5440, 2540), (5360, 2540)],
        [(5865, 2380), (5965, 2380), (5965, 2540), (5865, 2540)]],
    bg=[[(0, 2150), (6256, 2150), (6256, 2235), (0, 2235)],
        [(2000, 2300), (2180, 2300), (2180, 2630), (2000, 2630)],
        [(3120, 2300), (3840, 2300), (3840, 2688), (3120, 2688)],
        [(4120, 2400), (4470, 2400), (4470, 2688), (4280, 2688)],
        [(1380, 2380), (1740, 2380), (1740, 2450), (1380, 2450)],
        [(1790, 2400), (2030, 2400), (2030, 2470), (1790, 2470)],
        [(4300, 2300), (4470, 2300), (4470, 2460), (4300, 2460)],
        [(620, 2250), (2200, 2250), (2200, 2330), (620, 2330)],
        [(3100, 2250), (3860, 2250), (3860, 2330), (3100, 2330)],
        [(4250, 2250), (5150, 2250), (5150, 2330), (4250, 2330)]],
)


def cabins_foreground_alpha(rgb, seeds=CAB_FG_SEEDS, scale=0.5, iters=6):
    H, W = rgb.shape[:2]
    y0 = seeds['y0']
    sub = np.ascontiguousarray(rgb[y0:])
    h, w = sub.shape[:2]
    sw, sh = int(round(w * scale)), int(round(h * scale))
    small = cv2.resize(sub, (sw, sh), interpolation=cv2.INTER_AREA)
    mask = np.full((sh, sw), cv2.GC_PR_BGD, np.uint8)

    def poly_s(p):
        return np.round((np.array(p, np.float64) - [0, y0]) * scale).astype(np.int32)
    prf = np.zeros_like(mask)
    for p in seeds['fg']:
        cv2.fillPoly(prf, [poly_s(p)], 1)
    prf = cv2.dilate(prf, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    mask[prf > 0] = cv2.GC_PR_FGD
    for p in seeds['bg']:
        cv2.fillPoly(mask, [poly_s(p)], cv2.GC_BGD)
    for p in seeds['fg']:
        cv2.fillPoly(mask, [poly_s(p)], cv2.GC_FGD)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.setRNGSeed(7)
    cv2.grabCut(small, mask, None, bgd, fgd, iters, cv2.GC_INIT_WITH_MASK)
    fg = ((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)).astype(np.float32)
    big = cv2.resize(fg, (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
    # clean: drop specks, fill pinholes
    n, lab, st, _ = cv2.connectedComponentsWithStats(big.astype(np.uint8), connectivity=8)
    keep = np.zeros(n, bool)
    keep[1:] = st[1:, cv2.CC_STAT_AREA] > 4000
    big = keep[lab]
    inv = ~big
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv.astype(np.uint8), connectivity=4)
    small_holes = np.zeros(n, bool)
    small_holes[1:] = st[1:, cv2.CC_STAT_AREA] < 3000
    big = big | small_holes[lab]
    al = unmix_matte_rgb(sub, big, band=7, sigma=10.0)
    al = cv2.GaussianBlur(al, (0, 0), 1.2)   # defocused edges: suppress grain wobble
    out = np.zeros((H, W), np.float32)
    out[y0:] = al
    return out


def _shell_tops(L, hem, lines):
    """Visible top rim of each shell (dark gap above -> lit cap below), arc y = c0 + k*S."""
    tops = []
    for s in range(4):
        xl, xr = _line_x(lines[f's{s}L'], 600), _line_x(lines[f's{s}R'], 600)
        xc, hw = (xl + xr) / 2, (xr - xl) / 2
        xs = np.arange(int(xl) + 4, int(xr) - 4, 1)
        ok = np.array([hem[x] > 0 and L[hem[x] + 4:hem[x] + 9, x].mean() < 32 for x in xs])
        xs = xs[ok]
        ys, _ = refine_horizontal_edge_curve(L, xs + 0.5, hem[xs] + 44.0, 40, sign=+1, sigma=1.0)
        Fd = arc_design(xs + 0.5, xc, hw)
        c, m, r = ransac_linear(Fd, ys, tol=1.5)
        span = (xs[m].max() - xs[m].min()) if m.any() else 0
        tops.append(dict(xc=xc, hw=hw, c=[float(c[0]), float(c[1])], rms=r, n=int(m.sum()),
                         span=float(span), xs=xs + 0.5, ys=ys))
    wide = [t['c'][1] for t in tops if t['span'] > 1.4 * t['hw']]
    kmed = float(np.median(wide)) if wide else 0.0
    for t in tops:
        if t['span'] <= 1.4 * t['hw']:
            Fd = arc_design(t['xs'], t['xc'], t['hw'])
            c0, m, r = ransac_linear(np.ones((len(t['xs']), 1)), t['ys'] - kmed * Fd[:, 1], tol=1.5)
            t['c'] = [float(c0[0]), kmed]
            t['shared_k'] = True
            t['rms'] = r
        del t['xs'], t['ys']
    return tops


def shell_sd(X, Y, sh):
    """Signed distance (approx.) to the amodal shell outline: two jamb lines + top / floor arcs."""
    lnL, lnR, top, flo = sh['lineL'], sh['lineR'], sh['top'], sh['floor']
    dL = (lnL['a'] + lnL['b'] * Y) - X
    dR = X - (lnR['a'] + lnR['b'] * Y)
    ft = lambda x: arc_y(top['c'], top['xc'], top['hw'], x).astype(np.float32)
    ff = lambda x: arc_y(flo['c'], flo['xc'], flo['hw'], x).astype(np.float32)
    dT = sd_curve_y(X, Y, ft, keep='below')
    dF = sd_curve_y(X, Y, ff, keep='above')
    return sd_inter(dL, dR, dT, dF)


def arch_polygon(arch, lnL, lnR, floor, n=900):
    """Closed outline of an arch opening: jambs from the floor arc up to the spring line,
    corrected elliptical head, floor arc back."""
    head = arch_head_points(arch, n)
    sy = arch['spring_y']
    xl_f = _line_x(lnL, 2600)
    xr_f = _line_x(lnR, 2600)
    xs = np.linspace(xr_f, xl_f, 200)
    ys = arc_y(floor['c'], floor['xc'], floor['hw'], xs)
    # jamb x at the floor (iterate once for slope)
    yl = float(arc_y(floor['c'], floor['xc'], floor['hw'], [xl_f])[0])
    yr = float(arc_y(floor['c'], floor['xc'], floor['hw'], [xr_f])[0])
    pl = [(_line_x(lnL, yl), yl), (_line_x(lnL, sy), sy)]
    pr = [(_line_x(lnR, sy), sy), (_line_x(lnR, yr), yr)]
    xs = np.linspace(pr[-1][0], pl[0][0], 200)
    ys = arc_y(floor['c'], floor['xc'], floor['hw'], xs)
    poly = np.concatenate([np.array(pl), head[1:-1], np.array(pr), np.stack([xs, ys], 1)[1:-1]], 0)
    return poly, dict(bottom_left_y=yl, bottom_right_y=yr)


# --------------------------------------------------------------------------- #
# overlays / previews
# --------------------------------------------------------------------------- #

PALETTE = [(255, 40, 120), (0, 220, 255), (255, 200, 0), (120, 255, 60), (170, 90, 255),
           (255, 120, 0), (0, 120, 255), (255, 255, 255)]


def overlay(rgb, masks, colors=None, alpha=0.38, outline=True, scale=1.0, dim=0.0):
    """Translucent colour overlay of float masks + 1px outlines (at the 0.5 level).
    scale < 1 downsamples first (area) so it is cheap for previews."""
    if scale != 1.0:
        sz = (max(1, int(round(rgb.shape[1] * scale))), max(1, int(round(rgb.shape[0] * scale))))
        img = cv2.resize(rgb, sz, interpolation=cv2.INTER_AREA).astype(np.float32)
        masks = [cv2.resize(m, sz, interpolation=cv2.INTER_AREA) for m in masks]
    else:
        img = rgb.astype(np.float32).copy()
    if dim:
        img *= (1 - dim)
    colors = colors or PALETTE
    for i, m in enumerate(masks):
        c = np.array(colors[i % len(colors)], np.float32)
        a = (m * alpha)[..., None]
        img = img * (1 - a) + c * a
    if outline:
        for i, m in enumerate(masks):
            b = (m > 0.5).astype(np.uint8)
            e = cv2.morphologyEx(b, cv2.MORPH_GRADIENT, np.ones((2, 2), np.uint8)) > 0
            img[e] = colors[i % len(colors)]
    return np.clip(img, 0, 255).astype(np.uint8)


def save_jpg(arr, path, max_side=1600, quality=88):
    im = Image.fromarray(arr)
    s = max_side / max(im.size)
    if s < 1:
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.convert('RGB').save(path, quality=quality)
    return path


def crop_check(rgb, masks, box, path, zoom=2, colors=None, alpha=0.3):
    """100%+ crop with mask outlines drawn at native resolution then nearest-upscaled."""
    x0, y0, x1, y1 = [int(v) for v in box]
    sub = rgb[y0:y1, x0:x1]
    ms = [m[y0:y1, x0:x1] for m in masks]
    ov = overlay(sub, ms, colors, alpha=alpha)
    im = Image.fromarray(ov).resize(((x1 - x0) * zoom, (y1 - y0) * zoom), Image.NEAREST)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, quality=92)
    return path


INDEX = []


def _open_geo(name):
    d = P('assets', 'cut', 'geo', name)
    os.makedirs(d, exist_ok=True)
    return open(os.path.join(d, 'geometry.json'), 'w')


def _entry(rel, size, desc, use, anchors=None, **kw):
    e = dict(path=rel, size=list(size), description=desc, suggested_use=use)
    if anchors is not None:
        e['anchors'] = anchors
    e.update(kw)
    INDEX.append(e)
    return e


def _r(v, n=2):
    if isinstance(v, dict):
        return {k: _r(x, n) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_r(x, n) for x in v]
    if isinstance(v, (float, np.floating)):
        return round(float(v), n)
    if isinstance(v, np.integer):
        return int(v)
    return v


def build_cabins():
    name = 'cabins_row'
    rgb = load_src(name)
    H, W = rgb.shape[:2]
    L = gray(rgb)
    fit = cabins_fit(save=True)
    lines = fit['lines']
    ceil, hem = drape_ceiling_alpha(rgb)
    tops = _shell_tops(L, hem, lines)
    fg = cabins_foreground_alpha(rgb)
    rel = lambda f: f'assets/cut/geo/{name}/{f}'
    X, Y = _grid(H, W)
    shells_geo, arches_geo, meta_sh, meta_ar = [], [], [], []
    for i in range(4):
        sh = dict(lineL=lines[f's{i}L'], lineR=lines[f's{i}R'], top=tops[i], floor=fit['floors'][i])
        xl0, xr0 = _line_x(sh['lineL'], 1500), _line_x(sh['lineR'], 1500)
        box = clipbox((xl0 - 10, 250, xr0 + 10, 2650), H, W)
        Xb, Yb = _grid(H, W, box)
        sg = place((H, W), cov(shell_sd(Xb, Yb, sh)), box)
        shells_geo.append(sg)
        arch = fit['arches'][i]
        poly, bot = arch_polygon(arch, lines[f'a{i}L'], lines[f'a{i}R'], sh['floor'])
        ag = poly_coverage([poly], H, W, ss=4)
        arches_geo.append(ag)
        xc_t, hw_t = tops[i]['xc'], tops[i]['hw']
        meta_sh.append(dict(
            id=i + 1, left_x=xl0, right_x=xr0, centre_x=(xl0 + xr0) / 2,
            top_y=float(arc_y(tops[i]['c'], xc_t, hw_t, [xc_t])[0]),
            top_y_at_sides=tops[i]['c'][0],
            bottom_y=float(arc_y(sh['floor']['c'], sh['floor']['xc'], sh['floor']['hw'], [sh['floor']['xc']])[0]),
            bottom_y_at_sides=sh['floor']['c'][0],
            side_lines={'left': [lines[f's{i}L']['a'], lines[f's{i}L']['b']],
                        'right': [lines[f's{i}R']['a'], lines[f's{i}R']['b']], 'form': 'x = a + b*y'},
            top_arc={'c0': tops[i]['c'][0], 'k': tops[i]['c'][1], 'xc': xc_t, 'hw': hw_t,
                     'form': 'y = c0 + k*sqrt(1-((x-xc)/hw)^2)', 'shared_k': tops[i].get('shared_k', False),
                     'rms': tops[i]['rms']},
            bottom_arc={'c0': sh['floor']['c'][0], 'k': sh['floor']['c'][1], 'xc': sh['floor']['xc'],
                        'hw': sh['floor']['hw'], 'form': 'y = c0 + k*sqrt(1-((x-xc)/hw)^2)',
                        'note': 'floor line = bottom of stainless kick plate'}))
        fr = fit['frames'][i]
        side, _ = CAB_SEEDS['reveal'][i]
        rv = lines[f'b{i}{side}']
        meta_ar.append(dict(
            id=i + 1, left_x=arch['left_x'], right_x=arch['right_x'], centre_x=arch['cx'],
            spring_y=arch['spring_y'], crown_y=arch['crown_y'],
            bottom_y=float(arc_y(sh['floor']['c'], sh['floor']['xc'], sh['floor']['hw'], [arch['cx']])[0]),
            bottom_y_at_left_jamb=bot['bottom_left_y'], bottom_y_at_right_jamb=bot['bottom_right_y'],
            rx=arch['rx'], ry=arch['ry'],
            jamb_lines={'left': [lines[f'a{i}L']['a'], lines[f'a{i}L']['b']],
                        'right': [lines[f'a{i}R']['a'], lines[f'a{i}R']['b']], 'form': 'x = a + b*y'},
            head_correction={'coeffs': arch['corr'], 't_range': arch['corr_t'],
                             'form': 'normal offset d(t)=sum c_k sin(k*pi*u), u=(t-t0)/(t1-t0); '
                                     'ellipse point (cx+rx cos t, spring_y+ry sin t), t in [pi,2pi]',
                             'max_abs_px': arch['max_corr'], 'edge_resid_rms_px': arch['resid_rms'],
                             'pure_ellipse_resid_rms_px': arch['raw_resid_rms']},
            frame_outer={'left_x': fr['left_x'], 'right_x': fr['right_x'], 'crown_y': fr['crown_y'],
                         'spring_y': fr['spring_y'], 'note': 'outer edge of the smooth arch frame band'},
            reveal_back_edge={'side': side, 'x_at_y1400': _line_x(rv, 1400),
                              'note': 'visible jamb reveal (inside the opening) ends here'}))
    sum_shell = np.zeros((H, W), np.float32)
    for sg in shells_geo:
        sum_shell += sg
    sum_shell = np.clip(sum_shell, 0, 1)
    rem = (1 - fg) * (1 - ceil)
    ceil_vis = ceil * (1 - fg)
    back = rem * (1 - sum_shell)
    shells_vis = [sg * (1 - ag) * rem for sg, ag in zip(shells_geo, arches_geo)]
    arches_vis = [ag * rem for ag in arches_geo]
    for i in range(4):
        n = i + 1
        _entry(save_mask(shells_vis[i], rel(f'shell_{n}.png')), (W, H),
               f'cabin {n}: VISIBLE fluted-oak shell incl. smooth arch frame band and kick plate; opening, '
               'drapery and defocused foreground removed (partition layer)',
               'clip oak texture / colour washes to the visible shell', anchors=_r(meta_sh[i]))
        _entry(save_mask(shells_geo[i], rel(f'shell_{n}_geo.png')), (W, H),
               f'cabin {n}: AMODAL shell silhouette (parametric cylinder: 2 vertical lines + top/floor '
               'elliptical arcs), ignores occluders and the opening', 'rebuild / extend shells, shadows')
        _entry(save_mask(arches_vis[i], rel(f'arch_{n}.png')), (W, H),
               f'cabin {n}: VISIBLE arch opening = front-face hole (rect + elliptical head, inner edge of '
               'the arch frame) down to the floor line; includes the visible jamb reveal',
               'glow / colour intensity inside the cabin, place content behind the arch',
               anchors=_r(meta_ar[i]))
        _entry(save_mask(arches_geo[i], rel(f'arch_{n}_geo.png')), (W, H),
               f'cabin {n}: AMODAL arch opening (parametric, ignores foreground)', 'parametric cut-outs')
    _entry(save_mask(ceil_vis, rel('ceiling_band.png')), (W, H),
           'festoon drapery strip along the top (height field from y=0 to the scalloped hem), '
           'soft hem matte by blue-channel unmixing', 'separate / recolour the draped ceiling',
           anchors={'hem_y_min': int(hem.min()), 'hem_y_max': int(hem.max())})
    _entry(save_mask(fg, rel('foreground_band.png')), (W, H),
           'defocused foreground: chairs, two tables, glasses, candles (GrabCut from seed polygons + '
           'RGB colour-unmixing for the soft defocus edges)', 'keep foreground on top / blur / darken')
    _entry(save_mask(back, rel('back_wall.png')), (W, H),
           'everything else: gaps between and behind the cabins, side views into the restaurant, '
           'floor around the shells', 'background replacement / atmosphere fills')
    _entry(save_mask(np.clip(sum(shells_vis), 0, 1), rel('shells_all.png')), (W, H),
           'union of the 4 visible shells', 'one-shot shell selection')
    _entry(save_mask(np.clip(sum(arches_vis), 0, 1), rel('arches_all.png')), (W, H),
           'union of the 4 visible arch openings', 'one-shot opening selection')
    geo = dict(source=f'assets/gen/{name}.png', size=[W, H], arches=_r(meta_ar), shells=_r(meta_sh))
    with _open_geo(name) as fh:
        json.dump(geo, fh, indent=1)
    _entry(f'assets/cut/geo/{name}/geometry.json', (W, H), 'all fitted cabin parameters (JSON)',
           'parametric reconstruction', anchors=None)
    # previews
    parts = [ceil_vis, fg, back] + shells_vis + arches_vis
    cols = [(255, 255, 255), (60, 255, 120), (40, 80, 255)] + [(255, 150, 0)] * 4 + [(255, 0, 200)] * 4
    ov = overlay(rgb, parts, cols, alpha=0.35, scale=0.35)
    save_jpg(ov, os.path.join(PREV, 'cabins_overlay.jpg'))
    allm = [ceil_vis, fg] + shells_vis + arches_vis
    cc = [(255, 255, 255), (60, 255, 120)] + [(255, 150, 0)] * 4 + [(255, 0, 200)] * 4
    a0 = fit['arches'][0]
    crop_check(rgb, allm, (560, 620, 960, 1020), os.path.join(PREV, 'cab_c1_head.jpg'), 2, cc, 0.25)
    crop_check(rgb, allm, (1250, 900, 1450, 1100), os.path.join(PREV, 'cab_c2_spring.jpg'), 3, cc, 0.25)
    crop_check(rgb, allm, (1600, 280, 2000, 520), os.path.join(PREV, 'cab_c3_tops.jpg'), 2, cc, 0.25)
    crop_check(rgb, allm, (1700, 2250, 2300, 2600), os.path.join(PREV, 'cab_c4_base.jpg'), 2, cc, 0.25)
    crop_check(rgb, allm, (5550, 750, 5850, 1100), os.path.join(PREV, 'cab_c5_head4.jpg'), 2, cc, 0.25)
    return ov


def fit_ellipse5(gx, gy, init, sign, t=None, valid=None, scale=1.0, steps=(8, 4, 2, 1, 0.5, 0.25),
                 clip=25.0, fixed=()):
    """Contrast-maximising general ellipse fit (cx, cy, rx, ry, angle_deg) in full-res coords.
    gx/gy may be computed on an image downscaled by `scale`; `valid` (same grid) masks out
    occluded samples (e.g. tree). Normals point outward; sign=+1: brighter outside."""
    if t is None:
        t = np.linspace(0, 2 * np.pi, 1440, endpoint=False)
    p0 = np.array(init, np.float64)

    def score(p):
        pts, nrm = ellipse_points(p[0], p[1], p[2], p[3], p[4], t)
        q = pts * scale
        d = (sample_bilinear(gx, q[:, 0], q[:, 1]) * nrm[:, 0] + sample_bilinear(gy, q[:, 0], q[:, 1]) * nrm[:, 1])
        d = np.abs(d) if sign == 0 else d * sign
        d = np.clip(d, -clip, clip)
        if valid is not None:
            w = sample_bilinear(valid, q[:, 0], q[:, 1])
            inb = (q[:, 0] > 2) & (q[:, 1] > 2) & (q[:, 0] < gx.shape[1] - 2) & (q[:, 1] < gx.shape[0] - 2)
            w = w * inb
            return float((d * w).sum() / max(w.sum(), 1.0))
        return float(d.mean())
    p = p0.copy()
    best = score(p)
    for st in steps:
        improved = True
        while improved:
            improved = False
            for k in range(5):
                if k in fixed:
                    continue
                for dl in (st, -st):
                    q = p.copy()
                    q[k] += dl * (0.1 if k == 4 else 1.0)
                    s = score(q)
                    if s > best + 1e-7:
                        p, best, improved = q, s, True
    return p, best


# =========================================================================== #
# 2./3. void_lookup_B / void_lookup_A — concentric ring ellipses
# =========================================================================== #

def _tree_valid(rgb, dil=9):
    """1 where the pixel is NOT tree foliage / branches (used to ignore occluded edge samples)."""
    a = rgb.astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    L = 0.2126 * r + 0.7152 * g + 0.0722 * b
    tree = ((g - np.maximum(r, b)) > 6) | ((L < 90) & (b > r))
    tree = cv2.dilate(tree.astype(np.uint8), np.ones((dil, dil), np.uint8))
    return (1 - tree).astype(np.float32)


def fit_rings(name, seeds, windows=(10, 5)):
    """Refine each seed ellipse (cx, cy, rx, ry, angle) by dense edge tracing along its normals
    + robust general-ellipse fit at full resolution (tree-occluded samples ignored)."""
    rgb = load_src(name)
    L = gray(rgb)
    valid = _tree_valid(rgb)
    out = {}
    for k, (p0, sign) in seeds.items():
        if sign is None:      # keep the seed (hand-measured anchors), just report the edge agreement
            p, frac, rms = np.array(p0, np.float64), float('nan'), float('nan')
        else:
            p, frac, rms = trace_ellipse(L, p0, valid, windows=windows, sign=sign)
        out[k] = dict(cx=float(p[0]), cy=float(p[1]), rx=float(p[2]), ry=float(p[3]), angle=float(p[4]),
                      edge_inlier_fraction=frac, edge_rms_px=rms)
    return out


def ring_masks(shape, ells, order):
    """Nested coverages for ellipses listed outer -> inner; returns dict of insides (clamped so
    every inner ellipse lies inside the previous one)."""
    H, W = shape
    X, Y = _grid(H, W)
    ins = {}
    prev = None
    for k in order:
        e = ells[k]
        c = cov(sd_ellipse(X, Y, e['cx'], e['cy'], e['rx'], e['ry'], e['angle']))
        if prev is not None:
            c = np.minimum(c, prev)
        ins[k] = c
        prev = c
    return ins


VOID_B_SEEDS = {   # (cx, cy, rx, ry, angle), edge polarity (0 = either)
    'slab_outer': ((1824.69, 2152.26, 2359.64, 1870.09, -1.2), 0),    # white slab ring | ground-floor ceiling
    'rail_outer': ((1838.31, 2024.0, 1961.02, 1689.0, 0.21), None),  # slab edge (fixed: tracing unreliable)
    'rail_inner': ((1884.10, 1817.64, 1694.46, 1477.69, 0.0), 0),     # inner edge of the handrail tube
    'upper_slab': ((1845.34, 1568.52, 1542.72, 1236.51, -2.63), 0),   # outer edge of the upper white fascia ring
    'skylight': ((1773.56, 1170.55, 1011.78, 760.7, 6.47), 0),        # skylight glazing edge
}


def build_void_B():
    name = 'void_lookup_B'
    rgb = load_src(name)
    H, W = rgb.shape[:2]
    ells = fit_rings(name, VOID_B_SEEDS)
    order = ['slab_outer', 'rail_outer', 'rail_inner', 'upper_slab', 'skylight']
    ins = ring_masks((H, W), ells, order)
    rel = lambda f: f'assets/cut/geo/{name}/{f}'
    Ycoord = np.arange(H, dtype=np.float32)[:, None] + 0.5
    outside = 1 - ins['slab_outer']
    lower = outside * (Ycoord > ells['slab_outer']['cy'])
    masks = {
        'skylight_glazing': (ins['skylight'], 'skylight glazing: everything inside the innermost ring '
                             '(glazing + mullions + sky; the tree canopy in front is included)'),
        'upper_slab_ring': (ins['upper_slab'] - ins['skylight'], 'white fascia of the upper slab + inner '
                            'rail + skylight well wall (between upper slab edge and glazing)'),
        'upper_floor_annulus': (ins['rail_inner'] - ins['upper_slab'], 'first-floor annulus between the '
                                'stainless handrail and the upper slab edge: curtains, pendants, dining'),
        'rail_band': (ins['rail_outer'] - ins['rail_inner'], 'stainless rail ring band: handrail tube + '
                      'balusters, from the slab edge to the inner edge of the handrail'),
        'slab_underside_ring': (ins['slab_outer'] - ins['rail_outer'], 'white underside/edge of the '
                                'first-floor slab ringing the void'),
        'outside_ceiling': (outside, 'everything outside the slab ring (ground-floor ceiling, walls, '
                            'lower part of the image)'),
        'lower_part': (lower, 'ground-floor zone below the slab ring (outside the slab ellipse, below '
                       'its centre line)'),
    }
    for k, (m, d) in masks.items():
        _entry(save_mask(np.clip(m, 0, 1), rel(f'{k}.png')), (W, H), d,
               'clip colour planes / textures per ring; the rings are concentric depth layers')
    E = {k: _r(dict(centre=[v['cx'], v['cy']], axes=[v['rx'], v['ry']], angle_deg=v['angle'],
                    form='semi-axes rx (along angle) / ry, angle clockwise in image coords',
                    edge_inlier_fraction=v['edge_inlier_fraction'], edge_rms_px=v['edge_rms_px']))
         for k, v in ells.items()}
    with _open_geo(name) as fh:
        json.dump(dict(source=f'assets/gen/{name}.png', size=[W, H], ellipses=E,
                       order_outer_to_inner=order), fh, indent=1)
    _entry(rel('geometry.json'), (W, H), 'fitted ring ellipses (centre, semi-axes, angle)',
           'parametric rings / sound-ring graphics aligned to the void', anchors=E)
    parts = [masks[k][0] for k in ('skylight_glazing', 'upper_slab_ring', 'upper_floor_annulus',
                                   'rail_band', 'slab_underside_ring', 'outside_ceiling')]
    cols = [(0, 200, 255), (255, 255, 255), (255, 150, 0), (255, 0, 160), (120, 255, 60), (60, 60, 255)]
    ov = overlay(rgb, parts, cols, alpha=0.3, scale=0.35)
    save_jpg(ov, os.path.join(PREV, 'voidB_overlay.jpg'))
    for i, (x, y) in enumerate([(130, 1700), (1800, 300), (1800, 3150), (3450, 1750), (800, 700)]):
        crop_check(rgb, parts, (max(0, x - 150), max(0, y - 150), min(W, x + 150), min(H, y + 150)),
                   os.path.join(PREV, f'vb_c{i}.jpg'), 2, cols, 0.22)
    return ov


def trace_ellipse(L, p, valid=None, windows=(25, 12, 6), sign=0, tol=2.5, n=1440, sigma=1.0, seed=0):
    """Dense edge tracing around an ellipse: per-angle strongest step within +-window along the
    normal, then robust (iteratively trimmed) general-ellipse fit; repeated with shrinking
    windows. Returns (params, inlier_fraction, rms)."""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    p = np.array(p, np.float64)
    frac, rms = 0.0, 0.0
    for win in windows:
        pts, nrm = ellipse_points(*p, t=t)
        inb = (pts[:, 0] > win + 3) & (pts[:, 1] > win + 3) & (pts[:, 0] < L.shape[1] - win - 3) & \
              (pts[:, 1] < L.shape[0] - win - 3)
        if valid is not None:
            inb &= sample_bilinear(valid, pts[:, 0], pts[:, 1]) > 0.99
        off, st = edge_offsets(L, pts[inb], nrm[inb], win, step=0.25, sign=sign, smooth=sigma)
        q = pts[inb] + nrm[inb] * off[:, None]
        m = np.ones(len(q), bool)
        for _ in range(6):
            (cx, cy), (d1, d2), ang = cv2.fitEllipseDirect(q[m].astype(np.float32))
            pp = np.array([cx, cy, d1 / 2, d2 / 2, ang])
            if abs(pp[4]) > 45:
                pp = np.array([cx, cy, d2 / 2, d1 / 2, ang - 90])
            r = sd_ellipse(q[:, 0], q[:, 1], *pp)
            m = np.abs(r) < tol
        p = pp
        frac, rms = float(m.mean()), float(np.sqrt(np.mean(r[m] ** 2)))
    return p, frac, rms


VOID_A_SEEDS = {
    'collar_outer': ((1936.0, 1369.9, 1515.7, 1131.2, -0.8), 0),    # outer edge of the white slab collar
    'collar_inner': ((1924.5, 1303.9, 1368.1, 1064.4, 0.1), 0),     # opening edge = foot of upper balusters
    'upper_handrail': ((1850.0, 1180.0, 1121.0, 880.0, 0.0), 0),    # inner edge of the upper handrail
}
# first-floor rail: only its near (lower) arc is visible and the wide-angle lens bends it away
# from an ellipse -> traced as smooth curves y(x). Anchors (x, y) read off column profiles.
VOID_A_FF_ANCHORS = {
    'ff_handrail_top': [(150, 2478), (300, 2576), (600, 2680), (900, 2769), (1300, 2868), (2500, 2893),
                        (3000, 2765), (3300, 2661), (3400, 2625), (3550, 2562)],
    'ff_slab_edge': [(150, 3080), (600, 3170), (1300, 3276), (2500, 3292), (3300, 3170), (3550, 3123)],
}


def _anchor_curve(L, anchors, valid, win=6, sign=+1, step=2, dark_above=None):
    """Column-wise sub-pixel edge trace (+-win px around a natural cubic spline through the
    anchors; sign +1 = brighter below), robust smoothing spline. Returns (xs, ys, rms, frac)."""
    from scipy.interpolate import CubicSpline, UnivariateSpline
    H, W = L.shape
    an = np.asarray(anchors, np.float64)
    xs = np.arange(1, W - 1, step, dtype=np.float64) + 0.5
    prior = CubicSpline(an[:, 0], an[:, 1], bc_type='natural')(xs)
    ys, _ = refine_horizontal_edge_curve(L, xs.astype(np.float32), prior.astype(np.float32), win, sign=sign,
                                         sigma=1.0)
    ok = sample_bilinear(valid, xs, ys) > 0.99
    if dark_above is not None:     # only trust columns with a dark background above the edge
        above = np.mean([sample_bilinear(L, xs, ys - d) for d in range(6, 26, 4)], 0)
        ok &= above < dark_above
    x_, y_ = xs[ok], ys[ok].astype(np.float64)
    w = np.ones_like(x_)
    for _ in range(6):
        spl = UnivariateSpline(x_, y_, w=w, s=w.sum() * 1.5 ** 2)
        r = y_ - spl(x_)
        sd = 1.4826 * np.median(np.abs(r[w > 0.5])) + 0.3
        w = np.where(np.abs(r) < 2.5 * sd, 1.0, 0.01)
    xd = np.arange(0, W + 1, 1.0)
    return xd, spl(xd), float(np.sqrt(np.mean(r[w > 0.5] ** 2))), float((w > 0.5).mean())


def build_void_A():
    name = 'void_lookup_A'
    rgb = load_src(name)
    H, W = rgb.shape[:2]
    L = gray(rgb)
    ells = fit_rings(name, VOID_A_SEEDS, windows=(6, 3))
    ins = ring_masks((H, W), ells, ['collar_outer', 'collar_inner', 'upper_handrail'])
    curves, dense = {}, {}
    valid = _tree_valid(rgb)
    for k, an in VOID_A_FF_ANCHORS.items():
        xd, yd, rms, frac = _anchor_curve(L, an, valid, dark_above=100.0 if 'handrail' in k else None)
        dense[k] = (xd, yd)
        curves[k] = dict(y_every_16px=[[float(x), round(float(y), 2)] for x, y in zip(xd[::16], yd[::16])],
                         edge_rms_px=rms, inlier_fraction=frac, anchors=an)
    X, Y = _grid(H, W)
    yh = lambda x: np.interp(x, *dense['ff_handrail_top']).astype(np.float32)
    ys = lambda x: np.interp(x, *dense['ff_slab_edge']).astype(np.float32)
    band = cov(sd_inter(sd_curve_y(X, Y, yh, keep='below'), sd_curve_y(X, Y, ys, keep='above')))
    band = band * (1 - ins['collar_outer'])
    rel = lambda f: f'assets/cut/geo/{name}/{f}'
    masks = {
        'opening': (ins['collar_inner'], 'the round opening: everything inside the slab edge of the upper '
                    'void (upper rail, upper floor, skylight, tree canopy in front included)'),
        'opening_beyond_rail': (ins['upper_handrail'], 'inside the upper handrail: skylight + upper level '
                                'seen through the rail'),
        'upper_rail_band': (ins['collar_inner'] - ins['upper_handrail'], 'upper stainless rail ellipse band '
                            '(foot of balusters -> inner edge of handrail)'),
        'collar_ring': (ins['collar_outer'] - ins['collar_inner'], 'white slab collar ringing the opening'),
        'first_floor_rail_band': (band, 'first-floor stainless balustrade band: top of the handrail -> '
                                  'top of the white slab fascia (incl. bottom rail + base strip), near arc'),
    }
    for k, (m, d) in masks.items():
        _entry(save_mask(np.clip(m, 0, 1), rel(f'{k}.png')), (W, H), d,
               'clip colour/light planes to the void levels; ring graphics aligned to the opening')
    E = {k: _r(dict(centre=[v['cx'], v['cy']], axes=[v['rx'], v['ry']], angle_deg=v['angle'],
                    edge_rms_px=v['edge_rms_px'])) for k, v in ells.items()}
    E.update({k: _r(v, 2) for k, v in curves.items()})
    with _open_geo(name) as fh:
        json.dump(dict(source=f'assets/gen/{name}.png', size=[W, H], rings=E), fh, indent=1)
    _entry(rel('geometry.json'), (W, H), 'fitted ellipses (opening/collar/upper handrail) + first-floor '
           'rail curves', 'parametric overlays', anchors=E)
    parts = [masks[k][0] for k in ('opening_beyond_rail', 'upper_rail_band', 'collar_ring', 'first_floor_rail_band')]
    cols = [(0, 200, 255), (255, 0, 160), (120, 255, 60), (255, 150, 0)]
    ov = overlay(rgb, parts, cols, alpha=0.3, scale=0.35)
    save_jpg(ov, os.path.join(PREV, 'voidA_overlay.jpg'))
    for i, (x, y) in enumerate([(500, 1400), (1900, 2400), (150, 2700), (1300, 2870), (1300, 3270)]):
        crop_check(rgb, parts, (max(0, x - 150), max(0, y - 150), min(W, x + 150), min(H, y + 150)),
                   os.path.join(PREV, f'va_c{i}.jpg'), 2, cols, 0.22)
    return ov


# =========================================================================== #
# 4. glassblock_wall_A — mortar grid
# =========================================================================== #
GB_SEEDS = dict(v=[271, 875, 1462, 1976, 2382, 2762, 3153, 3566, 4154],   # vertical joint centres
                h=[781, 1180, 1859, 2500, 2754],                          # horizontal joint centres
                right_edge=4708, top_edge=30, bottom_edge=3220)           # perimeter block edges


def _plateau(m, c, search=30, wmin=12, wmax=40):
    """Flat mortar plateau near index c in a 1-D profile -> (left_edge, right_edge) sub-pixel."""
    best = None
    n = len(m)
    for cc in range(max(8, c - search), min(n - 8, c + search)):
        M = np.median(m[cc - 5:cc + 6])
        tol = max(5.0, 0.045 * M)
        if np.abs(m[cc - 5:cc + 6] - M).max() > tol:
            continue
        a = cc
        while a - 1 >= 0 and abs(m[a - 1] - M) < tol:
            a -= 1
        b = cc
        while b + 1 < n and abs(m[b + 1] - M) < tol:
            b += 1
        w = b - a + 1
        if w < wmin or w > wmax or a - 1 < 0 or b + 1 >= n:
            continue
        sc = min(abs(m[a - 1] - M), abs(m[b + 1] - M)) / tol + 0.02 * w
        if best is None or sc > best[2]:
            # sub-pixel: half-way crossing between plateau level and the outside neighbour
            def cross(i_in, i_out):
                v_in, v_out = m[i_in], m[i_out]
                half = (M + v_out) / 2
                if abs(v_in - v_out) < 1e-6:
                    return (i_in + i_out) / 2
                return i_in + (half - v_in) / (v_out - v_in) * (i_out - i_in)
            best = (cross(a, a - 1) + 0.5, cross(b, b + 1) + 0.5, sc)
    return best


def _joint_lines(L, c, axis, step=48, win=96, lo=0, hi=None):
    """Per-chunk plateau edges of a mortar joint (axis=0: vertical joint, profiles along x),
    robust line fits for both edges: pos = a + b*s (s = coordinate along the joint)."""
    hi = hi or (L.shape[0] if axis == 0 else L.shape[1])
    S, A, B = [], [], []
    for s0 in range(lo, hi - win + 1, step):
        prof = L[s0:s0 + win].mean(0) if axis == 0 else L[:, s0:s0 + win].mean(1)
        r = _plateau(prof, c)
        if r:
            S.append(s0 + win / 2)
            A.append(r[0])
            B.append(r[1])
    S, A, B = map(np.array, (S, A, B))
    ca, ra, ma = fit_poly_robust(S, A, 2, k=2.0)
    cb, rb, mb = fit_poly_robust(S, B, 2, k=2.0)
    return dict(e0=ca, e1=cb, rms=[ra, rb], n=int(len(S)), inl=[float(ma.mean()), float(mb.mean())])


def _single_edge_line(L, c, axis, sign, win=8, step=24, chunk=48):
    """Strongest step edge near c (axis=0: vertical line) per chunk, robust line fit."""
    n_along = L.shape[0] if axis == 0 else L.shape[1]
    S, E = [], []
    for s0 in range(0, n_along - chunk + 1, step):
        prof = L[s0:s0 + chunk].mean(0) if axis == 0 else L[:, s0:s0 + chunk].mean(1)
        seg = cv2.GaussianBlur(prof.astype(np.float32).reshape(1, -1), (0, 0), 0.8).ravel()
        d = np.gradient(seg)
        lo, hi = max(1, int(c - win)), min(len(seg) - 2, int(c + win))
        dd = d[lo:hi] * (sign if sign else 1)
        dd = np.abs(dd) if sign == 0 else dd
        i = int(np.argmax(dd)) + lo
        a, b, cc = d[i - 1] * (sign or 1), d[i] * (sign or 1), d[i + 1] * (sign or 1)
        den = a - 2 * b + cc
        sub = 0.5 * (a - cc) / den if abs(den) > 1e-9 else 0
        S.append(s0 + chunk / 2)
        E.append(i + np.clip(sub, -1, 1) + 0.5)
    c, rms, m = fit_poly_robust(np.array(S), np.array(E), 2, k=2.0)
    return dict(e=c, rms=rms, inl=float(m.mean()))


def glassblock_fit():
    rgb = load_src('glassblock_wall_A')
    L = rgb.astype(np.float32).mean(2)
    S = GB_SEEDS
    vj = [_joint_lines(L, c, 0, hi=3200) for c in S['v']]
    hj = [_joint_lines(L, c, 1) for c in S['h']]
    right = _single_edge_line(L, S['right_edge'], 0, 0)
    top = _single_edge_line(L, S['top_edge'], 1, 0)
    bottom = _single_edge_line(L, S['bottom_edge'], 1, 0)
    return dict(v=vj, h=hj, right=right, top=top, bottom=bottom)


def _pv(c, s):
    return np.polynomial.polynomial.polyval(s, c)


def build_glassblock(corner_r=6.0):
    name = 'glassblock_wall_A'
    rgb = load_src(name)
    H, W = rgb.shape[:2]
    f = glassblock_fit()
    with open(os.path.join(SCRATCH, 'gb_fit.json'), 'w') as fh:
        json.dump(f, fh, indent=1)
    # column bounds (functions of y) and row bounds (functions of x)
    xl = [lambda y: np.zeros_like(y)] + [lambda y, c=j['e1']: _pv(c, y) for j in f['v']]
    xr = [lambda y, c=j['e0']: _pv(c, y) for j in f['v']] + [lambda y, c=f['right']['e']: _pv(c, y)]
    yt = [lambda x, c=f['top']['e']: _pv(c, x)] + [lambda x, c=j['e1']: _pv(c, x) for j in f['h']]
    yb = [lambda x, c=j['e0']: _pv(c, x) for j in f['h']] + [lambda x, c=f['bottom']['e']: _pv(c, x)]
    ncol, nrow = len(xl), len(yt)
    X, Y = _grid(H, W)
    X = np.broadcast_to(X, (H, W))
    Y = np.broadcast_to(Y, (H, W))
    blocks_cov = np.zeros((H, W), np.float32)
    label = np.zeros((H, W), np.uint16)
    blocks = []
    bid = 0
    for r in range(nrow):
        for c in range(ncol):
            bid += 1
            # bounding box from corner estimates
            ys_mid = np.array([0.0, H / 2, H], np.float64)
            x0 = float(np.min(xl[c](ys_mid))) - 2
            x1 = float(np.max(xr[c](ys_mid))) + 2
            xs_mid = np.array([max(0, x0), (x0 + x1) / 2, min(W, x1)])
            y0 = float(np.min(yt[r](xs_mid))) - 2
            y1 = float(np.max(yb[r](xs_mid))) + 2
            box = clipbox((x0, y0, x1, y1), H, W, 2)
            bx0, by0, bx1, by1 = box
            Xb, Yb = X[by0:by1, bx0:bx1], Y[by0:by1, bx0:bx1]
            dx = np.maximum(xl[c](Yb) - Xb, Xb - xr[c](Yb))
            dy = np.maximum(yt[r](Xb) - Yb, Yb - yb[r](Xb))
            if c == 0:   # partial blocks cut by the image's left edge: no rounding there
                dx = Xb - xr[c](Yb)
            rr = corner_r
            qx, qy = dx + rr, dy + rr
            sd = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) + np.minimum(np.maximum(qx, qy), 0) - rr
            cv_ = cov(sd)
            blocks_cov[by0:by1, bx0:bx1] = np.maximum(blocks_cov[by0:by1, bx0:bx1], cv_)
            sub = label[by0:by1, bx0:bx1]
            sub[cv_ >= 0.5] = bid
            # corners (intersections) for JSON
            def corner(fx, fy):
                yv = fy(np.array([0.0]))[0] if False else None
                x = W / 2
                y = 0.0
                for _ in range(6):   # alternate projections (lines are near axis-aligned)
                    y = float(fy(np.array([x]))[0])
                    x = float(fx(np.array([y]))[0])
                return [round(x, 2), round(y, 2)]
            tl = corner(xl[c], yt[r]); tr = corner(xr[c], yt[r])
            br = corner(xr[c], yb[r]); bl = corner(xl[c], yb[r])
            blocks.append(dict(id=bid, row=r, col=c, tl=tl, tr=tr, br=br, bl=bl,
                               rect=[round(min(tl[0], bl[0]), 2), round(min(tl[1], tr[1]), 2),
                                     round(max(tr[0], br[0]), 2), round(max(bl[1], br[1]), 2)],
                               partial=(c == 0)))
    # wall extent: down to the bottom mortar line (bottom block edge + half a joint)
    hw = float(np.median([np.mean(np.array(_pv(j['e1'], W / 2)) - np.array(_pv(j['e0'], W / 2))) for j in f['h']]))
    vw = float(np.median([_pv(j['e1'], H / 2) - _pv(j['e0'], H / 2) for j in f['v']]))
    wall_bottom = lambda x: _pv(f['bottom']['e'], x) + 7.0
    Yc = np.arange(H, dtype=np.float32)[:, None] + 0.5
    Xc = np.arange(W, dtype=np.float32)[None, :] + 0.5
    wall = cov(sd_curve_y(Xc, Yc, lambda x: wall_bottom(x).astype(np.float32), keep='above'))
    mortar = np.clip(wall - blocks_cov, 0, 1)
    base = 1 - wall
    rel = lambda fn: f'assets/cut/geo/{name}/{fn}'
    vj = [dict(x_left=_r(_pv(j['e0'], H / 2)), x_right=_r(_pv(j['e1'], H / 2)),
               x_centre=_r((_pv(j['e0'], H / 2) + _pv(j['e1'], H / 2)) / 2),
               width=_r(_pv(j['e1'], H / 2) - _pv(j['e0'], H / 2)),
               left_edge_poly=_r(j['e0'], 8), right_edge_poly=_r(j['e1'], 8), rms_px=_r(j['rms'])) for j in f['v']]
    hj = [dict(y_top=_r(_pv(j['e0'], W / 2)), y_bottom=_r(_pv(j['e1'], W / 2)),
               y_centre=_r((_pv(j['e0'], W / 2) + _pv(j['e1'], W / 2)) / 2),
               width=_r(_pv(j['e1'], W / 2) - _pv(j['e0'], W / 2)),
               top_edge_poly=_r(j['e0'], 8), bottom_edge_poly=_r(j['e1'], 8), rms_px=_r(j['rms'])) for j in f['h']]
    geo = dict(source=f'assets/gen/{name}.png', size=[W, H],
               note='edge polys: value = c0 + c1*s + c2*s^2 with s = y (vertical joints) or x (horizontal); '
                    'vertical-joint x / horizontal-joint y quoted at the image centre line',
               vertical_joints=vj, horizontal_joints=hj,
               perimeter=dict(top_block_edge_poly=_r(f['top']['e'], 8), right_block_edge_poly=_r(f['right']['e'], 8),
                              bottom_block_edge_poly=_r(f['bottom']['e'], 8),
                              wall_bottom_y_at_centre=_r(float(wall_bottom(np.array([W / 2]))[0]))),
               joint_width_px=dict(vertical_median=_r(vw), horizontal_median=_r(hw)),
               block_corner_radius_px=corner_r, grid=dict(cols=ncol, rows=nrow),
               blocks=blocks)
    with _open_geo(name) as fh:
        json.dump(geo, fh, indent=1)
    _entry(save_mask(mortar, rel('mortar.png')), (W, H),
           'mortar grid (joints + top/right perimeter strips), anti-aliased, rounded block corners (r=%g px)' % corner_r,
           'tint / emboss the mortar, separate glass from joints',
           anchors=dict(vertical_joint_centres_x=[v['x_centre'] for v in vj],
                        horizontal_joint_centres_y=[h['y_centre'] for h in hj],
                        joint_width_px=geo['joint_width_px']))
    _entry(save_mask(blocks_cov, rel('glass_blocks.png')), (W, H), 'all glass block faces (complement of mortar inside the wall)',
           'clip refraction / colour plays to the glass')
    _entry(save_mask(base, rel('base_sill.png')), (W, H), 'below the wall: grey frame + terrazzo sill',
           'separate the sill')
    _entry(save_label16(label, rel('block_labels.png')), (W, H),
           '16-bit label map: 0 = mortar / non-glass, n = block id (row-major, row 0 at top, col 0 at left; '
           'see geometry.json blocks[])', 'per-block colour variation / animation, picking single blocks',
           anchors=dict(n_blocks=len(blocks), rows=nrow, cols=ncol))
    _entry(rel('geometry.json'), (W, H), 'joint lines (x / y, widths, edge polynomials) + every block rectangle '
           '(4 corners + axis-aligned rect)', 'rebuild the grid procedurally at any scale')
    # previews
    lab8 = (label.astype(np.int32) * 37 % 200 + 55).astype(np.uint8)
    lab8[label == 0] = 0
    ov = overlay(rgb, [mortar], [(255, 0, 140)], alpha=0.45, scale=0.33)
    save_jpg(ov, os.path.join(PREV, 'glassblock_overlay.jpg'))
    save_jpg(cv2.applyColorMap(cv2.resize(lab8, None, fx=0.33, fy=0.33, interpolation=cv2.INTER_NEAREST),
                               cv2.COLORMAP_JET)[..., ::-1], os.path.join(PREV, 'glassblock_labels.jpg'))
    for i, (x, y) in enumerate([(1462, 1180), (4154, 2754), (271, 781), (4700, 3220), (2382, 30)]):
        crop_check(rgb, [mortar], (max(0, x - 60), max(0, y - 60), min(W, x + 60), min(H, y + 60)),
                   os.path.join(PREV, f'gb_c{i}.jpg'), 4, [(255, 0, 140)], 0.25)
    return ov


# =========================================================================== #
# 5. festoon_valance — swag valance fabric
# =========================================================================== #
FV = dict(
    y0=150, y1=2500, scale=1 / 3.,
    fg_rects=[(450, 330, 6150, 560), (200, 700, 330, 1700), (170, 1700, 300, 2250), (6020, 700, 6140, 1700),
              (3640, 1000, 3720, 1250), (130, 1300, 180, 2200), (6000, 1900, 6120, 2300),
              (5895, 1400, 5925, 1900), (6150, 2330, 6172, 2368), (5886, 1960, 5900, 1995),
              (3738, 1035, 3768, 1105), (3790, 900, 3860, 1000)] + [(xc - 60, 600, xc + 60, 850) for xc in
                                           (680, 1330, 2000, 2680, 3350, 4230, 5090, 5730)],
    prfg_rects=[(140, 290, 6200, 1000), (100, 1000, 440, 2450), (5860, 1000, 6200, 2420)],
    bg_rects=[(500, 1400, 3550, 2450), (3850, 1400, 5850, 2450), (0, 150, 6256, 255), (0, 300, 100, 2450),
              (6200, 300, 6256, 2500), (5850, 2035, 5958, 2500), (5965, 2260, 6040, 2500),
              (6040, 2345, 6120, 2500), (5850, 2425, 6256, 2500)],
    swag_x=(430, 5990),        # hem traced between the side tails
    cords_x=(1580, 4760),      # pendant cords cross the valance here
    # hem key points read off a 0.3x preview: gather (cusp) x/y and swag-bottom y; refined by DP
    gathers=[(430, 1080), (993, 705), (1662, 705), (2340, 705), (3012, 705), (3683, 720), (3880, 767),
             (4762, 817), (5415, 717), (5990, 1050)],
    bottoms=[1100, 1073, 1060, 1060, 1040, None, 1000, 1060, 1060],
    # explicit hem key points (read off 1:1 crops) where the sine prior is not good enough
    hem_keys=[
        [(430, 1030), (445, 1035), (480, 1052), (510, 1068), (560, 1092), (610, 1106), (670, 1112),
         (720, 1108)],                                                            # swag 1, left half
        [(3885, 742), (3900, 745), (3950, 775), (4000, 808), (4050, 835), (4100, 855), (4140, 868),
         (4180, 900), (4220, 940), (4260, 975), (4300, 1005), (4350, 1040), (4400, 1050), (4450, 1052),
         (4510, 1048), (4570, 1030), (4630, 1005), (4680, 970), (4720, 920), (4740, 880), (4755, 835),
         (4762, 817)],                                                            # big asymmetric swag
        [(5415, 717), (5430, 830), (5460, 920), (5500, 980), (5550, 1020), (5600, 1045), (5660, 1057),
         (5720, 1057), (5780, 1050), (5830, 1035), (5880, 1015), (5920, 990), (5945, 960), (5960, 940),
         (5990, 920)],                                                            # last swag
    ],
    hem_fixed=[(3683, 3885)],    # hem hidden behind the jabot: keep the straight prior, no tracing
    jabot_x=(3590, 3890),
)


def _dp_path(cost, max_step):
    """Minimum-cost left->right path through cost[y, x] with |dy| <= max_step per column."""
    h, w = cost.shape
    acc = cost[:, 0].copy()
    back = np.zeros((h, w), np.int16)
    big = 1e9
    for x in range(1, w):
        best = np.full(h, big, np.float64)
        arg = np.zeros(h, np.int16)
        for d in range(-max_step, max_step + 1):
            sh = np.roll(acc, d)
            if d > 0:
                sh[:d] = big
            elif d < 0:
                sh[d:] = big
            pen = sh + 0.35 * abs(d)
            m = pen < best
            best[m] = pen[m]
            arg[m] = d
        acc = best + cost[:, x]
        back[:, x] = arg
    y = np.zeros(w, np.int32)
    y[-1] = int(np.argmin(acc))
    for x in range(w - 1, 0, -1):
        y[x - 1] = y[x] - back[y[x], x]
    return y


def fabric_wall_probability(rgb_sub, train_fab, train_wall):
    """P(fabric) per pixel from class-conditional histograms of (chroma r-b, chroma g-b, weave
    texture energy, luminance) learnt on the two training masks (histogram back-projection)."""
    a = rgb_sub.astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    S = r + g + b + 1
    L = a.mean(2)
    hp = L - cv2.GaussianBlur(L, (0, 0), 1.5)
    T = np.sqrt(cv2.GaussianBlur(hp * hp, (0, 0), 3))
    feats = [(cv2.GaussianBlur((r - b) / S, (0, 0), 2), 0.0, 0.45, 40),
             (cv2.GaussianBlur((g - b) / S, (0, 0), 2), 0.0, 0.3, 30),
             (T, 0.0, 12.0, 6), (cv2.GaussianBlur(L, (0, 0), 2), 40.0, 250.0, 8)]
    idx = np.zeros(L.shape, np.int64)
    N = 1
    for v, lo, hi, n in feats:
        idx = idx * n + np.clip(((v - lo) / (hi - lo) * n).astype(np.int64), 0, n - 1)
        N *= n
    Hf = np.bincount(idx[train_fab], minlength=N).astype(np.float64) + 0.5
    Hw = np.bincount(idx[train_wall], minlength=N).astype(np.float64) + 0.5
    Hf /= Hf.sum()
    Hw /= Hw.sum()
    pf = (Hf / (Hf + Hw))[idx].astype(np.float32)
    return cv2.GaussianBlur(pf, (0, 0), 2)


def _hem_from_classifier(rgb, cols, prior, y0=600, y1=1300, margin=45, corridor=45):
    """Hem = boundary minimising (#non-fabric above + #fabric below) per column, smooth DP path
    inside a corridor around the prior."""
    x0, x1 = int(cols[0]), int(cols[-1]) + 1
    sub = rgb[y0:y1, x0:x1]
    pr = prior - y0
    yy = np.arange(y1 - y0)[:, None]
    fab = (yy < pr[None, :] - margin) & (yy > 60)
    wal = yy > pr[None, :] + margin
    pf = fabric_wall_probability(sub, fab, wal)
    above = np.cumsum(1 - pf, axis=0)
    below = np.cumsum(pf[::-1], axis=0)[::-1]
    cost = above + below - pf
    dist = np.abs(yy - pr[None, :])
    cost = cost + 1e4 * (dist > corridor)
    path = _dp_path(cost.astype(np.float64), 6)
    hem = path.astype(np.float32) + y0 + 0.5
    return hem, pf


def valance_fit():
    rgb = load_src('festoon_valance')
    H, W = rgb.shape[:2]
    y0, y1, sc = FV['y0'], FV['y1'], FV['scale']
    sub = np.ascontiguousarray(rgb[y0:y1])
    sm = cv2.resize(sub, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    mask = np.full(sm.shape[:2], cv2.GC_PR_BGD, np.uint8)

    def R(r, v):
        x0, ya, x1, yb = r
        mask[int((ya - y0) * sc):int((yb - y0) * sc), int(x0 * sc):int(x1 * sc)] = v
    for r in FV['prfg_rects']:
        R(r, cv2.GC_PR_FGD)
    for r in FV['fg_rects']:
        R(r, cv2.GC_FGD)
    for r in FV['bg_rects']:
        R(r, cv2.GC_BGD)
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.setRNGSeed(3)
    cv2.grabCut(sm, mask, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    fg_s = ((mask == 1) | (mask == 3)).astype(np.float32)
    fg = np.zeros((H, W), bool)
    fg[y0:y1] = cv2.resize(fg_s, (W, y1 - y0), interpolation=cv2.INTER_LINEAR) > 0.5
    L = gray(rgb)
    # --- top edge: cove-light strip above, fabric below (straight line) ---
    xs = np.arange(200, W - 200, 8, dtype=np.float32) + 0.5
    yt, st = refine_horizontal_edge_curve(L, xs, np.full(len(xs), 285.0, np.float32), 20, sign=0, sigma=1.0)
    ct, rt, mt = fit_poly_robust(xs, yt, 1, k=2.0)
    # --- hem: DP along the darker-above / lighter-below edge near the GrabCut boundary ---
    xa, xb = FV['swag_x']
    cols = np.arange(xa, xb)
    from scipy.ndimage import median_filter
    prior = np.zeros(len(cols), np.float32)
    G_, B_ = FV['gathers'], FV['bottoms']
    for i in range(len(G_) - 1):
        (xa_, ya_), (xb_, yb_) = G_[i], G_[i + 1]
        m = (cols >= xa_) & (cols <= xb_)
        u = (cols[m] - xa_) / (xb_ - xa_)
        base = ya_ + (yb_ - ya_) * u
        if B_[i] is None:
            prior[m] = base
        else:
            prior[m] = base + (B_[i] - (ya_ + yb_) / 2) * np.sin(np.pi * u) ** 0.6
    from scipy.interpolate import PchipInterpolator
    for keys in FV['hem_keys']:
        k = np.array(keys, np.float64)
        m = (cols >= k[0, 0]) & (cols <= k[-1, 0])
        prior[m] = PchipInterpolator(k[:, 0], k[:, 1])(cols[m])
    for (fa, fb) in FV['hem_fixed']:
        m = (cols >= fa) & (cols <= fb)
        prior[m] = np.interp(cols[m], [fa, fb], [prior[cols >= fa][0], prior[cols <= fb][-1]])
    hem, pf = _hem_from_classifier(rgb, cols, prior)
    for (fa, fb) in FV['hem_fixed']:
        m = (cols >= fa) & (cols <= fb)
        hem[m] = prior[m]
    return dict(fg=fg, top=ct, top_rms=rt, hem_x=cols, hem_y=hem, prior=prior)


def fit_cord(L, xc, y0, y1, search=20):
    """Thin dark vertical cord near x=xc between rows y0..y1: sub-pixel centre per row (dark
    dip), robust line x = a + b*y, width = FWHM of the aligned mean profile."""
    ys = np.arange(y0, y1, 2)
    Ls = cv2.GaussianBlur(L[y0:y1, xc - search - 8:xc + search + 8], (0, 0), 0.8)
    prof = Ls[::2]
    i = np.argmin(prof[:, 8:-8], axis=1) + 8
    r_ = np.arange(len(i))
    a_, b_, c_ = prof[r_, i - 1], prof[r_, i], prof[r_, i + 1]
    den = a_ - 2 * b_ + c_
    sub = np.where(np.abs(den) > 1e-6, 0.5 * (a_ - c_) / den, 0)
    xs = xc - search - 8 + i + np.clip(sub, -1, 1) + 0.5
    a, b, rms, m = fit_line_x_of_y(ys + 0.5, xs)
    # aligned profile -> FWHM
    t = np.arange(-12, 12.01, 0.25)
    yy = ys[m][::4] + 0.5
    px = (a + b * yy)[:, None] + t[None]
    pr = sample_bilinear(L, px, np.repeat(yy[:, None], len(t), 1)).mean(0)
    base = np.median(np.r_[pr[:8], pr[-8:]])
    dip = pr.min()
    half = (base + dip) / 2
    below = t[pr < half]
    width = float(below.max() - below.min() + 0.25) if len(below) else 4.0
    return dict(a=a, b=b, rms=rms, width=width, y0=y0, y1=y1)


def cord_coverage(H, W, c):
    x0 = int(min(c['a'] + c['b'] * c['y0'], c['a'] + c['b'] * c['y1'])) - 10
    x1 = int(max(c['a'] + c['b'] * c['y0'], c['a'] + c['b'] * c['y1'])) + 10
    box = (max(0, x0), c['y0'], min(W, x1), c['y1'])
    X, Y = _grid(H, W, box)
    d = np.abs(X - (c['a'] + c['b'] * Y)) / np.sqrt(1 + c['b'] ** 2) - c['width'] / 2
    return place((H, W), cov(d), box)


def grabcut_refine(rgb, region, pad=40, band=14, iters=4, seed=5, smooth=3.0):
    """Full-resolution GrabCut in a narrow band around a coarse region (crop only), then a
    smoothed, lightly anti-aliased float matte."""
    H, W = region.shape
    b = bbox_bool(region)
    x0, y0, x1, y1 = max(0, b[0] - pad), max(0, b[1] - pad), min(W, b[2] + pad), min(H, b[3] + pad)
    R = region[y0:y1, x0:x1].astype(np.uint8)
    ker = lambda k: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))
    m = np.full(R.shape, cv2.GC_PR_BGD, np.uint8)
    m[R > 0] = cv2.GC_PR_FGD
    m[cv2.erode(R, ker(band)) > 0] = cv2.GC_FGD
    m[cv2.erode(1 - R, ker(band)) > 0] = cv2.GC_BGD
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.setRNGSeed(seed)
    cv2.grabCut(np.ascontiguousarray(rgb[y0:y1, x0:x1]), m, None, bgd, fgd, iters, cv2.GC_INIT_WITH_MASK)
    lab = ((m == 1) | (m == 3)).astype(np.uint8)
    lab = cv2.morphologyEx(lab, cv2.MORPH_OPEN, ker(2))
    lab = cv2.morphologyEx(lab, cv2.MORPH_CLOSE, ker(4))
    # fill holes
    inv = (1 - lab).astype(np.uint8)
    n, cc, st, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    border = np.unique(np.r_[cc[0], cc[-1], cc[:, 0], cc[:, -1]])
    hole = ~np.isin(cc, border) & (inv > 0)
    lab[hole] = 1
    a = cv2.GaussianBlur(lab.astype(np.float32), (0, 0), smooth)
    a = np.clip((a - 0.5) * 0.8 * smooth + 0.5, 0, 1)   # smooth contour, ~1.5 px soft edge
    out = np.zeros((H, W), np.float32)
    out[y0:y1, x0:x1] = a
    return out


def bbox_bool(m):
    ys = np.nonzero(m.any(1))[0]
    xs = np.nonzero(m.any(0))[0]
    if not len(xs):
        return None
    return int(xs[0]), int(ys[0]), int(xs[-1]) + 1, int(ys[-1]) + 1


def build_valance():
    from scipy.interpolate import UnivariateSpline
    name = 'festoon_valance'
    rgb = load_src(name)
    H, W = rgb.shape[:2]
    f = valance_fit()
    cols, hem = f['hem_x'].astype(np.float64) + 0.5, f['hem_y'].astype(np.float64)
    # refine gather (cusp) x as the local minimum of the traced hem near each seed
    gx_ = []
    for (xg, _) in FV['gathers']:
        m = np.abs(cols - xg) < 40
        gx_.append(float(cols[m][np.argmin(hem[m])]) if m.any() and 430 < xg < 5990 else float(xg))
    # smooth spline per swag (pinned at the cusps -> sharp gathers survive)
    smooth = hem.copy()
    for i in range(len(gx_) - 1):
        m = (cols >= gx_[i]) & (cols <= gx_[i + 1])
        if m.sum() < 20:
            continue
        x_, y_ = cols[m], hem[m]
        w = np.ones_like(x_)
        w[[0, -1]] = 50.0
        for _ in range(5):   # robust re-weighting
            spl = UnivariateSpline(x_, y_, w=w, s=float(w[1:-1].sum()) * 2.2 ** 2)
            r = y_ - spl(x_)
            sd = 1.4826 * np.median(np.abs(r)) + 0.3
            w = np.where(np.abs(r) < 2.0 * sd, 1.0, 0.02)
            w[[0, -1]] = 50.0
        smooth[m] = spl(x_)
    top_c = f['top']
    X, Y = _grid(H, W)
    hem_f = lambda x: np.interp(x, cols, smooth).astype(np.float32)
    top_f = lambda x: (top_c[0] + top_c[1] * x).astype(np.float32)
    xa, xb = FV['swag_x']
    box = (int(xa), 0, int(xb), 1400)
    Xb, Yb = _grid(H, W, box)
    sd = sd_inter(sd_curve_y(Xb, Yb, top_f, keep='below'), sd_curve_y(Xb, Yb, hem_f, keep='above'))
    swag = place((H, W), cov(sd), box)
    # tails (left, right) + middle jabot from GrabCut, colour-unmixed soft edges
    fg = f['fg']
    tails = np.zeros((H, W), bool)
    tails[:, :xa + 40] = fg[:, :xa + 40]
    tails[:, xb - 120:] = fg[:, xb - 120:]
    ja, jb = FV['jabot_x']
    jm = np.zeros((H, W), bool)
    jm[:1500, ja:jb] = fg[:1500, ja:jb]
    tails |= jm
    tails[:int(top_c[0])] = False
    n, lab, st, _ = cv2.connectedComponentsWithStats(tails.astype(np.uint8), connectivity=8)
    keep = np.zeros(n, bool)
    keep[1:] = st[1:, cv2.CC_STAT_AREA] > 5000
    tails = keep[lab]
    tails = cv2.morphologyEx(tails.astype(np.uint8), cv2.MORPH_CLOSE,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))).astype(bool)
    ta = np.zeros((H, W), np.float32)
    n, lab = cv2.connectedComponents(tails.astype(np.uint8), connectivity=8)
    for k in range(1, n):          # each tail / the jabot separately at full resolution
        ta = np.maximum(ta, grabcut_refine(rgb, lab == k))
    fabric = np.maximum(swag, ta)
    fabric[:int(np.floor(top_c[0]))] = 0
    # pendant cords in front of the fabric: fitted straight lines with measured width
    L = gray(rgb)
    cords = []
    cord = np.zeros((H, W), np.float32)
    for xc in FV['cords_x']:
        c = fit_cord(L, xc, int(top_c[0]) - 40, 1500)
        cords.append(c)
        cord = np.maximum(cord, cord_coverage(H, W, c))
    fabric = fabric * (1 - cord)
    rel = lambda fn: f'assets/cut/geo/{name}/{fn}'
    xs16 = np.arange(xa, xb + 1, 16, dtype=np.float64)
    hem16 = [[float(x), round(float(np.interp(x, cols, smooth)), 2)] for x in xs16]
    geo = dict(source=f'assets/gen/{name}.png', size=[W, H],
               top_edge=dict(y_at_x0=_r(top_c[0]), slope=_r(top_c[1], 8), rms_px=_r(f['top_rms'])),
               gather_x=_r(gx_[1:-1]), swag_span_x=[xa, xb], tail_left_x=[130, xa], tail_right_x=[xb, 6190],
               jabot_x=list(FV['jabot_x']), hem_every_16px=hem16,
               pendant_cords=[_r(c, 6) for c in cords],
               note='hem: lowest fabric edge (DP edge trace, then a robust smoothing spline per swag pinned at '
                    'the gathers). Tails / jabot outline from GrabCut + colour unmixing.')
    with _open_geo(name) as fh:
        json.dump(geo, fh, indent=1)
    _entry(save_mask(fabric, rel('valance_fabric.png')), (W, H),
           'swag valance fabric only: straight top edge, scalloped hem, side tails, middle jabot tail; '
           'plaster wall, pendants and their cords excluded',
           'cut the linen valance out as a layer (hem anchors in geometry.json)',
           anchors=dict(top_y=_r(top_c[0]), gather_x=_r(gx_[1:-1]),
                        hem_lowest_y=_r(float(smooth.max()))))
    _entry(rel('geometry.json'), (W, H), 'valance top line, gather x, hem curve every 16 px',
           'redraw festoon outlines / align line work')
    ov = overlay(rgb, [fabric], [(255, 0, 140)], alpha=0.35, scale=0.3)
    save_jpg(ov, os.path.join(PREV, 'valance_overlay.jpg'), 1880)
    for i, (x, y) in enumerate([(700, 1080), (1662, 720), (3700, 1150), (4300, 960), (300, 1500), (6080, 1400), (1580, 600)]):
        crop_check(rgb, [fabric], (max(0, x - 120), max(0, y - 120), min(W, x + 120), min(H, y + 120)),
                   os.path.join(PREV, f'fv_c{i}.jpg'), 2, [(255, 0, 140)], 0.2)
    return ov


# =========================================================================== #
# 6. ceiling_lookup_A / _B — black pendant lamps + cords
# =========================================================================== #
CEIL = {
    'ceiling_lookup_A': dict(thr=40.0, open_k=9, min_area=600, min_thick=8.0,
                             exclude_pts=[(2210, 975), (4790, 1155), (4590, 2500), (225, 2750),
                                          (4787, 2905), (5150, 2930), (1430, 2980), (680, 2980),
                                          (4890, 2995)],
                             # lamps merged with the dark window band: (seed x, y, ROI box)
                             extra_seeds=[(400, 2760, (258, 2640, 495, 2858), False),
                                          (1700, 3030, (1630, 2950, 1770, 3072), True)],
                             vp=(2726.5, -7320.7), vp_tol_deg=6.0, max_cord_angle=35.0),
    # B: the black gaps between the swags are as dark as the shades -> seeded lamps only
    'ceiling_lookup_B': dict(thr=40.0, open_k=9, min_area=600, min_thick=8.0, seeds_only=True,
                             exclude_pts=[],
                             extra_seeds=[(1857, 2560, (1720, 2430, 1990, 2700)),
                                          (3132, 2470, (2995, 2360, 3270, 2620)),
                                          (4381, 2430, (4240, 2290, 4525, 2570)),
                                          (3389, 2840, (3290, 2750, 3485, 2940)),
                                          (4201, 2800, (4105, 2715, 4300, 2910)),
                                          (3648, 2930, (3585, 2865, 3715, 3000)),
                                          (4307, 2965, (4230, 2890, 4390, 3045)),
                                          (1390, 3040, (1335, 2985, 1450, 3072)),
                                          (2070, 3010, (1990, 2940, 2155, 3072)),
                                          (2702, 3030, (2645, 2975, 2765, 3072)),
                                          (980, 2950, (900, 2860, 1060, 3005))],
                             vp=(2811.0, -6754.0), vp_tol_deg=6.0, max_cord_angle=35.0, symmetrize=True),
}


def _lamp_cores(L, cfg, seeds=None):
    Lb = cv2.GaussianBlur(L, (0, 0), 1.0)
    D = (Lb < cfg['thr']).astype(np.uint8)
    k = cfg['open_k']
    Do = cv2.morphologyEx(D, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    dt = cv2.distanceTransform(Do, cv2.DIST_L2, 5)
    n, lab, st, cen = cv2.connectedComponentsWithStats(Do, connectivity=8)
    import scipy.ndimage as ndi
    thick = ndi.maximum(dt, lab, index=np.arange(n))
    H, W = L.shape
    keep = []
    for i in range(1, n):
        x, y, w, h, ar = st[i]
        if seeds is not None:
            if not any(x <= sx < x + w and y <= sy < y + h and lab[sy, sx] == i for sx, sy in seeds):
                continue
        else:
            if ar < cfg['min_area'] or thick[i] < cfg['min_thick']:
                continue
            if y + h >= H - 2 or w > 600 or h > 600:     # window frames / beams touching the bottom
                continue
            if any(x <= ex < x + w and y <= ey < y + h for ex, ey in cfg['exclude_pts']):
                continue
        keep.append(i)
    return lab, st, keep, Lb


def capsule_coverage(H, W, c, extra=0.0):
    x0, y0, x1, y1 = c['x0'], c['y0'], c['x1'], c['y1']
    box = clipbox((min(x0, x1) - 10, min(y0, y1) - 10, max(x0, x1) + 10, max(y0, y1) + 10), H, W)
    X, Y = _grid(H, W, box)
    dx, dy = x1 - x0, y1 - y0
    l2 = dx * dx + dy * dy
    tt = np.clip(((X - x0) * dx + (Y - y0) * dy) / l2, 0, 1)
    d = np.hypot(X - (x0 + tt * dx), Y - (y0 + tt * dy)) - (c['width'] / 2 + extra)
    return place((H, W), cov(d), box)


def _symmetrize_core(core, Lb, thr, tilt_deg=0.0):
    """Remove dark clutter behind a seeded lamp (black gaps between the swags run sideways
    out of the ROI). Per row and per side the dark run from the lamp axis is measured; a side
    whose run reaches the ROI border is contaminated and its extent is interpolated from the
    nearest clean rows. Rows with a bright centre (bulb / bowl) use the outer edges of the
    nearest dark runs. Returns the lamp silhouette (filled between the side extents)."""
    h, w = core.shape
    rows = np.nonzero(core.any(1))[0]
    if len(rows) < 5:
        return core
    y_top = rows[0]
    mids = []
    for y in rows[:15]:
        xs = np.nonzero(core[y])[0]
        mids.append((xs.min() + xs.max()) / 2)
    x_top = float(np.median(mids))
    ta = np.tan(np.deg2rad(tilt_deg))
    dark = (Lb < thr + 15) | core
    E = np.full((h, 2), np.nan)          # left / right extent from the axis
    clean = np.zeros((h, 2), bool)
    for y in range(rows[0], rows[-1] + 1):
        xi = int(round(x_top + ta * (y - y_top)))
        if not (1 <= xi < w - 1):
            continue
        row = dark[y]
        for k, seq in enumerate((row[:xi + 1][::-1], row[xi:])):
            if not seq.any():
                continue
            s0 = int(np.argmax(seq))            # 0 when the axis pixel itself is dark
            if s0 > 0.45 * len(seq) + 5:
                continue
            rest = seq[s0:]
            ext = s0 + (int(np.argmin(rest)) if not rest.all() else len(rest))
            E[y, k] = ext
            clean[y, k] = ext < len(seq) - 1
    # per side: rows whose dark run reaches the ROI border are contaminated (swag gaps) and
    # interpolated from clean rows; a side may not exceed 1.35x the other side; small dips
    # (highlights) repaired; non-decreasing from the top down to the rim row (bell shape)
    from scipy.ndimage import median_filter
    ys = np.arange(h)
    Ec = np.where(clean, E, np.nan)
    for k in range(2):
        ok = np.isfinite(Ec[:, k])
        if ok.sum() < 3:
            return core
        rng = (ys >= ys[ok][0]) & (ys <= ys[ok][-1])
        Ec[rng & ~ok, k] = np.interp(ys[rng & ~ok], ys[ok], Ec[ok, k])
    in_rows = (ys >= rows[0]) & (ys <= rows[-1])
    for k in range(2):      # one side unknown (contaminated to the end): mirror the other side
        miss = in_rows & ~np.isfinite(Ec[:, k]) & np.isfinite(Ec[:, 1 - k])
        Ec[miss, k] = Ec[miss, 1 - k]
    both = np.isfinite(Ec).all(1)
    if both.sum() < 5:
        return core
    Ec[both, 0] = np.minimum(Ec[both, 0], 1.35 * Ec[both, 1] + 3)
    Ec[both, 1] = np.minimum(Ec[both, 1], 1.35 * Ec[both, 0] + 3)
    yv = ys[both]
    tot = np.where(both, Ec[:, 0] + Ec[:, 1], 0.0)
    lower = yv[yv >= yv[0] + 0.45 * (yv[-1] - yv[0])]
    y_rim = int(lower[np.argmax(median_filter(tot, 5, mode='nearest')[lower])])
    Em = np.zeros((h, 2))
    for k in range(2):
        v = np.where(both, Ec[:, k], 0.0)
        med = median_filter(v, 9, mode='nearest')
        v = np.where(both & (v < 0.7 * med), med, v)
        Em[:, k] = v
        for y in range(y_rim - 1, yv[0] - 1, -1):
            Em[y, k] = min(v[y], Em[y + 1, k]) if both[y] else Em[y + 1, k]
        cap = Em[y_rim, k] * 1.05 + 1
        Em[y_rim + 1:, k] = np.minimum(v[y_rim + 1:], cap)
    Em[~both] = 0
    X = np.arange(w)[None, :] + 0.5
    xa = (x_top + ta * (ys - y_top))[:, None] + 0.5
    env = (X >= xa - Em[:, 0:1] - 0.5) & (X <= xa + Em[:, 1:2] + 0.5) & (Em.min(1)[:, None] > 0)
    return env


def _lamp_matte(L, Lb, core, thr, grow=True):
    """Soft matte of one pendant: dark shade (core + thin attached dark details) with the
    enclosed lit bowl filled in; outer edge by luminance unmixing (dark shade vs. fabric)."""
    import scipy.ndimage as ndi
    ker = lambda k: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))
    near = cv2.dilate(core.astype(np.uint8), ker(8 if grow else 1)).astype(bool)
    cy_ = np.nonzero(core.any(1))[0]
    cx_ = np.nonzero(core.any(0))[0]
    near[int(cy_[-1] + 0.12 * (cx_[-1] - cx_[0]) + 3):] = False   # no growth far below the shade
    dark = Lb < thr + 25
    region = core | (near & dark)
    region = cv2.morphologyEx(region.astype(np.uint8), cv2.MORPH_CLOSE, ker(3)).astype(bool)
    filled = ndi.binary_fill_holes(region)
    bowl = filled & ~region
    # drop small bright specks that are not a bowl; keep the bowl (largest hole) only
    if bowl.any():
        n, lab_, st_, _ = cv2.connectedComponentsWithStats(bowl.astype(np.uint8), connectivity=4)
        big = 1 + int(np.argmax(st_[1:, cv2.CC_STAT_AREA]))
        keep = np.zeros(n, bool)
        keep[big] = True
        keep[1:] |= st_[1:, cv2.CC_STAT_AREA] < 60      # pinholes inside the shade
        bowl = keep[lab_] & bowl
    full = region | bowl
    inner = cv2.erode(full.astype(np.uint8), ker(2)).astype(bool)
    outer = cv2.erode((~full).astype(np.uint8), ker(2)).astype(bool)
    Fd, _ = masked_mean(L, inner & dark, 5.0)
    B, _ = masked_mean(L, outer, 5.0)
    d = Fd - B
    al = np.clip((L - B) / np.where(np.abs(d) > 1e-3, d, -1e-3), 0, 1)
    al = np.where(np.abs(d) > 25, al, full.astype(np.float32))
    alpha = full.astype(np.float32)
    band = ~(inner | outer)
    alpha[band] = al[band]
    # bowl pixels never lose opacity; the band only softens the outer silhouette
    alpha[bowl & ~cv2.dilate(outer.astype(np.uint8), ker(1)).astype(bool)] = 1.0
    alpha = np.maximum(cv2.GaussianBlur(alpha, (0, 0), 0.7), (inner & full).astype(np.float32))
    info = dict(enclosed_bowl_px=int(bowl.sum()), shade_area_px=int(region.sum()))
    # lit bowl = rim ellipse: its far half is the lower outline of the dark shade
    rim = _bowl_ellipse(L, full) if grow else _bowl_from_bell(L, full)
    if rim is None and not grow:
        # small far lamps: lit bowl = bright pixels hanging directly under the bell's bottom row
        rows = np.nonzero(full.any(1))[0]
        if len(rows) > 6:
            yb = rows[-1]
            xs_b = np.nonzero(full[yb - 1])[0] if full[yb - 1].any() else np.nonzero(full[yb])[0]
            x0b, x1b = xs_b.min(), xs_b.max() + 1
            Wb = x1b - x0b
            zone = np.zeros_like(full)
            zone[yb - 2:min(L.shape[0], yb + max(3, int(0.3 * Wb))), max(0, x0b - 2):x1b + 2] = True
            br = zone & (Lb > 150) & ~full
            n_, cc = cv2.connectedComponents(br.astype(np.uint8), connectivity=8)
            touch = np.unique(cc[cv2.dilate(full.astype(np.uint8), ker(2)).astype(bool) & br])
            bowl2 = np.isin(cc, touch[touch > 0])
            if bowl2.any():
                bowl2 = cv2.morphologyEx(bowl2.astype(np.uint8), cv2.MORPH_CLOSE, ker(2)).astype(bool)
                alpha = np.maximum(alpha, cv2.GaussianBlur(bowl2.astype(np.float32), (0, 0), 0.7))
                info['bowl_from_bright_pixels'] = int(bowl2.sum())
    if rim is not None:
        h, w = L.shape
        X, Y = _grid(h, w)
        ell = cov(sd_ellipse(X, Y, rim[0], rim[1], rim[2] + 1.0, rim[3] + 1.0, rim[4]))
        alpha = np.maximum(alpha, ell)
        info['rim_ellipse_local'] = [float(v) for v in rim]
        lip = _rim_lip(L, rim)
        if lip is not None:
            alpha = np.maximum(alpha, poly_coverage([lip], h, w, ss=4))
            info['rim_lip'] = True
    return alpha.astype(np.float32), info


def _rim_lip(L, p, n=120):
    """Inner rim band below a big shade's lit bowl: per angle on the near half, a thin dark
    dip (the rim edge) 4..45 px outside the bowl ellipse; smooth offset curve -> polygon of the
    band (None unless the dip is found consistently)."""
    h, w = L.shape
    if p[3] < 0.22 * p[2]:      # the inner rim band is only visible when looking up into the shade
        return None
    t = np.linspace(0.15, np.pi - 0.15, n)
    pts, nrm = ellipse_points(*p, t=t)
    smax = min(48.0, 0.25 * p[2])
    if smax < 10:
        return None
    sg = np.arange(0, smax, 0.5)
    px = pts[:, 0:1] + nrm[:, 0:1] * sg[None]
    py = pts[:, 1:2] + nrm[:, 1:2] * sg[None]
    if px.min() < 1 or py.min() < 1 or px.max() > w - 2 or py.max() > h - 2:
        return None
    pr = cv2.GaussianBlur(sample_bilinear(L, px, py), (5, 1), 1.0)
    i0 = int(4 / 0.5)
    j = np.argmin(pr[:, i0:], axis=1) + i0
    lo = pr[np.arange(n), j]
    inner = np.array([np.median(pr[k, :max(i0, j[k] - 4)]) for k in range(n)])
    good = (lo < 0.6 * inner) & (lo < 95)
    if good.mean() < 0.6:
        return None
    d = sg[j].astype(np.float64)
    from scipy.ndimage import median_filter
    tt = t[good]
    dd = median_filter(d[good], 9, mode='nearest')
    if np.mean(np.abs(d[good] - dd) < 3) < 0.7:
        return None
    c = np.polynomial.polynomial.polyfit(tt, dd, 3)
    dfit = np.clip(np.polynomial.polynomial.polyval(t, c), 0, smax)
    tt2 = np.linspace(0, np.pi, 200)
    P2, N2 = ellipse_points(*p, t=tt2)
    dd2 = np.interp(tt2, t, dfit) * np.clip(np.minimum(tt2, np.pi - tt2) / 0.15, 0, 1)
    outer = P2 + N2 * (dd2[:, None] + 1.0)
    back, _ = ellipse_points(*p, t=np.linspace(np.pi, 0, 100)[1:-1] + np.pi)
    return np.concatenate([outer, P2[::-1]], 0)


def _bowl_from_bell(L, shade):
    """Side-view bell (ceiling B): rim ellipse just below the bell's widest bottom row,
    fitted by edge contrast (lit interior brighter than the dark bell above and the dark rim
    outline below)."""
    h, w = shade.shape
    rows = np.nonzero(shade.any(1))[0]
    if len(rows) < 10:
        return None
    width = np.array([np.ptp(np.nonzero(shade[y])[0]) + 1 if shade[y].any() else 0 for y in range(h)])
    low = rows[rows >= rows[0] + 0.6 * (rows[-1] - rows[0])]
    y_r = int(low[np.argmax(width[low])])
    xs = np.nonzero(shade[y_r])[0]
    xl, xr = xs.min(), xs.max() + 1
    W_ = xr - xl
    # far rim = the bell's bottom row, rim ends = its extremes; only ry is unknown: choose it
    # so the near half of the ellipse sits on the strongest bright->dark step (lit interior ->
    # dark rim outline)
    cx, rx, top = (xl + xr) / 2, W_ / 2 + 1.0, y_r + 1.0
    Ls = cv2.GaussianBlur(L, (0, 0), 1.0)
    tn = np.linspace(0.35, np.pi - 0.35, 80)
    best = None
    for ry in np.arange(3.0, 0.6 * rx, 0.5):
        pts, nrm = ellipse_points(cx, top + ry, rx, ry, 0.0, t=tn)
        a_ = pts - nrm * 2.5
        b_ = pts + nrm * 2.5
        if a_[:, 1].max() > h - 2 or b_[:, 1].max() > h - 2:
            break
        c_ = float(np.mean(sample_bilinear(Ls, a_[:, 0], a_[:, 1]) - sample_bilinear(Ls, b_[:, 0], b_[:, 1])))
        if best is None or c_ > best[0]:
            best = (c_, ry)
    if best is None or best[0] < 25 or top + 2 * best[1] > h - 2:
        return None
    ry = best[1]
    p = [cx, top + ry, rx, ry, 0.0]
    # include the thin dark/orange rim outline: grow to the darkest point beyond the step + 1 px
    pts, nrm = ellipse_points(*p, t=tn)
    sg = np.arange(0, 8.01, 0.5)
    pr = sample_bilinear(Ls, pts[:, 0:1] + nrm[:, 0:1] * sg[None], pts[:, 1:2] + nrm[:, 1:2] * sg[None])
    d = float(np.median(sg[np.argmin(pr, axis=1)])) + 1.0
    p = [cx, top + ry, rx + d, ry + d, 0.0]
    X, Y = _grid(h, w)
    inside = (sd_ellipse(X, Y, *p) < -1.5) & ~shade
    if inside.sum() < 30 or np.median(L[inside]) < 120:
        return None
    return [float(v) for v in p]


def _bowl_ellipse(L, shade):
    """Rim ellipse of a dome shade seen from below. The rim ends are the silhouette's extreme
    columns; the far half of the rim is the central part of the silhouette's lower outline
    (sub-pixel): y = cy + (x-cx)*tan(a) - ry*sqrt(1-u^2), robust LSQ for (cy, ry). Kept only
    if the near half (below the outline) is clearly bright = the lit bowl."""
    h, w = shade.shape
    cols = np.nonzero(shade.any(0))[0]
    if len(cols) < 20:
        return None
    lows = np.array([np.nonzero(shade[:, c])[0].max() for c in cols], np.float32)
    xs = cols.astype(np.float32) + 0.5
    ys, _ = refine_horizontal_edge_curve(L, xs, lows + 1.0, 3, sign=+1, sigma=0.8)
    x_min, x_max = float(cols[0]), float(cols[-1] + 1)
    cx, rx = (x_min + x_max) / 2, (x_max - x_min) / 2
    e = max(2, len(cols) // 25)
    yl, yr = float(np.median(ys[:e])), float(np.median(ys[-e:]))
    ta = (yr - yl) / (x_max - x_min)
    u = (xs - cx) / rx
    m = np.abs(u) < 0.8
    if m.sum() < 10:
        return None
    A = np.stack([np.ones(m.sum()), -np.sqrt(np.clip(1 - u[m] ** 2, 0, 1))], 1)
    rhs = ys[m] - (xs[m] - cx) * ta
    keep = np.ones(m.sum(), bool)
    for _ in range(4):
        (cy, ry), *_ = np.linalg.lstsq(A[keep], rhs[keep], rcond=None)
        res = rhs - A @ np.array([cy, ry])
        sd = 1.4826 * np.median(np.abs(res[keep])) + 0.3
        keep = np.abs(res) < 2.5 * sd
    if not (3 <= ry <= rx) or cy + ry > h - 2:     # rim must be fully inside the crop
        return None
    p = [cx, float(cy), rx, float(ry), float(np.degrees(np.arctan(ta)))]
    X, Y = _grid(h, w)
    inside = (sd_ellipse(X, Y, *p) < -1.5) & ~shade
    if inside.sum() < 30 or np.median(L[inside]) < 110:
        return None
    return p


def pendants(name):
    """Pendant lamps (shade + lit bowl) and cords of a ceiling photo. Returns
    (lamps_alpha, cords_alpha, meta list)."""
    cfg = CEIL[name]
    rgb = load_src(name)
    H, W = rgb.shape[:2]
    L = gray(rgb)
    lab, st, keep, Lb = _lamp_cores(L, cfg)
    if cfg.get('seeds_only'):
        keep = []
    # seeded lamps that touch dark structure: own label image, core = dark comp ∩ ROI box
    lab2 = np.zeros_like(lab)
    st2 = [None]
    keep2 = []
    seed_thr, seed_sym = {}, {}
    for k, sd_ in enumerate(cfg['extra_seeds']):
        sx, sy, (bx0, by0, bx1, by1) = sd_[:3]
        seed_sym[k + 1] = sd_[3] if len(sd_) > 3 else bool(cfg.get('symmetrize'))
        roi = Lb[by0:by1, bx0:bx1]
        p10, p50 = np.percentile(roi, [10, 50])
        thr_k = cfg['thr'] if p50 >= 60 else float(np.clip(2.5 * p10 + 8, 16, cfg['thr']))
        seed_thr[k + 1] = thr_k
        D = (roi < thr_k).astype(np.uint8)
        D = cv2.morphologyEx(D, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        n_, cc = cv2.connectedComponents(D, connectivity=8)
        idx = cc[sy - by0, sx - bx0]
        if idx == 0:   # seed not on a dark pixel: take the largest dark component within 20 px
            win = cc[max(0, sy - by0 - 20):sy - by0 + 21, max(0, sx - bx0 - 20):sx - bx0 + 21]
            v = win[win > 0]
            if not len(v):
                continue
            idx = np.bincount(v).argmax()
        comp = cc == idx
        ys_, xs_ = np.nonzero(comp)
        lab2[by0:by1, bx0:bx1][comp] = k + 1
        st2.append(np.array([bx0 + xs_.min(), by0 + ys_.min(), xs_.max() - xs_.min() + 1,
                             ys_.max() - ys_.min() + 1, comp.sum()]))
        keep2.append(k + 1)
    gx, gy = grad_images(L, 1.0)
    bh = cv2.morphologyEx(Lb, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))) - Lb
    lamps = np.zeros((H, W), np.float32)
    cords = np.zeros((H, W), np.float32)
    meta = []
    comps = [(lab, st, i) for i in keep] + [(lab2, st2, i) for i in keep2]
    for lb, sx, i in comps:
        x, y, w, h, ar = sx[i]
        pad = max(12, int(0.15 * max(w, h)))
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(W, x + w + pad), min(H, y + h + int(0.6 * w) + pad)
        core = lb[y0:y1, x0:x1] == i
        thr_i = seed_thr.get(i, cfg['thr']) if lb is lab2 else cfg['thr']
        sym_i = lb is lab2 and seed_sym.get(i, False)
        if sym_i:
            yc_ = y + h / 2
            xc_ = x + w / 2
            tilt = np.degrees(np.arctan2(cfg['vp'][0] - xc_, yc_ - cfg['vp'][1])) if cfg.get('vp') else 0.0
            core = _symmetrize_core(core, Lb[y0:y1, x0:x1], thr_i, -tilt)
        lamp, info = _lamp_matte(L[y0:y1, x0:x1], Lb[y0:y1, x0:x1], core, thr_i,
                                 grow=not sym_i)
        m = dict(bbox=[int(x), int(y), int(w), int(h)], **info)
        lamps[y0:y1, x0:x1] = np.maximum(lamps[y0:y1, x0:x1], lamp)
        # cord from the top of the core
        ys_, xs_ = np.nonzero(core)
        yt = ys_.min()
        xt = xs_[ys_ <= yt + 2].mean()
        xt_, yt_ = x0 + xt + 0.5, y0 + yt + 0.5
        if cfg.get('vp') is not None:
            a0 = np.degrees(np.arctan2(cfg['vp'][0] - xt_, yt_ - cfg['vp'][1]))
            tol = cfg.get('vp_tol_deg', 4.0)
            angs = np.arange(a0 - tol, a0 + tol + 1e-6, 0.2)
        else:
            angs = np.arange(-cfg['max_cord_angle'], cfg['max_cord_angle'] + 1e-6, 0.25)
        cr = _cord_trace(L, xt_, yt_, angs)
        if cr is not None and cr['rms'] < 1.5:
            cords = np.maximum(cords, capsule_coverage(H, W, cr, extra=0.3))
            m['cord'] = cr
        m['top'] = [float(x0 + xt + 0.5), float(y0 + yt + 0.5)]
        if 'cord' in m and cfg.get('canopies', False):   # ceiling canopy: dark blob at the cord top
            cx_, cy_ = m['cord']['x1'], m['cord']['y1']
            r_ = 60
            bx0, by0 = int(max(0, cx_ - r_)), int(max(0, cy_ - r_))
            bx1, by1 = int(min(W, cx_ + r_)), int(min(H, cy_ + r_))
            roi = Lb[by0:by1, bx0:bx1]
            D = (roi < cfg['thr']).astype(np.uint8)
            D = cv2.morphologyEx(D, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
            n_, cc, st_, _ = cv2.connectedComponentsWithStats(D, connectivity=8)
            yy_, xx_ = np.mgrid[by0:by1, bx0:bx1]
            best = None
            for j in range(1, n_):
                ar_ = st_[j, cv2.CC_STAT_AREA]
                if not (60 <= ar_ <= 8000):
                    continue
                if st_[j, cv2.CC_STAT_WIDTH] >= 2 * r_ - 2 or st_[j, cv2.CC_STAT_HEIGHT] >= 2 * r_ - 2:
                    continue       # touches the ROI on both sides -> a swag gap, not a canopy
                dd = np.min(np.hypot(xx_[cc == j] + 0.5 - cx_, yy_[cc == j] + 0.5 - cy_))
                if dd < 12 and (best is None or ar_ > best[1]):
                    best = (j, ar_)
            if best is not None:
                reg = cc == best[0]
                al_ = unmix_matte(L[by0:by1, bx0:bx1], reg, band=1.5, sigma=3.0, min_contrast=25.0)
                al_[~cv2.dilate(reg.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)] = 0
                lamps[by0:by1, bx0:bx1] = np.maximum(lamps[by0:by1, bx0:bx1], al_)
                ys_c, xs_c = np.nonzero(reg)
                m['canopy_bbox'] = [int(bx0 + xs_c.min()), int(by0 + ys_c.min()),
                                    int(xs_c.max() - xs_c.min() + 1), int(ys_c.max() - ys_c.min() + 1)]
        meta.append(m)
    return lamps, cords, meta


def _cord_trace(L, x_t, y_t, angles_deg, probe=140, sides=(4.0, 7.0, 11.0), dxs=range(-24, 25, 4)):
    best, bside = None, None
    for dx in dxs:
        for sd_ in sides:
            r = _cord_trace1(L, x_t + dx, y_t, angles_deg, probe, sd_)
            if r is not None and (best is None or r['contrast'] > best['contrast']):
                best, bside = r, sd_
    # iterate: re-aim along the fitted line and extend the probe to the traced length
    for _ in range(3):
        if best is None:
            break
        ang = np.degrees(np.arctan2(best['x1'] - best['x0'], best['y0'] - best['y1']))
        ln = np.hypot(best['x1'] - best['x0'], best['y1'] - best['y0'])
        r = _cord_trace1(L, best['x0'], best['y0'], np.arange(ang - 0.6, ang + 0.61, 0.1),
                         int(max(probe, ln)), bside)
        if r is None:
            break
        best = r
    return best


def _cord_trace1(L, x_t, y_t, angles_deg, probe=140, side=5.0):
    """Straight dark cord leaving (x_t, y_t) upwards. For every candidate angle the line
    contrast (mean of the two side samples at +-side px minus the centre sample) is averaged
    over the first `probe` px; the best angle's contrast profile then gives the extent (run
    with gaps <= 20 px). Returns dict or None."""
    H, W = L.shape
    Ls = cv2.GaussianBlur(L, (0, 0), 0.8)
    s = np.arange(12, 4000, 1.0)
    best = None
    for ad in angles_deg:
        a = np.deg2rad(ad)
        d = np.array([np.sin(a), -np.cos(a)])
        n = np.array([-d[1], d[0]])
        ss = s[:probe]
        xs, ys = x_t + d[0] * ss, y_t + d[1] * ss
        ok = (xs > side + 2) & (ys > side + 2) & (xs < W - side - 2)
        if ok.sum() < 30:
            continue
        c = sample_bilinear(Ls, xs[ok], ys[ok])
        l_ = sample_bilinear(Ls, xs[ok] + n[0] * side, ys[ok] + n[1] * side)
        r_ = sample_bilinear(Ls, xs[ok] - n[0] * side, ys[ok] - n[1] * side)
        con = np.minimum(l_, r_) - c
        sc = float(np.mean(np.clip(con, 0, 60)))
        if best is None or sc > best[0]:
            best = (sc, ad)
    if best is None or best[0] < 6:
        return None
    sc, ad = best
    a = np.deg2rad(ad)
    d = np.array([np.sin(a), -np.cos(a)])
    n = np.array([-d[1], d[0]])
    xs, ys = x_t + d[0] * s, y_t + d[1] * s
    ok = (xs > side + 2) & (ys > side + 2) & (xs < W - side - 2)
    s_, xs, ys = s[ok], xs[ok], ys[ok]
    c = sample_bilinear(Ls, xs, ys)
    con = np.minimum(sample_bilinear(Ls, xs + n[0] * side, ys + n[1] * side),
                     sample_bilinear(Ls, xs - n[0] * side, ys - n[1] * side)) - c
    con = np.convolve(con, np.ones(9) / 9, mode='same')
    ref = float(np.median(con[:min(len(con), 60)]))
    if ref < 15:
        return None
    thr = max(6.0, 0.2 * ref)
    end, gap = 0, 0
    for i in range(len(con)):
        if con[i] > thr:
            end, gap = i, 0
        else:
            gap += 1
            if gap > 45:
                break
    if end < 25:
        return None
    # sub-pixel centre + robust line, width (FWHM of the aligned profile)
    seg = np.arange(0, end, 4)
    t = np.arange(-4, 4.01, 0.25)
    px = (xs[seg])[:, None] + n[0] * t[None]
    py = (ys[seg])[:, None] + n[1] * t[None]
    pr = sample_bilinear(Ls, px, py)
    off = t[np.argmin(pr, axis=1)]
    sv = s_[seg]
    A = np.stack([np.ones_like(sv), sv], 1)
    m = np.ones(len(sv), bool)
    for _ in range(4):
        cf, *_ = np.linalg.lstsq(A[m], off[m], rcond=None)
        r = off - A @ cf
        sd = 1.4826 * np.median(np.abs(r[m])) + 0.2
        m = np.abs(r) < 2.5 * sd
    p0 = np.array([x_t, y_t]) + n * cf[0]
    p1 = np.array([x_t, y_t]) + d * s_[end] + n * (cf[0] + cf[1] * s_[end])
    t2 = np.arange(-8, 8.01, 0.25)
    q = np.stack([xs[seg], ys[seg]], 1)[m] + n[None] * (A @ cf)[m][:, None]
    prof = sample_bilinear(Ls, q[:, 0:1] + n[0] * t2[None], q[:, 1:2] + n[1] * t2[None]).mean(0)
    base = np.median(np.r_[prof[:8], prof[-8:]])
    below = t2[prof < (base + prof.min()) / 2]
    width = float(np.clip(below.max() - below.min() + 0.25, 1.5, 12)) if len(below) else 2.0
    return dict(x0=float(p0[0]), y0=float(p0[1]), x1=float(p1[0]), y1=float(p1[1]), width=width,
                angle_deg=float(ad), contrast=ref, rms=float(np.sqrt(np.mean(r[m] ** 2))))


def build_ceilings():
    out = []
    for name in ('ceiling_lookup_A', 'ceiling_lookup_B'):
        rgb = load_src(name)
        H, W = rgb.shape[:2]
        lamps, cords, meta = pendants(name)
        both = np.maximum(lamps, cords)
        rel = lambda fn: f'assets/cut/geo/{name}/{fn}'
        for m in meta:     # local rim ellipse -> image coords
            if 'rim_ellipse_local' in m:
                bx, by = m['bbox'][0], m['bbox'][1]
                pad = max(12, int(0.15 * max(m['bbox'][2], m['bbox'][3])))
                ox, oy = max(0, bx - pad), max(0, by - pad)
                e = m.pop('rim_ellipse_local')
                m['bowl_rim_ellipse'] = dict(centre=[e[0] + ox, e[1] + oy], axes=[e[2], e[3]], angle_deg=e[4])
        geo = dict(source=f'assets/gen/{name}.png', size=[W, H], n_lamps=len(meta),
                   lamps=_r(meta), note='bbox = dark-shade core [x, y, w, h]; cord = fitted straight segment '
                                        '(x0,y0 at the lamp, x1,y1 upper end) with measured width')
        with _open_geo(name) as fh:
            json.dump(geo, fh, indent=1)
        _entry(save_mask(both, rel('pendants.png')), (W, H),
               'all black pendant lamps (shade + lit bowl/rim) and their cords', 'cut lamps out / keep '
               'them above colour washes', anchors=dict(n_lamps=len(meta)))
        _entry(save_mask(lamps, rel('pendant_shades.png')), (W, H), 'lamp bodies only (shade + lit bowl)',
               'separate glow layers (screen the bowls)')
        _entry(save_mask(cords, rel('pendant_cords.png')), (W, H), 'cords only (anti-aliased capsules on the '
               'fitted cord lines)', 'restore cords above effects')
        _entry(rel('geometry.json'), (W, H), 'per-lamp bbox, bowl rim ellipse, cord segment', 'anchors for '
               'light beams / glows', anchors=None)
        ov = overlay(rgb, [lamps, cords], [(0, 255, 255), (255, 0, 200)], alpha=0.45, scale=0.3)
        save_jpg(ov, os.path.join(PREV, f'{name}_overlay.jpg'), 1640)
        if name.endswith('A'):
            crop_check(rgb, [lamps, cords], (1230, 1900, 1610, 2340), os.path.join(PREV, 'ceil_A_lamp.jpg'), 1,
                       [(0, 255, 255), (255, 0, 200)], 0.3)
        out.append(ov)
    return out


# =========================================================================== #
# contact sheet + build
# =========================================================================== #

def _font(size):
    for f in (P('assets', 'fonts', 'IBMPlexMono-Regular.ttf'), '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def contact_sheet(items, path=CONTACT, col_w=1100, cols=3, pad=18, title='geometry — fitted masks'):
    """items: list of (label, image path or uint8 array). Tiles scaled to col_w wide."""
    f_lab, f_tit = _font(22), _font(34)
    tiles = []
    for lab, im in items:
        im = Image.open(im).convert('RGB') if isinstance(im, str) else Image.fromarray(im).convert('RGB')
        if im.height > 1.25 * im.width:      # keep tall previews from dominating the sheet
            im = im.resize((round(im.width * 1.25 * im.width / im.height), round(1.25 * im.width)), Image.LANCZOS)
        s = col_w / im.width
        im = im.resize((col_w, max(1, round(im.height * s))), Image.LANCZOS)
        tiles.append((lab, im))
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    H = 70 + sum(max(t[1].height for t in r) + 40 + pad for r in rows)
    W = cols * col_w + (cols + 1) * pad
    sheet = Image.new('RGB', (W, H), (238, 229, 211))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 18), title, fill=(43, 36, 32), font=f_tit)
    y = 70
    for r in rows:
        rh = max(t[1].height for t in r)
        for j, (lab, im) in enumerate(r):
            x = pad + j * (col_w + pad)
            d.text((x, y + 4), lab, fill=(43, 36, 32), font=f_lab)
            sheet.paste(im, (x, y + 34))
        y += rh + 40 + pad
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sheet.save(path, quality=88)
    return path


def build():
    """Regenerate every geometry asset, assets/cut/geo/index.json and the contact sheet."""
    INDEX.clear()
    os.makedirs(OUT, exist_ok=True)
    build_cabins()
    build_void_B()
    build_void_A()
    build_glassblock()
    build_valance()
    build_ceilings()
    index = dict(
        area='geometry', module='src/lib/geometry.py', build='cd src && python3 -c "from lib import geometry; geometry.build()"',
        conventions='All masks are full source-image size, 8-bit L PNG, white = keep, analytically anti-aliased '
                    '(signed-distance coverage) for parametric shapes. Coordinates are source-image pixels; '
                    'pixel (i, j) covers [i, i+1) x [j, j+1). Ellipses: centre, semi-axes (rx along angle, ry), '
                    'angle in degrees clockwise (image y down). Lines: x = a + b*y (vertical) / polynomials as noted.',
        outputs=INDEX)
    with open(os.path.join(OUT, 'index.json'), 'w') as fh:
        json.dump(index, fh, indent=1)
    pv = lambda f: os.path.join(PREV, f)
    items = [('cabins_row: ceiling/fg/back/shells/arches', pv('cabins_overlay.jpg')),
             ('cabins 200%: arch 1 head + shell rim', pv('cab_c1_head.jpg')),
             ('cabins 300%: arch 2 spring line', pv('cab_c2_spring.jpg')),
             ('cabins 200%: shell base, floor arcs, fg', pv('cab_c4_base.jpg')),
             ('void_lookup_B: 6 concentric zones', pv('voidB_overlay.jpg')),
             ('void_B 200%: left side rings', pv('vb_c0.jpg')),
             ('void_B 200%: right side rings', pv('vb_c3.jpg')),
             ('void_B 200%: skylight edge', pv('vb_c4.jpg')),
             ('void_lookup_A: opening/rail/collar/1F rail', pv('voidA_overlay.jpg')),
             ('void_A 200%: collar + upper rail', pv('va_c0.jpg')),
             ('void_A 200%: 1F handrail top edge', pv('va_c3.jpg')),
             ('void_A 200%: 1F rail / slab fascia edge', pv('va_c4.jpg')),
             ('glassblock: mortar grid', pv('glassblock_overlay.jpg')),
             ('glassblock 400%: joint crossing', pv('gb_c0.jpg')),
             ('glassblock 400%: right perimeter', pv('gb_c3.jpg')),
             ('glassblock: block label map', pv('glassblock_labels.jpg')),
             ('festoon_valance: fabric mask', pv('valance_overlay.jpg')),
             ('valance 200%: hem at a gather', pv('fv_c1.jpg')),
             ('valance 200%: jabot tail', pv('fv_c2.jpg')),
             ('valance 200%: hem, swag 1', pv('fv_c0.jpg')),
             ('valance 200%: cord over the valance', pv('fv_c6.jpg')),
             ('ceiling_lookup_A: lamps + cords', pv('ceiling_lookup_A_overlay.jpg')),
             ('ceiling_lookup_B: lamps + cords', pv('ceiling_lookup_B_overlay.jpg')),
             ('ceiling_A 100%: near lamp', pv('ceil_A_lamp.jpg'))]
    items = [(l, f) for l, f in items if os.path.exists(f)]
    contact_sheet(items, col_w=820, cols=4)
    return index
