"""geo — procedural geometry for the restaurant scene (numpy -> bpy meshes / curves).

Everything is built from the client's drawings (plans, sections, elevations 01-04): metres,
z up, x east, y north. Components: primitives, lathe objects, drapes (ceiling swags, festoon
valances, void rings), the olive tree, glass-block panels, fluted cabins, banquettes, tables,
chairs, pendants, table settings.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from nodes import material


# ----------------------------------------------------------------------------------------------
# core mesh helpers
def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def mesh_obj(name, verts, faces, mat=None, uvs=None, smooth=True, attrs=None, coll=None, loc=(0, 0, 0)):
    """verts (N,3); faces: list of index lists or (F,k) array; uvs: per-vertex (N,2)."""
    me = bpy.data.meshes.new(name)
    verts = np.asarray(verts, np.float32)
    if isinstance(faces, np.ndarray):
        faces = faces.tolist()
    me.from_pydata(verts.tolist(), [], faces)
    if uvs is not None:
        uvs = np.asarray(uvs, np.float32)
        ul = me.uv_layers.new(name='UVMap')
        vi = np.empty(len(me.loops), np.int32)
        me.loops.foreach_get('vertex_index', vi)
        ul.data.foreach_set('uv', uvs[vi].ravel())
    for k, (domain, vals) in (attrs or {}).items():
        a = me.attributes.new(k, 'FLOAT', domain)
        a.data.foreach_set('value', np.asarray(vals, np.float32))
    me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    if mat is not None:
        ob.data.materials.append(material(mat) if isinstance(mat, str) else mat)
    return link(ob, coll)


def grid_faces(nu, nv, wrap_u=False):
    """Quad faces for a (nu, nv) vertex grid indexed i*nv + j."""
    i = np.arange(nu if wrap_u else nu - 1)
    j = np.arange(nv - 1)
    I, J = np.meshgrid(i, j, indexing='ij')
    I2 = (I + 1) % nu
    a = I * nv + J
    b = I2 * nv + J
    c = I2 * nv + J + 1
    d = I * nv + J + 1
    return np.stack([a, b, c, d], -1).reshape(-1, 4)


def grid_obj(name, P, mat=None, uv_scale=None, smooth=True, wrap_u=False, coll=None, attrs=None):
    nu, nv = P.shape[:2]
    faces = grid_faces(nu, nv, wrap_u)
    uvs = None
    if uv_scale is not None:
        # arc-length UVs in metres (for textures authored per metre)
        du = np.linalg.norm(np.diff(P, axis=0), axis=-1).mean(axis=1)
        dv = np.linalg.norm(np.diff(P, axis=1), axis=-1).mean(axis=0)
        u = np.concatenate([[0], np.cumsum(du)])
        v = np.concatenate([[0], np.cumsum(dv)])
        U, V = np.meshgrid(u, v, indexing='ij')
        uvs = np.stack([U, V], -1).reshape(-1, 2) * uv_scale
    return mesh_obj(name, P.reshape(-1, 3), faces, mat, uvs, smooth, attrs, coll)


def bm_obj(name, bm, mat=None, smooth=True, coll=None, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    if mat is not None:
        ob.data.materials.append(material(mat) if isinstance(mat, str) else mat)
    return link(ob, coll)


def add_mod(ob, kind, **props):
    m = ob.modifiers.new(kind.lower(), kind)
    for k, v in props.items():
        setattr(m, k, v)
    return m


def subsurf(ob, levels=2, render=None):
    return add_mod(ob, 'SUBSURF', levels=levels, render_levels=render or levels)


def bevel(ob, width=0.005, segments=3):
    return add_mod(ob, 'BEVEL', width=width, segments=segments, limit_method='ANGLE')


def adaptive(ob, pixel=1.5):
    m = add_mod(ob, 'SUBSURF', subdivision_type='SIMPLE', levels=0, render_levels=1)
    m.use_adaptive_subdivision = True
    m.adaptive_pixel_size = pixel
    return m


def box(name, size, loc, mat=None, bev=0.0, coll=None, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    ob = bm_obj(name, bm, mat, smooth=False, coll=coll, loc=loc)
    ob.rotation_euler = rot
    if bev:
        bevel(ob, bev, 2)
    return ob


def box_uv(name, size, loc, mat=None, coll=None, uv_axes='xz'):
    """Box with planar metre UVs (for image-mapped materials such as split-face stone)."""
    sx, sy, sz = size
    ob = box(name, size, loc, mat, coll=coll)
    me = ob.data
    ul = me.uv_layers.new(name='UVMap')
    co = np.array([v.co[:] for v in me.vertices]) + np.array(loc)
    for poly in me.polygons:
        n = np.abs(np.array(poly.normal[:]))
        for li in poly.loop_indices:
            p = co[me.loops[li].vertex_index]
            if n[2] > 0.5:
                uv = (p[0], p[1])
            elif n[0] > 0.5:
                uv = (p[1], p[2])
            else:
                uv = (p[0], p[2])
            ul.data[li].uv = uv
    return ob


def cyl(name, r, h, loc, mat=None, seg=48, coll=None, cap=True, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    return bm_obj(name, bm, mat, smooth=True, coll=coll, loc=loc)


def lathe(name, prof, loc=(0, 0, 0), mat=None, seg=64, coll=None, smooth=True, close_top=False):
    """Revolve a profile [(r, z), ...] around z."""
    prof = np.asarray(prof, np.float32)
    th = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    P = np.zeros((seg, len(prof), 3), np.float32)
    P[..., 0] = np.cos(th)[:, None] * prof[None, :, 0]
    P[..., 1] = np.sin(th)[:, None] * prof[None, :, 0]
    P[..., 2] = prof[None, :, 1]
    ob = grid_obj(name, P, mat, smooth=smooth, wrap_u=True, coll=coll)
    ob.location = loc
    return ob


def curve_obj(name, polylines, radii, mat=None, coll=None, bevel_res=3, resolution=2):
    """polylines: list of (n,3) arrays; radii: list of (n,) arrays. Poly splines with bevel."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 1.0
    cu.bevel_resolution = bevel_res
    cu.use_fill_caps = True
    cu.resolution_u = resolution
    for pts, rad in zip(polylines, radii):
        sp = cu.splines.new('NURBS' if len(pts) > 3 else 'POLY')
        sp.points.add(len(pts) - 1)
        co = np.hstack([pts, np.ones((len(pts), 1))]).astype(np.float32)
        sp.points.foreach_set('co', co.ravel())
        sp.points.foreach_set('radius', np.asarray(rad, np.float32))
        if sp.type == 'NURBS':
            sp.order_u = 3
            sp.use_endpoint_u = True
    ob = bpy.data.objects.new(name, cu)
    if mat is not None:
        cu.materials.append(material(mat) if isinstance(mat, str) else mat)
    return link(ob, coll)


# ----------------------------------------------------------------------------------------------
# drapes
def _folds(x, v, rng, n=4, lam=(0.10, 0.34)):
    """Gathered-fabric folds along x (metres), drifting slightly with v. Sharpened sines."""
    f = np.zeros(np.broadcast(x, v).shape, np.float32)
    for k in range(n):
        lmb = rng.uniform(*lam)
        ph = rng.uniform(0, 2 * np.pi)
        drift = rng.uniform(-0.6, 0.6)
        s = np.sin(2 * np.pi * x / lmb + ph + drift * v * 2 * np.pi)
        f += (np.sign(s) * np.abs(s) ** 0.75) / (k + 1) ** 0.6
    return f / 2.0


def swag(name, x0, x1, ya, yb, z, sag=0.55, seed=0, mat='linen', coll=None, res=0.02, fold_amp=0.035):
    """Ceiling swag: fabric spanning along x, hung between battens at y=ya and y=yb at height z,
    sagging in between, gathered (big folds) at the battens."""
    rng = np.random.default_rng(seed)
    nu = max(8, int((x1 - x0) / res))
    nv = 36
    u = np.linspace(0, 1, nu, dtype=np.float32)
    v = np.linspace(0, 1, nv, dtype=np.float32)
    U, V = np.meshgrid(u, v, indexing='ij')
    X = x0 + U * (x1 - x0)
    sagx = sag * (1 + 0.12 * np.sin(2 * np.pi * (U * 1.7 + rng.uniform())))
    Y = ya + V * (yb - ya)
    Z = z - sagx * np.sin(np.pi * V)
    # surface normal in the y-z plane
    dy = (yb - ya)
    dz = -sagx * np.pi * np.cos(np.pi * V)
    nrm = np.sqrt(dy * dy + dz * dz)
    ny, nz = -dz / nrm, dy / nrm
    A = fold_amp * (1 - np.sin(np.pi * V)) ** 1.4 + 0.25 * fold_amp
    F = A * _folds(X, V, rng)
    P = np.stack([X, Y + F * ny, Z + F * nz], -1)
    ob = grid_obj(name, P, mat, coll=coll)
    add_mod(ob, 'SOLIDIFY', thickness=0.003, offset=0)
    return ob


def festoon(name, x0, x1, y, z_top, drop=0.55, scallop=0.9, sag=0.32, seed=0, mat='linen', coll=None,
            facing=-1, res=0.015):
    """Festoon valance (elevation 02 'ceiling draping'): vertical fabric along x at y, pulled up at
    cords every `scallop` m, so the hem hangs in scallops; stacked curved swag folds; billows out."""
    rng = np.random.default_rng(seed)
    L = x1 - x0
    nu = max(16, int(L / res))
    nw = 60
    u = np.linspace(0, 1, nu, dtype=np.float32)
    w = np.linspace(0, 1, nw, dtype=np.float32)
    U, W = np.meshgrid(u, w, indexing='ij')
    X = x0 + U * L
    k = (X - x0) / scallop
    fu = k - np.floor(k)                                      # 0..1 within a scallop
    bell = np.sin(np.pi * fu)
    depth = drop + sag * bell                                 # hem lower between cords
    Z = z_top - W * depth
    # stacked swag folds: curved lines w' = const, ruching amplitude grows to the hem
    wp = W * (1 + 0.25 * bell)
    nfold = 5.5
    ruche = np.sin(2 * np.pi * nfold * wp + 0.3 * np.sin(2 * np.pi * fu))
    ruche = np.sign(ruche) * np.abs(ruche) ** 0.6
    bil = 0.10 * bell * np.sin(np.pi * np.clip(W * 0.95, 0, 1)) + 0.025 * W * ruche * (0.4 + bell)
    # vertical gathers at the cords
    gath = 0.012 * (1 - bell) ** 3 * np.sin(2 * np.pi * X / 0.05 + rng.uniform(0, 6))
    Y = y + facing * (bil + gath) + 0.004 * _folds(X, W, rng, 3, (0.2, 0.5))
    P = np.stack([X, Y, Z], -1)
    ob = grid_obj(name, P, mat, coll=coll)
    add_mod(ob, 'SOLIDIFY', thickness=0.003, offset=0)
    return ob


def ring_drape(name, c, r, z_top, drop=0.9, n_scallops=18, sag=0.35, seed=0, mat='linen', coll=None,
               flare=0.25):
    """Festoon ring hung around a circular void (reference 10): scalloped hem, billowing inwards."""
    rng = np.random.default_rng(seed)
    nu = 900
    nw = 50
    th = np.linspace(0, 2 * np.pi, nu, endpoint=False, dtype=np.float32)
    w = np.linspace(0, 1, nw, dtype=np.float32)
    TH, W = np.meshgrid(th, w, indexing='ij')
    k = TH / (2 * np.pi) * n_scallops
    fu = k - np.floor(k)
    bell = np.sin(np.pi * fu)
    depth = drop + sag * bell
    Z = z_top - W * depth
    wp = W * (1 + 0.25 * bell)
    ruche = np.sin(2 * np.pi * 4.5 * wp)
    ruche = np.sign(ruche) * np.abs(ruche) ** 0.6
    R = r - flare * W ** 1.3 - 0.12 * bell * np.sin(np.pi * W) - 0.03 * W * ruche * (0.4 + bell)
    R += 0.01 * (1 - bell) ** 3 * np.sin(TH * r / 0.05 + rng.uniform(0, 6))
    P = np.stack([c[0] + R * np.cos(TH), c[1] + R * np.sin(TH), Z], -1)
    ob = grid_obj(name, P, mat, wrap_u=True, coll=coll)
    add_mod(ob, 'SOLIDIFY', thickness=0.003, offset=0)
    return ob


def curtain(name, x0, x1, y, z0, z1, gather=0.08, amp=0.05, seed=0, mat='sheer', coll=None, axis='x',
            hem_wave=0.0):
    """Hanging pleated curtain (sheer or linen) between x0..x1 (or y if axis='y') at the other coord."""
    rng = np.random.default_rng(seed)
    L = abs(x1 - x0)
    nu = max(16, int(L / 0.012))
    nv = 60
    u = np.linspace(0, 1, nu, dtype=np.float32)
    v = np.linspace(0, 1, nv, dtype=np.float32)
    U, V = np.meshgrid(u, v, indexing='ij')
    S = x0 + U * (x1 - x0)
    Z = z1 - V * (z1 - z0) + hem_wave * V ** 4 * np.sin(2 * np.pi * U * 3 + rng.uniform(0, 6))
    D = amp * _folds(S, V * 0.3, rng, 4, (gather * 0.7, gather * 1.6)) * (1 + 0.6 * V)
    if axis == 'x':
        P = np.stack([S, y + D, Z], -1)
    else:
        P = np.stack([y + D, S, Z], -1)
    ob = grid_obj(name, P, mat, coll=coll)
    add_mod(ob, 'SOLIDIFY', thickness=0.002, offset=0)
    return ob


# ----------------------------------------------------------------------------------------------
# olive tree
def olive_tree(name, base, height=6.5, spread=5.0, seed=3, leaf_mat='leaf', bark_mat='bark', coll=None,
               leaf_density=1.0, leaf_len=0.072, stems=3, levels=None, crown_z0=None):
    """Gnarled multi-stem olive: twisted stems -> limbs -> branches -> shoots -> sprays, tapered
    NURBS wood, lanceolate leaves in opposite pairs clumped on the outer shoots.
    Returns (wood_obj, leaves_obj)."""
    rng = np.random.default_rng(seed)
    base = np.asarray(base, np.float32)
    top = base[2] + height
    # per level: children (lo, hi), length (lo, hi) as fraction of parent, angle deg, radius factor,
    # up bias, droop, wander
    L = levels or [
        dict(n=(3, 4), f=(0.7, 0.9), ang=(24, 44), rf=0.62, up=0.45, droop=0.0, wander=0.12, t0=0.55),   # limbs
        dict(n=(3, 5), f=(0.5, 0.7), ang=(30, 55), rf=0.55, up=0.2, droop=0.05, wander=0.16, t0=0.4),   # branches
        dict(n=(5, 8), f=(0.30, 0.45), ang=(30, 65), rf=0.5, up=0.0, droop=0.25, wander=0.22, t0=0.45),  # shoots
        dict(n=(3, 6), f=(0.25, 0.42), ang=(25, 70), rf=0.6, up=0.0, droop=0.35, wander=0.3, t0=0.2),    # sprays
    ]
    lines, radii, leafy = [], [], []

    def walk(p, d, length, wander, up, droop, nseg=None):
        n = nseg or max(4, int(length / 0.08))
        pts = [p.copy()]
        dd = d / np.linalg.norm(d)
        for i in range(n):
            dd = dd + rng.normal(0, wander, 3) + np.array([0, 0, up * 0.2 - droop * 0.2])
            rv = pts[-1][:2] - base[:2]
            rn = np.linalg.norm(rv)
            if rn > spread * 0.5:
                dd[:2] -= rv / rn * 0.3
            if pts[-1][2] > top:
                dd[2] -= 0.5
            dd /= np.linalg.norm(dd)
            pts.append(pts[-1] + dd * length / n)
        return np.array(pts, np.float32)

    def spawn(pts, rr, lvl, length):
        if lvl >= len(L):
            leafy.append(pts)
            return
        cfg = L[lvl]
        n = int(rng.integers(cfg['n'][0], cfg['n'][1] + 1))
        tvals = np.sort(rng.uniform(cfg.get('t0', 0.3), 1.0, n))
        az0 = rng.uniform(0, 2 * np.pi)
        for c, t in enumerate(tvals):
            k = min(int(t * (len(pts) - 1)), len(pts) - 2)
            pd = pts[k + 1] - pts[k]
            pd /= np.linalg.norm(pd) + 1e-9
            # perpendicular, rotated around the parent by the golden angle
            ref = np.array([0, 0, 1.0]) if abs(pd[2]) < 0.9 else np.array([1.0, 0, 0])
            u = np.cross(pd, ref)
            u /= np.linalg.norm(u)
            v = np.cross(pd, u)
            az = az0 + c * 2.39996
            ortho = u * np.cos(az) + v * np.sin(az)
            ang = np.radians(rng.uniform(*cfg['ang']))
            cd = pd * np.cos(ang) + ortho * np.sin(ang)
            cl = length * rng.uniform(*cfg['f'])
            cr = rr[k] * cfg['rf'] * rng.uniform(0.85, 1.1)
            q = walk(pts[k], cd, cl, cfg['wander'], cfg['up'], cfg['droop'])
            qr = np.linspace(cr, max(cr * 0.45, 0.0016), len(q))
            lines.append(q)
            radii.append(qr)
            if lvl >= len(L) - 2:
                leafy.append(q)
            spawn(q, qr, lvl + 1, cl)

    trunk_h = rng.uniform(1.4, 1.9)
    for s_ in range(stems):
        a = 2 * np.pi * s_ / stems + rng.uniform(-0.4, 0.4)
        p0 = base + np.array([np.cos(a) * 0.1, np.sin(a) * 0.1, 0], np.float32)
        lean = np.array([np.cos(a) * 0.35, np.sin(a) * 0.35, 1.0])
        pts = [p0]
        d = lean / np.linalg.norm(lean)
        for i in range(12):
            tw = np.array([np.cos(a + i * 0.45), np.sin(a + i * 0.45), 0]) * 0.16
            d = d + tw + rng.normal(0, 0.06, 3)
            d[2] = max(d[2], 0.75)
            d /= np.linalg.norm(d)
            pts.append(pts[-1] + d * trunk_h / 12)
        pts = np.array(pts, np.float32)
        tt = np.linspace(0, 1, len(pts))
        rr = (0.15 - 0.04 * tt) * (1 + 0.45 * np.exp(-tt * 9))                 # root flare
        lines.append(pts)
        radii.append(rr)
        limb_len = (height - trunk_h) * 0.85
        spawn(pts, rr, 0, limb_len)

    wood = curve_obj(name + '_wood', lines, radii, bark_mat, coll, bevel_res=2)
    # leaves: clumped on the outer part of each leafy shoot
    tmpl_u = np.array([0.0, 0.16, 0.16, 0.5, 0.5, 0.84, 0.84, 1.0], np.float32)
    tmpl_w = np.array([0.0, -0.8, 0.8, -1.0, 1.0, -0.62, 0.62, 0.0], np.float32)
    tmpl_f = [[0, 1, 2], [1, 3, 4, 2], [3, 5, 6, 4], [5, 7, 6]]
    V, F, R = [], [], []
    nleaf = 0
    for pts in leafy:
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        cum = np.concatenate([[0], np.cumsum(seg)])
        total = cum[-1]
        spacing = 0.0125 / leaf_density
        s0 = total * rng.uniform(0.1, 0.3)
        n = int((total - s0) / spacing)
        for i in range(n):
            s = s0 + (i + rng.uniform(0, 0.4)) * spacing
            k = int(np.clip(np.searchsorted(cum, s) - 1, 0, len(pts) - 2))
            t = (s - cum[k]) / (seg[k] + 1e-9)
            p = pts[k] + (pts[k + 1] - pts[k]) * t
            td = pts[k + 1] - pts[k]
            td /= np.linalg.norm(td) + 1e-9
            ref = np.array([0, 0, 1.0]) if abs(td[2]) < 0.9 else np.array([1.0, 0, 0])
            u = np.cross(td, ref)
            u /= np.linalg.norm(u)
            v = np.cross(td, u)
            roll = rng.uniform(0, 2 * np.pi)
            for side in (-1, 1):
                ax = u * np.cos(roll) + v * np.sin(roll)
                ang = np.radians(rng.uniform(18, 60))
                ld = td * np.cos(ang) + ax * side * np.sin(ang)
                ld = ld + rng.normal(0, 0.32, 3)
                ld[2] -= rng.uniform(0.1, 0.55)
                ld /= np.linalg.norm(ld)
                wd = np.cross(ld, ax)
                if np.linalg.norm(wd) < 1e-3:
                    wd = np.cross(ld, [0, 0, 1])
                wd /= np.linalg.norm(wd)
                upv = np.cross(wd, ld)
                ll = leaf_len * rng.uniform(0.75, 1.2)
                ww = ll * rng.uniform(0.14, 0.19) / 2
                fold = rng.uniform(0.2, 0.4)
                curl = rng.uniform(-0.15, 0.1)
                vu, vw = tmpl_u * ll, tmpl_w * ww
                vv = np.abs(tmpl_w) * ww * fold + curl * tmpl_u ** 2 * ll
                V.append(p[None] + vu[:, None] * ld + vw[:, None] * wd + vv[:, None] * upv)
                F.extend([[nleaf * 8 + q for q in f] for f in tmpl_f])
                R.append(np.full(8, rng.uniform(), np.float32))
                nleaf += 1
    leaves = mesh_obj(name + '_leaves', np.concatenate(V), F, leaf_mat, smooth=True,
                      attrs={'rnd': ('POINT', np.concatenate(R))}, coll=coll)
    return wood, leaves


# ----------------------------------------------------------------------------------------------
# glass blocks
def glass_block_panel(name, origin, nx, nz, axis='x', block=0.19, joint=0.012, depth=0.08, coll=None,
                      frame_mat='mortar'):
    """Wall of glass blocks in a vertical plane. origin = bottom-left corner (centre of thickness).
    axis: 'x' -> wall runs along +x (faces +-y); 'y' -> runs along +y (faces +-x)."""
    pitch = block + joint
    bm = bmesh.new()
    for i in range(nx):
        for k in range(nz):
            res = bmesh.ops.create_cube(bm, size=1.0)
            vs = res['verts']
            bmesh.ops.scale(bm, vec=Vector((block, depth, block)), verts=vs)
            bmesh.ops.translate(bm, vec=Vector((joint + i * pitch + block / 2, 0, joint + k * pitch + block / 2)),
                                verts=vs)
    blocks = bm_obj(name + '_blocks', bm, 'glass_block', smooth=False, coll=coll)
    bevel(blocks, 0.012, 3)
    # mortar grid
    bm = bmesh.new()
    W = nx * pitch + joint
    H = nz * pitch + joint
    for i in range(nx + 1):
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=Vector((joint, depth * 0.8, H)), verts=r['verts'])
        bmesh.ops.translate(bm, vec=Vector((i * pitch + joint / 2, 0, H / 2)), verts=r['verts'])
    for k in range(nz + 1):
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=Vector((W, depth * 0.8, joint)), verts=r['verts'])
        bmesh.ops.translate(bm, vec=Vector((W / 2, 0, k * pitch + joint / 2)), verts=r['verts'])
    mortar = bm_obj(name + '_mortar', bm, frame_mat, smooth=False, coll=coll)
    for ob in (blocks, mortar):
        ob.location = origin
        if axis == 'y':
            ob.rotation_euler = (0, 0, math.pi / 2)
    return blocks, mortar, (W, H)


# ----------------------------------------------------------------------------------------------
# cabins (elevation 02 / plan): curved fluted oak shell, round velvet sofa, round table, pendant
def fluted_arc(name, c, r, a0, a1, h, thick=0.07, flute=0.045, depth=0.012, mat='oak', coll=None, top_round=0.0):
    """Curved wall (arc from angle a0 to a1, radians) with vertical half-round flutes outside and
    inside. Top edge optionally rounded down at both ends (elevation shows rounded shoulders)."""
    arc = abs(a1 - a0) * r
    nu = max(60, int(arc / (flute / 6)))
    nv = 40
    th = np.linspace(a0, a1, nu, dtype=np.float32)
    z = np.linspace(0, h, nv, dtype=np.float32)
    TH, Z = np.meshgrid(th, z, indexing='ij')
    s = (TH - a0) * r
    fl = np.abs(np.sin(np.pi * s / flute)) ** 0.5 * depth
    # rounded shoulders at the free ends: drop the top near each end
    if top_round > 0:
        e = np.minimum(s, arc - s)
        cut = np.where(e < top_round, top_round - np.sqrt(np.maximum(0, top_round ** 2 - (top_round - e) ** 2)), 0)
        Z = np.minimum(Z, h - cut)
    ro = r + thick / 2 + fl
    ri = r - thick / 2 - fl * 0.6
    outer = np.stack([c[0] + ro * np.cos(TH), c[1] + ro * np.sin(TH), Z], -1)
    inner = np.stack([c[0] + ri * np.cos(TH), c[1] + ri * np.sin(TH), Z], -1)
    o1 = grid_obj(name + '_out', outer, mat, coll=coll)
    o2 = grid_obj(name + '_in', inner[:, ::-1], mat, coll=coll)
    # top cap
    top = np.stack([outer[:, -1], inner[:, -1]], 1)
    o3 = grid_obj(name + '_top', top, mat, coll=coll)
    ends = []
    for idx in (0, -1):
        e = np.stack([outer[idx], inner[idx]], 1)
        ends.append(grid_obj(name + f'_end{idx}', e, mat, coll=coll))
    return [o1, o2, o3] + ends


def channel_back(name, c, r, a0, a1, z0, h, lean=0.12, channels=0.16, puff=0.03, mat='velvet', coll=None):
    """Curved channel-tufted backrest (vertical channels), leaning back."""
    nu = int(abs(a1 - a0) * r / 0.01)
    nv = 30
    th = np.linspace(a0, a1, nu, dtype=np.float32)
    v = np.linspace(0, 1, nv, dtype=np.float32)
    TH, V = np.meshgrid(th, v, indexing='ij')
    s = (TH - a0) * r
    ch = np.abs(np.sin(np.pi * s / channels)) ** 0.45 * puff * np.sin(np.pi * np.clip(V * 1.05, 0, 1)) ** 0.5
    R = r + lean * V - ch
    Z = z0 + V * h
    # rolled top
    P = np.stack([c[0] + R * np.cos(TH), c[1] + R * np.sin(TH), Z], -1)
    ob = grid_obj(name, P, mat, coll=coll)
    add_mod(ob, 'SOLIDIFY', thickness=0.10, offset=1)
    subsurf(ob, 1)
    return ob


def seat_ring(name, c, r_in, r_out, a0, a1, z, h, mat='velvet', coll=None):
    """Curved seat cushion (annular sector), soft edges."""
    bm = bmesh.new()
    n = max(24, int(abs(a1 - a0) * r_out / 0.06))
    th = np.linspace(a0, a1, n)
    vs = []
    for t in th:
        ring = [bm.verts.new((c[0] + rr * math.cos(t), c[1] + rr * math.sin(t), zz))
                for rr, zz in ((r_in, z), (r_out, z), (r_out, z + h), (r_in, z + h))]
        vs.append(ring)
    for i in range(n - 1):
        for k in range(4):
            bm.faces.new((vs[i][k], vs[i + 1][k], vs[i + 1][(k + 1) % 4], vs[i][(k + 1) % 4]))
    bm.faces.new(vs[0][::-1])
    bm.faces.new(vs[-1])
    ob = bm_obj(name, bm, mat, coll=coll)
    bevel(ob, 0.035, 4)
    return ob


def round_table(name, loc, r=0.5, h=0.75, top='marble_white', base='brass', coll=None, top_th=0.03):
    x, y = loc[0], loc[1]
    t = cyl(name + '_top', r, top_th, (x, y, h - top_th / 2), top, seg=96, coll=coll)
    bevel(t, 0.006, 3)
    col = lathe(name + '_base', [(0.0, 0.0), (0.27, 0.0), (0.27, 0.015), (0.06, 0.03), (0.045, 0.1),
                                 (0.045, h - 0.06), (0.11, h - top_th - 0.01), (0.0, h - top_th - 0.01)],
                (x, y, 0), base, seg=64, coll=coll)
    return [t, col]


def pendant_dome(name, loc, r=0.24, z_ceiling=5.0, mat='brass', coll=None, light=True, power=40.0, inner='lampshade'):
    """Dome pendant (elevations 01/02): spun shell + cord to the ceiling + bulb + point light."""
    x, y, z = loc
    prof = [(0.012, r * 0.62), (r * 0.22, r * 0.6), (r * 0.62, r * 0.48), (r * 0.9, r * 0.25), (r, 0.0),
            (r * 0.985, -0.006)]
    shell = lathe(name + '_shell', prof, (x, y, z), mat, seg=72, coll=coll)
    add_mod(shell, 'SOLIDIFY', thickness=0.004, offset=1)
    lining = lathe(name + '_lining', [(p[0] * 0.97, p[1] - 0.004) for p in prof[:-1]], (x, y, z), inner, seg=72,
                   coll=coll)
    cord = cyl(name + '_cord', 0.004, z_ceiling - (z + r * 0.6), (x, y, (z_ceiling + z + r * 0.6) / 2), 'rope', seg=8,
               coll=coll)
    bulb = cyl(name + '_bulb', 0.035, 0.03, (x, y, z + 0.01), 'bulb', seg=24, coll=coll)
    out = [shell, lining, cord, bulb]
    if light:
        ld = bpy.data.lights.new(name + '_L', 'SPOT')
        ld.energy = power
        ld.spot_size = math.radians(150)
        ld.spot_blend = 0.6
        ld.shadow_soft_size = 0.04
        ld.color = (1.0, 0.72, 0.45)
        lo = bpy.data.objects.new(name + '_L', ld)
        lo.location = (x, y, z + 0.005)
        link(lo, coll)
        # soft fill bounced off the inner shell
        ld2 = bpy.data.lights.new(name + '_up', 'POINT')
        ld2.energy = power * 0.25
        ld2.shadow_soft_size = 0.05
        ld2.color = (1.0, 0.75, 0.5)
        lo2 = bpy.data.objects.new(name + '_up', ld2)
        lo2.location = (x, y, z + 0.06)
        link(lo2, coll)
        out += [lo, lo2]
    return out


def tub_chair(name, loc, rot=0.0, mat='velvet', leg='walnut', coll=None, seat_h=0.46):
    """Upholstered tub dining chair: curved back/arms shell, seat cushion, four tapered legs."""
    x, y = loc[0], loc[1]
    parts = []
    # shell: arc of 250 deg around the seat, height ramps from arms (0.62) to back (0.78)
    nu, nv = 80, 12
    a = np.linspace(-np.radians(125), np.radians(125), nu)
    v = np.linspace(0, 1, nv)
    A, V = np.meshgrid(a, v, indexing='ij')
    top = 0.64 + 0.14 * np.cos(A / 2.2) ** 2
    R = 0.27 + 0.03 * V
    Z = seat_h - 0.06 + V * (top - seat_h + 0.06)
    P = np.stack([R * np.cos(A + np.pi), R * np.sin(A + np.pi), Z], -1)    # opening faces +x
    sh = grid_obj(name + '_shell', P.astype(np.float32), mat, coll=coll)
    add_mod(sh, 'SOLIDIFY', thickness=0.06, offset=1)
    subsurf(sh, 2)
    parts.append(sh)
    seat = cyl(name + '_seat', 0.26, 0.08, (0, 0, seat_h - 0.02), mat, seg=48, coll=coll)
    bevel(seat, 0.03, 4)
    parts.append(seat)
    base = cyl(name + '_base', 0.27, 0.05, (0, 0, seat_h - 0.08), leg, seg=48, coll=coll)
    parts.append(base)
    for i in range(4):
        t = np.pi / 4 + i * np.pi / 2
        lx, ly = 0.19 * math.cos(t), 0.19 * math.sin(t)
        lg = cyl(name + f'_leg{i}', 0.018, seat_h - 0.1, (lx, ly, (seat_h - 0.1) / 2), leg, seg=12, coll=coll, r2=0.022)
        parts.append(lg)
    parent = bpy.data.objects.new(name, None)
    link(parent, coll)
    for p in parts:
        p.parent = parent
    parent.location = (x, y, 0)
    parent.rotation_euler = (0, 0, rot)
    return parent


def wine_glass(name, loc, fill=0.0, coll=None):
    prof = [(0.0, 0.0), (0.035, 0.0), (0.036, 0.002), (0.006, 0.006), (0.0035, 0.02), (0.0035, 0.10),
            (0.012, 0.115), (0.034, 0.14), (0.042, 0.17), (0.04, 0.2), (0.034, 0.225)]
    g = lathe(name, prof, loc, 'wine_glass', seg=64, coll=coll)
    add_mod(g, 'SOLIDIFY', thickness=0.0012, offset=-1)
    out = [g]
    if fill > 0:
        zf = 0.115 + fill
        w = lathe(name + '_wine', [(0.0, 0.117), (0.012, 0.117), (0.03, 0.14), (0.038, min(zf, 0.17)), (0.0, min(zf, 0.17))],
                  loc, 'wine', seg=48, coll=coll)
        out.append(w)
    return out


def plate(name, loc, r=0.14, coll=None):
    prof = [(0.0, 0.0), (r * 0.6, 0.0), (r * 0.66, 0.006), (r * 0.95, 0.014), (r, 0.017), (r * 0.98, 0.019),
            (r * 0.93, 0.016), (r * 0.64, 0.009), (0.0, 0.009)]
    return lathe(name, prof, loc, 'ceramic', seg=72, coll=coll)


def mushroom_lamp(name, loc, coll=None, power=6.0):
    """Brass mushroom table lamp (reference 11) with warm glow under the cap."""
    x, y, z = loc
    stem = lathe(name + '_stem', [(0.0, 0.0), (0.06, 0.0), (0.06, 0.008), (0.012, 0.02), (0.012, 0.2), (0.0, 0.2)],
                 (x, y, z), 'brass', coll=coll)
    cap = lathe(name + '_cap', [(0.0, 0.29), (0.05, 0.285), (0.11, 0.255), (0.135, 0.215), (0.13, 0.205),
                                (0.1, 0.215), (0.0, 0.22)], (x, y, z), 'brass', coll=coll)
    ld = bpy.data.lights.new(name + '_L', 'POINT')
    ld.energy = power
    ld.shadow_soft_size = 0.03
    ld.color = (1.0, 0.68, 0.40)
    lo = bpy.data.objects.new(name + '_L', ld)
    lo.location = (x, y, z + 0.19)
    link(lo, coll)
    glow = cyl(name + '_glow', 0.03, 0.01, (x, y, z + 0.205), 'bulb', seg=24, coll=coll)
    return [stem, cap, lo, glow]


def candle(name, loc, coll=None, h=0.07):
    x, y, z = loc
    holder = lathe(name + '_holder', [(0.0, 0.0), (0.035, 0.0), (0.035, 0.05), (0.031, 0.05), (0.031, 0.004),
                                      (0.0, 0.004)], (x, y, z), 'wine_glass', coll=coll)
    c = cyl(name + '_wax', 0.022, h, (x, y, z + h / 2 + 0.004), 'candle', seg=24, coll=coll)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.006)
    bmesh.ops.scale(bm, vec=Vector((1, 1, 2.6)), verts=bm.verts)
    fl = bm_obj(name + '_flame', bm, 'flame', coll=coll, loc=(x, y, z + h + 0.02))
    ld = bpy.data.lights.new(name + '_L', 'POINT')
    ld.energy = 0.8
    ld.shadow_soft_size = 0.01
    ld.color = (1.0, 0.55, 0.25)
    lo = bpy.data.objects.new(name + '_L', ld)
    lo.location = (x, y, z + h + 0.025)
    link(lo, coll)
    return [holder, c, fl, lo]


def area_light(name, loc, size, energy, color=(1.0, 0.75, 0.5), rot=(0, 0, 0), coll=None, shape='RECTANGLE',
               spread=180.0, camera=False):
    """size = (local x, local y). Hidden from camera rays unless camera=True (e.g. a glow meant to
    be seen through glass blocks)."""
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape = shape
    ld.size = size[0]
    ld.size_y = size[1]
    ld.energy = energy
    ld.color = color
    ld.spread = math.radians(spread)
    lo = bpy.data.objects.new(name, ld)
    lo.location = loc
    lo.rotation_euler = rot
    lo.visible_camera = camera
    link(lo, coll)
    return lo


def point_light(name, loc, energy, color=(1.0, 0.72, 0.45), radius=0.05, coll=None):
    ld = bpy.data.lights.new(name, 'POINT')
    ld.energy = energy
    ld.color = color
    ld.shadow_soft_size = radius
    lo = bpy.data.objects.new(name, ld)
    lo.location = loc
    link(lo, coll)
    return lo


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def disc_with_hole(name, outer_rect, hole_c, hole_r, z, th, mat, coll=None, seg=128):
    """Floor slab (rectangle) with a round void cut out, via an exact boolean."""
    (x0, y0, x1, y1) = outer_rect
    slab = box(name, (x1 - x0, y1 - y0, th), ((x0 + x1) / 2, (y0 + y1) / 2, z + th / 2), mat, coll=coll)
    cutter = cyl(name + '_cut', hole_r, th * 3, (hole_c[0], hole_c[1], z + th / 2), None, seg=seg, coll=coll)
    m = add_mod(slab, 'BOOLEAN', operation='DIFFERENCE', solver='EXACT')
    m.object = cutter
    cutter.hide_render = True
    cutter.hide_viewport = True
    return slab


def apply_matrix(ob, M):
    ob.matrix_world = Matrix(M) @ ob.matrix_world
