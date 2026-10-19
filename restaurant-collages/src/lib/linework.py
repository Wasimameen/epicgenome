"""linework — the client's CAD drawings as crisp, transparent ink linework.

Source: ``assets/client_RESTAURANT_drawings.pdf`` (AutoCAD plot, 4 vector pages, 2384 x 1684 pt, A1).
The 300 dpi sheet renders in ``assets/drawings/sheet-N.png`` are used to *locate* each drawing
(long-line morphology finds the building frame, a tight ink bbox finds the full drawing).  Every
region is then re-rendered straight from the vector PDF at 600 dpi with poppler's ``pdftoppm``.

"Building only" variants are not just rectangular crops: the label leaders and their arrowheads
cut across the drawings, so the page content stream is parsed (paths + text, with CTM tracking)
and those annotation objects are neutralised in a temporary copy of the PDF (their paint operator
becomes ``n`` / their string becomes empty) before rendering.  The result is pixel-identical
linework with the annotations genuinely absent (no in-painting, no erased holes).

Grey levels become straight-alpha ink (``ink_rgba``): RGB = ink #2B2420, alpha = darkness ** gamma
through a 256-entry LUT, paper (255) is exactly alpha 0.

Public API
----------
render_region(page, x_pt, y_pt, w_pt, h_pt, dpi=600, pdf=None)  -> uint8 grey (H, W), straight from the PDF
ink_rgba(gray, color='#2B2420', gamma=0.72, floor=0.0)           -> uint8 RGBA (paper = alpha 0)
recolor(rgba, hex)                                               -> same dtype RGBA, new flat ink colour
thicken(rgba, px)                                                -> same dtype RGBA (soft disc dilation, fractional px)
hand_wobble(rgba, amount=1.5, seed=0, wavelength=None, fine=0.35, pressure=0.0)
                                                                 -> same dtype RGBA (smooth sketch jitter)
page_items(page)                    parse a page content stream -> [Item] (paths/text, page pt, layer, pen)
annotation_drops(page, box)         leaders / arrowheads / outside dims + labels for a building frame
write_pdf_variant(page, drops, out) PDF copy with those objects neutralised
locate_frame(sheet, window) / locate_ink(sheet, window)   find drawings on the 300 dpi sheets
render_view(name, clean=True)       one of VIEWS rendered at 600 dpi (cached in build/linework/cache)
measure_section_AA / measure_section_BB / measure_elev02 / measure_plan_ground / measure_plan_first
                                    registration anchors measured on the rendered pixels
thin helpers: long_lines, measure_slabs, slab_gaps, measure_trunk, hough_circles, refine_circle,
              best_circle, ring_radii, tree_canopy, shift_anchors, linen_paper
build(use_cache=True)               regenerates assets/lines/*.png, index.json, build/contact/linework.jpg

Coordinates: page points are measured from the TOP-LEFT of the page (y down), like the sheet
PNGs and pdftoppm's -x/-y.  600 dpi px = pt * 600 / 72.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PDF = os.path.join(ROOT, 'assets', 'client_RESTAURANT_drawings.pdf')
SHEETS = os.path.join(ROOT, 'assets', 'drawings', 'sheet-{}.png')
OUT = os.path.join(ROOT, 'assets', 'lines')
BUILD = os.path.join(ROOT, 'build', 'linework')
PREVIEW = os.path.join(ROOT, 'build', 'preview', 'linework')
CONTACT = os.path.join(ROOT, 'build', 'contact', 'linework.jpg')

PAGE_W, PAGE_H = 2384.0, 1684.0
SHEET_DPI = 300
DPI = 600
INK = '#2B2420'
LINEN = '#EEE5D3'


def _hex(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def pt2px(v, dpi=DPI):
    return v * dpi / 72.0


def px2pt(v, dpi=DPI):
    return v * 72.0 / dpi


# =========================================================================== #
# 1. PDF content-stream model
# =========================================================================== #

_TOK = re.compile(
    rb'(?P<ws>\s+)|(?P<cmt>%[^\r\n]*)'
    rb'|(?P<num>[-+]?(?:\d+\.?\d*|\.\d+))'
    rb'|(?P<name>/[^\s/\[\]()<>{}%]*)'
    rb'|(?P<dict><<|>>)'
    rb'|(?P<hex><[0-9A-Fa-f\s]*>)'
    rb'|(?P<str>\((?:\\.|[^\\()]|\((?:\\.|[^\\()])*\))*\))'
    rb'|(?P<arr>[\[\]])'
    rb'|(?P<op>[A-Za-z\'"][A-Za-z0-9*\'"]*)')

_PAINT = {b'S', b's', b'f', b'F', b'f*', b'B', b'B*', b'b', b'b*'}
_FILL = {b'f', b'F', b'f*', b'B', b'B*', b'b', b'b*'}


@dataclass
class Item:
    """One painted object of a page content stream."""
    kind: str                 # 'path' | 'text'
    idx: int                  # running index in the page
    span: tuple               # byte span to neutralise (paint operator / text string operand)
    op: bytes                 # paint operator (path) or show operator (text)
    layer: str                # CAD layer (optional-content group name)
    pts: np.ndarray           # (N, 2) vertices in page pt, top-left origin (text: bbox corners)
    lw: float = 0.0           # stroke width in pt
    stroke: float = 0.0       # stroke grey 0..1
    fill: float = 0.0         # fill grey 0..1
    curved: bool = False
    nsub: int = 1
    nglyph: int = 0
    bbox: tuple = field(default=None)

    def __post_init__(self):
        if self.bbox is None and len(self.pts):
            self.bbox = (float(self.pts[:, 0].min()), float(self.pts[:, 1].min()),
                         float(self.pts[:, 0].max()), float(self.pts[:, 1].max()))


_PAGE_CACHE: dict = {}


def _reader():
    logging.getLogger('pypdf').setLevel(logging.ERROR)
    from pypdf import PdfReader
    return PdfReader(PDF)


def page_items(page):
    """Parse page `page` (1-based) -> (content_bytes, [Item]).  Cached per process."""
    if page in _PAGE_CACHE:
        return _PAGE_CACHE[page]
    r = _reader()
    p = r.pages[page - 1]
    props = p['/Resources'].get('/Properties', {})
    lname = {k[1:].encode(): str(props[k].get_object().get('/Name', k)) for k in props}
    data = p.get_contents().get_data()

    items = []
    ctm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    gstack = []
    lw, sc, fc = 1.0, 0.0, 0.0
    layers = []
    subs, sub, curved = [], [], False
    tm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    fsize = 1.0
    operands = []
    last_operand_span = None

    def tr(x, y):
        a, b, c, d, e, f = ctm
        return a * x + c * y + e, PAGE_H - (b * x + d * y + f)

    def scale():
        a, b, c, d, _, _ = ctm
        return float(np.sqrt(abs(a * d - b * c)))

    depth = 0  # array nesting for TJ
    arr_start = None
    for m in _TOK.finditer(data):
        g = m.lastgroup
        if g in ('ws', 'cmt'):
            continue
        if g == 'num':
            if depth == 0:
                operands.append(float(m.group(g)))
            continue
        if g == 'arr':
            if m.group(g) == b'[':
                if depth == 0:
                    arr_start = m.start()
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    operands.append(b'[]')
                    last_operand_span = (arr_start, m.end())
            continue
        if g != 'op':
            if depth == 0:
                operands.append(m.group(g))
                last_operand_span = (m.start(), m.end())
            continue
        op = m.group('op')
        a = operands
        operands = []
        if op == b'q':
            gstack.append((ctm, lw, sc, fc))
        elif op == b'Q':
            if gstack:
                ctm, lw, sc, fc = gstack.pop()
        elif op == b'cm' and len(a) == 6:
            a0, b0, c0, d0, e0, f0 = a
            A, B, C, D, E, F = ctm
            ctm = (a0 * A + b0 * C, a0 * B + b0 * D, c0 * A + d0 * C, c0 * B + d0 * D,
                   e0 * A + f0 * C + E, e0 * B + f0 * D + F)
        elif op == b'w' and a:
            lw = a[0]
        elif op in (b'RG', b'G', b'K') and a:
            sc = float(np.mean(a[:3])) if op != b'K' else 1.0 - a[3]
        elif op in (b'rg', b'g', b'k') and a:
            fc = float(np.mean(a[:3])) if op != b'k' else 1.0 - a[3]
        elif op == b'BDC':
            nm = a[1] if len(a) > 1 and isinstance(a[1], bytes) else b'/?'
            layers.append(lname.get(nm[1:], nm.decode('latin1')))
        elif op == b'BMC':
            layers.append('?')
        elif op == b'EMC':
            if layers:
                layers.pop()
        elif op == b'm' and len(a) >= 2:
            if len(sub) > 0:
                subs.append(sub)
            sub = [tr(a[0], a[1])]
        elif op == b'l' and len(a) >= 2:
            sub.append(tr(a[0], a[1]))
        elif op == b'c' and len(a) >= 6:
            sub.append(tr(a[0], a[1])); sub.append(tr(a[2], a[3])); sub.append(tr(a[4], a[5]))
            curved = True
        elif op in (b'v', b'y') and len(a) >= 4:
            sub.append(tr(a[0], a[1])); sub.append(tr(a[2], a[3]))
            curved = True
        elif op == b're' and len(a) >= 4:
            if len(sub) > 0:
                subs.append(sub)
            x, y, w, h = a[:4]
            subs.append([tr(x, y), tr(x + w, y), tr(x + w, y + h), tr(x, y + h)])
            sub = []
        elif op == b'h':
            pass
        elif op in _PAINT or op == b'n':
            if len(sub) > 0:
                subs.append(sub)
            if op != b'n' and subs:
                pts = np.array([q for s in subs for q in s], np.float64)
                items.append(Item('path', len(items), (m.start(), m.end()), op,
                                  layers[-1] if layers else '', pts, lw * scale(), sc, fc,
                                  curved, len(subs)))
            subs, sub, curved = [], [], False
        elif op == b'BT':
            tm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        elif op == b'Tf' and len(a) >= 2:
            fsize = a[1]
        elif op == b'Tm' and len(a) == 6:
            tm = tuple(a)
        elif op in (b'Tj', b'TJ', b"'", b'"'):
            s = a[-1] if a else b''
            if isinstance(s, bytes) and s.startswith(b'<'):
                n = len(re.sub(rb'\s', b'', s)) // 4
            else:
                n = max(1, len(s) - 2)
            ta, tb, tc, td, te, tf = tm
            # glyph box in text space: x 0..0.6*n*size, y -0.2..0.9*size  (Arial-ish metrics)
            corners = []
            for gx, gy in ((0, -0.2), (0.62 * n, -0.2), (0.62 * n, 0.9), (0, 0.9)):
                X, Y = gx * fsize, gy * fsize
                corners.append(tr(ta * X + tc * Y + te, tb * X + td * Y + tf))
            items.append(Item('text', len(items), last_operand_span, op,
                              layers[-1] if layers else '', np.array(corners), nglyph=n))
    _PAGE_CACHE[page] = (data, items)
    return data, items


def write_pdf_variant(page, drops, path):
    """Copy of the PDF where the items `drops` (iterable of Item) of `page` are neutralised."""
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject
    data, _ = page_items(page)
    uniq = {it.span: it for it in drops if it.span is not None}
    edits = sorted(((s_, e_, b'n' if it.kind == 'path' else
                     (b'[]' if data[s_:s_ + 1] == b'[' else b'<>'))
                    for (s_, e_), it in uniq.items()), key=lambda e: e[0])
    out, pos = [], 0
    for s, e, rep in edits:
        out.append(data[pos:s]); out.append(rep); pos = e
    out.append(data[pos:])
    w = PdfWriter(clone_from=PDF)
    st = DecodedStreamObject()
    st.set_data(b''.join(out))
    w.pages[page - 1][NameObject('/Contents')] = w._add_object(st.flate_encode())
    with open(path, 'wb') as fh:
        w.write(fh)
    return path


def annotation_drops(page, box, tol=1.5, keep_text_inside=True, report=None):
    """Annotation objects to remove for a clean 'building only' view of the drawing inside `box`
    (x0, y0, x1, y1 page pt).

    * leaders: straight stroked polylines (<= 4 vertices) with a vertex outside box (+tol) and one
      strictly inside (-tol); their inner end points are collected
    * arrowheads / leader dots: small filled shapes (< 9 pt) touching a leader end point
    * anything (path or text) lying wholly outside the box (dims, level marks, level lines, labels)
      so nothing leaks into the crop padding
    * text whose centre lies outside the box (keep_text_inside keeps room names / signage)
    """
    _, items = page_items(page)
    x0, y0, x1, y1 = box
    drops, ends, leaders = [], [], []
    crossing_kept = []
    for it in items:
        p = it.pts
        ins = (p[:, 0] > x0 + tol) & (p[:, 0] < x1 - tol) & (p[:, 1] > y0 + tol) & (p[:, 1] < y1 - tol)
        out = (p[:, 0] < x0 - tol) | (p[:, 0] > x1 + tol) | (p[:, 1] < y0 - tol) | (p[:, 1] > y1 + tol)
        if it.kind == 'text':
            cx, cy = p[:, 0].mean(), p[:, 1].mean()
            inside_c = x0 < cx < x1 and y0 < cy < y1
            if not (keep_text_inside and inside_c):
                bx = it.bbox
                if bx[2] > x0 - 40 and bx[0] < x1 + 40 and bx[3] > y0 - 40 and bx[1] < y1 + 40:
                    drops.append(it)
            continue
        if not ins.any():
            if out.any():
                bx = it.bbox
                if bx[2] > x0 - 40 and bx[0] < x1 + 40 and bx[3] > y0 - 40 and bx[1] < y1 + 40:
                    drops.append(it)
            continue
        if out.any():
            if it.op == b'S' and not it.curved and len(p) <= 4 and it.nsub == 1:
                drops.append(it)
                leaders.append(it)
                ends.extend(p[ins].tolist())
            else:
                crossing_kept.append(it)
    dropped = {it.idx for it in drops}

    def _straight(it):
        return it.kind == 'path' and it.op == b'S' and not it.curved and it.nsub == 1 and len(it.pts) <= 4

    # chained leaders: a second leg that starts exactly on a vertex of a removed leader
    # (e.g. one label pointing at two objects) lies wholly inside the box
    cand = [it for it in items if _straight(it) and it.idx not in dropped]

    def _inside(q, m=tol):
        return x0 + m < q[0] < x1 - m and y0 + m < q[1] < y1 - m

    changed = True
    while changed and leaders:
        changed = False
        for it in cand:
            if it.idx in dropped:
                continue
            for q in (it.pts[0], it.pts[-1]):
                if not _inside(q, 3.0):
                    continue
                hit = [d for d in leaders if abs(d.lw - it.lw) < 0.02 and d.layer == it.layer and
                       np.min(np.hypot(d.pts[:, 0] - q[0], d.pts[:, 1] - q[1])) < 0.3]
                if hit:
                    drops.append(it); dropped.add(it.idx); leaders.append(it)
                    ends.extend([v for v in it.pts.tolist() if _inside(v)]); changed = True
                    break
    # dashed annotation lines (section cut lines, level lines) whose last dash pokes over the
    # frame edge: collinear continuation of a removed outside dash, same pen, near the edge
    dash = [it for it in drops if _straight(it) and len(it.pts) == 2]
    for it in cand:
        if it.idx in dropped or len(it.pts) != 2:
            continue
        p = it.pts
        if np.hypot(*(p[1] - p[0])) > 15:
            continue
        near_edge = (np.min(np.abs(p[:, 0][:, None] - np.array([x0, x1])[None])) < 12 or
                     np.min(np.abs(p[:, 1][:, None] - np.array([y0, y1])[None])) < 12)
        if not near_edge:
            continue
        for d in dash:
            if abs(d.lw - it.lw) > 0.02 or d.layer != it.layer:
                continue
            a, b = d.pts
            u = b - a
            L_ = np.hypot(*u)
            if L_ < 1e-6:
                continue
            nrm = np.array([-u[1], u[0]]) / L_
            if np.all(np.abs((p - a) @ nrm) < 0.3):
                gap = np.min(np.hypot(*(p[:, None, :] - d.pts[None, :, :]).reshape(-1, 2).T))
                if gap < 15:
                    drops.append(it); dropped.add(it.idx)
                    break
    if ends:
        E = np.array(ends)
        for it in items:
            if it.kind != 'path' or it.op not in _FILL:
                continue
            bx = it.bbox
            if max(bx[2] - bx[0], bx[3] - bx[1]) > 9.0:
                continue
            hit = ((E[:, 0] >= bx[0] - 2.5) & (E[:, 0] <= bx[2] + 2.5) &
                   (E[:, 1] >= bx[1] - 2.5) & (E[:, 1] <= bx[3] + 2.5))
            if hit.any() and it.idx not in dropped:
                drops.append(it); dropped.add(it.idx)
    if report is not None:
        report['leaders'] = len(ends)
        report['dropped'] = len(drops)
        report['crossing_kept'] = [(it.idx, it.op.decode(), it.layer, len(it.pts),
                                    [round(v, 1) for v in it.bbox]) for it in crossing_kept]
    return drops


# =========================================================================== #
# 2. rendering
# =========================================================================== #

def snap_region(x_pt, y_pt, w_pt, h_pt, dpi=DPI):
    """Snap a pt rectangle to the dpi pixel grid -> (x_px, y_px, w_px, h_px)."""
    x = int(round(pt2px(x_pt, dpi))); y = int(round(pt2px(y_pt, dpi)))
    x1 = int(round(pt2px(x_pt + w_pt, dpi))); y1 = int(round(pt2px(y_pt + h_pt, dpi)))
    return x, y, x1 - x, y1 - y


def render_region(page, x_pt, y_pt, w_pt, h_pt, dpi=DPI, pdf=None):
    """Render a page rectangle (pt, top-left origin) straight from the vector PDF with pdftoppm.
    Returns uint8 greyscale (H, W); the pixel origin is snap_region(...)[:2]."""
    x, y, w, h = snap_region(x_pt, y_pt, w_pt, h_pt, dpi)
    os.makedirs(BUILD, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=BUILD) as td:
        pre = os.path.join(td, 'r')
        subprocess.run(['pdftoppm', '-r', str(dpi), '-gray', '-aa', 'yes', '-aaVector', 'yes',
                        '-f', str(page), '-l', str(page), '-x', str(x), '-y', str(y),
                        '-W', str(w), '-H', str(h), '-png', '-singlefile', pdf or PDF, pre],
                       check=True)
        im = Image.open(pre + '.png')
        g = np.asarray(im.convert('L') if im.mode != 'L' else im).copy()
    return g


# =========================================================================== #
# 3. ink conversion + stylisation
# =========================================================================== #

def ink_lut(gamma=0.72, floor=0.0):
    """256-entry darkness -> alpha LUT.  alpha = ((d - floor)/(1 - floor)) ** gamma, d = 1 - g/255.
    gamma < 1 lifts the faint anti-aliased hairline pixels; paper (g = 255) maps to exactly 0."""
    d = 1.0 - np.arange(256, dtype=np.float64) / 255.0
    d = np.clip((d - floor) / (1.0 - floor), 0, 1)
    a = np.power(d, gamma)
    lut = np.clip(np.round(a * 255), 0, 255).astype(np.uint8)
    lut[255] = 0
    lut[0] = 255
    return lut


def ink_rgba(gray, color=INK, gamma=0.72, floor=0.0):
    """Grey render (uint8 or float 0..1) -> straight-alpha RGBA uint8: RGB = ink colour,
    alpha from darkness through ink_lut(gamma, floor)."""
    g = np.asarray(gray)
    if g.dtype != np.uint8:
        g = np.clip(np.round(g * 255), 0, 255).astype(np.uint8)
    if g.ndim == 3:
        g = cv2.cvtColor(g[..., :3], cv2.COLOR_RGB2GRAY)
    a = cv2.LUT(g, ink_lut(gamma, floor))
    out = np.empty(g.shape + (4,), np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = _hex(color)
    out[..., 3] = a
    return out


def _as_u8(rgba):
    if rgba.dtype == np.uint8:
        return rgba, True
    return np.clip(np.round(rgba * 255), 0, 255).astype(np.uint8), False


def _back(u8, was_u8):
    return u8 if was_u8 else u8.astype(np.float32) / 255.0


def recolor(rgba, hex_color):
    """Same alpha, new flat ink colour.  Keeps the input dtype (uint8 or float 0..1)."""
    out = np.array(rgba, copy=True)
    c = np.array(_hex(hex_color), np.float32)
    out[..., :3] = c if out.dtype == np.uint8 else c / 255.0
    return out


def thicken(rgba, px):
    """Grow line weight by `px` pixels (radius, fractional allowed) with a soft-edged disc
    grey-dilation of alpha: full-weight disc via cv2.dilate, the fractional rim via weighted
    shifted maxima, so 0.5 px really is half a pixel.  RGB of the result is the alpha-weighted
    original colour (flat ink stays flat)."""
    if px <= 0:
        return np.array(rgba, copy=True)
    u8, was = _as_u8(rgba)
    a = u8[..., 3]
    R = int(np.ceil(px + 0.5))
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1]
    wgt = np.clip(px + 0.5 - np.sqrt(xx ** 2 + yy ** 2), 0, 1)
    core = (wgt >= 0.999).astype(np.uint8)
    out_a = cv2.dilate(a, core)
    rim = np.argwhere((wgt > 0.001) & (wgt < 0.999))
    if len(rim):
        pad = cv2.copyMakeBorder(a, R, R, R, R, cv2.BORDER_CONSTANT, value=0)
        H, W = a.shape
        acc = out_a.astype(np.uint16) * 0
        for (j, i) in rim:
            sh = pad[j:j + H, i:i + W]
            v = (sh.astype(np.uint16) * int(round(wgt[j, i] * 256))) >> 8
            np.maximum(acc, v, out=acc)
        out_a = np.maximum(out_a, acc.astype(np.uint8))
    out = u8.copy()
    out[..., 3] = out_a
    # carry colour into the new pixels (dilate premultiplied colour channels the same way)
    if not (np.all(u8[..., 0] == u8[0, 0, 0]) and np.all(u8[..., 1] == u8[0, 0, 1])
            and np.all(u8[..., 2] == u8[0, 0, 2])):
        for ch in range(3):
            out[..., ch] = cv2.dilate(u8[..., ch], core)
    return _back(out, was)


def _smooth_noise(gh, gw, rng):
    return rng.standard_normal((gh, gw)).astype(np.float32)


def hand_wobble(rgba, amount=1.5, seed=0, wavelength=None, fine=0.35, pressure=0.0, tile=1024):
    """Subtle hand-drawn jitter: a smooth random displacement field (bicubic-interpolated
    lattice noise, two octaves) warps the linework by up to ~`amount` px; `pressure` (0..1)
    additionally modulates alpha along the lines like varying pen pressure.  Deterministic
    for a given seed; processed in row tiles to bound memory.  Same dtype as input."""
    u8, was = _as_u8(rgba)
    H, W = u8.shape[:2]
    if amount <= 0 and pressure <= 0:
        return _back(u8.copy(), was)
    wl = float(wavelength or max(60.0, 90.0 * amount))
    rng = np.random.default_rng(seed)
    octs = []
    for k, (wlen, amp) in enumerate(((wl, 1.0), (wl / 3.7, fine))):
        gh, gw = int(np.ceil(H / wlen)) + 4, int(np.ceil(W / wlen)) + 4
        octs.append((wlen, amp, _smooth_noise(gh, gw, rng), _smooth_noise(gh, gw, rng)))
    pg = _smooth_noise(int(np.ceil(H / wl)) + 4, int(np.ceil(W / wl)) + 4, rng)
    norm = amount / np.sqrt(sum(o[1] ** 2 for o in octs)) / 0.85
    pre = u8.astype(np.float32)
    pre[..., :3] *= pre[..., 3:4] / 255.0
    out = np.empty_like(u8)
    xs = np.arange(W, dtype=np.float32)
    for y0 in range(0, H, tile):
        y1 = min(H, y0 + tile)
        ys = np.arange(y0, y1, dtype=np.float32)
        gx, gy = np.meshgrid(xs, ys)
        dx = np.zeros_like(gx); dy = np.zeros_like(gx)
        for wlen, amp, nx, ny in octs:
            mx = (gx / wlen + 1.5).astype(np.float32); my = (gy / wlen + 1.5).astype(np.float32)
            dx += amp * cv2.remap(nx, mx, my, cv2.INTER_CUBIC)
            dy += amp * cv2.remap(ny, mx, my, cv2.INTER_CUBIC)
        mapx = (gx + dx * norm).astype(np.float32); mapy = (gy + dy * norm).astype(np.float32)
        m0 = max(0, int(np.floor(mapy.min())) - 2); m1 = min(H, int(np.ceil(mapy.max())) + 3)
        src = pre[m0:m1]
        res = cv2.remap(src, mapx, (mapy - m0).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                        borderValue=(0, 0, 0, 0))
        a = res[..., 3]
        if pressure > 0:
            pm = cv2.remap(pg, (gx / wl + 1.5).astype(np.float32), (gy / wl + 1.5).astype(np.float32),
                           cv2.INTER_CUBIC)
            a = a * np.clip(1.0 - pressure * 0.5 * (1.0 + np.tanh(pm)), 0, 1)
        rgb = np.where(res[..., 3:4] > 1e-3, res[..., :3] * 255.0 / np.maximum(res[..., 3:4], 1e-3), 0)
        out[y0:y1, :, :3] = np.clip(np.round(rgb), 0, 255).astype(np.uint8)
        out[y0:y1, :, 3] = np.clip(np.round(a), 0, 255).astype(np.uint8)
    return _back(out, was)


# =========================================================================== #
# 4. locating drawings on the 300 dpi sheets
# =========================================================================== #

_SHEET_CACHE: dict = {}


def sheet(n):
    if n not in _SHEET_CACHE:
        _SHEET_CACHE.clear()
        _SHEET_CACHE[n] = np.asarray(Image.open(SHEETS.format(n)).convert('L'))
    return _SHEET_CACHE[n]


def _sheet_pt(v):
    return v * 72.0 / SHEET_DPI


def locate_ink(n, window, thresh=250, pad_pt=6.0):
    """Tight bbox (page pt) of all ink inside `window` (sheet px x0, y0, x1, y1) + padding."""
    x0, y0, x1, y1 = window
    sub = sheet(n)[y0:y1, x0:x1] < thresh
    ys = np.nonzero(sub.any(1))[0]; xs = np.nonzero(sub.any(0))[0]
    if xs[0] == 0 or ys[0] == 0 or xs[-1] == sub.shape[1] - 1 or ys[-1] == sub.shape[0] - 1:
        raise RuntimeError(f'ink touches the search window edge on sheet {n}: {window}')
    bx = (x0 + xs[0], y0 + ys[0], x0 + xs[-1] + 1, y0 + ys[-1] + 1)
    return tuple(_sheet_pt(v) for v in bx), pad_pt


def locate_frame(n, window, frac=0.5, thresh=230):
    """Building frame (page pt) inside a sheet window: union bbox of all long horizontal and
    vertical ink runs (>= frac of the window size) — the slabs/roof/floor lines and outer walls.
    Leaders, dims and dashed level lines are shorter and are ignored."""
    x0, y0, x1, y1 = window
    ink = (sheet(n)[y0:y1, x0:x1] < thresh).astype(np.uint8)
    h, w = ink.shape
    Hl = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (int(w * frac), 1)))
    Vl = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(h * frac))))
    m = np.zeros((h, w), bool)
    # a run that reaches the window edge is a level line / leader running off into the label
    # column (it merged with a floor line) -> not part of the building frame
    for M, axis in ((Hl, 1), (Vl, 0)):
        nl, lab, st, _ = cv2.connectedComponentsWithStats(M, connectivity=8)
        for k in range(1, nl):
            X, Y, Ww, Hh, _a = st[k]
            if axis == 1 and (X <= 1 or X + Ww >= w - 1):
                continue
            if axis == 0 and (Y <= 1 or Y + Hh >= h - 1):
                continue
            m |= lab == k
    ys = np.nonzero(m.any(1))[0]; xs = np.nonzero(m.any(0))[0]
    bx = (x0 + xs[0], y0 + ys[0], x0 + xs[-1] + 1, y0 + ys[-1] + 1)
    return tuple(_sheet_pt(v) for v in bx)


# =========================================================================== #
# 5. the views
# =========================================================================== #

TITLE_BLOCK_LAYERS = ('A-TBLK', 'PDF3_0', 'PDF3_Text', 'WALL NEW')

# Search windows on the 300 dpi sheets (sheet px x0, y0, x1, y1).  'frame' windows exclude the
# label / dimension columns (leaders may still cross them), 'ink' windows hold the whole
# drawing incl. labels, dims and title and nothing else.
VIEWS = {
    'AA': dict(page=2, frame=(3229, 714, 6159, 2949), ink=(2452, 621, 6674, 3228)),
    'BB': dict(page=2, frame=(1378, 3818, 8146, 5991), ink=(546, 3694, 8599, 6333)),
    'E01': dict(page=3, frame=(1863, 1925, 3042, 3073), ink=(1521, 1894, 3508, 3229)),
    'E02': dict(page=3, frame=(5042, 1863, 8009, 3042), ink=(4861, 1832, 8320, 3198)),
    'E04': dict(page=3, frame=(5526, 4470, 7202, 5650), ink=(5495, 4440, 7672, 5790)),
    'PG': dict(page=1, frame=(2732, 1738, 6147, 3198), ink=(2000, 1100, 7000, 3330)),
    'PF': dict(page=1, frame=(2732, 3713, 6147, 5184), ink=(2000, 3600, 7000, 5800)),
    'AXO': dict(page=4, frame=None, ink=(2400, 345, 7400, 6700)),
}

PAD_PT = 2.0        # transparent margin around building-only crops
PAD_FULL_PT = 3.0   # margin around full (annotated) crops


@dataclass
class View:
    name: str
    page: int
    origin_pt: tuple          # page pt of pixel (0, 0) (snapped to the 600 dpi grid)
    frame_pt: tuple           # building frame in page pt (None for the axo)
    gray: np.ndarray          # uint8 600 dpi render
    clean: bool               # annotations removed?
    dropped: int = 0

    def px(self, x_pt, y_pt):
        return (pt2px(x_pt - self.origin_pt[0]), pt2px(y_pt - self.origin_pt[1]))

    def pt(self, x_px, y_px):
        return (self.origin_pt[0] + px2pt(x_px), self.origin_pt[1] + px2pt(y_px))


def _cache_path(key):
    return os.path.join(BUILD, 'cache', key + '.png')


def render_view(name, clean=True, dpi=DPI, use_cache=True):
    """Render a drawing straight from the PDF.  clean=True: building only (frame located on the
    300 dpi sheet, annotations removed from the vector content); clean=False: the whole drawing
    with labels / dims / title (tight ink bbox on the 300 dpi sheet)."""
    v = VIEWS[name]
    page = v['page']
    if clean and v['frame'] is not None:
        frame = locate_frame(page, v['frame'])
        x0, y0, x1, y1 = frame[0] - PAD_PT, frame[1] - PAD_PT, frame[2] + PAD_PT, frame[3] + PAD_PT
        rep = {}
        drops = annotation_drops(page, frame, report=rep)
    else:
        frame = locate_frame(page, v['frame']) if v['frame'] is not None else None
        bx, _ = locate_ink(page, v['ink'])
        p = PAD_FULL_PT
        x0, y0, x1, y1 = bx[0] - p, bx[1] - p, bx[2] + p, bx[3] + p
        _, items = page_items(page)
        drops = [it for it in items if it.layer in TITLE_BLOCK_LAYERS]
    X, Y, W, H = snap_region(x0, y0, x1 - x0, y1 - y0, dpi)
    origin = (px2pt(X, dpi), px2pt(Y, dpi))
    key = '%s_%s_%d_%d_%d_%d_%d' % (name, 'clean' if clean else 'full', dpi, X, Y, W, H)
    cp = _cache_path(key)
    if use_cache and os.path.exists(cp):
        g = np.asarray(Image.open(cp).convert('L'))
    else:
        os.makedirs(os.path.dirname(cp), exist_ok=True)
        pdf = None
        if drops:
            pdf = os.path.join(BUILD, 'cache', key + '.pdf')
            write_pdf_variant(page, drops, pdf)
        g = render_region(page, origin[0], origin[1], px2pt(W, dpi), px2pt(H, dpi), dpi, pdf=pdf)
        Image.fromarray(g).save(cp, compress_level=1)
        if pdf:
            os.remove(pdf)
    return View(name, page, origin, frame, g, clean, len(drops))


# =========================================================================== #
# 6. measuring registration anchors on the rendered images
# =========================================================================== #
# Everything below works on the 600 dpi grey renders (0 = ink, 188 = poché grey, 255 = paper).

POCHE = (170, 205)


def _runs(mask):
    """1-D bool -> [(start, end_inclusive)] of True runs."""
    m = np.asarray(mask, bool).astype(np.int8)
    d = np.diff(np.r_[0, m, 0])
    return list(zip(np.nonzero(d == 1)[0].tolist(), (np.nonzero(d == -1)[0] - 1).tolist()))


def _merge(runs, gap):
    out = []
    for a, b in runs:
        if out and a - out[-1][1] - 1 <= gap:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


def long_lines(g, horizontal=True, min_len=1000, thresh=140, roi=None):
    """Long straight horizontal (or vertical) ink lines via morphological opening.
    Returns [dict(c=centre, a, b (line thickness range), lo, hi (extent along the line))]."""
    x0, y0, x1, y1 = roi or (0, 0, g.shape[1], g.shape[0])
    ink = (g[y0:y1, x0:x1] < thresh).astype(np.uint8)
    k = (int(min_len), 1) if horizontal else (1, int(min_len))
    M = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, k))
    prof = M.any(1) if horizontal else M.any(0)
    out = []
    for a, b in _runs(prof):
        seg = M[a:b + 1] if horizontal else M[:, a:b + 1]
        ext = np.nonzero(seg.any(0) if horizontal else seg.any(1))[0]
        off, off2 = (y0, x0) if horizontal else (x0, y0)
        out.append(dict(c=(a + b) / 2 + off, a=a + off, b=b + off, lo=int(ext[0]) + off2,
                        hi=int(ext[-1]) + off2))
    return out


def measure_slabs(g):
    """Floor / roof slabs of a section: poché bands bounded by long lines.
    Returns slabs top->bottom: dict(top_y (FFL / roof top line), underside_y, ceiling_y)."""
    H, W = g.shape
    grey = ((g >= POCHE[0]) & (g <= POCHE[1])).mean(1)
    bands = [r for r in _runs(grey > 0.25) if r[1] - r[0] >= 25]
    lines = long_lines(g, True, 0.3 * W)
    slabs = []
    for a, b in bands:
        above = [l for l in lines if l['b'] < a + 3 and a - l['b'] < 15]
        below = [l for l in lines if l['a'] > b - 3 and l['a'] - b < 15]
        top = above[-1]['c'] if above else a - 0.5
        und = below[0]['c'] if below else b + 0.5
        ceil = [l for l in lines if und + 60 < l['c'] < und + 700 and l['hi'] - l['lo'] > 0.5 * W]
        slabs.append(dict(top_y=round(float(top), 1), underside_y=round(float(und), 1),
                          ceiling_y=round(float(ceil[0]['c']), 1) if ceil else None,
                          band=(int(a), int(b))))
    return slabs


def slab_gaps(g, slab, min_gap=300):
    """Openings in a slab's poché band (x ranges with no poché), e.g. the void."""
    a, b = slab['band']
    rows = g[a + 4:b - 3]
    grey = ((rows >= POCHE[0]) & (rows <= POCHE[1])).mean(0) > 0.5
    runs = [r for r in _runs(grey) if r[1] - r[0] > 20]
    gaps = []
    for (p, q), (r, s) in zip(runs[:-1], runs[1:]):
        if r - q - 1 >= min_gap:
            gaps.append((q + 1, r - 1))
    return gaps


def measure_trunk(g, x0, x1, y0, y1, thresh=110):
    """Tree trunk = the strongest pair of near-parallel, near-vertical long lines in the window
    (Hough transform, +-9 deg).  Returns (x_at(y) function, info dict)."""
    from skimage.transform import hough_line, hough_line_peaks
    ink = (g[y0:y1, x0:x1] < thresh).astype(np.uint8)
    ink = cv2.dilate(ink, np.ones((1, 5), np.uint8))   # tolerate the hand-drawn waviness
    ang = np.deg2rad(np.linspace(-9, 9, 181))
    h, th, d = hough_line(ink, theta=ang)
    acc, ths, ds = hough_line_peaks(h, th, d, num_peaks=16, min_distance=6, min_angle=2,
                                    threshold=0.2 * h.max())
    ym = (y1 - y0) / 2.0
    cand = [(int(a_), t, r, (r - ym * np.sin(t)) / np.cos(t)) for a_, t, r in zip(acc, ths, ds)]
    cand.sort(key=lambda c: -c[0])
    best = None
    for i, c in enumerate(cand):
        for e in cand[i + 1:]:
            sep = abs(c[3] - e[3])
            if 12 <= sep <= 260 and abs(c[1] - e[1]) < np.deg2rad(4):
                score = min(c[0], e[0])
                if best is None or score > best[0]:
                    best = (score, c, e)
    if best is None:
        raise RuntimeError('trunk not found')
    _, c, e = best

    def x_at(y):
        yy = y - y0
        xa = (c[2] - yy * np.sin(c[1])) / np.cos(c[1])
        xb = (e[2] - yy * np.sin(e[1])) / np.cos(e[1])
        return x0 + (xa + xb) / 2.0, abs(xa - xb)
    return x_at, dict(votes=(c[0], e[0]), lean_deg=round(float(np.rad2deg((c[1] + e[1]) / 2)), 2))


def fit_circle(xs, ys):
    """Algebraic (Kasa) least-squares circle -> (cx, cy, r)."""
    A = np.c_[2 * xs, 2 * ys, np.ones_like(xs)]
    b = xs ** 2 + ys ** 2
    (cx, cy, c), *_ = np.linalg.lstsq(A, b, rcond=None)
    return cx, cy, float(np.sqrt(c + cx ** 2 + cy ** 2))


def refine_circle(g, cx, cy, r, band=18, thresh=140, iters=3, region=None):
    """Refine a circle estimate by fitting all ink pixels within +-band px of it."""
    ys, xs = np.nonzero(g < thresh)
    if region is not None:
        X0, Y0, X1, Y1 = region
        k = (xs >= X0) & (xs < X1) & (ys >= Y0) & (ys < Y1)
        xs, ys = xs[k], ys[k]
    xs = xs.astype(np.float64); ys = ys.astype(np.float64)
    n = 0
    for _ in range(iters):
        d = np.hypot(xs - cx, ys - cy)
        k = np.abs(d - r) < band
        n = int(k.sum())
        if n < 20:
            break
        cx, cy, r = fit_circle(xs[k], ys[k])
        band = max(6, band * 0.6)
    return float(cx), float(cy), float(r), n


def hough_circles(g, rmin, rmax, roi=None, scale=0.25, n=8, param2=30, min_dist=None):
    """cv2.HoughCircles on a downscaled, slightly blurred ink image.  Full-res (cx, cy, r) list."""
    x0, y0, x1, y1 = roi or (0, 0, g.shape[1], g.shape[0])
    sub = g[y0:y1, x0:x1]
    sm = cv2.resize(sub, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    sm = cv2.GaussianBlur(sm, (5, 5), 1.2)
    c = cv2.HoughCircles(sm, cv2.HOUGH_GRADIENT, dp=1, minDist=(min_dist or rmin) * scale,
                         param1=80, param2=param2, minRadius=int(rmin * scale),
                         maxRadius=int(rmax * scale))
    if c is None:
        return []
    return [(x / scale + x0, y / scale + y0, r / scale) for x, y, r in c[0][:n]]


def circle_coverage(g, cx, cy, r, band=5, thresh=140, bins=360):
    """Fraction of the circumference (angular bins) carrying ink within +-band px."""
    R = int(r + band + 2)
    x0, y0 = max(0, int(cx) - R), max(0, int(cy) - R)
    sub = g[y0:int(cy) + R + 1, x0:int(cx) + R + 1] < thresh
    ys, xs = np.nonzero(sub)
    xs = xs + x0 - cx; ys = ys + y0 - cy
    k = np.abs(np.hypot(xs, ys) - r) < band
    ang = ((np.degrees(np.arctan2(ys[k], xs[k])) + 360) % 360 * bins / 360).astype(int)
    return len(np.unique(ang)) / bins


def best_circle(g, rmin, rmax, roi=None):
    """Largest well-supported circle: Hough candidates, least-squares refined, ranked by how much
    of the circumference is inked (a dashed circle still scores ~0.6, a mere arc much less)."""
    best = None
    for c in hough_circles(g, rmin, rmax, roi=roi, scale=0.25, n=8, param2=25):
        cx, cy, r, n = refine_circle(g, *c, band=30)
        if not (rmin * 0.9 < r < rmax * 1.1):
            continue
        cov = circle_coverage(g, cx, cy, r)
        if best is None or cov > best[3]:
            best = (cx, cy, r, cov)
    return best


# ---- per-drawing anchor measurement ------------------------------------------------------- #
# Prior search windows (in the clean 600 dpi render's px) only say *where to look*; every
# coordinate reported is measured from the pixels inside them.

def _r(v, nd=1):
    return None if v is None else round(float(v), nd)


def _walls_lr(g, min_frac=0.8):
    vl = long_lines(g, False, min_frac * g.shape[0])
    return vl[0], vl[-1]


def measure_section(g, trunk_band=950, rail_search=1000):
    """Slabs (FFLs), void (slab opening), first-floor rail, tree trunk of a section render."""
    H, W = g.shape
    roof, first, ground = measure_slabs(g)[:3]
    gaps = slab_gaps(g, first)
    a = {}
    a['roof_top_y'] = roof['top_y']
    a['roof_underside_y'] = roof['underside_y']
    a['ceiling_first_floor_y'] = roof['ceiling_y']
    a['ffl_first_y'] = first['top_y']
    a['first_slab_underside_y'] = first['underside_y']
    a['ceiling_ground_floor_y'] = first['ceiling_y']
    a['ffl_ground_y'] = ground['top_y']
    a['ground_slab_bottom_y'] = ground['underside_y']
    wl, wr = _walls_lr(g)
    a['outer_wall_left_x'] = _r(wl['c']); a['outer_wall_right_x'] = _r(wr['c'])
    a['first_slab_openings_x'] = [[int(p), int(q)] for p, q in gaps]
    # rail = the long double horizontal line just above the first FFL over the widest opening
    gx0, gx1 = max(gaps, key=lambda t: t[1] - t[0])
    y0 = int(first['top_y'] - rail_search)
    hl = long_lines(g, True, 0.5 * (gx1 - gx0), roi=(max(0, gx0 - 200), y0, min(W, gx1 + 200),
                                                    int(first['top_y'] - 40)))
    if hl:
        top = hl[0]
        a['rail_top_y'] = _r(top['c'])
        a['rail_x'] = [int(top['lo']), int(top['hi'])]
        a['rail_lines_y'] = [_r(l['c']) for l in hl]
    a['px_per_m'] = _r(((ground['top_y'] - first['top_y']) / 5.0 + (first['top_y'] - roof['top_y']) / 4.0) / 2, 2)
    return a, (gx0, gx1), (roof, first, ground)


def _trunk(g, x0, x1, ground_y, first_y, band):
    f, info = measure_trunk(g, int(x0), int(x1), int(ground_y - band), int(ground_y - 5))
    xg, wg = f(ground_y)
    xf, wf = f(first_y)
    xm, _ = f((ground_y + first_y) / 2)
    return dict(trunk_at_ffl_ground_x=_r(xg), trunk_width_at_ground_px=_r(wg),
                trunk_at_ffl_first_x=_r(xf), trunk_mid_height_x=_r(xm),
                trunk_lean_deg=info['lean_deg'])


def measure_section_AA(g):
    a, (vx0, vx1), (roof, first, ground) = measure_section(g)
    a['void_left_x'] = int(vx0); a['void_right_x'] = int(vx1)
    a['void_centre_x'] = _r((vx0 + vx1) / 2)
    a.update(_trunk(g, vx0 + 150, vx1 - 150, ground['top_y'], first['top_y'], 950))
    return a


BB_SPLIT_PRIORS = dict(ground_wall=(6900, 7500), first_panel=(6650, 6950), counter=(6650, 7500))


def measure_section_BB(g):
    a, (ox0, ox1), (roof, first, ground) = measure_section(g)
    rx0, rx1 = a['rail_x']
    a['void_rail_x'] = [rx0, rx1]
    a.update(_trunk(g, rx0 + 200, rx1 - 200, ground['top_y'], first['top_y'], 1300))
    # split between the party-hall + cabins portion and the bar + void + stairs portion
    gx0, gx1 = BB_SPLIT_PRIORS['ground_wall']
    gw = long_lines(g, False, 0.6 * (ground['top_y'] - first['underside_y']),
                    roi=(gx0, int(first['underside_y']), gx1, int(ground['top_y'])))
    wall = (gw[0]['a'], gw[-1]['b'])
    cx0, cx1 = BB_SPLIT_PRIORS['counter']
    ct = long_lines(g, True, 400, roi=(cx0, int(first['top_y'] - 700), cx1, int(first['top_y'] - 50)))
    counter_top = ct[0]['a']
    px0, px1 = BB_SPLIT_PRIORS['first_panel']
    pv = long_lines(g, False, 0.8 * (counter_top - roof['ceiling_y']), thresh=60,
                    roi=(px0, int(roof['ceiling_y']), px1, int(counter_top - 2)))
    panel_edge = (pv[-1]['a'], pv[-1]['b'])
    counter_left = ct[0]['lo']                                   # left end of the counter top
    slab_bottom = int(round(first['underside_y'] + 4))   # whole slab follows the counter cut
    a['split'] = dict(ground_wall_x=[int(wall[0]), int(wall[1])], counter_top_y=int(counter_top),
                      counter_left_x=int(counter_left),
                      first_floor_panel_edge_x=[int(panel_edge[0]), int(panel_edge[1])],
                      slab_cut_y=slab_bottom)
    return a


def bb_split_masks(g, split):
    """Per-row keep limits for the stepped BB split -> (left_max_x(row), right_min_x(row))."""
    H, W = g.shape
    rows = np.arange(H)
    ct = split['counter_top_y'] - 2
    sm = split['slab_cut_y']
    lmax = np.where(rows < ct, split['first_floor_panel_edge_x'][1] + 2,
                    np.where(rows < sm, split['counter_left_x'] - 3, split['ground_wall_x'][1] + 1))
    rmin = np.where(rows < ct, split['first_floor_panel_edge_x'][0] - 2,
                    np.where(rows < sm, split['counter_left_x'] - 2, split['ground_wall_x'][0] - 1))
    return lmax, rmin


def measure_elev02(g):
    """Elevation 02: cabins (shell edges = black long verticals), openings (gaps in the fluting),
    pendants (shade bbox in each opening), floor and ceiling lines, drapery bottom."""
    H, W = g.shape
    hl = long_lines(g, True, 0.6 * W)
    ceiling_y, floor_y = hl[0]['c'], hl[-1]['c']
    edges = [l['c'] for l in long_lines(g, False, 0.4 * H, thresh=60)]
    frame_l, frame_r = edges[0], edges[-1]
    inner = edges[1:-1]                      # cabin 1 left .. cabin 4 right (pairs at joints)
    # fluting columns in the band between the panel tops and the seat backs
    vl_top = min(l['lo'] for l in long_lines(g, False, 0.4 * H, thresh=60)[2:-2]) if len(edges) > 4 else int(0.45 * H)
    band = g[vl_top + 120: vl_top + 300]
    col = (band < 140).mean(0) > 0.9
    clusters = _merge(_runs(col), 150)
    openings = [(clusters[i][1] + 1, clusters[i + 1][0] - 1) for i in range(len(clusters) - 1)]
    cabins = []
    bounds = [inner[0]] + [v for v in inner[1:-1]] + [inner[-1]]
    lefts = [bounds[0]] + bounds[2::2]
    rights = bounds[1::2][:len(lefts) - 1] + [bounds[-1]]
    # drapery bottom: lowest swag pixel above the pendant shades (cords excluded)
    for k, (o0, o1) in enumerate(openings):
        y_off = int(ceiling_y) + 40
        o0s, o1s = o0 + 8, o1 - 8                     # keep clear of the fluting's first lines
        sub = g[y_off: vl_top + 150, o0s:o1s + 1] < 140
        has = sub.any(1)
        idx = np.arange(sub.shape[1])
        lo = np.where(has, np.argmax(sub, 1), 0)
        hi = np.where(has, sub.shape[1] - 1 - np.argmax(sub[:, ::-1], 1), -1)
        ext = np.where(has, hi - lo + 1, 0)
        # cord: the narrow ink (< 40 px wide) directly above the shade; shade: the last block of
        # rows wider than the cord, ending at the shade's bottom rim
        wide = _runs(ext > 40)
        sb = wide[-1]
        cord_w = np.median(ext[max(0, sb[0] - 150):sb[0] - 5])
        sb0 = sb[0]
        while sb0 > 0 and ext[sb0 - 1] > cord_w + 3:
            sb0 -= 1
        shade = (o0s + int(lo[sb0:sb[1] + 1].min()), y_off + sb0, o0s + int(hi[sb0:sb[1] + 1].max()),
                 y_off + sb[1])
        cord_rows = sub[max(0, sb0 - 200):sb0 - 20]
        cxs = np.nonzero(cord_rows.any(0))[0]
        cord_x = o0s + float(np.median(cxs)) if len(cxs) else None
        cabins.append(dict(n=k + 1, left_x=_r(lefts[k]), right_x=_r(rights[k]),
                           centre_x=_r((lefts[k] + rights[k]) / 2),
                           opening_x=[int(o0), int(o1)], opening_centre_x=_r((o0 + o1) / 2),
                           opening_top_y=int(vl_top),
                           pendant_x=_r((shade[0] + shade[2]) / 2), pendant_cord_x=_r(cord_x),
                           pendant_shade_bbox=[int(v) for v in shade]))
    # drapery bottom (exclude cords +-12 px and the frame/wall columns)
    top_shade = min(c['pendant_shade_bbox'][1] for c in cabins)
    m = g[int(ceiling_y) + 5: top_shade - 30] < 140
    for c in cabins:
        x = int(round(c['pendant_cord_x']))
        m[:, x - 12:x + 13] = False
    m[:, :int(inner[0]) + 6] = False
    m[:, int(inner[-1]) - 6:] = False
    rows = np.nonzero(m.sum(1) > 3)[0]
    drapery_bottom = int(ceiling_y) + 5 + int(rows[-1])
    return dict(ceiling_y=_r(ceiling_y), drapery_top_y=_r(ceiling_y), drapery_bottom_y=drapery_bottom,
                floor_y=_r(floor_y), wall_left_x=[_r(frame_l), _r(inner[0])],
                wall_right_x=[_r(inner[-1]), _r(frame_r)], cabins=cabins,
                cabin_joints_x=[[_r(inner[i]), _r(inner[i + 1])] for i in range(1, len(inner) - 1, 2)],
                pendants_x=[c['pendant_x'] for c in cabins],
                opening_centres_x=[c['opening_centre_x'] for c in cabins])


PLAN_PRIORS = dict(cabin_strip=(0, 600, 4000, 1600), void=(3800, 400, 6300, 2700))


def measure_plan_ground(g):
    H, W = g.shape
    vx, vy, vr, cov = best_circle(g, 380, 650, roi=PLAN_PRIORS['void'])
    a = dict(void_circle=dict(cx=_r(vx), cy=_r(vy), r=_r(vr), coverage=_r(cov, 2),
                              note='dashed circle = edge of the double-height void above'))
    # cabins: round tables (Hough) + walls (vertical poché bands) + curved fronts
    tabs = hough_circles(g, 90, 160, roi=PLAN_PRIORS['cabin_strip'], scale=0.5, n=8, param2=30,
                         min_dist=500)
    tabs = sorted(tabs, key=lambda t: t[0])[:4]
    tabs = [refine_circle(g, *t, band=12, region=(int(t[0] - 220), int(t[1] - 220),
                                                  int(t[0] + 220), int(t[1] + 220))) for t in tabs]
    cy = float(np.mean([t[1] for t in tabs]))
    rows = g[int(cy - 300):int(cy + 200)]
    poche = ((rows >= POCHE[0]) & (rows <= POCHE[1])).mean(0) > 0.9
    walls = [r for r in _runs(poche) if r[1] - r[0] >= 12]
    xs_t = [t[0] for t in tabs]
    walls = [w for w in walls if xs_t[0] - 900 < w[0] < xs_t[-1] + 900]
    cabins = []
    for k, (tx, ty, tr_, _) in enumerate(tabs):
        lw = max([w for w in walls if w[1] < tx], key=lambda w: w[1])
        rw = min([w for w in walls if w[0] > tx], key=lambda w: w[0])
        x0, x1 = lw[1] + 1, rw[0] - 1
        colp = g[:, x0 + 20:x1 - 20]
        pc = ((colp >= POCHE[0]) & (colp <= POCHE[1])).mean(1)
        back = [r for r in _runs(pc > 0.9) if r[1] < ty][-1]
        # curved front: lowest poché row below the table inside the cell
        cell = g[int(ty):int(ty) + 520, x0 + 4:x1 - 3]
        pm = (cell >= POCHE[0]) & (cell <= POCHE[1])
        prow = np.nonzero(pm.any(1))[0]
        front = int(ty) + int(prow[-1])
        low = pm[prow[-1] - 30:prow[-1] + 1].any(0)
        pieces = [r for r in _runs(low) if r[1] - r[0] > 5]
        if len(pieces) >= 2:
            op = (x0 + 4 + pieces[0][1] + 1, x0 + 4 + pieces[-1][0] - 1)
        elif len(pieces) == 1:   # only one curved jamb: the cabin opens up to the straight wall
            mid = x0 + 4 + (pieces[0][0] + pieces[0][1]) / 2
            op = (x0 + 4 + pieces[0][1] + 1, x1) if mid < (x0 + x1) / 2 else (x0, x0 + 4 + pieces[0][0] - 1)
        else:
            op = None
        # outer radius of the round sofa (strongest ring of ink 220..420 px from the table centre,
        # upper half only)
        yy, xx = np.nonzero(g[int(ty) - 450:int(ty), int(tx) - 450:int(tx) + 451] < 140)
        d = np.hypot(xx - 450, yy - 450)
        hist = np.bincount(d[(d > 220) & (d < 430)].astype(int), minlength=430)
        sofa_r = int(np.argmax(hist[300:430]) + 300) if hist[300:430].max() > 0 else None
        cabins.append(dict(n=k + 1, centre=[_r(tx), _r(ty)], table_r=_r(tr_), sofa_outer_r=sofa_r,
                           cell_x=[int(x0), int(x1)], back_wall_inner_y=int(back[1] + 1),
                           back_wall_outer_y=int(back[0]),
                           front_outer_y=front, opening_x=[int(op[0]), int(op[1])] if op else None,
                           wall_bands_x=[[int(lw[0]), int(lw[1])], [int(rw[0]), int(rw[1])]]))
    a['cabins'] = cabins
    a['cabin_centres'] = [c['centre'] for c in cabins]
    # bar: the counter outline = largest ink component between the cabins' right wall and the void
    bar_wall = min([w for w in walls if w[0] > cabins[-1]['cell_x'][1]], key=lambda w: w[0])
    bx0 = bar_wall[1] + 8
    bx1 = int(vx - vr - 30)
    by0, by1 = int(cy - 450), int(vy + vr + 250)
    ink = (g[by0:by1, bx0:bx1] < 140).astype(np.uint8)
    nl, lab, st, cen = cv2.connectedComponentsWithStats(ink, connectivity=8)
    k = 1 + int(np.argmax(st[1:, 2] * st[1:, 3]))
    X, Y, Ww, Hh, _ = st[k]
    a['bar'] = dict(bbox=[int(bar_wall[1]), int(by0 + Y), int(bx0 + X + Ww), int(by0 + Y + Hh)],
                    back_wall_x=[int(bar_wall[0]), int(bar_wall[1])],
                    note='counter outline bbox; x0 = face of the wall the counter returns into')
    stools = []
    for j in range(1, nl):
        X2, Y2, W2, H2, A2 = st[j]
        if 80 < W2 < 200 and 80 < H2 < 200 and X2 > X + Ww - 10:
            stools.append([_r(bx0 + cen[j][0]), _r(by0 + cen[j][1])])
    a['bar']['stools'] = sorted(stools, key=lambda s: s[1])
    # entrance facade (right-hand wall): outer & inner face lines
    vl = long_lines(g, False, 0.25 * H, roi=(W - 450, 0, W, H))
    a['entrance_wall'] = dict(outer_x=_r(vl[-1]['c']), inner_x=_r(vl[0]['c']))
    a['entrance_wall_x'] = _r(vl[-1]['c'])
    wl, wr = _walls_lr(g, 0.5)
    hl = long_lines(g, True, 0.5 * W)
    a['plan_outer'] = dict(left_x=_r(wl['c']), right_x=_r(vl[-1]['c']), top_y=_r(hl[0]['c']),
                           bottom_y=_r(hl[-1]['c']))
    return a


def ring_radii(g, cx, cy, r, band=25, thresh=140):
    """Radii of the individual concentric lines of a ring (radial ink histogram peaks)."""
    R = int(r + band + 2)
    x0, y0 = int(cx) - R, int(cy) - R
    ys, xs = np.nonzero(g[y0:y0 + 2 * R + 1, x0:x0 + 2 * R + 1] < thresh)
    d = np.hypot(xs + x0 - cx, ys + y0 - cy)
    d = d[np.abs(d - r) < band]
    h, e = np.histogram(d, bins=np.arange(r - band, r + band + 0.5, 0.5))
    h = np.convolve(h, np.ones(3) / 3, 'same')
    c = (e[:-1] + e[1:]) / 2
    on = h > 0.3 * h.max()
    # each inked line = one contiguous run of strong bins (merged across <= 2 px dips)
    runs = _merge(_runs(on), 4)
    return [_r(np.average(c[a:b + 1], weights=h[a:b + 1])) for a, b in runs]


def measure_plan_first(g):
    vx, vy, vr, cov = best_circle(g, 380, 650, roi=PLAN_PRIORS['void'])
    return dict(void_circle=dict(cx=_r(vx), cy=_r(vy), r=_r(vr), coverage=_r(cov, 2),
                                 ring_line_radii=ring_radii(g, vx, vy, vr),
                                 note='double-line ring = void edge at first floor (OPEN BELLOW); '
                                      'r = ring centre line'))


def measure_frame_lines(g):
    """Generic: top / floor long lines and outer verticals of an elevation."""
    H, W = g.shape
    hl = long_lines(g, True, 0.6 * W)
    vl = long_lines(g, False, 0.6 * H)
    out = dict(top_y=_r(hl[0]['c']), floor_y=_r(hl[-1]['c']))
    if vl:
        out.update(left_x=_r(vl[0]['c']), right_x=_r(vl[-1]['c']))
    return out


def tree_canopy(g, void):
    """Tree canopy symbol inside a plan's void circle (Hough r 120..300 px, inside the void)."""
    cx, cy, r = void['cx'], void['cy'], void['r']
    roi = (int(cx - r), int(cy - r), int(cx + r), int(cy + r))
    best = None
    for c in hough_circles(g, 120, 300, roi=roi, scale=0.5, n=6, param2=20, min_dist=50):
        if np.hypot(c[0] - cx, c[1] - cy) > 0.4 * r:
            continue
        # the canopy outline is a light-grey hairline -> generous ink threshold
        x, y, rr, n = refine_circle(g, *c, band=12, thresh=235, region=roi)
        if n < 50:
            continue
        cov = circle_coverage(g, x, y, rr, band=4, thresh=235)
        if best is None or cov > best[3]:
            best = (x, y, rr, cov)
    if best is None:
        return None
    return dict(cx=_r(best[0]), cy=_r(best[1]), r=_r(best[2]), coverage=_r(best[3], 2))


def measure_layer_extent(v, layer, dpi=150):
    """Render ONLY one CAD layer of a view's region (all other objects neutralised) and measure
    the ink extent -> dict(bbox, base) in the view's 600 dpi px (base = lowest inked point)."""
    _, items = page_items(v.page)
    drops = [it for it in items if it.layer != layer]
    pdf = os.path.join(BUILD, 'cache', f'layer_{v.page}_{re.sub(r"[^A-Za-z0-9]", "_", layer)}.pdf')
    os.makedirs(os.path.dirname(pdf), exist_ok=True)
    write_pdf_variant(v.page, drops, pdf)
    H, W = v.gray.shape
    g = render_region(v.page, v.origin_pt[0], v.origin_pt[1], px2pt(W), px2pt(H), dpi, pdf=pdf)
    os.remove(pdf)
    ys, xs = np.nonzero(g < 200)
    k = DPI / dpi
    bot = ys.max()
    bx = xs[ys >= bot - 2]
    return dict(bbox=[_r(xs.min() * k), _r(ys.min() * k), _r((xs.max() + 1) * k), _r((bot + 1) * k)],
                base=[_r((bx.mean() + 0.5) * k), _r((bot + 1) * k)])


# =========================================================================== #
# 7. build
# =========================================================================== #

_NOSHIFT = {'r', 'n', 'coverage', 'ring_line_radii', 'table_r', 'sofa_outer_r', 'px_per_m', 'trunk_width_at_ground_px',
            'trunk_lean_deg', 'note'}
_PAIRS = {'centre', 'stools', 'cabin_centres', 'tree_base'}


def shift_anchors(obj, dx, dy, key=''):
    """Translate an anchor tree by (-dx, -dy): keys *_x / cx -> x, *_y / cy -> y, centre-like
    keys hold (x, y) pairs, *bbox holds (x0, y0, x1, y1)."""
    if isinstance(obj, dict):
        return {k: shift_anchors(v, dx, dy, k) for k, v in obj.items()}
    if obj is None or isinstance(obj, str) or key in _NOSHIFT:
        return obj
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], dict):
            return [shift_anchors(o, dx, dy, '') for o in obj]
        if key.endswith('bbox'):
            return [_r(obj[0] - dx), _r(obj[1] - dy), _r(obj[2] - dx), _r(obj[3] - dy)]
        if key in _PAIRS:
            if obj and isinstance(obj[0], (list, tuple)):
                return [[_r(p[0] - dx), _r(p[1] - dy)] for p in obj]
            return [_r(obj[0] - dx), _r(obj[1] - dy)]
        return [shift_anchors(o, dx, dy, key) for o in obj]
    if key.endswith('_x') or key == 'cx':
        return _r(obj - dx)
    if key.endswith('_y') or key == 'cy':
        return _r(obj - dy)
    return obj


def _save_rgba(rgba, name):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    rgba = np.ascontiguousarray(rgba)
    im = Image.frombuffer('RGBA', (rgba.shape[1], rgba.shape[0]), rgba, 'raw', 'RGBA', 0, 1)
    im.save(path, compress_level=6, dpi=(DPI, DPI))
    return path


def _src(v, extra=None):
    d = dict(pdf='assets/client_RESTAURANT_drawings.pdf', page=v.page,
             sheet_png=f'assets/drawings/sheet-{v.page}.png',
             origin_pt=[_r(v.origin_pt[0], 2), _r(v.origin_pt[1], 2)],
             origin_sheet300_px=[_r(v.origin_pt[0] * SHEET_DPI / 72, 1), _r(v.origin_pt[1] * SHEET_DPI / 72, 1)],
             px_per_pt=round(DPI / 72, 4), dpi=DPI,
             annotations_removed=v.clean, pdf_objects_neutralised=v.dropped)
    if v.frame_pt is not None:
        d['building_frame_pt'] = [_r(t, 2) for t in v.frame_pt]
    if extra:
        d.update(extra)
    return d


USE_LINE = ('Overlay in ink (multiply 60-90 %, or normal at 35-70 % opacity) over the photographic '
            'layers; scale with compose.resize (alpha-correct). Below ~0.45x apply '
            'thicken(rgba, 0.4 / scale) first so the 1-px hairlines survive; recolor() for '
            'tinted ghosts; hand_wobble() for a sketchier hand.')


def build(use_cache=True, contact=True):
    """Regenerate every asset in assets/lines/, index.json and the contact sheet."""
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PREVIEW, exist_ok=True)
    index = dict(module='src/lib/linework.py', generated_by='linework.build()',
                 conventions=dict(format='8-bit RGBA PNG, straight alpha, RGB = ink #2B2420 everywhere, '
                                         'alpha = (1 - grey/255) ** 0.72, paper = alpha 0',
                                  dpi=DPI, coords='pixel coords of each file, x right, y down, '
                                                  'origin top-left; *_x / *_y keys, centre = [x, y], '
                                                  'bbox = [x0, y0, x1, y1]',
                                  page_pt='page point = origin_pt + px / px_per_pt (page top-left origin)'),
                 functions={
                     'render_region(page, x_pt, y_pt, w_pt, h_pt, dpi=600, pdf=None)': 'uint8 grey render of a page rectangle straight from the vector PDF (pdftoppm)',
                     "ink_rgba(gray, color='#2B2420', gamma=0.72, floor=0.0)": 'grey -> straight-alpha ink RGBA, paper exactly alpha 0',
                     'recolor(rgba, hex)': 'same alpha, new flat ink colour',
                     'thicken(rgba, px)': 'grow line weight by px (fractional ok) - use before strong downscaling',
                     'hand_wobble(rgba, amount=1.5, seed=0, wavelength=None, fine=0.35, pressure=0.0)': 'subtle deterministic hand-drawn jitter (+ optional pen-pressure fade)',
                     'render_view(name, clean=True)': "re-render one of VIEWS ('AA','BB','E01','E02','E04','PG','PF','AXO') at 600 dpi",
                 },
                 assets=[])
    A = index['assets']

    def add(name, rgba, v, desc, anchors=None, use=USE_LINE, extra_src=None, notes=None):
        path = _save_rgba(rgba, name)
        e = dict(path=os.path.relpath(path, ROOT), size=[int(rgba.shape[1]), int(rgba.shape[0])],
                 description=desc, source=_src(v, extra_src), anchors=anchors or {}, suggested_use=use)
        if notes:
            e['notes'] = notes
        A.append(e)
        print(f'  {name:26s} {rgba.shape[1]}x{rgba.shape[0]}', flush=True)
        return e

    def offset(v_from, v_to):
        """px offset of v_from's (0,0) inside v_to."""
        return (int(round(pt2px(v_from.origin_pt[0] - v_to.origin_pt[0]))),
                int(round(pt2px(v_from.origin_pt[1] - v_to.origin_pt[1]))))

    # ---- section A-A ----------------------------------------------------------------------
    v = render_view('AA', True, use_cache=use_cache)
    a_aa = measure_section_AA(v.gray)
    add('section_AA.png', ink_rgba(v.gray), v,
        'SECTION A-A, building only: both storeys with ceiling drapery, the double-height void with '
        'the tree, stainless rail, bar with RESTAURANT signage + pendants + stools, service stairs. '
        'Level/dimension column, label text, leaders + arrowheads and title removed from the vector '
        'content (not erased).', a_aa)
    vf = render_view('AA', False, use_cache=use_cache)
    ox, oy = offset(v, vf)
    add('section_AA_full.png', ink_rgba(vf.gray), vf,
        'SECTION A-A as drawn: building + level marks (FFL +11/+16/+20 m), 4000/5000 dims, all '
        'labels with leaders, and the SECTION A-A title with underline.',
        dict(section_AA_origin_in_this_file=[ox, oy], **shift_anchors(a_aa, -ox, -oy)))
    del v, vf

    _PAGE_CACHE.clear()
    # ---- section B-B ----------------------------------------------------------------------
    v = render_view('BB', True, use_cache=use_cache)
    a_bb = measure_section_BB(v.gray)
    rgba = ink_rgba(v.gray)
    add('section_BB.png', rgba, v,
        'SECTION B-B (long section), building only: party hall with curtains, 4 ground-floor '
        'cabins under festoon drapery with pendants, first-floor cabins + planters, first-floor bar, '
        'void with tree and stainless rail, both stair flights, dining. Annotations removed.', a_bb)
    sp = a_bb['split']
    lmax, rmin = bb_split_masks(v.gray, sp)
    H, W = v.gray.shape
    xl1 = int(lmax.max()) + 1
    left = rgba[:, :xl1].copy()
    cols = np.arange(xl1)[None, :]
    left[..., 3][cols > lmax[:, None]] = 0
    keys_l = ['roof_top_y', 'roof_underside_y', 'ceiling_first_floor_y', 'ffl_first_y',
              'first_slab_underside_y', 'ceiling_ground_floor_y', 'ffl_ground_y',
              'ground_slab_bottom_y', 'outer_wall_left_x', 'px_per_m', 'split']
    add('section_BB_left.png', left, v,
        'SECTION B-B left portion: party hall + the 4 ground-floor private cabins (drapery, pendants, '
        'banquettes) and above them the first-floor toilets/brick wall + first-floor cabins with '
        'planters. Stepped cut: first floor ends at the edge of the cabin fluting, ground floor at '
        'the far face of the wall between cabins and bar (transparent beyond).',
        dict(offset_in_section_BB=[0, 0], **{k: a_bb[k] for k in keys_l}),
        extra_src=dict(crop_of='assets/lines/section_BB.png', crop_x=[0, xl1]))
    xr0 = int(rmin.min())
    right = rgba[:, xr0:].copy()
    cols = np.arange(xr0, W)[None, :]
    right[..., 3][cols < rmin[:, None]] = 0
    keys_r = [k for k in a_bb if k not in ('outer_wall_left_x',)]
    a_r = shift_anchors({k: a_bb[k] for k in keys_r}, xr0, 0)
    add('section_BB_right.png', right, v,
        'SECTION B-B right portion: first-floor bar, the void with the tree and stainless steel rail, '
        'the double stair flights, ground-floor bar counter, dining, entrance-end wall. Stepped cut '
        '(first-floor bar counter / wall face / ground-floor wall) mirrors section_BB_left.',
        dict(offset_in_section_BB=[xr0, 0], **a_r),
        extra_src=dict(crop_of='assets/lines/section_BB.png', crop_x=[xr0, W]))
    del rgba, left, right, v

    _PAGE_CACHE.clear()
    # ---- elevations -------------------------------------------------------------------------
    v = render_view('E02', True, use_cache=use_cache)
    a_e2 = measure_elev02(v.gray)
    add('elev02_cabins.png', ink_rgba(v.gray), v,
        'ELEVATION 02 - ground-floor private cabin seating, drawing only: festoon ceiling draping '
        'across the top, 4 fluted cabin shells with arched openings, pendant in each, round '
        'banquettes + tables, CABIN 01-04 names. Right-hand labels/leaders, 2400 dim and title removed.',
        a_e2)
    vf = render_view('E02', False, use_cache=use_cache)
    ox, oy = offset(v, vf)
    add('elev02_full.png', ink_rgba(vf.gray), vf,
        'ELEVATION 02 as drawn, with the 2400 height dimension, right-hand labels (CEILING DRAPING, '
        'PENDANT LIGHT, ROUND SOFA SEATING INSIDE, CURVE WALL FROM OUT SIDE, ROUND TABLE) and title.',
        dict(elev02_cabins_origin_in_this_file=[ox, oy], **shift_anchors(a_e2, -ox, -oy)))
    del v, vf
    v = render_view('E01', True, use_cache=use_cache)
    add('elev01_bar.png', ink_rgba(v.gray), v,
        'ELEVATION 01 - ground-floor bar, drawing only: fluted counter-hanging ceiling with '
        'RESTAURANT signage + leaf logo, decorative brick back wall, 4 dome pendants, POS + espresso '
        'machine on the counter, fluted counter front, 4 stools. Dims/labels/title removed.',
        measure_frame_lines(v.gray))
    v = render_view('E04', True, use_cache=use_cache)
    add('elev04_partyhall.png', ink_rgba(v.gray), v,
        'ELEVATION 04 - party hall, drawing only: festoon draping, tied-back sheer curtains, curved '
        'fluted wall, pendants, arched-back dining chairs at the long table. Labels/title removed.',
        measure_frame_lines(v.gray))
    del v

    _PAGE_CACHE.clear()
    # ---- plans ---------------------------------------------------------------------------------
    v = render_view('PG', True, use_cache=use_cache)
    a_pg = measure_plan_ground(v.gray)
    a_pg['tree_canopy'] = tree_canopy(v.gray, a_pg['void_circle'])
    rgba = ink_rgba(v.gray)
    add('plan_ground.png', rgba, v,
        'PROPOSED GROUND FLOOR plan only (room names kept): kitchen strip, party hall, 4 private '
        'cabins, curved banquette, bar, dashed open-void circle with the tree, stairs, glazed entrance '
        'end. Section markers A/B, their cut lines and the title removed.', a_pg)
    cab = a_pg['cabins']
    x0 = cab[0]['wall_bands_x'][0][0] - 40
    x1 = cab[-1]['wall_bands_x'][1][1] + 40
    y0 = min(c['back_wall_outer_y'] for c in cab) - 24
    y1 = max(c['front_outer_y'] for c in cab) + 60
    a_c = shift_anchors(dict(cabins=cab, cabin_centres=a_pg['cabin_centres']), x0, y0)
    add('plan_ground_cabins.png', rgba[y0:y1, x0:x1].copy(), v,
        'Tight crop of the ground-floor plan: the row of 4 private cabins (curved shells, round '
        'banquettes, tables, chairs) between the corridor wall and their curved fronts.',
        dict(offset_in_plan_ground=[x0, y0], **a_c),
        extra_src=dict(crop_of='assets/lines/plan_ground.png', crop_box=[x0, y0, x1, y1]))
    vc = a_pg['void_circle']
    m = int(vc['r'] + 90)
    x0, y0 = int(vc['cx'] - m), int(vc['cy'] - m)
    x1, y1 = int(vc['cx'] + m), int(vc['cy'] + m)
    add('plan_ground_void.png', rgba[y0:y1, x0:x1].copy(), v,
        'Tight crop of the ground-floor plan around the open void: dashed void circle with the '
        'tree-canopy symbol and OPEN VOID label (square, void centred).',
        dict(offset_in_plan_ground=[x0, y0],
             **shift_anchors(dict(void_circle=vc, tree_canopy=a_pg['tree_canopy']), x0, y0)),
        extra_src=dict(crop_of='assets/lines/plan_ground.png', crop_box=[x0, y0, x1, y1]))
    del rgba, v
    v = render_view('PF', True, use_cache=use_cache)
    a_pf = measure_plan_first(v.gray)
    a_pf['tree_canopy'] = tree_canopy(v.gray, a_pf['void_circle'])
    add('plan_first.png', ink_rgba(v.gray), v,
        'PROPOSED FIRST FLOOR plan only: toilets, 3 first-floor cabins with planters, dining, round '
        'banquettes, bar, the void ring (OPEN BELLOW) with tree canopy, stairs. Markers/title removed.',
        a_pf)
    del v

    _PAGE_CACHE.clear()
    # ---- axo -----------------------------------------------------------------------------------
    v = render_view('AXO', True, use_cache=use_cache)
    tree = measure_layer_extent(v, 'CAY')
    a_axo = dict(tree_bbox=tree['bbox'], tree_base=tree['base'],
                 note='tree measured on a render of its CAD layer (CAY) alone; base = foot of trunk')
    add('axo_exploded.png', ink_rgba(v.gray), v,
        'EXPLODED AXONOMETRIC: roof slab with round skylight drum, peeled-off walls, both stair '
        'flights, ground floor grid with the cabin shells, bar and the tree. Grey wall faces become '
        'a translucent ink wash (alpha ~0.38). Sheet frame/title block removed.', a_axo)
    del v

    with open(os.path.join(OUT, 'index.json'), 'w') as fh:
        json.dump(index, fh, indent=1)
    print('  index.json', len(A), 'assets', flush=True)
    if contact:
        contact_sheet(index)
    return index


# =========================================================================== #
# 8. contact sheet
# =========================================================================== #

def _font(size, style='Regular'):
    for p in (os.path.join(ROOT, 'assets', 'fonts', f'IBMPlexMono-{style}.ttf'),
              '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _serif(size):
    p = os.path.join(ROOT, 'assets', 'fonts', 'CormorantGaramond-Italic.ttf')
    return ImageFont.truetype(p, size) if os.path.exists(p) else _font(size)


def linen_paper(h, w, seed=7, color=LINEN, strip=1024):
    """Warm linen paper (uint8 RGB): base colour + fine horizontal/vertical fibre grain + soft
    mottling.  Generated in row strips to bound memory."""
    rng = np.random.default_rng(seed)
    base = np.array(_hex(color), np.float32)
    mott = cv2.resize(rng.standard_normal((h // 160 + 2, w // 160 + 2)).astype(np.float32), (w, h),
                      interpolation=cv2.INTER_CUBIC)
    out = np.empty((h, w, 3), np.uint8)
    pad = 16
    for y0 in range(0, h, strip):
        y1 = min(h, y0 + strip)
        a0, a1 = max(0, y0 - pad), min(h, y1 + pad)
        n1 = cv2.GaussianBlur(rng.standard_normal((a1 - a0, w)).astype(np.float32), (0, 0), sigmaX=4.0, sigmaY=0.6)
        n2 = cv2.GaussianBlur(rng.standard_normal((a1 - a0, w)).astype(np.float32), (0, 0), sigmaX=0.6, sigmaY=3.0)
        n1 = n1[y0 - a0:y0 - a0 + (y1 - y0)] / 0.187   # unit std (measured for these sigmas)
        n2 = n2[y0 - a0:y0 - a0 + (y1 - y0)] / 0.217
        lum = 1 + 0.011 * n1 + 0.007 * n2 + 0.006 * mott[y0:y1]
        out[y0:y1] = np.clip(base[None, None] * lum[..., None], 0, 255).astype(np.uint8)
    return out


def _comp(dst, rgba, x, y, alpha_scale=1.0):
    """Composite uint8 straight-alpha RGBA onto a uint8 RGB canvas at (x, y) (region-wise)."""
    h, w = rgba.shape[:2]
    a = rgba[..., 3:4].astype(np.float32) / 255.0 * alpha_scale
    reg = dst[y:y + h, x:x + w].astype(np.float32)
    dst[y:y + h, x:x + w] = np.clip(rgba[..., :3].astype(np.float32) * a + reg * (1 - a) + 0.5,
                                    0, 255).astype(np.uint8)


def _thumb(rgba, scale):
    """Alpha-correct downscale of flat-colour ink (resizes premultiplied colour + alpha)."""
    h, w = rgba.shape[:2]
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    a = rgba[..., 3]
    at = cv2.resize(a, size, interpolation=cv2.INTER_AREA)
    out = np.empty((size[1], size[0], 4), np.uint8)
    out[..., :3] = rgba[0, 0, :3]
    out[..., 3] = at
    return out


def _anchor_marks(entry, scale, w, h):
    """Draw primitives (lines/points/circles) for an index entry's anchors, in thumbnail px."""
    prims = []

    def walk(o, key=''):
        if isinstance(o, dict):
            if 'cx' in o and 'cy' in o and 'r' in o:
                prims.append(('circle', o['cx'] * scale, o['cy'] * scale, o['r'] * scale))
            for k, v in o.items():
                if k in ('split', 'wall_bands_x', 'first_slab_openings_x', 'rail_lines_y',
                         'pendant_shade_bbox', 'cabin_joints_x', 'cabins', 'offset_in_section_BB',
                         'offset_in_plan_ground', 'section_AA_origin_in_this_file',
                         'elev02_cabins_origin_in_this_file', 'plan_outer', 'pendant_cord_x',
                         'opening_x', 'cell_x', 'back_wall_x', 'opening_top_y', 'wall_left_x',
                         'wall_right_x', 'back_wall_inner_y', 'back_wall_outer_y', 'front_outer_y',
                         'trunk_mid_height_x'):
                    if k == 'cabins':
                        for c in v:
                            if 'centre' in c:
                                prims.append(('point', c['centre'][0] * scale, c['centre'][1] * scale))
                    continue
                walk(v, k)
        elif isinstance(o, list):
            if key.endswith('bbox') and len(o) == 4:
                prims.append(('rect', *[t * scale for t in o]))
            elif key in ('stools', 'tree_base'):
                if key == 'tree_base':
                    o = [o]
                for p in o:
                    prims.append(('point', p[0] * scale, p[1] * scale))
            elif key.endswith('_x') and all(isinstance(t, (int, float)) for t in o):
                for t in o:
                    prims.append(('vline', t * scale))
        elif isinstance(o, (int, float)) and not isinstance(o, bool):
            if key.endswith('_x'):
                prims.append(('vline', o * scale))
            elif key.endswith('_y'):
                prims.append(('hline', o * scale))
    walk(entry.get('anchors', {}))
    return prims


def contact_sheet(index, path=CONTACT, width=5200):
    """All outputs on linen paper, labelled, with their measured registration anchors as thin
    terracotta marks, plus 100 % crops (hairline crispness) and a stylisation strip."""
    t_lbl = _font(30); t_sml = _font(24, 'Light'); t_hdr = _serif(84); t_mono = _font(34, 'Medium')
    M, G, LBL = 90, 60, 96
    entries = {os.path.basename(e['path']): e for e in index['assets']}
    rows = [['section_AA.png', 'section_AA_full.png'],
            ['section_BB.png'],
            ['section_BB_left.png', 'section_BB_right.png'],
            ['elev02_cabins.png', 'elev02_full.png'],
            ['elev01_bar.png', 'elev04_partyhall.png', 'plan_ground_cabins.png', 'plan_ground_void.png'],
            ['plan_ground.png', 'plan_first.png']]
    avail = width - 2 * M
    layout, y = [], 260
    for row in rows:
        ar = [entries[n]['size'][0] / entries[n]['size'][1] for n in row]
        hgt = min((avail - G * (len(row) - 1)) / sum(ar), 1250)
        x = M
        for n, a in zip(row, ar):
            w_ = int(round(hgt * a))
            layout.append((n, x, y, w_, int(round(hgt))))
            x += w_ + G
        y += int(round(hgt)) + LBL + G
    # last block: the axo on the left, 100 % crops + stylisation strip in a grid on its right
    axo = entries['axo_exploded.png']
    cs = 600
    ncol = 4
    grid_w = ncol * cs + (ncol - 1) * G
    axo_w = avail - grid_w - 2 * G
    axo_h = int(round(axo_w * axo['size'][1] / axo['size'][0]))
    layout.append(('axo_exploded.png', M, y + 70, axo_w, axo_h))
    gx = M + axo_w + 2 * G
    # tree of the axo: bbox of the CAY (tree) layer on page 4, mapped into the asset's px
    _, it4 = page_items(4)
    tb = np.array([it.bbox for it in it4 if it.layer == 'CAY'])
    org = axo['source']['origin_pt']
    tcx = pt2px((tb[:, 0].min() + tb[:, 2].max()) / 2 - org[0])
    tcy = pt2px((tb[:, 1].min() + tb[:, 3].max()) / 2 - org[1])
    crops = [('section_AA.png', 150, 300, 'drapery swags'),
             ('section_AA.png', 3300, 2950, 'brick + pendant hairlines'),
             ('elev02_cabins.png', 520, 760, 'pendant + fluting'),
             ('plan_ground.png', 860, 700, 'cabin banquette'),
             ('section_BB_right.png', None, None, 'rail + canopy'),
             ('axo_exploded.png', int(tcx - cs / 2), int(tcy - cs * 0.62), 'axo tree'),
             ('plan_first.png', None, None, 'void ring + canopy'),
             ('section_BB_left.png', 1300, 2350, 'party-hall curtain')]
    crop_y = y + 70 + 70
    crop_rows = -(-len(crops) // ncol)
    sty_y = crop_y + crop_rows * (cs + LBL + G) + 70
    H = max(sty_y + 2 * (cs + LBL + G), y + 70 + axo_h + LBL) + M
    arr = linen_paper(H, width)
    terr = (194, 96, 46)
    draw_queue = []
    for n, x, y_, w_, h_ in layout:
        e = entries[n]
        im = np.asarray(Image.open(os.path.join(ROOT, e['path'])))
        sc = w_ / im.shape[1]
        th = _thumb(im, sc)
        del im
        _comp(arr, th[:h_, :w_], x, y_)
        draw_queue.append((n, x, y_, th.shape[1], th.shape[0], sc, e))
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img, 'RGBA')
    d.text((M, 70), 'linework', font=t_hdr, fill=_hex(INK))
    d.text((M + 330, 108), "CLIENT DRAWINGS AS INK  ·  VECTOR PDF -> 600 DPI RGBA  ·  ANNOTATIONS REMOVED IN THE "
           "CONTENT STREAM  ·  TERRACOTTA = MEASURED ANCHORS (index.json)", font=t_sml, fill=_hex(INK))
    for n, x, y_, w_, h_, sc, e in draw_queue:
        d.rectangle([x - 1, y_ - 1, x + w_, y_ + h_], outline=(43, 36, 32, 40))
        for p in _anchor_marks(e, sc, w_, h_):
            if p[0] == 'vline':
                d.line([(x + p[1], y_), (x + p[1], y_ + h_)], fill=terr + (150,), width=1)
            elif p[0] == 'hline':
                d.line([(x, y_ + p[1]), (x + w_, y_ + p[1])], fill=terr + (150,), width=1)
            elif p[0] == 'point':
                cx, cy = x + p[1], y_ + p[2]
                d.line([(cx - 9, cy), (cx + 9, cy)], fill=terr + (255,), width=2)
                d.line([(cx, cy - 9), (cx, cy + 9)], fill=terr + (255,), width=2)
            elif p[0] == 'circle':
                cx, cy, r = x + p[1], y_ + p[2], p[3]
                d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=terr + (220,), width=2)
                d.line([(cx - 9, cy), (cx + 9, cy)], fill=terr + (255,), width=2)
                d.line([(cx, cy - 9), (cx, cy + 9)], fill=terr + (255,), width=2)
            elif p[0] == 'rect':
                d.rectangle([x + p[1], y_ + p[2], x + p[3], y_ + p[4]], outline=terr + (220,), width=2)
        sz = e['size']
        d.text((x, y_ + h_ + 16), n, font=t_mono, fill=_hex(INK))
        d.text((x, y_ + h_ + 58), f"{sz[0]} x {sz[1]} px  ·  600 dpi", font=t_sml, fill=(43, 36, 32, 200))
    # 100 % crops
    d.text((gx, crop_y - 58), '100 % CROPS AT 600 DPI (1 asset px = 1 sheet px)', font=t_lbl,
           fill=_hex(INK))
    arr = np.array(img)
    boxes = []
    for i, (n, cx0, cy0, lab) in enumerate(crops):
        e = entries[n]
        im = np.asarray(Image.open(os.path.join(ROOT, e['path'])))
        if cx0 is None:     # windows placed on measured anchors
            if n.startswith('section_BB_right'):
                tx = e['anchors']['trunk_at_ffl_first_x']; ty = e['anchors']['rail_top_y']
                cx0, cy0 = int(tx - cs / 2), int(ty - 120)
            else:
                vc = e['anchors']['void_circle']
                cx0, cy0 = int(vc['cx'] - vc['r'] * 0.55 - cs / 2), int(vc['cy'] - vc['r'] * 0.55 - cs / 2)
        c = im[cy0:cy0 + cs, cx0:cx0 + cs]
        del im
        col, row = i % ncol, i // ncol
        x = gx + col * (cs + G); y_ = crop_y + row * (cs + LBL + G)
        _comp(arr, c, x, y_)
        boxes.append((x, y_, c.shape[1], c.shape[0], f'{n}  @ {cx0},{cy0}', lab))
    # stylisation strip (elev02 pendant detail)
    e = entries['elev02_cabins.png']
    im = np.asarray(Image.open(os.path.join(ROOT, e['path'])))
    base = im[760:760 + cs, 450:450 + cs].copy()
    del im
    sty = [(base, 'ink_rgba (gamma 0.72)'), (thicken(base, 1.5), 'thicken(px=1.5)'),
           (hand_wobble(base, 2.0, seed=4, pressure=0.2), 'hand_wobble(2.0, pressure=.2)'),
           (recolor(base, '#A9502F'), "recolor('#A9502F')"),
           (recolor(thicken(hand_wobble(base, 1.5, seed=9), 0.8), '#6B2430'), 'wobble+thicken+oxblood')]
    for i, (s_, lab) in enumerate(sty):
        x = gx + (i % ncol) * (cs + G); y_ = sty_y + (i // ncol) * (cs + LBL + G)
        _comp(arr, s_, x, y_)
        boxes.append((x, y_, s_.shape[1], s_.shape[0], 'stylisation', lab))
    img = Image.fromarray(arr)
    del arr
    d = ImageDraw.Draw(img, 'RGBA')
    d.text((gx, sty_y - 58), 'STYLISATION FUNCTIONS (100 %)', font=t_lbl, fill=_hex(INK))
    for x, y_, w_, h_, t1, t2 in boxes:
        d.rectangle([x - 1, y_ - 1, x + w_, y_ + h_], outline=(43, 36, 32, 70))
        d.text((x, y_ + h_ + 14), t2, font=t_lbl, fill=_hex(INK))
        d.text((x, y_ + h_ + 54), t1, font=t_sml, fill=(43, 36, 32, 190))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, quality=90, subsampling=0)
    s = 1600 / max(img.size)
    img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS).save(
        os.path.join(PREVIEW, 'contact_preview.jpg'), quality=90)
    print('  contact sheet', path, img.size, flush=True)
    return path


if __name__ == '__main__':
    build()
