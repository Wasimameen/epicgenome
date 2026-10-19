"""render — build the scene for a view and render it with Cycles.

    python3 render.py --view 1 --res 675 900 --samples 32 --out ../../../build/v2/test/v1.png
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import scene  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--view', type=int, required=True)
    ap.add_argument('--res', type=int, nargs=2, default=(2700, 3600))
    ap.add_argument('--samples', type=int, default=256)
    ap.add_argument('--exposure', type=float, default=0.0)
    ap.add_argument('--out', required=True)
    ap.add_argument('--blend', default=None)
    ap.add_argument('--border', type=float, nargs=4, default=None, help='xmin xmax ymin ymax (0..1)')
    a = ap.parse_args()
    t0 = time.time()
    scene.build(a.view, tuple(a.res), a.samples, a.exposure)
    print(f'built in {time.time() - t0:.1f}s', flush=True)
    sc = bpy.context.scene
    if a.border:
        sc.render.use_border = True
        sc.render.use_crop_to_border = True
        sc.render.border_min_x, sc.render.border_max_x, sc.render.border_min_y, sc.render.border_max_y = a.border
    if a.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.blend))
    sc.render.filepath = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(sc.render.filepath), exist_ok=True)
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f'rendered in {time.time() - t1:.1f}s -> {sc.render.filepath}', flush=True)


if __name__ == '__main__':
    main()
