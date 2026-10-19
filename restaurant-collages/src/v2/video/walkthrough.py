"""walkthrough — camera walk through the restaurant model: from the street, through the glazed
entrance, past the olive tree in the void, across the dining room to the private cabins.

    python3 walkthrough.py [--test FRAME ...]   -> build/v2/video/frames/####.png (resumable)
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scene'))

import bpy  # noqa: E402

import geo as G  # noqa: E402
import nodes  # noqa: E402
import scene as S  # noqa: E402

FPS = 12                       # rendered rate; interpolated to 24 fps afterwards
RES = (1920, 1080)
SAMPLES = 12
OUT = os.path.join(nodes.ROOT, 'build', 'v2', 'video', 'frames')

# (seconds, camera position, look-at target)
KEYS = [
    (0.0,  (23.0, -0.9, 1.65), (10.0, -0.6, 2.2)),
    (5.0,  (17.0, -1.1, 1.62), (9.0, 0.2, 2.6)),
    (9.5,  (12.2, -1.5, 1.60), (9.4, 1.4, 3.6)),     # under the olive tree, looking up
    (13.5, (9.6, -2.6, 1.55),  (3.0, 4.0, 1.8)),     # turn towards the dining room
    (20.0, (5.2, 0.3, 1.50),   (1.6, 5.6, 1.25)),    # arrive in front of the cabins
]


def setup():
    S.build(2, res=RES, samples=SAMPLES)
    sc = bpy.context.scene
    # open the entrance bay: hide its glass so the camera can walk in
    for ob in sc.objects:
        if ob.name in ('bay1_glass', 'lamppost', 'lamphead'):
            ob.hide_render = True
    cy = sc.cycles
    cy.adaptive_threshold = 0.05
    cy.max_bounces = 6
    cy.transmission_bounces = 6
    cy.use_denoising = True
    sc.render.use_persistent_data = True
    sc.render.fps = FPS
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_depth = '8'
    sc.render.use_overwrite = False
    sc.render.use_placeholder = True
    sc.render.filepath = os.path.join(OUT, '')
    cd = bpy.data.cameras.new('walk')
    cd.lens = 22
    cd.sensor_width = 36
    cam = bpy.data.objects.new('walk', cd)
    G.link(cam)
    tgt = bpy.data.objects.new('walk_target', None)
    G.link(tgt)
    c = cam.constraints.new('TRACK_TO')
    c.target = tgt
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    for t, p, q in KEYS:
        f = int(round(t * FPS)) + 1
        cam.location = p
        cam.keyframe_insert('location', frame=f)
        tgt.location = q
        tgt.keyframe_insert('location', frame=f)
    for ob in (cam, tgt):
        for fc in ob.animation_data.action.fcurves if hasattr(ob.animation_data.action, 'fcurves') else []:
            for k in fc.keyframe_points:
                k.interpolation = 'BEZIER'
                k.easing = 'AUTO'
    sc.camera = cam
    sc.frame_start = 1
    sc.frame_end = int(round(KEYS[-1][0] * FPS)) + 1
    return sc


if __name__ == '__main__':
    sc = setup()
    os.makedirs(OUT, exist_ok=True)
    if '--test' in sys.argv:
        import time
        for f in [int(a) for a in sys.argv[sys.argv.index('--test') + 1:]]:
            sc.frame_set(f)
            sc.render.filepath = os.path.join(nodes.ROOT, 'build', 'v2', 'video', f'test_{f:04d}.png')
            t = time.time()
            bpy.ops.render.render(write_still=True)
            print(f'frame {f}: {time.time() - t:.1f}s', flush=True)
    else:
        bpy.ops.render.render(animation=True)
        print('walkthrough frames done', flush=True)
