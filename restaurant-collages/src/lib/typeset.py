"""typeset — precise, print-quality text and hairline rendering for the collages.

Text is set from the real font outlines (fontTools), shaped with the fonts' own GPOS
kerning and GSUB ligatures / figure styles, and rasterised by an exact-coverage
non-zero-winding scanline rasteriser (analytic horizontal coverage x 8-16 vertical
sub-scanlines).  Rotation is applied to the vector outlines *before* rasterisation, so
rotated text is exactly as crisp as horizontal text (no resampling).

Fonts (all SIL OFL 1.1, see assets/fonts/index.json):
    key        aliases                      face
    cg-400     serif                        Cormorant Garamond Regular
    cg-400i    italic                       Cormorant Garamond Italic
    cg-500i    italic-medium                Cormorant Garamond Medium Italic
    cg-300i    italic-light                 Cormorant Garamond Light Italic
    cg-600     serif-semibold               Cormorant Garamond SemiBold
    plex-300   mono-light                   IBM Plex Mono Light
    plex-400   mono                         IBM Plex Mono Regular
    plex-500   mono-medium                  IBM Plex Mono Medium
Per-character fallback chain: font latin subset -> same style latin-ext subset ->
in-family synthesised arrows (-> and <- built by rotating the font's own up-arrow
outline) -> weight-matched Inter, scaled to the primary cap height.

Coordinates: pixels, x right, y down.  All public renderers return float32 straight-alpha
RGBA arrays (H, W, 4) in 0..1.

Main API
    text_rgba(text, font_key, size_px, color, tracking=0, leading=1.2, align='left',
              max_width=None, uppercase=False, angle=0, ...) -> (rgba, meta)
    place(meta, x, y, anchor='origin') -> (left, top) integer paste position
    measure(text, font_key, size_px, tracking=0, ...) -> dict
    label_block(label, phrase, ...) -> (rgba, meta)       mono label over italic phrase
    leader(points, width, color, dot_at_end=True, ...) -> (rgba, (x, y))
    fill_contours(contours, h, w) -> float coverage        exact AA polygon fill
    stroke_polyline(points, width, ...) -> (coverage, (x, y))
    install_fonts(force=False)                             npm fetch + woff2 -> ttf
    build()                                                install fonts + write index
"""
from __future__ import annotations

import glob
import json
import math
import os
import shutil
import subprocess
import tarfile
from functools import lru_cache

import numpy as np
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FONT_DIR = os.path.join(ROOT, 'assets', 'fonts')
SCRATCH = os.path.join(ROOT, 'build', 'sensory')

INK = '#2B2420'

# --------------------------------------------------------------------------- #
# font registry
# --------------------------------------------------------------------------- #

# key: (npm package, fontsource file stem, output name, family, style, weight)
_FONT_SPECS = {
    'cg-400':   ('cormorant-garamond', '400-normal', 'CormorantGaramond-Regular', 'Cormorant Garamond', 'normal', 400),
    'cg-400i':  ('cormorant-garamond', '400-italic', 'CormorantGaramond-Italic', 'Cormorant Garamond', 'italic', 400),
    'cg-500i':  ('cormorant-garamond', '500-italic', 'CormorantGaramond-MediumItalic', 'Cormorant Garamond', 'italic', 500),
    'cg-300i':  ('cormorant-garamond', '300-italic', 'CormorantGaramond-LightItalic', 'Cormorant Garamond', 'italic', 300),
    'cg-600':   ('cormorant-garamond', '600-normal', 'CormorantGaramond-SemiBold', 'Cormorant Garamond', 'normal', 600),
    'plex-300': ('ibm-plex-mono', '300-normal', 'IBMPlexMono-Light', 'IBM Plex Mono', 'normal', 300),
    'plex-400': ('ibm-plex-mono', '400-normal', 'IBMPlexMono-Regular', 'IBM Plex Mono', 'normal', 400),
    'plex-500': ('ibm-plex-mono', '500-normal', 'IBMPlexMono-Medium', 'IBM Plex Mono', 'normal', 500),
}

ALIASES = {
    'serif': 'cg-400', 'italic': 'cg-400i', 'italic-medium': 'cg-500i', 'italic-light': 'cg-300i',
    'serif-semibold': 'cg-600', 'mono-light': 'plex-300', 'mono': 'plex-400', 'mono-medium': 'plex-500',
}

# weight-matched Inter fallback (Cormorant is optically lighter, so it maps one step down)
_INTER = {
    ('cg-400',): 'Inter-Light.otf', ('cg-400i',): 'Inter-LightItalic.otf',
    ('cg-500i',): 'Inter-Italic.otf', ('cg-300i',): 'Inter-ExtraLightItalic.otf',
    ('cg-600',): 'Inter-Medium.otf', ('plex-300',): 'Inter-Light.otf',
    ('plex-400',): 'Inter-Regular.otf', ('plex-500',): 'Inter-Medium.otf',
}
_INTER_FILES = sorted({v for v in _INTER.values()})
_INTER_SYS = '/usr/share/fonts/opentype/inter'

COVERAGE_CHECK = '·—–’‘“”…é→×°'


def font_key(key):
    k = ALIASES.get(key, key)
    if k not in _FONT_SPECS:
        raise KeyError(f'unknown font {key!r}; use one of {sorted(_FONT_SPECS) + sorted(ALIASES)}')
    return k


def font_path(key, ext=False):
    k = font_key(key)
    name = _FONT_SPECS[k][2]
    if ext:
        return os.path.join(FONT_DIR, 'latin-ext', name + '-LatinExt.ttf')
    return os.path.join(FONT_DIR, name + '.ttf')


def _inter_path(key):
    k = font_key(key)
    for ks, f in _INTER.items():
        if k in ks:
            return os.path.join(FONT_DIR, 'fallback', f)
    return os.path.join(FONT_DIR, 'fallback', 'Inter-Regular.otf')


# --------------------------------------------------------------------------- #
# installation (npm @fontsource -> .ttf) + index
# --------------------------------------------------------------------------- #

def install_fonts(force=False, log=print):
    """Fetch @fontsource packages with `npm pack`, convert the latin + latin-ext .woff2
    subsets of the needed styles to .ttf (pure format conversion, tables untouched),
    copy the OFL licences and the Inter fallback faces, then write index.json."""
    need = [font_path(k) for k in _FONT_SPECS] + [font_path(k, ext=True) for k in _FONT_SPECS]
    need += [os.path.join(FONT_DIR, 'fallback', f) for f in _INTER_FILES]
    if not force and all(os.path.exists(p) for p in need):
        write_font_index()
        return
    dl = os.path.join(SCRATCH, 'npm_fonts')
    shutil.rmtree(dl, ignore_errors=True)
    os.makedirs(dl)
    pkgs = sorted({s[0] for s in _FONT_SPECS.values()})
    for pkg in pkgs:
        subprocess.run(['npm', 'pack', f'@fontsource/{pkg}', '--silent'], cwd=dl, check=True,
                       stdout=subprocess.DEVNULL)
    os.makedirs(os.path.join(FONT_DIR, 'latin-ext'), exist_ok=True)
    os.makedirs(os.path.join(FONT_DIR, 'fallback'), exist_ok=True)
    for pkg in pkgs:
        tgz = glob.glob(os.path.join(dl, f'fontsource-{pkg}-*.tgz'))[0]
        xdir = os.path.join(dl, 'x_' + pkg)
        os.makedirs(xdir)
        with tarfile.open(tgz) as tf:
            members = [m for m in tf.getmembers() if m.isfile() and
                       (m.name.endswith('.woff2') or m.name.endswith('LICENSE')) and '..' not in m.name]
            tf.extractall(xdir, members=members, filter='data')
        lic = os.path.join(xdir, 'package', 'LICENSE')
        fam = {'cormorant-garamond': 'CormorantGaramond', 'ibm-plex-mono': 'IBMPlexMono'}[pkg]
        shutil.copyfile(lic, os.path.join(FONT_DIR, f'OFL-{fam}.txt'))
        for k, (p, stem, *_r) in _FONT_SPECS.items():
            if p != pkg:
                continue
            for sub, out in (('latin', font_path(k)), ('latin-ext', font_path(k, ext=True))):
                src = os.path.join(xdir, 'package', 'files', f'{pkg}-{sub}-{stem}.woff2')
                f = TTFont(src)
                f.flavor = None
                f.save(out)
                log(f'  font {os.path.relpath(out, ROOT)}')
    for f in _INTER_FILES:
        shutil.copyfile(os.path.join(_INTER_SYS, f), os.path.join(FONT_DIR, 'fallback', f))
    shutil.copyfile('/usr/share/doc/fonts-inter/copyright', os.path.join(FONT_DIR, 'OFL-Inter.txt'))
    _face.cache_clear()
    write_font_index()


def _coverage(face, chars=COVERAGE_CHECK):
    return ''.join(c for c in chars if ord(c) not in face.cmap)


def write_font_index():
    entries = []
    for k, (pkg, stem, _name, fam, style, wt) in _FONT_SPECS.items():
        f = _face(font_path(k))
        fe = _face(font_path(k, ext=True))
        al = [a for a, v in ALIASES.items() if v == k]
        miss = _coverage(f)
        miss_ext = ''.join(c for c in miss if ord(c) not in fe.cmap)
        entries.append({
            'key': k, 'aliases': al, 'path': os.path.relpath(font_path(k), ROOT),
            'latin_ext_path': os.path.relpath(font_path(k, ext=True), ROOT),
            'fallback_path': os.path.relpath(_inter_path(k), ROOT),
            'pixel_size': None, 'family': fam, 'style': style, 'weight': wt,
            'source': f'npm @fontsource/{pkg} (latin + latin-ext subsets, {stem}), woff2 -> ttf with fontTools, tables untouched',
            'licence': 'SIL OFL 1.1 — ' + ('assets/fonts/OFL-CormorantGaramond.txt' if pkg.startswith('cormorant')
                                           else 'assets/fonts/OFL-IBMPlexMono.txt'),
            'metrics_per_1000_em': {
                'units_per_em': f.upem, 'cap_height': round(f.cap * 1000 / f.upem),
                'x_height': round(f.xh * 1000 / f.upem), 'ascender': round(f.asc * 1000 / f.upem),
                'descender': round(f.desc * 1000 / f.upem)},
            'glyphs_latin': len(f.cmap), 'glyphs_latin_ext': len(fe.cmap),
            'coverage_check': COVERAGE_CHECK,
            'missing_in_latin_subset': miss,
            'missing_after_latin_ext': miss_ext,
            'fallback_strategy': ('-> and <- are synthesised at render time from the font\'s own up-arrow '
                                  'outline (rotated, mono shaft shortened to the 600-unit cell); anything else '
                                  'missing falls back to weight-matched Inter scaled to the cap height'),
            'description': f'{fam} {style} {wt}',
            'suggested_use': ('poetic sensory phrases / display (italic), titles (regular/semibold)'
                              if pkg.startswith('cormorant') else
                              'labels, captions, numbers — uppercase, tracked +60..120'),
        })
    idx = {
        'area': 'sensory / typeset',
        'module': 'src/lib/typeset.py (text_rgba, label_block, leader) + src/lib/sensory.py',
        'fonts': entries,
        'fallback_fonts': [{'path': f'assets/fonts/fallback/{f}', 'family': 'Inter',
                            'licence': 'SIL OFL 1.1 — assets/fonts/OFL-Inter.txt',
                            'use': 'last-resort per-glyph fallback only'} for f in _INTER_FILES],
        'notes': ('Font files are byte-faithful format conversions of the @fontsource subsets (no outline or '
                  'name changes; the arrows are synthesised in typeset.py at render time, so no Modified '
                  'Version of an OFL font is distributed). Text in the PSD is rasterised (layers named '
                  '"TXT · <text>").'),
    }
    os.makedirs(FONT_DIR, exist_ok=True)
    with open(os.path.join(FONT_DIR, 'index.json'), 'w') as fh:
        json.dump(idx, fh, indent=1, ensure_ascii=False)
    return idx


# --------------------------------------------------------------------------- #
# font face: cmap, metrics, outlines, kerning, GSUB
# --------------------------------------------------------------------------- #

class _FlatPen(BasePen):
    """Flattens glyph outlines into polygons (font units, y up)."""

    def __init__(self, glyphset, tol):
        super().__init__(glyphset)
        self.tol = tol
        self.contours = []
        self.cur = []

    def _moveTo(self, p):
        self._flush()
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        dev = math.hypot(p0[0] - 2 * p1[0] + p2[0], p0[1] - 2 * p1[1] + p2[1]) / 4
        n = max(2, int(math.ceil(math.sqrt(dev / self.tol))))
        t = np.linspace(0, 1, n + 1)[1:, None]
        a, b, c = (np.array(p, float) for p in (p0, p1, p2))
        pts = (1 - t) ** 2 * a + 2 * (1 - t) * t * b + t ** 2 * c
        self.cur.extend(map(tuple, pts))

    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        d1 = math.hypot(p0[0] - 2 * p1[0] + p2[0], p0[1] - 2 * p1[1] + p2[1])
        d2 = math.hypot(p1[0] - 2 * p2[0] + p3[0], p1[1] - 2 * p2[1] + p3[1])
        n = max(2, int(math.ceil(math.sqrt(0.75 * max(d1, d2) / self.tol))))
        t = np.linspace(0, 1, n + 1)[1:, None]
        a, b, c, d = (np.array(p, float) for p in (p0, p1, p2, p3))
        pts = (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t ** 2 * c + t ** 3 * d
        self.cur.extend(map(tuple, pts))

    def _closePath(self):
        self._flush()

    def _endPath(self):
        self._flush()

    def _flush(self):
        if len(self.cur) >= 3:
            self.contours.append(np.asarray(self.cur, np.float64))
        self.cur = []


_SYNTH = {0x2192: 'right', 0x2190: 'left'}


class Face:
    def __init__(self, path):
        self.path = path
        f = TTFont(path, lazy=False)
        self.font = f
        self.upem = f['head'].unitsPerEm
        os2 = f['OS/2']
        self.asc = os2.sTypoAscender
        self.desc = os2.sTypoDescender
        self.cap = getattr(os2, 'sCapHeight', 0) or int(self.upem * 0.7)
        self.xh = getattr(os2, 'sxHeight', 0) or int(self.upem * 0.48)
        self.cmap = f.getBestCmap()
        self.gs = f.getGlyphSet()
        self.hmtx = f['hmtx'].metrics
        self.mono = bool(f['post'].isFixedPitch) or len({w for w, _ in self.hmtx.values() if w}) <= 2
        self._kern_lookups = self._collect_gpos('kern')
        self._kcache = {}
        self._outline_cache = {}
        self._cov_cache = {}

    # -- GPOS kerning ------------------------------------------------------- #
    def _collect_gpos(self, tag):
        if 'GPOS' not in self.font:
            return []
        t = self.font['GPOS'].table
        idx = sorted({i for fr in t.FeatureList.FeatureRecord if fr.FeatureTag == tag
                      for i in fr.Feature.LookupListIndex})
        out = []
        for i in idx:
            lk = t.LookupList.Lookup[i]
            sts = []
            for st in lk.SubTable:
                typ = lk.LookupType
                if typ == 9:
                    typ, st = st.ExtensionLookupType, st.ExtSubTable
                if typ == 2:
                    sts.append(st)
            if sts:
                out.append(sts)
        return out

    def _cov(self, st):
        c = self._cov_cache.get(id(st))
        if c is None:
            c = {g: i for i, g in enumerate(st.Coverage.glyphs)}
            if st.Format == 1:
                c = (c, [{r.SecondGlyph: r.Value1 for r in ps.PairValueRecord} for ps in st.PairSet])
            else:
                c = (c, None)
            self._cov_cache[id(st)] = c
        return c

    def kern(self, a, b):
        key = (a, b)
        v = self._kcache.get(key)
        if v is not None:
            return v
        total = 0
        for sts in self._kern_lookups:
            for st in sts:
                cov, pairs = self._cov(st)
                if a not in cov:
                    continue
                if st.Format == 1:
                    vr = pairs[cov[a]].get(b)
                    if vr is None:
                        continue
                else:
                    c1 = st.ClassDef1.classDefs.get(a, 0) if st.ClassDef1 else 0
                    c2 = st.ClassDef2.classDefs.get(b, 0) if st.ClassDef2 else 0
                    vr = st.Class1Record[c1].Class2Record[c2].Value1
                total += (getattr(vr, 'XAdvance', 0) or 0) if vr is not None else 0
                break
        self._kcache[key] = total
        return total

    # -- GSUB ---------------------------------------------------------------- #
    @lru_cache(maxsize=None)
    def _gsub_lookups(self, tag):
        if 'GSUB' not in self.font:
            return ()
        t = self.font['GSUB'].table
        idx = sorted({i for fr in t.FeatureList.FeatureRecord if fr.FeatureTag == tag
                      for i in fr.Feature.LookupListIndex})
        out = []
        for i in idx:
            lk = t.LookupList.Lookup[i]
            for st in lk.SubTable:
                typ = lk.LookupType
                if typ == 7:
                    typ, st = st.ExtensionLookupType, st.ExtSubTable
                if typ in (1, 4):
                    out.append((typ, st))
        return tuple(out)

    def substitute(self, names, features):
        """Apply single (type 1) and ligature (type 4) substitutions for `features`."""
        names = list(names)
        for tag in features:
            for typ, st in self._gsub_lookups(tag):
                if typ == 1:
                    names = [st.mapping.get(n, n) if n is not None else None for n in names]
                else:
                    out, i = [], 0
                    while i < len(names):
                        n = names[i]
                        done = False
                        for lig in (st.ligatures.get(n, ()) if n is not None else ()):
                            k = len(lig.Component)
                            if names[i + 1:i + 1 + k] == list(lig.Component):
                                out.append(lig.LigGlyph)
                                i += 1 + k
                                done = True
                                break
                        if not done:
                            out.append(n)
                            i += 1
                    names = out
        return names

    # -- glyphs -------------------------------------------------------------- #
    def glyph(self, ch):
        cp = ord(ch)
        g = self.cmap.get(cp)
        if g is not None:
            return g
        if cp in _SYNTH and 0x2191 in self.cmap:
            return '__arrow_' + _SYNTH[cp]
        return None

    def advance(self, g):
        if g.startswith('__arrow_'):
            return self._synth_arrow(g)[1]
        return self.hmtx[g][0]

    def outline(self, g, tol):
        """Flattened contours of glyph g in font units (y up)."""
        key = (g, round(tol, 3))
        c = self._outline_cache.get(key)
        if c is None:
            if g.startswith('__arrow_'):
                c = self._synth_arrow(g, tol)[0]
            else:
                pen = _FlatPen(self.gs, tol)
                self.gs[g].draw(pen)
                c = pen.contours
            self._outline_cache[key] = c
        return c

    def _synth_arrow(self, g, tol=0.5):
        """-> / <- built from the font's own up-arrow: rotated +-90 deg, centred on the
        en-dash axis; in monospaced faces the shaft is shortened to fit the cell."""
        up = self.cmap[0x2191]
        pen = _FlatPen(self.gs, tol)
        self.gs[up].draw(pen)
        cs = [c.copy() for c in pen.contours]
        allp = np.concatenate(cs)
        xmin, ymin = allp.min(0)
        xmax, ymax = allp.max(0)
        xc = (xmin + xmax) / 2
        dash = self.cmap.get(0x2013) or self.cmap.get(0x2D)
        dpen = _FlatPen(self.gs, tol)
        self.gs[dash].draw(dpen)
        dp = np.concatenate(dpen.contours)
        yaxis = (dp[:, 1].min() + dp[:, 1].max()) / 2
        side = max(20.0, float(dp[:, 0].min()))
        length = ymax - ymin
        adv_up = self.hmtx[up][0]
        if self.mono:
            target = adv_up - 2 * side
            if length > target:  # shorten the shaft: move the tail end of the outline
                tail = ymin + 0.12 * length
                for c in cs:
                    c[c[:, 1] <= tail, 1] += length - target
                length = target
                ymin = ymin + (ymax - ymin - target)
            adv = adv_up
        else:
            adv = length + 2 * side
        out = []
        for c in cs:
            x, y = c[:, 0], c[:, 1]
            if g.endswith('right'):
                nx, ny = (y - ymin) + (adv - length) / 2, xc - x + yaxis
            else:
                nx, ny = (ymax - y) + (adv - length) / 2, x - xc + yaxis
            out.append(np.stack([nx, ny], 1))
        return out, adv


@lru_cache(maxsize=None)
def _face(path):
    return Face(path)


def _faces(key):
    k = font_key(key)
    p = font_path(k)
    if not os.path.exists(p):
        install_fonts()
    chain = [_face(p)]
    pe = font_path(k, ext=True)
    if os.path.exists(pe):
        chain.append(_face(pe))
    pi = _inter_path(k)
    if os.path.exists(pi):
        chain.append(_face(pi))
    return chain


# --------------------------------------------------------------------------- #
# exact-coverage rasteriser
# --------------------------------------------------------------------------- #

def fill_contours(contours, h, w, ss=8, band_rows=4096):
    """Rasterise closed polygons (list of (N, 2) arrays, pixel coords, y down) with the
    non-zero winding rule.  Coverage is analytic along x and supersampled `ss`x along y.
    Pixel (i, j) covers [j, j+1) x [i, i+1).  Returns float32 (h, w) in 0..1."""
    h, w = int(h), int(w)
    out = np.zeros((h, w), np.float32)
    segs = []
    for c in contours:
        p = np.asarray(c, np.float64)
        if len(p) < 3:
            continue
        q = np.roll(p, -1, axis=0)
        segs.append(np.concatenate([p, q], 1))
    if not segs or h <= 0 or w <= 0:
        return out
    E = np.concatenate(segs)
    E = E[E[:, 1] != E[:, 3]]
    if not len(E):
        return out
    d = np.where(E[:, 3] > E[:, 1], 1.0, -1.0)
    ya = np.minimum(E[:, 1], E[:, 3])
    yb = np.maximum(E[:, 1], E[:, 3])
    R = h * ss
    r0 = np.clip(np.ceil(ya * ss - 0.5), 0, R).astype(np.int64)
    r1 = np.clip(np.ceil(yb * ss - 0.5), 0, R).astype(np.int64)
    n = r1 - r0
    keep = n > 0
    E, d, r0, n = E[keep], d[keep], r0[keep], n[keep]
    if not len(E):
        return out
    tot = int(n.sum())
    ei = np.repeat(np.arange(len(E)), n)
    r = r0[ei] + (np.arange(tot) - np.repeat(np.cumsum(n) - n, n))
    ys = (r + 0.5) / ss
    x0, y0, x1, y1 = E[ei, 0], E[ei, 1], E[ei, 2], E[ei, 3]
    xs = x0 + (ys - y0) / (y1 - y0) * (x1 - x0)
    dd = d[ei]
    del ei, x0, y0, x1, y1, ys
    xs = np.clip(xs, 0.0, w + 1.0)
    ix = np.floor(xs).astype(np.int64)
    f = xs - ix
    ix = np.minimum(ix, w + 1)
    W2 = w + 2
    order = np.argsort(r, kind='stable')
    r, ix, f, dd = r[order], ix[order], f[order], dd[order]
    step = max(ss, (band_rows // ss) * ss)
    for b0 in range(0, R, step):
        b1 = min(R, b0 + step)
        lo, hi = np.searchsorted(r, b0), np.searchsorted(r, b1)
        nb = b1 - b0
        if hi > lo:
            rr = r[lo:hi] - b0
            k = rr * W2 + ix[lo:hi]
            acc = np.bincount(k, weights=dd[lo:hi] * (1 - f[lo:hi]), minlength=nb * W2)
            k2 = np.minimum(k + 1, rr * W2 + W2 - 1)
            acc += np.bincount(k2, weights=dd[lo:hi] * f[lo:hi], minlength=nb * W2)
            acc = acc.reshape(nb, W2)
            cov = np.minimum(np.abs(np.cumsum(acc, axis=1)), 1.0)[:, :w]
            out[b0 // ss:b1 // ss] = cov.reshape(nb // ss, ss, w).mean(1)
    return out


def stroke_polyline(points, width, alpha=None, dash=None, closed=False, pad=2, box=None):
    """Anti-aliased stroke of a polyline using exact box-filtered distance coverage
    (round joins/caps).  `width` and `alpha` may be scalars or per-vertex arrays (taper /
    fade).  dash=(on, off[, phase]) in px along the arc.  Returns (coverage float32, (x0, y0))
    where (x0, y0) is the canvas offset of the coverage window (or the given box)."""
    P = np.asarray(points, np.float64)
    if closed:
        P = np.vstack([P, P[:1]])
    n = len(P)
    wv = np.broadcast_to(np.asarray(width, np.float64), (n,)).copy()
    av = np.ones(n) if alpha is None else np.broadcast_to(np.asarray(alpha, np.float64), (n,)).copy()
    seg = np.diff(P, axis=0)
    L = np.hypot(seg[:, 0], seg[:, 1])
    S = np.concatenate([[0], np.cumsum(L)])
    hw = wv.max() / 2 + 1.5
    if box is None:
        x0 = int(math.floor(P[:, 0].min() - hw - pad))
        y0 = int(math.floor(P[:, 1].min() - hw - pad))
        x1 = int(math.ceil(P[:, 0].max() + hw + pad))
        y1 = int(math.ceil(P[:, 1].max() + hw + pad))
    else:
        x0, y0, x1, y1 = box
    H, Wd = y1 - y0, x1 - x0
    cov = np.zeros((H, Wd), np.float32)
    for i in range(n - 1):
        a, b = P[i], P[i + 1]
        r = max(wv[i], wv[i + 1]) / 2 + 1.0
        bx0 = max(0, int(math.floor(min(a[0], b[0]) - r)) - x0)
        by0 = max(0, int(math.floor(min(a[1], b[1]) - r)) - y0)
        bx1 = min(Wd, int(math.ceil(max(a[0], b[0]) + r)) - x0 + 1)
        by1 = min(H, int(math.ceil(max(a[1], b[1]) + r)) - y0 + 1)
        if bx1 <= bx0 or by1 <= by0:
            continue
        gx = np.arange(bx0, bx1, dtype=np.float64) + x0 + 0.5
        gy = np.arange(by0, by1, dtype=np.float64)[:, None] + y0 + 0.5
        ab = b - a
        ll = ab @ ab
        if ll < 1e-12:
            t = np.zeros((len(gy), len(gx)))
        else:
            t = np.clip(((gx - a[0]) * ab[0] + (gy - a[1]) * ab[1]) / ll, 0, 1)
        dx = gx - (a[0] + t * ab[0])
        dy = gy - (a[1] + t * ab[1])
        dist = np.sqrt(dx * dx + dy * dy)
        ww = wv[i] + t * (wv[i + 1] - wv[i])
        c = np.clip((ww + 1) / 2 - dist, 0, np.minimum(ww, 1.0))
        c *= av[i] + t * (av[i + 1] - av[i])
        if dash is not None:
            on, off = dash[0], dash[1]
            ph = dash[2] if len(dash) > 2 else 0.0
            per = on + off
            s = (S[i] + t * L[i] + ph) % per
            # box-filtered dash along the arc (+ the start of the next dash near the wrap)
            c *= np.maximum(np.clip(np.minimum(s + 0.5, on + 0.5 - s), 0, 1),
                            np.clip(s - per + 0.5, 0, 1))
        sub = cov[by0:by1, bx0:bx1]
        np.maximum(sub, c.astype(np.float32), out=sub)
    return cov, (x0, y0)


def disc_coverage(cx, cy, r, h, w, x0=0, y0=0):
    """Exact-ish AA disc coverage on a (h, w) window whose top-left is canvas (x0, y0)."""
    gx = np.arange(w, dtype=np.float32) + x0 + 0.5 - cx
    gy = np.arange(h, dtype=np.float32)[:, None] + y0 + 0.5 - cy
    d = np.sqrt(gx * gx + gy * gy)
    return np.clip(r + 0.5 - d, 0, min(1.0, 2 * r)).astype(np.float32)


def _rgb(color):
    if isinstance(color, str):
        c = color.lstrip('#')
        return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0
    c = np.asarray(color, np.float32)
    return c / 255.0 if c.max() > 1.0 else c


def colorize(cov, color, opacity=1.0):
    out = np.empty(cov.shape + (4,), np.float32)
    out[..., :3] = _rgb(color)
    out[..., 3] = cov * opacity
    return out


def over(dst, src, x=0, y=0):
    """Straight-alpha 'over' of src onto dst (both float RGBA) at offset (x, y), in place."""
    h, w = src.shape[:2]
    H, W = dst.shape[:2]
    sx0, sy0 = max(0, -x), max(0, -y)
    dx0, dy0 = max(0, x), max(0, y)
    ww, hh = min(w - sx0, W - dx0), min(h - sy0, H - dy0)
    if ww <= 0 or hh <= 0:
        return dst
    s = src[sy0:sy0 + hh, sx0:sx0 + ww]
    d = dst[dy0:dy0 + hh, dx0:dx0 + ww]
    sa = s[..., 3:4]
    da = d[..., 3:4]
    oa = sa + da * (1 - sa)
    rgb = (s[..., :3] * sa + d[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6)
    d[..., :3] = np.where(oa > 1e-6, rgb, d[..., :3])
    d[..., 3:4] = oa
    return dst


# --------------------------------------------------------------------------- #
# shaping + layout
# --------------------------------------------------------------------------- #

def _shape(text, key, size_px, tracking=0.0, features=None, kern=True):
    """Glyph run for one line: list of (face, glyph, x_px, scale) + advance width (px).
    Tracking is in 1/1000 em, applied between glyphs (not after the last one), on top of
    the font's kerning."""
    chain = _faces(key)
    prim = chain[0]
    s0 = size_px / prim.upem
    feats = features if features is not None else _default_features(text, tracking)
    # map characters to (face, glyph)
    runs = []
    for ch in text:
        face, g = None, None
        for fc in chain:
            g = fc.glyph(ch)
            if g is not None:
                face = fc
                break
        if face is None:
            face, g = prim, '.notdef'
        runs.append([face, g])
    # GSUB on maximal runs of primary-face glyphs
    if feats:
        out, i = [], 0
        while i < len(runs):
            if runs[i][0] is prim and not runs[i][1].startswith('__'):
                j = i
                while j < len(runs) and runs[j][0] is prim and not runs[j][1].startswith('__'):
                    j += 1
                names = prim.substitute([r[1] for r in runs[i:j]], feats)
                out.extend([[prim, nm] for nm in names if nm is not None])
                i = j
            else:
                out.append(runs[i])
                i += 1
        runs = out
    glyphs = []
    x = 0.0
    trk = tracking / 1000.0 * size_px
    for k, (face, g) in enumerate(runs):
        if face is prim or face.upem == prim.upem and face.cap == prim.cap:
            sc = s0 * prim.upem / face.upem
        else:  # foreign fallback: match the cap height
            sc = s0 * prim.cap / face.cap
        glyphs.append((face, g, x, sc))
        x += face.advance(g) * sc
        if k + 1 < len(runs):
            nf, ng = runs[k + 1]
            if kern and nf is face and not g.startswith('__') and not ng.startswith('__'):
                x += face.kern(g, ng) * sc
            x += trk
    return glyphs, x


def _default_features(text, tracking):
    f = []
    if abs(tracking) < 15:
        f.append('liga')
    letters = [c for c in text if c.isalpha()]
    if letters and all(c.isupper() for c in letters):
        f.append('lnum')
    return f


def _wrap(text, key, size_px, tracking, max_width, features):
    lines = []
    for para in text.split('\n'):
        if max_width is None:
            lines.append(para)
            continue
        words = para.split(' ')
        cur = ''
        for wd in words:
            cand = wd if not cur else cur + ' ' + wd
            if cur and _shape(cand, key, size_px, tracking, features)[1] > max_width:
                lines.append(cur)
                cur = wd
            else:
                cur = cand
        lines.append(cur)
    return lines


def measure(text, font_key_, size_px, tracking=0, uppercase=False, features=None):
    """Advance width and font metrics (px) of a single line, without rendering."""
    if uppercase:
        text = text.upper()
    prim = _faces(font_key_)[0]
    g, wdt = _shape(text, font_key_, size_px, tracking, features)
    s = size_px / prim.upem
    return {'width': wdt, 'cap_height': prim.cap * s, 'x_height': prim.xh * s,
            'ascender': prim.asc * s, 'descender': -prim.desc * s, 'n_glyphs': len(g)}


def _layout(text, key, size_px, tracking=0, leading=1.2, align='left', max_width=None,
            uppercase=False, features=None):
    """Returns contours (pen space, px, y down, origin = alignment anchor on the first
    baseline) and a meta dict (unrotated)."""
    if uppercase:
        text = text.upper()
    prim = _faces(key)[0]
    s = size_px / prim.upem
    lh = leading * size_px
    lines = _wrap(text, key, size_px, tracking, max_width, features)
    contours = []
    widths, starts = [], []
    tol_px = 0.04
    for li, line in enumerate(lines):
        glyphs, wdt = _shape(line, key, size_px, tracking, features)
        x0 = {'left': 0.0, 'center': -wdt / 2, 'right': -wdt}[align]
        by = li * lh
        widths.append(wdt)
        starts.append(x0)
        for face, g, gx, sc in glyphs:
            for c in face.outline(g, tol_px / sc):
                pts = np.empty_like(c)
                pts[:, 0] = x0 + gx + c[:, 0] * sc
                pts[:, 1] = by - c[:, 1] * sc
                contours.append(pts)
    meta = {
        'font': font_key(key), 'size_px': size_px, 'tracking': tracking, 'leading': leading,
        'align': align, 'lines': lines, 'line_widths': widths, 'line_starts': starts,
        'baselines': [i * lh for i in range(len(lines))], 'line_height': lh,
        'width': max(widths) if widths else 0.0,
        'cap_height': prim.cap * s, 'x_height': prim.xh * s,
        'ascender': prim.asc * s, 'descender': -prim.desc * s,
    }
    return contours, meta


def _rot(theta_deg):
    t = math.radians(theta_deg)
    c, s_ = math.cos(t), math.sin(t)
    # visual counter-clockwise rotation in y-down coordinates
    return np.array([[c, s_], [-s_, c]])


def _render_items(items, angle=0.0, pad=3, subpixel=(0.0, 0.0), ss=None, size_hint=40):
    """items: list of (contours_pen_space, color, opacity).  Shares one pen space; returns
    (rgba, M) with M the 2x3 pen->image matrix."""
    Rm = _rot(angle)
    allc = [np.asarray(c) @ Rm.T for cs, _, _ in items for c in cs]
    if allc:
        pts = np.concatenate(allc)
        mn, mx = pts.min(0), pts.max(0)
    else:
        mn = mx = np.zeros(2)
    sx, sy = subpixel
    ox = -int(math.floor(mn[0] + sx)) + pad
    oy = -int(math.floor(mn[1] + sy)) + pad
    W = int(math.ceil(mx[0] + sx)) + ox + pad
    H = int(math.ceil(mx[1] + sy)) + oy + pad
    W, H = max(W, 1), max(H, 1)
    T = np.array([ox + sx, oy + sy])
    if ss is None:
        ss = 16 if size_hint < 48 else 8
    out = np.zeros((H, W, 4), np.float32)
    for cs, color, op in items:
        cc = [np.asarray(c) @ Rm.T + T for c in cs]
        cov = fill_contours(cc, H, W, ss=ss)
        over(out, colorize(cov, color, op))
    M = np.hstack([Rm, T[:, None]])
    return out, M


def _finish_meta(meta, M, contours):
    def tf(p):
        p = np.asarray(p, np.float64)
        return tuple((M[:, :2] @ p + M[:, 2]).tolist())
    o = tf((0, 0))
    meta['origin'] = (int(round(o[0])), int(round(o[1])))
    meta['origin_exact'] = o
    meta['matrix'] = M.tolist()
    meta['angle'] = float(math.degrees(math.atan2(-M[1, 0], M[0, 0])))
    if contours:
        pts = np.concatenate(contours)
        mn, mx = pts.min(0), pts.max(0)
        meta['ink_box_pen'] = (float(mn[0]), float(mn[1]), float(mx[0]), float(mx[1]))
        ip = np.concatenate([np.asarray(c) @ M[:, :2].T + M[:, 2] for c in contours])
        a, b = ip.min(0), ip.max(0)
        meta['ink_box'] = (float(a[0]), float(a[1]), float(b[0]), float(b[1]))
    else:
        meta['ink_box_pen'] = meta['ink_box'] = (0.0, 0.0, 0.0, 0.0)
    ls = meta['line_starts']
    bl = meta['baselines']
    lw = meta['line_widths']
    ib = meta['ink_box_pen']
    meta['anchors'] = {
        'origin': o,
        'baseline_left': tf((ls[0], bl[0])), 'baseline_right': tf((ls[0] + lw[0], bl[0])),
        'cap_top_left': tf((ls[0], bl[0] - meta['cap_height'])),
        'x_top_left': tf((ls[0], bl[0] - meta['x_height'])),
        'last_baseline_left': tf((ls[-1], bl[-1])),
        'ink_center': tf(((ib[0] + ib[2]) / 2, (ib[1] + ib[3]) / 2)),
        'ink_left_baseline': tf((ib[0], bl[0])),
    }
    return meta


def text_rgba(text, font_key, size_px, color=INK, tracking=0, leading=1.2, align='left',
              max_width=None, uppercase=False, angle=0.0, features=None, opacity=1.0,
              pad=3, subpixel=(0.0, 0.0), ss=None):
    """Render text to straight-alpha RGBA (float32) + placement metadata.

    tracking  letter-spacing in 1/1000 em, added on top of the font's GPOS kerning
    leading   baseline-to-baseline distance as a multiple of size_px
    align     'left' | 'center' | 'right' (the anchor is the left end / centre / right end
              of the first baseline)
    max_width wrap width in px (greedy, on spaces); '\\n' always breaks
    angle     degrees, counter-clockwise, about the anchor; outlines are rotated before
              rasterisation
    features  list of OpenType feature tags (GSUB single/ligature: 'liga', 'lnum', 'pnum',
              'tnum', ...); default = liga when |tracking| < 15, lnum for all-caps text
    Returns (rgba, meta).  meta['origin'] = integer pixel of the anchor inside rgba, so
    paste at (X - ox, Y - oy) to put the first baseline anchor exactly on canvas (X, Y)
    (see place()).  meta also has baselines / line widths / cap_height / x_height /
    ascender / descender (px), ink_box (image px), ink_box_pen (pen px, relative to the
    anchor, unrotated) and named anchors (image px)."""
    contours, meta = _layout(text, font_key, size_px, tracking, leading, align, max_width,
                             uppercase, features)
    rgba, M = _render_items([(contours, color, opacity)], angle, pad, subpixel, ss, size_px)
    meta = _finish_meta(meta, M, contours)
    meta['size'] = (rgba.shape[1], rgba.shape[0])
    return rgba, meta


def place(meta, x, y, anchor='origin'):
    """Top-left paste position so that `anchor` (a key of meta['anchors']) lands on
    canvas (x, y).  Rounded to whole pixels."""
    ax, ay = meta['anchors'][anchor] if anchor != 'origin' else meta['origin']
    return int(round(x - ax)), int(round(y - ay))


def label_block(label, phrase, label_key='mono', phrase_key='italic', label_size=30,
                phrase_size=64, color=INK, label_color=None, label_tracking=110,
                phrase_tracking=0, gap=None, align='left', max_width=None, phrase_leading=1.12,
                rule=0.0, rule_gap=None, rule_width=1.6, angle=0.0, opacity=1.0, pad=3):
    """Stacked annotation: small tracked uppercase mono label over an italic serif phrase.

    gap       label baseline -> phrase cap-top distance (default 0.55 x label size + a bit)
    rule      length (px) of an optional hairline dash drawn before the label
              ("— SOUND"), vertically centred on the label's cap height
    Returns (rgba, meta): meta['origin'] is the label baseline anchor (left end for
    align='left'), meta['anchors'] adds 'phrase_baseline' and 'label_baseline'."""
    lc = label_color or color
    lab_c, lab_m = _layout(label, label_key, label_size, label_tracking, 1.2, align, None, True)
    gap = (0.62 * label_size + 0.2 * phrase_size) if gap is None else gap
    ph_c, ph_m = _layout(phrase, phrase_key, phrase_size, phrase_tracking, phrase_leading, align,
                         max_width, False)
    dy = gap + ph_m['cap_height']
    ph_c = [c + np.array([0.0, dy]) for c in ph_c]
    items = [(lab_c, lc, opacity), (ph_c, color, opacity)]
    rule_c = []
    if rule:
        rg = rule_gap if rule_gap is not None else 0.6 * label_size
        yc = -lab_m['cap_height'] / 2
        x1 = lab_m['line_starts'][0] - rg
        x0 = x1 - rule
        hw = rule_width / 2
        rule_c = [np.array([[x0, yc - hw], [x1, yc - hw], [x1, yc + hw], [x0, yc + hw]])]
        items.append((rule_c, lc, opacity))
    rgba, M = _render_items(items, angle, pad, (0, 0), None, label_size)
    meta = dict(lab_m)
    meta['phrase'] = ph_m
    meta['phrase_dy'] = dy
    meta = _finish_meta(meta, M, lab_c + ph_c + rule_c)
    tf = lambda p: tuple((M[:, :2] @ np.asarray(p, float) + M[:, 2]).tolist())  # noqa: E731
    meta['anchors']['label_baseline'] = tf((lab_m['line_starts'][0], 0))
    meta['anchors']['phrase_baseline'] = tf((ph_m['line_starts'][0], dy))
    meta['anchors']['phrase_last_baseline'] = tf((ph_m['line_starts'][-1], dy + ph_m['baselines'][-1]))
    if rule:
        meta['anchors']['rule_start'] = tf((rule_c[0][0, 0], -lab_m['cap_height'] / 2))
    meta['size'] = (rgba.shape[1], rgba.shape[0])
    return rgba, meta


def leader(points, width=2.0, color=INK, dot_at_end=True, dot_r=None, dot_at_start=False,
           start_r=None, opacity=1.0, dash=None, smooth=False, ring_at_end=False):
    """Hairline leader line through canvas points [(x, y), ...] with an optional dot at the
    end (and/or start).  ring_at_end draws an open circle instead of a filled dot.
    smooth=True passes a Catmull-Rom spline through the points.
    Returns (rgba, (x, y)) — paste the image with its top-left at canvas (x, y)."""
    P = np.asarray(points, np.float64)
    if smooth and len(P) > 2:
        P = catmull_rom(P, spacing=2.0)
    dr = dot_r if dot_r is not None else max(3.0, 2.6 * width)
    sr = start_r if start_r is not None else dr
    margin = max(dr, sr) + width + 3
    x0 = int(math.floor(P[:, 0].min() - margin))
    y0 = int(math.floor(P[:, 1].min() - margin))
    x1 = int(math.ceil(P[:, 0].max() + margin))
    y1 = int(math.ceil(P[:, 1].max() + margin))
    cov, _ = stroke_polyline(P, width, dash=dash, box=(x0, y0, x1, y1))
    h, w = cov.shape
    for flag, (cx, cy), r in ((dot_at_end, P[-1], dr), (dot_at_start, P[0], sr)):
        if not flag:
            continue
        if ring_at_end and flag is dot_at_end:
            ring, _ = stroke_polyline(_circle(cx, cy, r, 96), width, closed=True, box=(x0, y0, x1, y1))
            # knock the line out inside the ring
            inside = disc_coverage(cx, cy, r - width / 2, h, w, x0, y0)
            cov = np.maximum(cov * (1 - inside), ring)
        else:
            cov = np.maximum(cov, disc_coverage(cx, cy, r, h, w, x0, y0))
    return colorize(cov, color, opacity), (x0, y0)


def _circle(cx, cy, r, n=128):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([cx + r * np.cos(t), cy + r * np.sin(t)], 1)


def catmull_rom(points, spacing=2.0, alpha=0.5, closed=False):
    """Centripetal Catmull-Rom spline through points, resampled to ~`spacing` px."""
    P = np.asarray(points, np.float64)
    if len(P) < 3:
        return resample(P, spacing)
    if closed:
        Q = np.vstack([P[-1:], P, P[:2]])
    else:
        Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-6) ** alpha
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-6) ** alpha
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-6) ** alpha
        m = max(4, int(np.linalg.norm(p2 - p1) / max(spacing / 2, 0.25)))
        t = np.linspace(t1, t2, m, endpoint=False)[:, None]
        a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
        b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
        out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(P[-1:] if not closed else P[:1])
    return resample(np.vstack(out), spacing)


def resample(P, spacing):
    P = np.asarray(P, np.float64)
    if len(P) < 2:
        return P
    L = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))])
    if L[-1] <= 0:
        return P[:1]
    n = max(2, int(math.ceil(L[-1] / spacing)) + 1)
    s = np.linspace(0, L[-1], n)
    return np.stack([np.interp(s, L, P[:, 0]), np.interp(s, L, P[:, 1])], 1)


def build():
    install_fonts()
    return write_font_index()
