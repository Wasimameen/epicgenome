"""collage_common — shared builder for the two A3 atmosphere collages.

Wraps a psdkit Document with helpers that keep every layer named, grouped and
non-destructive:
  * photos keep their pixels behind layer masks (cut-outs use the ORIGINAL photo
    pixels + the cut-out alpha as a layer mask, so edges can be refined);
  * colour washes / silhouettes are Solid Color fill layers with masks (recolourable);
  * shadows and glows are separate layers;
  * every piece of type is a raster layer (pixel-exact everywhere) with a hidden,
    editable Photoshop type layer directly above it ('EDIT · …');
  * each annotation lives in its own sub-group with its paper tag and shadow.
"""
from __future__ import annotations

import json
import os
import numpy as np
import cv2

import psdkit
from psdkit import Document, Group, Pixel, Fill, Mask, Text
from lib import compose as C
from lib import typeset as T
from lib import sensory as S

W, H = C.W, C.H
INK = '#2B2420'
PAL = S.PAL
MARGIN = 168                        # left / right page margin
LIGHT = (0.75, 1.0)                 # one light direction for every cast shadow (dx, dy per unit depth)

# Photoshop PostScript names of the shipped fonts (assets/fonts)
PS_FONT = {
    'italic': 'CormorantGaramond-Italic', 'cg-400i': 'CormorantGaramond-Italic',
    'italic-medium': 'CormorantGaramond-MediumItalic', 'cg-500i': 'CormorantGaramond-MediumItalic',
    'italic-light': 'CormorantGaramond-LightItalic', 'cg-300i': 'CormorantGaramond-LightItalic',
    'serif': 'CormorantGaramond-Regular', 'cg-400': 'CormorantGaramond-Regular',
    'serif-semibold': 'CormorantGaramond-SemiBold', 'cg-600': 'CormorantGaramond-SemiBold',
    'mono': 'IBMPlexMono-Regular', 'plex-400': 'IBMPlexMono-Regular',
    'mono-light': 'IBMPlexMono-Light', 'plex-300': 'IBMPlexMono-Light',
    'mono-medium': 'IBMPlexMono-Medium', 'plex-500': 'IBMPlexMono-Medium',
}

# type scale shared by both sheets (px at 300 ppi; mono caps >= 19 px = 1.6 mm)
LABEL = 27          # mono labels
HERO = 50           # one hero phrase per sheet
PHRASE = 42         # standard phrases
SUB = 28            # mono sublines / headings
FOOT = 3418         # shared footer baseline: title subline, last swatch labels, key-plan labels (90 px margin)
HEAD = 3040         # shared footer top baseline: kicker and legend headings


def asset(*parts):
    return C.P('assets', *parts)


def have(*parts):
    return os.path.exists(asset(*parts))


_CUT_INDEX = None


def cut_info(name):
    """index.json record of an assets/cut cut-out."""
    global _CUT_INDEX
    if _CUT_INDEX is None:
        d = json.load(open(asset('cut', 'index.json')))
        items = d.get('files') or d.get('assets') or d
        _CUT_INDEX = {os.path.basename(it['path']): it for it in items if isinstance(it, dict) and 'path' in it}
    return _CUT_INDEX[name]


def shadow_offset(depth):
    return int(round(LIGHT[0] * depth)), int(round(LIGHT[1] * depth))


class TagBox(tuple):
    """(x0, y0, x1, y1) of a tag / card, plus .group: put its leaders and extras in the same group so the
    annotation moves as one."""
    def __new__(cls, box, group):
        t = super().__new__(cls, tuple(int(round(v)) for v in box))
        t.group = group
        return t


class Builder:
    def __init__(self, title):
        self.doc = Document(W, H, 300, title)

    # ------------------------------------------------------------------ groups
    def group(self, name, label=None, parent=None, opened=False):
        g = Group(name, label=label, opened=opened)
        (parent or self.doc.root).add(g)
        return g

    # ------------------------------------------------------------------ pixels
    def px(self, g, name, img, x, y, **kw):
        """Add a pixel layer (float RGBA) at canvas (x, y); cropped to the canvas."""
        layer = C.pixel(name, img, int(round(x)), int(round(y)), **kw)
        g.add(layer)
        return layer

    def gen(self, g, name, out, **kw):
        """Add a sensory generator result ``(rgba, (x, y))``."""
        rgba, (x, y) = out
        return self.px(g, name, rgba, x, y, **kw)

    def photo(self, g, name, img, x, y, mask_alpha=None, mask_xy=None, margin=None, **kw):
        """Photo pixel layer with an optional layer mask (full-canvas or local at mask_xy).
        With ``margin`` the photo is trimmed to the mask extent + margin px of spare image."""
        mask = None
        x, y = int(round(x)), int(round(y))
        if mask_alpha is not None:
            if mask_xy is None:
                mask = C.canvas_mask(name, mask_alpha)
            else:
                mask = C.mask_for(mask_alpha, mask_xy[0], mask_xy[1])
            if margin is not None:
                mx0, my0, mx1, my1 = mask.bounds
                cx0 = max(0, mx0 - margin - x)
                cy0 = max(0, my0 - margin - y)
                cx1 = min(img.shape[1], mx1 + margin - x)
                cy1 = min(img.shape[0], my1 + margin - y)
                img = img[cy0:cy1, cx0:cx1]
                x, y = x + cx0, y + cy0
        layer = C.pixel(name, img, x, y, mask=mask, **kw)
        g.add(layer)
        return layer

    def fill(self, g, name, color, alpha=None, **kw):
        layer = C.fill(name, color, alpha, **kw)
        g.add(layer)
        return layer

    def fill_local(self, g, name, color, alpha, x, y, **kw):
        """Solid Color fill whose mask is a local alpha placed at (x, y)."""
        layer = Fill(name, color, mask=C.mask_for(alpha, int(round(x)), int(round(y))), **kw)
        g.add(layer)
        return layer

    def shadow(self, g, name, alpha, x, y, depth=36, sigma=None, opacity=0.42, color=INK, dx=None, dy=None):
        """Cast shadow from a local alpha placed at (x, y); offset follows the page light."""
        ox, oy = shadow_offset(depth)
        dx = ox if dx is None else dx
        dy = oy if dy is None else dy
        sigma = sigma if sigma is not None else max(8.0, depth * 0.9)
        layer = C.shadow(name, alpha, int(round(x)), int(round(y)), dx, dy, sigma, opacity, color)
        g.add(layer)
        return layer

    # ------------------------------------------------------------------ cut-outs
    def cutout(self, g, name, cut_name, scale, x, y, margin=40, flat_color=None, alpha_fn=None, **kw):
        """Non-destructive cut-out: the ORIGINAL photo pixels (cut-out box + margin) with the
        cut-out alpha as a layer mask.  ``flat_color`` makes it a recolourable Solid Color
        silhouette instead.  Returns (layer, (x, y, w, h)) of the visible cut-out at canvas scale."""
        info = cut_info(cut_name)
        cut = C.load(os.path.join('assets', 'cut', cut_name))
        alpha = cut[..., 3]
        if alpha_fn is not None:
            alpha = alpha_fn(alpha)
        sx0, sy0, sx1, sy1 = info['src_box']
        a_s = C.resize(alpha, scale)
        h, w = a_s.shape
        if flat_color is not None:
            layer = Fill(name, flat_color, mask=C.mask_for(a_s, int(round(x)), int(round(y))), **kw)
            g.add(layer)
            return layer, (x, y, w, h)
        src = info['source']
        if src.startswith('skimage'):
            from skimage import data as skd
            full = skd.coffee().astype(np.float32) / 255.0
        else:
            full = C.load(src, 'RGB')
        m = margin
        bx0, by0 = max(0, sx0 - m), max(0, sy0 - m)
        bx1, by1 = min(full.shape[1], sx1 + m), min(full.shape[0], sy1 + m)
        rgb = full[by0:by1, bx0:bx1]
        del full
        rgb = C.resize(rgb, scale)
        ox, oy = (sx0 - bx0) * scale, (sy0 - by0) * scale
        layer = C.pixel(name, rgb, int(round(x - ox)), int(round(y - oy)),
                        mask=C.mask_for(a_s, int(round(x)), int(round(y))), **kw)
        g.add(layer)
        return layer, (x, y, w, h)

    # ------------------------------------------------------------------ type
    def _live(self, g, name, text, font, size, x, y, color, tracking=0, leading=None, justification='left',
              angle=0.0):
        g.add(Text(name, text, PS_FONT.get(font, font), size, x, y, color=color, tracking=tracking,
                   leading=leading, justification=justification, angle=angle))

    def text(self, g, text, font, size, x, y, anchor='baseline_left', color=INK, name=None,
             opacity=1.0, blend='normal', live=True, **kw):
        rgba, meta = T.text_rgba(text, font, size, color=color, **kw)
        px, py = T.place(meta, x, y, anchor)
        nm = (name or ('TXT · ' + text.replace('\n', ' / ')))[:90]
        self.px(g, nm, rgba, px, py, opacity=opacity, blend=blend)
        if live:
            # the alignment origin (left end / centre / right end of the first baseline, rotated with
            # the text) so the live twin re-flows exactly like the raster when retyped
            ox, oy = meta['anchors']['origin']
            self._live(g, 'EDIT · ' + nm[6:] if nm.startswith(('TXT · ', 'TXT - ')) else 'EDIT · ' + nm, text, font, size,
                       px + ox, py + oy, color, kw.get('tracking', 0),
                       size * kw.get('leading', 1.2) if '\n' in text else None,
                       justification=kw.get('align', 'left'), angle=kw.get('angle', 0.0))
        return meta, (px, py)

    def _label_block(self, g, label, phrase, x, y, color, label_color, label_size, phrase_size, short):
        rgba, meta = T.label_block(label, phrase, color=color, label_color=label_color,
                                   label_size=label_size, phrase_size=phrase_size)
        return rgba, meta

    def _block_layers(self, g, rgba, meta, tx, ty, label, phrase, color, label_color, label_size, phrase_size):
        short = label.replace(' · ', ' ')
        self.px(g, f'TXT · {short}', rgba, tx, ty)
        la = meta['anchors']['label_baseline']
        pa = meta['anchors']['phrase_baseline']
        self._live(g, f'EDIT · {short} label', label, 'mono', label_size, tx + la[0], ty + la[1], label_color,
                   tracking=110)
        self._live(g, f'EDIT · {short} phrase', phrase, 'italic', phrase_size, tx + pa[0], ty + pa[1], color,
                   leading=phrase_size * 1.12 if '\n' in phrase else None)

    def tag(self, parent, label, phrase, x, y, hero=False, pad=(36, 28), paper='#F4EEE2', color=INK,
            label_color='#A9502F', shadow=0.38, depth=14):
        """A linen paper tag (own shadow) carrying a mono label + italic phrase, in its own group.
        (x, y) is the tag's top-left.  Returns the tag box (x0, y0, x1, y1)."""
        ps = HERO if hero else PHRASE
        g = Group(f'Tag · {label}', opened=False)
        parent.add(g)
        rgba, meta = T.label_block(label, phrase, color=color, label_color=label_color, label_size=LABEL,
                                   phrase_size=ps)
        ix0, iy0, ix1, iy1 = meta['ink_box']
        pw = int(round(ix1 - ix0 + 2 * pad[0]))
        ph = int(round(iy1 - iy0 + 2 * pad[1]))
        tagimg = _paper_tag(ph, pw, paper, seed=len(phrase) * 7 + len(label))
        if shadow:
            self.shadow(g, f'Shadow · tag {label}', np.ones((ph, pw), np.float32), x, y, depth=depth,
                        opacity=shadow)
        self.px(g, f'Paper · tag {label}', tagimg, x, y)
        self._block_layers(g, rgba, meta, x + pad[0] - ix0, y + pad[1] - iy0, label, phrase, color, label_color,
                           LABEL, ps)
        return TagBox((x, y, x + pw, y + ph), g)

    def card(self, parent, name, entries, x, y, pad=(40, 32), gap=30, paper='#F4EEE2', color=INK,
             label_color='#A9502F', shadow=0.38, depth=14):
        """One paper card carrying several stacked (label, phrase) annotations, in its own group."""
        g = Group(f'Card · {name}', opened=False)
        parent.add(g)
        blocks = [T.label_block(lab, ph, color=color, label_color=label_color, label_size=LABEL,
                                phrase_size=PHRASE) for lab, ph in entries]
        boxes = [m['ink_box'] for _, m in blocks]
        width = max(b[2] - b[0] for b in boxes)
        height = sum(b[3] - b[1] for b in boxes) + gap * (len(blocks) - 1)
        pw, ph = int(round(width + 2 * pad[0])), int(round(height + 2 * pad[1]))
        if shadow:
            self.shadow(g, f'Shadow · card {name}', np.ones((ph, pw), np.float32), x, y, depth=depth,
                        opacity=shadow)
        self.px(g, f'Paper · card {name}', _paper_tag(ph, pw, paper, seed=pw + len(entries)), x, y)
        cy = y + pad[1]
        for (rgba, meta), (lab, phr), b in zip(blocks, entries, boxes):
            self._block_layers(g, rgba, meta, x + pad[0] - b[0], cy - b[1], lab, phr, color, label_color,
                               LABEL, PHRASE)
            cy += (b[3] - b[1]) + gap
        return TagBox((x, y, x + pw, y + ph), g)

    def leader(self, g, name, points, width=2.2, color=INK, opacity=0.9, **kw):
        rgba, (x, y) = T.leader(points, width=width, color=color, **kw)
        return self.px(g, name, rgba, x, y, opacity=opacity)

    # ------------------------------------------------------------------ page furniture
    def title_block(self, parent, kicker, lines, subline):
        """Shared title grid: kicker baseline 3040, title baselines 3192 (+142 per line), subline on FOOT."""
        g = Group('Title block', opened=False)
        parent.add(g)
        self.text(g, kicker, 'mono', SUB, MARGIN, 3040, tracking=140, color=PAL['terracotta'],
                  name='TXT · kicker')
        yb = 3192
        for i, ln in enumerate(lines):
            self.text(g, ln, 'italic', 150, MARGIN - 6, yb, name=f'TXT · title line {i + 1}')
            yb += 142
        self.text(g, subline, 'mono-light', SUB, MARGIN, FOOT, tracking=100, name='TXT · subline')
        return g

    def legend(self, parent, sheet, swatches):
        """Shared legend at the bottom right: palette + materials grid and the key plan.
        Creates its own top-level-style group '95 · Legend …' inside `parent` (pass B.doc.root).

        sheet: '01' (void) or '02' (cabins) — both chosen areas are tinted on the
        same full ground-floor key plan; the active one carries the view cone."""
        g = Group('95 · Legend — key plan & palette', label='violet', opened=False)
        parent.add(g)
        # ---- swatch grid (2 rows x 4): colours on top, materials below; row-2 labels sit on FOOT
        gx0, pitch, row = 3150, 236, 190
        chip_h, gap = 70, 14
        cap = T.text_rgba('H', 'mono', LABEL)[1]['cap_height']
        gy1 = FOOT - chip_h - gap - cap                      # top of row 2
        gy0 = gy1 - row
        self.text(g, 'PALETTE  &  MATERIALS', 'mono', LABEL, gx0, HEAD, tracking=120,
                  name='TXT · legend heading palette')
        cw_ = 150
        rim, _ = T.stroke_polyline(np.array([[0, 0], [cw_, 0], [cw_, chip_h], [0, chip_h]], float) + 3, 1.2,
                                   closed=True, box=(0, 0, cw_ + 6, chip_h + 6))
        for i, (kind, val, lab) in enumerate(swatches):
            cx = gx0 + (i % 4) * pitch
            cy = (gy0, gy1)[i // 4]
            sg = Group(f'Swatch · {lab.lower()}', opened=False)
            g.add(sg)
            if kind == 'colour':        # a Solid Color fill: double-click to change the palette colour
                self.fill_local(sg, f'Chip · {lab.lower()} {PAL.get(val, val)}', PAL.get(val, val),
                                np.ones((chip_h, cw_), np.float32), cx, cy)
            else:
                self.px(sg, f'Chip · {lab.lower()} (material)', C.cover(C.load(f'assets/mat/{val}.png', 'RGB'), cw_,
                                                                       chip_h), cx, cy)
            self.px(sg, f'Chip rim · {lab.lower()}', colour_rgba(rim * 0.55, INK), cx - 3, cy - 3)
            self.text(sg, lab.upper(), 'mono', LABEL, cx, cy + chip_h + gap + cap, tracking=110,
                      name=f'TXT · swatch {lab.lower()}')
        # ---- key plan (full ground floor, label-free client drawing); its labels sit on FOOT
        plan = C.load('assets/lines/plan_ground_notext.png')
        ps = 0.088
        pc = C.resize(LW_thicken(plan, 0.6), ps)
        del plan
        kx = W - MARGIN - pc.shape[1]
        ky = int(FOOT - 56 - pc.shape[0])
        self.text(g, 'KEY PLAN — GROUND FLOOR', 'mono', LABEL, kx, HEAD, tracking=120,
                  name='TXT · legend heading key plan')
        kp = Group('Key plan · ground floor', opened=False)
        g.add(kp)
        self.px(kp, 'Key plan · ground floor (client)', pc, kx, ky, locked=True)

        def P_(x, y):
            return kx + x * ps, ky + y * ps

        void = P_(4948.8, 1607.9)
        cabins = [P_(cx, 1124.1) for cx in (1163.3, 1865.3, 2566.4, 3249.3)]
        a, hx, hy = local(C.ellipse_mask(void[0], void[1], 500 * ps, 500 * ps))
        self.fill_local(kp, 'Key plan · 01 the void (tint)', PAL['canopy'], a, hx, hy, blend='multiply',
                        opacity=0.75 if sheet == '01' else 0.35)
        cab = np.zeros((H, W), np.float32)
        for c in cabins:
            cab = np.maximum(cab, C.ellipse_mask(c[0], c[1] - 8, 300 * ps, 300 * ps))
        a, hx, hy = local(cab)
        self.fill_local(kp, 'Key plan · 02 the cabins (tint)', PAL['terracotta'], a, hx, hy, blend='multiply',
                        opacity=0.75 if sheet == '02' else 0.35)
        if sheet == '01':
            cone = S.view_cone(apex=void, direction=-4, fov=64, length=(6650 - 4948.8) * ps + 10,
                               color=PAL['terracotta'], fill=0.25, apex_dot=5, apex_ring=10, arc_dash=(6.0, 6.0),
                               arc_width=2.2)
        else:
            apex = P_(2200, 2330)
            cone = S.view_cone(apex=apex, direction=94, fov=104, length=(2330 - 1180) * ps,
                               color=PAL['terracotta'], fill=0.25, apex_dot=5, apex_ring=10, arc_dash=(6.0, 6.0),
                               arc_width=2.2)
        self.gen(kp, 'Key plan · view cone (this sheet)', cone)
        # north point: right end of the heading line, above the plan's top-right corner ('N' is live type)
        nx, ny, nsz = W - MARGIN - 30, HEAD - 8, 60
        self.gen(kp, 'Key plan · north point', S.north_arrow(at=(nx, ny), size=nsz, label=None))
        self.text(kp, 'N', 'mono', LABEL, nx, ny - nsz / 2 * 1.18 - LABEL * 1.05 + cap / 2, anchor='origin',
                  align='center', name='TXT · north point N')
        # own labels under the plan (client labels removed), on the footer baseline
        yb = FOOT
        self.text(kp, '01 VOID', 'mono', LABEL, void[0] - 60, yb, tracking=100, name='TXT · key plan label void',
                  color=INK if sheet == '01' else '#6E655D')
        self.text(kp, '02 CABINS', 'mono', LABEL, cabins[0][0] - 46, yb, tracking=100,
                  name='TXT · key plan label cabins', color=INK if sheet == '02' else '#6E655D')
        self.leader(kp, 'Leader · key plan void', [(void[0], yb - 30), (void[0], void[1] + 500 * ps + 6)],
                    width=1.6, dot_at_end=False, opacity=0.7)
        self.leader(kp, 'Leader · key plan cabins', [(cabins[0][0], yb - 30), (cabins[0][0], cabins[0][1] + 300 * ps + 4)],
                    width=1.6, dot_at_end=False, opacity=0.7)
        return g

    def readme(self, sheet_title, sources='- Client drawings (RESTAURANT.pdf); photographs generated for this project (FLUX via ElevenLabs).'):
        """Hidden top group explaining how the file is built.  `sources` lists this sheet's own sources."""
        fonts = sorted({n.font for n in self.doc.root.iter_layers() if getattr(n, 'kind', '') == 'text'})
        txt = README_TEXT.format(title=sheet_title, fonts=', '.join(fonts), sources=sources.strip('\n'))
        rgba, meta = T.text_rgba(txt, 'mono', 30, color=INK, leading=1.45, max_width=2600)
        h, w = rgba.shape[:2]
        bg = C.solid(h + 160, w + 160, '#F7F2E8')
        bg[80:80 + h, 80:80 + w, :3] = rgba[..., :3] * rgba[..., 3:4] + bg[80:80 + h, 80:80 + w, :3] * (1 - rgba[..., 3:4])
        g = Group('!! READ ME — how this file is built', hidden=True, opened=False)
        self.doc.root.add(g)
        g.add(C.pixel('READ ME · notes (hide group to view)', bg, 300, 300))
        return g


def terrazzo_mosaic(cache_path, Wm=3600, Hm=1900, tile_scale=0.32, n=150, seed=23):
    """Aperiodic terrazzo plate (float RGBA): the seamless tile texture-bombed into Voronoi cells (random
    offset + dihedral turn per cell, 2 px soft seams), so no repeat shows once perspective-warped.
    Cached at cache_path (8-bit RGBA PNG)."""
    if os.path.exists(cache_path):
        return C.load(cache_path)
    from scipy.spatial import cKDTree
    tile = C.resize(C.load('assets/mat/terrazzo_cream.png', 'RGB'), tile_scale)
    T_ = tile.shape[0]
    variants = [tile, np.rot90(tile, 1), np.rot90(tile, 2), np.rot90(tile, 3),
                tile[:, ::-1], np.rot90(tile[:, ::-1], 1), tile[::-1], np.rot90(tile[::-1], 1)]
    variants = [np.ascontiguousarray(v) for v in variants]
    rng = np.random.default_rng(seed)
    seeds = np.stack([rng.uniform(-200, Wm + 200, n), rng.uniform(-200, Hm + 200, n)], 1)
    yy, xx = np.mgrid[0:Hm, 0:Wm]
    pts = np.stack([xx.ravel(), yy.ravel()], 1).astype(np.float32)
    d, idx = cKDTree(seeds).query(pts, k=2)
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
        ys, xs = np.nonzero(np.isin(idx0, cells))
        cid = idx0[ys, xs]
        out[ys, xs] = variants[v][(ys + offy[cid]) % T_, (xs + offx[cid]) % T_]
    bl = cv2.GaussianBlur(out, (0, 0), 1.2)
    k = np.clip(seam / 3.0, 0, 1)
    k = (k * k * (3 - 2 * k))[..., None]
    out = out * k + bl * (1 - k)
    rgba = np.dstack([out, np.ones((Hm, Wm), np.float32)])
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    from PIL import Image
    Image.fromarray(np.clip(np.floor(rgba * 255 + 0.5), 0, 255).astype(np.uint8), 'RGBA').save(cache_path)
    return C.load(cache_path)


def aa_line(mask, points, width=2.0, alpha=1.0, dash=None):
    """Draw an anti-aliased polyline (canvas px, exact box-filtered coverage) into a float mask, in place."""
    pts = np.asarray(points, np.float64)
    cov, (x0, y0) = T.stroke_polyline(pts, width, dash=dash)
    h, w = cov.shape
    X0, Y0 = max(0, x0), max(0, y0)
    X1, Y1 = min(mask.shape[1], x0 + w), min(mask.shape[0], y0 + h)
    if X1 > X0 and Y1 > Y0:
        sub = mask[Y0:Y1, X0:X1]
        np.maximum(sub, cov[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * alpha, out=sub)
    return mask


def LW_thicken(rgba, px):
    from lib import linework as LW
    return LW.thicken(rgba, px)


def _paper_tag(h, w, paper, seed):
    img = C.solid(h, w, paper)
    rng = np.random.default_rng(seed)
    img[..., :3] *= (1 + 0.012 * rng.standard_normal((h, w, 1))).astype(np.float32)
    return np.clip(img, 0, 1)


README_TEXT = """{title}

HOW THIS FILE IS BUILT
- A3 landscape, 4961 x 3508 px at 300 ppi, sRGB IEC61966-2.1 (embedded), 8-bit. Groups are numbered from the
  back (00) to the front (98).
- Colour labels:  grey = paper   violet = client drawings & key plan   blue = outside / far planes
  orange = interior photo planes   green = the chosen area   yellow = light & colour intensity   red = senses
- Photos are never erased: every cut-out is the original photo with a LAYER MASK. Paint the mask white/black
  to reveal or hide more. Shadows are separate layers named 'Shadow - ...' - move them with their object.
- Colour washes, intensities, silhouettes, palette chips and photo grades ('Grade - ...') are SOLID COLOR fill
  layers: double-click the thumbnail to recolour, or hide a grade to see the untouched photo.
- Layers marked 'clipped' (indented arrow) only show inside the layer directly below them.
- TYPE: each 'TXT - ...' layer is the rendered text; directly above it sits a hidden, editable type layer
  'EDIT - ...' (a tag has two: label and phrase). To change wording: show the EDIT layer(s), type, then hide
  the TXT layer. Photoshop may ask to update text layers when opening - click Update. Each tag / card is its
  own group (paper, shadow, type and its leader), so it moves as one.
- Fonts used by the live type (free, SIL OFL; install them from fonts-to-install.zip, delivered beside this
  file): {fonts}.
- Paper, client drawings and the key plan are locked (position and pixels) to avoid accidental edits -
  unlock them in the Layers panel if needed.

SOURCES (all royalty-free)
{sources}

Hide this group (eye icon) to see the collage.
"""


# ---------------------------------------------------------------------- shapes

def scallop_hem_mask(x0, x1, top, gather_y, sag, period, h=H, w=W, phase=0.0, power=0.75,
                     jitter=0.0, seed=0):
    """Mask of a festoon band: everything above a scalloped hem."""
    rng = np.random.default_rng(seed)
    xs = np.arange(x0, x1 + 1, 2.0)
    u = ((xs - x0) / period + phase) % 1.0
    n = int(np.ceil((x1 - x0) / period)) + 2
    sags = sag * (1 + jitter * rng.uniform(-1, 1, n))
    idx = np.floor((xs - x0) / period + phase).astype(int) + 1
    ys = gather_y + sags[np.clip(idx, 0, n - 1)] * np.sin(np.pi * u) ** power
    pts = [(x0, top)] + list(zip(xs, ys)) + [(x1, top)]
    return C.poly_mask(pts, h, w)


def card_edge(alpha, width=10, color='#F6F0E4', opacity=1.0):
    """A paper-card rim around an alpha shape.  Pads internally so the rim is never clipped.
    Returns (rgba, offset) — place the rgba at (x - offset, y - offset)."""
    pad = width + 4
    a = np.pad(alpha.astype(np.float32), pad)
    k = width * 2 + 1
    grown = cv2.dilate(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    rim = np.clip(grown - a, 0, 1)
    out = C.solid(a.shape[0], a.shape[1], color)
    out[..., 3] = rim * opacity
    return out, pad


def local(alpha_full):
    """Crop a full-canvas alpha to its bbox -> (local, x, y)."""
    b = C.bbox(alpha_full)
    if b is None:
        return np.zeros((1, 1), np.float32), 0, 0
    x0, y0, x1, y1 = b
    return alpha_full[y0:y1, x0:x1], x0, y0


def colour_rgba(alpha, color):
    out = C.solid(alpha.shape[0], alpha.shape[1], color)
    out[..., 3] = alpha
    return out


def grade(img, lift=0.0, gamma=1.0, gain=1.0, sat=1.0, tint=None, tint_amt=0.0):
    """Simple photographic grade on float RGB(A)."""
    rgb = img[..., :3]
    out = np.clip((rgb * gain + lift), 0, 1) ** (1.0 / gamma)
    if sat != 1.0:
        l = C.lum(out)[..., None]
        out = np.clip(l + (out - l) * sat, 0, 1)
    if tint is not None and tint_amt:
        t = np.array(psdkit.hex_rgb(tint), np.float32) / 255
        out = out * (1 - tint_amt) + out * t * tint_amt * 2.0
    out = np.clip(out, 0, 1)
    if img.shape[2] == 4:
        return np.dstack([out, img[..., 3]])
    return out


def hairline_rings(cx, cy, radii, width, color, alpha=0.5, dash=None, ratio=1.0):
    """Full concentric rings (one RGBA layer, canvas-local) — calm, print-safe line weight."""
    acc = None
    for k, r in enumerate(radii):
        rg, (x, y) = S.sound_rings(at=(cx, cy), r_max=r, r_min=r, n=1, ratio=ratio, width=width, color=color,
                                   alpha=alpha, decay=1.0, dash=dash, seed=k)
        if acc is None:
            acc = (np.zeros((H, W, 4), np.float32))
        h_, w_ = rg.shape[:2]
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w_), min(H, y + h_)
        if x1 <= x0 or y1 <= y0:
            continue
        sub = rg[y0 - y:y1 - y, x0 - x:x1 - x]
        dst = acc[y0:y1, x0:x1]
        a_ = sub[..., 3:4]
        dst[..., :3] = sub[..., :3] * a_ + dst[..., :3] * (1 - a_)
        dst[..., 3:4] = a_ + dst[..., 3:4] * (1 - a_)
    return acc
