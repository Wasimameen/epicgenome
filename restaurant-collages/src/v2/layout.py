"""layout — page layout data for the v2 atmosphere collages (read by src/v2/compose.py).

    !!  PROVISIONAL LAYOUT  !!  Drafted against placeholder images, before the real renders and
    swatches existed.  Every number below is meant to be retuned by eye once
    build/v2/render/view{1,2}.png and build/v2/swatch/*.png are in place.

Page: A3 portrait, 3508 x 4961 px at 300 ppi.  Coordinates are page pixels, x right, y down.
Angles: degrees, POSITIVE = COUNTER-CLOCKWISE on the page (same as the live type twins).
Z-order: within each list, later entries sit on top.

SHEET keys
  title     {'text', 'x', 'y' (cap top of the title), 'size', 'tracking' (1/1000 em)}
  subtitle  {'text', 'dx' ('auto' = under the first word after the number, or px), 'dy' (baseline
             below the title baseline), 'size', 'tracking'}
  view      the main perspective render, placed with a stepped outline:
              'outline'  list of rectangles (x0, y0, x1, y1, torn_sides) whose UNION is the visible
                         image; torn_sides is a string of the sides of THAT rectangle that are torn
                         ('T', 'R', 'B', 'L', any combination, '' = clean cut)
              'frame'    (x0, y0, x1, y1) the render is cover-fitted into (default: outline bbox)
              'focus'    (fx, fy) 0..1 which part of the render stays in frame when cover-fitting
              'zoom'     >= 1 zooms the render inside the frame
              'seed', 'rim' (paper core on the torn sides), 'shadow' (dx, dy, blur, opacity)
  fragments list of material fragments:
              (swatch, crop, target, rot, edge, z, seed[, opts])
                swatch  name of build/v2/swatch/<swatch>.png
                crop    (u0, v0, u1, v1) box in the swatch, 0..1 of its width / height.  It is
                        widened or heightened about its centre to match the target's aspect, so a
                        swatch is never stretched.  None = centred, about 1:1 pixel scale.
                target  (x, y, w, h) page rectangle (rotated by `rot` about its centre), or a
                        quad ((x, y) top-left, top-right, bottom-right, bottom-left) for perspective
                        (rot is then ignored)
                rot     degrees, counter-clockwise
                edge    'torn' (all four sides), 'cut' (clean straight cut), or a string of the
                        torn sides of the unrotated rectangle, e.g. 'LB' = left and bottom torn
                z       'behind' (under the main view) or 'front' (over it)
                seed    any int: changes the tear
                opts    optional dict: 'rim' False (no white paper core), 'tear' amplitude x
                        (default 1.0), 'shadow' (dx, dy, blur, opacity), 'name' (layer name),
                        'tone' {'color', 'blend', 'opacity'} a clipped colour fill to harmonise
  echoes    patches cut from the render itself and laid back over its edge:
              (src_box, scale, (dx, dy), rot, edge, seed[, opts])
                src_box (x0, y0, x1, y1) a PAGE rectangle of the placed view to copy
                scale   ~1.0 .. 1.15 about the patch centre; (dx, dy) offset; rot, edge, seed as above
  notes     handwritten notes: (text, (x, y), rot, target, bend[, opts])
                text    '\\n' breaks lines;  (x, y) = left end of the FIRST baseline
                target  (x, y) the arrow tip, or None for no arrow
                bend    curvature of the arrow, about -0.5 .. 0.5 (sign flips the side)
                opts    'from': where the arrow leaves the text - 'auto', 'below', 'above', 'left',
                        'right', 'below_left', 'below_right', 'above_left', 'above_right', 'end'
                        (after the last line) or an absolute (x, y);
                        'from_offset': (dx, dy) nudge of the arrow start;
                        'c1', 'c2': absolute Bezier control points (override `bend`);
                        'style': 'note' (default) or 'sense' (smaller, softer sensory note);
                        'size', 'color', 'align', 'head' (arrowhead length px), 'gap' (px)
  intensity {'overlap': {'color', 'blend', 'opacity', 'feather'},  front fragments x the view
             'glows': [((cx, cy), radius, color, blend, opacity), ...]}  radial 'chosen area'
  footer    [(text, (x, y) baseline, align), ...]   small italic key line
  sources   one line for the hidden READ ME group
"""

# --------------------------------------------------------------------------------------------- #
# SHEET 1 - LOOKING FROM WITHIN (chosen area -> outside views)            PROVISIONAL
# --------------------------------------------------------------------------------------------- #
DARK = {'color': '#4A3C32', 'blend': 'multiply', 'opacity': 0.55}      # walnut reads near-black
CALM = {'color': '#8C8C8C', 'blend': 'saturation', 'opacity': 0.32}    # tame CG saturation
VIEW_TONE = {'color': '#8C8C8C', 'blend': 'saturation', 'opacity': 0.35}
EDGE = {'rim': False, 'tear': 0.5, 'shadow': (5, 7, 14, 0.20)}
LIFT = {'rim': False, 'tear': 0.4, 'shadow': (4, 6, 10, 0.18)}

SHEET1 = {
    'title': {'text': '1.  LOOKING FROM WITHIN', 'x': 230, 'y': 200, 'size': 96, 'tracking': 140},
    'subtitle': {'text': 'chosen area to outside views', 'dx': 'auto', 'dy': 72, 'size': 40, 'tracking': 300},

    # render -> page (before the 0.95 inset): page_x ~ 344 + rx * 1.097, page_y ~ 520 + ry * 1.097
    # olive trunk px 344-540 / py 2500-2890; canopy + leaf-shadowed void ceiling py 520-1650;
    # festoon py 1650-2150; windows py 2350-3530 (glass-brick panel px 1180-1580, street tree px
    # 2710-3250); our table, bread, lamp py 3530-4470
    'view': {
        'outline': [
            (490, 640, 3160, 4300, ''),            # body
            (920, 520, 2500, 700, ''),             # raised step, top
            (360, 1250, 540, 3350, 'L'),           # left step, torn (keeps the olive trunk)
            (3100, 1150, 3290, 3900, 'R'),         # right step, torn
            (1040, 4240, 2660, 4470, 'B'),         # bottom step, torn
        ],
        'frame': (360, 520, 3290, 4470),
        'focus': (0.5, 0.5), 'zoom': 1.0, 'seed': 11, 'tone': VIEW_TONE, **EDGE,
    },

    'fragments': [
        # swatch             crop (u0, v0, u1, v1)       target (x, y, w, h)       rot   edge    z        seed
        # ---- behind the view
        ('dark_timber',      (0.10, 0.12, 0.80, 0.42),  (1180, 380, 760, 300),     -0.7, 'cut',  'behind', 101, {'tone': DARK}),
        ('sheer_fabric',     (0.15, 0.10, 0.85, 0.60),  (2560, 380, 720, 820),      1.1, 'LB',   'behind', 102),
        # ---- in front of the view
        ('olive_leaves',     (0.18, 0.24, 0.92, 0.60),  (60, 470, 470, 560),        1.5, 'torn', 'front',  201),
        ('concrete',         (0.20, 0.10, 0.60, 0.45),  (880, 420, 360, 300),      -1.2, 'torn', 'front',  202, {'tear': 1.0}),
        ('split_face_stone', (0.05, 0.05, 0.30, 0.40),  (40, 1300, 450, 820),       0.6, 'torn', 'front',  203),
        ('dark_timber',      (0.55, 0.30, 0.80, 0.70),  (60, 3000, 480, 1050),     -0.5, 'torn', 'front',  204, {'tone': DARK}),
        ('split_face_stone', (0.05, 0.55, 0.95, 0.95),  (60, 3990, 980, 600),      -0.8, 'torn', 'front',  205),
        ('glass_block',      (0.05, 0.15, 0.60, 0.75),  (980, 3900, 560, 700),      0.9, 'cut',  'front',  206),
        ('brass',            (0.20, 0.20, 0.60, 0.55),  (1480, 4200, 500, 420),    -0.5, 'cut',  'front',  207),
        ('velvet',           (0.20, 0.30, 0.60, 0.52),  (1940, 4320, 380, 300),    -1.6, 'cut',  'front',  104, {'tone': CALM}),
        ('linen_drape',      (0.10, 0.05, 0.60, 0.95),  (2980, 820, 470, 1080),    -0.7, 'TB',   'front',  208),
        ('glass_block',      (0.50, 0.10, 0.85, 0.80),  (3150, 2200, 330, 860),     0.4, 'cut',  'front',  209),
        ('travertine',       (0.55, 0.05, 0.85, 0.70),  (3130, 3260, 350, 880),    -1.3, 'torn', 'front',  210),
        ('concrete',         (0.20, 0.10, 0.55, 0.55),  (2250, 4080, 460, 560),     2.0, 'torn', 'front',  211, {'tear': 1.0}),
        ('dark_timber',      (0.55, 0.30, 0.80, 0.70),  (2620, 4000, 300, 620),     1.4, 'cut',  'front',  105, {'tone': DARK}),
    ],

    'echoes': [
        # src_box on the page          scale  (dx, dy)    rot   edge    seed
    ],

    'notes': [
        # text                    (x, y) baseline   rot    arrow tip       bend   opts
        ('olive\ntree',           (40, 1120),        2.0,  (640, 1250),   -0.25, {'from': 'right', 'size': 76}),
        ('texture\n+ shadow',     (30, 2230),        2.5,  (250, 2090),    0.35, {'from': 'above', 'size': 74}),
        ('filtered light,\nleaf shadows', (1990, 400), -1.5, (1800, 1000), 0.25, {'from': 'below', 'size': 70}),
        ('ceiling draping,\nsoft linen', (2880, 320),  2.0,  (3150, 860),    0.35, {'from': 'below', 'size': 72}),
        ('glass\nbrick',          (3215, 1990),     -3.0,  (3290, 2310),  -0.35, {'from': 'below', 'size': 76}),
        ('split face stone',      (330, 4720),       0.5,  (230, 4480),    0.40, {'from': 'left'}),
        ('warm + intimate',       (1330, 4790),     -1.0,  (1700, 4560),  -0.30, {'from': 'above_right'}),
        ('concrete',              (2830, 4820),      1.5,  (2620, 4560),   0.25, {'from': 'left'}),
        # the senses (softer, no arrow)
        ('sound:\nvoices\nrise up\nthe void', (40, 2460), 2.0, None,     0.0,  {'style': 'sense', 'size': 54}),
        ('colour:\nhoney,\nlinen,\nolive', (40, 2760), 1.5, None,          0.0,  {'style': 'sense', 'size': 54}),
        ('smell + taste: warm bread, olive oil', (1060, 4920), -1.0, None,  0.0,  {'style': 'sense'}),
        ('sound:\nstreet hum,\nmuffled', (3120, 4420), -2.0, None,       0.0,  {'style': 'sense', 'size': 56}),
    ],

    'intensity': {
        'overlap': {'color': '#B07A50', 'blend': 'soft light', 'opacity': 0.25, 'feather': 60},
        'glows': [
            ((1750, 3700), 750, '#A9502F', 'color', 0.40),          # our table in the void
            ((2300, 2900), 850, '#D98A3D', 'soft light', 0.30),     # where the void meets the street
        ],
    },

    'footer': [
        ('restaurant  —  atmosphere collage 1 of 2', (230, 4868), 'left'),
        ('sound · smell · taste · texture · colour', (3278, 4868), 'right'),
    ],
    'sources': 'Main view: build/v2/render/view1.png (Blender render of the client design). Material swatches: build/v2/swatch/*.png.',
}


SHEET2 = {
    'title': {'text': '2.  LOOKING TOWARDS', 'x': 230, 'y': 200, 'size': 96, 'tracking': 140},
    'subtitle': {'text': 'chosen area from a distance', 'dx': 'auto', 'dy': 72, 'size': 40, 'tracking': 300},

    # render -> page (before the inset): page_x ~ 344 + rx * 1.097, page_y ~ 520 + ry * 1.097
    # void rail py 520-1150; swag ceiling py 1110-2490; cabins px 1000-2190 / py 2560-3250;
    # glass-brick screen px 2150-2910 / py 2380-3730; olive trunk px 2880-3300; our table
    # px 720-2140 / py 3760-4470
    'view': {
        'outline': [
            (500, 660, 3140, 4300, ''),            # body
            (820, 520, 2420, 700, ''),             # raised step, top
            (360, 1300, 540, 3500, 'L'),           # left step, torn
            (3080, 1500, 3290, 3900, ''),          # right step
            (880, 4240, 2500, 4470, 'B'),          # bottom step, torn
        ],
        'frame': (360, 520, 3290, 4470),
        'focus': (0.5, 0.5), 'zoom': 1.0, 'seed': 12, 'tone': VIEW_TONE, **EDGE,
    },

    'fragments': [
        # ---- behind
        ('linen_drape',      (0.05, 0.30, 0.95, 0.55),  (980, 380, 1400, 380),     -0.6, 'B',    'behind', 401),
        ('dark_timber',      (0.20, 0.05, 0.60, 0.40),  (2380, 600, 300, 520),      0.8, 'cut',  'behind', 402, {'tone': DARK}),
        ('dark_timber',      (0.55, 0.10, 0.85, 0.95),  (70, 2150, 300, 700),       0.3, 'cut',  'behind', 403, {'tone': DARK}),
        # ---- in front
        ('linen_drape',      (0.45, 0.20, 0.95, 0.90),  (40, 640, 430, 760),       -0.8, 'torn', 'front',  501),
        ('concrete',         (0.05, 0.05, 0.75, 0.55),  (2780, 330, 600, 470),      1.3, 'torn', 'front',  502, {'tear': 1.0}),
        ('white_brick',      (0.30, 0.05, 0.75, 0.95),  (3000, 1140, 340, 1060),   -1.5, 'L',    'front',  503),
        ('travertine',       (0.15, 0.15, 0.55, 0.85),  (60, 2900, 430, 1100),     -1.0, 'torn', 'front',  504),
        ('fluted_oak',       (0.10, 0.05, 0.60, 0.95),  (2900, 3560, 560, 1080),   -1.1, 'torn', 'front',  505),
        ('split_face_stone', (0.05, 0.30, 0.80, 0.70),  (50, 3980, 700, 520),       0.7, 'torn', 'front',  506),
        ('velvet',           (0.10, 0.20, 0.55, 0.50),  (980, 4150, 540, 420),     -1.2, 'cut',  'front',  404, {'tone': CALM}),
        ('dark_timber',      (0.05, 0.05, 0.30, 0.90),  (1900, 4080, 300, 560),    -1.8, 'cut',  'front',  509, {'tone': DARK}),
        ('brass',            (0.10, 0.30, 0.55, 0.65),  (2150, 4320, 420, 320),     0.9, 'cut',  'front',  508),
    ],

    'echoes': [
        ((1000, 2560, 2150, 3250),     1.06,  (-25, -35), -0.8, 'cut',  601, LIFT),      # the cabins lift forward
    ],

    'notes': [
        ('layered ceiling: linen swags', (1120, 455), -1.0, (1500, 1550), 0.25, {'from': 'below'}),
        ('concrete',              (2420, 330),       1.5,  (2830, 470),   -0.30, {'from': 'right'}),
        ('private cabins',        (1640, 3460),     -1.0,  (1900, 3020),   0.20, {'from': 'above', 'size': 72}),
        ('white\nbrick\nwall',    (3290, 2300),     -2.5,  (3300, 2180),   0.35, {'from': 'above', 'gap': 14, 'size': 72}),
        ('glass\nbrick\nscreen',  (3300, 2860),     -2.0,  (2860, 3000),   0.30, {'from': 'left', 'size': 70}),
        ('a path from the\nvoid to the cabins', (200, 4690), 1.0, (1000, 3700), -0.30,
         {'from': 'above_right', 'c1': (820, 4450), 'c2': (900, 3950)}),
        ('tactile: velvet,\noak, brass', (1600, 4700), -0.8, (1450, 4480), -0.25, {'from': 'above'}),
        ('fluted oak\ncurve wall', (2560, 4760),     1.2,  (2980, 4580),   0.30, {'from': 'right'}),
        # the senses
        ('sound:\nmurmur\nsinks into\nthe linen', (30, 1520), 2.0, None,  0.0,  {'style': 'sense', 'size': 52}),
        ('colour:\nlinen,\namber,\nterracotta', (30, 1830), 1.5, None,   0.0,  {'style': 'sense', 'size': 52}),
        ('taste: red wine  ·  smell: candle wax', (1340, 4930), -0.8, None, 0.0, {'style': 'sense'}),
    ],

    'intensity': {
        'overlap': {'color': '#B07A50', 'blend': 'soft light', 'opacity': 0.25, 'feather': 60},
        'glows': [
            ((1700, 2950), 650, '#A9502F', 'color', 0.35),          # dining room x the cabins
            ((1700, 2900), 900, '#D98A3D', 'soft light', 0.25),
        ],
    },

    'footer': [
        ('restaurant  —  atmosphere collage 2 of 2', (230, 4868), 'left'),
        ('sound · smell · taste · texture · colour', (3278, 4868), 'right'),
    ],
    'sources': 'Main view: build/v2/render/view2.png (Blender render of the client design). Material swatches: build/v2/swatch/*.png.',
}


# --------------------------------------------------------------------------------------------- #
# print-safe inset: every collage coordinate is scaled about the page centre of the collage
# (title, subtitle and footer stay put), keeping notes and fragments >= ~4 mm from the trim
# --------------------------------------------------------------------------------------------- #
INSET, INSET_C = 0.95, (1754.0, 2600.0)


def _p(pt, k=INSET, c=INSET_C):
    return (c[0] + (pt[0] - c[0]) * k, c[1] + (pt[1] - c[1]) * k)


def _inset(sh, k=INSET):
    v = sh['view']
    v['outline'] = [(*_p(r[:2]), *_p(r[2:4]), r[4]) for r in v['outline']]
    if v.get('frame'):
        f = v['frame']
        v['frame'] = (*_p(f[:2]), *_p(f[2:4]))
    frs = []
    for f in sh['fragments']:
        f = list(f)
        t = f[2]
        if len(t) == 4 and not isinstance(t[0], (tuple, list)):
            x, y = _p(t[:2])
            f[2] = (x, y, t[2] * k, t[3] * k)
        else:
            f[2] = tuple(_p(q) for q in t)
        frs.append(tuple(f))
    sh['fragments'] = frs
    ech = []
    for e in sh['echoes']:
        e = list(e)
        e[0] = (*_p(e[0][:2]), *_p(e[0][2:4]))
        e[2] = (e[2][0] * k, e[2][1] * k)
        ech.append(tuple(e))
    sh['echoes'] = ech
    nts = []
    for n in sh['notes']:
        n = list(n)
        n[1] = _p(n[1])
        if n[3] is not None:
            n[3] = _p(n[3])
        if len(n) > 5:
            o = dict(n[5])
            for key in ('c1', 'c2'):
                if key in o:
                    o[key] = _p(o[key])
            if isinstance(o.get('from'), (tuple, list)):
                o['from'] = _p(o['from'])
            n[5] = o
        nts.append(tuple(n))
    sh['notes'] = nts
    it = sh.get('intensity', {})
    it['glows'] = [(_p(c), r * k, *rest) for c, r, *rest in it.get('glows', [])]
    return sh


SHEETS = {1: _inset(SHEET1), 2: _inset(SHEET2)}
