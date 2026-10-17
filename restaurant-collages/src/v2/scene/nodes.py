"""nodes — a small helper layer over Blender's shader node API, plus every material of the scene.

All materials are procedural (Cycles shader nodes) or driven by height / colour maps that
`textures.py` synthesises in numpy. No photographs and no generated imagery.

    m = material('travertine')      # cached: one bpy material per name
"""
from __future__ import annotations

import os

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
TEX = os.path.join(ROOT, 'build', 'v2', 'tex')


# ----------------------------------------------------------------------------------------------
# node-building helpers
class G:
    """Wraps a node tree: G(nt).n('TexNoise', Scale=4) -> node; g.l(a.outputs[0], b.inputs['X'])."""

    def __init__(self, nt):
        self.nt = nt
        self.x = 0

    def n(self, kind, _props=None, **inputs):
        node = self.nt.nodes.new(kind if kind.startswith(('Shader', 'Node')) else 'ShaderNode' + kind)
        node.location = (self.x, 0)
        self.x += 200
        for k, v in (_props or {}).items():
            setattr(node, k, v)
        for k, v in inputs.items():
            self.set(node, k, v)
        return node

    def sock(self, node, name, out=False):
        socks = node.outputs if out else node.inputs
        for s in socks:                         # identifier first (Mix node has duplicate names)
            if s.identifier == name and s.enabled:
                return s
        for s in socks:
            if s.name == name and s.enabled:
                return s
        for s in socks:
            if s.name == name:
                return s
        raise KeyError(f'{node.bl_idname}: no socket {name!r}')

    def set(self, node, name, v):
        s = self.sock(node, name)
        if isinstance(v, bpy.types.NodeSocket):
            self.nt.links.new(v, s)
        else:
            if isinstance(v, (tuple, list)) and len(v) == 3 and s.type == 'RGBA':
                v = (*v, 1.0)
            s.default_value = v

    def o(self, node, name=None):
        if name is None:
            return [s for s in node.outputs if s.enabled][0]
        return self.sock(node, name, out=True)

    def l(self, a, b):
        self.nt.links.new(a, b)

    # common compound nodes ------------------------------------------------------------------
    def mix(self, fac, a, b, blend='MIX', clamp=True):
        m = self.n('Mix', {'data_type': 'RGBA', 'blend_type': blend, 'clamp_result': clamp})
        self.set(m, 'Factor_Float', fac)
        self.set(m, 'A_Color', a)
        self.set(m, 'B_Color', b)
        return self.o(m, 'Result_Color')

    def mixf(self, fac, a, b):
        m = self.n('Mix', {'data_type': 'FLOAT'})
        self.set(m, 'Factor_Float', fac)
        self.set(m, 'A_Float', a)
        self.set(m, 'B_Float', b)
        return self.o(m, 'Result_Float')

    def math(self, op, a, b=0.0, clamp=False):
        m = self.n('Math', {'operation': op, 'use_clamp': clamp})
        for sock, v in ((m.inputs[0], a), (m.inputs[1], b)):
            if isinstance(v, bpy.types.NodeSocket):
                self.nt.links.new(v, sock)
            else:
                sock.default_value = v
        return m.outputs[0]

    def vmath(self, op, a, b=(0, 0, 0)):
        m = self.n('VectorMath', {'operation': op})
        self.l(a, m.inputs[0]) if isinstance(a, bpy.types.NodeSocket) else setattr(m.inputs[0], 'default_value', a)
        self.l(b, m.inputs[1]) if isinstance(b, bpy.types.NodeSocket) else setattr(m.inputs[1], 'default_value', b)
        return m.outputs[0]

    def ramp(self, fac, stops, interp='LINEAR'):
        r = self.n('ValToRGB')
        r.color_ramp.interpolation = interp
        els = r.color_ramp.elements
        while len(els) > 1:
            els.remove(els[-1])
        els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
        for p, c in stops[1:]:
            e = els.new(p)
            e.color = (*c, 1)
        self.l(fac, r.inputs['Fac'])
        return r.outputs['Color'], r.outputs['Alpha']

    def maprange(self, v, a0, a1, b0=0.0, b1=1.0, clamp=True, interp='LINEAR'):
        m = self.n('MapRange', {'interpolation_type': interp, 'clamp': clamp})
        self.set(m, 'Value', v)
        self.set(m, 'From Min', a0)
        self.set(m, 'From Max', a1)
        self.set(m, 'To Min', b0)
        self.set(m, 'To Max', b1)
        return m.outputs['Result']

    def coord(self, kind='Object', scale=(1, 1, 1), rot=(0, 0, 0), loc=(0, 0, 0)):
        tc = self.n('TexCoord')
        mp = self.n('Mapping', Scale=scale, Rotation=rot, Location=loc)
        self.l(tc.outputs[kind], mp.inputs['Vector'])
        return mp.outputs['Vector']

    def noise(self, vec, scale=5.0, detail=4.0, rough=0.55, dist=0.0, dims='3D', kind='FBM', lac=2.0):
        nz = self.n('TexNoise', {'noise_dimensions': dims, 'noise_type': kind},
                    Scale=scale, Detail=detail, Roughness=rough, Distortion=dist, Lacunarity=lac)
        if vec is not None:
            self.l(vec, nz.inputs['Vector'])
        return nz

    def voronoi(self, vec, scale=5.0, feature='F1', rand=1.0, metric='EUCLIDEAN', dims='3D'):
        v = self.n('TexVoronoi', {'feature': feature, 'distance': metric, 'voronoi_dimensions': dims},
                   Scale=scale, Randomness=rand)
        if vec is not None:
            self.l(vec, v.inputs['Vector'])
        return v

    def bump(self, h, strength=0.3, dist=0.01, normal=None):
        b = self.n('Bump', Strength=strength, Distance=dist)
        self.l(h, b.inputs['Height'])
        if normal is not None:
            self.l(normal, b.inputs['Normal'])
        return b.outputs['Normal']

    def image(self, path, vec=None, colorspace='sRGB', interp='Cubic', ext='REPEAT'):
        img = bpy.data.images.load(path, check_existing=True)
        img.colorspace_settings.name = colorspace
        t = self.n('TexImage', {'interpolation': interp, 'extension': ext})
        t.image = img
        if vec is not None:
            self.l(vec, t.inputs['Vector'])
        return t

    def principled(self, **kw):
        p = self.n('BsdfPrincipled')
        names = {'base': 'Base Color', 'rough': 'Roughness', 'metal': 'Metallic', 'normal': 'Normal',
                 'sheen': 'Sheen Weight', 'sheen_rough': 'Sheen Roughness', 'sheen_tint': 'Sheen Tint',
                 'trans': 'Transmission Weight', 'ior': 'IOR', 'spec': 'Specular IOR Level',
                 'coat': 'Coat Weight', 'coat_rough': 'Coat Roughness', 'aniso': 'Anisotropic',
                 'sss': 'Subsurface Weight', 'sss_radius': 'Subsurface Radius', 'sss_scale': 'Subsurface Scale',
                 'emit': 'Emission Color', 'emit_strength': 'Emission Strength', 'alpha': 'Alpha',
                 'thin': 'Thin Wall', 'diffuse_rough': 'Diffuse Roughness', 'spec_tint': 'Specular Tint'}
        for k, v in kw.items():
            self.set(p, names.get(k, k), v)
        return p.outputs[0]


_CACHE: dict[str, bpy.types.Material] = {}


def new_material(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:  # noqa: BLE001  (Blender 6 drops the flag)
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    return m, G(nt), out


def material(name):
    if name in _CACHE:
        return _CACHE[name]
    m = BUILDERS[name](name)
    _CACHE[name] = m
    return m


def reset_cache():
    _CACHE.clear()


# ----------------------------------------------------------------------------------------------
# materials
def _travertine(name):
    """Honed travertine floor tiles 600 x 1200, cream to honey, banded, small elongated pits."""
    m, g, out = new_material(name)
    co = g.coord('Object')
    # tile grid: 1.2 m along x, 0.6 m along y, running bond
    sep = g.n('SeparateXYZ')
    g.l(co, sep.inputs[0])
    row = g.math('FLOOR', g.math('DIVIDE', sep.outputs['Y'], 0.6))
    xoff = g.math('ADD', sep.outputs['X'], g.math('MULTIPLY', g.math('MODULO', row, 2.0), 0.6))
    col = g.math('FLOOR', g.math('DIVIDE', xoff, 1.2))
    fx = g.math('FRACT', g.math('DIVIDE', xoff, 1.2))
    fy = g.math('FRACT', g.math('DIVIDE', sep.outputs['Y'], 0.6))
    jx = g.math('MINIMUM', g.math('MULTIPLY', fx, 1.2), g.math('MULTIPLY', g.math('SUBTRACT', 1.0, fx), 1.2))
    jy = g.math('MINIMUM', g.math('MULTIPLY', fy, 0.6), g.math('MULTIPLY', g.math('SUBTRACT', 1.0, fy), 0.6))
    jd = g.math('MINIMUM', jx, jy)
    joint = g.maprange(jd, 0.0012, 0.0026, 1.0, 0.0)             # 1 inside the joint
    # per-tile random offset so bands don't continue across tiles
    tid = g.math('ADD', g.math('MULTIPLY', row, 17.31), g.math('MULTIPLY', col, 3.7))
    wn = g.n('TexWhiteNoise', {'noise_dimensions': '1D'})
    g.l(tid, g.sock(wn, 'W'))
    tile_rand = g.o(wn, 'Value')
    comb = g.n('CombineXYZ')
    g.l(g.math('MULTIPLY', tile_rand, 37.0), comb.inputs['X'])
    g.l(g.math('MULTIPLY', tile_rand, 11.0), comb.inputs['Z'])
    co2 = g.vmath('ADD', co, comb.outputs[0])
    # bedding bands along x (the long side), wobbly
    stretch = g.vmath('MULTIPLY', co2, (0.35, 6.0, 1.0))
    bandn = g.noise(stretch, scale=1.6, detail=6, rough=0.62, dist=0.9)
    bands = g.o(bandn, 'Fac')
    c1, _ = g.ramp(bands, [(0.30, (0.56, 0.43, 0.29)), (0.42, (0.78, 0.67, 0.52)),
                           (0.52, (0.87, 0.79, 0.66)), (0.60, (0.72, 0.59, 0.43)), (0.70, (0.82, 0.72, 0.58))])
    # tile-to-tile tone
    toner, _ = g.ramp(tile_rand, [(0.0, (0.92, 0.92, 0.92)), (1.0, (1.06, 1.03, 0.98))])
    c1 = g.mix(1.0, c1, toner, 'MULTIPLY')
    # pits: stretched voronoi
    pitv = g.voronoi(g.vmath('MULTIPLY', co2, (1.0, 3.2, 1.0)), scale=26.0)
    pit_n = g.noise(co2, scale=9.0, detail=2)
    pit_mask = g.math('MULTIPLY', g.maprange(g.o(pitv, 'Distance'), 0.05, 0.11, 1.0, 0.0),
                      g.maprange(g.o(pit_n, 'Fac'), 0.46, 0.56, 0.0, 1.0))
    c2 = g.mix(g.math('MULTIPLY', pit_mask, 0.8), c1, (0.38, 0.29, 0.20))
    # fine grain
    fine = g.noise(co, scale=180.0, detail=3)
    c3 = g.mix(0.10, c2, g.o(fine, 'Color'), 'OVERLAY')
    c4 = g.mix(g.math('MULTIPLY', joint, 0.85), c3, (0.55, 0.47, 0.37))
    rough = g.math('ADD', 0.30, g.math('MULTIPLY', g.math('ADD', pit_mask, joint), 0.45))
    h = g.math('SUBTRACT', g.math('MULTIPLY', g.math('ADD', pit_mask, joint), -1.0), 0.0)
    nrm = g.bump(h, strength=0.35, dist=0.0015)
    bsdf = g.principled(base=c4, rough=rough, normal=nrm, spec=0.45)
    g.l(bsdf, out.inputs['Surface'])
    return m


def _split_face(name):
    """Split-face sandstone / limestone. Height + colour maps from textures.split_face(); true
    displacement (objects using it get adaptive subdivision)."""
    m, g, out = new_material(name)
    m.displacement_method = 'BOTH'
    uv = g.n('UVMap')
    vec = g.vmath('MULTIPLY', g.o(uv), (0.5, 0.5, 1.0))           # UVs are in metres; tile = 2 m
    hgt = g.image(os.path.join(TEX, 'split_face_height.png'), vec, 'Non-Color')
    colt = g.image(os.path.join(TEX, 'split_face_color.png'), vec, 'sRGB')
    fine = g.noise(g.o(uv), scale=420.0, detail=2)
    base = g.mix(0.12, g.o(colt, 'Color'), g.o(fine, 'Color'), 'OVERLAY')
    nrm = g.bump(g.o(fine, 'Fac'), strength=0.25, dist=0.0008)
    bsdf = g.principled(base=base, rough=0.92, normal=nrm, spec=0.3)
    g.l(bsdf, out.inputs['Surface'])
    disp = g.n('Displacement', Scale=0.045, Midlevel=0.5)
    g.l(g.o(hgt, 'Color'), disp.inputs['Height'])
    g.l(disp.outputs[0], out.inputs['Displacement'])
    return m


def _concrete(name):
    m, g, out = new_material(name)
    co = g.coord('Object')
    big = g.noise(co, scale=0.9, detail=5, rough=0.6)
    mid = g.noise(co, scale=7.0, detail=6, rough=0.65)
    c, _ = g.ramp(g.o(big, 'Fac'), [(0.35, (0.50, 0.48, 0.45)), (0.65, (0.66, 0.64, 0.60))])
    c = g.mix(0.5, c, g.o(mid, 'Color'), 'OVERLAY')
    pores = g.voronoi(co, scale=60.0)
    pn = g.noise(co, scale=30.0, detail=1)
    pm = g.math('MULTIPLY', g.maprange(g.o(pores, 'Distance'), 0.04, 0.20, 1.0, 0.0),
                g.maprange(g.o(pn, 'Fac'), 0.40, 0.5, 0.0, 1.0))
    c = g.mix(g.math('MULTIPLY', pm, 0.8), c, (0.28, 0.27, 0.25))
    h = g.math('ADD', g.math('MULTIPLY', g.o(mid, 'Fac'), 0.4), g.math('MULTIPLY', pm, -1.0))
    bsdf = g.principled(base=c, rough=0.86, normal=g.bump(h, 0.8, 0.005), spec=0.35)
    g.l(bsdf, out.inputs['Surface'])
    return m


def _plaster(name, tint=(0.80, 0.73, 0.63)):
    """Warm limewash plaster with soft clouding and trowel marks."""
    m, g, out = new_material(name)
    co = g.coord('Object')
    big = g.noise(co, scale=0.7, detail=6, rough=0.6)
    mid = g.noise(g.vmath('MULTIPLY', co, (1.0, 1.0, 2.5)), scale=3.5, detail=8, rough=0.7)
    lo = tuple(v * 0.88 for v in tint)
    hi = tuple(min(1.0, v * 1.07) for v in tint)
    c, _ = g.ramp(g.o(big, 'Fac'), [(0.35, lo), (0.65, hi)])
    c = g.mix(0.18, c, g.o(mid, 'Color'), 'OVERLAY')
    bsdf = g.principled(base=c, rough=0.9, normal=g.bump(g.o(mid, 'Fac'), 0.12, 0.004), spec=0.3)
    g.l(bsdf, out.inputs['Surface'])
    return m


def _wood(name, dark=(0.10, 0.055, 0.03), light=(0.24, 0.135, 0.07), rough=0.42, grain_axis='Z'):
    """Quarter-sawn timber; grain runs along grain_axis (object space)."""
    m, g, out = new_material(name)
    sc = {'X': (0.12, 2.6, 2.6), 'Y': (2.6, 0.12, 2.6), 'Z': (2.6, 2.6, 0.12)}[grain_axis]
    co = g.vmath('MULTIPLY', g.coord('Object'), sc)
    warp = g.noise(co, scale=1.5, detail=3)
    co2 = g.vmath('ADD', co, g.vmath('MULTIPLY', g.o(warp, 'Color'), (0.6, 0.6, 0.6)))
    ring = g.n('TexWave', {'wave_type': 'BANDS', 'bands_direction': 'X', 'wave_profile': 'SAW'},
               Scale=9.0, Distortion=4.0, Detail=4.0, **{'Detail Scale': 1.5})
    g.l(co2, ring.inputs['Vector'])
    fib = g.noise(g.vmath('MULTIPLY', co, (6, 6, 0.6)), scale=30.0, detail=4)
    f = g.math('ADD', g.math('MULTIPLY', g.o(ring, 'Fac'), 0.7), g.math('MULTIPLY', g.o(fib, 'Fac'), 0.3))
    c, _ = g.ramp(f, [(0.15, dark), (0.55, tuple((a + b) / 2 for a, b in zip(dark, light))), (0.95, light)])
    bsdf = g.principled(base=c, rough=rough, normal=g.bump(f, 0.18, 0.001), spec=0.5, coat=0.15, coat_rough=0.3)
    g.l(bsdf, out.inputs['Surface'])
    return m


def _oak(name):
    return _wood(name, dark=(0.20, 0.115, 0.055), light=(0.42, 0.27, 0.14), rough=0.5)


def _walnut(name):
    return _wood(name)


def _white_brick(name):
    """Painted white brick (lime-washed), with a little red brick showing through worn paint."""
    m, g, out = new_material(name)
    co = g.coord('Object')
    sep = g.n('SeparateXYZ')
    g.l(co, sep.inputs[0])
    # brick texture works in 2D: use (x + y) along the wall, z up
    comb = g.n('CombineXYZ')
    g.l(g.math('ADD', sep.outputs['X'], sep.outputs['Y']), comb.inputs['X'])
    g.l(sep.outputs['Z'], comb.inputs['Y'])
    br = g.n('TexBrick', {'offset': 0.5, 'squash_frequency': 1},
             Scale=1.0, **{'Mortar Size': 0.011, 'Mortar Smooth': 0.35, 'Bias': 0.0,
                           'Brick Width': 0.23, 'Row Height': 0.075})
    g.set(br, 'Color1', (1, 1, 1))
    g.set(br, 'Color2', (0.7, 0.7, 0.7))
    g.l(comb.outputs[0], br.inputs['Vector'])
    mortar = g.o(br, 'Fac')
    per = g.o(br, 'Color')
    wear = g.noise(co, scale=3.0, detail=8, rough=0.7)
    worn = g.maprange(g.o(wear, 'Fac'), 0.62, 0.70, 0.0, 1.0)
    paint = g.mix(0.5, (0.88, 0.86, 0.82), per, 'MULTIPLY')
    brick_red = (0.45, 0.22, 0.14)
    face = g.mix(g.math('MULTIPLY', worn, 0.85), paint, brick_red)
    mn = g.noise(co, scale=60, detail=3)
    c = g.mix(mortar, face, (0.80, 0.78, 0.74))
    c = g.mix(0.12, c, g.o(mn, 'Color'), 'OVERLAY')
    h = g.math('ADD', g.math('MULTIPLY', mortar, -1.0), g.math('MULTIPLY', g.o(mn, 'Fac'), 0.25))
    bsdf = g.principled(base=c, rough=0.88, normal=g.bump(h, 0.45, 0.006), spec=0.3)
    g.l(bsdf, out.inputs['Surface'])
    return m


def _breccia(name):
    """Breccia marble ('unique stone'): angular clasts of cream, taupe, rust and charcoal in two
    sizes, set in a darker matrix with fine veins; polished."""
    m, g, out = new_material(name)
    co = g.coord('Object')
    warp = g.noise(co, scale=2.0, detail=4)
    co2 = g.vmath('ADD', co, g.vmath('MULTIPLY', g.o(warp, 'Color'), (0.08, 0.08, 0.08)))
    big = g.voronoi(co2, scale=7.0, metric='CHEBYCHEV')
    small = g.voronoi(co2, scale=21.0, metric='CHEBYCHEV')
    e_big = g.voronoi(co2, scale=7.0, feature='DISTANCE_TO_EDGE', metric='CHEBYCHEV')
    e_small = g.voronoi(co2, scale=21.0, feature='DISTANCE_TO_EDGE', metric='CHEBYCHEV')
    sb = g.n('SeparateColor')
    g.l(g.o(big, 'Color'), sb.inputs[0])
    ss = g.n('SeparateColor')
    g.l(g.o(small, 'Color'), ss.inputs[0])
    pal = [(0.0, (0.88, 0.84, 0.76)), (0.22, (0.74, 0.66, 0.55)), (0.40, (0.52, 0.44, 0.36)),
           (0.55, (0.66, 0.40, 0.22)), (0.68, (0.92, 0.89, 0.83)), (0.80, (0.30, 0.27, 0.24)),
           (0.90, (0.80, 0.72, 0.60)), (1.0, (0.58, 0.50, 0.42))]
    cb, _ = g.ramp(g.o(sb, 'Red'), pal, 'CONSTANT')
    cs, _ = g.ramp(g.o(ss, 'Green'), pal, 'CONSTANT')
    use_small = g.math('GREATER_THAN', g.o(sb, 'Blue'), 0.55)
    c = g.mix(use_small, cb, cs)
    tex = g.noise(co, scale=40.0, detail=8, rough=0.65)
    c = g.mix(0.25, c, g.o(tex, 'Color'), 'OVERLAY')
    edge = g.mixf(use_small, g.o(e_big, 'Distance'), g.math('MINIMUM', g.o(e_big, 'Distance'), g.o(e_small, 'Distance')))
    matrix = g.maprange(edge, 0.0, 0.012, 1.0, 0.0)
    c = g.mix(matrix, c, (0.36, 0.30, 0.25))
    vein = g.maprange(edge, 0.0, 0.0035, 1.0, 0.0)
    c = g.mix(g.math('MULTIPLY', vein, 0.7), c, (0.16, 0.13, 0.11))
    bsdf = g.principled(base=c, rough=0.14, spec=0.5, coat=0.25, coat_rough=0.06)
    g.l(bsdf, out.inputs['Surface'])
    return m


def _marble_white(name):
    """Calacatta-like white marble with grey-gold veining for table tops."""
    m, g, out = new_material(name)
    co = g.coord('Object')
    warp = g.noise(co, scale=1.4, detail=8, rough=0.62, dist=1.6)
    w = g.n('TexWave', {'wave_type': 'BANDS', 'bands_direction': 'DIAGONAL', 'wave_profile': 'SIN'},
            Scale=1.3, Distortion=12.0, Detail=8.0, **{'Detail Scale': 1.2, 'Detail Roughness': 0.6})
    g.l(g.vmath('ADD', co, g.o(warp, 'Color')), w.inputs['Vector'])
    vein = g.maprange(g.o(w, 'Fac'), 0.0, 0.12, 1.0, 0.0)
    c = g.mix(g.math('MULTIPLY', vein, 0.8), (0.90, 0.88, 0.84), (0.45, 0.42, 0.38))
    soft = g.noise(co, scale=4.0, detail=6)
    c = g.mix(0.08, c, g.o(soft, 'Color'), 'OVERLAY')
    bsdf = g.principled(base=c, rough=0.12, spec=0.5, coat=0.3, coat_rough=0.05, sss=0.05,
                        sss_radius=(0.4, 0.35, 0.3), sss_scale=0.02)
    g.l(bsdf, out.inputs['Surface'])
    return m


def _velvet(name, base=(0.15, 0.06, 0.032), sheen=(1.0, 0.76, 0.6)):
    m, g, out = new_material(name)
    co = g.coord('Object')
    crush = g.noise(co, scale=18.0, detail=5, rough=0.6)
    c = g.mix(0.25, base, g.o(crush, 'Color'), 'OVERLAY')
    bsdf = g.principled(base=c, rough=0.82, sheen=1.0, sheen_rough=0.32, sheen_tint=sheen, spec=0.25,
                        normal=g.bump(g.o(crush, 'Fac'), 0.12, 0.002))
    g.l(bsdf, out.inputs['Surface'])
    return m


def _velvet_olive(name):
    return _velvet(name, base=(0.17, 0.17, 0.09), sheen=(0.85, 0.85, 0.62))


def _leather(name):
    m, g, out = new_material(name)
    co = g.coord('Object')
    grain = g.voronoi(co, scale=220.0)
    big = g.noise(co, scale=3.0, detail=4)
    c, _ = g.ramp(g.o(big, 'Fac'), [(0.3, (0.16, 0.07, 0.035)), (0.7, (0.27, 0.12, 0.055))])
    bsdf = g.principled(base=c, rough=0.42, spec=0.5, coat=0.25, coat_rough=0.35,
                        normal=g.bump(g.o(grain, 'Distance'), 0.15, 0.0008))
    g.l(bsdf, out.inputs['Surface'])
    return m


def _brass(name, rough=0.26):
    m, g, out = new_material(name)
    co = g.coord('Object')
    scr = g.noise(g.vmath('MULTIPLY', co, (1, 1, 40)), scale=60.0, detail=3)
    patina = g.noise(co, scale=6.0, detail=5)
    c = g.mix(g.math('MULTIPLY', g.o(patina, 'Fac'), 0.25), (0.86, 0.66, 0.38), (0.62, 0.45, 0.24))
    r = g.math('ADD', rough, g.math('MULTIPLY', g.o(scr, 'Fac'), 0.12))
    bsdf = g.principled(base=c, metal=1.0, rough=r, aniso=0.35, normal=g.bump(g.o(scr, 'Fac'), 0.05, 0.0005))
    g.l(bsdf, out.inputs['Surface'])
    return m


def _steel(name):
    m, g, out = new_material(name)
    co = g.coord('Object')
    scr = g.noise(g.vmath('MULTIPLY', co, (1, 1, 60)), scale=80.0, detail=3)
    bsdf = g.principled(base=(0.72, 0.71, 0.69), metal=1.0, rough=g.math('ADD', 0.22, g.math('MULTIPLY', g.o(scr, 'Fac'), 0.1)),
                        aniso=0.5)
    g.l(bsdf, out.inputs['Surface'])
    return m


def _black_metal(name):
    m, g, out = new_material(name)
    g.l(g.principled(base=(0.028, 0.026, 0.024), rough=0.38, metal=0.6), out.inputs['Surface'])
    return m


def _bronze_frame(name):
    m, g, out = new_material(name)
    g.l(g.principled(base=(0.10, 0.075, 0.05), rough=0.35, metal=0.9), out.inputs['Surface'])
    return m


def _glass(name, tint=(0.98, 0.98, 0.97), rough=0.0, thin=False):
    m, g, out = new_material(name)
    bsdf = g.principled(base=tint, trans=1.0, rough=rough, ior=1.45, spec=0.5, thin=thin)
    g.l(bsdf, out.inputs['Surface'])
    return m


def _shadow_pass(g, out, shader, transp=1.0, tint=(1, 1, 1)):
    """Archviz trick: shadow rays pass straight through (so the sun/sky light the interior
    without caustics), camera and reflection rays see the real shader."""
    lp = g.n('LightPath')
    tr = g.n('BsdfTransparent', Color=tint)
    mx = g.n('MixShader')
    g.l(g.math('MULTIPLY', g.o(lp, 'Is Shadow Ray'), transp), mx.inputs[0])
    g.l(shader, mx.inputs[1])
    g.l(tr.outputs[0], mx.inputs[2])
    g.l(mx.outputs[0], out.inputs['Surface'])


def _window_glass(name):
    """Single-plane glazing: thin-walled, slightly reflective, faint warm tint; shadow-transparent."""
    m, g, out = new_material(name)
    bsdf = g.principled(base=(0.80, 0.80, 0.78), trans=1.0, rough=0.0, ior=1.45, spec=0.5, thin=True)
    _shadow_pass(g, out, bsdf, 1.0, (0.96, 0.96, 0.94))
    return m


def _wine_glass(name):
    return _glass(name, tint=(1, 1, 1))


def _wine(name):
    m, g, out = new_material(name)
    bsdf = g.principled(base=(0.35, 0.02, 0.03), trans=1.0, rough=0.0, ior=1.34)
    g.l(bsdf, out.inputs['Surface'])
    vol = g.n('VolumeAbsorption', Color=(0.5, 0.02, 0.04), Density=60.0)
    g.l(vol.outputs[0], out.inputs['Volume'])
    return m


def _glass_block(name):
    """Glass block faces: amber-tinted glass with the moulded ripple pattern on both faces."""
    m, g, out = new_material(name)
    co = g.coord('Object')
    sep = g.n('SeparateXYZ')
    g.l(co, sep.inputs[0])
    # ripple: concentric-ish waves per block (blocks are 0.2 m on a grid in local x/z)
    w1 = g.n('TexWave', {'wave_type': 'RINGS', 'rings_direction': 'SPHERICAL', 'wave_profile': 'SIN'},
             Scale=38.0, Distortion=2.5, Detail=2.0)
    cell = g.vmath('FRACTION', g.vmath('DIVIDE', g.vmath('SUBTRACT', co, (0.006, 0.0, 0.006)), (0.202, 0.202, 0.202)))
    g.l(g.vmath('SUBTRACT', cell, (0.5, 0.5, 0.5)), w1.inputs['Vector'])
    nz = g.noise(co, scale=14.0, detail=3)
    h = g.math('ADD', g.math('MULTIPLY', g.o(w1, 'Fac'), 0.7), g.math('MULTIPLY', g.o(nz, 'Fac'), 0.5))
    nrm = g.bump(h, 0.9, 0.004)
    bsdf = g.principled(base=(0.98, 0.86, 0.68), trans=1.0, rough=0.05, ior=1.5, spec=0.5, normal=nrm)
    tl = g.n('BsdfTranslucent', Color=(1.0, 0.76, 0.48))
    g.l(nrm, tl.inputs['Normal'])
    mx = g.n('MixShader', Fac=0.16)
    g.l(bsdf, mx.inputs[1])
    g.l(tl.outputs[0], mx.inputs[2])
    _shadow_pass(g, out, mx.outputs[0], 0.55, (1.0, 0.74, 0.45))
    return m


def _mortar(name):
    m, g, out = new_material(name)
    co = g.coord('Object')
    nz = g.noise(co, scale=80, detail=3)
    c = g.mix(0.15, (0.83, 0.81, 0.76), g.o(nz, 'Color'), 'OVERLAY')
    g.l(g.principled(base=c, rough=0.9, normal=g.bump(g.o(nz, 'Fac'), 0.3, 0.001)), out.inputs['Surface'])
    return m


def _linen(name, col=(0.86, 0.80, 0.70), translucent=0.45):
    """Draped linen: two-sided, light glows through it."""
    m, g, out = new_material(name)
    co = g.coord('Object')
    weave = g.noise(g.vmath('MULTIPLY', co, (1, 1, 1)), scale=600.0, detail=1)
    slub = g.noise(g.vmath('MULTIPLY', co, (0.3, 1, 1)), scale=40.0, detail=3)
    c = g.mix(0.10, col, g.o(slub, 'Color'), 'OVERLAY')
    p = g.principled(base=c, rough=0.85, sheen=0.4, sheen_rough=0.5, spec=0.2,
                     normal=g.bump(g.o(weave, 'Fac'), 0.08, 0.0005))
    tr = g.n('BsdfTranslucent', Color=tuple(min(1, v * 1.05) for v in col))
    mx = g.n('MixShader', Fac=translucent)
    g.l(p, mx.inputs[1])
    g.l(tr.outputs[0], mx.inputs[2])
    g.l(mx.outputs[0], out.inputs['Surface'])
    return m


def _sheer(name):
    """Sheer voile: mostly see-through, glows when backlit."""
    m, g, out = new_material(name)
    co = g.coord('Object')
    weave = g.noise(co, scale=900.0, detail=1)
    dens = g.noise(g.vmath('MULTIPLY', co, (0.2, 0.2, 1)), scale=20, detail=2)
    tr = g.n('BsdfTranslucent', Color=(1.0, 0.96, 0.9))
    df = g.n('BsdfDiffuse', Color=(0.96, 0.93, 0.87))
    tp = g.n('BsdfTransparent', Color=(1, 1, 1))
    a = g.n('MixShader', Fac=0.25)
    g.l(tr.outputs[0], a.inputs[1])
    g.l(df.outputs[0], a.inputs[2])
    fac = g.math('ADD', 0.38, g.math('MULTIPLY', g.math('ADD', g.o(weave, 'Fac'), g.o(dens, 'Fac')), 0.12))
    b = g.n('MixShader')
    g.l(fac, b.inputs[0])
    g.l(a.outputs[0], b.inputs[1])
    g.l(tp.outputs[0], b.inputs[2])
    g.l(b.outputs[0], out.inputs['Surface'])
    return m


def _leaf(name, top=(0.105, 0.125, 0.075), under=(0.40, 0.43, 0.36)):
    """Olive leaf: dark grey-green above, silvery below; per-leaf variation from attribute 'rnd'."""
    m, g, out = new_material(name)
    attr = g.n('Attribute', {'attribute_name': 'rnd', 'attribute_type': 'GEOMETRY'})
    geo = g.n('NewGeometry')
    rnd = g.o(attr, 'Fac')
    vt, _ = g.ramp(rnd, [(0.0, top), (0.5, tuple(v * 1.18 for v in top)), (1.0, (0.20, 0.22, 0.12))])
    vu, _ = g.ramp(rnd, [(0.0, under), (1.0, tuple(v * 1.12 for v in under))])
    c = g.mix(g.o(geo, 'Backfacing'), vt, vu)
    p = g.principled(base=c, rough=g.mixf(g.o(geo, 'Backfacing'), 0.42, 0.62), spec=0.45)
    tr = g.n('BsdfTranslucent', Color=(0.32, 0.38, 0.12))
    mx = g.n('MixShader', Fac=0.18)
    g.l(p, mx.inputs[1])
    g.l(tr.outputs[0], mx.inputs[2])
    g.l(mx.outputs[0], out.inputs['Surface'])
    return m


def _leaf_street(name):
    return _leaf(name, top=(0.10, 0.20, 0.05), under=(0.25, 0.35, 0.12))


def _bark(name):
    """Olive bark: grey-brown, deeply fissured along the stem (ridged noise stretched along z),
    paler weathered ridges, a little lichen."""
    m, g, out = new_material(name)
    co = g.coord('Object')
    st = g.vmath('MULTIPLY', co, (7.0, 7.0, 1.6))
    warp = g.noise(co, scale=3.0, detail=3)
    st = g.vmath('ADD', st, g.vmath('MULTIPLY', g.o(warp, 'Color'), (0.6, 0.6, 0.6)))
    ridges = g.n('TexNoise', {'noise_dimensions': '3D', 'noise_type': 'RIDGED_MULTIFRACTAL'},
                 Scale=2.2, Detail=7.0, Roughness=0.6, Lacunarity=2.2, Offset=0.9, Gain=1.6)
    g.l(st, ridges.inputs['Vector'])
    r = g.maprange(g.o(ridges, 'Fac'), 0.2, 1.4, 0.0, 1.0)
    fine = g.noise(g.vmath('MULTIPLY', co, (40, 40, 12)), scale=1.0, detail=4)
    h = g.math('ADD', g.math('MULTIPLY', r, 0.85), g.math('MULTIPLY', g.o(fine, 'Fac'), 0.15))
    c, _ = g.ramp(h, [(0.15, (0.045, 0.04, 0.032)), (0.45, (0.15, 0.135, 0.11)), (0.8, (0.30, 0.28, 0.24)),
                      (1.0, (0.40, 0.38, 0.33))])
    lich = g.noise(co, scale=5.0, detail=5)
    c = g.mix(g.maprange(g.o(lich, 'Fac'), 0.6, 0.68, 0.0, 0.3), c, (0.42, 0.44, 0.36))
    g.l(g.principled(base=c, rough=0.92, normal=g.bump(h, 0.85, 0.02), spec=0.25), out.inputs['Surface'])
    return m


def _soil(name):
    m, g, out = new_material(name)
    co = g.coord('Object')
    v = g.voronoi(co, scale=60.0)
    n = g.noise(co, scale=20.0, detail=6)
    c, _ = g.ramp(g.o(n, 'Fac'), [(0.3, (0.05, 0.04, 0.03)), (0.7, (0.14, 0.11, 0.08))])
    g.l(g.principled(base=c, rough=0.95, normal=g.bump(g.o(v, 'Distance'), 0.5, 0.004)), out.inputs['Surface'])
    return m


def _pebble(name):
    m, g, out = new_material(name)
    co = g.coord('Object')
    v = g.voronoi(co, scale=40.0, feature='SMOOTH_F1')
    sc = g.n('SeparateColor')
    g.l(g.o(v, 'Color'), sc.inputs[0])
    c, _ = g.ramp(g.o(sc, 'Red'), [(0.0, (0.62, 0.58, 0.52)), (0.5, (0.78, 0.75, 0.70)), (1.0, (0.45, 0.42, 0.38))])
    h = g.maprange(g.o(v, 'Distance'), 0.0, 0.5, 1.0, 0.0)
    g.l(g.principled(base=c, rough=0.6, normal=g.bump(h, 0.8, 0.02)), out.inputs['Surface'])
    return m


def _emit(name, temp=2600, strength=12.0):
    m, g, out = new_material(name)
    bb = g.n('Blackbody', Temperature=temp)
    e = g.n('Emission', Strength=strength)
    g.l(bb.outputs[0], e.inputs['Color'])
    g.l(e.outputs[0], out.inputs['Surface'])
    return m


def _bulb(name):
    return _emit(name, 2500, 40.0)


def _lampshade(name):
    """Opal glass / linen shade lit from inside."""
    m, g, out = new_material(name)
    tr = g.n('BsdfTranslucent', Color=(1.0, 0.86, 0.66))
    df = g.n('BsdfDiffuse', Color=(0.95, 0.9, 0.82))
    mx = g.n('MixShader', Fac=0.6)
    g.l(df.outputs[0], mx.inputs[1])
    g.l(tr.outputs[0], mx.inputs[2])
    g.l(mx.outputs[0], out.inputs['Surface'])
    return m


def _ceramic(name):
    m, g, out = new_material(name)
    g.l(g.principled(base=(0.90, 0.87, 0.81), rough=0.18, spec=0.5, coat=0.4, coat_rough=0.05), out.inputs['Surface'])
    return m


def _stone_rough(name):
    """Bush-hammered limestone (planter rims, pendants): cream, fine pits, no displacement."""
    m, g, out = new_material(name)
    co = g.coord('Object')
    p = g.voronoi(co, scale=90.0)
    n = g.noise(co, scale=6.0, detail=8, rough=0.7)
    c, _ = g.ramp(g.o(n, 'Fac'), [(0.3, (0.66, 0.60, 0.50)), (0.7, (0.83, 0.78, 0.69))])
    h = g.math('ADD', g.o(n, 'Fac'), g.math('MULTIPLY', g.maprange(g.o(p, 'Distance'), 0.0, 0.25), 0.6))
    g.l(g.principled(base=c, rough=0.9, normal=g.bump(h, 0.55, 0.004), spec=0.3), out.inputs['Surface'])
    return m


def _brick_red(name):
    """Street facades opposite: soft red / brown brick."""
    m, g, out = new_material(name)
    co = g.coord('Object')
    sep = g.n('SeparateXYZ')
    g.l(co, sep.inputs[0])
    comb = g.n('CombineXYZ')
    g.l(g.math('ADD', sep.outputs['X'], sep.outputs['Y']), comb.inputs['X'])
    g.l(sep.outputs['Z'], comb.inputs['Y'])
    br = g.n('TexBrick', {'offset': 0.5}, Scale=1.0, **{'Mortar Size': 0.01, 'Brick Width': 0.23, 'Row Height': 0.075,
                                                        'Bias': 0.0})
    g.set(br, 'Color1', (0.44, 0.20, 0.12))
    g.set(br, 'Color2', (0.55, 0.30, 0.18))
    g.set(br, 'Mortar', (0.62, 0.58, 0.52))
    g.l(comb.outputs[0], br.inputs['Vector'])
    n = g.noise(co, scale=2.0, detail=5)
    c = g.mix(0.25, g.o(br, 'Color'), g.o(n, 'Color'), 'OVERLAY')
    g.l(g.principled(base=c, rough=0.85, normal=g.bump(g.o(br, 'Fac'), 0.4, 0.004)), out.inputs['Surface'])
    return m


def _render_plaster_out(name):
    return _plaster(name, (0.52, 0.39, 0.25))      # ochre render: stays below clipping in full sun


def _stone_out(name):
    return _plaster(name, (0.52, 0.46, 0.38))      # pale stone facades / trims opposite (sunlit)


def _asphalt(name):
    m, g, out = new_material(name)
    co = g.coord('Object')
    n = g.noise(co, scale=40.0, detail=6)
    c, _ = g.ramp(g.o(n, 'Fac'), [(0.3, (0.07, 0.065, 0.06)), (0.7, (0.16, 0.15, 0.14))])
    g.l(g.principled(base=c, rough=0.6, normal=g.bump(g.o(n, 'Fac'), 0.4, 0.003)), out.inputs['Surface'])
    return m


def _paving(name):
    m, g, out = new_material(name)
    co = g.coord('Object')
    sep = g.n('SeparateXYZ')
    g.l(co, sep.inputs[0])
    comb = g.n('CombineXYZ')
    g.l(sep.outputs['X'], comb.inputs['X'])
    g.l(sep.outputs['Y'], comb.inputs['Y'])
    br = g.n('TexBrick', {'offset': 0.5}, Scale=1.0, **{'Mortar Size': 0.006, 'Brick Width': 0.6, 'Row Height': 0.6})
    g.set(br, 'Color1', (0.55, 0.52, 0.47))
    g.set(br, 'Color2', (0.62, 0.59, 0.54))
    g.set(br, 'Mortar', (0.3, 0.29, 0.27))
    g.l(comb.outputs[0], br.inputs['Vector'])
    g.l(g.principled(base=g.o(br, 'Color'), rough=0.75, normal=g.bump(g.o(br, 'Fac'), 0.3, 0.004)), out.inputs['Surface'])
    return m


def _facade_windows(name):
    """Opposite-building windows: dark glass reflecting sky, some rooms lit warm."""
    m, g, out = new_material(name)
    co = g.coord('Object')
    v = g.voronoi(g.vmath('MULTIPLY', co, (0.5, 0.5, 0.33)), scale=1.0, rand=0.0)
    sc = g.n('SeparateColor')
    g.l(g.o(v, 'Color'), sc.inputs[0])
    lit = g.maprange(g.o(sc, 'Red'), 0.80, 0.82)
    glass = g.principled(base=(0.035, 0.035, 0.04), rough=0.04, metal=0.0, spec=1.0, coat=1.0, coat_rough=0.0)
    em = g.n('Emission', Color=(1.0, 0.62, 0.32), Strength=1.2)
    mx = g.n('MixShader')
    g.l(lit, mx.inputs[0])
    g.l(glass, mx.inputs[1])
    g.l(em.outputs[0], mx.inputs[2])
    g.l(mx.outputs[0], out.inputs['Surface'])
    return m


def _shopfront(name):
    """Shop window: dark reflective glass over a warm-lit interior (glow stronger low down)."""
    m, g, out = new_material(name)
    co = g.coord('Object')
    sep = g.n('SeparateXYZ')
    g.l(co, sep.inputs[0])
    nz = g.noise(co, scale=1.3, detail=3)
    glow = g.math('MULTIPLY', g.maprange(sep.outputs['Z'], 2.6, 0.2, 0.15, 1.0), g.o(nz, 'Fac'))
    glass = g.principled(base=(0.03, 0.03, 0.03), rough=0.03, spec=1.0, coat=1.0, coat_rough=0.0)
    em = g.n('Emission', Color=(1.0, 0.6, 0.3))
    g.l(g.math('MULTIPLY', glow, 1.6), em.inputs['Strength'])
    mx = g.n('MixShader', Fac=0.5)
    g.l(glass, mx.inputs[1])
    g.l(em.outputs[0], mx.inputs[2])
    g.l(mx.outputs[0], out.inputs['Surface'])
    return m


def _awning_stripe(name):
    m, g, out = new_material(name)
    co = g.coord('Object')
    sep = g.n('SeparateXYZ')
    g.l(co, sep.inputs[0])
    st = g.math('GREATER_THAN', g.math('FRACT', g.math('DIVIDE', sep.outputs['Y'], 0.32)), 0.5)
    c = g.mix(st, (0.82, 0.78, 0.68), (0.20, 0.28, 0.20))
    g.l(g.principled(base=c, rough=0.85, sheen=0.3), out.inputs['Surface'])
    return m


def _awning(name):
    m, g, out = new_material(name)
    g.l(g.principled(base=(0.16, 0.20, 0.13), rough=0.8, sheen=0.3), out.inputs['Surface'])
    return m


def _rope(name):
    m, g, out = new_material(name)
    g.l(g.principled(base=(0.05, 0.045, 0.04), rough=0.6), out.inputs['Surface'])
    return m


def _bread(name):
    m, g, out = new_material(name)
    co = g.coord('Object')
    n = g.noise(co, scale=30.0, detail=6)
    c, _ = g.ramp(g.o(n, 'Fac'), [(0.3, (0.35, 0.17, 0.06)), (0.7, (0.62, 0.38, 0.16))])
    g.l(g.principled(base=c, rough=0.75, normal=g.bump(g.o(n, 'Fac'), 0.5, 0.003)), out.inputs['Surface'])
    return m


def _olive_oil(name):
    m, g, out = new_material(name)
    g.l(g.principled(base=(0.55, 0.45, 0.08), trans=0.9, rough=0.02, ior=1.47), out.inputs['Surface'])
    return m


def _candle(name):
    m, g, out = new_material(name)
    g.l(g.principled(base=(0.93, 0.88, 0.78), rough=0.4, sss=0.6, sss_radius=(1.0, 0.6, 0.3), sss_scale=0.03),
        out.inputs['Surface'])
    return m


def _flame(name):
    return _emit(name, 1800, 60.0)


BUILDERS = {
    'travertine': _travertine, 'split_face': _split_face, 'concrete': _concrete,
    'plaster': _plaster, 'plaster_out': _render_plaster_out, 'stone_out': _stone_out, 'oak': _oak, 'walnut': _walnut,
    'white_brick': _white_brick, 'breccia': _breccia, 'marble_white': _marble_white,
    'velvet': _velvet, 'velvet_olive': _velvet_olive, 'leather': _leather, 'brass': _brass,
    'steel': _steel, 'black_metal': _black_metal, 'bronze_frame': _bronze_frame,
    'window_glass': _window_glass, 'wine_glass': _wine_glass, 'wine': _wine,
    'glass_block': _glass_block, 'mortar': _mortar, 'linen': _linen, 'sheer': _sheer,
    'leaf': _leaf, 'leaf_street': _leaf_street, 'bark': _bark, 'soil': _soil, 'pebble': _pebble,
    'bulb': _bulb, 'lampshade': _lampshade, 'ceramic': _ceramic, 'stone_rough': _stone_rough,
    'brick_red': _brick_red, 'asphalt': _asphalt, 'paving': _paving, 'facade_windows': _facade_windows,
    'awning': _awning, 'shopfront': _shopfront, 'awning_stripe': _awning_stripe, 'rope': _rope, 'bread': _bread, 'olive_oil': _olive_oil, 'candle': _candle,
    'flame': _flame,
}
