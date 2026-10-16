"""psdkit — a small layered-document model with a Photoshop-compatible compositor.

A Document is a tree of Groups / Pixel layers / solid-colour Fill layers, ordered
bottom -> top exactly like the Photoshop Layers panel read upwards.  Every layer
is quantised to 8-bit at construction time so the flattened render produced here
is computed from the very same pixels that go into the PSD.

Supported (and mirrored 1:1 by write_psd.js):
  * pixel layers cropped to their content bounds
  * layer masks (white reveals) with a default colour outside the mask bounds
  * clipping masks ("Create Clipping Mask"), clipped layers blend as a group
  * solid-colour fill layers (double-click to recolour in Photoshop)
  * pass-through groups with colour labels, collapsed/expanded state
  * opacity, visibility and the separable + non-separable blend modes below
"""
from __future__ import annotations

import json
import os
import numpy as np
from PIL import Image

# --------------------------------------------------------------------------- #
# blend modes (Cb = backdrop, Cs = source, both float32 0..1)
# --------------------------------------------------------------------------- #

def _multiply(cb, cs): return cb * cs
def _screen(cb, cs): return cb + cs - cb * cs
def _overlay(cb, cs): return _hard_light(cs, cb)
def _darken(cb, cs): return np.minimum(cb, cs)
def _lighten(cb, cs): return np.maximum(cb, cs)
def _linear_dodge(cb, cs): return np.minimum(1.0, cb + cs)
def _linear_burn(cb, cs): return np.maximum(0.0, cb + cs - 1.0)
def _difference(cb, cs): return np.abs(cb - cs)
def _exclusion(cb, cs): return cb + cs - 2 * cb * cs


def _hard_light(cb, cs):
    return np.where(cs <= 0.5, cb * 2 * cs, _screen(cb, 2 * cs - 1))


def _soft_light(cb, cs):
    # Photoshop's soft light (sqrt branch for every backdrop value)
    return np.where(cs <= 0.5,
                    2 * cb * cs + cb * cb * (1 - 2 * cs),
                    np.sqrt(np.clip(cb, 0, 1)) * (2 * cs - 1) + 2 * cb * (1 - cs))


def _color_dodge(cb, cs):
    with np.errstate(divide='ignore', invalid='ignore'):
        r = np.where(cs >= 1.0, 1.0, np.minimum(1.0, cb / np.maximum(1e-6, 1 - cs)))
    return np.where(cb <= 0.0, 0.0, r)


def _color_burn(cb, cs):
    with np.errstate(divide='ignore', invalid='ignore'):
        r = np.where(cs <= 0.0, 0.0, 1 - np.minimum(1.0, (1 - cb) / np.maximum(1e-6, cs)))
    return np.where(cb >= 1.0, 1.0, r)


def _lum(c):
    return 0.3 * c[..., 0:1] + 0.59 * c[..., 1:2] + 0.11 * c[..., 2:3]


def _clip_color(c):
    l = _lum(c)
    n = c.min(axis=-1, keepdims=True)
    x = c.max(axis=-1, keepdims=True)
    with np.errstate(divide='ignore', invalid='ignore'):
        c = np.where(n < 0, l + (c - l) * l / np.maximum(1e-6, l - n), c)
        c = np.where(x > 1, l + (c - l) * (1 - l) / np.maximum(1e-6, x - l), c)
    return c


def _set_lum(c, l):
    return _clip_color(c + (l - _lum(c)))


def _sat(c):
    return c.max(axis=-1, keepdims=True) - c.min(axis=-1, keepdims=True)


def _set_sat(c, s):
    mn = c.min(axis=-1, keepdims=True)
    mx = c.max(axis=-1, keepdims=True)
    rng = mx - mn
    with np.errstate(divide='ignore', invalid='ignore'):
        out = np.where(rng > 1e-6, (c - mn) * s / np.maximum(1e-6, rng), 0.0)
    return out


def _hue(cb, cs): return _set_lum(_set_sat(cs, _sat(cb)), _lum(cb))
def _saturation(cb, cs): return _set_lum(_set_sat(cb, _sat(cs)), _lum(cb))
def _color(cb, cs): return _set_lum(cs, _lum(cb))
def _luminosity(cb, cs): return _set_lum(cb, _lum(cs))


BLEND = {
    'normal': None,
    'multiply': _multiply,
    'screen': _screen,
    'overlay': _overlay,
    'soft light': _soft_light,
    'hard light': _hard_light,
    'darken': _darken,
    'lighten': _lighten,
    'color dodge': _color_dodge,
    'color burn': _color_burn,
    'linear dodge': _linear_dodge,
    'linear burn': _linear_burn,
    'difference': _difference,
    'exclusion': _exclusion,
    'hue': _hue,
    'saturation': _saturation,
    'color': _color,
    'luminosity': _luminosity,
}

LABELS = {'none', 'red', 'orange', 'yellow', 'green', 'blue', 'violet', 'gray'}


def _q8(a):
    """float 0..1 -> uint8 (round half up), keeps arrays exactly reproducible."""
    return np.clip(np.floor(np.asarray(a, dtype=np.float32) * 255.0 + 0.5), 0, 255).astype(np.uint8)


def _to_u8_rgba(rgba):
    rgba = np.asarray(rgba)
    if rgba.dtype != np.uint8:
        rgba = _q8(rgba)
    if rgba.ndim != 3 or rgba.shape[2] not in (3, 4):
        raise ValueError(f'expected HxWx3/4 array, got {rgba.shape}')
    if rgba.shape[2] == 3:
        rgba = np.concatenate([rgba, np.full(rgba.shape[:2] + (1,), 255, np.uint8)], axis=2)
    return np.ascontiguousarray(rgba)


def hex_rgb(c):
    if isinstance(c, str):
        c = c.lstrip('#')
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(v) for v in c)


# --------------------------------------------------------------------------- #
# nodes
# --------------------------------------------------------------------------- #

class Mask:
    """Layer mask. `alpha` is HxW (float 0..1 or uint8); white reveals."""

    def __init__(self, alpha, x=0, y=0, default=0):
        a = np.asarray(alpha)
        if a.dtype != np.uint8:
            a = _q8(a)
        self.alpha = np.ascontiguousarray(a)
        self.x, self.y = int(x), int(y)
        self.default = 255 if default else 0

    @property
    def bounds(self):
        h, w = self.alpha.shape
        return self.x, self.y, self.x + w, self.y + h

    def sample(self, x0, y0, x1, y1):
        """Mask values (float 0..1) over the canvas rectangle [x0,x1)x[y0,y1)."""
        out = np.full((y1 - y0, x1 - x0), self.default / 255.0, np.float32)
        mx0, my0, mx1, my1 = self.bounds
        ix0, iy0 = max(x0, mx0), max(y0, my0)
        ix1, iy1 = min(x1, mx1), min(y1, my1)
        if ix1 > ix0 and iy1 > iy0:
            out[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0] = \
                self.alpha[iy0 - my0:iy1 - my0, ix0 - mx0:ix1 - mx0] / 255.0
        return out


class Node:
    kind = 'node'

    def __init__(self, name, blend='normal', opacity=1.0, hidden=False, label=None, clip=False):
        if blend not in BLEND and blend != 'pass through':
            raise ValueError(f'unsupported blend mode {blend!r}')
        if label is not None and label not in LABELS:
            raise ValueError(f'bad colour label {label!r}')
        self.name = name
        self.blend = blend
        self.opacity = float(opacity)
        self.hidden = bool(hidden)
        self.label = label
        self.clip = bool(clip)


class Pixel(Node):
    kind = 'pixel'

    def __init__(self, name, rgba, x=0, y=0, mask=None, trim=True, **kw):
        super().__init__(name, **kw)
        rgba = _to_u8_rgba(rgba)
        x, y = int(x), int(y)
        if trim:
            nz = rgba[..., 3] > 0
            if nz.any():
                rows = np.flatnonzero(nz.any(axis=1))
                cols = np.flatnonzero(nz.any(axis=0))
                r0, r1, c0, c1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
                rgba = rgba[r0:r1, c0:c1]
                x += int(c0)
                y += int(r0)
            else:
                rgba = rgba[:0, :0]
        self.rgba = np.ascontiguousarray(rgba)
        self.x, self.y = x, y
        self.mask = mask

    @property
    def bounds(self):
        h, w = self.rgba.shape[:2]
        return self.x, self.y, self.x + w, self.y + h


class Fill(Node):
    """Solid Color fill layer; the shape comes from its mask."""
    kind = 'fill'

    def __init__(self, name, color, mask=None, **kw):
        super().__init__(name, **kw)
        self.color = hex_rgb(color)
        self.mask = mask


class Group(Node):
    kind = 'group'

    def __init__(self, name, children=None, opened=False, **kw):
        kw.setdefault('blend', 'pass through')
        super().__init__(name, **kw)
        if self.blend != 'pass through' or self.opacity != 1.0:
            raise ValueError('groups are pass-through at 100% so the render stays exact')
        self.children = list(children or [])
        self.opened = bool(opened)

    def add(self, node):
        self.children.append(node)
        return node

    def iter_layers(self):
        for c in self.children:
            yield c
            if isinstance(c, Group):
                yield from c.iter_layers()


# --------------------------------------------------------------------------- #
# document + compositor
# --------------------------------------------------------------------------- #

class Document:
    def __init__(self, width, height, dpi=300, title='Untitled'):
        self.width, self.height, self.dpi, self.title = int(width), int(height), dpi, title
        self.root = Group('root', opened=True)

    def add(self, node):
        return self.root.add(node)

    # --- rendering -------------------------------------------------------- #
    def render(self, upto=None):
        canvas = np.ones((self.height, self.width, 3), np.float32)
        self._composite(canvas, self.root.children)
        return canvas

    def _layer_src(self, node, region=None):
        """Return (rgb float, alpha float, (x0,y0,x1,y1)) clipped to canvas, or None."""
        W, H = self.width, self.height
        if isinstance(node, Pixel):
            x0, y0, x1, y1 = node.bounds
        else:  # Fill
            if node.mask is not None and node.mask.default == 0:
                x0, y0, x1, y1 = node.mask.bounds
            else:
                x0, y0, x1, y1 = 0, 0, W, H
        if region is not None:
            x0, y0 = max(x0, region[0]), max(y0, region[1])
            x1, y1 = min(x1, region[2]), min(y1, region[3])
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if x1 <= x0 or y1 <= y0:
            return None
        if isinstance(node, Pixel):
            sub = node.rgba[y0 - node.y:y1 - node.y, x0 - node.x:x1 - node.x].astype(np.float32) / 255.0
            rgb, a = sub[..., :3], sub[..., 3]
        else:
            rgb = np.empty((y1 - y0, x1 - x0, 3), np.float32)
            rgb[:] = np.array(node.color, np.float32) / 255.0
            a = np.ones((y1 - y0, x1 - x0), np.float32)
        if node.mask is not None:
            a = a * node.mask.sample(x0, y0, x1, y1)
        return rgb, a, (x0, y0, x1, y1)

    @staticmethod
    def _blend_into(cb, cs, a, mode):
        """In-place: cb = (1-a) cb + a B(cb, cs) for an opaque backdrop."""
        fn = BLEND[mode]
        b = cs if fn is None else fn(cb, cs)
        a3 = a[..., None]
        cb += a3 * (b - cb)
        np.clip(cb, 0.0, 1.0, out=cb)

    def _composite(self, canvas, children):
        i, n = 0, len(children)
        while i < n:
            node = children[i]
            j = i + 1
            clipped = []
            while j < n and children[j].clip:
                clipped.append(children[j])
                j += 1
            if node.clip:
                raise ValueError(f'clipped layer {node.name!r} has no base layer below it')
            if node.hidden:
                i = j
                continue
            if isinstance(node, Group):
                if clipped:
                    raise ValueError(f'clipping onto group {node.name!r} is not supported')
                self._composite(canvas, node.children)
                i = j
                continue
            src = self._layer_src(node)
            if src is None:
                i = j
                continue
            rgb, a, (x0, y0, x1, y1) = src
            rgb = rgb.copy()
            for c in clipped:
                if c.hidden:
                    continue
                if isinstance(c, Group):
                    raise ValueError('groups cannot be clipped')
                csrc = self._layer_src(c, region=(x0, y0, x1, y1))
                if csrc is None:
                    continue
                crgb, ca, (cx0, cy0, cx1, cy1) = csrc
                sl = (slice(cy0 - y0, cy1 - y0), slice(cx0 - x0, cx1 - x0))
                # clipped layers composite "source-atop" onto the base layer pixels
                self._blend_into(rgb[sl], crgb, ca * c.opacity, c.blend)
            region = canvas[y0:y1, x0:x1]
            self._blend_into(region, rgb, a * node.opacity, node.blend)
            i = j

    # --- export ----------------------------------------------------------- #
    def export(self, out_dir, composite=None):
        """Write manifest.json + per-layer PNGs (+ composite.png) for write_psd.js."""
        layers_dir = os.path.join(out_dir, 'layers')
        os.makedirs(layers_dir, exist_ok=True)
        counter = [0]

        def dump(node):
            counter[0] += 1
            idx = counter[0]
            d = {'type': node.kind, 'name': node.name, 'blend': node.blend,
                 'opacity': node.opacity, 'hidden': node.hidden, 'clip': node.clip}
            if node.label:
                d['label'] = node.label
            if isinstance(node, Group):
                d['opened'] = node.opened
                d['children'] = [dump(c) for c in node.children]
                return d
            if isinstance(node, Pixel):
                d['x'], d['y'] = node.x, node.y
                if node.rgba.size:
                    p = os.path.join('layers', f'{idx:04d}.png')
                    Image.fromarray(node.rgba, 'RGBA').save(os.path.join(out_dir, p), compress_level=1)
                    d['png'] = p
            if isinstance(node, Fill):
                d['color'] = list(node.color)
            if node.mask is not None:
                mp = os.path.join('layers', f'{idx:04d}_mask.png')
                Image.fromarray(node.mask.alpha, 'L').save(os.path.join(out_dir, mp), compress_level=1)
                d['mask'] = {'png': mp, 'x': node.mask.x, 'y': node.mask.y, 'default': node.mask.default}
            return d

        manifest = {
            'title': self.title, 'width': self.width, 'height': self.height, 'dpi': self.dpi,
            'layers': [dump(c) for c in self.root.children],
        }
        if composite is None:
            composite = self.render()
        comp8 = _q8(composite)
        Image.fromarray(comp8, 'RGB').save(os.path.join(out_dir, 'composite.png'), compress_level=1)
        manifest['composite'] = 'composite.png'
        with open(os.path.join(out_dir, 'manifest.json'), 'w') as f:
            json.dump(manifest, f, indent=1)
        return manifest

    def layer_count(self):
        return sum(1 for _ in self.root.iter_layers())
