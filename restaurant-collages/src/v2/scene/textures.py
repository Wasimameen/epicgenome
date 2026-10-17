"""textures — numpy-synthesised maps that the Blender materials read (written to build/v2/tex/).

split_face(): coursed split-face sandstone, 2 m x 2 m tile at 2048 px (about 1 mm / px),
tileable in both directions. Height (16-bit, mid-level 0.5) + colour (sRGB).

Run:  python3 textures.py
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
TEX = os.path.join(ROOT, 'build', 'v2', 'tex')


def fbm(n, rng, octaves=((4, 1.0), (8, 0.6), (16, 0.35), (32, 0.2), (64, 0.12), (128, 0.07), (256, 0.04))):
    """Tileable fractal noise in [-1, 1] approx: band-limited FFT noise summed over octaves."""
    out = np.zeros((n, n), np.float32)
    fy = np.fft.fftfreq(n)[:, None] * n
    fx = np.fft.rfftfreq(n)[None, :] * n
    r = np.sqrt(fx * fx + fy * fy)
    for f0, amp in octaves:
        band = np.exp(-((r - f0) / (0.5 * f0)) ** 2)
        spec = (rng.standard_normal(band.shape) + 1j * rng.standard_normal(band.shape)) * band
        layer = np.fft.irfft2(spec, s=(n, n)).astype(np.float32)
        layer /= layer.std() + 1e-9
        out += amp * layer
    return out / 2.2


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def split_face(n=2048, size=2.0, seed=7):
    rng = np.random.default_rng(seed)
    ppm = n / size
    H = np.full((n, n), 0.12, np.float32)                  # joints: deep
    C = np.zeros((n, n, 3), np.float32)
    # courses
    heights = []
    tot = 0.0
    while tot < size - 0.05:
        h = float(rng.choice([0.09, 0.12, 0.15, 0.19, 0.24]))
        heights.append(h)
        tot += h
    heights = np.array(heights) * (size / sum(heights))
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    noise_a = fbm(n, rng)
    noise_b = fbm(n, rng, ((48, 1.0), (96, 0.6), (192, 0.4), (384, 0.25)))
    palette = np.array([[0.84, 0.79, 0.70], [0.80, 0.74, 0.64], [0.87, 0.83, 0.75], [0.78, 0.72, 0.62],
                        [0.82, 0.77, 0.68], [0.89, 0.86, 0.79], [0.76, 0.71, 0.63]], np.float32)
    joint = 0.006                                          # 6 mm joint
    y0 = 0.0
    for ch in heights:
        x = rng.uniform(0, size)
        start = x
        while x < start + size - 0.1:
            bl = float(rng.uniform(0.28, 0.75))
            if x + bl > start + size - 0.12:
                bl = start + size - x
            _block(H, C, x, y0, bl, ch, joint, ppm, n, rng, palette, noise_a, noise_b)
            x += bl
        y0 += ch
    # cavity darkening (local relief below its blurred self)
    k = np.fft.rfft2(H)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    g = np.exp(-(fx * fx + fy * fy) * (2 * np.pi * 9) ** 2 / 2)
    blur = np.fft.irfft2(k * g, s=(n, n))
    cav = np.clip((blur - H) * 4.0, -0.3, 0.6)
    C *= (1 - 0.55 * np.clip(cav, 0, 1))[..., None]
    C *= (1 + 0.25 * np.clip(-cav, 0, 0.3))[..., None]
    speck = fbm(n, rng, ((300, 1.0), (600, 0.8)))
    C *= (1 + 0.06 * speck)[..., None]
    C = np.clip(C, 0, 1)
    return H, C


def _block(H, C, x0, y0, bl, ch, joint, ppm, n, rng, palette, na, nb):
    xs = int(np.floor(x0 * ppm))
    xe = int(np.ceil((x0 + bl) * ppm))
    ys = int(np.floor(y0 * ppm))
    ye = int(min(n, np.ceil((y0 + ch) * ppm)))
    w = xe - xs
    h = ye - ys
    if w <= 2 or h <= 2:
        return
    lx = (np.arange(w, dtype=np.float32) + 0.5) / ppm                      # metres in block
    ly = (np.arange(h, dtype=np.float32) + 0.5) / ppm
    LX, LY = np.meshgrid(lx, ly)
    cx, cy = bl / 2, ch / 2
    # faceted split face: min of K random planes around a peak, i.e. conchoidal facets
    K = int(rng.integers(7, 14))
    face = np.full_like(LX, 9.0)
    peak = rng.uniform(0.55, 0.8)
    for _ in range(K):
        ang = rng.uniform(0, 2 * np.pi)
        slope = rng.uniform(1.2, 4.5)
        ox = cx + rng.uniform(-0.35, 0.35) * bl
        oy = cy + rng.uniform(-0.35, 0.35) * ch
        plane = peak + rng.uniform(-0.05, 0.08) - slope * ((LX - ox) * np.cos(ang) + (LY - oy) * np.sin(ang)) ** 1
        face = np.minimum(face, np.maximum(plane, 0.0) + 0.0)
    face = np.clip(face, 0.25, 0.92)
    # edge falloff into the joint (chipped arrises)
    d = np.minimum.reduce([LX, bl - LX, LY, ch - LY])
    rough_edge = d + 0.004 * na[ys:ye, np.arange(xs, xe) % n]
    e = smoothstep(joint / 2, joint / 2 + 0.014, rough_edge)
    cols = np.arange(xs, xe) % n
    relief = face + 0.10 * na[ys:ye][:, cols] + 0.05 * nb[ys:ye][:, cols]
    hh = 0.12 + (relief - 0.12) * e
    hh = np.where(d < joint / 2, 0.10, hh)
    H[ys:ye][:, cols] = hh
    base = palette[rng.integers(len(palette))] * rng.uniform(0.93, 1.06)
    tint = base[None, None, :] * (1 + 0.08 * na[ys:ye][:, cols, None])
    jc = np.array([0.55, 0.50, 0.43], np.float32)
    C[ys:ye][:, cols] = np.where((d < joint / 2)[..., None], jc, tint)


def save16(path, a):
    a16 = (np.clip(a, 0, 1) * 65535).astype(np.uint16)
    Image.fromarray(a16).save(path)


def save8(path, rgb):
    Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)


def main():
    os.makedirs(TEX, exist_ok=True)
    H, C = split_face()
    save16(os.path.join(TEX, 'split_face_height.png'), H)
    save8(os.path.join(TEX, 'split_face_color.png'), C)          # palette is authored in sRGB
    print('split_face', H.min(), H.max())


if __name__ == '__main__':
    main()
