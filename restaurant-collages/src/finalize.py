"""finalize — render a psdkit Document and ship it: layered PSD + flattened JPEG/PNG + checks.

    from finalize import finalize
    report = finalize(doc, 'collage-01-from-the-void', verify=True)

Outputs (output/):
  <slug>.psd          layered, editable (groups, masks, clipping, fill layers, blend modes)
  <slug>.jpg          flattened, quality 95, 4:4:4, sRGB ICC, 300 ppi
  <slug>_preview.jpg  2000 px web preview
  <slug>_layers.txt   human-readable layer tree
Verification re-opens the PSD with psd-tools (an independent PSD reader + compositor) and
re-composites it from the layers, comparing against our render.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import psdkit  # noqa: E402

ICC = os.path.join(HERE, 'sRGB.icc')


def _tree_lines(nodes, depth=0):
    out = []
    for n in reversed(nodes):  # top of the Layers panel first, like Photoshop
        flags = []
        if n.blend not in ('normal', 'pass through'):
            flags.append(n.blend)
        if n.opacity < 1:
            flags.append(f'{round(n.opacity * 100)}%')
        if n.clip:
            flags.append('clipped')
        if getattr(n, 'mask', None) is not None:
            flags.append('mask')
        if n.hidden:
            flags.append('hidden')
        kind = {'group': '▾', 'fill': '■', 'pixel': '·'}[n.kind]
        out.append('  ' * depth + f'{kind} {n.name}' + (f'   [{", ".join(flags)}]' if flags else ''))
        if isinstance(n, psdkit.Group):
            out += _tree_lines(n.children, depth + 1)
    return out


def check_names(doc):
    bad = []
    seen = {}
    for n in doc.root.iter_layers():
        nm = n.name.strip()
        if not nm or nm.lower().startswith(('layer ', 'group ', 'untitled')):
            bad.append(nm or '<empty>')
        seen[nm] = seen.get(nm, 0) + 1
    dups = sorted(k for k, v in seen.items() if v > 1)
    return bad, dups


def finalize(doc, slug, verify=True, zip_psd=False):
    t0 = time.time()
    out_dir = os.path.join(ROOT, 'output')
    build_dir = os.path.join(ROOT, 'build', slug)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(build_dir, exist_ok=True)

    comp = doc.render()
    doc.export(build_dir, composite=comp)
    comp8 = np.asarray(Image.open(os.path.join(build_dir, 'composite.png')).convert('RGB'))

    psd_path = os.path.join(out_dir, f'{slug}.psd')
    cmd = ['node', os.path.join(HERE, 'write_psd.js'), build_dir, psd_path, '--icc', ICC]
    if zip_psd:
        cmd.append('--zip')
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError('write_psd failed:\n' + res.stdout + res.stderr)
    writer = json.loads(res.stdout.strip().splitlines()[-1])

    icc = open(ICC, 'rb').read()
    im = Image.fromarray(comp8)
    jpg_path = os.path.join(out_dir, f'{slug}.jpg')
    im.save(jpg_path, quality=95, subsampling=0, dpi=(doc.dpi, doc.dpi), icc_profile=icc, optimize=True)
    prev = im.copy()
    prev.thumbnail((2000, 2000), Image.LANCZOS)
    prev.save(os.path.join(out_dir, f'{slug}_preview.jpg'), quality=90, icc_profile=icc)

    tree = _tree_lines(doc.root.children)
    with open(os.path.join(out_dir, f'{slug}_layers.txt'), 'w') as f:
        f.write(f'{doc.title}\n{doc.width} x {doc.height} px @ {doc.dpi} ppi (A3), sRGB, 8-bit RGB\n')
        f.write(f'{doc.layer_count()} layers/groups — top of the Layers panel first\n\n')
        f.write('\n'.join(tree) + '\n')

    bad, dups = check_names(doc)
    report = {
        'slug': slug, 'psd': psd_path, 'jpg': jpg_path,
        'psd_mb': writer['mb'], 'jpg_mb': round(os.path.getsize(jpg_path) / 1048576, 1),
        'layers_total': doc.layer_count(), 'writer': writer,
        'bad_names': bad, 'duplicate_names': dups,
    }

    if verify:
        from psd_tools import PSDImage
        psd = PSDImage.open(psd_path)
        report['psd_size'] = list(psd.size)
        report['psd_layers_read'] = sum(1 for _ in psd.descendants())
        embedded = np.asarray(psd.composite().convert('RGB'), np.int16)
        report['embedded_composite_maxdiff'] = int(np.abs(embedded - comp8).max())
        rerender = np.asarray(psd.composite(force=True).convert('RGB'), np.int16)
        d = np.abs(rerender - comp8.astype(np.int16))
        report['rerender_mean_diff'] = round(float(d.mean()), 3)
        report['rerender_p99_diff'] = float(np.percentile(d, 99))
        report['rerender_max_diff'] = int(d.max())
        heat = np.clip(d.max(axis=2) * 8, 0, 255).astype(np.uint8)
        hm = Image.fromarray(heat)
        hm.thumbnail((1600, 1600))
        hm.save(os.path.join(build_dir, 'verify_diff_x8.png'))
    report['seconds'] = round(time.time() - t0, 1)
    with open(os.path.join(build_dir, 'report.json'), 'w') as f:
        json.dump(report, f, indent=1)
    return report
