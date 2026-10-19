"""compose — placement / warping / mask helpers shared by the two collage builds.

All images are float32 arrays in 0..1 (H, W, 4) straight alpha unless noted.
Coordinates are canvas pixels (x right, y down) on the 4961 x 3508 A3 @ 300 ppi page.
"""
from __future__ import annotations

import os
import numpy as np
import cv2
from PIL import Image

import psdkit
from psdkit import Pixel, Fill, Mask, Group, hex_rgb

W, H = 4961, 3508
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def P(*parts):
    return os.path.join(ROOT, *parts)


# --------------------------------------------------------------------------- #
# io
# --------------------------------------------------------------------------- #

def load(path, mode='RGBA'):
    """Load an image (path relative to the repo root or absolute) as float32 0..1."""
    if not os.path.isabs(path):
        path = P(path)
    im = Image.open(path)
    if mode == 'L':
        return np.asarray(im.convert('L'), np.float32) / 255.0
    if im.mode in ('I;16', 'I'):
        return np.asarray(im)
    return np.asarray(im.convert(mode), np.float32) / 255.0


def save_preview(arr, path, max_side=1600, quality=88):
    a = np.asarray(arr)
    if a.dtype != np.uint8:
        a = np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8)
    if a.ndim == 3 and a.shape[2] == 4:  # flatten on linen for viewing
        rgb = a[..., :3].astype(np.float32)
        al = a[..., 3:4].astype(np.float32) / 255
        bg = np.array(hex_rgb('#EFE6D6'), np.float32)
        a = (rgb * al + bg * (1 - al)).astype(np.uint8)
    im = Image.fromarray(a)
    s = max_side / max(im.size)
    if s < 1:
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.convert('RGB').save(path, quality=quality)
    return path


def rgba(rgb, alpha=None):
    rgb = np.asarray(rgb, np.float32)
    if rgb.shape[-1] == 4:
        return rgb if alpha is None else np.dstack([rgb[..., :3], rgb[..., 3] * alpha])
    if alpha is None:
        alpha = np.ones(rgb.shape[:2], np.float32)
    return np.dstack([rgb, np.asarray(alpha, np.float32)])


def solid(h, w, color, alpha=1.0):
    c = np.array(hex_rgb(color), np.float32) / 255.0
    out = np.empty((h, w, 4), np.float32)
    out[..., :3] = c
    out[..., 3] = alpha
    return out


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #

def _premul(img):
    out = img.copy()
    out[..., :3] *= out[..., 3:4]
    return out


def _unpremul(img):
    out = img.copy()
    a = out[..., 3:4]
    out[..., :3] = np.where(a > 1e-5, out[..., :3] / np.maximum(a, 1e-5), 0)
    return np.clip(out, 0, 1)


def resize(img, scale=None, size=None):
    """Alpha-correct resize (premultiplied). size = (w, h)."""
    h, w = img.shape[:2]
    if size is None:
        size = (max(1, round(w * scale)), max(1, round(h * scale)))
    interp = cv2.INTER_AREA if size[0] < w else cv2.INTER_LANCZOS4
    if img.ndim == 2:
        return np.clip(cv2.resize(img, size, interpolation=interp), 0, 1)
    if img.shape[2] == 4:
        return _unpremul(np.clip(cv2.resize(_premul(img), size, interpolation=interp), 0, 1))
    return np.clip(cv2.resize(img, size, interpolation=interp), 0, 1)


def crop(img, x0, y0, x1, y1):
    return img[int(y0):int(y1), int(x0):int(x1)]


def cover(img, w, h, focus=(0.5, 0.5)):
    """Scale + crop to exactly fill w x h (like CSS object-fit: cover)."""
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih)
    r = resize(img, s)
    rh, rw = r.shape[:2]
    x0 = int(round((rw - w) * focus[0]))
    y0 = int(round((rh - h) * focus[1]))
    return r[y0:y0 + h, x0:x0 + w]


def affine(img, scale=1.0, angle=0.0, flip=False):
    """Scale + rotate (degrees, CCW) around the centre, alpha-correct.
    Returns (rgba, dx, dy): the top-left offset of the result relative to the
    top-left of the *unrotated scaled* image, so place at (x + dx, y + dy)."""
    if img.shape[2] == 3:
        img = rgba(img)
    if flip:
        img = img[:, ::-1]
    h, w = img.shape[:2]
    sw, sh = w * scale, h * scale
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
    cos, sin = abs(M[0, 0]), abs(M[0, 1])
    nw = int(np.ceil(h * sin + w * cos)) + 2
    nh = int(np.ceil(h * cos + w * sin)) + 2
    M[0, 2] += nw / 2 - w / 2
    M[1, 2] += nh / 2 - h / 2
    interp = cv2.INTER_AREA if scale < 0.7 else cv2.INTER_LANCZOS4
    out = cv2.warpAffine(_premul(img), M, (nw, nh), flags=interp,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    out = _unpremul(np.clip(out, 0, 1))
    dx = int(round((sw - nw) / 2))
    dy = int(round((sh - nh) / 2))
    return out, dx, dy


def warp_quad(img, quad):
    """Perspective-warp the full image onto quad [(x,y) tl, tr, br, bl] in canvas space.
    Returns (rgba, x0, y0) cropped to the quad's bounding box."""
    if img.shape[2] == 3:
        img = rgba(img)
    h, w = img.shape[:2]
    q = np.array(quad, np.float32)
    x0, y0 = np.floor(q.min(0)).astype(int)
    x1, y1 = np.ceil(q.max(0)).astype(int)
    src = np.array([[0, 0], [w, 0], [w, h], [0, h]], np.float32)
    dst = q - np.array([x0, y0], np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    out = cv2.warpPerspective(_premul(img), M, (int(x1 - x0), int(y1 - y0)), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    return _unpremul(np.clip(out, 0, 1)), int(x0), int(y0)


# --------------------------------------------------------------------------- #
# masks (anti-aliased, float 0..1, full canvas unless h/w given)
# --------------------------------------------------------------------------- #

_SS = 4  # sub-pixel bits for cv2 shift


def poly_mask(points, h=H, w=W, feather=0.0):
    m = np.zeros((h, w), np.uint8)
    pts = np.round(np.asarray(points, np.float64) * (1 << _SS)).astype(np.int32)
    cv2.fillPoly(m, [pts], 255, lineType=cv2.LINE_AA, shift=_SS)
    m = m.astype(np.float32) / 255.0
    return blur(m, feather) if feather else m


def ellipse_mask(cx, cy, rx, ry, angle=0.0, h=H, w=W, feather=0.0):
    m = np.zeros((h, w), np.uint8)
    c = (int(round(cx * (1 << _SS))), int(round(cy * (1 << _SS))))
    ax = (int(round(rx * (1 << _SS))), int(round(ry * (1 << _SS))))
    cv2.ellipse(m, c, ax, angle, 0, 360, 255, -1, lineType=cv2.LINE_AA, shift=_SS)
    m = m.astype(np.float32) / 255.0
    return blur(m, feather) if feather else m


def arch_mask(left, right, spring_y, bottom_y, crown_y=None, h=H, w=W, feather=0.0, n=180):
    """Round/elliptical-headed arch: rectangle from spring_y..bottom_y + half-ellipse above."""
    cx = (left + right) / 2
    rx = (right - left) / 2
    ry = rx if crown_y is None else spring_y - crown_y
    t = np.linspace(np.pi, 2 * np.pi, n)
    top = np.stack([cx + rx * np.cos(t), spring_y + ry * np.sin(t)], 1)
    pts = np.concatenate([[[left, bottom_y]], top, [[right, bottom_y]]], 0)
    return poly_mask(pts, h, w, feather)


def rect_mask(x0, y0, x1, y1, h=H, w=W, feather=0.0):
    return poly_mask([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], h, w, feather)


def ring_mask(cx, cy, rx, ry, width, angle=0.0, h=H, w=W, feather=0.0):
    outer = ellipse_mask(cx, cy, rx, ry, angle, h, w)
    inner = ellipse_mask(cx, cy, max(1, rx - width), max(1, ry - width), angle, h, w)
    m = np.clip(outer - inner, 0, 1)
    return blur(m, feather) if feather else m


def blur(img, sigma):
    if sigma <= 0:
        return img
    k = int(sigma * 3) * 2 + 1
    return cv2.GaussianBlur(img, (k, k), sigma, borderType=cv2.BORDER_REPLICATE)


def bbox(alpha, thresh=1e-3, pad=0):
    ys, xs = np.nonzero(alpha > thresh)
    if not len(xs):
        return None
    return (max(0, xs.min() - pad), max(0, ys.min() - pad),
            min(alpha.shape[1], xs.max() + 1 + pad), min(alpha.shape[0], ys.max() + 1 + pad))


# --------------------------------------------------------------------------- #
# layer factories
# --------------------------------------------------------------------------- #

def pixel(name, img, x=0, y=0, keep_offcanvas=False, **kw):
    """Pixel layer from float RGBA/RGB; crops to the canvas unless keep_offcanvas."""
    if img.shape[2] == 3:
        img = rgba(img)
    x, y = int(x), int(y)
    if not keep_offcanvas:
        h, w = img.shape[:2]
        cx0, cy0 = max(0, -x), max(0, -y)
        cx1, cy1 = min(w, W - x), min(h, H - y)
        if cx1 <= cx0 or cy1 <= cy0:
            raise ValueError(f'layer {name!r} is entirely off canvas')
        img = img[cy0:cy1, cx0:cx1]
        x, y = x + cx0, y + cy0
    return Pixel(name, img, x, y, **kw)


def canvas_mask(name_unused, alpha, default=0):
    """Wrap a full-canvas float mask as a psdkit Mask cropped to its content."""
    b = bbox(alpha)
    if b is None:
        return Mask(np.zeros((1, 1), np.uint8), 0, 0, default)
    x0, y0, x1, y1 = b
    return Mask(alpha[y0:y1, x0:x1], x0, y0, default)


def mask_for(alpha, x=0, y=0, default=0):
    """psdkit Mask from a local float mask at canvas offset (x, y), trimmed to content."""
    b = bbox(alpha)
    if b is None:
        return Mask(np.zeros((1, 1), np.uint8), x, y, default)
    x0, y0, x1, y1 = b
    return Mask(alpha[y0:y1, x0:x1], x + x0, y + y0, default)


def fill(name, color, alpha=None, **kw):
    """Solid Color fill layer; alpha is a full-canvas float mask (None = whole canvas)."""
    m = None if alpha is None else canvas_mask(name, alpha)
    return Fill(name, color, mask=m, **kw)


def shadow(name, alpha, x, y, dx=18, dy=24, sigma=28, opacity=0.45, color='#2B2420'):
    """Soft cast-shadow pixel layer from a local alpha placed at (x, y)."""
    pad = int(sigma * 3) + max(abs(dx), abs(dy))
    a = np.pad(alpha, pad)
    a = blur(a, sigma)
    img = solid(a.shape[0], a.shape[1], color)
    img[..., 3] = a
    return pixel(name, img, x - pad + dx, y - pad + dy, opacity=opacity, blend='multiply')


def texture_fill(tex, h, w, scale=1.0, offset=(0, 0)):
    """Tile (mirror-free) a texture to h x w after scaling."""
    t = resize(tex, scale) if scale != 1.0 else tex
    th, tw = t.shape[:2]
    ry, rx = -(-(h + offset[1]) // th), -(-(w + offset[0]) // tw)
    big = np.tile(t, (ry + 1, rx + 1, 1))
    return big[offset[1]:offset[1] + h, offset[0]:offset[0] + w]


def lum(img):
    return 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]


def mix(a, b, t):
    return a + (b - a) * t
