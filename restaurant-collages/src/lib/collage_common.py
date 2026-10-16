"""collage_common — shared builder for the two A3 atmosphere collages.

Wraps a psdkit Document with helpers that keep every layer named, grouped and
non-destructive: photos keep their full pixels behind layer masks, textures are
clipped into shapes, washes are Solid Color fill layers with masks, shadows and
glows are separate layers, and type is rasterised into clearly named layers.
"""
from __future__ import annotations

import os
import numpy as np
import cv2

import psdkit
from psdkit import Document, Group, Pixel, Fill, Mask
from lib import compose as C
from lib import typeset as T
from lib import sensory as S

W, H = C.W, C.H
INK = '#2B2420'
PAL = S.PAL


def asset(*parts):
    return C.P('assets', *parts)


def have(*parts):
    return os.path.exists(asset(*parts))


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

    def photo(self, g, name, img, x, y, mask_alpha=None, mask_xy=None, **kw):
        """Photo pixel layer with an optional layer mask.

        ``mask_alpha`` is either a full-canvas float mask (mask_xy None) or a local
        mask placed at ``mask_xy``.  The photo keeps all its pixels; the mask decides
        what shows, so the client can repaint it in Photoshop.
        """
        mask = None
        if mask_alpha is not None:
            if mask_xy is None:
                mask = C.canvas_mask(name, mask_alpha)
            else:
                mask = C.mask_for(mask_alpha, mask_xy[0], mask_xy[1])
        layer = C.pixel(name, img, int(round(x)), int(round(y)), mask=mask, **kw)
        g.add(layer)
        return layer

    def fill(self, g, name, color, alpha=None, **kw):
        layer = C.fill(name, color, alpha, **kw)
        g.add(layer)
        return layer

    def shadow(self, g, name, alpha, x, y, dx=22, dy=30, sigma=34, opacity=0.42, color=INK):
        layer = C.shadow(name, alpha, int(round(x)), int(round(y)), dx, dy, sigma, opacity, color)
        g.add(layer)
        return layer

    # ------------------------------------------------------------------ type
    def text(self, g, text, font, size, x, y, anchor='baseline_left', color=INK, name=None,
             opacity=1.0, blend='normal', **kw):
        rgba, meta = T.text_rgba(text, font, size, color=color, **kw)
        px, py = T.place(meta, x, y, anchor)
        nm = name or ('TXT · ' + text.replace('\n', ' / '))
        self.px(g, nm[:120], rgba, px, py, opacity=opacity, blend=blend)
        return meta, (px, py)

    def label(self, g, label, phrase, x, y, anchor='label_baseline', name=None, color=INK,
              label_color='#A9502F', opacity=1.0, **kw):
        rgba, meta = T.label_block(label, phrase, color=color, label_color=label_color, **kw)
        px, py = T.place(meta, x, y, anchor)
        nm = name or f'TXT · {label} — {phrase}'.replace('\n', ' ')
        self.px(g, nm[:120], rgba, px, py, opacity=opacity)
        return meta, (px, py)

    def leader(self, g, name, points, width=2.0, color=INK, opacity=0.9, **kw):
        rgba, (x, y) = T.leader(points, width=width, color=color, **kw)
        return self.px(g, name, rgba, x, y, opacity=opacity)

    def tag(self, g, label, phrase, x, y, pad=(34, 26), paper='#F4EEE2', color=INK,
            label_color='#A9502F', shadow=0.38, **kw):
        """A small linen paper tag (own drop shadow) carrying a label + phrase.

        (x, y) is the tag's top-left.  Returns the tag box (x0, y0, x1, y1)."""
        rgba, meta = T.label_block(label, phrase, color=color, label_color=label_color, **kw)
        ix0, iy0, ix1, iy1 = meta['ink_box']
        pw = int(round(ix1 - ix0 + 2 * pad[0]))
        ph = int(round(iy1 - iy0 + 2 * pad[1]))
        tagimg = C.solid(ph, pw, paper)
        # faint fibre tone so the tag reads as paper, not a flat box
        rng = np.random.default_rng(len(phrase) * 7 + len(label))
        tagimg[..., :3] *= (1 + 0.012 * rng.standard_normal((ph, pw, 1))).astype(np.float32)
        tagimg = np.clip(tagimg, 0, 1)
        short = f'{label}'
        if shadow:
            self.shadow(g, f'Tag shadow · {short}', np.ones((ph, pw), np.float32), x, y, dx=10, dy=14,
                        sigma=14, opacity=shadow)
        self.px(g, f'Tag · {short} (paper)', tagimg, x, y)
        tx = x + pad[0] - ix0
        ty = y + pad[1] - iy0
        self.px(g, f'TXT · {label} — {phrase}'.replace('\n', ' ')[:120], rgba, tx, ty)
        return (x, y, x + pw, y + ph)

    def card(self, g, name, entries, x, y, pad=(40, 32), gap=34, paper='#F4EEE2', color=INK,
             label_color='#A9502F', shadow=0.38, **kw):
        """One paper card carrying several stacked (label, phrase) annotations."""
        blocks = [T.label_block(lab, ph, color=color, label_color=label_color, **kw) for lab, ph in entries]
        boxes = [m['ink_box'] for _, m in blocks]
        width = max(b[2] - b[0] for b in boxes)
        height = sum(b[3] - b[1] for b in boxes) + gap * (len(blocks) - 1)
        pw, ph = int(round(width + 2 * pad[0])), int(round(height + 2 * pad[1]))
        tagimg = C.solid(ph, pw, paper)
        rng = np.random.default_rng(len(entries) * 13 + pw)
        tagimg[..., :3] *= (1 + 0.012 * rng.standard_normal((ph, pw, 1))).astype(np.float32)
        if shadow:
            self.shadow(g, f'Card shadow · {name}', np.ones((ph, pw), np.float32), x, y, dx=10, dy=14,
                        sigma=14, opacity=shadow)
        self.px(g, f'Card · {name} (paper)', np.clip(tagimg, 0, 1), x, y)
        cy = y + pad[1]
        for (rgba, meta), (lab, phr), b in zip(blocks, entries, boxes):
            self.px(g, f'TXT · {lab} — {phr}'.replace('\n', ' ')[:120], rgba, x + pad[0] - b[0], cy - b[1])
            cy += (b[3] - b[1]) + gap
        return (x, y, x + pw, y + ph)


# ---------------------------------------------------------------------- shapes

def scallop_hem_mask(x0, x1, top, gather_y, sag, period, h=H, w=W, phase=0.0, power=0.75,
                     jitter=0.0, seed=0):
    """Mask of a festoon band: everything above a scalloped hem.

    Gathers sit at ``gather_y``; between them the hem sags by ``sag`` px."""
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
    """A thin paper-card rim around an alpha shape (returns RGBA same size)."""
    a = alpha.astype(np.float32)
    k = width * 2 + 1
    grown = cv2.dilate(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    rim = np.clip(grown - a, 0, 1)
    out = C.solid(a.shape[0], a.shape[1], color)
    out[..., 3] = rim * opacity
    return out


def ring_stroke(cx, cy, rx, ry, width, h=H, w=W, angle=0.0):
    return C.ring_mask(cx, cy, rx + width / 2, ry + width / 2, width, angle, h, w)


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
