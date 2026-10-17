"""process — a clay axonometric of the 3D model (roof and first floor lifted off), showing that the
views are renders of the client's own design, modelled from her plans and sections.

    python3 process.py [--test]   -> build/v2/render/process_axo.png
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import geo as G  # noqa: E402
import nodes  # noqa: E402
import scene as S  # noqa: E402

HIDE = ('roof', 'rooflight', 'slab1', 'void_edge', 'wall_N_ff', 'rail', 'post', 'void_ring', 'ff', 'street',
        'pavement', 'kerb', 'road', 'bldg', 'win', 'surr', 'sill', 'band', 'shop', 'fascia', 'awning', 'cornice',
        'lamp', 'treepit', 'wall_S', 'wall_W', 'swag', 'festoon_void', 'party_curtain')


def main(test=False):
    S.build(1, res=(800, 600) if test else (2400, 1800), samples=16 if test else 48)
    sc = bpy.context.scene
    clay = bpy.data.materials.new('clay')
    nt = clay.node_tree
    p = nt.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (0.82, 0.79, 0.74, 1)
    p.inputs['Roughness'].default_value = 0.7
    keep = {'window_glass', 'glass_block', 'wine_glass', 'leaf', 'leaf_street', 'bark', 'linen', 'sheer', 'bulb'}
    for ob in list(sc.objects):
        if any(ob.name.startswith(h) for h in HIDE) or ob.name.startswith('streettree'):
            ob.hide_render = True
            continue
        if ob.type in ('MESH', 'CURVE'):
            mats = [m.name for m in ob.data.materials if m]
            if not any(m in keep for m in mats):
                ob.data.materials.clear()
                ob.data.materials.append(clay)
    # soft studio light, no sun
    for ob in sc.objects:
        if ob.type == 'LIGHT' and ob.data.type == 'SUN':
            ob.data.energy = 2.0
    w = sc.world
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6 if 'Background' in w.node_tree.nodes else 0
    cd = bpy.data.cameras.new('axo')
    cd.type = 'ORTHO'
    cd.ortho_scale = 30.0
    co = bpy.data.objects.new('axo', cd)
    G.link(co)
    az, el = math.radians(215), math.radians(38)
    tgt = (3.5, 0.5, 1.2)
    d = 60
    co.location = (tgt[0] + d * math.sin(az) * math.cos(el), tgt[1] + d * math.cos(az) * math.cos(el), tgt[2] + d * math.sin(el))
    G.look_at(co, tgt)
    sc.camera = co
    sc.render.resolution_x, sc.render.resolution_y = (800, 600) if test else (2400, 1800)
    sc.view_settings.exposure = -0.9
    sc.render.film_transparent = True
    out = os.path.join(nodes.ROOT, 'build', 'v2', 'test' if test else 'render', 'process_axo.png')
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print('process ->', out, flush=True)


if __name__ == '__main__':
    main('--test' in sys.argv)
