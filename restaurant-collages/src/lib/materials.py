"""materials — tileable material swatches + procedural paper / grain / edge / wash generators.

Area "materials" of the restaurant-collage asset library.  Everything is float32 0..1
(H, W, C) internally; RGBA files are 8-bit straight alpha.

Swatches (assets/mat/*.png, 1600 x 1600, seamlessly tileable, flattened lighting)
    velvet_terracotta, oak_fluted, marble, linen_glow, linen_plain, plaster_warm,
    glassblock, steel_brushed, terrazzo_cream, greenery
Full-canvas instances (A3, 4961 x 3508)
    paper_linen_A3.png, grain_A3.png
Client reference
    client_drape_soft.png (6x), client_drape_sheer.png (RGBA veil)

Reusable functions (see their docstrings):
    periodic_noise, fbm, warp_periodic, flatten_light, quilt, rectify_columns, tile, grade,
    linen_weave, key_foliage, seam_score,
    paper_linen, grain, torn_mask, deckle_rgba, drop_shadow, watercolour_wash,
    halftone, paper_cut_edge, upscale_soft
build() regenerates every asset, index.json and the contact sheet deterministically.
"""
from __future__ import annotations

import gc
import json
import os
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import fft as sfft
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MAT = os.path.join(ROOT, 'assets', 'mat')
BUILD = os.path.join(ROOT, 'build', 'materials')
PREV = os.path.join(ROOT, 'build', 'preview', 'materials')
CONTACT = os.path.join(ROOT, 'build', 'contact', 'materials.jpg')
A3 = (3508, 4961)          # (h, w)
SW = 1600                  # swatch size

PALETTE = {
    'ink': '#2B2420', 'linen': '#EFE6D6', 'oat': '#DCCDB4', 'sand': '#C9B391',
    'honey': '#E8B062', 'amber': '#D98A3D', 'ember': '#C2602E', 'terracotta': '#A9502F',
    'oxblood': '#6B2430', 'wine': '#4A1A26', 'oak': '#B07A45', 'sage': '#8E9A72',
    'leaf': '#4F6B3A', 'canopy': '#7FA35A', 'glass': '#C8DAD3', 'celadon': '#A9C4BC',
    'dusk': '#3D4A6B', 'indigo': '#262C45', 'violet': '#5A4E7A', 'steel': '#B8BCBD',
    'paper': '#EEE5D3',
}


def P(*parts):
    return os.path.join(ROOT, *parts)


def hexf(c):
    """'#RRGGBB' (or palette name) -> float32 rgb 0..1."""
    c = PALETTE.get(c, c).lstrip('#')
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


# --------------------------------------------------------------------------- #
# io
# --------------------------------------------------------------------------- #

def load_src(name, box=None, scale=1.0):
    """Load an assets/gen (or any repo-relative) image as float32 RGB, optional crop box
    (x0, y0, x1, y1) in source pixels and Lanczos/area rescale."""
    path = name if os.path.isabs(name) else (P('assets', 'gen', name) if '/' not in name else P(name))
    im = Image.open(path).convert('RGB')
    if box is not None:
        im = im.crop(tuple(int(v) for v in box))
    a = np.asarray(im, np.float32) / 255.0
    if scale != 1.0:
        a = rescale(a, scale)
    return a


def rescale(a, s):
    h, w = a.shape[:2]
    size = (max(1, int(round(w * s))), max(1, int(round(h * s))))
    interp = cv2.INTER_AREA if s < 1 else cv2.INTER_LANCZOS4
    return np.clip(cv2.resize(a, size, interpolation=interp), 0, 1).astype(np.float32)


def to_u8(a):
    return np.clip(np.floor(np.asarray(a, np.float32) * 255.0 + 0.5), 0, 255).astype(np.uint8)


def save_png(path, a, mode=None):
    """Save float (0..1) or uint8 array as PNG. 2-D -> 'L'; 3-ch -> RGBA (opaque) unless
    mode='RGB'; 4-ch -> RGBA straight alpha."""
    a = np.asarray(a)
    u = a if a.dtype == np.uint8 else to_u8(a)
    if u.ndim == 2:
        im = Image.fromarray(u, 'L')
    elif u.shape[2] == 3:
        if mode == 'RGB':
            im = Image.fromarray(u, 'RGB')
        else:
            im = Image.fromarray(np.dstack([u, np.full(u.shape[:2], 255, np.uint8)]), 'RGBA')
    else:
        im = Image.fromarray(u, 'RGBA')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, optimize=False, compress_level=6)
    return path


def preview(a, path, max_side=1600, bg='#EFE6D6', quality=88):
    """Downscaled JPEG preview (RGBA flattened on linen)."""
    a = np.asarray(a, np.float32) if np.asarray(a).dtype != np.uint8 else np.asarray(a, np.float32) / 255
    if a.ndim == 2:
        a = np.dstack([a] * 3)
    if a.shape[2] == 4:
        al = a[..., 3:4]
        a = a[..., :3] * al + hexf(bg) * (1 - al)
    s = max_side / max(a.shape[:2])
    if s < 1:
        a = rescale(a, s)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(to_u8(a[..., :3])).save(path, quality=quality)
    return path


def lum(a):
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).astype(np.float32)


def gblur(a, sigma, mode='reflect'):
    """Gaussian blur (float32). mode 'wrap' gives a periodic (tile-safe) blur."""
    if sigma <= 0:
        return a
    if mode == 'wrap':
        if a.ndim == 3:
            return np.dstack([ndi.gaussian_filter(a[..., c], sigma, mode='wrap', truncate=3.0)
                              for c in range(a.shape[2])]).astype(np.float32)
        return ndi.gaussian_filter(a, sigma, mode='wrap', truncate=3.0).astype(np.float32)
    k = int(sigma * 3) * 2 + 1
    return cv2.GaussianBlur(a, (k, k), sigma, borderType=cv2.BORDER_REFLECT_101)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# --------------------------------------------------------------------------- #
# noise
# --------------------------------------------------------------------------- #

def periodic_noise(h, w, seed, sigma, sigma_y=None, white=None):
    """Gaussian-filtered white noise, unit std, seamlessly periodic (FFT filtered).
    sigma (x) / sigma_y (y) are the feature sizes in pixels (anisotropic if they differ)."""
    sy = sigma if sigma_y is None else sigma_y
    if white is None:
        white = np.random.default_rng(seed).standard_normal((h, w), dtype=np.float32)
    F = sfft.rfft2(white, workers=2)
    fy = sfft.fftfreq(h).astype(np.float32)[:, None]
    fx = sfft.rfftfreq(w).astype(np.float32)[None, :]
    G = np.exp(-2.0 * np.pi ** 2 * ((fy * sy) ** 2 + (fx * sigma) ** 2)).astype(np.float32)
    out = sfft.irfft2(F * G, s=(h, w), workers=2).astype(np.float32)
    out -= out.mean()
    sd = out.std()
    return out / (sd if sd > 0 else 1)


def fbm(h, w, seed, sigma, octaves=4, gain=0.5, lacunarity=2.0, sigma_y=None):
    """Periodic fractal noise (sum of periodic_noise octaves), unit std."""
    out = np.zeros((h, w), np.float32)
    amp, s, sy = 1.0, float(sigma), float(sigma if sigma_y is None else sigma_y)
    for o in range(octaves):
        out += amp * periodic_noise(h, w, seed * 7919 + o * 104729 + 1, s, sy)
        amp *= gain
        s /= lacunarity
        sy /= lacunarity
    return out / out.std()


# --------------------------------------------------------------------------- #
# lighting flattening + seamless synthesis
# --------------------------------------------------------------------------- #

def flatten_light(img, sigma, mask=None, per_channel=False, strength=1.0, sigma_y=None):
    """Remove low-frequency lighting (gradients, pools, vignettes) by dividing by a
    mask-normalised Gaussian low-pass. per_channel=True also flattens colour casts.
    Returns the image rescaled to its original (masked) mean."""
    img = np.asarray(img, np.float32)
    rgb = img[..., :3]
    m = np.ones(img.shape[:2], np.float32) if mask is None else np.asarray(mask, np.float32)
    sy = sigma if sigma_y is None else sigma_y

    def lp(ch):
        k = (int(sigma * 3) * 2 + 1, int(sy * 3) * 2 + 1)
        num = cv2.GaussianBlur(ch * m, k, sigmaX=sigma, sigmaY=sy, borderType=cv2.BORDER_REFLECT_101)
        den = cv2.GaussianBlur(m, k, sigmaX=sigma, sigmaY=sy, borderType=cv2.BORDER_REFLECT_101)
        return num / np.maximum(den, 1e-4)

    out = img.copy()
    if per_channel:
        for c in range(3):
            ch = rgb[..., c]
            low = np.maximum(lp(ch), 1e-3)
            tgt = (ch * m).sum() / max(m.sum(), 1)
            out[..., c] = ch * (tgt / low) ** strength
    else:
        L = lum(rgb)
        low = np.maximum(lp(L), 1e-3)
        tgt = (L * m).sum() / max(m.sum(), 1)
        out[..., :3] = rgb * ((tgt / low) ** strength)[..., None]
    out[..., :3] = np.clip(out[..., :3], 0, 1)
    return out


def _mincut(E):
    """Minimum-error vertical boundary through E (h, w) (8-connected DP). Returns col per row."""
    h, w = E.shape
    C = E.astype(np.float64).copy()
    back = np.zeros((h, w), np.int8)
    ar = np.arange(w)
    for i in range(1, h):
        prev = C[i - 1]
        st = np.vstack([np.r_[np.inf, prev[:-1]], prev, np.r_[prev[1:], np.inf]])
        k = np.argmin(st, 0)
        C[i] += st[k, ar]
        back[i] = k - 1
    path = np.empty(h, np.int64)
    path[-1] = int(np.argmin(C[-1]))
    for i in range(h - 1, 0, -1):
        path[i - 1] = path[i] + back[i, path[i]]
    return np.clip(path, 0, w - 1)


def _valid_positions(valid, ph, pw):
    """bool map of top-left positions whose (ph, pw) window lies fully inside `valid`."""
    inv = (~valid).astype(np.float64)
    ii = cv2.integral(inv)
    s = ii[ph:, pw:] - ii[:-ph, pw:] - ii[ph:, :-pw] + ii[:-ph, :-pw]
    return s < 0.5


def quilt(sources, size, patch, overlap, seed=0, masks=None, snap=None, tol=0.12, reuse=1.5,
          search_scale=0.5, feather=1.2, weights=None, flip=False, verbose=False):
    """Toroidal image quilting (Efros & Freeman 2001, min-error boundary cuts) that wraps
    around both edges, so the result tiles seamlessly.

    sources : list of float32 (h, w, C) arrays (C = 3 or 4)
    size    : (H, W) output; H % (ph - oh) == 0 and W % (pw - ow) == 0
    patch   : (ph, pw)   overlap : (oh, ow)
    masks   : optional list of bool arrays (True = usable source pixel)
    snap    : (sy, sx) lattice (pixels) the source position must share with the target
              position (e.g. flute period); None / 0 = free.
    reuse   : penalty that discourages re-using the same source neighbourhood.
    flip    : also allow horizontally mirrored copies of the sources.
    """
    rng = np.random.default_rng(seed)
    H, W = (size, size) if np.isscalar(size) else size
    ph, pw = (patch, patch) if np.isscalar(patch) else patch
    oh, ow = (overlap, overlap) if np.isscalar(overlap) else overlap
    sy_, sx_ = ph - oh, pw - ow
    assert H % sy_ == 0 and W % sx_ == 0, (H, W, sy_, sx_)
    ny, nx = H // sy_, W // sx_
    snap = (0, 0) if snap is None else snap
    srcs, valids = [], []
    for i, s in enumerate(sources):
        v = np.ones(s.shape[:2], bool) if masks is None or masks[i] is None else masks[i].astype(bool)
        srcs.append(s.astype(np.float32)); valids.append(v)
        if flip:
            srcs.append(np.ascontiguousarray(s[:, ::-1]).astype(np.float32))
            valids.append(np.ascontiguousarray(v[:, ::-1]))
    wts = None
    if weights is not None:
        wts = np.repeat(np.asarray(weights, np.float64), 2 if flip else 1)
    C = srcs[0].shape[2]
    pos_ok, keep = [], []
    for i, (s, v) in enumerate(zip(srcs, valids)):
        if s.shape[0] < ph or s.shape[1] < pw:
            continue
        ok = _valid_positions(v, ph, pw)
        if snap[1]:
            ok &= (np.arange(ok.shape[1]) % snap[1] == 0)[None, :]
        if snap[0]:
            ok &= (np.arange(ok.shape[0]) % snap[0] == 0)[:, None]
        if ok.any():
            pos_ok.append(ok)
            keep.append(i)
    assert keep, 'no source is large enough for the patch size'
    srcs = [srcs[i] for i in keep]
    valids = [valids[i] for i in keep]
    if wts is not None:
        wts = wts[keep]
    sc = search_scale
    small = [rescale(s, sc) for s in srcs]
    php, pwp = max(4, int(round(ph * sc))), max(4, int(round(pw * sc)))
    # pos_ok at search scale: a small-scale position is usable if any full-res position
    # within reach of the refinement window is usable.
    r_ref = int(np.ceil(1 / sc)) + 1
    ok_small, usage = [], []
    for s, ok in zip(small, pos_ok):
        hs, ws = s.shape[0] - php + 1, s.shape[1] - pwp + 1
        okd = cv2.dilate(ok.astype(np.uint8), np.ones((2 * r_ref + 1, 2 * r_ref + 1), np.uint8))
        okd = cv2.resize(okd, (max(1, int(round(okd.shape[1] * sc))), max(1, int(round(okd.shape[0] * sc)))),
                         interpolation=cv2.INTER_NEAREST)
        o = np.zeros((hs, ws), bool)
        hh, ww = min(hs, okd.shape[0]), min(ws, okd.shape[1])
        o[:hh, :ww] = okd[:hh, :ww] > 0
        ok_small.append(o)
        usage.append(np.zeros((hs, ws), np.float32))
    out = np.zeros((H, W, C), np.float32)
    filled = np.zeros((H, W), bool)
    t0 = time.time()
    for i in range(ny):
        for j in range(nx):
            y, x = i * sy_, j * sx_
            rows = (y + np.arange(ph)) % H
            cols = (x + np.arange(pw)) % W
            T = out[np.ix_(rows, cols)]
            M = filled[np.ix_(rows, cols)]
            if not M.any():
                k = int(rng.choice(len(srcs), p=None if wts is None else wts / wts.sum()))
                vy, vx = np.nonzero(pos_ok[k])
                q = int(rng.integers(len(vy)))
                v0, u0 = int(vy[q]), int(vx[q])
            else:
                Ts = cv2.resize(T, (pwp, php), interpolation=cv2.INTER_AREA)
                Ms = (cv2.resize(M.astype(np.float32), (pwp, php), interpolation=cv2.INTER_AREA) > 0.999)
                Msf = Ms.astype(np.float32)
                nmask = max(Msf.sum(), 1.0)
                cands = []
                for k, s in enumerate(small):
                    cost = cv2.matchTemplate(s, Ts, cv2.TM_SQDIFF, mask=np.dstack([Msf] * C)) / nmask
                    cost = cost[:ok_small[k].shape[0], :ok_small[k].shape[1]]
                    cost = cost * (1 + reuse * usage[k])
                    if wts is not None:
                        cost = cost / max(wts[k], 1e-3)
                    cost[~ok_small[k]] = np.inf
                    cands.append(cost)
                cmin = min(float(c.min()) for c in cands)
                thr = cmin * (1 + tol) + 1e-7
                pool = [(k, *np.nonzero(c <= thr)) for k, c in enumerate(cands)]
                tot = sum(len(p[1]) for p in pool)
                q = int(rng.integers(tot))
                for k, yy, xx in pool:
                    if q < len(yy):
                        ys, xs = int(yy[q]), int(xx[q])
                        break
                    q -= len(yy)
                # refine at full resolution around the coarse hit
                cy, cx = int(round(ys / sc)), int(round(xs / sc))
                best = None
                Mf = M.astype(np.float32)[..., None]
                okk = pos_ok[k]
                for vv in range(max(0, cy - r_ref), min(okk.shape[0], cy + r_ref + 1)):
                    for uu in range(max(0, cx - r_ref), min(okk.shape[1], cx + r_ref + 1)):
                        if not okk[vv, uu]:
                            continue
                        e = float((((srcs[k][vv:vv + ph, uu:uu + pw] - T) ** 2) * Mf).sum())
                        if best is None or e < best[0]:
                            best = (e, vv, uu)
                if best is None:  # fall back to any valid position nearby
                    vy, vx = np.nonzero(okk)
                    d = (vy - cy) ** 2 + (vx - cx) ** 2
                    q = int(np.argmin(d))
                    best = (0, int(vy[q]), int(vx[q]))
                v0, u0 = best[1], best[2]
            yy, xx = np.ogrid[:usage[k].shape[0], :usage[k].shape[1]]
            sg = max(php, pwp) * 0.7
            usage[k] += np.exp(-(((yy - v0 * sc) ** 2 + (xx - u0 * sc) ** 2) / (2 * sg * sg))).astype(np.float32)
            Pt = srcs[k][v0:v0 + ph, u0:u0 + pw]
            if M.any():
                E = ((Pt - T) ** 2).sum(-1)
                newm = np.ones((ph, pw), np.float32)
                if M[:, :ow].all():
                    pth = _mincut(E[:, :ow])
                    newm[np.arange(pw)[None, :] < pth[:, None]] = 0
                if M[:, pw - ow:].all():
                    pth = _mincut(E[:, pw - ow:]) + pw - ow
                    newm[np.arange(pw)[None, :] > pth[:, None]] = 0
                if M[:oh, :].all():
                    pth = _mincut(E[:oh, :].T)
                    newm[np.arange(ph)[:, None] < pth[None, :]] = 0
                if M[ph - oh:, :].all():
                    pth = _mincut(E[ph - oh:, :].T) + ph - oh
                    newm[np.arange(ph)[:, None] > pth[None, :]] = 0
                newm = np.where(M, newm, 1.0).astype(np.float32)
                if feather > 0:
                    newm = np.where(M, gblur(newm, feather), 1.0).astype(np.float32)
                out[np.ix_(rows, cols)] = T * (1 - newm[..., None]) + Pt * newm[..., None]
            else:
                out[np.ix_(rows, cols)] = Pt
            filled[np.ix_(rows, cols)] = True
        if verbose:
            print(f'  quilt row {i + 1}/{ny}  {time.time() - t0:.1f}s', flush=True)
    return out


def tile(tex, h, w, offset=(0, 0), scale=1.0):
    """Repeat a (tileable) texture to h x w; offset = (dx, dy) phase; optional rescale."""
    t = tex if scale == 1.0 else rescale(tex, scale)
    th, tw = t.shape[:2]
    dx, dy = offset[0] % tw, offset[1] % th
    ry, rx = -(-(h + dy) // th), -(-(w + dx) // tw)
    reps = (ry, rx) + ((1,) if t.ndim == 3 else ())
    return np.tile(t, reps)[dy:dy + h, dx:dx + w]


def seam_score(tex, band=2):
    """Mean abs jump across the wrap seams relative to the mean interior jump (1.0 = ideal)."""
    t = np.asarray(tex, np.float32)[..., :3]
    dx_in = np.abs(np.diff(t, axis=1)).mean()
    dy_in = np.abs(np.diff(t, axis=0)).mean()
    sx = np.abs(t[:, 0] - t[:, -1]).mean() / max(dx_in, 1e-6)
    sy = np.abs(t[0] - t[-1]).mean() / max(dy_in, 1e-6)
    return float(sx), float(sy)


def warp_periodic(field, dx, dy):
    """Sample a periodic field at (x + dx, y + dy) with wrap-around (keeps periodicity)."""
    h, w = field.shape[:2]
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(field, gx + dx.astype(np.float32), gy + dy.astype(np.float32),
                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)


def color_response(img, mask=None, sigma=20):
    """Fit per-channel exponents a_c of log(C_c) ~ a_c * log(L) on the low band of a photo
    (how colour shifts with brightness: darker velvet turns oxblood, lighter turns orange)."""
    low = gblur(np.asarray(img[..., :3], np.float32), sigma)
    L = np.maximum(lum(low), 1e-3)
    m = np.ones(L.shape, bool) if mask is None else mask.astype(bool)
    lx = np.log(L[m]) - np.log(L[m]).mean()
    a = []
    for c in range(3):
        ly = np.log(np.maximum(low[..., c][m], 1e-3))
        ly = ly - ly.mean()
        a.append(float((lx * ly).sum() / max((lx * lx).sum(), 1e-6)))
    return np.array(a, np.float32)


def modulate(rgb, delta, resp):
    """Apply a log-luminance modulation `delta` (H, W) using channel response exponents."""
    return np.clip(rgb * np.exp(delta[..., None] * resp[None, None, :]), 0, 1).astype(np.float32)


# --------------------------------------------------------------------------- #
# swatch helpers
# --------------------------------------------------------------------------- #

def _poly_sources(img, polys, scale=1.0, pad=40, flat_sigma=None, per_channel=True, erode=5):
    """Crop polygons (source pixel coords) out of img -> list of (crop, bool mask)."""
    out = []
    for p in polys:
        p = np.asarray(p, np.float32)
        x0, y0 = np.maximum(p.min(0).astype(int) - pad, 0)
        x1 = min(img.shape[1], int(p[:, 0].max()) + pad)
        y1 = min(img.shape[0], int(p[:, 1].max()) + pad)
        crop = img[y0:y1, x0:x1].copy()
        m = np.zeros(crop.shape[:2], np.uint8)
        cv2.fillPoly(m, [np.round(p - [x0, y0]).astype(np.int32)], 1)
        if flat_sigma:
            crop = flatten_light(crop, flat_sigma, mask=m.astype(np.float32), per_channel=per_channel)
        if scale != 1.0:
            crop = rescale(crop, scale)
            m = cv2.resize(m, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_NEAREST)
        if erode:
            m = cv2.erode(m, np.ones((erode, erode), np.uint8))
        out.append((crop, m > 0))
    return out


def _match_means(srcs, masks, target=None):
    """Scale every source so its masked mean colour equals target (default: mean of means)."""
    means = [(c[..., :3] * m[..., None]).sum((0, 1)) / max(m.sum(), 1) for c, m in zip(srcs, masks)]
    tgt = np.mean(means, 0) if target is None else np.asarray(target, np.float32)
    res = []
    for c, mu in zip(srcs, means):
        c = c.copy()
        c[..., :3] = np.clip(c[..., :3] * (tgt / np.maximum(mu, 1e-3)), 0, 1)
        res.append(c)
    return res


def _finish(tex):
    return np.clip(tex, 0, 1).astype(np.float32)


# --------------------------------------------------------------------------- #
# A) material swatches
# --------------------------------------------------------------------------- #

VELVET_POLYS = [  # cabin_interior.png backrest faces (clean velvet, no props)
    [[540, 2470], [800, 2375], [1100, 2280], [1450, 2235], [1840, 2215], [1840, 2630], [1500, 2710],
     [1200, 2785], [950, 2865], [800, 2925], [640, 3000], [540, 3060]],
    [[3330, 2220], [3720, 2240], [3720, 2680], [3330, 2700]],
    [[2880, 2215], [3280, 2215], [3280, 2440], [2880, 2440]],
]


def make_velvet(seed=5):
    """velvet_terracotta: crushed terracotta velvet.  Two-band synthesis: the fine band
    (pile grain, tiny crush marks; log-luminance high-pass of the banquette backrests in
    cabin_interior.png) is quilted toroidally; the large crushed-pile sheen pattern is
    periodic, domain-warped procedural noise; both are pushed through the photo's own colour
    response (darker pile -> oxblood, sheen -> orange) around a terracotta base."""
    N = SW
    im = load_src('cabin_interior.png')
    parts = _poly_sources(im, VELVET_POLYS, scale=1.0, flat_sigma=120, erode=0)
    del im
    resp = np.mean([color_response(c, m, 15) for c, m in parts], 0)
    srcs, masks = [], []
    for c, m in parts:
        c = rescale(c, 0.8)
        m = cv2.resize(m.astype(np.uint8), (c.shape[1], c.shape[0]), interpolation=cv2.INTER_NEAREST)
        L = lum(c)
        fine = np.log(np.maximum(L, 1e-3)) - np.log(np.maximum(gblur(L, 4), 1e-3))
        srcs.append(np.dstack([fine] * 3).astype(np.float32) + 0.5)
        masks.append(cv2.erode(m, np.ones((5, 5), np.uint8)) > 0)
    hi = quilt(srcs, N, (200, 200), (100, 100), seed=seed, masks=masks, tol=0.3, reuse=3.0)[..., 0] - 0.5
    wx = fbm(N, N, seed + 1, 260, 4) * 45
    wy = fbm(N, N, seed + 2, 260, 4) * 30
    c1 = warp_periodic(fbm(N, N, seed + 3, 85, 5, gain=0.58, sigma_y=130), wx, wy)
    c1b = warp_periodic(fbm(N, N, seed + 9, 40, 3, sigma_y=24), wx, wy)
    crush = np.tanh(1.25 * c1 + 0.45 * c1b)
    sheen = smoothstep(0.9, 2.2, warp_periodic(fbm(N, N, seed + 10, 120, 4, sigma_y=200), wy, wx) + 0.3 * c1b)
    nap = warp_periodic(fbm(N, N, seed + 11, 22, 3, sigma_y=60), wx * 0.8, wy * 0.8)   # pile-direction streaks
    pm = warp_periodic(periodic_noise(N, N, seed + 4, 2.0, sigma_y=14), wx * 0.4, wy * 0.4)
    pile = periodic_noise(N, N, seed + 5, 0.8)
    big = fbm(N, N, seed + 8, 400, 2)
    delta = (0.105 * crush + 0.07 * sheen + 0.035 * nap + 0.016 * pm + 0.028 * pile + 0.04 * big
             + 0.6 * np.clip(hi, -0.4, 0.4))
    delta -= delta.mean()
    base = np.array([150, 56, 31], np.float32) / 255.0
    return _finish(base * np.exp(delta[..., None] * resp[None, None, :]))


def grade(rgb, stops, amount=1.0, normalize=False, lo_hi=(0.5, 99.5), mask=None):
    """Gradient-map grading. Luminance is mapped through colour `stops` and mixed with the
    image by `amount` (0..1).  stops: ['#hex' or palette name, ...] evenly spaced, or
    [(pos 0..1, '#hex'), ...].  normalize=True stretches the luminance percentiles lo_hi to
    0..1 first (so the full ramp is used).  Alpha (if present) is preserved."""
    rgb = np.asarray(rgb, np.float32)
    col = rgb[..., :3]
    if isinstance(stops[0], str):
        stops = [(i / max(1, len(stops) - 1), s) for i, s in enumerate(stops)]
    pos = np.array([p for p, _ in stops], np.float32)
    cols = np.stack([hexf(c) for _, c in stops])
    L = lum(col)
    if normalize:
        sel = L if mask is None else L[mask > 0.5]
        a, b = np.percentile(sel, lo_hi)
        L = np.clip((L - a) / max(b - a, 1e-4), 0, 1)
    mapped = np.stack([np.interp(L, pos, cols[:, c]) for c in range(3)], -1).astype(np.float32)
    out = rgb.copy()
    out[..., :3] = np.clip(col + (mapped - col) * amount, 0, 1)
    return out


OAK_PERIOD = 50  # px per flute (groove centre at x = k * 50)


def _comb_lowpass(a, mk, period, K=3, sk=1.8, sv=40):
    """Mask-normalised low-pass that only averages pixels of the same flute phase
    (taps at multiples of `period` horizontally, Gaussian sv vertically)."""
    k = int(sv * 3) * 2 + 1
    vb = lambda z: cv2.GaussianBlur(z, (1, k), sigmaX=0.1, sigmaY=sv, borderType=cv2.BORDER_REFLECT_101)
    num, den = vb(a * mk), vb(mk)
    W = a.shape[1]
    nc, dc = np.zeros_like(num), np.zeros_like(den)
    for j in range(-K, K + 1):
        w, s = np.exp(-j * j / (2 * sk * sk)), j * period
        if s >= 0:
            nc[:, :W - s] += w * num[:, s:]
            dc[:, :W - s] += w * den[:, s:]
        else:
            nc[:, -s:] += w * num[:, :W + s]
            dc[:, -s:] += w * den[:, :W + s]
    return nc / np.maximum(dc, 1e-4)


def make_oak(seed=7):
    """oak_fluted: the cabin's slatted wall. Grooves are detected (sub-pixel) and the wall is
    resampled so every flute is exactly OAK_PERIOD px (perfectly vertical, regular); every
    flute phase is then normalised to the wall-average profile (removes the pendant shadow
    band, uplight glow and the curved-wall shading = evenly lit); the swatch is assembled from
    whole, distinct slats (stretched along the grain, wrap cross-faded at a random height per
    slat), with a gentle golden-oak grade."""
    from scipy.signal import find_peaks
    P_ = OAK_PERIOD
    X0, X1, Y0, Y1 = 650, 2440, 1010, 2100   # regular part of the wall, below the drape
    reg = load_src('cabin_interior.png', box=(X0, Y0, X1, Y1))
    valid = np.ones(reg.shape[:2], bool)
    valid[:1468 - Y0, 2055 - X0:] = False     # pendant + cord
    L = lum(reg)
    prof = (L * valid).sum(0) / np.maximum(valid.sum(0), 1)
    hp = prof - cv2.GaussianBlur(prof.reshape(1, -1).astype(np.float32), (0, 0), 30).ravel()
    pk, _ = find_peaks(-hp, distance=32, prominence=0.004)
    pk = np.array([p + 0.5 * (hp[p - 1] - hp[p + 1]) / (hp[p - 1] - 2 * hp[p] + hp[p + 1])
                   if 1 <= p < len(hp) - 1 and abs(hp[p - 1] - 2 * hp[p] + hp[p + 1]) > 1e-9 else p
                   for p in pk], np.float32)
    n = len(pk)
    xt = np.arange(0, (n - 1) * P_, dtype=np.float32)
    xs = np.interp(xt, np.arange(n) * P_, pk).astype(np.float32)
    Hh = reg.shape[0]
    mapx = np.repeat(xs[None, :], Hh, 0)
    mapy = np.repeat(np.arange(Hh, dtype=np.float32)[:, None], len(xt), 1)
    rect = np.clip(cv2.remap(reg, mapx, mapy, cv2.INTER_CUBIC), 0, 1)
    rv = cv2.remap(valid.astype(np.uint8), mapx, mapy, cv2.INTER_NEAREST) > 0
    del reg
    # remove the generator's fine 'knit' upscaling pattern: smooth along the grain only
    rect = cv2.GaussianBlur(rect, (0, 0), sigmaX=0.6, sigmaY=1.6)
    W = rect.shape[1]
    m = rv.astype(np.float32)
    phase = np.arange(W) % P_
    L = lum(rect)
    loc = _comb_lowpass(L, m, P_)
    G = np.array([(L[:, phase == f] * m[:, phase == f]).sum() / max(m[:, phase == f].sum(), 1)
                  for f in range(P_)], np.float32)
    gain = np.clip(G[phase][None, :] / np.maximum(loc, 1e-3), 0.5, 2.0)
    eq = np.clip(rect * gain[..., None], 0, 1)
    eq = flatten_light(eq, 150, mask=m, per_channel=True)
    full = [k for k in range(W // P_) if rv[:, k * P_:(k + 1) * P_].all()]
    rng = np.random.default_rng(seed)
    ncol, B = SW // P_, 260
    Hs = SW + B
    order = list(rng.permutation(full))
    while len(order) < ncol:
        order += list(rng.permutation(full))
    order = order[:ncol]
    gm = lum(eq[:, :max(full) * P_ + P_]).mean()
    out = np.zeros((SW, SW, 3), np.float32)
    w = smoothstep(0, 1, (np.arange(B, dtype=np.float32) + 0.5) / B)[:, None, None]
    for j, k in enumerate(order):
        strip = eq[:, k * P_:(k + 1) * P_]
        strip = np.clip(strip * ((gm / lum(strip).mean()) ** 0.5), 0, 1)
        s = cv2.resize(strip, (P_, Hs), interpolation=cv2.INTER_CUBIC)
        col = s[:SW].copy()
        col[:B] = s[:B] * w + s[SW:SW + B] * (1 - w)
        out[:, j * P_:(j + 1) * P_] = np.roll(col, int(rng.integers(0, SW)), axis=0)
    out = grade(np.clip(out, 0, 1), ['#17100B', '#3A2416', '#7E4F2B', '#B07A45', '#D9A464'],
                amount=0.5, normalize=True)
    return _finish(out)


def _periodic_cells(N, pts, X, Y):
    """Periodic Voronoi query. Returns (d1, edge_dist, i1, i2): distance to the nearest site,
    exact distance to the bisector with the 2nd-nearest site, and both site indices."""
    from scipy.spatial import cKDTree
    tree = cKDTree(pts, boxsize=[N, N])
    q = np.c_[np.mod(X.ravel(), N), np.mod(Y.ravel(), N)]
    d, idx = tree.query(q, k=2, workers=2)
    p1, p2 = pts[idx[:, 0]], pts[idx[:, 1]]
    dl = np.mod(p2 - p1 + N / 2, N) - N / 2
    sep = np.maximum(np.hypot(dl[:, 0], dl[:, 1]), 1e-3)
    edge = (d[:, 1] ** 2 - d[:, 0] ** 2) / (2 * sep)
    sh = X.shape
    return (d[:, 0].reshape(sh).astype(np.float32), edge.reshape(sh).astype(np.float32),
            idx[:, 0].reshape(sh), idx[:, 1].reshape(sh))


def _edge_hash(a, b, salt=0):
    lo, hi = np.minimum(a, b).astype(np.uint64), np.maximum(a, b).astype(np.uint64)
    h = (lo * np.uint64(73856093)) ^ (hi * np.uint64(19349663)) ^ np.uint64(salt * 83492791 + 1)
    h = (h ^ (h >> np.uint64(13))) * np.uint64(0x5bd1e995)
    h = h ^ (h >> np.uint64(15))
    return ((h & np.uint64(0xFFFFFF)).astype(np.float64) / float(0xFFFFFF)).astype(np.float32)


def _jittered_points(N, n, rng, jitter=0.85):
    g = int(np.ceil(np.sqrt(n)))
    c = (np.stack(np.meshgrid(np.arange(g), np.arange(g)), -1).reshape(-1, 2) + 0.5) / g
    c = c + (rng.random(c.shape) - 0.5) * jitter / g
    return np.mod(c[rng.permutation(len(c))[:n]] * N, N).astype(np.float64)


def _splat_flecks(N, rng, n, lmin, lmax, wmin, wmax, ss=2):
    """Anti-aliased tiny elongated flecks (periodic) -> coverage map."""
    S = N * ss
    cv = np.zeros((S, S), np.uint8)
    for _ in range(n):
        x, y = rng.random(2) * S
        L = rng.uniform(lmin, lmax) * ss
        Wd = rng.uniform(wmin, wmax) * ss
        ang = rng.uniform(0, 180)
        val = int(rng.uniform(120, 255))
        for ox in (-S, 0, S):
            for oy in (-S, 0, S):
                cx, cy = x + ox, y + oy
                if -L < cx < S + L and -L < cy < S + L:
                    cv2.ellipse(cv, (int(cx * 16), int(cy * 16)), (int(L * 8), int(max(Wd, 1) * 8)),
                                ang, 0, 360, val, -1, cv2.LINE_AA, 4)
    return cv2.resize(cv.astype(np.float32) / 255.0, (N, N), interpolation=cv2.INTER_AREA)


def make_marble(seed=21, N=SW):
    """marble: polished warm-white marble with the cabin table's character — a pebbly network
    of veins (gold-ochre veins with a soft bleed, fine blue-grey veins and crackle 'nests'),
    per-pebble tint, grey pepper flecks and soft clouding.  Procedural (two periodic Voronoi
    networks, domain-warped) with colours sampled from the table top (white-balanced): crisp at
    any scale and seamlessly tileable."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    wx = fbm(N, N, seed + 1, 170, 3) * 36 + periodic_noise(N, N, seed + 2, 9) * 2.2
    wy = fbm(N, N, seed + 3, 170, 3) * 30 + periodic_noise(N, N, seed + 4, 9) * 2.2
    X, Y = xx + wx, yy + wy
    p1 = _jittered_points(N, 90, rng)
    _, e1, a1, b1 = _periodic_cells(N, p1, X, Y)
    wx2 = wx + periodic_noise(N, N, seed + 11, 30) * 6
    wy2 = wy + periodic_noise(N, N, seed + 12, 30) * 6
    p2 = _jittered_points(N, 520, rng)
    _, e2, a2, b2 = _periodic_cells(N, p2, xx + wx2, yy + wy2)
    r1 = _edge_hash(a1, b1, seed)
    r2 = _edge_hash(a2, b2, seed + 9)
    along = fbm(N, N, seed + 5, 45, 3)
    thick = 0.6 + 0.4 * np.tanh(fbm(N, N, seed + 6, 70, 3))
    grain = periodic_noise(N, N, seed + 13, 1.2)
    nest = smoothstep(0.2, 1.4, fbm(N, N, seed + 7, 200, 3))
    cloud = fbm(N, N, seed + 8, 240, 5)

    def line(dist, hw, aa=1.1):
        return np.clip(0.5 + (hw - dist) / aa, 0, 1).astype(np.float32)

    def over(rgb, col, a):
        return rgb + (np.asarray(col, np.float32) - rgb) * np.clip(a, 0, 1)[..., None]

    # stone: warm white with cloudy, per-pebble tints
    rgb = np.empty((N, N, 3), np.float32)
    rgb[:] = hexf('#EEE6D8')
    tint = rng.normal(0, 1, len(p1)).astype(np.float32)
    ptint = gblur(tint[a1].astype(np.float32), 14, mode='wrap') * 0.010
    rgb *= (1 + 0.022 * cloud + ptint)[..., None]
    warm = smoothstep(0.1, 1.7, fbm(N, N, seed + 10, 200, 4))
    rgb = over(rgb, hexf('#E3CFB0'), 0.30 * warm)
    greyc = smoothstep(0.6, 1.9, fbm(N, N, seed + 14, 160, 4))
    rgb = over(rgb, hexf('#D3CEC8'), 0.35 * greyc)
    vis = smoothstep(-1.1, -0.35, along)                      # veins break up in places
    thick_v = np.clip(0.25 + 1.25 * np.tanh(0.9 * fbm(N, N, seed + 15, 26, 3)) + 0.55, 0, 2.6)
    gold_sel = (r1 < 0.34).astype(np.float32)
    grey_sel = (r1 < 0.86).astype(np.float32)                 # most primary edges carry a vein
    core1 = line(e1, 0.35 + 0.75 * thick_v * thick) * grey_sel * vis * (0.82 + 0.18 * np.tanh(grain))
    # long meandering veins: contour lines of a warped low-frequency field
    F = warp_periodic(fbm(N, N, seed + 20, 320, 3), wx * 1.3, wy * 1.3)
    gy_, gx_ = np.gradient(F)
    gmag = np.maximum(np.hypot(gx_, gy_), 1e-4)
    lvis = smoothstep(-1.3, -0.4, fbm(N, N, seed + 21, 90, 3))
    gok = smoothstep(0.5, 1.0, gmag / float(np.median(gmag)))       # no rings around extrema
    long_core = line(np.abs(F) / gmag, 0.4 + 1.1 * thick_v) * lvis * gok
    core = np.maximum(core1, long_core)
    gold_src = np.maximum(core1 * gold_sel, long_core)
    sec_vis = (r2 < 0.6) * smoothstep(-1.5, -0.2, along)
    sec_core = line(e2, 0.35 + 0.3 * nest) * sec_vis * (0.10 + 0.45 * nest)
    # ochre / gold staining bleeding out of some veins (soft, diffuse), grey veil around veins
    stain_w = gblur(gold_src, 12, mode='wrap')
    stain_n = gblur(gold_src, 3.5, mode='wrap')
    veil = gblur(core, 5, mode='wrap')
    nest_veil = gblur(sec_core, 7, mode='wrap')
    stain_mod = 0.7 + 0.3 * np.tanh(fbm(N, N, seed + 16, 30, 3))
    rgb = over(rgb, hexf('#DDB27A'), np.minimum(0.55, 9.0 * stain_w) * stain_mod)
    rgb = over(rgb, hexf('#CB9150'), np.minimum(0.65, 3.2 * stain_n) * stain_mod)
    rgb = over(rgb, hexf('#B5AEA8'), 0.9 * veil)
    rgb = over(rgb, hexf('#BDB6AF'), 0.8 * nest_veil)
    rgb = over(rgb, hexf('#6E6A6C'), 0.75 * sec_core)
    gold_core = np.clip(gold_src * 1.0, 0, 1)
    core_col = hexf('#3F3B3F')
    rgb = over(rgb, core_col, 0.92 * core)
    rgb = over(rgb, hexf('#8A6238'), 0.30 * gold_core * core)     # warmer cores in gold veins
    fl = _splat_flecks(N, rng, 700, 1.2, 3.5, 0.5, 1.1)
    rgb = over(rgb, hexf('#7D7A7C'), 0.55 * fl)
    fl2 = gblur(_splat_flecks(N, rng, 240, 3, 9, 1.5, 3), 1.2, mode='wrap')
    rgb = over(rgb, hexf('#A29C98'), 0.35 * fl2)
    return _finish(rgb)


# glassblock_wall_A.png mortar grid: joint centres and flat-mortar edges (measured)
GB_V = {272: (261, 280), 875: (864, 884), 1461: (1451, 1470), 1975: (1965, 1984), 2382: (2372, 2391),
        2761: (2751, 2769), 3152: (3143, 3161), 3565: (3555, 3573), 4155: (4145, 4163)}
GB_H = {778: (774, 788), 1181: (1175, 1188), 1860: (1852, 1867), 2500: (2493, 2508),
        2753: (2748, 2762), 3289: (3280, 3298)}
GB_COLS = [272, 875, 1461, 1975, 2382, 2761, 3152, 3565, 4155]
GB_ROWS = [None, 778, 1181, 1860, 2500, 2753, 3289]
# 3 x 3 mosaic of (row, col) source blocks (1-based, e.g. R3C2). Column 9 is cut by the image
# edge and rows 1/5 / columns 4-7 are too far from square, so they are not used.  Plant blocks
# sit on one diagonal; the two sunbursts and the three 'wave' blocks never touch (incl. wrap).
GB_LAYOUT = [[(3, 2), (6, 3), (4, 8)],
             [(3, 8), (4, 1), (2, 7)],
             [(6, 2), (6, 8), (6, 1)]]
GB_CELL = [0, 533, 1067, 1600]
GB_HALF_JOINT = 9


def _knot_map(t, c0, e0, e1, c1, T, hj):
    """piecewise-linear target->source coordinate: [0,hj]->[c0,e0], [hj,T-hj]->[e0,e1],
    [T-hj,T]->[e1,c1] (extrapolated linearly outside 0..T)."""
    t = np.asarray(t, np.float32)
    return np.where(t < hj, c0 + t / hj * (e0 - c0),
                    np.where(t > T - hj, e1 + (t - (T - hj)) / hj * (c1 - e1),
                             e0 + (t - hj) / (T - 2 * hj) * (e1 - e0))).astype(np.float32)


def make_glassblock():
    """glassblock: 3 x 3 mosaic of real blocks from glassblock_wall_A, re-gridded on the mortar
    lines.  Every block is cut from mortar centre to mortar centre and piecewise-resampled so
    the glass fills the cell and every joint has exactly the same width; mortar tone is
    equalised and the joints (which carry the tile seams) are cross-faded, so the tile
    repeats exactly on the mortar grid (mortar centre lines at x, y = 0, 533, 1067)."""
    im = load_src('glassblock_wall_A.png')
    im = cv2.GaussianBlur(im, (0, 0), 0.45)
    hj, mg = GB_HALF_JOINT, 6
    acc = np.zeros((SW, SW, 3), np.float32)
    wacc = np.zeros((SW, SW), np.float32)
    cells = []
    for r in range(3):
        for c in range(3):
            R, Cc = GB_LAYOUT[r][c]
            xc0, xc1 = GB_COLS[Cc - 1], GB_COLS[Cc]
            yc0, yc1 = GB_ROWS[R - 1], GB_ROWS[R]
            xe0, xe1 = GB_V[xc0][1] + 1, GB_V[xc1][0]
            ye0, ye1 = GB_H[yc0][1] + 1, GB_H[yc1][0]
            Tx = GB_CELL[c + 1] - GB_CELL[c]
            Ty = GB_CELL[r + 1] - GB_CELL[r]
            tx = np.arange(-mg, Tx + mg, dtype=np.float32) + 0.5
            ty = np.arange(-mg, Ty + mg, dtype=np.float32) + 0.5
            sx = _knot_map(tx, xc0, xe0, xe1, xc1, Tx, hj)
            sy = _knot_map(ty, yc0, ye0, ye1, yc1, Ty, hj)
            mx, my = np.meshgrid(sx, sy)
            blk = np.clip(cv2.remap(im, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT), 0, 1)
            yy, xx = np.mgrid[0:blk.shape[0], 0:blk.shape[1]].astype(np.float32)
            dx = np.minimum(xx + 0.5 - mg, Tx + mg - xx - 0.5)   # distance to cell edge (px)
            dy = np.minimum(yy + 0.5 - mg, Ty + mg - yy - 0.5)
            mortar = (np.minimum(dx, dy) < hj + 0.5)
            cells.append((r, c, blk, dx, dy, mortar))
    del im
    # tone: glass partially to common brightness, mortar exactly to common colour
    gl = [lum(b)[~m].mean() for _, _, b, _, _, m in cells]
    mt = np.mean([b[m].mean(0) for _, _, b, _, _, m in cells], 0)
    gref = float(np.median(gl))
    for (r, c, blk, dx, dy, mortar), g in zip(cells, gl):
        glass_gain = (gref / g) ** 0.55
        mmean = blk[mortar].mean(0)
        dist = np.minimum(dx, dy)
        wm = 1 - smoothstep(hj - 1.0, hj + 2.5, dist)                 # 1 in mortar
        out = blk * glass_gain * (1 - wm[..., None]) + blk * (mt / mmean) * wm[..., None]
        # seam weights: linear ramps across each cell boundary (2*mg wide)
        w = np.clip((np.minimum(dx, dy) + mg) / (2 * mg), 0, 1).astype(np.float32)
        Ty, Tx = out.shape[:2]
        rows = (GB_CELL[r] - mg + np.arange(Ty)) % SW
        cols = (GB_CELL[c] - mg + np.arange(Tx)) % SW
        acc[np.ix_(rows, cols)] += np.clip(out, 0, 1) * w[..., None]
        wacc[np.ix_(rows, cols)] += w
    return _finish(acc / np.maximum(wacc, 1e-6)[..., None])


def rectify_columns(img, gathers, y0, y1, col_w, mask=None):
    """Piecewise-linear horizontal rectification of a band [y0, y1) of `img`.
    gathers: list of (x_at_y0, x_at_y1) for consecutive column boundaries (e.g. swag gather
    lines, flute grooves).  Every column is resampled to exactly col_w px.
    Returns (rect, rect_mask)."""
    H = y1 - y0
    n = len(gathers) - 1
    t = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    g = np.array(gathers, np.float32)
    gx = g[:, 0][None, :] * (1 - t) + g[:, 1][None, :] * t      # (H, n+1)
    xt = np.arange(n * col_w, dtype=np.float32) + 0.5
    k = np.minimum((xt // col_w).astype(int), n - 1)
    f = (xt - k * col_w) / col_w
    mapx = gx[:, k] * (1 - f)[None, :] + gx[:, k + 1] * f[None, :]
    mapy = np.repeat(np.arange(y0, y1, dtype=np.float32)[:, None], len(xt), 1)
    mapx = np.ascontiguousarray(mapx - 0.5, dtype=np.float32)
    mapy = np.ascontiguousarray(mapy, dtype=np.float32)
    rect = np.clip(cv2.remap(img, mapx, mapy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT), 0, 1)
    rm = None
    if mask is not None:
        rm = cv2.remap(mask.astype(np.uint8), mapx, mapy, cv2.INTER_NEAREST) > 0
    return rect, rm


def make_linen_glow(seed=3):
    """linen_glow: backlit honey linen festoon swags (ceiling_lookup_A).  The two most regular
    parts of the swag ceiling (a 3-column band and the upper centre column) are rectified so
    every swag column is exactly 400 px wide in the swatch (gather lines vertical), global
    glow gradients are flattened, then lattice-snapped toroidal quilting assembles 4 columns
    with min-cut seams that run along the gather lines.  Gather lines at x = 0, 400, 800, 1200."""
    A = load_src('ceiling_lookup_A.png')
    H, W = A.shape[:2]
    bad = np.zeros((H, W), np.uint8)
    for x0, y0, x1, y1 in [(1330, 1350, 1600, 1500), (1440, 1450, 1565, 2050), (1330, 1990, 1640, 2350),
                           (3565, 1440, 3645, 2180), (3470, 2170, 3740, 2350), (3870, 1550, 3990, 2350),
                           (4250, 800, 5456, 2400)]:
        bad[y0:y1, x0:x1] = 1
    CW = 780
    r1, m1 = rectify_columns(A, [(1562, 1582), (2335, 2390), (3160, 3140), (3925, 3912)], 1330, 2260, CW, mask=bad)
    r2, m2 = rectify_columns(A, [(2160, 2245), (3330, 3175)], 40, 1330, CW, mask=bad)
    del A
    # undo foreshortening: the upper column is near-frontal (keep its aspect: same scale as its
    # width), the farther band is stretched along the depth direction
    s2 = CW / 1050.0
    r2 = cv2.resize(r2, (r2.shape[1], int(r2.shape[0] * s2)), interpolation=cv2.INTER_AREA)
    m2 = cv2.resize(m2.astype(np.uint8), (m2.shape[1], r2.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    s1 = 1.45
    r1 = cv2.resize(r1, (r1.shape[1], int(r1.shape[0] * s1)), interpolation=cv2.INTER_CUBIC)
    m1 = cv2.resize(m1.astype(np.uint8), (m1.shape[1], r1.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    sc, pad = 400 / CW, 40
    srcs, masks = [], []
    for r, m in ((r1, ~m1), (r2, ~m2)):
        r = flatten_light(r, 260, mask=m.astype(np.float32), per_channel=True)
        r = rescale(r, sc)
        m = cv2.resize(m.astype(np.uint8), (r.shape[1], r.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
        srcs.append(np.concatenate([r[:, -pad:], r, r[:, :pad]], 1))
        masks.append(np.concatenate([m[:, -pad:], m, m[:, :pad]], 1))
    srcs = _match_means(srcs, masks)
    tex = quilt(srcs, SW, (260, 480), (100, 80), seed=seed, masks=masks, snap=(0, 400), tol=0.05,
                reuse=1.0, feather=2.0)
    # quilt patches start 40 px left of a gather line -> shift so gathers sit at x = k*400
    return _finish(np.roll(tex, -pad, axis=1))


def _recolor(hi, mean_rgb, mod=None, resp=None):
    """hi: flattened texture (any mean) -> rescaled to mean_rgb, times exp(mod * resp)."""
    hi = hi / np.maximum(hi.reshape(-1, 3).mean(0), 1e-4)
    out = hi * np.asarray(mean_rgb, np.float32)
    if mod is not None:
        r = np.ones(3, np.float32) if resp is None else np.asarray(resp, np.float32)
        out = out * np.exp(mod[..., None] * r[None, None, :])
    return np.clip(out, 0, 1).astype(np.float32)


def linen_weave(N, seed, period=5, ss=2, slub=1.0, contrast=0.22):
    """Procedural plain-weave linen luminance (mean 1), seamlessly periodic (N % period == 0).
    period = thread pitch in output px.  Yarns are slubbed (long thick/thin, brighter/darker
    stretches along each thread), wander slightly, vary in tone per thread and carry fibre fuzz;
    `contrast` is the depth of the over/under weave relief.  Rendered at ss x supersampling."""
    assert N % period == 0
    M_ = N * ss
    p = period * ss
    nt = N // period
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:M_, 0:M_].astype(np.float32)
    dx = (periodic_noise(M_, M_, seed + 1, 6 * ss, sigma_y=90 * ss) * 0.10 +
          periodic_noise(M_, M_, seed + 11, 60 * ss, sigma_y=300 * ss) * 0.25) * p
    dy = (periodic_noise(M_, M_, seed + 2, 90 * ss, sigma_y=6 * ss) * 0.10 +
          periodic_noise(M_, M_, seed + 12, 300 * ss, sigma_y=60 * ss) * 0.25) * p
    u, v = (xx + dx) / p, (yy + dy) / p
    iu, iv = np.floor(u).astype(np.int32) % nt, np.floor(v).astype(np.int32) % nt
    fu, fv = u - np.floor(u), v - np.floor(v)
    yi, xi = yy.astype(np.int32), xx.astype(np.int32)
    # slubs: long-correlated thickness/brightness along each yarn (+ occasional fat slub)
    ws = periodic_noise(M_, nt, seed + 3, 1e-3, sigma_y=22 * ss)
    fs = periodic_noise(nt, M_, seed + 4, 22 * ss, sigma_y=1e-3)
    ws = ws + 1.6 * smoothstep(1.4, 2.4, periodic_noise(M_, nt, seed + 13, 1e-3, sigma_y=30 * ss))
    fs = fs + 1.6 * smoothstep(1.4, 2.4, periodic_noise(nt, M_, seed + 14, 30 * ss, sigma_y=1e-3))
    sw, sf = ws[yi, iu], fs[iv, xi]
    tw = np.clip(0.78 + slub * 0.10 * sw, 0.5, 1.15)
    tf = np.clip(0.78 + slub * 0.10 * sf, 0.5, 1.15)
    tone_w = (1 + 0.045 * rng.standard_normal(nt).astype(np.float32))[iu] * (1 + 0.035 * slub * np.tanh(sw))
    tone_f = (1 + 0.045 * rng.standard_normal(nt).astype(np.float32))[iv] * (1 + 0.035 * slub * np.tanh(sf))
    pw = np.clip(1 - ((fu - 0.5) / (0.5 * tw)) ** 2, 0, 1)
    pf = np.clip(1 - ((fv - 0.5) / (0.5 * tf)) ** 2, 0, 1)
    top_warp = ((iu + iv) % 2 == 0)
    hw = np.sqrt(pw) * (0.8 + 0.2 * np.sin(np.pi * fv))
    hf = np.sqrt(pf) * (0.8 + 0.2 * np.sin(np.pi * fu))
    h = np.where(top_warp, np.maximum(hw, 0.6 * hf), np.maximum(hf, 0.6 * hw))
    tone = np.where(top_warp, tone_w, tone_f)
    cover = np.clip(np.maximum(pw, pf), 0, 1)
    lumv = (1 - contrast + contrast * h) * tone * (0.88 + 0.12 * np.sqrt(cover))
    lumv = lumv * (1 + 0.03 * periodic_noise(M_, M_, seed + 5, 0.8 * ss))
    out = cv2.resize(lumv.astype(np.float32), (N, N), interpolation=cv2.INTER_AREA)
    return out / out.mean()


def make_linen_plain(seed=8):
    """linen_plain: ivory plain-weave linen, procedural: slubbed yarns, per-thread tone,
    wandering threads, fibre fuzz, very soft cloth undulation.  Palette linen colour, thread
    pitch 5 px (320 threads per tile).  Flat-lit so it can be shaded in the collage."""
    N = SW
    weave = linen_weave(N, seed, period=5)
    soft = fbm(N, N, seed + 20, 320, 3)
    wx, wy = fbm(N, N, seed + 21, 300, 3) * 80, fbm(N, N, seed + 22, 300, 3) * 80
    folds = warp_periodic(periodic_noise(N, N, seed + 23, 140, sigma_y=360), wx, wy)
    relief = -(np.roll(folds, -2, 1) - np.roll(folds, 2, 1) + np.roll(folds, -2, 0) - np.roll(folds, 2, 0))
    relief /= relief.std() + 1e-6
    L = weave * np.exp(0.018 * soft + 0.022 * relief)
    warm = hexf('#E6DCCA')
    rgb = warm * L[..., None] ** np.array([0.92, 1.0, 1.12], np.float32)[None, None, :]
    rgb = rgb * (warm / np.maximum(rgb.reshape(-1, 3).mean(0), 1e-4))
    return _finish(rgb)


def make_plaster(seed=9):
    """plaster_warm: warm lime plaster. Fine band (scratches, pits, trowel grain) high-passed
    from the wall under the festoon valance (lamps, cords, light pools masked/flattened) and
    quilted at 0.75x; cloudy limewash mottling is periodic procedural noise; colour set to the
    sand/plaster palette."""
    box = (420, 1150, 5880, 2420)
    im = load_src('festoon_valance.png', box=box)
    h, w = im.shape[:2]
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(1530, 1150, 1620, 1600), (1280, 1500, 1860, 1960), (4710, 1150, 4810, 1600),
                           (4460, 1500, 5050, 1960), (3560, 1150, 3760, 1360), (5820, 1150, 5880, 2420)]:
        m[max(0, y0 - box[1]):y1 - box[1], max(0, x0 - box[0]):x1 - box[0]] = False
    im = flatten_light(im, 22, mask=m.astype(np.float32), per_channel=True)
    im = rescale(im, 0.75)
    m = cv2.resize(m.astype(np.uint8), (im.shape[1], im.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    m = cv2.erode(m.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    hi = quilt([im], SW, (210, 210), (50, 50), seed=seed, masks=[m], tol=0.2, reuse=2.0, feather=2.0)
    N = SW
    wx, wy = fbm(N, N, seed + 1, 260, 3) * 60, fbm(N, N, seed + 2, 260, 3) * 60
    cloud = warp_periodic(fbm(N, N, seed + 3, 220, 5, gain=0.55), wx, wy)
    wash = smoothstep(-0.2, 1.6, warp_periodic(fbm(N, N, seed + 4, 140, 4), wy, wx))
    trowel = warp_periodic(periodic_noise(N, N, seed + 5, 60, sigma_y=34), wx * 1.6, wy * 2.2)
    mod = 0.05 * cloud + 0.018 * trowel - 0.05 * wash
    return _finish(_recolor(hi, hexf('#D3BFA1'), mod, resp=[0.85, 1.0, 1.3]))


def make_steel(seed=31, N=SW):
    """steel_brushed: satin/brushed stainless steel (procedural, horizontal grain).  Long
    anisotropic brushing lines at three scales, sparse longer scratches, faint broad sheen
    bands along the grain (no perspective gradient), cool steel palette colour."""
    rng = np.random.default_rng(seed)
    wy = periodic_noise(N, N, seed + 1, 400, sigma_y=300) * 3.0      # gentle waviness of the grain
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    fine = warp_periodic(periodic_noise(N, N, seed + 2, 70, sigma_y=0.5), np.zeros_like(wy), wy)
    mid = warp_periodic(periodic_noise(N, N, seed + 3, 220, sigma_y=1.1), np.zeros_like(wy), wy)
    coarse = warp_periodic(periodic_noise(N, N, seed + 4, 700, sigma_y=4.0), np.zeros_like(wy), wy)
    micro = periodic_noise(N, N, seed + 7, 0.6)
    bands = periodic_noise(N, N, seed + 5, 1200, sigma_y=60)
    blot = fbm(N, N, seed + 6, 220, 3)
    # sparse scratches: thin, long, nearly horizontal lines with fading ends (periodic)
    S = N * 2
    cv = np.zeros((S, S), np.float32)
    for _ in range(140):
        x0, y0 = rng.random() * S, rng.random() * S
        L = rng.uniform(80, 520) * 2
        ang = np.deg2rad(rng.normal(0, 1.2))
        val = rng.uniform(0.25, 1.0) * (1 if rng.random() < 0.7 else -1)
        n = int(L / 3)
        t = np.linspace(0, 1, n)
        px, py = x0 + np.cos(ang) * L * t, y0 + np.sin(ang) * L * t
        prof = np.sin(np.pi * t) ** 0.6 * val
        ix, iy = np.mod(np.round(px).astype(int), S), np.mod(np.round(py).astype(int), S)
        np.add.at(cv, (iy, ix), prof)
        np.add.at(cv, (iy, np.mod(ix + 1, S)), prof * 0.6)
    cv = gblur(cv, 0.7, mode='wrap')
    scr = cv2.resize(cv, (N, N), interpolation=cv2.INTER_AREA)
    scr = scr / (np.abs(scr).max() + 1e-6)
    L = (0.73 + 0.022 * fine + 0.014 * mid + 0.010 * coarse + 0.018 * bands + 0.010 * blot
         + 0.006 * micro + 0.045 * scr)
    base = hexf('#B8BCBD')
    cool = hexf('#AEB6BA')
    t = smoothstep(-1.5, 1.5, bands)[..., None]
    col = base * (1 - 0.35 * t) + cool * 0.35 * t
    rgb = col * (L / 0.73)[..., None]
    return _finish(rgb)


TERRAZZO_CHIPS = [  # (palette colour, weight, lightness jitter)
    ('#B4603F', 0.26, 0.10),   # terracotta / brick
    ('#C27A58', 0.08, 0.08),   # lighter terracotta
    ('#97A07C', 0.17, 0.08),   # sage
    ('#C99A4A', 0.15, 0.08),   # ochre
    ('#8E8C88', 0.14, 0.12),   # warm grey
    ('#5F5E5C', 0.05, 0.10),   # dark grey
    ('#F4F0E8', 0.15, 0.03),   # white marble
]


def _chip_polygon(rng, r, elong=1.5, n=None):
    """Angular, slightly irregular stone chip outline (convex-ish polygon) of radius ~r."""
    n = n or int(rng.integers(5, 10))
    ang = np.sort(rng.random(n) * 2 * np.pi)
    rad = r * (0.70 + 0.30 * rng.random(n))
    e = rng.uniform(1.0, elong)
    rot = rng.random() * np.pi
    x, y = rad * np.cos(ang) * e, rad * np.sin(ang) / e
    c, s = np.cos(rot), np.sin(rot)
    return np.stack([x * c - y * s, x * s + y * c], 1)


def make_terrazzo(seed=41, N=SW, ss=2):
    """terrazzo_cream: polished cream terrazzo.  Cream cement matrix with fine multicoloured
    sand, cloudy polish and rare pores; angular chips in three size classes (large / medium /
    small) in terracotta, sage, ochre, grey and white marble, each with its own internal stone
    mottle, a faint darker rim (cut edge) and no overlaps; everything wraps around, so the tile
    is seamless.  Rendered at 2x and area-downsampled for clean anti-aliased chip edges."""
    rng = np.random.default_rng(seed)
    S = N * ss
    ids = np.zeros((S, S), np.int32)
    chips = []                       # (colour rgb, mottle amp, grain amp)
    cols = [c for c, _, _ in TERRAZZO_CHIPS]
    w = np.array([wt for _, wt, _ in TERRAZZO_CHIPS], np.float64)
    w /= w.sum()
    classes = [(52, 26, 42), (26, 120, 18), (11, 900, 7), (5.5, 2600, 3.5)]   # (radius px, count, min gap)
    for r0, count, gap in classes:
        placed, tries = 0, 0
        while placed < count and tries < count * 12:
            tries += 1
            r = r0 * rng.uniform(0.7, 1.3) * ss
            poly = _chip_polygon(rng, r)
            # rough the outline a little (subdivide + jitter)
            P = np.repeat(poly, 3, 0)
            nxt = np.roll(poly, -1, 0).repeat(3, 0)
            t = np.tile([0, 1 / 3, 2 / 3], len(poly))[:, None]
            P = P * (1 - t) + nxt * t + rng.normal(0, max(0.6, r * 0.035), P.shape)
            R = int(np.ceil(np.abs(P).max())) + 2
            cx, cy = rng.random() * S, rng.random() * S
            loc = np.zeros((2 * R + 1, 2 * R + 1), np.uint8)
            pts = np.round((P + R + (cx % 1, cy % 1)) * 16).astype(np.int32)
            cv2.fillPoly(loc, [pts], 1, cv2.LINE_8, 4)
            rows = (int(cy) - R + np.arange(2 * R + 1)) % S
            cls = (int(cx) - R + np.arange(2 * R + 1)) % S
            sub = ids[np.ix_(rows, cls)]
            g = int(gap * ss)
            grown = cv2.dilate(loc, np.ones((2 * g + 1, 2 * g + 1), np.uint8)) if g > 0 else loc
            if (sub[grown > 0] > 0).any():
                continue
            k = int(rng.choice(len(cols), p=w))
            base = hexf(cols[k]) * (1 + rng.normal(0, TERRAZZO_CHIPS[k][2]))
            chips.append((np.clip(base, 0, 1), rng.uniform(0.025, 0.075), rng.uniform(0.015, 0.05),
                          k))
            sub = np.where(loc > 0, len(chips), sub)
            ids[np.ix_(rows, cls)] = sub
            placed += 1
    nc = len(chips)
    lut = np.zeros((nc + 1, 3), np.float32)
    mot = np.zeros(nc + 1, np.float32)
    grn = np.zeros(nc + 1, np.float32)
    for i, (c, m, g, k) in enumerate(chips):
        lut[i + 1], mot[i + 1], grn[i + 1] = c, m, g
    # matrix
    matrix = hexf('#E9E0CE')
    cloud = fbm(S, S, seed + 1, 160 * ss, 4)
    sand_n = periodic_noise(S, S, seed + 2, 0.6 * ss)
    rgb = np.empty((S, S, 3), np.float32)
    rgb[:] = matrix
    rgb *= (1 + 0.025 * cloud + 0.025 * sand_n)[..., None]
    # fine sand grains in the matrix (sub-chip size, many colours)
    sand = rng.random((S, S)) < 0.010
    sand_col = np.stack([hexf(c) for c in ('#B4603F', '#97A07C', '#C99A4A', '#8E8C88', '#5F5E5C',
                                           '#D9CDB8')])
    sc_idx = rng.integers(0, len(sand_col), (S, S))
    grain_rgb = sand_col[sc_idx]
    sand = cv2.dilate(sand.astype(np.uint8), np.ones((2, 2), np.uint8)).astype(np.float32)
    rgb = rgb * (1 - 0.55 * sand[..., None]) + grain_rgb * 0.55 * sand[..., None]
    # chips
    inside = ids > 0
    mott = fbm(S, S, seed + 3, 9 * ss, 3)
    vein = periodic_noise(S, S, seed + 4, 1.0 * ss)
    chip_rgb = lut[ids] * (1 + mot[ids][..., None] * mott[..., None] + grn[ids][..., None] * vein[..., None])
    # cut-edge rim: slightly darker 1-2 px band inside each chip, faint halo in matrix
    dist_in = cv2.distanceTransform(inside.astype(np.uint8), cv2.DIST_L2, 3)
    rim = np.exp(-dist_in / (1.2 * ss))
    chip_rgb *= (1 - 0.10 * rim)[..., None]
    rgb = np.where(inside[..., None], chip_rgb, rgb)
    dist_out = cv2.distanceTransform((~inside).astype(np.uint8), cv2.DIST_L2, 3)
    rgb *= (1 - 0.05 * np.exp(-dist_out / (1.0 * ss)) * (~inside))[..., None]
    # pores: rare tiny dark pits in the matrix
    pores = (rng.random((S, S)) < 0.00025) & ~inside
    pores = gblur(cv2.dilate(pores.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), 0.8, 'wrap')
    rgb *= (1 - 0.45 * np.clip(pores * 2, 0, 1))[..., None]
    # polish: very faint broad sheen variation
    rgb *= (1 + 0.012 * fbm(S, S, seed + 5, 400 * ss, 2))[..., None]
    out = cv2.resize(np.clip(rgb, 0, 1), (N, N), interpolation=cv2.INTER_AREA)
    return _finish(out)


def key_foliage(im):
    """Key foliage (leaves + twigs) off a bright, neutral sky/skylight.  Returns RGBA with
    1-2 px anti-aliased edges; the source's violet sharpening fringe is treated as background
    and edge colours are replaced by colour bled from the solid leaf interior (no white or
    violet halos on dark backgrounds)."""
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    L = lum(im)
    mx, mn = im.max(-1), im.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-3)
    # background = bright neutral sky AND the grey/white skylight mullions (low saturation,
    # mid-to-high luminance); foreground = saturated leaves or dark twigs
    sky = (1 - smoothstep(0.20, 0.34, sat)) * smoothstep(0.30, 0.42, L)
    fringe = smoothstep(0.0, 0.06, b - g) * (1 - sky)
    f = cv2.GaussianBlur(np.clip((1 - sky) * (1 - fringe), 0, 1).astype(np.float32), (0, 0), 0.7)
    alpha = smoothstep(0.35, 0.70, f)
    core = (alpha > 0.95) & (fringe < 0.05)
    core = cv2.erode(core.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32)
    bl = []
    for sg in (2.5, 8, 24):
        num = cv2.GaussianBlur(im * core[..., None], (0, 0), sg)
        den = cv2.GaussianBlur(core, (0, 0), sg)
        bl.append((num / np.maximum(den, 1e-4)[..., None], den))
    bleed = np.where((bl[0][1] > 0.02)[..., None], bl[0][0],
                     np.where((bl[1][1] > 0.01)[..., None], bl[1][0], bl[2][0]))
    near = cv2.dilate((1 - core).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    rgb = np.where(near[..., None], bleed, im)
    return np.dstack([np.clip(rgb, 0, 1), alpha]).astype(np.float32)


def make_greenery(seed=12):
    """greenery: RGBA foliage overlay — the void tree's pinnate canopy keyed off the skylight in
    void_lookup_B.png (alpha = leaves/twigs, sky transparent), quilted toroidally in
    premultiplied RGBA so it tiles seamlessly."""
    box = (1050, 850, 2800, 2000)
    im = load_src('void_lookup_B.png', box=box)
    rgba = key_foliage(im)
    del im
    H, W = rgba.shape[:2]
    poly = np.array([(1050, 1000), (2700, 850), (2700, 1250), (2560, 1500), (2560, 2000), (1100, 2000),
                     (1050, 1700)], np.float32) - box[:2]
    vm = np.zeros((H, W), np.uint8)
    cv2.fillPoly(vm, [poly.astype(np.int32)], 1)
    pm = rgba.copy()
    pm[..., :3] *= pm[..., 3:4]
    pm = rescale(pm, 0.9)
    vm = cv2.resize(vm, (pm.shape[1], pm.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    dens = gblur(pm[..., 3], 70)
    vm &= dens > 0.42                    # only the full part of the crown (even density when tiled)
    tex = quilt([pm], SW, (200, 200), (40, 40), seed=seed, masks=[vm], tol=0.2, reuse=2.0, feather=1.0)
    a = np.clip(tex[..., 3:4], 0, 1)
    rgb = np.where(a > 1e-3, tex[..., :3] / np.maximum(a, 1e-3), 0)
    return _finish(np.dstack([np.clip(rgb, 0, 1), a]))


# --------------------------------------------------------------------------- #
# B) generators
# --------------------------------------------------------------------------- #

def _fibres(h, w, rng, n, lmin, lmax, width=1.0, curl=0.35, ss=2):
    """Anti-aliased thin curved fibre strokes -> coverage map (h, w) in 0..1 with per-fibre
    intensity.  Rendered at ss x and area-downsampled."""
    H, W = h * ss, w * ss
    cv = np.zeros((H, W), np.uint8)
    for _ in range(n):
        L = rng.uniform(lmin, lmax) * ss
        k = int(rng.integers(12, 18))
        a0 = rng.uniform(0, 2 * np.pi)
        da = rng.normal(0, curl / 2.6, k)          # many small turns: a smooth curve, never a zigzag
        ang = a0 + np.cumsum(da)
        step = L / k
        x, y = rng.uniform(-L, W + L), rng.uniform(-L, H + L)
        pts = [(x, y)]
        for a in ang:
            x, y = x + np.cos(a) * step, y + np.sin(a) * step
            pts.append((x, y))
        P = np.array(pts)
        for _ in range(2):                          # Chaikin corner cutting
            Q = 0.75 * P[:-1] + 0.25 * P[1:]
            R = 0.25 * P[:-1] + 0.75 * P[1:]
            P = np.vstack([P[:1], np.stack([Q, R], 1).reshape(-1, 2), P[-1:]])
        p = np.round(P * 16).astype(np.int32)
        val = int(rng.uniform(90, 255))
        th = max(1, int(round(width * ss * rng.uniform(0.6, 1.3))))
        cv2.polylines(cv, [p], False, val, th, cv2.LINE_AA, 4)
    return cv2.resize(cv.astype(np.float32) / 255.0, (w, h), interpolation=cv2.INTER_AREA)


def paper_linen(h=A3[0], w=A3[1], seed=1, color='#EEE5D3', mottle=0.022, fibre=1.0):
    """Warm linen paper ground (RGB float).  Deliberately low-entropy so it can be a full-canvas
    PSD layer: smooth, soft cloudy mottling (periodic fbm, large scale) + a faint felt 'tooth'
    (smooth, ~4 px, ~1 level) + sparse fine fibres (dark tan and light), no per-pixel noise.
    The mottle/tooth fields are periodic but fibres are not wrapped, so treat it as a single
    full-canvas sheet rather than a tile."""
    rng = np.random.default_rng(seed)
    base = hexf(color)
    m1 = fbm(h, w, seed + 1, 420, 3, gain=0.5)
    m2 = fbm(h, w, seed + 2, 120, 2, gain=0.5)
    tooth = periodic_noise(h, w, seed + 3, 4.0)
    L = 1 + mottle * (0.75 * m1 + 0.25 * m2) + 0.0035 * tooth
    warm = smoothstep(0.4, 2.0, fbm(h, w, seed + 4, 600, 2))
    rgb = base[None, None, :] * L[..., None]
    rgb = rgb * (1 - 0.010 * warm[..., None]) + hexf('#E8D9BE') * 0.010 * warm[..., None]
    area = h * w / 1e6
    if fibre > 0:
        dark = _fibres(h, w, rng, int(70 * area * fibre), 12, 55, 0.9)
        light = _fibres(h, w, rng, int(50 * area * fibre), 10, 40, 1.1)
        rare = _fibres(h, w, rng, int(4 * area * fibre), 30, 90, 1.0, curl=0.5)
        rgb = rgb * (1 - 0.08 * dark[..., None]) + hexf('#B9A07A') * 0.08 * dark[..., None]
        rgb = rgb * (1 - 0.14 * rare[..., None]) + hexf('#9C8462') * 0.14 * rare[..., None]
        rgb = rgb + (1 - rgb) * 0.25 * light[..., None]
    return _finish(rgb)


def grain(h=A3[0], w=A3[1], seed=2, amount=0.05):
    """Neutral film grain for an overlay / soft-light layer: mid-grey (0.5) +/- amount, two grain
    sizes (fine 0.6 px dominant + clumped 1.4 px), luminance only, gently gamma-shaped so
    highlights and shadows of the grain are not symmetric (photographic).  Returns (h, w)."""
    a = periodic_noise(h, w, seed, 0.6)
    b = periodic_noise(h, w, seed + 1, 1.4)
    g = 0.8 * a + 0.45 * b
    g = g / g.std()
    g = np.tanh(g * 0.8) / np.tanh(0.8 * 2.5) * 2.5 / 2.5     # soft clip of the tails
    g = g / g.std()
    return np.clip(0.5 + amount * g, 0, 1).astype(np.float32)


def _noise_field(h, w, rng, sigma):
    """Non-periodic smooth unit-std noise of feature size sigma (fast for large sigma)."""
    if sigma < 6:
        n = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), sigma)
    else:
        f = max(1, int(sigma // 3))
        hs, ws = h // f + 3, w // f + 3
        n = cv2.GaussianBlur(rng.standard_normal((hs, ws)).astype(np.float32), (0, 0), sigma / f)
        n = cv2.resize(n, (ws * f, hs * f), interpolation=cv2.INTER_CUBIC)[:h, :w]
    return n / (n.std() + 1e-8)


def _sdf(mask):
    """Signed distance (px), positive inside, from a float/bool mask (threshold 0.5)."""
    m = (np.asarray(mask) > 0.5).astype(np.uint8)
    din = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    dout = cv2.distanceTransform(1 - m, cv2.DIST_L2, 5)
    return (din - dout + np.where(m > 0, -0.5, 0.5)).astype(np.float32)


def _with_bbox(mask, pad, fn):
    """Run fn on the padded bounding-box crop of a mask and paste back into a full-size array."""
    m = np.asarray(mask, np.float32)
    ys, xs = np.nonzero(m > 0.5)
    if not len(xs):
        return None
    y0, y1 = max(0, ys.min() - pad), min(m.shape[0], ys.max() + 1 + pad)
    x0, x1 = max(0, xs.min() - pad), min(m.shape[1], xs.max() + 1 + pad)
    res = fn(m[y0:y1, x0:x1])
    out = np.zeros(m.shape + res.shape[2:], np.float32)
    out[y0:y1, x0:x1] = res
    return out


def torn_mask(mask, seed=0, roughness=1.0, scale=1.0):
    """Roughen the edge of any binary mask like torn paper.  The edge wanders at three scales
    (long tear drift, mid jaggies, fine fibrous serration), biased so tears bite inward a bit
    more than they bulge; result is anti-aliased float 0..1, same size as `mask`.
    roughness scales displacement amplitude, scale scales feature sizes (both ~1 at 300 ppi)."""
    rng = np.random.default_rng(seed)
    amp = roughness * scale

    def run(m):
        h, w = m.shape
        d = _sdf(m)
        n = (9.0 * _noise_field(h, w, rng, 60 * scale) +
             3.2 * _noise_field(h, w, rng, 9 * scale) +
             1.1 * _noise_field(h, w, rng, 2.2 * scale) +
             0.45 * _noise_field(h, w, rng, 0.8))
        # sharpen the jaggies a little (torn paper has crisp micro-points)
        n2 = _noise_field(h, w, rng, 4 * scale)
        n += 1.4 * (np.abs(n2) - 0.8) * np.sign(n2) ** 2
        f = d + amp * n - 1.5 * amp
        return np.clip(0.5 + f / 1.1, 0, 1).astype(np.float32)

    pad = int(40 * amp + 10)
    out = _with_bbox(mask, pad, run)
    return np.zeros_like(np.asarray(mask, np.float32)) if out is None else out


def deckle_rgba(mask, seed=0, width=6.0, color='#FBF8F2', fibres=1.0):
    """Thin white fibrous torn-edge strip as its own RGBA layer (place above the torn image,
    normal blend).  Along the inside of the (torn) mask edge a white paper-core band of varying
    width (0.25..1.6 x `width` px) with a feathered, fibrous inner boundary; outside the edge,
    sparse hair-like fibres and fuzz up to ~4 px.  Same size as `mask`."""
    rng = np.random.default_rng(seed)
    col = hexf(color)

    def run(m):
        h, w = m.shape
        d = _sdf(m)
        wv = width * np.clip(0.9 + 0.55 * _noise_field(h, w, rng, 45) + 0.25 * _noise_field(h, w, rng, 8),
                             0.25, 1.6)
        fz = _noise_field(h, w, rng, 1.0)
        inner = 1 - smoothstep(wv - 1.8, wv + 0.6 + 0.8 * np.clip(fz, -1.5, 1.5), d)   # band inside the edge
        edge_in = np.clip(0.5 + d / 0.9, 0, 1)                          # inside the torn mask
        band = inner * edge_in
        # outside fuzz + fibres
        out_d = np.maximum(-d, 0)
        fuzz = smoothstep(0.2, 1.2, fz + 0.3) * np.exp(-out_d / 1.2) * (d < 0.5)
        fb = _fibres(h, w, rng, int(fibres * (h + w) * 0.9), 3, 12, 0.7, curl=0.5)
        fb = fb * np.exp(-out_d / 3.0) * (out_d < 6) * (d < 1.0)
        a = np.clip(np.maximum(band * 0.97, np.maximum(fuzz * 0.55, fb * 0.75)), 0, 1)
        # subtle shading: band slightly greyer where thin/deep (fibre shadow)
        shade = 1 - 0.06 * smoothstep(0, 1, d / np.maximum(wv, 1)) - 0.03 * np.abs(fz)
        rgb = col[None, None, :] * shade[..., None]
        return np.dstack([np.clip(rgb, 0, 1), a]).astype(np.float32)

    out = _with_bbox(mask, int(width * 3 + 12), run)
    if out is None:
        return np.zeros(np.asarray(mask).shape + (4,), np.float32)
    return out


def drop_shadow(alpha, dx=14, dy=20, blur=22, opacity=0.42, color='#2B2420', contact=0.35):
    """Soft paper-cut drop shadow as an RGBA layer.  Two components: a tight contact shadow
    (offset/4, blur/4) and the main soft shadow; opacity is baked into alpha.
    Returns (rgba, ox, oy): place the layer at (x + ox, y + oy) where (x, y) is the position of
    `alpha`'s top-left.  Suggested blend: multiply (or normal) beneath the casting layer."""
    a = np.asarray(alpha, np.float32)
    pad = int(np.ceil(blur * 3)) + int(max(abs(dx), abs(dy))) + 2
    P = np.pad(a, pad)
    M1 = np.float32([[1, 0, dx], [0, 1, dy]])
    M2 = np.float32([[1, 0, dx / 4], [0, 1, dy / 4]])
    s1 = gblur(cv2.warpAffine(P, M1, (P.shape[1], P.shape[0]), flags=cv2.INTER_LINEAR), blur)
    s2 = gblur(cv2.warpAffine(P, M2, (P.shape[1], P.shape[0]), flags=cv2.INTER_LINEAR), max(0.8, blur / 4))
    sa = np.clip((1 - contact) * s1 + contact * s2 * 1.3, 0, 1) * opacity
    rgba = np.zeros(P.shape + (4,), np.float32)
    rgba[..., :3] = hexf(color)
    rgba[..., 3] = sa
    return rgba, -pad, -pad


def watercolour_wash(mask, color, seed=0, opacity=0.85, edge=1.0, granulation=1.0, blooms=3,
                     wobble=1.0):
    """Organic watercolour pigment wash in `color` inside `mask` (same-size RGBA, straight
    alpha = pigment density; use multiply or normal).  Features: wobbly, slightly bled outline;
    uneven pigment (soft fbm pooling); darker dried edge (edge-darkening 'coffee ring');
    pigment granulation (fine speckle that settles in the paper's tooth); `blooms` cauliflower
    back-runs (paler centres with darker frilly rims); subtle hue shift where dense."""
    rng = np.random.default_rng(seed)
    base = hexf(color)

    def run(m):
        h, w = m.shape
        d = _sdf(m)
        n_low = _noise_field(h, w, rng, 70)
        n_mid = _noise_field(h, w, rng, 14)
        n_fine = _noise_field(h, w, rng, 2.5)
        f = d + wobble * (7 * n_low + 2.2 * n_mid + 0.6 * n_fine)
        cover = smoothstep(-0.8, 1.2, f)
        dist = np.maximum(f, 0)
        # soft pigment pooling (large, gentle), slightly heavier towards one side (gravity)
        pool = (0.64 + 0.15 * _noise_field(h, w, rng, 150) + 0.05 * _noise_field(h, w, rng, 45)
                + 0.04 * np.linspace(-1, 1, h, dtype=np.float32)[:, None])
        rim = edge * (0.40 * np.exp(-dist / 3.0) * (0.75 + 0.25 * np.tanh(n_mid))
                      + 0.10 * np.exp(-dist / 16))
        dens = pool + rim
        # blooms (back-runs): pale centre, thin dark cauliflower rim with fractal outline
        ys, xs = np.nonzero(f > 25)
        yy, xx = np.ogrid[:h, :w]
        centres = []
        for _ in range(int(blooms)):
            if not len(xs):
                break
            R = rng.uniform(0.05, 0.13) * np.sqrt(h * w)
            for _try in range(30):          # keep blooms apart
                q = int(rng.integers(len(xs)))
                cy, cx = ys[q], xs[q]
                if all(np.hypot(cy - a, cx - b) > 1.6 * (R + rb) for a, b, rb in centres):
                    break
            centres.append((cy, cx, R))
            ang = np.arctan2(yy - cy, xx - cx).astype(np.float32)
            frill = np.zeros_like(ang)
            for k in range(2, 28):
                frill += rng.normal(0, 1) / k ** 1.05 * np.cos(k * ang + rng.uniform(0, 2 * np.pi))
            frill = 1 + 0.22 * frill / max(0.3, float(np.abs(frill).max())) + 0.05 * n_mid + 0.02 * n_fine
            r = np.hypot(yy - cy, xx - cx).astype(np.float32) / (R * frill)
            inside = 1 - smoothstep(0.80, 1.0, r)
            ring = np.exp(-((r - 0.985) / 0.022) ** 2) * (0.7 + 0.3 * np.tanh(n_fine))
            dens = dens * (1 - 0.24 * inside) + 0.20 * ring * cover
        # granulation: fine pigment particles settling in the paper tooth (stronger where dense)
        gran = granulation * (0.055 * _noise_field(h, w, rng, 1.2) + 0.035 * _noise_field(h, w, rng, 0.7))
        dens = np.clip(dens * (1 + gran * (0.6 + dens)), 0, 1.2)
        a = np.clip(cover * dens * opacity, 0, 1)
        t = np.clip((dens - 0.65) * 0.8, -0.3, 0.5)[..., None]
        rgb = np.clip(base * (1 - 0.30 * t) - 0.03 * t, 0, 1)
        return np.dstack([rgb, a]).astype(np.float32)

    out = _with_bbox(mask, 40, run)
    if out is None:
        return np.zeros(np.asarray(mask).shape + (4,), np.float32)
    return out


def halftone(gray, cell=12, angle=45.0, gain=1.0):
    """AM halftone screen: returns ink coverage (0..1 float, 1 = ink) for a gray image
    (0 = black ... 1 = white).  Round dots that merge into a chequer at mid-tones (classic
    cosine spot function), rotated by `angle`, anti-aliased analytically."""
    g = np.asarray(gray, np.float32)
    if g.ndim == 3:
        g = lum(g)
    h, w = g.shape
    dark = np.clip((1 - gblur(g, cell * 0.35)) * gain, 0, 1)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = np.deg2rad(angle)
    u = (xx * np.cos(t) + yy * np.sin(t)) * (2 * np.pi / cell)
    v = (-xx * np.sin(t) + yy * np.cos(t)) * (2 * np.pi / cell)
    spot = 0.5 - 0.25 * (np.cos(u) + np.cos(v))          # 0 at dot centre .. 1 between dots
    # the threshold that gives area coverage == dark is ~ dark itself for this spot function
    gm = np.hypot(*np.gradient(spot)) + 1e-4
    return np.clip(0.5 + (dark - spot) / gm, 0, 1).astype(np.float32)


def paper_cut_edge(mask, light=(-0.6, -0.8), width=3.0, strength=0.55, rim=0.35):
    """Subtle bevel / lit cut edge for 2.5D card planes, as an RGBA layer (normal blend, above
    the card).  Edges facing the light (`light` = 2-D direction towards the light, image coords)
    get a soft highlight, edges facing away a soft shade, plus a thin even white 'paper core'
    rim.  `width` = bevel width px.  Same size as `mask`."""
    lx, ly = np.asarray(light, np.float32) / (np.hypot(*light) + 1e-6)

    def run(m):
        d = _sdf(m)
        ds = gblur(d, 1.2)
        gy, gx = np.gradient(ds)
        gn = np.hypot(gx, gy) + 1e-6
        nx, ny = -gx / gn, -gy / gn                       # outward normal
        facing = nx * lx + ny * ly                         # +1 lit, -1 shaded
        bev = np.exp(-np.maximum(d, 0) / width) * np.clip(0.5 + d / 0.9, 0, 1)
        hi = np.clip(facing, 0, 1) * bev * strength
        sh = np.clip(-facing, 0, 1) * bev * strength * 0.8
        core = np.exp(-np.maximum(d, 0) / 0.8) * np.clip(0.5 + d / 0.9, 0, 1) * rim
        white = np.maximum(hi, core)
        a = np.clip(white + sh, 0, 1)
        t = (white / np.maximum(white + sh, 1e-6))[..., None]
        rgb = t * hexf('#FFFDF7') + (1 - t) * hexf('#2B2420')
        return np.dstack([rgb, a]).astype(np.float32)

    out = _with_bbox(mask, int(width * 4 + 6), run)
    if out is None:
        return np.zeros(np.asarray(mask).shape + (4,), np.float32)
    return out


# --------------------------------------------------------------------------- #
# C) client drape reference
# --------------------------------------------------------------------------- #

DRAPE_BOX = (0, 9, 368, 470)   # content of client_drape_reference.png without its white border
DRAPE_SCALE = 6


def upscale_soft(img, s=DRAPE_SCALE):
    """Best-available classical upscale for a tiny, JPEG-compressed photo: non-local-means
    denoise (removes blocking / mosquito noise) at source res, Lanczos in two stages (2x, then
    the rest), edge-aware smoothing of ringing, then gentle unsharp mask and an imperceptible
    fine grain so the enlargement does not look plastic."""
    u8 = to_u8(img)
    den = cv2.fastNlMeansDenoisingColored(u8, None, 3, 3, 5, 15)
    a = den.astype(np.float32) / 255.0
    h, w = a.shape[:2]
    a = cv2.resize(a, (w * 2, h * 2), interpolation=cv2.INTER_LANCZOS4)
    a = cv2.resize(np.clip(a, 0, 1), (w * s, h * s), interpolation=cv2.INTER_LANCZOS4)
    a = np.clip(a, 0, 1).astype(np.float32)
    a = cv2.bilateralFilter(a, 9, 0.04, 4)
    bl = gblur(a, 4.0)
    a = np.clip(a + 0.45 * (a - bl), 0, 1)
    g = periodic_noise(a.shape[0], a.shape[1], 77, 0.9)
    a = np.clip(a * (1 + 0.006 * g[..., None]), 0, 1)
    return a.astype(np.float32)


def make_drape():
    """Returns (soft RGB, sheer RGBA) versions of the client's drape reference."""
    src = np.asarray(Image.open(P('assets', 'client_drape_reference.png')).convert('RGB')
                     .crop(DRAPE_BOX), np.float32) / 255.0
    soft = upscale_soft(src)
    L = lum(soft)
    lo, hi = np.percentile(L, [2, 99.5])
    Ln = np.clip((L - lo) / (hi - lo), 0, 1)
    grey = np.dstack([L] * 3)
    desat = soft * 0.35 + grey * 0.65
    light = desat + (1 - desat) * 0.45
    light = light * 0.6 + hexf('#F3ECDF') * 0.4 * (light / np.maximum(light.mean((0, 1)), 1e-3))
    alpha = 0.10 + 0.72 * smoothstep(0.05, 1.0, Ln) ** 1.2
    sheer = np.dstack([np.clip(light, 0, 1), alpha])
    return _finish(soft), _finish(sheer)


# --------------------------------------------------------------------------- #
# build: assets, index.json, contact sheet
# --------------------------------------------------------------------------- #

SWATCHES = [
    # name, builder, description, anchors, suggested use
    ('velvet_terracotta', make_velvet,
     'Crushed terracotta velvet (banquette of cabin_interior.png): photographic fine pile band, '
     'periodic procedural crush/sheen, colour response of the real fabric (shadow -> oxblood, '
     'sheen -> orange). Flat-lit, seamless.',
     {'tile_period_px': [1600, 1600]},
     'Clip into cabin banquette / cushion shapes (collage 02); multiply a terracotta->oxblood '
     'gradient on top for depth.'),
    ('oak_fluted', make_oak,
     'Fluted / slatted oak wall from cabin_interior.png: grooves rectified to exactly 50 px pitch '
     '(perfectly vertical), every flute phase normalised to the wall-average profile (evenly '
     'lit), assembled from whole real slats, golden-oak grade.',
     {'tile_period_px': [1600, 1600], 'flute_pitch_px': OAK_PERIOD,
      'groove_centres_x': 'x = 50*k (k = 0..31), plus wrap', 'flutes_per_tile': SW // OAK_PERIOD},
     'Clip into the arched cabin shells / bar counter front; scale so pitch matches the drawing; '
     'keep vertical. Add a soft vertical light falloff per plane in the collage.'),
    ('marble', make_marble,
     'Warm-white polished marble with the cabin table character: gold-ochre veins with bleed, '
     'fine grey crackle network and nests, pepper flecks, clouding. Procedural (colours sampled '
     'from the table top), crisp at any scale, seamless.',
     {'tile_period_px': [1600, 1600]},
     'Table tops (ellipse-warp), bar top, sills.'),
    ('linen_glow', make_linen_glow,
     'Back-lit honey linen festoon swags (ceiling_lookup_A.png): swag columns rectified to 400 px, '
     'glow gradients flattened, lattice-quilted so seams run along gather lines.',
     {'tile_period_px': [1600, 1600], 'swag_column_width_px': 400,
      'gather_lines_x': [0, 400, 800, 1200]},
     'Ceiling draping planes (both collages): perspective-warp onto ceiling quads; screen/soft-'
     'light a honey glow on top.'),
    ('linen_plain', make_linen_plain,
     'Ivory plain-weave linen (procedural): slubbed yarns, per-thread tone, wandering threads, '
     'fibre fuzz, very soft cloth undulation. Thread pitch 5 px. Flat-lit, seamless.',
     {'tile_period_px': [1600, 1600], 'thread_pitch_px': 5},
     'Sheer / blind / curtain planes, label cards, base for translucent overlays (multiply or '
     'soft light at low opacity over photos for a linen-print feel).'),
    ('plaster_warm', make_plaster,
     'Warm lime plaster (wall under festoon_valance.png): real fine detail (scratches, pits, '
     'trowel grain) quilted, cloudy limewash mottle procedural, sand/plaster colour. Seamless.',
     {'tile_period_px': [1600, 1600]},
     'Wall planes, void drum, background card planes.'),
    ('glassblock', make_glassblock,
     '3 x 3 mosaic of real wavy glass blocks from glassblock_wall_A.png, re-gridded on the mortar: '
     'every block resampled to its cell, equal 18 px joints, mortar tone equalised; repeats '
     'exactly on the mortar grid.',
     {'tile_period_px': [1600, 1600], 'mortar_centre_lines_x': [0, 533, 1067],
      'mortar_centre_lines_y': [0, 533, 1067], 'joint_width_px': 2 * GB_HALF_JOINT,
      'block_pitch_px': [533, 534, 533]},
     'Glass-brick facade / screen (collage 01 facade, collage 02 edge screen). Tile with an '
     'offset that keeps mortar lines on the grid; overlay dusk/amber gradients in soft light.'),
    ('steel_brushed', make_steel,
     'Brushed stainless steel (procedural): horizontal grain at 3 scales, sparse scratches, broad '
     'satin bands, cool steel colour. Seamless.',
     {'tile_period_px': [1600, 1600], 'grain_direction': 'horizontal (x)'},
     'Void rail ring, bar details, pendants; rotate to follow the rail direction.'),
    ('terrazzo_cream', make_terrazzo,
     'Polished cream terrazzo (procedural): cream cement matrix with fine coloured sand, chips in '
     '4 size classes (terracotta, sage, ochre, warm/dark grey, white marble) with internal '
     'mottle and cut-edge rims, faint polish. Seamless.',
     {'tile_period_px': [1600, 1600]},
     'Floors (perspective warp), sills, table bases, swatch cards.'),
    ('greenery', make_greenery,
     'RGBA foliage overlay: the void tree canopy keyed off the skylight (void_lookup_B.png), '
     'violet fringe removed, edge colour decontaminated, quilted in premultiplied RGBA. '
     'Transparent where sky. Seamless.',
     {'tile_period_px': [1600, 1600], 'mean_alpha': None},
     'Canopy fill / leafy overlays around the tree (collage 01), shadow-play (fill black at '
     'low opacity), planters.'),
]


def _font(size, kind='mono'):
    f = {'mono': 'IBMPlexMono-Regular.ttf', 'monol': 'IBMPlexMono-Light.ttf',
         'serif': 'CormorantGaramond-Italic.ttf'}[kind]
    for path in (P('assets', 'fonts', f), '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _rel(path):
    return os.path.relpath(path, ROOT)


def _flat(img, bg='#EFE6D6'):
    img = np.asarray(img, np.float32)
    if img.ndim == 2:
        return np.dstack([img] * 3)
    if img.shape[2] == 4:
        a = img[..., 3:4]
        return img[..., :3] * a + hexf(bg) * (1 - a)
    return img


def _over(dst, src, x=0, y=0, mode='normal'):
    """Composite straight-alpha RGBA src onto RGB dst at (x, y) in place (clipped)."""
    h, w = src.shape[:2]
    y0, x0 = max(0, y), max(0, x)
    y1, x1 = min(dst.shape[0], y + h), min(dst.shape[1], x + w)
    if y1 <= y0 or x1 <= x0:
        return dst
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    a = s[..., 3:4]
    d = dst[y0:y1, x0:x1]
    c = s[..., :3] if mode == 'normal' else d * s[..., :3]
    dst[y0:y1, x0:x1] = d * (1 - a) + c * a
    return dst


def _demo_torn(paper):
    """rectangle + circle torn with deckle + shadow + cut edge on the paper (h, w, 3)."""
    H, W = paper.shape[:2]
    img = np.asarray(Image.open(P('assets', 'mat', 'velvet_terracotta.png')).convert('RGB'),
                     np.float32)[:H, :W] / 255.0 if os.path.exists(P('assets', 'mat', 'velvet_terracotta.png')) \
        else np.full((H, W, 3), hexf('terracotta'), np.float32)
    img2 = np.asarray(Image.open(P('assets', 'mat', 'glassblock.png')).convert('RGB'),
                      np.float32) / 255.0 if os.path.exists(P('assets', 'mat', 'glassblock.png')) \
        else np.full((H, W, 3), hexf('glass'), np.float32)
    img2 = rescale(img2, 0.5)
    m1 = np.zeros((H, W), np.float32)
    m1[int(H * 0.16):int(H * 0.80), int(W * 0.08):int(W * 0.46)] = 1
    m2 = np.zeros((H, W), np.uint8)
    cv2.circle(m2, (int(W * 0.72), int(H * 0.48)), int(H * 0.30), 1, -1)
    t1 = torn_mask(m1, seed=3)
    t2 = torn_mask(m2.astype(np.float32), seed=4)
    comp = paper.copy()
    for t, im, sd in ((t1, img, 3), (t2, tile(img2, H, W), 4)):
        sh, ox, oy = drop_shadow(t, 12, 16, 18, 0.45)
        _over(comp, sh, ox, oy, mode='multiply')
        _over(comp, np.dstack([im[:H, :W], t]))
        _over(comp, deckle_rgba(t, seed=sd))
        _over(comp, paper_cut_edge(t))
    return comp


def _demo_washes(paper):
    H, W = paper.shape[:2]
    comp = paper.copy()
    cols = ['terracotta', 'honey', 'sage', 'dusk']
    cw = W // 2
    ch = H // 2
    for i, c in enumerate(cols):
        x0, y0 = (i % 2) * cw, (i // 2) * ch
        m = np.zeros((H, W), np.uint8)
        cv2.ellipse(m, (x0 + cw // 2, y0 + ch // 2), (int(cw * 0.40), int(ch * 0.36)), 8 * i - 10, 0, 360, 1, -1)
        wsh = watercolour_wash(m.astype(np.float32), c, seed=10 + i, blooms=2)
        _over(comp, wsh, mode='multiply')
    return comp, cols


def contact_sheet(sw, extra, path=CONTACT):
    """Labelled contact sheet: every swatch (single + 2x2 tile), generator demos, A3 instances,
    client drape versions."""
    T = 520                    # swatch thumb size
    G = 36                     # gutter
    LBL = 70
    cols = 5
    Wd = cols * (2 * T + 12) + (cols + 1) * G
    rows_sw = int(np.ceil(len(sw) / cols))
    demo_h = 1000
    Ht = 140 + rows_sw * (T + LBL + G) + 2 * (demo_h + LBL + G) + G
    sheet = Image.new('RGB', (Wd, Ht), (239, 230, 214))
    dr = ImageDraw.Draw(sheet)
    fT, fL, fS = _font(56, 'serif'), _font(26, 'mono'), _font(19, 'monol')
    ink = (43, 36, 32)
    dr.text((G, 34), 'materials — swatches & generators', font=fT, fill=ink)
    dr.text((Wd - G - 900, 60), 'ASSETS/MAT · 1600 PX SEAMLESS TILES · LEFT: TILE  RIGHT: 2 x 2 REPEAT',
            font=fS, fill=ink)
    y = 140
    for i, (name, tex) in enumerate(sw.items()):
        c, r = i % cols, i // cols
        x = G + c * (2 * T + 12 + G)
        yy = y + r * (T + LBL + G)
        one = to_u8(_flat(rescale(tex, T / tex.shape[0]), '#FFFFFF' if name != 'greenery' else '#3D4A6B'))
        rep = tile(tex, 2 * SW, 2 * SW, offset=(SW // 2, SW // 2))
        two = to_u8(_flat(rescale(rep, T / rep.shape[0]), '#3D4A6B'))
        sheet.paste(Image.fromarray(one), (x, yy + LBL))
        sheet.paste(Image.fromarray(two), (x + T + 12, yy + LBL))
        dr.text((x, yy + 8), name.upper(), font=fL, fill=ink)
        dr.text((x, yy + 42), 'seams at the centre of the right-hand 2x2 view', font=fS, fill=(110, 100, 90))
    y += rows_sw * (T + LBL + G)
    # demo row 1: torn shapes | 4 washes | grain | paper
    def put(img, x, yy, label, sub='', w=None, h=None, bg='#EFE6D6'):
        im = _flat(img, bg)
        if w is not None:
            im = rescale(im, min(w / im.shape[1], h / im.shape[0]))
        sheet.paste(Image.fromarray(to_u8(im)), (x, yy + LBL))
        dr.text((x, yy + 8), label.upper(), font=fL, fill=ink)
        if sub:
            dr.text((x, yy + 42), sub, font=fS, fill=(110, 100, 90))
        return im.shape[1]
    x = G
    x += put(extra['torn'], x, y, 'torn_mask + deckle_rgba + drop_shadow + paper_cut_edge',
             'rectangle and circle on paper_linen; 100% scale', ) + G
    x += put(extra['washes'], x, y, 'watercolour_wash x4 (multiply)', ' · '.join(extra['wash_cols'])) + G
    x += put(extra['grain_crop'], x, y, 'grain (100%)', 'mid-grey, overlay / soft light') + G
    put(extra['paper_crop'], x, y, 'paper_linen (100%)', 'A3 instance: paper_linen_A3.png')
    y += demo_h + LBL + G
    x = G
    x += put(extra['paper_a3'], x, y, 'paper_linen_A3 (whole, contrast x4)', '4961 x 3508', w=1400, h=demo_h) + G
    x += put(extra['halftone'], x, y, 'halftone + grade', 'cell 14 px · gradient map honey > ember > wine',
             w=900, h=demo_h) + G
    x += put(extra['drape_soft'], x, y, 'client_drape_soft (6x)', 'source 368 x 461', w=800, h=demo_h) + G
    put(extra['drape_sheer'], x, y, 'client_drape_sheer', 'RGBA veil over dusk', w=800, h=demo_h, bg='#3D4A6B')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sheet.save(path, quality=90)
    return path


def build(only=None, resume=False):
    """Regenerate every asset in assets/mat/, index.json and build/contact/materials.jpg.
    only: optional list of swatch names to rebuild; resume=True skips existing PNGs."""
    os.makedirs(MAT, exist_ok=True)
    entries = []
    sw = {}
    t0 = time.time()
    for name, fn, desc, anchors, use in SWATCHES:
        path = os.path.join(MAT, name + '.png')
        if (only and name not in only) or (resume and os.path.exists(path)):
            tex = np.asarray(Image.open(path).convert('RGBA'), np.float32) / 255.0
            if name != 'greenery':
                tex = tex[..., :3]
        else:
            tex = fn()
            save_png(path, tex)
            print(f'  {name:18s} {time.time() - t0:6.1f}s  seam {seam_score(tex)}', flush=True)
        sw[name] = tex
        an = dict(anchors)
        if 'mean_alpha' in an:
            an['mean_alpha'] = round(float(tex[..., 3].mean()), 3)
        entries.append({'path': _rel(path), 'size': [SW, SW], 'type': 'RGBA' if name == 'greenery' else 'RGBA (opaque)',
                        'description': desc, 'anchors': an, 'tileable': True, 'suggested_use': use})
        gc.collect()
    # A3 instances
    pth = os.path.join(MAT, 'paper_linen_A3.png')
    if not (resume and os.path.exists(pth)):
        paper = paper_linen(A3[0], A3[1], seed=1)
        save_png(pth, paper)
    else:
        paper = np.asarray(Image.open(pth).convert('RGB'), np.float32) / 255.0
    entries.append({'path': _rel(pth), 'size': [A3[1], A3[0]], 'type': 'RGBA (opaque)',
                    'description': 'Warm linen paper ground #EEE5D3: smooth large mottling, faint felt tooth, '
                                   'sparse fine fibres; low-entropy (no per-pixel noise). paper_linen(3508, 4961, seed=1).',
                    'anchors': {'canvas': 'full A3 @ 300 ppi, place at (0, 0)'}, 'tileable': False,
                    'suggested_use': 'Bottom paper layer of both collages.'})
    pgr = os.path.join(MAT, 'grain_A3.png')
    g = grain(A3[0], A3[1], seed=2, amount=0.05)
    save_png(pgr, np.dstack([g, g, g]))
    entries.append({'path': _rel(pgr), 'size': [A3[1], A3[0]], 'type': 'RGBA (opaque, neutral grey)',
                    'description': 'Neutral film grain, mean 0.5 (128), std 0.05; fine 0.6 px + clumped 1.4 px grain. '
                                   'grain(3508, 4961, seed=2, amount=0.05).',
                    'anchors': {'canvas': 'full A3, place at (0, 0)', 'neutral_value': 128},
                    'tileable': True, 'suggested_use': 'Top layer, blend overlay or soft light at 30-60 %.'})
    # client drape
    soft, sheer = make_drape()
    ps, pe = os.path.join(MAT, 'client_drape_soft.png'), os.path.join(MAT, 'client_drape_sheer.png')
    save_png(ps, soft)
    save_png(pe, sheer)
    dh, dw = soft.shape[:2]
    entries.append({'path': _rel(ps), 'size': [dw, dh], 'type': 'RGBA (opaque)',
                    'description': 'Client mood reference (client_drape_reference.png, 380x470, white border cropped '
                                   'to 368x461) upscaled 6x: NL-means denoise, 2-stage Lanczos, bilateral de-ringing, '
                                   'gentle unsharp, imperceptible grain. LOW SOURCE RES: it stays soft - use as a '
                                   'soft/overlay/background element only, never as a sharp foreground.',
                    'anchors': {'source_crop_box_xyxy': list(DRAPE_BOX), 'scale': DRAPE_SCALE,
                                'swag_ceiling_band_y': [0, int(0.53 * dh)], 'sheer_curtains_y': [int(0.45 * dh), dh]},
                    'tileable': False, 'suggested_use': 'Soft-light / low-opacity ceiling-drape atmosphere.'})
    entries.append({'path': _rel(pe), 'size': [dw, dh], 'type': 'RGBA (straight alpha)',
                    'description': 'Sheer veil from the client drape: lightened, mostly desaturated toward linen, alpha '
                                   'from luminance (0.10..0.82: bright fabric opaque, shadowed folds transparent).',
                    'anchors': {'alpha_range': [0.10, 0.82]}, 'tileable': False,
                    'suggested_use': 'Translucent sheer-linen overlay (normal or screen) over diners / windows.'})
    # demos for the contact sheet
    dp = paper_linen(1000, 1500, seed=5)
    torn = _demo_torn(dp)
    wp = paper_linen(1000, 1300, seed=6)
    washes, wash_cols = _demo_washes(wp)
    gr = g[1000:1500, 1000:1500]
    pc = paper[1000:1500, 1000:1500]
    pa3 = rescale(paper, 0.3)
    Lp = lum(pa3)
    pa3 = np.clip(pa3 * (1 + 4 * (Lp / Lp.mean() - 1))[..., None], 0, 1)       # luminance x4
    src = np.asarray(Image.open(P('assets', 'client_drape_reference.png')).convert('L'), np.float32)[9:, :368] / 255.
    src = rescale(src[..., None].repeat(3, 2), 2.4)[..., 0]
    ht = halftone(src, 14)
    htg = grade(np.dstack([1 - ht] * 3), ['#4A1A26', '#C2602E', '#E8B062', '#EFE6D6'])
    extra = {'torn': torn, 'washes': washes, 'wash_cols': wash_cols, 'grain_crop': gr, 'paper_crop': pc,
             'paper_a3': pa3, 'halftone': htg, 'drape_soft': soft, 'drape_sheer': sheer}
    del paper
    gc.collect()
    funcs = {
        'paper_linen(h, w, seed, color, mottle, fibre)': 'warm linen paper RGB, low-entropy, tileable',
        'grain(h, w, seed, amount)': 'neutral mid-grey film grain (h, w) for overlay / soft light',
        'torn_mask(mask, seed, roughness, scale)': 'torn-paper edge for any mask -> float mask',
        'deckle_rgba(mask, seed, width, color, fibres)': 'white fibrous torn-edge strip RGBA layer',
        'drop_shadow(alpha, dx, dy, blur, opacity, color, contact) -> (rgba, ox, oy)': 'soft paper shadow layer',
        'watercolour_wash(mask, color, seed, opacity, edge, granulation, blooms, wobble)': 'pigment wash RGBA',
        'halftone(gray, cell, angle, gain)': 'AM halftone ink coverage 0..1',
        'grade(rgb, stops, amount, normalize)': 'gradient-map grading toward palette stops',
        'tile(tex, h, w, offset, scale)': 'repeat a tileable texture',
        'paper_cut_edge(mask, light, width, strength, rim)': 'bevel / lit cut edge RGBA for card planes',
        'upscale_soft(img, s)': 'denoise + Lanczos + de-ring + gentle sharpen upscale',
        'quilt(sources, size, patch, overlap, ...)': 'toroidal image quilting (seamless synthesis)',
        'flatten_light(img, sigma, mask, per_channel, strength)': 'remove low-frequency lighting',
        'periodic_noise / fbm / warp_periodic': 'seamless noise fields',
        'key_foliage(im)': 'key leaves off bright sky with fringe removal + edge decontamination',
    }
    idx = {'area': 'materials', 'module': 'src/lib/materials.py', 'build': 'python3 -c "from lib import materials; materials.build()"  (run from src/)',
           'contact_sheet': _rel(CONTACT), 'conventions': 'RGBA 8-bit straight alpha; swatches flat-lit and '
           'seamlessly tileable (period = image size); palette per ART_DIRECTION.md',
           'files': entries, 'functions': funcs}
    with open(os.path.join(MAT, 'index.json'), 'w') as f:
        json.dump(idx, f, indent=2)
    contact_sheet(sw, extra)
    print(f'build done {time.time() - t0:.1f}s', flush=True)
    return idx


if __name__ == '__main__':
    build()
