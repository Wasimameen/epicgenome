"""collage02_prep — derived plates for collage 02 (cached in build/c02/, rebuilt on demand).

  cabins_plate()    cabins_row.png with the defocused foreground chairs/tables removed from the
                    cabin bases (cloned from the neighbouring cabin at the same place on its
                    cylinder, Telea inpaint for the rest), plus the cut mask: the four fluted shells
                    cut FLAT at 2.4 m (elevation 02: open-topped partitions under the draped
                    ceiling) and the four pendant shades kept as islands.
  valance_frieze()  a seamless festoon frieze from whole swags of festoon_valance.png: joins sit in
                    the gathered columns, the two pendant cords are retouched out, the side tails
                    and the jabot are never used, alternate swags are mirrored so no swag repeats
                    next to itself, every swag is gain-matched.
"""
from __future__ import annotations

import json
import os

import cv2
import numpy as np
from PIL import Image

from lib import compose as C

CACHE = C.P('build', 'c02')
PEDESTAL_X = (1180, 2474, 3851, 5168)   # table base disc centre = pendant axis in each opening (source px)
YCUT = 1322.0          # source row of the 2.4 m partition top (elevation 02 registered on the jambs)


def _save(path, arr, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    a = np.clip(arr * 255 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(a, mode).save(path)


def _arc(sh, x, key):
    a = sh[key]
    u = np.clip((x - a['xc']) / a['hw'], -1, 1)
    return a['c0'] + a['k'] * np.sqrt(1 - u * u)


# --------------------------------------------------------------------------- cabins
def _bilinear(img, x, y):
    h, w = img.shape[:2]
    x = np.clip(x, 0, w - 1.001)
    y = np.clip(y, 0, h - 1.001)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def _clean_cabins(img, geo):
    """Replace the defocused foreground (chairs, glasses, table tops) in front of the cabin bases.

    Fluted flanks: the flutes are vertical, so each occluded column is mirrored from just above the
    occluder.  Stainless kick plate: continued sideways from the nearest clean columns along the
    floor arc.  Openings (dark floor, table bases): cloned from the same place in a neighbouring
    cabin (matched on the cylinder), Telea inpaint for the rest, tone-matched to the surround."""
    fb = C.load('assets/cut/geo/cabins_row/foreground_band.png', 'L') > 0.5
    fbd = cv2.dilate(fb.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (51, 51))) > 0
    shells = geo['shells']
    amodal = [C.load(f'assets/cut/geo/cabins_row/shell_{s["id"]}_geo.png', 'L') > 0.5 for s in shells]
    opening = [cv2.dilate((C.load(f'assets/cut/geo/cabins_row/arch_{s["id"]}.png', 'L') > 0.5).astype(np.uint8),
                          np.ones((5, 5), np.uint8)) > 0 for s in shells]
    out = img.copy()
    todo = np.zeros(fb.shape, bool)
    clone = np.zeros(fb.shape, bool)
    Hs, Ws = fb.shape
    KICK = 74
    for n, sh in enumerate(shells):
        T = amodal[n] & fbd
        T[:int(YCUT)] = False
        if not T.any():
            continue
        ar = geo['arches'][n]
        xx = np.arange(Ws)
        in_x = (xx >= ar['left_x'] - 2) & (xx <= ar['right_x'] + 2)
        T_in = T & (opening[n] | in_x[None, :])
        T_fl = T & ~T_in
        # ---- fluted flanks + kick plate
        cols = np.nonzero(T_fl.any(0))[0]
        flank = amodal[n] & ~opening[n]
        yb_all = _arc(sh, np.arange(Ws, dtype=np.float64), 'bottom_arc')
        kick_occ = np.zeros(Ws, bool)
        for x in cols:
            ys = np.nonzero(T_fl[:, x])[0]
            if ys.max() >= yb_all[x] - KICK - 2:
                kick_occ[x] = True
        clean_all = np.nonzero(flank[int(min(Hs - 1, yb_all.mean() - 30))] & ~kick_occ)[0]
        for x in cols:
            side = clean_all < ar['left_x'] if x < ar['left_x'] else clean_all > ar['right_x']
            clean_kick = clean_all[side]
            ys = np.nonzero(T_fl[:, x])[0]
            yk = yb_all[x] - KICK
            y0 = ys.min()
            fl = ys[ys < yk]
            if len(fl):
                ysrc = np.clip(2 * y0 - fl - 6, int(YCUT), Hs - 1)
                out[fl, x] = img[ysrc, x]
            kz = ys[ys >= yk]
            if len(kz):
                if not len(clean_kick):
                    todo[kz, x] = True
                    continue
                left = clean_kick[clean_kick < x]
                right = clean_kick[clean_kick > x]
                srcs = []
                if len(left):
                    srcs.append((left.max(), x - left.max()))
                if len(right):
                    srcs.append((right.min(), right.min() - x))
                acc = np.zeros((len(kz), 3), np.float32)
                wsum = 0.0
                for xs_, d in srcs:
                    w = 1.0 / max(d, 1)
                    yy = np.clip(kz + (yb_all[xs_] - yb_all[x]), 0, Hs - 1).astype(np.float64)
                    acc += w * _bilinear(img, np.full(len(kz), float(xs_)), yy)
                    wsum += w
                out[kz, x] = acc / wsum
        # ---- openings: mirror about the table pedestal (the booth floor + table base are symmetric)
        if T_in.any():
            xp = PEDESTAL_X[n]
            ar = geo['arches'][n]
            ys, xs = np.nonzero(T_in)
            xm = 2 * xp - xs
            ok = (xm > ar['left_x'] + 48) & (xm < ar['right_x'] - 48)      # never mirror the jamb reveals
            ok[ok] &= ~fbd[ys[ok], xm[ok]]
            out[ys[ok], xs[ok]] = img[ys[ok], xm[ok]]
            todo[ys[~ok], xs[~ok]] = True
            clone |= T_in
    # second pass: what neither side of a booth could supply is cloned (not mirrored) from the same
    # place in a neighbouring booth that is already clean, aligned on the table axis and the floor arc
    for n, sh in enumerate(shells):
        ar = geo['arches'][n]
        box = np.zeros(fb.shape, bool)
        box[:, int(ar['left_x']):int(ar['right_x']) + 1] = True
        ys, xs = np.nonzero(todo & box)
        if not len(xs):
            continue
        rem = np.ones(len(xs), bool)
        for m in sorted([i for i in range(len(shells)) if i != n], key=lambda i: abs(i - n)):
            am_ = geo['arches'][m]
            xd = xs - PEDESTAL_X[n] + PEDESTAL_X[m]
            yd = ys + (_arc(shells[m], xd, 'bottom_arc') - _arc(sh, xs, 'bottom_arc'))
            xi, yi = np.round(xd).astype(int), np.clip(np.round(yd).astype(int), 0, Hs - 1)
            ok = rem & (xi > am_['left_x'] + 48) & (xi < am_['right_x'] - 48)
            ok[ok] &= ~todo[yi[ok], xi[ok]]
            if not ok.any():
                continue
            out[ys[ok], xs[ok]] = _bilinear(out, xd[ok], yd[ok])
            todo[ys[ok], xs[ok]] = False
            rem &= ~ok
    if todo.any():
        # everything under the foreground that is NOT cabin is unknown too, so Telea only
        # propagates from the cabin itself (never from the lit dining tables below the floor line)
        unknown = todo | (fbd & ~np.any(amodal, axis=0))
        u8 = np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8)
        u8 = cv2.inpaint(u8, unknown.astype(np.uint8) * 255, 9, cv2.INPAINT_TELEA)
        out = u8.astype(np.float32) / 255
    # the defocused chairs also cast a soft penumbra well beyond their mask: rebuild the whole
    # occluded side of each booth floor (below the banquette) as a mirror of its clean side
    for n, sh in enumerate(shells):
        ar = geo['arches'][n]
        xp = PEDESTAL_X[n]
        occ = fbd & amodal[n]
        occ[:2250] = False
        oc = np.nonzero(occ[:, int(ar['left_x']):int(ar['right_x'])].any(0))[0]
        if not len(oc):
            continue
        side = 1 if (oc.mean() + ar['left_x']) > xp else -1          # +1: right side occluded
        y0z = 2195
        xs = np.arange(int(ar['left_x']) + 48, int(ar['right_x']) - 47)
        xs = xs[(xs - xp) * side > 0]
        xm = (2 * xp - xs).astype(int)
        keep = (xm > ar['left_x'] + 48) & (xm < ar['right_x'] - 48)
        xs, xm = xs[keep], xm[keep]
        yb = _arc(sh, xs.astype(np.float64), 'bottom_arc')
        for k, (x, xmi) in enumerate(zip(xs, xm)):
            y1 = int(yb[k]) + 4
            ys = np.arange(y0z, y1)
            wv = np.clip((ys - y0z) / 30.0, 0, 1) * min(1.0, abs(x - xp) / 10.0)
            out[ys, x] = out[ys, xmi] * wv[:, None] + out[ys, x] * (1 - wv[:, None])
        clone[y0z:, xs.min():xs.max() + 1] |= amodal[n][y0z:, xs.min():xs.max() + 1]

    # tone-match each cloned opening patch to its untouched surroundings
    anyam = np.any(amodal, axis=0)
    nlab, lab = cv2.connectedComponents(clone.astype(np.uint8))
    for i in range(1, nlab):
        comp = lab == i
        ring = cv2.dilate(comp.astype(np.uint8), np.ones((41, 41), np.uint8)) > 0
        band = ring & ~fbd & anyam & ~(cv2.dilate(comp.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
        edge = comp & ~cv2.erode(comp.astype(np.uint8), np.ones((21, 21), np.uint8)).astype(bool)
        if band.sum() < 200 or edge.sum() < 200:
            continue
        g = np.clip((img[band].mean(0) + 1e-3) / (out[edge].mean(0) + 1e-3), 0.7, 1.4)
        out[comp] = np.clip(out[comp] * g, 0, 1)
    rep = clone.copy()
    for n in range(len(shells)):
        T = amodal[n] & fbd
        T[:int(YCUT)] = False
        rep |= T
    core = cv2.erode(rep.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
    a = np.maximum.reduce([fb.astype(np.float32), core, C.blur(rep.astype(np.float32), 3.0)])
    return img * (1 - a[..., None]) + out * a[..., None]


def _pendant_islands(img, geo):
    """Clean masks of the four dome shades: an analytic half-ellipse dome on the cord axis (no
    threshold edges, so dark flute grooves behind cannot leak in), the cap, and the lit inner rim."""
    L = C.lum(img)
    m = np.zeros(L.shape, np.float32)
    shades = []
    for a in geo['arches']:
        cx = int(a['centre_x'])
        x0, y0, x1, y1 = cx - 270, 1060, cx + 270, 1250
        sub = L[y0:y1, x0:x1]
        hh, ww = sub.shape
        hard = (sub < 0.05).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(hard)
        i = 1 + int(np.argmax(st[1:, 4]))
        comp = lab == i
        widths = comp.sum(1)
        rows = np.nonzero(widths)[0]
        dome_top = int(rows[np.argmax(widths[rows] > 40)])          # first row wider than the cap
        cap_rows = rows[rows < dome_top]
        axis = float(np.median(np.nonzero(comp[cap_rows[-12:]])[1])) if len(cap_rows) else ww / 2
        yb = int(rows.max())                                        # last dark row = dome bottom
        # half-width at the bottom: the smaller side (a groove behind can only inflate one side)
        cols = np.nonzero(comp[yb - 4:yb + 1].any(0))[0]
        hw = min(axis - cols.min(), cols.max() - axis) + 0.5
        yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32) + 0.5
        ry = yb + 1 - dome_top
        # supersampled analytic half ellipse
        ss = 4
        oy, ox = np.mgrid[0:ss, 0:ss].astype(np.float32)
        dome = np.zeros((hh, ww), np.float32)
        for dy_, dx_ in zip(((oy + 0.5) / ss - 0.5).ravel(), ((ox + 0.5) / ss - 0.5).ravel()):
            X, Y = xx + dx_, yy + dy_
            inside = (((X - axis) / hw) ** 2 + ((Y - (yb + 1)) / ry) ** 2 <= 1) & (Y <= yb + 1)
            dome += inside
        dome /= ss * ss
        rim = C.ellipse_mask(axis, yb + 2.0, hw, 6.5, h=hh, w=ww)
        rim[: yb - 2] = 0
        cap = C.rect_mask(axis - 6, dome_top - 22, axis + 6, dome_top + 3, h=hh, w=ww)
        isl = np.clip(np.maximum.reduce([dome, rim, cap]), 0, 1)
        m[y0:y1, x0:x1] = np.maximum(m[y0:y1, x0:x1], isl)
        shades.append({'cap_top': [float(x0 + axis), float(y0 + dome_top - 22)],
                       'rim': [float(x0 + axis), float(y0 + yb + 2)], 'half_width': float(hw)})
    return m, shades


def cabins_plate(force=False):
    """-> (rgb, cut_mask, pendant_mask, shades, geo) at SOURCE resolution (6256 x 2688)."""
    geo = json.load(open(C.P('assets', 'cut', 'geo', 'cabins_row', 'geometry.json')))
    p_rgb = os.path.join(CACHE, 'cabins_row_clean.png')
    p_msk = os.path.join(CACHE, 'cabins_row_cut.png')
    p_js = os.path.join(CACHE, 'cabins_row_cut.json')
    p_pen = os.path.join(CACHE, 'cabins_row_pendants.png')
    if not force and all(os.path.exists(p) for p in (p_rgb, p_msk, p_js, p_pen)):
        return (C.load(p_rgb, 'RGB'), C.load(p_msk, 'L'), C.load(p_pen, 'L'), json.load(open(p_js))['shades'], geo)
    img = C.load('assets/gen/cabins_row.png', 'RGB')
    rgb = _clean_cabins(img, geo)
    Hs, Ws = img.shape[:2]
    yy, xx = np.mgrid[0:Hs, 0:Ws].astype(np.float32)
    cut = np.zeros((Hs, Ws), np.float32)
    for s in geo['shells']:
        amod = C.load(f'assets/cut/geo/cabins_row/shell_{s["id"]}_geo.png', 'L')
        amod = cv2.dilate(amod, np.ones((1, 31), np.uint8))       # neighbouring shells meet (no paper slivers)
        # flat 2.4 m top: at eye level the cylinder top reads as a straight edge (+4 px sag at the front)
        u = np.clip((xx[0] - s['top_arc']['xc']) / s['top_arc']['hw'], -1, 1)
        ytop = YCUT + 4.0 * np.sqrt(1 - u * u)
        topm = np.clip(yy - ytop[None, :] + 0.5, 0, 1)
        cut = np.maximum(cut, amod * topm)
    pend, shades = _pendant_islands(img, geo)
    _save(p_rgb, rgb)
    _save(p_msk, cut, 'L')
    _save(p_pen, pend, 'L')
    json.dump({'ycut': YCUT, 'shades': shades}, open(p_js, 'w'), indent=1)
    return rgb, cut, pend, shades, geo


# --------------------------------------------------------------------------- valance
UNITS = {'A': (993.5, 1669.5), 'B': (1669.5, 2332.5), 'C': (2332.5, 3001.5), 'D': (4764.5, 5404.5),
         'E': (3001.5, 3687.0), 'F': (5404.5, 5989.5)}
MIRROR_CLONES = ((3600, 3705, 3344.0), (5850, 6010, 5697.0))   # (x0, x1, swag centre): E's jabot, F's tail
CORDS = ((1582.5, 1571.0), (4754.0, 4761.0))   # pendant cord x at source rows 300 and 1050
V_Y0, V_Y1 = 262, 1130          # source rows kept (heading top 280 .. lowest hem ~1118)


def _valance_source():
    fv = C.load('assets/gen/festoon_valance.png', 'RGB')[V_Y0:V_Y1].copy()
    fm = C.load('assets/cut/geo/festoon_valance/valance_fabric.png', 'L')[V_Y0:V_Y1].copy()
    # retouch the two pendant cords that cross the valance: mirror-clone the same swag across its
    # own centre (swag halves are near-symmetric), feathered over 6 px - no smeared inpaint streaks
    src = fv.copy()
    for (xa, xb), uc in zip(CORDS, (1331.5, 5084.5)):
        for r in range(fv.shape[0]):
            cx = xa + (xb - xa) * ((r + V_Y0) - 300) / 750.0
            xs = np.arange(int(round(cx - 16)), int(round(cx + 17)))
            w = np.clip((14.5 - np.abs(xs - cx)) / 6.0, 0, 1)[:, None]
            xm = np.clip(np.round(2 * uc - xs).astype(int), 0, fv.shape[1] - 1)
            fv[r, xs] = src[r, xm] * w + src[r, xs] * (1 - w)
    # close the cord slits in the fabric mask, soften the edge by ~1 px
    fm = cv2.morphologyEx(fm, cv2.MORPH_CLOSE, np.ones((1, 23), np.uint8))
    # the mask's cusps hide little triangles of plaster wall between the gathered column and the
    # swag above each cusp tip: remove smooth, wall-coloured pixels there
    Lm = C.lum(fv)
    mu = cv2.blur(Lm, (7, 7))
    sd = np.sqrt(np.maximum(cv2.blur(Lm * Lm, (7, 7)) - mu * mu, 0))
    for g in (993.5, 1669.5, 2332.5, 3001.5, 4764.5, 5404.5):
        gx = int(round(g))
        col = fm[:, gx - 3:gx + 4].mean(1)
        rows = np.nonzero(col > 0.5)[0]
        t = rows.max()
        ref = np.median(fv[t + 12:t + 60, gx - 15:gx + 16].reshape(-1, 3), axis=0)
        ya, yb, xa, xb = max(0, t - 110), t + 6, gx - 50, gx + 51
        dist = np.abs(fv[ya:yb, xa:xb] - ref).max(-1)
        wall = ((dist < 0.07) & (sd[ya:yb, xa:xb] < 0.025)).astype(np.uint8)
        wall = cv2.morphologyEx(wall, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        wall = C.blur(cv2.dilate(wall, np.ones((3, 3), np.uint8)).astype(np.float32), 1.0)
        fm[ya:yb, xa:xb] *= 1 - wall
    fm = C.blur(cv2.erode(fm, np.ones((3, 3), np.uint8)), 1.2)
    # two more whole swags (E, F): the swag beside the jabot and the swag beside the right side tail
    # are completed by mirror-cloning their clean half across the swag centre (RGB AND fabric mask,
    # full height, 12 px linear feather), which removes the jabot, its ring hook and the tail cascade
    src, srm = fv.copy(), fm.copy()
    for x0, x1, c in MIRROR_CLONES:
        xs = np.arange(x0 - 12, x1 + 1)
        w = np.clip((xs - (x0 - 12)) / 12.0, 0, 1)
        xm = np.round(2 * c - xs).astype(int)
        fv[:, xs] = src[:, xm] * w[None, :, None] + src[:, xs] * (1 - w[None, :, None])
        fm[:, xs] = srm[:, xm] * w[None, :] + srm[:, xs] * (1 - w[None, :])
    return fv, fm


# every source swag at most once among the visible slots 2-15, straight / mirrored copies >= 6 apart
# (only C and E return, at slots 14 / 15: slot 2 is half behind the glass-brick screen, slot 15 is
# ~130 px of the right bleed)
FRIEZE_ORDER = 'ABCEaFdBceAfDbCE'


def valance_frieze(width_src, order=FRIEZE_ORDER, ov=14, force=False, seed=11):
    """Frieze at source scale: -> (rgb, mask, gathers_x).  Upper-case = as photographed,
    lower-case = mirrored.  Joins cross-fade over 2*ov px inside a gathered column."""
    key = f'{order}_{int(width_src)}_{ov}_v{seed}'
    p_rgb = os.path.join(CACHE, f'valance_{key}.png')
    p_msk = os.path.join(CACHE, f'valance_{key}_mask.png')
    p_js = os.path.join(CACHE, f'valance_{key}.json')
    if not force and all(os.path.exists(p) for p in (p_rgb, p_msk, p_js)):
        return C.load(p_rgb, 'RGB'), C.load(p_msk, 'L'), json.load(open(p_js))['gathers']
    fv, fm = _valance_source()
    rng = np.random.default_rng(seed)
    lum = C.lum(fv)
    ref = float((lum * fm).sum() / fm.sum())
    pieces = []
    for ch in order:
        x0, x1 = UNITS[ch.upper()]
        a, b = int(round(x0)) - ov, int(round(x1)) + ov
        rgb, msk = fv[:, a:b].copy(), fm[:, a:b].copy()
        g = ref / float((C.lum(rgb) * msk).sum() / msk.sum())
        rgb = np.clip(rgb * g, 0, 1)
        if ch.islower():
            rgb, msk = rgb[:, ::-1], msk[:, ::-1]
        # every swag a little different: +-4 % width, +-5 % drop (heading stays on the top row)
        sx, sy = 1 + rng.uniform(-0.04, 0.04), 1 + rng.uniform(-0.05, 0.05)
        size = (int(round(rgb.shape[1] * sx)), int(round(rgb.shape[0] * sy)))
        rgb = np.clip(cv2.resize(rgb, size, interpolation=cv2.INTER_LANCZOS4), 0, 1)[:fv.shape[0]]
        msk = np.clip(cv2.resize(msk, size, interpolation=cv2.INTER_LANCZOS4), 0, 1)[:fv.shape[0]]
        if rgb.shape[0] < fv.shape[0]:
            padn = fv.shape[0] - rgb.shape[0]
            rgb = np.pad(rgb, ((0, padn), (0, 0), (0, 0)), mode='edge')
            msk = np.pad(msk, ((0, padn), (0, 0)))
        pieces.append((rgb, msk))
    h = fv.shape[0]
    total = sum(p[0].shape[1] - 2 * ov for p in pieces) + 2 * ov
    out = np.zeros((h, total, 3), np.float32)
    om = np.zeros((h, total), np.float32)
    wsum = np.zeros((1, total, 1), np.float32)
    x = 0
    gathers = []
    for rgb, msk in pieces:
        w = rgb.shape[1]
        ramp = np.ones(w, np.float32)
        r = np.linspace(0, 1, 2 * ov + 2, dtype=np.float32)[1:-1]
        ramp[:2 * ov] = r
        ramp[-2 * ov:] = r[::-1]
        out[:, x:x + w] += rgb * ramp[None, :, None]
        om[:, x:x + w] += msk * ramp[None, :]
        wsum[:, x:x + w, 0] += ramp
        gathers.append(x + ov)
        x += w - 2 * ov
    gathers.append(x + ov)
    wsum = np.maximum(wsum, 1e-4)
    out /= wsum
    om /= wsum[..., 0]
    # trim the unblended outer ramps
    out, om = out[:, ov:-ov], om[:, ov:-ov]
    gathers = [g - ov for g in gathers]
    if out.shape[1] < width_src:
        raise ValueError(f'frieze {out.shape[1]} px < {width_src}: add units')
    _save(p_rgb, out)
    _save(p_msk, om, 'L')
    json.dump({'gathers': gathers, 'order': order}, open(p_js, 'w'))
    return out, om, gathers


if __name__ == '__main__':
    import time
    t = time.time()
    rgb, cut, pend, shades, geo = cabins_plate(force=True)
    print('cabins', time.time() - t, shades)
    fr, fm, gx = valance_frieze(10200, force=True)
    print('valance', fr.shape, gx, time.time() - t)
    sp = C.P('build', 'c02')
    C.save_preview(np.dstack([rgb, np.maximum(cut, pend)]), os.path.join(sp, 'cabins_cut_preview.jpg'), 1800)
    C.save_preview(np.dstack([rgb, pend])[1050:1260], os.path.join(sp, 'pendants_preview.jpg'), 2400)
    C.save_preview(rgb[2050:2688, 300:6256], os.path.join(sp, 'cabins_clean_bottom.jpg'), 1985)
    C.save_preview(np.dstack([fr, fm]), os.path.join(sp, 'valance_preview.jpg'), 1800)
