"""scene — the client's restaurant (ground floor east half + the double-height void) for v2.

Layout from the drawings, simplified where a collage does not need precision (metres):
  ground floor z 0..5.0 · slab 5.0..5.35 · first floor 5.35..9.0 · roof 9.0..9.4
  x -10 (west, party hall curtains) .. 16 (glazed entrance facade, east)
  y -8 (south) .. 8 (north, kitchen wall in painted white brick)
  open void: circle centre (9, 0), R 3.6, round rooflight above, olive tree in a stone planter
  four private cabins on the north side: curved fluted oak shells 2.4 m high, open above,
  round velvet sofa, round marble table, dome pendant each (elevation 02)
  ceiling draping: catenary swags across the dining room; festoon valance along the cabins;
  festoon ring around the void
  glass blocks: facade panel + a free-standing screen by the cabins

    build(view)  -> camera for view 1 (from within the void, looking out) or 2 (towards the cabins)
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Vector

import geo as G
from nodes import material

GF, SLAB, FF, ROOF = 5.0, 0.35, 9.0, 0.4
VOID_C, VOID_R = (9.0, 0.0), 3.6
X0, X1, Y0, Y1 = -10.0, 16.0, -8.0, 8.0
CABINS = [(5.0, 5.7), (1.2, 5.7), (-2.6, 5.7), (-6.4, 5.7)]
CAB_R = 1.7
TREE = (9.6, 1.2, 0.0)
STREET_TREE = [
    dict(n=(3, 4), f=(0.6, 0.8), ang=(20, 40), rf=0.6, up=0.6, droop=0.0, wander=0.1, t0=0.5),
    dict(n=(4, 6), f=(0.45, 0.6), ang=(30, 55), rf=0.55, up=0.2, droop=0.05, wander=0.15, t0=0.4),
    dict(n=(5, 7), f=(0.35, 0.5), ang=(30, 60), rf=0.5, up=0.05, droop=0.15, wander=0.2, t0=0.4),
]
SUN_AZ, SUN_EL = 250.0, 27.0          # late-afternoon sun from the west-south-west: the street glows


def coll(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


# ----------------------------------------------------------------------------------------------
def shell():
    c = coll('shell')
    G.box('floor', (X1 - X0 + 2, Y1 - Y0 + 2, 0.2), ((X0 + X1) / 2, 0, -0.1), 'travertine', coll=c)
    # ground-floor ceiling slab with the void
    G.disc_with_hole('slab1', (X0, Y0, X1, Y1), VOID_C, VOID_R, GF, SLAB, 'plaster', coll=c)
    # slab edge band around the void (concrete) - a thin ring
    ring = G.lathe('void_edge', [(VOID_R - 0.001, GF - 0.001), (VOID_R - 0.001, GF + SLAB + 0.001)],
                   (VOID_C[0], VOID_C[1], 0), 'concrete', seg=160, coll=c)
    ring.data.flip_normals()
    # first-floor ceiling / roof with round rooflight
    G.disc_with_hole('roof', (X0, Y0, X1, Y1), VOID_C, 2.4, FF, ROOF, 'plaster', coll=c)
    rl = G.lathe('rooflight_upstand', [(2.4, FF), (2.4, FF + ROOF + 0.25)], (VOID_C[0], VOID_C[1], 0), 'plaster',
                 seg=128, coll=c)
    rl.data.flip_normals()
    G.cyl('rooflight_glass', 2.42, 0.01, (VOID_C[0], VOID_C[1], FF + ROOF + 0.25), 'window_glass', seg=128, coll=c)
    # first floor floor finish (seen through the void)
    # walls
    G.box_uv('wall_N_brick', (X1 - X0, 0.3, GF), ((X0 + X1) / 2, Y1 + 0.15, GF / 2), 'white_brick', coll=c)
    G.box('wall_N_ff', (X1 - X0, 0.3, FF - GF), ((X0 + X1) / 2, Y1 + 0.15, (GF + FF) / 2), 'plaster', coll=c)
    G.box('wall_S', (X1 - X0, 0.3, FF), ((X0 + X1) / 2, Y0 - 0.15, FF / 2), 'plaster', coll=c)
    G.box('wall_W', (0.3, Y1 - Y0, FF), (X0 - 0.15, 0, FF / 2), 'plaster', coll=c)
    # stainless rail around the void at first floor
    rail = []
    for z in (GF + SLAB + 1.05, GF + SLAB + 0.55):
        rail.append(G.lathe(f'rail_{z:.2f}', [(VOID_R - 0.06, z - 0.02), (VOID_R - 0.04, z), (VOID_R - 0.06, z + 0.02),
                                              (VOID_R - 0.08, z)], (VOID_C[0], VOID_C[1], 0), 'steel', seg=160, coll=c))
    for i in range(48):
        a = 2 * math.pi * i / 48
        G.cyl(f'post{i}', 0.012, 1.05, (VOID_C[0] + (VOID_R - 0.06) * math.cos(a),
                                       VOID_C[1] + (VOID_R - 0.06) * math.sin(a), GF + SLAB + 0.525), 'steel',
              seg=12, coll=c)
    # glass balustrade panel inside the rail
    gb = G.lathe('rail_glass', [(VOID_R - 0.05, GF + SLAB + 0.05), (VOID_R - 0.05, GF + SLAB + 1.0)],
                 (VOID_C[0], VOID_C[1], 0), 'window_glass', seg=160, coll=c)
    _ = gb


def facade():
    """East facade at x = 16: split-face stone piers, bronze-framed glazing, a glass-block panel,
    sheer curtains; first floor glazing above."""
    c = coll('facade')
    X = X1
    piers = [(-8.0, -7.1), (-3.7, -2.8), (2.8, 3.7), (7.1, 8.0)]
    for i, (a, b) in enumerate(piers):
        ob = G.box_uv(f'pier{i}', (0.5, b - a, GF), (X + 0.1, (a + b) / 2, GF / 2), 'split_face', coll=c)
        G.adaptive(ob, 1.5)
    # lintel band
    G.box('lintel', (0.5, Y1 - Y0, 0.42), (X + 0.1, 0, GF - 0.21), 'concrete', coll=c)
    bays = [(-7.1, -3.7), (-2.8, 0.6), (3.7, 7.1)]
    for i, (a, b) in enumerate(bays):
        glazing(f'bay{i}', X, a, b, 0.0, GF - 0.42, c, transom=3.3)
    # glass-block panel (client loves glass brick), backlit by the low sun
    nx = int((2.8 - 0.6) / 0.202)
    nz = int((GF - 0.42) / 0.202)
    G.glass_block_panel('gb_facade', (X, 0.6, 0.0), nx, nz, axis='y', coll=c)
    # warm glow behind the glass blocks only: local x -> vertical (4.3 m), local y -> along y (2.0 m)
    G.area_light('gb_facade_sun', (X + 0.7, 1.7, 2.3), (4.2, 1.7), 300, color=(1.0, 0.82, 0.60),
                 rot=(0, math.radians(90), 0), coll=c)   # emits towards -x, through the blocks
    # sheer curtains, partly drawn
    G.curtain('sheer0', -7.0, -5.6, X - 0.25, 0.02, GF - 0.45, axis='y', seed=1, coll=c)
    G.curtain('sheer1', -2.7, -1.6, X - 0.25, 0.02, GF - 0.45, axis='y', seed=2, coll=c)
    G.curtain('sheer2', 5.9, 7.0, X - 0.25, 0.02, GF - 0.45, axis='y', seed=3, coll=c)
    G.curtain('sheer3', 3.8, 4.6, X - 0.25, 0.02, GF - 0.45, axis='y', seed=4, coll=c)
    # first floor: concrete band + tall glazing
    G.box('ff_band', (0.5, Y1 - Y0, SLAB + 0.3), (X + 0.1, 0, GF + (SLAB + 0.3) / 2), 'concrete', coll=c)
    for i, (a, b) in enumerate(bays):
        glazing(f'ffbay{i}', X, a, b, GF + SLAB + 0.3, FF - 0.3, c, transom=None)
    for i, (a, b) in enumerate(piers + [(0.6, 2.8)]):
        ob = G.box_uv(f'ffpier{i}', (0.5, b - a, FF - GF - SLAB - 0.3), (X + 0.1, (a + b) / 2, (FF + GF + SLAB + 0.3) / 2),
                      'split_face', coll=c)
        G.adaptive(ob, 2.0)
    G.box('ff_top', (0.5, Y1 - Y0, 0.3), (X + 0.1, 0, FF - 0.15), 'concrete', coll=c)


def glazing(name, X, y0, y1, z0, z1, c, transom=3.3, mull=1.13):
    G.box(name + '_glass', (0.012, y1 - y0, z1 - z0), (X, (y0 + y1) / 2, (z0 + z1) / 2), 'window_glass', coll=c)
    n = max(1, round((y1 - y0) / mull))
    for i in range(n + 1):
        y = y0 + (y1 - y0) * i / n
        G.box(f'{name}_m{i}', (0.12, 0.06, z1 - z0), (X, y, (z0 + z1) / 2), 'bronze_frame', coll=c)
    for z in [z0 + 0.03, z1 - 0.03] + ([transom] if transom else []):
        G.box(f'{name}_t{z:.1f}', (0.12, y1 - y0, 0.06), (X, (y0 + y1) / 2, z), 'bronze_frame', coll=c)


def street():
    """Outside the entrance: pavement, road, street trees, a terrace of two- and three-storey
    shops and houses opposite in late sun (brick, cream render, pale stone), awnings, lit shops."""
    c = coll('street')
    G.box('pavement', (4.0, 70, 0.15), (18.0, 0, -0.06), 'paving', coll=c)
    G.box('kerb', (0.2, 70, 0.17), (20.0, 0, -0.04), 'stone_rough', coll=c)
    G.box('road', (8.0, 70, 0.1), (24.0, 0, -0.1), 'asphalt', coll=c)
    G.box('pavement2', (3.0, 70, 0.15), (29.5, 0, -0.06), 'paving', coll=c)
    rng = np.random.default_rng(5)
    y = -26.0
    k = 0
    FX = 31.0                                                   # facade line opposite
    kinds = ['brick_red', 'plaster_out', 'stone_out', 'brick_red', 'plaster_out', 'stone_out']
    while y < 26:
        w = float(rng.choice([6.0, 7.2, 8.4]))
        floors = int(rng.choice([2, 3, 3]))
        fh = 3.3
        h = floors * fh + 0.9
        mat = kinds[k % len(kinds)]
        G.box(f'bldg{k}', (6, w - 0.06, h), (FX + 3.0, y + w / 2, h / 2), mat, coll=c)
        trim = 'stone_out' if mat != 'stone_out' else 'plaster_out'
        # upper windows with surrounds and sills
        nwin = max(2, int(w / 2.1))
        for fl in range(1, floors):
            for j in range(nwin):
                wy = y + (j + 0.5) * w / nwin
                z0 = fl * fh + 0.55
                G.box(f'win{k}_{fl}_{j}', (0.06, 1.0, 1.9), (FX - 0.02, wy, z0 + 0.95), 'facade_windows', coll=c)
                G.box(f'surr{k}_{fl}_{j}', (0.08, 1.24, 2.14), (FX - 0.005, wy, z0 + 0.95), trim, coll=c)
                G.box(f'sill{k}_{fl}_{j}', (0.22, 1.36, 0.09), (FX - 0.08, wy, z0 - 0.08), trim, coll=c)
            G.box(f'band{k}_{fl}', (0.12, w, 0.18), (FX - 0.04, y + w / 2, fl * fh), trim, coll=c)
        # shopfront: bronze frame, lit interior, fascia, striped awning
        G.box(f'shop{k}', (0.06, w - 1.4, 2.5), (FX - 0.04, y + w / 2, 1.35), 'shopfront', coll=c)
        for j in range(4):
            G.box(f'shopm{k}_{j}', (0.1, 0.07, 2.5), (FX - 0.07, y + 0.7 + j * (w - 1.4) / 3, 1.35), 'bronze_frame', coll=c)
        G.box(f'fascia{k}', (0.14, w - 1.0, 0.55), (FX - 0.07, y + w / 2, 2.95), 'bronze_frame' if k % 2 else 'awning',
              coll=c)
        if k % 3 != 2:
            aw = G.box(f'awning{k}', (1.6, w - 1.6, 0.03), (FX - 0.75, y + w / 2, 2.55), 'awning_stripe', coll=c)
            aw.rotation_euler = (0, math.radians(16), 0)
        G.box(f'cornice{k}', (0.45, w, 0.32), (FX - 0.1, y + w / 2, h - 0.25), trim, coll=c)
        y += w
        k += 1
    for i, ty in enumerate((-5.0, 4.5, 13.0)):
        G.olive_tree(f'streettree{i}', (18.6, ty, 0.0), height=8.0, spread=5.0, seed=20 + i, leaf_mat='leaf_street',
                     coll=c, leaf_density=1.8, leaf_len=0.075, stems=1, levels=STREET_TREE)
        G.cyl(f'treepit{i}', 0.7, 0.05, (18.6, ty, 0.0), 'soil', coll=c)
    G.cyl('lamppost', 0.05, 4.5, (18.9, 1.0, 2.25), 'black_metal', seg=12, coll=c)
    G.lathe('lamphead', [(0.0, 4.45), (0.18, 4.5), (0.12, 4.75), (0.0, 4.8)], (18.9, 1.0, 0), 'black_metal', coll=c)


def void_and_tree():
    c = coll('void')
    x, y, _ = TREE
    # stone planter ring with soil and pebbles
    outer = G.lathe('planter', [(0.0, 0.0), (1.0, 0.0), (1.0, 0.42), (0.9, 0.45), (0.86, 0.42), (0.86, 0.36), (0.0, 0.36)],
                    (x, y, 0), 'stone_rough', seg=128, coll=c)
    G.bevel(outer, 0.01, 2)
    G.cyl('soil', 0.86, 0.02, (x, y, 0.37), 'soil', seg=96, coll=c)
    rng = np.random.default_rng(9)
    import bmesh
    bm = bmesh.new()
    for i in range(380):
        r = 0.86 * math.sqrt(rng.uniform(0.04, 1))
        a = rng.uniform(0, 2 * math.pi)
        res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=rng.uniform(0.018, 0.04))
        from mathutils import Vector
        bmesh.ops.scale(bm, vec=Vector((1, rng.uniform(0.7, 1), rng.uniform(0.45, 0.7))), verts=res['verts'])
        bmesh.ops.translate(bm, vec=Vector((x + r * math.cos(a), y + r * math.sin(a), 0.385)), verts=res['verts'])
    G.bm_obj('pebbles', bm, 'pebble', coll=c)
    G.olive_tree('olive', (x, y, 0.36), height=7.0, spread=5.8, seed=3, coll=c, leaf_density=1.5)
    # festoon ring under the roof around the void + a lower inner ring (reference 10)
    G.ring_drape('void_ring_a', VOID_C, VOID_R - 0.2, FF - 0.02, drop=0.75, n_scallops=22, sag=0.35, seed=1,
                 mat='linen', coll=c, flare=0.3)
    G.ring_drape('void_ring_b', VOID_C, VOID_R - 0.65, FF - 0.35, drop=0.7, n_scallops=18, sag=0.3, seed=2,
                 mat='linen', coll=c, flare=0.3)


def drapes():
    """Ceiling draping (sections A-A, B-B; elevations 02, 04)."""
    c = coll('drapes')
    # east zone, between void and facade: swag rows parallel to the facade (along y)
    for i, xb in enumerate((12.9, 13.75, 14.6, 15.45)):         # first batten 15 cm behind the festoon
        sw = G.swag(f'swagE{i}', Y0 + 0.2, Y1 - 0.2, xb, xb + 0.85, GF - 0.02, sag=0.58, seed=10 + i, coll=c,
                     fold_amp=0.05)
        # swag() spans along its first axis; rotate it so the span runs along y
        _rotate_xy_swap(sw)
    # dining room west of the void: swag rows along the room (battens along x, 1.0 m apart), so
    # the catenaries read as a rippling 'layered' ceiling when looking along the room
    yb = Y0 + 0.3
    i = 0
    while yb < Y1 - 1.2:
        G.swag(f'swagW{i}', X0 + 0.3, VOID_C[0] - VOID_R - 0.4, yb, yb + 1.0, GF - 0.02, sag=0.42 + 0.06 * (i % 2),
               seed=40 + i, coll=c, fold_amp=0.045)
        yb += 1.0
        i += 1
    fe = G.festoon('festoon_void_east', -6.5, 6.5, VOID_C[0] + VOID_R + 0.15, GF - 0.02, drop=0.5, scallop=0.95,
                   sag=0.32, seed=7, coll=c, facing=1)
    _rotate_xy_swap(fe)
    # festoon valance along the front of the cabins (elevation 02 'ceiling draping')
    G.festoon('festoon_cabins', -8.6, 7.0, 3.55, GF - 0.02, drop=0.45, scallop=0.95, sag=0.3, seed=5, coll=c)
    # party-hall curtains at the far west wall (elevation 04)
    for i in range(6):
        G.curtain(f'party_curtain{i}', Y0 + 0.4 + i * 2.6, Y0 + 0.4 + i * 2.6 + 2.0, X0 + 0.35, 0.0, GF - 0.1,
                  axis='y', gather=0.12, amp=0.07, seed=60 + i, mat='linen', coll=c)


def _rotate_xy_swap(ob):
    """swag(name, x0, x1, ya, yb...) built along x; we passed y-range as x-range and x-battens as y:
    mirror coordinates (x, y) -> (y, x)."""
    me = ob.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    co[:, [0, 1]] = co[:, [1, 0]]
    me.vertices.foreach_set('co', co.ravel())
    me.flip_normals()
    me.update()


def cabins():
    c = coll('cabins')
    for i, (cx, cy) in enumerate(CABINS):
        a0, a1 = math.radians(-38), math.radians(218)
        G.fluted_arc(f'cabin{i}', (cx, cy), CAB_R, a0, a1, 2.4, mat='oak', coll=c, top_round=0.35)
        # round sofa inside: seat + channel back
        G.seat_ring(f'sofa_seat{i}', (cx, cy), CAB_R - 0.75, CAB_R - 0.12, math.radians(-20), math.radians(200), 0.0, 0.46,
                    mat='velvet', coll=c)
        G.channel_back(f'sofa_back{i}', (cx, cy), CAB_R - 0.26, math.radians(-18), math.radians(198), 0.42, 0.62,
                       lean=0.08, mat='velvet', coll=c)
        G.round_table(f'cab_table{i}', (cx, cy - 0.2), r=0.5, coll=c)
        G.pendant_dome(f'cab_pendant{i}', (cx, cy - 0.2, 1.75), r=0.26, z_ceiling=GF, coll=c, power=120)
        G.candle(f'cab_candle{i}', (cx + 0.12, cy - 0.25, 0.75), coll=c)
        G.wine_glass(f'cab_glass{i}a', (cx - 0.15, cy - 0.05, 0.75), fill=0.03, coll=c)
        G.plate(f'cab_plate{i}', (cx - 0.05, cy - 0.45, 0.75), coll=c)
        # warm cove inside the top of the shell
        G.area_light(f'cab_cove{i}', (cx, cy + 0.2, 2.3), (1.6, 1.6), 80, color=(1.0, 0.68, 0.4),
                     rot=(math.pi, 0, 0), coll=c, shape='DISK')
    # glass-block screen beside the first cabin
    G.glass_block_panel('gb_screen', (6.9, 1.4, 0.0), 11, 12, axis='y', coll=c)
    G.box('gb_screen_cap', (0.12, 2.24, 0.06), (6.9, 1.4 + 1.12, 2.46), 'brass', coll=c)
    # warm wash behind the screen, onto cabin 0 and the floor (seen refracted through the blocks)
    G.area_light('gb_screen_glow', (6.35, 2.5, 1.2), (2.0, 2.2), 120, color=(1.0, 0.74, 0.50),
                 rot=(0, math.radians(90), 0), coll=c)


def dining():
    c = coll('dining')
    tables = [(4.6, -1.6), (1.6, -0.6), (-1.6, -1.8), (-4.6, -0.4), (2.8, -4.6), (-0.8, -4.9), (6.0, -5.2),
              (3.4, 1.4), (-0.6, 1.6), (-3.8, 2.0), (-7.0, -1.4), (-6.2, -4.6)]
    rng = np.random.default_rng(12)
    for i, (x, y) in enumerate(tables):
        G.round_table(f'table{i}', (x, y), r=0.42, coll=c)
        for k in range(3):
            a = rng.uniform(0, 2 * math.pi) if k == 0 else a + 2 * math.pi / 3 + rng.uniform(-0.3, 0.3)
            G.tub_chair(f'chair{i}_{k}', (x + 0.72 * math.cos(a), y + 0.72 * math.sin(a)), rot=a + math.pi, coll=c,
                        mat='velvet_olive' if (i + k) % 3 == 0 else 'velvet')
        G.candle(f'tcandle{i}', (x, y, 0.75), coll=c)
        G.wine_glass(f'tglass{i}', (x + 0.15, y + 0.1, 0.75), fill=0.025, coll=c)
        G.plate(f'tplate{i}', (x - 0.12, y - 0.12, 0.75), coll=c)


def foreground_v1():
    """View 1: our table at the edge of the void: marble top, mushroom lamp, wine, bread; curved
    rust velvet banquette behind it."""
    c = coll('fg1')
    tx, ty = 9.15, -2.45
    G.round_table('fg_table', (tx, ty), r=0.55, coll=c, top='marble_white')
    G.mushroom_lamp('fg_lamp', (tx - 0.22, ty + 0.18, 0.75), coll=c)
    G.wine_glass('fg_glass_a', (tx + 0.05, ty - 0.18, 0.75), fill=0.035, coll=c)
    G.wine_glass('fg_glass_b', (tx + 0.25, ty + 0.12, 0.75), fill=0.02, coll=c)
    G.plate('fg_plate_a', (tx - 0.12, ty - 0.28, 0.75), coll=c)
    G.plate('fg_plate_b', (tx + 0.22, ty - 0.08, 0.75), r=0.11, coll=c)
    G.candle('fg_candle', (tx + 0.1, ty + 0.3, 0.75), coll=c)
    # taste: torn bread on plate a, a small dish of olive oil on plate b
    import bmesh
    from mathutils import Vector, Euler
    rng = np.random.default_rng(31)
    for k, (dx, dy) in enumerate(((-0.04, 0.01), (0.04, -0.02), (0.0, 0.05))):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=0.042)
        for v in bm.verts:
            v.co *= 1.0 + 0.10 * rng.standard_normal()
        bmesh.ops.scale(bm, vec=Vector((1.6, 1.0, 0.6)), verts=bm.verts)
        ob = G.bm_obj(f'bread{k}', bm, 'bread', coll=c, loc=(tx - 0.12 + dx, ty - 0.28 + dy, 0.778))
        ob.rotation_euler = Euler((0.1 * rng.standard_normal(), 0.1 * rng.standard_normal(), rng.uniform(0, 3.1)))
    G.plate('fg_oil_dish', (tx + 0.22, ty - 0.08, 0.769), r=0.06, coll=c)
    G.cyl('fg_oil', 0.04, 0.004, (tx + 0.22, ty - 0.08, 0.7795), 'olive_oil', seg=48, coll=c)
    # banquette arc on the far side of the table (east), facing the camera
    G.seat_ring('fg_banq_seat', (tx, ty), 0.85, 1.45, math.radians(-75), math.radians(75), 0.0, 0.46, coll=c)
    G.channel_back('fg_banq_back', (tx, ty), 1.32, math.radians(-73), math.radians(73), 0.42, 0.42, lean=0.1, coll=c)
    G.tub_chair('fg_chair', (tx - 0.75, ty - 0.35), rot=math.radians(25), coll=c)     # faces the table


def foreground_v2():
    c = coll('fg2')
    tx, ty = 9.0, -1.25
    G.round_table('fg2_table', (tx, ty), r=0.5, coll=c, top='marble_white')
    G.wine_glass('fg2_glass_a', (tx - 0.12, ty + 0.1, 0.75), fill=0.03, coll=c)
    G.wine_glass('fg2_glass_b', (tx + 0.18, ty - 0.12, 0.75), fill=0.0, coll=c)
    G.plate('fg2_plate', (tx + 0.02, ty - 0.18, 0.75), coll=c)
    G.candle('fg2_candle', (tx - 0.2, ty - 0.15, 0.75), coll=c)
    G.tub_chair('fg2_chair', (tx + 0.55, ty + 0.55), rot=math.radians(225), coll=c, mat='leather')


def lights(view):
    c = coll('lights')
    sc = bpy.context.scene
    # sun: low golden sun from the east (behind the facade)
    sd = bpy.data.lights.new('sun', 'SUN')
    sd.energy = 2.5
    sd.angle = math.radians(0.8)
    sd.color = (1.0, 0.66, 0.38)
    so = bpy.data.objects.new('sun', sd)
    az, el = math.radians(SUN_AZ), math.radians(SUN_EL)          # azimuth from north, clockwise
    to_sun = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    so.rotation_euler = (-to_sun).to_track_quat('-Z', 'Y').to_euler()
    G.link(so, c)
    # world: physical sky, warm low sun
    w = bpy.data.worlds.new('sky')
    sc.world = w
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    sky = nt.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_elevation = math.radians(SUN_EL)
    sky.sun_rotation = math.radians(SUN_AZ)
    sky.sun_disc = False
    sky.altitude = 50.0
    sky.air_density = 1.4
    sky.aerosol_density = 2.5
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = 0.22
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(sky.outputs[0], bg.inputs[0])
    nt.links.new(bg.outputs[0], out.inputs[0])
    # drape uplights: long soft warm sources above the swags (light glows through linen)
    for i, xb in enumerate((13.2, 14.1, 15.0)):
        G.area_light(f'drapeE{i}', (xb, 0, GF - 0.08), (0.25, 15.0), 260, rot=(math.pi, 0, 0), coll=c)
    yb = Y0 + 0.8
    i = 0
    while yb < Y1 - 1.2:
        G.area_light(f'drapeW{i}', ((X0 + VOID_C[0] - VOID_R) / 2, yb, GF - 0.08), (VOID_C[0] - VOID_R - X0 - 1.0, 0.25),
                     220, rot=(math.pi, 0, 0), coll=c)
        yb += 2.0
        i += 1
    # void: rooflight glow + ring uplights
    G.area_light('rooflight', (VOID_C[0], VOID_C[1], FF + 0.2), (4.6, 4.6), 2200, color=(1.0, 0.86, 0.68),
                 rot=(math.pi, 0, 0), coll=c, shape='DISK')
    # a shaft of late sun through the rooflight and the olive canopy: dappled 'filtered light'
    sp = bpy.data.lights.new('dapple', 'SPOT')
    sp.energy = 16000
    sp.spot_size = math.radians(32)
    sp.spot_blend = 0.35
    sp.shadow_soft_size = 0.05
    sp.color = (1.0, 0.70, 0.42)
    spo = bpy.data.objects.new('dapple', sp)
    spo.location = (VOID_C[0] - 3.5, VOID_C[1] + 1.0, 14.5)
    G.link(spo, c)
    G.look_at(spo, (9.0, -1.6, 0.0))
    # uplight in the planter through the olive canopy: leaf shadows on the ceiling of the void
    # (reference 10)
    tu = bpy.data.lights.new('tree_up', 'SPOT')
    tu.energy = 4000
    tu.spot_size = math.radians(80)
    tu.spot_blend = 0.5
    tu.shadow_soft_size = 0.03
    tu.color = (1.0, 0.80, 0.58)
    tuo = bpy.data.objects.new('tree_up', tu)
    tuo.location = (TREE[0], TREE[1], 0.6)
    G.link(tuo, c)
    G.look_at(tuo, (12.5, 0.0, 9.0))
    # facade-side pendants (dining by the glazing) and a wall sconce on the pier
    for i, y in enumerate((-5.4, -1.2, 5.4)):
        G.pendant_dome(f'fac_pendant{i}', (14.6, y, 2.6), r=0.22, z_ceiling=GF, coll=c, power=45)
    # bar-side wash on the white brick wall (north)
    for i, x in enumerate((-8, -4, 0, 4, 7.5)):
        G.area_light(f'brickwash{i}', (x, Y1 - 0.6, GF - 0.3), (2.5, 0.3), 35, rot=(math.radians(150), 0, 0), coll=c)


def setup_render(res=(2700, 3600), samples=256, exposure=0.0):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    cy.device = 'CPU'
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.012
    cy.use_denoising = True
    cy.denoiser = 'OPENIMAGEDENOISE'
    cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    cy.use_light_tree = True
    cy.max_bounces = 10
    cy.diffuse_bounces = 4
    cy.glossy_bounces = 8
    cy.transmission_bounces = 10
    cy.transparent_max_bounces = 16
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.sample_clamp_indirect = 8.0
    cy.blur_glossy = 0.5
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    sc.view_settings.exposure = exposure
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_depth = '16'
    sc.render.threads_mode = 'AUTO'


def camera(view):
    cd = bpy.data.cameras.new(f'cam{view}')
    cd.sensor_fit = 'VERTICAL'
    cd.sensor_height = 36.0
    cd.sensor_width = 27.0
    co = bpy.data.objects.new(f'cam{view}', cd)
    G.link(co)
    if view == 1:
        co.location = (7.55, -2.75, 1.38)
        target = (16.0, -0.4, 1.38)
        cd.lens = 19.0
        cd.shift_y = 0.17
    else:
        co.location = (10.9, -2.3, 1.5)
        target = (0.6, 5.2, 1.45)
        cd.lens = 27.0
        cd.shift_y = 0.11
    G.look_at(co, target)
    bpy.context.scene.camera = co
    return co


def build(view, res=(2700, 3600), samples=256, exposure=0.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import nodes
    nodes.reset_cache()
    setup_render(res, samples, exposure)
    shell()
    facade()
    street()
    void_and_tree()
    drapes()
    cabins()
    dining()
    if view == 1:
        foreground_v1()
    else:
        foreground_v2()
    lights(view)
    cam = camera(view)
    _ = material
    return cam
