import cv2, numpy as np, subprocess, re, sys, os

SRC, OUT = sys.argv[1], sys.argv[2]
S = 6  # upscale factor before tracing
im = cv2.imread(SRC, cv2.IMREAD_UNCHANGED)
h, w = im.shape[:2]
big = cv2.resize(im, (w * S, h * S), interpolation=cv2.INTER_CUBIC)
big = cv2.bilateralFilter(big[..., :3], 9, 40, 9).astype(np.float32), big[..., 3]
rgb, alpha = big

# Brand palette (BGR order for distance), bottom -> top stacking
PAL = [
    ("shadow-gray",  "#5A585D"),
    ("white",        "#F1F2F6"),
    ("light-gray",   "#C9C9D1"),
    ("pink-dark",    "#8E1450"),
    ("pink",         "#FC1560"),
    ("black",        "#121111"),
]
def bgr(hx): return np.array([int(hx[5:7],16), int(hx[3:5],16), int(hx[1:3],16)], np.float32)
cols = np.stack([bgr(c) for _, c in PAL])
d = ((rgb[:, :, None, :] - cols[None, None]) ** 2).sum(-1)
lab = d.argmin(-1)
opaque = cv2.GaussianBlur(alpha, (0, 0), S * 0.5) > 120

# Glints: small white/light-gray specks sitting on the lettering (y > 270 in source px).
# Relabel them to the surrounding letter colour and redraw them as clean vector sparkles.
glints = []
wl = (((lab == 1) | (lab == 2)) & opaque).astype(np.uint8)
n, cc, stats, cent = cv2.connectedComponentsWithStats(wl)
for k in range(1, n):
    x, y, bw, bh, area = stats[k]
    gx, gy = cent[k] / S
    if area < 300 * S * S and gy > 285 and 115 < gx < 580 and not (gx < 160 and gy < 310):
        comp = cc == k
        ring = cv2.dilate(comp.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & ~comp
        votes = np.bincount(lab[ring & opaque], minlength=len(PAL))
        votes[[0, 1, 2]] = 0
        lab[comp] = votes.argmax()
        glints.append((cent[k][0] / S, cent[k][1] / S, max(bw, bh) / S))
print("glints", len(glints))

def trace(mask, name):
    mask = cv2.morphologyEx(mask.astype(np.uint8) * 255, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.GaussianBlur(mask, (0, 0), S * 0.6)
    mask = np.where(mask > 127, 255, 0).astype(np.uint8)
    pbm = f"/tmp/claude-0/-home-user-epicgenome/4a772880-79ba-51a7-92da-be3abe72c141/scratchpad/{name}.pbm"
    cv2.imwrite(pbm.replace(".pbm", ".png"), mask)
    with open(pbm, "wb") as f:
        f.write(f"P4\n{mask.shape[1]} {mask.shape[0]}\n".encode())
        f.write(np.packbits(mask > 127, axis=1).tobytes())
    svg = subprocess.run(["potrace", pbm, "-s", "-o", "-", "-t", "40", "-a", "1.0", "-O", "0.4",
                          "-u", "10", "-W", f"{w}pt", "-H", f"{h}pt"], capture_output=True, text=True).stdout
    g = re.search(r"(<g transform=.*?</g>)", svg, re.S).group(1)
    return g

layers = []
# Base silhouette: everything opaque, slightly grown, in shadow gray -> no hairline gaps between layers
for i, (name, hx) in enumerate(PAL):
    if i == 0:
        m = opaque
    else:
        m = opaque & (lab == i)
        m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    g = trace(m, name)
    g = g.replace('fill="#000000"', f'fill="{hx}"', 1)
    g = g.replace("<g ", f'<g id="{name}" ', 1)
    layers.append(g)

def star(cx, cy, r):
    r = max(r * 0.9, 5.0); t = r * 0.13
    return (f'    <path d="M{cx:.1f} {cy-r:.1f} Q{cx+t:.1f} {cy-t:.1f} {cx+r:.1f} {cy:.1f} '
            f'Q{cx+t:.1f} {cy+t:.1f} {cx:.1f} {cy+r:.1f} Q{cx-t:.1f} {cy+t:.1f} {cx-r:.1f} {cy:.1f} '
            f'Q{cx-t:.1f} {cy-t:.1f} {cx:.1f} {cy-r:.1f}Z"/>')
glint_svg = "\n".join(star(*g) for g in glints)
css = "\n".join(f"      .{n} {{ fill: {c}; }}" for n, c in PAL)
doc = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w*4}" height="{h*4}">
  <title>Simply Done - No Mess. No Stress.</title>
  {chr(10).join("  " + l for l in layers)}
  <g id="glints" fill="#FFFFFF">
{glint_svg}
  </g>
</svg>
'''
open(OUT, "w").write(doc)
print("ok", len(doc))
