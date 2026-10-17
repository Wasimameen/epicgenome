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
SHEET1 = {
    'title': {'text': '1.  LOOKING FROM WITHIN', 'x': 230, 'y': 200, 'size': 96, 'tracking': 140},
    'subtitle': {'text': 'chosen area to outside views', 'dx': 'auto', 'dy': 72, 'size': 40, 'tracking': 300},

    'view': {
        'outline': [
            (470, 690, 3080, 4330, ''),            # the body of the image
            (820, 560, 2420, 760, ''),             # raised step, top middle
            (2990, 1240, 3210, 3880, 'R'),         # right step, torn
            (330, 1460, 520, 2880, ''),            # left step
            (1030, 4240, 2560, 4480, 'B'),         # bottom step, torn
            (2560, 4240, 3080, 4400, 'B'),
        ],
        'focus': (0.5, 0.42), 'zoom': 1.0,
        'seed': 11, 'rim': True, 'shadow': (12, 16, 30, 0.30),
    },

    'fragments': [
        # swatch             crop (u0, v0, u1, v1)       target (x, y, w, h)       rot   edge    z        seed
        # ---- behind the view
        ('dark_timber',      (0.10, 0.12, 0.80, 0.42),  (1170, 400, 780, 400),     -0.7, 'cut',  'behind', 101),
        ('linen_drape',      (0.18, 0.05, 0.72, 0.62),  (2540, 430, 690, 860),      1.1, 'LB',   'behind', 102),
        ('dark_timber',      (0.30, 0.25, 0.52, 0.80),  (90, 1020, 300, 760),       0.6, 'cut',  'behind', 103),
        ('velvet',           (0.20, 0.30, 0.60, 0.52),  (2080, 4290, 520, 320),    -1.6, 'cut',  'behind', 104),
        ('dark_timber',      (0.55, 0.30, 0.80, 0.70),  (2700, 4200, 330, 470),     1.4, 'cut',  'behind', 105),
        # ---- in front of the view
        ('split_face_stone', (0.05, 0.05, 0.45, 0.70),  (560, 560, 600, 1060),      0.6, 'torn', 'front',  201),
        ('travertine',       (0.45, 0.10, 0.80, 0.45),  (1080, 650, 420, 560),     -1.4, 'RB',   'front',  202),
        ('travertine',       (0.08, 0.20, 0.38, 0.95),  (160, 1150, 470, 1460),    -0.5, 'torn', 'front',  203),
        ('olive_leaves',     (0.30, 0.30, 0.70, 0.70),  (330, 2420, 520, 600),      1.8, 'torn', 'front',  204),
        ('split_face_stone', (0.05, 0.55, 0.95, 0.95),  (60, 3640, 1100, 700),     -0.8, 'torn', 'front',  205),
        ('glass_block',      (0.10, 0.20, 0.55, 0.70),  (1100, 3830, 620, 700),     0.9, 'cut',  'front',  206),
        ('brass',            (0.20, 0.20, 0.60, 0.55),  (1740, 3990, 560, 490),    -0.5, 'cut',  'front',  207),
        ('sheer_fabric',     (0.40, 0.05, 0.80, 0.80),  (2650, 640, 600, 1220),    -0.7, 'TB',   'front',  208),
        ('glass_block',      (0.55, 0.10, 0.85, 0.80),  (2970, 1580, 400, 1120),    0.4, 'cut',  'front',  209),
        ('travertine',       (0.55, 0.05, 0.85, 0.70),  (3080, 2720, 380, 1240),   -1.3, 'torn', 'front',  210),
        ('concrete',         (0.20, 0.10, 0.55, 0.55),  (2330, 4170, 430, 540),     1.1, 'torn', 'front',  211),
    ],

    'echoes': [
        # src_box on the page          scale  (dx, dy)    rot   edge    seed
        ((2470, 2380, 2990, 2960),     1.08,  (150, 40),  -1.2, 'torn', 301),
        ((860, 3140, 1360, 3620),      1.12,  (-120, 150), 1.0, 'LTB',  302),
    ],

    'notes': [
        # text                    (x, y) baseline   rot    arrow tip       bend   opts
        ('texture\n+ shadow',     (110, 820),        2.5,  (330, 1240),    0.30, {'from': 'below'}),
        ('filtered light',        (2000, 470),      -1.5,  (2160, 1060),  -0.25, {'from': 'below'}),
        ('soft fabric',           (2950, 340),       2.0,  (2930, 760),    0.35, {'from': 'below'}),
        ('glass\nblocks',         (3260, 1350),     -3.0,  (3180, 1640),   0.35, {'from': 'below'}),
        ('olive tree',            (50, 3200),        2.0,  (560, 2960),   -0.35, {'from': 'right'}),
        ('split face stone',      (330, 4570),       0.5,  (230, 4330),    0.40, {'from': 'left'}),
        ('warm + intimate',       (1400, 4680),     -1.0,  (1880, 4430),  -0.30, {'from': 'above_right'}),
        ('concrete',              (2830, 4800),      1.5,  (2690, 4660),   0.25, {'from': 'left'}),
        # sensory notes (softer, no arrow)
        ('leaves rustle\nabove',  (60, 3330),        2.0,  None,           0.0,  {'style': 'sense'}),
        ('fresh bread + olive oil', (1400, 4780),   -1.0,  None,           0.0,  {'style': 'sense'}),
        ('street hum,\nmuffled',  (3110, 4200),     -2.0,  None,           0.0,  {'style': 'sense'}),
    ],

    'intensity': {
        'overlap': {'color': '#C27A3E', 'blend': 'soft light', 'opacity': 0.42, 'feather': 60},
        'glows': [
            ((1700, 2500), 1250, '#B8643A', 'soft light', 0.32),   # the chosen area
        ],
    },

    'footer': [
        ('restaurant  —  atmosphere collage 1 of 2', (230, 4868), 'left'),
        ('sound · smell · taste · texture · colour', (3278, 4868), 'right'),
    ],
    'sources': 'Main view: build/v2/render/view1.png. Material swatches: build/v2/swatch/*.png.',
}


# --------------------------------------------------------------------------------------------- #
# SHEET 2 - LOOKING TOWARDS (chosen area from a distance)                  PROVISIONAL
# --------------------------------------------------------------------------------------------- #
SHEET2 = {
    'title': {'text': '2.  LOOKING TOWARDS', 'x': 230, 'y': 200, 'size': 96, 'tracking': 140},
    'subtitle': {'text': 'chosen area from a distance', 'dx': 'auto', 'dy': 72, 'size': 40, 'tracking': 300},

    'view': {
        'outline': [
            (520, 760, 3020, 4300, ''),
            (900, 640, 2560, 800, ''),
            (380, 1300, 560, 3400, 'L'),
            (2960, 1500, 3160, 3900, ''),
            (760, 4220, 2400, 4440, 'B'),
        ],
        'focus': (0.5, 0.5), 'zoom': 1.0,
        'seed': 12, 'rim': True, 'shadow': (12, 16, 30, 0.30),
    },

    'fragments': [
        # ---- behind
        ('dark_timber',      (0.20, 0.05, 0.60, 0.40),  (250, 470, 430, 560),       0.8, 'cut',  'behind', 401),
        ('linen_drape',      (0.05, 0.05, 0.95, 0.45),  (1000, 470, 1500, 420),    -0.6, 'B',    'behind', 402),
        ('dark_timber',      (0.55, 0.10, 0.85, 0.95),  (330, 1720, 330, 1560),     0.3, 'cut',  'behind', 403),
        ('velvet',           (0.10, 0.20, 0.55, 0.50),  (1420, 4250, 560, 400),    -1.2, 'cut',  'behind', 404),
        ('fluted_oak',       (0.20, 0.10, 0.50, 0.90),  (2760, 820, 360, 1300),     0.6, 'cut',  'behind', 405),
        # ---- in front
        ('sheer_fabric',     (0.10, 0.30, 0.45, 0.70),  (230, 960, 420, 720),      -0.8, 'torn', 'front',  501),
        ('concrete',         (0.05, 0.05, 0.75, 0.55),  (2480, 290, 920, 760),      1.3, 'torn', 'front',  502),
        ('white_brick',      (0.30, 0.05, 0.75, 0.95),  (3120, 1150, 360, 1800),   -0.5, 'L',    'front',  503),
        ('travertine',       (0.15, 0.15, 0.55, 0.85),  (190, 2380, 460, 1150),    -1.0, 'torn', 'front',  504),
        ('glass_block',      (0.20, 0.05, 0.55, 0.95),  (2600, 1700, 420, 1650),    0.3, 'cut',  'front',  505),
        ('breccia_marble',   (0.10, 0.20, 0.70, 0.95),  (2860, 3330, 600, 1280),   -1.1, 'torn', 'front',  506),
        ('split_face_stone', (0.05, 0.30, 0.80, 0.70),  (400, 3880, 900, 560),      0.7, 'torn', 'front',  507),
        ('brass',            (0.10, 0.30, 0.55, 0.65),  (2340, 4230, 480, 420),     0.9, 'cut',  'front',  508),
        ('dark_timber',      (0.05, 0.05, 0.30, 0.90),  (1990, 4170, 290, 470),    -1.8, 'cut',  'front',  509),
    ],

    'echoes': [
        ((1500, 900, 2300, 1350),      1.06,  (40, -150),  0.8, 'TLR',  601),
        ((600, 2900, 1100, 3500),      1.10,  (-140, 60), -1.0, 'torn', 602),
    ],

    'notes': [
        ('layered ceiling elements', (1330, 455),   -1.0,  (1560, 1000),   0.25, {'from': 'below'}),
        ('concrete',              (2280, 230),       1.5,  (2700, 520),   -0.35, {'from': 'right'}),
        ('warm\nlighting',        (40, 1880),        2.5,  (760, 2400),   -0.35, {'from': 'below_right'}),
        ('white\nbrick\nwall',    (3300, 3100),     -2.5,  (3330, 2930),   0.35, {'from': 'above', 'gap': 14}),
        ('movement through space', (300, 4640),      1.0,  (720, 4380),    0.30, {'from': 'above'}),
        ('tactile materials',     (1430, 4720),     -0.8,  (1700, 4560),  -0.25, {'from': 'above_right'}),
        ('unique stone',          (2640, 4780),      1.2,  (3020, 4560),   0.30, {'from': 'right'}),
        # sensory
        ('low murmur,\nsoft acoustics', (40, 3660),  1.5,  None,           0.0,  {'style': 'sense'}),
        ('red wine + candle wax', (1430, 4815),     -0.8,  None,           0.0,  {'style': 'sense'}),
    ],

    'intensity': {
        'overlap': {'color': '#C27A3E', 'blend': 'soft light', 'opacity': 0.42, 'feather': 60},
        'glows': [
            ((1800, 2900), 1150, '#B8643A', 'soft light', 0.32),
        ],
    },

    'footer': [
        ('restaurant  —  atmosphere collage 2 of 2', (230, 4868), 'left'),
        ('sound · smell · taste · texture · colour', (3278, 4868), 'right'),
    ],
    'sources': 'Main view: build/v2/render/view2.png. Material swatches: build/v2/swatch/*.png.',
}

SHEETS = {1: SHEET1, 2: SHEET2}
