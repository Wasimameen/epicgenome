"""swatches — close-up 'material photographs' of the scene's own materials, for the torn fragments.

Each swatch is a small Cycles scene: the material on real geometry (displacement, flutes,
folds, blocks), a raking warm light, a camera filling the frame. 1600 x 2000 px (4:5).

    python3 swatches.py [name ...]      -> build/v2/swatch/<name>.png
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import geo as G  # noqa: E402
import nodes  # noqa: E402
import scene as S  # noqa: E402

OUT = os.path.join(nodes.ROOT, 'build', 'v2', 'swatch')
RES = (1600, 2000)


def base(samples=64, world=(0.55, 0.5, 0.45), strength=0.35):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    nodes.reset_cache()
    S.setup_render(RES, samples)
    sc = bpy.context.scene
    sc.cycles.adaptive_threshold = 0.01
    w = bpy.data.worlds.new('w')
    sc.world = w
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*world, 1)
    bg.inputs[1].default_value = strength
    return sc


def ortho_cam(width, loc=(0, -3, 0), target=(0, 0, 0)):
    cd = bpy.data.cameras.new('c')
    cd.type = 'ORTHO'
    cd.sensor_fit = 'HORIZONTAL'
    cd.ortho_scale = width
    co = bpy.data.objects.new('c', cd)
    G.link(co)
    co.location = loc
    G.look_at(co, target)
    bpy.context.scene.camera = co
    return co


def persp_cam(lens, loc, target):
    cd = bpy.data.cameras.new('c')
    cd.lens = lens
    cd.sensor_fit = 'HORIZONTAL'
    co = bpy.data.objects.new('c', cd)
    G.link(co)
    co.location = loc
    G.look_at(co, target)
    bpy.context.scene.camera = co
    return co


def sun(az_deg, el_deg, energy=4.0, color=(1.0, 0.78, 0.55), angle=2.0):
    """Sun shining from direction (azimuth from +x towards +z in the wall plane..., elevation)."""
    from mathutils import Vector
    ld = bpy.data.lights.new('sun', 'SUN')
    ld.energy = energy
    ld.color = color
    ld.angle = math.radians(angle)
    o = bpy.data.objects.new('sun', ld)
    az, el = math.radians(az_deg), math.radians(el_deg)
    to_light = Vector((math.cos(az) * math.cos(el), -math.sin(el), math.sin(az) * math.cos(el)))
    o.rotation_euler = (-to_light).to_track_quat('-Z', 'Y').to_euler()
    G.link(o)
    return o


def wall(mat, w=3.0, h=3.0, uv=False):
    """Vertical plane in x-z facing -y."""
    if uv:
        ob = G.box_uv('wall', (w, 0.02, h), (0, 0.01, 0), mat)
    else:
        ob = G.box('wall', (w, 0.02, h), (0, 0.01, 0), mat)
    return ob


# ----------------------------------------------------------------------------------------------
def split_face_stone():
    base(world=(0.6, 0.55, 0.5), strength=0.25)
    ob = wall('split_face', 2.0, 2.4, uv=True)
    G.adaptive(ob, 1.0)
    sun(170, 18, 5.0)                      # raking from the right, low: texture + shadow
    ortho_cam(0.9)


def travertine():
    base(samples=128)
    ob = wall('travertine', 3, 3)
    ob.location = (0.35, 0.01, 0.2)
    sun(120, 12, 3.0)                      # raking: pits and bands read
    ortho_cam(0.45)


def concrete():
    base(samples=128)
    wall('concrete', 3, 3)
    sun(160, 10, 4.0)
    ortho_cam(0.8)


def dark_timber():
    base()
    wall('walnut', 3, 3)
    sun(100, 40, 3.5)
    ortho_cam(0.45)


def white_brick():
    base()
    wall('white_brick', 3, 3)
    sun(165, 20, 4.0)
    ortho_cam(1.1)


def breccia_marble():
    base(strength=0.6)
    wall('breccia', 3, 3)
    sun(110, 50, 2.5)
    ortho_cam(0.55)


def glass_block():
    base(world=(0.2, 0.18, 0.15), strength=0.2)
    G.glass_block_panel('gb', (-0.65, 0.0, -0.8), 6, 8, axis='x')
    # warm glowing room beyond, with soft blurred shapes
    em = G.box('beyond', (4, 0.02, 4), (0, 1.2, 0), nodes.material('lampshade'))
    G.area_light('back', (0, 0.9, 0.2), (2.0, 2.0), 120, color=(1.0, 0.8, 0.55), rot=(math.radians(-90), 0, 0))
    G.box('shape1', (0.25, 0.25, 1.6), (-0.3, 0.3, -0.2), 'walnut')
    G.cyl('shape2', 0.18, 0.02, (0.35, 0.3, 0.3), 'bulb', seg=24).rotation_euler = (math.pi / 2, 0, 0)
    sun(130, 30, 1.2)
    _ = em
    persp_cam(120, (-0.03, -3.4, 0.02), (-0.03, 0, 0.02))


def sheer_fabric():
    base(world=(1.0, 0.92, 0.8), strength=0.15)
    G.curtain('sheer', -1.0, 1.0, 0.0, -1.4, 1.4, axis='x', gather=0.09, amp=0.06, seed=4, mat='sheer')
    G.box('window', (4, 0.02, 4), (0, 1.5, 0), nodes.material('lampshade'))
    G.area_light('day', (0, 1.2, 0.5), (3.0, 3.0), 160, color=(1.0, 0.84, 0.64), rot=(math.radians(-90), 0, 0))
    sun(150, 25, 1.6)
    ortho_cam(1.0)


def linen_drape():
    """Stacked festoon swags (her draped ceiling, reference 1): every row overlaps the next, so
    the whole frame is soft linen."""
    base(world=(0.5, 0.42, 0.35), strength=0.25)
    for k, (z, y) in enumerate(((1.15, 0.0), (0.62, 0.22), (0.09, 0.44), (-0.44, 0.66), (-0.97, 0.88))):
        G.festoon(f'festoon{k}', -2.2, 2.2, y, z, drop=0.5, scallop=0.95, sag=0.3, seed=7 + k, facing=-1)
    G.box('wall', (6, 0.05, 6), (0, 1.6, 0), 'plaster')
    G.area_light('front', (0.6, -1.6, -0.6), (2.5, 1.0), 70, color=(1.0, 0.8, 0.58), rot=(math.radians(70), 0, math.radians(20)))
    G.area_light('top', (0, -0.5, 2.2), (3.0, 1.0), 60, color=(1.0, 0.75, 0.5), rot=(math.radians(20), 0, 0))
    sun(150, 30, 1.0)
    persp_cam(70, (0.1, -3.0, 0.05), (0.0, 0.3, 0.05))


def brass():
    base(world=(0.18, 0.14, 0.1), strength=0.08)
    # gently curved brushed sheet so the reflection grades across it
    P = np.zeros((80, 2, 3), np.float32)
    th = np.linspace(-0.5, 0.5, 80)
    P[:, :, 0] = np.sin(th)[:, None] * 1.0
    P[:, :, 1] = (1 - np.cos(th))[:, None] * 1.0
    P[:, 0, 2] = -1.0
    P[:, 1, 2] = 1.0
    ob = G.grid_obj('sheet', P, 'brass')
    _ = ob
    G.area_light('soft', (-0.9, -1.4, 0.4), (0.6, 2.5), 45, color=(1.0, 0.85, 0.65), rot=(math.radians(90), 0, math.radians(-30)))
    G.area_light('rim', (1.2, -0.8, 0.0), (0.3, 2.5), 18, color=(1.0, 0.7, 0.4), rot=(math.radians(90), 0, math.radians(40)))
    ortho_cam(0.8)


def velvet():
    base(world=(0.4, 0.3, 0.25), strength=0.3)
    # flattened channel-tufted panel
    nu, nv = 400, 120
    u = np.linspace(-1, 1, nu)
    v = np.linspace(-1.2, 1.2, nv)
    U, V = np.meshgrid(u, v, indexing='ij')
    ch = np.abs(np.sin(np.pi * U / 0.16)) ** 0.45 * 0.035
    P = np.stack([U, -ch, V], -1).astype(np.float32)
    ob = G.grid_obj('panel', P, 'velvet')
    G.subsurf(ob, 1)
    sun(165, 28, 4.0, (1.0, 0.75, 0.55))
    G.area_light('fill', (-1.2, -1.5, 0.5), (2.0, 2.0), 60, rot=(math.radians(90), 0, math.radians(-40)))
    ortho_cam(0.6)


def olive_leaves():
    base(world=(0.95, 0.88, 0.76), strength=1.1)
    G.olive_tree('olive', (0, 0, -3.2), height=4.0, spread=3.0, seed=5, leaf_density=1.8)
    sun(60, 50, 3.5, (1.0, 0.82, 0.6))
    persp_cam(40, (0.6, -3.5, -1.4), (0.0, 0.0, -0.5))


def fluted_oak():
    base()
    G.fluted_arc('flute', (0, 6.0), 6.0, math.radians(-100), math.radians(-80), 3.0, mat='oak', flute=0.05, depth=0.014)
    for o in bpy.data.objects:
        if o.name.startswith('flute'):
            o.location.z = -1.5
    sun(165, 25, 4.0)
    ortho_cam(0.7, loc=(0, -3, 0), target=(0, 0, 0))


SWATCHES = {
    'split_face_stone': split_face_stone, 'travertine': travertine, 'concrete': concrete,
    'dark_timber': dark_timber, 'white_brick': white_brick, 'breccia_marble': breccia_marble,
    'glass_block': glass_block, 'sheer_fabric': sheer_fabric, 'linen_drape': linen_drape,
    'brass': brass, 'velvet': velvet, 'olive_leaves': olive_leaves, 'fluted_oak': fluted_oak,
}


def main(names, res=None, samples=None):
    global RES
    if res:
        RES = res
    os.makedirs(OUT, exist_ok=True)
    for n in names:
        SWATCHES[n]()
        sc = bpy.context.scene
        if samples:
            sc.cycles.samples = samples
        sc.render.resolution_x, sc.render.resolution_y = RES
        sc.render.filepath = os.path.join(OUT, f'{n}.png')
        bpy.ops.render.render(write_still=True)
        print('swatch', n, flush=True)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    test = '--test' in sys.argv
    if test:
        OUT = os.path.join(nodes.ROOT, 'build', 'v2', 'test', 'swatch')
    main(args or list(SWATCHES), res=(320, 400) if test else None, samples=16 if test else None)
